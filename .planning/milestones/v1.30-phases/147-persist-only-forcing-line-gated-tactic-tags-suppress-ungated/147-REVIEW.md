---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
reviewed: 2026-07-01T20:38:07Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/services/flaws_service.py
  - app/services/eval_drain.py
  - app/routers/eval_remote.py
  - app/schemas/eval_remote.py
  - scripts/remote_eval_worker.py
  - alembic/versions/20260701_190758_eb341e836ee9_suppress_ungated_tactic_tags_old_corpus.py
findings:
  critical: 2
  warning: 3
  info: 1
  total: 6
status: issues_found
---

# Phase 147: Code Review Report

**Reviewed:** 2026-07-01T20:38:07Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The `blobs_pending=True` deviation documented in 147-05-SUMMARY.md was traced line-by-line
through `_classify_tactic_gated` and is **correct**: it only affects the case where a
flaw's blob key is entirely absent from `flaw_pv_blobs` (server found a flaw the worker
didn't blob at all), has zero effect on flaws with a real submitted blob, and zero effect
on the D-06 `[]`-sentinel / mate-adjacent FINAL cases. `flaws_service.py`'s parameter
threading is clean and additive.

However, two of the new write paths that were supposed to *close* the ungated-tag window
have their own correctness defects:

1. **`_apply_atomic_submit` (app/routers/eval_remote.py) silently discards the
   `failed_ply_count` returned by `_apply_full_eval_results` and unconditionally stamps
   both completion markers**, regardless of whether the worker's submitted eval batch has
   holes. This reintroduces the exact "permanently stamped with gaps" bug class that
   Phase 119 (SEED-045, `MAX_EVAL_ATTEMPTS` bounded retry) was built to fix — a bug this
   same file's own `resweep_holed_games()` docstring describes verbatim as the
   pre-Phase-119 failure mode.

2. **`_hint_flaw_plies` (scripts/remote_eval_worker.py) has a systematic off-by-one
   indexing bug** that misaligns the worker's locally-hinted flaw plies against the
   server's post-move eval convention. Verified numerically against `_post_move_eval`
   and `_collect_full_ply_targets`: the hint's returned ply set is consistently the
   *wrong* index relative to the server's authoritative `classify_game_flaws`, so nearly
   all `blob_nodes` tokens the worker submits reference plies the server never classifies
   as flaws. The `blobs_pending=True` safety net still prevents any *raw/ungated* tag
   from being persisted (the core Phase 147 safety invariant holds), but the Part-B
   optimization this phase shipped — co-submitting gate-ready blobs so games are gated
   immediately instead of falling back to tier-4 — is functionally a no-op for the
   upgraded worker as written.

The old-corpus suppression migration is correct against every scenario its own test
suite constructs, and the `IS NULL` vs `[]` JSONB distinction is respected throughout
(no repeat of the asyncpg-JSONB-null pitfall). Its batching loop does have a latent
structural correctness gap (WARNING below) that is not currently reachable via any real
write path in this codebase, but would silently truncate the migration if that ever
changed.

## Structural Findings (fallow)

None provided for this review.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `/atomic-submit` unconditionally stamps completion markers, bypassing the SEED-045 bounded-retry/hole-detection invariant

**File:** `app/routers/eval_remote.py:1225-1250`
**Issue:**
`_apply_atomic_submit`'s write phase calls `_apply_full_eval_results` but never captures
its return value:

```python
async with async_session_maker() as write_session:
    await _apply_full_eval_results(
        write_session, targets, {}, engine_result_map, is_lichess_eval_game
    )
    ...
    await _mark_full_evals_completed(write_session, game_id)
    await _mark_full_pv_completed(write_session, game_id)
```

`_apply_full_eval_results` returns `failed_ply_count` — the number of NULL-hole
engine-game plies (`app/services/eval_drain.py:536-641`). The sibling `_apply_submit`
handler (`app/routers/eval_remote.py:284-352`, unchanged by this phase) explicitly
branches on this value into Path A (no holes → stamp), Path B (holes, `attempts <
MAX_EVAL_ATTEMPTS` → leave pending, increment `full_eval_attempts`, do NOT stamp), and
Path C (holes, cap reached → stamp anyway with an aggregated `sentry_sdk.capture_message`
warning). `_apply_atomic_submit` has none of this: it calls
`_mark_full_evals_completed`/`_mark_full_pv_completed` unconditionally on every submit,
regardless of hole count, and never increments `full_eval_attempts`.

Consequence: any transient engine failure during the worker's full-ply pass (one bad FEN,
one Stockfish timeout, one crashed subprocess) produces a game that is permanently marked
`full_evals_completed_at`/`full_pv_completed_at` complete with a NULL `eval_cp`/`eval_mate`
hole in `game_positions` — on the very first attempt, with zero retry and zero operator
visibility (no Sentry event is ever raised for a hole taking this path, unlike Path C).
`AtomicSubmitResponse` (`app/schemas/eval_remote.py:231-236`) doesn't even carry a
`failed_ply_count`/`stamp_complete` field, so the omission isn't observable from the
response either. `resweep_holed_games()` (`app/services/eval_drain.py:2761-2800`)
documents this *exact* failure mode as the reason SEED-045 exists: "Before Phase 119, the
drain stamped `full_evals_completed_at` unconditionally... games with transient mid-game
engine holes were permanently marked 'fully analyzed' with gaps." `_apply_atomic_submit`
reintroduces that pre-Phase-119 bug for every game routed through the new atomic path.
No test in `tests/test_eval_worker_endpoints.py` exercises a holed submit against
`/atomic-submit` (grep for `failed_ply_count`/`full_eval_attempts` only turns up the
`/submit` tests).

**Fix:**
```python
async with async_session_maker() as write_session:
    failed_ply_count = await _apply_full_eval_results(
        write_session, targets, {}, engine_result_map, is_lichess_eval_game
    )
    ...
    new_attempts = current_attempts + 1  # requires reading game.full_eval_attempts in the read phase
    if failed_ply_count == 0:
        await _mark_full_evals_completed(write_session, game_id)
        await _mark_full_pv_completed(write_session, game_id)
        stamp_complete = True
    elif new_attempts < MAX_EVAL_ATTEMPTS:
        await write_session.execute(
            update(Game.__table__).where(Game.__table__.c.id == game_id)
            .values(full_eval_attempts=new_attempts)
        )
        stamp_complete = False
    else:
        await _mark_full_evals_completed(write_session, game_id)
        await _mark_full_pv_completed(write_session, game_id)
        sentry_sdk.set_context("eval", {"game_id": game_id, "hole_count": failed_ply_count, "attempts": new_attempts})
        sentry_sdk.set_tag("source", "remote_eval_worker")
        sentry_sdk.capture_message(
            "atomic-submit: stamping complete after MAX_EVAL_ATTEMPTS with residual holes",
            level="warning",
        )
        stamp_complete = True
```
Mirror `_apply_submit`'s Path A/B/C exactly (including reading `current_attempts` in the
read phase and only signalling `_signal_flaw_completion`/stamping `eval_jobs` when
`stamp_complete`), and add `failed_ply_count`/`stamp_complete` to `AtomicSubmitResponse`
so the worker/operator can observe it.

---

### CR-02: `_hint_flaw_plies` is off-by-one relative to the server's post-move eval convention, making the worker's blob co-submission structurally miss the true flaw plies

**File:** `scripts/remote_eval_worker.py:182-215`
**Issue:**
```python
def _hint_flaw_plies(evals: list[dict[str, object]]) -> set[int]:
    eval_by_ply: dict[int, dict[str, object]] = {int(cast(int, e["ply"])): e for e in evals}
    ...
    hint_positions: list[GamePosition] = []
    for ply in range(max_ply + 1):
        pos = GamePosition()
        pos.ply = ply
        e = eval_by_ply.get(ply)
        pos.eval_cp = cast("int | None", e["eval_cp"]) if e is not None else None
        ...
        hint_positions.append(pos)
    all_moves = _run_all_moves_pass(hint_positions)
```

`evals` is **position-keyed** (per `_eval_positions`, each entry is the eval OF the
pre-push board at that `ply`, exactly matching `_FullPlyEvalTarget.ply` /
`_apply_full_eval_results`'s `pos_eval[target.ply]`). `_run_all_moves_pass`
(`app/services/flaws_service.py:338-379`), by contrast, expects **row-keyed / post-move**
values: `positions[N].eval_cp` must be "the eval AFTER move N", i.e.
`pos_eval[N + 1]` per `_post_move_eval` (`app/services/eval_drain.py:393-406`) — this is
literally the "eval-AFTER landmine" the rest of the codebase explicitly documents as
Pitfall 1 (`app/services/flaws_service.py:44-45, 347-357`).

`_hint_flaw_plies` assigns `hint_positions[ply].eval_cp = evals[ply]` directly — no `+1`
shift — so `hint_positions[k] == db_row[k-1]` (traced against `_post_move_eval`). Concrete
example using the module's own test fixture `_ATOMIC_EVALS`
(`tests/test_remote_eval_worker.py:495-499`, position-keyed: ply0=0, ply1=+600, ply2=+600
for a 2-move game): if these exact evals were submitted through `/atomic-submit`, the
resulting `game_positions` rows would be `row0 = pos_eval[1] = +600`, `row1 = pos_eval[2]
= +600` — **zero ES drop, no flaw at all** under the server's own
`classify_game_flaws`. Yet `_hint_flaw_plies(_ATOMIC_EVALS) == {1}`
(`tests/test_remote_eval_worker.py:509`) reports a "blunder" at ply=1 — a pure artifact
of comparing `eval_by_ply[0]` (the *initial* position, which is never itself gradable —
`_run_all_moves_pass` never emits a flaw for the true row 0) against `eval_by_ply[1]`.
The unit test locks in this output without cross-checking it against what the server's
real classify would find for the same underlying eval data, so it doesn't catch the bug.

Because the hinted ply is shifted, `_build_blob_walk_targets`
(`scripts/remote_eval_worker.py:218-252`) walks/tokenizes the wrong board pair for
`"missed"`/`"allowed"`, and the resulting `blob_nodes` tokens almost never key-match any
`(flaw_ply, line)` pair the server's own `_derive_atomic_sentinel_lines` /
`classify_game_flaws` produces. Net effect: for a typical game, essentially every
cp-based flaw the server finds has `flaw_pv_blobs.get(flaw_ply) is None`, so
`blobs_pending=True` suppresses its tag to NULL (safe, but the worker's whole MultiPV-2
blob-walk pass was wasted compute that never reaches a gated tag — the entire point of
147-06/SEED-074 Part B is defeated). 147-06-SUMMARY.md's "ply-indexing correctness proof"
claim does not hold up against this trace.

**Fix:** shift the eval lookup by one when building `hint_positions` so row `m` holds
`pos_eval[m + 1]`, matching `_post_move_eval`:
```python
hint_positions: list[GamePosition] = []
for row_ply in range(max_ply):  # one hint row per real move (0..max_ply-1)
    pos = GamePosition()
    pos.ply = row_ply
    e = eval_by_ply.get(row_ply + 1)
    pos.eval_cp = cast("int | None", e["eval_cp"]) if e is not None else None
    pos.eval_mate = cast("int | None", e["eval_mate"]) if e is not None else None
    hint_positions.append(pos)
```
Update `test_hint_flaw_plies_selects_mistake_and_blunder_only` and the
`_eval_atomic_game`/`_build_blob_walk_targets` tests to assert against evals that
correspond to a *real* db-row shift (e.g. add a genuine 3-position fixture and verify the
hint ply matches what `classify_game_flaws` would compute for the equivalent
`game_positions` rows), so a regression here is caught by the fixture rather than locked
in by it.

## Warnings

### WR-01: Old-corpus suppression migration's batch CTE can select rows it will never update, risking premature loop termination if a future write path produces asymmetric per-orientation blob state

**File:** `alembic/versions/20260701_190758_eb341e836ee9_suppress_ungated_tactic_tags_old_corpus.py:66-95`
**Issue:**
The batching loop's CTE selects candidates via a looser predicate than the UPDATE's guard:

```sql
WITH batch AS (
    SELECT ...,
           (gf.allowed_pv_lines IS NULL AND gp.eval_cp IS NOT NULL AND gf.allowed_tactic_motif IS NOT NULL) AS suppress_allowed,
           (gf.missed_pv_lines  IS NULL AND gp.eval_cp IS NOT NULL AND gf.missed_tactic_motif  IS NOT NULL) AS suppress_missed
    FROM game_flaws gf JOIN game_positions gp ON ...
    WHERE (gf.allowed_pv_lines IS NULL OR gf.missed_pv_lines IS NULL)
      AND gp.eval_cp IS NOT NULL
      AND (gf.allowed_tactic_motif IS NOT NULL OR gf.missed_tactic_motif IS NOT NULL)
    LIMIT batch_size
)
UPDATE game_flaws gf ... FROM batch b WHERE ... AND (b.suppress_allowed OR b.suppress_missed);
GET DIAGNOSTICS rows_updated = ROW_COUNT;
```
A row can satisfy the CTE's `WHERE` while `suppress_allowed` AND `suppress_missed` are
both false — e.g. `allowed_pv_lines` real/non-NULL with `allowed_tactic_motif` NULL, and
`missed_pv_lines` NULL with `missed_tactic_motif` also NULL. This row is selected into
`batch` (consuming one of `batch_size` slots) but never updated by the following
`UPDATE ... WHERE (b.suppress_allowed OR b.suppress_missed)`, so it re-enters every
subsequent batch unchanged. `WHILE rows_updated > 0` terminates as soon as any single
LIMIT-100000 batch happens to update zero rows — which, without an `ORDER BY`, could
happen on the very first iteration if enough non-suppressible-but-matching rows sort
ahead of the genuinely suppressible ones, silently leaving the rest of the old corpus
un-suppressed with no error, no warning, no diagnostic. `tests/
test_migration_suppress_ungated_tactic_tags.py`'s Row 4 fixture
(lines 184-192) proves this exact "matches WHERE, both suppress flags false" shape is
constructible.

Given the current write paths (`bulk_insert_game_flaws` never sets the blob columns;
`_batch_update_flaw_pv_lines` always writes `allowed_pv_lines` and `missed_pv_lines`
together for any flaw_ply key present in `blob_map`), organically-produced rows land in
either (NULL, NULL) or (non-NULL, non-NULL) states, which keeps this specific failure mode
out of reach today. It becomes reachable, though, the moment any write path assembles a
`blob_map` entry with one real line and one `[]`/missing line for the same flaw_ply (see
the `_assemble_flaw_blobs_from_submit`/`_assemble_one_line_blob` machinery this phase
extends to `AtomicBlobNode`).

**Fix:** fold the exact update condition into the CTE's `WHERE` so every selected row is
guaranteed to be updated (and `rows_updated` accurately reflects batch progress):
```sql
WHERE gp.eval_cp IS NOT NULL
  AND (
       (gf.allowed_pv_lines IS NULL AND gf.allowed_tactic_motif IS NOT NULL)
    OR (gf.missed_pv_lines  IS NULL AND gf.missed_tactic_motif  IS NOT NULL)
  )
```
This removes the possibility of a batch consisting entirely of non-suppressible rows and
makes the loop's termination condition provably correct regardless of future write-path
changes.

### WR-02: `AtomicSubmitResponse.flaws_written` can report stale pre-existing counts instead of flaws actually written by this call

**File:** `app/routers/eval_remote.py:1243-1245`
**Issue:** `flaws_written` is computed via `COUNT(*) FROM game_flaws WHERE game_id =
:game_id` immediately after `_classify_and_fill_oracle`. When that function takes its
early-return path (`"reason" in flaw_result` — insufficient eval coverage even after this
submit), it does **not** run `delete_flaws_for_game`/`bulk_insert_game_flaws`, so the
COUNT reflects whatever flaw rows already existed for the game (e.g. leftover rows from an
earlier entry-pass `_classify_and_insert_flaws` insert) rather than "flaws written by this
atomic-submit call." The field name and the docstring ("how many flaw/blob rows were
written") imply a delta, not a snapshot count.

**Fix:** have `_classify_and_fill_oracle` return whether it took the early-return branch
(or the actual inserted row count), and report `0` for `flaws_written` in that case, or
rename/document the field as "current flaw row count for this game" if the snapshot
semantics are intentional.

### WR-03: `_apply_atomic_submit` computes the token-range guard from `targets`, but doesn't validate `body.evals` ply values the same way

**File:** `app/routers/eval_remote.py:1179-1211`
**Issue:** The token tamper guard (T-147-02) validates every `body.blob_nodes[i].token`'s
embedded `flaw_ply` against `game_length`, but `body.evals` entries (fed straight into
`engine_result_map` at line 1190-1192) are never range-checked against the game's actual
ply count before being passed to `_apply_full_eval_results`. An out-of-range `ply` in
`body.evals` (e.g., a worker bug submitting a stale/duplicate eval for a ply beyond the
game's length) is looked up via `engine_result_map.get(target.ply)` inside
`_resolve_full_eval`, so it is effectively a harmless no-op today (unmatched entries are
simply never consulted) — but this relies on that downstream `.get()` behavior rather than
an explicit contract, and the asymmetry (evals unchecked, blob_nodes strictly checked)
is worth a short comment so a future refactor of `_apply_full_eval_results` doesn't
silently start indexing `engine_result_map` by an untrusted key.

**Fix:** either add a one-line comment at line 1190 noting that `engine_result_map` entries
for out-of-range plies are inert by construction (dict lookups by `target.ply` only), or
add the same `0 <= e.ply < game_length` filter applied to `body.blob_nodes` tokens.

## Info

### IN-01: `_apply_atomic_submit` never signals `_signal_flaw_completion` conditionally, unlike `_apply_submit`

**File:** `app/routers/eval_remote.py:1269-1270`
**Issue:** `_apply_submit` only calls `_signal_flaw_completion(owner_id)` when
`stamp_complete` is true (Path B — holes remain, not yet complete — deliberately skips the
signal). `_apply_atomic_submit` calls it unconditionally after every commit. This is a
direct consequence of CR-01 (no `stamp_complete` concept exists in the atomic path today),
so fixing CR-01 should also gate this signal the same way `_apply_submit` does, to avoid
prematurely notifying user-facing caches/UI that a game's analysis is complete while holes
remain.
**Fix:** covered by the CR-01 fix — gate this call on the reintroduced `stamp_complete`.

---

_Reviewed: 2026-07-01T20:38:07Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

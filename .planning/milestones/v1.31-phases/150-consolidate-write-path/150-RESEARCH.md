# Phase 150: Consolidate Write Path - Research

**Researched:** 2026-07-04
**Domain:** Backend eval-write-path consolidation (FastAPI + SQLAlchemy async + Stockfish, no new libraries)
**Confidence:** HIGH (this is a pure code-relocation/audit task against the current repo — every claim below is `[VERIFIED: codebase]` via direct read/grep of the files at HEAD unless marked otherwise)

## Summary

This phase does not need new libraries, external docs, or unfamiliar patterns — it is a
structure-only refactor of code that already exists and already works (post-Phase-149,
post-FLAWCHESS-8D). The research value here is exclusively **re-locating symbols** (the
CONTEXT.md/SEED-080 line numbers predate Phase 149's deletions) and **verifying the exact
shape of each "copy"** so the planner can write precise task diffs instead of vague
"consolidate the copies" instructions.

**Primary recommendation:** Execute R1 → R4 → R3 → R7 exactly as CONTEXT.md specifies, but
correct one factual drift before planning: **R1 now unifies 2 live copies, not 3** — Phase
149 (`53ea905e`) already deleted the Gen-1 `_apply_submit` completion-decision copy in
`eval_remote.py`. The remaining two (`eval_drain.py::_full_drain_tick`,
`eval_remote.py::_apply_atomic_submit`) are still genuinely duplicated and worth
`apply_completion_decision()`. For R4, one of the "4 repeated call sites" is materially
different from the other three (see R4 section) — the unification needs a parameterized
"skip overlay" branch, not a byte-identical merge. For R3, the codebase already has
exactly the primitive this phase needs to build on: `TACTIC_TAG_COLUMNS` (8-column tuple,
single source of truth for `bulk_update_tactic_tags`/`retag_flaws.py`) — D-04's
`FLAW_BLOB_COLUMNS` is a two-line extension of an existing pattern, not new ground. And a
project-documented landmine (`project_asyncpg_jsonb_null_vs_sql_null`) directly threatens
the most natural implementation of the diff/upsert (a single `ON CONFLICT DO UPDATE ...
COALESCE(...)` statement) — the safe design is a 4-way partition (delete / insert-new /
update-fresh-blob / update-preserve-by-omission) using patterns already established in
this file (`bulk_insert_game_flaws`, `_restore_preserved_flaw_blobs`'s ORM
bulk-update-by-PK, `_batch_update_flaw_pv_lines`'s raw-SQL JSONB write).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Completion decision (Path A/B/C, `eval_jobs` stamp) | API/Backend (service layer) | — | Pure business logic over DB state; no HTTP concerns; belongs in a service module, called by both the in-process drain loop and the router |
| Classify preamble (load + overlay + classify) | API/Backend (service layer) | — | DB read + in-memory position mutation + call into the classify kernel; no HTTP |
| Flaw write (diff/upsert) | Database / Storage (write path) | API/Backend (transaction orchestration) | The actual persistence semantics live in repository-layer SQL; the service layer owns transaction boundaries (single write_session, T-117-11) |
| Submit/tick orchestration (`eval_apply.py`) | API/Backend (service layer) | — | Coordinates read session → CPU work (no session) → write session; router and in-process loop both call into this one entry point |
| Router (`eval_remote.py`) | API/Backend (HTTP layer) | — | Should shrink to auth, request/response marshaling, and a call into `eval_apply.py` — no private-helper reach-through into `eval_drain.py` |
| EnginePool acquire/analyse/restart | API/Backend (engine wrapper) | — | Process-management + UCI protocol concern, isolated in `app/services/engine.py`; no DB access |
| Tier-3/tier-4 ES lottery | Database / Storage (query layer) | API/Backend (`eval_queue_service.py`) | Raw parameterized SQL against `games`/`game_flaws`/`users`; the "one shared implementation" is a query-shape helper, not a router/service concern |

This phase touches **zero** browser/CDN tiers — confirmed server-side-only by CONTEXT.md
and by the fact that none of the touched files (`eval_drain.py`, `eval_remote.py`,
`engine.py`, `eval_queue_service.py`) are imported by any frontend code (Python-only,
no client contract change).

## Symbol Re-Location (current HEAD, post-Phase-149)

All line numbers below are from the current `main`-branch HEAD (commit `f6ed49e9` /
branch `gsd/phase-150-consolidate-write-path`), verified via direct grep — **do not** trust
the pre-149 line numbers in SEED-080/CONTEXT.md's `canonical_refs`.

### `app/services/eval_drain.py` (3013 lines)

| Symbol | Line | Role |
|---|---|---|
| `_classify_and_fill_oracle` | 705 | R3 target — delete-then-insert → diff/upsert |
| `_flaw_engine_plies` | 901 | R4 site #1 — **structurally different**, see R4 below |
| `_missing_flaw_pv_targets` | 979 | R4 site #2 |
| `_reconstruct_pos_eval` | 954 | Shared helper the R4 sites call (pure, keep as-is) |
| `_build_flaw_multipv2_blobs` | 1216 | R4 site #3 |
| `_derive_atomic_sentinel_lines` | 1340 | R4 site #4 |
| `_batch_update_flaw_pv_lines` | 1413 | Raw-SQL JSONB writer — reusable pattern for R3's "fresh blob" branch |
| `_run_multipv2_pass` | 1447 | Thin wrapper enforcing write-session discipline |
| `_build_flaw_blob_lease_positions` | 1463 | Tier-4 lease positions (untouched by this phase) |
| `_full_drain_tick` | 2513 | R1 copy #1 (Path A/B/C at lines 2767–2821) + R7 consumer of the future `apply_full_eval` |
| `MAX_EVAL_ATTEMPTS` | 111 | Constant (`= 3`), imported by `eval_remote.py` |

### `app/routers/eval_remote.py` (1401 lines)

| Symbol | Line | Role |
|---|---|---|
| `entry_submit_eval` | 531 | Entry lane — **does NOT have a Path A/B/C completion decision** (see R1 correction below); out of scope for R1 |
| `_snapshot_preserved_flaw_blobs` | 961 | R3 target — DELETE |
| `_restore_preserved_flaw_blobs` | 1014 | R3 target — DELETE |
| `_apply_atomic_submit` | 1060 | R1 copy #2 (Path A/B/C at lines 1281–1334) + the `_apply_full_eval` body R7 moves to `eval_apply.py` |
| `atomic_submit_eval` | 1363 | Thin router wrapper calling `_apply_atomic_submit` |
| Private-helper import block | 81–107 | 21 private symbols + 3 constants imported from `eval_drain.py` — the R7 "router imports private drain helpers" leak |

### `app/services/engine.py` (647 lines)

| Symbol | Line | Role |
|---|---|---|
| `EnginePool._analyse` | 464 | Copy #1 — scalar `analyse()`, returns `(cp, mate)` |
| `EnginePool._analyse_with_pv` | 515 | Copy #2 — scalar `analyse()`, returns raw `InfoDict \| None` |
| `EnginePool._analyse_multipv2` | 573 | Copy #3 — `analyse(..., multipv=2)`, returns `list[InfoDict] \| None` |

### `app/services/eval_queue_service.py` (864 lines)

| Symbol | Line | Role |
|---|---|---|
| `_claim_tier3_derived` | 277 | Tier-3 ES lottery — 2-stage (user, game) + a 3rd residual-fallback stage |
| `_claim_tier4_blob` | 489 | Tier-4 ES lottery — 2-stage (user, game), no residual fallback |

### `app/services/eval_apply.py`

Does not exist yet — R7 target (new module).

## R1 — Completion Decision (WRITE-01)

**Correction to CONTEXT.md:** the phase description and REQUIREMENTS.md both say "3
verbatim copies (`eval_drain.py` ×1, `eval_remote.py` ×2)". `[VERIFIED: codebase]` — as of
this HEAD there are only **2 live copies**. Phase 149 (commit `53ea905e`, "retire dead
Gen-1 eval protocol") deleted the Gen-1 `/lease`+`/submit` pair and its `_apply_submit`
function, which held the second `eval_remote.py` copy. `entry_submit_eval` (the surviving
non-atomic submit endpoint) does **not** have a Path A/B/C decision at all — its completion
model is a flat "stamp the full leased set, no holes concept, no `MAX_EVAL_ATTEMPTS`"
(lines 640–645), because entry-lane targets either resolve or don't; there is no bounded
retry ladder. So R1's real scope is: **replace `_full_drain_tick`'s inline Path A/B/C block
(lines 2767–2821) and `_apply_atomic_submit`'s inline copy (lines 1281–1334) with one
`apply_completion_decision()`.** This does not change WRITE-01's intent or risk — it is
still worth doing — but the planner's task description/verification should say "2 copies"
not "3", and the "replacing the 3 verbatim copies" language in WRITE-01/ROADMAP should be
read as historically accurate-at-authorship-time rather than currently accurate.

**Exact shared shape** (both are line-for-line identical except for a Sentry source tag,
an inline-vs-module-level `EvalJob` import, and a Sentry-capture-message vs. logger.warning
choice on the Path C branch):

```
new_attempts = current_attempts + 1
if failed_ply_count == 0:
    # Path A: no holes — stamp both markers complete.
    mark_full_evals_completed(); mark_full_pv_completed(); stamp_complete = True
elif new_attempts < MAX_EVAL_ATTEMPTS:
    # Path B: holes remain, under cap — increment attempts, leave pending.
    UPDATE games SET full_eval_attempts = new_attempts; stamp_complete = False
else:
    # Path C: holes remain AND cap reached — stamp anyway (D-116-07 no-loop invariant).
    mark_full_evals_completed(); mark_full_pv_completed()
    <emit ONE aggregated warning>; stamp_complete = True

if stamp_complete and job_id is not None:
    UPDATE eval_jobs SET status='completed', completed_at=now()
        WHERE id = :job_id AND status = 'leased'   # guard: late/expired-lease submit is a no-op
```

Divergences to preserve as **parameters**, not code forks:
- `eval_drain.py` uses `logger.warning(...)` for the Path C log; `eval_remote.py` uses
  `sentry_sdk.set_context/set_tag/capture_message(level="warning")`. `eval_drain.py`'s
  comment explains this is deliberate (FLAWCHESS-5V: an earlier Sentry-per-tick call burned
  the error quota for an *expected* cap-path outcome, not a bug) — **do not silently unify
  these to one behavior**; parameterize the "on Path C" callback, or keep both explicit call
  sites passing a different `warn_fn`.
- `eval_drain.py` does `from app.models.eval_jobs import EvalJob` as a **local import inside
  the function body** (line ~2808), not at module scope like `eval_remote.py`'s top-level
  import (line 108). This is very likely a historical artifact avoiding some earlier
  circular-import concern (not verified as still-needed) — flag it to the planner rather
  than assuming it's load-bearing; test after moving to confirm no cycle reappears.
- `_apply_atomic_submit`'s copy additionally calls `upsert_worker_heartbeat(...)`
  (PRUNE-06 telemetry) right before commit — this is NOT part of the completion decision
  itself and should stay a sibling call in the orchestration function, not get folded into
  `apply_completion_decision()`.
- The Sentry `source` tag differs (`"full_eval_drain"` vs. `"remote_eval_worker"`) — this
  is exactly the "differing arg" CONTEXT.md's Integration Points section anticipated;
  thread it as a `source: Literal["full_eval_drain", "remote_eval_worker"]` parameter.

**Signature sketch** (planner may refine): `apply_completion_decision(write_session, *,
game_id, job_id, failed_ply_count, current_attempts, source, on_path_c_capacity_reached) ->
bool` (returns `stamp_complete`).

## R4 — Classify Preamble (WRITE-02)

**Important nuance CONTEXT.md does not fully capture:** the 4 named sites do **not** share
one identical preamble. Three of them are byte-for-byte the same shape; the fourth is
fundamentally different, and unifying all 4 behind one helper naively will silently break
lichess-eval-game flaw-ply detection.

**Shared preamble (`_missing_flaw_pv_targets` L979, `_build_flaw_multipv2_blobs` L1216,
`_derive_atomic_sentinel_lines` L1340)** — identical 3-step shape:

```python
pos_eval = _reconstruct_pos_eval(targets, dedup_map, engine_result_map)   # pure, in-memory
async with async_session_maker() as session:
    game = await session.scalar(select(Game).where(Game.id == game_id))
    positions = <load GamePosition ordered by ply>
# session closed
for pos in positions:
    cp, mate = _post_move_eval(pos_eval, pos.ply)   # OVERWRITES pos.eval_cp/eval_mate
    pos.eval_cp, pos.eval_mate = cp, mate
flaw_result = classify_game_flaws(game, positions)
if "reason" in flaw_result:
    return <empty>
```

This overlay step **unconditionally overwrites** `pos.eval_cp`/`pos.eval_mate` for every
position — including setting them to `None` where `pos_eval` has no entry. That's correct
here because at this pipeline stage the DB genuinely has NULL evals for engine games (the
batched write hasn't run yet), so overwriting is a required fill, not a destructive
overwrite.

**`_flaw_engine_plies` (L901) is different by necessity, not oversight:** it runs
**before** the engine gather, on `is_lichess_eval_game=True` games only, where
`game_positions.eval_cp/eval_mate` in the DB **already hold the real lichess %eval** (no
engine pass will ever fill them — lichess games keep their %eval permanently, D-116-04).
It calls `classify_game_flaws(game, positions)` directly on the DB-loaded positions **with
no overlay step at all**. If the unified helper applied the 3-site overlay unconditionally
here, it would overwrite every lichess-stored `eval_cp`/`eval_mate` with `None` (since
`pos_eval` would be built from empty `dedup_map={}`/`engine_result_map={}` at this
pre-gather point) and `classify_game_flaws` would see an all-NULL game and return
`GameNotAnalyzed` for every lichess game — this is the exact regression Phase 117's
post-deploy sanity check caught (see `_flaw_engine_plies`'s own docstring: "0% flaw-PV
coverage for analyzed lichess games").

**Recommendation for the planner:** design the unified preamble as `_classify_with_overlay
(game_id, positions_loader, *, overlay: bool, pos_eval=None) -> FlawResult | None`, where
`overlay=False` is what `_flaw_engine_plies` passes (skip the mutation loop entirely, use
DB-stored evals as-is) and `overlay=True` is what the other 3 sites pass. Do not try to
make `_flaw_engine_plies`'s call collapse into "pass an empty pos_eval" — that changes
behavior (`_post_move_eval({}, ply)` returns `(None, None)` unconditionally, which is
exactly the bug above). The four call sites still diverge downstream of the shared
preamble (what each does with `flaw_result` — pre-gather ply-set extraction vs. PV-target
detection vs. continuation-blob assembly vs. sentinel-line derivation stays separate);
R4's unification scope is genuinely just the "load + optionally overlay + classify" block,
not the whole function body.

**`engine_result_map` / `flaw_pv_blobs` threading (load-bearing, confirmed):**
`_classify_and_fill_oracle` (L705) builds `pv_by_ply` from `engine_result_map` (line
775–777) specifically because the freshly-computed PVs are "NOT yet written to
`game_positions` at this point" — the batched PV UPDATE (`_batch_update_pv_rows`) runs
*after* classify. This is the exact mechanism 260618-aiq depends on for live tactic
tagging. Any refactor of the preamble helper must keep passing `pv_by_ply`/`flaw_pv_blobs`
through unchanged into `classify_game_flaws`.

## R3 — Diff/Upsert (WRITE-03, the medium-risk item)

### Current delete-then-insert flow (`_classify_and_fill_oracle`, L705–898)

1. Load `Game` + ordered `GamePosition` rows.
2. Build `pv_by_ply` overlay from `engine_result_map` (live-tagging fix, see above).
3. `classify_game_flaws(...)` → `list[FlawRecord]` (M+B only, both players, D-06).
4. `delete_flaws_for_game(session, game_id, user_id)` — **unconditional full delete**.
5. `bulk_insert_game_flaws(session, rows)` where `rows = [flaw_record_to_row(...) for
   flaw in flaw_list]` — `flaw_record_to_row` (in `app/repositories/game_flaws_repository.py`
   L42–129) **never sets** `allowed_pv_lines`/`missed_pv_lines`/8-tactic-column values from
   any "preserve" source — those keys are entirely absent from every insert row's dict, so
   they land at the SQLAlchemy column default = **true SQL `NULL`** (verified: the JSONB
   columns are `deferred=True`, `nullable=True`, with no server default).
6. Two `count_game_severities` calls → oracle count `UPDATE games`.
7. Flaw-PV write for ply N / N+1 via `_batch_update_pv_rows` (best-effort, individually
   fault-tolerant — not part of the fail-closed contract).

**`_snapshot_preserved_flaw_blobs`/`_restore_preserved_flaw_blobs` (`eval_remote.py`
L961–1057)** wrap steps 4–5 from the **caller's** side (`_apply_atomic_submit` only —
`_full_drain_tick` does NOT snapshot/restore, because the in-process drain tick always
processes a game start-to-finish in one pass with no incremental retry concept; only the
atomic-submit path has the "worker re-submits a subset of plies" retry semantics SEED-076
introduced):
- Snapshot: `SELECT ply, allowed_pv_lines, missed_pv_lines, 8×tactic_cols WHERE
  allowed_pv_lines IS NOT NULL` — captures only already-blobbed flaws.
- Restore: filter the snapshot to `ply NOT IN freshly_blobbed AND ply IN
  <plies that survived classify's delete-then-insert>` (the FLAWCHESS-8D fix — the
  `existing_plies` intersection at L1040–1049), then `session.execute(update(GameFlaw),
  rows)` — SQLAlchemy's ORM bulk-update-by-PK.

### The 10 preserved columns — confirmed, and a ready-made single-source-of-truth exists

`[VERIFIED: codebase]` — `app/repositories/game_flaws_repository.py` L154–163 already
defines:
```python
TACTIC_TAG_COLUMNS: tuple[str, ...] = (
    "allowed_tactic_motif", "allowed_tactic_piece", "allowed_tactic_confidence",
    "allowed_tactic_depth", "missed_tactic_motif", "missed_tactic_piece",
    "missed_tactic_confidence", "missed_tactic_depth",
)
```
used by `bulk_update_tactic_tags` (L166) and `retag_flaws.py`. **D-04's `FLAW_BLOB_COLUMNS`
is a 2-line extension**, not new design: `FLAW_BLOB_COLUMNS: tuple[str, ...] =
("allowed_pv_lines", "missed_pv_lines") + TACTIC_TAG_COLUMNS`, defined once in
`game_flaws_repository.py`, imported by both the (deleted) snapshot logic and the new
diff/upsert's column-partitioning code. This directly satisfies D-04's "future 11th column
cannot be silently nulled" goal — add the column name to `TACTIC_TAG_COLUMNS` or
`FLAW_BLOB_COLUMNS` and every consumer (retag script, diff/upsert preserve branch) picks it
up.

Today `_snapshot_preserved_flaw_blobs` and `_restore_preserved_flaw_blobs` each hand-list
all 10 column names independently (verified — no shared constant used by either). This is
exactly the drift risk D-04 flags.

### Critical implementation pitfall: JSONB `NULL` vs. asyncpg `None` (project-documented landmine)

The user's own memory file `project_asyncpg_jsonb_null_vs_sql_null` states: *"passing
Python `None` to a JSONB column writes `null::jsonb` (not SQL `NULL`), so `col IS NULL`
predicates/partial indexes skip it; OMIT the column to get true NULL via default."* This
directly threatens the most tempting single-statement implementation of the diff/upsert —
a `pg_insert(...).on_conflict_do_update(set_={"allowed_pv_lines":
sa.func.coalesce(excluded.allowed_pv_lines, GameFlaw.allowed_pv_lines), ...})` approach,
binding `None` for non-freshly-blobbed rows to mean "no new value, keep old" via `COALESCE`.
**This will NOT work as intended**: a bound `None` parameter for a JSONB column serializes
as JSON `null` (a real, non-NULL JSONB value) via asyncpg, so `COALESCE(EXCLUDED.col,
game_flaws.col)` would see a non-NULL `'null'::jsonb` in `EXCLUDED.col` and always pick it
— silently nulling every "preserve" row's blob on the very first upsert after this
refactor ships. This is precisely the class of regression FLAWCHESS-8D-adjacent bugs come
from, and it would NOT be caught by any test that only checks "value is falsy/empty" — it
requires an explicit `IS NULL` (not `= NULL` truthiness) assertion.

**Recommended design (avoids the pitfall by construction, reuses 3 existing patterns
already proven in this file):** a 4-way partition executed as separate statements inside
the same write_session transaction (T-117-11: same transaction, same atomicity guarantee
as today):

1. **Delete** — `delete_flaws_for_game`-style, but scoped to `existing_ply - desired_ply`
   (plies previously flagged as flaws, no longer are). This is the exact FLAWCHESS-8D case
   (D-02 scenario 3) — a clean per-ply `DELETE ... WHERE ply IN (...)`, never a bulk-update
   assertion that can raise `StaleDataError`.
2. **Insert new** — plies in `desired_ply - existing_ply`: build rows via
   `flaw_record_to_row` (unchanged), **omit** the 10 `FLAW_BLOB_COLUMNS` keys entirely from
   the dict when the ply is NOT in `freshly_blobbed` (→ true `NULL` via column default,
   the existing insert-time behavior), or include real `json.dumps`'d values when it IS
   freshly blobbed. Use `bulk_insert_game_flaws` (unchanged) or an equivalent.
3. **Update existing, freshly-blobbed** — `session.execute(update(GameFlaw), rows)` (ORM
   bulk-update-by-PK, same idiom as today's `_restore_preserved_flaw_blobs` /
   `bulk_update_tactic_tags`) setting **all** non-PK columns including the 10 blob columns
   with their fresh values — never binds `None` to a JSONB column here (only real
   `list[Any]` values or the `[]` D-06 sentinel, both non-NULL JSON).
4. **Update existing, not freshly-blobbed** — same ORM bulk-update-by-PK pattern, but the
   update dict **excludes `FLAW_BLOB_COLUMNS` entirely** (via `{k: v for k, v in row.items()
   if k not in FLAW_BLOB_COLUMNS}`) — SQLAlchemy's `update(Model), rows` only sets columns
   present in each row dict, so omitted columns are simply left untouched by the SQL
   `UPDATE ... SET`. This is preservation-by-omission, not preservation-by-`COALESCE`, and
   it sidesteps the JSONB-null landmine entirely because the column is never mentioned in
   the SET clause at all.

This design also naturally satisfies D-03's per-ply case table without a "snapshot before /
restore after" compensation step — the classify pass computes `flaw_list` once, the caller
partitions plies into the 4 buckets using `existing_plies` (a `SELECT ply FROM game_flaws
WHERE game_id=... AND user_id=...` before mutating) and `freshly_blobbed` (unchanged
signal, still `_run_multipv2_pass`-derived), and executes 1–4 SQL statements instead of
delete+insert+snapshot+restore (4 round-trips → up to 4, but a `Delete`/`Insert` on an
empty set is skippable, so the common "no holes, no new flaws" case does 1 statement, not
4).

**Fail-closed contract (WR-01) must be preserved:** per the existing docstring, errors in
`bulk_insert_game_flaws` and the oracle-count `UPDATE` **must propagate** so the whole
write_session transaction aborts and completion markers are never committed. The new
partitioned statements (delete / insert-new / update-fresh / update-preserve) inherit this
by construction — they're all inside the same transaction, no `try/except` wrapping any of
them, same as today (only the flaw-PV write via `_batch_update_pv_rows` stays
individually fault-tolerant, per current code at L886–898).

**Post-move off-by-one (D-117-02) is untouched by R3** — it lives entirely in
`_post_move_eval`/`_resolve_full_eval` (both outside `_classify_and_fill_oracle`'s scope)
and in the flaw-PV-write loop's `(flaw_ply_val, flaw_ply_val + 1)` pairing (L873–875),
which the new diff/upsert does not need to change.

## R3 — Golden-Snapshot Equivalence Test: Concrete Construction Plan

### Existing test infrastructure to reuse (do not rebuild from scratch)

`[VERIFIED: codebase]` — every one of the 7 D-02 scenarios **already has a passing test**
against current HEAD, scattered across two files. The golden-snapshot generator should
harvest these exact setups rather than invent new fixtures:

| D-02 Scenario | Existing test (file:line) | Reusable fixture helpers |
|---|---|---|
| 1. Fresh full submit | `tests/test_eval_worker_endpoints.py::test_atomic_submit_fills_cached_opening_hole_server_side` (~3681) and `TestAtomicSubmitEndpoint` generally | `_insert_game`, `_insert_game_positions`, `_atomic_request`, `_BLUNDER_SUBMIT_EVALS_142` |
| 2. Residual-hole retry (preserve blob) | `test_atomic_retry_preserves_existing_flaw_blobs_and_tags` (3807) | Same + manual `UPDATE GameFlaw` to simulate a prior blobbed state |
| 3. Borderline ply flips OUT of flaw | `test_atomic_retry_snapshotted_ply_no_longer_flaw_does_not_raise` (3895, FLAWCHESS-8D regression) | `_FLAT_SUBMIT_EVALS_142` (no-flaw eval set) vs `_BLUNDER_SUBMIT_EVALS_142` |
| 4. Borderline ply flips IN to flaw | Not explicitly named — **inverse** of scenario 3 (swap submit order: flat first, then blunder); needs a new test, trivial to derive from #3's pattern |
| 5. Entry-pass rows replaced by oracle pass | `tests/services/test_full_eval_drain.py::TestClassifyHook` (~1743) — "must REPLACE pre-existing entry-pass flaw rows" | `_insert_game`/`_insert_game_positions` + pre-seeded stale entry-pass `GameFlaw` rows |
| 6. Dedup-transplanted plies (no `[]` sentinel taint) | `test_atomic_submit_merges_cached_pv_into_flaw_line_not_sentineled` (4012, quick 260703-qgp) | `_insert_opening_cache_with_pv`, `_build_flaw_blob_lease_positions` |
| 7. `blobs_pending=True` suppression | `tests/services/test_full_eval_drain.py::TestLocalDrainBlobsPendingSuppression` (~1851) | `_patch_drain_for_tick_tests`, monkeypatched `_detect_tactic_for_flaw` |

Also relevant: `tests/services/test_flaws_service.py::test_blobs_pending_true_sentinel_
empty_blob_keeps_raw` (2854) and `test_sentinel_empty_blob_skips_gate_returns_kernel_
result` (2713) for the D-06 sentinel/gate interaction underlying scenarios 6–7.

### Recommended generator + fixture structure (mirrors an existing, CI-enforced pattern)

`[VERIFIED: codebase]` — the project already has the exact "commit the generator +
drift-check test" pattern D-01 asks for, just for a different domain:
`scripts/gen_global_percentile_cdf.py` + `tests/scripts/test_gen_global_percentile_cdf_
unchanged.py` (byte-identical SQL-string goldens in `tests/scripts/fixtures/
global_percentile_cdf/*.sql`, regenerated via a documented one-liner in the test module's
docstring, checked by a `test_fixture_directory_covers_all_in_scope_cells` completeness
guard). Model R3's golden fixture the same way, adapted for DB-round-trip output instead
of pure-function SQL strings:

1. **New script** `scripts/gen_write_path_golden.py` — for each of the 7 (+1 inverse)
   scenarios, spins up the SAME game+position+submit sequence as the existing tests above
   (import the shared builders, e.g. factor `_insert_game`/`_insert_game_positions`/
   `_atomic_request` out of `test_eval_worker_endpoints.py` into a small shared test-utils
   module if not already importable cross-file — check for import cycles between test
   files first), runs it against the **current** `_classify_and_fill_oracle` +
   snapshot/restore path, then dumps the resulting `game_flaws` rows (all columns,
   ordered by `ply`) to a committed JSON fixture — one file per scenario, e.g.
   `tests/fixtures/write_path_golden/scenario_2_residual_hole_retry.json`.
2. **New equivalence test** `tests/services/test_write_path_equivalence.py` —
   parametrized over the 8 scenario fixtures, runs the SAME setup through the **new**
   diff/upsert implementation, loads the golden JSON, and asserts the live `game_flaws`
   state matches the golden byte-for-byte (dict equality after JSON round-trip,
   which naturally handles the JSONB-list vs. `None` distinction — assert `is None`
   explicitly for blob columns expected NULL, not falsy-equality, to catch the exact
   JSONB-null pitfall above if it regresses).
3. **Completeness guard** — same idiom as `test_fixture_directory_covers_all_in_scope_
   cells`: assert the fixture directory has exactly one file per named scenario constant,
   so a future 9th scenario can't silently ship without a golden.
4. **Regeneration instructions** live in the script's module docstring (not a separate doc)
   per the existing convention, and the test's docstring cross-references it — "if you
   change classify/gate/gate-margin logic intentionally, regenerate via `uv run python -m
   scripts.gen_write_path_golden` and review the diff before committing."

**Sequencing implication for the plan:** generate the goldens **before** touching
`_classify_and_fill_oracle` (i.e., as a Wave 0 / first-task step, against the
pre-refactor code) — the whole point of D-01 is that the golden captures *current,
correct* (post-149, post-8D) behavior. If the goldens are generated after the diff/upsert
lands, the equivalence proof is circular.

## R7 — Module Split (WRITE-04, Claude's Discretion / D-05)

### The leak, quantified

`eval_remote.py` imports **21 private symbols + 3 constants** directly from
`eval_drain.py` (lines 81–107): `_EvalTarget`, `_FullPlyEvalTarget`, `_apply_eval_results`,
`_apply_full_eval_results`, `_assemble_flaw_blobs_from_submit`,
`_batch_update_flaw_pv_lines`, `_build_flaw_blob_lease_positions`,
`_claim_entry_eval_games`, `_classify_and_fill_oracle`, `_classify_and_insert_flaws`,
`_collect_eval_targets_from_db`, `_collect_full_ply_targets`,
`_derive_atomic_sentinel_lines`, `_fetch_dedup_evals`, `_load_pgns_for_games`,
`_mark_evals_completed`, `_mark_full_evals_completed`, `_mark_full_pv_completed`,
`_parse_token`, `_run_multipv2_pass`, `_signal_flaw_completion` + `MAX_EVAL_ATTEMPTS`,
`ENTRY_LEASE_BACKLOG_THRESHOLD`, `ENTRY_LEASE_BATCH_SIZE`, `ENTRY_LEASE_TTL_SECONDS`.

### Circular-import risk (concrete, must be designed around)

`[VERIFIED: codebase]` — `eval_drain.py` does **not** import from `eval_remote.py` (only
from `app.schemas.eval_remote`, the Pydantic schema module — a different, safe module).
`eval_queue_service.py` imports from neither. So today's dependency direction is clean:
`eval_remote.py` (router) → `eval_drain.py` (service). **If `app/services/eval_apply.py`
is created as a thin module that only *re-exports* `apply_full_eval` by importing the
underlying primitives (`_apply_full_eval_results`, `_classify_and_fill_oracle`,
`_run_multipv2_pass`, `apply_completion_decision`, etc.) FROM `eval_drain.py`, and
`eval_drain.py`'s own `_full_drain_tick` is then changed to call `eval_apply.
apply_full_eval(...)` instead of the local functions directly, that creates
`eval_drain.py → eval_apply.py → eval_drain.py`, a circular import.**

**Recommended resolution:** physically **move** (not re-export) the shared-write-path
primitives into `eval_apply.py` — `_apply_full_eval_results`, `_classify_and_fill_oracle`
(→ R3's new diff/upsert), `_run_multipv2_pass`, `_batch_update_flaw_pv_lines`,
`apply_completion_decision` (R1's new function), and the R4-unified classify-preamble
helper. `eval_drain.py` then **imports FROM** `eval_apply.py` for its `_full_drain_tick`
(full-lane orchestration stays in `eval_drain.py`; the write-path body it calls lives in
`eval_apply.py`), and `eval_remote.py` also imports FROM `eval_apply.py` — both are leaves
depending on the new shared module, no cycle. This matches D-05's own framing
("`app/services/eval_apply.py` exposing `apply_full_eval(...)`, consumed by BOTH
`_full_drain_tick` and the router") — the plan should make explicit that this requires
**moving**, not just wrapping, the underlying helpers.

### Entry-lane vs. full-lane vs. shared-write-path split (concrete boundary)

Based on the full symbol inventory (Symbol Re-Location table above), the natural 3-way
split of `eval_drain.py`'s current 3013 lines:

- **Entry lane** (import-time, no-shift, depth-15): `_EvalTarget`, `_TargetSpec`,
  `_collect_target_specs`, `_snapshot_boards`, `_collect_eval_targets_per_game`,
  `_collect_midgame_eval_targets`, `_collect_endgame_span_eval_targets`,
  `_split_into_contiguous_islands`, `_batch_update_entry_eval_rows`,
  `_apply_eval_results`, `_claim_entry_eval_games`, `_pick_pending_game_ids`,
  `_load_pgns_for_games`, `_mark_evals_completed`, `_collect_eval_targets_from_db`,
  `_classify_and_insert_flaws`. Consumed only by `entry_submit_eval` /
  `import_service.py`.
- **Full lane (orchestration only, post-split)**: `run_eval_drain`, `_full_drain_tick`
  (slimmed to call `eval_apply.apply_full_eval`), `run_full_eval_drain`,
  `resweep_holed_games`, `_any_active_import_or_entry_ply_pending`,
  `_upsert_opening_cache` (tick-scoped cache fill — arguably belongs with shared-write-path
  since `_apply_atomic_submit` doesn't currently call it; verify whether R3/R4's
  consolidation should extend cache-fill to the atomic path too, or explicitly flag it as
  an intentional lane difference — CONTEXT.md does not mention this, worth a planner
  decision point, not a silent addition).
- **Shared write path (→ `eval_apply.py`)**: `_FullPlyEvalTarget`, `_collect_full_ply_
  targets`, `_fetch_dedup_evals`, `_resolve_full_eval`, `_post_move_eval`,
  `_batch_update_best_move_rows`, `_batch_update_pv_rows`, `_batch_update_eval_rows`,
  `_apply_full_eval_results`, `_mark_full_evals_completed`, `_mark_full_pv_completed`,
  `_classify_and_fill_oracle` (R3 target), the R4-unified preamble, `_flaw_engine_plies`,
  `_build_flaw_multipv2_blobs`, `_derive_atomic_sentinel_lines`, `_batch_update_flaw_pv_
  lines`, `_run_multipv2_pass`, `_GameColorView`, `_signal_flaw_completion`,
  `apply_completion_decision` (new, R1), `_parse_token`, `_assemble_flaw_blobs_from_
  submit`, `_assemble_one_line_blob`.
- **Stays isolated (not touched by this phase)**: `_build_flaw_blob_lease_positions`,
  `_apply_flaw_blob_submit` (`eval_remote.py`) — the flaw-blob-only tier-4 lane is
  explicitly isolated from the live-submit path today ("D-04 isolation boundary" per its
  own docstring) and CONTEXT.md's out-of-scope list does not ask to touch it.

`_parse_token` is used both by `_apply_atomic_submit`'s tamper guard and by
`_assemble_flaw_blobs_from_submit`/`_build_flaw_blob_lease_positions` — it's a small pure
function (parses a `token` string into `(flaw_ply, line, k)`), safe to move to
`eval_apply.py` since both current importers already cross the `eval_drain.py`/
`eval_remote.py` boundary for it.

### Thin shim fallback

D-05 says "thin re-export shims only if a clean move is genuinely blocked — flag it, don't
default to leaving the leak." Given the circular-import analysis above shows a clean move
IS achievable (just requires physically relocating code, not merely re-exporting), the
planner should not need a shim. If time pressure forces a partial R7 (e.g., only
`apply_full_eval` extracted, not the full 3-way file split), that's an acceptable
descope **as long as it's flagged**, not silently landed as "R7 done."

## R5 — EnginePool Generic Method (WRITE-05)

Confirmed genuinely near-identical and safely parameterizable. All 3 private methods
(`_analyse` L464, `_analyse_with_pv` L515, `_analyse_multipv2` L573) share an **identical**
14-line acquire/timeout/restart/release skeleton:

```python
if not self._started: return None  # or (None, None) for _analyse
idx = await self._available.get()
try:
    protocol = self._protocols[idx]
    if protocol is None: return None  # or (None, None)
    try:
        result = await asyncio.wait_for(protocol.analyse(board, limit[, multipv=2]), timeout=timeout)
    except (asyncio.TimeoutError, chess.engine.EngineError, chess.engine.EngineTerminatedError):
        await self._restart_worker(idx)
        return None  # or (None, None)
    return result  # or _score_to_cp_mate(result) for _analyse
finally:
    self._available.put_nowait(idx)
```

The only genuine differences: (a) whether `multipv=2` is passed to `protocol.analyse()`,
(b) the failure-sentinel shape (`(None, None)` tuple vs. bare `None`), (c) whether
`_score_to_cp_mate()` post-processes inline or the caller does. **Recommended generic
method:** one `_acquire_and_analyse(board, limit, timeout, *, multipv: int | None = None)
-> chess.engine.InfoDict | list[chess.engine.InfoDict] | None`, parameterized purely on
`multipv`; `evaluate()`/`evaluate_nodes()` call it with `multipv=None` and apply
`_score_to_cp_mate()` on the returned scalar `InfoDict`; `evaluate_nodes_with_pv()` calls
it with `multipv=None` and extracts PV; `evaluate_nodes_multipv2()` calls it with
`multipv=2` and post-processes the returned `list[InfoDict]` (already does this — no
change needed there, since `evaluate_nodes_multipv2` already calls `_analyse_multipv2` and
post-processes). No subtle behavioral differences found beyond the three listed above —
low risk, purely mechanical.

## R6 — ES Lottery Parameterization (WRITE-06)

Confirmed genuinely parameterizable, but **the "one shared implementation" is really two
reusable building blocks used 5 times, not one flat function** — worth being explicit
about in the plan so the task isn't scoped as "merge into 1 function" when the natural
factoring is "extract a generic weighted-user-pick + generic weighted-game-pick, call them
from both tiers."

- **Tier-3** (`_claim_tier3_derived`, L277) is **3 SQL stages**: Step 1 (weighted user
  pick over needs-engine games, `RECENCY_HALF_LIFE_DAYS`/`WEIGHT_FLOOR`), Step 2 (weighted
  game pick for that user, `GAME_RECENCY_HALF_LIFE_DAYS`/`GAME_WEIGHT_FLOOR`/
  `GAME_TC_WEIGHTS`), and a **residual fallback** (same game-pick shape, different WHERE
  predicate — PV-backfill-only games instead of needs-engine games).
- **Tier-4** (`_claim_tier4_blob`, L489) is **2 SQL stages** only (no residual fallback):
  Stage 1 (weighted user pick over analyzed games with a NULL-blob flaw,
  `TIER4_USER_RECENCY_HALF_LIFE_DAYS`/`TIER4_USER_WEIGHT_FLOOR`), Stage 2 (weighted game
  pick, `TIER4_GAME_RECENCY_HALF_LIFE_DAYS`/`TIER4_GAME_WEIGHT_FLOOR`, anchored on
  `full_evals_completed_at` instead of tier-3's `played_at`).
- Both share the **exact same TC-multiplier CASE block** (`GAME_TC_WEIGHTS` —
  classical=8/rapid=4/blitz=2/bullet=1/other=0.5) and the same `-ln(random()) / weight`
  Efraimidis–Spirakis key shape, differing only in: the `WHERE`/`EXISTS` predicate, which
  recency column anchors the exponential decay, and which named half-life/floor constants
  apply.

**Recommended shared building blocks:** a generic `_es_weighted_user_pick(session, *,
candidate_exists_sql, recency_col_sql, tau_seconds, floor) -> int | None` and a generic
`_es_weighted_game_pick(session, *, game_where_sql, recency_col_sql, tau_seconds,
game_floor, tc_weights) -> int | None`, both parameterized purely via `sa.text` bound
params (never f-string interpolation — both existing functions already enforce this via
inline comments; preserve that discipline in the shared helper). `_claim_tier3_derived`
becomes: user-pick → game-pick → (game-pick again with a different WHERE for the residual
fallback). `_claim_tier4_blob` becomes: user-pick → game-pick. **No subtle correctness
differences found** beyond the documented parameter differences — this is a legitimate,
low-risk consolidation. Per D-06, if R3 balloons, deferring R6 to a follow-up quick task is
an acceptable descope **as long as it's flagged in the plan/verification**, not silently
dropped.

## Runtime State Inventory

This phase is a **structure-only refactor**, not a rename/rebrand/migration — no
runtime-state inventory is required per the trigger conditions (no string renames, no
schema changes, no data migration). Confirmed against CONTEXT.md ("no schema change") and
against the touched-files list (no Alembic migration files touched). Stating explicitly
per the protocol: **None — this phase changes only in-process Python code paths; no
database schema, no external service config, no OS-registered state, no secrets/env vars,
and no build artifacts are affected.**

## Common Pitfalls

### Pitfall 1: Treating the R4 unification as byte-identical across all 4 sites
**What goes wrong:** naively merging `_flaw_engine_plies`'s preamble into the same helper
as the other 3 sites, applying the overlay unconditionally.
**Why it happens:** the 3 "big" sites really are byte-identical, making it tempting to
assume the 4th matches too; CONTEXT.md's phrasing ("4 repeated call sites") reads as if
all 4 are the same shape.
**How to avoid:** the unified helper must take an `overlay: bool` parameter (or
equivalent conditional), defaulting to skip-overlay only for the lichess-pre-gather site.
**Warning signs:** a regression test asserting lichess-eval-game flaw PV coverage (mirrors
the Phase 117 post-deploy sanity check that caught this originally) should be part of the
plan's verification, not just "existing tests pass" — the existing tests may not exercise
this path if `_flaw_engine_plies` isn't separately covered (check before assuming).

### Pitfall 2: Implementing R3's diff/upsert as a single `ON CONFLICT DO UPDATE ...
COALESCE(...)` statement
**What goes wrong:** binding Python `None` for "no fresh blob this submit" into a JSONB
column parameter serializes as `null::jsonb` (a real, non-NULL value) via asyncpg, not SQL
`NULL` — `COALESCE(EXCLUDED.col, existing.col)` then always picks the JSON-null, silently
wiping every preserved blob on the first upsert.
**Why it happens:** `COALESCE`-based upsert is the idiomatic single-statement pattern for
"insert or preserve," and it's exactly wrong for JSONB columns given asyncpg's `None`
handling (documented separately as a project landmine, `project_asyncpg_jsonb_null_vs_
sql_null`, discovered the hard way once already).
**How to avoid:** use the 4-way partition (delete / insert-new / update-fresh-blob /
update-preserve-by-omission) described in the R3 section — preservation happens by
*omitting* the column from the `UPDATE ... SET` clause entirely, never by relying on
`NULL`-vs-JSON-`null` comparison semantics.
**Warning signs:** any test asserting blob preservation via `assert row.allowed_pv_lines
== preserved_value` (truthy-equality) instead of also asserting `IS NOT NULL`/checking the
raw SQL type would NOT catch this bug — the golden-snapshot equivalence test must assert
exact equality including `None`-ness, not just "value present."

### Pitfall 3: Circular import between `eval_apply.py` and `eval_drain.py`
**What goes wrong:** creating `eval_apply.py` as a re-export layer that imports FROM
`eval_drain.py`, while also changing `eval_drain.py`'s `_full_drain_tick` to import FROM
`eval_apply.py` — a straightforward cycle that Python will raise `ImportError` on at
startup (not a subtle runtime bug — it fails loudly, but potentially wastes a full
plan-implement-test cycle if not designed around up front).
**Why it happens:** "extract a function into a new module, but keep the old module calling
the same helper" is the most natural first attempt when doing a mechanical extraction.
**How to avoid:** physically move the shared-write-path primitives (see R7 section) into
`eval_apply.py`; `eval_drain.py` becomes a pure importer of `eval_apply.py` for full-lane
orchestration, never the reverse.
**Warning signs:** `ty check` / `ruff check` will surface an import error immediately —
this pitfall is more about wasted implementation-order planning than a silent bug, but the
plan's task ordering should sequence "move the functions" before "update both call sites"
to avoid a broken intermediate commit.

### Pitfall 4: Forgetting `_upsert_opening_cache` is drain-tick-only
**What goes wrong:** assuming the shared-write-path extraction covers everything both
`_full_drain_tick` and `_apply_atomic_submit` currently do — `_upsert_opening_cache` (cache
population for the dedup optimization) is called by `_full_drain_tick` but **not** by
`_apply_atomic_submit` today. If R7's `apply_full_eval` unconditionally calls it, that's a
**behavior change** (opening cache gets populated from atomic-submit workers too — likely
harmless/beneficial, but it IS new behavior, and CONTEXT.md/REQUIREMENTS.md both say "no
behavior change").
**Why it happens:** natural to assume "shared write path" means literally everything both
callers do overlaps.
**How to avoid:** the planner should explicitly decide (and record as a decision, not
silently include) whether `apply_full_eval` gains an `update_opening_cache: bool`
parameter defaulting to preserve each caller's current behavior, or whether extending
cache-fill to the atomic path is an intentional (flagged) scope addition.
**Warning signs:** a diff to `_apply_atomic_submit`'s behavior showing a new
`opening_position_eval` write that wasn't there before, not caught by the golden-snapshot
test (which only asserts `game_flaws`, not `opening_position_eval` state) — if this
matters, add an assertion for it too.

## Code Examples

### Existing single-source-of-truth column-list pattern (model for `FLAW_BLOB_COLUMNS`)

```python
# Source: app/repositories/game_flaws_repository.py:154-163 (current HEAD)
TACTIC_TAG_COLUMNS: tuple[str, ...] = (
    "allowed_tactic_motif",
    "allowed_tactic_piece",
    "allowed_tactic_confidence",
    "allowed_tactic_depth",
    "missed_tactic_motif",
    "missed_tactic_piece",
    "missed_tactic_confidence",
    "missed_tactic_depth",
)

async def bulk_update_tactic_tags(session: AsyncSession, updates: list[dict[str, Any]]) -> None:
    """Update ONLY the 8 tactic-tag columns for existing game_flaws rows."""
    if not updates:
        return
    await session.execute(update(GameFlaw), updates)
```

### Existing raw-SQL JSONB write pattern (safe, never binds `None` to a JSONB column)

```python
# Source: app/services/eval_drain.py:1413-1444 (current HEAD) — _batch_update_flaw_pv_lines
# json.dumps() always produces a real JSON value (even for []), never Python None,
# so this is safe from the asyncpg JSONB-null pitfall by construction.
params[f"allowed_{i}"] = json.dumps(allowed_blobs)
params[f"missed_{i}"] = json.dumps(missed_blobs)
values_parts.append(f"(CAST(:ply_{i} AS smallint), CAST(:allowed_{i} AS jsonb), CAST(:missed_{i} AS jsonb))")
```

### Existing ORM bulk-update-by-PK pattern (model for R3's "update existing" branches)

```python
# Source: app/routers/eval_remote.py:1050-1057 (current HEAD) — _restore_preserved_flaw_blobs
rows = [
    {"user_id": user_id, "game_id": game_id, "ply": ply, **cols}
    for ply, cols in snapshot.items()
    if ply not in freshly_blobbed and ply in existing_plies
]
if not rows:
    return
await session.execute(update(GameFlaw), rows)
```

### Existing "commit the generator + drift-check test" pattern (model for D-01's golden)

```python
# Source: tests/scripts/test_gen_global_percentile_cdf_unchanged.py (current HEAD)
@pytest.mark.parametrize(("metric_id", "tc"), [...])
def test_build_per_user_with_anchor_query_byte_identical_after_refactor(metric_id, tc) -> None:
    expected = _load_golden(metric_id, tc)
    actual = _build_per_user_with_anchor_query(metric_id, tc, snapshot_date=_SNAPSHOT_DATE)
    assert actual == expected, "...regenerate via the snippet in the module docstring..."

def test_fixture_directory_covers_all_in_scope_cells() -> None:
    fixture_names = {p.stem for p in _FIXTURE_DIR.glob("*.sql")}
    in_scope = {f"{m}__{tc}" for m in IN_SCOPE_METRICS for tc in ALL_TIME_CONTROLS}
    assert not (in_scope - fixture_names), "Missing golden fixtures"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Gen-1 `/lease`+`/submit` + `_apply_submit` (3rd completion-decision copy) | Deleted entirely | Phase 149 (`53ea905e`, 2026-07-03/04) | R1 now consolidates **2** live copies, not 3 — correct CONTEXT.md/REQUIREMENTS.md wording when planning/verifying, do not silently "discover" a 3rd copy that no longer exists |
| Tier-4 top-50 recency-window cutoff (`TIER4_RECENCY_WINDOW`) | Two-stage ES weighted lottery (`_claim_tier4_blob`) | quick 260701-lw4 | Confirms tier-4's ES lottery is genuinely the SAME shape as tier-3's — good precedent for R6, not a coincidence |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The inline `from app.models.eval_jobs import EvalJob` import inside `_full_drain_tick` (vs. `eval_remote.py`'s module-level import) is a historical artifact, not a load-bearing circular-import guard | R1 | Low — worst case, moving it to module scope in the new `apply_completion_decision()` surfaces an import error immediately (loud, not silent); `ty`/`ruff` would catch it before merge |
| A2 | Extending `_upsert_opening_cache` to run on the atomic-submit path (if R7's `apply_full_eval` unifies orchestration) is out of scope unless the planner explicitly opts in | R7 Pitfall 4 | Medium — if silently included, it's a real (probably benign) behavior change that contradicts the phase's "no behavior change" contract; should be a flagged decision, not an accident |

**All claims above are `[VERIFIED: codebase]`** via direct file reads at the current HEAD
(commit `f6ed49e9`) — no `[ASSUMED]`-tier claims required external verification for this
phase, since the entire research task is "read and re-locate existing code," not "learn a
new library or pattern." The two items above are flagged as assumptions about *intent*
(why a design choice was made / what scope boundary the planner should draw), not about
verifiable facts.

## Open Questions

1. **Should `_full_drain_tick`'s and `_apply_atomic_submit`'s Path-C warning mechanisms
   (Sentry `capture_message` vs. `logger.warning`) be unified, or kept deliberately
   different?**
   - What we know: `eval_drain.py`'s own comment explains the `logger.warning` choice was
     a deliberate fix for FLAWCHESS-5V (an earlier per-tick Sentry call burned the error
     quota for an expected outcome).
   - What's unclear: whether `_apply_atomic_submit`'s Sentry-capture-message on the same
     Path C branch has the same quota-burn risk (remote-worker Path-C events may be rarer
     than in-process-drain ones, or may not — not measured here).
   - Recommendation: parameterize `apply_completion_decision()` with an injectable
     `on_path_c(game_id, hole_count, attempts)` callback so each caller keeps its current
     reporting mechanism; do not force a single choice without confirming relative event
     volume first (a prod Sentry query, not in this research's scope).

2. **Does the golden-snapshot generator need its own isolated test-DB session, or can it
   reuse the per-run-DB-isolation `test_engine` fixture from `tests/conftest.py`?**
   - What we know: `tests/conftest.py` already provides fully isolated per-pytest-run
     Postgres clones (auto-refreshing template) — the standard fixture stack
     (`eval_worker_session_maker`/`full_drain_session_maker` used by the existing
     scenario tests) already builds on this.
   - What's unclear: whether the golden-*generation* script (a one-off `uv run python -m
     scripts.gen_write_path_golden` invocation, not a pytest run) should spin up its own
     ad-hoc DB connection against the dev DB, or whether it should be structured as a
     pytest-invoked "regen mode" (like some `gen_*.py` scripts support) so it reuses the
     same isolated-DB machinery.
   - Recommendation: prefer a pytest-invoked regen path (mirrors `test_gen_global_
     percentile_cdf_unchanged.py`'s model where the regen snippet is itself a small
     script using the production functions, run outside pytest against no DB — but R3's
     golden requires a DB, unlike that SQL-string example) — the planner should decide
     whether a `--regen` pytest marker/fixture or a standalone `scripts/gen_write_path_
     golden.py` (using `async_session_maker` against the local dev DB, per CLAUDE.md's "no
     dev DB reset in plans" rule — this must NOT require `bin/reset_db.sh`) is cleaner.
     Either way, the generator must not depend on or mutate production data.

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest (async, `pytest-asyncio`), 3188+ backend tests at last full-suite run (Phase 149) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) — no new config needed |
| Quick run command | `uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py tests/services/test_eval_drain.py tests/services/test_engine.py tests/services/test_eval_queue.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| WRITE-01 | `apply_completion_decision()` produces identical Path A/B/C outcomes to both current inline copies | unit + existing-suite regression | `uv run pytest tests/services/test_full_eval_drain.py::TestHoleAwareCompletionGate tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint -x` | ✅ (existing tests exercise both call sites already; extend, don't replace) |
| WRITE-02 | Unified classify preamble preserves lichess-eval-game flaw-PV coverage (the `_flaw_engine_plies` non-overlay case) AND the 3 overlay-based sites | unit + regression | `uv run pytest tests/services/test_full_eval_drain.py::TestFlawPv tests/services/test_full_eval_drain.py::TestSeed049GameEndingPly -x` | ✅ existing; may need a **new** targeted test asserting lichess flaw-PV coverage survives the merge (Pitfall 1) — ❌ Wave 0 if not already covered, verify first |
| WRITE-03 | Diff/upsert reproduces delete-then-insert output across all 7+1 D-02 scenarios | golden-snapshot equivalence test (new) | `uv run pytest tests/services/test_write_path_equivalence.py -x` | ❌ Wave 0 — new file, but scenario setups are lifted from existing tests (see table above) |
| WRITE-04 | Router no longer imports private `eval_drain.py` symbols; `eval_apply.py` exposes `apply_full_eval` | static check + existing-suite regression | `uv run ruff check app/routers/eval_remote.py app/services/eval_apply.py && uv run ty check app/ tests/ && uv run pytest -n auto -x` | ✅ existing suite is the regression net; the "no private import" check is a `grep`/ruff-import-lint check, not a new test file |
| WRITE-05 | `EnginePool` generic method preserves the 3 distinct public method contracts (return shapes, failure sentinels) | unit | `uv run pytest tests/services/test_engine.py -x` | ✅ (`test_single_legal_move_sets_second_sentinel` and siblings already assert per-method contracts — extend with a generic-method-level test if warranted) |
| WRITE-06 | Parameterized ES lottery produces the same query shape/behavior as today's tier-3/tier-4 functions | unit + existing-suite regression | `uv run pytest tests/services/test_eval_queue.py -x` | ✅ existing |

### Sampling Rate
- **Per task commit:** the quick run command above (targeted eval-write-path suites)
- **Per wave merge:** `uv run pytest -n auto -x` (full suite — this phase touches
  high-fan-out shared code, a targeted subset is not sufficient at wave boundaries)
- **Phase gate:** full pre-merge gate per CLAUDE.md (`ruff format`, `ruff check --fix`,
  `ty check`, `pytest -n auto -x`, frontend lint+test as a no-op since this is
  backend-only) before the single local squash-merge to `main` (per D-07 — no incremental
  prod deploys between R1/R4/R3/R7 steps)

### Wave 0 Gaps
- [ ] `tests/services/test_write_path_equivalence.py` — new file, covers WRITE-03 (the
  golden-snapshot equivalence proof across 8 scenarios: 7 from D-02 + the inverse of
  scenario 3 for scenario 4)
- [ ] `scripts/gen_write_path_golden.py` — new generator script (Wave 0, run against
  **pre-refactor** code to capture correct-as-of-today behavior, per D-01's sequencing
  requirement)
- [ ] `tests/fixtures/write_path_golden/*.json` — 8 committed golden fixtures (generated,
  not hand-written)
- [ ] A targeted regression test asserting `_flaw_engine_plies`'s non-overlay preamble
  variant survives the WRITE-02 unification (verify whether existing tests already cover
  this before assuming a gap — the lichess-eval-game flaw-PV-coverage assertion may already
  exist somewhere in `TestFlawPv`; confirm during planning, not blind-add)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | No | Unchanged — `require_operator_token` (X-Operator-Token, constant-time compare) stays as-is, not touched by this refactor |
| V3 Session Management | No | No session/auth surface changed |
| V4 Access Control | No | No authorization boundary changed (T-147-03 "server never trusts worker's local hint-classify" boundary is preserved — the diff/upsert still re-derives `flaw_result` from the server's own `classify_game_flaws`, never from worker-submitted flaw claims) |
| V5 Input Validation | No | No new external input surface; `_parse_token`'s tamper guard (T-147-02) is relocated, not changed |
| V6 Cryptography | No | Not applicable |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Worker-submitted flaw/blob data trusted as authoritative | Tampering | Already mitigated (T-147-03): server re-runs `classify_game_flaws` on its own `game_positions`; the R3 refactor must preserve this — the diff/upsert computes `flaw_list` from the server's classify call, never from anything the worker submitted as a "this is a flaw" claim |
| Late/expired-lease submit corrupting an unrelated job's `eval_jobs` row | Tampering | Already mitigated: `WHERE status = 'leased'` guard on the `eval_jobs` UPDATE inside the completion decision — R1's `apply_completion_decision()` must keep this guard verbatim |
| Foreign/out-of-range blob token accepted | Tampering/Spoofing | Already mitigated (T-147-02, T-145-09): `_parse_token` + in-range ply check before any write; R7's relocation of `_parse_token` must not change its call-site ordering (validate-before-write) |

This phase introduces no new external attack surface (no new endpoints, no new user
input parsing) — the security domain is "preserve existing mitigations across the
refactor," verified structurally by the equivalence test (R3) and the existing-suite
regression run (R1/R4/R5/R6/R7), not by new threat modeling.

## Sources

### Primary (HIGH confidence — direct codebase inspection at current HEAD)
- `app/services/eval_drain.py` (3013 lines) — full symbol inventory, `_classify_and_fill_
  oracle`, `_full_drain_tick`, R4 preamble sites
- `app/routers/eval_remote.py` (1401 lines) — `_apply_atomic_submit`,
  `_snapshot_preserved_flaw_blobs`/`_restore_preserved_flaw_blobs`, private-import block
- `app/services/engine.py` (647 lines) — `EnginePool` 3 acquire/analyse/restart copies
- `app/services/eval_queue_service.py` (864 lines) — `_claim_tier3_derived`/
  `_claim_tier4_blob`
- `app/repositories/game_flaws_repository.py` — `TACTIC_TAG_COLUMNS`,
  `bulk_insert_game_flaws`, `bulk_update_tactic_tags`, `delete_flaws_for_game`,
  `flaw_record_to_row`
- `app/services/flaws_service.py` — `classify_game_flaws`/`_classify_tactic_gated`
  signatures (`blobs_pending` threading)
- `tests/test_eval_worker_endpoints.py` (4162 lines) — existing D-02 scenario test
  coverage (scenarios 1, 2, 3, 5, 6)
- `tests/services/test_full_eval_drain.py` (3544 lines) — existing D-02 scenario test
  coverage (scenario 5, 7), `TestHoleAwareCompletionGate`
- `tests/scripts/test_gen_global_percentile_cdf_unchanged.py` — the existing
  "generator + committed golden + drift test" pattern this phase's D-01 should mirror
- `git log` — confirmed Phase 149 (`53ea905e`) deleted the Gen-1 `_apply_submit`
  completion-decision copy

### Secondary (MEDIUM confidence)
- `.planning/phases/150-consolidate-write-path/150-CONTEXT.md` — user decisions (D-01
  through D-07), cross-checked against current code; one factual drift found and
  documented (R1's "3 copies" claim)
- `.planning/REQUIREMENTS.md` — WRITE-01…06 text, same drift noted
- User auto-memory `project_asyncpg_jsonb_null_vs_sql_null.md` — the JSONB-null pitfall
  this phase's R3 design must avoid

### Tertiary (LOW confidence)
- None — this phase required no external/web research; all findings are direct codebase
  verification.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new libraries; existing stack (FastAPI/SQLAlchemy async/
  asyncpg/python-chess) unchanged
- Architecture: HIGH — every symbol location, call graph, and import direction verified
  by direct grep/read against current HEAD
- Pitfalls: HIGH — the JSONB-null pitfall is drawn from the project's own documented
  incident history, not speculation; the R4 non-overlay divergence and R7 circular-import
  risk are both derived from direct code reading, not inference

**Research date:** 2026-07-04
**Valid until:** Until the next commit touches `eval_drain.py`, `eval_remote.py`,
`engine.py`, or `eval_queue_service.py` — line numbers will drift immediately on any
change to these files (as they already have once, post-Phase-149). Re-verify symbol
locations at plan time if any time has passed since this research.

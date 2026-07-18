---
phase: 177-worker-side-multipv2-gem-candidates
reviewed: 2026-07-17T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - app/schemas/eval_remote.py
  - app/routers/eval_remote.py
  - app/services/eval_apply.py
  - app/services/eval_drain.py
  - app/core/config.py
  - scripts/remote_eval_worker.py
  - tests/test_eval_worker_endpoints.py
  - tests/services/test_eval_apply.py
  - tests/services/test_full_eval_drain.py
  - tests/test_remote_eval_worker.py
findings:
  critical: 1
  warning: 1
  info: 3
  total: 5
status: issues
---

# Phase 177: Code Review Report

**Reviewed:** 2026-07-17
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 177 shifts the gem-candidate MultiPV-2 runner-up search from the server engine
pool to the remote worker fleet (protocol v2), adds an isolated tier-4b
`/bestmove-lease` + `/bestmove-submit` pair, gives the server drain a tier-aware
minimal path, and upgrades `scripts/remote_eval_worker.py` with a rung-5 ladder entry.
The bulk of the implementation is careful and well-documented: the inverse post-move
shift reconstruction (`_eval_of_position_map`) is correct including the `ply=0` edge,
session discipline is respected everywhere I traced (no `asyncio.gather` runs inside an
open `AsyncSession`), the `worker_schema_version` gate is genuinely the first statement
in `atomic_lease_eval_game` and applies uniformly to both `scope=explicit` and
`scope=idle`, and the tamper-guard convention (422 on out-of-range, silent drop on
in-range-but-non-candidate) is applied consistently across `second_best`, `blob_nodes`,
and the new `bestmove-submit` evals.

However, I found one **BLOCKER**: the new `/bestmove-submit` wire endpoint
(`_apply_bestmove_submit`) never checks the Phase 176 D-01 `maia_available` guardrail
before stamping `best_moves_completed_at` — the exact bug Plan 03 discovered and fixed
for the sibling in-process drain path (`_tier4b_minimal_drain_tick`, via an explicit
"Rule 2 auto-fix" called out in 177-03-SUMMARY.md) was never applied to the wire
endpoint added one plan earlier. This is provable directly from the existing test suite:
`test_bestmove_submit_minimal_write_no_reclassify` never touches `maia_engine._session`
yet asserts the stamp fires — the guard the test would need to fail against simply
isn't there.

I also found one **WARNING**: the new rung-5 worker handler
(`_eval_bestmove_positions`) does not filter out engine-failure results the way its
sibling `_eval_targeted_second_best` does in the same file, so a single transient
Stockfish failure on the worker silently and permanently forfeits that gem candidate
instead of falling through to the server's Pitfall-1 fallback.

Three INFO-level observations (code-duplication risk, a fragile pre-existing
`game_length` pattern reused into two new call sites, and a speculative note on the
known post-deploy 422 sighting) round out the review.

## Critical Issues

### CR-01: `/bestmove-submit` stamps `best_moves_completed_at` without the Phase 176 D-01 `maia_available` guardrail

**File:** `app/services/eval_apply.py:2256-2267` (`_apply_bestmove_submit`)
**Issue:**

`_apply_bestmove_submit` writes its result unconditionally:

```python
async with async_session_maker() as write_session:
    await _upsert_best_move_rows(write_session, best_move_rows)
    await _mark_best_moves_completed(write_session, game_id)   # <-- unconditional
    await upsert_worker_heartbeat(...)
    await write_session.commit()
```

Compare this to the two other places that stamp `best_moves_completed_at` in this
phase's own code:

- `apply_completion_decision` (the fresh-lane path, pre-existing) gates the stamp on
  `maia_available` (`app/services/eval_apply.py:781,798`).
- `_tier4b_minimal_drain_tick` (Plan 03, `app/services/eval_drain.py:809-816`) computes
  `maia_available = maia_engine.is_maia_available()` and gates the stamp on it — and
  177-03-SUMMARY.md documents this explicitly as a **Rule 2 auto-fix**: "the new tier
  branch bypasses `apply_completion_decision` entirely, so without an explicit
  `maia_engine.is_maia_available()` check ... a Maia-absent backend would incorrectly
  stamp `best_moves_completed_at` with zero candidate rows written."

`_apply_bestmove_submit` (Plan 02) bypasses `apply_completion_decision` in exactly the
same way — it has its own write session and never calls it — but was never given the
same fix. `_build_best_move_candidates` itself has no Maia gate either (it just returns
`[]` when `score_move` returns `None`, indistinguishable at the row-count level from "no
candidates found"), so nothing downstream catches this.

**Effect:** on a backend where `maia_engine.is_maia_available()` is `False` (no
`onnxruntime`, model not loaded, or any other misconfiguration the Phase 176 guardrail
was explicitly written to protect against), every `POST /bestmove-submit` writes **zero**
`game_best_moves` rows and still stamps `best_moves_completed_at`. Since the tier-4b
lottery predicate is `best_moves_completed_at IS NULL`, the game is then **permanently**
excluded from the tier-4b lottery with no gem/great data and no retry path — there is no
resweep/backfill script anywhere in `scripts/` that resets this column
(`grep -rl best_moves_completed_at scripts/` returns only `remote_eval_worker.py`).

**Proof this is untested, not just theoretical:** `test_bestmove_submit_minimal_write_no_reclassify`
(`tests/test_eval_worker_endpoints.py:4917-4972`) monkeypatches `score_move` directly but
never touches `maia_engine._session`, then asserts `stamped is not None`. Its sibling
drain-path test, `test_maia_absent_never_stamps_best_moves_completed_at`
(`tests/services/test_full_eval_drain.py:2512-2578`), explicitly sets
`monkeypatch.setattr(maia_engine, "_session", None)` and asserts the OPPOSITE — proving
the drain path is correctly guarded and the wire endpoint is not. There is no
`test_bestmove_submit_*maia*` test anywhere in `tests/test_eval_worker_endpoints.py`.

**Fix:** mirror the drain-path fix — compute `maia_available` and gate the stamp on it:

```python
maia_available = maia_engine.is_maia_available()

async with async_session_maker() as write_session:
    await _upsert_best_move_rows(write_session, best_move_rows)
    if maia_available:
        await _mark_best_moves_completed(write_session, game_id)
    await upsert_worker_heartbeat(...)
    await write_session.commit()
```

(`maia_engine` is already imported in `app/services/eval_apply.py:75`.) Add a
`test_bestmove_submit_maia_absent_never_stamps` test mirroring the drain-path negative
assertion.

## Warnings

### WR-01: Rung-5 worker handler submits engine failures as real second-best data instead of dropping them

**File:** `scripts/remote_eval_worker.py:903-929` (`_eval_bestmove_positions`)
**Issue:** `_eval_bestmove_positions` (rung 5, tier-4b) does not filter out the
all-`None` 7-tuple `evaluate_nodes_multipv2` returns on an engine failure:

```python
async def _eval_bestmove_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    boards: list[chess.Board] = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
    return [
        {"ply": pos["ply"], "second_cp": r[4], "second_mate": r[5], "second_uci": r[6]}
        for pos, r in zip(positions, results)
    ]
```

Its sibling in the same file, `_eval_targeted_second_best` (line 339), explicitly drops
a failed search so the ply is *absent* from what gets submitted:

```python
for pos, r in zip(candidates, results):
    if r[0] is None and r[1] is None:
        continue  # engine failure (all-None 7-tuple) — drop, server fallback covers it
    second_best.append(...)
```

`_eval_bestmove_positions` has no such filter — every leased ply is unconditionally
included, even a failed one with `second_cp=None, second_mate=None, second_uci=None`.

**Effect:** on the server, `_apply_bestmove_submit` builds
`second_best_map = {e.ply: (e.second_cp, e.second_mate, e.second_uci) for e in body.evals}`
(`app/services/eval_apply.py:2248-2250`), which is keyed on presence, not on whether the
values are non-`None`. In `_build_best_move_candidates`, `second = second_best_map.get(t.ply)`
is a non-`None` tuple even for a failed search, so the Pitfall-1 fallback path (`if t.ply
not in second_best_map`) never fires for that ply — the server never re-tries it. Instead
`(second_cp, second_mate) = (None, None)` flows into `passes_inaccuracy_gate`, which
returns `False` whenever either eval is `None` (`app/services/best_move_candidates.py:150-154`),
so the candidate is silently dropped. Combined with CR-01 (or even after CR-01 is fixed —
the game is still stamped complete after one pass on Path A), a single transient
Stockfish failure on the worker permanently forfeits that gem/great candidate instead of
falling through to the server's own designed safety net.

**Fix:** apply the same drop-on-failure filter used in `_eval_targeted_second_best`:

```python
async def _eval_bestmove_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    boards = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
    out: list[dict[str, object]] = []
    for pos, r in zip(positions, results):
        if r[0] is None and r[1] is None:
            continue  # engine failure — drop; server-side fallback covers it
        out.append({"ply": pos["ply"], "second_cp": r[4], "second_mate": r[5], "second_uci": r[6]})
    return out
```

## Info

### IN-01: Duplicated reconstruction logic across three near-identical write paths is what let CR-01 happen

**Files:** `app/services/eval_apply.py:2152-2269` (`_apply_bestmove_submit`),
`app/services/eval_drain.py:664-819` (`_tier4b_minimal_drain_tick`)

`_apply_bestmove_submit`, `_tier4b_minimal_drain_tick`, and (to a lesser extent)
`bestmove_lease`'s direct-stamp branch all re-derive `targets`/`engine_result_map` and
independently decide when to call `_mark_best_moves_completed`. 177-02-SUMMARY.md and
177-03-SUMMARY.md both note this is deliberate (so each call site can pass its own
`source=` label to `_build_best_move_candidates`), but CR-01 is a direct consequence:
the `maia_available` guard had to be manually re-added at each call site rather than
being enforced once in a shared write helper, and one site was missed. Consider a small
shared `_write_bestmove_result(session, game_id, best_move_rows) -> None` (or at minimum
a shared `_maia_gated_mark_best_moves_completed(session, game_id)` helper) that both
`_apply_bestmove_submit` and `_tier4b_minimal_drain_tick` call, so a future refactor of
this invariant can't silently drop it from one of the two sites again.

### IN-02: `game_length` computed as `len(targets)`/`sum(... not is_terminal)` is a count, not a range bound — fragile if `game_positions` rows are ever sparse

**Files:** `app/services/eval_apply.py:2221` (`_apply_bestmove_submit`), `app/routers/eval_remote.py:1153,1206` (`_apply_atomic_submit`, pre-existing pattern reused)

The tamper guards for `second_best`/`evals`/`blob_nodes` all check `0 <= ply < game_length`
where `game_length` is a **count** of `_FullPlyEvalTarget`s built from
`_collect_full_ply_targets`. That function only creates a target for a ply that has a
matching row in `game_positions_rows` (`ply_meta.get(ply) is not None`) — so if
`game_positions` ever has a gap for a mid-game ply (e.g. a partial/corrupted import), the
resulting `targets` list is shorter than the true ply count but its `.ply` values are
not contiguous from `0..len(targets)-1`. A legitimate candidate at a late ply could then
fail `ply < game_length` even though it was validly leased, producing a spurious 422
that looks identical to a real tamper attempt. This pattern pre-dates Phase 177
(`_apply_atomic_submit`'s `blob_nodes`/`second_best` guards use the same shape), and in
practice `game_positions` rows are written atomically at import time so gaps should not
occur — but Phase 177 reproduces the same fragile assumption into two brand-new call
sites (`_apply_bestmove_submit`, `_tier4b_minimal_drain_tick`) rather than switching to a
membership check (`ply in {t.ply for t in targets}`) or `max(t.ply for t in targets) + 1`,
either of which would be robust to a sparse target set. Not asking for a fix given the
established precedent, but flagging so a future incident isn't mis-diagnosed as an
attack.

### IN-03: Speculative note on the known post-deploy 422 (per reviewer request, not a code-change ask)

The prompt asked me to flag a plausible mechanism for the one observed `POST
/atomic-submit` 422 shortly after a v2 worker restart. I could not find a code path in
which a *single* worker's own self-consistent lease→submit round trip produces a
spurious out-of-range `ply` or malformed token — `_apply_atomic_submit`'s `game_length`
and the worker's `move_uci`/`ply` values are both derived from the identical
`_collect_full_ply_targets` walk over the same immutable `game_positions` row set, so
they should agree by construction for one worker's one cycle. The most plausible
mechanism given the codebase's own documented ~12%/h double-claim rate (mentioned in
177-05-PLAN.md's measurement checklist, D-08) is two workers concurrently processing the
same tier-3-derived `game_id` (which has no lease/TTL protection at all — only
tier-1/tier-2 `eval_jobs` claims are TTL-leased); if the restart caused the "old" worker
identity to resubmit stale state from a partially-completed cycle that raced a second,
faster submit for the same game, that would still need `game_positions`' row *set* to
have changed between the two reads to trigger `game_length` disagreement, which I
couldn't confirm happens anywhere in the current write paths (evals only update existing
rows' columns, never insert/delete rows). I'd suggest logging the rejected token/ply and
`game_id` on the 422 path (currently `detail=f"Malformed token: {node.token!r}"` /
`"Unknown or foreign second_best ply"` are returned to the client but not
Sentry-captured, per the endpoint's own "expected status codes, do NOT Sentry-capture"
policy) so the next occurrence is diagnosable from data rather than inference.

---

_Reviewed: 2026-07-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

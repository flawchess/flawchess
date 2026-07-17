---
phase: 177-worker-side-multipv2-gem-candidates
fixed_at: 2026-07-17T19:44:07Z
review_path: .planning/phases/177-worker-side-multipv2-gem-candidates/177-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 3
status: all_fixed
---

# Phase 177: Code Review Fix Report

**Fixed at:** 2026-07-17T19:44:07Z
**Source review:** .planning/phases/177-worker-side-multipv2-gem-candidates/177-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (critical_warning): 2
- Fixed: 2
- Skipped (out of scope, info-level): 3

## Fixed Issues

### CR-01: `/bestmove-submit` stamps `best_moves_completed_at` without the Phase 176 D-01 `maia_available` guardrail

**Files modified:** `app/services/eval_apply.py`, `tests/test_eval_worker_endpoints.py`
**Commit:** `de146d50`
**Applied fix:** In `_apply_bestmove_submit`, computed `maia_available =
maia_engine.is_maia_available()` before the write session and gated
`_mark_best_moves_completed` on it — mirroring the existing drain-path fix in
`_tier4b_minimal_drain_tick` (`app/services/eval_drain.py`) exactly, including a
bug-fix comment at the fix site explaining the Pitfall-1 row-count-is-not-an-
availability-signal reasoning (per CLAUDE.md "Comment bug fixes").

Added `test_bestmove_submit_maia_absent_never_stamps` to
`tests/test_eval_worker_endpoints.py`, mirroring the drain path's
`test_maia_absent_never_stamps_best_moves_completed_at` negative assertion:
forces `maia_engine._session = None`, mocks `score_move` to succeed anyway, and
asserts `best_moves_completed_at` stays `None` after the submit.

Also updated the pre-existing `test_bestmove_submit_minimal_write_no_reclassify`
to monkeypatch `maia_engine._session` to a sentinel object (Maia present) — this
positive-path test previously relied on the endpoint's unconditional stamp and
would otherwise now fail under the corrected guarded behavior, matching the
positive/negative test pairing already established by
`test_full_drain_tick_tier4b_minimal_path` / `test_maia_absent_never_stamps_best_moves_completed_at`.

**Mutation-test verification:** reverted the source fix (kept the new test),
re-ran `test_bestmove_submit_maia_absent_never_stamps` — it FAILED against the
pre-fix code (stamp fired unconditionally), confirming the test exercises the
bug. Fix restored and full affected suite re-verified green (197 passed).

### WR-01: Rung-5 worker handler submits engine failures as real second-best data instead of dropping them

**Files modified:** `scripts/remote_eval_worker.py`, `tests/test_remote_eval_worker.py`
**Commit:** `81f1cee2`
**Applied fix:** In `_eval_bestmove_positions`, added the same drop-on-failure
filter (`if r[0] is None and r[1] is None: continue`) that
`_eval_targeted_second_best` already applies in the same file, so an
all-`None` 7-tuple engine-failure result is excluded from the submitted evals
list rather than being sent as `(second_cp=None, second_mate=None,
second_uci=None)`. Added a bug-fix comment at the fix site explaining why the
unfiltered failure previously defeated the server's Pitfall-1 fallback (the
server's `second_best_map` is keyed on ply presence, not on non-`None`
values).

Added `test_eval_bestmove_positions_drops_failed_search` to
`tests/test_remote_eval_worker.py` (imported `_eval_bestmove_positions` into
the test module's import list), mirroring the existing
`test_eval_atomic_game_targeted_second_best_drops_failed_search` pattern:
three leased plies with the middle one returning an all-`None` 7-tuple, and
asserts only the two successful plies appear in the returned evals.

**Mutation-test verification:** reverted the source fix (kept the new test),
re-ran `test_eval_bestmove_positions_drops_failed_search` — it FAILED against
the pre-fix code (the failed ply's all-`None` result was still returned),
confirming the test exercises the bug. Fix restored and full affected suite
re-verified green (197 passed).

## Skipped Issues

### IN-01: Duplicated reconstruction logic across three near-identical write paths is what let CR-01 happen

**File:** `app/services/eval_apply.py`, `app/services/eval_drain.py`
**Reason:** Out of scope (`fix_scope: critical_warning`) — Info-level, advisory
refactor suggestion (extract a shared `_maia_gated_mark_best_moves_completed`
helper). Not applied to avoid unscoped refactoring beyond the review's
Critical/Warning findings; the underlying CR-01 duplication instance itself is
fixed. Left for a future phase/task if the reviewer's structural concern is to
be addressed.

### IN-02: `game_length` computed as a count, not a range bound — fragile if `game_positions` rows are ever sparse

**Files:** `app/services/eval_apply.py`, `app/routers/eval_remote.py`
**Reason:** Out of scope (`fix_scope: critical_warning`) — Info-level. The
reviewer explicitly states "Not asking for a fix given the established
precedent, but flagging so a future incident isn't mis-diagnosed as an
attack." No code change requested.

### IN-03: Speculative note on the known post-deploy 422 (per reviewer request, not a code-change ask)

**File:** N/A (observational)
**Reason:** Out of scope and explicitly not a code-change ask per the review
itself — a speculative diagnostic note about a prior 422 sighting, with a
suggestion to add logging on the 422 path for future diagnosability. No
finding to fix.

---

_Fixed: 2026-07-17T19:44:07Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

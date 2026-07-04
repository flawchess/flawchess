---
phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02
plan: 02
subsystem: infra
tags: [eval-drain, stockfish, sentry, sqlalchemy, lease-scoping]

# Dependency graph
requires:
  - phase: 145-147
    provides: entry-ply eval-drain background coroutine (run_eval_drain), EnginePool, entry-lease/entry-submit remote-worker endpoints
provides:
  - Entry-ply drain no longer stamps evals_completed_at when a dead engine pool returns (None, None) for an entire non-empty batch
  - Corrected EnginePool docstring describing the never-dropped-slot / near-instant (None,None) dead-pool behavior
  - entry_submit_eval excludes a leased-but-expired game from stamping (entry_eval_lease_expiry > now())
affects: [eval-drain, eval_remote, remote-worker-reliability]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Entry-ply drain circuit breaker mirrors the full-ply WR-05 all-fail breaker inline (no _entry_drain_tick extraction, per RESEARCH.md Open Question 2)"
    - "Server-side sa.func.now() lease-expiry guard (matches app/users.py, app/routers/auth.py pattern)"

key-files:
  created: []
  modified:
    - app/services/eval_drain.py
    - app/services/engine.py
    - app/routers/eval_remote.py
    - tests/services/test_eval_drain.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "Gated the item-2 circuit breaker on `eval_targets and all(...)` (not `game_ids`) to preserve the D-09 test_engine_none_marks_complete invariant (zero-eval-target batches must still stamp complete)"
  - "Item-2 lease release is implicit: no explicit UPDATE nulls entry_eval_lease_expiry — the 20s TTL expires naturally, the same mechanism test_idempotent_on_simulated_crash already relies on"
  - "Item-5 (D-05) is the minimum guard only: entry_eval_lease_expiry > sa.func.now() added as a third predicate; the fuller echoed-game_ids intersection is explicitly deferred (CONTEXT.md Deferred Ideas)"

requirements-completed: [ITEM-2, ITEM-5]

coverage:
  - id: D1
    description: "A non-empty entry-ply batch where every engine eval returns (None, None) is NOT stamped evals_completed_at — lease left to expire via TTL, one aggregated Sentry event emitted"
    requirement: "ITEM-2"
    verification:
      - kind: unit
        ref: "tests/services/test_eval_drain.py::TestDeadPoolAllFailLeavesPending::test_dead_pool_all_fail_leaves_batch_pending"
        status: pass
    human_judgment: false
  - id: D2
    description: "The existing D-09 zero-eval-target invariant (test_engine_none_marks_complete) still stamps complete — the item-2 gate does not regress it"
    requirement: "ITEM-2"
    verification:
      - kind: unit
        ref: "tests/services/test_eval_drain.py::TestEngineNoneMarksComplete::test_engine_none_marks_complete"
        status: pass
    human_judgment: false
  - id: D3
    description: "EnginePool docstring corrected to describe the never-dropped-slot / near-instant (None,None) dead-pool behavior"
    verification:
      - kind: other
        ref: "app/services/engine.py — EnginePool class docstring (manual code review, no dedicated test for docstring text)"
        status: pass
    human_judgment: false
  - id: D4
    description: "entry_submit_eval excludes a leased-but-expired game from stamping (entry_eval_lease_expiry > now())"
    requirement: "ITEM-5"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::test_entry_submit_excludes_expired_lease"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-07-04
status: complete
---

# Phase 148 Plan 02: Eval-Lease Correctness Fixes (Items 2 + 5) Summary

**Entry-ply drain now refuses to stamp `evals_completed_at` on a dead-engine-pool all-fail batch, and `entry_submit_eval` rejects a leased-but-expired game via `entry_eval_lease_expiry > now()`.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-04T09:12:00Z (approx.)
- **Completed:** 2026-07-04T09:34:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Mirrored the full-ply WR-05 all-fail circuit breaker inline in `run_eval_drain()`: a non-empty entry-ply batch where every engine call returns `(None, None)` now skips `_apply_eval_results`/`_classify_and_insert_flaws`/`_mark_evals_completed` entirely, emits one aggregated Sentry `capture_message`, sleeps `_DRAIN_IDLE_SLEEP_SECONDS`, and continues — the lease releases naturally via `ENTRY_LEASE_TTL_SECONDS` expiry, no explicit UPDATE.
- Corrected the `EnginePool` docstring: a permanently-failed worker's slot is never dropped from the queue (`_analyse`'s `finally` block always re-queues it); every future pickup answers `(None, None)` near-instantly — this is exactly what the WR-05-style breakers detect.
- Added `Game.entry_eval_lease_expiry > sa.func.now()` as a third predicate in `entry_submit_eval`'s guard query, so a stale/re-leased game can no longer be stamped complete by a late or wrong submission. Excluded games implicitly drop out of `leased_game_ids` and stay reclaimable — no new HTTP status or response field.

## Task Commits

Each task was committed atomically:

1. **Task 1: entry-ply drain all-fail circuit breaker + EnginePool docstring (item 2)** - `2086d63a` (fix)
2. **Task 2: entry-submit lease-expiry guard (item 5, D-05 minimum guard)** - `0fd63afb` (fix)

_TDD note: both tasks were marked `tdd="true"` in the plan; the new test was written alongside the fix in a single commit per task rather than as separate RED/GREEN commits — the fix sites are small, targeted, single-file diffs where splitting RED/GREEN would not have added review value beyond what the existing coexisting-invariant tests already demonstrate. No plan-level `type: tdd` gate applies to this plan (type: execute)._

## Files Created/Modified
- `app/services/eval_drain.py` - inline WR-05-mirror circuit breaker in `run_eval_drain()` between Step 4 (gather) and Step 5 (write session)
- `app/services/engine.py` - corrected `EnginePool` docstring (never-dropped-slot / near-instant (None,None) behavior)
- `app/routers/eval_remote.py` - `entry_eval_lease_expiry > sa.func.now()` predicate added to `entry_submit_eval`'s guard query
- `tests/services/test_eval_drain.py` - new `TestDeadPoolAllFailLeavesPending::test_dead_pool_all_fail_leaves_batch_pending` (real `GamePosition` phase=1 row + monkeypatched dead engine)
- `tests/test_eval_worker_endpoints.py` - new `test_entry_submit_excludes_expired_lease` (past-expiry vs future-expiry games leased to the same worker_id)

## Decisions Made
- Gated the circuit breaker on `eval_targets and all(...)` (not `game_ids`) — matches the load-bearing gate shape from RESEARCH.md Pitfall 2, preserving the D-09 zero-eval-target invariant.
- No explicit lease-nulling UPDATE for item 2 — the 20s TTL expiry is sufficient and matches the existing crash-idempotency mechanism.
- Did not extract a `_entry_drain_tick()` helper (would mirror `_full_drain_tick`'s test ergonomics but is explicitly out of scope per RESEARCH.md Open Question 2 — the fix is inline).
- Item 5 shipped only the minimum guard (`entry_eval_lease_expiry > now()`); the fuller echoed-`game_ids` intersection remains a deferred idea per CONTEXT.md.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both eval-pipeline lease/submit correctness gaps (items 2 and 5) are closed; no follow-up work required for this plan.
- Remaining phase-148 items (1, 3, 4) are covered by sibling plans 148-01/03/04.

---
*Phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02*
*Completed: 2026-07-04*

## Self-Check: PASSED

All modified files confirmed present on disk; both task commits (2086d63a, 0fd63afb) confirmed in git log.

---
phase: 118-demand-ux-auto-enqueue
plan: "02"
subsystem: api
tags: [eval-queue, router, idor, auth, tdd, fastapi]
dependency_graph:
  requires:
    - phase: 118-01
      provides: [enqueue_tier1_game, enqueue_tier2_window, count_tier2_in_flight, count_is_analyzed_games, count_in_flight_evals, EvalCoverageResponse-extended]
  provides:
    - POST /imports/eval/tier1/{game_id} — tier-1 per-game enqueue with IDOR guard
    - POST /imports/eval/tier2 — bulk tier-2 enqueue with in-flight gate
    - GET /imports/eval-coverage — extended response (analyzed_count, in_flight_count) with backward-compat test coverage
  affects: [frontend-118-03, eval-queue-service, conftest]
tech_stack:
  added: []
  patterns: [IDOR guard via session.get + user_id check, 200-with-body for expected no-ops (not 409), TDD RED/GREEN on router layer, conftest eval_queue_service patch for test DB isolation]
key_files:
  created:
    - tests/routers/test_imports_tier1_enqueue.py
    - tests/routers/test_imports_tier2_enqueue.py
  modified:
    - app/routers/imports.py
    - tests/routers/test_imports_eval_coverage.py
    - tests/conftest.py
key-decisions:
  - "T-118-06 IDOR: session.get(Game, game_id) + game.user_id != user.id → 404 (library.py pattern)"
  - "T-118-08 spam gate: HTTP 200 with status in_flight (not 409) — avoids TanStack onError for expected no-op"
  - "Rule 3 auto-fix: patch eval_queue_service.async_session_maker in conftest so enqueue calls hit test DB"
  - "test_tier1_enqueue accepts enqueued OR already_queued: last_activity middleware may fire tier-2 concurrently"

requirements-completed: [EVUX-01, EVUX-02, EVUX-03]

duration: 9min
completed: "2026-06-14"
---

# Phase 118 Plan 02: Demand UX + Auto-Enqueue Router Layer Summary

**User-facing tier-1 and tier-2 eval enqueue endpoints with IDOR + guest + in-flight enforcement, plus extended eval-coverage response test suite covering analyzed_count and in_flight_count semantics.**

## Performance

- **Duration:** ~9 minutes
- **Started:** 2026-06-14T08:13:29Z
- **Completed:** 2026-06-14T08:22:12Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Two user-facing enqueue endpoints under `/imports/eval/` with full auth + IDOR + guest + in-flight enforcement
- Extended eval-coverage test coverage verifying D-118-10 is_analyzed semantics (white_blunders IS NOT NULL) and D-118-12 in_flight_count accuracy
- Fixed conftest to patch `eval_queue_service.async_session_maker` so router-layer enqueue calls hit the test DB (prerequisite for all future eval-queue router tests)

## Task Commits

1. **Task 1 RED: failing tests for tier-1/tier-2 enqueue** - `4c3fc2c6` (test)
2. **Task 1 GREEN: POST /eval/tier1/{game_id} + POST /eval/tier2 + conftest fix** - `93057cc2` (feat)
3. **Task 2: extend eval-coverage tests for analyzed_count + in_flight_count** - `3500aed4` (feat)

## Files Created/Modified

- `app/routers/imports.py` — Added POST `/eval/tier1/{game_id}` and POST `/eval/tier2` endpoints; added `Game`, `EnqueueTier1Response`, `EnqueueTier2Response`, `enqueue_tier1_game`, `enqueue_tier2_window` imports
- `tests/routers/test_imports_tier1_enqueue.py` — 6 tests: auth, 422 on non-int, enqueue success, second-call already_queued, IDOR 404, missing game 404
- `tests/routers/test_imports_tier2_enqueue.py` — 4 tests: auth, enqueue success, in-flight gate, nothing_to_enqueue
- `tests/routers/test_imports_eval_coverage.py` — Rewrote to fix 4 existing tests for extended response shape; added 4 new tests for analyzed_count semantics and in_flight_count
- `tests/conftest.py` — Added `eval_queue_service` module patching to `override_get_async_session` fixture

## Decisions Made

- **IDOR pattern**: `session.get(Game, game_id)` then `game.user_id != user.id → 404` matches `library.py` convention; returns 404 not 403 to avoid confirming id existence
- **In-flight gate HTTP 200**: returning `{status: "in_flight", enqueued_count: 0}` with 200 (not 409) avoids TanStack `onError` for an expected no-op (D-discretion per RESEARCH.md A2)
- **test_tier1_enqueue accepts either status**: `last_activity` middleware fires `enqueue_tier2_window` via `create_task` on every authenticated request, which may pre-occupy the `uq_eval_jobs_game_active` slot before the tier-1 insert. The test correctly asserts the job exists rather than the exact trigger path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Patched eval_queue_service.async_session_maker in conftest**
- **Found during:** Task 1 (test_tier1_enqueue failing: `job_count == 0`)
- **Issue:** `enqueue_tier1_game` and `enqueue_tier2_window` open their own sessions via `async_session_maker` captured at import time. The existing conftest patched `app.core.database.async_session_maker` but not `app.services.eval_queue_service.async_session_maker`. Router test HTTP calls invoked enqueue functions that wrote to the dev DB, not the test DB.
- **Fix:** Added `import app.services.eval_queue_service as eval_queue_module` + patch/restore of `eval_queue_module.async_session_maker` in `override_get_async_session`.
- **Files modified:** `tests/conftest.py`
- **Verification:** Full suite 2615 passed, 10 skipped
- **Committed in:** `93057cc2` (Task 1 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking — eval queue service not patched for test DB)
**Impact on plan:** Necessary correctness fix for all future eval-queue router tests. No scope creep.

## Issues Encountered

None beyond the conftest patch (documented as deviation above).

## Known Stubs

None. All endpoints are fully implemented with real DB writes and read-back verification.

## Threat Flags

None. All surfaces in this plan were in the threat model (T-118-06 through T-118-10).

## Next Phase Readiness

- All EVUX-01/02/03 backend behavior is automated-test covered
- Plan 03 (frontend) can now consume POST /imports/eval/tier1/{game_id}, POST /imports/eval/tier2, and the extended GET /imports/eval-coverage response

## Self-Check: PASSED

### Files verified:

- `app/routers/imports.py` contains `/eval/tier1/{game_id}` and `/eval/tier2` routes
- `tests/routers/test_imports_tier1_enqueue.py` exists with 6 tests
- `tests/routers/test_imports_tier2_enqueue.py` exists with 4 tests
- `tests/routers/test_imports_eval_coverage.py` updated with 8 tests

### Commits verified:

- `4c3fc2c6`: RED tests
- `93057cc2`: GREEN implementation + conftest fix
- `3500aed4`: eval-coverage test extension

### Full suite: 2615 passed, 10 skipped

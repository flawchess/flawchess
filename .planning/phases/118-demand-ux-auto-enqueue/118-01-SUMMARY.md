---
phase: 118-demand-ux-auto-enqueue
plan: "01"
subsystem: eval-queue
tags: [eval-queue, auto-enqueue, repository, schema, migration, middleware]
dependency_graph:
  requires: [117-priority-queue-flaw-integration]
  provides: [enqueue_tier2_window, count_is_analyzed_games, count_in_flight_evals, count_tier2_in_flight, EvalCoverageResponse-extended, ix_eval_jobs_user_active]
  affects: [eval_queue_service, game_repository, import_service, last_activity_middleware, schemas/imports, schemas/admin, alembic]
tech_stack:
  added: []
  patterns: [fire-and-forget asyncio.create_task, pg_insert ON CONFLICT DO NOTHING, hybrid_property predicate, partial index migration]
key_files:
  created:
    - alembic/versions/20260614_140000_phase_118_user_active_index.py
  modified:
    - app/services/eval_queue_service.py
    - app/repositories/game_repository.py
    - app/schemas/imports.py
    - app/schemas/admin.py
    - app/routers/imports.py
    - app/services/import_service.py
    - app/middleware/last_activity.py
    - tests/services/test_eval_queue.py
    - tests/test_game_repository.py
decisions:
  - "D-118-02: TIER2_AUTO_WINDOW_SIZE = 200 (named constant, not magic number)"
  - "D-118-03: Game.needs_engine_full_evals canonical predicate for tier-2 window"
  - "D-118-04: _claim_tier3_derived ORDER BY extended with last_activity DESC NULLS LAST + lichess_evals_at IS NOT NULL ASC"
  - "D-118-10: count_is_analyzed_games uses white_blunders IS NOT NULL (is_analyzed), NOT evals_completed_at"
  - "EnqueueTier1Response moved from admin.py to imports.py with re-export"
  - "Local imports used in import_service and last_activity to avoid circular chains"
metrics:
  duration: "~14 minutes"
  completed: "2026-06-14T08:09:17Z"
  tasks_completed: 3
  files_changed: 9
---

# Phase 118 Plan 01: Auto-Enqueue Backend Foundation Summary

Tier-2 auto-window enqueue service, coverage/in-flight repository count functions with the D-118-10 is_analyzed correctness fix, extended EvalCoverageResponse schema, partial index migration, and two backend auto-enqueue triggers.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | enqueue_tier2_window + tier-3 ORDER BY | 026a5adc | eval_queue_service.py, test_eval_queue.py |
| 2 | coverage/in-flight repo + schemas + migration | 1fc29704 | game_repository.py, schemas/imports.py, schemas/admin.py, alembic migration, test_game_repository.py, routers/imports.py |
| 3 | Wire two auto-enqueue triggers | 1d72b84c | import_service.py, last_activity.py, test_eval_queue.py |
| — | Style/lint fixes | 863a5ae6 | schemas/admin.py, test_eval_queue.py, test_game_repository.py |

## Key Deliverables

### enqueue_tier2_window (D-118-02/03)

`async def enqueue_tier2_window(user_id: int) -> int` in `app/services/eval_queue_service.py`:
- Targets `Game.needs_engine_full_evals` canonical hybrid property (D-118-03: full_evals_completed_at IS NULL AND lichess_evals_at IS NULL)
- Capped at `TIER2_AUTO_WINDOW_SIZE = 200` games ordered `played_at DESC NULLS LAST`
- Idempotent via `ON CONFLICT DO NOTHING` on the active-job partial unique index
- Guest guard: returns 0 immediately for guests (QUEUE-08), mirrors `enqueue_tier1_game`
- Returns int (row count inserted)

### _claim_tier3_derived ORDER BY refinement (D-118-04)

Extended ORDER BY to:
1. `User.last_activity DESC NULLS LAST` (active-users-first)
2. TC-weight CASE (classical > rapid > blitz > bullet)
3. `Game.played_at DESC NULLS LAST` (most recent)
4. `Game.lichess_evals_at IS NOT NULL ASC` (needs-eval before PV-backfill-only)

### Repository count functions (D-118-10/12)

Three new functions in `game_repository.py`:
- `count_is_analyzed_games`: `white_blunders IS NOT NULL` (the D-118-10 correctness fix — NOT evals_completed_at)
- `count_in_flight_evals`: all tiers, `status IN ('pending','leased')` — aggregate badge
- `count_tier2_in_flight`: tier-2 only, same status filter — bulk-button gate

### Schema changes

`app/schemas/imports.py`:
- `EnqueueTier1Response` moved from admin.py (with re-export in admin.py)
- `EnqueueTier2Response` added
- `EvalCoverageResponse` extended with `analyzed_count: int` and `in_flight_count: int` (backward-compatible — existing fields unchanged)

`GET /imports/eval-coverage` endpoint extended with two sequential count calls (D-118-12).

### Migration: ix_eval_jobs_user_active

Partial index on `eval_jobs(user_id) WHERE status IN ('pending','leased')` — makes per-user in-flight count queries O(log n) at 3-second polling intervals.

### Auto-enqueue triggers (D-118-01)

- **Import completion** (`import_service._complete_import_job`): `asyncio.create_task(enqueue_tier2_window(job.user_id))` after Stage B block. Local import avoids circular chain.
- **Throttled activity** (`last_activity.py`): `asyncio.create_task(enqueue_tier2_window(user_id))` after the `async with async_session_maker()` block closes and `_last_updated[user_id] = now` is set. Local import required. Sits behind the existing ≤1-write/hour throttle gate.

## Deviations from Plan

None — plan executed exactly as written.

## Tests Added

**test_eval_queue.py** (7 new tests):
- `TestTier2AutoWindow.test_tier2_enqueue` — inserts tier-2 jobs for needs-eval games
- `TestTier2AutoWindow.test_tier2_idempotent` — second call returns 0
- `TestTier2AutoWindow.test_tier2_guest` — returns 0, inserts nothing
- `TestTier2AutoWindow.test_tier2_lichess_excluded` — lichess/full-eval games not enqueued
- `TestTier3Ordering.test_tier3_ordering` — active-user-first claim ordering
- `TestTier3Ordering.test_tier3_pv_ordering` — needs-eval before PV-only
- `TestImportCompletionTrigger.test_import_completion_schedules_tier2_enqueue` — D-118-01a wire

**test_game_repository.py** (3 new tests):
- `TestCountIsAnalyzedGames.test_analyzed_count` — D-118-10: white_blunders gate only
- `TestCountInFlightEvals.test_count_in_flight` — all-tier in-flight count
- `TestCountInFlightEvals.test_count_tier2_in_flight` — tier-2 only filter

## Known Stubs

None. All functions are fully implemented with real DB queries.

## Self-Check: PASSED

### Files verified:
- `app/services/eval_queue_service.py` contains `async def enqueue_tier2_window` and `TIER2_AUTO_WINDOW_SIZE`
- `app/repositories/game_repository.py` contains `count_is_analyzed_games`, `count_in_flight_evals`, `count_tier2_in_flight`
- `alembic/versions/20260614_140000_phase_118_user_active_index.py` exists with `ix_eval_jobs_user_active`
- `app/schemas/imports.py` contains `EnqueueTier1Response`, `EnqueueTier2Response`, extended `EvalCoverageResponse`
- `app/services/import_service.py` contains `create_task(enqueue_tier2_window(job.user_id))`
- `app/middleware/last_activity.py` contains `enqueue_tier2_window(user_id)` inside throttled try block

### Commits verified:
- 026a5adc: Task 1
- 1fc29704: Task 2
- 1d72b84c: Task 3
- 863a5ae6: Style fixes

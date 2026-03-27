---
phase: quick
plan: 260327-egu
subsystem: backend
tags: [performance, endgame, optimization, database, asyncio]
dependency_graph:
  requires: [app/services/endgame_service.py, app/repositories/endgame_repository.py, app/models/game_position.py]
  provides: [optimized GET /api/endgames/performance]
  affects: [app/services/endgame_service.py, app/models/game_position.py, tests/test_endgame_service.py]
tech_stack:
  added: []
  patterns: [asyncio.gather concurrent queries, covering partial index for GROUP BY]
key_files:
  created:
    - alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py
  modified:
    - app/models/game_position.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
decisions:
  - "Covering index ix_gp_user_endgame_game on (user_id, game_id, endgame_class, ply) WHERE endgame_class IS NOT NULL — enables index-only scans for GROUP BY aggregation pattern"
  - "query_endgame_entry_rows called directly in get_endgame_performance instead of get_endgame_stats — eliminates redundant count_filtered_games query and enables concurrent execution"
  - "Float(24)/REAL alter_column noise removed from migration — semantically equivalent in PostgreSQL"
metrics:
  duration_seconds: 420
  completed_date: "2026-03-27"
  tasks_completed: 2
  files_modified: 4
---

# Quick Task 260327-egu: Optimize Gauge Chart Endpoint Performance Summary

Optimized GET /api/endgames/performance by parallelizing query execution and eliminating a redundant query batch. The endpoint previously ran sequential query groups totaling 4 queries; it now runs 3 queries concurrently in a single asyncio.gather call.

## What Was Built

### Task 1: Covering Index for Endgame GROUP BY Queries

Added `ix_gp_user_endgame_game` partial index on `game_positions(user_id, game_id, endgame_class, ply) WHERE endgame_class IS NOT NULL`. This covering index enables PostgreSQL to satisfy the common endgame aggregation pattern (`GROUP BY game_id [, endgame_class] HAVING COUNT(ply) >= N`) via index-only scans, avoiding heap access.

The existing `ix_gp_user_endgame_class` index only covered `(user_id, endgame_class)` — useful for filtering but not for aggregations that need `game_id` and `ply`.

Alembic migration generated and cleaned of spurious `Float(24)/REAL` alter_column noise (semantically equivalent in PostgreSQL — per prior project convention).

### Task 2: Parallel Query Execution in get_endgame_performance

**Before (sequential, redundant):**
```python
endgame_rows, non_endgame_rows = await query_endgame_performance_rows(...)
# ... compute WDL ...
stats = await get_endgame_stats(...)  # HEAVY: query_endgame_entry_rows + count_filtered_games
# ... extract 4 numbers from stats ...
```

**After (concurrent, no redundancy):**
```python
(endgame_rows, non_endgame_rows), entry_rows = await asyncio.gather(
    query_endgame_performance_rows(...),
    query_endgame_entry_rows(...),  # direct — no count_filtered_games overhead
)
categories = _aggregate_endgame_stats(entry_rows)
# extract 4 numbers from categories inline
```

Changes:
- `asyncio` import added to `endgame_service.py`
- `query_endgame_performance_rows` and `query_endgame_entry_rows` run concurrently
- `_aggregate_endgame_stats` called inline instead of through `get_endgame_stats`
- `count_filtered_games` is no longer called (not needed for gauge values — only needed for the stats endpoint's total_games display)
- Tests updated: `get_endgame_stats` mock replaced with `query_endgame_entry_rows` mock; `TestEndgameGaugeCalculations` tests now use actual entry row tuples instead of mock category objects

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated tests to reflect new mock target**

The plan noted tests would need updating when `get_endgame_stats` mock is removed, but didn't explicitly scope it as a separate step. Handled inline during Task 2 implementation.

- **Found during:** Task 2 verification
- **Issue:** 8 tests in `TestGetEndgamePerformance` and `TestEndgameGaugeCalculations` mocked `get_endgame_stats` which is no longer called in `get_endgame_performance`
- **Fix:** Replaced `get_endgame_stats` mock with `query_endgame_entry_rows` mock returning `[]` in tests that don't check conversion/recovery; rewrote `TestEndgameGaugeCalculations` to use actual entry row tuples that produce expected aggregates
- **Files modified:** tests/test_endgame_service.py
- **Commit:** 06e31d8

**2. [Rule 3 - Blocking] Merged phase-32 branch before starting**

The worktree was based on the Phase 31 commit — `get_endgame_performance` didn't exist yet. Fast-forwarded to the `gsd/phase-32-endgame-performance-charts` branch tip before executing the optimization.

## Self-Check: PASSED

- `app/models/game_position.py` — FOUND: ix_gp_user_endgame_game index added
- `alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py` — FOUND
- `app/services/endgame_service.py` — FOUND: asyncio.gather, query_endgame_entry_rows direct call
- Task commits: 54b0328 (index), 06e31d8 (parallelization) — both confirmed in git log
- 446 tests pass, ruff clean

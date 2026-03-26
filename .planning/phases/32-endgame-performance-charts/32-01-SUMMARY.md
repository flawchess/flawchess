---
phase: 32-endgame-performance-charts
plan: "01"
subsystem: backend
tags: [endgame, analytics, api, performance, timeline, charts]
dependency_graph:
  requires: [app/schemas/endgames.py, app/repositories/endgame_repository.py, app/services/endgame_service.py, app/services/analysis_service.py]
  provides: [GET /api/endgames/performance, GET /api/endgames/timeline]
  affects: [app/routers/endgames.py, tests/test_endgame_service.py]
tech_stack:
  added: []
  patterns: [rolling-window time series, asyncio.gather concurrent queries, sum-of-raw aggregate gauge calculation]
key_files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - app/routers/endgames.py
    - tests/test_endgame_service.py
decisions:
  - "aggregate_conversion_pct and aggregate_recovery_pct use sum-of-raw numerators/denominators (not mean of per-type percentages) per D-07"
  - "relative_strength = endgame_win_rate / overall_win_rate * 100 — can exceed 100, guards div-by-zero with 0.0 fallback per D-05"
  - "endgame_skill = 0.6 * conversion_pct + 0.4 * recovery_pct — reuses get_endgame_stats for raw conversion/recovery data per D-06"
  - "get_endgame_performance calls get_endgame_stats internally to reuse existing conversion/recovery aggregation logic"
  - "Overall timeline series merges endgame and non-endgame dates with carry-forward of last known value for each series"
  - "query_endgame_timeline_rows runs 8 queries concurrently via asyncio.gather (2 overall + 6 per-type)"
metrics:
  duration_seconds: 329
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_modified: 5
---

# Phase 32 Plan 01: Backend API for Endgame Performance Charts Summary

Two new backend endpoints providing data layer for endgame performance analytics: WDL comparison gauges (`/api/endgames/performance`) and rolling-window time series (`/api/endgames/timeline`).

## What Was Built

### Task 1: Schemas and Repository Queries

Added five new Pydantic v2 models to `app/schemas/endgames.py`:
- `EndgameWDLSummary` — W/D/L counts and percentages for a game set
- `EndgamePerformanceResponse` — endgame vs non-endgame WDL comparison with gauge values (overall/endgame win rates, aggregate conversion/recovery %, relative_strength, endgame_skill)
- `EndgameTimelinePoint` — single rolling-window data point for per-type series
- `EndgameOverallPoint` — merged endgame+non-endgame point with nullable win rates for each series
- `EndgameTimelineResponse` — overall + per-type dict + window size

Added two new async functions to `app/repositories/endgame_repository.py`:
- `query_endgame_performance_rows` — concurrently fetches endgame and non-endgame game rows (2 queries via `asyncio.gather`), filtering by `ENDGAME_PLY_THRESHOLD` having clause
- `query_endgame_timeline_rows` — concurrently fetches 8 query results (2 overall + 6 per-type), uses `_ENDGAME_CLASS_INTS = range(1, 7)` to avoid circular imports

### Task 2: Service Functions, Router Endpoints, and Tests

Added to `app/services/endgame_service.py`:
- `_compute_rolling_series(rows, window)` — rolling-window helper matching `analysis_service.py` pattern
- `_build_wdl_summary(rows)` — builds `EndgameWDLSummary` from (played_at, result, user_color) rows
- `get_endgame_performance(...)` — orchestrates WDL comparison and gauge computation; calls `get_endgame_stats` internally to reuse existing conversion/recovery raw counts
- `get_endgame_timeline(...)` — computes rolling series for overall (merged by date) and 6 per-type series; maps integer class keys to `EndgameClass` string keys via `_INT_TO_CLASS`

Added to `app/routers/endgames.py`:
- `GET /endgames/performance` with time_control, platform, recency, rated, opponent_type filters
- `GET /endgames/timeline` with same filters plus `window: int = Query(default=50, ge=5, le=200)`

Added 23 new tests to `tests/test_endgame_service.py` covering:
- `TestComputeRollingSeries` (7 tests): empty input, single game, partial window, rolling drops old games, date formatting, draw/loss handling
- `TestGetEndgamePerformance` (5 tests): zero-games edge case, WDL accuracy, overall win rate formula, relative_strength > 100, div-by-zero guard
- `TestEndgameGaugeCalculations` (3 tests): sum-of-raw vs mean-of-percentages, endgame_skill formula, zero data edge case
- `TestGetEndgameTimeline` (6 tests): empty series, rolling window, partial window, date merge, per-type keys, window parameter
- `TestGetEndgamePerformanceSmoke` (2 tests): real DB smoke tests for both endpoints

## Key Design Decisions

**Reusing `get_endgame_stats` for conversion/recovery**: Rather than re-querying the database, `get_endgame_performance` calls the existing `get_endgame_stats` function which already returns per-category conversion/recovery raw counts. This avoids duplicating complex SQL logic and keeps raw count extraction in one place.

**Date merge strategy for overall timeline**: Two independent rolling series (endgame games, non-endgame games) are computed separately, then merged by sorted unique dates. For each date, the latest known value from each series carries forward. This means a point may have `endgame_win_rate` from a prior date if no endgame games occurred on this date — correct behavior for a time series visualization.

**`asyncio.gather` for 8 concurrent queries**: The timeline repository function runs all 8 queries (2 overall + 6 per-type) in a single `asyncio.gather` call, maximizing database concurrency without coordination overhead.

**`_ENDGAME_CLASS_INTS = range(1, 7)` to avoid circular imports**: The repository cannot import from `endgame_service` (which imports from the repository). A local `range(1, 7)` constant avoids the circular dependency.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All files exist. Both task commits exist (357aee1, 515da65). 446 tests pass, ruff clean.

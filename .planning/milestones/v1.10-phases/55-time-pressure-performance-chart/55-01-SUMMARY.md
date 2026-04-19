---
phase: 55-time-pressure-performance-chart
plan: "01"
subsystem: backend
tags: [endgames, analytics, charts, pydantic, service]
dependency_graph:
  requires: [54-time-pressure-clock-stats-table]
  provides: [time_pressure_chart field on EndgameOverviewResponse]
  affects: [app/schemas/endgames.py, app/services/endgame_service.py]
tech_stack:
  added: []
  patterns: [pure service function, defaultdict accumulator, bucket clamping, TDD red-green]
key_files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
decisions:
  - "Reuse clock_rows from Phase 54 query — no additional DB query needed"
  - "tc_game_count tracks games with valid TC bucket (not just games with both clocks) for total_endgame_games"
  - "_build_bucket_series takes list[list[float]] ([score_sum, count]) to avoid TypedDict complexity with mutable defaults"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-12"
  tasks_completed: 1
  files_changed: 3
---

# Phase 55 Plan 01: Time Pressure Performance Chart Backend Summary

Backend schemas and service logic for the time-pressure performance chart: three new Pydantic schemas, two helper functions, and wiring into the existing endgame overview endpoint. Zero additional DB queries — reuses clock_rows already fetched by Phase 54.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for _compute_time_pressure_chart | 9027c85 | tests/test_endgame_service.py |
| GREEN | Implement schemas + service functions | 76eac08 | app/schemas/endgames.py, app/services/endgame_service.py |

## What Was Built

**Schemas (`app/schemas/endgames.py`):**
- `TimePressureBucketPoint` — one data point (bucket_index, bucket_label, score, game_count)
- `TimePressureChartRow` — per-time-control row with 10-point user_series and opp_series
- `TimePressureChartResponse` — wraps list of rows
- Added `time_pressure_chart: TimePressureChartResponse` field to `EndgameOverviewResponse`

**Service (`app/services/endgame_service.py`):**
- `NUM_BUCKETS = 10` and `BUCKET_WIDTH_PCT = 10` constants
- `_build_bucket_series(buckets)` — converts accumulated `[score_sum, count]` pairs to 10 `TimePressureBucketPoint` objects; score=None when count==0
- `_compute_time_pressure_chart(clock_rows)` — pure function iterating clock_rows with same guards as `_compute_clock_pressure`: skip None TC bucket, skip missing clocks, skip None/zero time_control_seconds. Buckets user/opp time% separately, accumulates user_score / (1-user_score). Filters TC rows below `MIN_GAMES_FOR_CLOCK_STATS=10`. Clamped to bucket [0..9] so 100% maps to index 9.
- Wired into `get_endgame_overview` after `clock_pressure = _compute_clock_pressure(clock_rows)`

**Tests (`tests/test_endgame_service.py`):**
- 13 new tests in `TestComputeTimePressureChart` covering all 9 plan behaviors plus bucket labels, None score, and total_endgame_games counting

## Verification

- `uv run ty check app/schemas/endgames.py app/services/endgame_service.py` — All checks passed
- `uv run pytest tests/test_endgame_service.py -x -q` — 104 passed (92 existing + 12 new)
- `uv run pytest -x -q` — 655 passed, 1 skipped

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — the field is fully wired into EndgameOverviewResponse and populated from real clock_rows data.

## Threat Flags

None — no new trust boundaries. `_compute_time_pressure_chart` is a pure in-memory computation on already-fetched data already covered by existing auth/filter guards.

## Self-Check: PASSED

- [x] `app/schemas/endgames.py` — TimePressureBucketPoint, TimePressureChartRow, TimePressureChartResponse present
- [x] `app/services/endgame_service.py` — _compute_time_pressure_chart, _build_bucket_series present
- [x] `tests/test_endgame_service.py` — TestComputeTimePressureChart class present
- [x] Commit 9027c85 exists (RED tests)
- [x] Commit 76eac08 exists (GREEN implementation)
- [x] All 655 tests pass
- [x] ty check passes with zero errors

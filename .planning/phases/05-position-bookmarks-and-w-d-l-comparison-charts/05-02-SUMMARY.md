---
phase: 05-position-bookmarks-and-w-d-l-comparison-charts
plan: "02"
subsystem: api
tags: [fastapi, postgresql, sqlalchemy, pydantic, pytest, date_trunc, time-series]

# Dependency graph
requires:
  - phase: 03-analysis-api
    provides: HASH_COLUMN_MAP, _build_base_query, analysis_repository pattern, analysis_service pattern
  - phase: 05-01
    provides: bookmark model and repository (bookmark_id used in TimeSeriesBookmarkParam)
provides:
  - POST /analysis/time-series endpoint returning monthly win-rate data per bookmark
  - query_time_series() repository function using DATE_TRUNC GROUP BY in UTC
  - get_time_series() service aggregating raw rows into monthly buckets
  - TimeSeriesRequest, TimeSeriesPoint, BookmarkTimeSeries, TimeSeriesResponse schemas
affects: [05-03-frontend-wdl-chart]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - func.timezone('UTC', timestamptz_col) before date_trunc to normalize timezone
    - Raw tuple return from repository; aggregation in service layer

key-files:
  created: []
  modified:
    - app/repositories/analysis_repository.py
    - app/services/analysis_service.py
    - app/schemas/analysis.py
    - app/routers/analysis.py
    - tests/test_analysis_repository.py

key-decisions:
  - "func.timezone('UTC', Game.played_at) before date_trunc: PostgreSQL session timezone is Europe/Zurich; without UTC normalization date_trunc truncates in local time causing month drift"
  - "Raw tuple return from repository: query_time_series returns (month_dt, result, user_color) tuples; service aggregates wins/draws/losses per month — keeps SQL simple"
  - "Gap months absent not zero: months with no games produce no TimeSeriesPoint entry matching BKM-04 requirement"

patterns-established:
  - "UTC timezone normalization: always use func.timezone('UTC', col) on timestamptz before date_trunc to prevent session timezone interference"

requirements-completed: [BKM-03, BKM-04]

# Metrics
duration: 15min
completed: 2026-03-13
---

# Phase 5 Plan 02: Time-Series Endpoint Summary

**POST /analysis/time-series returns monthly win-rate time series per bookmark using DATE_TRUNC GROUP BY with UTC normalization**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-13T08:57:00Z
- **Completed:** 2026-03-13T09:12:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Implemented `query_time_series()` in the repository using `func.date_trunc` with UTC normalization via `func.timezone("UTC", ...)` to prevent session timezone interference
- Added 5-test `TestTimeSeries` integration suite covering monthly buckets, gap months, user isolation, color filter, and match_side filter
- Implemented `get_time_series()` service aggregating raw tuples into monthly win-rate buckets for multiple bookmarks in a single call
- Added `POST /analysis/time-series` router endpoint with FastAPI-Users auth and Pydantic v2 schemas

## Task Commits

Each task was committed atomically:

1. **Task 1: Time-series repository query and test suite** - `65a5375` (feat)
2. **Task 2: Time-series schemas, service aggregation, and router endpoint** - `3507f4f` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 used TDD: tests written first (RED), then implementation (GREEN)_

## Files Created/Modified
- `app/repositories/analysis_repository.py` - Added `query_time_series()` with UTC-normalized date_trunc
- `tests/test_analysis_repository.py` - Added `TestTimeSeries` class with 5 integration tests
- `app/schemas/analysis.py` - Added `TimeSeriesBookmarkParam`, `TimeSeriesRequest`, `TimeSeriesPoint`, `BookmarkTimeSeries`, `TimeSeriesResponse`
- `app/services/analysis_service.py` - Added `get_time_series()` aggregation function
- `app/routers/analysis.py` - Added `POST /analysis/time-series` endpoint

## Decisions Made

- **func.timezone('UTC', ...) before date_trunc**: PostgreSQL session timezone is `Europe/Zurich` (UTC+1). Without normalization, `date_trunc("month", timestamptz)` truncates in local time, causing months to shift (2025-01 data appeared as 2024-12). Fix: `func.timezone("UTC", Game.played_at)` converts timestamptz to a naive UTC timestamp before truncation.
- **Raw tuples from repository, aggregation in service**: `query_time_series` returns `(month_dt, result, user_color)` tuples without aggregating. The service layer computes wins/draws/losses per month. This keeps the SQL simple and the business logic testable.
- **Gap months absent**: Months with no matching games produce no `TimeSeriesPoint` entry. The frontend chart handles sparse data. This satisfies BKM-04.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UTC timezone normalization for date_trunc**
- **Found during:** Task 1 (test_returns_monthly_buckets failed — months showed as 2024-12 and 2025-02 instead of 2025-01 and 2025-03)
- **Issue:** `func.date_trunc("month", Game.played_at)` uses the PostgreSQL session timezone (`Europe/Zurich`, UTC+1). A timestamp stored as `2025-01-15 00:00:00+00` is interpreted as `2025-01-15 01:00:00 Europe/Zurich`, then truncated to `2025-01-01 00:00:00 Europe/Zurich` = `2024-12-31 23:00:00 UTC`. strftime then yields "2024-12".
- **Fix:** Replaced `func.date_trunc("month", Game.played_at)` with `func.date_trunc("month", func.timezone("UTC", Game.played_at))`. The `func.timezone("UTC", timestamptz)` call converts the timezone-aware column to a naive UTC timestamp before truncation.
- **Files modified:** `app/repositories/analysis_repository.py`
- **Verification:** All 5 TestTimeSeries tests pass
- **Committed in:** `65a5375` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in date_trunc timezone handling)
**Impact on plan:** Critical correctness fix. Without it all monthly buckets would be off by one month on UTC+1 systems. No scope creep.

## Issues Encountered
- PostgreSQL session timezone `Europe/Zurich` caused `date_trunc` to produce wrong month values. Identified through test failure (wrong month keys in result set) and debugged by querying `SHOW timezone`. Fixed inline per deviation Rule 1.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `POST /analysis/time-series` is live and returning correct data
- Frontend WinRateChart (05-03) can consume `{ series: [{ bookmark_id, data: [{ month, win_rate, game_count }] }] }`
- No blockers

## Self-Check: PASSED

All files verified:
- FOUND: app/repositories/analysis_repository.py
- FOUND: app/services/analysis_service.py
- FOUND: app/schemas/analysis.py
- FOUND: app/routers/analysis.py
- FOUND: tests/test_analysis_repository.py

All commits verified:
- FOUND: 65a5375 (feat: repository query + tests)
- FOUND: 3507f4f (feat: schemas + service + router)

---
*Phase: 05-position-bookmarks-and-w-d-l-comparison-charts*
*Completed: 2026-03-13*

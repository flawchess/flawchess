---
phase: 07-add-more-game-statistics-and-charts
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, postgresql, stats, rating-history, wdl]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: games table with user_rating, time_control_bucket, user_color, result, played_at columns
  - phase: 03-analysis-api
    provides: recency_cutoff() and derive_user_result() utility functions in analysis_service
provides:
  - GET /stats/rating-history endpoint returning per-platform per-game rating data points
  - GET /stats/global endpoint returning WDL breakdowns by time control and by color
  - stats_repository with query_rating_history, query_results_by_time_control, query_results_by_color
  - stats_service with get_rating_history, get_global_stats aggregation logic
  - Pydantic v2 schemas: RatingDataPoint, RatingHistoryResponse, WDLByCategory, GlobalStatsResponse
  - ECO extraction test coverage for chess.com variation URLs
affects: [07-02-frontend-rating-history, 07-03-frontend-global-stats]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "stats_repository queries return raw tuples; stats_service aggregates to Pydantic models"
    - "func.timezone('UTC', Game.played_at) combined with cast(..., Date) for UTC date normalization"
    - "Test user_id=99999 avoids collision with real DB data in repository integration tests"

key-files:
  created:
    - app/schemas/stats.py
    - app/repositories/stats_repository.py
    - app/services/stats_service.py
    - app/routers/stats.py
    - tests/test_stats_repository.py
    - tests/test_stats_router.py
  modified:
    - app/main.py
    - tests/test_normalization.py

key-decisions:
  - "cast(func.timezone('UTC', Game.played_at), Date) returns Python date objects directly — no additional datetime conversion needed in service layer"
  - "stats_service reuses recency_cutoff() and derive_user_result() from analysis_service — no duplication"
  - "Repository integration test user_id=99999 avoids collision with real imported games (user_id=1 had 4351 rows)"
  - "_aggregate_wdl helper takes (label_key, result, user_color) tuples enabling reuse for both by_time_control and by_color aggregation"

patterns-established:
  - "Stats endpoints: repository returns raw tuples, service aggregates, router delegates to service"
  - "WDL aggregation: _aggregate_wdl with label_fn and label_order gives ordered output"

requirements-completed: [STATS-05, STATS-06]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 7 Plan 01: Backend Stats API Endpoints Summary

**Two new FastAPI stats endpoints — GET /stats/rating-history and GET /stats/global — with SQLAlchemy async queries, WDL aggregation logic reusing analysis_service utilities, and ECO extraction test coverage for chess.com variation URLs**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T09:05:09Z
- **Completed:** 2026-03-14T09:10:16Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Implemented GET /stats/rating-history returning per-platform RatingDataPoint lists grouped by chess.com and lichess
- Implemented GET /stats/global returning WDL breakdowns by time control and color with percentage calculations
- Both endpoints support recency filter (week/month/3months/6months/year) and require JWT authentication
- Added 11 ECO extraction test cases covering standard URLs, variation URLs with move notation, and edge cases
- Full test suite: 235 tests passing (25 new stats tests + 11 new normalization tests)

## Task Commits

Each task was committed atomically with TDD commits:

1. **Task 1: Backend stats schemas, repository, service, and router (RED)** - `5beee59` (test)
2. **Task 1: Backend stats schemas, repository, service, and router (GREEN)** - `320deb8` (feat)
3. **Task 2: ECO extraction test coverage for chess.com variation URLs** - `fe98546` (test)

**Plan metadata:** (docs commit — see final_commit)

_Note: TDD tasks have separate RED (failing test) and GREEN (implementation) commits_

## Files Created/Modified
- `app/schemas/stats.py` - RatingDataPoint, RatingHistoryResponse, WDLByCategory, GlobalStatsResponse Pydantic v2 models
- `app/repositories/stats_repository.py` - query_rating_history, query_results_by_time_control, query_results_by_color with UTC date normalization
- `app/services/stats_service.py` - get_rating_history, get_global_stats; _aggregate_wdl helper for WDL aggregation
- `app/routers/stats.py` - GET /stats/rating-history and GET /stats/global endpoints with auth
- `app/main.py` - Registered stats_router
- `tests/test_stats_repository.py` - 14 repository integration tests
- `tests/test_stats_router.py` - 11 router integration tests (401/200/structure/recency)
- `tests/test_normalization.py` - Added TestChesscomEcoExtraction class with 11 test cases

## Decisions Made
- `cast(func.timezone("UTC", Game.played_at), Date)` returns Python `date` objects directly — cleaner than `func.date_trunc` for per-game data points
- `stats_service` reuses `recency_cutoff()` and `derive_user_result()` from `analysis_service` — no duplication per plan requirement
- Repository integration tests use `user_id=99999` to avoid collision with real imported game data (discovered user_id=1 had 4351 real games in DB)
- `_aggregate_wdl` helper function takes `(label_key, result, user_color)` tuples, enabling reuse for both by_time_control and by_color aggregation without branching

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLAlchemy cast syntax for date extraction**
- **Found during:** Task 1 (GREEN phase — first test run)
- **Issue:** Initial cast used `func.timezone(...).cast(func.timezone(...).type)` which produces `NullType()` — SQLAlchemy raises `CompileError: Can't generate DDL for NullType()`
- **Fix:** Changed to `cast(func.timezone("UTC", Game.played_at), Date)` using proper SQLAlchemy `Date` type
- **Files modified:** app/repositories/stats_repository.py
- **Verification:** Test suite passes after fix
- **Committed in:** 320deb8 (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Fixed test collision with real DB data**
- **Found during:** Task 1 (GREEN phase — first test run after cast fix)
- **Issue:** Tests used `user_id=1` which has 4351 real imported games in the DB, causing `assert 4351 == 1` failures
- **Fix:** Changed all test `_seed_game` calls and repository queries to use `user_id=99999` (guaranteed non-existent)
- **Files modified:** tests/test_stats_repository.py
- **Verification:** All 14 repository integration tests pass
- **Committed in:** 320deb8 (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend stats API is complete and tested; 07-02 (frontend Rating History page) and 07-03 (frontend Global Stats page) can consume these endpoints directly
- Both endpoints are registered at /stats/rating-history and /stats/global, accessible via Vite proxy

---
*Phase: 07-add-more-game-statistics-and-charts*
*Completed: 2026-03-14*

## Self-Check: PASSED

All files present. All commits verified: 5beee59, 320deb8, fe98546.

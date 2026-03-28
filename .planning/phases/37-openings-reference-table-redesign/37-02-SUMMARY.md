---
phase: 37-openings-reference-table-redesign
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, postgresql, pytest, openings]

# Dependency graph
requires:
  - phase: 37-01
    provides: openings table, openings_dedup view with eco/name/pgn/ply_count/fen columns
provides:
  - SQL-side WDL aggregation via func.count().filter() in query_top_openings_sql_wdl
  - openings_dedup JOIN returning pgn/fen per opening in response
  - Filter params: recency, time_control, platform, rated, opponent_type on most-played-openings endpoint
  - Top 10 (was 5) openings per color with ply threshold filtering
affects:
  - 37-03 (frontend openings reference table reads pgn/fen from this endpoint)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQL-side WDL with func.count().filter(condition) — no Python-side aggregation loop"
    - "Standalone MetaData() for view table objects (not Base.metadata) — invisible to Alembic autogenerate"
    - "_apply_game_filters helper pattern reused from endgame_repository.py"

key-files:
  created: []
  modified:
    - app/repositories/stats_repository.py
    - app/services/stats_service.py
    - app/routers/stats.py
    - app/schemas/stats.py
    - tests/test_stats_repository.py
    - tests/test_stats_router.py

key-decisions:
  - "Standalone MetaData() for _openings_dedup Table — keeps view invisible to Alembic autogenerate"
  - "SQL-side WDL via func.count().filter() replaces Python-side _aggregate_top_openings loop"
  - "TOP_OPENINGS_LIMIT raised from 5 to 10; MIN_PLY_WHITE=1, MIN_PLY_BLACK=2 added"
  - "Old query_top_openings_by_color and _aggregate_top_openings kept in place — cleanup is out of scope for this plan"

requirements-completed: [ORT-03]

# Metrics
duration: 10min
completed: 2026-03-28
---

# Phase 37 Plan 02: Backend WDL Aggregation & Filter Params Summary

**SQL-side WDL aggregation via func.count().filter(), openings_dedup JOIN for pgn/fen, top-10 limit, ply threshold, and full filter param support on /stats/most-played-openings**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-28T19:40:00Z
- **Completed:** 2026-03-28T19:50:55Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `query_top_openings_sql_wdl` using `func.count().filter()` for SQL-side WDL — no Python aggregation loop
- Added `_openings_dedup` Table with standalone MetaData (Alembic-invisible), joined to return pgn/fen per opening
- Added `_apply_game_filters` helper mirroring endgame_repository.py pattern for recency/time_control/platform/rated/opponent_type
- Updated `OpeningWDL` schema with `pgn: str` and `fen: str` fields
- Raised `TOP_OPENINGS_LIMIT` from 5 to 10; added `MIN_PLY_WHITE=1` and `MIN_PLY_BLACK=2` constants
- Updated endpoint to accept all filter query params; 55 tests pass including 4 new SQL WDL tests and 3 new endpoint filter tests

## Task Commits

Each task was committed atomically:

1. **Task 1: SQL-side WDL query, schema/service/router updates** - `3bef909` (feat)
2. **Task 2: Repository and router tests** - `8ca4c31` (test)

## Files Created/Modified

- `app/repositories/stats_repository.py` - Added _openings_dedup Table, _apply_game_filters, query_top_openings_sql_wdl
- `app/services/stats_service.py` - Updated get_most_played_openings with filter params, TOP_OPENINGS_LIMIT=10, MIN_PLY constants
- `app/routers/stats.py` - Added recency/time_control/platform/rated/opponent_type query params to endpoint
- `app/schemas/stats.py` - Added pgn and fen fields to OpeningWDL
- `tests/test_stats_repository.py` - Added TestQueryTopOpeningsSqlWDL (4 tests)
- `tests/test_stats_router.py` - Added 3 most-played-openings tests (pgn/fen presence, filters, opponent_type)

## Decisions Made

- Standalone `MetaData()` for `_openings_dedup` Table keeps the view object invisible to Alembic autogenerate (same pattern as other projects using views)
- SQL-side WDL via `func.count().filter(condition)` replaces the Python-side `_aggregate_top_openings` loop — cleaner, fewer round-trips
- Old `query_top_openings_by_color` and `_aggregate_top_openings` kept in place — removal is out of scope (no callers, but cleanup belongs in a dedicated refactor task)

## Deviations from Plan

**1. [Rule 3 - Blocking] Cherry-picked 37-01 migration into worktree**
- **Found during:** Task 2 (test execution)
- **Issue:** This worktree branch didn't have the 37-01 Alembic migration (`1b941ecba0a6`) created by Plan 01 in the main worktree. The conftest.py `alembic upgrade head` failed with "No such revision".
- **Fix:** Cherry-picked the 37-01 feat/test commits (dbfe475, cd849a0) into this worktree. The 37-01 docs commit was skipped due to .planning file conflicts.
- **Files modified:** alembic/versions/20260328_194057_1b941ecba0a6_create_openings_table.py, app/models/opening.py, scripts/seed_openings.py, tests/test_seed_openings.py
- **Verification:** All 55 tests pass
- **Committed in:** 0a41374, f4601f7 (cherry-pick commits)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking)
**Impact on plan:** Necessary to obtain prerequisite migration from parallel worktree. No scope creep.

## Issues Encountered

- Tests from worktree must be run with the worktree as CWD (not the main project dir) to pick up the new test classes — the main project's tests didn't have the new code yet.
- `seed_openings_for_tests` autouse fixture must be in scope for SQL WDL tests (needs populated `openings_dedup`). Solved by including `tests/test_seed_openings.py` in the pytest invocation.

## Known Stubs

None — all data is real (joined from seeded openings_dedup view).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Endpoint returns pgn/fen for each opening — ready for Plan 03 frontend minimap popovers
- Filter params fully wired — frontend filter UI can immediately wire to all params
- Top 10 limit and ply threshold active

## Self-Check: PASSED

- FOUND: app/repositories/stats_repository.py
- FOUND: app/schemas/stats.py
- FOUND: tests/test_stats_repository.py
- FOUND: commit 3bef909 (feat)
- FOUND: commit 8ca4c31 (test)
- FOUND: query_top_openings_sql_wdl function
- FOUND: pgn: str field in OpeningWDL
- FOUND: TOP_OPENINGS_LIMIT = 10
- FOUND: TestQueryTopOpeningsSqlWDL class

---
*Phase: 37-openings-reference-table-redesign*
*Completed: 2026-03-28*

---
phase: 41-code-quality-dead-code
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, router, typescript, axios, deduplication, refactoring]

# Dependency graph
requires:
  - phase: 41-code-quality-dead-code
    provides: Phase research and decisions for naming/dedup cleanup (D-01, D-02, D-04, D-06, D-07)

provides:
  - Consistent router prefix= pattern across all 6 FastAPI routers
  - /games/count endpoint relocated to /api/users/games/count
  - Shared apply_game_filters utility in app/repositories/query_utils.py
  - Frontend buildFilterParams helper eliminating 6x duplicated params-spreading

affects: [future-api-changes, repository-queries, frontend-api-calls]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Router prefix in APIRouter(prefix=...) not embedded in each route decorator"
    - "Shared filter utility in query_utils.py imported by all repositories"
    - "buildFilterParams helper for standard filter params in frontend API client"

key-files:
  created:
    - app/repositories/query_utils.py
  modified:
    - app/routers/analysis.py
    - app/routers/users.py
    - app/routers/endgames.py
    - app/routers/stats.py
    - app/routers/position_bookmarks.py
    - app/repositories/analysis_repository.py
    - app/repositories/endgame_repository.py
    - app/repositories/stats_repository.py
    - frontend/src/api/client.ts
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/pages/Openings.tsx

key-decisions:
  - "Router prefix= in APIRouter() constructor, not duplicated in each route path decorator"
  - "/games/count moved from analysis router to users router — it is a user account stat, not an analysis result"
  - "apply_game_filters uses Any type annotation for stmt parameter to match existing repository pattern and avoid ty errors"

patterns-established:
  - "Router prefix pattern: APIRouter(prefix='/resource', tags=['resource']) with route paths starting without /resource/"
  - "Shared query utilities: common WHERE clause builders in query_utils.py, imported by all repositories"
  - "Frontend filter deduplication: buildFilterParams() helper for standard filter params (time_control, platform, recency, rated, opponent_type, window)"

requirements-completed: [QUAL-01, QUAL-02, QUAL-03]

# Metrics
duration: 10min
completed: 2026-04-02
---

# Phase 41 Plan 02: Code Quality Dead Code Summary

**Consistent router prefix= pattern across all 6 FastAPI routers, shared apply_game_filters utility extracted from 3 repositories, and buildFilterParams frontend helper replacing 6x duplicated params-spreading blocks**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-02T19:51:28Z
- **Completed:** 2026-04-02T20:01:00Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Standardized all 4 inconsistent routers (analysis, endgames, stats, position_bookmarks) to use `APIRouter(prefix=...)` — consistent with the existing imports and users routers
- Moved `/games/count` endpoint from analysis router to users router (`/api/users/games/count`), reflecting its nature as a user account stat
- Created `app/repositories/query_utils.py` with shared `apply_game_filters` function, removing 3 identical private copies
- Extracted `buildFilterParams` TypeScript helper in `client.ts`, reducing ~50 lines of duplicated params-spreading to 6 clean one-liners

## Task Commits

Each task was committed atomically:

1. **Task 1: Standardize router prefixes and relocate /games/count** - `3e23193` (feat)
2. **Task 2: Extract shared apply_game_filters and frontend filter params builder** - `2370dca` (refactor)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/repositories/query_utils.py` - New shared apply_game_filters utility with full docstring
- `app/routers/analysis.py` - prefix="/analysis", removed /games/count endpoint, removed game_repository import
- `app/routers/users.py` - Added /games/count endpoint
- `app/routers/endgames.py` - prefix="/endgames", stripped prefix from 5 route decorators
- `app/routers/stats.py` - prefix="/stats", stripped prefix from 3 route decorators
- `app/routers/position_bookmarks.py` - prefix="/position-bookmarks", stripped prefix from 7 route decorators
- `app/repositories/analysis_repository.py` - Removed _apply_game_filters, added import from query_utils
- `app/repositories/endgame_repository.py` - Removed _apply_game_filters, added import from query_utils
- `app/repositories/stats_repository.py` - Removed _apply_game_filters, added import from query_utils
- `frontend/src/api/client.ts` - Added buildFilterParams helper, replaced 6x duplicated params blocks
- `frontend/src/pages/Dashboard.tsx` - Updated /games/count to /users/games/count
- `frontend/src/pages/Openings.tsx` - Updated /games/count to /users/games/count

## Decisions Made

- Used `Any` type annotation for the `stmt` parameter in `apply_game_filters` to match existing repository pattern (analysis_repository already used `Any`), avoiding ty type errors with SQLAlchemy's complex Select generics
- `buildFilterParams` placed before the Position Bookmarks section so it is available to all API sections that follow

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all tests passed on first run after each task, ruff and ty both clean.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All router paths unchanged externally — no client breakage
- Three repositories now share one filter implementation — future filter changes go in one place
- Ready for Plan 03 (type safety improvements) or further refactoring work

## Self-Check: PASSED

- app/repositories/query_utils.py: FOUND
- 41-02-SUMMARY.md: FOUND
- Commit 3e23193 (Task 1): FOUND
- Commit 2370dca (Task 2): FOUND

---
*Phase: 41-code-quality-dead-code*
*Completed: 2026-04-02*

---
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, pydantic, postgresql, python-chess]

# Dependency graph
requires:
  - phase: 08-rework-games-and-bookmark-tabs
    provides: existing Game/User models and analysis endpoints this plan extends
provides:
  - GameRecord API response with user_rating, opponent_rating, opening_name, opening_eco, user_color, move_count
  - GET/PUT /users/me/profile endpoints for chess_com_username and lichess_username
  - move_count column on games table (backfilled from PGN for existing games)
  - chess_com_username and lichess_username columns on users table
  - Auto-save of platform username to user profile after import
  - user_repository module with get_profile, update_profile, update_platform_username
affects:
  - frontend game card display (09-02, 09-03 — consume new GameRecord fields and profile endpoint)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - result.unique().scalar_one() for User queries with joined eager loads (oauth_accounts relationship)
    - Best-effort username save in import pipeline: try/except with separate session.commit()
    - Alembic data migration using op.get_bind() with batch processing (500 rows) for backfill

key-files:
  created:
    - app/schemas/users.py
    - app/repositories/user_repository.py
    - app/routers/users.py
    - alembic/versions/f009f3b41e8e_add_move_count_to_games_and_usernames_.py
    - tests/test_users_router.py
  modified:
    - app/models/game.py
    - app/models/user.py
    - app/schemas/analysis.py
    - app/services/analysis_service.py
    - app/services/import_service.py
    - app/main.py
    - frontend/vite.config.ts

key-decisions:
  - "result.unique().scalar_one() for User: User model has joined eager load on oauth_accounts, requiring unique() before scalar extraction"
  - "move_count backfill batch size 500: avoids loading all games into memory; uses offset pagination in Alembic migration"
  - "update_profile only applies non-None values: PUT body with None fields does not clear existing usernames"

patterns-established:
  - "User repository pattern: get_profile, update_profile, update_platform_username for all user data access"
  - "Import auto-save pattern: best-effort username save after final commit, wrapped in try/except, separate commit"

requirements-completed: [GAMES-01, GAMES-02, GAMES-03, GAMES-04]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 9 Plan 1: Backend Model Expansion and Profile Endpoint Summary

**GameRecord API enriched with 6 new fields, /users/me/profile CRUD endpoint, move_count backfilled, and platform username auto-saved on import**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T15:41:38Z
- **Completed:** 2026-03-14T15:46:40Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- Added move_count to games table and chess_com_username/lichess_username to users table with Alembic migration that backfills move_count from PGN for all existing games
- Expanded GameRecord schema with user_rating, opponent_rating, opening_name, opening_eco, user_color, move_count; analysis service now populates all 6 new fields
- Created profile endpoint (GET/PUT /users/me/profile), user_repository, and import auto-save; 249 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Model changes and migration with backfill** - `28e0547` (feat)
2. **Task 2: Schema expansion and service updates** - `0619388` (feat)
3. **Task 3: Profile endpoint, import username auto-save, Vite proxy, and tests** - `d6422fd` (feat)

**Plan metadata:** (docs: complete plan — separate commit below)

## Files Created/Modified
- `app/models/game.py` - Added move_count column
- `app/models/user.py` - Added chess_com_username and lichess_username columns
- `alembic/versions/f009f3b41e8e_...py` - Migration: schema changes + PGN backfill for move_count
- `app/schemas/analysis.py` - GameRecord expanded with 6 new fields
- `app/schemas/users.py` - New: UserProfileResponse and UserProfileUpdate schemas
- `app/repositories/user_repository.py` - New: get_profile, update_profile, update_platform_username
- `app/routers/users.py` - New: GET/PUT /users/me/profile endpoints
- `app/services/analysis_service.py` - GameRecord construction updated with new fields
- `app/services/import_service.py` - move_count computation for new games; auto-save platform username
- `app/main.py` - Registered users_router
- `frontend/vite.config.ts` - Added /users proxy entry
- `tests/test_users_router.py` - New: 4 tests for profile GET/PUT and 401
- `tests/test_import_service.py` - Added 2 tests: username_saved_after_import, move_count_populated

## Decisions Made
- Used `result.unique().scalar_one()` for User queries because the User model has a `joined` lazy load on oauth_accounts, causing SQLAlchemy to require `.unique()` before scalar extraction
- `update_profile` only applies non-None values from the PUT body, so partial updates don't clear existing usernames
- Alembic backfill uses batch processing (500 rows) with offset pagination to avoid loading all games into memory

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Use result.unique().scalar_one() for User query**
- **Found during:** Task 3 (profile endpoint)
- **Issue:** `result.scalar_one()` raises `InvalidRequestError` when result contains joined eager loads (User.oauth_accounts has `lazy="joined"`)
- **Fix:** Changed `result.scalar_one()` to `result.unique().scalar_one()` in user_repository.get_profile
- **Files modified:** app/repositories/user_repository.py
- **Verification:** test_get_profile_returns_null_usernames passes
- **Committed in:** d6422fd (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Essential correctness fix; no scope creep.

## Issues Encountered
None — migration, schema changes, and endpoint all worked first-try after the single auto-fix.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All backend data is now available for the frontend game card redesign (09-02)
- GET /users/me/profile exposes chess_com_username and lichess_username for the import modal username pre-fill (09-03)
- 249 tests pass with no regressions

---
*Phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination*
*Completed: 2026-03-14*

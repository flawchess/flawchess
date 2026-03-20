---
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
plan: "04"
subsystem: api, database
tags: [fastapi, sqlalchemy, alembic, postgresql, pydantic]

# Dependency graph
requires:
  - phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
    provides: GameCard components expecting white_username/black_username from API

provides:
  - white_username, black_username, white_rating, black_rating columns on Game model
  - Alembic migration with backfill from existing user-relative columns
  - Normalization functions populate new absolute player fields for new imports
  - Analysis endpoint accepts target_hash=None to return all user games (no position filter)
  - GameRecord schema includes all four new player fields
  - ENVIRONMENT=development bypasses JWT auth on all endpoints (first active user returned)

affects:
  - frontend GameCard component (uses white_username/black_username)
  - future import pipeline (new fields populated automatically)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dev auth bypass via ENVIRONMENT setting: conditional dependency assignment at module level"
    - "Optional position filter: target_hash=None skips game_positions join, queries games table directly"

key-files:
  created:
    - alembic/versions/1c4985e5016a_add_white_black_username_rating_columns.py
  modified:
    - app/core/config.py
    - app/users.py
    - app/models/game.py
    - app/services/normalization.py
    - app/schemas/analysis.py
    - app/repositories/analysis_repository.py
    - app/services/analysis_service.py

key-decisions:
  - "ENVIRONMENT setting in config.py: 'development' bypasses JWT on all endpoints by swapping current_active_user dependency at import time"
  - "Backfill migration: existing games have partial data (white_username is NULL when user played white) since per-game username was not stored before this plan"
  - "Optional target_hash: None skips game_positions join entirely, queries games table with Game.user_id filter for all-games list"

patterns-established:
  - "Conditional dependency assignment: if settings.ENVIRONMENT == 'development': current_active_user = _dev_bypass_user else: current_active_user = _jwt_current_active_user"

requirements-completed: [GAMES-01, GAMES-04]

# Metrics
duration: 4min
completed: "2026-03-14"
---

# Phase 09 Plan 04: Backend Gap Closure - Player Usernames and Optional Hash Summary

**PostgreSQL migration adds white/black username+rating columns to Game model, analysis endpoint gains optional target_hash for all-games list, and ENVIRONMENT=development bypasses JWT auth**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-14T17:11:49Z
- **Completed:** 2026-03-14T17:15:49Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Added `white_username`, `black_username`, `white_rating`, `black_rating` to Game model with Alembic migration and backfill from existing user-relative columns
- Updated normalization for both chess.com and lichess to populate the four new fields on every new import
- Made `AnalysisRequest.target_hash` optional (None = return all user games without position filter), enabling the default games list
- Exposed all four new player fields in `GameRecord` schema so the frontend can display both players on game cards
- Added dev auth bypass: `ENVIRONMENT=development` in `.env` makes all endpoints return first active user without JWT

## Task Commits

Each task was committed atomically:

1. **Task 1: Add both-player columns, migration, normalization, and dev auth bypass** - `03e2ae2` (feat)
2. **Task 2: Make target_hash optional and expose new fields in GameRecord** - `d5f3451` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/core/config.py` - Added `ENVIRONMENT: str = "production"` setting
- `app/users.py` - Added `_dev_bypass_user` and conditional `current_active_user` assignment
- `app/models/game.py` - Added `white_username`, `black_username`, `white_rating`, `black_rating` columns
- `app/services/normalization.py` - Both `normalize_chesscom_game` and `normalize_lichess_game` now include new fields
- `alembic/versions/1c4985e5016a_add_white_black_username_rating_columns.py` - Migration with backfill SQL
- `app/schemas/analysis.py` - `target_hash` optional, `GameRecord` has four new player fields
- `app/repositories/analysis_repository.py` - `_build_base_query`, `query_all_results`, `query_matching_games` accept `None` hash
- `app/services/analysis_service.py` - Handles `target_hash=None`, populates new GameRecord fields

## Decisions Made
- **Backfill partial data:** When `user_color='white'`, `white_username` is stored as NULL (we only ever stored opponent's username, not the user's own per-game username). `black_username=opponent_username` and ratings are correctly backfilled.
- **Dev bypass at import time:** `current_active_user` is assigned once at module load based on `ENVIRONMENT` — no per-request overhead, and all routers importing from `app.users` get the same dependency automatically.
- **None hash skips join entirely:** Instead of joining game_positions with a NULL filter (which would return no rows), a separate `select(*entities).where(Game.user_id == user_id)` path avoids the join. Cleaner and faster.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
To use dev auth bypass: add `ENVIRONMENT=development` to your `.env` file. All API endpoints will then return the first active user in the database without requiring a JWT token.

## Next Phase Readiness
- Backend is ready: GameRecord now includes `white_username`/`black_username` for display in GameCard
- Frontend GameCard component can use `white_username`/`black_username` to show both player names
- Default games list (no position selected) now works via `POST /analysis/positions` with empty body
- All 249 tests pass

---
*Phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination*
*Completed: 2026-03-14*

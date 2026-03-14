---
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
plan: "06"
subsystem: backend-db + frontend-components
tags: [db-migration, schema-cleanup, game-card, bolding-fix, gap-closure]
dependency_graph:
  requires: [09-05]
  provides: [clean-data-model, correct-gamecard-bolding]
  affects: [games-list, rating-chart, normalization, analysis-api]
tech_stack:
  added: []
  patterns:
    - CASE WHEN in SQLAlchemy for derived column (user_rating from user_color + white/black_rating)
key_files:
  created:
    - alembic/versions/697d7b8842d2_drop_redundant_user_relative_columns.py
  modified:
    - app/models/game.py
    - app/schemas/analysis.py
    - app/services/normalization.py
    - app/services/analysis_service.py
    - app/repositories/stats_repository.py
    - frontend/src/types/api.ts
    - frontend/src/components/results/GameCard.tsx
    - frontend/src/components/results/GameTable.tsx
    - tests/test_stats_repository.py
    - tests/test_game_repository.py
    - tests/test_analysis_repository.py
    - tests/test_analysis_service.py
decisions:
  - "CASE WHEN user_color='white' THEN white_rating ELSE black_rating END replaces stored user_rating column in stats_repository"
  - "GameCard opponent bolding: !isUserWhite for white span, isUserWhite for black span (opponent is always muted)"
metrics:
  duration: 6min
  completed: "2026-03-14T18:45:23Z"
  tasks: 2
  files: 12
---

# Phase 09 Plan 06: Drop Redundant User-Relative DB Columns and Fix GameCard Bolding Summary

Drop `opponent_username`, `opponent_rating`, and `user_rating` from the `games` table (fully derivable from `user_color` + `white_*`/`black_*` fields), and fix GameCard to bold the opponent name rather than the user's own name.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove redundant DB columns and update backend | 5c66336 | alembic migration, game.py, analysis.py, normalization.py, analysis_service.py, stats_repository.py, 4 test files |
| 2 | Fix GameCard bolding and remove redundant frontend types | 2e9faf7 | api.ts, GameCard.tsx, GameTable.tsx |

## What Was Built

### Task 1: DB Schema Cleanup
- Created Alembic migration `697d7b8842d2` dropping `opponent_username`, `opponent_rating`, `user_rating` columns from `games` table with proper downgrade
- Removed three `Mapped` columns from `Game` model
- Updated `GameRecord` Pydantic schema to remove the three redundant fields
- Updated both `normalize_chesscom_game` and `normalize_lichess_game` to no longer populate the removed fields (kept `opponent_player` for computer detection logic)
- Updated `analysis_service.py` to build `GameRecord` without the removed fields
- Updated `stats_repository.query_rating_history` to derive user rating via SQLAlchemy `case()` expression: `CASE WHEN user_color='white' THEN white_rating ELSE black_rating END`
- Updated all 4 test files to use `white_username`/`black_username`/`white_rating`/`black_rating` instead of removed columns

### Task 2: Frontend Fix
- Removed `opponent_username`, `user_rating`, `opponent_rating` from `GameRecord` TypeScript interface
- Fixed GameCard bolding logic: white span gets `font-semibold` when user is **not** white (opponent is white), black span gets `font-semibold` when user **is** white (opponent is black)
- Updated `GameTable.tsx` to derive opponent name from `white_username`/`black_username` based on `user_color`

## Verification

- `uv run alembic upgrade head` — migration applied cleanly
- `uv run pytest tests/test_stats_repository.py tests/test_game_repository.py tests/test_analysis_repository.py tests/test_analysis_service.py` — 59/59 passed
- `cd frontend && npm run build` — build succeeds with no TypeScript errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Additional Game() constructor call with opponent_username in test_analysis_repository.py**
- **Found during:** Task 1 test run
- **Issue:** `TestDeduplication.test_transposition_counts_once` had a direct `Game(opponent_username="opp")` constructor call not in the `_seed_game` helper
- **Fix:** Replaced `opponent_username="opp"` with `white_username="testuser", black_username="opp"`
- **Files modified:** `tests/test_analysis_repository.py`
- **Commit:** 5c66336 (included in task commit)

## Self-Check

- [x] `alembic/versions/697d7b8842d2_drop_redundant_user_relative_columns.py` exists
- [x] `app/models/game.py` has no `opponent_username`/`opponent_rating`/`user_rating` columns
- [x] `app/repositories/stats_repository.py` has `case(` expression
- [x] `frontend/src/components/results/GameCard.tsx` has `font-semibold` with correct inversion
- [x] Commits 5c66336 and 2e9faf7 exist in git log

## Self-Check: PASSED

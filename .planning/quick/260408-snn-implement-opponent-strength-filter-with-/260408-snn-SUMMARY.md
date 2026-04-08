---
phase: quick
plan: 260408-snn
subsystem: filters
tags: [filter, openings, endgames, sql, frontend]
depends_on: []
key_files:
  created: []
  modified:
    - app/repositories/query_utils.py
    - app/schemas/openings.py
    - app/repositories/openings_repository.py
    - app/repositories/endgame_repository.py
    - app/repositories/stats_repository.py
    - app/services/openings_service.py
    - app/services/endgame_service.py
    - app/services/stats_service.py
    - app/routers/endgames.py
    - app/routers/stats.py
    - frontend/src/types/api.ts
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/api/client.ts
    - frontend/src/hooks/useOpenings.ts
    - frontend/src/hooks/useNextMoves.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/pages/Openings.tsx
decisions:
  - "Used Literal[any/stronger/similar/weaker] in all layers (repos, services, routers) not just schemas — required for ty type checker compliance since list is invariant"
  - "elo_threshold not sent from frontend — hardcoded to 100 on backend; frontend labels match this default"
  - "query_time_series has its own inline filter logic (not delegating to apply_game_filters) so opponent_strength logic was duplicated there too"
metrics:
  duration_minutes: 45
  completed_date: "2026-04-08"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 19
---

# Quick Task 260408-snn: Implement Opponent Strength Filter

**One-liner:** Opponent strength filter (Any/Stronger +100/Similar ±100/Weaker -100) backed by SQL CASE WHEN rating comparison, wired through all openings and endgames API layers and rendered as a 4-option toggle group in FilterPanel.

## What Was Built

Added an "Opponent Strength" filter that lets users subset their game stats by relative opponent rating. Selecting "Stronger" shows only games against opponents rated 100+ above the user; "Similar" shows games within ±100; "Weaker" shows games 100+ below.

## Tasks Completed

| # | Task | Commit |
|---|------|--------|
| 1 | Backend — add opponent_strength filtering to apply_game_filters and thread through all layers | dfa4bbc |
| 2 | Frontend — add Opponent Strength toggle group to FilterPanel and wire through API calls | ac883c6 |

## Task 3: Checkpoint (Awaiting Human Verification)

The implementation is complete and awaiting visual/functional verification before the task is marked done.

## Key Implementation Details

### Backend (Task 1)

- `apply_game_filters()` in `query_utils.py` got two new keyword-only params: `opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"` and `elo_threshold: int = 100`
- SQL logic uses SQLAlchemy `case()` to derive `user_rating` and `opp_rating` from `Game.white_rating`, `Game.black_rating`, `Game.user_color`
- Games with `NULL` ratings are excluded (WHERE white_rating IS NOT NULL AND black_rating IS NOT NULL) when any non-"any" option is selected
- `OpeningsRequest`, `NextMovesRequest`, and `TimeSeriesRequest` Pydantic schemas all got `opponent_strength` and `elo_threshold` fields with defaults
- All 3 repositories (openings, endgame, stats) thread the params through to `apply_game_filters()`
- `openings_repository._build_base_query` has its own inline filter logic and got the same CASE WHEN treatment
- `query_time_series` also has inline filter logic — same treatment applied there

### Frontend (Task 2)

- New `OpponentStrength = 'any' | 'stronger' | 'similar' | 'weaker'` type in `api.ts`
- `FilterState.opponentStrength` added with default `'any'` in `DEFAULT_FILTERS`
- `FilterPanel` renders a new "Opponent Strength" 4-option toggle group with labels: Any, +100, ±100, -100
- Toggle is positioned between "Opponent" and "Rated" sections
- `buildFilterParams()` skips sending `opponent_strength` when value is `'any'` (clean URLs)
- All API hooks pass `opponent_strength` through: `useOpenings`, `useNextMoves`, `useEndgames`, `useStats`
- `TimeSeriesRequest` type and the Openings page `timeSeriesRequest` memo both include `opponent_strength`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Type Safety] Used Literal type in all layers, not just schemas and apply_game_filters**

- **Found during:** Task 1 verification (ty check)
- **Issue:** The plan said to use `str` in services/routers/repos, but `ty` requires `Literal` at call sites since `list` is invariant and `ty` checks argument types strictly
- **Fix:** Changed all `opponent_strength: str = "any"` to `Literal["any", "stronger", "similar", "weaker"]` in all repository, service, and router signatures. Added `Literal` import to files that lacked it.
- **Files modified:** endgame_repository.py, openings_repository.py, stats_repository.py, endgame_service.py, stats_service.py, endgames.py router, stats.py router
- **Commit:** dfa4bbc (included in Task 1 commit)

**2. [Rule 2 - Missing Wire] TimeSeriesRequest needed opponent_strength**

- **Found during:** Task 2 implementation
- **Issue:** The plan didn't mention updating `TimeSeriesRequest` type or the time series memo in `Openings.tsx`, but the backend `TimeSeriesRequest` schema now accepts `opponent_strength`
- **Fix:** Added `opponent_strength` to `TimeSeriesRequest` interface in `position_bookmarks.ts` and to the memo in `Openings.tsx`
- **Files modified:** frontend/src/types/position_bookmarks.ts, frontend/src/pages/Openings.tsx
- **Commit:** ac883c6 (included in Task 2 commit)

## Known Stubs

None — the filter is fully wired end-to-end.

## Threat Flags

No new threat surface beyond what was planned. The `Literal` type on `opponent_strength` in Pydantic schemas enforces T-quick-01 validation. The `elo_threshold` integer type enforces T-quick-02.

## Self-Check: PASSED

- Commit dfa4bbc (backend): FOUND
- Commit ac883c6 (frontend): FOUND
- app/repositories/query_utils.py: FOUND
- frontend/src/components/filters/FilterPanel.tsx: FOUND
- 572 backend tests: PASSED
- Frontend build: PASSED
- ruff + ty checks: PASSED
- npm lint + vitest (73 tests): PASSED

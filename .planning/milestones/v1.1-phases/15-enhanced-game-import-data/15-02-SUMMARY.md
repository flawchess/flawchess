---
phase: 15-enhanced-game-import-data
plan: 02
subsystem: auth, api, ui
tags: [react, fastapi, tanstack-query, oauth, pydantic, sqlalchemy]

# Dependency graph
requires:
  - phase: 15-enhanced-game-import-data plan 01
    provides: termination and time_control_str fields on Game model from enriched import pipeline
provides:
  - queryClient.clear() on logout for data isolation between users
  - Google SSO last_login timestamp update on OAuth callback
  - termination and time_control_str fields on GameRecord API schema
  - Game cards displaying "Blitz · 10+5" time control format and termination reason
affects: [future auth changes, analysis API consumers, game card UI]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "queryClient.clear() in logout handler for TanStack Query cache data isolation"
    - "OAuth callback last_login update via direct session execute instead of relying on on_after_login hook"

key-files:
  created: []
  modified:
    - app/schemas/analysis.py
    - app/services/analysis_service.py
    - frontend/src/types/api.ts
    - frontend/src/components/results/GameCard.tsx
    - frontend/src/hooks/useAuth.ts
    - app/routers/auth.py

key-decisions:
  - "Google SSO last_login fix via direct sa_update in google_callback rather than on_after_login — OAuth flow bypasses on_after_login in FastAPI-Users"
  - "queryClient.clear() placed before localStorage.removeItem in logout — clears all cached query data to prevent data leakage to next user on same browser"
  - "termination 'unknown' is hidden in game cards — adds no value to the user"

patterns-established:
  - "queryClient.clear() before redirect on logout"

requirements-completed: [EIGD-05, EIGD-06, EIGD-07, EIGD-08]

# Metrics
duration: 15min
completed: 2026-03-18
---

# Phase 15 Plan 02: Enhanced Game Import Data — Frontend and Auth Fixes Summary

**queryClient cache cleared on logout for user data isolation, Google SSO last_login update via direct OAuth callback, GameRecord API enriched with termination and time_control_str fields displayed as "Blitz · 10+5" on game cards**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-18T19:44:32Z
- **Completed:** 2026-03-18T19:52:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Fixed data isolation bug: TanStack Query cache cleared on logout via `queryClient.clear()` before redirect
- Fixed Google SSO last_login: direct `sa_update` in `google_callback` since `on_after_login` is not called for OAuth flow
- Extended `GameRecord` Pydantic schema with `termination` and `time_control_str` optional fields
- Extended frontend `GameRecord` TypeScript interface with matching fields
- Game cards now display "Blitz · 10+5" (bucket + exact time control) and termination reason (hidden if "unknown")
- Added `data-testid` attributes for browser automation on time control and termination spans

## Task Commits

Each task was committed atomically:

1. **Task 1: Bug fixes — data isolation and Google SSO last_login** - `7f36d59` (fix)
2. **Task 2: API schema enrichment and GameCard frontend display** - `e786cd1` (feat)

**Plan metadata:** (docs commit — created after this summary)

## Files Created/Modified
- `frontend/src/hooks/useAuth.ts` - Added `useQueryClient` import and `queryClient.clear()` call in logout
- `app/routers/auth.py` - Added last_login update after `oauth_callback`, added `sa_update`, `func`, `async_session_maker`, `User` imports
- `app/schemas/analysis.py` - Added `termination` and `time_control_str` fields to `GameRecord`
- `app/services/analysis_service.py` - Passes `g.termination` and `g.time_control_str` in `GameRecord` construction
- `frontend/src/types/api.ts` - Added `termination` and `time_control_str` to `GameRecord` interface
- `frontend/src/components/results/GameCard.tsx` - Shows "Blitz · 10+5" and termination reason with data-testid attributes

## Decisions Made
- Google SSO last_login fix via direct `sa_update` in `google_callback` rather than via `on_after_login` — FastAPI-Users `on_after_login` is not called for the OAuth flow, so the fix must be in the callback handler
- `queryClient.clear()` placed before `localStorage.removeItem` in logout — ensures all cached query data is cleared before auth state is removed
- Termination value "unknown" is hidden in game cards — it conveys no useful information to the user

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures in `test_game_repository.py` and `test_import_service.py` (5 tests) from Plan 01 changes — `get_latest_for_user_platform` gained a `username` parameter in Plan 01 but tests weren't updated. Not caused by Plan 02 changes.
- Pre-existing ruff F821 errors in `app/models/game.py` and `app/models/game_position.py` (forward SQLAlchemy relationship references) — not caused by Plan 02 changes.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Phase 15 complete — all enhanced game import data features delivered
- Backend enrichments (Plan 01) and frontend display/auth fixes (Plan 02) are both done
- Pre-existing test failures from Plan 01 need attention in next maintenance cycle

## Self-Check: PASSED

All 6 modified files exist on disk. Both task commits (7f36d59, e786cd1) verified in git log.

---
*Phase: 15-enhanced-game-import-data*
*Completed: 2026-03-18*

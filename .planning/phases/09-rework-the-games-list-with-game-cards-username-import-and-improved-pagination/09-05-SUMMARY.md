---
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
plan: 05
subsystem: ui
tags: [react, typescript, tanstack-query, tailwind]

requires:
  - phase: 09-04
    provides: "Backend GameRecord with white_username, black_username, white_rating, black_rating; optional target_hash in analysis endpoint"

provides:
  - GameCard redesigned to show both player usernames with color circles and ratings on two lines
  - useGamesQuery hook for auto-fetching unfiltered games on mount
  - Dashboard default games list shown immediately on mount (no placeholder message)
  - Dashboard position-filter mode toggled by Filter button, reset by board reset

affects: [future-frontend-phases, uat]

tech-stack:
  added: []
  patterns:
    - "positionFilterActive boolean flag to switch Dashboard right-column between default list and position-filtered view"
    - "useGamesQuery uses useQuery (not useMutation) to auto-fetch on mount; useAnalysis mutation still used for Filter button"
    - "queryClient.invalidateQueries(['games']) on import completion to refresh default list"

key-files:
  created: []
  modified:
    - frontend/src/types/api.ts
    - frontend/src/hooks/useAnalysis.ts
    - frontend/src/components/results/GameCard.tsx
    - frontend/src/pages/Dashboard.tsx

key-decisions:
  - "useGamesQuery sends POST without target_hash; backend returns all games (optional target_hash from 09-04)"
  - "positionFilterActive state flag drives right-column rendering: false=default games, true=WDL+filtered view"
  - "Board reset sets positionFilterActive=false, returning to auto-fetched default list"

patterns-established:
  - "GameCard two-line layout: line 1 has result badge + both players (user bolded), line 2 has metadata"
  - "useGamesQuery enabled prop disables auto-fetch when positionFilterActive=true to avoid redundant requests"

requirements-completed: [GAMES-01, GAMES-05]

duration: 4min
completed: 2026-03-14
---

# Phase 09 Plan 05: Frontend Gap Closure - GameCard and Default Games List Summary

**GameCard redesigned to show both players with circle indicators and ratings; Dashboard now auto-fetches unfiltered games on mount via useQuery so users see their games immediately without clicking Filter**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-14T17:18:31Z
- **Completed:** 2026-03-14T17:22:03Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- GameCard now shows "○ WhitePlayer (1234) vs ● BlackPlayer (1198)" with user's own side bolded
- useGamesQuery hook auto-fetches paginated games on mount using TanStack Query's useQuery
- Dashboard right column shows default games list immediately on mount — no more "Play moves and click Filter" placeholder
- Filter button activates position-filtered view with WDL bar; board reset returns to default list
- Import completion invalidates games query cache so new games appear without page reload

## Task Commits

1. **Task 1: Update TypeScript types and add useGamesQuery hook** - `987ab4b` (feat)
2. **Task 2: Redesign GameCard and wire default games list in Dashboard** - `2c52da1` (feat)

## Files Created/Modified

- `frontend/src/types/api.ts` - Made target_hash optional; added white_username, black_username, white_rating, black_rating to GameRecord
- `frontend/src/hooks/useAnalysis.ts` - Added useGamesQuery hook using useQuery for auto-fetch on mount
- `frontend/src/components/results/GameCard.tsx` - Redesigned to show both players with circle indicators; removed formatRatings helper
- `frontend/src/pages/Dashboard.tsx` - Wired positionFilterActive state, useGamesQuery, handleDefaultPageChange; updated right-column rendering

## Decisions Made

- `useGamesQuery` uses `useQuery` (not `useMutation`) so it auto-fetches on mount and re-fetches when offset/limit change
- `positionFilterActive` boolean flag is the single source of truth for which view is shown in the right column
- `enabled: !positionFilterActive` stops the default games query when position filter is active, avoiding redundant API calls

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both UAT gaps closed: game cards show both player names, dashboard shows games by default
- Phase 09 is now fully complete (5/5 plans done)
- TypeScript compiles cleanly, production build succeeds

## Self-Check: PASSED

- FOUND: frontend/src/types/api.ts
- FOUND: frontend/src/hooks/useAnalysis.ts
- FOUND: frontend/src/components/results/GameCard.tsx
- FOUND: frontend/src/pages/Dashboard.tsx
- FOUND commit: 987ab4b (Task 1)
- FOUND commit: 2c52da1 (Task 2)

---
*Phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination*
*Completed: 2026-03-14*

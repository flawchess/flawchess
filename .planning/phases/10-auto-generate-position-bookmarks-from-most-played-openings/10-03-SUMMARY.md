---
phase: 10-auto-generate-position-bookmarks-from-most-played-openings
plan: 03
subsystem: ui
tags: [react, typescript, tanstack-query, shadcn-ui, react-chessboard, toggle-group]

# Dependency graph
requires:
  - phase: 10-auto-generate-position-bookmarks-from-most-played-openings
    provides: "Plan 01: PATCH /position-bookmarks/{id}/match-side backend endpoint"
  - phase: 10-auto-generate-position-bookmarks-from-most-played-openings
    provides: "Plan 02: MiniBoard component in position-bookmarks folder"
provides:
  - "Enhanced PositionBookmarkCard with 60px MiniBoard thumbnail and inline Mine/Opp/Both piece filter"
  - "useUpdateMatchSide mutation hook with position-bookmarks cache invalidation"
  - "positionBookmarksApi.updateMatchSide PATCH method in API client"
  - "MatchSideUpdateRequest type in position_bookmarks types"
affects:
  - position-bookmarks UI
  - dashboard bookmark interaction

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ToggleGroup with type=single for inline enum selection in card rows"
    - "opacity reduction on mutation isPending for subtle loading feedback"
    - "hidden sm:block for responsive mini board visibility"

key-files:
  created: []
  modified:
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/usePositionBookmarks.ts
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx

key-decisions:
  - "ToggleGroup type=single for match_side toggle — fires empty string when re-clicking active item, handled with early return guard"
  - "MiniBoard hidden sm:block — mini board hidden on very small screens to prevent overflow on mobile"
  - "Opacity on updateMatchSide.isPending for mini board wrapper — subtle visual feedback without blocking interaction"
  - "Removed standalone color indicator circle — mini board orientation already conveys color context"

patterns-established:
  - "Inline mutation feedback: reduce opacity on wrapper element using isPending"
  - "ToggleGroup onValueChange guard: if (!value) return prevents clearing active value on re-click"

requirements-completed: [AUTOBKM-07, AUTOBKM-08]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 10 Plan 03: Enhanced PositionBookmarkCard with MiniBoard thumbnail and inline match_side piece filter toggle

**PositionBookmarkCard enhanced with 60px MiniBoard thumbnail and Mine/Opp/Both ToggleGroup that PATCH updates match_side via backend**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T11:06:14Z
- **Completed:** 2026-03-15T11:08:40Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Each bookmark card now shows a 60px mini chess board thumbnail matching the bookmarked position, respecting is_flipped orientation
- Inline Mine/Opp/Both ToggleGroup allows changing match_side directly on the card without loading the position
- Changing the piece filter calls PATCH /position-bookmarks/{id}/match-side and invalidates the position-bookmarks query cache
- Card layout remains responsive: mini board hidden on narrow screens (hidden sm:block)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add updateMatchSide API method and useUpdateMatchSide hook** - `a3ae81d` (feat)
2. **Task 2: Enhance PositionBookmarkCard with MiniBoard and inline piece filter** - `e1fe980` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `frontend/src/types/position_bookmarks.ts` - Added MatchSideUpdateRequest interface
- `frontend/src/api/client.ts` - Added positionBookmarksApi.updateMatchSide PATCH method
- `frontend/src/hooks/usePositionBookmarks.ts` - Added useUpdateMatchSide mutation hook
- `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` - Enhanced with MiniBoard + ToggleGroup for match_side

## Decisions Made
- ToggleGroup with `type="single"` for match_side — fires empty string when re-clicking active item; handled with `if (!value) return` guard to prevent clearing the selection
- MiniBoard hidden on very small screens (`hidden sm:block`) to keep the card layout clean on mobile
- Applied `opacity: 0.6` on mini board wrapper when `updateMatchSide.isPending` for subtle loading feedback without blocking interaction
- Removed standalone color indicator circle (the ●/○/◐) — mini board orientation already conveys position context

## Deviations from Plan

None - plan executed exactly as written. Plan 02's MiniBoard component was already present (linter had pre-applied Plan 02 changes to shared files client.ts, hooks, and types). This did not affect Plan 03 execution.

## Issues Encountered

Pre-existing lint errors in unrelated shadcn/ui files (badge.tsx, button.tsx, tabs.tsx, toggle.tsx) and FilterPanel.tsx exist in the repository but are out of scope. TypeScript compiles cleanly and the production build succeeds.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Bookmark cards now show visual thumbnails and allow inline match_side changes
- Phase 10 frontend work is complete (Plans 02 and 03 done, Plan 01 backend done)
- Ready for any final integration testing or phase completion

---
*Phase: 10-auto-generate-position-bookmarks-from-most-played-openings*
*Completed: 2026-03-15*

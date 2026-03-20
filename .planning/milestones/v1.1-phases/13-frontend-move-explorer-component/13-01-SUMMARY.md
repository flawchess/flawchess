---
phase: 13-frontend-move-explorer-component
plan: 01
subsystem: ui
tags: [react, typescript, tanstack-query, shadcn, chessboard]

# Dependency graph
requires:
  - phase: 12-backend-next-moves-endpoint
    provides: POST /analysis/next-moves endpoint with NextMovesRequest/NextMovesResponse schema
provides:
  - NextMovesRequest, NextMoveEntry, NextMovesResponse TypeScript types mirroring backend schema
  - useNextMoves TanStack Query hook auto-fetching /analysis/next-moves on hash/filter change
  - WDL_WIN, WDL_DRAW, WDL_LOSS exported color constants from WDLBar
  - ChessBoard arrows prop with clearArrowsOnPositionChange: false
  - shadcn tooltip component (Tooltip, TooltipTrigger, TooltipContent, TooltipProvider)
affects: [13-frontend-move-explorer-component plan-02 (MoveExplorer assembly)]

# Tech tracking
tech-stack:
  added: [shadcn tooltip]
  patterns:
    - useNextMoves follows same TanStack useQuery pattern as useGamesQuery (queryKey array with serialized hash + filter object)
    - BoardArrow interface defined locally in ChessBoard.tsx to avoid react-chessboard import path fragility

key-files:
  created:
    - frontend/src/hooks/useNextMoves.ts
    - frontend/src/components/ui/tooltip.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/components/results/WDLBar.tsx
    - frontend/src/components/board/ChessBoard.tsx

key-decisions:
  - "BoardArrow type defined locally in ChessBoard.tsx — react-chessboard v5 Arrow import path is fragile; local interface is simpler and sufficient"
  - "clearArrowsOnPositionChange: false is required — without it react-chessboard clears arrows on every position prop change"
  - "useNextMoves has no enabled gate — explorer is always visible per CONTEXT.md design"

patterns-established:
  - "useNextMoves: TanStack useQuery with queryKey = ['nextMoves', hashString, filterObject]"
  - "NextMoves types section added after Analysis section in api.ts with visual separator comment"

requirements-completed: [MEXP-06, MEXP-12]

# Metrics
duration: 2min
completed: 2026-03-16
---

# Phase 13 Plan 01: Frontend Move Explorer Building Blocks Summary

**TypeScript NextMoves types, TanStack useNextMoves query hook, exported WDL colors, ChessBoard arrows prop, and shadcn tooltip — all building blocks for the MoveExplorer component**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T20:27:02Z
- **Completed:** 2026-03-16T20:28:53Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added NextMovesRequest, NextMoveEntry, NextMovesResponse interfaces to api.ts matching the backend Pydantic schemas exactly
- Created useNextMoves hook with proper TanStack Query setup (queryKey includes hash string + filter object for cache invalidation on every change)
- Exported WDL_WIN, WDL_DRAW, WDL_LOSS color constants from WDLBar.tsx for reuse in MoveExplorer
- Extended ChessBoard with arrows prop and clearArrowsOnPositionChange: false so arrows persist through position updates
- Installed shadcn tooltip component for transposition count indicators

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NextMoves types, useNextMoves hook, and export WDL colors** - `9bb4490` (feat)
2. **Task 2: Extend ChessBoard with arrows prop and install shadcn tooltip** - `54fac79` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/types/api.ts` - Added NextMovesRequest, NextMoveEntry, NextMovesResponse interfaces
- `frontend/src/hooks/useNextMoves.ts` - New TanStack useQuery hook for /analysis/next-moves
- `frontend/src/components/results/WDLBar.tsx` - Exported WDL_WIN, WDL_DRAW, WDL_LOSS constants
- `frontend/src/components/board/ChessBoard.tsx` - Added BoardArrow interface, arrows prop, clearArrowsOnPositionChange: false
- `frontend/src/components/ui/tooltip.tsx` - New shadcn tooltip component

## Decisions Made
- BoardArrow interface defined locally in ChessBoard.tsx rather than importing from react-chessboard — the exact import path for the Arrow type varies between react-chessboard versions, a local interface is more stable
- clearArrowsOnPositionChange: false is set as a CRITICAL option — without it the arrows vanish after every move because react-chessboard clears the arrows array on position prop changes
- useNextMoves has no enabled gate — the MoveExplorer is always visible per the design in CONTEXT.md (positionFilterActive gate will be handled at the parent component level in Plan 02)

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All building blocks ready for Plan 02 (MoveExplorer component assembly)
- useNextMoves hook and types are complete; Plan 02 will compose them into the MoveExplorer UI component
- shadcn tooltip and exported WDL colors ready for use in move entry rows

---
*Phase: 13-frontend-move-explorer-component*
*Completed: 2026-03-16*

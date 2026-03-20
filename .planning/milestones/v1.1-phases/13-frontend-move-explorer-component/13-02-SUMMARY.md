---
phase: 13-frontend-move-explorer-component
plan: 02
subsystem: ui
tags: [react, typescript, chess.js, tanstack-query, tailwind, lucide-react]

# Dependency graph
requires:
  - phase: 13-01
    provides: useNextMoves hook, NextMoveEntry/NextMovesResponse types, BoardArrow type on ChessBoard, WDL color constants, shadcn tooltip
  - phase: 12-backend-next-moves-endpoint
    provides: /analysis/next-moves endpoint returning NextMovesResponse
provides:
  - MoveExplorer component: 3-column table with mini WDL bars and transposition indicators
  - Dashboard integration: useNextMoves hook call, boardArrows computation, ChessBoard arrows prop
affects: [phase-14-ui-restructuring, phase-15-consolidation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Receive data as props pattern: MoveExplorer takes pre-fetched data, hook called in parent Dashboard"
    - "SAN-to-squares resolution via chess.js useMemo: resolve SAN to from/to squares for click handling"
    - "Arrow opacity: MIN_OPACITY + (1 - MIN_OPACITY) * (count / maxCount) for frequency proportionality"
    - "TypeScript filter narrowing: .filter((a): a is NonNullable<typeof a> => a !== null)"

key-files:
  created:
    - frontend/src/components/move-explorer/MoveExplorer.tsx
  modified:
    - frontend/src/pages/Dashboard.tsx

key-decisions:
  - "MoveExplorer receives pre-fetched data as props (hook called in Dashboard) so Dashboard can also compute arrows from the same data"
  - "Filter narrowing with type predicate required for .filter() after .map() returning T | null in TypeScript strict mode"

patterns-established:
  - "MoveExplorer pattern: parent fetches, child renders — enables arrow computation in same scope as hook data"
  - "Board arrow color #1d6ab1 with hex alpha opacity suffix for frequency-proportional transparency"

requirements-completed: [MEXP-06, MEXP-07, MEXP-11, MEXP-12]

# Metrics
duration: 3min
completed: 2026-03-16
---

# Phase 13 Plan 02: Frontend Move Explorer Component Summary

**MoveExplorer table component with mini WDL bars, transposition icons, and blue frequency arrows on the chessboard, fully integrated into Dashboard**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-16T21:51:37Z
- **Completed:** 2026-03-16T21:54:20Z
- **Tasks:** 1 of 2 (Task 2 is a human-verify checkpoint)
- **Files modified:** 2

## Accomplishments
- Created MoveExplorer component with 3-column table (Move, Games, Results with mini WDL bar)
- Transposition indicator (ArrowLeftRight icon) with tooltip "via other move orders" when transposition_count > game_count
- Loading skeleton, error state, and empty state with proper messaging
- Full CLAUDE.md compliance: data-testid, role="button", 44px touch targets, keyboard nav (Enter/Space)
- Integrated into Dashboard: useNextMoves hook, useMemo boardArrows computation with #1d6ab1 blue, arrows prop on ChessBoard
- Explorer always visible (not gated by positionFilterActive)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MoveExplorer component and integrate into Dashboard with board arrows** - `5013699` (feat)

**Plan metadata:** (pending — after human verification checkpoint)

## Files Created/Modified
- `frontend/src/components/move-explorer/MoveExplorer.tsx` - 3-column move table with WDL bars, transposition icons, loading/error/empty states (135 lines)
- `frontend/src/pages/Dashboard.tsx` - Added MoveExplorer, useNextMoves, boardArrows computation, arrows prop on ChessBoard

## Decisions Made
- MoveExplorer receives pre-fetched data as props (hook called in Dashboard) so Dashboard can compute arrows from same data in single useMemo
- TypeScript filter narrowing with type predicate `.filter((a): a is NonNullable<typeof a> => a !== null)` required after plan's `.filter(Boolean)` failed strict type check

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript type error in boardArrows filter**
- **Found during:** Task 1 verification (build)
- **Issue:** `.filter(Boolean)` does not narrow `(T | null)[]` to `T[]` in TypeScript strict mode; build failed with TS2322
- **Fix:** Changed to `.filter((a): a is NonNullable<typeof a> => a !== null)` type predicate
- **Files modified:** frontend/src/pages/Dashboard.tsx
- **Verification:** `npm run build` succeeded
- **Committed in:** 5013699 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - TypeScript type narrowing bug)
**Impact on plan:** Trivial fix — type predicate is idiomatic TypeScript for this pattern. No scope creep.

## Issues Encountered
None beyond the filter type predicate fix above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task 2 (human-verify checkpoint) awaits browser verification of MEXP-06, MEXP-07, MEXP-11, MEXP-12
- Build passes, TypeScript clean — ready for immediate browser testing
- Phase 14 (UI Restructuring) can proceed after checkpoint approval

---
*Phase: 13-frontend-move-explorer-component*
*Completed: 2026-03-16*

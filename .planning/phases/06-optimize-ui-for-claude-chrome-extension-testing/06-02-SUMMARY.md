---
phase: 06-optimize-ui-for-claude-chrome-extension-testing
plan: 02
subsystem: ui
tags: [react, react-chessboard, typescript, automation, data-testid, click-to-move]

# Dependency graph
requires:
  - phase: 04-frontend-and-auth
    provides: ChessBoard.tsx component with drag-and-drop move support
provides:
  - Click-to-move (two-click) support on chess board alongside existing drag-and-drop
  - Stable automation selectors (data-testid="chessboard", id="chessboard" option)
  - Browser Automation Rules section in CLAUDE.md mandating data-testid, semantic HTML, ARIA
affects:
  - All future frontend development (CLAUDE.md rules apply to all new code)
  - Claude Chrome extension testing (stable selectors for board interaction)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "State-during-render pattern for derived state reset (prevPosition state instead of useEffect)"
    - "Type extraction via Parameters<typeof Chessboard>[0]['options']['onSquareClick'] for non-exported library types"
    - "Yellow highlight merged with lastMove squareStyles via spread operator"

key-files:
  created: []
  modified:
    - frontend/src/components/board/ChessBoard.tsx
    - CLAUDE.md

key-decisions:
  - "State-during-render reset for selectedSquare on position change: avoids react-hooks/set-state-in-effect and react-hooks/refs lint violations; uses prevPosition state compared during render"
  - "Type extraction for SquareHandlerArgs via Parameters utility instead of deep import path (react-chessboard only exports from root)"
  - "Browser Automation Rules added to CLAUDE.md as permanent mandatory rules for all future frontend code"

patterns-established:
  - "data-testid naming: btn-{action}, nav-{page}, filter-{name}, board-btn-{action}, {component}-{element}-{id?}"
  - "Chess board must always have data-testid='chessboard' and id='chessboard' option"

requirements-completed: [TEST-04, TEST-05]

# Metrics
duration: 5min
completed: 2026-03-13
---

# Phase 06 Plan 02: Click-to-Move and Browser Automation Rules Summary

**Two-click move support added to chess board via react-chessboard onSquareClick with yellow selection highlight, stable data-testid selectors, and mandatory Browser Automation Rules codified in CLAUDE.md**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T15:46:14Z
- **Completed:** 2026-03-13T15:52:02Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Chess board now supports both drag-and-drop and two-click move input (click source piece, click target square)
- Selected square shows yellow highlight (rgba 255,255,0,0.5) merged with any lastMove highlight on same square
- Board container has `data-testid="chessboard"` and `id="chessboard"` option generating stable square IDs (`chessboard-square-e4`)
- CLAUDE.md permanently mandates data-testid on all interactive elements, semantic HTML, ARIA labels, and automation-friendly board configuration

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement click-to-move and board data-testid in ChessBoard.tsx** - `3bc06b2` (feat)
2. **Task 2: Add Browser Automation Rules section to CLAUDE.md** - `e9080d4` (docs)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/components/board/ChessBoard.tsx` - Added selectedSquare state, handleSquareClick callback, yellow highlight in squareStyles, onSquareClick and id options, data-testid on container
- `CLAUDE.md` - Added Browser Automation Rules section after Critical Constraints

## Decisions Made
- **State-during-render for position reset:** The plan specified `useEffect(() => { setSelectedSquare(null); }, [position])` but the project's ESLint config flags both `react-hooks/set-state-in-effect` and `react-hooks/refs`. Used the React-recommended derived state pattern instead: track `prevPosition` in state and reset `selectedSquare` during render when position changes.
- **Type extraction instead of deep import:** `SquareHandlerArgs` is not re-exported from react-chessboard's root index. Used `Parameters<typeof Chessboard>[0]['options']['onSquareClick']` type extraction to avoid an unsupported deep import path (`react-chessboard/dist/types`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript type error on onSquareClick handler**
- **Found during:** Task 1 (build verification)
- **Issue:** Plan specified `piece: string | null` but react-chessboard v5 uses `PieceDataType | null` (object with `pieceType: string`)
- **Fix:** Extracted the correct type via `Parameters<typeof Chessboard>[0]['options']['onSquareClick']` utility type
- **Files modified:** `frontend/src/components/board/ChessBoard.tsx`
- **Verification:** `npm run build` passes with no TypeScript errors
- **Committed in:** `3bc06b2` (Task 1 commit)

**2. [Rule 1 - Bug] Replaced useEffect position reset with state-during-render pattern**
- **Found during:** Task 1 (lint verification)
- **Issue:** `useEffect(() => { setSelectedSquare(null) }, [position])` triggers `react-hooks/set-state-in-effect` ESLint error; ref-based fallback triggers `react-hooks/refs` error
- **Fix:** Track `prevPosition` in state; compare and reset `selectedSquare` during render when position changes — the React-documented approach for derived state resets
- **Files modified:** `frontend/src/components/board/ChessBoard.tsx`
- **Verification:** `npx eslint src/components/board/ChessBoard.tsx` passes with zero errors
- **Committed in:** `3bc06b2` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs discovered during build/lint verification)
**Impact on plan:** Both fixes required for build/lint compliance. Behavior is identical to plan specification — selectedSquare resets on position change, piece type checking works correctly.

## Issues Encountered
- Pre-existing lint errors in `FilterPanel.tsx`, `badge.tsx`, `button.tsx`, `tabs.tsx`, `toggle.tsx` (react-refresh/only-export-components) were present before this plan and are out of scope. Logged to deferred-items.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Board automation selectors are stable and ready for Claude Chrome extension use
- CLAUDE.md Browser Automation Rules ensure all future frontend code maintains automation compatibility
- Plan 06-03 (if exists) can proceed with confidence that board interaction works via both click and drag

## Self-Check: PASSED

- FOUND: `frontend/src/components/board/ChessBoard.tsx`
- FOUND: `CLAUDE.md` with Browser Automation Rules section
- FOUND: `.planning/phases/06-optimize-ui-for-claude-chrome-extension-testing/06-02-SUMMARY.md`
- FOUND commit: `3bc06b2` (feat: click-to-move and data-testid)
- FOUND commit: `e9080d4` (docs: Browser Automation Rules)

---
*Phase: 06-optimize-ui-for-claude-chrome-extension-testing*
*Completed: 2026-03-13*

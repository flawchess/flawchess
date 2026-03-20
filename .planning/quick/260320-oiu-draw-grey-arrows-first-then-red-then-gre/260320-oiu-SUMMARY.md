---
phase: quick
plan: 260320-oiu
subsystem: ui
tags: [react, chessboard, svg, arrows]

requires: []
provides:
  - Arrow render ordering: grey draws first (bottom SVG layer), red second, green last (top)
  - Exported color constants from arrowColor.ts for external comparisons
affects: [ChessBoard, ArrowOverlay, arrowColor]

tech-stack:
  added: []
  patterns:
    - "Color priority map (Record<string, number>) to drive SVG render order"
    - "Immutable sort via [...arrows].sort() to avoid mutating React props"

key-files:
  created: []
  modified:
    - frontend/src/lib/arrowColor.ts
    - frontend/src/components/board/ChessBoard.tsx

key-decisions:
  - "Priority map keyed by exact oklch strings: grey/grey_hover=0, red/red_hover=1, green/green_hover=2"
  - "Unknown colors default to priority 0 via nullish coalescing — safe fallback"

patterns-established:
  - "Arrow z-order controlled by sort order, not explicit z-index — SVG painters model"

requirements-completed: []

duration: 5min
completed: 2026-03-20
---

# Quick Task 260320-oiu: Draw Grey Arrows First Then Red Then Green Summary

**Arrow render ordering fixed: grey drawn first (bottom), red second, green last (top) — win/loss arrows are never hidden beneath neutral grey arrows.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T16:10:00Z
- **Completed:** 2026-03-20T16:15:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Exported GREEN, RED, GREY and their hover variants from `arrowColor.ts` so other modules can compare color identity
- Added `ARROW_COLOR_PRIORITY` map in `ChessBoard.tsx` mapping each color constant to a render tier (0/1/2)
- Sorted arrows with `[...arrows].sort()` in `ArrowOverlay` before rendering — grey first, green last
- TypeScript compiles cleanly and production build passes

## Task Commits

1. **Task 1: Export color constants and sort arrows by render priority** - `69d2bab` (feat)

## Files Created/Modified

- `frontend/src/lib/arrowColor.ts` - Added `export` keyword to GREEN, RED, GREY, GREEN_HOVER, RED_HOVER, GREY_HOVER constants
- `frontend/src/components/board/ChessBoard.tsx` - Imported color constants, added ARROW_COLOR_PRIORITY map, sorted arrows before rendering

## Decisions Made

- Priority map keyed by exact oklch strings matches getArrowColor output precisely; no string parsing needed
- Unknown colors fall back to priority 0 (grey tier) via nullish coalescing — safe for any future custom colors

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Arrow layer ordering is now deterministic. Any future arrow color additions should be added to `ARROW_COLOR_PRIORITY` in `ChessBoard.tsx` to maintain correct render order.

---
*Phase: quick*
*Completed: 2026-03-20*

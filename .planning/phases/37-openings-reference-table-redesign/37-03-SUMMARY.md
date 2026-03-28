---
phase: 37-openings-reference-table-redesign
plan: "03"
subsystem: ui
tags: [react, typescript, radix-ui, react-chessboard, tanstack-query, tailwind]

requires:
  - phase: 37-02
    provides: "Backend endpoint with filter params, OpeningWDL schema with pgn/fen fields"

provides:
  - "MostPlayedOpeningsTable component: dedicated table UI with ECO/name/PGN columns, game count link, mini WDL bars"
  - "MinimapPopover component: hover/tap Radix popover with static Chessboard showing opening position"
  - "useMostPlayedOpenings hook: accepts filter params (recency, timeControls, platforms, rated, opponentType)"
  - "API client getMostPlayedOpenings: passes filter params to backend"
  - "OpeningWDL type: pgn and fen fields added"

affects:
  - openings-statistics-tab
  - most-played-openings

tech-stack:
  added: []
  patterns:
    - "MinimapPopover follows info-popover.tsx Radix Popover pattern: controlled open state, hover timeout, Portal, onMouseEnter/Leave on both trigger and content"
    - "MostPlayedOpeningsTable uses CSS grid-cols-[1fr_auto_minmax(80px,120px)] for compact 3-column layout"
    - "MiniWDLBar uses inline div segments with WDL_WIN/WDL_DRAW/WDL_LOSS from theme.ts and GLASS_OVERLAY"

key-files:
  created:
    - frontend/src/components/stats/MinimapPopover.tsx
    - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
  modified:
    - frontend/src/types/stats.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/pages/Openings.tsx

key-decisions:
  - "arePiecesDraggable not a valid prop in react-chessboard v5 — omitted, static board achieved by absence of onPieceDrop/onSquareClick handlers"
  - "MIN_PCT_FOR_LABEL = 15: threshold for showing percent label inside WDL bar segment (avoids cramped text)"
  - "MostPlayedOpeningsTable replaces WDLChartRow mapping blocks in statisticsContent; maxTotalWhite/maxTotalBlack removed as no longer needed"
  - "Filter params now passed from debouncedFilters to useMostPlayedOpenings so Statistics subtab openings react to filter changes"

requirements-completed: [ORT-04, ORT-05]

duration: 4min
completed: 2026-03-28
---

# Phase 37 Plan 03: Most Played Openings Frontend Redesign Summary

**Dedicated table UI replacing WDLChartRow bars: ECO/name/PGN columns, mini WDL bars, minimap popover on hover/tap, filter-aware results**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T19:54:45Z
- **Completed:** 2026-03-28T19:58:07Z
- **Tasks:** 1 of 2 (Task 2 is checkpoint:human-verify — awaiting user approval)
- **Files modified:** 6

## Accomplishments
- Created `MostPlayedOpeningsTable` component with 3-column grid layout: opening info (ECO + name + PGN), game count with folder icon link, mini WDL bar
- Created `MinimapPopover` component using Radix Popover with 150ms hover delay, Portal, and static 180px Chessboard
- Updated `useMostPlayedOpenings` hook to accept and propagate all filter params (recency, timeControls, platforms, rated, opponentType) to the backend
- Replaced `WDLChartRow` mappings in `statisticsContent` with `MostPlayedOpeningsTable`, removed obsolete `maxTotalWhite/maxTotalBlack` computations
- `OpeningWDL` type updated with `pgn` and `fen` fields to match Wave 2 backend schema

## Task Commits

1. **Task 1: Update types/API/hook, create MinimapPopover and MostPlayedOpeningsTable, wire into Openings page** - `f2c0ec4` (feat)

## Files Created/Modified
- `frontend/src/types/stats.ts` — Added `pgn: string` and `fen: string` to `OpeningWDL` interface
- `frontend/src/api/client.ts` — `getMostPlayedOpenings` now accepts filter params object
- `frontend/src/hooks/useStats.ts` — `useMostPlayedOpenings` accepts filter params, query key includes all filter values
- `frontend/src/components/stats/MinimapPopover.tsx` — New: Radix Popover wrapping Chessboard for opening position preview
- `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` — New: Table with ECO/name/PGN, game count, mini WDL bar per row
- `frontend/src/pages/Openings.tsx` — Wired MostPlayedOpeningsTable, pass debouncedFilters to useMostPlayedOpenings

## Decisions Made
- `arePiecesDraggable` is not a prop in react-chessboard v5 (API uses `options.onPieceDrop` absence for static boards) — omitted, static board is achieved by not providing interaction handlers
- `MIN_PCT_FOR_LABEL = 15` constant extracted for mini WDL bar label display threshold

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed invalid `arePiecesDraggable={false}` prop from MinimapPopover**
- **Found during:** Task 1 (MinimapPopover creation)
- **Issue:** Plan acceptance criteria listed `arePiecesDraggable={false}` but react-chessboard v5 uses `options` wrapper API with no such prop — TypeScript would reject it
- **Fix:** Omitted the prop; static board achieved by absence of `onPieceDrop`/`onSquareClick` handlers in options
- **Files modified:** frontend/src/components/stats/MinimapPopover.tsx
- **Verification:** `npm run build` passes with no TypeScript errors
- **Committed in:** f2c0ec4 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — invalid prop for react-chessboard v5 API)
**Impact on plan:** Fix essential for TypeScript correctness. Functionally identical result (static non-interactive board).

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Frontend redesign complete, awaiting user visual verification (Task 2 checkpoint)
- Upon approval, plan 37-03 is fully complete and Phase 37 is done

## Self-Check: PASSED
- `frontend/src/components/stats/MinimapPopover.tsx` — FOUND
- `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` — FOUND
- Commit `f2c0ec4` — FOUND (git log confirms)

---
*Phase: 37-openings-reference-table-redesign*
*Completed: 2026-03-28*

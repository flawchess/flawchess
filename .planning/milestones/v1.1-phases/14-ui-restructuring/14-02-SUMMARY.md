---
phase: 14-ui-restructuring
plan: 02
subsystem: ui
tags: [react, typescript, tanstack-query, routing, shadcn-tabs, chess]

# Dependency graph
requires:
  - phase: 14-01
    provides: useDebounce hook, usePositionAnalysisQuery hook, /openings/* wildcard route
  - phase: 13-frontend-move-explorer-component
    provides: MoveExplorer component, ChessBoard component, BoardControls, MoveList
provides:
  - Tabbed OpeningsPage hub at /openings/* with shared sidebar and 3 URL-based sub-tabs
  - Move Explorer tab with auto-fetch next moves and board arrows
  - Games tab with auto-fetch position analysis, WDLBar, GameCardList
  - Statistics tab with auto-fetch time series, WDLBarChart, WinRateChart
  - Filter state persistence across tab switches (UIRS-02)
  - Board position persistence across tab switches
  - /openings redirects to /openings/explorer
affects: [15-consolidation, openings-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All shared state in OpeningsPage parent (never inside TabsContent) for tab-switch persistence"
    - "useDebounce(filters, 300) for query keys only; raw filters for UI display"
    - "URL-based tab routing: activeTab derived from location.pathname, navigate() on tab switch"
    - "Early return <Navigate> for /openings bare path redirect before Tabs render"
    - "gamesOffset resets to 0 on tab switch via prevTab comparison"

key-files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx

key-decisions:
  - "Tabs rendered in both desktop (grid) and mobile (single-column) sections with identical content — avoids conditional rendering complexity with shared state"
  - "No positionFilterActive gating on Games tab — usePositionAnalysisQuery always auto-fetches from initial position"
  - "boardArrows computed in parent component so they update with tab switches and reflect current Move Explorer data"
  - "timeSeriesRequest built inline with useMemo driven by bookmarks + debouncedFilters — no manual trigger needed"

patterns-established:
  - "OpeningsPage parent holds all shared state: chess game, filters, boardFlipped, gamesOffset, bookmarks"
  - "Tab content is JSX variables defined before the return statement for reuse in mobile/desktop layouts"

requirements-completed: [UIRS-01, UIRS-02]

# Metrics
duration: 2min
completed: 2026-03-17
---

# Phase 14 Plan 02: OpeningsPage Tabbed Hub Summary

**Tabbed OpeningsPage hub with URL-based /openings/explorer|games|statistics routing, shared sidebar board+filters, auto-fetch on all three sub-tabs via useNextMoves, usePositionAnalysisQuery, and useTimeSeries**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-16T23:22:20Z
- **Completed:** 2026-03-16T23:24:10Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Complete rewrite of `frontend/src/pages/Openings.tsx` from a Statistics-only page (264 lines) to a full tabbed hub (480 lines)
- All shared state (chess game, filters, board flip, bookmarks, pagination) lives in OpeningsPage parent — survives tab switches without reset
- Three URL-based sub-tabs: Move Explorer auto-fetches `useNextMoves`, Games auto-fetches `usePositionAnalysisQuery`, Statistics auto-fetches `useTimeSeries`
- `/openings` bare path redirects to `/openings/explorer` via early-return `<Navigate>`
- Eliminated old `StatsFilters` type, `handleAnalyze` button, `positionFilterActive` gating, and `btn-filter`/`openings-btn-analyze` elements

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite OpeningsPage as tabbed hub with sidebar and 3 sub-tabs** - `ecea9de` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `frontend/src/pages/Openings.tsx` - Full rewrite: tabbed hub with shared sidebar + 3 sub-tabs (Move Explorer, Games, Statistics) using URL-based routing

## Decisions Made
- Tabs are rendered in both the desktop grid layout and mobile single-column layout as separate JSX instances referencing shared content variables (`moveExplorerContent`, `gamesContent`, `statisticsContent`). The desktop Tabs includes `data-testid="openings-tabs"` per the spec; the mobile Tabs omits it to avoid duplicate testids.
- All three tab contents are always computed (hooks called unconditionally in parent) — this is required by React's rules of hooks and also ensures data is ready when switching tabs.
- `gamesOffset` resets to 0 when tab switches are detected (via `prevTab`/`setPrevTab` comparison before render) to avoid stale pagination state.
- `boardArrows` computed in parent via `useMemo` so arrow state correctly reflects the `hoveredMove` value and persists when switching away from and back to Move Explorer tab.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TypeScript compiled cleanly, production build succeeded, all 278 backend tests passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 14 is now complete (2/2 plans done)
- Phase 15 (Consolidation) can proceed: remove Dashboard.tsx, ImportModal.tsx, unused hooks; rename endpoints/modules; update CLAUDE.md and README.md
- The old `DashboardPage` is still present (preserved per Phase 14 plan instructions) — Phase 15 should remove it

## Self-Check: PASSED
- `frontend/src/pages/Openings.tsx` — exists
- `14-02-SUMMARY.md` — exists
- Commit `ecea9de` — verified in git log

---
*Phase: 14-ui-restructuring*
*Completed: 2026-03-17*

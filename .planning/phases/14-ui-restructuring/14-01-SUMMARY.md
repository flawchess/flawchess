---
phase: 14-ui-restructuring
plan: 01
subsystem: ui
tags: [react, typescript, tanstack-query, routing, import]

# Dependency graph
requires:
  - phase: 13-frontend-move-explorer-component
    provides: Dashboard and ImportModal component patterns used as reference
provides:
  - Dedicated Import page at /import with platform rows, sync/add flow, and delete all games
  - Updated App routing with Import | Openings | Rating | Global Stats navigation
  - ImportProgress lifted to App level for global toast coverage across all pages
  - useDebounce hook for filter state debouncing
  - usePositionAnalysisQuery hook using useQuery for auto-fetch position analysis
  - /openings/* wildcard route for Plan 02 tabbed hub
affects: [14-02, openings-page, filter-state]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ImportProgress at App level (AppRoutes) to track jobs from any page
    - isActive() helper for prefix-based nav active state (/openings/*)
    - useQueryClient in AppRoutes for cache invalidation on job completion

key-files:
  created:
    - frontend/src/pages/Import.tsx
    - frontend/src/hooks/useDebounce.ts
  modified:
    - frontend/src/App.tsx
    - frontend/src/hooks/useAnalysis.ts

key-decisions:
  - "ImportProgress rendered outside Routes in AppRoutes fragment so toasts fire from any page"
  - "isActive() helper uses startsWith('/openings') for prefix matching the /openings/* wildcard"
  - "Import page does not close/navigate on sync — user stays on page and sees progress toast inline"
  - "usePositionAnalysisQuery uses queryKey ['positionAnalysis', targetHash, filters, offset, limit] for proper cache keying"

patterns-established:
  - "Global job state: activeJobIds/handleImportStarted/handleJobDone pattern in AppRoutes"
  - "handleJobDone invalidates ['games'], ['gameCount'], ['userProfile'] query keys"

requirements-completed: [UIRS-03, UIRS-04]

# Metrics
duration: 20min
completed: 2026-03-17
---

# Phase 14 Plan 01: Routing Foundation and Import Page Summary

**Dedicated Import page at /import with platform sync rows and delete-games, ImportProgress lifted to App level, and useDebounce/usePositionAnalysisQuery hooks for Plan 02**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-16T23:00:00Z
- **Completed:** 2026-03-16T23:19:26Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created `Import.tsx` as a full-page replacement for the import modal, with platform rows (sync/add flow), inline progress, and Delete All Games section
- Updated `App.tsx`: new nav order (Import | Openings | Rating | Global Stats), `/openings/*` wildcard route, `/` redirects to `/openings`, `ImportProgress` lifted to App level
- Added `useDebounce` and `usePositionAnalysisQuery` hooks required by Plan 02

## Task Commits

Each task was committed atomically:

1. **Task 1: Create useDebounce hook and usePositionAnalysisQuery hook** - `9cac7e8` (feat)
2. **Task 2: Create Import page and update App routing/navigation** - `99dd7e5` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `frontend/src/pages/Import.tsx` - Dedicated import page with platform rows, sync/add, delete all games, data-testids
- `frontend/src/App.tsx` - Updated routing, navigation, lifted ImportProgress to AppRoutes level
- `frontend/src/hooks/useDebounce.ts` - Generic debounce hook
- `frontend/src/hooks/useAnalysis.ts` - Added usePositionAnalysisQuery using useQuery with positionAnalysis key

## Decisions Made
- ImportProgress rendered outside the `<Routes>` block in AppRoutes so it persists on every page transition; the floating toast component just needs to be mounted.
- `isActive()` helper correctly handles the `/openings/*` prefix — without it the active nav underline would never appear on sub-routes like `/openings/games`.
- Import page stays open after sync/import start (unlike the modal which closed). User sees progress feedback inline via ImportProgress toasts.
- `usePositionAnalysisQuery` uses `useQuery` (not `useMutation`) so Plan 02 can auto-fetch when position/filters change without manual trigger.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TypeScript compiled cleanly, production build succeeded, all 278 backend tests passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can now build the OpeningsPage tabbed hub on top of `/openings/*` route
- `useDebounce` and `usePositionAnalysisQuery` are available for the Openings tab components
- `DashboardPage` and `ImportModal` files preserved (not deleted) per plan instructions — cleanup in Phase 15

---
*Phase: 14-ui-restructuring*
*Completed: 2026-03-17*

---
phase: 104-library-page-shell-import-overview-subtab-migration
plan: 01
subsystem: ui
tags: [react, typescript, react-router, tabs, library-page]

# Dependency graph
requires: []
provides:
  - LibraryPage shell with state-dependent Navigate and Tabs variant=brand (desktop + mobile)
  - ImportTab subtab wrapper forwarding job-tracking props to ImportPage
  - OverviewTab zero-prop subtab wrapper rendering GlobalStatsPage
  - ImportPageProps exported from Import.tsx for downstream imports
affects:
  - 104-02 (App.tsx router + nav wiring consumes LibraryPage, ImportTab, OverviewTab)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LibraryPage mirrors Endgames.tsx two-subtab URL-routed Tabs pattern exactly"
    - "Thin subtab wrappers (ImportTab, OverviewTab) forward to existing page components without moving them"
    - "State-dependent page-level Navigate: noGames -> /library/import, has-games -> /library/overview"

key-files:
  created:
    - frontend/src/pages/library/LibraryPage.tsx
    - frontend/src/pages/library/ImportTab.tsx
    - frontend/src/pages/library/OverviewTab.tsx
  modified:
    - frontend/src/pages/Import.tsx

key-decisions:
  - "ImportPageProps exported from Import.tsx so ImportTab can import the type rather than re-declare it (D-14)"
  - "State-dependent redirect gated on profile != null to avoid momentary redirect before profile loads"
  - "Thin-wrap pattern: ImportTab/OverviewTab delegate to ImportPage/GlobalStatsPage, preserving import-page/global-stats-page testids"

patterns-established:
  - "Subtab wrapper pattern: import existing page component, forward props as-is, no structural change to wrapped page"

requirements-completed: [LIB-02, LIB-03, LIB-04, LIB-07, LIB-08, LIB-09]

# Metrics
duration: 2min
completed: 2026-06-05
---

# Phase 104 Plan 01: Library Page Shell + Import & Overview Subtab Migration Summary

**LibraryPage shell with Endgames-style two-subtab Tabs, state-dependent /library redirect, and thin ImportTab/OverviewTab wrappers delegating to existing page components**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-06-05T07:51:23Z
- **Completed:** 2026-06-05T07:53:12Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Exported `ImportPageProps` from `Import.tsx` for downstream consumption by `ImportTab`
- Created `ImportTab.tsx`: thin wrapper forwarding three job-tracking props to `ImportPage`, preserving the `import-page` testid and full import workflow
- Created `OverviewTab.tsx`: zero-prop wrapper delegating to `GlobalStatsPage`, preserving `global-stats-page` testid and SidebarLayout/FilterPanel behavior
- Created `LibraryPage.tsx`: Endgames-style two-subtab shell with state-dependent `/library` redirect (noGames -> `/library/import`, has-games -> `/library/overview`), desktop Tabs + mobile sticky subnav, all required testids, and both ImportTab instances receiving the three job-tracking props

## Task Commits

1. **Task 1: Create ImportTab + OverviewTab subtab wrappers, export ImportPageProps** - `5f218bb2` (feat)
2. **Task 2: Create LibraryPage shell with state-dependent default subtab, desktop + mobile tabs, prop threading** - `7728e79d` (feat)

## Files Created/Modified
- `frontend/src/pages/library/LibraryPage.tsx` - Library page shell: state-dependent Navigate, desktop + mobile Tabs variant=brand, all required testids (library-page, library-tabs, library-tabs-mobile, library-mobile-control-row, tab-import, tab-overview, tab-import-mobile, tab-overview-mobile), prop forwarding to both ImportTab instances
- `frontend/src/pages/library/ImportTab.tsx` - Thin wrapper importing ImportPage and ImportPageProps, forwarding all three job-tracking props
- `frontend/src/pages/library/OverviewTab.tsx` - Zero-prop wrapper rendering GlobalStatsPage
- `frontend/src/pages/Import.tsx` - Added `export` keyword to `ImportPageProps` interface (line 51); no other change

## Decisions Made
- Gated state-dependent redirect on `profile != null` to avoid a momentary flash redirect before the profile is loaded, matching how Openings/Endgames handle their page-level Navigate
- Used `import type { ImportPageProps }` in ImportTab so the interface is not re-declared, satisfying the type-import pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three new files (`LibraryPage.tsx`, `ImportTab.tsx`, `OverviewTab.tsx`) compile and lint clean
- `ImportPageProps` is now exported, enabling Plan 02's App.tsx wiring to import it for prop threading
- Plan 02 can now repoint the router (`/library/*`) and nav at `LibraryPage`, add old-route redirects, update nav items, and move the notification dot

## Self-Check: PASSED

- FOUND: frontend/src/pages/library/LibraryPage.tsx
- FOUND: frontend/src/pages/library/ImportTab.tsx
- FOUND: frontend/src/pages/library/OverviewTab.tsx
- FOUND: .planning/phases/104-library-page-shell-import-overview-subtab-migration/104-01-SUMMARY.md
- FOUND commit: 5f218bb2 (Task 1)
- FOUND commit: 7728e79d (Task 2)

---
*Phase: 104-library-page-shell-import-overview-subtab-migration*
*Completed: 2026-06-05*

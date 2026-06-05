---
phase: 104-library-page-shell-import-overview-subtab-migration
plan: 02
subsystem: ui
tags: [react, typescript, react-router, nav, library-page, routing]

# Dependency graph
requires:
  - 104-01 (LibraryPage shell with ImportTab/OverviewTab subtab wrappers)
provides:
  - Library nav item (FolderOpen) replacing Import + Overview in all three nav surfaces
  - /library/* route in App.tsx carrying job-tracking props to LibraryPage
  - Old-route redirects: /import->/library/import, /overview,/rating,/global-stats->/library/overview
  - Notification dot moved to Library nav item (all three surfaces)
  - ImportRequiredRoute redirect target repointed to /library/import
  - Internal Import-Games links swept to /library/import
affects:
  - consumers of nav-import/nav-overview testids (retired; use nav-library instead)
  - consumers of import-notification-dot testid (renamed to library-notification-dot)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Nav items array replaced wholesale: Library leftmost, Openings, Endgames (no Import/Overview)"
    - "isActive helper extended with /library prefix branch"
    - "MobileMoreDrawer notification dot is net-new (no analog in prior code)"
    - "Old routes kept as Navigate redirects for backward compatibility"

key-files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/Home.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/openings/GamesTab.tsx

key-decisions:
  - "FolderOpen icon from lucide-react used for Library nav item per D-01"
  - "NAV_ITEMS reduced from 4 to 3 entries (Library, Openings, Endgames)"
  - "/library route NOT wrapped in ImportRequiredRoute per D-08"
  - "noGames derivation added inline to MobileMoreDrawer for net-new drawer dot"
  - "DownloadIcon and LayoutDashboard removed from App.tsx lucide import (no longer used there)"

# Metrics
duration: 4min
completed: 2026-06-05
---

# Phase 104 Plan 02: Router + Nav Rewire Summary

**Top-level nav consolidated to Library (FolderOpen) · Openings · Endgames; full route migration and link sweep completed with all gates clean**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-05T07:56:56Z
- **Completed:** 2026-06-05T08:01:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Updated `NAV_ITEMS` and `BOTTOM_NAV_ITEMS` to `[Library (FolderOpen), Openings, Endgames]` — dropped standalone Import and Overview entries from both
- Added `FolderOpen` to lucide-react import; removed unused `DownloadIcon` and `LayoutDashboard` from App.tsx
- Added `import { LibraryPage }` from `@/pages/library/LibraryPage`; removed dead `ImportPage` and `GlobalStatsPage` imports
- Extended `isActive` helper with `/library` prefix branch
- Updated `ROUTE_TITLES` (added `/library: 'Library'`, dropped `/import` and `/overview`)
- Updated nav-lock exemption in all three nav surfaces: `to !== '/import'` → `to !== '/library'`
- Moved notification dot from `/import` to `/library` in NavHeader (testid `library-notification-dot`) and MobileBottomBar (testid `library-notification-dot-mobile`)
- Added net-new notification dot to MobileMoreDrawer (testid `library-notification-dot-drawer`) with `noGames` derivation added inline
- Added `/library/*` route carrying job-tracking props to LibraryPage (not import-gated)
- Added redirect routes: `/import` → `/library/import`; `/overview`, `/rating`, `/global-stats` → `/library/overview`
- Repointed `ImportRequiredRoute` redirect target to `/library/import`
- Swept `Home.tsx` gameless redirect to `/library/import` (has-games stays `/openings`)
- Swept `Endgames.tsx:711` and `openings/GamesTab.tsx:49` `<Link to="/import">` to `/library/import`

## Task Commits

1. **Task 1: Rewire App.tsx nav config, routes, redirects, guard, and notification dot** - `21706979` (feat)
2. **Task 2: Sweep internal Import-Games links to /library/import** - `5407a9c5` (feat)

## Files Created/Modified

- `frontend/src/App.tsx` - NAV_ITEMS/BOTTOM_NAV_ITEMS consolidated to Library+Openings+Endgames; isActive extended; ROUTE_TITLES updated; nav-lock exemptions updated (×3 surfaces); notification dot moved to Library (×2 surfaces + net-new drawer dot); /library/* route added; old-route redirects added; ImportRequiredRoute guard repointed; dead imports removed
- `frontend/src/pages/Home.tsx` - Gameless redirect `/import` → `/library/import`
- `frontend/src/pages/Endgames.tsx` - `<Link to="/import">` → `/library/import` (line 711)
- `frontend/src/pages/openings/GamesTab.tsx` - `<Link to="/import">` → `/library/import` (line 49)

## Decisions Made

- Removed `DownloadIcon` and `LayoutDashboard` from App.tsx's lucide import — they were only referenced in the old NAV_ITEMS entries and are no longer used directly in App.tsx (they remain used in LibraryPage.tsx)
- Used `relative` className on the MobileMoreDrawer `<Link>` to properly position the notification dot span within the link element

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Threat Surface Scan

No new security-relevant surface introduced. All changes are client-side React Router reconfiguration with static `<Navigate>` redirects (no user-controlled input, no new endpoints). T-104-03 mitigated: `/openings/*` and `/endgames/*` confirmed still wrapped in `ImportRequiredRoute`; `/admin` still in `SuperuserRoute`; `/library` intentionally ungated per D-08.

## Verification Results

- `npx tsc --noEmit`: clean (0 errors)
- `npm run knip`: clean (no new unused exports/imports)
- `npm run lint`: clean (0 errors)
- `npm test -- --run`: 744 tests passed (63 test files)

## User Setup Required

None.

## Self-Check: PASSED

- FOUND: frontend/src/App.tsx (modified — NAV_ITEMS contains `/library`, no `/import`/`/overview`)
- FOUND: frontend/src/pages/Home.tsx (modified — `/library/import` redirect)
- FOUND: frontend/src/pages/Endgames.tsx (modified — `/library/import` link)
- FOUND: frontend/src/pages/openings/GamesTab.tsx (modified — `/library/import` link)
- FOUND commit: 21706979 (Task 1)
- FOUND commit: 5407a9c5 (Task 2)

---
*Phase: 104-library-page-shell-import-overview-subtab-migration*
*Completed: 2026-06-05*

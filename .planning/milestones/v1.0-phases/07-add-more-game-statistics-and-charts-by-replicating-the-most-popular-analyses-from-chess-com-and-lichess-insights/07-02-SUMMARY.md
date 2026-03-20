---
phase: 07-add-more-game-statistics-and-charts
plan: 02
subsystem: ui
tags: [react, typescript, react-router, navigation]

# Dependency graph
requires:
  - phase: 05-position-bookmarks-and-wdl-charts
    provides: Stats page with bookmark-based analysis charts
provides:
  - 5-item navigation (Games, Bookmarks, Openings, Rating, Global Stats)
  - /openings route serving full bookmark analysis functionality (renamed from /stats)
  - /rating and /global-stats placeholder routes
  - /stats redirect to /openings for backward compatibility
affects: [07-03-game-statistics-charts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "data-testid hyphen normalization: label.toLowerCase().replace(/\\s+/g, '-') handles multi-word nav labels"

key-files:
  created:
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/Rating.tsx
    - frontend/src/pages/GlobalStats.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "data-testid hyphen normalization for multi-word labels: 'Global Stats' -> nav-global-stats via replace(/\\s+/g, '-')"
  - "Stats.tsx kept as dead code (not deleted) — will be removed in a cleanup step at end of phase"

patterns-established:
  - "Nav data-testid normalization: always replace whitespace with hyphens for multi-word labels"

requirements-completed: [STATS-01, STATS-02]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 7 Plan 2: Navigation Restructure Summary

**5-item navigation with renamed Openings page (was Stats) and placeholder Rating/GlobalStats routes using hyphen-normalized data-testid attributes**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T09:24:57Z
- **Completed:** 2026-03-14T09:27:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Expanded navigation from 3 to 5 items: Games, Bookmarks, Openings, Rating, Global Stats
- Renamed Stats page to Openings with all existing functionality preserved
- Added placeholder pages for Rating and Global Stats with proper data-testid attributes
- Fixed data-testid generation to handle multi-word nav labels correctly

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename Stats to Openings and create placeholder pages** - `5409161` (feat)
2. **Task 2: Update App.tsx navigation and routes** - `849bcd9` (feat)

## Files Created/Modified
- `frontend/src/pages/Openings.tsx` - Full copy of Stats.tsx with renamed exports (OpeningsPage), h1 "Openings", data-testid="openings-page", data-testid="openings-btn-analyze"
- `frontend/src/pages/Rating.tsx` - Minimal placeholder page with data-testid="rating-page"
- `frontend/src/pages/GlobalStats.tsx` - Minimal placeholder page with data-testid="global-stats-page"
- `frontend/src/App.tsx` - Updated NAV_ITEMS (5 items), fixed data-testid normalization, updated routes and imports

## Decisions Made
- `data-testid` hyphen normalization: changed `label.toLowerCase()` to `label.toLowerCase().replace(/\s+/g, '-')` so "Global Stats" produces `nav-global-stats` (not `nav-global stats` with a space)
- Stats.tsx left as dead code for reference during this phase; will be cleaned up later

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing ESLint `react-refresh/only-export-components` errors in shadcn/ui component files (tabs.tsx, toggle.tsx) — out of scope, not introduced by this plan. All plan-modified files pass lint with zero warnings.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Route structure is set up; plan 07-03 can implement Rating page (rating over time charts) and plan 07-04 can implement Global Stats page
- No blockers

---
*Phase: 07-add-more-game-statistics-and-charts*
*Completed: 2026-03-14*

---
phase: quick
plan: 260321-ftk
subsystem: frontend
tags: [ui, navigation, openings, tabs]
dependency_graph:
  requires: []
  provides: [renamed-compare-tab, renamed-statistics-nav, desktop-nav-icons]
  affects: [frontend/src/pages/Openings.tsx, frontend/src/App.tsx, frontend/src/pages/GlobalStats.tsx]
tech_stack:
  added: []
  patterns: [lucide-react icons in tabs and nav]
key_files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx
    - frontend/src/App.tsx
    - frontend/src/pages/GlobalStats.tsx
decisions:
  - Added /openings/statistics -> /openings/compare redirect for backward-compat URL stability
metrics:
  duration: ~10 minutes
  completed: 2026-03-21
---

# Quick Task 260321-ftk: Rename Statistics Sub-tab to Compare Summary

**One-liner:** Renamed Openings sub-tab "Statistics" -> "Compare" and top-level nav "Global Stats" -> "Statistics", added icons to desktop nav and Openings tabs matching mobile bottom nav.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rename tabs and add desktop nav icons | bf9009b | Openings.tsx, App.tsx, GlobalStats.tsx |

## What Was Built

**Openings.tsx:**
- Renamed "Statistics" sub-tab to "Compare" on both desktop and mobile TabsTriggers
- Updated tab value from `"statistics"` to `"compare"` throughout (TabsTrigger, TabsContent, activeTab routing)
- Added backward-compat redirect: `/openings/statistics` -> `/openings/compare`
- Added icons to all three sub-tabs: ListTree (Moves), Gamepad2 (Games), BarChartHorizontal (Compare)
- Updated data-testid: `tab-statistics` -> `tab-compare`, `tab-statistics-mobile` -> `tab-compare-mobile`
- Updated comment references from "Statistics tab charts" -> "Compare tab charts"

**App.tsx:**
- Added `Icon` property to `NAV_ITEMS` (DownloadIcon, LayoutGridIcon, BarChart3Icon)
- Renamed "Global Stats" -> "Statistics" in NAV_ITEMS, BOTTOM_NAV_ITEMS, and ROUTE_TITLES
- Updated NavHeader to render `<Icon className="mr-1.5 h-4 w-4" />` before each nav label

**GlobalStats.tsx:**
- Renamed page `<h1>` from "Global Stats" to "Statistics"

## Deviations from Plan

**1. [Rule 2 - Missing feature] Added backward-compat redirect for /openings/statistics**
- **Found during:** Task 1
- **Issue:** The old URL `/openings/statistics` would silently fall through to the explorer tab after the rename. Any bookmarked or linked URL would silently show the wrong tab.
- **Fix:** Added `needsStatisticsRedirect` guard that returns `<Navigate to="/openings/compare" replace />` when pathname ends with `/statistics`
- **Files modified:** frontend/src/pages/Openings.tsx
- **Commit:** bf9009b (included in task commit)

## Self-Check: PASSED

- frontend/src/pages/Openings.tsx: modified, committed in bf9009b
- frontend/src/App.tsx: modified, committed in bf9009b
- frontend/src/pages/GlobalStats.tsx: modified, committed in bf9009b
- TypeScript: compiles with no errors
- Build: succeeded (3.66s)

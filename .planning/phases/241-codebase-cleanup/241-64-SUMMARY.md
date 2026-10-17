---
phase: 241-codebase-cleanup
plan: 64
subsystem: frontend
tags: [naming, refactor, openings, hooks]
requires: [241-02, 241-03, 241-04, 241-31, 241-41]
provides: ["precise names for Openings opening field, mobile drawer state, stale-time constants, array locals"]
affects: [frontend/src/pages/Openings.tsx, frontend/src/pages/openings, frontend/src/hooks]
tech-stack:
  added: []
  patterns: ["unit suffix on duration constants (_MS)", "plural names for array-valued locals"]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-64.tsv
  modified:
    - frontend/src/hooks/useChessGame.ts
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx
    - frontend/src/pages/openings/useSidebarState.ts
    - frontend/src/pages/openings/OpeningsMobileDrawers.tsx
    - frontend/src/pages/openings/useOpeningsChartData.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/hooks/useOpeningInsights.ts
key-decisions:
  - "The three same-family drawer props outside the INVENTORY row's list were renamed too (planner assumption honored)"
requirements-completed: [D-06, D-07, D-17]
status: complete
commits: 6
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 726232e70a15c59d9809ac4b7d73b77aceea66cf
actuals:
  tokens: 6000
  tasks: 3
  commits: 6
duration: 12 min
completed: 2026-10-16
---

# Phase 241 Plan 64: Openings family and data-hook renames Summary

Six INVENTORY §5 renames in the Openings page family and four data hooks, one `refactor(naming)` commit each, behavior unchanged (renames only, no testid / localStorage key / API param change).

## Renames

| # | Old → New | Commit | Files touched |
|---|-----------|--------|---------------|
| a | `openingName` → `opening`, `setOpeningName` → `setOpening` (+ docstring "Current opening (eco + name)") | cc952f00c | useChessGame.ts, Openings.tsx, OpeningsMobileBoardPanel.tsx |
| b | `filterSidebarOpen`/`bookmarkSidebarOpen` → `filterDrawerOpen`/`bookmarkDrawerOpen`; `setFilterSidebarOpen`/`setBookmarkSidebarOpen` → `setFilterDrawerOpen`/`setBookmarkDrawerOpen`; `openFilterSidebar`/`openBookmarkSidebar` → `openFilterDrawer`/`openBookmarkDrawer`; `handleFilterSidebarOpenChange`/`handleBookmarkSidebarOpenChange` → `handleFilterDrawerOpenChange`/`handleBookmarkDrawerOpenChange`; `onOpenFilterSidebar` → `onOpenFilterDrawer`; plus the three same-family props `onOpenBookmarkSidebar` → `onOpenBookmarkDrawer`, `onFilterSidebarOpenChange` → `onFilterDrawerOpenChange`, `onBookmarkSidebarOpenChange` → `onBookmarkDrawerOpenChange` | f4d83a9ef | Openings.tsx, OpeningsMobileBoardPanel.tsx, OpeningsMobileDrawers.tsx, useSidebarState.ts, useOpeningsChartData.ts (comment) |
| c | `justCommittedFromDrawerRef` → `justCommittedFiltersRef` | a9f967285 | Openings.tsx |
| d | `ENDGAME_STALE_TIME` → `ENDGAME_STALE_TIME_MS` | 1d2312435 | useEndgames.ts |
| e | `LIBRARY_STALE_TIME` → `LIBRARY_STALE_TIME_MS` (incl. docstring) | f07298f9b | useLibrary.ts |
| f | array locals `timeControl`/`platform` → `timeControls`/`platforms` in useMostPlayedOpenings and useOpeningInsights | 726232e70 | useStats.ts, useOpeningInsights.ts |

The three same-family drawer props that the INVENTORY row does not list WERE included in commit (b), as the plan's planner_assumptions describe. If the owner rejects that, drop `onOpenBookmarkDrawer`, `onFilterDrawerOpenChange`, `onBookmarkDrawerOpenChange` from f4d83a9ef.

Kept unchanged: desktop `sidebarOpen` / `setSidebarOpen` / `handleDesktopSidebarOpenChange`, every testid containing "sidebar" (e.g. `btn-open-bookmark-sidebar`, `drawer-filter-sidebar`), API request keys (`time_control`, `platform`), query keys, scalar `platform` in the other useStats hooks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - consistency] Four descriptive comments for the mobile drawers updated**
- **Found during:** Task 1 (b)
- **Issue:** Comments "Mobile sidebar deferred-apply local state", "Mobile sidebar handlers" (Openings.tsx) and JSX comments "Filter sidebar" / "Bookmark sidebar" (OpeningsMobileDrawers.tsx) would have contradicted the renamed drawer identifiers beside them.
- **Fix:** Reworded sidebar → drawer in those four comments only (all within files_modified).
- **Commit:** f4d83a9ef

**Total deviations:** 1 (comment wording). **Impact:** none on behavior.

## Verification

Baseline (untouched tree) and after every rename: `npm --prefix frontend run build` (tsc -b + vite) clean, `npm --prefix frontend run lint` clean, Openings and useChessGame tests (33 passed), full `src/hooks` tests (51 files, 836 passed), `source_scan_tests.sh --fe` (131 passed), `cleanup.py absent` (17 rows, 0 hits), `cleanup.py diff --plan 241-64` pass (renames only).

Environment prep: `npm ci` in frontend and `uv sync --group maia-inference` (lockfile only).

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- rename-maps/241-64.tsv present (19 data rows) and committed; all six commits are ancestors of HEAD; `git status` clean before this file.

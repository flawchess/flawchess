---
phase: 15-chart-consolidation-and-polish
plan: "01"
subsystem: stats
tags: [backend, frontend, api, charts, navigation]
dependency_graph:
  requires: []
  provides: [stats-platform-filter, global-stats-merged-page]
  affects: [frontend-navigation, stats-endpoints]
tech_stack:
  added: []
  patterns: [platform-query-param, conditional-section-rendering, platform-toggle-pills]
key_files:
  created: []
  modified:
    - app/routers/stats.py
    - app/services/stats_service.py
    - app/repositories/stats_repository.py
    - tests/test_stats_repository.py
    - tests/test_stats_router.py
    - frontend/src/api/client.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/App.tsx
    - frontend/src/hooks/usePositionBookmarks.ts
  deleted:
    - frontend/src/pages/Rating.tsx
decisions:
  - selectedPlatforms state is null (all) or a Platform[] array; single-element array maps to a platform query param in the hook
  - Platform filter toggle: clicking an active platform deselects the other, clicking the only active platform resets to null (all)
  - Rating sections conditionally rendered client-side using selectedPlatforms state; backend also filters to reduce data
metrics:
  duration: ~15 minutes
  completed_date: "2026-03-17"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 11
---

# Phase 15 Plan 01: Merge Rating into Global Stats with Platform Filter Summary

Merged Rating page into Global Stats with platform toggle pills (Chess.com/Lichess) filtering both rating history and WDL charts; removed Rating nav tab and added /rating redirect.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Backend platform filter on stats endpoints | 48bf68c | Done |
| 2 | Merge Rating into Global Stats, update nav and routing | e0983ad | Done |

## What Was Built

**Task 1 — Backend platform filter:**
- Both `/stats/rating-history` and `/stats/global` endpoints now accept `platform: str | None = Query(default=None)`
- `get_rating_history` service: when `platform="chess.com"` returns empty lichess list (avoids unnecessary DB call), and vice versa for lichess
- `get_global_stats` service: passes platform to both `query_results_by_time_control` and `query_results_by_color`
- `query_results_by_time_control` and `query_results_by_color` repository functions gain `platform: str | None = None` param with `.where(Game.platform == platform)` conditional filter
- 6 new tests added (3 repository, 3 router); all 33 tests pass

**Task 2 — Frontend merge:**
- `statsApi.getRatingHistory` and `getGlobalStats` now accept `platform: string | null` and include it in query params
- `useRatingHistory` and `useGlobalStats` hooks accept `platforms: Platform[] | null`; map single-element arrays to platform param
- `GlobalStats.tsx` rewritten: platform toggle pill buttons above recency select; Chess.com and Lichess rating sections rendered above GlobalStatsCharts; sections conditionally shown based on `selectedPlatforms` state
- `App.tsx`: Rating nav item removed (3 items: Import, Openings, Global Stats); `/rating` route redirects to `/global-stats`; `RatingPage` import removed
- `Rating.tsx` deleted

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing TypeScript error in usePositionBookmarks.ts**
- **Found during:** Task 2 (npm run build verification)
- **Issue:** `mutationFn: (id: number) => positionBookmarksApi.remove(id)` returned `Promise<AxiosResponse>` but `useMutation<void, Error, number, DeleteContext>` expected `Promise<void>`
- **Fix:** Added `.then(() => undefined)` to the `remove` call to satisfy the void return type
- **Files modified:** `frontend/src/hooks/usePositionBookmarks.ts`
- **Commit:** e0983ad (bundled with Task 2 commit)

## Self-Check: PASSED

Files verified:
- app/routers/stats.py — contains `platform: str | None = Query(default=None)` in both endpoints
- app/services/stats_service.py — `get_rating_history` and `get_global_stats` contain `platform: str | None = None`
- app/repositories/stats_repository.py — `query_results_by_time_control` and `query_results_by_color` contain `platform: str | None = None` and `Game.platform == platform`
- frontend/src/pages/GlobalStats.tsx — contains `data-testid="filter-platform-chess-com"`, `data-testid="filter-platform-lichess"`, `data-testid="rating-section-chess-com"`, `data-testid="rating-section-lichess"`, `selectedPlatforms`, imports `RatingChart`
- frontend/src/App.tsx — NAV_ITEMS has 3 entries, contains `Navigate to="/global-stats"`, no RatingPage import
- frontend/src/pages/Rating.tsx — DELETED
- Commits 48bf68c and e0983ad exist in git log

---
phase: 238-endgame-stats-percentile-first
plan: 07
subsystem: ui
tags: [react, typescript, tanstack-query, endgames, insights, filters]

requires:
  - phase: 238-04
    provides: filter-free insights backend (POST /insights/endgame and GET /insights/endgame/cached take no query params)
  - phase: 238-02
    provides: GET /api/endgames/stats (filtered per-category stats for the Games tab)
  - phase: 238-05
    provides: filter-free EndgameStatsTab and the extracted useEndgameInsightsState hook
  - phase: 238-06
    provides: retired component tree deleted
provides:
  - "useEndgameInsights() (void variables, no params) and useCachedEndgameInsights() (no args, constant key ['endgame-insights', 'cached'])"
  - "useEndgameInsightsState without a filter-store read: one report per user, latest Generate result else cached data"
  - "useEndgameStats(filters, { enabled }) + endgameApi.getStats for GET /endgames/stats; Games tab runs on it"
  - "Filter UI (desktop strip + panel, mobile Filters button + drawer) hidden on the Stats tab, applied filters untouched"
  - "SidebarLayout renders no strip when given no panels"
affects: [238-08, 238-09]

plan_head_before: cf7de02271f922cba5713261c10a2cc7d9686553
plan_head_after: 58d5eff5294902a0dacb06b243c86c75dcb43e11
actuals:
  tokens: 21000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Hiding filter UI = derive the panel list / conditionally render by activeTab, and on entering Stats reset only the open flags (never the applied-filter setter)"
    - "Page test drives tab switches with an in-test navigate button and reads the real shared filter store through a probe component"

key-files:
  created:
    - frontend/src/hooks/__tests__/useEndgameStats.test.tsx
    - frontend/src/pages/__tests__/Endgames.filterVisibility.test.tsx
  modified:
    - frontend/src/hooks/useEndgameInsights.ts
    - frontend/src/hooks/__tests__/useEndgameInsights.test.tsx
    - frontend/src/components/endgames/useEndgameInsightsState.ts
    - frontend/src/components/insights/EndgameInsightsBlock.tsx
    - frontend/src/components/insights/EndgameInsightsBubble.tsx
    - frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/layout/SidebarLayout.tsx
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/api/client.ts
    - frontend/src/types/endgames.ts
    - frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
  deleted:
    - frontend/src/lib/insightsFilters.ts
    - frontend/src/lib/insightsFilters.test.ts
    - frontend/src/hooks/__tests__/useEndgameOverview.test.tsx

key-decisions:
  - "Import-completion handling in the insights state clears the held Generate result and calls the cached query's refetch (not queryClient.invalidateQueries), because the page tests mock the hooks without a QueryClientProvider; the server already answers 404 for a report older than the latest import, so the stale report disappears"
  - "On the Stats tab SidebarLayout receives an empty panel list and, with no side content, renders only the main column (no strip, no left margin); the column widens by the strip width (planner assumption A15, UAT 238-09 checks md/lg)"
  - "The mobile stats TabsContent lost its -mt-2 (it only compensated for the sticky Filters row that no longer renders on Stats)"

patterns-established:
  - "Tab-scoped filter UI: render by activeTab, close open flags in an effect on entering the filterless tab, never call the applied-filter setter"

requirements-completed: [D-02, D-04, D-00h, D-01, D-00i]

coverage:
  - id: D1
    description: "Generate Insights sends no filter parameters, never resets page filters; one cached report per user under a constant key"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useEndgameInsights.test.tsx"
        status: pass
    human_judgment: false
  - id: D2
    description: "Filter UI hidden on Stats and restored on Games; applied filters referentially equal across a Stats round trip; open panel/drawer closed without committing the pending draft"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Endgames.filterVisibility.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Main-column width shift when the 48 px strip disappears (A15) is a visual call for UAT 238-09"
  - id: D3
    description: "Games tab reads GET /api/endgames/stats with the applied filters, keeps category stats, match label and empty states"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useEndgameStats.test.tsx"
        status: pass
      - kind: integration
        ref: "frontend/src/pages/__tests__/Endgames.filterVisibility.test.tsx#Endgames Games tab data (D-01)"
        status: pass
    human_judgment: false
  - id: D4
    description: "No frontend call to /endgames/overview and no overview-only TS types; types/endgames.ts names no retired component"
    requirement: "D-00h"
    verification:
      - kind: other
        ref: "grep for useEndgameOverview|getOverview|EndgameOverviewResponse|PerTcBreakdownOut in frontend/src returns nothing; grep -c retired names in types/endgames.ts is 0; npm run build and npm run knip clean"
        status: pass
    human_judgment: false
  - id: D5
    description: "Shelly block and per-section narration slots render as before"
    requirement: "D-00i"
    verification:
      - kind: unit
        ref: "frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx; frontend/src/components/endgames/EndgameStatsTab.test.tsx"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-10-11
status: complete
---

# Phase 238 Plan 07: Filter-free insights, Games tab on /endgames/stats, filters hidden on Stats Summary

**Shelly insights are now one cached report per user with no filter parameters, the Games tab reads the filtered `/endgames/stats` endpoint, the whole filter UI disappears on the Stats tab with the applied filters left untouched, and the overview hook, API call and overview-only TypeScript types are gone.**

## Performance

- **Duration:** about 35 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files:** 18 touched (2 created, 13 modified, 3 deleted); 2 task commits

## Accomplishments

- **Filter-free insights (D-04, Task 1 tracer).** `useEndgameInsights()` is a `useMutation<..., void>` that POSTs `/insights/endgame` with no body and no config; `useCachedEndgameInsights()` takes no argument and uses the constant key `['endgame-insights', 'cached']` with the same 404-to-null, staleTime and retry settings. `buildInsightsParams` and `lib/insightsFilters.ts` (+ test) are deleted. `EndgameInsightsBlock`'s `mutation` prop is typed with `void` variables and its comments no longer mention the filter reset.
- **Insights state file named in the handoff.** `frontend/src/components/endgames/useEndgameInsightsState.ts` (extracted in 238-05, not in this plan's `files_modified`) is where the filter-keyed cache lived. It no longer imports `useFilterStore`, `areFiltersEqual` or `toInsightsFilters`: the rendered report is the latest successful Generate result, else the cached query data; Generate never touches filters; the import-completion edge (active jobs > 0 to 0) clears the held result and refetches the cached query. `EndgameStatsTab.tsx` needed no change (it already only called `useEndgameInsightsState()`).
- **Games tab on `/endgames/stats` (D-01, Task 2).** New `endgameApi.getStats` and `useEndgameStats(filters, { enabled })` with key `['endgameOverview', 'stats', params]` (the existing import-completion invalidations in `App.tsx` / `Import.tsx` still match) and the same Tier-2 gate and staleTime. The page's `statsData`, `selectedCategoryStats`, match label and `EndgamesTailEmptyState`-equivalent branches are unchanged apart from the data source.
- **Filter visibility (D-02).** Desktop: the panel list is `[filtersPanel]` on Games and `[]` on Stats, and `SidebarLayout` now skips the strip/bar/panel when `panels` is empty and there is no `sideContent`. Mobile: the sticky Filters button and `MobileFilterDrawer` render only on Games. An effect on entering Stats calls `setSidebarOpen(null)` and `setMobileFiltersOpen(false)` only; the applied-filter setter is never called and the pending draft is never committed (RESEARCH Pitfall 5, T-238-17).
- **Retirement (D-00h).** Deleted `useEndgameOverview`, `endgameApi.getOverview`, and the overview-only types (`EndgameOverviewResponse`, `PerTcBreakdownOut`, `ScoreGapMaterialResponse`, `PerTcBucketStats`, `EndgameMetricsTcCard`, `EndgameMetricsCardsResponse`, `TimePressureTcCard`, `TimePressureCardsResponse`, `ClockGapBullet`, `EndgamePerformanceResponse`, `EndgameTimelineResponse`, `EndgameTimelinePoint`, `EndgameOverallPoint`, `MaterialRow`, `ClockDiffTimelineResponse`). Kept: `EndgameEloTimelineResponse`, `ClockDiffTimelinePoint`, `ScoreGapTimelinePoint`, `PressureQuintileBullet`, `EndgameCategoryStats`, `RatingAnchorOut`, `EndgameStatsResponse`, `EndgameWDLSummary`, `MaterialBucket`. The `score_p_value` comment now cites TypeTable (and says the field is not rendered), the `RatingAnchorOut` doc says "ranked-metric popover", and no surviving comment names a retired component. `MiniBulletChart` is untouched.
- **Gates.** `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip` clean; full `npm test -- --run` 318 files / 5337 tests pass.

## Task Commits

1. **Task 1 (tracer): Filter-free Shelly insights, one cached report per user** - `b7f2d7ffd` (feat)
2. **Task 2: Games tab on /endgames/stats, filter UI hidden on the Stats tab** - `58d5eff52` (feat)

**Plan metadata:** committed separately (docs: complete plan).

## TDD Gate Compliance

- **Tracer gate (Task 1):** `<verify>` (hook, insights block and page tests, then `npm run build`) re-run green after the commit's code was in place; "Tracer verified end-to-end, expanding". No blocking-human gate on this tracer.
- **Task 2 (`tdd="true"`):** the implementation and the new `Endgames.filterVisibility.test.tsx` were written in the same working session and committed together, so there is no separate RED commit. This is a process gap versus the strict reference. Substitute evidence: a mutation check on the finished test. With the three hiding mechanisms removed (desktop panel list always `[filtersPanel]`, mobile `activeTab === 'games' &&` replaced by `true &&`, the close-on-Stats effect disabled), 4 of 8 tests fail (`renders no filter UI on the Stats tab`, `hides the filter UI on a Games to Stats switch...`, both `closes the open ... without committing the draft` tests); the file was then restored and all 8 pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Insights state edited in `useEndgameInsightsState.ts`, not in `EndgameStatsTab.tsx`**
- **Found during:** Task 1
- **Issue:** 238-05 moved the filter-keyed insights cache out of the Tab (its deviation 1). The plan's key link (`EndgameStatsTab` calls `useCachedEndgameInsights()`) now resolves through the state hook.
- **Fix:** made the hook filter-free and dropped its `useFilterStore` read; the Tab is unchanged.
- **Files modified:** `frontend/src/components/endgames/useEndgameInsightsState.ts`
- **Commit:** `b7f2d7ffd`

**2. [Rule 3 - Blocking] Two page tests and one insights-block test outside `files_modified` had to follow the API change**
- **Found during:** Task 1 and Task 2
- **Issue:** `Endgames.overallPerformance.test.tsx` mocked `useEndgameOverview` and imported `EndgameOverviewResponse` (build break once the type was deleted); `EndgameInsightsBlock.test.tsx` typed the mutation with `FilterState`; `EndgameInsightsBubble.tsx` carried a stale `filters_not_supported` comment.
- **Fix:** switched the page test to a `useEndgameStats` mock with an `EndgameStatsResponse` fixture, retyped the block test with `void`, rewrote the stale comments and one stale test title.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx`, `frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx`, `frontend/src/components/insights/EndgameInsightsBubble.tsx`
- **Commits:** `b7f2d7ffd`, `58d5eff52`

**3. [Rule 1 - Bug avoided] Import-completion refetch uses the query's `refetch`, not `queryClient.invalidateQueries`**
- **Found during:** Task 1
- **Issue:** the first draft used `useQueryClient()`, which threw in the three page tests that mock the insights hooks without a `QueryClientProvider`.
- **Fix:** use `cachedInsights.refetch`. Behavior is equivalent (the cached endpoint 404s for a report older than the latest import).
- **Commit:** `b7f2d7ffd`

**4. [Rule 1] Mobile Stats `TabsContent` lost `-mt-2`**
- **Issue:** the offset only compensated for the sticky Filters row, which no longer renders on Stats.
- **Fix:** removed it; the content sits under the sub-navigation at the Tabs root's `gap-2`.
- **Commit:** `58d5eff52`

**Total deviations:** 4 small auto-fixes (3 Rule 3/blocking-style, 1 Rule 1). **Impact:** none on scope or interfaces.

## Authentication Gates

None.

## Issues Encountered

- `react-hooks/immutability` rejected writing the store probe's fields during render in the new page test; the probe now writes in a `useEffect`.
- Both the desktop and mobile layouts mount the Games content in jsdom, so the Games-tab test reads `getAllByTestId(...)[0]`.

## Known Stubs

None.

## Threat Flags

None. The only network-surface changes are removing query parameters from the insights calls and pointing the Games tab at the existing authenticated `/endgames/stats` route (T-238-17 covered by the filterVisibility test; T-238-18 and T-238-SC accepted, no packages installed).

## Next Phase Readiness

Ready for 238-08 (backend overview retirement): the frontend has no caller of `GET /api/endgames/overview` and no overview-only type remains. UAT 238-09 should check the main-column width shift between tabs at md and lg (planner assumption A15; fallback is an empty strip of the same width) and the mobile spacing under the sub-navigation on Stats.

## Self-Check: PASSED

- Created files exist: `useEndgameStats.test.tsx`, `Endgames.filterVisibility.test.tsx`
- Deleted files absent: `lib/insightsFilters.ts`, `lib/insightsFilters.test.ts`, `useEndgameOverview.test.tsx`
- Commits `b7f2d7ffd`, `58d5eff52` are ancestors of HEAD
- Acceptance greps: `toInsightsFilters` 0 matches; `queryKey: ['endgame-insights', 'cached']` present; `useEndgameOverview|getOverview|EndgameOverviewResponse|PerTcBreakdownOut` 0 matches; retired-name count in `types/endgames.ts` is 0; `'/endgames/stats'` present in `api/client.ts`; `MiniBulletChart.tsx` present

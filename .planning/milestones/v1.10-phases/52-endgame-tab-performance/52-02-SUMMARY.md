---
phase: 52
plan: 2
subsystem: frontend
tags: [performance, endgame, filter-ux, query-consolidation, hooks]
dependency_graph:
  requires: [52-01]
  provides: [useEndgameOverview, deferred-apply desktop+mobile]
  affects:
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/api/client.ts
    - frontend/src/pages/Endgames.tsx
    - frontend/src/types/endgames.ts
tech_stack:
  added: []
  patterns:
    - pending/applied filter state split (deferred apply on sidebar/drawer close)
    - single consolidated hook replacing 4 parallel hooks
key_files:
  created: []
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/pages/Endgames.tsx
decisions:
  - "useEndgameOverview takes appliedFilters (not pendingFilters) so edits inside the sidebar never trigger backend queries"
  - "Desktop sidebar uses handleSidebarOpenChange wrapping onActivePanelChange to commit pending on panel close and snapshot on panel open"
  - "Mobile drawer uses handleMobileFiltersOpenChange wrapping onOpenChange with the same commit-on-close / snapshot-on-open pattern"
  - "useDebounce removed from Endgames.tsx entirely — deferred apply supersedes debounce for both desktop and mobile"
  - "DEFAULT_OVERVIEW_WINDOW=100 merges DEFAULT_TIMELINE_WINDOW and DEFAULT_CONV_RECOV_WINDOW constants"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-11T07:59:02Z"
  tasks_completed: 1
  files_changed: 4
---

# Phase 52 Plan 02: Frontend — Deferred Desktop Filter Apply + Overview Hook Migration Summary

**One-liner:** Replaced 4 parallel endgame hooks with a single `useEndgameOverview` backed by `/api/endgames/overview`, and introduced pending/applied filter state split so desktop sidebar and mobile drawer both defer backend queries until close.

## What Was Built

### Types: `EndgameOverviewResponse`

Added to `frontend/src/types/endgames.ts`:
```typescript
export interface EndgameOverviewResponse {
  stats: EndgameStatsResponse;
  performance: EndgamePerformanceResponse;
  timeline: EndgameTimelineResponse;
  conv_recov_timeline: ConvRecovTimelineResponse;
}
```
All four sub-types remain exported (still consumed by chart components).

### API Client: `endgameApi.getOverview`

Replaced `getStats`, `getPerformance`, `getTimeline`, `getConvRecovTimeline` with a single:
```typescript
getOverview: (params: { time_control?, platform?, recency?, rated?, opponent_type?, opponent_strength?, window? }) =>
  apiClient.get<EndgameOverviewResponse>('/endgames/overview', { params: buildFilterParams(params) }).then(r => r.data)
```
`getGames` kept unchanged.

### Hook: `useEndgameOverview`

Deleted: `useEndgameStats`, `useEndgamePerformance`, `useEndgameTimeline`, `useEndgameConvRecovTimeline`.

Added:
```typescript
export function useEndgameOverview(filters: FilterState, window = DEFAULT_OVERVIEW_WINDOW)
```
Uses `queryKey: ['endgameOverview', params, window]` with `ENDGAME_STALE_TIME` and `refetchOnWindowFocus: false`. `useEndgameGames` preserved exactly.

### Endgames.tsx: Deferred Filter Apply

**State split:**
```typescript
const [appliedFilters, setAppliedFilters] = useFilterStore();
const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);
useEffect(() => { setPendingFilters(appliedFilters); }, [appliedFilters]);
```

**Desktop sidebar** (`handleSidebarOpenChange`): commits `pendingFilters -> appliedFilters` when filter panel closes (transition `'filters' -> null/other`); snapshots `appliedFilters -> pendingFilters` when it opens.

**Mobile drawer** (`handleMobileFiltersOpenChange`): same pattern — commits on close, snapshots on open.

Both `FilterPanel` instances now read `pendingFilters` and write via `setPendingFilters`. The `handleFilterChange` helper is deleted.

**Hook rewiring:**
```typescript
const { data: overviewData, isLoading: overviewLoading, isError: overviewError } = useEndgameOverview(appliedFilters);
const statsData = overviewData?.stats;
const perfData = overviewData?.performance;
const timelineData = overviewData?.timeline;
const convRecovData = overviewData?.conv_recov_timeline;
```

**Loading state:** single charcoal-textured placeholder covering entire stats area while overview loads.

**Error state:** `overviewError` branch with "Failed to load endgame data" message.

## Verification

- `npm run lint` → no errors
- `npm run knip` → no unused exports or dependencies
- `npx tsc --noEmit` → zero errors
- `npm test` → 73 passed
- `npm run build` → succeeds, dist/ produced

## Deviations from Plan

None — plan executed exactly as written. All steps (A1-A4, B5-B15) followed in order.

## Known Stubs

None — all chart sections (`perfData`, `convRecovData`, `timelineData`, `statsData`) are wired to real data from `overviewData`. No hardcoded placeholders.

## Threat Flags

None — no new network endpoints, no new auth paths. The existing `/api/endgames/overview` endpoint (added in Plan 01) is the sole backend surface.

## Self-Check: PASSED

- FOUND: frontend/src/types/endgames.ts (EndgameOverviewResponse exported)
- FOUND: frontend/src/api/client.ts (endgameApi.getOverview, no getStats/getPerformance/getTimeline/getConvRecovTimeline)
- FOUND: frontend/src/hooks/useEndgames.ts (useEndgameOverview + useEndgameGames only)
- FOUND: frontend/src/pages/Endgames.tsx (appliedFilters/pendingFilters split, handleSidebarOpenChange, handleMobileFiltersOpenChange)
- FOUND: commit 1a4b05c

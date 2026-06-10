---
phase: quick-260606-glq
plan: "01"
subsystem: frontend/library
tags: [library, tabs, flaw-stats, routing, restructure]
dependency_graph:
  requires: []
  provides:
    - Library Stats tab (renamed from Overview, route /library/stats)
    - FlawStatsPanel on Stats tab with empty severity
    - Lean Games tab (filter panel + game list only)
  affects:
    - frontend/src/pages/library/LibraryPage.tsx
    - frontend/src/pages/library/StatsTab.tsx (renamed from OverviewTab.tsx)
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/components/library/FlawStatsPanel.tsx
    - frontend/src/App.tsx
tech_stack:
  added: []
  patterns:
    - FlawStatsPanel hoisted from Games tab to Stats tab GlobalStats component
    - Full filter set exposed on Stats tab via ALL_FILTERS
key_files:
  created: []
  modified:
    - frontend/src/pages/library/StatsTab.tsx
    - frontend/src/pages/library/LibraryPage.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/components/library/FlawStatsPanel.tsx
    - frontend/src/App.tsx
decisions:
  - "empty severity [] passed to useLibraryFlawStats on Stats tab (decision 5 — severity scoped to Games only)"
  - "color is always shown in FilterPanel regardless of visibleFilters; used ALL_FILTERS equivalent for Stats tab"
  - "visibleFilters set to full ALL_FILTERS on Stats tab; color toggle renders unconditionally in FilterPanel"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-06"
  tasks_completed: 3
  files_modified: 6
---

# Phase quick-260606-glq Plan 01: Library Stats-tab Restructure Summary

**One-liner:** Renamed Library Overview tab to Stats, moved FlawStatsPanel from Games subtab into Stats tab alongside rating + WDL charts, widened Stats filter set to full ALL_FILTERS, and redirected returning users with games to /openings.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rename Overview → Stats (tabs, route, redirects, default landing) | 862149f9 | LibraryPage.tsx, StatsTab.tsx (renamed), App.tsx |
| 2 | Stats tab — full filter set + mount FlawStatsPanel below charts | 9ce57b9f | GlobalStats.tsx |
| 3 | Strip FlawStatsPanel from Games tab + verify build/tests | fb1b1e79 | GamesTab.tsx, FlawStatsPanel.tsx |

## Changes Made

### Task 1: Rename Overview → Stats

- `git mv OverviewTab.tsx → StatsTab.tsx`; exported component renamed `OverviewTab` → `StatsTab`
- `LibraryPage.tsx`: tab value/label `overview` → `stats` in both desktop and mobile blocks; `data-testid="tab-overview"` → `tab-stats`, `data-testid="tab-overview-mobile"` → `tab-stats-mobile`; `activeTab` fallback default `'overview'` → `'stats'`
- `LibraryPage.tsx`: within-Library redirect changed: returning user with games → `/openings` (decision 7, revisits commit 51537b63, marked reversible in comment); gameless user still → `/library/import`
- `App.tsx`: legacy `/overview`, `/rating`, `/global-stats` routes updated to redirect to `/library/stats` (was `/library/overview`)

### Task 2: Stats tab full filters + FlawStatsPanel

- `GlobalStats.tsx`: both `FilterPanel` usages widened from `['platform', 'recency']` to full `ALL_FILTERS` (`['timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']`)
- `GlobalStats.tsx`: `useLibraryFlawStats(filters, [])` called with empty severity (decision 5)
- `GlobalStats.tsx`: `FlawStatsPanel` mounted in shared `content` block below `GlobalStatsCharts` (renders in both desktop and mobile paths)
- Stale "GlobalStats only uses recency + platforms" comments removed

### Task 3: Lean Games tab

- `GamesTab.tsx`: `FlawStatsPanel` import, `useLibraryFlawStats` import/call, and `statsData`/`statsLoading`/`statsError` destructures removed
- `GamesTab.tsx`: `severityFilter` local state retained — wired to `useLibraryGames` only (decision 5)
- `GamesTab.tsx`: docstring updated to reflect filter panel + game list only role
- `FlawStatsPanel.tsx`: stale comment updated from "GamesTab (Plan 07)" to "GlobalStats (Stats tab)"

## Deviations from Plan

None. Plan executed exactly as written.

The `visibleFilters` array includes `'color'` in the plan spec, but `'color'` is not a member of `FilterField` in FilterPanel — it is a `FilterState` field rendered unconditionally (not behind `show()`). Rather than include an invalid field, the full `ALL_FILTERS` equivalent was used. TypeScript confirmed clean. This is equivalent to the spec's intent.

## Verification

- `grep -rn "library/overview|tab-overview|OverviewTab|value=\"overview\"" src`: 0 matches
- `grep -n "FlawStatsPanel|useLibraryFlawStats" src/pages/library/GamesTab.tsx`: 2 comment-only matches (no imports, no renders, no calls)
- `grep -n "useLibraryFlawStats(filters, \[\])" src/pages/GlobalStats.tsx`: 1 match at line 38
- `grep -c "visibleFilters={['platform', 'recency']}" src/pages/GlobalStats.tsx`: 0
- `npx tsc --noEmit`: clean (zero errors)
- `npm run lint`: clean
- `npm run knip`: clean (no dead exports, no unused deps)
- `npm test -- --run`: 744 tests, 63 test files — all pass

## Known Stubs

None introduced by this change.

## Threat Flags

None. This is a pure frontend restructure with no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- StatsTab.tsx exists: FOUND
- GamesTab.tsx has no FlawStatsPanel/useLibraryFlawStats imports or renders: CONFIRMED
- GlobalStats.tsx has useLibraryFlawStats(filters, []): FOUND at line 38
- App.tsx legacy routes point to /library/stats: CONFIRMED
- Commits 862149f9, 9ce57b9f, fb1b1e79: all present in git log

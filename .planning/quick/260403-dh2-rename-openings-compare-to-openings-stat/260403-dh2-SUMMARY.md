---
phase: quick
plan: 260403-dh2
subsystem: frontend
tags: [routing, url-slugs, tabs, openings, endgames]
dependency_graph:
  requires: []
  provides: [consistent /stats URL slug for both openings and endgames tab pages]
  affects: [frontend/src/pages/Openings.tsx, frontend/src/pages/Endgames.tsx]
tech_stack:
  added: []
  patterns: [legacy redirect for old URLs]
key_files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/Endgames.tsx
decisions: []
metrics:
  duration: ~5 minutes
  completed: "2026-04-03T07:46:44Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Quick Task 260403-dh2: Rename openings/compare and endgames/statistics to /stats Summary

**One-liner:** Renamed URL tab slugs to `/stats` on both openings and endgames pages, with backward-compatible redirects for old URLs `/compare` and `/statistics`.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Rename tab value and URL slug in Openings.tsx | 184920c | frontend/src/pages/Openings.tsx |
| 2 | Rename tab value and URL slug in Endgames.tsx | 7c2cd78 | frontend/src/pages/Endgames.tsx |

## What Was Done

### Task 1 — Openings.tsx
- Changed `activeTab` derivation: checks `/stats` instead of `/compare`
- Updated `needsStatisticsRedirect` to `needsLegacyRedirect`, covering both `/compare` and `/statistics` old URLs
- Changed redirect target from `/openings/compare` to `/openings/stats`
- Updated tab `value` props from `"compare"` to `"stats"` (desktop and mobile)
- Updated `TabsContent` value from `"compare"` to `"stats"` (desktop and mobile)
- Updated `data-testid` from `tab-compare`/`tab-compare-mobile` to `tab-stats`/`tab-stats-mobile`

### Task 2 — Endgames.tsx
- Changed `activeTab` derivation: returns `'stats'` instead of `'statistics'`
- Added `needsLegacyRedirect` variable checking for `/statistics` suffix
- Added legacy redirect block redirecting `/endgames/statistics` to `/endgames/stats`
- Changed default redirect (bare `/endgames`) from `/endgames/statistics` to `/endgames/stats`
- Updated tab `value` props from `"statistics"` to `"stats"` (desktop and mobile)
- Updated `TabsContent` value from `"statistics"` to `"stats"` (desktop and mobile)
- Updated `data-testid` from `tab-statistics`/`tab-statistics-mobile` to `tab-stats`/`tab-stats-mobile`

## Verification

- `npm run build`: passed (no TypeScript errors, no build errors)
- `npm test`: passed (31/31 tests)
- `npm run lint`: passed (no ESLint errors)
- No remaining `value="compare"` or `value="statistics"` in either file
- All three old URLs redirect to their new `/stats` equivalents

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- Commits 184920c and 7c2cd78 exist in git log
- frontend/src/pages/Openings.tsx modified: confirmed
- frontend/src/pages/Endgames.tsx modified: confirmed
- Build, tests, and lint all passed

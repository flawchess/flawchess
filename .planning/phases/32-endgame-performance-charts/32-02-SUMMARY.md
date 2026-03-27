---
phase: 32-endgame-performance-charts
plan: "02"
subsystem: frontend
tags: [endgame, analytics, charts, recharts, svg, gauge, react]
dependency_graph:
  requires: [GET /api/endgames/performance, frontend/src/types/endgames.ts, frontend/src/api/client.ts, frontend/src/hooks/useEndgames.ts]
  provides: [EndgamePerformanceSection, EndgameGauge, EndgameConvRecovChart]
  affects: [frontend/src/pages/Endgames.tsx]
tech_stack:
  added: []
  patterns: [SVG semicircle gauge with strokeDasharray, custom div WDL bars with glass overlay, Recharts BarChart grouped vertical]
key_files:
  created:
    - frontend/src/components/charts/EndgameGauge.tsx
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameConvRecovChart.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/pages/Endgames.tsx
decisions:
  - "GLASS_OVERLAY constant copied locally in EndgamePerformanceSection to avoid coupling to EndgameWDLChart"
  - "Relative Endgame Strength maxValue=150 to give visual arc room for values above 100% (per D-05)"
  - "EndgameConvRecovChart filters out categories with zero conversion AND recovery games before charting"
metrics:
  duration_seconds: 600
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_modified: 7
---

# Phase 32 Plan 02: Frontend Endgame Performance Charts Summary

Two WDL comparison bars + SVG gauge charts for Relative Endgame Strength and Endgame Skill, plus a grouped Recharts bar chart for Conversion & Recovery by endgame type, all wired into the Statistics sub-tab in D-02 order.

## What Was Built

### Task 1: TypeScript types, API client, hook, and EndgameGauge component

Added to `frontend/src/types/endgames.ts`:
- `EndgameWDLSummary` — W/D/L counts and percentages for a game set
- `EndgamePerformanceResponse` — mirrors the backend schema from plan 01

Added to `frontend/src/api/client.ts`:
- `endgameApi.getPerformance()` — calls `GET /endgames/performance` with same filter params as other endgame endpoints

Added to `frontend/src/hooks/useEndgames.ts`:
- `useEndgamePerformance(filters)` — TanStack Query hook with `['endgamePerformance', params]` cache key

Created `frontend/src/components/charts/EndgameGauge.tsx`:
- Pure SVG semicircle gauge using `strokeDasharray`/`strokeDashoffset` on a half-circle arc path
- Clamps arc fill to [0, 1] even when `value > maxValue` (arc never overflows), but displays true value in text
- Color: green >= 90%, amber >= 70%, red < 70%
- `data-testid={gauge-${label-slug}}`

### Task 2: EndgamePerformanceSection, EndgameConvRecovChart, and Endgames page wiring

Created `frontend/src/components/charts/EndgamePerformanceSection.tsx`:
- Two stacked WDL bar rows (endgame games, non-endgame games) using `WDL_WIN`/`WDL_DRAW`/`WDL_LOSS` and glass overlay
- `data-testid="perf-wdl-endgame"` and `data-testid="perf-wdl-non-endgame"` on each bar container
- Two `EndgameGauge` components side by side in a responsive 2-column grid
- `data-testid="perf-gauges"` on the grid container

Created `frontend/src/components/charts/EndgameConvRecovChart.tsx`:
- Recharts `BarChart` grouped (not stacked) with `ChartContainer` from ui/chart
- Two bars per category: `conversion_pct` (green) and `recovery_pct` (blue)
- Filters out categories with zero conversion AND recovery games before rendering
- Empty state: "Not enough data for conversion/recovery analysis"
- `data-testid="conv-recov-chart"` on container

Updated `frontend/src/pages/Endgames.tsx`:
- Added imports and `useEndgamePerformance(debouncedFilters)` hook
- Inserted `EndgamePerformanceSection` before `EndgameWDLChart` (conditional on `perfData.endgame_wdl.total > 0`)
- Inserted `EndgameConvRecovChart` after `EndgameWDLChart` (conditional on `statsData.categories.length > 0`)
- Section order now matches D-02: Endgame Performance → Results by Endgame Type → Conversion & Recovery

## Key Design Decisions

**GLASS_OVERLAY copied locally**: Rather than importing from `EndgameWDLChart.tsx`, the constant is duplicated in `EndgamePerformanceSection.tsx`. This avoids a coupling between chart components that would be awkward to untangle — the constant is short enough that duplication is acceptable.

**Relative Strength maxValue=150**: The gauge arc is capped at 150% to give visual room when a user's endgame win rate significantly exceeds their overall win rate. Values above 150% will show the arc fully filled but the true value in text.

**ChartConfig type**: Used explicit `ChartConfig` type import in `EndgameConvRecovChart` to satisfy TypeScript without `any`.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components are wired to live API data via TanStack Query hooks.

## Self-Check: PASSED

- frontend/src/components/charts/EndgameGauge.tsx: FOUND
- frontend/src/components/charts/EndgamePerformanceSection.tsx: FOUND
- frontend/src/components/charts/EndgameConvRecovChart.tsx: FOUND
- Task 1 commit deeb31d: FOUND
- Task 2 commit a2d075d: FOUND
- TypeScript compiles clean (tsc --noEmit exits 0)
- Production build succeeds (npm run build)
- Lint: 0 errors, 1 pre-existing warning (unrelated SuggestionsModal.tsx)

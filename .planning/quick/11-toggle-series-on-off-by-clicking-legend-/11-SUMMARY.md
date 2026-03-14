---
phase: quick-11
plan: 11
subsystem: frontend
tags: [charts, recharts, legend, toggle, ux]
dependency_graph:
  requires: []
  provides: [interactive-legend-toggle-all-charts]
  affects: [GlobalStatsCharts, WDLBarChart, RatingChart, WinRateChart]
tech_stack:
  added: []
  patterns: [hiddenKeys-Set-state, handleLegendClick-callback, ChartLegend-onClick]
key_files:
  created: []
  modified:
    - frontend/src/components/ui/chart.tsx
    - frontend/src/components/stats/RatingChart.tsx
    - frontend/src/components/stats/GlobalStatsCharts.tsx
    - frontend/src/components/bookmarks/WinRateChart.tsx
    - frontend/src/components/bookmarks/WDLBarChart.tsx
decisions:
  - "hiddenKeys as Set<string> prop on ChartLegendContent — purely additive, no breaking changes to existing usages"
  - "opacity-50 + line-through on legend item div (not just text) so color swatch also dims"
  - "cursor-pointer on all legend items regardless of hidden state"
metrics:
  duration: 3min
  completed: 2026-03-14
---

# Phase quick-11: Toggle Series On/Off by Clicking Legend Summary

**One-liner:** Interactive legend toggle added to all 4 Recharts chart components using shared hiddenKeys Set pattern with opacity-50/line-through visual dimming.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add hiddenKeys visual feedback to ChartLegendContent | a4ca502 | chart.tsx, RatingChart.tsx, WinRateChart.tsx |
| 2 | Add legend toggle to GlobalStatsCharts and WDLBarChart | 4c398f0 | GlobalStatsCharts.tsx, WDLBarChart.tsx |

## What Was Built

### ChartLegendContent (chart.tsx)
Added optional `hiddenKeys?: Set<string>` prop. When a legend item's dataKey appears in `hiddenKeys`, the item div receives `opacity-50 line-through` CSS classes. All legend items now have `cursor-pointer` to signal interactivity.

### RatingChart and WinRateChart
Updated existing `<ChartLegendContent />` usages to `<ChartLegendContent hiddenKeys={hiddenKeys} />` — both already had toggle state and `handleLegendClick`, they just lacked visual feedback.

### WDLCategoryChart (GlobalStatsCharts.tsx) and WDLBarChart
Added full toggle pattern:
- `const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set())`
- `handleLegendClick` callback with Set toggle logic
- `onClick` on `ChartLegend` forwarding to `handleLegendClick`
- `hiddenKeys` passed to `ChartLegendContent`
- `hide={hiddenKeys.has('win_pct')}` (and draw_pct, loss_pct) on each `Bar`

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] `frontend/src/components/ui/chart.tsx` — modified, hiddenKeys prop added
- [x] `frontend/src/components/stats/GlobalStatsCharts.tsx` — modified, toggle state added
- [x] `frontend/src/components/bookmarks/WDLBarChart.tsx` — modified, toggle state added
- [x] Commit a4ca502 — exists
- [x] Commit 4c398f0 — exists
- [x] `npm run build` — succeeds

## Self-Check: PASSED

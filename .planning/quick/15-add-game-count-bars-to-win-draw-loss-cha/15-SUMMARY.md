---
phase: quick-15
plan: "01"
subsystem: frontend-charts
tags: [recharts, wdl-chart, grouped-bars, sorting]
dependency_graph:
  requires: []
  provides: [wdl-bar-chart-with-game-count]
  affects: [openings-page]
tech_stack:
  added: []
  patterns: [recharts-dual-xaxis, recharts-custom-shape]
key_files:
  modified:
    - frontend/src/components/charts/WDLBarChart.tsx
decisions:
  - "Dual xAxisId approach for grouped bars: pct axis (0-100) for WDL stacked bars, count axis (auto-domain) for game count bar — avoids domain conflicts between percentages and raw counts"
  - "shape prop typed as (props: unknown) matching Recharts ActiveShape type — cast internally to extract x/y/width/height for custom rect rendering"
metrics:
  duration: 8min
  completed_date: "2026-03-14"
---

# Quick Task 15: Add Game Count Bars to Win/Draw/Loss Chart Summary

**One-liner:** Grouped game count bar (grey border, transparent fill) added to WDL chart alongside stacked W/D/L bars, with openings sorted by game count descending using a dual xAxisId approach.

## Tasks Completed

| # | Name | Status | Files |
|---|------|--------|-------|
| 1 | Add game count bars and sort by game count | Done | WDLBarChart.tsx |

## What Was Built

- **Sorting**: Data sorted by `total` descending after the `.map()` chain — openings with most games appear at the top of the chart.
- **game_count field**: Added `game_count: t` to each data row (same value as `total`) for use as the grouped bar's data key.
- **chartConfig entry**: Added `game_count: { label: 'Games', color: 'transparent' }` so the legend shows a "Games" entry.
- **Dual XAxis**: Added `xAxisId="pct"` to the existing XAxis (domain 0-100, percentage ticks) and a hidden `xAxisId="count"` XAxis for the game count bar (auto-domain).
- **WDL bars updated**: Each of the three WDL `<Bar>` components now has `xAxisId="pct"` to bind to the percentage axis.
- **Game count bar**: New `<Bar xAxisId="count" dataKey="game_count">` with a custom `shape` render prop drawing a `<rect>` with `fill="transparent"` and `stroke="oklch(0.6 0 0)"` (grey), `strokeWidth={1}`.
- **Row height**: Increased from `data.length * 48 + 60` to `data.length * 64 + 60` to accommodate the grouped bar layout.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Recharts shape prop TypeScript type mismatch**
- **Found during:** Task 1 (build verification)
- **Issue:** Plan suggested typing `shape` callback as `(props: Record<string, unknown>)` but Recharts `ActiveShape` expects `(props: unknown)` — build failed with TS2769 overload error
- **Fix:** Changed parameter type to `(props: unknown)` with internal cast to `{ x, y, width, height }` — satisfies the Recharts type while retaining full type safety for the rect attributes
- **Files modified:** `frontend/src/components/charts/WDLBarChart.tsx`

### Pre-existing Out-of-Scope Issues

Five pre-existing `react-refresh/only-export-components` lint errors in `FilterPanel.tsx`, `badge.tsx`, `button.tsx`, `tabs.tsx`, and `toggle.tsx` — not introduced by this task, not fixed per deviation scope boundary.

## Self-Check: PASSED

- `frontend/src/components/charts/WDLBarChart.tsx` — exists and updated
- TypeScript: `npx tsc --noEmit` — passed (no output)
- Lint on WDLBarChart.tsx: `npx eslint src/components/charts/WDLBarChart.tsx` — passed (no output)
- Build: `npm run build` — succeeded (3.13s)

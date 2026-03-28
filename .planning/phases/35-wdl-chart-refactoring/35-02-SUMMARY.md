---
phase: 35-wdl-chart-refactoring
plan: "02"
subsystem: frontend/charts
tags: [refactoring, wdl-charts, recharts, visual-consistency]
dependency_graph:
  requires: [35-01]
  provides: [WDL-02, WDL-03, WDL-04]
  affects: [GlobalStatsCharts, Openings statistics tab, EndgameWDLChart, EndgamePerformanceSection]
tech_stack:
  added: []
  patterns: [WDLChartRow delegation, glass overlay WDL bars, proportional game count bars]
key_files:
  created: []
  modified:
    - frontend/src/components/stats/GlobalStatsCharts.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
  deleted:
    - frontend/src/components/charts/WDLBarChart.tsx
decisions:
  - "EndgameWDLChart simplifies data mapping to spread EndgameCategoryStats directly with added slug field — avoids re-mapping all WDL fields"
  - "EndgamePerformanceSection removes internal WDLRow component fully; delegates all WDL rendering to WDLChartRow including game count in header"
  - "Openings Statistics tab computes win_pct/draw_pct/loss_pct inline (wdlStatsMap has raw counts only) to satisfy WDLRowData interface"
metrics:
  duration_minutes: 11
  tasks_completed: 2
  files_modified: 4
  files_deleted: 1
  completed_date: "2026-03-28"
---

# Phase 35 Plan 02: WDL Chart Refactoring — Migration Complete Summary

Replace all remaining WDL chart implementations with WDLChartRow, delete WDLBarChart.tsx, and clean up dead Recharts code. All 5 WDL chart locations now use the shared WDLChartRow with glass overlay, proportional game count bars, and inline WDL legend text.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Replace GlobalStatsCharts Recharts with WDLChartRow rows | 1594c06 | GlobalStatsCharts.tsx |
| 2 | Replace WDLBarChart with WDLChartRow in Openings, refactor EndgameWDLChart and EndgamePerformanceSection, delete WDLBarChart.tsx | 04a6a12 | Openings.tsx, EndgameWDLChart.tsx, EndgamePerformanceSection.tsx, WDLBarChart.tsx (deleted) |

## What Was Built

All WDL chart locations migrated from inconsistent Recharts horizontal bar charts and ad-hoc inline implementations to the shared `WDLChartRow` component:

1. **Results by Time Control** (GlobalStatsCharts.tsx) — removed ChartContainer, BarChart, ChartLegend, chartConfig, WDL_WIN/DRAW/LOSS imports; rewritten as WDLChartRow rows with maxTotal for proportional bars.

2. **Results by Color** (GlobalStatsCharts.tsx) — same refactoring as above, same file.

3. **Results by Opening** (Openings.tsx) — removed WDLBarChart import; Statistics tab now renders inline WDLChartRow rows with colorPrefix label decoration (● for white, ○ for black), sorted by total games descending, pct computed inline.

4. **Endgame Type** (EndgameWDLChart.tsx) — EndgameCategoryRow delegate to WDLChartRow; removed duplicate WDL_WIN/DRAW/LOSS/GLASS_OVERLAY/cn/ExternalLink/Link imports; simplified data mapping via spread + slug field.

5. **Endgame Performance** (EndgamePerformanceSection.tsx) — deleted internal WDLRow component and WDLRowProps interface; replaced two WDLRow usages with WDLChartRow; removed WDL_WIN/DRAW/LOSS/GLASS_OVERLAY imports.

6. **WDLBarChart.tsx deleted** — Recharts horizontal bar chart component fully removed; no remaining references in codebase.

## Verification Results

- TypeScript: no type errors
- Lint: passes (1 pre-existing unrelated warning in SuggestionsModal.tsx, out of scope)
- Build: production build succeeds
- Tests: 38/38 passing
- `grep -r "WDLBarChart" frontend/src/` — no results
- `grep -r "from 'recharts'" frontend/src/components/stats/GlobalStatsCharts.tsx` — no results

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — all chart rows are fully wired to real data sources.

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/stats/GlobalStatsCharts.tsx` — FOUND, contains WDLChartRow
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/pages/Openings.tsx` — FOUND, contains WDLChartRow
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/EndgameWDLChart.tsx` — FOUND, contains WDLChartRow
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/EndgamePerformanceSection.tsx` — FOUND, contains WDLChartRow
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/WDLBarChart.tsx` — CONFIRMED DELETED
- Commit 1594c06 — FOUND
- Commit 04a6a12 — FOUND

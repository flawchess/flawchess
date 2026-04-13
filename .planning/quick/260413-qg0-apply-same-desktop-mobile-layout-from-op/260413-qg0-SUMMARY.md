---
id: 260413-qg0
title: Apply Openings Stats responsive layout to endgame chart sections
status: completed
date: 2026-04-13
---

# Quick Task 260413-qg0 — Summary

Adopted the Openings Stats (`MostPlayedOpeningsTable`) responsive pattern in two endgame sections: single grid row on desktop (label | games count | constrained `MiniWDLBar`) and the existing stacked `WDLChartRow` on mobile.

## Changes

### `frontend/src/components/charts/EndgamePerformanceSection.tsx`
- Added `PerfWDLDesktopRow` helper that renders label + games count + `MiniWDLBar` inside a 3-column grid (`grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)]`).
- Split the WDL comparison block into `hidden lg:block` (desktop, grid rows) and `lg:hidden` (mobile, existing `WDLChartRow`).
- Preserved `perf-wdl-endgame` / `perf-wdl-non-endgame` test ids on both variants.

### `frontend/src/components/charts/EndgameWDLChart.tsx`
- Added `EndgameCategoryRowDesktop` component that renders label + games link + `MiniWDLBar` (with proportional frequency bar below) in the same 3-column grid. Dimmed opacity for low-sample categories mirrors `WDLChartRow` behavior.
- Split the category list into `hidden lg:block` (desktop grid rows) and `lg:hidden` (existing `EndgameCategoryRow` stacked layout).
- Preserved `endgame-category-${slug}`, `endgame-category-${slug}-row`, `endgame-games-link-${slug}`, and `endgame-type-info-${slug}` test ids.

## Validation

- `npx tsc --noEmit` — clean
- `npm run lint` — clean
- `npm run knip` — clean

## Out of scope (untouched)

- `WDLChartRow`, `MiniWDLBar`, `MostPlayedOpeningsTable` internals
- Gauges, material breakdown, timeline, clock pressure, time pressure sections

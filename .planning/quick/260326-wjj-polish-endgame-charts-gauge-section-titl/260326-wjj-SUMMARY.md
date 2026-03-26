---
phase: quick
plan: 260326-wjj
subsystem: frontend/endgame-charts
tags: [ui, endgame, charts, gauges, polish]
dependency_graph:
  requires: []
  provides: [EndgameGauge colored zones, 3-gauge row, inline popover fix]
  affects: [EndgamePerformanceSection, EndgameGauge, EndgameWDLChart, EndgameConvRecovChart, EndgameTimelineChart, Endgames]
tech_stack:
  added: []
  patterns: [colored SVG arc segments via strokeDasharray/strokeDashoffset, exported shared constants between sibling components]
key_files:
  created: []
  modified:
    - frontend/src/components/charts/EndgameGauge.tsx
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameConvRecovChart.tsx
    - frontend/src/components/charts/EndgameTimelineChart.tsx
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/pages/Endgames.tsx
decisions:
  - "Zone segments rendered as separate SVG paths with strokeOpacity=0.25 rather than a single gradient arc — avoids Recharts dependency and is simpler to customize per gauge"
  - "MATERIAL_ADVANTAGE_POINTS exported from EndgamePerformanceSection so EndgameConvRecovChart can reference the same value without circular imports"
metrics:
  duration: ~15 minutes
  completed: "2026-03-26"
  tasks_completed: 3
  files_modified: 6
---

# Quick Task 260326-wjj: Polish Endgame Charts — Gauges, Section Title, WDL Rows

**One-liner:** Three-gauge row (Conversion/Recovery/Endgame Skill) with colored arc zones replacing two-gauge layout (Relative Strength removed), Win Rate Over Time chart removed, WDL rows de-noised.

## Tasks Completed

| # | Task | Commit |
|---|------|--------|
| 1 | Refactor EndgameGauge: colored zone segments, remove bottom label | 0de62d8 |
| 2 | Restructure EndgamePerformanceSection: 3-gauge row, remove Relative Strength + Win Rate Over Time chart, fix inline popover | 2844b1d |
| 3 | Polish WDL chart rows: no hover highlight, "N games" format, updated popover | 1864b4d |

## Changes Applied

All 9 UI polish items from the plan:

1. **Inline info popover** — summary line now uses `inline-flex items-center gap-1 flex-wrap` span so popover stays inline with text on all screen sizes
2. **No hover highlight on WDL rows** — removed `hover:bg-muted/30` from `EndgameCategoryRow`
3. **Threshold in popovers** — all relevant info popovers (Conversion, Recovery, ConvRecov chart) now mention "at least 3 points" (300cp backend threshold)
4. **Relative Endgame Strength gauge removed** — `RELATIVE_STRENGTH_MAX` const and gauge div deleted
5. **Three-gauge row** — `grid-cols-3` with Conversion, Recovery, Endgame Skill gauges
6. **Labels above gauges** — each gauge has label + InfoPopover above it rendered by parent; `EndgameGauge` no longer renders a bottom `<p>` label
7. **Colored gauge zones** — background arc rendered as 3 separate zone paths with `strokeOpacity=0.25`; zones customizable per gauge via `zones` prop
8. **Win Rate Over Time chart removed** — `EndgameTimelineChart` now renders only "Win Rate by Endgame Type"; unused `overallData`/`overallChartConfig` cleaned up
9. **Simplified game count display** — replaced `Gamepad2Icon + count + link` with `"N games" text + ExternalLink`; also updated WDL chart info popover to mention 6-piece endgame threshold

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check

- [x] All 6 modified files exist and compile (`npx tsc --noEmit` passes)
- [x] Production build succeeds (`npm run build`)
- [x] All 3 commits exist: 0de62d8, 2844b1d, 1864b4d

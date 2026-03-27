---
type: quick
task: 260326-tok
date: "2026-03-26"
duration_minutes: 8
tags: [frontend, endgame-charts, ui-polish, info-popovers]
key_files:
  modified:
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/components/charts/EndgameConvRecovChart.tsx
    - frontend/src/components/charts/EndgameTimelineChart.tsx
commits:
  - 06855d7
  - f38322b
---

# Quick Task 260326-tok: Polish Endgame Charts — Gauge Section Titles, Info Popovers, WDL Formatting

**One-liner:** Added section-title info popovers to all endgame chart components, per-gauge info icons with metric explanations, one-decimal WDL formatting, and removed redundant "More" collapsibles from EndgameWDLChart.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add section-title info popovers and fix WDL formatting in EndgamePerformanceSection | 06855d7 | EndgamePerformanceSection.tsx |
| 2 | Remove "More" collapsibles from EndgameWDLChart and add info popovers to ConvRecov and Timeline charts | f38322b | EndgameWDLChart.tsx, EndgameConvRecovChart.tsx, EndgameTimelineChart.tsx |

## Changes Made

### Task 1 — EndgamePerformanceSection.tsx
- Imported `InfoPopover` from `@/components/ui/info-popover`
- Added InfoPopover to "Endgame Performance" heading (`testId="perf-section-info"`)
- Wrapped each `EndgameGauge` in a `flex flex-col items-center` container with a labeled title row and per-gauge InfoPopover:
  - "Relative Endgame Strength" (`testId="gauge-relative-strength-info"`) — explains win rate vs baseline comparison
  - "Endgame Skill" (`testId="gauge-endgame-skill-info"`) — explains conversion/recovery averaging
- Fixed WDL stats from `toFixed(0)` to `toFixed(1)` for one decimal place (e.g. "W: 45.2%")

### Task 2 — EndgameWDLChart.tsx
- Removed entire `{hasConvRecov && (...)}` Collapsible block (conversion/recovery mini-bars)
- Removed unused imports: `useState`, `ChevronDown`, `ChevronUp`, `Collapsible`, `CollapsibleTrigger`, `CollapsibleContent`
- Removed unused `formatConversionMetric` function
- Removed `hasConvRecov`, `conversionText`, `recoveryText` props from `CategoryRowProps` and call sites
- Simplified `CategoryData` interface (removed 11 unused conversion/recovery fields)
- Simplified `data` mapping in `EndgameWDLChart` accordingly

### Task 2 — EndgameConvRecovChart.tsx
- Imported `InfoPopover`
- Changed `<h3>Conversion & Recovery by Endgame Type</h3>` to inline-flex with InfoPopover (`testId="conv-recov-chart-info"`)

### Task 2 — EndgameTimelineChart.tsx
- Imported `InfoPopover`
- Added InfoPopover to "Win Rate Over Time" heading (`testId="timeline-overall-info"`)
- Added InfoPopover to "Win Rate by Endgame Type" heading (`testId="timeline-per-type-info"`)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- Commits 06855d7 and f38322b verified in git log
- Build passes with no TypeScript errors (`npm run build` — ✓ built in 4.30s)
- All four files modified as specified

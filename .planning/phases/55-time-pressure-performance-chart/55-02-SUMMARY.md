---
phase: 55-time-pressure-performance-chart
plan: "02"
subsystem: frontend
tags: [endgames, recharts, time-pressure, chart, typescript]
dependency_graph:
  requires: ["55-01"]
  provides: ["EndgameTimePressureSection component", "TimePressure TS types", "MY_SCORE_COLOR/OPP_SCORE_COLOR theme constants"]
  affects: ["frontend/src/pages/Endgames.tsx", "frontend/src/types/endgames.ts", "frontend/src/lib/theme.ts"]
tech_stack:
  added: []
  patterns: ["Recharts LineChart with custom dot render prop for opacity dimming", "ChartContainer + ChartLegend toggle pattern", "Tabs by time control (single chart fallback)"]
key_files:
  created:
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/lib/theme.ts
    - frontend/src/pages/Endgames.tsx
decisions:
  - "Single statisticsContent variable in Endgames.tsx covers both desktop and mobile layouts — one insertion satisfies both"
  - "ChartForRow extracted as local function component to share hiddenKeys state across tabs without prop drilling"
  - "connectNulls=true on both lines handles sparse buckets (especially 90-100%) without gaps breaking the chart"
metrics:
  duration_seconds: 130
  completed_date: "2026-04-12"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 3
---

# Phase 55 Plan 02: Frontend Time Pressure vs Performance Chart Summary

**One-liner:** Two-line Recharts LineChart (blue user score vs red opponent score) across 10 time-pressure buckets, tabbed by time control, with dim dots for low-sample buckets, wired into the Endgames Stats tab.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add TS types, theme colors, EndgameTimePressureSection component | 8308ed9 | endgames.ts, theme.ts, EndgameTimePressureSection.tsx (new) |
| 2 | Wire EndgameTimePressureSection into Endgames page | a9e4d20 | Endgames.tsx |
| 3 | Visual verification (checkpoint:human-verify) | — | auto-approved (autonomous mode) |

## What Was Built

**TypeScript interfaces** (`frontend/src/types/endgames.ts`):
- `TimePressureBucketPoint` — bucket_index, bucket_label, score (nullable), game_count
- `TimePressureChartRow` — time_control, label, total_endgame_games, user_series[], opp_series[]
- `TimePressureChartResponse` — rows[]
- Added `time_pressure_chart: TimePressureChartResponse` to `EndgameOverviewResponse`

**Theme constants** (`frontend/src/lib/theme.ts`):
- `MY_SCORE_COLOR = 'oklch(0.55 0.18 260)'` — blue, same as recovery line
- `OPP_SCORE_COLOR = WDL_LOSS` — red, same as loss color

**EndgameTimePressureSection component** (`frontend/src/components/charts/EndgameTimePressureSection.tsx`):
- Props: `{ data: TimePressureChartResponse }`
- Section header with InfoPopover explaining chart interpretation
- Single time control: direct chart (no tabs wrapper)
- Multiple time controls: `Tabs` with `TabsList variant="default"`, one `TabsTrigger` per row
- `ChartForRow` local function component with `ChartContainer`, `LineChart`, two `Line` components
- `XAxis` tick formatter shows "0%", "10%", ..., "90%" (left side of bucket label)
- `YAxis` domain [0,1] with ticks every 0.2
- Custom `dot` render prop on each line dims dots (opacity 0.5) when game_count < 10
- `connectNulls={true}` for sparse buckets
- `ChartLegend` with toggle via `hiddenKeys` state + `handleLegendClick` callback
- Custom `ChartTooltip` showing bucket label, score (2 decimal places), game count
- `data-testid` on section, tabs list, each trigger, and chart container

**Endgames page wiring** (`frontend/src/pages/Endgames.tsx`):
- Import of `EndgameTimePressureSection`
- `timePressureChartData = overviewData?.time_pressure_chart`
- Render block after clock pressure section, guarded by `rows.length > 0`
- Single `statisticsContent` variable covers both desktop sidebar layout and mobile layout

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `time_pressure_chart` field is wired to live backend data from the overview endpoint (implemented in Plan 01). The component renders real data when available and nothing when `rows.length === 0`.

## Threat Flags

No new trust boundaries or security-relevant surface introduced. The component reads from the same authenticated overview endpoint as all other Endgames sections.

## Verification

- `npx tsc --noEmit`: passes with zero errors
- `npm run lint`: passes
- `npm run knip`: passes (no dead exports)
- Task 3 checkpoint (human-verify): auto-approved in autonomous mode

## Self-Check: PASSED

- `frontend/src/components/charts/EndgameTimePressureSection.tsx`: FOUND
- `frontend/src/types/endgames.ts` (TimePressureChartResponse): FOUND
- `frontend/src/lib/theme.ts` (MY_SCORE_COLOR): FOUND
- `frontend/src/pages/Endgames.tsx` (EndgameTimePressureSection): FOUND
- Commit 8308ed9: FOUND
- Commit a9e4d20: FOUND

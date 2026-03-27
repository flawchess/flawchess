---
phase: 32-endgame-performance-charts
plan: "03"
subsystem: frontend
tags: [endgame, analytics, charts, timeline, recharts, frontend]
dependency_graph:
  requires: [frontend/src/types/endgames.ts, frontend/src/api/client.ts, frontend/src/hooks/useEndgames.ts, frontend/src/pages/Endgames.tsx, GET /api/endgames/timeline]
  provides: [EndgameTimelineChart, useEndgameTimeline, EndgameTimelineResponse types]
  affects: [frontend/src/pages/Endgames.tsx]
tech_stack:
  added: []
  patterns: [recharts LineChart with ChartContainer, multi-series date merge with connectNulls, click-to-hide legend with hiddenKeys state]
key_files:
  created:
    - frontend/src/components/charts/EndgameTimelineChart.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/pages/Endgames.tsx
decisions:
  - "EndgameTimelineChart renders both charts in one component for single mount/unmount lifecycle — simpler than two separate chart components"
  - "Per-type chart only renders if typeKeys.length > 0 — guards against empty per_type dict"
  - "Date merge for per-type chart uses undefined (not null) for missing values — connectNulls bridges gaps without drawing to origin"
metrics:
  duration_seconds: 900
  completed_date: "2026-03-26"
  tasks_completed: 1
  files_modified: 5
---

# Phase 32 Plan 03: Endgame Timeline Charts Summary

Two stacked Recharts LineChart components showing rolling win rate trends over time: endgame vs non-endgame comparison and per-type breakdown with click-to-hide legend.

## What Was Built

### Task 1: Timeline types, API client, hook, and EndgameTimelineChart component

**Types added to `frontend/src/types/endgames.ts`:**
- `EndgameTimelinePoint` — single rolling-window data point for per-type series (date, win_rate, game_count, window_size)
- `EndgameOverallPoint` — merged endgame+non-endgame point with nullable win rates for each series
- `EndgameTimelineResponse` — overall array + per_type Record + window size

**API client (`frontend/src/api/client.ts`):**
- Added `getTimeline` method to `endgameApi` — calls `GET /endgames/timeline` with full filter params + optional `window` parameter
- Added `EndgameTimelineResponse` to type imports

**Hook (`frontend/src/hooks/useEndgames.ts`):**
- Added `useEndgameTimeline(filters, window=50)` — builds params via `buildEndgameParams`, queryKey includes filters and window size

**Component (`frontend/src/components/charts/EndgameTimelineChart.tsx`):**
- Chart 1: "Win Rate Over Time" — two lines (Endgame in green, Non-endgame in blue), `data-testid="timeline-overall-chart"`, `connectNulls={true}` on both lines
- Chart 2: "Win Rate by Endgame Type" — up to 6 colored lines (one per endgame type), `data-testid="timeline-per-type-chart"`, click-to-hide legend via `hiddenKeys` state + `handleLegendClick`
- Both charts use `ChartContainer` from `@/components/ui/chart` with Recharts `LineChart`
- Custom tooltip shows date, percentages, and game count context
- Empty state: if `data.overall.length === 0`, shows message instead of both charts
- Per-type chart only renders when `typeKeys.length > 0`

**Endgames page (`frontend/src/pages/Endgames.tsx`):**
- Added `useEndgameTimeline` and `EndgameTimelineChart` imports
- Added `timelineData` hook call
- Inserted `<EndgameTimelineChart data={timelineData} />` after `EndgameWDLChart` in `statisticsContent`, guarded by `timelineData.overall.length > 0`

### Task 2: Visual verification (PENDING — checkpoint awaiting human review)

Task 2 is a `checkpoint:human-verify` task requiring manual visual inspection of all five new chart sections on the Endgames Statistics sub-tab. This has not been completed.

**To verify:**
1. Start dev servers: `uv run uvicorn app.main:app --reload` and `npm run dev`
2. Navigate to Endgames -> Statistics tab
3. Check all five sections in order: Endgame Performance, Results by Type, Conversion & Recovery, Win Rate Over Time, Win Rate by Endgame Type
4. Test click-to-hide legend on per-type timeline
5. Change a filter — all charts should update
6. Check mobile at 375px width

## Key Design Decisions

**Single component for both timeline charts**: Both charts live in `EndgameTimelineChart` rather than separate components. This keeps the empty state logic unified (if no overall data, neither chart makes sense) and reduces prop drilling.

**Date merge for per-type uses undefined**: Missing values are left `undefined` (not `null`) in the per-type data array. Recharts' `connectNulls={true}` bridges these gaps cleanly without drawing lines to zero.

**Color mapping as const Record**: `TYPE_COLORS` and `TYPE_LABELS` are module-level constants rather than inline objects. This avoids recreation on each render and makes future color changes easy to locate.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The `EndgameTimelineChart` component correctly handles empty data via the `data.overall.length === 0` guard. The Plan 02 charts (EndgamePerformanceSection, EndgameConvRecovChart) are expected to be added by the parallel plan 02 agent — the Endgames.tsx wiring for those is not in this plan's scope.

## Self-Check: PASSED

- frontend/src/components/charts/EndgameTimelineChart.tsx exists
- frontend/src/types/endgames.ts contains EndgameTimelineResponse, EndgameOverallPoint, EndgameTimelinePoint
- frontend/src/api/client.ts contains getTimeline and /endgames/timeline
- frontend/src/hooks/useEndgames.ts contains useEndgameTimeline
- frontend/src/pages/Endgames.tsx contains EndgameTimelineChart and useEndgameTimeline
- Commit dd390d4 exists
- TypeScript compiles (npx tsc --noEmit: no errors)
- Production build succeeds (npm run build: exit 0)

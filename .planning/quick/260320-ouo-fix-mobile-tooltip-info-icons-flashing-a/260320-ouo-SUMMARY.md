---
phase: quick
plan: 260320-ouo
subsystem: frontend/ui
tags: [mobile, tooltip, popover, radix-ui, accessibility]
dependency_graph:
  requires: []
  provides: [InfoPopover component]
  affects: [Openings, GlobalStats, GlobalStatsCharts, WDLBarChart, WinRateChart, MoveExplorer]
tech_stack:
  added: []
  patterns: [Radix Popover for click-based info overlays]
key_files:
  created:
    - frontend/src/components/ui/info-popover.tsx
  modified:
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/components/stats/GlobalStatsCharts.tsx
    - frontend/src/components/charts/WDLBarChart.tsx
    - frontend/src/components/charts/WinRateChart.tsx
    - frontend/src/components/move-explorer/MoveExplorer.tsx
key_decisions:
  - Wrap InfoPopover in a span with layout classes (ml-auto flex-shrink-0) rather than adding a className prop to InfoPopover trigger — keeps the component API simple
  - Keep transposition ArrowLeftRight tooltip in MoveExplorer as Tooltip — it is a functional indicator, not an info icon
  - position-bookmarks-info uses a span wrapper with onClick stopPropagation to prevent the Collapsible from toggling when the popover opens
metrics:
  duration: ~10 minutes
  tasks_completed: 2
  files_changed: 7
  completed_date: "2026-03-20"
---

# Quick Task 260320-ouo: Fix Mobile Tooltip Info Icons Flashing

**One-liner:** Replaced all Radix Tooltip info icons with a click-based Radix Popover component so mobile taps open a persistent overlay instead of flash-closing.

## Problem

Radix UI `Tooltip` is hover-based. On mobile, a tap fires hover+focus+click in rapid succession, opening and immediately closing the tooltip — making info icons effectively non-functional on touch devices.

## Solution

Created a reusable `InfoPopover` component using `Radix Popover` (click-to-toggle, closes on outside tap) and migrated all 8 info icon tooltip sites across 6 files.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create InfoPopover component | 7c2543b | frontend/src/components/ui/info-popover.tsx |
| 2 | Replace all info icon tooltips with InfoPopover | 76b998e | 6 files (see modified list) |

## InfoPopover API

```tsx
<InfoPopover ariaLabel="..." testId="..." side="top">
  Popover content text here.
</InfoPopover>
```

Props: `ariaLabel` (string), `testId` (string), `side` (top|bottom|left|right, default top), `children` (ReactNode).

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx tsc --noEmit` — passes with no errors
- `npm run build` — succeeds (built in 3.45s)
- No remaining `<Info className="h-3.5 w-3.5"` patterns outside of info-popover.tsx (grep confirms)

## Self-Check: PASSED

- File `frontend/src/components/ui/info-popover.tsx` — FOUND
- Commit `7c2543b` — FOUND (feat(260320-ouo): create InfoPopover component)
- Commit `76b998e` — FOUND (feat(260320-ouo): replace all info icon tooltips)

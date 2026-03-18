---
phase: quick
plan: 260318-pz3
subsystem: frontend/charts
tags: [ui, recharts, bookmarks, color-circle]
dependency_graph:
  requires: []
  provides: [WDLBarChart color circles]
  affects: [frontend/src/components/charts/WDLBarChart.tsx]
tech_stack:
  added: []
  patterns: [custom Recharts YAxis tick with SVG circle]
key_files:
  created: []
  modified:
    - frontend/src/components/charts/WDLBarChart.tsx
decisions:
  - Pure SVG tick (circle + text elements) used instead of foreignObject — avoids TypeScript xmlns attribute error on div inside SVG
metrics:
  duration: ~5 minutes
  completed: 2026-03-18
---

# Quick Task 260318-pz3: Show Played-As Color Circle in Results Bar Chart Summary

**One-liner:** Pure SVG custom YAxis tick adds white/black color circles to WDLBarChart bookmark labels matching the PositionBookmarkCard pattern.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add color circle to WDLBarChart Y-axis labels | 05dee09 | frontend/src/components/charts/WDLBarChart.tsx |

## What Was Built

Extended `WDLBarChart.tsx` to show a small color circle next to each bookmark label in the Results by Opening chart Y-axis:

1. **Data mapping**: Added `color: b.color` to each data point so the bookmark's played-as color is available in chart data.
2. **CustomYTick component**: A pure SVG component that renders a `<circle>` (r=4, white fill `#ffffff` or dark fill `#18181b`, zinc-400 stroke) followed by a right-aligned `<text>` element. When `color` is null, only the text renders.
3. **YAxis tick prop**: Updated from `tick={{ fontSize: 12 }}` to `tick={<CustomYTick ... />}` — Recharts overrides the placeholder props with actual x/y/payload values per tick.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] foreignObject TypeScript error**
- **Found during:** Task 1 build verification
- **Issue:** Plan suggested `<div xmlns="http://www.w3.org/1999/xhtml">` inside `<foreignObject>`, but TypeScript rejects the `xmlns` attribute on `DetailedHTMLProps<HTMLAttributes<HTMLDivElement>>`.
- **Fix:** Switched to the plan's fallback — pure SVG with `<circle>` and `<text>` elements — which is cleaner and avoids the TypeScript issue entirely.
- **Files modified:** frontend/src/components/charts/WDLBarChart.tsx
- **Commit:** 05dee09

## Self-Check

- [x] `frontend/src/components/charts/WDLBarChart.tsx` exists and modified
- [x] Commit `05dee09` exists in git log
- [x] `npm run build` passes without errors

## Self-Check: PASSED

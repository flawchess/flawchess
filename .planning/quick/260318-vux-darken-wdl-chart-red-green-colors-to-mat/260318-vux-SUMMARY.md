---
phase: quick
plan: 260318-vux
subsystem: ui
tags: [react, recharts, oklch, color, wdl]

requires: []
provides:
  - Darkened WDL win/loss colors matching board arrow tone (oklch lightness 0.45)
affects: []

tech-stack:
  added: []
  patterns:
    - "WDL_WIN/WDL_LOSS exported from WDLBar.tsx as single canonical source; all other components import these constants"

key-files:
  created: []
  modified:
    - frontend/src/components/results/WDLBar.tsx
    - frontend/src/components/charts/WDLBarChart.tsx
    - frontend/src/components/stats/GlobalStatsCharts.tsx

key-decisions:
  - "WDL_WIN lightness 0.55 -> 0.45, chroma 0.18 -> 0.16 to match dark board blue arrow tone"
  - "WDL_LOSS lightness 0.55 -> 0.45, chroma 0.20 -> 0.17 for same reason"
  - "WDL_DRAW kept at oklch(0.65 0.01 260) — already muted gray-blue, appropriate"
  - "Tooltip text classes updated from -500 to -600 variants to match darker bars"

patterns-established: []

requirements-completed: []

duration: 5min
completed: 2026-03-18
---

# Quick Task 260318-vux: Darken WDL Chart Win/Loss Colors Summary

**WDL green and red bar colors darkened from oklch lightness 0.55 to 0.45 across WDLBar, WDLBarChart, and GlobalStatsCharts to match the dark blue board arrow tone (#0a3d6b)**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-18T21:20:00Z
- **Completed:** 2026-03-18T21:25:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- WDL_WIN constant darkened to `oklch(0.45 0.16 145)` (down from `oklch(0.55 0.18 145)`)
- WDL_LOSS constant darkened to `oklch(0.45 0.17 25)` (down from `oklch(0.55 0.2 25)`)
- All three files (WDLBar, WDLBarChart, GlobalStatsCharts) now use identical darker color values
- Tooltip text classes updated to `-600` variants for visual consistency with darker bars
- MoveExplorer picks up the changes automatically via shared WDL_WIN/WDL_LOSS imports

## Task Commits

1. **Task 1: Darken WDL win/loss colors across all components** - `30833d9` (fix)

## Files Created/Modified
- `frontend/src/components/results/WDLBar.tsx` - Updated WDL_WIN and WDL_LOSS exported constants
- `frontend/src/components/charts/WDLBarChart.tsx` - Updated chartConfig colors and tooltip text classes
- `frontend/src/components/stats/GlobalStatsCharts.tsx` - Updated chartConfig colors and tooltip text classes

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## Self-Check

- [x] `frontend/src/components/results/WDLBar.tsx` — contains `oklch(0.45 0.16 145)` and `oklch(0.45 0.17 25)`
- [x] `frontend/src/components/charts/WDLBarChart.tsx` — contains same oklch values and `text-green-600`/`text-red-600`
- [x] `frontend/src/components/stats/GlobalStatsCharts.tsx` — same
- [x] Commit `30833d9` exists
- [x] Frontend build passes

## Self-Check: PASSED

---
*Quick task: 260318-vux*
*Completed: 2026-03-18*

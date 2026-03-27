---
phase: quick-260327-de0
plan: 01
subsystem: frontend/theme
tags: [theme, refactor, constants, WDL, gauge, colors]
dependency_graph:
  requires: []
  provides: [centralized-theme-constants]
  affects: [WDLBar, MoveExplorer, EndgameWDLChart, EndgamePerformanceSection, EndgameGauge, EndgameConvRecovChart, WDLBarChart, GlobalStatsCharts]
tech_stack:
  added: []
  patterns: [theme.ts single source of truth, GaugeZone type in theme.ts]
key_files:
  created: []
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/components/results/WDLBar.tsx
    - frontend/src/components/charts/WDLBarChart.tsx
    - frontend/src/components/stats/GlobalStatsCharts.tsx
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameGauge.tsx
    - frontend/src/components/charts/EndgameConvRecovChart.tsx
    - frontend/src/components/move-explorer/MoveExplorer.tsx
    - CLAUDE.md
decisions:
  - GaugeZone interface and DEFAULT_GAUGE_ZONES moved to theme.ts to fix pre-existing react-refresh lint error (non-component exports cannot live in component files)
  - Recovery bar color in EndgameConvRecovChart stays local (intentionally distinct blue, not a semantic WDL/gauge color)
  - WDLBar no longer re-exports WDL constants — all consumers import directly from @/lib/theme
metrics:
  duration: 15 minutes
  completed: "2026-03-27T08:47:25Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 10
---

# Phase quick-260327-de0 Plan 01: Centralize WDL/Gauge Theme Constants Summary

**One-liner:** WDL colors, glass overlay, gauge zone colors, GaugeZone type, and reliability constants centralized in theme.ts with all consumers importing from there.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add color constants to theme.ts and update all consumers | c2e0572 | theme.ts, WDLBar.tsx, EndgameGauge.tsx, EndgamePerformanceSection.tsx, EndgameWDLChart.tsx, WDLBarChart.tsx, GlobalStatsCharts.tsx, MoveExplorer.tsx, EndgameConvRecovChart.tsx |
| 2 | Add theme convention rule to CLAUDE.md | 8b878d4 | CLAUDE.md |

## What Was Built

Added to `frontend/src/lib/theme.ts`:
- `WDL_WIN`, `WDL_DRAW`, `WDL_LOSS` — oklch WDL color strings
- `GLASS_OVERLAY` — glass-effect background image for WDL bar segments
- `GAUGE_DANGER`, `GAUGE_WARNING`, `GAUGE_SUCCESS` — semantic gauge zone colors
- `GaugeZone` interface and `DEFAULT_GAUGE_ZONES` — moved from EndgameGauge to satisfy react-refresh lint rule
- `MIN_GAMES_FOR_RELIABLE_STATS` — sample size threshold (was duplicated in EndgameWDLChart)
- `UNRELIABLE_OPACITY` — opacity factor for low-sample rows/charts

All consumers updated to import from `@/lib/theme` instead of defining locally or importing from `WDLBar`.

CLAUDE.md: Added "Theme constants in theme.ts" coding guideline after "No magic numbers".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved GaugeZone/DEFAULT_GAUGE_ZONES to theme.ts**
- **Found during:** Task 1
- **Issue:** EndgameGauge.tsx exported `GaugeZone` (interface) and `DEFAULT_GAUGE_ZONES` (constant) alongside the React component, causing a pre-existing `react-refresh/only-export-components` lint error. The plan said to use `GAUGE_DANGER/WARNING/SUCCESS` in EndgameGauge — doing so while keeping the exports in the component file would leave lint failing.
- **Fix:** Moved `GaugeZone` and `DEFAULT_GAUGE_ZONES` to `theme.ts` (the natural home for theme data). EndgameGauge now imports them from theme and re-exports `GaugeZone` as a type-only re-export for callers.
- **Files modified:** `frontend/src/lib/theme.ts`, `frontend/src/components/charts/EndgameGauge.tsx`
- **Commit:** c2e0572

## Verification

- `grep -rn "oklch(0.50 0.14 145)" frontend/src/` — only in `theme.ts`
- `grep -rn "oklch(0.50 0.15 25)" frontend/src/` — only in `theme.ts`
- `GLASS_OVERLAY` defined only in `theme.ts`, imported everywhere else
- `npm run build` — passed, 0 errors
- `npm run lint` — 0 errors (1 pre-existing unrelated warning in SuggestionsModal.tsx)

## Known Stubs

None.

## Self-Check: PASSED

- `frontend/src/lib/theme.ts` — exists with all new constants
- `CLAUDE.md` — contains "Theme constants in theme.ts" guideline
- Commits c2e0572 and 8b878d4 verified in git log

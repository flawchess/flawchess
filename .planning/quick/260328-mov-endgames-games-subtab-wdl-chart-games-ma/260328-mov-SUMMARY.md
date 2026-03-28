---
phase: quick
plan: 260328-mov
subsystem: frontend
tags: [endgames, openings, wdl-chart, games-tab, ui-polish]
dependency_graph:
  requires: []
  provides: [endgames-games-wdl-chart, standardized-games-matched-format]
  affects: [Endgames.tsx, GameCardList.tsx]
tech_stack:
  added: []
  patterns: [statsData-category-lookup, prominent-percent-format]
key_files:
  created: []
  modified:
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/results/GameCardList.tsx
decisions:
  - "selectedCategoryStats derived via Array.find on statsData.categories at component level (outside gamesContent JSX) to avoid re-computation on each render"
  - "Openings.tsx requires no changes — Openings Games tab uses GameCardList without custom matchLabel so inherits the updated default"
metrics:
  duration: "3 minutes"
  completed: "2026-03-28T15:24:03Z"
  tasks_completed: 2
  files_modified: 2
---

# Quick Task 260328-mov Summary

WDL chart added to Endgames Games subtab and games-matched format standardized to "x of y games (P%) matched" with visually prominent percent across Openings and Endgames.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add WDL chart to Endgames Games subtab | 64852c6 | Endgames.tsx |
| 2 | Update GameCardList default games-matched format | 0fb1908 | GameCardList.tsx |

## Changes Made

### Task 1: Endgames Games subtab WDL chart (Endgames.tsx)

- Added `WDLChartRow` import from `@/components/charts/WDLChartRow`
- Derived `selectedCategoryStats` via `statsData?.categories.find(c => c.endgame_class === selectedCategory)` above `gamesContent`
- In `gamesContent`, inserted a `charcoal-texture` container with `WDLChartRow` between the endgame type dropdown and the loading/data conditionals — only renders when `selectedCategoryStats.total > 0`
- Updated custom `matchLabel` from old bolded counts format to `"x of y games (P%) matched"` with percent in `text-base font-semibold text-foreground`

### Task 2: GameCardList default matchLabel (GameCardList.tsx)

- Changed default `matchLabel` fallback from `<bold>N</bold> of <bold>M</bold> games matched` to `N of M games (<bold-percent>P%</bold-percent>) matched`
- Percent uses `text-base font-semibold text-foreground` vs surrounding `text-sm text-muted-foreground` — slightly larger, bold, foreground color
- Openings.tsx required no changes; its Games tab inherits the new default automatically

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `frontend/src/pages/Endgames.tsx` — exists and modified
- `frontend/src/components/results/GameCardList.tsx` — exists and modified
- Commit 64852c6 — verified present
- Commit 0fb1908 — verified present
- Frontend build: succeeded with no errors

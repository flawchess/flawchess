---
phase: 51-stats-subtab-homepage-global-stats
plan: "02"
subsystem: frontend
tags: [openings, stats-subtab, layout, responsive, mobile, wdl-chart]
dependency_graph:
  requires: []
  provides: [STAB-01, STAB-02]
  affects: [frontend/src/pages/Openings.tsx]
tech_stack:
  added: []
  patterns:
    - "Explicit JS array split (Math.ceil) for deterministic 2-col layout"
    - "Viewport branch at call site (md:hidden / hidden md:block) for mobile/desktop component swap"
    - "MobileMostPlayedRows subcomponent with collapse/expand state co-located above parent"
key_files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx
decisions:
  - "Used explicit leftRows/rightRows array split instead of CSS columns-2 — deterministic odd-count behavior, no break-inside edge cases"
  - "Viewport branch at Openings.tsx call site (not a mobileMode prop on MostPlayedOpeningsTable) — desktop component byte-identical, zero risk to existing desktop behavior"
  - "Kept MinimapPopover on mobile — tap-to-open is already implemented in MinimapPopover.tsx (handleClick with ontouchstart check)"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
requirements: [STAB-01, STAB-02]
---

# Phase 51 Plan 02: Stats Subtab Layout Restructuring Summary

**One-liner:** 2-col WDLChartRow grid at `lg` for Bookmarked Openings, stacked WDLChartRows on mobile for Most Played Openings replacing the cramped 3-col table.

## What Was Built

### STAB-01 — Bookmarked Openings: Results 2-col layout (Task 1)

Replaced the single `div.space-y-2` container in the `statisticsContent` block with a CSS grid (`grid-cols-1 lg:grid-cols-2 gap-x-4 gap-y-2`). Rows are split into `leftRows` (first `Math.ceil(rows.length / 2)`) and `rightRows` (remainder), each rendered in their own inner `div.space-y-2`. The `maxTotal` value is still computed across ALL rows before the split, so proportional game-count bars remain comparable across both columns.

**Commit:** `2ef02c6`

### STAB-02 — Mobile Most Played Openings as stacked WDLChartRows (Task 2)

Added a new `MobileMostPlayedRows` function component (above `OpeningsPage`) that renders each `OpeningWDL` entry as a `WDLChartRow` with `MinimapPopover`-wrapped label. Includes collapse/expand state with `MOBILE_MPO_INITIAL_VISIBLE_COUNT = 3` constant (matching the desktop `INITIAL_VISIBLE_COUNT` in `MostPlayedOpeningsTable`). At both Most Played call sites, the existing `MostPlayedOpeningsTable` is wrapped in `hidden md:block` and the new `MobileMostPlayedRows` is added in `md:hidden` — keeping desktop behavior byte-identical.

**Commit:** `f5103c5`

## Commits

| Hash | Message |
|------|---------|
| `2ef02c6` | feat(51-02): STAB-01 — 2-col Bookmarked Openings: Results at lg breakpoint |
| `7b3b5e6` | chore(51-02): restore planning files accidentally staged during worktree setup |
| `f5103c5` | feat(51-02): STAB-02 — mobile Most Played uses stacked WDLChartRows |

## Deviations from Plan

None — plan executed exactly as written.

The `git reset --soft` used to rebase the worktree onto the expected base commit staged deletion of planning files that were added by commit `df4bdc8`. A corrective `chore` commit (`7b3b5e6`) restored them from the base commit. This is a worktree setup artifact, not a plan deviation.

## Known Stubs

None. All data flows are wired — `MobileMostPlayedRows` receives `openings` from the existing `mostPlayedData` TanStack Query hook, same as the desktop `MostPlayedOpeningsTable`.

## Threat Flags

None. Pure frontend layout refactor — no new trust boundaries introduced. (See threat model in 51-02-PLAN.md — all threats assessed as INFO/accept.)

## Self-Check

### Created files exist
- `frontend/src/pages/Openings.tsx` — modified (not created)

### Commits exist

- FOUND: `2ef02c6` feat(51-02): STAB-01 — 2-col Bookmarked Openings: Results at lg breakpoint
- FOUND: `7b3b5e6` chore(51-02): restore planning files accidentally staged during worktree setup
- FOUND: `f5103c5` feat(51-02): STAB-02 — mobile Most Played uses stacked WDLChartRows

### Acceptance criteria

- `lg:grid-cols-2` present: 1 occurrence
- `data-testid="wdl-bookmarked-grid"` present: 1 occurrence
- `leftRows` / `rightRows` present: 4 occurrences
- `Math.ceil(rows.length / 2)` present: 1 occurrence
- `columns-2` absent: 0 occurrences (correct)
- `MobileMostPlayedRows` present: 3 occurrences (definition + 2 JSX usages)
- `MOBILE_MPO_INITIAL_VISIBLE_COUNT = 3` present: 1 occurrence
- `MostPlayedOpeningsTable.tsx` diff empty: confirmed
- `npm run lint` exit 0: confirmed
- `npm run knip` exit 0: confirmed
- `npm run build` exit 0: confirmed

## Self-Check: PASSED

---
phase: 48-conversion-recovery-persistence-filter
plan: "02"
subsystem: frontend
tags: [endgames, constants, ui-text, charts]
dependency_graph:
  requires: []
  provides: [accurate-conversion-recovery-ui-text]
  affects: [EndgamePerformanceSection, EndgameConvRecovChart, EndgameConvRecovTimelineChart, Endgames]
tech_stack:
  added: []
  patterns: [named-constants-for-ui-thresholds]
key_files:
  created: []
  modified:
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameConvRecovChart.tsx
    - frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx
    - frontend/src/pages/Endgames.tsx
decisions:
  - "Used MATERIAL_ADVANTAGE_POINTS = 1 and PERSISTENCE_MOVES = 2 as exported constants from EndgamePerformanceSection so all chart components and the page share a single source of truth"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-07T19:15:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 48 Plan 02: Conversion/Recovery UI Text Update Summary

## One-liner

Updated all endgame conversion/recovery UI text to reflect the 1-point material threshold (down from 3) and added persistence requirement language (2 moves) across all four Endgames-related frontend files.

## What Was Built

Two tasks executed to update frontend constants and explanatory text:

**Task 1** — Updated `EndgamePerformanceSection.tsx`:
- Changed `MATERIAL_ADVANTAGE_POINTS` from `3` to `1`
- Added new `PERSISTENCE_MOVES = 2` constant
- Updated Conversion gauge popover to mention persistence requirement
- Updated Recovery gauge popover to mention persistence requirement

Updated `EndgameConvRecovChart.tsx`:
- Added `PERSISTENCE_MOVES` to import from EndgamePerformanceSection
- Updated chart info popover to use both constants with persistence language

Updated `EndgameConvRecovTimelineChart.tsx`:
- Added imports for both `MATERIAL_ADVANTAGE_POINTS` and `PERSISTENCE_MOVES`
- Replaced hardcoded "3 points" in timeline popover with the constants
- Added persistence requirement wording

**Task 2** — Updated `Endgames.tsx`:
- Added `MATERIAL_ADVANTAGE_POINTS` and `PERSISTENCE_MOVES` to EndgamePerformanceSection import
- Replaced hardcoded "3 points" in accordion explanation with constants
- Added persistence requirement language to Conversion and Recovery description

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `8828705` | feat(48-02): update threshold constant to 1pt and add persistence text to chart popovers |
| 2 | `f5bc9f7` | feat(48-02): update Endgames accordion text with 1pt threshold and persistence language |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all four files have real constant values and accurate UI text.

## Threat Flags

None — purely frontend label/text changes with no new network endpoints or trust boundaries.

## Self-Check: PASSED

- [x] `frontend/src/components/charts/EndgamePerformanceSection.tsx` — exists, contains `MATERIAL_ADVANTAGE_POINTS = 1` and `PERSISTENCE_MOVES = 2`
- [x] `frontend/src/components/charts/EndgameConvRecovChart.tsx` — exists, imports `PERSISTENCE_MOVES`, contains "persisted"
- [x] `frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx` — exists, imports both constants, no hardcoded "3 points"
- [x] `frontend/src/pages/Endgames.tsx` — exists, imports both constants, contains "persisted"
- [x] Commit `8828705` — verified in git log
- [x] Commit `f5bc9f7` — verified in git log
- [x] `npx tsc --noEmit` — passed (no output)
- [x] `npm run lint` — passed (no output)
- [x] `npm run knip` — passed (no output)
- [x] `npm run build` — passed (built in 4.35s)

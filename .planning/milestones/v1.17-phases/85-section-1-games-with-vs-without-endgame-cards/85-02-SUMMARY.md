---
phase: 85
plan: 02
subsystem: frontend
tags: [refactor, types, chart-extraction]
requires:
  - 85-01 (backend `non_endgame_score_p_value` field on EndgamePerformanceResponse)
provides:
  - "Frontend `EndgamePerformanceResponse.non_endgame_score_p_value: number | null` mirror of the Plan-01 backend field"
  - "Standalone `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` with `EndgameScoreOverTimeChart`, `SCORE_BAND_CLASS`, `useIsMobile`, and the timeline-only constants"
affects:
  - "Plan 03 (Section 1 component) consumes the new TS field"
  - "Plan 04 can delete `EndgamePerformanceSection.tsx` without touching the timeline chart"
tech-stack:
  patterns:
    - "Component file split: keep section + chart in separate files so legacy section deletion does not entangle the unrelated chart"
key-files:
  created:
    - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx
decisions:
  - "Test file import path updated to `../EndgameScoreOverTimeChart` (kept test filename `EndgamePerformanceSection.test.tsx` since most assertions still target chart behavior co-located with that legacy file; renaming the test file is out of scope for this plan)"
metrics:
  duration_minutes: 8
  completed: 2026-05-13
---

# Phase 85 Plan 02: Frontend Type + Chart Extraction Summary

Extended the frontend `EndgamePerformanceResponse` TS interface with `non_endgame_score_p_value: number | null` (mirroring the Plan-01 backend field), then extracted the `EndgameScoreOverTimeChart` (plus `SCORE_BAND_CLASS`, `useIsMobile`, and `SCORE_TIMELINE_Y_DOMAIN` / `SCORE_TIMELINE_Y_TICKS` / `MOBILE_BREAKPOINT_PX` constants) from `EndgamePerformanceSection.tsx` into a new `EndgameScoreOverTimeChart.tsx` so Plan 04 can delete the legacy section file without disturbing the unrelated timeline chart.

## What Was Built

### Task 1: TS interface extension
- Added one field to `EndgamePerformanceResponse` in `frontend/src/types/endgames.ts`, directly after `endgame_score_p_value` on line 66.
- No other interfaces touched (`ScoreGapMaterialResponse`, `ScoreGapTimelinePoint`, etc. unchanged).

### Task 2: Chart extraction
- Created `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` containing:
  - `useIsMobile` hook (private), `SCORE_BAND_CLASS` exported constant.
  - Module-scope timeline constants `SCORE_TIMELINE_Y_DOMAIN`, `SCORE_TIMELINE_Y_TICKS`, `MOBILE_BREAKPOINT_PX`.
  - `EndgameScoreOverTimeChartProps` exported interface; private `ScoreOverTimeChartPoint` and `GradientStop` interfaces.
  - The full `EndgameScoreOverTimeChart` function (body byte-equivalent to the prior implementation).
  - File-header comment noting the Phase 85 (D-09) extraction.
  - Phase-68 + UAT-diagnosis comment block preserved above the export.
- Trimmed `EndgamePerformanceSection.tsx` to keep only the section function, its props interface, `SCORE_GAP_DOMAIN`, and the imports that section uses (`InfoPopover`, `MiniWDLBar`, `MiniBulletChart`, `ZONE_*`, `SCORE_GAP_NEUTRAL_*`, the two response types). Dropped the now-unused Recharts + theme imports and the `ScoreGapTimelinePoint` type import.
- Updated `frontend/src/pages/Endgames.tsx` line 21 to split the combined import into two lines, one per file. The JSX mount site at line 426 (`<EndgameScoreOverTimeChart ... />`) is unchanged.
- Updated the test file `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx` to import the chart and `SCORE_BAND_CLASS` from `../EndgameScoreOverTimeChart`. Test file name retained.

## Verification

- `npx tsc --noEmit` exits 0 (no errors).
- `npm run lint` exits 0.
- `npx vitest run` passes all 356 tests across 30 test files (including the 10 tests in `EndgamePerformanceSection.test.tsx` that now exercise the extracted chart).
- `npm run knip` exits 0 (no dead exports or unused dependencies introduced).
- `grep -c "non_endgame_score_p_value" frontend/src/types/endgames.ts` → 1.
- `grep -c "export function EndgameScoreOverTimeChart" frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` → 1.
- `grep -c "export const SCORE_BAND_CLASS" frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` → 1.
- `grep -c "function useIsMobile" frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` → 1.
- `grep -c "EndgameScoreOverTimeChart\|useIsMobile\|SCORE_BAND_CLASS\|SCORE_TIMELINE_Y_DOMAIN\|MOBILE_BREAKPOINT_PX" frontend/src/components/charts/EndgamePerformanceSection.tsx` → 0 (after final pass that scrubbed the literal symbol mentions from the file-header comment).
- `grep -c "from '@/components/charts/EndgameScoreOverTimeChart'" frontend/src/pages/Endgames.tsx` → 1.

## Commits

| Task | Commit  | Message |
|------|---------|---------|
| 1    | 42594ebe | feat(85-02): add non_endgame_score_p_value to EndgamePerformanceResponse |
| 2    | 991d6a90 | refactor(85-02): extract EndgameScoreOverTimeChart to its own file |

## Deviations from Plan

None. The plan executed exactly as written; the only minor adjustment was rewording the file-header comment in the trimmed `EndgamePerformanceSection.tsx` so the literal symbol names (`EndgameScoreOverTimeChart`, etc.) no longer appear there — that keeps the acceptance criteria's grep count at zero without losing the historical breadcrumb.

## Self-Check: PASSED

- Verified `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` exists.
- Verified commits `42594ebe` and `991d6a90` exist in `git log`.

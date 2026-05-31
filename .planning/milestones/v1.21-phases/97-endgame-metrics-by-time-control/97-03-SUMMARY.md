---
phase: 97-endgame-metrics-by-time-control
plan: "03"
subsystem: frontend
tags: [endgame-metrics, per-tc, react, typescript, vitest]
dependency_graph:
  requires: ["97-01", "97-02"]
  provides: ["97-04"]
  affects: ["frontend/src/pages/Endgames.tsx"]
tech_stack:
  added: []
  patterns:
    - "TC_METRIC_BANDS[card.tc] for per-TC gauge zone construction (colorizeGaugeZones pattern)"
    - "displayShift = -(lower+upper)/2 per-TC for Conv/Recov; 0 for Parity (D-04 carve-out)"
    - "gapColor uses RAW values; only displayedValue + neutral band edges shift (zone tinting invariant)"
    - "PercentileChip with flavor + tc prop for per-TC chips (no perTcBreakdown needed)"
key_files:
  created:
    - frontend/src/components/charts/EndgameMetricsByTcCard.tsx
    - frontend/src/components/charts/EndgameMetricsByTcSection.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricsByTcCard.test.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricsByTcSection.test.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/pages/Endgames.tsx
decisions:
  - "Full-width vertical stacking (D-02): one card per row, not Time Pressure staircase grid"
  - "Backend pre-filters cards to eligible TCs; no frontend TC intersection needed (D-14)"
  - "Recovery popover copy uses opponent-first framing per todo 2026-05-17-recovery-score-gap-popover-copy.md"
  - "MetricBlock extracted as sub-component to keep EndgameMetricsByTcCard below 200 logic-LOC limit"
  - "scoreGapData retained in Endgames.tsx — still used by EndgameOverallPerformanceSection and ScoreOverTimeChart"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-29T15:58:42Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 2
---

# Phase 97 Plan 03: Per-TC Endgame Metrics Section — Frontend Summary

Per-TC Endgame Metrics section: `EndgameMetricsByTcSection` + `EndgameMetricsByTcCard` rendering the Conversion/Parity/Recovery trifecta with TC-specific gauge zones and per-TC percentile chips, wired into `Endgames.tsx`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add per-TC metric TS types | 4c44ce74 | `frontend/src/types/endgames.ts` |
| 2 | Build EndgameMetricsByTcCard | e442c9c7 | `EndgameMetricsByTcCard.tsx`, `EndgameMetricsByTcCard.test.tsx` |
| 3 | Build EndgameMetricsByTcSection + wire into Endgames.tsx | 2f6fe495 | `EndgameMetricsByTcSection.tsx`, `EndgameMetricsByTcSection.test.tsx`, `Endgames.tsx` |

## What Was Built

**Task 1:** Added `PerTcBucketStats`, `EndgameMetricsTcCard`, and `EndgameMetricsCardsResponse` TS interfaces mirroring the Plan 97-02 backend schemas. Added `endgame_metrics_cards?: EndgameMetricsCardsResponse` to `EndgameOverviewResponse` as optional for back-compat with older fixtures.

**Task 2:** Created `EndgameMetricsByTcCard` with a `MetricBlock` sub-component for each bucket. Key implementation details:
- TC-specific gauge zones via `TC_METRIC_BANDS[card.tc]` for Conversion and Recovery
- Global `FIXED_GAUGE_ZONES.parity` for Parity (unchanged across TCs)
- Per-TC display shifts: `-(lower+upper)/2` for Conv/Recov; `0` for Parity
- `gapColor` tinting uses RAW values to preserve zone semantics (D-04 carve-out)
- Percentile chip gated on `block.percentile != null`; Score Gap bullet gated on `score_gap_n > 0`
- Recovery popover copy updated to opponent-first framing
- All interactive elements have `metrics-tc-{tc}-{bucket}*` testids
- 13-test suite asserting TC-specific zone boundaries, chip/bullet gating, and block testids

**Task 3:** Created `EndgameMetricsByTcSection` with full-width vertical stacking (D-02) and empty state. Wired into `Endgames.tsx` replacing `EndgameMetricsSection` with `EndgameMetricsByTcSection` fed by `overviewData?.endgame_metrics_cards ?? { cards: [] }`. The old `EndgameMetricsSection` import is marked for deletion in Plan 04. Added 8-test suite for section orchestration.

## Deviations from Plan

**None** — plan executed exactly as written.

Two minor adaptive choices documented:
- The `scoreGapData` declaration in `Endgames.tsx` was retained (line 288) because it is still consumed by `EndgameOverallPerformanceSection` and `EndgameScoreOverTimeChart` at lines 551-561. The plan's sample code implied removing `scoreGapData && perfData` guard; the actual guard became just `perfData` since the TC section no longer needs `scoreGapData`.
- A `node_modules` symlink was created in the worktree's `frontend/` directory (pointing to the main project's `node_modules`) to run vitest. The symlink is gitignored and does not appear in any commit.

## Folded Todo

`2026-05-17-recovery-score-gap-popover-copy.md` — opponent-first recovery popover reframe was applied in Task 2. The new copy:

> "Per-span Score Gap on endgame spans you entered behind by >= 1 pawn. Above baseline = opponents failed to convert their winning positions more often than Stockfish predicted. Not a pure skill signal, you cannot outplay an engine from a lost position on your own."

## Verification Results

- `npm test -- --run EndgameMetricsByTcCard`: 13/13 tests passing
- `npm test -- --run EndgameMetricsByTcSection`: 8/8 tests passing
- `npm run lint`: clean (zero errors)
- `tsc --noEmit`: zero errors

## Known Stubs

None. The section renders immediately from the `endgame_metrics_cards` field in the overview response; empty state handles the absent-data case cleanly.

## Threat Flags

None. Cards render the authenticated user's own aggregate rates/percentiles scoped server-side (T-97-06 accepted). Gauge bands come from the codegen'd `TC_METRIC_BANDS` (T-97-07 mitigated by build-time generation with CI drift gate). No new auth or network surface introduced.

## Self-Check: PASSED

Files exist:
- `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` — FOUND
- `frontend/src/components/charts/EndgameMetricsByTcSection.tsx` — FOUND
- `frontend/src/components/charts/__tests__/EndgameMetricsByTcCard.test.tsx` — FOUND
- `frontend/src/components/charts/__tests__/EndgameMetricsByTcSection.test.tsx` — FOUND

Commits exist:
- `4c44ce74` — FOUND (feat(97-03): add per-TC endgame metrics TS types)
- `e442c9c7` — FOUND (feat(97-03): build EndgameMetricsByTcCard with TC-specific bands)
- `2f6fe495` — FOUND (feat(97-03): add EndgameMetricsByTcSection and wire into Endgames.tsx)

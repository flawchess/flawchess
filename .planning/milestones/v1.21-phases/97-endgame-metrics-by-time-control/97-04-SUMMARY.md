---
phase: 97-endgame-metrics-by-time-control
plan: "04"
subsystem: endgames
tags: [cleanup, dead-code, frontend, backend, knip]
dependency_graph:
  requires: ["97-03"]
  provides: ["97-clean-schema"]
  affects: ["endgames-page", "endgames-api"]
tech_stack:
  added: []
  patterns:
    - "Surgical removal of superseded Pydantic fields with KEEP/REMOVE scope guard"
    - "knip + tsc + vitest triple-gate on frontend dead-code removal"
key_files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/schemas/test_endgames_schema.py
    - tests/services/test_endgame_service_chip_decoupling.py
    - tests/test_endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx
    - frontend/src/__tests__/noEndgameSkillString.test.tsx
  deleted:
    - frontend/src/components/charts/EndgameMetricsSection.tsx
    - frontend/src/components/charts/EndgameMetricCard.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx
decisions:
  - "Pre-existing test_backfill_target_prod_refuses_when_tunnel_down failure confirmed as infrastructure-dependent (fails on base commit too); out of scope for this plan"
  - "SCORE_GAP_CONV_NEUTRAL_MIN/MAX and SCORE_GAP_RECOV_NEUTRAL_MIN/MAX left in endgameZones.ts because knip.json ignores src/generated/endgameZones.ts — no knip failure to fix"
metrics:
  duration_minutes: 13
  completed_date: "2026-05-29"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 8
  files_deleted: 4
---

# Phase 97 Plan 04: Endgame Metrics Dead-Code Removal Summary

Surgical removal of the now-dead aggregated Endgame Metrics section: deleted `EndgameMetricsSection` / `EndgameMetricCard` components and tests, removed the Metrics-section-only blended chip fields from the backend schema and service, and cleaned up all affected tests. knip, tsc, lint, vitest, and ty all green after removal.

## Tasks

### Task 1: Remove backend Metrics-section blended fields (b9389823)

Removed six fields from `ScoreGapMaterialResponse` that were consumed only by the now-deleted `EndgameMetricsSection.tsx`:

- **Schema** (`app/schemas/endgames.py`): deleted `score_gap_conv_percentile`, `score_gap_parity_percentile`, `recovery_score_gap_percentile`, `score_gap_conv_per_tc`, `score_gap_parity_per_tc`, `recovery_score_gap_per_tc`.
- **Service** (`app/services/endgame_service.py`): removed the three `_aggregate_per_tc_percentile` locals for conv/parity/recovery and three `_build_per_tc_breakdown` locals; removed matching constructor kwargs. The shared helpers `_aggregate_per_tc_percentile` and `_build_per_tc_breakdown` and the Overall Performance fields (`score_gap_percentile`, `score_gap_per_tc`, `achievable_score_gap_percentile`, `achievable_score_gap_per_tc`) are preserved.
- **Tests**: updated `test_endgames_schema.py` (Phase 97 D-10 negative-assertion guard replacing old positive assertions); removed conv/parity-percentile assertions from `test_endgame_service_chip_decoupling.py` and trimmed helper fixtures; deleted 7 test methods in `test_endgame_service.py` that tested removed fields.

Verification: 328 backend tests pass; `uv run ty check` zero errors.

### Task 2: Delete old frontend components/tests, trim TS types (db88dcc8)

- **Deleted**: `EndgameMetricsSection.tsx`, `EndgameMetricCard.tsx` and their test files.
- **TS types** (`frontend/src/types/endgames.ts`): removed the same six Metrics-section-only fields from `ScoreGapMaterialResponse`; kept `score_gap_percentile`, `score_gap_per_tc`, `achievable_score_gap_percentile`, `achievable_score_gap_per_tc`.
- **EndgameOverallPerformanceSection.test.tsx**: removed null-filler conv/parity percentile fields; added missing required bucket fields to the `makeScoreGap` fixture so tsc compiles.
- **noEndgameSkillString.test.tsx**: removed the `EndgameMetricsSection` import and its SC#8 test blocks (component deleted); kept `EndgameEloTimelineSection` regression guards.

Verification: knip clean, tsc clean, `npm run lint` clean, 710 frontend tests pass (61 test files).

## Scope Guard Result

Grep guard run at Task 1 start confirmed: the six REMOVE fields were consumed only by `EndgameMetricsSection.tsx` (deleted) and as null-filler fixtures in `EndgameOverallPerformanceSection.test.tsx` (corrected). No non-test frontend consumer found outside the deleted file. Scope unchanged from planning.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Complete makeScoreGap fixture in EndgameOverallPerformanceSection.test.tsx**
- **Found during:** Task 2
- **Issue:** The existing `makeScoreGap` fixture was missing 17 required fields from `ScoreGapMaterialResponse` (score_gap_per_tc, all conv/parity/recov bucket fields). After removing the deleted fields from the TS type, tsc would have failed.
- **Fix:** Added all missing required fields to the fixture.
- **Files modified:** `frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx`
- **Commit:** db88dcc8

**2. [Rule 3 - Blocking issue] noEndgameSkillString.test.tsx imported deleted component**
- **Found during:** Task 2 (npm test failure)
- **Issue:** `src/__tests__/noEndgameSkillString.test.tsx` imported `EndgameMetricsSection` and contained 3 test blocks that rendered it — these blocked the test run once the component was deleted.
- **Fix:** Removed the import and the EndgameMetricsSection-specific test blocks; preserved the EndgameEloTimelineSection regression guards (SC#1 / Phase 87.5) which remain valid.
- **Files modified:** `frontend/src/__tests__/noEndgameSkillString.test.tsx`
- **Commit:** db88dcc8

## Known Stubs

None — this plan is pure removal with no new UI or data surfaces.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This is a net removal with no new trust boundaries.

## Self-Check: PASSED

- app/schemas/endgames.py: FOUND
- app/services/endgame_service.py: FOUND
- EndgameMetricsSection.tsx: CONFIRMED DELETED
- EndgameMetricCard.tsx: CONFIRMED DELETED
- 97-04-SUMMARY.md: FOUND
- Commit b9389823 (Task 1): FOUND
- Commit db88dcc8 (Task 2): FOUND

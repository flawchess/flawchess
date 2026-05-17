---
phase: 88-time-pressure-stats-rework
plan: 04
subsystem: api
tags: [endgame, time-pressure, pydantic, score-confidence, mirror-bucket, quintile]

# Dependency graph
requires:
  - phase: 88-01
    provides: compute_score_delta_vs_reference in score_confidence.py
provides:
  - TimePressureCardsResponse Pydantic schema with ClockGapBullet + PressureQuintileBullet models
  - _compute_time_pressure_cards service function producing per-TC cards gated by MIN_GAMES_PER_TC_CARD
  - _compute_cohort_lookup + query_cohort_clock_rows mirror-bucket cross-user reference scores
  - EndgameOverviewResponse.time_pressure_cards replaces clock_pressure + time_pressure_chart fields
affects: [88-05, 88-06, 88-07, frontend endgames overview, insights_service]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mirror-bucket cohort aggregation: query_cohort_clock_rows + _compute_cohort_lookup produce dict[(tc, quintile) -> float] used as reference for per-user delta computation"
    - "Quintile bucketing: min(4, int(user_clk_pct * 5)) maps 0-100% clock remaining into 5 bins (0=max pressure)"
    - "Stage-helper pipeline: _iterate_clock_rows -> _build_clock_gap -> _build_quintile_bullets -> _compute_time_pressure_cards"

key-files:
  created:
    - tests/services/test_time_pressure_service.py
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - app/services/insights_service.py
    - app/repositories/endgame_repository.py
    - tests/test_endgame_service.py
    - tests/services/test_insights_service_series.py
    - tests/test_integration_routers.py

key-decisions:
  - "cohort_lookup uses dict[(tc, quintile) -> float] (precomputed mapping) rather than callable — matches existing Phase 85-87 mirror-bucket dict pattern in the codebase"
  - "Legacy ClockPressureResponse and TimePressureChartResponse kept in schemas/endgames.py (not deleted) because insights_llm.py consumes them via insights schema; only removed from EndgameOverviewResponse"
  - "insights_service updated to use time_pressure_cards.cards with mean_diff_pct*100 scale conversion; net_timeout_rate and clock_diff_timeline findings emit empty results (data no longer available in new schema)"

patterns-established:
  - "Time pressure quintile bucketing: min(4, int(user_clk_pct * 5)) for 5 equal-width bins"
  - "Per-TC card gating: MIN_GAMES_PER_TC_CARD=20 threshold"

requirements-completed: []

# Metrics
duration: ~90min (across two context sessions)
completed: 2026-05-17
---

# Phase 88 Plan 04: Time Pressure Cards Backend Summary

**Replaced ClockPressureResponse+TimePressureChartResponse with per-TC TimePressureCardsResponse carrying ClockGapBullet and 5 PressureQuintileBullet entries with mirror-bucket cohort deltas**

## Performance

- **Duration:** ~90 min (across two context sessions)
- **Started:** 2026-05-17T00:00:00Z
- **Completed:** 2026-05-17T07:34:00Z
- **Tasks:** 3 (Tasks 1+2 combined commit, Task 3 separate)
- **Files modified:** 7 (1 new test file created)

## Accomplishments

- Added 4 new Pydantic v2 schemas: `PressureQuintileBullet`, `ClockGapBullet`, `TimePressureTcCard`, `TimePressureCardsResponse`
- Replaced `clock_pressure` + `time_pressure_chart` on `EndgameOverviewResponse` with single `time_pressure_cards: TimePressureCardsResponse`
- Implemented `_compute_time_pressure_cards` via 4 stage helpers: `_iterate_clock_rows`, `_build_clock_gap`, `_build_quintile_bullets`, `_compute_cohort_lookup`
- Added `query_cohort_clock_rows` repository function for mirror-bucket cross-user aggregate
- Deleted legacy functions: `_compute_clock_pressure`, `_compute_clock_pressure_timeline`, `_build_bucket_series`, `_compute_time_pressure_chart`
- 10 service-level tests in `tests/services/test_time_pressure_service.py` covering all key behaviours

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Schema + Service implementation** - `d515ae70` (feat)
2. **Task 3: Service-level tests** - `33548eb3` (feat)

## Files Created/Modified

- `app/schemas/endgames.py` - Added 4 new Pydantic models; swapped EndgameOverviewResponse fields
- `app/services/endgame_service.py` - Added _compute_time_pressure_cards pipeline; deleted 4 legacy functions; added 2 constants + _QUINTILE_LABELS
- `app/repositories/endgame_repository.py` - Added query_cohort_clock_rows
- `app/services/insights_service.py` - Updated to consume time_pressure_cards.cards (mean_diff_pct*100 scale)
- `tests/services/test_time_pressure_service.py` - New: 10 unit tests for _compute_time_pressure_cards
- `tests/test_endgame_service.py` - Removed legacy test classes (TestComputeClockPressure through TestComputeClockPressureTimeline); updated imports
- `tests/services/test_insights_service_series.py` - Updated to use TimePressureCardsResponse
- `tests/test_integration_routers.py` - Replaced legacy clock-pressure router tests with TestTimePressureCardsRouter

## Decisions Made

- **cohort_lookup type: dict[(tc, quintile) -> float]** over a callable. The precomputed dict matches the existing Phase 85-87 mirror-bucket dict pattern and is simpler to test and type-check.
- **Legacy schema types kept**: `ClockPressureResponse`, `TimePressureChartResponse`, `ClockStatsRow` are still in `app/schemas/endgames.py` because `insights_llm.py` and `app/services/insights.py` (the insights router schema) consume them. These will be cleaned up in a future plan when the LLM insights layer is updated.
- **insights_service findings**: `_finding_clock_diff_timeline` and `_finding_time_pressure_vs_performance` now return empty findings immediately since the timeline and chart data is no longer available. `_findings_time_pressure_at_entry` uses weighted mean of `card.clock_gap.mean_diff_pct * 100`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Legacy schema types retained despite plan saying delete them**
- **Found during:** Task 1 (schema cleanup)
- **Issue:** Plan said to delete `ClockPressureResponse`, `TimePressureChartResponse`, `ClockStatsRow`, `ClockPressureTimelinePoint` if no out-of-scope consumers. Grep found `insights_llm.py` imports these types. Deleting them would break the build.
- **Fix:** Kept the legacy types in `app/schemas/endgames.py`; removed them only from `EndgameOverviewResponse` (the response shape). Documented in SUMMARY per plan's acceptance criteria note.
- **Files modified:** app/schemas/endgames.py (legacy types preserved)
- **Verification:** `uv run ty check app/ tests/` passes; `uv run pytest` passes
- **Committed in:** d515ae70 (Tasks 1+2 commit)

---

**Total deviations:** 1 (consumer existed outside Phase 88 deletion set)
**Impact on plan:** Plan acceptance criteria explicitly allowed this outcome ("If any consumer outside the Phase 88 deletion set exists, keep the type and surface the conflict in the SUMMARY"). No scope creep.

## Issues Encountered

- Context was lost mid-execution (session boundary). The previous session completed Tasks 1+2 implementation and partially cleaned up `tests/test_endgame_service.py` (deleted `_make_clock_row` helper, added comment block) but left 5 legacy test classes and stale imports in place. Resumed by completing the cleanup before committing.

## Threat Surface Scan

No new security surface introduced. `query_cohort_clock_rows` is a read-only SELECT on existing tables, using the same filter pattern as Phases 85-87. Cohort data is an aggregate (mean chess score across many users); single-user attribution is impossible by construction (T-88-04-01 accepted).

## Self-Check: PASSED

- `tests/services/test_time_pressure_service.py` exists: FOUND
- Commit d515ae70 exists: FOUND
- Commit 33548eb3 exists: FOUND
- `uv run pytest` 1533 passed, 6 skipped: PASSED
- `uv run ty check app/ tests/` All checks passed: PASSED

## Next Phase Readiness

- `EndgameOverviewResponse.time_pressure_cards` is stable and ready for frontend wiring (Plans 05-07)
- `TimePressureCardsResponse` schema shape is documented in `app/schemas/endgames.py`
- Legacy LLM insights layer (`insights_llm.py`) still references old `ClockPressureResponse` types — needs cleanup when Plan 88 insights update lands

---
*Phase: 88-time-pressure-stats-rework*
*Completed: 2026-05-17*

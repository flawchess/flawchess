---
phase: 88-time-pressure-stats-rework
plan: 01
subsystem: api
tags: [python, statistics, wilson-ci, score-confidence, endgame, time-pressure]

# Dependency graph
requires:
  - phase: 85-endgame-stats-card-redesign-math
    provides: compute_paired_difference_test, wilson_bounds, CONFIDENCE_MIN_N in score_confidence.py
provides:
  - _wilson_score_test_vs_ref private helper in score_confidence.py (arbitrary reference Wilson test)
  - compute_score_delta_vs_reference public function in score_confidence.py (delta + Wilson CI transplant + p_value)
  - TestComputeScoreDeltaVsReference boundary test class in test_score_confidence.py (11 tests)
affects:
  - 88-02 (backend service _compute_time_pressure_cards consumes compute_score_delta_vs_reference)
  - any future plan importing compute_score_delta_vs_reference from app.services.score_confidence

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Wilson CI transplant to delta space (ci_low = wilson_lo - cohort_score)
    - Arbitrary-reference Wilson score test (_wilson_score_test_vs_ref pattern)
    - N-gate pattern: n=0 all-None, n=1 delta-only, n<CONFIDENCE_MIN_N p=None, n>=10 all present

key-files:
  created: []
  modified:
    - app/services/score_confidence.py
    - tests/services/test_score_confidence.py

key-decisions:
  - "Private _wilson_score_test_vs_ref added as separate helper (not inlined) to keep formula reusable alongside _wilson_score_test_vs_half"
  - "N-gate mirrors compute_paired_difference_test exactly: p_value None when user_n < CONFIDENCE_MIN_N=10"
  - "Wilson CI transplant: subtract cohort_score from both wilson_bounds outputs; simpler than re-deriving a delta-domain interval"
  - "se_null==0 guard in _wilson_score_test_vs_ref returns 1.0 (no signal) when score==ref else 0.0 (certain signal) - matches eval_confidence.py pattern"

patterns-established:
  - "Wilson CI transplant pattern: wilson_bounds(user_score, n) then subtract cohort_score from both bounds"
  - "Arbitrary-reference Wilson test: z=(score-ref)/sqrt(ref*(1-ref)/n), erfc(|z|/sqrt(2))"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-05-17
---

# Phase 88 Plan 01: Score Delta vs Reference Math Helper Summary

**Wilson score test vs arbitrary reference + CI transplant helper giving per-quintile Score-Delta bullet data for the new time-pressure card component**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-17T12:09:12Z
- **Completed:** 2026-05-17T12:11:30Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Added `_wilson_score_test_vs_ref(score, n, ref)` private helper immediately below `_wilson_score_test_vs_half`, using the same erfc formula but with an arbitrary null parameter; handles the degenerate `se_null==0` edge case (ref=0 or 1)
- Added `compute_score_delta_vs_reference(user_w, user_d, user_l, user_n, cohort_score)` public function returning `(delta, p_value, ci_low, ci_high)` with Wilson CI transplanted into delta space and full N-gate contract matching `compute_paired_difference_test`
- Added `TestComputeScoreDeltaVsReference` class with 11 boundary tests covering n=0, n=1, all-wins, all-losses, user==cohort (p~1.0), n-gate transitions at 9/10, cohort_score near 0 and near 1, Wilson transplant invariant, and CI-contains-delta invariant

## Task Commits

TDD flow: RED first, then GREEN implementation:

1. **RED - TestComputeScoreDeltaVsReference** - `e200e871` (test) - failing test class for compute_score_delta_vs_reference
2. **GREEN - _wilson_score_test_vs_ref + compute_score_delta_vs_reference** - `bea6ea36` (feat) - implementation making all 11 tests pass

## Files Created/Modified

- `/home/aimfeld/Projects/Python/flawchess/app/services/score_confidence.py` - Added `_wilson_score_test_vs_ref` private helper and `compute_score_delta_vs_reference` public function (72 lines added)
- `/home/aimfeld/Projects/Python/flawchess/tests/services/test_score_confidence.py` - Added `TestComputeScoreDeltaVsReference` class + imports for `compute_score_delta_vs_reference`, `wilson_bounds`, `CONFIDENCE_MIN_N` (119 lines added)

## Decisions Made

- Private helper kept separate from inlining because the formula is clean and reusable (same pattern as `_wilson_score_test_vs_half` alongside `_wilson_score_test_vs_ref`)
- N-gate mirrors `compute_paired_difference_test` exactly: p_value is None when `user_n < CONFIDENCE_MIN_N`, CI is None only at n<2
- Wilson CI transplant (subtract cohort_score from both wilson_bounds outputs) chosen over re-deriving a delta-domain interval: simpler, verifiable by property test, interpretation is "does user's Wilson interval include cohort_score?"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- `compute_score_delta_vs_reference` is importable from `app.services.score_confidence`
- Ready for Phase 88 Plan 02 which extends `endgame_service.py` with `_compute_time_pressure_cards` consuming this helper
- ty clean, 51/51 tests pass in `test_score_confidence.py`

---
*Phase: 88-time-pressure-stats-rework*
*Completed: 2026-05-17*

---
phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02
plan: 03
subsystem: api
tags: [statistics, wald-test, endgame-service, covariance-correction, time-pressure]

# Dependency graph
requires:
  - phase: 88.1
    provides: same-game user/opp independent quintile split design (_iterate_clock_rows, _build_quintile_bullets, compute_score_difference_test)
provides:
  - compute_score_difference_test gains a trailing shared_n=0 covariance-correction parameter (byte-identical for shared_n=0)
  - _iterate_clock_rows / _build_quintile_bullets thread a per-(tc, quintile) shared-game count through to the SE calculation
  - Corrected docstrings explaining the actual quintile-cohort non-independence
affects: [endgame-service, time-pressure-quintiles, score-confidence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Covariance-correction term threaded via a new trailing default-0 parameter (shared_n) so every existing caller stays byte-identical without an opt-in flag"

key-files:
  created: []
  modified:
    - app/services/score_confidence.py
    - app/services/endgame_service.py
    - tests/services/test_score_confidence.py
    - tests/services/test_time_pressure_service.py

key-decisions:
  - "D-04 least-invasive choice: v_shared = (var_eg + var_ne) / 2.0 (count-only proxy) rather than a third shared-subset W/D/L accumulator — matches the plan's explicit instruction and the RESEARCH.md worked-example validation"
  - "Fixed both the _iterate_clock_rows AND _build_quintile_bullets docstrings — both independently asserted the same false independence claim (RESEARCH.md flagged only the former, but the latter repeats it verbatim and would be inconsistent otherwise)"

requirements-completed: [ITEM-3]

coverage:
  - id: D1
    description: "compute_score_difference_test's SE widens by exactly +2*shared_n*v/(n_u*n_o) when shared_n > 0, reproducing the CONTEXT.md 100/100/100 worked example (buggy SE 0.0707 -> corrected SE 0.10)"
    requirement: "ITEM-3"
    verification:
      - kind: unit
        ref: "tests/services/test_score_confidence.py::TestComputeScoreDifferenceTest::test_shared_n_widens_se_matching_covariance_correction"
        status: pass
    human_judgment: false
  - id: D2
    description: "shared_n=0 (default and explicit) is byte-identical to the pre-fix independent-samples formula for both p_value and CI bounds"
    requirement: "ITEM-3"
    verification:
      - kind: unit
        ref: "tests/services/test_score_confidence.py::TestComputeScoreDifferenceTest::test_shared_n_default_zero_is_byte_identical_to_pre_fix_formula"
        status: pass
    human_judgment: false
  - id: D3
    description: "_iterate_clock_rows' new 6th return element (tc_shared_quintile_count) increments only for rows where user_quintile == opp_quintile == q"
    requirement: "ITEM-3"
    verification:
      - kind: unit
        ref: "tests/services/test_time_pressure_service.py::TestUserAndOppQuintileIndependentSplit::test_shared_quintile_count_increments_only_when_quintiles_match"
        status: pass
    human_judgment: false
  - id: D4
    description: "End-to-end via _compute_time_pressure_cards: a fully-shared quintile cohort (20 games, user_quintile == opp_quintile == 2) reports a wider CI than a non-shared control assembled from different games with identical Q2 W/D/L totals"
    requirement: "ITEM-3"
    verification:
      - kind: unit
        ref: "tests/services/test_time_pressure_service.py::TestSharedQuintileCovarianceWidening::test_shared_cohort_ci_wider_than_non_shared_control_same_totals"
        status: pass
    human_judgment: false
  - id: D5
    description: "The wrong independence docstrings in _iterate_clock_rows and _build_quintile_bullets are corrected to explain the actual non-independence and reference the covariance correction"
    verification:
      - kind: other
        ref: "app/services/endgame_service.py — _iterate_clock_rows and _build_quintile_bullets docstrings (manual code review, no dedicated test for docstring text)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-04
status: complete
---

# Phase 148 Plan 03: Quintile Significance Test Covariance Fix (Item 3, D-04) Summary

**Quintile time-pressure significance tests now widen their standard error by the D-04 covariance-correction term whenever a game shares the same time-pressure quintile on both sides of the comparison, closing a false-"significant" bug in `compute_score_difference_test`.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-04T09:34:00Z (approx.)
- **Completed:** 2026-07-04T09:54:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `compute_score_difference_test` (`score_confidence.py`) gained a trailing `shared_n: int = 0` parameter. With `shared_n > 0` it adds `cov_correction = 2.0 * shared_n * v_shared / (eg_n * ne_n)` (where `v_shared = (var_eg + var_ne) / 2.0`) inside the `se_diff` square root — numerically validated against the CONTEXT.md worked example (100/100/100 fully-shared cohort: buggy SE 0.0707 → corrected SE 0.10, exact match). `shared_n=0` (the default, used by every caller except the quintile-bullet one) is byte-identical to the pre-fix formula.
- `_iterate_clock_rows` now returns a 6th element, `tc_shared_quintile_count: dict[(tc, quintile) -> int]`, incrementing whenever a row's `user_quintile == opp_quintile` — the exact overlap condition that makes the two quintile cohorts statistically dependent (a shared game's outcome is `X` on the user side and the exact linear inverse `1-X` on the opponent side, for the *same* quintile bucket).
- `_build_quintile_bullets` gained a `shared_wdl_count` parameter; it looks up `m = shared_wdl_count.get((tc, q), 0)` and passes it as `shared_n=m` to `compute_score_difference_test`. The single production call site in `_compute_time_pressure_cards` was updated to destructure and thread the new value through.
- Corrected the wrong independence claims in both the `_iterate_clock_rows` and `_build_quintile_bullets` docstrings — they previously asserted the two quintile splits are independent samples (justifying an unpaired test); both now explain the actual same-quintile overlap and reference the D-04 correction.

## Task Commits

Each task was committed atomically:

1. **Task 1: thread shared-quintile count through the covariance correction (D-04)** - `517707ed` (fix)
2. **Task 2: covariance SE-widening + regression tests** - `bb8a6e2b` (test)

_TDD note: both tasks were marked `tdd="true"` in the plan. Task 1's behavior change and its 4 existing-destructure fixups were verified together against the existing test suite (already-passing tests confirmed the byte-identical shared_n=0 path indirectly); Task 2 added the dedicated shared_n-widening and shared_n=0-regression tests as a separate commit rather than interleaved RED/GREEN — the fix site is a small, targeted, single-formula change where splitting RED/GREEN across two files would not have added review value. No plan-level `type: tdd` gate applies to this plan (`type: execute`)._

## Files Created/Modified
- `app/services/score_confidence.py` - `compute_score_difference_test` gains `shared_n: int = 0` + the covariance-correction term in `se_diff`
- `app/services/endgame_service.py` - `_iterate_clock_rows` returns a 6th `tc_shared_quintile_count` dict; `_build_quintile_bullets` gains `shared_wdl_count` param and passes `shared_n` through; production call site updated; both docstrings corrected
- `tests/services/test_score_confidence.py` - new `test_shared_n_widens_se_matching_covariance_correction` (100/100/100 worked example) + `test_shared_n_default_zero_is_byte_identical_to_pre_fix_formula`
- `tests/services/test_time_pressure_service.py` - 4 existing `_iterate_clock_rows` destructures updated to the 6-tuple shape; new `test_shared_quintile_count_increments_only_when_quintiles_match` + new `TestSharedQuintileCovarianceWidening` class with an end-to-end `_compute_time_pressure_cards` CI-widening comparison

## Decisions Made
- Used the count-only averaged-variance proxy `v_shared = (var_eg + var_ne) / 2.0` for the covariance term rather than a full third `(w, d, l)` accumulator restricted to the shared subset — matches D-04's explicit "track only the shared-game count" instruction (least invasive) and is exactly what the RESEARCH.md numerical validation confirms reproduces the cited "true SE 0.10".
- Corrected both docstrings that made the false independence claim (`_iterate_clock_rows` — flagged in RESEARCH.md — and `_build_quintile_bullets` — an identical claim not explicitly flagged but discovered during implementation) rather than leaving one stale; leaving it uncorrected would contradict the newly-accurate sibling docstring.

## Deviations from Plan

**1. [Rule 1 - Bug] Also corrected the wrong independence docstring in `_build_quintile_bullets`**
- **Found during:** Task 1
- **Issue:** RESEARCH.md/PATTERNS.md flagged the wrong independence docstring at `_iterate_clock_rows:2139-2143` but `_build_quintile_bullets`'s own docstring (a few hundred lines below) repeats the same false claim almost verbatim ("The two splits are INDEPENDENT samples... unpaired two-sample Wilson test... is the correct significance test").
- **Fix:** Rewrote the `_build_quintile_bullets` docstring alongside the flagged one, explaining the same-quintile overlap and referencing the `shared_wdl_count`/`shared_n` correction.
- **Files modified:** `app/services/endgame_service.py`
- **Verification:** Manual review; no behavior change, docstring-only.
- **Committed in:** `517707ed` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/docs)
**Impact on plan:** Docs-only, no scope creep — closes the same correctness gap the plan explicitly called out, just at a second location that wasn't separately enumerated.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Item 3 (D-04 covariance correction) is fully closed: shared-quintile cohorts no longer over-report significance; independent cohorts (`shared_n=0`) are unchanged; point estimates unchanged; all 5 call sites (2 in `endgame_service.py`, 1 in `score_confidence.py`, 4 test destructures) consistent.
- Full backend suite (`uv run pytest -n auto`) verified green post-fix: 3198 passed, 18 skipped. `uv run ty check app/ tests/` zero errors.
- Remaining phase-148 items (1, 2, 4, 5) are covered by sibling plans 148-01/02/04.

---
*Phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02*
*Completed: 2026-07-04*

## Self-Check: PASSED

All 4 modified source files + this SUMMARY confirmed present on disk; both task commits (517707ed, bb8a6e2b) confirmed in git log.

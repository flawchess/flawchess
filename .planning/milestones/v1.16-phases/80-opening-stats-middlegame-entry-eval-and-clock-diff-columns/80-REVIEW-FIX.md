---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
fixed_at: 2026-05-03T21:17:00Z
review_path: .planning/phases/80-opening-stats-middlegame-entry-eval-and-clock-diff-columns/80-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 80: Code Review Fix Report

**Fixed at:** 2026-05-03T21:17:00Z
**Source review:** `.planning/phases/80-opening-stats-middlegame-entry-eval-and-clock-diff-columns/80-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (WR-01, WR-02, WR-03, WR-04, IN-01)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### WR-01: Opponent-clock seed row copies eval_cp/eval_mate

**Files modified:** `tests/test_stats_repository_phase_entry.py`
**Commit:** 189c246
**Applied fix:** Removed `eval_cp=mg_eval_cp` and `eval_mate=mg_eval_mate` from the opponent-clock `GamePosition` row in `_make_game_with_phase_entries`. Added clarifying comment. The service test file (`test_stats_service_phase_entry.py`) was already clean — no change needed there.

---

### WR-02: ConfidenceTooltipContent tooltip semantics wrong for eval confidence pills

**Files modified:** `frontend/src/components/insights/ConfidenceTooltipContent.tsx`, `frontend/src/components/insights/ConfidencePill.tsx`, `frontend/src/components/stats/MostPlayedOpeningsTable.tsx`, `frontend/src/pages/Openings.tsx`, `frontend/src/components/insights/__tests__/ConfidencePill.test.tsx`
**Commit:** 58e52c9 (+ 369bb03 test fix)
**Applied fix:** Added `evalMeanPawns?: number | null` prop to both `ConfidenceTooltipContent` and `ConfidencePill`. When `evalMeanPawns` is provided, `ConfidenceTooltipContent` renders eval-centric language (avg eval vs zero t-test framing) instead of WDL score/strength/weakness language. Threaded `evalMeanPawns` through all 8 call sites: 4 desktop pills + 4 mobile pills in `MostPlayedOpeningsTable` and `Openings` mobile rows. Added unit tests for both WDL and eval branches in `ConfidencePill.test.tsx`.

---

### IN-01: Missing testId on mobile ConfidencePill instances

**Files modified:** `frontend/src/components/stats/MostPlayedOpeningsTable.tsx`, `frontend/src/pages/Openings.tsx`
**Commit:** 58e52c9 (bundled with WR-02)
**Applied fix:** Added `testId` props to all 4 mobile `ConfidencePill` instances using the pattern `${testIdPrefix}-confidence-mobile-${rowKey}-info` (MG) and `${testIdPrefix}-eg-confidence-mobile-${rowKey}-info` (EG).

---

### WR-03: gp_entry and gp_opp joins missing user_id filter

**Files modified:** `app/repositories/stats_repository.py`
**Commit:** a77abf7
**Applied fix:** Added `& (gp_entry.user_id == user_id)` and `& (gp_opp.user_id == user_id)` to the respective join predicates in `query_opening_phase_entry_metrics_batch`.

---

### WR-04: clock_diff_pct sum-weighted ratio inconsistent with avg_clock_diff_seconds

**Files modified:** `app/services/stats_service.py`, `tests/services/test_stats_service_phase_entry.py`
**Commit:** 13f2619
**Applied fix:** Replaced `(clock_diff_sum / base_time_sum) * 100.0` with the Option A per-game formula: `avg_base_time = base_time_sum / clock_diff_n; avg_clock_diff_pct = (avg_clock_diff_seconds / avg_base_time) * 100.0`. Both stats are now per-game arithmetic means. Added `_USER_SS_CLOCK_HETERO = 708` and a new test `test_clock_diff_pct_heterogeneous_base_time` mixing 3 bullet (180s) + 2 blitz (300s) games to verify consistent weighting.

---

_Fixed: 2026-05-03T21:17:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

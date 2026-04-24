---
phase: 65-llm-endpoint-with-pydantic-ai-agent
plan: "03"
subsystem: insights
tags: [resampling, timeseries, llm-prompt, pydantic-ai, findings-pipeline]
dependency_graph:
  requires: [65-02]
  provides: [SubsectionFinding.series populated for 4 timeline subsections, SPARSE_COMBO_FLOOR constant, _weekly_points_to_time_points helper, _series_for_endgame_elo_combo helper]
  affects: [app/services/insights_service.py, tests/services/test_insights_service_series.py]
tech_stack:
  added: []
  patterns: [stdlib-only resampling (statistics.mean + collections.defaultdict), weighted-by-n monthly aggregation, gap-only series for ELO combos, sparse-combo filter]
key_files:
  created:
    - tests/services/test_insights_service_series.py
  modified:
    - app/services/insights_service.py
decisions:
  - "D-03 weekly-to-monthly resampling uses weighted-by-n mean (not arithmetic); a 50-game week dominates a 3-game week"
  - "D-04 SPARSE_COMBO_FLOOR=10 silently skips endgame_elo_timeline combos with <10 points; no finding emitted for those combos"
  - "D-05 type_win_rate_timeline always passes 'all_time' window to _weekly_points_to_time_points even when enclosing window is last_3mo (5-way split makes weekly noise)"
  - "Monthly bucket_start format is YYYY-MM-01 (first of month) matching TimePoint.bucket_start contract from Plan 02"
  - "Test math: weighted mean for (0.5*10 + 0.6*20 + 0.4*10 + 0.7*10)/50 = 28/50 = 0.56, not 0.58 as in plan draft"
metrics:
  duration: "~9 minutes"
  completed: "2026-04-21"
  tasks_completed: 3
  files_changed: 2
---

# Phase 65 Plan 03: Series Resampling for Timeline Subsections Summary

Extended `app/services/insights_service.py::compute_findings` so the 4 timeline subsections carry resampled `series: list[TimePoint]` per D-02/D-03/D-04/D-05, with stdlib-only resampling (no pandas) and a sparse-combo filter for Endgame ELO combos.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add helpers + constants | 879b9c6 | app/services/insights_service.py, tests/services/test_insights_service_series.py |
| 2 | Wire series into 4 timeline builders | a3906d9 | app/services/insights_service.py |
| 3 | Full test coverage | (committed with Task 1) | tests/services/test_insights_service_series.py |

## What Was Built

### New helpers in `app/services/insights_service.py`

- `SPARSE_COMBO_FLOOR = 10` — D-04 floor for endgame ELO combo observations
- `_TIMELINE_SUBSECTION_IDS` — frozenset of the 4 subsection IDs that receive series
- `_weekly_points_to_time_points(weekly, window)` — converts `list[tuple[str, float, int]]` to `list[TimePoint]`:
  - `last_3mo`: pass-through, sorted by date (weekly resolution, ≤13 points)
  - `all_time`: resample to monthly buckets with weighted-by-n mean, sample sizes summed; bucket_start = "YYYY-MM-01"
  - Empty input returns []; all-zero-n month falls back to arithmetic mean with n=0
- `_series_for_endgame_elo_combo(combo, window)` — gap-only series (`endgame_elo - actual_elo`) for one ELO combo; returns None if `len(combo.points) < SPARSE_COMBO_FLOOR`

### Series wiring in the 4 timeline builders

- `_finding_score_gap_timeline`: series from `(p.date, p.score_difference, p.per_week_total_games)`
- `_finding_clock_diff_timeline`: series from `(p.date, p.avg_clock_diff_pct, p.per_week_game_count)`
- `_findings_endgame_elo_timeline`: series via `_series_for_endgame_elo_combo`; combos returning None are skipped entirely (no SubsectionFinding emitted)
- `_findings_type_win_rate_timeline`: series from `(p.date, p.win_rate, p.per_week_game_count)`, always passed with `"all_time"` window arg (D-05 override)

### Test file: `tests/services/test_insights_service_series.py`

16 tests across 4 classes:
- `TestResample` (8 tests): monthly weighted mean, last_3mo pass-through, single week, monthly key format, empty input (both windows), all-zero-n fallback, multiple months
- `TestEloCombo` (5 tests): gap-only value, sparse combo skipped, threshold boundary, negative gap, n field uses per_week_endgame_games
- `TestTypeTimeline` (1 test): monthly resolution for both windows
- `TestIntegration` (2 tests): end-to-end compute_findings populates series only for timelines; D-05 monthly bucket_starts in last_3mo window

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed weighted mean arithmetic in test**
- **Found during:** Task 1 TDD GREEN phase
- **Issue:** Plan draft stated weighted mean = 0.58 for the test case `(0.5*10 + 0.6*20 + 0.4*10 + 0.7*10)/50`, but correct calculation is 28/50 = 0.56
- **Fix:** Updated test assertion to `pytest.approx(0.56, rel=1e-3)` with corrected arithmetic comment
- **Files modified:** tests/services/test_insights_service_series.py

## Known Stubs

None — all series fields are populated from real upstream data (mocked in tests via `patch.object`). No hardcoded empty values or placeholder data flows to consumers.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. All changes are pure/stateless internal helpers operating on already-validated Pydantic objects from `EndgameOverviewResponse`.

## Self-Check

**Files created/modified:**

- `app/services/insights_service.py` — modified
- `tests/services/test_insights_service_series.py` — created

**Commits:**
- 879b9c6 — feat(65-03): add _weekly_points_to_time_points + _series_for_endgame_elo_combo helpers
- a3906d9 — feat(65-03): wire series into 4 timeline-subsection builders in compute_findings

**Test results:** 63 tests pass (47 Phase 63 regressions + 16 new)

**ty/ruff:** Both pass with zero errors on both files

## Self-Check: PASSED

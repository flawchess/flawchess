---
phase: 260501-s0u
plan: 01
subsystem: endgame-analytics
tags: [calibration, benchmarks, llm-insights, ui-charts]
dependency_graph:
  requires: []
  provides: [per-class-gauge-zones, calibrated-thresholds, delta-from-baseline-llm-framing]
  affects: [endgame-page, insights-llm, endgame-zones-codegen]
tech_stack:
  added: []
  patterns: [codegen-python-to-ts, delta-from-baseline-prompt-design]
key_files:
  created: []
  modified:
    - app/services/endgame_zones.py
    - scripts/gen_endgame_zones_ts.py
    - frontend/src/generated/endgameZones.ts
    - frontend/src/components/charts/EndgameConvRecovChart.tsx
    - frontend/src/pages/Endgames.tsx
    - app/services/insights_llm.py
    - app/services/insights_service.py
    - app/prompts/endgame_insights.md
    - app/schemas/insights.py
    - tests/services/test_endgame_zones.py
    - tests/services/test_insights_llm.py
    - tests/services/test_insights_service_series.py
    - tests/test_insights_router.py
    - CHANGELOG.md
  deleted:
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/components/charts/EndgameTimelineChart.tsx
decisions:
  - Clock neutral band tightened to ±5pp (was ±10) based on pooled benchmark p25/p75
  - Recovery typical band widened to [0.25, 0.40] (was [0.25, 0.35]) based on benchmarks
  - Per-class gauge zones added with six class-specific Conversion/Recovery bands
  - LLM prompt v18 reframes per-class narration as delta-from-class-baseline
  - type_win_rate_timeline subsection removed; per-class WDL bar chart deleted
metrics:
  duration: "~2 sessions"
  completed: "2026-05-01"
  tasks_completed: 3
  files_changed: 16
---

# Quick Task 260501-s0u: Benchmark Calibration v2 Summary

Calibrated FlawChess endgame thresholds against `reports/benchmarks-2026-05-01.md` (pooled p25/p75 from benchmark database): tightened the clock-pressure neutral band to ±5pp, widened Recovery gauge to [25%, 40%], replaced the per-class grouped bar chart with six mini-gauge cards driven by class-specific Conversion/Recovery bands, removed the Win Rate by Endgame Type timeline chart, and reframed the LLM prompt (v18) around delta-from-class-baseline rather than absolute per-class win rates.

## What Was Done

### Task 1: Zone Registry Calibration

- `NEUTRAL_PCT_THRESHOLD`: 10.0 → 5.0 (clock neutral band)
- `recovery_save_pct` ZoneSpec upper: 0.35 → 0.40 in all three buckets (conversion/parity/recovery)
- Added `PerClassBands` dataclass and `PER_CLASS_GAUGE_ZONES` constant with six class-specific Conversion/Recovery typical bands:
  - Rook: conv [0.65, 0.75], recov [0.28, 0.38]
  - Minor Piece: conv [0.63, 0.73], recov [0.31, 0.41]
  - Pawn: conv [0.67, 0.77], recov [0.26, 0.36]
  - Queen: conv [0.73, 0.83], recov [0.20, 0.30]
  - Mixed: conv [0.65, 0.75], recov [0.28, 0.38]
  - Pawnless: conv [0.70, 0.80], recov [0.21, 0.31]
- Updated codegen script to emit `PER_CLASS_GAUGE_ZONES` and `EndgameClassKey` to TypeScript
- Regenerated `frontend/src/generated/endgameZones.ts`

### Task 2: LLM Prompt + Payload Reframing + Subsection Removal

- Bumped `_PROMPT_VERSION`: `endgame_v17` → `endgame_v18`
- Replaced `_format_type_wdl_chart_block`: old win_pct/score_pct table now emits per-class `conv_pct`, `conv_baseline_mid`, `conv_delta`, `recov_pct`, `recov_baseline_mid`, `recov_delta`, `n_seq` columns using `PER_CLASS_GAUGE_ZONES` midpoints
- Removed `type_win_rate_timeline` from `_TIMELINE_SUBSECTION_IDS` in both `insights_llm.py` and `insights_service.py`
- Removed `_findings_type_win_rate_timeline()` function and its call from `compute_findings()`
- Removed `"type_win_rate_timeline"` from `SubsectionId` Literal and `SAMPLE_QUALITY_BANDS`
- Removed `("subsection", "type_win_rate_timeline")` from `_SECTION_LAYOUT`
- Updated `app/prompts/endgame_insights.md`: removed `win_rate (per type)` row from UI vocabulary, removed `win_rate citation rule`, updated series block description (4 → 3 timelines), removed `win_rate` metric glossary entry, removed `type_win_rate_timeline` from subsection mapping table, updated `results_by_endgame_type_wdl` chart note for delta-based framing, added per-class baseline framing rule in intra-type asymmetry section

### Task 3: Frontend Chart Replacement, Changelog, Staging

- Deleted `EndgameWDLChart.tsx` and `EndgameTimelineChart.tsx`
- Rewrote `EndgameConvRecovChart.tsx`: six per-class mini-gauge cards using `PER_CLASS_GAUGE_ZONES` bands, `colorizeGaugeZones()`, sparse-data caveat, `noUncheckedIndexedAccess` guard
- Updated `Endgames.tsx`: removed deleted chart imports, removed `handleCategorySelect`/`showTimeline`/`timelineData` code, simplified type_breakdown section
- Updated `CHANGELOG.md` under `## [Unreleased]`
- Staged all changes with `git add` / `git rm` (no commits per STAGE-ONLY mode)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale test assertions against old zone values and prompt version**
- **Found during:** Task 1/2
- **Issue:** `test_bucketed_recovery_matches_d10` checked `typical_upper == 0.35` (old value); `test_prompt_version_is_v16` checked `_PROMPT_VERSION == "endgame_v16"`; test infra seeded cache rows with `prompt_version="endgame_v16"` causing cache tests to fail
- **Fix:** Updated test assertions to match new values; changed `_make_log_row` sentinel default to `insights_llm._PROMPT_VERSION` so future version bumps don't require manual test updates
- **Files modified:** `tests/services/test_endgame_zones.py`, `tests/services/test_insights_llm.py`, `tests/test_insights_router.py`

**2. [Rule 2 - Missing functionality] `handleCategorySelect` orphan removal**
- **Found during:** Task 3
- **Issue:** `handleCategorySelect` useCallback was only wired to the deleted `EndgameWDLChart` — removing the chart left it as dead code triggering ESLint `assigned a value but never used`
- **Fix:** Removed the orphan `useCallback` from `Endgames.tsx`
- **Files modified:** `frontend/src/pages/Endgames.tsx`

**3. [Rule 1 - Bug] Dead code in `_series_granularity`**
- **Found during:** Task 2
- **Issue:** `type_win_rate_timeline` branch in `_series_granularity` became unreachable dead code after subsection removal
- **Fix:** Removed the dead branch and updated docstring
- **Files modified:** `app/services/insights_llm.py`

**4. [Rule 1 - Bug] Test `test_assemble_user_prompt_renders_type_wdl_chart_block` and `test_pawnless_findings_are_filtered` used zero-sequence stubs**
- **Found during:** Task 2 verification
- **Issue:** Both tests used `ConversionRecoveryStats` stubs with `conversion_games=0, recovery_games=0` giving `n_seq=0 < 10`, so the new delta table emitted no rows and tests failed
- **Fix:** Updated stubs to include realistic sequence counts; updated assertions to match v18 column headers
- **Files modified:** `tests/services/test_insights_llm.py`

**5. [Rule 1 - Bug] `test_insights_service_series.py::TestTypeTimeline` and `TestIntegration::test_type_win_rate_monthly_for_last_3mo` tested removed subsection**
- **Found during:** Task 2 verification
- **Issue:** Tests asserted `type_win_rate_timeline` findings exist in `compute_findings()` output, but the subsection was removed
- **Fix:** Updated `_TIMELINE_SUBSECTION_IDS` to 3 members, removed `test_type_win_rate_monthly_for_last_3mo`, renamed class `TestTypeTimeline` → `TestTimelineHelpers`
- **Files modified:** `tests/services/test_insights_service_series.py`

## Known Stubs

None. All gauge bands are wired to real `PER_CLASS_GAUGE_ZONES` data from the benchmark.

## Threat Flags

None. No new network endpoints or auth paths introduced.

## Self-Check

All 1167 backend tests pass (`uv run pytest`). All 211 frontend tests pass (`npm test`). `npm run knip` clean. `npm run build` succeeds. `uv run ty check app/ tests/` clean. `uv run ruff check` clean.

## Self-Check: PASSED

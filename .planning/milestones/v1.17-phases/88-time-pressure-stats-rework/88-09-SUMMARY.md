---
phase: 88-time-pressure-stats-rework
plan: 09
subsystem: api
tags: [endgame-analytics, time-pressure, wilson, hypothesis-test, llm-prompt, cohort-cleanup]

requires:
  - phase: 88
    provides: PressureQuintileBullet schema, _build_quintile_bullets, _iterate_clock_rows scaffolding, MIN_GAMES_PER_PRESSURE_BIN constant
  - phase: 85.1
    provides: compute_score_difference_test (unpaired two-sample Wilson) reused for the per-quintile delta
provides:
  - Cohort layer removed end-to-end (repository query, service aggregator, schema field, score_confidence helpers, LLM prompt scaffolding).
  - Same-game opponent-quintile split: _iterate_clock_rows now returns parallel user_quintile_wdl + opp_quintile_wdl built from a single pass over the same filtered game-set.
  - Per-quintile bullet computes delta = user_score_in_Q − opp_score_in_Q via compute_score_difference_test with min(n_user, n_opp) >= MIN_GAMES_PER_PRESSURE_BIN gate (WR-05 wired).
  - PressureQuintileBullet.cohort_score → opp_score (backend Pydantic).
  - WR-06 orphan cleanup: _SKIPPED_SUBSECTIONS, _format_time_pressure_chart_block, _low_time_gap_line, _LOW_TIME_BUCKETS, _LOW_TIME_GAP_DECISIVE all removed from insights_llm.py; clock_diff_timeline + time_pressure_vs_performance section_block entries dropped.
  - 88-CONTEXT.md D-07 entry retiring D-05 (locked).
affects:
  - 88-10 (popover copy "vs cohort" → "vs opponent")
  - 88-11 (frontend PressureQuintileBullet TS type cohort_score → opp_score, mirroring backend)
  - 88-12 (PRESSURE_BIN_SCORE_NEUTRAL_ZONES sanity recalibration against new opp-quintile semantics)

tech-stack:
  added: []
  patterns:
    - "Same-game opp-quintile split: build two independent quintile-bucketed accumulators in a single pass over the user's own filtered games, with user-side bucketed by user clock-pct and opp-side bucketed by opp clock-pct + result inverted. The two splits are independent samples of the same game-set (user and opp clocks fall in different quintiles within the same game), so an unpaired two-sample Wilson test is the correct significance test."
    - "OOM-risk removal pattern: a 'cohort = all other users' query with no apply_game_filters() was replaceable by carrying both sides of the comparison out of the user's own already-filtered rows. No new query, no cache, no precomputed constant — the existing query_clock_stats_rows return shape already carried opp_clock alongside user_clock."

key-files:
  created: []
  modified:
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - app/services/score_confidence.py
    - app/schemas/endgames.py
    - app/services/insights_service.py
    - app/services/insights_llm.py
    - tests/services/test_time_pressure_service.py
    - tests/services/test_score_confidence.py
    - tests/services/test_insights_llm.py
    - tests/test_endgame_service.py
    - .planning/milestones/v1.17-phases/88-time-pressure-stats-rework/88-CONTEXT.md

key-decisions:
  - "D-07 supersedes D-05: drop the mirror-bucket cohort framing in favour of a same-game opp-quintile split. Comparison set is the user's own filtered games; opp side is derived by bucketing the same rows by opponent's clock-pct and inverting the result."
  - "Reuse compute_score_difference_test (unpaired two-sample Wilson) rather than retain compute_score_delta_vs_reference (one-sample-vs-fixed-ref). The two splits are independent samples — user and opp clocks fall in different quintiles within the same game — so the two-sample shape is the right test."
  - "n-gate per bullet is min(n_user_in_Q, n_opp_in_Q) >= MIN_GAMES_PER_PRESSURE_BIN. This subsumes the small-N cohort cell gate flagged in REVIEW.md WR-01 (no separate sparse-cohort gate needed)."
  - "Full WR-06 orphan cleanup: removed not just the two empty-finding helpers but also _SKIPPED_SUBSECTIONS, _format_time_pressure_chart_block, _low_time_gap_line, the section_block entries, the chart_blocks dict slot, and the visible-findings filter clause. The 80+ lines of 'soon-dead' config paths the planner flagged are gone."

patterns-established:
  - "Independent-quintile split: when a per-quintile comparison is needed and both sides of the comparison are derivable from the user's own row stream (e.g. user clock + opp clock + result), build two parallel quintile accumulators in one pass. Avoid a separate cross-user query unless the comparison set is genuinely external."
  - "Cohort retirement: D-NN decisions that retire a previously-locked decision should explicitly mark the retired decision and explain why it failed. The retiring decision should also list what dies with it (helper functions, query helpers, schema field, LLM scaffolding) to make future archaeology trivial."

requirements-completed:
  - POLISH-01

duration: ~50min
completed: 2026-05-17
---

# Phase 88.1 Plan 09: Drop cohort layer, ship opp-quintile split Summary

**Backend gap closure for Phase 88 — replaces the unfiltered global cohort query (REVIEW.md CR-01) with a same-game opponent-quintile split, deletes the four supporting helpers (`query_cohort_clock_rows`, `_compute_cohort_lookup`, `compute_score_delta_vs_reference`, `_wilson_score_test_vs_ref`), renames the schema field `cohort_score` → `opp_score`, wires the previously-unused `MIN_GAMES_PER_PRESSURE_BIN` n-gate via `compute_score_difference_test`, and finishes the WR-06 LLM-prompt orphan cleanup (8+ symbols removed from `insights_llm.py`).**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-05-17T15:20Z (approx; plan execution start)
- **Completed:** 2026-05-17T16:10Z
- **Tasks:** 1 (single TDD task, RED + GREEN commits)
- **Files modified:** 11 (6 backend src, 4 backend tests, 1 planning doc)

## Accomplishments

- **CR-01 closed.** `query_cohort_clock_rows` is removed from `app/repositories/endgame_repository.py`. No cross-user query of any kind runs on `/api/endgames/overview`. The OOM-risk pattern documented in `CLAUDE.md` (Phase 41.1 / FLAWCHESS-3Q) cannot recur on this route.
- **Same-game opp-quintile split shipped.** `_iterate_clock_rows` now builds both `user_quintile_wdl[tc][q]` (user WDL bucketed by user clock-pct) and `opp_quintile_wdl[tc][q]` (opp WDL bucketed by opp clock-pct, result inverted) in a single pass. `_build_quintile_bullets` computes `delta = user_score − opp_score` via `compute_score_difference_test` with an `min(n_user, n_opp) >= MIN_GAMES_PER_PRESSURE_BIN` gate.
- **WR-05 wired.** The previously-unused `MIN_GAMES_PER_PRESSURE_BIN` constant is now the n-gate inside `_build_quintile_bullets`. Subsumes the WR-01 small-N cohort cell concern.
- **WR-06 orphan cleanup complete.** Removed `_SKIPPED_SUBSECTIONS`, `_format_time_pressure_chart_block`, `_low_time_gap_line`, `_LOW_TIME_BUCKETS`, `_LOW_TIME_GAP_DECISIVE`, the `("subsection", "clock_diff_timeline")` + `("chart", "time_pressure_vs_performance")` section_block entries, the `chart_blocks["time_pressure_vs_performance"]` slot, and the `_SKIPPED_SUBSECTIONS` filter clause in `_assemble_user_prompt`. The two upstream empty-finding helpers `_finding_clock_diff_timeline` and `_finding_time_pressure_vs_performance` are also gone from `insights_service.py`.
- **IN-01 closed.** Four dead constants removed from `endgame_service.py`: `MIN_GAMES_FOR_CLOCK_STATS`, `NUM_BUCKETS`, `BUCKET_WIDTH_PCT`, `CLOCK_PRESSURE_TIMELINE_WINDOW`.
- **IN-04 closed (moot).** The cohort docstring vs D-05 contradiction disappears with the deletion.
- **CONTEXT D-07 locked.** Documents the design pivot, retires D-05, lists what dies with it, and notes that the per-(TC, quintile) neutral band stays valid (recalibration sanity-check deferred to Plan 88-12).

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): failing tests for opp-quintile split** — `19f6a0fb` (test)
2. **Task 1 (GREEN): drop cohort layer, ship opp-quintile split** — `9e8eab69` (feat)

The SUMMARY metadata commit follows below.

## Files Created/Modified

- `app/repositories/endgame_repository.py` — deleted `query_cohort_clock_rows` (66 LOC removed); module docstring updated.
- `app/services/endgame_service.py` — rewrote `_iterate_clock_rows` (now returns 4-tuple including `opp_quintile_wdl`); rewrote `_build_quintile_bullets` (new opp-quintile signature, `compute_score_difference_test` for stats, min-n gate wired); simplified `_compute_time_pressure_cards` to single-arg; deleted `_compute_cohort_lookup` (~60 LOC); dropped imports of `query_cohort_clock_rows` and `compute_score_delta_vs_reference`; removed dead constants (IN-01); updated `compose_endgame_overview` to drop the cohort fetch + lookup wiring.
- `app/services/score_confidence.py` — deleted `compute_score_delta_vs_reference` and its private helper `_wilson_score_test_vs_ref` (~70 LOC).
- `app/schemas/endgames.py` — `PressureQuintileBullet.cohort_score` → `opp_score`; docstring rewritten for the new design.
- `app/services/insights_service.py` — removed the two empty-finding helpers `_finding_clock_diff_timeline` and `_finding_time_pressure_vs_performance` from `compose_findings`; deleted the helper definitions.
- `app/services/insights_llm.py` — removed `_SKIPPED_SUBSECTIONS`, `_format_time_pressure_chart_block`, `_low_time_gap_line`, `_LOW_TIME_BUCKETS`, `_LOW_TIME_GAP_DECISIVE`, the `TimePressureChartResponse` import, the `clock_diff_timeline` + `time_pressure_vs_performance` section_block tuples, the `chart_blocks` slot for `time_pressure_vs_performance`, the `_SKIPPED_SUBSECTIONS` filter clause, and the docstring reference to the skip-set.
- `tests/services/test_time_pressure_service.py` — full rewrite for the new design. New test classes: `TestUserAndOppQuintileIndependentSplit`, `TestQuintileBulletDelta`, `TestRepositoryNoCohortFunction`, `TestComputeTimePressureCardsSignature`, `TestSparseQuintile`, `TestMinGamesPerPressureBinWired`. Existing assertions repointed from `cohort_score` to `opp_score` and from the two-arg `_compute_time_pressure_cards(rows, cohort_lookup)` to the new single-arg signature.
- `tests/services/test_score_confidence.py` — deleted `TestComputeScoreDeltaVsReference` (11 boundary tests); dropped `compute_score_delta_vs_reference` + `wilson_bounds` imports.
- `tests/services/test_insights_llm.py` — deleted three tests covering the removed helpers (`test_assemble_user_prompt_skips_time_pressure_vs_performance_subsection_finding`, `test_assemble_user_prompt_renders_time_pressure_chart_block`, `test_assemble_user_prompt_omits_chart_block_when_empty`, `test_low_time_gap_line_emitted_in_time_pressure_chart`). Repointed three remaining tests (`test_all_time_series_trimmed_to_last_36_points`, `test_trend_emitted_on_summary_window_line`, `test_payload_summary_includes_all_time_window`) from the retired `clock_diff_timeline` subsection to `endgame_elo_timeline` (the surviving monthly-for-all_time timeline subsection — equivalent semantics for the bucket-cap behaviour they test).
- `tests/test_endgame_service.py` — removed two `query_cohort_clock_rows` mocks from the overview wiring tests.
- `.planning/milestones/v1.17-phases/88-time-pressure-stats-rework/88-CONTEXT.md` — appended D-07 section retiring D-05.

## Decisions Made

- **Test repointing over deletion (test_insights_llm.py)** — three tests originally used `clock_diff_timeline` as a generic probe for the all_time series 36-bucket cap behaviour. After dropping that subsection from the section_blocks, those tests started failing because the assembler filters out findings not registered in any section. Repointed to `endgame_elo_timeline` (also monthly-for-all_time, also in `_TIMELINE_SUBSECTION_IDS`) rather than deleting. The 36-bucket cap is a generic concern that deserves explicit coverage.
- **Black-side row builder (test_opp_inversion_user_loss_user_color_black)** — the `_make_row` helper assumed white perspective and embedded user_clock at ply 0, opp_clock at ply 1. For the black-user inversion test, hand-built the row tuple directly with the opp-clock at ply 0 and user-clock at ply 1 (matching `_extract_entry_clocks`'s parity logic). Avoided extending the helper signature since this is the only test that needs black perspective.

## Deviations from Plan

None — plan executed exactly as written. The plan was unusually thorough; every grep gate, every test rename, and every orphan-cleanup target listed in `<action>` step 9 was applied as specified.

## Issues Encountered

- **Three `tests/services/test_insights_llm.py` tests failed after removing `clock_diff_timeline` from compose_findings.** Two used `clock_diff_timeline` as a generic monthly-for-all_time timeline probe; one tested the trend-on-summary-line behaviour. All three were repointed to `endgame_elo_timeline` with minimal mechanical changes (subsection_id, metric, dimension). The behaviour-under-test is unchanged because both subsections share the same granularity and the same downstream rendering path.
- **`test_score_confidence.py` lost its `math` and `wilson_bounds` uses** when the `TestComputeScoreDeltaVsReference` class went away. Verified `math` is still used elsewhere (line 143 etc.). Dropped the `wilson_bounds` import (it was only used by the deleted test class).

## User Setup Required

None — backend-only gap closure. Frontend follows in Plan 88-11 (`cohort_score` → `opp_score` TS type rename, "vs cohort" → "vs opponent" popover copy). Frontend would break against this backend until 88-11 lands; that's the expected wave structure documented in 88-ROADMAP.

## Verification

- `uv run ruff check .` → All checks passed.
- `uv run ty check app/ tests/` → All checks passed.
- `uv run pytest -q` → **1528 passed, 6 skipped** in 17.58s.
- All acceptance-criteria grep gates pass (10 / 10):
  - `query_cohort_clock_rows` in `app/repositories/endgame_repository.py`: 0.
  - cohort plumbing (`_compute_cohort_lookup`/`cohort_lookup`/`cohort_rows`/`compute_score_delta_vs_reference`) in `app/services/endgame_service.py`: 0.
  - `compute_score_delta_vs_reference`/`_wilson_score_test_vs_ref` in `app/services/score_confidence.py`: 0.
  - Dead constants (`MIN_GAMES_FOR_CLOCK_STATS`/`NUM_BUCKETS`/`BUCKET_WIDTH_PCT`/`CLOCK_PRESSURE_TIMELINE_WINDOW`) in `app/services/endgame_service.py`: 0.
  - `opp_score` in `app/schemas/endgames.py`: 5 (>= 1 required).
  - `cohort_score` in `app/schemas/endgames.py`: 0.
  - `MIN_GAMES_PER_PRESSURE_BIN` refs in `app/services/endgame_service.py`: 4 (>= 2 required, constant declaration + consumer use + comment).
  - `_finding_clock_diff_timeline`/`_finding_time_pressure_vs_performance` in `app/services/insights_service.py`: 0.
  - Section-block tuples for the removed time-pressure entries in `app/services/insights_llm.py`: 0.
  - WR-06 orphans (`_SKIPPED_SUBSECTIONS`/`_format_time_pressure_chart_block`/`time_pressure_vs_performance`) in `app/services/insights_llm.py`: 0.
- `88-CONTEXT.md` contains `D-07` and `supersedes D-05`.

## Self-Check: PASSED

- `19f6a0fb` (RED test commit) — present in `git log --all`.
- `9e8eab69` (GREEN feat commit) — present in `git log --all`.
- `app/services/endgame_service.py` — modified, present.
- `app/repositories/endgame_repository.py` — modified, present.
- `app/services/score_confidence.py` — modified, present.
- `app/schemas/endgames.py` — modified, present.
- `app/services/insights_service.py` — modified, present.
- `app/services/insights_llm.py` — modified, present.
- `tests/services/test_time_pressure_service.py` — modified, present.
- `tests/services/test_score_confidence.py` — modified, present.
- `tests/services/test_insights_llm.py` — modified, present.
- `tests/test_endgame_service.py` — modified, present.
- `.planning/milestones/v1.17-phases/88-time-pressure-stats-rework/88-CONTEXT.md` — modified, present.

## Next Phase Readiness

Backend gap closure complete. Wave 2 of Phase 88.1 (Plan 88-10) can now update the popover copy ("vs cohort" → "vs opponent") in the frontend. Wave 3 (Plan 88-11) will rename the frontend TS type field `cohort_score` → `opp_score` and unwire the corresponding fixture data. Wave 4 (Plan 88-12) will rerun the benchmark sanity recalibration against the new opp-quintile semantics — D-02's band shape is mathematically unaffected by the swap, but the IQR values should be re-confirmed.

Frontend will be temporarily out-of-sync with backend after this plan merges but before 88-11 lands — same-wave plans are designed to absorb the discontinuity. No production deploy should occur mid-wave.

---

*Phase: 88.1-time-pressure-stats-rework*
*Plan: 09*
*Completed: 2026-05-17*

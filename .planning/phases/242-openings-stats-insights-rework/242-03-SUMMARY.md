---
phase: 242-openings-stats-insights-rework
plan: 03
subsystem: api
tags: [fastapi, openings, time-series, wilson, dev-clock, iso-week]

requires:
  - phase: 242-01
    provides: finalize_opening_eval, score_verdict_fields, repertoire_recency (is_current, resolve_current_cutoffs)
provides:
  - "POST /openings/positions: eval z-test centred on the colour baseline, eval_ci99 bounds on WDLStats"
  - "POST /openings/time-series: one point per active ISO week (Monday key) with per_week_games"
  - "BookmarkTimeSeries score, score_confidence, score_p_value, score_ci99_low/high (D-18) and is_current (D-04)"
  - "NowUtc dev-clock alias and now_utc plumbing on the openings router"
affects: [242-04, 242-06, 242-09, openings-frontend]

requirements-completed: [D-00, D-02, D-03, D-04, D-13, D-17, D-18]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 18c603f2a8927460526b7e77646f0794ca44842e
plan_head_after: e3cc497ac5c12f062ed29a5f90c8616126f5d43a

tech-stack:
  added: []
  patterns:
    - "Weekly bucketing keyed by ISO Monday (same as endgame_service), last in-window point per week wins"
    - "One cutoff query per distinct bookmark colour, sequential awaits, windowed dates"

key-files:
  created:
    - tests/routers/test_openings_time_series_router.py
  modified:
    - app/services/openings_service.py
    - app/schemas/openings.py
    - app/routers/openings.py
    - tests/test_openings_service.py
    - tests/test_openings_time_series.py
    - tests/test_aggregation_sanity.py

key-decisions:
  - "A weekly point is keyed by its ISO Monday, so the first point of a date-windowed series can be dated up to 6 days before from_date; it still contains only in-window games"
  - "Bookmark series with no games (or no colour) read as is_current True"
  - "Only in-window games compute the rolling window and per-week counts; pre-window games only warm results_so_far"

duration: 25min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 03: Weekly bookmark time series and centred Moves/Games eval Summary

**The Moves/Games position stats now test MG-entry eval against the colour baseline with 99% CIs, and `/openings/time-series` returns weekly Monday-keyed points with per-week game counts, server-side score p-value and 99% Wilson CI, and a per-colour `is_current` flag driven by the dev clock.**

## Accomplishments

- `analyze()` uses `finalize_opening_eval(pe, request.color)` and `resolve_eval_baseline_pawns`, copying all eight fields (including the new `eval_ci99_low_pawns` / `eval_ci99_high_pawns`) onto `WDLStats`. The raw mean stays in `avg_eval_pawns`; only p-value and bucket are centred.
- `_build_bookmark_time_series` buckets by ISO week (Monday key via `isocalendar`), keeps the rolling-50 score after the week's last in-window game, counts `per_week_games`, preserves the pre-window warm-up and the 10-game floor, and attaches `score_verdict_fields(...)` plus `is_current(last_played_at, cutoff)`. Nesting extracted into `_iso_week_monday` and `_rolling_score`.
- `get_time_series` takes a required keyword-only `now_utc`, resolves one cutoff per distinct bookmark colour under the request filters (windowed dates), and passes each bookmark its colour's cutoff (None for colour-less bookmarks).
- Router: `NowUtc` alias, `now_utc` parameter, stale "monthly" docstring fixed. `endgame_service.py` has no diff.

## Task Commits

1. **Task 1 (tracer): centred Moves/Games eval with 99% CIs** - `6e1870458` (feat)
2. **Task 2: weekly time series, score fields, is_current, router dev clock** - `e3cc497ac` (feat)

## Verification

- `uv run pytest tests/test_openings_time_series.py tests/test_aggregation_sanity.py tests/routers/test_openings_time_series_router.py tests/test_openings_service.py tests/test_endgame_service.py -x`: 208 passed.
- Full backend suite `uv run pytest -n auto -x`: 5556 passed, 19 skipped.
- `ruff check .`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean.
- Mutation proofs: forcing the eval baseline to 0 cp made `test_eval_is_centred_on_the_colour_baseline` fail; forcing `cutoff = None` in `get_time_series` made `TestIsCurrent` fail. Both restored.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing time-series assertions assumed per-date points**
- **Found during:** Task 2
- **Issue:** `test_score_across_multiple_days` expected one point per day, `test_emitted_points_fall_inside_window` required every point date inside `[from_date, to_date]`, and the warm-up test expected `date == "2026-03-01"`. With Monday keys the first two are wrong by construction (2026-02-01 and 2026-03-01 are Sundays, so their weeks start before the window).
- **Fix:** Rewrote those assertions for weekly semantics (week 1 dropped by the 10-game floor, week overlaps window, Monday `2026-02-23`) and documented the behaviour in the test.
- **Files modified:** `tests/test_openings_time_series.py`
- **Commit:** `e3cc497ac`

---

**Total deviations:** 1 auto-fixed (test expectations updated for the planned weekly granularity). **Impact:** none on production code.

## Issues Encountered

None. The plan-commit ledger file under `.git/worktrees/...` was not written (Bash sandbox refuses git-dir paths); `commits:` is measured with `git rev-list --count 18c603f2a..HEAD` (2).

## Known Stubs

None.

## Threat Flags

None. The time-series and cutoff queries are scoped by the authenticated `user.id`; `now_utc` comes only from `dev_now_utc` (development-only header).

## Next Phase Readiness

Frontend plans (04, 06, 09) can mirror the schema contract: `WDLStats.eval_ci99_*`, `TimeSeriesPoint.per_week_games` (date = ISO Monday), `BookmarkTimeSeries.{score, score_confidence, score_p_value, score_ci99_low, score_ci99_high, is_current}`. The ScoreChart must tolerate a first point dated before `from_date`.

## Self-Check: PASSED

- Created: `tests/routers/test_openings_time_series_router.py` exists.
- Commits `6e1870458` and `e3cc497ac` are ancestors of HEAD.
- Acceptance greps: `isocalendar` and `score_verdict_fields` in `openings_service.py`, `per_week_games` and `eval_ci99_low_pawns` in `schemas/openings.py`, `Depends(dev_now_utc)` in `routers/openings.py` all present.

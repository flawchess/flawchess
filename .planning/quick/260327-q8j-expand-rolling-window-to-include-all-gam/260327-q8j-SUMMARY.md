---
phase: quick-260327-q8j
plan: "01"
subsystem: backend
tags: [bug-fix, analysis, time-series, rolling-window]
dependency_graph:
  requires: []
  provides: [accurate-rolling-window-time-series]
  affects: [statistics-page, win-rate-over-time-chart]
tech_stack:
  added: []
  patterns: [full-history-fetch-then-filter]
key_files:
  modified:
    - app/services/analysis_service.py
decisions:
  - "Pass recency_cutoff=None to query_time_series so rolling window is computed over full history, matching the pattern in get_endgame_timeline and get_conv_recov_timeline"
metrics:
  duration: "5 minutes"
  completed: "2026-03-27"
  tasks_completed: 1
  files_changed: 1
---

# Phase quick-260327-q8j Plan 01: Expand Rolling Window to Include All Games Summary

**One-liner:** Fixed Win Rate Over Time chart to compute rolling window over full game history before filtering data points to the active recency window.

## What Was Built

The `get_time_series` function in `analysis_service.py` was passing the recency cutoff directly to the database query, meaning the rolling window was computed only over the filtered period. This caused the rolling window to ramp up from a small sample at the start of the recency window instead of reflecting the player's actual trailing history.

The fix applies the pattern already used by `get_endgame_timeline` and `get_conv_recov_timeline` in `endgame_service.py`:

1. Fetch all games (pass `recency_cutoff=None` to `query_time_series`)
2. Compute the rolling window over the full history
3. Filter data points to the recency window after the rolling window is computed
4. Recompute win/draw/loss totals from the recency-filtered period only

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix get_time_series to use full-history rolling window with recency filtering | b2b31a0 | app/services/analysis_service.py |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- File modified: `app/services/analysis_service.py` — exists and contains `recency_cutoff=None`
- Commit `b2b31a0` exists in git log
- 451 tests pass, ruff linting clean

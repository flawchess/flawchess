---
phase: quick-260320-d5b
plan: 01
subsystem: statistics-chart
tags: [rolling-window, win-rate, time-series, chart]
dependency_graph:
  requires: []
  provides: [rolling-win-rate-chart]
  affects: [openings-statistics-tab]
tech_stack:
  added: []
  patterns: [rolling-window-computation, aggregate-fields-on-parent]
key_files:
  created: []
  modified:
    - app/schemas/analysis.py
    - app/repositories/analysis_repository.py
    - app/services/analysis_service.py
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/components/charts/WinRateChart.tsx
    - frontend/src/pages/Openings.tsx
decisions:
  - "Rolling window computed in backend service (not frontend) for clean separation of concerns"
  - "Per-game rows returned from repository, window aggregation done in service layer"
  - "Aggregate totals (total_wins/draws/losses/total_games) added to BookmarkTimeSeries to avoid double-counting in wdlStatsMap"
  - "DISTINCT ON Game.id wrapped in subquery so outer query can order by played_at ASC without PostgreSQL constraint"
metrics:
  duration: ~15 minutes
  completed: "2026-03-20"
  tasks_completed: 2
  files_modified: 6
---

# Quick Task 260320-d5b: Smarter Win Rate Over Time Chart with Rolling Windows Summary

**One-liner:** Replaced monthly-bucketed win rate chart with rolling 20-game trailing window using per-game backend pipeline and date-based frontend chart.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Backend — per-game query + rolling window service | d2aae0e |
| 2 | Frontend — update types, chart, and Openings wdlStatsMap | 79ce0e8 |

## What Was Built

### Backend Changes

**`app/schemas/analysis.py`**
- `TimeSeriesPoint` now has `date` (ISO date string), `win_rate`, `game_count` (window games), `window_size` fields — removed per-point `wins`/`draws`/`losses` (not meaningful for rolling windows)
- `BookmarkTimeSeries` gained `total_wins`, `total_draws`, `total_losses`, `total_games` aggregate fields for unambiguous WDL derivation

**`app/repositories/analysis_repository.py`**
- `query_time_series` now returns `(played_at, result, user_color)` tuples per individual game (no DATE_TRUNC grouping)
- Rows ordered by `played_at ASC` via a subquery wrapper (required because PostgreSQL DISTINCT ON must appear first in ORDER BY)
- All existing filter parameters unchanged

**`app/services/analysis_service.py`**
- Added `ROLLING_WINDOW_SIZE = 20` constant
- `get_time_series` now builds a running results list, computes `window[-ROLLING_WINDOW_SIZE:]` at each game, emits one `TimeSeriesPoint` per game
- Partial windows (games 1-19) included from the start — no minimum threshold
- Accumulates `total_wins/draws/losses/total_games` for aggregate fields

### Frontend Changes

**`frontend/src/types/position_bookmarks.ts`**
- `TimeSeriesPoint` updated: `date` replaces `month`, added `window_size`, removed `wins`/`draws`/`losses`
- `BookmarkTimeSeries` updated: added `total_wins`/`total_draws`/`total_losses`/`total_games`

**`frontend/src/components/charts/WinRateChart.tsx`**
- Removed `MIN_GAMES` constant and `formatMonth` helper
- Added `formatDate` helper (formats "2025-01-15" as "Jan '25")
- Empty state now checks `data.length > 0` (no game threshold)
- Chart data built from unique `date` values across all series
- Tooltip shows "X/20 games" window fullness indicator
- XAxis uses `dataKey="date"` with `tickFormatter={formatDate}`

**`frontend/src/pages/Openings.tsx`**
- `wdlStatsMap` rewritten to use `s.total_wins`/`s.total_draws`/`s.total_losses`/`s.total_games` directly instead of summing rolling sub-counts (which would double-count)

## Deviations from Plan

None — plan executed exactly as written.

The DISTINCT ON subquery pattern in the repository was an implementation detail to satisfy PostgreSQL's requirement that DISTINCT ON expressions appear first in ORDER BY — this is a standard constraint and required no architectural decision.

## Self-Check

### Files exist:
- [x] app/schemas/analysis.py — modified
- [x] app/repositories/analysis_repository.py — modified
- [x] app/services/analysis_service.py — modified
- [x] frontend/src/types/position_bookmarks.ts — modified
- [x] frontend/src/components/charts/WinRateChart.tsx — modified
- [x] frontend/src/pages/Openings.tsx — modified

### Commits exist:
- [x] d2aae0e — backend task
- [x] 79ce0e8 — frontend task

### Verification:
- [x] `uv run python -c "from app.schemas.analysis import TimeSeriesPoint, BookmarkTimeSeries"` — passes
- [x] `npx tsc --noEmit` — passes (no errors)

## Self-Check: PASSED

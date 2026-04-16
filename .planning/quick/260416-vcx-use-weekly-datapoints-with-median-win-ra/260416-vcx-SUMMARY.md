---
quick_id: 260416-vcx
status: complete
date: 2026-04-16
description: Weekly datapoints for per-type "Win Rate by Endgame Type" chart
---

# Quick Task 260416-vcx: Weekly datapoints for per-type chart

## Outcome

Replaced the per-type rolling-window series in the "Win Rate by Endgame Type"
chart with weekly buckets (average win rate per ISO week, Monday-dated). The
overall endgame-vs-non-endgame series is unchanged — it still uses rolling
windows.

## Implementation

- `_compute_weekly_series(rows, min_games)` added alongside `_compute_rolling_series`.
  Groups games by `played_at.isocalendar()` → emits one point per ISO week on
  the Monday date, win_rate = wins / games in that week. Weeks with fewer than
  `MIN_GAMES_PER_WEEK = 3` games are dropped.
- `EndgameTimelinePoint` schema dropped `window_size` (backend Pydantic and
  frontend TS). `EndgameOverallPoint` keeps it (overall series still rolling).
- `get_endgame_timeline` per-type loop now calls `_compute_weekly_series` and
  constructs `EndgameTimelinePoint` without `window_size`.
- `EndgameTimelineChart` stopped forwarding the `_window_size` field into merged
  chart rows. Tooltip suffix changed from `(past N games)` to
  `(N games this week)`. InfoPopover copy updated to the weekly semantics with
  the 3-games-per-week threshold.
- `TestComputeWeeklySeries` added in `tests/test_endgame_service.py` with 4
  unit tests (empty input, min-games threshold, multi-week Monday dating,
  weighted average). Existing `test_per_type_keys_are_endgame_class_strings`
  fixture widened to 3 same-week games so it still emits a weekly point.

## Commits

- `10f2f0e` refactor(endgames): switch per-type timeline to weekly buckets
- `db324f1` test(endgames): add weekly-series unit tests; update per-type fixture
- `b208b31` refactor(frontend): switch per-type endgame timeline to weekly copy

## Verification

- `uv run ruff check .` — clean
- `uv run ty check app/ tests/` — zero errors
- `uv run pytest` — 767 passed, 1 skipped
- `cd frontend && npm run lint` — clean
- `cd frontend && npm run build` — builds successfully

## Not Performed

- Overall endgame-vs-non-endgame series unchanged on purpose (locked scope).
- No DB migration (pure compute change).
- STATE.md / ROADMAP.md updates deferred to orchestrator commit.

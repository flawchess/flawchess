---
id: 260416-w3q
type: quick
title: Clock-diff timeline chart in Time Pressure at Endgame Entry
status: complete
date: 2026-04-16
---

# Quick Task 260416-w3q — Summary

## Outcome

Added a weekly rolling-window timeline chart below the "Time Pressure at Endgame
Entry" table. Single line collapsed across time controls, ±30% Y-axis centered
on 0, dots colored per zone (green / blue / red) using the existing
NEUTRAL_PCT_THRESHOLD (10%). Uses a 100-game rolling window sampled once per
ISO week, mirroring the pattern in the "Win Rate by Endgame Type" chart.

## Changes

### Backend
- `app/repositories/endgame_repository.py` — appended `Game.played_at` to
  `query_clock_stats_rows` (row index 8). Existing consumers ignore the trailing
  column; the new timeline consumer reads it.
- `app/schemas/endgames.py` — new `ClockPressureTimelinePoint`; extended
  `ClockPressureResponse` with `timeline` + `timeline_window`.
- `app/services/endgame_service.py` — `CLOCK_PRESSURE_TIMELINE_WINDOW = 100`;
  new `_compute_clock_pressure_timeline` (weekly sampling, trailing-window
  mean, MIN_GAMES_FOR_TIMELINE filter); `_compute_clock_pressure` now returns
  the timeline in the response.
- `tests/test_endgame_service.py` — added `TestComputeClockPressureTimeline`
  with 5 tests covering empty input, MIN_GAMES filter, weekly cadence + rolling
  mean, window capping, invalid-row skipping, and end-to-end exposure via
  `_compute_clock_pressure`. Updated `_make_clock_row` helper to accept
  `played_at`.

### Frontend
- `frontend/src/types/endgames.ts` — added `ClockPressureTimelinePoint`;
  extended `ClockPressureResponse` with `timeline` + `timeline_window`.
- `frontend/src/components/charts/EndgameClockPressureSection.tsx` — added
  inline `ClockDiffTimelineChart` rendered below the coverage note. Uses the
  same Recharts `LineChart` + axis-label layout as
  `EndgameTimePressureSection` (vertical Y-axis label on desktop, centered
  X-axis label below the chart). Axis is fixed at [-30, 30] with ticks every
  10. Dots are colored by zone; the line itself stays muted-foreground so the
  dots carry the signal. `ReferenceLine y={0}` for the zero axis. Tooltip
  shows the full week date, signed diff%, and window size.

## Verification

- `uv run ruff check app/ tests/` — pass
- `uv run ty check app/ tests/` — pass
- `uv run pytest tests/` — 775 passed
- `cd frontend && npm run lint` — pass
- `cd frontend && npm test -- --run` — 73 passed
- `cd frontend && npm run build` — pass
- `cd frontend && npm run knip` — clean

## Commits

- `a55ddae` — feat(endgames): add clock-diff timeline payload (backend)
- `6729143` — feat(endgames): add clock-diff timeline chart (frontend)

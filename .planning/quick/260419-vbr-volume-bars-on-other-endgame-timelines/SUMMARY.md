---
quick_id: 260419-vbr
slug: volume-bars-on-other-endgame-timelines
status: complete
date: 2026-04-19
---

# Summary — Volume bars on three more endgame timelines

Replicated the muted weekly volume bars + "Games this week: N" tooltip indicator
from the Phase 57.1 Endgame ELO Timeline onto the three other endgame timeline charts.

## Changes

**Backend** (`app/`)

- `schemas/endgames.py`: added `per_week_game_count` to `EndgameTimelinePoint` and
  `ClockPressureTimelinePoint`; added `per_week_total_games` to `ScoreGapTimelinePoint`.
- `services/endgame_service.py`: extended `_compute_score_gap_timeline`,
  `_compute_clock_pressure_timeline`, and `_compute_weekly_rolling_series` to
  accumulate per-ISO-week event counts and emit them on each timeline point.
  `get_endgame_timeline` propagates the new field into per-type
  `EndgameTimelinePoint` construction.

**Frontend** (`frontend/src/`)

- `types/endgames.ts`: mirrored the new fields on the three timeline-point types.
- `components/charts/EndgamePerformanceSection.tsx` (Score % Difference over Time):
  swapped `LineChart` → `ComposedChart`, added hidden right Y-axis with
  `domain=[0, barMax * 5]`, attached `yAxisId="value"` to the existing axis +
  `<ReferenceArea>` + `<ReferenceLine>` + `<Line>`, added muted `<Bar>` keyed by
  `per_week_total_games`, prepended "Games this week: N" to the tooltip.
- `components/charts/EndgameClockPressureSection.tsx` (Average Clock Difference
  over Time): same pattern, bar keyed by `per_week_game_count`.
- `components/charts/EndgameTimelineChart.tsx` (Win Rate by Endgame Type):
  same pattern but multi-series — sums `per_week_game_count` across currently-visible
  endgame types into `per_week_total_visible` (recomputed on legend toggle, mirroring
  `barChartData` in `EndgameEloTimelineSection`).

## Verification

- `uv run ruff check app/ tests/` — all checks passed
- `uv run ty check app/ tests/` — all checks passed
- `uv run pytest tests/test_endgame_service.py tests/test_integration_routers.py` — 218 passed
- `cd frontend && npm run lint` — 0 errors
- `cd frontend && npm run build` — succeeded
- `cd frontend && npm test -- --run` — 83 passed

## Files modified

- `app/schemas/endgames.py`
- `app/services/endgame_service.py`
- `frontend/src/types/endgames.ts`
- `frontend/src/components/charts/EndgamePerformanceSection.tsx`
- `frontend/src/components/charts/EndgameClockPressureSection.tsx`
- `frontend/src/components/charts/EndgameTimelineChart.tsx`

## Notes

- New testids added: `score-diff-volume-bars`, `clock-diff-volume-bars`,
  `timeline-per-type-volume-bars` (per `Browser Automation Rules` in CLAUDE.md).
- Per-week counts are exact ISO-week aggregates of the underlying game stream,
  not rolling-window totals — so the bars represent activity *that specific week*,
  consistent with the Endgame ELO Timeline's reading.
- Did not commit — on `main`, per project convention `/gsd-quick` doesn't commit
  unless asked.

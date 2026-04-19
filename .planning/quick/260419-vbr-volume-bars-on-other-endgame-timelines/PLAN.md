---
quick_id: 260419-vbr
slug: volume-bars-on-other-endgame-timelines
status: in-progress
date: 2026-04-19
---

# Volume bars on three more endgame timelines

Add the muted grey weekly volume bars (with "Games this week: N" tooltip indicator) — already present in the **Endgame ELO Timeline** (Phase 57.1) — to:

1. **Score % Difference over Time** (`EndgamePerformanceSection.tsx` → `ScoreDiffTimelineChart`)
2. **Average Clock Difference over Time** (`EndgameClockPressureSection.tsx` → `ClockDiffTimelineChart`)
3. **Win Rate by Endgame Type** (`EndgameTimelineChart.tsx` per-type chart)

## Pattern (from Phase 57.1)

- `LineChart` → `ComposedChart`
- Existing `YAxis` gains `yAxisId="value"` (or similar)
- Hidden right `YAxis yAxisId="bars" orientation="right" hide domain={[0, barMax * 5]}` pins tallest bar to bottom 20%
- Existing `<Line>`, `<ReferenceArea>`, `<ReferenceLine>` get matching `yAxisId="value"`
- New `<Bar yAxisId="bars" dataKey="..." fill={ENDGAME_VOLUME_BAR_COLOR} legendType="none" isAnimationActive={false}/>`
- Tooltip prepends `Games this week: N` line

## Backend changes

Three timeline points need a per-week count field (separate from rolling-window counts):

- `EndgameTimelinePoint`: add `per_week_game_count: int`
- `ScoreGapTimelinePoint`: add `per_week_total_games: int` (endgame + non-endgame in this ISO week)
- `ClockPressureTimelinePoint`: add `per_week_game_count: int`

Service compute functions accumulate per-ISO-week counts and assign on emission, mirroring `_compute_endgame_elo_weekly_series`.

## Frontend

- Mirror types in `frontend/src/types/endgames.ts`
- For the per-type Win Rate chart (multi-series), sum `per_week_game_count` across currently-visible types per row, like `barChartData` in `EndgameEloTimelineSection`.

## Files to touch

- `app/schemas/endgames.py`
- `app/services/endgame_service.py`
- `frontend/src/types/endgames.ts`
- `frontend/src/components/charts/EndgamePerformanceSection.tsx`
- `frontend/src/components/charts/EndgameClockPressureSection.tsx`
- `frontend/src/components/charts/EndgameTimelineChart.tsx`

## Verification

- `uv run ruff check app/`
- `uv run ty check app/ tests/`
- `uv run pytest tests/test_endgame_service.py`
- `cd frontend && npm run lint && npm run build`

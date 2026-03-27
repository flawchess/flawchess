# Quick Task 260327-gyz: Add Conversion/Recovery Timeline Chart

## What Changed

Added a new "Conversion & Recovery Over Time" timeline chart to the Endgame Statistics page showing two rolling-window trend lines:
- **Conversion** (green): win rate over the last 50 games where the user entered endgame with material advantage (>=300cp)
- **Recovery** (amber): save rate (wins + draws) over the last 50 games where the user entered endgame with material disadvantage (<=-300cp)

## Files Modified

### Backend (4 files)
- `app/schemas/endgames.py` — Added `ConvRecovTimelinePoint` and `ConvRecovTimelineResponse` Pydantic models
- `app/repositories/endgame_repository.py` — Added `query_conv_recov_timeline_rows()` query function (reuses span/entry_ply pattern, filters abs(imbalance) >= 300cp in SQL)
- `app/services/endgame_service.py` — Added `_compute_conv_recov_rolling_series()` helper and `get_conv_recov_timeline()` orchestrator
- `app/routers/endgames.py` — Added `GET /api/endgames/conv-recov-timeline` endpoint with standard filters + window param

### Frontend (5 files)
- `frontend/src/types/endgames.ts` — Added `ConvRecovTimelinePoint` and `ConvRecovTimelineResponse` interfaces
- `frontend/src/api/client.ts` — Added `getConvRecovTimeline()` API method
- `frontend/src/hooks/useEndgames.ts` — Added `useEndgameConvRecovTimeline()` TanStack Query hook
- `frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx` — New Recharts LineChart component with legend toggling, tooltips, and date formatting
- `frontend/src/pages/Endgames.tsx` — Wired new chart after existing timeline chart
- `frontend/src/lib/theme.ts` — Added `CHART_CONVERSION` and `CHART_RECOVERY` color constants

## Key Design Decisions
- Only shows data points once the rolling window is full (no partial windows)
- SQL-level filtering of abs(material_imbalance) >= 300cp for efficiency
- Separate endpoint from existing timeline (different data shape and query logic)

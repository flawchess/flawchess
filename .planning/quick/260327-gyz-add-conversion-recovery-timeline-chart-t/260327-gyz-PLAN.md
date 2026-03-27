---
phase: quick-260327-gyz
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/endgames.py
  - app/repositories/endgame_repository.py
  - app/services/endgame_service.py
  - app/routers/endgames.py
  - frontend/src/types/endgames.ts
  - frontend/src/api/client.ts
  - frontend/src/hooks/useEndgames.ts
  - frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx
  - frontend/src/pages/Endgames.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Conversion rate rolling timeline shows win rate over last N games where user entered endgame with >=300cp advantage"
    - "Recovery rate rolling timeline shows save rate (win+draw) over last N games where user entered endgame with <=-300cp deficit"
    - "Both lines respond to all existing endgame sidebar filters"
  artifacts:
    - path: "app/schemas/endgames.py"
      provides: "ConvRecovTimelinePoint and ConvRecovTimelineResponse schemas"
    - path: "app/repositories/endgame_repository.py"
      provides: "query_conv_recov_timeline_rows function"
    - path: "app/services/endgame_service.py"
      provides: "get_conv_recov_timeline service function"
    - path: "app/routers/endgames.py"
      provides: "GET /api/endgames/conv-recov-timeline endpoint"
    - path: "frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx"
      provides: "Two-line Recharts LineChart for conversion and recovery over time"
  key_links:
    - from: "frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx"
      to: "/api/endgames/conv-recov-timeline"
      via: "useEndgameConvRecovTimeline hook"
    - from: "app/routers/endgames.py"
      to: "app/services/endgame_service.py"
      via: "get_conv_recov_timeline call"
    - from: "app/services/endgame_service.py"
      to: "app/repositories/endgame_repository.py"
      via: "query_conv_recov_timeline_rows call"
---

<objective>
Add a conversion/recovery timeline chart to endgame statistics — two rolling-window lines showing how conversion rate (winning when up material) and recovery rate (saving when down material) trend over time.

Purpose: Users can track whether their endgame technique is improving or declining over their game history.
Output: New backend endpoint + frontend chart rendered after the existing EndgameTimelineChart.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/repositories/endgame_repository.py
@app/services/endgame_service.py
@app/schemas/endgames.py
@app/routers/endgames.py
@frontend/src/types/endgames.ts
@frontend/src/api/client.ts
@frontend/src/hooks/useEndgames.ts
@frontend/src/components/charts/EndgameTimelineChart.tsx
@frontend/src/pages/Endgames.tsx
@frontend/src/lib/theme.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — repository, service, schema, router for conv/recov timeline</name>
  <files>app/schemas/endgames.py, app/repositories/endgame_repository.py, app/services/endgame_service.py, app/routers/endgames.py</files>
  <action>
**Schema** (`app/schemas/endgames.py`): Add two new models:
- `ConvRecovTimelinePoint(BaseModel)`: `date: str`, `rate: float` (0.0-1.0 fraction), `game_count: int` (games in rolling window), `window_size: int`.
- `ConvRecovTimelineResponse(BaseModel)`: `conversion: list[ConvRecovTimelinePoint]`, `recovery: list[ConvRecovTimelinePoint]`, `window: int`.

**Repository** (`app/repositories/endgame_repository.py`): Add `query_conv_recov_timeline_rows()` with same signature as `query_endgame_entry_rows` (session, user_id, time_control, platform, rated, opponent_type, recency_cutoff).
- Use same span_subq + entry_pos_subq pattern as `query_endgame_entry_rows`.
- SELECT `Game.played_at`, `Game.result`, `Game.user_color`, and `user_material_imbalance` (same color_sign CASE expression).
- Filter: only rows where `abs(user_material_imbalance) >= 300` — but since user_material_imbalance is computed in SQL (entry_pos_subq.c.material_imbalance * color_sign), you cannot filter on it directly in WHERE. Instead, return ALL rows (like query_endgame_entry_rows does) and let the service filter by imbalance threshold. Actually — to keep it efficient, add WHERE clause on raw material_imbalance: `func.abs(entry_pos_subq.c.material_imbalance) >= 300` (this works because abs is the same regardless of sign flip).
- ORDER BY `Game.played_at.asc()`.
- Filter out rows where `Game.played_at IS NULL`.
- Returns: `list[tuple]` of `(played_at, result, user_color, user_material_imbalance)`.

**Service** (`app/services/endgame_service.py`): Add `get_conv_recov_timeline()` with params: session, user_id, time_control, platform, recency, rated, opponent_type, window=50.
- Call `query_conv_recov_timeline_rows` to get rows.
- Split into two lists: `conversion_rows` where `user_material_imbalance >= 300` and `recovery_rows` where `user_material_imbalance <= -300`.
- For conversion_rows, compute rolling series: for each game in chronological order, track trailing `window` games. Rate = wins / total in window.
- For recovery_rows, compute rolling series: Rate = (wins + draws) / total in window.
- Use a helper similar to `_compute_rolling_series` but adapted: `_compute_conv_recov_rolling_series(rows, window, rate_fn)` where rate_fn takes a list of outcomes and returns the rate. For conversion: `lambda outcomes: outcomes.count("win") / len(outcomes)`. For recovery: `lambda outcomes: (outcomes.count("win") + outcomes.count("draw")) / len(outcomes)`.
- Return `ConvRecovTimelineResponse`.

Import `_MATERIAL_ADVANTAGE_THRESHOLD` (already 300) from the module scope — reuse it instead of hardcoding 300. Import `query_conv_recov_timeline_rows` from the repository. Import `ConvRecovTimelinePoint, ConvRecovTimelineResponse` from schemas.

**Router** (`app/routers/endgames.py`): Add `GET /endgames/conv-recov-timeline` endpoint. Same filter params as `/endgames/timeline` (time_control, platform, recency, rated, opponent_type, window). Response model: `ConvRecovTimelineResponse`. Import the new schema and add to the router imports. Call `endgame_service.get_conv_recov_timeline`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run python -c "from app.schemas.endgames import ConvRecovTimelinePoint, ConvRecovTimelineResponse; print('Schema OK')" && uv run python -c "from app.repositories.endgame_repository import query_conv_recov_timeline_rows; print('Repo OK')" && uv run python -c "from app.services.endgame_service import get_conv_recov_timeline; print('Service OK')" && uv run python -c "from app.routers.endgames import router; routes = [r.path for r in router.routes]; assert '/endgames/conv-recov-timeline' in routes, f'Route not found in {routes}'; print('Router OK')"</automated>
  </verify>
  <done>New endpoint GET /api/endgames/conv-recov-timeline returns ConvRecovTimelineResponse with conversion and recovery rolling series. All imports resolve, route is registered.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend — types, API client, hook, chart component, page wiring</name>
  <files>frontend/src/types/endgames.ts, frontend/src/api/client.ts, frontend/src/hooks/useEndgames.ts, frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx, frontend/src/pages/Endgames.tsx</files>
  <action>
**Types** (`frontend/src/types/endgames.ts`): Add interfaces mirroring backend:
- `ConvRecovTimelinePoint { date: string; rate: number; game_count: number; window_size: number; }`
- `ConvRecovTimelineResponse { conversion: ConvRecovTimelinePoint[]; recovery: ConvRecovTimelinePoint[]; window: number; }`

**API client** (`frontend/src/api/client.ts`):
- Import `ConvRecovTimelineResponse` from types.
- Add `getConvRecovTimeline` to `endgameApi` object. Same param shape as `getTimeline` (time_control, platform, recency, rated, opponent_type, window). URL: `/endgames/conv-recov-timeline`. Same param spreading pattern as existing methods.

**Hook** (`frontend/src/hooks/useEndgames.ts`):
- Add `useEndgameConvRecovTimeline(filters: FilterState, window = 50)`. Same pattern as `useEndgameTimeline` — uses `buildEndgameParams`, queryKey `['endgameConvRecovTimeline', params, window]`, calls `endgameApi.getConvRecovTimeline`.

**Chart** (`frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx`): Create new component following `EndgameTimelineChart` pattern.
- Props: `{ data: ConvRecovTimelineResponse }`.
- Import `GAUGE_SUCCESS` and `GAUGE_WARNING` from `@/lib/theme` for conversion (green) and recovery (amber) line colors.
- Merge conversion and recovery series into a single data array keyed by date. For each unique date, include `conversion_rate`, `recovery_rate`, `conversion_game_count`, `recovery_game_count`, etc. (same merging pattern as EndgameTimelineChart per-type data).
- Use same Recharts `LineChart` pattern: `ChartContainer`, `CartesianGrid`, `XAxis`, `YAxis` (domain [0, 1], formatted as percentage), two `Line` components.
- Legend with toggle (same `hiddenKeys` + `handleLegendClick` pattern).
- Tooltip showing date, rate as percentage, game count / window size for each visible line.
- Title: "Conversion & Recovery Over Time" with `InfoPopover`:
  - "**Conversion rate**: your win rate in the last {window} games where you entered the endgame with a significant material advantage (>=3 pawns). **Recovery rate**: your save rate (wins + draws) in the last {window} games where you entered the endgame at a significant material disadvantage (>=3 pawns down)."
- Chart config: `{ conversion: { label: 'Conversion', color: GAUGE_SUCCESS }, recovery: { label: 'Recovery', color: GAUGE_WARNING } }`.
- Add `data-testid="conv-recov-timeline-chart"` on the ChartContainer.
- Empty state: if both series are empty, return null (don't render anything).
- Reuse the same `formatDate` and `formatDateWithYear` helpers (copy from EndgameTimelineChart or extract — copying is simpler for this scope).

**Page** (`frontend/src/pages/Endgames.tsx`):
- Import `EndgameConvRecovTimelineChart` from `@/components/charts/EndgameConvRecovTimelineChart`.
- Import `useEndgameConvRecovTimeline` from `@/hooks/useEndgames`.
- Call `useEndgameConvRecovTimeline(debouncedFilters)` alongside existing hooks (same pattern as `useEndgameTimeline`).
- Render the chart AFTER the existing `EndgameTimelineChart` in `statisticsContent`, with same conditional: `{convRecovData && (convRecovData.conversion.length > 0 || convRecovData.recovery.length > 0) && (<EndgameConvRecovTimelineChart data={convRecovData} />)}`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit && npm run build</automated>
  </verify>
  <done>New EndgameConvRecovTimelineChart renders two lines (conversion green, recovery amber) in the Statistics tab after the Win Rate by Endgame Type chart. TypeScript compiles with no errors, build succeeds.</done>
</task>

</tasks>

<verification>
- Backend: `uv run ruff check .` passes (no lint errors)
- Backend: `uv run pytest -x` passes (no regressions)
- Frontend: `npm run build` succeeds
- Frontend: `npm run lint` passes
- Manual: visit /endgames/statistics page, scroll below Win Rate by Endgame Type chart, see Conversion & Recovery Over Time chart with two lines
</verification>

<success_criteria>
- GET /api/endgames/conv-recov-timeline returns two rolling-window series (conversion win rate, recovery save rate) respecting all sidebar filters
- Chart displays two colored lines with legend toggle, tooltip, and info popover
- Both series use 300cp material advantage threshold consistent with existing conversion/recovery stats
- No TypeScript or Python lint errors
</success_criteria>

<output>
After completion, create `.planning/quick/260327-gyz-add-conversion-recovery-timeline-chart-t/260327-gyz-SUMMARY.md`
</output>

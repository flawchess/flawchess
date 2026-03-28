# Phase 32: Endgame Performance Charts - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

New charts on the existing Endgames Statistics sub-tab comparing endgame vs non-endgame performance, two semicircle gauge charts (relative endgame strength and endgame skill composite), a grouped bar chart for conversion/recovery by type, and rolling-window timeline charts showing win rate trends over time. Two new backend endpoints provide the data. No changes to existing charts or endpoints.

</domain>

<decisions>
## Implementation Decisions

### Page Layout & Section Order
- **D-01:** All new charts go on the existing Statistics sub-tab (no new sub-tabs or pages).
- **D-02:** Section order top-to-bottom: "Endgame Performance" (WDL comparison + gauges) -> "Results by Endgame Type" (existing, unchanged) -> "Conversion & Recovery by Endgame Type" (new grouped bar chart) -> Timeline charts (overall + per-type).

### Endgame vs Non-Endgame WDL Comparison
- **D-03:** Two side-by-side horizontal stacked WDL bars (same visual style as existing EndgameWDLChart rows) — one labeled "Endgame games" and one "Non-endgame games".

### Strength Gauge Charts
- **D-04:** Two semicircle/radial gauge charts side by side.
- **D-05:** Left gauge: "Relative Endgame Strength" = `endgame_win_rate / overall_win_rate * 100`. 100% = endgame performance on par with overall. Below 100% = weaker in endgames.
- **D-06:** Right gauge: "Endgame Skill" = weighted composite of conversion and recovery: `0.6 * conversion_pct + 0.4 * recovery_pct`. Shown as 0-100%.
- **D-07:** Conversion and recovery percentages are aggregated across all endgame types for the gauge (not per-type).

### Conversion & Recovery Bar Chart
- **D-08:** Grouped vertical bar chart "Conversion & Recovery by Endgame Type". For each endgame type, two bars side by side: Conversion % and Recovery %. Uses existing data from the stats endpoint — no new backend work needed.
- **D-09:** Placed below the existing "Results by Endgame Type" section. The existing chart is NOT modified.

### Timeline Charts
- **D-10:** Date-based X-axis (calendar dates, not game index). Points plotted at game dates.
- **D-11:** Two separate charts stacked vertically:
  1. "Win Rate Over Time" — two lines: endgame games win rate and non-endgame games win rate (rolling 50-game window each).
  2. "Win Rate by Endgame Type" — multi-line chart with one colored line per endgame type (rolling 50-game window per type).
- **D-12:** Rolling window uses available games when fewer than 50 exist for a given type. The line starts from game 1.
- **D-13:** Both timeline charts use Recharts LineChart with ChartContainer/ChartTooltip/ChartLegend (existing pattern).

### Backend Endpoints
- **D-14:** Two new endpoints:
  - `GET /api/endgames/performance` — returns endgame WDL, non-endgame WDL, overall win rate, endgame win rate, aggregate conversion_pct, aggregate recovery_pct, relative_strength, endgame_skill.
  - `GET /api/endgames/timeline?window=50` — returns rolling win rate time series: `overall` array (endgame + non-endgame lines) and `per_type` dict keyed by endgame class.
- **D-15:** Rolling-window aggregation computed on the backend (not frontend). Database does the windowing.
- **D-16:** Both endpoints respect all existing filters (time control, platform, recency, rated, opponent type).

### Claude's Discretion
- Semicircle gauge implementation (Recharts radial chart, custom SVG, or a gauge library)
- Gauge color scheme and scale ranges (e.g., red/yellow/green zones)
- Exact colors for the per-type timeline lines
- Empty state design for users with no endgame data
- Mobile layout adaptation for the gauge charts and timeline charts
- How to handle the "non-endgame" line in the timeline when a user has very few non-endgame games
- SQL windowing strategy for rolling aggregation (window functions vs application-level)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing endgame implementation
- `.planning/phases/29-endgame-analytics/29-CONTEXT.md` — Original endgame analytics decisions (D-01 through D-16), filter design, category display patterns
- `.planning/phases/31-endgame-classification-redesign/31-CONTEXT.md` — Per-position endgame classification, multi-class-per-game counting, 6-ply threshold

### Existing chart patterns
- `frontend/src/components/charts/WinRateChart.tsx` — Recharts LineChart with ChartContainer, date formatting, multi-line pattern
- `frontend/src/components/charts/EndgameWDLChart.tsx` — Custom WDL bars with glass overlay, conversion/recovery sub-bars
- `frontend/src/components/charts/WDLBarChart.tsx` — Recharts BarChart pattern
- `frontend/src/components/stats/GlobalStatsCharts.tsx` — Recharts grouped BarChart pattern
- `frontend/src/components/ui/chart.tsx` — ChartContainer, ChartTooltip, ChartLegend wrappers

### Backend endgame service
- `app/services/endgame_service.py` — `_aggregate_endgame_stats()` function, conversion/recovery calculation logic
- `app/repositories/endgame_repository.py` — Endgame query patterns, user_material_imbalance normalization
- `app/schemas/endgames.py` — Pydantic response schemas

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChartContainer` + `ChartTooltip` + `ChartLegend` from shadcn chart.tsx — standard wrapper for all Recharts charts
- `WDL_WIN`, `WDL_DRAW`, `WDL_LOSS` color constants from `WDLBar.tsx` — reuse for WDL comparison bars
- `GLASS_OVERLAY` gradient from `EndgameWDLChart.tsx` — reuse for visual consistency on new WDL bars
- Existing `endgameApi.getStats()` — already returns conversion/recovery data per type, reusable for the grouped bar chart (D-08)
- `WinRateChart.tsx` — existing Recharts LineChart pattern with date formatting and multi-line support

### Established Patterns
- Recharts for all chart visualizations (LineChart, BarChart) wrapped in shadcn ChartContainer
- Custom HTML/CSS bars (not Recharts) for WDL bars in EndgameWDLChart — glass overlay style
- Filter state managed via URL params + TanStack Query hooks
- Backend: repository -> service -> router layering with Pydantic schemas

### Integration Points
- New sections insert into the existing Endgames Statistics sub-tab component
- New endpoints register in `app/routers/endgames.py`
- New service functions in `app/services/endgame_service.py`
- New repository queries in `app/repositories/endgame_repository.py`
- Frontend hooks for new endpoints alongside existing `useEndgameStats`

</code_context>

<specifics>
## Specific Ideas

- The overall timeline chart should have TWO lines — endgame win rate and non-endgame win rate — so the user can visually track how the gap between them evolves over time
- The strength gauge concept emerged from observing that weaker players tend to perform worse in endgames relative to their overall play, while stronger players have more balanced performance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-endgame-performance-charts*
*Context gathered: 2026-03-26*

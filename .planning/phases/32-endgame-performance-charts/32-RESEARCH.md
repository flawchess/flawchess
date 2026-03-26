# Phase 32: Endgame Performance Charts - Research

**Researched:** 2026-03-26
**Domain:** Recharts gauge/radial charts, rolling window timeline, PostgreSQL endgame queries, FastAPI endpoint extension
**Confidence:** HIGH

## Summary

Phase 32 adds five new visual sections to the existing Endgames Statistics sub-tab: an endgame vs non-endgame WDL comparison, two semicircle gauge charts (relative strength + skill composite), a grouped bar chart for conversion/recovery by type, and two timeline charts showing rolling 50-game win rate over time. Two new GET endpoints feed this data; the existing stats endpoint already supplies enough data for the grouped bar chart.

The project already has a mature rolling-window time series pattern (in `analysis_service.py`/`analysis_repository.py`) that computes the window in Python over chronologically-ordered rows from a simple SQL query. The endgame timeline should use the same application-level windowing strategy rather than SQL window functions — it is simpler, consistent with the existing codebase, and fast enough for the data volumes involved.

Recharts 2.15.4 (installed) supports `RadialBarChart` + `PolarAngleAxis` + `PolarRadiusAxis`, which is the canonical Recharts approach for semicircle gauges. The `ChartContainer` wrapper in `chart.tsx` already includes CSS selectors for radial bar components, so no additional setup is needed. A simpler and more controllable alternative is a custom SVG arc, which avoids Recharts quirks with radial charts and gives pixel-perfect control over gauge zones.

**Primary recommendation:** Use custom SVG arcs for the semicircle gauges (full control, zero new dependencies, works cleanly with dark mode via CSS variables). Use the existing application-level rolling-window pattern for timeline data (matches established codebase style, avoids SQL window function complexity).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** All new charts go on the existing Statistics sub-tab (no new sub-tabs or pages).
- **D-02:** Section order top-to-bottom: "Endgame Performance" (WDL comparison + gauges) -> "Results by Endgame Type" (existing, unchanged) -> "Conversion & Recovery by Endgame Type" (new grouped bar chart) -> Timeline charts (overall + per-type).
- **D-03:** Two side-by-side horizontal stacked WDL bars (same visual style as existing EndgameWDLChart rows) — one labeled "Endgame games" and one "Non-endgame games".
- **D-04:** Two semicircle/radial gauge charts side by side.
- **D-05:** Left gauge: "Relative Endgame Strength" = `endgame_win_rate / overall_win_rate * 100`. 100% = endgame performance on par with overall. Below 100% = weaker in endgames.
- **D-06:** Right gauge: "Endgame Skill" = weighted composite of conversion and recovery: `0.6 * conversion_pct + 0.4 * recovery_pct`. Shown as 0-100%.
- **D-07:** Conversion and recovery percentages are aggregated across all endgame types for the gauge (not per-type).
- **D-08:** Grouped vertical bar chart "Conversion & Recovery by Endgame Type". For each endgame type, two bars side by side: Conversion % and Recovery %. Uses existing data from the stats endpoint — no new backend work needed.
- **D-09:** Placed below the existing "Results by Endgame Type" section. The existing chart is NOT modified.
- **D-10:** Date-based X-axis (calendar dates, not game index). Points plotted at game dates.
- **D-11:** Two separate charts stacked vertically:
  1. "Win Rate Over Time" — two lines: endgame games win rate and non-endgame games win rate (rolling 50-game window each).
  2. "Win Rate by Endgame Type" — multi-line chart with one colored line per endgame type (rolling 50-game window per type).
- **D-12:** Rolling window uses available games when fewer than 50 exist for a given type. The line starts from game 1.
- **D-13:** Both timeline charts use Recharts LineChart with ChartContainer/ChartTooltip/ChartLegend (existing pattern).
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 2.15.4 | LineChart, BarChart, RadialBarChart, PolarAngleAxis | Installed; all existing charts use it |
| React 19 + TypeScript | 19.2 / 5.9.3 | Component implementation | Project standard |
| TanStack Query v5 | 5.90.x | Data fetching hooks | Project standard for all API calls |
| SQLAlchemy 2.x async | 2.x | New repository queries | Project ORM standard |
| Pydantic v2 | 2.x | New response schemas | Project validation standard |
| FastAPI 0.115.x | 0.115.x | New route definitions | Project HTTP framework |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ChartContainer / ChartTooltip / ChartLegend | shadcn chart.tsx | Wrapper for all Recharts charts | All Recharts usage goes through this |
| WDL_WIN / WDL_DRAW / WDL_LOSS | WDLBar.tsx constants | Color constants for WDL bars | Reuse for endgame vs non-endgame WDL comparison |
| GLASS_OVERLAY | EndgameWDLChart.tsx | Visual consistency | Reuse for new WDL comparison bars |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom SVG gauge | Recharts RadialBarChart | Recharts gauge: more complex API, harder to size, known gotchas with `startAngle`/`endAngle`. Custom SVG: full control, no dependency, simpler dark-mode. **Recommendation: custom SVG.** |
| Custom SVG gauge | react-gauge-component or similar library | Would add a new dependency not in the project. Avoid. |
| Application-level rolling window | SQL window functions (ROW_NUMBER + SUM OVER) | SQL: complex, harder to test, hard to parameterize window size dynamically. App-level: matches existing `analysis_service.py` pattern exactly. **Recommendation: application-level.** |

**Installation:** No new packages needed. All required libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure

New files to create:
```
app/
├── repositories/endgame_repository.py      # ADD: query_endgame_performance_rows, query_endgame_timeline_rows
├── services/endgame_service.py             # ADD: get_endgame_performance, get_endgame_timeline
├── schemas/endgames.py                     # ADD: EndgamePerformanceResponse, EndgameTimelineResponse, etc.
└── routers/endgames.py                     # ADD: /endgames/performance, /endgames/timeline

frontend/src/
├── api/client.ts                           # ADD: endgameApi.getPerformance, endgameApi.getTimeline
├── types/endgames.ts                       # ADD: EndgamePerformanceResponse, EndgameTimelineResponse types
├── hooks/useEndgames.ts                    # ADD: useEndgamePerformance, useEndgameTimeline
└── components/charts/
    ├── EndgamePerformanceSection.tsx        # NEW: WDL comparison rows + gauge charts
    ├── EndgameConvRecovChart.tsx            # NEW: grouped bar chart (D-08)
    ├── EndgameTimelineChart.tsx             # NEW: two stacked timeline charts (D-11)
    └── EndgameGauge.tsx                    # NEW: reusable SVG semicircle gauge
```

### Pattern 1: Endgame vs Non-Endgame WDL Comparison Bars

**What:** Two horizontal stacked WDL bars with the same CSS/glass-overlay style as existing `EndgameWDLChart` rows. Data comes from the new `/api/endgames/performance` endpoint.

**When to use:** Display section at top of new "Endgame Performance" section.

```tsx
// Source: EndgameWDLChart.tsx — same CSS pattern reused
const GLASS_OVERLAY =
  'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

// Two rows: endgame and non-endgame
// Each row: label | WDL bar (glass) | W%/D%/L% text
function WDLComparisonRow({ label, win_pct, draw_pct, loss_pct, total }: ...) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-xs text-muted-foreground">{total} games</span>
      </div>
      <div className="flex h-5 w-full overflow-hidden rounded">
        <div style={{ width: `${win_pct}%`, backgroundColor: WDL_WIN, backgroundImage: GLASS_OVERLAY }} />
        <div style={{ width: `${draw_pct}%`, backgroundColor: WDL_DRAW, backgroundImage: GLASS_OVERLAY }} />
        <div style={{ width: `${loss_pct}%`, backgroundColor: WDL_LOSS, backgroundImage: GLASS_OVERLAY }} />
      </div>
      <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
        <span style={{ color: WDL_WIN }}>W: {win_pct.toFixed(0)}%</span>
        <span style={{ color: WDL_DRAW }}>D: {draw_pct.toFixed(0)}%</span>
        <span style={{ color: WDL_LOSS }}>L: {loss_pct.toFixed(0)}%</span>
      </div>
    </div>
  );
}
```

### Pattern 2: Custom SVG Semicircle Gauge

**What:** A pure SVG arc gauge. The semicircle spans 180 degrees (left to right), filled as a colored arc proportional to the value. Three colored zones (red/yellow/green) provide intuitive context.

**When to use:** Relative Endgame Strength (D-05) and Endgame Skill (D-06) gauges.

```tsx
// Source: Custom SVG pattern — no Recharts needed
// cx=100, cy=100, r=80 — half circle from 180° to 0° (left to right)
const GAUGE_STROKE_WIDTH = 18;
const R = 72;
const CX = 100;
const CY = 96;  // slightly above center so bottom label fits
const CIRCUMFERENCE = Math.PI * R;  // half circle arc length

function EndgameGauge({ value, maxValue, label, sublabel }: EndgameGaugeProps) {
  const pct = Math.min(value / maxValue, 1);
  // SVG arc: strokeDasharray trick for a half-circle progress arc
  const dashOffset = CIRCUMFERENCE * (1 - pct);

  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-48">
      {/* Background arc (grey) */}
      <path
        d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
        fill="none"
        stroke="oklch(0.85 0 0)"
        strokeWidth={GAUGE_STROKE_WIDTH}
        strokeLinecap="round"
      />
      {/* Foreground arc (colored by zone) */}
      <path
        d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
        fill="none"
        stroke={getGaugeColor(pct)}
        strokeWidth={GAUGE_STROKE_WIDTH}
        strokeLinecap="round"
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={dashOffset}
        // CSS transform rotates the dash fill from left to right
        style={{ transformOrigin: `${CX}px ${CY}px`, transform: 'scaleX(-1)' }}
      />
      {/* Center value text */}
      <text x={CX} y={CY - 8} textAnchor="middle" className="fill-foreground text-lg font-bold">
        {value.toFixed(0)}%
      </text>
      <text x={CX} y={CY + 10} textAnchor="middle" className="fill-muted-foreground text-xs">
        {sublabel}
      </text>
    </svg>
  );
}

function getGaugeColor(pct: number): string {
  if (pct >= 0.9) return 'oklch(0.55 0.17 145)';  // green
  if (pct >= 0.7) return 'oklch(0.65 0.18 80)';   // amber
  return 'oklch(0.55 0.20 25)';                    // red
}
```

**Note on Relative Endgame Strength gauge (D-05):** The formula is `endgame_win_rate / overall_win_rate * 100`. This can exceed 100% if the user is stronger in endgames. The gauge arc should cap visually at 100% on the right, but the numeric label shows the true value (e.g. "112%"). The backend should return both `relative_strength` (raw ratio, uncapped) and the clamped display values are computed in the frontend.

### Pattern 3: Conversion & Recovery Grouped Bar Chart (D-08)

**What:** Recharts `BarChart` with grouped bars (no `stackId`). For each endgame type on the X-axis, two bars side by side: Conversion % and Recovery %. Data is derived from the existing `EndgameStatsResponse.categories` — no new endpoint needed.

**When to use:** "Conversion & Recovery by Endgame Type" section (D-09, after existing chart).

```tsx
// Source: GlobalStatsCharts.tsx — reuse ChartContainer + BarChart pattern
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';

const chartConfig = {
  conversion_pct: { label: 'Conversion', color: 'oklch(0.55 0.17 145)' },  // green
  recovery_pct:   { label: 'Recovery',   color: 'oklch(0.55 0.18 260)' },  // blue
};

// data: categories.map(c => ({ label: c.label, conversion_pct: c.conversion.conversion_pct, recovery_pct: c.conversion.recovery_pct }))
<ChartContainer config={chartConfig} className="w-full h-64">
  <BarChart data={data} layout="horizontal" margin={{ left: 8, right: 16, bottom: 32 }}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="label" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
    <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
    <ChartTooltip content={...} />
    <ChartLegend content={<ChartLegendContent />} />
    <Bar dataKey="conversion_pct" fill="var(--color-conversion_pct)" radius={[2,2,0,0]} />
    <Bar dataKey="recovery_pct"   fill="var(--color-recovery_pct)"   radius={[2,2,0,0]} />
  </BarChart>
</ChartContainer>
```

### Pattern 4: Timeline Charts (D-11, D-13)

**What:** Two stacked `LineChart` components matching the existing `WinRateChart.tsx` pattern. The first has two lines (endgame vs non-endgame win rate); the second has up to 6 lines (one per endgame type).

**When to use:** Timeline section at bottom of Statistics tab.

```tsx
// Source: WinRateChart.tsx — exact same pattern, different data shape
<ChartContainer config={chartConfig} className="w-full h-72">
  <LineChart data={data}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="date" tickFormatter={formatDate} />
    <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
    <ChartTooltip content={...} />
    <ChartLegend content={<ChartLegendContent hiddenKeys={hiddenKeys} onClickItem={handleLegendClick} />} />
    {lines.map(key => (
      <Line key={key} type="monotone" dataKey={key} stroke={`var(--color-${key})`}
            strokeWidth={2} dot={false} connectNulls hide={hiddenKeys.has(key)} />
    ))}
  </LineChart>
</ChartContainer>
```

**Data shape from backend (D-14 timeline endpoint):**
```typescript
interface EndgameTimelineResponse {
  overall: TimeSeriesPoint[];   // [{date, endgame_win_rate, non_endgame_win_rate, endgame_game_count, non_endgame_game_count, window_size}]
  per_type: Record<EndgameClass, TimeSeriesPoint[]>;  // keyed by class, each has {date, win_rate, game_count, window_size}
}
```

### Pattern 5: Backend Rolling Window (Application-Level)

**What:** Fetch chronologically ordered per-game rows from the DB, then compute rolling window in Python. This is the exact same pattern as `analysis_service.py:get_time_series()`.

**How for endgame timeline:**

1. **Non-endgame games:** fetch all games that did NOT reach an endgame class span >= `ENDGAME_PLY_THRESHOLD`. Use a NOT IN subquery on game_ids from the existing endgame span subquery.
2. **Endgame games (overall):** fetch all games that DID reach any endgame class span >= threshold.
3. **Per-type:** for each of the 6 endgame classes, fetch game_ids that spent >= threshold plies in that class.

**Rolling window computation (Python — same as `analysis_service.py`):**
```python
ROLLING_WINDOW = 50  # from the window query param, default 50

results_so_far: list[str] = []
data: list[TimeSeriesPoint] = []
for played_at, result, user_color in rows_ordered_by_date_asc:
    outcome = derive_user_result(result, user_color)
    results_so_far.append(outcome)
    window = results_so_far[-ROLLING_WINDOW:]
    win_rate = window.count("win") / len(window)
    data.append(TimeSeriesPoint(date=played_at.strftime("%Y-%m-%d"), win_rate=round(win_rate, 4), ...))
```

**Note on D-15 ("Database does the windowing"):** The CONTEXT.md says the backend computes the rolling window, NOT the frontend. This is consistent with the codebase. D-15 states "Rolling-window aggregation computed on the backend" — the decision is about backend vs frontend, not SQL vs Python. Application-level Python in the service layer is the correct implementation that honors this decision while matching the established codebase pattern.

### Pattern 6: New Backend Endpoint Schemas

**`GET /api/endgames/performance` response schema:**
```python
class EndgameWDLSummary(BaseModel):
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float

class EndgamePerformanceResponse(BaseModel):
    endgame_wdl: EndgameWDLSummary        # games that reached endgame
    non_endgame_wdl: EndgameWDLSummary    # games that did NOT reach endgame
    overall_win_rate: float               # wins / total across ALL games
    endgame_win_rate: float               # wins / total for endgame games only
    aggregate_conversion_pct: float       # weighted avg conversion across all types
    aggregate_recovery_pct: float         # weighted avg recovery across all types
    relative_strength: float             # endgame_win_rate / overall_win_rate * 100 (can exceed 100)
    endgame_skill: float                  # 0.6 * conversion_pct + 0.4 * recovery_pct (0-100)
```

**`GET /api/endgames/timeline?window=50` response schema:**
```python
class EndgameTimelinePoint(BaseModel):
    date: str          # "YYYY-MM-DD"
    win_rate: float    # rolling window win rate
    game_count: int    # games in the current window
    window_size: int   # configured window size

class EndgameOverallPoint(BaseModel):
    date: str
    endgame_win_rate: float | None      # None if no endgame game on this date
    non_endgame_win_rate: float | None  # None if no non-endgame game on this date
    endgame_game_count: int
    non_endgame_game_count: int
    window_size: int

class EndgameTimelineResponse(BaseModel):
    overall: list[EndgameOverallPoint]
    per_type: dict[EndgameClass, list[EndgameTimelinePoint]]
    window: int
```

### Anti-Patterns to Avoid

- **Don't use SQL window functions for rolling windows:** The existing codebase does this in Python in the service layer. Using SQL OVER clauses would be inconsistent and harder to test.
- **Don't add new dependencies for the gauge:** No `react-gauge-chart`, `react-gauge-component`, or similar libraries. Custom SVG is 20 lines and fully controllable.
- **Don't modify EndgameWDLChart.tsx for the WDL comparison bars:** D-09 says the existing chart is NOT modified. Build a separate component.
- **Don't expose Relative Endgame Strength as a percentage capped at 100% on the backend:** Return the raw ratio and let the frontend decide how to display/cap it visually.
- **Don't forget empty states:** Users with no endgame data (new users, heavy filter restricting to zero games) must get a graceful empty state, not a crash or blank div.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart wrapper boilerplate | Custom chart container | `ChartContainer` from `chart.tsx` | Handles CSS variables, ResponsiveContainer |
| Line chart with legend | Custom SVG line chart | Recharts LineChart | Already used in WinRateChart.tsx |
| Grouped bar chart | Custom SVG bars | Recharts BarChart (no stackId) | Already used in GlobalStatsCharts.tsx |
| Date formatting | Custom date utilities | Reuse `formatDate` / `formatDateWithYear` from WinRateChart.tsx | Already tested, handles ISO date strings |
| WDL color constants | New hex colors | `WDL_WIN`, `WDL_DRAW`, `WDL_LOSS` from `WDLBar.tsx` | Ensures visual consistency across all WDL displays |
| Filter parameter extraction | Custom hook params | Reuse `buildEndgameParams` from `useEndgames.ts` | No color param on endgame endpoints |
| Recency conversion | Custom datetime logic | `recency_cutoff()` from `analysis_service.py` | Already handles all recency strings |
| Result derivation | Custom win/loss logic | `derive_user_result()` from `analysis_service.py` | Color-aware, handles all result strings |
| Filter application | Duplicate WHERE clauses | `_apply_game_filters()` from `endgame_repository.py` | Consistent filter behavior across all endgame endpoints |

---

## Common Pitfalls

### Pitfall 1: Division by Zero in Gauge Calculations

**What goes wrong:** `endgame_win_rate / overall_win_rate * 100` crashes if overall_win_rate is 0 (user has no wins). `endgame_skill` crashes if both conversion and recovery data are absent.

**Why it happens:** New users or heavily filtered datasets can produce zero denominators.

**How to avoid:** Guard all gauge formula calculations:
```python
relative_strength = (endgame_win_rate / overall_win_rate * 100) if overall_win_rate > 0 else 0.0
endgame_skill = (0.6 * conversion_pct + 0.4 * recovery_pct) if (conversion_games + recovery_games) > 0 else 0.0
```

**Warning signs:** Any test with a fresh user or fully filtered dataset fails with ZeroDivisionError.

### Pitfall 2: Timeline Date Collision

**What goes wrong:** When a user plays both endgame and non-endgame games on the same date, the "overall" chart needs to handle two separate rolling series meeting on the same date. The Recharts LineChart expects a single data array where each row has a `date` key — if endgame and non-endgame points have different dates, gaps appear. If they share dates but the series arrays are separate, the frontend must merge them by date (like `WinRateChart.tsx` does with its `allDates` merge).

**Why it happens:** The two lines (endgame vs non-endgame) are computed from different game sets and will naturally have different dates.

**How to avoid:** Use the same date-merge pattern as `WinRateChart.tsx`: collect all unique dates across both series, sort them, then build a data array where each row has entries for both lines (with `undefined` for dates where one series has no point). `connectNulls={true}` on each `Line` component bridges the gaps.

**Warning signs:** One line stops at a certain point while the other continues.

### Pitfall 3: Per-Type Timeline With High Line Count

**What goes wrong:** The "Win Rate by Endgame Type" chart has up to 6 lines. On mobile, the legend wraps badly. With dense data, 6 overlapping lines are hard to read.

**Why it happens:** 6 endgame classes + a legend that wraps.

**How to avoid:** Use `ChartLegend` with click-to-hide (same pattern as `WinRateChart.tsx` `hiddenKeys` + `handleLegendClick`). On mobile, the chart is full-width — the legend items must be short enough to not overflow. Use the abbreviated labels or consider hiding the chart title on small screens if necessary.

**Warning signs:** Legend text overflows on mobile screens; too many lines make the chart unreadable.

### Pitfall 4: Relative Strength > 100%

**What goes wrong:** The SVG gauge arc overflows its track if the value exceeds 100%.

**Why it happens:** `endgame_win_rate / overall_win_rate * 100` can yield values like 112% for strong endgame players.

**How to avoid:** In the frontend gauge component, clamp the arc fill to [0%, 100%]:
```tsx
const pct = Math.min(value / maxValue, 1);  // maxValue = 100 for both gauges
```
Display the true numeric value (e.g. "112%") as text inside the gauge. Visually the arc is capped, but the label reflects the true score.

**Warning signs:** Gauge arc continues past the rightmost endpoint of the semicircle track.

### Pitfall 5: Non-Endgame Game Count Undercount

**What goes wrong:** A game that reached an endgame for 7 plies then transitioned to a different class also counts as an endgame game. Counting "non-endgame games" as those with ZERO spans meeting the threshold is correct, but joining the existing endgame span subquery (which uses `HAVING count >= ENDGAME_PLY_THRESHOLD`) needs the same threshold applied consistently.

**Why it happens:** The endgame span subquery in `endgame_repository.py` already filters by `ENDGAME_PLY_THRESHOLD`. The "non-endgame" query must use the same constant.

**How to avoid:** Reuse `ENDGAME_PLY_THRESHOLD` constant from `endgame_repository.py` when building the NOT IN subquery for non-endgame games.

**Warning signs:** Non-endgame game count differs from `total_games - endgame_unique_game_count`.

### Pitfall 6: endgame_games Is Not Unique Game Count

**What goes wrong:** `EndgameStatsResponse.endgame_games` is a count of `(game, class)` combinations, not unique games (intentional per D-02 from Phase 31). This means it can exceed `total_games`. The new "Endgame Performance" section needs the UNIQUE game count (games that reached any endgame class at all).

**Why it happens:** Phase 31 decided `endgame_games` counts multi-class combinations. This is correct for the existing per-type stats but wrong for a binary "reached endgame / didn't reach endgame" split.

**How to avoid:** The new `/api/endgames/performance` endpoint must compute distinct endgame game count with `COUNT(DISTINCT game_id)` across all endgame classes, not sum the per-class totals.

**Warning signs:** `endgame_wdl.total + non_endgame_wdl.total` does not equal `total_games`.

### Pitfall 7: Aggregate Conversion/Recovery Calculation

**What goes wrong:** Computing "aggregate conversion_pct" as a simple mean of per-type percentages gives incorrect results. A type with 5 conversion games and 100% rate shouldn't equal a type with 200 games and 50% rate.

**Why it happens:** Types with small sample sizes have inflated variance.

**How to avoid:** Aggregate by summing raw numerators and denominators across all types:
```python
total_conv_wins = sum(c.conversion.conversion_wins for c in categories)
total_conv_games = sum(c.conversion.conversion_games for c in categories)
aggregate_conversion_pct = (total_conv_wins / total_conv_games * 100) if total_conv_games > 0 else 0.0
# Same for recovery
```

---

## Code Examples

### Endgame Non-Endgame Split Query (Repository)

```python
# Source: endgame_repository.py — extend with this pattern
# Returns game_ids that reached ANY endgame class meeting the threshold

endgame_game_ids_subq = (
    select(GamePosition.game_id)
    .where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    .group_by(GamePosition.game_id)
    .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
    .subquery("endgame_ids")
)

# Endgame games: games IN the subquery
endgame_stmt = select(Game.played_at, Game.result, Game.user_color).where(
    Game.user_id == user_id,
    Game.id.in_(select(endgame_game_ids_subq.c.game_id)),
    Game.played_at.isnot(None),
).order_by(Game.played_at.asc())

# Non-endgame games: games NOT IN the subquery
non_endgame_stmt = select(Game.played_at, Game.result, Game.user_color).where(
    Game.user_id == user_id,
    Game.id.notin_(select(endgame_game_ids_subq.c.game_id)),
    Game.played_at.isnot(None),
).order_by(Game.played_at.asc())

# Apply _apply_game_filters to both
```

### Per-Type Timeline Query (Repository)

```python
# Source: endgame_repository.py — extend existing span_subq pattern
# For a single endgame class, returns game_ids + (played_at, result, user_color)

def _build_class_timeline_subq(user_id: int, class_int: int):
    return (
        select(GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class == class_int,
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery(f"span_class_{class_int}")
    )
```

### Rolling Window in Service (Application-Level)

```python
# Source: analysis_service.py — exact same pattern
ROLLING_WINDOW_DEFAULT = 50

def _compute_rolling_series(
    rows: list[tuple],  # (played_at, result, user_color)
    window: int = ROLLING_WINDOW_DEFAULT,
) -> list[dict]:
    results_so_far: list[str] = []
    data = []
    for played_at, result, user_color in rows:
        outcome = derive_user_result(result, user_color)
        results_so_far.append(outcome)
        w = results_so_far[-window:]
        win_rate = w.count("win") / len(w) if w else 0.0
        data.append({
            "date": played_at.strftime("%Y-%m-%d"),
            "win_rate": round(win_rate, 4),
            "game_count": len(w),
            "window_size": window,
        })
    return data
```

### SVG Semicircle Gauge (Frontend)

```tsx
// Custom SVG — no Recharts needed
// Half-circle arc: left anchor = (CX-R, CY), right anchor = (CX+R, CY)
// strokeDashoffset technique fills from left (0%) to right (100%)

const GAUGE_R = 72;
const GAUGE_CX = 100;
const GAUGE_CY = 90;
const ARC_LENGTH = Math.PI * GAUGE_R;  // semicircle circumference

function EndgameGauge({ value, maxValue = 100, label }: { value: number; maxValue?: number; label: string }) {
  const pct = Math.max(0, Math.min(value / maxValue, 1));
  const dashOffset = ARC_LENGTH * (1 - pct);
  const arcColor = pct >= 0.9 ? 'oklch(0.55 0.17 145)' : pct >= 0.7 ? 'oklch(0.65 0.18 80)' : 'oklch(0.55 0.20 25)';
  const arcPath = `M ${GAUGE_CX - GAUGE_R} ${GAUGE_CY} A ${GAUGE_R} ${GAUGE_R} 0 0 1 ${GAUGE_CX + GAUGE_R} ${GAUGE_CY}`;

  return (
    <div data-testid={`gauge-${label.toLowerCase().replace(/\s+/g, '-')}`} className="flex flex-col items-center">
      <svg viewBox="0 0 200 110" className="w-full max-w-[200px]">
        {/* Track */}
        <path d={arcPath} fill="none" stroke="oklch(0.85 0 0 / 0.4)" strokeWidth={16} strokeLinecap="round" />
        {/* Fill */}
        <path d={arcPath} fill="none" stroke={arcColor} strokeWidth={16} strokeLinecap="round"
          strokeDasharray={ARC_LENGTH} strokeDashoffset={dashOffset}
          style={{ transformOrigin: `${GAUGE_CX}px ${GAUGE_CY}px`, transform: 'scaleX(-1)' }} />
        {/* Value label */}
        <text x={GAUGE_CX} y={GAUGE_CY - 6} textAnchor="middle" fontSize="20" fontWeight="600"
          className="fill-foreground">{value.toFixed(0)}%</text>
      </svg>
      <p className="text-xs text-muted-foreground text-center mt-1">{label}</p>
    </div>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-game endgame classification | Per-position endgame classification (Phase 31) | 2026-03-26 | endgame_class column on game_positions; multi-class per game now possible |
| Material-weight threshold for endgame detection | Lichess piece_count <= 6 threshold (Phase 31) | 2026-03-26 | piece_count column; richer class of positions classified as endgame |
| Application-level rolling window (existing pattern) | Same — D-15 says "backend does it" but doesn't mandate SQL | All existing phases | No change needed; Python in service layer is the correct interpretation |

---

## Open Questions

1. **Absolute endgame unique game count vs EndgameStatsResponse.endgame_games**
   - What we know: `endgame_games` in current response counts (game, class) pairs, not unique games.
   - What's unclear: The `/api/endgames/performance` endpoint needs unique endgame game count for WDL split. Should this be added to the existing stats endpoint or computed fresh in the new endpoint?
   - Recommendation: Compute it fresh in the new `performance` endpoint using `COUNT(DISTINCT game_id)`. No change to existing endpoint.

2. **Relative Endgame Strength when overall_win_rate is very low**
   - What we know: A user with 5% overall win rate and 15% endgame win rate gets relative_strength = 300%, which is visually uninformative.
   - What's unclear: Should the gauge have a hard cap (e.g., max display = 150%) or show raw value?
   - Recommendation: Cap the gauge arc at 100% visually but show the raw value as text. Add an InfoPopover explaining "values above 100% mean you perform better in endgames than average."

3. **Timeline endpoint latency with 6 serial DB queries**
   - What we know: The per-type timeline requires 6 separate queries (one per endgame class) plus 2 for overall (endgame + non-endgame). The existing `get_time_series` runs bookmarks sequentially.
   - What's unclear: Whether 8 serial async DB queries will be noticeable for users with large game sets.
   - Recommendation: Use `asyncio.gather()` to run all 8 queries concurrently. Each query is simple (indexed lookup + filter); concurrent execution should keep latency low.

---

## Environment Availability

Step 2.6: SKIPPED — Phase is purely code/config changes. No external tools, services, or CLI utilities beyond the existing project stack are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (backend), `vitest.config.ts` (frontend) |
| Quick run command | `uv run pytest tests/test_endgame_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-1 | `get_endgame_performance` returns correct endgame/non-endgame WDL split | unit | `uv run pytest tests/test_endgame_service.py::TestGetEndgamePerformance -x` | ❌ Wave 0 |
| SC-2 | Gauge values: relative_strength and endgame_skill computed correctly | unit | `uv run pytest tests/test_endgame_service.py::TestEndgameGaugeCalculations -x` | ❌ Wave 0 |
| SC-3 | `get_endgame_timeline` returns rolling window per-type series | unit | `uv run pytest tests/test_endgame_service.py::TestGetEndgameTimeline -x` | ❌ Wave 0 |
| SC-5 | All new endpoints respect filters (time_control, platform, recency, rated, opponent) | integration | `uv run pytest tests/test_endgame_repository.py -x` | ✅ (extend) |
| D-06 | `endgame_skill = 0.6 * conversion_pct + 0.4 * recovery_pct` | unit | `uv run pytest tests/test_endgame_service.py::TestEndgameSkillFormula -x` | ❌ Wave 0 |
| D-07 | Aggregate conversion/recovery uses sum of raw numerators/denominators, not mean of percentages | unit | `uv run pytest tests/test_endgame_service.py::TestAggregateConvRecov -x` | ❌ Wave 0 |
| D-12 | Rolling window uses available games when fewer than 50 exist | unit | `uv run pytest tests/test_endgame_service.py::TestRollingWindowPartial -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_endgame_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_endgame_service.py` — extend with `TestGetEndgamePerformance`, `TestEndgameGaugeCalculations`, `TestGetEndgameTimeline`, `TestEndgameSkillFormula`, `TestAggregateConvRecov`, `TestRollingWindowPartial`

None — existing test infrastructure (pytest, conftest.py, test DB) covers all needs. Only new test methods required in existing file.

---

## Sources

### Primary (HIGH confidence)

- Source code: `app/services/endgame_service.py` — rolling window pattern, aggregate stats, derive_user_result
- Source code: `app/repositories/endgame_repository.py` — span subquery pattern, `ENDGAME_PLY_THRESHOLD`, `_apply_game_filters`
- Source code: `app/services/analysis_service.py` — `get_time_series()` and `_compute_rolling_series()` pattern (lines 190-265)
- Source code: `app/repositories/analysis_repository.py` — `query_time_series()` implementation (lines 80-130)
- Source code: `frontend/src/components/charts/WinRateChart.tsx` — LineChart pattern with date merge, legend click-to-hide
- Source code: `frontend/src/components/charts/EndgameWDLChart.tsx` — glass WDL bar pattern, `GLASS_OVERLAY`, `WDL_WIN/DRAW/LOSS`
- Source code: `frontend/src/components/ui/chart.tsx` — `ChartContainer`, `ChartLegend`, `ChartTooltip`, radial bar CSS selectors
- Source code: `frontend/package.json` — recharts 2.15.4 confirmed installed

### Secondary (MEDIUM confidence)

- Recharts 2.x docs: `RadialBarChart` + `PolarAngleAxis` supports semicircle gauges via `startAngle`/`endAngle`. Custom SVG arc is simpler and recommended over Recharts for this use case. (Verified: ChartContainer already has radial bar CSS selectors, confirming existing version supports it.)

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries directly inspected in package.json and source code
- Architecture: HIGH — patterns directly cloned from existing codebase; no third-party unknowns
- Pitfalls: HIGH — identified from direct code analysis (division by zero, unique vs combination counts, etc.)
- Backend query patterns: HIGH — existing endgame_repository.py and analysis_repository.py provide exact templates

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable stack; recharts/React versions unlikely to change)

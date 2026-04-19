# Phase 57: Endgame ELO — Timeline Chart - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 9 (8 to create/modify + 1 test file)
**Analogs found:** 9 / 9

Every new or modified file has a clean analog in-repo. Phase 57 is almost entirely composition of existing patterns (the one truly novel piece is the 4-line Elo formula itself). Executor should copy from the referenced analog rather than invent.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/endgame_service.py` | service (extend) | transform / request-response | self (`_compute_score_gap_timeline` at lines 540-615) | exact |
| `app/schemas/endgames.py` | schema (extend) | Pydantic response model | self (`ClockPressureResponse`/`ClockPressureTimelinePoint` at lines 260-293; `EndgameOverviewResponse` at 332-346) | exact |
| `app/repositories/endgame_repository.py` | repository (extend) | DB query → Row list | self (`query_endgame_performance_rows` at lines 449-520) + `query_rating_history` (stats_repository.py:46-97) | role+flow match |
| `frontend/src/components/charts/EndgameEloTimelineSection.tsx` (NEW) | component | request-response (renders prefetched data) | `EndgameTimelineChart.tsx` (entire file, 179 lines) + `RatingChart.tsx` (axis logic, 54-106) | exact |
| `frontend/src/lib/theme.ts` | config (extend) | constants | self (existing palette entries like `WDL_WIN`, `MY_SCORE_COLOR`, `FIXED_GAUGE_ZONES` via EndgameScoreGapSection) | exact |
| `frontend/src/lib/utils.ts` | utility (extend) | pure function | self (`niceWinRateAxis` lines 60-75) + `RatingChart.tsx` lines 54-106 (logic to lift) | exact |
| `frontend/src/types/endgames.ts` | types (extend) | TS mirror of Pydantic | self (`ClockPressureTimelinePoint`/`ClockPressureResponse` at lines 136-148; `EndgameOverviewResponse` at 163-170) | exact |
| `frontend/src/pages/Endgames.tsx` | page (extend) | wires new section into existing `statisticsContent` | self (lines 276-321, existing `EndgameScoreGapSection`/`EndgameTimelineChart` wiring) | exact |
| `tests/test_endgame_service.py` | test (extend) | unit tests for service helpers | self (`TestComputeScoreGapTimeline` at lines 2559-2680) | exact |

**No new hooks/routers needed:** Phase 57 piggybacks on `/api/endgames/overview` (extends `EndgameOverviewResponse`), so `useEndgameOverview` (`frontend/src/hooks/useEndgames.ts`) and `app/routers/endgames.py` are untouched.

---

## Pattern Assignments

### `app/services/endgame_service.py` (service — extend)

**Analog:** self. The closest function to clone is `_compute_score_gap_timeline` (lines 540-615), not `_compute_weekly_rolling_series` (1290-1337). Reason: Phase 57 walks *two independent row streams* (endgame games + all games) with two trailing windows, which is exactly what the score-gap helper does.

**Constant pattern** (clone from lines 165-167):
```python
# Rolling window size for the score-difference timeline chart (quick-260417-o2l).
# Mirrors the 100-game window used by the clock-diff timeline.
SCORE_GAP_TIMELINE_WINDOW = 100
```

For Phase 57, add just below:
```python
# Rolling window size for the Endgame ELO timeline chart (Phase 57).
# Matches SCORE_GAP_TIMELINE_WINDOW and CLOCK_PRESSURE_TIMELINE_WINDOW (D-05, D-06).
ENDGAME_ELO_TIMELINE_WINDOW = 100
```

**Two-stream weekly rolling helper** (clone from lines 558-615):
```python
# Tag each game with its side ("endgame"/"non_endgame") and merge into a
# single chronological event stream. We can't just walk both lists in
# lockstep — events must interleave by played_at to keep the rolling
# windows in sync with real history.
events: list[tuple[Any, Literal["endgame", "non_endgame"], float]] = []
for row in endgame_rows:
    score = _score_for(row)
    if score is None:
        continue
    events.append((row[0], "endgame", score))
for row in non_endgame_rows:
    ...

events.sort(key=lambda e: e[0])

endgame_window: list[float] = []
non_endgame_window: list[float] = []
data_by_week: dict[tuple[int, int], dict[str, Any]] = {}

for played_at, side, score in events:
    if side == "endgame":
        endgame_window.append(score)
        endgame_window = endgame_window[-window:]
    else:
        non_endgame_window.append(score)
        non_endgame_window = non_endgame_window[-window:]

    ...

    iso_year, iso_week, iso_weekday = played_at.isocalendar()
    monday = (played_at - timedelta(days=iso_weekday - 1)).date()
    data_by_week[(iso_year, iso_week)] = {
        "date": monday.isoformat(),
        ...
    }

return [
    ScoreGapTimelinePoint(**data_by_week[key])
    for key in sorted(data_by_week.keys())
    if data_by_week[key]["endgame_game_count"] >= MIN_GAMES_FOR_TIMELINE
    and ...
    and (cutoff_str is None or data_by_week[key]["date"] >= cutoff_str)
]
```

**Changes for Phase 57:**
1. Event streams are endgame-rows-with-rich-columns and all-games-rows (not "non-endgame"). The "all games" stream drives the Actual ELO line.
2. Event rows carry additional columns: `user_color`, `white_rating`, `black_rating` (to derive user_rating and opp_rating); endgame rows also carry bucket data (`user_material_imbalance`, `user_material_imbalance_after`, `result`) needed to compute skill per window.
3. Per week, compute `endgame_elo = round(avg_opp + 400 * log10(clamp(skill) / (1 − clamp)))` AND `actual_elo = round(mean(user_rating window))`. Emit when endgame-window ≥ 10.
4. Partition by `(platform, time_control_bucket)` before invoking; the helper runs per-combo.

**Orchestrator pattern** (clone from `get_endgame_performance` at lines 1363-1409):
```python
async def get_endgame_performance(session, user_id, time_control, platform, ...) -> EndgamePerformanceResponse:
    cutoff = recency_cutoff(recency)

    # Execute sequentially — AsyncSession is not safe for concurrent use from
    # multiple coroutines, and shares a single DB connection anyway.
    endgame_rows, non_endgame_rows = await query_endgame_performance_rows(session, ...)
    entry_rows = await query_endgame_entry_rows(session, ...)

    return _get_endgame_performance_from_rows(endgame_rows, non_endgame_rows, entry_rows)
```

For Phase 57, the orchestrator fetches per-combo rows, partitions in Python, invokes `_compute_endgame_elo_weekly_series` once per combo, and returns `EndgameEloTimelineResponse`.

**Recency-cutoff pattern — DO NOT starve the window** (clone from `get_endgame_timeline` lines 1435-1457):
```python
cutoff = recency_cutoff(recency)
cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None

# Fetch all games (no recency filter) so rolling windows are pre-filled.
# Other filters (time_control, platform, etc.) still applied.
endgame_rows, non_endgame_rows, per_type_rows = await query_endgame_timeline_rows(
    session, ..., recency_cutoff=None, ...
)

# Compute rolling series over full history, then filter to recency window
endgame_series = _compute_rolling_series(endgame_rows, window)
if cutoff_str:
    endgame_series = [pt for pt in endgame_series if pt["date"] >= cutoff_str]
```

**Sentry pattern** (clone from lines 217-222):
```python
sentry_sdk.set_context("invalid_endgame_class", {"class_int": endgame_class_int})
sentry_sdk.set_tag("source", "endgame_aggregate")
sentry_sdk.capture_exception(ValueError("Unknown endgame_class integer from DB"))
```
Phase 57 is unlikely to need this since the Elo formula is pure math (after clamp, no exceptions), but any new `except` in the orchestrator must follow this shape.

**Sorting convention** (reuse lines 821-822):
```python
# Fixed display order for time control rows (fastest to slowest).
_TIME_CONTROL_ORDER: list[str] = ["bullet", "blitz", "rapid", "classical"]
```
Combos in the response should be ordered platform-first (chess.com, lichess), then by `_TIME_CONTROL_ORDER` within each platform. See Open Question 2 in RESEARCH.md.

---

### `app/schemas/endgames.py` (schema — extend)

**Analog:** self. The closest pattern is `ClockPressureTimelinePoint` + `ClockPressureResponse` (lines 260-293), because they model *a per-point timeline plus a wrapper with the window size*. Extension of `EndgameOverviewResponse` (lines 332-346) is trivial addition of a field.

**Imports** (already at top of file):
```python
from typing import Literal

from pydantic import BaseModel
```
No new imports needed.

**Per-point shape pattern** (clone from `ClockPressureTimelinePoint` lines 260-272):
```python
class ClockPressureTimelinePoint(BaseModel):
    """One point in the clock-diff timeline (quick-260416-w3q).

    date: Monday of the ISO week, YYYY-MM-DD.
    avg_clock_diff_pct: mean of (user_clock - opp_clock) / base_time_seconds * 100
        over the trailing `timeline_window` games (see ClockPressureResponse).
        Positive means the user entered the endgame with more clock than the opponent.
    game_count: games represented in the window (<= timeline_window).
    """

    date: str
    avg_clock_diff_pct: float
    game_count: int
```

For Phase 57 (one point = one week per combo):
```python
class EndgameEloTimelinePoint(BaseModel):
    """One weekly point for a (platform, time_control) combo (Phase 57).

    date: Monday of the ISO week, YYYY-MM-DD.
    endgame_elo: performance rating from skill composite + avg opponent rating,
        derived from the trailing ENDGAME_ELO_TIMELINE_WINDOW endgame games.
    actual_elo: mean user_rating across the trailing window of ALL games
        for this combo (not just endgame games) — per D-04.
    endgame_games_in_window: count of endgame games contributing to the skill /
        opp-avg computation. Used by the frontend tooltip and the ≥ MIN_GAMES_FOR_TIMELINE
        threshold check.
    """
    date: str
    endgame_elo: int
    actual_elo: int
    endgame_games_in_window: int
```

**Wrapper-with-window pattern** (clone from `ClockPressureResponse` lines 275-293):
```python
class ClockPressureResponse(BaseModel):
    """Time Pressure at Endgame Entry — table broken down by time control (Phase 54).
    ...
    timeline: weekly rolling-window series of average clock-diff % across all time
        controls (quick-260416-w3q). Collapsed to a single series — filter by time
        control via the sidebar filter.
    timeline_window: rolling window size used for each timeline point.
    """

    rows: list[ClockStatsRow]
    total_clock_games: int
    total_endgame_games: int
    timeline: list[ClockPressureTimelinePoint]
    timeline_window: int
```

For Phase 57 (per-combo list instead of rows):
```python
class EndgameEloTimelineCombo(BaseModel):
    """One (platform, time_control) combo's paired-line series.

    combo_key: underscore-joined key like "chess_com_blitz" / "lichess_classical".
        Frontend uses this as the lookup key into ELO_COMBO_COLORS.
    platform / time_control: denormalized for the legend label (avoids frontend string-split).
    points: weekly points sorted by date ASC. May be empty if the combo was
        narrowed out by sidebar filters — callers typically drop empty combos.
    """
    combo_key: str
    platform: Literal["chess.com", "lichess"]
    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    points: list[EndgameEloTimelinePoint]


class EndgameEloTimelineResponse(BaseModel):
    """Response for Phase 57 endgame_elo_timeline — one series per qualifying combo.
    ...
    """
    combos: list[EndgameEloTimelineCombo]
    timeline_window: int
```

**EndgameOverviewResponse extension pattern** (clone the existing diff — add one field):
```python
# Existing (lines 332-346):
class EndgameOverviewResponse(BaseModel):
    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    score_gap_material: ScoreGapMaterialResponse
    clock_pressure: ClockPressureResponse
    time_pressure_chart: TimePressureChartResponse
    # Add:
    endgame_elo_timeline: EndgameEloTimelineResponse  # Phase 57
```

---

### `app/repositories/endgame_repository.py` (repository — extend)

**Analog:** self. `query_endgame_performance_rows` (lines 449-520) + `query_rating_history` (`app/repositories/stats_repository.py:46-97`) are both partial matches; Phase 57's query shape composes them.

**Shared filter application — mandatory** (clone from `query_rating_history` lines 86-94):
```python
# Use shared filter helper per CLAUDE.md "Shared Query Filters".
# platform is wrapped in a single-element list because apply_game_filters
# expects Sequence[str] | None for the platform arg.
stmt = apply_game_filters(
    stmt,
    time_control=None,
    platform=[platform],
    rated=None,
    opponent_type=opponent_type,
    recency_cutoff=recency_cutoff,
    opponent_strength=opponent_strength,
)

result = await session.execute(stmt)
return list(result.fetchall())
```

**User-rating case expression** (clone verbatim from `stats_repository.py:63-66`):
```python
user_rating_expr = case(
    (Game.user_color == "white", Game.white_rating),
    else_=Game.black_rating,
).label("user_rating")
```

For Phase 57 also need the opponent-rating mirror (derive from `apply_game_filters` lines 63-66 in `query_utils.py`):
```python
opp_rating_expr = case(
    (Game.user_color == "white", Game.black_rating),
    else_=Game.white_rating,
).label("opp_rating")
```

**Two-stream endgame-and-all-games query pattern** (clone from `query_endgame_performance_rows` at 449-520):
```python
endgame_game_ids_subq = _any_endgame_ply_subquery(user_id)

# Base select for game rows — columns needed for WDL derivation and timeline
game_cols = select(Game.played_at, Game.result, Game.user_color).where(
    Game.user_id == user_id,
    Game.played_at.isnot(None),
)

# Endgame games: id in the endgame subquery
endgame_stmt = game_cols.where(Game.id.in_(select(endgame_game_ids_subq.c.game_id))).order_by(
    Game.played_at.asc()
)
endgame_stmt = apply_game_filters(endgame_stmt, time_control, platform, ...)

# Non-endgame games: id NOT in the endgame subquery
non_endgame_stmt = game_cols.where(
    Game.id.notin_(select(endgame_game_ids_subq.c.game_id))
).order_by(Game.played_at.asc())
non_endgame_stmt = apply_game_filters(non_endgame_stmt, ...)

# Execute sequentially — AsyncSession is not safe for concurrent use from
# multiple coroutines, and a single session uses one DB connection so there's
# no concurrency benefit from asyncio.gather here.
endgame_result = await session.execute(endgame_stmt)
non_endgame_result = await session.execute(non_endgame_stmt)
return list(endgame_result.fetchall()), list(non_endgame_result.fetchall())
```

**Phase 57 modifications:**
1. SELECT list adds `Game.platform`, `Game.time_control_bucket`, `user_rating_expr`, `opp_rating_expr`, plus the bucket columns needed for skill computation (either pre-join to `game_positions` bucket columns, or fetch bucket rows separately).
2. The "non_endgame" side becomes "all games" — drop the `id.notin_` filter, since Actual ELO = avg(user_rating over **ALL** games per combo).
3. Fetch bucket/entry rows (`query_endgame_entry_rows` or `query_endgame_bucket_rows` shape) aligned with the endgame games so skill can be computed per rolling window.

**Alternative minimal path:** invoke 2 existing repo functions sequentially, partition in Python by `(platform, time_control_bucket)`. This avoids inventing a new repo function at all — the orchestrator does the partitioning. RESEARCH.md recommends this composition-only path.

---

### `frontend/src/components/charts/EndgameEloTimelineSection.tsx` (NEW)

**Analog:** `frontend/src/components/charts/EndgameTimelineChart.tsx` (entire file, 179 lines). Exact structural match — same imports, same legend-toggle state, same ChartContainer wrapping, same empty-state shape, same tooltip pattern.

**Imports block** (clone lines 1-6):
```tsx
import { useState, useCallback, useMemo } from 'react';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { createDateTickFormatter, formatDateWithYear, niceWinRateAxis } from '@/lib/utils';
import type { EndgameTimelineResponse } from '@/types/endgames';
```

For Phase 57, swap `niceWinRateAxis` → `niceEloAxis` and `EndgameTimelineResponse` → `EndgameEloTimelineResponse`, add `ELO_COMBO_COLORS, type EloComboKey` from `@/lib/theme`.

**Legend toggle state pattern** (clone verbatim from lines 33-45):
```tsx
const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());

const handleLegendClick = useCallback((dataKey: string) => {
  setHiddenKeys((prev) => {
    const next = new Set(prev);
    if (next.has(dataKey)) {
      next.delete(dataKey);
    } else {
      next.add(dataKey);
    }
    return next;
  });
}, []);
```

**Date dedupe + flatten pattern** (clone from lines 52-57):
```tsx
const allTypeDates = useMemo(() => [
  ...new Set(
    // safe: typeKeys comes from Object.keys(data.per_type), so each key exists
    typeKeys.flatMap((key) => (data.per_type[key] ?? []).map((p) => p.date))
  ),
].sort(), [data.per_type, typeKeys]);
```

For Phase 57: iterate `data.combos[]` and flatten `combo.points[].date`.

**Empty-state pattern** (clone from lines 67-73):
```tsx
// Empty state: no overall data
if (data.overall.length === 0) {
  return (
    <div className="text-center text-muted-foreground py-8">
      Not enough game data for timeline charts.
    </div>
  );
}
```

For Phase 57, the check is `data.combos.length === 0` and the exact copy is locked in UI-SPEC §Copywriting Contract: "Not enough endgame games yet for a timeline." + "Import more games or loosen the recency filter." Wrap with `data-testid="endgame-elo-timeline-empty"`.

**Chart structure pattern** (clone from lines 105-177 — heading, info popover, chart container, XAxis/YAxis/Tooltip/Legend, Line per key):
```tsx
<div>
  <div className="mb-3">
    <h3 className="text-base font-semibold">
      <span className="inline-flex items-center gap-1">
        Win Rate by Endgame Type
        <InfoPopover ariaLabel="Win Rate by Endgame Type info" testId="timeline-per-type-info" side="top">
          Rolling win rate over the last 100 games for each endgame type, sampled once per week. ...
        </InfoPopover>
      </span>
    </h3>
    <p className="text-sm text-muted-foreground mt-1">
      Win rate trend over time, per endgame type.
    </p>
  </div>
  <ChartContainer config={perTypeChartConfig} className="w-full h-72" data-testid="timeline-per-type-chart">
    <LineChart data={perTypeData}>
      <CartesianGrid vertical={false} />
      <XAxis dataKey="date" tickFormatter={formatDateTick} />
      <YAxis domain={yAxis.domain} ticks={yAxis.ticks} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
      <ChartTooltip content={...} />
      <ChartLegend content={<ChartLegendContent hiddenKeys={hiddenKeys} onClickItem={handleLegendClick} />} />
      {typeKeys.map((key) => (
        <Line
          key={key}
          type="monotone"
          dataKey={key}
          stroke={`var(--color-${key})`}
          strokeWidth={2}
          dot={false}
          connectNulls={true}
          hide={hiddenKeys.has(key)}
        />
      ))}
    </LineChart>
  </ChartContainer>
</div>
```

**Phase 57 modifications to the chart block:**
1. Heading: "Endgame ELO Timeline"; sub-description from UI-SPEC locked copy.
2. `InfoPopover` carries `testId="endgame-elo-timeline-info"` and the 4-paragraph locked prose from UI-SPEC §InfoPopover copy.
3. `ChartContainer` gets `data-testid="endgame-elo-timeline-chart"`.
4. `<YAxis domain={yAxis.domain} ticks={yAxis.ticks} tick={{ fontSize: 12 }} />` — no % tickFormatter (Elo values are plain integers).
5. Two `<Line>` elements per combo (bright Endgame ELO + dark Actual ELO), both keyed on `hide={hiddenKeys.has(combo.combo_key)}`. See UI-SPEC §Chart Specification §Lines for the exact stroke props (strokeWidth 2 vs 1.5, strokeDasharray on dark).
6. `ChartLegend` uses a custom `content` with split-swatch (linear-gradient) — see UI-SPEC §Legend — mobile parity decision. One legend entry per combo (not per line). Each entry gets `data-testid="endgame-elo-legend-{combo_key}"`.
7. Tooltip filters payload by `!hiddenKeys.has(combo_key)` per RESEARCH Open Question 3. Gap computed as `endgame_elo - actual_elo` with sign. See UI-SPEC §Tooltip.

**Tooltip pattern** (clone from `EndgameTimelineChart.tsx` lines 129-157):
```tsx
<ChartTooltip
  content={({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1">
        <div className="font-medium">{formatDateWithYear(label as string)}</div>
        {payload
          .filter((item) => item.value !== undefined)
          .map((item) => {
            ...
          })}
      </div>
    );
  }}
/>
```

**Axis recomputation-on-toggle pattern** (clone from `RatingChart.tsx` lines 54-106; niceEloAxis is the promoted helper — see `utils.ts` section below):
```tsx
const yAxis = useMemo(() => {
  // collect visible Elo values across both endgame_elo and actual_elo columns for visible combos
  const visibleValues: number[] = [];
  for (const combo of data.combos) {
    if (hiddenKeys.has(combo.combo_key)) continue;
    for (const pt of combo.points) {
      visibleValues.push(pt.endgame_elo, pt.actual_elo);
    }
  }
  return niceEloAxis(visibleValues);
}, [data.combos, hiddenKeys]);
```

---

### `frontend/src/lib/theme.ts` (config — extend)

**Analog:** self. Existing palette patterns show exactly the shape Phase 57 needs. Reference: `WDL_WIN/WDL_DRAW/WDL_LOSS` (14-18, per-category), `GAUGE_DANGER/GAUGE_SUCCESS/GAUGE_NEUTRAL` (38-40, semantic), and `MY_SCORE_COLOR/OPP_SCORE_COLOR` (70-72, per-series). For `Record<X, Y>` palettes, `FIXED_GAUGE_ZONES: Record<MaterialBucket, GaugeZone[]>` in `EndgameScoreGapSection.tsx:79-95` is the structural match.

**Constant naming convention** (observe throughout `theme.ts`):
- All caps snake_case for color constants.
- Group by subject with comment headers (e.g. `// Board square colors`, `// WDL colors`, `// Time Pressure chart line colors (Phase 55)`).
- `oklch()` preferred over hex for new constants; matches `RatingChart.tsx:14-19` which already uses `oklch()` for the per-TC palette that Phase 57 inherits.

**Palette pattern** (clone shape from `RatingChart.tsx:14-19`, but export from theme.ts per CLAUDE.md §Frontend rule):
```ts
// Existing pattern (RatingChart.tsx):
const chartConfig = {
  bullet: { label: 'Bullet', color: 'oklch(0.60 0.22 30)' },
  blitz: { label: 'Blitz', color: 'oklch(0.65 0.20 260)' },
  rapid: { label: 'Rapid', color: 'oklch(0.70 0.18 80)' },
  classical: { label: 'Classic', color: 'oklch(0.60 0.22 310)' },
};
```

For Phase 57 add to `theme.ts`:
```ts
// Endgame ELO Timeline chart combo palette (Phase 57). 8 combos = 2 platforms × 4 TCs.
// Two constants per combo (bright Endgame ELO stroke + dark Actual ELO stroke) rather
// than an opacity modifier — preserves the "same hue family" read on dark surface.
// Hues chosen to clear WCAG AA 3:1 non-text contrast against oklch(0.145 0 0) background.
// Values locked in 57-UI-SPEC.md §ELO_COMBO_COLORS.

export type EloComboKey =
  | 'chess_com_bullet'
  | 'chess_com_blitz'
  | 'chess_com_rapid'
  | 'chess_com_classical'
  | 'lichess_bullet'
  | 'lichess_blitz'
  | 'lichess_rapid'
  | 'lichess_classical';

export const ELO_COMBO_COLORS: Record<EloComboKey, { bright: string; dark: string }> = {
  chess_com_bullet:    { bright: 'oklch(0.62 0.22 30)',  dark: 'oklch(0.42 0.18 30)'  },
  chess_com_blitz:     { bright: 'oklch(0.65 0.20 260)', dark: 'oklch(0.45 0.16 260)' },
  ...
};
```
Use the exact oklch values from UI-SPEC §ELO_COMBO_COLORS table (lines 81-90).

---

### `frontend/src/lib/utils.ts` (utility — extend)

**Analog:** self. `niceWinRateAxis` (lines 60-75) is the structural twin — same return type `{ domain, ticks }`, same useMemo-friendly design, same Recharts input contract. Axis tick algorithm to extract lives in `RatingChart.tsx:54-106`.

**Existing `niceWinRateAxis`** (clone shape):
```ts
/**
 * Compute a nice y-axis domain and evenly-spaced ticks for win-rate data (0–1).
 * Uses 10% steps when range ≤ 40%, otherwise 20% steps.
 */
export function niceWinRateAxis(values: number[]): { domain: [number, number]; ticks: number[] } {
  if (values.length === 0) return { domain: [0, 1], ticks: [0, 0.2, 0.4, 0.6, 0.8, 1] };

  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const step = (dataMax - dataMin) <= 0.4 ? 0.1 : 0.2;

  const lo = Math.max(0, Math.floor(dataMin / step) * step);
  const hi = Math.min(1, Math.ceil(dataMax / step) * step);

  const ticks: number[] = [];
  for (let v = lo; v <= hi + step / 2; v += step) {
    ticks.push(Math.round(v * 100) / 100);
  }
  return { domain: [lo, hi], ticks };
}
```

**Source of the algorithm to lift** (from `RatingChart.tsx:54-106`):
```tsx
const { yDomain, yTicks } = useMemo(() => {
  const visibleTcs = TIME_CONTROLS.filter((tc) => !hiddenKeys.has(tc));
  if (visibleTcs.length === 0 || chartData.length === 0) {
    return { yDomain: ['auto', 'auto'] as [string, string], yTicks: undefined };
  }

  let min = Infinity;
  let max = -Infinity;
  for (const row of chartData) {
    for (const tc of visibleTcs) {
      const val = row[tc];
      if (typeof val === 'number') {
        if (val < min) min = val;
        if (val > max) max = val;
      }
    }
  }

  if (!isFinite(min) || !isFinite(max)) {
    return { yDomain: ['auto', 'auto'] as [string, string], yTicks: undefined };
  }

  // If all ratings are identical, use a small range so ticks are meaningful
  if (min === max) {
    min = min - 50;
    max = max + 50;
  }

  const range = max - min;

  // Pick the largest step where range/step >= 4 (aim for 4-8 ticks)
  const STEP_CANDIDATES = [10, 20, 50, 100, 200, 500];
  // start with a known numeric value to avoid noUncheckedIndexedAccess widening to number | undefined
  let step: number = 10;
  for (const candidate of STEP_CANDIDATES) {
    if (range / candidate >= 4) {
      step = candidate;
    }
  }

  const domainMin = Math.floor(min / step) * step;
  const domainMax = Math.ceil(max / step) * step;

  const ticks: number[] = [];
  for (let t = domainMin; t <= domainMax; t += step) {
    ticks.push(t);
  }

  return {
    yDomain: [domainMin, domainMax] as [number, number],
    yTicks: ticks,
  };
}, [chartData, hiddenKeys]);
```

**For Phase 57 — new `niceEloAxis`** — UI-SPEC §Axes (lines 196-205) prescribes:
- Input: flat array of pre-filtered numeric Elo values.
- Step candidates: `[50, 100, 200, 500]` (UI-SPEC differs from RatingChart's `[10, 20, 50, 100, 200, 500]` — Elo ranges are always ≥ 50, so smaller steps are noise).
- Fallback when all equal: ±50 around the point.
- Fallback when empty: `{ domain: ['auto', 'auto'], ticks: undefined }` (Recharts auto-scale).
- Return type: match `niceWinRateAxis` return shape but add the `'auto'` domain fallback — likely `{ domain: [number, number] | ['auto', 'auto']; ticks: number[] | undefined }`.

**Knip-safe**: the new export must be imported by `EndgameEloTimelineSection.tsx` (and ideally by the existing `RatingChart.tsx` as a refactor — but that's a quick-win, not phase scope). Per CLAUDE.md §Frontend Code Style, Knip CI will fail if an export is unused.

---

### `frontend/src/types/endgames.ts` (types — extend)

**Analog:** self. Existing types mirror Pydantic 1:1 (see `ClockPressureTimelinePoint` 136-140, `ClockPressureResponse` 142-148, `EndgameOverviewResponse` 163-170).

**Imports** (no change):
```ts
import type { GameRecord } from './api';
```

**Per-point + response-wrapper pattern** (clone from lines 136-148):
```ts
export interface ClockPressureTimelinePoint {
  date: string;
  avg_clock_diff_pct: number;
  game_count: number;
}

export interface ClockPressureResponse {
  rows: ClockStatsRow[];
  total_clock_games: number;
  total_endgame_games: number;
  timeline: ClockPressureTimelinePoint[];
  timeline_window: number;
}
```

For Phase 57:
```ts
export type EloComboKey =
  | 'chess_com_bullet'
  | 'chess_com_blitz'
  | 'chess_com_rapid'
  | 'chess_com_classical'
  | 'lichess_bullet'
  | 'lichess_blitz'
  | 'lichess_rapid'
  | 'lichess_classical';

export interface EndgameEloTimelinePoint {
  date: string;                    // Monday of ISO week, YYYY-MM-DD
  endgame_elo: number;
  actual_elo: number;
  endgame_games_in_window: number; // drives the ≥ 10 threshold + tooltip
}

export interface EndgameEloTimelineCombo {
  combo_key: EloComboKey;
  platform: 'chess.com' | 'lichess';
  time_control: 'bullet' | 'blitz' | 'rapid' | 'classical';
  points: EndgameEloTimelinePoint[];
}

export interface EndgameEloTimelineResponse {
  combos: EndgameEloTimelineCombo[];
  timeline_window: number;
}
```

Decide: duplicate `EloComboKey` between `theme.ts` and `types/endgames.ts` OR import one from the other. Pragmatic choice: define in `types/endgames.ts` (mirror of Pydantic `Literal`), re-export from `theme.ts` via `import type { EloComboKey } from '@/types/endgames'`.

**EndgameOverviewResponse extension pattern** (clone the existing diff — add one field at line 170):
```ts
export interface EndgameOverviewResponse {
  stats: EndgameStatsResponse;
  performance: EndgamePerformanceResponse;
  timeline: EndgameTimelineResponse;
  score_gap_material: ScoreGapMaterialResponse;
  clock_pressure: ClockPressureResponse;
  time_pressure_chart: TimePressureChartResponse;
  endgame_elo_timeline: EndgameEloTimelineResponse;  // Phase 57
}
```

---

### `frontend/src/pages/Endgames.tsx` (page — extend)

**Analog:** self. The existing `statisticsContent` block (lines 217-321) shows the exact wiring idiom: pull data from `useEndgameOverview`, compute `show*` booleans, render a section h2 + `charcoal-texture rounded-md p-4` card wrapper around each subcomponent.

**Import pattern** (clone line 23 idiom):
```tsx
import { EndgameScoreGapSection } from '@/components/charts/EndgameScoreGapSection';
```
Add for Phase 57:
```tsx
import { EndgameEloTimelineSection } from '@/components/charts/EndgameEloTimelineSection';
```

**Data extraction from overview response** (pattern used throughout `statisticsContent` — the existing code destructures fields like `statsData`, `perfData`, `scoreGapData`, `clockPressureData`, `timelineData`, `timePressureChartData` from the overview query result).

Locate the existing destructure site (grep for `const timelineData`) and add `const eloTimelineData = overviewData?.endgame_elo_timeline;`.

**Show-guard pattern** (clone from lines 212-215):
```tsx
const showPerfSection = !!(perfData && perfData.endgame_wdl.total > 0);
const showClockPressure = !!(clockPressureData && clockPressureData.rows.length > 0);
const showTimePressureChart = !!(timePressureChartData && timePressureChartData.total_endgame_games > 0);
const showTimeline = !!(timelineData && timelineData.overall.length > 0);
```
Phase 57 differs per UI-SPEC §Conditional render (Pitfall 4 in RESEARCH.md): the `<EndgameEloTimelineSection />` must ALWAYS render so the heading + info popover stay visible; only the chart body swaps to empty-state when `data.combos.length === 0`. So no outer `showEloTimeline &&` guard is needed — render unconditionally when `eloTimelineData` exists.

**Section placement pattern** (clone verbatim from lines 304-321 with the `{showTimeline && ...}` wrapper removed per above):
```tsx
{/* ── Endgame Type Breakdown ── */}
<h2 className="text-lg font-semibold text-foreground mt-2">Endgame Type Breakdown</h2>
<div className="charcoal-texture rounded-md p-4">
  <EndgameWDLChart categories={statsData.categories} onCategorySelect={handleCategorySelect} />
</div>
{statsData.categories.length > 0 && (
  <div className="charcoal-texture rounded-md p-4">
    <EndgameConvRecovChart categories={statsData.categories} />
  </div>
)}
{showTimeline && (
  <div className="charcoal-texture rounded-md p-4">
    <EndgameTimelineChart data={timelineData} />
  </div>
)}
```

For Phase 57, add a new shared-h2 block AFTER the Type Breakdown group per UI-SPEC §Section Layout & Placement:
```tsx
{/* ── Endgame ELO (shared container for Phase 56 breakdown + Phase 57 timeline) ── */}
{eloTimelineData && (
  <>
    <h2 className="text-lg font-semibold text-foreground mt-2">Endgame ELO</h2>
    {/* Phase 56 breakdown table will also live here when that phase ships. */}
    <div className="charcoal-texture rounded-md p-4" data-testid="endgame-elo-timeline-section">
      <EndgameEloTimelineSection data={eloTimelineData} />
    </div>
  </>
)}
```

**Mobile / desktop parity:** lines 478 and 551 show `{statisticsContent}` reused in both the desktop sidebar layout and the mobile drawer layout. Phase 57 inherits this automatically — one component, one render site, no duplicated markup.

**Error-state pattern** (clone from lines 323-329 — shown when the overview query itself errors):
```tsx
) : overviewError ? (
  <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
    <p className="mb-2 text-base font-medium text-foreground">Failed to load endgame data</p>
    <p className="text-sm text-muted-foreground">
      Something went wrong. Please try again in a moment.
    </p>
  </div>
)
```
Phase 57 inherits this page-level error handling via the shared `overviewError` branch. The component-level `data-testid="endgame-elo-timeline-error"` from UI-SPEC §Browser Automation Contract applies only if the component itself branches on a sub-error (it doesn't — the overview response already succeeded by the time `EndgameEloTimelineSection` renders).

---

### `tests/test_endgame_service.py` (test — extend)

**Analog:** self. `TestComputeScoreGapTimeline` (lines 2559-2680) is the exact structural twin — tests a weekly-rolling two-stream timeline helper with the same inputs/outputs shape Phase 57 will have.

**Imports pattern** (clone from lines 1-42 — add new symbols):
```python
import datetime
from typing import Any, NamedTuple
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import EndgameWDLSummary
from app.services.endgame_service import (
    CLOCK_PRESSURE_TIMELINE_WINDOW,
    SCORE_GAP_TIMELINE_WINDOW,
    _aggregate_endgame_stats,
    ...,
)
```
Add Phase 57 imports: `ENDGAME_ELO_TIMELINE_WINDOW`, `_compute_endgame_elo_weekly_series` (or whatever the helper ends up being named), `_endgame_elo_from_skill` if exposed.

**Test row fixture pattern** (clone from lines 44-58 and 2550-2556):
```python
class _FakeRow(NamedTuple):
    """Lightweight stand-in for a SQLAlchemy Row used by endgame service tests."""
    game_id: int
    endgame_class: int
    result: str
    user_color: str
    user_material_imbalance: Any
    user_material_imbalance_after: Any


def _perf_row(played_at: Any, result: str, user_color: str) -> tuple:
    """Build a row matching query_endgame_performance_rows output shape.

    Shape: (played_at, result, user_color). Used for the score-gap timeline
    where derive_user_result(result, user_color) yields the per-game outcome.
    """
    return (played_at, result, user_color)
```

For Phase 57, add an `_elo_row` helper matching the Phase 57 row shape (played_at, user_color, white_rating, black_rating, ... plus bucket columns for the endgame side).

**Test class structure** (clone pattern from lines 2559-2680):
```python
class TestComputeScoreGapTimeline:
    """Unit tests for _compute_score_gap_timeline (quick-260417-o2l)."""

    def test_empty_inputs_returns_empty(self):
        assert _compute_score_gap_timeline([], [], 100) == []

    def test_drops_weeks_with_either_side_below_min_games(self):
        """10 endgame games + 5 non-endgame games -> no points (non_endgame < 10)."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        ...

    def test_emits_one_point_per_iso_week_using_rolling_diff(self):
        ...

    def test_rolling_window_caps_at_window_size(self):
        ...

    def test_skips_rows_without_played_at(self):
        ...
```

For Phase 57, RESEARCH.md §Phase Requirements → Test Map specifies these test names:
- `TestEndgameElo::test_clamp_boundaries` — skill=0.0 and skill=1.0 don't blow up.
- `TestEndgameElo::test_formula` — `round(avg_opp + 400·log10(clamp(skill) / (1 − clamp)))` produces the expected value for known inputs.
- `TestEndgameEloTimeline::test_actual_elo_from_all_games` — Actual ELO = mean(user_rating over all-games-100-window), not endgame-only.
- `TestEndgameEloTimeline::test_below_min_games_dropped` — weekly point dropped when endgame window < 10 (D-06).
- `TestEndgameEloTimeline::test_combo_dropped_when_zero_points` — combo entirely absent from response when no qualifying points (D-10 tier 2).
- `TestEndgameEloTimeline::test_cutoff_does_not_starve_window` — recency cutoff filters output but window pre-fills from earlier games (Pitfall 2).

**Integration test pattern** (point to existing `tests/test_integration_routers.py` — follows the mock/AsyncMock pattern in `TestGetEndgameTimeline` at line 666 of this file).

---

## Shared Patterns

### CLAUDE.md §Critical Constraints — no `asyncio.gather` on `AsyncSession`

**Source:** `app/services/endgame_service.py:1384-1386` and `app/repositories/endgame_repository.py:514-518`
**Apply to:** `app/services/endgame_service.py` orchestrator (Phase 57) and any new repo function

```python
# Execute sequentially — AsyncSession is not safe for concurrent use from
# multiple coroutines, and shares a single DB connection anyway.
endgame_rows, non_endgame_rows = await query_endgame_performance_rows(session, ...)
entry_rows = await query_endgame_entry_rows(session, ...)
```

### CLAUDE.md §Shared Query Filters — `apply_game_filters` as the only path

**Source:** `app/repositories/query_utils.py:13-78`
**Apply to:** any new or modified SQL in `app/repositories/endgame_repository.py`

Invocation template (clone from `query_rating_history` lines 86-94):
```python
stmt = apply_game_filters(
    stmt,
    time_control=None,
    platform=[platform],
    rated=None,
    opponent_type=opponent_type,
    recency_cutoff=recency_cutoff,
    opponent_strength=opponent_strength,
)
```
Never inline WHERE clauses that duplicate these filters — bug by design per CLAUDE.md.

### CLAUDE.md §Frontend — theme constants centralized

**Source:** `frontend/src/lib/theme.ts`
**Apply to:** any color usage in `EndgameEloTimelineSection.tsx`

All `oklch()` strings (bright+dark per combo) live in `ELO_COMBO_COLORS`. Component imports the record, never inlines hex/oklch.

### CLAUDE.md §Frontend Code Style — `noUncheckedIndexedAccess`

**Source:** `frontend/src/components/charts/EndgameTimelineChart.tsx:54,62,80` ("// safe: typeKeys comes from Object.keys(...), so each key exists") and `RatingChart.tsx:86-87` ("start with a known numeric value to avoid noUncheckedIndexedAccess widening")

**Apply to:** every `ELO_COMBO_COLORS[combo]` access in `EndgameEloTimelineSection.tsx`

Either (preferred) narrow `combo.combo_key: string` to `EloComboKey` at the API boundary and read `ELO_COMBO_COLORS[combo_key as EloComboKey]` after validating against the known set, or use `ELO_COMBO_COLORS[combo_key] ?? FALLBACK` to satisfy strict indexing.

### Recharts legend+line toggle pattern

**Source:** `frontend/src/components/charts/EndgameTimelineChart.tsx:33-45` (legend state), `RatingChart.tsx:22-34` (same pattern)
**Apply to:** `EndgameEloTimelineSection.tsx`

Standard `Set<string>` keyed by combo, with `ChartLegendContent` receiving `hiddenKeys` + `onClickItem`. See `frontend/src/components/ui/chart.tsx:107-169` for the primitive — it already supports these props.

### Browser automation — `data-testid` on all structural + interactive elements

**Source:** CLAUDE.md §Browser Automation Rules + every existing chart component
**Apply to:** `EndgameEloTimelineSection.tsx` and `Endgames.tsx` wiring

Locked IDs from UI-SPEC §Browser Automation Contract:
- Section wrapper: `endgame-elo-timeline-section`
- ChartContainer: `endgame-elo-timeline-chart`
- Info popover trigger: `endgame-elo-timeline-info`
- Legend item per combo: `endgame-elo-legend-{combo_key}`
- Empty-state container: `endgame-elo-timeline-empty`
- Error-state container: `endgame-elo-timeline-error`

### Sentry in service orchestrators

**Source:** `app/services/endgame_service.py:217-222` + CLAUDE.md §Error Handling & Sentry
**Apply to:** any non-trivial `except` in the Phase 57 service orchestrator

Elo formula itself is pure math (after clamp) so should not throw. Only relevant if the orchestrator adds defensive parsing or network-adjacent logic — unlikely for Phase 57.

---

## No Analog Found

**None.** Every file in Phase 57 has a concrete in-repo analog. The only truly new code is the ~4-line Elo formula (`round(avg_opp + 400·log10(clamp(skill) / (1 − clamp)))`) which has no analog by design.

---

## Metadata

**Analog search scope:**
- `app/services/` (endgame_service.py, openings_service.py, stats_service.py)
- `app/repositories/` (endgame_repository.py, stats_repository.py, query_utils.py)
- `app/schemas/` (endgames.py)
- `app/routers/` (endgames.py)
- `frontend/src/components/charts/` (EndgameTimelineChart, EndgameScoreGapSection, EndgameClockPressureSection)
- `frontend/src/components/stats/RatingChart.tsx`
- `frontend/src/components/ui/chart.tsx`
- `frontend/src/lib/` (theme.ts, utils.ts)
- `frontend/src/types/endgames.ts`
- `frontend/src/pages/Endgames.tsx`
- `frontend/src/hooks/useEndgames.ts`
- `tests/test_endgame_service.py`

**Files scanned:** ~18 source files + 3 planning docs (CONTEXT, RESEARCH, UI-SPEC).

**Pattern extraction date:** 2026-04-18

**Key takeaway for planner:** Phase 57 is a composition phase. The locked algorithm (D-01) plus the locked visual spec (57-UI-SPEC.md) leave essentially zero design choices for the executor — every line of code either copies from a named analog or implements the clamped log-odds formula. Plans should reference analog line numbers verbatim in each task's action section so the executor never has to invent structure.

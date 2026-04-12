# Phase 55: Time Pressure — Performance Chart - Research

**Researched:** 2026-04-12
**Domain:** Recharts line chart + bucketed performance aggregation + tabbed by time control
**Confidence:** HIGH

## Summary

Phase 55 adds a two-line Recharts `LineChart` that answers "do I crack under time pressure more than my opponents?" — each line shows average score at 10 equal-width time-remaining buckets, tabbed by time control. The heavy lifting (clock extraction, ply-parity logic, `query_clock_stats_rows`) already exists from Phase 54. The new phase adds:

1. A new `_compute_time_pressure_chart` service function that re-uses Phase 54's `clock_rows` (the same data already fetched in `get_endgame_overview`) to build per-bucket score averages grouped by time control.
2. A new `TimePressureChartResponse` Pydantic schema and a corresponding TypeScript interface.
3. `EndgameOverviewResponse` gains a new `time_pressure_chart` field.
4. A new `EndgameTimePressureSection` React component with Tabs (one per time control) and a Recharts `LineChart`.

No new repository query or DB round-trip is needed — `query_clock_stats_rows` already returns everything required (user_score derivable from `result`/`user_color`, both clocks, `time_control_bucket`).

**Primary recommendation:** Re-use `clock_rows` already fetched in `get_endgame_overview`; compute bucket aggregates in a pure service function; render with Recharts `LineChart` + Radix Tabs variant `"default"` (not `"brand"`) inside a new container section.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None — discuss phase was skipped per user request.

### Claude's Discretion
All implementation choices are at Claude's discretion. Detailed specs are in `docs/endgame-analysis-v2.md` section 3.2. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

---

## Project Constraints (from CLAUDE.md)

[VERIFIED: codebase grep]

- **Backend**: FastAPI 0.115.x, Python 3.13, SQLAlchemy 2.x async. `uv run ty check app/ tests/` must pass with zero errors.
- **Never `asyncio.gather` on same `AsyncSession`** — queries must be sequential.
- **Pydantic v2** for all schemas; `Literal[...]` for fixed-value fields; `Sequence[str]` not `list[str]` for covariant params.
- **`ty` compliance**: explicit return type annotations on all functions; `# ty: ignore[rule-name]` with reason for suppressed errors.
- **Frontend**: `data-testid` on every interactive element; `noUncheckedIndexedAccess` enabled (index access returns `T | undefined`); Knip runs in CI.
- **Theme constants in `theme.ts`**: semantic colors (score lines, dim state) must be defined there and imported.
- **Mobile-friendly UI**: apply changes to both desktop and mobile layouts.
- **No magic numbers**: extract `MIN_GAMES_FOR_CLOCK_STATS = 10` (already in service) and bucket width into named constants.
- **Sentry**: capture exceptions in non-trivial except blocks; never embed variables in error message strings.

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| recharts | existing | LineChart, Line, CartesianGrid, XAxis, YAxis | [VERIFIED: codebase] |
| `@/components/ui/chart` | internal | ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent | [VERIFIED: codebase] |
| `@/components/ui/tabs` | internal | Tabs, TabsList, TabsTrigger, TabsContent (variants: default/brand/underline/line) | [VERIFIED: codebase] |
| Pydantic v2 | existing | backend response schemas | [VERIFIED: codebase] |

No new packages required.

---

## Architecture Patterns

### Data Flow

```
clock_rows (already fetched in get_endgame_overview)
  └─> _compute_time_pressure_chart(clock_rows)   [NEW pure service fn]
        └─> TimePressureChartResponse             [NEW Pydantic schema]
              └─> EndgameOverviewResponse.time_pressure_chart  [NEW field]
                    └─> EndgameTimePressureSection             [NEW component]
```

`get_endgame_overview` already calls `query_clock_stats_rows` and stores the result in `clock_rows`. Pass `clock_rows` to `_compute_time_pressure_chart` alongside `_compute_clock_pressure` — zero extra DB round-trips.

### Bucketing Algorithm

[VERIFIED: docs/endgame-analysis-v2.md section 3.2]

```python
NUM_BUCKETS = 10
BUCKET_WIDTH_PCT = 10  # each bucket spans 10 percentage points

def _time_pct_to_bucket(pct: float) -> int:
    """Map time remaining % (0-100) to bucket index 0-9."""
    bucket = int(pct / BUCKET_WIDTH_PCT)
    return min(bucket, NUM_BUCKETS - 1)  # clamp 100% to bucket 9

# X-axis label for bucket i: f"{i*10}-{(i+1)*10}%"
```

### Score Derivation

[VERIFIED: docs/endgame-analysis-v2.md section 3.2]

```python
# user_score: 1.0 win, 0.5 draw, 0.0 loss
# "My score" series: AVG(user_score) grouped by user's bucket
# "Opponent's score" series: AVG(1 - user_score) grouped by opponent's bucket
```

Both series use the SAME games — each game contributes twice: once to user's bucket, once to opponent's bucket.

### Backend Schema (new)

```python
# app/schemas/endgames.py — additions

class TimePressureBucketPoint(BaseModel):
    """One data point in the time-pressure performance chart (Phase 55).

    bucket_index: 0-9 (0 = 0-10% time remaining, 9 = 90-100%)
    bucket_label: "0-10%" ... "90-100%"
    score: AVG score for this series in this bucket (0.0-1.0); None if game_count == 0
    game_count: number of games backing this data point
    """
    bucket_index: int          # 0-9
    bucket_label: str          # "0-10%" etc.
    score: float | None        # None when game_count == 0
    game_count: int


class TimePressureChartRow(BaseModel):
    """Per-time-control data for the time-pressure chart (Phase 55).

    time_control: one of bullet/blitz/rapid/classical
    label: "Bullet" etc.
    total_endgame_games: total endgame games for this time control (with clock data)
    user_series: 10 points — user's score by user's time bucket
    opp_series: 10 points — opponent's score by opponent's time bucket
    """
    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    label: str
    total_endgame_games: int
    user_series: list[TimePressureBucketPoint]   # always 10 elements
    opp_series: list[TimePressureBucketPoint]    # always 10 elements


class TimePressureChartResponse(BaseModel):
    """Time Pressure vs Performance chart data (Phase 55).

    rows: per-time-control data; only rows with >= MIN_GAMES_FOR_CLOCK_STATS games included.
    """
    rows: list[TimePressureChartRow]


# EndgameOverviewResponse gets new field:
# time_pressure_chart: TimePressureChartResponse  # Phase 55
```

### Service Function Pattern

```python
# app/services/endgame_service.py

def _compute_time_pressure_chart(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> TimePressureChartResponse:
    """Compute time-pressure performance chart data from clock_rows.

    Reuses the same clock_rows already fetched in get_endgame_overview by
    query_clock_stats_rows — no additional DB query needed.

    For each game with both clocks:
    - Bucket user's time% -> accumulate user_score (1/0.5/0) into user_series
    - Bucket opp's time% -> accumulate (1 - user_score) into opp_series
    Both series are populated from the same game.

    Returns TimePressureChartResponse with rows for time controls having
    >= MIN_GAMES_FOR_CLOCK_STATS games with clock data.
    """
    # Source: docs/endgame-analysis-v2.md section 3.2
    ...
```

### Frontend Component Pattern

```tsx
// frontend/src/components/charts/EndgameTimePressureSection.tsx

import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ChartContainer, ChartTooltip, ChartLegend, ChartLegendContent } from '@/components/ui/chart';
import { LineChart, Line, CartesianGrid, XAxis, YAxis } from 'recharts';
import { InfoPopover } from '@/components/ui/info-popover';
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';

// Chart line colors — defined in theme.ts per CLAUDE.md rule
// MY_SCORE_COLOR = blue; OPP_SCORE_COLOR = red
import { MY_SCORE_COLOR, OPP_SCORE_COLOR } from '@/lib/theme';
```

**Tab selection behavior** [VERIFIED: docs/endgame-analysis-v2.md section 3.2]:
- Multiple time controls in data → render Tabs with one tab per row
- Single time control → render chart directly (no tabs wrapper)
- Controlled via `useState` with first available tab as default

**Dot dimming pattern for < 10 games per bucket**:

Recharts `Line` supports a `dot` render prop. When `game_count < MIN_GAMES_FOR_RELIABLE_STATS`, render a dim dot at reduced opacity:

```tsx
dot={(props) => {
  const { cx, cy, payload } = props;
  const isDim = (payload.game_count ?? 0) < MIN_GAMES_FOR_RELIABLE_STATS;
  return (
    <circle
      key={`dot-${payload.bucket_index}`}
      cx={cx}
      cy={cy}
      r={4}
      fill={color}
      opacity={isDim ? UNRELIABLE_OPACITY : 1}
    />
  );
}}
```

[VERIFIED: codebase — `UNRELIABLE_OPACITY = 0.5` in theme.ts, dot render prop supported in Recharts]

### X-Axis Format

X-axis shows 10 labels: `"0-10%"`, `"10-20%"`, ..., `"90-100%"`. With 10 labels on a small chart these may crowd on mobile. Use `angle={-30}` or `tickFormatter` to shorten to `"0%"`, `"10%"`, ..., `"90%"` (meaning "up to N% remaining"):

```tsx
<XAxis
  dataKey="bucket_label"
  tickFormatter={(v: string) => v.split('-')[0]!}
  // e.g. "0-10%" -> "0%", "90-100%" -> "90%"
/>
```

### Y-Axis

Fixed domain `[0, 1]` with ticks every 0.2 is appropriate since score is always in `[0.0, 1.0]`. Can use `niceWinRateAxis` if tight clustering, but given the spec says "Y-axis = score (0.0 to 1.0)" a fixed `domain={[0, 1]}` is clearest.

```tsx
<YAxis
  domain={[0, 1]}
  ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]}
  tickFormatter={(v: number) => v.toFixed(1)}
/>
```

### Placement in Endgames.tsx

New section added after the `clockPressureData` block in `statisticsContent`:

```tsx
{timePressureChartData && timePressureChartData.rows.length > 0 && (
  <div className="charcoal-texture rounded-md p-4">
    <EndgameTimePressureSection data={timePressureChartData} />
  </div>
)}
```

`timePressureChartData` comes from `overviewData?.time_pressure_chart`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Clock extraction | Custom ply-parity logic | `_extract_entry_clocks` (Phase 54, already exists) |
| New DB query | Extra `game_positions` scan | Re-use `clock_rows` from `query_clock_stats_rows` already in `get_endgame_overview` |
| Dot dimming | CSS hacks | Recharts `dot` render prop with inline opacity |
| Tab rendering | Custom tab UI | Existing `Tabs/TabsList/TabsTrigger/TabsContent` from `@/components/ui/tabs` |
| Color constants | Inline oklch strings | Add to `theme.ts` and import |

---

## Common Pitfalls

### Pitfall 1: Two Passes Per Game, One Accumulator Per Series
**What goes wrong:** Confusing "each game contributes to BOTH user_series and opp_series" — they are separate accumulators, not a single WDL table.
**Why it happens:** The description mentions "same games bucketed twice."
**How to avoid:** Use two separate `defaultdict` structures: `tc_user_buckets[tc][bucket_idx]` and `tc_opp_buckets[tc][bucket_idx]`, each accumulating (score_sum, game_count).

### Pitfall 2: Excluding Games Without Both Clocks
**What goes wrong:** Including games where only one clock is available, which would make the user_series and opp_series non-comparable (different game pools).
**How to avoid:** Require BOTH `user_clock is not None and opp_clock is not None` before accumulating into either series. This is the same guard already used in `_compute_clock_pressure`.

### Pitfall 3: `time_control_seconds` Is Needed for Percentage
**What goes wrong:** Accessing `time_control_seconds` from `clock_rows` row but it can be `None` for some games.
**How to avoid:** Check `time_control_seconds is not None and time_control_seconds > 0` before computing `pct = clock / time_control_seconds * 100`. Skip games without `time_control_seconds` (they cannot be bucketed by %).

### Pitfall 4: Bucket Clamping for 100% Time Remaining
**What goes wrong:** `int(100 / 10) = 10` which is out of bounds for a 0-9 index.
**How to avoid:** `bucket = min(int(pct / 10), 9)` — clamp to 9.

### Pitfall 5: `noUncheckedIndexedAccess` in TypeScript
**What goes wrong:** `row.user_series[i]` returns `TimePressureBucketPoint | undefined`. Accessing `.score` directly causes a type error.
**How to avoid:** Always assign to a local variable and narrow: `const pt = row.user_series[i]; if (pt) { ... }`.

### Pitfall 6: Tab Value When Only One Time Control
**What goes wrong:** Wrapping a single time control in `<Tabs>` causes a one-tab UI that looks odd; the spec says single selection = no tabs.
**How to avoid:** `if (rows.length === 1) { render chart directly }; else { render Tabs wrapper }`.

### Pitfall 7: Recharts `dot` Render Prop Key
**What goes wrong:** Recharts `dot` render prop called per-point; missing `key` prop causes React warning.
**How to avoid:** Return `<circle key={...} ...>` with a stable key (e.g. `bucket_label` or `bucket_index`).

### Pitfall 8: `ty` Complaint on `cast()` for Literal Type Control Field
**What goes wrong:** `time_control` field is typed `Literal["bullet", "blitz", "rapid", "classical"]` but `tc` is `str`. Same pattern already solved in `_compute_clock_pressure`.
**How to avoid:** Use `cast(Literal["bullet", "blitz", "rapid", "classical"], tc)` with same pattern as Phase 54.

---

## Code Examples

### Service Layer Accumulator Pattern

```python
# Source: app/services/endgame_service.py (_compute_clock_pressure — Phase 54)
# Extended pattern for bucket accumulation

# Per-time-control, per-bucket accumulators
# tc_user_buckets[tc][bucket_idx] = [score_sum, game_count]
tc_user_buckets: dict[str, list[list[float]]] = defaultdict(
    lambda: [[0.0, 0] for _ in range(NUM_BUCKETS)]
)
tc_opp_buckets: dict[str, list[list[float]]] = defaultdict(
    lambda: [[0.0, 0] for _ in range(NUM_BUCKETS)]
)

for row in clock_rows:
    ...
    user_clock, opp_clock = _extract_entry_clocks(ply_array, clock_array, user_color)
    if user_clock is None or opp_clock is None:
        continue
    if time_control_seconds is None or time_control_seconds <= 0:
        continue

    user_pct = user_clock / time_control_seconds * 100
    opp_pct = opp_clock / time_control_seconds * 100
    user_bucket = min(int(user_pct / BUCKET_WIDTH_PCT), NUM_BUCKETS - 1)
    opp_bucket = min(int(opp_pct / BUCKET_WIDTH_PCT), NUM_BUCKETS - 1)

    user_score = {"win": 1.0, "draw": 0.5, "loss": 0.0}[
        derive_user_result(result, user_color)
    ]

    tc_user_buckets[tc][user_bucket][0] += user_score
    tc_user_buckets[tc][user_bucket][1] += 1

    tc_opp_buckets[tc][opp_bucket][0] += (1.0 - user_score)
    tc_opp_buckets[tc][opp_bucket][1] += 1
```

### Building Series Points

```python
def _build_bucket_series(
    buckets: list[list[float]],
) -> list[TimePressureBucketPoint]:
    """Build 10-point series from accumulated [score_sum, game_count] pairs."""
    points: list[TimePressureBucketPoint] = []
    for i, (score_sum, game_count) in enumerate(buckets):
        lo = i * BUCKET_WIDTH_PCT
        hi = (i + 1) * BUCKET_WIDTH_PCT
        label = f"{lo}-{hi}%"
        score = (score_sum / game_count) if game_count > 0 else None
        points.append(TimePressureBucketPoint(
            bucket_index=i,
            bucket_label=label,
            score=score,
            game_count=game_count,
        ))
    return points
```

### Frontend: Merging Two Series Into One Chart Data Array

```tsx
// Each element maps one X-axis bucket label to both series' values
const chartData = row.user_series.map((userPt, i) => {
  const oppPt = row.opp_series[i];  // noUncheckedIndexedAccess: T | undefined
  return {
    bucket_label: userPt.bucket_label,
    my_score: userPt.score ?? undefined,      // null -> undefined produces gap
    opp_score: oppPt?.score ?? undefined,
    my_game_count: userPt.game_count,
    opp_game_count: oppPt?.game_count ?? 0,
  };
});
```

### Frontend: Tab Rendering Pattern

```tsx
// Source: frontend/src/pages/Endgames.tsx — existing Tabs usage
// Use variant="default" (not "brand") for inline section tabs

const [activeTab, setActiveTab] = useState(data.rows[0]?.time_control ?? 'bullet');

{data.rows.length === 1 ? (
  <ChartForRow row={data.rows[0]!} />
) : (
  <Tabs value={activeTab} onValueChange={setActiveTab}>
    <TabsList variant="default" data-testid="time-pressure-tabs">
      {data.rows.map((row) => (
        <TabsTrigger
          key={row.time_control}
          value={row.time_control}
          data-testid={`tab-time-pressure-${row.time_control}`}
        >
          {row.label}
        </TabsTrigger>
      ))}
    </TabsList>
    {data.rows.map((row) => (
      <TabsContent key={row.time_control} value={row.time_control}>
        <ChartForRow row={row} />
      </TabsContent>
    ))}
  </Tabs>
)}
```

---

## Codebase Integration Points

[VERIFIED: codebase read]

### Files to Modify

| File | Change |
|------|--------|
| `app/schemas/endgames.py` | Add `TimePressureBucketPoint`, `TimePressureChartRow`, `TimePressureChartResponse`; add `time_pressure_chart: TimePressureChartResponse` to `EndgameOverviewResponse` |
| `app/services/endgame_service.py` | Add `NUM_BUCKETS = 10`, `BUCKET_WIDTH_PCT = 10` constants; add `_compute_time_pressure_chart()` and `_build_bucket_series()` pure functions; call in `get_endgame_overview` passing `clock_rows` |
| `frontend/src/types/endgames.ts` | Add `TimePressureBucketPoint`, `TimePressureChartRow`, `TimePressureChartResponse` interfaces; add `time_pressure_chart: TimePressureChartResponse` to `EndgameOverviewResponse` |
| `frontend/src/lib/theme.ts` | Add `MY_SCORE_COLOR` (blue) and `OPP_SCORE_COLOR` (red) constants |
| `frontend/src/pages/Endgames.tsx` | Import `EndgameTimePressureSection`; extract `timePressureChartData` from `overviewData`; add render block after clock pressure section (both desktop and mobile `statisticsContent`) |

### Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/components/charts/EndgameTimePressureSection.tsx` | New component: section header, InfoPopover, Tabs or direct chart, Recharts LineChart |

### No New Files Required in Backend

The service and schema changes are additive to existing files. No new repository function, no new router endpoint, no new router file — `get_endgame_overview` already collects everything needed.

---

## Key Insight: clock_rows Is the Right Source

Phase 54's `query_clock_stats_rows` returns rows of:
`(game_id, time_control_bucket, time_control_seconds, termination, result, user_color, ply_array, clock_array)`

This contains exactly what Phase 55 needs:
- `result` + `user_color` → `user_score` via `derive_user_result`
- `user_clock` + `opp_clock` → via `_extract_entry_clocks` (already exists)
- `time_control_seconds` → for computing `time_remaining_%`
- `time_control_bucket` → for grouping by time control

`_compute_time_pressure_chart` follows the exact same loop structure as `_compute_clock_pressure` — same row shape, same parity logic, same guard for missing clocks/time_control_seconds.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tabs `variant="default"` (not `"brand"`) is appropriate for inline section tabs — "brand" is used for main page navigation | Architecture Patterns | Low — worst case is a styling inconsistency, easy to change |
| A2 | Fixed Y-axis `[0, 1]` with 0.2 step ticks is cleaner than `niceWinRateAxis` for score data | Architecture Patterns | Low — `niceWinRateAxis` can be swapped in trivially |
| A3 | X-axis tick shortening (show only lower bound `"0%"`, `"10%"` etc.) is preferred for mobile readability | Architecture Patterns | Low — label format is cosmetic |

---

## Open Questions (RESOLVED)

1. **Color choices for My Score (blue) vs Opponent's Score (red)**
   - **RESOLVED:** Use `oklch(0.55 0.18 260)` for blue (same as EndgameConvRecovChart recovery line) and `oklch(0.50 0.15 25)` = `WDL_LOSS` for red — both already in the palette. Incorporated into Plan 55-02 Task 1.

2. **`connectNulls` behavior for sparse buckets**
   - **RESOLVED:** Use `connectNulls={true}` for continuity; the dim-dot rule handles < 10 games visually. Incorporated into Plan 55-02 Task 1.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — purely additive code changes to existing stack)

---

## Validation Architecture

No nyquist_validation config found. Treating as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/test_endgame_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Behavior | Test Type | Notes |
|----------|-----------|-------|
| `_compute_time_pressure_chart` bucket assignment | unit | Pure function, easy to test with synthetic rows |
| `_build_bucket_series` score averaging | unit | Pure function |
| Bucket clamping at 100% | unit | Edge case: pct=100.0 → bucket 9 |
| Games without both clocks excluded | unit | Guards in loop |

### Wave 0 Gaps

Check if `tests/test_endgame_service.py` exists and covers `_compute_time_pressure_chart`. If not, add unit tests as part of Wave 0.

---

## Security Domain

No new authentication, authorization, or input validation surfaces introduced. All inputs flow through existing `apply_game_filters` (validated upstream). No ASVS changes required.

---

## Sources

### Primary (HIGH confidence)
- `[VERIFIED: codebase]` — `app/services/endgame_service.py` — full Phase 54 implementation reviewed
- `[VERIFIED: codebase]` — `app/repositories/endgame_repository.py` — `query_clock_stats_rows` row shape confirmed
- `[VERIFIED: codebase]` — `app/schemas/endgames.py` — existing schema structure confirmed
- `[VERIFIED: codebase]` — `frontend/src/types/endgames.ts` — TypeScript interface shapes confirmed
- `[VERIFIED: codebase]` — `frontend/src/components/charts/EndgameTimelineChart.tsx` — Recharts LineChart pattern
- `[VERIFIED: codebase]` — `frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx` — two-series merge pattern
- `[VERIFIED: codebase]` — `frontend/src/components/ui/tabs.tsx` — tab variants confirmed
- `[VERIFIED: codebase]` — `frontend/src/lib/theme.ts` — `MIN_GAMES_FOR_RELIABLE_STATS`, `UNRELIABLE_OPACITY` confirmed
- `[VERIFIED: codebase]` — `docs/endgame-analysis-v2.md` section 3.2 — spec for bucketing, scoring, display

### Secondary
- `[ASSUMED]` — Recharts `dot` render prop supports per-point opacity control — standard Recharts API, consistent with how other charts in codebase use `dot={false}` as a render prop shorthand

---

## Metadata

**Confidence breakdown:**
- Backend data flow: HIGH — clock_rows already contain all needed fields; verified by reading service/repository
- Bucket algorithm: HIGH — spec is explicit and validated against production data
- Frontend Recharts pattern: HIGH — multiple existing charts follow the same LineChart + ChartContainer pattern
- Dot dimming via render prop: MEDIUM — Recharts supports it but no existing example in codebase (all current charts use `dot={false}`)
- Tab variant choice: MEDIUM — `variant="default"` seems right for inline section tabs, `"brand"` is for main navigation

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable stack, low churn risk)

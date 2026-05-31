# Phase 97: Endgame Metrics by Time Control - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 9 new/modified files + 3 deleted files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/schemas/endgames.py` (modify) | schema | request-response | `app/schemas/endgames.py` — `TimePressureTcCard` / `TimePressureCardsResponse` blocks | exact |
| `app/services/endgame_zones.py` (modify) | config | transform | `app/services/endgame_zones.py` — `PressureBinBand` / `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | exact |
| `app/services/endgame_service.py` (modify) | service | CRUD | `app/services/endgame_service.py` — `_compute_time_pressure_cards` | exact |
| `app/repositories/endgame_repository.py` (modify) | repository | CRUD | `app/repositories/endgame_repository.py` — `query_endgame_entry_rows` (LEAD pattern) | exact |
| `scripts/gen_endgame_zones_ts.py` (modify) | utility | transform | `scripts/gen_endgame_zones_ts.py` — `_format_pressure_bin_zones` / `_format_per_class_gauge_zones` | exact |
| `frontend/src/generated/endgameZones.ts` (regenerated) | config | transform | `frontend/src/generated/endgameZones.ts` — current scalar + object export blocks | exact |
| `frontend/src/components/charts/EndgameMetricsByTcSection.tsx` (new) | component | request-response | `frontend/src/components/charts/EndgameTimePressureSection.tsx` | exact |
| `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` (new) | component | request-response | `frontend/src/components/charts/EndgameTimePressureCard.tsx` | role-match |
| `frontend/src/types/endgames.ts` (modify) | config | request-response | `frontend/src/types/endgames.ts` — `TimePressureTcCard` / `TimePressureCardsResponse` interfaces | exact |

**Files to delete (planner scope for knip-clean):**
- `frontend/src/components/charts/EndgameMetricsSection.tsx`
- `frontend/src/components/charts/EndgameMetricCard.tsx`
- `frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx` (if exists)
- `frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx` (if exists)

---

## Pattern Assignments

### `app/schemas/endgames.py` — new `PerTcBucketStats`, `EndgameMetricsTcCard`, `EndgameMetricsCardsResponse`; add `endgame_metrics_cards` to `EndgameOverviewResponse`

**Analog:** `app/schemas/endgames.py` lines 858-957

**Existing `TimePressureTcCard` / `TimePressureCardsResponse` / `EndgameOverviewResponse` pattern** (lines 858-957):
```python
class TimePressureTcCard(BaseModel):
    """Per-time-control time pressure card..."""
    tc: Literal["bullet", "blitz", "rapid", "classical"]
    total: int
    # ... metric fields with explicit | None = None defaults for B-2 lock
    time_pressure_score_gap_percentile: float | None = None
    clock_gap_percentile: float | None = None
    net_flag_rate_percentile: float | None = None

class TimePressureCardsResponse(BaseModel):
    """... cards: list of TimePressureTcCard, ordered bullet -> blitz -> rapid -> classical."""
    cards: list[TimePressureTcCard]

class EndgameOverviewResponse(BaseModel):
    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    score_gap_material: ScoreGapMaterialResponse
    time_pressure_cards: TimePressureCardsResponse
    clock_diff_timeline: ClockDiffTimelineResponse
    endgame_elo_timeline: EndgameEloTimelineResponse
    rating_anchors: dict[TimeControlBucket, RatingAnchorOut] = Field(default_factory=dict)
```

**New schemas to add (copy this exact shape):**
```python
class PerTcBucketStats(BaseModel):
    """Per-bucket (conv/parity/recov) stats for one TC metric block."""
    games: int
    win_pct: float    # percent 0-100, not fraction
    draw_pct: float
    loss_pct: float
    rate: float | None          # conversion win%, parity score%, recovery save%
    score_gap_mean: float | None
    score_gap_n: int | None
    score_gap_p_value: float | None
    score_gap_ci_low: float | None
    score_gap_ci_high: float | None
    percentile: float | None    # per-TC DeltaES-gap percentile

class EndgameMetricsTcCard(BaseModel):
    """Per-TC card: Conv/Parity/Recovery trifecta for one time control."""
    tc: Literal["bullet", "blitz", "rapid", "classical"]
    total: int
    conversion: PerTcBucketStats
    parity: PerTcBucketStats
    recovery: PerTcBucketStats

class EndgameMetricsCardsResponse(BaseModel):
    cards: list[EndgameMetricsTcCard]  # pre-filtered, fixed order
```

Add to `EndgameOverviewResponse` (lines 931-957), following the `rating_anchors` default-factory pattern:
```python
endgame_metrics_cards: EndgameMetricsCardsResponse = Field(
    default_factory=lambda: EndgameMetricsCardsResponse(cards=[])
)
```

**Key conventions to copy:**
- Explicit `| None = None` defaults on optional fields to preserve B-2 lock (existing test fixtures construct models keyword-style).
- `Literal["bullet", "blitz", "rapid", "classical"]` for tc field — not a bare `str`.
- `Field(default_factory=...)` for the new top-level field on `EndgameOverviewResponse`.

---

### `app/services/endgame_zones.py` — new `TcConvRecovBands` dataclass and `TC_METRIC_BANDS` registry

**Analog:** `app/services/endgame_zones.py` lines 445-508 (`PerClassBands` + `PER_CLASS_GAUGE_ZONES`) and lines 526-590 (`PressureBinBand` + `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`)

**`PerClassBands` dataclass pattern** (lines 445-451):
```python
@dataclass(frozen=True)
class PerClassBands:
    """Typical [lower, upper] bands for Conversion, Recovery, and Score Gap for one endgame type."""
    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]
```

**`PressureBinBand` dataclass pattern** (lines 526-531):
```python
@dataclass(frozen=True)
class PressureBinBand:
    """Neutral [lower, upper] band for Score-Delta in one (TC, quintile) cell."""
    lower: float
    upper: float
```

**`PRESSURE_BIN_SCORE_NEUTRAL_ZONES` TC-keyed Mapping pattern** (lines 538-542):
```python
PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Mapping[
    Literal["bullet", "blitz", "rapid", "classical"],
    Mapping[Literal[0, 1, 2, 3, 4], PressureBinBand],
] = {
    "bullet": { 0: PressureBinBand(...), 1: PressureBinBand(...), ... },
    ...
}
```

**New `TcConvRecovBands` + `TC_METRIC_BANDS` to add (model directly on both analogs):**
```python
@dataclass(frozen=True)
class TcConvRecovBands:
    """Per-TC typical [lower, upper] bands for Conv/Recov rate and DeltaES gap."""
    conv_rate: tuple[float, float]
    recov_rate: tuple[float, float]
    conv_score_gap: tuple[float, float]
    recov_score_gap: tuple[float, float]

TC_METRIC_BANDS: Mapping[Literal["bullet", "blitz", "rapid", "classical"], TcConvRecovBands] = {
    "bullet":    TcConvRecovBands(
        conv_rate=(0.588, 0.719),
        recov_rate=(0.295, 0.412),
        conv_score_gap=(-0.195, -0.057),
        recov_score_gap=(0.074, 0.177),
    ),
    "blitz":     TcConvRecovBands(
        conv_rate=(0.667, 0.769),
        recov_rate=(0.251, 0.357),
        conv_score_gap=(-0.085, 0.003),
        recov_score_gap=(0.011, 0.084),
    ),
    "rapid":     TcConvRecovBands(
        conv_rate=(0.696, 0.800),
        recov_rate=(0.218, 0.333),
        conv_score_gap=(-0.063, 0.021),
        recov_score_gap=(-0.008, 0.062),
    ),
    "classical": TcConvRecovBands(
        conv_rate=(0.685, 0.833),
        recov_rate=(0.174, 0.316),
        conv_score_gap=(-0.053, 0.038),
        recov_score_gap=(-0.037, 0.035),
    ),
}
```

**Key conventions:**
- `@dataclass(frozen=True)` — all zone dataclasses are frozen.
- `Mapping[..., ...]` return type (not `dict`) — matches every existing registry in the file.
- Import `Mapping` from `collections.abc` (already at top of file, line 14).
- Place `TC_METRIC_BANDS` after `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (line 590) — keeps TC-keyed registries grouped.
- `BUCKETED_ZONE_REGISTRY` stays untouched — parity uses it for LLM insights; only the TS codegen side is being updated.

---

### `app/services/endgame_service.py` — new `_MetricTcAccumulator` dataclass + `_compute_per_tc_metric_cards`; remove `_aggregate_per_tc_percentile`

**Analog:** `app/services/endgame_service.py`

**`_ClockAggregate` dataclass pattern** (lines 1643-1679) — `slots=True`, all summable fields, no constructor:
```python
@dataclass(slots=True)
class _ClockAggregate:
    """Plan 88-14 A-3: per-TC accumulator..."""
    user_clock_sum_pct: float = 0.0
    user_clock_sum_seconds: float = 0.0
    ...
    clock_games: int = 0
    total_games: int = 0
```

**`_TIME_CONTROL_ORDER` constant** (line 1640):
```python
_TIME_CONTROL_ORDER: list[str] = ["bullet", "blitz", "rapid", "classical"]
```

**`_compute_time_pressure_cards` function signature and body pattern** (lines 2088-2209):
```python
def _compute_time_pressure_cards(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
    *,
    percentile_rows: Mapping[CdfMetricId, Mapping[TimeControlBucket, PercentileRow]] | None = None,
) -> TimePressureCardsResponse:
    """..."""
    # 1. Single-pass iteration into per-TC accumulators
    # 2. Empty-mapping guard for percentile_rows:
    _effective_rows: Mapping[...] = (percentile_rows if percentile_rows is not None else {})
    # 3. Loop over _TIME_CONTROL_ORDER, gate on MIN_GAMES_PER_TC_CARD:
    cards: list[TimePressureTcCard] = []
    for tc in _TIME_CONTROL_ORDER:
        total = tc_total.get(tc, 0)
        if total < MIN_GAMES_PER_TC_CARD:
            continue
        # 4. Per-TC percentile lookup bypassing _aggregate_per_tc_percentile:
        tc_literal = cast(Literal["bullet", "blitz", "rapid", "classical"], tc)
        tc_bucket: TimeControlBucket = tc_literal
        conv_row = _effective_rows.get("score_gap_conv", {}).get(tc_bucket)
        parity_row = _effective_rows.get("score_gap_parity", {}).get(tc_bucket)
        recov_row = _effective_rows.get("recovery_score_gap", {}).get(tc_bucket)
        # 5. Build and append card:
        cards.append(TimePressureTcCard(...))
    return TimePressureCardsResponse(cards=cards)
```

**`_aggregate_per_tc_percentile` to remove** (lines 1269-1319):
```python
def _aggregate_per_tc_percentile(
    per_tc_rows: Mapping[TimeControlBucket, PercentileRow] | None,
) -> float | None:
    """Game-count-weighted mean across per-TC percentiles for a single metric.
    ...
    """
```
Remove function + all 5 call sites (lines 1529, 1533, 1536, 1545, 2596).

**`_compute_per_bucket_score_gap` reuse pattern** (lines 1237-1260) — call for per-TC DeltaES gaps:
```python
def _compute_per_bucket_score_gap(
    gaps_by_bucket: dict[str, list[float]],
) -> dict[MaterialBucket, tuple[float | None, int, float | None, float | None, float | None]]:
    """..."""
    for bucket in ("conversion", "parity", "recovery"):
        gaps = gaps_by_bucket.get(b, [])
        n = len(gaps)
        mean_raw, p_val, ci_lo, ci_hi = compute_paired_difference_test(gaps)
        mean_out: float | None = mean_raw if n > 0 else None
        result[b] = (mean_out, n, p_val, ci_lo, ci_hi)
```

**`_aggregate_bucket_counts` WDL accumulator pattern** (lines 1106-1175) — per-bucket W/D/L tally with priority ordering (conversion > recovery > parity). The new accumulator mirrors this logic per-TC.

**Where to thread `_compute_per_tc_metric_cards` into `get_endgame_overview`** (lines 3227-3236):
```python
return EndgameOverviewResponse(
    stats=stats,
    performance=performance,
    timeline=timeline,
    score_gap_material=score_gap_material,
    time_pressure_cards=time_pressure_cards,
    clock_diff_timeline=clock_diff_timeline,
    endgame_elo_timeline=endgame_elo_timeline,
    rating_anchors=rating_anchors,
    # ADD:
    endgame_metrics_cards=endgame_metrics_cards,
)
```

**New imports to add** (follow existing import pattern at lines 42-70):
```python
from app.schemas.endgames import (
    ...
    EndgameMetricsCardsResponse,
    EndgameMetricsTcCard,
    PerTcBucketStats,
)
from app.services.endgame_zones import (
    ...
    TC_METRIC_BANDS,
)
```

---

### `app/repositories/endgame_repository.py` — extend `query_endgame_bucket_rows` to project `time_control_bucket` and LEAD eval columns

**Analog:** `app/repositories/endgame_repository.py` lines 144-286 (`query_endgame_entry_rows` — the proven LEAD pattern)

**Current `query_endgame_bucket_rows` SELECT** (lines 360-371):
```python
stmt = (
    select(
        Game.id.label("game_id"),
        span_subq.c.endgame_class,
        Game.result,
        Game.user_color,
        span_subq.c.entry_eval_cp.label("eval_cp"),
        span_subq.c.entry_eval_mate.label("eval_mate"),
        # CURRENTLY STOPS HERE at column index 5
    )
    .join(span_subq, Game.id == span_subq.c.game_id)
    .where(Game.user_id == user_id)
)
```

**LEAD window pattern from `query_endgame_entry_rows`** (lines 226-244):
```python
span_with_next = select(
    span_subq.c.game_id,
    span_subq.c.endgame_class,
    span_subq.c.entry_eval_cp,
    span_subq.c.entry_eval_mate,
    span_subq.c.span_min_ply,
    func.lead(span_subq.c.entry_eval_cp)
    .over(
        partition_by=span_subq.c.game_id,
        order_by=span_subq.c.span_min_ply.asc(),
    )
    .label("next_entry_eval_cp"),
    func.lead(span_subq.c.entry_eval_mate)
    .over(
        partition_by=span_subq.c.game_id,
        order_by=span_subq.c.span_min_ply.asc(),
    )
    .label("next_entry_eval_mate"),
).subquery("span_with_next")
```

**`array_agg` pattern for entry eval** (lines 326-339 in `query_endgame_bucket_rows`):
```python
entry_eval_cp_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.eval_cp, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)[1]
```

**Extension to add to `query_endgame_bucket_rows`:**
1. Add `Game.time_control_bucket` at column index 6 in the SELECT.
2. Add next-eval LEAD columns for span gaps at indices 7-8 (mirroring `query_endgame_entry_rows`).
3. Update the docstring row-shape comment (`Returns rows of:`) to include the new columns.
4. The subquery's `span_subq` already computes `entry_eval_cp_agg` + `entry_eval_mate_agg`; for LEAD, wrap with a second subquery like `query_endgame_entry_rows` does.

**Key conventions:**
- `eval_cp` and `eval_mate` projected raw (white-perspective, no SQL color flip) — service layer applies flip via `_classify_endgame_bucket`.
- `apply_game_filters` call at end of function stays unchanged.
- Return type `list[Row[Any]]` — no change.

---

### `scripts/gen_endgame_zones_ts.py` — add `_format_tc_metric_bands()` and emit `TC_METRIC_BANDS`

**Analog:** `scripts/gen_endgame_zones_ts.py` lines 97-128

**`_format_per_class_gauge_zones` pattern** (lines 97-113):
```python
def _format_per_class_gauge_zones() -> str:
    """Emit the PER_CLASS_GAUGE_ZONES object literal."""
    lines: list[str] = []
    for cls, bands in PER_CLASS_GAUGE_ZONES.items():
        c_lo, c_hi = bands.conversion
        r_lo, r_hi = bands.recovery
        g_lo, g_hi = bands.achievable_score_gap
        lines.append(
            f"  {cls}: {{ conversion: [{c_lo}, {c_hi}], recovery: [{r_lo}, {r_hi}],"
            f" achievable_score_gap: [{g_lo}, {g_hi}] }},"
        )
    return "\n".join(lines) + "\n"
```

**`_format_pressure_bin_zones` pattern** (lines 116-128):
```python
def _format_pressure_bin_zones() -> str:
    """Emit PRESSURE_BIN_SCORE_NEUTRAL_ZONES as a nested TS Record literal."""
    lines: list[str] = []
    for tc, quintile_map in PRESSURE_BIN_SCORE_NEUTRAL_ZONES.items():
        q_entries = ", ".join(
            f"{q}: {{ min: {band.lower}, max: {band.upper} }}" for q, band in quintile_map.items()
        )
        lines.append(f"  {tc}: {{ {q_entries} }},")
    return "\n".join(lines) + "\n"
```

**Import to add** (lines 30-39):
```python
from app.services.endgame_zones import (
    ...
    TC_METRIC_BANDS,   # Phase 97: new TC-keyed conv/recov bands
)
```

**New `_format_tc_metric_bands()` function to add (model on both analogs):**
```python
def _format_tc_metric_bands() -> str:
    """Emit TC_METRIC_BANDS as a nested TS Record literal (Phase 97)."""
    lines: list[str] = []
    for tc, bands in TC_METRIC_BANDS.items():
        cr_lo, cr_hi = bands.conv_rate
        rr_lo, rr_hi = bands.recov_rate
        cg_lo, cg_hi = bands.conv_score_gap
        rg_lo, rg_hi = bands.recov_score_gap
        lines.append(
            f"  {tc}: {{ convRate: [{cr_lo}, {cr_hi}], recovRate: [{rr_lo}, {rr_hi}],"
            f" convScoreGap: [{cg_lo}, {cg_hi}], recovScoreGap: [{rg_lo}, {rg_hi}] }},"
        )
    return "\n".join(lines) + "\n"
```

**Emission in `_render()`** (append to the string return in `_render()`, after the existing `CLOCK_GAP_NEUTRAL_*` block at lines 240-243):
```python
"// Phase 97: per-TC gauge + DeltaES bullet bands for Conversion and Recovery.\n"
"// Source: reports/benchmark/benchmarks-latest.md §3.2.1 (rates) and §3.2.2 (DeltaES gaps).\n"
"export const TC_METRIC_BANDS: Record<\n"
"  'bullet' | 'blitz' | 'rapid' | 'classical',\n"
"  { convRate: [number, number]; recovRate: [number, number]; convScoreGap: [number, number]; recovScoreGap: [number, number] }\n"
"> = {\n"
+ _format_tc_metric_bands()
+ "} as const;\n"
```

**knip cleanup note:** After deletion of `EndgameMetricCard`, check whether `SCORE_GAP_CONV_NEUTRAL_MIN/MAX`, `SCORE_GAP_RECOV_NEUTRAL_MIN/MAX` exports become dead. If so, remove them from the `_render()` string and their corresponding `_SCORE_GAP_CONV_SPEC` / `_SCORE_GAP_RECOV_SPEC` variables in the script header. `SCORE_GAP_PARITY_NEUTRAL_MIN/MAX` and `FIXED_GAUGE_ZONES.parity` remain alive (parity gauge uses the global band in the new section).

---

### `frontend/src/generated/endgameZones.ts` (regenerated)

No direct edits — regenerated by `uv run python scripts/gen_endgame_zones_ts.py`. The new `TC_METRIC_BANDS` export will appear at the end of the file.

**New TS export shape (verbatim from codegen):**
```typescript
export const TC_METRIC_BANDS: Record<
  'bullet' | 'blitz' | 'rapid' | 'classical',
  { convRate: [number, number]; recovRate: [number, number]; convScoreGap: [number, number]; recovScoreGap: [number, number] }
> = {
  bullet:    { convRate: [0.588, 0.719], recovRate: [0.295, 0.412], convScoreGap: [-0.195, -0.057], recovScoreGap: [0.074, 0.177] },
  blitz:     { convRate: [0.667, 0.769], recovRate: [0.251, 0.357], convScoreGap: [-0.085, 0.003],  recovScoreGap: [0.011, 0.084] },
  rapid:     { convRate: [0.696, 0.800], recovRate: [0.218, 0.333], convScoreGap: [-0.063, 0.021],  recovScoreGap: [-0.008, 0.062] },
  classical: { convRate: [0.685, 0.833], recovRate: [0.174, 0.316], convScoreGap: [-0.053, 0.038],  recovScoreGap: [-0.037, 0.035] },
} as const;
```

**Drift check:** `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` — already in CI, no new gate needed.

---

### `frontend/src/components/charts/EndgameMetricsByTcSection.tsx` (new)

**Analog:** `frontend/src/components/charts/EndgameTimePressureSection.tsx` (93 lines — full file is the template)

**Full analog** (lines 1-93):
```tsx
import { EndgameTimePressureCard } from '@/components/charts/EndgameTimePressureCard';
import type { RatingAnchorsByTc } from '@/lib/percentileAnchor';
import type { TimePressureCardsResponse } from '@/types/endgames';

const GRID_ONE_CARD = 'w-full md:w-1/2 mt-2';
const GRID_TWO_CARDS = 'grid grid-cols-1 md:grid-cols-2 gap-4 mt-2';
const GRID_THREE_CARDS = 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mt-2';
const GRID_FOUR_CARDS = 'grid grid-cols-1 lg:grid-cols-2 gap-4 mt-2';

export function EndgameTimePressureSection({
  data,
  ratingAnchors,
}: {
  data: TimePressureCardsResponse;
  ratingAnchors?: RatingAnchorsByTc;
}) {
  const anchors = ratingAnchors ?? {};
  return (
    <section data-testid="time-pressure-cards-section" aria-label="Time pressure analysis">
      <p className="text-sm text-muted-foreground">
        How does your score change under time pressure?
      </p>
      {data.cards.length === 0 ? (
        <div className="mt-2 text-sm text-muted-foreground" data-testid="time-pressure-cards-empty">
          No time-pressure data yet. Import more games to see this section.
        </div>
      ) : (
        (() => {
          const visibleCount = data.cards.length;
          const grandTotal = data.cards.reduce((acc, c) => acc + c.total, 0);
          const gridClass =
            visibleCount === 1 ? GRID_ONE_CARD
            : visibleCount === 2 ? GRID_TWO_CARDS
            : visibleCount === 3 ? GRID_THREE_CARDS
            : GRID_FOUR_CARDS;
          return (
            <div className={gridClass}>
              {data.cards.map((card) => (
                <EndgameTimePressureCard key={card.tc} card={card} grandTotal={grandTotal} ratingAnchor={anchors[card.tc]} />
              ))}
            </div>
          );
        })()
      )}
    </section>
  );
}
```

**Adaptations for `EndgameMetricsByTcSection.tsx`:**
- Replace `TimePressureCardsResponse` with `EndgameMetricsCardsResponse`.
- Replace `EndgameTimePressureCard` with `EndgameMetricsByTcCard`.
- `data-testid`: `"endgame-metrics-tc-section"`.
- `aria-label`: `"Endgame metrics by time control"`.
- Section subtitle: `"How do you score from winning, balanced, and losing endgames, by time control?"`.
- Empty state `data-testid`: `"endgame-metrics-tc-section-empty"`.
- Empty state text: `"No endgame data yet. Import more games to see this section."`.
- Grid layout: D-02 requires **full-width vertical stacking** (one TC per row). Use `'w-full mt-2'` for all card counts — do NOT use the staircase grid from `EndgameTimePressureSection`. All four GRID_* constants collapse to the same value for this section.
- `grandTotal` prop: pass to `EndgameMetricsByTcCard` for the share-percentage display (same as Time Pressure analog).
- No `ratingAnchors` prop needed — per-TC percentile chips on this section use `tc` + `percentile` directly from the card data; there are no anchor-gated chips (D-11: badge pairs with DeltaES bullet, no anchor disclosure required here).

---

### `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` (new)

**Primary analog:** `frontend/src/components/charts/EndgameMetricCard.tsx` (298 lines — metric block anatomy)
**Secondary analog:** `frontend/src/components/charts/EndgameTimePressureCard.tsx` lines 1-46 (TC header + testid patterns)

**TC header + testid pattern from `EndgameTimePressureCard.tsx`** (lines 41-46):
```tsx
const TC_LABELS: Record<'bullet' | 'blitz' | 'rapid' | 'classical', string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classical',
};
// testid pattern: data-testid={`time-pressure-card-${card.tc}-...`}
```

**Metric block anatomy from `EndgameMetricCard.tsx`** (lines 93-298):

Imports pattern (lines 13-44):
```tsx
import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import { BUCKET_DISPLAY_LABELS, BUCKET_DISPLAY_LABELS_WITH_METRIC, SCORE_GAP_BUCKET_DISPLAY_SHIFT } from '@/lib/endgameMetrics';
// REPLACE per-bucket neutral min/max with TC_METRIC_BANDS:
import { TC_METRIC_BANDS, FIXED_GAUGE_ZONES } from '@/generated/endgameZones';
import type { MaterialBucket } from '@/types/endgames';
import { PercentileChip } from './PercentileChip';
import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import { deriveLevel } from './EndgameOverallShared';
```

Rate computation per bucket (lines 109-113):
```tsx
const userR = bucket === 'conversion'
  ? row.win_pct / 100
  : bucket === 'recovery'
    ? (row.win_pct + row.draw_pct) / 100
    : row.score;
```

Gauge zone construction — **new pattern for TC-specific bands** (copy from RESEARCH.md §D-08):
```tsx
// In EndgameMetricsByTcCard.tsx, for each metric block:
const bands = TC_METRIC_BANDS[card.tc];  // noUncheckedIndexedAccess: always defined since card.tc is the known Literal union
const convGaugeZones = colorizeGaugeZones([
  { from: 0, to: bands.convRate[0] },
  { from: bands.convRate[0], to: bands.convRate[1] },
  { from: bands.convRate[1], to: 1.0 },
]);
const recovGaugeZones = colorizeGaugeZones([
  { from: 0, to: bands.recovRate[0] },
  { from: bands.recovRate[0], to: bands.recovRate[1] },
  { from: bands.recovRate[1], to: 1.0 },
]);
const parityGaugeZones = colorizeGaugeZones(FIXED_GAUGE_ZONES.parity); // global, unchanged
```

DeltaES display shift — **TC-specific** (RESEARCH.md §Pitfall 3):
```tsx
// Replace the file-level SCORE_GAP_BUCKET_DISPLAY_SHIFT constant with per-TC computation:
const convShift = -(bands.convScoreGap[0] + bands.convScoreGap[1]) / 2;
const recovShift = -(bands.recovScoreGap[0] + bands.recovScoreGap[1]) / 2;
// Parity shift stays 0 (global symmetric band: (-0.04, +0.04))
const parityShift = 0;
```

Neutral band per bucket (replace static imports with TC-keyed lookup):
```tsx
// Conversion: [bands.convScoreGap[0], bands.convScoreGap[1]]
// Parity:     [SCORE_GAP_PARITY_NEUTRAL_MIN, SCORE_GAP_PARITY_NEUTRAL_MAX] (global)
// Recovery:   [bands.recovScoreGap[0], bands.recovScoreGap[1]]
```

PercentileChip flavor dispatch (lines 246-254 in `EndgameMetricCard.tsx`):
```tsx
// Existing flavor literals to reuse:
flavor={
  bucket === 'conversion' ? 'conversion'
  : bucket === 'parity'   ? 'parity'
  : 'recovery'
}
// New: pass tc prop directly from card.tc; no per-TC breakdown list needed
// (chips read per-TC percentile directly from PerTcBucketStats.percentile)
```

Card shell and testid conventions (lines 171-172 in `EndgameMetricCard.tsx`):
```tsx
<div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
  <h3 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
```

**New outer card structure for `EndgameMetricsByTcCard.tsx`:**
```tsx
<div
  className="charcoal-texture rounded-md p-4"
  data-testid={`metrics-tc-card-${card.tc}`}
>
  {/* TC header: icon + label + total */}
  <div className="flex items-center gap-2 mb-3">
    <TimeControlIcon tc={card.tc} />
    <h3 className="text-base font-semibold">{TC_LABELS[card.tc]}</h3>
    <span className="text-sm text-muted-foreground ml-auto">
      {card.total.toLocaleString()} games
    </span>
  </div>
  {/* 3-column metric row (D-03): side-by-side desktop, stacked mobile */}
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
    {/* Conversion block — data-testid="metrics-tc-{card.tc}-conversion" */}
    {/* Parity block    — data-testid="metrics-tc-{card.tc}-parity"     */}
    {/* Recovery block  — data-testid="metrics-tc-{card.tc}-recovery"   */}
  </div>
</div>
```

**Key conventions to preserve from `EndgameMetricCard.tsx`:**
- `hasGames` guard for `opacity-50` on gauge when `row.games === 0` (line 114, 184).
- `showGapRow = gapN > 0` gate before rendering `ScoreGapRow` (line 120).
- `gapColor` uses RAW (unshifted) values for zone tinting (lines 157-164).
- `POPOVER_COPY` per bucket — carry forward the existing copy, update recovery copy per the folded todo `2026-05-17-recovery-score-gap-popover-copy.md` (opponent-first framing).
- `data-testid` on every interactive element: `metrics-tc-{tc}-{bucket}`, `metrics-tc-{tc}-{bucket}-score-gap-bullet`, `metrics-tc-{tc}-{bucket}-score-gap-value`, `metrics-tc-{tc}-{bucket}-score-gap-info`, `metrics-tc-{tc}-{bucket}-percentile-chip`.

---

### `frontend/src/types/endgames.ts` — add `PerTcBucketStats`, `EndgameMetricsTcCard`, `EndgameMetricsCardsResponse`; add `endgame_metrics_cards` to `EndgameOverviewResponse`

**Analog:** `frontend/src/types/endgames.ts` lines 296-343 (`TimePressureTcCard` / `TimePressureCardsResponse`) and lines 426-440 (`EndgameOverviewResponse`)

**`TimePressureTcCard` interface pattern** (lines 296-338):
```typescript
export interface TimePressureTcCard {
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
  total: number;
  // optional fields with ? for B-2 back-compat
  time_pressure_score_gap_percentile?: number | null;
  clock_gap_percentile?: number | null;
  net_flag_rate_percentile?: number | null;
  ...
}
export interface TimePressureCardsResponse {
  cards: TimePressureTcCard[];
}
```

**`EndgameOverviewResponse` interface** (lines 426-440) — add new field:
```typescript
export interface EndgameOverviewResponse {
  stats: EndgameStatsResponse;
  performance: EndgamePerformanceResponse;
  timeline: EndgameTimelineResponse;
  score_gap_material: ScoreGapMaterialResponse;
  time_pressure_cards: TimePressureCardsResponse;
  clock_diff_timeline: ClockDiffTimelineResponse;
  endgame_elo_timeline: EndgameEloTimelineResponse;
  rating_anchors: Partial<Record<'bullet' | 'blitz' | 'rapid' | 'classical', RatingAnchorOut>>;
  // ADD:
  endgame_metrics_cards?: EndgameMetricsCardsResponse;  // optional for back-compat with older fixtures
}
```

**New interfaces to add:**
```typescript
export interface PerTcBucketStats {
  games: number;
  win_pct: number;    // percent 0-100
  draw_pct: number;
  loss_pct: number;
  rate: number | null;           // conversion win%, parity score%, recovery save%
  score_gap_mean: number | null;
  score_gap_n: number | null;
  score_gap_p_value: number | null;
  score_gap_ci_low: number | null;
  score_gap_ci_high: number | null;
  percentile: number | null;     // per-TC DeltaES-gap percentile
}

export interface EndgameMetricsTcCard {
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
  total: number;
  conversion: PerTcBucketStats;
  parity: PerTcBucketStats;
  recovery: PerTcBucketStats;
}

export interface EndgameMetricsCardsResponse {
  cards: EndgameMetricsTcCard[];
}
```

---

### `frontend/src/pages/Endgames.tsx` — swap `EndgameMetricsSection` for `EndgameMetricsByTcSection`

**Analog:** `frontend/src/pages/Endgames.tsx` line 585 (current `EndgameMetricsSection` usage)

Change:
```tsx
// BEFORE (line ~585):
import { EndgameMetricsSection } from '@/components/charts/EndgameMetricsSection';
// ...
<EndgameMetricsSection data={overview.score_gap_material} />

// AFTER:
import { EndgameMetricsByTcSection } from '@/components/charts/EndgameMetricsByTcSection';
// ...
<EndgameMetricsByTcSection data={overview.endgame_metrics_cards ?? { cards: [] }} />
```

The `?? { cards: [] }` fallback handles older server responses where `endgame_metrics_cards` is absent.

---

## Shared Patterns

### Authentication / V4 Access Control
**Source:** `app/services/endgame_service.py` lines 3050-3068 (orchestrator pattern)
**Apply to:** `_compute_per_tc_metric_cards` — receives `bucket_rows` already fetched with the authenticated `user_id` (never sourced from a query param). The new function takes pre-scoped row data as an argument, not a session or user_id directly.

### Sentry capture
**Source:** `CLAUDE.md` Sentry rules
**Apply to:** Any new `except` block in `endgame_service.py`. The new `_compute_per_tc_metric_cards` is a pure computation function (no I/O) — no `try/except` needed unless calling `compute_paired_difference_test` (which doesn't raise). No Sentry call required in the new function itself.

### Sequential DB access (no asyncio.gather)
**Source:** `CLAUDE.md` critical constraint
**Apply to:** `get_endgame_overview` orchestrator — the new `_compute_per_tc_metric_cards` call is a pure Python computation over already-fetched `bucket_rows`, not an additional DB query. No gather risk.

### `noUncheckedIndexedAccess` narrowing
**Source:** `CLAUDE.md` frontend rule + RESEARCH.md §Pitfall 5
**Apply to:** `TC_METRIC_BANDS[card.tc]` access in `EndgameMetricsByTcCard.tsx`. Since `card.tc` is `Literal["bullet" | "blitz" | "rapid" | "classical"]` and the Record has all four keys, use `const bands = TC_METRIC_BANDS[card.tc]` with a non-null assertion (`!`) or narrowing check — the key is provably in bounds.

### data-testid convention
**Source:** `CLAUDE.md` browser automation rules
**Apply to:** All new frontend components.
- Section: `data-testid="endgame-metrics-tc-section"`, empty state: `data-testid="endgame-metrics-tc-section-empty"`.
- Cards: `data-testid="metrics-tc-card-{tc}"` (e.g. `metrics-tc-card-bullet`).
- Metric blocks: `data-testid="metrics-tc-{tc}-{bucket}"` (e.g. `metrics-tc-bullet-conversion`).
- Sub-elements: `metrics-tc-{tc}-{bucket}-score-gap-bullet`, `metrics-tc-{tc}-{bucket}-score-gap-value`, `metrics-tc-{tc}-{bucket}-score-gap-info`, `metrics-tc-{tc}-{bucket}-percentile-chip`.

### Theme constants
**Source:** `CLAUDE.md` + `frontend/src/lib/theme.ts`
**Apply to:** `colorizeGaugeZones` in `EndgameMetricsByTcCard.tsx` — import from `@/lib/theme`, same as `EndgameMetricCard.tsx` line 14-17. `ZONE_DANGER` and `ZONE_SUCCESS` for zone tinting.

### Mobile parity
**Source:** `CLAUDE.md` frontend rules
**Apply to:** `EndgameMetricsByTcCard.tsx` inner metric grid: `grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4` (same staircase as the existing `EndgameMetricsSection.tsx` line 102) — metric blocks stack on mobile, side-by-side on desktop.

---

## Removal Scope (planner: include as explicit delete tasks)

### Backend removals
1. `_aggregate_per_tc_percentile` function (`endgame_service.py` lines 1269-1319) + 5 call sites at lines 1529, 1533, 1536-1545, 2596.
2. Fields on `ScoreGapMaterialResponse` (`app/schemas/endgames.py`): `score_gap_conv_percentile` (line 552), `score_gap_parity_percentile` (line 570), `recovery_score_gap_percentile` (line 596).
3. Also check: `score_gap_conv_per_tc`, `score_gap_parity_per_tc`, `recovery_score_gap_per_tc` list fields (lines 560, 578, 604) — these are chip tooltip bullet-2 data for the blended chips. Verify whether `EndgameOverallScoreGapRow` / `EndgameOverallPerformanceSection` still reference them before removing (RESEARCH.md Open Question 1 / Assumption A2). If they appear only in the deleted `EndgameMetricsSection`, remove them; if consumed by Overall Performance chip tooltips, keep them.
4. Also check: `score_gap_percentile` on `EndgamePerformanceResponse` — verify whether it feeds the Overall Performance section or only the deleted Metrics section (RESEARCH.md Assumption A1).

### Frontend removals
1. `frontend/src/components/charts/EndgameMetricsSection.tsx` — delete file.
2. `frontend/src/components/charts/EndgameMetricCard.tsx` — delete file (behavior absorbed into `EndgameMetricsByTcCard.tsx`).
3. Test files for the above if they exist (search pattern: `__tests__/EndgameMetricsSection.test.tsx`, `__tests__/EndgameMetricCard.test.tsx`).
4. Update `frontend/src/types/endgames.ts` `EndgameOverviewResponse` + `ScoreGapMaterialResponse` to remove the dropped fields.
5. After deletion, run `npm run knip` to surface dead exports in `endgameZones.ts` (specifically `SCORE_GAP_CONV_NEUTRAL_MIN/MAX`, `SCORE_GAP_RECOV_NEUTRAL_MIN/MAX` if no other consumer).
6. Remove the `FIXED_GAUGE_ZONES` import from `endgameMetrics.ts` if `EndgameMetricCard.tsx` was its only consumer.

---

## No Analog Found

All files have strong analogs in the codebase. No new patterns are needed.

---

## Metadata

**Analog search scope:** `app/services/`, `app/schemas/`, `app/repositories/`, `scripts/`, `frontend/src/components/charts/`, `frontend/src/types/`, `frontend/src/generated/`
**Files scanned:** 12 source files read directly
**Pattern extraction date:** 2026-05-29

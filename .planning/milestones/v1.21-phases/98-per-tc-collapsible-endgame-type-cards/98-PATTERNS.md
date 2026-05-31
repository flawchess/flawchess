# Phase 98: Per-TC Collapsible Endgame Type Cards - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/primaryTc.ts` | utility | transform | `frontend/src/lib/scoreBulletConfig.ts` | role-match |
| `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` | component | request-response | `frontend/src/components/charts/EndgameTimePressureSection.tsx` | exact |
| `frontend/src/components/charts/EndgameTypeCard.tsx` | component | request-response | `git show d3453597^:frontend/src/components/charts/EndgameTypeCard.tsx` | exact (restore) |
| `frontend/src/components/charts/EndgameTypeTcCard.tsx` (new) | component | request-response | `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` | exact |
| `frontend/src/types/endgames.ts` | type | transform | self (additive extension) | exact |
| `frontend/src/generated/endgameZones.ts` | config | transform | self (regenerated) | exact |
| `app/services/endgame_zones.py` | service | transform | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` / `PER_CLASS_GAUGE_ZONES` patterns within same file | exact |
| `scripts/gen_endgame_zones_ts.py` | utility | transform | `_format_tc_metric_bands()` within same file | exact |
| `app/services/endgame_service.py` | service | CRUD | `_compute_per_tc_metric_cards()` within same file | exact |
| `app/schemas/endgames.py` | model | CRUD | `EndgameStatsResponse` within same file | exact |

---

## Pattern Assignments

### `frontend/src/lib/primaryTc.ts` (new utility, transform)

**Analog:** `frontend/src/lib/scoreBulletConfig.ts`

This file uses the same idiom: named constants at the top, then one or two pure exported functions that consume them. No React, no imports beyond TS builtins.

**Imports / constants pattern** (scoreBulletConfig.ts lines 1-16):
```typescript
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

export const SCORE_BULLET_CENTER = 0.5;
export const SCORE_BULLET_NEUTRAL_MIN = -0.05;
export const SCORE_BULLET_NEUTRAL_MAX = 0.05;
```

**Pattern to replicate:** named `NOMINAL_DURATION` Record constant + `computePrimaryTc` pure function. No default export, only named exports. From RESEARCH.md §Code Examples:

```typescript
// frontend/src/lib/primaryTc.ts
// Accessible to both EndgameTypeBreakdownSection and future ELO Timeline (D-11).

const NOMINAL_DURATION: Record<'bullet' | 'blitz' | 'rapid' | 'classical', number> = {
  bullet: 60,
  blitz: 180,
  rapid: 600,
  classical: 900,
};

export function computePrimaryTc(
  categoriesByTc: Record<string, { total: number }[]>,
  minGames: number,
): 'bullet' | 'blitz' | 'rapid' | 'classical' | null {
  const TC_ORDER = ['bullet', 'blitz', 'rapid', 'classical'] as const;
  let bestTc: (typeof TC_ORDER)[number] | null = null;
  let bestScore = -1;
  for (const tc of TC_ORDER) {
    const tcTotal = (categoriesByTc[tc] ?? []).reduce((s, c) => s + c.total, 0);
    if (tcTotal < minGames) continue;
    const score = tcTotal * NOMINAL_DURATION[tc];
    if (score > bestScore) {
      bestScore = score;
      bestTc = tc;
    }
  }
  return bestTc;
}
```

**Test file to create:** `frontend/src/lib/__tests__/primaryTc.test.ts` — follow the pattern of `frontend/src/lib/scoreBulletConfig.ts` or `frontend/src/lib/significance.ts` (pure-function test, no mocks needed).

---

### `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` (modified component, request-response)

**Analog:** `frontend/src/components/charts/EndgameTimePressureSection.tsx`

The current 3-col grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`) is replaced with a full-width stacked accordion. The outer `<section>` wrapper, `data-testid`, and `aria-label` are kept. The `GRID_*_CARDS` staircase constants are NOT reused (mode-3 is full-width-only).

**What to reuse from EndgameTimePressureSection.tsx:**

TC ordering pattern (lines 59-75):
```tsx
// Fixed TC order. Backend pre-filters by MIN_GAMES_PER_TC_CARD.
const visibleCount = data.cards.length;
const grandTotal = data.cards.reduce((acc, c) => acc + c.total, 0);
```

Empty state (lines 51-55):
```tsx
{data.cards.length === 0 ? (
  <div
    className="mt-2 text-sm text-muted-foreground"
    data-testid="time-pressure-cards-empty"
  >
    No time-pressure data yet. Import more games to see this section.
  </div>
) : (
```

**What replaces the grid — controlled accordion (D-12, from RESEARCH.md §7):**
```tsx
// Section receives categories_by_tc (new field from backend)
// primary TC computed client-side via computePrimaryTc

const [expandedTc, setExpandedTc] = useState<string>(primaryTc ?? '');

// Reset on filter change (D-12): key prop on the section component OR useEffect.
// Simplest: pass a `filterKey` prop from the parent that changes on any filter
// change; React re-mounts the component (resets useState).

<Accordion
  type="single"
  collapsible
  value={expandedTc}
  onValueChange={setExpandedTc}
  className="flex flex-col gap-2 mt-2"
>
  {eligibleTcs.map((tc) => (
    <EndgameTypeTcCard
      key={tc}
      tc={tc}
      categories={categoriesByTc[tc] ?? []}
      grandTotal={grandTotal}
      onCategorySelect={onCategorySelect}
    />
  ))}
</Accordion>
```

**Props change:** The section previously received `categories: EndgameCategoryStats[]` (pooled). Phase 98 adds `categoriesByTc: Record<TC, EndgameCategoryStats[]>` from the new backend field. `categories` (pooled) is no longer consumed here but stays on the parent response for LLM.

---

### `frontend/src/components/charts/EndgameTypeTcCard.tsx` (new component, request-response)

**Analog:** `frontend/src/components/charts/EndgameMetricsByTcCard.tsx`

This is the new per-TC accordion item: full-bleed charcoal header + responsive 4-tile grid body. It wraps one `AccordionItem`.

**Full-bleed charcoal header pattern** (EndgameMetricsByTcCard.tsx lines 354-379):
```tsx
<div
  className="charcoal-texture rounded-md w-full overflow-hidden"
  data-testid={`metrics-tc-card-${card.tc}`}
>
  {/* Full-bleed recessed header */}
  <div
    className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40"
    data-testid={`metrics-tc-card-${card.tc}-header`}
  >
    <TimeControlIcon timeControl={card.tc} className="h-4 w-4" />
    <h3 className="text-base font-semibold">{TC_LABELS[card.tc]}</h3>
    <span
      className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums font-normal"
      data-testid={`metrics-tc-card-${card.tc}-total`}
    >
      Games: {pctOfTotal}% ({card.total.toLocaleString()})
      <Swords className="h-3.5 w-3.5" aria-hidden="true" />
    </span>
  </div>
  ...
```

**Accordion item wrapping (Endgames.tsx lines 381-387):**
```tsx
<Accordion type="single" collapsible>
  <AccordionItem value="concepts" className="charcoal-texture rounded-md px-4"
    data-testid="endgame-concepts-trigger">
    <AccordionTrigger className="text-foreground justify-start flex-none gap-2 ...">
      ...
    </AccordionTrigger>
    <AccordionContent className="text-muted-foreground space-y-2">
```

**Phase 98 adaptation:** The `AccordionTrigger` IS the full-bleed header. Remove `px-4` from `AccordionItem` (the trigger handles its own padding). The charcoal container is on `AccordionItem`. The trigger content renders the TC icon + label + Games header row.

**CRITICAL: AccordionContent padding note** (from RESEARCH.md §7): Do NOT add `px-4` on `AccordionContent` — the tile grid body adds its own `p-4`. The header `bg-black/20 border-b border-border/40` must be full-bleed.

**Two-axis divider technique** (D-08 — per RESEARCH.md §5, Pitfall 4):

The `EndgameMetricsByTcCard` divider helper (lines 347-352) handles one axis only:
```tsx
const divider = (
  <>
    <div className="hidden lg:block w-px bg-border/40 mx-6" aria-hidden="true" />
    <div className="block lg:hidden border-t border-border/40 my-4" aria-hidden="true" />
  </>
);
```

For Phase 98's `4×1 → 2×2 → 1×4` grid, use **per-cell conditional border classes** (not `divide-x`/`divide-y` which bleeds across wrapping rows). Static tile order (0=rook, 1=minor_piece, 2=pawn, 3=queen) enables breakpoint-conditioned classes:

```tsx
// Grid container
<div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
  {tiles.map((tile, i) => (
    <div
      key={tile.endgame_class}
      className={cn(
        // Mobile (1×4): horizontal divider above every tile except first
        i > 0 && 'border-t border-border/40',
        // Tablet 2×2: override top borders for row 0 tiles,
        //   add right border to left-column tiles (i % 2 === 0)
        'sm:border-t-0',
        i < 2 ? '' : 'sm:border-t sm:border-border/40',   // bottom row
        i % 2 === 0 ? 'sm:border-r sm:border-border/40' : '', // left col
        // Desktop 4×1: no top borders, right border on all but last
        'xl:border-t-0',
        i < 3 ? 'xl:border-r xl:border-border/40' : 'xl:border-r-0',
      )}
    >
      <EndgameTypeCard ... />
    </div>
  ))}
</div>
```

Note: the planner must resolve the exact Tailwind class stacking; the per-cell conditional border approach is the correct technique per RESEARCH.md.

---

### `frontend/src/components/charts/EndgameTypeCard.tsx` (modified — literal restore)

**Analog:** `git show d3453597^:frontend/src/components/charts/EndgameTypeCard.tsx`

This is a **literal restore** of the pre-removal anatomy with two changes: (1) gauge bands come from `PER_CLASS_TC_GAUGE_ZONES[class][tc]` instead of `PER_CLASS_GAUGE_ZONES[class]`; (2) the tile receives a `tc` prop.

**What the removal commit d3453597 stripped (RESEARCH.md §4):**
1. `EndgameGauge` import
2. `PER_CLASS_GAUGE_ZONES` import
3. The `bands` variable (`PER_CLASS_GAUGE_ZONES[category.endgame_class]`)
4. `const PER_TYPE_GAUGE_SIZE = 130`
5. `const convZones = ...` / `const recovZones = ...` (via `colorizeGaugeZones`)
6. The gauge row JSX (`<div className="grid grid-cols-2 gap-2" data-testid="...-gauges">`)
7. The `gamesLink` `<span>` with Swords icon (the post-removal version simplified this)

**Pre-removal gauge zone derivation** (lines 120-155 of d3453597^ version):
```tsx
// Per-class gauge zones (p25/p75 bands from the generated registry).
const bands =
  category.endgame_class !== 'pawnless'
    ? PER_CLASS_GAUGE_ZONES[category.endgame_class]
    : undefined;
```

**Phase 98 replacement** (RESEARCH.md §Code Examples):
```typescript
import { PER_CLASS_TC_GAUGE_ZONES } from '@/generated/endgameZones';
import { colorizeGaugeZones } from '@/lib/theme';

// Inside the tile component (receives tc prop):
const classBands = category.endgame_class !== 'pawnless'
  ? PER_CLASS_TC_GAUGE_ZONES[category.endgame_class]?.[tc]
  : undefined;

const convZones = classBands ? colorizeGaugeZones(
  0, 100, classBands.conversion[0] * 100, classBands.conversion[1] * 100
) : undefined;

const recovZones = classBands ? colorizeGaugeZones(
  0, 100, classBands.recovery[0] * 100, classBands.recovery[1] * 100
) : undefined;

const [sgNeutralMin, sgNeutralMax] = classBands?.achievable_score_gap ?? [-0.04, 0.04];
```

**Gauge row JSX to restore** (from d3453597^ — extracted from RESEARCH.md §4):
```tsx
<div
  className="grid grid-cols-2 gap-2"
  data-testid={`${tileTestId}-gauges`}
>
  <div className="flex flex-col items-center" data-testid={`${tileTestId}-conv-gauge`}>
    <div className="text-sm text-muted-foreground mb-1">Conversion</div>
    <EndgameGauge
      value={category.conversion.conversion_pct}
      maxValue={100}
      label="Conversion"
      zones={convZones ?? colorizeGaugeZones([{ from: 0, to: 1.0 }])}
      size={PER_TYPE_GAUGE_SIZE}
    />
  </div>
  <div className="flex flex-col items-center" data-testid={`${tileTestId}-recov-gauge`}>
    <div className="text-sm text-muted-foreground mb-1">Recovery</div>
    <EndgameGauge
      value={category.conversion.recovery_pct}
      maxValue={100}
      label="Recovery"
      zones={recovZones ?? colorizeGaugeZones([{ from: 0, to: 1.0 }])}
      size={PER_TYPE_GAUGE_SIZE}
    />
  </div>
</div>
```

**Score Gap row change:** The `neutralMin`/`neutralMax` props on `ScoreGapRow` change from the flat `ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN/MAX` constants to `sgNeutralMin`/`sgNeutralMax` from the per-(class × TC) band. All other ScoreGapRow props are unchanged.

**Props interface change:** Add `tc: 'bullet' | 'blitz' | 'rapid' | 'classical'` to `EndgameTypeCardProps`. The `sharePct` denominator changes from pooled total to the TC-card's `grandTotal`.

---

### `frontend/src/types/endgames.ts` (modified — additive extension)

**Analog:** self (existing `EndgameStatsResponse` interface)

Current shape (lines 67-71):
```typescript
export interface EndgameStatsResponse {
  categories: EndgameCategoryStats[];  // sorted by total desc
  total_games: number;
  endgame_games: number;
}
```

**Phase 98 addition:** Add optional `categories_by_tc` field (optional for back-compat with older server responses per Pitfall 6):
```typescript
export interface EndgameStatsResponse {
  categories: EndgameCategoryStats[];  // unchanged — LLM path reads this
  total_games: number;
  endgame_games: number;
  // Phase 98: per-(class × TC) rates for the collapsible tile grid.
  // Optional for back-compat: gate in consumer with `if (!stats.categories_by_tc) return null`.
  categories_by_tc?: Record<
    'bullet' | 'blitz' | 'rapid' | 'classical',
    EndgameCategoryStats[]
  >;
}
```

---

### `app/services/endgame_zones.py` (modified — new data structure alongside existing)

**Analog:** `PER_CLASS_GAUGE_ZONES` + `TC_METRIC_BANDS` structures in the same file

**Existing `PerClassBands` dataclass** (lines 445-451) — the shape to replicate as `PerClassTcBands`:
```python
@dataclass(frozen=True)
class PerClassBands:
    """Typical [lower, upper] bands for Conversion, Recovery, and Score Gap for one endgame type."""
    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]
```

**Existing TC-keyed nested-dict pattern** (PRESSURE_BIN_SCORE_NEUTRAL_ZONES lines 538-541):
```python
PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Mapping[
    Literal["bullet", "blitz", "rapid", "classical"],
    Mapping[Literal[0, 1, 2, 3, 4], PressureBinBand],
] = { ... }
```

**New structure to add AFTER `PER_CLASS_GAUGE_ZONES`, BEFORE `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`:**
```python
@dataclass(frozen=True)
class PerClassTcBands:
    """Per-(class × TC) typical bands. Same shape as PerClassBands but TC-keyed."""
    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]

PER_CLASS_TC_GAUGE_ZONES: Mapping[
    EndgameClass,
    Mapping[Literal["bullet", "blitz", "rapid", "classical"], PerClassTcBands]
] = {
    "rook": {
        "bullet":     PerClassTcBands(conversion=(0.56, 0.75), recovery=(0.27, 0.43), achievable_score_gap=(-0.05, 0.05)),
        "blitz":      PerClassTcBands(conversion=(0.67, 0.82), recovery=(0.20, 0.37), achievable_score_gap=(-0.05, 0.05)),
        "rapid":      PerClassTcBands(conversion=(0.69, 0.83), recovery=(0.17, 0.30), achievable_score_gap=(-0.05, 0.05)),
        "classical":  PerClassTcBands(conversion=(0.74, 0.87), recovery=(0.13, 0.25), achievable_score_gap=(-0.05, 0.05)),
    },
    # ... remaining 4 classes per RESEARCH.md §1 tables
    # pawnless: OMITTED — n below floor; hidden in live UI
}
```

**All benchmark numbers are in RESEARCH.md §1.** Do NOT modify `PER_CLASS_GAUGE_ZONES` — it must remain unchanged for `assign_per_class_zone()` (D-15).

---

### `scripts/gen_endgame_zones_ts.py` (modified — new emission function)

**Analog:** `_format_tc_metric_bands()` in the same file (lines 132-151)

```python
def _format_tc_metric_bands() -> str:
    """Emit TC_METRIC_BANDS as a nested TS Record literal (Phase 97)."""
    lines: list[str] = []
    for tc, bands in TC_METRIC_BANDS.items():
        cr_lo, cr_hi = bands.conv_rate
        rr_lo, rr_hi = bands.recov_rate
        pr_lo, pr_hi = bands.parity_rate
        cg_lo, cg_hi = bands.conv_score_gap
        rg_lo, rg_hi = bands.recov_score_gap
        lines.append(
            f"  {tc}: {{ convRate: [{cr_lo}, {cr_hi}], recovRate: [{rr_lo}, {rr_hi}],"
            f" parityRate: [{pr_lo}, {pr_hi}],"
            f" convScoreGap: [{cg_lo}, {cg_hi}], recovScoreGap: [{rg_lo}, {rg_hi}] }},"
        )
    return "\n".join(lines) + "\n"
```

**New function to add (mirrors `_format_per_class_gauge_zones` but with TC nesting):**
```python
def _format_per_class_tc_gauge_zones() -> str:
    """Emit PER_CLASS_TC_GAUGE_ZONES as a nested TS Record literal (Phase 98)."""
    lines: list[str] = []
    for cls, tc_map in PER_CLASS_TC_GAUGE_ZONES.items():
        tc_entries = []
        for tc, bands in tc_map.items():
            c_lo, c_hi = bands.conversion
            r_lo, r_hi = bands.recovery
            g_lo, g_hi = bands.achievable_score_gap
            tc_entries.append(
                f"    {tc}: {{ conversion: [{c_lo}, {c_hi}], recovery: [{r_lo}, {r_hi}],"
                f" achievable_score_gap: [{g_lo}, {g_hi}] }},"
            )
        lines.append(f"  {cls}: {{\n" + "\n".join(tc_entries) + "\n  },")
    return "\n".join(lines) + "\n"
```

**`_render()` extension:** Add import of `PER_CLASS_TC_GAUGE_ZONES` from `endgame_zones` and add the emission block at the end of `_render()`, following the Phase 97 `TC_METRIC_BANDS` emission at lines 268-274:
```python
# In the imports block at top of _render or at module level:
from app.services.endgame_zones import (
    ...
    PER_CLASS_TC_GAUGE_ZONES,  # Phase 98
    ...
)
```

The generated TS shape (to emit in `_render()`):
```
"// Phase 98: per-(class × TC) gauge bands for Conv/Recov/ScoreGap.\n"
"export const PER_CLASS_TC_GAUGE_ZONES: Record<\n"
"  EndgameClassKey,\n"
"  Record<\n"
"    'bullet' | 'blitz' | 'rapid' | 'classical',\n"
"    { conversion: [number, number]; recovery: [number, number]; achievable_score_gap: [number, number] }\n"
"  >\n"
"> = {\n" + _format_per_class_tc_gauge_zones() + "} as const;\n"
```

---

### `app/services/endgame_service.py` (modified — new aggregation function)

**Analog:** `_compute_per_tc_metric_cards()` in the same file (lines 2287-2379+)

**Structure to replicate exactly:**
```python
def _compute_per_tc_metric_cards(
    bucket_rows: Sequence[Row[Any] | tuple[Any, ...]],
    *,
    percentile_rows: ...,
) -> EndgameMetricsCardsResponse:
    """Single pass through bucket_rows grouping by TC at col 6."""
    tc_accumulators: dict[str, _MetricTcAccumulator] = {}
    for row in bucket_rows:
        tc = row[6]  # time_control_bucket
        ...
        if tc not in tc_accumulators:
            tc_accumulators[tc] = _MetricTcAccumulator()
        acc = tc_accumulators[tc]
        acc.total += 1
        ...
    # Build cards in fixed TC order
```

**New function for Phase 98** — group by `(tc, endgame_class)` instead of just `tc`:
```python
def _aggregate_endgame_stats_by_tc(
    rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> dict[str, list[EndgameCategoryStats]]:
    """Group endgame stats by (TC, class) for the collapsible type-breakdown cards.

    Phase 98: single pass over bucket_rows (already fetched), extending
    _aggregate_endgame_stats to also produce a TC-keyed breakdown.
    Returns dict[tc_str, list[EndgameCategoryStats]] in bullet/blitz/rapid/classical
    order, each list sorted rook/minor_piece/pawn/queen (Mixed excluded from
    rendering but included in data for completeness; pawnless omitted).

    Column indices: game_id[0], endgame_class[1], result[2], user_color[3],
    eval_cp[4], eval_mate[5], time_control_bucket[6], ...
    """
    # tc -> class_int -> accumulator
    ...
    for row in rows:
        tc = row[6]
        endgame_class_int = row[1]
        ...
```

**Call site in `query_endgame_overview`** (around line 3447 — after `_compute_per_tc_metric_cards`):
```python
categories_by_tc = _aggregate_endgame_stats_by_tc(bucket_rows)
```

Then thread into `EndgameStatsResponse` (additive, optional field):
```python
stats = EndgameStatsResponse(
    categories=categories,          # unchanged
    total_games=total_games,        # unchanged
    endgame_games=endgame_games,    # unchanged
    categories_by_tc=categories_by_tc,  # Phase 98 addition
)
```

**Key implementation notes:**
- Reuse `_aggregate_endgame_stats`'s existing `_aggregate_wdl_counts`, `derive_user_result`, `_compute_score_p_value` helpers
- `score_p_value` must be computed per-(class, TC) the same way `_aggregate_endgame_stats` does it (Pitfall 7)
- The Score Gap fields (`type_achievable_score_gap_*`) are computed from eval cols 4/5/7/8 — same as the existing aggregation's span-gap path

---

### `app/schemas/endgames.py` (modified — additive field on EndgameStatsResponse)

**Analog:** `EndgameStatsResponse` class in the same file (lines 211-221)

Current schema:
```python
class EndgameStatsResponse(BaseModel):
    categories: list[EndgameCategoryStats]
    total_games: int
    endgame_games: int
```

**Phase 98 addition:**
```python
from typing import Literal

class EndgameStatsResponse(BaseModel):
    categories: list[EndgameCategoryStats]
    total_games: int
    endgame_games: int
    # Phase 98: per-(class × TC) rates for the collapsible endgame type cards.
    # Optional for back-compat; frontend gates on presence before rendering.
    categories_by_tc: (
        dict[Literal["bullet", "blitz", "rapid", "classical"], list[EndgameCategoryStats]]
        | None
    ) = None
```

---

## Shared Patterns

### Full-bleed Charcoal Header
**Source:** `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` lines 360-379
**Apply to:** `EndgameTypeTcCard.tsx` header
```tsx
<div className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40"
     data-testid={`type-breakdown-tc-${tc}-header`}>
  <TimeControlIcon timeControl={tc} className="h-4 w-4" />
  <h3 className="text-base font-semibold">{TC_LABELS[tc]}</h3>
  <span className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums font-normal">
    Games: {pctOfTotal}% ({totalFormatted})
    <Swords className="h-3.5 w-3.5" aria-hidden="true" />
  </span>
</div>
```

### Gauge Zone Colorization
**Source:** `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` (TC_METRIC_BANDS pattern) + `frontend/src/lib/theme.ts` (`colorizeGaugeZones`)
**Apply to:** `EndgameTypeCard.tsx` (restored tile)

The convention is `colorizeGaugeZones(domainMin, domainMax, typicalLower * scale, typicalUpper * scale)`. Gauge scale is 0-100 (percent); band fractions multiply by 100:
```typescript
colorizeGaugeZones(0, 100, classBands.conversion[0] * 100, classBands.conversion[1] * 100)
```

### Accordion Controlled Pattern
**Source:** `frontend/src/pages/Endgames.tsx` lines 381-388 (uncontrolled), adapt to controlled
**Apply to:** `EndgameTypeBreakdownSection.tsx`

`accordion.tsx` exposes `Accordion`, `AccordionItem`, `AccordionTrigger`, `AccordionContent`. The `AccordionItem` has `not-last:border-b` by default — override with `border-none` or use `className` to suppress the divider between accordion items (the `charcoal-texture rounded-md` card itself provides the visual separation; inter-item borders are not wanted here given `gap-2` spacing on the parent).

### TC Ordering + Null Suppression
**Source:** `frontend/src/components/charts/EndgameTimePressureSection.tsx` lines 51-93
**Apply to:** `EndgameTypeBreakdownSection.tsx`

Pattern: backend returns only TCs that pass `MIN_GAMES_PER_TC_CARD`; frontend iterates in fixed `["bullet", "blitz", "rapid", "classical"]` order. Import `MIN_GAMES_PER_TC_CARD` from `@/generated/endgameZones`.

### Single-Pass Row Accumulation
**Source:** `_compute_per_tc_metric_cards()` in `app/services/endgame_service.py` lines 2318-2378
**Apply to:** `_aggregate_endgame_stats_by_tc()` (new function)

Pattern: `dict[str, Accumulator]`, loop over `bucket_rows` once, access `row[6]` for TC, produce result in fixed `_TIME_CONTROL_ORDER` list at the end.

### Codegen Drift Gate
**Source:** `scripts/gen_endgame_zones_ts.py` `_render()` function (lines 154-275)
**Apply to:** All edits to `endgame_zones.py` + `gen_endgame_zones_ts.py`

After every Python zone change, run `uv run python scripts/gen_endgame_zones_ts.py` and commit `frontend/src/generated/endgameZones.ts`. CI runs `git diff --exit-code` on the generated file.

---

## Reused Primitives (No Change)

These files are consumed as-is; no modifications needed:

| File | Role | What Phase 98 consumes |
|---|---|---|
| `frontend/src/components/charts/EndgameGauge.tsx` | component | `size={130}` + `zones` (per-(class × TC) colorized zones) |
| `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` (`ScoreGapRow`) | component | `neutralMin`/`neutralMax` from `PER_CLASS_TC_GAUGE_ZONES[class][tc].achievable_score_gap` |
| `frontend/src/components/ui/accordion.tsx` | component | `Accordion`, `AccordionItem`, `AccordionTrigger`, `AccordionContent` |
| `frontend/src/components/stats/MiniWDLBar.tsx` | component | unchanged `win_pct`/`draw_pct`/`loss_pct` props |
| `frontend/src/components/charts/MiniBulletChart.tsx` | component | unchanged Score bullet pattern |
| `frontend/src/components/icons/TimeControlIcon.tsx` | component | `timeControl={tc}` prop |
| `frontend/src/lib/endgameMetrics.ts` | utility | `ENDGAME_CLASS_TO_SLUG`, `HIDDEN_ENDGAME_CLASSES`, `ENDGAME_TYPE_DESCRIPTIONS`, `SHOW_WDL_BAR_IN_TYPE_CARDS` |
| `frontend/src/lib/theme.ts` | utility | `colorizeGaugeZones`, `ZONE_DANGER`, `ZONE_SUCCESS`, `ZONE_NEUTRAL`, `UNRELIABLE_OPACITY`, `MIN_GAMES_FOR_RELIABLE_STATS` |
| `app/repositories/endgame_repository.py` (`query_endgame_bucket_rows`) | repository | No change — `time_control_bucket` at col 6 already present from Phase 97 |

---

## No Analog Found

No files in this phase lack a close analog. All patterns are available in the existing codebase.

---

## Metadata

**Analog search scope:** `frontend/src/components/charts/`, `frontend/src/lib/`, `frontend/src/types/`, `app/services/`, `app/schemas/`, `scripts/`, `frontend/src/components/ui/`, `frontend/src/pages/`
**Files scanned:** 14 (read directly); codebase structure verified via Bash grep
**Pattern extraction date:** 2026-05-30

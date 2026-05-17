# Phase 88: Time Pressure Stats Rework — Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 15 new/modified files
**Analogs found:** 15 / 15

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/score_confidence.py` (extend) | math utility | transform | self — add `compute_score_delta_vs_reference` alongside existing helpers | exact |
| `app/services/endgame_service.py` (extend) | service | CRUD, request-response | self — replace `_compute_clock_pressure` + `_compute_time_pressure_chart` with `_compute_time_pressure_cards` | exact |
| `app/schemas/endgames.py` (extend) | schema / model | request-response | self — add `TimePressureCardsResponse`; remove `ClockPressureResponse`, `TimePressureChartResponse` from `EndgameOverviewResponse` | exact |
| `app/services/endgame_zones.py` (extend) | config / codegen source | transform | self — add `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` alongside `PER_CLASS_GAUGE_ZONES` | exact |
| `scripts/gen_endgame_zones_ts.py` (extend) | utility / codegen | transform | self — add `_format_pressure_bin_zones()` and `_format_clock_gap_zone()` alongside `_format_per_class_gauge_zones()` | exact |
| `frontend/src/generated/endgameZones.ts` (regenerated) | config / codegen output | transform | self — new constants appended by codegen | exact |
| `frontend/src/lib/pressureBulletConfig.ts` (new) | utility | transform | `frontend/src/lib/scoreBulletConfig.ts` | exact |
| `frontend/src/components/charts/EndgameTimePressureCard.tsx` (new) | component | request-response | `frontend/src/components/charts/EndgameTypeCard.tsx` | exact |
| `frontend/src/components/charts/EndgameTimePressureSection.tsx` (new, replaces deleted) | component | request-response | `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` | exact |
| `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` (new) | test | request-response | `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx` | exact |
| `frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` (new) | test | request-response | `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` | exact |
| `tests/services/test_score_confidence.py` (extend) | test | transform | self — add `TestComputeScoreDeltaVsReference` class | exact |
| `tests/services/test_endgame_zones.py` (extend) | test | transform | `tests/services/test_endgame_zones.py` `TestRegistrySanity` class | exact |
| `tests/services/test_time_pressure_service.py` (new) | test | CRUD | `tests/test_endgame_service.py` | role-match |
| `.claude/skills/benchmarks/SKILL.md` (extend) | docs/skill | — | self — add §3.3.3 + §3.3.1 extension | exact |

---

## Pattern Assignments by Layer

---

### Layer 1: Backend Math

#### `app/services/score_confidence.py` — extend with `compute_score_delta_vs_reference`

**Analog:** self, alongside `compute_paired_difference_test` (lines 249–316)

**Imports pattern** (lines 54–64 of score_confidence.py):
```python
import math
from collections.abc import Sequence
from typing import Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CI_Z_95 as CI_Z_95,
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P as CONFIDENCE_HIGH_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P as CONFIDENCE_MEDIUM_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MIN_N as CONFIDENCE_MIN_N,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)
```

**Core pattern — private Wilson test helper** (lines 104–121):
```python
def _wilson_score_test_vs_half(score: float, n: int) -> tuple[float, float]:
    """Return (p_value, se_null) for the two-sided Wilson score-test of H0: score == 0.5."""
    se_null = math.sqrt(SCORE_PIVOT * (1.0 - SCORE_PIVOT) / n)
    z = (score - SCORE_PIVOT) / se_null
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return p_value, se_null
```

**New helper to add — `_wilson_score_test_vs_ref`** (derive from the above):
```python
def _wilson_score_test_vs_ref(score: float, n: int, ref: float) -> float:
    """Return two-sided p-value for H0: score == ref (Wald approximation at n>=10).

    z = (score - ref) / sqrt(ref * (1 - ref) / n). Same erfc formula as
    _wilson_score_test_vs_half but with an arbitrary null parameter.
    Assumes n >= 1; callers must gate.
    """
    se_null = math.sqrt(ref * (1.0 - ref) / n)
    if se_null == 0.0:
        return 0.0 if score != ref else 1.0
    z = (score - ref) / se_null
    return math.erfc(abs(z) / math.sqrt(2.0))
```

**New public function signature** (mirrors `compute_paired_difference_test` at line 249):
```python
def compute_score_delta_vs_reference(
    user_w: int,
    user_d: int,
    user_l: int,
    user_n: int,
    cohort_score: float,
) -> tuple[float, float | None, float | None, float | None]:
    """Return (delta, p_value, ci_low, ci_high) treating cohort_score as fixed.

    delta = user_score - cohort_score
    Wilson 95% CI on user_score transplanted to delta space.
    p_value = None when user_n < CONFIDENCE_MIN_N.
    All None (except delta=0.0) when user_n == 0.
    """
```

**Error handling** (copy the n=0 guard from lines 285–287):
```python
    if user_n == 0:
        return 0.0, None, None, None
    if user_n == 1:
        user_score = (user_w + 0.5 * user_d) / user_n
        return user_score - cohort_score, None, None, None
```

**What to copy:** The `compute_paired_difference_test` docstring structure, n-gate pattern (`p_out: float | None = p_value if n >= CONFIDENCE_MIN_N else None`), and variance-0 trap handling.

**What to differ:** Use `wilson_bounds` for CI and `_wilson_score_test_vs_ref` for p-value (not Wald/Bessel); transplant CI to delta space by subtracting `cohort_score` from both Wilson bounds.

---

### Layer 2: Backend Service

#### `app/services/endgame_service.py` — replace `_compute_clock_pressure` + `_compute_time_pressure_chart` with `_compute_time_pressure_cards`

**Analog:** `_compute_clock_pressure` at line 1438 and its call site at lines 2579–2584

**Imports to add** (follow the existing import block at lines 40–77):
```python
from app.services.score_confidence import (
    compute_confidence_bucket,
    compute_paired_difference_test,
    compute_score_confidence_from_mean,
    compute_score_difference_test,
    compute_score_delta_vs_reference,  # Phase 88 — new
    wilson_bounds,
)
```

**Function signature pattern** (mirrors `_compute_clock_pressure` at line 1438):
```python
def _compute_time_pressure_cards(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
) -> TimePressureCardsResponse:
    """Compute per-TC time pressure card payload.

    Returns one TimePressureTcCard per TC (hidden when total < MIN_GAMES_PER_TC_CARD).
    Each card: 1 Clock Gap bullet + 5 Score-Delta bullets (one per 20% quintile).
    """
```

**Accumulator pattern** (copy defaultdict pattern from lines 1472–1480):
```python
    tc_game_ids: dict[str, set[int]] = defaultdict(set)
    tc_clock_diffs: dict[str, list[float]] = defaultdict(list)
    # per (tc, quintile): list of per-game (w, d, l) for score accumulation
    tc_quintile_wdl: dict[tuple[str, int], tuple[int, int, int]] = defaultdict(lambda: (0, 0, 0))
```

**Call site** (lines 2579–2584, replace the two calls with one):
```python
    # Phase 88: replaces _compute_clock_pressure + _compute_time_pressure_chart
    time_pressure_cards = _compute_time_pressure_cards(clock_rows)
```

**What to copy:** Row iteration + clock extraction logic from `_compute_clock_pressure` (lines 1482–1530), base_clock guard, timeout accounting, TC bucket accumulation pattern.

**What to differ:** Instead of per-TC summary rows, produce per-TC × per-quintile WDL accumulators; apply `compute_score_delta_vs_reference` against mirror-bucket `cohort_score`; add Clock Gap bullet via `compute_paired_difference_test` on per-game `(user_clock - opp_clock) / base_clock`.

---

### Layer 3: Backend Schemas

#### `app/schemas/endgames.py` — add `TimePressureCardsResponse`, modify `EndgameOverviewResponse`

**Analog:** `ClockPressureResponse` (line 481) and `TimePressureChartResponse` (line 517)

**Pydantic model pattern** (lines 481–499):
```python
class ClockPressureResponse(BaseModel):
    """..."""
    rows: list[ClockStatsRow]
    total_clock_games: int
    total_endgame_games: int
    timeline: list[ClockPressureTimelinePoint]
    timeline_window: int
```

**New schema structure:**
```python
class PressureQuintileBullet(BaseModel):
    """Score-Delta bullet data for one pressure quintile in a TC card."""
    quintile_index: int            # 0=0-20% (max pressure) … 4=80-100% (min)
    quintile_label: str            # "0-20%" … "80-100%"
    n: int                         # game count in this bin
    delta: float                   # user_score - cohort_score
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    cohort_score: float | None     # reference line (live mirror-bucket)

class ClockGapBullet(BaseModel):
    """Clock Gap bullet data for one TC card (mean of (my-opp)/base at endgame entry)."""
    n: int
    mean_diff_pct: float           # mean (user_clock - opp_clock) / base_clock
    p_value: float | None
    ci_low: float | None
    ci_high: float | None

class TimePressureTcCard(BaseModel):
    """All bullet data for one time-control card."""
    tc: Literal["bullet", "blitz", "rapid", "classical"]
    total: int                     # total endgame games in this TC
    clock_gap: ClockGapBullet
    quintiles: list[PressureQuintileBullet]  # always 5, ordered Q0..Q4

class TimePressureCardsResponse(BaseModel):
    """Replaces ClockPressureResponse + TimePressureChartResponse (Phase 88)."""
    cards: list[TimePressureTcCard]  # only TCs with total >= MIN_GAMES_PER_TC_CARD
```

**`EndgameOverviewResponse` diff** (lines 628–629):
```python
# REMOVE:
clock_pressure: ClockPressureResponse
time_pressure_chart: TimePressureChartResponse
# ADD:
time_pressure_cards: TimePressureCardsResponse  # Phase 88
```

**What to copy:** Pydantic v2 `BaseModel` with typed fields, `Literal` for TC, docstring convention.

**What to differ:** Nested structure (card > quintile bullets) instead of flat row list; `float | None` on p_value/CI with same None-means-insufficient-data semantics.

---

### Layer 4: Backend Zone Registry

#### `app/services/endgame_zones.py` — extend with `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` and `clock_gap_pct` in `MetricId`

**Analog:** `PER_CLASS_GAUGE_ZONES` pattern (lines 406–464 area; see RESEARCH.md excerpt)

**New frozen dataclass pattern** (mirror `PerClassBands` at line ~406):
```python
@dataclass(frozen=True)
class PressureBinBand:
    """Neutral [lower, upper] band for Score-Delta in one (TC, quintile) cell."""
    lower: float
    upper: float
```

**Registry shape** (mirror `PER_CLASS_GAUGE_ZONES` nested Mapping pattern):
```python
# Phase 88 D-02: per-(TC, pressure-quintile) neutral band.
# Calibrated from /benchmarks §3.3.3. ELO pooled (collapse confirmed per quintile).
# Editorial cap: PRESSURE_BIN_NEUTRAL_CAP = 0.06 (half-width max).
PRESSURE_BIN_NEUTRAL_CAP: float = 0.06

PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Mapping[
    Literal["bullet", "blitz", "rapid", "classical"],
    Mapping[Literal[0, 1, 2, 3, 4], PressureBinBand]
] = {
    "bullet":    {0: PressureBinBand(-0.06, 0.06), ...},
    ...
}
```

**`MetricId` extension** (line 30 Literal — add after `"win_rate"`):
```python
"clock_gap_pct",  # Phase 88: (my_clock - opp_clock) / base_clock at endgame entry
```

**`ZONE_REGISTRY` entry for clock_gap_pct** (mirror `avg_clock_diff_pct` entry):
```python
"clock_gap_pct": ZoneSpec(
    typical_lower=-NEUTRAL_PCT_THRESHOLD,  # placeholder; update after /benchmarks §3.3.1
    typical_upper=NEUTRAL_PCT_THRESHOLD,
    direction="higher_is_better",
),
```

**What to copy:** `@dataclass(frozen=True)`, `Mapping[..., Mapping[...]]` nested type, `ZONE_REGISTRY` scalar ZoneSpec pattern.

**What to differ:** Two-level key `(TC, quintile_index)` instead of one-level `EndgameClass`; add `PRESSURE_BIN_NEUTRAL_CAP` constant for editorial cap documentation.

---

### Layer 5: Codegen Script

#### `scripts/gen_endgame_zones_ts.py` — extend with `_format_pressure_bin_zones()` and clock_gap emission

**Analog:** `_format_per_class_gauge_zones()` at lines 90–106 and scalar emission at lines 137–155

**New import block** (follow lines 30–36 pattern):
```python
from app.services.endgame_zones import (  # noqa: E402
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_PCT_THRESHOLD,
    NEUTRAL_TIMEOUT_THRESHOLD,
    PER_CLASS_GAUGE_ZONES,
    PRESSURE_BIN_SCORE_NEUTRAL_ZONES,  # Phase 88
    ZONE_REGISTRY,
)
```

**New formatter function** (mirror `_format_per_class_gauge_zones` at lines 90–106):
```python
def _format_pressure_bin_zones() -> str:
    """Emit PRESSURE_BIN_SCORE_NEUTRAL_ZONES as a nested TS Record literal."""
    lines: list[str] = []
    for tc, quintile_map in PRESSURE_BIN_SCORE_NEUTRAL_ZONES.items():
        q_entries = ", ".join(
            f"{q}: {{ min: {band.lower}, max: {band.upper} }}"
            for q, band in quintile_map.items()
        )
        lines.append(f"  {tc}: {{ {q_entries} }},")
    return "\n".join(lines) + "\n"
```

**`_render()` extension** (append after the `PER_CLASS_GAUGE_ZONES` block at lines 183–187):
```python
"// Phase 88 D-02: per-(TC, pressure-quintile) neutral bands.\n"
"// Quintile 0 = 0-20% clock remaining (max pressure), 4 = 80-100%.\n"
"export const PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Record<\n"
"  'bullet' | 'blitz' | 'rapid' | 'classical',\n"
"  Record<0 | 1 | 2 | 3 | 4, { min: number; max: number }>\n"
"> = {\n"
+ _format_pressure_bin_zones()
+ "} as const;\n"
```

**What to copy:** The `_render()` string-concatenation pattern, `--check` mode in `main()`, the import-from-endgame_zones pattern.

**What to differ:** Two-level TS `Record<TC, Record<quintile, {min, max}>>` output instead of flat constant or single-level object.

---

### Layer 6: Frontend Config

#### `frontend/src/lib/pressureBulletConfig.ts` (new)

**Analog:** `frontend/src/lib/scoreBulletConfig.ts` (lines 1–52)

**Pattern to copy** (full file is 52 lines):
```typescript
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

// Center the pressure Score-Delta bullet on 0 (delta = 0 means matches cohort).
export const PRESSURE_DELTA_CENTER = 0;

// Axis half-width: ±20 score points covers the expected ±15pp IQR generously.
// CIs that overflow render with open-ended whiskers.
export const PRESSURE_DELTA_DOMAIN = 0.20;

// Axis half-width for the Clock Gap bullet: ±30pp covers the p5/p95 prod range.
export const CLOCK_GAP_DOMAIN = 0.30;

/** Clamp a delta-domain value (or CI bound) to a safe display range. */
export function clampDeltaCi(value: number): number {
  if (value < -1) return -1;
  if (value > 1) return 1;
  return value;
}

/** Pick the zone color for a score-delta relative to the per-bin neutral band.
 * neutralMin/Max come from PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][quintile].
 */
export function pressureDeltaZoneColor(
  delta: number,
  neutralMin: number,
  neutralMax: number,
): string {
  if (delta >= neutralMax) return ZONE_SUCCESS;
  if (delta <= neutralMin) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
```

**What to copy:** Named constants for center/domain, clamp util, zone-color function shape from `scoreBulletConfig.ts`.

**What to differ:** `pressureDeltaZoneColor` accepts explicit `(neutralMin, neutralMax)` params (looked up per-bin from `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`) rather than using module-level fixed constants, because the neutral band varies per `(TC, quintile)`.

---

### Layer 7: Frontend Components

#### `frontend/src/components/charts/EndgameTimePressureCard.tsx` (new per-TC card)

**Analog:** `frontend/src/components/charts/EndgameTypeCard.tsx` (full file, 441 lines)

**Imports pattern** (lines 23–71 of EndgameTypeCard.tsx):
```typescript
import type { CSSProperties } from 'react';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import {
  PRESSURE_BIN_SCORE_NEUTRAL_ZONES,
  CLOCK_GAP_NEUTRAL_MIN,
  CLOCK_GAP_NEUTRAL_MAX,
} from '@/generated/endgameZones';
import {
  PRESSURE_DELTA_CENTER,
  PRESSURE_DELTA_DOMAIN,
  CLOCK_GAP_DOMAIN,
  clampDeltaCi,
  pressureDeltaZoneColor,
} from '@/lib/pressureBulletConfig';
import { isConfident } from '@/lib/significance';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  UNRELIABLE_OPACITY,
} from '@/lib/theme';
```

**Per-bin sparse handling** (mirror EndgameTypeCard lines 95–100):
```typescript
// TC-level hide: total < MIN_GAMES_PER_TC_CARD
if (card.total < MIN_GAMES_PER_TC_CARD) return null;

// Per-bin: n=0 → dash, 0 < n < MIN_GAMES_PER_PRESSURE_BIN → dimmed bullet
const binStyle = (n: number): CSSProperties | undefined =>
  n > 0 && n < MIN_GAMES_PER_PRESSURE_BIN
    ? { opacity: UNRELIABLE_OPACITY }
    : undefined;
```

**MiniBulletChart usage for Score-Delta** (mirror EndgameTypeCard lines 372–384):
```typescript
<MiniBulletChart
  value={bin.delta}
  center={PRESSURE_DELTA_CENTER}
  neutralMin={PRESSURE_BIN_SCORE_NEUTRAL_ZONES[card.tc][bin.quintile_index].min}
  neutralMax={PRESSURE_BIN_SCORE_NEUTRAL_ZONES[card.tc][bin.quintile_index].max}
  domain={PRESSURE_DELTA_DOMAIN}
  ciLow={bin.ci_low != null ? clampDeltaCi(bin.ci_low) : undefined}
  ciHigh={bin.ci_high != null ? clampDeltaCi(bin.ci_high) : undefined}
  ariaLabel={`Score delta at ${bin.quintile_label} pressure: ${formattedDelta}`}
/>
```

**Triple-gate font coloring** (mirror EndgameTypeCard lines 107–111):
```typescript
const level = deriveLevel(bin.p_value, bin.n);
const neutralBand = PRESSURE_BIN_SCORE_NEUTRAL_ZONES[card.tc][bin.quintile_index];
const isInColoredZone =
  bin.delta >= neutralBand.max || bin.delta <= neutralBand.min;
const showFontColor =
  bin.n >= MIN_GAMES_PER_PRESSURE_BIN &&
  isConfident(level) &&
  isInColoredZone;
```

**Empty bin slot** (n=0 renders dash, no bullet, preserves height):
```typescript
{bin.n === 0 ? (
  <span className="text-muted-foreground text-sm" aria-label="no games">—</span>
) : (
  <div style={binStyle(bin.n)}> ... MiniBulletChart ... </div>
)}
```

**What to copy:** `EndgameTypeCard` full component structure — title row with InfoPopover, body wrapper with `UNRELIABLE_OPACITY`, `isConfident`/`deriveLevel` triple-gate, `MetricStatPopover` per bullet, `data-testid` on every element.

**What to differ:** No gauges (replaced by 6 bullets stacked); TC-level hide (not per-type empty shell); per-quintile sparse handling at the row level rather than whole-body; n=0 dash-slot (not opacity) to preserve uniform card height.

---

#### `frontend/src/components/charts/EndgameTimePressureSection.tsx` (new section orchestrator)

**Analog:** `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` (lines 1–75)

**Grid layout** (mirror EndgameTypeBreakdownSection line 55):
```typescript
<div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4 mt-2">
  {cards.map((card) => (
    <EndgameTimePressureCard
      key={card.tc}
      card={card}
      data-testid={`time-pressure-card-${card.tc}`}
    />
  ))}
</div>
```

**Section wrapper** (mirror EndgameTypeBreakdownSection lines 47–51):
```typescript
<section
  data-testid="time-pressure-cards-section"
  aria-labelledby="time-pressure-heading"
>
  <p className="text-sm text-muted-foreground">
    How does your score change as your clock runs down?
  </p>
```

**What to copy:** `EndgameTypeBreakdownSection` orchestrator pattern — `section` wrapper with `data-testid`, sub-question copy above the grid, map over cards, Tailwind responsive grid (`lg` 2-col, `xl` 4-col for 4 TC cards).

**What to differ:** Grid is 4-col at `xl` (vs 3-col for 5 type cards); no `HIDDEN_*` filter needed (backend already omits hidden TCs); no `sharePct` computation.

---

### Layer 8: Frontend Tests

#### `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` (new)

**Analog:** `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx` (lines 1–54 for boilerplate)

**Test file boilerplate** (lines 1–58 of EndgameTypeCard.test.tsx — copy exactly):
```typescript
// @vitest-environment jsdom
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', { writable: true, value: vi.fn()
    .mockImplementation((query: string) => ({
      matches: false, media: query, onchange: null,
      addEventListener: vi.fn(), removeEventListener: vi.fn(),
      addListener: vi.fn(), removeListener: vi.fn(), dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {} unobserve() {} disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub })
    .ResizeObserver = ResizeObserverStub;
});
afterEach(() => { cleanup(); });
```

**Key scenarios to cover** (from RESEARCH.md validation architecture):
```typescript
it('hides card when total < MIN_GAMES_PER_TC_CARD', ...)
it('renders dash for n=0 bin, preserving slot', ...)
it('dims bullet at UNRELIABLE_OPACITY when 0 < n < MIN_GAMES_PER_PRESSURE_BIN', ...)
it('renders n=X chip on dimmed bullet rows', ...)
it('applies font color when triple-gate passes', ...)
it('no font color when p_value above 0.05', ...)
it('always renders clock-gap bullet when card is visible', ...)
```

**What to copy:** Full `beforeAll`/`afterEach` boilerplate from `EndgameTypeCard.test.tsx` lines 21–58; builder function pattern for minimal fixture data; `describe` + `it` structure; `screen.getByTestId` assertions.

**What to differ:** Fixture data shape is `TimePressureTcCard` not `EndgameCategoryStats`; test sparse-bin per-row scenarios (not whole-card sparse); no `onCategorySelect` callback to test.

---

#### `frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` (new)

**Analog:** `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` (lines 1–60 for boilerplate + grid test patterns)

**Key scenarios** (from RESEARCH.md validation architecture):
```typescript
it('renders visible TC cards and omits hidden ones', ...)
it('asserts data-testid="time-pressure-card-bullet" present when bullet card included', ...)
it('asserts data-testid="time-pressure-card-blitz" absent when blitz hidden', ...)
it('asserts legacy data-testid="clock-pressure-section" is absent (knip clean proxy)', ...)
```

**What to copy:** Full boilerplate from `EndgameTypeBreakdownSection.test.tsx` lines 1–48; `MemoryRouter` + `TooltipProvider` wrapper pattern; mock payload builder pattern.

**What to differ:** Fixture is `TimePressureCardsResponse` not `EndgameCategoryStats[]`; grid check is `xl:grid-cols-4` not `lg:grid-cols-3`; assert absence of legacy `clock-pressure-section` testid.

---

### Layer 9: Backend Tests

#### `tests/services/test_score_confidence.py` (extend with new class)

**Analog:** self, `TestComputePairedDifferenceTest` class already in this file

**Class structure to copy** (lines 34–80 pattern from the file):
```python
class TestComputeScoreDeltaVsReference:
    """Boundary tests for compute_score_delta_vs_reference.

    Tests the delta = user_score - cohort_score path and Wilson CI transplant.
    """

    def test_n_zero_returns_zero_delta_all_none(self) -> None:
        delta, p, ci_low, ci_high = compute_score_delta_vs_reference(0, 0, 0, 0, 0.5)
        assert delta == 0.0
        assert p is None and ci_low is None and ci_high is None

    def test_all_wins_delta_positive(self) -> None:
        delta, p, ci_low, ci_high = compute_score_delta_vs_reference(5, 0, 0, 5, 0.5)
        assert delta == pytest.approx(0.5)
        assert ci_low is not None and ci_low > 0
        assert ci_high is not None

    def test_user_score_equals_cohort_score_delta_zero(self) -> None:
        ...  # p_value approx 1.0

    def test_n_below_gate_p_value_none(self) -> None:
        _, p, _, _ = compute_score_delta_vs_reference(5, 0, 4, 9, 0.5)
        assert p is None  # n=9 < CONFIDENCE_MIN_N=10
```

**What to copy:** `pytest.approx` tolerance pattern, `assert p is None` gate tests, docstring format.

**What to differ:** Test `cohort_score != 0.5` boundary (near 0 and near 1 per RESEARCH.md test table); assert `ci_low < delta < ci_high` for non-degenerate inputs.

---

#### `tests/services/test_endgame_zones.py` (extend with registry sanity for new metric)

**Analog:** `TestRegistrySanity.test_all_scalar_metrics_have_entries` at line 196

**Pattern to copy** (lines 196–250):
```python
def test_all_scalar_metrics_have_entries(self) -> None:
    assert set(ZONE_REGISTRY.keys()) == {
        "score_gap",
        ...
        "clock_gap_pct",  # Phase 88 — add this
    }

def test_pressure_bin_zones_shape(self) -> None:
    """PRESSURE_BIN_SCORE_NEUTRAL_ZONES covers all 4 TCs × 5 quintiles."""
    from app.services.endgame_zones import PRESSURE_BIN_SCORE_NEUTRAL_ZONES
    tcs = {"bullet", "blitz", "rapid", "classical"}
    assert set(PRESSURE_BIN_SCORE_NEUTRAL_ZONES.keys()) == tcs
    for tc in tcs:
        assert set(PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc].keys()) == {0, 1, 2, 3, 4}
        for q in range(5):
            band = PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q]
            assert band.lower < band.upper
            # Editorial cap: half-width <= PRESSURE_BIN_NEUTRAL_CAP
            assert (band.upper - band.lower) / 2 <= PRESSURE_BIN_NEUTRAL_CAP + 1e-9
```

**What to copy:** `TestRegistrySanity` class structure, `set()` equality assertion for registry keys, boundary assertions per spec value.

**What to differ:** Add new `test_pressure_bin_zones_shape` test covering the 4×5 shape invariant and editorial-cap assertion.

---

#### `tests/services/test_time_pressure_service.py` (new)

**Analog:** `tests/test_endgame_service.py` (for service-layer + mock-data patterns)

**What to copy:** The pattern of constructing minimal mock row sequences, calling the private `_compute_*` function directly (not via async endpoint), asserting on schema fields.

**What to differ:** Mock rows must include clock data (ply_array, clock_array, base_time_seconds); test the quintile bucketing math (Q0 = 0-20% clock remaining gets lowest quintile index).

---

### Layer 10: Docs / Skill

#### `.claude/skills/benchmarks/SKILL.md` — add §3.3.3 and extend §3.3.1

**Analog:** Existing §3.3.2 structure in the skill (medium-confidence match from RESEARCH.md §Q4)

**New subchapter §3.3.3 structure** (mirror §3.3.2 pattern — per RESEARCH.md §Q4):
```markdown
### §3.3.3 chess-score-per-pressure-bin

**Shape:** metric-with-sub-bins. Per-user `user_score = (W + 0.5D) / N` per
(user_id × TC × quintile) cell, where quintile = LEAST(4, FLOOR(user_clk_pct / 20)).

**Collapse verdict runs per-quintile (5 verdicts)** — not a global single verdict —
because score distributions compress at extreme quintiles.

**Shipped band shape:** 20 entries (4 TC × 5 quintile), ELO pooled by default.
Any quintile where ELO verdict is "keep separate" (d >= 0.5) gets promoted to
(TC × ELO × quintile) for that quintile only.

**Output:** per-(TC, quintile) Q1/Q3 of per-user `user_score` → `endgame_zones.py`
`PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (not cohort_score — that is the live mirror-bucket).
```

**What to copy:** §3.3.2 standard CTE reference, sparse-cell exclusion `NOT (elo_bucket = 2400 AND tc = 'classical')`, Cohen's d verdict table format, n_users ≥ 10 floor.

**What to differ:** Per-quintile iteration (5 separate Cohen's d runs per axis); per-user IQR output (not game-level aggregate); note that `cohort_score` is NOT in this output — only IQR band bounds.

---

## Shared Patterns

### Triple-gate font coloring
**Source:** `frontend/src/components/charts/EndgameTypeCard.tsx` lines 107–111 and `frontend/src/lib/significance.ts`
**Apply to:** Every Score-Delta bullet in `EndgameTimePressureCard`
```typescript
const level = deriveLevel(bin.p_value, bin.n);
const isInColoredZone = zoneColor !== ZONE_NEUTRAL;
const showFontColor = bin.n >= MIN_GAMES_PER_PRESSURE_BIN && isConfident(level) && isInColoredZone;
```

### `UNRELIABLE_OPACITY` dimming
**Source:** `frontend/src/lib/theme.ts`, consumed in `EndgameTypeCard.tsx` lines 96–100
**Apply to:** Per-bin bullet rows where `0 < n < MIN_GAMES_PER_PRESSURE_BIN`
```typescript
const binStyle: CSSProperties | undefined =
  bin.n > 0 && bin.n < MIN_GAMES_PER_PRESSURE_BIN
    ? { opacity: UNRELIABLE_OPACITY }
    : undefined;
```

### N-gate pattern (backend)
**Source:** `app/services/score_confidence.py` lines 285–287, 314
**Apply to:** `compute_score_delta_vs_reference`
```python
p_out: float | None = p_value if user_n >= CONFIDENCE_MIN_N else None
```

### `data-testid` naming convention
**Source:** `EndgameTypeCard.tsx` pattern (e.g. `data-testid={`${tileTestId}-score-bullet`}`)
**Apply to:** All interactive elements and major containers in `EndgameTimePressureCard`
```
time-pressure-card-{tc}             # card root
time-pressure-card-{tc}-clock-gap   # clock gap bullet row
time-pressure-card-{tc}-bin-{q}     # per-quintile bullet row (q=0..4)
time-pressure-card-{tc}-bin-{q}-n   # n-chip on dimmed row
```

### Pydantic v2 schema docstring convention
**Source:** `app/schemas/endgames.py` `ClockPressureResponse` docstring (lines 481–493)
**Apply to:** All new schema classes in `app/schemas/endgames.py`
```python
class TimePressureTcCard(BaseModel):
    """Per-TC card payload for the time-pressure section (Phase 88).

    total: all endgame games with clock data for this TC (pre-quintile-split).
    clock_gap: Clock Gap bullet — mean of (user_clock - opp_clock) / base_clock.
    quintiles: 5 Score-Delta bullets (Q0=0-20% to Q4=80-100% clock remaining).
    """
```

### Wilson CI transplant
**Source:** `app/services/score_confidence.py` `wilson_bounds` (lines 74–101)
**Apply to:** `compute_score_delta_vs_reference` CI output
```python
ci_lo_abs, ci_hi_abs = wilson_bounds(user_score, user_n)
ci_low = ci_lo_abs - cohort_score
ci_high = ci_hi_abs - cohort_score
```

---

## No Analog Found

All files have close analogs in the codebase. No file requires falling back to RESEARCH.md patterns alone.

---

## Files to Delete (no new analog needed)

| File | Reason |
|---|---|
| `frontend/src/components/charts/EndgameClockPressureSection.tsx` | Replaced by `EndgameTimePressureCard` + section orchestrator |
| `frontend/src/components/charts/EndgameTimePressureSection.tsx` | Same replacement (new file reuses the name or uses `EndgameTimePressureCardsSection`) |

Both deletions require a knip sweep to confirm no dead imports remain.

---

## Metadata

**Analog search scope:** `app/services/`, `app/schemas/`, `scripts/`, `frontend/src/components/charts/`, `frontend/src/lib/`, `tests/services/`, `frontend/src/components/charts/__tests__/`
**Files scanned (via Read):** 14 files read in full or targeted sections
**Pattern extraction date:** 2026-05-17

---

## PATTERN MAPPING COMPLETE

**Phase:** 88 — time-pressure-stats-rework
**Files classified:** 15
**Analogs found:** 15 / 15

### Coverage
- Files with exact analog: 15 (all are extensions of existing files or mirror an existing component one-to-one)
- Files with role-match analog: 0
- Files with no analog: 0

### Key Patterns Identified
- All per-TC card work mirrors `EndgameTypeCard.tsx` exactly: UNRELIABLE_OPACITY dimming, triple-gate font coloring via `isConfident`/`deriveLevel`, MiniBulletChart props, MetricStatPopover per bullet, data-testid on every element.
- The new math helper `compute_score_delta_vs_reference` copies `compute_paired_difference_test`'s n-gate/variance-0-trap structure but substitutes `wilson_bounds` for CI and `_wilson_score_test_vs_ref` for p-value.
- The codegen extension follows `_format_per_class_gauge_zones()` exactly: a `_format_pressure_bin_zones()` helper + string-concat in `_render()`, checked by CI drift gate.
- Backend schema changes are additive replacements: drop two flat response types, add nested `TimePressureCardsResponse`; `EndgameOverviewResponse` gains one field, loses two.

### File Created
`/home/aimfeld/Projects/Python/flawchess/.planning/milestones/v1.17-phases/88-time-pressure-stats-rework/88-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can reference analog file paths and line numbers in PLAN.md action sections.

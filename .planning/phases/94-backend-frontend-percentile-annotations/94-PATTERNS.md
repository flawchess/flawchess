# Phase 94: Backend & Frontend Percentile Annotations - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 10 (3 new, 7 modified)
**Analogs found:** 10 / 10 (exact match available for every file)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/schemas/endgames.py` (MOD) | schema (Pydantic v2) | request-response | self (existing `score_difference_p_value` / `_ci_*` sibling group, lines 421-455) | exact (self) |
| `app/services/endgame_service.py` (MOD, 2 sites) | service (compute) | request-response | self (existing `_p_value` gate at lines 2287-2289 and at 1322-1333) | exact (self) |
| `tests/schemas/test_endgames_schema.py` (MOD) | test (Pydantic schema assertion) | unit | self (existing field-presence assertion at lines 24-38) | exact (self) |
| `tests/test_endgame_service.py` (MOD) | test (service gate) | unit | self (existing PVALUE gate tests) | exact (self) |
| `frontend/src/types/endgames.ts` (MOD) | type-mirror (manual) | none | self (existing `achievable_score_gap_*` declarations at lines 112-115) | exact (self) |
| `frontend/src/components/charts/PercentileChip.tsx` (NEW) | component (popover trigger + pill) | event-driven | `frontend/src/components/popovers/MetricStatPopover.tsx` | role-match (popover shell mechanics); chip pill itself is bespoke |
| `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` (MOD) | component (slot-prop primitive) | request-response | self (existing optional `startSlot` / `endSlot` props at lines 50-54) | exact (self) |
| `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` (MOD) | component (orchestrator) | request-response | self (existing `ScoreGapRow` consumer + `MetricStatPopover` tooltip prop) | exact (self) |
| `frontend/src/components/charts/EndgameMetricCard.tsx` (MOD) | component (per-bucket card) | request-response | self (existing `ScoreGapRow` consumer with bucket dispatch at lines 205-242) | exact (self) |
| `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` (NEW) | test (Vitest + RTL) | unit/component | `frontend/src/components/charts/__tests__/EndgameOverallScoreGapRow.test.tsx` (mock + render + assertion shape) | role-match |

---

## Pattern Assignments

### `app/schemas/endgames.py` (schema, request-response)

**Analog:** self — extend the `ScoreGapMaterialResponse` and `EndgamePerformanceResponse` field groups in the same file.

**Field-shape pattern** — siblings already on `ScoreGapMaterialResponse` (lines 421-429):
```python
score_difference_p_value: float | None = None
"""Two-sided p-value of (endgame_score - non_endgame_score) vs 0.
None when min(endgame_wdl.total, non_endgame_wdl.total) < PVALUE_RELIABILITY_MIN_N (=10)."""

score_difference_ci_low: float | None = None
"""Lower bound of 95% Wald-z CI on score_difference. None when min(...) < 2."""

score_difference_ci_high: float | None = None
"""Upper bound of 95% Wald-z CI on score_difference. None when min(...) < 2."""
```

**Section 2 per-bucket sibling pattern** — already on `ScoreGapMaterialResponse` (lines 437-455):
```python
section2_score_gap_conv_mean: float | None = None
section2_score_gap_conv_n: int | None = None
section2_score_gap_conv_p_value: float | None = None
section2_score_gap_conv_ci_low: float | None = None
section2_score_gap_conv_ci_high: float | None = None
# (… parity / recov same shape)
```

**Achievable Score Gap sibling group** — on `EndgamePerformanceResponse` (lines 241-254):
```python
achievable_score_gap: float = 0.0
achievable_score_gap_p_value: float | None = None
achievable_score_gap_ci_low: float | None = None
achievable_score_gap_ci_high: float | None = None
```

**Copy pattern as:**
- `score_gap_percentile: float | None = None` on `ScoreGapMaterialResponse` (next to `score_difference_*` group). Docstring MUST note the deliberate field-name divergence (key mirrors MetricId `score_gap`, not the wire-format `score_difference` — RESEARCH §Pitfall 1).
- `section2_score_gap_conv_percentile` + `section2_score_gap_parity_percentile` on `ScoreGapMaterialResponse` (next to their `_p_value` / `_ci_*` siblings). NOTE: no recovery percentile — per CONTEXT D-12 the recovery CDF is not shipped.
- `achievable_score_gap_percentile: float | None = None` on `EndgamePerformanceResponse` (next to `achievable_score_gap_*` group).

---

### `app/services/endgame_service.py` — site A: `_get_endgame_performance_from_rows` (~line 2270-2322)

**Analog (self) — existing single-N gate at lines 2285-2289:**
```python
# Same wire-format gate as entry_eval_p_value / endgame_score_p_value
# (PVALUE_RELIABILITY_MIN_N, currently 10 — REVIEW IN-01 carry-forward).
entry_expected_score_p_value: float | None = (
    p_ex_raw if ex_n >= PVALUE_RELIABILITY_MIN_N else None
)
```

**Existing response construction with sibling fields (lines 2302-2322):**
```python
return EndgamePerformanceResponse(
    ...
    achievable_score_gap=achievable_score_gap,
    achievable_score_gap_p_value=achievable_p,
    achievable_score_gap_ci_low=achievable_ci_low,
    achievable_score_gap_ci_high=achievable_ci_high,
)
```

**Copy pattern as:**
```python
from app.services.global_percentile_cdf import interpolate_percentile

# After the existing achievable_score_gap computation, before constructing the response:
achievable_score_gap_percentile: float | None = (
    interpolate_percentile("achievable_score_gap", achievable_score_gap)
    if ex_n >= PVALUE_RELIABILITY_MIN_N
    else None
)

return EndgamePerformanceResponse(
    ...
    achievable_score_gap_percentile=achievable_score_gap_percentile,
)
```

---

### `app/services/endgame_service.py` — site B: `_compute_score_gap_material` (~line 1310-1390)

**Analog (self) — existing dual-N data already in scope (lines 1318-1333):**
```python
score_difference = endgame_score - non_endgame_score

# Phase 85.1: independent two-sample z-test on the chess-score difference.
# Helper gates p_value at min(eg, ne) >= PVALUE_RELIABILITY_MIN_N=10 ...
score_diff_p, score_diff_ci_low, score_diff_ci_high = compute_score_difference_test(
    endgame_wdl.wins, endgame_wdl.draws, endgame_wdl.losses, endgame_wdl.total,
    non_endgame_wdl.wins, non_endgame_wdl.draws, non_endgame_wdl.losses, non_endgame_wdl.total,
)
```

**Existing per-bucket Section 2 fields already unpacked (lines 1352-1354):**
```python
conv_mean, conv_n, conv_p, conv_ci_lo, conv_ci_hi = per_bucket["conversion"]
parity_mean, parity_n, parity_p, parity_ci_lo, parity_ci_hi = per_bucket["parity"]
recov_mean, recov_n, recov_p, recov_ci_lo, recov_ci_hi = per_bucket["recovery"]
```

**Copy pattern as:**
```python
# Dual-N gate per CONTEXT D-10 — both wings of the gap must clear the floor.
score_gap_percentile: float | None = (
    interpolate_percentile("score_gap", score_difference)
    if min(endgame_wdl.total, non_endgame_wdl.total) >= PVALUE_RELIABILITY_MIN_N
    else None
)

# Section 2 single-N gates (mirror the existing _p_value / _ci_* gates on the
# same conv_n / parity_n; guard mean is not None because _compute_per_bucket_score_gap
# returns mean=None on empty cohorts and interpolate_percentile crashes on None).
section2_score_gap_conv_percentile: float | None = (
    interpolate_percentile("section2_score_gap_conv", conv_mean)
    if conv_mean is not None and conv_n is not None and conv_n >= PVALUE_RELIABILITY_MIN_N
    else None
)
section2_score_gap_parity_percentile: float | None = (
    interpolate_percentile("section2_score_gap_parity", parity_mean)
    if parity_mean is not None and parity_n is not None and parity_n >= PVALUE_RELIABILITY_MIN_N
    else None
)

return ScoreGapMaterialResponse(
    ...
    score_gap_percentile=score_gap_percentile,
    section2_score_gap_conv_percentile=section2_score_gap_conv_percentile,
    section2_score_gap_parity_percentile=section2_score_gap_parity_percentile,
)
```

---

### `tests/schemas/test_endgames_schema.py` (test, unit)

**Analog (self) — existing field-presence assertion pattern (lines 24-38):**
```python
class TestScoreGapMaterialResponseSkillDropped:
    """SC#1 (backend, inherited from Phase 78): Skill composite fields stay off-wire."""

    def test_score_gap_response_drops_skill_fields(self) -> None:
        keys = set(ScoreGapMaterialResponse.model_fields.keys())
        forbidden = {
            "section2_score_gap_skill_mean",
            ...
        }
        leaked = forbidden & keys
        assert leaked == set(), f"Skill fields still present on wire: {leaked}"
```

**Copy pattern as (presence assertion, inverse of the `forbidden` shape):**
```python
class TestPercentileFieldsPresent:
    """Phase 94: 4 new `_percentile` fields must be on the wire."""

    def test_score_gap_response_has_percentile_fields(self) -> None:
        keys = set(ScoreGapMaterialResponse.model_fields.keys())
        required = {
            "score_gap_percentile",
            "section2_score_gap_conv_percentile",
            "section2_score_gap_parity_percentile",
        }
        missing = required - keys
        assert missing == set(), f"Percentile fields missing: {missing}"

    def test_performance_response_has_percentile_field(self) -> None:
        keys = set(EndgamePerformanceResponse.model_fields.keys())
        assert "achievable_score_gap_percentile" in keys
```

---

### `tests/test_endgame_service.py` (test, unit — gate semantics)

**Analog:** existing gate tests in the same file (search for `PVALUE_RELIABILITY_MIN_N` references; standard pattern is "construct fixture with n=9 → assert None; n=10 → assert not None"). The test scaffolding follows the same `async def test_*` + AsyncSession fixture pattern as the rest of `test_endgame_service.py`.

**Cases to cover (per RESEARCH §Validation Architecture):**
- 3 single-N gates: `n=9 → None`, `n=10 → not None` for achievable_score_gap, section2_score_gap_conv, section2_score_gap_parity.
- 1 dual-N gate (Endgame Score Gap): `endgame_total=9, non_endgame_total=10 → None`; `endgame_total=10, non_endgame_total=9 → None`; `endgame_total=10, non_endgame_total=10 → not None`.

---

### `frontend/src/types/endgames.ts` (type mirror, manual)

**Analog (self) — existing field declarations on `EndgamePerformanceResponse` (lines 112-115):**
```typescript
achievable_score_gap: number;
achievable_score_gap_p_value: number | null;
achievable_score_gap_ci_low: number | null;
achievable_score_gap_ci_high: number | null;
```

**Copy pattern as (4 nullable scalars; 1 on `EndgamePerformanceResponse`, 3 on `ScoreGapMaterialResponse`):**
```typescript
// On EndgamePerformanceResponse (after line 115):
achievable_score_gap_percentile: number | null;

// On ScoreGapMaterialResponse (next to score_difference_* and section2_score_gap_*_p_value siblings):
score_gap_percentile: number | null;
section2_score_gap_conv_percentile: number | null;
section2_score_gap_parity_percentile: number | null;
```

NOTE (RESEARCH Pitfall 4): the project does NOT run OpenAPI codegen — these mirror edits are mandatory; without them TS2339 errors will break `npm run build`.

---

### `frontend/src/components/charts/PercentileChip.tsx` (NEW component)

**Analog:** `frontend/src/components/popovers/MetricStatPopover.tsx` — reuse the **popover shell mechanics** verbatim (Radix Root + Trigger asChild + Portal + Content + 100ms hover delay + animation classes). The chip pill itself is bespoke.

**Imports pattern (from `MetricStatPopover.tsx` lines 17-26):**
```tsx
import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
```

**Copy pattern as (swap HelpCircle for chip pill; add Flame import):**
```tsx
import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Flame } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ZONE_DANGER, ZONE_SUCCESS, GAUGE_NEUTRAL } from '@/lib/theme';
```

**Hover-open delay + state mechanic (from `MetricStatPopover.tsx` lines 28, 45-55) — copy verbatim:**
```tsx
const HOVER_OPEN_DELAY_MS = 100;

const [open, setOpen] = React.useState(false);
const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

const handleMouseEnter = (): void => {
  hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
};
const handleMouseLeave = (): void => {
  if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  setOpen(false);
};
```

**Trigger pattern (from `MetricStatPopover.tsx` lines 57-74) — swap the inner content from `<HelpCircle />` to the chip pill (banded `style={{ backgroundColor }}` + flame stack + label):**
```tsx
<PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
  <PopoverPrimitive.Trigger asChild>
    <span
      role="button"
      tabIndex={0}
      className={cn(
        'inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer',
        triggerClassName,
      )}
      aria-label={ariaLabel}
      data-testid={testId}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <HelpCircle className="h-4 w-4" />
    </span>
  </PopoverPrimitive.Trigger>
```

→ becomes (chip pill, per UI-SPEC `## Component Inventory`):
```tsx
<PopoverPrimitive.Trigger asChild>
  <span
    role="button"
    tabIndex={0}
    aria-label={`${metricLabel} percentile: ${label}`}
    data-testid={testId}
    onMouseEnter={handleMouseEnter}
    onMouseLeave={handleMouseLeave}
    className={cn(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-sm font-normal cursor-pointer',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    )}
    style={{ backgroundColor: bandColor, color: 'oklch(0.98 0 0)' }}
  >
    {flameCount > 0 && (
      <span className="inline-flex" aria-hidden="true">
        {Array.from({ length: flameCount }).map((_, i) => (
          <Flame key={i} className="h-3 w-3" />
        ))}
      </span>
    )}
    <span>{label}</span>
  </span>
</PopoverPrimitive.Trigger>
```

**Portal + Content shell (from `MetricStatPopover.tsx` lines 75-93) — copy verbatim, swap body component:**
```tsx
<PopoverPrimitive.Portal>
  <PopoverPrimitive.Content
    side="top"
    sideOffset={4}
    onMouseEnter={() => {
      if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    }}
    onMouseLeave={handleMouseLeave}
    className={cn(
      'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
      'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
      'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
      'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
      'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
    )}
    data-testid={`${testId}-popover`}
  >
    <PercentileChipPopoverBody flavor={flavor} />
  </PopoverPrimitive.Content>
</PopoverPrimitive.Portal>
```

**Named constants pattern (per CLAUDE.md "No magic numbers" + UI-SPEC §Named Constants):**
```tsx
const PERCENTILE_BAND_LOW = 25;
const PERCENTILE_BAND_HIGH = 75;
const FLAME_TIER_1 = 90;
const FLAME_TIER_2 = 95;
const FLAME_TIER_3 = 99;
const HOVER_OPEN_DELAY_MS = 100;
```

**Helper functions (pure, per RESEARCH §Pattern 3):**
```tsx
function deriveBandColor(pct: number): string {
  if (pct < PERCENTILE_BAND_LOW) return ZONE_DANGER;
  if (pct > PERCENTILE_BAND_HIGH) return ZONE_SUCCESS;
  return GAUGE_NEUTRAL;
}

function deriveFlameCount(pct: number): 0 | 1 | 2 | 3 {
  if (pct >= FLAME_TIER_3) return 3;
  if (pct >= FLAME_TIER_2) return 2;
  if (pct >= FLAME_TIER_1) return 1;
  return 0;
}

function formatTopXPercent(pct: number): string {
  // Math.max(1, …) prevents "Top 0%" at p99.9 (RESEARCH §Pitfall 7).
  return `Top ${Math.max(1, Math.round(100 - pct))}%`;
}
```

---

### `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` (MOD — add `chipSlot?: ReactNode`)

**Analog (self) — existing optional slot-prop pattern at lines 50-54:**
```tsx
/** Optional left slot rendered before the center label group. Used by
 *  EndgameTypeCard to show the Start predicted score. Defaults to undefined
 *  (renders nothing) so the 3 other callers remain pixel-identical. */
startSlot?: ReactNode;
/** Optional right slot rendered after the center label group. Used by
 *  EndgameTypeCard to show the End predicted score. Defaults to undefined
 *  (renders nothing) so the 3 other callers remain pixel-identical. */
endSlot?: ReactNode;
```

**Existing single-line render branch (lines 97-108) where chip insertion happens:**
```tsx
<span className="flex items-center gap-1 text-sm tabular-nums w-full">
  <span className="text-muted-foreground">{label}</span>
  <span
    className={`font-semibold${valueClassName ? ` ${valueClassName}` : ''}`}
    style={resultColor ? { color: resultColor } : undefined}
    data-testid={valueTestId}
  >
    {formatted}
  </span>
  {tooltip}
</span>
```

**Copy pattern as (insert `chipSlot` wrapped in `ml-auto` between value and tooltip; preserve `hasSlots` branch identically):**
```tsx
// New prop on the interface (mirror the startSlot/endSlot docblock):
/** Optional chip rendered after the value, right-aligned via `ml-auto`,
 *  before the existing tooltip. Used by EndgameOverallPerformanceSection
 *  and EndgameMetricCard to show a PercentileChip. Defaults to undefined
 *  so EndgameTypeCard + Recovery card render pixel-identical. */
chipSlot?: ReactNode;
```

```tsx
// Inside the single-line render branch:
<span className="flex items-center gap-1 text-sm tabular-nums w-full">
  <span className="text-muted-foreground">{label}</span>
  <span
    className={`font-semibold${valueClassName ? ` ${valueClassName}` : ''}`}
    style={resultColor ? { color: resultColor } : undefined}
    data-testid={valueTestId}
  >
    {formatted}
  </span>
  {chipSlot && <span className="ml-auto">{chipSlot}</span>}
  {tooltip}
</span>
```

NOTE (RESEARCH §Pitfall 2): default `undefined` is the SAFETY GUARD — `EndgameTypeCard.tsx` (per-type cards, out of scope) calls `ScoreGapRow` and must keep rendering with no chip.

---

### `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` (MOD — pass chipSlot to 2 ScoreGapRow calls)

**Analog (self) — existing ScoreGapRow call site already has `tooltip` slot wired to `MetricStatPopover`.**

**Copy pattern as (conditional chip on the 2 in-scope page-level rows):**
```tsx
import { PercentileChip } from './PercentileChip';

<ScoreGapRow
  label="Endgame Score Gap:"
  // ... existing props ...
  chipSlot={
    scoreGap.score_gap_percentile != null ? (
      <PercentileChip
        percentile={scoreGap.score_gap_percentile}
        flavor="skill-isolating"
        metricLabel="Endgame Score Gap"
        testId="endgame-score-gap-percentile-chip"
      />
    ) : undefined
  }
  tooltip={/* existing MetricStatPopover — unchanged */}
/>

<ScoreGapRow
  label={/* Achievable Score Gap label */}
  // ... existing props ...
  chipSlot={
    data.achievable_score_gap_percentile != null ? (
      <PercentileChip
        percentile={data.achievable_score_gap_percentile}
        flavor="skill-isolating"
        metricLabel="Achievable Score Gap"
        testId="achievable-score-gap-percentile-chip"
      />
    ) : undefined
  }
  tooltip={/* existing MetricStatPopover — unchanged */}
/>
```

---

### `frontend/src/components/charts/EndgameMetricCard.tsx` (MOD — pass chipSlot to inner ScoreGapRow, bucket-routed)

**Analog (self) — existing ScoreGapRow call site at lines 205-242 (full structure already in place with `tooltip` slot):**
```tsx
{showGapRow && (
  <div data-testid={`${tileTestId}-score-gap-bullet`}>
    <ScoreGapRow
      label={...}
      value={displayedValue}
      formatted={gapFormatted}
      resultColor={gapColor}
      valueTestId={`${tileTestId}-score-gap-value`}
      ariaLabel={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap: ${gapFormatted}`}
      neutralMin={displayedNeutralMin}
      neutralMax={displayedNeutralMax}
      ciLow={scoreGapCiLow != null ? scoreGapCiLow + displayShift : undefined}
      ciHigh={scoreGapCiHigh != null ? scoreGapCiHigh + displayShift : undefined}
      tooltip={
        <MetricStatPopover ... />
      }
    />
  </div>
)}
```

**Copy pattern as (add new prop `scoreGapPercentile: number | null` to `EndgameMetricCardProps`; bucket-routed chip + flavor; Recovery is statically excluded):**
```tsx
// New prop on the interface:
scoreGapPercentile: number | null;

// In the JSX inside the existing ScoreGapRow call:
chipSlot={
  scoreGapPercentile != null && bucket !== 'recovery' ? (
    <PercentileChip
      percentile={scoreGapPercentile}
      flavor={bucket === 'conversion' ? 'improvement-focus' : 'skill-isolating'}
      metricLabel={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap`}
      testId={`${tileTestId}-percentile-chip`}
    />
  ) : undefined
}
```

**Parent (`EndgameMetricsSection.tsx`) routes the new prop per bucket:**
```tsx
<EndgameMetricCard bucket="conversion" ... scoreGapPercentile={scoreGap.section2_score_gap_conv_percentile} />
<EndgameMetricCard bucket="parity"     ... scoreGapPercentile={scoreGap.section2_score_gap_parity_percentile} />
<EndgameMetricCard bucket="recovery"   ... scoreGapPercentile={null} />
```

NOTE (RESEARCH §Pitfall 5): the `bucket !== 'recovery'` guard inside the chip conditional is **defensive** — even if a future CDF expansion adds a recovery percentile, the chip stays suppressed for the recovery bucket.

---

### `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` (NEW test file)

**Analog:** `frontend/src/components/charts/__tests__/EndgameOverallScoreGapRow.test.tsx` (lines 1-80).

**Test scaffolding pattern — vitest jsdom + matchMedia stub + ResizeObserver stub + cleanup after each (verbatim from analog lines 1-53):**
```tsx
// @vitest-environment jsdom
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

import { PercentileChip } from '../PercentileChip';
```

**Test body pattern (mirroring `EndgameOverallScoreGapRow.test.tsx` `describe` + `it` structure):**
```tsx
describe('PercentileChip', () => {
  it('renders "Top X%" with rounded integer percent', () => {
    render(<PercentileChip percentile={73} flavor="skill-isolating" metricLabel="X" testId="chip" />);
    expect(screen.getByTestId('chip')).toHaveTextContent('Top 27%');
  });

  it('floors at "Top 1%" for percentile near 100 (p99.9 -> Top 1%, not Top 0%)', () => { ... });

  it('routes red band for percentile < 25', () => {
    const { getByTestId } = render(<PercentileChip percentile={10} ... />);
    expect(getByTestId('chip').style.backgroundColor).toBeTruthy(); // assert oklch token presence
  });

  it('routes 3 flames at percentile >= 99', () => { ... });
  it('routes 0 flames at percentile < 90', () => { ... });

  it('renders skill-isolating popover copy when flavor="skill-isolating"', () => { ... });
  it('renders improvement-focus popover copy when flavor="improvement-focus"', () => { ... });
});
```

**Companion modifications:**
- `EndgameOverallPerformanceSection.test.tsx` — extend with `assert chip present when percentile non-null; assert absent when null`.
- `EndgameMetricCard.test.tsx` — extend with `assert chip on bucket="conversion" + bucket="parity"; assert NO chip on bucket="recovery" even with non-null percentile` (defensive guard per Pitfall 5).

---

## Shared Patterns

### Theme color tokens
**Source:** `frontend/src/lib/theme.ts` lines 32-46.
**Apply to:** `PercentileChip.tsx` (chip background fill).
```tsx
import { ZONE_DANGER, ZONE_SUCCESS, GAUGE_NEUTRAL } from '@/lib/theme';

// Available constants (already used by IQR zone bands on the same cards):
// ZONE_DANGER  = WDL_LOSS = 'oklch(0.50 0.15 25)'   (red)
// ZONE_SUCCESS = WDL_WIN  = 'oklch(0.50 0.14 145)'  (green)
// GAUGE_NEUTRAL          = 'oklch(0.55 0.18 260)'   (blue — preferred per UI-SPEC §Color Assumption A2)
// ZONE_NEUTRAL           = 'oklch(0.50 0.14 260)'   (alternative blue; slightly different shade)
```

### Reliability gate constant
**Source:** `app/services/endgame_service.py:205` — `PVALUE_RELIABILITY_MIN_N: int = 10`.
**Apply to:** all 4 percentile compute sites in `endgame_service.py`. NEVER hard-code `10` — always import the named constant.

### `interpolate_percentile` helper
**Source:** `app/services/global_percentile_cdf.py:592` — `def interpolate_percentile(metric_id: MetricId, value: float) -> float | None`.
**Apply to:** both compute sites (`_compute_score_gap_material`, `_get_endgame_performance_from_rows`). Returns `None` for unknown metric IDs and NaN input — but the reliability gate is layered separately (RESEARCH §Pitfall 6).

### `data-testid` naming convention
**Source:** CLAUDE.md Browser Automation Rules + UI-SPEC §Data-TestID Contract.
**Apply to:** every chip render site.
- Chip trigger: `{metric-kebab}-percentile-chip` (e.g. `endgame-score-gap-percentile-chip`, `achievable-score-gap-percentile-chip`, `{tileTestId}-percentile-chip`).
- Chip popover: same with `-popover` suffix.

### `aria-label` on icon/chip-only triggers
**Source:** CLAUDE.md Browser Automation Rule 3.
**Apply to:** the chip trigger `<span role="button">`.
- Pattern: `aria-label={`${metricLabel} percentile: Top ${x}%`}`.

### Popover hover-open timing
**Source:** `MetricStatPopover.tsx:28` — `HOVER_OPEN_DELAY_MS = 100`.
**Apply to:** `PercentileChip.tsx`. Same constant name. Same setTimeout + clearTimeout mechanic. Same `onOpenChange` for tap on mobile.

### Pydantic field-shape convention
**Source:** existing `*_p_value` / `*_ci_*` sibling groups on `EndgamePerformanceResponse` (lines 241-254) and `ScoreGapMaterialResponse` (lines 421-455).
**Apply to:** all 4 new `*_percentile` fields. `float | None = None` default. Triple-quoted docstring describing the gate semantics and the value range (`[0, 100]`).

### Frontend vitest test scaffolding
**Source:** `EndgameOverallScoreGapRow.test.tsx` lines 1-53.
**Apply to:** `PercentileChip.test.tsx` (NEW) + extended assertions in `EndgameOverallPerformanceSection.test.tsx` / `EndgameMetricCard.test.tsx`. Same matchMedia/ResizeObserver stubs, same `afterEach(() => { cleanup(); vi.clearAllMocks(); })`.

### Pydantic schema-presence test
**Source:** `tests/schemas/test_endgames_schema.py` lines 24-38.
**Apply to:** new `TestPercentileFieldsPresent` class. Same `set(Response.model_fields.keys())` introspection. Same "required − keys == set()" assertion shape.

---

## No Analog Found

None — every file in scope has a close in-codebase analog (most are self-extensions of existing patterns within the same file).

---

## Metadata

**Analog search scope:** `app/services/`, `app/schemas/`, `frontend/src/components/charts/`, `frontend/src/components/popovers/`, `frontend/src/components/ui/`, `frontend/src/lib/`, `frontend/src/types/`, `tests/`.
**Files inspected directly:** 9 (CONTEXT.md, RESEARCH.md, UI-SPEC.md, `MetricStatPopover.tsx`, `EndgameOverallScoreGapRow.tsx`, `EndgameOverallScoreGapRow.test.tsx`, `EndgameMetricCard.tsx` (relevant section), `EndgameMetricCard.test.tsx` (header), `endgames.py` (relevant section), `endgame_service.py` (2 relevant sections), `test_endgames_schema.py`, `theme.ts` (grep), `endgames.ts` (relevant section)).
**Pattern extraction date:** 2026-05-23

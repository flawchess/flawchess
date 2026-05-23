# Phase 94: Backend & Frontend Percentile Annotations - Research

**Researched:** 2026-05-23
**Domain:** Python/FastAPI Pydantic schema extension + React/TypeScript pill component + Radix popover trigger swap
**Confidence:** HIGH (codebase fully readable, all decisions locked, helper already shipped and tested)

## Summary

Phase 94 is a **plumbing phase**, not a design phase. Phase 93 already shipped `interpolate_percentile(metric_id, value) -> float | None` over a 99-breakpoint CDF for the 4 in-scope metrics; the helper, the registry, the audit-trail constants, and the test suite (`tests/services/test_global_percentile_cdf.py`) are all live and green. CONTEXT.md locks every shape decision worth disagreeing about (chip styling, popover trigger, banded color tokens, flame icon tiers, popover flavors, reliability gate floor at `PVALUE_RELIABILITY_MIN_N = 10`). The phase's risk surface is **discovery-driven**: the planner must hit several non-obvious facts about the codebase that contradict surface readings of CONTEXT.md / SEED-019.

**Top discrepancies the planner must absorb (covered in detail below):**

1. The wire-format field for "Endgame Score Gap" is `score_difference` (not `score_gap`). MetricId `score_gap` keys the CDF registry, but the Pydantic field next to which `score_gap_percentile` lands is `score_difference` (with siblings `score_difference_p_value` / `score_difference_ci_low` / `score_difference_ci_high`). The new field name diverges from the existing wire convention by design (CONTEXT D-11 explicitly names it `score_gap_percentile`).
2. The frontend file CONTEXT.md / SEED-019 calls `EndgameOverallScoreGapRow.tsx` is a **shared generic row primitive** (`ScoreGapRow` component). The actual page-level chip insertion site is the **orchestrator** `EndgameOverallPerformanceSection.tsx`. `ScoreGapRow` is also consumed by `EndgameTypeCard.tsx` (per-type cards, **explicitly out of scope for Phase 94**) — any chip slot added to `ScoreGapRow` must be optional and default-off.
3. TypeScript types are **manually maintained** in `frontend/src/types/endgames.ts`, not generated from OpenAPI. The planner must include a TS-type update task; new fields will NOT appear automatically.
4. The Section 2 cards apply a presentation-only **`SECTION2_DISPLAY_SHIFT`** affine (Conv −0.055, Parity 0, Recov +0.06) to the displayed value, neutral band, and CI bounds. The chip percentile must be computed from the **raw** `gapMean`, not the shifted `displayedValue` — otherwise the percentile compares a shifted user value against an unshifted CDF.
5. There is no FastAPI/OpenAPI contract test. There IS a tiny schema-test pattern at `tests/schemas/test_endgames_schema.py` that asserts Pydantic field presence; the planner should extend it for the 4 new fields.
6. `PVALUE_RELIABILITY_MIN_N` lives in `app/services/endgame_service.py:205`. The page-level Endgame Score Gap's existing dual-gate uses `endgame_wdl.total` AND `non_endgame_wdl.total` (there is no `endgame_n` field on the response — those values come from the nested `EndgameWDLSummary` sub-objects). The chip gate must mirror this same dual-N pattern.

**Primary recommendation:** 3-plan slice — (1) backend: 4 new nullable schema fields + wire-up at 2 compute sites + tests, (2) frontend: `PercentileChip` component + popover shell + manual TS-type update, (3) frontend: wire chip into the 4 target rows (2 in orchestrator, 2 in `EndgameMetricCard` via `ScoreGapRow` optional slot prop). LLM payload is Phase 95 — DO NOT touch.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Chip styling + popover trigger (discussed)**
- **D-01: Chip is the popover trigger.** Tap/hover the chip itself opens the popover. NO adjacent HelpCircle next to the chip. The chip carries semantic meaning ("top X%") rather than being decorative metadata, so it makes sense to read as a tappable element directly. This is a deliberate deviation from the existing `MetricStatPopover` HelpCircle-trigger pattern.
- **D-02: Banded color zones from `theme.ts`** — three discrete bands:
  - Percentile <p25 → theme red
  - Percentile p25..p75 → theme neutral
  - Percentile >p75 → theme green
  (Existing `theme.ts` semantic colors — danger / muted / success / similar. Planner picks the exact constants to reuse; no new theme colors introduced.)
- **D-03: Lucide `Flame` icons stack inside the chip** for the top-percentile tiers (top 10% / 5% / 1%):
  - Top 10% (percentile ≥90) → 1 flame
  - Top 5% (percentile ≥95) → 2 flames
  - Top 1% (percentile ≥99) → 3 flames
  Flames stack additively (render the highest tier only). Bottom tiers get no icon. Lucide `Flame` from `lucide-react`.
- **D-04: Pill/badge with colored background fill.** Rounded background in the banded color (red / neutral / green), contrasting text. Theme drives both background and text colors (no hard-coded values).
- **D-05: Inline, right-aligned on the row.** Metric value on the left edge of the row, chip floats to the right edge. Mobile parity at 375px; wrap to next line at narrow widths is acceptable.

**Phrasing + sign conventions (locked by ROADMAP / REQUIREMENTS)**
- **D-06: "Top X%" phrasing always.** NO "bottom Y%" wording anywhere. A user at p1 → "top 99%"; at p99 → "top 1%"; at p50 → "top 50%". Honest rounding (no spurious decimals — "top 0.1%" not "top 0.137%"). Locked by PCTL-03.
- **D-07: Render literally near the median.** "Top 49% / 50% / 51%" render exactly as the rounded value indicates; no neutral "≈ average" band suppresses the label.

**Metric-aware popover framing (locked)**
- **D-08: Two popover flavors, metric-routed.**
  - Skill-isolating — Endgame Score Gap, Achievable Score Gap, Parity ΔES (d ≤ 0.32): "Where you rank vs all players. Mostly independent of rating — reveals endgame ability separate from overall strength."
  - Improvement-focus — Conversion ΔES only (d = 1.37, skew −0.95): "Where you rank vs all players. Conversion tracks rating closely — if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO."
  Both flavors visible side-by-side on the same Stats page must read as deliberate companions, not contradictions.
- **D-09: Conversion ΔES chip renders at all percentiles** (no suppression in the right tail, no percentile capping).

**Reliability gating + schema shape (locked)**
- **D-10: Per-metric minimum-N reliability gate.**
  - Endgame Score Gap — gated on `endgame_n` AND `non_endgame_n` (both wings must clear the floor).
  - Achievable Score Gap — gated on the endgame-entry span count.
  - Section 2 Parity ΔES — gated on the parity span count (same `_n` already used for `_p_value` / `_ci_*`).
  - Section 2 Conversion ΔES — gated on the conversion span count.
  Recommended default: reuse `PVALUE_RELIABILITY_MIN_N = 10` from `app/services/endgame_service.py:205`. Planner may argue for a stricter per-metric floor if Phase 93's CDF-generation inclusion floors reveal a sharper threshold.
- **D-11: `{metric_id}_percentile` field naming convention.** Nullable `float | None` in [0, 100]. Field names mirror the `MetricId` literal exactly:
  - `score_gap_percentile` (on `ScoreGapMaterialResponse` — see Pitfall 1; name diverges from existing `score_difference_*` sibling)
  - `achievable_score_gap_percentile` (on `EndgamePerformanceResponse`)
  - `section2_score_gap_parity_percentile` (on `ScoreGapMaterialResponse`)
  - `section2_score_gap_conv_percentile` (on `ScoreGapMaterialResponse`)

**Phase 93 inheritance (locked)**
- **D-12: 4-metric scope is fixed.** Endgame Score Gap, Achievable Score Gap, Section 2 Parity ΔES, Section 2 Conversion ΔES. No chip on Recovery ΔES, no chip on the 3 raw % gauges, no chip on per-type cards / timelines / Time Pressure.
- **D-13: Backend imports `interpolate_percentile` from `app/services/global_percentile_cdf.py`.** No re-implementation.

### Claude's Discretion

- The exact `theme.ts` constant names to reuse for the red / neutral / green chip bands (recommend reusing the existing gauge-zone palette — semantic danger / muted / success roles).
- The exact pill background opacity / contrast / padding / size.
- Whether the flame icon stacks horizontally inline (`<Flame /><Flame /><Flame />`) or compresses (e.g. a single flame with a "×3" suffix). Recommend horizontal stacking.
- The reliability-floor value (default `PVALUE_RELIABILITY_MIN_N = 10`).
- Where the chip component lives — recommend `frontend/src/components/charts/PercentileChip.tsx` (sibling of `EndgameOverallScoreGapRow.tsx`).
- The exact popover copy strings (within `feedback_popover_copy_minimalism.md` discipline).
- Whether to add a UI test exercising the gate-below-N case — recommend yes.

### Deferred Ideas (OUT OF SCOPE)

- LLM payload + prompt rework consuming the percentiles → Phase 95 (LLM-05).
- Per-type-card percentile chips (rook / minor / pawn / queen / mixed) → future phase with hard sample gate.
- Opening Insights percentile annotations → future Opening Insights v2 milestone.
- Recovery ΔES chip → explicitly rejected (opponent-confounded, d=0.95 inverted).
- Client-side CDF viz → would justify TS codegen mirror that Phase 93 dropped.
- Percentile-aware sorting / filtering of per-type cards → future per-type phase.
- Conversion ΔES tail suppression / capping → accepted as honest distribution per D-09.
- Neutral "≈ average" band near the median → rejected per D-07.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PCTL-02 | Backend interpolates user value against CDF and emits a nullable `{metric}_percentile` field on the response. Field is `null` when sample size is below the reliability gate. | `interpolate_percentile` already shipped (Pitfall 6 details signature); compute sites identified at `_compute_score_gap_material` (lines 1361–1419 of `endgame_service.py`) and `_get_endgame_performance_from_rows` (lines 2302–2322); gate constant lives at `endgame_service.py:205`. |
| PCTL-03 | Each chipped row renders a compact percentile chip beside the metric value when `{metric}_percentile != null`. "Top X%" phrasing always; honest rounding. | Chip text formula: `pct >= 50 ? "top " + Math.round(100 - pct) + "%" : "top " + Math.round(100 - pct) + "%"` — both branches collapse to a single formula; render as integer percent. p1 → "top 99%", p50 → "top 50%", p99 → "top 1%". |
| PCTL-04 | Chip popovers carry metric-aware framing: 3 skill-isolating flavors + 1 improvement-focus (Conversion). | Two popover-body variants routed by metric: `<PercentileChipPopover flavor="skill-isolating" \| "improvement-focus" />`. Copy bounded by `feedback_popover_copy_minimalism.md` (WHAT + sign convention only). |
| PCTL-05 | Desktop + mobile parity, theme-driven colors (no hard-coded). | Verify at 375px mobile + desktop; theme tokens documented below (Standard Stack). |
| PCTL-06 | Per-metric minimum-N reliability gate; below the gate, no chip renders and no percentile is emitted. | Gate at the **service layer** (preferred — Pydantic field is `None` on the wire, FE renders nothing automatically). Dual-N gate for Endgame Score Gap; single-N for the other 3. Mirror the existing `_p_value` gate semantics on the same metrics. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Percentile interpolation | API / Backend | — | Pure compute, server-side. Helper already shipped in Phase 93. |
| Reliability gating (N floor) | API / Backend | Frontend (defense-in-depth) | Gate at service layer so the wire `null` becomes the chip-absence signal. FE renders nothing when null — no FE gate logic needed. |
| Schema field emission | API / Backend | — | Pydantic v2 adds 4 nullable fields next to existing siblings; non-breaking. |
| TS type definitions | Frontend (manual edit) | — | Project does NOT use OpenAPI codegen; types are hand-mirrored from Pydantic in `frontend/src/types/endgames.ts`. |
| Chip component (pill + popover trigger + flame icon logic) | Browser / Client | — | Single reusable `PercentileChip` component imported by 2 row components. |
| Per-row chip insertion | Browser / Client | — | Page-level rows live in `EndgameOverallPerformanceSection.tsx` (orchestrator). Section 2 rows live in `EndgameMetricCard.tsx`. `ScoreGapRow` is shared infrastructure — chip slot added as optional prop so per-type cards (`EndgameTypeCard.tsx`) are unaffected. |
| Popover hover/tap mechanics | Browser / Client | — | Reuse the Radix popover shell mechanics from `MetricStatPopover.tsx` (HOVER_OPEN_DELAY_MS=100, Portal + Content sideOffset, animation classes). |

## Project Constraints (from CLAUDE.md)

Directives that the planner must verify the plan honors:

- **ty must pass with zero errors.** All new fields get explicit type annotations. Use `float | None` for the 4 new fields. The narrower `CdfMetricId` Literal (`app/services/global_percentile_cdf.py`) is wider than the `MetricId` accepted by `interpolate_percentile`, so calling it with a `MetricId` value works as designed.
- **No magic numbers.** Extract the chip thresholds (`PERCENTILE_BAND_LOW = 25`, `PERCENTILE_BAND_HIGH = 75`, `FLAME_TIER_1 = 90`, `FLAME_TIER_2 = 95`, `FLAME_TIER_3 = 99`) into named constants in `PercentileChip.tsx` or a sibling `percentileChipConfig.ts`.
- **`noUncheckedIndexedAccess` is enabled.** A flame-tier array lookup (e.g. `FLAMES_BY_TIER[tier]`) returns `T | undefined`. Use `Map.get()` with explicit `?? defaultValue`, or guard with `if`. Avoid array-index access for tier dispatch.
- **Knip runs in CI.** Every new export must be imported somewhere (or marked in a knip-ignore comment). When removing the placeholder chip during iteration, also remove the export.
- **`text-sm` minimum font.** Popover bodies are the project's documented exception (use `text-xs`); the chip pill text must be at least `text-sm`.
- **Theme constants in `theme.ts`.** All chip colors must be imported from `@/lib/theme`. Reuse `ZONE_DANGER` / `ZONE_NEUTRAL` (or `GAUGE_NEUTRAL`) / `ZONE_SUCCESS` per CONTEXT D-02.
- **`data-testid` on every interactive element.** Each chip must have `data-testid` like `percentile-chip-{metric}` and the popover content gets `percentile-chip-popover-{metric}`. `aria-label` required on the chip (it acts as a button via the popover trigger).
- **"Always apply changes to mobile too."** The 4 row insertion sites all render the same JSX on desktop and mobile (these components use Tailwind responsive utilities, not separate mobile components). Verify the chip wraps cleanly at 375px when row gets narrow.
- **Pre-PR checklist.** Plans must include `uv run ruff format`, `uv run ruff check --fix`, `uv run ty check app/ tests/`, `uv run pytest -x`, and (cd frontend && npm run lint && npm test -- --run && npm run knip).
- **`feedback_no_dev_db_reset_in_plans.md`.** Do not gate completion on `bin/reset_db.sh`. Backend tests work against fixtures; frontend tests work against synthetic props.
- **`feedback_llm_significance_signal.md`.** Phase 94 does NOT touch the LLM payload. The chip is a UI-only annotation; LLM-05 is Phase 95's responsibility.
- **`feedback_popover_copy_minimalism.md`.** Popover copy = WHAT + sign convention only. No "sigmoid", no "Wilson", no "n=" callouts inside the percentile popover (the chip carries the comparison; methodology lives elsewhere).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x | Backend HTTP layer | Project default. No router work needed; existing endpoints carry the response schemas that grow new fields. |
| Pydantic | v2 | Schema validation | All endgame schemas use v2 BaseModel with explicit `float \| None = None` defaults. New fields follow the same pattern. |
| SQLAlchemy 2.x async | — | DB access | Not touched by this phase (no migration, no new query). |
| React | 19.2 | UI | Project default. |
| TypeScript | 5.9 | Type safety | `noUncheckedIndexedAccess` enabled. |
| `radix-ui` Popover | ^1.4.3 | Popover primitive | Already wraps `MetricStatPopover`, `InfoPopover`, `AchievableScorePopover`. Reuse the same primitive for the chip's popover. |
| `lucide-react` | ^0.577.0 | Icon library | `Flame` icon is already in the dep; no new package. |
| `class-variance-authority` | ^0.7.1 | Variant styling | Used by `Badge` component (`components/ui/badge.tsx`) — useful for chip variant typing if the planner chooses to extend or imitate Badge. |
| `tailwind-merge` + `clsx` (via `cn()`) | — | Class name composition | All existing chip-like components use `cn()` from `@/lib/utils`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `vitest` + `@testing-library/react` | ^4.1.x / ^16.3 | Frontend tests | Per-component `.test.tsx` files in `__tests__/` siblings. |
| `pytest` | 8.x | Backend tests | Schema tests at `tests/schemas/test_endgames_schema.py`. Service tests at `tests/test_endgame_service.py`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled chip primitive | Extend `components/ui/badge.tsx` via `asChild`/variant prop | Badge variants are pre-styled with `text-xs` and `h-5` — likely too small for the chip + flames combo, and the CLAUDE.md min-`text-sm` rule applies. A bespoke `PercentileChip` with `text-sm` and matching padding is cleaner than fighting Badge's variants. Recommend bespoke. |
| Compute percentile in router | Compute in service (`_compute_score_gap_material` / `_get_endgame_performance_from_rows`) | Service is the canonical home for the existing `_p_value` / `_ci_*` siblings. Stay consistent. |
| Add `endgame_n` / `non_endgame_n` as new fields | Reuse `endgame_wdl.total` / `non_endgame_wdl.total` from the existing nested objects | The existing dual-gate in `compute_score_difference_test` already uses these. Adding new flat `_n` fields would duplicate info on the wire. Reuse. |

**Installation:** No new packages.

**Version verification:** No new packages — all stack pieces already in `package.json` and `pyproject.toml`.

## Package Legitimacy Audit

Not applicable. Phase 94 installs no new packages. All deps (`lucide-react`, `radix-ui`, `class-variance-authority`, `clsx`, `tailwind-merge`) are already in the project lockfile and have been used in production for months.

## Architecture Patterns

### System Architecture Diagram

```
[Endgame Stats Page request]
        │
        ▼
[GET /api/endgames/overview] ── unchanged endpoint
        │
        ▼
[get_endgame_overview (orchestrator)]
        │
        ├── get_endgame_performance ───► _get_endgame_performance_from_rows
        │                                        │
        │                                        │ (existing) compute_paired_difference_test
        │                                        │ (existing) achievable_score_gap, p_value, ci_low/high
        │                                        │ (NEW)  achievable_score_gap_percentile  ← interpolate_percentile("achievable_score_gap", value) gated on ex_n >= MIN_N
        │                                        ▼
        │                                  [EndgamePerformanceResponse + 1 new field]
        │
        ├── _compute_score_gap_material  ───► (existing) compute_score_difference_test
        │                                     (existing) _compute_per_bucket_score_gap
        │                                        │
        │                                        │ (NEW) score_gap_percentile                      ← interpolate_percentile("score_gap", score_difference) gated on min(endgame_wdl.total, non_endgame_wdl.total) >= MIN_N
        │                                        │ (NEW) section2_score_gap_conv_percentile        ← interpolate_percentile("section2_score_gap_conv", conv_mean) gated on conv_n >= MIN_N
        │                                        │ (NEW) section2_score_gap_parity_percentile      ← interpolate_percentile("section2_score_gap_parity", parity_mean) gated on parity_n >= MIN_N
        │                                        ▼
        │                                  [ScoreGapMaterialResponse + 3 new fields]
        │
        ▼
[EndgameOverviewResponse]
        │
        ▼ wire (JSON)
[Frontend]
        │
        ├── EndgameOverallPerformanceSection.tsx (orchestrator — reads data, scoreGap)
        │       ├── ScoreGapRow (label="Achievable Score Gap")  ── + new chipSlot prop  ── <PercentileChip percentile={data.achievable_score_gap_percentile} flavor="skill-isolating" />
        │       └── ScoreGapRow (label="Endgame Score Gap")     ── + new chipSlot prop  ── <PercentileChip percentile={scoreGap.score_gap_percentile} flavor="skill-isolating" />
        │
        └── EndgameMetricCard.tsx (parity bucket)                ── + new chipSlot prop on its ScoreGapRow  ── <PercentileChip percentile={section2_score_gap_parity_percentile} flavor="skill-isolating" />
            EndgameMetricCard.tsx (conversion bucket)            ── + new chipSlot prop on its ScoreGapRow  ── <PercentileChip percentile={section2_score_gap_conv_percentile} flavor="improvement-focus" />
            EndgameMetricCard.tsx (recovery bucket)              ── unchanged (no chip)
```

### Recommended Project Structure

```
app/
├── services/
│   ├── endgame_service.py          # MODIFIED — 4 interpolate_percentile() calls + gate logic
│   └── global_percentile_cdf.py    # UNCHANGED (Phase 93 output)
├── schemas/
│   └── endgames.py                 # MODIFIED — 4 new nullable Pydantic fields
tests/
├── schemas/
│   └── test_endgames_schema.py     # MODIFIED — add field-presence assertions
└── test_endgame_service.py         # MODIFIED — add percentile compute + gate tests

frontend/
├── src/
│   ├── components/
│   │   ├── charts/
│   │   │   ├── PercentileChip.tsx                    # NEW — the chip + popover shell + flame logic
│   │   │   ├── PercentileChipPopover.tsx             # NEW (or inline inside PercentileChip) — flavor-routed popover body
│   │   │   ├── EndgameOverallScoreGapRow.tsx         # MODIFIED — optional chipSlot prop (default undefined for backward compat with EndgameTypeCard)
│   │   │   ├── EndgameOverallPerformanceSection.tsx  # MODIFIED — pass chipSlot to both ScoreGapRow calls
│   │   │   ├── EndgameMetricCard.tsx                 # MODIFIED — pass chipSlot to its ScoreGapRow (only for conversion + parity, NOT recovery)
│   │   │   └── __tests__/
│   │   │       ├── PercentileChip.test.tsx           # NEW
│   │   │       ├── EndgameOverallPerformanceSection.test.tsx  # MODIFIED — assert chip presence / absence by gate
│   │   │       └── EndgameMetricCard.test.tsx                 # MODIFIED — assert chip presence / absence by gate
│   │   └── ui/
│   │       └── badge.tsx           # UNCHANGED (reference, not extended)
│   ├── lib/
│   │   ├── theme.ts                # UNCHANGED — chip imports existing ZONE_DANGER / ZONE_SUCCESS / GAUGE_NEUTRAL
│   │   └── percentileChip.ts       # OPTIONAL NEW — pure helpers (formatTopXPercent, deriveBand, deriveFlameTier)
│   └── types/
│       └── endgames.ts             # MODIFIED — 4 new nullable field declarations (manual update; no codegen)
```

### Pattern 1: Backend — service computes + gates + attaches

Phase 87.2 plumbing already establishes this exact pattern for `section2_score_gap_*_p_value` siblings. Mirror it.

```python
# Source: app/services/endgame_service.py (existing pattern, e.g. lines 2287-2289)
# (existing) gate _p_value to None when n < PVALUE_RELIABILITY_MIN_N
entry_expected_score_p_value: float | None = (
    p_ex_raw if ex_n >= PVALUE_RELIABILITY_MIN_N else None
)

# NEW pattern for Phase 94 — identical shape for percentile:
from app.services.global_percentile_cdf import interpolate_percentile

achievable_score_gap_percentile: float | None = (
    interpolate_percentile("achievable_score_gap", achievable_score_gap)
    if ex_n >= PVALUE_RELIABILITY_MIN_N
    else None
)
```

For the page-level Endgame Score Gap (dual-N gate):

```python
score_gap_percentile: float | None = (
    interpolate_percentile("score_gap", score_difference)
    if min(endgame_wdl.total, non_endgame_wdl.total) >= PVALUE_RELIABILITY_MIN_N
    else None
)
```

For Section 2 (single-N gate, reusing the same `conv_n` / `parity_n` already gating their `_p_value` / `_ci_*`):

```python
section2_score_gap_conv_percentile: float | None = (
    interpolate_percentile("section2_score_gap_conv", conv_mean)
    if conv_mean is not None and conv_n >= PVALUE_RELIABILITY_MIN_N
    else None
)
```

Note the additional `conv_mean is not None` guard — `_compute_per_bucket_score_gap` returns `mean_out=None` when the cohort is empty (`endgame_service.py:1248`). `interpolate_percentile` would crash on `None`, so guard explicitly. Same applies to `parity_mean`.

### Pattern 2: Frontend — chip rendered inside ScoreGapRow's tooltip area, then optional chipSlot

Inspecting `ScoreGapRow` (`EndgameOverallScoreGapRow.tsx`), the existing JSX has a clear "after the result value" slot — the `{tooltip}` prop. The minimum-friction plan: add a new optional `chipSlot?: ReactNode` prop placed AFTER the `{formatted}` value, BEFORE the `{tooltip}`. Default `undefined` so the 4th consumer (`EndgameTypeCard.tsx`) renders pixel-identical.

```tsx
// Source: frontend/src/components/charts/EndgameOverallScoreGapRow.tsx (existing structure)
<span className="flex items-center gap-1 text-sm tabular-nums w-full">
  <span className="text-muted-foreground">{label}</span>
  <span
    className={`font-semibold${valueClassName ? ` ${valueClassName}` : ''}`}
    style={resultColor ? { color: resultColor } : undefined}
    data-testid={valueTestId}
  >
    {formatted}
  </span>
  {chipSlot}              {/* NEW — render the chip inline, right after the value */}
  {tooltip}               {/* existing — HelpCircle MetricStatPopover */}
</span>
```

CONTEXT D-05 says "chip floats to the right edge of the row" — but D-05 also says "metric value on the left edge, chip floats to the right edge of the row". The existing ScoreGapRow flex layout has `text-muted-foreground` label + `font-semibold` value + `tooltip` all on a single flex span. To right-align the chip, wrap it in a sibling with `ml-auto`:

```tsx
{chipSlot && <span className="ml-auto">{chipSlot}</span>}
{tooltip}
```

This pushes the chip away from the value and parks it at the row's right edge while the HelpCircle tooltip stays adjacent.

### Pattern 3: Chip component — banded color + flame tier + popover trigger

```tsx
// Source: project conventions (theme.ts + MetricStatPopover.tsx shell pattern)
import { Flame } from 'lucide-react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { ZONE_DANGER, ZONE_SUCCESS, GAUGE_NEUTRAL } from '@/lib/theme';

const PERCENTILE_BAND_LOW = 25;
const PERCENTILE_BAND_HIGH = 75;
const FLAME_TIER_1 = 90;
const FLAME_TIER_2 = 95;
const FLAME_TIER_3 = 99;
const HOVER_OPEN_DELAY_MS = 100;

function deriveBandColor(pct: number): string {
  if (pct < PERCENTILE_BAND_LOW) return ZONE_DANGER;
  if (pct > PERCENTILE_BAND_HIGH) return ZONE_SUCCESS;
  return GAUGE_NEUTRAL;   // or ZONE_NEUTRAL — planner picks the most visually consistent constant
}

function deriveFlameCount(pct: number): 0 | 1 | 2 | 3 {
  if (pct >= FLAME_TIER_3) return 3;
  if (pct >= FLAME_TIER_2) return 2;
  if (pct >= FLAME_TIER_1) return 1;
  return 0;
}

function formatTopXPercent(pct: number): string {
  // pct is the user's percentile in [0, 100]. "top X%" where X = 100 - pct, rounded honestly.
  return `Top ${Math.round(100 - pct)}%`;
}
```

The popover shell follows `MetricStatPopover` mechanics — Radix Root + Trigger asChild + Portal + Content — but the trigger node is the chip pill itself, not a HelpCircle icon. The chip must carry `role="button"`, `tabIndex={0}`, `aria-label`, and `data-testid`.

### Anti-Patterns to Avoid

- **Don't compute percentile on `displayedValue` for Section 2 metrics.** `EndgameMetricCard.tsx` applies `SECTION2_DISPLAY_SHIFT` (Conv −0.055, Parity 0, Recov +0.06) to `gapMean` before rendering. The backend computes percentile from the **raw** `gapMean`. The frontend only consumes the backend's pre-computed percentile scalar; it does not interpolate. So this isn't actually a frontend pitfall — it's only a problem if anyone is tempted to "interpolate locally"; do NOT.
- **Don't extend `MetricStatPopover` with a chip variant.** That popover's contract is "HelpCircle trigger + structured `MetricStatTooltip` body". The chip's content is different (skill-isolating vs. improvement-focus flavor + the "top X%" framing). A separate `PercentileChip` component reads cleaner.
- **Don't right-align the chip with `text-right` or `justify-end` on the parent.** Both would push the HelpCircle tooltip away from the value too. Use `ml-auto` on the chip wrapper specifically.
- **Don't gate the chip in the React component.** The backend emits `null` when the gate fails; the chip's render guard is purely `if (percentile == null) return null;`. Putting the gate in two places risks divergence at the next floor change.
- **Don't add the chip to the `Recovery` bucket** in `EndgameMetricCard.tsx`. The component receives a `bucket: MaterialBucket` prop; the chip-routing logic must skip when `bucket === 'recovery'`. Recommend a per-bucket dispatch in the parent (`EndgameMetricsSection.tsx`) that passes `undefined` for the recovery card's `chipSlot`.
- **Don't add a `score_gap_n` field.** The dual-gate uses `endgame_wdl.total` and `non_endgame_wdl.total`, which are already on the wire via the `EndgameWDLSummary` nested objects on `EndgamePerformanceResponse`. Reuse, don't duplicate. Note: the dual-N is read off `EndgamePerformanceResponse`, NOT `ScoreGapMaterialResponse` — these are sibling fields on the parent `EndgameOverviewResponse`. The backend gate is at the service site (where both objects are in scope at line 1324 already); for the frontend it doesn't matter since the percentile is already gated server-side.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile interpolation | A second `interpolate_percentile` | Import from `app/services/global_percentile_cdf.py` (Phase 93 output) | Already shipped, tested, monotone-invariant-asserted, NaN-safe, edge-clamped. |
| Popover hover/tap mechanics | A new Radix root | Copy `MetricStatPopover.tsx`'s `HOVER_OPEN_DELAY_MS`, Trigger asChild, Portal + Content, animation classes verbatim | The shell mechanics are battle-tested across `MetricStatPopover` / `AchievableScorePopover` / `InfoPopover` (4+ months in production). |
| Flame stacking | Custom icon | Lucide `Flame` rendered 1/2/3 times inline | Already a dep; size with Tailwind (`h-3 w-3` or `h-3.5 w-3.5` per the existing inline-icon convention in `EndgameMetricCard.tsx:191/210`). |
| Banded color logic | New theme entries | Reuse `ZONE_DANGER` / `ZONE_SUCCESS` / `GAUGE_NEUTRAL` from `theme.ts` | Per CONTEXT D-02; existing IQR zone-band palette is the visual language we want to inherit. |
| Manual TS types maintenance | Mirroring fields by hand again | Same hand-edit, no escape | Project does not use OpenAPI codegen. Just be deliberate. |
| Rounding | `toFixed()` (returns string with trailing zeros) | `Math.round()` then template-literal `%` | Per CONTEXT D-06: honest rounding, no spurious decimals. Integer percent only. |

**Key insight:** Phase 93 did the hard work. Phase 94 wires existing helpers into existing schemas + builds one new React component. The chip + popover shell + flame logic is ~150 LOC of bespoke component code; the rest is plumbing.

## Common Pitfalls

### Pitfall 1: Field-name divergence on `ScoreGapMaterialResponse`

**What goes wrong:** CONTEXT D-11 names the new field `score_gap_percentile`. The wire-format sibling for the Endgame Score Gap value is `score_difference`. So we get a schema like:

```python
class ScoreGapMaterialResponse(BaseModel):
    score_difference: float
    score_difference_p_value: float | None = None
    score_difference_ci_low: float | None = None
    score_difference_ci_high: float | None = None
    score_gap_percentile: float | None = None   # NEW — name diverges from siblings on purpose
```

**Why it happens:** The MetricId for the value is `score_gap` (not `score_difference`) — this is the key into `GLOBAL_PERCENTILE_CDF`. CONTEXT.md mandates field names mirror the MetricId.

**How to avoid:** Document this in a docstring on the new field. The planner's PLAN.md must include this exact wording so future reviewers don't "fix" it. Add an assertion in the schema test that both `score_difference` (existing) AND `score_gap_percentile` (new) are present on `ScoreGapMaterialResponse`.

**Warning signs:** Anyone renaming `score_difference` → `score_gap` "for consistency" would break the wire format and break the frontend.

### Pitfall 2: `EndgameOverallScoreGapRow.tsx` is shared infrastructure

**What goes wrong:** Naively reading CONTEXT.md, the planner adds chip-rendering code inside `EndgameOverallScoreGapRow.tsx` itself. But that file exports `ScoreGapRow`, a generic component consumed by FOUR call sites — the 2 page-level rows (in scope) AND 2 sites in `EndgameTypeCard.tsx` (per-type cards, **out of scope**) AND inside `EndgameMetricCard.tsx` (Section 2 cards — 3 buckets, 2 of which are in scope).

**Why it happens:** CONTEXT.md and SEED-019 both say "the chip goes on EndgameOverallScoreGapRow.tsx" — by which they mean the page-level orchestrator (`EndgameOverallPerformanceSection.tsx`) calls `ScoreGapRow` and passes a chip. They do NOT mean "edit `ScoreGapRow` and force all consumers to render a chip."

**How to avoid:** Add `chipSlot?: ReactNode` as an OPTIONAL prop on `ScoreGapRow`. Default `undefined`. Three of the five consumers (`EndgameTypeCard.tsx` and the Recovery bucket of `EndgameMetricCard`) pass `undefined` (or simply omit the prop). The other two pass `<PercentileChip … />`.

**Warning signs:** `EndgameTypeCard.test.tsx` failing after the change — that means the chip is leaking into per-type cards.

### Pitfall 3: Section 2 `SECTION2_DISPLAY_SHIFT` is a presentation affine

**What goes wrong:** The Section 2 chip is computed from the user's `gapMean` for `section2_score_gap_conv` and `section2_score_gap_parity`. The CDF breakpoints (from `app/services/global_percentile_cdf.py`) are in RAW units. The frontend displays `displayedValue = gapMean + SECTION2_DISPLAY_SHIFT[bucket]` — Conv is shifted by −0.055.

If anyone refactors the percentile to be computed on the frontend (e.g. "let's interpolate locally for parity with future client-side viz"), they'd risk computing the percentile against the shifted display value, which is calibrated against the band, NOT the CDF.

**Why it happens:** The display shift is documented in `EndgameMetricCard.tsx:126-150` but it's easy to miss when refactoring.

**How to avoid:** Backend computes percentile from raw `gapMean` and ships the scalar. Frontend NEVER calls `interpolate_percentile` (it doesn't exist in TS — Phase 93 D-01 was explicit about no TS mirror). Document this contract in the chip component's JSDoc: "The `percentile` prop is the backend-computed value in [0, 100]; do not re-derive."

**Warning signs:** Anyone proposing a `frontend/src/lib/percentile.ts` "for parity" — that's the Phase 93 TS-mirror discussion that was explicitly deferred.

### Pitfall 4: TS types are manually maintained

**What goes wrong:** Backend ships the 4 new nullable fields. Frontend never sees them because `frontend/src/types/endgames.ts` is a hand-mirrored copy of the Pydantic schemas. The frontend code that tries to access `data.achievable_score_gap_percentile` will fail TypeScript compilation: "Property 'achievable_score_gap_percentile' does not exist on type 'EndgamePerformanceResponse'."

**Why it happens:** Project does not run OpenAPI codegen. `grep -rn "openapi\|orval\|swagger"` in `frontend/` returns nothing. Types are mirrored by convention.

**How to avoid:** Plan a dedicated frontend task: "Mirror the 4 new backend fields into `frontend/src/types/endgames.ts`." Touch:
- `EndgamePerformanceResponse` interface — add `achievable_score_gap_percentile: number | null;`
- `ScoreGapMaterialResponse` interface — add 3 new fields: `score_gap_percentile`, `section2_score_gap_conv_percentile`, `section2_score_gap_parity_percentile`.

**Warning signs:** `npm run build` (which runs `tsc -b`) failing in CI with TS2339 errors.

### Pitfall 5: Recovery card sits between Conv and Parity but takes no chip

**What goes wrong:** `EndgameMetricCard.tsx` is shared across Conv / Parity / Recov buckets. The `bucket` prop is `MaterialBucket = "conversion" | "parity" | "recovery"`. The Recovery card MUST NOT render a chip.

**Why it happens:** It's tempting to write `<PercentileChip percentile={scoreGapPercentile} />` inside the shared `EndgameMetricCard.tsx` and rely on the percentile being `null` for recovery (because the backend doesn't emit `section2_score_gap_recov_percentile`). But that's a fragile contract — the recovery CDF isn't shipped (Phase 93 D-02 excluded it explicitly), so calling `interpolate_percentile("section2_score_gap_recov", value)` returns `None` because the metric isn't in `GLOBAL_PERCENTILE_CDF`. The backend therefore never emits a recovery percentile. Good. But the frontend still receives the `MaterialBucket` enum and must branch.

**How to avoid:** Either (a) the parent `EndgameMetricsSection.tsx` passes `chipSlot={bucket === 'recovery' ? undefined : <PercentileChip … />}` — explicit at the call site, OR (b) the chip-routing config is a `Record<MaterialBucket, ChipFlavor | undefined>` so the recovery case is statically excluded. Both work; (b) is more declarative.

**Warning signs:** A "recovery chip showing up after a future CDF expansion" — guard against this with an assertion in `EndgameMetricCard.test.tsx`: render with `bucket="recovery"` and a non-null `scoreGapPercentile`, assert no chip rendered (defensive against future "let's add recovery to the CDF" refactors).

### Pitfall 6: `interpolate_percentile` return-None overloads

**What goes wrong:** `interpolate_percentile(metric_id, value) -> float | None` returns `None` in two distinct cases (per the docstring at `global_percentile_cdf.py:592-611`):

1. `metric_id` is not in `GLOBAL_PERCENTILE_CDF` (e.g. "recovery", "endgame_score" — Phase 93 doesn't ship a CDF for them).
2. `value` is NaN.

The reliability gate (N floor) is layered on TOP — the helper itself doesn't gate by N.

**Why it happens:** It's tempting to think the helper does everything. It doesn't. The helper returns a percentile (or None for unknown metric / NaN). The service code must apply the N gate explicitly.

**How to avoid:** Use a clear two-step pattern:
```python
# Always compute, then gate (or gate-then-compute — pick one and stick to it).
# Recommend: gate first, compute second — avoids an unnecessary helper call when the gate fails.
percentile: float | None = (
    interpolate_percentile("score_gap", score_difference)
    if min(endgame_wdl.total, non_endgame_wdl.total) >= PVALUE_RELIABILITY_MIN_N
    else None
)
```

**Warning signs:** A test asserting "percentile is null when n=0" passes because of NaN/unknown — but the test should pass because of the gate, not the helper's edge handling. Write tests that exercise the gate explicitly (n=9 → null; n=10 → not null).

### Pitfall 7: Honest rounding vs. JavaScript `Math.round` half-to-even quirks

**What goes wrong:** `Math.round(0.5)` in JavaScript returns `1` (round half away from zero on positives). `Math.round(-0.5)` returns `0` (round half toward zero on negatives). For "top X%" rendering where X = 100 - pct, edge cases like pct=99.5 → "top 1%" (X = 0.5, rounds to 1) are FINE. But pct=99.4 → X=0.6 → "top 1%"; pct=99.6 → X=0.4 → "top 0%". The "top 0%" case is degenerate — clamp the displayed integer to a minimum of 1.

**Why it happens:** CONTEXT D-06 says "honest rounding, no spurious decimals". A user at p99.9 sees "top 0%" which is meaningless.

**How to avoid:**
```ts
function formatTopXPercent(pct: number): string {
  const x = Math.max(1, Math.round(100 - pct));
  return `Top ${x}%`;
}
```

The `Math.max(1, …)` floor prevents "top 0%". Symmetrically, "top 100%" would happen at pct ≤ 0.5; the CDF helper edge-clamps to 0, so this is "top 100%" — also a valid edge but a user there is the absolute weakest. The default is correct; just ensure the test covers `pct = 0.0` rendering as "Top 100%".

**Warning signs:** A snapshot test showing "Top 0%" — bug.

### Pitfall 8: Both popover flavors visible side-by-side on the same page

**What goes wrong:** CONTEXT D-08 / specifics §4 highlight that the Endgame Score Gap chip (skill-isolating) and the Conversion ΔES chip (improvement-focus) both render for the same user on the same Stats page. The two popover copies must read as deliberate companions, not contradictions.

**Why it happens:** Easy to draft each flavor in isolation. Easy to end up with the skill-isolating chip claiming "this metric is independent of rating" while the improvement-focus chip claims "this metric tracks rating closely" — and the user reads both within 5 seconds of scrolling.

**How to avoid:** Draft both copies side-by-side. Re-read together. The skill-isolating copy says "mostly independent of rating — reveals endgame ability separate from overall strength"; the improvement-focus copy says "tracks rating closely — if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO". They aren't contradictory if the user reads them sequentially; they describe distinct properties of distinct metrics. The plan should call out this UAT check explicitly: "Read both popover copies in sequence — they must feel complementary, not contradictory."

**Warning signs:** UAT feedback "these popovers say opposite things" — rework the copy.

## Runtime State Inventory

Not applicable. Phase 94 is a pure additive plumbing phase — no rename, no migration, no string-replace across the codebase. The 4 new field names are net-new identifiers (not renames). No stored data needs updating. No service registrations change.

**Categories explicitly checked:**
- Stored data: None (no DB schema change, no migration).
- Live service config: None (no n8n / Datadog / Tailscale references).
- OS-registered state: None.
- Secrets / env vars: None.
- Build artifacts: None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 8.x + Pydantic v2 |
| Backend config file | `pytest.ini` / `pyproject.toml` (existing) |
| Backend quick run command | `uv run pytest tests/test_endgame_service.py tests/schemas/test_endgames_schema.py -x` |
| Backend full suite command | `uv run pytest -x` |
| Frontend framework | vitest 4.x + @testing-library/react 16 |
| Frontend config file | `frontend/vitest.config.ts` / `vite.config.ts` (existing) |
| Frontend quick run command | `cd frontend && npm test -- --run PercentileChip EndgameOverallPerformanceSection EndgameMetricCard` |
| Frontend full suite command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PCTL-02 | All 4 fields appear on response schemas | unit (schema) | `uv run pytest tests/schemas/test_endgames_schema.py -x` | Wave 0 — extend existing file |
| PCTL-02 | Backend gates: n=9 → null, n=10 → not null (single-N) | unit (service) | `uv run pytest tests/test_endgame_service.py::test_percentile_gate -x` | Wave 0 — new |
| PCTL-02 | Backend gates: dual-N for Endgame Score Gap | unit (service) | `uv run pytest tests/test_endgame_service.py::test_score_gap_percentile_dual_gate -x` | Wave 0 — new |
| PCTL-03 | "Top X%" formatter rounds honestly + floors at 1 | unit (frontend) | `cd frontend && npm test -- --run percentileChip` | Wave 0 — new |
| PCTL-04 | Skill-isolating vs improvement-focus copy routes by metric | component | `cd frontend && npm test -- --run PercentileChip.test.tsx` | Wave 0 — new |
| PCTL-05 | Chip uses theme tokens, not hard-coded colors | component | Inspect rendered style attribute (or computed color); assert presence of token-derived oklch | Wave 0 — new |
| PCTL-05 | Mobile parity at 375px | smoke (manual UAT) | HUMAN-UAT — load `/endgames` on a 375px viewport, screenshot | Wave 0 — manual |
| PCTL-06 | Chip is absent when `percentile == null` | component | `EndgameOverallPerformanceSection.test.tsx` + `EndgameMetricCard.test.tsx` | Wave 0 — extend existing |
| PCTL-06 | Recovery card never renders a chip | component | `EndgameMetricCard.test.tsx` — render with `bucket="recovery"`, assert no chip | Wave 0 — extend existing |
| (regression) | `interpolate_percentile` returns existing values | unit (service) | `uv run pytest tests/services/test_global_percentile_cdf.py -x` | EXISTS (Phase 93) — no change |
| (regression) | `EndgameTypeCard` renders without chip | component | `EndgameTypeCard.test.tsx` (existing) | EXISTS — must stay green |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_endgame_service.py tests/schemas/test_endgames_schema.py -x` (backend) AND/OR `cd frontend && npm test -- --run <changed components>` (frontend).
- **Per wave merge:** `uv run pytest -x` AND `cd frontend && npm test -- --run`.
- **Phase gate:** Full pre-PR checklist (ruff format + ruff check --fix + ty check + pytest + frontend lint + npm test + knip + build). Plus HUMAN-UAT on a 375px mobile viewport AND a desktop viewport.

### Wave 0 Gaps

- [ ] `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` — new file covering: rendering, "Top X%" formatter, band color routing, flame-tier dispatch, popover-flavor routing.
- [ ] `tests/test_endgame_service.py` — extend with percentile compute + gate tests (4 metrics × 2 gates = 5 distinct gate cases: 3 single-N at n=9/n=10, 1 dual-N at endgame=9/non=10, dual-N at endgame=10/non=9, dual-N at endgame=10/non=10).
- [ ] `tests/schemas/test_endgames_schema.py` — extend with field-presence assertions for 4 new fields (mirroring the existing Phase 87.5 / Phase 78 dropped-field assertion pattern).
- [ ] Existing `EndgameOverallPerformanceSection.test.tsx` (577 LOC) — extend with chip presence/absence assertions.
- [ ] Existing `EndgameMetricCard.test.tsx` (403 LOC) — extend with chip presence/absence assertions + Recovery-no-chip guard.

## Code Examples

### Backend — wire-up at the page-level Endgame Score Gap site

```python
# Source: app/services/endgame_service.py (NEW lines inside _compute_score_gap_material)
from app.services.global_percentile_cdf import interpolate_percentile

# After existing CI / p-value computation, before constructing the response:

# Dual-N gate per CONTEXT D-10 — both wings of the gap must clear the floor.
score_gap_percentile: float | None = (
    interpolate_percentile("score_gap", score_difference)
    if min(endgame_wdl.total, non_endgame_wdl.total) >= PVALUE_RELIABILITY_MIN_N
    else None
)

# Section 2 (single-N, mirrors existing _p_value / _ci_* gate):
section2_score_gap_conv_percentile: float | None = (
    interpolate_percentile("section2_score_gap_conv", conv_mean)
    if conv_mean is not None and conv_n >= PVALUE_RELIABILITY_MIN_N
    else None
)
section2_score_gap_parity_percentile: float | None = (
    interpolate_percentile("section2_score_gap_parity", parity_mean)
    if parity_mean is not None and parity_n >= PVALUE_RELIABILITY_MIN_N
    else None
)

return ScoreGapMaterialResponse(
    # ... all existing fields ...
    score_gap_percentile=score_gap_percentile,
    section2_score_gap_conv_percentile=section2_score_gap_conv_percentile,
    section2_score_gap_parity_percentile=section2_score_gap_parity_percentile,
)
```

### Backend — wire-up at the Achievable Score Gap site

```python
# Source: app/services/endgame_service.py (NEW lines inside _get_endgame_performance_from_rows)
# After the existing achievable_score_gap computation (line ~2279) and before the response build (line ~2302):

# `ex_n` is the same N already gating achievable_score_gap_p_value / _ci_*.
achievable_score_gap_percentile: float | None = (
    interpolate_percentile("achievable_score_gap", achievable_score_gap)
    if ex_n >= PVALUE_RELIABILITY_MIN_N
    else None
)

return EndgamePerformanceResponse(
    # ... all existing fields ...
    achievable_score_gap_percentile=achievable_score_gap_percentile,
)
```

### Backend — new Pydantic field declarations

```python
# Source: app/schemas/endgames.py (NEW field on EndgamePerformanceResponse, ~line 256)
achievable_score_gap_percentile: float | None = None
"""Cohort percentile (0–100) of achievable_score_gap vs the Phase 93 global CDF.
None when ex_n < PVALUE_RELIABILITY_MIN_N (=10) — same reliability gate as
achievable_score_gap_p_value / _ci_*. See app/services/global_percentile_cdf.py
for the breakpoint table; helper is interpolate_percentile()."""

# Source: app/schemas/endgames.py (NEW fields on ScoreGapMaterialResponse, ~line 456)
# Field-name divergence from sibling score_difference_* fields is intentional —
# the field name mirrors MetricId "score_gap" (the CDF key), not the wire-format
# score_difference value. See Phase 94 CONTEXT D-11.
score_gap_percentile: float | None = None
"""Cohort percentile (0–100) of score_difference vs the Phase 93 global CDF.
None when min(endgame_wdl.total, non_endgame_wdl.total) < PVALUE_RELIABILITY_MIN_N
(=10) — same dual-N gate as score_difference_p_value / _ci_*."""

section2_score_gap_conv_percentile: float | None = None
"""Cohort percentile (0–100) of section2_score_gap_conv_mean vs the Phase 93 global CDF.
None when section2_score_gap_conv_n < PVALUE_RELIABILITY_MIN_N (=10) — same
single-N gate as section2_score_gap_conv_p_value / _ci_*."""

section2_score_gap_parity_percentile: float | None = None
"""Cohort percentile (0–100) of section2_score_gap_parity_mean vs the Phase 93 global CDF.
None when section2_score_gap_parity_n < PVALUE_RELIABILITY_MIN_N (=10) — same
single-N gate as section2_score_gap_parity_p_value / _ci_*."""
```

### Frontend — TS type mirror

```typescript
// Source: frontend/src/types/endgames.ts (additions)

// On EndgamePerformanceResponse interface:
achievable_score_gap_percentile: number | null;

// On ScoreGapMaterialResponse interface:
score_gap_percentile: number | null;
section2_score_gap_conv_percentile: number | null;
section2_score_gap_parity_percentile: number | null;
```

### Frontend — PercentileChip component (skeleton)

```tsx
// Source: frontend/src/components/charts/PercentileChip.tsx (NEW)
import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Flame } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ZONE_DANGER, ZONE_SUCCESS, GAUGE_NEUTRAL } from '@/lib/theme';

const HOVER_OPEN_DELAY_MS = 100;
const PERCENTILE_BAND_LOW = 25;
const PERCENTILE_BAND_HIGH = 75;
const FLAME_TIER_1 = 90;
const FLAME_TIER_2 = 95;
const FLAME_TIER_3 = 99;

export type PercentileChipFlavor = 'skill-isolating' | 'improvement-focus';

interface PercentileChipProps {
  percentile: number;          // [0, 100]
  flavor: PercentileChipFlavor;
  metricLabel: string;         // for aria-label + popover heading
  testId: string;
}

export function PercentileChip({ percentile, flavor, metricLabel, testId }: PercentileChipProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const x = Math.max(1, Math.round(100 - percentile));
  const label = `Top ${x}%`;

  const bandColor =
    percentile < PERCENTILE_BAND_LOW
      ? ZONE_DANGER
      : percentile > PERCENTILE_BAND_HIGH
        ? ZONE_SUCCESS
        : GAUGE_NEUTRAL;

  const flameCount: 0 | 1 | 2 | 3 =
    percentile >= FLAME_TIER_3 ? 3 : percentile >= FLAME_TIER_2 ? 2 : percentile >= FLAME_TIER_1 ? 1 : 0;

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };
  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          aria-label={`${metricLabel} percentile: ${label}`}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className={cn(
            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-sm font-medium cursor-pointer',
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
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); }}
          onMouseLeave={handleMouseLeave}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2',
          )}
          data-testid={`${testId}-popover`}
        >
          <PercentileChipPopoverBody flavor={flavor} percentile={percentile} />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

function PercentileChipPopoverBody({ flavor, percentile }: { flavor: PercentileChipFlavor; percentile: number }) {
  // Copy bounded by feedback_popover_copy_minimalism.md (WHAT + sign convention only).
  // Planner finalizes the exact strings — these are placeholders.
  if (flavor === 'skill-isolating') {
    return (
      <p>
        Where you rank vs all players. Mostly independent of rating — reveals endgame ability separate from overall strength.
      </p>
    );
  }
  return (
    <p>
      Where you rank vs all players. Conversion tracks rating closely — if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO.
    </p>
  );
}
```

### Frontend — call site at the page-level orchestrator

```tsx
// Source: frontend/src/components/charts/EndgameOverallPerformanceSection.tsx (MODIFIED)
import { PercentileChip } from './PercentileChip';

// ... existing code ...

<ScoreGapRow
  label={/* existing */}
  value={achievableGapValue}
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
  tooltip={/* existing MetricStatPopover */}
/>

<ScoreGapRow
  label="Endgame Score Gap:"
  value={scoreGap.score_difference}
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
  tooltip={/* existing MetricStatPopover */}
/>
```

### Frontend — call site at the EndgameMetricCard (per-bucket)

```tsx
// Source: frontend/src/components/charts/EndgameMetricCard.tsx (MODIFIED)
import { PercentileChip } from './PercentileChip';

// Inside the component, add a new prop:
interface EndgameMetricCardProps {
  // ... existing props ...
  scoreGapPercentile: number | null;   // NEW; recovery card receives null
}

// In the JSX, inside the existing ScoreGapRow call (around line 207):
<ScoreGapRow
  // ... existing props ...
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
  tooltip={/* existing MetricStatPopover */}
/>
```

The parent (`EndgameMetricsSection.tsx`) routes the new prop:

```tsx
<EndgameMetricCard
  bucket="conversion"
  // ... existing props ...
  scoreGapPercentile={scoreGap.section2_score_gap_conv_percentile}
/>
<EndgameMetricCard
  bucket="parity"
  // ... existing props ...
  scoreGapPercentile={scoreGap.section2_score_gap_parity_percentile}
/>
<EndgameMetricCard
  bucket="recovery"
  // ... existing props ...
  scoreGapPercentile={null}    // explicit — recovery is out of scope per CONTEXT D-12
/>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-rolled tier zone bands | `ZONE_REGISTRY` + `colorizeGaugeZones()` from `theme.ts` | Phase 63 | Phase 94 chip reuses the same semantic color tokens — no new constants needed. |
| Multiple bespoke popover shells | `MetricStatPopover` shared shell + `InfoPopover` for simple cases | Phase 91 (quick task 260514-i3l) | Phase 94 follows the same shell-mechanics pattern (Radix Root + Trigger asChild + Portal + Content + 100ms hover delay). |
| Frontend re-derives metrics from raw counts | Backend computes + ships scalar; frontend renders | Phase 85.1 (SEC1-10) for achievable_score_gap; carried forward for `_p_value` / `_ci_*` / now `_percentile` | Phase 94 inherits this contract — chip never interpolates locally. |
| Per-row pixel-level bespoke layout | Shared `ScoreGapRow` primitive with slot props | Phase 85 / Phase 87.1 quick-260519-ni3 (startSlot/endSlot pattern) | Phase 94 adds a `chipSlot?: ReactNode` prop following the same slot pattern. |

**Deprecated/outdated:**
- Phase 93's earlier TS-codegen plan was deferred (D-01). Do not extend `scripts/gen_endgame_zones_ts.py`.
- The retracted Phase 87.3 "Endgame Skill" composite is irrelevant; do not reference it in new code.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reusing `PVALUE_RELIABILITY_MIN_N = 10` for all 4 chip gates is acceptable | Standard Stack / Pitfall 6 | CONTEXT D-10 lists this as the recommended default and explicitly allows the planner to argue for a stricter floor. Risk: if real-world UAT shows a chip rendering on n=10 with visible jitter from one game to the next, the planner may want a higher floor (e.g. n=20 for Section 2). Mitigation: ship at n=10, plan a UAT review point. |
| A2 | The chip should use `GAUGE_NEUTRAL` (blue) for the p25–p75 band, not `ZONE_NEUTRAL` | Standard Stack | `GAUGE_NEUTRAL` is the existing "typical skill-cohort range" blue used on raw % gauges. `ZONE_NEUTRAL` is also blue but a slightly different shade. Both are valid; planner picks visually. Risk: low — easily swapped in one constant edit. |
| A3 | Adding `chipSlot?: ReactNode` to `ScoreGapRow` is the cleanest surface change | Architecture Patterns | An alternative would be wrapping each consuming row in a higher-order component that renders the chip outside `ScoreGapRow`. The `chipSlot` approach mirrors the existing `startSlot` / `endSlot` pattern (quick-260519-ni3) — same risk profile. Risk: low. |
| A4 | The popover body component (`PercentileChipPopoverBody`) inlined inside `PercentileChip.tsx` is clean enough; no need to split into a sibling file | Architecture Patterns | Sibling files (like `MetricStatTooltip.tsx`) earn their keep when they're consumed externally. The chip's body is internal. Risk: low — easy to split later if a use case emerges. |
| A5 | Conversion ΔES chip uses `flavor="improvement-focus"`; the other 3 use `flavor="skill-isolating"`. Routing happens at the call site, not inside `PercentileChip` | Frontend wiring | Alternative: route by metric_id inside `PercentileChip`. The call-site approach keeps `PercentileChip` agnostic of metric semantics — cleaner separation. Risk: low. |
| A6 | The popover copy strings in the skeleton above are placeholders; the planner finalizes the exact wording | Code Examples | Within `feedback_popover_copy_minimalism.md` discipline. Risk: low — these are HOW decisions per CONTEXT discretion list. |
| A7 | A single Vitest test asserting "chip absent when percentile === null" per row is sufficient coverage for PCTL-06 | Validation Architecture | If the gate logic in the service is correctly tested at the backend layer, the frontend test just needs to assert the conditional render. Risk: low. |

## Open Questions

1. **Should the chip's text size be `text-sm` or `text-xs`?**
   - What we know: CLAUDE.md mandates `text-sm` minimum for all UI surfaces; popovers are the documented exception (use `text-xs`). The chip is NOT a popover — it's primary content carrying meaning.
   - What's unclear: With 3 flames + "Top 1%" the chip can get visually busy at `text-sm`. The instinct to shrink to `text-xs` for visual balance must be resisted.
   - Recommendation: `text-sm`. Plan to UAT on mobile at 375px; if too cramped, fix via padding / icon size / chip width — not by shrinking the text.

2. **Should the chip background be a solid fill or a tinted background?**
   - What we know: CONTEXT D-04 says "pill/badge with colored background fill", and the existing Badge component uses `bg-{token}/10` (10% opacity) for `destructive` variant or `bg-{token}` (solid) for `default`.
   - What's unclear: At p<25 the chip background is `ZONE_DANGER` (saturated red, same hue as WDL_LOSS). At full opacity it competes with the WDL bars in the same card. At 10% opacity it disappears against the charcoal-texture card surface.
   - Recommendation: Solid fill with white text (`color: oklch(0.98 0 0)` or similar). This matches the IMPERSONATION_PILL pattern (already established for solid-fill semantic pills with light text on a colored surface). UAT verifies contrast.

3. **Should the flame icon use Lucide `Flame` or `lucide-react` `FlameIcon`?**
   - What we know: `Flame` is the canonical Lucide name (verified in dep version ^0.577.0). Other call sites in the codebase use `Cpu`, `Swords`, `BookMarked` (no `Flame` yet).
   - What's unclear: None — `import { Flame } from 'lucide-react'` is the correct import.
   - Recommendation: `Flame`. No question.

4. **Is "Top 100%" a legal render at percentile=0?**
   - What we know: A user at percentile=0 (below p1) renders as "Top 100%" with the formula `max(1, round(100 - 0)) = 100`.
   - What's unclear: Is "Top 100%" misleading? It means "as low as everyone, or lower" — which is technically honest but reads oddly.
   - Recommendation: Accept it. Per CONTEXT D-06: literal-render path; no neutral band suppresses. At p=0 the user IS the weakest. If UAT flags this, revisit by clamping at `Math.max(1, Math.min(99, …))` for a "Top 99%" floor — but D-07 explicitly says render literally near the edges too.

## Environment Availability

Not applicable. Phase 94 introduces no new tools, services, or runtimes beyond what's already installed for this project (Python 3.13, FastAPI, PostgreSQL 18, Node, npm). All deps (`lucide-react`, `radix-ui`, `class-variance-authority`) are already in `package.json` and `pyproject.toml`.

## Security Domain

Reviewed against the project's security posture:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (no auth surface changes) | n/a |
| V3 Session Management | no | n/a |
| V4 Access Control | no (no new endpoint, no new authorization decision) | n/a |
| V5 Input Validation | yes (Pydantic v2 validates new `float \| None` fields; helper rejects NaN at the service boundary) | Pydantic + `math.isnan` guard in `interpolate_percentile` (already present). |
| V6 Cryptography | no | n/a |
| V8 Data Protection | no (percentile is derived, non-PII, non-secret) | n/a |
| V9 Communication | no | n/a |

### Known Threat Patterns for FastAPI + React + Pydantic

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Data exposure via response inflation | Information Disclosure | Verify no PII added — confirmed: percentile is a scalar in [0, 100], non-identifying. |
| Untrusted input via response field | Tampering | The percentile is computed server-side from a committed CDF; not user-controlled. |
| Frontend XSS via popover content | XSS | Popover body uses React children (no `dangerouslySetInnerHTML`); strings are constants. Safe. |
| Cache staleness on prompt version bump | Stale data exposure | n/a for Phase 94 — no LLM payload changes. Phase 95 handles prompt-version invalidation. |

## Sources

### Primary (HIGH confidence)
- `app/services/global_percentile_cdf.py` (full file read) — `interpolate_percentile` signature, return semantics, edge clamps, NaN handling. Phase 93 output, in production.
- `app/services/endgame_service.py` (relevant sections: lines 205, 1259–1419, 2142–2322) — compute sites, existing reliability-gate pattern, helper functions, response construction.
- `app/schemas/endgames.py` (full file read) — exact field names, sibling patterns, `EndgamePerformanceResponse` and `ScoreGapMaterialResponse` shapes.
- `app/services/endgame_zones.py` (lines 1–110) — `MetricId` Literal definition (the 4 in-scope IDs all live here).
- `tests/services/test_global_percentile_cdf.py` — Phase 93 test surface; confirms the helper behavior the planner relies on.
- `frontend/src/lib/theme.ts` (full file read) — exact constant names available for the chip palette (`ZONE_DANGER`, `ZONE_NEUTRAL`, `ZONE_SUCCESS`, `GAUGE_DANGER`, `GAUGE_NEUTRAL`, `GAUGE_SUCCESS`, `IMPERSONATION_PILL_*`).
- `frontend/src/components/popovers/MetricStatPopover.tsx` (full file read) — popover shell pattern to mirror.
- `frontend/src/components/charts/EndgameOverallScoreGapRow.tsx` (full file read) — shared `ScoreGapRow` primitive, slot prop pattern.
- `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` (lines 1–260) — page-level orchestrator + 2 chip insertion sites.
- `frontend/src/components/charts/EndgameMetricCard.tsx` (lines 1–260) — Section 2 card + per-bucket dispatch + SECTION2_DISPLAY_SHIFT affine.
- `frontend/src/types/endgames.ts` (lines 1–250) — manual TS-type mirror.
- `frontend/src/components/ui/badge.tsx` + `frontend/src/components/ui/info-popover.tsx` (full file read) — primitives available but not extended.
- `.planning/phases/94-backend-frontend-percentile-annotations/94-CONTEXT.md` — locked decisions.
- `.planning/phases/93-global-percentile-benchmark-artifact/93-CONTEXT.md` — upstream phase decisions.
- `.planning/seeds/SEED-019-global-percentile-annotations-on-endgame-metrics.md` — design rationale.
- `.planning/REQUIREMENTS.md` PCTL-02..06 — locked requirements.
- `.planning/ROADMAP.md` Phase 94 — locked success criteria.
- `CLAUDE.md` — project-wide rules (mobile parity, theme.ts, text-sm floor, ty, knip, pre-PR checklist).

### Secondary (MEDIUM confidence)
- Project memory `feedback_popover_copy_minimalism.md` — popover copy discipline.
- Project memory `feedback_llm_significance_signal.md` — Phase 94 stays out of LLM payload.
- Project memory `feedback_no_dev_db_reset_in_plans.md` — verification design.

### Tertiary (LOW confidence)
- None — all critical claims are verified directly from source files.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep already in the project; helper already shipped and tested.
- Architecture: HIGH — patterns established by Phase 85.1 / 87.2 / 91 are directly reusable.
- Pitfalls: HIGH — all 8 pitfalls discovered by direct code inspection during research.

**Research date:** 2026-05-23
**Valid until:** ~2026-06-22 (30 days; stable codebase, no external dep churn expected)

# Phase 98: Per-TC Collapsible Endgame Type Cards - Research

**Researched:** 2026-05-30
**Domain:** Endgame Type Breakdown UI restructure — per-(class × TC) benchmark bands, zone codegen, backend per-(class × TC) aggregation, collapsible accordion layout
**Confidence:** HIGH (all findings verified from codebase and authoritative benchmark report)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Restore the pre-removal `EndgameTypeCard` 5-element anatomy (from `git show d3453597^:frontend/src/components/charts/EndgameTypeCard.tsx`). Full anatomy, not a trimmed version.
- **D-02:** Tile layout, top-to-bottom: (1) Title + InfoPopover + sparse `n=total` chip; (2) Side-by-side Conversion + Recovery `EndgameGauge`; (3) WDL bar row with `Games: X% (count)` deep-link; (4) Score bullet (W + 0.5·D / N) sig-gated vs 50%; (5) Per-span Score Gap bullet (`ScoreGapRow`).
- **D-03:** All five elements on every tile, no content thinning at any breakpoint.
- **D-04:** Conv/Recov gauges (#2) and Score-Gap bullet (#5) banded per-(class × TC). Score bullet (#4) keeps its existing 50% anchor + sig-gate (unchanged).
- **D-05:** Each TC card: single `charcoal-texture rounded-md` container with full-bleed header (TC icon + TC label + `Games: X% (count)` with Swords icon), matching `EndgameMetricsByTcCard` header convention.
- **D-06:** Four type tiles separated by thin dividers (not bordered sub-cards). Divider grammar: vertical `w-px bg-border/40` between columns, horizontal `border-t border-border/40` between rows.
- **D-07:** Responsive staircase: 4×1 (desktop) → 2×2 (tablet) → 1×4 (mobile). No content thinning at any width.
- **D-08 [PLANNER FLAG]:** 2×2 staircase needs dividers on both axes at the 2×2 stage. Exact CSS-grid divider technique is planner's call.
- **D-09:** `primary = argmax( games_in_bucket(tc) × NOMINAL_DURATION[tc] )` over TCs passing games floor. Flat all-time. Computed over currently-filtered game set.
- **D-10:** `NOMINAL_DURATION` = `{ bullet: 60, blitz: 180, rapid: 600, classical: 900 }` (seconds, user-chosen ratios 1:3:10:15). Named constants, not magic numbers.
- **D-11 [PLANNER FLAG]:** Heuristic + constants in one shared util (for later timeline alignment). Module location is planner's call.
- **D-12:** Reset accordion to recomputed primary TC on any filter change. Manual expand/collapse persists only within a stable filter set.
- **D-13:** `/stats` endgame breakdown must expose per-(class × TC) rates + games counts. No eligible-count weighting payload.
- **D-14:** Per-(class × TC) Conv/Recov bands + per-(class × TC) ΔES Score-Gap bands generated into `endgameZones.ts` via `endgame_zones.py` + `gen_endgame_zones_ts.py`. Today's single per-class `achievable_score_gap` band gains a TC dimension.
- **D-15:** LLM insights path (`_findings_conversion_recovery_by_type` / `assign_per_class_zone`) unaffected — response shape preserved or additively extended only.

### Claude's Discretion
- Exact backend response shape for the per-(class × TC) rate+count grouping (D-13).
- Whether the new per-(class × TC) band structure replaces or sits alongside the existing `BUCKETED_ZONE_REGISTRY` entries (D-14).
- Exact CSS-grid divider technique for the both-axes 2×2 staircase (D-08).
- Exact module location for the shared primary-TC util (D-11).
- knip/dead-code cleanup of old 3-col grid assumptions and dropped Mixed tile.
- Whether a `/gsd-ui-phase` pass is warranted (process note, not a plan deliverable).

### Deferred Ideas (OUT OF SCOPE)
- Align the Endgame ELO Timeline's default-line algo to this phase's primary-TC heuristic.
- Adopt mode-3 collapsible affordance on Phase 97 Endgame Metrics by TC section.
- Mixed endgame-type analysis (tile dropped; backend computes per-class Mixed for LLM path).
- `2026-05-17-recovery-score-gap-popover-copy.md` reframe (declined scope expansion).
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` (fix opportunistically only if file touched).
</user_constraints>

---

## Summary

Phase 98 restructures `EndgameTypeBreakdownSection` from a 3-col grid of 5 per-type cards into vertically-stacked full-width collapsible per-TC cards (one per TC), each containing a 4-tile grid (rook/minor_piece/pawn/queen; Mixed dropped). The Conv/Recov gauges removed on 2026-05-29 return, now banded against the correct per-(class × TC) benchmark IQR.

The phase is primarily a re-assembly of existing components into a new layout. All primitives exist: `EndgameGauge`, `ScoreGapRow`, `MiniBulletChart`, `MiniWDLBar`, `accordion.tsx`. The main new work is: (1) 20 new per-(class × TC) band entries in `endgame_zones.py` + codegen; (2) a new backend per-(class × TC) rate+count aggregation added to the overview response; (3) new frontend section/card components replacing `EndgameTypeBreakdownSection`'s 3-col grid; (4) a shared primary-TC util.

**Primary recommendation:** Model the new backend aggregation on `_compute_per_tc_metric_cards` (Phase 97 pattern), add per-(class × TC) bands as a new `PER_CLASS_TC_GAUGE_ZONES` dict alongside the existing `PER_CLASS_GAUGE_ZONES` (not replacing it — LLM path uses `assign_per_class_zone` which reads from `PER_CLASS_GAUGE_ZONES`), and model the frontend section on `EndgameTimePressureSection` for per-TC card selection + `EndgameMetricsByTcCard` for header + divider grammar.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Per-(class × TC) benchmark band data | Backend (Python) | Frontend (generated TS) | Python is authoritative source of truth per Phase 63 D-01; codegen'd to TS via CI-gated script |
| Per-(class × TC) rate+count aggregation | API/Backend | — | New backend query on existing `query_endgame_bucket_rows` result rows |
| Primary-TC heuristic computation | Frontend | — | Client-side: operates on the per-TC games counts returned by the backend; no server round-trip needed |
| Accordion state management | Frontend | — | React state (`useState`) gated on filter change via `useEffect` or key reset |
| Collapsible TC card layout | Frontend | — | New `EndgameTypeBreakdownSection` + new per-TC card component |
| Score Gap band generation (ΔES) | Backend (Python) | Frontend (generated TS) | Same codegen pipeline as Conv/Recov bands |
| LLM insights path | Backend only | — | D-15: unaffected, reads `categories` from pooled stats (additive extension only if needed) |

---

## 1. Benchmark Band Numbers (Per-(class × TC)) — Numeric Source of Truth

**Source:** `reports/benchmark/benchmarks-latest.md` §3.4.1 TC marginal tables [VERIFIED: codebase read]

### Conversion Rate per-(class × TC) — p25/p75 IQR

From the TC marginal table in §3.4.1 (format: `mean (p25–p75, n_users)`):

| class | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| rook | 65.0% (56–75) | 73.4% (67–82) | 75.8% (69–83) | 80.0% (74–87) |
| minor_piece | 61.7% (51–73) | 71.5% (64–81) | 75.4% (68–83) | 80.9% (75–89) |
| pawn | 67.0% (57–80) | 76.6% (68–87) | 81.8% (75–91) | 86.1% (80–92) |
| queen | 73.9% (64–83) | 78.8% (70–90) | 82.7% (75–92) | 91.6% (88–100) |
| mixed | 65.6% (60–72) | 71.8% (68–76) | 74.7% (70–79) | 76.1% (70–83) |

**As fraction tuples for `endgame_zones.py` (p25, p75):**

| class | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| rook | (0.56, 0.75) | (0.67, 0.82) | (0.69, 0.83) | (0.74, 0.87) |
| minor_piece | (0.51, 0.73) | (0.64, 0.81) | (0.68, 0.83) | (0.75, 0.89) |
| pawn | (0.57, 0.80) | (0.68, 0.87) | (0.75, 0.91) | (0.80, 0.92) |
| queen | (0.64, 0.83) | (0.70, 0.90) | (0.75, 0.92) | (0.88, 1.00) |
| mixed | (0.60, 0.72) | (0.68, 0.76) | (0.70, 0.79) | (0.70, 0.83) |

### Recovery Rate per-(class × TC) — p25/p75 IQR

| class | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| rook | 34.4% (27–43) | 28.5% (20–37) | 23.7% (17–30) | 19.6% (13–25) |
| minor_piece | 39.9% (29–50) | 30.8% (21–40) | 25.2% (15–33) | 20.2% (12–28) |
| pawn | 35.4% (25–46) | 25.8% (17–36) | 19.5% (10–28) | 16.8% (8–21) |
| queen | 27.9% (19–36) | 23.7% (14–31) | 17.9% (8–25) | 7.4% (0–9) |
| mixed | 35.3% (30–40) | 30.2% (25–35) | 27.5% (23–31) | 24.4% (18–30) |

**As fraction tuples (p25, p75):**

| class | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| rook | (0.27, 0.43) | (0.20, 0.37) | (0.17, 0.30) | (0.13, 0.25) |
| minor_piece | (0.29, 0.50) | (0.21, 0.40) | (0.15, 0.33) | (0.12, 0.28) |
| pawn | (0.25, 0.46) | (0.17, 0.36) | (0.10, 0.28) | (0.08, 0.21) |
| queen | (0.19, 0.36) | (0.14, 0.31) | (0.08, 0.25) | (0.00, 0.09) |
| mixed | (0.30, 0.40) | (0.25, 0.35) | (0.23, 0.31) | (0.18, 0.30) |

**Note on pawnless:** n far below floor for per-(class × TC) analysis; hidden in live UI. Keep pinned to existing `PER_CLASS_GAUGE_ZONES["pawnless"]` values — no per-TC entries needed.

### Cohen's d Collapse Verdicts for Conv/Recov per Class

From §3.4.1 collapse verdict table [VERIFIED: codebase read]:

| class | conv TC d | conv TC verdict | recov TC d | recov TC verdict |
|---|---:|---|---:|---|
| rook | 1.24 | **keep separate** | 1.33 | **keep separate** |
| minor_piece | 1.50 | **keep separate** | 1.48 | **keep separate** |
| pawn | 1.40 | **keep separate** | 1.36 | **keep separate** |
| queen | 1.43 | **keep separate** | 1.67 | **keep separate** |
| mixed | 1.19 | **keep separate** | 1.28 | **keep separate** |

All 5 visible classes × 2 metrics keep-separate on TC (d ≈ 1.19–1.67). This validates per-(class × TC) bands as required.

### Score-Gap (ΔES) per-(class × TC) — TC Collapse Verdict

From §3.4.2 TC marginal [VERIFIED: codebase read]:

| class | TC d | verdict |
|---|---:|---|
| rook | 0.07 | **collapse** |
| minor_piece | 0.07 | **collapse** |
| pawn | 0.10 | **collapse** |
| queen | 0.18 | **collapse** |
| mixed | 0.13 | **collapse** |

All per-class ΔES Score-Gap TC axes collapse (d < 0.2). The four per-(class × TC) ΔES bands per class will be statistically near-identical. Per D-04/D-14: "Score Gap forced per-TC for visual consistency — redundancy is chosen, not a bug." Planner must specify these bands as near-copies of the existing per-class `achievable_score_gap` bands:

| class | live per-class `achievable_score_gap` band | use for all 4 TCs |
|---|---|---|
| rook | (-0.05, 0.05) | yes |
| minor_piece | (-0.04, 0.06) | yes |
| pawn | (-0.04, 0.05) | yes |
| queen | (-0.04, 0.05) | yes |
| mixed | (-0.03, 0.04) | yes |

---

## 2. Zone System — Current Structure and How It Must Change

**Source:** `app/services/endgame_zones.py`, `scripts/gen_endgame_zones_ts.py`, `frontend/src/generated/endgameZones.ts` [VERIFIED: codebase read]

### Current Zone Data Structures

#### `PER_CLASS_GAUGE_ZONES` (per-class only, used by LLM + existing tile)

```python
@dataclass(frozen=True)
class PerClassBands:
    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]

PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands]
# entries: rook, minor_piece, pawn, queen, mixed, pawnless
```

This is consumed by:
- `assign_per_class_zone()` in `endgame_zones.py` — used by LLM path (`_findings_conversion_recovery_by_type` in `insights_service.py`). **Must remain unchanged (D-15).**
- `gen_endgame_zones_ts.py` — emitted as `PER_CLASS_GAUGE_ZONES` export to `endgameZones.ts`.
- Current (post-removal) `EndgameTypeCard.tsx` imports `PER_CLASS_GAUGE_ZONES` from `@/generated/endgameZones`.

#### `TC_METRIC_BANDS` (Phase 97, per-TC for metrics section)

```python
@dataclass(frozen=True)
class TcConvRecovBands:
    conv_rate: tuple[float, float]
    recov_rate: tuple[float, float]
    parity_rate: tuple[float, float]
    conv_score_gap: tuple[float, float]
    recov_score_gap: tuple[float, float]

TC_METRIC_BANDS: Mapping[Literal["bullet", "blitz", "rapid", "classical"], TcConvRecovBands]
```

This is the **structural model** for the new per-(class × TC) bands.

#### `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` — the TC-keyed nested-dict model

```python
PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Mapping[
    Literal["bullet", "blitz", "rapid", "classical"],
    Mapping[Literal[0, 1, 2, 3, 4], PressureBinBand],
]
```

This is the **structural template** for nested TC-keyed lookups.

### Recommended New Python Structure

Add a **new `PER_CLASS_TC_GAUGE_ZONES` dict alongside `PER_CLASS_GAUGE_ZONES`** (do NOT replace it — LLM path must stay unaffected):

```python
@dataclass(frozen=True)
class PerClassTcBands:
    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]

PER_CLASS_TC_GAUGE_ZONES: Mapping[
    EndgameClass,
    Mapping[Literal["bullet", "blitz", "rapid", "classical"], PerClassTcBands]
]
# 5 classes (rook/minor_piece/pawn/queen/mixed) × 4 TCs = 20 entries per metric.
# pawnless omitted (below floor; hidden in UI).
```

**Why not replace:** `assign_per_class_zone()` reads `PER_CLASS_GAUGE_ZONES` and is called by the LLM path. Replacing `PER_CLASS_GAUGE_ZONES` would require updating the LLM path, which D-15 forbids. Adding a parallel structure keeps both co-existing.

### Codegen Extension

`gen_endgame_zones_ts.py` must emit a new `PER_CLASS_TC_GAUGE_ZONES` export mirroring the Python structure, following the pattern of `_format_per_class_gauge_zones()` and `_format_tc_metric_bands()`.

The generated TS shape:
```typescript
export const PER_CLASS_TC_GAUGE_ZONES: Record<
  EndgameClassKey,
  Record<
    'bullet' | 'blitz' | 'rapid' | 'classical',
    { conversion: [number, number]; recovery: [number, number]; achievable_score_gap: [number, number] }
  >
> = { ... } as const;
```

The new `EndgameTypeCard` tile (now inside a per-TC card) resolves its gauge `zones` by: `PER_CLASS_TC_GAUGE_ZONES[category.endgame_class][tc].conversion` (and `.recovery`, `.achievable_score_gap`), then wraps with `colorizeGaugeZones()`.

**CI gate:** After editing `endgame_zones.py`, run `uv run python scripts/gen_endgame_zones_ts.py` and commit the updated `frontend/src/generated/endgameZones.ts`. CI runs `git diff --exit-code` on the generated file.

---

## 3. Backend Per-(class × TC) Rate+Count Aggregation

**Source:** `app/services/endgame_service.py`, `app/repositories/endgame_repository.py`, `app/schemas/endgames.py`, `frontend/src/types/endgames.ts` [VERIFIED: codebase read]

### Current `EndgameStatsResponse` Shape (Pooled Across TC)

```python
# app/schemas/endgames.py
class EndgameStatsResponse(BaseModel):
    categories: list[EndgameCategoryStats]  # pooled across all TCs; sorted by total desc
    total_games: int
    endgame_games: int
```

Each `EndgameCategoryStats` carries `conversion_pct`, `recovery_pct`, `total`, WDL counts, Score Gap fields — all pooled across TCs.

### `query_endgame_bucket_rows` — Row Shape

```
(game_id, endgame_class, result, user_color, eval_cp, eval_mate,
 time_control_bucket,          # col 6 — added in Phase 97
 next_entry_eval_cp,           # col 7
 next_entry_eval_mate)         # col 8
```

`time_control_bucket` at column index 6 is already present (Phase 97 added it). The existing `_aggregate_endgame_stats()` function ignores column 6 — it only processes columns 0-5.

### The Aggregation Path: `_aggregate_endgame_stats()` → `query_endgame_stats()`

```python
def query_endgame_stats(...) -> EndgameStatsResponse:
    rows = await query_endgame_bucket_rows(...)
    categories, _gaps = _aggregate_endgame_stats(rows)
    return EndgameStatsResponse(categories=categories, ...)
```

`_aggregate_endgame_stats()` groups by `endgame_class_int` only, accumulating `wdl`, `conv`, `recov` dicts keyed by `EndgameClass`. It does NOT group by TC.

### How Phase 97 Added Per-TC Aggregation (the model to follow)

Phase 97 added `_compute_per_tc_metric_cards()` as a **parallel single-pass** over `bucket_rows`, grouping by `row[6]` (TC). The result is a new `EndgameMetricsCardsResponse` attached to `EndgameOverviewResponse.endgame_metrics_cards`.

### Recommended Approach for Phase 98

Add a **new parallel aggregation** that groups `bucket_rows` by `(endgame_class_int, tc)`:

**New dataclass:**
```python
@dataclass(frozen=True)
class PerClassTcStats:
    total: int                    # total games for this (class, TC)
    wins: int
    draws: int
    losses: int
    conversion_games: int
    conversion_wins: int
    conversion_draws: int
    recovery_games: int
    recovery_wins: int
    recovery_draws: int

# Or model on EndgameCategoryStats but slimmed to what the tile needs.
```

**New response field on `EndgameStatsResponse` (additive, optional for back-compat):**
```python
class EndgameStatsResponse(BaseModel):
    categories: list[EndgameCategoryStats]  # unchanged
    total_games: int                         # unchanged
    endgame_games: int                       # unchanged
    # New (Phase 98): per-(class × TC) rates for the collapsible tile grid.
    # Optional for back-compat with older clients.
    categories_by_tc: dict[
        Literal["bullet", "blitz", "rapid", "classical"],
        list[EndgameCategoryStats]           # same shape, scoped to one TC
    ] | None = None
```

**Alternative shape (planner's discretion, D-13):** A list of TC-card wrappers, each containing a list of 4 class-stats objects, matching the frontend render order (rook/minor_piece/pawn/queen). The frontend renders TCs in bullet/blitz/rapid/classical order anyway; Mixed is excluded on the frontend side.

**D-15 safeguard:** `_findings_conversion_recovery_by_type()` in `insights_service.py` reads `response.stats.categories` (the pooled list) and calls `assign_per_class_zone()` (which reads `PER_CLASS_GAUGE_ZONES`). The new `categories_by_tc` field is additive — it does not replace `categories`. The LLM path remains unaffected.

### Query Pattern

The existing `query_endgame_bucket_rows` already returns `time_control_bucket` at col 6. A new helper function (following `_compute_per_tc_metric_cards`) does a single pass:

```python
def _aggregate_endgame_stats_by_tc(
    rows: Sequence[Row],
) -> dict[str, list[EndgameCategoryStats]]:
    """Group endgame stats by (TC, class). Returns dict keyed by TC."""
    # Accumulators: tc_str -> class_int -> wdl/conv/recov counters
    ...
    for row in rows:
        tc = row[6]
        endgame_class_int = row[1]  # or row.endgame_class for named access
        ...
```

No new DB query is needed — reuses the existing `bucket_rows` passed to `_aggregate_endgame_stats`.

---

## 4. Pre-Removal `EndgameTypeCard` 5-Element Anatomy (D-01/D-02)

**Source:** `git show d3453597^:frontend/src/components/charts/EndgameTypeCard.tsx` [VERIFIED: codebase read]

### What Was Removed in Commit `d3453597`

The removal commit stripped:
- The `EndgameGauge` import and all gauge-related code.
- The `PER_CLASS_GAUGE_ZONES` import (for `convZones`/`recovZones`).
- The gauge row (`grid grid-cols-2 gap-2` with two `EndgameGauge` instances).
- The `PER_TYPE_GAUGE_SIZE = 130` constant.
- The `convZones`/`recovZones` derivation via `colorizeGaugeZones()`.
- The `gamesLink` `<span>` containing the Swords icon + `Games: X% (count)` format with the deep-link.

The post-removal card (current state) has: (1) title row; (2) WDL bar; (3) Score bullet; (4) Score Gap bullet.

### Full Pre-Removal Anatomy to Restore

```
1. titleRow — <h3 className="flex items-center gap-1 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold">
     <span>{category.label}</span>
     <InfoPopover ariaLabel="..." testId="...title-info">…</InfoPopover>
     {isUnreliable && <span … data-testid="…n-chip">n={category.total}</span>}
   </h3>

2. Gauge row — <div className="grid grid-cols-2 gap-2" data-testid="…gauges">
     Conversion column: <div data-testid="…conv-gauge">
       <div className="text-sm text-muted-foreground mb-1">Conversion</div>
       <EndgameGauge value={conversion_pct} maxValue={100} zones={convZones} size={130} />
     </div>
     Recovery column: <div data-testid="…recov-gauge">
       <div className="text-sm text-muted-foreground mb-1">Recovery</div>
       <EndgameGauge value={recovery_pct} maxValue={100} zones={recovZones} size={130} />
     </div>
   </div>

3. WDL row + Games link — the pre-removal code had:
     gamesLink = <span …><Swords /><span>Games: {sharePctFormatted}% ({gamesCountFormatted})</span></span>
     Wrapped in a Link to the filtered endgame-games page.
     Conditionally: if SHOW_WDL_BAR_IN_TYPE_CARDS → WDL bar above + gamesLink; else just gamesLink.

4. Score bullet row — (showScoreRow) Score: wins+0.5draws/total, sig-gated vs 50%.
     MiniBulletChart with ENDGAME_TILE_SCORE_DOMAIN, SCORE_BULLET_* constants, Wilson CIs.
     MetricStatPopover for the info icon.

5. Score Gap bullet row — (showGapRow) ScoreGapRow with:
     label="Gap:"
     value=gapMean, neutralMin/Max from per-class band (→ per-(class × TC) band in Phase 98)
     startSlot: <Cpu /> Start: {startMean}%
     endSlot: End: {endMean}%
     MetricStatPopover tooltip.
```

### Key Props for the Restored Tile in Phase 98 Context

The restored tile no longer receives `sharePct` from a pooled total. Instead, it receives data scoped to one TC:
- `category`: an `EndgameCategoryStats`-shaped object but scoped to one TC (wins/draws/losses/total/conversion/recovery all from that TC's data only).
- `tc`: the TC string (for band lookup).
- `convZones` / `recovZones`: derived from `PER_CLASS_TC_GAUGE_ZONES[endgame_class][tc]`.
- `neutralMin` / `neutralMax` for Score Gap: from `PER_CLASS_TC_GAUGE_ZONES[endgame_class][tc].achievable_score_gap`.

The `onCategorySelect` deep-link behavior and the Score bullet (50% anchor, Wilson CI, sig-gate) are unchanged.

---

## 5. Divider Grammar — D-06/D-08 Details

**Source:** `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` ~line 347 [VERIFIED: codebase read]

### `EndgameMetricsByTcCard` Divider — the Template

```tsx
// Single-axis divider (flex-col / flex-row at lg):
const divider = (
  <>
    {/* Vertical rule between metric blocks (lg+) */}
    <div className="hidden lg:block w-px bg-border/40 mx-6" aria-hidden="true" />
    {/* Horizontal rule below lg */}
    <div className="block lg:hidden border-t border-border/40 my-4" aria-hidden="true" />
  </>
);

// Body: flex-col (mobile) / flex-row (lg+)
<div className="flex flex-col lg:flex-row p-4">
  <MetricBlock ... />
  {divider}
  <MetricBlock ... />
  {divider}
  <MetricBlock ... />
</div>
```

This single-axis pattern (always either a vertical or horizontal divider) is designed for a 1×N → N×1 layout. It does **not** handle the 2×2 staircase needed for Phase 98.

### D-08 Two-Axis Divider Problem

For the 4-tile staircase (4×1 → 2×2 → 1×4):

- **4×1 (desktop, `xl:` or `2xl:`):** 3 vertical dividers between 4 columns. One row, no horizontal dividers.
- **2×2 (tablet, `sm:` or `md:`):** 1 vertical divider between columns 0 and 1 (and 2 and 3), plus 1 horizontal divider between the two rows.
- **1×4 (mobile):** 3 horizontal dividers between tiles. No vertical dividers.

**Recommended CSS approach (planner's discretion):** Use a CSS grid container with `divide-x` / `divide-y` utilities that don't survive multi-row grids cleanly, so per-cell border classes are more reliable:

```tsx
// Option A: Per-cell conditional borders
// Each tile gets border classes depending on its column + row position in the grid.
// Using Tailwind: add `border-r border-border/40` to col 0 at desktop, etc.
// Problem: n_tiles = 4, positions are static.

// Recommended approach: Use a responsive grid and add borders per-cell.
// grid-cols-1 sm:grid-cols-2 xl:grid-cols-4
// tile at index i gets:
//   sm: border-r border-border/40 if i % 2 === 0 (right border of left column)
//   sm: border-t border-border/40 if i >= 2 (top border of bottom row)
//   xl: border-r border-border/40 if i < 3 (right border of non-last columns)
//   mobile: border-t border-border/40 if i > 0
```

**Key constraint:** The `EndgameMetricsByTcCard` divider helper works for exactly 3 items in a 1D flex. The 4-tile 2D grid requires a different technique. The `divide-x`/`divide-y` utilities only work reliably on single-row/single-column flex containers. For a CSS grid that wraps, per-cell border classes (conditioned on grid position) are the standard approach. The planner should choose the exact pattern.

---

## 6. Per-TC Card Scaffolding from `EndgameTimePressureSection`

**Source:** `frontend/src/components/charts/EndgameTimePressureSection.tsx` [VERIFIED: codebase read]

### Reusable Pattern

```tsx
// Grid layout by visible card count (1/2/3/4 TCs)
const GRID_ONE_CARD = 'w-full md:w-1/2 mt-2';
const GRID_TWO_CARDS = 'grid grid-cols-1 md:grid-cols-2 gap-4 mt-2';
const GRID_THREE_CARDS = 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mt-2';
const GRID_FOUR_CARDS = 'grid grid-cols-1 lg:grid-cols-2 gap-4 mt-2';
```

**Phase 98 deviation:** The mode-3 collapsible accordion layout is **full-width stacked** (D-07 hard constraint). Unlike `EndgameTimePressureSection`'s multi-column grid, Phase 98 uses a single-column vertical stack of accordion items. The `GRID_*_CARDS` pattern is NOT reused for the outer TC card layout — instead each accordion item spans full width.

**What IS reused:**
- TC ordering: `["bullet", "blitz", "rapid", "classical"]` (use `_TIME_CONTROL_ORDER` pattern or the same fixed order).
- Null/sparse suppression: only TCs with `total >= MIN_GAMES_PER_TC_CARD` render (same gate as Time Pressure).
- Empty state: no eligible TCs → show "No endgame type data..." message.
- Grand total for per-card percentage header.

### `MIN_GAMES_PER_TC_CARD` and `MIN_GAMES_FOR_RELIABLE_STATS`

From `app/services/endgame_zones.py` [VERIFIED: codebase read]:
- `MIN_GAMES_PER_TC_CARD = 20` — gate for a whole TC card to appear (from Phase 88).
- `MIN_GAMES_FOR_RELIABLE_STATS = 10` — gate within a tile for showing the Score bullet; defined in `frontend/src/lib/theme.ts`.

For the tile grid within a TC card: a tile with `total < MIN_GAMES_FOR_RELIABLE_STATS` still renders but with `UNRELIABLE_OPACITY` (same pre-removal behavior). A TC card with `total < MIN_GAMES_PER_TC_CARD` is fully suppressed.

---

## 7. Accordion Primitive — Usage for Per-TC Headers

**Source:** `frontend/src/components/ui/accordion.tsx`, `frontend/src/pages/Endgames.tsx` [VERIFIED: codebase read]

### Current `accordion.tsx` API

The Radix Accordion wrapper exposes `Accordion`, `AccordionItem`, `AccordionTrigger`, `AccordionContent` (same API as shadcn/ui accordion).

**Existing usage on `Endgames.tsx` (line 381):**
```tsx
<Accordion type="single" collapsible>
  <AccordionItem value="concepts" className="charcoal-texture rounded-md px-4"
    data-testid="endgame-concepts-trigger">
    <AccordionTrigger className="text-foreground justify-start flex-none gap-2 ...">
      ...
    </AccordionTrigger>
    <AccordionContent className="text-muted-foreground space-y-2">
      ...
    </AccordionContent>
  </AccordionItem>
</Accordion>
```

### What Phase 98 Needs

**Multi-item controlled accordion (one item expanded at a time):**

```tsx
<Accordion
  type="single"
  collapsible
  value={expandedTc}              // controlled: tracks which TC is expanded
  onValueChange={setExpandedTc}   // updates on click
>
  {eligibleTcCards.map((tc) => (
    <AccordionItem key={tc} value={tc} className="...">
      <AccordionTrigger
        data-testid={`type-breakdown-tc-${tc}-trigger`}
        aria-label={`${TC_LABELS[tc]} endgame type breakdown`}
        className="..."
      >
        {/* Full-bleed header: TC icon, TC label, Games: X% (count) with Swords icon */}
        ...
      </AccordionTrigger>
      <AccordionContent>
        {/* 4-tile grid with dividers */}
        ...
      </AccordionContent>
    </AccordionItem>
  ))}
</Accordion>
```

**Default-expanded state (D-09):**
```tsx
// Compute primaryTc from per-TC game counts × NOMINAL_DURATION
const primaryTc = computePrimaryTc(categoriesByTc, NOMINAL_DURATION);
const [expandedTc, setExpandedTc] = useState<string>(primaryTc ?? '');
```

**Filter-change reset (D-12):**
```tsx
// Reset on any filter change: recompute primary TC and reset
useEffect(() => {
  const newPrimary = computePrimaryTc(categoriesByTc, NOMINAL_DURATION);
  setExpandedTc(newPrimary ?? '');
}, [/* filter dependency array */]);
```

Alternatively: use the filter params as a `key` prop on the section component — React re-mounts the component (and resets `useState`) whenever the key changes. This is simpler but more aggressive (full unmount/mount).

**Keyboard accessibility:** `AccordionTrigger` wraps `AccordionPrimitive.Trigger` which is a `<button>` — keyboard navigation (Enter/Space to toggle, Tab to move between triggers) is provided by Radix. The `data-testid` on each trigger satisfies SC-2.

### `AccordionContent` Styling Note

The existing `AccordionContent` adds `pt-0 pb-2.5 h-(--radix-accordion-content-height)`. The per-TC tile grid lives inside `AccordionContent` — do NOT add `px-4` on `AccordionContent` if you want the header to be full-bleed (the card container handles padding, not the content wrapper). The tile grid body has its own `p-4` on the content area.

---

## 8. Existing Test Infrastructure and What Must Change

**Source:** `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx`, `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx` [VERIFIED: codebase read]

### Tests That Must Be Updated (SC-10)

**`EndgameTypeBreakdownSection.test.tsx`** — four test suites:
1. "renders 5 cards when all 6 EndgameClass entries present (pawnless filtered)" — must change to assert 4 TC accordion items with 4 type tiles each (Mixed dropped).
2. "renders the locked sub-question copy" — copy may change.
3. **"renders a grid container carrying all locked Tailwind breakpoint classes"** — MUST change: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` is the old 5-card layout. New layout uses accordion items, not a multi-col grid.
4. "renders cards in the backend-sorted order" — ordering changes from by-total-desc to fixed bullet/blitz/rapid/classical per-TC order.

**`EndgameTypeCard.test.tsx`** — tests the pre-gauge-removal layout's Score bullet, sparse state, empty state. Must update for:
- Tile is now inside a TC card (receives per-TC data).
- Conv/Recov gauge testids restored (`…-conv-gauge`, `…-recov-gauge`).
- `data-testid` scheme for accordion triggers.

### Backend Test Coverage

The endgame service tests (`tests/test_endgame_service.py` or similar) should cover the new `_aggregate_endgame_stats_by_tc()` function. The existing `_compute_per_tc_metric_cards` tests are the model.

---

## Architecture Patterns

### System Architecture Diagram

```
Sidebar filters (TC, recency, color, platform, opponent)
        │
        ▼
useEndgames hook → GET /endgames/overview
                        │
        ┌───────────────┼──────────────────────┐
        ▼               ▼                      ▼
 stats.categories  stats.categories_by_tc  endgame_metrics_cards
 (pooled, LLM use) (new per-TC per-class)   (Phase 97)
        │               │
        ▼               ▼
 LLM path reads    EndgameTypeBreakdownSection (new)
 categories only         │
 (D-15: unaffected)  computePrimaryTc()
                         │
                    [Accordion: per-TC items]
                         │
                    AccordionItem (bullet/blitz/rapid/classical)
                         │
                    [4-tile grid: rook | minor_piece | pawn | queen]
                         │
                    EndgameTypeTile (restored 5-element anatomy)
                    ├── EndgameGauge (conv) ← PER_CLASS_TC_GAUGE_ZONES[class][tc]
                    ├── EndgameGauge (recov) ← PER_CLASS_TC_GAUGE_ZONES[class][tc]
                    ├── MiniWDLBar + Games link
                    ├── MiniBulletChart (score vs 50%)
                    └── ScoreGapRow ← PER_CLASS_TC_GAUGE_ZONES[class][tc].achievable_score_gap
```

### Recommended Component Structure

```
frontend/src/components/charts/
├── EndgameTypeBreakdownSection.tsx  (replace 3-col grid with accordion orchestrator)
├── EndgameTypeTcCard.tsx            (new: single accordion item — header + 4-tile grid)
├── EndgameTypeCard.tsx              (rename/repurpose: now a single tile, not standalone card)
│                                     or keep EndgameTypeCard.tsx as the tile and wrap it)
└── [optional] primaryTc util        (shared util D-11 — or place in lib/)
```

**Naming note:** The planner should decide whether to keep `EndgameTypeCard.tsx` as the tile component (restoring its pre-removal anatomy) and wrap it in a new `EndgameTypeTcCard.tsx`, or merge everything into the section. The pre-removal `EndgameTypeCard.tsx` has the right anatomy already — restore its 5-element form and re-use it as the tile inside the new TC card.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---|---|---|
| Accordion expand/collapse with animation | Custom expand/collapse logic | Radix Accordion (`accordion.tsx`) |
| Gauge zone coloring | Manual color logic | `colorizeGaugeZones()` from `theme.ts` |
| TC band lookup | Inline band constants | `PER_CLASS_TC_GAUGE_ZONES` from generated `endgameZones.ts` |
| TC card ordering | Custom sort | `_TIME_CONTROL_ORDER = ["bullet", "blitz", "rapid", "classical"]` |
| Per-TC games floor gate | Custom threshold | `MIN_GAMES_PER_TC_CARD` from `endgameZones.ts` |
| Wilson CI for Score bullet | Manual CI math | `wilsonBounds()` from `scoreConfidence.ts` |
| Score zone color | Custom logic | `scoreZoneColor()` from `scoreBulletConfig.ts` |
| Codegen drift detection | Manual comparison | `uv run python scripts/gen_endgame_zones_ts.py` + CI |

---

## Common Pitfalls

### Pitfall 1: Breaking the LLM Path by Modifying `PER_CLASS_GAUGE_ZONES`
**What goes wrong:** The `assign_per_class_zone()` function in `endgame_zones.py` reads `PER_CLASS_GAUGE_ZONES`. If Phase 98 restructures or replaces it, `_findings_conversion_recovery_by_type` in `insights_service.py` breaks.
**How to avoid:** Add `PER_CLASS_TC_GAUGE_ZONES` as a parallel structure; leave `PER_CLASS_GAUGE_ZONES` and `assign_per_class_zone` unchanged.

### Pitfall 2: Forgetting to Regenerate `endgameZones.ts` After Python Changes
**What goes wrong:** CI fails with drift error even though the Python registry is correct.
**How to avoid:** Every plan that edits `endgame_zones.py` must include `uv run python scripts/gen_endgame_zones_ts.py` and commit the generated file.

### Pitfall 3: Accordion `value` Controlled Pattern — Filter Reset
**What goes wrong:** If `value` is uncontrolled (`defaultValue`) it cannot be reset on filter change, leaving a collapsed card pointing at a suppressed TC (D-12).
**How to avoid:** Use controlled `value` + `onValueChange`. Use `useEffect` keyed on filter state to call `setExpandedTc(recomputedPrimary)`.

### Pitfall 4: 2×2 Divider Bleeding Through Grid Wrapping
**What goes wrong:** `divide-x` in a 4-column grid that wraps to 2×2 adds vertical dividers after EVERY child, including those at column-end/column-start. The second tile in column 1 and the third tile in column 0 get a vertical divider between them, which is wrong.
**How to avoid:** Use per-cell conditional border classes (`border-r`, `border-t`) keyed on tile index and breakpoint. At `sm` (2 cols): `border-r` on tiles 0, 2 (left column); `border-t` on tiles 2, 3 (bottom row). At `xl` (4 cols): `border-r` on tiles 0, 1, 2 (non-last columns). No `divide-x`/`divide-y` utilities.

### Pitfall 5: `EndgameTypeTile` Using Wrong Gauge `zones` Prop
**What goes wrong:** Tile uses `PER_CLASS_GAUGE_ZONES[class]` (pooled across TC) instead of `PER_CLASS_TC_GAUGE_ZONES[class][tc]`, showing the pre-Phase-97-era mispainted band.
**How to avoid:** The TC context (`tc` prop) is always available at the tile level because tiles are rendered inside a per-TC accordion item. Pass `tc` down and resolve the band from `PER_CLASS_TC_GAUGE_ZONES`.

### Pitfall 6: `categories_by_tc` Not Optional on Wire — Breaking Older Responses
**What goes wrong:** `EndgameStatsResponse` gains a new required field that pre-Phase-98 server responses lack, breaking clients against older backends.
**How to avoid:** Make `categories_by_tc` optional (`| None = None`) in the Pydantic schema and optional in the TS type. Frontend gate: `if (!overviewData?.stats.categories_by_tc) return null;`.

### Pitfall 7: Score Bullet Sig-Gate Breaking if `score_p_value` Not Present on Per-TC Data
**What goes wrong:** The per-TC `EndgameCategoryStats`-shaped object needs `score_p_value` for the Score bullet sig-gate. If the new aggregation doesn't compute it, the tile crashes or always shows "no color."
**How to avoid:** The new `_aggregate_endgame_stats_by_tc()` must compute `score_p_value` (Wilson two-sided test) the same way `_aggregate_endgame_stats()` does for each (class, TC) pair. Or use `null` when `total < PVALUE_RELIABILITY_MIN_N`.

### Pitfall 8: `oldConversionRecoveryStats` Shape Mismatch
**What goes wrong:** `EndgameCategoryStats.conversion` (type `ConversionRecoveryStats`) has fields like `opp_conversion_pct`, `opp_recovery_pct`, `conv_diff_p_value` etc. (visible in test fixtures) that may not exist on the backend's current schema.
**How to avoid:** Check `app/schemas/endgames.py` for the current `ConversionRecoveryStats` definition. The tests have stale fixture fields (`opp_conversion_pct`, `conv_diff_p_value`) from before Phase 87 cleanup — those are test-only artifacts. The wire type and tile code use only `conversion_pct`, `conversion_games`, `recovery_pct`, `recovery_games`, and WDL breakdown.

---

## Code Examples

### Gauge Zone Derivation Pattern (new tile)
```typescript
// Source: EndgameMetricsByTcCard.tsx pattern + Phase 87.1 EndgameTypeCard.tsx
import { PER_CLASS_TC_GAUGE_ZONES } from '@/generated/endgameZones';
import { colorizeGaugeZones } from '@/lib/theme';

// Inside the tile component:
const classBands = category.endgame_class !== 'pawnless'
  ? PER_CLASS_TC_GAUGE_ZONES[category.endgame_class][tc]
  : undefined;

const convZones = classBands ? colorizeGaugeZones(
  0, 100, classBands.conversion[0] * 100, classBands.conversion[1] * 100
) : undefined;

const recovZones = classBands ? colorizeGaugeZones(
  0, 100, classBands.recovery[0] * 100, classBands.recovery[1] * 100
) : undefined;

const [sgNeutralMin, sgNeutralMax] = classBands?.achievable_score_gap ?? [-0.04, 0.04];
```

### Primary-TC Heuristic (shared util, D-09/D-10/D-11)
```typescript
// Suggested location: frontend/src/lib/primaryTc.ts
// (accessible to both EndgameTypeBreakdownSection and future ELO Timeline)

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

### Per-class × TC Band Python Structure
```python
# In app/services/endgame_zones.py — add alongside PER_CLASS_GAUGE_ZONES

@dataclass(frozen=True)
class PerClassTcBands:
    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]

PER_CLASS_TC_GAUGE_ZONES: Mapping[
    EndgameClass,
    Mapping[Literal["bullet", "blitz", "rapid", "classical"], PerClassTcBands]
] = {
    "rook": {
        "bullet": PerClassTcBands(conversion=(0.56, 0.75), recovery=(0.27, 0.43), achievable_score_gap=(-0.05, 0.05)),
        "blitz": PerClassTcBands(conversion=(0.67, 0.82), recovery=(0.20, 0.37), achievable_score_gap=(-0.05, 0.05)),
        "rapid": PerClassTcBands(conversion=(0.69, 0.83), recovery=(0.17, 0.30), achievable_score_gap=(-0.05, 0.05)),
        "classical": PerClassTcBands(conversion=(0.74, 0.87), recovery=(0.13, 0.25), achievable_score_gap=(-0.05, 0.05)),
    },
    "minor_piece": {
        "bullet": PerClassTcBands(conversion=(0.51, 0.73), recovery=(0.29, 0.50), achievable_score_gap=(-0.04, 0.06)),
        "blitz": PerClassTcBands(conversion=(0.64, 0.81), recovery=(0.21, 0.40), achievable_score_gap=(-0.04, 0.06)),
        "rapid": PerClassTcBands(conversion=(0.68, 0.83), recovery=(0.15, 0.33), achievable_score_gap=(-0.04, 0.06)),
        "classical": PerClassTcBands(conversion=(0.75, 0.89), recovery=(0.12, 0.28), achievable_score_gap=(-0.04, 0.06)),
    },
    "pawn": {
        "bullet": PerClassTcBands(conversion=(0.57, 0.80), recovery=(0.25, 0.46), achievable_score_gap=(-0.04, 0.05)),
        "blitz": PerClassTcBands(conversion=(0.68, 0.87), recovery=(0.17, 0.36), achievable_score_gap=(-0.04, 0.05)),
        "rapid": PerClassTcBands(conversion=(0.75, 0.91), recovery=(0.10, 0.28), achievable_score_gap=(-0.04, 0.05)),
        "classical": PerClassTcBands(conversion=(0.80, 0.92), recovery=(0.08, 0.21), achievable_score_gap=(-0.04, 0.05)),
    },
    "queen": {
        "bullet": PerClassTcBands(conversion=(0.64, 0.83), recovery=(0.19, 0.36), achievable_score_gap=(-0.04, 0.05)),
        "blitz": PerClassTcBands(conversion=(0.70, 0.90), recovery=(0.14, 0.31), achievable_score_gap=(-0.04, 0.05)),
        "rapid": PerClassTcBands(conversion=(0.75, 0.92), recovery=(0.08, 0.25), achievable_score_gap=(-0.04, 0.05)),
        "classical": PerClassTcBands(conversion=(0.88, 1.00), recovery=(0.00, 0.09), achievable_score_gap=(-0.04, 0.05)),
    },
    "mixed": {
        "bullet": PerClassTcBands(conversion=(0.60, 0.72), recovery=(0.30, 0.40), achievable_score_gap=(-0.03, 0.04)),
        "blitz": PerClassTcBands(conversion=(0.68, 0.76), recovery=(0.25, 0.35), achievable_score_gap=(-0.03, 0.04)),
        "rapid": PerClassTcBands(conversion=(0.70, 0.79), recovery=(0.23, 0.31), achievable_score_gap=(-0.03, 0.04)),
        "classical": PerClassTcBands(conversion=(0.70, 0.83), recovery=(0.18, 0.30), achievable_score_gap=(-0.03, 0.04)),
    },
    # pawnless omitted: n below per-class TC floor; hidden in live UI
}
```

**Note on queen classical conversion upper bound:** p75 = 100% (30 users, all converted). Clamped at 1.00 — this is a small-n artifact (n=30 users in the classical queen bracket). The band `(0.88, 1.00)` is accurate but will paint nearly every user as "typical" or "weak" in classical queen conversion. Planner note: consider whether to cap at 0.97 editorially or accept the benchmark as-is. The benchmark number is real.

---

## Validation Architecture

**Nyquist validation is ENABLED** (no `workflow.nyquist_validation: false` in `.planning/config.json`).

### Test Framework

| Property | Value |
|---|---|
| Backend framework | pytest (uv run pytest) |
| Frontend framework | Vitest (npm test) |
| Quick run command | `npm test -- --run` (frontend); `uv run pytest -x` (backend) |
| Full suite | `npm test -- --run && uv run pytest` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | Notes |
|---|---|---|---|
| SC-1: full-width collapsible TC cards replace 3-col grid | Unit (React) | `npm test -- --run src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` | Must update existing test |
| SC-2: primary TC expanded, keyboard-accessible with data-testids | Unit (React) | Same | Accordion trigger testid assertions |
| SC-3: 4 type tiles per TC card, Mixed absent | Unit (React) | Same | Assert 4 tiles, no mixed tile |
| SC-4: Conv/Recov gauges present with per-(class × TC) band | Unit (React) | `npm test -- --run src/components/charts/__tests__/EndgameTypeCard.test.tsx` | Restore gauge testid assertions |
| SC-5: Score Gap banded per-(class × TC) | Unit (React) | Same | Assert neutralMin/Max from per-TC band |
| SC-6: zones in endgameZones.ts green (CI drift gate) | Unit (Python) | `uv run python scripts/gen_endgame_zones_ts.py --check` | Automated codegen check |
| SC-7: TC cards self-suppress below MIN_GAMES_PER_TC_CARD | Unit (React) | EndgameTypeBreakdownSection test | Pass < 20 games per TC in fixture |
| SC-8: LLM path unaffected (response shape additive) | Unit (Python) | `uv run pytest tests/ -k endgame` | Add regression test on `EndgameStatsResponse.categories` unchanged |
| SC-9: mobile layout renders (no ragged multi-col) | Integration/manual | Manual browser test | `data-testid="endgame-type-breakdown-section"` verifiable |
| SC-10: all CI gates pass | CI | `uv run ruff check; uv run ty check; uv run pytest; npm run lint; npm test; npm run knip` | Pre-PR checklist |

### Wave 0 Gaps (Test Files to Create/Update)

- `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` — update: remove `grid-cols-3` assertion, add accordion + 4-tile assertions, add Mixed-absent assertion.
- `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx` — update: restore Conv/Recov gauge assertions (testids `…-conv-gauge`, `…-recov-gauge`), update for per-TC band props.
- `tests/test_endgame_service.py` (or equivalent) — add: test for `_aggregate_endgame_stats_by_tc()` output shape + values for known fixture rows.
- `frontend/src/lib/__tests__/primaryTc.test.ts` (new) — unit test for `computePrimaryTc()`: argmax of `games × NOMINAL_DURATION`, respect games floor, handle all-zero case.

---

## Environment Availability

Step 2.6: No external dependencies beyond the project's own stack. Python 3.13 + uv + PostgreSQL (Docker) are confirmed present per the dev environment. No new runtime dependencies introduced.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `ConversionRecoveryStats.conversion_pct` and `.recovery_pct` are on a 0-100 scale (percent), not 0-1 fraction | §4 Code Examples | Gauge values would be 100× too high or too low |
| A2 | `EndgameGauge` accepts `value` on 0-100 scale and `zones` as `{from, to}` arrays also on 0-100 (or 0-1 with `maxValue=1`) | §5 | Gauge would render at wrong position |
| A3 | Test fixture fields `opp_conversion_pct`, `conv_diff_p_value` in `EndgameTypeBreakdownSection.test.tsx` are stale artifacts not present on the current wire schema | §8 | Test fixtures need more surgery than expected |

**Note on A1/A2:** The pre-removal `EndgameTypeCard.tsx` passes `value={category.conversion.conversion_pct}` and `maxValue={100}`, and gauge zones are derived via `colorizeGaugeZones(0, 100, lo * 100, hi * 100)` (multiplying the 0-1 fraction by 100). This confirms the 0-100 convention at the component boundary. The zone registry stores 0-1 fractions. The `colorizeGaugeZones` call converts them.

---

## Open Questions

1. **Queen classical recovery upper bound clamp.** The benchmark shows `p25=0%, p75=9%` for queen classical recovery (n=35 users). Band `(0.00, 0.09)` is legitimate but very narrow. Should the planner editorially widen to `(0.00, 0.15)` for stability, or accept the benchmark as-is?
   - What we know: n=35 users, p25=0%, p75=9%. TC d=1.67 (keep separate) confirms per-TC is correct.
   - What's unclear: whether this n is stable enough for the tight band to be trustworthy vs an artifact of the small classical queen cohort.
   - Recommendation: accept the benchmark `(0.00, 0.09)` as-is per the "use benchmark numbers" rule; note the caveat in the zone comment.

2. **Backend response field name for `categories_by_tc`.** Planner must choose the exact shape. Two viable options: (a) `dict[TC, list[EndgameCategoryStats]]` — matches the existing `EndgameCategoryStats` shape, reuses the same TS type; (b) a slimmer new type with only the fields needed by the tile (wins/draws/losses/total/conversion/recovery/score_gap). Option (a) is simplest; option (b) avoids computing LLM-only fields (Score Gap CI, `type_achievable_score_gap_*`) per-TC.
   - Recommendation: start with option (a) for simplicity; the extra fields computed per-TC add minor CPU overhead but no correctness risk.

3. **Accordion `value` type.** Radix accordion `type="single"` `value` accepts `string`. TC strings `"bullet"|"blitz"|"rapid"|"classical"` work directly. Confirm the `AccordionItem value` prop matches the TC string exactly when used as the reset key.

---

## Sources

### Primary (HIGH confidence — codebase reads)
- `app/services/endgame_zones.py` — `PER_CLASS_GAUGE_ZONES`, `TC_METRIC_BANDS`, `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`, `MIN_GAMES_PER_TC_CARD`, `assign_per_class_zone`
- `scripts/gen_endgame_zones_ts.py` — codegen structure and patterns
- `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` — divider grammar template (~line 347)
- `frontend/src/components/charts/EndgameTimePressureSection.tsx` — per-TC card scaffolding
- `frontend/src/components/ui/accordion.tsx` — Radix Accordion API
- `frontend/src/types/endgames.ts` — `EndgameCategoryStats`, `EndgameStatsResponse`, `EndgameOverviewResponse`
- `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` — current 3-col grid (to replace)
- `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx` — locked assertions
- `git show d3453597^:frontend/src/components/charts/EndgameTypeCard.tsx` — pre-removal 5-element anatomy
- `app/services/endgame_service.py` — `_compute_per_tc_metric_cards`, `_aggregate_endgame_stats`, `_findings_conversion_recovery_by_type`
- `app/services/insights_service.py` — `_findings_conversion_recovery_by_type` (LLM path)

### Primary (HIGH confidence — benchmark report)
- `reports/benchmark/benchmarks-latest.md` §3.4.1 — per-(class × TC) conversion/recovery IQR tables and Cohen's d verdicts
- `reports/benchmark/benchmarks-latest.md` §3.4.2 — per-class ΔES Score-Gap TC collapse verdicts (all collapse, d < 0.2)
- `reports/benchmark/benchmarks-latest.md` §3.2.1 — TC_METRIC_BANDS values (already in code; cross-referenced)

### Secondary (MEDIUM confidence)
- `.planning/phases/98-per-tc-collapsible-endgame-type-cards/98-CONTEXT.md` — locked decisions D-01 through D-15
- `.planning/notes/endgame-tc-disclosure-pattern.md` — mode-3 rationale, primary-TC heuristic, Mixed-drop rationale

---

## Metadata

**Confidence breakdown:**
- Benchmark band numbers: HIGH — read directly from authoritative report
- Zone system structure: HIGH — read from production code
- Backend aggregation path: HIGH — read from production code; model confirmed (Phase 97 `_compute_per_tc_metric_cards`)
- Pre-removal tile anatomy: HIGH — read from `git show d3453597^`
- Accordion API: HIGH — read from `accordion.tsx` and live usage in `Endgames.tsx`
- Divider technique (D-08): MEDIUM — current pattern verified, new two-axis technique is a planner design choice
- Test assertions needed: HIGH — test files read directly

**Research date:** 2026-05-30
**Valid until:** 2026-06-30 (stable codebase domain; benchmark numbers are authoritative from the 2026-05-27 snapshot)

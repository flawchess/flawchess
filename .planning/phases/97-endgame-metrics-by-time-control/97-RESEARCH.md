# Phase 97: Endgame Metrics by Time Control — Research

**Researched:** 2026-05-29
**Domain:** Full-stack restructure: backend per-TC rate aggregation, zone registry expansion, codegen pipeline, frontend TC card layout
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** TC-only cards (bullet/blitz/rapid/classical). No aggregated Conversion/Parity/Recovery cards remain on top. This deliberately removes the current aggregated cards entirely.
- **D-02:** One card per time control, stacked vertically down the page (one TC per row, each reads as a labeled band). Mirror `EndgameTimePressureSection`'s responsive grid/section scaffolding.
- **D-03:** Inside each TC card, the three metric blocks (Conversion / Parity / Recovery) sit side-by-side in a row on desktop and stack on mobile — the same arrangement today's three metric cards use, now nested under a TC card.
- **D-04:** Each metric block = `gauge + WDL chart + ΔES score-gap bullet chart with percentile badge`. WDL is per-block (per metric × TC), as today. This is "today's three aggregated metric cards, replicated per-TC and un-blended."
- **D-05:** Keep the full Conversion / Parity / Recovery trifecta (not dropping parity). Parity's intuitive 50% anchor and per-TC value variation make it diagnostic even though its population band collapses on TC.
- **D-06:** Gauge bands (raw rates): Conversion and Recovery are TC-specific (benchmark §3.2.1 per-TC p25/p75). Parity gauge band stays global (TC d=0.08 → collapses).
- **D-07:** ΔES score-gap bullet bands: Conversion and Recovery ΔES bullets are TC-specific (benchmark §3.2.2). Parity ΔES bullet band stays global (TC d=0.10 → collapses).
- **D-08:** All TC-specific band values come from `reports/benchmark/benchmarks-latest.md` (§3.2.1 for rates, §3.2.2 for ΔES gaps). Implement as a new TC-keyed band structure in `app/services/endgame_zones.py` (model on the existing `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` which is already TC-keyed), then regenerate `frontend/src/generated/endgameZones.ts` via `scripts/gen_endgame_zones_ts.py` (CI drift gate already covers it).
- **D-09:** Per-TC badges are in scope, not deferred. Each card reads its own TC's percentile directly from the existing `user_benchmark_percentiles` rows keyed by `(metric, time_control_bucket)`: `score_gap_conv`, `score_gap_parity`, `recovery_score_gap` (legacy inconsistent naming — leave as-is). No new CDF materialization needed.
- **D-10:** Drop the blended aggregation. Remove the `_aggregate_per_tc_percentile` game-weighted-mean path and the page-level aggregated chips. This is a net simplification of the v1.19 chip logic.
- **D-11:** Badge semantics: gauge shows the raw rate (conversion win% / parity score% / recovery save%); badge shows the per-TC ΔES-gap percentile. The badge pairs with the ΔES bullet directly beneath the WDL. This is the same pairing today's aggregated cards use, just un-blended to per-TC.
- **D-12:** Reuse the existing `MIN_GAMES_PER_TC_CARD` floor (same constant the Time Pressure cards use), applied to the TC's endgame-game count. Card-level suppression (not per-block). Validate the floor is adequate for conditional conv/recov denominators against dev-DB distributions during planning — if clearly too low, flag rather than silently raise.
- **D-13:** Mirror `EndgameTimePressureSection`'s empty/no-eligible-cards state verbatim. If only one TC qualifies, that single card renders alone.
- **D-14:** Cards respect the sidebar TC filter — render only the intersection of (selected TCs) ∩ (eligible TCs). Default aggregated stats stay aggregated across the selected TC set elsewhere; this section is inherently per-TC.
- **D-15:** A new backend aggregation path is required: per-TC conversion/parity/recovery rate values (win% / score% / save%) do not exist today — only per-TC ΔES-gap percentiles do. Group the existing bucket-row query by TC before the bucket split and expose per-TC rate values on the endgame overview response. (Implementation shape is the researcher/planner's call.)
- **D-16:** No `/gsd-ui-phase` — all visual components already exist. Go straight to `/gsd-plan-phase 97`.

### Claude's Discretion

- Exact backend response shape for per-TC rate values.
- Whether the new TC-keyed band structure replaces or sits alongside the existing `BUCKETED_ZONE_REGISTRY` (planner decides; parity must still resolve to the global band).
- knip/dead-code cleanup of the removed aggregated-card components and the `_aggregate_per_tc_percentile` path.

### Deferred Ideas (OUT OF SCOPE)

- Per-TC conversion/recovery RATE percentile badges (vs the ΔES-gap percentiles used now): would require new per-`(conversion_win_pct, tc)` / `(recovery_save_pct, tc)` CDF materialization.
- Filter-responsive bands on any remaining aggregated surfaces.
- Per-class (rook/minor/pawn/queen/mixed) × TC stratification.
</user_constraints>

---

## Summary

Phase 97 restructures the Endgame Metrics section from three aggregated (Conversion/Parity/Recovery) cards into per-time-control cards, each containing the full trifecta. All visual components already exist — `EndgameGauge`, WDL bar, `MiniBulletChart` / `ScoreGapRow`, `PercentileChip` — and `EndgameTimePressureSection`/`EndgameTimePressureCard` are the direct structural templates. The core work is: (1) a new backend aggregation that groups `query_endgame_bucket_rows` results by TC before the bucket split; (2) a new TC-keyed band structure in `endgame_zones.py` (modeled on `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`) codegen'd to `endgameZones.ts`; and (3) a new frontend section component assembling the per-TC cards from the rebuilt response.

The dev-DB distribution check (D-12 validation) shows that `MIN_GAMES_PER_TC_CARD = 20` is **adequate** for the total-TC floor, but the conditional conv/recov denominators are thin in specific cases: a classical-only user with 20+ total endgame games could have as few as 9 recovery games (user 7 classical) or 8 (user 47 classical). The card gate itself is correct — gauge/WDL display is meaningful at 20 games — but recovery rate shown on a card where the recov denominator is <=10 warrants a "thin" `opacity-50` treatment or simply displaying the metric as-is with the gauge styled as confidence-limited. Research recommendation: do not raise the floor, but document that the per-block WDL display already uses the full games count (not the conditional denominator) so the gauge is the only thin-data surface.

The `_aggregate_per_tc_percentile` blended path being dropped is a pure simplification: the per-TC percentile rows already exist in `user_benchmark_percentiles` (keyed by `(metric, time_control_bucket)`) and the Time Pressure cards already consume them directly per-TC without the blended helper — Phase 97 replicates that pattern.

**Primary recommendation:** Add a new `per_tc_metrics: list[EndgameMetricsTcCard]` field on `EndgameOverviewResponse` (not on `ScoreGapMaterialResponse`, which stays for the Overall Performance section). Each `EndgameMetricsTcCard` carries the three rate values, per-bucket WDL rows, ΔES gaps, and per-TC percentile rows — mirroring `TimePressureTcCard`. The existing `ScoreGapMaterialResponse` and its aggregated chips on the Overall Performance section are untouched (only the "Endgame Metrics" section changes).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-TC rate aggregation (conv%, parity%, recov%) | API / Backend | — | Requires a DB query grouping by TC; pure backend computation |
| TC-keyed band constants | API / Backend | Frontend (via codegen) | Python is the authoritative source; TS generated by CI-gated script |
| Per-TC ΔES percentile lookup | API / Backend | — | Already materialized in `user_benchmark_percentiles`; fetched with existing `fetch_for_user` |
| TC card eligibility gate (MIN_GAMES_PER_TC_CARD) | API / Backend | Frontend (import from endgameZones.ts) | Backend pre-filters cards; frontend mirrors constant for potential local suppression |
| Per-TC card layout (stacked rows) | Browser / Client | — | Pure layout component; data comes from API |
| Gauge rendering with per-TC bands | Browser / Client | — | `EndgameGauge` accepts `zones` prop; bands codegen'd to TS |
| WDL bar rendering | Browser / Client | — | `MiniWDLBar` consumes win/draw/loss pct |
| ΔES bullet with per-TC neutral band | Browser / Client | — | `ScoreGapRow` + `MiniBulletChart`; band from codegen'd constants |
| Percentile badge (per-TC) | Browser / Client | — | `PercentileChip` reads per-TC `percentile` from card data |
| Sidebar TC filter intersection | Browser / Client | — | Frontend filters `cards` array by selected TCs, same as Time Pressure section |

---

## Standard Stack

All libraries are already in the project. No new dependencies required.

### Core (Backend)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| FastAPI / SQLAlchemy 2.x async | Locked | HTTP + ORM | Project stack |
| Pydantic v2 | Locked | Response schemas | Project stack |
| `app/services/endgame_zones.py` | — | Zone registry (Python source of truth) | Codegen contract |
| `scripts/gen_endgame_zones_ts.py` | — | Codegen to TS | CI drift gate already enforced |

### Core (Frontend)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `EndgameTimePressureSection.tsx` | — | Layout template (direct mirror) | Per-TC card pattern already solved |
| `EndgameTimePressureCard.tsx` | — | Card shell template | TC label, total count, grid, empty-state |
| `EndgameGauge.tsx` | — | Gauge visualization | `zones` prop accepts any `GaugeZone[]` |
| `MiniWDLBar` / `ScoreGapRow` | — | WDL + ΔES bullet | Already in `EndgameMetricCard` |
| `PercentileChip` | — | Per-TC badge | Already wired with `flavor`, `tc`, `percentile` |
| `colorizeGaugeZones` (from `theme.ts`) | — | Colors gauge zone bands | Used by all existing gauges |
| `frontend/src/generated/endgameZones.ts` | — | TC-keyed band constants | Codegen target |

### No New Packages
No external packages are installed by this phase.

---

## Package Legitimacy Audit

Not applicable — this phase installs no external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
sidebar TC filter (selected TCs)
        │
        ▼
GET /api/endgames/overview
        │
        ├─ [existing] query_endgame_bucket_rows → bucket_rows
        │       (game_id, endgame_class, result, user_color, eval_cp, eval_mate)
        │
        ├─ [NEW] _compute_per_tc_metric_cards(bucket_rows, percentile_rows)
        │       ├─ group by time_control_bucket (join games.time_control_bucket)
        │       ├─ for each TC: classify into conv/parity/recov buckets
        │       ├─ compute win%/score%/save% rates + WDL counts per bucket
        │       ├─ compute ΔES gaps per bucket (same logic as existing gaps_by_bucket)
        │       ├─ read per-TC percentile from percentile_rows[metric][tc]
        │       └─ suppress cards where total < MIN_GAMES_PER_TC_CARD
        │
        ├─ EndgameOverviewResponse.per_tc_metrics: list[EndgameMetricsTcCard]
        │
        ▼
Frontend: EndgameMetricsByTcSection
        │
        ├─ filter cards by sidebar selectedTimeControls ∩ eligible TCs
        ├─ render cards in fixed order: bullet → blitz → rapid → classical
        │
        └─ for each EndgameMetricsTcCard:
               ├─ TC label header (TimeControlIcon + label + total)
               └─ 3-column metric row (desktop) / stacked (mobile)
                      ├─ Conversion block: EndgameGauge(TC-specific zones)
                      │     + MiniWDLBar + ScoreGapRow(TC-specific band)
                      │     + PercentileChip(score_gap_conv, tc)
                      ├─ Parity block: EndgameGauge(global zones)
                      │     + MiniWDLBar + ScoreGapRow(global band)
                      │     + PercentileChip(score_gap_parity, tc)
                      └─ Recovery block: EndgameGauge(TC-specific zones)
                            + MiniWDLBar + ScoreGapRow(TC-specific band)
                            + PercentileChip(recovery_score_gap, tc)
```

### Recommended Project Structure Changes

```
app/
├── schemas/endgames.py            # Add EndgameMetricsTcCard, PerTcBucketStats
├── services/endgame_zones.py      # Add TC_CONV_GAUGE_ZONES, TC_RECOV_GAUGE_ZONES,
│                                  # TC_CONV_SCORE_GAP_ZONES, TC_RECOV_SCORE_GAP_ZONES
├── services/endgame_service.py    # Add _compute_per_tc_metric_cards(); remove
│                                  # _aggregate_per_tc_percentile(); thread per_tc_metrics
│                                  # into get_endgame_overview
├── repositories/endgame_repository.py   # Add time_control_bucket to query_endgame_bucket_rows
scripts/
├── gen_endgame_zones_ts.py        # Add TC-keyed band emission blocks
frontend/src/
├── generated/endgameZones.ts      # Regenerated (CI drift gate)
├── components/charts/
│   ├── EndgameMetricsByTcSection.tsx    # NEW: orchestrator (mirrors TimePressureSection)
│   ├── EndgameMetricsByTcCard.tsx       # NEW: per-TC card (mirrors TimePressureCard)
│   ├── EndgameMetricBlock.tsx           # NEW (optional): extracted metric block
│   │                                    #   if refactor of EndgameMetricCard is warranted
│   ├── EndgameMetricsSection.tsx        # DELETED
│   └── EndgameMetricCard.tsx            # DELETED (or repurposed as EndgameMetricBlock)
├── pages/Endgames.tsx             # Swap EndgameMetricsSection → EndgameMetricsByTcSection
└── types/endgames.ts              # Add EndgameMetricsTcCard type (mirrors backend schema)
```

---

## D-12: MIN_GAMES_PER_TC_CARD Floor Validation

**Dev-DB findings (queried 2026-05-29, non-guest users 7, 13, 14, 15, 28, 43, 46, 47):**

[VERIFIED: dev-DB direct query via asyncpg]

Per-TC total endgame game counts (rows with `endgame_class IS NOT NULL`, group by game, HAVING count(ply) >= 6):

| User | Bullet | Blitz | Rapid | Classical |
|------|--------|-------|-------|-----------|
| 7 | 13,012 | 32,608 | 658 | 165 |
| 13 | 237 | 4,392 | 42 | — |
| 14 | 6,621 | 4,006 | 3,899 | 206 |
| 15 | — | 89 | 577 | 104 |
| 28 | — | 1,801 | 1,645 | 9 |
| 43 | — | — | 167 | — |
| 46 | 3,689 | 2,033 | 1,508 | — |
| 47 | — | 1,829 | 1,024 | 57 |

Per-TC conditional denominators (conv / recov games within those totals), for TCs with total >= 20:

| User | TC | Conv | Recov | Total |
|------|-----|------|-------|-------|
| 7 | classical | 105 | 9 | 165 |
| 47 | classical | 42 | 8 | 57 |
| 15 | blitz | 41 | 12 | 89 |
| 13 | rapid | 15 | 12 | 42 |
| 15 | classical | 46 | 16 | 104 |

**Assessment:**

The `MIN_GAMES_PER_TC_CARD = 20` floor is **adequate** as the card-level gate. The thinnest cases:
- User 47, classical: 57 total endgame games → card shows. Recovery denominator = 8. That is 8 games out of the classical bucket, which is a real but thin signal.
- User 7, classical: 165 total, recovery = 9. Very thin conditional denominator.

**Recommendation: Keep MIN_GAMES_PER_TC_CARD = 20, do NOT raise it.** The card gate correctly reflects "did you play enough endgames to merit a TC card?". The thin conditional denominator for recovery is no different from the situation in the current aggregated card — a user with many parity games and very few recovery games has always had a thin recovery gauge. The existing `EndgameMetricCard` shows a zero-opacity gauge when `row.games == 0` (the `hasGames` check); if recovery games > 0 but small, the gauge renders normally. This is the correct behavior — the gauge number is accurate, just imprecise.

**Do not flag this as blocking.** Document in the plan that the per-block WDL/gauge is honest at thin denominators; the card-level gate (total games) is the right threshold to use.

---

## D-15: Backend Aggregation Shape

### What exists today

`query_endgame_bucket_rows` returns rows of:
```
(game_id, endgame_class, result, user_color, eval_cp, eval_mate)
```
It does NOT include `time_control_bucket`. The TC filter is applied via `apply_game_filters` in the WHERE clause (so if the sidebar says "blitz only", only blitz games return), but the TC value itself is not projected.

`_aggregate_endgame_stats` iterates these rows to build per-class (rook/minor/pawn/queen/mixed/pawnless) stats, including `gaps_by_bucket` (the ΔES per-bucket accumulator). It has no notion of time control.

`_compute_score_gap_material` receives `bucket_rows` and `gaps_by_bucket` and builds the three aggregated rate scalars + ΔES stats that feed the current `ScoreGapMaterialResponse`.

### Required change

**Option A (recommended): Extend `query_endgame_bucket_rows` to project `time_control_bucket`.**

Add `Game.time_control_bucket` to the SELECT in `query_endgame_bucket_rows`. New row shape:
```
(game_id, endgame_class, result, user_color, eval_cp, eval_mate, time_control_bucket)
```
This is additive and backward-compatible — existing callers that index by position still work if they only read columns 0-5, or we verify no callers do positional indexing past column 5 (there are none — the service layer uses named attribute access on Row objects from SQLAlchemy, or tuple unpacking that stops at index 5).

**Check the callers:**
- `_aggregate_endgame_stats(entry_rows)` — entry_rows comes from `query_endgame_entry_rows`, a different query. Not affected.
- `_compute_score_gap_material(bucket_rows)` — uses `bucket_rows` positionally at indices 0-5 in `_aggregate_bucket_counts`. A 7th column is ignored. Safe.
- The new `_compute_per_tc_metric_cards` reads column 6 for the TC.

**New function: `_compute_per_tc_metric_cards`**

Mirrors `_compute_time_pressure_cards` in structure. Single pass through `bucket_rows`, grouping accumulators by TC. For each TC that meets `MIN_GAMES_PER_TC_CARD`:

```python
@dataclass(slots=True)
class _MetricTcAccumulator:
    conv_wins: int = 0
    conv_draws: int = 0
    conv_total: int = 0
    parity_wins: int = 0
    parity_draws: int = 0
    parity_total: int = 0
    recov_wins: int = 0
    recov_draws: int = 0
    recov_total: int = 0
    total: int = 0
    gaps_conv: list[float] = field(default_factory=list)
    gaps_parity: list[float] = field(default_factory=list)
    gaps_recov: list[float] = field(default_factory=list)
```

After iterating all rows, for each TC with `total >= MIN_GAMES_PER_TC_CARD`:
- `conversion_win_pct = conv_wins / conv_total` (or None if conv_total == 0)
- `parity_score_pct = (parity_wins + 0.5 * parity_draws) / parity_total` (or None)
- `recovery_save_pct = (recov_wins + recov_draws) / recov_total` (or None)
- WDL pcts for each bucket (win_pct, draw_pct, loss_pct — for MiniWDLBar)
- Per-bucket ΔES: `compute_paired_difference_test(gaps_conv)` → (mean, n, p, ci_lo, ci_hi)
- Per-TC percentile: `percentile_rows["score_gap_conv"][tc].percentile` (None-safe)

The ΔES computation reuses `_compute_per_bucket_score_gap` logic (or inlines it). The span-gap values themselves come from `_aggregate_endgame_stats`'s `gaps_by_bucket` — but that is pooled across all TCs. To get per-TC ΔES gaps, the new function must independently accumulate span-gaps per TC.

**Where ΔES span gaps come from:** The ΔES gap for each game requires `entry_eval` and `exit_score` (the span gap = exit_score - ES_entry). Currently, `_aggregate_endgame_stats` processes `entry_rows` (from `query_endgame_entry_rows`, which includes per-span `next_entry_eval`). The bucket_rows from `query_endgame_bucket_rows` do NOT include the span gap directly.

**Two sub-options:**

**D-15 Sub-option A:** Also extend `query_endgame_bucket_rows` to include `next_entry_eval_cp` and `next_entry_eval_mate` (same LEAD columns `query_endgame_entry_rows` already uses). Then `_compute_per_tc_metric_cards` can compute per-TC span gaps from the extended bucket_rows.

**D-15 Sub-option B:** Run `_aggregate_endgame_stats` on a per-TC split of `entry_rows` (from the existing query that already has span data). This requires passing TC-tagged rows to `_aggregate_endgame_stats`, which currently only accepts the whole set. More invasive.

**Sub-option A is recommended**: a single query returns all needed data; the LEAD join is already proven in the existing query.

### Proposed Pydantic schema

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
    percentile: float | None    # per-TC ΔES-gap percentile from user_benchmark_percentiles

class EndgameMetricsTcCard(BaseModel):
    """Per-TC card: Conv/Parity/Recovery trifecta for one time control."""
    tc: Literal["bullet", "blitz", "rapid", "classical"]
    total: int                        # total endgame games in this TC
    conversion: PerTcBucketStats
    parity: PerTcBucketStats
    recovery: PerTcBucketStats

class EndgameMetricsCardsResponse(BaseModel):
    cards: list[EndgameMetricsTcCard]  # pre-filtered to eligible TCs, fixed order
```

Added to `EndgameOverviewResponse`:
```python
endgame_metrics_cards: EndgameMetricsCardsResponse = Field(
    default_factory=lambda: EndgameMetricsCardsResponse(cards=[])
)
```

**Why a new top-level field, not extending `ScoreGapMaterialResponse`:** `ScoreGapMaterialResponse` feeds the Overall Performance section (score gap, timeline, entry eval, material breakdown). It is already large (30+ fields) and its contract is stable. Adding per-TC metric cards there would mix two different UI sections' data in one object. A new `endgame_metrics_cards` field on `EndgameOverviewResponse` is clean and matches the pattern of `time_pressure_cards`.

### `_aggregate_per_tc_percentile` removal

This function (in `endgame_service.py`) and its 5 call sites (for `score_gap`, `score_gap_conv`, `score_gap_parity`, `recovery_score_gap`, `score_gap_achievable`) can be removed. The aggregated chips on the Overall Performance section also need to be dropped from `ScoreGapMaterialResponse` (the `score_gap_conv_percentile`, `score_gap_parity_percentile`, `recovery_score_gap_percentile` fields) and from `EndgamePerformanceResponse`'s `score_gap_percentile` — per D-10.

**Caution:** Check whether any OTHER section's chip still consumes the blended percentile. The `EndgameOverallPerformanceSection` and the `EndgameOverallScoreGapRow` are the places to verify. If those sections still show chips, their aggregated chips also get dropped (D-10 says "page-level aggregated chips" are dropped). Verify in `Endgames.tsx` and `EndgameOverallPerformanceSection.tsx` which fields they consume.

---

## D-08: TC-Keyed Band Structure

### New constants in `endgame_zones.py`

Model on `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`. Add two new TC-keyed registries:

```python
@dataclass(frozen=True)
class TcConvRecovBands:
    """Per-TC typical [lower, upper] bands for Conv/Recov rate and ΔES gap."""
    conv_rate: tuple[float, float]    # gauge band for conversion_win_pct
    recov_rate: tuple[float, float]   # gauge band for recovery_save_pct
    conv_score_gap: tuple[float, float]   # ΔES bullet band for conv bucket
    recov_score_gap: tuple[float, float]  # ΔES bullet band for recov bucket

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

**Parity stays in `BUCKETED_ZONE_REGISTRY` and `ZONE_REGISTRY` unchanged.** The global parity rate band `(0.45, 0.55)` and global parity ΔES band `(-0.04, 0.04)` are still valid. The new TC-keyed structure sits alongside (not replacing) `BUCKETED_ZONE_REGISTRY`.

**`BUCKETED_ZONE_REGISTRY` is NOT removed.** It is still used by `assign_bucketed_zone` (called by the insights service for zone assignment). Only its TS-codegen'd counterpart `FIXED_GAUGE_ZONES` is being replaced in the new per-TC cards. The Python registry and its zone assignment functions stay.

### Band values verification

[VERIFIED: reports/benchmark/benchmarks-latest.md §3.2.1 and §3.2.2, read directly]

**§3.2.1 Rate bands (p25 / p75 per TC):**
- Conversion: bullet (58.8%, 71.9%) / blitz (66.7%, 76.9%) / rapid (69.6%, 80.0%) / classical (68.5%, 83.3%)
- Recovery: bullet (29.5%, 41.2%) / blitz (25.1%, 35.7%) / rapid (21.8%, 33.3%) / classical (17.4%, 31.6%)

These match exactly the values quoted in CONTEXT.md §canonical_refs. No discrepancy found. [VERIFIED: cross-checked CONTEXT.md vs benchmark table]

**§3.2.2 ΔES gap bands (p25 / p75 per TC):**
- Conv ΔES: bullet (-19.5pp, -5.7pp) / blitz (-8.5pp, +0.3pp) / rapid (-6.3pp, +2.1pp) / classical (-5.3pp, +3.8pp)
- Recov ΔES: bullet (+7.4pp, +17.7pp) / blitz (+1.1pp, +8.4pp) / rapid (-0.8pp, +6.2pp) / classical (-3.7pp, +3.5pp)

CONTEXT.md quotes these identically. No discrepancy. [VERIFIED]

**Parity ΔES (global, stays unchanged):** pooled (-3.7pp, +4.1pp) → live `(-0.04, +0.04)`. [VERIFIED: §3.2.2 table]

### Codegen additions in `gen_endgame_zones_ts.py`

Add a `_format_tc_metric_bands()` function that emits:

```typescript
// Phase 97: per-TC gauge + ΔES bullet bands for Conversion and Recovery.
// Source: reports/benchmark/benchmarks-latest.md §3.2.1 (rates) and §3.2.2 (ΔES gaps).
export const TC_METRIC_BANDS: Record<
  'bullet' | 'blitz' | 'rapid' | 'classical',
  {
    convRate: [number, number];
    recovRate: [number, number];
    convScoreGap: [number, number];
    recovScoreGap: [number, number];
  }
> = {
  bullet:    { convRate: [0.588, 0.719], recovRate: [0.295, 0.412], convScoreGap: [-0.195, -0.057], recovScoreGap: [0.074, 0.177] },
  blitz:     { convRate: [0.667, 0.769], recovRate: [0.251, 0.357], convScoreGap: [-0.085, 0.003],  recovScoreGap: [0.011, 0.084] },
  rapid:     { convRate: [0.696, 0.800], recovRate: [0.218, 0.333], convScoreGap: [-0.063, 0.021],  recovScoreGap: [-0.008, 0.062] },
  classical: { convRate: [0.685, 0.833], recovRate: [0.174, 0.316], convScoreGap: [-0.053, 0.038],  recovScoreGap: [-0.037, 0.035] },
} as const;
```

Frontend consumers derive `GaugeZone[]` from these via `colorizeGaugeZones`:
```typescript
// In EndgameMetricsByTcCard.tsx:
const bands = TC_METRIC_BANDS[card.tc];
const convGaugeZones = colorizeGaugeZones([
  { from: 0, to: bands.convRate[0] },
  { from: bands.convRate[0], to: bands.convRate[1] },
  { from: bands.convRate[1], to: 1.0 },
]);
```

Parity gauge zones are read from the existing `FIXED_GAUGE_ZONES.parity` (global, unchanged).

---

## Frontend Component Anatomy

### Layout template: `EndgameTimePressureSection` / `EndgameTimePressureCard`

`EndgameTimePressureSection.tsx` [VERIFIED: read directly]:
- Renders `<section data-testid="time-pressure-cards-section">` with subtitle
- Empty-state: `data-testid="time-pressure-cards-empty"`, text "No time-pressure data yet. Import more games to see this section."
- Grid: `GRID_ONE_CARD / GRID_TWO_CARDS / GRID_THREE_CARDS / GRID_FOUR_CARDS` — named constants, no magic strings
- Iterates `data.cards.map(card => <EndgameTimePressureCard key={card.tc} ... />)`

**New `EndgameMetricsByTcSection.tsx`:** Same structure. Props: `{ data: EndgameMetricsCardsResponse; ratingAnchors?: RatingAnchorsByTc }`. Section label: "How do you score from winning, balanced, and losing endgames, by time control?" Empty state: "No endgame data yet. Import more games to see this section."

Grid layout decision: Phase 97 uses **vertical stacking** (D-02: "one TC per row, each reads as a labeled band"). This means each TC card is full-width. The responsive layout is `w-full mt-2` for all card counts. This differs from `EndgameTimePressureSection` which uses a 2-column grid for 2+ cards. Planner should confirm this with the D-02 requirement ("stacked vertically down the page").

### `EndgameMetricsByTcCard.tsx`

Renders one TC's three metric blocks. Structure:

```tsx
<div className="charcoal-texture rounded-md p-4" data-testid={`metrics-tc-card-${card.tc}`}>
  {/* Header: TC icon + label + total games */}
  <h3>...</h3>
  {/* 3-column grid on desktop, stacked on mobile — D-03 */}
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mt-2">
    <EndgameMetricBlock bucket="conversion" data={card.conversion} tc={card.tc} bands={...} />
    <EndgameMetricBlock bucket="parity" data={card.parity} tc={card.tc} bands={...} />
    <EndgameMetricBlock bucket="recovery" data={card.recovery} tc={card.tc} bands={...} />
  </div>
</div>
```

### `EndgameMetricBlock` (extracted from `EndgameMetricCard`)

The current `EndgameMetricCard` is the metric block anatomy to replicate. Its relevant props for Phase 97 become:
- `bucket` — drives gauge formula (win% for conv, score% for parity, save% for recov)
- `row: { games, win_pct, draw_pct, loss_pct }` — for WDL bar
- `rate: number | null` — for gauge value (was `userR = win% or score% or save%`)
- `scoreGapMean/N/PValue/CiLow/CiHigh` — for ΔES bullet
- `percentile: number | null` — for PercentileChip
- `tc: TimeControlBucket` — for PercentileChip flavor dispatch and band lookup
- `zones: GaugeZone[]` — per-TC zones (computed from `TC_METRIC_BANDS[tc]`)
- `neutralMin/Max: number` — per-TC ΔES bullet band edges (from `TC_METRIC_BANDS[tc]`)

The `PercentileChip` flavor dispatch: `score_gap_conv` → flavor `"conv-score-gap"`, `score_gap_parity` → `"parity-score-gap"`, `recovery_score_gap` → `"recovery-score-gap"`. These are the existing CdfMetricId family names already used in the current cards. Check `PercentileChip`'s `flavor` prop type to confirm the exact string.

### Existing `EndgameMetricsSection.tsx` and `EndgameMetricCard.tsx` — deletion/knip

Both files are **deleted** (D-01). The `EndgameMetricCard` behavior is absorbed into a new `EndgameMetricBlock` (or re-used as a presentational sub-component within `EndgameMetricsByTcCard`). If `EndgameMetricCard` is the only consumer of certain imports (e.g., `BUCKET_DISPLAY_LABELS_WITH_METRIC` from `endgameMetrics.ts`), those should be moved or re-exported where needed. Run `npm run knip` after deletion to surface dead exports.

The `TILE_TESTIDS` pattern from `EndgameMetricsSection.tsx` should carry forward into the new section as `data-testid="metrics-tc-card-{tc}"` at card level and `data-testid="metrics-tc-{tc}-{bucket}"` at metric block level.

### TC filter intersection (D-14)

`Endgames.tsx` currently passes `appliedFilters.timeControls` (a `string[] | null`) to the `useEndgameOverview` hook, which sends it as a query param to the backend. The backend's `apply_game_filters` gates which games are included. The cards returned in `endgame_metrics_cards.cards` will already be TC-filtered by the backend query (since `query_endgame_bucket_rows` uses the filter). No additional frontend filtering of cards by `selectedTimeControls` is needed — the backend returns only the eligible + requested TCs.

This is consistent with how `time_pressure_cards` works: the backend already pre-filters to eligible TCs given the sidebar filter; the frontend iterates whatever cards are returned.

---

## Removal / Cleanup Scope

### Backend removals

1. **`_aggregate_per_tc_percentile`** in `endgame_service.py` — remove function + all 5 call sites.
2. **Aggregated percentile fields on `ScoreGapMaterialResponse`**: `score_gap_conv_percentile`, `score_gap_parity_percentile`, `recovery_score_gap_percentile`, `score_gap_percentile`. These were aggregated blended chips on the Current Metrics section. Remove fields from schema + from `_compute_score_gap_material`.
3. **Aggregated percentile field on `EndgamePerformanceResponse`**: `score_gap_percentile`. Verify whether this is still consumed by the Overall Performance section, or if it too was a Metrics-section chip. If consumed only by the "Endgame Score Gap" chip on the Overall Performance card, keep it; if it was a Metrics-section chip, drop it.
4. **Per-TC breakdown lists on `ScoreGapMaterialResponse`**: `score_gap_conv_per_tc`, `score_gap_parity_per_tc`, `recovery_score_gap_per_tc`, `score_gap_per_tc` — these were tooltip bullet-2 data for the blended chips. Remove if no other consumer needs them after the Metrics-section swap.

**Caution:** Step 4 may need more investigation. The per-TC breakdown lists also feed the tooltip on the Overall Performance section's chips (e.g. the Endgame Score Gap chip tooltip shows per-TC breakdown). Check whether `EndgameOverallScoreGapRow` or `EndgameOverallPerformanceSection` reference any of those fields. If yes, keep those specific fields and only drop the metric-section-specific ones.

### Frontend removals

1. `EndgameMetricsSection.tsx` — delete
2. `EndgameMetricCard.tsx` — delete (or refactor into `EndgameMetricBlock.tsx`)
3. `EndgameMetricCard.test.tsx`, `EndgameMetricsSection.test.tsx` — delete and replace with new component tests
4. Remove import of `EndgameMetricsSection` from `Endgames.tsx`
5. Remove `score_gap_conv_percentile`, `score_gap_parity_percentile`, `recovery_score_gap_percentile` from `types/endgames.ts` `ScoreGapMaterialResponse` if the Overall Performance section does not consume them.

**knip note:** The TS type `MaterialBucket` exported from `endgameZones.ts` is used by `EndgameMetricCard` and `EndgameMetricsSection`. After deletion, verify no other consumer imports it — `endgameMetrics.ts` also exports `MaterialBucket` from `@/types/endgames`, so the codegen'd one may become dead.

---

## Reviewed Todos Assessment

**`2026-05-17-recovery-score-gap-popover-copy.md`** (Reframe Recovery Score Gap popover copy):
- Touches `EndgameMetricCard.tsx` — which will be deleted or refactored in this phase.
- **Recommendation: fold into this phase.** The new `EndgameMetricBlock` (successor to `EndgameMetricCard`) will need popover copy regardless. Writing the correct opponent-first copy at creation time is cheaper than a separate pass. The change is a one-string edit; no test changes required. The planner should add this as a task in Wave 2 (new component authoring).

**`2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`** (invalid `pt-33` in `EndgameScoreOverTimeChart.tsx`):
- Touches `EndgameScoreOverTimeChart.tsx` — this file is **not touched** in Phase 97 (it lives in the Overall Performance section, which is out of scope). The fix is mechanical (one token replacement) but out of scope per CONTEXT.md. **Do not fold.** Leave for a future opportunistic fix.

---

## Common Pitfalls

### Pitfall 1: ΔES span gaps require span-level data (not available in base bucket_rows)
**What goes wrong:** The current `query_endgame_bucket_rows` returns only entry eval, not exit score. Span gaps (`exit_score - ES_entry`) require `next_entry_eval_cp/mate` (the LEAD columns already in `query_endgame_entry_rows`). If the planner adds per-TC ΔES to `_compute_per_tc_metric_cards` without extending the query, gaps will always be empty.
**How to avoid:** Extend `query_endgame_bucket_rows` to include the LEAD columns (same pattern as `query_endgame_entry_rows`). The LEAD `array_agg` trick is already proven in the codebase.
**Warning signs:** `score_gap_n` always 0 in TC cards.

### Pitfall 2: Gauge zone direction — conv/recov Recovery rate is higher-is-better but range is inverted vs intuition
**What goes wrong:** Classical recovery p25=17.4%, p75=31.6%. Bullet p25=29.5%, p75=41.2%. A bullet player who recovers at 35% is "typical" for bullet but would be "strong" (green) against the global `(24%, 36%)` band. If the TC-specific zones are applied correctly, that player stays in the typical (blue) zone.
**How to avoid:** Use `TC_METRIC_BANDS[tc].recovRate` for the gauge when tc is known. The existing global `BUCKETED_ZONE_REGISTRY["recovery_save_pct"]` is pooled and must NOT be used in per-TC cards.

### Pitfall 3: Display shift for ΔES bullet is still needed per-TC
**What goes wrong:** The current `EndgameMetricCard` applies `SCORE_GAP_BUCKET_DISPLAY_SHIFT` (an affine recentering so each bucket's bullet is visually centered on zero). The shift is `midpoint of the pooled neutral band`. For TC-specific bands, the midpoint changes. If the pooled shift is applied to per-TC bands, the bullet will be offset.
**How to avoid:** Recompute `displayShift` per TC from `TC_METRIC_BANDS[tc]`: `shift = -(lower + upper) / 2` for conv/recov. Parity band is global and symmetric, shift = 0.
**Warning signs:** Recovery bullet in classical looks systematically negative (since the classical band midpoint is very close to 0, using the bullet-era global shift of +0.06 would over-shift).

### Pitfall 4: `_aggregate_per_tc_percentile` removal breaks tests
**What goes wrong:** Existing tests may construct `ScoreGapMaterialResponse` with `score_gap_conv_percentile` set, then assert on it. After deletion, those tests compile but the assertions become dead.
**How to avoid:** Search tests for `score_gap_conv_percentile`, `score_gap_parity_percentile`, `recovery_score_gap_percentile` — update or delete those assertions when removing the fields.

### Pitfall 5: `noUncheckedIndexedAccess` in `TC_METRIC_BANDS` access
**What goes wrong:** TypeScript's `noUncheckedIndexedAccess` is enabled (CLAUDE.md). Accessing `TC_METRIC_BANDS[card.tc]` returns `TcConvRecovBands | undefined`. Must narrow before use.
**How to avoid:** Use `const bands = TC_METRIC_BANDS[card.tc];` then `if (bands) { ... }` or non-null assertion if the key is provably in bounds (it is, since `card.tc` is already typed as the correct Literal union).

### Pitfall 6: knip drift from dead exports in `endgameZones.ts`
**What goes wrong:** After deletion of `EndgameMetricsSection` and `EndgameMetricCard`, the exported `FIXED_GAUGE_ZONES`, `SCORE_GAP_CONV_NEUTRAL_MIN/MAX`, etc. may become dead exports that knip flags.
**How to avoid:** After deleting the old components, run `npm run knip` and check for newly-dead exports from `endgameZones.ts`. If `FIXED_GAUGE_ZONES.parity` is still needed (for the parity gauge in the new section), keep the export. If `SCORE_GAP_CONV_NEUTRAL_MIN/MAX` are replaced by `TC_METRIC_BANDS`, the old scalars become dead — remove their emission from the codegen script too.

### Pitfall 7: AsyncSession concurrency — no asyncio.gather
**What goes wrong:** Adding a new DB query for per-TC metrics inside `get_endgame_overview` might tempt use of `asyncio.gather`.
**How to avoid:** Execute sequentially on the same session (CLAUDE.md: "Never use asyncio.gather on the same AsyncSession"). The new computation is a Python-side grouping of the already-fetched `bucket_rows` — no additional DB query needed if bucket_rows is extended to include TC.

---

## Code Examples

### Backend: extending `query_endgame_bucket_rows`

```python
# Source: app/repositories/endgame_repository.py — extend SELECT to add time_control_bucket
stmt = (
    select(
        Game.id.label("game_id"),
        span_subq.c.endgame_class,
        Game.result,
        Game.user_color,
        span_subq.c.entry_eval_cp.label("eval_cp"),
        span_subq.c.entry_eval_mate.label("eval_mate"),
        Game.time_control_bucket,           # NEW — column index 6
        # If adding span-gap support:
        # span_subq.c.next_entry_eval_cp.label("next_entry_eval_cp"),   # index 7
        # span_subq.c.next_entry_eval_mate.label("next_entry_eval_mate"), # index 8
    )
    .join(span_subq, Game.id == span_subq.c.game_id)
    .where(Game.user_id == user_id)
)
```

Return type annotation updated: `list[Row[Any]]` (no change needed).

### Backend: per-TC accumulator iteration pattern (from `_compute_time_pressure_cards`)

```python
# Source: app/services/endgame_service.py — _compute_time_pressure_cards pattern
_TIME_CONTROL_ORDER: list[str] = ["bullet", "blitz", "rapid", "classical"]

cards: list[TimePressureTcCard] = []
for tc in _TIME_CONTROL_ORDER:
    total = tc_total.get(tc, 0)
    if total < MIN_GAMES_PER_TC_CARD:
        continue
    # ... build card
cards.append(TimePressureTcCard(...))
return TimePressureCardsResponse(cards=cards)
```

### Backend: direct per-TC percentile lookup (no blending)

```python
# Source: app/services/endgame_service.py — _compute_time_pressure_cards lines 2174-2178
tc_literal = cast(Literal["bullet", "blitz", "rapid", "classical"], tc)
tc_bucket: TimeControlBucket = tc_literal
conv_row = _effective_rows.get("score_gap_conv", {}).get(tc_bucket)
parity_row = _effective_rows.get("score_gap_parity", {}).get(tc_bucket)
recov_row = _effective_rows.get("recovery_score_gap", {}).get(tc_bucket)
# Then: conv_row.percentile if conv_row is not None else None
```

### Frontend: TC-keyed gauge zone construction

```typescript
// Source: lib/theme.ts (colorizeGaugeZones), endgameZones.ts (TC_METRIC_BANDS)
import { TC_METRIC_BANDS } from '@/generated/endgameZones';
import { colorizeGaugeZones } from '@/lib/theme';

const bands = TC_METRIC_BANDS[card.tc];
// bands is TcConvRecovBands — safe since card.tc is a known TC literal
const convGaugeZones = colorizeGaugeZones([
  { from: 0, to: bands.convRate[0] },
  { from: bands.convRate[0], to: bands.convRate[1] },
  { from: bands.convRate[1], to: 1.0 },
]);
const parityGaugeZones = FIXED_GAUGE_ZONES.parity; // global, unchanged
```

### Frontend: display shift computation for per-TC bands

```typescript
// Recentering the bullet chart (mirrors SCORE_GAP_BUCKET_DISPLAY_SHIFT pattern)
// Shift = -midpoint of the neutral band
const convShift = -(bands.convScoreGap[0] + bands.convScoreGap[1]) / 2;
const recovShift = -(bands.recovScoreGap[0] + bands.recovScoreGap[1]) / 2;
// Parity shift = 0 (band is symmetric around 0)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global pooled gauge bands for all TCs | TC-specific bands for Conv/Recov (this phase) | Phase 97 | Bullet player at 35% recovery shows "typical" not "strong"; classical at 20% recovery shows "typical" not "strong" |
| Blended game-count-weighted percentile chip | Per-TC percentile chip read directly | Phase 97 (drop blended path) | Net simplification; same data already materialized |
| One aggregated Metrics section (3 cards) | Per-TC cards (up to 4 × 3 blocks) | Phase 97 | User sees TC-stratified performance, not a single blended view |

**Deprecated/outdated after this phase:**
- `_aggregate_per_tc_percentile`: blended helper, superseded by direct per-TC lookup (same pattern Time Pressure cards already use)
- `BUCKETED_ZONE_REGISTRY` codegen in `FIXED_GAUGE_ZONES`: the global pooled zones will no longer appear in the Metrics section. The Python registry stays for `assign_bucketed_zone` (LLM insights); only the TS codegen output for the per-bucket gauge display is replaced.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_compute_score_gap_material`'s call to `_aggregate_per_tc_percentile` is the ONLY consumer of blended chips in the "Endgame Metrics" section — no other section on the page will lose chips when it's removed. | Removal/Cleanup | If the Overall Performance section's Endgame Score Gap chip is also fed by `_aggregate_per_tc_percentile`, removing it drops that chip too. Verify by tracing `score_gap_percentile` on `EndgamePerformanceResponse` and `ScoreGapMaterialResponse`. | [ASSUMED] |
| A2 | `per_tc_breakdown` lists (`score_gap_conv_per_tc`, etc.) on `ScoreGapMaterialResponse` are only consumed by the OLD Metrics section's chip tooltips and can be dropped along with the chips. | Removal/Cleanup | If they're also shown in the Overall Performance chip tooltips, removing them breaks that tooltip's per-TC breakdown. | [ASSUMED] |
| A3 | The `SCORE_GAP_BUCKET_DISPLAY_SHIFT` constant in `endgameMetrics.ts` is safe to recompute per-TC dynamically rather than as a file-level constant. | Frontend pattern | No risk — it's a pure arithmetic derivation; the existing constant is just pre-computed for the pooled band midpoints. |

---

## Open Questions

1. **Does `EndgameOverallPerformanceSection` consume any of the aggregated metric chips (`score_gap_conv_percentile`, `score_gap_parity_percentile`, `recovery_score_gap_percentile`)?**
   - What we know: `score_gap_material.score_gap_conv_percentile` is passed as `scoreGapPercentile` in `EndgameMetricsSection.tsx` → `EndgameMetricCard`. This is the section being deleted.
   - What's unclear: Whether `EndgameOverallPerformanceSection` or `EndgameOverallScoreGapRow` also read these fields directly from `score_gap_material`.
   - Recommendation: The planner should grep `score_gap_conv_percentile`, `score_gap_parity_percentile`, `recovery_score_gap_percentile` in the frontend before finalizing the removal scope. If found in the Overall Performance section, those fields stay on the schema.

2. **Should `EndgameMetricCard.tsx` be deleted or refactored into `EndgameMetricBlock.tsx`?**
   - What we know: The component is self-contained and all its logic is needed in the new per-TC card.
   - Recommendation: Refactor (rename + prop adjustments for TC-specific bands) rather than delete + rewrite. Reduces diff size and preserves test coverage patterns.

3. **Does the per-TC vertical stacking layout (D-02, "one TC per row") mean all cards are full-width, or should the same 2/3/4-column staircase from `EndgameTimePressureSection` apply?**
   - What we know: D-02 says "stacked vertically down the page (one TC per row, each reads as a labeled band)". This clearly means full-width stacking, not a 2-column grid.
   - Recommendation: Full-width (`w-full mt-2` for all card counts). Do not apply the Time Pressure 2-column grid. Confirm with user if ambiguous.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL | D-12 DB queries | ✓ | 18 (Docker) | — |
| Python 3.13 / uv | Backend + codegen | ✓ | 3.13.12 | — |
| Node.js / npm | Frontend | ✓ | — | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest + SQLAlchemy async fixtures |
| Frontend framework | Vitest + React Testing Library |
| Backend quick run | `uv run pytest tests/services/test_endgame_service.py -x` |
| Backend full run | `uv run pytest -x` |
| Frontend quick run | `npm test -- --run --reporter=verbose` |
| Frontend drift check | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | Notes |
|----------|-----------|-------------------|-------|
| `_compute_per_tc_metric_cards` returns correct rate values for each TC | unit | `pytest tests/services/test_endgame_service.py::test_compute_per_tc_metric_cards -x` | Wave 0: create test |
| `EndgameOverviewResponse.endgame_metrics_cards` populated correctly | integration | `pytest tests/services/test_endgame_service.py::test_get_endgame_overview_per_tc_metrics -x` | Existing `get_endgame_overview` test can be extended |
| `_aggregate_per_tc_percentile` is gone (grep guard) | structural | `grep -r "_aggregate_per_tc_percentile" app/ tests/` exits non-zero | Add to CI if desired |
| TC-keyed bands in `endgameZones.ts` are current | drift | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | Already in CI |
| `EndgameMetricsByTcSection` renders cards in bullet→classical order | unit | `npm test -- --run EndgameMetricsByTcSection` | Wave 0: create test |
| `EndgameMetricsByTcSection` shows empty state when `cards=[]` | unit | same file | |
| Per-TC gauge zones apply TC-specific bands (not global) | unit | `npm test -- --run EndgameMetricsByTcCard` | Assert `convGaugeZones[1].from === TC_METRIC_BANDS.bullet.convRate[0]` |
| knip clean after deletion | knip | `npm run knip` | Run after deleting old files |
| ty + ruff clean | type | `uv run ty check app/ tests/ && uv run ruff check app/ tests/` | Pre-push gate |

### Wave 0 Gaps

- [ ] `tests/services/test_endgame_service.py` — add `test_compute_per_tc_metric_cards` with fixture rows including a TC column
- [ ] `tests/services/test_endgame_service.py` — update `test_get_endgame_overview` to assert `endgame_metrics_cards` is populated
- [ ] `frontend/src/components/charts/__tests__/EndgameMetricsByTcSection.test.tsx` — new file (mirrors `EndgameTimePressureSection.test.tsx` structure)
- [ ] `frontend/src/components/charts/__tests__/EndgameMetricsByTcCard.test.tsx` — new file (mirrors `EndgameTimePressureCard.test.tsx`)
- [ ] Delete `EndgameMetricCard.test.tsx` and `EndgameMetricsSection.test.tsx` when the source files are deleted

---

## Security Domain

`security_enforcement` applies. No new auth/session surfaces; no new input vectors; no new crypto. Existing V4 scoping (`user_id` from FastAPI-Users dep, never from query params) is maintained. The new `_compute_per_tc_metric_cards` function takes `bucket_rows` already fetched with the authenticated user's ID — no new V4 surface.

| ASVS Category | Applies | Control |
|---------------|---------|---------|
| V4 Access Control | yes (existing) | `user_id` flows from FastAPI-Users dep into `get_endgame_overview` orchestrator; new function receives pre-scoped rows |
| V5 Input Validation | yes (existing) | `time_control_bucket` validated via Pydantic Literal type on response schemas |
| Others | no | No new auth, session, crypto, or file upload surfaces |

---

## Sources

### Primary (HIGH confidence)
- `app/services/endgame_zones.py` — verified all registries: `BUCKETED_ZONE_REGISTRY`, `ZONE_REGISTRY`, `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`, `MIN_GAMES_PER_TC_CARD`, `PER_CLASS_GAUGE_ZONES`
- `app/services/endgame_service.py` — verified `_compute_time_pressure_cards`, `_aggregate_per_tc_percentile`, `get_endgame_overview`, `_compute_score_gap_material`, `_aggregate_endgame_stats`
- `app/repositories/endgame_repository.py` — verified `query_endgame_bucket_rows` return shape (columns 0-5, no TC)
- `app/repositories/user_benchmark_percentiles_repository.py` — verified `fetch_for_user` nested dict shape
- `app/schemas/endgames.py` — verified `EndgameOverviewResponse`, `ScoreGapMaterialResponse`, `TimePressureTcCard`, `PerTcBreakdownOut`
- `frontend/src/components/charts/EndgameTimePressureSection.tsx` — verified layout template
- `frontend/src/components/charts/EndgameMetricCard.tsx` — verified metric block anatomy
- `frontend/src/components/charts/EndgameMetricsSection.tsx` — verified orchestrator to replace
- `frontend/src/generated/endgameZones.ts` — verified current TS constants
- `scripts/gen_endgame_zones_ts.py` — verified codegen pipeline
- `reports/benchmark/benchmarks-latest.md` §3.2.1 and §3.2.2 — verified all TC band values
- Dev-DB queries (asyncpg 2026-05-29) — per-TC game counts and conditional denominators

### Secondary (MEDIUM confidence)
- `frontend/src/pages/Endgames.tsx` — verified `EndgameMetricsSection` usage location (line 585) and surrounding section structure

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Backend aggregation shape: HIGH — code read directly; pattern mirrors existing `_compute_time_pressure_cards` exactly
- Zone registry design: HIGH — band values verified against benchmark; dataclass pattern mirrors `PressureBinBand`
- Frontend component assembly: HIGH — all components exist; anatomy read directly from source
- Removal scope (A1/A2 assumptions): MEDIUM — needs confirmation of which chips the Overall Performance section consumes

**Research date:** 2026-05-29
**Valid until:** 2026-06-29 (stable codebase — no fast-moving dependencies)

# Phase 97: Endgame Metrics by Time Control - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the **Endgame Metrics section** of the Endgames page from single aggregated Conversion/Parity/Recovery cards into **per-time-control cards** (bullet/blitz/rapid/classical), mirroring the existing `EndgameTimePressureSection` per-TC card pattern.

Each TC card holds the Conversion/Parity/Recovery trifecta; each metric block is `gauge + WDL + ΔES score-gap bullet (with per-TC percentile badge)`. Conversion and Recovery get TC-specific neutral bands (they keep-separate on the TC axis per the benchmark); Parity keeps the global band (collapses on TC). The blended/aggregated percentile path is dropped — badges read per-TC rows directly.

**In scope:** the Endgame Metrics section only (the conv/parity/recov cards + their gauges, WDL, ΔES bullets, badges) and the backend/zone plumbing it needs.

**Out of scope (untouched this phase):** the Endgame Overall Performance section (score-over-time, Endgame ELO timeline, score-gap cards), the Time Pressure section, and the Endgame Type Breakdown section. Per-TC conversion/recovery **rate** percentile CDFs are NOT built (the existing ΔES-gap per-TC percentiles are reused as the badges).

</domain>

<decisions>
## Implementation Decisions

### Card structure
- **D-01:** TC-only cards (bullet/blitz/rapid/classical). **No aggregated Conversion/Parity/Recovery cards remain** on top. This deliberately removes the current aggregated cards entirely.
- **D-02:** One card per time control, **stacked vertically** down the page (one TC per row, each reads as a labeled band). Mirror `EndgameTimePressureSection`'s responsive grid/section scaffolding.
- **D-03:** Inside each TC card, the three metric blocks (Conversion / Parity / Recovery) sit **side-by-side in a row** on desktop and **stack on mobile** — the same arrangement today's three metric cards use, now nested under a TC card.
- **D-04:** Each metric block = `gauge + WDL chart + ΔES score-gap bullet chart with percentile badge`. WDL is per-block (per metric × TC), as today. This is "today's three aggregated metric cards, replicated per-TC and un-blended."
- **D-05:** Keep the full **Conversion / Parity / Recovery trifecta** (not dropping parity). Parity's intuitive 50% anchor and per-TC value variation (e.g. time-management issues surfacing as sub-50% bullet/blitz parity) make it diagnostic even though its population band collapses on TC.

### Bands (neutral zones)
- **D-06:** **Gauge bands (raw rates):** Conversion and Recovery are **TC-specific** (benchmark §3.2.1 per-TC p25/p75; TC Cohen's d ≈ 0.93 / 0.90 → keep-separate). **Parity gauge band stays global** (TC d=0.08 → collapses; one band is correct for every TC).
- **D-07:** **ΔES score-gap bullet bands:** Conversion and Recovery ΔES bullets are **TC-specific** (benchmark §3.2.2; TC d=1.25 / 1.69 → keep-separate). **Parity ΔES bullet band stays global** (TC d=0.10 → collapses). Rationale: a bullet player's typical conversion ΔES (~−12pp) is normal for bullet `(−0.195, −0.057)` but looks awful against the global `(−0.11, 0.00)` band, and the per-TC badge would visibly contradict a global band.
- **D-08:** All TC-specific band values come from `reports/benchmark/benchmarks-latest.md` (§3.2.1 for rates, §3.2.2 for ΔES gaps). Implement as a **new TC-keyed band structure** in `app/services/endgame_zones.py` (model on the existing `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` which is already TC-keyed), then regenerate `frontend/src/generated/endgameZones.ts` via `scripts/gen_endgame_zones_ts.py` (CI drift gate already covers it).

### Percentile badges
- **D-09:** Per-TC badges are **in scope, not deferred.** Each card reads its own TC's percentile directly from the **existing** `user_benchmark_percentiles` rows keyed by `(metric, time_control_bucket)`: `score_gap_conv`, `score_gap_parity`, `recovery_score_gap` (legacy inconsistent naming — leave as-is). No new CDF materialization needed.
- **D-10:** **Drop the blended aggregation.** Remove the `_aggregate_per_tc_percentile` game-weighted-mean path and the page-level aggregated chips. This is a net simplification of the v1.19 chip logic.
- **D-11:** Badge semantics: gauge shows the **raw rate** (conversion win% / parity score% / recovery save%); badge shows the **per-TC ΔES-gap percentile** (skill-adjusted: actual minus engine-expected score in that bucket's situations). The badge pairs with the ΔES bullet directly beneath the WDL. This is the same pairing today's aggregated cards use, just un-blended to per-TC.

### Eligibility & empty state
- **D-12:** Reuse the existing `MIN_GAMES_PER_TC_CARD` floor (same constant the Time Pressure cards use), applied to the TC's endgame-game count. Card-level suppression (not per-block). **Validate the floor is adequate for conditional conv/recov denominators against dev-DB distributions during planning** — if clearly too low, flag rather than silently raise.
- **D-13:** Mirror `EndgameTimePressureSection`'s empty/no-eligible-cards state verbatim. If only one TC qualifies, that single card renders alone.
- **D-14:** Cards respect the sidebar TC filter — render only the intersection of (selected TCs) ∩ (eligible TCs). Default aggregated stats stay aggregated across the selected TC set elsewhere; this section is inherently per-TC.

### Backend
- **D-15:** A **new backend aggregation path** is required: per-TC conversion/parity/recovery **rate values** (win% / score% / save%) do not exist today — only per-TC ΔES-gap percentiles do. Group the existing bucket-row query by TC before the bucket split and expose per-TC rate values on the endgame overview response. (Implementation shape is the researcher/planner's call.)

### Process
- **D-16:** **No `/gsd-ui-phase`** — all visual components already exist (gauge, WDL, ΔES bullet, badge) and `EndgameTimePressureSection` is a direct layout template. This is a re-grouping of existing pieces, not new visual design. Go straight to `/gsd-plan-phase 97`.

### Claude's Discretion
- Exact backend response shape for per-TC rate values.
- Whether the new TC-keyed band structure replaces or sits alongside the existing `BUCKETED_ZONE_REGISTRY` (planner decides; parity must still resolve to the global band).
- knip/dead-code cleanup of the removed aggregated-card components and the `_aggregate_per_tc_percentile` path.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Benchmark band/zone source of truth
- `reports/benchmark/benchmarks-latest.md` §3.2.1 — per-TC Conversion/Parity/Recovery **rate** distributions + collapse verdicts (gauge bands). Conversion bullet (0.588, 0.719) / blitz (0.667, 0.769) / rapid (0.696, 0.800) / classical (0.685, 0.833); Recovery bullet (0.295, 0.412) / blitz (0.251, 0.357) / rapid (0.218, 0.333) / classical (0.174, 0.316); Parity collapses (global band).
- `reports/benchmark/benchmarks-latest.md` §3.2.2 — per-TC **Section-2 ΔES Score Gap** distributions + collapse verdicts (ΔES bullet bands). Conv ΔES bullet (−0.195, −0.057)/blitz (−0.085, +0.003)/rapid (−0.063, +0.021)/classical (−0.053, +0.038); Recov ΔES bullet (+0.074, +0.177)/blitz (+0.011, +0.084)/rapid (−0.008, +0.062)/classical (−0.037, +0.035); Parity ΔES collapses (global `(−0.04, +0.04)`).

### Zone system (code source of truth)
- `app/services/endgame_zones.py` — `BUCKETED_ZONE_REGISTRY` (current pooled conv/parity/recov rate bands), `ZONE_REGISTRY` (`section2_score_gap_conv/parity/recov` ΔES bands), `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (existing TC-keyed structure to model the new bands on), `MIN_GAMES_PER_TC_CARD`.
- `scripts/gen_endgame_zones_ts.py` — regenerates `frontend/src/generated/endgameZones.ts`; CI fails on drift, re-run after editing the Python registry.
- `frontend/src/generated/endgameZones.ts` — generated bands consumed by the gauge/bullet components.

### Layout template & current components
- `frontend/src/components/.../EndgameTimePressureSection.tsx` + `EndgameTimePressureCard.tsx` — the per-TC card pattern to mirror (card selection by `MIN_GAMES_PER_TC_CARD`, silent percentile suppression on null, responsive `GRID_*_CARDS` staircase, fixed bullet/blitz/rapid/classical order, empty state).
- `frontend/src/pages/Endgames.tsx` — hosts the Endgame Metrics section (and the Overall Performance / Time Pressure / Endgame Type sections that stay untouched).
- The current `EndgameMetricsSection.tsx` / `EndgameMetricCard.tsx` + `EndgameGauge` — the metric-block anatomy (gauge + WDL + ΔES bullet + badge) being replicated per-TC and the aggregated cards being removed.

### Percentile data
- `app/repositories/user_benchmark_percentiles_repository.py` — `fetch_for_user()` returns nested `result[metric][tc] → PercentileRow`; metrics `score_gap_conv`, `score_gap_parity`, `recovery_score_gap` are the per-TC badge source.
- `app/services/endgame_service.py` — `_aggregate_per_tc_percentile` (the blended path to remove), `query_endgame_bucket_rows` / bucket aggregation (the per-TC rate-value query to add), `_compute_time_pressure_cards` (per-TC card backend pattern to mirror).

### Project conventions
- `CLAUDE.md` — theme constants in `theme.ts`, `data-testid` on interactive elements, mobile parity, `text-sm` floor (tooltip exception), no magic numbers, Sentry capture rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EndgameTimePressureSection` / `EndgameTimePressureCard`: direct structural template — per-TC card selection, responsive grid, empty state, null-percentile suppression.
- `EndgameGauge`, the WDL chart component, the ΔES score-gap bullet component, and the percentile badge component: all exist on today's metric cards and are re-grouped, not redesigned.
- `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`: existing TC-keyed band structure to model the new conv/recov TC bands on.
- `user_benchmark_percentiles` + `fetch_for_user()`: per-TC percentile rows already materialized for the three ΔES metrics — badges come for free.

### Established Patterns
- Zone bands are the Python source of truth (`endgame_zones.py`) codegen'd to TS (`endgameZones.ts`) with a CI drift gate — new bands must go through `gen_endgame_zones_ts.py`.
- Per-TC cards gate on `MIN_GAMES_PER_TC_CARD` and suppress whole cards below the floor.
- Sidebar `timeControls` filter flows through `apply_game_filters`; stats already re-scope by TC.

### Integration Points
- New per-TC rate-value query slots into the endgame overview service alongside the existing per-TC ΔES percentile fetch.
- New TC-keyed band export consumed by the per-TC metric blocks in the new section component.
- Removal of `_aggregate_per_tc_percentile` and the aggregated metric cards (knip-clean the now-unused exports).

</code_context>

<specifics>
## Specific Ideas

- Inspiration: Lichess Tutor (Beta) uses TC-specific endgame pages. FlawChess keeps a single page with the sidebar TC filter for aggregated views, but makes the keep-separate metrics (Conversion/Recovery) TC-correct via per-TC cards in this one section.
- The benchmark report is the explicit, numeric source of truth for every TC-specific band; the per-TC p25/p75 tables are already computed there.
- User's own example as the design north star: a player with time-management problems shows sub-50% parity in bullet/blitz but ~50% in classical — the per-TC parity values must surface that even though the parity band is global.

</specifics>

<deferred>
## Deferred Ideas

- **Per-TC conversion/recovery RATE percentile badges** (vs the ΔES-gap percentiles used now): would require new per-`(conversion_win_pct, tc)` / `(recovery_save_pct, tc)` CDF materialization in `user_benchmark_percentiles` (truncate + recompute). Not needed — the existing ΔES-gap per-TC percentiles serve as the badges. Revisit only if ranking the raw rate (not the skill-adjusted gap) becomes desirable.
- **Filter-responsive bands on any remaining aggregated surfaces** (single TC selected → that TC's band): not applicable here since the section is fully per-TC, but noted as a general pattern if aggregated gauges resurface elsewhere.
- **Per-class (rook/minor/pawn/queen/mixed) × TC stratification**: out of scope; the Endgame Type Breakdown section is untouched.

### Reviewed Todos (not folded)
- `2026-05-17-recovery-score-gap-popover-copy.md` (Reframe Recovery Score Gap popover copy — opponent-first): touches the recovery ΔES bullet copy this phase reuses; consider folding during planning if the popover is reworked, otherwise leave for its own pass.
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md` (invalid Tailwind class on Score Y-axis label): relates to a score chart that may be reused; minor, fix opportunistically if the file is touched.
- `2026-04-26-phase-70-requirements-roadmap-amendments.md`: unrelated (Phase 70 planning amendment) — keyword match only.

</deferred>

---

*Phase: 97-endgame-metrics-by-time-control*
*Context gathered: 2026-05-29*

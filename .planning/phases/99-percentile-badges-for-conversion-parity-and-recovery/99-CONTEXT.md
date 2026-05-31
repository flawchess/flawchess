# Phase 99: Percentile Badges for Conversion, Parity, and Recovery - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Add peer-relative **raw-rate** percentile chips (the v1.19 `PercentileChip` primitive) to the per-TC Conversion / Parity / Recovery cards delivered in Phase 97. This is the badge work deferred from Phase 97 ("Per-TC conversion/recovery percentile badges are deferred to a follow-up phase").

It requires materializing **12 new per-(rate metric, TC) cohort CDFs** in `user_benchmark_percentiles` (`{conversion_rate, parity_rate, recovery_rate} × {bullet, blitz, rapid, classical}`), computed via the shared `canonical_slice_sql.py` pooled-per-user builder parameterised by TC, cohort-matched on the per-(user, TC) rating anchor, and surfaced with the 4-bullet disclosure tooltip per `feedback_percentile_chip_tooltip_disclosure`.

**In scope:** the new raw-rate percentile chips on the Phase 97 per-TC metric cards (`EndgameMetricsByTcCard`), the 12 new ENUM metrics + cohort-CDF materialization + per-user lookup + backfill, and the tooltip wiring.

**Out of scope:** the existing ΔES score-gap percentile chips (they stay exactly as-is, on the ΔES bullets — NOT removed), the Endgame Type Breakdown section (Phase 98), the Time Pressure section, the Endgame ELO Timeline, and any LLM payload work (Phase 100). No new visual primitives — `PercentileChip` is reused.

</domain>

<decisions>
## Implementation Decisions

### Chip model (rate chip vs existing gap chip)
- **D-01:** **Show BOTH chips per metric block.** The new raw-rate percentile chip does NOT replace the existing ΔES score-gap percentile chip. Each Conversion / Parity / Recovery metric now surfaces two percentiles: the raw-rate rank (new) and the skill-adjusted ΔES-gap rank (existing, unchanged).
- **D-02:** **Placement:** the new raw-rate chips render on the **Conversion / Parity / Recovery title lines, right-aligned.** The existing ΔES-gap chips stay where they are today (on/near the ΔES score-gap bullet via `block.percentile`). Precedent: the Time Pressure per-TC cards already show 3 chips per card; this mirrors that title-line chip pattern.
- **D-03:** **Two-chip differentiation is carried by the tooltips, not new visual treatment.** No inline qualifier label is added. The title-line chip's tooltip describes the **raw rate** vs peers ("conversion rate"); the bullet chip's tooltip describes the **skill-adjusted gap** vs peers ("conversion score gap"). The metric-noun swap in D-08 is sufficient to distinguish them. Rationale captured: the two percentiles can diverge sharply (a ~1200 player may sit ~75th on raw conversion rate but ~40th on the skill-adjusted gap, because raw rate tracks ELO harder) — the tooltips must make clear which is which.

### Inclusion floor (chip suppression)
- **D-04:** **Reuse the Phase 94.3 per-metric chip inclusion floor** — the same percentile-inclusion floor the Time Pressure per-TC chips use, applied per (metric, TC). Below floor → no chip renders (Success Criterion 1). This is the chip-visibility floor and is distinct from Phase 97's card-rendering floor (`MIN_GAMES_PER_TC_CARD`); a card can render while one of its rate chips suppresses.
- **D-05:** Conversion and Recovery are conditional rates with thin per-TC denominators (carried over from Phase 97). **Validate the reused floor against dev-DB per-(metric, TC) denominator distributions during research/planning** — if clearly inadequate for conv/recov, flag rather than silently raise.

### Parity treatment
- **D-06:** **Parity gets its own per-(parity_rate, TC) cohort CDF** like conversion and recovery — all 12 metrics are per-TC (4 TCs each). This holds even though parity's neutral *band* collapses on TC (one global band, decided in Phase 97 D-06). The neutral band (zone coloring) and the percentile (peer ranking cohort) are **independent signals**: a per-TC cohort is the correct basis for ranking parity rate, while a single global band remains correct for zone coloring. Do not conflate the two — the band staying global is not a reason to collapse the percentile cohort.

### Tooltip disclosure
- **D-07:** **Reuse the 4-bullet disclosure contract verbatim** per `feedback_percentile_chip_tooltip_disclosure` (cohort framing, recent-games basis, filter independence, rating-anchor composition). First two bullets are TC-scoped (Success Criterion 4). No structural change to the contract.
- **D-08:** Only the **metric noun in bullet 1 changes** to name the raw rate (e.g. "conversion rate" / "parity rate" / "recovery rate") rather than the score-gap metric. The rate chips reuse the existing per-(user, TC) rating-anchor composition prose unchanged.

### Backend / materialization
- **D-09:** 12 new metrics added to the `user_benchmark_percentiles` ENUM: `{conversion_rate, parity_rate, recovery_rate}_{bullet, blitz, rapid, classical}`. Computed via the **shared `canonical_slice_sql.py` pooled-per-user builder parameterised by TC** — the same builder constructs both the cohort CDF and the per-user lookup, so drift between CDF construction and per-user value remains structurally impossible (Success Criterion 2).
- **D-10:** Cohort CDFs generated into `app/services/global_percentile_cdf.py` (or its cohort-CDF sibling) under the existing per-(metric, ELO anchor, TC) sliding-window protocol, with the regen report archived (Success Criterion 3).
- **D-11:** Backfill script populates the 12 new metrics on **dev first**, then **prod via `prod_db_tunnel.sh` after sign-off** (Success Criterion 5). Standard rollout, not a gray area.

### Claude's Discretion
- Exact ENUM member naming/casing and migration shape for the 12 new metrics (planner/researcher's call; criterion 2 names them functionally).
- Direction/sign convention per rate (higher rate → higher percentile is the obvious default for all three: more conversion, more parity score%, more recovery saves = better) — `PercentileChip` already encodes "higher percentile = better"; confirm the rate is fed in the correct orientation.
- Whether the new rate-percentile fields ride on the existing per-TC block payload (`block.percentile` sibling) or a new field on the metric/title-line level — backend response shape is the planner's call, but it must be a *separate* field from the existing gap `block.percentile` (D-01: both coexist).
- knip/dead-code posture: this phase ADDS chips, removes nothing from Phase 97; no cleanup expected.
- No `/gsd-ui-phase` — `PercentileChip` and the per-TC card are existing components; this is wiring a second chip onto an existing layout, not new visual design.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Percentile chip pattern & disclosure (the thing being mirrored)
- `frontend/src/components/charts/PercentileChip.tsx` — the chip primitive (percentile, anchorRating, nGames, value, tooltip props). Reused as-is.
- `frontend/src/components/charts/EndgameTimePressureCard.tsx` — the per-TC card that already shows multiple chips on title lines; the title-line right-aligned chip placement to mirror (D-02).
- Memory `feedback_percentile_chip_tooltip_disclosure` (project memory) — the MANDATORY 4-bullet tooltip contract, including the 2026-05-27 Phase 94.4 amendment (cohort framing + rating-anchor composition prose, 3 platform branches). First two bullets TC-scoped.

### Phase 97 cards being extended (the host surface)
- `frontend/src/components/charts/EndgameMetricsByTcCard.tsx` — the per-TC Conversion/Parity/Recovery card. Today renders one chip per block bound to the ΔES score-gap percentile (`block.percentile`, near the ΔES bullet). Phase 99 adds the title-line rate chips here without disturbing the existing gap chip.
- `.planning/phases/97-endgame-metrics-by-time-control/97-CONTEXT.md` — Phase 97 decisions (per-TC card structure D-01..D-05, bands D-06..D-08, the deferred-rate-badge note this phase fulfills). The deferred idea "Per-TC conversion/recovery RATE percentile badges (vs the ΔES-gap percentiles used now)" IS this phase.

### Percentile materialization infrastructure
- `app/models/user_benchmark_percentile.py` — the `user_benchmark_percentiles` ENUM (currently `score_gap_conv`, `score_gap_parity`, `recovery_score_gap`); the 12 new `*_rate_{tc}` members are added here (D-09).
- `app/services/canonical_slice_sql.py` — the shared pooled-per-user builder; parameterise by TC so CDF construction and per-user lookup share one code path (D-09, drift-proof per criterion 2).
- `app/services/global_percentile_cdf.py` — the cohort-CDF store; the per-(metric, ELO anchor, TC) sliding-window CDFs are generated here (D-10).
- `app/repositories/user_benchmark_percentiles_repository.py` — `fetch_for_user()` returns nested `result[metric][tc] → PercentileRow`; the new rate metrics surface through this same path.
- `app/services/endgame_service.py` — where the per-TC metric card payload is assembled; the new rate-percentile field is threaded onto the per-TC blocks here (separate from the existing gap `block.percentile`).

### Cohort / anchor methodology (already locked, read for fidelity)
- `reports/benchmark/benchmarks-latest.md` — per-TC rate distributions (the cohort population basis; §3.2.1 per-TC Conversion/Parity/Recovery rates).
- Phase 94.3 / 94.4 Time Pressure per-TC chip implementation — the pooled-per-user, per-(user, TC) rating-anchor, per-metric chip-inclusion-floor pattern being mirrored (D-04). (Phase dir under `.planning/phases/94*`; locate the Time Pressure per-TC chip plan during research.)

### Project conventions
- `CLAUDE.md` — `text-sm` floor (tooltip `text-xs` exception applies to the disclosure body), `data-testid` on interactive elements, mobile parity (apply title-line chip to both desktop + mobile renderers), theme constants in `theme.ts`, no magic numbers (the chip floor is a named constant), Sentry capture rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PercentileChip.tsx`: the chip is reused unchanged; only a second instance per metric block (title-line, right-aligned) plus its rate-percentile data + tooltip strings.
- `EndgameMetricsByTcCard.tsx`: already wires one `PercentileChip` (the ΔES-gap chip via `block.percentile` + `anchorRating`); the new rate chip follows the same null-suppression + anchor-gating pattern (`percentile != null && anchorRating != null`).
- `canonical_slice_sql.py`: the single pooled-per-user SQL builder — extend its metric parameterisation to the 3 rate families × TC rather than writing a parallel path (keeps CDF/lookup drift-proof).
- `user_benchmark_percentiles` + `fetch_for_user()`: the nested `[metric][tc] → PercentileRow` shape already serves the gap chips; the rate chips slot into the same structure once the ENUM + CDFs exist.

### Established Patterns
- Percentile chips suppress silently below a per-(metric) inclusion floor and when the anchor is null — mirror exactly (D-04).
- Cohort CDFs are per-(metric, ELO anchor, TC) sliding-window, regenerated into `global_percentile_cdf.py` with an archived regen report (D-10) — CI/regen discipline already established.
- Backfill runs dev → prod-via-tunnel after sign-off (D-11); existing percentile backfill scripts are the template.

### Integration Points
- New ENUM members → new cohort CDFs (regen) → new per-user backfill rows → new field on the per-TC block payload (`endgame_service.py`) → new title-line chip in `EndgameMetricsByTcCard.tsx` (desktop + mobile) with its own tooltip strings.
- The existing ΔES-gap chip path is untouched — the two chip data sources coexist on the same block (D-01).

</code_context>

<specifics>
## Specific Ideas

- North-star precedent: the **Time Pressure per-TC cards already show 3 chips per card** — Phase 99's title-line rate chips deliberately mirror that chip grammar so the Endgame Metrics cards read consistently with the Time Pressure cards.
- The two-percentile divergence is a feature, not a bug: raw-rate rank and skill-adjusted (ΔES) rank intentionally tell different stories (where you sit on the headline number vs how you perform relative to engine expectation). The tooltips must surface that distinction (D-03).

</specifics>

<deferred>
## Deferred Ideas

- **Inline "rate" / "gap" qualifier labels on the chips** — considered for at-a-glance differentiation; deferred in favor of tooltip-carried distinction (D-03). Revisit only if users report confusion between the two chips in situ.
- **Rework of the tooltip rating-coupling framing for raw rates** — considered (raw conversion rate may track ELO even harder than the skill-adjusted gap); deferred. The peer-relative cohort framing already absorbs rating coupling per Phase 94.4, so the contract is reused verbatim (D-07/D-08). Revisit if UAT shows raw-rate chips mislead despite cohort framing.
- **LLM narration of the new rate percentiles** — out of scope; belongs to Phase 100 (LLM Endgame-Insights Statistical-Reasoning Rework).

None — discussion otherwise stayed within phase scope.

</deferred>

---

*Phase: 99-percentile-badges-for-conversion-parity-and-recovery*
*Context gathered: 2026-05-30*

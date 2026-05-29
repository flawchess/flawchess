# Phase 97: Endgame Metrics by Time Control - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 97-endgame-metrics-by-time-control
**Areas discussed:** Percentile chips fate, Score Gap chart per card, Min-games floor + empty state, Card layout + UI phase

---

## Pre-discussion locked decisions (from design conversation before /gsd-discuss-phase)

Carried in from the benchmark analysis + design conversation; not re-asked:
- TC-only cards, no aggregated cards on top.
- Keep the Conversion/Parity/Recovery trifecta per card.
- Conversion + Recovery get TC-specific bands; Parity keeps the global band.
- Cards self-suppress below a min-games floor.
- Bands sourced from `reports/benchmark/benchmarks-latest.md` §3.2.1 (and §3.2.2 after discussion).

---

## Percentile chips fate

| Option | Description | Selected |
|--------|-------------|----------|
| Accept the gap | Ship TC cards with no conv/parity/recov percentile chips this phase; defer per-TC badges. | |
| Keep aggregated chips in a header | Render the game-weighted aggregated chips once above the TC cards. | |
| Pull per-TC badges into this phase | Build new per-(metric, TC) rate CDFs now for correctly-scoped badges. | |
| **(User free-text)** | Per-TC percentiles already exist in `user_benchmark_percentiles` (`score_gap_conv`, `score_gap_parity`, `recovery_score_gap`); use them directly per card, drop the blended aggregation. | ✓ |

**User's choice:** Use the existing per-TC percentile rows directly as badges; drop the blended/aggregated percentile path (simplification).
**Notes:** Confirmed pairing — gauge = raw rate, badge = ΔES-gap percentile (Section-2 ΔES Score Gap, skill-adjusted). Badges are NOT percentiles of the raw rates (those have no per-TC CDF). Legacy inconsistent metric naming left as-is.

---

## Score Gap chart per card

| Option | Description | Selected |
|--------|-------------|----------|
| Endgame Score Gap (eg − non_eg, ±0.10) | Top-level score-gap | |
| Achievable Score Gap (actual − expected, ±0.05) | Paired engine-adjusted gap | |
| **(Resolved by card-anatomy)** | The existing Section-2 ΔES per-bucket bullet chart already sitting below the WDL on each metric card. | ✓ |

**User's choice:** The score-gap chart is the Section-2 ΔES per-bucket bullet (`score_gap_conv` / `score_gap_parity` / `recovery_score_gap`), one per metric block, paired with the percentile badge.
**Notes:** Each TC card holds three blocks (Conversion/Parity/Recovery); each block = gauge + WDL + ΔES score-gap bullet with percentile badge. Consequence locked: ΔES bullet bands also go TC-specific for conv/recov (§3.2.2 keep-separate, d=1.25/1.69), parity ΔES band stays global (d=0.10).

---

## Min-games floor + empty state

| Option | Description | Selected |
|--------|-------------|----------|
| **Reuse Time Pressure floor** | Use existing `MIN_GAMES_PER_TC_CARD`. | ✓ |
| Higher dedicated floor | Separate higher floor for conditional rates. | |
| Per-block suppression | Blank individual blocks below their conditional count. | |
| **Mirror Time Pressure (empty state)** | Reuse `EndgameTimePressureSection`'s no-eligible-cards state. | ✓ |
| Explicit guidance message | Tailored "import more games in TC X" empty state. | |

**User's choice:** Reuse `MIN_GAMES_PER_TC_CARD`; mirror the Time Pressure empty state.
**Notes:** Validate the floor against dev-DB distributions during planning (conditional conv/recov denominators are thin); flag if clearly inadequate rather than silently raising.

---

## Card layout + UI phase

| Option | Description | Selected |
|--------|-------------|----------|
| **Blocks in a row, cards stacked** | Three blocks side-by-side per card; TC cards stacked vertically. | ✓ |
| Blocks in a row, cards in a grid | TC cards 2-up on wide screens. | |
| Metric × TC matrix | Rows = metric, columns = TC. | |
| **Skip UI phase** | Go straight to planning, reuse Time Pressure layout. | ✓ |
| Run /gsd-ui-phase | Produce a UI-SPEC.md design contract first. | |

**User's choice:** Blocks in a row, TC cards stacked vertically; skip the UI phase.
**Notes:** All visual components already exist; this is a re-grouping, not new visual design. Mobile stacks the blocks.

---

## Claude's Discretion

- Exact backend response shape for per-TC rate values.
- Whether the new TC-keyed band structure replaces or sits alongside `BUCKETED_ZONE_REGISTRY`.
- knip/dead-code cleanup of removed aggregated-card components and `_aggregate_per_tc_percentile`.

## Deferred Ideas

- Per-TC conversion/recovery RATE percentile badges (new CDF materialization) — not needed; ΔES-gap percentiles serve as badges.
- Filter-responsive bands on aggregated surfaces — not applicable here (section is fully per-TC).
- Per-class × TC stratification — Endgame Type Breakdown section untouched.
- Reviewed-not-folded todos: recovery-score-gap popover copy (2026-05-17), pt-33 Tailwind axis label (2026-05-18), Phase 70 amendments (keyword match only).

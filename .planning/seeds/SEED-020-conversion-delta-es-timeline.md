---
id: SEED-020
status: open
planted: 2026-05-17
revised: 2026-10-31 (opponent-mirror reference dropped; Conv ΔES is a shared-state metric under the governing rule in `.planning/notes/opponent-mirror-as-self-calibrating-cohort.md`; reference is now a rating-matched peer band)
planted_during: /gsd-explore session during Phase 88 (Time Pressure stats rework). Triggered by the §3.2.3 finding in `reports/benchmarks-latest.md` that Conversion ΔES has the strongest cohort effect of any benchmark metric on the ELO axis (Cohen's d = 1.62 across 800→2400, ranging −14.0pp to −0.3pp). User asked whether a Conversion ΔES timeline, with optional per-TC breakdown, would surface real signal beyond what the Endgame ELO timeline already shows.
trigger_when: After Phase 88 (Time Pressure rework) and Phase 89 (polish) ship and the Endgames page stabilizes. Surface when (a) users start asking "am I getting better at converting in bullet specifically?" type questions, or (b) the next endgame-analytics expansion is being scoped.
scope: phase (1-2 plans) — backend per-(platform × TC × week) aggregator for user Conv ΔES plus the user's rating anchor per week, a peer-band lookup against `benchmark_cohort_cdf` (`score_gap_conv`), frontend timeline component reusing EndgameEloTimelineSection patterns, popover copy. No new benchmark artifact: the `score_gap_conv` cohort CDF already exists per (anchor_elo, TC).
depends_on: Phase 87.6 (Endgame ELO via PR with dual lines + signed band) ships first — this chart shares its visual language (per-combo lines, ≥33% active-weeks filter, weekly buckets).
---

# SEED-020: Conversion Score Gap timeline with a rating-matched peer band

> **Revised 2026-10-31.** The original design used an opponent-mirror line (opponents' Conv ΔES in
> their own converting positions against the user). That line is the user's own Recovery ΔES, negated,
> so it compares the user with themselves and misattributes recovery weakness to conversion. The
> reference is now the cohort CDF's typical band at the user's rating and TC. Reasoning below and in
> `.planning/notes/opponent-mirror-as-self-calibrating-cohort.md` (governing rule, "Retracted" section).

## The product question

The §3.2.2 benchmark verdict ranks Conversion ΔES as `keep separate` on both TC and ELO axes (d=1.02 TC, d=1.62 ELO). It is a *genuine* two-axis metric: bullet players and rapid players really do convert differently, and the cohort effect on ELO is the strongest of any metric in the benchmark. A single scalar in Section 2 of the Endgames page collapses both axes. A timeline plus optional per-TC breakdown would expose:

1. **Are you improving at converting winning positions over time?** (temporal signal)
2. **Which TC do you convert best in?** (cross-TC signal, separate from raw conversion rate, because ΔES adjusts for what the engine expected)

The Endgame ELO timeline answers a related but distinct question (overall endgame performance vs your non-endgame baseline). Conversion ΔES isolates the conversion subskill specifically.

## The design call: raw ΔES with a rating-matched peer band

Framings considered:

- **Cohort-adjusted ΔES** (subtract the cohort median at each point). Rejected in the 2026-05 session: everyone hovers near zero with a noise band.
- **Raw ΔES with an opponent-mirror line.** Chosen in 2026-05, dropped on 2026-10-31 (see next section).
- **Raw ΔES against a zero line.** Rejected: Conversion's typical band sits well below zero (converting a winning position scores ~5pp below entry ES, see `endgame_zones.py`), so a zero reference paints every typical user as underperforming.
- **Raw ΔES with a rating-matched peer band** *(chosen)*. The user's line is drawn raw. Behind it, per (platform × TC) combo, a shaded band shows the cohort's typical range (p25–p75) of `score_gap_conv` at the user's rating anchor for that week, read from `benchmark_cohort_cdf`.

The peer band keeps what the mirror was supposed to deliver:

- **Rating-matched and drift-aware.** The band follows the user's rating week by week, so a rising line inside a rising band reads as "improving at the pace of your rating", and a line pulling above the band reads as real conversion gain.
- **TC-matched.** The CDF is keyed by TC.
- **No new artifact.** `score_gap_conv` is already one of the 11 `CdfMetricId` families with per-(anchor_elo, TC) breakpoints.

What it gives up relative to the mirror: a runtime dependency on the benchmark CDF table, and the cancellation of measurement bias (the user's evals must come from the same source and ply convention as the cohort's before the band is trusted; check lichess server evals vs. local Stockfish).

## Why the opponent mirror was dropped

Conversion ΔES is computed only on games where the player entered the endgame up material:

- **User Conv ΔES** = user's ΔES on games where the user entered the endgame up.
- **Opponent mirror Conv ΔES** = opponents' ΔES on games where the opponent entered the endgame up, i.e. the games where the user was down.

The 2026-05 version argued these are disjoint sets and therefore not an algebraic negation. That is true, but ΔES is zero-sum per game (`ΔES_opp = −ΔES_user`), so the mirror over those games is exactly the negated user Recov ΔES. It is a number the user already has, not a peer reference. Plotting it against the user's Conv ΔES compares the user's conversion with their own recovery.

Worked example: typical conversion (Conv ΔES 0), weak recovery (Recov ΔES −0.10). The mirror sits at +0.10, so the chart says "you convert worse than your opponents" when the user's conversion is fine and the weakness is in recovery. The 2026-05 design acknowledged the "recovery fold" and planned to handle it with honest labelling, but no label fixes a reference that points at the wrong subskill. This is the same structure as "came out worse vs. came out better" in SEED-206.

## Data availability — confirmed

`game_positions.eval_cp` stores the raw engine evaluation per ply (see `app/models/game_position.py:105`). Reuse the eval-baselining machinery already in place for the per-user Conv ΔES (Phase 87.2 / `app/services/endgame_service.py`). The peer band reads `benchmark_cohort_cdf` via `app/repositories/benchmark_cohort_cdf_repository.py`; the anchor grid step is `COHORT_ANCHOR_STEP_ELO = 50` (`app/services/global_percentile_cdf.py`). No opponent-side aggregation is needed.

## Proposed scope (1-2 plans)

### Plan 1 — Backend aggregator + endpoint

- Repository function in `app/repositories/endgame_repository.py` that returns per-(platform × TC × week) rows with: user Conv ΔES, user converting-game count, user's rating anchor for that week (e.g. median game-time rating, rounded to the 50-Elo grid). Same canonical CTE shape as the Endgame ELO timeline.
- Band lookup: for each distinct (anchor, TC) in the result, fetch the `score_gap_conv` cell from `benchmark_cohort_cdf` once and attach p25 / p75 (or whichever band width the planner settles on) to each weekly point.
- Service-level filtering: apply the `MIN_ACTIVE_WEEKS_RATIO = 0.33` active-weeks rule per combo, matching `EndgameEloTimelineSection.tsx:111`. Combos that fail the filter are dropped entirely.
- Schema: extend the endgames response with a `conv_score_gap_timeline` field. Match the existing `endgame_elo_timeline` shape where possible so the frontend component can be a near-copy.
- Sample-size gate per weekly bucket: drop weeks with fewer than N converting games (likely reuse `PVALUE_RELIABILITY_MIN_N` or a small dedicated constant like 3-5; calibrate during implementation).

### Plan 2 — Frontend chart + popover

- New `ConversionScoreGapTimelineSection.tsx`, structurally cloned from `EndgameEloTimelineSection.tsx`. Per active combo: the user line (full colour) and a shaded peer band (same hue, low opacity).
- Placement: stacked under the Endgame ELO timeline in the Endgame Metrics section.
- Popover copy (per memory `feedback_popover_copy_minimalism.md`): WHAT it shows + sign convention, and that the band is the typical range for players at your rating in that time control. No methodology jargon.
- Apply to both desktop and mobile (CLAUDE.md mobile-parity rule). Reuse the responsive patterns from `EndgameEloTimelineSection`.

## Design decisions captured

- **Raw ΔES, not cohort-adjusted.** Explicit user choice (2026-05). The drifting line reads better than a flat near-zero residual; the band supplies the context.
- **Peer band, not opponent mirror.** Conv ΔES is shared-state; the mirror would compare conversion with the user's own recovery (2026-10-31).
- **Not a zero line.** Conversion's typical band sits off zero.
- **≥33% active-weeks TC filter reused, not re-derived.** Consistency with the ELO timeline avoids cognitive load when users compare both charts.

## Open decisions (defer until phase planning)

- **Weekly noise vs. cohort spread.** The CDF describes per-user values pooled over many games (recent-3000 pool), while a weekly point covers only a handful of converting games. Weekly points will scatter well outside a p25–p75 band of long-run means. Options: (a) plot a rolling window (e.g. trailing N converting games) instead of raw weekly values; (b) keep weekly points but treat the band as a level reference only, never as a "you are outside the typical range" signal; (c) widen the band. Decide at planning time.
- **Single platform per chart vs combined?** Per-(platform × TC) combos each with a band could get crowded. Options: (a) merge platforms into a single line per TC if both pass the active-weeks filter; (b) keep per-(platform × TC) and rely on the filter; (c) add a platform toggle. Note the CDF is not split by platform, so the band is the same for both platforms at equal rating, which ignores the chess.com vs lichess rating offset.
- **Band styling and width.** p25–p75 vs the zone band from `endgame_zones.py`; shaded area vs dashed bounds. Affects readability with 3+ combos.
- **Sample-size gate threshold.** PVALUE_RELIABILITY_MIN_N=10 is a strong gate but may leave too few weekly points in bullet for casual users; a smaller bucket-level minimum (e.g. 3) with the line drawn only across spans of qualifying weeks may be better.
- **Recovery companion chart.** If a Recovery ΔES timeline follows, show it as its own chart with its own band, never as the reference line for Conversion.

## Why this is a phase, not a /gsd-quick

The backend aggregator is non-trivial (eval-baselined, weekly bucketed, rating-anchored, with band lookup, sample gating and active-weeks filtering) and the frontend chart needs the same care as the existing timeline charts (legend toggling, mobile parity, popover wiring, accessibility test IDs). Comparable in shape to Phase 87.5/87.6.

## Cross-references

- Governing rule and retraction: `.planning/notes/opponent-mirror-as-self-calibrating-cohort.md`.
- Shared-state precedent: SEED-206 (came out of the opening worse/better).
- Benchmark evidence: `reports/benchmarks-latest.md` §3.2.2 (axis-collapse verdicts table) and §3.2.3 (rate-vs-gap divergence). The d=1.62 ELO cohort effect on Conv ΔES is the empirical anchor.
- Peer band source: `app/services/global_percentile_cdf.py` (`score_gap_conv`, anchor grid), `app/repositories/benchmark_cohort_cdf_repository.py`, off-zero conversion band in `app/services/endgame_zones.py`.
- Visual prior art: `frontend/src/components/charts/EndgameEloTimelineSection.tsx` (the structural template, including `MIN_ACTIVE_WEEKS_RATIO = 0.33`).
- Data source: `app/models/game_position.py:105` (`eval_cp`); current ΔES machinery in `app/services/endgame_service.py` and `app/repositories/endgame_repository.py` from Phase 87.2.
- Adjacent seed: SEED-019 (cohort percentile annotations). SEED-020 now reuses its CDF artifact as a timeline band.
- Popover discipline: project memory `feedback_popover_copy_minimalism.md`.

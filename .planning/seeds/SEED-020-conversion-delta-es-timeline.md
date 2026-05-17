---
id: SEED-020
status: open
planted: 2026-05-17
planted_during: /gsd-explore session during Phase 88 (Time Pressure stats rework). Triggered by the §3.2.3 finding in `reports/benchmarks-latest.md` that Conversion ΔES has the strongest cohort effect of any benchmark metric on the ELO axis (Cohen's d = 1.62 across 800→2400, ranging −14.0pp to −0.3pp). User asked whether a Conversion ΔES timeline, with optional per-TC breakdown, would surface real signal beyond what the Endgame ELO timeline already shows.
trigger_when: After Phase 88 (Time Pressure rework) and Phase 89 (polish) ship and the Endgames page stabilizes. Surface when (a) users start asking "am I getting better at converting in bullet specifically?" type questions, or (b) the next endgame-analytics expansion is being scoped and the same /benchmarks pass can produce any needed reference data.
scope: phase (1-2 plans) — backend per-(platform × TC × week) aggregator for user Conv ΔES + opponent-mirror Conv ΔES, frontend timeline component reusing EndgameEloTimelineSection patterns, popover copy. Smaller than SEED-019 because no new benchmark artifact is needed (self-calibrating from the user's own games).
depends_on: Phase 87.6 (Endgame ELO via PR with dual lines + signed band) ships first — this chart shares its visual language (per-combo lines, ≥33% active-weeks filter, weekly buckets).
---

# SEED-020: Conversion Score Gap timeline with opponent-mirror reference

## The product question

The §3.2.2 benchmark verdict ranks Conversion ΔES as `keep separate` on both TC and ELO axes (d=1.02 TC, d=1.62 ELO). It is a *genuine* two-axis metric: bullet players and rapid players really do convert differently, and the cohort effect on ELO is the strongest of any metric in the benchmark. A single scalar in Section 2 of the Endgames page collapses both axes. A timeline plus optional per-TC breakdown would expose:

1. **Are you improving at converting winning positions over time?** (temporal signal)
2. **Which TC do you convert best in?** (cross-TC signal, separate from raw conversion rate, because ΔES adjusts for what the engine expected)

The Endgame ELO timeline answers a related but distinct question (overall endgame performance vs your non-endgame baseline). Conversion ΔES isolates the conversion subskill specifically.

## The design call: raw ΔES with an opponent-mirror line

Two framings were considered in the explore session:

- **Cohort-adjusted ΔES** (subtract the median of the user's (ELO bucket × TC bucket) cell at each point). Conceptually pure but reads poorly: everyone hovers near zero with a noise band.
- **Raw ΔES with an opponent-mirror reference line** *(chosen)*. The user's line drifts upward as their ELO climbs (consistent with the d=1.62 cohort effect), but is contextualized by a dimmer companion line per (platform × TC) showing **the user's opponents' Conv ΔES when those opponents were in converting positions**.

The opponent-mirror line is **self-calibrating**:

- Opponents are rating-matched (platform matchmaking pairs you with peers).
- Opponents are TC-matched (a bullet game pairs you with a bullet-rated opponent).
- The reference drifts with the user automatically as they climb.
- No /benchmarks DB dependency at runtime; everything derives from the user's imported games.
- No Lichess-vs-chess.com calibration offset (the issue that complicates SEED-019's global CDF).

## The non-obvious wrinkle: which positions count

Conversion ΔES is computed only on positions where *the player is up material*. Therefore:

- **User Conv ΔES** = user's performance on games where the *user* entered the endgame up.
- **Opponent mirror Conv ΔES** = opponents' performance on games where the *opponent* entered the endgame up — which are the games where the *user* was down.

These are disjoint sets of games. They are not the algebraic negation of each other (that confusion is easy to fall into because for any single position, `ES_opponent = 1 − ES_user`; but Conversion ΔES is restricted to converting positions, which differ by side).

**Implication for labeling:** the mirror line is *not* pure "peer conversion ability." It folds in the user's own *recovery* skill — a tenacious defender depresses opponents' Conv ΔES against them. Popover copy must call it "your opponents' mirror" or "opponents' Conv ΔES vs you," not "peer cohort average." The composite interpretation is actually a feature for users ("in winning positions, do I outscore my opponents in *their* winning positions?") provided the label is honest.

## Data availability — confirmed

`game_positions.eval_cp` stores the raw engine evaluation per ply (see `app/models/game_position.py:105`). Entry expected score is a sigmoid on `eval_cp` and is one-sided (`ES_opp = 1 − ES_user`). Computing the opponent-perspective ΔES is purely a query/aggregation change, not a data-availability issue. Reuse the same eval-baselining machinery already in place for the existing per-user Conv ΔES (Phase 87.2 / `app/services/endgame_service.py`), oriented to the opposite side.

## Proposed scope (1-2 plans)

### Plan 1 — Backend aggregator + endpoint

- Repository function in `app/repositories/endgame_repository.py` that returns per-(platform × TC × week) rows with: user Conv ΔES, user converting-game count, opponent Conv ΔES, opponent converting-game count. Same canonical CTE shape as the Endgame ELO timeline.
- Service-level filtering: apply the `MIN_ACTIVE_WEEKS_RATIO = 0.33` active-weeks rule per combo, matching `EndgameEloTimelineSection.tsx:111`. Combos that fail the filter are dropped entirely (both user and mirror line).
- Schema: extend the endgames response with a `conv_score_gap_timeline` field. Match the existing `endgame_elo_timeline` shape so the frontend component can be a near-copy.
- Sample-size gate per weekly bucket: drop weeks with fewer than N converting games (likely reuse `PVALUE_RELIABILITY_MIN_N` or a small dedicated constant like 3-5; calibrate during implementation).

### Plan 2 — Frontend chart + popover

- New `ConversionScoreGapTimelineSection.tsx`, structurally cloned from `EndgameEloTimelineSection.tsx`. Two lines per active combo: user line (full color) and opponent-mirror line (same hue, lower opacity or dashed). 8 lines max in the worst case (4 TCs × 2 lines, single platform), but the active-weeks filter typically trims to 2-4 combos.
- Placement: stacked under the Endgame ELO timeline in the Endgame Metrics section.
- Popover copy (per memory `feedback_popover_copy_minimalism.md`): WHAT it shows + sign convention. Explicitly call the mirror "your opponents' Conv ΔES in their own converting positions." No methodology jargon. No "peer average" framing.
- Apply to both desktop and mobile (CLAUDE.md mobile-parity rule). Reuse the responsive patterns from `EndgameEloTimelineSection`.

## Design decisions captured

- **Raw ΔES, not cohort-adjusted.** Explicit user choice. The drifting line vs drifting mirror tells two stories at once (am I improving + how does my growth compare to my opponents'?) and reads better than a flat near-zero residual.
- **Opponent mirror, not /benchmarks CDF reference.** Self-calibrating, platform-correct (no Lichess sigmoid offset), TC-matched by construction.
- **≥33% active-weeks TC filter reused, not re-derived.** Consistency with the ELO timeline avoids cognitive load when users compare both charts.
- **The recovery-fold is acknowledged in the label, not engineered away.** Trying to subtract recovery skill would require a benchmark cohort lookup and lose the self-calibrating property. Honest labeling is the lighter solution.

## Open decisions (defer until phase planning)

- **Single platform per chart vs combined?** The Endgame ELO timeline already shows per-(platform × TC) combos as separate lines. With two lines per combo here (user + mirror), 4-8 lines could get visually crowded. Options: (a) merge platforms into a single line per TC if both pass the active-weeks filter; (b) keep per-(platform × TC) and rely on the filter to keep the count low in practice; (c) add a platform toggle. Decide at planning time after sketching.
- **Mirror line styling.** Dashed same-hue, lower-opacity solid, or muted gray. Affects readability with 4+ combos active.
- **Sample-size gate threshold.** PVALUE_RELIABILITY_MIN_N=10 is a strong gate but may leave too few weekly points in bullet for casual users; a smaller bucket-level minimum (e.g. 3) with the line drawn only across spans of qualifying weeks may be better.
- **Tooltip detail.** Show both raw rates (user conversion % and opponent conversion %) on hover, or only the ΔES values? Raw rates add density but help interpretation.

## Why this is a phase, not a /gsd-quick

The backend aggregator is non-trivial (two-side eval-baselined, weekly bucketed, with sample gating and active-weeks filtering) and the frontend chart needs the same care as the existing timeline charts (legend toggling, mobile parity, popover wiring, accessibility test IDs). Comparable in shape to Phase 87.5/87.6, smaller in scope because the methodology decisions are settled upfront.

## Cross-references

- Benchmark evidence: `reports/benchmarks-latest.md` §3.2.2 (axis-collapse verdicts table) and §3.2.3 (rate-vs-gap divergence). The d=1.62 ELO cohort effect on Conv ΔES is the empirical anchor.
- Visual prior art: `frontend/src/components/charts/EndgameEloTimelineSection.tsx` (the structural template, including `MIN_ACTIVE_WEEKS_RATIO = 0.33`).
- Data source: `app/models/game_position.py:105` (`eval_cp`); current ΔES machinery in `app/services/endgame_service.py` and `app/repositories/endgame_repository.py` from Phase 87.2.
- Reusable insight (separate note): `.planning/notes/opponent-mirror-as-self-calibrating-cohort.md` — generalizes the opponent-mirror reference idea beyond this one chart.
- Adjacent seed: SEED-019 (global percentile annotations) — different approach to the same broad need ("contextualize my number"). Complementary, not competing: SEED-019 annotates scalars with a global rank; SEED-020 contextualizes a *time series* with a personal-cohort reference.
- Popover discipline: project memory `feedback_popover_copy_minimalism.md`.

---
title: Time Pressure stats rework — Phase 88 design
date: 2026-05-14
context: v1.17 endgame rework — closing phase for the Endgames page (Time Pressure section)
status: captured via /gsd-explore; pending spec + plan-phase
---

# Time Pressure stats rework — Phase 88 design

Captured during `/gsd-explore` on 2026-05-14. Inserted as Phase 88 after Phase 87
(per-type cards); the previously-numbered Phase 88 Polish was bumped to Phase 89 so the
polish sweep still runs last and naturally extends to the new Time Pressure card surfaces.
Closes the v1.17 endgame rework arc by applying CI + hypothesis-testing rigor to the last
table-driven section on the Endgames page.

## Goal

Replace two surfaces with the established WDL + bullet doctrine from Phases 85–87:

1. **Time Pressure at Endgame Entry** — currently a table with `My avg time`, `Opp avg time`,
   `Avg clock diff` columns.
2. **Time Pressure vs Performance** — currently a line chart (5 pressure levels × score).

Both fold into a single per-TC card grid.

## Layout

One card per time control (bullet / blitz / rapid / classical) in a 4-col grid on `xl`,
2-col on `lg`, 1-col on `md` and below. Same responsive breakpoints as the per-type cards
in Phase 87.

Each card stacks 6 horizontal bullets:

1. **Clock Gap** (top of card) — metric = `mean(my_time − opp_time at endgame entry) / base_clock`.
   Centred on 0% (matched pace). Wilson-style CI as whiskers. Color zone from benchmark
   global distribution.
2. **Score-Delta per pressure quintile** (5 stacked bullets below the Clock Gap) — pressure bins
   are 20% slices of base-clock remaining at endgame entry (0–20% / 20–40% / 40–60% /
   60–80% / 80–100%). Metric per bin = `user_chess_score − cohort_chess_score`. Centred
   on 0 (= matches cohort). Wilson CI from user bin score. Color zone from per-bin cohort
   inter-user spread.

Total: 6 bullets per TC card, 24 visible on desktop `xl`. Same visual grammar as Phases
85–87 — no variety-for-variety bars or grouped charts. Users learn the bullet pattern
once and apply it everywhere on the page.

## Statistical foundation

### Clock Gap

- **Unit of analysis:** per-game pair. Each of the user's games in this TC contributes one
  `(my_time − opp_time) / base_clock` value at endgame entry.
- **Base clock:** initial time only, no increment. Benchmark data shows this normalization
  collapses cleanly across ELO and TC, so % is a meaningful unit. (1+0 vs 1+2 differ in
  absolute seconds but converge in % terms.)
- **Test:** one-sample test against 0% (paired-difference z-test or Wilcoxon depending
  on distribution shape — defer to plan-phase).
- **CI:** 95% on the mean difference.
- **Reference line:** 0% (matched pace).

### Score-Delta per pressure quintile

- **Metric per bin:** `user_score − cohort_score`, where `user_score = (W + 0.5·D) / n` for
  the user's games whose endgame-entry clock-remaining-% falls in this quintile, and
  `cohort_score` is the equivalent for the benchmark cohort in this (TC, pressure bin).
- **Why delta instead of paired bars:** Paired bars (me vs cohort side-by-side) force the
  reader to mentally subtract. Delta framing puts sign and magnitude in one read; the
  error bar directly encodes "is this difference real". Statistically equivalent —
  cohort N >> user N per bin, so cohort SE contributes negligibly to the delta SE.
- **CI:** Wilson CI on `user_score` (per project's existing chess-score utility),
  transplanted onto the delta. Cohort acts as fixed reference.
- **Sig test:** CI on delta crosses 0 → no signal. Otherwise sign of delta tells the story.
- **Reference line:** 0 (= matches cohort).

### Cohort definition

Mirror-bucket cohort per the v1.17 doctrine (rating-tier × TC × color × opponent-type filter
responsive). Must match Phases 85–87 to preserve the unified "you vs comparable peers"
frame across the page.

## Sparse-TC handling

Going from one chart to one-chart-per-TC multiplies the small-N problem by 4. Most users
won't have meaningful rapid/classical sample sizes once filters apply.

Proposed gating policy:

- **Hide the entire TC card** when total user games for this TC < `MIN_GAMES_PER_TC_CARD`
  (proposed 20).
- **Suppress individual Score-Delta bullets** within a rendered card when bin n <
  `MIN_GAMES_PER_PRESSURE_BIN` (proposed 5). Show a dash + sample count where the bullet
  would be.
- **Always show Clock Gap bullet** when the card renders (the card-level threshold already
  guarantees enough clock-gap data).

Thresholds are illustrative; confirm during plan-phase with a real-data check.

## /benchmarks skill update (in-scope, not a pre-req phase)

Two new metrics to add to `.claude/skills/benchmarks/SKILL.md`:

1. **clock-gap-%** — distribution of `(my_time − opp_time at endgame entry) / base_clock`
   per (TC, ELO bucket). User-level metric, then aggregated across users to produce
   inter-user distribution. Existing benchmark data hints this collapses across both ELO
   and TC → likely a single global zone band. Confirm via Cohen's d collapse verdict.
2. **chess-score-per-pressure-bin** — new shape. Distribution of user-level chess scores
   per (TC, ELO, pressure bin). The Cohen's d collapse verdict must run **per pressure
   bin separately**, because cohort score distribution shifts with pressure (likely
   tighter at low pressure, spreads at high pressure with small-N noise).
   - Prior: won't collapse across TC (bullet vs rapid behave very differently).
   - Prior: may or may not collapse across ELO — open question.

This introduces a new "metric-with-sub-bins" pattern the existing /benchmarks skill
doesn't have. The skill change is non-trivial. Scope it as part of Phase 88's plan-phase,
not as a separate pre-req phase.

## Why bullet stack and not grouped bars

Considered three statistically-equivalent visual options:

1. **Paired bars (me vs cohort).** Two bars per pressure bin, error bar on user bar only.
   Forces mental subtraction. Most literal.
2. **Single delta bars centred on 0.** Cleaner. Sign + magnitude in one read.
3. **Mini bullet chart per bin** (cohort score as dashed reference, user score as dot with
   CI band).

Chose **#3 bullet stack** for visual cohesion: the Clock Gap bullet at the top of each
TC card + 5 Score-Delta bullets below = "every card is a stack of bullets". Same grammar
as Phases 85–87. Bars-for-variety would be context-switching ink. The "boring uniform"
risk is real but it's the right call.

## Backend math

Likely reusable from Phase 85.1:

- `compute_paired_difference_test(diffs)` → Clock Gap (per-game paired diffs).

New helper needed:

- `compute_score_delta_vs_reference(user_w, user_d, user_l, user_n, cohort_score) →
  (delta, p_value, ci_low, ci_high)` — treats cohort_score as a fixed reference, returns
  delta + Wilson-derived CI + one-sample p-value against `H0: user_score = cohort_score`.
  Unit-tested at boundaries (n=0, all-wins, all-losses, user_score == cohort_score).

## Plan-phase decisions

To be resolved when phase is planned:

- Increment edge cases — confirm `base_clock = initial time only` holds for correspondence
  / unusual TC strings (e.g. `30+30`, `1+30` correspondence). Probably out of scope (we
  bucket to bullet/blitz/rapid/classical anyway), but worth a sanity check.
- Pressure bin policy when user has 0 games in a bin: render dash (sample count = 0) or
  omit the bullet row entirely?
- Color-zone band width: cohort IQR (per project convention), tightened band (per
  `feedback_zone_band_judgement.md` memory: tighten when small effects are meaningful),
  or editorial judgement per metric?
- Cohort match: mirror-bucket (same as Phases 85–87) or global cohort? Strong default:
  mirror-bucket, to keep the page-wide story consistent.
- Triple-gate font coloring: apply the same `n ≥ threshold ∧ p < 0.05 ∧ outside neutral
  band` policy as elsewhere in v1.17.
- Phase 89 Polish extends to the new card surfaces by precedent — confirm.

## Open question for plan-phase

Sample sizes for rapid/classical at user level: real-data check needed. If most users have
<20 rapid games after filters, the rapid card hides for most users — does that justify
the rework cost? Worth running a quick query against prod DB during plan-phase to size
the problem before committing to 6–8 plans.

## Out of scope

- LLM narration of time pressure: future phase.
- Per-move pressure analysis: current scope is endgame-entry snapshot only.
- Time management on the Openings page: out of scope; Endgames page only.

## References

- `.planning/notes/v1.17-single-bullet-doctrine.md` — page-wide doctrine this phase follows.
- `.planning/notes/endgame-stats-card-redesign.md` — original v1.17 design document.
- Phase 85.1 entry in `.planning/milestones/v1.17-ROADMAP.md` — the math helpers
  precedent (`compute_paired_difference_test`, `compute_score_difference_test`).
- `reports/benchmarks-latest.md` — confirms clock-gap-% collapsibility across ELO and TC.
- Memory: `feedback_zone_band_judgement.md` — tighten bands when small effects matter.
- Memory: `feedback_llm_significance_signal.md` — don't add parallel sig fields to LLM
  payload; tighten the cohort band instead. (Applies if Time Pressure ever gets LLM
  narration — out of scope this phase.)

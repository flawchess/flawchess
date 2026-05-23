---
id: SEED-025
status: planted
planted: 2026-05-22
last_refined: 2026-05-23
planted_during: /gsd-explore session ("could we create percentiles also for the TC cards in the Time Pressure section?") — explored mid Phase 93 planning, scoped as a follow-on phase rather than a Phase 93 expansion. Refined 2026-05-23 via second /gsd-explore session ("collapse the quintile score gaps into a per-TC metric") that simplified the artifact from 24 per-(TC, quintile) CDFs with tooltip placement to 12 per-TC CDFs with card-header chips.
promoted_to: not yet — trigger condition below
scope: phase (single, ~3-4 plans) — per-TC empirical CDFs for the Time Pressure section + card-header percentile chips on three per-TC metrics (Time Pressure Score Gap, Clock Gap, Net Flag Rate)
depends_on: v1.19 shipped (Phases 93/94/94.1/95) — the global-pooled CDF + chip + canonical-slice user-percentile pattern is the parent design; this seed extends it to per-TC surfaces using the same `user_benchmark_percentiles` storage contract from Phase 94.1
---

# SEED-025: Per-TC percentile chips on Time Pressure cards

## Why This Matters

SEED-019 / Phases 93–95 ship percentile chips on 4 ΔES metrics, all **global-pooled** (across TC and ELO). The Time Pressure section is structurally different: its cards are **per-TC by construction** (one card each for bullet / blitz / rapid / classical), and the user-meaningful comparison there is "top X% of *bullet* players", not "top X% of all players". That forces a separate per-TC CDF artifact whose architecture inverts the global-pooling decision baked into Phase 93 D-02/D-05.

Phase 94.1's `user_benchmark_percentiles` storage contract is metric-keyed, not TC-keyed. Each per-TC chip is therefore expressed as a distinct metric name (e.g. `time_pressure_score_gap_bullet`), reusing the table's `(user_id, metric) → (value, percentile, cdf_snapshot)` shape verbatim. No schema change.

Without this, the Time Pressure section keeps its zone bands but never lets a bullet player see "you're in the top 15% of bullet players on score gap under time pressure" — a comparison the rest of the dashboard (after v1.19) will have conditioned them to expect.

## When to Surface

**Trigger condition:** Phase 94.1 lands in production AND any one of the four Phase 94 chips is shown to be load-bearing in UX telemetry (popover dwell, narrative influence) or LLM payload influence. Two signals worth waiting for:

- Do users engage with the global chips (popover clicks, dwell time, narrative quotes)? If chips are largely ignored, the per-TC expansion is dead weight.
- Does feedback or support traffic surface confusion about "where do I stand in bullet specifically?" — i.e. is the global pooling actually masking what users want to know?

Relaxed from the original v1.20+ deferral: with the binary per-TC metric design (below), the per-TC artifact is now structurally identical to the four Phase 94 chips and slots into infrastructure already being built. A Phase 96 candidate for late v1.19 is plausible if engagement signals come in fast; otherwise v1.20+.

## Metric Definitions

Three metrics per TC, twelve total chips across the four TC cards.

### 1. Time Pressure Score Gap (new — replaces per-quintile decomposition)

For each TC, a single scalar per user:

```
time_pressure_score_gap_{tc} = score(user's pressured games) − score(opp's pressured games)
```

Where:
- **pressured** = `clock_pct < 40%` at endgame entry (i.e. quintiles Q0+Q1 pooled, matching the left half of the per-quintile bullet chart on each TC card).
- **user's pressured games** = the user's games in this TC where the *user* hit clock_pct < 40% at endgame entry. Scored as W=1 / D=0.5 / L=0.
- **opp's pressured games** = the user's games in this TC where the *opponent* hit clock_pct < 40% at endgame entry. Scored as the opponent's W=1 / D=0.5 / L=0 (= 1 − user's score in those games).

Same total game population, partitioned differently for the user-side and opp-side means. Opponent strength is implicitly controlled because both means are drawn from the same set of opponents the user actually faced.

**Why binary and not the per-quintile average:** an unweighted-or-weighted average of per-(TC, quintile) score gaps requires either per-quintile inclusion floors (mixed-construct CDF when some users contribute 2 quintiles and others 4) or n-weighting (chip baked partly on clock-management style rather than skill). The binary collapse dissolves both — single construct per user, no aggregation knobs. Per-quintile granularity is preserved in the unchanged bullet chart beneath the chip. Chip = headline trait, chart = breakdown.

**Inclusion floor:** ≥30 games in each of the two pressured cells (user-pressured AND opp-pressured) — final value tunable against cohort coverage in the discuss step, likely in the 30–50 range. Below floor → NULL percentile → no chip on that TC card. Mirrors the Phase 94 "metric below inclusion floor produces no chip" contract.

### 2. Clock Gap per TC

User's mean clock advantage (in seconds or % depending on UI rendering) at endgame entry within this TC, compared against the per-TC cohort distribution. Already a per-TC scalar in the existing card; the new artifact is just the cohort CDF + chip wiring.

### 3. Net Flag Rate per TC

User's net flag rate (flag wins minus flag losses, normalised by games) within this TC. Already a per-TC scalar; lower-is-better.

## Proposed Scope (12 per-TC CDFs)

| Bucket | # CDFs | Cohort per cell (est., 36-mo Lichess) | Tail resolution |
|---|---|---|---|
| Time Pressure Score Gap × 4 TCs | 4 | ~300–500 users / TC | p1..p99 (matches Phase 93/94 global) |
| Clock Gap × 4 TCs | 4 | ~400–600 users / TC | p1..p99 |
| Net Flag Rate × 4 TCs | 4 | ~400–600 users / TC | p1..p99 |
| **Total** | **12** | | |

**Resolution choice — p1..p99 matching the existing badges.** Per-TC cohort sizes are smaller than the global pool (~500 vs. ~thousands), so tail SE at the extremes (p1, p99) is wider than for the global ΔES chips — roughly 2–3pp at n=300 vs. <1pp on the global pool. Methodological parity with Phase 94's chip resolution is the deliberate trade-off: the chip surface, popover copy slot, and tooltip framing are identical to the Phase 94 chips, so a user looking at "top X%" reads the same number type everywhere. If discuss-step benchmarking reveals cohort sizes meaningfully below the estimates above, the resolution can be re-tightened then.

**Pooling axes** — per-TC required by product framing. ELO **pooled within TC** (mirrors the global-CDF framing of "top X% of [bullet] players", which is the comparison users actually want). Per-(TC, ELO) cells would split the cohort further to no clear product benefit.

## Phase 94.1 Integration

The per-TC chips are pure additions to the Phase 94.1 contract — no schema change, no new compute mechanism.

- **Storage**: 12 new metric values added to the `metric` enum of `user_benchmark_percentiles`. One row per `(user, metric)` as today; `metric` ∈ `{time_pressure_score_gap_bullet, ..._blitz, ..._rapid, ..._classical, clock_gap_bullet, ..., net_flag_rate_bullet, ...}`.
- **Compute stage**: all 12 are **Stage B (post-cold-drain)** — Time Pressure Score Gap and Clock Gap both depend on endgame-entry detection, which requires Stockfish eval. Net Flag Rate is outcome-only and could be Stage A, but bundling all 12 into Stage B avoids a special-case hook and the cost is negligible (Stage B already runs for the eval-dependent ΔES metrics).
- **Canonical-slice CTE**: extends `scripts/gen_global_percentile_cdf.py` with three new per-TC builder families. Each builder takes a TC parameter and emits the per-user metric value over the canonical slice (status='completed' + ±100 ELO opponent at game time + sparse-cell exclusion + 36-month recency), restricted to that TC. The canonical-slice machinery extracted in Phase 94.1 is the source of truth — these builders are clients, not duplicates.
- **Backfill**: extend `scripts/backfill_user_percentiles.py` (introduced in Phase 94.1) with the 12 new metrics. One-shot population on rollout, same `--target dev|prod` flow.
- **Frontend**: reuse `PercentileChip` component from Phase 94 verbatim. Chip slot on each `TimePressureTcCard` header (three chips per card, one per metric). Per-quintile bullet chart unchanged.

## Open Design Questions (defer to discuss step)

1. **Net Flag Rate chip direction.** Lower-is-better; "top 5%" = fewest net timeouts. Inverted direction from the score-gap chips on the same card. Risk: user reads "top 5%" and assumes "most flags" the way "top 5% on score gap" means "biggest gap". Resolution likely: bake the direction into the popover prose ("you flag less than 95% of bullet players") rather than relying on raw "top X%" framing.

2. **Clock Gap chip semantics.** Signed metric. Is "top 5%" the user with the most clock-advantage at endgame entry (i.e. furthest positive)? Or the user closest to zero (most balanced clock management)? Almost certainly the former for product purposes, but worth confirming against actual user-question phrasing.

3. **Inclusion floor for Time Pressure Score Gap.** ≥30 per pressured cell is a defensible starting point but should be tuned against actual cohort coverage. The pressured-cell coverage may itself be skewed by TC — classical players reach Q0+Q1 less often. Discuss step should query the benchmark cohort and pin the floor at the value that balances chip coverage against tail-SE width.

4. **Cutpoint validation.** <40% (Q0+Q1) is locked as the pressured/un-pressured boundary based on alignment with the existing bullet chart's left half. Worth a single benchmark-data check: does the cohort's score-gap-vs-cutpoint curve show a meaningful inflection at 40%, or is the signal smoother and the cutpoint largely cosmetic? If smoother, the chip is still defensible — "<40%" is what the chart visualises — but the discuss step should know.

## Tier Placement

SEED-019 established an implicit tier hierarchy:

- **Tier 1** — global ΔES percentiles (Phase 93/94/94.1/95, shipping in v1.19).
- **Tier 2** — *this seed* — per-TC time-pressure percentiles as card-header chips (12 chips across 4 cards).
- **Tier 3** — per-class CDFs (per-endgame-type Conv/Recov/Score/Score Gap) — deferred per REQUIREMENTS.md §Future Requirements; per-type samples currently too thin.
- **Tier 4** — opening insights percentile annotations — candidate for a future Opening Insights v2 milestone.

This seed claims tier 2 because the per-TC pool is samples-rich enough to support a real chip-header artifact, and the methodological collapse to a binary per-TC metric removes the per-(TC, quintile) sparsity problem that originally pushed it to tooltip-only placement.

## What This Seed Is Not

- Not a Phase 93 scope expansion. Phase 93 stays locked at 4 global-pooled CDFs.
- Not a per-(TC, quintile) artifact. The per-quintile bullet chart remains unannotated; the chip summarises pressured-vs-unpressured pooled across Q0+Q1.
- Not a per-(TC, ELO) artifact. ELO is pooled within TC; "top X% of bullet players" is the framing.
- Not a per-class extension. Per-type CDFs remain deferred per SEED-019 and REQUIREMENTS.md.
- Not a schema change. `user_benchmark_percentiles` from Phase 94.1 absorbs the 12 new metrics by enum extension, not by adding columns or a TC dimension.

## Cross-references

- Sibling to [[SEED-019]] — global percentile annotations on Endgame metrics. Parent design and rationale for the percentile-chip pattern.
- Builds on Phase 94.1 design — `.planning/notes/percentile-chip-canonical-slice.md` (canonical-slice user value, two-stage compute, `user_benchmark_percentiles` table contract).
- Methodology to inherit (when promoted): `.claude/skills/benchmarks/SKILL.md` Chapter 4 (added by Phase 93) — Standard CTE, sparse-cell exclusion, equal-footing filter, game-time ELO bucketing. The per-TC CDFs **do not** drop the TC dimension from the CTE; everything else carries verbatim.
- Source-of-truth for Time Pressure card schema: `app/schemas/endgames.py:709-757` (`TimePressureTcCard`, `PressureQuintileBullet`).
- Source-of-truth for the pressured/un-pressured cutpoint visualisation: `frontend/src/components/charts/ScoreGapByTimePressureChart.tsx` (Q0+Q1 = left half of the existing per-quintile bullet chart; Q4 hiding per Plan 88-13 A-4).
- Canonical-slice CTE machinery to extend: `scripts/gen_global_percentile_cdf.py` (per-metric `_per_user_cte_*` builders, `_canonical_selected_users_cte`, `_equal_footing_filter_sql`, `_sparse_exclusion_sql`, `_elo_bucket_expr`).
- Chip component to reuse: `frontend/src/components/score-gap/PercentileChip.tsx`.
- Storage contract to extend: `user_benchmark_percentiles` table (introduced in Phase 94.1) — add 12 metric enum values, no schema change.

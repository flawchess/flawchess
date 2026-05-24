---
id: SEED-025
status: promoted
planted: 2026-05-22
last_refined: 2026-05-24
planted_during: /gsd-explore session ("could we create percentiles also for the TC cards in the Time Pressure section?") — explored mid Phase 93 planning, scoped as a follow-on phase rather than a Phase 93 expansion. Refined 2026-05-23 via second /gsd-explore session ("collapse the quintile score gaps into a per-TC metric") that simplified the artifact from 24 per-(TC, quintile) CDFs with tooltip placement to 12 per-TC CDFs with card-header chips. Refined 2026-05-24 post-Phase-94.2 to align methodology references, code touchpoints, and tooltip-disclosure contract with the shipped pooled-per-user redesign.
promoted_to: Phase 94.3 (inserted 2026-05-24 after 94.2 shipped) — see ROADMAP.md §Phase 94.3 and .planning/phases/94.3-per-tc-percentile-chips-time-pressure/
scope: phase (single, ~3-4 plans) — per-TC empirical CDFs for the Time Pressure section + card-header percentile chips on three per-TC metrics (Time Pressure Score Gap, Clock Gap, Net Flag Rate)
depends_on: v1.19 shipped (Phases 93/94/94.1/94.2/95) — the global-pooled CDF + chip + canonical-slice user-percentile pattern is the parent design; this seed extends it to per-TC surfaces using the same `user_benchmark_percentiles` storage contract from Phase 94.1 as redesigned by Phase 94.2
---

# SEED-025: Per-TC percentile chips on Time Pressure cards

## Why This Matters

SEED-019 / Phases 93–95 ship percentile chips on 4 ΔES metrics, all **global-pooled** (across TC and ELO; one CDF per metric over a single one-point-per-user pool, per Phase 94.2's redesign). The Time Pressure section is structurally different: its cards are **per-TC by construction** (one card each for bullet / blitz / rapid / classical), and the user-meaningful comparison there is "top X% of *bullet* players", not "top X% of all players". That forces a separate per-TC CDF artifact whose architecture parameterises 94.2's pooled aggregate by TC instead of fully collapsing it.

Phase 94.2's `user_benchmark_percentiles` storage contract is metric-keyed, not TC-keyed. Each per-TC chip is therefore expressed as a distinct metric name (e.g. `time_pressure_score_gap_bullet`), reusing the table's `(user_id, metric) → (value, percentile, n_games, cdf_snapshot)` shape verbatim. No schema change.

Without this, the Time Pressure section keeps its zone bands but never lets a bullet player see "you're in the top 15% of bullet players on score gap under time pressure" — a comparison the rest of the dashboard (after v1.19) will have conditioned them to expect.

## When to Surface

**Trigger condition:** Phase 94.2 lands in production AND any one of the four Phase 94 chips is shown to be load-bearing in UX telemetry (popover dwell, narrative influence) or LLM payload influence. Two signals worth waiting for:

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

**Pool recipe (inherited from 94.2, restricted to one TC):** each per-TC value is computed over the user's most-recent 1000 games **in that TC**, last 36 months from the snapshot date. Same universal filters as the global chip (`rated=true`, non-computer opponent, ±100 equal-footing, standard variant). The 1000/TC cap + 36-month recency are the same knobs the 94.2 pooled aggregate uses; per-TC just drops the cross-TC pooling step.

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

**Pooling axes** — per-TC required by product framing. ELO **pooled within TC** (mirrors the global-CDF framing of "top X% of [bullet] players", which is the comparison users actually want, and aligns with 94.2's "rating accepted as honest" stance). Per-(TC, ELO) cells would split the cohort further to no clear product benefit and run counter to 94.2's cell-collapse decision.

## Phase 94.2 Integration

The per-TC chips are pure additions to the Phase 94.2 contract — no schema change, no new compute mechanism.

- **Storage**: 12 new metric values added to the `benchmark_metric` ENUM of `user_benchmark_percentiles`. One row per `(user, metric)` as today; `metric` ∈ `{time_pressure_score_gap_bullet, ..._blitz, ..._rapid, ..._classical, clock_gap_bullet, ..., net_flag_rate_bullet, ...}`. Each row populates the 94.2 columns including `n_games` (the per-TC pool size for that metric).
- **CDF storage shape extension**: `app/services/global_percentile_cdf.py:GLOBAL_PERCENTILE_CDF` today holds one CDF per metric enum. 12 new keys (one per `(metric_base, tc)` pair) are added — same literal shape, just more entries. `interpolate_percentile(metric_id, value)` dispatches on metric enum verbatim, no signature change.
- **Compute stage**: all 12 are **Stage B (post-cold-drain)** — Time Pressure Score Gap and Clock Gap both depend on endgame-entry detection, which requires Stockfish eval. Net Flag Rate is outcome-only and could be Stage A, but bundling all 12 into Stage B avoids a special-case hook and the cost is negligible (Stage B already runs for the eval-dependent ΔES metrics).
- **Canonical-slice SQL**: extends `app/services/canonical_slice_sql.py` with three new per-TC pooled-aggregate builder families. Each builder takes a TC parameter and emits the per-user metric value over the canonical slice (`rated=true`, ±100 equal-footing, standard variant, non-computer, 36-month recency, 1000/TC cap), restricted to that TC. The shared canonical-slice module from 94.2 is the source of truth — these builders are clients, not duplicates. Drift between CDF construction (`scripts/gen_global_percentile_cdf.py`) and per-user lookup (`app/services/user_benchmark_percentiles_service.py`) stays structurally impossible because both consume the same shared builders.
- **Backfill**: extend `scripts/backfill_user_percentiles.py` (introduced in Phase 94.1, kept by 94.2) with the 12 new metrics. One-shot population on rollout, same `--target dev|prod` flow.
- **Frontend**: reuse `PercentileChip` component from Phase 94 verbatim. Chip slot on each `TimePressureTcCard` header (three chips per card, one per metric). Per-quintile bullet chart unchanged. Tooltip copy follows the 94.2 4-bullet disclosure mandate (see Open Design Questions §5).

## Open Design Questions (defer to discuss step)

1. **Net Flag Rate chip direction.** Lower-is-better; "top 5%" = fewest net timeouts. Inverted direction from the score-gap chips on the same card. Risk: user reads "top 5%" and assumes "most flags" the way "top 5% on score gap" means "biggest gap". Resolution likely: bake the direction into the popover prose ("you flag less than 95% of bullet players") rather than relying on raw "top X%" framing.

2. **Clock Gap chip semantics.** Signed metric. Is "top 5%" the user with the most clock-advantage at endgame entry (i.e. furthest positive)? Or the user closest to zero (most balanced clock management)? Almost certainly the former for product purposes, but worth confirming against actual user-question phrasing.

3. **Inclusion floor for Time Pressure Score Gap.** ≥30 per pressured cell is a defensible starting point but should be tuned against actual cohort coverage. The pressured-cell coverage may itself be skewed by TC — classical players reach Q0+Q1 less often. Discuss step should query the benchmark cohort and pin the floor at the value that balances chip coverage against tail-SE width.

4. **Cutpoint validation.** <40% (Q0+Q1) is locked as the pressured/un-pressured boundary based on alignment with the existing bullet chart's left half. Worth a single benchmark-data check: does the cohort's score-gap-vs-cutpoint curve show a meaningful inflection at 40%, or is the signal smoother and the cutpoint largely cosmetic? If smoother, the chip is still defensible — "<40%" is what the chart visualises — but the discuss step should know.

5. **Tooltip disclosure under the 94.2 contract.** Per-TC chips inherit the 4-bullet disclosure mandate from `feedback_percentile_chip_tooltip_disclosure` (benchmark composition, recent-games basis, filter independence, per-metric rating-correlation framing). For the per-TC surface the first two bullets are TC-scoped — "Calibrated against benchmarked Lichess players in {bullet/blitz/rapid/classical}, all ratings" and "Uses your most recent 1000 games in {tc} (last 36 months)". The fourth bullet (rating-correlation framing) is the open work: the 94.2 `reports/benchmarks-gap-metrics-percentile-candidacy.md` covers the four ΔES metrics but not the time-pressure family. The discuss step should produce an analogous candidacy table — Cohen's d per (metric × TC) for Time Pressure Score Gap, Clock Gap, Net Flag Rate — so each of the 12 chips gets a calibrated tooltip line ("tracks rating strongly" vs. "rating-invariant" vs. silent). Rating correlation may itself differ by TC (e.g. Net Flag Rate at bullet probably tracks rating much harder than at classical), so per-(metric, TC) calibration is non-trivial.

## Tier Placement

SEED-019 established an implicit tier hierarchy:

- **Tier 1** — global pooled ΔES percentiles (Phase 93/94/94.1/94.2/95, shipping in v1.19). One CDF per metric, one one-point-per-user pool across all TCs.
- **Tier 2** — *this seed* — per-TC time-pressure percentiles as card-header chips (12 chips across 4 cards). One CDF per (metric, TC), one pool per user per TC played.
- **Tier 3** — per-class CDFs (per-endgame-type Conv/Recov/Score/Score Gap) — deferred per REQUIREMENTS.md §Future Requirements; per-type samples currently too thin.
- **Tier 4** — opening insights percentile annotations — candidate for a future Opening Insights v2 milestone.

This seed claims tier 2 because the per-TC pool is samples-rich enough to support a real chip-header artifact, and the methodological collapse to a binary per-TC metric removes the per-(TC, quintile) sparsity problem that originally pushed it to tooltip-only placement.

**Framing inconsistency with Tier 1 — deliberate.** Tier 1 chips compare a user against all benchmarked players regardless of TC; Tier 2 chips compare against players in the same TC bucket. A 1600 bullet player and a 1600 classical player are benchmarked against *different* cohorts on the time-pressure cards, but against the *same* cohort on the endgame ΔES chips. This is intentional: Time Pressure cards are visually per-TC by construction (the user is already inside the bullet card when they read the bullet chip), so TC-scoped framing matches the card context. Endgame ΔES chips sit on a global "your endgames" surface with no per-TC slicing in the UI, so global framing matches *that* context. The disclosure tooltip's first bullet makes the cohort scope explicit on both surfaces.

## What This Seed Is Not

- Not a Phase 93 scope expansion. Phase 93 stays locked at 4 global-pooled CDFs.
- Not a per-(TC, quintile) artifact. The per-quintile bullet chart remains unannotated; the chip summarises pressured-vs-unpressured pooled across Q0+Q1.
- Not a per-(TC, ELO) artifact. ELO is pooled within TC; "top X% of bullet players" is the framing.
- Not a per-class extension. Per-type CDFs remain deferred per SEED-019 and REQUIREMENTS.md.
- Not a schema change. `user_benchmark_percentiles` from Phase 94.2 absorbs the 12 new metrics by ENUM extension, not by adding columns or a TC dimension.
- Not a return to per-cell methodology. Phase 94.2's single-pooled-CDF-per-metric model carries forward; this seed extends it by parameterising the pool with a TC filter, not by re-introducing (TC, ELO) cells with `apply_floor` averaging.

## Cross-references

- Sibling to [[SEED-019]] — global percentile annotations on Endgame metrics. Parent design and rationale for the percentile-chip pattern.
- Builds on Phase 94.2 design — `.planning/notes/per-user-percentile-pooled-redesign.md` (pooled-per-user methodology, recent-1000-per-TC cap, 36-month recency, rejected ELO-conditioned alternative). The shipped methodology that this seed parameterises by TC.
- Phase 94.1 predecessor design — `.planning/notes/percentile-chip-canonical-slice.md` (storage table shape, two-stage compute, `cdf_snapshot` semantics). Still authoritative on the storage contract; per-cell stratification superseded by 94.2.
- Methodology source of truth (when promoted): `app/services/canonical_slice_sql.py` (shared SQL builders for CDF construction and per-user lookup, post-94.2). The per-TC CDFs add a TC-parameterised variant of the pooled aggregate; everything else (universal filters, recency, cap) carries verbatim.
- `.claude/skills/benchmarks/SKILL.md` describes its own per-cohort analytical methodology (per-cell stratified) — NOT the production chip's. Read for cohort construction context, not as a production-CDF spec (per 94.2 D-13-amend).
- Source-of-truth for Time Pressure card schema: `app/schemas/endgames.py:709-757` (`TimePressureTcCard`, `PressureQuintileBullet`).
- Source-of-truth for the pressured/un-pressured cutpoint visualisation: `frontend/src/components/charts/ScoreGapByTimePressureChart.tsx` (Q0+Q1 = left half of the existing per-quintile bullet chart; Q4 hiding per Plan 88-13 A-4).
- Per-metric rating-correlation calibration source for tooltip copy: `reports/benchmarks-gap-metrics-percentile-candidacy.md` (covers the 4 ΔES metrics; the discuss step must produce an analogous report for the 3 time-pressure metric families × 4 TCs).
- Chip component to reuse: `frontend/src/components/score-gap/PercentileChip.tsx`.
- Storage contract to extend: `user_benchmark_percentiles` table (Phase 94.1 shape, retained by 94.2 with `n_games` re-added via D-9-amend) — add 12 metric ENUM values, no schema change.
- Tooltip-disclosure mandate to satisfy: `feedback_percentile_chip_tooltip_disclosure` (4-bullet disclosure overrides `feedback_popover_copy_minimalism` on this surface).

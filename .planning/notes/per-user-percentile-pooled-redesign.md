---
title: Per-user percentile — pooled-per-user redesign (supersedes Phase 94.1 per-cell methodology)
date: 2026-05-23
context: Phase 94.1 ships per-user percentiles by averaging across (elo_bucket, tc_bucket) cells; rising-ELO users get pooled across their journey rather than rated against their current state. Redesign moves both CDF construction and per-user lookup to one-point-per-user computed on a recent-1000-per-TC pool.
---

## Motivation

The Phase 94.1 percentile reflects a user's *career averaged across ELO buckets they've ever played in*, not their *current state*. A player whose rating climbed 1200 → 2000 contributes equally to all three bucket cells; their chip is a smear of journey, not a reading of where they stand now.

Quote from the exploration:

> I wouldn't be interested if my whole journey is in the top x%. I would wanna know where I stand now.

The CDF itself compounds the problem. Looking at `scripts/gen_global_percentile_cdf.py:233-242`, the breakpoint query is:

```sql
SELECT percentile_cont(...) WITHIN GROUP (ORDER BY metric_value)
FROM per_user_values
```

with no `GROUP BY` — it's a single globally pooled CDF, but `per_user_values` is *per-cell* (one row per `(user_id, elo_bucket, tc_bucket)` floor-passing cell). The `n_users` label is a misnomer — it counts cell-rows. So a benchmark user who played across three ELO buckets contributes three CDF points; the "Top 10%" line is 10% of `(user × elo_bucket × tc_bucket)` cells, not 10% of users.

That construction was the right call when the per-user side was also cell-based (`canonical_slice_sql.py:248-252`), but the collapse step in `_compute_metric_for_user` (`user_benchmark_percentiles_service.py:117-128`) averages cells before lookup, which is what produces the journey-smearing chip value.

## Redesign

**Both sides use the same recipe:**

For each subject (cohort user during CDF generation, app user at lookup time):

1. Take their games per TC played, ordered by `played_at DESC`.
2. Cap at the most recent 1000 per TC.
3. Drop anything older than 36 months from the snapshot date.
4. Pool the resulting per-TC subsets into one combined set.
5. Apply universal filters (rated, non-computer, equal-footing ±100, standard variant).
6. Compute the metric once on the pool.

**CDF:** `percentile_cont` over those one-point-per-user values → 99 breakpoints. Globally pooled across all rating buckets and TCs — "the whole Lichess player base."

**Lookup:** app user's pooled metric value is interpolated against the same global CDF.

**Inclusion floor:** ≥30 games of the metric-relevant type on the pooled set:

- `score_gap` — ≥30 endgame games AND ≥30 non-endgame games.
- `achievable_score_gap` — ≥30 endgame-entry games with non-null `d_i`.
- `section2_score_gap_conv` / `_parity` — ≥30 spans in the relevant entry-eval bucket.

If the floor fails: no row stored, chip suppressed (same suppression contract as Plan 13).

## Semantics

Percentile now answers: *"Of all Lichess players we benchmarked, where do I currently sit on this metric, computed on my recent games only?"*

**Acknowledged tradeoff: rating-correlated metrics will systematically favour high-rated players.** Achievable score gap, conversion gap, and parity gap all correlate with playing strength. Under the new model, a 2400 player will tend to read higher percentiles than a 1200 player on these metrics. This is intentional — the chip honestly says "where you stand among all chess players," which is closer to the question users actually have. The alternative (ELO-conditioned CDF) was considered and rejected: a 1200 reading "Top 5% at your level" on conversion gap conveys less than a 1200 reading "Top 30% overall" because the latter is rooted in absolute skill.

## Known unaddressed risk: TC-mix heterogeneity

The pooled value for a user mixes their games across all TCs they play (bullet + blitz + rapid + classical), weighted by volume. A user who plays 95% bullet + 5% classical produces a pooled value dominated by their bullet behavior; a user with the opposite split produces a value dominated by their classical behavior. Both are then compared against the same global CDF — whose own TC-mix reflects the cohort's aggregate TC distribution, not either user's.

This is a real interpretation problem for users with extreme TC concentration:

- A heavy-bullet player's pooled value reflects time-pressure-heavy decisions; comparing them to a cohort that includes slow-classical games inflates or deflates depending on how the metric responds to time pressure.
- A user's rating in different TCs can differ by hundreds of ELO points (1800 rapid + 1200 bullet is common). Their pooled value averages over two different skill modes presented as one.
- The cohort CDF itself has the same mix problem, but the cohort's mix is the population's mix — not the individual's.

Not addressed in 94.2. Mitigations considered and deferred:

- **Per-TC CDFs** — one CDF per metric per TC bucket. Cleaner conceptually but multiplies the surface (4 metrics × 4 TCs = 16 CDFs), forces a TC selector into the chip UI, and shrinks each CDF's cohort by ~4×. Probably the right long-term answer if the heterogeneity bites in practice.
- **Disclose user's TC mix in the tooltip** — surface the pooled-set composition ("70% bullet / 25% blitz / 5% classical") so the user can mentally weight the chip. Cheaper, doesn't fix the math but flags it.
- **Restrict the pool to the user's primary TC** — pick the TC with the most games and drop the rest. Loses the "pooled across all play" framing the chip was designed around.

Flag for revisit if user feedback surfaces "my chip doesn't match my rating mode" complaints, or for a future phase when per-TC CDFs are in scope.

## Code impact

The redesign supersedes most of Phase 94.1's per-cell stratification machinery:

- `app/services/canonical_slice_sql.py` — the per-cell `per_user_values` CTE shape (`elo_bucket`, `tc_bucket` projections, sparse-cell exclusion, sub-800 floor) loses its purpose at the per-user lookup level. The CTE collapses to a single pooled aggregate. `apply_floor` dual-mode goes away (replaced by a single floor on the pooled set). The benchmark/single_user source split likely remains as a thin wrapper around the same pooling SQL.
- `scripts/gen_global_percentile_cdf.py` — `_build_metric_breakpoint_query` rewrites the CTE to "one row per user" instead of one row per cell. `_build_per_bucket_sanity_query` can stay for the diagnostic report but no longer reflects what the production CDF measures.
- `app/services/global_percentile_cdf.py` — the `GLOBAL_PERCENTILE_CDF` literal gets regenerated with new breakpoint values (semantics shift means the old numbers are no longer comparable).
- `app/services/user_benchmark_percentiles_service.py` — `_compute_metric_for_user` simplifies further: one query, one value, no `apply_floor` argument. Plan 13's correctness fix becomes moot because there are no cells to average.
- `tests/scripts/test_gen_global_percentile_cdf_unchanged.py` — the byte-identical regression goldens need a fresh capture (the test should still exist, just gated against a new fixture).
- `.claude/skills/benchmarks/SKILL.md` — methodology chapter rewrite (per-cell stratification → one-point-per-user pooled).

The `user_benchmark_percentiles` table schema and the Stage A / Stage B trigger pattern stay valid. The CDF snapshot column remains useful.

## Sequencing

Belongs as a successor to Phase 94.1 (provisionally Phase 94.2). 94.1's apply_floor=True correctness fix from Plan 13 is a valid intermediate state — it produces a defensible per-cell percentile while 94.2 is in flight. Don't rip out 94.1 before 94.2 lands.

## Open question

How many distinct points remain in the CDF after collapsing `benchmark_selected_users` to one row per `lichess_username` (a user selected across multiple TC or rating slots dedupes to one CDF point)? Worth measuring before plan-phase commits — if the pooled cohort is too small at the tails the `p1` / `p99` breakpoints get unstable. Captured as a research question for 94.2's planning phase.

## Related files

- `app/services/canonical_slice_sql.py:101-476` — CTE builders this redesign replaces.
- `app/services/user_benchmark_percentiles_service.py:93-128` — `_compute_metric_for_user` simplifies.
- `scripts/gen_global_percentile_cdf.py:233-242` — CDF construction query.
- `app/services/global_percentile_cdf.py` — `GLOBAL_PERCENTILE_CDF` literal.
- `.planning/phases/94.1-canonical-slice-user-percentile-materialisation/` — current methodology (per-cell, apply_floor=True default after Plan 13).
- `.claude/skills/benchmarks/SKILL.md` §1 — cohort selection methodology this redesign mirrors at lookup time.

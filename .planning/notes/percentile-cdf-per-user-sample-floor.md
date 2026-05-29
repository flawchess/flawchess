---
date: 2026-05-29
context: /gsd-explore session questioning whether the cohort percentile CDFs (endgame percentile chips) need a per-user sample-size floor to avoid unstable metrics from low-game users. Initial framing was "below 300-500 total games might be unstable."
outcome: No code change. A per-metric subset floor of >=30 already exists in canonical_slice_sql.py and the evidence says it is the sweet spot; raising it only costs coverage. Possible future revisit captured as a seed.
participants: Adrian, Claude
---

# Per-user sample-size floor for cohort percentile CDFs — 2026-05-29

## Trigger

Adrian: *"Benchmark users have between 100 and 1000 games. For the CDF calculation, I think below 300 or 500 games might lead to unstable metrics. Note that metrics are only based on a subset of games."*

The worry: a per-user metric value computed from too few games is noisy, and noisy per-user values pollute the cohort empirical CDF (`reports/percentile/cohort-percentile-cdf-latest.md`), distorting where a player's chip lands.

## Two reframings that changed the question

1. **Wrong unit.** Metrics are computed over *conditioned subsets*, not whole game sets:
   - `score_gap` / `achievable_score_gap` → games that reached an endgame
   - `score_gap_conv` / `score_gap_parity` / `recovery_score_gap` → games entering the endgame ahead / even / behind in material (a three-way split of the endgame subset)
   - `clock_gap` / `net_flag_rate` / `time_pressure_score_gap` → endgame-entry games
   A "300-500 total games" floor is a blunt proxy: it admits users with few subset positions and excludes users with many clean endgames. The right lever is the per-metric subset count (`n_games`, already carried in `_build_per_user_with_anchor_query` rows).

2. **The floor already exists.** `app/services/canonical_slice_sql.py` gates per-user inclusion via `HAVING count(...) >= 30` on the relevant subset for every metric:
   `SCORE_GAP_MIN_ENDGAME_N`, `SCORE_GAP_MIN_NON_ENDGAME_N`, `ACHIEVABLE_MIN_GAMES`, `SCORE_GAP_BUCKET_MIN_SPANS` (conv/parity/recovery), `TIME_PRESSURE_MIN_PRESSURED_N`, `CLOCK_GAP_MIN_POOL_N`, `NET_FLAG_RATE_MIN_POOL_N`, `MEDIAN_ANCHOR_MIN_GAMES` — all = 30. So the feature requested already ships, at the correct granularity. The only live question is whether to *raise* it.

## Evidence (benchmark DB, snapshot 2026-05-27; queried via the gen-script's own query path)

- **Subset thinness confirms reframing #1.** Rate metrics sit at median ~120-180 samples; classical is far thinner (score_gap median 444 bullet vs 98 classical). Total-game count would have been the wrong unit.
- **Tails are NOT noise-dominated (decisive).** In the bottom-10% and top-10% metric-value regions (where a chip lands), `%` of users with `n<30` is **0% everywhere** (the floor guarantees it), and tail median sample size does not collapse (conv top-10% median n=80 vs middle 191 — thinner, not noise). Small-sample users do not pile up in the extremes, so raising the floor would not meaningfully correct chip placement.
- **Raising the floor is pure coverage cost** (newly-suppressed cells of ~927 qualifying):

  | floor | newly suppressed | where |
  |--:|--:|---|
  | 30 (current) | 0 | — |
  | 50 | 72 (8%) | 65 of 72 are rapid + classical |
  | 100 | 212 (23%) | classical loses 97 |

## Decision

Keep the per-metric `>=30` floor. It is at the right granularity (subset, not total games) and the evidence puts it at the sweet spot: the tails it would clean are already clean, while raising to 50 sacrifices rapid/classical coverage and 100 guts classical. No code change indicated.

## Door left open

If the benchmark DB later gains substantial rapid/classical depth, the coverage cost of a higher floor drops and a rate-metric-only floor of ~50 becomes cheap to revisit. Captured as a seed (trigger: benchmark DB rapid/classical depth grows materially).

Related: [[benchmark-rebuild-per-tc-selection]], [[benchmark-skill-v2-design]].

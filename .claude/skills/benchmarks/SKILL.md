---
name: benchmarks
description: Generate FlawChess endgame population benchmarks from the benchmark DB. Computes per-user distributions for score-gap (endgame vs non-endgame), Conversion/Parity/Recovery rates, composite Endgame Skill, Endgame ELO vs Actual ELO gap, time-pressure stats at endgame entry, time-pressure-vs-performance curves, and per-endgame-class (rook/minor_piece/pawn/queen/mixed/pawnless) score and conv/recov rates. All metrics are bucketed via 400-wide ELO buckets (anchored at 800/1200/1600/2000/2400 from `benchmark_selected_users.rating_bucket`) and the 4 TC buckets (anchored from `benchmark_selected_users.tc_bucket`). For every metric, the skill produces a Cohen's-d-based collapse verdict per axis ({TC, ELO}) that determines whether the metric needs cell-specific zones or collapses to a single global zone. Use this skill whenever the user asks about endgame benchmarks, neutral zones, gauge ranges, "what's typical", baseline distributions, calibrating thresholds, comparing time controls, deciding whether to collapse zones across TC or ELO, or breaking down stats by endgame class. Trigger on phrases like "benchmark", "benchmarks", "baseline", "neutral zone", "gauge range", "collapse verdict", "Cohen's d", "calibrate thresholds", "endgame type breakdown", "by endgame class", "rook vs minor piece". Writes a timestamped markdown report to reports/benchmarks-YYYY-MM-DD.md.
---

# Benchmarks

Generate population-level endgame benchmarks for FlawChess from the benchmark DB. The headline deliverable is a **per-metric collapse verdict** answering: does this metric need cell-specific zones across (TC × ELO), or can it use a single global zone?

## Target

- **Benchmark DB only** (`mcp__flawchess-benchmark-db__query`). Population baselines are computed against the stratified Lichess sample, never against FlawChess prod/dev data.
- Benchmark DB runs in Docker on `localhost:5433`. If `docker compose -p flawchess-benchmark ps` shows nothing, run `bin/benchmark_db.sh start` first.
- Each MCP call runs one statement (no `;`-separated multi-statement).

## Cell anchoring (canonical)

All cells anchor on `benchmark_selected_users`, never on per-game ratings.

### Schema

```
benchmark_selected_users
  id                  integer (PK)
  lichess_username    varchar  -- joins to users.lichess_username
  rating_bucket       smallint -- 800 / 1200 / 1600 / 2000 / 2400 (400-wide, anchored)
  tc_bucket           varchar  -- 'bullet' / 'blitz' / 'rapid' / 'classical'
  median_elo          smallint -- precise rating at selection time
  eval_game_count     smallint -- snapshot eval-bearing game count (sample quality)
  selected_at         timestamptz
  dump_month          varchar  -- provenance (currently '2026-03' for all rows)
```

### Cell rules

- **20 cells**: 5 ELO buckets × 4 TC buckets. ELO anchors are `800 (800–1199), 1200 (1200–1599), 1600 (1600–1999), 2000 (2000–2399), 2400 (2400+)`.
- **Per-user TC anchoring**: one user can occupy multiple cells, one per TC where they qualified at selection time (compound `(lichess_username, tc_bucket)` key). Each row contributes only its TC's games via `g.time_control_bucket = bsu.tc_bucket`. A user in `(2000, bullet)` and `(2000, classical)` is two distinct cell members, scored on each TC's games independently.
- **Per-user history caveat**: each user contributes up to 1000 games per TC (`max=1000` cap on the lichess API at ingest time), bounded by a 36-month window before the selection snapshot. `rating_bucket` is the per-TC median rating at snapshot, not at game-time. Interpret "ELO bucket effect" as "current rating cohort effect" rather than "rating-at-game-time effect". Surface this caveat in the report header.
- **Selection vs ingest**: per-cell selection target is `--per-cell` (typically 100–500). Multi-TC qualifiers add a small amount of incidental cross-cell membership (~0–10 users per ELO bucket overlap two cells). All cells should clear the ≥10 users/cell floor after ingest; verify with the sample-size query below.
- **Checkpoint-status filter (mandatory)**: the canonical CTE MUST join `benchmark_ingest_checkpoints` and filter `bic.status = 'completed'`. `benchmark_selected_users` is the *candidate pool*, not the ingested set — it includes rows that were never attempted (`null` checkpoint), 404'd / errored on import (`failed`), or fell below the `--min-games` ingest floor (`skipped`, with their games purged but stub `users` row preserved if a sibling TC filled). Without this filter, multi-TC qualifiers leak into queries with zero games for the unselected TC, dragging medians to zero. See "Sparse-cell exclusion" below.
- **Selection provenance**: 2026-03 Lichess monthly dump (single `dump_month` for the current DB). When new dumps land, group by `dump_month` so cross-snapshot drift is observable.

### Standard CTE — `selected_users`

Every query starts with:

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket,
         bsu.median_elo, bsu.eval_game_count
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
)
```

Then JOIN `selected_users su` on `g.user_id = su.user_id` and filter `g.time_control_bucket::text = su.tc_bucket`. Cells are formed from `(su.rating_bucket, su.tc_bucket)`. **Cast note**: `games.time_control_bucket` is a custom enum (`timecontrolbucket`) and `benchmark_selected_users.tc_bucket` is `varchar` — without the `::text` cast Postgres errors with `operator does not exist: timecontrolbucket = character varying`.

**Why the checkpoint join is non-optional**: `benchmark_selected_users` is the candidate *pool*. The ingest orchestrator (`scripts/import_benchmark_users.py`) walks the pool, marking each `(lichess_username, tc_bucket)` row as `completed`, `skipped` (low yield, games purged), `failed` (404/error), or leaving it `null` (never attempted because earlier candidates filled the slot). Only `completed` rows have games in this TC. Skipping the filter pulls in 'skipped' multi-TC qualifiers (whose games for this TC were deleted) and never-attempted pool members, both of which appear as 0-game users in cell aggregates.

### Sample size check

Verify cell coverage (count of `status='completed'` users) before running a full report:

```sql
SELECT bsu.rating_bucket, bsu.tc_bucket, COUNT(DISTINCT u.id) AS users_completed
FROM benchmark_selected_users bsu
JOIN benchmark_ingest_checkpoints bic
  ON bic.lichess_username = bsu.lichess_username
 AND bic.tc_bucket = bsu.tc_bucket
 AND bic.status = 'completed'
JOIN users u ON u.lichess_username = bsu.lichess_username
GROUP BY 1, 2
ORDER BY 2, 1;
```

Optionally also report the full status breakdown to spot pool exhaustion:

```sql
SELECT bsu.rating_bucket, bsu.tc_bucket,
       COALESCE(bic.status, 'unattempted') AS status,
       COUNT(*) AS n
FROM benchmark_selected_users bsu
LEFT JOIN benchmark_ingest_checkpoints bic
  ON bic.lichess_username = bsu.lichess_username
 AND bic.tc_bucket = bsu.tc_bucket
GROUP BY 1, 2, 3
ORDER BY 2, 1, 3;
```

A cell is **pool-exhausted** when `unattempted = 0` and `completed < target`. Topping up via re-running the orchestrator does nothing — the only fix is widening selection criteria in `select_benchmark_users.py` and re-running selection.

### Sparse-cell exclusion

**Known sparse cell**: `(rating_bucket=2400, tc_bucket='classical')` is structurally undersampled and pool-exhausted as of the 2026-03 dump (12 completed users out of a 23-user pool, ~55 games/user vs ~900 in 2400-bullet). This is a property of the Lichess 2400-classical population (low player count × low games-per-player), not a fixable ingestion gap.

**Rule**: this cell **MUST be excluded from cross-axis aggregations** (TC marginals, ELO marginals, pooled overall, and Cohen's d on either axis) but **kept in cell-level 5×4 tables** for transparency. Add a footnote to the cell value and to every report header.

**Implementation pattern**: when computing marginals or pooled values, gate the aggregation:

```sql
-- Marginal / pooled aggregation: exclude the sparse cell
... WHERE NOT (elo_bucket = 2400 AND tc = 'classical') ...

-- Cell-level 5×4 grid: keep the cell, render with a footnote (e.g. "n=12*")
```

The Cohen's d marginal pools must apply the same exclusion — both the per-level `(n, mean, var)` aggregates and any pairwise comparisons it feeds. A 2400-row of an ELO-axis Cohen's d that includes (2400, classical) at n=12 would be statistically dominated by the other three TCs anyway, but mixing the sparse cell in distorts the variance estimate at the marginal level.

**Future extensions of this skill (new sections, new metrics) MUST honor this exclusion**: any new query that computes a TC marginal, ELO marginal, pooled overall, or Cohen's d input must apply the `NOT (elo_bucket = 2400 AND tc = 'classical')` filter at the marginal aggregation stage. Cell-level outputs should still include the cell with a footnote. If a future Lichess dump produces a denser 2400-classical cell (e.g. ≥40 completed users with ≥200 games/user), revisit this rule and document the change in the report header.

## Collapse verdict methodology (Cohen's d)

Per metric, answer: does this metric collapse across TC? across ELO? both? neither?

### Computation

For each per-user metric:

1. Compute one value per user, labeled by their `(rating_bucket, tc_bucket)` cell. Floor: ≥10 users/cell for inclusion.
2. **TC marginal**: 4 levels (bullet/blitz/rapid/classical) — pool users across ELO within each TC. **Exclude `(2400, classical)` users from the classical pool** (see "Sparse-cell exclusion").
3. **ELO marginal**: 5 levels (800/1200/1600/2000/2400) — pool users across TC within each ELO. **Exclude `(2400, classical)` users from the 2400 pool** for the same reason.
4. Compute pairwise Cohen's d on user-level distributions:
   - TC axis: 4 levels → 6 pairs → take **`max |d|`** (`tc_d_max`).
   - ELO axis: 5 levels → 10 pairs → take **`max |d|`** (`elo_d_max`).
5. Cohen's d formula: `d = (mean_a - mean_b) / pooled_sd`, where `pooled_sd = sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))`.

### Verdict thresholds (hard-coded)

| `max |d|` | Verdict | Meaning |
|---|---|---|
| < 0.2 | **collapse** | Negligible. Single global zone is fine. |
| 0.2 ≤ d < 0.5 | **review** | Small but noticeable. Default to single zone unless a UI argument warrants splitting. |
| ≥ 0.5 | **keep separate** | Meaningful. Stratify zones along this axis. |

Each axis is evaluated independently; a metric can land at "collapse on TC, keep ELO" or vice versa.

### Why marginals not all-cell pairwise

Pairwise on all 20 cells over-rejects collapse on outlier cells. Marginal-pair max d directly answers "does this dimension matter?".

### Why Cohen's d not gauge-range relative

Gauge ranges in `theme.ts` were chosen with varying degrees of arbitrariness. Cohen's d is standardized in within-group SD units and gauge-range-independent.

### Computing Cohen's d in SQL

For a per-user value column `x` over a marginal axis (e.g. TC), produce per-level `(n, mean, var)` then compute pairwise d in post-processing. SQL fragment:

```sql
SELECT axis_level, count(*) AS n, avg(x) AS mean_x, var_samp(x) AS var_x
FROM per_user_values
GROUP BY axis_level
HAVING count(*) >= 10;
```

Then for each pair `(a, b)`: `pooled_sd = sqrt(((n_a-1)*var_a + (n_b-1)*var_b) / (n_a+n_b-2))`; `d = (mean_a - mean_b) / pooled_sd`. Take `max(|d|)` across pairs as the axis verdict input.

### Per-metric output block (every section)

```
### Collapse verdict
- TC axis: max |d| = X.XX (between {pair}) → {collapse | review | keep}
- ELO axis: max |d| = Y.YY (between {pair}) → {collapse | review | keep}
- Heatmap of per-user p50 (5 ELO × 4 TC):

           bullet   blitz   rapid   classical
  800       0.51    0.48    0.49    0.49
  1200      0.51    0.50    0.50    0.47
  ...
```

The heatmap is a 5×4 grid of per-user p50 — visual sanity check for interaction effects that marginals would miss.

## Score-gap re-centering — out of scope

Score-gap gauge currently uses symmetric `±0.10`. **Do not propose re-centering for sub-5pp population median offsets** — round bounds beat data-fitted asymmetry below that threshold. (2026-04-30 design decision.)

## Live-threshold grep table

Before running each section, grep the code for the constants the section's gauge depends on. Record literal values in a "Currently set in code" subsection so recommendations compare data-driven proposals against the live values.

| Section | Metric | File | Constants |
|---|---|---|---|
| 1 | Score gap (eg vs non-eg) + timeline | `frontend/src/components/charts/EndgamePerformanceSection.tsx` | `SCORE_GAP_NEUTRAL_MIN/MAX`, `SCORE_GAP_DOMAIN`, `SCORE_TIMELINE_Y_DOMAIN`, any `SCORE_TIMELINE_NEUTRAL_*` constants |
| 2 | Conv / Par / Recov + Endgame Skill | `frontend/src/components/charts/EndgameScoreGapSection.tsx`, `frontend/src/generated/endgameZones.ts` | `FIXED_GAUGE_ZONES`, `NEUTRAL_ZONE_MIN/MAX`, `BULLET_DOMAIN`, `ENDGAME_SKILL_ZONES` |
| 3 | Endgame ELO formula | `app/services/endgame_service.py` | `ENDGAME_ELO_TIMELINE_WINDOW`, `_ENDGAME_ELO_SKILL_CLAMP_LO/HI`, `MIN_GAMES_FOR_TIMELINE`, `_MATERIAL_ADVANTAGE_THRESHOLD` |
| 4 | Clock-diff + net timeout | `frontend/src/components/charts/EndgameClockPressureSection.tsx` | `NEUTRAL_PCT_THRESHOLD`, `NEUTRAL_TIMEOUT_THRESHOLD` |
| 5 | Time-pressure chart | `app/services/endgame_service.py::_compute_time_pressure_chart`, `EndgameTimePressureSection.tsx` | `Y_AXIS_DOMAIN`, `X_AXIS_DOMAIN`, `MIN_GAMES_FOR_CLOCK_STATS` |
| 6 | Per-class score-diff + conv/recov | `frontend/src/components/charts/EndgameWDLChart.tsx`, `EndgameConvRecovChart.tsx` | `NEUTRAL_ZONE_MIN/MAX`, `BULLET_DOMAIN`; conv/recov chart has no per-class zones today |

Use the Grep tool, not bash. Record literal values.

## Shared SQL building blocks

### `endgame_game_ids`
Games meeting the 6-ply endgame rule (`ENDGAME_PLY_THRESHOLD = 6`):
```sql
SELECT game_id FROM game_positions
WHERE endgame_class IS NOT NULL
GROUP BY game_id HAVING count(*) >= 6
```

### `first_endgame`
First endgame ply per qualifying game:
```sql
SELECT game_id, min(ply) AS entry_ply
FROM game_positions
WHERE endgame_class IS NOT NULL
GROUP BY game_id HAVING count(*) >= 6
```

### `user_score_expr`
User's score in a game:
```sql
CASE
  WHEN (g.result = '1-0' AND g.user_color = 'white')
    OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
  WHEN g.result = '1/2-1/2' THEN 0.5
  ELSE 0.0
END
```

### Base filter
Every query: `g.rated AND NOT g.is_computer_game`. Do not apply `opponent_strength` or `recency` filters — population stats are unconstrained by per-user UI filters.

### Sample floors

| Section | Per-user / per-cell minimum |
|---|---|
| 1 score-gap | ≥30 endgame AND ≥30 non-endgame games per user (in their selected TC) |
| 2 Conv/Par/Recov pooled | cell shown if pooled n ≥ 100 |
| 2 Endgame Skill per-user | ≥20 endgame games per user, ≥2 of 3 material buckets non-empty; cell shown if ≥10 users |
| 3 Endgame ELO gap | ≥30 endgame games per user in their cell |
| 4 clock stats | ≥20 endgame games per user in their cell |
| 5 pressure-vs-performance | per-(TC × time-bucket) cell shown if n ≥ 100 |
| 6 endgame-type | per-(cell × class): n ≥ 100 for score, ≥30 for conversion / recovery |
| Cohen's d | ≥10 users per marginal level |

---

## Section 1 — Score gap (endgame vs non-endgame)

**Question:** How does per-user `eg_score − non_eg_score` distribute across the population, and does the distribution shift across (TC × ELO) cells?

**Per-user metrics:**
- `eg_score` = avg score in endgame games (within selected TC)
- `non_eg_score` = avg score in non-endgame games (within selected TC)
- `diff` = eg_score − non_eg_score

### Query
```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
endgame_game_ids AS (
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
rows AS (
  SELECT
    g.user_id,
    su.rating_bucket AS elo_bucket,
    su.tc_bucket AS tc,
    CASE
      WHEN (g.result = '1-0' AND g.user_color = 'white')
        OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
      WHEN g.result = '1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    (eg.game_id IS NOT NULL) AS has_endgame
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  LEFT JOIN endgame_game_ids eg ON eg.game_id = g.id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
),
per_user AS (
  SELECT
    user_id, elo_bucket, tc,
    count(*) FILTER (WHERE has_endgame) AS eg_games,
    count(*) FILTER (WHERE NOT has_endgame) AS non_eg_games,
    avg(score) FILTER (WHERE has_endgame) AS eg_score,
    avg(score) FILTER (WHERE NOT has_endgame) AS non_eg_score
  FROM rows
  GROUP BY user_id, elo_bucket, tc
  HAVING count(*) FILTER (WHERE has_endgame) >= 30
     AND count(*) FILTER (WHERE NOT has_endgame) >= 30
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  round(avg(eg_score - non_eg_score)::numeric, 4) AS diff_mean,
  round(stddev_samp(eg_score - non_eg_score)::numeric, 4) AS diff_std,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS diff_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS diff_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS diff_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS diff_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY eg_score - non_eg_score)::numeric, 4) AS diff_p95,
  round(avg(eg_score)::numeric, 4) AS eg_mean,
  round(avg(non_eg_score)::numeric, 4) AS non_eg_mean
FROM per_user
GROUP BY elo_bucket, tc
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

### Output

1. **5×4 cell table** of per-user `diff` distribution (`diff_p25 / diff_p50 / diff_p75 (n)`).
2. **TC marginal** (4 rows pooled across ELO): `n_users / mean / SD / p25 / p50 / p75`.
3. **ELO marginal** (5 rows pooled across TC): same columns.
4. **Pooled overall**: 1 row (used for the score-gap gauge recommendation).
5. Recommendations:
   - **Score-gap gauge neutral zone** = pooled `[diff_p25, diff_p75]`. Compare to `SCORE_GAP_NEUTRAL_MIN/MAX`. Use **keep symmetric ±0.10** unless |median| ≥ 5pp (out-of-scope guard).
   - **Score-gap gauge half-width** = pooled `max(|diff_p05|, |diff_p95|)`. Compare to `SCORE_GAP_DOMAIN`.
   - **Timeline neutral zone** = intersection of pooled `[eg_p25, eg_p75]` and `[non_eg_p25, non_eg_p75]`. If overlap ≥ 50% of narrower interval, propose `[max(p25s), min(p75s)]` as a single unified band.
   - **Timeline Y-axis** = `[min(eg_p05, non_eg_p05), max(eg_p95, non_eg_p95)]` padded.
6. **Collapse verdict block** (per `diff` distribution): `tc_d_max`, `elo_d_max`, 5×4 heatmap of `diff_p50`.

---

## Section 2 — Conversion / Parity / Recovery + Endgame Skill

**Question:** How do per-user Conversion/Parity/Recovery rates and composite Endgame Skill distribute across cells? Does each metric collapse across TC and/or ELO?

### Material-bucket rule (mirrors `_compute_score_gap_material`)
- `entry_imb_user = entry.material_imbalance * sign` (`sign = +1` white, `-1` black)
- `after_imb_user = after.material_imbalance * sign` where `after` is at `entry_ply + 4` AND `after.endgame_class IS NOT NULL` (else NULL)
- Bucket: `conversion` if both ≥ +100, `recovery` if both ≤ −100, else `parity` (including NULL after)

### Per-bucket rate definitions (mirror `_endgame_skill_from_bucket_rows`)
- conversion → `1.0` if user won else `0.0` (Win %)
- parity → user score `1.0 / 0.5 / 0.0` (Score %)
- recovery → `1.0` if user won or drew else `0.0` (Save %)

### Endgame Skill
Unweighted mean of the non-empty per-bucket rates. A user with all three buckets has `skill = (conv + par + recov) / 3`; one with only parity has `skill = parity_rate`. Need ≥2 of 3 buckets non-empty + ≥20 endgame games per user per cell.

### Query
```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
bucketed AS (
  SELECT
    g.user_id,
    su.rating_bucket AS elo_bucket,
    su.tc_bucket AS tc,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb,
    ap.material_imbalance AS after_imb
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe ON fe.game_id = g.id
  JOIN game_positions ep
    ON ep.game_id = g.id AND ep.ply = fe.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id AND ap.ply = fe.entry_ply + 4
   AND ap.endgame_class IS NOT NULL
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
),
classified AS (
  SELECT
    user_id, elo_bucket, tc, score,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN 'parity'
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100 THEN 'conversion'
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100 THEN 'recovery'
      ELSE 'parity'
    END AS bucket,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN score
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100
        THEN CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100
        THEN CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END
      ELSE score
    END AS bucket_contribution
  FROM bucketed
),
per_user_bucket AS (
  SELECT user_id, elo_bucket, tc, bucket,
         count(*) AS games,
         avg(bucket_contribution) AS bucket_rate
  FROM classified
  GROUP BY user_id, elo_bucket, tc, bucket
),
per_user_cell AS (
  -- pivot per-user buckets to wide form, plus skill
  SELECT
    user_id, elo_bucket, tc,
    sum(games) AS total_games,
    count(*) AS buckets_used,
    max(bucket_rate) FILTER (WHERE bucket = 'conversion') AS conv_rate,
    max(bucket_rate) FILTER (WHERE bucket = 'parity')     AS par_rate,
    max(bucket_rate) FILTER (WHERE bucket = 'recovery')   AS recov_rate,
    avg(bucket_rate) AS skill
  FROM per_user_bucket
  GROUP BY user_id, elo_bucket, tc
  HAVING sum(games) >= 20 AND count(*) >= 2
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  -- Endgame Skill
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS skill_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS skill_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY skill)::numeric, 4) AS skill_p75,
  -- Conversion (per-user, only users with conversion games)
  count(*) FILTER (WHERE conv_rate IS NOT NULL) AS n_conv,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY conv_rate)::numeric, 4) AS conv_p50,
  round(avg(conv_rate)::numeric, 4) AS conv_mean,
  round(var_samp(conv_rate)::numeric, 6) AS conv_var,
  -- Parity
  count(*) FILTER (WHERE par_rate IS NOT NULL) AS n_par,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY par_rate)::numeric, 4) AS par_p50,
  round(avg(par_rate)::numeric, 4) AS par_mean,
  round(var_samp(par_rate)::numeric, 6) AS par_var,
  -- Recovery
  count(*) FILTER (WHERE recov_rate IS NOT NULL) AS n_recov,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY recov_rate)::numeric, 4) AS recov_p50,
  round(avg(recov_rate)::numeric, 4) AS recov_mean,
  round(var_samp(recov_rate)::numeric, 6) AS recov_var,
  -- Skill mean/var for Cohen's d
  round(avg(skill)::numeric, 4) AS skill_mean,
  round(var_samp(skill)::numeric, 6) AS skill_var
FROM per_user_cell
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

The `mean` / `var_samp` columns feed Cohen's d. Pooled rates come from re-aggregating the same `per_user_cell` CTE without the `elo_bucket, tc` GROUP BY.

### Output (one block per metric: Conversion, Parity, Recovery, Endgame Skill)

1. **5×4 cell table** of per-user p50 (`p50 (n_users)`).
2. **TC marginal** + **ELO marginal** percentile tables.
3. **Pooled overall** — feeds the gauge neutral-zone recommendation.
4. **Recommendations** per metric:
   - `Conversion` neutral band = pooled `[conv_p25, conv_p75]` rounded. Compare to `FIXED_GAUGE_ZONES.conversion` (`[0.65, 0.75]`).
   - `Parity` neutral band = same. Compare to `[0.45, 0.55]`.
   - `Recovery` neutral band = same. Compare to `[0.25, 0.35]`.
   - `Endgame Skill` neutral band = pooled `[skill_p25, skill_p75]`. Compare to `ENDGAME_SKILL_ZONES`.
   - For each, if the cell-level p50 spread across cells exceeds `2 × (band width)`, the pooled band cannot center every cell — flag in the verdict.
5. **Collapse verdict block** per metric.

---

## Section 3 — Endgame ELO vs Actual ELO Gap

**Question:** How does the gap `Endgame ELO − Actual ELO` distribute per cell? Sanity-checks the 400-Elo scaling and the [0.05, 0.95] skill clamp.

Phase 57.1 formula: `endgame_elo = round(actual_elo_at_date + 400 · log10(clamped_skill / (1 − clamped_skill)))`. The gap is `400 · log10(clamped_skill / (1 − clamped_skill))` — a deterministic transform of clamped skill (anchor cancels).

The benchmark DB is lichess-only, so platform drops out — Section 3 is per-(TC × ELO), not per-(platform × TC). Use the user's **latest-in-window** user_rating in their selected TC as a snapshot proxy for `actual_elo_at_date`; mirrors the asof-join at the latest emitted week.

### Query
```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
endgame_games AS (
  SELECT
    g.id AS game_id,
    g.user_id,
    su.rating_bucket AS elo_bucket,
    su.tc_bucket AS tc,
    g.played_at,
    CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END AS user_rating,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb,
    ap.material_imbalance AS after_imb,
    row_number() OVER (
      PARTITION BY g.user_id
      ORDER BY g.played_at DESC, g.id DESC
    ) AS rn_desc
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe ON fe.game_id = g.id
  JOIN game_positions ep ON ep.game_id = g.id AND ep.ply = fe.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id AND ap.ply = fe.entry_ply + 4
   AND ap.endgame_class IS NOT NULL
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) IS NOT NULL
),
window_games AS (
  -- Trailing 100 endgame games per user (matches ENDGAME_ELO_TIMELINE_WINDOW = 100)
  SELECT * FROM endgame_games WHERE rn_desc <= 100
),
classified AS (
  SELECT
    user_id, elo_bucket, tc, score, user_rating, played_at, game_id,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN score
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100
        THEN CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100
        THEN CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END
      ELSE score
    END AS bucket_contribution,
    CASE
      WHEN entry_imb IS NULL OR after_imb IS NULL THEN 'parity'
      WHEN (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100 THEN 'conversion'
      WHEN (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100 THEN 'recovery'
      ELSE 'parity'
    END AS bucket
  FROM window_games
),
per_user_bucket AS (
  SELECT user_id, elo_bucket, tc, bucket,
         count(*) AS games,
         avg(bucket_contribution) AS bucket_rate
  FROM classified
  GROUP BY user_id, elo_bucket, tc, bucket
),
per_user_skill AS (
  SELECT user_id, elo_bucket, tc,
         sum(games) AS total_games,
         count(*) AS buckets_used,
         avg(bucket_rate) AS skill
  FROM per_user_bucket
  GROUP BY user_id, elo_bucket, tc
  HAVING sum(games) >= 30 AND count(*) >= 2
),
per_user_snapshot AS (
  SELECT user_id, elo_bucket, tc,
         (ARRAY_AGG(user_rating ORDER BY played_at DESC, game_id DESC))[1]::numeric AS actual_elo
  FROM window_games
  GROUP BY user_id, elo_bucket, tc
),
per_user_gap AS (
  SELECT
    s.user_id, s.elo_bucket, s.tc, s.skill, s.total_games,
    p.actual_elo,
    least(0.95, greatest(0.05, s.skill)) AS clamped_skill,
    round(400 * log(10, least(0.95, greatest(0.05, s.skill)) / (1 - least(0.95, greatest(0.05, s.skill))))) AS gap
  FROM per_user_skill s
  JOIN per_user_snapshot p USING (user_id, elo_bucket, tc)
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  round(avg(gap)::numeric, 1) AS gap_mean,
  round(var_samp(gap)::numeric, 1) AS gap_var,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY gap)::numeric) AS gap_p95,
  sum(CASE WHEN skill <= 0.05 THEN 1 ELSE 0 END) AS n_clamp_low,
  sum(CASE WHEN skill >= 0.95 THEN 1 ELSE 0 END) AS n_clamp_high
FROM per_user_gap
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

### Output

1. **5×4 cell table** `gap_p25 / gap_p50 / gap_p75 (n)`.
2. **TC + ELO marginals** (mean, SD, p05/p25/p50/p75/p95).
3. **Pooled clamp saturation**: `n_clamp_low / n_clamp_high / total`. If > 1% saturate, the clamp is doing heavy lifting — flag.
4. **Recommendations**:
   - **Window size**: keep `ENDGAME_ELO_TIMELINE_WINDOW = 100` if std_gap pooled lands in 60–200 (well-behaved).
   - **Skill clamp `[0.05, 0.95]`**: keep if saturation < 1%.
   - **400-Elo scaling**: keep if pooled std_gap is in 60–200 range.
   - **"Notable divergence" callout threshold (forward-looking)**: pooled `|gap_p90|` if a future UI feature adds a callout.
5. **Collapse verdict block** on `gap`.

---

## Section 4 — Time pressure at endgame entry

**Question:** How do per-user clock-diff (% of base time) and net-timeout-rate distribute per cell?

**Primary metric: % of base time.** Live gauge compares `user_avg_pct − opp_avg_pct`, both = `clock_seconds / base_time_seconds * 100`.

### SQL approximation

The backend scans ply arrays for the first non-NULL clock per parity. SQL approximates by taking clocks at `entry_ply` and `entry_ply + 1` and routing by parity + user_color. This misses NULL-clock plies; small systematic bias vs backend logic.

### Query
```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
clock_raw AS (
  SELECT
    g.id AS game_id, g.user_id, g.user_color,
    su.rating_bucket AS elo_bucket,
    su.tc_bucket AS tc,
    g.base_time_seconds, g.termination, g.result,
    fe.entry_ply,
    p1.clock_seconds AS clk_at_entry,
    p2.clock_seconds AS clk_at_entry_plus_1
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe ON fe.game_id = g.id
  LEFT JOIN game_positions p1 ON p1.game_id = g.id AND p1.ply = fe.entry_ply
  LEFT JOIN game_positions p2 ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
),
routed AS (
  SELECT
    user_id, elo_bucket, tc, base_time_seconds, termination, result, user_color,
    CASE
      WHEN user_color='white' AND entry_ply % 2 = 0 THEN clk_at_entry
      WHEN user_color='white' AND entry_ply % 2 = 1 THEN clk_at_entry_plus_1
      WHEN user_color='black' AND entry_ply % 2 = 1 THEN clk_at_entry
      ELSE clk_at_entry_plus_1
    END AS user_clk,
    CASE
      WHEN user_color='white' AND entry_ply % 2 = 0 THEN clk_at_entry_plus_1
      WHEN user_color='white' AND entry_ply % 2 = 1 THEN clk_at_entry
      WHEN user_color='black' AND entry_ply % 2 = 1 THEN clk_at_entry_plus_1
      ELSE clk_at_entry
    END AS opp_clk
  FROM clock_raw
),
clean AS (
  SELECT user_id, elo_bucket, tc, termination, result, user_color,
         user_clk, opp_clk, base_time_seconds,
         (user_clk - opp_clk) / NULLIF(base_time_seconds, 0) * 100 AS diff_pct
  FROM routed
  WHERE user_clk IS NOT NULL AND opp_clk IS NOT NULL
    AND base_time_seconds > 0
    AND user_clk <= 2.0 * base_time_seconds
    AND opp_clk <= 2.0 * base_time_seconds
),
per_user_cell AS (
  SELECT
    user_id, elo_bucket, tc,
    count(*) AS games,
    avg(diff_pct) AS avg_diff_pct,
    sum(CASE WHEN termination='timeout' AND (
              (result='1-0' AND user_color='white') OR
              (result='0-1' AND user_color='black')) THEN 1 ELSE 0 END) AS timeout_wins,
    sum(CASE WHEN termination='timeout' AND (
              (result='1-0' AND user_color='black') OR
              (result='0-1' AND user_color='white')) THEN 1 ELSE 0 END) AS timeout_losses
  FROM clean
  GROUP BY user_id, elo_bucket, tc
  HAVING count(*) >= 20
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  -- Clock diff %
  round(avg(avg_diff_pct)::numeric, 2) AS pct_mean,
  round(var_samp(avg_diff_pct)::numeric, 2) AS pct_var,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY avg_diff_pct)::numeric, 2) AS pct_p95,
  -- Net timeout
  round(avg((timeout_wins - timeout_losses)::numeric / games * 100), 2) AS net_mean,
  round(var_samp((timeout_wins - timeout_losses)::numeric / games * 100), 2) AS net_var,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY (timeout_wins - timeout_losses)::numeric / games * 100)::numeric, 2) AS net_p75
FROM per_user_cell
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

### Output

Two metric blocks (% diff, net timeout). Each:
1. **5×4 cell table** of per-user p50.
2. **TC + ELO marginals** with full percentiles.
3. **Recommendations**:
   - `NEUTRAL_PCT_THRESHOLD` = pooled `[pct_p25, pct_p75]` rounded. Compare to live ±10pp.
   - `NEUTRAL_TIMEOUT_THRESHOLD` = pooled `[net_p25, net_p75]`. Compare to live ±5pp.
   - If TC verdict = `keep`, recommend per-TC thresholds (one value per TC).
4. **Collapse verdict block** per metric.

---

## Section 5 — Time pressure vs performance

**Question:** Does the time-pressure-vs-performance curve collapse across (TC × ELO), or does it need stratified display?

The metric is per-time-bucket (10 buckets, 0–100% time-remaining), not a single per-user value, so the verdict is computed slightly differently.

### Query
```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
clock_raw AS (
  SELECT
    g.id AS game_id, g.user_color,
    su.rating_bucket AS elo_bucket,
    su.tc_bucket AS tc,
    g.base_time_seconds, g.result,
    fe.entry_ply,
    p1.clock_seconds AS clk_at_entry,
    p2.clock_seconds AS clk_at_entry_plus_1
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe ON fe.game_id = g.id
  LEFT JOIN game_positions p1 ON p1.game_id = g.id AND p1.ply = fe.entry_ply
  LEFT JOIN game_positions p2 ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.base_time_seconds > 0
),
game_pct AS (
  SELECT
    elo_bucket, tc,
    CASE
      WHEN (result='1-0' AND user_color='white')
        OR (result='0-1' AND user_color='black') THEN 1.0
      WHEN result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS user_score,
    (CASE
       WHEN user_color='white' AND entry_ply % 2 = 0 THEN clk_at_entry
       WHEN user_color='white' AND entry_ply % 2 = 1 THEN clk_at_entry_plus_1
       WHEN user_color='black' AND entry_ply % 2 = 1 THEN clk_at_entry
       ELSE clk_at_entry_plus_1
     END) / NULLIF(base_time_seconds, 0) * 100 AS user_pct
  FROM clock_raw
)
SELECT
  elo_bucket, tc,
  least(floor(user_pct / 10)::int, 9) AS time_bucket,
  count(*) AS games,
  round(avg(user_score)::numeric, 4) AS score
FROM game_pct
WHERE user_pct IS NOT NULL AND user_pct <= 200
GROUP BY elo_bucket, tc, time_bucket
ORDER BY elo_bucket, tc, time_bucket;
```

### Output

1. **Per-bucket curves**: 10-row × 4-column table per ELO bucket (rows = time-bucket 0–9, cols = TCs). Cell = `score (n)`. Suppress n < 100.
2. **TC marginals** (pool ELO): 10-row × 4-col table — the answer to "is TC pooling justified".
3. **ELO marginals** (pool TC): 10-row × 5-col table.
4. **Verdict (per axis)**: per time-bucket, compute marginal-pair Cohen's d on **per-game-score binary outcome** (0/0.5/1) using `n / mean / var_samp`. Take **`max |d|` across buckets where ≥3 marginal levels have n ≥ 100** as the axis verdict input.
5. Recommendation: if either axis verdict ≠ `collapse`, recommend stratified display (per-TC overlay or full per-(TC × ELO) display).
6. **Collapse verdict block**: TC and ELO axes evaluated independently using the per-bucket-pooled approach.

---

## Section 6 — Endgame type breakdown

**Question:** How do per-game score, conversion, and recovery vary across the 6 endgame classes (rook / minor_piece / pawn / queen / mixed / pawnless), and across (TC × ELO)?

**Multi-class semantics**: per `query_endgame_entry_rows`, each `(game, endgame_class)` span ≥6 plies contributes one row. A single game traversing queen→rook contributes once to each. This is the same convention as the live Endgame Categories tab.

**Persistence approximation**: SQL uses `entry_ply + 4` with same-class join, approximating the backend's stricter `array_agg` + contiguity check. Small systematic difference, document in report.

### Query
```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
class_span AS (
  SELECT game_id, endgame_class, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id, endgame_class
  HAVING count(*) >= 6
),
bucketed AS (
  SELECT
    g.id AS game_id,
    g.user_id,
    su.rating_bucket AS elo_bucket,
    su.tc_bucket AS tc,
    cs.endgame_class AS endgame_class_int,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    CASE WHEN g.user_color='white' THEN 1 ELSE -1 END AS color_sign,
    ep.material_imbalance AS entry_imb,
    ap.material_imbalance AS after_imb
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN class_span cs ON cs.game_id = g.id
  JOIN game_positions ep
    ON ep.game_id = g.id AND ep.ply = cs.entry_ply
  LEFT JOIN game_positions ap
    ON ap.game_id = g.id
   AND ap.ply = cs.entry_ply + 4
   AND ap.endgame_class = cs.endgame_class
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
)
SELECT
  elo_bucket, tc,
  CASE endgame_class_int
    WHEN 1 THEN 'rook'
    WHEN 2 THEN 'minor_piece'
    WHEN 3 THEN 'pawn'
    WHEN 4 THEN 'queen'
    WHEN 5 THEN 'mixed'
    WHEN 6 THEN 'pawnless'
  END AS endgame_class,
  count(*) AS games,
  count(DISTINCT user_id) AS users,
  round(avg(score)::numeric, 4) AS score,
  round((avg(score) * 2 - 1)::numeric, 4) AS score_diff,
  count(*) FILTER (WHERE (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100) AS conv_games,
  round((avg(CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END)
         FILTER (WHERE (entry_imb * color_sign) >=  100 AND (after_imb * color_sign) >=  100))::numeric, 4) AS conversion,
  count(*) FILTER (WHERE (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100) AS recov_games,
  round((avg(CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END)
         FILTER (WHERE (entry_imb * color_sign) <= -100 AND (after_imb * color_sign) <= -100))::numeric, 4) AS recovery
FROM bucketed
GROUP BY elo_bucket, tc, endgame_class_int
ORDER BY elo_bucket,
         CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END,
         endgame_class_int;
```

### Output

For each of the three metrics (score / conversion / recovery):

1. **One sub-table per endgame class** (6 sub-tables): rows = ELO bucket (5), columns = TC (4). Cell = `metric (n)`. Suppress per sample-floor (n_games < 100 for score; n_conv < 30 for conv; n_recov < 30 for recov).
2. **Pooled-by-class summary** (collapses ELO and TC): one row per class with pooled `score / score_diff / conversion / recovery` and sample sizes. This is the row most likely to drive UI decisions.
3. **Recommendations**:
   - **Per-class score-diff neutral zone** (`NEUTRAL_ZONE_MIN/MAX` in `EndgameWDLChart.tsx`, currently `±0.05`): keep if pooled per-class score_diff fits within ±0.05.
   - **Per-class conv/recov neutral zones** (currently none in `EndgameConvRecovChart.tsx`): if pooled per-class spread > 5pp, propose initial bands per class as `pooled_rate ± 5pp`. Otherwise recommend keeping pooled-only display.
4. **Collapse verdict per (metric × class)**: 6 classes × 3 metrics = 18 verdicts. For each metric × class, run Cohen's d across {TC, ELO} marginals on the per-cell pooled rate (n ≥ 30 cell-floor). This is rate-level rather than per-user because per-user-per-class would be too sparse at the current sample size.

If 18 verdicts is too noisy, aggregate to one verdict per metric (across-class max d) plus per-class footnote when an outlier class fails the metric-level verdict.

---

## Report file layout

Write to `reports/benchmarks-YYYY-MM-DD.md` (UTC date). Layout:

```markdown
# FlawChess Benchmarks — <DATE>

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: <ISO timestamp>
- **Population**: <N_users> users / <N_games> games / <N_positions> positions
- **Cell anchoring**: 400-wide ELO buckets via benchmark_selected_users.rating_bucket; tc_bucket from same table; per-user TC restricted to selected tc_bucket
- **Selection provenance**: 2026-03 Lichess monthly dump, 9133 selected users, <N_ingested> ingested at ~50/cell
- **Per-user history caveat**: rating_bucket is per-TC median rating at selection snapshot; each user contributes up to 1000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: g.rated AND NOT g.is_computer_game; per-user filter g.time_control_bucket = bsu.tc_bucket; benchmark_ingest_checkpoints.status = 'completed' (mandatory canonical-CTE filter)
- **Sparse-cell exclusion**: `(2400, classical)` is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user, pool exhausted). It is still shown in cell-level 5×4 tables with an `n=12*` footnote. Revisit if a future dump produces ≥40 completed users at ≥200 games/user.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate
- **Sample floors**: <floors used per section>
- **Cell coverage** (status='completed' users per cell): <inline 5×4 table, sparse cell flagged>

## 1. Score gap (endgame vs non-endgame)
... (cell table, marginals, recommendations, **collapse verdict block**)

## 2. Conversion / Parity / Recovery + Endgame Skill
... (one block per metric, each with cell table, marginals, recommendations, **collapse verdict block**)

## 3. Endgame ELO vs Actual ELO Gap
...

## 4. Time pressure at endgame entry
... (% diff and net timeout, each with verdict)

## 5. Time pressure vs performance
... (per-bucket verdict — see methodology caveat)

## 6. Endgame type breakdown
... (one block per endgame class × metric)

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|
| Score gap (eg − non_eg) | ... | ... | ... |
| Conversion (per-user) | ... | ... | ... |
| Parity (per-user) | ... | ... | ... |
| Recovery (per-user) | ... | ... | ... |
| Endgame Skill (per-user) | ... | ... | ... |
| Endgame ELO gap (per-user) | ... | ... | ... |
| Clock pressure %-of-base | ... | ... | ... |
| Net timeout rate | ... | ... | ... |
| Time-pressure curve (per-bucket) | ... | ... | ... |
| Per-class score | ... | ... | ... |
| Per-class conversion | ... | ... | ... |
| Per-class recovery | ... | ... | ... |

Every cell states `max |d|` and a verdict. Drives Phase 73 zone calibration in SEED-006.

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|

One row per gauge constant. Recommended value comes from the pooled or per-cell distribution depending on the collapse verdict. Action is one of `keep` / `widen to X` / `narrow to Y` / `stratify per TC` / `stratify per ELO` / `stratify fully`.
```

## Re-running

If `reports/benchmarks-YYYY-MM-DD.md` exists for today and the user asks for a section subset, replace only those sections; preserve header and the two final summary tables. Always rebuild the summary tables from whatever sections are present.

If the user asks for a fresh snapshot, write to today's file; never mutate prior dates.

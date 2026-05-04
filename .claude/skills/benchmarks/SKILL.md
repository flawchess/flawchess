---
name: benchmarks
description: Generate FlawChess endgame population benchmarks from the benchmark DB. Computes per-user distributions for score-gap (endgame vs non-endgame), Conversion/Parity/Recovery rates, composite Endgame Skill, time-pressure stats at endgame entry, time-pressure-vs-performance curves, and per-endgame-class (rook/minor_piece/pawn/queen/mixed/pawnless) score and conv/recov rates. All metrics are bucketed via 400-wide ELO buckets (anchored at 800/1200/1600/2000/2400 from `benchmark_selected_users.rating_bucket`) and the 4 TC buckets (anchored from `benchmark_selected_users.tc_bucket`). For every metric, the skill produces a Cohen's-d-based collapse verdict per axis ({TC, ELO}) that determines whether the metric needs cell-specific zones or collapses to a single global zone. Use this skill whenever the user asks about endgame benchmarks, neutral zones, gauge ranges, "what's typical", baseline distributions, calibrating thresholds, comparing time controls, deciding whether to collapse zones across TC or ELO, or breaking down stats by endgame class. Trigger on phrases like "benchmark", "benchmarks", "baseline", "neutral zone", "gauge range", "collapse verdict", "Cohen's d", "calibrate thresholds", "endgame type breakdown", "by endgame class", "rook vs minor piece". Writes a timestamped markdown report to reports/benchmarks-YYYY-MM-DD.md.
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

### Eval coverage check

Sections 2/3/6 depend on Stockfish eval being present at the first endgame ply. Coverage should be ~100% on the benchmark DB. If it dips below 99% the report header should flag it (NULL eval routes to parity, biasing the parity bucket).

```sql
WITH first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
)
SELECT
  count(*) AS endgame_games,
  count(*) FILTER (WHERE ep.eval_cp IS NOT NULL OR ep.eval_mate IS NOT NULL) AS with_eval,
  round(100.0 * count(*) FILTER (WHERE ep.eval_cp IS NOT NULL OR ep.eval_mate IS NOT NULL) / count(*), 2) AS pct_with_eval
FROM first_endgame fe
JOIN game_positions ep ON ep.game_id = fe.game_id AND ep.ply = fe.entry_ply;
```

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

## Equal-footing opponent filter (all sections)

**Apply `abs(opp_rating - user_rating) <= 100` to every per-game CTE across all sections (§1, §2, §4, §5, §6).** No exceptions — the filter is part of the canonical "Base filter" alongside `g.rated AND NOT g.is_computer_game`.

### Why

Without the filter, the 2400 cohort plays opponents averaging 50–130 Elo weaker (and 2400-classical is even more skewed). That matchmaking confound inflates the apparent ELO skill ramp on every per-game metric and makes cohort differences look larger than they actually are. The 2026-05-03 report measured per-cell `avg_opp_minus_user` ranging from +47 (800-classical) down to -372 (2400-classical) — see that report's opponent-gap analysis section.

The filter was originally scoped to §2/§6 only, on the argument that §1 (within-user diff), §4, and §5 (clock behavior) were less skill-stratified. Decision revisited 2026-05-03: methodological consistency wins. §5's per-time-bucket score curve is genuinely confounded by matchmaking; §1's timeline Y-axis uses absolute eg/non_eg percentiles that are also inflated; §4's net-timeout-rate is partly "I beat weaker players on time." Single rule, single rationale, simpler header.

### Framing — design decision

Benchmark zones are calibrated as the **"skill at equal footing"** baseline. The user's measured value in the live UI still uses unfiltered games (their real performance, including any matchmaking advantage), but the zones it's compared against are confound-free. Higher-rated players will naturally see their measurement sit above the equal-footing baseline — *that* is the intended signal. Users who want to view skill-only stats apply the in-app opponent-strength filter, which collapses their measurement to the equal-footing comparator. Full rationale in `.planning/notes/benchmark-equal-footing-framing.md`.

### Sample-loss escape hatch

The filter retains ~85–90% of mid-ELO games but drops 2400-rapid to ~51% and 2400-classical to ~15% (already excluded as sparse cell). If a non-sparse cell drops below per-user sample floors after filtering:

1. **First-line fix**: re-run selection with a higher per-cell user target via `select_benchmark_users.py --per-cell N`, then re-ingest. The benchmark DB is meant to be re-populated, not preserved.
2. **Second-line fix**: widen the per-user game window in `import_benchmark_users.py` (currently capped at 1000 games / 36-month window per TC).
3. **Last resort**: footnote the cell with reduced n and exclude from marginals. Do NOT relax the equal-footing tolerance below ±100 Elo just to keep games — the whole point is the equal-footing baseline.

Track post-filter sample sizes per section in the equal-footing retention subsection. Flag any cell that drops below floor.

### SQL fragment

In every per-game CTE (across all sections), the filter goes alongside the existing `g.rated AND NOT g.is_computer_game` clause:

```sql
WHERE g.rated AND NOT g.is_computer_game
  AND g.time_control_bucket::text = su.tc_bucket
  AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
  AND abs(
        (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
      - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
      ) <= 100
```

Both rating columns must be NOT NULL — the abs() expression silently returns NULL if either side is missing, and a NULL-comparing predicate evaluates to NULL (drops the row), but explicitly stating the NOT NULL keeps the intent legible and prevents accidental interaction with future SQL refactors.

### Reporting

Add an "Equal-footing retention" subsection under each section's cell coverage (every section, not just §2/§6), showing the per-cell game retention vs the unfiltered baseline. The 2026-05-03 retention pattern was: mid-ELO cells retain ~85–90%, 2400-rapid drops to ~51%, 2400-classical to ~15% (already excluded as sparse cell). Flag any cell that drops below the per-user sample floor and apply the escape-hatch fix above.

When comparing against pre-2026-05-03 snapshots, note in the report header that §1/§4/§5 changed from unfiltered to equal-footing — the absolute numbers are not directly comparable across the boundary.

## Score-gap re-centering — out of scope

Score-gap gauge currently uses symmetric `±0.10`. **Do not propose re-centering for sub-5pp population median offsets** — round bounds beat data-fitted asymmetry below that threshold. (2026-04-30 design decision.)

## Live-threshold grep table

Before running each section, grep the code for the constants the section's gauge depends on. Record literal values in a "Currently set in code" subsection so recommendations compare data-driven proposals against the live values.

| Section | Metric | File | Constants |
|---|---|---|---|
| 1 | Score gap (eg vs non-eg) + timeline | `frontend/src/components/charts/EndgamePerformanceSection.tsx` | `SCORE_GAP_NEUTRAL_MIN/MAX`, `SCORE_GAP_DOMAIN`, `SCORE_TIMELINE_Y_DOMAIN`, any `SCORE_TIMELINE_NEUTRAL_*` constants |
| 2 | Conv / Par / Recov + Endgame Skill | `frontend/src/components/charts/EndgameScoreGapSection.tsx`, `frontend/src/generated/endgameZones.ts` | `FIXED_GAUGE_ZONES`, `NEUTRAL_ZONE_MIN/MAX`, `BULLET_DOMAIN`, `ENDGAME_SKILL_ZONES` |
| 3 | Phase-entry eval (mid + eg) | TBD — bullet chart not yet implemented (target `frontend/src/components/charts/PhaseEntryEvalSection.tsx` or similar). For the **symmetric engine-asymmetry baseline** (consumed by the in-app z-test), grep `app/services/opening_insights_constants.py` for `EVAL_BASELINE_CP_WHITE`, `EVAL_BASELINE_CP_BLACK`, and `EVAL_CONFIDENCE_MIN_N`. `EVAL_BASELINE_CP_BLACK` must equal `-EVAL_BASELINE_CP_WHITE` (symmetric by construction — flag if violated). | Bullet-chart bounds: TBD. Baseline: live values are `EVAL_BASELINE_CP_WHITE = 28`, `EVAL_BASELINE_CP_BLACK = -20` (re-grep at run time), `EVAL_CONFIDENCE_MIN_N = 20`. |
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
Every query: `g.rated AND NOT g.is_computer_game` PLUS the **equal-footing opponent filter** (`abs(opp_rating - user_rating) <= 100`, both ratings NOT NULL). The equal-footing filter is universal across §1, §2, §4, §5, §6 — see "Equal-footing opponent filter (all sections)" for SQL fragment and rationale. Do not apply `recency` filters — population stats are unconstrained by per-user UI filters.

### Sample floors

| Section | Per-user / per-cell minimum |
|---|---|
| 1 score-gap | ≥30 endgame AND ≥30 non-endgame games per user (in their selected TC) |
| 2 Conv/Par/Recov pooled | cell shown if pooled n ≥ 100 |
| 2 Endgame Skill per-user | ≥20 endgame games per user, ≥2 of 3 material buckets non-empty; cell shown if ≥10 users |
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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all sections)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
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

### Eval-bucket rule (REFAC-02 — mirrors `_classify_endgame_bucket`)

Per-game classification uses the Stockfish eval at the **first endgame ply** of the game. The old `material_imbalance + 4-ply persistence` proxy is gone — REFAC-02 replaced it with a single-point engine eval. With ~100% engine-eval coverage at endgame entry on the benchmark DB, NULL eval should be a rounding error; any remaining NULLs route to `parity`.

- `user_eval = sign * eval_cp` where `sign = +1` for white, `−1` for black.
- If `eval_mate IS NOT NULL`: treat as ±∞ in the user's perspective (positive `user_eval = sign * eval_mate > 0` ⇒ user has the mate ⇒ conversion; negative ⇒ recovery).
- Else if `eval_cp IS NOT NULL`: bucket on `user_eval` vs `EVAL_ADVANTAGE_THRESHOLD = 100` cp.
  - `conversion` if `user_eval >=  100`
  - `recovery`   if `user_eval <= -100`
  - `parity`     otherwise
- Else (both NULL): `parity`.

The mate-score handling matches `_classify_endgame_bucket` exactly — mate scores skip the cp threshold and force conversion/recovery.

### Per-bucket rate definitions (mirror `_endgame_skill_from_bucket_rows`)
- conversion → `1.0` if user won else `0.0` (Win %)
- parity → user score `1.0 / 0.5 / 0.0` (Score %)
- recovery → `1.0` if user won or drew else `0.0` (Save %)

### Population bucket prevalence (reference, 2026-05-03)

How endgame-entry games partition into the three buckets across the benchmark DB (selected users, `status='completed'`, sparse `(2400, classical)` cell excluded). Useful as a sanity check for bucketing changes — if a refactor of the eval rule moves these numbers more than ~1pp it warrants investigation.

Cell = `n (%) [avg user_eval_cp]`. The eval is `sign * eval_cp` (user-perspective), averaged across games where `eval_cp IS NOT NULL` (mate scores excluded from the average).

| Filter | n_games | conversion | parity | recovery | overall avg eval |
|---|---:|---:|---:|---:|---:|
| Base only (`rated AND NOT is_computer_game`) | 708,032 | 274,391 (38.75%) [+430 cp] | 177,987 (25.14%) [+1 cp] | 255,654 (36.11%) [−429 cp] | +12 cp |
| Base + equal-footing (`abs(opp_rating − user_rating) ≤ 100`) | 554,608 | 211,443 (38.12%) [+430 cp] | 137,133 (24.73%) [+1 cp] | 206,032 (37.15%) [−430 cp] | +4 cp |

The equal-footing filter retains ~78% of games and shrinks the conversion–recovery gap from +2.7pp to +1.0pp, consistent with higher-rated cohorts padding their conversion rate via softer matchmaking. The overall user-perspective eval also shrinks from +12 cp to +4 cp, confirming the same matchmaking confound at the eval level. Per-bucket eval magnitudes (~±430 cp) are nearly identical across filter regimes — the equal-footing filter changes which games qualify, not the within-bucket eval distribution. Buckets are roughly balanced (≈38 / 25 / 37), so eval-coverage regressions to NULL would noticeably swell the parity bucket and shift its avg-eval column toward the games-without-eval cohort's true distribution.

### Eval distribution at endgame entry (reference, 2026-05-03)

Shape of the per-game user-perspective eval (`sign * eval_cp`) at first endgame ply, equal-footing filter applied, mate scores and NULL eval excluded. Useful when evaluating whether to surface "avg eval at endgame entry" as a user-facing metric — the per-game noise is the relevant constraint for any per-user mean displayed in the live UI.

**Summary** (n = 541,642): mean = **+4.0 cp**, **SD = 417.9 cp**, median = 0, IQR `[−300, +312]`, p05/p95 `[−681, +684]`.

**Histogram (100 cp bins, % of games):**

| bin (cp) | pct | bin (cp) | pct |
|---:|---:|---:|---:|
| ≤ −1000 | 0.45 | +0…+100 | **13.76** |
| −1000…−900 | 0.55 | +100…+200 | 6.44 |
| −900…−800 | 1.18 | +200…+300 | 5.72 |
| −800…−700 | 2.28 | +300…+400 | 5.71 |
| −700…−600 | 3.18 | +400…+500 | 7.08 |
| −600…−500 | 4.97 | +500…+600 | 5.07 |
| −500…−400 | 6.87 | +600…+700 | 3.26 |
| −400…−300 | 5.50 | +700…+800 | 2.29 |
| −300…−200 | 5.53 | +800…+900 | 1.22 |
| −200…−100 | 6.29 | +900…+1000 | 0.56 |
| −100…0 | **11.62** | ≥ +1000 | 0.48 |

**Shape:** strong central peak (~25% of games within ±100 cp), gentle dip in ±200–300, mild secondary shoulders around ±400–500 ("piece hung in the middlegame" cohort), symmetric tails decaying out past ±1000. **Trimodal-ish, not bimodal** — the central peak dominates by a wide margin. Conv-vs-recov bucket counts (38/25/37) are not a faithful split of the eval distribution: most parity-bucket games sit in the central spike, but conversion/recovery buckets have substantial mass at moderate evals (±150-300) on top of the heavy ±400-500 shoulder.

**Sample-size implications for per-user mean significance** (test against 0, α=0.05, 80% power, with σ ≈ 418 cp ⇒ n ≈ 16·σ²/Δ²):

| effect Δ (cp) | n endgame games |
|---:|---:|
| +50 | ~1,100 |
| +100 | ~280 |
| +200 | ~70 |

So a per-user sig test against 0 reliably catches users systematically entering at ≳+150 cp ("you outplay opponents into endgames") on a few-hundred-game corpus, and will say "no signal" for genuine +50 to +100 cp users. UI copy should phrase the null as "we can't tell" rather than "no advantage."

### Eval × clock-diff cross-user correlation (reference, 2026-05-03)

Cross-user Pearson correlation between **per-user mean eval at endgame entry** (cp) and **per-user mean clock-diff %** (`(user_clk - opp_clk) / base_time_seconds * 100`). Filter floor: ≥30 endgame games/user/TC, mate scores excluded, equal-footing applied. Computed to test whether the proposed user-facing narrative *"you enter endgames at +X cp but pay for it with Y% less time"* is supported by population-level co-movement.

| TC | n users | Pearson r | avg user_mean_eval (cp) | avg user_mean_clock_diff (%) |
|---|---:|---:|---:|---:|
| bullet | 494 | **−0.43** | −2 | −0.16 |
| blitz | 494 | **−0.33** | +14 | −1.38 |
| rapid | 482 | −0.00 | +22 | −1.47 |
| classical | 212 | +0.06 | +7 | −4.52 |
| pooled | 1,682 | −0.13 | +11 | −1.44 |

**Interpretation:** the trade-off is real in **bullet/blitz** — users who systematically enter endgames at higher eval do systematically have lower relative clock. r ≈ −0.4 is moderate but unambiguous. In **rapid/classical** the correlation collapses to zero — time isn't the binding constraint, so eval differences and clock differences come from independent sources (skill vs move-pace habits). The pooled r = −0.13 is dominated by the bullet/blitz signal.

**Design implication:** a global "you paid for it with time" framing in the live UI would tell a false causal story to roughly half of users (everyone on rapid/classical). Three honest options: (a) show the two numbers as independent facts, (b) compute per-user across-game r and gate the trade-off framing on it, (c) TC-gate the framing (bullet/blitz only). Note that this is **cross-user** correlation; the within-user across-games version is what actually backs a user's own dashboard claim, but the cross-user zero in slow TCs strongly suggests the within-user effect is unlikely to be robust there either.

**Per-user-mean averaging caveat:** the user-weighted mean eval (+11 cp pooled) sits higher than the game-weighted population mean (+4 cp from the prevalence table) because each user counts equally regardless of game count. Both numbers are "right" — pick the unit that matches the framing.

### Endgame Skill
Unweighted mean of the non-empty per-bucket rates. A user with all three buckets has `skill = (conv + par + recov) / 3`; one with only parity has `skill = parity_rate`. Sample floor: ≥20 endgame games per user per cell + ≥2 of 3 buckets non-empty (defensive — with eval coverage near 100% essentially every user has all three).

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
    ep.eval_cp   AS entry_eval_cp,    -- white-perspective Stockfish eval at endgame entry
    ep.eval_mate AS entry_eval_mate   -- white-perspective mate-in-N at endgame entry
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe ON fe.game_id = g.id
  JOIN game_positions ep
    ON ep.game_id = g.id AND ep.ply = fe.entry_ply
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all sections)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
),
classified AS (
  -- Mirrors _classify_endgame_bucket: mate first (forces conv/recov), then cp vs ±100, NULL = parity.
  SELECT
    user_id, elo_bucket, tc, score,
    CASE
      WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) > 0 THEN 'conversion'
      WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) < 0 THEN 'recovery'
      WHEN entry_eval_cp   IS NOT NULL AND (entry_eval_cp   * color_sign) >=  100 THEN 'conversion'
      WHEN entry_eval_cp   IS NOT NULL AND (entry_eval_cp   * color_sign) <= -100 THEN 'recovery'
      ELSE 'parity'
    END AS bucket,
    CASE
      WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) > 0
        THEN CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END
      WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) < 0
        THEN CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END
      WHEN entry_eval_cp   IS NOT NULL AND (entry_eval_cp   * color_sign) >=  100
        THEN CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END
      WHEN entry_eval_cp   IS NOT NULL AND (entry_eval_cp   * color_sign) <= -100
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

## Section 3 — Evals at game phase transitions

**Question:** At the first ply of the middlegame (and endgame), how does the per-(user, color) Stockfish eval distribute *after centering on a symmetric ±BASELINE*? The output calibrates the bullet chart's neutral and domain bounds for per-(user, opening, color) cells, where the live z-test runs `delta = signed_user_pov_eval − baseline_C` (Phase 80 area for MG; Phase 81+ for EG).

**Two metrics, same shape (twin tile):**
- **Middlegame-entry eval** — per-(user, color) mean signed user-POV eval at the first ply where `phase = 1`.
- **Endgame-entry eval** — per-(user, color) mean signed user-POV eval at the first ply where `phase = 2`.

### Phase-entry definitions

Both entry plies come from `game_positions.phase` (SmallInteger, `0=opening / 1=middlegame / 2=endgame`; see `app/models/game_position.py:90-94`). The endgame-entry definition is consistent with §2 / §4 / §6's `endgame_class IS NOT NULL` thanks to **PHASE-INV-01** (`phase=2 ⟺ endgame_class IS NOT NULL`). Future edits to either definition must preserve this invariant — if PHASE-INV-01 is ever broken, §3's endgame metric and the §2/§4/§6 metrics will silently drift apart.

### Symmetric baseline — the calibration target

The baseline encodes Stockfish's structural first-move tempo for white at the entry ply. We use a **symmetric** baseline by construction: `EVAL_BASELINE_CP_WHITE = +X`, `EVAL_BASELINE_CP_BLACK = −X`, computed from a **single deduplicated game-level mean** (one row per `(platform, platform_game_id)`, white-POV).

Why dedupe: the benchmark sample stores one row per (benchmark user, game). The white-user and black-user slices are made up of almost entirely *different* physical games (typically <1% overlap), so the per-color slice means absorb the small skill edge of benchmark users vs their typical opponent and split asymmetrically (e.g. +31.5 / −18.9 in 2026-05 Lichess). Deduping to physical games cancels that skill edge and yields a single number (~+25 cp for current data). The symmetric baseline is then `+X / −X`, which:

- Folds the engine-tempo asymmetry into the baseline cleanly.
- Leaves the centered per-(user, color) distributions the **same shape** in both colors, offset by at most the benchmark skill edge (~±6 cp), which is small relative to the per-user-mean SD (~75 cp) and irrelevant to bullet-chart zone widths.
- Eliminates the need for a per-color sub-block, color-axis Cohen's d, or per-color skew/kurtosis — all degenerate under symmetry.

**Methodology change history:**
- 2026-05-04 v3 (this version): symmetric baseline from deduped game-level mean. Color-split sub-block, color-axis Cohen's d, and per-color skew/kurtosis dropped — degenerate by construction. Both color slices pool into a single calibration distribution.
- 2026-05-04 v2 (rejected): per-color asymmetric baselines (+31.5 / −18.9) computed from per-user-color slices. Rejected — the asymmetry was a sampling artefact of the single-row-per-benchmark-user data shape, not a real population effect. Per-color baselines were harder to explain and didn't improve calibration.
- 2026-05-04 v1 (rejected): per-user mean pooled across colors. Rejected — conflated color-mix variance with within-color spread.
- Pre-2026-05-04 (rejected): per-user median. Rejected for definitional consistency with the live z-test (`mean = eval_sum / n`).

### Sign convention

User-POV: `signed_cp = CASE WHEN user_color='white' THEN eval_cp ELSE -eval_cp END`. Positive values mean the user is winning at the entry ply. Centered: `delta = signed_cp − (CASE WHEN user_color='white' THEN +X ELSE -X END)`.

### Mate handling and outlier trim — match production exactly

The production aggregator (`app/repositories/stats_repository.py:556-560`, `has_continuous_in_domain_eval` predicate) feeds the live z-test only rows where:

- `eval_cp IS NOT NULL`
- `eval_mate IS NULL`           (mate scores excluded entirely — no sentinel)
- `abs(eval_cp) < 2000`          (D-08 outlier trim, `EVAL_OUTLIER_TRIM_CP = 2000`)

§3 must apply the **same three filters** in both passes so per-user means are computed over the same row set the live test consumes. Mate scores are reported separately as a footnote count, but never folded into the mean (no sentinel). NULL-eval rows are dropped (not routed to 0). Outlier rows (`|eval_cp| >= 2000`) are dropped (not clipped).

### Sample floor

≥ 20 games per user with a continuous in-domain eval at the entry ply (matches `EVAL_CONFIDENCE_MIN_N = 20` in `opening_insights_constants.py` — same gate the live z-test uses). Two notes on the asymmetry:
- **Middlegame entry retains ≈ all qualifying games** — almost every rated game reaches `phase = 1`.
- **Endgame entry retains the games that reach `phase = 2`** — closer to the §2/§4-style endgame-reaching subset, but *without* the §2/§4 `≥ 6 endgame plies` requirement (§3's metric only needs the entry ply itself to exist). Per-cell sample sizes for the endgame metric will therefore be slightly looser than §2/§4's.

### Eval coverage sanity check

Reuse the §2-area "Eval coverage check" CTE pattern, parameterized over phase: substitute `WHERE phase = 1` (and drop the `HAVING count(*) >= 6`) for middlegame entry, `WHERE phase = 2` for endgame entry. Lichess analyzed games typically have eval from move 1, but partial-analysis games can be sparser at early plies — flag in the report header if **middlegame-entry coverage is materially below endgame-entry coverage** (e.g. >2 pp gap). NULL-eval and mate-eval entry plies are excluded from the per-user mean (matching production), so a coverage drop biases the mean toward whichever subset of games happens to have continuous in-domain eval. Report mate-row prevalence as a footnote.

### Query

The query runs in **two passes** per metric:
1. **Symmetric baseline pass (deduped, game-level)** — produces `BASELINE_CP` (one number, white-POV). Inlined into pass 2. NO equal-footing filter — calibrate against the production-realistic regime, matching what the live z-test consumes.
2. **Centered per-(user, color) pooled distribution** — the calibration target.

```sql
-- Pass 1: symmetric engine baseline at MG entry, deduped per physical game.
-- Substitute phase = 2 for endgame entry. NO equal-footing filter.
WITH first_phase AS (
  SELECT game_id, MIN(ply) AS entry_ply
  FROM game_positions
  WHERE phase = 1   -- swap to 2 for EG entry
  GROUP BY game_id
),
phase_entry AS (
  SELECT g.platform, g.platform_game_id, gp.eval_cp AS raw_cp_white_pov
  FROM games g
  JOIN first_phase fp ON fp.game_id = g.id
  JOIN game_positions gp ON gp.game_id = g.id AND gp.ply = fp.entry_ply
  WHERE g.rated AND NOT g.is_computer_game
    AND gp.eval_cp IS NOT NULL AND gp.eval_mate IS NULL
    AND abs(gp.eval_cp) < 2000   -- match production trim from D-08
),
deduped AS (
  SELECT DISTINCT ON (platform, platform_game_id) raw_cp_white_pov
  FROM phase_entry
  ORDER BY platform, platform_game_id
)
SELECT
  COUNT(*) AS n_games,
  ROUND(AVG(raw_cp_white_pov)::numeric, 2) AS baseline_cp_white,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY raw_cp_white_pov)::numeric, 1) AS median_white_pov,
  ROUND(STDDEV_SAMP(raw_cp_white_pov)::numeric, 1) AS sd_white_pov
FROM deduped;
```

For 2026-05 Lichess at MG entry the deduped baseline was **+25 cp** (n=1.25M; median +24; SD 238). Black baseline = −25 cp by construction.

```sql
-- Pass 2: per-(user, color) centered, pooled distribution at MG entry.
-- Substitute baseline value from pass 1 below (BASELINE_CP_WHITE).
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.rating_bucket, bsu.tc_bucket
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
first_middlegame AS (
  SELECT game_id, min(ply) AS entry_ply FROM game_positions WHERE phase = 1 GROUP BY game_id
),
games_filtered AS (
  SELECT g.id AS game_id, g.user_id, g.user_color::text AS user_color,
         su.rating_bucket AS elo_bucket, su.tc_bucket AS tc
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all sections)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color::text='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
),
mid_entry AS (
  -- Match production filter: continuous in-domain eval only.
  SELECT gf.user_id, gf.elo_bucket, gf.tc, gf.user_color, gp.eval_cp AS raw_cp
  FROM games_filtered gf
  JOIN first_middlegame fm ON fm.game_id = gf.game_id
  JOIN game_positions gp ON gp.game_id = gf.game_id AND gp.ply = fm.entry_ply
  WHERE gp.eval_cp IS NOT NULL AND gp.eval_mate IS NULL AND abs(gp.eval_cp) < 2000
),
mid_per_user_color AS (
  -- One row per (user, color) cell.
  SELECT user_id, elo_bucket, tc, user_color,
         avg(CASE WHEN user_color='white' THEN raw_cp ELSE -raw_cp END) AS mean_signed_cp
  FROM mid_entry
  GROUP BY user_id, elo_bucket, tc, user_color
  HAVING count(*) >= 20
),
mid_centered AS (
  -- Symmetric centering. Sparse-cell exclusion applied here.
  SELECT mean_signed_cp - (CASE WHEN user_color='white' THEN 25.0 ELSE -25.0 END) AS centered_cp,
         elo_bucket, tc
  FROM mid_per_user_color
  WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
)
SELECT
  count(*) AS n,
  round(avg(centered_cp)::numeric, 2) AS ctr_mean,
  round(stddev_samp(centered_cp)::numeric, 1) AS ctr_sd,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p95
FROM mid_centered;
```

**Repeat** for endgame entry: substitute `first_middlegame` → `first_endgame` (`WHERE phase = 2`) in both passes, and the MG baseline `25.0` → the EG baseline from pass 1. Sparse-cell exclusion (`(2400, classical)`) applies inside `*_centered`.

**TC and ELO collapse verdicts on centered data.** `GROUP BY tc` (resp. `elo_bucket`) over `mid_centered` / `eg_centered`, then apply Cohen's d (max group mean minus min group mean, divided by sqrt(avg of group variances)). Centering is constant within a color so within-color spread is unchanged; report once for the headline summary.

### Output (one block per metric: Middlegame entry, Endgame entry)

1. **Symmetric baseline table** — single row from pass 1: `n_games / baseline_cp_white / median / SD` (white-POV, deduped).
2. **Centered pooled distribution table** — single row from pass 2: `n / mean / p05 / p25 / p50 / p75 / p95 / SD`.
3. **Collapse verdict block** — TC (d_max on centered) and ELO (d_max on centered). Color collapse is automatic by construction; do not report.
4. **Recommendations** per metric:
   - **Baseline constant**: compare pass-1 `baseline_cp_white` to live `EVAL_BASELINE_CP_WHITE` (in `app/services/opening_insights_constants.py`). Recommend update when |measured − constant| > 5 cp; round to whole cp. `EVAL_BASELINE_CP_BLACK` should always equal `-EVAL_BASELINE_CP_WHITE` — flag if violated.
   - **Neutral-zone bounds**: pooled centered `[p25, p75]`, rounded to **symmetric ±X cp** (use the larger of |p25|, |p75| rounded to nearest 5 cp). Asymmetric bounds only if `|ctr_mean| > 10 cp` (means the benchmark skill edge is large enough to bias zones).
   - **Domain bounds**: pooled centered `[p05, p95]`, rounded to symmetric ±X cp. Stretch to cover the 800-cohort tail if the bullet chart serves all ELOs.
   - **Comparison vs live constants**: grep against `EVAL_NEUTRAL_MIN/MAX_PAWNS` and `EVAL_BULLET_DOMAIN_PAWNS` in `frontend/src/lib/openingStatsZones.ts`. Recommend update when |measured − constant| > 5 cp.
   - **Mate-row footnote**: count of mate rows excluded by the `eval_mate IS NULL` filter (per metric, total across the deduped sample).

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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all sections)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all sections)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
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

**Bucketing**: per REFAC-02, conv/recov is determined by the Stockfish eval at the **first ply of each class span** (not at the game's first endgame ply). This matches `query_endgame_entry_rows`, which projects `eval_cp` / `eval_mate` per (game, endgame_class) span via `array_agg(... ORDER BY ply)[1]`. The classification rule is identical to Section 2: mate scores force conv/recov; otherwise cp vs ±`EVAL_ADVANTAGE_THRESHOLD = 100`; NULL routes to parity. There is no longer a 4-ply persistence join — the old material-imbalance proxy is gone.

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
  -- Pull the Stockfish eval at the FIRST ply of each (game, class) span (REFAC-02).
  -- White-perspective raw; sign flip happens below via color_sign.
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
    ep.eval_cp   AS entry_eval_cp,
    ep.eval_mate AS entry_eval_mate
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN class_span cs ON cs.game_id = g.id
  JOIN game_positions ep
    ON ep.game_id = g.id AND ep.ply = cs.entry_ply
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all sections)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
),
classified AS (
  -- Apply _classify_endgame_bucket: mate first, else cp vs ±100, else parity (NULL or in-band).
  SELECT
    *,
    CASE
      WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) > 0 THEN 'conversion'
      WHEN entry_eval_mate IS NOT NULL AND (entry_eval_mate * color_sign) < 0 THEN 'recovery'
      WHEN entry_eval_cp   IS NOT NULL AND (entry_eval_cp   * color_sign) >=  100 THEN 'conversion'
      WHEN entry_eval_cp   IS NOT NULL AND (entry_eval_cp   * color_sign) <= -100 THEN 'recovery'
      ELSE 'parity'
    END AS bucket
  FROM bucketed
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
  count(*) FILTER (WHERE bucket = 'conversion') AS conv_games,
  round((avg(CASE WHEN score = 1.0 THEN 1.0 ELSE 0.0 END)
         FILTER (WHERE bucket = 'conversion'))::numeric, 4) AS conversion,
  count(*) FILTER (WHERE bucket = 'recovery') AS recov_games,
  round((avg(CASE WHEN score >= 0.5 THEN 1.0 ELSE 0.0 END)
         FILTER (WHERE bucket = 'recovery'))::numeric, 4) AS recovery
FROM classified
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
- **Equal-footing filter (universal — all sections)**: `abs(opp_rating - user_rating) <= 100`. Applied to every per-game CTE in §1, §2, §4, §5, §6 to remove the matchmaking confound (high-rated cohorts otherwise play systematically weaker opponents and inflate the apparent ELO ramp on every metric). Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. Scope changed from §2/§6-only to universal on 2026-05-03; pre-2026-05-03 §1/§4/§5 numbers are not directly comparable. If a non-sparse cell drops below sample floor after filtering, escalate by re-selecting/re-ingesting more users/games rather than relaxing the filter. See `.planning/notes/benchmark-equal-footing-framing.md` for rationale.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in section 6). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity). REFAC-02 — the old `material_imbalance + 4-ply persistence` proxy is gone; sections 2/3/6 read `eval_cp` / `eval_mate` directly.
- **Eval coverage**: <pct>% of qualifying endgame entries have non-NULL eval (`eval_cp IS NOT NULL OR eval_mate IS NOT NULL`). Expected ~100% on the benchmark DB after the Stockfish backfill — flag if < 99%.
- **Sparse-cell exclusion**: `(2400, classical)` is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user, pool exhausted). It is still shown in cell-level 5×4 tables with an `n=12*` footnote. Revisit if a future dump produces ≥40 completed users at ≥200 games/user.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate
- **Sample floors**: <floors used per section>
- **Cell coverage** (status='completed' users per cell): <inline 5×4 table, sparse cell flagged>

## 1. Score gap (endgame vs non-endgame)
... (cell table, marginals, recommendations, **collapse verdict block**)

## 2. Conversion / Parity / Recovery + Endgame Skill
... (one block per metric, each with cell table, marginals, recommendations, **collapse verdict block**)

## 3. Evals at game phase transitions
... (two blocks: middlegame entry, endgame entry; each with **symmetric baseline table** (deduped game-level mean, white-POV) comparing live `EVAL_BASELINE_CP_WHITE` against measured value, **centered pooled distribution table** (per-(user, color) means centered on ±BASELINE), proposed neutral-zone and domain bounds, **collapse verdict block** (TC + ELO only — color collapse is automatic by construction))

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
| Middlegame-entry eval (per-user median) | ... | ... | ... |
| Endgame-entry eval (per-user median) | ... | ... | ... |
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

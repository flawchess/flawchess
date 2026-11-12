# Benchmarks — per-subchapter reference SQL

QA reference for what `scripts/gen_benchmarks.py` computes (`scripts/benchmarks/chapter*.py`). Do not execute these by hand to produce a report; the generator is the source of numbers. Building blocks (Standard CTE, `user_elo_at_game` / `elo_bucket`, equal-footing filter) live in SKILL.md "Shared SQL building blocks".

## 1. Full-game analysis share

```sql
WITH selected_users AS ( /* Standard CTE */ ),
gt AS (
  SELECT (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS ueag,
         su.tc_bucket AS tc,
         (g.white_blunders IS NOT NULL) AS analyzed,
         (g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
          AND abs(...) <= 100)                                   AS ef
  FROM games g JOIN selected_users su ON su.user_id = g.user_id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
)
SELECT (/* canonical elo_bucket CASE */) AS elo, tc,
       count(*) AS games,
       count(*) FILTER (WHERE analyzed)          AS analyzed,
       count(*) FILTER (WHERE ef)                AS games_ef,
       count(*) FILTER (WHERE ef AND analyzed)   AS analyzed_ef
FROM gt WHERE ueag >= 800 GROUP BY 1, 2;
```

## 2.1 Middlegame-entry eval

```sql
-- Pass 1: symmetric engine baseline at MG entry, deduped per physical game.
-- NO equal-footing filter.
WITH first_phase AS (
  SELECT game_id, MIN(ply) AS entry_ply
  FROM game_positions
  WHERE phase = 1   -- swap to 2 for EG entry (see 3.1.2)
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

```sql
-- Pass 2: per-(user, color) centered, pooled distribution at MG entry.
-- Substitute baseline value from pass 1 below (BASELINE_CP_WHITE).
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
         -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
         (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
         (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
               ELSE 2400 END) AS elo_bucket, su.tc_bucket AS tc
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
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

## 3.1.1 Non-Endgame Score (per-user)

```sql
-- Reuse 3.1.6's per_user CTE and aggregate non_eg_score directly.
SELECT
  count(*) AS n_users,
  round(avg(non_eg_score)::numeric, 4) AS non_eg_mean,
  round(stddev_samp(non_eg_score)::numeric, 4) AS non_eg_sd,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY non_eg_score)::numeric, 4) AS non_eg_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY non_eg_score)::numeric, 4) AS non_eg_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY non_eg_score)::numeric, 4) AS non_eg_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY non_eg_score)::numeric, 4) AS non_eg_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY non_eg_score)::numeric, 4) AS non_eg_p95
FROM per_user
WHERE NOT (elo_bucket = 2400 AND tc = 'classical');
```

## 3.1.2 Endgame-entry eval (pawns)

```sql
-- Pass 1: symmetric engine baseline at EG entry, deduped per physical game.
-- NO equal-footing filter.
WITH first_phase AS (
  SELECT game_id, MIN(ply) AS entry_ply
  FROM game_positions
  WHERE phase = 2
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

```sql
-- Pass 2: per-(user, color) pooled distribution at EG entry.
-- Substitute the EG baseline from pass 1 in place of 25.0 below.
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
first_endgame AS (
  SELECT game_id, min(ply) AS entry_ply FROM game_positions WHERE phase = 2 GROUP BY game_id
),
games_filtered AS (
  SELECT g.id AS game_id, g.user_id, g.user_color::text AS user_color,
         -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
         (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
         (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
               WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
               ELSE 2400 END) AS elo_bucket, su.tc_bucket AS tc
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color::text='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
),
eg_entry AS (
  -- Match production filter: continuous in-domain eval only.
  SELECT gf.user_id, gf.elo_bucket, gf.tc, gf.user_color, gp.eval_cp AS raw_cp
  FROM games_filtered gf
  JOIN first_endgame fe ON fe.game_id = gf.game_id
  JOIN game_positions gp ON gp.game_id = gf.game_id AND gp.ply = fe.entry_ply
  WHERE gp.eval_cp IS NOT NULL AND gp.eval_mate IS NULL AND abs(gp.eval_cp) < 2000
),
eg_per_user_color AS (
  -- One row per (user, color) cell — UNCENTERED user-POV mean (drives the live tile).
  SELECT user_id, elo_bucket, tc, user_color,
         avg(CASE WHEN user_color='white' THEN raw_cp ELSE -raw_cp END) AS mean_signed_cp
  FROM eg_entry
  GROUP BY user_id, elo_bucket, tc, user_color
  HAVING count(*) >= 20
),
eg_uncentered AS (
  -- Uncentered — feeds the 0-centered EG-entry bullet (recommendations read from this).
  SELECT mean_signed_cp AS uncentered_cp, elo_bucket, tc
  FROM eg_per_user_color
  WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
),
eg_centered AS (
  -- Centered (reported for Cohen's d / methodological parity with 2.1).
  -- Replace 25.0 with the pass-1 baseline_cp_white from this subchapter.
  SELECT mean_signed_cp - (CASE WHEN user_color='white' THEN 25.0 ELSE -25.0 END) AS centered_cp,
         elo_bucket, tc
  FROM eg_per_user_color
  WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
)
SELECT
  'uncentered' AS variant,
  count(*) AS n,
  round(avg(uncentered_cp)::numeric, 2) AS mean_cp,
  round(stddev_samp(uncentered_cp)::numeric, 1) AS sd_cp,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY uncentered_cp)::numeric, 1) AS p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY uncentered_cp)::numeric, 1) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY uncentered_cp)::numeric, 1) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY uncentered_cp)::numeric, 1) AS p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY uncentered_cp)::numeric, 1) AS p95
FROM eg_uncentered
UNION ALL
SELECT
  'centered' AS variant,
  count(*) AS n,
  round(avg(centered_cp)::numeric, 2) AS mean_cp,
  round(stddev_samp(centered_cp)::numeric, 1) AS sd_cp,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY centered_cp)::numeric, 1) AS p95
FROM eg_centered;
```

## 3.1.3 Achievable Score (Stockfish-predicted expected score at EG entry)


```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
entry_rows AS (
  -- One row per game: the first endgame-class ply (lowest ply where endgame_class IS NOT NULL).
  SELECT
    gp.game_id, gp.eval_cp, gp.eval_mate,
    ROW_NUMBER() OVER (PARTITION BY gp.game_id ORDER BY gp.ply ASC) AS rn
  FROM game_positions gp
  JOIN endgame_game_ids eg ON eg.game_id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
),
rows AS (
  SELECT
    g.user_id,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket AS tc,
    -- Per-game expected_score from the user's perspective:
    --   mate forces 0 or 1 (sign-flipped for black),
    --   |cp| < 2000 uses the Lichess winning-chances sigmoid (k=0.00368208),
    --   |cp| >= 2000 is clamped to NULL (treated as decisive but mate-undeclared — caller can decide).
    CASE
      WHEN er.eval_mate IS NOT NULL AND (er.eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0
      WHEN er.eval_mate IS NOT NULL AND (er.eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) < 0 THEN 0.0
      WHEN er.eval_cp IS NOT NULL AND abs(er.eval_cp) < 2000
           THEN 1.0 / (1.0 + exp(-0.00368208 * (er.eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
      ELSE NULL
    END AS expected_score
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN entry_rows er ON er.game_id = g.id AND er.rn = 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
),
per_user AS (
  SELECT user_id, elo_bucket, tc,
    avg(expected_score) AS entry_xs
  FROM rows
  GROUP BY user_id, elo_bucket, tc
  HAVING count(*) FILTER (WHERE expected_score IS NOT NULL) >= 20
),
per_user_excl_sparse AS (
  -- Sparse-cell exclusion mirrors universal handling.
  SELECT * FROM per_user
  WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  round(avg(entry_xs)::numeric, 4) AS xs_mean,
  round(stddev_samp(entry_xs)::numeric, 4) AS xs_sd,
  round(var_samp(entry_xs)::numeric, 6) AS xs_var,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY entry_xs)::numeric, 4) AS xs_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY entry_xs)::numeric, 4) AS xs_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY entry_xs)::numeric, 4) AS xs_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY entry_xs)::numeric, 4) AS xs_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY entry_xs)::numeric, 4) AS xs_p95
FROM per_user_excl_sparse
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

The full 5×4 cell table re-runs the same shape for the sparse `(2400, classical)` cell with an `n=2*` footnote (12 completed users overall, most below the 20-game floor). TC marginal, ELO marginal, and pooled overall come from re-aggregating `per_user_excl_sparse` over `tc` only / `elo_bucket` only / no group. `xs_mean` / `xs_var` columns feed Cohen's d per the canonical "Computing Cohen's d in SQL" recipe.

## 3.1.4 Endgame Score (per-user, EG-only)


```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket AS tc,
    CASE
      WHEN (g.result = '1-0' AND g.user_color = 'white')
        OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
      WHEN g.result = '1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN endgame_game_ids eg ON eg.game_id = g.id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
),
per_user AS (
  SELECT
    user_id, elo_bucket, tc,
    count(*) AS eg_games,
    avg(score) AS eg_score
  FROM rows
  GROUP BY user_id, elo_bucket, tc
  HAVING count(*) >= 20
),
per_user_excl_sparse AS (
  -- Sparse-cell exclusion mirrors universal handling.
  SELECT * FROM per_user
  WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  round(avg(eg_score)::numeric, 4) AS eg_mean,
  round(stddev_samp(eg_score)::numeric, 4) AS eg_sd,
  round(var_samp(eg_score)::numeric, 6) AS eg_var,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY eg_score)::numeric, 4) AS eg_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY eg_score)::numeric, 4) AS eg_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY eg_score)::numeric, 4) AS eg_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY eg_score)::numeric, 4) AS eg_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY eg_score)::numeric, 4) AS eg_p95
FROM per_user_excl_sparse
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

The full 5×4 cell table also re-runs the same shape for the sparse `(2400, classical)` cell with an `n=12*` footnote. TC marginal, ELO marginal, and pooled overall come from re-aggregating `per_user_excl_sparse` over `tc` only / `elo_bucket` only / no group. The `eg_mean` / `eg_var` columns feed Cohen's d per the canonical "Computing Cohen's d in SQL" recipe.

## 3.1.5 Achievable Score Gap


```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
entry_rows AS (
  -- One row per game: the first endgame-class ply.
  SELECT
    gp.game_id, gp.eval_cp, gp.eval_mate,
    ROW_NUMBER() OVER (PARTITION BY gp.game_id ORDER BY gp.ply ASC) AS rn
  FROM game_positions gp
  JOIN endgame_game_ids eg ON eg.game_id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
),
rows AS (
  -- Mirror live filter: mate INCLUDED, |eval_cp| < 2000 only, both-NULL skipped.
  -- d_i = actual_score_i - expected_score_i (paired per-game diff).
  SELECT
    g.user_id,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket AS tc,
    -- actual_score_i (user POV)
    CASE
      WHEN (g.result = '1-0' AND g.user_color = 'white')
        OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
      WHEN g.result = '1/2-1/2' THEN 0.5
      ELSE 0.0
    END
    -
    -- expected_score_i (user POV; mate -> 0/1, cp -> Lichess sigmoid)
    CASE
      WHEN er.eval_mate IS NOT NULL AND (er.eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0
      WHEN er.eval_mate IS NOT NULL AND (er.eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) < 0 THEN 0.0
      WHEN er.eval_cp IS NOT NULL AND abs(er.eval_cp) < 2000
           THEN 1.0 / (1.0 + exp(-0.00368208 * (er.eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
      ELSE NULL  -- both-NULL or cp clip — dropped at the HAVING below
    END AS d_i
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN entry_rows er ON er.game_id = g.id AND er.rn = 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
),
per_user AS (
  SELECT user_id, elo_bucket, tc,
    count(*) FILTER (WHERE d_i IS NOT NULL) AS n_pairs,
    avg(d_i) AS achievable_gap,
    var_samp(d_i) AS d_var_within  -- per-user within-game variance (informational; not used for between-user Cohen's d)
  FROM rows
  GROUP BY user_id, elo_bucket, tc
  HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= 20
),
per_user_excl_sparse AS (
  -- Sparse-cell exclusion mirrors universal handling.
  SELECT * FROM per_user
  WHERE NOT (elo_bucket = 2400 AND tc = 'classical')
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  round(avg(achievable_gap)::numeric, 4) AS gap_mean,         -- proportion units (rendered as pp)
  round(stddev_samp(achievable_gap)::numeric, 4) AS gap_sd,
  round(var_samp(achievable_gap)::numeric, 6) AS gap_var,     -- between-user variance, feeds Cohen's d
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY achievable_gap)::numeric, 4) AS gap_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY achievable_gap)::numeric, 4) AS gap_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY achievable_gap)::numeric, 4) AS gap_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY achievable_gap)::numeric, 4) AS gap_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY achievable_gap)::numeric, 4) AS gap_p95
FROM per_user_excl_sparse
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

The full 5×4 cell table re-runs the same shape for the sparse `(2400, classical)` cell with an `n=N*` footnote. TC marginal, ELO marginal, and pooled overall come from re-aggregating `per_user_excl_sparse` over `tc` only / `elo_bucket` only / no group. `gap_mean` / `gap_var` columns feed Cohen's d per the canonical "Computing Cohen's d in SQL" recipe.

## 3.1.6 Endgame Score Gap and Timeline

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
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

## 3.2.1 Conversion / Parity / Recovery + Endgame Skill

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
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

## 3.2.2 Per-bucket ΔES Score Gap (Section 2 — Phase 87.2)


Equal-footing opponent filter (`abs(opp_rating - user_rating) <= 100`) preserved per memory `feedback_260503-fef` (universal as of 2026-05-03).

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
spans AS (
  -- One row per (game_id, endgame_class) span >= 6 plies, with entry eval at first ply.
  SELECT
    gp.game_id,
    gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN games g           ON g.id = gp.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE gp.endgame_class IS NOT NULL
    AND g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
  GROUP BY gp.game_id, gp.endgame_class
  HAVING count(gp.ply) >= 6
),
spans_with_next AS (
  SELECT
    s.*,
    lead(s.entry_eval_cp)   OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_cp,
    lead(s.entry_eval_mate) OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_mate
  FROM spans s
),
gap_rows AS (
  -- gap_span = exit_score - ES_entry. Bucket derived from entry eval per _classify_endgame_bucket.
  SELECT
    g.user_id,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket,
    -- Bucket assignment: mirrors _classify_endgame_bucket(eval_cp, eval_mate, user_color)
    CASE
      WHEN swn.entry_eval_mate IS NOT NULL THEN
        CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
          THEN 'conversion' ELSE 'recovery' END
      WHEN swn.entry_eval_cp IS NOT NULL THEN
        CASE
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100 THEN 'conversion'
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) <= -100 THEN 'recovery'
          ELSE 'parity'
        END
      ELSE 'parity'  -- NULL eval -> parity
    END AS bucket,
    (
      CASE
        WHEN next_eval_mate IS NOT NULL
          THEN CASE WHEN (next_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0 ELSE 0.0 END
        WHEN next_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 * (next_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE
          CASE
            WHEN (g.result='1-0' AND g.user_color='white')
              OR (g.result='0-1' AND g.user_color='black') THEN 1.0
            WHEN g.result='1/2-1/2' THEN 0.5
            ELSE 0.0
          END
      END
    )
    -
    (
      CASE
        WHEN swn.entry_eval_mate IS NOT NULL
          THEN CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0 ELSE 0.0 END
        WHEN swn.entry_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 * (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS gap_span
  FROM spans_with_next swn
  JOIN games g           ON g.id = swn.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) >= 800  -- drop sub-800
),
per_user_bucket AS (
  SELECT
    user_id, elo_bucket, tc_bucket, bucket,
    avg(gap_span)  AS mean_gap,
    count(*)       AS n_spans
  FROM gap_rows
  WHERE gap_span IS NOT NULL
    AND elo_bucket IS NOT NULL
    AND NOT (elo_bucket = 2400 AND tc_bucket = 'classical')  -- sparse-cell exclusion (game-time bucket)
  GROUP BY user_id, elo_bucket, tc_bucket, bucket
  HAVING count(*) >= 20         -- sample floor: >= 20 qualifying spans per user per bucket
)
SELECT
  bucket,
  elo_bucket,
  tc_bucket,
  count(*)                                                          AS n_users,
  round(avg(mean_gap)::numeric,              4)                    AS mean,
  round(stddev_samp(mean_gap)::numeric,      4)                    AS sd,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p95
FROM per_user_bucket
GROUP BY bucket, elo_bucket, tc_bucket
ORDER BY bucket, elo_bucket, tc_bucket;
```

Run a second pass for the pooled-across-cells distribution (sparse-cell exclusion already in CTE):

```sql
-- Pooled per-bucket (all cells combined, sparse-cell exclusion applied in CTE above).
SELECT
  bucket,
  count(*)                                                          AS n_users,
  round(avg(mean_gap)::numeric,              4)                    AS pooled_mean,
  round(stddev_samp(mean_gap)::numeric,      4)                    AS pooled_sd,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p75
FROM per_user_bucket
GROUP BY bucket
ORDER BY bucket;
```

## 3.3.1 Clock pressure at endgame entry

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
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

## 3.3.1 clock-gap-%

```sql
-- Extend the §3.3.1 query: replace per_user_cell with per_user_gap
per_user_gap AS (
  SELECT
    user_id, elo_bucket, tc,
    count(*) AS games,
    avg((user_clk - opp_clk) / NULLIF(base_time_seconds, 0)) AS mean_gap_frac
  FROM routed
  WHERE user_clk IS NOT NULL AND opp_clk IS NOT NULL
    AND base_time_seconds > 0
    AND user_clk <= 2.0 * base_time_seconds
    AND opp_clk <= 2.0 * base_time_seconds
    -- Equal-footing filter already applied in clock_raw
  GROUP BY user_id, elo_bucket, tc
  HAVING count(*) >= 20
)
SELECT
  elo_bucket, tc,
  count(*) AS n_users,
  round(avg(mean_gap_frac)::numeric, 4) AS gap_mean,
  round(var_samp(mean_gap_frac)::numeric, 6) AS gap_var,
  round(percentile_cont(0.05) WITHIN GROUP (ORDER BY mean_gap_frac)::numeric, 4) AS gap_p05,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY mean_gap_frac)::numeric, 4) AS gap_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY mean_gap_frac)::numeric, 4) AS gap_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY mean_gap_frac)::numeric, 4) AS gap_p75,
  round(percentile_cont(0.95) WITHIN GROUP (ORDER BY mean_gap_frac)::numeric, 4) AS gap_p95
FROM per_user_gap
GROUP BY elo_bucket, tc
HAVING count(*) >= 10
ORDER BY elo_bucket,
  CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

## 3.3.2 Time pressure vs performance

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
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

## §3.3.3 chess-score-per-pressure-bin


```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
endgame_games_with_clock AS (
  -- One row per game with endgame entry and clock data
  SELECT
    g.id AS game_id, g.user_id, g.user_color,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket AS tc,
    g.base_time_seconds, g.result,
    fe.entry_ply,
    -- user clock at endgame entry (same routing logic as _compute_clock_pressure)
    CASE
      WHEN g.user_color='white' AND fe.entry_ply % 2 = 0 THEN p1.clock_seconds
      WHEN g.user_color='white' AND fe.entry_ply % 2 = 1 THEN p2.clock_seconds
      WHEN g.user_color='black' AND fe.entry_ply % 2 = 1 THEN p1.clock_seconds
      ELSE p2.clock_seconds
    END AS user_clk,
    -- derived fields
    CASE
      WHEN g.user_color='white' AND fe.entry_ply % 2 = 0 THEN p1.clock_seconds
      WHEN g.user_color='white' AND fe.entry_ply % 2 = 1 THEN p2.clock_seconds
      WHEN g.user_color='black' AND fe.entry_ply % 2 = 1 THEN p1.clock_seconds
      ELSE p2.clock_seconds
    END / NULLIF(g.base_time_seconds, 0) * 100 AS user_clk_pct,
    -- game score from user perspective
    CASE
      WHEN (g.result='1-0' AND g.user_color='white')
        OR (g.result='0-1' AND g.user_color='black') THEN 1.0
      WHEN g.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe ON fe.game_id = g.id
  LEFT JOIN game_positions p1 ON p1.game_id = g.id AND p1.ply = fe.entry_ply
  LEFT JOIN game_positions p2 ON p2.game_id = g.id AND p2.ply = fe.entry_ply + 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.base_time_seconds > 0
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
    -- Drop sub-800 + sparse-cell exclusion (game-time ELO bucket — see "user_elo_at_game / elo_bucket" building block)
    AND (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) >= 800
    AND NOT ((CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) >= 2400
             AND su.tc_bucket = 'classical')
    -- Outlier guard on clock percentage
    AND (
      CASE
        WHEN g.user_color='white' AND fe.entry_ply % 2 = 0 THEN p1.clock_seconds
        WHEN g.user_color='white' AND fe.entry_ply % 2 = 1 THEN p2.clock_seconds
        WHEN g.user_color='black' AND fe.entry_ply % 2 = 1 THEN p1.clock_seconds
        ELSE p2.clock_seconds
      END / NULLIF(g.base_time_seconds, 0) * 100
    ) BETWEEN 0 AND 200
),
per_user_quintile AS (
  SELECT
    user_id, elo_bucket, tc,
    LEAST(4, FLOOR(user_clk_pct / 20.0)::int) AS quintile,
    count(*) AS n_games,
    avg(score) AS user_score
  FROM endgame_games_with_clock
  WHERE user_clk IS NOT NULL
  GROUP BY user_id, elo_bucket, tc, LEAST(4, FLOOR(user_clk_pct / 20.0)::int)
  HAVING count(*) >= 5  -- sample floor per bin
)
-- Per-(quintile, ELO, TC) distribution: use for Cohen's d + IQR band
SELECT
  quintile, elo_bucket, tc,
  count(*) AS n_users,
  round(avg(user_score)::numeric, 4) AS mean_score,
  round(var_samp(user_score)::numeric, 6) AS var_score,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY user_score)::numeric, 4) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY user_score)::numeric, 4) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY user_score)::numeric, 4) AS p75
FROM per_user_quintile
GROUP BY quintile, elo_bucket, tc
HAVING count(*) >= 10  -- Cohen's d floor
ORDER BY quintile, elo_bucket,
  CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 WHEN 'classical' THEN 4 END;
```

## 3.4.1 Per-class score / conversion / recovery

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
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
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
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

## 3.4.1 Per-user per-class score distribution

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
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
per_user_class AS (
  SELECT
    g.user_id,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block; drop sub-800 via WHERE user_elo_at_game >= 800)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket AS tc,
    cs.endgame_class AS endgame_class_int,
    count(*) AS n_games,
    avg(
      CASE
        WHEN (g.result='1-0' AND g.user_color='white')
          OR (g.result='0-1' AND g.user_color='black') THEN 1.0
        WHEN g.result='1/2-1/2' THEN 0.5
        ELSE 0.0
      END
    ) AS user_class_score
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN class_span cs ON cs.game_id = g.id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
    AND (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) >= 800  -- drop sub-800 (game-time ELO)
  GROUP BY g.user_id, user_elo_at_game, elo_bucket, su.tc_bucket, cs.endgame_class
  HAVING count(*) >= 10        -- min 10 games per user per class
)
SELECT
  CASE endgame_class_int
    WHEN 1 THEN 'rook'
    WHEN 2 THEN 'minor_piece'
    WHEN 3 THEN 'pawn'
    WHEN 4 THEN 'queen'
    WHEN 5 THEN 'mixed'
    WHEN 6 THEN 'pawnless'
  END AS endgame_class,
  count(*) AS n_users,
  round(avg(user_class_score)::numeric, 4) AS mean_score,
  round(percentile_cont(0.10) WITHIN GROUP (ORDER BY user_class_score)::numeric, 4) AS p10,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY user_class_score)::numeric, 4) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY user_class_score)::numeric, 4) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY user_class_score)::numeric, 4) AS p75,
  round(percentile_cont(0.90) WITHIN GROUP (ORDER BY user_class_score)::numeric, 4) AS p90
FROM per_user_class
GROUP BY endgame_class_int
ORDER BY endgame_class_int;
```

## 3.4.1 Per-class per-axis conv/recov rate distribution

```sql
-- TC-axis pass: unit = (user, tc, class), pooling ELO.
-- (CTEs selected_users / class_span / bucketed identical to the cell-level query,
--  EXCEPT classified adds: WHERE uelo>=800 AND NOT (elo_bucket=2400 AND tc='classical'))
, per_user_tc AS (
  SELECT user_id, tc, cls,
    avg(CASE WHEN score=1.0  THEN 1.0 ELSE 0.0 END) FILTER (WHERE bucket='conversion') AS conv_rate,
    count(*) FILTER (WHERE bucket='conversion') AS conv_n,
    avg(CASE WHEN score>=0.5 THEN 1.0 ELSE 0.0 END) FILTER (WHERE bucket='recovery')   AS recov_rate,
    count(*) FILTER (WHERE bucket='recovery')   AS recov_n
  FROM classified GROUP BY user_id, tc, cls
)
SELECT cls, tc,
  count(*) FILTER (WHERE conv_n>=10)  AS conv_users,
  round(avg(conv_rate)      FILTER (WHERE conv_n>=10)::numeric,4)  AS conv_mean,
  round(var_samp(conv_rate) FILTER (WHERE conv_n>=10)::numeric,6)  AS conv_var,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY conv_rate) FILTER (WHERE conv_n>=10)::numeric,4) AS conv_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY conv_rate) FILTER (WHERE conv_n>=10)::numeric,4) AS conv_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY conv_rate) FILTER (WHERE conv_n>=10)::numeric,4) AS conv_p75,
  count(*) FILTER (WHERE recov_n>=10) AS recov_users,
  round(avg(recov_rate)      FILTER (WHERE recov_n>=10)::numeric,4) AS recov_mean,
  round(var_samp(recov_rate) FILTER (WHERE recov_n>=10)::numeric,6) AS recov_var,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY recov_rate) FILTER (WHERE recov_n>=10)::numeric,4) AS recov_p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY recov_rate) FILTER (WHERE recov_n>=10)::numeric,4) AS recov_p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY recov_rate) FILTER (WHERE recov_n>=10)::numeric,4) AS recov_p75
FROM per_user_tc WHERE cls <= 5
GROUP BY cls, tc
ORDER BY cls, CASE tc WHEN 'bullet' THEN 1 WHEN 'blitz' THEN 2 WHEN 'rapid' THEN 3 ELSE 4 END;

-- ELO-axis pass: identical, but per_user_elo groups by (user_id, elo_bucket, cls)
-- and the final SELECT groups by (cls, elo_bucket) ORDER BY cls, elo_bucket.
```

## 3.4.2 Per-span Score Gap by Endgame Type (Phase 87.1 SEED-016)


Equal-footing opponent filter (`abs(opp_rating - user_rating) <= 100`) preserved per memory `feedback_260503-fef` (universal as of 2026-05-03).

```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
spans AS (
  -- One row per (game_id, endgame_class) span ≥6 plies, with entry eval at first ply.
  -- Matches the ≥6-ply gate from 3.4.1 / `query_endgame_entry_rows`.
  SELECT
    gp.game_id,
    gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN games g          ON g.id = gp.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE gp.endgame_class IS NOT NULL
    AND g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    -- Equal-footing filter (universal — see "Equal-footing opponent filter (all subchapters)")
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
  GROUP BY gp.game_id, gp.endgame_class
  HAVING count(gp.ply) >= 6
),
spans_with_next AS (
  -- LEAD() over (game_id ORDER BY span_min_ply) gives the next span's entry eval.
  -- NULL on the terminal span of each game; the gap_rows CTE falls back to game result.
  SELECT
    s.*,
    lead(s.entry_eval_cp)   OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_cp,
    lead(s.entry_eval_mate) OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_mate
  FROM spans s
),
gap_rows AS (
  -- Compute gap_span = exit_score - ES_entry per CONTEXT D-07.
  -- Uses the Lichess winning-chances sigmoid: 1 / (1 + exp(-0.00368208 * cp_signed)).
  SELECT
    g.user_id,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket,
    swn.endgame_class,
    (
      -- exit_score: transitory uses sigmoid on next-span entry eval; terminal uses game result.
      CASE
        WHEN next_eval_mate IS NOT NULL
          THEN CASE WHEN (next_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0 ELSE 0.0 END
        WHEN next_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 * (next_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE
          CASE
            WHEN (g.result='1-0' AND g.user_color='white')
              OR (g.result='0-1' AND g.user_color='black') THEN 1.0
            WHEN g.result='1/2-1/2' THEN 0.5
            ELSE 0.0
          END
      END
    )
    -
    (
      -- ES_entry: sigmoid on the span's entry eval (mate scores saturate to 0/1).
      CASE
        WHEN swn.entry_eval_mate IS NOT NULL
          THEN CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0 ELSE 0.0 END
        WHEN swn.entry_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 * (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS gap_span
  FROM spans_with_next swn
  JOIN games g          ON g.id = swn.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) >= 800  -- drop sub-800
),
per_user_class AS (
  SELECT
    user_id, elo_bucket, tc_bucket, endgame_class,
    avg(gap_span)   AS mean_gap,
    count(*)        AS n_spans
  FROM gap_rows
  WHERE gap_span IS NOT NULL
    AND elo_bucket IS NOT NULL
  GROUP BY user_id, elo_bucket, tc_bucket, endgame_class
  HAVING count(*) >= 20         -- §3.4.2 sample floor: ≥20 qualifying spans per user per class per cell
)
SELECT
  elo_bucket, tc_bucket,
  CASE endgame_class
    WHEN 1 THEN 'rook'
    WHEN 2 THEN 'minor_piece'
    WHEN 3 THEN 'pawn'
    WHEN 4 THEN 'queen'
    WHEN 5 THEN 'mixed'
    WHEN 6 THEN 'pawnless'
  END AS endgame_class,
  count(*) AS users,
  round(percentile_cont(0.25) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p25,
  round(percentile_cont(0.50) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p50,
  round(percentile_cont(0.75) WITHIN GROUP (ORDER BY mean_gap)::numeric, 4) AS p75,
  round(avg(mean_gap)::numeric, 4)     AS mean_x,
  round(var_samp(mean_gap)::numeric, 6) AS var_x
FROM per_user_class
GROUP BY elo_bucket, tc_bucket, endgame_class
ORDER BY endgame_class, elo_bucket, tc_bucket;
```

## 3.4.3 Endgame Type Score vs Score Gap — agreement / redundancy analysis


```sql
WITH selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,  -- LONGITUDINAL ONLY (ELO axis is game-time, per building block)
         bsu.median_elo
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON u.lichess_username = bsu.lichess_username
),
class_span AS (
  -- 3.4.1 / 3.4.2 shared gate: ≥6-ply per (game, class) span.
  SELECT game_id, endgame_class, min(ply) AS entry_ply
  FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id, endgame_class
  HAVING count(*) >= 6
),
per_user_class_score AS (
  -- Mirrors §3.4.1 per-user-per-class score CTE.
  SELECT
    g.user_id,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket,
    cs.endgame_class,
    count(*) AS n_games,
    avg(
      CASE
        WHEN (g.result='1-0' AND g.user_color='white')
          OR (g.result='0-1' AND g.user_color='black') THEN 1.0
        WHEN g.result='1/2-1/2' THEN 0.5
        ELSE 0.0
      END
    ) AS user_class_score
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN class_span cs     ON cs.game_id = g.id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
    AND (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) >= 800  -- drop sub-800 (game-time ELO)
  GROUP BY g.user_id, user_elo_at_game, elo_bucket, su.tc_bucket, cs.endgame_class
  HAVING count(*) >= 10
),
spans AS (
  -- Mirrors §3.4.2: one row per (game_id, endgame_class), ≥6 plies.
  SELECT
    gp.game_id,
    gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN games g           ON g.id = gp.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE gp.endgame_class IS NOT NULL
    AND g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND abs(
          (CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)
        - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)
        ) <= 100
  GROUP BY gp.game_id, gp.endgame_class
  HAVING count(gp.ply) >= 6
),
spans_with_next AS (
  SELECT
    s.*,
    lead(s.entry_eval_cp)   OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_cp,
    lead(s.entry_eval_mate) OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_mate
  FROM spans s
),
gap_rows AS (
  SELECT
    g.user_id,
    -- game-time ELO (canonical "user_elo_at_game / elo_bucket" building block)
    (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) AS user_elo_at_game,
    (CASE WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 800 THEN NULL
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1200 THEN 800
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 1600 THEN 1200
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2000 THEN 1600
          WHEN (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) < 2400 THEN 2000
          ELSE 2400 END) AS elo_bucket,
    su.tc_bucket,
    swn.endgame_class,
    (
      CASE
        WHEN next_eval_mate IS NOT NULL
          THEN CASE WHEN (next_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0 ELSE 0.0 END
        WHEN next_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 * (next_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE
          CASE
            WHEN (g.result='1-0' AND g.user_color='white')
              OR (g.result='0-1' AND g.user_color='black') THEN 1.0
            WHEN g.result='1/2-1/2' THEN 0.5
            ELSE 0.0
          END
      END
    )
    -
    (
      CASE
        WHEN swn.entry_eval_mate IS NOT NULL
          THEN CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0 ELSE 0.0 END
        WHEN swn.entry_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 * (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS gap_span
  FROM spans_with_next swn
  JOIN games g           ON g.id = swn.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) >= 800  -- drop sub-800
),
per_user_class_gap AS (
  SELECT
    user_id, elo_bucket, tc_bucket, endgame_class,
    avg(gap_span) AS user_class_mean_gap,
    count(*)      AS n_spans
  FROM gap_rows
  WHERE gap_span IS NOT NULL
    AND elo_bucket IS NOT NULL
  GROUP BY user_id, elo_bucket, tc_bucket, endgame_class
  HAVING count(*) >= 20
),
joined AS (
  -- Inner join: user contributes only when both metrics clear their floors,
  -- paired within the same game-time ELO bucket. Sparse cell (2400, classical) excluded.
  SELECT
    s.user_id, s.elo_bucket, s.tc_bucket, s.endgame_class,
    s.user_class_score AS score,
    g.user_class_mean_gap AS gap
  FROM per_user_class_score s
  JOIN per_user_class_gap g
    ON g.user_id = s.user_id
   AND g.elo_bucket = s.elo_bucket
   AND g.tc_bucket = s.tc_bucket
   AND g.endgame_class = s.endgame_class
  WHERE NOT (s.elo_bucket = 2400 AND s.tc_bucket = 'classical')
),
class_iqr AS (
  -- Per-class IQR-derived band edges. Drives zone classification below.
  SELECT
    endgame_class,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY score) AS score_p25,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY score) AS score_p75,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY gap)   AS gap_p25,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY gap)   AS gap_p75
  FROM joined
  GROUP BY endgame_class
),
classified AS (
  -- Per-class IQR zones: red = below p25, green = above p75, neutral otherwise.
  -- Lights-up rate is 50% per class per metric by construction (uninformative).
  SELECT
    j.user_id, j.elo_bucket, j.tc_bucket, j.endgame_class,
    j.score, j.gap,
    CASE
      WHEN j.score < ci.score_p25 THEN 'red'
      WHEN j.score > ci.score_p75 THEN 'green'
      ELSE 'neutral'
    END AS score_zone,
    CASE
      WHEN j.gap < ci.gap_p25 THEN 'red'
      WHEN j.gap > ci.gap_p75 THEN 'green'
      ELSE 'neutral'
    END AS gap_zone
  FROM joined j
  JOIN class_iqr ci ON ci.endgame_class = j.endgame_class
),
per_class_stats AS (
  SELECT
    CASE endgame_class
      WHEN 1 THEN 'rook'
      WHEN 2 THEN 'minor_piece'
      WHEN 3 THEN 'pawn'
      WHEN 4 THEN 'queen'
      WHEN 5 THEN 'mixed'
      WHEN 6 THEN 'pawnless'
    END AS endgame_class,
    count(*) AS n_users,
    round(corr(score, gap)::numeric, 3) AS pearson_r,
    round(avg(CASE WHEN sign(score - 0.5) = sign(gap) THEN 1.0 ELSE 0.0 END)::numeric, 3) AS sign_agreement,
    round(avg(CASE WHEN score_zone = gap_zone THEN 1.0 ELSE 0.0 END)::numeric, 3) AS zone_strict_agreement,
    round(avg(CASE WHEN (score_zone='red' AND gap_zone='green')
                     OR (score_zone='green' AND gap_zone='red')
                   THEN 1.0 ELSE 0.0 END)::numeric, 3) AS strong_disagreement,
    round(stddev_samp(score)::numeric, 4) AS score_stdev,
    round(stddev_samp(gap)::numeric,   4) AS gap_stdev
  FROM classified
  GROUP BY endgame_class
  HAVING count(*) >= 30
)
SELECT * FROM per_class_stats
ORDER BY endgame_class;
```

Also run the 3×3 zone-agreement matrix as a second query (one matrix per class):

```sql
-- Replace <CLASS_INT> with 1..6 and re-run; or wrap in a per-class loop.
WITH /* (paste CTEs above through `classified`) */
matrix AS (
  SELECT score_zone, gap_zone, count(*) AS users
  FROM classified
  WHERE endgame_class = <CLASS_INT>
  GROUP BY score_zone, gap_zone
)
SELECT score_zone, gap_zone, users,
       round(users::numeric / sum(users) OVER (), 3) AS frac
FROM matrix
ORDER BY score_zone, gap_zone;
```

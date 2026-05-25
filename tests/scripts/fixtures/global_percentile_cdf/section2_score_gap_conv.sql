WITH selected_users AS (
  SELECT u.id AS user_id
  FROM users u
  JOIN (
    SELECT lower(bsu.lichess_username) AS lname
    FROM benchmark_selected_users bsu
    JOIN benchmark_ingest_checkpoints bic
      ON bic.lichess_username = bsu.lichess_username
     AND bic.tc_bucket = bsu.tc_bucket
     AND bic.status = 'completed'
    GROUP BY lower(bsu.lichess_username)
    HAVING bool_or(NOT (bsu.rating_bucket = 2400 AND bsu.tc_bucket = 'classical'))
  ) deduped ON lower(u.lichess_username) = deduped.lname
),
recent_capped AS (
  SELECT g.id, g.user_id, g.user_color, g.result, g.played_at
  FROM (
    SELECT g.*,
           row_number() OVER (PARTITION BY g.user_id, g.time_control_bucket
                              ORDER BY g.played_at DESC) AS rn
    FROM games g
    JOIN selected_users su ON su.user_id = g.user_id
    WHERE g.rated AND NOT g.is_computer_game
      AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
      AND g.played_at >= DATE '2026-03-31' - INTERVAL '36 months'
      AND abs((CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)) <= 100
  ) g
  WHERE g.rn <= 1000
),
spans AS (
  SELECT
    gp.game_id, gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id, gp.endgame_class
  HAVING count(gp.ply) >= 6
),
spans_with_next AS (
  SELECT s.*,
         lead(s.entry_eval_cp)   OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_cp,
         lead(s.entry_eval_mate) OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_mate
  FROM spans s
),
gap_rows AS (
  SELECT
    g.user_id,
    CASE
      WHEN swn.entry_eval_mate IS NOT NULL THEN
        CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
          THEN 'conversion' ELSE 'recovery' END
      WHEN swn.entry_eval_cp IS NOT NULL THEN
        CASE
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100
            THEN 'conversion'
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) <= -100
            THEN 'recovery'
          ELSE 'parity'
        END
      ELSE 'parity'
    END AS bucket,
    (
      CASE
        WHEN swn.next_eval_mate IS NOT NULL
          THEN CASE WHEN (swn.next_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
                    THEN 1.0 ELSE 0.0 END
        WHEN swn.next_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 *
                 (swn.next_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE
          CASE
            WHEN (g.result='1-0' AND g.user_color='white')
              OR (g.result='0-1' AND g.user_color='black') THEN 1.0
            WHEN g.result='1/2-1/2' THEN 0.5
            ELSE 0.0
          END
      END
    ) - (
      CASE
        WHEN swn.entry_eval_mate IS NOT NULL
          THEN CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
                    THEN 1.0 ELSE 0.0 END
        WHEN swn.entry_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 *
                 (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS gap_span
  FROM spans_with_next swn
  JOIN games g ON g.id = swn.game_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) >= 800
),
per_user_bucket AS (
  SELECT user_id, bucket,
         avg(gap_span) AS mean_gap,
         count(*) AS span_n
  FROM gap_rows
  WHERE gap_span IS NOT NULL
  GROUP BY user_id, bucket
  HAVING count(*) >= 30
),
per_user_values AS (
  SELECT
    mean_gap AS metric_value,
    span_n AS n_games
  FROM per_user_bucket
  WHERE bucket = 'conversion'
)
SELECT
  percentile_cont(ARRAY[0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29, 0.30, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39, 0.40, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49, 0.50, 0.51, 0.52, 0.53, 0.54, 0.55, 0.56, 0.57, 0.58, 0.59, 0.60, 0.61, 0.62, 0.63, 0.64, 0.65, 0.66, 0.67, 0.68, 0.69, 0.70, 0.71, 0.72, 0.73, 0.74, 0.75, 0.76, 0.77, 0.78, 0.79, 0.80, 0.81, 0.82, 0.83, 0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.90, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]::double precision[]) WITHIN GROUP (ORDER BY metric_value) AS breakpoints,
  count(*) AS n_users
FROM per_user_values

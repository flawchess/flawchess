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
           row_number() OVER (PARTITION BY g.user_id
                              ORDER BY g.played_at DESC) AS rn
    FROM games g
    JOIN selected_users su ON su.user_id = g.user_id
    WHERE g.rated AND NOT g.is_computer_game
      AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
      AND g.played_at >= DATE '2026-05-26' - INTERVAL '36 months'
      AND abs((CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)) <= 100
      AND g.time_control_bucket = 'blitz'
  ) g
  WHERE g.rn <= 3000
),
spans AS (
  SELECT gp.game_id,
         (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
         (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id
  HAVING count(gp.ply) >= 6
),
bucket_rows AS (
  SELECT g.user_id,
    CASE
      WHEN (s.entry_eval_mate IS NOT NULL
            AND (s.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0)
        OR (s.entry_eval_cp IS NOT NULL
            AND (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100)
      THEN true ELSE false
    END AS is_conversion,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white') OR (g.result='0-1' AND g.user_color='black')
      THEN 1 ELSE 0
    END AS is_win
  FROM spans s
  JOIN games g ON g.id = s.game_id
  WHERE (s.entry_eval_cp IS NOT NULL OR s.entry_eval_mate IS NOT NULL)
    AND (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) >= 800
),
per_user AS (
  SELECT user_id,
    count(*) FILTER (WHERE is_conversion) AS conv_n,
    sum(is_win) FILTER (WHERE is_conversion)::float AS conv_wins
  FROM bucket_rows
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE is_conversion) >= 30
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT user_id,
    conv_wins / NULLIF(conv_n, 0) AS metric_value,
    conv_n::int AS n_games
  FROM per_user
  WHERE conv_wins IS NOT NULL
),
recent_capped_anchor AS (
  SELECT g.id, g.user_id, g.user_color, g.result, g.played_at
  FROM (
    SELECT g.*,
           row_number() OVER (PARTITION BY g.user_id
                              ORDER BY g.played_at DESC) AS rn
    FROM games g
    JOIN selected_users su ON su.user_id = g.user_id
    WHERE g.rated AND NOT g.is_computer_game
      AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
      AND g.played_at >= DATE '2026-05-26' - INTERVAL '36 months'
      AND abs((CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END) - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)) <= 100
      AND g.time_control_bucket = 'blitz'
  ) g
  WHERE g.rn <= 3000
),
recent_capped_anchor_no_daily AS (
  SELECT rc.*
  FROM recent_capped_anchor rc
  JOIN games g ON g.id = rc.id
  WHERE NOT (g.platform = 'chess.com' AND g.time_control_str LIKE '1/%')
    
),
per_user_anchor AS (
  SELECT
    rc.user_id,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END))::int AS anchor_rating,
    count(*) AS n_games
  FROM recent_capped_anchor_no_daily rc
  JOIN games g ON g.id = rc.id
  GROUP BY rc.user_id
  HAVING count(*) >= 30
)
SELECT
  puv.user_id,
  puv.metric_value,
  puv.n_games,
  pua.anchor_rating
FROM per_user_values puv
JOIN per_user_anchor pua USING (user_id)

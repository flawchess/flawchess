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
      AND g.time_control_bucket = 'rapid'
  ) g
  WHERE g.rn <= 3000
),
opening_out_mg_entry AS (
  SELECT DISTINCT ON (gp.game_id) gp.game_id, gp.eval_cp, gp.eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id AND gp.user_id = rc.user_id
  WHERE gp.phase = 1
  ORDER BY gp.game_id, gp.ply
),
opening_out_classified AS (
  SELECT rc.id AS game_id, rc.user_id, rc.user_color::text AS user_color,
    CASE
      WHEN me.game_id IS NULL THEN
        CASE
          WHEN g.termination IN ('resignation', 'checkmate', 'timeout') AND g.result <> '1/2-1/2'
          THEN CASE WHEN (g.result = '1-0') = (rc.user_color = 'white') THEN 1 ELSE -1 END
        END
      WHEN me.eval_mate IS NOT NULL THEN sign(me.eval_mate)::int * (CASE WHEN rc.user_color = 'white' THEN 1 ELSE -1 END)
      WHEN me.eval_cp IS NOT NULL THEN
        CASE
          WHEN (me.eval_cp * (CASE WHEN rc.user_color = 'white' THEN 1 ELSE -1 END) - (CASE WHEN rc.user_color = 'white' THEN (25) ELSE (-25) END)) <= -100 THEN -1
          WHEN (me.eval_cp * (CASE WHEN rc.user_color = 'white' THEN 1 ELSE -1 END) - (CASE WHEN rc.user_color = 'white' THEN (25) ELSE (-25) END)) >= 100 THEN 1
          ELSE 0
        END
    END AS side
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  LEFT JOIN opening_out_mg_entry me ON me.game_id = rc.id
  WHERE (CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END) >= 800
),
per_user_color_counts AS (
  SELECT user_id, user_color,
    count(side)::int AS n_games,
    (count(*) FILTER (WHERE side = -1))::int AS worse_n,
    (count(*) FILTER (WHERE side = 1))::int AS better_n
  FROM opening_out_classified
  GROUP BY user_id, user_color
),
per_user_values AS (
  SELECT user_id, user_color,
    worse_n::float / n_games AS metric_value,
    n_games
  FROM per_user_color_counts
  WHERE n_games >= 30
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
      AND g.time_control_bucket = 'rapid'
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
  puv.user_color,
  puv.metric_value,
  puv.n_games,
  pua.anchor_rating
FROM per_user_values puv
JOIN per_user_anchor pua USING (user_id)

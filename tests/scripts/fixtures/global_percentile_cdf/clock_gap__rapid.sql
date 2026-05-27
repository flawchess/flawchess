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
endgame_entry_clocks AS (
  SELECT
    gp.game_id,
    (array_agg(gp.clock_seconds ORDER BY gp.ply ASC)
       FILTER (WHERE gp.clock_seconds IS NOT NULL AND gp.ply % 2 = 0))[1] AS white_entry_clock,
    (array_agg(gp.clock_seconds ORDER BY gp.ply ASC)
       FILTER (WHERE gp.clock_seconds IS NOT NULL AND gp.ply % 2 = 1))[1] AS black_entry_clock
  FROM game_positions gp
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id
  HAVING count(gp.ply) >= 6
),
joined AS (
  SELECT
    rc.user_id,
    (
      (CASE WHEN rc.user_color = 'white' THEN ee.white_entry_clock
            ELSE ee.black_entry_clock END)
      - (CASE WHEN rc.user_color = 'white' THEN ee.black_entry_clock
              ELSE ee.white_entry_clock END)
    )::float / NULLIF(g.base_time_seconds, 0) AS clock_gap_frac
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  JOIN endgame_entry_clocks ee ON ee.game_id = rc.id
  WHERE g.base_time_seconds IS NOT NULL AND g.base_time_seconds > 0
    AND ee.white_entry_clock IS NOT NULL
    AND ee.black_entry_clock IS NOT NULL
),
per_user AS (
  SELECT
    user_id,
    avg(clock_gap_frac) AS clock_gap_frac_avg,
    count(*) AS pool_n
  FROM joined
  WHERE clock_gap_frac IS NOT NULL
  GROUP BY user_id
  HAVING count(*) >= 30
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    clock_gap_frac_avg AS metric_value,
    pool_n AS n_games
  FROM per_user
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
  puv.metric_value,
  puv.n_games,
  pua.anchor_rating
FROM per_user_values puv
JOIN per_user_anchor pua USING (user_id)

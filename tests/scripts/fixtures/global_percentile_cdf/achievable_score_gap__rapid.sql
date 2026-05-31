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
endgame_game_ids AS (
  -- Scoped to recent_capped (result-equivalent): only recent_capped games survive the
  -- downstream scored JOIN (via entry_rows JOIN endgame_game_ids then rc.id = rc.id).
  -- entry_rows inherits the scoping automatically via its JOIN on endgame_game_ids.
  -- HAVING count(*) >= 6 counts rows within each retained game; membership filtering
  -- does not alter the per-game count or the retained game set.
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL AND game_id IN (SELECT id FROM recent_capped)
  GROUP BY game_id HAVING count(*) >= 6
),
entry_rows AS (
  SELECT gp.game_id, gp.eval_cp, gp.eval_mate,
         ROW_NUMBER() OVER (PARTITION BY gp.game_id ORDER BY gp.ply ASC) AS rn
  FROM game_positions gp
  JOIN endgame_game_ids eg ON eg.game_id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
),
scored AS (
  SELECT
    rc.user_id,
    (
      CASE
        WHEN (rc.result = '1-0' AND rc.user_color = 'white')
          OR (rc.result = '0-1' AND rc.user_color = 'black') THEN 1.0
        WHEN rc.result = '1/2-1/2' THEN 0.5
        ELSE 0.0
      END
      -
      CASE
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END)) < 0 THEN 0.0
        WHEN er.eval_cp IS NOT NULL AND abs(er.eval_cp) < 2000
             THEN 1.0 / (1.0 + exp(-0.00368208 *
                  (er.eval_cp * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS d_i
  FROM recent_capped rc
  JOIN entry_rows er ON er.game_id = rc.id AND er.rn = 1
),
per_user AS (
  SELECT
    user_id,
    avg(d_i) AS achievable_gap,
    count(*) FILTER (WHERE d_i IS NOT NULL) AS di_n
  FROM scored
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= 30
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    achievable_gap AS metric_value,
    di_n AS n_games
  FROM per_user
  WHERE achievable_gap IS NOT NULL
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

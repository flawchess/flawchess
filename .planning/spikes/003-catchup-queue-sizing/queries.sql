-- Spike 003: tier-2 catch-up queue sizing (run via flawchess-prod-db, read-only).
-- "Lacks eval" proxy = white_blunders IS NULL AND black_blunders IS NULL
-- (the Q-007-validated summary-column proxy, inverted).
-- Evaluated plies per game = ply_count - 14 (book-skip approximation).

-- Activity windows (note: users.last_activity was backfilled ~2026-03-22,
-- so windows >= ~80 days include everyone and are meaningless).
SELECT
  COUNT(*) FILTER (WHERE last_activity >= now() - interval '30 days') AS active_30d,
  COUNT(*) FILTER (WHERE last_activity >= now() - interval '60 days') AS active_60d,
  COUNT(*) AS total_users
FROM users;

-- Tier-2 queue size per window (w100/w200/w500), split 30d-active vs 31-60d.
WITH ranked AS (
  SELECT g.user_id,
         COALESCE(g.ply_count, 60) AS plies,
         (g.white_blunders IS NULL AND g.black_blunders IS NULL) AS lacks_eval,
         ROW_NUMBER() OVER (PARTITION BY g.user_id ORDER BY g.played_at DESC NULLS LAST) AS rn,
         (u.last_activity >= now() - interval '30 days') AS active30
  FROM games g
  JOIN users u ON u.id = g.user_id
  WHERE u.last_activity >= now() - interval '60 days'
)
SELECT
  active30,
  COUNT(DISTINCT user_id) AS users,
  COUNT(*) FILTER (WHERE rn <= 100 AND lacks_eval) AS games_w100,
  SUM(GREATEST(plies - 14, 0)) FILTER (WHERE rn <= 100 AND lacks_eval) AS eval_plies_w100,
  COUNT(*) FILTER (WHERE rn <= 200 AND lacks_eval) AS games_w200,
  SUM(GREATEST(plies - 14, 0)) FILTER (WHERE rn <= 200 AND lacks_eval) AS eval_plies_w200,
  COUNT(*) FILTER (WHERE rn <= 500 AND lacks_eval) AS games_w500,
  SUM(GREATEST(plies - 14, 0)) FILTER (WHERE rn <= 500 AND lacks_eval) AS eval_plies_w500,
  COUNT(*) FILTER (WHERE lacks_eval) AS games_all,
  SUM(GREATEST(plies - 14, 0)) FILTER (WHERE lacks_eval) AS eval_plies_all
FROM ranked
GROUP BY active30
ORDER BY active30 DESC;

-- Tier-3 ceiling: entire prod DB.
SELECT COUNT(*) AS total_games,
       COUNT(*) FILTER (WHERE white_blunders IS NULL AND black_blunders IS NULL) AS games_lacking,
       SUM(GREATEST(COALESCE(ply_count,60) - 14, 0))
         FILTER (WHERE white_blunders IS NULL AND black_blunders IS NULL) AS eval_plies_lacking
FROM games;

-- 261121-ha7: prod per-user x TC paired facepalm deltas -> per-TC quartiles.
-- First run 2026-11-21 on the Phase 257 model; re-run 2026-11-22 on the Phase 259 model (this file).
-- Run via the flawchess-prod-db MCP (read-only).
-- The score and type expressions are facepalm_expr(FACEPALM_LIBRARY_LAMBDA) / facepalm_type_expr()
-- compiled with literal binds from app/services/facepalm_score.py (game_flaws. -> f.), unedited.
-- Regenerate them if FACEPALM_MODEL is refit or the stored material rule changes.
WITH win AS (
  SELECT g.id, g.user_id, g.user_color, g.time_control_bucket AS tc, g.ply_count, g.full_evals_completed_at,
         row_number() OVER (PARTITION BY g.user_id, g.time_control_bucket ORDER BY g.played_at DESC) rn
  FROM games g JOIN users u ON u.id = g.user_id
  WHERE NOT u.is_guest AND NOT g.is_computer_game AND g.platform IN ('chess.com','lichess')
    AND g.time_control_bucket IS NOT NULL AND g.played_at >= NOW() - INTERVAL '36 months'),
anchor AS (
  SELECT id AS game_id, user_id, user_color, tc,
         CASE WHEN user_color = 'white' THEN ceil(ply_count/2.0) ELSE floor(ply_count/2.0) END AS user_moves
  FROM win WHERE rn <= 1000 AND full_evals_completed_at IS NOT NULL AND ply_count > 0),
scored AS (
  SELECT f.game_id, f.ply,
    1.0 / CAST((1.0 + exp(-(-1.4308 + -0.6065 * ln(f.maia_played_prob + 0.01) + 0.8379 * f.material_loss + CASE WHEN (f.maia_played_prob IS NULL OR f.material_loss IS NULL) THEN NULL WHEN (f.material_loss > 0) THEN CASE WHEN (f.maia_best_reply_prob IS NULL) THEN NULL ELSE 0.9133 * ln(f.maia_best_reply_prob + 0.01) END ELSE CASE WHEN (f.maia_best_prob IS NULL) THEN NULL ELSE 2.0786 * ln(f.maia_best_prob + 0.01) END END + 0.4971 * f.material_missed))) AS FLOAT) AS s,
    CASE WHEN (f.material_loss IS NULL) THEN NULL WHEN (f.material_loss > 0 AND f.material_loss >= coalesce(f.material_missed, 0.0)) THEN 'allowed_loss' ELSE 'missed_win' END AS ftype
  FROM game_flaws f JOIN anchor a ON a.game_id = f.game_id AND a.user_id = f.user_id
  WHERE f.severity = 2),
per_game AS (
  SELECT a.user_id, a.tc, a.user_moves,
    count(sc.ply) FILTER (WHERE (sc.ply % 2 = 0) = (a.user_color='white')) p_bl,
    count(sc.s) FILTER (WHERE (sc.ply % 2 = 0) = (a.user_color='white')) p_sc,
    count(sc.ply) FILTER (WHERE (sc.ply % 2 = 0) <> (a.user_color='white')) o_bl,
    count(sc.s) FILTER (WHERE (sc.ply % 2 = 0) <> (a.user_color='white')) o_sc,
    count(*) FILTER (WHERE sc.s >= 0.7 AND (sc.ply % 2 = 0) = (a.user_color='white')) p_fp,
    count(*) FILTER (WHERE sc.s >= 0.7 AND (sc.ply % 2 = 0) <> (a.user_color='white')) o_fp,
    count(*) FILTER (WHERE sc.s >= 0.7 AND sc.ftype='missed_win' AND (sc.ply % 2 = 0) = (a.user_color='white')) p_mw,
    count(*) FILTER (WHERE sc.s >= 0.7 AND sc.ftype='missed_win' AND (sc.ply % 2 = 0) <> (a.user_color='white')) o_mw,
    count(*) FILTER (WHERE sc.s >= 0.7 AND sc.ftype='allowed_loss' AND (sc.ply % 2 = 0) = (a.user_color='white')) p_al,
    count(*) FILTER (WHERE sc.s >= 0.7 AND sc.ftype='allowed_loss' AND (sc.ply % 2 = 0) <> (a.user_color='white')) o_al
  FROM anchor a LEFT JOIN scored sc ON sc.game_id = a.game_id
  WHERE a.user_moves > 0
  GROUP BY a.game_id, a.user_id, a.tc, a.user_moves, a.user_color),
per_user AS (
  SELECT user_id, tc, count(*) n_games, sum(p_bl) p_bl, sum(p_sc) p_sc, sum(o_bl) o_bl, sum(o_sc) o_sc,
    avg((p_fp - o_fp) * 100.0 / user_moves) d_fp, avg((p_mw - o_mw) * 100.0 / user_moves) d_mw,
    avg((p_al - o_al) * 100.0 / user_moves) d_al, avg(p_fp * 100.0 / user_moves) r_fp
  FROM per_game GROUP BY user_id, tc)
SELECT tc, count(*) n_users, sum(n_games) n_games,
  percentile_cont(ARRAY[0.25,0.5,0.75]) WITHIN GROUP (ORDER BY d_fp) d_fp,
  percentile_cont(ARRAY[0.25,0.5,0.75]) WITHIN GROUP (ORDER BY d_mw) d_mw,
  percentile_cont(ARRAY[0.25,0.5,0.75]) WITHIN GROUP (ORDER BY d_al) d_al,
  percentile_cont(ARRAY[0.25,0.5,0.75]) WITHIN GROUP (ORDER BY r_fp) r_fp
FROM per_user
WHERE n_games >= 20 AND (p_bl = 0 OR p_sc::float / p_bl >= 0.8) AND (o_bl = 0 OR o_sc::float / o_bl >= 0.8)
GROUP BY tc ORDER BY tc

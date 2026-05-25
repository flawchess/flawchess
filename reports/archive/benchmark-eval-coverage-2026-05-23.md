# Benchmark DB — Stockfish Eval Coverage per Cell

**Date:** 2026-05-23
**Database:** benchmark (read-only via MCP)
**Question:** what percentage of cohort games have **full** Stockfish eval coverage (every mid-game position carries `eval_cp` or `eval_mate`), broken down by ELO bucket × TC bucket?

Full coverage here means **lichess provided evals at import time** (the player had local analysis on, or it was a broadcast/study). It is *not* the backfilled `evals_completed_at` flag — that one only marks games where we computed phase-transition evals, not full per-ply coverage.

## Result

| ELO ↓ / TC → | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800**  | 9.24% (2,438 / 26,376)    | 10.46% (2,738 / 26,176)   | 8.17% (1,870 / 22,900)    | 10.06% (279 / 2,774)     |
| **1200** | 7.83% (7,302 / 93,297)    | 10.74% (7,686 / 71,548)   | 12.85% (9,079 / 70,650)   | 15.99% (4,100 / 25,640)  |
| **1600** | 5.49% (4,986 / 90,891)    | 9.89% (11,252 / 113,724)  | 15.20% (12,147 / 79,890)  | 34.56% (14,501 / 41,954) |
| **2000** | 4.80% (4,748 / 98,922)    | 12.33% (12,049 / 97,700)  | 27.87% (25,985 / 93,246)  | **50.66%** (15,264 / 30,131) |
| **2400** | 6.11% (6,248 / 102,224)   | **34.62%** (31,412 / 90,722) | **52.24%** (30,272 / 57,951) | **52.29%** (2,020 / 3,863) |

Across the full cohort: **~228k of ~1.24M games (~17%)** have full mid-game eval coverage.

## Patterns

- **Bullet stays low everywhere** (4.8–9.2%). Analysis is rarely enabled for 1-minute games, and lichess's eval pipeline frequently skips them. Even at 2400 only 6.1% — the ELO gradient that holds for slower TCs doesn't apply to bullet.
- **Rapid + classical at 2000–2400 cross 50%** — these are the cells where lichess-provided evals could realistically be used as a primary signal.
- **Strong ELO gradient at slower TCs**: classical jumps 10% → 16% → 35% → 51% → 52% from 800 to 2400; rapid 8% → 13% → 15% → 28% → 52%.
- **Classical 2400 is a small cell** (3,863 games) so its 52.29% is noisy.

## Method

### Cohort

Games joined to `benchmark_ingest_checkpoints` with `status='completed'` — excludes failed, in-progress, and skipped imports. This matches the cohort definition used by the benchmarks skill (`reports/benchmarks-latest.md`).

### Cells

- **ELO bucket**: 400-wide, anchored at 800/1200/1600/2000/2400, computed from the **cohort user's rating at game time** (`games.white_rating` if `user_color='white'`, otherwise `games.black_rating`). The frozen selection-snapshot rating in `benchmark_selected_users` is deliberately *not* used (see the "Rating-lag selection bias" note in chapter 1 of the benchmarks report).
- **TC bucket**: `games.time_control_bucket` (bullet / blitz / rapid / classical).

### "Full coverage" definition

For each game, count positions in `game_positions` where `0 < ply < max(ply)` (i.e. excluding the starting position and the terminal position — neither ever has an eval since one is pre-move and the other is the game-ending state). The game has full coverage iff **every** such position has `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`.

### SQL

```sql
WITH cohort_games AS (
  SELECT
    g.id,
    g.time_control_bucket::text AS tc_bucket,
    CASE WHEN g.user_color = 'white' THEN g.white_rating ELSE g.black_rating END AS user_rating_at_game
  FROM games g
  JOIN users u ON u.id = g.user_id
  JOIN benchmark_ingest_checkpoints c
    ON c.benchmark_user_id = u.id
   AND c.tc_bucket::text = g.time_control_bucket::text
   AND c.status = 'completed'
),
bucketed AS (
  SELECT
    CASE
      WHEN user_rating_at_game BETWEEN  600 AND  999 THEN  800
      WHEN user_rating_at_game BETWEEN 1000 AND 1399 THEN 1200
      WHEN user_rating_at_game BETWEEN 1400 AND 1799 THEN 1600
      WHEN user_rating_at_game BETWEEN 1800 AND 2199 THEN 2000
      WHEN user_rating_at_game BETWEEN 2200 AND 2599 THEN 2400
    END AS elo_bucket,
    id, tc_bucket
  FROM cohort_games
),
ply_bounds AS (
  SELECT game_id, MIN(ply) AS min_ply, MAX(ply) AS max_ply
  FROM game_positions
  GROUP BY game_id
),
pos_coverage AS (
  SELECT
    p.game_id,
    COUNT(*) AS positions,
    COUNT(*) FILTER (WHERE p.eval_cp IS NOT NULL OR p.eval_mate IS NOT NULL) AS evaled
  FROM game_positions p
  JOIN ply_bounds b ON b.game_id = p.game_id
  WHERE p.ply > 0 AND p.ply < b.max_ply
  GROUP BY p.game_id
)
SELECT
  b.elo_bucket,
  b.tc_bucket,
  COUNT(*) AS total_games,
  COUNT(*) FILTER (WHERE p.positions IS NOT NULL AND p.positions = p.evaled) AS fully_evaled_games,
  ROUND(100.0 * COUNT(*) FILTER (WHERE p.positions IS NOT NULL AND p.positions = p.evaled) / NULLIF(COUNT(*),0), 2) AS pct_full_coverage
FROM bucketed b
LEFT JOIN pos_coverage p ON p.game_id = b.id
WHERE b.elo_bucket IS NOT NULL
GROUP BY b.elo_bucket, b.tc_bucket
ORDER BY b.elo_bucket, b.tc_bucket;
```

## Caveats

- A game with all-but-one positions evaled is counted as **not** fully covered. This is the strict definition; partial coverage (e.g. ≥95%) was not measured here.
- The terminal-ply exclusion assumes the final stored position is the game-ending one (mate / stalemate / resignation / flag-fall / draw agreement). Games where lichess returned an eval on the terminal ply anyway (rare) are still counted correctly because the terminal ply is dropped from the denominator.
- Classical 2400 cell has only 3,863 games — treat its percentage as noisy.

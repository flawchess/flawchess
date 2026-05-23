# Benchmark DB — Eval/Outcome Consistency per ELO Bucket

**Date:** 2026-05-23
**Database:** benchmark (read-only via MCP)
**Scope:** blitz, rapid, classical (bullet excluded). Cohort = games joined to `benchmark_ingest_checkpoints` with `status='completed'`.

Two questions, both conditioned on the eval trajectory of the mid-game/endgame (phase > 0, full lichess-provided eval coverage):

1. **Conversion of a sustained advantage.** Among games where one side had `|eval_cp| >= 200` on every phase>0 ply with the same sign throughout (a sustained ≥2-pawn lead), how often does the leader actually win?
2. **Outcome of a quiet game.** Among games where `|eval_cp| <= 50` on every phase>0 ply (eval pinned within half a pawn), how often is the result a draw?

Both questions condition on **full eval coverage** on every mid-game ply (excluding ply 0 and the terminal ply). Games without full coverage are excluded.

---

## Section 1 — Conversion of a sustained ≥200 cp advantage

Among games where the eval stayed at ≥2 pawns for the leader on every phase>0 ply, the result distribution per ELO bucket:

| ELO bucket | sustained-lead games | **leader wins** | draws | **leader loses** |
|------------|---------------------:|----------------:|------:|-----------------:|
| **800**   | 1,482 | **89.81%** | 0.27% | **9.92%** |
| **1200**  | 4,907 | **95.21%** | 0.57% | **4.22%** |
| **1600**  | 5,708 | **96.60%** | 0.46% | **2.94%** |
| **2000**  | 4,610 | **98.70%** | 0.22% | **1.08%** |
| **2400**  | 3,258 | **98.43%** | 0.28% | **1.29%** |

### Per-TC breakdown — % leader loses

| ELO ↓ / TC → | blitz   | rapid   | classical |
|---|---:|---:|---:|
| **800**  | 11.65% |  8.52% |  5.21% |
| **1200** |  6.00% |  2.85% |  4.30% |
| **1600** |  3.60% |  1.97% |  3.32% |
| **2000** |  1.31% |  0.96% |  1.11% |
| **2400** |  1.64% |  1.05% |  0.58% |

### Patterns

- **Conversion of a sustained lead rises sharply with ELO**: 800 leaders blow a sustained winning advantage **9.9%** of the time vs **1.1%** at 2000+. Even a +2 pawn lead held through the whole mid-game/endgame is not safe at 800 level.
- **The 2000 → 2400 jump is flat** — once players reach master-class technique, holding a sustained advantage is essentially automatic (~1.1–1.3% loss rate).
- **Slow time controls help convert at low ELO**: 800 classical loses 5.2% vs 800 blitz 11.7%. Extra thinking time substantially reduces the giveaway rate at the bottom of the ladder. At 2000+ the TC effect is small because conversion is already near-ceiling.
- **Draws are negligible** (~0.2–0.6%) — when one side has a sustained +2 pawn lead in eval terms, the game basically resolves win-or-loss; perpetual / fortress / stalemate draws from a winning position are rare.
- **2400 classical** (n=173) and **800 classical** (n=96) are small cells — treat their TC-level percentages as noisy.

---

## Section 2 — Outcome of games with eval pinned to ±50 throughout

Among games where eval stayed within ±50 cp on every phase>0 ply (no side ever had more than a half-pawn edge), the result distribution per ELO bucket:

| ELO bucket | quiet games | **draws** | decisive |
|------------|------------:|----------:|---------:|
| **800**   |  25 |  **4.00%** | 96.00% |
| **1200**  |  73 |  **1.37%** | 98.63% |
| **1600**  | 143 | **16.78%** | 83.22% |
| **2000**  | 215 | **49.77%** | 50.23% |
| **2400**  | 348 | **76.44%** | 23.56% |

### Patterns

- **A "quiet" game is not a drawn game at low ELO.** At 800 / 1200 the result is decisive ~97–99% of the time — even when the eval never leaves ±50 in the mid-game, the game ends with someone winning. Termination breakdown explains why: **~70% of these are resignations** of a balanced position (17/25 at 800, 47/73 at 1200), with the rest split between abandonments (disconnects, counted as losses by lichess) and flag-fall. Low-ELO players resign positions they shouldn't.
- **Draw rate climbs steeply with ELO**: 4% → 1% → 17% → 50% → 76%. By 1600, explicit "draw" terminations appear in volume (22 games); by 2400 they dominate.
- **Quiet games are still rare overall** — only 804 games across 829k full-coverage cohort games (~0.10%). A whole game inside ±50 cp is unusual at every level, especially at low ELO where evals swing wildly.
- **The 800/1200 cells are still small** (25 and 73 games). The ~97–99% decisive rate is directionally robust (two thresholds, ±30 and ±50, both yield the same finding) but the exact value is noisy.

---

## Method

### Cohort

Games joined to `benchmark_ingest_checkpoints` with `status='completed'`. Time controls restricted to blitz, rapid, classical (bullet excluded).

### ELO bucket

400-wide, anchored at 800/1200/1600/2000/2400, computed from the cohort user's **rating at game time** (`games.white_rating` if `user_color='white'`, else `games.black_rating`). Frozen selection-snapshot rating is not used.

### Ply window

For each game, look at positions where `phase > 0` (mid-game / endgame; opening phase=0 excluded), `ply > 0` (start position skipped), and `ply < max(ply)` (terminal position skipped — checkmate/stalemate/resign/flag-fall positions never carry an eval).

### Full coverage gate

A game is eligible only if **every** position in the ply window has `eval_cp` or `eval_mate` set. Games without full coverage are excluded entirely.

### Section 1 — sustained-lead condition

Among full-coverage games, keep games where:
- `min(|eval|) >= 200` across the ply window (every ply was ≥2 pawns).
- `min(sign(eval)) = max(sign(eval))` and nonzero (the same side led throughout — no sign-flip).

Then classify outcome relative to the leading side:
- `leader_wins` — leader sign is positive and `result = '1-0'`, or leader sign is negative and `result = '0-1'`.
- `leader_loses` — opposite.
- `draws` — `result = '1/2-1/2'`.

### Section 2 — quiet condition

Among full-coverage games, keep games where `max(|eval|) <= 50` across the ply window. Positions with `eval_mate` set are treated as `|eval| = 10000` and thus disqualify the game (no mate distance can sit inside ±50 cp).

Then classify by result: `1/2-1/2` vs decisive.

### Mate handling (Section 1)

Positions with `eval_mate` set are treated as `|eval| = 10000` with sign matching `eval_mate`. So mate-in-N counts toward the leader's sustained advantage and trivially passes the ≥200 threshold.

### SQL

```sql
WITH cohort_games AS (
  SELECT g.id, g.result,
         g.time_control_bucket::text AS tc_bucket,
         CASE WHEN g.user_color = 'white' THEN g.white_rating ELSE g.black_rating END AS user_rating_at_game
  FROM games g
  JOIN users u ON u.id = g.user_id
  JOIN benchmark_ingest_checkpoints c
    ON c.benchmark_user_id = u.id
   AND c.tc_bucket::text = g.time_control_bucket::text
   AND c.status = 'completed'
  WHERE g.time_control_bucket::text IN ('blitz', 'rapid', 'classical')
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
    id, tc_bucket, result
  FROM cohort_games
),
ply_bounds AS (
  SELECT game_id, MAX(ply) AS max_ply FROM game_positions GROUP BY game_id
),
phase_gt0_agg AS (
  SELECT
    p.game_id,
    COUNT(*) AS positions,
    COUNT(*) FILTER (WHERE p.eval_cp IS NOT NULL OR p.eval_mate IS NOT NULL) AS evaled,
    MIN(CASE WHEN p.eval_cp IS NOT NULL THEN abs(p.eval_cp)
             WHEN p.eval_mate IS NOT NULL THEN 10000 END) AS min_abs_eval,
    MAX(CASE WHEN p.eval_cp IS NOT NULL THEN abs(p.eval_cp)
             WHEN p.eval_mate IS NOT NULL THEN 10000 END) AS max_abs_eval,
    MIN(CASE WHEN p.eval_cp IS NOT NULL THEN sign(p.eval_cp)
             WHEN p.eval_mate IS NOT NULL THEN sign(p.eval_mate) END) AS min_sign,
    MAX(CASE WHEN p.eval_cp IS NOT NULL THEN sign(p.eval_cp)
             WHEN p.eval_mate IS NOT NULL THEN sign(p.eval_mate) END) AS max_sign
  FROM game_positions p
  JOIN ply_bounds pb ON pb.game_id = p.game_id
  WHERE p.phase > 0 AND p.ply > 0 AND p.ply < pb.max_ply
  GROUP BY p.game_id
)
-- Section 1
SELECT b.elo_bucket,
  COUNT(*) AS sustained_lead_games,
  COUNT(*) FILTER (WHERE (a.min_sign > 0 AND b.result='1-0') OR (a.min_sign < 0 AND b.result='0-1')) AS leader_wins,
  COUNT(*) FILTER (WHERE b.result='1/2-1/2') AS draws,
  COUNT(*) FILTER (WHERE (a.min_sign > 0 AND b.result='0-1') OR (a.min_sign < 0 AND b.result='1-0')) AS leader_loses
FROM bucketed b
JOIN phase_gt0_agg a ON a.game_id = b.id
WHERE b.elo_bucket IS NOT NULL
  AND a.positions = a.evaled
  AND a.min_abs_eval >= 200
  AND a.min_sign = a.max_sign AND a.min_sign <> 0
GROUP BY b.elo_bucket ORDER BY b.elo_bucket;

-- Section 2
SELECT b.elo_bucket,
  COUNT(*) AS quiet_games,
  COUNT(*) FILTER (WHERE b.result = '1/2-1/2') AS draws,
  COUNT(*) FILTER (WHERE b.result <> '1/2-1/2') AS decisive
FROM bucketed b
JOIN phase_gt0_agg a ON a.game_id = b.id
WHERE b.elo_bucket IS NOT NULL
  AND a.positions = a.evaled
  AND a.max_abs_eval <= 50
GROUP BY b.elo_bucket ORDER BY b.elo_bucket;
```

## Caveats

- The thresholds (≥200 and ≤50 cp) are strict per-ply. A single transient spike disqualifies a game. Loosening to "≥95% of plies meet the threshold" would broaden the sample but wasn't measured here.
- Eval coverage varies sharply across cells (see `benchmark-eval-coverage-2026-05-23.md`); the conditional denominators reflect only games with full lichess-provided evals, which skew toward longer time controls and higher ratings.
- The terminal ply is excluded from the ply window because it doesn't reliably carry an eval. This doesn't drive the Section 2 "100% decisive at 800/1200" finding — the dominant cause there is resignation of balanced positions, which is captured by the recorded result rather than by any eval on the terminal move.
- Small-cell warnings: Section 2 at 800 (n=25) and 1200 (n=73); Section 1 at 2400 classical (n=173) and 800 classical (n=96).

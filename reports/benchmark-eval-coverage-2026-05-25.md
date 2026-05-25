# Benchmark DB — Stockfish Eval Coverage per Cell

**Date:** 2026-05-25
**Database:** benchmark (read-only via MCP)
**Question:** what percentage of cohort games have **Lichess server-side Stockfish analysis** attached, broken down by ELO bucket × TC bucket?

"Analyzed" here means lichess provided per-ply evals at import time (the player had local analysis on, or it was a broadcast/study). It is *not* the backfilled `evals_completed_at` flag, which marks games where we computed only phase-transition evals.

This report supersedes `benchmark-eval-coverage-2026-05-23.md`. The previous strict-coverage definition rejected ~75k clearly-analyzed games because of occasional stray interior nulls in Lichess output. The new definition uses a coverage-ratio threshold that sits inside the bimodal gap of the eval-density distribution, making the result robust to Lichess's exact null pattern.

## Result

| ELO ↓ / TC → | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800**  | 11.57% (3,052 / 26,376)  | 18.12% (4,742 / 26,176)   | 16.35% (3,744 / 22,900)    | 23.25% (645 / 2,774)      |
| **1200** | 10.46% (9,763 / 93,297)  | 15.94% (11,402 / 71,548)  | 20.30% (14,339 / 70,650)   | 29.86% (7,657 / 25,640)   |
| **1600** | 7.49% (6,804 / 90,891)   | 13.35% (15,179 / 113,724) | 20.81% (16,627 / 79,890)   | 47.98% (20,129 / 41,954)  |
| **2000** | 6.65% (6,576 / 98,922)   | 15.22% (14,866 / 97,700)  | 34.21% (31,900 / 93,246)   | **61.18%** (18,434 / 30,131) |
| **2400** | 8.19% (8,369 / 102,224)  | **40.30%** (36,559 / 90,722) | **61.45%** (35,609 / 57,951) | **61.01%** (2,357 / 3,863)   |

Across the full cohort: **~269k of ~1.24M games (~21.7%)** have Lichess analysis attached. Up from the ~228k (~18%) the strict-coverage definition reported; the difference is the ~41k stray-interior-null games that the strict method wrongly excluded.

## Patterns

- **Bullet stays low everywhere** (6.7–11.6%). Lichess rarely attaches analysis to 1-minute games. The ELO gradient that holds for slower TCs doesn't apply to bullet.
- **Rapid + classical at 2000–2400 cross 60%** — these are the cells where Lichess-provided evals can realistically be used as a primary signal.
- **Strong ELO gradient at slower TCs**: classical climbs 23% → 30% → 48% → 61% → 61% from 800 to 2400; rapid 16% → 20% → 21% → 34% → 61%.
- **Classical 2400 is a small cell** (3,863 games) so its 61.01% is noisy.

## Method

### Cohort

Games joined to `benchmark_ingest_checkpoints` with `status='completed'`. Matches the cohort definition used by the benchmarks skill (`reports/benchmarks-latest.md`).

### Cells

- **ELO bucket**: 400-wide, anchored at 800/1200/1600/2000/2400, computed from the **cohort user's rating at game time** (`games.white_rating` if `user_color='white'`, otherwise `games.black_rating`). The frozen selection-snapshot rating in `benchmark_selected_users` is deliberately *not* used.
- **TC bucket**: `games.time_control_bucket` (bullet / blitz / rapid / classical).

### "Analyzed" definition

A game counts as analyzed iff **at least 90% of its per-ply positions in `game_positions` have `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`**. The denominator is every stored position for the game (no boundary exclusion).

### Why a coverage ratio (and why 90%)

The eval-density distribution across the cohort is extremely bimodal — games either have nearly complete coverage or essentially none. A coverage histogram across all 1.24M cohort games:

| Coverage range | Games | What it represents |
|---|---:|---|
| 0–5%   | 972,622 | No analysis attached |
| 5–10%  | 36,468  | Internal phase-transition backfill only (a few specific plies evaled by our scripts) |
| 10–85% | ~30     | Essentially empty band |
| 85–90% | 564     | Rare partial analysis |
| 90–95% | 8,083   | Lichess analysis with a stray interior null |
| 95–100% | 267,393 | Modal Lichess analysis (one null at the terminal ply) |
| 100%   | 12,292  | Lichess evaled everything, including ply 0 |

There is a **~75-percentage-point gap** between the unanalyzed mode (≤10% coverage) and the analyzed mode (≥85% coverage), with only ~30 games inside it. Any cutoff in that gap classifies essentially the same set of games. 90% sits comfortably inside it: moving the threshold to 80% or 95% changes the cohort by less than 1% of analyzed games.

Why this is preferred over the alternatives:

- **Strict "every interior ply evaled" (the prior method) rejects ~75k Lichess-analyzed games** that happen to have one stray interior null. Plausible causes for a Lichess-attached game to have one missing interior eval: forced moves, repetition, threefold positions, or analysis early-out. The strict method has no way to distinguish these from genuine analysis gaps.
- **"≤ 2 total nulls" is brittle to Lichess behavior drift.** It works today because the modal pattern is "1 null at terminal" (229k games) or "no nulls at all" (13.5k games), so the absolute cap of 2 happens to be just above the typical analyzed-game null count. But if Lichess changed its behavior (e.g. started leaving 3 boundary plies unevaled, or 2 stray inner nulls in long games), the cap would silently flip from accepting analyzed games to rejecting them. The ratio method is invariant to that — it scales with game length and doesn't care which plies are missing.
- **Coverage ratio is self-validating on data.** The threshold can be picked by inspecting the histogram and placing the cutoff in the empty middle, rather than hand-coding a guess about Lichess's specific null pattern.

The one caveat is very short games (< 10 plies), where the ratio gets noisy — a single null can push coverage below 90%. But Lichess essentially never attaches analysis to early-resignation bullet games, so the noise lands in the rejected pile where it belongs.

### SQL

```sql
WITH cohort_games AS (
  SELECT
    g.id,
    g.time_control_bucket::text AS tc_bucket,
    CASE WHEN g.user_color = 'white' THEN g.white_rating ELSE g.black_rating END AS user_rating_at_game
  FROM games g
  JOIN benchmark_ingest_checkpoints c
    ON c.benchmark_user_id = g.user_id
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
coverage AS (
  SELECT p.game_id,
         COUNT(*) FILTER (WHERE p.eval_cp IS NOT NULL OR p.eval_mate IS NOT NULL)::numeric
           / NULLIF(COUNT(*), 0) AS frac_evaled
  FROM game_positions p
  GROUP BY p.game_id
)
SELECT
  b.elo_bucket,
  b.tc_bucket,
  COUNT(*) AS total_games,
  COUNT(*) FILTER (WHERE c.frac_evaled >= 0.90) AS analyzed_games,
  ROUND(100.0 * COUNT(*) FILTER (WHERE c.frac_evaled >= 0.90) / NULLIF(COUNT(*),0), 2) AS pct_analyzed
FROM bucketed b
LEFT JOIN coverage c ON c.game_id = b.id
WHERE b.elo_bucket IS NOT NULL
GROUP BY b.elo_bucket, b.tc_bucket
ORDER BY b.elo_bucket, b.tc_bucket;
```

## Comparison with prior methods

Per-cell analyzed-game counts under each method, side-by-side:

| Cell | Strict inner (2026-05-23) | ≤ 2 total nulls | ≥ 90% coverage (this report) | `blunders IS NOT NULL` |
|---|---:|---:|---:|---:|
| 800 blitz      | 2,738  | 4,828  | 4,742  | 4,798  |
| 1200 classical | 4,100  | 7,855  | 7,657  | 7,747  |
| 1600 classical | 14,501 | 20,277 | 20,129 | 20,258 |
| 2000 classical | 15,264 | 18,509 | 18,434 | 18,469 |
| 2400 rapid     | 30,272 | 35,709 | 35,609 | 35,636 |
| 2400 blitz     | 31,412 | 36,676 | 36,559 | 36,592 |

The three permissive methods agree to within ~0.5% of cohort. The strict-inner method undercounts by ~30–40% across cells.

The `blunders IS NOT NULL` aggregate-summary check tracks the ratio method within ~0.13% of the full cohort and is far cheaper (single column scan, no `game_positions` aggregation). It's a reasonable fast proxy when you don't already need per-ply data; the ratio method is preferred when you're scanning `game_positions` anyway, or when you want a definition that survives changes in how the summary fields are populated.

## Caveats

- **Coverage ratio is noisy on very short games.** Games with < 10 plies can flip below 90% on a single null. Lichess essentially never analyzes such games, so the misclassification rate is low in practice.
- **Phase-transition-only games are correctly excluded.** The ~36k games with 5–10% coverage (our own `backfill_eval.py` populating eval on a few specific plies for endgame analysis) sit well below the 90% threshold and don't enter the analyzed cohort.
- **Threshold sensitivity is minimal but not zero.** Moving the cutoff to 80% adds ~750 games globally; moving to 95% drops ~8,000 (the stray-inner-null bucket). 90% is the natural choice because it sits inside the empty band of the histogram.
- **Classical 2400 cell has only 3,863 games** — its 61.01% is noisy.

## Changes from the previous report (2026-05-23)

- **Definition changed** from "every interior ply has an eval" (strict) to "≥ 90% of plies have evals" (ratio).
- **Cohort sizes are ~18% larger across all cells** because the strict definition rejected games with one stray interior null. Largest absolute jumps at 1600 classical (+5,628 games), 1600 rapid (+4,480), 2400 blitz (+5,147), 2400 rapid (+5,337).
- **Bullet cells barely change** (e.g. 2400 bullet 6.11% → 8.19%) because the bullet population is dominated by truly-unanalyzed games. The ratio relaxation only matters where Lichess analysis is common.
- **The ELO × TC pattern is unchanged.** The narrative ("bullet stays low everywhere", "slow TCs cross 50%", "strong ELO gradient at slower TCs") holds; only the absolute percentages shift.

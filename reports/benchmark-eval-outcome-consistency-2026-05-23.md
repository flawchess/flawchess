# Eval vs Outcome Consistency by Rating

**Date:** 2026-05-23
**Source:** Lichess games imported from a curated benchmark pool of players sampled across rating buckets and time controls. Each game's Stockfish evaluation comes from Lichess itself — only games where Lichess attached a server-side analysis to every move are used.
**Scope:** blitz, rapid, classical only (bullet is excluded because Lichess almost never attaches an analysis to bullet games).

Two questions, both about how cleanly the engine evaluation lines up with the actual game result through the **middlegame and endgame** (the opening is excluded).

1. **Sustained advantage.** How often does a game both (a) have one side hold a **≥ 2-pawn lead** (engine eval ≥ +200 cp for that side) on every move of the middlegame and endgame, and (b) end as a win for the leader / a draw / a loss for the leader?
2. **Quiet game.** How often does a game both (a) stay within a **half-pawn** band (engine eval ≤ ±50 cp) on every move of the middlegame and endgame, and (b) end as a draw / decisively?

Every percentage in every table is **relative to `n_games`** — the full analyzed cohort per rating bucket. That makes the numbers joint rates (eval condition AND outcome), not conditional rates within a subset. The conditional rate (e.g. "given a sustained lead, what fraction convert") is easy to derive: divide the outcome column by the `% of n_games` column.

Only games where Lichess attached an evaluation to every middlegame/endgame move are counted. Games without a complete server-side analysis are excluded.

---

## Section 1 — Sustained ≥ 2-pawn advantage

For each rating bucket: `n_games` is the total number of games with a complete Lichess analysis. **sustained-lead** is the count of games where one side's eval was ≥ +200 cp on every middlegame/endgame move with no sign-flip. The right-hand columns show what fraction of `n_games` games matched each (eval-condition + outcome) combination. The three outcome columns sum to the **% of n_games** column.

| Rating | n_games | sustained-lead | % of n_games | leader wins | draws | leader loses |
|--------|--------:|---------------:|-------------:|------------:|------:|-------------:|
| **800**   |  5,074 | 1,482 | **29.21%** | **26.23%** | 0.08% | **2.90%** |
| **1200**  | 20,926 | 4,907 | **23.45%** | **22.33%** | 0.13% | **0.99%** |
| **1600**  | 37,522 | 5,708 | **15.21%** | **14.70%** | 0.07% | **0.45%** |
| **2000**  | 52,785 | 4,610 |  **8.73%** |  **8.62%** | 0.02% | **0.09%** |
| **2400**  | 62,998 | 3,258 |  **5.17%** |  **5.09%** | 0.01% | **0.07%** |

The **conversion rate** (% of sustained leads that convert to a win) is the ratio `leader wins / % of n_games`. At 800: 26.23 / 29.21 = **89.8%** convert; at 2400: 5.09 / 5.17 = **98.4%** convert.

### How often the leader loses, by time control (% of cell's own n_games)

Each cell's denominator is the `n_games` for that rating × time-control combination.

| Rating ↓ / TC → | blitz | rapid | classical |
|---|---:|---:|---:|
| **800**  | 3.175% | 2.651% | 1.838% |
| **1200** | 1.229% | 0.663% | 1.277% |
| **1600** | 0.514% | 0.312% | 0.512% |
| **2000** | 0.123% | 0.085% | 0.087% |
| **2400** | 0.077% | 0.057% | 0.051% |

### Mistakes by leader vs opponent (per analyzed game)

Total Lichess-reported inaccuracies / mistakes / blunders committed **in sustained-lead games** by the leader and the opponent respectively, divided by `n_games`. Games without a sustained lead contribute zero. So 0.399 leader inaccuracies at 800 means: across all 5,074 analyzed 800-rated games, the average game has 0.4 inaccuracies attributable to "a sustained-lead leader" (i.e., 0 most of the time, ~1.85 in the 29% of games that do have a sustained lead).

| Rating | n_games | leader inacc | leader mist | leader blun | opp inacc | opp mist | opp blun |
|--------|--------:|-------------:|------------:|------------:|----------:|---------:|---------:|
| **800**  |  5,074 | 0.399 | 0.175 | 0.164 | 0.608 | 0.324 | **0.390** |
| **1200** | 20,926 | 0.289 | 0.118 | 0.110 | 0.483 | 0.235 | **0.299** |
| **1600** | 37,522 | 0.183 | 0.061 | 0.052 | 0.325 | 0.144 | **0.175** |
| **2000** | 52,785 | 0.088 | 0.026 | 0.017 | 0.188 | 0.081 | **0.086** |
| **2400** | 62,998 | 0.044 | 0.011 | 0.007 | 0.114 | 0.048 | **0.047** |

### What the numbers mean

- **Sustained-lead games are common at low rating, rare at high rating**: 29% of low-rated games (800) have one side ≥ +200 cp throughout middlegame/endgame, vs only 5% at 2400. Low-rated games are blunder-driven and produce decisive evals fast; master-level games stay competitive and tight.
- **"Leader loses" plummets with rating**: 2.90% of all 800-rated games end with a sustained leader who then loses, vs only 0.07% at 2400 — a **40× drop**. Combines lower sustained-lead prevalence with stronger conversion skill.
- **Conversion rate (derived from the table) climbs sharply with rating**: an 800 player converts only 89.8% of sustained leads, vs 98.4% at 2400. Even a +2-pawn lead held through the entire middlegame and endgame is not safe at 800 level.
- **Conversion is essentially solved by 2000.** The 2000 → 2400 jump in "leader loses %" is from 0.09% to 0.07% — once a player reaches expert strength, holding a sustained advantage is automatic.
- **Slow time controls help low-rated players convert**: 800 classical "leader loses" rate is 1.84% of n_games vs 800 blitz 3.18%. Extra thinking time roughly halves the giveaway rate at the bottom of the ladder. The TC effect almost disappears at 2000+ because conversion is already near ceiling.
- **Draws from sustained leads are negligible** (~0.01–0.13% of n_games) — when one side holds a sustained +2-pawn lead, the game almost always resolves win-or-loss. Perpetual / fortress / stalemate draws from a winning position are rare.
- **The opponent contributes 1.5–2.5× more blunders per analyzed game than the leader.** At 800 the gap is 0.16 vs 0.39 (opponent 2.4× higher); at 2400 it's 0.007 vs 0.047 (opponent 6.7× higher). The ratio widens with rating even as absolute counts shrink.
- **The cohort-wide blunder load from sustained-lead games drops ~20×** from 800 to 2400 (combined leader + opponent: 0.55 → 0.054 per analyzed game). Fewer sustained-lead games × cleaner play within them = compounding effect.
- **Small-cell warning**: 2400 classical (n=1,952 analyzed) and 800 classical (n=272) are sparse — treat their by-TC percentages as noisy.

---

## Section 2 — Quiet game (eval stayed within ±50 cp throughout)

For each rating bucket: `n_games` is the same denominator as Section 1. **quiet** is the count of games where neither side ever exceeded a half-pawn edge in the middlegame or endgame. The right-hand columns show what fraction of `n_games` games matched each (eval-condition + outcome) combination. The two outcome columns sum to the **% of n_games** column.

| Rating | n_games | quiet | % of n_games | draws | decisive |
|--------|--------:|------:|-------------:|------:|---------:|
| **800**   |  5,074 |  25 | **0.493%** | **0.020%** | **0.473%** |
| **1200**  | 20,926 |  73 | **0.349%** | **0.005%** | **0.344%** |
| **1600**  | 37,522 | 143 | **0.381%** | **0.064%** | **0.317%** |
| **2000**  | 52,785 | 215 | **0.407%** | **0.203%** | **0.205%** |
| **2400**  | 62,998 | 348 | **0.552%** | **0.422%** | **0.130%** |

The **conditional draw rate** (% of quiet games that ended in a draw) is `draws / % of n_games`. At 2400: 0.422 / 0.552 = **76%** draw; at 800: 0.020 / 0.493 = **4%** draw.

### Mistakes by side (per analyzed game)

Total Lichess-reported inaccuracies / mistakes / blunders committed **in quiet games** by the white side and the black side respectively, divided by `n_games`. Quiet games are rare (0.35–0.55% of the cohort), so these per-cohort values are very small — they're useful for symmetry checks and cohort-wide accounting, not as standalone per-game intuition.

| Rating | n_games | white inacc | white mist | white blun | black inacc | black mist | black blun |
|--------|--------:|------------:|-----------:|-----------:|------------:|-----------:|-----------:|
| **800**  |  5,074 | 0.00079 | 0.00039 | 0.00000 | 0.00079 | 0.00039 | 0.00000 |
| **1200** | 20,926 | 0.00086 | 0.00033 | 0.00033 | 0.00105 | 0.00019 | 0.00014 |
| **1600** | 37,522 | 0.00189 | 0.00061 | 0.00043 | 0.00189 | 0.00061 | 0.00040 |
| **2000** | 52,785 | 0.00224 | 0.00030 | 0.00019 | 0.00157 | 0.00038 | 0.00015 |
| **2400** | 62,998 | 0.00178 | 0.00025 | 0.00017 | 0.00163 | 0.00022 | 0.00013 |

For intuition about per-quiet-game rates, divide by the **% of n_games** column from the main Section 2 table. E.g. at 2400 white inaccuracies: 0.00178 ÷ 0.00552 = **0.32 inaccuracies per quiet game** — consistent with master-level near-perfect play.

### What the numbers mean

- **"Quiet decisive" is a low-rating pattern; "quiet draw" is a high-rating pattern.** Reading the outcome columns top-to-bottom:
  - The **decisive** column trends **down** with rating (0.473% → 0.130%) — quiet games that resolve with a winner become less common as rating rises.
  - The **draws** column trends **up** with rating (0.020% → 0.422%) — quiet games that resolve as draws become much more common as rating rises.
  - They cross around the **2000** band, where the two are nearly equal (0.203% draws vs 0.205% decisive).
- **A quiet game is not a drawn game at low rating.** At 800 / 1200, decisive outcomes outnumber draws by **24× and 72×** respectively. The termination breakdown explains why: about 70% of these decisive quiet games are **resignations of an equal position** (17 of 25 at 800; 47 of 73 at 1200). The remainder are abandonments (disconnects, scored as losses by Lichess) and flag-falls. Low-rated players resign positions they shouldn't.
- **Quiet games are rare at every rating** — only 0.35%–0.55% of analyzed games per bucket. The rate is lowest at 1200 / 1600 (~0.35–0.38%) and slightly higher at the extremes. Low rating produces the occasional tactical accident that ends quietly; high rating produces strategic technical draws; the middle of the ladder is the noisiest.
- **The mistake table is symmetric between white and black at every rating** — no systematic color bias in quiet games. The cohort-wide mistake load from quiet games rises from 800 to 1600/2000 then plateaus, driven by rising quiet-game prevalence rather than per-game mistake rates.
- **Small-cell warning**: 800 (n=25 quiet) and 1200 (n=73 quiet) are sparse. The decisive-dominance finding is directionally robust (a stricter ±30 cp threshold gives the same result) but the exact value is noisy.

---

## Method

### Players and games

The benchmark pool consists of players selected from a Lichess monthly dump, stratified by rating bucket and time control. Each player's games are imported from the Lichess API; only games from players whose import completed successfully are used.

### Rating buckets

400-point-wide, anchored at 800 / 1200 / 1600 / 2000 / 2400. Each game is bucketed by the **player's actual Lichess rating at the time the game was played**, not the rating at the moment the player was selected for the benchmark pool. (A snapshot rating would bias the buckets — players selected at 1599 with falling form get tagged 1600 even though most of their analyzed games are below that.)

### Move window

For every game we look at the **middlegame and endgame** moves only — the opening phase is excluded. We also drop the very first position (the starting position, which never has an eval) and the very last position (the checkmate / stalemate / resignation / flag-fall state, which usually doesn't carry an eval either). What's left is the body of the game, where Lichess's server-side Stockfish annotation should be present for every move.

A game is included in the analysis only if Lichess attached an evaluation to **every** move in that window. Games with partial coverage are excluded entirely.

### Section 1 — sustained-lead condition

Among included games, keep those where:
- The engine evaluation was **≥ +200 cp for one side on every middlegame/endgame move** (no move was inside the ±200 cp band).
- The eval **never flipped sign** — i.e., it always favored the same side throughout.

Then classify the result relative to that side: leader wins / draws / leader loses.

### Section 2 — quiet condition

Among included games, keep those where the engine evaluation was **within ±50 cp on every middlegame/endgame move**. A mate-in-N evaluation anywhere disqualifies the game (mate is treated as an effectively infinite edge).

Then classify the result: draw vs decisive.

### Handling of mate-in-N

When Lichess reports `mate in N` instead of a centipawn value, we treat the absolute eval as effectively infinite with the appropriate side leading. Mate-in-N counts toward Section 1's sustained ≥ +200 lead, and disqualifies a game from Section 2's ±50 cp quiet condition.

### Denominator consistency

Every percentage in every table uses **`n_games` for that rating bucket** (or that rating × time-control cell, for the per-TC table) as the denominator. Outcome columns are joint rates: fraction of `n_games` games that both met the eval condition AND ended each way. Mistake-breakdown columns are also normalized to `n_games`: total mistakes summed across qualifying games, divided by `n_games`. To recover conditional rates (e.g. "given a sustained lead, what fraction convert"), divide an outcome column by the `% of n_games` column.

## Caveats

- The thresholds (≥ 200 cp and ≤ 50 cp) are strict per-move. A single transient spike disqualifies a game. Loosening to "≥ 95% of moves meet the threshold" would broaden the sample but wasn't measured here.
- Lichess's analysis coverage varies sharply by rating and time control (see `benchmark-eval-coverage-2026-05-23.md`). The denominators here skew toward longer time controls and higher-rated players, who are far more likely to have Lichess analysis attached.
- The final move of a game is excluded from the evaluation window because Lichess doesn't reliably score the terminal position. This does NOT drive Section 2's "97–99% decisive at 800/1200" finding — the dominant cause is resignation of balanced positions, which is a recorded outcome rather than something we miss in the eval.
- Small-cell warnings: Section 2 at 800 (n=25 quiet) and 1200 (n=73 quiet); Section 1 at 2400 classical (n=1,952 analyzed) and 800 classical (n=272 analyzed).

## Reproducibility — SQL

For anyone replicating the analysis directly against the benchmark database. Skip this section if you're not running queries yourself.

```sql
WITH cohort_games AS (
  SELECT g.id, g.result,
         g.white_inaccuracies, g.white_mistakes, g.white_blunders,
         g.black_inaccuracies, g.black_mistakes, g.black_blunders,
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
  SELECT CASE
      WHEN user_rating_at_game BETWEEN  600 AND  999 THEN  800
      WHEN user_rating_at_game BETWEEN 1000 AND 1399 THEN 1200
      WHEN user_rating_at_game BETWEEN 1400 AND 1799 THEN 1600
      WHEN user_rating_at_game BETWEEN 1800 AND 2199 THEN 2000
      WHEN user_rating_at_game BETWEEN 2200 AND 2599 THEN 2400
    END AS elo_bucket, *
  FROM cohort_games
),
ply_bounds AS (SELECT game_id, MAX(ply) AS max_ply FROM game_positions GROUP BY game_id),
phase_gt0_agg AS (
  SELECT p.game_id,
    COUNT(*) AS positions,
    COUNT(*) FILTER (WHERE p.eval_cp IS NOT NULL OR p.eval_mate IS NOT NULL) AS evaled,
    MIN(CASE WHEN p.eval_cp IS NOT NULL THEN abs(p.eval_cp) WHEN p.eval_mate IS NOT NULL THEN 10000 END) AS min_abs_eval,
    MAX(CASE WHEN p.eval_cp IS NOT NULL THEN abs(p.eval_cp) WHEN p.eval_mate IS NOT NULL THEN 10000 END) AS max_abs_eval,
    MIN(CASE WHEN p.eval_cp IS NOT NULL THEN sign(p.eval_cp) WHEN p.eval_mate IS NOT NULL THEN sign(p.eval_mate) END) AS min_sign,
    MAX(CASE WHEN p.eval_cp IS NOT NULL THEN sign(p.eval_cp) WHEN p.eval_mate IS NOT NULL THEN sign(p.eval_mate) END) AS max_sign
  FROM game_positions p JOIN ply_bounds pb ON pb.game_id = p.game_id
  WHERE p.phase > 0 AND p.ply > 0 AND p.ply < pb.max_ply
  GROUP BY p.game_id
),
flagged AS (
  SELECT b.elo_bucket, b.id, b.result,
    (a.positions IS NOT NULL AND a.positions = a.evaled) AS full_cov,
    (a.positions IS NOT NULL AND a.positions = a.evaled
       AND a.min_abs_eval >= 200 AND a.min_sign = a.max_sign AND a.min_sign <> 0) AS sustained,
    a.min_sign,
    (a.positions IS NOT NULL AND a.positions = a.evaled AND a.max_abs_eval <= 50) AS quiet,
    b.white_inaccuracies, b.white_mistakes, b.white_blunders,
    b.black_inaccuracies, b.black_mistakes, b.black_blunders
  FROM bucketed b LEFT JOIN phase_gt0_agg a ON a.game_id = b.id
)
SELECT
  elo_bucket,
  COUNT(*) FILTER (WHERE full_cov) AS n_games,
  COUNT(*) FILTER (WHERE sustained) AS sustained,
  COUNT(*) FILTER (WHERE sustained AND ((min_sign > 0 AND result='1-0') OR (min_sign < 0 AND result='0-1'))) AS leader_wins,
  COUNT(*) FILTER (WHERE sustained AND result = '1/2-1/2') AS s1_draws,
  COUNT(*) FILTER (WHERE sustained AND ((min_sign > 0 AND result='0-1') OR (min_sign < 0 AND result='1-0'))) AS leader_loses,
  COUNT(*) FILTER (WHERE quiet) AS quiet,
  COUNT(*) FILTER (WHERE quiet AND result = '1/2-1/2') AS quiet_draws,
  COUNT(*) FILTER (WHERE quiet AND result <> '1/2-1/2') AS quiet_decisive
FROM flagged
WHERE elo_bucket IS NOT NULL
GROUP BY elo_bucket
ORDER BY elo_bucket;
```

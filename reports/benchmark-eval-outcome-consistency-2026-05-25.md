# Eval vs Outcome Consistency by Rating

**Date:** 2026-05-25
**Source:** Lichess games imported from a curated benchmark pool of players sampled across rating buckets and time controls. Each game's Stockfish evaluation comes from Lichess itself — only games where Lichess attached a server-side analysis are used.
**Scope:** blitz, rapid, classical only (bullet is excluded because Lichess almost never attaches an analysis to bullet games).

Two questions, both about how cleanly the engine evaluation lines up with the actual game result through the **middlegame and endgame** (the opening is excluded).

1. **Sustained advantage.** How often does a game both (a) have one side hold a **≥ 2-pawn lead** (engine eval ≥ +200 cp for that side) on every move of the middlegame and endgame, and (b) end as a win for the leader / a draw / a loss for the leader?
2. **Quiet game.** How often does a game both (a) stay within a **half-pawn** band (engine eval ≤ ±50 cp) on every move of the middlegame and endgame, and (b) end as a draw / decisively?

Every percentage in every table is **relative to `n_games`** — the full analyzed cohort per rating bucket. That makes the numbers joint rates (eval condition AND outcome), not conditional rates within a subset. The conditional rate (e.g. "given a sustained lead, what fraction convert") is easy to derive: divide the outcome column by the `% of n_games` column.

### Game inclusion: ≥ 90% per-ply eval coverage

A game is **included** in the analyzed cohort if **at least 90% of its plies in `game_positions` have `eval_cp` or `eval_mate` populated** (denominator: every stored ply for the game). This is the same definition used in `benchmark-eval-coverage-2026-05-25.md`.

The eval-density distribution across the cohort is sharply bimodal — games either have ≥ 85% coverage (Lichess analysis attached) or ≤ 10% coverage (no analysis, or only our own phase-transition backfill). A ~75-point empty band separates the two modes, so any cutoff inside it picks essentially the same set of games. 90% sits cleanly in that gap.

This rule is preferred over the previous report's "≤ 2 total missing evals per game" criterion because:

- **It's robust to Lichess null-pattern drift.** "≤ 2 nulls" works today only because the modal Lichess-analyzed game has 1 null at the terminal ply or 0 nulls overall. If Lichess started leaving 3 boundary plies unevaled, or sometimes adding 2 stray inner nulls in long games, the absolute cap would silently flip from including analyzed games to excluding them. The ratio method scales with game length and doesn't care which plies are missing.
- **The threshold is data-driven.** It's picked by inspecting the coverage histogram and placing the cutoff in the empty middle, not by guessing Lichess's specific null pattern.

The new cohort is **0.3–2.3% smaller** than the previous report at every rating bucket (it correctly excludes ~500–8,000 partially-analyzed games per bucket that the ≤2-nulls rule was letting through when Lichess attached only most of an analysis). Headline metrics shift by ≤ 0.04 percentage points; the report's narrative is unchanged.

---

## Section 1 — Sustained ≥ 2-pawn advantage

For each rating bucket: `n_games` is the total number of games meeting the inclusion criterion. **sustained-lead** is the count of games where one side's eval was ≥ +200 cp on every middlegame/endgame move with no sign-flip. The right-hand columns show what fraction of `n_games` games matched each (eval-condition + outcome) combination. The three outcome columns sum to the **% of n_games** column.

| Rating | n_games | sustained-lead | % of n_games | leader wins | draws | leader loses |
|--------|--------:|---------------:|-------------:|------------:|------:|-------------:|
| **800**   |  9,131 | 2,430 | **26.61%** | **25.24%** | 0.03% | **1.34%** |
| **1200**  | 33,398 | 6,798 | **20.35%** | **19.75%** | 0.07% | **0.53%** |
| **1600**  | 51,935 | 7,029 | **13.53%** | **13.20%** | 0.04% | **0.29%** |
| **2000**  | 65,200 | 5,372 |  **8.24%** |  **8.16%** | 0.02% | **0.06%** |
| **2400**  | 74,525 | 3,864 |  **5.19%** |  **5.12%** | 0.01% | **0.06%** |

The **conversion rate** (% of sustained leads that convert to a win) is the ratio `leader wins / % of n_games`. At 800: 25.24 / 26.61 = **94.9%** convert; at 2400: 5.12 / 5.19 = **98.7%** convert.

### How often the leader loses, by time control (% of cell's own n_games)

Each cell's denominator is the `n_games` for that rating × time-control combination.

| Rating ↓ / TC → | blitz | rapid | classical |
|---|---:|---:|---:|
| **800**  | 1.708% | 1.015% | 0.465% |
| **1200** | 0.763% | 0.321% | 0.575% |
| **1600** | 0.336% | 0.205% | 0.328% |
| **2000** | 0.087% | 0.050% | 0.060% |
| **2400** | 0.063% | 0.048% | 0.042% |

### Mistakes by leader vs opponent (per analyzed game)

Total Lichess-reported inaccuracies / mistakes / blunders committed **in sustained-lead games** by the leader and the opponent respectively, divided by `n_games`. Games without a sustained lead contribute zero. So 0.487 leader inaccuracies at 800 means: across all 9,131 analyzed 800-rated games, the average game contributes 0.49 inaccuracies attributable to "a sustained-lead leader" (i.e., 0 most of the time, ~1.83 in the 27% of games that do have a sustained lead).

| Rating | n_games | leader inacc | leader mist | leader blun | opp inacc | opp mist | opp blun |
|--------|--------:|-------------:|------------:|------------:|----------:|---------:|---------:|
| **800**  |  9,131 | 0.487 | 0.234 | 0.205 | 0.784 | 0.454 | **0.511** |
| **1200** | 33,398 | 0.333 | 0.144 | 0.128 | 0.567 | 0.306 | **0.356** |
| **1600** | 51,935 | 0.196 | 0.072 | 0.057 | 0.356 | 0.174 | **0.204** |
| **2000** | 65,200 | 0.094 | 0.031 | 0.020 | 0.205 | 0.095 | **0.100** |
| **2400** | 74,525 | 0.048 | 0.013 | 0.008 | 0.124 | 0.055 | **0.054** |

### What the numbers mean

- **Sustained-lead games are common at low rating, rare at high rating**: 27% of low-rated games (800) have one side ≥ +200 cp throughout middlegame/endgame, vs only 5% at 2400. Low-rated games are blunder-driven and produce decisive evals fast; master-level games stay competitive and tight.
- **"Leader loses" plummets with rating**: 1.34% of all 800-rated games end with a sustained leader who then loses, vs only 0.06% at 2400 — a **~22× drop**. Combines lower sustained-lead prevalence with stronger conversion skill.
- **Conversion rate (derived from the table) climbs sharply with rating**: an 800 player converts 94.9% of sustained leads, vs 98.7% at 2400. Even a +2-pawn lead held through the entire middlegame and endgame is not bulletproof at 800 level.
- **Conversion is essentially solved by 2000.** The 2000 → 2400 jump in "leader loses %" is flat at 0.06% — once a player reaches expert strength, holding a sustained advantage is automatic.
- **Slow time controls help low-rated players convert**: 800 classical "leader loses" rate is 0.47% of n_games vs 800 blitz 1.71%. Extra thinking time roughly quarters the giveaway rate at the bottom of the ladder. The TC effect almost disappears at 2000+ because conversion is already near ceiling.
- **Draws from sustained leads are negligible** (~0.01–0.07% of n_games) — when one side holds a sustained +2-pawn lead, the game almost always resolves win-or-loss. Perpetual / fortress / stalemate draws from a winning position are rare.
- **The opponent contributes 1.5–2.5× more blunders per analyzed game than the leader.** At 800 the gap is 0.20 vs 0.51 (opponent 2.5× higher); at 2400 it's 0.008 vs 0.054 (opponent 6.8× higher). The ratio widens with rating even as absolute counts shrink.
- **The cohort-wide blunder load from sustained-lead games drops ~11×** from 800 to 2400 (combined leader + opponent: 0.72 → 0.062 per analyzed game). Fewer sustained-lead games × cleaner play within them = compounding effect.
- **Small-cell warning**: 2400 classical (n=2,357) and 800 classical (n=645) are sparse — treat their by-TC percentages as noisy.

---

## Section 2 — Quiet game (eval stayed within ±50 cp throughout)

For each rating bucket: `n_games` is the same denominator as Section 1. **quiet** is the count of games where neither side ever exceeded a half-pawn edge in the middlegame or endgame. The right-hand columns show what fraction of `n_games` games matched each (eval-condition + outcome) combination. The two outcome columns sum to the **% of n_games** column.

| Rating | n_games | quiet | % of n_games | draws | decisive |
|--------|--------:|------:|-------------:|------:|---------:|
| **800**   |  9,131 |   4 | **0.044%** | **0.000%** | **0.044%** |
| **1200**  | 33,398 |  20 | **0.060%** | **0.003%** | **0.057%** |
| **1600**  | 51,935 |  71 | **0.137%** | **0.040%** | **0.096%** |
| **2000**  | 65,200 | 172 | **0.264%** | **0.161%** | **0.103%** |
| **2400**  | 74,525 | 326 | **0.437%** | **0.346%** | **0.091%** |

The **conditional draw rate** (% of quiet games that ended in a draw) is `draws / % of n_games`. At 2400: 0.346 / 0.437 = **79%** draw; at 800: 0 / 0.044 = **0%** draw (sample of 4 — see small-cell warning).

### Mistakes by side (per analyzed game)

Total Lichess-reported inaccuracies / mistakes / blunders committed **in quiet games** by the white side and the black side respectively, divided by `n_games`. Quiet games are rare (0.04–0.44% of the cohort), so these per-cohort values are very small — they're useful for symmetry checks and cohort-wide accounting, not as standalone per-game intuition.

| Rating | n_games | white inacc | white mist | white blun | black inacc | black mist | black blun |
|--------|--------:|------------:|-----------:|-----------:|------------:|-----------:|-----------:|
| **800**  |  9,131 | 0.00044 | 0.00022 | 0.00000 | 0.00044 | 0.00022 | 0.00000 |
| **1200** | 33,398 | 0.00054 | 0.00021 | 0.00021 | 0.00066 | 0.00012 | 0.00009 |
| **1600** | 51,935 | 0.00137 | 0.00044 | 0.00031 | 0.00137 | 0.00044 | 0.00029 |
| **2000** | 65,200 | 0.00181 | 0.00025 | 0.00015 | 0.00127 | 0.00031 | 0.00012 |
| **2400** | 74,525 | 0.00150 | 0.00021 | 0.00015 | 0.00138 | 0.00019 | 0.00011 |

For intuition about per-quiet-game rates, divide by the **% of n_games** column from the main Section 2 table. E.g. at 2400 white inaccuracies: 0.00150 ÷ 0.00437 = **0.34 inaccuracies per quiet game** — consistent with master-level near-perfect play.

### What the numbers mean

- **"Quiet decisive" is a low-rating pattern; "quiet draw" is a high-rating pattern.** Reading the outcome columns top-to-bottom:
  - The **decisive** column trends **up then flat** (0.044% → 0.096% → 0.103% → 0.091%). At low rating quiet decisive games are extremely rare in absolute terms (4 games at 800) because almost no 800-rated game stays within ±50 cp end-to-end.
  - The **draws** column trends sharply **up** with rating (0.000% → 0.346%) — quiet games that resolve as draws become much more common as rating rises.
  - They cross around the **1800–2000** band, where draws first dominate decisives.
- **A quiet game is not a drawn game at low rating.** At 800 / 1200, decisive outcomes outnumber draws (4–0 and 19–1). The termination breakdown explains why: of 23 decisive quiet games at 800/1200 combined, **15 are resignations of equal positions**, 5 are timeouts, and 3 are abandonments. Low-rated players resign positions they shouldn't.
- **Quiet games are very rare at low rating** — only 4 of 9,131 games (0.04%) at 800, climbing to 326 of 74,525 games (0.44%) at 2400. A 10× increase in prevalence. Low-rated chess produces decisive imbalances quickly; master-level chess tolerates a long balanced middlegame.
- **The mistake table is symmetric between white and black at every rating** — no systematic color bias in quiet games. The cohort-wide mistake load from quiet games rises with rating, driven by rising quiet-game prevalence rather than per-game mistake rates.
- **Small-cell warning**: 800 (n=4 quiet) and 1200 (n=20 quiet) are very sparse. Don't read precision into the percentages there — directionally they show that low-rated chess rarely produces a ±50 cp game, and the few that exist tend to be premature resignations.

---

## Method

### Players and games

The benchmark pool consists of players selected from a Lichess monthly dump, stratified by rating bucket and time control. Each player's games are imported from the Lichess API; only games from players whose import completed successfully are used.

### Rating buckets

400-point-wide, anchored at 800 / 1200 / 1600 / 2000 / 2400. Each game is bucketed by the **player's actual Lichess rating at the time the game was played**, not the rating at the moment the player was selected for the benchmark pool. (A snapshot rating would bias the buckets — players selected at 1599 with falling form get tagged 1600 even though most of their analyzed games are below that.)

### Game inclusion criterion

A game is included in the analyzed cohort if **at least 90% of its plies in `game_positions` have `eval_cp` or `eval_mate` populated** (denominator: all stored plies for the game; no boundary exclusion). This matches the definition in `benchmark-eval-coverage-2026-05-25.md` and is the threshold that sits inside the empty band of the bimodal coverage histogram (essentially-zero games fall between 10% and 85% coverage).

### Move window for eval conditions

For every game we evaluate the sustained-lead and quiet conditions over the **middlegame and endgame** moves only — the opening phase is excluded. We also drop the very first position (the starting position, which never has an eval) and the very last position (the checkmate / stalemate / resignation / flag-fall state, which usually doesn't carry an eval either).

Within that window, we look at the non-null evals only. With the ≥ 90% coverage inclusion rule, the middlegame/endgame window is typically near-fully covered; the rare stray interior null inside the window is simply skipped when evaluating the condition.

### Section 1 — sustained-lead condition

Among included games, keep those where:
- The engine evaluation was **≥ +200 cp for one side on every middlegame/endgame move** with an eval (no eval was inside the ±200 cp band).
- The eval **never flipped sign** — i.e., it always favored the same side throughout.

Then classify the result relative to that side: leader wins / draws / leader loses.

### Section 2 — quiet condition

Among included games, keep those where the engine evaluation was **within ±50 cp on every middlegame/endgame move** with an eval. A mate-in-N evaluation anywhere disqualifies the game (mate is treated as an effectively infinite edge).

Then classify the result: draw vs decisive.

### Handling of mate-in-N

When Lichess reports `mate in N` instead of a centipawn value, we treat the absolute eval as effectively infinite with the appropriate side leading. Mate-in-N counts toward Section 1's sustained ≥ +200 lead, and disqualifies a game from Section 2's ±50 cp quiet condition.

### Denominator consistency

Every percentage in every table uses **`n_games` for that rating bucket** (or that rating × time-control cell, for the per-TC table) as the denominator. Outcome columns are joint rates: fraction of `n_games` games that both met the eval condition AND ended each way. Mistake-breakdown columns are also normalized to `n_games`: total mistakes summed across qualifying games, divided by `n_games`. To recover conditional rates (e.g. "given a sustained lead, what fraction convert"), divide an outcome column by the `% of n_games` column.

### Changes from the previous report (also dated 2026-05-25, using ≤ 2 nulls)

- **Inclusion rule changed** from "≤ 2 missing evals across the whole game" to "≥ 90% of plies have evals." Both rules try to capture the same target — fully analyzed Lichess games — but the ratio method survives any future drift in Lichess's null pattern (e.g. if they started attaching analyses with 3 boundary nulls, or with occasional 2 stray inner nulls in long games, the absolute-cap rule would silently misclassify). See `benchmark-eval-coverage-2026-05-25.md` for the per-cell comparison and the coverage histogram that motivates the threshold.
- **Cohort sizes shrink slightly** at every rating: 9,346 → 9,131 (800), 33,920 → 33,398 (1200), 52,438 → 51,935 (1600), 65,584 → 65,200 (2000), 74,772 → 74,525 (2400). The ≤ 2-nulls rule was over-including a small number of partially-analyzed games (analysis present but with 3+ interior gaps).
- **Headline metrics barely move.** Sustained-lead conversion at 800 stays at 94.9%; "leader loses" rates shift by at most 0.04 percentage points at any bucket; the 22–24× drop from 800 to 2400 in "leader loses" stands. Quiet-game prevalences at every rating round to the same value. The narrative is unchanged.

## Caveats

- The thresholds (≥ 200 cp and ≤ 50 cp) are strict per-move. A single transient spike disqualifies a game. Loosening to "≥ 95% of moves meet the threshold" would broaden the sample but wasn't measured here.
- Lichess's analysis coverage varies sharply by rating and time control. The denominators here skew toward longer time controls and higher-rated players, who are far more likely to have Lichess analysis attached.
- The final move of a game is excluded from the evaluation window because Lichess doesn't reliably score the terminal position. This does NOT drive Section 2's "all decisive at 800" finding — the dominant cause is resignation of balanced positions, which is a recorded outcome rather than something we miss in the eval.
- Very short games (< 10 plies) can fall below 90% coverage on a single null. Lichess essentially never attaches analysis to such games, so the noise lands in the rejected pile where it belongs.
- Small-cell warnings: Section 2 at 800 (n=4 quiet) and 1200 (n=20 quiet); Section 1 at 2400 classical (n=2,357) and 800 classical (n=645).

## Reproducibility — SQL

Step-by-step CTEs designed to be easy to read and modify. Each CTE has a single, well-defined responsibility.

```sql
-- Step 1: pull the cohort of games where the import completed successfully.
WITH cohort_games AS (
  SELECT g.id, g.result,
         g.white_inaccuracies, g.white_mistakes, g.white_blunders,
         g.black_inaccuracies, g.black_mistakes, g.black_blunders,
         g.time_control_bucket::text AS tc_bucket,
         CASE WHEN g.user_color = 'white' THEN g.white_rating ELSE g.black_rating END AS user_rating
  FROM games g
  JOIN users u ON u.id = g.user_id
  JOIN benchmark_ingest_checkpoints c
    ON c.benchmark_user_id = u.id
   AND c.tc_bucket::text = g.time_control_bucket::text
   AND c.status = 'completed'
  WHERE g.time_control_bucket::text IN ('blitz', 'rapid', 'classical')
),

-- Step 2: bucket each game by the player's actual rating at game time.
bucketed AS (
  SELECT *,
    CASE
      WHEN user_rating BETWEEN  600 AND  999 THEN  800
      WHEN user_rating BETWEEN 1000 AND 1399 THEN 1200
      WHEN user_rating BETWEEN 1400 AND 1799 THEN 1600
      WHEN user_rating BETWEEN 1800 AND 2199 THEN 2000
      WHEN user_rating BETWEEN 2200 AND 2599 THEN 2400
    END AS elo_bucket
  FROM cohort_games
),

-- Step 3: per-game eval coverage = fraction of plies with eval_cp or eval_mate.
coverage AS (
  SELECT p.game_id,
         COUNT(*) FILTER (WHERE p.eval_cp IS NOT NULL OR p.eval_mate IS NOT NULL)::numeric
           / NULLIF(COUNT(*), 0) AS frac_evaled
  FROM game_positions p
  GROUP BY p.game_id
),

-- Step 4: include games with at least 90% eval coverage.
-- The 90% threshold sits inside the empty band of the bimodal coverage histogram
-- (essentially-zero games between 10% and 85%); see benchmark-eval-coverage-2026-05-25.md.
included AS (
  SELECT b.*
  FROM bucketed b
  JOIN coverage c ON c.game_id = b.id
  WHERE c.frac_evaled >= 0.90 AND b.elo_bucket IS NOT NULL
),

-- Step 5: find the terminal ply per game (for excluding the last position).
ply_bounds AS (
  SELECT game_id, MAX(ply) AS max_ply FROM game_positions GROUP BY game_id
),

-- Step 6: aggregate middlegame/endgame evals per game (mate = effectively infinite).
mg_eg_evals AS (
  SELECT p.game_id,
         COUNT(*) AS positions,
         MIN(CASE WHEN p.eval_cp IS NOT NULL THEN abs(p.eval_cp)
                  WHEN p.eval_mate IS NOT NULL THEN 10000 END) AS min_abs,
         MAX(CASE WHEN p.eval_cp IS NOT NULL THEN abs(p.eval_cp)
                  WHEN p.eval_mate IS NOT NULL THEN 10000 END) AS max_abs,
         MIN(CASE WHEN p.eval_cp IS NOT NULL THEN sign(p.eval_cp)
                  WHEN p.eval_mate IS NOT NULL THEN sign(p.eval_mate) END) AS min_sign,
         MAX(CASE WHEN p.eval_cp IS NOT NULL THEN sign(p.eval_cp)
                  WHEN p.eval_mate IS NOT NULL THEN sign(p.eval_mate) END) AS max_sign
  FROM game_positions p
  JOIN ply_bounds pb ON pb.game_id = p.game_id
  JOIN included i ON i.id = p.game_id
  WHERE p.phase > 0 AND p.ply > 0 AND p.ply < pb.max_ply
    AND (p.eval_cp IS NOT NULL OR p.eval_mate IS NOT NULL)
  GROUP BY p.game_id
),

-- Step 7: flag each included game as sustained-lead / quiet.
flagged AS (
  SELECT i.elo_bucket, i.id, i.result, i.tc_bucket,
         i.white_inaccuracies, i.white_mistakes, i.white_blunders,
         i.black_inaccuracies, i.black_mistakes, i.black_blunders,
         e.min_sign,
         (e.positions > 0 AND e.min_abs >= 200
          AND e.min_sign = e.max_sign AND e.min_sign <> 0) AS sustained,
         (e.positions > 0 AND e.max_abs <= 50) AS quiet
  FROM included i
  LEFT JOIN mg_eg_evals e ON e.game_id = i.id
)

-- Step 8: roll up per rating bucket.
SELECT
  elo_bucket,
  COUNT(*) AS n_games,
  COUNT(*) FILTER (WHERE sustained) AS sustained,
  COUNT(*) FILTER (WHERE sustained
    AND ((min_sign > 0 AND result='1-0') OR (min_sign < 0 AND result='0-1'))) AS leader_wins,
  COUNT(*) FILTER (WHERE sustained AND result = '1/2-1/2') AS sus_draws,
  COUNT(*) FILTER (WHERE sustained
    AND ((min_sign > 0 AND result='0-1') OR (min_sign < 0 AND result='1-0'))) AS leader_loses,
  COUNT(*) FILTER (WHERE quiet) AS quiet,
  COUNT(*) FILTER (WHERE quiet AND result = '1/2-1/2') AS quiet_draws,
  COUNT(*) FILTER (WHERE quiet AND result <> '1/2-1/2') AS quiet_decisive
FROM flagged
GROUP BY elo_bucket
ORDER BY elo_bucket;
```

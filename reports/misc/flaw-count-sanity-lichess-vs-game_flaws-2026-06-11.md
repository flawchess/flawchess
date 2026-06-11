# Sanity check: lichess-reported flaws vs `game_flaws` — benchmark DB

**Date:** 2026-06-11
**DB:** benchmark (`localhost:5433`)
**Question:** Do the blunder/mistake counts in `game_flaws` (derived by
FlawChess) match the counts lichess reports directly on import
(`games.*_blunders` / `games.*_mistakes`)?

**Verdict:** Yes, they match well once compared on the right scope. `game_flaws`
in the benchmark DB stores flaws for **both players** (cohort user **and**
opponent), so the correct comparison is against lichess's **both-colors** totals.
On that basis FlawChess recovers **91–93%** of lichess's flaws per color and
severity (correlation **0.978** on blunders). The ~7–9% shortfall is **entirely
attributable to mate handling**: in games with no mate eval FlawChess reproduces
lichess exactly (100.2%), while the deliberately-flattened mate ES (Option B)
under-counts conversion errors inside won/mate endgames (the "checkmate ladder").
There is no over-detection. See "Root cause" below.

> **Correction note.** An earlier draft of this report claimed a 1.85× *over*-detection.
> That was a scope error on my part: I compared lichess's **user-color-only** counts
> against `game_flaws` rows that actually cover **both players**. Comparing like-for-like
> removes the discrepancy. The corrected analysis is below.

---

## Two corrections that drove the re-analysis

1. **Eval source is lichess, not FlawChess Stockfish.** Flaw detection runs off
   the per-ply `%eval` lichess supplies in the PGN (stored on
   `game_positions.eval_cp`). FlawChess's own Stockfish (`engine.py`, depth 15)
   only backfills **endgame-span entry plies** when lichess didn't provide them —
   it does **not** feed flaw classification. So flaws and lichess's own judgment
   come from the **same** evals. (`evals_completed_at` is therefore *not* a proxy
   for "has eval" — it marks "no pending entry-ply backfill", and was the wrong
   filter in the first draft.)

2. **`game_flaws` stores both players' flaws.** Each `(game_id, user_id)` row set
   contains flaws for the user **and** their opponent, with the offending player
   derived from `ply` parity against `games.user_color`. There is no color column
   on `game_flaws` (`ply`, `severity`, `tempo`, `phase`, `is_miss`, `is_lucky`,
   `fen`, `is_reversed`, `is_squandered`). This is required by the §5 benchmark
   "you − opponent" flaw-delta zones, which need the opponent's flaws too.

   Evidence — flaws split ~50/50 across ply parity regardless of user color (if
   only the user's moves were stored, one parity would be ~0):

   | user_color | even-ply flaws | odd-ply flaws |
   |---|---:|---:|
   | white | 939,950 | 962,480 |
   | black | 963,160 | 940,101 |

---

## How the two sources are defined

| Source | Where | Severities | Scope |
|---|---|---|---|
| **lichess** | `games.white_*` / `games.black_*` (`inaccuracies`, `mistakes`, `blunders`), from the imported lichess analysis | inaccuracy, mistake, blunder | per color |
| **FlawChess** | `game_flaws` rows (`flaws_service.py`) | `severity` 1=mistake, 2=blunder (**no inaccuracies** — D-03) | both players; color via ply parity |

Severity int mapping confirmed live: `game_flaws` holds only severity 1
(1,547,995) and 2 (2,257,696) — zero inaccuracies, by design.

Thresholds and win-model are deliberately lichess-aligned, which is *why* the
counts line up: `MISTAKE_DROP=0.10` / `BLUNDER_DROP=0.15` on the [0,1] expected-
score scale (lichess winningChances 0.20/0.30 halved), and the published lichess
sigmoid `LICHESS_K=0.00368208` (`eval_utils.py`).

---

## Finding 1 — correct-scope comparison (both colors)

Over all 641,855 lichess-analyzed games (`white_blunders IS NOT NULL`):

| Severity | lichess (both colors) | `game_flaws` | ratio (FC / lichess) | corr |
|---|---:|---:|---:|---:|
| Blunders | 2,433,236 | 2,257,696 | **0.928** | **0.978** |
| Mistakes | 1,693,532 | 1,547,995 | **0.914** | — |

Per-color (mapping odd ply → white, even ply → black):

| | lichess | `game_flaws` | FC / lichess |
|---|---:|---:|---:|
| White blunders | 1,216,121 | 1,126,365 | 92.6% |
| Black blunders | 1,217,115 | 1,131,331 | 92.9% |
| White mistakes | 842,711 | 776,216 | 92.1% |
| Black mistakes | 850,821 | 771,779 | 90.7% |

The shortfall is small, one-directional (FlawChess slightly under), and uniform
across both colors and both severities — the signature of a benign per-ply
divergence, not a systematic bias.

## Finding 2 — the wrong-scope artifact, for the record

Comparing lichess **user-color-only** against the **both-player** `game_flaws`
counts produces the spurious 1.85–1.88× "over-detection" and a mean of +1.1
mistakes / +1.6 blunders per game. The per-game correlation against user-color
(0.909) is markedly *worse* than against both-colors (0.978) — which is itself
the tell that the both-player scope is the right one.

---

## Root cause of the residual — mate handling (Option B), confirmed

The entire shortfall comes from **games containing mate evaluations**. It is the
deliberately-simplified mate handling, not coverage and not noise.

### The shortfall is 100% in mate-eval games

Splitting the 641,855 lichess-analyzed games by whether any ply carries a mate
eval (`game_positions.eval_mate IS NOT NULL`):

| | games | blunder recovery (FC/lichess) | mistake recovery |
|---|---:|---:|---:|
| **No mate eval** | 330,448 | **100.2%** | **100.2%** |
| **Has mate eval** | 311,407 | 87.9% | 85.0% |

In games with no mate eval, FlawChess reproduces lichess **exactly**. Every
missing flaw lives in a mate-eval game.

A from-scratch reconstruction of the classifier (consecutive-ply ES drops under
Option B, recomputed in SQL from `game_positions`) matches the stored
`game_flaws` counts to within 0.1% — so the classifier logic is faithful and the
divergence is purely in the inputs, i.e. how mate is scored.

### Dose-response with mate density

Recovery falls monotonically as a game gets more mate-laden (sample, all
lichess-analyzed games):

| mate plies in game | games | blunder recovery | mistake recovery |
|---|---:|---:|---:|
| 0 | 3,210 | 100.3% | 100.4% |
| 1–3 | 1,441 | 89.2% | 93.3% |
| 4–10 | 1,037 | 87.7% | 82.7% |
| 11+ | 751 | 86.9% | 74.9% |

### The mechanism — flattened mate ES suppresses conversion errors

`_ply_to_es` maps **every** mate to a flat ±1000 cp → ES **0.9755** (mating
side) / **0.0245** (mated side), regardless of mate distance. So the whole
won/mate region of a game collapses to a near-constant ES.

In messy won endgames the eval oscillates between "mate in N" and "winning but
not mate" (e.g. +5 to +7) as the winning side repeatedly reaches a forced mate
and throws it back. lichess scores each throw-away as a mistake/blunder
(win% 100% → ~88% is a punishable drop). Under Option B the same throw is only
`0.9755 − 0.885 ≈ 0.09` — below the 0.10 mistake threshold — so it is **not
counted**.

Worked example (benchmark game `1958407`, 3+0 blitz): Black is a queen up but
cannot convert, bouncing between `eval_mate −4/−5/−8` and `eval_cp ≈ −550` for
~30 plies. lichess flags **7 blunders**; FlawChess records **0**.

Two consequences explain the magnitude:

- The **cap value** (0.9755 vs lichess's true 1.0) is only a minor slice.
  Re-running the reconstruction with lichess's own full-mate convention
  (ES 1.0/0.0) recovers just ~14% of the missing blunders. The dominant effect
  is the **flattening of the entire mate region**, which zeroes the per-move
  swings that lichess still scores during mate conversion.
- Mistakes degrade worse than blunders in mate-heavy games (74.9% vs 86.9% at
  11+ mate plies) because these conversion throw-aways mostly land in the
  0.10–0.15 mistake band, exactly where the 0.0245 compression pushes them under
  the bar.

### Why this is acceptable (it was a deliberate trade-off)

Option B was chosen over Option A (hard 1.0/0.0 mate) precisely to **avoid
over-flagging** mate-adjacent moves as false blunders (RESEARCH Pitfall 3: a hard
mate score makes every transition between mate and a high-cp line look like a
huge swing). The cost is a known, one-directional **under-count of genuine
conversion errors inside won/mate endgames** — positions that are already
decided, where a missed-faster-mate matters little to the player's actual result.

Net: only **0.56%** of lichess-flaw games are dropped wholesale by the 90%
coverage gate; ply-level coverage is ~equal in mate vs non-mate games (98.2% vs
97.8%), so coverage is not the driver. The `game_flaws` data is sound for
benchmark use — the under-count is confined to the conversion phase of already-
won games and is internally consistent across the cohort.

---

## Implications

1. **No bug, no recompute.** The benchmark `game_flaws` table faithfully tracks
   lichess (≈92% recovery, 0.978 correlation). The §5 you-vs-opponent flaw-delta
   zones, which depend on both-player flaws, are built on sound data.
2. **Always compare on both-color scope.** Any future sanity check or UI copy
   must remember `game_flaws` holds both players' flaws; comparing against
   user-color lichess counts will falsely suggest ~1.85× over-detection.
3. **`evals_completed_at` is not an "is analyzed" gate.** Use eval coverage
   (`game_positions.eval_cp` non-null fraction ≥ 0.90) or the presence of lichess
   analysis columns (`white_blunders IS NOT NULL`), not `evals_completed_at`,
   to scope flaw-eligible games.

## Addendum (2026-06-11): mate ladder implemented on `feat/mate-ladder`

Lichess's MateAdvice ("mate ladder") was ported into the kernel
(`_classify_mate_ladder` in `flaws_service.py`, commit `8780d9c4`): transitions
touching a mate eval are now graded by lila's rules (MateCreated / MateLost with
cp-based downgrades at ±700/±999) instead of the Option-B ES drop, which is kept
only for the es_before/es_after payload. **No backfill has been run** — existing
`game_flaws` rows are unchanged; the keep-or-revert decision is pending.

A SQL reconstruction of the ladder over the benchmark DB (sample n=6,439
lichess-analyzed games) projects what a backfill would produce:

| | current (Option B) | with mate ladder |
|---|---:|---:|
| Blunder recovery vs lichess | 92.7% | **100.3%** |
| Mistake recovery vs lichess | 91.1% | **101.4%** |

Per mate-density bucket, ladder blunder recovery is 100.1–100.8% with per-game
exact-match 96.7–99.4%, within-±2 at 99.9–100%, and correlation 0.998–1.000 —
i.e. essentially full lichess parity, including in the mate-heavy games where
Option B missed up to 25% of mistakes. The residual ~1–3% mistake over-count in
mate-heavy games is the remaining mate-pipeline noise, well inside
`SANITY_TOLERANCE`.

## Reproduction

```sql
-- Correct-scope (both colors) sanity check on the benchmark DB
WITH gf AS (
  SELECT game_id, user_id,
    count(*) FILTER (WHERE severity=2) AS gf_b,
    count(*) FILTER (WHERE severity=1) AS gf_m
  FROM game_flaws GROUP BY game_id, user_id
)
SELECT
  SUM(g.white_blunders + g.black_blunders) AS li_blunders_both,
  SUM(COALESCE(gf.gf_b,0))                 AS fc_blunders,
  SUM(g.white_mistakes + g.black_mistakes) AS li_mistakes_both,
  SUM(COALESCE(gf.gf_m,0))                 AS fc_mistakes,
  ROUND(corr(COALESCE(gf.gf_b,0), g.white_blunders + g.black_blunders)::numeric,3) AS corr_blunders
FROM games g
LEFT JOIN gf ON gf.game_id=g.id AND gf.user_id=g.user_id
WHERE g.white_blunders IS NOT NULL;
```

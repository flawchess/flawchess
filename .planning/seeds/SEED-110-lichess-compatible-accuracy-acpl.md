---
id: SEED-110
status: dormant
planted: 2026-07-16
planted_during: v2.4
trigger_when: next analysis/stats-related phase, or alongside a backfill phase (e.g. near Phase 176) — recommend promoting to its own phase
scope: medium
related: SEED-109 (lichess-eval full-analyze — changes eval-source coverage), SEED-043 (lichess best-move/PV backfill)
---

# SEED-110: Lichess-compatible accuracy & ACPL (computed columns)

## Why This Matters

We want per-game accuracy and ACPL for **every** analyzed game, computed with
**one consistent methodology** so games are comparable across platforms and time.

Today the two metrics come from whichever platform provided them, with a gap on
each side:

- `white_accuracy` / `black_accuracy` — populated **only for chess.com** analyzed
  games, using **chess.com's** accuracy formula (not lichess's). NULL for lichess
  and unanalyzed games.
- `white_acpl` / `black_acpl` (+ `*_inaccuracies` / `*_mistakes` / `*_blunders`)
  — populated **only from lichess** imports that arrived pre-analyzed. NULL for
  chess.com and self-analyzed games.

So neither platform gives us both metrics, the accuracy that exists uses an
incompatible formula, and self-analyzed lichess games get nothing. We can't do
apples-to-apples accuracy/ACPL analytics across the game history.

## The Idea

Compute accuracy and ACPL ourselves from the per-ply evals already stored in
`game_positions.eval_cp` / `eval_mate`, using **lichess's exact formulas**, into
**four new dedicated columns** — leaving the existing platform-provided columns
untouched as a separate comparison signal.

### Key insight: eval source is already per-game correct

`game_positions.eval_cp` comes from whatever analyzed the game:
- lichess `%eval` for lichess imports (`lichess_evals_at IS NOT NULL`),
- our Stockfish for chess.com / self-analyzed games (`full_evals_completed_at`).

So applying one uniform formula over those evals **reproduces lichess's own
accuracy for lichess games** (validation surface vs the imported acpl), and gives
our-Stockfish-through-the-lichess-formula for chess.com games. Uniform formula,
per-ply eval from the source that analyzed the game — the best consistency
achievable.

## Locked Design Decisions

1. **Four new columns** on `games`, exact names TBD (e.g.
   `white_accuracy_computed` / `black_accuracy_computed` /
   `white_acpl_computed` / `black_acpl_computed`). Filled uniformly for every
   analyzed game.
2. **Do not overwrite** the existing chess.com accuracy or lichess acpl columns —
   keep them as a separate signal so we can compare "our computed value" vs "what
   the platform reported" (our lichess-game numbers should closely track
   lichess's own → validation).
3. **Complete-sequence gate**: only compute when the per-ply eval sequence for the
   game is complete (gate on `is_analyzed` / no eval holes). The accuracy
   aggregation uses a **sliding volatility window**, so a hole silently distorts
   the weights. Incomplete → leave the four columns NULL.
4. **Single Python path, no SQL backfill**. Write one Python function; use it at
   the live hook (when full analysis completes) AND in a `scripts/backfill_*.py`
   that iterates analyzed games. ACPL alone is SQL-doable, but the accuracy
   aggregation (harmonic mean + windowed stddev + edge padding) is impractical in
   SQL and easy to get subtly wrong. One code path guarantees backfill and
   go-forward values are computed identically.

## Exact Lichess Formulas (confirmed from source, 2026-07-16)

Sources:
- `scalachess/core/src/main/scala/eval.scala`
- `lila/modules/analyse/src/main/AccuracyPercent.scala`
- lila PR #11148 (the `-0.00368208` constant)

### 1. Win% from centipawns

```
winningChances(cp) = clamp(2 / (1 + exp(-0.00368208 * cp)) - 1, -1, +1)   # [-1,+1]
Win%(cp)           = 50 + 50 * winningChances(cp_ceiled)                   # [0,100]
```
- `cp` is **ceiled to ±1000** (`Cp.CEILING = 1000`) BEFORE the sigmoid.
- **Mate → cp**: maps to `±1000` by sign (`ceilingWithSignum`).

### 2. Per-move accuracy (from the Win% drop)

```
if after >= before:
    100
else:
    clamp(103.1668100711649 * exp(-0.04354415386753951 * (before - after))
          - 3.166924740191411 + 1,                                        # note the +1
          0, 100)
```
- `before` / `after` are Win% from the **moving player's perspective** (evals
  inverted for Black).
- The trailing **`+1` "uncertainty bonus"** is real — easy to miss.

### 3. Game-level aggregation (NOT a plain mean)

```
winPercents = [Win%(Cp.initial = 15)] ++ [Win%(cp) for each ply]
windowSize  = clamp(nMoves // 10, 2, 8)
windows     = [take(windowSize)] * (windowSize - 2) ++ sliding(winPercents, windowSize)
weight_i    = clamp(population_stddev(window_i), 0.5, 12)     # stddev of raw Win% values
```
Then slide pairs `(prev, next)` over `winPercents`, assign each move to a color by
ply parity vs `startColor`, compute per-move accuracy weighted by `weight_i`.
Per color:
```
game_accuracy = ( weightedMean(accuracies, weights) + harmonicMean(accuracies) ) / 2
```
- Sequence is **seeded with the initial position at 15cp**; the start is padded
  with `windowSize - 2` copies of the first window so every move gets a weight.

### 4. ACPL

```
per_move_loss = max(0, before_cp - after_cp)   # mover's POV, evals capped ±1000
ACPL          = arithmetic mean of per_move_loss for that color
```
- Cap = ±1000 (`Cp.CEILING`, same constant). Plain arithmetic mean (not the
  volatility/harmonic aggregation used for accuracy).

## Open Implementation Questions (for the plan phase)

- **Where the live hook fires**: natural spot is when the full-eval sequence
  completes (`full_evals_completed_at` set by the drain, or `lichess_evals_at` at
  import). Confirm the exact seam and that the sequence is guaranteed complete
  there.
- **Eval sign convention**: verify how `game_positions.eval_cp` is signed and the
  "post-move shift" (memory `atomic_eval_submit_incremental_lease`: row P may hold
  the eval of position P+1) so `before`/`after` map to the right plies.
- **Terminal ply handling**: last ply / checkmate eval, and games with 0–1 moves.
- **Exact column names + migration** (SMALLINT for acpl matching existing
  `white_acpl`; REAL for accuracy matching `white_accuracy`).
- **Backfill scale**: ~718k games in prod (per SEED-109); batch + `--db` flag per
  the `scripts/backfill_*.py` convention.

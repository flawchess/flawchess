# Bot calibration — what the 2026-07-12 harness run actually showed

**Date:** 2026-07-13
**Source:** `/gsd-explore` session reading `reports/data/calibration-harness-2026-07-12T16-34-46-551Z*.tsv`
**Why this note exists:** three load-bearing findings that are not visible in the TSVs themselves.
SEED-101/102/103/104 all depend on them.

## The run

9 cells (bot_elo 1100/1500/1900 × blend 0/0.5/1), 10 games per (cell, anchor), maia-argmax
anchors only. 4.85h wall clock, ~400 games, ~82 games/hr at `--stockfish-procs 4`.

| bot_elo | blend 0 | blend 0.5 | blend 1 |
|---|---|---|---|
| 1100 | 878 | 1336 | 1712 |
| 1500 | 980 | 1938 | 2092 |
| 1900 | 1480 | 2308 | 2506 |

All 9 cells report `any_clamped = true`. These are bounds, not measurements.

---

## Finding 1 — `blend` is a regime dispatch, not a mix (this is code fact, not inference)

`selectBotMove.ts:113-146` dispatches three ways:

- **`blend === 0`** — one Maia policy call, **no search at all**, sample the raw policy (`:113-118`).
- **`0 < blend < 1`** — full MCTS, then softmax-sample **Stockfish-derived** `practicalScore`
  at `tau = TAU_MAX * (1 - blend)`, `TAU_MAX = 0.1` (`:140-145`).
- **`blend === 1`** — same search, deterministic argmax (`:134-138`).

The instant `blend` exceeds 0, **Maia stops choosing the move**. It survives only as priors
shaping tree expansion; the sampling weights are pure Stockfish expected score
(`botSampling.ts:81-85`). There is no "half human, half Stockfish" anywhere on the axis, and
there is a genuine discontinuity at 0.

Consequence: the 980 → 1938 jump at bot_elo 1500 is a **cliff** (no-search → full MCTS) bundled
with a mild temperature change, not a ramp you can interpolate into. Any attempt to read a
"sweet spot" off a linear interpolation between blend 0 and 0.5 is invalid.

**Open (measurable) question, NOT established:** whether the *interior* of (0, 1] is a usable
playstyle axis at all. Within the search regime, blend only sharpens a softmax, and going
0.5 → 1 bought just +154 / +198 / +375 ELO. Two measurements settle it, both in SEED-102:
a **blend ≈ 0.05 cell** (separates cliff height from temperature effect) and a **Maia-agreement
rate** per cell (the operational definition of "how human is this bot").

Do not act on a mixture redesign before those land — the theory is read off the formula, not
off games.

## Finding 2 — Maia rung ELO is not human ELO, and the error is not a constant offset

Real lichess ratings of the official Maia bots (argmax, no search — exactly like our anchors),
over 200k–575k games against actual humans:

| model | nominal | lichess blitz | error |
|---|---|---|---|
| maia1 | 1100 | **1373** (RD 45 — converged) | **+273** |
| maia5 | 1500 | **1507** | +7 |
| maia9 | 1900 | **1611** | **−289** |

The ladder is **compressed ~3.3x**: 800 nominal points of spread buy 238 real blitz points
(slope ≈ 0.30; rapid is worse at 0.21). Mechanism, and it applies to Maia-3 too:

- **Low end overperforms** — argmax truncates the blunder tail, and blundering is what makes a
  1100 player 1100.
- **High end underperforms** — no search. A real 1900 blitz player calculates; policy-argmax
  pattern-matches the modal 1900 move and hits a tactical ceiling.

Caveat: those bots are **Maia-1** (per-rung models). We run **Maia-3** ("Chessformer",
ELO-conditioned single model, `maiaEncoding.ts:2`). So the magnitude is a proxy, not a
measurement of our ladder — but the mechanism is structural, so the *direction* is certain.
Measuring our own ladder's internal spacing is SEED-101.

**The part that actually breaks the harness:** our anchors are search-less, and the thing we
are measuring is a search knob. That bias is **correlated with the treatment** and does not
cancel. A blend>0 bot with a real MCTS crushes tactically-blind anchors far more easily than
it would crush humans who calculate — so the blend axis looks like a bigger strength dial than
it is, inflated specifically at the blend>0 end.

Corollary: **relabeling the anchors is necessary but not sufficient.** Strength is not
transitive across playing styles. Even perfectly-labeled search-less anchors would still let a
searching bot exploit a blind spot humans don't have. The only honest absolute number comes
from playing humans (SEED-103).

## Finding 3 — the anchor window is centered on `bot_elo`, which is why every cell clamped

`ANCHOR_ELO_WINDOW = 400` brackets anchors around **`bot_elo`** — but a cell's actual strength
sits up to 600 ELO away from its `bot_elo`. The harness therefore prunes exactly the anchors
that would be informative, then sweeps every anchor it does play.

Directly visible in the TSV:

```
1500  1  maia2100  ...  out_of_window     ← |2100 − 1500| = 600 > 400
```

That cell's bot **plays at 2092**. `maia2100` was the ideal anchor and it was pruned. Same at
bot_elo 1900 / blend 1: bot plays 2506, strongest in-window anchor was `maia2300`, swept 10–0.

Fix: center the window on the cell's **expected strength**, not on `bot_elo`. Priors for that
now exist (table above). SEED-102 uses a locate-then-measure two-pass instead.

## Finding 4 (minor) — 10 games/cell is ±110 ELO and it shows

At bot_elo 1100 / blend 0 the bot scored 0.45 vs maia900 but 0.25 vs maia700, and 0.40 vs
maia1300 but 0.10 vs maia1100. Non-monotone in both places. That is noise, not signal. Near
score 0.5, SE ≈ 695 × 0.5/√N ELO: N=10 → ±110, N=24 → ±71, and combining ~4 anchors halves it.
24–30 games per (cell, anchor) is the floor for anything a lookup table gets built on.

## The resulting architecture

**Anchors calibrate each other (SEED-101) → the bot is rated against them on that internal
scale (SEED-102) → lichess corrects the whole scale to human ELO once (SEED-103) → invert the
corrected surface into the shipping lookup table (SEED-104).**

The offline harness produces *shape*. It does not get to name the units. Asking it for a human
ELO number is a job it structurally cannot do.

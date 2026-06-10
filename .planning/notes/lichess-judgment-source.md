---
title: Lichess mistake-judgment — source-grounded reference (lila / scalachess)
date: 2026-06-05
context: SEED-036 (Library) Q-CLASS — reproducing Lichess inaccuracy/mistake/blunder
  classification from stored per-ply evals. Also feeds SEED-037 (Train) move grading.
source_verified: lila modules/tree/src/main/Advice.scala; scalachess core/src/main/scala/eval.scala
---

# Lichess mistake-judgment — source reference

How Lichess (`lila` + `scalachess`) classifies inaccuracy / mistake / blunder, verified
against source so we don't re-derive it. The one fact that changes our spec is the
**scale**: Lichess judges on `winningChances` **[−1, +1]**, while our
`eval_cp_to_expected_score` returns **[0, 1]**, so every Lichess drop threshold **halves**
on our scale.

## 1. Judgment thresholds — `winningChances` scale [−1, +1]

`lila` `modules/tree/src/main/Advice.scala` (moved from `modules/analyse/`):

```scala
private val winningChanceJudgements = List(
  .3 -> Advice.Judgement.Blunder,
  .2 -> Advice.Judgement.Mistake,
  .1 -> Advice.Judgement.Inaccuracy)
...
prevWinningChances    = WinPercent.winningChances(cp)
currentWinningChances = WinPercent.winningChances(infoCp)
delta = (currentWinningChances - prevWinningChances).pipe(d => info.color.fold(-d, d))
judgement <- winningChanceJudgements.find((d, _) => d <= delta)._2F
```

- Cutoffs **0.10 / 0.20 / 0.30** are on `winningChances`, the **[−1, +1]** scale (NOT win-%
  points, NOT a [0,1] fraction).
- `delta` is **side-to-move signed** (`info.color.fold(-d, d)`) — a positive delta is a drop
  for the player who just moved. Classify each move from the **mover's** POV.
- Highest matching band wins (`find` walks blunder→mistake→inaccuracy).

## 2. Win% / winning-chances formula + clamp

`scalachess` `core/src/main/scala/eval.scala`:

```scala
def winningChances(cp: Eval.Cp) = {
  val MULTIPLIER = -0.00368208
  2 / (1 + Math.exp(MULTIPLIER * cp.value)) - 1
}.atLeast(-1).atMost(+1)                                  // [-1, +1]

def fromCentiPawns(cp: Eval.Cp) =
  WinPercent: 50 + 50 * winningChances(cp.ceiled)          // [0, 100], ceil at +-1000
```

- `winningChances(cp) = 2/(1+exp(-0.00368208·cp)) − 1`, range [−1, +1].
- **Judgment path passes RAW, un-ceiled cp** (`Info.cp`). The only clamp there is the
  output `.atLeast(-1).atMost(+1)`, a near-no-op. The ±1000 cp **`.ceiled`** applies only to
  the *displayed* `fromCentiPawns` win% / accuracy, **not** to judgment.
- Our `eval_utils.py` sigmoid `1/(1+exp(-0.00368208·cp))` is exactly `(winningChances+1)/2`.
  So **our_ES = (winningChances + 1) / 2** and **Δour_ES = ΔwinningChances / 2**.

### ⇒ Our [0,1] thresholds (halved)

| Class | Lichess Δ (winningChances) | **Our Δ (ES [0,1])** | ≈ cp swing near equality |
|---|---|---|---|
| Inaccuracy | 0.10 | **0.05** | ~55 cp |
| Mistake | 0.20 | **0.10** | ~110 cp |
| Blunder | 0.30 | **0.15** | ~165 cp |

## 3. Position guard — NONE

`CpAdvice` flags purely on `delta` magnitude vs the thresholds. No before/after
absolute-strength guard; an already-lost position still flags a blunder if the drop ≥
threshold. The sigmoid's saturation at the extremes is the *only* suppression mechanism.
⇒ We add **no** `ES_before < 0.85` gate and **no** losing-side floor.

## 4. Mate handling — separate `MateAdvice` ladder

`Advice.apply = CpAdvice.orElse(MateAdvice)` — sigmoid path first; mate path only when a
mate score is involved. For win% *conversion*, `fromMate(mate) = fromCentiPawns(ceiling ·
signum)` ⇒ mate maps to **±1000 cp ⇒ win% ≈ 99.64 / 0.36** (NOT exactly 100/0).

For cp↔mate **transitions**, `MateAdvice` uses its own ladder keyed on the **non-mate cp
endpoint** (distance-to-mate ignored):

- **MateCreated** (you walked into a forced mate against you), keyed on `prevCp` (your
  eval before, negative = you were already worse):
  - `prevCp < −999` → **Inaccuracy** (you were lost anyway)
  - `−999 ≤ prevCp < −700` → **Mistake**
  - `prevCp ≥ −700` → **Blunder** (converted a playable position into a forced loss)
- **MateLost** (you squandered your own forced mate), symmetric on `currentCp` (your eval
  after, positive = you're still better):
  - `currentCp > 999` → **Inaccuracy** (blew the mate but still totally winning)
  - `700 < currentCp ≤ 999` → **Mistake**
  - `currentCp ≤ 700` → **Blunder** (threw away the win with no decisive edge to show)
- **Mate persists** (mate→mate, same side) → no judgment (mate-in-3 → mate-in-8 not flagged).
- **Mate flips sides** is the extreme corner — verify exact handling from source before
  relying on it.

Principle: the worse you already were (MateCreated) or the better you remain (MateLost),
the milder the verdict — recovering the nuance the saturated sigmoid loses.

> Boundary details (`<` vs `≤`, mate-flip) are reconstructed from a research summary, not
> verbatim source. Lift the exact `MateAdvice` block from `Advice.scala` before implementing
> Option A.

## 5. Pipeline subtleties

- Perspective: side-to-move signed (see §1).
- `CpAdvice.orElse(MateAdvice)` — cp-vs-cp first, mate path only on mate scores.
- **No** only-move exception, **no** min-depth, **no** opening-book skip *in the judgment
  logic* (book/depth handled upstream in eval generation).

## Verdict for FlawChess

A `1/(1+exp(-0.00368208·cp))` [0,1] sigmoid with no clamp and mate→1.0/0.0 does **NOT**
reproduce Lichess. Minimal deltas:

1. **Scale:** use drop cutoffs **0.15 / 0.10 / 0.05** (blunder/mistake/inaccuracy) on our
   [0,1] ES delta.
2. **Mate:** map mate → ±1000 cp (ES ≈ 0.9964 / 0.0036), **not** 1.0/0.0. SEED-036 v1 takes
   **Option B** (this mapping + normal sigmoid thresholds, skipping the `MateAdvice` ladder)
   and accepts the documented under-flagging of mate transitions. The ladder above is the
   Option-A upgrade path.
3. **Clamp:** do **not** pre-clamp cp for judgment (raw cp into the sigmoid); ±1000 ceil is
   display-only. Our un-clamped `eval_utils.py` is therefore correct as-is for cp judgments.

## Appendix — criticisms of chess.com / lichess classification → FlawChess tags (2026-06-05)

Researched the most frequent substantive criticisms of both systems to mine for additional
*tags* (severity stays Lichess-pure; tags layer on top). Prioritized by frequency + instructive
value, not exhaustiveness.

**Top criticisms — chess.com:** (1) **"Brilliant" is overused / not actually brilliant** —
the loudest complaint; the sacrifice gate fires on forced recaptures and obvious-but-good
moves, and rating-relative thresholds offend purists. (2) **Non-determinism** — same game
re-analyzed gives different labels/accuracies across depths/runs. (3) **"Miss" is confusing**
— users can't separate it from Mistake/Blunder. (4) **Gamification over instruction** (weakly
citable sentiment).

**Top criticisms — lichess:** (1) **Too coarse (3 labels)** — no positive feedback, no
"only move," no thematic grouping (most-requested improvement). (2) **No "missed win"/
missed-tactic flag.** (3) **Already-decided floor/ceiling** — below ~30% win chance you
can't "blunder," and in a won position you can hang a queen / miss mate-in-1 with no flag;
the single most *substantive* lichess gap. (4) **Cloud/depth dependence.**

**Cross-cutting gaps coaches actually want:** recurring/thematic mistakes across games (the
#1 "real training signal"); time-pressure attribution; "you got away with it" (unpunished
blunders); tying mistakes to game result and to difficulty of finding the move.

**Candidate tags, ranked by value × cheapness** (D = differentiated vs chess.com/lichess,
TS = table-stakes catch-up):

| Tag | Data dep | D/TS | Status in SEED-036 |
|-----|----------|------|--------------------|
| `miss` (missed win/tactic) | eval-only | TS | **adopted** (earlier) |
| `from-winning` | eval-only | D | **adopted** (earlier) |
| `unpunished` ("got away with it") | eval-only | D | **adopted** |
| `result-changing` (flipped outcome) | eval + result | D | **adopted** |
| `time-pressure` | eval + clocks | D | **adopted** |
| `hasty` (unforced rush) | eval + clocks | D | **adopted** |
| `knowledge-gap` (slow + still wrong) | eval + clocks | D | **adopted** |
| `phase` | stored column | TS | **adopted** |
| already-decided suppressor / material-swing overlay | eval (+material) | TS/D | **deferred** — `result-changing` is the v1 catch |
| recurring-theme clustering | eval-only (+motif to name) | D | **deferred** — stats/insights layer, not a per-move tag |
| `only-move` / forced | needs 2nd-best eval = engine call (NOT eval-only for us) | TS | **deferred** — on-demand enrichment only |
| "Brilliant" positive label | engine best-move + 2nd-best | TS-ish | **skipped** — expensive, off-brand, most-mocked |
| tactical vs positional motif | motif detection | D | **deferred** — expensive, low ROI |

Key correction to the generic research: **`only-move` is NOT eval-only for FlawChess** —
detecting it needs the second-best move's eval, which stored lichess `%eval` does not provide
(same limitation that broke the original "Missed Tactic" rule). It requires the best-move
endpoint, so it's on-demand enrichment, not a bulk tag.

**Skeptical note:** the only pure *entertainment* gripe is "Brilliant feels bad" — everything
else above is a genuine instructive gap. Positive labeling is optional polish at best, and a
sloppy version inherits chess.com's most-ridiculed flaw, so FlawChess skips it.

Criticism-source threads (community sentiment where not citable):
chess.com brilliant-overuse forums, "what is a Miss" forums, "inconsistent analyses" forum;
lichess "better classification" + "what constitutes an inaccuracy" feedback threads.

## Sources

- lila `modules/tree/src/main/Advice.scala` — https://github.com/lichess-org/lila/blob/master/modules/tree/src/main/Advice.scala
- scalachess `core/src/main/scala/eval.scala` — https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/eval.scala
- lila `modules/analyse/src/main/AccuracyPercent.scala` (accuracy %, distinct from judgment)
- lila PR #11148 — origin of the −0.00368208 multiplier
- Lichess accuracy page — https://lichess.org/page/accuracy

---
spike: 007
idea: facepalm-puzzle-validation
name: facepalm-vs-puzzle-ratings
type: standard
validates: "Given a rating-stratified sample of Lichess puzzles read as blunders (loss view) and as misses (miss view), when scored with the shipped facepalm model, then the score ranks them against puzzle rating with Spearman <= -0.30 on short non-mate puzzles"
verdict: PARTIAL
related: []
tags: [facepalm, maia, lichess-puzzles, seed-261117-hfb]
---

# Spike 007: Facepalm score vs Lichess puzzle ratings

Step 1 of `SEED-261117-hfb`. Run 2026-11-17 against the model shipped in release #486
(`FACEPALM_MATERIAL_INPUT = "decaying_mean"`, prod commit `91c0c9b92`).

## What This Validates

Given 26,464 Lichess puzzles with a settled rating, sampled evenly over 100-point rating bins,
when each is scored with the app's own `facepalm_score` under `FACEPALM_MODEL`, then a high
score (obvious) goes with a low puzzle rating (easy).

Criterion, fixed before the run: Spearman <= -0.30 between the composite score and the rating
on the primary slice (non-mate puzzles with at most 2 solver moves), in both views.

## Method

- Sample: the 2026-06 puzzle dump, `RatingDeviation <= 80` and `NbPlays >= 200`, a seeded
  reservoir of 1,250 puzzles per rating bin from 500 to 2900 (the bins above 2700 are nearly
  empty, so 26,464 instead of 30,000).
- Loss view (the puzzle's blunder is the user's blunder): `line_facts(pre, Moves[0], Moves[1:])`,
  Maia's probability of the blunder, the reply spread one ply later.
- Miss view (the solver's first move is the best move the user missed):
  `best_line_facts(post, Moves[1:])` and Maia's probability of `Moves[1]`. A puzzle has no
  played move on the solver's side, so the played line is a neutral quiet move (material 0 at
  every depth) and the played probability a constant.
- Maia at a fixed Elo of 1500 for every puzzle; 1100 and 1900 on a 6,000-puzzle subsample.
- Rank correlations are Spearman. "Length partialled out" regresses the rank of the number of
  solver moves out of both sides.
- Signs: every term should correlate negatively with the rating, except the reply spread
  (positive).

## How to Run

```bash
D=.planning/spikes/007-facepalm-vs-puzzle-ratings
# Features (Maia, about 70 minutes on a loaded 16-core machine); the tables are committed.
uv run --group maia-inference python $D/build_features.py \
    --puzzle-path ~/Downloads/lichess_db_puzzle.csv.zst --elo 1500 \
    --out $D/features-elo1500.tsv.gz
# Analysis (no Maia, no database, a few seconds)
uv run python $D/analyze.py --features $D/features-elo1500.tsv.gz \
    --sensitivity $D/features-elo1100.tsv.gz $D/features-elo1900.tsv.gz \
    --markdown $D/results.md > $D/results.json
```

## Results

Verdict: **PARTIAL**. The miss view passes clearly, the loss view fails as shipped. Full tables:
`results.md`.

### Composite score against the rating

| slice | n | loss view | loss view, played prob fixed | miss view |
|---|---|---|---|---|
| primary: non-mate, <= 2 solver moves | 9,072 | -0.237 | -0.321 | -0.567 |
| all | 26,464 | -0.618 | -0.666 | -0.642 |
| all, length partialled out | 26,464 | -0.296 | -0.362 | -0.508 |
| non-mate | 18,839 | -0.299 | -0.374 | -0.453 |
| mate | 7,625 | -0.444 | -0.528 | -0.555 |

The loss view scores 72% of the puzzles (63% of the primary slice), the miss view all of them.

### Findings

1. **Miss side works.** The missed term plus the best-move probability rank puzzles at -0.57 on
   the primary slice and -0.51 overall once length is removed.
2. **The loss side fails the criterion as shipped (-0.24)** and passes narrowly (-0.32) with the
   played probability held constant. The played-probability term cannot be tested on puzzles
   (its own correlation with the rating is -0.03), so here it is pure noise in the composite.
   That says nothing about its value on real blunders.
3. **The loss view cannot score 39% of non-mate puzzles** (7,386 of 18,839). Their line shows
   no material loss under the app's rules, so the model treats them as pure misses and needs
   the blunderer's best-move probability, which a puzzle does not have. These puzzles are
   harder (mean rating 1972 vs 1701) and lean to endgame, advanced-pawn, defensive-move and
   quiet-move themes. `line_material` counts captures only, so a promotion is not a loss.
4. **Probability of the punishing move beats reply spread everywhere.** Overall -0.49 vs +0.37,
   primary slice -0.45 vs +0.25, non-mate -0.34 vs +0.17. The two are strongly related
   (Spearman -0.77), and spread adds nothing once the probability is in: a cross-validated
   linear model of the rating reaches R^2 0.476 with loss + probability, 0.477 with spread
   added, and 0.430 with loss + spread (the shipped pair).
5. **Decaying mean holds up.** For the loss term with length partialled out: decaying mean
   -0.41, first stable -0.35, depth 3 -0.34. On 3-move puzzles it is the only input with signal
   (-0.25 vs 0.00 and -0.02). On the primary slice depth 3 is slightly ahead (-0.40 vs -0.37).
   For the missed term depth 3 is blind on short puzzles (the line ends before depth 3), which
   is a puzzle artefact: stored engine lines are longer.
6. **Solution length is the largest single factor** (Spearman +0.61 with the rating, R^2 0.38
   alone). Raw correlations over all puzzles overstate the terms by roughly a factor of two.
   Signal is concentrated in 2-move puzzles (-0.41 loss view, -0.63 miss view) and fades at 3
   moves (-0.10, -0.33) and at 4 or more (-0.02, -0.18). All 1-move puzzles in the sample are
   mates in 1, where the material terms are constant.
7. **Elo choice does not matter for the conclusions.** At 1100 / 1500 / 1900 the loss-view
   composite is -0.60 / -0.61 / -0.63 and the miss view -0.62 / -0.64 / -0.66. Reply spread
   moves most (0.31 / 0.37 / 0.41). No need to fetch player ratings from the game links.
8. **A small linear model on storable features recovers about half of the rating variance**
   on this sample: R^2 0.49 (Spearman 0.70) from the four shipped terms, 0.58 (0.76) with
   length and a few cheap extras, RMSE 392 against a rating SD of 607. These figures are on a
   sample that is uniform over rating, so they are not comparable with published results on
   the natural distribution.

## Signal for the next steps

- Step 2: test Maia's probability of the punishing move as a replacement for reply spread on
  the owner's labels. This spike is the strongest evidence for it so far. It is one stored
  float per flaw from the policy call that already produces the spread, but it needs a backfill.
- Step 2: keep the decaying mean. No reason here to reopen depth 3 or first stable.
- Open: whether the 39% no-material-loss share has a counterpart in real blunders (promotions,
  quiet wins). If it does, material-only loss facts under-rank them.
- Step 3 (predicted puzzle difficulty as a model input) has signal to work with, but any
  predictor must not lean on solution length: a stored engine line has no natural end, so
  length is not available for a real blunder.

## Limits

- The rating measures the whole solution, the score mostly reads the first reply and the first
  plies. That is the main reason signal fades with length.
- Puzzles have one winning move and a clear win; real blunders often have neither.
- The sample is uniform over rating, not the natural puzzle distribution.
- The miss view's neutral played move is a convention of this spike, not an app rule.

## Investigation Trail

1. Smoke run on 300 puzzles: the app's line-material rules replay puzzle lines without changes
   (one odd-looking row, `S4kjG`, turned out to be the quiet-square rule working as designed).
2. Full run at Elo 1500 (26,464 puzzles, none skipped), then 1100 and 1900 on 6,000 puzzles.
3. First reading: loss-view composite far below its own loss term on the primary slice. Added
   the composite with the played probability held constant, which closed most of the gap.
4. The 28% unscored share in the loss view led to the no-material-loss finding (themes checked).
5. Added the feature-set comparisons (spread vs probability of the punishing move, alone and
   next to the loss term) to settle whether the two carry separate information.

---
id: SEED-261117-hfb
status: dormant
planted: 2026-11-17
planted_during: after Phase 256 (facepalm refit, material aggregated over depths); owner review of the model with a literature check
trigger_when: the next facepalm refit, or any phase that changes the score's shape (material input, spread form, new stored Maia facts). Run step 1 (validation) before the next shape decision is made on the owner's labels.
scope: step 1 (validation spike) is small, no schema change and no backfill. Step 2 (shape choices, new features) is small to medium. Step 3 (predicted puzzle difficulty as a model input) is medium to large, with new stored Maia facts and a backfill.
---

# SEED-261117-hfb: Validate and improve the facepalm score against Lichess puzzle ratings

Puzzle framing: a pure miss is a puzzle the player failed, and a material-losing blunder is a puzzle
handed to the opponent. Every Lichess puzzle is a real-game blunder (`Moves[0]`) followed by its
punishment (`Moves[1:]`), with a human-measured difficulty. That makes the puzzle database a large,
independent label set for the question the facepalm score asks: how visible was it?

## Why This Matters

The shipped model (`app/services/facepalm_score.py`, constants in `app/services/blunder_check_rules.py`)
is a 6-coefficient logistic regression fitted on 261 owner labels
(`reports/blunder-check/facepalm-fit-2026-11-16.md`). Its limits are in the validation, not the form:

- Cross-validation folds are a random permutation of rows (`scripts/blunder_check/fit_facepalm.py`,
  `cv_predictions`), but the labels came in 8 sets, each sampled around what an earlier model passed.
  CV AUC is 0.90; fitting on sets 1-7 and scoring set 8 gives 0.82.
- Shape choices are ties within noise. Decaying mean beat depth 3 by 0.023 in CV and lost by 0.014 on
  set 8; with 261 rows the AUC standard error is about 0.02.
- Reply spread is an indirect proxy for "the punishment is obvious": it measures how concentrated the
  opponent's policy is, not whether it concentrates on the refutation.
- The score is a ranking, not a probability, so no copy may say "x% of peers would have seen this".

Lichess puzzle ratings address all four: millions of labels, no label-set selection, a direct measure
of how hard a punishing line is to find, and a rating scale that turns into a solve probability.

The puzzle condition also fits the target. A solver knows something is there, so puzzle difficulty
answers "would you have seen it had you looked", which is the normative question the owner's labels
encode. Maia answers the other question (what players do in a game when nobody tells them to look).

## What the data offers

- CC0 dump at database.lichess.org/#puzzles. Columns include `Rating` (Glicko-2 from solver attempts),
  `RatingDeviation`, `NbPlays`, `Popularity`, `Themes`, `GameUrl`.
- Easy items exist: themes `hangingPiece`, `oneMove`, `short`, `mateIn1`.
  `app/data/sharp_filler_puzzles.csv` already holds hanging-piece puzzles rated about 1000 to 1400.
- Format fit: the published FEN is the position before the blunder, so
  `line_facts(pre_board, Moves[0], " ".join(Moves[1:]))` (`app/services/line_material.py`) computes the
  facepalm facts on a puzzle with existing code. `scripts/select_tagger_fixtures.py` already reads the
  dump from a local `.csv.zst` path.

## Proposed steps

Step 1 was run on 2026-11-17 as spike 007 (`.planning/spikes/007-facepalm-vs-puzzle-ratings/`,
verdict PARTIAL): the miss side ranks puzzles well (Spearman -0.57 on short non-mate puzzles),
the loss side fails as shipped (-0.24), Maia's probability of the punishing move beats reply
spread, and the decaying mean holds up. Steps 2 and 3 remain open.

### 1. Validate (spike, do first)

Compute the shipped score's facts on a rating-stratified sample (about 30k puzzles with a settled
rating) and report the rank correlation between score and puzzle rating. Read each puzzle both ways:

- as a loss (blunderer's view): tests the loss and spread terms;
- as a miss (solver's view, `Moves[1]` is the best move): tests the missed and best-move-probability
  terms.

It cannot test the played-probability term: puzzle rating says how hard the punishment is to find, not
how tempting the blunder was.

### 2. Improve

- Settle the shape choices on puzzles instead of 261 rows: decaying mean vs depth 3 vs first stable,
  the caps at 5, `MATERIAL_DECAY_RATIO`, the loss gate. Then fit only the coefficients on the owner's
  labels.
- Test reply spread against Maia's probability of the punishing move at the mover's rating. This was
  already proposed as the "Findable" criterion in `SEED-261108-dk0-blunder-check-training.md` (line 90).
- Make leave-one-label-set-out the headline CV figure and report AUC per material type.
- Fit on soft labels (the owner's comments give ranges such as "should be 30-70%") instead of 0/1 with
  the 0.5 rows dropped.

### 3. Hybrid model (only if step 1 shows signal)

Train a small puzzle-difficulty predictor on storable features, apply it to each blunder as a virtual
puzzle, and feed the predicted rating D into the logistic layer. With a fitted rating offset,
`1 / (1 + 10^((D - R_user) / 400))` is a solve probability. A material loss needs a look-ahead penalty
on D, because the user had to see the opponent's puzzle one ply ahead.

Not a replacement for the score. Puzzle difficulty has no notion of temptation or of the size of the
loss, and Lichess puzzles require a clear win, so the "neither" rows (59 of the 261 labels) have no
puzzle counterpart. The owner's labels stay as the normative calibration layer.

## Open question: player ratings from the game links

The puzzle CSV has no player ratings, and Maia needs an Elo. Two options:

- Fixed Elo (for example 1500) for every puzzle. Simple, no network calls, enough for a rank
  correlation.
- Fetch the mover's rating from `GameUrl` through the Lichess API. Gives the real mover level, at the
  cost of rate-limited calls for every sampled puzzle.

The owner is not sure the fetched ratings should be used (2026-11-17). Points against: the puzzle
rating is measured on solvers of all levels, not on the two players of the source game, so the game
ratings describe who blundered, not who solved. They matter only for the played-probability term,
which the puzzle rating cannot validate anyway. Suggested default: fixed Elo in step 1, and revisit
only if a result turns out to be sensitive to the Elo choice (check by running two fixed Elos).

## Risks and caveats

- Uniqueness: Lichess puzzles have one winning move; real misses often have several and are easier
  than a puzzle predictor would say. Handling that needs evals for all winning moves.
- Rating scale: puzzle ratings are not game ratings, and users span chess.com, Lichess and four time
  controls. The offset must be fitted per platform and time control.
- Short solutions: many puzzles are 2 to 6 plies, so the deeper material slots are empty. The decaying
  mean renormalises over known depths; depth-3 scoring may drop rows.
- Cost of step 3: the published winning puzzle-difficulty models rely on Maia's probability for each
  solution move, which is 3 to 5 extra inferences per flaw and a backfill over millions of rows.
- Predictor quality: the competition winners are heavy ensembles. How much a small model on storable
  features recovers is unknown, which is why step 1 comes first.
- A second label source exists in-house: `blunder_check_answers` and `drill_solve` record users solving
  real-game blunders under puzzle conditions. Small today, but it is the exact target distribution.

## Prior art (checked 2026-11-17)

- Anderson, Kleinberg, Mullainathan, "Assessing Human Error Against a Benchmark of Perfection" (KDD
  2016, arXiv 1606.04956): position-difficulty features predict blunders far better than rating or
  time; blunder potential alone reaches 0.73 accuracy.
- McIlroy-Young et al., "Aligning Superhuman AI with Human Behavior" (Maia, arXiv 2006.01855): a
  blunder-prediction task from the board alone.
- IEEE BigData Cup 2024 and FedCSIS 2025 "Predicting Chess Puzzle Difficulty": the 2025 winner
  (Björkqvist, annals-csis.org/Volume_43/drp/pdf/6497.pdf) combines a fine-tuned Maia-2, the Maia and
  Leela probability of each solution move, the Stockfish depth at which the move is found, and
  hand-crafted features (material gain, captures of undefended pieces, checks).
- Biswas and Regan, "Quantifying Depth and Complexity of Thinking and Knowledge" (2015): swing, the
  change of a move's value across search depths, as a difficulty measure. Supports depth weighting.

No published model for the normative target ("should have seen this") was found.

## Breadcrumbs

- `app/services/facepalm_score.py`, `app/services/facepalm_material.py`: the score and its material inputs
- `app/services/blunder_check_rules.py`: FACEPALM_* constants
- `app/services/line_material.py`: `line_facts`, `best_line_facts`
- `app/services/maia_flaw_stats.py`: `reply_spread`
- `scripts/blunder_check/fit_facepalm.py`: fit and CV tooling
- `scripts/select_tagger_fixtures.py`: reads the Lichess puzzle dump
- `reports/blunder-check/facepalm-fit-2026-11-16.md`: current fit report
- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md`: the "Findable" refutation-probability idea
- `.planning/seeds/SEED-261115-agg-facepalm-material-across-depths.md`: the depth-aggregation seed
- `.planning/seeds/SEED-129-rated-puzzle-benchmark.md`: rated puzzles as an engine calibration instrument

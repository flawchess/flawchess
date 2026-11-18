---
id: SEED-261117-hfb
status: dormant
planted: 2026-11-17
planted_during: after Phase 256 (facepalm refit, material aggregated over depths); owner review of the model with a literature check
trigger_when: the next facepalm refit, or any phase that changes the score's shape (material input, spread form, new stored Maia facts). Step 1 is done (spike 007, 2026-11-17); tabled by the owner on 2026-11-18 with steps 2 and 3 open.
scope: step 1 (validation spike) is done. Step 2 (shape choices, new features) is small to medium; its main candidate needs one new stored Maia fact and a backfill. Step 3 (predicted puzzle difficulty as a model input) is medium to large, with new stored Maia facts and a backfill.
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

### 1. Validate (done, see "Step 1 results")

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

## Step 1 results (spike 007, 2026-11-17)

Full write-up and tables: `.planning/spikes/007-facepalm-vs-puzzle-ratings/` (`README.md`,
`results.md`). Run against the model of release #486 (decaying mean) on 26,464 puzzles with a
settled rating, sampled evenly over 100-point rating bins, Maia at a fixed Elo of 1500.

Verdict PARTIAL against the criterion set before the run (Spearman <= -0.30 between the
composite score and the puzzle rating on non-mate puzzles with at most 2 solver moves):

| view | Spearman | passes |
|---|---|---|
| miss view (the solver's first move is the missed best move) | -0.57 | yes |
| loss view (the puzzle's blunder is the user's blunder), as shipped | -0.24 | no |
| loss view, played probability held constant | -0.32 | narrowly |

Findings:

- The miss side (missed term plus best-move probability) ranks puzzles well, -0.51 over all
  puzzles once solution length is removed.
- The loss side is diluted by the played-probability term, which puzzles cannot test (its own
  correlation with the rating is -0.03). This says nothing about its value on real blunders.
- The loss view cannot score 39% of non-mate puzzles (7,386 of 18,839): their line shows no
  material loss under the app's rules. They are harder (mean rating 1972 vs 1701) and lean to
  endgame, advanced-pawn and quiet-move themes. `line_material` counts captures only, so a
  promotion is not a loss. Whether real blunders have the same blind spot was not checked.
- Maia's probability of the punishing move beats reply spread in every slice (overall -0.49 vs
  +0.37, primary slice -0.45 vs +0.25). The two are strongly related (Spearman -0.77) and
  spread adds nothing once the probability is in: a cross-validated linear model of the rating
  reaches R^2 0.476 with loss + probability, 0.477 with spread added, 0.430 with loss + spread.
- The decaying mean holds up. Loss term with length removed: decaying mean -0.41, first stable
  -0.35, depth 3 -0.34. On 3-move puzzles it is the only input with signal.
- Solution length is the largest single factor (Spearman +0.61 with the rating). Raw
  correlations over all puzzles overstate the terms by about a factor of two; signal sits in
  2-move puzzles and fades beyond.
- The Elo choice does not matter (1100 / 1500 / 1900: loss view -0.60 / -0.61 / -0.63, miss
  view -0.62 / -0.64 / -0.66).
- A linear model on the four shipped terms recovers about half of the rating variance (R^2
  0.49, Spearman 0.70; 0.58 with length and cheap extras). The sample is uniform over rating,
  so this is not comparable with published figures.

Consequences for the steps below:

- Step 2, spread vs probability of the punishing move, is the strongest candidate. The value
  is NOT stored today: `maia_refutation_prob` (Phase 248) was dropped in Phase 250 D-11 on
  2026-11-14. Bringing it back means a column and a backfill (the policy call at ply + 1
  already runs for the spread, so going forward it is free). Cheaper first check, no prod
  change: compute it for the 261 labelled rows with `scripts/blunder_check/facepalm_features.py`
  and refit. Phase 250 preferred spread on the owner's labels; the reason is not written down
  in `250-CONTEXT.md` and should be looked up before reversing it.
- Step 2, material shape: no reason to reopen the Phase 256 choice of the decaying mean.
- Step 3 has signal to build on, but a predictor must not use solution length: a stored
  engine line has no natural end, so length does not exist for a real blunder.
- New open question: does the no-material-loss share (39% of non-mate puzzles) have a
  counterpart in real blunders, for example promotions and quiet wins?

## Open question: player ratings from the game links (settled by step 1)

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

Settled: step 1 ran three fixed Elos and no conclusion moved, so the game ratings are not needed.

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
- `.planning/spikes/007-facepalm-vs-puzzle-ratings/`: step 1 scripts, feature tables and results
- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md`: the "Findable" refutation-probability idea
- `.planning/seeds/closed/SEED-261115-agg-facepalm-material-across-depths.md`: the depth-aggregation seed
- `.planning/seeds/SEED-129-rated-puzzle-benchmark.md`: rated puzzles as an engine calibration instrument

# Facepalm score fit

A ranking, not a probability (D-01): the labels are mostly rule passers, so the fitted values are not calibrated to all blunders.

Features: facepalm-features-2026-11-16.tsv (facts schema). Seed 250 (repeats 250-254), 10 folds, threshold 0.7. The loss floor is fixed at 0 (D-05), there is no forcing-flag input (D-10).

## Data

- rows in the features file: 291
- usable for the fit: 261 (136 fair, 125 unfair)
- excluded, label 0.5 (undecided): 11
- excluded, no label (extra row): 1
- excluded, NULL played_prob: 0
- excluded, NULL loss feature (line too short to tell): 18
- label rows with a NULL best line (the missed term contributes 0, D-18): 36 of 290 (27 usable for the fit)
- label rows with a best-line mate within 3 plies (the missed-mate value stays MATE_LOSS = 5): 10

Rows each spread form and gate fits, and the usable rows it excludes (the shipped twin would leave them unscored or never reads the fact, D-04 / D-05 / D-12):

- spread always: 261 rows fit, excluded: NULL reply_spread 0, NULL best_prob 0
- spread loss_only, gate none: 261 rows fit, excluded: NULL reply_spread 0, NULL best_prob 0
- spread loss_only, gate 1: 261 rows fit, excluded: NULL reply_spread 0, NULL best_prob 0
- spread best_prob_for_misses, gate none: 261 rows fit, excluded: NULL reply_spread 0, NULL best_prob 0
- spread best_prob_for_misses, gate 1: 261 rows fit, excluded: NULL reply_spread 0, NULL best_prob 0
- rows that qualify only under a gated form (NULL reply_spread, the row does not lose material under the gate, so the spread is never read, D-12): 0

Usable rows per label set and material type (D-13):

| set | loses | misses | loses_and_misses | neither | unknown | all |
|---|---|---|---|---|---|---|
| 1 | 3 | 5 | 0 | 9 | 0 | 17 |
| 2 | 9 | 4 | 0 | 1 | 0 | 14 |
| 3 | 8 | 1 | 6 | 4 | 0 | 19 |
| 4 | 6 | 4 | 2 | 1 | 0 | 13 |
| 5 | 16 | 7 | 7 | 14 | 0 | 44 |
| 6 | 24 | 5 | 11 | 8 | 0 | 48 |
| 7 | 0 | 38 | 10 | 0 | 0 | 48 |
| 8 | 5 | 25 | 6 | 22 | 0 | 58 |
| all | 71 | 89 | 42 | 59 | 0 | 261 |

## Material input (D-06, D-07, D-08, D-09)

Each input runs the whole staged pipeline (stage 1 material form, stage 2 spread form and gate, stage 3 optional inputs); its final candidate is compared here. Rows can differ per input and per candidate (a NULL fact excludes a row only where the form reads it), so AUCs are listed with their row count. CV AUC and fair share (at the cut 0.7) are means over 5 cross-validation seeds, run over every labelled set. The set-8 columns are D-08: the whole pipeline refitted on sets 1-7 only and its final model scored on set 8 untouched (fair / unfair among passers at the cut).

| input | final candidate | rows | CV AUC mean | CV AUC spread | fair share mean | set-8 rows | set-8 AUC | set-8 fair / unfair at the cut | |
|---|---|---|---|---|---|---|---|---|---|
| decaying_mean | decaying mean, split, missed floor 0, cap 5, spread best_prob_for_misses gate none | 261 | 0.902 | 0.006 | 0.887 | 58 | 0.821 | 9 / 5 | chosen |
| first_stable | first stable, split, missed floor 0, cap 5, spread best_prob_for_misses gate none | 261 | 0.877 | 0.009 | 0.901 | 58 | 0.727 | 6 / 2 |  |
| depth_3 | depth 3, split, missed floor none, cap 5, spread best_prob_for_misses gate none | 261 | 0.879 | 0.008 | 0.881 | 58 | 0.835 | 9 / 2 |  |

Chosen input: decaying_mean. Reason: higher cross-validated AUC.

Disagreement: the cross-validated choice is decaying_mean (set-8 AUC 0.821) but depth_3 scores 0.835 on set 8, more than the tie tolerance 0.005 higher. The owner settles it at the D-13 checkpoint.

Set 8 has about 55 decided rows, so its AUC moves by several hundredths between samples: read the set-8 columns as a check on the cross-validated choice, not as a second ranking.

## Stage 1: material form (D-06)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| decaying mean: baseline: split, no missed term (pre-refit shape) | 261 | 4 | 0.851 | 0.848 | 0.008 | 90 | 79 | 11 | 0.878 | 0.884 | reference only, not a candidate |
| decaying mean, combined, missed floor none, cap 5, spread always | 261 | 4 | 0.826 | 0.823 | 0.011 | 88 | 75 | 13 | 0.852 | 0.846 |  |
| decaying mean, combined, missed floor none, cap 9, spread always | 261 | 4 | 0.817 | 0.813 | 0.009 | 85 | 72 | 13 | 0.847 | 0.841 |  |
| decaying mean, combined, missed floor 0, cap 5, spread always | 261 | 4 | 0.838 | 0.834 | 0.011 | 89 | 77 | 12 | 0.865 | 0.868 |  |
| decaying mean, combined, missed floor 0, cap 9, spread always | 261 | 4 | 0.826 | 0.822 | 0.009 | 85 | 73 | 12 | 0.859 | 0.850 |  |
| decaying mean, split, missed floor none, cap 5, spread always | 261 | 5 | 0.860 | 0.857 | 0.011 | 90 | 80 | 10 | 0.889 | 0.880 |  |
| decaying mean, split, missed floor none, cap 9, spread always | 261 | 5 | 0.858 | 0.855 | 0.011 | 90 | 80 | 10 | 0.889 | 0.875 |  |
| decaying mean, split, missed floor 0, cap 5, spread always | 261 | 5 | 0.869 | 0.866 | 0.013 | 94 | 82 | 12 | 0.872 | 0.872 | chosen |
| decaying mean, split, missed floor 0, cap 9, spread always | 261 | 5 | 0.864 | 0.861 | 0.012 | 91 | 80 | 11 | 0.879 | 0.873 |  |

Chosen: decaying mean, split, missed floor 0, cap 5, spread always. Reason: AUC and fair share tie, fewer free coefficients.

## Stage 2: reply-spread form (D-07)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| decaying mean, split, missed floor 0, cap 5, spread always | 261 | 5 | 0.869 | 0.866 | 0.013 | 94 | 82 | 12 | 0.872 | 0.872 |  |
| decaying mean, split, missed floor 0, cap 5, spread loss_only gate none | 261 | 5 | 0.864 | 0.862 | 0.007 | 89 | 81 | 8 | 0.910 | 0.906 |  |
| decaying mean, split, missed floor 0, cap 5, spread loss_only gate 1 | 261 | 5 | 0.865 | 0.865 | 0.007 | 85 | 78 | 7 | 0.918 | 0.902 |  |
| decaying mean, split, missed floor 0, cap 5, spread best_prob_for_misses gate none | 261 | 6 | 0.901 | 0.902 | 0.006 | 99 | 88 | 11 | 0.889 | 0.887 | chosen |
| decaying mean, split, missed floor 0, cap 5, spread best_prob_for_misses gate 1 | 261 | 6 | 0.872 | 0.872 | 0.010 | 89 | 82 | 7 | 0.921 | 0.912 |  |

Chosen: decaying mean, split, missed floor 0, cap 5, spread best_prob_for_misses gate none. Reason: higher cross-validated AUC.

## Stage 3b: pre-blunder spread (D-08)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| decaying mean, split, missed floor 0, cap 5, spread best_prob_for_misses gate none | 261 | 6 | 0.901 | 0.902 | 0.006 | 99 | 88 | 11 | 0.889 | 0.887 | chosen |
| decaying mean, split, missed floor 0, cap 5, spread best_prob_for_misses gate none, + pre_spread | 261 | 7 | 0.897 | 0.901 | 0.009 | 103 | 89 | 14 | 0.864 | 0.881 |  |

Chosen: decaying mean, split, missed floor 0, cap 5, spread best_prob_for_misses gate none. Reason: AUC and fair share tie, fewer free coefficients.

## Chosen model

- material input: decaying mean (the loss and the missed gain read the same input)
- material: separate loss and missed coefficients (split); missed floor 0, cap 5, missed-mate value 5
- spread: the reply spread enters on rows that lose material, the best-move probability stands in for pure misses
- loss gate: a row loses material when its loss is above 0
- best-move probability enters the model (coefficient 1.9618)
- pre-blunder spread earns nothing and keeps a 0.0 coefficient

- intercept: -1.2172
- played: -0.6083
- spread: -0.3617
- loss: 1.1643
- missed: 0.3538
- best_prob: 1.9618
- AUC in sample: 0.913
- AUC 10-fold cross-validated: 0.901; over 5 seeds mean 0.902, spread 0.006

Assumptions the inputs rest on (D-13, confirm at the checkpoint):

- A1 first stable: the first odd-depth pair with equal values, discounted by the decay ratio 0.5 to the power of its onset index; without such a pair, the last known value discounted by its index.
- A2 mate: a mate within LINE_DEPTH = 3 plies on either line short-circuits the input to MATE_LOSS = 5 (the missed-mate value on the best line); a later mate enters per depth from its ply.
- A4 loss gate: the numeric gate of the gated spread forms uses "at least" (a constant one-pawn loss counts as losing under gate 1).
- loss floor 0 per depth (D-05): the loss is max(0, -material) at each depth before it is aggregated.
- missed floor 0, cap 5, applied per depth before it is aggregated.

## Fair / unfair among passers by material type

Cells are fair / unfair among rows whose out-of-fold score of the chosen model is at or above the cut.

| material type | rows | fair | unfair | score >= 0.50 | score >= 0.60 | score >= 0.70 | score >= 0.80 | score >= 0.90 |
|---|---|---|---|---|---|---|---|---|
| loses | 71 | 62 | 9 | 54 / 3 | 52 / 2 | 44 / 1 | 40 / 1 | 35 / 0 |
| misses | 89 | 26 | 63 | 16 / 9 | 15 / 8 | 12 / 4 | 8 / 3 | 7 / 0 |
| loses_and_misses | 42 | 33 | 9 | 31 / 7 | 31 / 6 | 28 / 4 | 25 / 3 | 21 / 1 |
| neither | 59 | 15 | 44 | 8 / 7 | 8 / 4 | 4 / 2 | 4 / 1 | 3 / 1 |
| all | 261 | 136 | 125 | 109 / 26 | 106 / 20 | 88 / 11 | 77 / 8 | 66 / 2 |

## Fair / unfair among passers by label set

Cells are fair / unfair among rows whose out-of-fold score of the chosen model is at or above the cut.

| label set | rows | fair | unfair | score >= 0.50 | score >= 0.60 | score >= 0.70 | score >= 0.80 | score >= 0.90 |
|---|---|---|---|---|---|---|---|---|
| 1 | 17 | 8 | 9 | 3 / 3 | 3 / 2 | 3 / 0 | 1 / 0 | 0 / 0 |
| 2 | 14 | 9 | 5 | 6 / 3 | 6 / 2 | 3 / 1 | 3 / 1 | 3 / 0 |
| 3 | 19 | 11 | 8 | 9 / 2 | 9 / 1 | 8 / 1 | 6 / 1 | 4 / 0 |
| 4 | 13 | 8 | 5 | 7 / 0 | 6 / 0 | 6 / 0 | 5 / 0 | 4 / 0 |
| 5 | 44 | 23 | 21 | 22 / 3 | 22 / 3 | 17 / 1 | 16 / 1 | 14 / 0 |
| 6 | 48 | 36 | 12 | 35 / 3 | 34 / 2 | 29 / 1 | 26 / 0 | 23 / 0 |
| 7 | 48 | 24 | 24 | 18 / 2 | 17 / 2 | 14 / 2 | 12 / 2 | 10 / 0 |
| 8 | 58 | 17 | 41 | 9 / 10 | 9 / 8 | 8 / 5 | 8 / 3 | 8 / 2 |
| all | 261 | 136 | 125 | 109 / 26 | 106 / 20 | 88 / 11 | 77 / 8 | 66 / 2 |

## Sets 1-7 vs set 8

The chosen input's pipeline fitted on sets 1-7 (203 usable rows), scored on set 8 (58 usable rows).

- AUC on set 8: 0.821

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 23 | 12 | 11 | 0.522 |
| 0.60 | 19 | 10 | 9 | 0.526 |
| 0.70 | 14 | 9 | 5 | 0.643 |
| 0.80 | 14 | 9 | 5 | 0.643 |
| 0.90 | 9 | 6 | 3 | 0.667 |

## Owner checks (D-13, information only, not gates)

### Commented label rows

The owner's comments and links, verbatim. Scores use the drill lambda (1.0): 'old' is the model in the checkout (FACEPALM_MODEL), 'new' the chosen model of this fit (in sample).

| n | set | label | link | comment | old score | new score |
|---|---|---|---|---|---|---|
| 211 | 7 | 1 | https://flawchess.com/analysis?game_id=2333333&ply=114 | currently 6%, should be at least 90% | 0.505 | 0.677 |
| 216 | 7 | 1 | https://flawchess.com/analysis?game_id=1941531&ply=89 | currently 33%, should be above 60% | 0.713 | 0.912 |
| 217 | 7 | 1 | https://flawchess.com/analysis?game_id=2218424&ply=89 | currently 10%, should be above 70% | 0.587 | 0.782 |
| 219 | 7 | 1 | https://flawchess.com/analysis?game_id=1161949&ply=24 | currently 23%, should be above 60% | 0.291 | 0.234 |
| 220 | 7 | 0 | https://flawchess.com/analysis?game_id=1161949&ply=26 | currently 1%, should be between 30-70% | 0.234 | 0.269 |
| 223 | 7 | 0.5 | https://flawchess.com/analysis?game_id=2425058&ply=50 | currently 23%, should be between 30%-70% | 0.552 | 0.711 |
| 224 | 7 | 0 | https://flawchess.com/analysis?game_id=2474796&ply=25 | currently 9%, should be 30%-70% | 0.623 | 0.116 |
| 225 | 7 | 1 | https://flawchess.com/analysis?game_id=2664826&ply=74 | currently 16%, should be above 80% | 0.309 | 0.370 |
| 227 | 7 | 0 | https://flawchess.com/analysis?game_id=562300&ply=40 | currently 0%, should be above 20% | 0.174 | 0.130 |
| 228 | 7 | 1 | https://flawchess.com/analysis?game_id=2952292&ply=85 | currently 30%, should be above 70% | 0.706 | 0.877 |
| 232 | 7 | 1 | https://flawchess.com/analysis?game_id=2960887&ply=21 | currently 11%, should be above 70% | 0.352 | 0.234 |
| 233 | 7 | 1 | https://flawchess.com/analysis?game_id=1554612&ply=24 | currently 18%, should be above 70% | 0.723 | 0.913 |
| 234 | 7 | 1 | https://flawchess.com/analysis?game_id=3264420&ply=25 | currently 11%, should be above 70% | 0.039 | 0.182 |
| 239 | 7 | 0 | https://flawchess.com/analysis?game_id=2433781&ply=50 | currently 0%, should be above 20% | 0.103 | 0.035 |
| 240 | 7 | 1 | https://flawchess.com/analysis?game_id=2561505&ply=41 | currently 63%, should be above 70% | 0.746 | 0.627 |
| 244 | 8 | 1 | https://flawchess.com/analysis?game_id=2068559&ply=31 | currently 8, should be above 70% | 0.090 | 0.630 |
| 251 | 8 | 0 | https://flawchess.com/analysis?game_id=1871758&ply=50 | currently 52%, should be below 30% | 0.521 | 0.670 |
| 252 | 8 | 0 | https://flawchess.com/analysis?game_id=3143227&ply=26 | currently 88%, should be below 60% | 0.885 | 0.795 |
| 253 | 8 | 0.5 | https://flawchess.com/analysis?game_id=505289&ply=21 | currently 51%, should be 50-80% | 0.516 | 0.653 |
| 260 | 8 | 0 | https://flawchess.com/analysis?game_id=1919895&ply=5 | should be below 30% | 0.107 | 0.017 |
| 263 | 8 | 1 | https://flawchess.com/analysis?game_id=2674500&ply=33 | currently 13%, should be above 70% | 0.140 | 0.132 |
| 265 | 8 | 0 | https://flawchess.com/analysis?game_id=2494184&ply=26 | currently 99%, should be below 70% | 0.995 | 0.973 |
| 269 | 8 | 1 | https://flawchess.com/analysis?game_id=2048229&ply=20 | currently 40%, should be above 70% | 0.406 | 0.433 |
| 270 | 8 | 1 | https://flawchess.com/analysis?game_id=1635462&ply=40 | currently 40%, should be above 70% | 0.405 | 0.416 |
| 280 | 8 | 0 | https://flawchess.com/analysis?game_id=1586714&ply=109 | currently 17%, should be 30-70% | 0.179 | 0.133 |
| 282 | 8 | 1 | https://flawchess.com/analysis?game_id=2727402&ply=30 | currently 48%, should be 70-90% | 0.486 | 0.449 |
| 292 | 8 | 1 | https://flawchess.com/analysis?game_id=1551685&ply=33 | currently 12%, should be above 70% | 0.126 | 0.971 |
| 294 | 8 | 1 | https://flawchess.com/analysis?game_id=2881177&ply=17 | currently 66% should be above 70% | 0.668 | 0.934 |

### Added rows, old and new score

Unlabelled rows of the features table, scored under the model in the checkout (old) and the chosen model (new). Window 14 (game 2099808 ply 23) must still fall below the chosen cut.

| row | old score | new score | below 0.50 | below 0.60 | below 0.70 | below 0.80 | below 0.90 |
|---|---|---|---|---|---|---|---|
| extra | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### Pure-miss pass rate

Among the chosen candidate's rows of material type 'misses' (nothing lost, material left on the table), the rows whose out-of-fold score is at or above each cut.

| cut | passers | rows | pass rate |
|---|---|---|---|
| 0.50 | 25 | 89 | 0.281 |
| 0.60 | 23 | 89 | 0.258 |
| 0.70 | 16 | 89 | 0.180 |
| 0.80 | 11 | 89 | 0.124 |
| 0.90 | 7 | 89 | 0.079 |

The two owner fixtures (games 817357 ply 24 and 820181 ply 65) are dev-DB games that are not on prod and not in the features table: they are scored at the checkpoint from tests/services/facepalm_owner_fixtures.py.

## Other input: first_stable

### Stage 1: material form (D-06)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| first stable: baseline: split, no missed term (pre-refit shape) | 261 | 4 | 0.850 | 0.845 | 0.010 | 88 | 80 | 8 | 0.909 | 0.905 | reference only, not a candidate |
| first stable, combined, missed floor none, cap 5, spread always | 261 | 4 | 0.837 | 0.834 | 0.009 | 85 | 75 | 10 | 0.882 | 0.880 |  |
| first stable, combined, missed floor none, cap 9, spread always | 261 | 4 | 0.826 | 0.824 | 0.010 | 87 | 74 | 13 | 0.851 | 0.869 |  |
| first stable, combined, missed floor 0, cap 5, spread always | 261 | 4 | 0.845 | 0.843 | 0.008 | 88 | 77 | 11 | 0.875 | 0.875 |  |
| first stable, combined, missed floor 0, cap 9, spread always | 261 | 4 | 0.836 | 0.832 | 0.009 | 86 | 74 | 12 | 0.860 | 0.864 |  |
| first stable, split, missed floor none, cap 5, spread always | 261 | 5 | 0.858 | 0.856 | 0.010 | 94 | 84 | 10 | 0.894 | 0.895 |  |
| first stable, split, missed floor none, cap 9, spread always | 261 | 5 | 0.855 | 0.853 | 0.009 | 91 | 81 | 10 | 0.890 | 0.894 |  |
| first stable, split, missed floor 0, cap 5, spread always | 261 | 5 | 0.863 | 0.863 | 0.011 | 93 | 84 | 9 | 0.903 | 0.899 | chosen |
| first stable, split, missed floor 0, cap 9, spread always | 261 | 5 | 0.860 | 0.857 | 0.011 | 93 | 84 | 9 | 0.903 | 0.898 |  |

Chosen: first stable, split, missed floor 0, cap 5, spread always. Reason: higher cross-validated AUC.

### Stage 2: reply-spread form (D-07)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| first stable, split, missed floor 0, cap 5, spread always | 261 | 5 | 0.863 | 0.863 | 0.011 | 93 | 84 | 9 | 0.903 | 0.899 |  |
| first stable, split, missed floor 0, cap 5, spread loss_only gate none | 261 | 5 | 0.851 | 0.851 | 0.004 | 90 | 82 | 8 | 0.911 | 0.905 |  |
| first stable, split, missed floor 0, cap 5, spread loss_only gate 1 | 261 | 5 | 0.853 | 0.850 | 0.008 | 86 | 79 | 7 | 0.919 | 0.907 |  |
| first stable, split, missed floor 0, cap 5, spread best_prob_for_misses gate none | 261 | 6 | 0.876 | 0.877 | 0.009 | 97 | 87 | 10 | 0.897 | 0.901 | chosen |
| first stable, split, missed floor 0, cap 5, spread best_prob_for_misses gate 1 | 261 | 6 | 0.880 | 0.880 | 0.006 | 97 | 88 | 9 | 0.907 | 0.901 |  |

Chosen: first stable, split, missed floor 0, cap 5, spread best_prob_for_misses gate none. Reason: AUC and fair share tie, fewer free coefficients.

### Stage 3b: pre-blunder spread (D-08)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| first stable, split, missed floor 0, cap 5, spread best_prob_for_misses gate none | 261 | 6 | 0.876 | 0.877 | 0.009 | 97 | 87 | 10 | 0.897 | 0.901 | chosen |
| first stable, split, missed floor 0, cap 5, spread best_prob_for_misses gate none, + pre_spread | 261 | 7 | 0.872 | 0.875 | 0.009 | 95 | 84 | 11 | 0.884 | 0.904 |  |

Chosen: first stable, split, missed floor 0, cap 5, spread best_prob_for_misses gate none. Reason: AUC and fair share tie, fewer free coefficients.

### Sets 1-7 vs set 8

The first_stable pipeline fitted on sets 1-7 (203 usable rows), scored on set 8 (58 usable rows).

- AUC on set 8: 0.727

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 19 | 10 | 9 | 0.526 |
| 0.60 | 12 | 8 | 4 | 0.667 |
| 0.70 | 8 | 6 | 2 | 0.750 |
| 0.80 | 7 | 6 | 1 | 0.857 |
| 0.90 | 2 | 2 | 0 | 1.000 |

## Other input: depth_3

### Stage 1: material form (D-06)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| depth 3: baseline: split, no missed term (pre-refit shape) | 261 | 4 | 0.856 | 0.852 | 0.014 | 90 | 80 | 10 | 0.889 | 0.885 | reference only, not a candidate |
| depth 3, combined, missed floor none, cap 5, spread always | 261 | 4 | 0.816 | 0.811 | 0.008 | 81 | 68 | 13 | 0.840 | 0.830 |  |
| depth 3, combined, missed floor none, cap 9, spread always | 261 | 4 | 0.803 | 0.798 | 0.008 | 80 | 65 | 15 | 0.812 | 0.806 |  |
| depth 3, combined, missed floor 0, cap 5, spread always | 261 | 4 | 0.820 | 0.817 | 0.006 | 78 | 66 | 12 | 0.846 | 0.845 |  |
| depth 3, combined, missed floor 0, cap 9, spread always | 261 | 4 | 0.805 | 0.803 | 0.007 | 79 | 64 | 15 | 0.810 | 0.803 |  |
| depth 3, split, missed floor none, cap 5, spread always | 261 | 5 | 0.859 | 0.852 | 0.015 | 91 | 81 | 10 | 0.890 | 0.882 | chosen |
| depth 3, split, missed floor none, cap 9, spread always | 261 | 5 | 0.857 | 0.851 | 0.015 | 90 | 80 | 10 | 0.889 | 0.883 |  |
| depth 3, split, missed floor 0, cap 5, spread always | 261 | 5 | 0.862 | 0.857 | 0.015 | 92 | 82 | 10 | 0.891 | 0.882 |  |
| depth 3, split, missed floor 0, cap 9, spread always | 261 | 5 | 0.859 | 0.854 | 0.015 | 92 | 82 | 10 | 0.891 | 0.882 |  |

Chosen: depth 3, split, missed floor none, cap 5, spread always. Reason: AUC and fair share tie, fewer free coefficients.

### Stage 2: reply-spread form (D-07)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| depth 3, split, missed floor none, cap 5, spread always | 261 | 5 | 0.859 | 0.852 | 0.015 | 91 | 81 | 10 | 0.890 | 0.882 |  |
| depth 3, split, missed floor none, cap 5, spread loss_only gate none | 261 | 5 | 0.857 | 0.849 | 0.013 | 85 | 76 | 9 | 0.894 | 0.890 |  |
| depth 3, split, missed floor none, cap 5, spread loss_only gate 1 | 261 | 5 | 0.857 | 0.849 | 0.013 | 85 | 76 | 9 | 0.894 | 0.890 |  |
| depth 3, split, missed floor none, cap 5, spread best_prob_for_misses gate none | 261 | 6 | 0.883 | 0.879 | 0.008 | 99 | 88 | 11 | 0.889 | 0.881 | chosen |
| depth 3, split, missed floor none, cap 5, spread best_prob_for_misses gate 1 | 261 | 6 | 0.883 | 0.879 | 0.008 | 99 | 88 | 11 | 0.889 | 0.881 |  |

Chosen: depth 3, split, missed floor none, cap 5, spread best_prob_for_misses gate none. Reason: AUC and fair share tie, fewer free coefficients.

### Stage 3b: pre-blunder spread (D-08)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | rows | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|---|
| depth 3, split, missed floor none, cap 5, spread best_prob_for_misses gate none | 261 | 6 | 0.883 | 0.879 | 0.008 | 99 | 88 | 11 | 0.889 | 0.881 | chosen |
| depth 3, split, missed floor none, cap 5, spread best_prob_for_misses gate none, + pre_spread | 261 | 7 | 0.879 | 0.879 | 0.008 | 100 | 89 | 11 | 0.890 | 0.887 |  |

Chosen: depth 3, split, missed floor none, cap 5, spread best_prob_for_misses gate none. Reason: AUC and fair share tie, fewer free coefficients.

### Sets 1-7 vs set 8

The depth_3 pipeline fitted on sets 1-7 (203 usable rows), scored on set 8 (58 usable rows).

- AUC on set 8: 0.835

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 16 | 11 | 5 | 0.688 |
| 0.60 | 15 | 11 | 4 | 0.733 |
| 0.70 | 11 | 9 | 2 | 0.818 |
| 0.80 | 6 | 4 | 2 | 0.667 |
| 0.90 | 2 | 1 | 1 | 0.500 |

## Extra rows

Unlabelled rows scored with the model below (threshold 0.7).

- row extra: played_prob 0.095, reply_spread 7.760, line_loss_3 None, line_mate_ply None: score n/a, not scored (a NULL input)

## Constants

```python
FACEPALM_INTERCEPT: float = -1.2172
FACEPALM_PLAYED_COEF: float = -0.6083
FACEPALM_SPREAD_COEF: float = -0.3617
FACEPALM_LOSS_COEF: float = 1.1643
FACEPALM_LOSS_FLOOR: int | None = 0
FACEPALM_MATERIAL_FORM: MaterialForm = "split"
FACEPALM_MISSED_COEF: float = 0.3538
FACEPALM_MISSED_FLOOR: int | None = 0
FACEPALM_MISSED_CAP: int = 5
FACEPALM_MISSED_MATE: int = 5
FACEPALM_SPREAD_FORM: SpreadForm = "best_prob_for_misses"
FACEPALM_BEST_PROB_COEF: float = 1.9618
FACEPALM_PRE_SPREAD_COEF: float = 0.0000
FACEPALM_MATERIAL_INPUT: MaterialInput = "decaying_mean"
FACEPALM_LOSS_GATE: float | None = None
```

# Facepalm score fit

A ranking, not a probability (D-01): the labels are mostly rule passers, so the fitted values are not calibrated to all blunders.

Features: facepalm-features-2026-11-15.tsv (facts schema). Seed 250 (repeats 250-254), 10 folds, threshold 0.7. The loss floor is fixed at 0 (D-05), there is no forcing-flag input (D-10).

## Data

- rows in the features file: 231
- usable for the fit: 199 (117 fair, 82 unfair)
- excluded, label 0.5 (undecided): 9
- excluded, no label (extra row): 1
- excluded, NULL played_prob: 0
- excluded, NULL reply_spread: 0
- excluded, NULL loss feature (line too short to tell): 22
- label rows with a NULL best line (the missed term contributes 0, D-18): 45 of 230 (36 usable for the fit)
- label rows with a best-line mate within 3 plies (the missed-mate value stays MATE_LOSS = 5): 7

Usable rows per label set and material type (D-13):

| set | loses | misses | loses_and_misses | neither | unknown | all |
|---|---|---|---|---|---|---|
| 1 | 3 | 5 | 0 | 9 | 0 | 17 |
| 2 | 8 | 4 | 0 | 1 | 0 | 13 |
| 3 | 9 | 1 | 5 | 3 | 0 | 18 |
| 4 | 6 | 4 | 2 | 1 | 0 | 13 |
| 5 | 16 | 6 | 7 | 15 | 0 | 44 |
| 6 | 25 | 5 | 9 | 7 | 0 | 46 |
| 7 | 0 | 38 | 10 | 0 | 0 | 48 |
| all | 67 | 63 | 33 | 36 | 0 | 199 |

## Stage 1: material form (D-06)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline: split, no missed term (pre-refit shape) | 4 | 0.852 | 0.852 | 0.005 | 87 | 79 | 8 | 0.908 | 0.901 | reference only, not a candidate |
| combined, missed floor none, cap 5, spread always | 4 | 0.803 | 0.804 | 0.005 | 84 | 71 | 13 | 0.845 | 0.851 |  |
| combined, missed floor none, cap 9, spread always | 4 | 0.783 | 0.784 | 0.006 | 85 | 68 | 17 | 0.800 | 0.808 |  |
| combined, missed floor 0, cap 5, spread always | 4 | 0.806 | 0.810 | 0.009 | 85 | 71 | 14 | 0.835 | 0.849 |  |
| combined, missed floor 0, cap 9, spread always | 4 | 0.786 | 0.789 | 0.006 | 83 | 66 | 17 | 0.795 | 0.819 |  |
| split, missed floor none, cap 5, spread always | 5 | 0.852 | 0.852 | 0.005 | 87 | 77 | 10 | 0.885 | 0.897 | chosen |
| split, missed floor none, cap 9, spread always | 5 | 0.849 | 0.850 | 0.003 | 86 | 77 | 9 | 0.895 | 0.902 |  |
| split, missed floor 0, cap 5, spread always | 5 | 0.853 | 0.855 | 0.004 | 87 | 77 | 10 | 0.885 | 0.891 |  |
| split, missed floor 0, cap 9, spread always | 5 | 0.850 | 0.852 | 0.005 | 87 | 78 | 9 | 0.897 | 0.898 |  |

Chosen: split, missed floor none, cap 5, spread always. Reason: AUC and fair share tie, fewer free coefficients.

## Stage 2: reply-spread form (D-07)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|
| split, missed floor none, cap 5, spread always | 5 | 0.852 | 0.852 | 0.005 | 87 | 77 | 10 | 0.885 | 0.897 |  |
| split, missed floor none, cap 5, spread loss_only | 5 | 0.833 | 0.833 | 0.004 | 81 | 72 | 9 | 0.889 | 0.910 |  |
| split, missed floor none, cap 5, spread best_prob_for_misses | 6 | 0.874 | 0.874 | 0.004 | 90 | 81 | 9 | 0.900 | 0.902 | chosen |

Chosen: split, missed floor none, cap 5, spread best_prob_for_misses. Reason: higher cross-validated AUC.

## Stage 3b: pre-blunder spread (D-08)

At the cut 0.7. CV AUC and fair share are the base seed's; the mean and the spread (max - min) of CV AUC, and the mean fair share, are over 5 seeds. Choices are made on the seed means.

| candidate | free coefs | CV AUC | CV AUC mean | CV AUC spread | passers | fair | unfair | fair share | fair share mean | |
|---|---|---|---|---|---|---|---|---|---|---|
| split, missed floor none, cap 5, spread best_prob_for_misses | 6 | 0.874 | 0.874 | 0.004 | 90 | 81 | 9 | 0.900 | 0.902 | chosen |
| split, missed floor none, cap 5, spread best_prob_for_misses, + pre_spread | 7 | 0.873 | 0.873 | 0.007 | 89 | 80 | 9 | 0.899 | 0.899 |  |

Chosen: split, missed floor none, cap 5, spread best_prob_for_misses. Reason: AUC and fair share tie, fewer free coefficients.

## Chosen model

- material: separate loss and missed coefficients (split); missed floor none, cap 5, missed-mate value 5
- spread: the reply spread enters on rows that lose material, the best-move probability stands in for pure misses
- best-move probability enters the model (coefficient 1.0405)
- pre-blunder spread earns nothing and keeps a 0.0 coefficient

- intercept: -0.7583
- played: -0.4146
- spread: -0.2585
- loss: 1.0129
- missed: 0.0891
- best_prob: 1.0405
- AUC in sample: 0.896
- AUC 10-fold cross-validated: 0.874; over 5 seeds mean 0.874, spread 0.004

## Fair / unfair among passers by material type

Cells are fair / unfair among rows whose out-of-fold score of the chosen model is at or above the cut.

| material type | rows | fair | unfair | score >= 0.50 | score >= 0.60 | score >= 0.70 | score >= 0.80 | score >= 0.90 |
|---|---|---|---|---|---|---|---|---|
| loses | 67 | 58 | 9 | 55 / 7 | 54 / 4 | 52 / 4 | 44 / 3 | 39 / 2 |
| misses | 63 | 21 | 42 | 12 / 6 | 6 / 3 | 2 / 1 | 1 / 1 | 0 / 0 |
| loses_and_misses | 33 | 29 | 4 | 29 / 4 | 29 / 4 | 27 / 3 | 24 / 3 | 20 / 0 |
| neither | 36 | 9 | 27 | 2 / 4 | 0 / 3 | 0 / 1 | 0 / 0 | 0 / 0 |
| all | 199 | 117 | 82 | 98 / 21 | 89 / 14 | 81 / 9 | 69 / 7 | 59 / 2 |

## Fair / unfair among passers by label set

Cells are fair / unfair among rows whose out-of-fold score of the chosen model is at or above the cut.

| label set | rows | fair | unfair | score >= 0.50 | score >= 0.60 | score >= 0.70 | score >= 0.80 | score >= 0.90 |
|---|---|---|---|---|---|---|---|---|
| 1 | 17 | 8 | 9 | 3 / 3 | 2 / 3 | 2 / 1 | 1 / 0 | 1 / 0 |
| 2 | 13 | 8 | 5 | 7 / 4 | 5 / 2 | 4 / 1 | 3 / 0 | 3 / 0 |
| 3 | 18 | 11 | 7 | 10 / 4 | 10 / 3 | 10 / 3 | 7 / 3 | 6 / 1 |
| 4 | 13 | 8 | 5 | 8 / 0 | 7 / 0 | 7 / 0 | 4 / 0 | 4 / 0 |
| 5 | 44 | 23 | 21 | 21 / 5 | 19 / 2 | 17 / 1 | 17 / 1 | 11 / 0 |
| 6 | 46 | 35 | 11 | 32 / 3 | 31 / 2 | 30 / 2 | 28 / 2 | 27 / 1 |
| 7 | 48 | 24 | 24 | 17 / 2 | 15 / 2 | 11 / 1 | 9 / 1 | 7 / 0 |
| all | 199 | 117 | 82 | 98 / 21 | 89 / 14 | 81 / 9 | 69 / 7 | 59 / 2 |

## Sets 1-5 vs set 6

The chosen model fitted on sets 1-5 and 7 (153 usable rows), scored on set 6 (46 usable rows).

- AUC on set 6: 0.901

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 35 | 32 | 3 | 0.914 |
| 0.60 | 31 | 29 | 2 | 0.935 |
| 0.70 | 31 | 29 | 2 | 0.935 |
| 0.80 | 31 | 29 | 2 | 0.935 |
| 0.90 | 28 | 27 | 1 | 0.964 |

## Extra rows

Unlabelled rows scored with the model below (threshold 0.7).

- row extra: played_prob 0.095, reply_spread 7.760, line_loss_3 None, line_mate_ply None: score n/a, not scored (a NULL input)

## Constants

```python
FACEPALM_INTERCEPT: float = -0.7583
FACEPALM_PLAYED_COEF: float = -0.4146
FACEPALM_SPREAD_COEF: float = -0.2585
FACEPALM_LOSS_COEF: float = 1.0129
FACEPALM_LOSS_FLOOR: int | None = 0
FACEPALM_MATERIAL_FORM: MaterialForm = "split"
FACEPALM_MISSED_COEF: float = 0.0891
FACEPALM_MISSED_FLOOR: int | None = None
FACEPALM_MISSED_CAP: int = 5
FACEPALM_MISSED_MATE: int = 5
FACEPALM_SPREAD_FORM: SpreadForm = "best_prob_for_misses"
FACEPALM_BEST_PROB_COEF: float = 1.0405
FACEPALM_PRE_SPREAD_COEF: float = 0.0000
```

# Facepalm score fit

A ranking, not a probability (D-01): the labels are mostly rule passers, so the fitted values are not calibrated to all blunders.

Features: facepalm-features-2026-11-13.tsv. Seed 250, 10 folds, threshold 0.7.

## Data

- rows in the features file: 181
- usable for the fit: 140 (88 fair, 52 unfair)
- excluded, label 0.5 (undecided): 7
- excluded, no label (extra row): 1
- excluded, NULL played_prob: 0
- excluded, NULL reply_spread: 0
- excluded, NULL loss feature (line too short to tell): 33

## Form A

ln(played_prob + PLAYED_PROB_OFFSET), reply spread, loss feature at LINE_DEPTH (loss floor: 0). This form ships (D-01).

- intercept: -1.4193
- ln(played_prob + offset): -0.6629
- reply_spread: -0.3304
- loss feature: 1.1570
- AUC in sample: 0.910
- AUC 10-fold cross-validated: 0.880

Fair / unfair among passers, out-of-fold predictions:

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 85 | 72 | 13 | 0.847 |
| 0.60 | 77 | 68 | 9 | 0.883 |
| 0.70 | 72 | 64 | 8 | 0.889 |
| 0.80 | 64 | 60 | 4 | 0.938 |
| 0.90 | 55 | 53 | 2 | 0.964 |

## Form B

Raw played probability, reply spread, binary loss (line_loss_3 >= 2 or a mate within 3 plies). Reported for the owner's comparison only.

- intercept: 1.5020
- played_prob: -6.5140
- reply_spread: -0.3690
- binary loss: 3.1065
- AUC in sample: 0.899
- AUC 10-fold cross-validated: 0.863

Fair / unfair among passers, out-of-fold predictions:

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 85 | 71 | 14 | 0.835 |
| 0.60 | 77 | 67 | 10 | 0.870 |
| 0.70 | 66 | 61 | 5 | 0.924 |
| 0.80 | 65 | 61 | 4 | 0.938 |
| 0.90 | 60 | 57 | 3 | 0.950 |

## Clip choice

Form A with the loss unclipped against a lower clip at 0 (fair share at threshold 0.7).

| loss floor | AUC cross-validated | passers | fair | unfair | fair share |
|---|---|---|---|---|---|
| none | 0.878 | 71 | 63 | 8 | 0.887 |
| 0 | 0.880 | 72 | 64 | 8 | 0.889 |

Chosen loss floor: 0. Reason: AUCs within 0.005, higher out-of-fold fair share among passers.

## Sets 1-5 vs set 6

Form A fitted on sets 1-5 (96 usable rows), scored on set 6 (44 usable rows).

- AUC on set 6: 0.911

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 34 | 32 | 2 | 0.941 |
| 0.60 | 32 | 30 | 2 | 0.938 |
| 0.70 | 32 | 30 | 2 | 0.938 |
| 0.80 | 31 | 29 | 2 | 0.935 |
| 0.90 | 29 | 28 | 1 | 0.966 |

## Extra rows

Unlabelled rows scored with the Form A model below (threshold 0.7).

- row extra: played_prob 0.095, reply_spread 7.760, line_loss_3 None, line_mate_ply None: score n/a, not scored (a NULL input)

## Constants

```python
FACEPALM_INTERCEPT: float = -1.4193
FACEPALM_PLAYED_COEF: float = -0.6629
FACEPALM_SPREAD_COEF: float = -0.3304
FACEPALM_LOSS_COEF: float = 1.1570
FACEPALM_LOSS_FLOOR: int | None = 0
```

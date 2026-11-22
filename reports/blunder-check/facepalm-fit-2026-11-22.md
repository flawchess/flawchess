# Facepalm score fit

A ranking, not a probability (250 D-01): the labels are mostly rule passers, so the fitted values are not calibrated to all blunders.

Features: facepalm-features-2026-11-22.tsv. Seed 250 (repeats 250-254), 10 folds, threshold 0.7. The model shape is fixed (D-01), label sets 1 to 8 are used as they are (D-14).

## Data

- rows in the features file: 291
- usable for the fit: 268 (139 fair, 129 unfair)
- excluded, label 0.5 (undecided): 11
- excluded, no label (extra row): 2
- excluded, NULL played_prob: 0
- excluded, NULL loss (no settled line): 10
- excluded, NULL reply_prob on a row that loses material (D-08): 0
- excluded, NULL best_prob on a row that does not lose material (256 D-04): 0

## Chosen shape

Fixed by first principles (D-01, D-03, D-08), only the coefficients are fitted: quiet rule, reply probability on losing rows (the shape that ships). The missed term is fitted at lambda 1.0.

- intercept: -1.4308
- played: -0.6065
- loss: 0.8379
- missed: 0.4971
- best_prob: 2.0786
- reply_prob: 0.9133
- AUC in sample: 0.919
- AUC 10-fold cross-validated: 0.909; over 5 seeds mean 0.908, spread 0.006

## Fair / unfair among passers at the D-15 cuts

Cells are fair / unfair among rows whose out-of-fold score of the chosen shape is at or above the cut, split by material type (loss > 0 loses, missed >= 1 misses).

| material type | rows | fair | unfair | score >= 0.50 | score >= 0.55 | score >= 0.60 | score >= 0.65 | score >= 0.70 |
|---|---|---|---|---|---|---|---|---|
| loses | 120 | 86 | 34 | 79 / 10 | 78 / 8 | 74 / 7 | 70 / 7 | 65 / 5 |
| misses | 67 | 24 | 43 | 15 / 4 | 14 / 3 | 14 / 2 | 14 / 1 | 13 / 0 |
| loses_and_misses | 38 | 25 | 13 | 22 / 9 | 22 / 9 | 20 / 8 | 20 / 8 | 20 / 6 |
| neither | 43 | 4 | 39 | 2 / 2 | 2 / 1 | 1 / 1 | 1 / 1 | 0 / 0 |
| all | 268 | 139 | 129 | 118 / 25 | 116 / 21 | 109 / 18 | 105 / 17 | 98 / 11 |

## Alternatives (information only)

D-01: the shape is fixed, these fits never choose it and the constants below are always the chosen shape's. Every shape is fitted on the same rows; AUCs are 10-fold cross-validated, mean over 5 seeds.

| shape | rows | CV AUC mean | CV AUC spread |
|---|---|---|---|
| shipped_baseline: shipped rule and shape (loss_shipped / missed_shipped, spread on losing rows) | 268 | 0.897 | 0.007 |
| quiet_spread: quiet rule, spread on losing rows | 268 | 0.903 | 0.007 |
| quiet_spread_reply: quiet rule, spread and reply probability on losing rows | 268 | 0.910 | 0.009 |
| chosen: quiet rule, reply probability on losing rows (the shape that ships) | 268 | 0.908 | 0.006 |

|AUC(chosen) - AUC(shipped_baseline)| = 0.012 against the range 0.02: within range.

## Sets 1-7 vs set 8

The chosen shape fitted on sets 1-7 (210 usable rows), scored on set 8 (58 usable rows).

- AUC on set 8: 0.838

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 24 | 12 | 12 | 0.500 |
| 0.55 | 22 | 12 | 10 | 0.545 |
| 0.60 | 22 | 12 | 10 | 0.545 |
| 0.65 | 21 | 12 | 9 | 0.571 |
| 0.70 | 19 | 12 | 7 | 0.632 |

Set 8 has about 55 decided rows, so its AUC moves by several hundredths between samples: read it as a check on the cross-validated numbers, not as a second ranking.

## Owner checks (D-13, information only, not gates)

### Commented label rows

The owner's comments and links, verbatim. The score is the chosen shape's (in sample).

| n | set | label | link | comment | score |
|---|---|---|---|---|---|
| 211 | 7 | 1 | https://flawchess.com/analysis?game_id=2333333&ply=114 | currently 6%, should be at least 90% | 0.761 |
| 216 | 7 | 1 | https://flawchess.com/analysis?game_id=1941531&ply=89 | currently 33%, should be above 60% | 0.949 |
| 217 | 7 | 1 | https://flawchess.com/analysis?game_id=2218424&ply=89 | currently 10%, should be above 70% | 0.846 |
| 219 | 7 | 1 | https://flawchess.com/analysis?game_id=1161949&ply=24 | currently 23%, should be above 60% | 0.155 |
| 220 | 7 | 0 | https://flawchess.com/analysis?game_id=1161949&ply=26 | currently 1%, should be between 30-70% | 0.419 |
| 223 | 7 | 0.5 | https://flawchess.com/analysis?game_id=2425058&ply=50 | currently 23%, should be between 30%-70% | 0.783 |
| 224 | 7 | 0 | https://flawchess.com/analysis?game_id=2474796&ply=25 | currently 9%, should be 30%-70% | 0.563 |
| 225 | 7 | 1 | https://flawchess.com/analysis?game_id=2664826&ply=74 | currently 16%, should be above 80% | 0.468 |
| 227 | 7 | 0 | https://flawchess.com/analysis?game_id=562300&ply=40 | currently 0%, should be above 20% | 0.172 |
| 228 | 7 | 1 | https://flawchess.com/analysis?game_id=2952292&ply=85 | currently 30%, should be above 70% | 0.931 |
| 232 | 7 | 1 | https://flawchess.com/analysis?game_id=2960887&ply=21 | currently 11%, should be above 70% | 0.218 |
| 233 | 7 | 1 | https://flawchess.com/analysis?game_id=1554612&ply=24 | currently 18%, should be above 70% | 0.936 |
| 234 | 7 | 1 | https://flawchess.com/analysis?game_id=3264420&ply=25 | currently 11%, should be above 70% | 0.262 |
| 239 | 7 | 0 | https://flawchess.com/analysis?game_id=2433781&ply=50 | currently 0%, should be above 20% | 0.042 |
| 240 | 7 | 1 | https://flawchess.com/analysis?game_id=2561505&ply=41 | currently 63%, should be above 70% | 0.635 |
| 244 | 8 | 1 | https://flawchess.com/analysis?game_id=2068559&ply=31 | currently 8, should be above 70% | 0.856 |
| 251 | 8 | 0 | https://flawchess.com/analysis?game_id=1871758&ply=50 | currently 52%, should be below 30% | 0.468 |
| 252 | 8 | 0 | https://flawchess.com/analysis?game_id=3143227&ply=26 | currently 88%, should be below 60% | 0.170 |
| 253 | 8 | 0.5 | https://flawchess.com/analysis?game_id=505289&ply=21 | currently 51%, should be 50-80% | 0.495 |
| 260 | 8 | 0 | https://flawchess.com/analysis?game_id=1919895&ply=5 | should be below 30% | 0.015 |
| 263 | 8 | 1 | https://flawchess.com/analysis?game_id=2674500&ply=33 | currently 13%, should be above 70% | 0.209 |
| 265 | 8 | 0 | https://flawchess.com/analysis?game_id=2494184&ply=26 | currently 99%, should be below 70% | 0.680 |
| 269 | 8 | 1 | https://flawchess.com/analysis?game_id=2048229&ply=20 | currently 40%, should be above 70% | 0.452 |
| 270 | 8 | 1 | https://flawchess.com/analysis?game_id=1635462&ply=40 | currently 40%, should be above 70% | 0.410 |
| 280 | 8 | 0 | https://flawchess.com/analysis?game_id=1586714&ply=109 | currently 17%, should be 30-70% | 0.175 |
| 282 | 8 | 1 | https://flawchess.com/analysis?game_id=2727402&ply=30 | currently 48%, should be 70-90% | 0.400 |
| 292 | 8 | 1 | https://flawchess.com/analysis?game_id=1551685&ply=33 | currently 12%, should be above 70% | 0.984 |
| 294 | 8 | 1 | https://flawchess.com/analysis?game_id=2881177&ply=17 | currently 66% should be above 70% | 0.918 |

### Pure-miss pass rate

Among the rows of material type 'misses' (nothing lost, material left on the table), the rows whose out-of-fold score is at or above each cut.

| cut | passers | rows | pass rate |
|---|---|---|---|
| 0.50 | 19 | 67 | 0.284 |
| 0.55 | 17 | 67 | 0.254 |
| 0.60 | 16 | 67 | 0.239 |
| 0.65 | 15 | 67 | 0.224 |
| 0.70 | 13 | 67 | 0.194 |

The two owner fixtures (games 817357 ply 24 and 820181 ply 65) are dev-DB games that are not on prod and not in the features table: they are scored at the checkpoint from tests/services/facepalm_owner_fixtures.py.

## Extra rows

Unlabelled rows scored with the constants below (threshold 0.7).

- row extra (game 2099808 ply 23): played_prob 0.095, loss 0.000, missed 0.000, reply_prob 0.133: score 0.091, below threshold
- row extra (game 2883555 ply 47): played_prob 0.030, loss 2.935, missed 0.000, reply_prob 0.200: score 0.825, AT OR ABOVE THRESHOLD

## Constants

```python
FACEPALM_INTERCEPT: float = -1.4308
FACEPALM_PLAYED_COEF: float = -0.6065
FACEPALM_LOSS_COEF: float = 0.8379
FACEPALM_MISSED_COEF: float = 0.4971
FACEPALM_BEST_PROB_COEF: float = 2.0786
FACEPALM_REPLY_PROB_COEF: float = 0.9133
```

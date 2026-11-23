# Facepalm score fit

A ranking, not a probability (250 D-01): the labels are mostly rule passers, so the fitted values are not calibrated to all blunders.

Features: facepalm-features-2026-11-23.tsv. Seed 250 (repeats 250-254), 10 folds, threshold 0.7. The model shape is fixed (D-01), label sets 1 to 8 are used as they are (D-14).

## Data

- rows in the features file: 291
- usable for the fit: 268 (139 fair, 129 unfair)
- excluded, label 0.5 (undecided): 11
- excluded, no label (extra row): 2
- excluded, NULL played_prob: 0
- excluded, NULL loss (no settled line): 10
- excluded, NULL reply_prob on an allowed loss (262 D-04): 0
- excluded, NULL best_prob on a row that is not an allowed loss (262 D-04): 0

## Chosen shape

Fixed by first principles (D-01, D-03, D-08), only the coefficients are fitted: new inputs, reply probability on allowed losses (the type rule, the shape that ships). The missed term is fitted at lambda 1.0.

- intercept: -1.7891
- played: -0.6193
- loss: 0.8879
- missed: 0.3993
- best_prob: 1.1635
- reply_prob: 0.8057
- AUC in sample: 0.901
- AUC 10-fold cross-validated: 0.890; over 5 seeds mean 0.889, spread 0.005

## Fair / unfair among passers at the D-15 cuts

Cells are fair / unfair among rows whose out-of-fold score of the chosen shape is at or above the cut, split by material type (loss > 0 loses, missed >= 1 misses).

| material type | rows | fair | unfair | score >= 0.50 | score >= 0.55 | score >= 0.60 | score >= 0.65 | score >= 0.70 |
|---|---|---|---|---|---|---|---|---|
| loses | 119 | 84 | 35 | 76 / 9 | 73 / 8 | 69 / 8 | 64 / 6 | 63 / 6 |
| misses | 66 | 23 | 43 | 15 / 3 | 15 / 3 | 14 / 1 | 11 / 0 | 11 / 0 |
| loses_and_misses | 43 | 28 | 15 | 22 / 9 | 22 / 9 | 22 / 8 | 21 / 8 | 20 / 5 |
| neither | 40 | 4 | 36 | 1 / 2 | 1 / 1 | 1 / 0 | 1 / 0 | 0 / 0 |
| all | 268 | 139 | 129 | 114 / 23 | 111 / 21 | 106 / 17 | 97 / 14 | 94 / 11 |

## Alternatives (information only)

D-01: the shape is fixed, these fits never choose it and the constants below are always the chosen shape's. Every shape is fitted on the same rows; AUCs are 10-fold cross-validated, mean over 5 seeds.

| shape | rows | CV AUC mean | CV AUC spread |
|---|---|---|---|
| shipped_baseline: shipped rule and shape (Phase 259: loss_shipped / missed_shipped, reply probability when loss > 0) | 268 | 0.908 | 0.006 |
| quiet_spread: quiet rule, spread on losing rows | 268 | 0.883 | 0.007 |
| quiet_spread_reply: quiet rule, spread and reply probability on losing rows | 268 | 0.888 | 0.007 |
| chosen: new inputs, reply probability on allowed losses (the type rule, the shape that ships) | 268 | 0.889 | 0.005 |
| old_gate: new inputs with the Phase 259 gate (reply probability when loss > 0), the D-05 reference | 268 | 0.902 | 0.009 |

|AUC(chosen) - AUC(shipped_baseline)| = 0.019 against the range 0.02: within range.

## Old gate reference (D-05, information only)

The model is fitted with the type-rule gate (262 D-04). This line fits the same shape on the same rows and inputs with the Phase 259 gate (the reply probability whenever loss > 0) and only informs (259 D-01): it never chooses the constants.

| gate | rows | CV AUC mean | fair / unfair at 0.70 (out of fold) |
|---|---|---|---|
| type (chosen) | 268 | 0.889 | 94 / 11 |
| loss (old gate) | 268 | 0.902 | 99 / 12 |

## Rows whose inputs changed

Rows whose (loss, missed) pair under the current material rule differs from the Phase 259 pair (loss_shipped, missed_shipped).

| n | set | label | loss_shipped / missed_shipped | loss / missed |
|---|---|---|---|---|
| 31 | 2 | 1 | 1.000 / 0.000 | 1.000 / 5.000 |
| 35 | 2 | 1 | 0.000 / 1.484 | 2.419 / 1.484 |
| 57 | 3 | 0 | 0.000 / 0.000 | 0.000 / 0.129 |
| 139 | 5 | 0 | 0.903 / 0.484 | 2.935 / 0.000 |
| 170 | 6 | 0 | 0.000 / 0.903 | 0.387 / 1.000 |
| 177 | 6 | 0 | 0.000 / 0.000 | 3.871 / 2.323 |
| 231 | 7 | 1 | 0.774 / 0.774 | 1.903 / 1.194 |
| 266 | 8 | 0 | 0.000 / 0.000 | 1.129 / 0.000 |

## Sets 1-7 vs set 8

The chosen shape fitted on sets 1-7 (210 usable rows), scored on set 8 (58 usable rows).

- AUC on set 8: 0.857

| threshold | passers | fair | unfair | fair share |
|---|---|---|---|---|
| 0.50 | 26 | 13 | 13 | 0.500 |
| 0.55 | 22 | 12 | 10 | 0.545 |
| 0.60 | 20 | 12 | 8 | 0.600 |
| 0.65 | 19 | 12 | 7 | 0.632 |
| 0.70 | 19 | 12 | 7 | 0.632 |

Set 8 has about 55 decided rows, so its AUC moves by several hundredths between samples: read it as a check on the cross-validated numbers, not as a second ranking.

## Owner checks (D-13, information only, not gates)

### Commented label rows

The owner's comments and links, verbatim. The score is the chosen shape's (in sample).

| n | set | label | link | comment | score |
|---|---|---|---|---|---|
| 211 | 7 | 1 | https://flawchess.com/analysis?game_id=2333333&ply=114 | currently 6%, should be at least 90% | 0.725 |
| 216 | 7 | 1 | https://flawchess.com/analysis?game_id=1941531&ply=89 | currently 33%, should be above 60% | 0.955 |
| 217 | 7 | 1 | https://flawchess.com/analysis?game_id=2218424&ply=89 | currently 10%, should be above 70% | 0.807 |
| 219 | 7 | 1 | https://flawchess.com/analysis?game_id=1161949&ply=24 | currently 23%, should be above 60% | 0.322 |
| 220 | 7 | 0 | https://flawchess.com/analysis?game_id=1161949&ply=26 | currently 1%, should be between 30-70% | 0.413 |
| 223 | 7 | 0.5 | https://flawchess.com/analysis?game_id=2425058&ply=50 | currently 23%, should be between 30%-70% | 0.796 |
| 224 | 7 | 0 | https://flawchess.com/analysis?game_id=2474796&ply=25 | currently 9%, should be 30%-70% | 0.634 |
| 225 | 7 | 1 | https://flawchess.com/analysis?game_id=2664826&ply=74 | currently 16%, should be above 80% | 0.450 |
| 227 | 7 | 0 | https://flawchess.com/analysis?game_id=562300&ply=40 | currently 0%, should be above 20% | 0.253 |
| 228 | 7 | 1 | https://flawchess.com/analysis?game_id=2952292&ply=85 | currently 30%, should be above 70% | 0.892 |
| 232 | 7 | 1 | https://flawchess.com/analysis?game_id=2960887&ply=21 | currently 11%, should be above 70% | 0.248 |
| 233 | 7 | 1 | https://flawchess.com/analysis?game_id=1554612&ply=24 | currently 18%, should be above 70% | 0.900 |
| 234 | 7 | 1 | https://flawchess.com/analysis?game_id=3264420&ply=25 | currently 11%, should be above 70% | 0.209 |
| 239 | 7 | 0 | https://flawchess.com/analysis?game_id=2433781&ply=50 | currently 0%, should be above 20% | 0.177 |
| 240 | 7 | 1 | https://flawchess.com/analysis?game_id=2561505&ply=41 | currently 63%, should be above 70% | 0.034 |
| 244 | 8 | 1 | https://flawchess.com/analysis?game_id=2068559&ply=31 | currently 8, should be above 70% | 0.846 |
| 251 | 8 | 0 | https://flawchess.com/analysis?game_id=1871758&ply=50 | currently 52%, should be below 30% | 0.480 |
| 252 | 8 | 0 | https://flawchess.com/analysis?game_id=3143227&ply=26 | currently 88%, should be below 60% | 0.182 |
| 253 | 8 | 0.5 | https://flawchess.com/analysis?game_id=505289&ply=21 | currently 51%, should be 50-80% | 0.473 |
| 260 | 8 | 0 | https://flawchess.com/analysis?game_id=1919895&ply=5 | should be below 30% | 0.098 |
| 263 | 8 | 1 | https://flawchess.com/analysis?game_id=2674500&ply=33 | currently 13%, should be above 70% | 0.381 |
| 265 | 8 | 0 | https://flawchess.com/analysis?game_id=2494184&ply=26 | currently 99%, should be below 70% | 0.709 |
| 269 | 8 | 1 | https://flawchess.com/analysis?game_id=2048229&ply=20 | currently 40%, should be above 70% | 0.505 |
| 270 | 8 | 1 | https://flawchess.com/analysis?game_id=1635462&ply=40 | currently 40%, should be above 70% | 0.511 |
| 280 | 8 | 0 | https://flawchess.com/analysis?game_id=1586714&ply=109 | currently 17%, should be 30-70% | 0.266 |
| 282 | 8 | 1 | https://flawchess.com/analysis?game_id=2727402&ply=30 | currently 48%, should be 70-90% | 0.347 |
| 292 | 8 | 1 | https://flawchess.com/analysis?game_id=1551685&ply=33 | currently 12%, should be above 70% | 0.978 |
| 294 | 8 | 1 | https://flawchess.com/analysis?game_id=2881177&ply=17 | currently 66% should be above 70% | 0.901 |

### Pure-miss pass rate

Among the rows of material type 'misses' (nothing lost, material left on the table), the rows whose out-of-fold score is at or above each cut.

| cut | passers | rows | pass rate |
|---|---|---|---|
| 0.50 | 18 | 66 | 0.273 |
| 0.55 | 18 | 66 | 0.273 |
| 0.60 | 15 | 66 | 0.227 |
| 0.65 | 11 | 66 | 0.167 |
| 0.70 | 11 | 66 | 0.167 |

The two owner fixtures (games 817357 ply 24 and 820181 ply 65) are dev-DB games that are not on prod and not in the features table: they are scored at the checkpoint from tests/services/facepalm_owner_fixtures.py.

## Extra rows

Unlabelled rows scored with the constants below (threshold 0.7).

- row extra (game 2099808 ply 23): played_prob 0.095, loss 0.000, missed 0.000, reply_prob 0.133: score 0.162, below threshold
- row extra (game 2883555 ply 47): played_prob 0.030, loss 2.935, missed 0.000, reply_prob 0.200: score 0.825, AT OR ABOVE THRESHOLD

## Constants

```python
FACEPALM_INTERCEPT: float = -1.7891
FACEPALM_PLAYED_COEF: float = -0.6193
FACEPALM_LOSS_COEF: float = 0.8879
FACEPALM_MISSED_COEF: float = 0.3993
FACEPALM_BEST_PROB_COEF: float = 1.1635
FACEPALM_REPLY_PROB_COEF: float = 0.8057
```

## Prod facts at the 262 checkpoint (appended by the orchestrator, not generated)

Read on 2026-11-23 from prod, read-only, one connection at a time, with the constants above in the
working tree only (restored after the runs; nothing is committed in the app). The line-repair feed was
running on prod during the reads (owner's go-ahead), so stored lines were still moving and every count
is a snapshot.

### Rows the new gate leaves unscored (D-04, accepted)

Stored (old-rule) material pair, so promotion rows are approximate until the pass:

| Rows (severity 2, played probability present, 0 < loss < missed) | Count |
|---|---|
| all mixed rows | 392,581 |
| without a best-move probability (unscored under the type gate) | 161 |
| of those, with a reply probability (they lose the score they have today) | 161 |

CONTEXT expected about 1,600; the best-move probability backfill has filled most of them since.
refit_shift on its 10% game sample agrees: 17 rows lose a score (about 170 on all prod) and 100 gain
one (about 1,000). Its 719 sampled rows "unscored with a settled loss" (about 7,190) also count rows
that have no key-move probability under either gate, so they are unscored today as well.

### Passers and movement at 0.70 (refit_shift, games with id % 10 = 0, 472,589 blunders)

| cut | shipped (Phase 259) | candidate (Phase 262) | change |
|---|---|---|---|
| 0.50 | 209,271 | 196,297 | -6.2% |
| 0.55 | 195,702 | 182,089 | -7.0% |
| 0.60 | 182,161 | 167,884 | -7.8% |
| 0.65 | 168,405 | 154,033 | -8.5% |
| 0.70 | 154,205 | 140,082 | -9.2% |

At 0.70, 3,835 sampled rows enter and 17,958 leave. By candidate type: allowed loss 1,797 enter and
7,783 leave; missed win 2,038 enter and 10,175 leave. Own blunders at 0.70 (drill-pool proxy): 77,680
shipped against 70,491 candidate (-9.3%). Rows whose inputs change with the promotion rule: 12,737
sampled, about 127,370 on all prod, which matches the pass estimate of about 127k real changes.
Multiply sample counts by 10 for prod.

### Drill pool by cut (calibration, 25 permille sample, candidate model)

Usable own blunder windows per non-guest user, p25 / median: 142.8 / 524.0 at 0.50, 122.4 / 446.4 at
0.60, 101.1 / 370.1 at 0.70, 80.1 / 292.9 at 0.80. The shipped model on 2026-11-22 gave 112.9 / 413.9
at 0.70, so the own pool at 0.70 shrinks by about 10%. Foreign qualifying blunders at 0.70 per rating
level run from 23,040 (level 800) to 153,920 (level 1200); the thinnest levels are 2400 (17,200) and
2600 (11,200). The calibration reads the stored inputs, so promotion rows still carry the old rule there.

### Caught rate by band, snapshot against rescored (for HARD_TO_CATCH_SCORE_BELOW)

Main arm, own and foreign together, reached / caught:

| band | snapshot score | rescored (candidate) |
|---|---|---|
| 0.3-0.5 | 0 / 0 | 1 / 1 |
| 0.6-0.7 | 0 / 0 | 3 / 2 |
| 0.7-0.8 | 7 / 2 (29%) | 11 / 4 (36%) |
| 0.8-0.9 | 23 / 14 (61%) | 20 / 12 (60%) |
| 0.9-1.0 | 36 / 23 (64%) | 31 / 20 (65%) |

Five main-arm windows drop below 0.70 on the candidate score; one drops below 0.5. The exploration arm
has 7 windows and the legacy arm (live score in both reports) is unchanged: 33% to 41% below 0.5 and
43% to 67% above 0.7. Too few windows to move the 0.5 cut on evidence.

### Index check

Both facepalm reader statements of user 95 read game_flaws through
`Index Only Scan using ix_game_flaws_facepalm_inputs` under the new gate (counts 172 to 195 ms,
comparison 18 ms, JIT off). No index rebuild.

### Reports

- reports/blunder-check/refit-shift-2026-11-23.md (with 20 newly passing rows to spot check)
- reports/blunder-check/blunder-check-calibration-2026-11-23.md and spot-check-2026-11-23.md
- reports/blunder-check/caught-rate-rescore-262-2026-11-23.md
- reports/blunder-check/facepalm-explain-262.md

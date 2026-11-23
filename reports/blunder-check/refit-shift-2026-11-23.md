# Facepalm refit shift (Phase 262 owner checkpoint)

Target: prod. Sample: games with id % 10 == 0, 472589 blunders of line-stamped games with a played-move probability. Counts are raw sample counts followed by the count times 10.

## Versions

- shipped (Phase 259): INTERCEPT -1.4308, PLAYED_COEF -0.6065, LOSS_COEF 0.8379, MISSED_COEF 0.4971, BEST_PROB_COEF 2.0786, REPLY_PROB_COEF 0.9133; gate loss (reply term on any loss above zero); stored inputs.
- candidate (Phase 262): INTERCEPT -1.7891, PLAYED_COEF -0.6193, LOSS_COEF 0.8879, MISSED_COEF 0.3993, BEST_PROB_COEF 1.1635, REPLY_PROB_COEF 0.8057; gate type (reply term on an allowed loss); promotion rows recomputed with the app rule.

## Passers at the D-15 cuts

| cut | shipped | candidate |
|---|---|---|
| 0.50 | 209271 (x10 = 2092710) | 196297 (x10 = 1962970) |
| 0.55 | 195702 (x10 = 1957020) | 182089 (x10 = 1820890) |
| 0.60 | 182161 (x10 = 1821610) | 167884 (x10 = 1678840) |
| 0.65 | 168405 (x10 = 1684050) | 154033 (x10 = 1540330) |
| 0.70 | 154205 (x10 = 1542050) | 140082 (x10 = 1400820) |

## Enter and leave at 0.70 by type

A row enters when the candidate passes the cut and the shipped score did not; it leaves in the opposite case.

| type | enter (by candidate type) | enter (by shipped type) | leave (by candidate type) | leave (by shipped type) |
|---|---|---|---|---|
| allowed_loss | 1797 (x10 = 17970) | 551 (x10 = 5510) | 7783 (x10 = 77830) | 7949 (x10 = 79490) |
| missed_win | 2038 (x10 = 20380) | 3282 (x10 = 32820) | 10175 (x10 = 101750) | 10009 (x10 = 100090) |
| unknown | 0 (x10 = 0) | 2 (x10 = 20) | 0 (x10 = 0) | 0 (x10 = 0) |
| total | 3835 (x10 = 38350) | 3835 (x10 = 38350) | 17958 (x10 = 179580) | 17958 (x10 = 179580) |

## Own blunders at 0.70 (drill-pool proxy)

- shipped: 77680 (x10 = 776800)
- candidate: 70491 (x10 = 704910)

## Scored and unscored rows

- rows whose inputs changed (a promotion): 12737 (x10 = 127370)
- rows that lose a score (shipped scored, candidate not): 17 (x10 = 170)
- rows that gain a score (shipped unscored, candidate scored): 100 (x10 = 1000)
- rows the candidate gate leaves unscored with a settled loss (a NULL key-move probability, D-04): 719 (x10 = 7190)

## Newly passing 0.70

Seeded sample (seed 262) of at most 20 rows that pass under the candidate and did not under the shipped version.

| link | own | type shipped / candidate | pair shipped | pair candidate | score shipped / candidate | moved by |
|---|---|---|---|---|---|---|
| https://flawchess.com/analysis?game_id=476880&ply=14 | no | missed_win / missed_win | 0.581 / 1.903 | 0.581 / 1.903 | 0.650 / 0.721 | gate and coefficients |
| https://flawchess.com/analysis?game_id=1212610&ply=14 | yes | missed_win / missed_win | 0.484 / 1.000 | 0.484 / 1.000 | 0.400 / 0.787 | gate and coefficients |
| https://flawchess.com/analysis?game_id=1428790&ply=56 | yes | missed_win / missed_win | 0.032 / 3.774 | 0.032 / 3.774 | 0.536 / 0.725 | gate and coefficients |
| https://flawchess.com/analysis?game_id=1433480&ply=120 | yes | missed_win / allowed_loss | 0.000 / 0.000 | 3.000 / 0.000 | 0.118 / 0.774 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=1598400&ply=49 | yes | missed_win / allowed_loss | 0.000 / 0.000 | 2.000 / 1.000 | 0.082 / 0.820 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=1657420&ply=16 | no | missed_win / missed_win | 0.032 / 5.000 | 0.032 / 5.000 | 0.528 / 0.846 | gate and coefficients |
| https://flawchess.com/analysis?game_id=1676130&ply=110 | no | missed_win / allowed_loss | 0.000 / 0.000 | 1.935 / 0.000 | 0.004 / 0.829 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=1869470&ply=44 | yes | missed_win / missed_win | 0.065 / 5.000 | 0.065 / 5.000 | 0.698 / 0.821 | gate and coefficients |
| https://flawchess.com/analysis?game_id=1942520&ply=107 | no | allowed_loss / missed_win | 0.194 / 0.000 | 0.129 / 4.613 | 0.501 / 0.938 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=1948350&ply=105 | no | missed_win / allowed_loss | 0.000 / 0.000 | 2.419 / 0.000 | 0.034 / 0.782 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=2087540&ply=63 | yes | missed_win / missed_win | 0.516 / 5.000 | 0.516 / 5.000 | 0.649 / 0.759 | gate and coefficients |
| https://flawchess.com/analysis?game_id=2305770&ply=62 | yes | missed_win / missed_win | 0.000 / 1.032 | 1.129 / 1.484 | 0.418 / 0.772 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=2425540&ply=8 | yes | missed_win / missed_win | 0.903 / 1.000 | 0.903 / 1.000 | 0.628 / 0.811 | gate and coefficients |
| https://flawchess.com/analysis?game_id=2446520&ply=2 | yes | allowed_loss / allowed_loss | 1.452 / 0.484 | 4.032 / 0.484 | 0.412 / 0.874 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=2688970&ply=33 | no | missed_win / missed_win | 1.387 / 3.000 | 1.387 / 3.000 | 0.696 / 0.873 | gate and coefficients |
| https://flawchess.com/analysis?game_id=2791820&ply=88 | no | missed_win / allowed_loss | 0.000 / 0.774 | 5.000 / 0.774 | 0.034 / 0.948 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=2862960&ply=27 | no | missed_win / missed_win | 1.484 / 3.000 | 1.484 / 3.000 | 0.686 / 0.846 | gate and coefficients |
| https://flawchess.com/analysis?game_id=2880830&ply=72 | yes | missed_win / missed_win | 0.000 / 1.903 | 0.000 / 2.935 | 0.693 / 0.778 | promotion (inputs changed) |
| https://flawchess.com/analysis?game_id=3042610&ply=20 | no | missed_win / missed_win | 0.097 / 3.000 | 0.097 / 3.000 | 0.696 / 0.858 | gate and coefficients |
| https://flawchess.com/analysis?game_id=3086800&ply=57 | no | missed_win / missed_win | 0.000 / 0.774 | 1.097 / 1.226 | 0.375 / 0.721 | promotion (inputs changed) |

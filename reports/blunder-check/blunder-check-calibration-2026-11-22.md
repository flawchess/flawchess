# Blunder-check calibration report

## How to read this report

- **Population:** fully evaluated games on chess.com, lichess (pasted and bot games are out). Database: `flawchess`. Run date: 2026-11-22.
- **Sampling:** deterministic, 25 permille (2.5%) of games chosen by md5 residue of the game id; the same sample on every re-run.
- **Expected score (ES):** every ES comes from the flaw classifier's own per-ply pass (`_run_all_moves_pass`), from the mover's point of view. Pre-move ES is the ES before the user's move, `ES_played` the ES after the blunder, `ES_ref` the user's ES before the opponent's previous move (what the user would have had without the gift).
- **Cases (D-13):** *allowed* = the blunder is not a miss (the opponent's previous move was not a mistake or blunder). *Pure miss* = a miss whose `ES_played` is at least `ES_ref` minus the inaccuracy drop: the user only gave back what the opponent gifted. *Mixed* = a miss that lost more than the gift. *Unclassified* = a miss without usable ES.
- **Facepalm score (250 D-01, 254 D-01):** a ranking of how careless a blunder is at the mover's level, fitted on the owner's labels. The report reads the stored FACTS of each blunder (the played move's Maia probability, the opponent's reply spread, the depth-3 material of the played and best lines, both mate plies, the best move's probability and the pre-blunder spread) and scores them with the Python twin at the drill lambda (1.0) and the constants and model of this checkout, never the stored score column, so a candidate refit is judged here before it ships. It is not a probability and not a share of peers; a blunder qualifies when its score is at least the chosen threshold. A blunder without a score never qualifies; the Facepalm score section tells why.
- **Window mix (250 D-12):** every slot independently draws a herring (33%), an own blunder (33%) or a foreign blunder (33%); window length is uniform over 3 to 5 user moves for both kinds, a blunder's position follows the per-move hazard 0.265 within that length, 1 lead-in plies. Pure misses are capped at 30% of the blunder supply (report estimate only).
- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only aggregates times per-bucket sample rates, with rating groups approximating each game's exact Elo. It is an estimate, not an exact count.
- **Chosen values:** facepalm threshold = 0.5, eval band [0.10, 0.90]. These are a recommendation only; no constant is wired into app code by this report.
- Guest users' flaws are never Maia-scored, so guest games are excluded from every section except the sample counts.

## Sample

- Games sampled: 27258 (113 guest, excluded below)
- Games skipped for a ply gap: 55
- Unrated games (no rating at game time): 0 (0 user-side blunders not bucketed)
- User-side blunders (rated, non-guest): 59482

| Elo bucket | games (engine) | games (lichess) | blunders (engine) | blunders (lichess) |
| --- | --- | --- | --- | --- |
| <800 | 2641 | 74 | 6960 | 297 |
| 800-1199 | 3863 | 584 | 9201 | 1488 |
| 1200-1599 | 6156 | 701 | 13597 | 1682 |
| 1600-1999 | 7357 | 832 | 15027 | 1716 |
| 2000-2399 | 3588 | 410 | 7261 | 652 |
| 2400+ | 792 | 147 | 1340 | 261 |

## Control

Stored `game_flaws` (ply, severity) pairs against the mistakes and blunders recomputed from the per-ply evals (all sampled games, both colors; D-13).

- Agreement: 197221 of 197329 = 99.9% (n=197329)

## Cases by Elo bucket

| Elo bucket | blunders | allowed | pure_miss | mixed | unclassified | mixed / (pure miss + mixed) |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 7257 | 54.3% (n=7257) | 27.6% (n=7257) | 18.1% (n=7257) | 0.0% (n=7257) | 39.6% (n=3318) |
| 800-1199 | 10689 | 58.9% (n=10689) | 24.3% (n=10689) | 16.7% (n=10689) | 0.0% (n=10689) | 40.8% (n=4392) |
| 1200-1599 | 15279 | 62.5% (n=15279) | 22.6% (n=15279) | 14.9% (n=15279) | 0.0% (n=15279) | 39.7% (n=5734) |
| 1600-1999 | 16743 | 64.2% (n=16743) | 22.3% (n=16743) | 13.6% (n=16743) | 0.0% (n=16743) | 37.9% (n=6000) |
| 2000-2399 | 7913 | 64.8% (n=7913) | 21.6% (n=7913) | 13.6% (n=7913) | 0.0% (n=7913) | 38.6% (n=2786) |
| 2400+ | 1601 | 64.0% (n=1601) | 22.9% (n=1601) | 13.1% (n=1601) | 0.0% (n=1601) | 36.3% (n=576) |
| all | 59482 | 61.7% (n=59482) | 23.3% (n=59482) | 15.0% (n=59482) | 0.0% (n=59482) | 39.2% (n=22806) |

## Facepalm score

User-side blunders of rated, non-guest games and their stored facepalm score (250 D-01): a ranking of how careless the blunder is at the mover's level, not a share of peers. `scored` is the share with a score; the next four columns split the unscored ones by reason (shares of all user blunders): no reply spread yet, no stored engine line, a line shorter than 3 plies without an early mate (or one that cannot be replayed), and a missing played-move probability. The `pass` columns are shares of the scored blunders at or above each threshold; `qualifying of all` is the share of every user blunder that qualifies at the chosen threshold (an unscored blunder never qualifies).

| Elo bucket | user blunders | scored | no spread | no line | line too short | no played prob | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | qualifying of all (>= 0.50) | score q1 / median / q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 7257 | 93.4% (n=7257) | 0.0% (n=7257) | 6.3% (n=7257) | 0.3% (n=7257) | 0.0% (n=7257) | 52.2% (n=6779) | 46.5% (n=6779) | 40.0% (n=6779) | 33.3% (n=6779) | 48.7% (n=7257) | 0.118 / 0.542 / 0.889 |
| 800-1199 | 10689 | 93.6% (n=10689) | 0.0% (n=10689) | 6.2% (n=10689) | 0.2% (n=10689) | 0.0% (n=10689) | 50.1% (n=10001) | 43.6% (n=10001) | 37.2% (n=10001) | 30.3% (n=10001) | 46.9% (n=10689) | 0.121 / 0.503 / 0.867 |
| 1200-1599 | 15279 | 93.8% (n=15279) | 0.0% (n=15279) | 5.9% (n=15279) | 0.3% (n=15279) | 0.0% (n=15279) | 47.6% (n=14336) | 41.1% (n=14336) | 35.1% (n=14336) | 28.3% (n=14336) | 44.6% (n=15279) | 0.106 / 0.461 / 0.842 |
| 1600-1999 | 16743 | 92.3% (n=16743) | 0.0% (n=16743) | 7.4% (n=16743) | 0.2% (n=16743) | 0.0% (n=16743) | 45.7% (n=15457) | 39.9% (n=15457) | 33.5% (n=15457) | 26.8% (n=15457) | 42.2% (n=16743) | 0.099 / 0.436 / 0.824 |
| 2000-2399 | 7913 | 93.7% (n=7913) | 0.0% (n=7913) | 6.1% (n=7913) | 0.2% (n=7913) | 0.0% (n=7913) | 48.1% (n=7415) | 41.5% (n=7415) | 34.7% (n=7415) | 27.7% (n=7415) | 45.1% (n=7913) | 0.125 / 0.475 / 0.833 |
| 2400+ | 1601 | 99.1% (n=1601) | 0.1% (n=1601) | 0.7% (n=1601) | 0.1% (n=1601) | 0.0% (n=1601) | 35.1% (n=1587) | 29.4% (n=1587) | 23.2% (n=1587) | 17.6% (n=1587) | 34.8% (n=1601) | 0.058 / 0.304 / 0.660 |
| all | 59482 | 93.4% (n=59482) | 0.0% (n=59482) | 6.3% (n=59482) | 0.2% (n=59482) | 0.0% (n=59482) | 47.8% (n=55575) | 41.6% (n=55575) | 35.2% (n=55575) | 28.5% (n=55575) | 44.7% (n=59482) | 0.109 / 0.465 / 0.844 |

## Pass shares by material type

User-side blunders of rated, non-guest games by what they do to the material balance (D-13), read from the stored decaying-mean inputs (259 D-03): *loses* = the played line loses material or mates, *misses* = the best line gains material (at least 1) or mates, *loses and misses* = both, *neither*, and *unknown* = no loss input is stored. Scores use the drill lambda (1.0) and the model in this checkout, computed from the stored facts. `scored` is the share of the type with a score; each `pass` column is the share of those scored blunders at or above the cut; the last column is the type's share of all user blunders in the row group.

| material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- |
| loses | 26475 | 100.0% (n=26475) | 64.1% (n=26475) | 55.9% (n=26475) | 47.4% (n=26475) | 38.4% (n=26475) | 44.5% (n=59482) |
| misses | 8637 | 100.0% (n=8637) | 35.6% (n=8636) | 29.3% (n=8636) | 22.6% (n=8636) | 15.3% (n=8636) | 14.5% (n=59482) |
| loses_and_misses | 7027 | 100.0% (n=7027) | 83.7% (n=7027) | 77.8% (n=7027) | 70.6% (n=7027) | 61.5% (n=7027) | 11.8% (n=59482) |
| neither | 13534 | 99.3% (n=13534) | 4.8% (n=13437) | 2.5% (n=13437) | 0.8% (n=13437) | 0.1% (n=13437) | 22.8% (n=59482) |
| unknown | 3809 | 0.0% (n=3809) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.4% (n=59482) |

### By Elo bucket

| Elo bucket | material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | loses | 3121 | 100.0% (n=3121) | 67.3% (n=3121) | 59.5% (n=3121) | 51.0% (n=3121) | 42.9% (n=3121) | 43.0% (n=7257) |
| <800 | misses | 1251 | 100.0% (n=1251) | 29.5% (n=1251) | 23.7% (n=1251) | 17.8% (n=1251) | 10.3% (n=1251) | 17.2% (n=7257) |
| <800 | loses_and_misses | 1239 | 100.0% (n=1239) | 85.2% (n=1239) | 80.0% (n=1239) | 72.5% (n=1239) | 63.8% (n=1239) | 17.1% (n=7257) |
| <800 | neither | 1181 | 98.9% (n=1181) | 1.0% (n=1168) | 0.3% (n=1168) | 0.1% (n=1168) | 0.0% (n=1168) | 16.3% (n=7257) |
| <800 | unknown | 465 | 0.0% (n=465) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.4% (n=7257) |
| 800-1199 | loses | 4858 | 100.0% (n=4858) | 65.6% (n=4858) | 57.1% (n=4858) | 48.4% (n=4858) | 39.3% (n=4858) | 45.4% (n=10689) |
| 800-1199 | misses | 1634 | 100.0% (n=1634) | 35.1% (n=1634) | 28.8% (n=1634) | 21.5% (n=1634) | 13.7% (n=1634) | 15.3% (n=10689) |
| 800-1199 | loses_and_misses | 1387 | 100.0% (n=1387) | 85.1% (n=1387) | 78.6% (n=1387) | 72.5% (n=1387) | 64.5% (n=1387) | 13.0% (n=10689) |
| 800-1199 | neither | 2140 | 99.2% (n=2140) | 3.5% (n=2122) | 1.5% (n=2122) | 0.3% (n=2122) | 0.0% (n=2122) | 20.0% (n=10689) |
| 800-1199 | unknown | 670 | 0.0% (n=670) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.3% (n=10689) |
| 1200-1599 | loses | 6975 | 100.0% (n=6975) | 64.7% (n=6975) | 56.0% (n=6975) | 48.0% (n=6975) | 38.8% (n=6975) | 45.7% (n=15279) |
| 1200-1599 | misses | 2179 | 100.0% (n=2179) | 33.9% (n=2179) | 27.5% (n=2179) | 21.4% (n=2179) | 14.2% (n=2179) | 14.3% (n=15279) |
| 1200-1599 | loses_and_misses | 1735 | 100.0% (n=1735) | 82.0% (n=1735) | 76.1% (n=1735) | 69.3% (n=1735) | 60.3% (n=1735) | 11.4% (n=15279) |
| 1200-1599 | neither | 3478 | 99.1% (n=3478) | 4.2% (n=3447) | 1.9% (n=3447) | 0.5% (n=3447) | 0.0% (n=3447) | 22.8% (n=15279) |
| 1200-1599 | unknown | 912 | 0.0% (n=912) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.0% (n=15279) |
| 1600-1999 | loses | 7387 | 100.0% (n=7387) | 62.1% (n=7387) | 54.4% (n=7387) | 45.9% (n=7387) | 37.1% (n=7387) | 44.1% (n=16743) |
| 1600-1999 | misses | 2274 | 100.0% (n=2274) | 37.4% (n=2273) | 31.2% (n=2273) | 24.6% (n=2273) | 17.4% (n=2273) | 13.6% (n=16743) |
| 1600-1999 | loses_and_misses | 1697 | 100.0% (n=1697) | 83.6% (n=1697) | 77.5% (n=1697) | 69.7% (n=1697) | 59.0% (n=1697) | 10.1% (n=16743) |
| 1600-1999 | neither | 4122 | 99.5% (n=4122) | 5.2% (n=4100) | 3.1% (n=4100) | 1.2% (n=4100) | 0.1% (n=4100) | 24.6% (n=16743) |
| 1600-1999 | unknown | 1263 | 0.0% (n=1263) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 7.5% (n=16743) |
| 2000-2399 | loses | 3471 | 100.0% (n=3471) | 64.2% (n=3471) | 56.2% (n=3471) | 47.3% (n=3471) | 37.7% (n=3471) | 43.9% (n=7913) |
| 2000-2399 | misses | 1088 | 100.0% (n=1088) | 44.0% (n=1088) | 36.5% (n=1088) | 28.9% (n=1088) | 21.3% (n=1088) | 13.7% (n=7913) |
| 2000-2399 | loses_and_misses | 815 | 100.0% (n=815) | 84.5% (n=815) | 79.1% (n=815) | 71.4% (n=815) | 62.7% (n=815) | 10.3% (n=7913) |
| 2000-2399 | neither | 2054 | 99.4% (n=2054) | 8.2% (n=2041) | 4.3% (n=2041) | 1.6% (n=2041) | 0.1% (n=2041) | 26.0% (n=7913) |
| 2000-2399 | unknown | 485 | 0.0% (n=485) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.1% (n=7913) |
| 2400+ | loses | 663 | 100.0% (n=663) | 51.9% (n=663) | 43.1% (n=663) | 35.4% (n=663) | 25.8% (n=663) | 41.4% (n=1601) |
| 2400+ | misses | 211 | 100.0% (n=211) | 29.9% (n=211) | 26.5% (n=211) | 19.4% (n=211) | 13.7% (n=211) | 13.2% (n=1601) |
| 2400+ | loses_and_misses | 154 | 100.0% (n=154) | 74.7% (n=154) | 68.2% (n=154) | 56.5% (n=154) | 51.9% (n=154) | 9.6% (n=1601) |
| 2400+ | neither | 559 | 100.0% (n=559) | 6.3% (n=559) | 3.4% (n=559) | 0.9% (n=559) | 0.0% (n=559) | 34.9% (n=1601) |
| 2400+ | unknown | 14 | 0.0% (n=14) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 0.9% (n=1601) |

## Drill pool by cut

What the drill can draw from at each candidate cut (D-13), so the cut can be chosen before it ships. Scores use the drill lambda (1.0) and the model in this checkout. The report prints the pool at every cut and recommends none.

### Own pool per user

**Estimate** (D-23): usable blunder windows per non-guest user, as p25 / median, from exact per-user counts times per-bucket rates at the cut (after the 30% cap on pure misses); the Elo bucket columns count only a user's games in that bucket. A user under 50 windows falls back to foreign slots (250 D-15).

| cut | all users | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 152.5 / 562.7 | 8.1 / 79.0 | 4.0 / 44.4 | 6.5 / 54.5 | 8.4 / 130.4 | 16.3 / 165.2 | 3.4 / 29.2 |
| 0.60 | 133.4 / 489.8 | 7.1 / 69.8 | 3.4 / 38.2 | 5.6 / 46.7 | 7.2 / 112.5 | 14.0 / 141.5 | 2.8 / 24.5 |
| 0.70 | 112.9 / 413.9 | 6.0 / 59.2 | 2.9 / 32.0 | 4.7 / 39.3 | 6.0 / 93.0 | 11.5 / 116.2 | 2.2 / 19.0 |
| 0.80 | 89.8 / 331.7 | 4.9 / 48.4 | 2.3 / 25.9 | 3.7 / 31.0 | 4.7 / 72.9 | 8.9 / 90.6 | 1.6 / 14.1 |

### Foreign pool per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13), population estimates: the sample count times 1000 / 25 sample permille.

| level (pinned Elo) | note | qualifying >= 0.50 | qualifying >= 0.60 | qualifying >= 0.70 | qualifying >= 0.80 |
| --- | --- | --- | --- | --- | --- |
| 600 | extreme: below 800 | 136440 | 121200 | 104480 | 87120 |
| 800 |  | 34120 | 30000 | 26160 | 20880 |
| 1000 |  | 152680 | 132320 | 113000 | 91760 |
| 1200 |  | 234000 | 203080 | 172680 | 139200 |
| 1400 |  | 208160 | 179600 | 154320 | 124240 |
| 1600 |  | 232080 | 200760 | 170560 | 137640 |
| 1800 |  | 203000 | 176760 | 148160 | 118120 |
| 2000 |  | 194200 | 169240 | 142560 | 113760 |
| 2200 |  | 109960 | 94720 | 79160 | 63600 |
| 2400 | extreme: 2400 and above | 27440 | 23920 | 19360 | 15160 |
| 2600 | extreme: 2400 and above | 19640 | 16440 | 13080 | 9800 |

## Eval band

Pre-move ES bounds (D-15), at the chosen facepalm threshold. First table: share of qualifying (facepalm) blunders whose pre-move ES is inside the band. Second table: disjoint herring windows per game, averaged uniformly over window lengths 3 to 5, with the band applied to every judged user move.

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 100.0% (n=3536) | 100.0% (n=5015) | 100.0% (n=6822) | 100.0% (n=7068) | 100.0% (n=3565) | 100.0% (n=557) | 100.0% (n=26563) |
| [0.05, 0.95] | 91.7% (n=3536) | 93.0% (n=5015) | 95.0% (n=6822) | 94.6% (n=7068) | 94.9% (n=3565) | 93.2% (n=557) | 94.0% (n=26563) |
| [0.10, 0.90] | 83.3% (n=3536) | 86.5% (n=5015) | 89.3% (n=6822) | 89.3% (n=7068) | 89.3% (n=3565) | 86.7% (n=557) | 87.9% (n=26563) |
| [0.15, 0.85] | 72.9% (n=3536) | 76.6% (n=5015) | 80.1% (n=6822) | 80.6% (n=7068) | 81.2% (n=3565) | 79.2% (n=557) | 78.7% (n=26563) |
| [0.20, 0.80] | 62.3% (n=3536) | 66.6% (n=5015) | 70.3% (n=6822) | 71.4% (n=7068) | 72.6% (n=3565) | 71.1% (n=557) | 69.2% (n=26563) |

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 3.309 (n=2715) | 3.981 (n=4447) | 4.540 (n=6857) | 5.116 (n=8189) | 5.795 (n=3998) | 7.803 (n=939) | 4.797 (n=27145) |
| [0.05, 0.95] | 2.330 (n=2715) | 3.176 (n=4447) | 3.904 (n=6857) | 4.573 (n=8189) | 5.160 (n=3998) | 7.306 (n=939) | 4.132 (n=27145) |
| [0.10, 0.90] | 1.790 (n=2715) | 2.640 (n=4447) | 3.404 (n=6857) | 4.134 (n=8189) | 4.723 (n=3998) | 6.977 (n=939) | 3.656 (n=27145) |
| [0.15, 0.85] | 1.382 (n=2715) | 2.119 (n=4447) | 2.861 (n=6857) | 3.611 (n=8189) | 4.220 (n=3998) | 6.499 (n=939) | 3.144 (n=27145) |
| [0.20, 0.80] | 1.121 (n=2715) | 1.792 (n=4447) | 2.462 (n=6857) | 3.191 (n=8189) | 3.780 (n=3998) | 6.017 (n=939) | 2.755 (n=27145) |

## Window fit

Share of usable blunders (facepalm and pre-move ES in band) whose k-1 preceding user moves are all Good and in band, for window positions 1 to 5 (D-16). The last column weights the positions with the blunder-window position weights below.

| Elo bucket | usable blunders | pos 1 | pos 2 | pos 3 | pos 4 | pos 5 | window-weighted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 2947 | 100.0% (n=2947) | 52.2% (n=2947) | 31.6% (n=2947) | 20.1% (n=2947) | 13.5% (n=2947) | 62.0% (n=2947) |
| 800-1199 | 4339 | 100.0% (n=4339) | 57.4% (n=4339) | 38.0% (n=4339) | 26.0% (n=4339) | 18.6% (n=4339) | 65.5% (n=4339) |
| 1200-1599 | 6095 | 100.0% (n=6095) | 61.5% (n=6095) | 41.9% (n=6095) | 30.2% (n=6095) | 22.4% (n=6095) | 68.0% (n=6095) |
| 1600-1999 | 6309 | 100.0% (n=6309) | 63.4% (n=6309) | 44.9% (n=6309) | 32.6% (n=6309) | 25.4% (n=6309) | 69.5% (n=6309) |
| 2000-2399 | 3184 | 100.0% (n=3184) | 65.1% (n=3184) | 46.0% (n=3184) | 34.4% (n=3184) | 26.9% (n=3184) | 70.4% (n=3184) |
| 2400+ | 483 | 100.0% (n=483) | 67.1% (n=483) | 52.6% (n=483) | 42.4% (n=483) | 35.6% (n=483) | 73.4% (n=483) |
| all | 23357 | 100.0% (n=23357) | 60.7% (n=23357) | 41.5% (n=23357) | 29.6% (n=23357) | 22.2% (n=23357) | 67.6% (n=23357) |

Blunder windows (250 D-12): length uniform over (3, 4, 5), then the position drawn with weight proportional to 0.265 * (1 - 0.265)^(k - 1) within that length, so the length alone never reveals the blunder. The weights below are the marginal over the length. Herrings are not part of this table: a herring is 33.3% of all slots, an independent draw.

| position | P(position | blunder window) |
| --- | --- |
| 1 | 0.3837 |
| 2 | 0.2820 |
| 3 | 0.2073 |
| 4 | 0.0942 |
| 5 | 0.0328 |

## Herring supply

Disjoint windows of L consecutive Good user moves with pre-move ES in [0.10, 0.90], per sampled game. Each maximal run of qualifying moves contributes floor(run / L) windows. Herrings are 33.3% of the slots (250 D-12), so a session of 6 windows needs about 2.0 of them.

| Elo bucket | games | L=3 | L=4 | L=5 | L-uniform mean |
| --- | --- | --- | --- | --- | --- |
| <800 | 2715 | 2.719 | 1.629 | 1.023 | 1.790 |
| 800-1199 | 4447 | 3.862 | 2.445 | 1.613 | 2.640 |
| 1200-1599 | 6857 | 4.890 | 3.146 | 2.178 | 3.404 |
| 1600-1999 | 8189 | 5.859 | 3.853 | 2.691 | 4.134 |
| 2000-2399 | 3998 | 6.617 | 4.413 | 3.138 | 4.723 |
| 2400+ | 939 | 9.532 | 6.559 | 4.840 | 6.977 |
| all | 27145 | 5.212 | 3.397 | 2.358 | 3.656 |

## Supply by origin

### Own supply per user

**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times per-bucket sample rates at the chosen threshold, after the 30% cap on pure misses. Rating groups approximate each game's exact Elo.

- Non-guest users with a fully evaluated game: 601
- Users under 50 usable blunder windows (their own slots turn into foreign ones, 250 D-15): 68 of 601

| per user | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- |
| usable blunder windows | 43.8 | 152.5 | 562.7 | 1110.6 | 2335.3 |
| herring windows | 197.0 | 643.0 | 2815.0 | 7103.7 | 14889.7 |

### Foreign supply per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13: rating only, no widening). Counts are population estimates: the sample count times 1000 / 25 sample permille (non-guest games, so a run capped with `--limit-games` undercounts). A session takes at most one window per game, so the games column is the pool a foreign slot draws from. The rows below 800 and at 2400 and above are the extremes, where the pool is thinnest.

| level (pinned Elo) | mover Elo | qualifying blunders | usable (in band) | games with a qualifying blunder | sample n (qualifying) | note |
| --- | --- | --- | --- | --- | --- | --- |
| 600 | 450 to 750 | 136440 | 113760 | 69040 | 3411 | extreme: below 800 |
| 800 | 650 to 950 | 34120 | 29200 | 17880 | 853 |  |
| 1000 | 850 to 1150 | 152680 | 131840 | 81680 | 3817 |  |
| 1200 | 1050 to 1350 | 234000 | 205280 | 129520 | 5850 |  |
| 1400 | 1250 to 1550 | 208160 | 186280 | 121720 | 5204 |  |
| 1600 | 1450 to 1750 | 232080 | 206280 | 138880 | 5802 |  |
| 1800 | 1650 to 1950 | 203000 | 181880 | 124920 | 5075 |  |
| 2000 | 1850 to 2150 | 194200 | 174000 | 115040 | 4855 |  |
| 2200 | 2050 to 2350 | 109960 | 98080 | 64760 | 2749 |  |
| 2400 | 2250 to 2550 | 27440 | 24200 | 16640 | 686 | extreme: 2400 and above |
| 2600 | 2450 to 2750 | 19640 | 17280 | 13160 | 491 | extreme: 2400 and above |

## Provenance

Engine full evals against lichess `%eval` games (provenance = whether the game carries lichess evals). Rates, fit and supply are recomputed inside each provenance.

| provenance | games | blunders | usable blunders | window-weighted fit | herring windows per game | users | blunder windows p10 / p50 / p90 | users under 50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| engine | 24397 | 53386 | 21200 | 67.7% (n=21200) | 3.625 | 601 | 27.6 / 460.2 / 2152.9 | 88 of 601 |
| lichess | 2748 | 6096 | 2157 | 66.5% (n=2157) | 3.928 | 312 | 7.0 / 77.2 / 433.0 | 128 of 312 |

## Arrow oddness

Maia's probability of the move actually played, at the user's pinned Elo on the exact pre-move board (D-17). Good moves are a seeded sample of judged Good user moves (1500 per bucket requested, seed 248261108, 0 not scorable) with pre-move ES inside [0.10, 0.90]. Blunders are the usable ones at the chosen facepalm threshold and band, with their stored played-move probability.

AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows wins without reading the position.

| Elo bucket | n Good | n blunder | Good prob q1 / median / q3 | blunder prob q1 / median / q3 | AUC |
| --- | --- | --- | --- | --- | --- |
| <800 | 986 | 2947 | 0.139 / 0.304 / 0.535 | 0.020 / 0.056 / 0.135 | 0.835 |
| 800-1199 | 1102 | 4339 | 0.168 / 0.367 / 0.639 | 0.014 / 0.048 / 0.143 | 0.851 |
| 1200-1599 | 1206 | 6095 | 0.190 / 0.423 / 0.684 | 0.012 / 0.045 / 0.133 | 0.874 |
| 1600-1999 | 1267 | 6309 | 0.197 / 0.436 / 0.733 | 0.009 / 0.036 / 0.113 | 0.890 |
| 2000-2399 | 1274 | 3184 | 0.216 / 0.453 / 0.760 | 0.005 / 0.025 / 0.088 | 0.903 |
| 2400+ | 1367 | 483 | 0.217 / 0.475 / 0.787 | 0.007 / 0.032 / 0.107 | 0.894 |
| all | 7202 | 23357 | 0.185 / 0.414 / 0.701 | 0.011 / 0.041 / 0.124 | 0.876 |

### Drill against the unselected baseline

The target is not AUC 0.5: blunders looking somewhat odd is a real signal the drill should train. The target is a drill AUC close to the unselected one, i.e. selection does not widen the real-game gap. Unselected = every scored Good move against every rated user-side blunder (no band, no facepalm threshold); band only = both sides inside the eval band; drill = the table above. A clearly positive drill - unselected means flagging odd-looking arrows pays more in the drill than in games.

| Elo bucket | n Good (unselected) | n blunder (unselected) | AUC unselected | AUC band only | AUC drill | drill - unselected |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 1500 | 7257 | 0.755 | 0.761 | 0.835 | +0.080 |
| 800-1199 | 1500 | 10689 | 0.762 | 0.759 | 0.851 | +0.089 |
| 1200-1599 | 1500 | 15279 | 0.766 | 0.775 | 0.874 | +0.108 |
| 1600-1999 | 1500 | 16742 | 0.780 | 0.781 | 0.890 | +0.110 |
| 2000-2399 | 1500 | 7913 | 0.797 | 0.795 | 0.903 | +0.106 |
| 2400+ | 1500 | 1601 | 0.768 | 0.771 | 0.894 | +0.126 |
| all | 9000 | 59481 | 0.771 | 0.776 | 0.876 | +0.105 |

## Recommended constants

- Facepalm threshold **0.5** (a user blunder qualifies at or above it).
- Eval band **[0.10, 0.90]** on the pre-move ES.

These are a recommendation only: nothing here is wired into app code, and the owner decides the final values. Re-render with another `--facepalm-threshold` from the cache to compare.

Fair-share proxies per threshold (250 D-03: a false alarm is worse than a miss). The report cannot tell a fair position from an unfair one, so it prints what drives fairness among the passers: how rarely the move is played, how few replies the opponent has, and how often the stored line wins material or mates at once. The owner's labels (2026-11-13, decided labels with a stored line, cross-validated) measured fair among passers at >= 0.5: 80%, >= 0.7: 89%, >= 0.8: 92%. Judge precision on the spot-check, not on these columns alone.

| threshold | pass of scored | pass of all | median played prob | median reply spread | median best-reply prob | mate or >= 2 points down | median usable windows per user |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 47.8% (n=55575) | 44.7% (n=59482) | 0.041 | 2.65 | 0.676 | 54.6% (n=26563) | 562.7 |
| 0.60 | 41.6% (n=55575) | 38.9% (n=59482) | 0.035 | 2.53 | 0.703 | 59.8% (n=23120) | 489.8 |
| 0.70 | 35.2% (n=55575) | 32.9% (n=59482) | 0.030 | 2.40 | 0.728 | 66.0% (n=19586) | 413.9 |
| 0.80 | 28.5% (n=55575) | 26.6% (n=59482) | 0.025 | 2.25 | 0.760 | 73.7% (n=15819) | 331.7 |

Window-weighted share of usable blunders (qualifying and in band) that fit a window, at the chosen threshold:

| Elo bucket | window fit (usable blunders) |
| --- | --- |
| <800 | 62.0% (n=2947) |
| 800-1199 | 65.5% (n=4339) |
| 1200-1599 | 68.0% (n=6095) |
| 1600-1999 | 69.5% (n=6309) |
| 2000-2399 | 70.4% (n=3184) |
| 2400+ | 73.4% (n=483) |
| all | 67.6% (n=23357) |

Resulting supply per non-guest user (estimate): median 562.7 usable blunder windows and 2815.0 herring windows; 68 of 601 users are under 50 blunder windows.

Read the spot-check before choosing: `spot-check-2026-11-22.md`.

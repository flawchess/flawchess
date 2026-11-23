# Blunder-check calibration report

## How to read this report

- **Population:** fully evaluated games on chess.com, lichess (pasted and bot games are out). Database: `flawchess`. Run date: 2026-11-23.
- **Sampling:** deterministic, 25 permille (2.5%) of games chosen by md5 residue of the game id; the same sample on every re-run.
- **Expected score (ES):** every ES comes from the flaw classifier's own per-ply pass (`_run_all_moves_pass`), from the mover's point of view. Pre-move ES is the ES before the user's move, `ES_played` the ES after the blunder, `ES_ref` the user's ES before the opponent's previous move (what the user would have had without the gift).
- **Cases (D-13):** *allowed* = the blunder is not a miss (the opponent's previous move was not a mistake or blunder). *Pure miss* = a miss whose `ES_played` is at least `ES_ref` minus the inaccuracy drop: the user only gave back what the opponent gifted. *Mixed* = a miss that lost more than the gift. *Unclassified* = a miss without usable ES.
- **Facepalm score (250 D-01, 254 D-01):** a ranking of how careless a blunder is at the mover's level, fitted on the owner's labels. The report reads the stored FACTS of each blunder (the played move's Maia probability, the stored material loss and missed gain, each the decaying mean over the odd depths of the quiet-point walk, and the opponent's reply probability on a losing row or the best move's probability otherwise) and scores them with the Python twin at the drill lambda (1.0) and the constants and model of this checkout, never the stored score column, so a candidate refit is judged here before it ships. It is not a probability and not a share of peers; a blunder qualifies when its score is at least the chosen threshold. A blunder without a score never qualifies; the Facepalm score section tells why.
- **Window mix (250 D-12):** every slot independently draws a herring (33%), an own blunder (33%) or a foreign blunder (33%); window length is uniform over 3 to 5 user moves for both kinds, a blunder's position follows the per-move hazard 0.265 within that length, 1 lead-in plies. Pure misses are capped at 30% of the blunder supply (report estimate only).
- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only aggregates times per-bucket sample rates, with rating groups approximating each game's exact Elo. It is an estimate, not an exact count.
- **Chosen values:** facepalm threshold = 0.7, eval band [0.10, 0.90]. These are a recommendation only; no constant is wired into app code by this report.
- Guest users' flaws are never Maia-scored, so guest games are excluded from every section except the sample counts.

## Sample

- Games sampled: 27264 (113 guest, excluded below)
- Games skipped for a ply gap: 55
- Unrated games (no rating at game time): 0 (0 user-side blunders not bucketed)
- User-side blunders (rated, non-guest): 59499

| Elo bucket | games (engine) | games (lichess) | blunders (engine) | blunders (lichess) |
| --- | --- | --- | --- | --- |
| <800 | 2647 | 74 | 6977 | 297 |
| 800-1199 | 3863 | 584 | 9201 | 1488 |
| 1200-1599 | 6156 | 701 | 13597 | 1682 |
| 1600-1999 | 7357 | 832 | 15027 | 1716 |
| 2000-2399 | 3588 | 410 | 7261 | 652 |
| 2400+ | 792 | 147 | 1340 | 261 |

## Control

Stored `game_flaws` (ply, severity) pairs against the mistakes and blunders recomputed from the per-ply evals (all sampled games, both colors; D-13).

- Agreement: 197276 of 197384 = 99.9% (n=197384)

## Cases by Elo bucket

| Elo bucket | blunders | allowed | pure_miss | mixed | unclassified | mixed / (pure miss + mixed) |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 7274 | 54.2% (n=7274) | 27.6% (n=7274) | 18.1% (n=7274) | 0.0% (n=7274) | 39.6% (n=3328) |
| 800-1199 | 10689 | 58.9% (n=10689) | 24.3% (n=10689) | 16.7% (n=10689) | 0.0% (n=10689) | 40.8% (n=4392) |
| 1200-1599 | 15279 | 62.5% (n=15279) | 22.6% (n=15279) | 14.9% (n=15279) | 0.0% (n=15279) | 39.7% (n=5734) |
| 1600-1999 | 16743 | 64.2% (n=16743) | 22.3% (n=16743) | 13.6% (n=16743) | 0.0% (n=16743) | 37.9% (n=6000) |
| 2000-2399 | 7913 | 64.8% (n=7913) | 21.6% (n=7913) | 13.6% (n=7913) | 0.0% (n=7913) | 38.6% (n=2786) |
| 2400+ | 1601 | 64.0% (n=1601) | 22.9% (n=1601) | 13.1% (n=1601) | 0.0% (n=1601) | 36.3% (n=576) |
| all | 59499 | 61.7% (n=59499) | 23.3% (n=59499) | 15.0% (n=59499) | 0.0% (n=59499) | 39.2% (n=22816) |

## Facepalm score

User-side blunders of rated, non-guest games and their stored facepalm score (250 D-01): a ranking of how careless the blunder is at the mover's level, not a share of peers. `scored` is the share with a score; the next four columns split the unscored ones by reason (shares of all user blunders): no reply spread yet, no stored engine line, a line shorter than 3 plies without an early mate (or one that cannot be replayed), and a missing played-move probability. The `pass` columns are shares of the scored blunders at or above each threshold; `qualifying of all` is the share of every user blunder that qualifies at the chosen threshold (an unscored blunder never qualifies).

| Elo bucket | user blunders | scored | no spread | no line | line too short | no played prob | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | qualifying of all (>= 0.70) | score q1 / median / q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 7274 | 93.4% (n=7274) | 0.0% (n=7274) | 6.3% (n=7274) | 0.3% (n=7274) | 0.0% (n=7274) | 49.3% (n=6797) | 42.8% (n=6797) | 36.7% (n=6797) | 30.5% (n=6797) | 34.3% (n=7274) | 0.153 / 0.488 / 0.864 |
| 800-1199 | 10689 | 93.6% (n=10689) | 0.0% (n=10689) | 6.2% (n=10689) | 0.2% (n=10689) | 0.0% (n=10689) | 46.6% (n=10000) | 39.9% (n=10000) | 33.3% (n=10000) | 26.8% (n=10000) | 31.1% (n=10689) | 0.142 / 0.451 / 0.828 |
| 1200-1599 | 15279 | 93.8% (n=15279) | 0.0% (n=15279) | 5.9% (n=15279) | 0.3% (n=15279) | 0.0% (n=15279) | 43.9% (n=14335) | 37.5% (n=14335) | 31.3% (n=14335) | 25.0% (n=14335) | 29.4% (n=15279) | 0.133 / 0.413 / 0.800 |
| 1600-1999 | 16743 | 92.3% (n=16743) | 0.0% (n=16743) | 7.4% (n=16743) | 0.3% (n=16743) | 0.0% (n=16743) | 41.8% (n=15456) | 35.7% (n=15456) | 29.6% (n=15456) | 23.3% (n=15456) | 27.3% (n=16743) | 0.126 / 0.388 / 0.774 |
| 2000-2399 | 7913 | 93.7% (n=7913) | 0.0% (n=7913) | 6.1% (n=7913) | 0.2% (n=7913) | 0.0% (n=7913) | 44.6% (n=7415) | 37.3% (n=7415) | 30.9% (n=7415) | 24.3% (n=7415) | 29.0% (n=7913) | 0.148 / 0.422 / 0.790 |
| 2400+ | 1601 | 99.1% (n=1601) | 0.1% (n=1601) | 0.7% (n=1601) | 0.1% (n=1601) | 0.0% (n=1601) | 31.9% (n=1587) | 25.2% (n=1587) | 20.0% (n=1587) | 14.6% (n=1587) | 19.8% (n=1601) | 0.094 / 0.283 / 0.604 |
| all | 59499 | 93.4% (n=59499) | 0.0% (n=59499) | 6.3% (n=59499) | 0.3% (n=59499) | 0.0% (n=59499) | 44.2% (n=55590) | 37.7% (n=55590) | 31.5% (n=55590) | 25.1% (n=55590) | 29.4% (n=59499) | 0.135 / 0.416 / 0.802 |

## Pass shares by material type

User-side blunders of rated, non-guest games by what they do to the material balance (D-13), read from the stored decaying-mean inputs (259 D-03): *loses* = the played line loses material or mates, *misses* = the best line gains material (at least 1) or mates, *loses and misses* = both, *neither*, and *unknown* = no loss input is stored. Scores use the drill lambda (1.0) and the model in this checkout, computed from the stored facts. `scored` is the share of the type with a score; each `pass` column is the share of those scored blunders at or above the cut; the last column is the type's share of all user blunders in the row group.

| material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- |
| loses | 26488 | 100.0% (n=26488) | 59.8% (n=26488) | 51.8% (n=26488) | 44.1% (n=26488) | 35.6% (n=26488) | 44.5% (n=59499) |
| misses | 8637 | 100.0% (n=8637) | 35.5% (n=8636) | 27.1% (n=8636) | 18.8% (n=8636) | 10.7% (n=8636) | 14.5% (n=59499) |
| loses_and_misses | 7031 | 99.9% (n=7031) | 71.4% (n=7027) | 65.7% (n=7027) | 59.0% (n=7027) | 51.3% (n=7027) | 11.8% (n=59499) |
| neither | 13534 | 99.3% (n=13534) | 5.0% (n=13439) | 2.0% (n=13439) | 0.5% (n=13439) | 0.0% (n=13439) | 22.7% (n=59499) |
| unknown | 3809 | 0.0% (n=3809) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.4% (n=59499) |

### By Elo bucket

| Elo bucket | material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | loses | 3134 | 100.0% (n=3134) | 64.5% (n=3134) | 56.1% (n=3134) | 48.9% (n=3134) | 41.4% (n=3134) | 43.1% (n=7274) |
| <800 | misses | 1251 | 100.0% (n=1251) | 32.3% (n=1251) | 23.6% (n=1251) | 15.6% (n=1251) | 8.3% (n=1251) | 17.2% (n=7274) |
| <800 | loses_and_misses | 1243 | 100.0% (n=1243) | 73.4% (n=1243) | 68.7% (n=1243) | 61.7% (n=1243) | 54.2% (n=1243) | 17.1% (n=7274) |
| <800 | neither | 1181 | 99.0% (n=1181) | 1.1% (n=1169) | 0.4% (n=1169) | 0.0% (n=1169) | 0.0% (n=1169) | 16.2% (n=7274) |
| <800 | unknown | 465 | 0.0% (n=465) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.4% (n=7274) |
| 800-1199 | loses | 4858 | 100.0% (n=4858) | 61.4% (n=4858) | 53.4% (n=4858) | 45.6% (n=4858) | 37.1% (n=4858) | 45.4% (n=10689) |
| 800-1199 | misses | 1634 | 100.0% (n=1634) | 36.0% (n=1634) | 27.1% (n=1634) | 17.9% (n=1634) | 9.9% (n=1634) | 15.3% (n=10689) |
| 800-1199 | loses_and_misses | 1387 | 99.9% (n=1387) | 72.8% (n=1386) | 66.8% (n=1386) | 58.8% (n=1386) | 51.9% (n=1386) | 13.0% (n=10689) |
| 800-1199 | neither | 2140 | 99.2% (n=2140) | 3.7% (n=2122) | 1.4% (n=2122) | 0.2% (n=2122) | 0.0% (n=2122) | 20.0% (n=10689) |
| 800-1199 | unknown | 670 | 0.0% (n=670) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.3% (n=10689) |
| 1200-1599 | loses | 6975 | 100.0% (n=6975) | 60.0% (n=6975) | 52.3% (n=6975) | 44.4% (n=6975) | 35.5% (n=6975) | 45.7% (n=15279) |
| 1200-1599 | misses | 2179 | 100.0% (n=2179) | 33.5% (n=2179) | 24.8% (n=2179) | 17.2% (n=2179) | 9.7% (n=2179) | 14.3% (n=15279) |
| 1200-1599 | loses_and_misses | 1735 | 99.9% (n=1735) | 70.8% (n=1733) | 65.0% (n=1733) | 58.2% (n=1733) | 51.6% (n=1733) | 11.4% (n=15279) |
| 1200-1599 | neither | 3478 | 99.1% (n=3478) | 4.4% (n=3448) | 1.6% (n=3448) | 0.2% (n=3448) | 0.0% (n=3448) | 22.8% (n=15279) |
| 1200-1599 | unknown | 912 | 0.0% (n=912) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.0% (n=15279) |
| 1600-1999 | loses | 7387 | 100.0% (n=7387) | 57.5% (n=7387) | 49.9% (n=7387) | 42.2% (n=7387) | 34.3% (n=7387) | 44.1% (n=16743) |
| 1600-1999 | misses | 2274 | 100.0% (n=2274) | 35.6% (n=2273) | 28.9% (n=2273) | 20.2% (n=2273) | 11.4% (n=2273) | 13.6% (n=16743) |
| 1600-1999 | loses_and_misses | 1697 | 99.9% (n=1697) | 69.3% (n=1696) | 63.3% (n=1696) | 57.4% (n=1696) | 47.2% (n=1696) | 10.1% (n=16743) |
| 1600-1999 | neither | 4122 | 99.5% (n=4122) | 5.4% (n=4100) | 2.3% (n=4100) | 0.6% (n=4100) | 0.0% (n=4100) | 24.6% (n=16743) |
| 1600-1999 | unknown | 1263 | 0.0% (n=1263) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 7.5% (n=16743) |
| 2000-2399 | loses | 3471 | 100.0% (n=3471) | 59.8% (n=3471) | 51.6% (n=3471) | 43.2% (n=3471) | 34.0% (n=3471) | 43.9% (n=7913) |
| 2000-2399 | misses | 1088 | 100.0% (n=1088) | 43.3% (n=1088) | 32.7% (n=1088) | 24.4% (n=1088) | 15.8% (n=1088) | 13.7% (n=7913) |
| 2000-2399 | loses_and_misses | 815 | 100.0% (n=815) | 72.8% (n=815) | 67.1% (n=815) | 62.0% (n=815) | 55.3% (n=815) | 10.3% (n=7913) |
| 2000-2399 | neither | 2054 | 99.4% (n=2054) | 8.2% (n=2041) | 3.7% (n=2041) | 1.0% (n=2041) | 0.0% (n=2041) | 26.0% (n=7913) |
| 2000-2399 | unknown | 485 | 0.0% (n=485) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 6.1% (n=7913) |
| 2400+ | loses | 663 | 100.0% (n=663) | 47.4% (n=663) | 38.3% (n=663) | 30.8% (n=663) | 22.5% (n=663) | 41.4% (n=1601) |
| 2400+ | misses | 211 | 100.0% (n=211) | 28.9% (n=211) | 22.3% (n=211) | 16.6% (n=211) | 7.6% (n=211) | 13.2% (n=1601) |
| 2400+ | loses_and_misses | 154 | 100.0% (n=154) | 63.6% (n=154) | 57.8% (n=154) | 50.0% (n=154) | 43.5% (n=154) | 9.6% (n=1601) |
| 2400+ | neither | 559 | 100.0% (n=559) | 5.9% (n=559) | 1.8% (n=559) | 0.2% (n=559) | 0.0% (n=559) | 34.9% (n=1601) |
| 2400+ | unknown | 14 | 0.0% (n=14) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 0.9% (n=1601) |

## Drill pool by cut

What the drill can draw from at each candidate cut (D-13), so the cut can be chosen before it ships. Scores use the drill lambda (1.0) and the model in this checkout. The report prints the pool at every cut and recommends none.

### Own pool per user

**Estimate** (D-23): usable blunder windows per non-guest user, as p25 / median, from exact per-user counts times per-bucket rates at the cut (after the 30% cap on pure misses); the Elo bucket columns count only a user's games in that bucket. A user under 50 windows falls back to foreign slots (250 D-15).

| cut | all users | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 142.8 / 524.0 | 7.6 / 74.5 | 3.7 / 40.8 | 6.0 / 50.1 | 7.6 / 118.6 | 15.1 / 153.0 | 3.1 / 26.6 |
| 0.60 | 122.4 / 446.4 | 6.5 / 64.0 | 3.1 / 34.6 | 5.0 / 42.3 | 6.4 / 100.0 | 12.5 / 126.6 | 2.4 / 20.9 |
| 0.70 | 101.1 / 370.1 | 5.5 / 54.1 | 2.6 / 28.7 | 4.2 / 34.8 | 5.2 / 81.5 | 10.1 / 102.7 | 1.9 / 16.4 |
| 0.80 | 80.1 / 292.9 | 4.6 / 44.8 | 2.1 / 22.8 | 3.3 / 27.3 | 4.1 / 63.3 | 7.8 / 78.6 | 1.4 / 11.7 |

### Foreign pool per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13), population estimates: the sample count times 1000 / 25 sample permille.

| level (pinned Elo) | note | qualifying >= 0.50 | qualifying >= 0.60 | qualifying >= 0.70 | qualifying >= 0.80 |
| --- | --- | --- | --- | --- | --- |
| 600 | extreme: below 800 | 129320 | 112240 | 96280 | 80160 |
| 800 |  | 31120 | 27400 | 23040 | 18760 |
| 1000 |  | 142120 | 121800 | 101680 | 81600 |
| 1200 |  | 216000 | 185280 | 153920 | 123640 |
| 1400 |  | 191960 | 163800 | 137840 | 109800 |
| 1600 |  | 213760 | 181040 | 151400 | 119520 |
| 1800 |  | 184640 | 157280 | 130320 | 101760 |
| 2000 |  | 179200 | 152680 | 126640 | 99080 |
| 2200 |  | 102000 | 85280 | 70360 | 56320 |
| 2400 | extreme: 2400 and above | 25240 | 20960 | 17200 | 13720 |
| 2600 | extreme: 2400 and above | 17880 | 14200 | 11200 | 8200 |

## Eval band

Pre-move ES bounds (D-15), at the chosen facepalm threshold. First table: share of qualifying (facepalm) blunders whose pre-move ES is inside the band. Second table: disjoint herring windows per game, averaged uniformly over window lengths 3 to 5, with the band applied to every judged user move.

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 100.0% (n=2494) | 100.0% (n=3328) | 100.0% (n=4488) | 100.0% (n=4579) | 100.0% (n=2292) | 100.0% (n=317) | 100.0% (n=17498) |
| [0.05, 0.95] | 90.9% (n=2494) | 92.6% (n=3328) | 94.4% (n=4488) | 94.0% (n=4579) | 93.9% (n=2292) | 91.5% (n=317) | 93.3% (n=17498) |
| [0.10, 0.90] | 81.8% (n=2494) | 85.0% (n=3328) | 87.7% (n=4488) | 87.5% (n=4579) | 87.0% (n=2292) | 85.8% (n=317) | 86.2% (n=17498) |
| [0.15, 0.85] | 70.0% (n=2494) | 74.1% (n=3328) | 77.5% (n=4488) | 77.5% (n=4579) | 77.4% (n=2292) | 74.4% (n=317) | 75.7% (n=17498) |
| [0.20, 0.80] | 59.3% (n=2494) | 64.2% (n=3328) | 67.3% (n=4488) | 68.0% (n=4579) | 68.8% (n=2292) | 65.3% (n=317) | 65.9% (n=17498) |

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 3.305 (n=2721) | 3.981 (n=4447) | 4.540 (n=6857) | 5.116 (n=8189) | 5.795 (n=3998) | 7.803 (n=939) | 4.796 (n=27151) |
| [0.05, 0.95] | 2.327 (n=2721) | 3.176 (n=4447) | 3.904 (n=6857) | 4.573 (n=8189) | 5.160 (n=3998) | 7.306 (n=939) | 4.131 (n=27151) |
| [0.10, 0.90] | 1.788 (n=2721) | 2.640 (n=4447) | 3.404 (n=6857) | 4.134 (n=8189) | 4.723 (n=3998) | 6.977 (n=939) | 3.655 (n=27151) |
| [0.15, 0.85] | 1.380 (n=2721) | 2.119 (n=4447) | 2.861 (n=6857) | 3.611 (n=8189) | 4.220 (n=3998) | 6.499 (n=939) | 3.143 (n=27151) |
| [0.20, 0.80] | 1.119 (n=2721) | 1.792 (n=4447) | 2.462 (n=6857) | 3.191 (n=8189) | 3.780 (n=3998) | 6.017 (n=939) | 2.755 (n=27151) |

## Window fit

Share of usable blunders (facepalm and pre-move ES in band) whose k-1 preceding user moves are all Good and in band, for window positions 1 to 5 (D-16). The last column weights the positions with the blunder-window position weights below.

| Elo bucket | usable blunders | pos 1 | pos 2 | pos 3 | pos 4 | pos 5 | window-weighted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 2040 | 100.0% (n=2040) | 50.6% (n=2040) | 31.2% (n=2040) | 19.6% (n=2040) | 13.1% (n=2040) | 61.4% (n=2040) |
| 800-1199 | 2830 | 100.0% (n=2830) | 56.4% (n=2830) | 37.5% (n=2830) | 25.6% (n=2830) | 18.2% (n=2830) | 65.0% (n=2830) |
| 1200-1599 | 3936 | 100.0% (n=3936) | 60.1% (n=3936) | 40.9% (n=3936) | 29.4% (n=3936) | 22.0% (n=3936) | 67.3% (n=3936) |
| 1600-1999 | 4006 | 100.0% (n=4006) | 61.4% (n=4006) | 43.4% (n=4006) | 31.4% (n=4006) | 24.0% (n=4006) | 68.4% (n=4006) |
| 2000-2399 | 1995 | 100.0% (n=1995) | 63.8% (n=1995) | 45.6% (n=1995) | 34.0% (n=1995) | 26.0% (n=1995) | 69.9% (n=1995) |
| 2400+ | 272 | 100.0% (n=272) | 67.3% (n=272) | 51.8% (n=272) | 41.5% (n=272) | 33.8% (n=272) | 73.1% (n=272) |
| all | 15079 | 100.0% (n=15079) | 59.1% (n=15079) | 40.5% (n=15079) | 28.7% (n=15079) | 21.4% (n=15079) | 66.8% (n=15079) |

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
| <800 | 2721 | 2.716 | 1.626 | 1.021 | 1.788 |
| 800-1199 | 4447 | 3.862 | 2.445 | 1.613 | 2.640 |
| 1200-1599 | 6857 | 4.890 | 3.146 | 2.178 | 3.404 |
| 1600-1999 | 8189 | 5.859 | 3.853 | 2.691 | 4.134 |
| 2000-2399 | 3998 | 6.617 | 4.413 | 3.138 | 4.723 |
| 2400+ | 939 | 9.532 | 6.559 | 4.840 | 6.977 |
| all | 27151 | 5.211 | 3.397 | 2.358 | 3.655 |

## Supply by origin

### Own supply per user

**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times per-bucket sample rates at the chosen threshold, after the 30% cap on pure misses. Rating groups approximate each game's exact Elo.

- Non-guest users with a fully evaluated game: 602
- Users under 50 usable blunder windows (their own slots turn into foreign ones, 250 D-15): 92 of 602

| per user | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- |
| usable blunder windows | 29.0 | 101.1 | 370.1 | 709.6 | 1494.6 |
| herring windows | 200.1 | 643.0 | 2814.4 | 7084.1 | 14858.9 |

### Foreign supply per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13: rating only, no widening). Counts are population estimates: the sample count times 1000 / 25 sample permille (non-guest games, so a run capped with `--limit-games` undercounts). A session takes at most one window per game, so the games column is the pool a foreign slot draws from. The rows below 800 and at 2400 and above are the extremes, where the pool is thinnest.

| level (pinned Elo) | mover Elo | qualifying blunders | usable (in band) | games with a qualifying blunder | sample n (qualifying) | note |
| --- | --- | --- | --- | --- | --- | --- |
| 600 | 450 to 750 | 96280 | 78720 | 57880 | 2407 | extreme: below 800 |
| 800 | 650 to 950 | 23040 | 19480 | 14360 | 576 |  |
| 1000 | 850 to 1150 | 101680 | 86080 | 65000 | 2542 |  |
| 1200 | 1050 to 1350 | 153920 | 132920 | 100760 | 3848 |  |
| 1400 | 1250 to 1550 | 137840 | 120880 | 94320 | 3446 |  |
| 1600 | 1450 to 1750 | 151400 | 132200 | 104280 | 3785 |  |
| 1800 | 1650 to 1950 | 130320 | 114320 | 92400 | 3258 |  |
| 2000 | 1850 to 2150 | 126640 | 110720 | 85280 | 3166 |  |
| 2200 | 2050 to 2350 | 70360 | 61280 | 47800 | 1759 |  |
| 2400 | 2250 to 2550 | 17200 | 14600 | 11680 | 430 | extreme: 2400 and above |
| 2600 | 2450 to 2750 | 11200 | 9880 | 8320 | 280 | extreme: 2400 and above |

## Provenance

Engine full evals against lichess `%eval` games (provenance = whether the game carries lichess evals). Rates, fit and supply are recomputed inside each provenance.

| provenance | games | blunders | usable blunders | window-weighted fit | herring windows per game | users | blunder windows p10 / p50 / p90 | users under 50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| engine | 24403 | 53403 | 13778 | 66.9% (n=13778) | 3.624 | 602 | 17.9 / 295.1 / 1388.0 | 119 of 602 |
| lichess | 2748 | 6096 | 1301 | 65.6% (n=1301) | 3.928 | 312 | 3.9 / 46.1 / 260.3 | 163 of 312 |

## Arrow oddness

Maia's probability of the move actually played, at the user's pinned Elo on the exact pre-move board (D-17). Good moves are a seeded sample of judged Good user moves (1500 per bucket requested, seed 248261108, 0 not scorable) with pre-move ES inside [0.10, 0.90]. Blunders are the usable ones at the chosen facepalm threshold and band, with their stored played-move probability.

AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows wins without reading the position.

| Elo bucket | n Good | n blunder | Good prob q1 / median / q3 | blunder prob q1 / median / q3 | AUC |
| --- | --- | --- | --- | --- | --- |
| <800 | 985 | 2040 | 0.139 / 0.302 / 0.535 | 0.017 / 0.045 / 0.120 | 0.850 |
| 800-1199 | 1102 | 2830 | 0.168 / 0.367 / 0.639 | 0.009 / 0.036 / 0.111 | 0.870 |
| 1200-1599 | 1205 | 3936 | 0.190 / 0.423 / 0.685 | 0.007 / 0.027 / 0.092 | 0.900 |
| 1600-1999 | 1268 | 4006 | 0.197 / 0.436 / 0.733 | 0.005 / 0.020 / 0.076 | 0.915 |
| 2000-2399 | 1274 | 1995 | 0.216 / 0.453 / 0.760 | 0.002 / 0.012 / 0.048 | 0.930 |
| 2400+ | 1366 | 272 | 0.217 / 0.473 / 0.787 | 0.003 / 0.019 / 0.078 | 0.913 |
| all | 7200 | 15079 | 0.185 / 0.414 / 0.701 | 0.006 / 0.026 / 0.090 | 0.899 |

### Drill against the unselected baseline

The target is not AUC 0.5: blunders looking somewhat odd is a real signal the drill should train. The target is a drill AUC close to the unselected one, i.e. selection does not widen the real-game gap. Unselected = every scored Good move against every rated user-side blunder (no band, no facepalm threshold); band only = both sides inside the eval band; drill = the table above. A clearly positive drill - unselected means flagging odd-looking arrows pays more in the drill than in games.

| Elo bucket | n Good (unselected) | n blunder (unselected) | AUC unselected | AUC band only | AUC drill | drill - unselected |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 1500 | 7274 | 0.755 | 0.761 | 0.850 | +0.095 |
| 800-1199 | 1500 | 10689 | 0.762 | 0.759 | 0.870 | +0.108 |
| 1200-1599 | 1500 | 15279 | 0.767 | 0.775 | 0.900 | +0.134 |
| 1600-1999 | 1500 | 16742 | 0.780 | 0.781 | 0.915 | +0.135 |
| 2000-2399 | 1500 | 7913 | 0.797 | 0.795 | 0.930 | +0.133 |
| 2400+ | 1500 | 1601 | 0.768 | 0.771 | 0.913 | +0.146 |
| all | 9000 | 59498 | 0.771 | 0.776 | 0.899 | +0.127 |

## Recommended constants

- Facepalm threshold **0.7** (a user blunder qualifies at or above it).
- Eval band **[0.10, 0.90]** on the pre-move ES.

These are a recommendation only: nothing here is wired into app code, and the owner decides the final values. Re-render with another `--facepalm-threshold` from the cache to compare.

Fair-share proxies per threshold (250 D-03: a false alarm is worse than a miss). The report cannot tell a fair position from an unfair one, so it prints what drives fairness among the passers: how rarely the move is played, how few replies the opponent has, and how often the stored line wins material or mates at once. The owner's labels (2026-11-13, decided labels with a stored line, cross-validated) measured fair among passers at >= 0.5: 80%, >= 0.7: 89%, >= 0.8: 92%. Judge precision on the spot-check, not on these columns alone.

| threshold | pass of scored | pass of all | median played prob | median reply spread | median best-reply prob | mate or >= 2 points down | median usable windows per user |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 44.2% (n=55590) | 41.3% (n=59499) | 0.035 | 2.64 | 0.676 | 54.1% (n=24571) | 524.0 |
| 0.60 | 37.7% (n=55590) | 35.2% (n=59499) | 0.030 | 2.50 | 0.705 | 61.6% (n=20953) | 446.4 |
| 0.70 | 31.5% (n=55590) | 29.4% (n=59499) | 0.026 | 2.37 | 0.735 | 70.0% (n=17498) | 370.1 |
| 0.80 | 25.1% (n=55590) | 23.5% (n=59499) | 0.023 | 2.22 | 0.767 | 79.7% (n=13971) | 292.9 |

Window-weighted share of usable blunders (qualifying and in band) that fit a window, at the chosen threshold:

| Elo bucket | window fit (usable blunders) |
| --- | --- |
| <800 | 61.4% (n=2040) |
| 800-1199 | 65.0% (n=2830) |
| 1200-1599 | 67.3% (n=3936) |
| 1600-1999 | 68.4% (n=4006) |
| 2000-2399 | 69.9% (n=1995) |
| 2400+ | 73.1% (n=272) |
| all | 66.8% (n=15079) |

Resulting supply per non-guest user (estimate): median 370.1 usable blunder windows and 2814.4 herring windows; 92 of 602 users are under 50 blunder windows.

Read the spot-check before choosing: `spot-check-2026-11-23.md`.

# Blunder-check calibration report

## How to read this report

- **Population:** fully evaluated games on chess.com, lichess (pasted and bot games are out). Database: `flawchess`. Run date: 2026-11-16.
- **Sampling:** deterministic, 25 permille (2.5%) of games chosen by md5 residue of the game id; the same sample on every re-run.
- **Expected score (ES):** every ES comes from the flaw classifier's own per-ply pass (`_run_all_moves_pass`), from the mover's point of view. Pre-move ES is the ES before the user's move, `ES_played` the ES after the blunder, `ES_ref` the user's ES before the opponent's previous move (what the user would have had without the gift).
- **Cases (D-13):** *allowed* = the blunder is not a miss (the opponent's previous move was not a mistake or blunder). *Pure miss* = a miss whose `ES_played` is at least `ES_ref` minus the inaccuracy drop: the user only gave back what the opponent gifted. *Mixed* = a miss that lost more than the gift. *Unclassified* = a miss without usable ES.
- **Facepalm score (250 D-01, 254 D-01):** a ranking of how careless a blunder is at the mover's level, fitted on the owner's labels. The report reads the stored FACTS of each blunder (the played move's Maia probability, the opponent's reply spread, the depth-3 material of the played and best lines, both mate plies, the best move's probability and the pre-blunder spread) and scores them with the Python twin at the drill lambda (1.0) and the constants and model of this checkout, never the stored score column, so a candidate refit is judged here before it ships. It is not a probability and not a share of peers; a blunder qualifies when its score is at least the chosen threshold. A blunder without a score never qualifies; the Facepalm score section tells why.
- **Window mix (250 D-12):** every slot independently draws a herring (33%), an own blunder (33%) or a foreign blunder (33%); window length is uniform over 3 to 5 user moves for both kinds, a blunder's position follows the per-move hazard 0.265 within that length, 1 lead-in plies. Pure misses are capped at 30% of the blunder supply (report estimate only).
- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only aggregates times per-bucket sample rates, with rating groups approximating each game's exact Elo. It is an estimate, not an exact count.
- **Chosen values:** facepalm threshold = 0.5, eval band [0.10, 0.90]. These are a recommendation only; no constant is wired into app code by this report.
- Guest users' flaws are never Maia-scored, so guest games are excluded from every section except the sample counts.

## Sample

- Games sampled: 26865 (101 guest, excluded below)
- Games skipped for a ply gap: 55
- Unrated games (no rating at game time): 0 (0 user-side blunders not bucketed)
- User-side blunders (rated, non-guest): 58780

| Elo bucket | games (engine) | games (lichess) | blunders (engine) | blunders (lichess) |
| --- | --- | --- | --- | --- |
| <800 | 2600 | 74 | 6871 | 297 |
| 800-1199 | 3739 | 582 | 8962 | 1483 |
| 1200-1599 | 6012 | 701 | 13342 | 1682 |
| 1600-1999 | 7317 | 832 | 14952 | 1716 |
| 2000-2399 | 3560 | 408 | 7225 | 649 |
| 2400+ | 792 | 147 | 1340 | 261 |

## Control

Stored `game_flaws` (ply, severity) pairs against the mistakes and blunders recomputed from the per-ply evals (all sampled games, both colors; D-13).

- Agreement: 194612 of 194720 = 99.9% (n=194720)

## Cases by Elo bucket

| Elo bucket | blunders | allowed | pure_miss | mixed | unclassified | mixed / (pure miss + mixed) |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 7168 | 54.1% (n=7168) | 27.7% (n=7168) | 18.2% (n=7168) | 0.0% (n=7168) | 39.7% (n=3289) |
| 800-1199 | 10445 | 58.8% (n=10445) | 24.4% (n=10445) | 16.8% (n=10445) | 0.0% (n=10445) | 40.8% (n=4306) |
| 1200-1599 | 15024 | 62.4% (n=15024) | 22.7% (n=15024) | 14.9% (n=15024) | 0.0% (n=15024) | 39.6% (n=5650) |
| 1600-1999 | 16668 | 64.2% (n=16668) | 22.3% (n=16668) | 13.5% (n=16668) | 0.0% (n=16668) | 37.8% (n=5969) |
| 2000-2399 | 7874 | 64.8% (n=7874) | 21.6% (n=7874) | 13.6% (n=7874) | 0.0% (n=7874) | 38.6% (n=2770) |
| 2400+ | 1601 | 64.0% (n=1601) | 22.9% (n=1601) | 13.1% (n=1601) | 0.0% (n=1601) | 36.3% (n=576) |
| all | 58780 | 61.6% (n=58780) | 23.3% (n=58780) | 15.0% (n=58780) | 0.0% (n=58780) | 39.2% (n=22560) |

## Facepalm score

User-side blunders of rated, non-guest games and their stored facepalm score (250 D-01): a ranking of how careless the blunder is at the mover's level, not a share of peers. `scored` is the share with a score; the next four columns split the unscored ones by reason (shares of all user blunders): no reply spread yet, no stored engine line, a line shorter than 3 plies without an early mate (or one that cannot be replayed), and a missing played-move probability. The `pass` columns are shares of the scored blunders at or above each threshold; `qualifying of all` is the share of every user blunder that qualifies at the chosen threshold (an unscored blunder never qualifies).

| Elo bucket | user blunders | scored | no spread | no line | line too short | no played prob | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | qualifying of all (>= 0.50) | score q1 / median / q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 7168 | 88.2% (n=7168) | 0.0% (n=7168) | 6.5% (n=7168) | 5.3% (n=7168) | 0.0% (n=7168) | 42.7% (n=6322) | 38.1% (n=6322) | 33.0% (n=6322) | 28.2% (n=6322) | 37.7% (n=7168) | 0.067 / 0.360 / 0.851 |
| 800-1199 | 10445 | 84.8% (n=10445) | 0.0% (n=10445) | 6.1% (n=10445) | 9.0% (n=10445) | 0.0% (n=10445) | 47.2% (n=8861) | 41.3% (n=8861) | 35.4% (n=8861) | 29.5% (n=8861) | 40.0% (n=10445) | 0.131 / 0.455 / 0.869 |
| 1200-1599 | 15024 | 83.4% (n=15024) | 0.0% (n=15024) | 5.9% (n=15024) | 10.7% (n=15024) | 0.0% (n=15024) | 46.5% (n=12524) | 40.6% (n=12524) | 34.6% (n=12524) | 28.2% (n=12524) | 38.8% (n=15024) | 0.123 / 0.442 / 0.846 |
| 1600-1999 | 16668 | 82.2% (n=16668) | 0.0% (n=16668) | 7.5% (n=16668) | 10.2% (n=16668) | 0.0% (n=16668) | 45.4% (n=13704) | 39.2% (n=13704) | 33.0% (n=13704) | 26.7% (n=13704) | 37.4% (n=16668) | 0.125 / 0.437 / 0.826 |
| 2000-2399 | 7874 | 83.6% (n=7874) | 0.0% (n=7874) | 6.1% (n=7874) | 10.3% (n=7874) | 0.0% (n=7874) | 49.2% (n=6580) | 42.2% (n=6580) | 35.2% (n=6580) | 28.1% (n=6580) | 41.1% (n=7874) | 0.158 / 0.488 / 0.839 |
| 2400+ | 1601 | 78.5% (n=1601) | 0.1% (n=1601) | 0.7% (n=1601) | 20.8% (n=1601) | 0.0% (n=1601) | 36.5% (n=1256) | 30.4% (n=1256) | 23.6% (n=1256) | 17.6% (n=1256) | 28.6% (n=1601) | 0.087 / 0.329 / 0.675 |
| all | 58780 | 83.8% (n=58780) | 0.0% (n=58780) | 6.4% (n=58780) | 9.8% (n=58780) | 0.0% (n=58780) | 46.0% (n=49247) | 39.9% (n=49247) | 33.9% (n=49247) | 27.7% (n=49247) | 38.5% (n=58780) | 0.119 / 0.436 / 0.840 |

## Pass shares by material type

User-side blunders of rated, non-guest games by what they do to the material balance over 3 plies (D-13): *loses* = mated or ending behind on the played line, *misses* = the best line gains material the played line did not keep (or mates), *loses and misses* = both, *neither*, and *unknown* = the played line is too short to tell and holds no mate. Scores use the drill lambda (1.0) and the model in this checkout, computed from the stored facts. `scored` is the share of the type with a score; each `pass` column is the share of those scored blunders at or above the cut; the last column is the type's share of all user blunders in the row group.

| material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- |
| loses | 15770 | 100.0% (n=15770) | 75.4% (n=15770) | 68.5% (n=15770) | 60.8% (n=15770) | 52.1% (n=15770) | 26.8% (n=58780) |
| misses | 9931 | 100.0% (n=9931) | 33.0% (n=9931) | 25.8% (n=9931) | 18.9% (n=9931) | 11.7% (n=9931) | 16.9% (n=58780) |
| loses_and_misses | 5919 | 100.0% (n=5919) | 83.8% (n=5919) | 78.5% (n=5919) | 71.8% (n=5919) | 64.0% (n=5919) | 10.1% (n=58780) |
| neither | 17716 | 99.5% (n=17716) | 14.3% (n=17627) | 9.4% (n=17627) | 5.5% (n=17627) | 2.8% (n=17627) | 30.1% (n=58780) |
| unknown | 9444 | 0.0% (n=9444) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 16.1% (n=58780) |

### By Elo bucket

| Elo bucket | material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | loses | 2046 | 100.0% (n=2046) | 65.5% (n=2046) | 59.9% (n=2046) | 53.6% (n=2046) | 46.8% (n=2046) | 28.5% (n=7168) |
| <800 | misses | 1502 | 100.0% (n=1502) | 24.9% (n=1502) | 19.4% (n=1502) | 13.3% (n=1502) | 8.3% (n=1502) | 21.0% (n=7168) |
| <800 | loses_and_misses | 1132 | 100.0% (n=1132) | 77.3% (n=1132) | 71.6% (n=1132) | 65.5% (n=1132) | 59.4% (n=1132) | 15.8% (n=7168) |
| <800 | neither | 1655 | 99.2% (n=1655) | 6.6% (n=1642) | 4.8% (n=1642) | 2.9% (n=1642) | 1.9% (n=1642) | 23.1% (n=7168) |
| <800 | unknown | 833 | 0.0% (n=833) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 11.6% (n=7168) |
| 800-1199 | loses | 3002 | 100.0% (n=3002) | 75.6% (n=3002) | 68.6% (n=3002) | 60.7% (n=3002) | 52.8% (n=3002) | 28.7% (n=10445) |
| 800-1199 | misses | 1816 | 100.0% (n=1816) | 32.3% (n=1816) | 24.7% (n=1816) | 17.0% (n=1816) | 10.0% (n=1816) | 17.4% (n=10445) |
| 800-1199 | loses_and_misses | 1203 | 100.0% (n=1203) | 83.8% (n=1203) | 79.2% (n=1203) | 72.5% (n=1203) | 64.7% (n=1203) | 11.5% (n=10445) |
| 800-1199 | neither | 2858 | 99.4% (n=2858) | 11.2% (n=2840) | 7.1% (n=2840) | 4.7% (n=2840) | 2.5% (n=2840) | 27.4% (n=10445) |
| 800-1199 | unknown | 1566 | 0.0% (n=1566) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 15.0% (n=10445) |
| 1200-1599 | loses | 4191 | 100.0% (n=4191) | 76.4% (n=4191) | 69.9% (n=4191) | 62.5% (n=4191) | 52.8% (n=4191) | 27.9% (n=15024) |
| 1200-1599 | misses | 2434 | 100.0% (n=2434) | 32.3% (n=2434) | 24.8% (n=2434) | 18.2% (n=2434) | 11.1% (n=2434) | 16.2% (n=15024) |
| 1200-1599 | loses_and_misses | 1448 | 100.0% (n=1448) | 84.2% (n=1448) | 78.8% (n=1448) | 72.0% (n=1448) | 64.2% (n=1448) | 9.6% (n=15024) |
| 1200-1599 | neither | 4476 | 99.4% (n=4476) | 14.0% (n=4451) | 9.2% (n=4451) | 5.2% (n=4451) | 2.7% (n=4451) | 29.8% (n=15024) |
| 1200-1599 | unknown | 2475 | 0.0% (n=2475) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 16.5% (n=15024) |
| 1600-1999 | loses | 4226 | 100.0% (n=4226) | 77.3% (n=4226) | 69.8% (n=4226) | 61.5% (n=4226) | 52.5% (n=4226) | 25.4% (n=16668) |
| 1600-1999 | misses | 2666 | 100.0% (n=2666) | 34.4% (n=2666) | 27.5% (n=2666) | 20.9% (n=2666) | 12.8% (n=2666) | 16.0% (n=16668) |
| 1600-1999 | loses_and_misses | 1433 | 100.0% (n=1433) | 86.0% (n=1433) | 80.2% (n=1433) | 73.3% (n=1433) | 64.8% (n=1433) | 8.6% (n=16668) |
| 1600-1999 | neither | 5399 | 99.6% (n=5399) | 15.1% (n=5379) | 10.0% (n=5379) | 6.0% (n=5379) | 3.2% (n=5379) | 32.4% (n=16668) |
| 1600-1999 | unknown | 2944 | 0.0% (n=2944) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 17.7% (n=16668) |
| 2000-2399 | loses | 1984 | 100.0% (n=1984) | 79.7% (n=1984) | 72.6% (n=1984) | 64.8% (n=1984) | 55.9% (n=1984) | 25.2% (n=7874) |
| 2000-2399 | misses | 1302 | 100.0% (n=1302) | 42.5% (n=1302) | 34.0% (n=1302) | 26.0% (n=1302) | 17.4% (n=1302) | 16.5% (n=7874) |
| 2000-2399 | loses_and_misses | 618 | 100.0% (n=618) | 88.8% (n=618) | 84.3% (n=618) | 77.7% (n=618) | 68.4% (n=618) | 7.8% (n=7874) |
| 2000-2399 | neither | 2689 | 99.5% (n=2689) | 20.7% (n=2676) | 13.8% (n=2676) | 7.8% (n=2676) | 3.4% (n=2676) | 34.2% (n=7874) |
| 2000-2399 | unknown | 1281 | 0.0% (n=1281) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 16.3% (n=7874) |
| 2400+ | loses | 321 | 100.0% (n=321) | 70.1% (n=321) | 62.6% (n=321) | 53.0% (n=321) | 41.4% (n=321) | 20.0% (n=1601) |
| 2400+ | misses | 211 | 100.0% (n=211) | 28.0% (n=211) | 21.8% (n=211) | 15.6% (n=211) | 10.9% (n=211) | 13.2% (n=1601) |
| 2400+ | loses_and_misses | 85 | 100.0% (n=85) | 89.4% (n=85) | 83.5% (n=85) | 75.3% (n=85) | 65.9% (n=85) | 5.3% (n=1601) |
| 2400+ | neither | 639 | 100.0% (n=639) | 15.3% (n=639) | 10.0% (n=639) | 4.5% (n=639) | 1.4% (n=639) | 39.9% (n=1601) |
| 2400+ | unknown | 345 | 0.0% (n=345) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 21.5% (n=1601) |

## Drill pool by cut

What the drill can draw from at each candidate cut (D-13), so the cut can be chosen before it ships. Scores use the drill lambda (1.0) and the model in this checkout. The report prints the pool at every cut and recommends none.

### Own pool per user

**Estimate** (D-23): usable blunder windows per non-guest user, as p25 / median, from exact per-user counts times per-bucket rates at the cut (after the 30% cap on pure misses); the Elo bucket columns count only a user's games in that bucket. A user under 50 windows falls back to foreign slots (250 D-15).

| cut | all users | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 122.9 / 478.0 | 5.3 / 60.0 | 3.4 / 37.4 | 5.6 / 46.1 | 6.9 / 122.4 | 14.6 / 149.3 | 2.8 / 23.8 |
| 0.60 | 107.5 / 414.4 | 4.7 / 53.0 | 2.9 / 32.4 | 4.8 / 39.9 | 5.9 / 104.7 | 12.4 / 126.5 | 2.3 / 19.7 |
| 0.70 | 90.9 / 349.3 | 4.0 / 45.6 | 2.5 / 27.4 | 4.1 / 33.7 | 4.9 / 86.9 | 10.2 / 104.0 | 1.7 / 14.7 |
| 0.80 | 75.4 / 284.6 | 3.4 / 38.3 | 2.0 / 22.8 | 3.3 / 27.0 | 3.9 / 69.0 | 8.0 / 81.6 | 1.2 / 10.7 |

### Foreign pool per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13), population estimates: the sample count times 1000 / 25 sample permille.

| level (pinned Elo) | note | qualifying >= 0.50 | qualifying >= 0.60 | qualifying >= 0.70 | qualifying >= 0.80 |
| --- | --- | --- | --- | --- | --- |
| 600 | extreme: below 800 | 103840 | 92520 | 80200 | 68800 |
| 800 |  | 26320 | 23520 | 20480 | 16760 |
| 1000 |  | 127720 | 112720 | 95880 | 80200 |
| 1200 |  | 195960 | 171560 | 146360 | 121400 |
| 1400 |  | 177280 | 154640 | 132160 | 107400 |
| 1600 |  | 199680 | 172560 | 146760 | 118720 |
| 1800 |  | 178840 | 153920 | 129840 | 104080 |
| 2000 |  | 176560 | 153080 | 128240 | 103000 |
| 2200 |  | 99640 | 85440 | 71560 | 57440 |
| 2400 | extreme: 2400 and above | 24600 | 21000 | 17600 | 14000 |
| 2600 | extreme: 2400 and above | 16000 | 13280 | 10200 | 7440 |

## Eval band

Pre-move ES bounds (D-15), at the chosen facepalm threshold. First table: share of qualifying (facepalm) blunders whose pre-move ES is inside the band. Second table: disjoint herring windows per game, averaged uniformly over window lengths 3 to 5, with the band applied to every judged user move.

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 100.0% (n=2699) | 100.0% (n=4182) | 100.0% (n=5827) | 100.0% (n=6227) | 100.0% (n=3237) | 100.0% (n=458) | 100.0% (n=22630) |
| [0.05, 0.95] | 91.0% (n=2699) | 92.9% (n=4182) | 94.8% (n=5827) | 94.4% (n=6227) | 94.7% (n=3237) | 92.1% (n=458) | 93.8% (n=22630) |
| [0.10, 0.90] | 81.7% (n=2699) | 86.0% (n=4182) | 88.7% (n=5827) | 89.0% (n=6227) | 89.1% (n=3237) | 86.0% (n=458) | 87.4% (n=22630) |
| [0.15, 0.85] | 70.5% (n=2699) | 75.7% (n=4182) | 79.4% (n=5827) | 80.3% (n=6227) | 80.7% (n=3237) | 77.1% (n=458) | 78.0% (n=22630) |
| [0.20, 0.80] | 59.5% (n=2699) | 65.9% (n=4182) | 69.8% (n=5827) | 71.3% (n=6227) | 72.5% (n=3237) | 69.2% (n=458) | 68.6% (n=22630) |

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 3.304 (n=2674) | 3.979 (n=4321) | 4.546 (n=6713) | 5.121 (n=8149) | 5.796 (n=3968) | 7.803 (n=939) | 4.805 (n=26764) |
| [0.05, 0.95] | 2.324 (n=2674) | 3.172 (n=4321) | 3.908 (n=6713) | 4.577 (n=8149) | 5.160 (n=3968) | 7.306 (n=939) | 4.140 (n=26764) |
| [0.10, 0.90] | 1.786 (n=2674) | 2.636 (n=4321) | 3.407 (n=6713) | 4.137 (n=8149) | 4.722 (n=3968) | 6.977 (n=939) | 3.663 (n=26764) |
| [0.15, 0.85] | 1.377 (n=2674) | 2.116 (n=4321) | 2.862 (n=6713) | 3.614 (n=8149) | 4.217 (n=3968) | 6.499 (n=939) | 3.151 (n=26764) |
| [0.20, 0.80] | 1.115 (n=2674) | 1.791 (n=4321) | 2.464 (n=6713) | 3.194 (n=8149) | 3.777 (n=3968) | 6.017 (n=939) | 2.762 (n=26764) |

## Window fit

Share of usable blunders (facepalm and pre-move ES in band) whose k-1 preceding user moves are all Good and in band, for window positions 1 to 5 (D-16). The last column weights the positions with the blunder-window position weights below.

| Elo bucket | usable blunders | pos 1 | pos 2 | pos 3 | pos 4 | pos 5 | window-weighted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 2204 | 100.0% (n=2204) | 52.2% (n=2204) | 32.2% (n=2204) | 20.4% (n=2204) | 13.8% (n=2204) | 62.1% (n=2204) |
| 800-1199 | 3595 | 100.0% (n=3595) | 56.7% (n=3595) | 37.6% (n=3595) | 25.8% (n=3595) | 18.3% (n=3595) | 65.2% (n=3595) |
| 1200-1599 | 5170 | 100.0% (n=5170) | 61.0% (n=5170) | 41.2% (n=5170) | 29.5% (n=5170) | 21.9% (n=5170) | 67.6% (n=5170) |
| 1600-1999 | 5543 | 100.0% (n=5543) | 62.8% (n=5543) | 44.8% (n=5543) | 32.8% (n=5543) | 25.4% (n=5543) | 69.3% (n=5543) |
| 2000-2399 | 2883 | 100.0% (n=2883) | 64.4% (n=2883) | 45.3% (n=2883) | 33.5% (n=2883) | 25.7% (n=2883) | 69.9% (n=2883) |
| 2400+ | 394 | 100.0% (n=394) | 67.3% (n=394) | 52.3% (n=394) | 42.9% (n=394) | 35.8% (n=394) | 73.4% (n=394) |
| all | 19789 | 100.0% (n=19789) | 60.4% (n=19789) | 41.4% (n=19789) | 29.6% (n=19789) | 22.2% (n=19789) | 67.5% (n=19789) |

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
| <800 | 2674 | 2.711 | 1.625 | 1.022 | 1.786 |
| 800-1199 | 4321 | 3.857 | 2.441 | 1.610 | 2.636 |
| 1200-1599 | 6713 | 4.894 | 3.147 | 2.178 | 3.407 |
| 1600-1999 | 8149 | 5.863 | 3.856 | 2.693 | 4.137 |
| 2000-2399 | 3968 | 6.616 | 4.412 | 3.137 | 4.722 |
| 2400+ | 939 | 9.532 | 6.559 | 4.840 | 6.977 |
| all | 26764 | 5.222 | 3.404 | 2.363 | 3.663 |

## Supply by origin

### Own supply per user

**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times per-bucket sample rates at the chosen threshold, after the 30% cap on pure misses. Rating groups approximate each game's exact Elo.

- Non-guest users with a fully evaluated game: 587
- Users under 50 usable blunder windows (their own slots turn into foreign ones, 250 D-15): 74 of 587

| per user | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- |
| usable blunder windows | 36.1 | 122.9 | 478.0 | 949.9 | 2027.8 |
| herring windows | 212.4 | 642.3 | 2870.5 | 7302.8 | 15464.4 |

### Foreign supply per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13: rating only, no widening). Counts are population estimates: the sample count times 1000 / 25 sample permille (non-guest games, so a run capped with `--limit-games` undercounts). A session takes at most one window per game, so the games column is the pool a foreign slot draws from. The rows below 800 and at 2400 and above are the extremes, where the pool is thinnest.

| level (pinned Elo) | mover Elo | qualifying blunders | usable (in band) | games with a qualifying blunder | sample n (qualifying) | note |
| --- | --- | --- | --- | --- | --- | --- |
| 600 | 450 to 750 | 103840 | 84640 | 59720 | 2596 | extreme: below 800 |
| 800 | 650 to 950 | 26320 | 22360 | 15080 | 658 |  |
| 1000 | 850 to 1150 | 127720 | 109000 | 73080 | 3193 |  |
| 1200 | 1050 to 1350 | 195960 | 170920 | 115200 | 4899 |  |
| 1400 | 1250 to 1550 | 177280 | 157360 | 109760 | 4432 |  |
| 1600 | 1450 to 1750 | 199680 | 176440 | 126000 | 4992 |  |
| 1800 | 1650 to 1950 | 178840 | 159680 | 115440 | 4471 |  |
| 2000 | 1850 to 2150 | 176560 | 157600 | 107800 | 4414 |  |
| 2200 | 2050 to 2350 | 99640 | 88760 | 60840 | 2491 |  |
| 2400 | 2250 to 2550 | 24600 | 21520 | 15400 | 615 | extreme: 2400 and above |
| 2600 | 2450 to 2750 | 16000 | 14040 | 11320 | 400 | extreme: 2400 and above |

## Provenance

Engine full evals against lichess `%eval` games (provenance = whether the game carries lichess evals). Rates, fit and supply are recomputed inside each provenance.

| provenance | games | blunders | usable blunders | window-weighted fit | herring windows per game | users | blunder windows p10 / p50 / p90 | users under 50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| engine | 24020 | 52692 | 17933 | 67.6% (n=17933) | 3.632 | 587 | 23.5 / 384.1 / 1871.6 | 98 of 587 |
| lichess | 2744 | 6088 | 1856 | 66.8% (n=1856) | 3.932 | 310 | 6.0 / 66.9 / 382.3 | 134 of 310 |

## Arrow oddness

Maia's probability of the move actually played, at the user's pinned Elo on the exact pre-move board (D-17). Good moves are a seeded sample of judged Good user moves (1500 per bucket requested, seed 248261108, 0 not scorable) with pre-move ES inside [0.10, 0.90]. Blunders are the usable ones at the chosen facepalm threshold and band, with their stored played-move probability.

AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows wins without reading the position.

| Elo bucket | n Good | n blunder | Good prob q1 / median / q3 | blunder prob q1 / median / q3 | AUC |
| --- | --- | --- | --- | --- | --- |
| <800 | 988 | 2204 | 0.138 / 0.301 / 0.534 | 0.019 / 0.054 / 0.134 | 0.837 |
| 800-1199 | 1100 | 3595 | 0.168 / 0.371 / 0.638 | 0.012 / 0.043 / 0.133 | 0.858 |
| 1200-1599 | 1205 | 5170 | 0.191 / 0.429 / 0.691 | 0.011 / 0.038 / 0.120 | 0.881 |
| 1600-1999 | 1274 | 5543 | 0.196 / 0.428 / 0.727 | 0.008 / 0.032 / 0.100 | 0.895 |
| 2000-2399 | 1278 | 2883 | 0.214 / 0.460 / 0.765 | 0.004 / 0.022 / 0.076 | 0.912 |
| 2400+ | 1366 | 394 | 0.219 / 0.468 / 0.785 | 0.006 / 0.024 / 0.100 | 0.901 |
| all | 7211 | 19789 | 0.184 / 0.414 / 0.701 | 0.009 / 0.036 / 0.112 | 0.883 |

### Drill against the unselected baseline

The target is not AUC 0.5: blunders looking somewhat odd is a real signal the drill should train. The target is a drill AUC close to the unselected one, i.e. selection does not widen the real-game gap. Unselected = every scored Good move against every rated user-side blunder (no band, no facepalm threshold); band only = both sides inside the eval band; drill = the table above. A clearly positive drill - unselected means flagging odd-looking arrows pays more in the drill than in games.

| Elo bucket | n Good (unselected) | n blunder (unselected) | AUC unselected | AUC band only | AUC drill | drill - unselected |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 1500 | 7168 | 0.755 | 0.760 | 0.837 | +0.082 |
| 800-1199 | 1500 | 10445 | 0.762 | 0.761 | 0.858 | +0.097 |
| 1200-1599 | 1500 | 15024 | 0.767 | 0.776 | 0.881 | +0.114 |
| 1600-1999 | 1500 | 16667 | 0.778 | 0.778 | 0.895 | +0.118 |
| 2000-2399 | 1500 | 7874 | 0.799 | 0.796 | 0.912 | +0.113 |
| 2400+ | 1500 | 1601 | 0.768 | 0.772 | 0.901 | +0.133 |
| all | 9000 | 58779 | 0.771 | 0.776 | 0.883 | +0.112 |

## Recommended constants

- Facepalm threshold **0.5** (a user blunder qualifies at or above it).
- Eval band **[0.10, 0.90]** on the pre-move ES.

These are a recommendation only: nothing here is wired into app code, and the owner decides the final values. Re-render with another `--facepalm-threshold` from the cache to compare.

Fair-share proxies per threshold (250 D-03: a false alarm is worse than a miss). The report cannot tell a fair position from an unfair one, so it prints what drives fairness among the passers: how rarely the move is played, how few replies the opponent has, and how often the stored line wins material or mates at once. The owner's labels (2026-11-13, decided labels with a stored line, cross-validated) measured fair among passers at >= 0.5: 80%, >= 0.7: 89%, >= 0.8: 92%. Judge precision on the spot-check, not on these columns alone.

| threshold | pass of scored | pass of all | median played prob | median reply spread | mate or >= 2 points down | median usable windows per user |
| --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 46.0% (n=49247) | 38.5% (n=58780) | 0.036 | 2.43 | 59.1% (n=22630) | 478.0 |
| 0.60 | 39.9% (n=49247) | 33.5% (n=58780) | 0.031 | 2.32 | 64.8% (n=19674) | 414.4 |
| 0.70 | 33.9% (n=49247) | 28.4% (n=58780) | 0.027 | 2.21 | 71.6% (n=16696) | 349.3 |
| 0.80 | 27.7% (n=49247) | 23.2% (n=58780) | 0.024 | 2.09 | 79.5% (n=13658) | 284.6 |

Window-weighted share of usable blunders (qualifying and in band) that fit a window, at the chosen threshold:

| Elo bucket | window fit (usable blunders) |
| --- | --- |
| <800 | 62.1% (n=2204) |
| 800-1199 | 65.2% (n=3595) |
| 1200-1599 | 67.6% (n=5170) |
| 1600-1999 | 69.3% (n=5543) |
| 2000-2399 | 69.9% (n=2883) |
| 2400+ | 73.4% (n=394) |
| all | 67.5% (n=19789) |

Resulting supply per non-guest user (estimate): median 478.0 usable blunder windows and 2870.5 herring windows; 74 of 587 users are under 50 blunder windows.

Read the spot-check before choosing: `spot-check-2026-11-16.md`.

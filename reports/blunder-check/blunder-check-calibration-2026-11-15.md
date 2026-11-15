# Blunder-check calibration report

## How to read this report

- **Population:** fully evaluated games on chess.com, lichess (pasted and bot games are out). Database: `flawchess`. Run date: 2026-11-15.
- **Sampling:** deterministic, 25 permille (2.5%) of games chosen by md5 residue of the game id; the same sample on every re-run.
- **Expected score (ES):** every ES comes from the flaw classifier's own per-ply pass (`_run_all_moves_pass`), from the mover's point of view. Pre-move ES is the ES before the user's move, `ES_played` the ES after the blunder, `ES_ref` the user's ES before the opponent's previous move (what the user would have had without the gift).
- **Cases (D-13):** *allowed* = the blunder is not a miss (the opponent's previous move was not a mistake or blunder). *Pure miss* = a miss whose `ES_played` is at least `ES_ref` minus the inaccuracy drop: the user only gave back what the opponent gifted. *Mixed* = a miss that lost more than the gift. *Unclassified* = a miss without usable ES.
- **Facepalm score (250 D-01, 254 D-01):** a ranking of how careless a blunder is at the mover's level, fitted on the owner's labels. The report reads the stored FACTS of each blunder (the played move's Maia probability, the opponent's reply spread, the depth-3 material of the played and best lines, both mate plies, the best move's probability and the pre-blunder spread) and scores them with the Python twin at the drill lambda (1.0) and the constants and model of this checkout, never the stored score column, so a candidate refit is judged here before it ships. It is not a probability and not a share of peers; a blunder qualifies when its score is at least the chosen threshold. A blunder without a score never qualifies; the Facepalm score section tells why.
- **Window mix (250 D-12):** every slot independently draws a herring (33%), an own blunder (33%) or a foreign blunder (33%); window length is uniform over 3 to 5 user moves for both kinds, a blunder's position follows the per-move hazard 0.265 within that length, 1 lead-in plies. Pure misses are capped at 30% of the blunder supply (report estimate only).
- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only aggregates times per-bucket sample rates, with rating groups approximating each game's exact Elo. It is an estimate, not an exact count.
- **Chosen values:** facepalm threshold = 0.7, eval band [0.10, 0.90]. These are a recommendation only; no constant is wired into app code by this report.
- Guest users' flaws are never Maia-scored, so guest games are excluded from every section except the sample counts.

## Sample

- Games sampled: 26784 (99 guest, excluded below)
- Games skipped for a ply gap: 54
- Unrated games (no rating at game time): 0 (0 user-side blunders not bucketed)
- User-side blunders (rated, non-guest): 58616

| Elo bucket | games (engine) | games (lichess) | blunders (engine) | blunders (lichess) |
| --- | --- | --- | --- | --- |
| <800 | 2600 | 74 | 6871 | 297 |
| 800-1199 | 3723 | 576 | 8931 | 1471 |
| 1200-1599 | 5999 | 696 | 13322 | 1671 |
| 1600-1999 | 7282 | 829 | 14870 | 1712 |
| 2000-2399 | 3559 | 408 | 7221 | 649 |
| 2400+ | 792 | 147 | 1340 | 261 |

## Control

Stored `game_flaws` (ply, severity) pairs against the mistakes and blunders recomputed from the per-ply evals (all sampled games, both colors; D-13).

- Agreement: 194023 of 194131 = 99.9% (n=194131)

## Cases by Elo bucket

| Elo bucket | blunders | allowed | pure_miss | mixed | unclassified | mixed / (pure miss + mixed) |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 7168 | 54.1% (n=7168) | 27.7% (n=7168) | 18.2% (n=7168) | 0.0% (n=7168) | 39.7% (n=3289) |
| 800-1199 | 10402 | 58.7% (n=10402) | 24.4% (n=10402) | 16.8% (n=10402) | 0.0% (n=10402) | 40.8% (n=4291) |
| 1200-1599 | 14993 | 62.4% (n=14993) | 22.7% (n=14993) | 14.9% (n=14993) | 0.0% (n=14993) | 39.7% (n=5638) |
| 1600-1999 | 16582 | 64.2% (n=16582) | 22.3% (n=16582) | 13.5% (n=16582) | 0.0% (n=16582) | 37.7% (n=5941) |
| 2000-2399 | 7870 | 64.8% (n=7870) | 21.6% (n=7870) | 13.6% (n=7870) | 0.0% (n=7870) | 38.7% (n=2768) |
| 2400+ | 1601 | 64.0% (n=1601) | 22.9% (n=1601) | 13.1% (n=1601) | 0.0% (n=1601) | 36.3% (n=576) |
| all | 58616 | 61.6% (n=58616) | 23.4% (n=58616) | 15.0% (n=58616) | 0.0% (n=58616) | 39.2% (n=22503) |

## Facepalm score

User-side blunders of rated, non-guest games and their stored facepalm score (250 D-01): a ranking of how careless the blunder is at the mover's level, not a share of peers. `scored` is the share with a score; the next four columns split the unscored ones by reason (shares of all user blunders): no reply spread yet, no stored engine line, a line shorter than 3 plies without an early mate (or one that cannot be replayed), and a missing played-move probability. The `pass` columns are shares of the scored blunders at or above each threshold; `qualifying of all` is the share of every user blunder that qualifies at the chosen threshold (an unscored blunder never qualifies).

| Elo bucket | user blunders | scored | no spread | no line | line too short | no played prob | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | qualifying of all (>= 0.70) | score q1 / median / q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 7168 | 88.4% (n=7168) | 0.0% (n=7168) | 6.7% (n=7168) | 4.9% (n=7168) | 0.0% (n=7168) | 46.2% (n=6335) | 40.1% (n=6335) | 34.6% (n=6335) | 29.2% (n=6335) | 30.5% (n=7168) | 0.162 / 0.436 / 0.867 |
| 800-1199 | 10402 | 85.0% (n=10402) | 0.0% (n=10402) | 6.2% (n=10402) | 8.8% (n=10402) | 0.0% (n=10402) | 49.3% (n=8842) | 42.3% (n=8842) | 36.4% (n=8842) | 30.3% (n=8842) | 30.9% (n=10402) | 0.178 / 0.492 / 0.887 |
| 1200-1599 | 14993 | 83.5% (n=14993) | 0.0% (n=14993) | 6.0% (n=14993) | 10.5% (n=14993) | 0.0% (n=14993) | 48.3% (n=12521) | 41.7% (n=12521) | 35.3% (n=12521) | 29.2% (n=12521) | 29.5% (n=14993) | 0.173 / 0.475 / 0.871 |
| 1600-1999 | 16582 | 82.3% (n=16582) | 0.0% (n=16582) | 7.6% (n=16582) | 10.1% (n=16582) | 0.0% (n=16582) | 47.2% (n=13650) | 40.0% (n=13650) | 33.1% (n=13650) | 26.8% (n=13650) | 27.2% (n=16582) | 0.161 / 0.459 / 0.826 |
| 2000-2399 | 7870 | 83.7% (n=7870) | 0.0% (n=7870) | 6.2% (n=7870) | 10.1% (n=7870) | 0.0% (n=7870) | 49.1% (n=6589) | 41.5% (n=6589) | 33.6% (n=6589) | 26.3% (n=6589) | 28.1% (n=7870) | 0.188 / 0.487 / 0.820 |
| 2400+ | 1601 | 78.5% (n=1601) | 0.1% (n=1601) | 0.7% (n=1601) | 20.8% (n=1601) | 0.0% (n=1601) | 38.3% (n=1256) | 31.4% (n=1256) | 25.1% (n=1256) | 19.0% (n=1256) | 19.7% (n=1601) | 0.128 / 0.382 / 0.701 |
| all | 58616 | 83.9% (n=58616) | 0.0% (n=58616) | 6.4% (n=58616) | 9.6% (n=58616) | 0.0% (n=58616) | 47.7% (n=49193) | 40.8% (n=49193) | 34.3% (n=49193) | 28.1% (n=49193) | 28.8% (n=58616) | 0.169 / 0.469 / 0.848 |

## Pass shares by material type

User-side blunders of rated, non-guest games by what they do to the material balance over 3 plies (D-13): *loses* = mated or ending behind on the played line, *misses* = the best line gains material the played line did not keep (or mates), *loses and misses* = both, *neither*, and *unknown* = the played line is too short to tell and holds no mate. Scores use the drill lambda (1.0) and the model in this checkout, computed from the stored facts. `scored` is the share of the type with a score; each `pass` column is the share of those scored blunders at or above the cut; the last column is the type's share of all user blunders in the row group.

| material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- |
| loses | 15733 | 100.0% (n=15733) | 88.5% (n=15733) | 80.8% (n=15733) | 72.3% (n=15733) | 61.7% (n=15733) | 26.8% (n=58616) |
| misses | 9897 | 100.0% (n=9897) | 26.6% (n=9897) | 16.5% (n=9897) | 7.4% (n=9897) | 1.1% (n=9897) | 16.9% (n=58616) |
| loses_and_misses | 5904 | 100.0% (n=5904) | 91.5% (n=5904) | 86.1% (n=5904) | 78.1% (n=5904) | 67.6% (n=5904) | 10.1% (n=58616) |
| neither | 17659 | 100.0% (n=17659) | 8.6% (n=17659) | 3.7% (n=17659) | 0.8% (n=17659) | 0.0% (n=17659) | 30.1% (n=58616) |
| unknown | 9423 | 0.0% (n=9423) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 16.1% (n=58616) |

### By Elo bucket

| Elo bucket | material type | user blunders | scored | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | share of blunders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | loses | 2046 | 100.0% (n=2046) | 79.5% (n=2046) | 72.5% (n=2046) | 65.4% (n=2046) | 56.2% (n=2046) | 28.5% (n=7168) |
| <800 | misses | 1502 | 100.0% (n=1502) | 20.0% (n=1502) | 10.7% (n=1502) | 3.3% (n=1502) | 0.1% (n=1502) | 21.0% (n=7168) |
| <800 | loses_and_misses | 1132 | 100.0% (n=1132) | 84.1% (n=1132) | 78.1% (n=1132) | 70.8% (n=1132) | 61.5% (n=1132) | 15.8% (n=7168) |
| <800 | neither | 1655 | 100.0% (n=1655) | 2.7% (n=1655) | 0.8% (n=1655) | 0.1% (n=1655) | 0.0% (n=1655) | 23.1% (n=7168) |
| <800 | unknown | 833 | 0.0% (n=833) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 11.6% (n=7168) |
| 800-1199 | loses | 2992 | 100.0% (n=2992) | 88.2% (n=2992) | 80.3% (n=2992) | 72.5% (n=2992) | 63.0% (n=2992) | 28.8% (n=10402) |
| 800-1199 | misses | 1804 | 100.0% (n=1804) | 24.6% (n=1804) | 14.2% (n=1804) | 6.2% (n=1804) | 0.5% (n=1804) | 17.3% (n=10402) |
| 800-1199 | loses_and_misses | 1195 | 100.0% (n=1195) | 91.3% (n=1195) | 85.2% (n=1195) | 77.1% (n=1195) | 65.7% (n=1195) | 11.5% (n=10402) |
| 800-1199 | neither | 2851 | 100.0% (n=2851) | 6.7% (n=2851) | 2.1% (n=2851) | 0.4% (n=2851) | 0.0% (n=2851) | 27.4% (n=10402) |
| 800-1199 | unknown | 1560 | 0.0% (n=1560) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 15.0% (n=10402) |
| 1200-1599 | loses | 4187 | 100.0% (n=4187) | 89.4% (n=4187) | 82.3% (n=4187) | 73.8% (n=4187) | 62.9% (n=4187) | 27.9% (n=14993) |
| 1200-1599 | misses | 2421 | 100.0% (n=2421) | 25.3% (n=2421) | 15.6% (n=2421) | 6.3% (n=2421) | 1.1% (n=2421) | 16.1% (n=14993) |
| 1200-1599 | loses_and_misses | 1446 | 100.0% (n=1446) | 93.0% (n=1446) | 87.5% (n=1446) | 79.6% (n=1446) | 69.0% (n=1446) | 9.6% (n=14993) |
| 1200-1599 | neither | 4467 | 100.0% (n=4467) | 7.7% (n=4467) | 3.0% (n=4467) | 0.6% (n=4467) | 0.0% (n=4467) | 29.8% (n=14993) |
| 1200-1599 | unknown | 2472 | 0.0% (n=2472) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 16.5% (n=14993) |
| 1600-1999 | loses | 4204 | 100.0% (n=4204) | 91.0% (n=4204) | 82.5% (n=4204) | 73.3% (n=4204) | 62.3% (n=4204) | 25.4% (n=16582) |
| 1600-1999 | misses | 2657 | 100.0% (n=2657) | 28.2% (n=2657) | 17.9% (n=2657) | 8.5% (n=2657) | 1.3% (n=2657) | 16.0% (n=16582) |
| 1600-1999 | loses_and_misses | 1428 | 100.0% (n=1428) | 94.2% (n=1428) | 89.5% (n=1428) | 80.7% (n=1428) | 70.0% (n=1428) | 8.6% (n=16582) |
| 1600-1999 | neither | 5361 | 100.0% (n=5361) | 9.7% (n=5361) | 4.4% (n=5361) | 1.1% (n=5361) | 0.0% (n=5361) | 32.3% (n=16582) |
| 1600-1999 | unknown | 2932 | 0.0% (n=2932) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 17.7% (n=16582) |
| 2000-2399 | loses | 1983 | 100.0% (n=1983) | 91.7% (n=1983) | 83.9% (n=1983) | 74.7% (n=1983) | 62.9% (n=1983) | 25.2% (n=7870) |
| 2000-2399 | misses | 1302 | 100.0% (n=1302) | 36.3% (n=1302) | 25.2% (n=1302) | 13.7% (n=1302) | 2.5% (n=1302) | 16.5% (n=7870) |
| 2000-2399 | loses_and_misses | 618 | 100.0% (n=618) | 95.3% (n=618) | 90.6% (n=618) | 82.8% (n=618) | 73.1% (n=618) | 7.9% (n=7870) |
| 2000-2399 | neither | 2686 | 100.0% (n=2686) | 13.3% (n=2686) | 6.8% (n=2686) | 1.5% (n=2686) | 0.0% (n=2686) | 34.1% (n=7870) |
| 2000-2399 | unknown | 1281 | 0.0% (n=1281) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 16.3% (n=7870) |
| 2400+ | loses | 321 | 100.0% (n=321) | 86.6% (n=321) | 76.3% (n=321) | 67.6% (n=321) | 55.1% (n=321) | 20.0% (n=1601) |
| 2400+ | misses | 211 | 100.0% (n=211) | 24.2% (n=211) | 15.2% (n=211) | 7.1% (n=211) | 0.5% (n=211) | 13.2% (n=1601) |
| 2400+ | loses_and_misses | 85 | 100.0% (n=85) | 97.6% (n=85) | 92.9% (n=85) | 88.2% (n=85) | 71.8% (n=85) | 5.3% (n=1601) |
| 2400+ | neither | 639 | 100.0% (n=639) | 10.8% (n=639) | 5.9% (n=639) | 1.3% (n=639) | 0.0% (n=639) | 39.9% (n=1601) |
| 2400+ | unknown | 345 | 0.0% (n=345) | n/a (n=0) | n/a (n=0) | n/a (n=0) | n/a (n=0) | 21.5% (n=1601) |

## Drill pool by cut

What the drill can draw from at each candidate cut (D-13), so the cut can be chosen before it ships. Scores use the drill lambda (1.0) and the model in this checkout. The report prints the pool at every cut and recommends none.

### Own pool per user

**Estimate** (D-23): usable blunder windows per non-guest user, as p25 / median, from exact per-user counts times per-bucket rates at the cut (after the 30% cap on pure misses); the Elo bucket columns count only a user's games in that bucket. A user under 50 windows falls back to foreign slots (250 D-15).

| cut | all users | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 132.6 / 507.5 | 5.9 / 66.9 | 3.6 / 40.0 | 5.9 / 48.7 | 7.3 / 129.0 | 14.8 / 151.1 | 2.9 / 25.3 |
| 0.60 | 112.8 / 434.0 | 5.1 / 57.9 | 3.1 / 34.0 | 5.1 / 41.9 | 6.1 / 108.8 | 12.4 / 126.5 | 2.4 / 20.4 |
| 0.70 | 96.8 / 367.5 | 4.4 / 49.6 | 2.6 / 29.2 | 4.3 / 35.3 | 5.1 / 89.6 | 9.9 / 101.2 | 1.8 / 15.9 |
| 0.80 | 81.0 / 301.6 | 3.7 / 41.8 | 2.2 / 24.3 | 3.5 / 29.0 | 4.1 / 72.1 | 7.7 / 78.8 | 1.4 / 12.2 |

### Foreign pool per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13), population estimates: the sample count times 1000 / 25 sample permille.

| level (pinned Elo) | note | qualifying >= 0.50 | qualifying >= 0.60 | qualifying >= 0.70 | qualifying >= 0.80 |
| --- | --- | --- | --- | --- | --- |
| 600 | extreme: below 800 | 112720 | 98200 | 84600 | 71600 |
| 800 |  | 28080 | 24240 | 20600 | 16960 |
| 1000 |  | 133560 | 114520 | 98200 | 81920 |
| 1200 |  | 204280 | 176200 | 151400 | 126560 |
| 1400 |  | 184400 | 158120 | 133640 | 110600 |
| 1600 |  | 206720 | 176560 | 146920 | 120160 |
| 1800 |  | 184880 | 156880 | 129800 | 103960 |
| 2000 |  | 178000 | 152800 | 126320 | 100760 |
| 2200 |  | 99920 | 84400 | 68640 | 54080 |
| 2400 | extreme: 2400 and above | 24840 | 20480 | 16880 | 13080 |
| 2600 | extreme: 2400 and above | 16600 | 13720 | 10880 | 8360 |

## Eval band

Pre-move ES bounds (D-15), at the chosen facepalm threshold. First table: share of qualifying (facepalm) blunders whose pre-move ES is inside the band. Second table: disjoint herring windows per game, averaged uniformly over window lengths 3 to 5, with the band applied to every judged user move.

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 100.0% (n=2189) | 100.0% (n=3215) | 100.0% (n=4419) | 100.0% (n=4518) | 100.0% (n=2214) | 100.0% (n=315) | 100.0% (n=16870) |
| [0.05, 0.95] | 93.1% (n=2189) | 95.0% (n=3215) | 96.0% (n=4419) | 95.5% (n=4518) | 95.1% (n=2214) | 92.1% (n=315) | 95.1% (n=16870) |
| [0.10, 0.90] | 84.3% (n=2189) | 88.1% (n=3215) | 90.0% (n=4419) | 90.1% (n=4518) | 88.9% (n=2214) | 86.7% (n=315) | 88.7% (n=16870) |
| [0.15, 0.85] | 73.1% (n=2189) | 77.4% (n=3215) | 80.7% (n=4419) | 81.4% (n=4518) | 80.0% (n=2214) | 77.1% (n=315) | 79.1% (n=16870) |
| [0.20, 0.80] | 63.3% (n=2189) | 68.8% (n=3215) | 71.8% (n=4419) | 73.0% (n=4518) | 72.3% (n=2214) | 70.2% (n=315) | 70.5% (n=16870) |

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 3.304 (n=2674) | 3.981 (n=4299) | 4.547 (n=6695) | 5.123 (n=8111) | 5.796 (n=3967) | 7.803 (n=939) | 4.806 (n=26685) |
| [0.05, 0.95] | 2.324 (n=2674) | 3.171 (n=4299) | 3.909 (n=6695) | 4.579 (n=8111) | 5.160 (n=3967) | 7.306 (n=939) | 4.140 (n=26685) |
| [0.10, 0.90] | 1.786 (n=2674) | 2.634 (n=4299) | 3.408 (n=6695) | 4.138 (n=8111) | 4.722 (n=3967) | 6.977 (n=939) | 3.664 (n=26685) |
| [0.15, 0.85] | 1.377 (n=2674) | 2.114 (n=4299) | 2.863 (n=6695) | 3.615 (n=8111) | 4.217 (n=3967) | 6.499 (n=939) | 3.151 (n=26685) |
| [0.20, 0.80] | 1.115 (n=2674) | 1.790 (n=4299) | 2.466 (n=6695) | 3.196 (n=8111) | 3.778 (n=3967) | 6.017 (n=939) | 2.764 (n=26685) |

## Window fit

Share of usable blunders (facepalm and pre-move ES in band) whose k-1 preceding user moves are all Good and in band, for window positions 1 to 5 (D-16). The last column weights the positions with the blunder-window position weights below.

| Elo bucket | usable blunders | pos 1 | pos 2 | pos 3 | pos 4 | pos 5 | window-weighted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 1846 | 100.0% (n=1846) | 50.5% (n=1846) | 31.0% (n=1846) | 20.1% (n=1846) | 13.7% (n=1846) | 61.4% (n=1846) |
| 800-1199 | 2834 | 100.0% (n=2834) | 55.4% (n=2834) | 36.9% (n=2834) | 25.1% (n=2834) | 17.8% (n=2834) | 64.6% (n=2834) |
| 1200-1599 | 3978 | 100.0% (n=3978) | 60.1% (n=3978) | 40.5% (n=3978) | 28.8% (n=3978) | 21.9% (n=3978) | 67.1% (n=3978) |
| 1600-1999 | 4072 | 100.0% (n=4072) | 61.5% (n=4072) | 44.2% (n=4072) | 31.8% (n=4072) | 24.6% (n=4072) | 68.7% (n=4072) |
| 2000-2399 | 1968 | 100.0% (n=1968) | 63.1% (n=1968) | 44.8% (n=1968) | 33.4% (n=1968) | 25.4% (n=1968) | 69.4% (n=1968) |
| 2400+ | 273 | 100.0% (n=273) | 64.5% (n=273) | 46.9% (n=273) | 37.7% (n=273) | 30.4% (n=273) | 70.8% (n=273) |
| all | 14971 | 100.0% (n=14971) | 58.9% (n=14971) | 40.3% (n=14971) | 28.6% (n=14971) | 21.4% (n=14971) | 66.7% (n=14971) |

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
| 800-1199 | 4299 | 3.854 | 2.440 | 1.608 | 2.634 |
| 1200-1599 | 6695 | 4.897 | 3.149 | 2.180 | 3.408 |
| 1600-1999 | 8111 | 5.864 | 3.857 | 2.693 | 4.138 |
| 2000-2399 | 3967 | 6.617 | 4.412 | 3.138 | 4.722 |
| 2400+ | 939 | 9.532 | 6.559 | 4.840 | 6.977 |
| all | 26685 | 5.222 | 3.405 | 2.364 | 3.664 |

## Supply by origin

### Own supply per user

**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times per-bucket sample rates at the chosen threshold, after the 30% cap on pure misses. Rating groups approximate each game's exact Elo.

- Non-guest users with a fully evaluated game: 586
- Users under 50 usable blunder windows (their own slots turn into foreign ones, 250 D-15): 88 of 586

| per user | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- |
| usable blunder windows | 28.1 | 96.8 | 367.5 | 710.7 | 1527.6 |
| herring windows | 212.3 | 642.1 | 2844.6 | 7304.3 | 15115.7 |

### Foreign supply per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13: rating only, no widening). Counts are population estimates: the sample count times 1000 / 25 sample permille (non-guest games, so a run capped with `--limit-games` undercounts). A session takes at most one window per game, so the games column is the pool a foreign slot draws from. The rows below 800 and at 2400 and above are the extremes, where the pool is thinnest.

| level (pinned Elo) | mover Elo | qualifying blunders | usable (in band) | games with a qualifying blunder | sample n (qualifying) | note |
| --- | --- | --- | --- | --- | --- | --- |
| 600 | 450 to 750 | 84600 | 71320 | 53560 | 2115 | extreme: below 800 |
| 800 | 650 to 950 | 20600 | 17720 | 13560 | 515 |  |
| 1000 | 850 to 1150 | 98200 | 86080 | 63680 | 2455 |  |
| 1200 | 1050 to 1350 | 151400 | 134760 | 98760 | 3785 |  |
| 1400 | 1250 to 1550 | 133640 | 120320 | 92000 | 3341 |  |
| 1600 | 1450 to 1750 | 146920 | 132280 | 103200 | 3673 |  |
| 1800 | 1650 to 1950 | 129800 | 117360 | 92520 | 3245 |  |
| 2000 | 1850 to 2150 | 126320 | 112920 | 85640 | 3158 |  |
| 2200 | 2050 to 2350 | 68640 | 61120 | 47200 | 1716 |  |
| 2400 | 2250 to 2550 | 16880 | 14480 | 11720 | 422 | extreme: 2400 and above |
| 2600 | 2450 to 2750 | 10880 | 9720 | 8320 | 272 | extreme: 2400 and above |

## Provenance

Engine full evals against lichess `%eval` games (provenance = whether the game carries lichess evals). Rates, fit and supply are recomputed inside each provenance.

| provenance | games | blunders | usable blunders | window-weighted fit | herring windows per game | users | blunder windows p10 / p50 / p90 | users under 50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| engine | 23955 | 52555 | 13612 | 66.8% (n=13612) | 3.633 | 586 | 18.3 / 293.7 / 1431.5 | 115 of 586 |
| lichess | 2730 | 6061 | 1359 | 65.9% (n=1359) | 3.937 | 309 | 4.3 / 48.3 / 282.9 | 158 of 309 |

## Arrow oddness

Maia's probability of the move actually played, at the user's pinned Elo on the exact pre-move board (D-17). Good moves are a seeded sample of judged Good user moves (1500 per bucket requested, seed 248261108, 0 not scorable) with pre-move ES inside [0.10, 0.90]. Blunders are the usable ones at the chosen facepalm threshold and band, with their stored played-move probability.

AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows wins without reading the position.

| Elo bucket | n Good | n blunder | Good prob q1 / median / q3 | blunder prob q1 / median / q3 | AUC |
| --- | --- | --- | --- | --- | --- |
| <800 | 988 | 1846 | 0.138 / 0.301 / 0.534 | 0.020 / 0.059 / 0.149 | 0.820 |
| 800-1199 | 1101 | 2834 | 0.171 / 0.375 / 0.641 | 0.012 / 0.048 / 0.164 | 0.840 |
| 1200-1599 | 1206 | 3978 | 0.191 / 0.429 / 0.692 | 0.010 / 0.041 / 0.144 | 0.862 |
| 1600-1999 | 1276 | 4072 | 0.197 / 0.428 / 0.724 | 0.006 / 0.030 / 0.122 | 0.879 |
| 2000-2399 | 1282 | 1968 | 0.211 / 0.456 / 0.765 | 0.003 / 0.017 / 0.080 | 0.902 |
| 2400+ | 1364 | 273 | 0.217 / 0.469 / 0.780 | 0.003 / 0.027 / 0.160 | 0.873 |
| all | 7217 | 14971 | 0.184 / 0.415 / 0.701 | 0.008 / 0.037 / 0.136 | 0.866 |

### Drill against the unselected baseline

The target is not AUC 0.5: blunders looking somewhat odd is a real signal the drill should train. The target is a drill AUC close to the unselected one, i.e. selection does not widen the real-game gap. Unselected = every scored Good move against every rated user-side blunder (no band, no facepalm threshold); band only = both sides inside the eval band; drill = the table above. A clearly positive drill - unselected means flagging odd-looking arrows pays more in the drill than in games.

| Elo bucket | n Good (unselected) | n blunder (unselected) | AUC unselected | AUC band only | AUC drill | drill - unselected |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 1500 | 7168 | 0.755 | 0.760 | 0.820 | +0.065 |
| 800-1199 | 1500 | 10402 | 0.763 | 0.762 | 0.840 | +0.077 |
| 1200-1599 | 1500 | 14993 | 0.767 | 0.776 | 0.862 | +0.095 |
| 1600-1999 | 1500 | 16581 | 0.778 | 0.778 | 0.879 | +0.101 |
| 2000-2399 | 1500 | 7870 | 0.799 | 0.795 | 0.902 | +0.103 |
| 2400+ | 1500 | 1601 | 0.767 | 0.772 | 0.873 | +0.106 |
| all | 9000 | 58615 | 0.771 | 0.776 | 0.866 | +0.094 |

## Recommended constants

- Facepalm threshold **0.7** (a user blunder qualifies at or above it).
- Eval band **[0.10, 0.90]** on the pre-move ES.

These are a recommendation only: nothing here is wired into app code, and the owner decides the final values. Re-render with another `--facepalm-threshold` from the cache to compare.

Fair-share proxies per threshold (250 D-03: a false alarm is worse than a miss). The report cannot tell a fair position from an unfair one, so it prints what drives fairness among the passers: how rarely the move is played, how few replies the opponent has, and how often the stored line wins material or mates at once. The owner's labels (2026-11-13, decided labels with a stored line, cross-validated) measured fair among passers at >= 0.5: 80%, >= 0.7: 89%, >= 0.8: 92%. Judge precision on the spot-check, not on these columns alone.

| threshold | pass of scored | pass of all | median played prob | median reply spread | mate or >= 2 points down | median usable windows per user |
| --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 47.7% (n=49193) | 40.1% (n=58616) | 0.041 | 2.59 | 63.3% (n=23487) | 507.5 |
| 0.60 | 40.8% (n=49193) | 34.3% (n=58616) | 0.036 | 2.45 | 72.8% (n=20083) | 434.0 |
| 0.70 | 34.3% (n=49193) | 28.8% (n=58616) | 0.035 | 2.30 | 83.7% (n=16870) | 367.5 |
| 0.80 | 28.1% (n=49193) | 23.6% (n=58616) | 0.038 | 2.18 | 94.4% (n=13810) | 301.6 |

Window-weighted share of usable blunders (qualifying and in band) that fit a window, at the chosen threshold:

| Elo bucket | window fit (usable blunders) |
| --- | --- |
| <800 | 61.4% (n=1846) |
| 800-1199 | 64.6% (n=2834) |
| 1200-1599 | 67.1% (n=3978) |
| 1600-1999 | 68.7% (n=4072) |
| 2000-2399 | 69.4% (n=1968) |
| 2400+ | 70.8% (n=273) |
| all | 66.7% (n=14971) |

Resulting supply per non-guest user (estimate): median 367.5 usable blunder windows and 2844.6 herring windows; 88 of 586 users are under 50 blunder windows.

Read the spot-check before choosing: `spot-check-2026-11-15.md`.

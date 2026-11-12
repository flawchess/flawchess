# Blunder-check calibration report

## How to read this report

- **Population:** fully evaluated games on chess.com, lichess (pasted and bot games are out). Database: `flawchess`. Run date: 2026-11-10.
- **Sampling:** deterministic, 25 permille (2.5%) of games chosen by md5 residue of the game id; the same sample on every re-run.
- **Expected score (ES):** every ES comes from the flaw classifier's own per-ply pass (`_run_all_moves_pass`), from the mover's point of view. Pre-move ES is the ES before the user's move, `ES_played` the ES after the blunder, `ES_ref` the user's ES before the opponent's previous move (what the user would have had without the gift).
- **Cases (D-13):** *allowed* = the blunder is not a miss (the opponent's previous move was not a mistake or blunder). *Pure miss* = a miss whose `ES_played` is at least `ES_ref` minus the inaccuracy drop: the user only gave back what the opponent gifted. *Mixed* = a miss that lost more than the gift. *Unclassified* = a miss without usable ES.
- **Findability (D-14):** allowed blunders test Maia's probability of the refutation, pure misses Maia's probability of the best move, mixed ones pass if either does; a pair passes at threshold t when its probability is at least t or its rank is 1.
- **Hazard model (D-16):** per-move blunder hazard 0.265, window length uniform over 3 to 5 user moves, 3 lead-in plies. Pure misses are capped at 30% of the blunder supply.
- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only aggregates times per-bucket sample rates, with rating groups approximating each game's exact Elo. It is an estimate, not an exact count.
- **Chosen values:** refutation R = 0.3, best-move X' = 0.2, eval band [0.10, 0.90]. These are a recommendation only; no constant is wired into app code in this phase.
- Guest users' flaws are never Maia-scored, so guest games are excluded from every section except the sample counts.

## Sample

- Games sampled: 26477 (79 guest, excluded below)
- Games skipped for a ply gap: 52
- Unrated games (no rating at game time): 0 (0 user-side blunders not bucketed)
- User-side blunders (rated, non-guest): 57947

| Elo bucket | games (engine) | games (lichess) | blunders (engine) | blunders (lichess) |
| --- | --- | --- | --- | --- |
| <800 | 2558 | 74 | 6730 | 297 |
| 800-1199 | 3699 | 576 | 8883 | 1471 |
| 1200-1599 | 5867 | 692 | 13026 | 1664 |
| 1600-1999 | 7212 | 818 | 14712 | 1697 |
| 2000-2399 | 3555 | 408 | 7217 | 649 |
| 2400+ | 792 | 147 | 1340 | 261 |

## Control

Stored `game_flaws` (ply, severity) pairs against the mistakes and blunders recomputed from the per-ply evals (all sampled games, both colors; D-13).

- Agreement: 191633 of 191741 = 99.9% (n=191741)

## Cases by Elo bucket

| Elo bucket | blunders | allowed | pure_miss | mixed | unclassified | mixed / (pure miss + mixed) |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 7027 | 54.1% (n=7027) | 27.7% (n=7027) | 18.2% (n=7027) | 0.0% (n=7027) | 39.6% (n=3226) |
| 800-1199 | 10354 | 58.7% (n=10354) | 24.4% (n=10354) | 16.8% (n=10354) | 0.0% (n=10354) | 40.8% (n=4273) |
| 1200-1599 | 14690 | 62.4% (n=14690) | 22.7% (n=14690) | 14.9% (n=14690) | 0.0% (n=14690) | 39.6% (n=5526) |
| 1600-1999 | 16409 | 64.2% (n=16409) | 22.3% (n=16409) | 13.5% (n=16409) | 0.0% (n=16409) | 37.7% (n=5880) |
| 2000-2399 | 7866 | 64.8% (n=7866) | 21.6% (n=7866) | 13.6% (n=7866) | 0.0% (n=7866) | 38.6% (n=2767) |
| 2400+ | 1601 | 64.0% (n=1601) | 22.9% (n=1601) | 13.1% (n=1601) | 0.0% (n=1601) | 36.3% (n=576) |
| all | 57947 | 61.6% (n=57947) | 23.4% (n=57947) | 15.0% (n=57947) | 0.0% (n=57947) | 39.1% (n=22248) |

## Findability grid

Share of scored blunders passing the Maia test at each threshold t (D-14); unscored (NULL pair) blunders are counted separately and excluded from every denominator. A pair passes at t when its probability is at least t or its rank is 1; the `rank 1 only` column counts rank 1 alone.

### Allowed (refutation pair, t = R)

| Elo bucket | n scored | unscored (NULL pair) | rank 1 only | 0.05 | 0.10 | 0.15 | 0.20 | 0.30 | 0.40 | 0.50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 3799 | 2 | 63.6% (n=3799) | 93.0% (n=3799) | 85.0% (n=3799) | 78.9% (n=3799) | 74.1% (n=3799) | 67.0% (n=3799) | 64.2% (n=3799) | 63.6% (n=3799) |
| 800-1199 | 6070 | 11 | 68.1% (n=6070) | 93.9% (n=6070) | 88.8% (n=6070) | 83.8% (n=6070) | 79.2% (n=6070) | 72.7% (n=6070) | 69.1% (n=6070) | 68.1% (n=6070) |
| 1200-1599 | 9144 | 20 | 70.2% (n=9144) | 94.4% (n=9144) | 89.4% (n=9144) | 85.1% (n=9144) | 81.4% (n=9144) | 75.1% (n=9144) | 71.3% (n=9144) | 70.2% (n=9144) |
| 1600-1999 | 10511 | 18 | 70.3% (n=10511) | 94.2% (n=10511) | 89.6% (n=10511) | 85.5% (n=10511) | 81.7% (n=10511) | 75.6% (n=10511) | 71.6% (n=10511) | 70.3% (n=10511) |
| 2000-2399 | 5093 | 6 | 72.0% (n=5093) | 94.7% (n=5093) | 90.8% (n=5093) | 87.0% (n=5093) | 83.6% (n=5093) | 77.3% (n=5093) | 73.3% (n=5093) | 72.0% (n=5093) |
| 2400+ | 1024 | 1 | 63.2% (n=1024) | 94.1% (n=1024) | 88.2% (n=1024) | 82.7% (n=1024) | 77.6% (n=1024) | 69.4% (n=1024) | 64.6% (n=1024) | 63.2% (n=1024) |
| all | 35641 | 58 | 69.2% (n=35641) | 94.1% (n=35641) | 89.1% (n=35641) | 84.5% (n=35641) | 80.6% (n=35641) | 74.1% (n=35641) | 70.4% (n=35641) | 69.2% (n=35641) |

### Pure miss (best-move pair, t = X')

| Elo bucket | n scored | unscored (NULL pair) | rank 1 only | 0.05 | 0.10 | 0.15 | 0.20 | 0.30 | 0.40 | 0.50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 1946 | 1 | 42.9% (n=1946) | 85.6% (n=1946) | 73.4% (n=1946) | 62.0% (n=1946) | 53.9% (n=1946) | 45.8% (n=1946) | 43.3% (n=1946) | 42.9% (n=1946) |
| 800-1199 | 2527 | 2 | 45.6% (n=2527) | 85.2% (n=2527) | 74.6% (n=2527) | 66.6% (n=2527) | 59.4% (n=2527) | 50.3% (n=2527) | 46.4% (n=2527) | 45.6% (n=2527) |
| 1200-1599 | 3336 | 4 | 46.4% (n=3336) | 86.9% (n=3336) | 78.2% (n=3336) | 69.9% (n=3336) | 62.3% (n=3336) | 52.3% (n=3336) | 47.6% (n=3336) | 46.4% (n=3336) |
| 1600-1999 | 3657 | 7 | 49.1% (n=3657) | 86.9% (n=3657) | 78.8% (n=3657) | 71.5% (n=3657) | 64.4% (n=3657) | 54.5% (n=3657) | 50.2% (n=3657) | 49.1% (n=3657) |
| 2000-2399 | 1694 | 4 | 54.8% (n=1694) | 89.3% (n=1694) | 80.9% (n=1694) | 74.2% (n=1694) | 69.4% (n=1694) | 60.7% (n=1694) | 56.4% (n=1694) | 54.8% (n=1694) |
| 2400+ | 367 | 0 | 45.2% (n=367) | 87.5% (n=367) | 75.2% (n=367) | 68.4% (n=367) | 60.5% (n=367) | 51.5% (n=367) | 46.3% (n=367) | 45.2% (n=367) |
| all | 13527 | 18 | 47.5% (n=13527) | 86.7% (n=13527) | 77.3% (n=13527) | 69.1% (n=13527) | 61.9% (n=13527) | 52.6% (n=13527) | 48.5% (n=13527) | 47.5% (n=13527) |

### Mixed (either pair passes, R = X' = t)

| Elo bucket | n scored | unscored (NULL pair) | rank 1 only | 0.05 | 0.10 | 0.15 | 0.20 | 0.30 | 0.40 | 0.50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 1279 | 0 | 75.9% (n=1279) | 98.6% (n=1279) | 94.9% (n=1279) | 89.5% (n=1279) | 84.4% (n=1279) | 78.1% (n=1279) | 76.2% (n=1279) | 75.9% (n=1279) |
| 800-1199 | 1744 | 0 | 81.5% (n=1744) | 99.2% (n=1744) | 96.9% (n=1744) | 93.5% (n=1744) | 90.9% (n=1744) | 86.4% (n=1744) | 82.3% (n=1744) | 81.5% (n=1744) |
| 1200-1599 | 2185 | 1 | 80.9% (n=2185) | 98.8% (n=2185) | 96.5% (n=2185) | 93.8% (n=2185) | 90.5% (n=2185) | 84.6% (n=2185) | 81.9% (n=2185) | 80.9% (n=2185) |
| 1600-1999 | 2216 | 0 | 82.1% (n=2216) | 99.1% (n=2216) | 97.2% (n=2216) | 94.4% (n=2216) | 91.8% (n=2216) | 86.4% (n=2216) | 83.4% (n=2216) | 82.1% (n=2216) |
| 2000-2399 | 1068 | 1 | 86.2% (n=1068) | 99.2% (n=1068) | 97.8% (n=1068) | 96.2% (n=1068) | 94.0% (n=1068) | 90.0% (n=1068) | 87.0% (n=1068) | 86.2% (n=1068) |
| 2400+ | 209 | 0 | 80.4% (n=209) | 99.5% (n=209) | 98.6% (n=209) | 96.7% (n=209) | 92.3% (n=209) | 85.6% (n=209) | 81.3% (n=209) | 80.4% (n=209) |
| all | 8701 | 2 | 81.2% (n=8701) | 99.0% (n=8701) | 96.7% (n=8701) | 93.6% (n=8701) | 90.5% (n=8701) | 85.1% (n=8701) | 82.1% (n=8701) | 81.2% (n=8701) |

## Eval band

Pre-move ES bounds (D-15), at the chosen R and X'. First table: share of qualifying (findable) blunders whose pre-move ES is inside the band. Second table: disjoint herring windows per game, averaged uniformly over window lengths 3 to 5, with the band applied to every judged user move.

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 100.0% (n=4626) | 100.0% (n=7454) | 100.0% (n=10862) | 100.0% (n=12270) | 100.0% (n=6090) | 100.0% (n=1120) | 100.0% (n=42422) |
| [0.05, 0.95] | 91.4% (n=4626) | 93.7% (n=7454) | 94.9% (n=10862) | 95.3% (n=12270) | 95.5% (n=6090) | 94.6% (n=1120) | 94.5% (n=42422) |
| [0.10, 0.90] | 84.1% (n=4626) | 88.2% (n=7454) | 90.0% (n=10862) | 90.8% (n=12270) | 90.6% (n=6090) | 90.1% (n=1120) | 89.4% (n=42422) |
| [0.15, 0.85] | 74.4% (n=4626) | 79.5% (n=7454) | 81.9% (n=10862) | 82.9% (n=12270) | 83.3% (n=6090) | 83.4% (n=1120) | 81.2% (n=42422) |
| [0.20, 0.80] | 64.3% (n=4626) | 69.1% (n=7454) | 72.4% (n=10862) | 73.6% (n=12270) | 74.9% (n=6090) | 75.4% (n=1120) | 71.7% (n=42422) |

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 3.283 (n=2632) | 3.978 (n=4275) | 4.543 (n=6559) | 5.126 (n=8030) | 5.798 (n=3963) | 7.803 (n=939) | 4.808 (n=26398) |
| [0.05, 0.95] | 2.310 (n=2632) | 3.167 (n=4275) | 3.901 (n=6559) | 4.580 (n=8030) | 5.162 (n=3963) | 7.306 (n=939) | 4.141 (n=26398) |
| [0.10, 0.90] | 1.774 (n=2632) | 2.632 (n=4275) | 3.399 (n=6559) | 4.139 (n=8030) | 4.724 (n=3963) | 6.977 (n=939) | 3.664 (n=26398) |
| [0.15, 0.85] | 1.369 (n=2632) | 2.114 (n=4275) | 2.854 (n=6559) | 3.617 (n=8030) | 4.219 (n=3963) | 6.499 (n=939) | 3.153 (n=26398) |
| [0.20, 0.80] | 1.108 (n=2632) | 1.791 (n=4275) | 2.460 (n=6559) | 3.198 (n=8030) | 3.779 (n=3963) | 6.017 (n=939) | 2.766 (n=26398) |

## Window fit

Share of usable blunders (findable and pre-move ES in band) whose k-1 preceding user moves are all Good and in band, for window positions 1 to 5 (D-16). The last column weights the positions with the normalized hazard weights below.

| Elo bucket | usable blunders | pos 1 | pos 2 | pos 3 | pos 4 | pos 5 | hazard-weighted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 3890 | 100.0% (n=3890) | 55.2% (n=3890) | 34.3% (n=3890) | 22.0% (n=3890) | 15.0% (n=3890) | 63.1% (n=3890) |
| 800-1199 | 6573 | 100.0% (n=6573) | 59.4% (n=6573) | 38.8% (n=6573) | 26.6% (n=6573) | 18.9% (n=6573) | 65.8% (n=6573) |
| 1200-1599 | 9777 | 100.0% (n=9777) | 62.9% (n=9777) | 43.1% (n=9777) | 31.1% (n=9777) | 23.2% (n=9777) | 68.2% (n=9777) |
| 1600-1999 | 11147 | 100.0% (n=11147) | 65.0% (n=11147) | 46.5% (n=11147) | 34.0% (n=11147) | 26.3% (n=11147) | 69.9% (n=11147) |
| 2000-2399 | 5519 | 100.0% (n=5519) | 67.2% (n=5519) | 48.0% (n=5519) | 36.3% (n=5519) | 28.7% (n=5519) | 71.2% (n=5519) |
| 2400+ | 1009 | 100.0% (n=1009) | 68.3% (n=1009) | 54.7% (n=1009) | 43.3% (n=1009) | 34.9% (n=1009) | 73.8% (n=1009) |
| all | 37915 | 100.0% (n=37915) | 62.9% (n=37915) | 43.5% (n=37915) | 31.3% (n=37915) | 23.6% (n=37915) | 68.4% (n=37915) |

Hazard 0.265, window length uniform over (3, 4, 5); herring (no-blunder) share 0.3011.

| position | raw P(blunder at k) | normalized weight |
| --- | --- | --- |
| 1 | 0.2650 | 0.3792 |
| 2 | 0.1948 | 0.2787 |
| 3 | 0.1432 | 0.2048 |
| 4 | 0.0701 | 0.1004 |
| 5 | 0.0258 | 0.0369 |

## Herring supply

Disjoint windows of L consecutive Good user moves with pre-move ES in [0.10, 0.90], per sampled game. Each maximal run of qualifying moves contributes floor(run / L) windows.

| Elo bucket | games | L=3 | L=4 | L=5 | L-uniform mean |
| --- | --- | --- | --- | --- | --- |
| <800 | 2632 | 2.696 | 1.613 | 1.013 | 1.774 |
| 800-1199 | 4275 | 3.852 | 2.438 | 1.607 | 2.632 |
| 1200-1599 | 6559 | 4.885 | 3.141 | 2.173 | 3.399 |
| 1600-1999 | 8030 | 5.865 | 3.857 | 2.694 | 4.139 |
| 2000-2399 | 3963 | 6.619 | 4.414 | 3.139 | 4.724 |
| 2400+ | 939 | 9.532 | 6.559 | 4.840 | 6.977 |
| all | 26398 | 5.223 | 3.405 | 2.364 | 3.664 |

## Supply per user

**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times per-bucket sample rates at the chosen thresholds, after the 30% cap on pure misses. Rating groups approximate each game's exact Elo.

- Non-guest users with a fully evaluated game: 579
- Users under 50 usable blunder windows (need the similar-rating fallback): 43 of 579

| per user | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- |
| usable blunder windows | 68.8 | 225.5 | 927.0 | 1861.3 | 3982.0 |
| herring windows | 211.7 | 642.0 | 2814.6 | 7253.9 | 15397.1 |

## Provenance

Engine full evals against lichess `%eval` games (provenance = whether the game carries lichess evals). Rates, fit and supply are recomputed inside each provenance.

| provenance | games | blunders | usable blunders | hazard-weighted fit | herring windows per game | users | blunder windows p10 / p50 / p90 | users under 50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| engine | 23683 | 51908 | 34177 | 68.4% (n=34177) | 3.632 | 579 | 45.8 / 723.9 / 3730.1 | 64 of 579 |
| lichess | 2715 | 6039 | 3738 | 67.6% (n=3738) | 3.941 | 306 | 11.9 / 132.0 / 822.5 | 86 of 306 |

## Arrow oddness

Maia's probability of the move actually played, at the user's pinned Elo on the exact pre-move board (D-17). Good moves are a seeded sample of judged Good user moves (1500 per bucket requested, seed 248261108, 0 not scorable) with pre-move ES inside [0.10, 0.90]. Blunders are the usable ones at the chosen R, X' and band, with their stored played-move probability.

AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows wins without reading the position.

| Elo bucket | n Good | n blunder | Good prob q1 / median / q3 | blunder prob q1 / median / q3 | Good rank 1 | blunder rank 1 | AUC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 985 | 3890 | 0.138 / 0.298 / 0.533 | 0.029 / 0.084 / 0.195 | 55.8% | 16.9% | 0.776 |
| 800-1199 | 1100 | 6573 | 0.173 / 0.376 / 0.640 | 0.027 / 0.094 / 0.243 | 58.9% | 18.4% | 0.778 |
| 1200-1599 | 1200 | 9777 | 0.190 / 0.425 / 0.691 | 0.025 / 0.098 / 0.260 | 62.0% | 19.5% | 0.789 |
| 1600-1999 | 1271 | 11147 | 0.197 / 0.426 / 0.723 | 0.022 / 0.093 / 0.264 | 62.9% | 19.5% | 0.795 |
| 2000-2399 | 1285 | 5519 | 0.214 / 0.463 / 0.772 | 0.015 / 0.081 / 0.251 | 63.1% | 17.5% | 0.812 |
| 2400+ | 1362 | 1009 | 0.212 / 0.468 / 0.774 | 0.026 / 0.112 / 0.305 | 62.8% | 21.6% | 0.785 |
| all | 7203 | 37915 | 0.184 / 0.413 / 0.701 | 0.023 / 0.092 / 0.250 | 61.2% | 18.8% | 0.791 |

### Drill against the unselected baseline

The target is not AUC 0.5: blunders looking somewhat odd is a real signal the drill should train. The target is a drill AUC close to the unselected one, i.e. selection does not widen the real-game gap. Unselected = every scored Good move against every rated user-side blunder (no band, no findability); band only = both sides inside the eval band; drill = the table above. A clearly positive drill - unselected means flagging odd-looking arrows pays more in the drill than in games.

| Elo bucket | n Good (unselected) | n blunder (unselected) | AUC unselected | AUC band only | AUC drill | drill - unselected |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 1500 | 7027 | 0.755 | 0.761 | 0.776 | +0.021 |
| 800-1199 | 1500 | 10354 | 0.763 | 0.762 | 0.778 | +0.015 |
| 1200-1599 | 1500 | 14690 | 0.766 | 0.775 | 0.789 | +0.023 |
| 1600-1999 | 1500 | 16408 | 0.778 | 0.778 | 0.795 | +0.016 |
| 2000-2399 | 1500 | 7866 | 0.803 | 0.799 | 0.812 | +0.009 |
| 2400+ | 1500 | 1601 | 0.765 | 0.769 | 0.785 | +0.021 |
| all | 9000 | 57946 | 0.772 | 0.777 | 0.791 | +0.019 |

## Recommended constants

- Refutation threshold **R = 0.3** (allowed blunders).
- Best-move threshold **X' = 0.2** (pure misses).
- Eval band **[0.10, 0.90]** on the pre-move ES.

These are a recommendation only: nothing here is wired into app code, and the owner decides the final values. Re-render with other thresholds from the cache to compare.

### Rationale

- **R = 0.3 (not 0.2).** The face-palm intent is that a player of the blunderer's rating would find the punishment
  if they checked. Rank 1 alone already passes 69.2% of allowed blunders. R = 0.2 adds 11.4 points of refutations
  that are not Maia's top reply and that a player at that rating plays only one time in five. R = 0.3 adds 4.9 points
  (74.1% overall, 67.0% at <800). Supply does not bind: from the same cache, R = 0.2 gives a median of 986 usable
  blunder windows per user and R = 0.3 gives 927 (-6%). Users under 50 windows go from 42 to 43 of 579. The
  arrow-oddness gap barely moves (drill minus unselected AUC +0.018 at R = 0.2, +0.019 at R = 0.3).
- **X' = 0.2 (not 0.3).** Pure misses are capped at 30% of the blunder supply anyway, so a stricter X' buys little
  supply control. It does widen the oddness gap: R = X' = 0.3 gives +0.024 against +0.019. It also drops the pure-miss
  pass share from 61.9% to 52.6%, and finding a missed winning move is a harder task than seeing a reply that punishes
  you. The value is tuned toward the oddness gap and the face-palm intent, not toward a target supply.
- **Band [0.10, 0.90].** Outside it the game is already decided, so a blunder there barely changes the result. Near
  ES 0 or 1 the blunder threshold also stops meaning much. The band keeps 89.7% of findable blunders. It cuts herring
  windows from 4.81 to 3.66 per game. [0.15, 0.85] would keep only 81.6% and leave <800 with 1.37 herrings per game.
  The band does not widen the oddness gap: band-only AUC 0.777 against 0.772 unselected.
- **What the spot-check should look for:** whether the refutations at rank 1 with probability below 0.3 (they pass
  through the rank rule) are really obvious at <800 and 800-1199. Whether positional blunders (no capture, check or
  mate in the refutation, such as a pawn push that wins a piece only later) reach the low buckets. The deferred
  capture/check/mate fallback is NOT applied here, so such windows appear as drawn. Also whether pure misses at high
  pre-move ES (0.8 and above) read as fair questions.

Pass shares at these values (scored blunders only; the share in parentheses is the denominator) and the hazard-weighted share of usable blunders that fit a window:

| Elo bucket | allowed pass | pure miss pass | mixed pass | hazard-weighted window fit (usable blunders) |
| --- | --- | --- | --- | --- |
| <800 | 67.0% (n=3799) | 53.9% (n=1946) | 80.5% (n=1279) | 63.1% (n=3890) |
| 800-1199 | 72.7% (n=6070) | 59.4% (n=2527) | 88.2% (n=1744) | 65.8% (n=6573) |
| 1200-1599 | 75.1% (n=9144) | 62.3% (n=3336) | 87.6% (n=2185) | 68.2% (n=9777) |
| 1600-1999 | 75.6% (n=10511) | 64.4% (n=3657) | 88.9% (n=2216) | 69.9% (n=11147) |
| 2000-2399 | 77.3% (n=5093) | 69.4% (n=1694) | 91.6% (n=1068) | 71.2% (n=5519) |
| 2400+ | 69.4% (n=1024) | 60.5% (n=367) | 89.5% (n=209) | 73.8% (n=1009) |
| all | 74.1% (n=35641) | 61.9% (n=13527) | 87.6% (n=8701) | 68.4% (n=37915) |

Resulting supply per non-guest user (estimate): median 927.0 usable blunder windows and 2814.6 herring windows; 43 of 579 users are under 50 blunder windows.

Read the spot-check before choosing: `spot-check-2026-11-10.md`.

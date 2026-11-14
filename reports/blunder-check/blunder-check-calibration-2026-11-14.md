# Blunder-check calibration report

## How to read this report

- **Population:** fully evaluated games on chess.com, lichess (pasted and bot games are out). Database: `flawchess`. Run date: 2026-11-14.
- **Sampling:** deterministic, 25 permille (2.5%) of games chosen by md5 residue of the game id; the same sample on every re-run.
- **Expected score (ES):** every ES comes from the flaw classifier's own per-ply pass (`_run_all_moves_pass`), from the mover's point of view. Pre-move ES is the ES before the user's move, `ES_played` the ES after the blunder, `ES_ref` the user's ES before the opponent's previous move (what the user would have had without the gift).
- **Cases (D-13):** *allowed* = the blunder is not a miss (the opponent's previous move was not a mistake or blunder). *Pure miss* = a miss whose `ES_played` is at least `ES_ref` minus the inaccuracy drop: the user only gave back what the opponent gifted. *Mixed* = a miss that lost more than the gift. *Unclassified* = a miss without usable ES.
- **Facepalm score (250 D-01):** a ranking of how careless a blunder is at the mover's level, fitted on the owner's labels and stored on `game_flaws` from the played move's Maia probability, the opponent's reply spread and the material the stored engine line wins. It is not a probability and not a share of peers; a blunder qualifies when its score is at least the chosen threshold. A blunder without a score never qualifies; the Facepalm score section tells why.
- **Window mix (250 D-12):** every slot independently draws a herring (33%), an own blunder (33%) or a foreign blunder (33%); window length is uniform over 3 to 5 user moves for both kinds, a blunder's position follows the per-move hazard 0.265 within that length, 1 lead-in plies. Pure misses are capped at 30% of the blunder supply (report estimate only).
- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only aggregates times per-bucket sample rates, with rating groups approximating each game's exact Elo. It is an estimate, not an exact count.
- **Chosen values:** facepalm threshold = 0.7, eval band [0.10, 0.90]. These are a recommendation only; no constant is wired into app code by this report.
- Guest users' flaws are never Maia-scored, so guest games are excluded from every section except the sample counts.

## Sample

- Games sampled: 26654 (71 guest, excluded below)
- Games skipped for a ply gap: 52
- Unrated games (no rating at game time): 0 (0 user-side blunders not bucketed)
- User-side blunders (rated, non-guest): 58404

| Elo bucket | games (engine) | games (lichess) | blunders (engine) | blunders (lichess) |
| --- | --- | --- | --- | --- |
| <800 | 2599 | 74 | 6868 | 297 |
| 800-1199 | 3714 | 576 | 8906 | 1471 |
| 1200-1599 | 5962 | 695 | 13248 | 1671 |
| 1600-1999 | 7238 | 821 | 14773 | 1702 |
| 2000-2399 | 3557 | 408 | 7218 | 649 |
| 2400+ | 792 | 147 | 1340 | 261 |

## Control

Stored `game_flaws` (ply, severity) pairs against the mistakes and blunders recomputed from the per-ply evals (all sampled games, both colors; D-13).

- Agreement: 193089 of 193197 = 99.9% (n=193197)

## Cases by Elo bucket

| Elo bucket | blunders | allowed | pure_miss | mixed | unclassified | mixed / (pure miss + mixed) |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 7165 | 54.1% (n=7165) | 27.7% (n=7165) | 18.2% (n=7165) | 0.0% (n=7165) | 39.7% (n=3289) |
| 800-1199 | 10377 | 58.7% (n=10377) | 24.4% (n=10377) | 16.8% (n=10377) | 0.0% (n=10377) | 40.8% (n=4282) |
| 1200-1599 | 14919 | 62.4% (n=14919) | 22.7% (n=14919) | 14.9% (n=14919) | 0.0% (n=14919) | 39.6% (n=5613) |
| 1600-1999 | 16475 | 64.2% (n=16475) | 22.3% (n=16475) | 13.5% (n=16475) | 0.0% (n=16475) | 37.7% (n=5902) |
| 2000-2399 | 7867 | 64.8% (n=7867) | 21.6% (n=7867) | 13.6% (n=7867) | 0.0% (n=7867) | 38.6% (n=2767) |
| 2400+ | 1601 | 64.0% (n=1601) | 22.9% (n=1601) | 13.1% (n=1601) | 0.0% (n=1601) | 36.3% (n=576) |
| all | 58404 | 61.6% (n=58404) | 23.4% (n=58404) | 15.0% (n=58404) | 0.0% (n=58404) | 39.1% (n=22429) |

## Facepalm score

User-side blunders of rated, non-guest games and their stored facepalm score (250 D-01): a ranking of how careless the blunder is at the mover's level, not a share of peers. `scored` is the share with a score; the next four columns split the unscored ones by reason (shares of all user blunders): no reply spread yet, no stored engine line, a line shorter than 3 plies without an early mate (or one that cannot be replayed), and a missing played-move probability. The `pass` columns are shares of the scored blunders at or above each threshold; `qualifying of all` is the share of every user blunder that qualifies at the chosen threshold (an unscored blunder never qualifies).

| Elo bucket | user blunders | scored | no spread | no line | line too short | no played prob | pass >= 0.50 | pass >= 0.60 | pass >= 0.70 | pass >= 0.80 | qualifying of all (>= 0.70) | score q1 / median / q3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 7165 | 81.9% (n=7165) | 0.0% (n=7165) | 7.2% (n=7165) | 10.9% (n=7165) | 0.0% (n=7165) | 40.1% (n=5870) | 36.6% (n=5870) | 33.4% (n=5870) | 29.0% (n=5870) | 27.4% (n=7165) | 0.073 / 0.280 / 0.882 |
| 800-1199 | 10377 | 81.1% (n=10377) | 0.0% (n=10377) | 6.3% (n=10377) | 12.6% (n=10377) | 0.0% (n=10377) | 43.7% (n=8417) | 38.9% (n=8417) | 35.3% (n=8417) | 30.9% (n=8417) | 28.6% (n=10377) | 0.154 / 0.383 / 0.904 |
| 1200-1599 | 14919 | 80.0% (n=14919) | 0.0% (n=14919) | 6.0% (n=14919) | 14.0% (n=14919) | 0.0% (n=14919) | 43.7% (n=11930) | 38.9% (n=11930) | 34.3% (n=11930) | 30.0% (n=11930) | 27.4% (n=14919) | 0.168 / 0.398 / 0.892 |
| 1600-1999 | 16475 | 77.8% (n=16475) | 0.0% (n=16475) | 7.6% (n=16475) | 14.6% (n=16475) | 0.0% (n=16475) | 43.5% (n=12810) | 37.6% (n=12810) | 32.6% (n=12810) | 27.9% (n=12810) | 25.4% (n=16475) | 0.184 / 0.408 / 0.856 |
| 2000-2399 | 7867 | 79.0% (n=7867) | 0.0% (n=7867) | 6.2% (n=7867) | 14.8% (n=7867) | 0.0% (n=7867) | 45.6% (n=6212) | 38.9% (n=6212) | 32.9% (n=6212) | 27.7% (n=6212) | 26.0% (n=7867) | 0.203 / 0.442 / 0.852 |
| 2400+ | 1601 | 77.3% (n=1601) | 0.1% (n=1601) | 0.7% (n=1601) | 21.9% (n=1601) | 0.0% (n=1601) | 34.3% (n=1238) | 28.5% (n=1238) | 23.6% (n=1238) | 19.1% (n=1238) | 18.2% (n=1601) | 0.177 / 0.340 / 0.672 |
| all | 58404 | 79.6% (n=58404) | 0.0% (n=58404) | 6.5% (n=58404) | 13.9% (n=58404) | 0.0% (n=58404) | 43.2% (n=46477) | 38.0% (n=46477) | 33.4% (n=46477) | 28.9% (n=46477) | 26.6% (n=58404) | 0.164 / 0.392 / 0.874 |

## Eval band

Pre-move ES bounds (D-15), at the chosen facepalm threshold. First table: share of qualifying (facepalm) blunders whose pre-move ES is inside the band. Second table: disjoint herring windows per game, averaged uniformly over window lengths 3 to 5, with the band applied to every judged user move.

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 100.0% (n=1960) | 100.0% (n=2968) | 100.0% (n=4089) | 100.0% (n=4179) | 100.0% (n=2042) | 100.0% (n=292) | 100.0% (n=15530) |
| [0.05, 0.95] | 93.5% (n=1960) | 95.9% (n=2968) | 96.8% (n=4089) | 96.3% (n=4179) | 96.1% (n=2042) | 93.5% (n=292) | 95.9% (n=15530) |
| [0.10, 0.90] | 85.0% (n=1960) | 89.1% (n=2968) | 90.8% (n=4089) | 91.2% (n=4179) | 90.4% (n=2042) | 88.0% (n=292) | 89.7% (n=15530) |
| [0.15, 0.85] | 73.9% (n=1960) | 78.7% (n=2968) | 81.5% (n=4089) | 82.8% (n=4179) | 82.0% (n=2042) | 78.1% (n=292) | 80.4% (n=15530) |
| [0.20, 0.80] | 64.3% (n=1960) | 70.6% (n=2968) | 72.7% (n=4089) | 75.0% (n=4179) | 74.7% (n=2042) | 70.9% (n=292) | 72.1% (n=15530) |

| band | <800 | 800-1199 | 1200-1599 | 1600-1999 | 2000-2399 | 2400+ | all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [0.00, 1.00] | 3.304 (n=2673) | 3.979 (n=4290) | 4.543 (n=6657) | 5.124 (n=8059) | 5.797 (n=3965) | 7.803 (n=939) | 4.806 (n=26583) |
| [0.05, 0.95] | 2.324 (n=2673) | 3.168 (n=4290) | 3.906 (n=6657) | 4.579 (n=8059) | 5.161 (n=3965) | 7.306 (n=939) | 4.139 (n=26583) |
| [0.10, 0.90] | 1.786 (n=2673) | 2.633 (n=4290) | 3.406 (n=6657) | 4.137 (n=8059) | 4.723 (n=3965) | 6.977 (n=939) | 3.663 (n=26583) |
| [0.15, 0.85] | 1.376 (n=2673) | 2.114 (n=4290) | 2.861 (n=6657) | 3.615 (n=8059) | 4.218 (n=3965) | 6.499 (n=939) | 3.151 (n=26583) |
| [0.20, 0.80] | 1.115 (n=2673) | 1.790 (n=4290) | 2.466 (n=6657) | 3.197 (n=8059) | 3.779 (n=3965) | 6.017 (n=939) | 2.764 (n=26583) |

## Window fit

Share of usable blunders (facepalm and pre-move ES in band) whose k-1 preceding user moves are all Good and in band, for window positions 1 to 5 (D-16). The last column weights the positions with the blunder-window position weights below.

| Elo bucket | usable blunders | pos 1 | pos 2 | pos 3 | pos 4 | pos 5 | window-weighted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <800 | 1666 | 100.0% (n=1666) | 50.3% (n=1666) | 30.4% (n=1666) | 19.5% (n=1666) | 12.9% (n=1666) | 61.1% (n=1666) |
| 800-1199 | 2645 | 100.0% (n=2645) | 55.6% (n=2645) | 36.6% (n=2645) | 24.9% (n=2645) | 17.7% (n=2645) | 64.6% (n=2645) |
| 1200-1599 | 3711 | 100.0% (n=3711) | 59.9% (n=3711) | 40.3% (n=3711) | 28.7% (n=3711) | 21.7% (n=3711) | 67.0% (n=3711) |
| 1600-1999 | 3812 | 100.0% (n=3812) | 61.3% (n=3812) | 43.5% (n=3812) | 31.1% (n=3812) | 24.1% (n=3812) | 68.4% (n=3812) |
| 2000-2399 | 1845 | 100.0% (n=1845) | 63.2% (n=1845) | 45.0% (n=1845) | 33.2% (n=1845) | 25.3% (n=1845) | 69.5% (n=1845) |
| 2400+ | 257 | 100.0% (n=257) | 64.6% (n=257) | 47.1% (n=257) | 37.4% (n=257) | 29.2% (n=257) | 70.8% (n=257) |
| all | 13936 | 100.0% (n=13936) | 58.8% (n=13936) | 40.0% (n=13936) | 28.3% (n=13936) | 21.1% (n=13936) | 66.6% (n=13936) |

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
| <800 | 2673 | 2.711 | 1.624 | 1.022 | 1.786 |
| 800-1199 | 4290 | 3.853 | 2.439 | 1.607 | 2.633 |
| 1200-1599 | 6657 | 4.894 | 3.147 | 2.178 | 3.406 |
| 1600-1999 | 8059 | 5.863 | 3.856 | 2.693 | 4.137 |
| 2000-2399 | 3965 | 6.618 | 4.413 | 3.138 | 4.723 |
| 2400+ | 939 | 9.532 | 6.559 | 4.840 | 6.977 |
| all | 26583 | 5.221 | 3.404 | 2.363 | 3.663 |

## Supply by origin

### Own supply per user

**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times per-bucket sample rates at the chosen threshold, after the 30% cap on pure misses. Rating groups approximate each game's exact Elo.

- Non-guest users with a fully evaluated game: 583
- Users under 50 usable blunder windows (their own slots turn into foreign ones, 250 D-15): 95 of 583

| per user | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- |
| usable blunder windows | 26.6 | 89.3 | 343.1 | 664.8 | 1434.5 |
| herring windows | 212.8 | 642.3 | 2816.9 | 7261.3 | 15244.2 |

### Foreign supply per rating level

Qualifying blunders of other users whose mover's pinned Elo is within +-150 of the level (250 D-13: rating only, no widening). Counts are population estimates: the sample count times 1000 / 25 sample permille (non-guest games, so a run capped with `--limit-games` undercounts). A session takes at most one window per game, so the games column is the pool a foreign slot draws from. The rows below 800 and at 2400 and above are the extremes, where the pool is thinnest.

| level (pinned Elo) | mover Elo | qualifying blunders | usable (in band) | games with a qualifying blunder | sample n (qualifying) | note |
| --- | --- | --- | --- | --- | --- | --- |
| 600 | 450 to 750 | 75920 | 64400 | 50080 | 1898 | extreme: below 800 |
| 800 | 650 to 950 | 18360 | 16160 | 12920 | 459 |  |
| 1000 | 850 to 1150 | 90800 | 80360 | 60280 | 2270 |  |
| 1200 | 1050 to 1350 | 139640 | 125280 | 93440 | 3491 |  |
| 1400 | 1250 to 1550 | 123400 | 112320 | 87280 | 3085 |  |
| 1600 | 1450 to 1750 | 137200 | 124880 | 98200 | 3430 |  |
| 1800 | 1650 to 1950 | 119600 | 109640 | 88000 | 2990 |  |
| 2000 | 1850 to 2150 | 116160 | 105040 | 81640 | 2904 |  |
| 2200 | 2050 to 2350 | 63440 | 57560 | 45280 | 1586 |  |
| 2400 | 2250 to 2550 | 15440 | 13480 | 11160 | 386 | extreme: 2400 and above |
| 2600 | 2450 to 2750 | 10160 | 9200 | 8120 | 254 | extreme: 2400 and above |

## Provenance

Engine full evals against lichess `%eval` games (provenance = whether the game carries lichess evals). Rates, fit and supply are recomputed inside each provenance.

| provenance | games | blunders | usable blunders | window-weighted fit | herring windows per game | users | blunder windows p10 / p50 / p90 | users under 50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| engine | 23862 | 52353 | 12679 | 66.7% (n=12679) | 3.631 | 583 | 17.1 / 272.1 / 1351.3 | 120 of 583 |
| lichess | 2721 | 6051 | 1257 | 65.6% (n=1257) | 3.939 | 308 | 4.0 / 45.0 / 267.3 | 163 of 308 |

## Arrow oddness

Maia's probability of the move actually played, at the user's pinned Elo on the exact pre-move board (D-17). Good moves are a seeded sample of judged Good user moves (1500 per bucket requested, seed 248261108, 0 not scorable) with pre-move ES inside [0.10, 0.90]. Blunders are the usable ones at the chosen facepalm threshold and band, with their stored played-move probability.

AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows wins without reading the position.

| Elo bucket | n Good | n blunder | Good prob q1 / median / q3 | blunder prob q1 / median / q3 | AUC |
| --- | --- | --- | --- | --- | --- |
| <800 | 988 | 1666 | 0.138 / 0.301 / 0.534 | 0.019 / 0.056 / 0.141 | 0.827 |
| 800-1199 | 1103 | 2645 | 0.171 / 0.376 / 0.641 | 0.012 / 0.047 / 0.154 | 0.846 |
| 1200-1599 | 1208 | 3711 | 0.190 / 0.427 / 0.691 | 0.009 / 0.038 / 0.133 | 0.869 |
| 1600-1999 | 1275 | 3812 | 0.196 / 0.428 / 0.725 | 0.006 / 0.029 / 0.117 | 0.885 |
| 2000-2399 | 1286 | 1845 | 0.216 / 0.461 / 0.769 | 0.002 / 0.016 / 0.074 | 0.911 |
| 2400+ | 1363 | 257 | 0.214 / 0.467 / 0.777 | 0.003 / 0.023 / 0.129 | 0.884 |
| all | 7223 | 13936 | 0.184 / 0.414 / 0.701 | 0.008 / 0.035 / 0.126 | 0.872 |

### Drill against the unselected baseline

The target is not AUC 0.5: blunders looking somewhat odd is a real signal the drill should train. The target is a drill AUC close to the unselected one, i.e. selection does not widen the real-game gap. Unselected = every scored Good move against every rated user-side blunder (no band, no facepalm threshold); band only = both sides inside the eval band; drill = the table above. A clearly positive drill - unselected means flagging odd-looking arrows pays more in the drill than in games.

| Elo bucket | n Good (unselected) | n blunder (unselected) | AUC unselected | AUC band only | AUC drill | drill - unselected |
| --- | --- | --- | --- | --- | --- | --- |
| <800 | 1500 | 7165 | 0.755 | 0.760 | 0.827 | +0.072 |
| 800-1199 | 1500 | 10377 | 0.764 | 0.763 | 0.846 | +0.082 |
| 1200-1599 | 1500 | 14919 | 0.766 | 0.775 | 0.869 | +0.103 |
| 1600-1999 | 1500 | 16474 | 0.778 | 0.778 | 0.885 | +0.107 |
| 2000-2399 | 1500 | 7867 | 0.801 | 0.798 | 0.911 | +0.110 |
| 2400+ | 1500 | 1601 | 0.766 | 0.771 | 0.884 | +0.118 |
| all | 9000 | 58403 | 0.772 | 0.777 | 0.872 | +0.101 |

## Recommended constants

- Facepalm threshold **0.7** (a user blunder qualifies at or above it).
- Eval band **[0.10, 0.90]** on the pre-move ES.

These are a recommendation only: nothing here is wired into app code, and the owner decides the final values. Re-render with another `--facepalm-threshold` from the cache to compare.

Fair-share proxies per threshold (250 D-03: a false alarm is worse than a miss). The report cannot tell a fair position from an unfair one, so it prints what drives fairness among the passers: how rarely the move is played, how few replies the opponent has, and how often the stored line wins material or mates at once. The owner's labels (2026-11-13, decided labels with a stored line, cross-validated) measured fair among passers at >= 0.5: 80%, >= 0.7: 89%, >= 0.8: 92%. Judge precision on the spot-check, not on these columns alone.

| threshold | pass of scored | pass of all | median played prob | median reply spread | mate or >= 2 points down | median usable windows per user |
| --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 43.2% (n=46477) | 34.4% (n=58404) | 0.034 | 2.32 | 71.1% (n=20079) | 439.6 |
| 0.60 | 38.0% (n=46477) | 30.2% (n=58404) | 0.035 | 2.25 | 79.0% (n=17643) | 386.7 |
| 0.70 | 33.4% (n=46477) | 26.6% (n=58404) | 0.034 | 2.21 | 86.2% (n=15530) | 343.1 |
| 0.80 | 28.9% (n=46477) | 23.0% (n=58404) | 0.033 | 2.15 | 92.8% (n=13417) | 296.5 |

Window-weighted share of usable blunders (qualifying and in band) that fit a window, at the chosen threshold:

| Elo bucket | window fit (usable blunders) |
| --- | --- |
| <800 | 61.1% (n=1666) |
| 800-1199 | 64.6% (n=2645) |
| 1200-1599 | 67.0% (n=3711) |
| 1600-1999 | 68.4% (n=3812) |
| 2000-2399 | 69.5% (n=1845) |
| 2400+ | 70.8% (n=257) |
| all | 66.6% (n=13936) |

Resulting supply per non-guest user (estimate): median 343.1 usable blunder windows and 2816.9 herring windows; 95 of 583 users are under 50 blunder windows.

Read the spot-check before choosing: `spot-check-2026-11-14.md`.

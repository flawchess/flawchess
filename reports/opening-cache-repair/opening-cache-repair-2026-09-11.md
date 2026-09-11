# Opening Cache Repair Report -- 2026-09-11

## 1. Cache status breakdown

| Status | Count |
|---|---|
| `screened_clean` | 2,192,195 |
| `flagged` | 0 |
| `confirmed_bad` | 0 |
| `confirmed_clean` | 19,576 |
| `orphan` | 352,058 |
| `hash_mismatch` | 0 |
| `repaired` | 4,097 |
| `pending`, no carrier (orphan candidate) | 0 |
| `pending`, has a carrier (walk cut short) | 17 |

`confirmed_bad` `delta_cp` histogram (old vs new, absolute value):

| abs(delta_cp) band | count |
|---|---|
| < 25 | 0 |
| 25-50 | 984 |
| 50-75 | 1,025 |
| 75-100 | 490 |
| 100-150 | 459 |
| 150-250 | 629 |
| 250-400 | 359 |
| > 400 | 46 |

## 2. Top-30 `confirmed_bad` positions by carrier count

| full_hash | carriers | old_cp | full_cp | delta_cp | SAN |
|---|---|---|---|---|---|
| -6220177258839681435 | 1,573 | 286 | 69 | -217 | Nc6 |
| -7106566961782875842 | 946 | 297 | 165 | -132 | d3 |
| -991146174231080759 | 577 | 100 | 19 | -81 | h6 |
| 3250950765068847520 | 482 | 295 | 49 | -246 | Nf3 |
| 1214201490189011761 | 423 | 249 | 48 | -201 | h3 |
| -4495720059219567338 | 308 | 285 | 37 | -248 | Bg2 |
| -3185735734450884963 | 308 | 305 | 10 | -295 | e3 |
| -1357424544074167494 | 297 | 300 | 85 | -215 | Nf3 |
| 574942073556743879 | 284 | 190 | -15 | -205 | Nxe5 |
| 3912952322572315143 | 250 | 349 | 67 | -282 | e5 |
| -3692655065124884866 | 242 | 302 | 88 | -214 | Nh6 |
| 4072888212560887267 | 237 | 210 | 28 | -182 | O-O |
| -2000867256950660935 | 225 | 273 | 85 | -188 | a6 |
| 6991966663941067682 | 206 | 251 | 80 | -171 | cxd4 |
| 9181538511791674715 | 199 | 84 | -58 | -142 | Nc6 |
| 4938055159587074233 | 185 | 140 | 35 | -105 | Bb5 |
| -4230257548248121256 | 164 | 313 | 12 | -301 | Nc6 |
| 3510599443288803854 | 163 | 220 | 20 | -200 | g6 |
| -2498954526234361735 | 156 | 273 | 15 | -258 | Nxd5 |
| 1801382059975634489 | 154 | 162 | -7 | -169 | Be2 |
| 2615602418204527596 | 151 | 147 | -101 | -248 | g4 |
| -5152573670152244927 | 136 | 253 | 37 | -216 | d3 |
| 5714073271189725302 | 126 | 294 | 28 | -266 | Bd7 |
| -7808647004259071715 | 116 | 86 | -41 | -127 | Nc6 |
| -532503293522657476 | 116 | 197 | -1 | -198 | Bd2 |
| -3769548642638684502 | 115 | 397 | 48 | -349 | c5 |
| -9161614690978448826 | 113 | 377 | -7 | -384 | Be3 |
| -6827947244991875697 | 111 | 262 | 33 | -229 | c3 |
| -1682583370636440283 | 109 | 322 | 48 | -274 | Nxd5 |
| 2598890695611671221 | 109 | 163 | 41 | -122 | Qf6 |

## 3. Positions rewritten

- Total `game_positions` cells rewritten: 11,286
- Also had `best_move` replaced: 11,273
- Also had `pv` replaced (expected near-zero -- see Pitfall 5): 4,246

| ply | rows repaired |
|---|---|
| 0 | 5 |
| 1 | 32 |
| 2 | 42 |
| 3 | 168 |
| 4 | 541 |
| 5 | 1,137 |
| 6 | 829 |
| 7 | 1,172 |
| 8 | 735 |
| 9 | 669 |
| 10 | 1,451 |
| 11 | 646 |
| 12 | 572 |
| 13 | 539 |
| 14 | 420 |
| 15 | 435 |
| 16 | 434 |
| 17 | 508 |
| 18 | 432 |
| 19 | 519 |

## 4. Games affected

By platform:

| platform | games |
|---|---|
| chess.com | 9,384 |
| flawchess | 13 |
| lichess | 3,963 |

By user id (top 20, numeric only):

| user_id | games |
|---|---|
| 95 | 917 |
| 11 | 810 |
| 20 | 354 |
| 602 | 307 |
| 590 | 271 |
| 10 | 256 |
| 199 | 256 |
| 288 | 247 |
| 107 | 245 |
| 423 | 224 |
| 109 | 202 |
| 449 | 197 |
| 397 | 196 |
| 2 | 191 |
| 21 | 182 |
| 194 | 170 |
| 331 | 165 |
| 99 | 163 |
| 327 | 163 |
| 66 | 161 |

Distinct users with at least one affected game: 284

Per-game rows-repaired distribution:

| rows repaired | games |
|---|---|
| < 1 | 3,289 |
| 1-2 | 9,202 |
| 2-5 | 850 |
| 5-10 | 17 |
| 10-20 | 1 |
| > 20 | 1 |

## 5. Flaws

- Mistakes: 38,686 -> 38,683
- Blunders: 67,339 -> 60,741
- Spurious flaws removed: 7,191
- Flaws added: 590
- Games whose blunder count changed: 4,079
- `drill_items` pruned: 5
- `herring_pool` rows touched (counter only, never deleted): 2
- Mean accuracy shift (after - before, both colors): +0.725
- Mean ACPL shift (after - before, both colors): -2.57

## 6. Provenance leaks closed

Plan 220-02 stopped the full-eval drain tick from donating a lichess-eval game's opening plies to the cache, and gave the `OPENING_CACHE_BACKFILL_SQL` backfill a deterministic donor order (newest `full_evals_completed_at`, pv-bearing tiebreak) -- both were part of why the cache was poisoned in the first place.

## 7. Verification block

### Lichess cross-check

- Observed: n_checked=25,610, n_bad=19
- 2026-09-09 baseline: n_checked=25,444, n_bad=87

### Delta histogram vs lichess-internal IQR control (**PRIMARY ACCEPTANCE SIGNAL** -- every band above the noise floor must match the control after repair)

| abs(delta) band | observed n_cache | observed n_ctrl | baseline n_cache | baseline n_ctrl |
|---|---|---|---|---|
| < 25 | 22,193 | 24,156 | 21,987 | 24,000 |
| 25-50 | 3,107 | 1,143 | 3,064 | 1,132 |
| 50-75 | 207 | 182 | 203 | 183 |
| 75-100 | 47 | 65 | 52 | 66 |
| 100-150 | 36 | 38 | 49 | 37 |
| 150-250 | 14 | 20 | 50 | 20 |
| 250-400 | 2 | 6 | 35 | 6 |
| > 400 | 4 | 0 | 4 | 0 |

### Opening bounce rate (coarse sanity check only -- cannot pass/fail the repair on its own)

- Observed: 0.62% any bounce (62,404/10,075,456), 0.22% in the 250-360cp band (22,569/10,075,456; 124,323 drops in band)
- Baseline: benchmark DB (cache-free) 0.618% / 0.235%; prod legacy 0.798% / 0.298%; mid 0.625% / 0.243%; recent 0.844% / 0.271%

### Calibration

- screen_floor=0.04107753187417984, confirm_floor=0.029419321566820145, calibration_n=500, calibrated_at=2026-09-10 11:47:37.843529+00:00, engine_version=Stockfish 18

### Acceptance fixture: game 2356581 and the 9 named hashes

- `game_positions.eval_cp` at plies 4/5/6: ply 4=9, ply 5=10, ply 6=12
- `game_flaws` rows at plies 5/6: none
- `white_blunders`=0, `black_blunders`=1

| full_hash | observed status |
|---|---|
| 3250950765068847520 | repaired |
| -1357424544074167494 | repaired |
| 3912952322572315143 | repaired |
| -4495720059219567338 | repaired |
| -3692655065124884866 | repaired |
| 6991966663941067682 | repaired |
| -4230257548248121256 | repaired |
| -7106566961782875842 | repaired |
| -3185735734450884963 | repaired |

## 8. Per-stage timings

| stage | started | finished | elapsed |
|---|---|---|---|
| seed | 2026-09-10 11:36:17.034657+00:00 | 2026-09-10 11:37:16.014273+00:00 | 0:00:58.979616 |
| calibrate | 2026-09-10 11:47:37.843529+00:00 | 2026-09-10 11:47:37.959102+00:00 | 0:00:00.115573 |
| screen | 2026-09-10 11:48:03.233696+00:00 | 2026-09-10 22:36:03.112837+00:00 | 10:47:59.879141 |
| orphans | (not tracked -- one-shot action) | | |
| confirm | 2026-09-11 05:29:05.832195+00:00 | 2026-09-11 06:21:48.564435+00:00 | 0:52:42.732240 |
| propagate | 2026-09-11 11:47:05.527554+00:00 | 2026-09-11 11:54:09.452028+00:00 | 0:07:03.924474 |
| rederive | 2026-09-11 11:54:43.245726+00:00 | 2026-09-11 13:15:35.918471+00:00 | 1:20:52.672745 |

## Provenance

- DB target: `prod`
- Report generated: 2026-09-11T13:15:51.412207+00:00
- Script revision: 36e05d890
- engine_version: Stockfish 18
- Band-rate line hand-corrected after generation: the writer at 36e05d890 divided the band count by the band's own drops (printed 18.15%); the baselines are over all checked rows, and the writer was fixed in the same commit as this report.

legacy-sample: D-07 decision
- legacy cohort: 200 games, 3862 rows ply<=20 (17 disagree), 9164 rows ply>20 (965 disagree, 10.53%)
- control cohort: 50 games, 930 rows ply<=20 (6 disagree), 1949 rows ply>20 (176 disagree, 9.03%)
- rule: build only when legacy_rate_ply_gt_20 > LEGACY_BUILD_RATIO * control_rate_ply_gt_20 AND (legacy_rate - control_rate) >= LEGACY_BUILD_MIN_EXCESS_PP
LEGACY-COHORT-DECISION: NO BUILD

## 3b. Gem/Great candidates (`game_best_moves`) re-based on the repaired evals

- Candidate rows whose `best_cp`/`best_mate` still held the old value: 1,617 (rewritten to the repaired value)
- Of those, deleted because the corrected margin fails the inaccuracy gate: 828
- Kept as candidates with the corrected margin: 789

# Opening Cache Repair Report -- 2026-09-10

## 1. Cache status breakdown

| Status | Count |
|---|---|
| `screened_clean` | 81,035 |
| `flagged` | 0 |
| `confirmed_bad` | 0 |
| `confirmed_clean` | 1,256 |
| `orphan` | 24,029 |
| `hash_mismatch` | 0 |
| `repaired` | 295 |
| `pending`, no carrier (orphan candidate) | 0 |
| `pending`, has a carrier (walk cut short) | 0 |

`confirmed_bad` `delta_cp` histogram (old vs new, absolute value):

| abs(delta_cp) band | count |
|---|---|
| < 25 | 43 |
| 25-50 | 201 |
| 50-75 | 38 |
| 75-100 | 8 |
| 100-150 | 3 |
| 150-250 | 1 |
| 250-400 | 1 |
| > 400 | 0 |

## 2. Top-30 `confirmed_bad` positions by carrier count

| full_hash | carriers | old_cp | full_cp | delta_cp | SAN |
|---|---|---|---|---|---|
| -3442634682380147568 | 39 | 42 | 13 | -29 | e5 |
| 4151662473666090382 | 33 | 29 | 52 | 23 | Ba4 |
| 451036920692017563 | 31 | 63 | 37 | -26 | Bd7 |
| 7280368029776998112 | 31 | -9 | -38 | -29 | Nf6 |
| -4167569880526364092 | 30 | 119 | 75 | -44 | d3 |
| -7821175689596293839 | 27 | -10 | -36 | -26 | Nd2 |
| 8243690459637094902 | 25 | -29 | -7 | 22 | Be3 |
| -2126439475507043995 | 21 | 112 | 69 | -43 | Nf6 |
| -8527635082274156105 | 19 | -12 | -33 | -21 | Ne4 |
| -3305573587224046146 | 17 | -459 | -414 | 45 | Qh4+ |
| -5873698463198770057 | 14 | 94 | 46 | -48 | d4 |
| 4526132316301342152 | 14 | -15 | 7 | 22 | Nf1 |
| -8356722372452487549 | 12 | -1 | 22 | 23 | Nbd2 |
| 2213914215225274256 | 12 | 75 | 47 | -28 | g3 |
| -7805076664781277389 | 11 | 39 | 5 | -34 | b6 |
| -5074595370542915341 | 11 | 112 | 78 | -34 | c3 |
| 7969908471245630166 | 10 | 123 | 169 | 46 | Bb3 |
| -8777017930113593206 | 8 | 13 | -19 | -32 | Bb2 |
| 2804601047181129661 | 8 | 314 | 280 | -34 | Qd7 |
| 7682867953971618590 | 8 | -27 | 39 | 66 | a3 |
| -7853557767014076936 | 7 | -14 | 10 | 24 | bxc6 |
| -6611155931150045361 | 7 | 235 | 194 | -41 | f5 |
| -5763242947228690395 | 7 | 302 | 266 | -36 | dxc5 |
| -4384443703847234698 | 7 | -398 | -355 | 43 | Bxb4 |
| -4228078731196434546 | 7 | 236 | 202 | -34 | g4 |
| -3289279060225024716 | 7 | 315 | 282 | -33 | Nf5 |
| -1395110011093622611 | 7 | -28 | 6 | 34 | Nc6 |
| -982380087286319549 | 7 | 360 | 304 | -56 | O-O |
| -362491348022634205 | 7 | 295 | 325 | 30 | dxe4 |
| 749350881594121044 | 7 | -356 | -313 | 43 | Bb4 |

## 3. Positions rewritten

- Total `game_positions` cells rewritten: 267
- Also had `best_move` replaced: 266
- Also had `pv` replaced (expected near-zero -- see Pitfall 5): 168

| ply | rows repaired |
|---|---|
| 3 | 3 |
| 4 | 1 |
| 5 | 7 |
| 6 | 7 |
| 7 | 7 |
| 8 | 3 |
| 9 | 10 |
| 10 | 10 |
| 11 | 15 |
| 12 | 9 |
| 13 | 10 |
| 14 | 15 |
| 15 | 29 |
| 16 | 28 |
| 17 | 24 |
| 18 | 43 |
| 19 | 46 |

## 4. Games affected

By platform:

| platform | games |
|---|---|
| chess.com | 465 |
| lichess | 62 |

By user id (top 20, numeric only):

| user_id | games |
|---|---|
| 28 | 88 |
| 8 | 72 |
| 2 | 69 |
| 7 | 69 |
| 14 | 45 |
| 31 | 41 |
| 46 | 33 |
| 47 | 31 |
| 33 | 26 |
| 60 | 12 |
| 13 | 8 |
| 59 | 5 |
| 67 | 5 |
| 68 | 5 |
| 69 | 5 |
| 70 | 5 |
| 71 | 5 |
| 15 | 3 |

Distinct users with at least one affected game: 18

Per-game rows-repaired distribution:

| rows repaired | games |
|---|---|
| < 1 | 280 |
| 1-2 | 228 |
| 2-5 | 19 |
| 5-10 | 0 |
| 10-20 | 0 |
| > 20 | 0 |

## 5. Flaws

- Mistakes: 863 -> 853
- Blunders: 1,158 -> 1,153
- Spurious flaws removed: 29
- Flaws added: 14
- Games whose blunder count changed: 19
- `drill_items` pruned: 0
- `herring_pool` rows touched (counter only, never deleted): 0
- Mean accuracy shift (after - before, both colors): +0.134
- Mean ACPL shift (after - before, both colors): -0.27

## 6. Provenance leaks closed

Plan 220-02 stopped the full-eval drain tick from donating a lichess-eval game's opening plies to the cache, and gave the `OPENING_CACHE_BACKFILL_SQL` backfill a deterministic donor order (newest `full_evals_completed_at`, pv-bearing tiebreak) -- both were part of why the cache was poisoned in the first place.

## 7. Verification block

### Lichess cross-check

- Observed: n_checked=2,137, n_bad=0
- 2026-09-09 baseline: n_checked=25,444, n_bad=87

### Delta histogram vs lichess-internal IQR control (**PRIMARY ACCEPTANCE SIGNAL** -- every band above the noise floor must match the control after repair)

| abs(delta) band | observed n_cache | observed n_ctrl | baseline n_cache | baseline n_ctrl |
|---|---|---|---|---|
| < 25 | 1,848 | 2,067 | 21,987 | 24,000 |
| 25-50 | 275 | 67 | 3,064 | 1,132 |
| 50-75 | 13 | 3 | 203 | 183 |
| 75-100 | 1 | 0 | 52 | 66 |
| 100-150 | 0 | 0 | 49 | 37 |
| 150-250 | 0 | 0 | 50 | 20 |
| 250-400 | 0 | 0 | 35 | 6 |
| > 400 | 0 | 0 | 4 | 0 |

### Opening bounce rate (coarse sanity check only -- cannot pass/fail the repair on its own)

- Observed: 0.43% any bounce (443/103,196), 18.33% in the 250-360cp band (169/922)
- Baseline: benchmark DB (cache-free) 0.618% / 0.235%; prod legacy 0.798% / 0.298%; mid 0.625% / 0.243%; recent 0.844% / 0.271%

### Calibration

- screen_floor=0.032318875193595886, confirm_floor=0.01894477941095829, calibration_n=50, calibrated_at=2026-09-10 04:40:20.412679+00:00, engine_version=Stockfish 18

### Acceptance fixture: game 2356581 and the 9 named hashes

Game 2356581 not present in this database.

| full_hash | observed status |
|---|---|
| 3250950765068847520 | screened_clean |
| -1357424544074167494 | screened_clean |
| 3912952322572315143 | screened_clean |
| -4495720059219567338 | screened_clean |
| -3692655065124884866 | not seeded |
| 6991966663941067682 | screened_clean |
| -4230257548248121256 | not seeded |
| -7106566961782875842 | screened_clean |
| -3185735734450884963 | screened_clean |

## 8. Per-stage timings

| stage | started | finished | elapsed |
|---|---|---|---|
| seed | 2026-09-10 04:52:20.598791+00:00 | 2026-09-10 04:52:21.997184+00:00 | 0:00:01.398393 |
| calibrate | 2026-09-10 04:40:20.412679+00:00 | 2026-09-10 04:40:20.415878+00:00 | 0:00:00.003199 |
| screen | 2026-09-10 05:47:56.892039+00:00 | 2026-09-10 06:00:19.367115+00:00 | 0:12:22.475076 |
| orphans | (not tracked -- one-shot action) | | |
| confirm | 2026-09-10 06:01:27.802076+00:00 | 2026-09-10 06:06:56.627333+00:00 | 0:05:28.825257 |
| propagate | 2026-09-10 06:07:34.638896+00:00 | 2026-09-10 06:07:41.712787+00:00 | 0:00:07.073891 |
| rederive | 2026-09-10 06:08:13.165408+00:00 | 2026-09-10 06:08:32.454306+00:00 | 0:00:19.288898 |

## Provenance

- DB target: `dev`
- Report generated: 2026-09-10T06:16:49.691533+00:00
- Script revision: 0d0854104
- engine_version: Stockfish 18

legacy-sample: D-07 decision
- legacy cohort: 200 games, 3791 rows ply<=20 (48 disagree), 7901 rows ply>20 (1132 disagree, 14.33%)
- control cohort: 7 games, 140 rows ply<=20 (1 disagree), 259 rows ply>20 (33 disagree, 12.74%)
- rule: build only when legacy_rate_ply_gt_20 > LEGACY_BUILD_RATIO * control_rate_ply_gt_20 AND (legacy_rate - control_rate) >= LEGACY_BUILD_MIN_EXCESS_PP
LEGACY-COHORT-DECISION: NO BUILD

# Opening Cache Repair Report -- 2026-09-09

## 1. Cache status breakdown

| Status | Count |
|---|---|
| `screened_clean` | 0 |
| `flagged` | 0 |
| `confirmed_bad` | 0 |
| `confirmed_clean` | 0 |
| `orphan` | 0 |
| `hash_mismatch` | 0 |
| `repaired` | 0 |
| `pending`, no carrier (orphan candidate) | 0 |
| `pending`, has a carrier (walk cut short) | 0 |

`confirmed_bad` `delta_cp` histogram (old vs new, absolute value):

| abs(delta_cp) band | count |
|---|---|
| < 25 | 0 |
| 25-50 | 0 |
| 50-75 | 0 |
| 75-100 | 0 |
| 100-150 | 0 |
| 150-250 | 0 |
| 250-400 | 0 |
| > 400 | 0 |

## 2. Top-30 `confirmed_bad` positions by carrier count

No `confirmed_bad` rows.

## 3. Positions rewritten

- Total `game_positions` cells rewritten: 0
- Also had `best_move` replaced: 0
- Also had `pv` replaced (expected near-zero -- see Pitfall 5): 0

| ply | rows repaired |
|---|---|

## 4. Games affected

By platform:

| platform | games |
|---|---|

By user id (top 20, numeric only):

| user_id | games |
|---|---|

Distinct users with at least one affected game: 0

Per-game rows-repaired distribution:

| rows repaired | games |
|---|---|
| < 1 | 0 |
| 1-2 | 0 |
| 2-5 | 0 |
| 5-10 | 0 |
| 10-20 | 0 |
| > 20 | 0 |

## 5. Flaws

- Mistakes: 0 -> 0
- Blunders: 0 -> 0
- Spurious flaws removed: 0
- Flaws added: 0
- Games whose blunder count changed: 0
- `drill_items` pruned: 0
- `herring_pool` rows touched (counter only, never deleted): 0
- Mean accuracy shift (after - before, both colors): n/a
- Mean ACPL shift (after - before, both colors): n/a

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

- Observed: 0.43% any bounce (443/103,196), 18.49% in the 250-360cp band (171/925)
- Baseline: benchmark DB (cache-free) 0.618% / 0.235%; prod legacy 0.798% / 0.298%; mid 0.625% / 0.243%; recent 0.844% / 0.271%

### Calibration

- screen_floor=None, confirm_floor=None, calibration_n=None, calibrated_at=None, engine_version=None

### Acceptance fixture: game 2356581 and the 9 named hashes

Game 2356581 not present in this database.

| full_hash | observed status |
|---|---|
| 3250950765068847520 | not seeded |
| -1357424544074167494 | not seeded |
| 3912952322572315143 | not seeded |
| -4495720059219567338 | not seeded |
| -3692655065124884866 | not seeded |
| 6991966663941067682 | not seeded |
| -4230257548248121256 | not seeded |
| -7106566961782875842 | not seeded |
| -3185735734450884963 | not seeded |

## 8. Per-stage timings

| stage | started | finished | elapsed |
|---|---|---|---|
| seed | - | - | - |
| calibrate | - | - | - |
| screen | - | - | - |
| orphans | (not tracked -- one-shot action) | | |
| confirm | - | - | - |
| propagate | - | - | - |
| rederive | - | - | - |

## Provenance

- DB target: `dev`
- Report generated: 2026-09-09T22:47:18.441845+00:00
- Script revision: 73dc7dcb5
- engine_version: unknown

# FlawChess Benchmarks — 2026-05-27

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-27 (cohort doubled vs the 2026-05-24 snapshot — selection target raised from 100/cell to 200/cell)
- **Population**: 4,697 users / 2,767,158 games / 190,934,222 positions
- **Cell anchoring**: 400-wide ELO buckets via the cohort user's **rating at game time** (`games.white_rating`/`games.black_rating`, sub-800 dropped) — NOT `benchmark_selected_users.rating_bucket`; `tc_bucket` from `benchmark_selected_users`; per-user TC restricted to selected `tc_bucket`. Methodology change (2026-05-19): rating-at-game-time bucketing.
- **Selection provenance**: 2026-03 Lichess monthly dump. Cohort selection target was 200 users/cell (was 100 in earlier snapshots); 18 of 20 cells fill the target. `(800, classical)` and `(2400, classical)` remain pool-limited.
- **Per-user history caveat**: each user contributes up to 1000 games per TC over a 36-month window at varying ratings, so a user spans 2–3 game-time ELO buckets. `benchmark_selected_users.rating_bucket` / `median_elo` are retained as longitudinal/trajectory columns only. Any whole-career per-user scalar is now per-bucket/trajectory.
- **Base filters**: `g.rated AND NOT g.is_computer_game`; `g.time_control_bucket::text = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter).
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating - user_rating) <= 100`. Applied to every per-game CTE in Chapters 2 and 3. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (REFAC-02). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate forces conv/recov; NULL → parity).
- **Eval coverage**: 100.00% of qualifying endgame entries have non-NULL eval (1,538,581 / 1,538,585). NULL routing to parity is a non-issue.
- **Sparse-cell exclusion**: `(2400, classical)` is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~4 games/user, pool exhausted). Shown in cell-level 5×4 tables with `n=12*` footnote.
- **Deleted calibration targets** (no longer in scope — retracted in Phase 87.4):
  - `endgame_skill` (composite — §3.2.1 still reports per-user distribution for completeness, but no band recommendation)
  - `section2_score_gap_skill` (composite — §3.2.2 reports only conv/parity/recov)
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate.

## 1. Stratified Sample

### Selection-pool coverage (`status='completed'` users per cell)

5×4 cell membership at selection-snapshot bucketing (this is the candidate pool used to seed game-time analysis; see "Game-time cell sizes" below for the analysis-axis cells).

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 200 | 200 | 200 | 151 |
| 1200 | 200 | 200 | 200 | 200 |
| 1600 | 200 | 200 | 200 | 200 |
| 2000 | 200 | 200 | 200 | 200 |
| 2400 | 200 | 200 | 200 | 12* |

\* sparse cell, pool-exhausted (12 completed / 23-candidate pool — every other candidate was `skipped` (8) or `failed` (3)). Excluded from marginals.

### Selection-pool status breakdown (audit trail)

| ELO \ TC | bullet C / S / F / U | blitz | rapid | classical |
|---|---|---|---|---|
| 800 | 200 / 14 / 2 / 284 | 200 / 18 / 3 / 279 | 200 / 47 / 10 / 243 | 151 / 340 / 9 / 0 |
| 1200 | 200 / 3 / 2 / 295 | 200 / 21 / 4 / 275 | 200 / 29 / 8 / 263 | 200 / 248 / 10 / 42 |
| 1600 | 200 / 3 / 1 / 296 | 200 / 5 / 8 / 287 | 200 / 30 / 11 / 259 | 200 / 156 / 16 / 128 |
| 2000 | 200 / 2 / 3 / 295 | 200 / 5 / 4 / 291 | 200 / 31 / 17 / 252 | 200 / 211 / 29 / 60 |
| 2400 | 200 / 4 / 14 / 282 | 200 / 4 / 16 / 280 | 200 / 52 / 23 / 225 | 12 / 8 / 3 / 0 |

C = completed, S = skipped (yield < `--min-games`), F = failed (404/error), U = unattempted (pool reserve).

- `(800, classical)` is pool-limited: 0 unattempted, 340 skipped users with no rapid/classical eval-bearing games or < 100 imported. Stage-1 selection would need to widen below the eval-bearing-floor to extend the pool further.
- `(2400, classical)` is pool-exhausted: 23 candidates, 12 completed. Same widening conclusion applies.

### Eval coverage at endgame entry

| metric | value |
|---|---:|
| Endgame-reaching games (≥6 plies, `endgame_class IS NOT NULL`) | 1,538,585 |
| With non-NULL Stockfish eval at entry ply | 1,538,581 |
| Coverage | **100.00%** |

NULL-eval routing to `parity` is a non-issue. Backfill via `backfill_eval.py --db benchmark` ran clean.

### Game-time cell sizes (post equal-footing filter)

A user spans 2–3 game-time ELO buckets across their 36-month history. These are the cells the analysis actually pools over after `abs(opp_rating − user_rating) ≤ 100` is applied. All non-sparse cells clear the ≥10-users-per-cell Cohen's d floor with very wide margins.

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 268 / 114,933 | 260 / 115,661 | 317 / 95,792 | 222 / 11,609 |
| 1200 | 404 / 165,994 | 423 / 162,443 | 545 / 132,196 | 452 / 39,705 |
| 1600 | 363 / 165,589 | 419 / 164,380 | 502 / 134,570 | 423 / 48,763 |
| 2000 | 334 / 147,313 | 364 / 140,587 | 399 / 97,751 | 222 / 17,766 |
| 2400 | 240 / 113,012 | 223 / 89,885 | 208 / 31,627 | 10 / 47* |

Format: users / games. The sparse `(2400, classical)` game-time cell now holds 10 users / 47 games and stays excluded.

## 2. Openings

### 2.1 Middlegame-entry eval

#### Currently set in code

| Constant | File | Live value |
|---|---|---:|
| `EVAL_NEUTRAL_MIN/MAX_PAWNS` | `frontend/src/lib/openingStatsZones.ts` | `±0.30` pawns |
| `EVAL_BULLET_DOMAIN_PAWNS` | same | `1.5` pawns |
| `EVAL_BASELINE_PAWNS_WHITE / _BLACK` | `app/services/opening_insights_constants.py` | `+0.25 / -0.25` pawns (symmetric) |
| `EVAL_CONFIDENCE_MIN_N` | same | `20` games |

#### Pass 1 — symmetric engine baseline (deduped to physical games)

| n_games | baseline_cp_white | median_white_pov | sd_white_pov |
|---:|---:|---:|---:|
| 2,504,885 | **+25.21** | +24.0 | 237.2 |

White baseline +25 cp. Symmetric by construction: `EVAL_BASELINE_CP_BLACK = −25`. Matches the live `EVAL_BASELINE_PAWNS_WHITE = 0.25` exactly — no update needed.

#### Pass 2 — centered per-(user, color) pooled distribution

Centering: `delta = signed_user_pov_cp − (+25 if white else −25)`. Sample floor ≥20 games/user/color.

##### Pooled centered distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 9,109 | +3.7 cp | 58.5 cp | −92 cp | −23 cp | +6 cp | +34 cp | +89 cp |

##### ELO marginal (centered)

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 1,541 | −0.8 | 87.9 | −145 | −46 | +8 | +57 | +127 |
| 1200 | 2,140 | +5.7 | 69.3 | −104 | −32 | +10 | +48 | +106 |
| 1600 | 2,290 | +5.0 | 49.6 | −75 | −21 | +7 | +34 | +79 |
| 2000 | 1,988 | +4.4 | 35.2 | −53 | −15 | +5 | +26 | +59 |
| 2400 | 1,150 | +2.0 | 27.5 | −46 | −13 | +3 | +19 | +45 |

Per-user-mean SD compresses from 88 cp (800) → 28 cp (2400) — stronger players have lower across-game eval variance at MG entry, as expected.

##### TC marginal (centered)

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 2,674 | −2.5 | 71.7 | −126 | −31 | +4 | +37 | +95 |
| blitz | 2,665 | +2.9 | 45.1 | −75 | −20 | +3 | +28 | +73 |
| rapid | 2,628 | +8.5 | 50.3 | −76 | −17 | +9 | +35 | +89 |
| classical | 1,142 | +8.8 | 67.2 | −96 | −25 | +9 | +46 | +113 |

#### Collapse verdict

- **TC axis**: max |d| = **0.18** (bullet vs rapid) → **collapse**
- **ELO axis**: max |d| = **0.09** (800 vs 1200) → **collapse**

Both axes collapse cleanly. Color collapse is automatic by construction (symmetric baseline).

#### Recommendations

- **Baseline constant**: pass-1 +25.21 cp ≡ live `EVAL_BASELINE_PAWNS_WHITE = 0.25`. **Keep.**
- **Neutral-zone bounds**: pooled centered `[p25, p75] = [−23, +34] cp` → symmetric **±30 cp = ±0.30 pawns**. Matches live `EVAL_NEUTRAL_MIN/MAX_PAWNS = ±0.30`. **Keep.**
- **Domain bounds**: pooled `[p05, p95] = [−92, +89] cp` ≈ ±90 cp / ±0.90 pawns. Live `EVAL_BULLET_DOMAIN_PAWNS = 1.5` is wider (intentional whisker headroom for the 800-cohort tail). **Keep.**
- **Pooled mean** +3.7 cp (~0.04 pawns) — well inside the symmetric tolerance, no asymmetric tweak warranted.
- **Mate-row footnote**: mate rows are excluded from pass 1 by the `eval_mate IS NULL` filter. In the deduped sample they are negligible at MG entry (eval coverage near 100% on the benchmark DB; the few mate-at-MG cases are flag-the-king blunders).

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

Derived from §3.1.6's per-user CTE. Aggregates `non_eg_score = (W + 0.5·D)/total` over games NOT reaching the 6-ply endgame floor.

##### Pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,020 | 51.9% | 8.3% | 38.1% | 46.1% | 51.6% | 57.3% | 67.1% |

##### ELO marginal

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 697 | 51.9% | 7.5% | 46.8% | 51.9% | 56.6% |
| 1200 | 968 | 52.0% | 8.5% | 46.4% | 51.3% | 56.9% |
| 1600 | 1,016 | 51.5% | 9.2% | 45.3% | 51.2% | 56.8% |
| 2000 | 839 | 52.4% | 9.1% | 46.2% | 52.0% | 58.1% |
| 2400 | 500 | 52.2% | 9.4% | 46.4% | 52.1% | 58.0% |

##### TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,238 | 50.7% | 8.4% | 45.5% | 50.8% | 55.6% |
| blitz | 1,228 | 51.2% | 8.0% | 45.6% | 51.0% | 56.3% |
| rapid | 1,156 | 53.1% | 9.1% | 46.7% | 52.4% | 58.5% |
| classical | 398 | 54.8% | 9.9% | 48.4% | 54.5% | 61.9% |

#### Collapse verdict

- **TC axis**: max |d| = **0.46** (bullet vs classical) → **review** (borderline keep)
- **ELO axis**: max |d| = **0.10** (1600 vs 2000) → **collapse**

The TC effect is sigmoid asymmetry combined with classical players' slow-play skill edge — classical Non-EG games average +5pp above bullet. ELO axis collapses cleanly because equal-footing filtering removes the matchmaking effect.

#### Recommendations

- Pooled `[p25, p75] = [46.1%, 57.3%]` vs live `SCORE_BULLET_NEUTRAL = [45%, 55%]`. Midpoint drift +1.7pp; upper edge p75=57.3% is 2.3pp above live 55%, so ~25% of users currently land in green on Non-EG (equal-footing skill edge is real but small).
- **Action**: keep `SCORE_BULLET_NEUTRAL = [0.45, 0.55]` as a shared global band — the misalignment is within the editorial-tightening tolerance and the same constant drives the Openings score bullet on a different population. If a dedicated non-EG band ever surfaces, target `[0.46, 0.57]`.

---

#### 3.1.2 Endgame-entry eval (pawns)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.60` pawns | `frontend/src/lib/endgameEntryEvalZones.ts` |
| `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `2.25` pawns | same |
| `ENDGAME_ENTRY_EVAL_CENTER` | `0` (0-centered tile) | same |
| `ZONE_REGISTRY["entry_eval_pawns"]` | `(-0.60, +0.60)` | `app/services/endgame_zones.py` |

##### Pass 1 — symmetric EG-entry baseline (deduped game-level)

| n_games | baseline_cp_white | median_white_pov | sd_white_pov |
|---:|---:|---:|---:|
| 1,604,885 | **+10.32** | +0.0 | 443.8 |

White baseline +10 cp (vs MG's +25). Half the MG baseline — by EG entry the engine valuation has compressed (many decisive games already over, surviving games closer to balanced). Symmetric: `EG_BASELINE_CP_BLACK = −10`.

##### Pass 2 — pooled distribution (uncentered drives the live tile recommendation)

| variant | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **uncentered** | 8,322 | +9.3 cp | 119.2 cp | −185 | −57 | +10 | +77 | +200 |
| centered | 8,322 | +9.3 cp | 118.6 cp | −183 | −57 | +10 | +76 | +199 |

The centered and uncentered distributions are nearly identical because the EG baseline is small (±10 cp) relative to the per-user-mean SD (~119 cp). Recommendations read off the **uncentered** distribution since the live tile is 0-centered.

##### ELO marginal (centered)

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 1,359 | +1.7 | 163.6 | −261 | −101 | +1 | +102 | +270 |
| 1200 | 1,943 | +3.6 | 137.4 | −221 | −77 | +4 | +91 | +226 |
| 1600 | 2,099 | +15.1 | 109.5 | −163 | −51 | +16 | +82 | +191 |
| 2000 | 1,817 | +15.2 | 86.7 | −127 | −40 | +17 | +67 | +154 |
| 2400 | 1,104 | +7.9 | 67.1 | −94 | −36 | +7 | +48 | +116 |

##### TC marginal (centered)

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 2,563 | −0.1 | 144.8 | −80 | +2 | +80 |
| blitz | 2,521 | +12.3 | 99.4 | −46 | +11 | +70 |
| rapid | 2,406 | +17.1 | 104.6 | −43 | +16 | +77 |
| classical | 832 | +6.5 | 118.8 | −60 | +9 | +75 |

#### Collapse verdict

- **TC axis**: max |d| = **0.14** (bullet vs rapid) → **collapse**
- **ELO axis**: max |d| = **0.11** (800 vs 2000) → **collapse**

#### Recommendations

- **Neutral-zone bounds** (uncentered IQR): `[−0.57, +0.77]` pawns. Symmetric round = ±0.65 pawns. Live = ±0.60 → recommendation +0.05 pawns asymmetric drift, but symmetric ±0.60 already inside cohort IQR. **Keep ±0.60** (already editorially tightened per Phase 82 diff item A).
- **Domain bounds** (uncentered p05/p95): `[−1.85, +2.00]` pawns. Live = ±2.25 (slightly wider for whisker headroom). **Keep.**
- **Center**: 0 pawns. Tile remains 0-centered. **Keep.**
- **Asymmetry note**: pooled mean is +0.09 pawns (cohort skill edge). The asymmetry is small relative to band width; symmetric band is defensible.

---

#### 3.1.3 Achievable Score (entry_xs)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["entry_expected_score"]` | `(0.45, 0.55)` | `app/services/endgame_zones.py` |

Per-user `entry_xs = avg(expected_score)` via the Lichess winning-chances sigmoid on entry-ply eval (mate forces 0/1).

##### Pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 50.9% | 8.0% | 38.0% | 46.2% | 51.0% | 55.7% | 64.0% |

##### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 50.5% | 10.5% | 33.3% | 43.9% | 50.6% | 57.0% | 67.8% |
| 1200 | 1,068 | 50.7% | 9.2% | 36.2% | 44.8% | 50.5% | 56.6% | 65.7% |
| 1600 | 1,166 | 51.4% | 7.5% | 39.4% | 46.5% | 51.5% | 56.2% | 63.6% |
| 2000 | 1,028 | 51.3% | 6.1% | 41.4% | 47.4% | 51.3% | 55.0% | 61.2% |
| 2400 | 598 | 50.6% | 4.9% | 43.2% | 47.6% | 50.3% | 53.3% | 58.6% |

The per-user SD compresses sharply from 10.5pp (800) → 4.9pp (2400). Strong players settle into endgames with very predictable expected scores; weak players walk into far more variable positions.

##### TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.4% | 9.4% | 44.7% | 50.4% | 56.2% |
| blitz | 1,353 | 51.0% | 6.8% | 47.0% | 51.1% | 55.1% |
| rapid | 1,334 | 51.4% | 7.2% | 46.9% | 51.2% | 55.8% |
| classical | 579 | 50.9% | 8.5% | 45.8% | 50.7% | 56.0% |

#### Collapse verdict

- **TC axis**: max |d| = **0.12** (bullet vs rapid) → **collapse**
- **ELO axis**: max |d| = **0.12** (1600 vs 2400) → **collapse**

#### Recommendations

- Pooled `[p25, p75] = [46.2%, 55.7%]`. Live `[0.45, 0.55]` is essentially identical. **Keep.** The cohort skill edge (+1pp midpoint vs 50%) is well within editorial tolerance.
- Sanity check: 800–1600 game-time buckets sit at `[50.5%, 50.7%, 51.4%]` — within ≈±1.5pp of 50% with no monotone ramp. 2000/2400 sit at `[51.3%, 50.6%]` — also flat. Equal-footing filter is working as intended.

---

#### 3.1.4 Endgame Score (per-user, EG-only)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["endgame_score"]` | `(0.45, 0.55)` | `app/services/endgame_zones.py` |
| `SCORE_BULLET_NEUTRAL_MIN/MAX` | `±0.05` around 0.5 | `frontend/src/lib/scoreBulletConfig.ts` |

##### Pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 51.4% | 8.7% | 38.3% | 46.1% | 51.0% | 56.5% | 66.5% |

##### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 49.9% | 9.4% | 36.1% | 44.0% | 49.3% | 55.0% | 66.5% |
| 1200 | 1,068 | 50.2% | 9.1% | 36.4% | 44.5% | 49.6% | 55.3% | 65.3% |
| 1600 | 1,166 | 51.6% | 8.6% | 38.6% | 46.0% | 50.8% | 56.8% | 67.1% |
| 2000 | 1,028 | 52.9% | 8.3% | 41.1% | 47.3% | 52.5% | 57.7% | 67.5% |
| 2400 | 598 | 52.8% | 7.0% | 41.5% | 48.7% | 52.7% | 56.6% | 63.6% |

##### TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.6% | 7.6% | 46.0% | 50.0% | 54.7% |
| blitz | 1,353 | 51.7% | 8.2% | 46.2% | 51.6% | 56.5% |
| rapid | 1,334 | 52.3% | 8.9% | 46.6% | 51.9% | 57.4% |
| classical | 579 | 50.9% | 10.9% | 43.9% | 50.2% | 57.9% |

#### Collapse verdict

- **TC axis**: max |d| = **0.21** (bullet vs rapid) → **review** (just over threshold)
- **ELO axis**: max |d| = **0.35** (800 vs 2000) → **review**

The 800-cohort scores ≈3pp below the 2000-cohort against equal-footing opponents — a residual rating-tail confound (D-01 no-cheat-filtering at high ELO; weak-player rating-noise at low ELO). Per the SKILL's "Sanity check (game-time bucketing aware)" rule, this is the known out-of-scope confound — not a filter failure.

#### Recommendations

- Pooled `[p25, p75] = [46.1%, 56.5%]`. Live `[0.45, 0.55]` is +0.5pp narrow on the upper edge but well within tolerance. **Keep.** The cohort skill edge (+1.4pp) is real but small.
- ELO ramp `49.9% → 52.9%` (3pp spread) is the known matchmaking-residual (filed under "rating-lag selection bias"). Per the SKILL the binding action is to flag, not retune. Per-ELO `ENDGAME_SCORE_ZONES` stratification deferred (already deferred via D-11 per the live constant comment).

---

#### 3.1.5 Achievable Score Gap (paired actual − expected)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["achievable_score_gap"]` | `(-0.05, +0.05)` | `app/services/endgame_zones.py` |
| `EVAL_CLIP_MAX_CP` | 2000 | `app/services/endgame_service.py` |
| `PVALUE_RELIABILITY_MIN_N` | 10 | same |

##### Pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | +0.5pp | 8.2pp | −12.8pp | −3.9pp | +0.7pp | +5.1pp | +13.2pp |

##### ELO marginal

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 756 | −0.6pp | 9.3pp | −5.8pp | −0.4pp | +4.5pp |
| 1200 | 1,068 | −0.5pp | 8.6pp | −4.7pp | −0.3pp | +4.2pp |
| 1600 | 1,166 | +0.2pp | 7.8pp | −3.9pp | +0.4pp | +4.6pp |
| 2000 | 1,028 | **+1.7pp** | 7.6pp | −2.8pp | +1.7pp | +6.1pp |
| 2400 | 598 | **+2.2pp** | 6.9pp | −2.0pp | +2.5pp | +6.4pp |

The mean shifts monotonically with rating: 800 sits at −0.6pp (underperforms engine), 2400 at +2.2pp (outperforms). Game-time bucketing didn't fully neutralize this — stronger players genuinely outperform the engine's sigmoid prediction at endgame entry (the cohort skill edge survives the equal-footing filter because the sigmoid is calibrated on a flat-skill assumption).

##### TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | +0.2pp | 11.0pp | −6.0pp | +0.7pp | +7.2pp |
| blitz | 1,353 | +0.7pp | 7.0pp | −3.4pp | +1.0pp | +5.0pp |
| rapid | 1,334 | +0.9pp | 6.3pp | −2.7pp | +0.7pp | +4.4pp |
| classical | 579 | 0.0pp | 6.7pp | −4.2pp | −0.1pp | +4.0pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.13** (bullet vs rapid) → **collapse**
- **ELO axis**: max |d| = **0.34** (800 vs 2400) → **review**

The 2026-05-24 snapshot had ELO d = 0.62 ("keep separate"); doubling the cohort dropped it to 0.34 ("review"). The cohort-skill drift is real but the d_max compression suggests the previous estimate was tail-driven.

#### Recommendations

- Pooled `[p25, p75] = [−3.9pp, +5.1pp]` → symmetric **±5pp**. Live `(−0.05, +0.05)` matches exactly. **Keep.**
- Pooled `[p05, p95] = [−12.8pp, +13.2pp]` — symmetric ~±13pp, consistent with the asymmetric `±5pp` neutral band fitting cleanly inside the per-game noise.
- **Per-ELO stratification**: still defer. The d=0.34 verdict says "review", not "keep separate"; the 800 (−0.6pp) → 2400 (+2.2pp) drift fits inside the symmetric ±5pp band at every level (only 2400's p50 = +2.5pp grazes the upper edge). Single global band remains defensible.

---

#### 3.1.6 Endgame Score Gap and Timeline

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["score_gap"]` | `(-0.10, +0.10)` | `app/services/endgame_zones.py` |

##### Pooled distribution (per-user `eg_score − non_eg_score`)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,020 | −0.9pp | 13.2pp | −21.8pp | −9.9pp | −1.0pp | +8.0pp | +20.7pp |

##### ELO marginal

| ELO | n | diff mean | diff SD | diff p25 | diff p50 | diff p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 697 | −2.4pp | 13.6pp | −11.7pp | −3.0pp | +6.4pp |
| 1200 | 968 | −1.7pp | 13.6pp | −11.0pp | −2.1pp | +7.7pp |
| 1600 | 1,016 | −0.3pp | 13.9pp | −9.0pp | −0.3pp | +9.0pp |
| 2000 | 839 | −0.4pp | 12.4pp | −8.5pp | −0.4pp | +8.2pp |
| 2400 | 500 | +0.3pp | 11.3pp | −7.1pp | +0.6pp | +7.8pp |

##### TC marginal

| TC | n | diff mean | diff SD | diff p25 | diff p50 | diff p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,238 | −0.4pp | 12.3pp | −9.0pp | −1.2pp | +7.8pp |
| blitz | 1,228 | +0.2pp | 12.5pp | −8.4pp | +0.1pp | +8.5pp |
| rapid | 1,156 | −1.4pp | 13.6pp | −10.4pp | −1.0pp | +7.9pp |
| classical | 398 | −4.8pp | 15.8pp | −15.9pp | −4.7pp | +7.0pp |

Classical players score nearly 5pp lower in endgames than non-endgames — slow games resolve more endgame structure, so the eg/non-eg split is more visible.

#### Collapse verdict

- **TC axis**: max |d| = **0.37** (blitz vs classical) → **review**
- **ELO axis**: max |d| = **0.21** (800 vs 2400) → **review**

#### Recommendations

- Pooled `[p25, p75] = [−9.9pp, +8.0pp]` → symmetric **±10pp**. Live `(−0.10, +0.10)` matches. **Keep.**
- Pooled `[p05, p95] = [−21.8pp, +20.7pp]` ≈ ±21pp. The score-gap gauge domain is set elsewhere; the cohort sits inside the live ±25pp domain comfortably.
- **Timeline overlay**: pooled `eg_score` IQR `[46.1%, 55.6%]` overlaps `non_eg_score` IQR `[46.1%, 57.3%]` strongly. Combined band `[46.1%, 55.6%]` (intersection) suffices for a single unified neutral band on the timeline. Pooled `eg_score` p05/p95 `[38.9%, 64.2%]` and `non_eg_score` p05/p95 `[38.1%, 67.1%]` set the timeline Y-axis at roughly `[38%, 67%]`.


### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery (+ retracted Endgame Skill)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `BUCKETED_ZONE_REGISTRY["conversion_win_pct"]` | `(0.65, 0.77)` | `app/services/endgame_zones.py` |
| `BUCKETED_ZONE_REGISTRY["parity_score_pct"]` | `(0.45, 0.55)` | same |
| `BUCKETED_ZONE_REGISTRY["recovery_save_pct"]` | `(0.24, 0.36)` | same |
| `endgame_skill` ZoneSpec | **deleted** (Phase 87.4 D-05) | n/a |

##### Conversion (per-user)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,616 | 71.1% | **64.9%** | 71.6% | **77.7%** |
| 800 | 756 | 67.8% | 61.3% | 69.1% | 75.0% |
| 1200 | 1,068 | 70.0% | 63.8% | 71.2% | 76.8% |
| 1600 | 1,166 | 71.7% | 65.7% | 72.0% | 78.3% |
| 2000 | 1,028 | 72.5% | 66.7% | 72.9% | 79.0% |
| 2400 | 598 | 73.3% | 67.8% | 73.0% | 78.6% |
| bullet | 1,350 | 65.2% | 58.8% | 65.6% | 71.9% |
| blitz | 1,353 | 71.7% | 66.7% | 71.9% | 76.9% |
| rapid | 1,334 | 74.4% | 69.6% | 74.6% | 80.0% |
| classical | 579 | 75.5% | 68.5% | 76.0% | 83.3% |

**Collapse verdict:** TC d=**0.93** (bullet vs classical) → **keep separate**; ELO d=**0.51** (800 vs 2400) → **keep separate**.

##### Parity (per-user)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,616 | 50.7% | **44.0%** | 50.0% | **57.3%** |
| 800 | 756 | 49.3% | 40.0% | 50.0% | 57.9% |
| 1200 | 1,068 | 49.4% | 42.1% | 50.0% | 56.4% |
| 1600 | 1,166 | 50.7% | 43.8% | 50.0% | 57.1% |
| 2000 | 1,028 | 52.1% | 46.1% | 52.0% | 58.3% |
| 2400 | 598 | 52.2% | 46.7% | 52.0% | 57.1% |
| bullet | 1,350 | 50.4% | 43.6% | 50.0% | 57.2% |
| blitz | 1,353 | 50.8% | 44.8% | 51.0% | 56.9% |
| rapid | 1,334 | 51.3% | 44.9% | 50.5% | 57.5% |
| classical | 579 | 49.8% | 40.4% | 50.0% | 59.1% |

**Collapse verdict:** TC d=**0.08** → **collapse**; ELO d=**0.20** (800 vs 2400) → **review** (at threshold).

##### Recovery (per-user)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,616 | 30.8% | **24.0%** | 30.0% | **37.0%** |
| 800 | 756 | 31.3% | 23.9% | 30.2% | 37.3% |
| 1200 | 1,068 | 29.9% | 23.3% | 29.4% | 36.0% |
| 1600 | 1,166 | 30.3% | 23.4% | 29.4% | 36.4% |
| 2000 | 1,028 | 31.0% | 23.6% | 30.2% | 37.5% |
| 2400 | 598 | 32.5% | 26.1% | 31.6% | 37.5% |
| bullet | 1,350 | 35.7% | 29.5% | 35.3% | 41.2% |
| blitz | 1,353 | 30.9% | 25.1% | 30.0% | 35.7% |
| rapid | 1,334 | 28.1% | 21.8% | 27.3% | 33.3% |
| classical | 579 | 25.6% | 17.4% | 23.5% | 31.6% |

**Collapse verdict:** TC d=**0.90** (bullet vs classical) → **keep separate**; ELO d=**0.25** (1200 vs 2400) → **review**.

##### Endgame Skill (per-user) — informational only (composite retracted)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,616 | 50.9% | 46.4% | 50.8% | 55.3% |
| 800 | 756 | 49.5% | 44.7% | 49.8% | 54.6% |
| 2400 | 598 | 52.6% | 48.1% | 52.5% | 56.5% |

Composite spread is ~3pp across ELOs; per `endgame-skill-dropped-conversion-elo.md` the metric was retracted Phase 87.4, so no band recommendation. Reported only for cross-snapshot continuity.

#### Recommendations

- **Conversion** pooled `[p25, p75] = [64.9%, 77.7%]`. Live `[0.65, 0.77]` matches exactly. **Keep.** ELO + TC both keep-separate at d > 0.5 — but the live `BUCKETED_ZONE_REGISTRY` uses a single band per material-bucket (no TC/ELO stratification), and the pooled band centers everyone within ±5pp of cohort median. Per-TC stratification would help (bullet midpoint 65% vs classical 76%) — flag for future Phase if/when bucketed-per-TC zones become possible.
- **Parity** pooled `[p25, p75] = [44.0%, 57.3%]`. Live `[0.45, 0.55]` is +1pp narrower on the upper edge. The cohort upper IQR sits at 57.3% so ~25% of users land green on parity — defensible (cohort skill edge). **Keep.**
- **Recovery** pooled `[p25, p75] = [24.0%, 37.0%]`. Live `[0.24, 0.36]` matches on lower, +1pp narrow on upper. **Keep** (the +1pp on the upper edge is within editorial tolerance and the live band was already calibrated to this distribution in 2026-05-03).
- **TC stratification flag**: Conversion and Recovery both fail the collapse threshold at the TC axis (d≈0.9). Bullet players convert at 65% / recover at 36%; classical convert at 76% / recover at 26%. Single-band `BUCKETED_ZONE_REGISTRY` masks this. Per-TC stratification would let bullet players' Conv numbers paint green at 75%, not red. Track as a deferred improvement.


#### 3.2.2 Section-2 ΔES Score Gap (per entry-eval bucket)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["section2_score_gap_conv"]` | `(-0.11, 0.00)` | `app/services/endgame_zones.py` |
| `ZONE_REGISTRY["section2_score_gap_parity"]` | `(-0.04, 0.04)` | same |
| `ZONE_REGISTRY["section2_score_gap_recov"]` | `(+0.01, +0.11)` | same |
| `section2_score_gap_skill` | **deleted** (Phase 87.4 D-05) | n/a |

##### Conversion-bucket ΔES (per-user)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,138 | −6.2pp | **−11.0pp** | −4.8pp | **+0.2pp** |
| 800 | 683 | −12.9pp | −17.4pp | −10.5pp | −6.3pp |
| 1200 | 973 | −8.7pp | −12.8pp | −6.5pp | −2.5pp |
| 1600 | 1,048 | −5.2pp | −9.8pp | −3.8pp | +0.8pp |
| 2000 | 901 | −2.5pp | −6.8pp | −1.2pp | +3.2pp |
| 2400 | 533 | −1.2pp | −5.2pp | −1.1pp | +3.5pp |
| bullet | 1,270 | −13.2pp | −19.5pp | −11.6pp | −5.7pp |
| blitz | 1,254 | −4.5pp | −8.5pp | −4.0pp | +0.3pp |
| rapid | 1,201 | −2.3pp | −6.3pp | −2.0pp | +2.1pp |
| classical | 413 | −1.1pp | −5.3pp | −0.1pp | +3.8pp |

**Collapse verdict:** TC d=**1.25** (bullet vs classical) → **keep separate**; ELO d=**1.35** (800 vs 2400) → **keep separate**.

##### Parity-bucket ΔES (per-user)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 3,623 | +0.1pp | **−3.7pp** | +0.3pp | **+4.1pp** |
| 800 | 456 | −0.7pp | −5.6pp | 0.0pp | +4.5pp |
| 1200 | 780 | −0.6pp | −4.6pp | −0.6pp | +3.3pp |
| 1600 | 948 | −0.2pp | −4.0pp | −0.1pp | +3.8pp |
| 2000 | 883 | +0.8pp | −2.8pp | +0.9pp | +4.7pp |
| 2400 | 556 | +1.3pp | −2.0pp | +1.2pp | +4.8pp |
| bullet | 1,100 | −0.1pp | −4.0pp | +0.2pp | +4.2pp |
| blitz | 1,163 | +0.3pp | −3.3pp | +0.4pp | +4.1pp |
| rapid | 1,049 | +0.5pp | −3.7pp | +0.5pp | +4.6pp |
| classical | 311 | −0.7pp | −5.0pp | −0.4pp | +3.2pp |

**Collapse verdict:** TC d=**0.10** → **collapse**; ELO d=**0.31** (800 vs 2400) → **review**.

##### Recovery-bucket ΔES (per-user)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 3,973 | +6.4pp | **+0.9pp** | +5.4pp | **+11.0pp** |
| 800 | 670 | +11.2pp | +5.7pp | +9.5pp | +15.5pp |
| 1200 | 940 | +7.7pp | +2.6pp | +6.3pp | +11.8pp |
| 1600 | 989 | +5.2pp | −0.1pp | +3.5pp | +9.4pp |
| 2000 | 848 | +4.2pp | −1.0pp | +3.4pp | +9.1pp |
| 2400 | 526 | +3.9pp | −0.7pp | +3.6pp | +8.1pp |
| bullet | 1,240 | +12.9pp | +7.4pp | +12.4pp | +17.7pp |
| blitz | 1,219 | +5.1pp | +1.1pp | +4.8pp | +8.4pp |
| rapid | 1,123 | +2.8pp | −0.8pp | +2.6pp | +6.2pp |
| classical | 391 | +0.2pp | −3.7pp | +0.2pp | +3.5pp |

**Collapse verdict:** TC d=**1.69** (bullet vs classical) → **keep separate**; ELO d=**0.95** (800 vs 2400) → **keep separate**.

#### Recommendations

- **Conversion bucket** pooled `[p25, p75] = [−11.0pp, +0.2pp]` → round to **(−0.11, 0.00)**. Live matches exactly. **Keep.**
- **Parity bucket** pooled `[p25, p75] = [−3.7pp, +4.1pp]` → round to **(−0.04, +0.04)**. Live matches exactly. **Keep.**
- **Recovery bucket** pooled `[p25, p75] = [+0.9pp, +11.0pp]` → round to **(+0.01, +0.11)**. Live matches exactly. **Keep.**
- **Per-axis stratification flag**: all three buckets fail the collapse threshold on at least one axis, sometimes both. The scalar live bands paint a typical bullet-cohort player as `red on conversion`, `green on recovery` simultaneously even when their relative skill is at-cohort. Per-(TC × ELO) stratification of `section2_score_gap_*` would let bullet players see "typical for your TC" coloring. Track as a deferred improvement (consistent with the 2026-05-24 snapshot recommendation).


#### 3.2.3 Rate vs Score-Gap divergence (Conv & Recov cross-cut — derived)

Cross-cut of §3.2.1 raw rates against §3.2.2 ΔES gaps for the conversion and recovery buckets. Answers: where does the gap re-expose a signal the raw rate masks?

##### Axis-driver table

| Bucket | Raw rate ELO sweep | Raw rate ELO d / verdict | Raw rate TC sweep | Raw rate TC d / verdict | Gap ELO sweep | Gap ELO d / verdict | Gap TC sweep | Gap TC d / verdict |
|---|---|---:|---|---:|---|---:|---|---:|
| Conversion | 67.8% → 73.3% | 0.51 / keep | 65.2% → 75.5% | 0.93 / keep | −12.9pp → −1.2pp | 1.35 / keep | −13.2pp → −1.1pp | 1.25 / keep |
| Recovery | 31.3% → 32.5% (~flat) | 0.25 / review | 35.7% → 25.6% | 0.90 / keep | +11.2pp → +3.9pp | 0.95 / keep | +12.9pp → +0.2pp | 1.69 / keep |

##### Divergence callout

- **Conversion**: raw rate and gap agree across both axes (both two-axis metrics). No divergence — Conversion is consistently a TC + ELO stratified signal.
- **Recovery (ELO axis divergence)**: raw recovery rate is ~flat across ELO (29.9%–32.5%, d=0.25 review), but the recovery-bucket ΔES gap exposes a strong ELO signal (+11.2pp at 800 → +3.9pp at 2400, d=0.95 keep). The raw rate is flat because the engine's expected score also drops at higher ELOs (their opponents are stronger relative to the engine baseline), so absolute recovery hits the same draw-skewed ceiling. The gap subtracts ES_entry and re-exposes the relative-skill signal: weak players outperform engine expectations *much more* when recovering (~+10pp above sigmoid) than strong players do (~+4pp).
- **Mirror-axis note**: Recovery raw rate runs *opposite* to Conversion on the TC axis — more time → less recovery (your opponent also converts cleanly when given time). The gaps compress toward their off-zero sigmoid null as players strengthen and games slow, closer to engine-quality play.

##### Implication

The recovery-gap ELO `keep separate` (d=0.95) is the strongest argument against §3.2.2's scalar-registry deferral. **Recommendation unchanged for this phase**: scalar pooled bands stay shipped per §3.2.2. Recovery is the first candidate for per-(TC × ELO) stratification if/when that work is revisited.


### 3.3 Time Pressure

#### 3.3.1 Clock pressure at endgame entry (+ clock-gap-%)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `NEUTRAL_PCT_THRESHOLD` | `5.0` (±5%) | `app/services/endgame_zones.py` |
| `NEUTRAL_TIMEOUT_THRESHOLD` | `5.0` (±5pp) | same |
| `ZONE_REGISTRY["clock_gap_pct"]` | `(-0.065, +0.047)` | same |

##### Clock-diff % per-user mean

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,604 | −1.12% | **−6.35%** | −0.50% | **+4.83%** |
| 800 | 752 | −1.00% | −6.10% | −0.36% | +5.05% |
| 1200 | 1,067 | −1.28% | −6.83% | −0.47% | +5.20% |
| 1600 | 1,164 | −1.82% | −7.44% | −1.06% | +4.71% |
| 2000 | 1,025 | −0.86% | −6.18% | −0.56% | +4.49% |
| 2400 | 596 | −0.09% | −4.56% | −0.04% | +4.15% |
| bullet | 1,343 | −0.17% | −3.96% | −0.29% | +3.29% |
| blitz | 1,353 | −0.77% | −6.68% | −0.29% | +5.27% |
| rapid | 1,334 | −1.81% | −8.14% | −0.94% | +5.21% |
| classical | 574 | −2.60% | −11.29% | −1.21% | +8.19% |

**Collapse verdict (clock-diff %):** TC d=**0.24** (bullet vs classical) → **review**; ELO d=**0.17** → **collapse**.

##### Clock-gap-fraction (per-user mean of `(user_clk − opp_clk) / base_clock`)

| slice | n | p25 | p50 | p75 |
|---|---:|---:|---:|---:|
| **POOLED** | 4,604 | **−0.0635** | −0.0050 | **+0.0483** |
| bullet | 1,343 | −0.0396 | −0.0029 | +0.0329 |
| blitz | 1,353 | −0.0668 | −0.0029 | +0.0527 |
| rapid | 1,334 | −0.0814 | −0.0094 | +0.0521 |
| classical | 574 | −0.1129 | −0.0121 | +0.0819 |

Pooled `[p25, p75] = [−0.0635, +0.0483]` — matches live `ZONE_REGISTRY["clock_gap_pct"] = (-0.065, +0.047)` essentially exactly.

##### Net-timeout-rate (pp; positive = more flag wins than losses)

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,604 | +0.45pp | **−4.46pp** | +1.13pp | **+6.09pp** |
| 800 | 752 | −0.93pp | −5.89pp | 0.00pp | +4.81pp |
| 2400 | 596 | +2.33pp | −3.80pp | +2.85pp | +9.29pp |
| bullet | 1,343 | +0.45pp | −10.95pp | +0.53pp | +11.86pp |
| classical | 574 | −0.05pp | 0.00pp | 0.00pp | +1.80pp |

**Collapse verdict (net-timeout):** TC d=**0.04** → **collapse**; ELO d=**0.28** (800 vs 2400) → **review**.

#### Recommendations

- **Clock-diff %**: pooled `[p25, p75] = [−6.4%, +4.8%]` — slightly asymmetric. Live `±5%` is a defensible symmetric band; the cohort midpoint sits at −0.5%, so the live band centers near cohort median. **Keep ±5%.** The classical tail (IQR [−11%, +8%]) is wide but the d-verdict says review, not keep — single global band is fine.
- **Clock-gap-fraction**: live `(-0.065, +0.047)` matches pooled IQR essentially exactly. **Keep.**
- **Net-timeout**: pooled `[p25, p75] = [−4.5pp, +6.1pp]`. Live `±5pp` is close; the cohort skews slightly positive (median +1pp). **Keep symmetric ±5pp** — within editorial tolerance.


#### 3.3.2 Time pressure vs performance curve

##### Pooled curve (10 time-buckets, 0–9 = 0–100% clock remaining)

| tb | n_games | pooled score |
|---:|---:|---:|
| 0 | 74,569 | 31.0% |
| 1 | 97,328 | 41.8% |
| 2 | 106,008 | 49.0% |
| 3 | 125,531 | 52.2% |
| 4 | 140,322 | 54.0% |
| 5 | 150,007 | **54.7%** (peak) |
| 6 | 148,644 | 54.3% |
| 7 | 128,236 | 53.7% |
| 8 | 84,609 | 52.7% |
| 9 | 52,117 | 51.5% |

Pooled curve: strong forced-loss pressure at tb=0 (31%), peak at tb=5 (54.7%), gentle decline at high time-remaining (overplay / move-pace mismatch).

##### TC marginal (per time-bucket score)

| tb | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 0 | **25.6%** | 34.2% | 34.7% | **42.5%** |
| 1 | 39.7% | 44.0% | 44.0% | 47.4% |
| 2 | 49.3% | 49.3% | 47.5% | 47.6% |
| 3 | 53.2% | 51.7% | 50.2% | 48.6% |
| 4 | 55.2% | 53.6% | 52.6% | 49.2% |
| 5 | 56.3% | 54.6% | 52.7% | 49.6% |
| 6 | 56.5% | 54.3% | 52.4% | 50.7% |
| 7 | 55.8% | 54.2% | 52.3% | 50.6% |
| 8 | 54.3% | 53.6% | 52.1% | 50.3% |
| 9 | 50.3% | 52.6% | 52.3% | 50.6% |

At tb=0 (extreme time pressure), bullet players score 25.6% vs classical 42.5% — a 17pp TC gap that swamps every other variable. At tb=5–9 the TC effect compresses to ~5pp.

##### ELO marginal (per time-bucket score)

| tb | 800 | 1200 | 1600 | 2000 | 2400 |
|---:|---:|---:|---:|---:|---:|
| 0 | 26.8% | 28.5% | 31.1% | 33.8% | 33.7% |
| 1 | 39.4% | 40.0% | 40.8% | 43.4% | 44.9% |
| 5 | 53.8% | 53.9% | 53.9% | 55.7% | 56.4% |
| 9 | 50.6% | 50.4% | 52.5% | 53.0% | 56.2% |

ELO effect is steady ~3–7pp across the curve — much smaller than the TC effect at low tb.

#### Collapse verdict (per-time-bucket, marginal-pair max d on per-game score)

- **TC axis (per tb)**: tb=0 d ≈ **0.38** (bullet vs classical) → **review/keep**; tb=5 d ≈ **0.13** → collapse; tb=9 d ≈ **0.05** → collapse. Stratified verdict — TC matters most at extreme pressure.
- **ELO axis (per tb)**: d ≈ 0.10–0.18 across all time-buckets → **collapse** throughout.

#### Recommendations

- This curve feeds the older 10-bucket Time-Pressure-vs-Performance chart. The live UI ships per-(TC × quintile) bands via §3.3.3's `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`, not per-time-bucket overlays. **No code constant to retune from this subchapter alone** — see §3.3.3 for the actual zone calibration.
- TC stratification is justified for the chart's overlay (per-TC line series), especially at the high-pressure end. ELO can collapse.


#### 3.3.3 Chess score per pressure bin (per-(TC × quintile))

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `PRESSURE_BIN_NEUTRAL_CAP` | `0.06` | `app/services/endgame_zones.py` |
| `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | 20 bands (4 TC × 5 quintile) | same |
| `MIN_GAMES_PER_PRESSURE_BIN` | 5 | same |

ELO pooled per design (accept-pooled-with-caveat 2026-05-17). Bands are Score-Delta: `[max(p25-p50, -cap), min(p75-p50, +cap)]`.

##### Per-(TC × quintile) p25/p50/p75 and delta bands

| TC | Q | n_users | p25 | p50 | p75 | delta IQR | proposed band (cap = 0.06) |
|---|---:|---:|---:|---:|---:|---|---|
| bullet | 0 | 1,304 | 0.275 | 0.343 | 0.419 | (−0.069, +0.076) | (**−0.060**, **+0.060**) cap both |
| bullet | 1 | 1,362 | 0.463 | 0.516 | 0.579 | (−0.053, +0.063) | (−0.053, **+0.060**) upper cap |
| bullet | 2 | 1,356 | 0.507 | 0.562 | 0.619 | (−0.055, +0.057) | (−0.055, +0.057) no cap |
| bullet | 3 | 1,274 | 0.500 | 0.569 | 0.633 | (−0.069, +0.065) | (**−0.060**, **+0.060**) cap both |
| bullet | 4 | 679 | 0.449 | 0.543 | 0.643 | (−0.094, +0.100) | (**−0.060**, **+0.060**) cap both |
| blitz | 0 | 1,218 | 0.307 | 0.389 | 0.476 | (−0.082, +0.087) | (**−0.060**, **+0.060**) cap both |
| blitz | 1 | 1,296 | 0.450 | 0.511 | 0.586 | (−0.061, +0.075) | (**−0.060**, **+0.060**) cap both |
| blitz | 2 | 1,341 | 0.491 | 0.548 | 0.615 | (−0.057, +0.067) | (−0.057, **+0.060**) upper cap |
| blitz | 3 | 1,340 | 0.492 | 0.553 | 0.619 | (−0.061, +0.066) | (**−0.060**, **+0.060**) cap both |
| blitz | 4 | 1,057 | 0.455 | 0.544 | 0.625 | (−0.090, +0.081) | (**−0.060**, **+0.060**) cap both |
| rapid | 0 | 830 | 0.297 | 0.400 | 0.500 | (−0.103, +0.100) | (**−0.060**, **+0.060**) cap both |
| rapid | 1 | 1,110 | 0.417 | 0.500 | 0.583 | (−0.083, +0.083) | (**−0.060**, **+0.060**) cap both |
| rapid | 2 | 1,297 | 0.460 | 0.539 | 0.620 | (−0.079, +0.082) | (**−0.060**, **+0.060**) cap both |
| rapid | 3 | 1,358 | 0.472 | 0.540 | 0.614 | (−0.068, +0.074) | (**−0.060**, **+0.060**) cap both |
| rapid | 4 | 1,158 | 0.457 | 0.529 | 0.615 | (−0.073, +0.086) | (**−0.060**, **+0.060**) cap both |
| classical | 0 | 187 | 0.340 | 0.433 | 0.571 | (−0.093, +0.138) | (**−0.060**, **+0.060**) cap both |
| classical | 1 | 263 | 0.400 | 0.500 | 0.583 | (−0.100, +0.083) | (**−0.060**, **+0.060**) cap both |
| classical | 2 | 357 | 0.400 | 0.500 | 0.605 | (−0.100, +0.105) | (**−0.060**, **+0.060**) cap both |
| classical | 3 | 489 | 0.400 | 0.500 | 0.611 | (−0.100, +0.111) | (**−0.060**, **+0.060**) cap both |
| classical | 4 | 727 | 0.420 | 0.506 | 0.615 | (−0.086, +0.109) | (**−0.060**, **+0.060**) cap both |

##### Comparison to live constants

The doubled cohort produced wider delta IQRs across nearly every (TC, quintile) cell vs the 2026-05-17 snapshot. **17 of 20 bands now hit the cap at both edges**; only `bullet Q1` (−0.053, +0.060), `bullet Q2` (−0.055, +0.057), and `blitz Q2` (−0.057, +0.060) stay inside.

Live constants:

- `bullet Q1`: live `(−0.0481, +0.0524)` vs measured `(−0.0533, +0.0632)` — both edges drift outward; lower edge widens by 0.5pp, upper hits cap.
- `bullet Q2`: live `(−0.0380, +0.0493)` vs measured `(−0.0546, +0.0568)` — both edges widen meaningfully (1.7pp on lower, 0.8pp on upper).
- `bullet Q3`: live `(−0.0563, +0.06)` vs measured (cap both) — both edges widen, upper still at cap.
- `blitz Q2`: live `(−0.0557, +0.053)` vs measured `(−0.0571, +0.060)` — close.
- All other cells stay capped at ±0.06.

##### Collapse verdict (per quintile)

- **Q0 (extreme pressure)**: TC d ≈ **0.43** (bullet 0.343 vs classical 0.433) → **review/keep**; ELO d ≈ 0.20 → review.
- **Q1**: TC d ≈ **0.31** (bullet 0.516 vs classical 0.485) → review; ELO d ≈ 0.15 → collapse.
- **Q2**: TC d ≈ **0.37** (bullet 0.562 vs classical 0.511) → review; ELO d ≈ 0.18 → collapse.
- **Q3**: TC d ≈ **0.46** (bullet 0.569 vs classical 0.517) → review; ELO d ≈ 0.21 → review.
- **Q4**: TC d ≈ **0.18** (bullet 0.543 vs classical 0.506) → collapse; ELO d ≈ 0.15 → collapse.

TC stratification is justified at every quintile (the live per-TC band shape is correct); ELO mostly collapses (the live pooled-ELO design holds).

#### Recommendations

- **3 cells need narrowing** in `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (bullet Q1 / Q2, blitz Q2). The doubled cohort fits a slightly wider IQR than the 2026-05-17 calibration. Updates:
  - `bullet Q1`: `(-0.0533, +0.06)` (upper cap)
  - `bullet Q2`: `(-0.0546, +0.0568)` (no cap)
  - `bullet Q3`: `(-0.06, +0.06)` (both cap, was `(-0.0563, +0.06)`)
  - `blitz Q2`: `(-0.0571, +0.06)` (upper cap, was `(-0.0557, +0.053)`)
- All other 16 bands remain capped at ±0.06. Per-TC stratification is correct; ELO pool is correct. **Keep overall registry shape.**


### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

##### Currently set in code

| Constant | Live shape | File |
|---|---|---|
| `PER_CLASS_GAUGE_ZONES[<class>].conversion` | per-class `(lower, upper)` | `app/services/endgame_zones.py` |
| `PER_CLASS_GAUGE_ZONES[<class>].recovery` | per-class `(lower, upper)` | same |
| `SCORE_BULLET_NEUTRAL_MIN/MAX` (global, shared with non-EG) | `±0.05` around 0.5 | `frontend/src/lib/scoreBulletConfig.ts` |

##### Pooled-by-class summary (sparse cell excluded)

| class | games | users | pooled score | pooled conv | conv_n | pooled recov | recov_n |
|---|---:|---:|---:|---:|---:|---:|---:|
| rook | 187,177 | 3,655 | 50.7% | **71.2%** | 64,242 | **29.8%** | 62,058 |
| minor_piece | 139,393 | 3,611 | 50.9% | **69.4%** | 47,649 | **32.5%** | 46,300 |
| pawn | 74,055 | 3,487 | 50.9% | **73.9%** | 28,648 | **27.4%** | 27,713 |
| queen | 68,196 | 3,495 | 50.8% | **77.5%** | 28,439 | **23.5%** | 27,400 |
| mixed | 1,060,245 | 3,735 | 50.6% | **69.6%** | 408,600 | **31.1%** | 400,758 |
| pawnless | 11,690 | 2,723 | 50.8% | **79.3%** | 5,064 | **19.7%** | 4,734 |

Live `PER_CLASS_GAUGE_ZONES` calibration (260503) vs measured pooled:

| class | live conv | measured conv | Δ midpoint | live recov | measured recov | Δ midpoint |
|---|---|---:|---:|---|---:|---:|
| rook | (0.65, 0.75) → mid 70% | 71.2% | +1.2pp | (0.26, 0.36) → mid 31% | 29.8% | −1.2pp |
| minor_piece | (0.63, 0.73) → mid 68% | 69.4% | +1.4pp | (0.28, 0.38) → mid 33% | 32.5% | −0.5pp |
| pawn | (0.67, 0.79) → mid 73% | 73.9% | +0.9pp | (0.23, 0.34) → mid 28.5% | 27.4% | −1.1pp |
| queen | (0.73, 0.83) → mid 78% | 77.5% | −0.5pp | (0.20, 0.30) → mid 25% | 23.5% | −1.5pp |
| mixed | (0.65, 0.75) → mid 70% | 69.6% | −0.4pp | (0.28, 0.38) → mid 33% | 31.1% | −1.9pp |
| pawnless | (0.70, 0.80) → mid 75% | 79.3% | +4.3pp | (0.21, 0.31) → mid 26% | 19.7% | −6.3pp |

All midpoints sit within ±2pp of live except **pawnless**, which drifts +4.3pp on conv and −6.3pp on recov — the doubled cohort surfaces pawnless players at higher conversion / lower recovery than the previous calibration. Pawnless has small per-class n (5,064 conv games / 4,734 recov games — well above the n≥30 floor but small relative to other classes).

##### Per-class chess-score IQR (per-user, ≥10 games/user/class)

| class | n_users | mean | p10 | p25 | p50 | p75 | p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| rook | 3,075 | 50.5% | 37.4% | 43.9% | 50.0% | 57.1% | 63.9% |
| minor_piece | 2,841 | 50.4% | 35.1% | 43.0% | 50.8% | 57.8% | 64.8% |
| pawn | 2,353 | 50.2% | 33.3% | 41.9% | 50.0% | 58.6% | 66.4% |
| queen | 2,303 | 51.8% | 32.2% | 41.2% | 52.1% | 62.5% | 70.8% |
| mixed | 3,597 | 51.4% | 41.8% | 46.2% | 51.0% | 56.0% | 61.4% |
| pawnless | 243 | 44.6% | 21.1% | 30.0% | 41.7% | 58.6% | 68.6% |

Mixed has the tightest IQR (`±5pp`); pawn / queen are wider (`±9pp / ±11pp`); pawnless is by far the widest (`±14pp` and `n=243` users only at the ≥10-game floor — high noise).

#### Collapse verdict (per metric across class)

- Per-class **score** is flat (~50–51% pooled across all classes); class-effect on pooled score is `collapse`.
- Per-class **conversion** spread: 69% (minor_piece) → 79% (pawnless). Range 10pp → **keep separate** (this is why per-class `PER_CLASS_GAUGE_ZONES` exists).
- Per-class **recovery** spread: 20% (pawnless) → 33% (minor_piece). Range 13pp → **keep separate** (same).

#### Recommendations

- **Conv/recov per-class gauge zones** (live `PER_CLASS_GAUGE_ZONES`): rook/minor_piece/pawn/queen/mixed all sit within ±2pp of midpoint — **keep**. **Pawnless** (only class drifting >2pp) — recommend updating:
  - conversion: `(0.70, 0.80)` → **`(0.74, 0.84)`** (pooled +4.3pp midpoint drift; doubled cohort confirms higher conv rate).
  - recovery: `(0.21, 0.31)` → **`(0.15, 0.25)`** (pooled −6.3pp midpoint drift; doubled cohort confirms lower recov).
  - Caveat: pawnless has per-user `n_users=243`, much smaller than other classes (`2,303–3,597`). Apply update with caution; the recov drift especially is large.
- **Per-class score-bullet** (currently global `SCORE_BULLET_NEUTRAL = [0.45, 0.55]`): only **queen** and **pawnless** materially exceed the global band. Pooled score IQR per class:
  - mixed `[0.46, 0.56]` ≈ global; **keep**.
  - rook, minor_piece, pawn `[~0.43, ~0.58]` — moderately wider; per-class override would tighten typical zone painting marginally. **Keep global** (within editorial tolerance).
  - queen `[0.41, 0.63]` — meaningfully wider. Consider per-class override `(0.41, 0.63)` if the queen card's score bullet routinely paints red/green at typical values.
  - pawnless `[0.30, 0.59]` — very wide and small-n. **Keep global** — pawnless cards are hidden in the live UI (`HIDDEN_ENDGAME_CLASSES`) anyway.


#### 3.4.2 Per-span ΔES Score Gap by endgame type

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ZONE_REGISTRY["endgame_type_achievable_score_gap"]` | `(-0.04, +0.04)` | `app/services/endgame_zones.py` |
| `PER_CLASS_GAUGE_ZONES[<class>].achievable_score_gap` | per-class `(lower, upper)` | same |

##### Per-class pooled distribution (per-user `mean(gap_span)`, sparse cell excluded)

| class | n_users | mean | p25 | p50 | p75 | live band | live midpoint | measured midpoint | drift |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| rook | 2,841 | −0.4pp | −5.1pp | +0.1pp | +4.8pp | (−0.05, +0.05) | 0pp | −0.1pp | ✓ |
| minor_piece | 2,332 | +0.3pp | −4.8pp | +0.3pp | +5.6pp | (−0.04, +0.06) | +1pp | +0.4pp | ✓ |
| pawn | 1,417 | +0.5pp | −3.8pp | +0.6pp | +5.0pp | (−0.04, +0.05) | +0.5pp | +0.6pp | ✓ |
| queen | 1,307 | +0.4pp | −4.2pp | +0.5pp | +5.4pp | (−0.04, +0.05) | +0.5pp | +0.6pp | ✓ |
| mixed | 4,587 | +0.3pp | −3.1pp | +0.5pp | +3.8pp | (−0.03, +0.04) | +0.5pp | +0.3pp | ✓ |
| pawnless | 12* | +1.1pp | −1.1pp | +0.6pp | +3.8pp | (−0.04, +0.04) | 0pp | (n too low) | n=12 |

\* pawnless has only 12 users at the ≥20-spans-per-user floor — n far below the per-class minimum. Live band pinned to the global pooled band per Phase 87.1 — confirmed appropriate, no recommendation.

##### Per-class ELO marginal (for collapse verdicts)

| class | 800 (mean) | 1200 | 1600 | 2000 | 2400 | ELO d |
|---|---:|---:|---:|---:|---:|---:|
| rook | −0.9pp | −0.7pp | −0.6pp | +0.1pp | +0.5pp | 0.17 / collapse |
| minor_piece | −0.8pp | −0.6pp | −0.1pp | +0.6pp | +1.7pp | 0.30 / review |
| pawn | +0.2pp | 0.0pp | +0.4pp | +0.5pp | +1.0pp | 0.13 / collapse |
| queen | +1.3pp | +0.2pp | +0.4pp | +0.1pp | +0.2pp | 0.16 / collapse |
| mixed | −0.4pp | −0.4pp | 0.0pp | +1.1pp | +1.6pp | 0.30 / review |

##### Per-class TC marginal

| class | bullet | blitz | rapid | classical | TC d |
|---|---:|---:|---:|---:|---:|
| rook | −0.7pp | −0.1pp | −0.2pp | −0.5pp | 0.07 / collapse |
| minor_piece | +0.0pp | +0.6pp | +0.3pp | −0.2pp | 0.07 / collapse |
| pawn | +0.6pp | +0.5pp | +0.1pp | +1.0pp | 0.10 / collapse |
| queen | +0.7pp | +0.1pp | +0.1pp | −0.9pp | 0.18 / collapse |
| mixed | +0.1pp | +0.5pp | +0.5pp | −0.3pp | 0.13 / collapse |

#### Collapse verdict

- All per-class TC axes **collapse** (max d ≈ 0.18 across classes).
- Per-class ELO axes are mostly **collapse** (rook, pawn, queen) with **review** for minor_piece and mixed (d ≈ 0.30).
- The pooled-by-class verdicts (~0.13 TC, ~0.30 ELO) are consistent with the 2026-05-15 calibration.

#### Recommendations

- **Per-class achievable_score_gap bands**: all measured per-class IQRs sit within ±0.5pp of the live midpoints. The doubled cohort confirms the 2026-05-15 calibration. **Keep all 6 entries.**
- **Global default `ZONE_REGISTRY["endgame_type_achievable_score_gap"] = (-0.04, +0.04)`**: pooled-across-classes is approximately `(−0.04, +0.05)`, matching the live band's center but slightly wider on the upper edge. **Keep** — the asymmetric +1pp drift is within the editorial tolerance and the per-class entries dominate the live UI anyway.
- **Pawnless**: live `(−0.04, +0.04)` matches the global default. Stay pinned to the global until pawnless n exceeds 100.


#### 3.4.3 Endgame Type Score vs Score Gap — agreement / redundancy

Cross-cut decision input for the `EndgameTypeCard.tsx` chart inventory (Score bullet + Conv/Recov gauges + ΔES Score Gap + WDL). Question: do per-card Score and ΔES Score Gap rank users redundantly?

##### Per-class summary table

After the inner join (`≥10 games/user/class` for score AND `≥20 spans/user/class` for gap, paired within the same game-time ELO bucket), only the **mixed** class clears the ≥30-users floor required for stable Pearson r. The other classes (rook, minor_piece, pawn, queen, pawnless) drop below the floor because their (user × game-time-ELO × TC × class) cells are too thin once both metrics' floors stack.

| class | n_users | Pearson r | sign_agree | strict zone-agree | strong disagreement | score SD | gap SD |
|---|---:|---:|---:|---:|---:|---:|---:|
| mixed | 5,274 | **+0.105** | 46.3% | **42.2%** | **9.0%** | 0.149 | 0.049 |

##### Independence baselines (per metric, marginally 25/50/25 across red/neutral/green under IQR zones)

- **Strict zone-agreement under independence** (r=0): 37.5%
- **Strong disagreement under independence** (r=0): 12.5%

Observed for mixed: strict agreement 42.2% (≈+4.7pp above independence floor — very weak positive overlap); strong disagreement 9.0% (≈−3.5pp *below* independence — very slight anti-disagreement). Both consistent with the r=+0.105 effective signal: the two metrics carry **mostly orthogonal information**.

##### Verdict (decision rubric)

- r = 0.105 (well below 0.60 threshold)
- strict zone-agreement = 42.2% (well below 55% threshold)
- strong disagreement = 9.0% (just below the 10% threshold, but combined with r=0.10 this lands in the bottom row of the rubric)

**Decision: KEEP ALL THREE SIGNALS.** Score, Score Gap, and the Conv/Recov gauges on each Endgame Type card are reading meaningfully different things. The Score Gap is an engine-baseline-adjusted relative metric; the Score is the absolute outcome; together they answer "did you score 50% AND was that against typical positions you walked into?". Cognitive cost is justified.

##### Scope caveat

Only `mixed` reached the ≥30-users joint floor under the current data shape. The rubric verdict is class-specific; it's drawn from the mode (mixed, by far the largest class) and applied to the layout decision. Repeating this analysis with looser score-and-gap floors (`≥5 games`, `≥10 spans`) would surface the other 4 classes — but the mixed-class verdict is so unambiguous (r=0.10) that running them is unlikely to change the recommendation.

This subchapter does not calibrate a code constant — it informs the `EndgameTypeCard.tsx` chart inventory decision.


---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| MG-entry eval (centered) | 2.1 | collapse (0.18) | collapse (0.09) | Single symmetric ±30 cp band fits all cells |
| Non-Endgame Score (per-user) | 3.1.1 | review (0.46) | collapse (0.10) | Classical tail; keep global ±5pp band |
| EG-entry eval (uncentered) | 3.1.2 | collapse (0.14) | collapse (0.11) | Single 0-centered ±0.60 pawn band fits |
| Achievable Score (entry_xs) | 3.1.3 | collapse (0.12) | collapse (0.12) | Single [0.45, 0.55] band fits |
| EG Score (per-user, EG-only) | 3.1.4 | review (0.21) | review (0.35) | ELO tail residual — known D-01 confound |
| Achievable Score Gap (paired) | 3.1.5 | collapse (0.13) | review (0.34) | Sample doubled the 0.62 → 0.34 verdict; keep ±5pp |
| EG Score Gap (eg − non_eg) | 3.1.6 | review (0.37) | review (0.21) | Classical tail; keep ±10pp |
| Conversion (per-user rate) | 3.2.1 | **keep (0.93)** | **keep (0.51)** | Per-TC stratification deferred |
| Parity (per-user rate) | 3.2.1 | collapse (0.08) | review (0.20) | Keep global |
| Recovery (per-user rate) | 3.2.1 | **keep (0.90)** | review (0.25) | Per-TC stratification deferred (mirror axis to Conv) |
| Endgame Skill (composite) | 3.2.1 | — | — | **Retracted Phase 87.4** — no band |
| Section-2 Conversion ΔES gap | 3.2.2 | **keep (1.25)** | **keep (1.35)** | Per-axis stratification deferred |
| Section-2 Parity ΔES gap | 3.2.2 | collapse (0.10) | review (0.31) | Keep scalar |
| Section-2 Recovery ΔES gap | 3.2.2 | **keep (1.69)** | **keep (0.95)** | Per-axis stratification deferred; mirror to Conv |
| Section-2 Skill ΔES gap | 3.2.2 | — | — | **Retracted Phase 87.4** — no band |
| Clock-diff % at EG entry | 3.3.1 | review (0.24) | collapse (0.17) | Keep symmetric ±5% |
| Clock-gap fraction | 3.3.1 | (per-TC IQRs vary) | collapse | Live (−0.065, +0.047) matches |
| Net-timeout rate | 3.3.1 | collapse (0.04) | review (0.28) | Keep ±5pp |
| Time-pressure curve (per-bucket) | 3.3.2 | review/keep at tb=0 → collapse at tb=9 | collapse | TC stratification justified at extreme tb |
| Score per pressure quintile Q0 | 3.3.3 | review (0.43) | review (0.20) | Per-TC band stratification — correct |
| Score per pressure quintile Q1 | 3.3.3 | review (0.31) | collapse (0.15) | Per-TC band — correct |
| Score per pressure quintile Q2 | 3.3.3 | review (0.37) | collapse (0.18) | Per-TC band — correct |
| Score per pressure quintile Q3 | 3.3.3 | review (0.46) | review (0.21) | Per-TC band — correct |
| Score per pressure quintile Q4 | 3.3.3 | collapse (0.18) | collapse (0.15) | Per-TC band — could pool, low priority |
| Per-class score (pooled) | 3.4.1 | collapse (~0.10) | collapse (~0.10) | Class-effect on pooled score is flat |
| Per-class conversion (pooled rate) | 3.4.1 | (per-class spread 10pp) | — | **Keep per-class** (`PER_CLASS_GAUGE_ZONES`) |
| Per-class recovery (pooled rate) | 3.4.1 | (per-class spread 13pp) | — | **Keep per-class** (`PER_CLASS_GAUGE_ZONES`) |
| Per-class per-span ΔES Score Gap | 3.4.2 | collapse (~0.13) | review (~0.30) | Keep per-class achievable_score_gap bands |

---

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| MG-entry baseline | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | `+0.25` | `+0.25` | — | **keep** |
| MG-entry neutral | 2.1 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.30` | `±0.30` | TC + ELO collapse | **keep** |
| MG-entry domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | `1.5` | `1.5` | — | **keep** (whisker headroom) |
| Non-EG score band | 3.1.1 | `SCORE_BULLET_NEUTRAL_MIN/MAX` (shared) | `±0.05` | `±0.05` (or `(−0.04, +0.07)` if non-EG-only band) | TC review, ELO collapse | **keep** shared band |
| EG-entry eval neutral | 3.1.2 | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.60` | `±0.60` | both collapse | **keep** |
| EG-entry eval domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `2.25` | `2.25` | — | **keep** |
| Achievable Score band | 3.1.3 | `ZONE_REGISTRY["entry_expected_score"]` | `(0.45, 0.55)` | `(0.45, 0.55)` | both collapse | **keep** |
| EG Score band | 3.1.4 | `ZONE_REGISTRY["endgame_score"]` | `(0.45, 0.55)` | `(0.45, 0.55)` | both review (within tolerance) | **keep** |
| Achievable Score Gap band | 3.1.5 | `ZONE_REGISTRY["achievable_score_gap"]` | `(−0.05, +0.05)` | `(−0.05, +0.05)` | TC collapse, ELO review | **keep** |
| EG Score Gap band | 3.1.6 | `ZONE_REGISTRY["score_gap"]` | `(−0.10, +0.10)` | `(−0.10, +0.10)` | both review | **keep** |
| Conversion rate band | 3.2.1 | `BUCKETED_ZONE_REGISTRY["conversion_win_pct"]` | `(0.65, 0.77)` | `(0.65, 0.77)` | TC + ELO keep | **keep** (per-TC stratification deferred) |
| Parity rate band | 3.2.1 | `BUCKETED_ZONE_REGISTRY["parity_score_pct"]` | `(0.45, 0.55)` | `(0.45, 0.55)` | TC collapse, ELO review | **keep** |
| Recovery rate band | 3.2.1 | `BUCKETED_ZONE_REGISTRY["recovery_save_pct"]` | `(0.24, 0.36)` | `(0.24, 0.36)` | TC keep, ELO review | **keep** (per-TC stratification deferred) |
| Section-2 Conv ΔES | 3.2.2 | `ZONE_REGISTRY["section2_score_gap_conv"]` | `(−0.11, 0.00)` | `(−0.11, 0.00)` | both keep | **keep** scalar (per-axis stratification deferred) |
| Section-2 Parity ΔES | 3.2.2 | `ZONE_REGISTRY["section2_score_gap_parity"]` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | TC collapse, ELO review | **keep** |
| Section-2 Recov ΔES | 3.2.2 | `ZONE_REGISTRY["section2_score_gap_recov"]` | `(+0.01, +0.11)` | `(+0.01, +0.11)` | both keep | **keep** scalar (per-axis stratification deferred) |
| Clock-diff % band | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | `5.0` | `5.0` | review/collapse | **keep** |
| Clock-gap-fraction band | 3.3.1 | `ZONE_REGISTRY["clock_gap_pct"]` | `(−0.065, +0.047)` | `(−0.0635, +0.0483)` | review/collapse | **keep** (matches within 0.2pp) |
| Net-timeout band | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | `5.0` | `5.0` | collapse/review | **keep** |
| Pressure-bin bullet Q1 | 3.3.3 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES["bullet"][1]` | `(−0.0481, +0.0524)` | `(−0.0533, +0.0600)` | per-quintile review | **narrow → widen** |
| Pressure-bin bullet Q2 | 3.3.3 | `…["bullet"][2]` | `(−0.0380, +0.0493)` | `(−0.0546, +0.0568)` | per-quintile review | **widen** |
| Pressure-bin bullet Q3 | 3.3.3 | `…["bullet"][3]` | `(−0.0563, +0.0600)` | `(−0.0600, +0.0600)` | per-quintile review | **widen lower → cap** |
| Pressure-bin blitz Q2 | 3.3.3 | `…["blitz"][2]` | `(−0.0557, +0.0530)` | `(−0.0571, +0.0600)` | per-quintile review | **widen upper → cap** |
| Pressure-bin other 16 cells | 3.3.3 | various | mostly `(−0.06, +0.06)` capped | `(−0.06, +0.06)` capped | per-quintile various | **keep** (already capped) |
| Per-class conv pawnless | 3.4.1 | `PER_CLASS_GAUGE_ZONES["pawnless"].conversion` | `(0.70, 0.80)` | `(0.74, 0.84)` | class-effect keep | **shift +4pp** |
| Per-class recov pawnless | 3.4.1 | `PER_CLASS_GAUGE_ZONES["pawnless"].recovery` | `(0.21, 0.31)` | `(0.15, 0.25)` | class-effect keep | **shift −6pp** (caveat: n=243) |
| Per-class conv/recov rook–mixed | 3.4.1 | `PER_CLASS_GAUGE_ZONES` (5 entries) | various | all measured within ±2pp midpoint | class-effect keep | **keep** |
| Per-class score-bullet | 3.4.1 | `SCORE_BULLET_NEUTRAL_MIN/MAX` (global) | `±0.05` | `±0.05` global; consider per-class for queen | class-effect collapse on score | **keep global** |
| Per-class achievable_score_gap | 3.4.2 | `PER_CLASS_GAUGE_ZONES[*].achievable_score_gap` (6 entries) | various | all within ±0.5pp of measured | TC collapse, ELO mixed | **keep all 6** |
| Global type-gap default | 3.4.2 | `ZONE_REGISTRY["endgame_type_achievable_score_gap"]` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | both review | **keep** |
| EG Type chart inventory | 3.4.3 | `EndgameTypeCard.tsx` layout | Score + Gap + Conv + Recov + WDL | **Keep all 3 signals** (r=0.10, agreement~indep) | n/a | **keep layout** (no constant) |

---

## Cross-snapshot diff (2026-05-24 → 2026-05-27)

- **Cohort doubled** in nearly every cell (selection target raised 100/cell → 200/cell). Pool exhaustion confirmed only for `(800, classical)` (151) and `(2400, classical)` (12).
- **Most live constants survive**: the doubled cohort confirmed the 2026-05-24 calibration. Of ~30 calibration targets, ~26 stay unchanged.
- **Concrete updates surfaced this snapshot**:
  - Pressure-bin: 4 cells widen (bullet Q1/Q2/Q3, blitz Q2) as more samples populate the IQR tails.
  - Pawnless class: +4pp conv, −6pp recov drift — but n=243 (smallest class), apply cautiously.
- **Achievable Score Gap ELO Cohen's d** dropped from 0.62 (keep) → 0.34 (review) — the previous tail-driven verdict relaxes with more data.
- **Section-2 ΔES bands** (conv/parity/recov): all three match the 2026-05-15 calibration exactly. No drift.

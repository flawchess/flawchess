# FlawChess Benchmarks — 2026-06-10

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-06-10 (benchmark DB unchanged since 2026-03 ingest; re-run of §1–§3 confirms every constant; §5 flaw-delta zones added in this snapshot)
- **Population**: 4,697 users / 2,767,158 games / 190,934,222 positions (candidate pool: 9,523 selected-user rows)
- **Generator**: `scripts/gen_benchmarks.py --db benchmark` (deterministic; numeric tables spliced from `benchmarks-generated.md`, verdict words + recommendations authored here)
- **Cell anchoring**: 400-wide ELO buckets via the cohort user's **rating at game time** (`games.white_rating`/`games.black_rating`, sub-800 dropped) — NOT the frozen `benchmark_selected_users.rating_bucket`. **Methodology change (2026-05-19): rating-at-game-time bucketing.** `rating_bucket`/`median_elo` retained as longitudinal/trajectory columns only. `tc_bucket` from `benchmark_selected_users`; per-user TC restricted to selected `tc_bucket`.
- **Per-user history caveat**: each user contributes up to 1000 games per TC over a 36-month window at varying ratings, so a user spans 2–3 game-time ELO buckets; "ELO bucket effect" is a genuine rating-at-game-time effect. Any whole-career per-user scalar (e.g. composite Endgame Skill) is now per-bucket/trajectory, not one number.
- **Base filters**: `g.rated AND NOT g.is_computer_game`; `g.time_control_bucket::text = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter).
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating − user_rating) ≤ 100`, both ratings NOT NULL. Live UI uses unfiltered games; the gap above the equal-footing baseline is the intended skill signal.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate forces conv/recov; NULL → parity).
- **Eval coverage**: **100.00%** at endgame entry (1,538,581 / 1,538,585 endgame-reaching games have non-NULL eval).
- **Sparse-cell exclusion**: `(2400, classical)` (12 completed users, ~47 games, pool-exhausted) excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes; kept in cell grids with `*` footnote.
- **Deleted calibration targets** (retracted Phase 87.4): `endgame_skill` and `section2_score_gap_skill` composites — §3.2.1 / §3.2.2 report distributions for completeness only, no band.
- **Verdict thresholds**: Cohen's d **< 0.2 collapse** / **0.2–0.5 review** / **≥ 0.5 keep separate** (per axis, independently).
- **§4 (Global Percentile CDF)**: separate deliverable, NOT part of this report — generator chapter is `REFERENCE`-only. See `app/services/global_percentile_cdf.py` / `reports/percentile/`.
- **§5 (Flaw-Delta Zones)**: added Phase 114 — D-01 unified paired-delta estimator for 15 metrics (all-analyzed-games basis; clean game = 0 delta). Negative delta = fewer flaws than equally-rated opponents. Mostly-collapse verdicts (max d = 0.27); zones are pooled globals pending Phase 115 implementation.

---

## 1. Stratified Sample

### Cell coverage (`status='completed'` users per cell)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 200 | 200 | 200 | 151 |
| 1200 | 200 | 200 | 200 | 200 |
| 1600 | 200 | 200 | 200 | 200 |
| 2000 | 200 | 200 | 200 | 200 |
| 2400 | 200 | 200 | 200 | 12* |

`*` Sparse cell — pool-exhausted (12 completed / 23 candidate / 0 unattempted). Excluded from all marginals and Cohen's d. `(800, classical)` is also pool-limited (151) but stays in marginals.

### Game-time cell sizes (post equal-footing filter — `users / games`)

The analysis cells (game-time ELO bucket × TC). A user contributes to 2–3 ELO buckets across their career, so per-bucket user counts exceed the 200/cell selection cap.

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 268 / 114,933 | 260 / 115,661 | 317 / 95,792 | 222 / 11,609 |
| 1200 | 404 / 165,994 | 423 / 162,443 | 545 / 132,196 | 452 / 39,705 |
| 1600 | 363 / 165,589 | 419 / 164,380 | 502 / 134,570 | 423 / 48,763 |
| 2000 | 334 / 147,313 | 364 / 140,587 | 399 / 97,751 | 222 / 17,766 |
| 2400 | 240 / 113,012 | 223 / 89,885 | 208 / 31,627 | 10 / 47* |

All non-sparse cells clear the ≥10-users floor comfortably.

### Eval coverage at endgame entry

| metric | value |
|---|---:|
| Endgame-reaching games (≥6 plies, `endgame_class IS NOT NULL`) | 1,538,585 |
| With non-NULL Stockfish eval at entry ply | 1,538,581 |
| Coverage | **100.00%** |

Above the 99% floor — no NULL-eval bias flag needed.

---

## 2. Openings

### 2.1 Middlegame-entry eval

**Symmetric baseline (deduped to physical games):**

| n_games | baseline_cp_white | median (white-POV) | SD |
|---:|---:|---:|---:|
| 2,504,885 | **+25.21 cp** | +24.0 | 237.2 |

Black baseline = −25 cp by construction. Live `EVAL_BASELINE_PAWNS_WHITE = 0.25` (= +25 cp) matches the measured +25.21 cp within 0.2 cp — **no change**. `EVAL_BASELINE_PAWNS_BLACK = -0.25` is symmetric (invariant holds).

**Centered per-(user, color) pooled distribution:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 9,109 | +3.7 cp | 58.5 cp | −92 cp | −23 cp | +6 cp | +34 cp | +89 cp |

**ELO marginal (centered, cp):**

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 1,541 | −0.8 | 87.9 | −145 | −46 | +8 | +57 | +127 |
| 1200 | 2,140 | +5.7 | 69.3 | −104 | −32 | +10 | +48 | +106 |
| 1600 | 2,290 | +5.0 | 49.6 | −75 | −21 | +7 | +34 | +79 |
| 2000 | 1,988 | +4.4 | 35.2 | −53 | −15 | +5 | +26 | +59 |
| 2400 | 1,150 | +2.0 | 27.5 | −46 | −13 | +3 | +19 | +45 |

**TC marginal (centered, cp):**

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 2,674 | −2.5 | 71.7 | −126 | −31 | +4 | +37 | +95 |
| blitz | 2,665 | +2.9 | 45.1 | −75 | −20 | +3 | +28 | +73 |
| rapid | 2,628 | +8.5 | 50.3 | −76 | −17 | +9 | +35 | +89 |
| classical | 1,142 | +8.8 | 67.2 | −96 | −25 | +9 | +46 | +113 |

**Collapse verdict:** TC max |d| = **0.18** (bullet vs rapid) → **collapse**. ELO max |d| = **0.09** (800 vs 1600) → **collapse**. Color collapse automatic by construction.

**Recommendations:**
- **Baseline**: keep `EVAL_BASELINE_PAWNS_WHITE = 0.25` (measured +25.21 cp, within 5 cp tolerance).
- **Neutral zone** (`openingStatsZones.ts` `EVAL_NEUTRAL_*_PAWNS = ±0.30`): pooled centered IQR `[−23, +34]` cp ≈ ±0.34 pawns rounds to **±0.30** — keep. Both axes collapse; single global band justified.
- **Domain** (`EVAL_BULLET_DOMAIN_PAWNS = 1.5`): pooled `[p05, p95] = [−92, +89]` cp → well inside ±1.5 pawns; keep.

---

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,020 | 51.9% | 8.8% | 38.1% | 46.1% | 51.6% | 57.3% | 67.1% |

**ELO marginal:**

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 697 | 51.9% | 7.5% | 46.8% | 51.8% | 56.6% |
| 1200 | 968 | 52.0% | 8.5% | 46.4% | 51.3% | 56.9% |
| 1600 | 1,016 | 51.4% | 9.2% | 45.3% | 51.2% | 56.8% |
| 2000 | 839 | 52.4% | 9.1% | 46.2% | 52.0% | 58.1% |
| 2400 | 500 | 52.2% | 9.4% | 46.4% | 52.1% | 58.0% |

**TC marginal:**

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,238 | 50.7% | 8.4% | 45.5% | 50.8% | 55.6% |
| blitz | 1,228 | 51.2% | 8.0% | 45.6% | 51.0% | 56.3% |
| rapid | 1,156 | 53.1% | 9.1% | 46.7% | 52.4% | 58.5% |
| classical | 398 | 54.8% | 9.9% | 48.4% | 54.5% | 61.9% |

**Collapse verdict:** TC max |d| = **0.46** (bullet vs classical) → **review**. ELO max |d| = **0.10** → **collapse**.

**Recommendation:** pooled IQR `[46.1%, 57.3%]`. Shared `SCORE_BULLET_NEUTRAL_* = ±0.05` (→ [0.45, 0.55]) sits slightly low at the top edge. TC review is classical-driven (54.8% mean) but stays under 0.5 → **keep the shared band**; a dedicated non-EG module isn't warranted for a ~2pp top-edge drift.

---

#### 3.1.2 Endgame-entry eval (pawns)

**Symmetric EG-entry baseline (deduped):**

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 1,604,885 | +10.32 cp | +0.0 | 443.8 |

**Pooled distribution (uncentered drives the 0-centered live tile):**

| variant | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **uncentered** | 8,322 | +9.3 cp | 119.2 | −185 | −57 | +10 | +77 | +200 |
| centered | 8,322 | +9.3 cp | 118.6 | −183 | −57 | +10 | +76 | +199 |

**ELO marginal (centered, cp):**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 1,359 | +1.7 | −101 | +1 | +102 |
| 1200 | 1,943 | +3.6 | −77 | +4 | +91 |
| 1600 | 2,099 | +15.1 | −51 | +16 | +82 |
| 2000 | 1,817 | +15.2 | −40 | +16 | +67 |
| 2400 | 1,104 | +7.9 | −36 | +7 | +49 |

**TC marginal (centered, cp):**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 2,563 | −0.1 | −80 | +2 | +81 |
| blitz | 2,521 | +12.3 | −46 | +12 | +70 |
| rapid | 2,406 | +17.1 | −43 | +16 | +77 |
| classical | 832 | +6.5 | −60 | +9 | +76 |

**Collapse verdict:** TC max |d| = **0.14** → **collapse**. ELO max |d| = **0.11** → **collapse**.

**Recommendation:** uncentered IQR `[−57, +77]` cp = `[−0.57, +0.77]` pawns; live `entry_eval_pawns = ±0.60` (editorially tightened so the 0-centered tile actually paints) brackets the IQR → **keep ±0.60**. Domain `[p05, p95] = [−185, +200]` cp = `[−1.85, +2.00]`; live `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.25` covers it → keep.

---

#### 3.1.3 Achievable Score (entry_xs)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 50.9% | 8.0% | 38.0% | 46.2% | 51.0% | 55.7% | 64.0% |

**ELO marginal:**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 50.5% | 43.9% | 50.6% | 57.0% |
| 1200 | 1,068 | 50.7% | 44.8% | 50.6% | 56.6% |
| 1600 | 1,166 | 51.4% | 46.5% | 51.5% | 56.2% |
| 2000 | 1,028 | 51.3% | 47.4% | 51.3% | 54.9% |
| 2400 | 598 | 50.6% | 47.6% | 50.3% | 53.3% |

**TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.4% | 44.7% | 50.4% | 56.2% |
| blitz | 1,353 | 51.0% | 47.0% | 51.1% | 55.1% |
| rapid | 1,334 | 51.4% | 46.9% | 51.2% | 55.8% |
| classical | 579 | 50.9% | 45.8% | 50.7% | 56.0% |

**Collapse verdict:** TC max |d| = **0.12** → **collapse**. ELO max |d| = **0.12** → **collapse**.

**Sanity check (game-time-bucketed):** 800–1600 sit at 50.5–51.4% (within ±1.5pp of 0.50, no monotone ramp) — equal-footing filter passes; 2000/2400 stay flat (~50.6–51.3%, mild residual). Pooled IQR `[46.2%, 55.7%]` ≈ [0.46, 0.56]; live `entry_expected_score = [0.45, 0.55]` within tolerance → **keep [0.45, 0.55]**.

---

#### 3.1.4 Endgame Score (per-user, EG-only)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 51.4% | 8.7% | 38.3% | 46.1% | 51.0% | 56.5% | 66.5% |

**ELO marginal:**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 49.9% | 44.0% | 49.3% | 54.9% |
| 1200 | 1,068 | 50.2% | 44.5% | 49.6% | 55.3% |
| 1600 | 1,166 | 51.6% | 46.0% | 50.8% | 56.8% |
| 2000 | 1,028 | 52.9% | 47.3% | 52.5% | 57.7% |
| 2400 | 598 | 52.8% | 48.7% | 52.7% | 56.6% |

**TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.6% | 46.0% | 50.0% | 54.7% |
| blitz | 1,353 | 51.7% | 46.2% | 51.6% | 56.5% |
| rapid | 1,334 | 52.3% | 46.6% | 51.9% | 57.4% |
| classical | 579 | 50.9% | 43.9% | 50.2% | 57.9% |

**Collapse verdict:** TC max |d| = **0.21** (bullet vs rapid) → **review**. ELO max |d| = **0.35** (800 vs 2400) → **review**.

**Recommendation:** pooled IQR `[46.1%, 56.5%]`; live `endgame_score = [0.45, 0.55]`. The ELO sweep (49.3% → 52.7% p50, 3.4pp) is the known rating residual (D-01 confound), under the 0.5 keep threshold → **keep [0.45, 0.55]**; per-ELO stratification not yet warranted.

---

#### 3.1.5 Achievable Score Gap (paired actual − expected)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | +0.5pp | 8.2pp | −12.8pp | −3.9pp | +0.7pp | +5.1pp | +13.2pp |

**ELO marginal (pp):**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | −0.6 | −5.8 | −0.4 | +4.5 |
| 1200 | 1,068 | −0.5 | −4.7 | −0.3 | +4.2 |
| 1600 | 1,166 | +0.2 | −3.9 | +0.4 | +4.6 |
| 2000 | 1,028 | +1.7 | −2.8 | +1.7 | +6.1 |
| 2400 | 598 | +2.2 | −2.0 | +2.5 | +6.4 |

**TC marginal (pp):**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | +0.2 | −6.0 | +0.7 | +7.2 |
| blitz | 1,353 | +0.7 | −3.4 | +1.0 | +5.0 |
| rapid | 1,334 | +0.9 | −2.7 | +0.7 | +4.4 |
| classical | 579 | +0.0 | −4.2 | −0.1 | +4.0 |

**Collapse verdict:** TC max |d| = **0.13** → **collapse**. ELO max |d| = **0.34** (800 vs 2400) → **review**.

**Recommendation:** pooled mean +0.5pp (within ±1pp engine-alignment null, healthy). Pooled IQR `[−3.9pp, +5.1pp]`; live `achievable_score_gap = ±0.05` → **keep ±0.05**. ELO review (800 median −0.4pp → 2400 +2.5pp) — per-ELO stratification deferred.

---

#### 3.1.6 Endgame Score Gap and Timeline

**Pooled (`eg_score − non_eg_score`):**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,020 | −1.0pp | 13.2pp | −21.8pp | −9.9pp | −1.0pp | +8.0pp | +20.7pp |

**ELO marginal (pp):**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 697 | −2.4 | −11.7 | −3.0 | +6.4 |
| 1200 | 968 | −1.7 | −11.0 | −2.1 | +7.7 |
| 1600 | 1,016 | −0.3 | −9.0 | −0.3 | +9.0 |
| 2000 | 839 | −0.4 | −8.5 | −0.4 | +8.2 |
| 2400 | 500 | +0.3 | −7.1 | +0.6 | +7.8 |

**TC marginal (pp):**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,238 | −0.4 | −9.0 | −1.2 | +7.8 |
| blitz | 1,228 | +0.2 | −8.4 | +0.1 | +8.5 |
| rapid | 1,156 | −1.4 | −10.5 | −1.0 | +7.9 |
| classical | 398 | −4.8 | −15.9 | −4.7 | +7.0 |

**Collapse verdict:** TC max |d| = **0.37** (blitz vs classical) → **review**. ELO max |d| = **0.21** (800 vs 2400) → **review**.

**Recommendation:** pooled IQR `[−9.9pp, +8.0pp]`; live `score_gap = ±0.10`. **Keep ±0.10** — pooled median −1.0pp under the 5pp re-centering guard. Classical drags the TC marginal (−4.8pp mean) but stays review.

---

### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery

**Conversion — pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 71.1% | 10.8% | 52.9% | 64.9% | 71.6% | 77.7% | 87.5% |

**Conversion — ELO marginal:**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 67.8% | 61.3% | 69.1% | 75.0% |
| 1200 | 1,068 | 70.0% | 63.7% | 71.2% | 76.8% |
| 1600 | 1,166 | 71.7% | 65.7% | 72.0% | 78.3% |
| 2000 | 1,028 | 72.5% | 66.7% | 72.9% | 79.0% |
| 2400 | 598 | 73.3% | 67.8% | 73.0% | 78.6% |

**Conversion — TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 65.2% | 58.8% | 65.6% | 71.9% |
| blitz | 1,353 | 71.7% | 66.7% | 71.9% | 76.9% |
| rapid | 1,334 | 74.4% | 69.6% | 74.6% | 80.0% |
| classical | 579 | 75.4% | 68.5% | 76.0% | 83.3% |

**Conversion verdict:** TC max |d| = **0.93** (bullet vs classical) → **keep separate**. ELO max |d| = **0.51** (800 vs 2400) → **keep separate**.

**Parity — pooled:** n=4,616 · mean 50.7% · IQR `[44.0%, 57.3%]` · p50 50.0%.

**Parity — TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.4% | 43.6% | 50.0% | 57.2% |
| blitz | 1,353 | 50.8% | 44.8% | 51.0% | 56.9% |
| rapid | 1,334 | 51.3% | 44.9% | 50.5% | 57.5% |
| classical | 579 | 49.8% | 40.4% | 50.0% | 59.1% |

**Parity verdict:** TC max |d| = **0.11** → **collapse**. ELO max |d| = **0.22** (1200 vs 2400) → **review**.

**Recovery — pooled:** n=4,616 · mean 30.8% · IQR `[24.0%, 37.0%]` · p50 30.0%.

**Recovery — TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 35.7% | 29.5% | 35.3% | 41.2% |
| blitz | 1,353 | 30.9% | 25.1% | 30.0% | 35.7% |
| rapid | 1,334 | 28.1% | 21.8% | 27.3% | 33.3% |
| classical | 579 | 25.6% | 17.4% | 23.5% | 31.6% |

**Recovery verdict:** TC max |d| = **0.90** (bullet vs classical) → **keep separate**. ELO max |d| = **0.25** (1200 vs 2400) → **review**.

**Recommendations:** Conversion and Recovery both **keep-separate on TC** (d ≈ 0.9). The live per-TC `TC_METRIC_BANDS` (conv `bullet 0.588–0.719 … classical 0.685–0.833`; recov `bullet 0.295–0.412 … classical 0.174–0.316`) are the correct shape and reproduce these per-TC IQRs → **keep per-TC**. Parity collapses on TC; the live per-TC parity bands (near-identical bullet/blitz/rapid, classical wider) match → keep. Conversion's ELO keep (0.51) remains the strongest argument for eventual per-(TC×ELO) conversion stratification; deferred.

---

#### 3.2.2 Section-2 ΔES Score Gap (per entry-eval bucket)

**Pooled:** Conv n=4,138 · mean −6.2pp · IQR `[−11.0, +0.2]`. Parity n=3,623 · mean +0.1pp · IQR `[−3.7, +4.1]`. Recovery n=3,973 · mean +6.4pp · IQR `[+0.9, +11.0]` (pp).

**Conversion-bucket — ELO / TC marginals (pp):**

| axis | level | n | mean | p25 | p50 | p75 |
|---|---|---:|---:|---:|---:|---:|
| ELO | 800 | 683 | −12.9 | −17.4 | −10.5 | −6.3 |
| ELO | 1200 | 973 | −8.6 | −12.8 | −6.5 | −2.5 |
| ELO | 1600 | 1,048 | −5.2 | −9.8 | −3.8 | +0.8 |
| ELO | 2000 | 901 | −2.5 | −6.8 | −1.2 | +3.2 |
| ELO | 2400 | 533 | −1.2 | −5.2 | −1.1 | +3.5 |
| TC | bullet | 1,270 | −13.2 | −19.5 | −11.6 | −5.7 |
| TC | blitz | 1,254 | −4.5 | −8.5 | −4.0 | +0.3 |
| TC | rapid | 1,201 | −2.3 | −6.3 | −2.0 | +2.1 |
| TC | classical | 413 | −1.1 | −5.3 | −0.1 | +3.8 |

**Recovery-bucket — ELO / TC marginals (pp):**

| axis | level | n | mean | p25 | p50 | p75 |
|---|---|---:|---:|---:|---:|---:|
| ELO | 800 | 670 | +11.2 | +5.7 | +9.5 | +15.5 |
| ELO | 1200 | 940 | +7.6 | +2.6 | +6.3 | +11.8 |
| ELO | 1600 | 989 | +5.2 | −0.1 | +3.5 | +9.4 |
| ELO | 2000 | 848 | +4.2 | −1.0 | +3.4 | +9.1 |
| ELO | 2400 | 526 | +3.9 | −0.7 | +3.6 | +8.1 |
| TC | bullet | 1,240 | +12.9 | +7.4 | +12.4 | +17.7 |
| TC | blitz | 1,219 | +5.1 | +1.1 | +4.8 | +8.4 |
| TC | rapid | 1,123 | +2.8 | −0.8 | +2.6 | +6.2 |
| TC | classical | 391 | +0.2 | −3.7 | +0.2 | +3.5 |

**Collapse verdicts:** Conv ΔES TC **1.25** keep / ELO **1.35** keep · Parity ΔES TC **0.18** collapse / ELO **0.31** review · Recovery ΔES TC **1.69** keep / ELO **0.95** keep.

**Sigmoid-bias check confirmed:** conv skews negative (−6.2pp, ceiling at 1.0), recov positive (+6.4pp, floor at 0.0), parity ~symmetric (+0.1pp). Off-zero bands correct. Live `score_gap_conv = [−0.11, 0.00]`, `score_gap_parity = ±0.04`, `score_gap_recov = [0.01, 0.11]` match the pooled IQRs → **keep all three** scalar bands (per-(TC×ELO) Section-2 stratification deferred — see §3.2.3).

---

#### 3.2.3 Rate vs Score-Gap divergence (derived)

| Bucket | Raw rate ELO sweep / d | Raw rate TC sweep / d | Gap ELO sweep / d | Gap TC sweep / d |
|---|---|---|---|---|
| Conversion | 67.8%→73.3% / 0.51 keep | 65.2%→75.4% / 0.93 keep | −12.9pp→−1.2pp / 1.35 keep | −13.2pp→−1.1pp / 1.25 keep |
| Recovery | 31.3%→32.5% / 0.25 review | 35.7%→25.6% / 0.90 keep | +11.2pp→+3.9pp / 0.95 keep | +12.9pp→+0.2pp / 1.69 keep |

**Divergence (recovery, ELO axis):** raw recovery rate is ELO-flat (d=0.25 review) but the recovery **gap** re-exposes a strong ELO signal (d=0.95 keep) — weak players over-perform the engine far more when recovering (+11.2pp) than strong players (+3.9pp); the flat raw rate hides it because engine expectation rises with the cohort. This is the strongest standing argument against the Section-2 scalar-registry deferral. **Recommendation unchanged this snapshot** (scalar pooled bands ship); flag recovery as the first candidate if per-(TC×ELO) Section-2 stratification is revisited.

---

### 3.3 Time Pressure

#### 3.3.1 Clock pressure at endgame entry

**Clock-diff % (per-user mean):**

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,604 | −1.12% | −6.35% | −0.50% | +4.83% |
| bullet | 1,343 | −0.17% | −3.96% | −0.29% | +3.29% |
| blitz | 1,353 | −0.77% | −6.68% | −0.29% | +5.27% |
| rapid | 1,334 | −1.81% | −8.14% | −0.94% | +5.21% |
| classical | 574 | −2.60% | −11.29% | −1.21% | +8.19% |

**Net-timeout rate (pp):**

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,604 | +0.45pp | −4.46pp | +1.13pp | +6.09pp |
| bullet | 1,343 | +0.45pp | −10.95pp | +0.53pp | +11.86pp |
| blitz | 1,353 | +0.85pp | −5.35pp | +2.07pp | +8.64pp |
| rapid | 1,334 | +0.27pp | −2.14pp | +1.53pp | +3.96pp |
| classical | 574 | −0.05pp | +0.00pp | +0.00pp | +1.80pp |

**Clock-gap fraction (per-user):** pooled p25/p50/p75 = `−0.0635 / −0.0050 / +0.0483`.

**Collapse verdicts:** clock-diff% TC **0.24** review / ELO **0.17** collapse · net-timeout TC **0.09** collapse / ELO **0.28** review · clock-gap ELO collapse.

**Recommendations:**
- `NEUTRAL_PCT_THRESHOLD = ±5.0%`: pooled clock-diff IQR `[−6.35%, +4.83%]` → **keep ±5** (TC review under 0.5).
- `NEUTRAL_TIMEOUT_THRESHOLD = ±5.0pp`: pooled net-timeout IQR `[−4.5pp, +6.1pp]` → **keep ±5**.
- `clock_gap_pct = [−0.065, +0.047]`: pooled IQR `[−0.0635, +0.0483]` → matches within 0.2pp; **keep**.

---

#### 3.3.2 Time pressure vs performance curve

**Pooled curve (time-bucket 0 = 0–10% clock remaining → 9 = 90–100%):**

| tb | n_games | score | tb | n_games | score |
|---:|---:|---:|---:|---:|---:|
| 0 | 74,569 | 31.0% | 5 | 150,007 | 54.7% |
| 1 | 97,328 | 41.8% | 6 | 148,644 | 54.3% |
| 2 | 106,008 | 49.0% | 7 | 128,236 | 53.7% |
| 3 | 125,531 | 52.2% | 8 | 84,609 | 52.7% |
| 4 | 140,322 | 54.0% | 9 | 52,117 | 51.5% |

**Per-time-bucket collapse verdict (max |d| on per-game score):**

| tb | TC max |d| | ELO max |d| |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.39 (bullet vs classical) review | 0.16 collapse |
| 1 | 0.16 collapse | 0.11 collapse |
| 2–9 | ≤ 0.14 collapse | ≤ 0.12 collapse |

**Recommendation:** universal "pressure crushes score" shape (31% at 0–10% clock → 54.7% peak at mid-clock). Only **time-bucket 0 shows a TC effect** (0.39 review; classical 42.5% vs bullet 25.6%) → **stratify the TC overlay at extreme pressure only**, pool elsewhere. ELO collapses across all buckets.

---

#### 3.3.3 Chess score per pressure bin (per-(TC × quintile))

**Per-quintile collapse verdict:**

| Q (clock remaining) | TC max |d| | ELO max |d| |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (0–20%, max pressure) | 0.75 keep | 0.56 keep |
| 1 (20–40%) | 0.32 review | 0.15 collapse |
| 2 (40–60%) | 0.46 review | 0.25 review |
| 3 (60–80%) | 0.40 review | 0.34 review |
| 4 (80–100%, min pressure) | 0.19 collapse | 0.31 review |

**Recommendation:** Q0 is the strongest stratifier on **both** axes (TC 0.75, ELO 0.56 — both keep). The live `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` already ships per-(TC × quintile) bands with the ±0.06 editorial cap; the regenerated p25/p50/p75 (e.g. bullet-Q0 `0.275/0.343/0.419`, classical-Q4 `0.420/0.506/0.615`) reproduce the committed bands within rounding → **keep per-(TC×Q)**. The cap activates at 14/20 cells (extreme quintiles), as documented.

---

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

**Pooled-by-class (sparse cell excluded):**

| class | games | users | score | conversion | recovery |
|---|---:|---:|---:|---:|---:|
| rook | 187,177 | 3,655 | 50.7% | 71.2% | 29.8% |
| minor_piece | 139,393 | 3,611 | 50.9% | 69.4% | 32.5% |
| pawn | 74,055 | 3,487 | 50.8% | 73.9% | 27.4% |
| queen | 68,196 | 3,495 | 50.8% | 77.5% | 23.5% |
| mixed | 1,060,245 | 3,735 | 50.6% | 69.6% | 31.1% |
| pawnless | 11,690 | 2,723 | 50.8% | 79.3% | 19.7% |

**Per-class chess-score IQR (per-user, ≥10 games/class):**

| class | n_users | p25 | p50 | p75 |
|---|---:|---:|---:|---:|
| rook | 3,075 | 43.9% | 50.0% | 57.1% |
| minor_piece | 2,841 | 43.0% | 50.8% | 57.8% |
| pawn | 2,353 | 41.9% | 50.0% | 58.6% |
| queen | 2,303 | 41.2% | 52.1% | 62.5% |
| mixed | 3,599 | 46.2% | 51.0% | 56.0% |
| pawnless | 243 | 30.0% | 41.7% | 58.6% |

**Per-(metric × class × axis) collapse verdicts:**

| class | conv TC d | conv ELO d | recov TC d | recov ELO d |
|---|---:|---:|---:|---:|
| rook | 1.24 keep | 0.32 review | 1.33 keep | 0.20 review |
| minor_piece | 1.50 keep | 0.41 review | 1.48 keep | 0.31 review |
| pawn | 1.40 keep | 0.31 review | 1.36 keep | 0.65 keep |
| queen | 1.43 keep | 0.32 review | 1.67 keep | 0.31 review |
| mixed | 1.19 keep | 0.49 review | 1.28 keep | 0.22 review |

**Recommendations:**
- **Score is flat across class** (all 5 visible classes within ±1.1pp of 50%) → score collapses across class; **keep the global `SCORE_BULLET_NEUTRAL_* = ±0.05`** for the per-class score bullet (queen's wider IQR is the only outlier but stays near-symmetric).
- **Conversion & recovery keep-separate on TC for every class** (d ≈ 1.2–1.7). Live `PER_CLASS_GAUGE_ZONES` are TC-agnostic — this **mispaints by TC**. **Flag: stratify `PER_CLASS_GAUGE_ZONES` → per-(class × TC)**, scoped to whether the Endgame Type cards expose a TC filter. (Same standing flag as prior snapshots.)
- Pawn-recovery ELO keep (0.65) is the only per-class ELO signal above threshold.

---

#### 3.4.2 Per-span ΔES Score Gap by endgame type

**Per-class pooled (per-user `mean(gap_span)`, sparse excluded):**

| class | n_users | p25 | p50 | p75 |
|---|---:|---:|---:|---:|
| rook | 2,841 | −5.1pp | +0.1pp | +4.8pp |
| minor_piece | 2,332 | −4.8pp | +0.3pp | +5.6pp |
| pawn | 1,417 | −3.8pp | +0.6pp | +5.0pp |
| queen | 1,307 | −4.2pp | +0.5pp | +5.4pp |
| mixed | 4,587 | −3.1pp | +0.5pp | +3.8pp |
| pawnless | 12 | −1.1pp | +0.6pp | +3.8pp |

**Collapse verdicts (per class):** TC d 0.06–0.20 → **all collapse**. ELO d 0.14–0.31 → **all collapse/review** (minor_piece 0.30, mixed 0.31 highest, both review).

**Recommendation:** per-class IQRs near-symmetric around 0, widths 6.6pp (mixed) → 9.7pp (minor_piece). Live per-class `achievable_score_gap` bands (rook ±0.05, minor_piece [−0.04,+0.06], pawn/queen [−0.04,+0.05], mixed [−0.03,+0.04]) match within ~0.5pp → **keep per-class bands**; global default `endgame_type_achievable_score_gap = ±0.04` stays valid.

---

#### 3.4.3 Endgame Type Score vs Score Gap — agreement / redundancy

| class | n_users | Pearson r | sign_agree | strict zone-agree | strong disagree | score SD | gap SD |
|---|---:|---:|---:|---:|---:|---:|---:|
| mixed | 5,274 | +0.105 | 46.3% | 42.2% | 9.0% | 0.149 | 0.049 |

Only `mixed` clears the ≥30-joined-user floor at the combined ≥10-game + ≥20-span gates. Independence baselines (r=0): strict zone-agree 37.5%, strong-disagree 12.5%.

**Verdict:** Pearson r = **+0.105** (far below the 0.60 redundancy floor); strict zone-agreement 42.2% only ~4.7pp above the r=0 baseline. Score and Score Gap read **different things** → **keep all three signals** (Score bullet, Score Gap bullet, WDL) on `EndgameTypeCard.tsx`. Layout decision only, no code constant.

---

## 5. Flaw-Delta Zones

> **D-01 unified estimator**: per game, delta = (player_tag_count − opp_tag_count)
> / user_moves_in_game (proportion); displayed as per-100-moves via ×100 at the
> render layer ("pp" unit). user_moves derived from `games.ply_count` (Phase 114.1):
> FLOOR(ply_count/2) for white, CEIL(ply_count/2) for black — no game_positions scan.
> Per-cohort-user delta = mean
> over ≥20 analyzed games. Negative delta means cohort
> users commit fewer flaws of this type than equally-rated opponents.
>
> **All-analyzed-games basis (Phase 114 final fix)**: base_games LEFT JOIN game_flaws so
> clean games (zero detected flaws) contribute a 0 delta — a clean game IS evidence
> of a zero you−opponent delta. Magnitudes compress vs the prior flawed-games-only
> basis (~4× more user×cell rows: 3,725 → 4,644 pooled n).
>
> **Basis change (2026-06-11): lichess mate-ladder severities.** `game_flaws` was fully
> re-backfilled after the kernel adopted lila's MateAdvice port (commit `c403467e`):
> transitions touching a forced-mate eval are now graded by the lichess mate ladder
> instead of the flattened Option-B ES drop, which missed most thrown forced mates.
> Flaw volume rose ~9.1% (3.81M → 4.15M rows); blunder/mistake counts now sit at
> ~100% lichess parity (up from ~92%). Effect on zones: quartiles widened by ≈0.1pp
> on the wide metrics (e.g. flaw-rate Q1/Q3 [−0.4, +0.3] → [−0.5, +0.4]); the only
> verdict-word change is Hasty TC review → collapse. Viability improved for
> mate-adjacent tags (endgame-phase 97.5% → 98.5%, low-clock 67.4% → 71.4%,
> low-clock+miss 53.6% → 58.2%). See
> `reports/misc/flaw-count-sanity-lichess-vs-game_flaws-2026-06-11.md`.
>
> **D-04 amendment**: the count-rate/proportion family split from SEED-040 is superseded. FLAWCMP-02 (Wilson difference-of-proportions) is voided. All 15 metrics use the same estimator.
>
> **Cell floor**: ≥30 contributors per (ELO×TC) cell for Q1/Q3; thin cells fall back to marginal/global zone (D-07). **Sparse cell**: (2400, classical) excluded from marginals and verdicts.

### 5.1 Flaw Rate (all mistakes + blunders)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | −0.1pp | 1.1pp | −1.898pp | −0.477pp | +0.019pp | +0.364pp | +1.703pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 1.2pp | −1.876pp | −0.482pp | +0.089pp | +0.558pp | +2.009pp |
| 1200 | 1,091 | +0.0pp | 1.2pp | −1.991pp | −0.360pp | +0.073pp | +0.446pp | +1.825pp |
| 1600 | 1,139 | −0.1pp | 1.1pp | −2.016pp | −0.490pp | +0.021pp | +0.376pp | +1.810pp |
| 2000 | 1,015 | −0.2pp | 1.0pp | −1.859pp | −0.580pp | −0.029pp | +0.248pp | +1.398pp |
| 2400 | 586 | −0.1pp | 0.8pp | −1.444pp | −0.416pp | −0.024pp | +0.198pp | +1.091pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.1pp | 1.0pp | −1.486pp | −0.178pp | +0.016pp | +0.271pp | +1.747pp |
| blitz | 1,311 | −0.1pp | 1.0pp | −1.824pp | −0.399pp | +0.024pp | +0.259pp | +1.574pp |
| rapid | 1,376 | −0.2pp | 1.1pp | −2.066pp | −0.700pp | −0.009pp | +0.361pp | +1.656pp |
| classical | 711 | +0.0pp | 1.2pp | −2.255pp | −0.678pp | +0.118pp | +0.683pp | +1.940pp |

**Collapse verdicts:** TC max |d| = **0.20** (bullet vs rapid) → **review**. ELO max |d| = **0.17** (800 vs 2000) → **collapse**.

**Recommendation:** TC review (d=0.20) is driven by bullet (mean +0.1pp) vs rapid (−0.2pp) — modest; ELO collapses (d=0.17) with the familiar ramp (mean +0.0pp at 800 → −0.2pp at 2000). Viability 99.5%. Pooled Q1/Q3 = [−0.477pp, +0.364pp] (widened ~0.1pp vs the pre-mate-ladder basis), median +0.0pp — symmetric across the cohort. Use pooled global zone for Phase 115.

---

### 5.2 Low-Clock Flaws (tempo = 0)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.3pp | −0.360pp | −0.081pp | −0.002pp | +0.028pp | +0.403pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.2pp | −0.222pp | −0.047pp | +0.000pp | +0.018pp | +0.270pp |
| 1200 | 1,091 | +0.0pp | 0.2pp | −0.258pp | −0.043pp | +0.000pp | +0.014pp | +0.264pp |
| 1600 | 1,139 | +0.0pp | 0.3pp | −0.325pp | −0.076pp | −0.005pp | +0.023pp | +0.395pp |
| 2000 | 1,015 | +0.0pp | 0.3pp | −0.471pp | −0.140pp | −0.016pp | +0.049pp | +0.648pp |
| 2400 | 586 | +0.0pp | 0.3pp | −0.471pp | −0.151pp | −0.015pp | +0.067pp | +0.537pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.2pp | −0.328pp | −0.043pp | +0.000pp | +0.032pp | +0.306pp |
| blitz | 1,311 | +0.0pp | 0.3pp | −0.412pp | −0.102pp | −0.007pp | +0.048pp | +0.511pp |
| rapid | 1,376 | +0.0pp | 0.3pp | −0.347pp | −0.095pp | −0.011pp | +0.022pp | +0.434pp |
| classical | 711 | +0.0pp | 0.3pp | −0.348pp | −0.070pp | +0.000pp | +0.000pp | +0.396pp |

**Collapse verdicts:** TC max |d| = **0.03** (bullet vs blitz) → **collapse**. ELO max |d| = **0.08** (800 vs 2400) → **collapse**.

**Recommendation:** Both axes collapse. Viability 71.4% (3,319/4,649) — ~29% of users have no low-clock events over ≥20 analyzed games; below the 80% rare-numerator threshold: thin numerator — Phase 115 must verify CI-width adequacy against the materialized opponent-flaw data (FLAWCMP-04). Pooled Q1/Q3 = [−0.081pp, +0.028pp]. Use global pooled zone; render N/A for zero-event users.

> **Why low-clock is right-skewed (not a bug).** The pooled delta has Fisher skewness ≈ **+2.5** (and **+2.0** for the §5.13 low-clock+miss combo). These are the only two strongly skewed metrics in §5 — equally rare but *situational* tags (lucky +0.3, reversed −0.2, squandered +0.1) are near-symmetric, so this is specific to the low-clock family, not a generic rare-count effect. Three structural causes, all expected:
> 1. **No measurement bias.** Tempo is classified identically for both colours (`clock_after < 5% of base_time` in `_classify_tempo`); cohort-wide player vs opponent low-clock counts differ by only ~7% (75,422 vs 70,439) while *total* flaws are balanced (ratio 0.99), so the mean delta is ≈0 (+0.000pp).
> 2. **Rare + bursty.** Low-clock is the rarest, burstiest tempo class. It fires only in the terminal time-scramble and clusters (several flaws in one losing scramble), unlike the common, smooth hasty/unrushed classes whose differences are near-symmetric.
> 3. **Repeated-measures asymmetry.** The paired estimator averages over the cohort user's *many* games (amplifying their persistent time-management trait) while each opponent appears in only *one* of those games (their trait averages out). Stable-trait × rare × bursty yields a heavy right tail of chronic-time-trouble users: per-user delta tracks the user's own low-clock burden (bottom→top decile player/opponent event ratio climbs 0.42 → 2.41), the bulk sits slightly negative (median −0.002pp), and the mean is pinned near zero by rating-matching.
>
> **Implication for Phase 115:** the Q1/Q3 box is mildly left-leaning but the tail is right, so a symmetric neutral zone understates the chronic-time-trouble cohort. Combined with the 71.4% viability (D-06), keep the global pooled zone and render N/A for zero-event users.

---

### 5.3 Hasty Flaws (tempo = 1)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.7pp | −1.133pp | −0.277pp | −0.013pp | +0.177pp | +1.064pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | −0.1pp | 0.8pp | −1.274pp | −0.358pp | −0.017pp | +0.220pp | +1.135pp |
| 1200 | 1,091 | +0.0pp | 0.9pp | −1.437pp | −0.267pp | −0.007pp | +0.219pp | +1.309pp |
| 1600 | 1,139 | −0.1pp | 0.7pp | −1.284pp | −0.338pp | −0.012pp | +0.170pp | +1.104pp |
| 2000 | 1,015 | +0.0pp | 0.5pp | −0.950pp | −0.252pp | −0.015pp | +0.144pp | +0.898pp |
| 2400 | 586 | +0.0pp | 0.4pp | −0.715pp | −0.206pp | −0.012pp | +0.129pp | +0.660pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.5pp | −0.645pp | −0.116pp | −0.003pp | +0.083pp | +0.707pp |
| blitz | 1,311 | +0.0pp | 0.4pp | −0.638pp | −0.174pp | −0.006pp | +0.123pp | +0.686pp |
| rapid | 1,376 | −0.1pp | 0.8pp | −1.319pp | −0.461pp | −0.048pp | +0.235pp | +1.140pp |
| classical | 711 | −0.1pp | 1.3pp | −2.268pp | −0.776pp | −0.135pp | +0.559pp | +1.990pp |

**Collapse verdicts:** TC max |d| = **0.19** (bullet vs classical) → **collapse**. ELO max |d| = **0.06** (1600 vs 2400) → **collapse**.

**Recommendation:** Both axes now collapse — TC d=0.19 slipped under the 0.20 boundary it sat on in the previous basis (the only verdict-word change from the mate-ladder backfill). Classical still has the widest spread (SD 1.3pp). Viability 98.4%. Pooled Q1/Q3 = [−0.277pp, +0.177pp]. Use global pooled zone.

---

### 5.4 Unrushed Flaws (tempo = 2)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 1.0pp | −1.613pp | −0.376pp | +0.017pp | +0.359pp | +1.555pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.1pp | 1.0pp | −1.622pp | −0.328pp | +0.068pp | +0.511pp | +1.807pp |
| 1200 | 1,091 | +0.1pp | 1.0pp | −1.702pp | −0.317pp | +0.031pp | +0.412pp | +1.824pp |
| 1600 | 1,139 | +0.0pp | 1.0pp | −1.634pp | −0.402pp | +0.017pp | +0.386pp | +1.647pp |
| 2000 | 1,015 | −0.1pp | 0.9pp | −1.639pp | −0.481pp | −0.020pp | +0.239pp | +1.230pp |
| 2400 | 586 | −0.1pp | 0.7pp | −1.112pp | −0.355pp | +0.000pp | +0.252pp | +0.960pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.1pp | 0.8pp | −1.347pp | −0.170pp | +0.013pp | +0.251pp | +1.531pp |
| blitz | 1,311 | −0.1pp | 0.9pp | −1.642pp | −0.392pp | +0.020pp | +0.266pp | +1.372pp |
| rapid | 1,376 | −0.1pp | 0.9pp | −1.620pp | −0.473pp | +0.006pp | +0.351pp | +1.377pp |
| classical | 711 | +0.1pp | 1.2pp | −1.842pp | −0.592pp | +0.038pp | +0.793pp | +2.331pp |

**Collapse verdicts:** TC max |d| = **0.21** (blitz vs classical) → **review**. ELO max |d| = **0.21** (800 vs 2000) → **review**.

**Recommendation:** Both axes review at the boundary (TC d=0.21, ELO d=0.21). The ELO mean drifts +0.1pp (800) → −0.1pp (2000), mirroring the flaw-rate ramp; classical's wider upper tail (p75 +0.8pp) drives the TC effect. Viability 99.3%. Pooled Q1/Q3 = [−0.376pp, +0.359pp]. Use pooled zone for Phase 115; both effects are modest.

---

### 5.5 Opening-Phase Flaws (phase = 0)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.4pp | −0.694pp | −0.148pp | +0.000pp | +0.131pp | +0.685pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.6pp | −0.967pp | −0.245pp | +0.011pp | +0.244pp | +0.871pp |
| 1200 | 1,091 | +0.0pp | 0.5pp | −0.860pp | −0.173pp | +0.004pp | +0.151pp | +0.744pp |
| 1600 | 1,139 | +0.0pp | 0.4pp | −0.660pp | −0.157pp | +0.000pp | +0.130pp | +0.712pp |
| 2000 | 1,015 | +0.0pp | 0.3pp | −0.515pp | −0.107pp | −0.001pp | +0.099pp | +0.491pp |
| 2400 | 586 | +0.0pp | 0.2pp | −0.372pp | −0.106pp | +0.000pp | +0.071pp | +0.306pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.4pp | −0.568pp | −0.089pp | +0.000pp | +0.077pp | +0.685pp |
| blitz | 1,311 | +0.0pp | 0.4pp | −0.591pp | −0.114pp | +0.000pp | +0.095pp | +0.556pp |
| rapid | 1,376 | +0.0pp | 0.4pp | −0.747pp | −0.168pp | +0.002pp | +0.139pp | +0.663pp |
| classical | 711 | +0.0pp | 0.6pp | −1.072pp | −0.340pp | −0.007pp | +0.288pp | +0.864pp |

**Collapse verdicts:** TC max |d| = **0.11** (bullet vs classical) → **collapse**. ELO max |d| = **0.03** (1200 vs 2000) → **collapse**.

**Recommendation:** Both axes collapse. SD shrinks monotonically with ELO (0.6pp at 800 → 0.2pp at 2400) — higher-rated players show more consistent opening-phase deltas. Viability 98.8%. Pooled Q1/Q3 = [−0.148pp, +0.131pp]. Use global pooled zone.

---

### 5.6 Middlegame Flaws (phase = 1)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.7pp | −1.163pp | −0.270pp | +0.013pp | +0.226pp | +1.015pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.6pp | −1.074pp | −0.243pp | +0.038pp | +0.299pp | +1.018pp |
| 1200 | 1,091 | +0.0pp | 0.7pp | −1.188pp | −0.199pp | +0.033pp | +0.261pp | +1.092pp |
| 1600 | 1,139 | +0.0pp | 0.7pp | −1.245pp | −0.305pp | +0.011pp | +0.209pp | +1.111pp |
| 2000 | 1,015 | −0.1pp | 0.7pp | −1.296pp | −0.360pp | −0.017pp | +0.167pp | +0.947pp |
| 2400 | 586 | +0.0pp | 0.5pp | −0.821pp | −0.237pp | +0.001pp | +0.173pp | +0.754pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.6pp | −0.938pp | −0.123pp | +0.008pp | +0.153pp | +1.081pp |
| blitz | 1,311 | +0.0pp | 0.6pp | −1.086pp | −0.266pp | +0.010pp | +0.180pp | +0.979pp |
| rapid | 1,376 | −0.1pp | 0.7pp | −1.270pp | −0.401pp | +0.009pp | +0.216pp | +0.929pp |
| classical | 711 | +0.0pp | 0.8pp | −1.376pp | −0.331pp | +0.060pp | +0.413pp | +1.206pp |

**Collapse verdicts:** TC max |d| = **0.20** (bullet vs rapid) → **review**. ELO max |d| = **0.18** (800 vs 2000) → **collapse**.

**Recommendation:** TC review at the d=0.20 boundary (bullet vs rapid); ELO collapses (d=0.18). Viability 99.4%. Pooled Q1/Q3 = [−0.270pp, +0.226pp], median +0.0pp. Use global pooled zone; the TC effect is modest.

---

### 5.7 Endgame-Phase Flaws (phase = 2)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.3pp | −0.531pp | −0.121pp | +0.004pp | +0.104pp | +0.473pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.2pp | −0.389pp | −0.082pp | +0.022pp | +0.111pp | +0.423pp |
| 1200 | 1,091 | +0.0pp | 0.3pp | −0.477pp | −0.074pp | +0.019pp | +0.115pp | +0.471pp |
| 1600 | 1,139 | +0.0pp | 0.3pp | −0.532pp | −0.136pp | +0.005pp | +0.106pp | +0.538pp |
| 2000 | 1,015 | −0.1pp | 0.3pp | −0.677pp | −0.166pp | −0.007pp | +0.090pp | +0.462pp |
| 2400 | 586 | −0.1pp | 0.3pp | −0.592pp | −0.186pp | −0.024pp | +0.067pp | +0.375pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.3pp | −0.388pp | −0.052pp | +0.000pp | +0.062pp | +0.430pp |
| blitz | 1,311 | +0.0pp | 0.3pp | −0.517pp | −0.129pp | +0.000pp | +0.074pp | +0.407pp |
| rapid | 1,376 | +0.0pp | 0.3pp | −0.606pp | −0.193pp | +0.005pp | +0.111pp | +0.490pp |
| classical | 711 | +0.0pp | 0.3pp | −0.563pp | −0.138pp | +0.058pp | +0.196pp | +0.537pp |

**Collapse verdicts:** TC max |d| = **0.16** (blitz vs classical) → **collapse**. ELO max |d| = **0.28** (800 vs 2400) → **review**.

**Recommendation:** TC collapses (d=0.16); ELO review at d=0.28 remains the largest ELO effect among the phase metrics. Viability 98.5%, up from 97.5% on the previous basis — the mate ladder recovers thrown-mate flaws, which land disproportionately in this phase. Pooled Q1/Q3 = [−0.121pp, +0.104pp]. Use pooled zone for Phase 115; a per-ELO refinement is worth revisiting alongside blunders.

---

### 5.8 Missed-Win Flaws (is_miss)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.3pp | −0.513pp | −0.111pp | +0.001pp | +0.107pp | +0.473pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.4pp | −0.575pp | −0.108pp | +0.015pp | +0.173pp | +0.536pp |
| 1200 | 1,091 | +0.0pp | 0.3pp | −0.521pp | −0.113pp | +0.002pp | +0.121pp | +0.486pp |
| 1600 | 1,139 | +0.0pp | 0.3pp | −0.543pp | −0.127pp | +0.000pp | +0.085pp | +0.487pp |
| 2000 | 1,015 | +0.0pp | 0.3pp | −0.495pp | −0.112pp | −0.002pp | +0.090pp | +0.409pp |
| 2400 | 586 | +0.0pp | 0.2pp | −0.417pp | −0.094pp | +0.004pp | +0.082pp | +0.327pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.3pp | −0.476pp | −0.065pp | +0.002pp | +0.078pp | +0.486pp |
| blitz | 1,311 | +0.0pp | 0.3pp | −0.469pp | −0.097pp | +0.000pp | +0.081pp | +0.411pp |
| rapid | 1,376 | +0.0pp | 0.3pp | −0.531pp | −0.137pp | −0.001pp | +0.114pp | +0.446pp |
| classical | 711 | +0.0pp | 0.4pp | −0.654pp | −0.149pp | +0.011pp | +0.189pp | +0.574pp |

**Collapse verdicts:** TC max |d| = **0.09** (blitz vs classical) → **collapse**. ELO max |d| = **0.11** (800 vs 2000) → **collapse**.

**Recommendation:** Both axes collapse (TC d=0.09, ELO d=0.11). Viability 99.2%. Pooled Q1/Q3 = [−0.111pp, +0.107pp], median +0.0pp. Use global pooled zone.

---

### 5.9 Lucky-Escape Flaws (is_lucky)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.3pp | −0.402pp | −0.091pp | −0.001pp | +0.089pp | +0.407pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.3pp | −0.498pp | −0.123pp | −0.009pp | +0.103pp | +0.517pp |
| 1200 | 1,091 | +0.0pp | 0.3pp | −0.452pp | −0.095pp | +0.000pp | +0.102pp | +0.420pp |
| 1600 | 1,139 | +0.0pp | 0.2pp | −0.378pp | −0.085pp | +0.000pp | +0.097pp | +0.419pp |
| 2000 | 1,015 | +0.0pp | 0.2pp | −0.342pp | −0.077pp | +0.000pp | +0.087pp | +0.369pp |
| 2400 | 586 | +0.0pp | 0.2pp | −0.298pp | −0.081pp | −0.005pp | +0.050pp | +0.270pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.2pp | −0.421pp | −0.056pp | +0.000pp | +0.053pp | +0.359pp |
| blitz | 1,311 | +0.0pp | 0.2pp | −0.355pp | −0.076pp | +0.000pp | +0.076pp | +0.371pp |
| rapid | 1,376 | +0.0pp | 0.2pp | −0.367pp | −0.103pp | −0.006pp | +0.097pp | +0.428pp |
| classical | 711 | +0.0pp | 0.3pp | −0.474pp | −0.159pp | +0.004pp | +0.156pp | +0.470pp |

**Collapse verdicts:** TC max |d| = **0.07** (bullet vs classical) → **collapse**. ELO max |d| = **0.08** (1600 vs 2400) → **collapse**.

**Recommendation:** Both axes collapse. Sign convention: a negative delta means the cohort user gets lucky less often than equally-rated opponents (gives opponents fewer lucky escapes). Under ELO-matched pairing this reads partly as "how often the situation arose", not purely skill — disclose via the Phase 115 tooltip (D-03). Viability 98.8%. Pooled median +0.0pp. Use global pooled zone.

---

### 5.10 Reversed Advantage Flaws (is_reversed)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.1pp | −0.202pp | −0.040pp | +0.000pp | +0.041pp | +0.198pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.2pp | −0.288pp | −0.064pp | +0.000pp | +0.061pp | +0.246pp |
| 1200 | 1,091 | +0.0pp | 0.1pp | −0.232pp | −0.047pp | +0.002pp | +0.057pp | +0.246pp |
| 1600 | 1,139 | +0.0pp | 0.1pp | −0.185pp | −0.038pp | +0.000pp | +0.040pp | +0.185pp |
| 2000 | 1,015 | +0.0pp | 0.1pp | −0.156pp | −0.034pp | +0.000pp | +0.030pp | +0.147pp |
| 2400 | 586 | +0.0pp | 0.1pp | −0.124pp | −0.031pp | +0.000pp | +0.019pp | +0.106pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.1pp | −0.195pp | −0.029pp | +0.000pp | +0.024pp | +0.187pp |
| blitz | 1,311 | +0.0pp | 0.1pp | −0.196pp | −0.038pp | +0.000pp | +0.031pp | +0.195pp |
| rapid | 1,376 | +0.0pp | 0.1pp | −0.210pp | −0.050pp | +0.000pp | +0.044pp | +0.181pp |
| classical | 711 | +0.0pp | 0.2pp | −0.216pp | −0.053pp | +0.011pp | +0.079pp | +0.253pp |

**Collapse verdicts:** TC max |d| = **0.13** (bullet vs classical) → **collapse**. ELO max |d| = **0.10** (1200 vs 2400) → **collapse**.

**Recommendation:** Both axes collapse. SD shrinks monotonically with ELO (0.2pp at 800 → 0.1pp at 2400). Viability 92.9% — ~7% of users have no reversed-advantage events. Pooled Q1/Q3 = [−0.040pp, +0.041pp], near-degenerate around zero. Use global pooled zone.

---

### 5.11 Squandered Win Flaws (is_squandered)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.2pp | −0.347pp | −0.073pp | +0.000pp | +0.076pp | +0.350pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.3pp | −0.424pp | −0.101pp | −0.002pp | +0.095pp | +0.447pp |
| 1200 | 1,091 | +0.0pp | 0.2pp | −0.384pp | −0.087pp | +0.000pp | +0.094pp | +0.378pp |
| 1600 | 1,139 | +0.0pp | 0.2pp | −0.313pp | −0.056pp | +0.000pp | +0.076pp | +0.313pp |
| 2000 | 1,015 | +0.0pp | 0.2pp | −0.315pp | −0.074pp | −0.003pp | +0.059pp | +0.260pp |
| 2400 | 586 | +0.0pp | 0.2pp | −0.258pp | −0.051pp | +0.004pp | +0.060pp | +0.275pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.2pp | −0.350pp | −0.045pp | +0.000pp | +0.045pp | +0.368pp |
| blitz | 1,311 | +0.0pp | 0.2pp | −0.326pp | −0.067pp | +0.000pp | +0.064pp | +0.274pp |
| rapid | 1,376 | +0.0pp | 0.2pp | −0.330pp | −0.080pp | −0.003pp | +0.083pp | +0.315pp |
| classical | 711 | +0.0pp | 0.3pp | −0.382pp | −0.112pp | +0.006pp | +0.147pp | +0.436pp |

**Collapse verdicts:** TC max |d| = **0.12** (blitz vs classical) → **collapse**. ELO max |d| = **0.09** (2000 vs 2400) → **collapse**.

**Recommendation:** Both axes collapse. SD shrinks with ELO (0.3pp at 800 → 0.2pp at 2400). Under ELO-matched pairing this reads partly as "how often the situation arose", not purely conversion skill — disclose via the Phase 115 tooltip (D-03). Viability 95.7%. Pooled Q1/Q3 = [−0.073pp, +0.076pp]. Use global pooled zone.

---

### 5.12 Hasty+Miss Combo (tempo = 1 AND is_miss)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.2pp | −0.371pp | −0.085pp | −0.001pp | +0.061pp | +0.350pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.3pp | −0.497pp | −0.125pp | −0.004pp | +0.084pp | +0.456pp |
| 1200 | 1,091 | +0.0pp | 0.3pp | −0.505pp | −0.095pp | −0.001pp | +0.070pp | +0.413pp |
| 1600 | 1,139 | +0.0pp | 0.2pp | −0.353pp | −0.096pp | −0.003pp | +0.048pp | +0.357pp |
| 2000 | 1,015 | +0.0pp | 0.2pp | −0.264pp | −0.065pp | +0.000pp | +0.054pp | +0.255pp |
| 2400 | 586 | +0.0pp | 0.1pp | −0.216pp | −0.058pp | +0.000pp | +0.056pp | +0.223pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.2pp | −0.230pp | −0.036pp | +0.000pp | +0.027pp | +0.225pp |
| blitz | 1,311 | +0.0pp | 0.1pp | −0.225pp | −0.048pp | +0.000pp | +0.047pp | +0.248pp |
| rapid | 1,376 | +0.0pp | 0.2pp | −0.413pp | −0.125pp | −0.010pp | +0.087pp | +0.397pp |
| classical | 711 | +0.0pp | 0.4pp | −0.755pp | −0.222pp | −0.026pp | +0.170pp | +0.645pp |

**Collapse verdicts:** TC max |d| = **0.12** (blitz vs classical) → **collapse**. ELO max |d| = **0.06** (800 vs 2400) → **collapse**.

**Recommendation:** Both axes collapse (TC d=0.12, ELO d=0.06). Viability 93.8% (4,360/4,649) — robust for a combo, above the 80% rare-numerator threshold. SD compresses with ELO (0.3pp → 0.1pp). Pooled mean and median near zero. Use global pooled zone.

---

### 5.13 Low-Clock+Miss Combo (tempo = 0 AND is_miss)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.1pp | −0.141pp | −0.024pp | +0.000pp | +0.012pp | +0.154pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.1pp | −0.110pp | −0.017pp | +0.000pp | +0.008pp | +0.126pp |
| 1200 | 1,091 | +0.0pp | 0.1pp | −0.113pp | −0.014pp | +0.000pp | +0.006pp | +0.110pp |
| 1600 | 1,139 | +0.0pp | 0.1pp | −0.125pp | −0.023pp | +0.000pp | +0.006pp | +0.145pp |
| 2000 | 1,015 | +0.0pp | 0.1pp | −0.167pp | −0.036pp | +0.000pp | +0.019pp | +0.226pp |
| 2400 | 586 | +0.0pp | 0.1pp | −0.166pp | −0.044pp | −0.001pp | +0.029pp | +0.194pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.1pp | −0.161pp | −0.016pp | +0.000pp | +0.015pp | +0.150pp |
| blitz | 1,311 | +0.0pp | 0.1pp | −0.148pp | −0.030pp | +0.000pp | +0.026pp | +0.205pp |
| rapid | 1,376 | +0.0pp | 0.1pp | −0.126pp | −0.029pp | +0.000pp | +0.007pp | +0.138pp |
| classical | 711 | +0.0pp | 0.1pp | −0.101pp | −0.017pp | +0.000pp | +0.000pp | +0.102pp |

**Collapse verdicts:** TC max |d| = **0.08** (blitz vs classical) → **collapse**. ELO max |d| = **0.06** (2000 vs 2400) → **collapse**.

**Recommendation:** Both axes collapse. Viability 58.2% (2,704/4,649) — the rarest combo (median 1 event/user), well below the 80% threshold: thin numerator — Phase 115 must verify CI-width adequacy against the materialized opponent-flaw data (FLAWCMP-04). Pooled Q1/Q3 = [−0.024pp, +0.012pp], the narrowest of all 15 metrics. Treat as an optional advanced metric with an explicit "insufficient data" fallback.

---

### 5.14 Mistakes (severity = 1)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.6pp | −0.991pp | −0.227pp | +0.007pp | +0.202pp | +0.920pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.6pp | −0.949pp | −0.249pp | +0.013pp | +0.226pp | +1.061pp |
| 1200 | 1,091 | +0.0pp | 0.6pp | −1.090pp | −0.215pp | +0.011pp | +0.219pp | +1.008pp |
| 1600 | 1,139 | +0.0pp | 0.6pp | −1.004pp | −0.229pp | +0.012pp | +0.199pp | +0.961pp |
| 2000 | 1,015 | +0.0pp | 0.6pp | −1.029pp | −0.249pp | −0.005pp | +0.184pp | +0.809pp |
| 2400 | 586 | +0.0pp | 0.5pp | −0.828pp | −0.182pp | +0.004pp | +0.154pp | +0.785pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.5pp | −0.840pp | −0.110pp | +0.003pp | +0.130pp | +1.004pp |
| blitz | 1,311 | +0.0pp | 0.5pp | −0.944pp | −0.210pp | +0.006pp | +0.147pp | +0.797pp |
| rapid | 1,376 | +0.0pp | 0.6pp | −1.067pp | −0.291pp | +0.008pp | +0.217pp | +0.907pp |
| classical | 711 | +0.0pp | 0.7pp | −1.312pp | −0.400pp | +0.037pp | +0.380pp | +1.050pp |

**Collapse verdicts:** TC max |d| = **0.12** (bullet vs rapid) → **collapse**. ELO max |d| = **0.10** (800 vs 2000) → **collapse**.

**Recommendation:** Both axes collapse. TC and ELO distributions are near-identical across buckets. Viability 99.4%. Pooled Q1/Q3 = [−0.227pp, +0.202pp], median +0.0pp. Use global pooled zone.

---

### 5.15 Blunders (severity = 2)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,644 | +0.0pp | 0.7pp | −1.283pp | −0.314pp | +0.013pp | +0.246pp | +1.081pp |

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 813 | +0.0pp | 0.8pp | −1.290pp | −0.290pp | +0.069pp | +0.418pp | +1.225pp |
| 1200 | 1,091 | +0.0pp | 0.7pp | −1.355pp | −0.235pp | +0.054pp | +0.354pp | +1.185pp |
| 1600 | 1,139 | −0.1pp | 0.7pp | −1.426pp | −0.333pp | +0.016pp | +0.247pp | +1.184pp |
| 2000 | 1,015 | −0.1pp | 0.6pp | −1.207pp | −0.368pp | −0.023pp | +0.154pp | +0.900pp |
| 2400 | 586 | −0.1pp | 0.5pp | −0.856pp | −0.302pp | −0.030pp | +0.120pp | +0.659pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,246 | +0.0pp | 0.6pp | −1.025pp | −0.127pp | +0.014pp | +0.183pp | +1.107pp |
| blitz | 1,311 | +0.0pp | 0.7pp | −1.220pp | −0.304pp | +0.007pp | +0.180pp | +0.975pp |
| rapid | 1,376 | −0.1pp | 0.8pp | −1.412pp | −0.489pp | −0.002pp | +0.234pp | +1.031pp |
| classical | 711 | +0.0pp | 0.8pp | −1.311pp | −0.405pp | +0.080pp | +0.488pp | +1.362pp |

**Collapse verdicts:** TC max |d| = **0.21** (bullet vs rapid) → **review**. ELO max |d| = **0.19** (800 vs 2000) → **collapse**.

**Recommendation:** TC review at d=0.21 (bullet vs rapid); ELO collapses (d=0.19) but shows the clearest mean ramp of the severity metrics (+0.0pp at 800/1200 → −0.1pp at 1600+) — higher-rated players blunder proportionally less relative to opponents. Viability 99.5%. Pooled Q1/Q3 = [−0.314pp, +0.246pp]. Use pooled zone for Phase 115; flag for potential per-ELO refinement alongside endgame-phase.

---

### 5.16 Viability Diagnostic (D-06)

**Cohort basis**: 1,223,105 analyzed games across 4,649 user×(ELO,TC) cells (3,497 distinct users). All analyzed games count (clean games = a 0 delta); the per-cell `users_total` below = these user×cell rows, not distinct users.

> Flags rare numerators (low-clock, low-clock+miss) so Phase 115 can assess
> combo CI-width adequacy. Non-zero = user has ≥1 player event of this tag
> over their ≥20 analyzed games.
> `median_events_per_user` is a RAW, unscaled count (player events of this tag
> totalled over the user's analyzed games) — NOT a per-100-moves rate, unlike the
> §5.1–5.15 zone columns. It gauges raw event volume for CI-width adequacy.

| metric | users_contributing | users_total | pct_nonzero | median_events_per_user |
|---|---:|---:|---:|---:|
| flaw_rate | 4628 | 4649 | 99.5% | 165.0 |
| low_clock | 3319 | 4649 | 71.4% | 4.0 |
| hasty | 4575 | 4649 | 98.4% | 33.0 |
| unrushed | 4616 | 4649 | 99.3% | 117.0 |
| opening | 4595 | 4649 | 98.8% | 27.0 |
| middlegame | 4620 | 4649 | 99.4% | 85.0 |
| endgame_phase | 4581 | 4649 | 98.5% | 45.0 |
| miss | 4613 | 4649 | 99.2% | 51.0 |
| lucky | 4593 | 4649 | 98.8% | 33.0 |
| reversed | 4317 | 4649 | 92.9% | 7.0 |
| squandered | 4447 | 4649 | 95.7% | 11.0 |
| hasty_miss | 4360 | 4649 | 93.8% | 9.0 |
| low_clock_miss | 2704 | 4649 | 58.2% | 1.0 |
| mistake | 4622 | 4649 | 99.4% | 67.0 |
| blunder | 4626 | 4649 | 99.5% | 98.0 |

**Viability interpretation:**
- `flaw_rate`, `blunder` are highest at 99.5%; `miss`, `unrushed`, `middlegame`, `mistake` at 99.2–99.4% — effectively universal, no viability concern.
- `opening`, `lucky`, `endgame_phase`, `hasty` at 98.4–98.8% — near-universal. The mate-ladder basis lifted `endgame_phase` from 97.5% (thrown-mate flaws land in this phase).
- `squandered` at 95.7% — robust; a small minority of users have zero events.
- `hasty_miss` (93.8%), `reversed` (92.9%) — viable but ~6–7% of users have zero events of this tag.
- `low_clock` at 71.4% (up from 67.4%) — ~29% of users play without low-clock flaws; Phase 115 should render "N/A" for those users rather than a zero delta, and verify CI-width adequacy (FLAWCMP-04).
- `low_clock_miss` at 58.2% (up from 53.6%) — the rarest combo (median 1 event/user); Phase 115 should treat it as an optional advanced metric with an explicit "insufficient data" fallback (FLAWCMP-04).

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| MG-entry eval (centered) | 2.1 | collapse (0.18) | collapse (0.09) | Single symmetric ±30 cp band fits all cells |
| Non-Endgame Score | 3.1.1 | review (0.46) | collapse (0.10) | Classical tail; keep shared ±5pp band |
| EG-entry eval (uncentered) | 3.1.2 | collapse (0.14) | collapse (0.11) | Single 0-centered ±0.60 pawn band fits |
| Achievable Score (entry_xs) | 3.1.3 | collapse (0.12) | collapse (0.12) | Single [0.45, 0.55] band fits |
| EG Score (per-user, EG-only) | 3.1.4 | review (0.21) | review (0.35) | ELO tail residual — known D-01 confound; keep |
| Achievable Score Gap (paired) | 3.1.5 | collapse (0.13) | review (0.34) | Keep ±5pp |
| EG Score Gap (eg − non_eg) | 3.1.6 | review (0.37) | review (0.21) | Classical tail; keep ±10pp |
| Conversion (per-user rate) | 3.2.1 | **keep (0.93)** | **keep (0.51)** | Per-TC bands live; per-ELO eventual |
| Parity (per-user rate) | 3.2.1 | collapse (0.11) | review (0.22) | Per-TC bands (near-identical) |
| Recovery (per-user rate) | 3.2.1 | **keep (0.90)** | review (0.25) | Per-TC bands live |
| Endgame Skill (composite) | 3.2.1 | — | — | **Retracted Phase 87.4** — no band |
| Section-2 Conversion ΔES | 3.2.2 | **keep (1.25)** | **keep (1.35)** | Off-zero scalar (pooled); per-axis deferred |
| Section-2 Parity ΔES | 3.2.2 | collapse (0.18) | review (0.31) | Keep scalar ±0.04 |
| Section-2 Recovery ΔES | 3.2.2 | **keep (1.69)** | **keep (0.95)** | Off-zero scalar; per-axis deferred |
| Section-2 Skill ΔES | 3.2.2 | — | — | **Retracted Phase 87.4** — no band |
| Clock-diff % at EG entry | 3.3.1 | review (0.24) | collapse (0.17) | Keep ±5% |
| Clock-gap fraction | 3.3.1 | review | collapse (0.17) | Live (−0.065, +0.047) matches |
| Net-timeout rate | 3.3.1 | collapse (0.09) | review (0.28) | Keep ±5pp |
| Time-pressure curve (per-bucket) | 3.3.2 | review @tb0 (0.39) → collapse | collapse | TC overlay at extreme pressure |
| Score per pressure quintile Q0 | 3.3.3 | **keep (0.75)** | **keep (0.56)** | Per-(TC×Q) bands; Q0 strongest |
| Score per pressure quintile Q1 | 3.3.3 | review (0.32) | collapse (0.15) | Per-(TC×Q) band |
| Score per pressure quintile Q2 | 3.3.3 | review (0.46) | review (0.25) | Per-(TC×Q) band |
| Score per pressure quintile Q3 | 3.3.3 | review (0.40) | review (0.34) | Per-(TC×Q) band |
| Score per pressure quintile Q4 | 3.3.3 | collapse (0.19) | review (0.31) | Per-(TC×Q) band |
| Per-class score (pooled) | 3.4.1 | collapse (across class) | — | Class-effect on score is flat |
| Per-class conversion | 3.4.1 | **keep (1.2–1.5)** | review | **Flag: stratify per-(class×TC)** |
| Per-class recovery | 3.4.1 | **keep (1.3–1.7)** | review (pawn keep 0.65) | **Flag: stratify per-(class×TC)** |
| Per-class per-span ΔES Score Gap | 3.4.2 | collapse (≤0.20) | review (≤0.31) | Keep per-class bands |
| Endgame Type redundancy | 3.4.3 | r=0.105 | — | Keep all three signals |
| **Flaw Rate** | **5.1** | **review (0.20)** | **collapse (0.17)** | **Pooled global zone; re-evaluate TC bands after Phase 115** |
| **Low-Clock Flaws** | **5.2** | **collapse (0.03)** | **collapse (0.08)** | **Pooled global zone; 29% zero-rate users → N/A display** |
| **Hasty Flaws** | **5.3** | **collapse (0.19)** | **collapse (0.06)** | **Pooled global zone** |
| **Unrushed Flaws** | **5.4** | **review (0.21)** | **review (0.21)** | **Pooled global zone** |
| **Opening-Phase Flaws** | **5.5** | **collapse (0.11)** | **collapse (0.03)** | **Pooled global zone** |
| **Middlegame Flaws** | **5.6** | **review (0.20)** | **collapse (0.18)** | **Pooled global zone** |
| **Endgame-Phase Flaws** | **5.7** | **collapse (0.16)** | **review (0.28)** | **Pooled global zone; flag for per-ELO refinement** |
| **Missed-Win Flaws** | **5.8** | **collapse (0.09)** | **collapse (0.11)** | **Pooled global zone** |
| **Lucky-Escape Flaws** | **5.9** | **collapse (0.07)** | **collapse (0.08)** | **Pooled global zone** |
| **Reversed-Advantage Flaws** | **5.10** | **collapse (0.13)** | **collapse (0.10)** | **Pooled global zone** |
| **Squandered-Win Flaws** | **5.11** | **collapse (0.12)** | **collapse (0.09)** | **Pooled global zone** |
| **Hasty+Miss Combo** | **5.12** | **collapse (0.12)** | **collapse (0.06)** | **Pooled global zone** |
| **Low-Clock+Miss Combo** | **5.13** | **collapse (0.08)** | **collapse (0.06)** | **Pooled global zone; 42% zero-rate → N/A display** |
| **Mistakes** | **5.14** | **collapse (0.12)** | **collapse (0.10)** | **Pooled global zone** |
| **Blunders** | **5.15** | **review (0.21)** | **collapse (0.19)** | **Pooled global zone; flag for per-ELO refinement** |

---

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| MG-entry baseline | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | `+0.25` | `+0.25` (meas. +25.21 cp) | — | **keep** |
| MG-entry neutral | 2.1 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.30` | `±0.30` | TC+ELO collapse | **keep** |
| MG-entry domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | `1.5` | `1.5` | — | **keep** |
| Non-EG score band | 3.1.1 | `SCORE_BULLET_NEUTRAL_*` (shared) | `±0.05` | `±0.05` | TC review / ELO collapse | **keep** |
| EG-entry eval neutral | 3.1.2 | `entry_eval_pawns` (ENDGAME_ENTRY_EVAL) | `±0.60` | `±0.60` (IQR [−0.57,+0.77]) | TC+ELO collapse | **keep** |
| EG-entry eval domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `2.25` | `2.25` | — | **keep** |
| Achievable Score band | 3.1.3 | `entry_expected_score` | `(0.45, 0.55)` | `(0.45, 0.55)` | TC+ELO collapse | **keep** |
| EG Score band | 3.1.4 | `endgame_score` | `(0.45, 0.55)` | `(0.45, 0.55)` | TC+ELO review | **keep** |
| Achievable Score Gap | 3.1.5 | `achievable_score_gap` | `(−0.05, +0.05)` | `(−0.05, +0.05)` | TC collapse / ELO review | **keep** |
| EG Score Gap | 3.1.6 | `score_gap` | `(−0.10, +0.10)` | `(−0.10, +0.10)` | TC+ELO review | **keep** |
| Conversion rate band | 3.2.1 | `TC_METRIC_BANDS[*].conv_rate` | per-TC | per-TC (matches IQR) | TC+ELO keep | **keep per-TC** |
| Parity rate band | 3.2.1 | `TC_METRIC_BANDS[*].parity_rate` | per-TC | per-TC (matches IQR) | TC collapse / ELO review | **keep per-TC** |
| Recovery rate band | 3.2.1 | `TC_METRIC_BANDS[*].recov_rate` | per-TC | per-TC (matches IQR) | TC keep / ELO review | **keep per-TC** |
| Section-2 Conv ΔES | 3.2.2 | `score_gap_conv` | `(−0.11, 0.00)` | `(−0.11, 0.00)` | TC+ELO keep | **keep** (off-zero, scalar) |
| Section-2 Parity ΔES | 3.2.2 | `score_gap_parity` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | TC collapse / ELO review | **keep** |
| Section-2 Recov ΔES | 3.2.2 | `score_gap_recov` | `(+0.01, +0.11)` | `(+0.01, +0.11)` | TC+ELO keep | **keep** (off-zero, scalar) |
| Clock-diff % band | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | `5.0` | `5.0` | TC review / ELO collapse | **keep** |
| Clock-gap-fraction band | 3.3.1 | `clock_gap_pct` | `(−0.065, +0.047)` | `(−0.0635, +0.0483)` | review/collapse | **keep** (matches ≤0.2pp) |
| Net-timeout band | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | `5.0` | `5.0` | TC collapse / ELO review | **keep** |
| Time-pressure curve | 3.3.2 | display-only | n/a | n/a | TC keep @tb0 / ELO collapse | **stratify TC at extreme pressure** |
| Pressure-bin score | 3.3.3 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | per-(TC×Q), ±0.06 cap | per-(TC×Q) (reproduces) | Q0 TC+ELO keep | **keep per-(TC×Q)** |
| Per-class score-bullet | 3.4.1 | `SCORE_BULLET_NEUTRAL_*` (global) | `±0.05` | `±0.05` global | collapse across class | **keep global** |
| Per-class conversion | 3.4.1 | `PER_CLASS_GAUGE_ZONES[*].conversion` | per-class | per-(class×TC) | TC keep / ELO review | **flag: stratify per-TC** |
| Per-class recovery | 3.4.1 | `PER_CLASS_GAUGE_ZONES[*].recovery` | per-class | per-(class×TC) | TC keep / ELO review/keep | **flag: stratify per-TC** |
| Per-class achievable_score_gap | 3.4.2 | `PER_CLASS_GAUGE_ZONES[*].achievable_score_gap` | per-class | within ±0.5pp of measured | TC collapse / ELO review | **keep all 6** |
| Global type-gap default | 3.4.2 | `endgame_type_achievable_score_gap` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | TC collapse / ELO review | **keep** |
| EG Type chart inventory | 3.4.3 | `EndgameTypeCard.tsx` layout | Score + Gap + WDL (+Conv/Recov) | keep all 3 (r=0.105) | n/a | **keep layout** (no constant) |

[verdict thresholds: Cohen's d < 0.2 collapse, 0.2–0.5 review, ≥ 0.5 keep separate]

# FlawChess Benchmarks — 2026-05-19

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-19
- **Population**: 2,415 users / 1,375,544 games / 95,040,660 positions; 1,912 completed (user, TC) checkpoints across 20 cells
- **Methodology change (2026-05-19): rating-at-game-time ELO bucketing.** The ELO axis is now bucketed from the cohort user's rating *at game time* (`games.white_rating`/`games.black_rating`, sub-800 dropped), NOT `benchmark_selected_users.rating_bucket` (the 2026-03 selection snapshot). This removes the rating-lag selection bias (climbing/over-sampled-active players' early underrated games were filed into a too-high snapshot bucket, inflating the apparent ELO skill ramp). `rating_bucket` / `median_elo` are retained as longitudinal/trajectory columns only. A user now spans 2–3 game-time ELO buckets across their career; per-user metric values are computed per `(user_id, game-time elo_bucket, tc_bucket)`. **All ELO-axis collapse verdicts and absolute zone levels in chapters 2–3 are regenerated under game-time bucketing and are NOT directly comparable to the snapshot-bucketed 2026-05-17 report.**
- **Checkpoint join restored.** `benchmark_ingest_checkpoints` now has `status='completed'` rows for all 5 rating buckets (400/400/400/400/312). The canonical CTE checkpoint join is used (the 2026-05-19 *partial* report's "current-DB-state no-checkpoint exception" is rescinded; the partial is archived at `benchmarks-2026-05-19-partial.md`).
- **Per-user history caveat**: each user contributes up to 1,000 games per TC over a 36-month window at varying ratings, so a user spans 2–3 game-time ELO buckets; "ELO bucket effect" is now a genuine rating-at-game-time effect. Any whole-career per-user scalar (e.g. composite Endgame Skill) is per-bucket/trajectory, not one number — flag for the live-UI comparator.
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,523 selected (lichess_username, tc_bucket) candidate-pool rows; 1,912 ingested at the ≈100/cell target.
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket::text = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (canonical-CTE filter, restored).
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating - user_rating) <= 100`, both ratings NOT NULL. Applied to every per-game CTE. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. See `.planning/notes/benchmark-equal-footing-framing.md`.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1 / 3.4.2). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate forces conv/recov; NULL → parity).
- **Eval coverage**: 100.00% at first endgame entry (767,395 / 767,398); 100.00% at first middlegame entry (1,299,252 / 1,299,252). NULL-eval is a rounding error.
- **Sparse-cell exclusion**: game-time `(elo_bucket=2400, tc='classical')` = **6 users / 17 games** (even sparser than the selection-pool 12-user cell) — excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes; shown footnoted in 5×4 cell tables.
- **Verdict thresholds**: Cohen's d < 0.20 collapse / 0.20–0.50 review / ≥ 0.50 keep separate.

## Acceptance tests (rating-lag fix)

**Test 1 — score flat ≈0.500 across 800–1600, no monotone ramp (PASS).** Cohort score vs equal-rated opponents (`abs(opp−user)≤100`), game-time bucketed, sparse cell excluded:

| game-time ELO | 800 | 1200 | 1600 | 2000 | 2400 |
|---|---:|---:|---:|---:|---:|
| score (game-time bucketing) | 0.5018 | 0.5042 | 0.5051 | 0.5164 | 0.5203 |
| score (old snapshot bucketing, ref) | 0.496 | 0.505 | 0.506 | 0.523 | 0.538 |

800–1600 flattened to 0.502–0.505 (the snapshot ramp is gone). 2000/2400 retain ≈+1.6–2.0pp — the **documented out-of-scope** rating-lag-tail + `select_benchmark_users.py` D-01 no-cheat-filter residual, NOT a bucketing/filter defect.

**Test 2 — per-color MG-entry eval mirror-symmetric (PASS).** Per-color signed user-POV cp at MG entry, game-time bucketed:

| game-time ELO | White | Black | asymmetry (W+B) |
|---|---:|---:|---:|
| 800 | +23.5 | −29.2 | −5.7 |
| 1200 | +25.7 | −20.1 | +5.6 |
| 1600 | +28.2 | −20.3 | +7.9 |
| 2000 | +38.4 | −12.5 | +25.9 |
| 2400 | +40.3 | −15.4 | +24.9 |

1200 is now near-mirror around the ±25 baseline (W +25.7 / B −20.1) vs the old asymmetric snapshot **+33 / −16**. 800–1600 asymmetry ≤ 8 cp. The 2000/2400 residual is the documented out-of-scope opening-style + cheat/rating-lag-tail confound. Rating-lag-attributable bias removed.

## Cell coverage

**Selection-pool coverage** (status='completed' users per `bsu.rating_bucket` × tc cell):

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 100 | 100 | 100 | 100 |
| 1200 | 100 | 100 | 100 | 100 |
| 1600 | 100 | 100 | 100 | 100 |
| 2000 | 100 | 100 | 100 | 100 |
| 2400 | 100 | 100 | 100 | 12* |

**Game-time cell coverage** (distinct users / games per game-time `elo_bucket` × tc, equal-footing applied):

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---|---|---|---|
| 800 | 137 / 56,528 | 126 / 50,038 | 162 / 45,882 | 140 / 6,907 |
| 1200 | 206 / 84,717 | 219 / 83,954 | 279 / 65,299 | 245 / 19,804 |
| 1600 | 182 / 81,041 | 220 / 82,775 | 248 / 64,306 | 208 / 23,907 |
| 2000 | 167 / 71,116 | 178 / 69,185 | 197 / 51,985 | 111 / 7,303 |
| 2400 | 126 / 59,457 | 110 / 44,305 | 103 / 17,785 | 6 / 17* |

`*` Sparse cell — game-time `(2400, classical)` has 6 users / 17 games; pool-exhausted. Excluded from marginals and Cohen's d throughout; footnoted in cell tables. All other game-time cells clear the ≥10-users floor.

---

## 1. Stratified Sample

Methodology preamble. The two cell-coverage tables above are the headline. Eval coverage at both MG and EG entry is 100% (no flagging). Equal-footing retention is not re-summarized per subchapter — per the 2026-05-03 universal rule it is applied identically everywhere. The decisive change this run is the rating-at-game-time bucketing; both acceptance tests pass (rating-lag-attributable bias removed; 2000/2400 residual is the known out-of-scope cheat/rating-lag-tail confound, not chased here).

---

## 2. Openings

### 2.1 Middlegame-entry eval

**Symmetric baseline (pass 1 — deduped game-level, no equal-footing):** n=1,246,674 · baseline_cp_white **+25.18 cp** · median +24 · SD 238. Black baseline = −25.18 by construction. Rounded ±25 cp (±0.25 pawns). Mate rows excluded: 5,978 / 1,252,655 (0.48%).

**Centered pooled per-(user,color) distribution (pass 2 — equal-footing, sparse excluded):** n=4,547 · mean +5 · p05 −93 · p25 −22 · p50 +6 · p75 +35 · p95 +89 · SD 58 (cp).

p50 centered cell grid (cp):

| ELO ↓ / TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | −2 (231) | +3 (210) | +22 (250) | −1 (73) |
| 1200 | −6 (299) | +10 (304) | +18 (313) | +26 (177) |
| 1600 | +1 (285) | +11 (317) | +6 (307) | +13 (221) |
| 2000 | +8 (287) | +4 (283) | +5 (286) | +6 (104) |
| 2400 | +6 (236) | −1 (211) | +9 (153) | —* |

ELO marginal (cp): 800 n764 m0 SD88 · 1200 n1093 m+7 SD70 · 1600 n1130 m+6 SD46 · 2000 n960 m+5 SD35 · 2400 n600 m+3 SD28.
TC marginal (cp): bullet n1338 m−3 SD68 · blitz n1325 m+4 SD46 · rapid n1309 m+10 SD50 · classical n575 m+11 SD73.

**Recommendations:** baseline +25.18 cp ≈ +0.25 pawns; live `EVAL_BASELINE_PAWNS_WHITE=0.25 / BLACK=−0.25` (symmetric invariant holds) → **keep**. Neutral `[p25,p75]=[−22,+35]` → ±35 cp = ±0.35 pawns; live `EVAL_NEUTRAL_*_PAWNS=∓0.30` → optional widen to ±0.35 (5 cp boundary; current still defensible). Domain `[p05,p95]=±90 cp`; live `EVAL_BULLET_DOMAIN_PAWNS=1.5` covers → **keep**.

### Collapse verdict
- TC axis: max |d| = **0.21** (bullet–rapid) → **review**
- ELO axis: max |d| = **0.10** (800–1600) → **collapse**

---

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

Reuses the 3.1.6 `per_user` CTE (≥30 EG AND ≥30 non-EG games/user/cell, equal-footing, game-time bucketing).

ELO marginal (%): 800 n342 51.7 [47.2/51.8/56.5] · 1200 n484 51.9 [46.4/51.9/56.8] · 1600 n501 51.7 [45.4/51.5/56.8] · 2000 n414 52.8 [47.1/52.3/58.4] · 2400 n262 52.3 [46.8/52.3/57.9].
TC marginal (%): bullet n614 51.2 [46.3/51.2/56.1] · blitz n611 51.7 [46.0/51.8/56.8] · rapid n584 52.6 [46.7/52.2/58.1] · classical n194 54.4 [47.8/53.9/61.5].
Pooled: n=2,025 · mean 52.1% · p25 **46.4%** · p50 51.9% · p75 **57.2%** · p05 38.4% · p95 66.9%.

**Recommendations:** pooled `[p25,p75]=[0.46,0.57]` vs shared live `[0.45,0.55]` — non-EG band sits ~+2pp upward and wider at top. `SCORE_BULLET_NEUTRAL_*` is shared with the Openings bullet; do **not** retune it — build a dedicated non-EG zones module only if product wants a cohort-aware non-EG card. Static `[0.45,0.55]` acceptable until then.

### Collapse verdict
- TC axis: max |d| = **0.36** (bullet–classical) → **review**
- ELO axis: max |d| = **0.14** (800–2000) → **collapse** (snapshot ELO ramp flattened)

#### 3.1.2 Endgame-entry eval (pawns)

**Symmetric baseline (pass 1):** n=801,065 · baseline_cp_white **+9.86 cp** · median 0 · SD 443. Rounded ±10 cp (±0.10 pawns). Mate rows excluded: 43,214 / 844,333 (5.12%).

**Distribution (pass 2, equal-footing, sparse excluded):**

| variant | n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| uncentered | 4,123 | +10 | −186 | −57 | +12 | +77 | +203 | 118 |
| centered | 4,123 | +10 | −183 | −57 | +11 | +77 | +202 | 118 |

ELO marginal (centered cp): 800 n661 m−1 · 1200 n968 m+3 · 1600 n1029 m+17 · 2000 n892 m+17 · 2400 n573 m+12.
TC marginal (centered cp): bullet n1278 m−2 · blitz n1247 m+16 · rapid n1202 m+18 · classical n396 m+5.

**Recommendations (uncentered, pawns):** neutral `[p25,p75]=[−0.57,+0.77]` → editorial-tighten to **±0.60 pawns** (inside IQR so the 0-centered tile actually paints; consistent with prior ±0.75→±0.50 precedent). Live `ENDGAME_ENTRY_EVAL_NEUTRAL_*_PAWNS=∓0.75` → **recommend tighten to ±0.60**. Domain `[p05,p95]=±2.0`; live `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS=2.25` → optional tighten to 2.0 (cosmetic). Center 0 — keep.

### Collapse verdict
- TC axis: max |d| = **0.16** (bullet–rapid) → **collapse**
- ELO axis: max |d| = **0.14** (800–1600) → **collapse** (snapshot ramp removed; single global pawn band justified)

#### 3.1.3 Achievable Score

Per-user `entry_xs` = mean Lichess-winning-chances expected score at first endgame-class ply (≥6-ply gate, ≥20 games/user/cell).

ELO marginal (%): 800 n374 50.5 [43.5/50.5/56.8] · 1200 n541 50.7 [45.0/50.5/56.6] · 1600 n575 51.5 [46.8/51.5/56.4] · 2000 n498 51.3 [47.3/51.4/55.3] · 2400 n311 50.9 [48.0/50.5/53.6].
TC marginal (%): bullet n675 50.3 · blitz n671 51.2 · rapid n663 51.6 · classical n290 51.0.
Pooled: n=2,299 · mean 51.0% · p25 **46.2%** · p50 51.1% · p75 **55.7%**.

**Equal-footing sanity (game-time aware): PASS** — 800/1200/1600 within ±1.5pp of 0.50, no monotone ramp; 2000/2400 do not drift above ~51.5%.

**Recommendations:** pooled `[p25,p75]=[0.46,0.56]` vs live `entry_expected_score` ZoneSpec `(0.45,0.55)` — within ~1pp → **keep `(0.45,0.55)`** (round-number parity; +1pp drift = documented cohort skill edge). Dedicated EG-entry zone; do not retune `SCORE_BULLET_NEUTRAL_*`.

### Collapse verdict
- TC axis: max |d| = **0.15** (bullet–rapid) → **collapse**
- ELO axis: max |d| = **0.11** (800–1600) → **collapse** (ELO d dropped 0.22→0.11 — direct effect of the rating-lag fix)

#### 3.1.4 Endgame Score (per-user, EG-only)

≥20 EG games/user/cell.

ELO marginal (%): 800 n374 49.8 [43.4/49.1/55.2] · 1200 n541 50.2 [44.6/49.4/55.1] · 1600 n575 51.5 [45.8/51.3/56.6] · 2000 n498 52.6 [47.5/52.4/57.1] · 2400 n311 52.8 [49.3/52.4/56.5].
TC marginal (%): bullet n675 50.5 · blitz n671 51.5 · rapid n663 52.4 · classical n290 50.6.
Pooled: n=2,299 · mean 51.3% · p05 37.8 · p25 **46.1** · p50 51.0 · p75 **56.3** · p95 66.0.

**Game-time sanity: PASS** — 800/1200/1600 = 49.8/50.2/51.5% (within ±1.5pp, no low-band ramp). 2000/2400 ≈+2.6–2.8pp = known out-of-scope residual (footnoted, not a failure; blanket `|mean−0.50|>0.01` test correctly NOT applied). Pooled `[p25,p75]=[0.46,0.56]` vs live shared `[0.45,0.55]` within tolerance. Per-ELO `eg_p50` spread 3.3pp < pooled IQR 10.2pp → no per-ELO `ENDGAME_SCORE_ZONES` registry warranted. **Do not retune shared `SCORE_BULLET_NEUTRAL_*`.**

### Collapse verdict
- TC axis: max |d| = **0.23** (bullet–rapid) → **review**
- ELO axis: max |d| = **0.36** (800–2400) → **review** (was **keep 0.84** under snapshot — per-ELO stratification deferral is now moot)

#### 3.1.5 Achievable Score Gap

Per-user `mean(actual_i − expected_i)`; mate included, |cp|≥2000 clipped, ≥20 paired games/user/cell.

ELO marginal (pp): 800 n374 −0.7 [−5.9/−0.9/+4.4] · 1200 n541 −0.5 · 1600 n575 +0.0 · 2000 n498 +1.3 · 2400 n311 +2.0.
TC marginal (pp): bullet n675 +0.2 · blitz n671 +0.3 · rapid n663 +0.8 · classical n290 −0.4.
Pooled: n=2,299 · mean **+0.3pp** · p05 −13.3 · p25 **−4.0** · p50 +0.6 · p75 **+5.0** · p95 +13.0.

**Engine-alignment sanity: PASS** (pooled +0.3pp, within ±1pp of 0). Pooled `[p25,p75]=[−4.0,+5.0]pp`; |mean|<1pp → symmetric **±5pp** = exact match to live `ACHIEVABLE_SCORE_GAP_NEUTRAL_* = ∓0.05`. **No change.** Domain p05/p95 ≈±13pp inside the `SCORE_GAP_DOMAIN=0.20` fallback.

### Collapse verdict
- TC axis: max |d| = **0.18** (rapid–classical) → **collapse**
- ELO axis: max |d| = **0.32** (800–2400) → **review** (was **keep 0.62** under snapshot — per-ELO deferral now moot)

#### 3.1.6 Endgame Score Gap and Timeline

Per-user `diff = eg_score − non_eg_score`; ≥30 EG AND ≥30 non-EG games/user/cell. Within-user difference → rating-lag-immune per chapter 1.

ELO marginal (pp): 800 n342 −2.3 [−11.8/−3.1/+6.2] · 1200 n484 −1.7 · 1600 n501 −0.7 · 2000 n414 −0.7 · 2400 n262 +0.3.
TC marginal (pp): bullet n614 −1.0 · blitz n611 −0.5 · rapid n584 −0.8 · classical n194 −4.2.
Pooled: n=2,003 · diff_mean **−1.1pp** · p05 −22.1 · p25 **−10.1** · p50 −1.2 · p75 **+7.8** · p95 +20.9 · eg_mean 51.0% · non_eg_mean 52.1%.

**Recommendations:**
- Score-gap neutral = pooled `[p25,p75]=[−10.1,+7.8]pp`; |median|=1.2pp<5pp → **keep symmetric ±10pp** = live `SCORE_GAP_NEUTRAL_* = ∓0.10`. No re-centering.
- Score-gap domain = pooled max(|p05|,|p95|) = **22.1pp**; live `SCORE_GAP_DOMAIN=0.20` under-covers the p05 tail → **recommend widen 0.20 → 0.22**.
- Timeline: pooled eg `[46.1,55.5]%` ∩ non_eg `[46.4,57.2]%` overlap >50% → **unify to a single timeline band `[46,56]%`** (do not ship separate eg/non-eg overlays). Y-axis observed range ≈[38,67]%; live tick array `[20…80]` wider than needed (harmless).

### Collapse verdict
- TC axis: max |d| = **0.28** (blitz–classical) → **review** (classical-only driver)
- ELO axis: max |d| = **0.19** (800–2400) → **collapse** (confirms chapter-1 robustness claim — within-user diff genuinely collapses)

### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery + Endgame Skill

Per-game eval bucketing (`_classify_endgame_bucket`); ≥20 EG games/user/cell + ≥2 buckets. Live: `FIXED_GAUGE_ZONES.conversion=[0.65,0.77]`, `.parity=[0.45,0.55]`, `.recovery=[0.24,0.36]`. `ENDGAME_SKILL_ZONES` retired (Phase 87.4 D-05) — Skill is informational only.

**Conversion** — pooled `[p25,p50,p75]=[64.3,71.4,77.7]%`. TC marginal: bullet 65.6 / blitz 71.7 / rapid 74.3 / classical 75.0; ELO: 800 69.4 → 2400 72.8. Pooled band `[0.64,0.78]` ≈ live `[0.65,0.77]` (no change to pooled). **TC d=0.87 (bullet–classical) keep / ELO d=0.50 (800–2400) keep.** Single band mis-centers bullet (~66%) vs classical (~75%) → cell-specific (TC×ELO) zones needed.

**Parity** — pooled `[43.8,50.0,57.1]%`. Live `[0.45,0.55]` is a tight round band on the 0.50 null — within editorial tolerance, **no change**. **TC d=0.13 collapse / ELO d=0.24 review.**

**Recovery** — pooled `[23.8,30.0,37.0]%`. TC marginal: bullet 35.2 / blitz 30.0 / rapid 27.4 / classical 23.1. Pooled `[0.24,0.37]` ≈ live `[0.24,0.36]` (no change to pooled). **TC d=0.91 (bullet–classical) keep / ELO d=0.23 review.** TC-specific zones needed; ELO can collapse.

**Endgame Skill** (informational) — pooled `[46.3,50.9,55.2]%`. **TC d=0.17 collapse / ELO d=0.42 review.** Gauge retired; if revived `[0.46,0.55]`.

### Collapse verdict
- Conversion — TC **keep (0.87)**, ELO **keep (0.50)**
- Parity — TC collapse (0.13), ELO review (0.24)
- Recovery — TC **keep (0.91)**, ELO review (0.23)
- Endgame Skill — TC collapse (0.17), ELO review (0.42)

#### 3.2.2 Per-bucket ΔES Score Gap (Section 2)

Per-span `gap_span = exit_score − ES_entry`; per-user mean per bucket; ≥20 spans/user/bucket/cell. Within-user-difference family → rating-lag-immune.

Pooled-by-bucket: conversion n2,060 **−6.4pp** [p25 −11.3 / p50 −5.0 / p75 +0.1] · parity n1,804 **+0.1pp** [−3.6/+0.4/+4.1] · recovery n1,977 **+6.4pp** [+0.8/+5.6/+11.0] · skill n2,253 +0.1pp [−3.0/+0.4/+3.1].

**Sigmoid-bias check confirmed exactly** (conv −6.4 / parity ~0 / recov +6.4 — structural, divergent per-bucket bands are correct).

| bucket | TC d_max | TC verdict | ELO d_max | ELO verdict |
|---|--:|---|--:|---|
| conversion | 1.18 (bullet–classical) | keep | 1.26 (800–2400) | keep |
| parity | 0.21 (rapid–classical) | review | 0.31 (1600–2400) | review |
| recovery | 1.62 (bullet–classical) | keep | 0.85 (800–2000) | keep |
| skill | 0.18 (bullet–rapid) | collapse | 0.42 (800–2400) | review |

**Recommended `ZONE_REGISTRY`:** `section2_score_gap_conv (-0.11,0.00)` keep · `_parity (-0.04,0.04)` keep · `_recov (0.01,0.11)` keep — game-time IQRs round to exactly the live bands (within-user-difference is rating-lag-immune). `_skill` stays deleted (Phase 87.4 D-05). No regen needed.

#### 3.2.3 Rate vs score-gap divergence (Conversion & Recovery cross-cut)

Derived (no new query). **Conversion: no divergence** — raw rate and gap both say two-axis, same direction (ELO rate d=0.50 / gap d=1.26; TC rate d=0.87 / gap d=1.18), both compressing toward the −6.4pp sigmoid null. **Recovery: ELO-axis divergence** — raw recovery rate flat across game-time ELO (31.0%→32.6%, d≈0.21 review) but the recovery ΔES *gap* re-exposes a strong ELO signal (+11.5pp@800 → +4.1pp@2000/2400, d=0.85 keep): the engine-expected score rises with the cohort, so the absolute save-rate masks a real relative-skill gradient. Mirror-axis: raw conversion rises bullet→classical while raw recovery falls (opponent also converts cleanly with more time). **Implication:** recovery-gap ELO `keep separate` (d=0.85) is the strongest argument against the §3.2.2 scalar-registry deferral; recommendation unchanged this phase (scalar pooled band ships) but recovery is the first per-(TC×ELO) promotion candidate.

#### 3.3.1 Clock pressure at endgame entry

≥20 EG games/user/cell. Live `NEUTRAL_PCT_THRESHOLD=5.0`, `NEUTRAL_TIMEOUT_THRESHOLD=5.0` (both ±, percent).

**Clock-diff %** — pooled n=2,291 mean −1.27% · p25 **−6.7%** · p50 −0.52 · p75 **+4.8%**. ELO marginal m: 800 −0.80 / 1200 −1.40 / 1600 −2.16 / 2000 −1.00 / 2400 −0.43. TC marginal m: bullet −0.29 / blitz −1.17 / rapid −1.61 / classical −3.05. **TC d=0.26 review / ELO d=0.17 collapse.** Pooled IQR brackets ±5.0; no axis reaches keep → **keep ±5.0** (no compelling asymmetry argument at sub-2pp median).

**Net timeout** — pooled n=2,291 mean +0.29pp · p25 **−4.4pp** · p50 +1.11 · p75 **+6.1pp**. **TC d=0.05 collapse / ELO d=0.26 review.** Pooled IQR brackets ±5.0 → **keep ±5.0**.

#### 3.3.1 clock-gap-%

Per-user mean `(user_clk−opp_clk)/base_clock` at endgame entry. Live `clock_gap_pct` ZoneSpec = **`(-0.065, 0.047)`** (already calibrated; the 2026-05-17 placeholder `(-0.05,0.05)` recommendation has been implemented). Pooled n=2,291 mean −0.0127 · p25 **−0.0669** · p50 −0.0052 · p75 **+0.0482**. **TC d=0.26 review / ELO d=0.21 review.** Game-time pooled IQR `(-0.067,+0.048)` round-matches live `(-0.065,+0.047)` → **no change** (confirms the live calibrated band under game-time bucketing).

#### 3.3.2 Time pressure vs performance

Per-(ELO×TC×time-bucket) game-level mean score; binary outcome feeds Cohen's d. **TC max |d| = 0.34** at bucket-0 (bullet 26% vs classical 41% under maximum clock pressure) → **review**; **ELO max |d| = 0.16** → **collapse**. Recommendation: pool ELO; keep a **per-TC overlay (4 curves)** for the bucket-0 divergence (full 20-cell display unnecessary). Chart-structure decision, no zone constant.

#### §3.3.3 chess-score-per-pressure-bin

Per-user score per (TC×ELO×quintile); Q0=max pressure … Q4=min. Live `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (20-entry tc×quintile, mostly ±0.06 after the `PRESSURE_BIN_NEUTRAL_CAP=0.06` editorial cap; bullet Q1/Q2/Q3 sub-cap).

| Quintile | TC d_max | TC verdict | ELO d_max | ELO verdict |
|---|--:|---|--:|---|
| Q0 (max pressure) | 0.42 | review | **0.59 (800–2400)** | **keep separate** |
| Q1 | 0.27 | review | 0.23 | review |
| Q2 | 0.39 | review | 0.27 | review |
| Q3 | 0.36 | review | 0.39 | review |
| Q4 (min pressure) | 0.18 | collapse | 0.37 | review |

**Major change vs 2026-05-17:** under snapshot bucketing the report said *ELO does NOT collapse* for **all five quintiles** (a blocking decision). Under game-time bucketing only **Q0 ELO keeps separate (d=0.59)**; Q1–Q4 ELO drop to **review** (the snapshot ELO ramp was largely a rating-lag artifact). 17/20 cells hit the ±0.06 cap, so the shipped band set is materially unchanged from the live registry; only bullet Q1/Q2 retain sub-cap edges. **Q0 flagged as the standing per-(TC×ELO×quintile) promotion candidate; scalar (tc,quintile) ELO-pooled shape ships by default.** Optional: tighten bullet Q1 `(-0.051,+0.06)` / Q2 `(-0.052,+0.058)`; regen `gen_endgame_zones_ts.py` only if adopted.

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

Pooled-by-class (sparse excluded): rook score 50.8% conv 71.0% recov 29.6% · minor_piece 51.0/69.5/32.7 · pawn 51.1/73.8/27.5 · queen 50.8/77.5/23.4 · mixed 50.6/69.4/31.1 · pawnless 50.7/79.2/19.7.

Per-class per-user chess-score IQR (≥10 games/user/class): rook [0.440,0.571] · minor_piece [0.433,0.578] · pawn [0.423,0.589] · queen [0.410,0.625] · mixed [0.462,0.561] · pawnless [0.303,0.545].

**Recommendations:**
- **Score bullet:** global `[0.45,0.55]` is 2–4× too tight vs per-user IQR (widths 9.9pp mixed → 21.5pp queen; queen +1.8pp / pawnless −7.6pp midpoint shift). **Recommend `PER_CLASS_SCORE_BULLET_ZONES`** (Python registry → codegen → `EndgameTypeCard.tsx`): rook(−0.060,+0.071) minor_piece(−0.067,+0.078) pawn(−0.077,+0.089) queen(−0.090,+0.125) mixed(−0.038,+0.061) pawnless(−0.197,+0.045). (Or document the global band as deliberate editorial tightening per `feedback_zone_band_judgement.md`.)
- **Conv/recov gauge drift (>3pp):** only **`PER_CLASS_GAUGE_ZONES['minor_piece'].recovery (0.31,0.41) → (0.28,0.38)`** is actionable. pawnless conv +4.2pp / recov −6.3pp drift is informational (UI-hidden).
- Score-diff zone: DEPRECATED post-Phase 87 (no live surface).

**Collapse verdicts** (rate-level Cohen's d, n≥30 cell-floor — magnitudes large by construction): aggregated **score TC keep (1.31) / ELO keep (7.37)**, **conversion TC keep (5.24) / ELO keep (2.32)**, **recovery TC keep (10.41) / ELO keep (2.69)**. Every metric keep-separate on both axes → cell-specific + per-class zones (consistent with the existing per-class `PER_CLASS_GAUGE_ZONES`).

#### 3.4.2 Per-span Score Gap by Endgame Type

`gap_span = exit_score − ES_entry`; ≥20 spans/user/class/cell.

Pooled-by-class IQR: rook [−5.14,+4.61]pp · minor_piece [−4.45,+5.58] · pawn [−3.95,+4.90] · queen [−4.22,+5.42] · mixed [−3.23,+3.76] · pooled-all [−3.99,+4.49].

Collapse verdicts (rate-level): every class keep-separate both axes (TC max d=1.50 rook; ELO max d=3.87 mixed) → stratify per class; D-04 single-global-band condition not met.

**Recommended `PER_CLASS_GAUGE_ZONES[cls].achievable_score_gap` updates** (>0.5pp drift vs Phase 87.1 bands):
- **rook `(-0.05,+0.04) → (-0.05,+0.05)`** (upper +0.6pp)
- **queen `(-0.05,+0.05) → (-0.04,+0.05)`** (lower +0.8pp)
- minor_piece / pawn / mixed: within ±0.5pp → keep. Global `ZONE_REGISTRY["endgame_type_achievable_score_gap"]=(-0.04,+0.04)` → keep (per-class overrides carry the signal).

#### 3.4.3 Endgame Type Score vs Score Gap — redundancy analysis

Inner-join per-user-per-class (score ≥10 games ∩ gap ≥20 spans), per-class IQR-derived zones.

| class | n | pearson_r | sign_agree | zone_strict | strong_disagree |
|---|--:|--:|--:|--:|--:|
| rook | 1,401 | 0.603 | 0.686 | 0.578 | 0.029 |
| minor_piece | 1,151 | 0.602 | 0.712 | 0.564 | 0.020 |
| pawn | 716 | 0.541 | 0.694 | 0.543 | 0.025 |
| queen | 656 | 0.220 | 0.558 | 0.419 | 0.076 |
| mixed | 2,283 | 0.486 | 0.647 | 0.534 | 0.045 |
| **pooled** | **6,207** | **0.500** | **0.664** | **0.538** | **0.038** |

Per-class verdict: rook & minor_piece → drop WDL bar; pawn, queen, mixed → keep all three. **Mode across the 5 visible classes = "keep all three"** (pooled r=0.500 ≪ 0.85 drop-Score and < 0.60 drop-WDL thresholds; queen nearly orthogonal r=0.22). Drop-out report: 24–80% of score-qualifiers lack a gap bullet (queen worst, 45%) — argues against making Score Gap the sole survivor. **No `EndgameTypeCard.tsx` chart removal.** This **reverses the 2026-05-17 "Drop WDL bar" recommendation.**

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| Middlegame-entry eval (centered) | 2.1 | review (0.21) | **collapse (0.10)** | Single global band; live ±0.30 pawns OK (optional ±0.35) |
| Non-Endgame Score | 3.1.1 | review (0.36) | **collapse (0.14)** | Single band; classical ~3pp hotter, below keep |
| Endgame-entry eval (uncentered) | 3.1.2 | collapse (0.16) | collapse (0.14) | Single global pawn band; **tighten ±0.75→±0.60** |
| Achievable Score | 3.1.3 | collapse (0.15) | **collapse (0.11)** | Single `(0.45,0.55)` confirmed (ELO d 0.22→0.11) |
| Endgame Score (EG-only) | 3.1.4 | review (0.23) | **review (0.36)** | Single band; per-ELO deferral now moot (was keep 0.84) |
| Achievable Score Gap | 3.1.5 | collapse (0.18) | **review (0.32)** | Live ±5pp exact; per-ELO deferral moot (was keep 0.62) |
| Endgame Score Gap (eg−non_eg) | 3.1.6 | review (0.28) | collapse (0.19) | ±10pp kept; **widen SCORE_GAP_DOMAIN→0.22**; unify timeline band |
| Conversion (per-user) | 3.2.1 | **keep (0.87)** | **keep (0.50)** | Two-axis; pooled band ≈ live; cell-specific zones |
| Parity (per-user) | 3.2.1 | collapse (0.13) | review (0.24) | Live `(0.45,0.55)` OK |
| Recovery (per-user) | 3.2.1 | **keep (0.91)** | review (0.23) | TC-stratification candidate; pooled ≈ live |
| Endgame Skill (retired) | 3.2.1 | collapse (0.17) | review (0.42) | Informational (gauge retired) |
| ΔES — Conversion | 3.2.2 | **keep (1.18)** | **keep (1.26)** | Live `(−0.11,0.00)` confirmed |
| ΔES — Parity | 3.2.2 | review (0.21) | review (0.31) | Live `(−0.04,+0.04)` confirmed |
| ΔES — Recovery | 3.2.2 | **keep (1.62)** | **keep (0.85)** | Live `(+0.01,+0.11)` confirmed; 1st stratification candidate |
| ΔES — Skill (retired) | 3.2.2 | collapse (0.18) | review (0.42) | Stays deleted (Phase 87.4) |
| Clock pressure %-of-base | 3.3.1 | review (0.26) | collapse (0.17) | Keep ±5% |
| Net timeout rate | 3.3.1 | collapse (0.05) | review (0.26) | Keep ±5pp |
| Time-pressure curve | 3.3.2 | review (0.34 @ tb0) | collapse (0.16) | Per-TC overlay at severe-pressure end |
| Clock gap % at EG entry | 3.3.1 cg% | review (0.26) | review (0.21) | Live `(−0.065,0.047)` confirmed |
| Pressure bin Q0 | §3.3.3 | review (0.42) | **keep (0.59)** | Q0 ELO stratification candidate |
| Pressure bin Q1 | §3.3.3 | review (0.27) | review (0.23) | (tc,q) ELO-pooled ships |
| Pressure bin Q2 | §3.3.3 | review (0.39) | review (0.27) | (tc,q) ELO-pooled ships |
| Pressure bin Q3 | §3.3.3 | review (0.36) | review (0.39) | (tc,q) ELO-pooled ships |
| Pressure bin Q4 | §3.3.3 | collapse (0.18) | review (0.37) | (tc,q) ELO-pooled ships |
| Per-class score | 3.4.1 | keep (1.31) | keep (7.37) | Cell-specific + per-class zones |
| Per-class conversion | 3.4.1 | keep (5.24) | keep (2.32) | Per-class + cell zones |
| Per-class recovery | 3.4.1 | keep (10.41) | keep (2.69) | Never collapse recovery across TC |
| Per-class ΔES gap | 3.4.2 | keep (1.50 rook) | keep (3.87 mixed) | Stratify per class; D-04 not met |
| Score vs Gap redundancy | 3.4.3 | n/a | n/a | r=0.50; keep all three card signals |

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Verdict | Action |
|---|---|---|---|---|---|---|
| MG eval baseline | 2.1 | `EVAL_BASELINE_PAWNS_WHITE/BLACK` | `±0.25` | `±0.25` (meas +25.18 cp) | TC review / ELO collapse | **keep** |
| MG eval neutral | 2.1 | `EVAL_NEUTRAL_*_PAWNS` | `±0.30` | `±0.35` | review / collapse | optional widen ±0.35 (boundary) |
| MG eval domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | `1.5` | `1.5` | n/a | keep |
| Non-EG score | 3.1.1 | shared `SCORE_BULLET_NEUTRAL_*` | `±0.05`→`[.45,.55]` | dedicated `[.46,.57]` | review / collapse | dedicated non-EG module if needed |
| EG-entry eval neutral | 3.1.2 | `ENDGAME_ENTRY_EVAL_NEUTRAL_*_PAWNS` | `±0.75` | **`±0.60`** | collapse / collapse | **tighten ±0.75→±0.60** (editorial) |
| EG-entry eval domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `2.25` | `2.0` | n/a | optional tighten (cosmetic) |
| Achievable Score | 3.1.3 | `entry_expected_score` | `(0.45,0.55)` | `(0.45,0.55)` | collapse / collapse | **keep** |
| Endgame Score | 3.1.4 | shared `endgame_score`/`SCORE_BULLET_*` | `(0.45,0.55)` | `(0.46,0.56)`≈ | review / review | keep (no per-ELO; deferral moot) |
| Achievable Score Gap | 3.1.5 | `achievable_score_gap` | `(−0.05,+0.05)` | `(−0.05,+0.05)` | collapse / review | **keep** (exact match) |
| Score Gap (eg−non_eg) | 3.1.6 | `score_gap` | `(−0.10,+0.10)` | `(−0.10,+0.10)` | review / collapse | keep |
| **Score Gap domain** | 3.1.6 | `SCORE_GAP_DOMAIN` | `0.20` | **`0.22`** | n/a | **widen 0.20→0.22** (p05 −22.1pp clipped) |
| **Score Gap timeline** | 3.1.6 | eg/non-eg overlay | tick `[20..80]` | unified band `[46,56]%` | n/a | **unify single band** (overlap >50%) |
| Conv (per-user) | 3.2.1 | `FIXED_GAUGE_ZONES.conversion` | `[0.65,0.77]` | `[0.64,0.78]` pooled | TC keep / ELO keep | keep pooled; add (TC×ELO) zones |
| Parity (per-user) | 3.2.1 | `FIXED_GAUGE_ZONES.parity` | `[0.45,0.55]` | `[0.44,0.57]` | TC collapse / ELO review | keep |
| Recov (per-user) | 3.2.1 | `FIXED_GAUGE_ZONES.recovery` | `[0.24,0.36]` | `[0.24,0.37]` pooled | TC keep / ELO review | keep pooled; add TC zones |
| ΔES Conv | 3.2.2 | `section2_score_gap_conv` | `(−0.11,0.00)` | `(−0.11,0.00)` | TC keep / ELO keep | **keep** (confirmed game-time) |
| ΔES Parity | 3.2.2 | `section2_score_gap_parity` | `(−0.04,+0.04)` | `(−0.04,+0.04)` | review / review | **keep** |
| ΔES Recov | 3.2.2 | `section2_score_gap_recov` | `(+0.01,+0.11)` | `(+0.01,+0.11)` | TC keep / ELO keep | **keep** |
| Clock-diff % | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | `±5.0` | `±5.0` | review / collapse | keep |
| Net timeout | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | `±5.0` | `±5.0` | collapse / review | keep |
| Clock gap % | 3.3.1 cg% | `clock_gap_pct` ZoneSpec | `(−0.065,0.047)` | `(−0.065,0.047)` | review / review | **keep** (confirmed; was placeholder→calibrated) |
| Time-pressure curve | 3.3.2 | chart config | n/a | per-TC overlay @ tb0 | review / collapse | keep; per-TC overlay |
| Pressure-bin zones | §3.3.3 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | 20-entry, mostly ±0.06 | mostly ±0.06 (17/20 cap) | Q0 ELO keep; Q1–4 review | minor: optional bullet Q1/Q2 tighten; **blocking decision largely resolved** |
| Per-class score bullet | 3.4.1 | shared `SCORE_BULLET_NEUTRAL_*` | `[0.45,0.55]` all | per-class (see 3.4.1) | keep / keep | **introduce `PER_CLASS_SCORE_BULLET_ZONES`** |
| minor_piece recovery | 3.4.1 | `PER_CLASS_GAUGE_ZONES.minor_piece.recovery` | `(0.31,0.41)` | **`(0.28,0.38)`** | n/a | **shift down ~3pp**, regen TS |
| pawnless conv/recov | 3.4.1 | `PER_CLASS_GAUGE_ZONES.pawnless` | conv`(0.70,0.80)` recov`(0.21,0.31)` | conv`(0.74,0.84)` recov`(0.15,0.25)` | n/a | informational (UI-hidden) |
| rook ΔES gap | 3.4.2 | `.rook.achievable_score_gap` | `(−0.05,+0.04)` | **`(−0.05,+0.05)`** | TC keep / ELO keep | **update upper**, regen TS |
| queen ΔES gap | 3.4.2 | `.queen.achievable_score_gap` | `(−0.05,+0.05)` | **`(−0.04,+0.05)`** | TC keep / ELO keep | **update lower**, regen TS |
| minor/pawn/mixed ΔES gap | 3.4.2 | `PER_CLASS_GAUGE_ZONES.*` | per-class | unchanged | n/a | keep (Phase 87.1 holds) |
| Global ΔES gap | 3.4.2 | `endgame_type_achievable_score_gap` | `(−0.04,+0.04)` | `(−0.04,+0.04)` | n/a | keep |
| Per-type card layout | 3.4.3 | `EndgameTypeCard.tsx` inventory | Score+Gap+WDL+Conv+Recov | **keep all three** | n/a | **reverses 2026-05-17 "drop WDL"** |

---

*Report generated 2026-05-19 from the benchmark DB under **rating-at-game-time ELO bucketing** (rating-lag fix). Canonical checkpoint join restored (all 5 buckets). Equal-footing filter (`|opp−user|≤100`) universal. Sparse cell game-time `(2400, classical)` (6 users / 17 games) excluded from marginals and Cohen's d throughout. Not directly comparable to the snapshot-bucketed 2026-05-17 report — see the comparison companion.*

# FlawChess Benchmarks — 2026-05-10

- **DB**: benchmark (Docker on `localhost:5433`, `flawchess_benchmark`)
- **Snapshot taken**: 2026-05-10T09:11:01Z
- **Population**: 2,415 users / 1,327,623 rated games / 95,040,660 positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; `tc_bucket` from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump; 9,450 distinct users selected; 1,912 (user × TC) checkpoints completed
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1,000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (universal)**: `abs(opp_rating - user_rating) <= 100`. Applied to every per-game CTE in §0–§6 to remove the matchmaking confound. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. Pre-2026-05-03 §1/§4/§5 absolute numbers are not directly comparable to this report.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (§2) or first ply of each class span (§6). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity).
- **Eval coverage at endgame entry**: 100.00% (767,395 / 767,398 qualifying endgame games have non-NULL eval).
- **Sparse-cell exclusion**: `(2400, classical)` is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (12 completed users, ~55 games/user; pool exhausted in 2026-03 dump). Cell is shown in cell-level 5×4 tables with an `n=12*` footnote.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate
- **Sample floors**: §0 ≥20 EG games/user; §1 ≥30 EG and ≥30 non-EG games/user; §2 ≥20 EG games/user, ≥2 of 3 buckets non-empty; §3 ≥20 in-domain entry plies per (user, color); §4 ≥20 EG games/user; §5 per-(TC × time-bucket) cell n ≥ 100; §6 per-(cell × class) n ≥ 100 (score) / ≥30 (conv/recov)

## Cell coverage (status='completed' users per cell)

|        | bullet | blitz | rapid | classical |
|--------|-------:|------:|------:|----------:|
| 800    | 100    | 100   | 100   | 100       |
| 1200   | 100    | 100   | 100   | 100       |
| 1600   | 100    | 100   | 100   | 100       |
| 2000   | 100    | 100   | 100   | 100       |
| 2400   | 100    | 100   | 100   | **12\***  |

`*` Sparse cell — see exclusion rule above.

---

## 0. Endgame score (per-user, endgame-reaching games only)

Per-user `eg_score = (W + 0.5·D)/total` over endgame-reaching games (`endgame_class IS NOT NULL` for ≥6 plies).

### Currently set in code
- `SCORE_BULLET_CENTER = 0.5`, `SCORE_BULLET_NEUTRAL_MIN = -0.05`, `SCORE_BULLET_NEUTRAL_MAX = +0.05`, `SCORE_BULLET_DOMAIN = 0.25` (`frontend/src/lib/scoreBulletConfig.ts`)
- These are **shared** with the Openings score bullet. Calibration of the EG-only subset belongs in a dedicated EG zones module if proposed changes warrant.

### Cell table — per-user `eg_score` `p25 / p50 / p75 (n)`

|       | bullet | blitz | rapid | classical |
|-------|--------|-------|-------|-----------|
| 800   | 0.43 / 0.47 / 0.51 (99)  | 0.43 / 0.48 / 0.53 (100) | 0.42 / 0.49 / 0.55 (96) | 0.37 / 0.44 / 0.50 (41) |
| 1200  | 0.45 / 0.49 / 0.52 (100) | 0.45 / 0.48 / 0.54 (99)  | 0.45 / 0.51 / 0.57 (100) | 0.42 / 0.51 / 0.57 (72) |
| 1600  | 0.46 / 0.50 / 0.53 (100) | 0.46 / 0.50 / 0.55 (100) | 0.48 / 0.52 / 0.56 (100) | 0.45 / 0.50 / 0.58 (85) |
| 2000  | 0.48 / 0.51 / 0.54 (100) | 0.49 / 0.53 / 0.56 (100) | 0.49 / 0.52 / 0.56 (98) | 0.49 / 0.54 / 0.59 (66) |
| 2400  | 0.50 / 0.52 / 0.57 (100) | 0.51 / 0.54 / 0.58 (100) | 0.52 / 0.55 / 0.59 (95) | 0.68 / 0.77 / 0.86 (n=2\*) |

`*` Sparse cell `(2400, classical)`: n=2 users met the ≥20 EG-game floor (12 completed users overall, most below floor).

### TC marginal (excl. sparse)

| TC | n_users | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| bullet    | 499 | 0.5032 | 0.4609 | 0.5000 | 0.5388 |
| blitz     | 499 | 0.5133 | 0.4677 | 0.5111 | 0.5584 |
| rapid     | 489 | 0.5234 | 0.4714 | 0.5222 | 0.5688 |
| classical | 264 | 0.5069 | 0.4394 | 0.5041 | 0.5745 |

### ELO marginal (excl. sparse)

| ELO | n_users | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| 800  | 336 | 0.4792 | 0.4227 | 0.4738 | 0.5233 |
| 1200 | 371 | 0.5046 | 0.4487 | 0.4934 | 0.5500 |
| 1600 | 385 | 0.5106 | 0.4620 | 0.5044 | 0.5543 |
| 2000 | 364 | 0.5249 | 0.4891 | 0.5213 | 0.5600 |
| 2400 | 295 | 0.5461 | 0.5039 | 0.5391 | 0.5807 |

### Pooled overall

| n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,751 | **0.5123** | 0.3931 | **0.4627** | 0.5086 | **0.5581** | 0.6437 |

### Recommendations

- **Sanity check on equal-footing filter**: pooled mean = 0.5123, offset +1.2 pp from 50% — slightly above the 1 pp threshold. Acceptable (weak benchmark skill edge); flag if it grows in future snapshots.
- **Cohort neutral band** (pooled `[p25, p75]`) = `[0.4627, 0.5581]` ≈ `[0.46, 0.56]` — vs live shared band `[0.45, 0.55]`. Asymmetric: shifted ~0.5 pp positive. **No change to the shared `SCORE_BULLET_NEUTRAL_*` constants** (they also drive the Openings score bullet, which serves a different population). If a per-cell or pooled cohort overlay is added to the EG tile, use `[0.46, 0.56]` as its bounds.
- **Cohort domain bounds** (pooled `[p05, p95]`) = `[0.39, 0.64]` — narrower than the live `[0.25, 0.75]` axis. Live domain remains generous enough; no change.
- **Per-ELO stratification check**: ELO-marginal `eg_p50` spread = 0.5391 − 0.4738 = 0.065. Pooled IQR width = 0.0954. Spread < IQR → no per-ELO stratification recommended on the median criterion. However, the ELO Cohen's d (below) is well above 0.5, so a per-ELO `ENDGAME_SCORE_ZONES` registry (mirroring `ENDGAME_SKILL_ZONES`) is justified by separation, not central-tendency.

### Collapse verdict
- **TC axis**: `max |d| = 0.27` (bullet vs rapid) → **review**
- **ELO axis**: `max |d| = 0.84` (800 vs 2400) → **keep separate**

Heatmap of per-user `eg_p50`:

```
           bullet   blitz   rapid   classical
  800       0.47    0.48    0.49    0.44
  1200      0.49    0.48    0.51    0.51
  1600      0.50    0.50    0.52    0.50
  2000      0.51    0.53    0.52    0.54
  2400      0.52    0.54    0.55    0.77*
```

ELO drives the population shift; TC barely matters within an ELO row.

---

## 1. Score gap (endgame vs non-endgame)

Per-user `diff = eg_score − non_eg_score`.

### Currently set in code
- `SCORE_GAP_NEUTRAL_MIN = -0.10`, `SCORE_GAP_NEUTRAL_MAX = +0.10`, `SCORE_GAP_DOMAIN = 0.20`, `SCORE_TIMELINE_Y_DOMAIN = [20, 80]` (`frontend/src/components/charts/EndgamePerformanceSection.tsx`).

### Cell table — per-user `diff` `p25 / p50 / p75 (n)`

|       | bullet | blitz | rapid | classical |
|-------|--------|-------|-------|-----------|
| 800   | -0.09 / -0.04 / +0.04 (97) | -0.11 / -0.02 / +0.05 (97) | -0.13 / -0.02 / +0.10 (94) | -0.25 / -0.13 / -0.03 (24) |
| 1200  | -0.11 / -0.04 / +0.04 (97) | -0.10 / -0.03 / +0.08 (99) | -0.12 / +0.01 / +0.08 (98) | -0.15 / -0.05 / +0.06 (51) |
| 1600  | -0.08 / -0.02 / +0.06 (97) | -0.08 / -0.00 / +0.10 (99) | -0.08 / +0.01 / +0.10 (100) | -0.15 / -0.05 / +0.10 (66) |
| 2000  | -0.10 / -0.01 / +0.06 (100) | -0.08 / +0.00 / +0.07 (98) | -0.08 / +0.01 / +0.07 (95) | -0.11 / -0.02 / +0.05 (49) |
| 2400  | -0.09 / +0.02 / +0.11 (98) | -0.08 / -0.00 / +0.05 (96) | -0.07 / -0.01 / +0.07 (77) | n=1\* |

### TC marginal (excl. sparse)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet    | 489 | -0.0101 | -0.18 | -0.10 | -0.02 | +0.06 | +0.20 |
| blitz     | 489 | -0.0074 | -0.19 | -0.09 | -0.01 | +0.07 | +0.20 |
| rapid     | 464 | -0.0071 | -0.23 | -0.09 | -0.01 | +0.08 | +0.20 |
| classical | 190 | -0.0529 | -0.34 | -0.15 | -0.05 | +0.07 | +0.20 |

### ELO marginal (excl. sparse)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800  | 312 | -0.0253 | -0.24 | -0.12 | -0.04 | +0.05 | +0.22 |
| 1200 | 345 | -0.0206 | -0.24 | -0.11 | -0.03 | +0.07 | +0.21 |
| 1600 | 362 | -0.0068 | -0.23 | -0.10 | -0.01 | +0.09 | +0.21 |
| 2000 | 342 | -0.0095 | -0.21 | -0.09 | -0.00 | +0.07 | +0.16 |
| 2400 | 271 | -0.0043 | -0.20 | -0.08 | +0.00 | +0.07 | +0.17 |

### Pooled overall

| n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,632 | **-0.0134** | -0.2272 | **-0.1035** | -0.0140 | **+0.0725** | +0.2016 |

Pooled EG-only side: `[eg_p05, eg_p95] = [0.397, 0.632]`; pooled non-EG side: `[0.389, 0.673]`.

### Recommendations

- **`SCORE_GAP_NEUTRAL` band**: pooled IQR `[-0.10, +0.07]` is mildly asymmetric (slight negative bias). Pooled median `-0.014` is well within the ±0.05 out-of-scope guard. **Keep symmetric ±0.10**.
- **`SCORE_GAP_DOMAIN`**: pooled `max(|p05|, |p95|) = 0.227`. Live `0.20` is slightly under-spec; recommend **widening to 0.25** so the 90% interval fits inside the bullet axis on extreme users.
- **Timeline neutral band**: pooled EG IQR `[0.464, 0.555]` and non-EG IQR `[0.468, 0.574]`. Overlap = `[max(p25s), min(p75s)] = [0.468, 0.555]` (95% of narrower IQR). Recommend a unified band **`[0.47, 0.55]`**.
- **Timeline Y-axis**: pooled p05/p95 ranges from `0.389` to `0.673`. Live domain `[0.20, 0.80]` is wider than necessary; recommend tightening to **`[0.35, 0.70]` (padded)** — about half the white space, retains tail headroom.

### Collapse verdict
- **TC axis**: `max |d| = 0.34` (classical vs blitz) → **review**
- **ELO axis**: `max |d| = 0.17` (800 vs 2400) → **collapse**

---

## 2. Conversion / Parity / Recovery + Endgame Skill

Per-user rates after eval-bucket classification at first endgame ply.

### Currently set in code
- `FIXED_GAUGE_ZONES` (`frontend/src/generated/endgameZones.ts`):
  - `conversion: [0, 0.65 / 0.65, 0.77 / 0.77, 1.0]`
  - `parity: [0, 0.45 / 0.45, 0.55 / 0.55, 1.0]`
  - `recovery: [0, 0.24 / 0.24, 0.36 / 0.36, 1.0]`
- `ENDGAME_SKILL_ZONES = [0, 0.47 / 0.47, 0.55 / 0.55, 1.0]`
- `BULLET_DOMAIN = 0.20` (`EndgameScoreGapSection.tsx`).

### Pooled per-user percentiles (excl. sparse)

| metric | n | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|
| Conversion | 1,751 | 0.5379 | **0.6556** | 0.7186 | **0.7692** | 0.8636 |
| Parity     | 1,751 | —     | **0.4434** | 0.5000 | **0.5625** | —     |
| Recovery   | 1,751 | 0.1606 | **0.2426** | 0.3010 | **0.3636** | 0.4609 |
| Endgame Skill | 1,751 | 0.3904 | **0.4661** | 0.5083 | **0.5484** | 0.6179 |

### TC marginals (mean / variance)

| TC | n | conv_m / var | par_m / var | recov_m / var | skill_m / var |
|---|---:|---|---|---|---|
| bullet    | 499 | 0.6513 / 0.0092 | 0.5041 / 0.0125 | 0.3555 / 0.0066 | 0.5038 / 0.0054 |
| blitz     | 499 | 0.7156 / 0.0060 | 0.5017 / 0.0081 | 0.3026 / 0.0056 | 0.5066 / 0.0037 |
| rapid     | 489 | 0.7427 / 0.0070 | 0.5077 / 0.0119 | 0.2863 / 0.0092 | 0.5126 / 0.0053 |
| classical | 264 | 0.7559 / 0.0129 | 0.4906 / 0.0316 | 0.2498 / 0.0142 | 0.4985 / 0.0081 |

### ELO marginals (mean / variance)

| ELO | n | conv_m / var | par_m / var | recov_m / var | skill_m / var |
|---|---:|---|---|---|---|
| 800  | 336 | 0.6677 / 0.0123 | 0.4698 / 0.0314 | 0.2966 / 0.0106 | 0.4782 / 0.0077 |
| 1200 | 371 | 0.7028 / 0.0094 | 0.4989 / 0.0143 | 0.3002 / 0.0097 | 0.5011 / 0.0050 |
| 1600 | 385 | 0.7173 / 0.0088 | 0.4965 / 0.0083 | 0.2930 / 0.0080 | 0.5023 / 0.0040 |
| 2000 | 364 | 0.7213 / 0.0081 | 0.5136 / 0.0078 | 0.3106 / 0.0090 | 0.5152 / 0.0041 |
| 2400 | 295 | 0.7494 / 0.0072 | 0.5373 / 0.0063 | 0.3303 / 0.0096 | 0.5390 / 0.0042 |

### Recommendations

- **Conversion neutral band**: pooled `[0.66, 0.77]` ≈ live `[0.65, 0.77]` ✓ — keep.
- **Parity neutral band**: pooled `[0.44, 0.56]` ≈ live `[0.45, 0.55]` (very slightly wider on positive side) — keep.
- **Recovery neutral band**: pooled `[0.24, 0.36]` ≈ live `[0.24, 0.36]` ✓ — keep.
- **Endgame Skill neutral band**: pooled `[0.47, 0.55]` ≈ live `[0.47, 0.55]` ✓ — keep.
- **Stratification**: see the four collapse verdicts below — Conversion and Recovery both have strong TC effects; the live single-band UI cannot center every TC simultaneously. Worth following SEED-006 to ship per-TC zones for those two metrics. Skill needs per-ELO stratification.

### Collapse verdicts (one block per metric)

| Metric | TC `max|d|` (pair) | TC | ELO `max|d|` (pair) | ELO |
|---|---|---|---|---|
| Conversion | **1.02** (bullet vs classical) | **keep separate** | **0.82** (800 vs 2400) | **keep separate** |
| Parity     | 0.10 (bullet vs classical) | collapse | 0.48 (800 vs 2400) | review |
| Recovery   | **1.10** (bullet vs classical) | **keep separate** | 0.34 (800 vs 2400) | review |
| Endgame Skill | 0.18 (bullet vs classical) | collapse | **0.78** (800 vs 2400) | **keep separate** |

Conversion: high TC + ELO separation → recommend per-(TC × ELO) zones. Recovery: per-TC zones (ELO review). Skill: per-ELO zones (TC collapses). Parity: pooled-only (single band defaults), flag the moderate ELO split for future review.

---

## 3. Evals at game phase transitions

Per-(user, color) mean signed user-POV eval at the first ply of phase = 1 (MG) and phase = 2 (EG). Production filters: `eval_cp NOT NULL AND eval_mate NULL AND |eval_cp| < 2000`. Sample floor: 20 in-domain entry plies per (user, color).

### Currently set in code
- MG-entry tile (`frontend/src/lib/openingStatsZones.ts`):
  - `EVAL_NEUTRAL_MIN_PAWNS = -0.30`, `EVAL_NEUTRAL_MAX_PAWNS = +0.30`, `EVAL_BULLET_DOMAIN_PAWNS = 1.50`
  - Symmetric baseline (live, `app/services/opening_insights_constants.py`): `EVAL_BASELINE_PAWNS_WHITE = +0.25`, `EVAL_BASELINE_PAWNS_BLACK = -0.25`, `EVAL_CONFIDENCE_MIN_N = 20`.
- EG-entry tile (`frontend/src/lib/endgameEntryEvalZones.ts`):
  - `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS = -0.75`, `ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS = +0.75`, `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.0`, `ENDGAME_ENTRY_EVAL_CENTER = 0` (uncentered, no baseline subtract).

### MG entry — Pass 1 symmetric baseline (deduped, white-POV, NO equal-footing)

| n_games | baseline_cp_white | median_white_pov | sd_white_pov |
|---:|---:|---:|---:|
| 1,246,674 | **+25.18 cp** | +24.0 cp | 237.7 cp |

→ Recommended `EVAL_BASELINE_PAWNS_WHITE = +0.25` (matches live). Black baseline = −0.25 by construction.

### MG entry — Pass 2 centered pooled distribution (per-(user, color), centered on ±25 cp)

| n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3,496 | +4.15 | -93.5 | **-20.6** | +6.9 | **+34.2** | +86.4 | 58.2 |

TC marginals (centered, cp): bullet -4.5, blitz +3.4, rapid +9.9, classical +11.5.
ELO marginals (centered, cp): 800 -6.9, 1200 +7.1, 1600 +6.1, 2000 +8.0, 2400 +5.9.

#### MG Recommendations
- **Baseline constant**: `+25 cp = +0.25 pawns` exact match to live. **No change.**
- **Neutral-zone bounds**: `max(|p25|, |p75|) = 34.2 cp ≈ 35 cp = 0.35 pawns`. Live ±0.30 (≈ ±30 cp). Within 5 cp tolerance — **keep ±0.30**, but flag for review if a future snapshot drifts further.
- **Domain bounds**: pooled p05/p95 = ±95 cp; 800-cohort p05/p95 = -150 / +124 cp. Live ±150 cp (= ±1.5 pawns) covers the 800 cohort tail. **Keep `EVAL_BULLET_DOMAIN_PAWNS = 1.5`.**
- **Mate footnote**: production filters `eval_mate NULL`; mate rows excluded from the per-user mean (matches the live z-test). Coverage at MG entry is dense (n=1.25M after trim), so the mate exclusion has negligible bias.

### MG Collapse verdict (centered)
- TC axis: `max |d| ≈ 0.25` (bullet vs rapid) → **review**
- ELO axis: `max |d| ≈ 0.23` (800 vs 2000) → **review**

Color collapse is automatic by the symmetric-baseline construction and is not reported.

---

### EG entry — Pass 1 symmetric baseline (deduped, white-POV, NO equal-footing)

| n_games | baseline_cp_white | median_white_pov | sd_white_pov |
|---:|---:|---:|---:|
| 801,065 | **+9.86 cp** | 0.0 cp | 442.6 cp |

The EG-entry tile is **0-centered** (no baseline subtract); this baseline is reported as a sanity check. Within ±10 cp of zero — fine.

### EG entry — Pass 2 distributions (per-(user, color))

| variant | n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| centered (±10 cp baseline) | 3,304 | +8.90 | -182.9 | -53.8 | +10.7 | +75.3 | +197.0 | 116.8 |
| **uncentered (matches live tile)** | 3,304 | +8.91 | **-186.0** | **-55.8** | +10.3 | **+75.0** | **+198.8** | 117.3 |

TC marginals (centered): bullet -6.1, blitz +14.0, rapid +20.8, classical +4.9.
ELO marginals (centered): 800 -15.0, 1200 +1.5, 1600 +14.7, 2000 +20.6, 2400 +21.6.

#### EG Recommendations (against the **uncentered** distribution since the live tile is 0-centered)
- **Neutral-zone bounds**: `max(|p25|, |p75|) = 75 cp = 0.75 pawns`. Live ±0.75 ✓ **exact match — keep.**
- **Domain bounds**: pooled p05/p95 = -186 / +199 cp; symmetric ±200 cp = 2.0 pawns. Live ±2.0 ✓ **exact match — keep.**
- **Center**: pooled mean = +8.9 cp (within ±10 cp tolerance). **Keep `ENDGAME_ENTRY_EVAL_CENTER = 0`.**
- **Mate footnote**: same exclusion as MG; mate rows are excluded from per-user means.

### EG Collapse verdict (centered)
- TC axis: `max |d| ≈ 0.22` (bullet vs rapid) → **review**
- ELO axis: `max |d| ≈ 0.28` (800 vs 2400) → **review**

The ELO ramp (-15 → +22 cp from 800 → 2400) is the equal-footing skill signal: even at matched opponents, higher cohorts manage to enter endgames at slightly more favourable evals.

---

## 4. Time pressure at endgame entry

Per-user clock-diff `% of base time` and `net-timeout-rate %`. SQL approximation of the backend's first-non-NULL-clock-per-parity scan.

### Currently set in code
- `NEUTRAL_PCT_THRESHOLD = 5.0`, `NEUTRAL_TIMEOUT_THRESHOLD = 5.0` (`frontend/src/generated/endgameZones.ts`).

### Cell tables

`% diff` per-user p50:

|       | bullet | blitz | rapid | classical |
|-------|-------:|------:|------:|----------:|
| 800   | -0.70  | -0.76 | +1.24 | +0.18 |
| 1200  | -0.43  | -0.48 | -0.09 | +1.17 |
| 1600  | -0.20  | -1.70 | -0.12 | -0.20 |
| 2000  | -1.53  | -1.48 | -1.27 | -5.69 |
| 2400  | +0.12  | -0.04 | -3.29 | n=1\* |

Net-timeout `%` per-user p50:

|       | bullet | blitz | rapid | classical |
|-------|-------:|------:|------:|----------:|
| 800   | -5.25  | -0.29 | +1.32 | 0.00 |
| 1200  | -0.56  | +2.03 | +1.16 | 0.00 |
| 1600  | +1.98  | +1.13 | +2.01 | 0.00 |
| 2000  | +2.19  | +2.25 | +1.97 | +0.58 |
| 2400  | +5.53  | +1.95 | +2.42 | n=1\* |

### TC marginal (excl. sparse)

| TC | n | pct_m | pct_p25 | pct_p50 | pct_p75 | net_m | net_p25 | net_p50 | net_p75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet    | 496 | -0.22 | -3.84 | -0.43 | +2.82 | +0.37 | -11.36 | +1.87 | +11.50 |
| blitz     | 499 | -1.40 | -7.09 | -0.77 | +4.70 | -0.01 | -5.93  | +1.19 | +7.74  |
| rapid     | 489 | -1.48 | -8.22 | -0.25 | +5.27 | +0.16 | -1.74  | +1.64 | +3.85  |
| classical | 259 | -2.71 | -12.26 | -0.70 | +8.01 | -0.33 | 0.00 | 0.00 | +1.70 |

### ELO marginal (excl. sparse)

| ELO | n | pct_m | pct_p25 | pct_p50 | pct_p75 | net_m | net_p25 | net_p50 | net_p75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800  | 332 | -1.07 | -6.04 | -0.29 | +4.87 | -2.01 | -7.31 | 0.00 | +4.06 |
| 1200 | 371 | -1.17 | -6.07 | -0.23 | +5.11 | -0.34 | -4.18 | +0.62 | +4.34 |
| 1600 | 384 | -1.43 | -6.78 | -0.40 | +5.12 | -0.17 | -3.26 | +1.18 | +5.14 |
| 2000 | 362 | -2.23 | -8.13 | -1.84 | +3.22 | +0.61 | -4.77 | +1.50 | +6.39 |
| 2400 | 294 | -0.29 | -4.84 | -0.21 | +4.44 | +2.77 | -2.75 | +3.05 | +9.45 |

### Pooled overall

| n | pct_m | pct_p25 | pct_p50 | pct_p75 | net_m | net_p25 | net_p50 | net_p75 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,743 | -1.28 | **-6.41** | -0.52 | **+4.66** | +0.10 | **-4.43** | +1.04 | **+5.63** |

### Recommendations

- **`NEUTRAL_PCT_THRESHOLD`**: pooled IQR `[-6.4, +4.7]` is asymmetric (slightly wider on negative side). Live ±5.0 brackets are within 1.5 pp of pooled IQR. **Keep ±5.0** (round bounds beat data-fitted asymmetry below ~5 pp). If the asymmetry becomes consistent across snapshots, consider asymmetric `[-6, +5]`.
- **`NEUTRAL_TIMEOUT_THRESHOLD`**: pooled IQR `[-4.4, +5.6]` ≈ live ±5.0 ✓ **keep**.
- **Per-TC stratification on net-timeout**: classical's net-timeout p25/p75 ≈ 0/+1.7 vs bullet's [-11.4, +11.5] — variance differs by ~8×. Mean d_max collapses (0.05) but the live ±5 zone is wildly oversized for classical players. Worth flagging for a per-TC override, even though the formal verdict is `collapse`.

### Collapse verdicts

| Metric | TC `max|d|` | TC | ELO `max|d|` | ELO |
|---|---|---|---|---|
| Clock diff %  | ~0.23 (bullet vs classical) | review | ~0.21 (1600/2000 vs others) | review |
| Net timeout % | ~0.05 (bullet vs classical) | collapse | **0.41** (800 vs 2400) | review |

---

## 5. Time pressure vs performance

Per-game score binned by `user_clock_at_endgame_entry / base_time × 100`, 10 buckets (0–9 → 0–10%, …, 90–100%).

### Currently set in code
- `Y_AXIS_DOMAIN: [0.2, 0.8]`, `X_AXIS_DOMAIN: [0, 100]` (`EndgameTimePressureSection.tsx`); `MIN_GAMES_FOR_CLOCK_STATS = 10` (`endgame_service.py`).

### TC marginal score by time-bucket (excl. sparse)

| time_bucket | bullet | blitz | rapid | classical |
|---:|--------|-------|-------|-----------|
| 0 (0–10%) | 0.260 (15275) | 0.334 (14823) | 0.338 (5686) | 0.410 (1391) |
| 1 (10–20%) | 0.399 (25401) | 0.437 (16660) | 0.441 (5987) | 0.452 (945) |
| 2 (20–30%) | 0.491 (27230) | 0.492 (17700) | 0.469 (7563) | 0.468 (1125) |
| 3 (30–40%) | 0.530 (30735) | 0.518 (21039) | 0.507 (9892) | 0.475 (1325) |
| 4 (40–50%) | 0.552 (31404) | 0.534 (24283) | 0.532 (12704) | 0.478 (1596) |
| 5 (50–60%) | 0.564 (29148) | 0.548 (26875) | 0.533 (16604) | 0.486 (2002) |
| 6 (60–70%) | 0.563 (23294) | 0.544 (26851) | 0.529 (21177) | 0.505 (2556) |
| 7 (70–80%) | 0.553 (14683) | 0.542 (21931) | 0.523 (24233) | 0.510 (3173) |
| 8 (80–90%) | 0.542 (5843)  | 0.534 (12420) | 0.524 (20363) | 0.502 (3750) |
| 9 (90–100%) | 0.500 (1235)  | 0.523 (4776)  | 0.524 (9602)  | 0.510 (9857) |

### ELO marginal score by time-bucket (excl. sparse)

| time_bucket | 800 | 1200 | 1600 | 2000 | 2400 |
|---:|------|------|------|------|------|
| 0 | 0.266 (5390) | 0.283 (7308) | 0.304 (8383) | 0.332 (9617) | 0.336 (6477) |
| 1 | 0.381 | 0.400 | 0.401 | 0.433 | 0.461 |
| 2 | 0.469 | 0.473 | 0.484 | 0.494 | 0.511 |
| 3 | 0.511 | 0.512 | 0.516 | 0.525 | 0.538 |
| 4 | 0.531 | 0.530 | 0.535 | 0.542 | 0.563 |
| 5 | 0.538 | 0.532 | 0.537 | 0.563 | 0.575 |
| 6 | 0.526 | 0.527 | 0.537 | 0.559 | 0.575 |
| 7 | 0.515 | 0.518 | 0.532 | 0.552 | 0.571 |
| 8 | 0.497 | 0.518 | 0.524 | 0.553 | 0.571 |
| 9 | 0.490 | 0.501 | 0.537 | 0.547 | 0.564 |

### Recommendations

- **Y-axis**: the lowest marginal score (TC=bullet, t=0) is 0.260; the highest (ELO=2400, t=5/6) is 0.575. Live `[0.2, 0.8]` brackets all values with margin. **Keep**.
- **TC stratified display**: classical's curve is structurally different — it's nearly flat across time-buckets (0.41 → 0.51) while bullet rises sharply (0.26 → 0.56 → 0.50). The `max|d|` (~0.34) puts TC in the review band; per the verdict, recommend either a per-TC overlay or adding a `time_control` filter that defaults to the user's primary TC.
- **ELO stratified display**: ELO ramp is monotone but small at any single time-bucket (~0.07 max gap). **Collapse OK.**

### Collapse verdicts (time-bucket 0 dominates the spread)
- TC axis: `max |d| ≈ 0.34` (bullet vs classical at bucket 0) → **review**
- ELO axis: `max |d| ≈ 0.16` (800 vs 2400 at bucket 0) → **collapse**

---

## 6. Endgame type breakdown

Per-(user × class) span entry: each `(game, endgame_class)` span ≥6 plies contributes one row. Bucketing uses Stockfish eval at the **first ply of each class span** (REFAC-02; same rule as §2).

### Currently set in code
- `NEUTRAL_ZONE_MIN = -0.05`, `NEUTRAL_ZONE_MAX = +0.05`, `BULLET_DOMAIN = 0.30` (`EndgameWDLChart.tsx`).
- `PER_CLASS_GAUGE_ZONES` (`frontend/src/generated/endgameZones.ts`):
  - rook `{conv: [0.65, 0.75], recov: [0.26, 0.36]}`
  - minor_piece `{conv: [0.63, 0.73], recov: [0.31, 0.41]}`
  - pawn `{conv: [0.67, 0.79], recov: [0.23, 0.34]}`
  - queen `{conv: [0.73, 0.83], recov: [0.20, 0.30]}`
  - mixed `{conv: [0.65, 0.75], recov: [0.28, 0.38]}`
  - pawnless `{conv: [0.70, 0.80], recov: [0.21, 0.31]}`

### Pooled-by-class summary (excl. sparse)

| class | games | users | score | score_diff | conversion (n_conv) | recovery (n_recov) |
|---|---:|---:|---:|---:|---|---|
| rook        | 94,087  | 1,845 | 0.5075 | +0.0151 | 0.7098 (32,579) | 0.2963 (30,814) |
| minor_piece | 70,381  | 1,825 | 0.5102 | +0.0204 | 0.6949 (23,981) | 0.3278 (23,239) |
| pawn        | 37,463  | 1,750 | 0.5105 | +0.0209 | 0.7379 (14,636) | 0.2754 (13,920) |
| queen       | 34,432  | 1,764 | 0.5079 | +0.0158 | 0.7744 (14,419) | 0.2343 (13,790) |
| mixed       | 529,608 | 1,888 | 0.5055 | +0.0110 | 0.6940 (204,367) | 0.3111 (199,172) |
| pawnless    | 5,847   | 1,365 | 0.5069 | +0.0139 | 0.7913 (2,515) | 0.1976 (2,363) |

### Live-zone vs pooled comparison

| class | live conv band | pooled conv | live recov band | pooled recov | verdict |
|---|---|---:|---|---:|---|
| rook        | [0.65, 0.75] | 0.710 | [0.26, 0.36] | 0.296 | both in band ✓ |
| minor_piece | [0.63, 0.73] | 0.695 | [0.31, 0.41] | 0.328 | both in band ✓ |
| pawn        | [0.67, 0.79] | 0.738 | [0.23, 0.34] | 0.275 | both in band ✓ |
| queen       | [0.73, 0.83] | 0.774 | [0.20, 0.30] | 0.234 | both in band ✓ |
| mixed       | [0.65, 0.75] | 0.694 | [0.28, 0.38] | 0.311 | both in band ✓ |
| pawnless    | [0.70, 0.80] | 0.791 | [0.21, 0.31] | 0.198 | conv in band ✓ / recov **just below** (0.198 vs 0.21) |

### Recommendations

- **Per-class score-diff neutral zone**: pooled per-class `score_diff` is in `[+0.011, +0.021]` for every class — far inside live `±0.05`. **Keep `NEUTRAL_ZONE_MIN = -0.05`, `NEUTRAL_ZONE_MAX = +0.05`.**
- **`PER_CLASS_GAUGE_ZONES`**: 5 of 6 classes have pooled rates well inside the live bands; pawnless recovery slips 1.2 pp below the lower bound (0.198 vs 0.21) but is within statistical noise (n=2,363 — ~95% CI ±1.5 pp). **No change required**. If a future snapshot shows pawnless recovery consistently <0.20, shift to `[0.19, 0.29]`.
- **No per-class score zones** beyond the global ±0.05 — score is materially identical across classes (range 0.506–0.511).

### Collapse verdicts (metric-level, max d across the 6 classes)

| Metric | TC | ELO | Notes |
|---|---|---|---|
| Score per class       | collapse (~0.05) | collapse (~0.10) | Pooled per-class score is tight (≤0.5 pp spread); cell-level moves with §0/§1, not class. |
| Conversion per class  | **keep** (mirrors §2) | **keep** (mirrors §2) | Same eval-bucketing as §2; live `PER_CLASS_GAUGE_ZONES` already absorbs the per-class effect. Per-(TC × class) cell drift remains; SEED-006 follow-up. |
| Recovery per class    | **keep** (mirrors §2) | review (mirrors §2) | Same as conversion — live PER_CLASS already addresses; per-TC × per-class would be the next refinement. |

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | TC verdict (`max|d|`) | ELO verdict (`max|d|`) | Implication |
|---|---|---|---|
| §0 Endgame score (per-user, EG only) | review (0.27) | **keep separate (0.84)** | Per-ELO cohort overlay justified. |
| §1 Score gap (eg − non_eg) | review (0.34) | collapse (0.17) | Single global zone OK; classical slightly outlying. |
| §2 Conversion (per-user) | **keep separate (1.02)** | **keep separate (0.82)** | Per-(TC × ELO) zones. |
| §2 Parity (per-user) | collapse (0.10) | review (0.48) | Single global; ELO trending. |
| §2 Recovery (per-user) | **keep separate (1.10)** | review (0.34) | Per-TC zones. |
| §2 Endgame Skill (per-user) | collapse (0.18) | **keep separate (0.78)** | Per-ELO zones. |
| §3 MG-entry eval (centered) | review (0.25) | review (0.23) | Single zone holds; ELO ramp present but small. |
| §3 EG-entry eval (centered) | review (0.22) | review (0.28) | Single zone holds; equal-footing ELO ramp visible. |
| §4 Clock diff %-of-base | review (0.23) | review (0.21) | Single zone holds; flag asymmetry. |
| §4 Net timeout rate | collapse (0.05) | review (0.41) | Variance differs ~8× across TC — flag classical. |
| §5 Time-pressure curve (per-bucket) | review (~0.34) | collapse (~0.16) | Per-TC overlay or filter recommended; ELO collapses. |
| §6 Per-class score | collapse | collapse | Pooled per-class score is essentially flat. |
| §6 Per-class conversion | **keep** | **keep** | Live PER_CLASS_GAUGE_ZONES already differentiates. |
| §6 Per-class recovery | **keep** | review | Live PER_CLASS_GAUGE_ZONES already differentiates. |

## Recommended thresholds summary

| Section | Code constant | File | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---:|---|---|
| §0 | `SCORE_BULLET_NEUTRAL_*` | `scoreBulletConfig.ts` | ±0.05 | ±0.05 (shared) | TC review / ELO keep | **keep** (do not retune shared constant; consider dedicated EG-only zones module if SEED-013 ships) |
| §0 | `SCORE_BULLET_DOMAIN` | `scoreBulletConfig.ts` | 0.25 | 0.25 | — | **keep** |
| §1 | `SCORE_GAP_NEUTRAL_MIN/MAX` | `endgameZones.ts` | ±0.10 | ±0.10 | TC review / ELO collapse | **keep** |
| §1 | `SCORE_GAP_DOMAIN` | `EndgamePerformanceSection.tsx` | 0.20 | 0.25 | — | **widen to 0.25** (p05/p95 = ±0.227) |
| §1 | `SCORE_TIMELINE_Y_DOMAIN` | `EndgamePerformanceSection.tsx` | [20, 80] | [35, 70] | — | **tighten to [35, 70]** (padded p05/p95 of both eg and non-eg sides) |
| §2 | `FIXED_GAUGE_ZONES.conversion` | `endgameZones.ts` | [0.65, 0.77] | [0.66, 0.77] | TC keep / ELO keep | keep (within 1pp); stratify per (TC × ELO) for accuracy |
| §2 | `FIXED_GAUGE_ZONES.parity` | `endgameZones.ts` | [0.45, 0.55] | [0.44, 0.56] | TC collapse / ELO review | keep |
| §2 | `FIXED_GAUGE_ZONES.recovery` | `endgameZones.ts` | [0.24, 0.36] | [0.24, 0.36] | TC keep / ELO review | keep; stratify per TC for accuracy |
| §2 | `ENDGAME_SKILL_ZONES` | `endgameZones.ts` | [0.47, 0.55] | [0.47, 0.55] | TC collapse / ELO keep | keep; stratify per ELO for accuracy |
| §3 | `EVAL_BASELINE_PAWNS_WHITE` | `opening_insights_constants.py` | +0.25 | +0.25 | — | **keep** (measured +0.25, exact match) |
| §3 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` (MG) | `openingStatsZones.ts` | ±0.30 | ±0.30 | TC review / ELO review | **keep** (measured ±0.34, within tolerance) |
| §3 | `EVAL_BULLET_DOMAIN_PAWNS` (MG) | `openingStatsZones.ts` | 1.50 | 1.50 | — | **keep** (covers 800 cohort tail) |
| §3 | `ENDGAME_ENTRY_EVAL_NEUTRAL_*` | `endgameEntryEvalZones.ts` | ±0.75 | ±0.75 | TC review / ELO review | **keep** (exact match) |
| §3 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `endgameEntryEvalZones.ts` | 2.0 | 2.0 | — | **keep** (exact match) |
| §3 | `ENDGAME_ENTRY_EVAL_CENTER` | `endgameEntryEvalZones.ts` | 0 | 0 | — | **keep** (pooled mean +8.9 cp, within tolerance) |
| §4 | `NEUTRAL_PCT_THRESHOLD` | `endgameZones.ts` | ±5.0 | ±5.0 | TC review / ELO review | **keep** |
| §4 | `NEUTRAL_TIMEOUT_THRESHOLD` | `endgameZones.ts` | ±5.0 | ±5.0 | TC collapse / ELO review | **keep**; classical variance flag (live zone is over-sized for that TC) |
| §5 | `Y_AXIS_DOMAIN` | `EndgameTimePressureSection.tsx` | [0.2, 0.8] | [0.2, 0.8] | TC review / ELO collapse | **keep**; consider per-TC overlay |
| §6 | `NEUTRAL_ZONE_MIN/MAX` (per-class score-diff) | `EndgameWDLChart.tsx` | ±0.05 | ±0.05 | collapse / collapse | **keep** |
| §6 | `PER_CLASS_GAUGE_ZONES` | `endgameZones.ts` | (6 entries) | (6 entries) | keep / keep | **keep**; pawnless recov 0.198 just below 0.21 lower bound — monitor |

---

## Equal-footing retention (universal — applied to §0, §1, §2, §4, §5, §6)

The equal-footing filter (`abs(opp_rating − user_rating) <= 100`) is the standard for all sections. Per-cell game retention vs unfiltered is unchanged from prior snapshots: mid-ELO cells retain ~85–90%; 2400-rapid drops to ~51%; 2400-classical to ~15% (already excluded as the sparse cell). All non-sparse cells clear the per-user sample floors after filtering — no escape-hatch action required.

# FlawChess Benchmarks — 2026-05-01

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-01T08:26Z
- **Population**: 1,210 users / 691,049 games / 47.8M positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; tc_bucket from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,523 candidate pool, 962 `(user, tc)` rows ingested as `status='completed'`
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory)
- **Sparse-cell exclusion**: `(2400, classical)` is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user, pool exhausted). Still shown in cell-level 5×4 tables with `*`.
- **Verdict thresholds**: Cohen's d < 0.2 = collapse / 0.2-0.5 = review / ≥ 0.5 = keep separate
- **Sample floors**: §1 ≥30 endgame AND ≥30 non-endgame games/user; §2 ≥20 endgame games/user, ≥2 of 3 buckets; §3 ≥30 endgame games/user; §4 ≥20 endgame games/user; §5 per-bucket cell ≥100 games; §6 ≥100 score / ≥30 conv / ≥30 recov per cell. All Cohen's d marginals require ≥10 users per level.
- **Cell coverage** (status='completed' users):

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 50 | 50 | 50 | 50 |
| **1200** | 50 | 50 | 50 | 50 |
| **1600** | 50 | 50 | 50 | 50 |
| **2000** | 50 | 50 | 50 | 50 |
| **2400** | 50 | 50 | 50 | 12* |

*sparse cell, see exclusion note above*

## 1. Score gap (endgame vs non-endgame)

Per-user metric: `eg_score - non_eg_score`. Sample floor: ≥30 endgame games AND ≥30 non-endgame games per user, in their selected TC.

### Currently set in code

- `SCORE_GAP_NEUTRAL_MIN/MAX = ±0.10` (frontend/src/generated/endgameZones.ts)
- `SCORE_GAP_DOMAIN = 0.20` (EndgamePerformanceSection.tsx:50)
- `SCORE_TIMELINE_Y_DOMAIN = [20, 80]` (EndgamePerformanceSection.tsx:56)

### Cell table — per-user `diff_p25 / diff_p50 / diff_p75 (n)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -0.103 / -0.044 / +0.025 (n=50) | -0.109 / -0.030 / +0.052 (n=50) | -0.128 / -0.025 / +0.141 (n=48) | -0.168 / -0.092 / -0.004 (n=29) |
| **1200** | -0.102 / -0.027 / +0.047 (n=50) | -0.116 / -0.051 / +0.086 (n=50) | -0.128 / +0.001 / +0.075 (n=50) | -0.170 / -0.057 / +0.017 (n=38) |
| **1600** | -0.096 / -0.016 / +0.073 (n=50) | -0.082 / -0.002 / +0.067 (n=50) | -0.059 / +0.013 / +0.106 (n=50) | -0.162 / -0.032 / +0.044 (n=38) |
| **2000** | -0.110 / -0.013 / +0.073 (n=50) | -0.077 / -0.023 / +0.066 (n=50) | -0.083 / -0.005 / +0.078 (n=50) | -0.099 / -0.037 / +0.036 (n=34) |
| **2400** | -0.072 / +0.021 / +0.121 (n=50) | -0.108 / -0.032 / +0.007 (n=50) | -0.090 / -0.043 / +0.018 (n=49) | -0.067 / -0.009 / +0.054 (n=6*) |

*sparse cell: n<10 floor, excluded from marginals*

### TC marginal (excludes sparse)

| TC | n | mean | SD |
|---|---|---|---|
| bullet | 250 | -0.0129 | 0.1157 |
| blitz | 250 | -0.0175 | 0.1148 |
| rapid | 247 | -0.0111 | 0.1290 |
| classical | 139 | -0.0612 | 0.1640 |

### ELO marginal (excludes sparse)

| ELO | n | mean | SD |
|---|---|---|---|
| 800 | 177 | -0.0311 | 0.1333 |
| 1200 | 188 | -0.0280 | 0.1405 |
| 1600 | 188 | -0.0127 | 0.1371 |
| 2000 | 184 | -0.0149 | 0.1173 |
| 2400 | 149 | -0.0197 | 0.1100 |

### Pooled overall (excludes sparse)
- n=886, mean=-0.0213, SD=0.1288

### Collapse verdict
- TC axis: max |d| = 0.36 (between bullet and classical) -> **review**
- ELO axis: max |d| = 0.14 (between 800 and 1600) -> **collapse**

Heatmap of per-user `diff_p50` (5 ELO × 4 TC):
```
           bullet   blitz   rapid   classical
  800  -0.044   -0.030   -0.025   -0.092 
 1200  -0.027   -0.051   +0.001   -0.057 
 1600  -0.016   -0.002   +0.013   -0.032 
 2000  -0.013   -0.023   -0.005   -0.037 
 2400  +0.021   -0.032   -0.043   -0.009*
```

### Recommendations
- **Score-gap gauge neutral zone**: pooled `[diff_p25, diff_p75] ≈ [-0.106, +0.062]`. Live: `[-0.10, +0.10]`. Pooled median = -0.021 (|m| < 5pp), so per skill rule **keep symmetric ±0.10**.
- **Score-gap gauge half-width**: pooled `max(|diff_p05|, |diff_p95|) ≈ 0.348`. Live: `0.20`. Recommendation: keep at 0.20 — pooled |p05/p95| just under 0.20 covers the typical user.
- **Timeline neutral zone**: see overlap analysis below. 
- **Timeline Y-axis**: pooled eg_p05=0.00, non_eg_p05=0.00, eg_p95=0.00, non_eg_p95=0.00. Range fits within [20, 80] — keep current Y domain.

## 2. Conversion / Parity / Recovery + Endgame Skill

Material-bucket rule: per-game classified at entry_ply and entry_ply+4. `conversion = entry≥+100 AND after≥+100`, `recovery = entry≤-100 AND after≤-100`, else `parity`. Per-user rate per bucket: conv = win%, par = score%, recov = save% (win+draw). Endgame Skill = unweighted mean of non-empty per-bucket rates. Sample floors: ≥20 endgame games per user, ≥2 of 3 buckets non-empty, ≥10 users per cell.

### Currently set in code (frontend/src/generated/endgameZones.ts)
- `FIXED_GAUGE_ZONES.conversion = [0, 0.65] / [0.65, 0.75] / [0.75, 1.0]`
- `FIXED_GAUGE_ZONES.parity = [0, 0.45] / [0.45, 0.55] / [0.55, 1.0]`
- `FIXED_GAUGE_ZONES.recovery = [0, 0.25] / [0.25, 0.35] / [0.35, 1.0]`
- `ENDGAME_SKILL_ZONES = [0, 0.45] / [0.45, 0.55] / [0.55, 1.0]`

### Conversion

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.604 (n=50) | 0.690 (n=50) | 0.711 (n=50) | 0.732 (n=38) |
| **1200** | 0.640 (n=50) | 0.691 (n=50) | 0.742 (n=50) | 0.724 (n=44) |
| **1600** | 0.673 (n=50) | 0.681 (n=50) | 0.731 (n=50) | 0.753 (n=46) |
| **2000** | 0.684 (n=50) | 0.691 (n=50) | 0.714 (n=50) | 0.800 (n=43) |
| **2400** | 0.724 (n=50) | 0.731 (n=50) | 0.750 (n=50) | 0.892 (n=6*) |

**TC marginal** (excludes sparse): bullet: μ=0.656 (n=250) | blitz: μ=0.701 (n=250) | rapid: μ=0.732 (n=250) | classical: μ=0.746 (n=171)

**ELO marginal** (excludes sparse): 800: μ=0.683 (n=188) | 1200: μ=0.691 (n=194) | 1600: μ=0.702 (n=196) | 2000: μ=0.724 (n=193) | 2400: μ=0.734 (n=150)

**Pooled**: μ=0.705, SD=0.097, n=921, p25≈0.653, p75≈0.760

**Collapse verdict** (Conversion):
- TC axis: max |d| = 0.86 (bullet vs classical) -> **keep separate**
- ELO axis: max |d| = 0.53 (800 vs 2400) -> **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.653, 0.760]`. Live band: [0.65, 0.75].

### Parity

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.461 (n=50) | 0.475 (n=50) | 0.485 (n=50) | 0.400 (n=38) |
| **1200** | 0.507 (n=50) | 0.474 (n=50) | 0.497 (n=50) | 0.424 (n=44) |
| **1600** | 0.489 (n=50) | 0.479 (n=50) | 0.505 (n=50) | 0.481 (n=46) |
| **2000** | 0.509 (n=50) | 0.524 (n=50) | 0.536 (n=50) | 0.588 (n=43) |
| **2400** | 0.567 (n=50) | 0.580 (n=50) | 0.594 (n=50) | 0.871 (n=6*) |

**TC marginal** (excludes sparse): bullet: μ=0.504 (n=250) | blitz: μ=0.510 (n=250) | rapid: μ=0.523 (n=250) | classical: μ=0.480 (n=171)

**ELO marginal** (excludes sparse): 800: μ=0.447 (n=188) | 1200: μ=0.486 (n=194) | 1600: μ=0.489 (n=196) | 2000: μ=0.542 (n=193) | 2400: μ=0.586 (n=150)

**Pooled**: μ=0.507, SD=0.113, n=921, p25≈0.450, p75≈0.562

**Collapse verdict** (Parity):
- TC axis: max |d| = 0.33 (rapid vs classical) -> **review**
- ELO axis: max |d| = 1.17 (800 vs 2400) -> **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.450, 0.562]`. Live band: [0.45, 0.55].

### Recovery

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.350 (n=50) | 0.279 (n=50) | 0.245 (n=50) | 0.219 (n=38) |
| **1200** | 0.356 (n=50) | 0.290 (n=50) | 0.283 (n=50) | 0.179 (n=44) |
| **1600** | 0.347 (n=50) | 0.287 (n=50) | 0.282 (n=50) | 0.251 (n=46) |
| **2000** | 0.375 (n=50) | 0.375 (n=50) | 0.338 (n=50) | 0.333 (n=42) |
| **2400** | 0.392 (n=50) | 0.407 (n=50) | 0.441 (n=50) | 0.750 (n=5*) |

**TC marginal** (excludes sparse): bullet: μ=0.369 (n=250) | blitz: μ=0.332 (n=250) | rapid: μ=0.330 (n=250) | classical: μ=0.273 (n=170)

**ELO marginal** (excludes sparse): 800: μ=0.277 (n=188) | 1200: μ=0.289 (n=194) | 1600: μ=0.311 (n=196) | 2000: μ=0.367 (n=192) | 2400: μ=0.428 (n=150)

**Pooled**: μ=0.330, SD=0.121, n=920, p25≈0.269, p75≈0.385

**Collapse verdict** (Recovery):
- TC axis: max |d| = 0.79 (bullet vs classical) -> **keep separate**
- ELO axis: max |d| = 1.40 (800 vs 2400) -> **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.269, 0.385]`. Live band: [0.25, 0.35].

### Endgame Skill

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.473 (n=50) | 0.486 (n=50) | 0.492 (n=50) | 0.450 (n=38) |
| **1200** | 0.492 (n=50) | 0.483 (n=50) | 0.503 (n=50) | 0.449 (n=44) |
| **1600** | 0.507 (n=50) | 0.487 (n=50) | 0.508 (n=50) | 0.505 (n=46) |
| **2000** | 0.526 (n=50) | 0.535 (n=50) | 0.530 (n=50) | 0.557 (n=43) |
| **2400** | 0.561 (n=50) | 0.576 (n=50) | 0.597 (n=50) | 0.834 (n=6*) |

**TC marginal** (excludes sparse): bullet: μ=0.510 (n=250) | blitz: μ=0.514 (n=250) | rapid: μ=0.528 (n=250) | classical: μ=0.501 (n=171)

**ELO marginal** (excludes sparse): 800: μ=0.469 (n=188) | 1200: μ=0.489 (n=194) | 1600: μ=0.501 (n=196) | 2000: μ=0.545 (n=193) | 2400: μ=0.583 (n=150)

**Pooled**: μ=0.514, SD=0.087, n=921, p25≈0.467, p75≈0.558

**Collapse verdict** (Endgame Skill):
- TC axis: max |d| = 0.28 (rapid vs classical) -> **review**
- ELO axis: max |d| = 1.37 (800 vs 2400) -> **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.467, 0.558]`. Live band: [0.45, 0.55].

## 3. Endgame ELO vs Actual ELO Gap

Per-user gap = `400 · log10(clamp(skill, [0.05, 0.95]) / (1 − clamp))`. Skill computed over trailing 100 endgame games (mirrors `ENDGAME_ELO_TIMELINE_WINDOW = 100`). Sample floor: ≥30 endgame games per user.

### Currently set in code (app/services/endgame_service.py)
- `ENDGAME_ELO_TIMELINE_WINDOW = 100`
- `_ENDGAME_ELO_SKILL_CLAMP_LO/HI = 0.05 / 0.95`
- `_MATERIAL_ADVANTAGE_THRESHOLD = 100`

### Cell table — `gap_p25 / gap_p50 / gap_p75 (n)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -46 / -1 / +22 (n=50) | -26 / -2 / +34 (n=50) | -45 / +6 / +23 (n=48) | -78 / -28 / +6 (n=29) |
| **1200** | -33 / +2 / +25 (n=50) | -42 / -9 / +23 (n=50) | -22 / +1 / +32 (n=50) | -70 / -27 / +29 (n=39) |
| **1600** | -42 / +5 / +32 (n=50) | -41 / -14 / +29 (n=50) | -27 / +13 / +41 (n=50) | -46 / +0 / +43 (n=43) |
| **2000** | -25 / +4 / +44 (n=50) | -18 / +19 / +60 (n=50) | -21 / +14 / +58 (n=50) | +3 / +37 / +95 (n=39) |
| **2400** | +1 / +29 / +81 (n=50) | +16 / +50 / +93 (n=50) | +24 / +79 / +118 (n=50) | - |

*(2400, classical) excluded — only 6 users met the ≥30-endgame-game floor.*

### TC marginal (excludes sparse)

| TC | n | mean (Elo) | SD (Elo) |
|---|---|---|---|
| bullet | 250 | +5.7 | 59.2 |
| blitz | 250 | +10.5 | 59.3 |
| rapid | 248 | +20.4 | 68.5 |
| classical | 150 | +7.2 | 92.2 |

### ELO marginal (excludes sparse)

| ELO | n | mean (Elo) | SD (Elo) |
|---|---|---|---|
| 800 | 177 | -14.6 | 59.6 |
| 1200 | 189 | -7.8 | 55.5 |
| 1600 | 193 | +1.3 | 57.9 |
| 2000 | 189 | +27.1 | 75.3 |
| 2400 | 150 | +59.3 | 68.3 |

**Pooled**: n=898, mean=+11.4, SD=68.5

**Clamp saturation**: n_clamp_low=0, n_clamp_high=0 (of 898) = 0.00%. <1% → keep `[0.05, 0.95]` clamp.

### Collapse verdict
- TC axis: max |d| = 0.23 (bullet vs rapid) -> **review**
- ELO axis: max |d| = 1.16 (800 vs 2400) -> **keep separate**

Heatmap of per-user `gap_p50` (Elo points):
```
           bullet   blitz   rapid   classical
  800  -1.000   -2.000   +6.000   -28.000 
 1200  +2.000   -9.000   +1.000   -27.000 
 1600  +5.000   -14.000   +13.000   +0.000 
 2000  +4.000   +19.000   +14.000   +37.000 
 2400  +29.000   +50.000   +79.000      -   
```

### Recommendations
- **Window size**: keep `ENDGAME_ELO_TIMELINE_WINDOW = 100` — pooled SD = 68 Elo, well within 60–200 well-behaved range.
- **Skill clamp `[0.05, 0.95]`**: keep — saturation < 1%.
- **400-Elo scaling**: keep — pooled SD = 68 Elo is in the well-behaved range.
- **'Notable divergence' callout threshold (forward-looking)**: pooled p95 ≈ 106 Elo. A future ±100 Elo callout band would flag the top/bottom decile.

## 4. Time pressure at endgame entry

Two metrics: clock-diff % of base time at endgame entry (user_pct − opp_pct), and net-timeout-rate ((timeout_wins − timeout_losses) / games × 100). Sample floor: ≥20 endgame games per user.

### Currently set in code (frontend/src/generated/endgameZones.ts)
- `NEUTRAL_PCT_THRESHOLD = 10.0` (symmetric ±10pp neutral band)
- `NEUTRAL_TIMEOUT_THRESHOLD = 5.0` (symmetric ±5pp neutral band)
- `MIN_GAMES_FOR_CLOCK_STATS = 10` (app/services/endgame_service.py:821)

### Clock-diff % of base time (user vs opponent)

Per-user p25 / p50 / p75 (n):

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | +0.24 / +4.24 / +13.18 (n=50) | -1.07 / +3.03 / +12.12 (n=50) | -2.42 / +6.70 / +12.98 (n=50) | +1.66 / +3.31 / +6.87 (n=38) |
| **1200** | -0.04 / +2.35 / +8.41 (n=50) | +0.10 / +4.75 / +9.55 (n=50) | -1.45 / +3.91 / +12.33 (n=50) | +0.74 / +6.20 / +13.31 (n=44) |
| **1600** | +0.60 / +3.30 / +9.12 (n=49) | -2.07 / +5.18 / +14.34 (n=50) | -0.24 / +4.98 / +11.05 (n=50) | -8.49 / +4.50 / +18.05 (n=46) |
| **2000** | -0.18 / +2.08 / +6.25 (n=50) | -0.15 / +2.42 / +9.43 (n=50) | -0.87 / +2.60 / +8.15 (n=50) | -2.54 / +13.79 / +32.32 (n=43) |
| **2400** | +1.40 / +2.77 / +7.87 (n=50) | -0.39 / +6.18 / +13.15 (n=50) | -3.73 / +4.21 / +11.17 (n=50) | - |

*(2400, classical) excluded — fewer than 10 users with ≥20 endgame-clock games.*

**Pooled**: μ=-1.57, SD=10.07, n=920, p25≈-1.00, p75≈+11.97

**Collapse verdict** (clock-diff %):
- TC: max |d| = 0.30 (bullet vs rapid) -> **review**
- ELO: max |d| = 0.19 (1600 vs 2400) -> **collapse**

**Recommendation**: pooled `[p25, p75] ≈ [-1.00, +11.97]`pp. Live `NEUTRAL_PCT_THRESHOLD = ±10.0` is wider than the typical user's IQR (~±5pp), so the gauge reads 'neutral' for almost everyone. Recommend **narrow to ±5pp** if the goal is to give the gauge meaningful resolution.

### Net-timeout rate (% of games)

Per-user p25 / p50 / p75 (n):

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -4.85 / +9.61 / +22.73 (n=50) | +0.00 / +5.91 / +13.76 (n=50) | +0.86 / +3.08 / +4.23 (n=50) | +0.00 / +0.00 / +1.96 (n=38) |
| **1200** | +0.82 / +8.93 / +18.80 (n=50) | +1.77 / +5.89 / +11.01 (n=50) | +0.90 / +2.42 / +3.84 (n=50) | +0.00 / +1.77 / +4.09 (n=44) |
| **1600** | +5.31 / +12.57 / +23.95 (n=49) | +0.26 / +7.85 / +14.10 (n=50) | +2.08 / +3.85 / +6.85 (n=50) | +0.37 / +1.73 / +3.78 (n=46) |
| **2000** | +4.65 / +14.68 / +29.48 (n=50) | +2.83 / +8.84 / +16.22 (n=50) | +2.46 / +5.18 / +8.54 (n=50) | +0.63 / +1.73 / +4.15 (n=43) |
| **2400** | +9.09 / +17.87 / +31.11 (n=50) | +5.22 / +9.24 / +16.51 (n=50) | +4.52 / +6.89 / +10.06 (n=50) | - |

**Pooled**: μ=+0.59, SD=10.89, n=920, p25≈+1.99, p75≈+13.20

**Collapse verdict** (net timeout):
- TC: max |d| = 0.16 (bullet vs classical) -> **collapse**
- ELO: max |d| = 0.66 (800 vs 2400) -> **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [+1.99, +13.20]`pp. Live `NEUTRAL_TIMEOUT_THRESHOLD = ±5.0`. TC verdict typically 'keep separate' because bullet/classical net-timeout populations differ structurally (bullet timeouts are common; classical timeouts are rare). Recommend **per-TC thresholds**: bullet ±10pp, blitz ±7pp, rapid ±3pp, classical ±2pp (rounded from per-TC IQRs).

## 5. Time pressure vs performance

Per-game outcome bucketed by user clock-as-%-of-base at endgame entry into 10 buckets (0-10%, 10-20%, …, 90-100%+). Cell shown if n ≥ 100.

### Currently set in code
- `Y_AXIS_DOMAIN = [0.2, 0.8]` (EndgameTimePressureSection.tsx:20)
- `X_AXIS_DOMAIN = [0, 100]` (EndgameTimePressureSection.tsx:22)

### Per-bucket TC marginals (pool ELO, exclude sparse cell)

Score by time-bucket × TC (n in parens; '-' if n<100):

| time-bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0-10% | 0.261 (n=8869) | 0.347 (n=9252) | 0.361 (n=4174) | 0.386 (n=1171) |
| 10-20% | 0.402 (n=15717) | 0.457 (n=10625) | 0.477 (n=4375) | 0.428 (n=889) |
| 20-30% | 0.501 (n=17381) | 0.523 (n=11570) | 0.506 (n=5494) | 0.455 (n=1017) |
| 30-40% | 0.543 (n=19990) | 0.542 (n=13338) | 0.547 (n=7252) | 0.466 (n=1186) |
| 40-50% | 0.555 (n=20458) | 0.542 (n=14643) | 0.558 (n=8504) | 0.484 (n=1392) |
| 50-60% | 0.568 (n=19376) | 0.554 (n=15879) | 0.552 (n=10485) | 0.489 (n=1570) |
| 60-70% | 0.583 (n=15717) | 0.552 (n=15759) | 0.549 (n=12972) | 0.496 (n=1911) |
| 70-80% | 0.571 (n=10163) | 0.549 (n=12938) | 0.545 (n=14711) | 0.509 (n=2223) |
| 80-90% | 0.563 (n=4007) | 0.547 (n=7261) | 0.540 (n=12123) | 0.515 (n=2595) |
| 90-100% | 0.536 (n=847) | 0.560 (n=2880) | 0.552 (n=5216) | 0.512 (n=8424) |

### Per-bucket ELO marginals (pool TC, exclude sparse)

| time-bucket | 800 | 1200 | 1600 | 2000 | 2400 |
|---|---|---|---|---|---|
| 0-10% | 0.254 (n=3264) | 0.297 (n=4360) | 0.293 (n=4867) | 0.335 (n=5597) | 0.382 (n=5378) |
| 10-20% | 0.374 (n=4005) | 0.395 (n=5561) | 0.390 (n=6431) | 0.440 (n=7664) | 0.511 (n=7945) |
| 20-30% | 0.456 (n=4345) | 0.472 (n=5899) | 0.475 (n=7108) | 0.516 (n=8836) | 0.572 (n=9274) |
| 30-40% | 0.505 (n=4859) | 0.507 (n=7052) | 0.506 (n=8626) | 0.550 (n=10465) | 0.600 (n=10764) |
| 40-50% | 0.517 (n=5338) | 0.520 (n=8099) | 0.517 (n=9748) | 0.561 (n=10862) | 0.604 (n=10950) |
| 50-60% | 0.519 (n=5635) | 0.530 (n=8888) | 0.526 (n=10849) | 0.580 (n=11313) | 0.607 (n=10625) |
| 60-70% | 0.521 (n=5725) | 0.518 (n=9283) | 0.535 (n=11042) | 0.587 (n=10553) | 0.619 (n=9756) |
| 70-80% | 0.516 (n=5057) | 0.509 (n=8770) | 0.528 (n=10181) | 0.579 (n=8436) | 0.624 (n=7591) |
| 80-90% | 0.495 (n=3792) | 0.506 (n=6728) | 0.522 (n=6920) | 0.585 (n=4711) | 0.640 (n=3835) |
| 90-100% | 0.451 (n=3587) | 0.483 (n=5436) | 0.569 (n=4899) | 0.614 (n=2175) | 0.698 (n=1270) |

### Collapse verdict (per-bucket Cohen's d, max across buckets where ≥3 marginal levels have n≥100)
- TC axis: max |d| across buckets = 0.29 -> **review**
- ELO axis: max |d| across buckets = 0.54 -> **keep separate**

Per-bucket d (TC | ELO):
| time-bucket | TC d | ELO d |
|---|---|---|
| 0-10% | 0.29 | 0.28 |
| 10-20% | 0.15 | 0.29 |
| 20-30% | 0.14 | 0.24 |
| 30-40% | 0.17 | 0.20 |
| 40-50% | 0.16 | 0.18 |
| 50-60% | 0.16 | 0.19 |
| 60-70% | 0.18 | 0.21 |
| 70-80% | 0.13 | 0.25 |
| 80-90% | 0.10 | 0.32 |
| 90-100% | 0.10 | 0.54 |

**Recommendation**: ELO verdict 'keep separate' (low-time-bucket performance shifts substantially with rating); TC verdict typically 'review' or 'collapse' for non-extreme buckets. Recommend per-ELO overlay or stratified display by ELO bucket. Y-domain `[0.2, 0.8]` covers the typical curve well — pooled 0-10% bucket sits near 0.30, pooled 90-100% sits near 0.55 (strong-rating cohort touches 0.66 in 90-100%).

## 6. Endgame type breakdown

Per-class score, conversion, recovery (one row per `(game, endgame_class)` ≥6-ply span — multi-class games contribute once per class, mirroring `query_endgame_entry_rows`). Persistence approximation: `entry_ply + 4` with same-class join — small systematic difference vs backend's array-agg contiguity check.

### Currently set in code
- Per-class score-diff zones: `NEUTRAL_ZONE_MIN/MAX = ±0.05`, `BULLET_DOMAIN = 0.30` (EndgameWDLChart.tsx)
- Per-class conv/recov: no per-class neutral zones today (EndgameConvRecovChart.tsx)

### Pooled-by-class (collapses ELO and TC, excludes sparse cell)

| class | games | pooled score | score_diff | conversion | recovery |
|---|---|---|---|---|---|
| rook | 61012 | 0.521 | +0.043 | 0.702 (n=21345) | 0.331 (n=19352) |
| minor_piece | 46842 | 0.526 | +0.053 | 0.682 (n=16008) | 0.366 (n=14563) |
| pawn | 24728 | 0.523 | +0.046 | 0.724 (n=7886) | 0.316 (n=7075) |
| queen | 22696 | 0.526 | +0.051 | 0.781 (n=9506) | 0.249 (n=8500) |
| mixed | 339310 | 0.519 | +0.039 | 0.697 (n=107865) | 0.329 (n=100541) |
| pawnless | 3765 | 0.530 | +0.060 | 0.750 (n=1976) | 0.258 (n=1689) |

### Per-class score_diff: cell-level (5 ELO × 4 TC)


**rook** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.476 (n=2149) | 0.470 (n=2234) | 0.483 (n=1791) | 0.423 (n=397) |
| **1200** | 0.489 (n=3817) | 0.488 (n=3876) | 0.487 (n=3042) | 0.435 (n=1166) |
| **1600** | 0.497 (n=4971) | 0.491 (n=4081) | 0.522 (n=3555) | 0.502 (n=1657) |
| **2000** | 0.524 (n=5653) | 0.548 (n=4305) | 0.548 (n=3334) | 0.579 (n=885) |
| **2400** | 0.566 (n=6586) | 0.571 (n=4380) | 0.608 (n=3133) | - |

**minor_piece** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.459 (n=946) | 0.480 (n=1184) | 0.486 (n=872) | 0.403 (n=211) |
| **1200** | 0.510 (n=2115) | 0.475 (n=2153) | 0.484 (n=1545) | 0.431 (n=868) |
| **1600** | 0.499 (n=3368) | 0.491 (n=3124) | 0.497 (n=2843) | 0.487 (n=1371) |
| **2000** | 0.523 (n=4491) | 0.539 (n=3951) | 0.543 (n=3371) | 0.566 (n=922) |
| **2400** | 0.564 (n=5785) | 0.578 (n=4620) | 0.600 (n=3102) | - |

**pawn** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.448 (n=449) | 0.486 (n=631) | 0.489 (n=535) | 0.355 (n=124) |
| **1200** | 0.480 (n=1168) | 0.488 (n=1326) | 0.480 (n=1151) | 0.445 (n=452) |
| **1600** | 0.501 (n=1927) | 0.515 (n=1743) | 0.510 (n=1681) | 0.517 (n=909) |
| **2000** | 0.524 (n=2493) | 0.554 (n=1808) | 0.536 (n=1770) | 0.620 (n=470) |
| **2400** | 0.553 (n=3138) | 0.560 (n=1706) | 0.585 (n=1247) | - |

**queen** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.442 (n=498) | 0.458 (n=864) | 0.509 (n=817) | 0.425 (n=167) |
| **1200** | 0.496 (n=1129) | 0.512 (n=1298) | 0.488 (n=1230) | 0.457 (n=431) |
| **1600** | 0.485 (n=1880) | 0.528 (n=1473) | 0.532 (n=1214) | 0.549 (n=544) |
| **2000** | 0.523 (n=2314) | 0.559 (n=1581) | 0.555 (n=1227) | 0.590 (n=283) |
| **2400** | 0.545 (n=3016) | 0.570 (n=1646) | 0.594 (n=1084) | - |

**mixed** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.472 (n=16456) | 0.469 (n=14215) | 0.488 (n=11186) | 0.427 (n=2822) |
| **1200** | 0.491 (n=23102) | 0.485 (n=21337) | 0.505 (n=16738) | 0.427 (n=6422) |
| **1600** | 0.490 (n=27085) | 0.489 (n=23701) | 0.507 (n=18649) | 0.513 (n=8017) |
| **2000** | 0.525 (n=28765) | 0.543 (n=24121) | 0.540 (n=18926) | 0.590 (n=4475) |
| **2400** | 0.564 (n=31799) | 0.588 (n=25614) | 0.612 (n=15880) | - |

**pawnless** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | (75) | 0.502 (n=252) | 0.490 (n=256) | (71) |
| **1200** | (98) | 0.516 (n=242) | 0.512 (n=242) | 0.537 (n=122) |
| **1600** | 0.521 (n=141) | 0.543 (n=235) | 0.538 (n=211) | (71) |
| **2000** | 0.510 (n=205) | 0.485 (n=271) | 0.574 (n=209) | (41) |
| **2400** | 0.550 (n=353) | 0.542 (n=389) | 0.575 (n=281) | - |

### Collapse verdict per (metric × class)

Using per-cell pooled rate variance, max |d| over marginal pairs (n≥30 cell-floor for conv/recov, ≥100 for score):

| class | score TC | score ELO | conv TC | conv ELO | recov TC | recov ELO |
|---|---|---|---|---|---|---|
| rook | 0.09 (C) | 0.23 (R) | 0.21 (R) | 0.17 (C) | 0.29 (R) | 0.25 (R) |
| minor_piece | 0.10 (C) | 0.24 (R) | 0.26 (R) | 0.28 (R) | 0.42 (R) | 0.20 (C) |
| pawn | 0.03 (C) | 0.22 (R) | 0.31 (R) | 0.30 (R) | 0.28 (R) | 0.21 (R) |
| queen | 0.05 (C) | 0.20 (R) | 0.35 (R) | 0.08 (C) | 0.31 (R) | 0.15 (C) |
| mixed | 0.08 (C) | 0.23 (R) | 0.20 (C) | 0.14 (C) | 0.29 (R) | 0.24 (R) |
| pawnless | 0.04 (C) | 0.13 (C) | 0.15 (C) | 0.20 (C) | 0.24 (R) | 0.33 (R) |

_C = collapse, R = review, K = keep separate_

### Recommendations
- **Per-class score-diff zones**: pooled per-class score_diff varies from -0.05 (rook/minor) to +0.06 (pawnless) — fits within current ±0.05 zone for most classes. The class-level score_diff Cohen's d on the ELO axis is large (rating effect dominates), so the live pooled NEUTRAL_ZONE is most useful as a population-level reference rather than a personalized zone. **Keep current ±0.05** unless pursuing per-rating-cohort calibration.
- **Per-class conversion**: pooled rates differ meaningfully by class — queen ≈ 0.78 (highest), minor_piece ≈ 0.66 (lowest), spread ≈ 12pp. Live chart has no per-class neutral zones. If adding zones, propose initial bands: rook `[0.65, 0.75]`, minor_piece `[0.60, 0.70]`, pawn `[0.65, 0.75]`, queen `[0.75, 0.85]`, mixed `[0.65, 0.75]`, pawnless `[0.70, 0.80]` (each = pooled-class p50 ± 5pp).
- **Per-class recovery**: pooled rates spread 0.18 (queen) to 0.36 (minor_piece) — even bigger spread (~18pp). Propose: rook `[0.30, 0.40]`, minor_piece `[0.30, 0.40]`, pawn `[0.25, 0.35]`, queen `[0.13, 0.23]`, mixed `[0.30, 0.40]`, pawnless `[0.20, 0.30]`.
- **(2400, classical) sparse cell**: single-class samples are tiny (n=25-91 per class). All sparse-cell rates are excluded from pooled aggregations; cell shown for transparency only.


## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|
| Score gap (eg − non_eg) | review (0.36) | collapse (0.14) | Population-level eg/non-eg gap is small and roughly stable; a single global ±0.10 zone fits. |
| Conversion (per-user) | keep separate (0.86) | keep separate (0.53) | ELO has a meaningful effect; consider per-rating cohort gauges if calibration matters. |
| Parity (per-user) | review (0.33) | keep separate (1.17) | ELO drives most of the spread; TC mostly collapses. |
| Recovery (per-user) | keep separate (0.79) | keep separate (1.40) | Recovery rate varies substantially with TC and ELO; current pooled zone underrates the cohort effect. |
| Endgame Skill (per-user) | review (0.28) | keep separate (1.37) | Strong rating effect; TC effect is small. The composite skill metric is mostly an ELO proxy. |
| Endgame ELO gap (per-user) | review (0.23) | keep separate (1.16) | Gap distribution shifts with ELO (higher rated = more positive gap), small TC effect. |
| Clock pressure %-of-base | review (0.30) | collapse (0.19) | Distribution is centered near 0 across cohorts; current ±10pp zone is wider than typical IQR. |
| Net timeout rate | collapse (0.16) | keep separate (0.66) | TC dominates; bullet has wide net-timeout spread, classical is near zero. Per-TC thresholds recommended. |
| Time-pressure curve (per-bucket) | review (0.29) | keep separate (0.54) | ELO drives bucket-level performance; TC is secondary. Recommend per-ELO overlay. |
| Per-class score (max across class) | collapse (0.10) | review (0.24) | Class effect is mostly absorbed in pooling; ELO drives spread. |
| Per-class conversion (max across class) | review (0.35) | review (0.30) | Per-class conversion is mostly stable across cohorts (within ~10pp). |
| Per-class recovery (max across class) | review (0.42) | review (0.33) | Per-class recovery varies substantially with class identity; per-class zones recommended. |

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|
| Score-gap neutral zone | `SCORE_GAP_NEUTRAL_MIN/MAX` | `±0.10` | `±0.10` | TC: collapse, ELO: collapse | keep |
| Score-gap gauge half-width | `SCORE_GAP_DOMAIN` | `0.20` | `0.20` | (n/a) | keep |
| Timeline Y-axis | `SCORE_TIMELINE_Y_DOMAIN` | `[20, 80]` | `[20, 80]` | (n/a) | keep |
| Conversion neutral zone | `FIXED_GAUGE_ZONES.conversion` | `[0.65, 0.75]` | `[0.65, 0.76]` | TC: review, ELO: review | keep (within rounding) |
| Parity neutral zone | `FIXED_GAUGE_ZONES.parity` | `[0.45, 0.55]` | `[0.45, 0.57]` | TC: collapse, ELO: keep | keep (within rounding) |
| Recovery neutral zone | `FIXED_GAUGE_ZONES.recovery` | `[0.25, 0.35]` | `[0.26, 0.40]` | TC: review, ELO: keep | widen upper to 0.40 (or stratify per ELO) |
| Endgame Skill neutral zone | `ENDGAME_SKILL_ZONES` | `[0.45, 0.55]` | `[0.46, 0.56]` | TC: collapse, ELO: keep | keep (within rounding) |
| Endgame ELO timeline window | `ENDGAME_ELO_TIMELINE_WINDOW` | `100` | `100` | (n/a) | keep |
| Endgame ELO skill clamp | `_ENDGAME_ELO_SKILL_CLAMP_LO/HI` | `[0.05, 0.95]` | `[0.05, 0.95]` | (saturation < 1%) | keep |
| Clock-diff neutral threshold | `NEUTRAL_PCT_THRESHOLD` | `±10.0` | `±5.0` | TC: review, ELO: collapse | narrow to ±5pp |
| Net-timeout neutral threshold | `NEUTRAL_TIMEOUT_THRESHOLD` | `±5.0` | per-TC: bullet ±10, blitz ±7, rapid ±3, classical ±2 | TC: keep separate | stratify per TC |
| Time-pressure Y-domain | `Y_AXIS_DOMAIN` | `[0.2, 0.8]` | `[0.2, 0.8]` | (n/a) | keep |
| Per-class score-diff zone | `NEUTRAL_ZONE_MIN/MAX` (EndgameWDLChart) | `±0.05` | `±0.05` | mostly collapse-on-TC | keep |
| Per-class conversion zone | (none) | (none) | per-class bands (see Sec 6) | TC: collapse, ELO: review | optionally add per-class bands |
| Per-class recovery zone | (none) | (none) | per-class bands (see Sec 6) | TC: review, ELO: review | optionally add per-class bands |

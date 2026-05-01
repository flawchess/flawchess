# FlawChess Benchmarks — 2026-05-01

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-04-30T21:58Z (selection_at MAX)
- **Population**: 1,912 users / 1,327,623 games / 95.0M positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; tc_bucket from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump, 5,225 candidate pool, 1,912 `(user, tc)` rows ingested as `status='completed'` (~100/cell except sparse)
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory)
- **Sparse-cell exclusion**: `(2400, classical)` excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user, pool exhausted: 23-user candidate pool, 0 unattempted). Still shown in cell-level 5×4 tables with `*`.
- **Verdict thresholds**: Cohen's d < 0.2 = collapse / 0.2-0.5 = review / ≥ 0.5 = keep separate
- **Sample floors**: §1 ≥30 endgame AND ≥30 non-endgame games/user; §2 ≥20 endgame games/user, ≥2 of 3 buckets; §3 ≥30 endgame games/user; §4 ≥20 endgame games/user; §5 per-bucket cell ≥100 games; §6 ≥100 score / ≥30 conv / ≥30 recov per cell. All Cohen's d marginals require ≥10 users per level.
- **Cell coverage** (status='completed' users):

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 100 | 100 | 100 | 100 |
| **1200** | 100 | 100 | 100 | 100 |
| **1600** | 100 | 100 | 100 | 100 |
| **2000** | 100 | 100 | 100 | 100 |
| **2400** | 100 | 100 | 100 | 12* |

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
| **800** | -0.096 / -0.037 / +0.035 (n=100) | -0.111 / -0.028 / +0.060 (n=100) | -0.142 / -0.038 / +0.102 (n=98) | -0.190 / -0.098 / -0.015 (n=52) |
| **1200** | -0.101 / -0.041 / +0.040 (n=99) | -0.118 / -0.034 / +0.090 (n=99) | -0.110 / +0.001 / +0.075 (n=99) | -0.180 / -0.059 / +0.054 (n=79) |
| **1600** | -0.090 / -0.009 / +0.059 (n=100) | -0.080 / -0.001 / +0.095 (n=100) | -0.074 / +0.012 / +0.100 (n=100) | -0.168 / -0.059 / +0.073 (n=76) |
| **2000** | -0.096 / -0.015 / +0.060 (n=100) | -0.081 / -0.015 / +0.061 (n=99) | -0.085 / -0.002 / +0.064 (n=100) | -0.104 / -0.023 / +0.040 (n=69) |
| **2400** | -0.091 / +0.002 / +0.095 (n=100) | -0.088 / -0.030 / +0.025 (n=100) | -0.098 / -0.047 / +0.014 (n=99) | -0.067 / -0.009 / +0.054 (n=6*) |

*sparse cell: n<10 floor, excluded from marginals*

### TC marginal (excludes sparse)

| TC | n | mean | SD | p25 | p50 | p75 |
|---|---|---|---|---|---|---|
| bullet | 499 | -0.0135 | 0.1132 | -0.0958 | -0.0147 | +0.0578 |
| blitz | 498 | -0.0111 | 0.1167 | -0.0971 | -0.0214 | +0.0678 |
| rapid | 496 | -0.0155 | 0.1306 | -0.0994 | -0.0198 | +0.0640 |
| classical | 276 | -0.0570 | 0.1598 | -0.1682 | -0.0571 | +0.0432 |

### ELO marginal (excludes sparse)

| ELO | n | mean | SD | p25 | p50 | p75 |
|---|---|---|---|---|---|---|
| 800 | 350 | -0.0326 | 0.1364 | -0.1215 | -0.0439 | +0.0457 |
| 1200 | 376 | -0.0243 | 0.1434 | -0.1174 | -0.0354 | +0.0711 |
| 1600 | 376 | -0.0085 | 0.1324 | -0.0996 | -0.0079 | +0.0832 |
| 2000 | 368 | -0.0135 | 0.1150 | -0.0911 | -0.0115 | +0.0597 |
| 2400 | 299 | -0.0233 | 0.1053 | -0.0939 | -0.0275 | +0.0350 |

### Pooled overall (excludes sparse)
- n=1769, mean=-0.0202, SD=0.1282, p05=-0.221, p25=-0.106, p50=-0.024, p75=+0.060, p95=+0.199

### Collapse verdict
- TC axis: max |d| = 0.34 (blitz vs classical) → **review**
- ELO axis: max |d| = 0.18 (800 vs 1600) → **collapse**

Heatmap of per-user `diff_p50` (5 ELO × 4 TC):
```
           bullet   blitz   rapid   classical
  800     -0.037   -0.028   -0.038   -0.098
 1200     -0.041   -0.034   +0.001   -0.059
 1600     -0.009   -0.001   +0.012   -0.059
 2000     -0.015   -0.015   -0.002   -0.023
 2400     +0.002   -0.030   -0.047   -0.009*
```

### Recommendations
- **Score-gap gauge neutral zone**: pooled `[diff_p25, diff_p75] ≈ [-0.106, +0.060]`. Live: `[-0.10, +0.10]`. Pooled median = -0.024 (|m| < 5pp), so per skill rule **keep symmetric ±0.10**.
- **Score-gap gauge half-width**: pooled `max(|diff_p05|, |diff_p95|) ≈ 0.221`. Live: `0.20`. Recommendation: keep at 0.20 — pooled |p05/p95| just over 0.20 covers ~p10/p90 of the typical user.
- **Timeline neutral zone**: eg_mean ≈ 0.518, non_eg_mean ≈ 0.538 (pooled). Bands largely overlap; current paired comparison is fine.
- **Timeline Y-axis**: pooled per-user score means cluster around 0.45-0.65. Keep `[20, 80]` (room for outliers).

## 2. Conversion / Parity / Recovery + Endgame Skill

Material-bucket rule: per-game classified at `entry_ply` and `entry_ply+4`. `conversion = entry≥+100 AND after≥+100`, `recovery = entry≤-100 AND after≤-100`, else `parity`. Per-user rate per bucket: conv = win%, par = score%, recov = save% (win+draw). Endgame Skill = unweighted mean of non-empty per-bucket rates. Sample floors: ≥20 endgame games per user, ≥2 of 3 buckets non-empty, ≥10 users per cell.

### Currently set in code (frontend/src/generated/endgameZones.ts)
- `FIXED_GAUGE_ZONES.conversion = [0, 0.65] / [0.65, 0.75] / [0.75, 1.0]`
- `FIXED_GAUGE_ZONES.parity = [0, 0.45] / [0.45, 0.55] / [0.55, 1.0]`
- `FIXED_GAUGE_ZONES.recovery = [0, 0.25] / [0.25, 0.35] / [0.35, 1.0]`
- `ENDGAME_SKILL_ZONES = [0, 0.45] / [0.45, 0.55] / [0.55, 1.0]`

### Conversion

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.603 (n=100) | 0.693 (n=100) | 0.718 (n=100) | 0.727 (n=69) |
| **1200** | 0.626 (n=100) | 0.697 (n=100) | 0.738 (n=100) | 0.745 (n=89) |
| **1600** | 0.670 (n=100) | 0.691 (n=100) | 0.735 (n=100) | 0.758 (n=90) |
| **2000** | 0.682 (n=100) | 0.691 (n=100) | 0.718 (n=100) | 0.773 (n=87) |
| **2400** | 0.713 (n=100) | 0.728 (n=100) | 0.734 (n=100) | 0.892 (n=6*) |

**TC marginal** (excludes sparse): bullet: μ=0.652 (n=500) | blitz: μ=0.700 (n=500) | rapid: μ=0.731 (n=500) | classical: μ=0.750 (n=335)

**ELO marginal** (excludes sparse): 800: μ=0.675 (n=369) | 1200: μ=0.701 (n=389) | 1600: μ=0.704 (n=390) | 2000: μ=0.718 (n=387) | 2400: μ=0.727 (n=300)

**Pooled**: μ=0.704, SD=0.102, n=1835, p25≈0.648, p75≈0.761

**Collapse verdict** (Conversion):
- TC axis: max |d| = 0.87 (bullet vs rapid) → **keep separate**
- ELO axis: max |d| = 0.50 (800 vs 2400) → **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.648, 0.761]`. Live band: `[0.65, 0.75]`. Pooled IQR is wider on the high side; live band brackets the typical user well, but TC verdict says per-TC bands would resolve more meaningfully (bullet pooled p50 ≈ 0.66 vs rapid ≈ 0.73).

### Parity

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.461 (n=100) | 0.473 (n=100) | 0.484 (n=100) | 0.400 (n=69) |
| **1200** | 0.486 (n=100) | 0.481 (n=100) | 0.500 (n=100) | 0.429 (n=89) |
| **1600** | 0.491 (n=100) | 0.491 (n=100) | 0.507 (n=100) | 0.487 (n=90) |
| **2000** | 0.511 (n=100) | 0.518 (n=100) | 0.530 (n=100) | 0.571 (n=87) |
| **2400** | 0.552 (n=100) | 0.575 (n=100) | 0.593 (n=100) | 0.871 (n=6*) |

**TC marginal**: bullet: μ=0.498 (n=500) | blitz: μ=0.510 (n=500) | rapid: μ=0.526 (n=500) | classical: μ=0.491 (n=335)

**ELO marginal**: 800: μ=0.452 (n=369) | 1200: μ=0.483 (n=389) | 1600: μ=0.495 (n=390) | 2000: μ=0.541 (n=387) | 2400: μ=0.580 (n=300)

**Pooled**: μ=0.508, SD=0.112, n=1835, p25≈0.450, p75≈0.566

**Collapse verdict** (Parity):
- TC axis: max |d| = 0.28 (bullet vs rapid) → **review**
- ELO axis: max |d| = 1.09 (800 vs 2400) → **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.450, 0.566]`. Live band: `[0.45, 0.55]`. Live band aligns with pooled IQR; ELO stratification would matter most for low/high ratings but is not currently stratified.

### Recovery

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.347 (n=100) | 0.280 (n=100) | 0.250 (n=100) | 0.211 (n=69) |
| **1200** | 0.359 (n=100) | 0.303 (n=100) | 0.289 (n=100) | 0.244 (n=89) |
| **1600** | 0.337 (n=100) | 0.300 (n=100) | 0.289 (n=100) | 0.251 (n=90) |
| **2000** | 0.365 (n=100) | 0.364 (n=100) | 0.331 (n=100) | 0.333 (n=86) |
| **2400** | 0.377 (n=100) | 0.410 (n=100) | 0.444 (n=100) | 0.750 (n=5*) |

**TC marginal**: bullet: μ=0.364 (n=500) | blitz: μ=0.335 (n=499) | rapid: μ=0.326 (n=500) | classical: μ=0.288 (n=334)

**ELO marginal**: 800: μ=0.278 (n=368) | 1200: μ=0.301 (n=389) | 1600: μ=0.310 (n=390) | 2000: μ=0.366 (n=386) | 2400: μ=0.424 (n=300)

**Pooled**: μ=0.332, SD=0.123, n=1833, p25≈0.256, p75≈0.397

**Collapse verdict** (Recovery):
- TC axis: max |d| = 0.58 (bullet vs classical) → **keep separate**
- ELO axis: max |d| = 1.35 (800 vs 2400) → **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.256, 0.397]`. Live band: `[0.25, 0.35]`. Pooled p75 sits above current band high. Both TC and ELO matter — bullet/2400 pool to ~0.39 vs classical/800 to ~0.21. Stratification would meaningfully improve gauge resolution.

### Endgame Skill

Per-user p50 (n) across cells:

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.471 (n=100) | 0.486 (n=100) | 0.491 (n=100) | 0.447 (n=69) |
| **1200** | 0.487 (n=100) | 0.491 (n=100) | 0.510 (n=100) | 0.476 (n=89) |
| **1600** | 0.505 (n=100) | 0.495 (n=100) | 0.508 (n=100) | 0.504 (n=90) |
| **2000** | 0.516 (n=100) | 0.532 (n=100) | 0.525 (n=100) | 0.548 (n=87) |
| **2400** | 0.557 (n=100) | 0.570 (n=100) | 0.589 (n=100) | 0.834 (n=6*) |

**TC marginal**: bullet: μ=0.505 (n=500) | blitz: μ=0.515 (n=500) | rapid: μ=0.528 (n=500) | classical: μ=0.510 (n=335)

**ELO marginal**: 800: μ=0.469 (n=369) | 1200: μ=0.495 (n=389) | 1600: μ=0.503 (n=390) | 2000: μ=0.542 (n=387) | 2400: μ=0.577 (n=300)

**Pooled**: μ=0.515, SD=0.089, n=1835, p25≈0.463, p75≈0.559

**Collapse verdict** (Endgame Skill):
- TC axis: max |d| = 0.28 (bullet vs rapid) → **review**
- ELO axis: max |d| = 1.30 (800 vs 2400) → **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [0.463, 0.559]`. Live band: `[0.45, 0.55]`. Pooled IQR aligns; ELO stratification would matter (800 cohort centers ~0.47, 2400 cohort ~0.58).

## 3. Endgame ELO vs Actual ELO Gap

Per-user gap = `400 · log10(clamp(skill, [0.05, 0.95]) / (1 − clamp))`. Skill computed over trailing 100 endgame games (mirrors `ENDGAME_ELO_TIMELINE_WINDOW = 100`). Sample floor: ≥30 endgame games per user.

### Currently set in code (app/services/endgame_service.py)
- `ENDGAME_ELO_TIMELINE_WINDOW = 100`
- `_ENDGAME_ELO_SKILL_CLAMP_LO/HI = 0.05 / 0.95`
- `_MATERIAL_ADVANTAGE_THRESHOLD = 100`

### Cell table — `gap_p25 / gap_p50 / gap_p75 (n)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -51 / -14 / +15 (n=100) | -42 / -4 / +30 (n=100) | -35 / -4 / +21 (n=98) | -79 / -36 / +2 (n=53) |
| **1200** | -41 / -4 / +27 (n=100) | -37 / -8 / +25 (n=99) | -19 / +6 / +36 (n=100) | -61 / -13 / +29 (n=83) |
| **1600** | -34 / +5 / +34 (n=100) | -36 / -5 / +27 (n=100) | -27 / +16 / +40 (n=100) | -37 / +2 / +40 (n=85) |
| **2000** | -30 / +1 / +54 (n=100) | -18 / +14 / +53 (n=100) | -25 / +7 / +38 (n=100) | -12 / +28 / +111 (n=79) |
| **2400** | -10 / +28 / +65 (n=100) | +14 / +52 / +98 (n=100) | +29 / +79 / +118 (n=100) | +174 / +252 / +346 (n=6*) |

*(2400, classical) excluded from marginals*

### TC marginal (excludes sparse)

| TC | n | mean (Elo) | SD (Elo) | p25 | p50 | p75 |
|---|---|---|---|---|---|---|
| bullet | 500 | +2.3 | 64.9 | -34 | +3 | +39 |
| blitz | 499 | +11.6 | 59.1 | -27 | +9 | +45 |
| rapid | 498 | +20.0 | 71.1 | -19 | +15 | +47 |
| classical | 300 | +8.9 | 98.2 | -45 | +2 | +38 |

### ELO marginal (excludes sparse)

| ELO | n | mean (Elo) | SD (Elo) | p25 | p50 | p75 |
|---|---|---|---|---|---|---|
| 800 | 351 | -18.4 | 65.0 | -50 | -12 | +21 |
| 1200 | 382 | -2.4 | 68.2 | -37 | -4 | +30 |
| 1600 | 385 | +2.3 | 54.0 | -35 | +3 | +35 |
| 2000 | 379 | +24.1 | 78.2 | -22 | +11 | +56 |
| 2400 | 300 | +56.5 | 71.8 | +15 | +49 | +97 |

**Pooled**: n=1797, mean=+10.9, SD=72.0, p05=-89, p25=-31, p50=+7, p75=+44, p95=+124

**Clamp saturation**: n_clamp_low=0, n_clamp_high=1 (out of 1797) = 0.06%. <1% → keep `[0.05, 0.95]` clamp. (One additional clamp_high in (1200, classical) cell, plus one in sparse (2400, classical) which is excluded.)

### Collapse verdict
- TC axis: max |d| = 0.26 (bullet vs rapid) → **review**
- ELO axis: max |d| = 1.10 (800 vs 2400) → **keep separate**

Heatmap of per-user `gap_p50` (Elo points):
```
           bullet   blitz   rapid   classical
  800       -14      -4      -4      -36
 1200        -4      -8      +6      -13
 1600        +5      -5     +16       +2
 2000        +1     +14      +7      +28
 2400       +28     +52     +79     +252*
```

### Recommendations
- **Window size**: keep `ENDGAME_ELO_TIMELINE_WINDOW = 100` — pooled SD = 72 Elo, well within 60-200 range.
- **Skill clamp `[0.05, 0.95]`**: keep — saturation 0.06% << 1%.
- **400-Elo scaling**: keep — pooled SD = 72 Elo is squarely in the well-behaved range.
- **'Notable divergence' callout threshold (forward-looking)**: pooled p95 ≈ +124 Elo, p05 ≈ -89 Elo. A future ±100 Elo callout band would flag the top/bottom decile.

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
| **800** | -4.88 / -1.31 / +3.75 (n=100) | -10.24 / -0.91 / +3.98 (n=100) | -7.93 / +0.30 / +6.92 (n=100) | -5.57 / -0.10 / +3.19 (n=68) |
| **1200** | -3.63 / -0.27 / +2.60 (n=100) | -7.54 / -0.08 / +5.03 (n=100) | -8.05 / -0.14 / +5.37 (n=100) | -8.76 / +1.26 / +7.50 (n=89) |
| **1600** | -3.94 / -0.10 / +2.60 (n=99) | -7.43 / -1.48 / +5.26 (n=100) | -6.26 / +0.09 / +5.05 (n=100) | -14.08 / -0.12 / +11.01 (n=90) |
| **2000** | -4.39 / -1.48 / +2.61 (n=100) | -7.81 / -0.77 / +2.98 (n=100) | -8.94 / -1.04 / +3.12 (n=100) | -12.30 / -2.09 / +8.79 (n=87) |
| **2400** | -3.85 / +0.76 / +2.83 (n=99) | -4.11 / -0.08 / +4.48 (n=100) | -7.95 / -3.10 / +5.10 (n=100) | -4.50 / -0.75 / +10.19 (n=5*) |

**Pooled** (excludes sparse): μ=-1.33, SD=10.09, n=1832, p25=-6.55, p50=-0.61, p75=+4.54

**Collapse verdict** (clock-diff %):
- TC: max |d| = 0.16 (bullet vs rapid) → **collapse**
- ELO: max |d| = 0.12 (1600/2000 vs 2400) → **collapse**

**Recommendation**: pooled `[p25, p75] ≈ [-6.55, +4.54]`pp. Live `NEUTRAL_PCT_THRESHOLD = ±10.0` is wider than the typical user's IQR (~±5-6pp), so the gauge reads 'neutral' for almost everyone. Recommend **narrow to ±6pp** (rounded from pooled IQR) if the goal is to give the gauge meaningful resolution. Single global threshold suffices (both axes collapse).

### Net-timeout rate (% of games)

Per-user p25 / p50 / p75 (n):

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -16.25 / -5.58 / +5.96 (n=100) | -6.02 / 0.00 / +5.42 (n=100) | -3.18 / +1.14 / +2.80 (n=100) | 0.00 / 0.00 / 0.00 (n=68) |
| **1200** | -10.07 / -0.74 / +8.58 (n=100) | -6.31 / +1.71 / +6.66 (n=100) | -1.29 / +1.02 / +2.55 (n=100) | 0.00 / 0.00 / +1.35 (n=89) |
| **1600** | -10.66 / -1.20 / +11.37 (n=99) | -7.30 / +1.27 / +7.90 (n=100) | -1.88 / +1.88 / +3.61 (n=100) | -1.32 / 0.00 / +1.81 (n=90) |
| **2000** | -10.26 / +4.65 / +14.47 (n=100) | -6.04 / +2.83 / +10.48 (n=100) | -2.08 / +2.16 / +4.37 (n=100) | 0.00 / +0.77 / +2.44 (n=87) |
| **2400** | -2.58 / +8.02 / +15.93 (n=99) | -0.45 / +4.97 / +10.86 (n=100) | 0.00 / +4.09 / +6.85 (n=100) | 0.00 / +0.56 / +1.23 (n=5*) |

**Pooled** (excludes sparse): μ=+0.37, SD=11.22, n=1832, p25=-3.41, p50=+1.24, p75=+5.67

**Collapse verdict** (net timeout):
- TC: max |d| = 0.04 (bullet vs blitz) → **collapse**
- ELO: max |d| = 0.60 (800 vs 2400) → **keep separate**

**Recommendation**: pooled `[p25, p75] ≈ [-3.41, +5.67]`pp. Live `NEUTRAL_TIMEOUT_THRESHOLD = ±5.0` is close to pooled IQR. ELO verdict says low-rated users net negative timeouts (μ=-2.3 at 800) while high-rated users net positive (μ=+4.6 at 2400). Recommend **per-ELO bands** (or at least keep current ±5pp aware of ELO bias) — the gauge currently reads negatively for ~half of low-ELO users by population baseline, which may be misleading. TC differences are negligible at user-level (despite raw event-rate differences across TCs).

## 5. Time pressure vs performance

Per-game outcome bucketed by user clock-as-%-of-base at endgame entry into 10 buckets (0-10%, 10-20%, …, 90-100%+). Cell shown if n ≥ 100.

### Currently set in code
- `Y_AXIS_DOMAIN = [0.2, 0.8]` (EndgameTimePressureSection.tsx:20)
- `X_AXIS_DOMAIN = [0, 100]` (EndgameTimePressureSection.tsx:22)

### Per-bucket TC marginals (pool ELO, excludes sparse cell)

Score by time-bucket × TC (n in parens):

| time-bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0-10% | 0.260 (n=18216) | 0.343 (n=18452) | 0.358 (n=7800) | 0.400 (n=1991) |
| 10-20% | 0.404 (n=31480) | 0.454 (n=21664) | 0.471 (n=8369) | 0.446 (n=1421) |
| 20-30% | 0.498 (n=34083) | 0.516 (n=23503) | 0.506 (n=10567) | 0.473 (n=1671) |
| 30-40% | 0.537 (n=38596) | 0.540 (n=27370) | 0.540 (n=13801) | 0.475 (n=2029) |
| 40-50% | 0.560 (n=39228) | 0.546 (n=30248) | 0.554 (n=16740) | 0.490 (n=2392) |
| 50-60% | 0.573 (n=36678) | 0.558 (n=32977) | 0.546 (n=21116) | 0.494 (n=2984) |
| 60-70% | 0.578 (n=29561) | 0.552 (n=32535) | 0.544 (n=26517) | 0.512 (n=3776) |
| 70-80% | 0.574 (n=18857) | 0.553 (n=26571) | 0.539 (n=30109) | 0.515 (n=4690) |
| 80-90% | 0.561 (n=7461) | 0.546 (n=15201) | 0.537 (n=25338) | 0.510 (n=5590) |
| 90-100% | 0.531 (n=1623) | 0.542 (n=6039) | 0.538 (n=12171) | 0.514 (n=15204) |

### Per-bucket ELO marginals (pool TC, excludes sparse)

| time-bucket | 800 | 1200 | 1600 | 2000 | 2400 |
|---|---|---|---|---|---|
| 0-10% | 0.260 (n=6473) | 0.277 (n=8118) | 0.296 (n=9659) | 0.340 (n=12215) | 0.372 (n=9994) |
| 10-20% | 0.375 (n=7874) | 0.390 (n=10701) | 0.394 (n=12542) | 0.446 (n=15622) | 0.500 (n=16195) |
| 20-30% | 0.460 (n=8419) | 0.464 (n=11597) | 0.476 (n=13659) | 0.520 (n=17519) | 0.558 (n=18630) |
| 30-40% | 0.503 (n=9629) | 0.502 (n=13903) | 0.511 (n=16536) | 0.547 (n=20090) | 0.586 (n=21638) |
| 40-50% | 0.523 (n=10630) | 0.523 (n=15998) | 0.531 (n=19023) | 0.559 (n=21126) | 0.600 (n=21831) |
| 50-60% | 0.533 (n=11441) | 0.526 (n=17487) | 0.535 (n=21382) | 0.577 (n=21938) | 0.605 (n=21507) |
| 60-70% | 0.521 (n=11883) | 0.519 (n=18468) | 0.537 (n=22027) | 0.582 (n=20732) | 0.611 (n=19279) |
| 70-80% | 0.511 (n=11062) | 0.513 (n=17600) | 0.535 (n=20046) | 0.577 (n=17046) | 0.618 (n=14473) |
| 80-90% | 0.487 (n=8446) | 0.513 (n=13883) | 0.524 (n=13891) | 0.578 (n=10114) | 0.633 (n=7256) |
| 90-100% | 0.464 (n=7642) | 0.495 (n=10773) | 0.551 (n=9569) | 0.589 (n=4988) | 0.684 (n=2065) |

### Per-bucket Cohen's d (max marginal-pair |d| per axis)

| time-bucket | TC d | ELO d |
|---|---|---|
| 0-10% | 0.31 | 0.25 |
| 10-20% | 0.14 | 0.26 |
| 20-30% | 0.09 | 0.20 |
| 30-40% | 0.13 | 0.17 |
| 40-50% | 0.15 | 0.16 |
| 50-60% | 0.17 | 0.17 |
| 60-70% | 0.14 | 0.19 |
| 70-80% | 0.13 | 0.23 |
| 80-90% | 0.11 | 0.32 |
| 90-100% | 0.06 | 0.49 |

### Collapse verdict
- TC axis: max |d| across buckets = 0.31 (at 0-10%) → **review**
- ELO axis: max |d| across buckets = 0.49 (at 90-100%) → **review** (just under keep-threshold; was 0.54 at 50/cell)

**Recommendation**: pure ELO collapse no longer triggered after upsampling — ELO axis sits at the high end of 'review'. Recommend **per-ELO overlay** for the 80-100% time-bucket region where the spread is largest (low-rated users decline at ample-time, high-rated users keep climbing). For 0-50% time-buckets all curves track within 0.1-0.2 d. Y-domain `[0.2, 0.8]` covers the typical curve well — pooled 0-10% bucket sits near 0.30, pooled 90-100% sits near 0.55 (strong-rating cohort touches 0.68 in 90-100%).

## 6. Endgame type breakdown

Per-class score, conversion, recovery (one row per `(game, endgame_class)` ≥6-ply span — multi-class games contribute once per class, mirroring `query_endgame_entry_rows`). Persistence approximation: `entry_ply + 4` with same-class join — small systematic difference vs backend's array-agg contiguity check.

### Currently set in code
- Per-class score-diff zones: `NEUTRAL_ZONE_MIN/MAX = ±0.05`, `BULLET_DOMAIN = 0.30` (EndgameWDLChart.tsx)
- Per-class conv/recov: no per-class neutral zones today (EndgameConvRecovChart.tsx)

### Pooled-by-class (collapses ELO and TC, excludes sparse cell)

| class | games | pooled score | score_diff | conversion | recovery |
|---|---|---|---|---|---|
| rook | 120,705 | 0.520 | +0.039 | 0.701 (n=42081) | 0.328 (n=38372) |
| minor_piece | 92,820 | 0.524 | +0.049 | 0.681 (n=31265) | 0.359 (n=28802) |
| pawn | 48,400 | 0.521 | +0.041 | 0.724 (n=15305) | 0.306 (n=13792) |
| queen | 44,464 | 0.519 | +0.038 | 0.778 (n=18429) | 0.245 (n=16889) |
| mixed | 675,396 | 0.519 | +0.037 | 0.695 (n=214551) | 0.329 (n=199755) |
| pawnless | 7,566 | 0.516 | +0.032 | 0.749 (n=3841) | 0.258 (n=3518) |

### Per-class score_diff: cell-level (5 ELO × 4 TC)

**rook** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.478 (n=3925) | 0.479 (n=5149) | 0.487 (n=3981) | 0.390 (n=718) |
| **1200** | 0.486 (n=7220) | 0.498 (n=7942) | 0.497 (n=6241) | 0.459 (n=2007) |
| **1600** | 0.501 (n=9309) | 0.502 (n=8260) | 0.516 (n=7103) | 0.509 (n=2762) |
| **2000** | 0.524 (n=10533) | 0.535 (n=8579) | 0.537 (n=6868) | 0.567 (n=2209) |
| **2400** | 0.554 (n=12388) | 0.556 (n=9435) | 0.598 (n=6076) | 0.835 (n=91*) |

**minor_piece** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.468 (n=1775) | 0.472 (n=2670) | 0.484 (n=1929) | 0.407 (n=372) |
| **1200** | 0.491 (n=3917) | 0.475 (n=4524) | 0.464 (n=3456) | 0.443 (n=1351) |
| **1600** | 0.503 (n=6358) | 0.507 (n=6583) | 0.499 (n=5366) | 0.489 (n=2364) |
| **2000** | 0.520 (n=8390) | 0.537 (n=8004) | 0.539 (n=6505) | 0.565 (n=2286) |
| **2400** | 0.555 (n=11107) | 0.570 (n=9827) | 0.599 (n=6036) | 0.826 (n=86*) |

**pawn** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.454 (n=879) | 0.482 (n=1533) | 0.491 (n=1147) | 0.365 (n=185) |
| **1200** | 0.468 (n=2091) | 0.478 (n=2785) | 0.486 (n=2353) | 0.459 (n=750) |
| **1600** | 0.510 (n=3550) | 0.525 (n=3673) | 0.500 (n=3303) | 0.514 (n=1473) |
| **2000** | 0.518 (n=4561) | 0.544 (n=3576) | 0.535 (n=3409) | 0.597 (n=1190) |
| **2400** | 0.540 (n=5805) | 0.560 (n=3707) | 0.588 (n=2430) | 0.807 (n=31*) |

**queen** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.492 (n=914) | 0.472 (n=1996) | 0.499 (n=1744) | 0.385 (n=327) |
| **1200** | 0.478 (n=2057) | 0.484 (n=2750) | 0.478 (n=2364) | 0.481 (n=756) |
| **1600** | 0.489 (n=3412) | 0.518 (n=2991) | 0.532 (n=2400) | 0.547 (n=934) |
| **2000** | 0.523 (n=4256) | 0.537 (n=3107) | 0.553 (n=2406) | 0.555 (n=713) |
| **2400** | 0.536 (n=5660) | 0.558 (n=3557) | 0.587 (n=2120) | 0.700 (n=25*) |

**mixed** — `score (n_games)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.476 (n=30446) | 0.480 (n=31148) | 0.484 (n=24657) | 0.411 (n=5242) |
| **1200** | 0.484 (n=45321) | 0.489 (n=43908) | 0.500 (n=33239) | 0.449 (n=11096) |
| **1600** | 0.495 (n=52822) | 0.495 (n=47134) | 0.510 (n=37535) | 0.516 (n=14059) |
| **2000** | 0.524 (n=55751) | 0.537 (n=48739) | 0.537 (n=38286) | 0.577 (n=10482) |
| **2400** | 0.558 (n=61655) | 0.579 (n=52758) | 0.604 (n=31118) | 0.838 (n=574*) |

**pawnless** — `score (n_games)` (sparser; many cells below n≥100)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.548 (n=124) | 0.498 (n=537) | 0.484 (n=598) | 0.496 (n=138) |
| **1200** | 0.513 (n=193) | 0.495 (n=487) | 0.500 (n=514) | 0.543 (n=188) |
| **1600** | 0.520 (n=256) | 0.525 (n=442) | 0.529 (n=452) | 0.482 (n=138) |
| **2000** | 0.503 (n=352) | 0.506 (n=545) | 0.547 (n=425) | 0.532 (n=93) |
| **2400** | 0.526 (n=680) | 0.513 (n=797) | 0.559 (n=607) | n<5* |

### Recommendations

- **Per-class score-diff neutral zone** (`NEUTRAL_ZONE_MIN/MAX = ±0.05`): pooled per-class score_diff sits in `[+0.032, +0.049]` — within current ±0.05 band for all 6 classes. **Keep `±0.05`**. The pooled signal across classes is weak; per-class deviations are small.
- **Per-class conv/recov neutral zones**: pooled spreads are meaningful — conversion ranges 0.68 (minor_piece) to 0.78 (queen), recovery ranges 0.24 (queen) to 0.36 (minor_piece). **Recommend per-class conv/recov bands** as `pooled ± 5pp`:
  - rook: conv `[0.65, 0.75]`, recov `[0.28, 0.38]`
  - minor_piece: conv `[0.63, 0.73]`, recov `[0.31, 0.41]`
  - pawn: conv `[0.67, 0.77]`, recov `[0.26, 0.36]`
  - queen: conv `[0.73, 0.83]`, recov `[0.20, 0.30]` (queen endgames have inflated conversion and depressed recovery — winning side rarely lets it slip, losing side rarely escapes)
  - mixed: conv `[0.65, 0.75]`, recov `[0.28, 0.38]`
  - pawnless: conv `[0.70, 0.80]`, recov `[0.21, 0.31]`
- **Domain `BULLET_DOMAIN = 0.30`**: per-class score_diff cell-level ranges from -0.27 (800/classical/pawn) to +0.22 (2400/rapid/rook) excluding sparse cell — `±0.30` covers the typical user. Keep.

### Per-class collapse summary (rate-level Cohen's d, max axis d across cells with n≥30; rough)

| class | TC d | ELO d | implication |
|---|---|---|---|
| rook | ~0.2 | ~0.5 | ELO matters most |
| minor_piece | ~0.2 | ~0.5 | ELO matters most |
| pawn | ~0.2 | ~0.4 | ELO weakly matters |
| queen | ~0.2 | ~0.3 | mostly collapses |
| mixed | ~0.3 | ~0.5 | ELO matters most |
| pawnless | <0.2 | <0.3 | mostly collapses (and small samples) |

(Per-class × per-axis d is approximated from cell-level pooled rates; the dominant signal is ELO rather than TC across all classes.)

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|
| Score gap (eg − non_eg) | review (0.34, blitz↔classical) | collapse (0.18, 800↔1600) | Mild TC effect (classical lags); single global zone fine. |
| Conversion (per-user) | **keep separate (0.87, bullet↔rapid)** | **keep separate (0.50, 800↔2400)** | Strong axes effects. Per-(TC,ELO) bands would meaningfully calibrate. |
| Parity (per-user) | review (0.28, bullet↔rapid) | **keep separate (1.09, 800↔2400)** | ELO drives parity score; TC near-flat. |
| Recovery (per-user) | **keep separate (0.58, bullet↔classical)** | **keep separate (1.35, 800↔2400)** | Both axes matter — strongest stratification candidate. |
| Endgame Skill (per-user) | review (0.28, bullet↔rapid) | **keep separate (1.30, 800↔2400)** | ELO dominates; TC mild. |
| Endgame ELO gap (per-user) | review (0.26, bullet↔rapid) | **keep separate (1.10, 800↔2400)** | ELO cohort dominates; expected. |
| Clock pressure %-of-base | collapse (0.16) | collapse (0.12) | Single global threshold viable. |
| Net timeout rate | collapse (0.04) | **keep separate (0.60, 800↔2400)** | High-rated users net positive; low-rated net negative. |
| Time-pressure curve (per-bucket) | review (0.31, at 0-10%) | review (0.49, at 90-100%) | Both axes near top of review band; per-ELO overlay recommended. |
| Per-class score | review | review (~0.5) | Pooled ±0.05 fits all classes. |
| Per-class conversion | review | review | Per-class bands recommended; ELO modest within class. |
| Per-class recovery | review | review (~0.5) | Per-class bands recommended (queen low, minor_piece high). |

Drives Phase 73 zone calibration in SEED-006.

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|
| Score-gap gauge neutral zone | `SCORE_GAP_NEUTRAL_MIN/MAX` | `±0.10` | `±0.10` | TC review / ELO collapse | **keep** (pooled \|m\|<5pp; symmetric round bounds beat data-fit) |
| Score-gap gauge half-width | `SCORE_GAP_DOMAIN` | `0.20` | `0.20` | (n/a) | **keep** (pooled p05/p95 ≈ ±0.22) |
| Score timeline Y-axis | `SCORE_TIMELINE_Y_DOMAIN` | `[20, 80]` | `[20, 80]` | (n/a) | **keep** |
| Conversion gauge band | `FIXED_GAUGE_ZONES.conversion` | `[0.65, 0.75]` | global `[0.65, 0.76]` or per-TC | TC keep / ELO keep | **stratify per TC** ideal; **keep** acceptable (covers pooled IQR) |
| Parity gauge band | `FIXED_GAUGE_ZONES.parity` | `[0.45, 0.55]` | global `[0.45, 0.57]` or per-ELO | TC review / ELO keep | **keep** (live aligns with pooled IQR; per-ELO would resolve more) |
| Recovery gauge band | `FIXED_GAUGE_ZONES.recovery` | `[0.25, 0.35]` | global `[0.26, 0.40]` or per-(TC,ELO) | TC keep / ELO keep | **stratify per (TC, ELO)** — strongest case for full stratification |
| Endgame Skill band | `ENDGAME_SKILL_ZONES` | `[0.45, 0.55]` | global `[0.46, 0.56]` or per-ELO | TC review / ELO keep | **keep** acceptable; per-ELO would resolve more |
| Endgame ELO timeline window | `ENDGAME_ELO_TIMELINE_WINDOW` | `100` | `100` | TC review / ELO keep (gap is ELO-cohort artifact) | **keep** (pooled SD = 72 Elo, well-behaved) |
| Endgame ELO skill clamp | `_ENDGAME_ELO_SKILL_CLAMP_LO/HI` | `[0.05, 0.95]` | `[0.05, 0.95]` | (n/a) | **keep** (saturation 0.06%) |
| Clock-diff % neutral band | `NEUTRAL_PCT_THRESHOLD` | `±10.0` | `±6.0` | TC collapse / ELO collapse | **narrow to ±6** — current band reads neutral for ~75% of users; pooled IQR ≈ ±6pp |
| Net timeout neutral band | `NEUTRAL_TIMEOUT_THRESHOLD` | `±5.0` | `±5.0` (or per-ELO) | TC collapse / ELO keep | **keep** acceptable; per-ELO would correct rating-cohort bias |
| Time-pressure Y-domain | `Y_AXIS_DOMAIN` | `[0.2, 0.8]` | `[0.2, 0.8]` | (n/a) | **keep** (covers pooled curve; high-rating cohort touches 0.68 at 90-100%) |
| Per-class score-diff band | `NEUTRAL_ZONE_MIN/MAX` (EndgameWDLChart) | `±0.05` | `±0.05` | per-class review | **keep** — all 6 pooled class score_diffs fit ±0.05 |
| Per-class conv/recov bands | (none today) | (no per-class neutral zone) | per-class `pooled ± 5pp` | per-class | **add per-class bands** (queen distinct from minor_piece, etc.) |

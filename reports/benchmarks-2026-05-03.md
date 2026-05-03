# FlawChess Benchmarks — 2026-05-03

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-03T15:00Z (selection_at MAX = 2026-04-30T21:58Z)
- **Population**: 2,415 users / 1,375,544 games / 95.0M positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; tc_bucket from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,523 candidate pool, 1,912 `(user, tc)` rows ingested as `status='completed'` (~100/cell except sparse)
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory)
- **Equal-footing filter (universal — all sections)**: `abs(opp_rating - user_rating) <= 100`. Applied to every per-game CTE in §1, §2, §4, §5, §6 to remove the matchmaking confound. Higher-rated cohorts otherwise play systematically weaker opponents (per-cell `avg_opp_minus_user` ranged from +47 in 800-classical down to -372 in 2400-classical in the unfiltered data), inflating the apparent ELO ramp on every per-game metric. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. **Scope changed from §2/§6-only to universal on 2026-05-03**; pre-2026-05-03 §1/§4/§5 numbers in older reports are not directly comparable. Rationale: `.planning/notes/benchmark-equal-footing-framing.md`.
- **Conv/Parity/Recovery bucketing (REFAC-02)**: Stockfish eval at the first endgame ply (or first ply of each class span in §6). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity). The old `material_imbalance + 4-ply persistence` proxy is gone — sections 2/6 read `eval_cp` / `eval_mate` directly.
- **Eval coverage**: **99.99%** of qualifying endgame entries have non-NULL eval (767,343 of 767,398). Stockfish backfill is effectively complete.
- **Sparse-cell exclusion**: `(2400, classical)` excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user, 14.6% equal-footing retention → ~184 games total). Still shown in cell-level 5×4 tables with `*`. Some §1/§2/§4 cells in 800/1200-classical also reduced after equal-footing filtering — flagged inline.
- **Verdict thresholds**: Cohen's d < 0.2 = collapse / 0.2-0.5 = review / ≥ 0.5 = keep separate
- **Sample floors**: §1 ≥30 endgame AND ≥30 non-endgame games/user; §2 ≥20 endgame games/user, ≥2 of 3 buckets; §4 ≥20 endgame games/user; §5 per-bucket cell ≥100 games; §6 ≥100 score / ≥30 conv / ≥30 recov per cell. All Cohen's d marginals require ≥10 users per level.

### Cell coverage (status='completed' users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 100 | 100 | 100 | 100 |
| **1200** | 100 | 100 | 100 | 100 |
| **1600** | 100 | 100 | 100 | 100 |
| **2000** | 100 | 100 | 100 | 100 |
| **2400** | 100 | 100 | 100 | 12* |

*sparse cell, see exclusion note above*

### Equal-footing retention (% of cell games kept after `|opp − user| ≤ 100`)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 83.1% | 84.6% | 81.5% | 53.2% |
| **1200** | 89.5% | 89.4% | 87.8% | 72.2% |
| **1600** | 85.6% | 88.8% | 87.9% | 70.9% |
| **2000** | 78.3% | 78.4% | 73.8% | 57.1% |
| **2400** | 66.5% | 61.9% | 51.3% | 14.6%* |

Mid-ELO bullet/blitz/rapid retain 78–90%. 2400 cohorts drop to ~51–67% (high-rated players play more uneven matches at lower-population pools). Classical drops further across all ELOs because classical games are scarcer per user. 2400-classical drops to 14.6% — already excluded as sparse. **No non-sparse cell drops below per-user sample floors**, so the escape-hatch (re-select at higher per-cell N) is not needed for this snapshot.

---

## 1. Score gap (endgame vs non-endgame)

Per-user metric: `eg_score − non_eg_score`. Sample floor: ≥30 endgame games AND ≥30 non-endgame games per user, in their selected TC.

### Currently set in code

- `SCORE_GAP_NEUTRAL_MIN/MAX = ±0.10` (frontend/src/generated/endgameZones.ts:38-39)
- `SCORE_GAP_DOMAIN = 0.20` (EndgamePerformanceSection.tsx:44)
- `SCORE_TIMELINE_Y_DOMAIN = [20, 80]` (EndgamePerformanceSection.tsx:50)

### Cell table — per-user `diff_p25 / diff_p50 / diff_p75 (n)`

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -0.089 / -0.036 / +0.038 (n=97) | -0.110 / -0.024 / +0.052 (n=97) | -0.128 / -0.023 / +0.105 (n=94) | -0.249 / -0.134 / -0.033 (n=24) |
| **1200** | -0.105 / -0.040 / +0.035 (n=97) | -0.104 / -0.032 / +0.076 (n=99) | -0.120 / +0.008 / +0.080 (n=98) | -0.148 / -0.054 / +0.060 (n=51) |
| **1600** | -0.085 / -0.017 / +0.061 (n=97) | -0.078 / -0.001 / +0.101 (n=99) | -0.077 / +0.007 / +0.098 (n=100) | -0.154 / -0.048 / +0.101 (n=66) |
| **2000** | -0.097 / -0.014 / +0.059 (n=100) | -0.083 / +0.005 / +0.072 (n=98) | -0.084 / +0.008 / +0.072 (n=95) | -0.114 / -0.019 / +0.046 (n=49) |
| **2400** | -0.092 / +0.023 / +0.113 (n=98) | -0.082 / -0.002 / +0.053 (n=96) | -0.066 / -0.009 / +0.071 (n=77) | n=1* |

*sparse cell, n_users < floor after equal-footing filter*

### TC marginal (excludes sparse)

| TC | n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 489 | -0.010 | -0.182 | -0.095 | -0.018 | +0.064 | +0.198 |
| blitz | 489 | -0.007 | -0.191 | -0.093 | -0.009 | +0.069 | +0.195 |
| rapid | 464 | -0.007 | -0.232 | -0.095 | -0.006 | +0.082 | +0.203 |
| classical | 190 | -0.053 | -0.337 | -0.151 | -0.046 | +0.065 | +0.199 |

### ELO marginal (excludes sparse)

| ELO | n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| 800 | 312 | -0.025 | -0.242 | -0.116 | -0.036 | +0.053 | +0.219 |
| 1200 | 345 | -0.021 | -0.237 | -0.112 | -0.031 | +0.072 | +0.212 |
| 1600 | 362 | -0.007 | -0.231 | -0.103 | -0.009 | +0.094 | +0.210 |
| 2000 | 342 | -0.010 | -0.206 | -0.088 | -0.004 | +0.068 | +0.164 |
| 2400 | 271 | -0.004 | -0.197 | -0.082 | +0.001 | +0.074 | +0.167 |

### Pooled overall (excludes sparse)

| n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|
| 1,632 | -0.013 | -0.227 | -0.103 | -0.014 | +0.073 | +0.202 |

### Recommendations

- **Score-gap neutral zone**: pooled `[-0.103, +0.073]`. Live `±0.10` is approximately right; pooled p25/p75 is mildly asymmetric (-0.103/+0.073) but |median| = 0.014 is well below the 5pp guard, so **keep symmetric ±0.10**.
- **Score-gap domain (gauge half-width)**: pooled `max(|p05|, |p95|) = max(0.227, 0.202) = 0.227`. Live `0.20` clips ~5% of users at extremes. Consider widening to **0.25** if more headroom is needed; otherwise keep.
- **Timeline neutral zone**: pooled eg `[0.464, 0.555]`, non_eg `[0.468, 0.574]`. Overlap is `[0.468, 0.555]` (87% of narrower interval). Single unified band **`[0.47, 0.55]`** is reasonable.
- **Timeline Y-axis**: pooled `[min(eg_p05, non_eg_p05), max(eg_p95, non_eg_p95)] = [0.389, 0.673]`. Live `[0.20, 0.80]` is generous; could narrow to `[0.35, 0.70]` for more visual contrast, but the wider domain keeps users with extreme baselines on-chart.

### Collapse verdict

- TC axis: max |d| = 0.34 (blitz vs classical) → **review** (classical eg-deficit larger than other TCs)
- ELO axis: max |d| = 0.17 (800 vs 2400) → **collapse** (per-user diff is stable across rating cohorts at equal-footing)

#### Per-user `diff_p50` heatmap (5×4)

|  | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -0.036 | -0.024 | -0.023 | -0.134 |
| **1200** | -0.040 | -0.032 | +0.008 | -0.054 |
| **1600** | -0.017 | -0.001 | +0.007 | -0.048 |
| **2000** | -0.014 | +0.005 | +0.008 | -0.019 |
| **2400** | +0.023 | -0.002 | -0.009 | * |

Classical column is consistently the most negative — confirms the TC-axis review verdict. The interaction is "classical players score worse in endgames vs non-endgames" rather than a uniform shift, so a single global gauge is OK but the gauge will sit slightly skewed for classical-heavy users.

---

## 2. Conversion / Parity / Recovery + Endgame Skill

Per-user metrics computed via Stockfish-eval bucketing at first endgame ply (REFAC-02).

### Population bucket prevalence (sanity reference)

Per-game (not per-user) bucket counts across the benchmark DB endgame-entry games (selected users, `status='completed'`, sparse `(2400, classical)` cell excluded). Useful as a sanity check for bucketing changes — if a refactor of the eval rule moves these numbers more than ~1pp it warrants investigation.

Cell = `n (%) [avg user_eval_cp]`. The eval is `sign * eval_cp` (user-perspective), averaged across games where `eval_cp IS NOT NULL` (mate scores excluded from the average).

| Filter | n_games | conversion | parity | recovery | overall avg eval |
|---|---:|---:|---:|---:|---:|
| Base only (`rated AND NOT is_computer_game`) | 708,032 | 274,391 (38.75%) [+430 cp] | 177,987 (25.14%) [+1 cp] | 255,654 (36.11%) [−429 cp] | +12 cp |
| Base + equal-footing (`abs(opp_rating − user_rating) ≤ 100`) | 554,608 | 211,443 (38.12%) [+430 cp] | 137,133 (24.73%) [+1 cp] | 206,032 (37.15%) [−430 cp] | +4 cp |

The equal-footing filter retains ~78% of games and shrinks the conversion–recovery gap from +2.7pp to +1.0pp, consistent with higher-rated cohorts padding their conversion rate via softer matchmaking. The overall user-perspective eval also shrinks from +12 cp to +4 cp, confirming the same matchmaking confound at the eval level. Per-bucket eval magnitudes (~±430 cp) are nearly identical across filter regimes — the equal-footing filter changes which games qualify, not the within-bucket eval distribution. Buckets are roughly balanced (≈38 / 25 / 37), so eval-coverage regressions to NULL would noticeably swell the parity bucket.

### Currently set in code

- `FIXED_GAUGE_ZONES.conversion` neutral = `[0.65, 0.75]` (frontend/src/generated/endgameZones.ts:14-15)
- `FIXED_GAUGE_ZONES.parity` neutral = `[0.45, 0.55]` (line 19-20)
- `FIXED_GAUGE_ZONES.recovery` neutral = `[0.25, 0.40]` (line 24-25)
- `ENDGAME_SKILL_ZONES` neutral = `[0.45, 0.55]` (line 31-32)
- `NEUTRAL_ZONE_MIN/MAX = ±0.05`, `BULLET_DOMAIN = 0.20` (EndgameScoreGapSection.tsx:42-48)

### 2a. Conversion (Win % when up ≥100 cp at endgame entry)

#### Cell table — per-user p50 (n_users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.597 (99) | 0.701 (100) | 0.714 (96) | 0.714 (41) |
| **1200** | 0.624 (100) | 0.709 (99) | 0.734 (100) | 0.750 (72) |
| **1600** | 0.659 (100) | 0.712 (100) | 0.747 (100) | 0.776 (85) |
| **2000** | 0.672 (100) | 0.726 (100) | 0.749 (98) | 0.774 (66) |
| **2400** | 0.713 (100) | 0.744 (100) | 0.778 (95) | 0.794 (n=2*) |

#### TC marginal (excludes sparse)

| TC | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| bullet | 499 | 0.651 | 0.583 | 0.658 | 0.720 |
| blitz | 499 | 0.716 | 0.674 | 0.718 | 0.761 |
| rapid | 489 | 0.743 | 0.697 | 0.745 | 0.787 |
| classical | 264 | 0.756 | 0.698 | 0.761 | 0.830 |

#### ELO marginal (excludes sparse)

| ELO | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| 800 | 336 | 0.668 | 0.599 | 0.682 | 0.739 |
| 1200 | 371 | 0.703 | 0.647 | 0.709 | 0.760 |
| 1600 | 385 | 0.717 | 0.667 | 0.721 | 0.776 |
| 2000 | 364 | 0.721 | 0.669 | 0.725 | 0.775 |
| 2400 | 295 | 0.749 | 0.699 | 0.743 | 0.799 |

#### Pooled overall

| n | mean | p25 | p50 | p75 |
|---|---|---|---|---|
| 1,751 | 0.711 | 0.656 | 0.719 | 0.769 |

#### Recommendations

- Pooled neutral `[p25, p75] = [0.656, 0.769]`. Live `[0.65, 0.75]` is slightly under-shifted but close. **Pooled bands won't fit each cell**: bullet p50=0.658 sits below the band; classical p50=0.761 sits at the top.
- TC verdict says `keep separate` — **propose per-TC bands**:
  - bullet `[0.58, 0.72]`
  - blitz `[0.67, 0.76]`
  - rapid `[0.70, 0.79]`
  - classical `[0.70, 0.83]`

#### Collapse verdict

- TC axis: max |d| = 1.02 (bullet vs classical) → **keep separate**
- ELO axis: max |d| = 0.82 (800 vs 2400) → **keep separate**

### 2b. Parity (Score % when within ±100 cp at endgame entry)

#### Cell table — per-user p50 (n_users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.500 (97) | 0.479 (100) | 0.500 (96) | 0.385 (39) |
| **1200** | 0.490 (100) | 0.489 (99) | 0.487 (100) | 0.500 (72) |
| **1600** | 0.515 (100) | 0.500 (100) | 0.500 (100) | 0.500 (85) |
| **2000** | 0.499 (100) | 0.515 (100) | 0.519 (98) | 0.521 (66) |
| **2400** | 0.522 (100) | 0.552 (100) | 0.540 (95) | 0.712 (n=2*) |

#### TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| bullet | 499 | 0.504 | 0.444 | 0.500 | 0.564 |
| blitz | 499 | 0.502 | 0.447 | 0.507 | 0.561 |
| rapid | 489 | 0.508 | 0.456 | 0.506 | 0.558 |
| classical | 264 | 0.491 | 0.395 | 0.500 | 0.583 |

#### ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| 800 | 336 | 0.470 | 0.383 | 0.500 | 0.551 |
| 1200 | 371 | 0.499 | 0.433 | 0.489 | 0.550 |
| 1600 | 385 | 0.497 | 0.440 | 0.500 | 0.554 |
| 2000 | 364 | 0.514 | 0.461 | 0.512 | 0.564 |
| 2400 | 295 | 0.537 | 0.486 | 0.539 | 0.581 |

#### Pooled overall

| n | mean | p25 | p50 | p75 |
|---|---|---|---|---|
| 1,751 | 0.502 | 0.443 | 0.500 | 0.563 |

#### Recommendations

- Pooled neutral `[0.443, 0.563]`. Live `[0.45, 0.55]` is approximately correct. **Keep `[0.45, 0.55]`** (or slightly widen to `[0.44, 0.56]` to cover the IQR more fully).

#### Collapse verdict

- TC axis: max |d| = 0.12 → **collapse**
- ELO axis: max |d| = 0.48 (800 vs 2400) → **review** (single zone OK; expect 800 cohort skewed low and 2400 skewed high in observed data)

### 2c. Recovery (Save % when down ≥100 cp at endgame entry)

#### Cell table — per-user p50 (n_users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.354 (99) | 0.290 (100) | 0.258 (96) | 0.203 (41) |
| **1200** | 0.365 (100) | 0.290 (99) | 0.286 (99) | 0.226 (72) |
| **1600** | 0.340 (100) | 0.287 (100) | 0.269 (100) | 0.222 (85) |
| **2000** | 0.345 (100) | 0.330 (100) | 0.264 (98) | 0.272 (66) |
| **2400** | 0.347 (100) | 0.317 (100) | 0.300 (95) | 0.250 (n=2*) |

#### TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| bullet | 499 | 0.355 | 0.302 | 0.353 | 0.405 |
| blitz | 499 | 0.302 | 0.251 | 0.304 | 0.355 |
| rapid | 489 | 0.286 | 0.233 | 0.277 | 0.328 |
| classical | 264 | 0.250 | 0.182 | 0.233 | 0.316 |

#### ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| 800 | 336 | 0.297 | 0.234 | 0.297 | 0.356 |
| 1200 | 371 | 0.300 | 0.238 | 0.295 | 0.358 |
| 1600 | 385 | 0.293 | 0.231 | 0.287 | 0.353 |
| 2000 | 364 | 0.311 | 0.250 | 0.305 | 0.373 |
| 2400 | 295 | 0.330 | 0.275 | 0.323 | 0.380 |

#### Pooled overall

| n | mean | p25 | p50 | p75 |
|---|---|---|---|---|
| 1,751 | 0.305 | 0.243 | 0.301 | 0.364 |

#### Recommendations

- Pooled neutral `[0.243, 0.364]`. Live `[0.25, 0.40]` upper bound is slightly high; pooled p75 is 0.364. **Live band is approximately right**; consider tightening upper bound to `0.36`, but the difference is cosmetic.
- TC verdict says `keep separate` — **propose per-TC bands**:
  - bullet `[0.30, 0.40]`
  - blitz `[0.25, 0.36]`
  - rapid `[0.23, 0.33]`
  - classical `[0.18, 0.32]`

#### Collapse verdict

- TC axis: max |d| = 1.10 (bullet vs classical) → **keep separate**
- ELO axis: max |d| = 0.40 (1600 vs 2400) → **review**

### 2d. Endgame Skill (mean of conv/par/recov rates)

#### Cell table — per-user p50 (n_users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.481 (99) | 0.497 (100) | 0.493 (96) | 0.438 (41) |
| **1200** | 0.492 (100) | 0.496 (99) | 0.508 (100) | 0.496 (72) |
| **1600** | 0.509 (100) | 0.502 (100) | 0.507 (100) | 0.516 (85) |
| **2000** | 0.506 (100) | 0.521 (100) | 0.512 (98) | 0.523 (66) |
| **2400** | 0.528 (100) | 0.543 (100) | 0.544 (95) | 0.585 (n=2*) |

#### TC marginal

| TC | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| bullet | 499 | 0.504 | 0.459 | 0.506 | 0.553 |
| blitz | 499 | 0.507 | 0.470 | 0.509 | 0.548 |
| rapid | 489 | 0.513 | 0.479 | 0.512 | 0.546 |
| classical | 264 | 0.499 | 0.445 | 0.499 | 0.549 |

#### ELO marginal

| ELO | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| 800 | 336 | 0.478 | 0.428 | 0.488 | 0.528 |
| 1200 | 371 | 0.501 | 0.458 | 0.497 | 0.537 |
| 1600 | 385 | 0.502 | 0.466 | 0.507 | 0.544 |
| 2000 | 364 | 0.515 | 0.480 | 0.514 | 0.551 |
| 2400 | 295 | 0.539 | 0.499 | 0.539 | 0.575 |

#### Pooled overall

| n | mean | p25 | p50 | p75 |
|---|---|---|---|---|
| 1,751 | 0.506 | 0.466 | 0.508 | 0.548 |

#### Recommendations

- Pooled neutral `[0.466, 0.548]`. Live `[0.45, 0.55]` is essentially right. **Keep `[0.45, 0.55]`**.
- TC collapse verdict supports a single global band. ELO `keep` verdict means a 800-rated user will sit lower in the band on average and a 2400-rated user higher. That is the "skill at equal footing" signal — the gauge correctly shows that endgame skill ramps with rating cohort.

#### Collapse verdict

- TC axis: max |d| = 0.18 → **collapse**
- ELO axis: max |d| = 0.78 (800 vs 2400) → **keep separate** (rating-cohort effect is real, but a single band is fine since the ramp is the intended skill signal)

---

## 4. Time pressure at endgame entry

Per-user metrics: `clock_diff_pct` (% of base time) and `net_timeout_pct` (timeout-wins minus timeout-losses, % of cell games). SQL approximates the backend's first-non-NULL-clock walk by reading clocks at `entry_ply` and `entry_ply + 1` — small bias vs backend.

### Currently set in code

- `NEUTRAL_PCT_THRESHOLD = 5.0` (% diff neutral zone is ±5%)
- `NEUTRAL_TIMEOUT_THRESHOLD = 5.0` (net timeout neutral zone is ±5pp)
- (frontend/src/generated/endgameZones.ts:36-37, EndgameClockPressureSection.tsx)

### 4a. Clock diff % (user_pct − opp_pct, % of base time)

#### Cell table — per-user p50 (n_users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -0.70 (98) | -0.76 (100) | +1.24 (96) | +0.18 (38) |
| **1200** | -0.43 (100) | -0.48 (99) | -0.09 (100) | +1.17 (72) |
| **1600** | -0.20 (99) | -1.70 (100) | -0.12 (100) | -0.20 (85) |
| **2000** | -1.53 (100) | -1.48 (100) | -1.27 (98) | -5.69 (64) |
| **2400** | +0.12 (99) | -0.04 (100) | -3.29 (95) | +4.30 (n=2*) |

#### TC marginal (excludes sparse)

| TC | n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 496 | -0.22 | -9.0 | -3.84 | -0.43 | +2.82 | +9.2 |
| blitz | 499 | -1.40 | -17.6 | -7.09 | -0.77 | +4.70 | +11.9 |
| rapid | 489 | -1.48 | -18.2 | -8.22 | -0.25 | +5.27 | +12.8 |
| classical | 259 | -2.71 | -31.8 | -12.26 | -0.70 | +8.01 | +19.2 |

#### ELO marginal (excludes sparse)

| ELO | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| 800 | 332 | -1.07 | -6.04 | -0.29 | +4.87 |
| 1200 | 371 | -1.17 | -6.07 | -0.23 | +5.11 |
| 1600 | 384 | -1.43 | -6.78 | -0.40 | +5.12 |
| 2000 | 362 | -2.23 | -8.13 | -1.84 | +3.22 |
| 2400 | 294 | -0.29 | -4.84 | -0.21 | +4.44 |

#### Pooled overall

| n | mean | p25 | p50 | p75 |
|---|---|---|---|---|
| 1,743 | -1.28 | -6.41 | -0.52 | +4.66 |

#### Recommendations

- Pooled neutral `[p25, p75] = [-6.4, +4.7]`. Live `±5.0%` is approximately the right shape but slightly asymmetric in the data (population centers at -1.28%). Asymmetry is < 5pp, so **keep symmetric ±5%** — at population scale most users sit inside ±5%.
- IQRs differ by TC (bullet ~±3.8, classical ~±12). The larger classical IQR reflects the much higher per-game variance (classical games run far longer than the base time `g.base_time_seconds` by the time they reach endgame, so the % computation gets noisy). If users complain that classical-cell readings feel bouncy, consider per-TC zones (bullet ±4, blitz ±7, rapid ±8, classical ±12).

#### Collapse verdict

- TC axis: max |d| = 0.23 (bullet vs classical) → **review**
- ELO axis: max |d| = 0.21 (2000 vs 2400) → **review**

### 4b. Net timeout rate (timeout_wins − timeout_losses) / games × 100

#### Cell table — per-user p50 (n_users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -5.25 (98) | -0.29 (100) | +1.32 (96) | 0.00 (38) |
| **1200** | -0.56 (100) | +2.03 (99) | +1.16 (100) | 0.00 (72) |
| **1600** | +1.98 (99) | +1.13 (100) | +2.01 (100) | 0.00 (85) |
| **2000** | +2.19 (100) | +2.25 (100) | +1.97 (98) | +0.58 (64) |
| **2400** | +5.53 (99) | +1.95 (100) | +2.42 (95) | 0.00 (n=2*) |

#### TC marginal (excludes sparse)

| TC | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| bullet | 496 | +0.37 | -11.36 | +1.87 | +11.50 |
| blitz | 499 | -0.01 | -5.93 | +1.19 | +7.74 |
| rapid | 489 | +0.16 | -1.74 | +1.64 | +3.85 |
| classical | 259 | -0.33 | 0.00 | 0.00 | +1.70 |

#### ELO marginal (excludes sparse)

| ELO | n | mean | p25 | p50 | p75 |
|---|---|---|---|---|---|
| 800 | 332 | -2.01 | -7.31 | 0.00 | +4.06 |
| 1200 | 371 | -0.34 | -4.18 | +0.62 | +4.34 |
| 1600 | 384 | -0.17 | -3.26 | +1.18 | +5.14 |
| 2000 | 362 | +0.61 | -4.77 | +1.50 | +6.39 |
| 2400 | 294 | +2.77 | -2.75 | +3.05 | +9.45 |

#### Pooled overall

| n | mean | p25 | p50 | p75 |
|---|---|---|---|---|
| 1,743 | +0.10 | -4.43 | +1.04 | +5.63 |

#### Recommendations

- Pooled neutral `[-4.4, +5.6]`. Live `±5.0pp` is roughly right; the median is +1.04 (more flag-wins than flag-losses across the board). **Keep ±5pp** (asymmetry is small).
- IQRs differ wildly by TC (bullet ±11, classical ±1.7) — a bullet user's "neutral" range is much wider than a classical user's. Consider per-TC zones if user complaints arise (bullet ±10pp, blitz ±7pp, rapid ±3pp, classical ±2pp). Cohen's d says TC is fine to collapse, but the per-TC IQR is a different signal.

#### Collapse verdict

- TC axis: max |d| = 0.07 → **collapse**
- ELO axis: max |d| = 0.41 (800 vs 2400) → **review** (high-rated cohort wins more on time)

---

## 5. Time pressure vs performance

Per-game outcome (0 / 0.5 / 1) bucketed by % of base time remaining at endgame entry. 10 buckets (0–9 = 0–10%, 10–20%, …, 90–100%+). Per-bucket cell shown if n ≥ 100.

### Currently set in code

- `Y_AXIS_DOMAIN = [0.2, 0.8]`, `X_AXIS_DOMAIN = [0, 100]` (EndgameTimePressureSection.tsx:20-22)
- `MIN_GAMES_FOR_CLOCK_STATS = 10` (app/services/endgame_service.py:853)

### TC marginals (score per time bucket, pool ELO)

| bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **0** (0–10%) | 0.260 (15275) | 0.334 (14823) | 0.338 (5686) | 0.410 (1391) |
| **1** (10–20%) | 0.399 (25401) | 0.437 (16660) | 0.441 (5987) | 0.452 (945) |
| **2** (20–30%) | 0.491 (27230) | 0.492 (17700) | 0.469 (7563) | 0.468 (1125) |
| **3** | 0.530 (30735) | 0.518 (21039) | 0.508 (9892) | 0.475 (1325) |
| **4** | 0.552 (31404) | 0.534 (24283) | 0.532 (12704) | 0.478 (1596) |
| **5** | 0.564 (29148) | 0.548 (26875) | 0.533 (16604) | 0.486 (2002) |
| **6** | 0.563 (23294) | 0.544 (26851) | 0.529 (21177) | 0.505 (2556) |
| **7** | 0.553 (14683) | 0.542 (21931) | 0.523 (24233) | 0.510 (3173) |
| **8** | 0.542 (5843) | 0.534 (12420) | 0.524 (20363) | 0.502 (3750) |
| **9** (90–100%+) | 0.500 (1235) | 0.523 (4776) | 0.524 (9602) | 0.510 (9857) |

### ELO marginals (score per time bucket, pool TC)

| bucket | 800 | 1200 | 1600 | 2000 | 2400 |
|---|---|---|---|---|---|
| **0** | 0.266 | 0.283 | 0.304 | 0.332 | 0.336 |
| **1** | 0.381 | 0.400 | 0.401 | 0.433 | 0.461 |
| **2** | 0.469 | 0.473 | 0.484 | 0.494 | 0.511 |
| **3** | 0.511 | 0.512 | 0.516 | 0.525 | 0.538 |
| **4** | 0.531 | 0.530 | 0.535 | 0.542 | 0.563 |
| **5** | 0.538 | 0.532 | 0.537 | 0.563 | 0.575 |
| **6** | 0.526 | 0.527 | 0.537 | 0.559 | 0.575 |
| **7** | 0.515 | 0.518 | 0.532 | 0.552 | 0.571 |
| **8** | 0.497 | 0.518 | 0.524 | 0.553 | 0.571 |
| **9** | 0.490 | 0.501 | 0.537 | 0.547 | 0.564 |

### Recommendations

- `Y_AXIS_DOMAIN = [0.2, 0.8]`: pooled scores range 0.26–0.57. Live domain has plenty of headroom, **keep**.
- TC verdict says `review` (driven mostly by bucket 0: bullet=0.26 vs classical=0.41 — bullet players are dramatically worse under severe time pressure, classical players much steadier). The shape of the curve is recognizable in all TCs (rising from 0% to ~50% time, plateauing thereafter), but the bullet curve is steeper at the low-time end. **Consider stratifying display per-TC** — show per-TC overlay or per-TC selector. Live UI presents pooled-by-TC already (TC selector), so this is already correctly handled.
- ELO verdict says `collapse` — single curve fine across rating cohorts at equal footing.

### Collapse verdict

- TC axis: max |d| = 0.34 (bucket 0, bullet vs classical) → **review** (bucket 0 is the meaningful divergence; buckets 2+ converge)
- ELO axis: max |d| = 0.17 (across buckets 0/1/8/9, 800 vs 2400) → **collapse**

---

## 6. Endgame type breakdown

Per-(game, endgame_class) span ≥6 plies. Eval-bucket determined at first ply of each class span (REFAC-02).

### Currently set in code

- `NEUTRAL_ZONE_MIN/MAX = ±0.05`, `BULLET_DOMAIN = 0.30` (EndgameWDLChart.tsx:42-48)
- `PER_CLASS_GAUGE_ZONES` per-class conv/recov bands (frontend/src/generated/endgameZones.ts:46-53), seeded from 2026-05-01 report

### Pooled-by-class summary (excludes sparse cell)

| Class | games | score | score_diff | conv (n) | recov (n) | par_score |
|---|---|---|---|---|---|---|
| rook | 94,087 | 0.508 | +0.015 | 0.710 (32,579) | 0.296 (30,814) | 0.503 |
| minor_piece | 70,381 | 0.510 | +0.020 | 0.695 (23,981) | 0.328 (23,239) | 0.501 |
| pawn | 37,463 | 0.511 | +0.021 | 0.738 (14,630) | 0.275 (13,913) | 0.504 |
| queen | 34,432 | 0.508 | +0.016 | 0.774 (14,419) | 0.234 (13,790) | 0.495 |
| mixed | 529,608 | 0.506 | +0.011 | 0.694 (204,341) | 0.311 (199,157) | 0.506 |
| pawnless | 5,847 | 0.507 | +0.014 | 0.791 (2,515) | 0.198 (2,363) | 0.496 |

### 6a. Score (per-class, per-cell)

#### Rook

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.485 (3334) | 0.489 (4410) | 0.489 (3305) | 0.423 (400) |
| **1200** | 0.489 (6462) | 0.501 (7077) | 0.500 (5542) | 0.483 (1431) |
| **1600** | 0.503 (7953) | 0.506 (7336) | 0.519 (6235) | 0.502 (2066) |
| **2000** | 0.502 (7977) | 0.521 (6664) | 0.530 (5209) | 0.515 (1320) |
| **2400** | 0.528 (8169) | 0.517 (6015) | 0.535 (3182) | 0.868 (n=19*) |

#### Minor piece

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.467 (1474) | 0.476 (2292) | 0.494 (1602) | 0.483 (173) |
| **1200** | 0.494 (3533) | 0.481 (4021) | 0.466 (3020) | 0.482 (935) |
| **1600** | 0.514 (5402) | 0.515 (5899) | 0.499 (4735) | 0.494 (1745) |
| **2000** | 0.502 (6383) | 0.523 (6184) | 0.518 (4776) | 0.532 (1367) |
| **2400** | 0.531 (7393) | 0.534 (6209) | 0.552 (3238) | n=15* |

#### Pawn

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.455 (750) | 0.479 (1344) | 0.499 (952) | 0.335 (88) |
| **1200** | 0.474 (1902) | 0.480 (2489) | 0.490 (2065) | 0.473 (522) |
| **1600** | 0.520 (3003) | 0.538 (3297) | 0.508 (2914) | 0.526 (1089) |
| **2000** | 0.500 (3452) | 0.528 (2783) | 0.521 (2537) | 0.558 (686) |
| **2400** | 0.525 (3925) | 0.527 (2353) | 0.528 (1312) | n=3* |

#### Queen

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.486 (781) | 0.477 (1734) | 0.501 (1453) | 0.389 (167) |
| **1200** | 0.475 (1851) | 0.491 (2405) | 0.478 (2075) | 0.489 (537) |
| **1600** | 0.490 (2898) | 0.529 (2664) | 0.537 (2100) | 0.551 (709) |
| **2000** | 0.515 (3250) | 0.517 (2432) | 0.533 (1774) | 0.525 (440) |
| **2400** | 0.516 (3810) | 0.522 (2234) | 0.526 (1118) | n=0* |

#### Mixed

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.482 (25.8k) | 0.486 (26.6k) | 0.492 (20.5k) | 0.444 (2778) |
| **1200** | 0.489 (40.7k) | 0.495 (39.2k) | 0.502 (29.5k) | 0.471 (7803) |
| **1600** | 0.497 (45.2k) | 0.501 (42.0k) | 0.511 (33.1k) | 0.506 (10.2k) |
| **2000** | 0.506 (43.2k) | 0.520 (38.1k) | 0.518 (28.5k) | 0.530 (6200) |
| **2400** | 0.527 (40.9k) | 0.534 (33.0k) | 0.538 (16.5k) | 0.731 (n=93*) |

#### Pawnless

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.564 (110*) | 0.497 (475) | 0.480 (493) | 0.506 (80*) |
| **1200** | 0.520 (173*) | 0.502 (436) | 0.510 (459) | 0.577 (143) |
| **1600** | 0.502 (215) | 0.522 (384) | 0.514 (403) | 0.431 (101) |
| **2000** | 0.517 (239) | 0.493 (411) | 0.528 (324) | 0.536 (55*) |
| **2400** | 0.491 (463) | 0.496 (516) | 0.530 (367) | n=0* |

(*n < 100 score floor*)

### 6b. Conversion (per-class, per-cell)

#### Rook

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.614 (1325) | 0.690 (1657) | 0.701 (1313) | 0.620 (142) |
| **1200** | 0.625 (2288) | 0.723 (2574) | 0.779 (1979) | 0.782 (519) |
| **1600** | 0.646 (2850) | 0.728 (2729) | 0.781 (2144) | 0.801 (663) |
| **2000** | 0.637 (2876) | 0.732 (2107) | 0.773 (1676) | 0.820 (355) |
| **2400** | 0.705 (2823) | 0.741 (1669) | 0.792 (890) | 1.000 (n=7*) |

#### Minor piece

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.526 (595) | 0.637 (893) | 0.707 (642) | 0.689 (61) |
| **1200** | 0.598 (1323) | 0.710 (1482) | 0.736 (1066) | 0.772 (373) |
| **1600** | 0.633 (1791) | 0.712 (2181) | 0.745 (1666) | 0.805 (594) |
| **2000** | 0.594 (2219) | 0.733 (1957) | 0.765 (1505) | 0.842 (410) |
| **2400** | 0.666 (2475) | 0.731 (1829) | 0.797 (919) | 0.833 (n=6*) |

#### Pawn

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.587 (310) | 0.661 (507) | 0.669 (411) | 0.286 (n=21*) |
| **1200** | 0.611 (758) | 0.719 (975) | 0.787 (776) | 0.780 (195) |
| **1600** | 0.684 (1169) | 0.778 (1425) | 0.829 (1107) | 0.875 (407) |
| **2000** | 0.626 (1424) | 0.784 (1077) | 0.838 (942) | 0.865 (259) |
| **2400** | 0.695 (1573) | 0.779 (855) | 0.866 (439) | n=1* |

#### Queen

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.695 (351) | 0.775 (728) | 0.786 (673) | 0.704 (54) |
| **1200** | 0.703 (789) | 0.764 (996) | 0.834 (812) | 0.884 (233) |
| **1600** | 0.723 (1156) | 0.777 (1168) | 0.850 (894) | 0.913 (321) |
| **2000** | 0.702 (1481) | 0.778 (939) | 0.835 (727) | 0.890 (173) |
| **2400** | 0.764 (1628) | 0.772 (888) | 0.816 (408) | n=0* |

#### Mixed

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.602 (10.8k) | 0.688 (11.1k) | 0.721 (8958) | 0.708 (1135) |
| **1200** | 0.617 (16.3k) | 0.705 (15.7k) | 0.731 (12.1k) | 0.737 (3257) |
| **1600** | 0.648 (17.1k) | 0.694 (16.8k) | 0.737 (13.0k) | 0.770 (3886) |
| **2000** | 0.649 (17.0k) | 0.720 (13.7k) | 0.744 (10.5k) | 0.785 (2102) |
| **2400** | 0.695 (15.1k) | 0.742 (10.7k) | 0.774 (5172) | 0.841 (n=44*) |

#### Pawnless

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.730 (63) | 0.748 (202) | 0.750 (216) | 0.600 (40) |
| **1200** | 0.819 (83) | 0.820 (189) | 0.871 (193) | 0.859 (71) |
| **1600** | 0.832 (95) | 0.807 (171) | 0.821 (168) | 0.972 (36) |
| **2000** | 0.809 (115) | 0.743 (167) | 0.850 (133) | 0.895 (n=19*) |
| **2400** | 0.789 (208) | 0.699 (216) | 0.792 (130) | n=0* |

### 6c. Recovery (per-class, per-cell)

#### Rook

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.333 (1210) | 0.289 (1741) | 0.266 (1298) | 0.261 (188) |
| **1200** | 0.352 (2538) | 0.273 (2466) | 0.232 (1994) | 0.189 (535) |
| **1600** | 0.365 (2955) | 0.268 (2219) | 0.246 (1964) | 0.198 (642) |
| **2000** | 0.362 (2721) | 0.286 (1831) | 0.237 (1382) | 0.213 (348) |
| **2400** | 0.347 (2518) | 0.287 (1500) | 0.266 (764) | n=0* |

#### Minor piece

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.393 (626) | 0.337 (968) | 0.325 (693) | 0.379 (87) |
| **1200** | 0.413 (1441) | 0.292 (1537) | 0.244 (1302) | 0.218 (390) |
| **1600** | 0.424 (2091) | 0.278 (1729) | 0.241 (1599) | 0.213 (601) |
| **2000** | 0.429 (2152) | 0.294 (1721) | 0.273 (1346) | 0.239 (385) |
| **2400** | 0.401 (2249) | 0.306 (1573) | 0.250 (749) | n=0* |

#### Pawn

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.331 (323) | 0.357 (603) | 0.290 (376) | 0.360 (50*) |
| **1200** | 0.339 (817) | 0.240 (964) | 0.235 (870) | 0.185 (227) |
| **1600** | 0.382 (1227) | 0.251 (1107) | 0.196 (1084) | 0.184 (397) |
| **2000** | 0.364 (1320) | 0.237 (949) | 0.171 (868) | 0.130 (185) |
| **2400** | 0.334 (1441) | 0.240 (717) | 0.160 (388) | n=0* |

#### Queen

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.228 (346) | 0.242 (840) | 0.242 (660) | 0.238 (101) |
| **1200** | 0.259 (834) | 0.212 (967) | 0.188 (958) | 0.129 (249) |
| **1600** | 0.297 (1329) | 0.237 (920) | 0.198 (767) | 0.091 (252) |
| **2000** | 0.292 (1319) | 0.238 (867) | 0.209 (590) | 0.079 (139) |
| **2400** | 0.255 (1559) | 0.226 (739) | 0.158 (354) | n=0* |

#### Mixed

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.363 (11.4k) | 0.299 (11.8k) | 0.266 (9028) | 0.226 (1370) |
| **1200** | 0.369 (17.4k) | 0.284 (15.4k) | 0.267 (11.8k) | 0.211 (3294) |
| **1600** | 0.359 (18.9k) | 0.285 (14.7k) | 0.262 (11.9k) | 0.238 (3634) |
| **2000** | 0.358 (16.1k) | 0.314 (12.7k) | 0.265 (9336) | 0.260 (1892) |
| **2400** | 0.349 (13.9k) | 0.309 (9861) | 0.289 (4718) | 0.300 (n=10*) |

#### Pawnless

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 0.205 (39*) | 0.264 (220) | 0.257 (237) | 0.378 (37*) |
| **1200** | 0.173 (75*) | 0.177 (175) | 0.141 (199) | 0.125 (48*) |
| **1600** | 0.202 (104) | 0.185 (146) | 0.147 (143) | 0.060 (50*) |
| **2000** | 0.202 (104) | 0.201 (154) | 0.147 (102) | 0.118 (n=17*) |
| **2400** | 0.219 (215) | 0.189 (180) | 0.220 (118) | n=0* |

### Recommendations

- **Per-class score-diff neutral zone** (`NEUTRAL_ZONE_MIN/MAX = ±0.05` in `EndgameWDLChart.tsx`): pooled per-class score_diff is `+0.011 to +0.021` for all 6 classes — well inside ±0.05. **Keep `±0.05`**.
- **Per-class conversion bands** (live `PER_CLASS_GAUGE_ZONES`):
  - rook live `[0.65, 0.75]` → pooled p25/p75 from cell aggregates clusters around `[0.64, 0.78]`. **Widen slightly** to `[0.63, 0.78]` if user-perceived "neutral" should track the population IQR.
  - minor_piece live `[0.63, 0.73]` → pooled mean 0.695. **Keep**.
  - pawn live `[0.67, 0.77]` → pooled mean 0.738. **Shift up** to `[0.67, 0.79]`.
  - queen live `[0.73, 0.83]` → pooled mean 0.774. **Keep**.
  - mixed live `[0.65, 0.75]` → pooled mean 0.694. **Keep**.
  - pawnless live `[0.70, 0.80]` → pooled mean 0.791. **Shift up** to `[0.72, 0.83]` (small-n class, hold off until more data).
- **Per-class recovery bands** (live `PER_CLASS_GAUGE_ZONES`):
  - rook live `[0.28, 0.38]` → pooled mean 0.296. **Shift down** to `[0.26, 0.36]`.
  - minor_piece live `[0.31, 0.41]` → pooled mean 0.328. **Keep**.
  - pawn live `[0.26, 0.36]` → pooled mean 0.275. **Shift down** to `[0.23, 0.34]`.
  - queen live `[0.20, 0.30]` → pooled mean 0.234. **Keep**.
  - mixed live `[0.28, 0.38]` → pooled mean 0.311. **Keep**.
  - pawnless live `[0.21, 0.31]` → pooled mean 0.198. **Shift down** to `[0.16, 0.26]` (small-n).

The shifts are small (≤3pp). Run a regen of `endgameZones.ts` if a pass on `app/services/endgame_zones.py` is opened — otherwise leave as-is, the gauges are already calibrated within ±5pp of the new pooled bands.

### Collapse verdict

Per skill methodology, aggregated to one verdict per metric (across-class max d):

| Metric | TC max \|d\| | ELO max \|d\| | TC | ELO |
|---|---|---|---|---|
| Per-class score | ~0.10 (mixed) | ~0.10 (mixed) | **collapse** | **collapse** |
| Per-class conversion | ~1.10 (pawn bullet vs classical) | ~0.85 (pawn 800 vs 2400) | **keep separate** | **keep separate** |
| Per-class recovery | ~1.20 (pawn bullet vs classical) | ~0.30 (varies) | **keep separate** | **review** |

(d_max estimates from cell rate spreads — score values within `±0.05` of 0.5 across all cells, conv/recov vary by 0.3+ across TC and ~0.2 across ELO.)

The TC verdict for conversion and recovery is consistent with §2 (whole-game): bullet has the lowest conv and the highest recov; classical has the highest conv and the lowest recov. Per-class bands are consistent with whole-game per-TC bands.

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|
| Score gap (eg − non_eg) | review (0.34) | collapse (0.17) | Single zone OK; classical cohort sits left-of-center |
| Conversion (per-user) | **keep separate** (1.02) | **keep separate** (0.82) | Stratify by both axes; use per-TC bands |
| Parity (per-user) | collapse (0.12) | review (0.48) | Single zone fine; ELO ramp expected |
| Recovery (per-user) | **keep separate** (1.10) | review (0.40) | Stratify by TC; bullet much higher than classical |
| Endgame Skill (per-user) | collapse (0.18) | **keep separate** (0.78) | Single zone correct; ELO ramp is the skill signal |
| Clock pressure %-of-base | review (0.23) | review (0.21) | Borderline collapse; ±5% is fine population-wide |
| Net timeout rate | collapse (0.07) | review (0.41) | Single zone OK; high-rated win more on time |
| Time-pressure curve (per-bucket) | review (0.34) | collapse (0.17) | TC stratification driven by bucket-0; UI already per-TC |
| Per-class score | collapse (~0.10) | collapse (~0.10) | Pooled `±0.05` band fits all classes |
| Per-class conversion | **keep separate** (~1.1) | **keep separate** (~0.85) | Per-class × per-TC bands ideally |
| Per-class recovery | **keep separate** (~1.2) | review (~0.3) | Per-class × per-TC bands ideally |

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|
| Score gap neutral | `SCORE_GAP_NEUTRAL_MIN/MAX` | ±0.10 | ±0.10 | TC review / ELO collapse | **keep** |
| Score gap domain | `SCORE_GAP_DOMAIN` | 0.20 | 0.23–0.25 | — | **widen to 0.25** (optional, gives p95 headroom) |
| Score timeline neutral | (none currently) | — | `[0.47, 0.55]` | TC review / ELO collapse | **add** unified eg/non_eg neutral band |
| Score timeline Y-axis | `SCORE_TIMELINE_Y_DOMAIN` | [20, 80] | [35, 70] | — | **keep** (current is generous, reflects extreme users) |
| Conversion neutral | `FIXED_GAUGE_ZONES.conversion` | [0.65, 0.75] | per-TC: bullet [0.58,0.72] / blitz [0.67,0.76] / rapid [0.70,0.79] / classical [0.70,0.83] | TC keep / ELO keep | **stratify per TC** |
| Parity neutral | `FIXED_GAUGE_ZONES.parity` | [0.45, 0.55] | [0.45, 0.55] | TC collapse / ELO review | **keep** |
| Recovery neutral | `FIXED_GAUGE_ZONES.recovery` | [0.25, 0.40] | per-TC: bullet [0.30,0.40] / blitz [0.25,0.36] / rapid [0.23,0.33] / classical [0.18,0.32] | TC keep / ELO review | **stratify per TC** |
| Endgame Skill neutral | `ENDGAME_SKILL_ZONES` | [0.45, 0.55] | [0.47, 0.55] | TC collapse / ELO keep | **keep** |
| Clock pressure neutral | `NEUTRAL_PCT_THRESHOLD` | ±5.0 | ±5.0 | both review | **keep** |
| Net timeout neutral | `NEUTRAL_TIMEOUT_THRESHOLD` | ±5.0 | ±5.0 | TC collapse / ELO review | **keep** |
| Time-pressure Y-axis | `Y_AXIS_DOMAIN` | [0.2, 0.8] | [0.2, 0.8] | — | **keep** |
| Per-class score-diff | `NEUTRAL_ZONE_MIN/MAX` (EndgameWDLChart) | ±0.05 | ±0.05 | both collapse | **keep** |
| Per-class conv (rook) | `PER_CLASS_GAUGE_ZONES.rook.conversion` | [0.65, 0.75] | [0.63, 0.78] | per-TC ideal | **widen slightly** |
| Per-class conv (pawn) | `PER_CLASS_GAUGE_ZONES.pawn.conversion` | [0.67, 0.77] | [0.67, 0.79] | per-TC ideal | **shift up** |
| Per-class conv (pawnless) | `PER_CLASS_GAUGE_ZONES.pawnless.conversion` | [0.70, 0.80] | [0.72, 0.83] | per-TC ideal | **shift up** (small-n) |
| Per-class conv (others) | minor/queen/mixed | per zone file | (within ±2pp of pooled) | per-TC ideal | **keep** |
| Per-class recov (rook) | `PER_CLASS_GAUGE_ZONES.rook.recovery` | [0.28, 0.38] | [0.26, 0.36] | per-TC ideal | **shift down** |
| Per-class recov (pawn) | `PER_CLASS_GAUGE_ZONES.pawn.recovery` | [0.26, 0.36] | [0.23, 0.34] | per-TC ideal | **shift down** |
| Per-class recov (pawnless) | `PER_CLASS_GAUGE_ZONES.pawnless.recovery` | [0.21, 0.31] | [0.16, 0.26] | per-TC ideal | **shift down** (small-n) |
| Per-class recov (others) | minor/queen/mixed | per zone file | (within ±2pp of pooled) | per-TC ideal | **keep** |

The most impactful changes are §2 conversion + recovery per-TC stratification. Splitting those gauges into per-TC bands aligns the live UI with the single largest cohort effect in the data.

# FlawChess Benchmarks — 2026-05-04

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-04T16:53:48Z
- **Population**: 2,415 users in DB / 1,912 selected with ≥1 completed cell / 1,375,544 games / 95,040,660 game_positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; `tc_bucket` from same table; per-user TC restricted to selected `tc_bucket` (`g.time_control_bucket::text = bsu.tc_bucket`)
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,133 candidate users, ~100 users/cell completed
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (universal — all sections)**: `abs(opp_rating - user_rating) <= 100`. Applied to every per-game CTE in §1, §2, §4, §5, §6 and to the §3 main block. **NOT** applied to the §3 color-split sub-block (production calibration target — the live z-test runs on unfiltered games). See `.planning/notes/benchmark-equal-footing-framing.md` for rationale.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in §6). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity).
- **Eval coverage**: 100.00% at endgame entry (767,395 of 767,398 qualifying endgame games have non-NULL eval); 100.00% at MG entry; mate-row prevalence ≈0.5% at MG, ≈5.2% at EG.
- **Sparse-cell exclusion**: `(rating_bucket=2400, tc_bucket='classical')` excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user, pool exhausted: 0 unattempted out of 23). Shown in cell-level 5×4 tables with `n=12*` footnote.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate.
- **Sample floors**: §1 ≥30 endgame AND ≥30 non-endgame games per user; §2 ≥20 endgame games per user, ≥2/3 buckets non-empty, ≥10 users per cell; §3 ≥20 phase-entry games per (user, color); §4 ≥20 endgame games per user; §5 ≥100 games per cell; §6 cell-level n_games ≥100 for score, ≥30 for conv/recov; Cohen's d ≥10 users per marginal level.

## Cell coverage (status='completed' users per cell)

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | 100 | 100 | 100 | 100 |
| 1200 | 100 | 100 | 100 | 100 |
| 1600 | 100 | 100 | 100 | 100 |
| 2000 | 100 | 100 | 100 | 100 |
| 2400 | 100 | 100 | 100 | **12*** |

\* `(2400, classical)` is pool-exhausted (12 completed / 23 candidate; 0 unattempted). Excluded from marginals.

## Status breakdown (per cell, all statuses)

Pool exhaustion limited to (2400, classical) — every other cell has 270–400 unattempted candidates and could be re-selected upward via `select_benchmark_users.py --per-cell N`. Notable outliers: classical cells have heavy `skipped` counts (228 in 800-classical, 119 in 1200-classical, 117 in 2000-classical) reflecting Lichess users who don't reach the per-TC `min-games` floor in classical.

---

## 1. Score gap (endgame vs non-endgame)

Per-user `eg_score − non_eg_score`. Sample floor: ≥30 eg AND ≥30 non-eg games per (user, TC).

### Cell table — per-user `diff_p50 (n)`

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | -0.036 (97) | -0.024 (97) | -0.023 (94) | -0.134 (24) |
| 1200 | -0.040 (97) | -0.032 (99) | +0.008 (98) | -0.055 (51) |
| 1600 | -0.017 (97) | -0.001 (99) | +0.007 (100) | -0.048 (66) |
| 2000 | -0.014 (100) | +0.005 (98) | +0.008 (95) | -0.019 (49) |
| 2400 | +0.023 (98) | -0.002 (96) | -0.009 (77) | +0.064* (n=1) |

\* Only 1 user in (2400, classical) cleared the ≥30/≥30 floor.

Color reading: classical has the most negative score-gap (users score worse in eg vs non-eg games — likely because users in classical reach endgames more often when the position has gone wrong); bullet/blitz/rapid hover near zero.

### TC marginal (sparse cell excluded)

| tc | n_users | mean | SD | p25 | p50 | p75 | p05 | p95 |
|----|--------:|-----:|---:|----:|----:|----:|----:|----:|
| bullet | 489 | -0.010 | 0.118 | -0.095 | -0.018 | +0.064 | -0.182 | +0.198 |
| blitz | 489 | -0.007 | 0.119 | -0.093 | -0.009 | +0.069 | -0.191 | +0.195 |
| rapid | 464 | -0.007 | 0.132 | -0.095 | -0.006 | +0.082 | -0.232 | +0.203 |
| classical | 190 | -0.053 | 0.162 | -0.151 | -0.046 | +0.065 | -0.337 | +0.199 |

### ELO marginal (sparse cell excluded)

| elo | n_users | mean | SD | p25 | p50 | p75 |
|----:|--------:|-----:|---:|----:|----:|----:|
| 800 | 312 | -0.025 | 0.135 | -0.116 | -0.036 | +0.053 |
| 1200 | 345 | -0.021 | 0.137 | -0.112 | -0.031 | +0.072 |
| 1600 | 362 | -0.007 | 0.137 | -0.103 | -0.009 | +0.094 |
| 2000 | 342 | -0.010 | 0.115 | -0.088 | -0.004 | +0.068 |
| 2400 | 271 | -0.004 | 0.115 | -0.082 | +0.001 | +0.074 |

### Pooled overall

n=1,632, mean=-0.013, SD=0.129, p25=-0.104, p50=-0.014, p75=+0.073, p05=-0.227, p95=+0.202.

eg side: p25=0.464, p75=0.555. non_eg side: p25=0.468, p75=0.574.

### Recommendations

- **Score-gap gauge neutral zone**: pooled `[p25, p75] = [-0.104, +0.073]`, asymmetric. Round to symmetric **±0.10** — matches live `SCORE_GAP_NEUTRAL_MIN = -0.1` / `MAX = 0.1`. **Action: keep.** (Per the skill's "score-gap re-centering — out of scope" guard, |median| = 0.014 ≪ 5pp, so symmetric ±0.10 wins.)
- **Score-gap gauge half-width**: pooled `max(|p05|, |p95|) = 0.227`. Live `SCORE_GAP_DOMAIN = 0.20` is slightly tight on the negative tail. **Action: review** — recommend bumping to **±0.25** if the negative tail looks clipped in the UI; otherwise keep.
- **Timeline neutral zone**: intersection of eg `[0.464, 0.555]` and non_eg `[0.468, 0.574]` = `[0.468, 0.555]` (overlap covers ~95% of narrower interval). **Action: propose unified band [0.47, 0.55] in score units (47–55%)**, vs. current `SCORE_TIMELINE_Y_DOMAIN = [20, 80]` with no neutral band shaded — purely informational.
- **Timeline Y-axis**: pooled tails `[min(p05, non_p05), max(p95, non_p95)] = [0.389, 0.673]` → 39–67% padded. Live `[20, 80]` is comfortably wider. **Action: keep.**

### Collapse verdict

- **TC axis**: `max |d| = 0.34` (blitz vs classical) → **review**
- **ELO axis**: `max |d| = 0.17` (800 vs 2400) → **collapse**

Heatmap of per-user `diff_p50`:

```
            bullet   blitz   rapid   classical
800         -0.036  -0.024  -0.023  -0.134*
1200        -0.040  -0.032  +0.008  -0.055
1600        -0.017  -0.001  +0.007  -0.048
2000        -0.014  +0.005  +0.008  -0.019
2400        +0.023  -0.002  -0.009  +0.064*  (n=1, sparse)
```

The TC effect is mostly classical pulling the median down (~5pp lower than other TCs); ELO effect is monotonic but small. Single-zone is fine for the gauge, but UI can reasonably annotate "classical typical-low" with a footnote.

---

## 2. Conversion / Parity / Recovery + Endgame Skill

Per-user rates bucketed by Stockfish eval at first endgame ply. Sample floor: ≥20 endgame games per user, ≥2/3 buckets non-empty.

### Currently set in code

- `FIXED_GAUGE_ZONES.conversion`: neutral band **[0.65, 0.77]**
- `FIXED_GAUGE_ZONES.parity`: neutral band **[0.45, 0.55]**
- `FIXED_GAUGE_ZONES.recovery`: neutral band **[0.24, 0.36]**
- `ENDGAME_SKILL_ZONES`: neutral band **[0.47, 0.55]**
- Score-gap chart: `NEUTRAL_ZONE_MIN = -0.05`, `MAX = 0.05`, `BULLET_DOMAIN = 0.20`

### 2a. Conversion rate (per-user p50)

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | 0.597 (99) | 0.701 (100) | 0.714 (96) | 0.714 (41) |
| 1200 | 0.625 (100) | 0.709 (99) | 0.734 (100) | 0.750 (72) |
| 1600 | 0.659 (100) | 0.712 (100) | 0.747 (100) | 0.776 (85) |
| 2000 | 0.672 (100) | 0.726 (100) | 0.749 (98) | 0.774 (66) |
| 2400 | 0.713 (100) | 0.744 (100) | 0.778 (95) | n<10* |

TC marginal mean: bullet 0.651 / blitz 0.716 / rapid 0.743 / classical 0.756. ELO marginal mean: 800=0.668 → 2400=0.749.

Pooled: n=1,751, mean=0.711, p25=0.656, p50=0.719, p75=0.769.

**Recommendation**: pooled p25/p75 = `[0.656, 0.769]`. Live band `[0.65, 0.77]` matches within 1pp. **Action: keep.** But conversion rate has a strong TC AND ELO ramp, so the "single global band" is a deliberate choice — see verdict.

**Collapse verdict**:
- TC: `max |d| ≈ 1.02` (bullet vs classical) → **keep separate**
- ELO: `max |d| ≈ 0.82` (800 vs 2400) → **keep separate**

The single FIXED band loses fidelity at the extremes: bullet-800 users (median 0.60) sit below the band even when performing typically; rapid-2400 users (median 0.78) sit above. Stratification (per-TC or per-(TC × ELO)) would give more honest signal — see "Recommended thresholds summary" for rollup.

### 2b. Parity rate (per-user p50)

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | 0.500 (97) | 0.479 (100) | 0.500 (96) | 0.385 (39) |
| 1200 | 0.490 (100) | 0.489 (99) | 0.487 (100) | 0.500 (72) |
| 1600 | 0.515 (100) | 0.500 (100) | 0.500 (100) | 0.500 (85) |
| 2000 | 0.499 (100) | 0.513 (100) | 0.519 (98) | 0.521 (66) |
| 2400 | 0.521 (100) | 0.552 (100) | 0.540 (95) | n<10* |

TC marginal mean: bullet 0.504 / blitz 0.502 / rapid 0.508 / classical 0.491. ELO marginal mean: 800=0.470 → 2400=0.537.

Pooled: n=1,751, mean=0.502, p25=0.443, p50=0.500, p75=0.563.

**Recommendation**: pooled p25/p75 = `[0.443, 0.563]`. Live band `[0.45, 0.55]` is slightly narrower. **Action: keep** (1pp drift on each side; within noise).

**Collapse verdict**:
- TC: `max |d| ≈ 0.13` → **collapse**
- ELO: `max |d| ≈ 0.48` (800 vs 2400) → **review**

Single zone OK; the ELO ramp is real (800-cohort pools sit ~7pp below 2400) but under the "keep separate" threshold.

### 2c. Recovery rate (per-user p50)

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | 0.354 (99) | 0.290 (100) | 0.258 (96) | 0.203 (41) |
| 1200 | 0.365 (100) | 0.290 (99) | 0.286 (99) | 0.226 (72) |
| 1600 | 0.340 (100) | 0.287 (100) | 0.269 (100) | 0.222 (85) |
| 2000 | 0.344 (100) | 0.330 (100) | 0.264 (98) | 0.272 (66) |
| 2400 | 0.346 (100) | 0.317 (100) | 0.300 (95) | n<10* |

TC marginal mean: bullet 0.356 / blitz 0.303 / rapid 0.286 / classical 0.250. ELO marginal mean: 800=0.297 → 2400=0.330.

Pooled: n=1,751, mean=0.305, p25=0.243, p50=0.301, p75=0.364.

**Recommendation**: pooled p25/p75 = `[0.243, 0.364]`. Live band `[0.24, 0.36]` matches within 0.4pp. **Action: keep.**

**Collapse verdict**:
- TC: `max |d| ≈ 1.10` (bullet vs classical) → **keep separate**
- ELO: `max |d| ≈ 0.40` → **review**

The TC ramp (0.36 in bullet down to 0.25 in classical) is the dominant story — bullet users save more "lost" endgames because in time pressure the opponent fails to convert. Single-zone underrepresents this.

### 2d. Endgame Skill (per-user p50)

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | 0.481 (99) | 0.497 (100) | 0.493 (96) | 0.438 (41) |
| 1200 | 0.492 (100) | 0.496 (99) | 0.508 (100) | 0.496 (72) |
| 1600 | 0.509 (100) | 0.501 (100) | 0.507 (100) | 0.516 (85) |
| 2000 | 0.506 (100) | 0.521 (100) | 0.512 (98) | 0.523 (66) |
| 2400 | 0.528 (100) | 0.543 (100) | 0.544 (95) | n<10* |

TC marginal mean: bullet 0.504 / blitz 0.507 / rapid 0.513 / classical 0.499. ELO marginal mean: 800=0.478 → 2400=0.539.

Pooled: n=1,751, mean=0.506, p25=0.466, p50=0.508, p75=0.548.

**Recommendation**: pooled p25/p75 = `[0.466, 0.548]`. Live `ENDGAME_SKILL_ZONES` neutral band `[0.47, 0.55]` matches within 0.4pp. **Action: keep.**

**Collapse verdict**:
- TC: `max |d| ≈ 0.18` → **collapse**
- ELO: `max |d| ≈ 0.78` (800 vs 2400) → **keep separate**

Skill is the unweighted mean of conv/par/recov — its ELO effect aggregates the conv ramp (++) with the recov ramp (mild +) and parity ramp (+). 800 cohort medians ~0.48 vs 2400 cohort ~0.54 — band-width gap. Single-zone misses this; per-ELO band would be more honest (see threshold summary).

---

## 3. Evals at game phase transitions

Per-(user, color) mean signed user-POV `eval_cp` at first ply where `phase = 1` (MG entry) or `phase = 2` (EG entry), centered on color-matched baseline. Mate scores and `|eval_cp| ≥ 2000` excluded (matches production filter `has_continuous_in_domain_eval`). Sample floor: ≥20 entry-ply games per (user, color).

### Currently set in code

- `EVAL_BASELINE_CP_WHITE = 31.5`, `EVAL_BASELINE_CP_BLACK = -18.9` (in `app/services/opening_insights_constants.py`)
- `EVAL_CONFIDENCE_MIN_N = 20`
- `EVAL_NEUTRAL_MIN_PAWNS = -0.30`, `EVAL_NEUTRAL_MAX_PAWNS = 0.30`, `EVAL_BULLET_DOMAIN_PAWNS = 1.5` (in `frontend/src/lib/openingStatsZones.ts`)
- EG-entry constants: not yet defined (no live z-test or bullet chart).

### 3a. MG entry — color-split engine-asymmetry baseline (game-level)

| color | n_games | mean | median | SD | p05 | p95 |
|-------|--------:|-----:|-------:|---:|----:|----:|
| white | 624,634 | **+31.53** | +28.0 | 238.0 | -397 | +462 |
| black | 625,130 | **-18.86** | -20.0 | 237.3 | -445 | +414 |
| pooled | 1,249,764 | +6.32 | +4.0 | 239.0 | -423 | +440 |

**Recommendation**: live `EVAL_BASELINE_CP_WHITE = 31.5` matches measured +31.53 (Δ=0.03 cp); `EVAL_BASELINE_CP_BLACK = -18.9` matches measured -18.86 (Δ=0.04 cp). **Action: keep both.** The benchmark population reproduces the 2026-03 calibration to two decimal places — engine-version and population drift have not moved the asymmetry baseline.

### 3b. MG entry — per-(user, color) centered distribution

| color | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|-------|--:|-----:|---:|----:|----:|----:|----:|----:|
| white | 1,745 | -1.81 | 58.6 | -102.8 | -28.6 | +2.2 | +29.1 | +82.1 |
| black | 1,751 | -2.55 | 57.7 | -97.8 | -25.7 | -0.7 | +26.2 | +78.5 |
| **pooled** | **3,496** | **-2.18** | **58.2** | **-100.0** | **-26.8** | **+0.6** | **+27.9** | **+80.2** |

**Color-axis Cohen's d**: `(−1.81 − (−2.55)) / sqrt((58.6² + 57.7²)/2) = 0.74 / 58.16 ≈ 0.013` → **collapse**. Centering on the color-matched baseline removes the engine asymmetry by construction; the residual cross-color drift is statistical noise (well below the 0.2 threshold).

**Collapse verdict (centered)**:
- Color: `|d| ≈ 0.013` → **collapse**
- TC: `max |d| ≈ 0.25` (bullet vs rapid) → **review**
- ELO: `max |d| ≈ 0.23` (800 vs 2000) → **review**

Both review verdicts are driven by the 800 cohort (-13 cp centered) and the bullet cohort (-11 cp centered) entering MG slightly worse than baseline. Effect size is ~25% of within-cell SD — small but real.

**Recommendations** (MG-entry bullet-chart neutral zone & domain):
- Neutral zone: pooled `[p25, p75] = [-26.8, +27.9]` → symmetric **±28 cp ≈ ±0.28 pawns**. Live `EVAL_NEUTRAL_MIN/MAX_PAWNS = ±0.30`. **Action: keep** (Δ=2 cp; within noise).
- Domain: pooled `[p05, p95] = [-100.0, +80.2]` → symmetric **±100 cp = ±1.0 pawns**. Live `EVAL_BULLET_DOMAIN_PAWNS = 1.5`. Live is wider than data demands; **Action: keep** for visual headroom (the 5–95% tails cover ±1.0 pawns; the live bound covers tail outliers cleanly).

### 3c. EG entry — color-split engine-asymmetry baseline (game-level)

| color | n_games | mean | median | SD | p05 | p95 |
|-------|--------:|-----:|-------:|---:|----:|----:|
| white | 400,153 | +23.11 | +9.0 | 443.1 | -710 | +736 |
| black | 402,909 | +3.21 | 0.0 | 441.7 | -723 | +720 |
| pooled | 803,062 | +13.12 | +3.0 | 442.5 | -716 | +728 |

**Note**: no live constants for EG entry yet (no z-test or bullet chart shipped). When that infrastructure lands, calibrate against these values.

### 3d. EG entry — per-(user, color) centered distribution

| color | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|-------|--:|-----:|---:|----:|----:|----:|----:|----:|
| white | 1,654 | -3.37 | 119.8 | -199.2 | -69.1 | +1.2 | +63.7 | +183.6 |
| black | 1,650 | -5.16 | 113.8 | -193.2 | -65.7 | -5.3 | +59.0 | +185.3 |
| **pooled** | **3,304** | **-4.26** | **116.8** | **-196.0** | **-66.9** | **-2.4** | **+62.2** | **+183.8** |

**Color-axis Cohen's d**: `(−3.37 − (−5.16)) / sqrt((119.8² + 113.8²)/2) = 1.79 / 116.83 ≈ 0.015` → **collapse**.

**Collapse verdict (centered)**:
- Color: `|d| ≈ 0.015` → **collapse**
- TC: `max |d| ≈ 0.22` (bullet vs rapid) → **review**
- ELO: `max |d| ≈ 0.28` (800 vs 2400) → **review**

Same pattern as MG: centering removes engine bias cleanly; weak TC + ELO cohort effects (lower ratings enter EG at slightly worse-than-baseline).

**Recommendations** (informational — no live constants):
- Neutral zone: pooled `[p25, p75] = [-66.9, +62.2]` → symmetric **±65 cp ≈ ±0.65 pawns**.
- Domain: pooled `[p05, p95] = [-196.0, +183.8]` → symmetric **±200 cp = ±2.0 pawns**.

EG-entry signal is ~2.5× as wide as MG-entry (SD 117 vs 58 cp) — by EG, evals have had time to drift further from book parity, and the within-user mean swings further too.

### 3e. Eval coverage at phase entry

| phase | n_games | with_eval | mate_count | pct_with_eval |
|-------|--------:|----------:|-----------:|--------------:|
| MG (phase=1) | 1,299,252 | 1,299,252 | 6,355 | 100.00% |
| EG (phase=2) | 875,463 | 875,460 | 45,335 | 100.00% |

Mate-row prevalence at MG ≈0.5%, at EG ≈5.2% — both excluded from the centered means per production filter. No coverage gap.

---

## 4. Time pressure at endgame entry

Per-user clock-diff % of base time (`(user_clk − opp_clk) / base_time_seconds × 100`) and net timeout rate (`(timeout_wins − timeout_losses) / games × 100`). SQL approximates the backend ply-walk by routing clocks at `entry_ply` and `entry_ply + 1` by parity.

### Currently set in code

- `NEUTRAL_PCT_THRESHOLD = 5.0` (clock-diff %)
- `NEUTRAL_TIMEOUT_THRESHOLD = 5.0` (net timeout %)

### 4a. Clock-diff % (per-user p50)

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | -0.70 (98) | -0.76 (100) | +1.24 (96) | +0.18 (38) |
| 1200 | -0.43 (100) | -0.48 (99) | -0.09 (100) | +1.17 (72) |
| 1600 | -0.20 (99) | -1.70 (100) | -0.12 (100) | -0.20 (85) |
| 2000 | -1.53 (100) | -1.48 (100) | -1.27 (98) | -5.69 (64) |
| 2400 | +0.12 (99) | -0.04 (100) | -3.29 (95) | n<10* |

TC marginal: bullet -0.43 / blitz -0.77 / rapid -0.25 / classical -0.70. ELO marginal: 800=-0.29 → 2400=-0.21 (no monotonic ramp).

Pooled: n=1,743, mean=-1.28, p25=-6.41, p50=-0.52, p75=+4.66, p05=-18.16, p95=+13.43.

**Recommendation**: pooled p25/p75 = `[-6.41, +4.66]`, asymmetric. Round to symmetric **±5pp** — matches live `NEUTRAL_PCT_THRESHOLD = 5.0`. **Action: keep.** (Pooled p50 = -0.52 ≪ 5pp re-centering threshold.)

**Collapse verdict**:
- TC: `max |d| ≈ 0.23` (bullet vs classical) → **review**
- ELO: `max |d| ≈ 0.21` (2000 vs 2400) → **review**

Both axes are noticeable but not dominant. Single-zone fine; UI could optionally widen the band for classical (where the SD is ~1.6× higher than bullet).

### 4b. Net timeout rate (per-user p50)

|     | bullet | blitz | rapid | classical |
|-----|-------:|------:|------:|----------:|
| 800 | -5.25 (98) | -0.29 (100) | +1.32 (96) | 0.00 (38) |
| 1200 | -0.56 (100) | +2.03 (99) | +1.16 (100) | 0.00 (72) |
| 1600 | +1.98 (99) | +1.13 (100) | +2.01 (100) | 0.00 (85) |
| 2000 | +2.19 (100) | +2.25 (100) | +1.97 (98) | +0.58 (64) |
| 2400 | +5.53 (99) | +1.95 (100) | +2.42 (95) | n<10* |

TC marginal mean: bullet +0.37 / blitz -0.01 / rapid +0.16 / classical -0.33. ELO marginal mean: 800=-2.01 → 2400=+2.77 (clear monotonic ramp).

Pooled: n=1,743, mean=+0.10, p25=-4.43, p50=+1.04, p75=+5.63, p05=-20.37, p95=+16.94.

**Recommendation**: pooled p25/p75 = `[-4.43, +5.63]`, near-symmetric. Round to symmetric **±5pp** — matches live `NEUTRAL_TIMEOUT_THRESHOLD = 5.0`. **Action: keep.**

**Collapse verdict**:
- TC: `max |d| ≈ 0.05` → **collapse**
- ELO: `max |d| ≈ 0.41` (800 vs 2400) → **review**

ELO has a real positive ramp — better players win net timeouts more (they're better at flagging opponents in flag races). Under "review", single-zone holds; per-ELO refinement would be cosmetic.

---

## 5. Time pressure vs performance

Per-(TC × ELO × time-bucket) score. Time bucket = `floor(clock_at_entry / base_time × 10)`, clamped to [0,9]. Sample floor: cell shown if n ≥ 100.

### Currently set in code

- `Y_AXIS_DOMAIN = [0.2, 0.8]`
- `X_AXIS_DOMAIN = [0, 100]`
- `MIN_GAMES_FOR_CLOCK_STATS = 10`

### Pooled curve (sparse cell excluded)

| time_bucket | games | score |
|------------:|------:|------:|
| 0 (0–10%) | 37,175 | 0.307 |
| 1 (10–20%) | 48,993 | 0.418 |
| 2 (20–30%) | 53,618 | 0.488 |
| 3 (30–40%) | 62,991 | 0.521 |
| 4 (40–50%) | 69,987 | 0.541 |
| 5 (50–60%) | 74,629 | 0.549 |
| 6 (60–70%) | 73,878 | 0.544 |
| 7 (70–80%) | 64,020 | 0.536 |
| 8 (80–90%) | 42,376 | 0.528 |
| 9 (90%+) | 25,470 | 0.517 |

The curve rises steeply through buckets 0–4, peaks at ~0.55 in buckets 5–6, then declines slightly into the high-clock region. The pooled p50 stays comfortably within `Y_AXIS_DOMAIN = [0.2, 0.8]`; bucket 0 (low-time) at 0.307 sits near the 0.2 floor.

### TC marginals (score per bucket, n in parens)

| bucket | bullet | blitz | rapid | classical |
|-------:|-------:|------:|------:|----------:|
| 0 | 0.260 (15275) | 0.334 (14823) | 0.338 (5686) | 0.410 (1391) |
| 1 | 0.399 (25401) | 0.437 (16660) | 0.441 (5987) | 0.452 (945) |
| 2 | 0.491 (27230) | 0.492 (17700) | 0.469 (7563) | 0.468 (1125) |
| 3 | 0.530 (30735) | 0.518 (21039) | 0.508 (9892) | 0.475 (1325) |
| 4 | 0.552 (31404) | 0.534 (24283) | 0.532 (12704) | 0.478 (1596) |
| 5 | 0.564 (29148) | 0.548 (26875) | 0.533 (16604) | 0.487 (2002) |
| 6 | 0.563 (23294) | 0.544 (26851) | 0.529 (21177) | 0.505 (2556) |
| 7 | 0.553 (14683) | 0.542 (21931) | 0.523 (24233) | 0.510 (3173) |
| 8 | 0.542 (5843) | 0.534 (12420) | 0.524 (20363) | 0.502 (3750) |
| 9 | 0.500 (1235) | 0.523 (4776) | 0.524 (9602) | 0.510 (9857) |

**Pattern**: classical curve is the flattest (range 0.41–0.51, ~10pp); bullet curve is the steepest (range 0.26–0.56, ~30pp). At bucket 0 (low time), classical scores 0.41 vs bullet 0.26 — a 15pp spread that flips at bucket 5 (classical 0.49 vs bullet 0.56).

### ELO marginals (score per bucket, n in parens)

| bucket | 800 | 1200 | 1600 | 2000 | 2400 |
|-------:|----:|-----:|-----:|-----:|-----:|
| 0 | 0.266 (5390) | 0.283 (7308) | 0.304 (8383) | 0.332 (9617) | 0.336 (6477) |
| 5 | 0.538 (9698) | 0.532 (15517) | 0.537 (18660) | 0.563 (16957) | 0.575 (13797) |
| 9 | 0.490 (5320) | 0.501 (8527) | 0.537 (7433) | 0.547 (3316) | 0.564 (874) |

ELO ramp is gentler than TC: bucket 0 spans 0.27–0.34 (7pp); bucket 5 spans 0.53–0.58 (5pp).

### Collapse verdict

- **TC axis** (per-bucket d on per-game score): `max |d| ≈ 0.34` at bucket 0 (bullet vs classical) → **review**
- **ELO axis**: `max |d| ≈ 0.16` at bucket 0 (800 vs 2400) → **collapse**

**Recommendation**: Time-pressure curve is genuinely TC-stratified at the low-time end (bucket 0–2). ELO collapses across all buckets. **Per-TC overlay** is the natural display choice — and a quick visual check on the live UI suggests this is already the rendering (one curve per TC). Keep the unified Y-axis `[0.2, 0.8]` (covers all buckets including bucket-0 low-rating cells).

---

## 6. Endgame type breakdown

Per-(game, endgame_class) span ≥6 plies. Each game traversing multiple classes contributes once per class. Bucketed by Stockfish eval at the first ply of each class span (REFAC-02). Sample floor for cell display: n_games ≥ 100 (score) / n_conv ≥ 30 / n_recov ≥ 30.

### Currently set in code (EndgameWDLChart score-diff)

- `NEUTRAL_ZONE_MIN = -0.05`, `NEUTRAL_ZONE_MAX = 0.05`, `BULLET_DOMAIN = 0.30`

### Currently set in code (PER_CLASS_GAUGE_ZONES, in `endgameZones.ts`, sourced from 2026-05-01 report)

| class | conv band | recov band |
|-------|-----------|------------|
| rook | [0.65, 0.75] | [0.26, 0.36] |
| minor_piece | [0.63, 0.73] | [0.31, 0.41] |
| pawn | [0.67, 0.79] | [0.23, 0.34] |
| queen | [0.73, 0.83] | [0.20, 0.30] |
| mixed | [0.65, 0.75] | [0.28, 0.38] |
| pawnless | [0.70, 0.80] | [0.21, 0.31] |

### Pooled-by-class summary (sparse cell excluded)

| class | games | users | score | score_diff | conv (n_conv) | recov (n_recov) |
|-------|------:|------:|------:|-----------:|--------------:|----------------:|
| rook | 94,087 | 1,845 | 0.5075 | +0.015 | 0.7098 (32,579) | 0.2963 (30,814) |
| minor_piece | 70,381 | 1,825 | 0.5102 | +0.020 | 0.6949 (23,981) | 0.3278 (23,239) |
| pawn | 37,463 | 1,750 | 0.5105 | +0.021 | 0.7379 (14,636) | 0.2754 (13,920) |
| queen | 34,432 | 1,764 | 0.5079 | +0.016 | 0.7744 (14,419) | 0.2343 (13,790) |
| mixed | 529,608 | 1,888 | 0.5055 | +0.011 | 0.6940 (204,367) | 0.3111 (199,172) |
| pawnless | 5,847 | 1,365 | 0.5069 | +0.014 | 0.7913 (2,515) | 0.1976 (2,363) |

### Per-class zone drift vs current PER_CLASS_GAUGE_ZONES

| class | pop conv | band center | Δ conv | pop recov | band center | Δ recov |
|-------|---------:|------------:|-------:|----------:|------------:|--------:|
| rook | 0.710 | 0.700 | +1.0pp | 0.296 | 0.310 | -1.4pp |
| minor_piece | 0.695 | 0.680 | +1.5pp | 0.328 | 0.360 | -3.2pp |
| pawn | 0.738 | 0.730 | +0.8pp | 0.275 | 0.285 | -1.0pp |
| queen | 0.774 | 0.780 | -0.6pp | 0.234 | 0.250 | -1.6pp |
| mixed | 0.694 | 0.700 | -0.6pp | 0.311 | 0.330 | -1.9pp |
| pawnless | 0.791 | 0.750 | **+4.1pp** | 0.198 | 0.260 | **-6.2pp** |

**Pawnless** is the outlier — population conv (0.79) sits at the band's upper edge and population recov (0.20) sits below the band's lower edge. The sample is small (n=5,847 across 1,365 users; ~4 games per user) so the pop estimate is noisier than other classes, but the drift is consistent with the underlying claim that pawnless endgames skew more decisive (high conv, low recov) than the band currently shows.

### Recommendations

- **Score-diff neutral zone** (`EndgameWDLChart`): all per-class score_diff values fit within ±0.025 of zero. Live ±0.05 is comfortable. **Action: keep.**
- **Conv/recov per-class bands**: rook / minor_piece / pawn / queen / mixed all sit within ±2pp of band center. **Action: keep.**
- **Pawnless band**: pop estimates have drifted ~5pp away from the current band on both metrics. **Action: review** — recommend tightening to `conv [0.74, 0.84]` and `recov [0.15, 0.25]` if confident in the sample (n=2,515 conv / n=2,363 recov is enough to detect 5pp shifts at α=0.05), or keep with footnote.

### Collapse verdict (rate-level, across-class summarized)

- **Score**: per-class score_diff range is +0.011 to +0.021 (10pp narrow). `max |d|` across class × axis combinations stays under 0.2 → **collapse**.
- **Conversion**: per-class spread 0.694 (mixed) → 0.791 (pawnless), ~10pp. Cross-class effect dominates. → **keep separate** (already implemented via PER_CLASS_GAUGE_ZONES).
- **Recovery**: per-class spread 0.198 (pawnless) → 0.328 (minor_piece), ~13pp. → **keep separate** (already implemented).

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | TC verdict (max \|d\|) | ELO verdict (max \|d\|) | Implication |
|--------|----------------------|------------------------|-------------|
| Score gap (eg − non_eg) per-user | review (0.34, blitz vs classical) | collapse (0.17) | Single zone OK; classical pulls median negative |
| Conversion per-user | **keep separate (1.02)** | **keep separate (0.82)** | Stratify per (TC × ELO); current single FIXED band underrepresents extremes |
| Parity per-user | collapse (0.13) | review (0.48) | Single zone OK; mild ELO ramp |
| Recovery per-user | **keep separate (1.10)** | review (0.40) | Stratify per TC; bullet >> classical |
| Endgame Skill per-user | collapse (0.18) | **keep separate (0.78)** | Stratify per ELO |
| MG-entry eval per-(user,color) centered | review (0.25) | review (0.23) | Color collapses (d≈0.01); single zone tolerable |
| EG-entry eval per-(user,color) centered | review (0.22) | review (0.28) | Color collapses (d≈0.02); single zone tolerable |
| Clock-diff %-of-base per-user | review (0.23) | review (0.21) | Single zone fine; mild axis effects |
| Net timeout rate per-user | collapse (0.05) | review (0.41) | Single zone OK; ELO has real ramp |
| Time-pressure curve per-bucket | review (0.34, bucket 0) | collapse (0.16) | Per-TC overlay needed at low-time end |
| Per-class score-diff | collapse | collapse | Single ±0.05 zone fits all classes |
| Per-class conversion | keep separate | (handled in cohorts) | Per-class bands required (already in code) |
| Per-class recovery | keep separate | (handled in cohorts) | Per-class bands required (already in code) |

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended | Collapse verdict | Action |
|--------|---------------|---------------|-------------|------------------|--------|
| Score-gap neutral zone | `SCORE_GAP_NEUTRAL_MIN/MAX` (`endgameZones.ts`) | ±0.10 | ±0.10 | TC review / ELO collapse | **keep** |
| Score-gap domain | `SCORE_GAP_DOMAIN` | 0.20 | 0.23 | TC review / ELO collapse | **keep** (or widen to ±0.25 if tail clipping visible) |
| Timeline Y-axis | `SCORE_TIMELINE_Y_DOMAIN` | [20, 80] | [39, 67] (data-driven), live wider | — | **keep** |
| Conversion neutral band | `FIXED_GAUGE_ZONES.conversion` | [0.65, 0.77] | pooled [0.66, 0.77] | **keep separate** on both axes | **keep** (single band is a deliberate choice; per-cell stratification would be more honest but adds UI complexity) |
| Parity neutral band | `FIXED_GAUGE_ZONES.parity` | [0.45, 0.55] | pooled [0.44, 0.56] | TC collapse / ELO review | **keep** |
| Recovery neutral band | `FIXED_GAUGE_ZONES.recovery` | [0.24, 0.36] | pooled [0.24, 0.36] | **keep separate** on TC, review ELO | **keep** (single band understates TC effect) |
| Endgame Skill neutral band | `ENDGAME_SKILL_ZONES` | [0.47, 0.55] | pooled [0.47, 0.55] | TC collapse / **keep separate** ELO | **keep** (consider per-ELO if UI affords it) |
| MG-entry baseline white | `EVAL_BASELINE_CP_WHITE` | 31.5 | 31.5 | color collapse | **keep** (Δ=0.03 cp) |
| MG-entry baseline black | `EVAL_BASELINE_CP_BLACK` | -18.9 | -18.9 | color collapse | **keep** (Δ=0.04 cp) |
| MG-entry neutral zone | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | ±0.30 | ±0.28 (pooled p25/p75) | color collapse / TC+ELO review | **keep** (Δ=2 cp) |
| MG-entry domain | `EVAL_BULLET_DOMAIN_PAWNS` | 1.5 | 1.0 (pooled p05/p95) | — | **keep** (live wider for visual headroom) |
| Confidence floor | `EVAL_CONFIDENCE_MIN_N` | 20 | 20 | — | **keep** |
| Clock-diff threshold | `NEUTRAL_PCT_THRESHOLD` | 5.0 | 5.0 (pooled p25/p75 ≈ ±5) | TC+ELO review | **keep** |
| Net-timeout threshold | `NEUTRAL_TIMEOUT_THRESHOLD` | 5.0 | 5.0 (pooled p25/p75 ≈ ±5) | TC collapse / ELO review | **keep** |
| Time-pressure Y-domain | `Y_AXIS_DOMAIN` | [0.2, 0.8] | [0.2, 0.8] | TC review / ELO collapse | **keep** |
| Per-class score-diff zone | `NEUTRAL_ZONE_MIN/MAX` (`EndgameWDLChart`) | ±0.05 | ±0.05 | collapse | **keep** |
| Per-class score-diff domain | `BULLET_DOMAIN` (`EndgameWDLChart`) | 0.30 | 0.30 | — | **keep** |
| Per-class conv (rook) | `PER_CLASS_GAUGE_ZONES.rook.conversion` | [0.65, 0.75] | [0.65, 0.75] | — | **keep** |
| Per-class conv (minor_piece) | `.minor_piece.conversion` | [0.63, 0.73] | [0.63, 0.73] | — | **keep** |
| Per-class conv (pawn) | `.pawn.conversion` | [0.67, 0.79] | [0.67, 0.79] | — | **keep** |
| Per-class conv (queen) | `.queen.conversion` | [0.73, 0.83] | [0.73, 0.83] | — | **keep** |
| Per-class conv (mixed) | `.mixed.conversion` | [0.65, 0.75] | [0.65, 0.75] | — | **keep** |
| Per-class conv (pawnless) | `.pawnless.conversion` | [0.70, 0.80] | [0.74, 0.84] | — | **review** (pop +4pp; tighten if confident in n=2515 sample) |
| Per-class recov (rook) | `.rook.recovery` | [0.26, 0.36] | [0.26, 0.36] | — | **keep** |
| Per-class recov (minor_piece) | `.minor_piece.recovery` | [0.31, 0.41] | [0.28, 0.38] | — | **keep** (Δ=3pp; below threshold) |
| Per-class recov (pawn) | `.pawn.recovery` | [0.23, 0.34] | [0.23, 0.34] | — | **keep** |
| Per-class recov (queen) | `.queen.recovery` | [0.20, 0.30] | [0.20, 0.30] | — | **keep** |
| Per-class recov (mixed) | `.mixed.recovery` | [0.28, 0.38] | [0.28, 0.38] | — | **keep** |
| Per-class recov (pawnless) | `.pawnless.recovery` | [0.21, 0.31] | [0.15, 0.25] | — | **review** (pop -6pp drift; tighten if confident in n=2363 sample) |

**Net actionable**: only **pawnless** conversion and recovery bands have drifted ≥5pp from the population. Everything else is within ±2pp and stays. The MG-entry baseline calibration constants (`EVAL_BASELINE_CP_WHITE/BLACK`) reproduce to 0.04 cp — engine-version drift has not moved them.

The two "keep separate" axes that current single-zone gauges don't honor (Conversion and Recovery on TC, Endgame Skill on ELO) are deliberate UI simplifications, not bugs. If/when stratified gauges become a UI priority, the per-cell tables in §2 give the cell-specific neutral zones.

# FlawChess Benchmarks — 2026-05-24

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-24
- **Population**: 2,415 users / 1,375,544 games / 95,040,660 positions; 1,912 completed `(user, TC)` checkpoints across 20 selection cells.
- **Cell anchoring**: 400-wide ELO buckets via the cohort user's **rating at game time** (`games.white_rating` / `games.black_rating`, sub-800 dropped), NOT `benchmark_selected_users.rating_bucket`. `bsu.rating_bucket` / `bsu.median_elo` are longitudinal columns only. tc_bucket from `benchmark_selected_users`. Per-user TC restricted to selected `tc_bucket`. Methodology change captured in §1 "Rating-lag selection bias (game-time bucketing)".
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,133 selected users (candidate pool), 1,912 ingested at ~100/cell after Stage-2 `--per-cell 100`.
- **Per-user history caveat**: each user contributes up to 1000 games per TC over a 36-month window at varying ratings, so a user spans 2–3 game-time ELO buckets. "ELO bucket effect" is a genuine rating-at-game-time effect. Any whole-career per-user scalar (composite Endgame Skill) is now per-bucket, not one number — flag for the live-UI comparator.
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket::text = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter).
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating - user_rating) <= 100`, both ratings NOT NULL. Applied to every per-game CTE in Chapters 2 and 3. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. Pre-2026-05-03 score-gap / clock / time-pressure numbers are not directly comparable.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity).
- **Eval coverage**: 100.00% of qualifying endgame-entry positions carry non-NULL Stockfish eval (767,395 of 767,398).
- **Sparse-cell exclusion**: `(elo_bucket = 2400, tc_bucket = 'classical')` is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (game-time membership: 6 users / 17 games — pool exhausted). Cell shown with footnote in cell-level grids where present.
- **Verdict thresholds**: Cohen's d < 0.20 collapse / 0.20–0.50 review / ≥ 0.50 keep separate.
- **Sample floors**: subchapter-specific (2.1/3.1.2 ≥20 in-domain entry plies per (user, color); 3.1.3/3.1.4/3.1.5 ≥20 endgame entry games per (user, cell); 3.1.6/3.1.1 ≥30 EG AND ≥30 non-EG per (user, cell); 3.2.1 ≥20 EG games + ≥2 of 3 buckets; 3.2.2/3.4.2 ≥20 spans per (user, bucket/class, cell); 3.3.1 ≥20 EG games; 3.3.2 ≥100 games per (TC × time-bucket); §3.3.3 ≥5 per (user, quintile, cell), ≥10 per marginal cell; 3.4.1 per-class ≥10 games per (user, cell, class); 3.4.3 ≥30 users per class after inner join. Cohen's d ≥10 users per marginal level.).

## 1. Stratified Sample

### Cell coverage — selection pool (status='completed')

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 100 | 100 | 100 | 100 |
| 1200 | 100 | 100 | 100 | 100 |
| 1600 | 100 | 100 | 100 | 100 |
| 2000 | 100 | 100 | 100 | 100 |
| 2400 | 100 | 100 | 100 | 12\* |

`*` sparse cell — excluded from TC/ELO marginals and Cohen's d across the whole report.

### Cell coverage — game-time bucketing (users, games per cell, equal-footing applied)

| ELO \ TC | bullet (users / games) | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 137 / 56,528 | 126 / 50,038 | 162 / 45,882 | 140 / 6,907 |
| 1200 | 206 / 84,717 | 219 / 83,954 | 279 / 65,299 | 245 / 19,804 |
| 1600 | 182 / 81,041 | 220 / 82,775 | 248 / 64,306 | 208 / 23,907 |
| 2000 | 167 / 71,116 | 178 / 69,185 | 197 / 51,985 | 111 / 7,303 |
| 2400 | 126 / 59,457 | 110 / 44,305 | 103 / 17,785 | 6 / 17\* |

`*` sparse cell.

### Equal-footing retention (game-time, % of unfiltered games kept)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 83.2% | 85.2% | 82.9% | 49.8% |
| 1200 | 89.3% | 89.2% | 87.7% | 73.2% |
| 1600 | 85.5% | 88.6% | 85.9% | 71.1% |
| 2000 | 79.3% | 76.9% | 71.0% | 49.1% |
| 2400 | 64.9% | 60.6% | 47.9% | 3.9%\* |

Mid-ELO cells retain ~85–90%; 2400-rapid drops to ~48%; 2400-classical is already excluded as sparse.

### Eval coverage check (first endgame ply)

| endgame_games | with_eval | pct_with_eval |
|---:|---:|---:|
| 767,398 | 767,395 | 100.00% |

## 2. Openings

### 2.1 Middlegame-entry eval

#### Currently set in code

| Constant | Live value |
|---|---:|
| `EVAL_NEUTRAL_MIN_PAWNS` | −0.30 |
| `EVAL_NEUTRAL_MAX_PAWNS` | +0.30 |
| `EVAL_BULLET_DOMAIN_PAWNS` | 1.5 |
| `EVAL_BASELINE_PAWNS_WHITE` | +0.25 |
| `EVAL_BASELINE_PAWNS_BLACK` | −0.25 |
| `EVAL_CONFIDENCE_MIN_N` | 20 |

#### Symmetric baseline (Pass 1 — deduped game-level mean, white-POV)

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 1,246,674 | +25.18 cp | +24 cp | 238 cp |

Black baseline by construction: −25 cp.

#### Centered pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,547 | +5 cp | 58 cp | −93 cp | −22 cp | +6 cp | +35 cp | +89 cp |

#### Centered ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 764 | 0 cp | 88 cp | −147 cp | −47 cp | +9 cp | +59 cp | +129 cp |
| 1200 | 1,093 | +7 cp | 70 cp | −107 cp | −32 cp | +11 cp | +49 cp | +107 cp |
| 1600 | 1,130 | +6 cp | 46 cp | −72 cp | −19 cp | +7 cp | +36 cp | +76 cp |
| 2000 | 960 | +5 cp | 35 cp | −53 cp | −13 cp | +5 cp | +27 cp | +58 cp |
| 2400 | 600 | +3 cp | 28 cp | −43 cp | −12 cp | +4 cp | +20 cp | +49 cp |

#### Centered TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,338 | −3 cp | 68 cp | −123 cp | −32 cp | +4 cp | +37 cp | +90 cp |
| blitz | 1,325 | +4 cp | 46 cp | −76 cp | −18 cp | +4 cp | +30 cp | +74 cp |
| rapid | 1,309 | +10 cp | 50 cp | −67 cp | −15 cp | +10 cp | +36 cp | +91 cp |
| classical | 575 | +11 cp | 72 cp | −109 cp | −23 cp | +11 cp | +47 cp | +134 cp |

#### Centered 5×4 cell p50 grid (cp)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −2 (231) | +3 (210) | +22 (250) | −1 (73) |
| 1200 | −6 (299) | +10 (304) | +18 (313) | +26 (177) |
| 1600 | +1 (285) | +11 (317) | +6 (307) | +13 (221) |
| 2000 | +8 (287) | +4 (283) | +5 (286) | +6 (104) |
| 2400 | +6 (236) | −1 (211) | +9 (153) | — |

#### Collapse verdict

- TC axis: max |d| = (10.86 − (−2.74)) / sqrt((4636.8 + 5263.3)/2) = **0.19** (bullet vs classical) → **collapse**
- ELO axis: max |d| = (6.54 − (−0.17)) / sqrt((7808.4 + 4938.0)/2) = **0.08** (800 vs 1200) → **collapse**

#### Recommendations

- **Baseline**: measured +25.18 cp vs live `EVAL_BASELINE_PAWNS_WHITE = +0.25` (= +25 cp). Difference < 1 cp — **keep**.
- **Neutral-zone bounds**: pooled centered `[p25, p75] = [−22, +35] cp` → symmetric round to **±35 cp = ±0.35 pawns**. Live `[−0.30, +0.30]` is slightly tighter; widening to ±0.35 would soften the neutral band marginally. Within tuning judgment — **keep at ±0.30** unless UI feedback warrants widening.
- **Domain bounds**: pooled `[p05, p95] = [−93, +89]` → symmetric **±95 cp ≈ ±0.95 pawns**. Live domain ±1.50 pawns covers the tails comfortably — **keep**.
- Mate rows: excluded by `eval_mate IS NULL` filter at pass 1 — count not separately enumerated (production-equivalent).

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

Reuses the 3.1.6 per-user CTE (`≥30 EG AND ≥30 non_EG` floor). Pooled distribution drives the cohort-band recommendation for the Games-without-Endgame card.

##### Pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,003 | 52.1% | 8.7% | 38.4% | 46.4% | 51.9% | 57.2% | 66.9% |

##### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 342 | 51.7% | 7.7% | 39.8% | 47.2% | 51.8% | 56.5% | 64.3% |
| 1200 | 484 | 51.9% | 8.5% | 38.9% | 46.4% | 51.9% | 56.8% | 66.3% |
| 1600 | 501 | 51.7% | 9.0% | 38.4% | 45.4% | 51.5% | 56.8% | 67.3% |
| 2000 | 414 | 52.8% | 8.7% | 39.3% | 47.1% | 52.3% | 58.4% | 68.3% |
| 2400 | 262 | 52.3% | 9.5% | 35.9% | 46.8% | 52.3% | 57.9% | 68.3% |

##### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 614 | 51.2% | 8.4% | 37.0% | 46.3% | 51.2% | 56.2% | 65.5% |
| blitz | 611 | 51.7% | 8.1% | 38.6% | 46.0% | 51.8% | 56.8% | 65.4% |
| rapid | 584 | 52.6% | 8.8% | 39.4% | 46.6% | 52.0% | 58.1% | 68.3% |
| classical | 194 | 54.4% | 10.1% | 39.5% | 47.8% | 53.9% | 61.5% | 70.6% |

##### Collapse verdict

- TC axis: max |d| = (0.5445 − 0.5123) / sqrt((0.00710 + 0.01015)/2) ≈ **0.35** (bullet vs classical) → **review**
- ELO axis: max |d| = (0.5284 − 0.5170) / sqrt((0.00592 + 0.00762)/2) ≈ **0.14** (800 vs 2000) → **collapse**

##### Recommendations

- Cohort neutral band = pooled `[p25, p75] = [46.4%, 57.2%]`. Live `SCORE_BULLET_NEUTRAL_*` is `[45%, 55%]` — within ~2 pp; classical's wider IQR drives the TC `review`, otherwise stable. Routing: dedicated EG-only / non-EG bands per memory `feedback_zone_band_judgement.md` if the live UI surfaces drift; not urgent.

#### 3.1.2 Endgame-entry eval (pawns)

##### Currently set in code

| Constant | Live value |
|---|---:|
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS` | −0.60 |
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS` | +0.60 |
| `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | 2.25 |
| `ENDGAME_ENTRY_EVAL_CENTER` | 0 |

##### Symmetric baseline (Pass 1)

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 801,065 | +9.86 cp | 0 cp | 443 cp |

##### Uncentered pooled distribution (per-(user, color))

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,123 | +10 cp | 119 cp | −186 cp | −57 cp | +12 cp | +77 cp | +203 cp |

##### Uncentered ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 661 | −1 cp | 169 cp | −265 cp | −108 cp | −5 cp | +110 cp | +271 cp |
| 1200 | 968 | +3 cp | 137 cp | −223 cp | −78 cp | +1 cp | +91 cp | +229 cp |
| 1600 | 1,029 | +17 cp | 103 cp | −152 cp | −49 cp | +19 cp | +78 cp | +188 cp |
| 2000 | 892 | +17 cp | 91 cp | −130 cp | −43 cp | +19 cp | +71 cp | +160 cp |
| 2400 | 573 | +12 cp | 68 cp | −86 cp | −35 cp | +9 cp | +54 cp | +126 cp |

##### Uncentered TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,278 | −2 cp | 141 cp | −248 cp | −84 cp | 0 cp | +81 cp | +227 cp |
| blitz | 1,247 | +16 cp | 101 cp | −139 cp | −47 cp | +14 cp | +73 cp | +179 cp |
| rapid | 1,202 | +18 cp | 106 cp | −156 cp | −46 cp | +16 cp | +80 cp | +203 cp |
| classical | 396 | +5 cp | 124 cp | −208 cp | −62 cp | +12 cp | +75 cp | +204 cp |

##### Uncentered 5×4 cell p50 grid (cp)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −5 (216) | −10 (195) | 0 (223) | −21 (27) |
| 1200 | −21 (282) | +14 (284) | +9 (289) | −15 (113) |
| 1600 | −5 (274) | +22 (292) | +25 (282) | +16 (181) |
| 2000 | +13 (275) | +28 (273) | +21 (269) | +13 (75) |
| 2400 | +12 (231) | +6 (203) | +9 (139) | — |

##### Centered pooled distribution (for parity with 2.1; recommendations come from uncentered)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,123 | +10 cp | 118 cp | −183 cp | −57 cp | +11 cp | +77 cp | +202 cp |

##### Collapse verdict (centered)

- TC axis: max |d| = (18.5 − (−2.0)) / sqrt((11,070.5 + 19,752.1)/2) ≈ **0.17** (rapid vs bullet) → **collapse**
- ELO axis: max |d| = (17.2 − (−1.4)) / sqrt((10,598.4 + 28,249.9)/2) ≈ **0.13** (1600 vs 800) → **collapse**

##### Recommendations

- **Neutral-zone bounds** (uncentered): pooled IQR `[−57, +77] cp = [−0.57, +0.77] pawns`. Live `±0.60` covers most of the IQR symmetrically; editorial choice to tighten (per `feedback_zone_band_judgement.md`) keeps the band readable. **Keep at ±0.60** unless UI tuning calls for `±0.65`.
- **Domain bounds**: pooled `[p05, p95] = [−1.86, +2.03] pawns`. Live `±2.25` accommodates the broader tail comfortably — **keep**.
- **Center**: `0` (UI-mandated zero-centering) — **keep**.
- Mate rows excluded by `eval_mate IS NULL` filter (production-equivalent).

#### 3.1.3 Achievable Score (Stockfish-predicted expected score at EG entry)

##### Pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,299 | 51.0% | 7.9% | 38.2% | 46.2% | 51.1% | 55.7% | 64.5% |

##### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 374 | 50.5% | 10.7% | 33.3% | 43.5% | 50.5% | 56.8% | 67.7% |
| 1200 | 541 | 50.7% | 9.3% | 35.9% | 45.0% | 50.5% | 56.6% | 66.7% |
| 1600 | 575 | 51.5% | 7.1% | 40.4% | 46.8% | 51.5% | 56.4% | 63.6% |
| 2000 | 498 | 51.3% | 6.2% | 40.5% | 47.3% | 51.4% | 55.3% | 61.0% |
| 2400 | 311 | 50.9% | 4.8% | 43.5% | 48.0% | 50.5% | 53.6% | 59.3% |

##### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 675 | 50.3% | 9.1% | 35.4% | 44.7% | 50.2% | 56.1% | 65.6% |
| blitz | 671 | 51.2% | 6.7% | 40.6% | 47.3% | 51.2% | 55.0% | 62.0% |
| rapid | 663 | 51.6% | 7.1% | 39.9% | 46.9% | 51.5% | 56.1% | 63.7% |
| classical | 290 | 51.0% | 9.1% | 36.8% | 45.7% | 50.9% | 56.2% | 67.4% |

##### 5×4 cell p50 grid

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 50.5 (116) | 50.1 (105) | 51.0 (123) | 49.9 (30) |
| 1200 | 49.4 (149) | 51.6 (150) | 50.7 (155) | 49.6 (87) |
| 1600 | 50.2 (145) | 52.1 (161) | 52.0 (155) | 51.3 (114) |
| 2000 | 50.5 (146) | 51.6 (148) | 51.7 (145) | 51.6 (59) |
| 2400 | 50.3 (119) | 50.7 (107) | 50.2 (85) | — |

##### Collapse verdict

- TC axis: max |d| = (0.5155 − 0.5031) / sqrt((0.00510 + 0.00824)/2) ≈ **0.15** (rapid vs bullet) → **collapse**
- ELO axis: max |d| = (0.5147 − 0.5049) / sqrt((0.00497 + 0.01145)/2) ≈ **0.11** (1600 vs 800) → **collapse**

##### Recommendations

- 800–1600 game-time buckets sit within ±0.7 pp of 50%; 2000/2400 sit ≈ +1 pp above — within the documented out-of-scope residual (rating-lag tail + D-01 no-cheat-filter). No filter failure.
- Cohort neutral band = pooled `[p25, p75] = [46.2%, 55.7%]`. Asymmetric +0.5 pp above midpoint, IQR ≈ ±5 pp.
- Routing: feeds a new EG-entry expected_score ZoneSpec — do not retune `SCORE_BULLET_NEUTRAL_*` (different population).

#### 3.1.4 Endgame Score (per-user, EG-only)

##### Currently set in code

| Constant | Live value |
|---|---:|
| `SCORE_BULLET_CENTER` | 0.50 |
| `SCORE_BULLET_NEUTRAL_MIN` | −0.05 |
| `SCORE_BULLET_NEUTRAL_MAX` | +0.05 |
| `SCORE_BULLET_DOMAIN` | 0.25 |

##### Pooled distribution

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,003 | 51.0% | 7.8% | 38.8% | 46.1% | 50.7% | 55.5% | 64.0% |

##### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 342 | 49.4% | 9.1% | 36.1% | 43.4% | 48.9% | 54.3% | 65.0% |
| 1200 | 484 | 50.3% | 8.1% | 37.6% | 45.0% | 49.4% | 54.9% | 64.0% |
| 1600 | 501 | 51.0% | 8.0% | 38.9% | 45.7% | 50.7% | 55.7% | 63.9% |
| 2000 | 414 | 52.1% | 7.0% | 41.9% | 47.5% | 52.2% | 56.1% | 63.9% |
| 2400 | 262 | 52.6% | 5.4% | 44.3% | 49.4% | 52.3% | 55.9% | 61.6% |

##### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 614 | 50.2% | 6.9% | 39.6% | 45.9% | 49.8% | 54.1% | 62.2% |
| blitz | 611 | 51.2% | 7.4% | 40.2% | 46.3% | 51.1% | 55.8% | 63.3% |
| rapid | 584 | 51.8% | 8.3% | 38.8% | 46.8% | 51.8% | 56.3% | 65.4% |
| classical | 194 | 50.3% | 9.9% | 32.9% | 44.5% | 50.4% | 56.8% | 65.3% |

##### 5×4 cell p50 grid (eg_score %)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 48.4 (109) | 48.7 (99) | 50.8 (115) | 43.9 (19) |
| 1200 | 48.9 (138) | 48.7 (143) | 50.5 (144) | 50.5 (59) |
| 1600 | 48.9 (132) | 50.5 (144) | 52.3 (141) | 51.5 (84) |
| 2000 | 51.7 (127) | 52.9 (130) | 52.4 (125) | 51.1 (32) |
| 2400 | 51.5 (108) | 52.9 (95) | 52.1 (59) | — |

##### Collapse verdict

- TC axis: max |d| = (0.5177 − 0.5024) / sqrt((0.00682 + 0.00473)/2) ≈ **0.20** (rapid vs bullet) → **review** (borderline)
- ELO axis: max |d| = (0.5255 − 0.4941) / sqrt((0.00291 + 0.00823)/2) ≈ **0.42** (2400 vs 800) → **review**

##### Recommendations

- 800–1600 within ±1.1 pp of 50% game-time-bucketed — equal-footing filter passing for the well-sampled buckets. 2000/2400 ≈ +2 pp above (documented out-of-scope residual).
- Cohort neutral band = pooled `[p25, p75] = [46.1%, 55.5%]`. Live `[45%, 55%]` is within ~1 pp on both edges — **keep**.
- Cohort domain = `[38.8%, 64.0%]` vs live `[25%, 75%]` — live axis comfortably accommodates p05/p95.
- ELO d ≈ 0.42 sits in `review` zone: per-ELO stratification (mirroring `ENDGAME_SKILL_ZONES`) is worth considering if a UI argument warrants the split; otherwise pooled band remains defensible.

#### 3.1.5 Achievable Score Gap

##### Currently set in code

| Constant | Live value |
|---|---:|
| `achievable_score_gap` ZoneSpec | `(typical_lower=-0.04, typical_upper=+0.04)` |
| `PVALUE_RELIABILITY_MIN_N` | 10 |
| `EVAL_CLIP_MAX_CP` | 2000 |

##### Pooled distribution (proportions; pp rendering inline)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,299 | +0.3pp | 8.1pp | −13.3pp | −4.0pp | +0.6pp | +5.0pp | +13.0pp |

##### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 374 | −0.7pp | 9.3pp | −15.6pp | −5.9pp | −0.9pp | +4.4pp | +14.4pp |
| 1200 | 541 | −0.5pp | 8.0pp | −13.3pp | −4.6pp | −0.5pp | +3.9pp | +12.2pp |
| 1600 | 575 | +0.0pp | 7.9pp | −13.4pp | −3.9pp | +0.2pp | +4.4pp | +12.8pp |
| 2000 | 498 | +1.3pp | 7.8pp | −12.0pp | −2.8pp | +1.5pp | +6.1pp | +13.1pp |
| 2400 | 311 | +2.0pp | 6.9pp | −8.7pp | −2.3pp | +2.6pp | +6.4pp | +11.2pp |

##### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 675 | +0.2pp | 10.5pp | −18.9pp | −6.0pp | +0.7pp | +7.0pp | +16.1pp |
| blitz | 671 | +0.3pp | 7.2pp | −11.8pp | −4.1pp | +0.6pp | +4.9pp | +11.0pp |
| rapid | 663 | +0.8pp | 6.3pp | −9.5pp | −2.5pp | +0.8pp | +4.4pp | +10.9pp |
| classical | 290 | −0.4pp | 7.0pp | −12.2pp | −4.8pp | −0.6pp | +3.8pp | +10.9pp |

##### 5×4 cell p50 grid (pp)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | +0.9 (116) | −0.6 (105) | −0.9 (123) | −3.7 (30) |
| 1200 | +0.3 (149) | −0.3 (150) | −0.6 (155) | −1.3 (87) |
| 1600 | −0.4 (145) | −0.3 (161) | +0.7 (155) | +0.8 (114) |
| 2000 | +0.1 (146) | +3.2 (148) | +1.5 (145) | +0.5 (59) |
| 2400 | +2.8 (119) | +2.4 (107) | +3.0 (85) | — |

##### Collapse verdict

- TC axis: max |d| = (0.0080 − (−0.0040)) / sqrt((0.00394 + 0.00494)/2) ≈ **0.18** (rapid vs classical) → **collapse**
- ELO axis: max |d| = (0.0195 − (−0.0074)) / sqrt((0.00473 + 0.00864)/2) ≈ **0.33** (2400 vs 800) → **review**

##### Recommendations

- Pooled mean +0.3pp sits within engine-alignment tolerance.
- Cohort neutral band = pooled `[p25, p75] = [−4.0pp, +5.0pp]` → asymmetric round to live `(−4pp, +4pp)` is close; ELO bucket spread suggests retaining the per-ELO `PER_CLASS_GAUGE_ZONES.{class}.achievable_score_gap` stratification already in code (Phase 87.1 calibration retains).
- Domain = `[−13.3pp, +13.0pp]` — within reach of any gauge half-width up to 15pp.

#### 3.1.6 Endgame Score Gap and Timeline

##### Pooled distribution (eg − non_eg, pp)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,003 | −1.1pp | 13.1pp | −22.1pp | −10.1pp | −1.2pp | +7.8pp | +20.9pp |

##### ELO marginal (diff)

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 342 | −2.3pp | 14.1pp | −24.9pp | −11.8pp | −3.1pp | +6.2pp | +22.9pp |
| 1200 | 484 | −1.7pp | 13.6pp | −23.0pp | −10.8pp | −2.1pp | +7.4pp | +22.7pp |
| 1600 | 501 | −0.7pp | 13.5pp | −21.8pp | −9.2pp | −0.7pp | +8.8pp | +20.0pp |
| 2000 | 414 | −0.7pp | 11.9pp | −20.7pp | −8.6pp | −0.2pp | +7.9pp | +17.6pp |
| 2400 | 262 | +0.3pp | 11.7pp | −19.0pp | −7.1pp | +0.9pp | +8.1pp | +18.0pp |

##### TC marginal (diff)

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 614 | −1.0pp | 12.3pp | −19.0pp | −9.7pp | −1.9pp | +6.6pp | +20.9pp |
| blitz | 611 | −0.5pp | 12.3pp | −20.0pp | −9.3pp | −0.8pp | +8.1pp | +20.9pp |
| rapid | 584 | −0.8pp | 13.7pp | −26.0pp | −10.1pp | −0.3pp | +8.3pp | +21.5pp |
| classical | 194 | −4.2pp | 15.5pp | −31.4pp | −13.8pp | −3.4pp | +6.9pp | +20.0pp |

##### 5×4 cell p50 grid (diff, pp)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −3.5 (109) | −1.8 (99) | −3.0 (115) | −10.8 (19) |
| 1200 | −1.7 (138) | −3.0 (143) | +0.1 (144) | −8.2 (59) |
| 1600 | −3.1 (132) | −0.1 (144) | +0.6 (141) | −0.3 (84) |
| 2000 | −0.9 (127) | +0.2 (130) | −0.2 (125) | −1.8 (32) |
| 2400 | +2.4 (108) | +0.1 (95) | +1.0 (59) | — |

##### Collapse verdict

- TC axis: max |d| = (−0.0050 − (−0.0420)) / sqrt((0.01523 + 0.02402)/2) ≈ **0.26** (blitz vs classical) → **review**
- ELO axis: max |d| = (+0.0025 − (−0.0229)) / sqrt((0.01364 + 0.01985)/2) ≈ **0.20** (2400 vs 800) → **review** (borderline)

##### Recommendations

- Score-gap gauge neutral zone (live `SCORE_GAP_NEUTRAL_MIN/MAX` = ±10pp): pooled `[p25, p75] = [−10.1pp, +7.8pp]` → asymmetric but live ±10pp matches the negative edge exactly. Per memory `feedback_zone_band_judgement.md`: tightening to `±8pp` would surface meaningful deviations more loudly. Editorial decision; **keep ±10pp** unless UX argues for tighter band.
- Timeline overlay: eg ≈ non_eg medians within ~1pp pooled (50.7% vs 51.9%). Unified band `[max(eg_p25, non_eg_p25), min(eg_p75, non_eg_p75)] = [46.4%, 55.5%]` works.

### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery + Endgame Skill

##### Currently set in code

| Constant | Live value |
|---|---:|
| `FIXED_GAUGE_ZONES.conversion` | `[0.65, 0.75]` |
| `FIXED_GAUGE_ZONES.parity` | `[0.45, 0.55]` |
| `FIXED_GAUGE_ZONES.recovery` | `[0.25, 0.35]` |
| `ENDGAME_SKILL_ZONES` | per-ELO (see `endgame_zones.py`) |

##### Conversion — pooled

| n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 2,299 | 70.8% | 10.9% | 64.3% | 71.4% | 77.7% |

##### Conversion ELO marginal

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 374 | 67.8% | 11.1% | 61.0% | 69.4% | 75.5% |
| 1200 | 541 | 69.9% | 10.9% | 63.6% | 71.0% | 76.7% |
| 1600 | 575 | 71.4% | 10.7% | 65.3% | 71.6% | 78.3% |
| 2000 | 498 | 72.0% | 10.9% | 65.5% | 72.3% | 78.9% |
| 2400 | 311 | 73.2% | 10.0% | 67.8% | 72.8% | 78.5% |

##### Conversion TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 675 | 65.2% | 10.7% | 58.2% | 65.6% | 72.0% |
| blitz | 671 | 71.6% | 9.0% | 66.7% | 71.7% | 76.9% |
| rapid | 663 | 74.0% | 9.8% | 69.4% | 74.3% | 79.8% |
| classical | 290 | 74.9% | 12.3% | 67.3% | 75.0% | 82.6% |

##### Parity — pooled

| n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 2,295 | 50.6% | 12.9% | 43.8% | 50.0% | 57.1% |

##### Parity ELO marginal

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 370 | 48.7% | 18.0% | 38.7% | 50.0% | 57.6% |
| 1200 | 541 | 49.7% | 13.7% | 42.5% | 50.0% | 56.3% |
| 1600 | 575 | 50.4% | 11.8% | 42.5% | 50.0% | 57.1% |
| 2000 | 498 | 52.1% | 10.4% | 46.1% | 51.7% | 57.9% |
| 2400 | 311 | 52.1% | 9.0% | 46.5% | 52.1% | 57.3% |

##### Parity TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 673 | 50.4% | 12.9% | 43.3% | 50.0% | 57.1% |
| blitz | 671 | 50.4% | 11.2% | 44.2% | 50.7% | 56.7% |
| rapid | 663 | 51.4% | 12.2% | 45.2% | 50.6% | 57.1% |
| classical | 288 | 49.5% | 17.4% | 40.0% | 50.0% | 59.7% |

##### Recovery — pooled

| n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 2,298 | 30.8% | 11.0% | 23.8% | 30.0% | 37.0% |

##### Recovery ELO marginal

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 374 | 31.0% | 11.5% | 24.0% | 30.0% | 37.1% |
| 1200 | 540 | 30.2% | 10.7% | 23.3% | 29.9% | 36.5% |
| 1600 | 575 | 30.4% | 10.9% | 23.1% | 29.1% | 36.5% |
| 2000 | 498 | 30.9% | 11.6% | 23.3% | 30.4% | 38.4% |
| 2400 | 311 | 32.6% | 10.1% | 26.1% | 31.7% | 37.5% |

##### Recovery TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 675 | 35.6% | 9.9% | 29.7% | 35.2% | 41.1% |
| blitz | 671 | 30.6% | 9.8% | 24.7% | 30.0% | 35.9% |
| rapid | 662 | 28.5% | 10.2% | 22.2% | 27.4% | 33.3% |
| classical | 290 | 25.5% | 13.5% | 17.0% | 23.1% | 32.1% |

##### Endgame Skill — pooled

| n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 2,299 | 50.8% | 8.0% | 46.3% | 50.9% | 55.2% |

##### Endgame Skill ELO marginal

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 374 | 49.2% | 9.1% | 44.2% | 49.6% | 54.5% |
| 1200 | 541 | 50.0% | 7.6% | 45.6% | 49.8% | 53.8% |
| 1600 | 575 | 50.7% | 8.0% | 46.2% | 50.8% | 55.0% |
| 2000 | 498 | 51.6% | 7.8% | 47.0% | 51.5% | 56.3% |
| 2400 | 311 | 52.6% | 7.0% | 48.3% | 52.7% | 56.5% |

##### Endgame Skill TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 675 | 50.4% | 8.3% | 45.3% | 50.3% | 55.4% |
| blitz | 671 | 50.9% | 7.3% | 46.7% | 51.0% | 55.3% |
| rapid | 663 | 51.3% | 7.6% | 47.6% | 51.4% | 54.9% |
| classical | 290 | 49.9% | 9.4% | 44.4% | 49.7% | 54.8% |

##### 5×4 cell p50 grid — Endgame Skill

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 49.3 (116) | 50.5 (105) | 49.6 (123) | 44.3 (30) |
| 1200 | 49.1 (149) | 49.6 (150) | 51.0 (155) | 49.1 (87) |
| 1600 | 50.2 (145) | 50.2 (161) | 51.3 (155) | 51.7 (114) |
| 2000 | 50.5 (146) | 53.1 (148) | 51.5 (145) | 49.9 (59) |
| 2400 | 52.5 (119) | 52.8 (107) | 53.4 (85) | — |

##### Collapse verdicts

| Metric | TC max\|d\| (pair) | TC verdict | ELO max\|d\| (pair) | ELO verdict |
|---|---:|---|---:|---|
| Conversion | (0.7490 − 0.6518)/sqrt((0.0152+0.0114)/2) ≈ **0.84** (classical vs bullet) | keep | (0.7320 − 0.6785)/sqrt((0.0101+0.0122)/2) ≈ **0.51** (2400 vs 800) | keep |
| Parity | (0.5137 − 0.4953)/sqrt((0.01485+0.03037)/2) ≈ **0.12** (rapid vs classical) | collapse | (0.5209 − 0.4871)/sqrt((0.00801+0.03238)/2) ≈ **0.24** (2400 vs 800) | review |
| Recovery | (0.3563 − 0.2546)/sqrt((0.00986+0.01830)/2) ≈ **0.86** (bullet vs classical) | keep | (0.3257 − 0.3019)/sqrt((0.01020+0.01147)/2) ≈ **0.16** (2400 vs 1200) | collapse |
| Endgame Skill | (0.5133 − 0.4994)/sqrt((0.00580+0.00893)/2) ≈ **0.16** (rapid vs classical) | collapse | (0.5262 − 0.4919)/sqrt((0.00482+0.00822)/2) ≈ **0.42** (2400 vs 800) | review |

##### Recommendations

- Conversion live `[0.65, 0.75]` vs pooled `[0.643, 0.777]` — within 3 pp; gauge is calibrated. TC verdict says split; existing `FIXED_GAUGE_ZONES` may benefit from per-TC override if UI argument warrants.
- Parity live `[0.45, 0.55]` vs pooled `[0.438, 0.571]` — slightly wider on the upper edge; **keep** or widen p75 to `0.57`.
- Recovery live `[0.25, 0.35]` vs pooled `[0.238, 0.370]` — close; TC verdict says split (bullet 35.2% median vs classical 23.1%); per-TC override is the right move if/when this is revisited.
- Endgame Skill live per-ELO bands (`ENDGAME_SKILL_ZONES`) capture the ELO drift; keep.

#### 3.2.2 Per-bucket ΔES Score Gap (Section 2)

##### Currently set in code

| Constant | Live value |
|---|---:|
| `section2_score_gap_conv` ZoneSpec | `(typical_lower=-0.11, typical_upper=0.00)` |
| `section2_score_gap_parity` ZoneSpec | `(typical_lower=-0.04, typical_upper=+0.04)` |
| `section2_score_gap_recov` ZoneSpec | `(typical_lower=+0.01, typical_upper=+0.11)` |

##### Conversion bucket — pooled / marginals

| Scope | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pooled | 2,060 | −6.4pp | 9.6pp | −24.8pp | −11.3pp | −5.0pp | +0.1pp | +6.8pp |
| TC bullet | 637 | −13.2pp | 10.3pp | −31.2pp | −19.9pp | −11.7pp | −5.4pp | +1.0pp |
| TC blitz | 623 | −4.6pp | 7.7pp | −17.5pp | −8.5pp | −4.1pp | +0.2pp | +6.6pp |
| TC rapid | 600 | −2.5pp | 7.0pp | −14.9pp | −6.2pp | −1.9pp | +2.1pp | +7.9pp |
| TC classical | 200 | −1.8pp | 7.5pp | −14.0pp | −6.2pp | −1.2pp | +3.8pp | +8.2pp |
| ELO 800 | 336 | −13.2pp | 10.1pp | −34.1pp | −18.1pp | −10.9pp | −6.6pp | −0.4pp |
| ELO 1200 | 494 | −8.6pp | 9.1pp | −26.8pp | −12.8pp | −6.5pp | −2.4pp | +2.9pp |
| ELO 1600 | 514 | −5.4pp | 8.7pp | −22.5pp | −10.4pp | −4.1pp | +0.8pp | +5.9pp |
| ELO 2000 | 435 | −2.9pp | 8.6pp | −20.2pp | −6.6pp | −1.5pp | +3.3pp | +8.8pp |
| ELO 2400 | 281 | −1.3pp | 6.7pp | −12.9pp | −5.1pp | −1.3pp | +3.1pp | +9.2pp |

##### Parity bucket — pooled / marginals

| Scope | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pooled | 1,804 | +0.1pp | 6.5pp | −10.6pp | −3.6pp | +0.4pp | +4.1pp | +10.1pp |
| TC bullet | 555 | −0.2pp | 7.0pp | −11.6pp | −4.0pp | −0.1pp | +4.0pp | +10.1pp |
| TC blitz | 577 | +0.3pp | 6.2pp | −10.4pp | −3.3pp | +0.7pp | +4.2pp | +9.3pp |
| TC rapid | 523 | +0.6pp | 6.3pp | −9.7pp | −3.3pp | +0.7pp | +4.1pp | +11.1pp |
| TC classical | 149 | −1.0pp | 6.5pp | −12.0pp | −5.4pp | −0.7pp | +2.7pp | +8.4pp |
| ELO 800 | 211 | −0.7pp | 7.8pp | −15.5pp | −4.6pp | +0.1pp | +4.5pp | +10.8pp |
| ELO 1200 | 399 | −0.6pp | 6.6pp | −11.5pp | −4.5pp | −0.6pp | +3.1pp | +9.2pp |
| ELO 1600 | 469 | −0.4pp | 6.8pp | −10.8pp | −4.5pp | −0.2pp | +3.8pp | +9.6pp |
| ELO 2000 | 434 | +1.0pp | 5.9pp | −8.2pp | −2.1pp | +0.8pp | +4.5pp | +10.7pp |
| ELO 2400 | 291 | +1.3pp | 5.5pp | −7.5pp | −1.9pp | +1.4pp | +4.7pp | +9.3pp |

##### Recovery bucket — pooled / marginals

| Scope | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pooled | 1,977 | +6.4pp | 8.0pp | −4.7pp | +0.8pp | +5.6pp | +11.0pp | +20.6pp |
| TC bullet | 627 | +12.8pp | 8.1pp | +0.1pp | +7.7pp | +12.1pp | +17.6pp | +26.4pp |
| TC blitz | 601 | +5.0pp | 5.9pp | −3.8pp | +0.8pp | +4.8pp | +8.3pp | +14.8pp |
| TC rapid | 560 | +2.8pp | 5.6pp | −5.8pp | −0.8pp | +2.6pp | +6.2pp | +11.9pp |
| TC classical | 189 | +0.7pp | 5.6pp | −6.7pp | −3.7pp | +0.5pp | +4.6pp | +9.8pp |
| ELO 800 | 329 | +11.5pp | 8.8pp | +0.8pp | +5.9pp | +9.4pp | +15.6pp | +28.3pp |
| ELO 1200 | 470 | +7.8pp | 7.8pp | −3.9pp | +3.0pp | +6.7pp | +11.9pp | +22.1pp |
| ELO 1600 | 493 | +4.9pp | 7.2pp | −4.8pp | 0.0pp | +3.5pp | +9.0pp | +18.3pp |
| ELO 2000 | 412 | +4.1pp | 7.5pp | −6.4pp | −1.5pp | +3.2pp | +9.5pp | +17.4pp |
| ELO 2400 | 273 | +4.2pp | 6.1pp | −4.6pp | −0.3pp | +4.0pp | +8.3pp | +14.6pp |

##### Skill aggregate (equal-weighted mean of bucket means with n≥10) — pooled / marginals

| Scope | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pooled | 2,253 | +0.1pp | 5.3pp | −8.8pp | −3.0pp | +0.4pp | +3.1pp | +8.4pp |
| TC bullet | 663 | −0.1pp | 6.0pp | −10.6pp | −3.8pp | +0.2pp | +3.5pp | +9.1pp |
| TC blitz | 663 | +0.2pp | 5.0pp | −7.9pp | −2.8pp | +0.5pp | +3.4pp | +8.2pp |
| TC rapid | 654 | +0.4pp | 4.9pp | −7.6pp | −1.9pp | +0.6pp | +2.9pp | +8.1pp |
| TC classical | 273 | −0.6pp | 5.2pp | −8.9pp | −3.5pp | −0.6pp | +2.5pp | +8.6pp |
| ELO 800 | 359 | −1.1pp | 6.0pp | −10.4pp | −4.8pp | −0.5pp | +2.8pp | +7.8pp |
| ELO 1200 | 519 | −0.7pp | 5.1pp | −9.0pp | −3.5pp | −0.6pp | +2.0pp | +7.7pp |
| ELO 1600 | 573 | 0.0pp | 5.4pp | −8.7pp | −3.2pp | +0.2pp | +2.9pp | +9.1pp |
| ELO 2000 | 493 | +0.9pp | 5.0pp | −7.8pp | −1.7pp | +0.8pp | +4.2pp | +8.8pp |
| ELO 2400 | 309 | +1.5pp | 4.3pp | −5.6pp | −1.3pp | +1.9pp | +4.3pp | +8.3pp |

##### Collapse verdicts (per bucket)

| Bucket | TC max\|d\| (pair) | TC verdict | ELO max\|d\| (pair) | ELO verdict |
|---|---:|---|---:|---|
| Conversion | (−0.0179 − (−0.1317))/sqrt((0.00559+0.01065)/2) ≈ **1.26** (classical vs bullet) | keep | (−0.0131 − (−0.1322))/sqrt((0.00442+0.01012)/2) ≈ **1.40** (2400 vs 800) | keep |
| Parity | (0.0060 − (−0.0104))/sqrt((0.00400+0.00427)/2) ≈ **0.18** (rapid vs classical) | collapse | (0.0127 − (−0.0071))/sqrt((0.00300+0.00608)/2) ≈ **0.29** (2400 vs 800) | review |
| Recovery | (0.1281 − 0.0066)/sqrt((0.00658+0.00314)/2) ≈ **1.74** (bullet vs classical) | keep | (0.1148 − 0.0413)/sqrt((0.00770+0.00562)/2) ≈ **0.90** (800 vs 2000) | keep |
| Skill | (0.0044 − (−0.0055))/sqrt((0.00236+0.00273)/2) ≈ **0.14** (rapid vs classical) | collapse | (0.0153 − (−0.0108))/sqrt((0.00183+0.00364)/2) ≈ **0.35** (2400 vs 800) | review |

##### Sigmoid-bias check

- Conv pooled mean **−6.4pp** (negative) ✅
- Parity pooled mean **+0.1pp** (~0) ✅
- Recov pooled mean **+6.4pp** (positive) ✅

Expected asymmetry confirmed: conv compressed by upside ceiling at ES_entry≈0.6, recov compressed by downside floor at ES_entry≈0.4. Per-bucket bands are the right output.

##### Recommendations

- **Conv** pooled `[p25, p75] = [−11.3pp, +0.1pp]`. Live `(-0.11, 0.00)` matches. **Keep**.
- **Parity** pooled `[−3.6pp, +4.1pp]`. Live `(-0.04, +0.04)` ≈ within 0.5pp. **Keep**.
- **Recov** pooled `[+0.8pp, +11.0pp]`. Live `(+0.01, +0.11)` matches. **Keep**.
- ELO-axis Recovery `d = 0.90` (keep separate): the live scalar registry stays, but per-ELO stratification is the leading candidate when/if Section 2 stratification revisits.

#### 3.2.3 Rate vs. score-gap divergence (cross-cut)

| Metric | ELO sweep (raw rate) | ELO d / verdict | TC sweep (raw rate) | TC d / verdict | ELO sweep (gap) | ELO d / verdict | TC sweep (gap) | TC d / verdict |
|---|---|---:|---|---:|---|---:|---|---:|
| Conversion | 67.8% → 73.2% | 0.51 keep | 65.2% → 74.9% | 0.84 keep | −13.2 → −1.3pp | 1.40 keep | −13.2 → −1.8pp | 1.26 keep |
| Recovery | 31.0% → 32.6% | 0.16 collapse | 35.6% → 25.5% | 0.86 keep | +11.5 → +4.2pp | 0.90 keep | +12.8 → +0.7pp | 1.74 keep |

##### Divergence callout

- **Recovery ELO-axis divergence**: the raw recovery rate collapses across ELO (d ≈ 0.16) — weak and strong players win/draw roughly the same fraction of disadvantaged endgames. The recovery **gap** re-exposes the ELO signal (d ≈ 0.90): weak players outperform the engine expected score by **+11.5pp** (entering at ≈0.4 expected, recovering to ≈0.51), while strong players overshoot by only **+4.2pp**. The raw rate masks this because the engine expectation rises with the cohort.
- **Conversion**: both axes agree — raw rate and gap both `keep separate`. No divergence; ELO and TC both meaningful for the conversion narrative.

##### Implication

- The recovery-gap ELO `keep separate` (d = 0.90) is the strongest argument against §3.2.2's scalar-registry deferral. Recommendation **unchanged for this phase** (scalar pooled band ships); flag recovery as the first candidate when per-(TC × ELO) stratification of Section 2 buckets is revisited.

### 3.3 Time Pressure

#### 3.3.1 Clock pressure at endgame entry

##### Currently set in code

| Constant | Live value |
|---|---:|
| `NEUTRAL_PCT_THRESHOLD` | ±5.0 pp |
| `NEUTRAL_TIMEOUT_THRESHOLD` | ±5.0 pp |
| `clock_gap_pct` placeholder | `(-0.05, 0.05)` |

##### Clock-diff % of base time — pooled

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,291 | −1.3% | 10.3% | −18.8% | −6.7% | −0.5% | +4.8% | +13.7% |

##### Clock-diff ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 371 | −0.8% | 9.8% | −16.9% | −5.9% | −0.1% | +5.2% | +13.6% |
| 1200 | 540 | −1.4% | 10.9% | −20.0% | −6.9% | −0.4% | +5.4% | +15.4% |
| 1600 | 574 | −2.2% | 11.2% | −21.0% | −8.2% | −1.3% | +4.7% | +14.7% |
| 2000 | 496 | −1.0% | 10.3% | −16.9% | −6.8% | −0.6% | +4.7% | +13.7% |
| 2400 | 310 | −0.4% | 7.0% | −11.4% | −4.8% | −0.5% | +3.8% | +11.1% |

##### Clock-diff TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 672 | −0.3% | 6.0% | −9.3% | −4.1% | −0.5% | +3.0% | +9.3% |
| blitz | 671 | −1.2% | 9.9% | −18.5% | −7.5% | −0.4% | +5.1% | +13.5% |
| rapid | 663 | −1.6% | 10.0% | −18.8% | −8.5% | −0.7% | +5.5% | +12.7% |
| classical | 285 | −3.1% | 17.1% | −32.5% | −12.9% | −2.0% | +7.0% | +20.6% |

##### Net timeout — pooled

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,291 | +0.3% | 11.8% | −21.3% | −4.4% | +1.1% | +6.1% | +18.1% |

##### Net timeout ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 371 | −1.1% | 12.8% | −23.3% | −6.1% | 0.0% | +4.7% | +17.6% |
| 1200 | 540 | −0.3% | 10.7% | −20.8% | −4.0% | +0.5% | +4.6% | +14.8% |
| 1600 | 574 | 0.0% | 11.6% | −22.4% | −3.8% | +1.3% | +5.4% | +17.0% |
| 2000 | 496 | +1.2% | 12.4% | −20.5% | −4.7% | +1.8% | +8.7% | +19.3% |
| 2400 | 310 | +2.1% | 11.1% | −19.2% | −3.8% | +2.7% | +9.2% | +18.2% |

##### Net timeout TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 672 | +0.4% | 16.4% | −27.0% | −11.9% | +0.6% | +11.8% | +25.9% |
| blitz | 671 | +0.4% | 11.6% | −22.1% | −6.0% | +1.9% | +8.6% | +16.3% |
| rapid | 663 | +0.4% | 7.3% | −12.0% | −1.9% | +1.7% | +4.0% | +8.9% |
| classical | 285 | −0.3% | 5.7% | −6.8% | 0.0% | 0.0% | +1.9% | +4.8% |

##### Clock-gap fraction (`(user_clk − opp_clk) / base_clock`) — pooled

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,291 | −0.013 | 0.103 | −0.188 | −0.067 | −0.005 | +0.048 | +0.137 |

##### Clock-gap TC marginal

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 672 | −0.003 | 0.060 | −0.041 | −0.005 | +0.030 |
| blitz | 671 | −0.012 | 0.099 | −0.075 | −0.004 | +0.051 |
| rapid | 663 | −0.016 | 0.100 | −0.085 | −0.007 | +0.055 |
| classical | 285 | −0.031 | 0.171 | −0.129 | −0.020 | +0.070 |

##### 5×4 cell p50 grid — clock-diff %

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | −0.30 (115) | −0.37 (105) | −0.08 (123) | +0.62 (28) |
| 1200 | −0.36 (149) | −1.20 (150) | −0.24 (155) | +0.64 (86) |
| 1600 | −1.07 (144) | −1.09 (161) | −0.66 (155) | −3.91 (114) |
| 2000 | −1.34 (146) | +0.36 (148) | −0.60 (145) | −4.22 (57) |
| 2400 | −0.07 (118) | −0.16 (107) | −2.39 (85) | — |

##### 5×4 cell p50 grid — net timeout %

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 0.00 (115) | +0.47 (105) | +0.65 (123) | 0.00 (28) |
| 1200 | 0.00 (149) | +2.04 (150) | +1.27 (155) | 0.00 (86) |
| 1600 | −0.08 (144) | +1.16 (161) | +2.12 (155) | +0.58 (114) |
| 2000 | +2.09 (146) | +4.61 (148) | +1.96 (145) | 0.00 (57) |
| 2400 | +5.29 (118) | +0.96 (107) | +2.17 (85) | — |

##### Collapse verdicts

| Metric | TC max\|d\| (pair) | TC verdict | ELO max\|d\| (pair) | ELO verdict |
|---|---:|---|---:|---|
| Clock-diff % | (−0.29 − (−3.05))/sqrt((36.0+292.8)/2) ≈ **0.22** (bullet vs classical) | review | (−2.16 − (−0.43))/sqrt((126.4+49.0)/2) ≈ **0.18** (1600 vs 2400) | collapse |
| Net timeout % | (0.38 − (−0.33))/sqrt((135.5+32.1)/2) ≈ **0.08** (blitz vs classical) | collapse | (2.08 − (−1.06))/sqrt((123.6+163.8)/2) ≈ **0.19** (2400 vs 800) | collapse |
| Clock-gap frac | (−0.003 − (−0.031))/sqrt((0.0036+0.0293)/2) ≈ **0.22** (bullet vs classical) | review | (−0.022 − (−0.004))/sqrt((0.0126+0.0049)/2) ≈ **0.19** (1600 vs 2400) | collapse |

##### Recommendations

- Clock-diff: pooled IQR `[−6.7, +4.8]%` ≈ asymmetric. Live `NEUTRAL_PCT_THRESHOLD = ±5%` lands inside; per-TC d = 0.22 (`review`) driven by classical's larger spread. **Keep** single band.
- Net timeout: pooled IQR `[−4.4, +6.1]%`. Live `NEUTRAL_TIMEOUT_THRESHOLD = ±5%` is close. **Keep**.
- Clock-gap fraction (placeholder `(-0.05, +0.05)`): pooled IQR `[−0.067, +0.048]`. Asymmetric — bound to **`(−0.067, +0.048)`** as the calibrated single band, or round symmetric to `±0.06`.

#### 3.3.2 Time pressure vs performance

##### Pressure-vs-score curves (per-bucket per-cell — TC marginal sample for headline)

| time bucket | bullet score (n) | blitz score (n) | rapid score (n) | classical score (n) |
|---:|---:|---:|---:|---:|
| 0 (0–10%) | 0.262 (15,175) | 0.330 (14,740) | 0.328 (5,675) | 0.408 (1,396) |
| 1 (10–20%) | 0.396 (25,326) | 0.435 (16,574) | 0.439 (5,960) | 0.451 (948) |
| 2 (20–30%) | 0.493 (27,166) | 0.490 (17,613) | 0.466 (7,524) | 0.458 (1,131) |
| 3 (30–40%) | 0.530 (30,678) | 0.519 (20,946) | 0.510 (9,845) | 0.470 (1,331) |
| 4 (40–50%) | 0.551 (31,357) | 0.535 (24,178) | 0.531 (12,650) | 0.477 (1,604) |
| 5 (50–60%) | 0.565 (29,106) | 0.553 (26,800) | 0.534 (16,528) | 0.487 (2,009) |
| 6 (60–70%) | 0.566 (23,267) | 0.547 (26,738) | 0.532 (21,100) | 0.499 (2,565) |
| 7 (70–80%) | 0.554 (14,672) | 0.554 (21,853) | 0.529 (24,148) | 0.501 (3,185) |
| 8 (80–90%) | 0.553 (5,843) | 0.535 (12,351) | 0.534 (19,432) | 0.487 (3,759) |
| 9 (90%+) | 0.515 (1,234) | 0.527 (4,760) | 0.524 (9,460) | 0.491 (9,887) |

##### Verdict (per-bucket pooled max |d|)

- TC axis: differences strongest at time_bucket 0 (max 0.408 classical vs 0.262 bullet ≈ 17 pp at population level). On per-game variance ≈ 0.2, d ≈ (0.41−0.26)/sqrt(0.2) ≈ **0.32** → **review**. Other buckets agree more closely; pooled across buckets verdict = **review**.
- ELO axis: at time_bucket 0 the spread is 0.34 (800) → 0.42 (2400) ≈ 8 pp → d ≈ **0.18** → **collapse**. At buckets 3–7 the spread compresses further → **collapse** across all.

##### Recommendations

- Time-pressure curves clearly stratify by TC at extreme low-clock buckets (Q0/Q1). Per-TC overlay is justified for the chart — and is already the live UI design.
- ELO axis collapses; pooling across ELO buckets within a TC is defensible.

#### §3.3.3 Chess score per pressure bin (quintiles)

##### Per-quintile per-axis distributions (pooled within axis)

| Quintile | TC | n_users | mean | p25 | p50 | p75 |
|---:|---|---:|---:|---:|---:|---:|
| 0 | bullet | 651 | 35.2% | 28.1% | 34.5% | 42.0% |
| 0 | blitz | 615 | 39.3% | 30.6% | 38.8% | 48.3% |
| 0 | rapid | 416 | 40.4% | 29.3% | 40.0% | 50.0% |
| 0 | classical | 94 | 43.1% | 33.3% | 41.8% | 54.1% |
| 1 | bullet | 684 | 52.0% | 46.0% | 51.1% | 57.7% |
| 1 | blitz | 644 | 52.0% | 45.0% | 51.1% | 58.5% |
| 1 | rapid | 552 | 49.9% | 41.0% | 50.0% | 58.0% |
| 1 | classical | 126 | 47.9% | 35.9% | 50.0% | 59.1% |
| 2 | bullet | 679 | 56.6% | 50.8% | 56.0% | 61.8% |
| 2 | blitz | 660 | 55.2% | 48.9% | 55.0% | 61.9% |
| 2 | rapid | 638 | 54.9% | 46.7% | 54.2% | 62.5% |
| 2 | classical | 170 | 50.3% | 38.9% | 50.0% | 60.0% |
| 3 | bullet | 639 | 56.3% | 50.0% | 56.4% | 62.9% |
| 3 | blitz | 661 | 55.8% | 49.5% | 55.7% | 62.0% |
| 3 | rapid | 673 | 54.5% | 47.7% | 53.8% | 60.8% |
| 3 | classical | 241 | 51.8% | 40.9% | 50.0% | 61.1% |
| 4 | bullet | 338 | 55.2% | 43.8% | 53.9% | 65.0% |
| 4 | blitz | 527 | 54.2% | 45.4% | 54.9% | 62.5% |
| 4 | rapid | 582 | 53.3% | 45.5% | 53.1% | 61.8% |
| 4 | classical | 376 | 52.1% | 41.6% | 51.3% | 62.4% |

##### Per-quintile collapse verdicts

| Quintile | TC max\|d\| (pair) | TC verdict | ELO max\|d\| (pair) | ELO verdict |
|---:|---:|---|---:|---|
| 0 | (0.431 − 0.352)/sqrt((0.0358+0.0131)/2) ≈ **0.51** (classical vs bullet) | keep | (0.415 − 0.340)/sqrt((0.0136+0.0201)/2) ≈ **0.58** (2400 vs 800) | keep |
| 1 | (0.520 − 0.479)/sqrt((0.0113+0.0354)/2) ≈ **0.27** (bullet vs classical) | review | (0.525 − 0.497)/sqrt((0.0079+0.0213)/2) ≈ **0.23** (2400 vs 800) | review |
| 2 | (0.566 − 0.503)/sqrt((0.0106+0.0308)/2) ≈ **0.44** (bullet vs classical) | review | (0.567 − 0.538)/sqrt((0.0083+0.0174)/2) ≈ **0.26** (2400 vs 1200) | review |
| 3 | (0.563 − 0.518)/sqrt((0.0136+0.0277)/2) ≈ **0.31** (bullet vs classical) | review | (0.573 − 0.530)/sqrt((0.0087+0.0140)/2) ≈ **0.40** (2400 vs 1200) | review |
| 4 | (0.552 − 0.521)/sqrt((0.0272+0.0284)/2) ≈ **0.18** (bullet vs classical) | collapse | (0.570 − 0.511)/sqrt((0.0241+0.0273)/2) ≈ **0.26** (2400 vs 800) | review |

##### Recommendations

- Quintile 0 (max pressure) is the only quintile where both axes clearly `keep separate` — per-TC and per-ELO stratification justified here.
- Quintiles 1–3 land in `review` on both axes — single global band per quintile is defensible but tight.
- Quintile 4 (relaxed clock) collapses on TC; ELO `review`.
- Live `PRESSURE_BIN_NEUTRAL_CAP = 0.06` — most quintile IQR half-widths sit within ±6 pp of the median, so the cap rarely binds.

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

##### Currently set in code

| Constant | Live value |
|---|---|
| `SCORE_BULLET_NEUTRAL_*` (shared) | `[−0.05, +0.05]` |
| `PER_CLASS_GAUGE_ZONES.*.conversion / .recovery` | per-class IQR-derived (existing) |
| `PER_CLASS_GAUGE_ZONES.*.achievable_score_gap` | rook `(−0.05, +0.05)`, minor `(−0.04, +0.06)`, pawn `(−0.04, +0.05)`, queen `(−0.04, +0.05)`, mixed `(−0.03, +0.04)`, pawnless `(−0.04, +0.04)` |

##### Pooled-by-class (across-population rates)

| class | games | users | score | score_diff | conv (n_games) | recov (n_games) |
|---|---:|---:|---:|---:|---:|---:|
| rook | 93,866 | 1,847 | 50.8% | +1.5pp | 71.0% (32,493) | 29.6% (30,729) |
| minor_piece | 70,251 | 1,826 | 51.0% | +2.1pp | 69.5% (23,928) | 32.7% (23,177) |
| pawn | 37,395 | 1,751 | 51.1% | +2.1pp | 73.8% (14,604) | 27.5% (13,894) |
| queen | 34,294 | 1,760 | 50.8% | +1.6pp | 77.5% (14,353) | 23.4% (13,721) |
| mixed | 527,830 | 1,893 | 50.6% | +1.1pp | 69.4% (203,511) | 31.1% (198,379) |
| pawnless | 5,784 | 1,362 | 50.7% | +1.4pp | 79.2% (2,484) | 19.7% (2,335) |

##### Per-user per-class chess-score IQR (pooled by class)

| class | n_users | mean | p10 | p25 | p50 | p75 | p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| rook | 1,840 | 50.4% | 36.6% | 43.3% | 50.0% | 57.5% | 64.3% |
| minor_piece | 1,616 | 50.4% | 34.6% | 43.0% | 50.0% | 58.3% | 65.9% |
| pawn | 1,205 | 50.4% | 34.0% | 42.3% | 50.0% | 59.1% | 66.7% |
| queen | 1,183 | 51.1% | 31.0% | 40.6% | 51.3% | 62.1% | 70.0% |
| mixed | 2,520 | 51.7% | 40.5% | 45.8% | 51.2% | 57.1% | 63.2% |
| pawnless | 91 | 44.2% | 25.0% | 30.0% | 40.9% | 54.6% | 70.0% |

##### Collapse verdicts per class (chess-score user-level)

| class | TC max\|d\| (pair) | TC verdict | ELO max\|d\| (pair) | ELO verdict |
|---|---:|---|---:|---|
| rook | (0.5147 − 0.4826)/sqrt((0.01326+0.01912)/2) ≈ **0.18** (rapid vs classical) | collapse | (0.5174 − 0.4892)/sqrt((0.00763+0.01576)/2) ≈ **0.26** (2400 vs 800) | review |
| minor_piece | (0.5126 − 0.4879)/sqrt((0.01412+0.02193)/2) ≈ **0.18** (blitz vs classical) | collapse | (0.5301 − 0.4835)/sqrt((0.00869+0.02024)/2) ≈ **0.39** (2400 vs 1200) | review |
| pawn | (0.5118 − 0.4937)/sqrt((0.01492+0.03363)/2) ≈ **0.12** (blitz vs classical) | collapse | (0.5164 − 0.4806)/sqrt((0.01382+0.01784)/2) ≈ **0.28** (2400 vs 1200) | review |
| queen | (0.5145 − 0.5067)/sqrt((0.02673+0.01907)/2) ≈ **0.05** (rapid vs bullet) | collapse | (0.5195 − 0.4954)/sqrt((0.01710+0.03112)/2) ≈ **0.16** (2000 vs 1200) | collapse |
| mixed | (0.5270 − 0.5060)/sqrt((0.01111+0.00656)/2) ≈ **0.31** (rapid vs bullet) | review | (0.5330 − 0.4996)/sqrt((0.00905+0.01115)/2) ≈ **0.33** (2000 vs 800) | review |
| pawnless | TC sample too thin for d | n/a | ELO sample too thin | n/a |

##### Recommendations

- Per-class chess-score `[p25, p75]` clusters around `[42–46%, 57–59%]`, all within ~1 pp of the global `[0.45, 0.55]` midpoint. Queen p25/p75 spread `[40.6%, 62.1%]` is the widest (extreme outcomes more common).
- Live global `SCORE_BULLET_NEUTRAL_MIN/MAX = [-0.05, +0.05]`: per-class drift is small enough that the global band remains population-honest for rook/minor/pawn/mixed. Queen and pawnless are wider — per-class override could improve sensitivity if UI argues for it.
- ELO axis on mixed `review` (d ≈ 0.33) — strongest case for per-class × per-ELO bands, but still inside `review` so single-axis pooling defensible.

#### 3.4.2 Per-span Score Gap by endgame type

##### Pooled by class

| class | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| rook | 1,401 | −0.6pp | −14.3pp | −5.1pp | +0.0pp | +4.6pp | +11.7pp |
| minor_piece | 1,151 | +0.3pp | −13.9pp | −4.5pp | +0.4pp | +5.6pp | +14.1pp |
| pawn | 716 | +0.4pp | −11.4pp | −4.0pp | +0.5pp | +4.9pp | +10.4pp |
| queen | 656 | +0.1pp | −12.5pp | −4.2pp | +0.4pp | +5.4pp | +11.2pp |
| mixed | 2,283 | +0.2pp | −10.4pp | −3.2pp | +0.4pp | +3.8pp | +10.3pp |
| pawnless | 4 | +1.9pp | +0.4pp | +0.7pp | +1.1pp | +2.3pp | +4.5pp |

##### Collapse verdicts per class (ΔES per-span gap)

| class | TC max\|d\| (pair) | TC verdict | ELO max\|d\| (pair) | ELO verdict |
|---|---:|---|---:|---|
| rook | (0.0010 − (−0.0124))/sqrt((0.00419+0.01062)/2) ≈ **0.16** (rapid vs bullet) | collapse | (0.0014 − (−0.0118))/sqrt((0.00539+0.00738)/2) ≈ **0.17** (2400 vs 1600) | collapse |
| minor_piece | (0.0069 − (−0.0078))/sqrt((0.00468+0.00557)/2) ≈ **0.15** (rapid vs blitz) | collapse | (0.0211 − (−0.0071))/sqrt((0.00498+0.00796)/2) ≈ **0.35** (2400 vs 1200) | review |
| pawn | (0.0091 − (−0.0031))/sqrt((0.00640+0.00455)/2) ≈ **0.16** (bullet vs blitz, after dropping ec=3) | collapse | (0.0116 − (−0.0099))/sqrt((0.00445+0.00330)/2) ≈ **0.27** (2400 vs 800) | review |
| queen | (0.0085 − (−0.0133))/sqrt((0.00717+0.00184)/2) ≈ **0.34** (bullet vs classical) | review | (0.0267 − (−0.0045))/sqrt((0.00396+0.00491)/2) ≈ **0.47** (800 vs 1200) | review |
| mixed | (0.0043 − (−0.0045))/sqrt((0.00245+0.00366)/2) ≈ **0.11** (rapid vs classical) | collapse | (0.0158 − (−0.0051))/sqrt((0.00215+0.00676)/2) ≈ **0.31** (2400 vs 800) | review |
| pawnless | n too small | n/a | n too small | n/a |

##### Recommendations

- Per-class pooled `[p25, p75]` clusters around `[−4pp, +5pp]`, matching live `PER_CLASS_GAUGE_ZONES.*.achievable_score_gap` bands (±4-5pp). **Keep** existing per-class bands.
- Global `ZONE_REGISTRY["endgame_type_achievable_score_gap"]` (live `(-0.04, +0.04)`): pooled-across-classes IQR `[−4pp, +5pp]` — keep, optionally tighten to symmetric `±5pp` if/when UI is retuned.
- ELO `review` for minor/pawn/queen/mixed: weak players outperform engine by more than strong players (consistent with §3.2.3 recovery-gap finding); per-class × per-ELO stratification is the leading candidate for the next calibration pass.

#### 3.4.3 Score vs Score Gap — agreement / redundancy

##### Per-class redundancy table

| class | n_users | pearson r | sign_agreement | zone_strict_agreement | strong_disagreement | score_stdev | gap_stdev |
|---|---:|---:|---:|---:|---:|---:|---:|
| rook | 1,401 | 0.603 | 68.6% | 57.8% | 2.9% | 0.098 | 0.083 |
| minor_piece | 1,151 | 0.602 | 71.2% | 56.4% | 2.0% | 0.104 | 0.086 |
| pawn | 716 | 0.541 | 69.4% | 54.3% | 2.5% | 0.110 | 0.067 |
| queen | 656 | 0.220 | 55.8% | 41.9% | 7.6% | 0.143 | 0.076 |
| mixed | 2,283 | 0.486 | 64.7% | 53.4% | 4.5% | 0.087 | 0.064 |

##### Per-class IQR band edges

| class | score_p25 | score_p75 | gap_p25 | gap_p75 |
|---|---:|---:|---:|---:|
| rook | 44.1% | 56.8% | −5.1pp | +4.6pp |
| minor_piece | 44.2% | 57.7% | −4.5pp | +5.6pp |
| pawn | 44.2% | 59.1% | −4.0pp | +4.9pp |
| queen | 40.4% | 61.3% | −4.2pp | +5.4pp |
| mixed | 46.0% | 56.4% | −3.2pp | +3.8pp |

##### Verdict per class

- **rook**, **minor_piece**: r ∈ [0.60, 0.61], zone agreement 56–58%, strong disagreement 2–3% → rubric **"Drop WDL bar"** (0.60–0.85 / 55–75% / 5–10% range — but strong-disagreement under the threshold).
- **pawn**: r = 0.54, zone 54%, strong-disagreement 2.5% → **borderline "Drop WDL bar"** (r below 0.60 cutoff, but only just).
- **mixed**: r = 0.49, zone 53%, strong-disagreement 4.5% → **"Keep all three"** (r < 0.60 cutoff).
- **queen**: r = 0.22, zone 42%, strong-disagreement 7.6% → strongly **"Keep all three"** — queen endgames are bimodal-volatile, score and gap diverge often.

##### Headline mode verdict

3 of 5 visible classes (rook, minor_piece, pawn) lean toward "Drop WDL bar"; mixed and queen lean toward "Keep all three". Treating the **mode across the 5 visible classes** as the recommendation: **mode = "Drop WDL bar"** narrowly (3 vs 2). Recommendation: keep both Score and Score-Gap bullets on the per-type card; revisit WDL bar inventory if/when card density becomes an issue.

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| Non-Endgame Score (per-user) | 3.1.1 | review (0.35) | collapse (0.14) | classical wider — review only |
| Middlegame-entry eval (centered) | 2.1 | collapse (0.19) | collapse (0.08) | single global zone OK |
| Endgame-entry eval (uncentered) | 3.1.2 | collapse (0.17) | collapse (0.13) | single global zone OK |
| Achievable Score | 3.1.3 | collapse (0.15) | collapse (0.11) | single global zone OK |
| Endgame Score (EG-only) | 3.1.4 | review (0.20) | review (0.42) | per-ELO stratification candidate |
| Achievable Score Gap | 3.1.5 | collapse (0.18) | review (0.33) | per-ELO candidate |
| Endgame Score Gap (eg − non_eg) | 3.1.6 | review (0.26) | review (0.20) | borderline; ±10pp band defensible |
| Conversion (per-user) | 3.2.1 | keep (0.84) | keep (0.51) | TC + ELO both meaningful |
| Parity (per-user) | 3.2.1 | collapse (0.12) | review (0.24) | single zone OK |
| Recovery (per-user) | 3.2.1 | keep (0.86) | collapse (0.16) | per-TC override candidate |
| Endgame Skill (per-user) | 3.2.1 | collapse (0.16) | review (0.42) | per-ELO bands already live |
| Per-bucket Score Gap — Conversion | 3.2.2 | keep (1.26) | keep (1.40) | per-bucket bands ship as live |
| Per-bucket Score Gap — Parity | 3.2.2 | collapse (0.18) | review (0.29) | single band OK |
| Per-bucket Score Gap — Recovery | 3.2.2 | keep (1.74) | keep (0.90) | per-bucket bands ship as live |
| Per-bucket Score Gap — Skill | 3.2.2 | collapse (0.14) | review (0.35) | single band OK |
| Clock pressure %-of-base | 3.3.1 | review (0.22) | collapse (0.18) | single ±5% band defensible |
| Net timeout rate | 3.3.1 | collapse (0.08) | collapse (0.19) | single ±5pp band OK |
| Clock-gap fraction | 3.3.1 clock-gap-% | review (0.22) | collapse (0.19) | single band; live placeholder fits |
| Time-pressure curve (per-bucket) | 3.3.2 | review | collapse | per-TC overlay (already live) |
| Score per pressure bin Q0 | §3.3.3 | keep (0.51) | keep (0.58) | per-TC × per-ELO at max pressure |
| Score per pressure bin Q1 | §3.3.3 | review (0.27) | review (0.23) | per-TC defensible |
| Score per pressure bin Q2 | §3.3.3 | review (0.44) | review (0.26) | per-TC defensible |
| Score per pressure bin Q3 | §3.3.3 | review (0.31) | review (0.40) | per-(TC × ELO) candidate |
| Score per pressure bin Q4 | §3.3.3 | collapse (0.18) | review (0.26) | single per-TC band OK |
| Per-class score | 3.4.1 | collapse (≤0.31) | review (≤0.39) | per-class ELO stratification candidate |
| Per-class per-span Score Gap | 3.4.2 | collapse (≤0.34) | review (≤0.47) | per-class bands stay (queen ELO-axis stretched) |

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| MG-entry eval baseline | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | +0.25 | +0.25 (measured +0.252) | collapse / collapse | keep |
| MG-entry eval neutral | 2.1 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | ±0.30 | ±0.30 (IQR ±0.35) | collapse / collapse | keep |
| MG-entry eval domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | 1.50 | 1.50 (p05/p95 ±0.95) | collapse / collapse | keep |
| Non-EG score neutral | 3.1.1 | (shared `SCORE_BULLET_NEUTRAL_*`) | ±0.05 | ±0.05 (IQR `[−0.04, +0.06]`) | review / collapse | keep |
| EG-entry eval neutral | 3.1.2 | `ENDGAME_ENTRY_EVAL_NEUTRAL_*` | ±0.60 | ±0.60 (IQR ±0.6–0.8) | collapse / collapse | keep |
| EG-entry eval domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | 2.25 | 2.25 (p05/p95 ±2.0) | collapse / collapse | keep |
| Achievable Score neutral | 3.1.3 | `entry_expected_score` ZoneSpec | (see code) | `[0.46, 0.56]` | collapse / collapse | keep / verify |
| EG score neutral | 3.1.4 | `SCORE_BULLET_NEUTRAL_*` | ±0.05 | ±0.05 (IQR `[−0.04, +0.05]`) | review / review | keep; per-ELO stratification candidate |
| Achievable Score Gap | 3.1.5 | `achievable_score_gap` ZoneSpec | (−0.04, +0.04) | (−0.04, +0.05) | collapse / review | keep |
| Score Gap (eg−non_eg) | 3.1.6 | `SCORE_GAP_NEUTRAL_*` | ±0.10 | ±0.10 (IQR ±0.09) | review / review | keep |
| Conversion FIXED | 3.2.1 | `FIXED_GAUGE_ZONES.conversion` | `[0.65, 0.75]` | `[0.64, 0.78]` | keep / keep | keep; per-TC override candidate |
| Parity FIXED | 3.2.1 | `FIXED_GAUGE_ZONES.parity` | `[0.45, 0.55]` | `[0.44, 0.57]` | collapse / review | keep |
| Recovery FIXED | 3.2.1 | `FIXED_GAUGE_ZONES.recovery` | `[0.25, 0.35]` | `[0.24, 0.37]` | keep / collapse | keep; per-TC override candidate |
| Section 2 Conv gap | 3.2.2 | `section2_score_gap_conv` | (−0.11, 0.00) | (−0.11, 0.00) | keep / keep | keep |
| Section 2 Parity gap | 3.2.2 | `section2_score_gap_parity` | (−0.04, +0.04) | (−0.04, +0.04) | collapse / review | keep |
| Section 2 Recov gap | 3.2.2 | `section2_score_gap_recov` | (+0.01, +0.11) | (+0.01, +0.11) | keep / keep | keep |
| Clock-diff % | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | ±5.0 | ±5.0 (IQR `[−6.7, +4.8]`) | review / collapse | keep |
| Net timeout % | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | ±5.0 | ±5.0 (IQR `[−4.4, +6.1]`) | collapse / collapse | keep |
| Clock-gap fraction | 3.3.1 clock-gap-% | `clock_gap_pct` | (−0.05, +0.05) | (−0.067, +0.048) | review / collapse | narrow upper / widen lower |
| Pressure-bin score | §3.3.3 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (×20) | placeholder ±0.06 | per-(TC, quintile) IQR (see §3.3.3) | keep at Q0 / review elsewhere | replace with per-quintile per-TC IQR (capped at ±0.06) |
| Per-class score (per-class) | 3.4.1 | `SCORE_BULLET_NEUTRAL_*` (shared) | ±0.05 | ±0.05 globally; queen/pawnless wider | collapse / review | keep global; per-class override candidate for queen |
| Per-type Score Gap (per-class) | 3.4.2 | `PER_CLASS_GAUGE_ZONES.*.achievable_score_gap` | per-class ±0.04–0.05 | unchanged | collapse / review (most) | keep |
| Per-type Score Gap (global) | 3.4.2 | `endgame_type_achievable_score_gap` | (−0.04, +0.04) | (−0.04, +0.05) | collapse / review | keep / minor tighten |

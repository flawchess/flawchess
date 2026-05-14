# FlawChess Benchmarks — 2026-05-14

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-14T08:46:48Z
- **Population**: 2,415 users / 1,375,544 games / 95,040,660 positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; tc_bucket from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump (single `dump_month`); 9,133 selected users in the candidate pool, 2,415 with `status='completed'` after ingest at ~100/cell (only `completed` rows enter any benchmark CTE).
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1,000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket::text = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating - user_rating) <= 100`. Applied to every per-game CTE in Chapter 2 and Chapter 3 to remove the matchmaking confound. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. Pre-2026-05-03 score-gap / clock / time-pressure numbers are not directly comparable across the boundary. See `.planning/notes/benchmark-equal-footing-framing.md` for rationale.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity). REFAC-02 — material-imbalance proxy is gone.
- **Eval coverage**: **99.9996%** of qualifying endgame entries have non-NULL eval (767,395 / 767,398). Essentially complete.
- **Sparse-cell exclusion**: `(2400, classical)` n=12 completed users, ~55 games/user. Excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes. Shown in cell-level 5×4 tables with an `n=12*` footnote.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate.
- **Sample floors**: per-cell ≥10 users for Cohen's d; per-user ≥20 EG games (3.1.3 / 3.1.4 / 3.2.1 / 3.3.1) / ≥30 EG AND ≥30 non-EG (3.1.5 / 3.1.1); per-cell n_games ≥100 for 3.3.2 / 3.4.1 score, ≥30 for 3.4.1 conv/recov.
- **What changed vs 2026-05-12**: source data unchanged (same ingest). Skill restructured into 3 chapters (`27a6242a`); **§3.1.1 Non-Endgame Score** and **§3.1.3 Achievable Score** are new dedicated subchapters in the restructured layout. Phase 85 shipped the Endgame Overall Performance section in the live UI (Cards 1/2/3 + score-differences row).

## Cell coverage (status='completed' users per cell)

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 100 | 100 | 100 | 100 |
| 1200 | 100 | 100 | 100 | 100 |
| 1600 | 100 | 100 | 100 | 100 |
| 2000 | 100 | 100 | 100 | 100 |
| 2400 | 100 | 100 | 100 | **12*** |

\* sparse — excluded from marginals / pooled / Cohen's d.

---

## 1. Stratified Sample

### Equal-footing retention (per cell, % of base-filtered games kept)

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 83.1% | 84.6% | 81.5% | 53.2% |
| 1200 | 89.5% | 89.4% | 87.8% | 72.2% |
| 1600 | 85.6% | 88.8% | 87.9% | 70.9% |
| 2000 | 78.3% | 78.4% | 73.8% | 57.1% |
| 2400 | 66.5% | 61.9% | 51.3% | **14.6%*** |

Mid-ELO retains ~85–90%. 2400 cells drop to 51–67% (higher-rated players play deeper into off-cohort opponents). Sparse `(2400, classical)` retains only ~14.6% — excluded from all marginals anyway. All non-sparse cells comfortably clear per-user sample floors.

### Eval coverage check

| qualifying endgame games | with eval | pct |
|---:|---:|---:|
| 767,398 | 767,395 | **99.9996%** |

Three NULL-eval entry plies out of 767k. Well above the 99% flag floor.

---

## 2. Openings

### 2.1 Middlegame-entry eval

#### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `EVAL_NEUTRAL_MIN_PAWNS` / `MAX_PAWNS` | −0.30 / +0.30 | `frontend/src/lib/openingStatsZones.ts` |
| `EVAL_BULLET_DOMAIN_PAWNS` | 1.5 | same |
| `EVAL_BASELINE_PAWNS_WHITE` / `BLACK` | +0.25 / −0.25 (symmetric ✓) | `app/services/opening_insights_constants.py` |
| `EVAL_CONFIDENCE_MIN_N` | 10 (subchapter uses ≥20 floor) | same |
| `EVAL_OUTLIER_TRIM_CP` | 2000 | `app/repositories/stats_repository.py` |

#### Symmetric baseline (pass 1 — deduped game-level, white-POV, no equal-footing filter)

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 1,246,674 | **+25.18** | +24.0 | 237.7 |

Black baseline = −25 cp by construction.

#### Centered pooled distribution (pass 2, excl sparse cell, ≥20 games/user-color)

| n | ctr_mean | p05 | p25 | p50 | p75 | p95 | SD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3,496 | +4.15 cp | -93.5 | **-20.6** | +6.9 | **+34.2** | +86.4 | 58.2 |

TC marginal (centered means): bullet **-4.5** / blitz **+3.4** / rapid **+9.9** / classical **+11.5** cp
ELO marginal (centered means): 800 **-6.9** / 1200 **+7.1** / 1600 **+6.1** / 2000 **+8.0** / 2400 **+5.9** cp

#### Collapse verdict

- **TC axis**: max |d| = **0.25** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.23** (800 vs 2000) → **review**

#### Recommendations

- **Baseline constant**: measured **+25.18 cp** ≈ live `EVAL_BASELINE_PAWNS_WHITE = 0.25`. **Keep**.
- **Neutral-zone bounds**: pooled centered IQR `[-20.6, +34.2]` cp = `[-0.21, +0.34]` pawns. Symmetric round to ±5 cp → ±35 cp = ±0.35 pawns. Live ±0.30 pawns is slightly tighter than the pooled IQR; **recommend widening to ±0.35** (same as 2026-05-12).
- **Domain**: pooled `[p05, p95]` = `[-94, +86]` cp = `[-0.94, +0.86]` pawns. Live ±1.5 pawns is wider than the cohort tails — **keep**.

---

## 3. Endgames

### 3.1 Endgame Overall Performance

Subsections in page-display order: Card 1 (Games without Endgame) → Card 2 row 1 (Endgame-entry eval) → Card 2 row 2 (Achievable Score) → Card 3 (Games with Endgame) → Endgame Score Differences row.

#### 3.1.1 Non-Endgame Score (per-user)

Per-user `non_eg_score = (W + 0.5·D) / total` over games that do NOT reach the 6-ply endgame floor. Aggregated from the 3.1.5 `per_user` CTE (≥30 EG AND ≥30 non-EG games/user).

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `SCORE_BULLET_CENTER` | 0.5 | `frontend/src/lib/scoreBulletConfig.ts` |
| `SCORE_BULLET_NEUTRAL_MIN` / `MAX` | −0.05 / +0.05 | same |
| `SCORE_BULLET_DOMAIN` | 0.25 (half-width) | same |

Shared with the Openings score bullet AND with the Card 3 EG-only tile (§3.1.4). Calibration recommendations for the non-EG subset go into a dedicated module if needed, not this constant.

##### 5×4 cell table — `non_eg_p50 (n_users)`

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 0.504 (97) | 0.500 (97) | 0.514 (94) | 0.551 (24) |
| 1200 | 0.516 (97) | 0.515 (99) | 0.516 (98) | 0.554 (51) |
| 1600 | 0.509 (97) | 0.505 (99) | 0.511 (100) | 0.544 (66) |
| 2000 | 0.523 (100) | 0.529 (98) | 0.535 (95) | 0.560 (49) |
| 2400 | 0.510 (98) | 0.556 (96) | 0.560 (77) | 0.530 (1)* |

##### TC marginal (excl sparse)

| TC | n_users | mean | non_eg_p25 | non_eg_p50 | non_eg_p75 |
|---|---:|---:|---:|---:|---:|
| bullet | 489 | 0.5124 | 0.4651 | 0.5130 | 0.5564 |
| blitz | 489 | 0.5195 | 0.4651 | 0.5190 | 0.5688 |
| rapid | 464 | 0.5272 | 0.4720 | 0.5265 | 0.5775 |
| classical | 190 | 0.5570 | 0.4885 | 0.5490 | 0.6290 |

##### ELO marginal (excl sparse)

| ELO | n_users | mean | non_eg_p25 | non_eg_p50 | non_eg_p75 |
|---|---:|---:|---:|---:|---:|
| 800 | 312 | 0.5052 | 0.4626 | 0.5064 | 0.5500 |
| 1200 | 345 | 0.5216 | 0.4685 | 0.5174 | 0.5673 |
| 1600 | 362 | 0.5162 | 0.4545 | 0.5132 | 0.5646 |
| 2000 | 342 | 0.5343 | 0.4755 | 0.5333 | 0.5833 |
| 2400 | 271 | 0.5457 | 0.4852 | 0.5465 | 0.6034 |

##### Pooled (excl sparse)

| n_users | mean | non_eg_p05 | non_eg_p25 | non_eg_p50 | non_eg_p75 | non_eg_p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1632 | 0.5239 | 0.3887 | **0.4679** | 0.5214 | **0.5739** | 0.6725 |

##### Collapse verdict

- **TC axis**: max |d| = **0.50** (bullet vs classical) → **keep separate** (just clears the 0.5 threshold)
- **ELO axis**: max |d| = **0.49** (800 vs 2400) → **review** (just below 0.5)

Heatmap of per-user `non_eg_p50`:

```
           bullet   blitz   rapid   classical
  800       0.50    0.50    0.51    0.55
  1200      0.52    0.52    0.52    0.55
  1600      0.51    0.51    0.51    0.54
  2000      0.52    0.53    0.53    0.56
  2400      0.51    0.56    0.56    0.53*
```

##### Recommendations

- **Pooled mean = 0.524** is +2.4 pp above the chess fairness null of 0.50 — larger than the EG-only or entry_xs cohort skill edge, consistent with non-endgame games being shorter and more decided by tactical edge (where the benchmark population outperforms its opponent pool more clearly than in endings).
- **Cohort neutral band**: pooled IQR `[0.47, 0.57]` (asymmetric: 3pp below center, 7pp above). The shared `SCORE_BULLET_NEUTRAL_*` band is `[0.45, 0.55]` — pooled IQR sits visibly above this on both bounds. The bullet's center=0.5 means the live tile paints "typical" symmetrically around 0.5; the cohort actually centers at ~0.52.
- **Recommendation routing**: `SCORE_BULLET_NEUTRAL_*` is **shared** with both the Openings score bullet AND the §3.1.4 EG-only Card 3 tile. The skill says: if non-EG `[p25, p75]` materially differs from the shared band, the right move is a dedicated non-EG zones module, not retuning the shared constant. The 2pp center-mismatch and asymmetric IQR justify a dedicated `NON_ENDGAME_SCORE_ZONES` entry (mirroring `endgame_score` / `entry_expected_score` in `endgame_zones.py`), centered at 0.52 with bounds `[0.47, 0.57]`. **Defer until UI/UX is ready** — leave the shared bullet alone for now and document the cohort drift.
- **TC verdict = keep separate (0.50)** is driven entirely by the **classical** cohort sitting +5pp above bullet — classical players in this stratified sample play fewer non-endgame games (those that don't reach `≥ 6 endgame plies`), and the surviving non-EG subset is dominated by decisive openings/middlegames where classical players are stronger. If a per-TC stratification ever ships for this metric, classical needs its own band; bullet/blitz/rapid can share one. **No action** without a UI argument — the metric is too tile-level for the user-facing tile to benefit from cell-specific zones.

#### 3.1.2 Endgame-entry eval (pawns)

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS` / `MAX_PAWNS` | −0.75 / +0.75 | `frontend/src/lib/endgameEntryEvalZones.ts` |
| `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | 2.25 | same |
| `ENDGAME_ENTRY_EVAL_CENTER` | 0 | same |

Tile is 0-centered (uncentered eval drives the live bullet — no baseline subtraction).

##### Symmetric baseline (pass 1, reference only — live tile is 0-centered)

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 801,065 | **+9.86** | 0.0 | 442.6 |

EG-entry baseline (+10 cp) is much smaller than MG (+25 cp) — piece trades dissipate engine tempo.

##### Uncentered pooled distribution (excl sparse, ≥20 games/user-color) — feeds the 0-centered bullet

| n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3,304 | +8.9 cp | -186.0 | **-55.8** | +10.3 | **+75.0** | +198.8 | 117.3 |

##### Centered pooled distribution (reported for Cohen's d / parity with §2.1)

| n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3,304 | +8.9 cp | -182.9 | -53.8 | +10.7 | +75.3 | +197.0 | 116.8 |

TC marginal (centered means): bullet **-6.1** / blitz **+14.0** / rapid **+20.8** / classical **+4.9** cp
ELO marginal (centered means): 800 **-15.0** / 1200 **+1.5** / 1600 **+14.7** / 2000 **+20.6** / 2400 **+21.6** cp

##### Collapse verdict (on centered data)

- **TC axis**: max |d| = **0.22** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.28** (800 vs 2400) → **review**

##### Recommendations

- **Neutral band**: pooled uncentered IQR `[-56, +75]` cp = `[-0.56, +0.75]` pawns. Live `[-0.75, +0.75]` matches the upper bound exactly; lower bound is wider than the pooled p25. **Editorial tightening (memory `feedback_zone_band_judgement.md`)**: pooled IQR is wide enough that a "small but real" -0.40 pawn entry still lands in `typical`. Live ±0.75 is acceptable as a conservative band on the danger side; tightening to ±0.55 pawns is a defensible alternative. **No change recommended** without UX evidence the live band paints too rarely.
- **Domain**: pooled `[p05, p95]` = `[-186, +199]` cp = `[-1.86, +1.99]` pawns. Live ±2.25 slightly wider — **keep**.
- **Center**: live `ENDGAME_ENTRY_EVAL_CENTER = 0`. Pooled mean = **+9 cp ≈ +0.09 pawns** — within ±10 cp of 0, **keep 0-center**.

#### 3.1.3 Achievable Score (Stockfish-predicted expected score at EG entry)

Per-user `entry_xs = avg(P(win | eval at first endgame ply))` via the Lichess winning-chances sigmoid (cp) / direct 0|1 (mate). Sample floor ≥20 EG-entry games/user.

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN` | 0.45 | `frontend/src/generated/endgameZones.ts` |
| `ENTRY_EXPECTED_SCORE_NEUTRAL_MAX` | 0.55 | same |
| `entry_expected_score` ZoneSpec | `typical_lower=0.45, typical_upper=0.55, direction="higher_is_better"` | `app/services/endgame_zones.py` |
| `entryExpectedScoreZoneColor()` | red < 0.45, neutral [0.45, 0.55), green ≥ 0.55 | `frontend/src/generated/endgameZones.ts` |

##### 5×4 cell table — per-user `xs_p50 (n_users)`

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 0.495 (99) | 0.494 (100) | 0.498 (96) | 0.477 (41) |
| 1200 | 0.486 (100) | 0.513 (99) | 0.506 (100) | 0.519 (72) |
| 1600 | 0.492 (100) | 0.521 (100) | 0.517 (100) | 0.508 (85) |
| 2000 | 0.503 (100) | 0.517 (100) | 0.524 (98) | 0.518 (66) |
| 2400 | 0.505 (100) | 0.511 (100) | 0.517 (95) | 0.653 (2)* |

##### TC marginal (excl sparse)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 499 | 0.4998 | 0.359 | 0.448 | 0.501 | 0.553 | 0.647 |
| blitz | 499 | 0.5112 | 0.410 | 0.471 | 0.512 | 0.548 | 0.624 |
| rapid | 489 | 0.5171 | 0.407 | 0.473 | 0.515 | 0.561 | 0.633 |
| classical | 264 | 0.5102 | 0.364 | 0.456 | 0.509 | 0.563 | 0.669 |

##### ELO marginal (excl sparse)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 0.4961 | 0.325 | 0.420 | 0.493 | 0.560 | 0.684 |
| 1200 | 371 | 0.5080 | 0.366 | 0.451 | 0.504 | 0.562 | 0.671 |
| 1600 | 385 | 0.5130 | 0.406 | 0.469 | 0.512 | 0.561 | 0.633 |
| 2000 | 364 | 0.5155 | 0.421 | 0.479 | 0.516 | 0.555 | 0.607 |
| 2400 | 295 | 0.5144 | 0.443 | 0.485 | 0.512 | 0.541 | 0.599 |

##### Pooled (excl sparse)

| n | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1751 | 0.5094 | 0.382 | **0.463** | 0.510 | **0.554** | 0.641 |

##### Collapse verdict

- **TC axis**: max |d| = **0.22** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.23** (800 vs 2000) → **review**

##### Recommendations

- **Sanity check**: pooled mean = **0.5094** (+0.9 pp above 50%) — small benchmark skill edge, within tolerance. Equal-footing filter is healthy.
- **Cohort neutral band**: pooled IQR `[0.46, 0.55]`. Live `[0.45, 0.55]` matches the upper bound exactly and is 1pp wider on the lower bound. **Keep** — both bounds are within rounding tolerance of pooled IQR, and the band aligns with the §3.1.4 endgame_score band for visual parity (memory `feedback_zone_band_judgement.md`).
- **No stratification recommended**: TC and ELO d both in 0.20–0.25 (review tier, near collapse). Pooled band is honest enough for all cohorts.

#### 3.1.4 Endgame Score (per-user, EG-only)

Per-user `eg_score = (W + 0.5·D) / total` over endgame-reaching games in the user's selected TC. Sample floor ≥20 EG games per user.

##### Currently set in code (shared score-bullet config)

| Constant | Live value | File |
|---|---:|---|
| `SCORE_BULLET_CENTER` | 0.5 | `frontend/src/lib/scoreBulletConfig.ts` |
| `SCORE_BULLET_NEUTRAL_MIN` / `MAX` | −0.05 / +0.05 | same |
| `SCORE_BULLET_DOMAIN` | 0.25 (half-width) | same |
| `endgame_score` ZoneSpec | `typical_lower=0.45, typical_upper=0.55, direction="higher_is_better"` | `app/services/endgame_zones.py` |

Shared with the Openings score bullet and with §3.1.1.

##### 5×4 cell table — per-user `eg_p50 (n_users)`

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 0.473 (99) | 0.478 (100) | 0.490 (96) | 0.439 (41) |
| 1200 | 0.492 (100) | 0.481 (99) | 0.513 (100) | 0.512 (72) |
| 1600 | 0.499 (100) | 0.504 (100) | 0.517 (100) | 0.500 (85) |
| 2000 | 0.506 (100) | 0.528 (100) | 0.522 (98) | 0.536 (66) |
| 2400 | 0.524 (100) | 0.541 (100) | 0.548 (95) | 0.774 (2)* |

##### TC marginal (excl sparse)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 499 | 0.5032 | 0.406 | 0.461 | 0.500 | 0.539 | 0.616 |
| blitz | 499 | 0.5133 | 0.409 | 0.468 | 0.511 | 0.558 | 0.627 |
| rapid | 489 | 0.5234 | 0.398 | 0.471 | 0.522 | 0.569 | 0.668 |
| classical | 264 | 0.5069 | 0.333 | 0.439 | 0.504 | 0.575 | 0.665 |

##### ELO marginal (excl sparse)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 0.4792 | 0.340 | 0.423 | 0.474 | 0.523 | 0.640 |
| 1200 | 371 | 0.5046 | 0.377 | 0.449 | 0.493 | 0.550 | 0.646 |
| 1600 | 385 | 0.5106 | 0.400 | 0.462 | 0.504 | 0.554 | 0.639 |
| 2000 | 364 | 0.5249 | 0.427 | 0.489 | 0.521 | 0.560 | 0.630 |
| 2400 | 295 | 0.5461 | 0.450 | 0.504 | 0.539 | 0.581 | 0.661 |

##### Pooled (excl sparse)

| n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1751 | 0.5123 | 0.393 | 0.463 | 0.509 | 0.558 | 0.644 |

##### Collapse verdict

- **TC axis**: max |d| = **0.27** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.84** (800 vs 2400) → **keep separate**

Heatmap of per-user `eg_p50`:

```
           bullet   blitz   rapid   classical
  800       0.47    0.48    0.49    0.44
  1200      0.49    0.48    0.51    0.51
  1600      0.50    0.50    0.52    0.50
  2000      0.51    0.53    0.52    0.54
  2400      0.52    0.54    0.55    0.77*
```

##### Recommendations

- **Pooled mean = 0.512** is +1.2 pp above the chess fairness null of 0.50 — within the expected benchmark skill edge. Equal-footing filter healthy.
- **Cohort neutral band** (pooled IQR): `[0.46, 0.56]`. Slightly tighter than live `[0.45, 0.55]` on the low side, slightly wider on the high side. Within rounding tolerance — **keep ±0.05 on the shared score bullet**.
- **Cohort domain** (pooled `[p05, p95]`): `[0.39, 0.64]` (half-width ≈ 0.13). Live `±0.25` is wider than the pooled distribution; **keep** — extreme users still need to render.
- **ELO stratification recommended**: ELO p50 spreads from 0.47 → 0.55 across cohorts (8 pp, wider than the ±5 pp IQR width). The shared score bullet stays as-is, but the EG-only tile should consider a dedicated `ENDGAME_SCORE_ZONES` per-ELO registry (mirroring `ENDGAME_SKILL_ZONES`). Document the 8 pp expected drift until then.

#### 3.1.5 Score Gap (gauge + timeline)

Per-user `diff = eg_score − non_eg_score`. Floor: ≥30 EG AND ≥30 non-EG games.

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `SCORE_GAP_NEUTRAL_MIN` / `MAX` | −0.10 / +0.10 | `frontend/src/generated/endgameZones.ts` |
| `SCORE_GAP_DOMAIN` (half-width) | 0.20 | `frontend/src/components/charts/EndgameOverallShared.ts` |
| `SCORE_TIMELINE_Y_DOMAIN` | [20, 80] | `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` |

##### 5×4 cell table — `diff_p50 (n_users)`

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | -0.036 (97) | -0.024 (97) | -0.023 (94) | -0.134 (24) |
| 1200 | -0.040 (97) | -0.032 (99) | +0.008 (98) | -0.055 (51) |
| 1600 | -0.017 (97) | -0.001 (99) | +0.007 (100) | -0.048 (66) |
| 2000 | -0.014 (100) | +0.005 (98) | +0.008 (95) | -0.019 (49) |
| 2400 | +0.023 (98) | -0.002 (96) | -0.009 (77) | +0.064 (1)* |

##### TC marginal (excl sparse)

| TC | n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 489 | -0.0101 | -0.182 | -0.095 | -0.018 | +0.064 | +0.198 |
| blitz | 489 | -0.0074 | -0.191 | -0.093 | -0.009 | +0.069 | +0.195 |
| rapid | 464 | -0.0071 | -0.232 | -0.095 | -0.006 | +0.082 | +0.203 |
| classical | 190 | -0.0529 | -0.337 | -0.151 | -0.046 | +0.065 | +0.199 |

##### ELO marginal (excl sparse)

| ELO | n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 312 | -0.0253 | -0.242 | -0.116 | -0.036 | +0.053 | +0.219 |
| 1200 | 345 | -0.0206 | -0.237 | -0.112 | -0.031 | +0.072 | +0.212 |
| 1600 | 362 | -0.0068 | -0.231 | -0.103 | -0.009 | +0.094 | +0.210 |
| 2000 | 342 | -0.0095 | -0.206 | -0.088 | -0.004 | +0.068 | +0.164 |
| 2400 | 271 | -0.0043 | -0.197 | -0.082 | +0.001 | +0.074 | +0.167 |

##### Pooled (excl sparse)

| n | mean | p05 | p25 | p50 | p75 | p95 | eg_mean | non_eg_mean |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1632 | -0.0134 | -0.227 | -0.104 | -0.014 | +0.073 | +0.202 | 0.5105 | 0.5239 |

##### Collapse verdict

- **TC axis**: max |d| = **0.34** (blitz vs classical) → **review**
- **ELO axis**: max |d| = **0.17** (800 vs 2400) → **collapse**

##### Recommendations

- **Score-gap neutral zone**: pooled IQR `[-0.10, +0.07]`. Median = -0.014 (well under the 5pp out-of-scope guard). **Keep symmetric ±0.10** — lower bound matches exactly, upper bound slightly tighter than pooled.
- **Score-gap domain**: pooled `[p05, p95]` = `[-0.227, +0.202]`. Half-width 0.227 vs live 0.20 — recommend **widening to ±0.23** so extreme bullet/classical users don't clip (same as 2026-05-12).
- **Timeline Y-axis**: pooled eg_mean=0.51, non_eg_mean=0.52. Live `[20, 80]` (in %) easily encloses cohort behaviour — **keep**.
- **TC split**: classical's `diff_mean = -0.053` is the only TC with meaningful mean drift (others within ±1 pp). Per "review" verdict — no immediate action; revisit if user feedback shows classical-only complaints.

---

### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery + Endgame Skill

##### Currently set in code

| Constant | Live value | File |
|---|---|---|
| `FIXED_GAUGE_ZONES.conversion` | neutral [0.65, 0.77] | `frontend/src/generated/endgameZones.ts` |
| `FIXED_GAUGE_ZONES.parity` | neutral [0.45, 0.55] | same |
| `FIXED_GAUGE_ZONES.recovery` | neutral [0.24, 0.36] | same |
| `ENDGAME_SKILL_ZONES` | neutral [0.47, 0.55] | same |
| `NEUTRAL_ZONE_MIN` / `MAX` (score-gap bullet, §2 file) | −0.05 / +0.05 | `frontend/src/components/charts/EndgameScoreGapSection.tsx` |
| `BULLET_DOMAIN` | 0.20 | same |

##### Conversion

5×4 cell table — per-user `conv_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 0.597 (99) | 0.701 (100) | 0.714 (96) | 0.714 (41) |
| 1200 | 0.625 (100) | 0.709 (99) | 0.734 (100) | 0.750 (72) |
| 1600 | 0.659 (100) | 0.712 (100) | 0.747 (100) | 0.776 (85) |
| 2000 | 0.672 (100) | 0.726 (100) | 0.749 (98) | 0.774 (66) |
| 2400 | 0.713 (100) | 0.744 (100) | 0.778 (95) | 0.794 (2)* |

TC marginal: bullet **0.658** / blitz **0.718** / rapid **0.745** / classical **0.761**
ELO marginal: 800 **0.684** / 1200 **0.709** / 1600 **0.721** / 2000 **0.725** / 2400 **0.743**
Pooled: mean 0.711, **p25/p50/p75 = 0.656 / 0.719 / 0.769**

**Collapse verdict** — TC d_max ≈ **1.02** (bullet vs classical) → **keep separate**. ELO d_max ≈ **0.82** (800 vs 2400) → **keep separate**.

Recommendation: live neutral `[0.65, 0.77]` ≈ pooled `[0.66, 0.77]` — **keep as pooled default**. A per-TC/per-ELO stratified registry would meaningfully tighten zones (bullet pooled p25/p75 ≈ 0.58/0.72 vs classical ≈ 0.70/0.83).

##### Parity

5×4 cell table — per-user `par_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 0.500 (97) | 0.479 (100) | 0.500 (96) | 0.385 (39) |
| 1200 | 0.490 (100) | 0.489 (99) | 0.487 (100) | 0.500 (72) |
| 1600 | 0.515 (100) | 0.500 (100) | 0.500 (100) | 0.500 (85) |
| 2000 | 0.499 (100) | 0.513 (100) | 0.519 (98) | 0.521 (66) |
| 2400 | 0.522 (100) | 0.552 (100) | 0.540 (95) | 0.712 (2)* |

TC marginal: bullet **0.500** / blitz **0.507** / rapid **0.506** / classical **0.500**
ELO marginal: 800 **0.500** / 1200 **0.489** / 1600 **0.500** / 2000 **0.512** / 2400 **0.539**
Pooled: mean 0.502, **p25/p50/p75 = 0.443 / 0.500 / 0.563**

**Collapse verdict** — TC d_max ≈ **0.12** → **collapse**. ELO d_max ≈ **0.48** (800 vs 2400) → **review**.

Recommendation: live `[0.45, 0.55]` matches pooled IQR `[0.44, 0.56]` closely — **keep**. ELO ramp borderline meaningful (0.49 → 0.54).

##### Recovery

5×4 cell table — per-user `recov_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 0.354 (99) | 0.290 (100) | 0.258 (96) | 0.203 (41) |
| 1200 | 0.365 (100) | 0.290 (99) | 0.286 (99) | 0.226 (72) |
| 1600 | 0.340 (100) | 0.287 (100) | 0.269 (100) | 0.222 (85) |
| 2000 | 0.344 (100) | 0.330 (100) | 0.264 (98) | 0.272 (66) |
| 2400 | 0.346 (100) | 0.317 (100) | 0.300 (95) | 0.250 (2)* |

TC marginal: bullet **0.353** / blitz **0.303** / rapid **0.277** / classical **0.233**
ELO marginal: 800 **0.297** / 1200 **0.296** / 1600 **0.287** / 2000 **0.305** / 2400 **0.323**
Pooled: mean 0.305, **p25/p50/p75 = 0.243 / 0.301 / 0.364**

**Collapse verdict** — TC d_max ≈ **1.10** (bullet vs classical) → **keep separate**. ELO d_max ≈ **0.40** → **review**.

Recommendation: live `[0.24, 0.36]` matches pooled IQR exactly — **keep**. TC ramp is huge (bullet 0.35 → classical 0.23). A per-TC registry would meaningfully sharpen feedback.

##### Endgame Skill (composite)

5×4 cell table — per-user `skill_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 0.481 (99) | 0.497 (100) | 0.493 (96) | 0.438 (41) |
| 1200 | 0.492 (100) | 0.496 (99) | 0.508 (100) | 0.496 (72) |
| 1600 | 0.509 (100) | 0.501 (100) | 0.507 (100) | 0.516 (85) |
| 2000 | 0.506 (100) | 0.521 (100) | 0.512 (98) | 0.523 (66) |
| 2400 | 0.528 (100) | 0.543 (100) | 0.544 (95) | 0.585 (2)* |

TC marginal: bullet **0.506** / blitz **0.509** / rapid **0.512** / classical **0.499**
ELO marginal: 800 **0.489** / 1200 **0.497** / 1600 **0.507** / 2000 **0.514** / 2400 **0.539**
Pooled: mean 0.506, **p25/p50/p75 = 0.466 / 0.508 / 0.548**

**Collapse verdict** — TC d_max ≈ **0.18** → **collapse**. ELO d_max ≈ **0.78** (800 vs 2400) → **keep separate**.

Recommendation: live `[0.47, 0.55]` matches pooled `[0.47, 0.55]` exactly — **keep as pooled**. Live `ENDGAME_SKILL_ZONES` already serves the ELO stratification need.

---

### 3.3 Time Pressure

#### 3.3.1 Clock pressure at endgame entry

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `NEUTRAL_PCT_THRESHOLD` | 5.0 (band ±5pp) | `frontend/src/generated/endgameZones.ts` |
| `NEUTRAL_TIMEOUT_THRESHOLD` | 5.0 (band ±5pp) | same |

##### Clock-diff % (user − opp, as % of base time)

5×4 cell table — per-user `pct_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | -0.70 (98) | -0.76 (100) | +1.24 (96) | +0.18 (38) |
| 1200 | -0.43 (100) | -0.48 (99) | -0.09 (100) | +1.17 (72) |
| 1600 | -0.20 (99) | -1.70 (100) | -0.12 (100) | -0.20 (85) |
| 2000 | -1.53 (100) | -1.48 (100) | -1.27 (98) | -5.69 (64) |
| 2400 | +0.12 (99) | -0.04 (100) | -3.29 (95) | +4.30 (2)* |

TC marginal: bullet **-0.22** / blitz **-1.40** / rapid **-1.48** / classical **-2.71**
ELO marginal: 800 **-1.07** / 1200 **-1.17** / 1600 **-1.43** / 2000 **-2.23** / 2400 **-0.29**
Pooled: p25/p50/p75 = **-6.41 / -0.52 / +4.66**

**Collapse verdict** — TC d_max ≈ **0.23** (bullet vs classical) → **review**. ELO d_max ≈ **0.21** (2000 vs 2400) → **review**.

Recommendation: pooled IQR slightly asymmetric (`[-6.4, +4.7]`). Live ±5 close but lower tail is wider — **widen to ±6** if narrative emphasis warrants, otherwise keep. TC ramp mild; per-TC split not required.

##### Net timeout rate (timeout_wins − timeout_losses per game, %)

5×4 cell table — per-user `net_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | -5.25 | -0.29 | +1.32 | 0.00 |
| 1200 | -0.56 | +2.03 | +1.16 | 0.00 |
| 1600 | +1.98 | +1.13 | +2.01 | 0.00 |
| 2000 | +2.19 | +2.25 | +1.97 | +0.58 |
| 2400 | +5.53 | +1.95 | +2.42 | 0.00 (2)* |

TC marginal: bullet **+0.37** / blitz **-0.01** / rapid **+0.16** / classical **-0.33**
ELO marginal: 800 **-2.01** / 1200 **-0.34** / 1600 **-0.17** / 2000 **+0.61** / 2400 **+2.77**
Pooled: p25/p50/p75 = **-4.43 / +1.04 / +5.63**

**Collapse verdict** — TC d_max ≈ **0.07** → **collapse**. ELO d_max ≈ **0.41** (800 vs 2400) → **review**.

Recommendation: pooled IQR `[-4.4, +5.6]`. Live ±5 fits reasonably — **keep**. ELO ramp is real (800 nets -2 / 2400 nets +2.8); the "typical" band centered on 0 still reads cleanly across cohorts.

#### 3.3.2 Time pressure vs performance

Per (TC × time-bucket) curves. Time bucket 0 = 0-10% time remaining (max pressure); 9 = 90-100% (min pressure). Per-cell pooled score (not per-user).

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `Y_AXIS_DOMAIN` | [0.2, 0.8] | `frontend/src/components/charts/EndgameTimePressureSection.tsx` |
| `X_AXIS_DOMAIN` | [0, 100] | same |
| `MIN_GAMES_FOR_CLOCK_STATS` | 10 | `app/services/endgame_service.py` |

##### TC marginals — pooled across ELO (excl sparse)

| Time bucket | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 0 (max pressure) | 0.260 | 0.334 | 0.338 | 0.410 |
| 1 | 0.399 | 0.437 | 0.441 | 0.452 |
| 2 | 0.491 | 0.492 | 0.469 | 0.468 |
| 3 | 0.530 | 0.518 | 0.508 | 0.475 |
| 4 | 0.552 | 0.534 | 0.532 | 0.478 |
| 5 | 0.564 | 0.548 | 0.533 | 0.487 |
| 6 | 0.563 | 0.544 | 0.529 | 0.505 |
| 7 | 0.553 | 0.542 | 0.523 | 0.510 |
| 8 | 0.542 | 0.534 | 0.524 | 0.502 |
| 9 (min pressure) | 0.500 | 0.523 | 0.524 | 0.510 |

bullet/blitz show strong pressure penalty (0.26 → 0.56); classical curve is flat (0.41 → 0.51).

##### ELO marginals — pooled across TC (excl sparse)

| Time bucket | 800 | 1200 | 1600 | 2000 | 2400 |
|---:|---:|---:|---:|---:|---:|
| 0 | 0.266 | 0.283 | 0.304 | 0.332 | 0.336 |
| 3 | 0.511 | 0.512 | 0.516 | 0.525 | 0.538 |
| 5 | 0.538 | 0.532 | 0.537 | 0.563 | 0.575 |
| 9 | 0.490 | 0.501 | 0.537 | 0.547 | 0.564 |

Higher ELO → flatter/higher curve.

**Collapse verdict (per-bucket Cohen's d on per-game binary scores)** — TC d_max ≈ **0.34** (bullet vs classical at tb=0) → **review**. ELO d_max ≈ **0.17** (across buckets) → **collapse** at the per-game granularity.

Recommendation: **show TC overlay** in the live curve (TC pooled across ELO) — the bullet/classical curve gap is large enough to matter. ELO overlay optional; can collapse to a single global curve.

---

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

##### Currently set in code

| Constant | Live | File |
|---|---|---|
| `NEUTRAL_ZONE_MIN/MAX` (score-diff bullet, `EndgameWDLChart`) | ±0.05 | `frontend/src/components/charts/EndgameWDLChart.tsx` |
| `BULLET_DOMAIN` (score-diff) | 0.30 | same |
| `PER_CLASS_GAUGE_ZONES.rook` | conv [0.65, 0.75], recov [0.26, 0.36] | `frontend/src/generated/endgameZones.ts` |
| `PER_CLASS_GAUGE_ZONES.minor_piece` | conv [0.63, 0.73], recov [0.31, 0.41] | same |
| `PER_CLASS_GAUGE_ZONES.pawn` | conv [0.67, 0.79], recov [0.23, 0.34] | same |
| `PER_CLASS_GAUGE_ZONES.queen` | conv [0.73, 0.83], recov [0.20, 0.30] | same |
| `PER_CLASS_GAUGE_ZONES.mixed` | conv [0.65, 0.75], recov [0.28, 0.38] | same |
| `PER_CLASS_GAUGE_ZONES.pawnless` | conv [0.70, 0.80], recov [0.21, 0.31] | same |

##### Pooled-by-class summary (excl sparse cell)

| class | games | users | score | score_diff | conv | recov |
|---|---:|---:|---:|---:|---:|---:|
| rook | 94,087 | 1,845 | 0.5075 | +0.0151 | 0.7098 | 0.2963 |
| minor_piece | 70,381 | 1,825 | 0.5102 | +0.0204 | 0.6949 | 0.3278 |
| pawn | 37,463 | 1,750 | 0.5105 | +0.0209 | 0.7379 | 0.2754 |
| queen | 34,432 | 1,764 | 0.5079 | +0.0158 | 0.7744 | 0.2343 |
| mixed | 529,608 | 1,888 | 0.5055 | +0.0110 | 0.6940 | 0.3111 |
| pawnless | 5,847 | 1,365 | 0.5069 | +0.0139 | 0.7913 | 0.1976 |

##### Score-diff (cell-level)

All cell-level score_diff values land in `[-0.22, +0.15]`. Pooled per-class score_diff = `+0.01..+0.02` — within ±0.05.

##### Conversion comparison

| class | live neutral | pooled (this snapshot) | delta |
|---|---|---:|---|
| rook | [0.65, 0.75] | 0.710 | ≈ centered ✓ |
| minor_piece | [0.63, 0.73] | 0.695 | ≈ centered ✓ |
| pawn | [0.67, 0.79] | 0.738 | ≈ centered ✓ |
| queen | [0.73, 0.83] | 0.774 | ≈ centered ✓ |
| mixed | [0.65, 0.75] | 0.694 | ≈ centered ✓ |
| pawnless | [0.70, 0.80] | 0.791 | shifted high — recommend [0.74, 0.84] |

##### Recovery comparison

| class | live neutral | pooled | delta |
|---|---|---:|---|
| rook | [0.26, 0.36] | 0.296 | ≈ centered ✓ |
| minor_piece | [0.31, 0.41] | 0.328 | ≈ centered ✓ |
| pawn | [0.23, 0.34] | 0.275 | ≈ centered ✓ |
| queen | [0.20, 0.30] | 0.234 | ≈ centered ✓ |
| mixed | [0.28, 0.38] | 0.311 | ≈ centered ✓ |
| pawnless | [0.21, 0.31] | 0.198 | shifted low — recommend [0.15, 0.25] |

##### Recommendations

- Live per-class registry is healthy. Two classes drifted vs 2026-05-01 baseline:
  - **pawnless conversion**: live midpoint 0.75 vs new pooled 0.79 (~4 pp drift up). Suggest shifting to `[0.74, 0.84]`.
  - **pawnless recovery**: live midpoint 0.26 vs new pooled 0.20 (~6 pp drift down). Suggest shifting to `[0.15, 0.25]`.
  - pawnless has the smallest sample (5,847 games / 1,365 users). Drift may also reflect sampling noise.
- Per-class **score_diff**: all classes within ±0.025 — live `NEUTRAL_ZONE_MIN/MAX = ±0.05` continues to fit. **Keep**.
- **Collapse verdicts**: same ELO ramp pattern observed in §3.2.1 — conversion climbs with ELO across classes, recovery roughly flat. ELO stratification per class is statistically supported but UI cost is high; stick with pooled per-class until users ask for finer grain.

---

## Top-axis collapse summary (headline deliverable)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| Non-Endgame Score (per-user) | 3.1.1 | **keep separate (0.50)** | review (0.49) | classical TC drifts +5pp; dedicated non-EG zones if UI ever stratifies |
| Endgame-entry eval (uncentered) | 3.1.2 | review (0.22) | review (0.28) | pooled band fits; 0-center stays |
| Achievable Score | 3.1.3 | review (0.22) | review (0.23) | pooled band fits live [0.45, 0.55] |
| Endgame Score (per-user, EG-only) | 3.1.4 | review (0.27) | **keep separate (0.84)** | ELO stratification justified for EG-only score band |
| Score gap (eg − non_eg) | 3.1.5 | review (0.34) | collapse (0.17) | classical only TC drifts; single pooled ±0.10 OK |
| Middlegame-entry eval (centered) | 2.1 | review (0.25) | review (0.23) | pooled band fits; no stratification |
| Conversion (per-user) | 3.2.1 | **keep separate (1.02)** | **keep separate (0.82)** | per-cell calibration well justified |
| Parity (per-user) | 3.2.1 | collapse (0.12) | review (0.48) | live [0.45, 0.55] OK; ELO ramp borderline |
| Recovery (per-user) | 3.2.1 | **keep separate (1.10)** | review (0.40) | per-TC bands warranted |
| Endgame Skill (per-user) | 3.2.1 | collapse (0.18) | **keep separate (0.78)** | matches live `ENDGAME_SKILL_ZONES` |
| Clock pressure %-of-base | 3.3.1 | review (0.23) | review (0.21) | single pooled threshold OK |
| Net timeout rate | 3.3.1 | collapse (0.07) | review (0.41) | single pooled threshold OK; strong ELO ramp |
| Time-pressure curve (per-bucket) | 3.3.2 | review (0.34) | collapse (0.17) | TC overlay recommended |
| Per-class score | 3.4.1 | flat across classes | — | pooled ±0.05 OK |
| Per-class conversion | 3.4.1 | — | — | pawnless drift detected — recalibrate |
| Per-class recovery | 3.4.1 | — | — | pawnless drift detected — recalibrate |

**Verdict changes vs 2026-05-12**: only 3.1.1 (Non-Endgame Score) is genuinely new — restructured-skill subchapter computed for the first time, lands at "keep separate" on TC (just clears 0.5). All other metrics are bit-identical to 2026-05-12 (same ingest, no DB change).

---

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| Non-EG score neutral (shared bullet) | 3.1.1 | `SCORE_BULLET_NEUTRAL_MIN/MAX` (shared) | ±0.05 | ±0.05 (shared); dedicated `NON_ENDGAME_SCORE_ZONES` ≈ `[0.47, 0.57]` centered at 0.52 | TC keep, ELO review | keep shared; defer dedicated module |
| EG-entry eval neutral | 3.1.2 | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` | ±0.75 | ±0.75 (or tighten to ±0.55 editorial) | both review | keep |
| EG-entry eval domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | 2.25 | 2.25 | — | keep |
| EG-entry eval center | 3.1.2 | `ENDGAME_ENTRY_EVAL_CENTER` | 0 | 0 | — | keep |
| Achievable Score neutral | 3.1.3 | `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX` | [0.45, 0.55] | [0.45, 0.55] (pooled IQR [0.46, 0.55]) | both review | keep |
| EG-only score neutral (shared bullet) | 3.1.4 | `SCORE_BULLET_NEUTRAL_MIN/MAX` | ±0.05 | ±0.05 | ELO keep | keep (shared); add EG-only registry later |
| EG-only score domain | 3.1.4 | `SCORE_BULLET_DOMAIN` | 0.25 | 0.25 | — | keep |
| Score-gap neutral | 3.1.5 | `SCORE_GAP_NEUTRAL_MIN/MAX` | ±0.10 | ±0.10 | TC review, ELO collapse | keep |
| Score-gap domain | 3.1.5 | `SCORE_GAP_DOMAIN` | 0.20 | **0.23** | — | widen to 0.23 |
| Score-timeline Y | 3.1.5 | `SCORE_TIMELINE_Y_DOMAIN` | [20, 80] | [20, 80] | — | keep |
| MG-entry baseline (white) | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | +0.25 | +0.25 | — | keep |
| MG-entry neutral | 2.1 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | ±0.30 | **±0.35** | both review | widen to ±0.35 |
| MG-entry domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | 1.5 | 1.5 | — | keep |
| Conversion neutral (pooled) | 3.2.1 | `FIXED_GAUGE_ZONES.conversion` | [0.65, 0.77] | [0.66, 0.77] | both keep | keep (or stratify per TC) |
| Parity neutral | 3.2.1 | `FIXED_GAUGE_ZONES.parity` | [0.45, 0.55] | [0.44, 0.56] | ELO review | keep |
| Recovery neutral (pooled) | 3.2.1 | `FIXED_GAUGE_ZONES.recovery` | [0.24, 0.36] | [0.24, 0.36] | TC keep | keep (or stratify per TC) |
| Endgame Skill neutral | 3.2.1 | `ENDGAME_SKILL_ZONES` | [0.47, 0.55] | [0.47, 0.55] | ELO keep | keep (already ELO-aware) |
| Clock-pressure threshold | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | 5.0 | 5.0 or 6.0 | both review | keep |
| Net-timeout threshold | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | 5.0 | 5.0 | ELO review | keep |
| Time-pressure Y axis | 3.3.2 | `Y_AXIS_DOMAIN` | [0.2, 0.8] | [0.2, 0.8] | — | keep (TC overlay still recommended) |
| Per-class pawnless conv | 3.4.1 | `PER_CLASS_GAUGE_ZONES.pawnless.conversion` | [0.70, 0.80] | **[0.74, 0.84]** | — | shift up |
| Per-class pawnless recov | 3.4.1 | `PER_CLASS_GAUGE_ZONES.pawnless.recovery` | [0.21, 0.31] | **[0.15, 0.25]** | — | shift down |
| Per-class score-diff bullet | 3.4.1 | `NEUTRAL_ZONE_MIN/MAX` (`EndgameWDLChart`) | ±0.05 | ±0.05 | — | keep |

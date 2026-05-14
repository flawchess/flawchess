# FlawChess Benchmarks — 2026-05-14

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-14T12:16:39Z
- **Population**: 2,415 users / 1,375,544 games / 95,040,660 positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; tc_bucket from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,133 selected users, 1,912 ingested at ~100/cell (one cell at 12)
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1,000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating - user_rating) <= 100`. Applied to every per-game CTE in Chapters 2 and 3. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. Pre-2026-05-03 score-gap / clock / time-pressure numbers are not directly comparable. See `.planning/notes/benchmark-equal-footing-framing.md`.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity). REFAC-02 — the old material-imbalance + 4-ply persistence proxy is gone.
- **Eval coverage**: 99.9996% of qualifying endgame entries have non-NULL eval (767,395 / 767,398).
- **Sparse-cell exclusion**: `(2400, classical)` is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user, pool exhausted). It is still shown in cell-level 5×4 tables with an `n=12*` footnote.
- **Verdict thresholds**: Cohen's d < 0.20 collapse / 0.20–0.50 review / ≥ 0.50 keep separate.
- **Sample floors**: 2.1 / 3.1.2 entry-eval: ≥20 in-domain games per user-color (live `EVAL_CONFIDENCE_MIN_N = 10`, calibration target ≥20). 3.1.3 / 3.1.4 / 3.1.5 / 3.2.1 / 3.3.1: ≥20 EG games/user/cell. 3.1.6 / 3.1.1: ≥30 EG AND ≥30 non-EG games/user. 3.3.2 / 3.4.1: per-cell n ≥ 100 for score, ≥30 for conv/recov. Cohen's d: ≥10 users per marginal level.

## 1. Stratified Sample

### Cell coverage (status='completed' users per cell)

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 100 | 100 | 100 | 100 |
| 1200 | 100 | 100 | 100 | 100 |
| 1600 | 100 | 100 | 100 | 100 |
| 2000 | 100 | 100 | 100 | 100 |
| 2400 | 100 | 100 | 100 | **12*** |

\* sparse — excluded from marginals / pooled / Cohen's d.

### Eval coverage

`first_endgame` games with non-NULL `eval_cp` OR `eval_mate` at entry ply: **767,395 / 767,398 = 99.9996%**. Essentially complete.

### Equal-footing retention

Per the 2026-05-03 retention pattern: mid-ELO cells retain ~85–90% of games after the equal-footing filter, 2400-rapid drops to ~51%, 2400-classical to ~15% (already excluded as sparse). All non-sparse cells clear sample floor on every subchapter below.

---

## 2. Openings

### 2.1 Middlegame-entry eval

#### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `EVAL_NEUTRAL_MIN_PAWNS` / `MAX_PAWNS` | −0.30 / +0.30 | `frontend/src/lib/openingStatsZones.ts` |
| `EVAL_BULLET_DOMAIN_PAWNS` | 1.5 | same |
| `EVAL_BASELINE_PAWNS_WHITE` / `BLACK` | +0.25 / −0.25 (symmetric ✓) | `app/services/opening_insights_constants.py` |
| `EVAL_CONFIDENCE_MIN_N` | 10 (calibration target ≥20) | same |
| `EVAL_OUTLIER_TRIM_CP` | 2000 | same |

#### Symmetric baseline (pass 1, deduped game-level, white-POV)

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 1,246,674 | **+25 cp** | +24 cp | 238 cp |

Black baseline = −25 cp by construction.

#### Centered pooled distribution (pass 2, excl sparse, ≥20 games/user-color)

| n | ctr_mean | p05 | p25 | p50 | p75 | p95 | SD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3,496 | +4 cp | −94 cp | **−21 cp** | +7 cp | **+34 cp** | +86 cp | 58 cp |

TC marginal (centered means): bullet **−5 cp** / blitz **+3 cp** / rapid **+10 cp** / classical **+12 cp**
ELO marginal (centered means): 800 **−7 cp** / 1200 **+7 cp** / 1600 **+6 cp** / 2000 **+8 cp** / 2400 **+6 cp**

#### Collapse verdict

- **TC axis**: max |d| = **0.25** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.23** (800 vs 2000) → **review**

#### Recommendations

- **Baseline constant**: measured **+25 cp** ≡ live `EVAL_BASELINE_PAWNS_WHITE = 0.25`. **Keep**.
- **Neutral-zone bounds**: pooled centered IQR `[−21, +34] cp` = `[−0.21, +0.34] pawns`. Rounded symmetric to nearest 5 cp → **±35 cp = ±0.35 pawns**. Live ±0.30 pawns is slightly tighter than pooled IQR; recommend **widening to ±0.35 pawns**.
- **Domain**: pooled `[p05, p95]` = `[−94, +86] cp` = `[−0.94, +0.86] pawns`. Live ±1.5 pawns is wider than cohort tails — **keep** (retains outlier margin).

---

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

Per-user `non_eg_score = (W + 0.5·D) / total` over games that do NOT reach the 6-ply endgame floor. Reuses 3.1.6's `per_user` aggregation (no separate query). Sample floor inherited from 3.1.6: ≥30 EG AND ≥30 non-EG games/user.

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `SCORE_BULLET_CENTER` | 0.5 | `frontend/src/lib/scoreBulletConfig.ts` |
| `SCORE_BULLET_NEUTRAL_MIN` / `MAX` | −0.05 / +0.05 | same |
| `SCORE_BULLET_DOMAIN` | 0.25 | same |

Shared with the Openings score bullet.

##### 5×4 cell table — per-user `non_eg_p50 (n_users)`

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 50.4% (97) | 50.0% (97) | 51.4% (94) | 55.1% (24) |
| 1200 | 51.6% (97) | 51.5% (99) | 51.6% (98) | 55.4% (51) |
| 1600 | 50.9% (97) | 50.5% (99) | 51.1% (100) | 54.4% (66) |
| 2000 | 52.3% (100) | 52.9% (98) | 53.5% (95) | 56.0% (49) |
| 2400 | 51.0% (98) | 55.6% (96) | 56.0% (77) | 53.0% (1)* |

##### TC marginal (excl sparse)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 489 | 51.2% | 37.1% | 46.5% | 51.3% | 55.6% | 64.0% |
| blitz | 489 | 52.0% | 39.2% | 46.5% | 51.9% | 56.9% | 65.4% |
| rapid | 464 | 52.7% | 39.9% | 47.2% | 52.7% | 57.8% | 67.1% |
| classical | 190 | 55.7% | 38.8% | 48.9% | 54.9% | 62.9% | 72.4% |

##### ELO marginal (excl sparse)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 312 | 50.5% | 38.0% | 46.3% | 50.6% | 55.0% | 62.0% |
| 1200 | 345 | 52.2% | 39.2% | 46.9% | 51.7% | 56.7% | 66.0% |
| 1600 | 362 | 51.6% | 38.6% | 45.5% | 51.3% | 56.5% | 67.3% |
| 2000 | 342 | 53.4% | 40.4% | 47.6% | 53.3% | 58.3% | 68.0% |
| 2400 | 271 | 54.6% | 38.5% | 48.5% | 54.7% | 60.3% | 70.8% |

##### Pooled (excl sparse)

| n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,632 | 52.4% | 38.9% | 46.8% | 52.1% | 57.4% | 67.3% |

##### Collapse verdict

- **TC axis**: max |d| = **0.50** (bullet vs classical) → **keep separate (boundary)**
- **ELO axis**: max |d| = **0.49** (800 vs 2400) → **review (boundary)**

Heatmap of per-user `non_eg_p50` (%):

```
           bullet   blitz   rapid   classical
  800       50.4    50.0    51.4    55.1
  1200      51.6    51.5    51.6    55.4
  1600      50.9    50.5    51.1    54.4
  2000      52.3    52.9    53.5    56.0
  2400      51.0    55.6    56.0    53.0*
```

##### Recommendations

- **Cohort neutral band** (pooled IQR `[46.8%, 57.4%]`) is wider than the live `±5pp` band on both sides — classical 2400 sits at +5–8pp above the bullet/blitz median. The shared `SCORE_BULLET_NEUTRAL_*` constant should **stay at ±5pp** (mirrors Openings score-bullet baseline), but the non-EG tile would meaningfully benefit from a dedicated `NON_ENDGAME_SCORE_ZONES` module that follows the per-TC shape (classical mid ≈ 55%, bullet/blitz ≈ 51%).
- **Cohort domain**: pooled `[p05, p95]` = `[38.9%, 67.3%]` (half-width ≈ 0.14). Live `±0.25` is wider than pooled — **keep**.
- **Sanity check on equal-footing filter**: pooled mean = 52.4% sits **+2.4pp** above the chess fairness null of 50%. Higher than 3.1.4's +1.2pp and 3.1.3's +0.9pp — non-EG games carry a slightly larger benchmark skill edge than EG-reaching games. Within tolerance but flag if subsequent dumps drift further.
- **TC effect newly significant**: 2026-05-12 reported TC d_max = 0.27 for the *EG-only* score and "review" for the *score gap*. For the *non-EG* score the bullet-vs-classical d hits 0.50 at the keep/review boundary, driven by classical's mean drift from blitz +51.9% to classical +54.9%. Worth a dedicated band per the routing note above.

#### 3.1.2 Endgame-entry eval (pawns)

#### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS` / `MAX_PAWNS` | −0.75 / +0.75 | `frontend/src/lib/endgameEntryEvalZones.ts` |
| `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | 2.25 | same |
| `ENDGAME_ENTRY_EVAL_CENTER` | 0 | same |

#### Symmetric baseline (pass 1, reference only — live tile is 0-centered)

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 801,065 | **+10 cp** | 0 cp | 443 cp |

EG baseline is much smaller than MG (+10 vs +25 cp) — piece trades dissipate engine tempo. Black baseline = −10 cp by construction.

#### Uncentered pooled distribution (pass 2, excl sparse, ≥20 games/user-color)

| n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3,304 | +9 cp | −186 cp | **−56 cp** | +10 cp | **+75 cp** | +199 cp | 117 cp |

TC marginal (uncentered means): bullet **−6 cp** / blitz **+14 cp** / rapid **+21 cp** / classical **+5 cp**
ELO marginal: 800 **−15 cp** / 1200 **+2 cp** / 1600 **+15 cp** / 2000 **+21 cp** / 2400 **+22 cp**

#### Centered pooled (reference, for Cohen's d / parity with 2.1)

| n | ctr_mean | p25 | p50 | p75 | SD |
|---:|---:|---:|---:|---:|---:|
| 3,304 | +9 cp | −54 cp | +11 cp | +75 cp | 117 cp |

#### Collapse verdict (centered)

- **TC axis**: max |d| = **0.22** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.28** (800 vs 2400) → **review**

#### Recommendations

Calibration reads off the **uncentered** distribution (live tile is 0-centered).

- **Neutral band**: pooled uncentered IQR `[−56, +75] cp` = `[−0.56, +0.75] pawns`. Live `±0.75` matches the upper bound exactly; lower bound is wider than pooled p25. Editorial tightening could compress to **±0.55 pawns** (matches pooled p25 magnitude); live ±0.75 stays acceptable since the band is meant to be conservative on the danger side. **Keep ±0.75** for this cycle (no UI argument for tightening yet).
- **Domain**: pooled `[p05, p95]` = `[−186, +199] cp` = `[−1.86, +1.99] pawns`. Live ±2.25 pawns slightly wider — **keep**.
- **Center**: pooled uncentered mean = **+9 cp ≈ +0.09 pawns**, within ±10 cp of 0 → **keep `ENDGAME_ENTRY_EVAL_CENTER = 0`**.

#### 3.1.3 Achievable Score (Stockfish-predicted expected score at EG entry)

Per-user `entry_xs = avg(P(win | eval at first endgame ply))` via Lichess sigmoid. Sample floor ≥20 EG-entry games/user.

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN` | 0.45 | `frontend/src/generated/endgameZones.ts` |
| `ENTRY_EXPECTED_SCORE_NEUTRAL_MAX` | 0.55 | same |

##### 5×4 cell table — per-user `xs_p50 (n_users)`

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 49.5% (99) | 49.4% (100) | 49.8% (96) | 47.7% (41) |
| 1200 | 48.6% (100) | 51.3% (99) | 50.6% (100) | 51.9% (72) |
| 1600 | 49.2% (100) | 52.1% (100) | 51.7% (100) | 50.8% (85) |
| 2000 | 50.3% (100) | 51.7% (100) | 52.4% (98) | 51.8% (66) |
| 2400 | 50.5% (100) | 51.1% (100) | 51.7% (95) | 65.3% (2)* |

##### TC marginal (excl sparse)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 499 | 50.0% | 35.9% | 44.8% | 50.1% | 55.3% | 64.7% |
| blitz | 499 | 51.1% | 41.0% | 47.1% | 51.2% | 54.8% | 62.4% |
| rapid | 489 | 51.7% | 40.7% | 47.3% | 51.5% | 56.1% | 63.3% |
| classical | 264 | 51.0% | 36.4% | 45.6% | 50.9% | 56.3% | 66.9% |

##### ELO marginal (excl sparse)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 49.6% | 32.5% | 42.0% | 49.3% | 56.0% | 68.4% |
| 1200 | 371 | 50.8% | 36.6% | 45.1% | 50.4% | 56.2% | 67.1% |
| 1600 | 385 | 51.3% | 40.6% | 46.9% | 51.2% | 56.1% | 63.3% |
| 2000 | 364 | 51.6% | 42.1% | 47.9% | 51.6% | 55.5% | 60.7% |
| 2400 | 295 | 51.4% | 44.3% | 48.5% | 51.2% | 54.1% | 59.9% |

##### Pooled (excl sparse)

| n | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,751 | 50.9% | 38.2% | **46.3%** | 51.0% | **55.4%** | 64.1% |

##### Collapse verdict

- **TC axis**: max |d| = **0.22** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.23** (800 vs 2000) → **review**

Heatmap of per-user `xs_p50` (%):

```
           bullet   blitz   rapid   classical
  800       49.5    49.4    49.8    47.7
  1200      48.6    51.3    50.6    51.9
  1600      49.2    52.1    51.7    50.8
  2000      50.3    51.7    52.4    51.8
  2400      50.5    51.1    51.7    65.3*
```

##### Recommendations

- **Sanity check**: pooled mean = **50.9%** (+0.9pp above 50%). Small benchmark skill edge within tolerance.
- **Cohort neutral band**: pooled IQR `[46.3%, 55.4%]` ≈ `[0.46, 0.55]`. Live `[0.45, 0.55]` matches the upper bound and is slightly wider on the lower side. **Keep live values** — IQR fits within rounding tolerance.
- **No stratification recommended**: both axes in 0.20–0.25 review tier, near collapse.

#### 3.1.4 Endgame Score (per-user, EG-only)

Per-user `eg_score = (W + 0.5·D) / total_eg_games` over endgame-reaching games. Sample floor ≥20 EG games/user.

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `SCORE_BULLET_CENTER` | 0.5 | `frontend/src/lib/scoreBulletConfig.ts` |
| `SCORE_BULLET_NEUTRAL_MIN` / `MAX` | −0.05 / +0.05 | same |
| `SCORE_BULLET_DOMAIN` | 0.25 (half-width) | same |

Shared with the Openings score bullet and §3.1.1.

##### 5×4 cell table — per-user `eg_p50 (n_users)`

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 47.3% (99) | 47.8% (100) | 49.0% (96) | 43.9% (41) |
| 1200 | 49.2% (100) | 48.1% (99) | 51.3% (100) | 51.2% (72) |
| 1600 | 49.9% (100) | 50.4% (100) | 51.7% (100) | 50.0% (85) |
| 2000 | 50.6% (100) | 52.8% (100) | 52.2% (98) | 53.6% (66) |
| 2400 | 52.4% (100) | 54.1% (100) | 54.8% (95) | 77.4% (2)* |

##### TC marginal (excl sparse)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 499 | 50.3% | 40.6% | 46.1% | 50.0% | 53.9% | 61.6% |
| blitz | 499 | 51.3% | 40.9% | 46.8% | 51.1% | 55.8% | 62.7% |
| rapid | 489 | 52.3% | 39.8% | 47.1% | 52.2% | 56.9% | 66.8% |
| classical | 264 | 50.7% | 33.3% | 43.9% | 50.4% | 57.5% | 66.5% |

##### ELO marginal (excl sparse)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | 47.9% | 34.0% | 42.3% | 47.4% | 52.3% | 64.0% |
| 1200 | 371 | 50.5% | 37.7% | 44.9% | 49.3% | 55.0% | 64.6% |
| 1600 | 385 | 51.1% | 40.0% | 46.2% | 50.4% | 55.4% | 63.9% |
| 2000 | 364 | 52.5% | 42.7% | 48.9% | 52.1% | 56.0% | 63.0% |
| 2400 | 295 | 54.6% | 45.1% | 50.4% | 53.9% | 58.1% | 66.1% |

##### Pooled (excl sparse)

| n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,751 | 51.2% | 39.3% | 46.3% | 50.9% | 55.8% | 64.4% |

##### Collapse verdict

- **TC axis**: max |d| = **0.27** (bullet vs rapid) → **review**
- **ELO axis**: max |d| = **0.84** (800 vs 2400) → **keep separate**

Heatmap of per-user `eg_p50` (%):

```
           bullet   blitz   rapid   classical
  800       47.3    47.8    49.0    43.9
  1200      49.2    48.1    51.3    51.2
  1600      49.9    50.4    51.7    50.0
  2000      50.6    52.8    52.2    53.6
  2400      52.4    54.1    54.8    77.4*
```

##### Recommendations

- **Pooled mean = 51.2%** is +1.2pp above the chess fairness null of 50% — within expected benchmark skill edge.
- **Cohort neutral band**: pooled IQR `[46.3%, 55.8%]`. Live `[0.45, 0.55]` ≈ `[45%, 55%]` — within rounding tolerance. **Keep ±5pp on the shared score bullet**.
- **Cohort domain** (pooled `[p05, p95]`): `[39.3%, 64.4%]` (half-width ≈ 0.13). Live ±0.25 is wider than pooled — **keep**.
- **ELO stratification recommended**: ELO p50 spreads 47.4% → 53.9% across cohorts (6.5pp, wider than the ±5pp IQR width on the bullet). The shared score bullet stays as-is, but the EG-only tile should consider a dedicated `ENDGAME_SCORE_ZONES` per-ELO registry (mirroring `ENDGAME_SKILL_ZONES`). Until then, document the 6.5pp expected drift.

#### 3.1.5 Achievable Score Gap

Per-user `achievable_score_gap = mean(actual_i − expected_i)` over the user's paired (actual, expected) games at EG entry. Mate INCLUDED; `|eval_cp| >= 2000` clipped. Sample floor ≥20 paired games/user.

##### Currently set in code

| Constant | Live value | File |
|---|---:|---|
| `SCORE_GAP_NEUTRAL_MIN` / `MAX` | −0.10 / +0.10 | `frontend/src/generated/endgameZones.ts` |
| `SCORE_GAP_DOMAIN` | 0.20 | `frontend/src/components/charts/EndgameOverallShared.ts` |
| `PVALUE_RELIABILITY_MIN_N` | 10 | `app/services/endgame_service.py` |
| `EVAL_CLIP_MAX_CP` | 2000 | same |

Live gauge centered at 0 (engine-alignment null). Achievable Score Gap shares the `SCORE_GAP_*` constants with Endgame Score Gap (§3.1.6) by design — both rows in the same row of the Score Differences card.

##### 5×4 cell table — per-user `gap_p50 (n_users)` rendered as pp

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | −0.3pp (99) | −1.1pp (100) | −1.2pp (96) | −4.1pp (41) |
| 1200 | +0.3pp (100) | −0.3pp (99) | −0.7pp (100) | −1.1pp (72) |
| 1600 | +0.7pp (100) | +0.0pp (100) | +0.8pp (100) | +0.5pp (85) |
| 2000 | +0.4pp (100) | +1.0pp (100) | +0.8pp (98) | +2.0pp (66) |
| 2400 | +3.4pp (100) | +4.3pp (100) | +3.5pp (95) | +12.1pp (2)* |

##### TC marginal (excl sparse)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 499 | +0.4pp | −18.5pp | −5.5pp | +1.3pp | +6.7pp | +14.8pp |
| blitz | 499 | +0.2pp | −10.5pp | −3.8pp | +0.7pp | +4.4pp | +9.9pp |
| rapid | 489 | +0.6pp | −8.1pp | −2.6pp | +0.7pp | +4.1pp | +10.4pp |
| classical | 264 | −0.3pp | −10.7pp | −4.7pp | −0.1pp | +3.9pp | +10.7pp |

##### ELO marginal (excl sparse)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 336 | −1.7pp | −17.3pp | −7.0pp | −1.3pp | +4.0pp | +11.7pp |
| 1200 | 371 | −0.3pp | −11.7pp | −4.7pp | −0.6pp | +3.5pp | +13.0pp |
| 1600 | 385 | −0.2pp | −12.4pp | −3.8pp | +0.5pp | +3.8pp | +9.9pp |
| 2000 | 364 | +1.0pp | −11.1pp | −2.7pp | +1.2pp | +4.8pp | +11.5pp |
| 2400 | 295 | +3.2pp | −6.5pp | −0.5pp | +3.5pp | +7.3pp | +13.1pp |

##### Pooled (excl sparse)

| n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,751 | +0.3pp | −12.4pp | **−3.9pp** | +0.7pp | **+4.6pp** | +11.6pp |

##### Collapse verdict

- **TC axis**: max |d| = **0.15** (rapid vs classical) → **collapse**
- **ELO axis**: max |d| = **0.62** (800 vs 2400) → **keep separate**

Heatmap of per-user `gap_p50` (pp):

```
           bullet   blitz   rapid   classical
  800       -0.3    -1.1    -1.2    -4.1
  1200      +0.3    -0.3    -0.7    -1.1
  1600      +0.7    +0.0    +0.8    +0.5
  2000      +0.4    +1.0    +0.8    +2.0
  2400      +3.4    +4.3    +3.5    +12.1*
```

##### Recommendations

- **Sanity check on engine alignment**: pooled mean = **+0.3pp** — within ±1pp of 0. No model-calibration concern.
- **Cohort neutral band**: pooled IQR `[−3.9pp, +4.6pp]` is **substantially narrower** than the live `±10pp` band. Asymmetric tilt (+0.7pp median) is below the sub-5pp re-centering guard, so keep symmetric. Recommend **tightening to ±5pp** so the gauge actually paints red/green for the 2400 cohort (whose median sits at +3.5pp, currently rendered as "typical" by the wide band). The 800-cohort lower tail (−7pp p25) also lands in danger correctly under the tighter band.
- **Cohort domain**: pooled `[p05, p95]` = `[−12.4pp, +11.6pp]`. Half-width = 12.4pp vs live `SCORE_GAP_DOMAIN = 0.20` (= ±20pp). Live is wider than cohort tails — **keep** (the 800-bullet tail at −20.6pp still needs to render). Note this constant is shared with §3.1.6 — keep at 0.20 even if 3.1.6 wants 0.23 (it doesn't this cycle).
- **ELO stratification strongly indicated**: ELO d_max = 0.62 (keep), with the 800-cohort gap median at −1.3pp and the 2400-cohort at +3.5pp. The Achievable Score Gap is the metric where strong-cohort users systematically outperform Stockfish's expected score at entry — well-known phenomenon and worth a per-ELO `ACHIEVABLE_SCORE_GAP_ZONES` registry if the tile is meant to paint cohort-aware feedback. Without per-ELO bands, the recommended ±5pp pooled band still works as a single global setting.

**Routing note**: the live SCORE_GAP_* constants are shared with §3.1.6 — see "Recommended thresholds summary" for the dual-row impact. If the implementer agrees the tighter band reflects both metrics, the single shared constant can move from ±0.10 → ±0.05. If only one row should tighten, a split into `ACHIEVABLE_SCORE_GAP_*` (distinct module) is needed.

#### 3.1.6 Endgame Score Gap and Timeline

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
| 800 | −3.6pp (97) | −2.4pp (97) | −2.3pp (94) | −13.4pp (24) |
| 1200 | −4.0pp (97) | −3.2pp (99) | +0.8pp (98) | −5.5pp (51) |
| 1600 | −1.7pp (97) | −0.1pp (99) | +0.7pp (100) | −4.8pp (66) |
| 2000 | −1.4pp (100) | +0.5pp (98) | +0.8pp (95) | −1.9pp (49) |
| 2400 | +2.3pp (98) | −0.2pp (96) | −0.9pp (77) | +6.4pp (1)* |

##### TC marginal (excl sparse)

| TC | n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bullet | 489 | −1.0pp | −18.2pp | −9.5pp | −1.8pp | +6.4pp | +19.8pp |
| blitz | 489 | −0.7pp | −19.1pp | −9.3pp | −0.9pp | +6.9pp | +19.5pp |
| rapid | 464 | −0.7pp | −23.2pp | −9.5pp | −0.6pp | +8.2pp | +20.3pp |
| classical | 190 | −5.3pp | −33.7pp | −15.1pp | −4.6pp | +6.5pp | +19.9pp |

##### ELO marginal (excl sparse)

| ELO | n | mean | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 800 | 312 | −2.5pp | −24.2pp | −11.6pp | −3.6pp | +5.3pp | +21.9pp |
| 1200 | 345 | −2.1pp | −23.7pp | −11.2pp | −3.1pp | +7.2pp | +21.2pp |
| 1600 | 362 | −0.7pp | −23.1pp | −10.3pp | −0.9pp | +9.4pp | +21.0pp |
| 2000 | 342 | −1.0pp | −20.6pp | −8.8pp | −0.4pp | +6.8pp | +16.4pp |
| 2400 | 271 | −0.4pp | −19.7pp | −8.2pp | +0.1pp | +7.4pp | +16.7pp |

##### Pooled (excl sparse)

| n | mean | p05 | p25 | p50 | p75 | p95 | eg_mean | non_eg_mean |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,632 | −1.3pp | −22.7pp | −10.4pp | −1.4pp | +7.3pp | +20.2pp | 51.1% | 52.4% |

##### Collapse verdict

- **TC axis**: max |d| = **0.34** (blitz vs classical) → **review**
- **ELO axis**: max |d| = **0.17** (800 vs 2400) → **collapse**

Heatmap of per-user `diff_p50` (pp):

```
           bullet   blitz   rapid   classical
  800       -3.6    -2.4    -2.3    -13.4
  1200      -4.0    -3.2    +0.8    -5.5
  1600      -1.7    -0.1    +0.7    -4.8
  2000      -1.4    +0.5    +0.8    -1.9
  2400      +2.3    -0.2    -0.9    +6.4*
```

##### Recommendations

- **Score-gap neutral zone**: pooled IQR `[−10.4pp, +7.3pp]`. Median = −1.4pp (well under the 5pp out-of-scope guard for re-centering). Asymmetric tilt is small. The current ±10pp band is consistent with the lower bound but wider than the upper IQR. **Keep symmetric ±10pp** for stand-alone calibration of 3.1.6 — but see the cross-row note in §3.1.5: if both rows agree on tightening, ±5pp is closer to both pooled IQRs. **Status**: relative strength/weakness gauge; framing should describe the gap as cohort-relative rather than absolute (per commit 5a855400). Until the achievable-gap calibration triggers a registry split, **keep ±10pp**.
- **Score-gap domain**: pooled `[p05, p95]` = `[−22.7pp, +20.2pp]`. Half-width 22.7pp vs live 20pp — recommend **widening `SCORE_GAP_DOMAIN` to 0.23** so extreme bullet/classical users don't clip. (Same recommendation as 2026-05-12.)
- **Timeline Y-axis**: pooled eg_mean=51.1%, non_eg_mean=52.4%. Live `[20, 80]` easily encloses cohort behavior — **keep**.
- **TC split**: classical's `diff_mean = −5.3pp` is the only TC with meaningful mean drift (others within ±1pp). Per "review" verdict — no immediate action; revisit if user feedback shows classical-only complaints.

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
| `NEUTRAL_ZONE_MIN` / `MAX` (score-diff bullet, §2 file) | −0.05 / +0.05 | `EndgameScoreGapSection.tsx` |
| `BULLET_DOMAIN` | 0.20 | same |

##### Conversion

5×4 cell table — per-user `conv_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 59.7% (99) | 70.1% (100) | 71.4% (96) | 71.4% (41) |
| 1200 | 62.5% (100) | 70.9% (99) | 73.4% (100) | 75.0% (72) |
| 1600 | 65.9% (100) | 71.2% (100) | 74.7% (100) | 77.6% (85) |
| 2000 | 67.2% (100) | 72.6% (100) | 74.9% (98) | 77.4% (66) |
| 2400 | 71.3% (100) | 74.4% (100) | 77.8% (95) | 79.4% (2)* |

TC marginal (mean): bullet **65.1%** / blitz **71.6%** / rapid **74.3%** / classical **75.6%**
ELO marginal (mean): 800 **66.8%** / 1200 **70.3%** / 1600 **71.7%** / 2000 **72.1%** / 2400 **74.9%**
Pooled: mean **71.1%**, p25/p50/p75 = **65.6% / 71.9% / 76.9%**

**Collapse verdict** — TC d_max = **1.02** (bullet vs classical) → **keep separate**. ELO d_max = **0.82** (800 vs 2400) → **keep separate**.

Recommendation: live neutral `[0.65, 0.77]` ≈ pooled `[0.66, 0.77]` — **keep as pooled default**. A per-TC/per-ELO stratified registry mirroring `ENDGAME_SKILL_ZONES` would meaningfully sharpen feedback (bullet pooled IQR ≈ 58/72 vs classical ≈ 70/83). Worth stratifying.

##### Parity

5×4 cell table — per-user `par_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 50.0% (97) | 47.9% (100) | 50.0% (96) | 38.5% (39) |
| 1200 | 49.0% (100) | 48.9% (99) | 48.7% (100) | 50.0% (72) |
| 1600 | 51.5% (100) | 50.0% (100) | 50.0% (100) | 50.0% (85) |
| 2000 | 49.9% (100) | 51.3% (100) | 51.9% (98) | 52.1% (66) |
| 2400 | 52.2% (100) | 55.2% (100) | 54.0% (95) | 71.2% (2)* |

TC marginal: bullet **50.4%** / blitz **50.2%** / rapid **50.8%** / classical **49.1%**
ELO marginal: 800 **47.0%** / 1200 **49.9%** / 1600 **49.7%** / 2000 **51.4%** / 2400 **53.7%**
Pooled: mean **50.2%**, p25/p50/p75 = **44.3% / 50.0% / 56.3%**

**Collapse verdict** — TC d_max = **0.12** → **collapse**. ELO d_max = **0.48** (800 vs 2400) → **review**.

Recommendation: live `[0.45, 0.55]` matches pooled IQR exactly — **keep**. ELO ramp is borderline meaningful (47% → 54% across cohorts); revisit if domain experts complain that 2400 users see "typical" when they're outperforming the parity median.

##### Recovery

5×4 cell table — per-user `recov_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 35.4% (99) | 29.0% (100) | 25.8% (96) | 20.3% (41) |
| 1200 | 36.5% (100) | 29.0% (99) | 28.6% (99) | 22.6% (72) |
| 1600 | 34.0% (100) | 28.7% (100) | 26.9% (100) | 22.2% (85) |
| 2000 | 34.4% (100) | 33.0% (100) | 26.4% (98) | 27.2% (66) |
| 2400 | 34.6% (100) | 31.7% (100) | 30.0% (95) | 25.0% (2)* |

TC marginal: bullet **35.6%** / blitz **30.3%** / rapid **28.6%** / classical **25.0%**
ELO marginal: 800 **29.7%** / 1200 **30.0%** / 1600 **29.3%** / 2000 **31.1%** / 2400 **33.0%**
Pooled: mean **30.5%**, p25/p50/p75 = **24.3% / 30.1% / 36.4%**

**Collapse verdict** — TC d_max = **1.10** (bullet vs classical) → **keep separate**. ELO d_max = **0.40** → **review**.

Recommendation: live `[0.24, 0.36]` matches pooled IQR exactly — **keep**. TC ramp is huge (bullet 35% → classical 25%) — a per-TC registry would sharpen feedback. Worth a stratified band.

##### Endgame Skill (composite)

5×4 cell table — per-user `skill_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | 48.1% (99) | 49.7% (100) | 49.3% (96) | 43.8% (41) |
| 1200 | 49.2% (100) | 49.6% (99) | 50.8% (100) | 49.6% (72) |
| 1600 | 50.9% (100) | 50.1% (100) | 50.7% (100) | 51.6% (85) |
| 2000 | 50.6% (100) | 52.1% (100) | 51.2% (98) | 52.3% (66) |
| 2400 | 52.8% (100) | 54.3% (100) | 54.4% (95) | 58.5% (2)* |

TC marginal: bullet **50.4%** / blitz **50.7%** / rapid **51.3%** / classical **49.9%**
ELO marginal: 800 **47.8%** / 1200 **50.1%** / 1600 **50.2%** / 2000 **51.5%** / 2400 **53.9%**
Pooled: mean **50.6%**, p25/p50/p75 = **46.6% / 50.8% / 54.8%**

**Collapse verdict** — TC d_max = **0.18** → **collapse**. ELO d_max = **0.78** (800 vs 2400) → **keep separate**.

Recommendation: live `[0.47, 0.55]` matches pooled `[0.47, 0.55]` exactly — **keep as pooled**. ELO stratification still strongly indicated; current `ENDGAME_SKILL_ZONES` registry already serves this.

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
| 800 | −0.7% (98) | −0.8% (100) | +1.2% (96) | +0.2% (38) |
| 1200 | −0.4% (100) | −0.5% (99) | −0.1% (100) | +1.2% (72) |
| 1600 | −0.2% (99) | −1.7% (100) | −0.1% (100) | −0.2% (85) |
| 2000 | −1.5% (100) | −1.5% (100) | −1.3% (98) | −5.7% (64) |
| 2400 | +0.1% (99) | −0.0% (100) | −3.3% (95) | +4.3% (2)* |

TC marginal (mean): bullet **−0.2%** / blitz **−1.4%** / rapid **−1.5%** / classical **−2.7%**
ELO marginal: 800 **−1.1%** / 1200 **−1.2%** / 1600 **−1.4%** / 2000 **−2.2%** / 2400 **−0.3%**
Pooled: p25/p50/p75 = **−6.4% / −0.5% / +4.7%**

**Collapse verdict** — TC d_max = **0.23** (bullet vs classical) → **review**. ELO d_max = **0.21** (2000 vs 2400) → **review**.

Recommendation: pooled IQR slightly asymmetric (`[−6.4%, +4.7%]`). Live ±5% is close but the lower tail is wider — **widen to ±6%** if narrative emphasis warrants, otherwise keep. TC ramp is mild; per-TC split not required.

##### Net timeout rate (timeout_wins − timeout_losses per game, %)

5×4 cell table — per-user `net_p50 (n_users)`:

| ELO ↓ \ TC → | bullet | blitz | rapid | classical |
|---|---:|---:|---:|---:|
| 800 | −5.3pp | −0.3pp | +1.3pp | 0.0pp |
| 1200 | −0.6pp | +2.0pp | +1.2pp | 0.0pp |
| 1600 | +2.0pp | +1.1pp | +2.0pp | 0.0pp |
| 2000 | +2.2pp | +2.2pp | +2.0pp | +0.6pp |
| 2400 | +5.5pp | +2.0pp | +2.4pp | 0.0pp (2)* |

TC marginal (mean): bullet **+0.4pp** / blitz **−0.0pp** / rapid **+0.2pp** / classical **−0.3pp**
ELO marginal: 800 **−2.0pp** / 1200 **−0.3pp** / 1600 **−0.2pp** / 2000 **+0.6pp** / 2400 **+2.8pp**
Pooled: p25/p50/p75 = **−4.4pp / +1.0pp / +5.6pp**

**Collapse verdict** — TC d_max = **0.07** → **collapse**. ELO d_max = **0.41** (800 vs 2400) → **review**.

Recommendation: pooled IQR `[−4.4pp, +5.6pp]`. Live ±5pp fits reasonably. **Keep**. ELO ramp is real (800 nets −2.0pp / 2400 nets +2.8pp) — strong-cohort users net flag opponents. The "typical" band centered on 0 still reads cleanly across cohorts.

#### 3.3.2 Time pressure vs performance

Per (TC × time-bucket) curves. Time bucket 0 = 0–10% time remaining (max pressure); 9 = 90–100% (min pressure). Per-cell pooled score (not per-user).

##### TC marginals — pooled across ELO (excl sparse)

| Time bucket | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 0 (max pressure) | 26.0% | 33.4% | 33.8% | 41.0% |
| 1 | 39.9% | 43.7% | 44.1% | 45.2% |
| 2 | 49.1% | 49.2% | 46.9% | 46.8% |
| 3 | 53.0% | 51.8% | 50.7% | 47.5% |
| 4 | 55.2% | 53.4% | 53.2% | 47.8% |
| 5 | 56.4% | 54.8% | 53.3% | 48.7% |
| 6 | 56.3% | 54.4% | 52.9% | 50.5% |
| 7 | 55.3% | 54.2% | 52.3% | 51.0% |
| 8 | 54.2% | 53.4% | 52.4% | 50.2% |
| 9 (min pressure) | 50.0% | 52.3% | 52.4% | 51.0% |

bullet/blitz show strong pressure penalty (26% → 56%); classical curve is flat (41% → 51%). Classical "0–10% time" is still many seconds of thinking; bullet "0–10%" is sudden death.

##### ELO marginals — pooled across TC (excl sparse)

| Time bucket | 800 | 1200 | 1600 | 2000 | 2400 |
|---:|---:|---:|---:|---:|---:|
| 0 | 26.6% | 28.3% | 30.4% | 33.2% | 33.6% |
| 3 | 51.1% | 51.2% | 51.6% | 52.5% | 53.8% |
| 5 | 53.8% | 53.2% | 53.7% | 56.3% | 57.5% |
| 9 | 49.0% | 50.1% | 53.7% | 54.7% | 56.4% |

Higher ELO → flatter/higher curve (better at all pressure levels).

##### Collapse verdict (per-bucket Cohen's d on per-game binary scores)

- **TC axis**: d_max = **0.34** (bullet vs classical at low-time buckets) → **review**
- **ELO axis**: d_max = **0.17** → **collapse** at the per-game granularity

Caveat: per-game outcome variance dominates (~0.25 per Bernoulli trial). Cohort effects are real and visible in marginals but small relative to single-game noise.

Recommendation: **show TC overlay** in the live curve — the bullet/classical gap is large enough to matter. ELO overlay is optional; can collapse to a single global curve if UI clarity > per-ELO precision.

---

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

##### Currently set in code

| Constant | Live | File |
|---|---|---|
| `SCORE_BULLET_CENTER` | `0.5` | `frontend/src/lib/scoreBulletConfig.ts` |
| `SCORE_BULLET_NEUTRAL_MIN` / `MAX` (per-card Score bullet, global) | `−0.05` / `+0.05` | same |
| `SCORE_BULLET_DOMAIN` | `0.25` | same |
| `PER_CLASS_GAUGE_ZONES.{class}.conversion` / `.recovery` | per `endgameZones.ts` (calibrated 2026-05-01) | `frontend/src/generated/endgameZones.ts` |
| `NEUTRAL_ZONE_MIN/MAX` (legacy score-diff bullet) | DEPRECATED in Phase 87 | n/a (`EndgameWDLChart.tsx` removed) |

##### Pooled-by-class summary (excl sparse cell)

| class | games | users | score | score_diff | conv | recov |
|---|---:|---:|---:|---:|---:|---:|
| rook | 94,087 | 1,845 | 50.8% | +1.5pp | 71.0% | 29.6% |
| minor_piece | 70,381 | 1,825 | 51.0% | +2.0pp | 69.5% | 32.8% |
| pawn | 37,463 | 1,750 | 51.1% | +2.1pp | 73.8% | 27.5% |
| queen | 34,432 | 1,764 | 50.8% | +1.6pp | 77.4% | 23.4% |
| mixed | 529,608 | 1,888 | 50.6% | +1.1pp | 69.4% | 31.1% |
| pawnless | 5,847 | 1,365 | 50.7% | +1.4pp | 79.1% | 19.8% |

##### Per-user per-class chess-score IQR (Phase 87 Score-bullet calibration)

Per-user chess-score (`(W + 0.5·D) / total`) over each (user × class) pair with ≥10 games. Sparse `(2400, classical)` cell excluded. This is the row that drives the per-card Score bullet's neutral-zone calibration in `EndgameTypeCard.tsx`.

| class | n_users | mean | p10 | p25 | p50 | p75 | p90 | IQR width |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rook | 1,533 | 50.4% | 37.5% | 43.9% | 50.0% | 57.1% | 63.5% | 13.2pp |
| minor_piece | 1,417 | 50.5% | 35.7% | 43.3% | 50.8% | 57.8% | 65.0% | 14.5pp |
| pawn | 1,149 | 50.2% | 34.4% | 42.1% | 50.0% | 58.9% | 66.7% | 16.8pp |
| queen | 1,149 | 51.7% | 32.1% | 41.1% | 52.4% | 62.5% | 70.6% | 21.4pp |
| mixed | 1,815 | 51.4% | 41.9% | 46.2% | 50.9% | 56.1% | 61.7% | 9.9pp |
| pawnless | 119 | 43.6% | 25.0% | 30.3% | 40.0% | 54.8% | 68.2% | 24.5pp |

Notable shape:
- **mixed** is the tightest distribution (9.9pp IQR) — close to the global ±5pp band.
- **queen** sits ~1.8pp above 50% and runs wide (21.4pp) — high-variance class where small samples per user dominate.
- **pawnless** is the most distorted: midpoint pulled down to ~42.5% (n_users only 119, since most users don't accumulate ≥10 pawnless games). Treat as suggestive, not actionable.

##### Score (per (ELO × TC × class), suppressed n_games < 100)

All cell-level score_diff values land in `[−22pp, +15pp]`. Pooled per-class score_diff = `+1.1pp..+2.1pp` — within ±5pp.

##### Conversion (suppressed n_conv < 30)

Pooled per-class conversion ranges from 69.4% (mixed) to 79.1% (pawnless). Live `PER_CLASS_GAUGE_ZONES.conversion` neutral midpoints (from `endgameZones.ts`):

| class | live neutral | pooled (this snapshot) | delta |
|---|---|---:|---|
| rook | [0.65, 0.75] | 71.0% | ≈ centered ✓ |
| minor_piece | [0.63, 0.73] | 69.5% | ≈ centered ✓ |
| pawn | [0.67, 0.79] | 73.8% | ≈ centered ✓ |
| queen | [0.73, 0.83] | 77.4% | ≈ centered ✓ |
| mixed | [0.65, 0.75] | 69.4% | ≈ centered ✓ |
| pawnless | [0.70, 0.80] | 79.1% | shifted high — recommend [0.74, 0.84] |

##### Recovery (suppressed n_recov < 30)

| class | live neutral | pooled | delta |
|---|---|---:|---|
| rook | [0.26, 0.36] | 29.6% | ≈ centered ✓ |
| minor_piece | [0.31, 0.41] | 32.8% | ≈ centered ✓ |
| pawn | [0.23, 0.34] | 27.5% | ≈ centered ✓ |
| queen | [0.20, 0.30] | 23.4% | ≈ centered ✓ |
| mixed | [0.28, 0.38] | 31.1% | ≈ centered ✓ |
| pawnless | [0.21, 0.31] | 19.8% | shifted low — recommend [0.15, 0.25] |

##### Recommendations

**Per-card Score bullet (Phase 87 — global vs per-class):**

Skill rule: propose a per-class override if a class's `[p25, p75]` shifts the midpoint by > 1pp from 0.50 OR widens / narrows by > 2pp vs the global `[0.45, 0.55]` band.

| class | midpoint vs 0.50 | width vs 10pp | proposal |
|---|---:|---:|---|
| rook | +0.5pp | +3.2pp wider | per-class `[0.44, 0.57]` |
| minor_piece | +0.6pp | +4.5pp wider | per-class `[0.43, 0.58]` |
| pawn | +0.5pp | +6.8pp wider | per-class `[0.42, 0.59]` |
| queen | **+1.8pp** | +11.4pp wider | per-class `[0.41, 0.63]` |
| mixed | +1.1pp | −0.1pp ≈ | per-class `[0.46, 0.56]` (borderline; could keep global) |
| pawnless | **−7.5pp** | +14.5pp wider | n=119 only — defer, sample too small |

By the rule, every class except (borderline) mixed warrants an override. The practical signal: **per-class IQRs are systematically wider than the global ±5pp band**, because a user's per-class score samples fewer games than their overall EG score. If we keep the global band, almost every user's per-class Score bullet will paint as "outside neutral" on at least one class — bad UX.

Two routes:
1. **Add a `PER_CLASS_SCORE_BULLET_ZONES` registry** in `app/services/endgame_zones.py` (codegen'd to `endgameZones.ts`), consumed in `EndgameTypeCard.tsx` via a lookup analogous to `PER_CLASS_GAUGE_ZONES[class]`. Use the proposals above; defer pawnless until n_users ≥ ~500 (next dump).
2. **Widen the global band to ±7-8pp** to reduce over-painting without per-class infrastructure. Cheaper but less precise — queen and pawnless still mis-painted.

Editorial tightening (memory `feedback_zone_band_judgement.md`): the recommended per-class bands above use raw `[p25, p75]`. If a meaningful effect (e.g. a class where you score 5pp below cohort) needs to paint red/green, tighten inside IQR — but the live IQR widths are already wider than meaningful effects, so raw IQR is the appropriate ceiling here, not the floor.

**Per-class conv/recov gauges:** Live per-class registry is healthy. Two classes drifted vs 2026-05-01 baseline:
- **pawnless conversion**: live midpoint 0.75 vs new pooled 0.79 (~4pp drift up). Suggest shifting to `[0.74, 0.84]`.
- **pawnless recovery**: live midpoint 0.26 vs new pooled 0.20 (~6pp drift down). Suggest shifting to `[0.15, 0.25]`.
- pawnless has the smallest sample (5,847 games / 1,365 users) — drift may also reflect sampling noise. Re-evaluate after the next dump.

**Per-class score_diff:** legacy score-diff bullet was removed in Phase 87 (replaced by the absolute chess-score bullet). The `NEUTRAL_ZONE_MIN/MAX = ±0.05` constant in `EndgameWDLChart.tsx` is deprecated — no live UI surface consumes it.

**Collapse verdicts** for per-(metric × class): per-cell sample sizes show the same ELO ramp pattern observed in §3.2.1 — conversion climbs with ELO, recovery is roughly flat. ELO stratification per class is statistically supported but UI-cost is high. Stick with pooled per-class until users ask for the finer grain.

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| Non-Endgame Score (per-user) | 3.1.1 | **keep (0.50)** | review (0.49) | TC drift driven by classical; dedicated non-EG zone module worth considering |
| Endgame-entry eval (uncentered) | 3.1.2 | review (0.22) | review (0.28) | pooled band fits; 0-center stays |
| Achievable Score | 3.1.3 | review (0.22) | review (0.23) | pooled band fits live [0.45, 0.55] |
| Endgame Score (per-user, EG-only) | 3.1.4 | review (0.27) | **keep (0.84)** | ELO stratification justified for EG-only score band |
| Achievable Score Gap (actual − expected) | 3.1.5 | collapse (0.15) | **keep (0.62)** | strong ELO ramp; tighten neutral band; consider per-ELO registry |
| Endgame Score Gap (eg − non_eg) | 3.1.6 | review (0.34) | collapse (0.17) | classical only TC drifts; single pooled ±10pp OK |
| Middlegame-entry eval (centered) | 2.1 | review (0.25) | review (0.23) | pooled band fits; widen neutral to ±0.35 pawns |
| Conversion (per-user) | 3.2.1 | **keep (1.02)** | **keep (0.82)** | per-cell calibration well justified |
| Parity (per-user) | 3.2.1 | collapse (0.12) | review (0.48) | live [0.45, 0.55] OK; ELO ramp borderline |
| Recovery (per-user) | 3.2.1 | **keep (1.10)** | review (0.40) | per-TC bands warranted |
| Endgame Skill (per-user) | 3.2.1 | collapse (0.18) | **keep (0.78)** | matches live ENDGAME_SKILL_ZONES |
| Clock pressure %-of-base | 3.3.1 | review (0.23) | review (0.21) | single pooled threshold OK |
| Net timeout rate | 3.3.1 | collapse (0.07) | review (0.41) | single pooled threshold OK; strong ELO ramp |
| Time-pressure curve (per-bucket) | 3.3.2 | review (0.34) | collapse (0.17) | TC overlay recommended |
| Per-class score (pooled, by-class) | 3.4.1 | flat across classes | (see 3.2.1) | pooled ±5pp OK |
| Per-class chess-score IQR (per-user) | 3.4.1 | n/a | n/a | global ±5pp band too narrow — add `PER_CLASS_SCORE_BULLET_ZONES` |
| Per-class conversion | 3.4.1 | (see 3.2.1) | (see 3.2.1) | pawnless drift — recalibrate |
| Per-class recovery | 3.4.1 | (see 3.2.1) | (see 3.2.1) | pawnless drift — recalibrate |

---

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| Non-EG score neutral (shared bullet) | 3.1.1 | `SCORE_BULLET_NEUTRAL_MIN/MAX` | ±0.05 | ±0.05 | TC keep, ELO review | keep (shared); add non-EG registry later |
| EG-only score neutral (shared bullet) | 3.1.4 | `SCORE_BULLET_NEUTRAL_MIN/MAX` | ±0.05 | ±0.05 | ELO keep | keep (shared); add EG-only registry later |
| EG-only score domain | 3.1.4 | `SCORE_BULLET_DOMAIN` | 0.25 | 0.25 | — | keep |
| MG-entry baseline (white) | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | +0.25 | +0.25 | — | keep |
| MG-entry neutral | 2.1 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | ±0.30 | **±0.35** | both review | **widen to ±0.35** |
| MG-entry domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | 1.5 | 1.5 | — | keep |
| EG-entry neutral | 3.1.2 | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` | ±0.75 | ±0.75 | both review | keep (or tighten to ±0.55 editorial) |
| EG-entry domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | 2.25 | 2.25 | — | keep |
| EG-entry center | 3.1.2 | `ENDGAME_ENTRY_EVAL_CENTER` | 0 | 0 | — | keep |
| EG-entry expected score | 3.1.3 | `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX` | [0.45, 0.55] | [0.46, 0.55] | both review | keep |
| Achievable Score Gap neutral (shared) | 3.1.5 | `SCORE_GAP_NEUTRAL_MIN/MAX` | ±0.10 | **±0.05** (alt: keep) | TC collapse, ELO keep | **consider tightening** to ±0.05 (or split into a dedicated `ACHIEVABLE_SCORE_GAP_*` module so 3.1.6 keeps ±0.10) |
| Endgame Score Gap neutral (shared) | 3.1.6 | `SCORE_GAP_NEUTRAL_MIN/MAX` | ±0.10 | ±0.10 | TC review, ELO collapse | keep |
| Endgame Score Gap domain (shared) | 3.1.6 | `SCORE_GAP_DOMAIN` | 0.20 | **0.23** | — | **widen to 0.23** |
| Conversion neutral (pooled) | 3.2.1 | `FIXED_GAUGE_ZONES.conversion` | [0.65, 0.77] | [0.66, 0.77] | both keep | keep (or stratify per TC) |
| Parity neutral | 3.2.1 | `FIXED_GAUGE_ZONES.parity` | [0.45, 0.55] | [0.44, 0.56] | ELO review | keep |
| Recovery neutral (pooled) | 3.2.1 | `FIXED_GAUGE_ZONES.recovery` | [0.24, 0.36] | [0.24, 0.36] | TC keep | keep (or stratify per TC) |
| Endgame Skill neutral | 3.2.1 | `ENDGAME_SKILL_ZONES` | [0.47, 0.55] | [0.47, 0.55] | ELO keep | keep (already ELO-aware) |
| Clock-pressure threshold | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | 5.0 | 5.0 or 6.0 | both review | keep |
| Net-timeout threshold | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | 5.0 | 5.0 | ELO review | keep |
| Per-class pawnless conv | 3.4.1 | `PER_CLASS_GAUGE_ZONES.pawnless.conversion` | [0.70, 0.80] | **[0.74, 0.84]** | — | **shift up** |
| Per-class pawnless recov | 3.4.1 | `PER_CLASS_GAUGE_ZONES.pawnless.recovery` | [0.21, 0.31] | **[0.15, 0.25]** | — | **shift down** |
| Per-class Score bullet (rook) | 3.4.1 | `SCORE_BULLET_NEUTRAL_MIN/MAX` (global) | ±0.05 (= [0.45, 0.55]) | **[0.44, 0.57]** | width +3.2pp wider | **add `PER_CLASS_SCORE_BULLET_ZONES`** registry |
| Per-class Score bullet (minor_piece) | 3.4.1 | same | ±0.05 | **[0.43, 0.58]** | width +4.5pp wider | same registry |
| Per-class Score bullet (pawn) | 3.4.1 | same | ±0.05 | **[0.42, 0.59]** | width +6.8pp wider | same registry |
| Per-class Score bullet (queen) | 3.4.1 | same | ±0.05 | **[0.41, 0.63]** | midpoint +1.8pp, width +11.4pp | same registry |
| Per-class Score bullet (mixed) | 3.4.1 | same | ±0.05 | [0.46, 0.56] (≈ global) | borderline | keep global or include in registry |
| Per-class Score bullet (pawnless) | 3.4.1 | same | ±0.05 | defer (n_users=119) | n too small | re-evaluate next dump |

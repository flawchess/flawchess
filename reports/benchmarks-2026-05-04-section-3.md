# FlawChess Benchmarks — 2026-05-04 (§3 only)

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-04T (selection_at MAX = 2026-04-30T21:58Z)
- **Population**: 2,415 users / 1,375,544 games / 95.0M positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; tc_bucket from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump, 9,523 candidate pool, 1,912 `(user, tc)` rows ingested as `status='completed'` (~100/cell except sparse)
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory)
- **Equal-footing filter (universal — all sections)**: `abs(opp_rating - user_rating) <= 100`. Applied to §3 main per-user-mean block. NOT applied to §3 color-split sub-block (calibrating against production-realistic regime, no opponent-strength filter — production z-test runs on the user's actual games).
- **Sparse-cell exclusion**: `(2400, classical)` excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes (n=12 completed users, ~55 games/user). Still shown in cell-level 5×4 tables with `*`.
- **Verdict thresholds**: Cohen's d < 0.2 = collapse / 0.2-0.5 = review / ≥ 0.5 = keep separate
- **Sample floor**: §3 ≥20 in-domain games/user (matches `EVAL_CONFIDENCE_MIN_N = 20` in `opening_insights_constants.py` — same gate live z-test uses); cell shown if ≥10 users
- **METHODOLOGY CHANGE 2026-05-04 — per-user mean, not median**: §3 main block now reports per-user **mean** (signed user-POV `eval_cp`) over the same row set the live z-test consumes (`eval_cp NOT NULL`, `eval_mate IS NULL`, `|eval_cp| < 2000`). The earlier per-user median approach was rejected for definitional consistency with `compute_eval_confidence_bucket` (`mean = eval_sum / n`). Numbers in this section are **not directly comparable** to the per-user-median tables in `benchmarks-2026-05-03.md` §3.

### Cell coverage (status='completed' users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 100 | 100 | 100 | 100 |
| **1200** | 100 | 100 | 100 | 100 |
| **1600** | 100 | 100 | 100 | 100 |
| **2000** | 100 | 100 | 100 | 100 |
| **2400** | 100 | 100 | 100 | 12* |

### Eval coverage at phase entry (after §3 production-aligned filters)

| Phase | Total entries | Mate rows (excluded) | Outliers `\|cp\| ≥ 2000` (excluded) | NULL eval (excluded) | In-domain rows used |
|---|---:|---:|---:|---:|---:|
| Middlegame (`phase=1`) | 1,299,252 | 6,355 (0.49%) | 4 | 0 | 1,292,893 |
| Endgame (`phase=2`)    |   875,463 | 45,335 (5.18%) | 55 | 3 | 830,070 |

Stockfish backfill is essentially complete — middlegame coverage rose from 66% (2026-05-03) to ~99.5% in-domain after the recent backfill; the asymmetric coverage caveat from the prior report is gone. Mate-row prevalence is the only meaningful exclusion.

### Equal-footing retention (% of phase-entry games kept after `|opp − user| ≤ 100`)

**Middlegame entries:**

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 83.5% | 84.9% | 82.3% | 53.5% |
| **1200** | 89.6% | 89.6% | 88.6% | 72.0% |
| **1600** | 85.8% | 89.0% | 88.1% | 71.4% |
| **2000** | 78.3% | 78.5% | 74.1% | 57.9% |
| **2400** | 66.6% | 62.1% | 51.7% | 15.3%* |

**Endgame entries:**

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | 84.5% | 85.5% | 83.1% | 52.9% |
| **1200** | 89.7% | 89.3% | 88.8% | 70.4% |
| **1600** | 85.6% | 89.1% | 88.2% | 72.2% |
| **2000** | 77.7% | 78.3% | 74.4% | 59.1% |
| **2400** | 66.3% | 62.2% | 52.6% | 16.3%* |

Retention is essentially identical to §1/§2/§4/§5/§6 (same per-game CTE pattern). Mid-ELO retains 78–90%. 2400-classical drops to ~15% — already excluded as sparse. **No non-sparse cell drops below per-user sample floors after the 20-game-floor + 10-users-cell-floor.**

---

## 3. Evals at game phase transitions

Per-(user, color) **mean** signed user-POV Stockfish eval (cp) at the first ply of each phase, **centered on the matching color baseline**. Filter: production trim (`eval_cp NOT NULL`, `eval_mate IS NULL`, `|eval_cp| < 2000`) + equal-footing. Sample floor: ≥20 in-domain games per (user, color). Calibrates the bullet-chart in `frontend/src/lib/openingStatsZones.ts`, which displays one cell per (user, opening, color) and applies its zone test on `delta = value − baseline_C`.

### Currently set in code

- **Bullet chart**: `frontend/src/lib/openingStatsZones.ts` — `EVAL_NEUTRAL_MIN_PAWNS = -0.30`, `EVAL_NEUTRAL_MAX_PAWNS = 0.30`, `EVAL_BULLET_DOMAIN_PAWNS = 1.5`. Centers: `EVAL_BASELINE_PAWNS_WHITE = 0.315`, `EVAL_BASELINE_PAWNS_BLACK = -0.189`.
- **Live z-test baselines** (consumed by `eval_confidence.py`): `EVAL_BASELINE_CP_WHITE = 28`, `EVAL_BASELINE_CP_BLACK = -20`, `EVAL_CONFIDENCE_MIN_N = 20` (in `app/services/opening_insights_constants.py:65-74`).

### Phase-entry definitions

Both entry plies come from `game_positions.phase` (SmallInteger, `0=opening / 1=middlegame / 2=endgame`; see `app/models/game_position.py:90-94`). Endgame-entry definition is consistent with §2/§4/§6's `endgame_class IS NOT NULL` thanks to **PHASE-INV-01** (`phase=2 ⟺ endgame_class IS NOT NULL`).

### Why per-(user, color) centered, not pooled-color

The chart applies its zone test on `delta = value − baseline_C` per cell, where the cell is filtered by user color. The right calibration target is the per-(user, color) centered distribution, not pooled-color per-user means. Pooling-then-centering conflates color-mix variance (each user's pooled mean is pulled between +31 and −19 by their game-color split) with the within-color sampling spread the chart actually displays. This report drops the earlier 5×4 cell tables, TC marginals, ELO marginals, and pooled-overall blocks; only the centered per-(user, color) summary and the engine-asymmetry baselines that define the centers remain.

---

### Middlegame-entry eval — color-split engine-asymmetry baselines (game-level)

The live z-test in `eval_confidence.py:104` consumes per-game evals via `mean = eval_sum / n`. This sub-block reports the game-level distribution that defines the per-color centers. Filter: production trim, base filter only (no EF — production runs on user's actual games).

| color | n_games | mean | median | SD | p05 | p95 |
|---|---:|---:|---:|---:|---:|---:|
| white | 624,634 | **+31.53** | +28 | 238.0 | -397 | 462 |
| black | 625,130 | **-18.86** | -20 | 237.3 | -445 | 414 |

**Comparison to live constants** (rule: keep when |measured mean − constant| ≤ 5 cp):

| color | constant | measured mean | gap | recommendation |
|---|---:|---:|---:|---|
| white | `EVAL_BASELINE_CP_WHITE = 28` | +31.53 | +3.5 | **keep** (within 5cp tolerance) |
| black | `EVAL_BASELINE_CP_BLACK = -20` | -18.86 | -1.1 | **keep** (within 5cp tolerance) |

Excess kurtosis ~2.4 motivates `EVAL_CONFIDENCE_MIN_N = 20` (Edgeworth leading-error term on the normal approximation stays under ~2% at N ≥ 20).

### Middlegame-entry eval — centered per-(user, color)

Filter: production trim + EF + ≥20 (user, color) games. Sparse cell `(2400, classical)` excluded. Centered = `(per-(user,color) mean signed cp) − baseline_C`.

| color | n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| white | 1,745 | -1.81 | -102.8 | **-28.6** | +2.2 | **+29.1** | +82.1 | 58.6 |
| black | 1,751 | -2.55 |  -97.8 | **-25.7** | -0.7 | **+26.2** | +78.5 | 57.7 |
| pooled | 3,496 | -2.18 | -100.0 | **-26.8** | +0.6 | **+27.9** | +80.2 | 58.2 |

**Cohen's d (white centered vs black centered) = 0.013** — color collapse, single symmetric zone applies.

#### Collapse verdicts (centered)

| axis | d_max | verdict |
|---|---:|---|
| color | 0.013 | **collapse** |
| TC    | 0.269 | review |
| ELO   | 0.258 | review |

#### Recommendations

- **Neutral zone**: pooled centered `[p25, p75]` = `[−26.8, +27.9]` cp → symmetric **±30 cp (±0.30 pawns)**. Color asymmetry is statistically null (d=0.013); symmetric is correct.
- **Domain**: pooled centered `[p05, p95]` = `[−100, +80]` cp → symmetric **±150 cp (±1.5 pawns)** covers the lower tail with margin.
- **Live z-test baselines stand** — `EVAL_BASELINE_CP_WHITE = 28`, `EVAL_BASELINE_CP_BLACK = -20` are within 5 cp of measured means (+31.5 / −18.9). No code change.
- **Single global zone is correct** — TC and ELO collapse verdicts both "review" but defensible; cohort skill ramp is the natural signal.

---

### Endgame-entry eval — color-split engine-asymmetry baselines (game-level)

| color | n_games | mean | median | SD | p05 | p95 |
|---|---:|---:|---:|---:|---:|---:|
| white | 400,153 | **+23.11** | +9 | 443.1 | -710 | 736 |
| black | 402,909 |  **+3.21** |  0 | 441.7 | -723 | 720 |

White's structural advantage halves by EG entry vs MG (gap 20 cp vs ~50 cp). No live EG-entry constant exists yet; record for Phase 81+: `WHITE_EG ≈ 23`, `BLACK_EG ≈ 3`. A pooled baseline of 0 would be a defensible simplification at EG entry.

### Endgame-entry eval — centered per-(user, color)

Filter: production trim + EF + ≥20 (user, color) games. Sparse cell `(2400, classical)` excluded. Centered = `(per-(user,color) mean signed cp) − baseline_C` with `WHITE = +23.11, BLACK = +3.21`.

| color | n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| white | 1,654 | -3.37 | -199.2 | **-69.1** | +1.2 | **+63.7** | +183.6 | 119.8 |
| black | 1,650 | -5.16 | -193.2 | **-65.7** | -5.3 | **+59.0** | +185.3 | 113.8 |
| pooled | 3,304 | -4.26 | -196.0 | **-66.9** | -2.4 | **+62.2** | +183.8 | 116.8 |

**Cohen's d (white centered vs black centered) ≈ 0.015** — color collapse, single symmetric zone applies.

#### Collapse verdicts (centered)

| axis | d_max | verdict |
|---|---:|---|
| color | 0.015 | **collapse** |
| TC    | 0.229 | review |
| ELO   | 0.314 | review |

#### Recommendations (Phase 81+ — chart not yet built)

- **Neutral zone**: pooled centered `[p25, p75]` = `[−67, +62]` cp → symmetric **±65 cp (±0.65 pawns)**.
- **Domain**: pooled centered `[p05, p95]` = `[−196, +184]` cp → symmetric **±200 cp tight, ±300 cp wide** (800 cohort tail).
- **Center on per-color baselines** (`+23 / +3`) once the EG-entry chart is built, mirroring the MG approach.

---

## Top-axis collapse summary (HEADLINE DELIVERABLE — §3 only)

| Metric | Color (d) | TC (d_max) | ELO (d_max) | Implication |
|---|---|---|---|---|
| Middlegame-entry eval | **collapse (0.013)** | review (0.269) | review (0.258) | Single symmetric zone, color-centered |
| Endgame-entry eval    | **collapse (0.015)** | review (0.229) | review (0.314) | Single symmetric zone, color-centered |

Other §1/§2/§4/§5/§6 metrics: **NOT REFRESHED** in this run — see `benchmarks-2026-05-03.md`.

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended | Action |
|---|---|---|---|---|
| MG-entry eval — neutral zone | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.25` (pre-color-split) | **`±0.30` pawns (±30 cp)** — pooled centered `[p25, p75]` = `[−27, +28]` | **update** |
| MG-entry eval — chart domain | `EVAL_BULLET_DOMAIN_PAWNS` | `1.5` | **`±1.5` pawns (±150 cp)** — covers centered p05/p95 with margin | keep |
| EG-entry eval — neutral zone | TBD (chart not built) | n/a | `±65` cp (±0.65 pawns) | initial value |
| EG-entry eval — chart domain | TBD (chart not built) | n/a | `±200` cp tight, `±300` cp wide | initial value |
| Live z-test white baseline | `EVAL_BASELINE_CP_WHITE` | `28` cp | **28** cp (measured +31.5; gap 3.5 ≤ 5 tol) | **keep** |
| Live z-test black baseline | `EVAL_BASELINE_CP_BLACK` | `-20` cp | **-20** cp (measured −18.9; gap 1.1 ≤ 5 tol) | **keep** |
| Live z-test min-N gate | `EVAL_CONFIDENCE_MIN_N` | `20` | **20** (excess kurtosis 2.4 confirms Edgeworth motivation) | **keep** |

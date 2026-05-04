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

Per-user **mean** signed user-POV Stockfish eval (cp) at the first ply of each phase, computed over rows passing the production filter (`eval_cp NOT NULL`, `eval_mate IS NULL`, `|eval_cp| < 2000`). Sample floor: ≥20 in-domain games per user; cell shown if ≥10 users. Twin-tile bullet-chart inputs (Phase 80 area).

### Currently set in code

- **Bullet chart components**: TBD — not yet implemented (target `frontend/src/components/charts/PhaseEntryEvalSection.tsx` or similar). This section produces *initial* threshold proposals.
- **Color-split engine-asymmetry baselines** (consumed by `eval_confidence.py`): `EVAL_BASELINE_CP_WHITE = 28`, `EVAL_BASELINE_CP_BLACK = -20`, `EVAL_CONFIDENCE_MIN_N = 20` (in `app/services/opening_insights_constants.py:65-74`).

### Phase-entry definitions

Both entry plies come from `game_positions.phase` (SmallInteger, `0=opening / 1=middlegame / 2=endgame`; see `app/models/game_position.py:90-94`). Endgame-entry definition is consistent with §2/§4/§6's `endgame_class IS NOT NULL` thanks to **PHASE-INV-01** (`phase=2 ⟺ endgame_class IS NOT NULL`).

---

### Middlegame-entry eval (per-user mean)

#### Cell table — per-user mean signed cp (n_users)

Cell value is the per-cell **median** of per-user means (i.e. p50 of the per-user-mean distribution within that cell), n is users with ≥20 in-domain MG-entry games.

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -9.8 (100) | 3.6 (100) | 12.9 (100) | -9.8 (68) |
| **1200** | -5.9 (100) | 11.9 (100) | 18.8 (100) | 25.9 (87) |
| **1600** | -1.8 (100) | 5.2 (100) | 5.4 (100) | 20.4 (92) |
| **2000** | 10.8 (100) | 4.7 (100) | 8.0 (100) | 9.5 (73) |
| **2400** | 6.0 (100) | -1.1 (100) | 10.1 (98) | 22.6 (3*) |

Pattern: low-ELO bullet skews negative (-10 cp at 800-bullet) reflecting the tougher equal-footing matchmaking at that level; everywhere else the per-user-mean median sits within ±20 cp of zero. Classical cohorts trend slightly positive across all ELOs (different opponent pools, slower TC's smaller matchmaking pools).

#### TC marginal — per-user mean (sparse-cell excluded)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 | var |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 500 | -4.4 | -113.2 | -31.5 | 3.0 | 33.3 | 83.7 | 4242 |
| blitz | 500 | 3.3 | -80.7 | -12.3 | 3.5 | 27.9 | 68.8 | 1952 |
| rapid | 498 | 9.3 | -63.1 | -12.3 | 10.6 | 32.3 | 76.2 | 2146 |
| classical | 320 | 15.0 | -110.8 | -15.1 | 16.4 | 49.4 | 140.0 | 5543 |

#### ELO marginal — per-user mean (sparse-cell excluded)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 | var |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 368 | -5.3 | -148.5 | -52.7 | 2.6 | 48.2 | 132.6 | 8046 |
| 1200 | 387 | 8.7 | -99.0 | -21.8 | 13.0 | 46.6 | 98.3 | 4469 |
| 1600 | 392 | 6.6 | -68.0 | -14.0 | 6.4 | 32.1 | 72.7 | 1808 |
| 2000 | 373 | 8.3 | -42.5 | -9.2 | 8.2 | 29.8 | 57.2 | 1040 |
| 2400 | 298 | 6.1 | -33.7 | -7.9 | 4.4 | 19.5 | 48.8 | 643 |

Variance collapses monotonically with ELO (8046 → 643, ~12.5×). Higher-rated cohorts converge tightly near 0; low-rated have a long left tail.

#### Pooled overall (sparse-cell excluded)

n=1,818 users. mean **+4.9 cp**, p05 **−91.2**, p25 **−16.9**, p50 **+7.3**, p75 **+33.6**, p95 **+83.7**, var 3309.

#### Color-split engine-asymmetry baselines (game-level, NO equal-footing filter)

The live z-test in `eval_confidence.py:104` consumes per-game evals via `mean = eval_sum / n`, so this sub-block reports game-level distribution stats. Filter: `eval_cp NOT NULL`, `eval_mate IS NULL`, `|eval_cp| < 2000`, base filter only (no EF — production runs on user's actual games).

| color | n_games | mean | median | SD | p05 | p95 |
|---|---:|---:|---:|---:|---:|---:|
| white | 624,634 | **+31.53** | +28 | 238.0 | -397 | 462 |
| black | 625,130 | **-18.86** | -20 | 237.3 | -445 | 414 |
| pooled | 1,249,764 | +6.32 | +4 | 239.0 | -423 | 440 |

**Distribution shape (Edgeworth-relevance for the z-test):**

| color | skew | excess kurtosis |
|---|---:|---:|
| white | +0.036 | +2.408 |
| black | +0.067 | +2.448 |

Skew is essentially zero (mean ≈ median to 4 cp). Excess kurtosis ~2.4 — heavier tails than normal, exactly the value used to motivate `EVAL_CONFIDENCE_MIN_N = 20` (vs the score test's MIN_N = 10). Edgeworth leading-error term on the normal approximation stays under ~2% at N ≥ 20.

**Comparison to live constants** (rule: keep when |measured mean − constant| ≤ 5 cp):

| color | constant | measured mean | gap | recommendation |
|---|---:|---:|---:|---|
| white | `EVAL_BASELINE_CP_WHITE = 28` | +31.53 | +3.5 | **keep** (within 5cp tolerance) |
| black | `EVAL_BASELINE_CP_BLACK = -20` | -18.86 | -1.1 | **keep** (within 5cp tolerance) |

Both constants stand. The white baseline drifted +3.5 cp toward the new measurement vs the snapshot used to set the constant (`reports/eval-mg-entry-normality-2026-05-04.md` cited median +28 / mean unspecified at the time); a future re-calibration could raise white to 30 or 32 without harm, but the gap is below the 5cp tolerance. Black is essentially unchanged.

#### Recommendations

- **Proposed bullet-chart neutral zone** (per-user-mean): pooled `[p25, p75]` = `[−16.9, +33.6]` cp. Mildly asymmetric to the right. Two options:
  - Honor data: **`[−15, +35] cp`** (rounded to 5).
  - Symmetric: **`[−25, +25] cp`** (gives up ~10cp of fidelity on each side).
  - **Recommendation: `[−15, +35]`**. The asymmetry is real and reflects engine bias plus the "mid-ELO and up enter MG slightly favorable on average" signal. Symmetric bounds would visually overstate "below baseline" performance for users at the population center.
- **Proposed bullet-chart domain**: `[p05, p95]` = `[−91, +84]` cp. Symmetric **±100 cp** covers >95% of users and aligns with the score-gap convention of round symmetric bounds. Stretching to **±150 cp** covers the 800 cohort's p05 (−149 cp).
- **Cohort note**: 800-rated users sit ~10 cp left of pooled with 12.5× the variance. Bullet-chart visual contrast across cohorts will be visible but not dramatic.
- **Live z-test constants stand** — `EVAL_BASELINE_CP_WHITE = 28`, `EVAL_BASELINE_CP_BLACK = -20` are within 5 cp of measured population means. No code change needed.

#### Collapse verdict

- TC axis: max |d| = **0.28** (bullet vs classical, mean −4.4 vs +15.0) → **review**
- ELO axis: max |d| = **0.20** (800 vs 2000, mean −5.3 vs +8.3) → **review** (just barely above the collapse threshold)

Single-zone display defensible on both axes — neither verdict hits "keep separate". The 800-bullet cell's negative mean drives the TC verdict; the 800-cohort heavy left tail drives the ELO verdict. Both are the natural skill-cohort signal that should remain visible in the chart.

---

### Endgame-entry eval (per-user mean)

#### Cell table — per-user mean signed cp (n_users)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| **800** | -36.0 (99) | -16.7 (100) | -22.9 (96) | -49.9 (40) |
| **1200** | -9.1 (100) | 4.1 (100) | 15.7 (100) | 22.1 (73) |
| **1600** | -13.8 (100) | 23.5 (100) | 8.4 (100) | 20.0 (87) |
| **2000** | -1.8 (100) | 25.8 (100) | 29.7 (98) | 20.3 (69) |
| **2400** | 15.5 (100) | 17.1 (100) | 29.7 (96) | 206.1 (2*) |

Pattern: 800-bullet at −36 cp and 800-classical at −50 cp confirm the low-rated entering-endgames-already-losing pattern. 1200+ trends positive across all TCs. The (2400, classical) `n=2*` cell at +206 is dominated by two users; not generalizable.

#### TC marginal — per-user mean (sparse-cell excluded)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 | var |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 499 | -6.0 | -222.5 | -81.3 | -4.3 | 75.8 | 202.5 | 17843 |
| blitz | 500 | 14.4 | -135.3 | -40.8 | 14.4 | 64.8 | 167.3 | 9585 |
| rapid | 490 | 22.4 | -139.3 | -37.6 | 17.0 | 83.1 | 183.2 | 9977 |
| classical | 269 | 18.4 | -202.5 | -65.7 | 14.8 | 91.4 | 258.0 | 18292 |

Bullet has the most negative mean and the heaviest left tail (p05 = −223 cp). Slower TCs trend more positive.

#### ELO marginal — per-user mean (sparse-cell excluded)

| ELO | n_users | mean | p05 | p25 | p50 | p75 | p95 | var |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 335 | -13.5 | -268.6 | -116.6 | -22.4 | 84.9 | 279.5 | 28002 |
| 1200 | 373 | 8.7 | -195.6 | -77.2 | 3.5 | 89.6 | 244.1 | 18560 |
| 1600 | 387 | 16.8 | -138.3 | -41.8 | 12.6 | 82.2 | 178.8 | 9162 |
| 2000 | 367 | 22.3 | -105.1 | -27.3 | 18.8 | 71.3 | 150.5 | 6511 |
| 2400 | 296 | 22.7 | -74.0 | -21.5 | 20.6 | 56.5 | 131.6 | 4064 |

Variance collapses 7× from 800 to 2400 (28K → 4K). Strong monotonic ELO ramp on the mean (-13.5 → +22.7), much wider than the MG ramp (−5 → +6).

#### Pooled overall (sparse-cell excluded)

n=1,758 users. mean **+11.4 cp**, p05 **−180.8**, p25 **−54.4**, p50 **+11.1**, p75 **+76.1**, p95 **+199.6**, var 13476.

#### Color-split engine-asymmetry baselines at endgame entry (game-level, NO equal-footing filter)

| color | n_games | mean | median | SD | p05 | p95 |
|---|---:|---:|---:|---:|---:|---:|
| white | 400,153 | **+23.11** | +9 | 443.1 | -710 | 736 |
| black | 402,909 | **+3.21** | 0 | 441.7 | -723 | 720 |
| pooled | 803,062 | +13.12 | +3 | 442.5 | -716 | 728 |

**Distribution shape:**

| color | skew | excess kurtosis |
|---|---:|---:|
| white | -0.042 | -0.466 |
| black | -0.017 | -0.472 |

Skew ~0. Excess kurtosis is **negative** at EG entry (~-0.47) — slightly *lighter* tails than normal, the opposite of MG entry. The EG distribution is bimodal-leaning (the conv/parity/recov bucket structure) and the trim removes the heavy mate cohort, so the residual shape is platykurtic rather than leptokurtic.

**Color-split for future EG-entry confidence pill** (no live constant exists for this yet — record for Phase 81+ work):
- `EVAL_BASELINE_CP_WHITE_EG ≈ 23` (mean) / `+9` (median)
- `EVAL_BASELINE_CP_BLACK_EG ≈ +3` (mean) / `0` (median)
- White's structural advantage compresses substantially by EG entry — by then, both sides have had time to drift from book parity, and the per-color bias halves vs MG entry. A pooled baseline of **0** would be a defensible simplification for EG-entry confidence (vs MG, where the 28/-20 gap is too large to ignore).

#### Recommendations

- **Proposed bullet-chart neutral zone** (per-user-mean): pooled `[p25, p75]` = `[−54.4, +76.1]` cp. Asymmetric to the right.
  - Honor data: **`[−55, +75] cp`**.
  - Symmetric: **`[−65, +65] cp`**.
  - **Recommendation: `[−55, +75]`** to preserve the ~10pp positive tilt that's the natural "users typically enter endgames slightly favorable" signal across the population center.
- **Proposed bullet-chart domain**: `[p05, p95]` = `[−181, +200]` cp. Symmetric **±200 cp** covers >95% of users. Stretch to **±300 cp** for the 800 cohort's p05.
- **Cohort note**: 800-rated users sit ~25 cp left of pooled with ~7× the variance of 2400-rated. The bullet-chart visual contrast across ELO will be much more dramatic than for MG entry.

#### Collapse verdict

- TC axis: max |d| = **0.24** (bullet vs rapid, mean −6.0 vs +22.4) → **review**
- ELO axis: max |d| = **0.28** (800 vs 2400, mean −13.5 vs +22.7) → **review**

Single-zone display defensible. The 800 cohort's heavy negative tail and bullet's lower-mean pattern are the dominant signals; both are interpretable as the "skill" axis the chart should surface, not noise to stratify away.

---

## Top-axis collapse summary (HEADLINE DELIVERABLE — §3 only)

| Metric | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|
| Middlegame-entry eval (per-user mean) | review (0.28) | review (0.20) | Single global zone defensible; cohort skill ramp is the natural signal |
| Endgame-entry eval (per-user mean) | review (0.24) | review (0.28) | Single global zone defensible; cohort skill ramp is the natural signal |

Other §1/§2/§4/§5/§6 metrics: **NOT REFRESHED** in this run — see `benchmarks-2026-05-03.md` for those.

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended | Verdict | Action |
|---|---|---|---|---|---|
| MG-entry eval — neutral zone | TBD (chart not built) | n/a | `[−15, +35]` cp (asymmetric) or `±25` cp (symmetric) | review/review | initial value |
| MG-entry eval — chart domain | TBD (chart not built) | n/a | `±100` cp tight, `±150` cp wide | — | initial value |
| EG-entry eval — neutral zone | TBD (chart not built) | n/a | `[−55, +75]` cp (asymmetric) or `±65` cp (symmetric) | review/review | initial value |
| EG-entry eval — chart domain | TBD (chart not built) | n/a | `±200` cp tight, `±300` cp wide | — | initial value |
| Live z-test white baseline | `EVAL_BASELINE_CP_WHITE` | `28` cp | **28** cp (measured mean +31.5; gap 3.5 cp ≤ tolerance) | — | **keep** |
| Live z-test black baseline | `EVAL_BASELINE_CP_BLACK` | `-20` cp | **-20** cp (measured mean −18.9; gap 1.1 cp ≤ tolerance) | — | **keep** |
| Live z-test min-N gate | `EVAL_CONFIDENCE_MIN_N` | `20` | **20** (excess kurtosis 2.4 confirms Edgeworth motivation) | — | **keep** |

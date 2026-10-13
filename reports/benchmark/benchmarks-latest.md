# FlawChess Benchmarks — 2026-10-12

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Benchmark DB dump**: https://drive.google.com/file/d/1JWGPIvjAPIXsRowOy4IaHcDwSngnjxcC/view?usp=sharing
- **Snapshot taken**: §1 to §4 are carried over verbatim from `benchmarks-2026-08-18.md` (the benchmark DB population for those chapters is unchanged since the 2026-06-10 snapshot; the only edit is the §1 sentence that describes the §5 basis); **§5 was recomputed on 2026-10-12T21:01Z** on the Phase 212 full-analysis lane (`benchmark_selection`, armed, classical + rapid, full evals + PVs + blobs). Population counts below are the carried-over §1 to §4 cohort, not the §5 lane sample (138,104 games).
- **Population**: 4,697 users / 2,767,158 games / 190,934,222 positions (candidate pool: 9,523 selected-user rows)
- **Generator**: `scripts/gen_benchmarks.py --db benchmark` (deterministic; numeric tables spliced from `benchmarks-generated.md`, verdict words + recommendations authored here)
- **Cell anchoring**: 400-wide ELO buckets via the cohort user's **rating at game time** (`games.white_rating`/`games.black_rating`, sub-800 dropped) — NOT the frozen `benchmark_selected_users.rating_bucket`. **Methodology change (2026-05-19): rating-at-game-time bucketing.** `rating_bucket`/`median_elo` retained as longitudinal/trajectory columns only. `tc_bucket` from `benchmark_selected_users`; per-user TC restricted to selected `tc_bucket`.
- **Per-user history caveat**: each user contributes up to 1000 games per TC over a 36-month window at varying ratings, so a user spans 2–3 game-time ELO buckets; "ELO bucket effect" is a genuine rating-at-game-time effect. Any whole-career per-user scalar (e.g. composite Endgame Skill) is now per-bucket/trajectory, not one number.
- **Base filters**: `g.rated AND NOT g.is_computer_game`; `g.time_control_bucket::text = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter).
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating − user_rating) ≤ 100`, both ratings NOT NULL. Live UI uses unfiltered games; the gap above the equal-footing baseline is the intended skill signal.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate forces conv/recov; NULL → parity).
- **Eval coverage**: **100.00%** at endgame entry (1,538,581 / 1,538,585 endgame-reaching games have non-NULL eval).
- **Full-game analysis share (new, §1)**: **22.3%** of cohort games carry whole-game Lichess move-quality analysis (562,753 / 2,528,031). Strongly cell-dependent — 8.6% in bullet vs 51.8% in classical — and it is the per-cell sample ceiling for any all-ply analysis built on this DB. **The analyzed subset is loss-tilted in every TC** (paired within-user score Δ: bullet −3.5pp, blitz −3.4pp, rapid −5.3pp, classical −13.5pp), so no outcome rate computed on it is a population rate. Diagnostic only: no zone, no collapse verdict.
- **Sparse-cell exclusion**: `(2400, classical)` (12 completed users, ~47 games, pool-exhausted) excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes; kept in cell grids with `*` footnote.
- **Deleted calibration targets** (retracted Phase 87.4): `endgame_skill` and `section2_score_gap_skill` composites — §3.2.1 / §3.2.2 report distributions for completeness only, no band.
- **Verdict thresholds**: Cohen's d **< 0.2 collapse** / **0.2–0.5 review** / **≥ 0.5 keep separate** (per axis, independently).
- **§4 (Global Percentile CDF)**: separate deliverable, NOT part of this report — generator chapter is `REFERENCE`-only. See `app/services/global_percentile_cdf.py` / `reports/percentile/`.
- **§5 (Flaw-Delta and Tactic-Delta Zones)**: recomputed 2026-10-12T21:01Z (Phase 239, plan 239-06) on the full-analysis lane only (classical 99.9% and rapid 99.9% of `benchmark_selection` complete at the snapshot; 138,104 analyzed games across 2,006 user×(ELO,TC) cells, 1,590 distinct users), on a new basis. **Owner decision (239-06 checkpoint, accept with edits): the 12 flaw bands are NOT adopted from this run; the app keeps the live flaw bands** (derived on the older whole-cohort `evals_completed_at` basis, 1,223,105 games, up to 1000 games per user), because the proposed widening (1.5x to 3.5x) is mostly sampling noise from the lane's 100-games-per-TC cap. The flaw-delta values in this section are therefore the noise-inflated proposal that was not adopted; the 9 viable tactic bands are adopted as measured. 12 flaw metrics plus 38 tactic metrics (19 families × Missed/Allowed); the overall flaw rate and the two combo flaws are retired (Phase 239). **Blitz and bullet use the rapid zones in the app** until their tranches finish (D-08/D-09 stopgap); the half-finished blitz tranche is never used. Per-user values come from at most 100 games per TC (the lane cap), so each band includes sampling noise: the noise-only IQR is reported next to the observed IQR for every metric (§5.15), and the bands are mostly noise. Negative delta = fewer flaws than equally rated opponents. Verdicts: no metric reaches keep-separate on either axis, so every band is one pooled band for both zone TCs and nothing is Elo keyed.

---

## 1. Stratified Sample

### Cell coverage (`status='completed'` users per cell)

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 200 | 200 | 200 | 151 |
| 1200 | 200 | 200 | 200 | 200 |
| 1600 | 200 | 200 | 200 | 200 |
| 2000 | 200 | 200 | 200 | 200 |
| 2400 | 200 | 200 | 200 | 12* |

`*` Sparse cell — pool-exhausted (12 completed / 23 candidate / 0 unattempted). Excluded from all marginals and Cohen's d. `(800, classical)` is also pool-limited (151) but stays in marginals.

### Game-time cell sizes (post equal-footing filter — `users / games`)

The analysis cells (game-time ELO bucket × TC). A user contributes to 2–3 ELO buckets across their career, so per-bucket user counts exceed the 200/cell selection cap.

| ELO \ TC | bullet | blitz | rapid | classical |
|---:|---:|---:|---:|---:|
| 800 | 268 / 114,933 | 260 / 115,661 | 317 / 95,792 | 222 / 11,609 |
| 1200 | 404 / 165,994 | 423 / 162,443 | 545 / 132,196 | 452 / 39,705 |
| 1600 | 363 / 165,589 | 419 / 164,380 | 502 / 134,570 | 423 / 48,763 |
| 2000 | 334 / 147,313 | 364 / 140,587 | 399 / 97,751 | 222 / 17,766 |
| 2400 | 240 / 113,012 | 223 / 89,885 | 208 / 31,627 | 10 / 47* |

All non-sparse cells clear the ≥10-users floor comfortably.

### Eval coverage at endgame entry

| metric | value |
|---|---:|
| Endgame-reaching games (≥6 plies, `endgame_class IS NOT NULL`) | 1,538,585 |
| With non-NULL Stockfish eval at entry ply | 1,538,581 |
| Coverage | **100.00%** |

Above the 99% floor — no NULL-eval bias flag needed.

### Full-game analysis share

What fraction of each cell's games carry **whole-game move-quality analysis** — Lichess's
server-side Stockfish pass (per-ply evals + per-color inaccuracy/mistake/blunder counts).
Distinct from the eval-coverage check above, which asks only whether the *first endgame ply*
has an eval and sits at ~100% because our own backfill fills it.

Definition: `games.white_blunders IS NOT NULL`, the same predicate as the app's
`Game.is_analyzed`. On this DB it is exactly Lichess analysis — all 641,855 flagged rows also
have `lichess_evals_at` set and none is engine-written. It agrees with the ≥90%-of-plies-have-an-eval
definition used by the ad-hoc coverage reports to within 0.05pp of cohort (563,226 vs 561,950
games before the sub-800 drop; 1,276 flagged games have sparser per-ply coverage, and zero
games clear 90% coverage without the flag).

Basis: the cohort filter alone (rated, human opponent, TC-anchored), **without** the
equal-footing filter — analysis availability is a property of the ingested data, not of an
analysis design. The equal-footing subset is shown below as a sensitivity check.

#### Share of games with whole-game analysis

| ELO \ TC | bullet | blitz | rapid | classical | **all TC** |
|---:|---:|---:|---:|---:|---:|
| 800 | 11.5% | 15.5% | 18.5% | 27.1% | **15.6%** |
| 1200 | 9.1% | 14.0% | 21.3% | 40.3% | **16.8%** |
| 1600 | 6.6% | 14.6% | 25.1% | 57.5% | **19.7%** |
| 2000 | 7.0% | 20.4% | 43.3% | 73.7% | **25.0%** |
| 2400 | 9.8% | 55.2% | 70.2% | 77.7%* | **37.4%** |
| **all ELO** | **8.6%** | **22.9%** | **32.0%** | **51.8%** | **22.3%** |

#### Analyzed / total games

| ELO \ TC | bullet | blitz | rapid | classical | **all TC** |
|---:|---:|---:|---:|---:|---:|
| 800 | 15,914 / 138,400 | 20,991 / 135,447 | 21,355 / 115,483 | 6,105 / 22,494 | **64,365 / 411,824** |
| 1200 | 16,774 / 184,122 | 25,380 / 181,336 | 31,735 / 148,778 | 21,913 / 54,337 | **95,802 / 568,573** |
| 1600 | 12,666 / 193,294 | 27,636 / 189,074 | 39,772 / 158,664 | 40,060 / 69,725 | **120,134 / 610,757** |
| 2000 | 13,284 / 190,624 | 37,527 / 183,668 | 59,357 / 136,965 | 26,427 / 35,864 | **136,595 / 547,121** |
| 2400 | 17,180 / 175,462 | 79,609 / 144,349 | 49,068 / 69,945 | 473 / 609* | **145,857 / 389,756** |
| **all ELO** | **75,818 / 881,902** | **191,143 / 833,874** | **201,287 / 629,835** | **94,505 / 182,420** | **562,753 / 2,528,031** |

`*` sparse cell — kept in the grids, excluded from every marginal and the pooled total.

#### Cohort vs equal-footing subset

| level | cohort share | equal-footing share | Δ |
|---|---:|---:|---:|
| TC = bullet | 8.6% | 7.9% | −0.7pp |
| TC = blitz | 22.9% | 20.5% | −2.4pp |
| TC = rapid | 32.0% | 29.1% | −2.9pp |
| TC = classical | 51.8% | 51.3% | −0.5pp |
| ELO = 800 | 15.6% | 15.0% | −0.6pp |
| ELO = 1200 | 16.8% | 16.0% | −0.9pp |
| ELO = 1600 | 19.7% | 18.2% | −1.5pp |
| ELO = 2000 | 25.0% | 22.4% | −2.6pp |
| ELO = 2400 | 37.4% | 35.3% | −2.1pp |
| **pooled** | 22.3% | 20.0% | −2.3pp |

#### Reading

**Time control is the dominant axis, not rating.** The TC marginal spans 6× (bullet 8.6% →
classical 51.8%); the ELO marginal spans 2.4× (15.6% → 37.4%), and most of that comes from two
cells. Anyone sizing an all-ply study on this DB should budget by TC first.

**The two axes interact, so the marginals mislead on their own.** Within bullet the rating
gradient is flat-to-inverted (11.5% at 800, bottoming at 6.6% at 1600, back to 9.8% at 2400) —
Lichess bullet games rarely get analyzed at any strength. Within classical it is steep and
monotone (27.1% → 77.7%). The pooled ELO gradient is therefore mostly a TC-mix effect plus the
2400 blitz/rapid cells (55.2% / 70.2%), which are the only fast-TC cells that clear half.

**Usable cells.** Above 50%: 2400 rapid (49,068 analyzed games), 2000 classical (26,427),
2400 blitz (79,609), 1600 classical (40,060). Bullet cells sit at 6.6–11.5% but still carry
12,666–17,180 analyzed games each off ~180k, so absolute volume is rarely the constraint.
`(2400, classical)` has 473 analyzed games and stays excluded from marginals.

**The analyzed subset is tilted toward the cohort user's losses in every time control.**
A share below 100% means someone chose these games, so the question is whether the chosen ones
differ in outcome. Two limits on how far this can be answered:

- **Requester attribution is not available.** Lichess attaches analysis to the *game*, not to a
  player — the export exposes only whether `%eval` annotations exist (`lichess_client.py`,
  `"evals": True`), and neither the API nor our schema records who asked for it. So "the loser
  requested it" is not something this data can confirm; only the association is measurable.
- **The pooled comparison is confounded and must not be used.** Users differ enormously in how
  much they analyze, so pooling compares partly different users. Paired within (user, TC) —
  restricted to users with ≥20 analyzed and ≥20 unanalyzed games — gives a different and in one
  case opposite answer. Score = win + ½ draw, from the cohort user's POV:

| TC | pooled Δ (confounded) | **paired Δ** | paired users | users scoring worse when analyzed |
|---|---:|---:|---:|---:|
| bullet | −0.4pp | **−3.5pp** | 959 | 62.4% |
| blitz | **+2.3pp** | **−3.4pp** | 922 | 66.8% |
| rapid | −0.8pp | **−5.3pp** | 923 | 65.8% |
| classical | −9.7pp | **−13.5pp** | 485 | 78.4% |

Blitz flips sign between the two estimators — a Simpson's paradox, and the reason the pooled
row is shown only as a warning. On the paired estimator the effect is **negative in all four
time controls**, and it is a majority-of-individuals effect, not a few outliers: 62–78% of users
score worse in their own analyzed games than in their own unanalyzed ones.

Reading: classical is the extreme (−13.5pp, and its 51.8% coverage means this tilt applies to
half the cell), but no TC is exempt — bullet's low 8.6% share does not make it a clean random
sample. The direction is consistent with cohort users requesting analysis after losses, which
Stage-1 selection would amplify (the pool requires ≥10 eval-bearing games, i.e. it selects
people who request analysis). But it is equally consistent with opponents requesting, or with
longer/sharper games being both more analysis-worthy and more often lost. **Treat the analyzed
subset as loss-tilted, and do not read any outcome-rate computed on it as a population rate.**

Two scope notes. The paired estimator excludes users at either coverage extreme (485 of the
classical cell's users qualify), so it describes users who analyze *some* of their games. And
§5's zones (recomputed 2026-10-12, Phase 239) are built on the full-analysis lane instead: classical and rapid
games of `benchmark_selection` whose evals, PVs and tactic blobs were all computed by our engine (both the
lichess-analyzed and the never-analyzed arm are re-evaluated), capped at 100 games per user per TC. That is a
different, equal-footing, engine-homogeneous sample, so the loss tilt above does not transfer to §5 without its own check.

**The equal-footing filter does not distort availability.** Every level moves by less than 3pp
and always in the same direction (analyzed games are marginally more often rating-mismatched).
The §2–§5 denominators need no coverage caveat beyond what is already in this chapter.

---

## 2. Openings

### 2.1 Middlegame-entry eval

**Symmetric baseline (deduped to physical games):**

| n_games | baseline_cp_white | median (white-POV) | SD |
|---:|---:|---:|---:|
| 2,504,885 | **+25.21 cp** | +24.0 | 237.2 |

Black baseline = −25 cp by construction. Live `EVAL_BASELINE_PAWNS_WHITE = 0.25` (= +25 cp) matches the measured +25.21 cp within 0.2 cp — **no change**. `EVAL_BASELINE_PAWNS_BLACK = -0.25` is symmetric (invariant holds).

**Centered per-(user, color) pooled distribution:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 9,109 | +3.7 cp | 58.5 cp | −92 cp | −23 cp | +6 cp | +34 cp | +89 cp |

**ELO marginal (centered, cp):**

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 1,541 | −0.8 | 87.9 | −145 | −46 | +8 | +57 | +127 |
| 1200 | 2,140 | +5.7 | 69.3 | −104 | −32 | +10 | +48 | +106 |
| 1600 | 2,290 | +5.0 | 49.6 | −75 | −21 | +7 | +34 | +79 |
| 2000 | 1,988 | +4.4 | 35.2 | −53 | −15 | +5 | +26 | +59 |
| 2400 | 1,150 | +2.0 | 27.5 | −46 | −13 | +3 | +19 | +45 |

**TC marginal (centered, cp):**

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bullet | 2,674 | −2.5 | 71.7 | −126 | −31 | +4 | +37 | +95 |
| blitz | 2,665 | +2.9 | 45.1 | −75 | −20 | +3 | +28 | +73 |
| rapid | 2,628 | +8.5 | 50.3 | −76 | −17 | +9 | +35 | +89 |
| classical | 1,142 | +8.8 | 67.2 | −96 | −25 | +9 | +46 | +113 |

**Collapse verdict:** TC max |d| = **0.18** (bullet vs rapid) → **collapse**. ELO max |d| = **0.09** (800 vs 1600) → **collapse**. Color collapse automatic by construction.

**Recommendations:**
- **Baseline**: keep `EVAL_BASELINE_PAWNS_WHITE = 0.25` (measured +25.21 cp, within 5 cp tolerance).
- **Neutral zone** (`openingStatsZones.ts` `EVAL_NEUTRAL_*_PAWNS = ±0.30`): pooled centered IQR `[−23, +34]` cp ≈ ±0.34 pawns rounds to **±0.30** — keep. Both axes collapse; single global band justified.
- **Domain** (`EVAL_BULLET_DOMAIN_PAWNS = 1.5`): pooled `[p05, p95] = [−92, +89]` cp → well inside ±1.5 pawns; keep.

---

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,020 | 51.9% | 8.8% | 38.1% | 46.1% | 51.6% | 57.3% | 67.1% |

**ELO marginal:**

| ELO | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| 800 | 697 | 51.9% | 7.5% | 46.8% | 51.8% | 56.6% |
| 1200 | 968 | 52.0% | 8.5% | 46.4% | 51.3% | 56.9% |
| 1600 | 1,016 | 51.4% | 9.2% | 45.3% | 51.2% | 56.8% |
| 2000 | 839 | 52.4% | 9.1% | 46.2% | 52.0% | 58.1% |
| 2400 | 500 | 52.2% | 9.4% | 46.4% | 52.1% | 58.0% |

**TC marginal:**

| TC | n | mean | SD | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|---:|
| bullet | 1,238 | 50.7% | 8.4% | 45.5% | 50.8% | 55.6% |
| blitz | 1,228 | 51.2% | 8.0% | 45.6% | 51.0% | 56.3% |
| rapid | 1,156 | 53.1% | 9.1% | 46.7% | 52.4% | 58.5% |
| classical | 398 | 54.8% | 9.9% | 48.4% | 54.5% | 61.9% |

**Collapse verdict:** TC max |d| = **0.46** (bullet vs classical) → **review**. ELO max |d| = **0.10** → **collapse**.

**Recommendation:** pooled IQR `[46.1%, 57.3%]`. Shared `SCORE_BULLET_NEUTRAL_* = ±0.05` (→ [0.45, 0.55]) sits slightly low at the top edge. TC review is classical-driven (54.8% mean) but stays under 0.5 → **keep the shared band**; a dedicated non-EG module isn't warranted for a ~2pp top-edge drift.

---

#### 3.1.2 Endgame-entry eval (pawns)

**Symmetric EG-entry baseline (deduped):**

| n_games | baseline_cp_white | median | SD |
|---:|---:|---:|---:|
| 1,604,885 | +10.32 cp | +0.0 | 443.8 |

**Pooled distribution (uncentered drives the 0-centered live tile):**

| variant | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **uncentered** | 8,322 | +9.3 cp | 119.2 | −185 | −57 | +10 | +77 | +200 |
| centered | 8,322 | +9.3 cp | 118.6 | −183 | −57 | +10 | +76 | +199 |

**ELO marginal (centered, cp):**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 1,359 | +1.7 | −101 | +1 | +102 |
| 1200 | 1,943 | +3.6 | −77 | +4 | +91 |
| 1600 | 2,099 | +15.1 | −51 | +16 | +82 |
| 2000 | 1,817 | +15.2 | −40 | +16 | +67 |
| 2400 | 1,104 | +7.9 | −36 | +7 | +49 |

**TC marginal (centered, cp):**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 2,563 | −0.1 | −80 | +2 | +81 |
| blitz | 2,521 | +12.3 | −46 | +12 | +70 |
| rapid | 2,406 | +17.1 | −43 | +16 | +77 |
| classical | 832 | +6.5 | −60 | +9 | +76 |

**Collapse verdict:** TC max |d| = **0.14** → **collapse**. ELO max |d| = **0.11** → **collapse**.

**Recommendation:** uncentered IQR `[−57, +77]` cp = `[−0.57, +0.77]` pawns; live `entry_eval_pawns = ±0.60` (editorially tightened so the 0-centered tile actually paints) brackets the IQR → **keep ±0.60**. Domain `[p05, p95] = [−185, +200]` cp = `[−1.85, +2.00]`; live `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.25` covers it → keep.

---

#### 3.1.3 Achievable Score (entry_xs)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 50.9% | 8.0% | 38.0% | 46.2% | 51.0% | 55.7% | 64.0% |

**ELO marginal:**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 50.5% | 43.9% | 50.6% | 57.0% |
| 1200 | 1,068 | 50.7% | 44.8% | 50.6% | 56.6% |
| 1600 | 1,166 | 51.4% | 46.5% | 51.5% | 56.2% |
| 2000 | 1,028 | 51.3% | 47.4% | 51.3% | 54.9% |
| 2400 | 598 | 50.6% | 47.6% | 50.3% | 53.3% |

**TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.4% | 44.7% | 50.4% | 56.2% |
| blitz | 1,353 | 51.0% | 47.0% | 51.1% | 55.1% |
| rapid | 1,334 | 51.4% | 46.9% | 51.2% | 55.8% |
| classical | 579 | 50.9% | 45.8% | 50.7% | 56.0% |

**Collapse verdict:** TC max |d| = **0.12** → **collapse**. ELO max |d| = **0.12** → **collapse**.

**Sanity check (game-time-bucketed):** 800–1600 sit at 50.5–51.4% (within ±1.5pp of 0.50, no monotone ramp) — equal-footing filter passes; 2000/2400 stay flat (~50.6–51.3%, mild residual). Pooled IQR `[46.2%, 55.7%]` ≈ [0.46, 0.56]; live `entry_expected_score = [0.45, 0.55]` within tolerance → **keep [0.45, 0.55]**.

---

#### 3.1.4 Endgame Score (per-user, EG-only)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 51.4% | 8.7% | 38.3% | 46.1% | 51.0% | 56.5% | 66.5% |

**ELO marginal:**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 49.9% | 44.0% | 49.3% | 54.9% |
| 1200 | 1,068 | 50.2% | 44.5% | 49.6% | 55.3% |
| 1600 | 1,166 | 51.6% | 46.0% | 50.8% | 56.8% |
| 2000 | 1,028 | 52.9% | 47.3% | 52.5% | 57.7% |
| 2400 | 598 | 52.8% | 48.7% | 52.7% | 56.6% |

**TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.6% | 46.0% | 50.0% | 54.7% |
| blitz | 1,353 | 51.7% | 46.2% | 51.6% | 56.5% |
| rapid | 1,334 | 52.3% | 46.6% | 51.9% | 57.4% |
| classical | 579 | 50.9% | 43.9% | 50.2% | 57.9% |

**Collapse verdict:** TC max |d| = **0.21** (bullet vs rapid) → **review**. ELO max |d| = **0.35** (800 vs 2400) → **review**.

**Recommendation:** pooled IQR `[46.1%, 56.5%]`; live `endgame_score = [0.45, 0.55]`. The ELO sweep (49.3% → 52.7% p50, 3.4pp) is the known rating residual (D-01 confound), under the 0.5 keep threshold → **keep [0.45, 0.55]**; per-ELO stratification not yet warranted.

---

#### 3.1.5 Achievable Score Gap (paired actual − expected)

**Pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | +0.5pp | 8.2pp | −12.8pp | −3.9pp | +0.7pp | +5.1pp | +13.2pp |

**ELO marginal (pp):**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | −0.6 | −5.8 | −0.4 | +4.5 |
| 1200 | 1,068 | −0.5 | −4.7 | −0.3 | +4.2 |
| 1600 | 1,166 | +0.2 | −3.9 | +0.4 | +4.6 |
| 2000 | 1,028 | +1.7 | −2.8 | +1.7 | +6.1 |
| 2400 | 598 | +2.2 | −2.0 | +2.5 | +6.4 |

**TC marginal (pp):**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | +0.2 | −6.0 | +0.7 | +7.2 |
| blitz | 1,353 | +0.7 | −3.4 | +1.0 | +5.0 |
| rapid | 1,334 | +0.9 | −2.7 | +0.7 | +4.4 |
| classical | 579 | +0.0 | −4.2 | −0.1 | +4.0 |

**Collapse verdict:** TC max |d| = **0.13** → **collapse**. ELO max |d| = **0.34** (800 vs 2400) → **review**.

**Recommendation:** pooled mean +0.5pp (within ±1pp engine-alignment null, healthy). Pooled IQR `[−3.9pp, +5.1pp]`; live `achievable_score_gap = ±0.05` → **keep ±0.05**. ELO review (800 median −0.4pp → 2400 +2.5pp) — per-ELO stratification deferred.

---

#### 3.1.6 Endgame Score Gap and Timeline

**Pooled (`eg_score − non_eg_score`):**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,020 | −1.0pp | 13.2pp | −21.8pp | −9.9pp | −1.0pp | +8.0pp | +20.7pp |

**ELO marginal (pp):**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 697 | −2.4 | −11.7 | −3.0 | +6.4 |
| 1200 | 968 | −1.7 | −11.0 | −2.1 | +7.7 |
| 1600 | 1,016 | −0.3 | −9.0 | −0.3 | +9.0 |
| 2000 | 839 | −0.4 | −8.5 | −0.4 | +8.2 |
| 2400 | 500 | +0.3 | −7.1 | +0.6 | +7.8 |

**TC marginal (pp):**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,238 | −0.4 | −9.0 | −1.2 | +7.8 |
| blitz | 1,228 | +0.2 | −8.4 | +0.1 | +8.5 |
| rapid | 1,156 | −1.4 | −10.5 | −1.0 | +7.9 |
| classical | 398 | −4.8 | −15.9 | −4.7 | +7.0 |

**Collapse verdict:** TC max |d| = **0.37** (blitz vs classical) → **review**. ELO max |d| = **0.21** (800 vs 2400) → **review**.

**Recommendation:** pooled IQR `[−9.9pp, +8.0pp]`; live `score_gap = ±0.10`. **Keep ±0.10** — pooled median −1.0pp under the 5pp re-centering guard. Classical drags the TC marginal (−4.8pp mean) but stays review.

---

### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery

**Conversion — pooled:**

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,616 | 71.1% | 10.8% | 52.9% | 64.9% | 71.6% | 77.7% | 87.5% |

**Conversion — ELO marginal:**

| ELO | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| 800 | 756 | 67.8% | 61.3% | 69.1% | 75.0% |
| 1200 | 1,068 | 70.0% | 63.7% | 71.2% | 76.8% |
| 1600 | 1,166 | 71.7% | 65.7% | 72.0% | 78.3% |
| 2000 | 1,028 | 72.5% | 66.7% | 72.9% | 79.0% |
| 2400 | 598 | 73.3% | 67.8% | 73.0% | 78.6% |

**Conversion — TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 65.2% | 58.8% | 65.6% | 71.9% |
| blitz | 1,353 | 71.7% | 66.7% | 71.9% | 76.9% |
| rapid | 1,334 | 74.4% | 69.6% | 74.6% | 80.0% |
| classical | 579 | 75.4% | 68.5% | 76.0% | 83.3% |

**Conversion verdict:** TC max |d| = **0.93** (bullet vs classical) → **keep separate**. ELO max |d| = **0.51** (800 vs 2400) → **keep separate**.

**Parity — pooled:** n=4,616 · mean 50.7% · IQR `[44.0%, 57.3%]` · p50 50.0%.

**Parity — TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 50.4% | 43.6% | 50.0% | 57.2% |
| blitz | 1,353 | 50.8% | 44.8% | 51.0% | 56.9% |
| rapid | 1,334 | 51.3% | 44.9% | 50.5% | 57.5% |
| classical | 579 | 49.8% | 40.4% | 50.0% | 59.1% |

**Parity verdict:** TC max |d| = **0.11** → **collapse**. ELO max |d| = **0.22** (1200 vs 2400) → **review**.

**Recovery — pooled:** n=4,616 · mean 30.8% · IQR `[24.0%, 37.0%]` · p50 30.0%.

**Recovery — TC marginal:**

| TC | n | mean | p25 | p50 | p75 |
|---:|---:|---:|---:|---:|---:|
| bullet | 1,350 | 35.7% | 29.5% | 35.3% | 41.2% |
| blitz | 1,353 | 30.9% | 25.1% | 30.0% | 35.7% |
| rapid | 1,334 | 28.1% | 21.8% | 27.3% | 33.3% |
| classical | 579 | 25.6% | 17.4% | 23.5% | 31.6% |

**Recovery verdict:** TC max |d| = **0.90** (bullet vs classical) → **keep separate**. ELO max |d| = **0.25** (1200 vs 2400) → **review**.

**Recommendations:** Conversion and Recovery both **keep-separate on TC** (d ≈ 0.9). The live per-TC `TC_METRIC_BANDS` (conv `bullet 0.588–0.719 … classical 0.685–0.833`; recov `bullet 0.295–0.412 … classical 0.174–0.316`) are the correct shape and reproduce these per-TC IQRs → **keep per-TC**. Parity collapses on TC; the live per-TC parity bands (near-identical bullet/blitz/rapid, classical wider) match → keep. Conversion's ELO keep (0.51) remains the strongest argument for eventual per-(TC×ELO) conversion stratification; deferred.

---

#### 3.2.2 Section-2 ΔES Score Gap (per entry-eval bucket)

**Pooled:** Conv n=4,138 · mean −6.2pp · IQR `[−11.0, +0.2]`. Parity n=3,623 · mean +0.1pp · IQR `[−3.7, +4.1]`. Recovery n=3,973 · mean +6.4pp · IQR `[+0.9, +11.0]` (pp).

**Conversion-bucket — ELO / TC marginals (pp):**

| axis | level | n | mean | p25 | p50 | p75 |
|---|---|---:|---:|---:|---:|---:|
| ELO | 800 | 683 | −12.9 | −17.4 | −10.5 | −6.3 |
| ELO | 1200 | 973 | −8.6 | −12.8 | −6.5 | −2.5 |
| ELO | 1600 | 1,048 | −5.2 | −9.8 | −3.8 | +0.8 |
| ELO | 2000 | 901 | −2.5 | −6.8 | −1.2 | +3.2 |
| ELO | 2400 | 533 | −1.2 | −5.2 | −1.1 | +3.5 |
| TC | bullet | 1,270 | −13.2 | −19.5 | −11.6 | −5.7 |
| TC | blitz | 1,254 | −4.5 | −8.5 | −4.0 | +0.3 |
| TC | rapid | 1,201 | −2.3 | −6.3 | −2.0 | +2.1 |
| TC | classical | 413 | −1.1 | −5.3 | −0.1 | +3.8 |

**Recovery-bucket — ELO / TC marginals (pp):**

| axis | level | n | mean | p25 | p50 | p75 |
|---|---|---:|---:|---:|---:|---:|
| ELO | 800 | 670 | +11.2 | +5.7 | +9.5 | +15.5 |
| ELO | 1200 | 940 | +7.6 | +2.6 | +6.3 | +11.8 |
| ELO | 1600 | 989 | +5.2 | −0.1 | +3.5 | +9.4 |
| ELO | 2000 | 848 | +4.2 | −1.0 | +3.4 | +9.1 |
| ELO | 2400 | 526 | +3.9 | −0.7 | +3.6 | +8.1 |
| TC | bullet | 1,240 | +12.9 | +7.4 | +12.4 | +17.7 |
| TC | blitz | 1,219 | +5.1 | +1.1 | +4.8 | +8.4 |
| TC | rapid | 1,123 | +2.8 | −0.8 | +2.6 | +6.2 |
| TC | classical | 391 | +0.2 | −3.7 | +0.2 | +3.5 |

**Collapse verdicts:** Conv ΔES TC **1.25** keep / ELO **1.35** keep · Parity ΔES TC **0.18** collapse / ELO **0.31** review · Recovery ΔES TC **1.69** keep / ELO **0.95** keep.

**Sigmoid-bias check confirmed:** conv skews negative (−6.2pp, ceiling at 1.0), recov positive (+6.4pp, floor at 0.0), parity ~symmetric (+0.1pp). Off-zero bands correct. Live `score_gap_conv = [−0.11, 0.00]`, `score_gap_parity = ±0.04`, `score_gap_recov = [0.01, 0.11]` match the pooled IQRs → **keep all three** scalar bands (per-(TC×ELO) Section-2 stratification deferred — see §3.2.3).

---

#### 3.2.3 Rate vs Score-Gap divergence (derived)

| Bucket | Raw rate ELO sweep / d | Raw rate TC sweep / d | Gap ELO sweep / d | Gap TC sweep / d |
|---|---|---|---|---|
| Conversion | 67.8%→73.3% / 0.51 keep | 65.2%→75.4% / 0.93 keep | −12.9pp→−1.2pp / 1.35 keep | −13.2pp→−1.1pp / 1.25 keep |
| Recovery | 31.3%→32.5% / 0.25 review | 35.7%→25.6% / 0.90 keep | +11.2pp→+3.9pp / 0.95 keep | +12.9pp→+0.2pp / 1.69 keep |

**Divergence (recovery, ELO axis):** raw recovery rate is ELO-flat (d=0.25 review) but the recovery **gap** re-exposes a strong ELO signal (d=0.95 keep) — weak players over-perform the engine far more when recovering (+11.2pp) than strong players (+3.9pp); the flat raw rate hides it because engine expectation rises with the cohort. This is the strongest standing argument against the Section-2 scalar-registry deferral. **Recommendation unchanged this snapshot** (scalar pooled bands ship); flag recovery as the first candidate if per-(TC×ELO) Section-2 stratification is revisited.

---

### 3.3 Time Pressure

#### 3.3.1 Clock pressure at endgame entry

**Clock-diff % (per-user mean):**

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,604 | −1.12% | −6.35% | −0.50% | +4.83% |
| bullet | 1,343 | −0.17% | −3.96% | −0.29% | +3.29% |
| blitz | 1,353 | −0.77% | −6.68% | −0.29% | +5.27% |
| rapid | 1,334 | −1.81% | −8.14% | −0.94% | +5.21% |
| classical | 574 | −2.60% | −11.29% | −1.21% | +8.19% |

**Net-timeout rate (pp):**

| slice | n | mean | p25 | p50 | p75 |
|---|---:|---:|---:|---:|---:|
| **POOLED** | 4,604 | +0.45pp | −4.46pp | +1.13pp | +6.09pp |
| bullet | 1,343 | +0.45pp | −10.95pp | +0.53pp | +11.86pp |
| blitz | 1,353 | +0.85pp | −5.35pp | +2.07pp | +8.64pp |
| rapid | 1,334 | +0.27pp | −2.14pp | +1.53pp | +3.96pp |
| classical | 574 | −0.05pp | +0.00pp | +0.00pp | +1.80pp |

**Clock-gap fraction (per-user):** pooled p25/p50/p75 = `−0.0635 / −0.0050 / +0.0483`.

**Collapse verdicts:** clock-diff% TC **0.24** review / ELO **0.17** collapse · net-timeout TC **0.09** collapse / ELO **0.28** review · clock-gap ELO collapse.

**Recommendations:**
- `NEUTRAL_PCT_THRESHOLD = ±5.0%`: pooled clock-diff IQR `[−6.35%, +4.83%]` → **keep ±5** (TC review under 0.5).
- `NEUTRAL_TIMEOUT_THRESHOLD = ±5.0pp`: pooled net-timeout IQR `[−4.5pp, +6.1pp]` → **keep ±5**.
- `clock_gap_pct = [−0.065, +0.047]`: pooled IQR `[−0.0635, +0.0483]` → matches within 0.2pp; **keep**.

---

#### 3.3.2 Time pressure vs performance curve

**Pooled curve (time-bucket 0 = 0–10% clock remaining → 9 = 90–100%):**

| tb | n_games | score | tb | n_games | score |
|---:|---:|---:|---:|---:|---:|
| 0 | 74,569 | 31.0% | 5 | 150,007 | 54.7% |
| 1 | 97,328 | 41.8% | 6 | 148,644 | 54.3% |
| 2 | 106,008 | 49.0% | 7 | 128,236 | 53.7% |
| 3 | 125,531 | 52.2% | 8 | 84,609 | 52.7% |
| 4 | 140,322 | 54.0% | 9 | 52,117 | 51.5% |

**Per-time-bucket collapse verdict (max |d| on per-game score):**

| tb | TC max |d| | ELO max |d| |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.39 (bullet vs classical) review | 0.16 collapse |
| 1 | 0.16 collapse | 0.11 collapse |
| 2–9 | ≤ 0.14 collapse | ≤ 0.12 collapse |

**Recommendation:** universal "pressure crushes score" shape (31% at 0–10% clock → 54.7% peak at mid-clock). Only **time-bucket 0 shows a TC effect** (0.39 review; classical 42.5% vs bullet 25.6%) → **stratify the TC overlay at extreme pressure only**, pool elsewhere. ELO collapses across all buckets.

---

#### 3.3.3 Chess score per pressure bin (per-(TC × quintile))

**Per-quintile collapse verdict:**

| Q (clock remaining) | TC max |d| | ELO max |d| |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (0–20%, max pressure) | 0.75 keep | 0.56 keep |
| 1 (20–40%) | 0.32 review | 0.15 collapse |
| 2 (40–60%) | 0.46 review | 0.25 review |
| 3 (60–80%) | 0.40 review | 0.34 review |
| 4 (80–100%, min pressure) | 0.19 collapse | 0.31 review |

**Recommendation:** Q0 is the strongest stratifier on **both** axes (TC 0.75, ELO 0.56 — both keep). The live `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` already ships per-(TC × quintile) bands with the ±0.06 editorial cap; the regenerated p25/p50/p75 (e.g. bullet-Q0 `0.275/0.343/0.419`, classical-Q4 `0.420/0.506/0.615`) reproduce the committed bands within rounding → **keep per-(TC×Q)**. The cap activates at 14/20 cells (extreme quintiles), as documented.

---

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

**Pooled-by-class (sparse cell excluded):**

| class | games | users | score | conversion | recovery |
|---|---:|---:|---:|---:|---:|
| rook | 187,177 | 3,655 | 50.7% | 71.2% | 29.8% |
| minor_piece | 139,393 | 3,611 | 50.9% | 69.4% | 32.5% |
| pawn | 74,055 | 3,487 | 50.8% | 73.9% | 27.4% |
| queen | 68,196 | 3,495 | 50.8% | 77.5% | 23.5% |
| mixed | 1,060,245 | 3,735 | 50.6% | 69.6% | 31.1% |
| pawnless | 11,690 | 2,723 | 50.8% | 79.3% | 19.7% |

**Per-class chess-score IQR (per-user, ≥10 games/class):**

| class | n_users | p25 | p50 | p75 |
|---|---:|---:|---:|---:|
| rook | 3,075 | 43.9% | 50.0% | 57.1% |
| minor_piece | 2,841 | 43.0% | 50.8% | 57.8% |
| pawn | 2,353 | 41.9% | 50.0% | 58.6% |
| queen | 2,303 | 41.2% | 52.1% | 62.5% |
| mixed | 3,599 | 46.2% | 51.0% | 56.0% |
| pawnless | 243 | 30.0% | 41.7% | 58.6% |

**Per-(metric × class × axis) collapse verdicts:**

| class | conv TC d | conv ELO d | recov TC d | recov ELO d |
|---|---:|---:|---:|---:|
| rook | 1.24 keep | 0.32 review | 1.33 keep | 0.20 review |
| minor_piece | 1.50 keep | 0.41 review | 1.48 keep | 0.31 review |
| pawn | 1.40 keep | 0.31 review | 1.36 keep | 0.65 keep |
| queen | 1.43 keep | 0.32 review | 1.67 keep | 0.31 review |
| mixed | 1.19 keep | 0.49 review | 1.28 keep | 0.22 review |

**Recommendations:**
- **Score is flat across class** (all 5 visible classes within ±1.1pp of 50%) → score collapses across class; **keep the global `SCORE_BULLET_NEUTRAL_* = ±0.05`** for the per-class score bullet (queen's wider IQR is the only outlier but stays near-symmetric).
- **Conversion & recovery keep-separate on TC for every class** (d ≈ 1.2–1.7). Live `PER_CLASS_GAUGE_ZONES` are TC-agnostic — this **mispaints by TC**. **Flag: stratify `PER_CLASS_GAUGE_ZONES` → per-(class × TC)**, scoped to whether the Endgame Type cards expose a TC filter. (Same standing flag as prior snapshots.)
- Pawn-recovery ELO keep (0.65) is the only per-class ELO signal above threshold.

---

#### 3.4.2 Per-span ΔES Score Gap by endgame type

**Per-class pooled (per-user `mean(gap_span)`, sparse excluded):**

| class | n_users | p25 | p50 | p75 |
|---|---:|---:|---:|---:|
| rook | 2,841 | −5.1pp | +0.1pp | +4.8pp |
| minor_piece | 2,332 | −4.8pp | +0.3pp | +5.6pp |
| pawn | 1,417 | −3.8pp | +0.6pp | +5.0pp |
| queen | 1,307 | −4.2pp | +0.5pp | +5.4pp |
| mixed | 4,587 | −3.1pp | +0.5pp | +3.8pp |
| pawnless | 12 | −1.1pp | +0.6pp | +3.8pp |

**Collapse verdicts (per class):** TC d 0.06–0.20 → **all collapse**. ELO d 0.14–0.31 → **all collapse/review** (minor_piece 0.30, mixed 0.31 highest, both review).

**Recommendation:** per-class IQRs near-symmetric around 0, widths 6.6pp (mixed) → 9.7pp (minor_piece). Live per-class `achievable_score_gap` bands (rook ±0.05, minor_piece [−0.04,+0.06], pawn/queen [−0.04,+0.05], mixed [−0.03,+0.04]) match within ~0.5pp → **keep per-class bands**; global default `endgame_type_achievable_score_gap = ±0.04` stays valid.

---

#### 3.4.3 Endgame Type Score vs Score Gap — agreement / redundancy

| class | n_users | Pearson r | sign_agree | strict zone-agree | strong disagree | score SD | gap SD |
|---|---:|---:|---:|---:|---:|---:|---:|
| mixed | 5,274 | +0.105 | 46.3% | 42.2% | 9.0% | 0.149 | 0.049 |

Only `mixed` clears the ≥30-joined-user floor at the combined ≥10-game + ≥20-span gates. Independence baselines (r=0): strict zone-agree 37.5%, strong-disagree 12.5%.

**Verdict:** Pearson r = **+0.105** (far below the 0.60 redundancy floor); strict zone-agreement 42.2% only ~4.7pp above the r=0 baseline. Score and Score Gap read **different things** → **keep all three signals** (Score bullet, Score Gap bullet, WDL) on `EndgameTypeCard.tsx`. Layout decision only, no code constant.

---

## 5. Flaw-Delta Zones

> **Basis (Phase 239 D-07/D-08)**: the full-analysis lane only (classical + rapid tranches of
> `benchmark_selection`: armed games with full evals, full PVs and tactic blobs done).
> Blitz and bullet are not computed here; the app registries map them to the rapid zones
> (D-09 stopgap) until their full-analysis samples finish.
>
> **Owner override (239-06 checkpoint)**: the flaw-delta bands below are the noise-inflated
> proposal that was NOT adopted; the app keeps the live flaw bands (see the registry mapping
> table at the end of this report). The tactic bands (5.13) are adopted as measured.
>
> **D-01 unified estimator**: per game, delta = (player_tag_count − opp_tag_count)
> / user_moves_in_game (proportion); displayed as per-100-moves via ×100 at the
> render layer ("pp" unit). user_moves derived from `games.ply_count` (Phase 114.1):
> FLOOR(ply_count/2) for white, CEIL(ply_count/2) for black — no game_positions scan.
> Per-cohort-user delta = mean
> over ≥20 analyzed games. Negative delta means cohort
> users commit fewer flaws of this type than equally-rated opponents.
>
> **Cell floor**: marginal levels with <30 contributing
> user-cells are removed from the marginals and verdicts (listed as thin levels);
> a registry author falls back to the pooled band for them (D-10).
> **Sparse cell**: (2400, classical) excluded from marginals and verdicts (see §1).

> **Snapshot**: 2026-10-12T21:01Z (one run of `uv run python -m scripts.benchmarks.chapter5 --db benchmark`; classical 99.9% and rapid 99.9% complete in `benchmark_selection` at that moment; 138,104 analyzed games, 2,006 user×(ELO,TC) cells, 1,590 distinct users). The old whole-cohort basis (`evals_completed_at`, 1,223,105 games, up to 1000 games per user) is retired; the lane caps each user at 100 games per TC, so every per-user mean is far noisier than before and the bands are wider (see §5.15).
>
> **Blitz and bullet read the rapid zones in the app** until their full-analysis tranches finish (D-08/D-09 stopgap, `ZONE_TC_FOR` in the registries, silent in the UI). Refresh: add the tranche to `FULL_ANALYSIS_TRANCHES`, re-run §5.
>
> **Retired in Phase 239**: the overall flaw rate and the two combo flaws no longer have a zone; the Library shows 12 flaw metrics and 38 tactic metrics (19 families × Missed/Allowed).

### 5.1 Mistakes (severity = 1)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | −0.1pp | 0.9pp | −1.527pp | −0.652pp | −0.136pp | +0.390pp | +1.342pp |

Noise-only IQR: 1.022pp (observed IQR: 1.041pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 1.3pp | −1.837pp | −0.705pp | −0.061pp | +0.660pp | +2.096pp |
| 1200 | 503 | −0.1pp | 1.1pp | −1.897pp | −0.792pp | −0.163pp | +0.519pp | +1.544pp |
| 1600 | 549 | −0.1pp | 0.8pp | −1.358pp | −0.558pp | −0.132pp | +0.349pp | +1.103pp |
| 2000 | 436 | −0.2pp | 0.7pp | −1.305pp | −0.620pp | −0.151pp | +0.269pp | +0.965pp |
| 2400 | 162 | −0.2pp | 0.6pp | −1.064pp | −0.540pp | −0.115pp | +0.187pp | +0.715pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | −0.1pp | 0.9pp | −1.426pp | −0.630pp | −0.150pp | +0.371pp | +1.215pp |
| classical | 733 | −0.1pp | 1.1pp | −1.752pp | −0.690pp | −0.106pp | +0.439pp | +1.421pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.00** (rapid vs classical)
- **ELO axis**: max |d| = **0.18** (800 vs 2000)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.00, rapid vs classical)
- **ELO verdict**: collapse (max |d| = 0.18, 800 vs 2000)
- ELO mean by level (pp): 800 +0.00, 1200 −0.15, 1600 −0.14, 2000 −0.18, 2400 −0.16 (not monotone)
- **Currently set in code**: [−0.23, +0.20] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 1.022pp against an observed IQR of 1.041pp (noise share 98%): the band is essentially sampling noise: it is about what per-user means would spread to if every user had the same true gap.

**Recommendation**: one pooled band for both zone TCs: **[−0.66, +0.39] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: collapse). Versus the live band this is 2.4x as wide (0.43 to 1.05). Negative delta = fewer flaws than equally rated opponents = good.

---

### 5.2 Blunders (severity = 2)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | −0.3pp | 1.0pp | −1.949pp | −0.826pp | −0.213pp | +0.307pp | +1.228pp |

Noise-only IQR: 1.102pp (observed IQR: 1.133pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | −0.3pp | 1.3pp | −2.425pp | −1.085pp | −0.163pp | +0.479pp | +1.480pp |
| 1200 | 503 | −0.4pp | 1.2pp | −2.339pp | −1.043pp | −0.332pp | +0.322pp | +1.485pp |
| 1600 | 549 | −0.2pp | 0.9pp | −1.802pp | −0.724pp | −0.181pp | +0.344pp | +1.155pp |
| 2000 | 436 | −0.3pp | 0.8pp | −1.512pp | −0.720pp | −0.212pp | +0.209pp | +0.885pp |
| 2400 | 162 | −0.2pp | 0.5pp | −1.151pp | −0.609pp | −0.214pp | +0.108pp | +0.635pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | −0.2pp | 0.9pp | −1.733pp | −0.778pp | −0.196pp | +0.311pp | +1.217pp |
| classical | 733 | −0.4pp | 1.1pp | −2.279pp | −0.971pp | −0.257pp | +0.305pp | +1.236pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.15** (rapid vs classical)
- **ELO axis**: max |d| = **0.14** (1200 vs 1600)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.15, rapid vs classical)
- **ELO verdict**: collapse (max |d| = 0.14, 1200 vs 1600)
- ELO mean by level (pp): 800 −0.30, 1200 −0.36, 1600 −0.21, 2000 −0.26, 2400 −0.25 (not monotone)
- **Currently set in code**: [−0.31, +0.25] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 1.102pp against an observed IQR of 1.133pp (noise share 97%): the band is essentially sampling noise: it is about what per-user means would spread to if every user had the same true gap.

**Recommendation**: one pooled band for both zone TCs: **[−0.83, +0.31] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: collapse). Versus the live band this is 2.0x as wide (0.56 to 1.14). Negative delta = fewer flaws than equally rated opponents = good.

---

### 5.3 Low-Clock Flaws (tempo = 0)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | +0.0pp | 0.3pp | −0.385pp | −0.118pp | +0.000pp | +0.050pp | +0.549pp |

Noise-only IQR: 0.238pp (observed IQR: 0.167pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 0.2pp | −0.175pp | −0.053pp | +0.000pp | +0.000pp | +0.290pp |
| 1200 | 503 | +0.0pp | 0.2pp | −0.239pp | −0.072pp | +0.000pp | +0.000pp | +0.256pp |
| 1600 | 549 | +0.0pp | 0.3pp | −0.316pp | −0.109pp | −0.007pp | +0.062pp | +0.705pp |
| 2000 | 436 | +0.0pp | 0.4pp | −0.563pp | −0.202pp | −0.038pp | +0.146pp | +0.762pp |
| 2400 | 162 | −0.1pp | 0.4pp | −0.618pp | −0.303pp | −0.080pp | +0.153pp | +0.606pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | +0.0pp | 0.3pp | −0.398pp | −0.137pp | −0.023pp | +0.077pp | +0.609pp |
| classical | 733 | +0.0pp | 0.3pp | −0.319pp | −0.074pp | +0.000pp | +0.000pp | +0.456pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.03** (rapid vs classical)
- **ELO axis**: max |d| = **0.25** (1600 vs 2400)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.03, rapid vs classical)
- **ELO verdict**: review (max |d| = 0.25, 1600 vs 2400)
- ELO mean by level (pp): 800 +0.01, 1200 −0.00, 1600 +0.03, 2000 +0.01, 2400 −0.05 (not monotone)
- **Currently set in code**: [−0.08, +0.03] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 0.238pp against an observed IQR of 0.167pp (noise share 142%): the closed-form noise-only IQR meets or exceeds the observed IQR, so none of the band can be read as a real between-user difference (the per-game deltas are zero-inflated and skewed, which makes the closed form conservative, but the direction is unambiguous).

**Recommendation**: one pooled band for both zone TCs: **[−0.12, +0.05] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: review). Versus the live band this is 1.5x as wide (0.11 to 0.17). Negative delta = fewer flaws than equally rated opponents = good.

**Thin numerator**: only 59.1% of user-cells have at least one player low-clock flaw (median 2 events per user), below the 80% flag threshold. The classical marginal's p75 is +0.000pp, so the upper edge of the typical range sits at zero there. The registry still gets a band (`zone_viable`), but the owner may prefer to hold this metric back.

---

### 5.4 Hasty Flaws (tempo = 1)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | −0.4pp | 1.6pp | −2.983pp | −1.151pp | −0.352pp | +0.442pp | +2.185pp |

Noise-only IQR: 1.126pp (observed IQR: 1.593pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | −0.6pp | 2.2pp | −4.283pp | −1.996pp | −0.621pp | +0.765pp | +2.989pp |
| 1200 | 503 | −0.6pp | 2.0pp | −3.694pp | −1.675pp | −0.728pp | +0.741pp | +2.659pp |
| 1600 | 549 | −0.3pp | 1.3pp | −2.201pp | −1.145pp | −0.325pp | +0.432pp | +1.737pp |
| 2000 | 436 | −0.2pp | 0.8pp | −1.302pp | −0.699pp | −0.237pp | +0.249pp | +1.181pp |
| 2400 | 162 | −0.1pp | 0.6pp | −0.899pp | −0.471pp | −0.112pp | +0.307pp | +0.879pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | −0.2pp | 1.2pp | −2.202pp | −0.964pp | −0.298pp | +0.434pp | +1.846pp |
| classical | 733 | −0.6pp | 2.0pp | −4.176pp | −1.651pp | −0.500pp | +0.530pp | +2.717pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.21** (rapid vs classical)
- **ELO axis**: max |d| = **0.28** (1200 vs 2400)

#### Verdicts and recommendation

- **TC verdict**: review (max |d| = 0.21, rapid vs classical)
- **ELO verdict**: review (max |d| = 0.28, 1200 vs 2400)
- ELO mean by level (pp): 800 −0.58, 1200 −0.56, 1600 −0.31, 2000 −0.17, 2400 −0.07 (monotone rising)
- **Currently set in code**: [−0.28, +0.18] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 1.126pp against an observed IQR of 1.593pp (noise share 71%): most of the band is sampling noise, with a small real between-user component.

**Recommendation**: one pooled band for both zone TCs: **[−1.16, +0.45] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: review). Versus the live band this is 3.5x as wide (0.46 to 1.61). Negative delta = fewer flaws than equally rated opponents = good.

TC is a `review` verdict (d = 0.21): the rapid marginal IQR is [−0.97, +0.44] and the classical one is [−1.66, +0.53]. The verdict rule keeps the pooled band; per-TC bands are the owner's alternative if the classical tail should be honoured.

---

### 5.5 Unrushed Flaws (tempo = 2)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | +0.0pp | 1.5pp | −2.308pp | −0.939pp | −0.102pp | +0.733pp | +2.653pp |

Noise-only IQR: 1.165pp (observed IQR: 1.672pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.3pp | 2.0pp | −3.088pp | −0.891pp | +0.230pp | +1.310pp | +3.902pp |
| 1200 | 503 | +0.1pp | 1.8pp | −2.782pp | −1.147pp | −0.043pp | +1.096pp | +3.122pp |
| 1600 | 549 | −0.1pp | 1.3pp | −2.210pp | −0.929pp | −0.056pp | +0.638pp | +2.079pp |
| 2000 | 436 | −0.3pp | 1.0pp | −1.930pp | −0.851pp | −0.204pp | +0.346pp | +1.182pp |
| 2400 | 162 | −0.3pp | 0.8pp | −1.724pp | −0.783pp | −0.212pp | +0.218pp | +0.990pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | −0.1pp | 1.3pp | −2.218pp | −0.860pp | −0.122pp | +0.664pp | +2.030pp |
| classical | 733 | +0.1pp | 1.8pp | −2.552pp | −1.085pp | −0.043pp | +0.928pp | +3.487pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.11** (rapid vs classical)
- **ELO axis**: max |d| = **0.36** (800 vs 2000)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.11, rapid vs classical)
- **ELO verdict**: review (max |d| = 0.36, 800 vs 2000)
- ELO mean by level (pp): 800 +0.27, 1200 +0.06, 1600 −0.07, 2000 −0.27, 2400 −0.27 (monotone falling)
- **Currently set in code**: [−0.38, +0.36] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 1.165pp against an observed IQR of 1.672pp (noise share 70%): most of the band is sampling noise, with a small real between-user component.

**Recommendation**: one pooled band for both zone TCs: **[−0.94, +0.74] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: review). Versus the live band this is 2.3x as wide (0.74 to 1.68). Negative delta = fewer flaws than equally rated opponents = good.

---

### 5.6 Opening-Phase Flaws (phase = 0)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | −0.2pp | 1.0pp | −1.892pp | −0.595pp | −0.143pp | +0.268pp | +1.262pp |

Noise-only IQR: 1.080pp (observed IQR: 0.863pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | −0.3pp | 1.5pp | −2.944pp | −1.066pp | −0.299pp | +0.603pp | +2.292pp |
| 1200 | 503 | −0.4pp | 1.2pp | −2.482pp | −1.021pp | −0.323pp | +0.363pp | +1.586pp |
| 1600 | 549 | −0.1pp | 0.7pp | −1.267pp | −0.497pp | −0.141pp | +0.269pp | +1.042pp |
| 2000 | 436 | −0.1pp | 0.5pp | −0.906pp | −0.314pp | −0.055pp | +0.201pp | +0.750pp |
| 2400 | 162 | −0.1pp | 0.3pp | −0.681pp | −0.272pp | −0.086pp | +0.072pp | +0.318pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | −0.1pp | 0.8pp | −1.473pp | −0.507pp | −0.105pp | +0.256pp | +1.138pp |
| classical | 733 | −0.3pp | 1.2pp | −2.550pp | −0.829pp | −0.228pp | +0.287pp | +1.476pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.20** (rapid vs classical)
- **ELO axis**: max |d| = **0.33** (1200 vs 2000)

#### Verdicts and recommendation

- **TC verdict**: review (max |d| = 0.20, rapid vs classical)
- **ELO verdict**: review (max |d| = 0.33, 1200 vs 2000)
- ELO mean by level (pp): 800 −0.31, 1200 −0.37, 1600 −0.13, 2000 −0.05, 2400 −0.12 (not monotone)
- **Currently set in code**: [−0.15, +0.13] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 1.080pp against an observed IQR of 0.863pp (noise share 125%): the closed-form noise-only IQR meets or exceeds the observed IQR, so none of the band can be read as a real between-user difference (the per-game deltas are zero-inflated and skewed, which makes the closed form conservative, but the direction is unambiguous).

**Recommendation**: one pooled band for both zone TCs: **[−0.60, +0.27] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: review). Versus the live band this is 3.1x as wide (0.28 to 0.87). Negative delta = fewer flaws than equally rated opponents = good.

TC is a `review` verdict (d = 0.20): the rapid marginal IQR is [−0.51, +0.26] and the classical one is [−0.83, +0.29]. The verdict rule keeps the pooled band; per-TC bands are the owner's alternative.

---

### 5.7 Middlegame Flaws (phase = 1)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | −0.2pp | 0.8pp | −1.494pp | −0.616pp | −0.108pp | +0.341pp | +1.035pp |

Noise-only IQR: 0.869pp (observed IQR: 0.957pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 0.8pp | −1.386pp | −0.446pp | +0.019pp | +0.486pp | +1.127pp |
| 1200 | 503 | −0.1pp | 0.8pp | −1.496pp | −0.602pp | −0.021pp | +0.376pp | +1.034pp |
| 1600 | 549 | −0.2pp | 0.8pp | −1.498pp | −0.665pp | −0.146pp | +0.342pp | +1.026pp |
| 2000 | 436 | −0.3pp | 0.8pp | −1.577pp | −0.708pp | −0.257pp | +0.203pp | +0.915pp |
| 2400 | 162 | −0.2pp | 0.7pp | −1.288pp | −0.542pp | −0.104pp | +0.241pp | +0.760pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | −0.2pp | 0.8pp | −1.429pp | −0.617pp | −0.135pp | +0.324pp | +1.025pp |
| classical | 733 | −0.2pp | 0.8pp | −1.676pp | −0.605pp | −0.063pp | +0.368pp | +1.066pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.02** (rapid vs classical)
- **ELO axis**: max |d| = **0.34** (800 vs 2000)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.02, rapid vs classical)
- **ELO verdict**: review (max |d| = 0.34, 800 vs 2000)
- ELO mean by level (pp): 800 −0.02, 1200 −0.13, 1600 −0.19, 2000 −0.28, 2400 −0.17 (not monotone)
- **Currently set in code**: [−0.27, +0.23] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 0.869pp against an observed IQR of 0.957pp (noise share 91%): the band is essentially sampling noise: it is about what per-user means would spread to if every user had the same true gap.

**Recommendation**: one pooled band for both zone TCs: **[−0.62, +0.35] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: review). Versus the live band this is 1.9x as wide (0.50 to 0.97). Negative delta = fewer flaws than equally rated opponents = good.

---

### 5.8 Endgame-Phase Flaws (phase = 2)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | +0.0pp | 0.4pp | −0.657pp | −0.233pp | −0.022pp | +0.180pp | +0.528pp |

Noise-only IQR: 0.421pp (observed IQR: 0.413pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 0.3pp | −0.446pp | −0.157pp | +0.008pp | +0.202pp | +0.553pp |
| 1200 | 503 | +0.0pp | 0.4pp | −0.684pp | −0.194pp | +0.017pp | +0.187pp | +0.564pp |
| 1600 | 549 | +0.0pp | 0.4pp | −0.621pp | −0.234pp | −0.006pp | +0.192pp | +0.512pp |
| 2000 | 436 | −0.1pp | 0.4pp | −0.736pp | −0.300pp | −0.070pp | +0.137pp | +0.429pp |
| 2400 | 162 | −0.1pp | 0.4pp | −0.680pp | −0.356pp | −0.113pp | +0.116pp | +0.445pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | +0.0pp | 0.4pp | −0.656pp | −0.248pp | −0.036pp | +0.177pp | +0.512pp |
| classical | 733 | +0.0pp | 0.4pp | −0.658pp | −0.205pp | +0.012pp | +0.190pp | +0.530pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.09** (rapid vs classical)
- **ELO axis**: max |d| = **0.44** (800 vs 2400)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.09, rapid vs classical)
- **ELO verdict**: review (max |d| = 0.44, 800 vs 2400)
- ELO mean by level (pp): 800 +0.03, 1200 −0.01, 1600 −0.03, 2000 −0.10, 2400 −0.11 (monotone falling)
- **Currently set in code**: [−0.12, +0.10] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 0.421pp against an observed IQR of 0.413pp (noise share 102%): the closed-form noise-only IQR meets or exceeds the observed IQR, so none of the band can be read as a real between-user difference (the per-game deltas are zero-inflated and skewed, which makes the closed form conservative, but the direction is unambiguous).

**Recommendation**: one pooled band for both zone TCs: **[−0.24, +0.18] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: review). Versus the live band this is 1.9x as wide (0.22 to 0.42). Negative delta = fewer flaws than equally rated opponents = good.

The ELO axis is the strongest of the 12 (`review`, d = 0.44, below the 0.5 keep-separate line): no Elo keying is triggered, but it is the metric closest to it.

---

### 5.9 Missed-Win Flaws (is_miss)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | +0.0pp | 0.5pp | −0.856pp | −0.314pp | −0.015pp | +0.270pp | +0.795pp |

Noise-only IQR: 0.652pp (observed IQR: 0.584pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 0.8pp | −1.358pp | −0.465pp | −0.027pp | +0.415pp | +1.212pp |
| 1200 | 503 | +0.0pp | 0.6pp | −0.972pp | −0.389pp | −0.032pp | +0.328pp | +0.941pp |
| 1600 | 549 | +0.0pp | 0.4pp | −0.749pp | −0.290pp | −0.008pp | +0.251pp | +0.698pp |
| 2000 | 436 | +0.0pp | 0.3pp | −0.532pp | −0.264pp | −0.013pp | +0.176pp | +0.490pp |
| 2400 | 162 | +0.0pp | 0.3pp | −0.464pp | −0.125pp | +0.009pp | +0.194pp | +0.533pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | +0.0pp | 0.5pp | −0.817pp | −0.290pp | −0.015pp | +0.257pp | +0.704pp |
| classical | 733 | +0.0pp | 0.6pp | −0.977pp | −0.342pp | −0.015pp | +0.305pp | +0.926pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.02** (rapid vs classical)
- **ELO axis**: max |d| = **0.16** (2000 vs 2400)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.02, rapid vs classical)
- **ELO verdict**: collapse (max |d| = 0.16, 2000 vs 2400)
- ELO mean by level (pp): 800 −0.04, 1200 −0.02, 1600 −0.01, 2000 −0.03, 2400 +0.02 (not monotone)
- **Currently set in code**: [−0.11, +0.11] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 0.652pp against an observed IQR of 0.584pp (noise share 112%): the closed-form noise-only IQR meets or exceeds the observed IQR, so none of the band can be read as a real between-user difference (the per-game deltas are zero-inflated and skewed, which makes the closed form conservative, but the direction is unambiguous).

**Recommendation**: one pooled band for both zone TCs: **[−0.32, +0.28] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: collapse). Versus the live band this is 2.7x as wide (0.22 to 0.60). Negative delta = fewer flaws than equally rated opponents = good.

---

### 5.10 Lucky-Escape Flaws (is_lucky)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | +0.0pp | 0.5pp | −0.685pp | −0.223pp | +0.002pp | +0.251pp | +0.736pp |

Noise-only IQR: 0.559pp (observed IQR: 0.474pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 0.7pp | −1.048pp | −0.362pp | +0.076pp | +0.392pp | +1.172pp |
| 1200 | 503 | +0.0pp | 0.5pp | −0.870pp | −0.283pp | +0.007pp | +0.334pp | +0.930pp |
| 1600 | 549 | +0.0pp | 0.4pp | −0.559pp | −0.210pp | −0.009pp | +0.226pp | +0.590pp |
| 2000 | 436 | +0.0pp | 0.3pp | −0.381pp | −0.153pp | −0.005pp | +0.166pp | +0.441pp |
| 2400 | 162 | +0.0pp | 0.2pp | −0.378pp | −0.151pp | −0.016pp | +0.116pp | +0.394pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | +0.0pp | 0.4pp | −0.623pp | −0.224pp | −0.006pp | +0.223pp | +0.662pp |
| classical | 733 | +0.0pp | 0.6pp | −0.877pp | −0.223pp | +0.025pp | +0.292pp | +0.939pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.07** (rapid vs classical)
- **ELO axis**: max |d| = **0.09** (1200 vs 2400)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.07, rapid vs classical)
- **ELO verdict**: collapse (max |d| = 0.09, 1200 vs 2400)
- ELO mean by level (pp): 800 +0.04, 1200 +0.03, 1600 +0.00, 2000 +0.01, 2400 −0.01 (not monotone)
- **Currently set in code**: [−0.09, +0.09] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 0.559pp against an observed IQR of 0.474pp (noise share 118%): the closed-form noise-only IQR meets or exceeds the observed IQR, so none of the band can be read as a real between-user difference (the per-game deltas are zero-inflated and skewed, which makes the closed form conservative, but the direction is unambiguous).

**Recommendation**: one pooled band for both zone TCs: **[−0.23, +0.26] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: collapse). Versus the live band this is 2.7x as wide (0.18 to 0.49). Negative delta = fewer flaws than equally rated opponents = good.

State-conditional (D-03): under ELO-matched pairing this reads partly as 'how often the situation arose', not purely luck.

---

### 5.11 Reversed Advantage Flaws (is_reversed)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | +0.0pp | 0.3pp | −0.421pp | −0.116pp | −0.007pp | +0.101pp | +0.349pp |

Noise-only IQR: 0.300pp (observed IQR: 0.217pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 0.4pp | −0.744pp | −0.271pp | −0.021pp | +0.183pp | +0.585pp |
| 1200 | 503 | +0.0pp | 0.3pp | −0.449pp | −0.179pp | −0.005pp | +0.155pp | +0.426pp |
| 1600 | 549 | +0.0pp | 0.2pp | −0.299pp | −0.103pp | −0.005pp | +0.090pp | +0.274pp |
| 2000 | 436 | +0.0pp | 0.1pp | −0.222pp | −0.077pp | +0.000pp | +0.070pp | +0.186pp |
| 2400 | 162 | +0.0pp | 0.1pp | −0.161pp | −0.058pp | −0.012pp | +0.028pp | +0.125pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | +0.0pp | 0.2pp | −0.377pp | −0.117pp | −0.007pp | +0.093pp | +0.338pp |
| classical | 733 | +0.0pp | 0.3pp | −0.464pp | −0.113pp | −0.005pp | +0.111pp | +0.385pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.01** (rapid vs classical)
- **ELO axis**: max |d| = **0.13** (800 vs 1600)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.01, rapid vs classical)
- **ELO verdict**: collapse (max |d| = 0.13, 800 vs 1600)
- ELO mean by level (pp): 800 −0.04, 1200 −0.01, 1600 −0.01, 2000 −0.01, 2400 −0.02 (not monotone)
- **Currently set in code**: [−0.04, +0.04] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 0.300pp against an observed IQR of 0.217pp (noise share 138%): the closed-form noise-only IQR meets or exceeds the observed IQR, so none of the band can be read as a real between-user difference (the per-game deltas are zero-inflated and skewed, which makes the closed form conservative, but the direction is unambiguous).

**Recommendation**: one pooled band for both zone TCs: **[−0.12, +0.11] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: collapse). Versus the live band this is 2.9x as wide (0.08 to 0.23). Negative delta = fewer flaws than equally rated opponents = good.

---

### 5.12 Squandered Win Flaws (is_squandered)

#### Pooled distribution (you − opponent delta, per 100 moves)

| n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,004 | +0.0pp | 0.3pp | −0.533pp | −0.166pp | +0.014pp | +0.190pp | +0.519pp |

Noise-only IQR: 0.410pp (observed IQR: 0.356pp)

#### ELO marginal

| ELO | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 800 | 354 | +0.0pp | 0.5pp | −0.806pp | −0.304pp | +0.001pp | +0.317pp | +0.838pp |
| 1200 | 503 | +0.0pp | 0.4pp | −0.567pp | −0.200pp | +0.027pp | +0.223pp | +0.605pp |
| 1600 | 549 | +0.0pp | 0.3pp | −0.411pp | −0.137pp | +0.022pp | +0.184pp | +0.438pp |
| 2000 | 436 | +0.0pp | 0.2pp | −0.342pp | −0.122pp | +0.018pp | +0.164pp | +0.381pp |
| 2400 | 162 | +0.0pp | 0.2pp | −0.370pp | −0.098pp | −0.013pp | +0.103pp | +0.281pp |

#### TC marginal

| TC | n | mean | SD | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rapid | 1,271 | +0.0pp | 0.3pp | −0.470pp | −0.156pp | +0.020pp | +0.191pp | +0.499pp |
| classical | 733 | +0.0pp | 0.4pp | −0.610pp | −0.185pp | +0.010pp | +0.190pp | +0.573pp |

#### Collapse verdict

- **TC axis**: max |d| = **0.03** (rapid vs classical)
- **ELO axis**: max |d| = **0.11** (2000 vs 2400)

#### Verdicts and recommendation

- **TC verdict**: collapse (max |d| = 0.03, rapid vs classical)
- **ELO verdict**: collapse (max |d| = 0.11, 2000 vs 2400)
- ELO mean by level (pp): 800 +0.00, 1200 +0.01, 1600 +0.01, 2000 +0.02, 2400 −0.01 (not monotone)
- **Currently set in code**: [−0.07, +0.08] per 100 moves, one pooled band for every TC (whole-cohort Lichess-eval basis, carried over unchanged by plan 239-02).
- **Noise**: noise-only IQR 0.410pp against an observed IQR of 0.356pp (noise share 115%): the closed-form noise-only IQR meets or exceeds the observed IQR, so none of the band can be read as a real between-user difference (the per-game deltas are zero-inflated and skewed, which makes the closed form conservative, but the direction is unambiguous).

**Recommendation**: one pooled band for both zone TCs: **[−0.17, +0.19] per 100 moves** (p25 and p75 of the pooled distribution rounded outward to the 0.01 grid). Elo keying: none (ELO verdict: collapse). Versus the live band this is 2.4x as wide (0.15 to 0.36). Negative delta = fewer flaws than equally rated opponents = good.

State-conditional (D-03): under ELO-matched pairing this reads partly as 'how often the situation arose', not purely conversion skill.

---

### 5.13 Tactic Missed/Allowed Zones (D-06)

> One row per tactic family and orientation. Value = per-user mean over ≥20 analyzed games of the per-game count difference
> (your tactic flaws − opponent's) whose motif is in the family's `FAMILY_TO_MOTIF_INTS`
> ints and whose confidence is ≥ 70; shown per 100 games
> ("per100g" unit). Negative = you commit/allow fewer than equally-rated opponents.
> `n/a` = a thin TC level (<30 user-cells) or a verdict that could not be computed.

| family | orientation | n | p25 | p50 | p75 | rapid p25 to p75 | classical p25 to p75 | TC max abs d | ELO max abs d | pct_nonzero | noise-only IQR | zone_viable |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fork | missed | 2,004 | −2.20 | +0.00 | +2.13 | −2.33 to +2.13 | −2.00 to +2.13 | 0.04 (collapse) | 0.05 (collapse) | 79.2% | 5.37 | yes |
| fork | allowed | 2,004 | −4.11 | +0.00 | +3.23 | −4.10 to +3.11 | −4.11 to +3.53 | 0.01 (collapse) | 0.14 (collapse) | 93.8% | 8.06 | yes |
| skewer | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.05 (collapse) | 0.04 (collapse) | 23.1% | 1.78 | no |
| skewer | allowed | 2,004 | +0.00 | +0.00 | +0.00 | −1.00 to +1.00 | +0.00 to +0.00 | 0.04 (collapse) | 0.07 (collapse) | 35.6% | 2.38 | no |
| pin | missed | 2,004 | −1.41 | +0.00 | +1.89 | −1.54 to +2.00 | −1.25 to +1.69 | 0.04 (collapse) | 0.08 (collapse) | 66.1% | 3.95 | yes |
| pin | allowed | 2,004 | −2.86 | +0.00 | +2.04 | −2.63 to +2.07 | −3.00 to +2.00 | 0.05 (collapse) | 0.12 (collapse) | 80.0% | 5.20 | yes |
| x_ray | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.02 (collapse) | 0.10 (collapse) | 1.1% | 0.41 | no |
| x_ray | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.02 (collapse) | 0.10 (collapse) | 1.5% | 0.39 | no |
| double_check | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.06 (collapse) | 0.08 (collapse) | 4.1% | 0.69 | no |
| double_check | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.00 (collapse) | 0.11 (collapse) | 7.9% | 0.96 | no |
| discovered_check | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.01 (collapse) | 0.12 (collapse) | 25.8% | 1.92 | no |
| discovered_check | allowed | 2,004 | −1.00 | +0.00 | +1.00 | −1.00 to +1.00 | −1.00 to +1.00 | 0.06 (collapse) | 0.06 (collapse) | 41.7% | 2.60 | no |
| discovered_attack | missed | 2,004 | +0.00 | +0.00 | +0.00 | −1.00 to +0.00 | +0.00 to +0.00 | 0.01 (collapse) | 0.09 (collapse) | 37.3% | 2.40 | no |
| discovered_attack | allowed | 2,004 | −1.23 | +0.00 | +1.06 | −1.28 to +1.09 | −1.19 to +1.01 | 0.01 (collapse) | 0.08 (collapse) | 55.3% | 3.15 | yes |
| trapped_piece | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.06 (collapse) | 0.22 (review) | 23.6% | 1.75 | no |
| trapped_piece | allowed | 2,004 | +0.00 | +0.00 | +0.25 | −1.00 to +1.00 | +0.00 to +0.00 | 0.05 (collapse) | 0.18 (collapse) | 37.4% | 2.30 | no |
| hanging | missed | 2,004 | −1.13 | +0.00 | +1.48 | −1.18 to +1.57 | −1.04 to +1.41 | 0.00 (collapse) | 0.20 (review) | 61.4% | 4.43 | yes |
| hanging | allowed | 2,004 | −5.10 | −1.00 | +3.03 | −5.00 to +3.09 | −5.36 to +2.86 | 0.05 (collapse) | 0.15 (collapse) | 92.8% | 9.03 | yes |
| mate | missed | 2,004 | −2.17 | +0.00 | +2.90 | −2.33 to +2.78 | −1.89 to +3.00 | 0.06 (collapse) | 0.14 (collapse) | 78.9% | 6.50 | yes |
| mate | allowed | 2,004 | −7.00 | −1.16 | +4.09 | −7.00 to +4.00 | −7.00 to +4.35 | 0.03 (collapse) | 0.06 (collapse) | 95.8% | 10.55 | yes |
| deflection | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.04 (collapse) | 0.23 (review) | 30.4% | 1.97 | no |
| deflection | allowed | 2,004 | −1.00 | +0.00 | +1.00 | −1.02 to +1.00 | +0.00 to +1.00 | 0.06 (collapse) | 0.23 (review) | 40.4% | 2.46 | no |
| intermezzo | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.03 (collapse) | 0.15 (collapse) | 11.7% | 1.15 | no |
| intermezzo | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.07 (collapse) | 0.22 (review) | 18.3% | 1.43 | no |
| interference | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.09 (collapse) | 0.12 (collapse) | 5.4% | 0.74 | no |
| interference | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.03 (collapse) | 0.15 (collapse) | 7.8% | 0.92 | no |
| capturing_defender | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.04 (collapse) | 0.28 (review) | 7.9% | 0.88 | no |
| capturing_defender | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.05 (collapse) | 0.23 (review) | 13.0% | 1.28 | no |
| attraction | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +1.00 | +0.00 to +0.00 | 0.07 (collapse) | 0.10 (collapse) | 34.1% | 2.16 | no |
| attraction | allowed | 2,004 | −1.01 | +0.00 | +1.00 | −1.05 to +1.00 | +0.00 to +1.00 | 0.13 (collapse) | 0.11 (collapse) | 43.2% | 2.55 | no |
| sacrifice | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.01 (collapse) | 0.11 (collapse) | 33.3% | 2.16 | no |
| sacrifice | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.04 (collapse) | 0.11 (collapse) | 32.5% | 2.15 | no |
| en_passant | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.01 (collapse) | 0.08 (collapse) | 6.1% | 0.72 | no |
| en_passant | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.05 (collapse) | 0.24 (review) | 9.9% | 0.95 | no |
| under_promotion | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.07 (collapse) | 0.10 (collapse) | 0.2% | 0.20 | no |
| under_promotion | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.04 (collapse) | 0.10 (collapse) | 0.5% | 0.29 | no |
| promotion | missed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.07 (collapse) | 0.12 (collapse) | 21.0% | 1.58 | no |
| promotion | allowed | 2,004 | +0.00 | +0.00 | +0.00 | +0.00 to +0.00 | +0.00 to +0.00 | 0.05 (collapse) | 0.09 (collapse) | 31.2% | 2.05 | no |

#### Tactic verdicts and viability narrative

Verdict words are in the `TC max abs d` and `ELO max abs d` columns above (collapse < 0.2, review 0.2 to 0.5, keep separate >= 0.5). On the TC axis (rapid vs classical) every one of the 38 tactic metrics is a `collapse` (largest d = 0.13); on the ELO axis 30 collapse and 8 are `review` (largest d = 0.28). Nothing reaches keep-separate, so no tactic metric needs Elo keying and every viable family gets one pooled band for both zone TCs.

**Viable (9 of 38, `has_zone = true`)**: fork (missed), fork (allowed), pin (missed), pin (allowed), discovered attack (allowed), hanging (missed), hanging (allowed), mate (missed), mate (allowed). These are the families where at least half of the user-cells have one or more events (55.3% to 95.8% non-zero) and the pooled IQR has width.

**Not viable (29 of 38, `has_zone = false`)**: all 29 are below 50% non-zero (from 43.2% for attraction allowed down to 0.2% for under-promotion missed); 25 of them also have a degenerate pooled IQR (p25 = p75 = 0), so a band would be zero-width and would paint any non-zero gap as better or worse than typical. The remaining 4 have a non-degenerate IQR but still fail the 50% rule: discovered check allowed (41.7%), trapped piece allowed (37.4%), deflection allowed (40.4%), attraction allowed (43.2%). `tactic_trapped_piece_allowed` shows a 918% noise share (observed IQR 0.25 per 100 games against 2.30 noise-only).

**Noise**: every viable tactic metric has a noise share between 95% and 170% (see §5.15): at 100 games per user the per-user spread of rare events is almost entirely Poisson noise. The bands below are what the lane measures; they are not evidence of real between-user differences.

#### Proposed tactic bands (pooled, both zone TCs, per 100 games)

| family | orientation | proposed band | live band | TC verdict | ELO verdict | noise share |
|---|---|---:|---|---|---|---:|
| fork | missed | [−2.21, +2.13] | none (band-less) | collapse (0.04) | collapse (0.05) | 124% |
| fork | allowed | [−4.12, +3.23] | none (band-less) | collapse (0.01) | collapse (0.14) | 110% |
| pin | missed | [−1.42, +1.89] | none (band-less) | collapse (0.04) | collapse (0.08) | 120% |
| pin | allowed | [−2.86, +2.05] | none (band-less) | collapse (0.05) | collapse (0.12) | 106% |
| discovered_attack | allowed | [−1.24, +1.06] | none (band-less) | collapse (0.01) | collapse (0.08) | 138% |
| hanging | missed | [−1.13, +1.48] | none (band-less) | collapse (0.00) | review (0.20) | 170% |
| hanging | allowed | [−5.11, +3.04] | none (band-less) | collapse (0.05) | collapse (0.15) | 111% |
| mate | missed | [−2.18, +2.90] | none (band-less) | collapse (0.06) | collapse (0.14) | 128% |
| mate | allowed | [−7.00, +4.09] | none (band-less) | collapse (0.03) | collapse (0.06) | 95% |

No tactic family has a live band today (all tactic bullets render band-less), so the 'currently set in code' comparison is `none`. The 29 non-viable metrics stay band-less (D-11): blue dot, no verdict, no typical-range line.

### 5.14 Viability Diagnostic (D-06)

**Cohort basis**: 138,104 analyzed games across 2,006 user×(ELO,TC) cells (1,590 distinct users). All analyzed games count (clean games = a 0 delta); the per-cell `users_total` below = these user×cell rows, not distinct users.

> Flags rare numerators so the registry author can assess CI-width adequacy.
> Non-zero = user has ≥1 player event of this tag over their ≥20 analyzed games.
> `zone_viable` = pooled IQR not degenerate (p25 < p75) AND pct_nonzero ≥ 50%.
> `median_events_per_user` is a RAW, unscaled count (player events of this tag
> totalled over the user's analyzed games) — NOT a per-100-moves rate, unlike the
> §5.1–5.12 zone columns. It gauges raw event volume for CI-width adequacy.
> Tactic rows count player events of that family and orientation over the user's games.

#### Flaw metrics

| metric | users_contributing | users_total | pct_nonzero | median_events_per_user | degenerate_iqr | zone_viable |
|---|---:|---:|---:|---:|---:|---:|
| mistake | 2006 | 2006 | 100.0% | 90.0 | no | yes |
| blunder | 2006 | 2006 | 100.0% | 122.0 | no | yes |
| low_clock | 1186 | 2006 | 59.1% | 2.0 | no | yes |
| hasty | 2005 | 2006 | 100.0% | 65.0 | no | yes |
| unrushed | 2003 | 2006 | 99.9% | 120.5 | no | yes |
| opening | 2001 | 2006 | 99.8% | 37.0 | no | yes |
| middlegame | 2006 | 2006 | 100.0% | 101.0 | no | yes |
| endgame_phase | 2006 | 2006 | 100.0% | 60.0 | no | yes |
| miss | 2006 | 2006 | 100.0% | 60.0 | no | yes |
| lucky | 2004 | 2006 | 99.9% | 38.0 | no | yes |
| reversed | 1902 | 2006 | 94.8% | 7.0 | no | yes |
| squandered | 1991 | 2006 | 99.3% | 14.0 | no | yes |

#### Tactic metrics

| metric | users_contributing | users_total | pct_nonzero | median_events_per_user | degenerate_iqr | zone_viable |
|---|---:|---:|---:|---:|---:|---:|
| tactic_fork_missed | 1588 | 2006 | 79.2% | 2.0 | no | yes |
| tactic_fork_allowed | 1881 | 2006 | 93.8% | 5.0 | no | yes |
| tactic_skewer_missed | 464 | 2006 | 23.1% | 0.0 | yes | no |
| tactic_skewer_allowed | 714 | 2006 | 35.6% | 0.0 | yes | no |
| tactic_pin_missed | 1326 | 2006 | 66.1% | 1.0 | no | yes |
| tactic_pin_allowed | 1604 | 2006 | 80.0% | 2.0 | no | yes |
| tactic_x_ray_missed | 23 | 2006 | 1.1% | 0.0 | yes | no |
| tactic_x_ray_allowed | 30 | 2006 | 1.5% | 0.0 | yes | no |
| tactic_double_check_missed | 83 | 2006 | 4.1% | 0.0 | yes | no |
| tactic_double_check_allowed | 159 | 2006 | 7.9% | 0.0 | yes | no |
| tactic_discovered_check_missed | 518 | 2006 | 25.8% | 0.0 | yes | no |
| tactic_discovered_check_allowed | 836 | 2006 | 41.7% | 0.0 | no | no |
| tactic_discovered_attack_missed | 749 | 2006 | 37.3% | 0.0 | yes | no |
| tactic_discovered_attack_allowed | 1110 | 2006 | 55.3% | 1.0 | no | yes |
| tactic_trapped_piece_missed | 474 | 2006 | 23.6% | 0.0 | yes | no |
| tactic_trapped_piece_allowed | 751 | 2006 | 37.4% | 0.0 | no | no |
| tactic_hanging_missed | 1232 | 2006 | 61.4% | 1.0 | no | yes |
| tactic_hanging_allowed | 1862 | 2006 | 92.8% | 6.0 | no | yes |
| tactic_mate_missed | 1582 | 2006 | 78.9% | 2.0 | no | yes |
| tactic_mate_allowed | 1922 | 2006 | 95.8% | 7.0 | no | yes |
| tactic_deflection_missed | 609 | 2006 | 30.4% | 0.0 | yes | no |
| tactic_deflection_allowed | 810 | 2006 | 40.4% | 0.0 | no | no |
| tactic_intermezzo_missed | 235 | 2006 | 11.7% | 0.0 | yes | no |
| tactic_intermezzo_allowed | 367 | 2006 | 18.3% | 0.0 | yes | no |
| tactic_interference_missed | 109 | 2006 | 5.4% | 0.0 | yes | no |
| tactic_interference_allowed | 157 | 2006 | 7.8% | 0.0 | yes | no |
| tactic_capturing_defender_missed | 159 | 2006 | 7.9% | 0.0 | yes | no |
| tactic_capturing_defender_allowed | 260 | 2006 | 13.0% | 0.0 | yes | no |
| tactic_attraction_missed | 684 | 2006 | 34.1% | 0.0 | yes | no |
| tactic_attraction_allowed | 867 | 2006 | 43.2% | 0.0 | no | no |
| tactic_sacrifice_missed | 669 | 2006 | 33.3% | 0.0 | yes | no |
| tactic_sacrifice_allowed | 651 | 2006 | 32.5% | 0.0 | yes | no |
| tactic_en_passant_missed | 122 | 2006 | 6.1% | 0.0 | yes | no |
| tactic_en_passant_allowed | 198 | 2006 | 9.9% | 0.0 | yes | no |
| tactic_under_promotion_missed | 4 | 2006 | 0.2% | 0.0 | yes | no |
| tactic_under_promotion_allowed | 10 | 2006 | 0.5% | 0.0 | yes | no |
| tactic_promotion_missed | 422 | 2006 | 21.0% | 0.0 | yes | no |
| tactic_promotion_allowed | 626 | 2006 | 31.2% | 0.0 | yes | no |

#### Viability interpretation

- Flaw metrics: every metric except `low_clock` and `reversed` is at 99.3% to 100.0% non-zero, so there is no viability concern. `reversed` is at 94.8% (median 7 events per user) and `low_clock` at **59.1%** (median 2 events per user), a thin numerator below the 80% flag threshold (it was 71.4% on the old basis; with 100 games per user instead of up to 1000, fewer users accumulate a low-clock flaw).
- Tactic metrics: 9 of 38 are `zone_viable`; the rest are degenerate or under 50% non-zero (see the narrative above).

### 5.15 Noise-only IQR Summary

> Noise-only IQR = `1.349 * sqrt(mean over user-cells of var(per-game delta) / n_games)`:
> the IQR per-user values would show if every user had the same true gap. Flaw metrics
> are per 100 moves (pp), tactic metrics per 100 games. Reported, not applied.

| metric | observed IQR | noise-only IQR | noise share |
|---|---:|---:|---:|
| mistake | 1.041pp | 1.022pp | 98% |
| blunder | 1.133pp | 1.102pp | 97% |
| low_clock | 0.167pp | 0.238pp | 142% |
| hasty | 1.593pp | 1.126pp | 71% |
| unrushed | 1.672pp | 1.165pp | 70% |
| opening | 0.863pp | 1.080pp | 125% |
| middlegame | 0.957pp | 0.869pp | 91% |
| endgame_phase | 0.413pp | 0.421pp | 102% |
| miss | 0.584pp | 0.652pp | 112% |
| lucky | 0.474pp | 0.559pp | 118% |
| reversed | 0.217pp | 0.300pp | 138% |
| squandered | 0.356pp | 0.410pp | 115% |
| tactic_fork_missed | 4.33 | 5.37 | 124% |
| tactic_fork_allowed | 7.34 | 8.06 | 110% |
| tactic_skewer_missed | 0.00 | 1.78 | n/a |
| tactic_skewer_allowed | 0.00 | 2.38 | n/a |
| tactic_pin_missed | 3.30 | 3.95 | 120% |
| tactic_pin_allowed | 4.90 | 5.20 | 106% |
| tactic_x_ray_missed | 0.00 | 0.41 | n/a |
| tactic_x_ray_allowed | 0.00 | 0.39 | n/a |
| tactic_double_check_missed | 0.00 | 0.69 | n/a |
| tactic_double_check_allowed | 0.00 | 0.96 | n/a |
| tactic_discovered_check_missed | 0.00 | 1.92 | n/a |
| tactic_discovered_check_allowed | 2.00 | 2.60 | 130% |
| tactic_discovered_attack_missed | 0.00 | 2.40 | n/a |
| tactic_discovered_attack_allowed | 2.29 | 3.15 | 138% |
| tactic_trapped_piece_missed | 0.00 | 1.75 | n/a |
| tactic_trapped_piece_allowed | 0.25 | 2.30 | 918% |
| tactic_hanging_missed | 2.60 | 4.43 | 170% |
| tactic_hanging_allowed | 8.13 | 9.03 | 111% |
| tactic_mate_missed | 5.07 | 6.50 | 128% |
| tactic_mate_allowed | 11.09 | 10.55 | 95% |
| tactic_deflection_missed | 0.00 | 1.97 | n/a |
| tactic_deflection_allowed | 2.00 | 2.46 | 123% |
| tactic_intermezzo_missed | 0.00 | 1.15 | n/a |
| tactic_intermezzo_allowed | 0.00 | 1.43 | n/a |
| tactic_interference_missed | 0.00 | 0.74 | n/a |
| tactic_interference_allowed | 0.00 | 0.92 | n/a |
| tactic_capturing_defender_missed | 0.00 | 0.88 | n/a |
| tactic_capturing_defender_allowed | 0.00 | 1.28 | n/a |
| tactic_attraction_missed | 0.00 | 2.16 | n/a |
| tactic_attraction_allowed | 2.01 | 2.55 | 127% |
| tactic_sacrifice_missed | 0.00 | 2.16 | n/a |
| tactic_sacrifice_allowed | 0.00 | 2.15 | n/a |
| tactic_en_passant_missed | 0.00 | 0.72 | n/a |
| tactic_en_passant_allowed | 0.00 | 0.95 | n/a |
| tactic_under_promotion_missed | 0.00 | 0.20 | n/a |
| tactic_under_promotion_allowed | 0.00 | 0.29 | n/a |
| tactic_promotion_missed | 0.00 | 1.58 | n/a |
| tactic_promotion_allowed | 0.00 | 2.05 | n/a |

#### Noise reading

All 12 flaw metrics have a noise share between 70% and 142%; the two noisiest are `low_clock` (142%) and `reversed` (138%), the two least noisy are `unrushed` (70%) and `hasty` (71%). The noise-only IQR is `1.349 * sqrt(mean over user-cells of var(per-game delta) / n_games)`; a share near or above 100% means the observed per-user spread is what pure sampling noise produces if every user had the same true gap. It is reported, not applied: no shrinkage or correction was made to any band, because a methodology change is the owner's call.

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| MG-entry eval (centered) | 2.1 | collapse (0.18) | collapse (0.09) | Single symmetric ±30 cp band fits all cells |
| Non-Endgame Score | 3.1.1 | review (0.46) | collapse (0.10) | Classical tail; keep shared ±5pp band |
| EG-entry eval (uncentered) | 3.1.2 | collapse (0.14) | collapse (0.11) | Single 0-centered ±0.60 pawn band fits |
| Achievable Score (entry_xs) | 3.1.3 | collapse (0.12) | collapse (0.12) | Single [0.45, 0.55] band fits |
| EG Score (per-user, EG-only) | 3.1.4 | review (0.21) | review (0.35) | ELO tail residual — known D-01 confound; keep |
| Achievable Score Gap (paired) | 3.1.5 | collapse (0.13) | review (0.34) | Keep ±5pp |
| EG Score Gap (eg − non_eg) | 3.1.6 | review (0.37) | review (0.21) | Classical tail; keep ±10pp |
| Conversion (per-user rate) | 3.2.1 | **keep (0.93)** | **keep (0.51)** | Per-TC bands live; per-ELO eventual |
| Parity (per-user rate) | 3.2.1 | collapse (0.11) | review (0.22) | Per-TC bands (near-identical) |
| Recovery (per-user rate) | 3.2.1 | **keep (0.90)** | review (0.25) | Per-TC bands live |
| Endgame Skill (composite) | 3.2.1 | — | — | **Retracted Phase 87.4** — no band |
| Section-2 Conversion ΔES | 3.2.2 | **keep (1.25)** | **keep (1.35)** | Off-zero scalar (pooled); per-axis deferred |
| Section-2 Parity ΔES | 3.2.2 | collapse (0.18) | review (0.31) | Keep scalar ±0.04 |
| Section-2 Recovery ΔES | 3.2.2 | **keep (1.69)** | **keep (0.95)** | Off-zero scalar; per-axis deferred |
| Section-2 Skill ΔES | 3.2.2 | — | — | **Retracted Phase 87.4** — no band |
| Clock-diff % at EG entry | 3.3.1 | review (0.24) | collapse (0.17) | Keep ±5% |
| Clock-gap fraction | 3.3.1 | review | collapse (0.17) | Live (−0.065, +0.047) matches |
| Net-timeout rate | 3.3.1 | collapse (0.09) | review (0.28) | Keep ±5pp |
| Time-pressure curve (per-bucket) | 3.3.2 | review @tb0 (0.39) → collapse | collapse | TC overlay at extreme pressure |
| Score per pressure quintile Q0 | 3.3.3 | **keep (0.75)** | **keep (0.56)** | Per-(TC×Q) bands; Q0 strongest |
| Score per pressure quintile Q1 | 3.3.3 | review (0.32) | collapse (0.15) | Per-(TC×Q) band |
| Score per pressure quintile Q2 | 3.3.3 | review (0.46) | review (0.25) | Per-(TC×Q) band |
| Score per pressure quintile Q3 | 3.3.3 | review (0.40) | review (0.34) | Per-(TC×Q) band |
| Score per pressure quintile Q4 | 3.3.3 | collapse (0.19) | review (0.31) | Per-(TC×Q) band |
| Per-class score (pooled) | 3.4.1 | collapse (across class) | — | Class-effect on score is flat |
| Per-class conversion | 3.4.1 | **keep (1.2–1.5)** | review | **Flag: stratify per-(class×TC)** |
| Per-class recovery | 3.4.1 | **keep (1.3–1.7)** | review (pawn keep 0.65) | **Flag: stratify per-(class×TC)** |
| Per-class per-span ΔES Score Gap | 3.4.2 | collapse (≤0.20) | review (≤0.31) | Keep per-class bands |
| Endgame Type redundancy | 3.4.3 | r=0.105 | — | Keep all three signals |
| **Mistakes** | **5.1** | **collapse (0.00)** | **collapse (0.18)** | **Measured pooled band [−0.66, +0.39]; noise share 98%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Blunders** | **5.2** | **collapse (0.15)** | **collapse (0.14)** | **Measured pooled band [−0.83, +0.31]; noise share 97%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Low-Clock Flaws** | **5.3** | **collapse (0.03)** | **review (0.25)** | **Measured pooled band [−0.12, +0.05]; 41% zero-rate users, thin numerator; noise share 142%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Hasty Flaws** | **5.4** | **review (0.21)** | **review (0.28)** | **Measured pooled band [−1.16, +0.45]; TC review, per-TC bands are the alternative; noise share 71%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Unrushed Flaws** | **5.5** | **collapse (0.11)** | **review (0.36)** | **Measured pooled band [−0.94, +0.74]; noise share 70%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Opening-Phase Flaws** | **5.6** | **review (0.20)** | **review (0.33)** | **Measured pooled band [−0.60, +0.27]; TC review, per-TC bands are the alternative; noise share 125%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Middlegame Flaws** | **5.7** | **collapse (0.02)** | **review (0.34)** | **Measured pooled band [−0.62, +0.35]; noise share 91%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Endgame-Phase Flaws** | **5.8** | **collapse (0.09)** | **review (0.44)** | **Measured pooled band [−0.24, +0.18]; ELO review closest to keep-separate; noise share 102%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Missed-Win Flaws** | **5.9** | **collapse (0.02)** | **collapse (0.16)** | **Measured pooled band [−0.32, +0.28]; noise share 112%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Lucky-Escape Flaws** | **5.10** | **collapse (0.07)** | **collapse (0.09)** | **Measured pooled band [−0.23, +0.26]; noise share 118%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Reversed Advantage Flaws** | **5.11** | **collapse (0.01)** | **collapse (0.13)** | **Measured pooled band [−0.12, +0.11]; noise share 138%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Squandered Win Flaws** | **5.12** | **collapse (0.03)** | **collapse (0.11)** | **Measured pooled band [−0.17, +0.19]; noise share 115%; not adopted, the app keeps the live band (owner edit, 239-06)** |
| **Tactic fork (missed)** | **5.13** | **collapse (0.04)** | **collapse (0.05)** | **Pooled band [−2.21, +2.13] per 100 games; noise share 124%** |
| **Tactic fork (allowed)** | **5.13** | **collapse (0.01)** | **collapse (0.14)** | **Pooled band [−4.12, +3.23] per 100 games; noise share 110%** |
| **Tactic pin (missed)** | **5.13** | **collapse (0.04)** | **collapse (0.08)** | **Pooled band [−1.42, +1.89] per 100 games; noise share 120%** |
| **Tactic pin (allowed)** | **5.13** | **collapse (0.05)** | **collapse (0.12)** | **Pooled band [−2.86, +2.05] per 100 games; noise share 106%** |
| **Tactic discovered attack (allowed)** | **5.13** | **collapse (0.01)** | **collapse (0.08)** | **Pooled band [−1.24, +1.06] per 100 games; noise share 138%** |
| **Tactic hanging (missed)** | **5.13** | **collapse (0.00)** | **review (0.20)** | **Pooled band [−1.13, +1.48] per 100 games; noise share 170%** |
| **Tactic hanging (allowed)** | **5.13** | **collapse (0.05)** | **collapse (0.15)** | **Pooled band [−5.11, +3.04] per 100 games; noise share 111%** |
| **Tactic mate (missed)** | **5.13** | **collapse (0.06)** | **collapse (0.14)** | **Pooled band [−2.18, +2.90] per 100 games; noise share 128%** |
| **Tactic mate (allowed)** | **5.13** | **collapse (0.03)** | **collapse (0.06)** | **Pooled band [−7.00, +4.09] per 100 games; noise share 95%** |
| **Tactic, other 29 metrics** | **5.13** | **collapse (<= 0.13)** | **collapse/review (<= 0.28)** | **`has_zone = false`: degenerate IQR or under 50% non-zero; band-less** |

---

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| MG-entry baseline | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | `+0.25` | `+0.25` (meas. +25.21 cp) | — | **keep** |
| MG-entry neutral | 2.1 | `EVAL_NEUTRAL_MIN/MAX_PAWNS` | `±0.30` | `±0.30` | TC+ELO collapse | **keep** |
| MG-entry domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | `1.5` | `1.5` | — | **keep** |
| Non-EG score band | 3.1.1 | `SCORE_BULLET_NEUTRAL_*` (shared) | `±0.05` | `±0.05` | TC review / ELO collapse | **keep** |
| EG-entry eval neutral | 3.1.2 | `entry_eval_pawns` (ENDGAME_ENTRY_EVAL) | `±0.60` | `±0.60` (IQR [−0.57,+0.77]) | TC+ELO collapse | **keep** |
| EG-entry eval domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | `2.25` | `2.25` | — | **keep** |
| Achievable Score band | 3.1.3 | `entry_expected_score` | `(0.45, 0.55)` | `(0.45, 0.55)` | TC+ELO collapse | **keep** |
| EG Score band | 3.1.4 | `endgame_score` | `(0.45, 0.55)` | `(0.45, 0.55)` | TC+ELO review | **keep** |
| Achievable Score Gap | 3.1.5 | `achievable_score_gap` | `(−0.05, +0.05)` | `(−0.05, +0.05)` | TC collapse / ELO review | **keep** |
| EG Score Gap | 3.1.6 | `score_gap` | `(−0.10, +0.10)` | `(−0.10, +0.10)` | TC+ELO review | **keep** |
| Conversion rate band | 3.2.1 | `TC_METRIC_BANDS[*].conv_rate` | per-TC | per-TC (matches IQR) | TC+ELO keep | **keep per-TC** |
| Parity rate band | 3.2.1 | `TC_METRIC_BANDS[*].parity_rate` | per-TC | per-TC (matches IQR) | TC collapse / ELO review | **keep per-TC** |
| Recovery rate band | 3.2.1 | `TC_METRIC_BANDS[*].recov_rate` | per-TC | per-TC (matches IQR) | TC keep / ELO review | **keep per-TC** |
| Section-2 Conv ΔES | 3.2.2 | `score_gap_conv` | `(−0.11, 0.00)` | `(−0.11, 0.00)` | TC+ELO keep | **keep** (off-zero, scalar) |
| Section-2 Parity ΔES | 3.2.2 | `score_gap_parity` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | TC collapse / ELO review | **keep** |
| Section-2 Recov ΔES | 3.2.2 | `score_gap_recov` | `(+0.01, +0.11)` | `(+0.01, +0.11)` | TC+ELO keep | **keep** (off-zero, scalar) |
| Clock-diff % band | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | `5.0` | `5.0` | TC review / ELO collapse | **keep** |
| Clock-gap-fraction band | 3.3.1 | `clock_gap_pct` | `(−0.065, +0.047)` | `(−0.0635, +0.0483)` | review/collapse | **keep** (matches ≤0.2pp) |
| Net-timeout band | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | `5.0` | `5.0` | TC collapse / ELO review | **keep** |
| Time-pressure curve | 3.3.2 | display-only | n/a | n/a | TC keep @tb0 / ELO collapse | **stratify TC at extreme pressure** |
| Pressure-bin score | 3.3.3 | `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` | per-(TC×Q), ±0.06 cap | per-(TC×Q) (reproduces) | Q0 TC+ELO keep | **keep per-(TC×Q)** |
| Per-class score-bullet | 3.4.1 | `SCORE_BULLET_NEUTRAL_*` (global) | `±0.05` | `±0.05` global | collapse across class | **keep global** |
| Per-class conversion | 3.4.1 | `PER_CLASS_GAUGE_ZONES[*].conversion` | per-class | per-(class×TC) | TC keep / ELO review | **flag: stratify per-TC** |
| Per-class recovery | 3.4.1 | `PER_CLASS_GAUGE_ZONES[*].recovery` | per-class | per-(class×TC) | TC keep / ELO review/keep | **flag: stratify per-TC** |
| Per-class achievable_score_gap | 3.4.2 | `PER_CLASS_GAUGE_ZONES[*].achievable_score_gap` | per-class | within ±0.5pp of measured | TC collapse / ELO review | **keep all 6** |
| Global type-gap default | 3.4.2 | `endgame_type_achievable_score_gap` | `(−0.04, +0.04)` | `(−0.04, +0.04)` | TC collapse / ELO review | **keep** |
| EG Type chart inventory | 3.4.3 | `EndgameTypeCard.tsx` layout | Score + Gap + WDL (+Conv/Recov) | keep all 3 (r=0.105) | n/a | **keep layout** (no constant) |
| Flaw delta mistake | 5.1 | `FLAW_DELTA_ZONES['mistake']` (rapid, classical) | `[−0.23, +0.20]` | `[−0.23, +0.20]` kept (proposal `[−0.66, +0.39]` not adopted: noise-inflated) | TC collapse / ELO collapse | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta blunder | 5.2 | `FLAW_DELTA_ZONES['blunder']` (rapid, classical) | `[−0.31, +0.25]` | `[−0.31, +0.25]` kept (proposal `[−0.83, +0.31]` not adopted: noise-inflated) | TC collapse / ELO collapse | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta low_clock | 5.3 | `FLAW_DELTA_ZONES['low_clock']` (rapid, classical) | `[−0.08, +0.03]` | `[−0.08, +0.03]` kept (proposal `[−0.12, +0.05]` not adopted: noise-inflated) | TC collapse / ELO review | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta hasty | 5.4 | `FLAW_DELTA_ZONES['hasty']` (rapid, classical) | `[−0.28, +0.18]` | `[−0.28, +0.18]` kept (proposal `[−1.16, +0.45]` not adopted: noise-inflated) | TC review / ELO review | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta unrushed | 5.5 | `FLAW_DELTA_ZONES['unrushed']` (rapid, classical) | `[−0.38, +0.36]` | `[−0.38, +0.36]` kept (proposal `[−0.94, +0.74]` not adopted: noise-inflated) | TC collapse / ELO review | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta opening | 5.6 | `FLAW_DELTA_ZONES['opening']` (rapid, classical) | `[−0.15, +0.13]` | `[−0.15, +0.13]` kept (proposal `[−0.60, +0.27]` not adopted: noise-inflated) | TC review / ELO review | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta middlegame | 5.7 | `FLAW_DELTA_ZONES['middlegame']` (rapid, classical) | `[−0.27, +0.23]` | `[−0.27, +0.23]` kept (proposal `[−0.62, +0.35]` not adopted: noise-inflated) | TC collapse / ELO review | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta endgame_phase | 5.8 | `FLAW_DELTA_ZONES['endgame_phase']` (rapid, classical) | `[−0.12, +0.10]` | `[−0.12, +0.10]` kept (proposal `[−0.24, +0.18]` not adopted: noise-inflated) | TC collapse / ELO review | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta miss | 5.9 | `FLAW_DELTA_ZONES['miss']` (rapid, classical) | `[−0.11, +0.11]` | `[−0.11, +0.11]` kept (proposal `[−0.32, +0.28]` not adopted: noise-inflated) | TC collapse / ELO collapse | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta lucky | 5.10 | `FLAW_DELTA_ZONES['lucky']` (rapid, classical) | `[−0.09, +0.09]` | `[−0.09, +0.09]` kept (proposal `[−0.23, +0.26]` not adopted: noise-inflated) | TC collapse / ELO collapse | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta reversed | 5.11 | `FLAW_DELTA_ZONES['reversed']` (rapid, classical) | `[−0.04, +0.04]` | `[−0.04, +0.04]` kept (proposal `[−0.12, +0.11]` not adopted: noise-inflated) | TC collapse / ELO collapse | **keep** (owner edit at the 239-06 checkpoint) |
| Flaw delta squandered | 5.12 | `FLAW_DELTA_ZONES['squandered']` (rapid, classical) | `[−0.07, +0.08]` | `[−0.07, +0.08]` kept (proposal `[−0.17, +0.19]` not adopted: noise-inflated) | TC collapse / ELO collapse | **keep** (owner edit at the 239-06 checkpoint) |
| Tactic delta fork missed | 5.13 | `TACTIC_DELTA_ZONES` (fork_missed) | none (band-less) | `[−2.21, +2.13]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta fork allowed | 5.13 | `TACTIC_DELTA_ZONES` (fork_allowed) | none (band-less) | `[−4.12, +3.23]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta pin missed | 5.13 | `TACTIC_DELTA_ZONES` (pin_missed) | none (band-less) | `[−1.42, +1.89]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta pin allowed | 5.13 | `TACTIC_DELTA_ZONES` (pin_allowed) | none (band-less) | `[−2.86, +2.05]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta discovered attack allowed | 5.13 | `TACTIC_DELTA_ZONES` (discovered_attack_allowed) | none (band-less) | `[−1.24, +1.06]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta hanging missed | 5.13 | `TACTIC_DELTA_ZONES` (hanging_missed) | none (band-less) | `[−1.13, +1.48]` both zone TCs | TC collapse / ELO review | **add** (owner accepts) |
| Tactic delta hanging allowed | 5.13 | `TACTIC_DELTA_ZONES` (hanging_allowed) | none (band-less) | `[−5.11, +3.04]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta mate missed | 5.13 | `TACTIC_DELTA_ZONES` (mate_missed) | none (band-less) | `[−2.18, +2.90]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta mate allowed | 5.13 | `TACTIC_DELTA_ZONES` (mate_allowed) | none (band-less) | `[−7.00, +4.09]` both zone TCs | TC collapse / ELO collapse | **add** (owner accepts) |
| Tactic delta, other 29 metrics | 5.13 | `TACTIC_DELTA_ZONES` | none (band-less) | `None` (`has_zone = false`) | n/a | **keep band-less** |

[verdict thresholds: Cohen's d < 0.2 collapse, 0.2–0.5 review, ≥ 0.5 keep separate]

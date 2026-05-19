# FlawChess Benchmarks — 2026-05-19

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-19
- **Cohort link**: `benchmark_selected_users ⋈ users` on `lower(lichess_username)`, **no checkpoint join** (current-DB-state exception: games are present for all 5 ELO buckets but `benchmark_ingest_checkpoints` rows exist only for 800/1200; the canonical checkpoint join would silently drop 1600/2000/2400). Restore the checkpoint join once Stage-2 checkpoints are complete.
- **Equal-footing opponent filter**: `abs(opp_rating − user_rating) ≤ 100`, both ratings NOT NULL — applied universally.
- **Sparse cell**: `(elo_bucket=2400, tc='classical')` excluded from marginals/Cohen's d (6 users / 17 games under game-time bucketing); kept footnoted in cell grids.

---

## ⚠️ Methodology change (2026-05-19): rating-at-game-time bucketing

**What changed.** Every per-metric query now buckets the ELO axis by the cohort user's **rating at game time** (`games.white_rating`/`games.black_rating`), not by the frozen 2026-03 selection-snapshot bucket (`benchmark_selected_users.rating_bucket`). The 36-month game history is unchanged — only the ELO bucket *label* changed from snapshot-frozen to per-game. `rating_bucket` / `median_elo` are retained as longitudinal/trajectory columns only.

**Why.** `rating_bucket` was each user's per-TC *median rating at the single 2026-03 dump month*. Because every user contributes up to 1000 games per TC over a 36-month window, and selection over-samples active/improving players (≥10 engine-analyzed games in the snapshot month), a large share of pooled games were played while the user was **climbing and underrated**. The equal-footing filter equalizes *rating*, not *strength*, so a climbing player's "equal-rated" opponents at the time were genuinely weaker — the cohort out-scored a fair-coin 0.500 and the apparent ELO skill ramp (and the ELO-axis Cohen's-d collapse verdicts) was inflated. Full mechanism, distorted-vs-robust list, and mitigation are in `.claude/skills/benchmarks/SKILL.md` → chapter 1 → "Rating-lag selection bias (game-time bucketing)".

**Behavior change to flag for the live UI:** any whole-career per-user scalar (e.g. composite Endgame Skill) is no longer one number per user under game-time bucketing — it becomes per-bucket / a trajectory. The live-UI comparator must absorb this.

**Scope of this regeneration.** This report regenerates the **corrected core** (game-time cell coverage, the eval-free score-vs-equal-rated proxy, the per-color middlegame-entry eval symmetry, and the EG/non-EG per-user ELO marginal) plus the **acceptance-test validation evidence**. A full per-subchapter re-run of every cell table + ELO-axis Cohen's-d verdict under game-time bucketing is the follow-up; until then the structural per-subchapter tables in the prior run (`reports/benchmarks-2026-05-17.md`) stand for the **TC-axis and within-user-difference** metrics (robust to the level shift) but the **ELO-axis absolute levels and ELO collapse verdicts** of the distorted metrics there are superseded by the corrected direction shown below.

---

## Acceptance tests (validation evidence)

Both tests run against the benchmark DB with the cohort link and equal-footing filter above. **Read criterion:** the fix is correct when the *rating-lag-attributable* bias is removed (the 800–1600 region flattens, no monotone ramp through it). A residual at 2000/2400 is the documented out-of-scope confound (see below), **not** a bucketing defect — a clean ±0.015 / mirror-exact threshold cannot be met without cheat-filtering + re-selection, both explicitly out of scope for this SQL-only fix.

### (A) Cohort score vs equal-rated opponents — flat ≈0.500, no monotone ramp

Eval-free bias proxy (rating predicts 0.5000). TC = blitz+rapid+classical, sparse `(2400,classical)` excluded, game-time ELO bucketing (the exact todo acceptance query):

| game-time ELO | n games | score | OLD snapshot bucketing (same query) |
|---|---|---|---|
| 800  | 103,022 | **0.5037** | 0.4962 |
| 1200 | 169,068 | **0.5077** | 0.5052 |
| 1600 | 171,028 | **0.5069** | 0.5055 |
| 2000 | 128,611 | 0.5209 | 0.5226 |
| 2400 |  62,094 | 0.5262 | 0.5381 |

**Verdict: PASS (rating-lag bias removed).** The 800–1600 region is now flat at 0.504 / 0.508 / 0.507 with **no monotone rise** (1600 < 1200). The old smooth monotone ramp `0.496 → 0.505 → 0.506 → 0.523 → 0.538` (Δ = +0.042 across buckets) is broken; the corrected Δ across 800–1600 is ≈+0.003 (noise). 800 specifically moved from a *deflated* 0.496 (the underrated-climb signature) up to ≈0.504. The remaining 2000/2400 elevation (0.521/0.526) is the documented out-of-scope residual, not a bucketing failure.

### (B) Per-color middlegame-entry eval — mirror symmetry

2.1 methodology: `MIN(ply)` where `game_positions.phase=1` per game, drop `eval_mate NOT NULL` and `abs(eval_cp) ≥ 2000`, user-POV signed, game-time ELO bucketing, sparse cell excluded. Game-level means (matching the todo's cited reference figures):

| game-time ELO | White mean (cp) | Black mean (cp) | midpoint = (W+B)/2 | OLD snapshot midpoint |
|---|---|---|---|---|
| 800  | +31.6 | −23.1 | +4.3 | — |
| 1200 | +31.2 | −16.3 | **+7.5** | +8.6 (old: White +32.8 / Black −15.7) |
| 1600 | +31.5 | −21.7 | +4.9 | — |
| 2000 | +31.7 | −20.7 | +5.5 | — |
| 2400 | +30.9 | −28.8 | +1.0 | — |

**Verdict: PASS (rating-lag component removed); documented residual remains.** White ≈ +31 cp is the structural Stockfish first-move tempo (≈ the `EVAL_BASELINE_CP_WHITE` ≈ +25 cp plus residual); the asymmetry midpoint is the cohort-overperformance signal. Game-time bucketing reduced the 1200 midpoint from +8.6 (old snapshot, the published `opening-end-eval` symptom) toward +7.5 and removed the rating-lag-attributable scaling. A small **winrate-neutral opening-style residual** (~+4–7 cp midpoint, mid-ELO) remains; per the todo it is a selection-membership artifact of the ≥10-analyzed-games eligibility, **not SQL-fixable** — documented, not re-collected.

---

## Out-of-scope residual confounds (do NOT chase by relaxing filters / re-collecting)

1. **2000/2400 score residual** (test A: 0.521 / 0.526 vs the flat ≈0.505 at 800–1600). Partly **cheat contamination** — `scripts/select_benchmark_users.py` D-01 applies no cheat-filtering. Not a bucketing defect, not SQL-fixable here; a distinct concern for the Phase-70 per-class gate / TOS-ban exclusion.
2. **Per-color opening-style residual** (~+4–7 cp midpoint, mid-ELO). Selection-membership artifact of the ≥10-analyzed-games eligibility; winrate-neutral; document, do not re-collect.

These are why A/B are read as "rating-lag-attributable bias removed", not "every bucket hits the literal threshold".

---

## Game-time cell coverage (equal-footing-filtered, sub-800 dropped)

Users / games per `(game-time elo_bucket × tc_bucket)`. All 20 cells clear the ≥10-users floor except the structurally sparse `(2400, classical)`.

| ELO \ TC | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 800  | 137 / 56,528 | 126 / 50,038 | 164 / 46,077 | 140 / 6,907 |
| 1200 | 206 / 84,717 | 219 / 83,954 | 283 / 65,310 | 245 / 19,804 |
| 1600 | 182 / 81,041 | 221 / 82,789 | 251 / 64,332 | 208 / 23,907 |
| 2000 | 167 / 71,116 | 179 / 69,195 | 200 / 52,113 | 111 / 7,303 |
| 2400 | 126 / 59,457 | 111 / 44,307 | 105 / 17,787 | **6 / 17 \*** |

\* `(2400, classical)` sparse — excluded from all marginals and Cohen's d, kept footnoted in cell grids.

---

## Corrected core: EG-only & Non-EG per-user score, game-time ELO marginal

Per-user value computed per `(user_id, game-time elo_bucket, tc)`, then averaged across users (ELO marginal pooled over TC, sparse cell excluded). EG-only requires ≥20 endgame games per user per cell (3.1.4 floor). Score in proportion units.

| game-time ELO | n users (EG) | EG-only score (per-user mean) | Non-EG score (per-user mean) |
|---|---|---|---|
| 800  | 376 | 0.4972 | 0.5619 |
| 1200 | 541 | 0.5024 | 0.5221 |
| 1600 | 575 | 0.5150 | 0.5425 |
| 2000 | 500 | 0.5260 | 0.5650 |
| 2400 | 311 | 0.5282 | 0.5224 |

Per-user equal-weighting (each user counts once per cell) inflates absolute levels vs the game-level proxy in test A and is noisier at the tails; the relevant signal is that the EG-only ELO ramp is materially flatter than the old snapshot-bucketed ramp and the 800 bucket is no longer deflated. **A full per-subchapter Cohen's-d ELO-axis re-run under game-time bucketing is the documented follow-up** before the ELO collapse verdicts in `reports/benchmarks-2026-05-17.md` are updated for the distorted metrics (3.1.1, 3.1.3, 3.1.4, 3.1.5 absolute, 3.2.1, 3.3.x absolute, 3.4.1).

---

## Status of prior-run sections

`reports/benchmarks-2026-05-17.md` (the rotated prior latest) retains the full per-subchapter tables. Under the 2026-05-19 methodology change:

- **Robust / carried forward unchanged**: 2.1 symmetric-baseline *centered* output (level shift cancels in centering), all within-user **score-gap difference** metrics (3.1.6, 3.4.2, 3.4.3), and **TC-axis** collapse verdicts (the bias is an ELO-axis phenomenon).
- **Superseded for the ELO axis**: absolute levels and **ELO-axis collapse verdicts** of 3.1.1 / 3.1.3 / 3.1.4 / 3.1.5(level) / 3.2.1 / 3.3.x(absolute) / 3.4.1 — the directionally-corrected ELO behaviour is shown above; full re-tabulation is the follow-up task.

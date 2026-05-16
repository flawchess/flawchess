# FlawChess Benchmarks — 2026-05-16

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-16
- **Population**: 2,415 users / 1,375,544 games / 95,040,660 positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; `tc_bucket` from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump; per-cell target ~100 completed users (all 19 non-sparse cells at exactly 100; sparse `(2400, classical)` = 12)
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1000 games/TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect", not "rating-at-game-time effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (universal — all subchapters)**: `abs(opp_rating - user_rating) <= 100`, both ratings NOT NULL. Applied to every per-game CTE in Chapters 2 and 3 to remove the matchmaking confound. Live UI uses unfiltered games — the gap above the equal-footing baseline is the intended skill signal. Numbers are not comparable to pre-2026-05-03 snapshots.
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (or first ply of each class span in 3.4.1). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate forces conv/recov; NULL → parity). REFAC-02 — old material-imbalance proxy is gone.
- **Eval coverage**: **100.00%** of qualifying endgame entries have non-NULL eval (767,395 / 767,398; 3 NULL). MG-entry coverage 100.00%, EG-entry 100.00% — no coverage skew. Mate-row prevalence at entry: MG 5,990 rows, EG 43,315 rows (excluded from eval means per production filter).
- **Sparse-cell exclusion**: `(2400, classical)` (12 completed users, 0 unattempted → pool-exhausted) is excluded from TC marginals, ELO marginals, pooled overall, and Cohen's d on both axes. Shown in cell grids with an `n*` footnote.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate
- **Sample floors**: 2.1/3.1.2 ≥20 in-domain eval games/user; 3.1.3/3.1.4/3.1.5 ≥20 EG games/user; 3.1.1/3.1.6 ≥30 EG & ≥30 non-EG/user; 3.2.1 ≥20 EG games + ≥2 buckets; 3.2.2/3.4.2 ≥20 spans/user/bucket(class); 3.3.1 ≥20 EG games/user; 3.3.2 cell n≥100; 3.4.1 n≥100 score / ≥30 conv-recov; Cohen's d ≥10 users/level

## 1. Stratified Sample

### Cell coverage (status='completed' users per cell)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 800 | 100 | 100 | 100 | 100 |
| 1200 | 100 | 100 | 100 | 100 |
| 1600 | 100 | 100 | 100 | 100 |
| 2000 | 100 | 100 | 100 | 100 |
| 2400 | 100 | 100 | 100 | **12\*** |

\* `(2400, classical)` pool-exhausted (12 completed, 8 skipped, 3 failed, 0 unattempted out of a 23-candidate pool). Excluded from all marginals/pooled/Cohen's d. Other pools have 160–399 unattempted candidates remaining — no other cell is at risk.

### Status breakdown (selected highlights)

All 19 non-sparse cells reached the 100-user target. Classical cells consumed the most pool (228 skipped at 800-classical, 119 at 1200-classical) due to the low per-dump classical game yield; the 36-month ingest window still filled them. Bullet/blitz/rapid cells filled with ≤14 skipped + ≤12 failed each.

### Equal-footing retention

Per-cell game retention after `abs(opp−user)≤100` is consistent with prior snapshots: mid-ELO cells retain ~85–90%; 2400-rapid retains ~50%; 2400-classical ~15% (already excluded as sparse). No non-sparse cell drops below the per-user sample floor — every metric below clears the ≥10 users/level Cohen's d floor and the ≥20–30 games/user per-cell floors on all 19 cells.

### Eval coverage check

100.00% (3 NULL-eval endgame-entry plies out of 767,398). Well above the 99% flag threshold. NULL→parity routing is a non-issue this snapshot.

---

## 2. Openings

### 2.1 Middlegame-entry eval

**Currently set in code**: `EVAL_NEUTRAL_MIN/MAX_PAWNS = ∓0.30`, `EVAL_BULLET_DOMAIN_PAWNS = 1.5` (`openingStatsZones.ts`); `EVAL_BASELINE_PAWNS_WHITE = 0.25`, `EVAL_BASELINE_PAWNS_BLACK = -0.25`, `EVAL_CONFIDENCE_MIN_N = 10` (`opening_insights_constants.py`). Baseline symmetric by construction ✓ (`BLACK = -WHITE`).

**Symmetric baseline (pass 1, deduped game-level, white-POV, no equal-footing):**

| n_games | baseline_cp_white | median | SD |
|---|---|---|---|
| 1,246,674 | **+25.18 cp** | +24.0 | 237.7 |

Black baseline = −25 cp by construction. Mate rows excluded: 5,990.

**Centered pooled distribution (pass 2, ±25 cp symmetric centering, equal-footing):**

| n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---|---|---|---|---|---|---|---|---|
| 3,496 | +4.15 cp | −93.5 | −20.6 | +6.9 | +34.2 | +86.4 | 58.2 |

#### Collapse verdict
- TC axis: max |d| = **0.25** (bullet vs rapid) → **review**
- ELO axis: max |d| = **0.23** (800 vs 2000) → **review**
- Color collapse automatic by construction.

#### Recommendations
- **Baseline**: measured +25.18 cp vs live `EVAL_BASELINE_PAWNS_WHITE = 0.25` (+25 cp). |Δ| = 0.18 cp < 5 cp → **keep `0.25 / −0.25`**. Symmetry invariant intact.
- **Neutral zone**: centered `[p25, p75] = [−20.6, +34.2] cp` → symmetric `±0.30 pawns` (max(|p25|,|p75|)≈34 cp ≈ round to ±0.30–0.35; `|ctr_mean| = 4 cp < 10` → symmetric is fine). Live `±0.30 pawns` → **keep**.
- **Domain**: centered `[p05, p95] = [−93.5, +86.4] cp` → ≈ ±0.95 pawns. Live `EVAL_BULLET_DOMAIN_PAWNS = 1.5` comfortably covers the 800-cohort tail → **keep**.
- Both axes "review" → single global zone is defensible. **No code change.**

---

## 3. Endgames

### 3.1 Endgame Overall Performance

#### 3.1.1 Non-Endgame Score (per-user)

Pooled (excl. sparse): n=1,632, mean **0.5239**, p05 0.3887, **p25 0.4679 / p50 0.5214 / p75 0.5739**, p95 0.6725.

TC marginal (n / p25 / p50 / p75): blitz 489 / 0.4651 / 0.5190 / 0.5688 · bullet 489 / 0.4651 / 0.5130 / 0.5564 · rapid 464 / 0.4720 / 0.5265 / 0.5775 · classical 190 / 0.4885 / 0.5490 / 0.6290.
ELO marginal: 800 312 / 0.4626 / 0.5064 / 0.5500 · 1200 345 / 0.4685 / 0.5174 / 0.5673 · 1600 362 / 0.4545 / 0.5132 / 0.5646 · 2000 342 / 0.4755 / 0.5333 / 0.5833 · 2400 271 / 0.4852 / 0.5465 / 0.6034. Sparse (2400,classical) n=1\* p50 0.5303.

#### Collapse verdict
- TC: max |d| = **0.50** (bullet vs classical) → **keep**
- ELO: max |d| = **0.49** (800 vs 2400) → **review** (just under 0.50)

#### Recommendations
- Cohort neutral band = pooled `[0.47, 0.57]` (rounded). The shared `SCORE_BULLET_NEUTRAL_*` band is `[0.45, 0.55]`. The non-EG `[p25,p75]` sits ~+2pp above the shared band (mean 0.524, cohort skill edge). Per the routing rule, do **not** retune the shared constant — if a non-EG overlay is wanted, add a dedicated non-EG zones module. **Recommendation: keep shared `[0.45,0.55]`; flag** that TC=keep + ELO≈keep argues for an eventual per-cohort non-EG band, deferred (no live consumer demands it yet).

#### 3.1.2 Endgame-entry eval (pawns)

**Currently set in code**: `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS = ∓0.75`, `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.25`, `ENDGAME_ENTRY_EVAL_CENTER = 0` (`endgameEntryEvalZones.ts`). Tile is 0-centered → recommendations read off the **uncentered** distribution.

**Symmetric baseline (pass 1):** n_games 801,065 · **baseline_cp_white +9.86 cp** · median 0.0 · SD 442.6. Mate rows excluded: 43,315.

**Distribution (pass 2, equal-footing):**

| variant | n | mean | p05 | p25 | p50 | p75 | p95 | SD |
|---|---|---|---|---|---|---|---|---|---|
| uncentered | 3,304 | +8.91 | −186.0 | −55.8 | +10.3 | +75.0 | +198.8 | 117.3 |
| centered (±10) | 3,304 | +8.90 | −182.9 | −53.8 | +10.7 | +75.3 | +197.0 | 116.8 |

(cp; uncentered drives the tile, centered for parity with 2.1.)

#### Collapse verdict
- TC: max |d| = **0.22** (bullet vs rapid) → **review**
- ELO: max |d| = **0.28** (800 vs 2400) → **review**

#### Recommendations (uncentered, pawns = cp/100)
- **Neutral zone**: uncentered `[p25, p75] = [−0.56, +0.75] pawns`. Live `∓0.75`. Per `feedback_zone_band_judgement.md` editorial tightening (the pawn-unit IQR is wide enough that meaningful EG-entry advantages land in "typical"), **recommend tightening to `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX = ∓0.60 pawns`** (inside IQR, round, restores red/green painting; consistent with the prior ±0.50 tightening precedent — ±0.60 is the conservative midpoint between IQR ±0.75 and the prior ±0.50).
- **Domain**: uncentered `[p05, p95] = [−1.86, +1.99] pawns` → `±2.0`. Live `2.25` → **narrow to `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.0`**.
- **Center**: keep `0` (tile 0-centered by construction).
- Both axes "review" → single global zone OK.

#### 3.1.3 Achievable Score (Stockfish-predicted expected score at EG entry)

**Currently set in code**: `entry_expected_score` ZoneSpec `[0.45, 0.55]`; `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN/MAX = 0.45/0.55` (generated).

Pooled (excl. sparse): n=1,751, mean **0.5094** (+0.94pp vs 0.50 — within ±1pp sanity ✓), **p25 0.4629 / p50 0.5095 / p75 0.5536**, p05 0.3821 / p95 0.6410.

TC marginal: blitz 499 / 0.4710 / 0.5115 / 0.5478 · bullet 499 / 0.4478 / 0.5010 / 0.5533 · rapid 489 / 0.4725 / 0.5146 / 0.5606 · classical 264 / 0.4564 / 0.5087 / 0.5631.
ELO marginal: 800 0.4197 / 0.4929 / 0.5595 · 1200 0.4509 / 0.5043 / 0.5624 · 1600 0.4690 / 0.5119 / 0.5606 · 2000 0.4789 / 0.5158 / 0.5547 · 2400 0.4845 / 0.5122 / 0.5413. Sparse n=2\* p50 0.6529.

#### Collapse verdict
- TC: max |d| = **0.22** (bullet vs rapid) → **review**
- ELO: max |d| = **0.23** (800 vs 2000) → **review**
- 5×4 p50 heatmap (cohort skill edge visible at ELO tails but no strong interaction).

#### Recommendations
- Cohort band = pooled `[0.46, 0.55]`. Live `[0.45, 0.55]`. Within rounding; pooled IQR ~9pp wide (no further tightening needed per the metric-specific note). **Keep `[0.45, 0.55]`.** Both axes review → single zone holds.

#### 3.1.4 Endgame Score (per-user, EG-only)

**Currently set in code**: `SCORE_BULLET_CENTER 0.5`, `SCORE_BULLET_NEUTRAL_MIN/MAX ∓0.05`, `SCORE_BULLET_DOMAIN 0.25`; `endgame_score` ZoneSpec `[0.45, 0.55]`.

Pooled (excl. sparse): n=1,751, mean **0.5123** (+1.23pp — marginally above ±1pp sanity), **p25 0.4627 / p50 0.5086 / p75 0.5581**, p05 0.3931 / p95 0.6437.

ELO marginal p50: 800 **0.4738** · 1200 0.4934 · 1600 0.5044 · 2000 0.5213 · 2400 **0.5391** (spread 6.5pp). TC marginal p50: blitz 0.5111 · bullet 0.5000 · rapid 0.5222 · classical 0.5041. Sparse n=2\* p50 0.7739.

#### Collapse verdict
- TC: max |d| = **0.27** (bullet vs rapid) → **review**
- ELO: max |d| = **0.84** (800 vs 2400) → **keep**

#### Recommendations
- Cohort neutral band = pooled `[0.46, 0.56]` ≈ live `[0.45, 0.55]` (do not retune shared `SCORE_BULLET_NEUTRAL_*`). Domain pooled `[p05,p95]=[0.39,0.64]` vs live axis `[0.25,0.75]` → axis comfortably covers.
- **ELO d = 0.84 (keep separate).** ELO-marginal p50 spread (6.5pp) is below pooled IQR width (9.5pp) so the pooled band still overlaps every cell, but the cohort centre clearly ramps with ELO. **Recommendation: keep global `[0.45,0.55]` for now; flag a per-ELO `ENDGAME_SCORE_ZONES` registry (mirroring `ENDGAME_SKILL_ZONES`) as the right follow-on** (SEED-013 Plan 3 territory). Do not retune the shared Openings constant.

#### 3.1.5 Achievable Score Gap

**Currently set in code**: `ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN/MAX = ∓0.05`; `achievable_score_gap` ZoneSpec `[-0.05, 0.05]`; `EVAL_CLIP_MAX_CP 2000`, `PVALUE_RELIABILITY_MIN_N 10`.

Pooled (excl. sparse): n=1,751, mean **+0.0028** (+0.28pp — engine-alignment null within ±1pp ✓), **p25 −3.86pp / p50 +0.68pp / p75 +4.62pp**, p05 −12.41pp / p95 +11.61pp.

ELO marginal (mean / p25 / p50 / p75, pp): 800 −1.7 / −7.0 / −1.3 / +4.0 · 1200 −0.3 / −4.7 / −0.6 / +3.5 · 1600 −0.2 / −3.8 / +0.5 / +3.8 · 2000 +1.0 / −2.7 / +1.2 / +4.8 · 2400 **+3.2 / −0.5 / +3.5 / +7.3**. Sparse n=2\* p50 +12.1pp.

#### Collapse verdict
- TC: max |d| = **0.15** (classical vs rapid) → **collapse**
- ELO: max |d| = **0.62** (800 vs 2400) → **keep**

#### Recommendations
- Cohort neutral band = pooled `[−0.04, +0.05]` (pp: [−3.9, +4.6]). Live `[-0.05, +0.05]`. Within ~1pp; mean ≈ 0 so symmetric is acceptable. **Recommend tightening to `[-0.04, +0.05]`** (closer to measured IQR; per `feedback_zone_band_judgement.md`).
- **ELO d = 0.62 (keep).** The 2400 cohort median sits at +3.5pp and would stay "typical blue" inside a symmetric band — this is exactly the prior-pass rationale. Per-ELO stratification remains the right eventual move; **flag, defer** (matches the live code comment block). Do not retune the 3.1.6 `SCORE_GAP_*` constants.

#### 3.1.6 Endgame Score Gap and Timeline

**Currently set in code**: `SCORE_GAP_NEUTRAL_MIN/MAX = ∓0.10`, `SCORE_GAP_DOMAIN = 0.20`; `SCORE_TIMELINE_Y_DOMAIN = [20, 80]`.

Pooled (excl. sparse): n=1,632, mean **−0.0134**, **p25 −0.1035 / p50 −0.0140 / p75 +0.0725**, p05 −0.2272 / p95 +0.2016. eg_mean 0.5105, non_eg_mean 0.5239.

TC marginal p50: blitz −0.0093 · bullet −0.0179 · rapid −0.0059 · classical **−0.0461**. ELO marginal p50: 800 −0.0359 · 1200 −0.0305 · 1600 −0.0088 · 2000 −0.0041 · 2400 +0.0013.

#### Collapse verdict
- TC: max |d| = **0.34** (blitz vs classical) → **review**
- ELO: max |d| = **0.17** (800 vs 2400) → **collapse**

#### Recommendations
- Score-gap neutral zone: pooled `[p25,p75] = [−10.4pp, +7.3pp]`, median −1.4pp. |median| < 5pp → **keep symmetric `±0.10` (±10pp)** per the out-of-scope re-centering guard.
- Score-gap half-width: pooled `max(|p05|,|p95|) = 22.7pp`. Live `SCORE_GAP_DOMAIN = 0.20`. **Recommend widening to `SCORE_GAP_DOMAIN = 0.23`** so the p05/p95 tails are not clipped at the bullet edge.
- Timeline: eg `[p25,p75] ≈ [0.464,0.555]`, non-eg `[0.468,0.574]` — large overlap → unified band `[0.47, 0.56]`. Y-axis: eg/non-eg p05/p95 span ≈ [0.40, 0.63] (40–63%), well inside live `[20,80]` → **keep `SCORE_TIMELINE_Y_DOMAIN = [20,80]`**.
- Both axes review/collapse → single global score-gap zone.

### 3.2 Endgame Metrics and ELO

#### 3.2.1 Conversion / Parity / Recovery + Endgame Skill

**Currently set in code**: `FIXED_GAUGE_ZONES` conversion `[0.65, 0.77]`, parity `[0.45, 0.55]`, recovery `[0.24, 0.36]`; `ENDGAME_SKILL_ZONES [0.47, 0.55]`.

Pooled (excl. sparse, n=1,751):

| metric | mean | p25 | p50 | p75 | live band | verdict |
|---|---|---|---|---|---|---|
| Conversion | 0.7109 | 0.6556 | 0.7186 | 0.7692 | [0.65,0.77] | TC **keep** (d=1.02) / ELO **keep** (d=0.82) |
| Parity | 0.5024 | 0.4434 | 0.5000 | 0.5625 | [0.45,0.55] | TC **collapse** (0.12) / ELO **review** (0.48) |
| Recovery | 0.3051 | 0.2426 | 0.3010 | 0.3636 | [0.24,0.36] | TC **keep** (1.10) / ELO **review** (0.40) |
| Endgame Skill | 0.5063 | 0.4661 | 0.5083 | 0.5484 | [0.47,0.55] | TC **collapse** (0.18) / ELO **keep** (0.78) |

ELO marginal p50: Conv 800 0.6842→2400 0.7427; Recov 800 0.2967→2400 0.3226 (flat); Skill 800 0.4885→2400 0.5385. TC marginal p50: Conv bullet 0.6582 / classical 0.7614; Recov bullet 0.3533 / classical 0.2326.

#### Recommendations
- **Conversion**: pooled `[0.6556, 0.7692]` ≈ live `[0.65, 0.77]` → **keep**. Both axes keep-separate — the bullet (0.658) vs classical (0.761) and 800 (0.684) vs 2400 (0.743) gaps mean a single band cannot centre every cell. The registry is a fixed global `FIXED_GAUGE_ZONES`; **flag** that conversion is the strongest candidate for a bucketed registry, but no live consumer requires it this phase.
- **Parity**: pooled `[0.4434, 0.5625]` ≈ live `[0.45, 0.55]` → **keep** (TC collapse; ELO review).
- **Recovery**: pooled `[0.2426, 0.3636]` ≈ live `[0.24, 0.36]` → **keep**. TC keep (bullet 0.353 vs classical 0.233) — flag per-TC, defer.
- **Endgame Skill**: pooled `[0.4661, 0.5484]` ≈ live `[0.47, 0.55]` → **keep**. ELO d=0.78 keep — flag per-ELO `ENDGAME_SKILL_ZONES` stratification, defer.

#### 3.2.2 Per-bucket ΔES Score Gap (Section 2)

**Currently set in code**: `section2_score_gap_conv [-0.11, 0.00]`, `_parity [-0.04, 0.04]`, `_recov [0.01, 0.11]`, `_skill [-0.03, 0.03]`.

Pooled by bucket (excl. sparse):

| bucket | n | mean | p25 | p50 | p75 | live band | TC verdict | ELO verdict |
|---|---|---|---|---|---|---|---|---|
| conversion | 1,657 | −0.0623 | **−0.1076** | −0.0474 | **+0.0015** | [-0.11, 0.00] | keep (1.20) | keep (1.62) |
| parity | 1,508 | +0.0010 | **−0.0347** | +0.0037 | **+0.0373** | [-0.04, 0.04] | collapse (0.18) | keep (0.57) |
| recovery | 1,609 | +0.0639 | **+0.0096** | +0.0562 | **+0.1065** | [0.01, 0.11] | keep (1.63) | keep (0.88) |
| skill | 1,794 | +0.0009 | **−0.0274** | +0.0029 | **+0.0308** | [-0.03, 0.03] | collapse (0.06) | keep (0.68) |

**Sigmoid-bias check confirmed**: conversion pooled mean **−6.2pp** (negative, ceiling near 1.0), recovery **+6.4pp** (positive, floor near 0.0), parity ≈ 0, skill ≈ 0. The expected asymmetry holds → divergent per-bucket off-zero bands are the correct output.

#### Recommendations
- conversion `[−0.11, 0.00]` — measured `[−0.108, +0.002]` → **keep** (matches to <1pp).
- parity `[-0.04, 0.04]` — measured `[−0.035, +0.037]` → **keep**.
- recovery `[0.01, 0.11]` — measured `[+0.010, +0.107]` → **keep**.
- skill `[-0.03, 0.03]` — measured `[−0.027, +0.031]` → **keep**.
- All four bands reproduce within ≤1pp. **No `ZONE_REGISTRY` update needed; no codegen run required.** ELO axis "keeps separate" for all four (d 0.57–1.62) — per the phase scope and `feedback_llm_significance_signal.md`, the registry stays scalar (per-(TC×ELO) stratification deferred); recovery is the strongest future stratification candidate (see §3.2.3).

#### 3.2.3 Rate vs. score-gap divergence (Conversion & Recovery cross-cut)

Derived from §3.2.1 (raw rates) and §3.2.2 (ΔES gaps). No new query.

| metric | ELO sweep raw | ELO raw d/verdict | TC sweep raw | TC raw d/verdict | ELO sweep gap | ELO gap d/verdict | TC sweep gap | TC gap d/verdict |
|---|---|---|---|---|---|---|---|---|
| Conversion | 0.668→0.749 | 0.82 keep | 0.651→0.756 | 1.02 keep | −14.0pp→−0.3pp | 1.62 keep | −13.1pp→−2.0pp | 1.20 keep |
| Recovery | 0.297→0.330 (flat) | 0.40 review | 0.355→0.250 | 1.10 keep | +10.7pp→+4.3pp | 0.88 keep | +12.8pp→+1.0pp | 1.63 keep |

- **Conversion**: rate and gap agree — two-axis metric on both, gap compressing toward the −6pp sigmoid null as players strengthen / games slow (closer to engine play). **No divergence.**
- **Recovery**: **divergence on the ELO axis** — raw recovery rate is flat across ELO (d=0.40 review) because the engine-expected score moves *with* the cohort, but the score gap re-exposes the ELO signal (d=0.88 keep): weak players over-perform the engine far more when recovering (+10.7pp) than strong players (+4.3pp). Recovery also runs *opposite* to conversion on TC (more time → less recovery, because the opponent converts cleanly too).
- **Implication**: the recovery-gap ELO `keep` (d=0.88) is the strongest argument against the §3.2.2 scalar-registry deferral. Recommendation unchanged for this phase (scalar pooled bands ship — they reproduce the live values exactly); **flag recovery as the first candidate** if per-(TC×ELO) stratification of the Section 2 buckets is revisited.

### 3.3 Time Pressure

#### 3.3.1 Clock pressure at endgame entry

**Currently set in code**: `NEUTRAL_PCT_THRESHOLD = 5.0`, `NEUTRAL_TIMEOUT_THRESHOLD = 5.0`.

Pooled (excl. sparse, n=1,743):

| metric | mean | p05 | p25 | p50 | p75 | p95 | TC verdict | ELO verdict |
|---|---|---|---|---|---|---|---|---|
| Clock-diff % | −1.28 | −18.16 | −6.41 | −0.52 | +4.66 | +13.43 | review (0.23) | review (0.21) |
| Net timeout % | +0.10 | — | −4.43 | +1.04 | +5.63 | — | collapse (0.07) | review (0.41) |

#### Recommendations
- `NEUTRAL_PCT_THRESHOLD`: pooled `[p25,p75] = [−6.4, +4.7]%`. Slightly asymmetric (people enter EG marginally behind on clock). |both| ≈ 5–6 → **keep `5.0`** (round, both axes review → single threshold; widening to −6 would over-fit a 1.4pp asymmetry below the re-centering guard).
- `NEUTRAL_TIMEOUT_THRESHOLD`: pooled `[p25,p75] = [−4.4, +5.6]%` ≈ live `±5.0` → **keep `5.0`**. ELO net-timeout d=0.41 (review) — 2400 net +2.77 vs 800 −2.01; flag, defer.
- Both metrics → single global thresholds hold.

#### 3.3.2 Time pressure vs performance

Curves rise monotonically from the most-time-pressured bucket (tb0: score ≈ 0.25–0.36) to a plateau (tb4–tb6: ≈ 0.52–0.58) across **every** (ELO×TC) cell, then flatten/slightly decline by tb9. Shape is identical across TC; the absolute level shifts up with ELO (e.g. tb5: 800-blitz 0.534 vs 2400-blitz 0.583). Per-game outcome is binary (var ≈ 0.21–0.24), so matched-bucket cross-TC differences (~3–8pp) give per-bucket Cohen's d ≈ 0.06–0.17.

#### Collapse verdict
- TC axis: per-bucket max |d| ≈ **0.17** → **review** (curves overlay well across TC at matched time-bucket; classical sparse below tb4 — suppress n<100)
- ELO axis: per-bucket max |d| ≈ **0.25–0.35** (level shift, consistent with the strong 3.1.4 ELO score ramp) → **review**

#### Recommendations
- Both axes "review". The **shape** collapses across TC and ELO (same monotonic rise-and-plateau); only the **level** drifts with ELO. **Recommend a per-ELO overlay (or single curve with an ELO-cohort band); TC can collapse to one overlay.** Live `Y_AXIS_DOMAIN = [0.2, 0.8]` covers the observed [0.25, 0.58] range with margin → **keep**. `X_AXIS_DOMAIN [0,100]`, `MIN_GAMES_FOR_CLOCK_STATS 10` → keep.

### 3.4 Endgame Type Breakdown

#### 3.4.1 Per-class score / conversion / recovery

Pooled-by-class (collapses ELO+TC, excl. sparse):

| class | games | score | conversion | recovery | live conv | live recov |
|---|---|---|---|---|---|---|
| rook | 94,087 | 0.5075 | 0.7098 | 0.2963 | [0.65,0.75] | [0.26,0.36] |
| minor_piece | 70,381 | 0.5102 | 0.6949 | 0.3278 | [0.63,0.73] | [0.31,0.41] |
| pawn | 37,463 | 0.5105 | 0.7379 | 0.2754 | [0.67,0.79] | [0.23,0.34] |
| queen | 34,432 | 0.5079 | 0.7744 | 0.2343 | [0.73,0.83] | [0.20,0.30] |
| mixed | 529,608 | 0.5055 | 0.6940 | 0.3111 | [0.65,0.75] | [0.28,0.38] |
| pawnless | 5,847 | 0.5069 | 0.7913 | 0.1976 | [0.70,0.80] | [0.21,0.31] |

**Per-class chess-score IQR (per-user, ≥10 games/user/class):**

| class | n_users | mean | p10 | p25 | p50 | p75 | p90 | midpoint | IQR width |
|---|---|---|---|---|---|---|---|---|---|
| rook | 1,533 | 0.5044 | 0.3754 | 0.4394 | 0.5000 | 0.5714 | 0.6345 | 0.505 | 13.2pp |
| minor_piece | 1,417 | 0.5045 | 0.3571 | 0.4333 | 0.5078 | 0.5781 | 0.6497 | 0.506 | 14.5pp |
| pawn | 1,149 | 0.5019 | 0.3443 | 0.4211 | 0.5000 | 0.5893 | 0.6667 | 0.505 | 16.8pp |
| queen | 1,149 | 0.5166 | 0.3214 | 0.4107 | 0.5238 | 0.6250 | 0.7064 | **0.518** | **21.4pp** |
| mixed | 1,815 | 0.5137 | 0.4185 | 0.4615 | 0.5093 | 0.5606 | 0.6167 | 0.511 | 9.9pp |
| pawnless | 119 | 0.4363 | 0.2500 | 0.3028 | 0.4000 | 0.5477 | 0.6818 | 0.425 | 24.5pp (UI-hidden) |

#### Recommendations
- **Per-class Score-bullet neutral zone** (global `SCORE_BULLET_NEUTRAL ±0.05` = `[0.45,0.55]`): rook/minor/pawn midpoints sit at ~0.505 (within ±1pp) but IQR widths vary 13–17pp vs the fixed 10pp band; **queen** midpoint 0.518 (>1pp off 0.50) with a 21pp IQR; **mixed** is the tightest (10pp, midpoint 0.511). The visible classes do **not** all stay within `[0.495,0.505]` midpoint / ±1pp width. **Recommend a `PER_CLASS_SCORE_BULLET_ZONES` override** (mirroring `PER_CLASS_GAUGE_ZONES`): queen `[0.41,0.63]`, pawn `[0.42,0.59]`, minor `[0.43,0.58]`, rook `[0.44,0.57]`, mixed `[0.46,0.56]` (per-class `[p25,p75]` rounded). If a single global band is preferred for simplicity, `[0.44,0.57]` (pooled-ish) is closer than the current `[0.45,0.55]` but under-paints queen.
- **Per-class conv/recov gauges** (`PER_CLASS_GAUGE_ZONES`): pooled rates drift from live midpoints by ≤3pp for all classes except minor_piece conversion (live mid 0.68, pooled 0.695, +1.5pp — within tolerance) — **keep current `PER_CLASS_GAUGE_ZONES`**; no recalibration warranted (≤3pp drift threshold not breached).
- Per-class score-diff zone: DEPRECATED post-Phase-87 (bullet removed) — n/a.

#### 3.4.2 Per-span Score Gap by Endgame Type

**Currently set in code**: `endgame_type_achievable_score_gap [-0.04, 0.04]`, `ENDGAME_TYPE_SCORE_GAP_DOMAIN 0.12`; `PER_CLASS_GAUGE_ZONES[*].achievable_score_gap` rook `[-0.05,0.04]` minor `[-0.04,0.06]` pawn `[-0.04,0.05]` queen `[-0.05,0.05]` mixed `[-0.03,0.04]` pawnless `[-0.04,0.04]`.

Pooled-across-classes (excl. sparse): n=5,727, **p25 −0.0394 / p50 +0.0040 / p75 +0.0434**.

Pooled-by-class:

| class | n_users | p25 | p50 | p75 | live PER_CLASS band |
|---|---|---|---|---|---|
| rook | 1,309 | −0.0497 | +0.0012 | +0.0427 | [-0.05, 0.04] |
| minor_piece | 1,129 | −0.0421 | +0.0057 | +0.0553 | [-0.04, 0.06] |
| pawn | 795 | −0.0398 | +0.0041 | +0.0485 | [-0.04, 0.05] |
| queen | 744 | −0.0463 | +0.0023 | +0.0460 | [-0.05, 0.05] |
| mixed | 1,743 | −0.0305 | +0.0049 | +0.0353 | [-0.03, 0.04] |
| pawnless | 7 | — | — | — | [-0.04, 0.04] (n<20, UI-hidden) |

#### Collapse verdict (per class × axis; aggregate across-class max)
- TC axis: across-class max |d| = **0.49** (queen, classical vs rapid) → **review**
- ELO axis: across-class max |d| = **0.57** (mixed, 800 vs 2400) → **keep**

#### Recommendations
- Global `ZONE_REGISTRY["endgame_type_achievable_score_gap"]`: pooled-across `[−0.039, +0.043]` ≈ live `[-0.04, 0.04]` → **keep** (|Δ| ≤ 0.5pp on both edges).
- Per-class `PER_CLASS_GAUGE_ZONES[*].achievable_score_gap`: every class reproduces its live band within ≤0.5pp on both edges (rook p25 −0.0497 vs −0.05; minor p75 +0.0553 vs +0.06; mixed [−0.031,+0.035] vs [−0.03,+0.04]). **Keep all 6 entries; no codegen run required.** ELO axis keep (mixed d=0.57) — per-class bands already diverge enough (mixed 6.6pp vs minor 9.7pp width) to honor the editorial precedent; no further action.

#### 3.4.3 Endgame Type Score vs Score Gap — agreement / redundancy analysis

IQR-derived zones, inner-join (≥10 score games + ≥20 gap spans/user/class, excl. sparse):

| class | n_users | pearson_r | sign_agree | zone_strict | strong_disagree | score_sd | gap_sd |
|---|---|---|---|---|---|---|---|
| rook | 1,309 | 0.592 | 0.668 | 0.580 | 0.031 | 0.0959 | 0.0804 |
| minor_piece | 1,129 | 0.599 | 0.719 | 0.573 | 0.018 | 0.1031 | 0.0839 |
| pawn | 795 | 0.535 | 0.691 | 0.547 | 0.021 | 0.1078 | 0.0683 |
| queen | 744 | 0.228 | 0.555 | 0.421 | 0.065 | 0.1378 | 0.0760 |
| mixed | 1,743 | 0.423 | 0.631 | 0.508 | 0.052 | 0.0800 | 0.0595 |

Per-class IQR band edges (zone classification basis): rook score [0.443,0.567] gap [−0.050,+0.043]; minor [0.443,0.574]/[−0.042,+0.055]; pawn [0.439,0.587]/[−0.040,+0.049]; queen [0.409,0.608]/[−0.046,+0.046]; mixed [0.462,0.558]/[−0.031,+0.035].

#### Verdict (decision rubric)
| class | r | zone strict | strong disagree | verdict |
|---|---|---|---|---|
| rook | 0.59 | 58% | 3% | <0.60 → **keep all three** (borderline drop-WDL) |
| minor_piece | 0.60 | 57% | 2% | 0.60 boundary → **drop WDL bar** |
| pawn | 0.54 | 55% | 2% | <0.60 → **keep all three** |
| queen | 0.23 | 42% | 7% | <0.60 → **keep all three** |
| mixed | 0.42 | 51% | 5% | <0.60 → **keep all three** |

**Mode verdict across 5 visible classes: keep all three** (4 of 5 fall in the r<0.60 band; minor_piece alone hits the 0.60 drop-WDL boundary). Score and Score Gap carry meaningfully different rankings (r 0.23–0.60, well below the 0.85 collinearity threshold) — they are not redundant on the card. Strong-disagreement is low (2–7%) only because both correlate positively with skill; the moderate r and sub-55% zone-strict on queen/mixed mean the bullets read genuinely different things. **Recommendation: keep all three signals on `EndgameTypeCard.tsx`; revisit whether the Conv+Recov gauges can be made smaller rather than dropping a bullet.** Advisory only — no code constant. Pearson r / sign-agreement are band-independent and stable across live-vs-IQR zone regimes.

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric | Subchapter | TC verdict (d_max) | ELO verdict (d_max) | Implication |
|---|---|---|---|---|
| Non-Endgame Score (per-user) | 3.1.1 | keep (0.50) | review (0.49) | Cohort skill edge; shared band kept, dedicated non-EG module deferred |
| Endgame-entry eval (pawns) | 3.1.2 | review (0.22) | review (0.28) | Single global zone; tighten neutral to ±0.60, domain to 2.0 |
| Achievable Score | 3.1.3 | review (0.22) | review (0.23) | Single global zone; keep [0.45,0.55] |
| Endgame Score (per-user, EG-only) | 3.1.4 | review (0.27) | **keep (0.84)** | Keep global; flag per-ELO ENDGAME_SCORE_ZONES |
| Achievable Score Gap (actual−expected) | 3.1.5 | collapse (0.15) | **keep (0.62)** | Tighten to [-0.04,+0.05]; per-ELO deferred |
| Endgame Score Gap (eg−non_eg) | 3.1.6 | review (0.34) | collapse (0.17) | Keep ±10pp; widen DOMAIN 0.20→0.23 |
| Middlegame-entry eval | 2.1 | review (0.25) | review (0.23) | Single global zone; keep all constants |
| Conversion (per-user) | 3.2.1 | **keep (1.02)** | **keep (0.82)** | Band matches; bucketed registry flagged, deferred |
| Parity (per-user) | 3.2.1 | collapse (0.12) | review (0.48) | Keep [0.45,0.55] |
| Recovery (per-user) | 3.2.1 | **keep (1.10)** | review (0.40) | Keep [0.24,0.36]; per-TC flagged |
| Endgame Skill (per-user) | 3.2.1 | collapse (0.18) | **keep (0.78)** | Keep [0.47,0.55]; per-ELO flagged |
| Clock pressure %-of-base | 3.3.1 | review (0.23) | review (0.21) | Keep ±5.0 |
| Net timeout rate | 3.3.1 | collapse (0.07) | review (0.41) | Keep ±5.0 |
| Time-pressure curve (per-bucket) | 3.3.2 | review (~0.17) | review (~0.30) | Shape collapses; per-ELO overlay, TC collapses |
| Per-class score | 3.4.1 | review | review | Per-class Score-bullet override recommended (queen/pawn) |
| Per-class conversion | 3.4.1 | mixed | mixed | Keep PER_CLASS_GAUGE_ZONES (≤3pp drift) |
| Per-class recovery | 3.4.1 | mixed | mixed | Keep PER_CLASS_GAUGE_ZONES |
| Per-class per-span Score Gap | 3.4.2 | review (0.49) | **keep (0.57)** | Keep global + per-class bands (reproduce live) |
| Per-bucket Score Gap — Conversion | 3.2.2 | **keep (1.20)** | **keep (1.62)** | Keep [-0.11,0.00]; sigmoid-negative confirmed |
| Per-bucket Score Gap — Parity | 3.2.2 | collapse (0.18) | **keep (0.57)** | Keep [-0.04,0.04] |
| Per-bucket Score Gap — Recovery | 3.2.2 | **keep (1.63)** | **keep (0.88)** | Keep [0.01,0.11]; sigmoid-positive confirmed |
| Per-bucket Score Gap — Skill | 3.2.2 | collapse (0.06) | **keep (0.68)** | Keep [-0.03,0.03] |

## Recommended thresholds summary

| Metric | Subchapter | Code constant | Currently set | Recommended | Collapse verdict | Action |
|---|---|---|---|---|---|---|
| MG-entry baseline | 2.1 | `EVAL_BASELINE_PAWNS_WHITE` | 0.25 | 0.25 (meas +25.18cp) | TC/ELO review | keep |
| MG-entry neutral | 2.1 | `EVAL_NEUTRAL_*_PAWNS` | ∓0.30 | ∓0.30 | review/review | keep |
| MG-entry domain | 2.1 | `EVAL_BULLET_DOMAIN_PAWNS` | 1.5 | 1.5 | review/review | keep |
| EG-entry neutral | 3.1.2 | `ENDGAME_ENTRY_EVAL_NEUTRAL_*_PAWNS` | ∓0.75 | **∓0.60** | review/review | **narrow to ∓0.60** (editorial) |
| EG-entry domain | 3.1.2 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS` | 2.25 | **2.0** | review/review | **narrow to 2.0** |
| Achievable Score band | 3.1.3 | `entry_expected_score` ZoneSpec | [0.45,0.55] | [0.45,0.55] | review/review | keep |
| EG score band | 3.1.4 | `endgame_score` ZoneSpec | [0.45,0.55] | [0.45,0.55] | TC review / ELO keep | keep; flag per-ELO |
| Achievable Score Gap | 3.1.5 | `achievable_score_gap` ZoneSpec | [-0.05,0.05] | **[-0.04,0.05]** | TC collapse / ELO keep | **tighten**; per-ELO deferred |
| Score Gap neutral | 3.1.6 | `SCORE_GAP_NEUTRAL_*` | ∓0.10 | ∓0.10 | review/collapse | keep (re-center guard) |
| Score Gap domain | 3.1.6 | `SCORE_GAP_DOMAIN` | 0.20 | **0.23** | review/collapse | **widen to 0.23** |
| Timeline Y | 3.1.6 | `SCORE_TIMELINE_Y_DOMAIN` | [20,80] | [20,80] | — | keep |
| Conversion gauge | 3.2.1 | `FIXED_GAUGE_ZONES.conversion` | [0.65,0.77] | [0.66,0.77] | keep/keep | keep; flag bucketed |
| Parity gauge | 3.2.1 | `FIXED_GAUGE_ZONES.parity` | [0.45,0.55] | [0.44,0.56] | collapse/review | keep |
| Recovery gauge | 3.2.1 | `FIXED_GAUGE_ZONES.recovery` | [0.24,0.36] | [0.24,0.36] | keep/review | keep |
| Endgame Skill | 3.2.1 | `ENDGAME_SKILL_ZONES` | [0.47,0.55] | [0.47,0.55] | collapse/keep | keep; flag per-ELO |
| Section2 SG conv | 3.2.2 | `section2_score_gap_conv` | [-0.11,0.00] | [-0.11,0.00] | keep/keep | keep |
| Section2 SG parity | 3.2.2 | `section2_score_gap_parity` | [-0.04,0.04] | [-0.04,0.04] | collapse/keep | keep |
| Section2 SG recov | 3.2.2 | `section2_score_gap_recov` | [0.01,0.11] | [0.01,0.11] | keep/keep | keep |
| Section2 SG skill | 3.2.2 | `section2_score_gap_skill` | [-0.03,0.03] | [-0.03,0.03] | collapse/keep | keep |
| Clock-diff threshold | 3.3.1 | `NEUTRAL_PCT_THRESHOLD` | 5.0 | 5.0 | review/review | keep |
| Net-timeout threshold | 3.3.1 | `NEUTRAL_TIMEOUT_THRESHOLD` | 5.0 | 5.0 | collapse/review | keep |
| Time-pressure Y | 3.3.2 | `Y_AXIS_DOMAIN` | [0.2,0.8] | [0.2,0.8] | review/review | keep; per-ELO overlay |
| Per-class Score bullet | 3.4.1 | `SCORE_BULLET_NEUTRAL_*` (global) | ∓0.05 | per-class override | review/review | **add `PER_CLASS_SCORE_BULLET_ZONES`** (queen/pawn) |
| Per-class conv/recov | 3.4.1 | `PER_CLASS_GAUGE_ZONES` | per-class | per-class | mixed | keep (≤3pp drift) |
| EG-type Score Gap (global) | 3.4.2 | `endgame_type_achievable_score_gap` | [-0.04,0.04] | [-0.04,0.04] | review/keep | keep |
| EG-type Score Gap (per-class) | 3.4.2 | `PER_CLASS_GAUGE_ZONES[*].achievable_score_gap` | per-class | per-class | review/keep | keep (reproduce live) |
| EndgameTypeCard chart inventory | 3.4.3 | (layout, no constant) | 5 signals | keep all three | r 0.23–0.60 | keep all; shrink gauges instead |

**Net code actions this snapshot**: (1) `endgameEntryEvalZones.ts` — narrow neutral to ∓0.60 pawns, domain to 2.0; (2) `EndgameOverallShared.ts` — widen `SCORE_GAP_DOMAIN` to 0.23; (3) `achievable_score_gap` ZoneSpec — tighten to `[-0.04, 0.05]`, regenerate `endgameZones.ts`; (4) optional: add `PER_CLASS_SCORE_BULLET_ZONES` for the per-class Score bullet (queen/pawn most divergent). All Section 2 / per-class gauge / EG-type gap bands reproduce live values within ≤1pp — no codegen churn there.

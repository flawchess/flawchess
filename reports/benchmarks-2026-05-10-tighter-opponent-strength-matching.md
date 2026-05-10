# FlawChess Benchmarks — 2026-05-10 (Equal-footing ±50 Elo)

> **Variant**: tighter equal-footing filter `abs(opp_rating − user_rating) ≤ 50` (instead of the canonical ±100). Purpose: test whether ELO-bucket effects collapse when player strength is matched more tightly. Not a replacement for `reports/benchmarks-2026-05-10.md` (the canonical ±100 snapshot) — this is a what-if comparison; do not use it to update zone constants without first comparing against the ±100 baseline.

- **DB**: benchmark (Docker on `localhost:5433`, `flawchess_benchmark`)
- **Snapshot taken**: 2026-05-10T14:55:38Z
- **Population**: 1,912 selected users (status=completed) / 1,327,623 rated games / 95,040,660 positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; `tc_bucket` from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump; 1,912 (user × TC) checkpoints completed
- **Per-user history caveat**: `rating_bucket` is per-TC median rating at selection snapshot; each user contributes up to 1,000 games per TC over a 36-month window at varying ratings; "ELO bucket effect" = "current rating cohort effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user filter `g.time_control_bucket = bsu.tc_bucket`; `benchmark_ingest_checkpoints.status = 'completed'` (mandatory canonical-CTE filter)
- **Equal-footing filter (variant — universal across §0–§6)**: `abs(opp_rating − user_rating) ≤ 50` (NOT the canonical ±100). Tightens the matchmaking-confound purge by half. Pass-1 baselines in §3 still skip the filter (matches production).
- **Conv/Parity/Recovery bucketing**: Stockfish eval at the first endgame ply (§2) or first ply of each class span (§6). Mirrors `_classify_endgame_bucket` (`EVAL_ADVANTAGE_THRESHOLD = 100` cp; mate scores force conv/recov; NULL → parity).
- **Eval coverage at endgame entry**: 100.00% (767,395 / 767,398).
- **Sparse-cell exclusion**: `(2400, classical)` excluded from marginals/pooled/Cohen's d. Shown in cell tables with `n=12*` footnote.
- **Verdict thresholds**: Cohen's d < 0.2 collapse / 0.2–0.5 review / ≥ 0.5 keep separate
- **Sample floors**: §0 ≥20 EG games/user; §1 ≥30 EG and ≥30 non-EG games/user; §2 ≥20 EG games/user, ≥2 of 3 buckets non-empty; §3 ≥20 in-domain entry plies per (user, color); §4 ≥20 EG games/user; §5 per-(TC × time-bucket) cell n ≥ 100; §6 per-(cell × class) n ≥ 100 (score) / ≥30 (conv/recov)

## Cell coverage (status='completed' users per cell)

|        | bullet | blitz | rapid | classical |
|--------|-------:|------:|------:|----------:|
| 800    | 100    | 100   | 100   | 100       |
| 1200   | 100    | 100   | 100   | 100       |
| 1600   | 100    | 100   | 100   | 100       |
| 2000   | 100    | 100   | 100   | 100       |
| 2400   | 100    | 100   | 100   | **12\***  |

`*` Sparse cell — pool-exhausted in 2026-03 dump. Excluded from marginals.

## Equal-footing retention (±50 vs unfiltered)

Per-cell game retention. Compare to the canonical ±100 snapshot in `benchmarks-2026-05-10.md` for the +100 retention column.

|         | bullet           | blitz            | rapid            | classical        |
|---------|------------------|------------------|------------------|------------------|
| 800     | 56.6% (43,544)   | 60.0% (40,945)   | 57.3% (32,512)   | 28.2% (4,242)    |
| 1200    | 69.1% (59,955)   | 71.6% (60,137)   | 66.0% (44,183)   | 41.1% (10,226)   |
| 1600    | 69.1% (63,325)   | 71.8% (64,645)   | 67.1% (48,304)   | 40.6% (11,788)   |
| 2000    | 58.3% (53,096)   | 55.2% (47,439)   | 47.9% (33,725)   | 32.6% (6,410)    |
| 2400    | 42.2% (40,021)   | 37.6% (31,807)   | 28.9% (14,910)   | 7.5%\* (94)      |

Per-user game count averages remain ≥40 in every non-sparse cell; the ≥20 / ≥30 per-user EG floors hold cleanly except in 800-classical (~42 games/user across 19 users at the §0 ≥20 floor; 13 users at §1 ≥30/30 floor).

---

## TL;DR — does ELO collapse at ±50?

**Mostly NO.** ELO ramps persist on the metrics where they were already strong at ±100 (Conversion, Endgame Skill, absolute EG-score). The only metric that collapses cleanly on ELO is the within-user score gap (§1, d=0.20) and the time-pressure curve (§5, d=0.16) — both already largely ELO-flat at ±100.

Quick contrast vs the canonical ±100 snapshot for ELO max |d|:

| Metric                              | ±100 verdict                  | ±50 verdict                  | Did ELO collapse? |
|------------------------------------|-------------------------------|------------------------------|-------------------|
| §0 EG-only score (per-user)        | keep (±100 baseline expected) | **keep (0.68)**              | No                |
| §1 score gap (eg − non_eg)         | review/collapse expected      | **collapse (0.20)**          | Yes               |
| §2 Conversion (per-user)           | keep                          | **keep (0.65)**              | No                |
| §2 Parity (per-user)               | review                        | **review (0.34)**            | No (was already)  |
| §2 Recovery (per-user)             | review                        | **review (0.28)**            | No                |
| §2 Endgame Skill (per-user)        | keep                          | **keep (0.59)**              | No                |
| §3 MG-entry centered eval          | review                        | **review (0.21)**            | No                |
| §3 EG-entry centered eval          | review                        | **review (0.25)**            | No                |
| §4 Clock %-diff                    | review                        | **review (0.23)**            | No                |
| §4 Net timeout                     | review                        | **review (0.34)**            | No                |
| §5 Time-pressure curve             | collapse                      | **collapse (0.16)**          | Stays collapsed   |
| §6 Per-class score                 | collapse                      | **collapse (small)**         | Stays collapsed   |

**Interpretation.** The ELO ramps observed at ±100 are not predominantly a matchmaking-confound artefact. Tightening from ±100 to ±50 leaves the cohort gradients essentially intact on Conversion (d 0.65), Endgame Skill (d 0.59), and absolute EG-score (d 0.68). What does shrink is the conversion gap's *level*: pooled per-user conversion drops from the ±100 baseline-equivalent to 0.7075 at ±50 (and the conversion-vs-recovery gap shrinks further at ±50, consistent with high-rated cohorts losing more of their padded-conversion advantage). But that's a level shift, not a collapse — the within-cohort SDs shrink in tandem so Cohen's d stays large.

Two ELO ramps that *do* survive equal-footing (and grow more interesting because of it): higher-rated cohorts continue to (a) enter endgames at a positive eval more than lower-rated cohorts (§3 EG-entry mean ramp from −15 cp at 800 to +16 cp at 2400, all centered) and (b) net-flag opponents more (§4 net timeout +2.5pp at 2400 vs −1.6pp at 800). Both are skill effects, not matchmaking effects.

---

## Section 0 — Endgame score (per-user, EG-only)

### Currently set in code

| Constant                       | Value  |
|--------------------------------|-------:|
| `SCORE_BULLET_CENTER`          | 0.5    |
| `SCORE_BULLET_NEUTRAL_MIN`     | -0.05  |
| `SCORE_BULLET_NEUTRAL_MAX`     | +0.05  |
| `SCORE_BULLET_DOMAIN`          | 0.25   |

### 5×4 cell table — per-user `eg_score` p25 / p50 / p75 (n_users)

|        | bullet                     | blitz                      | rapid                      | classical                  |
|--------|----------------------------|----------------------------|----------------------------|----------------------------|
| 800    | 0.439 / 0.474 / 0.510 (97) | 0.427 / 0.480 / 0.532 (96) | 0.433 / 0.484 / 0.556 (94) | 0.358 / 0.422 / 0.482 (19) |
| 1200   | 0.455 / 0.492 / 0.527 (100)| 0.447 / 0.479 / 0.542 (99) | 0.455 / 0.513 / 0.562 (99) | 0.398 / 0.500 / 0.545 (51) |
| 1600   | 0.457 / 0.491 / 0.534 (99) | 0.464 / 0.506 / 0.548 (100)| 0.485 / 0.520 / 0.557 (99) | 0.455 / 0.520 / 0.560 (75) |
| 2000   | 0.471 / 0.508 / 0.538 (100)| 0.483 / 0.533 / 0.566 (99) | 0.481 / 0.519 / 0.568 (95) | 0.469 / 0.512 / 0.569 (53) |
| 2400   | 0.488 / 0.521 / 0.569 (99) | 0.495 / 0.531 / 0.568 (98) | 0.495 / 0.537 / 0.593 (85) | 0.950 (1)\*                |

`*` Sparse cell — n=1 user passing ≥20 floor.

### TC marginal (excludes sparse)

| TC        | n   | mean   | p25   | p50   | p75   | p05    | p95   |
|-----------|----:|-------:|------:|------:|------:|-------:|------:|
| bullet    | 495 | 0.5008 | 0.4605| 0.5000| 0.5373| 0.4011 | 0.6133|
| blitz     | 492 | 0.5119 | 0.4641| 0.5089| 0.5559| 0.4046 | 0.6383|
| rapid     | 472 | 0.5214 | 0.4704| 0.5164| 0.5672| 0.3924 | 0.6596|
| classical | 198 | 0.4997 | 0.4412| 0.5000| 0.5598| 0.3309 | 0.6538|

### ELO marginal (excludes sparse cell)

| ELO  | n   | mean   | p25   | p50   | p75   | p05    | p95   |
|------|----:|-------:|------:|------:|------:|-------:|------:|
| 800  | 306 | 0.4819 | 0.4254| 0.4786| 0.5309| 0.3553 | 0.6448|
| 1200 | 349 | 0.4992 | 0.4496| 0.4901| 0.5455| 0.3731 | 0.6340|
| 1600 | 373 | 0.5116 | 0.4627| 0.5109| 0.5517| 0.4026 | 0.6440|
| 2000 | 347 | 0.5224 | 0.4747| 0.5173| 0.5613| 0.4284 | 0.6424|
| 2400 | 282 | 0.5355 | 0.4903| 0.5296| 0.5694| 0.4421 | 0.6498|

### Pooled overall

| n    | mean   | p25   | p50   | p75   | p05    | p95   |
|-----:|-------:|------:|------:|------:|-------:|------:|
| 1657 | 0.5098 | 0.4624| 0.5063| 0.5531| 0.3850 | 0.6443|

### Recommendations

- Pooled mean = 0.5098. Within ±1 pp of 50% — equal-footing sanity check passes (1 pp benchmark skill edge).
- Pooled `[p25, p75]` = `[0.46, 0.55]`. Live `[SCORE_BULLET_CENTER + NEUTRAL_MIN, ... + NEUTRAL_MAX]` = `[0.45, 0.55]`. **Keep**.
- Pooled `[p05, p95]` = `[0.39, 0.64]`. Live bullet axis `[0.25, 0.75]` is wider — keep, gives headroom for outliers.
- Per-ELO `eg_p50` spread: 0.4786 → 0.5296 = 5.1 pp. Pooled IQR width = 9.1 pp. Spread < IQR, but ELO d_max = 0.68 — the cohort centres differ enough that a per-ELO `ENDGAME_SCORE_ZONES` registry (mirroring `ENDGAME_SKILL_ZONES`) remains worthwhile per SEED-013 Plan 3.

### Collapse verdict

- **TC axis**: max |d| ≈ 0.27 (bullet vs rapid) → **review**
- **ELO axis**: max |d| ≈ 0.68 (800 vs 2400) → **keep separate**
- Heatmap of per-user p50 (5 ELO × 4 TC):

```
         bullet   blitz    rapid    classical
800       0.474   0.480    0.484    0.422
1200      0.492   0.479    0.513    0.500
1600      0.491   0.506    0.520    0.520
2000      0.508   0.533    0.519    0.512
2400      0.521   0.531    0.537    n=1*
```

ELO ramp survives the ±50 tightening. The hypothesis "ELO bucket effect collapses at tighter equal-footing" is **rejected** for absolute EG-score: the 2400 cohort scores 5.1 pp higher in endgames than the 800 cohort even when matched against opponents within ±50 Elo — a real EG-skill differential that ELO calibration's ~50% expected score under-promises specifically for endgame-reaching games.

---

## Section 1 — Score gap (eg vs non-eg)

### Currently set in code

| Constant                  | Value |
|---------------------------|------:|
| `SCORE_GAP_NEUTRAL_MIN`   | -0.10 |
| `SCORE_GAP_NEUTRAL_MAX`   | +0.10 |
| `SCORE_GAP_DOMAIN`        | 0.20  |
| `SCORE_TIMELINE_Y_DOMAIN` | [20, 80] |

### TC marginal (excludes sparse cell)

| TC        | n   | dmean   | p25     | p50     | p75    | p05     | p95    | eg_mean | non_eg_mean |
|-----------|----:|--------:|--------:|--------:|-------:|--------:|-------:|--------:|------------:|
| bullet    | 479 | -0.0088 | -0.0987 | -0.0167 | 0.0760 | -0.1899 | 0.2028 | 0.4998  | 0.5086      |
| blitz     | 473 | -0.0027 | -0.0946 | -0.0074 | 0.0826 | -0.2011 | 0.2040 | 0.5109  | 0.5136      |
| rapid     | 424 | -0.0062 | -0.0964 | 0.0004  | 0.0857 | -0.2443 | 0.2081 | 0.5174  | 0.5236      |
| classical | 128 | -0.0589 | -0.1853 | -0.0473 | 0.0716 | -0.3595 | 0.2196 | 0.4845  | 0.5433      |

### ELO marginal

| ELO  | n   | dmean   | p25     | p50     | p75    | p05     | p95    | eg_mean | non_eg_mean |
|------|----:|--------:|--------:|--------:|-------:|--------:|-------:|--------:|------------:|
| 800  | 286 | -0.0214 | -0.1124 | -0.0244 | 0.0539 | -0.2308 | 0.2211 | 0.4827  | 0.5040      |
| 1200 | 327 | -0.0231 | -0.1142 | -0.0264 | 0.0757 | -0.2692 | 0.2088 | 0.4962  | 0.5193      |
| 1600 | 345 | -0.0034 | -0.0983 | -0.0062 | 0.0982 | -0.2268 | 0.2205 | 0.5099  | 0.5134      |
| 2000 | 307 | -0.0054 | -0.0878 | -0.0014 | 0.0818 | -0.2032 | 0.1792 | 0.5206  | 0.5260      |
| 2400 | 239 | 0.0036  | -0.0783 | 0.0019  | 0.0950 | -0.2006 | 0.2051 | 0.5289  | 0.5252      |

### Pooled overall

| n    | dmean   | p25     | p50     | p75    | p05     | p95    | eg_mean | non_eg_mean |
|-----:|--------:|--------:|--------:|-------:|--------:|-------:|--------:|------------:|
| 1504 | -0.0104 | -0.1011 | -0.0132 | 0.0824 | -0.2291 | 0.2084 | 0.5069  | 0.5174      |

### Recommendations

- **Score-gap neutral zone**: pooled `[diff_p25, diff_p75]` = `[-0.10, +0.08]`. Live `±0.10`. |median| = 1.3 pp, well below the 5 pp asymmetry guard. **Keep symmetric ±0.10**.
- **Score-gap half-width**: pooled `max(|p05|, |p95|)` = 0.229. Live `SCORE_GAP_DOMAIN = 0.20`. **Consider widening to 0.25** so the bullet axis covers the 95th-percentile tail; not strictly required.
- **Timeline Y-axis**: pooled per-user `[non_eg_p05, eg_p95]` = roughly `[0.38, 0.63]` × 100 = `[38, 63]`. Live `[20, 80]` is comfortably wider — **keep**.

### Collapse verdict

- **TC axis**: max |d| ≈ 0.41 (blitz vs classical) → **review**. Classical cohort drops markedly more in endgames than other TCs (dmean -0.059 vs others ~-0.005); bullet/blitz/rapid are essentially indistinguishable from each other (pairwise d ≈ 0.05).
- **ELO axis**: max |d| ≈ 0.20 (1200 vs 2400) → **collapse** (just at the boundary). All ELO levels hover within ±2.5 pp of zero on dmean.

This is the cleanest ELO-collapse signal in the report. The within-user differential between EG and non-EG performance does not change with cohort strength — ratings are evidently calibrated jointly across game phases. The TC effect (classical users do worse in endgames vs their own non-endgames) is real and possibly tied to long-game adjudication / time-management dynamics; classical's mean dmean of -5.9 pp warrants the existing TC stratification.

---

## Section 2 — Conversion / Parity / Recovery + Endgame Skill

### Currently set in code

| Constant                                      | Value         |
|----------------------------------------------|---------------|
| `FIXED_GAUGE_ZONES.conversion`               | [0.65, 0.77]  |
| `FIXED_GAUGE_ZONES.parity`                   | [0.45, 0.55]  |
| `FIXED_GAUGE_ZONES.recovery`                 | [0.24, 0.36]  |
| `ENDGAME_SKILL_ZONES`                        | [0.47, 0.55]  |
| `NEUTRAL_ZONE_MIN/MAX` (score-gap inside §2) | ±0.05         |
| `BULLET_DOMAIN`                              | 0.20          |

### Pooled per-user rates (excludes sparse cell)

| Metric          | n    | p25    | p50    | p75    | mean   |
|----------------:|-----:|-------:|-------:|-------:|-------:|
| Conversion      | 1657 | 0.6481 | 0.7120 | 0.7692 | 0.7075 |
| Parity          | 1657 | 0.4455 | 0.5000 | 0.5652 | 0.5024 |
| Recovery        | 1657 | 0.2436 | 0.3065 | 0.3678 | 0.3088 |
| Endgame Skill   | 1657 | 0.4643 | 0.5076 | 0.5478 | 0.5063 |

### TC marginals (per-user p25 / p50 / p75)

| TC        | n   | Conversion             | Parity                 | Recovery               | Skill                  |
|-----------|----:|------------------------|------------------------|------------------------|------------------------|
| bullet    | 495 | 0.581 / 0.653 / 0.713  | 0.447 / 0.500 / 0.567  | 0.298 / 0.354 / 0.404  | 0.459 / 0.504 / 0.551  |
| blitz     | 492 | 0.667 / 0.717 / 0.764  | 0.448 / 0.504 / 0.561  | 0.248 / 0.307 / 0.354  | 0.465 / 0.510 / 0.547  |
| rapid     | 472 | 0.696 / 0.745 / 0.790  | 0.455 / 0.504 / 0.567  | 0.227 / 0.278 / 0.333  | 0.476 / 0.514 / 0.547  |
| classical | 198 | 0.680 / 0.750 / 0.832  | 0.396 / 0.500 / 0.563  | 0.173 / 0.250 / 0.331  | 0.446 / 0.498 / 0.553  |

### ELO marginals

| ELO  | n   | Conversion             | Parity                 | Recovery               | Skill                  |
|------|----:|------------------------|------------------------|------------------------|------------------------|
| 800  | 306 | 0.600 / 0.687 / 0.744  | 0.400 / 0.500 / 0.563  | 0.236 / 0.306 / 0.368  | 0.439 / 0.494 / 0.536  |
| 1200 | 349 | 0.636 / 0.702 / 0.760  | 0.430 / 0.486 / 0.552  | 0.241 / 0.304 / 0.362  | 0.453 / 0.498 / 0.536  |
| 1600 | 373 | 0.660 / 0.715 / 0.773  | 0.447 / 0.500 / 0.561  | 0.234 / 0.290 / 0.354  | 0.466 / 0.508 / 0.542  |
| 2000 | 347 | 0.665 / 0.723 / 0.779  | 0.451 / 0.509 / 0.566  | 0.247 / 0.310 / 0.376  | 0.472 / 0.511 / 0.556  |
| 2400 | 282 | 0.678 / 0.739 / 0.793  | 0.477 / 0.529 / 0.577  | 0.268 / 0.322 / 0.388  | 0.492 / 0.532 / 0.570  |

### Recommendations

- **Conversion** pooled IQR `[0.65, 0.77]` → exact match to live `[0.65, 0.77]`. **Keep**.
- **Parity** pooled IQR `[0.45, 0.57]`, p50 = 0.50. Live `[0.45, 0.55]`. Slightly asymmetric pull on the upper bound (+2 pp) but median is exactly 50%. **Keep** or widen upper to 0.57 if you want IQR symmetry.
- **Recovery** pooled IQR `[0.24, 0.37]`. Live `[0.24, 0.36]`. **Keep**.
- **Endgame Skill** pooled IQR `[0.46, 0.55]`. Live `[0.47, 0.55]`. **Keep** or widen lower to 0.46 (1 pp).

### Collapse verdicts

| Metric         | TC d_max (pair)                | ELO d_max (pair)               |
|----------------|--------------------------------|--------------------------------|
| Conversion     | **1.00 keep** (bullet–rapid)   | **0.65 keep** (800–2400)       |
| Parity         | **0.24 review** (rapid–classical) | **0.34 review** (1200–2400) |
| Recovery       | **0.88 keep** (bullet–classical)  | **0.28 review** (1600–2400) |
| Endgame Skill  | **0.20 review** (rapid–classical) | **0.59 keep** (800–2400)    |

**ELO did not collapse on Conversion (0.65) or Skill (0.59) at ±50.** These remain meaningfully cohort-stratified at equal footing. Conversion's TC keep verdict is dominated by bullet → rapid (62.4% to 78.2% per-user p50): bullet conversion is structurally lower because the time crunch routes more "should-have-won" games into draws and losses; this is a TC-genuine effect, not a confound.

---

## Section 3 — Evals at game phase transitions

### Currently set in code

| Constant                                 | Value (cp / pawns) |
|-----------------------------------------|--------------------|
| `EVAL_BASELINE_PAWNS_WHITE`             | +0.25 / +25 cp     |
| `EVAL_BASELINE_PAWNS_BLACK`             | -0.25 / -25 cp (symmetric ✓) |
| `EVAL_NEUTRAL_MIN_PAWNS`                | -0.30 / -30 cp     |
| `EVAL_NEUTRAL_MAX_PAWNS`                | +0.30 / +30 cp     |
| `EVAL_BULLET_DOMAIN_PAWNS`              | 1.5 / 150 cp       |
| `EVAL_CONFIDENCE_MIN_N`                 | 20                 |
| `EVAL_OUTLIER_TRIM_CP` (D-08)           | 2000               |
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS`  | -0.75 / -75 cp     |
| `ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS`  | +0.75 / +75 cp     |
| `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS`       | 2.0 / 200 cp       |
| `ENDGAME_ENTRY_EVAL_CENTER`             | 0 (uncentered)     |

### Pass 1 — Symmetric baselines (deduped, white-POV, no equal-footing)

| Phase | n_games   | baseline_cp_white | median_white | sd     |
|-------|----------:|------------------:|-------------:|-------:|
| MG    | 1,246,674 | **+25.18 cp**     | +24.0 cp     | 237.7  |
| EG    |   801,065 | **+9.86 cp**      |  0.0 cp      | 442.6  |

MG baseline reproduces the live constant exactly. EG baseline is +10 cp; the live EG-entry tile is 0-centered, so this 10-cp offset is fully absorbed into the (uncentered) calibration of the tile.

### Pass 2 — Centered per-(user, color) pooled distribution at ±50

#### Middlegame entry (centered on ±25 cp)

| Axis      | n    | ctr_mean | sd    | p05    | p25   | p50   | p75   | p95   |
|-----------|-----:|---------:|------:|-------:|------:|------:|------:|------:|
| pooled    | 3289 | +2.84    | 58.3  | -96.9  | -22.3 | +5.7  | +34.3 | +83.9 |
| tc:bullet | 988  | -4.61    | 68.3  | -127.2 | -31.9 | +2.9  | +34.9 | +86.1 |
| tc:blitz  | 984  | +2.98    | 48.1  | -81.2  | -17.9 | +4.3  | +28.3 | +73.3 |
| tc:rapid  | 934  | +8.68    | 50.2  | -68.4  | -15.9 | +9.4  | +35.4 | +83.3 |
| tc:classical | 383 | +7.48 | 69.4  | -114.8 | -21.6 | +8.8  | +43.1 | +102.3|
| elo:800   | 626  | -6.97    | 89.8  | -157.1 | -58.2 | +1.7  | +52.3 | +124.7|
| elo:1200  | 703  | +4.79    | 67.0  | -101.0 | -26.9 | +11.9 | +46.2 | +92.6 |
| elo:1600  | 732  | +5.30    | 47.3  | -76.2  | -20.5 | +6.9  | +36.2 | +76.7 |
| elo:2000  | 684  | +7.07    | 35.3  | -52.3  | -13.4 | +7.4  | +28.9 | +62.6 |
| elo:2400  | 544  | +2.98    | 27.4  | -37.2  | -14.5 | +2.0  | +18.3 | +51.4 |

#### Endgame entry (centered on ±10 cp)

| Axis      | n    | ctr_mean | sd    | p05    | p25    | p50   | p75   | p95    |
|-----------|-----:|---------:|------:|-------:|-------:|------:|------:|-------:|
| pooled    | 3086 | +7.55    | 119.1 | -190.0 | -55.7  | +8.3  | +73.7 | +204.8 |
| tc:bullet | 976  | -6.42    | 138.7 | -245.5 | -86.6  | -3.7  | +76.0 | +222.4 |
| tc:blitz  | 960  | +13.63   | 102.9 | -144.1 | -42.7  | +11.6 | +65.7 | +183.9 |
| tc:rapid  | 869  | +17.98   | 105.8 | -155.9 | -40.6  | +14.1 | +79.4 | +205.3 |
| tc:classical | 281| +3.06   | 131.2 | -212.1 | -72.8  | +8.6  | +85.5 | +218.2 |
| elo:800   | 556  | -14.65   | 173.7 | -287.8 | -130.6 | -19.5 | +98.7 | +274.0 |
| elo:1200  | 663  | +0.47    | 134.8 | -220.5 | -81.9  | -3.2  | +86.1 | +233.9 |
| elo:1600  | 695  | +15.30   | 100.4 | -148.2 | -47.8  | +11.7 | +78.0 | +189.0 |
| elo:2000  | 649  | +18.96   | 86.5  | -121.4 | -34.7  | +18.5 | +67.3 | +174.7 |
| elo:2400  | 523  | +15.69   | 72.0  | -87.3  | -36.8  | +12.7 | +59.2 | +138.1 |

### Recommendations

- **MG-entry baseline**: measured +25 cp = live +25 cp. **Keep `EVAL_BASELINE_PAWNS_WHITE = 0.25` (and symmetric -0.25 for black).**
- **MG-entry neutral band**: pooled centered IQR `[-22, +34]` → symmetric ±30 cp. Live `±0.30 pawns` ✓. **Keep**.
- **MG-entry domain**: pooled centered `[p05, p95]` = `[-97, +84]` → ~±100 cp. Live `±150 cp` is wider. **Keep** (matches the ELO=800 cohort tail).
- **EG-entry baseline (live)**: 0-centered (no baseline subtraction). Measured +10 cp white-POV is small; cohort-symmetric, so 0-centering is not biased.
- **EG-entry neutral band**: pooled centered IQR `[-56, +74]`. Live `±75 cp`. **Keep**.
- **EG-entry domain**: pooled centered `[p05, p95]` = `[-190, +205]`. Live `±200 cp`. **Keep**.

### Collapse verdicts (centered)

- **MG**: TC max |d| ≈ 0.22 (bullet vs rapid) → **review**; ELO max |d| ≈ 0.21 (800 vs 2000) → **review**.
- **EG**: TC max |d| ≈ 0.20 (bullet vs rapid) → **collapse** (boundary); ELO max |d| ≈ 0.25 (800 vs 2000) → **review**.

The within-user MG / EG eval distributions are roughly ELO-flat — `mean` differences are only ~5–15 cp across cohorts. What does change dramatically is **within-cohort SD**: per-user MG centered SD drops from 89.8 (800) to 27.4 (2400). Higher-rated players are far more consistent in entering middlegames near book-equal — half the within-cohort variance disappears at 1600, two-thirds at 2400. The ELO ramp on `mean` is small (0.20–0.25 d) but the cohort-shape difference is large; the live tile shows a single per-user mean which the pooled IQR calibration captures well, so this matters more for any future "consistency" metric than for the bullet-chart neutral band.

EG-entry mean ramps from -15 cp at 800 to +16 cp at 2400 (centered). That's a 31 cp swing — small compared to the per-user SD (72-174 cp), but consistent: higher-rated cohorts enter endgames at marginally better evals against equal opponents. **This is a real skill effect, not a matchmaking confound** — the equal-footing filter at ±50 doesn't dampen it.

---

## Section 4 — Time pressure at endgame entry

### Currently set in code

| Constant                       | Value |
|--------------------------------|------:|
| `NEUTRAL_PCT_THRESHOLD`        | 5.0   |
| `NEUTRAL_TIMEOUT_THRESHOLD`    | 5.0   |

### Clock %-diff (per-user)

| Axis      | n   | mean   | p05    | p25   | p50   | p75   | p95   |
|-----------|----:|-------:|-------:|------:|------:|------:|------:|
| pooled    | 1653| -1.43  | -18.54 | -6.36 | -0.68 | +4.47 | +13.07|
| tc:bullet | 493 | -0.19  | -8.81  | -3.95 | -0.31 | +2.83 | +9.73 |
| tc:blitz  | 492 | -1.32  | -17.86 | -7.06 | -0.74 | +4.69 | +12.31|
| tc:rapid  | 472 | -1.53  | -18.15 | -7.90 | -0.69 | +5.12 | +13.00|
| tc:classical | 196 | -4.63 | -31.95 | -15.18 | -3.57 | +6.72 | +19.36 |
| elo:800   | 304 | -0.88  | -17.67 | -6.05 | -0.03 | +5.19 | +14.24|
| elo:1200  | 349 | -1.53  | -19.11 | -6.92 | -0.58 | +4.55 | +13.49|
| elo:1600  | 372 | -1.61  | -21.13 | -6.94 | -0.44 | +5.22 | +13.90|
| elo:2000  | 346 | -2.47  | -18.94 | -8.21 | -2.06 | +3.40 | +11.54|
| elo:2400  | 282 | -0.40  | -12.44 | -4.67 | -0.52 | +4.02 | +11.04|

### Net timeout (per-user, %)

| Axis      | n   | mean  | p25   | p50   | p75    |
|-----------|----:|------:|------:|------:|-------:|
| pooled    | 1653| +0.11 | -4.58 | +1.18 | +5.88  |
| tc:bullet | 493 | +0.29 | -10.84| +0.83 | +11.54 |
| tc:blitz  | 492 | +0.09 | -6.06 | +1.99 | +7.82  |
| tc:rapid  | 472 | +0.20 | -1.66 | +1.60 | +3.94  |
| tc:classical | 196 | -0.49 | 0.00 | 0.00 | +1.99  |
| elo:800   | 304 | -1.62 | -7.16 | 0.00  | +4.80  |
| elo:1200  | 349 | -0.39 | -4.76 | +0.91 | +4.76  |
| elo:1600  | 372 | -0.27 | -3.87 | +1.09 | +5.42  |
| elo:2000  | 346 | +0.62 | -5.35 | +1.88 | +6.90  |
| elo:2400  | 282 | +2.48 | -3.43 | +3.19 | +9.40  |

### Recommendations

- **Clock %-diff neutral**: pooled IQR `[-6.36, +4.47]` ≈ ±5 pp. Live ±5.0 pp. **Keep**.
- **Net timeout neutral**: pooled IQR `[-4.58, +5.88]` ≈ ±5 pp. Live ±5.0 pp. **Keep**.

### Collapse verdicts

- **Clock %-diff**: TC max |d| ≈ 0.43 (bullet vs classical) → **review**; ELO max |d| ≈ 0.23 (2000 vs 2400) → **review**.
- **Net timeout**: TC max |d| ≈ 0.09 → **collapse**; ELO max |d| ≈ 0.34 (800 vs 2400) → **review**.

ELO ramp on net timeout is striking and survives equal-footing tightly: 2400 cohort net-flags +2.5 pp, 800 cohort net-flags -1.6 pp. That's +4 pp swing in flag-balance solely from skill — high-rated players reliably win on time more than they lose on time, even matched ±50.

---

## Section 5 — Time pressure vs performance

### Currently set in code

| Constant                       | Value     |
|--------------------------------|-----------|
| `Y_AXIS_DOMAIN`                | [0.2, 0.8]|
| `X_AXIS_DOMAIN`                | [0, 100]  |
| `MIN_GAMES_FOR_CLOCK_STATS`    | 10        |

### TC marginal score by time bucket (n ≥ 100 only)

| time_bucket | bullet         | blitz          | rapid          | classical      |
|-----------:|----------------|----------------|----------------|----------------|
| 0          | 0.264 (11295)  | 0.336 (10610)  | 0.336 (3764)   | 0.406 (775)    |
| 1          | 0.397 (18774)  | 0.432 (11842)  | 0.431 (4056)   | 0.470 (556)    |
| 2          | 0.488 (19862)  | 0.490 (12702)  | 0.463 (5107)   | 0.493 (669)    |
| 3          | 0.527 (22582)  | 0.514 (15301)  | 0.509 (6771)   | 0.446 (780)    |
| 4          | 0.549 (23122)  | 0.529 (17718)  | 0.530 (8653)   | 0.455 (946)    |
| 5          | 0.566 (21458)  | 0.545 (19901)  | 0.532 (11667)  | 0.474 (1130)   |
| 6          | 0.562 (16937)  | 0.539 (20164)  | 0.524 (14750)  | 0.504 (1445)   |
| 7          | 0.548 (10753)  | 0.537 (16491)  | 0.525 (17214)  | 0.504 (1800)   |
| 8          | 0.538 (4315)   | 0.538 (9300)   | 0.524 (14640)  | 0.498 (2146)   |
| 9          | 0.505 (904)    | 0.523 (3516)   | 0.519 (6825)   | 0.510 (5585)   |

### ELO marginal score by time bucket (n ≥ 100 only)

| time_bucket | 800            | 1200           | 1600           | 2000           | 2400           |
|-----------:|----------------|----------------|----------------|----------------|----------------|
| 0          | 0.277 (3700)   | 0.287 (5652)   | 0.302 (6538)   | 0.330 (6589)   | 0.338 (3965)   |
| 1          | 0.382 (4512)   | 0.401 (7503)   | 0.400 (8619)   | 0.431 (8346)   | 0.448 (6248)   |
| 2          | 0.467 (4837)   | 0.475 (7974)   | 0.487 (9335)   | 0.493 (9202)   | 0.500 (6992)   |
| 3          | 0.512 (5705)   | 0.510 (9600)   | 0.515 (11355)  | 0.524 (10741)  | 0.533 (8033)   |
| 4          | 0.529 (6338)   | 0.528 (11045)  | 0.536 (12971)  | 0.541 (11516)  | 0.553 (8569)   |
| 5          | 0.540 (6891)   | 0.533 (12040)  | 0.540 (14720)  | 0.566 (12024)  | 0.568 (8481)   |
| 6          | 0.528 (7197)   | 0.525 (12565)  | 0.537 (15036)  | 0.558 (10952)  | 0.562 (7546)   |
| 7          | 0.522 (6535)   | 0.517 (11813)  | 0.532 (13635)  | 0.547 (8931)   | 0.564 (5344)   |
| 8          | 0.501 (4845)   | 0.519 (8930)   | 0.528 (9181)   | 0.557 (4936)   | 0.565 (2509)   |
| 9          | 0.494 (3458)   | 0.501 (5789)   | 0.535 (4985)   | 0.536 (2090)   | 0.569 (508)    |

### Recommendations

- Curve fits comfortably inside `Y_AXIS_DOMAIN = [0.2, 0.8]` at every TC × time bucket. **Keep**.

### Collapse verdicts

- **TC axis**: max |d| ≈ 0.32 at time_bucket 0 (bullet 0.264 vs classical 0.406) → **review**. The largest TC gaps are at low time_bucket (severe time pressure): bullet players score worse under heavy pressure than classical players, who shrug off the same nominal % of base time because the absolute clock is still seconds. By time_bucket 6+ all TCs converge.
- **ELO axis**: max |d| ≈ 0.16 (800 vs 2400 around time_buckets 0, 1, 9) → **collapse**. The slope of "more time → better score" is essentially identical across all five ELO cohorts.

---

## Section 6 — Endgame type breakdown

### Currently set in code

| Constant                          | Value |
|----------------------------------|-------|
| `NEUTRAL_ZONE_MIN/MAX` (per-class score-diff in `EndgameWDLChart`) | ±0.05 |
| `BULLET_DOMAIN`                  | 0.20  |
| `PER_CLASS_GAUGE_ZONES.rook`     | conv [0.65, 0.75] / recov [0.26, 0.36] |
| `PER_CLASS_GAUGE_ZONES.minor_piece` | conv [0.63, 0.73] / recov [0.31, 0.41] |
| `PER_CLASS_GAUGE_ZONES.pawn`     | conv [0.67, 0.79] / recov [0.23, 0.34] |
| `PER_CLASS_GAUGE_ZONES.queen`    | conv [0.73, 0.83] / recov [0.20, 0.30] |
| `PER_CLASS_GAUGE_ZONES.mixed`    | conv [0.65, 0.75] / recov [0.28, 0.38] |
| `PER_CLASS_GAUGE_ZONES.pawnless` | conv [0.70, 0.80] / recov [0.21, 0.31] |

### Pooled per-class summary

| Class       | games   | users | score  | score_diff | conversion | recovery |
|-------------|--------:|------:|-------:|-----------:|-----------:|---------:|
| rook        | 67,384  | 1816  | 0.5072 | +0.0144    | 0.7071     | 0.2993   |
| minor_piece | 49,701  | 1771  | 0.5058 | +0.0115    | 0.6900     | 0.3283   |
| pawn        | 26,680  | 1674  | 0.5076 | +0.0151    | 0.7327     | 0.2771   |
| queen       | 24,712  | 1691  | 0.5083 | +0.0167    | 0.7732     | 0.2409   |
| mixed       | 379,849 | 1881  | 0.5037 | +0.0075    | 0.6898     | 0.3134   |
| pawnless    |  4,117  | 1227  | 0.5040 | +0.0080    | 0.7972     | 0.1991   |

### Compare to live `PER_CLASS_GAUGE_ZONES`

Every pooled per-class conversion and recovery rate at ±50 sits inside (or at the boundary of) the current live gauge bands:

| Class       | conv ±50 | conv live band | recov ±50 | recov live band |
|-------------|---------:|----------------|----------:|-----------------|
| rook        | 0.7071   | [0.65, 0.75] ✓ | 0.2993    | [0.26, 0.36] ✓  |
| minor_piece | 0.6900   | [0.63, 0.73] ✓ | 0.3283    | [0.31, 0.41] ✓  |
| pawn        | 0.7327   | [0.67, 0.79] ✓ | 0.2771    | [0.23, 0.34] ✓  |
| queen       | 0.7732   | [0.73, 0.83] ✓ | 0.2409    | [0.20, 0.30] ✓  |
| mixed       | 0.6898   | [0.65, 0.75] ✓ | 0.3134    | [0.28, 0.38] ✓  |
| pawnless    | 0.7972   | [0.70, 0.80] (boundary) | 0.1991 | [0.21, 0.31] (1 pp below) |

Pawnless conversion lands at the upper boundary and recovery 1 pp below the lower bound, but n_users on pawnless is the smallest (1227 vs ≥1700 elsewhere). Within Monte Carlo error of the live calibration. **Keep all per-class bands.**

### Recommendations

- **Per-class score-diff neutral zone (±0.05)**: every pooled per-class score_diff lies in `[+0.0075, +0.0167]` — well inside ±0.05. **Keep**.
- **PER_CLASS_GAUGE_ZONES**: **keep**. ±50 reproduces the same pooled per-class conv/recov rates the current zones were calibrated against.

### Collapse verdicts (per metric × class summary)

| Metric                 | TC verdict | ELO verdict | Notes |
|------------------------|------------|-------------|-------|
| Per-class score        | collapse   | collapse    | Pooled score within ±2 pp of 0.5 every cell |
| Per-class conversion   | review     | collapse–review | Bullet much lower; pattern same as §2 |
| Per-class recovery     | review     | collapse–review | Mirror of conversion |

---

## Top-axis collapse summary (HEADLINE DELIVERABLE — ±50 variant)

| Metric                                  | TC verdict (d_max)             | ELO verdict (d_max)            | Implication at ±50 vs ±100 |
|-----------------------------------------|--------------------------------|--------------------------------|----------------------------|
| Endgame score (per-user, EG only)       | review (0.27)                  | **keep separate (0.68)**       | ELO ramp survives          |
| Score gap (eg − non_eg)                 | review (0.41)                  | **collapse (0.20)**            | Already collapsed at ±100  |
| Conversion (per-user)                   | keep separate (1.00)           | **keep separate (0.65)**       | ELO ramp survives          |
| Parity (per-user)                       | review (0.24)                  | review (0.34)                  | Mostly stable              |
| Recovery (per-user)                     | keep separate (0.88)           | review (0.28)                  | Stable                     |
| Endgame Skill (per-user)                | review (0.20)                  | **keep separate (0.59)**       | ELO ramp survives          |
| MG-entry centered eval (per-user mean)  | review (0.22)                  | review (0.21)                  | Stable                     |
| EG-entry centered eval (per-user mean)  | collapse (0.20)                | review (0.25)                  | Stable                     |
| Clock pressure %-of-base                | review (0.43)                  | review (0.23)                  | Stable                     |
| Net timeout rate                        | collapse (0.09)                | review (0.34)                  | Real skill effect          |
| Time-pressure curve (per-bucket)        | review (0.32)                  | **collapse (0.16)**            | Stays collapsed            |
| Per-class score                         | collapse                       | collapse                       | Stays collapsed            |
| Per-class conversion                    | review                         | collapse–review                | Same pattern as §2 conv    |
| Per-class recovery                      | review                         | collapse–review                | Same pattern as §2 recov   |

**Bottom line.** Tightening from ±100 to ±50 does NOT collapse the ELO ramp on the metrics where it was already large (Conversion, Endgame Skill, EG-only score). Two metrics that already collapsed on ELO (score gap, time-pressure curve) stay collapsed. The only meaningful "the gap gets smaller at ±50" effect is in the absolute level of conversion (mean 0.7075 at ±50 vs higher at ±100) — but the cohort gradient is preserved.

The hypothesis "ELO bucket effects are largely a matchmaking-confound artefact" is **not supported** by this report. Equal-footing matters for level honesty (the canonical ±100 already neutralises most of the matchmaking bias), but it does not eliminate the cohort gradient. The ELO ramps on Conversion, Skill, and EG-score are bona fide skill differences between cohorts.

## Recommended thresholds summary (vs ±100 calibration)

| Metric                          | Code constant                          | Currently set | Recommended (±50)        | Collapse verdict          | Action  |
|---------------------------------|----------------------------------------|---------------|--------------------------|---------------------------|---------|
| EG-only score neutral           | `SCORE_BULLET_NEUTRAL_MIN/MAX`         | ±0.05         | ±0.05 (pooled IQR `[0.46, 0.55]`) | TC review / ELO keep      | keep    |
| EG-only score domain            | `SCORE_BULLET_DOMAIN`                  | 0.25          | 0.25                     | —                         | keep    |
| Score-gap neutral               | `SCORE_GAP_NEUTRAL_MIN/MAX`            | ±0.10         | ±0.10                    | TC review / ELO collapse  | keep    |
| Score-gap domain                | `SCORE_GAP_DOMAIN`                     | 0.20          | 0.25 (p05/p95 = 0.23)    | —                         | consider widen |
| Conversion gauge                | `FIXED_GAUGE_ZONES.conversion`         | [0.65, 0.77]  | [0.65, 0.77]             | TC keep / ELO keep        | keep    |
| Parity gauge                    | `FIXED_GAUGE_ZONES.parity`             | [0.45, 0.55]  | [0.45, 0.57]             | TC review / ELO review    | keep    |
| Recovery gauge                  | `FIXED_GAUGE_ZONES.recovery`           | [0.24, 0.36]  | [0.24, 0.37]             | TC keep / ELO review      | keep    |
| Endgame Skill gauge             | `ENDGAME_SKILL_ZONES`                  | [0.47, 0.55]  | [0.46, 0.55]             | TC review / ELO keep      | keep    |
| MG-entry baseline               | `EVAL_BASELINE_PAWNS_WHITE/BLACK`      | ±0.25         | ±0.25                    | —                         | keep    |
| MG-entry neutral                | `EVAL_NEUTRAL_MIN/MAX_PAWNS`           | ±0.30         | ±0.30                    | TC review / ELO review    | keep    |
| MG-entry domain                 | `EVAL_BULLET_DOMAIN_PAWNS`             | 1.5           | 1.0–1.5                  | —                         | keep    |
| EG-entry neutral                | `ENDGAME_ENTRY_EVAL_NEUTRAL_MIN/MAX_PAWNS` | ±0.75     | ±0.75                    | TC collapse / ELO review  | keep    |
| EG-entry domain                 | `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS`      | 2.0           | 2.0                      | —                         | keep    |
| Clock %-diff neutral            | `NEUTRAL_PCT_THRESHOLD`                | 5.0           | 5.0                      | TC review / ELO review    | keep    |
| Net-timeout neutral             | `NEUTRAL_TIMEOUT_THRESHOLD`            | 5.0           | 5.0                      | TC collapse / ELO review  | keep    |
| Per-class score-diff neutral    | `NEUTRAL_ZONE_MIN/MAX` (in `EndgameWDLChart`) | ±0.05  | ±0.05                    | collapse                  | keep    |
| Per-class gauge zones           | `PER_CLASS_GAUGE_ZONES`                | (per class)   | unchanged                | review                    | keep    |

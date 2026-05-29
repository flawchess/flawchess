# Gap-Metric Percentile Candidacy — 2026-05-22

Empirical input for SEED-019 tier classification. Tests whether the 5 candidate gap metrics on the Endgame Stats page are genuine percentile-chip candidates (skill-isolating, clean distribution) or merely rating proxies in disguise.

- **DB**: benchmark (Docker localhost:5433, `flawchess_benchmark`)
- **Cohort**: full ingest, 100 users/cell × 5 ELO × 4 TC, sparse `(2400, classical)` cell (n=12) excluded from all marginals and the pooled distribution.
- **Filters**: canonical CTE with `bic.status='completed'`; equal-footing opponent filter (`|opp_rating − user_rating| ≤ 100`); ELO bucketed by the cohort user's **rating at game time** (per the "Rating-lag selection bias" methodology fix); sub-800 dropped.
- **Per-user floors**: ≥30 endgame AND ≥30 non-endgame games for Endgame Score Gap; ≥20 endgame-entry games for Achievable Score Gap; ≥20 spans/bucket for Section 2 ΔES.

---

## Headline verdicts

| Metric | Pooled n | Pooled median | Skew | Excess kurt | 800 median | 2400 median | d_max (800↔2400) | Verdict | SEED-019 tier |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| **Endgame Score Gap** | 2003 | −1.2pp | +0.02 | −0.03 | −3.1pp | +0.9pp | **0.19** collapse | **Skill-isolating, clean** | **Tier 1 — KEEP** |
| **Achievable Score Gap** | 2299 | +0.6pp | −0.28 | +1.78 | −0.9pp | +2.6pp | **0.32** review | **Mostly skill-isolating, mild proxy** | **Tier 1 — KEEP** |
| **Parity Score Gap** (Section 2) | 1804 | +0.4pp | −0.16 | +1.33 | +0.1pp | +1.4pp | **0.30** review | **Cleanest Tier-1, slight proxy** | **Tier 1 — KEEP** |
| **Conversion Score Gap** (Section 2) | 2060 | −5.0pp | −0.95 | +1.42 | −10.9pp | −1.3pp | **1.37** keep separate | **Heavy rating-proxy** (sigmoid bias + skill convergence to engine) | **Tier 2 — demote**, or drop |
| **Recovery Score Gap** (Section 2) | 1977 | +5.6pp | +0.83 | +1.44 | +9.4pp | +4.0pp | **0.95** keep separate | **Heavy rating-proxy (inverted)** + opponent confound | **DROP** |

**One-line summary:** Endgame Score Gap is the cleanest empirically (surprising, given prior Socratic concern). Parity is the cleanest Section-2 candidate. Achievable Score Gap is acceptable with mild rating coupling. **Conversion and Recovery Score Gap are both heavy rating proxies** — Conversion because weaker players blunder more often when up material (engine-baseline rises with rating); Recovery because stronger players' opponents don't gift recoveries (the well-known opponent confound that knocked Recovery out of the retracted 87.3 Skill composite).

---

## 1. Endgame Score Gap (`endgame_score − non_endgame_score`, page-level)

### Pooled distribution (sparse cell excluded)

| n | mean | sd | p05 | p25 | p50 | p75 | p95 | skew | excess kurt |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2003 | −1.1pp | 13.1pp | −22.1pp | −10.1pp | **−1.2pp** | +7.8pp | +20.9pp | +0.02 | −0.03 |

**Distribution shape: textbook normal.** Skew ≈ 0, excess kurtosis ≈ 0, unimodal symmetric. Percentile is interpretable end-to-end.

### Per-bucket medians and SDs

| ELO bucket | n | median | sd | p05 | p95 |
|---:|---:|---:|---:|---:|---:|
| 800 | 342 | **−3.1pp** | 14.1pp | −24.9pp | +22.9pp |
| 1200 | 484 | −2.1pp | 13.6pp | −23.0pp | +22.7pp |
| 1600 | 501 | −0.7pp | 13.5pp | −21.8pp | +20.0pp |
| 2000 | 414 | −0.2pp | 11.9pp | −20.7pp | +17.6pp |
| 2400 | 262 | **+0.9pp** | 11.7pp | −19.0pp | +18.0pp |

Median shift across 1600 ELO points: **+4.0pp** (800 → 2400). Within-bucket IQR ≈ 18pp. The shift is one-quarter of the typical user's spread. SD narrows modestly from 14.1pp to 11.7pp — stronger players are slightly more balanced.

**Cohen's d (800 vs 2400) = 0.19 → COLLAPSE on the ELO axis.** Percentile is genuinely rating-invariant.

### Verdict

✅ **Strong percentile candidate.** Distribution is normal-shaped; per-bucket medians barely shift; d=0.19 means a user's percentile rank is essentially independent of their ELO. The conceptual concern I raised earlier (self-relative interpretation: "high gap rewards imbalance, not endgame skill") survives — a user with gap=+10pp could be a 1200 with weak non-endgame play OR a 2400 with strong endgame play — but statistically the chip is honest.

---

## 2. Achievable Score Gap (`endgame_score − entry_expected_score`, page-level)

### Pooled distribution

| n | mean | sd | p05 | p25 | p50 | p75 | p95 | skew | excess kurt |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2299 | +0.3pp | 8.1pp | −13.3pp | −4.0pp | **+0.6pp** | +5.0pp | +13.0pp | −0.28 | +1.78 |

**Distribution shape: slightly left-skewed, mildly heavy-tailed.** Still unimodal and reasonably symmetric — percentile is interpretable.

### Per-bucket medians and SDs

| ELO bucket | n | median | sd |
|---:|---:|---:|---:|
| 800 | 374 | **−0.9pp** | 9.3pp |
| 1200 | 541 | −0.5pp | 8.0pp |
| 1600 | 575 | +0.2pp | 7.9pp |
| 2000 | 498 | +1.5pp | 7.8pp |
| 2400 | 311 | **+2.6pp** | 6.9pp |

Median shift: **+3.5pp** across 1600 ELO points; within-bucket IQR ≈ 9pp. SD narrows from 9.3pp to 6.9pp.

**Cohen's d (800 vs 2400) = 0.32 → REVIEW.** Some rating coupling, but acceptable.

### Verdict

✅ **Tier-1 candidate.** Per-bucket median shift is ~40% of IQR (vs ~22% for Endgame Score Gap), so the chip carries a mild rating signal but the within-bucket variance dominates. Acceptable for Tier-1 with no special handling. The Stockfish-ceiling baseline does most of the rating-stripping work; the residual coupling likely reflects skill-stratified position quality at endgame entry (stronger players walk into slightly better positions even after eval-baseline adjustment).

---

## 3. Conversion Score Gap (Section 2 ΔES, conv bucket)

### Pooled distribution

| n | mean | sd | p05 | p25 | p50 | p75 | p95 | skew | excess kurt |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2060 | −6.4pp | 9.6pp | −24.8pp | −11.3pp | **−5.0pp** | +0.1pp | +6.8pp | **−0.95** | +1.42 |

**Distribution shape: meaningfully left-skewed, heavy-tailed.** Mass piles up at modest negative values; long left tail of catastrophic underperformers. Percentile interpretation suffers in the right tail: getting from p75 (+0.1pp) to p95 (+6.8pp) covers 7pp; getting from p25 (−11.3pp) to p05 (−24.8pp) covers 14pp.

### Per-bucket medians and SDs

| ELO bucket | n | median | sd |
|---:|---:|---:|---:|
| 800 | 336 | **−10.9pp** | 10.1pp |
| 1200 | 494 | −6.5pp | 9.1pp |
| 1600 | 514 | −4.1pp | 8.7pp |
| 2000 | 435 | −1.5pp | 8.6pp |
| 2400 | 281 | **−1.3pp** | 6.6pp |

Median shift: **+9.6pp** across 1600 ELO points; within-bucket IQR ≈ 11pp. The rating shift is nearly as large as the within-bucket spread.

**Cohen's d (800 vs 2400) = 1.37 → KEEP SEPARATE (large effect).** This metric is dominated by rating, not skill-isolated.

### Why this happens

Two compounding forces:
1. **Sigmoid bias** (per SKILL.md §3.2.2): `ES_entry ≈ 0.6` in the conv bucket (user up material), ceiling at 1.0 limits upside. The pooled mean is structurally negative (−6.4pp) for everyone.
2. **Skill-mediated convergence to engine prediction.** Strong players blunder less often when up material, so their realized score tracks the engine prediction closely (median ≈ 0). Weak players blunder frequently, dragging their realized score well below prediction (median ≈ −11pp).

The second effect is the "rating proxy" mechanism. A 1200 player's percentile on Conversion Score Gap is dominated by being-a-1200, not by their conversion skill within the 1200 cohort.

### Verdict

⚠️ **Demote from Tier 1.** Statistically dominated by rating. Options:
- **Tier 2** (rating-proxy, ship with honest "this mostly tracks ELO" labeling) — same treatment as the raw Conversion %.
- **Stratify** to a same-cohort percentile (compare against your own rating bucket) — but the seed explicitly chose global-only.
- **Drop** the percentile chip on this row entirely; the existing ΔES value + IQR zone band already carries the signal.

Lean toward **drop the chip; keep the value**. The "top X%" framing would be misleading.

---

## 4. Parity Score Gap (Section 2 ΔES, parity bucket)

### Pooled distribution

| n | mean | sd | p05 | p25 | p50 | p75 | p95 | skew | excess kurt |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1804 | +0.1pp | 6.5pp | −10.6pp | −3.6pp | **+0.4pp** | +4.0pp | +10.1pp | −0.16 | +1.33 |

**Distribution shape: cleanest of the Section-2 buckets.** Near-symmetric (skew −0.16), unimodal, mildly heavy-tailed. The expected sigmoid bias is small here because `ES_entry ≈ 0.5` (no ceiling/floor compression).

### Per-bucket medians and SDs

| ELO bucket | n | median | sd |
|---:|---:|---:|---:|
| 800 | 211 | **+0.1pp** | 7.8pp |
| 1200 | 399 | −0.5pp | 6.6pp |
| 1600 | 469 | −0.2pp | 6.8pp |
| 2000 | 434 | +0.8pp | 5.9pp |
| 2400 | 291 | **+1.4pp** | 5.5pp |

Median shift: **+1.3pp** across 1600 ELO points — the smallest of all five metrics. SD narrows from 7.8pp to 5.5pp.

**Cohen's d (800 vs 2400) = 0.30 → REVIEW.** Small rating effect, well within Tier-1 territory.

### Verdict

✅ **Strongest Section-2 percentile candidate.** Comparable rating-invariance to Endgame Score Gap. The parity bucket has no sigmoid-bias contamination and no opponent confound (you're at equal material vs an equally-rated opponent — the most level playing field on the page).

---

## 5. Recovery Score Gap (Section 2 ΔES, recov bucket)

### Pooled distribution

| n | mean | sd | p05 | p25 | p50 | p75 | p95 | skew | excess kurt |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1977 | +6.4pp | 8.0pp | −4.7pp | +0.8pp | **+5.6pp** | +11.0pp | +20.6pp | **+0.83** | +1.44 |

**Distribution shape: meaningfully right-skewed, heavy-tailed.** Mirror image of Conversion (sigmoid bias inverted: `ES_entry ≈ 0.4`, floor at 0.0 limits downside).

### Per-bucket medians and SDs

| ELO bucket | n | median | sd |
|---:|---:|---:|---:|
| 800 | 329 | **+9.4pp** | 8.8pp |
| 1200 | 470 | +6.7pp | 7.8pp |
| 1600 | 493 | +3.5pp | 7.2pp |
| 2000 | 412 | +3.2pp | 7.5pp |
| 2400 | 273 | **+4.0pp** | 6.1pp |

Median shift: **−5.4pp** across 1600 ELO points (notably non-monotonic: 1600 / 2000 / 2400 are all close, the drop is concentrated below 1600).

**Cohen's d (800 vs 2400) = 0.95 → KEEP SEPARATE (large effect, inverted sign vs Conversion).**

### Why this happens

Two compounding forces, opposite direction to Conversion:
1. **Sigmoid floor**: with `ES_entry ≈ 0.4` the realized score can rise to 1.0 but only fall to 0.0, so the gap distribution skews positive for everyone.
2. **Opponent confound.** The whole premise of the recovery bucket is that the opponent gave you a swing. At 800, opponents blunder enormously and gift swings constantly — the user's apparent "recovery skill" is mostly their opponents' error rate. At 2400, opponents don't blunder, so even when the user gets a recovery situation it's against tougher competition and the realized score is closer to the engine prediction.

This is the same finding that knocked Recovery out of the retracted Phase 87.3 Endgame Skill composite.

### Verdict

❌ **Drop.** Heavy inverted rating-proxy + opponent confound. A percentile chip would tell weak players they're "top X% at recovery" because their opponents helped them, and tell strong players they're "bottom X%" because their opponents didn't. The signal is the *opposite* of what users would read into the chip.

---

## Implications for SEED-019 tier classification

### Recommended revision

| Metric | Original seed | Refined (Socratic, pre-data) | **Final (empirical)** |
|---|---|---|---|
| Endgame Score Gap | Tier 1 | Demote (self-relative noise) | **Tier 1 — keep** ← data overrides critique |
| Achievable Score Gap | Tier 1 | Tier 1 | **Tier 1 — keep** |
| Parity Score Gap | Tier 1 | TBD | **Tier 1 — keep** (cleanest Section-2 candidate) |
| Conversion Score Gap | Tier 1 | Tier 1 | **Demote to Tier 2 or drop chip** (d=1.37) |
| Recovery Score Gap | Tier 1 gated | Drop | **Drop** (d=0.95, opponent-confounded — confirmed empirically) |

### Net change

- The data **rehabilitates Endgame Score Gap** — my Socratic critique was conceptually consistent but empirically wrong. The distribution is the cleanest of all five.
- The data **vindicates the Recovery concern** decisively — drop.
- The data **shifts Conversion out of Tier 1** — a result the original seed didn't anticipate. Conversion has been treated as the "marquee bragging number" but its rating coupling (d=1.37) makes it a poor percentile candidate. Either demote to Tier 2 alongside the raw Conversion %, or skip the percentile chip on this row.
- **Parity emerges as the strongest Section-2 candidate** — same-quality data, smallest rating effect.

### Final Tier-1 chip set (4 metrics)

| Card / row | Metric | Cohen's d (ELO) |
|---|---|---:|
| `EndgameOverallScoreGapRow.tsx` | Endgame Score Gap | 0.19 |
| `EndgameOverallScoreGapRow.tsx` | Achievable Score Gap | 0.32 |
| `EndgameMetricCard.tsx` (Parity) | Parity Score Gap | 0.30 |
| `EndgameMetricCard.tsx` (Conversion) | Conversion Score Gap | **1.37 (rejected)** |
| `EndgameMetricCard.tsx` (Recovery) | Recovery Score Gap | **0.95 (rejected)** |

This leaves 3 in-scope ΔES chips. If Tier-2 raw rates also ship, they would add Conversion %, Parity %, Recovery % as separate chips with "rating proxy" honesty labeling.

### Caveats

1. **Cohen's d on per-user means understates the within-rating variance available to the percentile.** Even at d=1.37, a 1200 player meaningfully outperforming their cohort's median Conversion Gap is still informative — the chip wouldn't be useless, just heavily ELO-correlated.
2. **The Phase 93 CDF could be stratified by rating bucket** as a future option (e.g. `top X% within your rating tier`) — but the seed explicitly chose global-only, and switching pools is a product decision, not a calibration one.
3. **Skew/kurtosis above ~|0.5| / ~|1.0|** raises a real concern that percentile rounding (e.g. "top 5%") obscures the tail asymmetry. For Conv and Recov this would be visible to users only in the extremes. Mitigation: if those metrics ship, render percentile only when |percentile − 50| ≥ some threshold to avoid the wide squashed-middle band.

---

## Time Pressure metric family (Phase 94.3)

Empirical input for SEED-025 / Phase 94.3 per-TC percentile chips. The Phase 94.2 candidacy report shape (one row per metric, pooled across all TCs) does not generalise to Time Pressure — Net Flag Rate at bullet likely tracks rating much harder than at classical, so the per-chip 4th tooltip bullet (rating-correlation framing) needs a per-cell calibration before Plan F can populate `RATING_NOTE_BY_FLAVOR` in `PercentileChip.tsx`. This section measures one Cohen's d per `(metric_family × tc)` cell so the per-chip copy is data-anchored, not invented.

- **DB**: benchmark (Docker `flawchess-benchmark-db-1` on port 5433).
- **Cohort**: full ingest (100 users/cell × 5 ELO × 4 TC; sparse `(2400, classical)` cell n=12 excluded from the cohort selection step). Per-cell **n_users** below counts deduped users (by lichess_username) passing the metric's inclusion floor in at least one ELO bucket within the per-TC pool.
- **Filters**: canonical CTE with `bic.status='completed'`; equal-footing opponent filter (`|opp_rating − user_rating| ≤ 100`); ELO bucketed by the cohort user's **rating at game time**; sub-800 rows dropped. The per-TC restriction `g.time_control_bucket::text = '{tc}'` is added to the inner `recent_games` filter; `recent_capped` keeps the most-recent 1000 games per user inside the restricted set; 36-month recency carries verbatim.
- **Per-user floors**: ≥30 user-pressured AND ≥30 opponent-pressured endgame-entry games for `time_pressure_score_gap_{tc}` (where "pressured" means `clock_pct < 0.40` of `games.base_time_seconds`); ≥30 endgame-entry games for `clock_gap_{tc}` and `net_flag_rate_{tc}`. The pressure cutoff value (0.40) and the inclusion floor (30) are inherited from SEED-025 / Phase 94.3 RESEARCH §Pitfall 5 verbatim.
- **Cohen's d** is `(mean(2400) − mean(800)) / pooled_sd` with `pooled_sd = sqrt(((n1−1)·s1² + (n2−1)·s2²) / (n1+n2−2))`; per the existing report's ladder, `d ≤ 0.20 → rating-invariant`, `≤ 0.35 → mild coupling`, `≤ 0.60 → moderate coupling`, `> 0.60 → heavy rating-proxy` (used verbatim — no new tier labels).
- **Source-of-truth note on clock data**: `game_positions.clock_seconds` is a single column per (game, ply), not user/opp split. User vs opponent clock at endgame entry is derived from `user_color` and ply parity: white = even plies, black = odd plies. The first endgame-entry clock for each side is the first non-NULL `clock_seconds` matching that parity, taken from a `game_positions` row stream restricted to `endgame_class IS NOT NULL` (`HAVING count(*) >= 6` per the standard endgame-entry rule). Termination value for time forfeits is `games.termination = 'timeout'` (Postgres ENUM); the user-side outcome on a timeout is derived from `games.result` and `games.user_color` exactly as `_iterate_clock_rows` does in `app/services/endgame_service.py`. Mirroring the production aggregator avoids classifier drift between this report and the runtime per-card `net_timeout_rate`.

### 12-cell tier table

| metric × TC | n_users | n_obs (pooled) | pooled median | pooled skew | 800 median | 2400 median | Cohen's d (800↔2400) | Tier | Tooltip 4th-bullet copy |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| `time_pressure_score_gap_bullet` | 470 | 574 | +0.25pp | +0.28 | −2.86pp | +4.78pp | **+0.52** | moderate coupling | This bullet score-gap partly tracks rating, so stronger players tend to absorb time pressure better; positive = you score higher under pressure than your opponents do. |
| `time_pressure_score_gap_blitz` | 425 | 492 | +2.60pp | +0.14 | −1.71pp | +4.76pp | **+0.40** | moderate coupling | This blitz score-gap partly tracks rating, so stronger players tend to score higher under pressure; positive = you outperform your opponents when the clock burns. |
| `time_pressure_score_gap_rapid` | 222 | 244 | −0.46pp | +0.46 | −11.51pp | +1.52pp | **+0.73** | heavy rating-proxy | This rapid score-gap tracks rating strongly: stronger players score much higher under pressure; positive = you outperform your opponents when the clock burns. |
| `time_pressure_score_gap_classical` | 19 | 20 | −5.96pp | −0.93 | — | — | — | n/a — insufficient cohort | This classical score-gap is not measured against enough players to characterise; positive = you outperform your opponents when the clock burns. *(n_users < 150 — chip suppression candidate (RESEARCH §Pitfall 8))* |
| `clock_gap_bullet` | 492 | 651 | −0.52pp | +0.25 | −0.30pp | −0.06pp | **−0.18** | rating-invariant | This bullet clock-management gap is mostly independent of rating; positive = you reach endgames with more clock left than your opponents do. |
| `clock_gap_blitz` | 489 | 640 | −0.38pp | −0.09 | −0.51pp | −0.16pp | **+0.29** | mild coupling | This blitz clock-management gap slightly tracks rating; positive = you reach endgames with more clock left than your opponents do. |
| `clock_gap_rapid` | 470 | 617 | −0.66pp | −0.35 | −0.08pp | −3.49pp | **−0.08** | rating-invariant | This rapid clock-management gap is mostly independent of rating; positive = you reach endgames with more clock left than your opponents do. |
| `clock_gap_classical` | 192 | 222 | −2.14pp | −0.49 | +1.04pp | — | **−0.12** (800↔2000) | rating-invariant | This classical clock-management gap is mostly independent of rating; positive = you reach endgames with more clock left than your opponents do. |
| `net_flag_rate_bullet` | 492 | 651 | +0.48pp | +0.00 | −3.23pp | +5.49pp | **+0.32** | mild coupling | At bullet, net flag rate slightly tracks rating in the opposite of the intuitive direction (stronger players win more on time than they lose); positive = your opponents flag more than you do. |
| `net_flag_rate_blitz` | 489 | 640 | +1.93pp | −0.83 | +0.24pp | +1.20pp | **+0.30** | mild coupling | At blitz, net flag rate slightly tracks rating; positive = your opponents flag more than you do. |
| `net_flag_rate_rapid` | 470 | 617 | +1.72pp | −3.04 | +1.22pp | +2.50pp | **+0.26** | mild coupling | At rapid, net flag rate slightly tracks rating; positive = your opponents flag more than you do. |
| `net_flag_rate_classical` | 192 | 222 | +0.00pp | −4.78 | +0.00pp | — | **+0.24** (800↔2000) | mild coupling | At classical, net flag rate slightly tracks rating; positive = your opponents flag more than you do. |

### Per-cell notes (only cells whose tier needs justification)

**`time_pressure_score_gap_bullet` (d = +0.52, on the moderate / heavy boundary).** d sits at 0.52 — clearly inside the moderate band (≤ 0.60) but on the high side. The per-bucket medians walk monotonically across ELO (800 → −2.86pp; 1200 → −0.85pp; 1600 → +0.36pp; 2000 → +1.92pp; 2400 → +4.78pp; per-bucket detail in the JSON dump `/tmp/p943/cells.json`), so the coupling is genuine. Cohort is plentiful (n_users=470) and pooled skew is near zero, so the chip is honest within its band — Plan F's copy must disclose the rating-correlation accordingly.

**`time_pressure_score_gap_rapid` (d = +0.73, heavy rating-proxy).** 800 median is −11.51pp vs 2400 +1.52pp — a 13pp shift across ELO is more than the typical within-bucket IQR. Stronger players who play rapid almost certainly play faster TCs too and bring superior time-management transfer; below 1200 the metric reads as "you lose decisively under pressure" almost regardless of skill within that bucket. Chip ships, but Plan F should treat the rating-correlation note as the headline disclosure.

**`time_pressure_score_gap_classical` (n_users = 19, d unmeasurable).** Cohort floor for the per-pressure-cell ≥30 / ≥30 dual gate is rarely met in classical — most classical games are not played under sustained sub-40% clock pressure for both sides over an endgame-entry-sized sample. Flagged for Plan F to apply chip-suppression escape hatch per RESEARCH §Pitfall 8 (n_users < 150). The pooled median is informative directionally but not for percentile chipping.

**Classical clock_gap & net_flag_rate (d via 800↔2000 fallback).** Both cells have n_users = 192 (well above the 150 suppression threshold) and clear per-bucket distributions for buckets 800 / 1200 / 1600 / 2000, but the (2400, classical) cohort cell is structurally pool-exhausted at the 2026-03 dump (only 12 selected users, none clearing the 30-game equal-footing floor at game-time ≥ 2400). The published d uses the 800↔2000 anchor as a substitute; both fallback d values land cleanly inside `rating-invariant` (clock_gap: |d| = 0.12) and `mild coupling` (net_flag_rate: d = +0.24) — well clear of any tier boundary, so the substitution does not change the tier assignment. Chips ship; Plan F's tooltip copy uses the tier label verbatim.

### Implications for Plan F (`RATING_NOTE_BY_FLAVOR`)

| Flavor | Direction | Tier copy lifts to |
|---|---|---|
| `time_pressure_score_gap_{bullet, blitz}` | higher_is_better | moderate-coupling line |
| `time_pressure_score_gap_rapid` | higher_is_better | heavy-rating-proxy line |
| `time_pressure_score_gap_classical` | higher_is_better | **chip suppressed — no copy needed** |
| `clock_gap_{bullet, rapid, classical}` | higher_is_better | rating-invariant line |
| `clock_gap_blitz` | higher_is_better | mild-coupling line |
| `net_flag_rate_{bullet, blitz, rapid, classical}` | lower_is_better | mild-coupling line (D-3 "Lower is better" prepend per RESEARCH §Pattern 7) |

Net Flag Rate at all four TCs lands at `+0.26 ≤ d ≤ +0.32` — mild but consistent coupling in the *helpful* direction (stronger players win more on time than they lose). Plan F's per-chip copy should not invent a "weak players flag less" framing for any TC.

---

## SQL provenance

All queries derive per-user values per `(user_id, game-time elo_bucket, tc_bucket)` using the canonical /benchmarks CTE (lichess_username join, `bic.status='completed'`, sparse-cell exclusion, equal-footing filter, sub-800 dropped). Section 2 ΔES uses the §3.2.2 spans + `LEAD()` pattern; Endgame Score Gap uses the §3.1.6 per_user pattern; Achievable Score Gap uses the §3.1.5 paired-diff pattern. Skew and excess kurtosis computed from the standardized third / fourth central moments (Fisher–Pearson, biased estimator).

The Phase 94.3 Time Pressure addendum reuses the same canonical-slice CTE with one additional predicate `AND g.time_control_bucket::text = '{tc}'` on the inner `recent_games` filter (no other change to selected_users / recent_capped / equal-footing). Per-user metric values: `clock_gap = avg((user_clock − opp_clock) / base_time_seconds)` at endgame entry (entry clocks extracted via ply parity over `game_positions` rows with `endgame_class IS NOT NULL`, `HAVING count(*) >= 6`); `net_flag_rate = (count(timeout & user_won) − count(timeout & user_lost)) / count(*)` over the same endgame-entry pool with the same denominator as the production `net_timeout_rate`; `time_pressure_score_gap = avg(user_score | user_clock_pct < 0.40) − avg(1 − user_score | opp_clock_pct < 0.40)`. The Phase 94.3 cell-by-cell numbers are reproducible by running `python3 /tmp/p943/run_cells.py` against the benchmark DB (the script was kept ad-hoc per the planning brief and is not committed to `scripts/` — Plan B will move the equivalent SQL into `app/services/canonical_slice_sql.py` as the three new builder families).

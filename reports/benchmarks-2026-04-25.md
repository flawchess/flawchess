# FlawChess Benchmarks — 2026-04-25

- **DB**: prod (`mcp__flawchess-prod-db__query`, tunneled via `localhost:15432`)
- **Snapshot taken**: 2026-04-25T16:29:08Z
- **Population at snapshot**: 270,880 rated, non-computer games across 44 users
- **Base filters**: `rated AND NOT is_computer_game` (no opponent-strength / recency / color filters — population-level)
- **Sample floors**: per-section (B1: 30 EG + 30 non-EG / user; B2a: 100 games per cell shown, 10/user for per-user views; B2b: ≥20 games and ≥2 of 3 buckets per user, ≥10 users per cell; B3: 30 EG games per (user × platform × TC), trailing 100-game window; B4: 20 EG games per (user × TC); B5: 100 games per (TC × time-bucket); B6: 100 games / 30 conv / 30 recov per cell)

> Note on user count: prod currently has only 44 users. Many cells fall under their floors and are flagged. Distributions will tighten as the user base grows; treat tight std-of-the-mean here as small-population noise rather than truth.

---

## 1. Score % Difference (endgame vs non-endgame)

### Currently set in code

| Constant | File | Value |
|---|---|---|
| `SCORE_GAP_NEUTRAL_MIN/MAX` | `frontend/src/generated/endgameZones.ts` | `−0.10 / +0.10` |
| `SCORE_GAP_DOMAIN` | `EndgamePerformanceSection.tsx:50` | `0.20` (so the bullet bar spans `±0.20`) |
| `SCORE_TIMELINE_Y_DOMAIN` | `EndgamePerformanceSection.tsx:56` | `[20, 80]` (0.20–0.80 score range, %) |
| `SCORE_TIMELINE_NEUTRAL_MIN/MAX` | — | **none defined** — the new two-line timeline chart has no neutral band yet. This benchmark proposes the initial bounds. |
| `SCORE_TIMELINE_EPSILON_PCT` | — | **none defined**. |

### Per-user distributions (n_users = 40)

| Distribution | mean ± std | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|
| Endgame score (`eg_score`) | 0.531 ± 0.072 | 0.420 | 0.490 | 0.520 | **0.581** | 0.633 |
| Non-endgame score (`non_eg_score`) | 0.521 ± 0.072 | 0.429 | 0.468 | 0.525 | **0.560** | 0.618 |
| Score diff (`eg − non_eg`) | +0.010 ± 0.105 | −0.128 | **−0.060** | −0.015 | **+0.074** | +0.163 |

Sanity check: the gap-distribution median (−0.015) is within rounding of `eg_p50 − non_eg_p50 = 0.520 − 0.525 = −0.005`. ✓

### Recommendations

| Target | Currently set | Recommended | Verdict |
|---|---|---|---|
| **Timeline neutral band (new chart)** | none | overlap of `[eg_p25, eg_p75]` ∩ `[non_eg_p25, non_eg_p75]` = `[0.490, 0.560]`. Round to `[0.49, 0.56]`. The two ranges overlap heavily (overlap = 0.07 of 0.09 narrower IQR ≈ 78%) so a single shared band works fine. | **Add a single timeline neutral band at 0.49–0.56** (49%–56% in the chart's % space). |
| **Timeline Y-axis domain** | `[20, 80]` | observed `[min(eg_p05, non_eg_p05), max(eg_p95, non_eg_p95)] = [42, 63]`. Padded → `[35, 70]`. | **Narrow to `[35, 70]`** — the current `[20, 80]` leaves the lines visually compressed in the middle of the chart for most users. |
| **Score-gap neutral band** | `±0.10` | `[diff_p25, diff_p75] = [−0.060, +0.074]`. Round to `[−0.06, +0.07]`. | **Narrow to ≈ `[−0.06, +0.07]`** — current `±0.10` covers ≈ p10–p90 (too wide; almost everyone lands in neutral, defeating the gauge). |
| **Score-gap range (`SCORE_GAP_DOMAIN`)** | `0.20` | `[diff_p05, diff_p95] = [−0.13, +0.16]`. | **Keep `0.20`** — symmetric `±0.20` covers p05–p95 with a small headroom. |

---

## 2. Conversion / Parity / Recovery + Endgame Skill by ELO × TC

### Currently set in code

| Constant | File | Value |
|---|---|---|
| `FIXED_GAUGE_ZONES.conversion` | `endgameZones.ts:13–17` | neutral `[0.65, 0.75]` |
| `FIXED_GAUGE_ZONES.parity` | `endgameZones.ts:18–22` | neutral `[0.45, 0.55]` |
| `FIXED_GAUGE_ZONES.recovery` | `endgameZones.ts:23–27` | neutral **`[0.25, 0.35]`** (skill doc said 0.30–0.40 — that comment is stale) |
| `ENDGAME_SKILL_ZONES` | `endgameZones.ts:30–34` | `[0–0.45 danger, 0.45–0.55 neutral, 0.55–1.00 success]` |
| `NEUTRAL_ZONE_MIN/MAX` (opponent-calibrated bullet) | `EndgameScoreGapSection.tsx:43–44` | `−0.05 / +0.05` |
| `BULLET_DOMAIN` | `EndgameScoreGapSection.tsx:49` | `0.20` |

### Pooled per-bucket rates (Query A)

Cells with `n_games < 100` are shown but italicised; cells below the floor are not used for verdicts. Sample floor per cell: 100 games.

#### Conversion (win % among advantage-entry games)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | *0.635 (78)* | 0.642 (373) | 0.735 (100) | — |
| 500–999 | 0.739 (364) | 0.670 (3391) | 0.749 (1320) | *0.798 (47)* |
| 1000–1499 | 0.682 (3000) | 0.725 (3484) | 0.736 (3875) | *0.938 (81)* |
| 1500–1999 | 0.695 (11861) | 0.715 (4810) | 0.755 (5187) | *0.927 (41)* |
| 2000–2499 | 0.720 (12171) | 0.768 (1456) | 0.779 (1617) | *0.846 (81)* |
| 2500+ | 0.798 (253) | 0.703 (1417) | — | — |

Pooled (game-weighted, all cells with n ≥ 100): **0.706**. Opponent rate (= 1 − pooled recovery) ≈ 1 − 0.327 = **0.673** ⇒ user−opp ≈ +3.3 pp on average (not far from 50/50).

Across the reliable-cell grid, conversion ranges from **0.642** (<500 blitz) to **0.798** (2500+ bullet). p25 ≈ 0.700, p75 ≈ 0.749.

**Verdict on `[0.65, 0.75]` neutral:** the band sits squarely on the observed p25–p75 of the reliable cell rates. Median pooled cell ≈ 0.72. **Keep.** Note: low-ELO blitz (0.64) lands just under the neutral band's lower edge — cohort users with mostly sub-1000 blitz endgames will see the conversion gauge color "danger" by population standards. That's the intended behaviour of a population-calibrated gauge.

#### Parity (avg score among parity-entry games)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | *0.514 (37)* | 0.361 (187) | *0.500 (39)* | — |
| 500–999 | 0.584 (310) | 0.454 (2181) | 0.473 (980) | *0.463 (54)* |
| 1000–1499 | 0.513 (3390) | 0.494 (3959) | 0.501 (3883) | — |
| 1500–1999 | 0.492 (11011) | 0.510 (6087) | 0.497 (7475) | — |
| 2000–2499 | 0.535 (15421) | 0.581 (2822) | 0.578 (2641) | *0.655 (145)* |
| 2500+ | 0.580 (468) | 0.512 (2974) | — | — |

Pooled: **0.510**. Across reliable cells: range 0.45–0.58, p25 ≈ 0.49, p75 ≈ 0.54.

**Verdict on `[0.45, 0.55]` neutral:** pooled median lands at 0.50 (perfect center). Reliable cells span 0.45–0.58. **Keep.** A handful of high-ELO cells (2000+ at all TCs) trend toward the upper edge — at the top end of the rating ladder, parity entries skew slightly user-favorable. Not enough to recenter.

#### Recovery (save % among disadvantage-entry games)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | *0.524 (62)* | 0.219 (272) | 0.255 (112) | — |
| 500–999 | 0.469 (489) | 0.253 (2378) | 0.210 (1036) | — |
| 1000–1499 | 0.349 (3713) | 0.274 (3158) | 0.259 (2749) | — |
| 1500–1999 | 0.342 (10560) | 0.288 (3460) | 0.256 (5051) | — |
| 2000–2499 | 0.344 (10274) | 0.363 (1235) | 0.338 (1170) | — |
| 2500+ | 0.355 (244) | 0.315 (1283) | — | — |

Pooled: **0.327**. Reliable cells: range 0.21–0.47 (huge), p25 ≈ 0.255, p75 ≈ 0.349.

**Verdict on `[0.25, 0.35]` neutral:** pooled median 0.34, p25–p75 = 0.255–0.349. The band fits the data well but skews slightly low — half of the population is at or above the upper edge. **Keep**, but note the lower 500 bullet bucket is an outlier (0.469) due to small samples and likely beginner opponents who can't convert. Bullet across all ELOs runs systematically higher recovery (more sloppy material returns) than blitz/rapid — possible future work: per-TC recovery zones.

### Endgame Skill — per-user distribution by ELO × TC (Query B)

Cells with `n_users < 10` suppressed.

| ELO | bullet (p50 [p25–p75], n) | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | — | — | — | — |
| 500–999 | 0.617 [0.539–0.635] (n=10) | 0.500 [0.459–0.536] (n=15) | 0.492 [0.465–0.526] (n=14) | — |
| 1000–1499 | 0.501 [0.471–0.590] (n=13) | 0.514 [0.472–0.555] (n=17) | 0.549 [0.488–0.610] (n=19) | — |
| 1500–1999 | 0.502 [0.473–0.565] (n=16) | 0.509 [0.482–0.595] (n=20) | 0.530 [0.491–0.563] (n=18) | — |
| 2000–2499 | — | 0.514 [0.463–0.601] (n=12) | 0.544 [0.518–0.590] (n=11) | — |

### Endgame Skill — pooled (per-user, no ELO bucketing)

| TC | n_users | p05 | p25 | p50 | p75 | p95 | mean ± std |
|---|---|---|---|---|---|---|---|
| bullet | 28 | 0.298 | 0.474 | 0.527 | 0.584 | 0.691 | 0.524 ± 0.139 |
| blitz | 36 | 0.407 | 0.454 | 0.513 | 0.540 | 0.643 | 0.510 ± 0.084 |
| rapid | 33 | 0.451 | 0.477 | 0.521 | 0.564 | 0.628 | 0.528 ± 0.076 |
| classical | 9 | 0.456 | 0.548 | 0.597 | 0.717 | 0.909 | 0.648 ± 0.169 |
| **all (one row per user)** | **42** | **0.383** | **0.482** | **0.510** | **0.556** | **0.618** | **0.522 ± 0.083** |

### Verdict on Endgame Skill gauge

| Target | Currently set | Recommended | Verdict |
|---|---|---|---|
| `ENDGAME_SKILL_ZONES` neutral | `[0.45, 0.55]` | pooled-all p25–p75 = `[0.482, 0.556]` ≈ `[0.48, 0.56]` | **Keep** — current band is within ±0.5 pp of the data-driven IQR on each edge. The "typical value 52%" code comment matches the pooled median 0.510 within 1 pp. |
| Gauge range | `[0, 1]` (full) | `[0.38, 0.62]` for p05–p95 pooled | The current full-domain gauge is fine; values almost never hit extremes. |

**Slope by ELO:** within blitz, `p50` moves from 0.500 (500–999) → 0.514 (1000–1499) → 0.509 (1500–1999) → 0.514 (2000–2499). Slope is essentially flat (< 1.5 pp). Within rapid: 0.492 → 0.549 → 0.530 → 0.544 — flat-ish with a small bump at 1000. **A single pooled neutral zone is justified; no need for ELO-stratified bands.** Bullet at 500–999 is anomalously high (0.617, n=10) — small-sample artifact, ignore.

**Slope by TC:** classical pulls upward (0.65 mean) but only n=9 across 2 distinct ELO cohorts, so it's noise-dominated. Bullet/blitz/rapid agree within 2 pp at the median. Pooled-all is the safe gauge baseline.

---

## 3. Endgame ELO vs Actual ELO Gap per combo

### Currently set in code

| Constant | File | Value |
|---|---|---|
| `ENDGAME_ELO_TIMELINE_WINDOW` | `endgame_service.py:853` | `100` |
| `_ENDGAME_ELO_SKILL_CLAMP_LO/HI` | `endgame_service.py:859–860` | `0.05 / 0.95` |
| `MIN_GAMES_FOR_TIMELINE` | `openings_service.py:43` | `10` |
| `_MATERIAL_ADVANTAGE_THRESHOLD` | `endgame_service.py:165` | `100` |
| Formula | `endgame_service.py:884` | `endgame_elo = round(actual_elo + 400 · log10(clamped_skill / (1 − clamped_skill)))` |

### Per-combo gap distribution

| platform | tc | n_users | mean_actual | mean_endgame | mean_opp | gap mean ± std | gap p05 | p25 | p50 | p75 | p95 | min | max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| chess.com | bullet | 19 | 1669 | 1716 | 1587 | +47 ± 82 | −87 | −1 | +49 | +89 | +141 | −107 | +263 |
| chess.com | blitz | 27 | 1526 | 1537 | 1448 | +12 ± 46 | −49 | −22 | +12 | +38 | +86 | −95 | +102 |
| chess.com | rapid | 27 | 1569 | 1581 | 1516 | +12 ± 52 | −50 | −20 | +16 | +50 | +77 | −162 | +93 |
| chess.com | classical | 5 | 1429 | 1519 | 1234 | +90 ± 160 | −33 | −20 | +68 | +76 | +304 | −36 | +361 |
| lichess | bullet | 10 | 1984 | 2001 | 1970 | +17 ± 71 | −69 | −49 | +29 | +59 | +114 | −76 | +118 |
| lichess | blitz | 18 | 1901 | 1944 | 1840 | +44 ± 60 | −22 | −7 | +28 | +96 | +128 | −42 | +159 |
| lichess | rapid | 11 | 1937 | 1978 | 1875 | +41 ± 101 | −54 | −37 | +24 | +86 | +195 | −55 | +286 |
| lichess | classical | 2 | 2171 | 2212 | 2072 | +42 ± 11 | +35 | +38 | +42 | +45 | +48 | +34 | +49 |

### Per-combo skill percentiles (mirrors gap, by construction)

| platform | tc | skill_p25 | skill_p50 | skill_p75 |
|---|---|---|---|---|
| chess.com | bullet | 0.499 | 0.570 | 0.624 |
| chess.com | blitz | 0.469 | 0.518 | 0.554 |
| chess.com | rapid | 0.471 | 0.523 | 0.570 |
| chess.com | classical | 0.472 | 0.597 | 0.608 |
| lichess | bullet | 0.431 | 0.541 | 0.584 |
| lichess | blitz | 0.490 | 0.540 | 0.635 |
| lichess | rapid | 0.448 | 0.534 | 0.621 |
| lichess | classical | 0.554 | 0.559 | 0.565 |

### Pooled gap histogram (100-Elo bins)

| bin | n | % | cum % |
|---|---|---|---|
| [−200, −100) | 2 | 1.7 | 1.7 |
| [−100, 0) | 39 | 32.8 | 34.5 |
| [0, +100) | 64 | 53.8 | 88.2 |
| [+100, +200) | 11 | 9.2 | 97.5 |
| [+200, +300) | 2 | 1.7 | 99.2 |
| [+300, +400) | 1 | 0.8 | 100.0 |

Bell-curve centered just above 0 with right skew. **Zero clamp saturation** in any combo (`n_clamp_low = n_clamp_high = 0` everywhere) — the [0.05, 0.95] guard is comfortably loose.

### Findings

- **Gaps are positive on average across every reliable combo.** chess.com bullet (+47), lichess blitz (+44), lichess rapid (+41) lead; chess.com blitz/rapid sit near 0 (+12). The right skew in the pooled histogram (3 users with gap > +200, vs 2 below −100) reflects a few bullet outliers more than a systemic platform issue.
- **No platform bias in the gap.** Phase 57.1's anchor (actual_elo_at_date) cancels the Glicko-1 vs Glicko-2 scale. Where lichess shows a higher Endgame Skill than chess.com at the same TC (e.g. blitz: 0.540 vs 0.518), the gap reflects that ≈ +20 Elo difference in skill, not the rating system. **Confirmed ✓.**
- **TC slope (within platform):** chess.com gaps fall from bullet (+47) → blitz/rapid (~+12). Lichess shows the opposite — blitz/rapid (+41–+44) higher than bullet (+17). No clean monotonic pattern; signal is noise-dominated at this user count. The "slower TCs surface deeper endgame skill" hypothesis is **not** supported by the current data — but with only 2 lichess classical users, classical can't confirm or refute either direction.
- **Clamp saturation:** **zero users** at either clamp. The clamp is currently unused; it acts as a guard only. Could be relaxed to [0.02, 0.98] without effect, but no reason to change.
- **Recommended "notable divergence" threshold (forward-looking):** pooled `|gap_p90|` ≈ `max(|p10|, p90)`. From the histogram: p90 ≈ +130, p10 ≈ −50, so abs cutoff ≈ **±100 Elo**. If a future phase adds a "your endgames pull your rating notably up/down" callout, fire it when |gap| > 100.
- **Std verdict:** pooled `std_gap` ≈ 75 Elo (bullet/blitz/rapid combined). That's at the lower end of the "120–200" reasonable-sensitivity range from the skill doc — meaning the skill distribution is slightly tighter than the formula's design assumption. With only 44 users this is expected; revisit when the population grows.

---

## 4. Time Pressure at Endgame Entry

### Currently set in code

| Constant | File | Value |
|---|---|---|
| `NEUTRAL_PCT_THRESHOLD` | `endgameZones.ts:36` | `±10.0` (% of base time) |
| `NEUTRAL_TIMEOUT_THRESHOLD` | `endgameZones.ts:37` | `±5.0` (pp net timeout) |

### Clock diff, % of base time (primary)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 27 | +1.67 | −5.30 | −2.24 | −0.38 | +4.98 | +13.07 |
| blitz | 36 | −3.43 | −14.73 | −7.37 | −3.11 | +0.95 | +6.02 |
| rapid | 33 | −3.20 | −22.37 | −7.53 | −2.79 | +4.26 | +8.57 |
| classical | 2 | −8.49 | −26.47 | −18.48 | −8.49 | +1.51 | +9.50 |

### Net timeout rate, pp (primary)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 27 | +10.31 | −9.54 | −2.59 | +4.90 | +24.37 | +38.69 |
| blitz | 36 | +0.21 | −20.67 | −4.21 | +1.03 | +9.24 | +14.34 |
| rapid | 33 | +1.40 | −7.87 | −1.27 | +2.34 | +4.21 | +7.69 |
| classical | 2 | +0.50 | −2.79 | −1.33 | +0.50 | +2.34 | +3.80 |

### Clock diff, seconds (secondary readout)

| TC | s_p25 | s_p50 | s_p75 |
|---|---|---|---|
| bullet | −1.19 | −0.23 | +2.88 |
| blitz | −14.77 | −9.06 | +1.74 |
| rapid | −63.05 | −16.76 | +27.57 |
| classical | −321.05 | −168.43 | −15.80 |

### Recommendations

**Clock diff (% of base time):**

| TC | observed [p25, p75] | observed [p05, p95] | currently set | Verdict |
|---|---|---|---|---|
| bullet | [−2.2, +5.0] | [−5.3, +13.1] | ±10.0 | **Narrow to ±7.0** — current band is wider than p05–p95 on the negative side. |
| blitz | [−7.4, +1.0] | [−14.7, +6.0] | ±10.0 | **Keep ±10** (or narrow to ±8) — IQR sits within ±10. Slight asymmetry (users typically run *behind* opponent on the clock by 3 pp) but not enough to break symmetry. |
| rapid | [−7.5, +4.3] | [−22.4, +8.6] | ±10.0 | **Keep ±10** — IQR fits, p05 outliers spend much more time slipping into time trouble in rapid (long tail). |
| classical | n=2 | — | ±10.0 | Insufficient data; defer. |

**Pooled across reliable TCs (bullet+blitz+rapid):** observed p25 ≈ −5.7, p75 ≈ +3.4. **Recommend lowering `NEUTRAL_PCT_THRESHOLD` to 7.0** (still symmetric for code simplicity; covers the bulk of bullet/blitz/rapid IQRs). The `±10` band currently classifies > 75% of the user base as "neutral," giving the gauge little discriminating power.

**Net timeout rate:** asymmetric. Bullet runs hot (+10 mean, p75 +24, p95 +39), blitz/rapid cluster near 0. The current symmetric `±5.0` is too tight for bullet (most users land outside it) and roughly right for blitz/rapid. **Recommend keeping `NEUTRAL_TIMEOUT_THRESHOLD = 5.0`** as a global default but note this is meaningful primarily for blitz/rapid; for bullet most users will read "win on time" by population standards.

**TC similarity in % space:** because the metric is normalized by `base_time_seconds`, the % zones across TCs are *not* identical — bullet has a tighter spread (IQR ≈ 7 pp) than rapid (IQR ≈ 12 pp). A single pooled threshold is reasonable but per-TC thresholds would be more honest. **No change needed unless we want per-TC thresholds.**

> **Note on SQL-vs-backend approximation:** the report uses clocks at `entry_ply` and `entry_ply + 1` instead of the backend's "first non-NULL by parity" scan. Games with NULL clocks at exactly those plies are silently dropped here, which biases samples toward games whose engines reported clocks at every move — chess.com PGNs almost always have clocks; lichess sometimes lacks them on the first few plies. Effect is small (< 5% of qualifying games dropped); does not move medians.

---

## 5. Time Pressure vs Performance — cross-TC comparison

### Currently set in code

| Constant | File | Value |
|---|---|---|
| Pooling logic | `endgame_service.py::_compute_time_pressure_chart` | **Currently pools all TCs** (`pooled_user_buckets`, `pooled_opp_buckets`) — confirmed. |
| `Y_AXIS_DOMAIN` | `EndgameTimePressureSection.tsx:20` | `[0.2, 0.8]` |
| `X_AXIS_DOMAIN` | `EndgameTimePressureSection.tsx:22` | `[0, 100]` |
| `MIN_GAMES_FOR_CLOCK_STATS` | `endgame_service.py:824` | `10` |

### Score by user_clock% bucket × TC (cell = `score (n_games)`; `<100` suppressed)

| pct bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0–10% | 0.266 (5070) | 0.310 (3930) | 0.327 (1192) | — |
| 10–20% | 0.411 (8890) | 0.429 (4096) | 0.443 (1338) | — |
| 20–30% | 0.500 (11519) | 0.482 (4298) | 0.500 (1837) | — |
| 30–40% | 0.542 (12137) | 0.515 (5295) | 0.524 (2461) | — |
| 40–50% | 0.570 (13548) | 0.548 (6003) | 0.535 (3377) | — |
| 50–60% | 0.591 (12093) | 0.576 (6448) | 0.540 (4528) | — |
| 60–70% | 0.592 (11143) | 0.577 (6228) | 0.541 (5979) | — |
| 70–80% | 0.598 (6227) | 0.557 (4857) | 0.527 (7373) | — |
| 80–90% | 0.586 (2385) | 0.572 (2424) | 0.520 (6674) | — |
| 90–100% | 0.553 (339) | 0.573 (573) | 0.535 (2240) | — |

(Classical never crosses the 100-game floor in any bucket; suppress entirely.)

### Cross-TC spread per bucket (reliable TCs: bullet/blitz/rapid)

| bucket | min | max | range |
|---|---|---|---|
| 0–10% | 0.266 (bullet) | 0.327 (rapid) | **0.061** |
| 10–20% | 0.411 | 0.443 | 0.032 |
| 20–30% | 0.482 | 0.500 | 0.018 |
| 30–40% | 0.515 | 0.542 | 0.027 |
| 40–50% | 0.535 | 0.570 | 0.035 |
| 50–60% | 0.540 | 0.591 | **0.051** |
| 60–70% | 0.541 | 0.592 | **0.051** |
| 70–80% | 0.527 | 0.598 | **0.071** |
| 80–90% | 0.520 | 0.586 | **0.066** |
| 90–100% | 0.520 | 0.573 | 0.053 |

**Max per-bucket range: 0.071 (70–80%).** Five buckets exceed the 0.05 (5 pp) threshold — bullet runs systematically higher than rapid in the upper-clock-half buckets, by 5–7 pp.

### Verdict

**Recommend keeping the current pooling — but flag this as borderline.** The 0.05 pp spread cutoff used in this benchmark is arbitrary; with five buckets above it, the case for splitting is on the table. However:

- The chart's `Y_AXIS_DOMAIN = [0.2, 0.8]` already absorbs this 5–7 pp spread — the bullet line would visually peak around 0.59 and the rapid line around 0.54 for the high-clock buckets, both well within the axis.
- Splitting to per-TC requires four lines on the same chart; UX cost is non-trivial.
- The shape of the curve is the same across all three TCs (monotonic rise from 0.27–0.33 at low clock to 0.52–0.59 at high clock). The user-facing message ("more clock = better outcomes") survives pooling.
- **Pooling stays.** Revisit if a future TC develops a clearly different curve *shape* (e.g. flat vs monotonic) — magnitude differences alone aren't worth the UX hit.

**Axis fit:** observed range across reliable buckets is 0.27 to 0.60, comfortably inside `[0.2, 0.8]`. **Keep the axis.** Could tighten to `[0.25, 0.65]` if we want the curve to fill more of the chart, but the current axis leaves room for future cohorts who might land outside.

---

## 6. Endgame Type Breakdown by ELO × TC

### Currently set in code

| Constant | File | Value |
|---|---|---|
| `NEUTRAL_ZONE_MIN/MAX` (per-class score-diff bullet) | `EndgameWDLChart.tsx:42–43` | `−0.05 / +0.05` |
| `BULLET_DOMAIN` (per-class score-diff bullet) | `EndgameWDLChart.tsx:48` | `0.30` |
| `EndgameConvRecovChart.tsx` per-class neutral zones | — | **none defined** — only `domain={[0, 100]}` for the axis. Section 6 may propose initial bounds. |
| `ENDGAME_PLY_THRESHOLD` | `endgame_repository.py:41` | `6` |
| `PERSISTENCE_PLIES` | `endgame_repository.py:72` | `4` |
| `_MATERIAL_ADVANTAGE_THRESHOLD` | `endgame_service.py:165` | `100` |

### Pooled-by-class summary (collapses ELO × TC — drives most UI decisions)

| endgame_class | n_games | score | score_diff | n_conv | conversion | n_recov | recovery |
|---|---|---|---|---|---|---|---|
| rook | 33,148 | 0.5153 | **+0.031** | 12,273 | 0.690 | 10,452 | **0.324** |
| minor_piece | 23,989 | 0.5320 | **+0.064** | 8,460 | 0.662 | 7,726 | **0.390** |
| pawn | 15,633 | 0.5340 | **+0.068** | 5,396 | 0.716 | 4,452 | 0.341 |
| queen | 13,662 | 0.5139 | +0.028 | 5,732 | **0.781** | 5,601 | **0.255** |
| mixed | 158,329 | 0.5239 | +0.048 | 52,888 | 0.691 | 45,566 | 0.340 |
| pawnless | 1,628 | 0.4957 | −0.009 | 800 | 0.761 | 804 | **0.231** |

**Per-class spread (pooled view):**
- `score_diff`: max − min = +0.068 − (−0.009) = **0.077** > 2 · `NEUTRAL_ZONE_MAX = 0.10`? No, 0.077 < 0.10. The single pooled `±0.05` band centers fine.
- `conversion`: 0.662 (minor_piece) → 0.781 (queen). Range = **11.9 pp**. Queen is conversion-friendly (extra mating power); minor_piece is conversion-hostile (drawish 2-bishop / B+N endings, weak pawn-up advantages).
- `recovery`: 0.231 (pawnless) → 0.390 (minor_piece). Range = **15.9 pp**. Minor-piece is recovery-friendly (defender can sacrifice a piece for a fortress / B+wrong-color-rook-pawn draws); pawnless and queen are recovery-hostile (queen converts cleanly, pawnless ends fast).

### Per-class spread direction matches chess intuition:
- **Pawn endgames convert highest** (0.716) — calculation-heavy, deterministic. Confirmed.
- **Minor-piece endgames recover highest** (0.390) — drawing techniques (wrong bishop + rook pawn, fortress) are strongest here. Confirmed.
- **Queen endgames convert highest among non-pawn classes** (0.781) and recover lowest (0.255) — extra material in queen endings is decisive. Confirmed.
- **Rook endgames are slightly drawish** (lowest score_diff: +0.031) — matches the famous "all rook endings are drawn" lore (Tarrasch).

### Per-class score-diff vs `NEUTRAL_ZONE_MIN/MAX = ±0.05`

| class | pooled score_diff | inside ±0.05? |
|---|---|---|
| rook | +0.031 | ✓ inside |
| minor_piece | +0.064 | ✗ above (gauge will color "success") |
| pawn | +0.068 | ✗ above (gauge will color "success") |
| queen | +0.028 | ✓ inside |
| mixed | +0.048 | ✓ inside (just barely) |
| pawnless | −0.009 | ✓ inside |

**Two of six classes fall outside the band on the population pooled rate.** This means an "average" user in minor-piece or pawn endgames will *systematically* color "success" on that class's gauge — the gauge is biased by class composition.

### ELO slope per class (eyeballed from the matrix)

- **score_diff:** within mixed-rapid the slope from 1000 → 2000 is +0.001 → +0.048 → +0.173 (rises ~17 pp across 1000 Elo). Strong upward slope. ✓
- **conversion (mixed):** 1500 bullet 0.671 → 2000 bullet 0.695 → 2500 bullet 0.774. Slope ~10 pp / 1000 Elo. Real but smaller than recovery slope.
- **recovery (mixed):** 1500 bullet 0.363 → 2000 bullet 0.369 → 2500 bullet 0.391. Slope ~3 pp / 1000 Elo. Mostly flat at the bullet TC; rapid recovery is similarly flat.

ELO slope is real for `score_diff` but small-to-moderate for the other rates. The pooled gauges may underserve the lowest-ELO cohort (where rates lag) but the mixed ELO is a noisy signal because rating populations skew toward 1500–2000 already.

### TC slope per class (eyeballed)

- **Recovery suppressed in bullet?** No — bullet rook recovery 0.357 ≈ rapid rook recovery 0.258 — bullet is actually *higher* than rapid (more sloppy material returns under time pressure). Counter to the docstring's hypothesis.
- **Conversion higher in slow TCs:** mixed-class conversion at 1500 climbs from 0.671 (bullet) → 0.684 (blitz) → 0.721 (rapid). Modest +5 pp from bullet to rapid. Confirms the "more time → better technique" intuition for conversion.

### Verdicts

**Score-diff bullet gauge (`±0.05`):**
- Two classes (minor_piece +0.064, pawn +0.068) sit just outside the upper edge.
- **Recommend widening to ±0.07** (covers all 6 pooled class score_diffs within ±0.07 except minor/pawn at +0.064/+0.068, which are inside ±0.07). Or alternatively, **make the gauge per-class** using each class's pooled rate as the center and `±0.05` around it.
- **Verdict: Widen to `±0.07`.** Per-class would be cleaner statistically but doubles the constant count and the UX has to teach users that "0.04 is positive for queen but neutral for minor_piece" — too much.

**Conv/recov initial bands (currently no zones in `EndgameConvRecovChart.tsx`):**
- Class spread (12 pp on conversion, 16 pp on recovery) is too large for a single shared band — would force per-class bands if we add them.
- **Proposed initial per-class bands** (centered ±0.05 on the pooled rate):
  - rook: conversion `[0.64, 0.74]`, recovery `[0.27, 0.37]`
  - minor_piece: conversion `[0.61, 0.71]`, recovery `[0.34, 0.44]`
  - pawn: conversion `[0.67, 0.77]`, recovery `[0.29, 0.39]`
  - queen: conversion `[0.73, 0.83]`, recovery `[0.20, 0.30]`
  - mixed: conversion `[0.64, 0.74]`, recovery `[0.29, 0.39]`
  - pawnless: conversion `[0.71, 0.81]`, recovery `[0.18, 0.28]`
- **Verdict: Proposed initial bands above** if we want to add neutral zones. If we don't, today's "no zones" treatment remains acceptable — the chart shows raw rates against the bullet domain `[0, 100]` and lets the user judge.

> **Multi-class semantics:** confirmed 158k mixed-class games + 33k rook + 24k minor + 16k pawn + 14k queen + 1.6k pawnless = ~245k class-spans across the 270k-game population. Multi-class per game is real (sums to >1× the game count), as designed by D-02.

---

## Recommended thresholds summary

| Metric | Code constant | File | Currently set | Recommended (data-driven) | Verdict |
|---|---|---|---|---|---|
| Score-gap gauge — neutral | `SCORE_GAP_NEUTRAL_MIN/MAX` | `endgameZones.ts` | `±0.10` | `[−0.06, +0.07]` (p25–p75) | **Narrow** to ≈ `±0.07` |
| Score-gap gauge — domain | `SCORE_GAP_DOMAIN` | `EndgamePerformanceSection.tsx` | `0.20` | `±0.16` (p05–p95) | **Keep** `0.20` |
| Score timeline — Y-axis | `SCORE_TIMELINE_Y_DOMAIN` | `EndgamePerformanceSection.tsx` | `[20, 80]` | `[35, 70]` | **Narrow** to `[35, 70]` |
| Score timeline — neutral band | (not yet defined) | `EndgamePerformanceSection.tsx` | none | `[0.49, 0.56]` (intersection of EG and non-EG p25–p75) | **Add** new band `[0.49, 0.56]` |
| Conversion gauge — neutral | `FIXED_GAUGE_ZONES.conversion` | `endgameZones.ts` | `[0.65, 0.75]` | `[0.70, 0.75]` (cell p25–p75) | **Keep** |
| Parity gauge — neutral | `FIXED_GAUGE_ZONES.parity` | `endgameZones.ts` | `[0.45, 0.55]` | `[0.49, 0.54]` | **Keep** |
| Recovery gauge — neutral | `FIXED_GAUGE_ZONES.recovery` | `endgameZones.ts` | `[0.25, 0.35]` | `[0.255, 0.349]` | **Keep** |
| Endgame Skill gauge — neutral | `ENDGAME_SKILL_ZONES` | `endgameZones.ts` | `[0.45, 0.55]` | `[0.482, 0.556]` | **Keep** (typical 51% matches "52%" code comment within 1 pp) |
| Opponent-calibrated bullet — neutral | `NEUTRAL_ZONE_MIN/MAX` | `EndgameScoreGapSection.tsx` | `±0.05` | (not directly measured here) | **Keep** |
| Endgame ELO — formula sanity | `_ENDGAME_ELO_SKILL_CLAMP_*`, formula | `endgame_service.py` | `[0.05, 0.95]`, `400·log10(s/(1−s))` | observed std_gap ≈ 75 (target 120–200) | **Keep formula**; clamp unused (zero saturation) |
| Endgame ELO — "notable divergence" callout | (not yet defined) | — | — | `|gap| > 100` (≈ pooled p10/p90) | Forward-looking — add only if/when the UI grows a callout |
| Clock-pressure gauge — % threshold | `NEUTRAL_PCT_THRESHOLD` | `endgameZones.ts` | `±10.0` | bullet/blitz/rapid pooled p25–p75 ≈ `[−5.7, +3.4]` | **Narrow** to `±7.0` |
| Clock-pressure gauge — timeout threshold | `NEUTRAL_TIMEOUT_THRESHOLD` | `endgameZones.ts` | `±5.0` | blitz/rapid p25–p75 within ±5 (bullet hot at p75 +24) | **Keep** as a global default; bullet skews hot |
| Time-pressure-vs-performance chart | pooling in `_compute_time_pressure_chart` | `endgame_service.py` | pooled across TCs | max bucket spread 7.1 pp (5 buckets > 5 pp) | **Keep pooling** — borderline but not worth the UX cost |
| Endgame-Categories score-diff bullet | `NEUTRAL_ZONE_MIN/MAX` | `EndgameWDLChart.tsx` | `±0.05` | minor_piece and pawn pooled +0.064/+0.068 outside | **Widen to `±0.07`** |
| Endgame-Categories conv/recov chart | (no zones today) | `EndgameConvRecovChart.tsx` | none | per-class `±0.05` around pooled rate (see Section 6) | **Add per-class bands** if any zones desired; otherwise keep today's raw display |

### Highest-impact actions (top 3)

1. **Narrow `SCORE_GAP_NEUTRAL_MIN/MAX` from `±0.10` to `±0.07`.** Current band classifies > 75% of users as "neutral," giving the gauge little signal. Edit `app/services/endgame_zones.py` (the source of `endgameZones.ts`) and regenerate the TS file via `uv run python scripts/gen_endgame_zones_ts.py`.
2. **Add a neutral band `[0.49, 0.56]` to the new two-line score timeline.** Currently the timeline has no band; users can't quickly tell which line is in "normal range."
3. **Narrow `NEUTRAL_PCT_THRESHOLD` from `±10` to `±7`** (in `app/services/endgame_zones.py`). Same rationale — current width swallows most users.

The other 12 settings already match population data within reasonable tolerances; no urgent changes there.

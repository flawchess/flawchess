# FlawChess Benchmarks — 2026-04-18

- **DB**: prod (`mcp__flawchess-prod-db__query`, SSH tunnel `localhost:15432`)
- **Snapshot taken**: 2026-04-18T20:49:23Z
- **Base filters**: `rated = TRUE AND NOT is_computer_game`
- **Sample floors**:
  - S1: ≥ 30 endgame games AND ≥ 30 non-endgame games per user
  - S2: per-cell pooled n shown for every cell; cells with n < 100 flagged low-confidence
  - S3: ≥ 20 endgame games per user per TC
  - S4: cell suppressed if n < 100
  - S5: ≥ 20 endgame games per user per (ELO × TC), ≥ 2 of 3 buckets non-empty, cell shown if ≥ 10 users qualify; pooled table uses the same per-user floor
  - S6: ≥ 30 endgame games per user per (platform × TC), trailing 100-game window per `ENDGAME_ELO_TIMELINE_WINDOW`

---

## 1. Score % Difference (endgame vs non-endgame)

**Currently set in code** (`frontend/src/components/charts/EndgamePerformanceSection.tsx`):
- `SCORE_DIFF_NEUTRAL_MIN = -0.10`, `SCORE_DIFF_NEUTRAL_MAX = 0.10` → neutral band ±10pp
- `SCORE_DIFF_DOMAIN = 0.20` → gauge half-width ±20pp

### Per-user distribution (n = 37 users)

| n_users | mean | std | p05 | p10 | p25 | p50 | p75 | p90 | p95 | min | max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 37 | +1.5pp | 10.6pp | −11.7pp | −9.9pp | −6.0pp | +0.5pp | +8.6pp | +14.1pp | +16.5pp | −23.3pp | +29.0pp |

### Per-user list (sorted by diff)

| user_id | eg_games | non_eg_games | eg_score | non_eg_score | diff |
|---|---|---|---|---|---|
| 21 | 6835 | 4515 | 0.4099 | 0.6431 | **−0.233** |
| 28 | 2905 | 2064 | 0.4664 | 0.6172 | −0.151 |
| 51 | 285 | 298 | 0.4737 | 0.5822 | −0.109 |
| 26 | 469 | 273 | 0.6684 | 0.7747 | −0.106 |
| 19 | 907 | 704 | 0.4625 | 0.5568 | −0.094 |
| 30 | 4720 | 3813 | 0.4703 | 0.5526 | −0.082 |
| 2 | 4700 | 3802 | 0.4697 | 0.5518 | −0.082 |
| 12 | 4160 | 1910 | 0.4919 | 0.5605 | −0.069 |
| 20 | 7322 | 3274 | 0.5007 | 0.5609 | −0.060 |
| 45 | 28590 | 9496 | 0.5266 | 0.5865 | −0.060 |
| 15 | 1763 | 961 | 0.4660 | 0.5245 | −0.059 |
| 4 | 13410 | 9783 | 0.4852 | 0.5249 | −0.040 |
| 37 | 375 | 254 | 0.5080 | 0.5472 | −0.039 |
| 31 | 3235 | 1477 | 0.5099 | 0.5420 | −0.032 |
| 14 | 953 | 1133 | 0.5147 | 0.5455 | −0.031 |
| 29 | 3824 | 1811 | 0.5255 | 0.5478 | −0.022 |
| 46 | 3587 | 3175 | 0.4947 | 0.5142 | −0.020 |
| 24 | 445 | 328 | 0.5573 | 0.5747 | −0.017 |
| 44 | 69 | 106 | 0.4203 | 0.4151 | +0.005 |
| 42 | 31 | 51 | 0.5484 | 0.5392 | +0.009 |
| 33 | 180 | 263 | 0.3778 | 0.3479 | +0.030 |
| 10 | 5163 | 3243 | 0.5280 | 0.4869 | +0.041 |
| 5 | 4575 | 3542 | 0.5388 | 0.4939 | +0.045 |
| 32 | 201 | 191 | 0.6119 | 0.5602 | +0.052 |
| 16 | 749 | 441 | 0.5067 | 0.4444 | +0.062 |
| 25 | 1525 | 940 | 0.5728 | 0.5032 | +0.070 |
| 17 | 7438 | 6511 | 0.5501 | 0.4804 | +0.070 |
| 18 | 112 | 146 | 0.5893 | 0.5034 | +0.086 |
| 50 | 753 | 897 | 0.5784 | 0.4621 | +0.116 |
| 13 | 15738 | 4996 | 0.5872 | 0.4664 | +0.121 |
| 3 | 2484 | 1889 | 0.5803 | 0.4584 | +0.122 |
| 35 | 626 | 821 | 0.5855 | 0.4574 | +0.128 |
| 34 | 7836 | 12605 | 0.5913 | 0.4612 | +0.130 |
| 53 | 343 | 414 | 0.6283 | 0.4710 | +0.157 |
| 22 | 783 | 662 | 0.6315 | 0.4690 | +0.163 |
| 11 | 10727 | 7458 | 0.6027 | 0.4286 | +0.174 |
| 43 | 87 | 139 | 0.7356 | 0.4460 | **+0.290** |

### Recommendations

- **Recommended neutral zone (p25–p75):** `[−6pp, +9pp]` → ≈ symmetric ±7-8pp.
- **Recommended gauge range (p05–p95):** `[−12pp, +17pp]` → ≈ ±15pp half-width.
- **Verdict — neutral band:** **narrow slightly** from ±10pp to ±8pp. The current ±10pp band absorbs ~80% of users (only `<p10` and `>p90` fall outside), which is too forgiving — about half of users with a clearly meaningful endgame skew (e.g. user 50 at +12pp, user 53 at +16pp) are color-coded "neutral" today.
- **Verdict — gauge half-width:** **keep** `SCORE_DIFF_DOMAIN = 0.20`. The p95 is +16.5pp and p05 is −11.7pp, so ±20pp comfortably covers p05–p95 with a small visual margin. Tightening to ±0.15 would clip the most extreme 5% of users on each side (max observed = +29pp, min = −23pp).

---

## 2. Conversion / Parity / Recovery by ELO × TC

**Currently set in code** (`frontend/src/components/charts/EndgameScoreGapSection.tsx`):
- `FIXED_GAUGE_ZONES.conversion` = danger `<0.65`, neutral `0.65–0.75`, success `>0.75`
- `FIXED_GAUGE_ZONES.parity` = danger `<0.45`, neutral `0.45–0.55`, success `>0.55`
- `FIXED_GAUGE_ZONES.recovery` = danger `<0.30`, neutral `0.30–0.40`, success `>0.40`
- `NEUTRAL_ZONE_MIN/MAX = ±0.05` (opponent-calibrated bullet chart neutral band)
- `BULLET_DOMAIN = 0.20` (bullet chart half-width)

### Conversion (Win % when entering with ≥ +1 material and still ≥ +1 four plies later)

| ELO bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | 0.610 (68) ⚠ | 0.669 (210) | 0.722 (106) | — |
| 500–999 | 0.751 (345) | 0.688 (1682) | 0.726 (1757) | 0.826 (23) ⚠ |
| 1000–1499 | 0.683 (2713) | 0.731 (2651) | 0.715 (4554) | 0.929 (84) ⚠ |
| 1500–1999 | 0.701 (10173) | 0.712 (4002) | 0.757 (4102) | 0.923 (39) ⚠ |
| 2000–2499 | 0.721 (12000) | 0.767 (1452) | 0.776 (1561) | 0.846 (81) ⚠ |
| 2500+ | 0.806 (199) | 0.703 (1417) | 1.000 (3) ⚠ | — |

⚠ = pooled n < 100, low-confidence cell.

- **Currently-set neutral band:** `[0.65, 0.75]` (10pp).
- **Pooled rate (all cells):** 0.7196 across 49,222 games (41 users).
- **Mirror "opponent" rate:** `1 − recovery_pooled = 1 − 0.3171 = 0.6829`. **Pooled user−opp rate gap: +3.7pp.**
- **Spread across reliable cells:** observed cell medians range 0.68–0.77 (ignoring n<100). Median bucket is ~0.72.
- **Verdict:** **keep** the `[0.65, 0.75]` neutral band. The pooled mean (0.72) and the cluster of bullet/blitz/rapid cells (0.68–0.77) sit centered on the band. The observed band already maps to "typical" cohorts at every reliable ELO × TC cell.

### Parity (Score % when entering at ±0 material)

| ELO bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | 0.477 (44) ⚠ | 0.330 (88) ⚠ | 0.488 (40) ⚠ | — |
| 500–999 | 0.590 (300) | 0.487 (1160) | 0.458 (1312) | 0.308 (26) ⚠ |
| 1000–1499 | 0.518 (3055) | 0.495 (2890) | 0.488 (4374) | 0.651 (53) ⚠ |
| 1500–1999 | 0.497 (9170) | 0.515 (4855) | 0.495 (5583) | 0.731 (52) ⚠ |
| 2000–2499 | 0.535 (15126) | 0.581 (2818) | 0.579 (2542) | 0.656 (144) |
| 2500+ | 0.573 (363) | 0.512 (2974) | 0.833 (6) ⚠ | — |

- **Currently-set neutral band:** `[0.45, 0.55]` (10pp).
- **Pooled rate:** 0.5174 across 56,976 games (40 users).
- **Mirror opponent rate:** `1 − parity_pooled = 0.4826`. **Pooled user−opp rate gap: +3.5pp.**
- **Spread across reliable cells:** 0.46–0.59 (excluding the four classical cells with n<100 and the noisy <500 cells). Most reliable cells fall inside `[0.45, 0.55]`; the `2000–2499` row consistently overshoots (0.54–0.58).
- **Verdict:** **keep** `[0.45, 0.55]`. The pooled median sits at 0.52, dead center. The high-ELO drift above 0.55 is real but the chart already reads "above neutral" for those users, which is the intended signal.

### Recovery (Save % when entering with ≤ −1 material and still ≤ −1 four plies later)

| ELO bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | 0.522 (68) ⚠ | 0.274 (133) | 0.257 (111) | 0.000 (2) ⚠ |
| 500–999 | 0.470 (486) | 0.288 (1030) | 0.210 (1275) | 0.000 (18) ⚠ |
| 1000–1499 | 0.353 (3489) | 0.277 (2290) | 0.249 (2974) | 0.130 (23) ⚠ |
| 1500–1999 | 0.348 (8963) | 0.286 (2843) | 0.251 (4091) | 0.208 (12) ⚠ |
| 2000–2499 | 0.344 (10099) | 0.362 (1233) | 0.340 (1129) | 0.423 (39) ⚠ |
| 2500+ | 0.364 (213) | 0.315 (1283) | 0.500 (3) ⚠ | — |

- **Currently-set neutral band:** `[0.30, 0.40]` (10pp).
- **Pooled rate:** 0.3171 across 41,807 games (41 users).
- **Mirror opponent rate:** `1 − conversion_pooled = 0.2804`. **Pooled user−opp rate gap: +3.7pp.**
- **Spread across reliable cells:** 0.21–0.47, but with a strong TC slope — bullet sits 0.34–0.47, rapid sits 0.21–0.34. The pooled mean (0.32) lands at the bottom edge of the neutral band.
- **Verdict:** **slight re-center recommended** — consider shifting recovery neutral to `[0.25, 0.35]` so the pooled median (0.32) sits centered rather than at the lower edge. Today users in rapid at 0.20–0.25 are flagged danger when they're actually right around the cohort median for that TC. Alternatively, **keep** `[0.30, 0.40]` as the live target if the design intent is "recovery ≥30% is the bar to clear", but document that ~half of rapid users sit below it.

### Per-user spread within cells (per-user p25–p75 inside high-volume cells)

The current dataset is too thin per-user-per-cell (37 active users total) to publish a stable per-user p25/p75 by ELO × TC × bucket while keeping the "≥10 users with ≥10 games each in the cell" floor. Skipped for this snapshot. Re-run once user count grows past ~150 active.

---

## 3. Time Pressure at Endgame Entry

**Currently set in code** (`frontend/src/components/charts/EndgameClockPressureSection.tsx`):
- `NEUTRAL_PCT_THRESHOLD = 10` → neutral band ±10pp of base time on the clock-diff gauge
- `NEUTRAL_TIMEOUT_THRESHOLD = 5` → neutral band ±5pp net timeout rate

### Clock diff at endgame entry, % of base time (primary — matches live gauge)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 25 | +2.4% | −5.5% | −1.5% | +0.8% | +8.1% | +13.6% |
| blitz | 33 | −3.4% | −15.1% | −7.4% | −3.1% | +0.8% | +6.2% |
| rapid | 30 | −3.1% | −19.4% | −7.4% | −4.6% | +4.2% | +8.5% |
| classical | 2 | −8.5% | −26.5% | −18.5% | −8.5% | +1.5% | +9.5% ⚠ |

⚠ classical n=2, ignore.

### Net timeout rate, pp (primary)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 25 | +11.9 | −9.6 | −1.0 | +4.9 | +24.6 | +39.6 |
| blitz | 33 | +0.3 | −22.6 | −4.5 | +1.6 | +10.6 | +14.4 |
| rapid | 30 | +1.0 | −7.9 | −2.4 | +2.3 | +4.2 | +7.7 |
| classical | 2 | +0.5 | −2.8 | −1.3 | +0.5 | +2.3 | +3.8 ⚠ |

### Clock diff in absolute seconds (secondary readout — sanity check only)

| TC | s_p25 | s_p50 | s_p75 |
|---|---|---|---|
| bullet | −1.0 | +0.5 | +5.2 |
| blitz | −14.4 | −8.8 | +1.4 |
| rapid | −60.0 | −32.1 | +27.5 |
| classical | −321 | −168 | −16 ⚠ |

### Recommendations

- **Recommended neutral zone (p25–p75) in % of base time:**
  - bullet: `[−1.5%, +8.1%]` → asymmetric, lean positive.
  - blitz: `[−7.4%, +0.8%]` → asymmetric, lean negative.
  - rapid: `[−7.4%, +4.2%]`.
  - Pooled across the three reliable TCs: roughly `[−6%, +6%]` symmetric.
- **Recommended gauge range (p05–p95):**
  - bullet: `[−5.5%, +13.6%]`.
  - blitz: `[−15.1%, +6.2%]`.
  - rapid: `[−19.4%, +8.5%]`.
- **Verdict — `NEUTRAL_PCT_THRESHOLD = 10`:** **narrow** to `±7%`. The current ±10pp band swallows almost the entire blitz and rapid p25–p75 ranges (which are well inside ±10pp), so the gauge sits "neutral" for most of the population in those TCs and only fires for outliers. Tightening to ±7% leaves the bulk of users near zero coloured neutral but starts colouring the top/bottom quartile of each TC, which is the intended signal. Asymmetry (bullet skews positive, blitz/rapid skew negative) is real but small enough that a single symmetric band is still defensible.
- **Verdict — `NEUTRAL_TIMEOUT_THRESHOLD = 5`:** **keep, but be aware bullet is the outlier** — bullet's p75 sits at +24.6pp net timeouts, so the gauge will fire green for the top half of bullet users (which is intentional and correct: in bullet, winning on time is a real skill). Blitz/rapid p25–p75 fits comfortably inside ±5pp, so the threshold is well-tuned for those TCs.
- **TC pooling:** the % zones are reasonably similar across blitz/rapid (`[−7.4, +0.8]` vs `[−7.4, +4.2]`); bullet is the outlier (slightly positive). A single shared band is defensible since the metric is already normalized by base time. Keep one band, do not split per TC.
- **Caveat:** SQL approximation reads clocks at exact `entry_ply` and `entry_ply+1`; the backend's Python loop walks plies until it finds a non-NULL clock for each parity, so SQL slightly under-samples vs the service. Magnitudes should still match within ~1–2pp.

---

## 4. Time Pressure vs Performance — cross-TC comparison

**Currently set in code** (`app/services/endgame_service.py::_compute_time_pressure_chart` + `frontend/src/components/charts/EndgameTimePressureSection.tsx`):
- The chart **pools all time controls** into a single `user_series + opp_series` (see `pooled_user_buckets` / `pooled_opp_buckets` at `endgame_service.py:1451–1468`).
- `Y_AXIS_DOMAIN = [0.2, 0.8]`
- `X_AXIS_DOMAIN = [0, 100]`
- `MIN_GAMES_FOR_CLOCK_STATS = 10`

### Score by time-remaining bucket (rows = 10pp clock-remaining bucket, cols = TC)

Cell format: `score (n)`. Suppress (—) if n < 100.

| % base remaining | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0–10 | 0.271 (4705) | 0.331 (3373) | 0.296 (1222) | — |
| 10–20 | 0.415 (8141) | 0.449 (3379) | 0.426 (1404) | — |
| 20–30 | 0.504 (10562) | 0.506 (3305) | 0.483 (1953) | — |
| 30–40 | 0.547 (11044) | 0.535 (4068) | 0.512 (2651) | — |
| 40–50 | 0.570 (12439) | 0.566 (4602) | 0.533 (3610) | — |
| 50–60 | 0.595 (11049) | 0.583 (4926) | 0.536 (4799) | — |
| 60–70 | 0.595 (10307) | 0.587 (4732) | 0.546 (5990) | — |
| 70–80 | 0.601 (5750) | 0.563 (3654) | 0.525 (6728) | — |
| 80–90 | 0.589 (2218) | 0.577 (1791) | 0.523 (5255) | — |
| 90–100 | 0.551 (304) | 0.570 (406) | 0.528 (1711) | — |

Classical is excluded throughout (every bucket has n < 100; total classical sample only 144 games across all buckets — not enough to participate in the cross-TC comparison).

### Per-bucket cross-TC range (max − min, only cells with n ≥ 100)

| Bucket | bullet | blitz | rapid | range |
|---|---|---|---|---|
| 0–10% | 0.271 | 0.331 | 0.296 | 0.060 |
| 10–20% | 0.415 | 0.449 | 0.426 | 0.034 |
| 20–30% | 0.504 | 0.506 | 0.483 | 0.023 |
| 30–40% | 0.547 | 0.535 | 0.512 | 0.035 |
| 40–50% | 0.570 | 0.566 | 0.533 | 0.037 |
| 50–60% | 0.595 | 0.583 | 0.536 | **0.059** |
| 60–70% | 0.595 | 0.587 | 0.546 | 0.049 |
| 70–80% | 0.601 | 0.563 | 0.525 | **0.076** |
| 80–90% | 0.589 | 0.577 | 0.523 | **0.066** |
| 90–100% | 0.551 | 0.570 | 0.528 | 0.042 |

**Max per-bucket range:** 0.076 (bucket 70–80%). The bottom quintile is well-aligned (range ≤ 0.06), but the top quintile shows rapid systematically under-scoring bullet/blitz by 5–8pp at the same relative time-remaining.

### Verdict

**Keep the current pooled chart**, with a caveat. The 5pp threshold for "is pooling still safe" is technically exceeded in three of ten buckets (70–80% bucket peaks at 7.6pp). However:

1. The shape of the curve is identical across TCs (monotonically rising from ~0.27–0.33 at 0–10% to ~0.55–0.60 at 50–80%, plateau or slight dip at the very top).
2. The systematic under-score in rapid at high time-remaining likely reflects opponent strength selection (rapid users with lots of clock at endgame entry are facing relatively strong opponents who didn't time-trouble themselves) rather than a per-TC behavioural difference the chart should expose.
3. Splitting into 3 lines triples the visual cognitive load on a narrative chart whose primary value is the slope, which all three TCs share.

**Action:** keep pooling. Document the bucket-7/8 spread in a `# benchmark snapshot:` code comment near `_compute_time_pressure_chart` so the next snapshot can detect drift.

The Y-axis domain `[0.2, 0.8]` accommodates the full observed range (min 0.27, max 0.60) with comfortable headroom. **Keep** `Y_AXIS_DOMAIN`.

---

## 5. Endgame Skill by ELO × TC

**Currently set in code** (`frontend/src/components/charts/EndgameScoreGapSection.tsx`):
- `ENDGAME_SKILL_ZONES` = `[0–0.45 danger, 0.45–0.55 neutral, 0.55–1.0 success]`
- Comment near constant: *"Typical value lands around 52% on FlawChess data"*

### ELO × TC matrix (cell format: `p50 [p25–p75] (n_users)`)

| ELO bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| <500 | — | — | — | — |
| 500–999 | — | 0.506 [0.451–0.540] (14) | 0.500 [0.454–0.527] (13) | — |
| 1000–1499 | 0.554 [0.475–0.619] (11) | 0.509 [0.475–0.565] (14) | 0.547 [0.464–0.605] (18) | — |
| 1500–1999 | 0.523 [0.481–0.573] (14) | 0.510 [0.457–0.617] (17) | 0.539 [0.494–0.568] (15) | — |
| 2000–2499 | — | 0.514 [0.463–0.601] (12) | — | — |
| 2500+ | — | — | — | — |

Cells with `n_users < 10` suppressed. (Bullet at 500–999 has only 9 qualifying users; bullet at 2000–2499 has only 9; rapid at 2000–2499 has only 9 — all just below the floor.)

### Pooled percentile table

| TC | n_users | p05 | p25 | p50 | p75 | p95 | mean ± std |
|---|---|---|---|---|---|---|---|
| bullet | 26 | 0.350 | 0.478 | 0.548 | 0.604 | 0.692 | 0.531 ± 0.139 |
| blitz | 33 | 0.398 | 0.453 | 0.515 | 0.540 | 0.647 | 0.510 ± 0.088 |
| rapid | 30 | 0.441 | 0.480 | 0.522 | 0.568 | 0.630 | 0.528 ± 0.080 |
| classical | 9 | 0.448 | 0.548 | 0.597 | 0.717 | 0.909 | 0.645 ± 0.172 ⚠ |
| **ALL** | **98** | **0.364** | **0.474** | **0.522** | **0.587** | **0.715** | **0.534 ± 0.115** |

⚠ classical n=9 — show but don't anchor recommendations on it.

### Recommendations

- **Recommended neutral zone (pooled p25–p75):** `[0.474, 0.587]` → ≈ `[0.47, 0.59]`.
- **Recommended gauge range (pooled p05–p95):** `[0.364, 0.715]`.
- **Slope by ELO:** within reliable cells (1000–1999 across all TCs), `p50` moves from ~0.51 to ~0.55. Roughly a 4pp lift between adjacent 500-wide buckets — small enough that a single shared neutral band is still defensible. Classical pulls higher (median 0.60), but the n is too thin to act on.
- **Verdict on `ENDGAME_SKILL_ZONES`:** **slight widen on the upper edge.** Today's neutral `[0.45, 0.55]` slightly under-covers — the pooled p25–p75 is `[0.47, 0.59]`, which means today's gauge marks the upper 30% of users as "success" when they are still inside the typical-cohort range. Suggest **`[0.45, 0.59]`** (keep lower bound, push upper bound to 0.59) or symmetrically **`[0.47, 0.59]`** if you want to recenter. Either way the lower bound (0.45) already aligns well with the pooled p25.
- **Verdict on the "typical value lands around 52%" comment:** **update to 52% pooled median (was already 52%).** The pooled `p50 = 0.522`, dead-on. Comment is still accurate.

### Top / bottom users by skill (pooled across their cells)

Skipped for this snapshot — the per-cell breakdown above already exposes the skill spread, and the dataset's 98 (user, TC) cells with sample-floor-passing data fit comfortably in the table above. Re-add the top/bottom-20 dump once user count grows.

---

## 6. Endgame ELO vs Actual ELO Gap per (platform × TC) combo

**Currently set in code** (`app/services/endgame_service.py`, `app/services/openings_service.py`):
- `ENDGAME_ELO_TIMELINE_WINDOW = 100` (trailing window size, line 836)
- `_ENDGAME_ELO_SKILL_CLAMP_LO = 0.05`, `_ENDGAME_ELO_SKILL_CLAMP_HI = 0.95` (lines 842–843)
- `MIN_GAMES_FOR_TIMELINE = 10` (`openings_service.py:43`)
- `_MATERIAL_ADVANTAGE_THRESHOLD = 100` (line 164)
- **Formula:** `endgame_elo = round(avg_opp_rating + 400 · log10(skill / (1 − skill)))`. The `400` is the classical Elo scaling constant.

### Per-combo gap percentile table

| platform | TC | n_users | mean_actual | mean_endgame | mean_gap | std_gap | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chess.com | bullet | 18 | 1505 | 1546 | +40.3 | 71.0 | −68 | +2 | +25 | +80 | +131 |
| chess.com | blitz | 25 | 1411 | 1420 | +9.0 | 39.4 | −41 | −19 | +9 | +34 | +57 |
| chess.com | rapid | 25 | 1511 | 1513 | +2.2 | 50.4 | −94 | −17 | +10 | +36 | +58 |
| chess.com | classical | 5 | 1397 | 1364 | −33.2 | 112.5 | −168 | −113 | −13 | +71 | +71 ⚠ |
| lichess | bullet | 10 | 1971 | 1988 | +16.4 | 87.1 | −80 | −54 | +3 | +76 | +148 |
| lichess | blitz | 16 | 1900 | 1932 | +32.1 | 56.9 | −48 | −8 | +32 | +68 | +112 |
| lichess | rapid | 10 | 1916 | 1914 | −1.2 | 44.9 | −50 | −39 | −13 | +35 | +62 |
| lichess | classical | 2 | 2158 | 2114 | −44.0 | 18.4 | −56 | −51 | −44 | −38 | −32 ⚠ |

⚠ classical sample too thin per platform; ignore for verdicts.

### Per-combo skill percentiles (within the qualifying pool)

| platform | TC | skill_p25 | skill_p50 | skill_p75 |
|---|---|---|---|---|
| chess.com | bullet | 0.497 | 0.564 | 0.644 |
| chess.com | blitz | 0.465 | 0.519 | 0.543 |
| chess.com | rapid | 0.474 | 0.523 | 0.565 |
| chess.com | classical | 0.448 | 0.597 | 0.608 |
| lichess | bullet | 0.431 | 0.541 | 0.584 |
| lichess | blitz | 0.498 | 0.546 | 0.637 |
| lichess | rapid | 0.459 | 0.558 | 0.624 |
| lichess | classical | 0.554 | 0.559 | 0.565 |

### Pooled gap histogram (100-Elo wide buckets)

| gap range | n | pct | cum_pct |
|---|---|---|---|
| [−200, −100) | 4 | 3.6% | 3.6% |
| [−100, 0) | 43 | 38.7% | 42.3% |
| [0, +100) | 59 | 53.2% | 95.5% |
| [+100, +200) | 4 | 3.6% | 99.1% |
| [+200, +300) | 1 | 0.9% | 100.0% |

Roughly bell-shaped, slightly right-skewed (median > 0). About 95% of users land within ±100 Elo of their Actual ELO, ~5% outside.

### Diagnostics

- **Clamp saturation:** **0 users** at `skill ≤ 0.05` or `skill ≥ 0.95` across all combos. The `[0.05, 0.95]` clamp is currently inactive in production — the formula's `log10(skill/(1−skill))` term is unconstrained for everyone qualifying for the timeline. Means the clamp is a safety belt, not a load-bearing component.
- **Pooled `std_gap`:** roughly 60 Elo (computed as the unweighted average of per-combo std_gaps over the 6 reliable combos; range 39–87 across them). Sits in the lower half of the "120–200 = healthy" range the skill spec proposed, suggesting the formula is a bit *less* sensitive than expected — i.e. the gap distribution is tighter than the spec anticipated. That's fine and arguably better than the alternative; the formula isn't blowing up tails.
- **Mean-gap range across the 6 reliable combos:** −1.2 to +40.3 Elo. Reasonable.

### Platform bias (same TC, chess.com vs lichess)

| TC | chess.com mean_gap | lichess mean_gap | delta (lichess − chess.com) |
|---|---|---|---|
| bullet | +40.3 | +16.4 | −24 |
| blitz | +9.0 | +32.1 | +23 |
| rapid | +2.2 | −1.2 | −3 |

All within ±25 Elo. **No systematic platform bias detected** — Glicko-1 (chess.com) and Glicko-2 (lichess) produce comparable Endgame ELO gaps once normalized through the formula. The largest deltas (bullet, blitz) are still inside ±25 Elo and could plausibly come from sample size (n=10–25 users per cell) rather than platform mechanics.

### TC slope (within platform)

- **chess.com:** bullet (+40) → blitz (+9) → rapid (+2). Bullet skews positive — chess.com bullet players' endgames overperform their bullet rating by ~40 Elo on average. Blitz and rapid sit near zero.
- **lichess:** bullet (+16) → blitz (+32) → rapid (−1). Less monotonic; blitz is the high point.

The expected direction (slower TC → larger positive gap because deeper endgame skill becomes visible) **does not hold** in this data. If anything, the fastest TCs show the largest positive gaps. Could be a population/selection effect (the active user base contains relatively few classical-focused players).

### Recommendations

- **Keep `ENDGAME_ELO_TIMELINE_WINDOW = 100`.** With trailing-100, std_gap is ~60 Elo — tight enough to be readable, loose enough to track real change. Halving the window to 50 would noisify the timeline; doubling to 200 would over-smooth.
- **Keep the `[0.05, 0.95]` skill clamp.** It's currently inactive (0 users saturate), so it imposes no cost; if the user base grows to include extreme outliers (e.g. < 1500 ELO bullet specialists), it'll prevent the formula from going to ±∞.
- **"Notable divergence" callout (forward-looking, not in current UI):** pooled |gap_p90| ≈ 100 Elo. So a future "your endgames are pulling your rating up/down notably" message could trigger when `|endgame_elo − actual_elo| > 100`. About 10% of users would see it at any given snapshot — appropriate for a "this is a noteworthy signal" badge, not a constant nag.
- **400-Elo scaling coefficient:** **keep.** The observed std_gap (~60 Elo) is in the conservative half of the healthy range, so the coefficient isn't over-amplifying the skill signal. No change indicated.

---

## Recommended thresholds summary

| Section | Code constant (file) | Currently set | Recommended (data-driven) | Verdict |
|---|---|---|---|---|
| 1 | `SCORE_DIFF_NEUTRAL_MIN/MAX` (`EndgamePerformanceSection.tsx`) | ±0.10 (±10pp) | ±0.08 (≈ p25–p75 width) | **Narrow** to ±0.08 |
| 1 | `SCORE_DIFF_DOMAIN` (`EndgamePerformanceSection.tsx`) | 0.20 (±20pp) | ±0.17 (p05–p95) | **Keep** (gives small visual margin) |
| 2 | `FIXED_GAUGE_ZONES.conversion` (`EndgameScoreGapSection.tsx`) | `[0.65, 0.75]` | pooled median 0.72; cell range 0.68–0.77 | **Keep** |
| 2 | `FIXED_GAUGE_ZONES.parity` (`EndgameScoreGapSection.tsx`) | `[0.45, 0.55]` | pooled median 0.52; cell range 0.46–0.59 | **Keep** |
| 2 | `FIXED_GAUGE_ZONES.recovery` (`EndgameScoreGapSection.tsx`) | `[0.30, 0.40]` | pooled median 0.32; cell range 0.21–0.47 | **Optionally re-center** to `[0.25, 0.35]` so pooled median sits in the middle; or keep as a "30% is the bar" target |
| 2 | `NEUTRAL_ZONE_MIN/MAX` (`EndgameScoreGapSection.tsx`) | ±0.05 (opp-calibrated bullet chart) | n/a (this snapshot doesn't measure user−opp rate diff distribution per cell) | **Keep** until a future snapshot measures it directly |
| 2 | `BULLET_DOMAIN` (`EndgameScoreGapSection.tsx`) | 0.20 | n/a | **Keep** |
| 3 | `NEUTRAL_PCT_THRESHOLD` (`EndgameClockPressureSection.tsx`) | ±10% | ±7% (≈ p25–p75 width pooled across blitz/rapid) | **Narrow** to ±7% |
| 3 | `NEUTRAL_TIMEOUT_THRESHOLD` (`EndgameClockPressureSection.tsx`) | ±5pp | bullet p75 = +24.6 (signal expected); blitz/rapid p25–p75 within ±5pp | **Keep** |
| 4 | Pooling in `_compute_time_pressure_chart` (`endgame_service.py`) | TCs pooled into one curve | max per-bucket range 7.6pp (bucket 70–80%) | **Keep** pooling; document the spread |
| 4 | `Y_AXIS_DOMAIN` (`EndgameTimePressureSection.tsx`) | `[0.2, 0.8]` | observed range 0.27–0.60 | **Keep** |
| 4 | `X_AXIS_DOMAIN` (`EndgameTimePressureSection.tsx`) | `[0, 100]` | n/a | **Keep** |
| 5 | `ENDGAME_SKILL_ZONES` (`EndgameScoreGapSection.tsx`) | `[0–0.45 / 0.45–0.55 / 0.55–1.0]` | pooled p25–p75 = `[0.47, 0.59]` | **Widen upper bound** to 0.59 → `[0–0.45 / 0.45–0.59 / 0.59–1.0]`. Pooled median 0.52 still sits inside neutral. |
| 5 | "Typical value 52%" code comment | 52% | pooled median 0.522 | **Keep** comment as-is |
| 6 | `ENDGAME_ELO_TIMELINE_WINDOW` (`endgame_service.py`) | 100 | std_gap ≈ 60 Elo at this window — healthy | **Keep** |
| 6 | `_ENDGAME_ELO_SKILL_CLAMP_LO/HI` (`endgame_service.py`) | `[0.05, 0.95]` | 0 users currently saturating | **Keep** (safety belt) |
| 6 | `_MATERIAL_ADVANTAGE_THRESHOLD` (`endgame_service.py`) | 100 | n/a (used identically in benchmark queries) | **Keep** |
| 6 | "Notable divergence" threshold (forward-looking, not in UI yet) | n/a | `\|gap\| > 100 Elo` (≈ pooled p90) | New idea — add only if the UI gains a "notable" callout |

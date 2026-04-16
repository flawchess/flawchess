# FlawChess Benchmarks — 2026-04-16

- **DB**: prod (read-only via `flawchess-prod-db` MCP over SSH tunnel on `localhost:15432`)
- **Snapshot taken**: 2026-04-16T20:29:51Z
- **Base filters**: `rated = TRUE AND NOT is_computer_game` (applied to every section; mirrors the frontend's default human-opponent / rated-only posture)
- **Sample floors**:
  - §1: ≥ 30 endgame AND ≥ 30 non-endgame games per user
  - §2: ≥ 100 games per (ELO × TC × bucket) cell for pooled rates; ≥ 10 users × ≥ 10 games each for per-user distributions
  - §3: ≥ 20 endgame games per user per TC
  - §4: ≥ 100 games per (TC × time-remaining bucket) cell to plot a point

---

## 1. Score % Difference (endgame vs non-endgame)

### Currently set in code

`frontend/src/components/charts/EndgamePerformanceSection.tsx`:

| Constant | Value |
|---|---|
| `SCORE_DIFF_NEUTRAL_MIN` | `-0.05` |
| `SCORE_DIFF_NEUTRAL_MAX` | `+0.05` |
| `SCORE_DIFF_DOMAIN` | `±0.20` |

### Population distribution (per-user diff = endgame_score − non_endgame_score)

| n_users | mean | std | p05 | p10 | p25 | p50 | p75 | p90 | p95 | min | max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 34 | +0.0117 | 0.1044 | −0.1219 | −0.0907 | −0.0596 | −0.0061 | +0.0696 | +0.1295 | +0.1666 | −0.2337 | +0.2896 |

### Raw per-user list (sorted by diff)

| user_id | eg_games | non_eg_games | eg_score | non_eg_score | diff |
|---|---|---|---|---|---|
| 21 | 6,796 | 4,491 | 0.4091 | 0.6427 | −0.2337 |
| 28 | 2,905 | 2,064 | 0.4664 | 0.6172 | −0.1508 |
| 26 | 469 | 273 | 0.6684 | 0.7747 | −0.1063 |
| 19 | 907 | 704 | 0.4625 | 0.5568 | −0.0943 |
| 30 | 4,720 | 3,813 | 0.4703 | 0.5526 | −0.0822 |
| 2 | 4,700 | 3,802 | 0.4697 | 0.5518 | −0.0821 |
| 12 | 4,160 | 1,910 | 0.4919 | 0.5605 | −0.0685 |
| 20 | 7,322 | 3,274 | 0.5007 | 0.5609 | −0.0603 |
| 45 | 28,590 | 9,496 | 0.5266 | 0.5865 | −0.0599 |
| 15 | 1,763 | 961 | 0.4660 | 0.5245 | −0.0585 |
| 4 | 13,410 | 9,783 | 0.4852 | 0.5249 | −0.0397 |
| 37 | 375 | 254 | 0.5080 | 0.5472 | −0.0392 |
| 31 | 3,235 | 1,477 | 0.5099 | 0.5420 | −0.0321 |
| 14 | 953 | 1,133 | 0.5147 | 0.5455 | −0.0308 |
| 29 | 3,824 | 1,811 | 0.5255 | 0.5478 | −0.0223 |
| 46 | 3,587 | 3,175 | 0.4947 | 0.5142 | −0.0195 |
| 24 | 445 | 328 | 0.5573 | 0.5747 | −0.0174 |
| 44 | 69 | 106 | 0.4203 | 0.4151 | +0.0052 |
| 42 | 31 | 51 | 0.5484 | 0.5392 | +0.0092 |
| 33 | 180 | 263 | 0.3778 | 0.3479 | +0.0299 |
| 10 | 5,163 | 3,243 | 0.5280 | 0.4869 | +0.0411 |
| 5 | 4,575 | 3,542 | 0.5388 | 0.4939 | +0.0449 |
| 32 | 201 | 191 | 0.6119 | 0.5602 | +0.0517 |
| 16 | 749 | 441 | 0.5067 | 0.4444 | +0.0622 |
| 25 | 1,525 | 940 | 0.5728 | 0.5032 | +0.0696 |
| 17 | 7,438 | 6,511 | 0.5501 | 0.4804 | +0.0697 |
| 18 | 112 | 146 | 0.5893 | 0.5034 | +0.0859 |
| 13 | 15,738 | 4,996 | 0.5872 | 0.4664 | +0.1209 |
| 3 | 2,484 | 1,889 | 0.5803 | 0.4584 | +0.1219 |
| 35 | 626 | 821 | 0.5855 | 0.4574 | +0.1281 |
| 34 | 7,836 | 12,605 | 0.5913 | 0.4612 | +0.1301 |
| 22 | 783 | 662 | 0.6315 | 0.4690 | +0.1625 |
| 11 | 10,727 | 7,458 | 0.6027 | 0.4286 | +0.1741 |
| 43 | 87 | 139 | 0.7356 | 0.4460 | +0.2896 |

### Recommendations

| Metric | Currently set | Data-driven (p25–p75) | Data-driven (p05–p95) | Verdict |
|---|---|---|---|---|
| Neutral zone | ±0.05 | [−0.060, +0.070] | — | **Widen to ±0.07**. The neutral IQR is ~13pp wide and slightly right-biased; the current ±5pp band flags a lot of essentially-typical users as outliers. Rounding to a readable ±0.07 (or asymmetric [−0.06, +0.07]) matches the data. |
| Gauge domain | ±0.20 | — | [−0.122, +0.167] | **Keep ±0.20** — already covers p05/p95 with a small margin on both sides. Last update (commit in `EndgamePerformanceSection.tsx`) cited this report, so domain is already calibrated. |

Mean diff (+0.012) is ≈ 0, so **do not re-center** — the zero anchor is correct.

**Tail notes**: user 21 (−0.23) and user 43 (+0.29) are the population extremes. User 43 only has 87 endgame games so rests on a thinner sample than most; user 21 at 6,796 endgame games is genuinely that bad in endgames.

---

## 2. Conversion / Parity / Recovery by ELO × TC

### Currently set in code

`frontend/src/components/charts/EndgameScoreGapSection.tsx`:

| Constant | Value |
|---|---|
| `FIXED_GAUGE_ZONES.conversion` | danger < 0.65, neutral 0.65–0.75 (**Win %**), success ≥ 0.75 |
| `FIXED_GAUGE_ZONES.parity` | danger < 0.45, neutral 0.45–0.55 (**Score %**), success ≥ 0.55 |
| `FIXED_GAUGE_ZONES.recovery` | danger < 0.30, neutral 0.30–0.40 (**Save %**), success ≥ 0.40 |
| `NEUTRAL_ZONE_MIN` / `NEUTRAL_ZONE_MAX` | ±0.05 (opponent-calibrated diff, applied to all three buckets) |
| `BULLET_DOMAIN` | ±0.20 |
| `MIN_OPPONENT_BASELINE_GAMES` | 10 |

### Conversion (`Win %`) — ELO × TC

Rows = user rating bucket (500-wide); columns = time control. Cells are Win % with `(n games)` underneath. Cells with < 100 games are italicized as low-confidence.

| ELO | Bullet | Blitz | Rapid | Classical |
|---|---|---|---|---|
| <500    | *0.59 (68)*    | 0.62 (153)  | *0.66 (61)* | — |
| 500–999 | 0.73 (335)     | 0.65 (1,544)| 0.69 (1,700)| *0.83 (18)* |
| 1000–1499 | 0.66 (2,712) | 0.69 (2,650)| 0.68 (4,453)| *0.92 (84)* |
| 1500–1999 | 0.68 (10,123)| 0.68 (4,002)| 0.72 (4,086)| *0.90 (39)* |
| 2000–2499 | 0.69 (11,997)| 0.73 (1,368)| 0.74 (1,560)| *0.79 (81)* |
| 2500+    | 0.78 (199)    | 0.67 (1,417)| *1.00 (3)*  | — |

**Pooled (reliable cells only)**: 48,299 games across 15 cells → Win % = **68.8 %**, Score % = 71.9 %, Save % = 74.9 %

- Currently set in code: conversion neutral band = **Win % 65–75 %**.
- Pooled Win % (68.8 %) sits in the middle of the band.
- Verdict: **Keep**. Gauge is well-calibrated at the population level.

### Parity (`Score %`) — ELO × TC

| ELO | Bullet | Blitz | Rapid | Classical |
|---|---|---|---|---|
| <500    | *0.48 (44)*    | *0.33 (69)* | *0.47 (19)* | — |
| 500–999 | 0.59 (298)    | 0.48 (1,108) | 0.46 (1,261)| *0.28 (25)* |
| 1000–1499 | 0.52 (3,054)| 0.49 (2,884) | 0.49 (4,247)| *0.65 (53)* |
| 1500–1999 | 0.50 (9,133)| 0.52 (4,854) | 0.49 (5,566)| *0.73 (52)* |
| 2000–2499 | 0.53 (15,125)| 0.58 (2,709)| 0.58 (2,542)| 0.66 (144) |
| 2500+    | 0.57 (363)   | 0.51 (2,974) | *0.83 (6)*  | — |

**Pooled (reliable cells only)**: 56,262 games → Win % = 47.3 %, Score % = **51.7 %**, Save % = 56.2 %

- Currently set in code: parity neutral band = **Score % 45–55 %**.
- Pooled Score % (51.7 %) squarely in the middle of the band.
- Verdict: **Keep**. Also well-calibrated.

### Recovery (`Save %`) — ELO × TC

| ELO | Bullet | Blitz | Rapid | Classical |
|---|---|---|---|---|
| <500    | *0.53 (68)*   | 0.30 (105)  | *0.36 (53)*  | — |
| 500–999 | 0.49 (472)    | 0.32 (928)  | 0.24 (1,217) | *0.00 (18)* |
| 1000–1499 | 0.38 (3,489)| 0.31 (2,287)| 0.28 (2,903) | *0.17 (23)* |
| 1500–1999 | 0.37 (8,950)| 0.32 (2,842)| 0.28 (4,075) | *0.25 (12)* |
| 2000–2499 | 0.37 (10,098)| 0.40 (1,192)| 0.39 (1,129)| *0.49 (39)* |
| 2500+    | 0.40 (213)   | 0.37 (1,283)| *0.67 (3)*   | — |

**Pooled (reliable cells only)**: 41,183 games → Win % = 28.7 %, Score % = 31.7 %, Save % = **34.8 %**

- Currently set in code: recovery neutral band = **Save % 30–40 %**.
- Pooled Save % (34.8 %) sits in the middle.
- Verdict: **Keep**. All three gauges are well-calibrated for the median population user.

### Opponent-relative diff (bullet-chart `NEUTRAL_ZONE_MIN..MAX` calibration)

Per-cell user-vs-mirror-opponent diffs across the 15 reliable (ELO × TC) cells:

| Bucket | cells | mean | p25 | p50 | p75 | min | max |
|---|---|---|---|---|---|---|---|
| Conversion | 15 | +0.042 | −0.014 | +0.034 | +0.094 | −0.074 | +0.223 |
| Parity     | 15 | +0.062 | −0.011 | +0.031 | +0.152 | −0.085 | +0.313 |
| Recovery   | 15 | +0.042 | −0.014 | +0.034 | +0.094 | −0.074 | +0.223 |

Note: conversion's Win-%-diff and recovery's Save-%-diff are algebraically identical by same-game symmetry, so the two rows match.

- Currently set in code: **±0.05** (symmetric, shared across buckets).
- Data-driven IQR (conv/rec): [−1.4 pp, +9.4 pp] — **asymmetric, median +3.4 pp**.
- Data-driven IQR (parity): [−1.1 pp, +15.2 pp] — even wider and more right-biased.
- Verdict: **Keep the symmetric ±5 pp.** The +3-4 pp right-shift reflects selection bias (FlawChess users tend to outperform their random pool), not gauge mis-calibration. The stated design principle in the code comment ("equally-rated players should score equally in mirrored situations") anchors the zone at zero by intent. Widening asymmetrically or per-bucket would break that principle. A single user's per-filter diff should still cluster near zero under equal-strength matchmaking, which is the right target for the Diff color.

### Per-user distribution within cells (spread within a cell)

Rate = the bucket's own metric (conversion=Win %, parity=Score %, recovery=Save %), per user per (ELO × TC × bucket) cell, after requiring ≥ 10 games per user. Only cells with ≥ 10 users shown.

| ELO | TC | Bucket | n_users | p25 | p50 | p75 |
|---|---|---|---|---|---|---|
| 500–999 | blitz | conversion | 13 | 0.66 | 0.74 | 0.77 |
| 500–999 | blitz | parity     | 12 | 0.44 | 0.47 | 0.51 |
| 500–999 | blitz | recovery   | 12 | 0.25 | 0.30 | 0.33 |
| 500–999 | rapid | conversion | 11 | 0.77 | 0.81 | 0.83 |
| 1000–1499 | bullet | conversion | 10 | 0.71 | 0.74 | 0.81 |
| 1000–1499 | bullet | recovery   | 12 | 0.24 | 0.35 | 0.41 |
| 1000–1499 | blitz  | conversion | 13 | 0.72 | 0.75 | 0.79 |
| 1000–1499 | blitz  | parity     | 13 | 0.45 | 0.48 | 0.54 |
| 1000–1499 | blitz  | recovery   | 12 | 0.21 | 0.27 | 0.32 |
| 1000–1499 | rapid  | conversion | 17 | 0.68 | 0.77 | 0.84 |
| 1000–1499 | rapid  | parity     | 16 | 0.45 | 0.53 | 0.57 |
| 1000–1499 | rapid  | recovery   | 14 | 0.22 | 0.27 | 0.35 |
| 1500–1999 | bullet | conversion | 12 | 0.66 | 0.71 | 0.76 |
| 1500–1999 | bullet | parity     | 12 | 0.48 | 0.49 | 0.55 |
| 1500–1999 | bullet | recovery   | 13 | 0.32 | 0.36 | 0.41 |
| 1500–1999 | blitz  | conversion | 17 | 0.70 | 0.73 | 0.82 |
| 1500–1999 | blitz  | parity     | 17 | 0.48 | 0.53 | 0.59 |
| 1500–1999 | blitz  | recovery   | 15 | 0.24 | 0.27 | 0.35 |
| 1500–1999 | rapid  | conversion | 14 | 0.73 | 0.76 | 0.84 |
| 1500–1999 | rapid  | parity     | 15 | 0.45 | 0.50 | 0.59 |
| 1500–1999 | rapid  | recovery   | 13 | 0.26 | 0.26 | 0.29 |
| 2000–2499 | blitz  | conversion | 11 | 0.68 | 0.71 | 0.80 |
| 2000–2499 | blitz  | parity     | 11 | 0.54 | 0.54 | 0.59 |
| 2000–2499 | blitz  | recovery   | 10 | 0.22 | 0.30 | 0.35 |

These IQRs tell you the *within-cell* spread across users. For example, at 1500 blitz, half the users convert between 70 % and 82 % Win % — matches the code's conversion neutral band (65–75 %) landing slightly below the bulk of typical users, which is consistent with the band's role as a *typical-cohort* anchor (below = needs work, above = strong) rather than a "median users live here" marker.

---

## 3. Time Pressure at Endgame Entry

### Currently set in code

`frontend/src/components/charts/EndgameClockPressureSection.tsx`:

| Constant | Value | Unit |
|---|---|---|
| `NEUTRAL_PCT_THRESHOLD` | 10 | pp of base time (symmetric ±10) |
| `NEUTRAL_TIMEOUT_THRESHOLD` | 5 | pp net timeout rate (symmetric ±5) |

### Clock diff (% of base time) — primary metric, matches live gauge

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| Bullet | 23 | +2.22 | −5.67 | −1.86 | −0.38 | +6.62 | +14.15 |
| Blitz  | 31 | −4.37 | −15.27 | −7.39 | −3.13 | −0.57 | +4.90 |
| Rapid  | 28 | −3.18 | −20.04 | −6.98 | −4.58 | +4.32 | +8.57 |
| Classical | 2 | −8.49 | −26.47 | −18.48 | −8.49 | +1.51 | +9.50 |

### Net timeout rate (pp)

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| Bullet | 23 | +11.69 | −9.63 | −0.77 | +4.90 | +24.38 | +40.43 |
| Blitz  | 31 | −0.53 | −22.55 | −5.18 | +1.14 | +8.49 | +14.36 |
| Rapid  | 28 | +1.06 | −7.99 | −1.64 | +2.28 | +4.50 | +7.77 |
| Classical | 2 | +0.50 | −2.79 | −1.33 | +0.50 | +2.34 | +3.80 |

### Clock diff (seconds) — secondary readout

| TC | s_p25 | s_p50 | s_p75 |
|---|---|---|---|
| Bullet | −1.1 s | −0.2 s | +4.1 s |
| Blitz | −15.1 s | −9.4 s | −0.9 s |
| Rapid | −53.8 s | −32.1 s | +28.0 s |
| Classical | −321 s | −168 s | −15.8 s |

### Recommendations

Current band is symmetric ±10 pp. Recommended neutral zone per TC (data-driven, per-user IQR of avg clock diff in % of base time):

| TC | Currently set (%pp) | Recommended [p25, p75] | Recommended [p05, p95] | Verdict |
|---|---|---|---|---|
| Bullet | ±10 | [−1.9, +6.6] | [−5.7, +14.1] | **Keep ±10**. IQR fits well inside. |
| Blitz  | ±10 | [−7.4, −0.6] | [−15.3, +4.9] | **Keep ±10** but note the p05 at −15 pp pokes outside the band — that tail (players habitually down 15 %+ of base time at endgame entry) is extreme but real. |
| Rapid  | ±10 | [−7.0, +4.3] | [−20.0, +8.6] | **Keep ±10**. IQR fits; the left tail (one user at −20 pp) is extreme but not typical. |
| Classical | ±10 | (only 2 users) | — | Low sample — no change advised. |

Net timeout band is currently ±5 pp. Per-TC IQRs:

| TC | Currently set (pp) | Recommended [p25, p75] | Verdict |
|---|---|---|---|
| Bullet | ±5 | [−0.8, +24.4] | **Current band under-fits bullet.** Median user has a net timeout rate of +4.9 pp and p75 is +24.4 pp — typical bullet players flag their opponents a lot more than they get flagged. Recommend widening to ±15 pp for bullet, or keeping ±5 and accepting that "neutral" in bullet is narrow for a good reason. |
| Blitz  | ±5 | [−5.2, +8.5] | **Keep ±5**, IQR is close. |
| Rapid  | ±5 | [−1.6, +4.5] | **Keep ±5**. IQR is tighter than the band; median is already near zero. |
| Classical | ±5 | (2 users) | Low sample — no change. |

**Cross-TC consistency of clock-diff band**: the % metric is already normalized by base time, which is supposed to make TCs comparable. The data mostly supports that — bullet, blitz, and rapid IQRs all fit inside ±10. The bullet median +0 vs blitz/rapid median ~−3/−5 pp is a mild right-shift that may reflect bullet-specific flagging dynamics. A single shared ±10 band is defensible.

**Known bias**: this SQL approximation takes clocks at `entry_ply` and `entry_ply + 1`. The backend scans the ply array for the first non-NULL clock per parity, so the backend sees slightly more games than this query. Magnitudes should be very close but exact percentiles may differ by ~1-2 pp.

---

## 4. Time Pressure vs Performance — cross-TC comparison

### Currently set in code

- `app/services/endgame_service.py::_compute_time_pressure_chart` — **POOLS all time controls** into a single `user_series + opp_series` pair (commit marker `quick-260416-pkx`).
- `frontend/src/components/charts/EndgameTimePressureSection.tsx`:
  - `Y_AXIS_DOMAIN` = `[0.2, 0.8]`
  - `X_AXIS_DOMAIN` = `[0, 100]`
  - `MIN_GAMES_FOR_RELIABLE_STATS` (from `lib/theme.ts`) = 10

**The question for this section is therefore: "is the current pooling still justified, or should it become per-TC?"**

### User score % by (TC × time-remaining bucket)

Rows = time-remaining bucket (0–10 % … 90–100 %); columns = TC. Cell format: `score (n games)`. Cells with n < 100 italicized.

| Bucket | Bullet | Blitz | Rapid | Classical |
|---|---|---|---|---|
| 0–10 %   | 0.272 (4,696)  | 0.331 (3,344) | 0.296 (1,219) | *0.275 (20)* |
| 10–20 %  | 0.415 (8,123)  | 0.449 (3,328) | 0.427 (1,396) | *0.609 (23)* |
| 20–30 %  | 0.503 (10,541) | 0.505 (3,229) | 0.484 (1,939) | *0.682 (11)* |
| 30–40 %  | 0.547 (11,031) | 0.533 (3,982) | 0.513 (2,622) | *0.881 (21)* |
| 40–50 %  | 0.570 (12,421) | 0.564 (4,501) | 0.533 (3,569) | *0.400 (10)* |
| 50–60 %  | 0.595 (11,025) | 0.580 (4,815) | 0.535 (4,736) | *0.533 (15)* |
| 60–70 %  | 0.595 (10,291) | 0.586 (4,655) | 0.546 (5,897) | *0.692 (13)* |
| 70–80 %  | 0.601 (5,743)  | 0.562 (3,598) | 0.525 (6,585) | *0.500 (10)* |
| 80–90 %  | 0.589 (2,211)  | 0.578 (1,759) | 0.521 (5,110) | *0.600 (10)* |
| 90–100 % | 0.551 (304)    | 0.573 (383)   | 0.527 (1,611) | *0.682 (11)* |

### Per-bucket spread (bullet / blitz / rapid, classical excluded — n<100 everywhere)

| Bucket | min TC | max TC | range (pp) |
|---|---|---|---|
| 0–10 %   | bullet 0.272 | blitz 0.331 | **5.9** |
| 10–20 %  | bullet 0.415 | blitz 0.449 | 3.4 |
| 20–30 %  | rapid 0.484  | blitz 0.505 | 2.1 |
| 30–40 %  | rapid 0.513  | bullet 0.547 | 3.3 |
| 40–50 %  | rapid 0.533  | bullet 0.570 | 3.7 |
| 50–60 %  | rapid 0.535  | bullet 0.595 | **6.0** |
| 60–70 %  | rapid 0.546  | bullet 0.595 | 4.9 |
| 70–80 %  | rapid 0.525  | bullet 0.601 | **7.6** |
| 80–90 %  | rapid 0.521  | bullet 0.589 | **6.8** |
| 90–100 % | rapid 0.527  | blitz 0.573 | 4.6 |

- **Max per-bucket range**: 7.6 pp (bucket 70–80 %)
- **Buckets exceeding the 5 pp threshold**: 0–10 %, 50–60 %, 70–80 %, 80–90 % (4 of 10)

### Verdict

**Consider switching away from pooled.** Max spread (7.6 pp at 70–80 %) exceeds the skill's 5 pp threshold, and 4 of 10 buckets show ≥ 5 pp spread between TCs. The pattern is systematic: rapid tends to score lowest in the mid-to-high time-remaining buckets (≥ 50 %), while bullet tends highest. On a Y-axis domain of `[0.2, 0.8]` (60 pp tall), 7-8 pp is ≈ 12 % of the axis — visible, not noise.

Two reasonable paths:

1. **Switch to per-TC lines** — most informative; makes the bullet-vs-rapid gap at high-time-remaining buckets visible. Chart gets busier (3-4 colored line pairs instead of 2) but the existing filter panel already lets users narrow by TC, so the default pooled view is essentially "all" and splitting is the natural next view.
2. **Keep pooled but document the bias** — the pooled series is weighted by game counts, which are dominated by bullet+blitz in most buckets, so the pooled line trends toward those TCs' numbers. A footnote would suffice if the bias isn't considered harmful.

Recommend **option 1** given the 7.6 pp bucket-7 spread. If preserving visual simplicity matters, a compromise is to keep pooled as default and add a "split by time control" toggle.

---

## Recommended thresholds summary

| Metric | Code constant | Currently set | Recommended (p25–p75 / p05–p95) | Verdict |
|---|---|---|---|---|
| Endgame vs non-endgame diff — neutral | `SCORE_DIFF_NEUTRAL_MIN..MAX` (`EndgamePerformanceSection.tsx`) | ±0.05 | [−0.060, +0.070] | **Widen to ±0.07** (or asymmetric [−0.06, +0.07]) |
| Endgame vs non-endgame diff — domain | `SCORE_DIFF_DOMAIN` (same file) | ±0.20 | [−0.122, +0.167] | **Keep ±0.20** |
| Conversion gauge | `FIXED_GAUGE_ZONES.conversion` (`EndgameScoreGapSection.tsx`) | Win % 65–75 neutral | pooled 68.8 % | **Keep** |
| Parity gauge | `FIXED_GAUGE_ZONES.parity` (same file) | Score % 45–55 neutral | pooled 51.7 % | **Keep** |
| Recovery gauge | `FIXED_GAUGE_ZONES.recovery` (same file) | Save % 30–40 neutral | pooled 34.8 % | **Keep** |
| Opponent-diff neutral band (all buckets) | `NEUTRAL_ZONE_MIN..MAX` (same file) | ±0.05 | conv/rec IQR [−0.014, +0.094]; parity IQR [−0.011, +0.152] | **Keep** — the zero anchor reflects an equal-strength design principle; the +3-4 pp right-shift is user selection, not gauge miscalibration |
| Opponent-diff bullet domain | `BULLET_DOMAIN` (same file) | ±0.20 | parity max reach +0.31 | **Keep ±0.20**; extreme cells clip but typical values display well |
| Clock-diff neutral band | `NEUTRAL_PCT_THRESHOLD` (`EndgameClockPressureSection.tsx`) | ±10 pp | bullet IQR ±7, blitz/rapid IQR ±7 | **Keep ±10 pp** |
| Net-timeout neutral band | `NEUTRAL_TIMEOUT_THRESHOLD` (same file) | ±5 pp | bullet IQR [−0.8, +24.4]; blitz [−5.2, +8.5]; rapid [−1.6, +4.5] | **Under-fits bullet** (median user at +4.9 pp, p75 +24 pp). Blitz/rapid fit. Either widen to ±10 pp (bullet-driven) or accept current band as the cross-TC compromise |
| Time-pressure chart pooling | `_compute_time_pressure_chart` (`endgame_service.py`) + `Y_AXIS_DOMAIN` (`EndgameTimePressureSection.tsx`) | single pooled pair of series, Y=[0.2, 0.8] | max per-bucket spread 7.6 pp (bucket 70–80 %), 4/10 buckets > 5 pp | **Switch to per-TC**, or add a toggle; pooled hides a systematic bullet-vs-rapid gap in the high-time-remaining buckets |

# FlawChess Benchmarks — 2026-04-24

- **DB**: prod
- **Snapshot taken**: 2026-04-24T16:36:51Z
- **Base filters**: `rated = TRUE AND NOT is_computer_game` (mirrors the frontend's default human-opponent, rated-only posture)
- **Endgame rule**: `game_positions.endgame_class IS NOT NULL` on ≥ 6 plies (matches `ENDGAME_PLY_THRESHOLD`)
- **Material threshold**: ±100 centipawns (`_MATERIAL_ADVANTAGE_THRESHOLD`)
- **Sample floors**: Section 1 — 30 endgame + 30 non-endgame games per user; Section 2a — per-user cell ≥ 10, pooled cell ≥ 100 games (shown with caveats below); Section 2b — ≥ 20 games per user per (ELO × TC) and ≥ 2 non-empty material sub-buckets, cells shown if n_users ≥ 10; Section 3 — 30 endgame games per user per combo; Section 4 — 20 endgame games per user per TC; Section 5 — 100 games per (TC × time-remaining bucket).

---

## 1. Endgame vs Non-Endgame Score Distributions

### Currently set in code (`frontend/src/components/charts/EndgamePerformanceSection.tsx`)

- `SCORE_GAP_NEUTRAL_MIN = -0.10` / `SCORE_GAP_NEUTRAL_MAX = 0.10` (gap gauge blue band)
- `SCORE_GAP_DOMAIN = 0.20` (gap gauge half-width, ±0.20)
- `SCORE_TIMELINE_Y_DOMAIN = [20, 80]` (two-line timeline y-axis, as %)
- `SCORE_TIMELINE_EPSILON_PCT = 1` (shading threshold between the two lines)
- **No `SCORE_TIMELINE_NEUTRAL_MIN/MAX`** — the new two-line timeline has no neutral band yet. This benchmark proposes the initial bounds.

### Per-user distribution (n_users = 40, ≥30 games each side)

| Distribution | mean | std | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| **Endgame score** (eg) | 0.531 | 0.072 | 0.420 | 0.490 | 0.520 | 0.581 | 0.633 |
| **Non-endgame score** (non-eg) | 0.521 | 0.072 | 0.428 | 0.468 | 0.525 | 0.560 | 0.619 |
| **Score diff** (eg − non-eg) | 0.010 | 0.105 | −0.128 | −0.060 | −0.015 | 0.074 | 0.163 |

**Sanity check**: `eg_p50 − non_eg_p50 = 0.520 − 0.525 = −0.005` vs `diff_p50 = −0.015`. Agree within rounding ✅. The typical user scores essentially the same in endgames as in non-endgames — the population median diff sits within ±2 pp of zero.

### Recommendations

- **Timeline neutral band** (new — no current value): intersection of `[eg_p25, eg_p75] ∩ [non_eg_p25, non_eg_p75] = [0.490, 0.560] ∩ [0.468, 0.581] = [0.490, 0.560]`. Overlap 0.070 / narrower-interval-width 0.091 = 77 % ⇒ collapse to a single unified band. **Proposed `SCORE_TIMELINE_NEUTRAL_MIN/MAX = [49 %, 56 %]`** (as percent on the timeline chart). Frame as "typical middle band — users who sit here are performing at the median of the player base on that axis".
- **Timeline axis range** `SCORE_TIMELINE_Y_DOMAIN`: observed combined `[p05, p95] = [42 %, 63 %]`. Currently `[20, 80]`. **Verdict: the current ±30pp domain is roughly 2× wider than needed.** Tightening to `[35, 70]` would use the chart's vertical space far better. Keep as-is only if you want to reserve headroom for extreme users (p05/p95 tails would still be shown).
- **Score-gap gauge neutral zone** `SCORE_GAP_NEUTRAL_MIN/MAX`: observed `[diff_p25, diff_p75] = [−0.060, +0.074]`. Currently `[−0.10, +0.10]`. **Verdict: keep** — the code's ±0.10 band comfortably includes p25–p75 and leaves a bit of slack. Narrowing to ±0.08 would tighten the neutral classification but risks reclassifying borderline users on every small sample shift. The diff median is near zero so re-centering isn't needed.
- **Score-gap gauge range** `SCORE_GAP_DOMAIN`: observed `[diff_p05, diff_p95] = [−0.128, +0.163]`. Currently ±0.20. **Verdict: keep** — p95 magnitude is 0.163 and p05 is 0.128, both within the current half-width with modest headroom. No change.

---

## 2. Conversion / Parity / Recovery + Endgame Skill by ELO × TC

### Currently set in code (`frontend/src/components/charts/EndgameScoreGapSection.tsx`)

- `FIXED_GAUGE_ZONES.conversion` — danger `[0, 0.65]`, **neutral `[0.65, 0.75]`**, success `[0.75, 1.0]`
- `FIXED_GAUGE_ZONES.parity` — danger `[0, 0.45]`, **neutral `[0.45, 0.55]`**, success `[0.55, 1.0]`
- `FIXED_GAUGE_ZONES.recovery` — danger `[0, 0.25]`, **neutral `[0.25, 0.35]`**, success `[0.35, 1.0]`
- `NEUTRAL_ZONE_MIN/MAX = [−0.05, 0.05]` (opponent-calibrated bullet chart)
- `BULLET_DOMAIN = 0.20` (bullet chart half-width)
- `ENDGAME_SKILL_ZONES` — danger `[0, 0.45]`, **neutral `[0.45, 0.55]`**, success `[0.55, 1.0]`; code comment notes "typical value lands around 52 % on FlawChess data"

### Query A — Conversion rate (Win % when user has ≥ +100 imbalance at entry AND after entry+4)

Rows = ELO bucket, columns = TC. Cell = pooled score, n in parens. Greyed-out (italic) cells have n < 100 (low confidence).

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0–499 | *0.635 (78)* | 0.642 (373) | 0.735 (100) | — |
| 500–999 | 0.739 (364) | 0.670 (3391) | 0.749 (1320) | *0.798 (47)* |
| 1000–1499 | 0.682 (3000) | 0.725 (3484) | 0.736 (3875) | *0.938 (81)* |
| 1500–1999 | 0.695 (11861) | 0.715 (4810) | 0.755 (5186) | *0.927 (41)* |
| 2000–2499 | 0.720 (12171) | 0.768 (1456) | 0.779 (1617) | *0.846 (81)* |
| 2500+ | 0.798 (253) | 0.703 (1417) | *1.00 (3)* | — |

- **Overall pooled conversion rate** (games-weighted, reliable cells only): ≈ **0.715**.
- **Observed cell range across TC × ELO** (n ≥ 100): 0.642 – 0.798, most cells land in **0.68 – 0.78**.
- **Opponent rate** (by symmetry, 1 − pooled recovery) ≈ 1 − 0.308 = **0.692**. Rate gap ≈ +2pp — conversion is slightly easier for the player in front than for the trailing opponent.
- **Recommended neutral band**: `[0.67, 0.77]`. Currently `[0.65, 0.75]`. **Verdict: shift up by 2 pp to `[0.67, 0.77]`**, or keep the current band and accept that the median user sits at the top edge of neutral. The current floor (0.65) flags nobody — no n ≥ 100 cell lands below it — so the lower boundary is doing no work. Narrowing to [0.67, 0.77] sharpens the signal.

### Query A — Parity rate (Score % when no material advantage either way)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0–499 | *0.514 (37)* | 0.361 (187) | *0.500 (39)* | — |
| 500–999 | 0.584 (310) | 0.454 (2181) | 0.474 (980) | *0.463 (54)* |
| 1000–1499 | 0.513 (3390) | 0.494 (3959) | 0.501 (3883) | *0.641 (46)* |
| 1500–1999 | 0.492 (11011) | 0.510 (6087) | 0.497 (7475) | *0.732 (54)* |
| 2000–2499 | 0.535 (15421) | 0.581 (2822) | 0.578 (2636) | *0.655 (145)* |
| 2500+ | 0.580 (468) | 0.512 (2974) | — | — |

- **Overall pooled parity rate** ≈ **0.510**.
- **Observed cell range** (n ≥ 100): 0.454 – 0.584 (excluding the outlier blitz@0–499 at 0.361 where n is still borderline).
- **Opponent rate** = 1 − 0.510 = **0.490**. Gap ≈ +2 pp.
- **Recommended neutral band**: `[0.45, 0.58]`. Currently `[0.45, 0.55]`. **Verdict: consider widening the upper bound to 0.58** — strong TCs (bullet@500, blitz@2000, rapid@2000) sit at ~0.58 which the current band classifies as "success". Whether that's desired depends on intent: if parity success should mean "meaningfully above median", keep 0.55; if it should mean "top quartile", shift to 0.58. **Keep** is defensible either way.

### Query A — Recovery rate (Save % when user has ≤ −100 imbalance at entry AND after entry+4)

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0–499 | *0.524 (62)* | 0.219 (272) | 0.254 (112) | — |
| 500–999 | 0.469 (489) | 0.253 (2378) | 0.210 (1036) | *0.095 (58)* |
| 1000–1499 | 0.349 (3713) | 0.274 (3158) | 0.259 (2749) | *0.118 (17)* |
| 1500–1999 | 0.342 (10560) | 0.288 (3460) | 0.256 (5050) | *0.208 (12)* |
| 2000–2499 | 0.344 (10274) | 0.363 (1235) | 0.338 (1169) | *0.413 (40)* |
| 2500+ | 0.354 (244) | 0.315 (1283) | — | — |

- **Overall pooled recovery rate** ≈ **0.306**.
- **Observed cell range** (n ≥ 100): 0.210 – 0.469, clustered around **0.25 – 0.36**. Bullet recovers substantially better than blitz/rapid at every ELO (time pressure on the opposing converter compounds).
- **Opponent rate** = 1 − 0.715 = **0.285**. Gap ≈ +2 pp — user recovers slightly better than the opponent would against them, same sign as conversion.
- **Recommended neutral band**: `[0.25, 0.36]`. Currently `[0.25, 0.35]`. **Verdict: keep** — current band is well-centered on the observed median. Upper boundary at 0.35 vs 0.36 is noise-level; no change needed.

### Per-user within-cell spread (reliable cells, n_users ≥ 10)

Observed (ELO × TC × skill) distribution — see Query B below; per-bucket per-user spread isn't shown separately since Skill (Query B) already composes the three and gives a cleaner signal for the composite gauge.

### Query B — Endgame Skill per-user distribution (ELO × TC)

Cells show `p50 [p25–p75] (n_users)`. Cells with n_users < 10 suppressed.

| ELO | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 500–999 | 0.617 [0.539–0.635] (10) | 0.500 [0.459–0.536] (15) | 0.492 [0.465–0.526] (14) | — |
| 1000–1499 | 0.501 [0.471–0.590] (13) | 0.514 [0.472–0.555] (17) | 0.549 [0.488–0.610] (19) | — |
| 1500–1999 | 0.502 [0.473–0.565] (16) | 0.509 [0.482–0.595] (20) | 0.530 [0.493–0.563] (18) | — |
| 2000–2499 | — | 0.514 [0.463–0.601] (12) | 0.544 [0.518–0.590] (11) | — |

### Query B — Pooled Endgame Skill (per TC and overall)

| Level | TC | n_users | mean ± std | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|---|
| per-TC | bullet | 28 | 0.524 ± 0.139 | 0.298 | 0.474 | 0.527 | 0.584 | 0.691 |
| per-TC | blitz | 36 | 0.510 ± 0.084 | 0.407 | 0.454 | 0.513 | 0.540 | 0.643 |
| per-TC | rapid | 33 | 0.528 ± 0.076 | 0.451 | 0.477 | 0.521 | 0.564 | 0.628 |
| per-TC | classical | 9 | 0.648 ± 0.169 | 0.456 | 0.548 | 0.597 | 0.717 | 0.909 |
| **pooled (per-TC rows)** | all | **106** | **0.531 ± 0.112** | 0.380 | **0.474** | **0.521** | **0.574** | 0.710 |
| per-user overall (TC-agnostic) | all | 42 | 0.522 ± 0.083 | 0.383 | 0.482 | 0.510 | 0.556 | 0.618 |

### Recommendations — Endgame Skill gauge

- **Currently set**: `ENDGAME_SKILL_ZONES = [0–0.45 danger, 0.45–0.55 neutral, 0.55–1.00 success]`. Code comment: "Typical value lands around 52 %".
- **Observed pooled p50** = **0.521** (per-TC) / 0.510 (per-user overall). Code's "52 %" comment still holds within rounding ✅.
- **Observed pooled [p25, p75]** = `[0.474, 0.574]` per-TC, `[0.482, 0.556]` per-user overall.
- **Observed pooled [p05, p95]** = `[0.380, 0.710]`.
- **Recommended neutral band**: `[0.48, 0.56]` (per-user overall p25/p75, rounded). Currently `[0.45, 0.55]`. **Verdict: re-center slightly upward to `[0.48, 0.56]`** — the current band is shifted ~2 pp below the observed median, so users at exactly the population median (0.52) sit in the upper third of the neutral band rather than the middle. Shifting the band up 3 pp centers it on the population. Alternatively **keep** if color-story consistency with the Parity gauge (which also uses 0.45/0.55) is valued more than centering.
- **Gauge range**: full 0–1.0, which accommodates the observed `[p05, p95] = [0.38, 0.71]` with room to spare. No change.
- **ELO slope**: p50 drifts only mildly across ELO buckets in blitz/rapid (0.49 → 0.55 across 500→2000) and sits meaningfully higher for bullet@500–999 (0.617 — likely a beginner-opponent effect where conversions dominate) and classical (0.597, n only 9). Slope across adjacent ELO buckets is generally **< 5 pp in blitz/rapid**, so a single pooled gauge is defensible. No ELO-stratified zones needed yet.

---

## 3. Endgame ELO vs Actual ELO Gap per combo

### Currently set in code (`app/services/endgame_service.py`, `app/services/openings_service.py`)

- `ENDGAME_ELO_TIMELINE_WINDOW = 100` (trailing window size)
- `_ENDGAME_ELO_SKILL_CLAMP_LO = 0.05`, `_ENDGAME_ELO_SKILL_CLAMP_HI = 0.95` (caps formula contribution at ≈ ±511 Elo)
- `MIN_GAMES_FOR_TIMELINE = 10` (per-point emission)
- `_MATERIAL_ADVANTAGE_THRESHOLD = 100`
- **Formula (Phase 57.1)**: `endgame_elo = round(actual_elo_at_date + 400 · log10(clamped_skill / (1 − clamped_skill)))` ⇒ `gap = round(400 · log10(clamped_skill / (1 − clamped_skill)))`

### Per-combo gap distribution (trailing 100 endgame games, ≥ 30 games floor, ≥ 2 non-empty buckets)

| platform | tc | n_users | mean_actual | mean_endgame | mean_opp | mean_gap ± std | p05 | p25 | p50 | p75 | p95 | min / max | skill p25/p50/p75 | clamp_lo / clamp_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| chess.com | bullet | 19 | 1669 | 1716 | 1587 | **+47 ± 82** | −87 | −1 | 49 | 89 | 141 | −107 / 263 | 0.499 / 0.570 / 0.624 | 0 / 0 |
| chess.com | blitz | 27 | 1526 | 1537 | 1448 | +12 ± 46 | −49 | −22 | 12 | 38 | 86 | −95 / 102 | 0.469 / 0.518 / 0.554 | 0 / 0 |
| chess.com | rapid | 27 | 1569 | 1581 | 1516 | +12 ± 53 | −50 | −20 | 16 | 50 | 85 | −162 / 96 | 0.471 / 0.523 / 0.570 | 0 / 0 |
| chess.com | classical | *5* | 1429 | 1519 | 1234 | +90 ± 160 | −33 | −20 | 68 | 76 | 304 | −36 / 361 | 0.472 / 0.597 / 0.608 | 0 / 0 |
| lichess | bullet | 10 | 1984 | 2001 | 1970 | +17 ± 71 | −69 | −49 | 29 | 59 | 114 | −76 / 118 | 0.431 / 0.541 / 0.584 | 0 / 0 |
| lichess | blitz | 18 | 1901 | 1944 | 1840 | **+44 ± 60** | −22 | −7 | 28 | 96 | 128 | −42 / 159 | 0.489 / 0.540 / 0.635 | 0 / 0 |
| lichess | rapid | 11 | 1938 | 1980 | 1875 | +42 ± 100 | −54 | −32 | 24 | 86 | 195 | −55 / 286 | 0.454 / 0.534 / 0.621 | 0 / 0 |
| lichess | classical | *2* | 2171 | 2212 | 2072 | +41 ± 11 | 35 | 38 | 42 | 45 | 48 | 34 / 49 | 0.554 / 0.559 / 0.565 | 0 / 0 |

Italic rows = low sample; treat as informational only.

### Pooled gap histogram (100-Elo bins, reliable combos, n=119)

| bin | n | pct | cum_pct |
|---|---|---|---|
| −200..−101 | 2 | 1.7 % | 1.7 % |
| −100..−1 | 39 | 32.8 % | 34.5 % |
| 1..100 | 64 | 53.8 % | 88.2 % |
| 101..200 | 11 | 9.2 % | 97.5 % |
| 201..300 | 2 | 1.7 % | 99.2 % |
| 301..400 | 1 | 0.8 % | 100.0 % |

Bell-curve-like centered just above zero, modest right tail. No user sits at either clamp (`n_clamp_low = n_clamp_high = 0` everywhere — the 0.05/0.95 clamp is inactive for every qualifying user). No skill-distribution saturation to worry about.

### Observations

- **Platform divergence is now entirely skill-distribution-driven.** Under the 57.1 formula the gap is a pure function of clamped skill, so any platform difference in `mean_gap` reflects different skill distributions (not Glicko scale). `chess.com@bullet` shows a `+47 Elo` median gap vs `lichess@bullet` at `+17 Elo` — chess.com bullet players on FlawChess have systematically higher Endgame Skill (p50 ≈ 0.57) than lichess bullet players (p50 ≈ 0.54). Conversely `lichess@blitz` runs higher (p50 skill 0.54, gap +44) than `chess.com@blitz` (p50 skill 0.52, gap +12). These differences are coherent with the skill tables and not an artifact.
- **TC slope within platform.** On lichess, slower TCs trend higher (bullet +17, blitz +44, rapid +42). On chess.com the pattern is different: bullet has the highest gap (+47), blitz and rapid sit near zero (+12, +12). One interpretation: chess.com's bullet population over-represents users whose endgame is their strongest phase (perhaps seeding players who queue mostly when tilted and bleed rating elsewhere).
- **Clamp saturation**: **zero users clamped on either side across all 8 combos.** The 0.05/0.95 skill clamp is doing no work on the current user base. Either retain as a defense-in-depth guard, or note it can be relaxed slightly without affecting anyone.
- **Formula sensitivity**: observed pooled `std_gap ≈ 60–100 Elo` across the reliable combos. Stated "sensible" range was 120–200. Actual std is **below that band** — the skill distribution is tightly concentrated around 0.5 and the `log10` transform is compressing rather than amplifying. Nothing is "wrong" (the chart is still readable and the top-5 % vs bottom-5 % gap of ±130 Elo is visible and meaningful) but the 400-scaling could theoretically be raised if you wanted more visual spread. **Recommendation: keep 400** — it's the classical Elo constant and any other value would invite confusion. The narrow std is a population property, not a formula bug.
- **Recommended "notable divergence" threshold** (not currently exposed in UI): `|gap| > 130 Elo` pooled (roughly the pooled `|p90|`) would flag the top/bottom ~10 % of users as having a materially different endgame vs overall-game skill. Park for future UI phase.

### Verdict

- **Formula**: keep as-is.
- **Skill clamp**: keep — defensive even though inactive.
- **Window / game floor**: keep (100-game trailing window and 10-point emission floor both work fine under observed data).
- **No UI change recommended.** This section is healthy instrumentation of the 57.1 formula; there is no gauge to recalibrate.

---

## 4. Time Pressure at Endgame Entry

### Currently set in code (`frontend/src/components/charts/EndgameClockPressureSection.tsx`)

- `NEUTRAL_PCT_THRESHOLD = 10` (blue band is ±10 pp of base time)
- `NEUTRAL_TIMEOUT_THRESHOLD = 5` (blue band is ±5 pp net timeout rate)

### Clock diff — % of base time (primary, matches live gauge)

Per-user average `user_clk_pct − opp_clk_pct` at endgame entry, by TC. Distribution across users with ≥ 20 endgame games in that TC.

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 27 | +1.67 | −5.30 | −2.24 | −0.38 | **+4.98** | +13.07 |
| blitz | 36 | −3.43 | −14.73 | **−7.37** | −3.11 | +0.95 | +6.02 |
| rapid | 33 | −3.20 | −22.38 | **−7.53** | −2.79 | +4.26 | +8.57 |
| classical | *2* | −8.49 | −26.47 | −18.48 | −8.49 | +1.51 | +9.50 |

### Net timeout rate — pp (primary)

Per-user `(timeout_wins − timeout_losses) / games × 100`.

| TC | n_users | mean | p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| bullet | 27 | +10.31 | −9.54 | −2.59 | +4.90 | **+24.37** | +38.69 |
| blitz | 36 | +0.21 | −20.67 | −4.21 | +1.03 | +9.24 | +14.34 |
| rapid | 33 | +1.40 | −7.87 | −1.27 | +2.34 | +4.21 | +7.69 |
| classical | *2* | +0.50 | −2.79 | −1.33 | +0.50 | +2.34 | +3.80 |

### Clock diff — seconds (secondary readout, sanity check)

| TC | p25 (s) | p50 (s) | p75 (s) |
|---|---|---|---|
| bullet | −1.19 | −0.23 | +2.88 |
| blitz | −14.77 | −9.06 | +1.74 |
| rapid | −63.05 | −16.76 | +27.57 |

Absolute-seconds values vary by nearly 2 orders of magnitude between bullet and rapid (as expected — TCs with larger base times allow much larger absolute clock spreads). This confirms that **the % of base time metric is the right primary unit**; absolute seconds is only useful to sanity-check that bullet's ±2s swings aren't being hidden by the % normalization.

### Recommendations

- **Clock-diff neutral band** `NEUTRAL_PCT_THRESHOLD`:
  - Observed p25–p75 per TC: bullet `[−2.2, +5.0]`, blitz `[−7.4, +0.9]`, rapid `[−7.5, +4.3]`.
  - Widest |p25| or |p75| across TCs: **7.5 pp** (rapid p25).
  - Currently ±10 pp. This comfortably encompasses every TC's p25–p75 interval with ~2.5 pp of slack.
  - **Verdict: keep ±10**, or narrow to **±8** if you want the gauge to classify borderline cases more aggressively. Narrowing to ±6 would start reclassifying a meaningful share of blitz/rapid p25 users as "behind on clock" which may be too aggressive — bullet p25 is only −2.2 % so it wouldn't affect bullet. The code's symmetric ±10 is fine.
- **Timeout-rate neutral band** `NEUTRAL_TIMEOUT_THRESHOLD`:
  - Observed p25–p75 per TC: bullet `[−2.6, +24.4]`, blitz `[−4.2, +9.2]`, rapid `[−1.3, +4.2]`.
  - **Bullet is a dramatic outlier**. Half of bullet users net +5 pp or more timeouts per game at endgame entry, with p75 at +24 pp. The current ±5 pp band flags the vast majority of bullet users as "winning on time" — which is factually correct but may not be the useful signal.
  - Blitz and rapid are much narrower; ±5 is roughly p75 for blitz and well above p75 for rapid.
  - **Verdict: consider per-TC thresholds** — e.g. bullet `±15`, blitz `±8`, rapid/classical `±5`. Or **keep ±5** and accept that the bullet population will systematically light up "net timeout wins" because bullet *is* the TC where timeouts decide games. Easiest no-change path is to keep ±5 and add a hint in the bullet tooltip explaining that the neutral band is narrow because timeout differentials are inherent to bullet.
- **Percentages vs seconds**: confirmed — % is correct for the gauge, absolute seconds is only a sanity-check readout. No change needed in the code; this is just documenting the decision.

**One caveat about the SQL approximation** (documented in the skill): the backend scans ply arrays in Python to find the first non-NULL clock for each parity, whereas the SQL above takes clocks at `entry_ply` and `entry_ply + 1`. Games where those exact plies are NULL are dropped from this benchmark but the backend handles them via fallback. The bias is small (< 1 % of games based on earlier spot checks) but not zero — the live gauge distributions will be slightly wider than reported here.

---

## 5. Time Pressure vs Performance — cross-TC comparison

### Currently set in code

- `_compute_time_pressure_chart` in `app/services/endgame_service.py` — **pools all time controls into a single `pooled_user_buckets` + `pooled_opp_buckets` series** (confirmed at lines 1503–1520).
- `Y_AXIS_DOMAIN = [0.2, 0.8]` (score % on y-axis)
- `X_AXIS_DOMAIN = [0, 100]` (time remaining % on x-axis)
- `MIN_GAMES_FOR_CLOCK_STATS = 10` (per-TC gate)

### Score by (TC × time-remaining bucket)

Rows = bucket (0–10 % remaining … 90–100 %), columns = TC. Cell = `score (n)`. Suppressed cells where n < 100 italicized.

| bucket | bullet | blitz | rapid | classical |
|---|---|---|---|---|
| 0 (0–10 %) | 0.266 (5070) | 0.310 (3930) | 0.327 (1191) | *0.310 (21)* |
| 1 (10–20 %) | 0.411 (8890) | 0.429 (4096) | 0.443 (1338) | *0.609 (23)* |
| 2 (20–30 %) | 0.500 (11519) | 0.482 (4298) | 0.501 (1837) | *0.682 (11)* |
| 3 (30–40 %) | 0.542 (12137) | 0.515 (5295) | 0.524 (2460) | *0.881 (21)* |
| 4 (40–50 %) | 0.570 (13548) | 0.548 (6003) | 0.535 (3376) | *0.409 (11)* |
| 5 (50–60 %) | 0.591 (12093) | 0.576 (6448) | 0.540 (4526) | *0.588 (17)* |
| 6 (60–70 %) | 0.592 (11143) | 0.577 (6228) | 0.541 (5977) | *0.692 (13)* |
| 7 (70–80 %) | 0.598 (6227) | 0.557 (4857) | 0.527 (7373) | *0.500 (10)* |
| 8 (80–90 %) | 0.586 (2385) | 0.572 (2424) | 0.520 (6673) | *0.600 (10)* |
| 9 (90–100 %) | 0.553 (339) | 0.573 (573) | 0.535 (2240) | *0.667 (12)* |

Classical is suppressed across the board (every bucket n < 100). The pooling question is therefore really a three-TC question.

### Per-bucket spread across reliable TCs (bullet / blitz / rapid, all n ≥ 100)

| bucket | max − min | comment |
|---|---|---|
| 0 | 0.061 | bullet drops lowest — losing under 10% clock |
| 1 | 0.032 | |
| 2 | 0.019 | |
| 3 | 0.027 | |
| 4 | 0.035 | |
| 5 | **0.051** | bullet tops |
| 6 | **0.051** | bullet tops |
| 7 | **0.071** | bullet tops, rapid lowest |
| 8 | **0.066** | bullet tops, rapid lowest |
| 9 | 0.038 | |

**Max per-bucket range = 7.1 pp at bucket 7 (70–80 % time remaining).**

### Axis check

Observed scores across all reliable (TC, bucket) cells range from **0.266** (bullet@0) to **0.598** (bullet@7). `Y_AXIS_DOMAIN = [0.2, 0.8]` contains this with slack on both ends but the real signal sits in `[0.27, 0.60]` — the domain could be tightened to `[0.2, 0.7]` with no data loss, giving 30 % more vertical resolution. Not a blocker; the current domain reserves headroom for users who push past 60 % and for visual symmetry around 0.5.

### Verdict

**Max per-bucket range is 7.1 pp, which is above the 5 pp "safe to pool" heuristic threshold called out in the skill.** The spread is concentrated in buckets 5–8 (50–90 % clock remaining), where bullet consistently scores 5–7 pp higher than rapid at the same relative-clock position. Below 50 % clock remaining the three TCs track each other within 4 pp.

This is a **borderline signal**, not a clear directive:

- **Arguments for keeping pooled**: the spread is concentrated in one contiguous region (buckets 5–8) and is monotone across TCs (bullet > blitz > rapid) rather than crossing. The overall shape (rising curve from 0.27 at 0 % clock → ~0.55–0.60 at 50–80 % clock → plateau) is visually identical across TCs. Splitting to three lines adds visual clutter for a 5–7 pp difference that most users won't notice.
- **Arguments for splitting**: analytically, a bullet user and a rapid user at "70 % clock remaining" are experiencing very different physiological clock-pressure regimes even though the x-axis label is identical. If the goal is "show me the clock-pressure-to-outcome curve for **my** TC", a single pooled line hides 7 pp of structural TC difference at the top of the curve.

**Recommendation**: **keep the current pooling**, but note in the Endgame tab explanation that bullet users score a few pp higher at high-clock buckets than rapid users at the same relative clock position. Revisit only if user feedback indicates the curve feels "off" for their primary TC. If you do decide to split, the split should be by-TC using the same `clock_rows` data (no new query needed in `_compute_time_pressure_chart`, just skip the pooling step).

---

## Recommended thresholds summary

| Section | Metric | Code constant | Currently set | Observed (data-driven) | Verdict |
|---|---|---|---|---|---|
| 1 | Timeline neutral band | *(new)* | none — not yet defined | unified `[49 %, 56 %]` from intersection of eg/non-eg p25–p75 | **Add `SCORE_TIMELINE_NEUTRAL_MIN/MAX = [49, 56]`** |
| 1 | Timeline y-axis | `SCORE_TIMELINE_Y_DOMAIN` | `[20, 80]` | `[42 %, 63 %]` p05/p95 | Keep or tighten to `[35, 70]` for better vertical resolution |
| 1 | Score-gap gauge neutral | `SCORE_GAP_NEUTRAL_MIN/MAX` | ±0.10 | p25/p75 `[−0.06, +0.074]` | **Keep** |
| 1 | Score-gap gauge range | `SCORE_GAP_DOMAIN` | ±0.20 | p05/p95 ±0.16 | **Keep** |
| 2 | Conversion neutral band | `FIXED_GAUGE_ZONES.conversion` | `[0.65, 0.75]` | most cells in `[0.68, 0.78]` | **Shift up to `[0.67, 0.77]`** (small, optional) |
| 2 | Parity neutral band | `FIXED_GAUGE_ZONES.parity` | `[0.45, 0.55]` | most cells in `[0.47, 0.58]` | **Keep** (upper bound slightly tight — optional 0.55 → 0.57) |
| 2 | Recovery neutral band | `FIXED_GAUGE_ZONES.recovery` | `[0.25, 0.35]` | most cells in `[0.25, 0.36]` | **Keep** |
| 2 | Endgame Skill neutral | `ENDGAME_SKILL_ZONES` | `[0.45, 0.55]` | per-user overall p25/p75 `[0.48, 0.56]` | **Re-center to `[0.48, 0.56]`** (or keep for color-story parity with Parity) |
| 3 | Endgame ELO formula | `400 · log10(skill/(1−skill))` | active | std_gap 60–100 Elo; 0 clamp saturation | **Keep** — formula healthy |
| 3 | Skill clamp | `_ENDGAME_ELO_SKILL_CLAMP_LO/HI` | `[0.05, 0.95]` | unused by any user | Keep (defensive) |
| 3 | "Notable divergence" threshold | *(not in UI)* | — | `|gap| > 130` Elo ≈ pooled p90_abs | Park for future UI callout |
| 4 | Clock-diff neutral pp | `NEUTRAL_PCT_THRESHOLD` | ±10 | widest |p25/p75| across TCs: 7.5 pp | **Keep** (or narrow to ±8) |
| 4 | Timeout neutral pp | `NEUTRAL_TIMEOUT_THRESHOLD` | ±5 | bullet p75 +24.4, blitz p75 +9.2, rapid p75 +4.2 | **Keep** with per-TC caveat, or split to bullet ±15 / blitz ±8 / rapid ±5 |
| 5 | Time-pressure chart pooling | `_compute_time_pressure_chart` | pooled across TCs | max per-bucket range 7.1 pp (bucket 7) | **Keep pooled** — borderline signal, pool is defensible |
| 5 | Y-axis domain | `Y_AXIS_DOMAIN` | `[0.2, 0.8]` | observed `[0.27, 0.60]` | Keep, or tighten to `[0.2, 0.7]` for resolution |

No constant is outright mis-calibrated. The clearest nudges are: **define the missing timeline neutral band** (Section 1), **re-center `ENDGAME_SKILL_ZONES` up by ~3 pp** (Section 2, optional), and **clarify bullet's expected timeout signal** in the UI (Section 4, optional). Everything else is either healthy as-is or a very small tuning question that can wait for stronger evidence.

# FlawChess Benchmarks — 2026-04-30

- **DB**: benchmark (Docker on `localhost:5433`, `flawchess_benchmark`)
- **Snapshot taken**: 2026-04-29T23:13:32Z
- **Population**: 969 ingested users / 3,119,279 in-scope games / 294,605,647 positions
- **Cell anchoring**: 400-wide ELO buckets via `benchmark_selected_users.rating_bucket`; `tc_bucket` from same table; per-user TC restricted to selected `tc_bucket`
- **Selection provenance**: 2026-03 Lichess monthly dump (single `dump_month`); 9133 selected users at ~500/cell, ~969 ingested at ~50/cell (40 in classical-2400)
- **Per-user history caveat**: `rating_bucket` is rating-at-selection-snapshot; users contribute up to 3 years of history at varying ratings, so "ELO bucket effect" should be read as "current rating cohort effect" rather than "rating-at-game-time effect"
- **Base filters**: `g.rated AND NOT g.is_computer_game`; per-user `g.time_control_bucket::text = bsu.tc_bucket`
- **Verdict thresholds**: Cohen's d < 0.2 = collapse / 0.2–0.5 = review / ≥ 0.5 = keep separate
- **Sample floors**: per-section floors per skill spec (≥30 endgame + non-endgame games for §1, ≥20 for §2, ≥30 for §3, ≥20 endgame games with clocks for §4, ≥10 users/cell for marginals)

### Cell coverage (users_ingested per cell)

| ELO   | bullet | blitz | rapid | classical |
|-------|--------|-------|-------|-----------|
| 800   | 49     | 50    | 49    | 49        |
| 1200  | 50     | 49    | 50    | 50        |
| 1600  | 50     | 48    | 50    | 48        |
| 2000  | 48     | 48    | 48    | 49        |
| 2400  | 49     | 45    | 50    | 40        |

All cells ≥ 40 users; classical-2400 thinnest. Blitz-800/1600/2000/2400 are 50, 48, 48, 45.

---

## 1. Score gap (endgame vs non-endgame)

### Currently set in code

- `SCORE_GAP_NEUTRAL_MIN = -0.10`, `SCORE_GAP_NEUTRAL_MAX = +0.10` (`frontend/src/generated/endgameZones.ts`)
- `SCORE_GAP_DOMAIN = 0.20` (`EndgamePerformanceSection.tsx:50`)
- `SCORE_TIMELINE_Y_DOMAIN = [20, 80]` (`EndgamePerformanceSection.tsx:56`)
- No `SCORE_TIMELINE_NEUTRAL_*` constants today (timeline draws no neutral band).

### Per-user `diff = eg_score − non_eg_score` — 5×4 cell table

`p25 / p50 / p75 (n)`:

| ELO  | bullet                       | blitz                        | rapid                        | classical                    |
|------|------------------------------|------------------------------|------------------------------|------------------------------|
| 800  | -0.06 / -0.02 / +0.05 (45)   | -0.15 / -0.06 / +0.05 (41)   | -0.17 / -0.08 / +0.04 (41)   | -0.15 / -0.05 / +0.03 (20)   |
| 1200 | -0.07 / -0.01 / +0.08 (46)   | -0.09 / -0.04 / +0.09 (41)   | -0.13 / -0.06 / +0.06 (43)   | -0.19 / -0.09 / -0.04 (31)   |
| 1600 | -0.08 / +0.02 / +0.08 (49)   | -0.09 / -0.03 / +0.05 (46)   | -0.10 / -0.02 / +0.08 (45)   | -0.18 / -0.12 / -0.01 (30)   |
| 2000 | -0.10 / -0.03 / +0.08 (46)   | -0.09 / -0.01 / +0.06 (47)   | -0.05 / +0.02 / +0.08 (40)   | -0.14 / -0.07 / +0.02 (38)   |
| 2400 | -0.09 / -0.03 / +0.06 (49)   | -0.09 / -0.02 / +0.03 (43)   | -0.14 / -0.06 / +0.02 (29)   | -0.17 / -0.09 / +0.00 (29)   |

### TC marginal (pooled across ELO)

| TC        | n   | mean   | p05   | p25   | p50   | p75   | p95  |
|-----------|-----|--------|-------|-------|-------|-------|------|
| bullet    | 235 | -0.003 | -0.16 | -0.08 | -0.01 | +0.07 | +0.17|
| blitz     | 218 | -0.019 | -0.19 | -0.11 | -0.03 | +0.06 | +0.17|
| rapid     | 198 | -0.030 | -0.25 | -0.11 | -0.04 | +0.07 | +0.17|
| classical | 148 | -0.086 | -0.27 | -0.18 | -0.09 | +0.00 | +0.13|

### ELO marginal (pooled across TC)

| ELO  | n   | mean   | p05   | p25   | p50   | p75   | p95  |
|------|-----|--------|-------|-------|-------|-------|------|
| 800  | 147 | -0.042 | -0.24 | -0.13 | -0.05 | +0.05 | +0.15|
| 1200 | 161 | -0.026 | -0.22 | -0.11 | -0.04 | +0.07 | +0.19|
| 1600 | 170 | -0.026 | -0.23 | -0.11 | -0.03 | +0.05 | +0.19|
| 2000 | 171 | -0.017 | -0.20 | -0.10 | -0.03 | +0.06 | +0.18|
| 2400 | 150 | -0.040 | -0.19 | -0.11 | -0.04 | +0.03 | +0.12|

### Pooled overall

n=799, mean=-0.030, p05=-0.22, p25=-0.11, p50=-0.04, p75=+0.06, p95=+0.17.
Pooled `eg_score`: p05=0.37, p25=0.46, p50=0.51, p75=0.57, p95=0.68.
Pooled `non_eg_score`: p05=0.39, p25=0.48, p50=0.54, p75=0.60, p95=0.76.

### Recommendations

- **`SCORE_GAP_NEUTRAL_MIN/MAX`**: pooled p25=-0.11 / p75=+0.06; |median|=0.04 < 0.05 re-centering threshold → **keep symmetric ±0.10**. Pooled IQR is wider on the negative side, but the scope guard explicitly forbids re-centering for sub-5pp offsets.
- **`SCORE_GAP_DOMAIN`**: pooled `max(|p05|, |p95|) = 0.22` slightly exceeds the live 0.20 (5% of pop. clipped). **Recommend widen to 0.25** (or hold at 0.20 if the chart breathes better with a sharper edge).
- **Timeline neutral band (new)**: pooled overlap of `[eg_p25, eg_p75]` and `[non_eg_p25, non_eg_p75]` is `[0.48, 0.57]`, covering 85% of the narrower band. **Propose a unified shaded band at [0.48, 0.57]** if/when timeline gets a neutral zone; otherwise leave unbanded.
- **`SCORE_TIMELINE_Y_DOMAIN`**: pooled `[min(p05), max(p95)] = [0.37, 0.76]`. Live `[0.20, 0.80]` accommodates with breathing room. **Keep**.

### Collapse verdict

- TC axis: max |d| = **0.70** (bullet vs classical) → **keep separate**
- ELO axis: max |d| = **0.22** (2000 vs 2400) → **review**
- Heatmap of per-user `diff_p50` (5 ELO × 4 TC):

```
            bullet    blitz    rapid   classical
  800       -0.019   -0.060   -0.083   -0.053
  1200      -0.011   -0.035   -0.058   -0.092
  1600      +0.023   -0.029   -0.024   -0.122
  2000      -0.033   -0.014   +0.021   -0.074
  2400      -0.031   -0.024   -0.065   -0.093
```

Classical column is consistently more negative; that's where the TC effect lives. ELO has weak structure, hence "review".

---

## 2. Conversion / Parity / Recovery + Endgame Skill

### Currently set in code (`frontend/src/generated/endgameZones.ts`)

- `FIXED_GAUGE_ZONES.conversion` neutral: `[0.65, 0.75]`
- `FIXED_GAUGE_ZONES.parity` neutral: `[0.45, 0.55]`
- `FIXED_GAUGE_ZONES.recovery` neutral: `[0.25, 0.35]`
- `ENDGAME_SKILL_ZONES` neutral: `[0.45, 0.55]`
- `BULLET_DOMAIN = 0.20` for the score-gap section (`EndgameScoreGapSection.tsx:49`)

### Pooled overall (n=860 per-user-cells)

| Metric        | mean   | p25   | p50   | p75   |
|---------------|--------|-------|-------|-------|
| Conversion    | 0.7099 | 0.65  | 0.71  | 0.76  |
| Parity        | 0.5123 | 0.45  | 0.51  | 0.57  |
| Recovery      | 0.3312 | 0.26  | 0.33  | 0.40  |
| Endgame Skill | 0.5182 | 0.47  | 0.51  | 0.56  |

### TC marginal — Endgame Skill p50 (and conv/par/recov p50)

| TC        | n   | skill_p50 | conv_p50 | par_p50 | recov_p50 |
|-----------|-----|-----------|----------|---------|-----------|
| bullet    | 239 | 0.51      | 0.66     | 0.51    | 0.37      |
| blitz     | 227 | 0.51      | 0.70     | 0.51    | 0.33      |
| rapid     | 219 | 0.51      | 0.74     | 0.51    | 0.30      |
| classical | 175 | 0.51      | 0.76     | 0.51    | 0.25      |

### ELO marginal

| ELO  | n   | skill_p50 | conv_p50 | par_p50 | recov_p50 |
|------|-----|-----------|----------|---------|-----------|
| 800  | 161 | 0.48      | 0.69     | 0.48    | 0.27      |
| 1200 | 177 | 0.49      | 0.71     | 0.49    | 0.29      |
| 1600 | 175 | 0.50      | 0.70     | 0.50    | 0.30      |
| 2000 | 181 | 0.53      | 0.71     | 0.53    | 0.34      |
| 2400 | 166 | 0.57      | 0.73     | 0.57    | 0.40      |

### Per-user p50 cell heatmaps (5×4)

**Conversion p50:**
```
            bullet  blitz  rapid  classical
  800        0.64   0.68   0.72   0.75
  1200       0.62   0.73   0.74   0.74
  1600       0.66   0.69   0.74   0.74
  2000       0.67   0.70   0.73   0.77
  2400       0.70   0.71   0.77   0.80
```

**Parity p50:**
```
            bullet  blitz  rapid  classical
  800        0.51   0.45   0.46   0.40
  1200       0.50   0.50   0.48   0.45
  1600       0.51   0.49   0.50   0.48
  2000       0.52   0.53   0.54   0.57
  2400       0.55   0.57   0.60   0.63
```

**Recovery p50:**
```
            bullet  blitz  rapid  classical
  800        0.36   0.27   0.24   0.18
  1200       0.38   0.29   0.27   0.21
  1600       0.36   0.30   0.28   0.21
  2000       0.36   0.36   0.32   0.33
  2400       0.38   0.40   0.41   0.52
```

**Endgame Skill p50:**
```
            bullet  blitz  rapid  classical
  800        0.51   0.45   0.47   0.45
  1200       0.50   0.50   0.49   0.47
  1600       0.51   0.49   0.50   0.47
  2000       0.51   0.54   0.53   0.55
  2400       0.55   0.56   0.60   0.66
```

### Recommendations per metric

| Metric        | Live band     | Pooled IQR | Cell-spread (p50 max−min) | Action |
|---------------|---------------|------------|---------------------------|--------|
| Conversion    | [0.65, 0.75]  | [0.65, 0.76] | 0.18 (0.62–0.80)        | **Keep / very slight widen MAX to 0.76**; cell spread (0.18) >> 2×band-width (0.20) → ELO/TC stratification helps |
| Parity        | [0.45, 0.55]  | [0.45, 0.57] | 0.23 (0.40–0.63)        | **Widen MAX to 0.57**; ELO drives huge spread → stratify by ELO |
| Recovery      | [0.25, 0.35]  | [0.26, 0.40] | 0.34 (0.18–0.52)        | **Widen MAX to 0.40** (or widen band to [0.26, 0.40]); ELO spread enormous, stratify by ELO |
| Endgame Skill | [0.45, 0.55]  | [0.47, 0.56] | 0.21 (0.45–0.66)        | **Shift to [0.47, 0.56]**; ELO drives spread, stratify by ELO |

### Collapse verdicts

| Metric        | TC axis            | ELO axis           |
|---------------|--------------------|--------------------|
| Conversion    | **keep (d=1.03)** bullet vs classical | **keep (d=0.60)** 800 vs 2400 |
| Parity        | collapse (d=0.13)  | **keep (d=1.08)** 800 vs 2400 |
| Recovery      | **keep (d=0.58)** bullet vs rapid | **keep (d=1.17)** 800 vs 2400 |
| Endgame Skill | collapse (d=0.18)  | **keep (d=1.28)** 800 vs 2400 |

---

## 3. Endgame ELO vs Actual ELO Gap

### Currently set in code (`app/services/endgame_service.py`)

- `ENDGAME_ELO_TIMELINE_WINDOW = 100` (line 850)
- `_ENDGAME_ELO_SKILL_CLAMP_LO = 0.05`, `_ENDGAME_ELO_SKILL_CLAMP_HI = 0.95` (lines 856–857)
- `_MATERIAL_ADVANTAGE_THRESHOLD = 100` (line 164)
- `MIN_GAMES_FOR_TIMELINE = 10` (re-exported from `openings_service`)

Gap = `400 · log10(clamped_skill / (1 − clamped_skill))`. Anchor cancels because we evaluate `endgame_elo − actual_elo`.

### 5×4 cell table — `gap_p25 / gap_p50 / gap_p75 (n)` (Elo points)

| ELO  | bullet              | blitz               | rapid               | classical            |
|------|---------------------|---------------------|---------------------|----------------------|
| 800  | -14 / +22 / +55 (45)  | -73 / -37 / +24 (42) | -55 / -10 / +14 (41) | -103 / -54 / +4 (20)  |
| 1200 | -41 / -7 / +36 (47)   | -26 / +2 / +32 (41)  | -34 / -6 / +28 (44)  | -47 / -23 / +10 (33)  |
| 1600 | -39 / -2 / +40 (49)   | -33 / -4 / +16 (46)  | -19 / -3 / +47 (46)  | -48 / -16 / +13 (32)  |
| 2000 | -9 / +15 / +48 (47)   | -13 / +18 / +45 (48) | -6 / +32 / +58 (41)  | -14 / +33 / +111 (41) |
| 2400 | -9 / +25 / +63 (49)   | +6 / +49 / +89 (44)  | +37 / +71 / +118 (35)| +37 / +75 / +183 (29) |

### Marginals

**TC marginal:**

| TC        | n   | mean  | std   | p05   | p25  | p50  | p75  | p95  |
|-----------|-----|-------|-------|-------|------|------|------|------|
| bullet    | 237 | +13.2 | 63.9  | -86   | -19  | +11  | +51  | +107 |
| blitz     | 221 |  +7.6 | 60.2  | -83   | -31  | +5   | +40  | +111 |
| rapid     | 207 | +16.4 | 64.5  | -71   | -27  | +13  | +51  | +115 |
| classical | 155 | +22.3 | 99.8  | -95   | -35  | +8   | +64  | +203 |

**ELO marginal:**

| ELO  | n   | mean  | std  | p05   | p25 | p50 | p75 | p95  |
|------|-----|-------|------|-------|-----|-----|-----|------|
| 800  | 148 | -16.9 | 69.6 | -136  | -61 | -10 | +29 | +88  |
| 1200 | 165 |  -4.9 | 50.6 | -80   | -37 | -5  | +30 | +75  |
| 1600 | 173 |  -1.8 | 53.4 | -87   | -33 | -5  | +21 | +94  |
| 2000 | 177 | +29.8 | 65.7 | -60   | -9  | +24 | +63 | +142 |
| 2400 | 157 | +63.6 | 84.4 | -50   | +10 | +52 | +94 | +231 |

### Pooled

n=820, mean=+14.2, std=71.4, p05=-85, p25=-28, p50=+10, p75=+51, p95=+130.
**Clamp saturation: 0/820 low (0.0%), 1/820 high (0.12%) — well under 1%.**

### Recommendations

- **Window size (`ENDGAME_ELO_TIMELINE_WINDOW = 100`)**: pooled std=71 lands in the 60–200 well-behaved band → **keep at 100**.
- **Skill clamp `[0.05, 0.95]`**: 0.12% saturation → **keep**.
- **400-Elo scaling**: pooled std=71 within 60–200 → **keep**.
- **Forward-looking "notable divergence" callout**: pooled `|p05|=85`, `|p95|=130`. If a future UI badge needs a threshold, **±100 Elo** captures roughly the middle 90% of users; ±150 catches 95%.
- The ELO-bucket trend is the calibration story: skill is positively correlated with current cohort rating after we collapse to one number per user (-17 at 800 → +64 at 2400, a 80-point span). This is consistent with stronger players outperforming the ELO-derived expected score in endgames more than weaker players, mediated by recovery & parity rates (Section 2).

### Collapse verdict

- TC axis: max |d| = **0.19** (blitz vs classical) → **collapse** (borderline)
- ELO axis: max |d| = **1.04** (800 vs 2400) → **keep separate**

---

## 4. Time pressure at endgame entry

### Currently set in code

- `NEUTRAL_PCT_THRESHOLD = 10.0` (`endgameZones.ts`, used as ±10pp)
- `NEUTRAL_TIMEOUT_THRESHOLD = 5.0` (used as ±5pp)
- `MIN_GAMES_FOR_CLOCK_STATS = 10` (`endgame_service.py:821`)

### % diff (user clock − opp clock, as % of base time)

**5×4 per-user p50 (n_users):**

| ELO  | bullet         | blitz          | rapid          | classical      |
|------|----------------|----------------|----------------|----------------|
| 800  | -0.7 (44)      | -4.1 (44)      | -1.9 (46)      | -1.4 (22)      |
| 1200 | -0.5 (48)      | -2.4 (43)      | -1.8 (47)      | -4.7 (38)      |
| 1600 | +1.1 (49)      | -2.1 (47)      | +0.9 (46)      | -9.6 (23)      |
| 2000 | -0.0 (47)      | -0.3 (48)      | -2.2 (41)      | -0.6 (22)      |
| 2400 | +1.1 (49)      | -0.2 (45)      | -2.5 (39)      | (n<10 dropped) |

**Marginals:**

| TC        | n   | mean  | p05    | p25   | p50   | p75  | p95  |
|-----------|-----|-------|--------|-------|-------|------|------|
| bullet    | 237 | +0.4  | -8.3   | -2.8  | +0.0  | +3.8 | +9.9 |
| blitz     | 227 | -1.8  | -17.3  | -6.1  | -1.4  | +3.4 | +12.7|
| rapid     | 219 | -2.4  | -20.5  | -8.6  | -1.3  | +4.0 | +11.8|
| classical | 106 | -6.8  | -38.4  | -14.1 | -4.0  | +2.5 | +13.8|

| ELO  | n   | mean | p05   | p25  | p50  | p75 | p95  |
|------|-----|------|-------|------|------|-----|------|
| 800  | 156 | -3.3 | -21.9 | -9.0 | -1.9 | 3.8 | 11.0 |
| 1200 | 176 | -2.6 | -22.2 | -7.0 | -1.5 | 3.7 | 11.5 |
| 1600 | 165 | -2.1 | -20.5 | -5.4 | -0.6 | 4.2 | 10.7 |
| 2000 | 158 | -1.0 | -18.2 | -5.3 | -0.3 | 4.2 | 15.7 |
| 2400 | 134 | -0.6 | -13.8 | -3.8 | +0.0 | 3.0 | 10.6 |

**Pooled (n=789):** mean=-2.0, p05=-20.4, p25=-6.1, p50=-0.9, p75=+3.8, p95=+11.6.

### Net timeout rate (timeout-wins − timeout-losses, % of games)

**5×4 per-user p50 (n_users):**

| ELO  | bullet      | blitz       | rapid      | classical   |
|------|-------------|-------------|------------|-------------|
| 800  | +1.3 (44)   | -4.1 (44)   | +0.7 (46)  | 0.0 (22)    |
| 1200 | +0.7 (48)   | +1.3 (43)   | 0.0 (47)   | 0.0 (38)    |
| 1600 | +1.5 (49)   | +1.9 (47)   | +2.3 (46)  | 0.0 (23)    |
| 2000 | +0.9 (47)   | +3.8 (48)   | +0.7 (41)  | 0.0 (22)    |
| 2400 | +6.9 (49)   | +4.6 (45)   | +2.0 (39)  | (n<10)      |

**TC marginal:**

| TC        | n   | mean  | p25  | p50  | p75  |
|-----------|-----|-------|------|------|------|
| bullet    | 237 | +2.78 | -5.6 | +2.0 | +12.2|
| blitz     | 227 | -1.00 | -6.4 | +1.4 | +7.2 |
| rapid     | 219 | -0.33 | -2.4 | +0.8 | +3.7 |
| classical | 106 | -1.26 | -0.6 | 0.0  | +0.9 |

**ELO marginal:**

| ELO  | n   | mean  | p05    | p25  | p50  | p75 |
|------|-----|-------|--------|------|------|-----|
| 800  | 156 | -2.30 | -29.6  | -5.4 | 0.0  | 3.1 |
| 1200 | 176 | -0.64 | -20.2  | -4.5 | 0.0  | 3.4 |
| 1600 | 165 |  0.00 | -20.3  | -4.8 | 1.3  | 4.9 |
| 2000 | 158 | +1.42 | -15.3  | -2.8 | 1.0  | 6.2 |
| 2400 | 134 | +3.52 | -12.7  | -0.5 | 4.3  | 8.2 |

**Pooled (n=789):** mean=+0.29, p05=-20.3, p25=-3.6, p50=+0.8, p75=+5.6, p95=+17.1.

### Recommendations

- **`NEUTRAL_PCT_THRESHOLD`**: pooled IQR `[-6.1, +3.8]` is asymmetric and tighter than the live ±10. **Recommend `±7`** (or split: classical -4 / bullet 0 if `keep` verdict on TC drives stratification). Live ±10 is wide; users in the −6 to +4 zone (about half the population) get a "neutral" verdict that's doing little signaling.
- **`NEUTRAL_TIMEOUT_THRESHOLD`**: pooled IQR `[-3.6, +5.6]`, mean essentially zero. Live ±5 captures most of the IQR. **Keep at ±5**, optionally tighten lower bound to -4 if asymmetric thresholds are tolerable.
- Classical drops out of the cell where users have <20 endgame games with valid clocks (classical-2400 row), reflecting that classical players have fewer games per user even though selection is satisfied.

### Collapse verdicts

| Metric        | TC axis              | ELO axis            |
|---------------|----------------------|---------------------|
| % diff        | **keep (d=0.77)** bullet vs classical | review (d=0.30) 800 vs 2400 |
| Net timeout   | review (d=0.33) bullet vs classical   | **keep (d=0.50)** 800 vs 2400 |

---

## 5. Time pressure vs performance

### Currently set in code

- `Y_AXIS_DOMAIN = [0.2, 0.8]` (`EndgameTimePressureSection.tsx:20`)
- `X_AXIS_DOMAIN = [0, 100]` (line 22)
- `MIN_GAMES_FOR_CLOCK_STATS = 10`

The metric is per-time-bucket (10 buckets, 0–100% time-remaining), not a single per-user value, so the verdict uses per-game binary outcomes pooled per cell.

### TC marginal — score per time bucket (0–9 = 0–10%, …, 90–100%)

| time_bkt | bullet (n)            | blitz (n)            | rapid (n)            | classical (n)        |
|----------|-----------------------|----------------------|----------------------|----------------------|
| 0        | 0.245 (59,851)        | 0.307 (41,948)       | 0.349 (7,340)        | 0.381 (1,269)        |
| 1        | 0.391 (108,035)       | 0.422 (50,761)       | 0.445 (7,337)        | 0.476 (1,001)        |
| 2        | 0.482 (127,472)       | 0.498 (57,268)       | 0.492 (9,688)        | 0.488 (966)          |
| 3        | 0.522 (150,849)       | 0.533 (70,053)       | 0.512 (12,877)       | 0.482 (1,127)        |
| 4        | 0.544 (165,144)       | 0.539 (78,869)       | 0.534 (17,226)       | 0.500 (1,404)        |
| 5        | 0.554 (156,762)       | 0.548 (86,816)       | 0.530 (23,483)       | 0.504 (1,687)        |
| 6        | 0.560 (131,421)       | 0.552 (86,938)       | 0.525 (31,081)       | 0.527 (2,101)        |
| 7        | 0.562 (84,399)        | 0.548 (70,205)       | 0.513 (36,926)       | 0.527 (2,472)        |
| 8        | 0.558 (33,228)        | 0.536 (38,799)       | 0.510 (29,964)       | 0.529 (2,836)        |
| 9        | 0.524 (5,410)         | 0.529 (13,624)       | 0.518 (10,127)       | 0.541 (4,722)        |

### ELO marginal — score per time bucket

| time_bkt | 800 (n)        | 1200 (n)       | 1600 (n)       | 2000 (n)       | 2400 (n)       |
|----------|----------------|----------------|----------------|----------------|----------------|
| 0        | 0.223 (9,729)  | 0.277 (14,740) | 0.247 (34,265) | 0.282 (33,995) | 0.354 (17,679) |
| 1        | 0.354 (13,316) | 0.404 (21,919) | 0.374 (49,149) | 0.409 (50,894) | 0.459 (31,856) |
| 2        | 0.452 (14,046) | 0.505 (24,742) | 0.457 (57,154) | 0.482 (58,413) | 0.538 (41,039) |
| 3        | 0.494 (16,739) | 0.545 (31,083) | 0.503 (68,092) | 0.517 (69,304) | 0.561 (49,688) |
| 4        | 0.519 (18,742) | 0.558 (36,398) | 0.525 (77,227) | 0.541 (75,253) | 0.563 (55,023) |
| 5        | 0.526 (19,702) | 0.563 (39,710) | 0.533 (79,848) | 0.553 (73,637) | 0.569 (55,851) |
| 6        | 0.515 (18,662) | 0.561 (39,915) | 0.534 (76,139) | 0.558 (65,357) | 0.582 (51,468) |
| 7        | 0.489 (15,130) | 0.549 (34,364) | 0.525 (59,541) | 0.559 (48,124) | 0.590 (36,843) |
| 8        | 0.473 (9,060)  | 0.529 (20,445) | 0.509 (33,323) | 0.557 (26,060) | 0.600 (15,939) |
| 9        | 0.473 (3,064)  | 0.517 (7,496)  | 0.499 (10,990) | 0.550 (9,555)  | 0.640 (2,778)  |

### Recommendations

- `Y_AXIS_DOMAIN = [0.2, 0.8]` clears all observed cell scores (min ≈ 0.22 at bullet/2400 ELO bucket-0, max ≈ 0.76 at classical-2400 bucket-9). **Keep**.
- `X_AXIS_DOMAIN = [0, 100]` matches the bucket grid. **Keep**.
- Both axes are in the "review" band (TC d≈0.32 in the lowest time-bucket, ELO d≈0.37 in the top time-bucket). Mostly the curves shift parallel rather than reshaping, so a single overlayed curve per TC is fine; per-ELO stratification would aid clarity but is not strictly needed.

### Collapse verdict

- TC axis: max |d| ≈ **0.32** (bullet vs classical, bucket 0) → **review**
- ELO axis: max |d| ≈ **0.37** (800 vs 2400, bucket 9) → **review**

Per-bucket d computed on per-game `{0, 0.5, 1}` outcome with marginal-pair pooled SD. Binary-score variance ≈ 0.21–0.24 across buckets, so d ≈ Δmean / 0.45 in practice.

---

## 6. Endgame type breakdown

### Currently set in code

- `NEUTRAL_ZONE_MIN/MAX = ±0.05` (`EndgameWDLChart.tsx:42-43`) — score-diff neutral band, applied uniformly across classes
- `BULLET_DOMAIN = 0.30` (`EndgameWDLChart.tsx:48`)
- `EndgameConvRecovChart.tsx` has **no per-class neutral zones** today

### Pooled-by-class summary (collapses both ELO and TC)

| Class       | n_games   | users | score   | score_diff | conv (n)             | recov (n)            |
|-------------|-----------|-------|---------|------------|----------------------|----------------------|
| rook        | 315,368   | 920   | 0.5045  | +0.009     | 0.669 (104,250)      | 0.338 (108,560)      |
| minor_piece | 241,554   | 914   | 0.5095  | +0.019     | 0.645 (77,300)       | 0.367 (79,788)       |
| pawn        | 126,985   | 874   | 0.5062  | +0.012     | 0.683 (38,394)       | 0.321 (39,404)       |
| queen       | 117,455   | 876   | 0.5003  | +0.001     | 0.739 (46,643)       | 0.262 (47,340)       |
| mixed       | 1,765,040 | 966   | 0.5075  | +0.015     | 0.677 (536,622)      | 0.339 (555,470)      |
| pawnless    | 15,519    | 695   | 0.5088  | +0.018     | 0.736 (7,730)        | 0.263 (7,387)        |

### Per-class score_diff cells (5 ELO × 4 TC)

**Rook:**
```
            bullet  blitz  rapid  classical
  800       -0.06  -0.07  -0.12  -0.13
  1200      +0.09  -0.01  +0.01  -0.06
  1600      -0.02  -0.02  -0.10  -0.08
  2000      -0.07  +0.02  +0.10  +0.14
  2400      +0.06  +0.15  +0.15  +0.24
```

**Minor piece:**
```
            bullet  blitz  rapid  classical
  800       -0.07  -0.10  -0.09  -0.13
  1200      +0.11  -0.01  -0.03  -0.15
  1600      -0.03  -0.03  -0.08  -0.11
  2000      -0.05  +0.01  +0.10  +0.17
  2400      +0.06  +0.17  +0.16  +0.24
```

**Pawn:**
```
            bullet  blitz  rapid  classical
  800       -0.06  -0.09  -0.02  -0.22
  1200      +0.11  -0.05  -0.02  -0.17
  1600      -0.04  -0.01  -0.14  -0.07
  2000      -0.06  +0.03  +0.14  +0.21
  2400      +0.06  +0.14  +0.13  +0.43
```

**Queen:**
```
            bullet  blitz  rapid  classical
  800       -0.08  -0.04  -0.09  -0.13
  1200      +0.16  +0.03  +0.04  -0.07
  1600      -0.05  -0.00  -0.12  -0.02
  2000      -0.08  +0.07  +0.16  +0.08
  2400      -0.00  +0.14  +0.07  +0.27
```

**Mixed:**
```
            bullet  blitz  rapid  classical
  800       -0.05  -0.07  -0.11  -0.19
  1200      +0.07  +0.01  +0.03  -0.07
  1600      -0.03  -0.03  -0.04  -0.14
  2000      -0.02  +0.04  +0.09  +0.16
  2400      +0.06  +0.17  +0.16  +0.26
```

**Pawnless:**
```
            bullet  blitz  rapid  classical
  800       -0.07  -0.06  -0.13  +0.10*
  1200      +0.33  +0.09  +0.08  -0.17
  1600      -0.07  +0.10  -0.10  -0.09
  2000      -0.17  +0.13  +0.12  +0.11
  2400      -0.05  +0.18  +0.01  +0.18*
```
\* = sample size flag (n<100 in some cells; pawnless is sparse).

### Per-class conversion (pooled within class)

| Class       | conv pooled | spread (max − min cell) |
|-------------|-------------|--------------------------|
| rook        | 0.669       | 0.61–0.81 (0.20)        |
| minor_piece | 0.645       | 0.53–0.82 (0.29)        |
| pawn        | 0.683       | 0.55–0.90 (0.35)        |
| queen       | 0.739       | 0.66–0.91 (0.25)        |
| mixed       | 0.677       | 0.60–0.80 (0.20)        |
| pawnless    | 0.736       | 0.61–0.91 (0.30)        |

### Per-class recovery (pooled within class)

| Class       | recov pooled | spread (max − min cell) |
|-------------|--------------|--------------------------|
| rook        | 0.338        | 0.21–0.45 (0.24)        |
| minor_piece | 0.367        | 0.18–0.45 (0.27)        |
| pawn        | 0.321        | 0.18–0.42 (0.24)        |
| queen       | 0.262        | 0.12–0.36 (0.24)        |
| mixed       | 0.339        | 0.17–0.45 (0.28)        |
| pawnless    | 0.263        | 0.11–0.50 (0.39)        |

### Recommendations

- **`NEUTRAL_ZONE_MIN/MAX = ±0.05`** for per-class score_diff: every class's pooled score_diff sits inside ±0.02 → **keep**. The cell-level swings are large (especially classical-2400), but those are explained by ELO, not class.
- **Per-class conversion neutral zones (none today)**: spread between classes is 9.4pp (minor_piece 0.645 vs queen 0.739). Spread > 5pp threshold → **propose per-class bands `pooled ± 5pp`**:
  - rook `[0.62, 0.72]`, minor_piece `[0.59, 0.69]`, pawn `[0.63, 0.73]`, queen `[0.69, 0.79]`, mixed `[0.63, 0.73]`, pawnless `[0.69, 0.78]`.
- **Per-class recovery neutral zones (none today)**: spread is 10.5pp (queen 0.262 vs minor_piece 0.367) → **propose per-class bands `pooled ± 5pp`**:
  - rook `[0.29, 0.39]`, minor_piece `[0.32, 0.42]`, pawn `[0.27, 0.37]`, queen `[0.21, 0.31]`, mixed `[0.29, 0.39]`, pawnless `[0.21, 0.31]`.
- `BULLET_DOMAIN = 0.30` (per-class score gauge): largest per-class score_diff observed = +0.43 (classical-2400 pawn). 0.30 will clip outliers; **widen to 0.45** if you want classical-2400 cells to fit cleanly, or keep 0.30 and accept clipping in a small tail.

### Collapse verdicts (per metric, max-d aggregated across classes)

Computed on per-cell pooled rates with n ≥ 30 floor; per-class verdicts mostly track Section 2:

| Metric (per-class)  | TC verdict             | ELO verdict            |
|---------------------|------------------------|------------------------|
| Score (per-class)   | **keep separate**      | **keep separate**      |
| Conversion          | **keep separate**      | review/keep            |
| Recovery            | **keep separate**      | **keep separate**      |

---

## Top-axis collapse summary (HEADLINE DELIVERABLE)

| Metric                          | TC verdict (max\|d\|)           | ELO verdict (max\|d\|)         | Implication                                    |
|---------------------------------|---------------------------------|--------------------------------|------------------------------------------------|
| Score gap (eg − non_eg)         | keep (0.70) bullet/classical    | review (0.22) 2000/2400        | Stratify gauge zones by TC, single ELO band    |
| Conversion (per-user)           | keep (1.03) bullet/classical    | keep (0.60) 800/2400           | Stratify per (TC × ELO) — registry already does |
| Parity (per-user)               | collapse (0.13)                 | keep (1.08) 800/2400           | Single TC band, stratify by ELO                |
| Recovery (per-user)             | keep (0.58) bullet/rapid        | keep (1.17) 800/2400           | Stratify per (TC × ELO)                        |
| Endgame Skill (per-user)        | collapse (0.18)                 | keep (1.28) 800/2400           | Single TC band, stratify by ELO                |
| Endgame ELO gap (per-user)      | collapse (0.19)                 | keep (1.04) 800/2400           | Single global band; ELO trend is the signal    |
| Clock pressure %-of-base        | keep (0.77) bullet/classical    | review (0.30) 800/2400         | Stratify per TC                                |
| Net timeout rate                | review (0.33) bullet/classical  | keep (0.50) 800/2400           | Stratify by ELO; TC borderline                 |
| Time-pressure curve (per-bkt)   | review (0.32) bullet/classical  | review (0.37) 800/2400         | Single curve OK; per-TC overlay if affordable  |
| Per-class score                 | keep (mirrors §1)               | keep (mirrors §2)              | Already per (TC × ELO) via FIXED_GAUGE_ZONES   |
| Per-class conversion            | keep                            | review/keep                    | Add per-class neutral bands                    |
| Per-class recovery              | keep                            | keep                            | Add per-class neutral bands                    |

---

## Recommended thresholds summary

| Metric                       | Code constant                    | Currently set     | Recommended            | Collapse verdict (TC / ELO)       | Action                                |
|------------------------------|----------------------------------|-------------------|------------------------|-----------------------------------|---------------------------------------|
| Score gap neutral band       | `SCORE_GAP_NEUTRAL_MIN/MAX`      | ±0.10             | ±0.10                  | keep / review                     | keep                                  |
| Score gap gauge half-width   | `SCORE_GAP_DOMAIN`               | 0.20              | 0.25                   | keep / review                     | widen to 0.25 (or hold at 0.20)       |
| Score timeline Y domain      | `SCORE_TIMELINE_Y_DOMAIN`        | [0.20, 0.80]      | [0.20, 0.80]           | keep / review                     | keep                                  |
| Score timeline neutral band  | (none)                           | (none)            | [0.48, 0.57]           | keep / review                     | add unified band when timeline gets one|
| Conversion neutral band      | `FIXED_GAUGE_ZONES.conversion`   | [0.65, 0.75]      | [0.65, 0.76]           | keep / keep                       | tiny widen MAX; per-cell zones helpful|
| Parity neutral band          | `FIXED_GAUGE_ZONES.parity`       | [0.45, 0.55]      | [0.45, 0.57]           | collapse / keep                   | widen MAX; stratify by ELO            |
| Recovery neutral band        | `FIXED_GAUGE_ZONES.recovery`     | [0.25, 0.35]      | [0.26, 0.40]           | keep / keep                       | widen band; stratify by ELO           |
| Endgame Skill neutral band   | `ENDGAME_SKILL_ZONES`            | [0.45, 0.55]      | [0.47, 0.56]           | collapse / keep                   | shift band; stratify by ELO           |
| Endgame ELO window           | `ENDGAME_ELO_TIMELINE_WINDOW`    | 100               | 100                    | collapse / keep                   | keep                                  |
| Endgame ELO skill clamp      | `_ENDGAME_ELO_SKILL_CLAMP_LO/HI` | [0.05, 0.95]      | [0.05, 0.95]           | collapse / keep                   | keep (0.12% saturate)                 |
| Clock pressure %-of-base     | `NEUTRAL_PCT_THRESHOLD`          | ±10               | ±7 (or per-TC)         | keep / review                     | tighten to ±7; consider per-TC        |
| Net timeout                  | `NEUTRAL_TIMEOUT_THRESHOLD`      | ±5                | ±5                     | review / keep                     | keep; stratify by ELO                 |
| Time-pressure Y domain       | `Y_AXIS_DOMAIN`                  | [0.2, 0.8]        | [0.2, 0.8]             | review / review                   | keep                                  |
| Per-class score-diff band    | `NEUTRAL_ZONE_MIN/MAX` (WDLChart)| ±0.05             | ±0.05                  | (per-class) keep                  | keep                                  |
| Per-class score-diff domain  | `BULLET_DOMAIN` (WDLChart)       | 0.30              | 0.45                   | (per-class) keep                  | widen for classical-2400 fit          |
| Per-class conversion bands   | (none)                           | (none)            | per-class ±5pp         | (per-class) keep                  | add (rook/minor/pawn/queen/mixed/pawnless) |
| Per-class recovery bands     | (none)                           | (none)            | per-class ±5pp         | (per-class) keep                  | add (rook/minor/pawn/queen/mixed/pawnless) |

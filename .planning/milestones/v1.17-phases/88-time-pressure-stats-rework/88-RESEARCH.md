# Phase 88 Research — Time Pressure stats rework

**Researched:** 2026-05-17
**Domain:** Endgames page time-pressure section — backend math, benchmark skill, frontend card component, API shape
**Confidence:** HIGH (code excerpts from codebase, prod-DB queries executed)

---

## Summary

Five-bullet digest of the open-question verdicts:

- **Q1 (thresholds):** `MIN_GAMES_PER_TC_CARD = 20` works well for bullet/blitz/rapid (84–88% of prod users pass), but classical is unusable at any threshold — only 3 of 19 classical users pass 20 games. Keep thresholds as proposed; the classical card hiding is the correct behaviour.
- **Q2 (clock gap test):** Use **z-test** (reuse `compute_paired_difference_test`). Per-game clock gap distribution is symmetric (skew ≈ −0.05 to −0.09 across TCs), moderate tails, not heavy-tailed. CLT applies at any reasonable per-user game count; Wilcoxon brings no benefit and introduces interpretation complexity.
- **Q3 (API route):** Extend `/api/endgames/overview` in place — fold the new time-pressure card payload into `EndgameOverviewResponse`. Do not introduce `/api/endgames/time-pressure-cards` or separate route. One network round-trip, zero new route, zero new callers.
- **Q4 (/benchmarks collapse verdict):** Add one new subchapter `3.3.3 chess-score-per-pressure-bin` with the "metric-with-sub-bins" pattern. Per-quintile Cohen's d runs five separate collapse verdicts (one per quintile). Hook into the existing 3.3.x section at the same SQL skeleton level as 3.3.2. Shipped band shape: 20 entries (4 TC × 5 quintile) in `endgame_zones.py`.
- **Q5 (codegen):** Add a `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` dict keyed `(tc, quintile_index)` in `endgame_zones.py`, emit it from `gen_endgame_zones_ts.py` as a nested TS object `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q]` of shape `{ min: number; max: number }`.

---

## Q1: Prod-DB sample-size sanity check

**SSH tunnel was up at research time** (`pg_isready -h localhost -p 15432` → accepting). All queries ran against prod.

### User counts by TC (total rated games, regardless of endgame)

| TC | Total users | ≥5 | ≥10 | ≥20 | ≥50 |
|---|---|---|---|---|---|
| bullet | 54 | 49 | 48 | 44 | 42 |
| blitz | 64 | 62 | 61 | 60 | 56 |
| rapid | 66 | 64 | 61 | 60 | 55 |
| classical | 41 | 35 | 30 | 19 | 15 |

### Endgame game counts per user per TC (deduplicated by game)

| TC | n_users | card visible (≥20) | ≥100 | p25 | p50 | p75 |
|---|---|---|---|---|---|---|
| bullet | 50 | 43 (86%) | 32 | 34 | 216 | 2362 |
| blitz | 63 | 56 (89%) | 45 | 87 | 385 | 1884 |
| rapid | 66 | 56 (85%) | 45 | 50 | 281 | 738 |
| classical | 19 | 3 (16%) | 0 | 2 | 3 | 9 |

### Per-quintile bin fill (actual clock data, all 5 quintiles)

For each (user, TC) pair with clock data, counted games per pressure quintile (Q0=0–20% clock remaining, Q4=80–100%):

| TC | n_users | all 5 bins present | all bins ≥1 | all bins ≥5 | all bins ≥10 | median min_bin |
|---|---|---|---|---|---|---|
| bullet | 50 | 36 (72%) | 50 (100%) | 26 (52%) | 20 (40%) | 5.0 |
| blitz | 63 | 55 (87%) | 63 (100%) | 46 (73%) | 40 (63%) | 18.0 |
| rapid | 65 | 55 (85%) | 65 (100%) | 41 (63%) | 34 (52%) | 12.0 |
| classical | 19 | 3 (16%) | 19 (100%) | 2 (11%) | 0 (0%) | 1.0 |

### Clock data availability

| TC | endgame games | with clock | pct |
|---|---|---|---|
| bullet | 96,396 | 96,214 | ~99% |
| blitz | 73,639 | 73,627 | ~100% |
| rapid | 48,222 | 48,217 | ~100% |
| classical | 213 | 213 | ~100% |

Note: an earlier query showed lower clock coverage per-user (65–85% for rapid/classical), but the per-game query confirms near-complete clock data when looking at the total game pool. The per-user query was approximate.

### Verdict

**`MIN_GAMES_PER_TC_CARD = 20` is correct.** It correctly passes 85–89% of active users for bullet/blitz/rapid and correctly hides the classical card for 84% of classical users (who have too few games to be meaningful).

**`MIN_GAMES_PER_PRESSURE_BIN = 5` is on the edge for bullet.** At the median min_bin of exactly 5, roughly 50% of bullet users would have at least one dimmed quintile. Consider raising to 5 and accepting partial dimming — the D-01 dimming behaviour (render at `UNRELIABLE_OPACITY` with n=X chip, no triple-gate coloring) correctly handles these cases. Do not raise to 10; that would dim all quintiles for ~60% of bullet users.

**Recommendation:** Keep `MIN_GAMES_PER_TC_CARD = 20` and `MIN_GAMES_PER_PRESSURE_BIN = 5` as proposed. The dimming / dash pattern from D-01 is exactly the right fallback for bullet's sparse extreme quintiles (0–20% clock remaining is genuinely rare — players rarely enter endgames on fumes). Classical card hiding is correct and expected.

---

## Q2: Clock Gap test choice

### Distribution shape evidence

From the prod-DB query on `(my_clock − opp_clock) / base_clock × 100` at endgame entry:

| TC | n_games | mean | std | p5 | p25 | p50 | p75 | p95 | skew_approx |
|---|---|---|---|---|---|---|---|---|---|
| bullet | 96,359 | −1.27% | 18.6% | −31.7% | −11.7% | −0.2% | +10.0% | +27.0% | −0.059 |
| blitz | 73,627 | −4.16% | 20.7% | −38.5% | −16.5% | −3.7% | +7.8% | +29.8% | −0.024 |
| rapid | 48,217 | −1.50% | 20.7% | −37.8% | −12.5% | −0.5% | +10.3% | +31.6% | −0.050 |
| classical | 213 | −15.4% | 30.8% | −66.3% | −35.3% | −12.7% | +5.2% | +25.2% | −0.088 |

Skewness approximation = (mean − median) / std. All values are near zero (−0.02 to −0.09), confirming near-symmetric distributions. The IQR is roughly ±10–16 pp; tails extend to ±30–40 pp but are not pathologically heavy.

### Recommendation: z-test (reuse `compute_paired_difference_test`)

The distribution is symmetric, not heavy-tailed. Wilcoxon would be appropriate if the distribution were right-skewed or had catastrophic outliers (e.g. someone entering an endgame with 1% clock vs opponent's 120%). The data shows no such skew. Moreover:

1. `compute_paired_difference_test` already exists, is tested, and handles the n-gate contract correctly.
2. The z-test CI (mean ± 1.96 × SE) is directly interpretable as the clock-gap whiskers on the bullet chart.
3. Wilcoxon returns a rank-based test statistic whose CI is on the median, not the mean — not what `MiniBulletChart` expects.
4. User N at the per-user level (after averaging across games) will be tens to hundreds, so CLT applies comfortably.

The Clock Gap metric is per-user, not per-game — each user contributes one mean `(my − opp)/base` across their games in the TC. The test is one-sample against H0: mean = 0. `compute_paired_difference_test([diff_pct_game1, diff_pct_game2, ...])` already does exactly this.

**Decision: z-test via `compute_paired_difference_test`, identical to Phase 85.1 / Score Gap usage.**

---

## Q3: API route shape

### Current architecture

All endgame data is fetched via one query: `useEndgameOverview` → `GET /api/endgames/overview` → `EndgameOverviewResponse`. The response already includes `clock_pressure: ClockPressureResponse` and `time_pressure_chart: TimePressureChartResponse`. There are **no separate `/api/endgames/clock-pressure` or `/api/endgames/time-pressure` routes** — the CONTEXT.md referenced them incorrectly; they do not exist. Both are computed inside `compute_endgame_overview` and returned in the overview payload.

### Caller inventory

From `git grep` in the frontend:
- `overviewData?.clock_pressure` — `Endgames.tsx:285`
- `overviewData?.time_pressure_chart` — `Endgames.tsx:286`
- `EndgameClockPressureSection` and `EndgameTimePressureSection` are the two consumers; both are deleted in Phase 88.
- `useEndgameOverview` is the sole hook; it hits `/api/endgames/overview`.

### Recommendation: fold into the existing `overview` payload (option c)

Replace `clock_pressure: ClockPressureResponse` and `time_pressure_chart: TimePressureChartResponse` in `EndgameOverviewResponse` with a new `time_pressure_cards: TimePressureCardsResponse`. The new type holds one entry per TC, each with the Clock Gap bullet data + 5 Score-Delta bullet entries.

**Rationale:**

- The Endgames page already issues exactly one network request at load time. Adding a second request for the time-pressure cards adds latency and network overhead with zero benefit — the data is computed from the same `clock_rows` already fetched for the old clock_pressure computation.
- The CONTEXT.md note about option (a) "extend in place" creates no benefit because the old response shapes are being deleted entirely; replacing with a new field in the same response is cleaner than preserving the old field names.
- Option (b) new route would require a second `useQuery` call, a new hook, and a new backend endpoint — all extra surface for zero gain.
- Knip cleanliness: deleting the old `ClockPressureResponse` and `TimePressureChartResponse` types and their consumers in the same phase keeps the type graph clean.

**Concretely:** in `EndgameOverviewResponse`, drop `clock_pressure` and `time_pressure_chart`, add `time_pressure_cards: TimePressureCardsResponse`. The backend drops `_compute_clock_pressure` + `_compute_time_pressure_chart` and adds a new `_compute_time_pressure_cards` function. The Endgames page destructures `time_pressure_cards` instead of the two old fields.

---

## Q4: Per-bin IQR collapse-verdict implementation

### How the existing skill computes Cohen's d collapse verdicts

From SKILL.md §"Collapse verdict methodology":

1. Compute one value per user, labeled by `(rating_bucket, tc_bucket)`. Floor: ≥10 users/cell.
2. TC marginal: 4 levels — pool users across ELO, compute group `(n, mean, var)`. Exclude `(2400, classical)`.
3. ELO marginal: 5 levels — pool users across TC, same exclusion.
4. Pairwise Cohen's d across all level pairs on each axis; take `max |d|`.
5. Verdict: < 0.2 = collapse; 0.2–0.5 = review; ≥ 0.5 = keep separate.

The existing time-pressure section (§3.3.2) currently has only a **game-level** metric (per-(TC × time-bucket) score), not a **per-user** metric, so the existing collapse verdict runs differently. Phase 88 requires upgrading to per-user metrics (same pattern as §3.1.4 endgame score).

### New subchapter structure: `3.3.3 chess-score-per-pressure-bin`

This is a new "metric-with-sub-bins" shape. The per-bin collapse verdict runs **per quintile independently** (5 verdicts, not 1), because the score distribution compresses at extreme quintiles (low clock = forced-loss pressure compresses scores toward 0).

#### SQL pattern (per-user per-quintile chess score)

```sql
WITH selected_users AS (...),  -- standard CTE
endgame_games_with_clock AS (
  -- One row per game with endgame entry and clock data
  SELECT g.id AS game_id, g.user_id, g.time_control_bucket::text AS tc,
         su.rating_bucket AS elo_bucket,
         -- user_clock / base_time * 100 -> quintile 0-4
         LEAST(4, FLOOR(user_clk_pct / 20.0)::int) AS quintile,
         -- game score from user perspective
         CASE WHEN (g.result='1-0' AND g.user_color='white')
                OR (g.result='0-1' AND g.user_color='black') THEN 1.0
              WHEN g.result='1/2-1/2' THEN 0.5
              ELSE 0.0
         END AS score
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN first_endgame fe ON fe.game_id = g.id
  -- clock routing logic (mirror _compute_clock_pressure)
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND abs(...) <= 100  -- equal-footing filter
    AND user_clk_pct BETWEEN 0 AND 200  -- outlier guard
),
per_user_quintile AS (
  SELECT user_id, elo_bucket, tc, quintile,
         count(*) AS n_games,
         avg(score) AS user_score
  FROM endgame_games_with_clock
  GROUP BY user_id, elo_bucket, tc, quintile
  HAVING count(*) >= 5  -- sample floor per bin
)
-- Then: per-quintile Cohen's d across TC axis, per-quintile across ELO axis
-- Per-quintile Q1/Q3 of user_score for the IQR band
SELECT quintile, elo_bucket, tc,
       count(*) AS n_users,
       avg(user_score) AS mean_score,
       var_samp(user_score) AS var_score,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY user_score) AS p25,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY user_score) AS p75
FROM per_user_quintile
GROUP BY quintile, elo_bucket, tc
HAVING count(*) >= 10;  -- Cohen's d floor
```

#### Collapse verdict per quintile

For each quintile (0–4), run the standard Cohen's d recipe on TC and ELO axes independently. The skill must emit 5 per-quintile verdicts:

```
Quintile 0 (0–20% clock remaining — maximum pressure):
  - TC axis: d_max = X.XX (bullet vs classical) → {collapse | review | keep}
  - ELO axis: d_max = Y.YY (800 vs 2400) → {collapse | review | keep}
Quintile 1 ... (repeat for Q1–Q4)
```

Expected from benchmarks-latest.md §3.3.2: Q0 (0–20% clock = extreme pressure) is where TC matters most (bullet 26% vs classical 41% score at tb=0). The Q4 (80–100% clock = full clock) should collapse more cleanly since "playing with full clock" is TC-agnostic in terms of score levels. ELO is expected to collapse across all quintiles (current d=0.17 pooled).

#### Shipped band shape

After per-quintile collapse verdicts:
- Default: pool ELO (expected to collapse) → 20 band entries: 4 TC × 5 quintile.
- Any quintile where ELO verdict is "keep separate" → promote that quintile's band to (TC × ELO × quintile), adding 5 entries per quintile that stays stratified.

The shipped constants are `p25` / `p75` of per-user `user_score` per (TC, quintile) cell, with ELO pooled.

#### What changes in the skill vs current §3.3.2

Current §3.3.2 is a game-level metric (not per-user): it pools all games in a (TC × time-bucket) cell and takes the aggregate score. The new §3.3.3 adds the **per-user** layer that was always missing. Specifically:

1. §3.3.2 remains (historical reference) — current collapse verdict on game-level data.
2. §3.3.3 is new — per-user per-quintile chess score distribution for IQR band calibration. This is what actually feeds the zone constants in `endgame_zones.py`.

The key difference: §3.3.3 computes `user_score = (W + 0.5D) / N` per user per (TC, quintile) cell, then takes the inter-user distribution (Q1/Q3) as the band. §3.3.2 pools all games directly.

#### Integration with existing skill sections

The new §3.3.3 hooks into the same infrastructure:
- Same `selected_users` standard CTE
- Same sparse-cell exclusion `NOT (elo_bucket = 2400 AND tc = 'classical')`
- Same equal-footing filter `abs(opp_rating − user_rating) ≤ 100`
- Same `n_users ≥ 10` floor for Cohen's d cells
- Same verdict table format

Additionally, §3.3.1 should add a new "clock-gap-%" submetric using the same 3.3.1 CTE extended to per-user mean `(my_clock − opp_clock) / base_clock`. Report distribution and Cohen's d. Expected verdict: collapse on both TC and ELO (blitz clock-diff correlation disappears at rapid/classical per the benchmark data).

#### Editorial cap on band half-width

The planner must set `PRESSURE_BIN_NEUTRAL_CAP = 0.06` (±6 score points) as the maximum half-width for any `(TC, quintile)` band. If `(p75 − p25) / 2 > 0.06`, cap at 0.06 symmetrically around the median. This is the "editorial cap" from D-02. In practice this fires at extreme quintiles (Q0, Q4) where sample sizes per user are small.

---

## Q5: endgame_zones.py codegen integration

### Existing pattern (from `endgame_zones.py`)

The existing patterns are:

1. **Scalar ZoneSpec** — one `(typical_lower, typical_upper, direction)` per `MetricId` in `ZONE_REGISTRY`. Emitted as flat constants `FOO_NEUTRAL_MIN / FOO_NEUTRAL_MAX`.

2. **Per-class bands** — `PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands]` where `PerClassBands` is a frozen dataclass with tuple fields per metric. Emitted as a nested TS object literal.

3. **Bucketed registry** — `BUCKETED_ZONE_REGISTRY: Mapping[BucketedMetricId, Mapping[MaterialBucket, ZoneSpec]]`. Emitted as `FIXED_GAUGE_ZONES`.

### New pattern: `PRESSURE_BIN_SCORE_NEUTRAL_ZONES`

Phase 88 requires a new shape: 5 quintiles × 4 TCs = 20 bands. This does not fit `ZONE_REGISTRY` (scalar) or `PER_CLASS_GAUGE_ZONES` (per-class). It needs its own typed container.

#### Python addition in `endgame_zones.py`

```python
from typing import NamedTuple

# Phase 88 D-02: per-(TC, pressure-quintile) neutral band for Score-Delta bullets.
# Calibrated from /benchmarks §3.3.3 (chess-score-per-pressure-bin):
# inter-user IQR [p25, p75] of per-user score per (TC, quintile) cell.
# ELO is pooled (expected to collapse; any quintile with ELO d >= 0.5 gets
# promoted to per-ELO faceting — tracked as a post-/benchmarks planner task).
# Editorial cap: band half-width capped at PRESSURE_BIN_NEUTRAL_CAP = 0.06.
PRESSURE_BIN_NEUTRAL_CAP: float = 0.06

# Quintile index 0 = 0-20% clock remaining (max pressure), 4 = 80-100% (min).
PressureQuintile = Literal[0, 1, 2, 3, 4]
TimeControl = Literal["bullet", "blitz", "rapid", "classical"]

@dataclass(frozen=True)
class PressureBinBand:
    """Neutral [lower, upper] band for Score-Delta in one (TC, quintile) cell."""
    lower: float
    upper: float

# PLACEHOLDER — filled by plan-phase after /benchmarks §3.3.3 runs.
# Keys: (tc, quintile_index). Values: p25/p75 of per-user score in that cell.
PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Mapping[TimeControl, Mapping[PressureQuintile, PressureBinBand]] = {
    "bullet":    {0: PressureBinBand(-0.06, 0.06), 1: PressureBinBand(-0.06, 0.06),
                  2: PressureBinBand(-0.06, 0.06), 3: PressureBinBand(-0.06, 0.06),
                  4: PressureBinBand(-0.06, 0.06)},
    "blitz":     {0: PressureBinBand(-0.06, 0.06), 1: PressureBinBand(-0.06, 0.06),
                  2: PressureBinBand(-0.06, 0.06), 3: PressureBinBand(-0.06, 0.06),
                  4: PressureBinBand(-0.06, 0.06)},
    "rapid":     {0: PressureBinBand(-0.06, 0.06), 1: PressureBinBand(-0.06, 0.06),
                  2: PressureBinBand(-0.06, 0.06), 3: PressureBinBand(-0.06, 0.06),
                  4: PressureBinBand(-0.06, 0.06)},
    "classical": {0: PressureBinBand(-0.06, 0.06), 1: PressureBinBand(-0.06, 0.06),
                  2: PressureBinBand(-0.06, 0.06), 3: PressureBinBand(-0.06, 0.06),
                  4: PressureBinBand(-0.06, 0.06)},
}
```

The placeholder values (`±0.06`) are the editorial cap fallback. They must be replaced with actual calibrated values from /benchmarks §3.3.3 before the constants ship. The planner should sequence the /benchmarks run before (or as Wave 0 of) the zone-constants plan.

#### Generated TypeScript in `endgameZones.ts`

The codegen script emits:

```typescript
// Phase 88 D-02: per-(TC, pressure-quintile) neutral bands for Score-Delta bullets.
// Quintile index 0 = 0–20% clock remaining (max pressure), 4 = 80–100% (min).
// Calibrated from /benchmarks §3.3.3. ELO pooled (collapse confirmed per quintile).
export const PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Record<
  'bullet' | 'blitz' | 'rapid' | 'classical',
  Record<0 | 1 | 2 | 3 | 4, { min: number; max: number }>
> = {
  bullet:    { 0: { min: -0.06, max: 0.06 }, 1: { min: -0.06, max: 0.06 }, ... },
  blitz:     { 0: { min: -0.06, max: 0.06 }, ... },
  rapid:     { 0: { min: -0.06, max: 0.06 }, ... },
  classical: { 0: { min: -0.06, max: 0.06 }, ... },
} as const;
```

The consumer in the card component accesses `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][quintileIndex]` to get `neutralMin` and `neutralMax` for `MiniBulletChart`.

#### Codegen changes in `gen_endgame_zones_ts.py`

Add two pieces:

1. Import `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` from `app.services.endgame_zones`.
2. A `_format_pressure_bin_zones()` function that iterates the nested dict and emits the TS literal. Append its output to `_render()`.

The CI drift check (`git diff --exit-code frontend/src/generated/endgameZones.ts`) fires on any mismatch as usual. The codegen script already runs via `uv run python scripts/gen_endgame_zones_ts.py`.

#### Clock-gap zone (simpler)

The Clock Gap zone (single global band from /benchmarks `clock-gap-%`) is a scalar ZoneSpec in `ZONE_REGISTRY` under a new `MetricId` `"clock_gap_pct"`. Emitted as `CLOCK_GAP_NEUTRAL_MIN / CLOCK_GAP_NEUTRAL_MAX` in the same flat constant pattern as `NEUTRAL_PCT_THRESHOLD`. Placeholder until /benchmarks §3.3.1 extended metric runs: use `(-0.05, 0.05)` (±5pp, same as current `NEUTRAL_PCT_THRESHOLD`).

---

## Existing patterns (code excerpts)

### 1. `EndgameTypeCard.tsx` — sparse handling and dimming

```tsx
// Lines 95-100: sparse detection and body opacity
const hasGames = category.total > 0;
const isUnreliable =
  hasGames && category.total < MIN_GAMES_FOR_RELIABLE_STATS;
const bodyStyle: CSSProperties | undefined = isUnreliable
  ? { opacity: UNRELIABLE_OPACITY }
  : undefined;
```

Phase 88 pattern: the TC card hides entirely when `total < MIN_GAMES_PER_TC_CARD`. Within a rendered card, individual Score-Delta bullets that have `n < MIN_GAMES_PER_PRESSURE_BIN` apply the same `UNRELIABLE_OPACITY` on the bullet row only (not the whole card body).

```tsx
// Lines 113, 179: two distinct empty-state paths
const showScoreRow = total >= MIN_GAMES_FOR_RELIABLE_STATS;
// ... later:
if (!hasGames) { return <div>...</div>; }  // whole-card empty shell
```

Phase 88 analogue: `if (tcCard.total < MIN_GAMES_PER_TC_CARD) return null;` at the card level. Per-bin: if `bin.n === 0`, render dash; if `0 < bin.n < MIN_GAMES_PER_PRESSURE_BIN`, render bullet at `UNRELIABLE_OPACITY`.

### 2. `MiniBulletChart.tsx` — the bullet primitive

```tsx
// Lines 90-103: the component signature (key props for Phase 88)
export function MiniBulletChart({
  value,          // signed delta (e.g. user_score − cohort_score)
  neutralMin,     // lower bound of neutral zone (offset from center)
  neutralMax,     // upper bound of neutral zone (offset from center)
  domain,         // half-width of axis
  center = 0,     // reference line position
  ciLow,          // optional CI lower bound
  ciHigh,         // optional CI upper bound
  barColor = 'zone',  // 'neutral' for grey bar (Openings style)
}: MiniBulletChartProps)
```

Phase 88 usage for Score-Delta bullet:
- `value = delta` (user_score − cohort_score, signed)
- `center = 0` (centred on 0 = matches cohort)
- `neutralMin/Max` from `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][quintile]`
- `domain = 0.20` (±20pp covers the expected ±15pp IQR generously)
- `ciLow/ciHigh` from Wilson bounds on user_score, transplanted to delta space

Clock Gap bullet:
- `value = mean_diff_pct` (user − opp clock as fraction of base clock)
- `center = 0`
- `neutralMin/Max` from `CLOCK_GAP_NEUTRAL_MIN/MAX`
- `domain = 0.30` (±30pp, covers p5/p95 range from prod data)

### 3. `endgame_math.py` — the math helper location

There is no `app/services/endgame_math.py` file. The helpers `compute_paired_difference_test` and `compute_score_difference_test` live in `app/services/score_confidence.py`. They are imported into `endgame_service.py`:

```python
# endgame_service.py line 74:
from app.services.score_confidence import (
    compute_paired_difference_test,
    compute_score_difference_test,
)
```

The new `compute_score_delta_vs_reference` should live in `score_confidence.py` alongside these two. Signature:

```python
def compute_score_delta_vs_reference(
    user_w: int,
    user_d: int,
    user_l: int,
    user_n: int,
    cohort_score: float,
) -> tuple[float, float | None, float | None, float | None]:
    """Return (delta, p_value, ci_low, ci_high) treating cohort_score as fixed.

    delta = user_score − cohort_score
    user_score = (user_w + 0.5 * user_d) / user_n
    Wilson 95% CI on user_score, transplanted to delta space:
      ci_low  = wilson_low(user_score, user_n)  − cohort_score
      ci_high = wilson_high(user_score, user_n) − cohort_score
    p_value = Wilson score test of H0: user_score == cohort_score
      (use _wilson_score_test_vs_half adapted to arbitrary reference)
    """
```

The Wilson CI transplant: `(ci_low, ci_high) = (wilson_lo − cohort_score, wilson_hi − cohort_score)`. Interpretation: does the user's Wilson interval include `cohort_score`? If yes, no signal. The p-value should be from a one-sample Wilson-style test vs `cohort_score` (not vs 0.5). Since the existing `_wilson_score_test_vs_half` is hardcoded to H0=0.5, a new internal helper `_wilson_score_test_vs_ref(score, n, ref)` is needed, or adapt the formula directly.

### 4. `endgame_zones.py` — codegen source (key shapes)

```python
# Pattern 1: scalar ZoneSpec in ZONE_REGISTRY (lines 161-331)
ZONE_REGISTRY: Mapping[MetricId, ZoneSpec] = {
    "avg_clock_diff_pct": ZoneSpec(
        typical_lower=-NEUTRAL_PCT_THRESHOLD,
        typical_upper=NEUTRAL_PCT_THRESHOLD,
        direction="higher_is_better",
    ),
    # ...
}

# Pattern 2: per-class frozen dataclass (lines 406-464)
@dataclass(frozen=True)
class PerClassBands:
    conversion: tuple[float, float]
    recovery: tuple[float, float]
    achievable_score_gap: tuple[float, float]

PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands] = {
    "rook": PerClassBands(
        conversion=(0.65, 0.75),
        recovery=(0.26, 0.36),
        achievable_score_gap=(-0.05, 0.04),
    ),
    # ...
}
```

Phase 88 adds a third pattern — nested mapping by (TC, quintile) — following the same frozen dataclass approach.

### 5. `scoreBulletConfig.ts` — bullet domain/zone helpers

```typescript
// Lines 12-34: the module's pattern for a metric family
export const SCORE_BULLET_CENTER = 0.5;
export const SCORE_BULLET_NEUTRAL_MIN = -0.05;    // offset from center
export const SCORE_BULLET_NEUTRAL_MAX = 0.05;     // offset from center
export const SCORE_BULLET_DOMAIN = 0.25;          // half-width

export function clampScoreCi(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

export function scoreZoneColor(score: number): string {
  if (score >= SCORE_NEUTRAL_HIGH) return ZONE_SUCCESS;
  if (score <= SCORE_NEUTRAL_LOW) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
```

Phase 88 will co-locate `pressureBulletDomain()` and `clampDeltaCi(delta)` here or in a new `pressureBulletConfig.ts`. Given the per-TC-per-quintile zones come from `endgameZones.ts`, the config module primarily provides domain constants and clamp utilities; zone lookups use `PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q]` directly.

---

## Validation Architecture (Nyquist)

### Test Framework

| Property | Value |
|---|---|
| Framework | Vitest (frontend) + pytest (backend) |
| Frontend config | `frontend/vite.config.ts` (vitest embedded) |
| Backend config | `pyproject.toml` (pytest) |
| Quick run (frontend) | `npm test -- --run` |
| Quick run (backend) | `uv run pytest tests/ -x -q` |
| Full suite | `npm test -- --run && uv run pytest tests/ -q` |

### Backend: `compute_score_delta_vs_reference`

Unit test boundaries (all in `tests/test_score_confidence.py` or new `tests/test_score_delta.py`):

| Case | Input | Expected |
|---|---|---|
| n=0 | `(0, 0, 0, 0, cohort_score)` | `(0.0, None, None, None)` — defensive no-data |
| all-wins | `(5, 0, 0, 5, 0.5)` | `delta=+0.5`, `ci_low > 0`, `ci_high ≤ 1.0 − 0.5` |
| all-losses | `(0, 0, 5, 5, 0.5)` | `delta=−0.5`, `ci_high < 0` |
| user_score == cohort_score | `(n, d, l, N, user_score_value)` | `delta=0.0`, `p_value ≈ 1.0` |
| threshold n=9 | user_n=9 | `p_value=None` (below CONFIDENCE_MIN_N=10) |
| threshold n=10 | user_n=10 | `p_value` is float |
| cohort_score near 0 | `(1, 0, 9, 10, 0.02)` | `delta ≈ 0.08`, CI shift correct |
| cohort_score near 1 | `(9, 0, 1, 10, 0.95)` | `delta ≈ −0.05`, CI shift correct |

Property invariants for pytest:
```python
# delta sign matches sign(user_score − cohort_score)
assert sign(delta) == sign(user_score - cohort_score)
# CI contains delta when user_score == cohort_score (trivially true, delta=0)
# CI lower < delta < CI upper (when n >= 2 and not degenerate)
assert ci_low < delta < ci_high  # for non-degenerate inputs
```

### Frontend: sparse-bin rendering contract

Unit tests for the TC card component (new `EndgameTimePressureCard.test.tsx`):

| Scenario | Assert |
|---|---|
| `total < MIN_GAMES_PER_TC_CARD` | card returns null (hidden) |
| `total >= MIN_GAMES_PER_TC_CARD`, bin n=0 | dash rendered, no bullet glyph, slot preserved |
| `0 < bin.n < MIN_GAMES_PER_PRESSURE_BIN` | bullet rendered at `UNRELIABLE_OPACITY`, `n=X` chip present, no font color |
| `bin.n >= MIN_GAMES_PER_PRESSURE_BIN, not confident` | bullet rendered at full opacity, no colored font |
| triple-gate all pass | bullet rendered with colored font matching zone |
| Clock Gap always renders when card renders | `data-testid="clock-gap-bullet"` present for any total >= MIN_GAMES_PER_TC_CARD |

### Integration: 4-TC grid rendering

Smoke test in `Endgames.overallPerformance.test.tsx` (existing, extend):
- Mock `time_pressure_cards` with 2 cards (bullet + rapid, blitz hidden, classical hidden)
- Assert `data-testid="time-pressure-card-bullet"` present
- Assert `data-testid="time-pressure-card-blitz"` absent
- Assert legacy `data-testid="clock-pressure-section"` absent (knip clean verification proxy)

### Sampling rate

- Per task commit: `uv run pytest tests/test_score_confidence.py -x && npm test -- --run --reporter=verbose src/components/charts/EndgameTimePressureCard.test.tsx`
- Per wave merge: full suite
- Phase gate: full suite green before `/gsd:verify-work`

### Wave 0 gaps

- [ ] `tests/test_score_delta.py` — `compute_score_delta_vs_reference` boundaries
- [ ] `frontend/src/components/charts/EndgameTimePressureCard.test.tsx` — card rendering
- [ ] `frontend/src/components/charts/EndgameTimePressureSectionOrchestrator.test.tsx` — grid rendering

---

## Open items the planner still owns

### 1. /benchmarks run must precede zone-constant commits

The `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` and `CLOCK_GAP_NEUTRAL_MIN/MAX` constants are placeholders until `/benchmarks` §3.3.3 + updated §3.3.1 are run on the benchmark DB. The planner must sequence this: /benchmarks skill invocation (Wave 0 or Wave 1 task) → update `endgame_zones.py` constants → regenerate `endgameZones.ts` → downstream tasks use real zones. If the benchmark DB is not running, start it first: `bin/benchmark_db.sh start`.

**Unblocking data:** Run the per-user per-quintile SQL from §Q4 above on the benchmark DB. The per-quintile `p25/p75` values across all (TC × ELO) cells are the calibrated zone bounds.

### 2. `compute_score_delta_vs_reference` — Wilson test vs arbitrary reference

The existing `_wilson_score_test_vs_half` is hardcoded to H0=0.5. A new internal `_wilson_score_test_vs_ref(score, n, ref)` is needed. The formula is the same Wilson score test but with `ref` replacing `0.5` in the null-parameter. Planner must decide whether to add this as a private helper in `score_confidence.py` or inline the formula inside the new public function. Either works; private helper is cleaner.

**Unblocking data:** None — this is a code decision. The math is: `z = (score − ref) / sqrt(ref*(1−ref)/n)`, p-value = `erfc(|z| / sqrt(2))`. This is the standard score test; the Wald approximation is adequate at n≥10.

### 3. `MetricId` Literal extension for `clock_gap_pct`

Adding `"clock_gap_pct"` to the `MetricId` Literal in `endgame_zones.py` requires confirming the insights service does not consume this metric for LLM narration (time-pressure LLM narration is out of scope per CONTEXT deferred items). The planner should grep `compute_findings` in `insights_service.py` for `time_pressure_at_entry` to confirm the new metric won't accidentally fire a finding.

**Unblocking data:** `grep -n "time_pressure_at_entry\|clock_gap\|avg_clock_diff" app/services/insights_service.py` — confirm scope.

### 4. Editorial cap value

The `PRESSURE_BIN_NEUTRAL_CAP = 0.06` (±6 score points) is the suggested editorial cap from CONTEXT.md D-02. The planner should verify this against the actual per-quintile IQRs from the /benchmarks run. If any quintile's IQR half-width is naturally below 0.06, the cap is inactive and can be documented as "no activation." If most quintiles need the cap, consider lowering to 0.05. Hardcode the cap as a named constant in `endgame_zones.py`.

### 5. Cohort score source (live API vs precomputed)

The `cohort_score` reference for the Score-Delta bullet comes from the **live API mirror-bucket lookup** (same pattern as Phases 85–87), not from benchmark precomputation. The planner must confirm how Phase 87's mirror-bucket lookup is plumbed (search `_compute_mirror_bucket` or similar in `endgame_service.py`) and extend it for the pressure-quintile bucketing. The mirror-bucket must now also group by pressure quintile to produce a `cohort_score` per (rating_tier × TC × color × opponent_type × quintile). This is the largest new backend query surface in Phase 88.

**Unblocking data:** Read `endgame_service.py` around the Phase 87 mirror-bucket implementation (search `mirror` or `peer` in the file) to understand the existing plumbing before writing the new query.

---

## Sources

### Primary (HIGH confidence)

- `/home/aimfeld/Projects/Python/flawchess/app/services/score_confidence.py` — `compute_paired_difference_test`, `compute_score_difference_test`, `wilson_bounds` implementations
- `/home/aimfeld/Projects/Python/flawchess/app/services/endgame_zones.py` — zone registry patterns (ZoneSpec, PerClassBands, PER_CLASS_GAUGE_ZONES)
- `/home/aimfeld/Projects/Python/flawchess/scripts/gen_endgame_zones_ts.py` — codegen pipeline (emit patterns)
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/generated/endgameZones.ts` — current TS output shape
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/EndgameTypeCard.tsx` — sparse handling + triple-gate pattern
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/MiniBulletChart.tsx` — bullet primitive API
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/lib/scoreBulletConfig.ts` — bullet config pattern
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/hooks/useEndgames.ts` — single `useEndgameOverview` hook
- `/home/aimfeld/Projects/Python/flawchess/app/routers/endgames.py` — only `/overview` and `/games` routes exist; no separate clock/time-pressure routes
- Prod DB queries via `localhost:15432` (SSH tunnel) — sample-size and distribution data

### Secondary (MEDIUM confidence)

- `/home/aimfeld/Projects/Python/flawchess/reports/benchmarks-latest.md` §3.3.2 — game-level time-pressure vs performance data (verified current)
- `/home/aimfeld/Projects/Python/flawchess/.claude/skills/benchmarks/SKILL.md` — Cohen's d collapse methodology, query patterns, sparse-cell rules
- `/home/aimfeld/Projects/Python/flawchess/.planning/milestones/v1.17-phases/88-time-pressure-stats-rework/88-CONTEXT.md` — locked decisions

---

## Metadata

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (stable codebase; prod-DB sample sizes valid until next large user import wave)

**Confidence breakdown:**
- Prod-DB sample sizes: HIGH (direct query)
- Clock gap distribution / test choice: HIGH (direct query)
- API route shape: HIGH (grepped codebase, confirmed no separate routes exist)
- /benchmarks skill changes: HIGH (read SKILL.md in full)
- Codegen integration: HIGH (read source files)
- Zone constant values (PRESSURE_BIN_SCORE_NEUTRAL_ZONES): LOW (placeholders only; require /benchmarks run)
- Mirror-bucket plumbing for cohort_score: MEDIUM (confirmed pattern exists in Phase 87; exact implementation unread)

# Phase 115: You-vs-Opponent Comparison API + Bullet-Grid UI — Research

**Researched:** 2026-06-11
**Domain:** FastAPI/SQLAlchemy paired-delta statistics + React MiniBulletChart grid
**Confidence:** HIGH (all findings verified against live code or dev DB)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Grid layout & grouping**
- D-01: Family-grouped grid with subsection headers per family: Severity (Flaw Rate, Mistakes, Blunders), Tempo, Phase, Opportunity, Impact, Combos. Not a flat 15-row wall; no oversized headline bullet.
- D-02: FlawStatsBand stays; the per-game/per-100 NormToggle is removed. The Band is fixed to per-100-moves so the whole panel speaks one unit. `NormToggle` and the `per_game` rendering path are deleted, not hidden.
- D-03: 3 bullet columns on desktop, 1 on mobile. ~5 rows of bullets at lg.
- D-04: Per-metric axis domains. Each bullet's `domain` is calibrated to its own metric (starting point: §5 pooled p05/p95), hand-set alongside the zone constants in the same registry.

**Zone constants & bands**
- D-05: Zone bands = raw §5 pooled Q1/Q3 verbatim. No editorial widening, no minimum band width. Near-degenerate zones (reversed [+0.0, +0.0], low-clock+miss [+0.0, +0.0]) render as-is, hairline accepted.
- D-06: Pooled global zones for all 15 metrics. No per-ELO refinement for endgame-phase (d=0.28) or blunders now.
- D-07: Constants live in a new backend registry (`flaw_delta_zones.py`) and the endpoint embeds each bullet's zone bounds in the response (FLAWCMP-03). No TS codegen, no committed frontend constants.
- D-08: Keep the you−opponent sign convention; invert the chart colors. `MiniBulletChart` gets an inverted-color mode (success zone paints LEFT of the neutral band, danger RIGHT).

**Sample gates & fallbacks**
- D-09: Section gate floor = 20 analyzed games.
- D-10: Below the floor, the grid zone renders an "analyze more games" CTA state.
- D-11: Zero-event bullets keep their row with a muted "no events" placeholder. No grid reflow.
- D-12: `low-clock+miss` ships (58% cohort viability). FLAWCMP-04 plan-time check against dev users 28/44 confirms.

**Filter interactions**
- D-13: Under a non-default severity filter, zones stay visible with a tooltip caveat.
- D-14: FLAWUI-03 requirement text stays unamended; tooltip copy is future-proof generic wording.
- D-15: Tooltips follow the endgame metrics style (`MetricStatPopover` pattern).
- D-16: No special handling for the opponent-gap filter.

### Claude's Discretion
- CI method: bootstrap vs normal/t approximation — default to normal/t unless research finds a concrete reason to bootstrap.
- Endpoint shape: extend `GET /api/library/flaw-stats` vs a sibling endpoint.
- Exact family header copy, bullet label text, CTA copy, popover prose.
- SQL aggregation strategy for per-game paired deltas.
- What happens to `FlawTagDistribution.tsx` and its tests.

### Deferred Ideas (OUT OF SCOPE)
- Per-ELO zone refinement for endgame-phase / blunders.
- Tactic-motif bullets (SEED-039).
- Eval-coverage raising (SEED-012 / FLAWCOV-01).
- Trend-chart comparison.
- Termination patterns.
- Prod `game_flaws` backfill (ships empty on prod per milestone scope).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLAWCMP-01 | Unified per-100-moves paired-delta for ALL 15 metrics, with CI per bullet | §SQL aggregation shape + CI method findings below |
| FLAWCMP-02 | **VOIDED** — Wilson proportion method superseded | Not applicable |
| FLAWCMP-03 | Full 15-bullet inventory (M+B + mistake/blunder split); zone bounds in response; all game filters honored | §15-bullet inventory, §endpoint shape, §filter plumbing |
| FLAWCMP-04 | Combo CI-width adequacy validated at plan time | §FLAWCMP-04 finding (actionable, see below) |
| FLAWCMP-05 | Section gate: "analyze more games" below N=20; zero-event placeholder per bullet | §sample gate plumbing |
| FLAWUI-01 | Tag-distribution zone replaced by MiniBulletChart grid | §MiniBulletChart inverted mode |
| FLAWUI-02 | Per-bullet tooltip: definition + sign convention + clock-conditioned caveat | §tooltip patterns |
| FLAWUI-03 | Tooltip: filter×zone interaction disclosure | §tooltip patterns |
| FLAWUI-04 | Graceful bullet degradation (no zone when cohort stat absent) | §MiniBulletChart patterns |
| FLAWUI-05 | Trend chart stays comparison-free | No changes to trend; not researched further |
| FLAWUI-06 | Mobile-responsive grid; data-testid + ARIA on all interactive elements | §frontend conventions |
</phase_requirements>

---

## Summary

Phase 115 replaces the flaw-stats panel's self-only tag-distribution zone with a 15-bullet you-vs-opponent comparison grid. The backend computes a per-game paired delta (player_tag_count − opp_tag_count) / user_moves × 100 for each of 15 metrics, takes the mean across analyzed games, and returns a normal-approx 95% CI per bullet. The frontend renders each bullet using the existing `MiniBulletChart` component (which already has CI whisker support) with a new inverted-color mode.

**Critical finding (FLAWCMP-04 combo CI validation):** Both combo metrics are adequate on dev users 28/44 (556/550 analyzed games each). `hasty+miss` CI half-width ≈ ±0.13 pp — well-determined. `low-clock+miss` CI half-width ≈ ±0.055 pp — narrow because the SD is small (0.67 pp), not because N is small. No catastrophic widening; `low-clock+miss` ships. See dedicated section below.

**Primary recommendation:** Use a sibling endpoint `GET /api/library/flaw-comparison` (not extending the existing `flaw-stats` endpoint) to keep the payload clean, avoid breaking the existing `useLibraryFlawStats` query key, and keep the two responsibilities decoupled.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-game paired delta computation | API / Backend | — | Requires JOIN across `game_flaws` + `games.ply_count`; too heavy for client |
| CI computation (mean, SD, z-score) | API / Backend | — | Pure math over per-game deltas; Python stdlib sufficient (no scipy needed) |
| Zone constants registry | API / Backend | — | D-07: backend registry, no TS codegen; frontend renders what API sends |
| Bullet grid rendering | Browser / Client | — | MiniBulletChart already exists; grid layout is pure presentational React |
| Inverted-color MiniBulletChart mode | Browser / Client | — | Needs new `invertColors` prop on existing component |
| Sample gate (analyzed_n ≥ 20) | API / Backend | — | Gate applied before returning bullets; CTA state returned in response |
| Filter application | API / Backend | — | `apply_game_filters` + `_analyzed_game_ids_subquery` already handle all filters |
| Tooltip popovers | Browser / Client | — | `MetricStatPopover` pattern already established |

---

## FLAWCMP-04: Combo CI-Width Validation (HIGHEST PRIORITY)

**Status: SHIPS. No catastrophic result. Decision is confirmed.**

Query run against dev DB (users 28 and 44, all analyzed games, `game_flaws` backfilled with Phase 113 opponent rows):

| User | N analyzed games | hasty+miss mean delta | hasty+miss SD | hasty+miss CI ±half | lc+miss mean delta | lc+miss SD | lc+miss CI ±half |
|------|------------------|-----------------------|---------------|---------------------|-------------------|------------|-------------------|
| 28 | 556 | −0.38 pp | 1.52 pp | ±0.13 pp | +0.06 pp | 0.67 pp | ±0.056 pp |
| 44 | 550 | −0.38 pp | 1.53 pp | ±0.13 pp | +0.05 pp | 0.66 pp | ±0.055 pp |

**Hasty+miss:** CI half-width ±0.13 pp at N≈550. Given the pooled zone is [−0.1, +0.1] pp (§5.12 Q1/Q3), this CI is wider than the zone band itself — meaning a single dev user with typical behavior straddles the zone. That is the expected behavior for a rare tag; the bar reads wide, conveying inconclusive. The metric is informative for users with many hasty flaws (negative deltas like −0.38 pp here are strongly below typical). **SHIPS normally.**

**Low-clock+miss:** CI half-width ±0.055 pp at N≈550. The SD is only 0.67 pp because most per-game deltas are 0 (the event is rare). For a user with ~29 player events + ~12 opponent events over 550 analyzed games, the mean delta is +0.06 pp with CI [+0.00, +0.11]. This is a usable signal. The zone [+0.0, +0.0] (§5.13 Q1/Q3) is degenerate, so D-05 renders it as a hairline. **SHIPS with the D-11 zero-event placeholder path and the D-05 hairline zone.** The CI gives it meaning even when the zone is a hairline.

**Raw event counts (users 28 and 44):**

| | player hasty+miss | opp hasty+miss | player lc+miss | opp lc+miss |
|---|---|---|---|---|
| User 28 | 32 | 103 | 29 | 12 |
| User 44 | 32 | 102 | 27 | 12 |

Note: the large opp hasty+miss count (~103) vs player (~32) drives the strongly negative mean delta (−0.38 pp). These two dev users are notably less hasty-and-missing than their opponents. This is the kind of signal the feature is designed to surface.

**SQL used (exact, for plan verification):**

```sql
-- Per-game deltas for combos
-- is_opponent convention: even ply = white mover, odd ply = black mover
-- player rows: NOT((ply%2=0 AND user_color='black') OR (ply%2!=0 AND user_color='white'))
-- opp rows: (ply%2=0 AND user_color='black') OR (ply%2!=0 AND user_color='white')
WITH analyzed_games AS (
  SELECT gp.game_id
  FROM game_positions gp
  WHERE gp.user_id = :user_id
  GROUP BY gp.game_id
  HAVING SUM(CASE WHEN gp.eval_cp IS NOT NULL OR gp.eval_mate IS NOT NULL THEN 1 ELSE 0 END)::float
         / COUNT(*) >= 0.90
),
game_moves AS (
  SELECT g.id as game_id, g.user_color,
    CASE WHEN g.user_color = 'white' THEN FLOOR(g.ply_count::float/2)
         ELSE CEIL(g.ply_count::float/2) END as user_moves
  FROM games g
  WHERE g.user_id = :user_id
    AND g.id IN (SELECT game_id FROM analyzed_games)
    AND g.ply_count IS NOT NULL AND g.ply_count > 0
),
flaw_counts AS (
  SELECT f.game_id, g.user_moves,
    SUM(CASE WHEN f.tempo=1 AND f.is_miss=true
             AND NOT ((f.ply%2=0 AND g.user_color='black') OR (f.ply%2!=0 AND g.user_color='white'))
             THEN 1 ELSE 0 END) as player_hasty_miss,
    SUM(CASE WHEN f.tempo=1 AND f.is_miss=true
             AND ((f.ply%2=0 AND g.user_color='black') OR (f.ply%2!=0 AND g.user_color='white'))
             THEN 1 ELSE 0 END) as opp_hasty_miss,
    ... (same for lc+miss with f.tempo=0)
  FROM game_flaws f JOIN game_moves g ON g.game_id = f.game_id
  WHERE f.user_id = :user_id
  GROUP BY f.game_id, g.user_moves
)
SELECT COUNT(*) as n,
  AVG((player_hasty_miss - opp_hasty_miss)::float / user_moves * 100) as hm_mean,
  STDDEV((player_hasty_miss - opp_hasty_miss)::float / user_moves * 100) as hm_sd,
  1.96 * STDDEV(...) / SQRT(COUNT(*)) as hm_ci_half
FROM flaw_counts WHERE user_moves > 0;
```

---

## §5 Zone Constants — Planner Transcription Table

Source: `reports/benchmark/benchmarks-latest.md` §5.1–§5.16 (2026-06-11 mate-ladder basis). [VERIFIED: dev codebase]

All values are pp (per-100-moves). Zone = pooled Q1/Q3. Axis domain starting point = pooled p05/p95 (round to nearest 0.1 pp). Per D-05 the Q1/Q3 values are verbatim from the report — no editorial widening.

| § | Metric | family | DB column / filter | Q1 (zone_lo) | Q3 (zone_hi) | p05 (domain hint) | p95 (domain hint) | Viability | Near-degenerate? |
|---|--------|--------|-------------------|-------------|-------------|-------------------|-------------------|-----------|-----------------|
| 5.1 | flaw_rate | severity | severity IN (1,2) | −0.5 | +0.4 | −1.9 | +1.7 | 99.5% | No |
| 5.2 | low_clock | tempo | tempo = 0 | −0.1 | +0.0 | −0.4 | +0.4 | 71.4% | Yes — right edge degenerate |
| 5.3 | hasty | tempo | tempo = 1 | −0.3 | +0.2 | −1.1 | +1.1 | 98.4% | No |
| 5.4 | unrushed | tempo | tempo = 2 | −0.4 | +0.4 | −1.6 | +1.6 | 99.3% | No |
| 5.5 | opening | phase | phase = 0 | −0.1 | +0.1 | −0.7 | +0.7 | 98.8% | No |
| 5.6 | middlegame | phase | phase = 1 | −0.3 | +0.2 | −1.2 | +1.0 | 99.4% | No |
| 5.7 | endgame_phase | phase | phase = 2 | −0.1 | +0.1 | −0.5 | +0.5 | 98.5% | No |
| 5.8 | miss | opportunity | is_miss = true | −0.1 | +0.1 | −0.5 | +0.5 | 99.2% | No |
| 5.9 | lucky | opportunity | is_lucky = true | −0.1 | +0.1 | −0.4 | +0.4 | 98.8% | No |
| 5.10 | reversed | impact | is_reversed = true | +0.0 | +0.0 | −0.2 | +0.2 | 92.9% | **Yes — both edges degenerate** |
| 5.11 | squandered | impact | is_squandered = true | −0.1 | +0.1 | −0.3 | +0.4 | 95.7% | No |
| 5.12 | hasty_miss | combo | tempo=1 AND is_miss=true | −0.1 | +0.1 | −0.4 | +0.3 | 93.8% | No |
| 5.13 | low_clock_miss | combo | tempo=0 AND is_miss=true | +0.0 | +0.0 | −0.1 | +0.2 | 58.2% | **Yes — both edges degenerate** |
| 5.14 | mistake | severity | severity = 1 | −0.2 | +0.2 | −1.0 | +0.9 | 99.4% | No |
| 5.15 | blunder | severity | severity = 2 | −0.3 | +0.2 | −1.3 | +1.1 | 99.5% | No |

**Near-degenerate zones (D-05 hairline accepted):**
- `reversed` [+0.0, +0.0]: Q1=Q3=0.0; the neutral band is a hairline at center. Render as-is.
- `low_clock_miss` [+0.0, +0.0]: same. CI half-width (~0.05 pp at N≈550) is wider than the zone, which is correct — the zone says "typical is ~zero difference"; the CI speaks to precision.

**Axis domain recommendations** (per D-04, starting from p05/p95, round to nearest 0.1 pp):

| Metric | Suggested `domain` (half-width from 0) |
|--------|----------------------------------------|
| flaw_rate | 2.0 pp |
| low_clock | 0.5 pp |
| hasty | 1.2 pp |
| unrushed | 1.7 pp |
| opening | 0.8 pp |
| middlegame | 1.3 pp |
| endgame_phase | 0.5 pp (expand if reversed zone invisible) |
| miss | 0.5 pp |
| lucky | 0.5 pp |
| reversed | 0.3 pp (expand so hairline zone is visible) |
| squandered | 0.4 pp |
| hasty_miss | 0.4 pp |
| low_clock_miss | 0.2 pp |
| mistake | 1.0 pp |
| blunder | 1.4 pp |

Note: for the two near-degenerate zones (reversed, low_clock_miss), the domain is deliberately wider than p05/p95 to ensure the hairline zone is at least 1px wide at typical chart widths. The executor should verify render at 80px (3-column desktop minimum) and expand as needed — this is a UI-only tweak.

**`flaw_delta_zones.py` registry shape** (mirrors `endgame_zones.py`):

```python
@dataclass(frozen=True)
class FlawDeltaZoneSpec:
    zone_lo: float      # Q1 in pp (verbatim from §5)
    zone_hi: float      # Q3 in pp (verbatim from §5)
    domain: float       # axis half-width in pp (hand-set from p05/p95)
    # D-08: inverted sign — negative delta = fewer flaws = good.
    # The MiniBulletChart inverted mode uses zone_lo/zone_hi directly;
    # no negation of the metric is needed.

FLAW_DELTA_ZONES: dict[str, FlawDeltaZoneSpec] = {
    "flaw_rate":      FlawDeltaZoneSpec(zone_lo=-0.5, zone_hi=+0.4, domain=2.0),
    "low_clock":      FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.0, domain=0.5),
    "hasty":          FlawDeltaZoneSpec(zone_lo=-0.3, zone_hi=+0.2, domain=1.2),
    "unrushed":       FlawDeltaZoneSpec(zone_lo=-0.4, zone_hi=+0.4, domain=1.7),
    "opening":        FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.8),
    "middlegame":     FlawDeltaZoneSpec(zone_lo=-0.3, zone_hi=+0.2, domain=1.3),
    "endgame_phase":  FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.5),
    "miss":           FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.5),
    "lucky":          FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.5),
    "reversed":       FlawDeltaZoneSpec(zone_lo=+0.0, zone_hi=+0.0, domain=0.3),
    "squandered":     FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.4),
    "hasty_miss":     FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.4),
    "low_clock_miss": FlawDeltaZoneSpec(zone_lo=+0.0, zone_hi=+0.0, domain=0.2),
    "mistake":        FlawDeltaZoneSpec(zone_lo=-0.2, zone_hi=+0.2, domain=1.0),
    "blunder":        FlawDeltaZoneSpec(zone_lo=-0.3, zone_hi=+0.2, domain=1.4),
}
```

---

## CI Method Recommendation

**Verdict: Use normal/t approximation. No bootstrap needed.**

**Rationale:**

1. **Gate floor is N=20 analyzed games** (D-09). At N=20 the t-distribution with 19 df gives a 95% CI multiplier of 2.093 vs the z-score 1.96. The difference is 6.8%. Given that zone bands are calibrated at ±0.1–0.5 pp precision, the 6.8% t-vs-z discrepancy is below the threshold of practical concern. Use `scipy.stats.t.ppf(0.975, df=n-1)` (or the approximation `1.96 + 2.2/n`) if exactness matters; use `1.96` for simplicity.

2. **Distribution shape.** The per-game deltas are bounded rational numbers (count differences divided by a positive integer). For common tags (flaw_rate, unrushed, middlegame), most games contribute a nonzero delta so the distribution is reasonably continuous. For rare tags (reversed, low_clock, low_clock_miss), the distribution is heavily zero-inflated. But at N≥20 the CLT is adequate for the zero-inflated case because the CI is capturing the mean delta, not the individual game distribution. Bootstrap would give the same result at much higher compute cost.

3. **Precedent.** `app/services/eval_confidence.py` already implements Wald z-test CI (same math: mean ± 1.96·SE) for the MG-entry eval metric. No scipy. The same pattern applies here.

4. **Concrete reason to bootstrap: none found.** Bootstrap is warranted when the statistic is non-linear (e.g. ratio of medians) or the tails are extreme. Mean-of-per-game-deltas is linear; the CLT holds at N=20.

**No new CI utility needed.** `eval_confidence.py`'s `compute_eval_confidence_bucket` computes exactly this (sum, sumsq, n → mean ± 1.96·SE). The flaw comparison endpoint can duplicate the same 3-line computation inline (it needs only mean + CI, not the p-value bucketing), or extract a shared `_mean_ci(values: list[float]) → tuple[float, float, float]` helper. The existing `score_confidence.py` (Wilson) is NOT reused — it is for proportions, and FLAWCMP-02 is voided.

**Implementation shape:**

```python
import math

def compute_mean_ci(
    values: list[float],
    z: float = 1.96,
) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) for a list of per-game deltas.

    Returns (0.0, 0.0, 0.0) when values is empty.
    Returns (mean, mean, mean) when n == 1 (undefined variance).
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean = sum(values) / n
    if n == 1:
        return mean, mean, mean
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    se = math.sqrt(variance / n)
    half = z * se
    return mean, mean - half, mean + half
```

---

## SQL Aggregation Shape

**Pattern: per-game GROUP BY with LEFT JOIN, then Python mean+CI.**

The existing `fetch_stats_aggregates` uses a single-scan `COUNT(*) FILTER` pattern across all games (no per-game granularity). For the comparison endpoint we need per-game deltas so that the game is the independence unit. Two approaches exist:

**Approach A (recommended): SQL GROUP BY game_id, Python mean+CI.**

```sql
-- Returns one row per (game_id, user_id) with both-side tag counts
-- and user_moves. Python aggregates into mean delta + CI.
SELECT
  f.game_id,
  gm.user_moves,
  -- player counts (NOT is_opponent)
  COUNT(*) FILTER (WHERE NOT is_opponent_expr(f.ply, g.user_color)
                    AND f.severity IN (1,2)) as player_flaw_count,
  COUNT(*) FILTER (WHERE NOT is_opponent_expr(f.ply, g.user_color)
                    AND f.tempo = 0) as player_low_clock,
  ... (one FILTER pair per metric)
  -- opponent counts
  COUNT(*) FILTER (WHERE is_opponent_expr(f.ply, g.user_color)
                    AND f.severity IN (1,2)) as opp_flaw_count,
  ...
FROM game_flaws f
JOIN games g ON g.id = f.game_id
JOIN (
  SELECT game_id,
    CASE WHEN user_color='white' THEN FLOOR(ply_count::float/2)
         ELSE CEIL(ply_count::float/2) END as user_moves
  FROM games WHERE user_id = :user_id AND ply_count > 0
) gm ON gm.game_id = f.game_id
WHERE f.user_id = :user_id
  AND f.game_id IN (SELECT game_id FROM analyzed_games_subq)
  AND f.game_id IN (SELECT id FROM filtered_games_subq)
GROUP BY f.game_id, gm.user_moves
```

But: some analyzed games have zero `game_flaws` rows (clean games = 0 delta, per §5 all-analyzed-games basis note). Use LEFT JOIN:

```sql
-- Anchor on the analyzed+filtered games list; LEFT JOIN game_flaws
SELECT
  ag.game_id,
  ag.user_moves,
  COALESCE(COUNT(f.ply) FILTER (WHERE NOT is_opponent_expr(f.ply, g.user_color)
                                 AND f.severity IN (1,2)), 0) as player_flaw_count,
  ...
FROM (
  SELECT g.id as game_id,
    CASE WHEN g.user_color='white' THEN FLOOR(g.ply_count::float/2)
         ELSE CEIL(g.ply_count::float/2) END as user_moves,
    g.user_color
  FROM games g
  WHERE g.user_id = :user_id
    AND g.id IN (analyzed_subq)
    AND g.id IN (filtered_subq)
    AND g.ply_count IS NOT NULL AND g.ply_count > 0
) ag
LEFT JOIN game_flaws f ON f.game_id = ag.game_id AND f.user_id = :user_id
LEFT JOIN games g ON g.id = ag.game_id
GROUP BY ag.game_id, ag.user_moves, ag.user_color
```

**Pitfall:** games with `ply_count IS NULL` or `ply_count = 0` must be excluded from the denominator. The `_analyzed_game_ids_subquery` does not filter on `ply_count`; the per-game delta query must add `AND g.ply_count IS NOT NULL AND g.ply_count > 0`.

**Pitfall:** The `is_opponent_expr` SQL expression is in `query_utils.py` but takes ORM column references, not raw SQL strings. For the new repository function, use the same `case()` idiom:

```python
from app.repositories.query_utils import is_opponent_expr
# Works directly in a FILTER clause:
func.count().filter(~is_opponent_expr(GameFlaw.ply, Game.user_color))
```

**Approach B: pure Python aggregation after fetching all rows.** Load all `game_flaws` rows for the analyzed+filtered set (same as `fetch_page_game_flaws` but unscoped to a page), then compute per-game deltas in Python. Simpler query, heavier Python loop. For a user with 1000 analyzed games and 10 flaws/game, this is 10,000 rows — acceptable. For heavy users (5000+ games), SQL GROUP BY is preferable.

**Recommendation: Approach A (SQL GROUP BY)**. The SQL GROUP BY returns at most one row per analyzed game (N≤10,000 for realistic users), which Python reduces to 15 mean+CI computations. It is the same shape used by the benchmark's `chapter5.py` generator. The left-join anchor ensures clean games contribute a 0-delta row.

**Important: `is_opponent_expr` sign convention.** From `query_utils.py`:
- even ply → white mover → is_opponent iff `user_color == 'black'`
- odd ply → black mover → is_opponent iff `user_color == 'white'`

For the flaw-rate numerator (player flaws), use `player_only_gate(GameFlaw.ply, Game.user_color)`.
For opponent flaws, use `is_opponent_expr(GameFlaw.ply, Game.user_color)`.

**Severity filter interaction (FLAWCMP-03/D-13):** The severity filter (`flaw_severity` kwarg) narrows both the player and opponent denominators' `game_flaws` rows. When severity filter = blunders-only, ALL 15 bullets are computed on the blunders-only basis — including the tempo/phase/opportunity/impact/combo bullets. The zone tooltip caveat (D-13) covers this. No per-bullet special-casing needed.

**Performance note:** The per-game GROUP BY scan replaces the flat `COUNT(*) FILTER` pattern. For users with many analyzed games (>2000), the query may be heavier. Given the existing `fetch_stats_aggregates` already scans `game_flaws` with a JOIN, this is acceptable. Add `EXPLAIN ANALYZE` to the plan's verification steps.

---

## Endpoint Shape Recommendation

**Recommendation: new sibling endpoint `GET /api/library/flaw-comparison`.**

**Rationale:**
1. The existing `GET /api/library/flaw-stats` payload (`FlawStatsResponse`) is already consumed by two callers (`GlobalStats.tsx` and `FlawsTab.tsx` unfiltered probe). Adding 15 bullets + zone bounds + analyzed_n gate + per-bullet CI would more than double the payload size and break the existing TypeScript type.
2. The `useLibraryFlawStats` query key is `['library-flaw-stats', params]` — adding new fields would require frontend type migration across multiple consumers.
3. The new endpoint can have a simpler type surface: it only returns the comparison block, not trend or band data.
4. The planner can assign the backend and frontend tasks independently.

**Response shape sketch:**

```python
class FlawBullet(BaseModel):
    tag: str                    # e.g. "flaw_rate", "hasty_miss"
    delta: float | None         # mean per-game delta (pp), None when zero events for both sides
    ci_low: float | None        # 95% CI lower bound (pp)
    ci_high: float | None       # 95% CI upper bound (pp)
    player_events: int          # total player-side events across analyzed games
    opp_events: int             # total opponent-side events
    zone_lo: float              # Q1 from flaw_delta_zones registry
    zone_hi: float              # Q3 from flaw_delta_zones registry
    domain: float               # axis half-width from registry
    has_zone: bool = True       # False for future tactic-motif bullets (FLAWUI-04)

class FlawComparisonResponse(BaseModel):
    bullets: list[FlawBullet]   # always 15 entries, ordered by family
    analyzed_n: int             # analyzed games count (the gate value)
    analyzed_gate: int = 20     # the minimum floor (D-09)
    below_gate: bool            # analyzed_n < 20 → show CTA, not bullets
```

**Router:** `APIRouter(prefix="/library", tags=["library"])` with `@router.get("/flaw-comparison")`. Follows the existing router convention.

**Query key:** `['library-flaw-comparison', params]` — independent of `['library-flaw-stats', params]`.

---

## Existing Code Integration Points

### Backend

**`_analyzed_game_ids_subquery(user_id)`** — already in `library_repository.py`. Returns a subquery of game_ids where eval coverage ≥ 90% (the EVAL_COVERAGE_MIN constant). The new endpoint uses this unchanged to gate the analyzed set.

**`_filtered_games_base(user_id, **filter_kwargs)`** — already in `library_repository.py`. Returns a `SELECT Game.id` base with all filter conditions applied. The new endpoint uses this as the filtered games anchor.

**`count_filtered_and_analyzed`** — already returns `(total_n, analyzed_n)`. The new endpoint calls this first to check the gate (analyzed_n ≥ 20) before running the expensive per-game delta query.

**`apply_game_filters`** — already handles all 9 filter dimensions including the `flaw_severity` EXISTS path. The comparison endpoint passes `flaw_severity` through identically.

**`is_opponent_expr` / `player_only_gate`** — already in `query_utils.py`. Use these in the per-game delta query's FILTER clauses. Do not inline the ply-parity logic.

**`_SEVERITY_INT`, `_TEMPO_INT`, `_PHASE_INT`** — in `game_flaws_repository.py`. Use these for the FILTER integer comparisons (e.g. `f.tempo == _TEMPO_INT["low-clock"]`).

**No new Alembic migration needed.** Phase 113 already materialized both-side flaws; `games.ply_count` was added in Phase 114.1. The new endpoint only reads.

### Frontend

**`MiniBulletChart`** — already supports `ciLow`/`ciHigh` whiskers, asymmetric `(neutralMin, neutralMax)` zones, per-instance `domain`, and `barColor`. The only gap is the **inverted-color mode** (D-08).

**Inverted-color mode analysis.** Currently:
```typescript
if (value >= absNeutralMax) fillColor = ZONE_SUCCESS;  // right of zone = green
else if (value >= absNeutralMin) fillColor = ZONE_NEUTRAL;
else fillColor = ZONE_DANGER;  // left of zone = red
```
For the flaw delta comparison, negative = fewer flaws = **good**, so the background zone layout must invert: left-of-zone should paint green (ZONE_SUCCESS), right-of-zone should paint red (ZONE_DANGER). The value bar color follows the same inversion.

The cleanest approach is a new `invertColors?: boolean` prop:

```typescript
interface MiniBulletChartProps {
  // ... existing props ...
  /**
   * When true, inverts the zone color semantics: values LEFT of the neutral band
   * paint ZONE_SUCCESS (fewer flaws = good); values RIGHT paint ZONE_DANGER.
   * Used for flaw-delta bullets where negative delta = better performance.
   * Default false (preserves existing callers unchanged).
   */
  invertColors?: boolean;
}
```

In the color logic:
```typescript
const rawPositiveColor = invertColors ? ZONE_DANGER : ZONE_SUCCESS;
const rawNegativeColor = invertColors ? ZONE_SUCCESS : ZONE_DANGER;

if (value >= absNeutralMax) fillColor = rawPositiveColor;
else if (value >= absNeutralMin) fillColor = ZONE_NEUTRAL;
else fillColor = ZONE_DANGER;  // becomes rawNegativeColor
```

Background zone order remains [left=ZONE_DANGER, center=ZONE_NEUTRAL, right=ZONE_SUCCESS] but inverts to [left=ZONE_SUCCESS, center=ZONE_NEUTRAL, right=ZONE_DANGER]. The existing `Endgame` and `Openings` callers do not pass `invertColors`, so their rendering is unchanged.

**`FlawTagDistribution.tsx`** — this component and its tests are deleted as part of D-02. It implements the per-family proportion bars that Zone 3 of `FlawStatsPanel` currently renders. The new `FlawComparisonGrid` component replaces it. Check for any imports of `FlawTagDistribution` outside `FlawStatsPanel.tsx` before deleting (grep shows it is only used there).

**`FlawStatsBand`** — stays, but the `NormToggle` is removed and the band is fixed to per-100 (D-02). The Band component itself likely has no internal normalization mode; the toggle is in `FlawStatsPanel.tsx`.

**`MetricStatPopover`** — the existing pattern in `frontend/src/components/popovers/MetricStatPopover.tsx`. Each bullet gets a `HelpCircle`-trigger popover with: definition paragraph, sign convention line ("negative = fewer flaws than equally-rated opponents = good"), tempo-interaction caveat for clock-conditioned tags (`low-clock`, `hasty`, `unrushed`, `low-clock+miss`, `hasty+miss`), exposure caveat for `squandered`/`lucky` (D-03 from 114-CONTEXT: "reads partly as how often the situation arose"), severity-basis caveat (D-13), and filter line (D-14). Text-xs is allowed per CLAUDE.md exception for info popovers.

**`FlawStatsPanel.tsx` Zone 3 replacement:** The panel currently renders `<FlawTagDistribution ... />` as Zone 3. This is replaced by `<FlawComparisonGrid />` which consumes a second `useQuery` hook (`useLibraryFlawComparison`). The panel's loading/error/empty ternary chain is extended with the new below-gate CTA state.

**`useLibraryFlawStats` query** — unchanged. The new `useLibraryFlawComparison` hook follows the same pattern in `hooks/useLibrary.ts` with query key `['library-flaw-comparison', params]`.

---

## Architecture Patterns

### New `flaw_delta_zones.py` Registry

Mirror `endgame_zones.py` shape: a frozen dataclass `FlawDeltaZoneSpec` and a `FLAW_DELTA_ZONES: dict[str, FlawDeltaZoneSpec]` dict. No TS codegen, no `generate_zones_ts.py` script. The endpoint reads from the dict and includes zone bounds in the response payload.

No `assign_zone` helper needed (the frontend renders the zone bands as MiniBulletChart props; the backend does not classify into weak/typical/strong for this surface).

### New `fetch_flaw_comparison` Repository Function

```python
async def fetch_flaw_comparison(
    session: AsyncSession,
    user_id: int,
    analyzed_game_ids_subq: Subquery,
    filtered_games_subq: Subquery,
) -> list[dict]:
    """Return one row per analyzed+filtered game with player/opp counts for all 15 metrics."""
```

Returns a list of dicts (or a list of ORM-lite tuples). The service iterates over the list once to compute per-game deltas, then calls `compute_mean_ci` per metric.

### Service Layer

```python
async def get_flaw_comparison(
    session: AsyncSession,
    user_id: int,
    **filter_kwargs,
) -> FlawComparisonResponse:
    total_n, analyzed_n = await count_filtered_and_analyzed(session, user_id, **filter_kwargs)
    if analyzed_n < FLAW_COMPARISON_GATE:  # = 20
        return FlawComparisonResponse(bullets=[], analyzed_n=analyzed_n, below_gate=True)
    analyzed_subq = _analyzed_game_ids_subquery(user_id)
    filtered_subq = _filtered_games_base(user_id, **filter_kwargs).subquery()
    rows = await fetch_flaw_comparison(session, user_id, analyzed_subq, filtered_subq)
    bullets = _compute_bullets(rows)  # per-metric mean+CI from per-game deltas
    return FlawComparisonResponse(bullets=bullets, analyzed_n=analyzed_n, below_gate=False)
```

### Frontend Grid Layout

```
FlawComparisonGrid (new component, replaces FlawTagDistribution zone)
  ├── FlawFamilySection (Severity)
  │   ├── FlawBulletRow (Flaw Rate)    ← MiniBulletChart[invertColors=true] + MetricStatPopover
  │   ├── FlawBulletRow (Mistakes)
  │   └── FlawBulletRow (Blunders)
  ├── FlawFamilySection (Tempo)
  │   ├── FlawBulletRow (Low-Clock)
  │   ├── FlawBulletRow (Hasty)
  │   └── FlawBulletRow (Unrushed)
  ... (Phase, Opportunity, Impact, Combos)
```

Grid layout: `grid grid-cols-1 lg:grid-cols-3 gap-2` (D-03: 3-col desktop, 1-col mobile). Family section headers span full width (`lg:col-span-3`).

### Bullet Row States (D-10, D-11)

Each `FlawBulletRow` renders one of three states:
1. **Normal**: `delta` + CI whisker bar + muted zone background + value label + popover trigger.
2. **Zero-event placeholder** (`player_events == 0 && opp_events == 0`): muted label "No events in current filter" at row position. Grid does not reflow.
3. **Below-gate CTA** (parent-level): rendered by `FlawComparisonGrid` in place of the full grid when `below_gate === true`. Shows current analyzed count + message about lichess server analysis.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Per-game delta aggregation | Custom loop over raw rows | SQL GROUP BY with LEFT JOIN anchor (clean games = 0 delta) |
| CI computation | Ad-hoc formula | Reuse `eval_confidence.py` pattern (mean ± 1.96·SE, stdlib math.sqrt) |
| Player/opponent split | Inline ply % 2 conditionals | `is_opponent_expr` / `player_only_gate` from `query_utils.py` |
| Filter application | Duplicating WHERE clauses | `_filtered_games_base` + `apply_game_filters` |
| Analyzed game gating | Re-implementing eval coverage check | `_analyzed_game_ids_subquery` |
| MiniBulletChart color inversion | New component | `invertColors` prop on existing `MiniBulletChart` |
| Tooltip popover | New disclosure framework | `MetricStatPopover` pattern |

---

## Common Pitfalls

### Pitfall 1: Clean Games (zero flaws) Must Count as Zero Deltas
**What goes wrong:** Joining `game_flaws` directly excludes games with no flaws. Cohort users with cleaner play appear to have fewer analyzed games.
**How to avoid:** LEFT JOIN or use the analyzed+filtered games list as the anchor, then LEFT JOIN `game_flaws`.
**Why it matters:** §5 all-analyzed-games basis is what the zone Q1/Q3 values were computed on. Using flawed-games-only basis would produce deltas ~4× larger (per §5 header note).

### Pitfall 2: `ply_count` Null Check
**What goes wrong:** `user_moves = FLOOR(ply_count/2)` divides by zero when `ply_count IS NULL`.
**How to avoid:** Filter `g.ply_count IS NOT NULL AND g.ply_count > 0` in the per-game query. Games with null ply_count are excluded from the delta calculation.

### Pitfall 3: Severity Filter Narrows the Delta Basis
**What goes wrong:** When `flaw_severity = ["blunder"]`, only blunder rows are in `game_flaws` for the filter. The per-game delta for `flaw_rate` becomes "blunder delta" not "M+B delta".
**How to avoid:** This is intentional (D-13). The tooltip caveat (D-13) discloses it. Do not suppress the zone for severity-filtered views.

### Pitfall 4: `is_opponent_expr` Sign Convention
**What goes wrong:** Inverting ply parity logic (e.g. treating even plies as opponent when user is white) gives wrong delta sign.
**How to avoid:** Always use `is_opponent_expr(GameFlaw.ply, Game.user_color)` from `query_utils.py`. Do not inline the ply % 2 logic. The convention is: even ply = white mover = is_opponent when user_color = 'black'.

### Pitfall 5: `asyncio.gather` on Single Session
**What goes wrong:** Running multiple queries concurrently on the same `AsyncSession`.
**How to avoid:** Execute queries sequentially per CLAUDE.md `§Critical Constraints`. The comparison endpoint runs: `count_filtered_and_analyzed` → (gate check) → `fetch_flaw_comparison`. Two sequential queries maximum.

### Pitfall 6: MiniBulletChart `neutralMin/neutralMax` Are Offsets from `center`
**What goes wrong:** Passing Q1/Q3 directly as `neutralMin`/`neutralMax` when `center ≠ 0`.
**How to avoid:** `center = 0` for all flaw-delta bullets (the reference point is zero delta). Pass Q1 directly as `neutralMin` and Q3 as `neutralMax`. The `absNeutralMin = center + neutralMin` math gives `absNeutralMin = Q1` as expected.

### Pitfall 7: NormToggle Deletion Must Remove `per_game` from Schema
**What goes wrong:** Removing `NormToggle` from the frontend but leaving `per_game` in the `FlawStatsResponse`/API causes dead code and type drift.
**How to avoid:** The `rates.per_game` field in `FlawStatsResponse` can stay (removal is optional), but the `NormalizationMode` type and `NormToggle` component must be removed from `FlawStatsPanel.tsx`, and the rendering path that branches on `per_game` mode must be removed.

### Pitfall 8: `FlawTagDistribution` Deletion Breaks Knip
**What goes wrong:** If `FlawTagDistribution.tsx` has named exports still referenced elsewhere, knip will fail CI.
**How to avoid:** Grep for `FlawTagDistribution` across the frontend before deleting. Currently only `FlawStatsPanel.tsx` imports it — safe to delete both component and its `__tests__/` file.

---

## Sample Gate Plumbing (FLAWCMP-05)

The `_analyzed_game_ids_subquery` + `count_filtered_and_analyzed` already return `analyzed_n`. The service checks `analyzed_n < 20` and returns `below_gate=True` in the response. No new DB mechanism needed.

The `analyzed_n` returned is the same value already shown in `FlawStatsBand` (the `X% analyzed` denominator pill). The CTA state should display: "You need at least 20 analyzed games to see flaw comparisons. You currently have N. To analyze more, use [lichess server analysis / link]."

The `FlawStatsBand` and `FlawTrendChart` (Zones 1 and 2) remain live when `below_gate=True`. Only Zone 3 (the bullet grid) shows the CTA.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), Vitest (frontend) |
| Backend config | `pyproject.toml` (pytest), `vitest.config.ts` (frontend) |
| Quick run (backend) | `uv run pytest tests/services/test_flaw_comparison.py -x` |
| Quick run (frontend) | `npm test -- --run frontend/src/components/charts/MiniBulletChart.test.tsx` |
| Full suite | `uv run pytest -n auto -x` / `npm test -- --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLAWCMP-01 | Unified per-game delta + CI returned for all 15 metrics | unit | `pytest tests/services/test_flaw_comparison.py::test_all_15_bullets -x` | No — Wave 0 |
| FLAWCMP-01 | CI half-width = 1.96 × SD / sqrt(N) | unit | `pytest tests/services/test_flaw_comparison.py::test_ci_formula -x` | No — Wave 0 |
| FLAWCMP-03 | All game filters applied; zone bounds in response | unit | `pytest tests/services/test_flaw_comparison.py::test_filter_plumbing -x` | No — Wave 0 |
| FLAWCMP-03 | Severity filter narrows delta basis but zones stay visible | unit | `pytest tests/services/test_flaw_comparison.py::test_severity_filter_zones -x` | No — Wave 0 |
| FLAWCMP-04 | Combo metrics (hasty+miss, lc+miss) returned correctly | unit | `pytest tests/services/test_flaw_comparison.py::test_combos -x` | No — Wave 0 |
| FLAWCMP-05 | `below_gate=True` when analyzed_n < 20; all 15 bullets when ≥20 | unit | `pytest tests/services/test_flaw_comparison.py::test_sample_gate -x` | No — Wave 0 |
| FLAWCMP-05 | Zero-event bullet has delta=None (not 0.0) | unit | `pytest tests/services/test_flaw_comparison.py::test_zero_event_bullet -x` | No — Wave 0 |
| FLAWUI-01 | MiniBulletChart `invertColors` mode: success LEFT, danger RIGHT | unit | `npm test -- --run frontend/src/components/charts/MiniBulletChart.test.tsx` | Yes (extend) |
| FLAWUI-06 | All bullet rows have `data-testid` + ARIA labels | unit | `npm test -- --run frontend/src/components/library/__tests__/FlawComparisonGrid.test.tsx` | No — Wave 0 |

### Wave 0 Gaps
- `tests/services/test_flaw_comparison.py` — covers FLAWCMP-01/03/04/05 with synthetic `game_flaws` fixtures; use `AsyncSession` with in-memory Postgres (existing test infra supports this)
- `frontend/src/components/library/__tests__/FlawComparisonGrid.test.tsx` — covers FLAWUI-06 testid/ARIA + below-gate CTA render
- `MiniBulletChart.test.tsx` extension — add `invertColors=true` test cases to the existing test file (already tested `barColor` in this file)

### Sampling Rate
- **Per task commit:** relevant test file for the task (e.g. `test_flaw_comparison.py` for backend tasks)
- **Per wave merge:** full suite `uv run pytest -n auto -x && npm test -- --run`
- **Phase gate:** full suite green before `/gsd-verify-work`

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users Bearer JWT — same as all library endpoints |
| V4 Access Control | yes | `user_id` from auth context only; never from request parameter (IDOR pattern already enforced in existing library endpoints) |
| V5 Input Validation | yes | Pydantic v2 on all query params; filter kwargs validated same as existing `get_flaw_stats` |
| V6 Cryptography | no | No new secrets |

**No new IDOR vectors:** The new endpoint scopes all queries via `user_id` from the authenticated session (same as `get_flaw_stats`). The `game_flaws` repository already has the IDOR pattern (T-108-07/08) for all existing query paths.

**No hash exposure:** The response payload is `FlawBullet` with delta/CI/zone/event-count fields. No `*_hash` columns are accessed or returned.

---

## Open Questions (RESOLVED)

1. **`ply_count` completeness in dev data.** The FLAWCMP-04 query filtered `ply_count IS NOT NULL AND ply_count > 0` and returned N=556/550 analyzed games. If a significant fraction of analyzed games have null `ply_count`, those games are excluded from the delta. Check: `SELECT COUNT(*) FROM games WHERE user_id IN (28,44) AND ply_count IS NULL` to confirm. Expected: zero (ply_count was added in Phase 114.1 and should be populated for all games).
   - **RESOLVED:** `ply_count` is a Phase 114.1 field populated at import for all games; Environment Availability table confirms it as available. The per-game LEFT-JOIN aggregation guards zero/null user-move games regardless. No planning impact.

2. **Impact threshold pending implementation.** `flaw-tag-definitions.md` notes the `reversed`/`squandered` thresholds are recalibrated targets (2026-06-09).
   - **RESOLVED (orchestrator verified against git, 2026-06-11):** The recalibration is NOT pending — it **landed 2026-06-09 23:03** (commit `35f742af` "recalibrate reversed/squandered ES thresholds to round-eval anchors", a code feat, plus `4192f4b9` tooltip sync). The §5 benchmark zones were then **refreshed 2026-06-11 14:29** (commit `ebcb6170` "refresh §5 flaw-delta zones on the mate-ladder game_flaws basis"), i.e. AFTER both the recalibration AND the mate-ladder grading (`c403467e`, 2026-06-11 11:06). **Therefore the §5 zone constants extracted in this research are CURRENT, not stale** — A2's "computed on OLD thresholds" assumption was inverted. The only residual is whether DEV `game_flaws` was backfilled to this same (mate-ladder + recalibrated) basis for UAT; that data-freshness check is encoded as a BLOCKING A2 pre-check in Plan 02 Task 4 (a data check, not a code or zone-derivation gate). No re-derivation of zone constants is required.

3. **`is_opponent_expr` in raw SQL (repository).** The repository function will use SQLAlchemy ORM expressions, which naturally accept `is_opponent_expr`. If the executor opts for raw SQL (via `text()`), the expression must be inlined manually. Recommend sticking with ORM expressions to inherit the tested helper.
   - **RESOLVED:** Both plans use SQLAlchemy ORM expressions (the recommended path), inheriting the tested `is_opponent_expr` helper. No raw `text()` SQL.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `games.ply_count` is populated for all analyzed games in dev | SQL aggregation shape | Per-game denominator would be zero; those games excluded from delta computation |
| A2 | ~~Impact threshold `/gsd-quick` has NOT yet landed~~ **CORRECTED: recalibration landed 2026-06-09; §5 refreshed 2026-06-11 on the post-recalibration mate-ladder basis → zone constants are CURRENT** | Zone constants table | Residual only: dev `game_flaws` may need reclassify/backfill to match the §5 basis for UAT — gated by Plan 02 Task 4 A2 pre-check (data, not code) |
| A3 | `FlawTagDistribution.tsx` is only imported by `FlawStatsPanel.tsx` (grep supports this) | Don't Hand-Roll | If imported elsewhere: deletion breaks compile; must update all callers |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev DB | All backend tests, FLAWCMP-04 validation | Yes | 18 (Docker) | — |
| `game_flaws` with opponent rows | Backend delta computation | Yes | Phase 113 backfilled | — |
| `games.ply_count` populated | Per-game user_moves denominator | Yes | Phase 114.1 | — |

---

## Sources

### Primary (HIGH confidence — verified against live code or dev DB)
- `app/repositories/library_repository.py` — `fetch_stats_aggregates`, `_analyzed_game_ids_subquery`, `_filtered_games_base`, `count_filtered_and_analyzed`
- `app/repositories/query_utils.py` — `is_opponent_expr`, `player_only_gate`, `apply_game_filters`
- `app/services/library_service.py` — `get_flaw_stats`, filter kwargs shape
- `app/services/eval_confidence.py` — CI computation pattern (Wald z, stdlib math.sqrt)
- `app/services/endgame_zones.py` — registry dataclass shape to mirror
- `frontend/src/components/charts/MiniBulletChart.tsx` — prop interface, color logic
- `frontend/src/components/library/FlawStatsPanel.tsx` — existing zone 3 structure
- `reports/benchmark/benchmarks-latest.md` §5.1–§5.16 — all Q1/Q3 and p05/p95 values
- Dev DB live query (users 28/44) — FLAWCMP-04 CI-width finding
- `.planning/phases/114-benchmark-flaw-delta-zone-computation/114-CONTEXT.md` — D-01 formula, D-03 caveat, D-10 hand-authored mandate
- `.planning/notes/flaw-tag-definitions.md` — all 15 tag definitions + DB columns

### Secondary (MEDIUM confidence — confirmed by code structure + design docs)
- `.planning/phases/115-you-vs-opponent-comparison-api-bullet-grid-ui/115-CONTEXT.md` — all locked decisions D-01 through D-16
- `.planning/REQUIREMENTS.md` §FLAWCMP + §FLAWUI — requirement text and voiding of FLAWCMP-02

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are in use; no new packages
- SQL aggregation shape: HIGH — derived from existing `fetch_stats_aggregates` + §5 generator pattern
- Zone constants: HIGH — verbatim from benchmark report, exact numbers verified
- FLAWCMP-04 finding: HIGH — direct live DB query on dev users 28/44
- CI method: HIGH — precedent in `eval_confidence.py`, statistics reasoning verified
- Frontend inverted-color mode: HIGH — component source read; prop interface clear
- MiniBulletChart `neutralMin/neutralMax` semantics: HIGH — component and test source read

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (30 days for stable codebase; re-verify §5 if impact-threshold gsd-quick lands before execution)

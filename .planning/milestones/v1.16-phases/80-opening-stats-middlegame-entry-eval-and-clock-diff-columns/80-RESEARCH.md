# Phase 80: Opening stats — middlegame-entry eval and clock-diff columns - Research

**Researched:** 2026-05-03
**Domain:** Backend SQL aggregation + statistical helper + frontend chart extension on existing FlawChess Openings → Stats subtab
**Confidence:** HIGH

## Summary

Phase 80 is a **downstream consumer** of Phase 79 (`phase` SmallInteger + middlegame-entry Stockfish evals). All upstream data is already populated on dev / benchmark / prod (rounds 1-3 of the v1.15 cutover, 2026-05-03). No migrations, no new infrastructure — purely additive SQL columns, a new statistical helper that mirrors `compute_confidence_bucket` shape, and frontend table/chart extensions that follow the established Material Breakdown / Endgame Clock Pressure patterns.

Three new metrics get added to **two reuses of `MostPlayedOpeningsTable`** (bookmarked openings + most-played openings, white + black, desktop + mobile): avg eval at MG entry (signed user-perspective, `MiniBulletChart` with 95% CI whisker), one-sample t-test confidence pill (low/medium/high, reusing the N≥10 / p<0.05 / p<0.10 thresholds), and avg clock diff at MG entry (`+8.2% (+24s)` formatter from `EndgameClockPressureSection`).

**Primary recommendation:** Land all three metrics as additional columns on the existing `query_position_wdl_batch` aggregation via a single LEFT JOIN to a per-(game_id, full_hash) middlegame-entry subquery — one round trip, one response payload, one TanStack Query cache slot. Use neutral zone `[-30 cp, +30 cp]` and bullet domain `±100 cp` based on the benchmark per-user-mean distribution (n=1638 users, mean=+0.86 cp, SD=62 cp, IQR `[-24.3, +33.1]`, p05/p95 `[-110.5, +86.9]`). Both Cohen's d marginal max values land in the **review** band (TC=0.215, ELO=0.256) — collapse to a **single global zone**, no per-cell stratification.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Per-game MG-entry row selection (`MIN(ply) WHERE phase=1`) | Database / SQL | — | Pure indexed aggregation; can fully use `ix_gp_user_endgame_game`-style window or correlated subquery |
| Avg eval + 95% CI computation | API / Backend | — | Needs color-flip helper + mate exclusion + N counting; SQL produces sums, Python finalizes for confidence helper |
| One-sample t-test (Wald approx) | API / Backend | — | Stdlib `math.erfc` only — sibling helper to `score_confidence.compute_confidence_bucket` |
| Clock-diff at MG entry | API / Backend | — | Reuses `_extract_entry_clocks` pattern; per-game user vs opp clock at entry ply |
| Confidence pill rendering | Frontend Server (SSR) | — | Static React component; theme-driven badge |
| `MiniBulletChart` whisker overlay | Frontend Server (SSR) | — | Pure presentational; SVG/CSS overlay on existing component |
| Hide ChessBoard on Stats subtab (desktop) | Frontend Server (SSR) | — | Conditional render gated by `activeTab === 'stats'` |
| Mobile second-line stack | Frontend Server (SSR) | — | Existing `MobileMostPlayedRows` extension |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Eval column (D-01..D-03)**
- **D-01:** Render the avg eval as a `MiniBulletChart` (signed, user-perspective, in pawns). No separate `±std` text in the cell — spread information is conveyed by the CI whisker.
- **D-02:** Extend `MiniBulletChart` with optional `ciLow?` / `ciHigh?` props that draw a thin horizontal whisker with end caps over the value bar. When the props are omitted the component renders unchanged (so existing call sites in the Endgame Material Breakdown table are unaffected).
- **D-03:** Hide the chess board on the Openings → Stats subtab (desktop) to free horizontal space for the new columns. Mobile already collapses the board area, so this aligns the two layouts.

**Confidence column (D-04)**
- **D-04:** Surface the t-test confidence as a separate column with a `low` / `medium` / `high` pill, mirroring the opening-insights card visual style. Reuse the same N≥10 gate and one-sided p-value thresholds (`p<0.05` → high, `p<0.10` → medium, else low) as `OPENING_INSIGHTS_CONFIDENCE_*` constants in `app/services/opening_insights_constants.py`. The statistical procedure is different (one-sample t-test on continuous eval vs trinomial Wald on WDL), so a new helper is needed; the threshold semantics carry over.

**Clock diff column (D-05)**
- **D-05:** Render avg clock diff at middlegame entry as `+8.2% (+24s)` — pct of base time with absolute seconds in parentheses, signed. Reuse the same `formatSignedSeconds` / pct-of-base formatter used by `EndgameClockPressureSection` so the two clock-diff cells read identically across the app.

**Mobile layout (D-06)**
- **D-06:** On mobile, each opening row becomes a small stacked card. The top line keeps the existing 3-col grid (name + games + WDL bar). A second line below stacks the three new metrics: bullet chart (with CI whisker) → confidence pill → clock diff. Everything visible without taps; no new collapse/expand behavior.

**Bullet chart zones (D-07)**
- **D-07:** Calibration deferred to research (this document). See `## Bullet Chart Zone Calibration` below for the data-driven recommendation.

### Claude's Discretion

- **Mate handling at middlegame entry.** Rare but possible (forced mate found at depth 15 right out of the opening). Sensible default: exclude `eval_mate IS NOT NULL` rows from the mean (eval is undefined as a continuous quantity for forced-mate positions); include them in `total` for the WDL counts (already counted there today). Researcher / planner can confirm with a quick benchmark-DB count of how many MG-entry rows have `eval_mate IS NOT NULL`.
- **Backend payload shape.** Extending the existing `OpeningWDL` schema with new optional fields (`avg_eval_pawns`, `eval_ci_low`, `eval_ci_high`, `eval_n`, `eval_p_value`, `eval_confidence`, `avg_clock_diff_pct`, `avg_clock_diff_seconds`, `clock_diff_n`) is the obvious shape — single round trip, single response model. Planner to confirm.
- **SQL aggregation pattern.** The middlegame-entry row per game is `MIN(ply)` filtered to `phase = 1`. Planner picks between (a) a window function `ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ply) WHERE phase = 1` or (b) a correlated subquery / `DISTINCT ON`. The endgame conv/recov code in `app/repositories/endgame_repository.py` has prior art for the same shape on endgame-entry — researcher should reference it.
- **Sortability of new columns.** Probably yes (eval value descending makes intuitive sense; clock diff descending too). Defer to planner if it complicates the existing table state.
- **Tooltip / column header info popovers.** Worthwhile so users understand what "eval at middlegame entry" means and why CI matters. Planner adds these following the pattern in `EndgameClockPressureSection.tsx` (lines 158-163 use `Tooltip` with explainer paragraphs).

### Deferred Ideas (OUT OF SCOPE)

- **Tabled phase-aware analytics ideas** (`.planning/notes/phase-aware-analytics-ideas.md` §"Tabled for later") — Middlegame ELO, Opening ELO, "where do you bleed centipawns" decomposition, phase-conditional conv/recov, time-vs-phase correlation, phase-flip game search filter, opponent diff per phase, LLM narrative upgrade. None of these are in Phase 80 scope; they live in the v1.16 brainstorm pool for follow-on phases.
- **Phase 81: Endgame entry eval — twin-tile decomposition in Endgame Overall Performance.** Different page (Endgames, not Openings), different data subset (endgame-entry rows, not middlegame-entry). Independent of Phase 80; no shared components beyond `MiniBulletChart`.
- **Concept-explainer accordion update.** Phase 81 plans an "Avg eval at endgame entry" paragraph in its accordion. Phase 80 has no concept-explainer accordion on the Stats subtab today; if one is wanted later, it's a separate UX phase.

## Project Constraints (from CLAUDE.md)

The planner must verify all of these are honored:

- **No `asyncio.gather` on the same `AsyncSession`** — sequential within the session.
- **`ty` must pass with zero errors** — explicit return types on all new functions, `Sequence[str]` not `list[str]` for params taking `list[Literal[...]]`, Pydantic models at boundaries.
- **No magic numbers** — neutral zone bounds, bar domain, statistical thresholds all named constants. Reuse the existing `OPENING_INSIGHTS_CONFIDENCE_*` constants for the t-test confidence helper.
- **`color_sign = +1 if user_color == 'white' else -1`** — match the convention in `_classify_endgame_bucket` exactly. Do NOT invent a new sign convention.
- **Theme constants via `theme.ts`** — confidence pill colors (`ZONE_DANGER` / `ZONE_NEUTRAL` / `ZONE_SUCCESS` already exist; whisker color is foreground/50 to match zero line).
- **`data-testid` on every interactive element** — confidence pill, info popover, mobile card.
- **Sentry capture on non-trivial except blocks** in services and routers.
- **Variables out of error messages** — pass via `sentry_sdk.set_context`.

## Phase Requirements

This phase has no formal `REQ-IDs`. The CONTEXT.md decisions D-01..D-07 act as the requirement set; the planner should map each plan to the decisions it implements.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | MiniBulletChart for avg eval (signed, user-perspective, in pawns) | `## Bullet Chart Zone Calibration` (neutral [-30, +30] cp; domain ±100 cp); `## Code Examples` (color-flip pattern) |
| D-02 | Extend MiniBulletChart with optional `ciLow`/`ciHigh` props | `## MiniBulletChart Extension` (whisker overlay design + clipping concerns) |
| D-03 | Hide ChessBoard on Openings → Stats subtab desktop | `## Stats Subtab Board Hide` (existing `activeTab === 'stats'` switch + ChessBoard at line 1278) |
| D-04 | One-sample t-test confidence pill (low/medium/high) | `## One-Sample T-Test Helper` (sibling to `compute_confidence_bucket`, stdlib only, mate-excluded N counting) |
| D-05 | Clock diff at MG entry as `+X% (+Ys)` | `## Clock Diff at MG Entry — SQL Pattern` (reuse `_extract_entry_clocks` ply-array shape OR window approach) |
| D-06 | Mobile second-line stacking (bullet → pill → clock diff) | `## MostPlayedOpeningsTable Mobile Layout` |
| D-07 | Bullet chart zone calibration | `## Bullet Chart Zone Calibration` (Cohen's d collapse verdict + benchmark-DB distribution) |

## Standard Stack

This phase adds **no new dependencies**. Everything is built from the existing stack.

### Core (existing)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x | HTTP layer (existing `/stats/most-played-openings` route) | Already in use |
| SQLAlchemy 2.x async | 2.x | ORM for new aggregation | Already in use |
| asyncpg | latest | Postgres driver | Already in use |
| Pydantic v2 | latest | Schema validation | Already in use |
| React 19 + TS + Vite | latest | Frontend | Already in use |
| Recharts (already used elsewhere) | — | Not strictly required — `MiniBulletChart` is pure CSS/divs, the whisker can stay CSS-only | — |

### Statistical Library Decision

**Recommendation: stdlib only, no scipy.** [VERIFIED: grep `from scipy\|import scipy` returns 0 hits in `app/`]

Rationale:
1. The existing `score_confidence.compute_confidence_bucket` uses `math.erfc` for the Wald p-value computation. The new helper should mirror that style for consistency.
2. With N≥10 (the gate is forced low otherwise), the **t-distribution and z-distribution differ by < 6%** at p=0.05. The existing pattern's z-approximation (one-sided Wald) is statistically defensible; introducing `scipy.stats.ttest_1samp` for sub-1% precision improvement would add a heavy dependency.
3. Project ethos: pyproject.toml lists 11 runtime deps, all critical. scipy alone is ~30 MB.

Implementation: `app/services/eval_confidence.py` (sibling to `score_confidence.py`), exposing one function:

```python
def compute_eval_confidence_bucket(
    eval_sum: float, eval_sumsq: float, n: int
) -> tuple[Literal["low", "medium", "high"], float, float, float]:
    """Return (confidence, p_value, mean, ci_half_width).

    SE = sqrt(variance / n) where variance = (sumsq - n * mean^2) / (n - 1) (Bessel-corrected).
    z = mean / SE
    p = 2 * 0.5 * erfc(|z| / sqrt(2))  # two-sided (matches "different from zero" framing)
    Bucket: n < 10 -> low; p < 0.05 -> high; p < 0.10 -> medium; else low.
    ci_half_width = 1.96 * SE  # 95% CI for the bullet-chart whisker.
    """
```

Edge cases:
- `n == 0`: return `("low", 1.0, 0.0, 0.0)`. No data, no signal.
- `n == 1`: variance undefined (division by `n-1 = 0`); return `("low", 1.0, mean, 0.0)`. Forced low by N gate anyway.
- All evals identical (variance=0): SE=0, z=±∞ if mean≠0 ⇒ `("high", 0.0, mean, 0.0)` after N gate; if mean=0 ⇒ `("low", 1.0, 0.0, 0.0)`.
- NaN inputs: not possible — eval_cp is `SmallInteger`, color_sign is `±1`, both non-null by SQL filter.

**Two-sided vs one-sided framing:** The opening-insights helper uses **one-sided** because a finding card asks a directional question ("is this score worse/better than 50%?"). For Phase 80, the avg eval at MG entry can be positive OR negative and both are meaningful (positive = systematically outplaying, negative = systematically getting worse positions). Use **two-sided** p-value to match the "is this different from zero?" framing. [ASSUMED — planner / discuss-phase to confirm direction.]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib t-test (z approx) | `scipy.stats.ttest_1samp` | scipy adds ~30 MB; precision gain at N≥10 < 1% on p; broken consistency with `score_confidence.py` |
| Single combined SQL | Separate queries: WDL + MG eval + clock | More round trips, more cache slots, harder to keep filter params in sync |
| Window function `ROW_NUMBER() OVER (PARTITION BY game_id) WHERE phase=1` | `MIN(ply) GROUP BY game_id WHERE phase=1` correlated subquery | Both work; planner picks based on EXPLAIN — see SQL Aggregation Pattern below |

## Architecture Patterns

### System Architecture Diagram

```
GET /api/stats/most-played-openings
       │ (filter params: time_control, platform, rated, opponent, recency, opp_gap)
       ▼
[stats router]──────────────────────────────────────────────┐
       │                                                     │
       ▼                                                     │
[stats_service.get_most_played_openings()]                   │
       │                                                     │
       ├──> query_top_openings_sql_wdl()  ── existing        │ all queries share filter params
       │                                                     │
       ├──> query_position_wdl_batch()    ── existing        │ via apply_game_filters()
       │                                                     │
       └──> NEW: query_opening_mg_metrics_batch()  ◄─────────┘
                  │
                  │  WHERE gp.full_hash IN (hashes)
                  │  JOIN games + filters
                  │  JOIN mg_entry subquery (MIN(ply) WHERE phase=1 GROUP BY game_id)
                  │  Returns: {full_hash: MgEntryMetrics(eval_sum, eval_sumsq, eval_n, mate_n,
                  │                                       clock_diff_sum, clock_diff_n,
                  │                                       base_time_seconds_sum)}
                  ▼
[Python finalizer]
  - For each opening: compute_eval_confidence_bucket(eval_sum, eval_sumsq, eval_n)
  - clock_diff_pct_mean = (clock_diff_sum / clock_diff_n) / (base_time_seconds_sum / clock_diff_n) * 100
  - Build OpeningWDL with new fields
       │
       ▼
[OpeningWDL schema] ── extended with optional fields
       │
       ▼
[Frontend: useMostPlayedOpenings + bookmark tsData paths]
       │
       ▼
[MostPlayedOpeningsTable (desktop) / MobileMostPlayedRows (mobile)]
       │
       ├──> MiniBulletChart(value=avg_eval/100, ciLow=..., ciHigh=..., neutralMin=-0.30, neutralMax=+0.30, domain=1.0)
       ├──> ConfidencePill(confidence)
       └──> ClockDiffCell(pct, secs) ── reusing formatSignedPct + formatSignedSeconds helpers
```

### Recommended Project Structure

```
app/services/
├── eval_confidence.py        # NEW — sibling to score_confidence.py, t-test helper
├── score_confidence.py       # existing — Wald confidence for WDL
├── stats_service.py          # MODIFIED — call new repository, finalize metrics, build OpeningWDL
└── endgame_service.py        # READ-ONLY — _classify_endgame_bucket signs eval; reference, do not modify

app/repositories/
├── stats_repository.py       # MODIFIED — add query_opening_mg_metrics_batch()
└── endgame_repository.py     # READ-ONLY — _extract_entry_clocks pattern reference

app/schemas/
└── stats.py                  # MODIFIED — extend OpeningWDL with optional new fields

frontend/src/components/charts/
└── MiniBulletChart.tsx       # MODIFIED — add ciLow?/ciHigh? props (additive, default-undefined)

frontend/src/components/stats/
└── MostPlayedOpeningsTable.tsx  # MODIFIED — add 3 columns (desktop) and mobile second line

frontend/src/components/insights/  # READ-ONLY reference
└── OpeningFindingCard.tsx    # confidence pill visual style to mirror

frontend/src/pages/
└── Openings.tsx              # MODIFIED — hide ChessBoard on `activeTab === 'stats'`

frontend/src/types/
└── stats.ts                  # MODIFIED — mirror schema additions
```

### Pattern 1: Two-Sided Wald T-Test on a Small Sample (stdlib)

**What:** Compute one-sample two-sided p-value against `mu = 0` using only `math.erfc`.
**When to use:** N≥10 small-sample mean test where adding scipy is overkill and t↔z difference is < 1% at the relevant p-thresholds.

```python
# Source: pattern derived from app/services/score_confidence.py + textbook Wald
import math
import statistics

def two_sided_p(mean: float, se: float) -> float:
    """Two-sided p-value for H0: mean == 0, given mean and standard error of the mean."""
    if se == 0.0:
        return 0.0 if mean != 0.0 else 1.0
    z = mean / se
    # 2 * 0.5 * erfc(|z|/sqrt(2)) = erfc(|z|/sqrt(2)); range [0, 1].
    return math.erfc(abs(z) / math.sqrt(2.0))
```

### Pattern 2: Per-Game MG-Entry Selection in SQL

**What:** For each game, find `MIN(ply) WHERE phase = 1` — the first ply that crossed into middlegame phase.
**When to use:** Consuming MG-entry data (eval, clock) per game, joined to per-game filters.

```sql
-- Pattern A: Correlated subquery via DISTINCT ON (Postgres-specific, simpler)
SELECT DISTINCT ON (game_id) game_id, ply, eval_cp, eval_mate, clock_seconds
FROM game_positions
WHERE user_id = :user_id AND phase = 1
ORDER BY game_id, ply;

-- Pattern B: GROUP BY HAVING + JOIN (portable, often the planner's preferred shape)
WITH mg_entry AS (
  SELECT game_id, MIN(ply) AS entry_ply
  FROM game_positions
  WHERE user_id = :user_id AND phase = 1
  GROUP BY game_id
)
SELECT m.game_id, gp.eval_cp, gp.eval_mate, gp.clock_seconds, opp_gp.clock_seconds AS opp_clock
FROM mg_entry m
JOIN game_positions gp ON gp.game_id = m.game_id AND gp.ply = m.entry_ply
JOIN game_positions opp_gp ON opp_gp.game_id = m.game_id AND opp_gp.ply = m.entry_ply + 1;
```

**Pattern A** is more compact but emits one row per game; you still need to JOIN games to filter and group by `full_hash`.
**Pattern B** is the canonical FlawChess shape (mirrors `endgame_repository.first_endgame` CTE in `endgame_service` `_classify_endgame_bucket` query).

The opponent clock at MG-entry-row+1 needs a second JOIN (or `LEAD()` window). The endgame analog (`_extract_entry_clocks`) does this in Python by aggregating `array_agg(clock_seconds ORDER BY ply)` and walking the array. **Reusing the array_agg + Python walk pattern is the lower-risk shape** — it sidesteps the second self-JOIN and exactly mirrors the endgame code.

[VERIFIED: the existing `query_clock_stats_rows` in `app/repositories/endgame_repository.py:626-735` uses `array_agg(GamePosition.clock_seconds ORDER BY GamePosition.ply.asc())` and `_extract_entry_clocks` in `endgame_service.py:1121-1142` walks the array using `ply % 2 == user_parity`. The same shape works for MG entry by aggregating positions where `phase = 1`.]

### Pattern 3: Confidence Pill (Frontend)

**What:** Render a small badge with low/medium/high pill, mirroring `OpeningFindingCard`.
**When to use:** Surfacing the t-test confidence in the table cell.

[ASSUMED — planner should grep for the actual pill component name and import path. The Phase 75/76 v1.14 work introduced this; likely path is `frontend/src/components/insights/OpeningFindingCard.tsx` per CONTEXT.md canonical refs. If a reusable `ConfidencePill` component doesn't exist yet, extracting one is recommended over duplicating inline JSX.]

### Anti-Patterns to Avoid

- **Re-implementing `_classify_endgame_bucket`'s sign convention.** The helper is the single source of truth: `sign = 1 if user_color == 'white' else -1; user_eval = sign * eval_cp`. Use the same expression at the SQL or Python level. Don't introduce a new convention.
- **Running per-opening MG-entry queries in a loop.** Use the batch shape that already exists for `query_position_wdl_batch` — one query, hash IN(...) clause.
- **Adding scipy.** Use `math.erfc` (already in stdlib) — see "Standard Stack" above.
- **Computing CI half-width on the frontend.** Pass `eval_ci_low` / `eval_ci_high` from the backend so the formula lives in one place (consistent with how `p_value` is computed backend-side in `score_confidence`).
- **Forgetting mate exclusion.** `eval_mate IS NOT NULL` rows are forced wins/losses, not continuous evals. Exclude from mean and CI; document the row count separately if useful.
- **Hardcoding magic centipawn thresholds.** All bounds (neutral zone, bullet domain, eval threshold for advantage) must be named constants — frontend in `theme.ts` or a sibling constants module.
- **Casting `time_control_bucket` without `::text`.** SQLAlchemy emits the cast for `Game.time_control_bucket` (it's a Postgres enum). The benchmark queries had to add `::text` casts; verify the new query's SA Column comparisons aren't tripping on this.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color-flip eval to user perspective | New helper | Use the same `sign = 1 if user_color == 'white' else -1` expression as `_classify_endgame_bucket` | Single source of truth; tested |
| One-sided / two-sided confidence pill bucketing | New thresholds | Reuse `OPENING_INSIGHTS_CONFIDENCE_MIN_N`, `_HIGH_MAX_P`, `_MEDIUM_MAX_P` | Visual + semantic consistency with v1.14 |
| Clock-diff seconds + percent formatter | New formatter | Reuse `formatSignedSeconds` + `formatSignedPct` from `EndgameClockPressureSection.tsx` (lines 62-75) — extract to shared util if not already shared | "Two clock-diff cells should look identical" (D-05) |
| 95% CI computation | Compute on frontend | Compute on backend, return `eval_ci_low` / `eval_ci_high` | Keeps statistical math co-located with `compute_eval_confidence_bucket` |
| `MiniBulletChart` re-implementation | Recharts re-skinning | Extend existing CSS-only component with optional whisker | D-02 explicitly: "additive, no behavior change when omitted" |
| Per-(user, opening) game filtering | New filter implementation | Reuse `apply_game_filters()` in `app/repositories/query_utils.py` — same single source of truth used by `query_position_wdl_batch` | CLAUDE.md: "Never duplicate filter logic in individual repositories." |

**Key insight:** The repository plumbing for opening-stats aggregations is already battle-tested across phases 36, 38, 51, 70 — the new metrics are **additional aggregation columns on the same query shape**, not a new pipeline.

## Runtime State Inventory

Phase 80 is greenfield consumption of Phase 79 data. No renames, no migrations, no string replacements.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — pure read of existing `phase` + `eval_cp` + `eval_mate` + `clock_seconds` columns | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

## Bullet Chart Zone Calibration

**(D-07 deliverable — primary research output.)**

Per the `/benchmarks` skill methodology, calibrated against the benchmark DB (selected users, status='completed', equal-footing filter, sparse `(2400, classical)` cell excluded from marginals).

### Per-Game Distribution at MG Entry [VERIFIED: benchmark-DB query 2026-05-03]

User-perspective eval (`sign * eval_cp`) at the MG-entry row, mate-excluded, NULL-excluded:

| n_games | mean_cp | std_cp | p05 | p25 | p50 | p75 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 608,426 | +2.15 | 244.21 | -438.0 | -95.0 | +1.0 | +99.0 | +444.0 |

**Shape:** Strong central peak at zero (median = +1 cp), wide IQR `[-95, +99]`, symmetric tails. Per-game noise (SD ≈ 244 cp) is ~3× larger than per-user-mean noise (SD ≈ 62 cp).

### Per-User-Mean Distribution [VERIFIED: benchmark-DB query 2026-05-03]

Closer analog to what the UI displays — average across all MG-entry games per user (≥30 game floor; for small-N per-opening cells the spread will be wider):

| n_users | mean_of_means | sd_of_means | p05 | p10 | p25 | p50 | p75 | p90 | p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,638 | +0.86 | 61.99 | -110.5 | -73.4 | -24.3 | +5.9 | +33.1 | +66.2 | +86.9 |

### Cohen's d Marginal Verdict [VERIFIED: SQL marginals + Python pairwise computation]

Per-user-mean MG-entry eval, sparse cell excluded:

| Axis | Levels | max \|d\| | Pair | Verdict |
|------|--------|---:|------|---------|
| TC | 4 | **0.215** | bullet (mean=-4.87, n=423) vs classical (mean=+10.80, n=257) | **review → collapse** |
| ELO | 5 | **0.256** | 800 (mean=-11.37, n=326) vs 2000 (mean=+6.01, n=339) | **review → collapse** |

Both `max |d|` values land in the **review** band [0.2, 0.5). Per skill methodology: *"default to single zone unless a UI argument warrants splitting."* No UI argument here — the mean shifts (-11 cp at 800 → +6 cp at 2000, or -5 cp bullet → +11 cp classical) are tiny relative to the per-user SD (~62 cp). **Recommendation: collapse both axes — one global zone.**

### 5×4 Heatmap (per-user p50, sanity check) [VERIFIED]

```
             bullet   blitz   rapid   classical
   800        -13.1     3.6     8.6     -39.5
  1200         -1.0     6.7    13.6     +25.9
  1600         -3.2    12.7     0.7     +18.2
  2000        +14.5     2.3     7.7      +9.9
  2400         +2.4    -1.5     9.1      n=2*  (excluded)
```

The (800, classical) cell has n=40 only and shows a -39.5 cp p50 — likely small-n noise rather than a real population shift. Even at face value, this is < 1 cell-SD from zero.

### Recommended Constants [CITED: derived from benchmark distribution above]

For UI rendering — values in **pawns** (frontend convention) so `MiniBulletChart` props read naturally:

| Constant | Value (cp) | Value (pawns) | Rationale |
|----------|-----------:|--------------:|-----------|
| `EVAL_NEUTRAL_MIN_PAWNS` | -30 | -0.30 | Half of user-mean IQR — most users sit inside |
| `EVAL_NEUTRAL_MAX_PAWNS` | +30 | +0.30 | Symmetric (population mean is +0.86 cp ≈ 0) |
| `EVAL_BULLET_DOMAIN_PAWNS` | ±100 | ±1.00 | Caps slightly past user-mean p95 (+86.9 cp); per-game outliers (per-row UI cells with low N) get clamped, which is fine |

A row whose 95% CI whisker touches the domain edge tells the same story the user wants: "this opening is wildly skewed (rare/extreme)" — clamping is correct.

**Edge case for per-opening cells:** A user's per-opening avg eval over N=10..30 games will have wider CI than the per-user-mean distribution above. Per-game SD ≈ 244 cp ⇒ SE at N=10 ≈ 77 cp, at N=30 ≈ 45 cp. The 95% CI whisker (~1.96 × SE) will routinely span ±150 cp at N=10. The neutral zone of ±30 cp is much narrower than typical CI — meaning many low-N rows will have a CI whisker spanning multiple zones, which is exactly the visual signal "we don't have enough data to tell." This is the desired UX.

### Mate Frequency at MG Entry [VERIFIED: benchmark-DB query 2026-05-03]

Of 1,299,252 games that reached middlegame phase:
- 857,935 (66.0%) have `eval_cp` (cleanly bucketable)
- **4,457 (0.34%)** have `eval_mate` (a forced mate found at depth 15 right out of the opening)
- 436,860 (33.6%) have neither (NULL) — likely games where the MG-entry ply fell outside the eval'd window, or where backfill hasn't yet covered the position

**UI implication:** With mate at < 1%, no special UI treatment is needed. Exclude `eval_mate IS NOT NULL` rows from the mean (they're forced wins/losses, not continuous evals) and exclude NULL rows. Document the exclusion in the InfoPopover. Optionally surface `eval_n` (the count of games actually used in the mean) on hover so users can see when their per-opening N is much lower than their total game count.

## SQL Aggregation Pattern

The new query joins three things: opening hashes (input), the existing per-(user, full_hash) game-filter pipeline, and the per-game MG-entry row.

### Recommended Shape (mirrors `query_position_wdl_batch`)

```python
# In app/repositories/stats_repository.py

async def query_opening_mg_metrics_batch(
    session: AsyncSession,
    user_id: int,
    hashes: list[int],
    color: Literal["white", "black"] | None,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str = "human",
    recency_cutoff: datetime.datetime | None = None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> dict[int, OpeningMgMetrics]:
    """Return {full_hash: OpeningMgMetrics} for games passing through each opening.

    Aggregates per-game user-perspective eval at MG entry and per-game user-vs-opp
    clock diff at MG entry. Joins the existing apply_game_filters() pipeline so
    filter semantics match the WDL aggregation exactly.
    """
    if not hashes:
        return {}

    # MG-entry row per game: MIN(ply) WHERE phase = 1
    mg_entry_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            func.min(GamePosition.ply).label("entry_ply"),
        )
        .where(GamePosition.user_id == user_id, GamePosition.phase == 1)
        .group_by(GamePosition.game_id)
        .subquery("mg_entry")
    )

    # Per-game DISTINCT JOIN to dedupe (user_id, full_hash) appearing at multiple plies
    dedup = (
        select(
            GamePosition.full_hash.label("full_hash"),
            Game.id.label("game_id"),
            Game.user_color.label("user_color"),
            Game.base_time_seconds.label("base_time_seconds"),
        )
        .join(Game, GamePosition.game_id == Game.id)
        .where(GamePosition.user_id == user_id, GamePosition.full_hash.in_(hashes))
        .distinct(GamePosition.full_hash, Game.id)
    )
    if color is not None:
        dedup = dedup.where(Game.user_color == color)
    dedup = apply_game_filters(dedup, time_control, platform, rated, opponent_type,
                                recency_cutoff,
                                opponent_gap_min=opponent_gap_min,
                                opponent_gap_max=opponent_gap_max)
    dedup = dedup.subquery("dedup")

    # Aggregate per-(full_hash) using array_agg + Python walk pattern OR SQL math.
    # Reuse the endgame_repository array_agg approach for clock diffs.
    # ... (see implementation note below)
```

**Implementation note:** Since clock-diff requires user_clock at entry_ply and opp_clock at entry_ply+1, two cleaner choices exist:

1. **Two `LEFT JOIN game_positions`** at `entry_ply` and `entry_ply + 1` — clean, pure SQL, no Python walking.
2. **`array_agg(ply ORDER BY ply)` + `array_agg(clock_seconds ORDER BY ply)` from `phase = 1` rows + `_extract_entry_clocks` in Python** — exactly mirrors `endgame_repository.query_clock_stats_rows`.

Pick #1: it's a smaller diff, doesn't require shipping multi-MB ply/clock arrays per row over the wire, and the planner's two indexed JOINs on `(game_id, ply)` are fast (the existing `ix_gp_user_game_ply` partial covers `ply BETWEEN 0 AND 17` only; for MG entry plies 6-30+ we rely on the FK index `ix_gp_game_id` plus the `(user_id, ...)` indexes).

**Index check:** [VERIFIED: `app/models/game_position.py` index list]
- `ix_gp_game_id` (FK index on `game_id`)
- `ix_gp_user_endgame_game` partial: `WHERE endgame_class IS NOT NULL` — does NOT cover MG-phase rows
- `ix_gp_user_game_ply` partial: `WHERE ply BETWEEN 0 AND 17` — covers most MG-entry plies but not all
- No partial index exists today on `WHERE phase = 1`

For Phase 80, the existing `(user_id, game_id, ply)` partial index ([0, 17] range) covers the typical MG-entry ply range. **Run EXPLAIN ANALYZE on a representative user before shipping** — if a covering partial index `WHERE phase = 1 INCLUDE (eval_cp, eval_mate, clock_seconds)` would dramatically improve the plan, propose adding it. **Otherwise leave indexes alone** — adding indexes incurs write cost and we don't yet know the access pattern at scale.

[ASSUMED — planner / executor confirms via EXPLAIN ANALYZE on Adrian's user data (28k games, multi-TC) before merge.]

### Performance Concern — Pre/Post Comparison

The current `/api/stats/most-played-openings` for a heavy-user (Adrian, ~30k games, full filters) runs in <500 ms. Adding a third aggregation that joins game_positions twice could push that. **Validation requirement:** EXPLAIN ANALYZE before/after on dev DB at Adrian's user; flag if total > 1.5×.

## Common Pitfalls

### Pitfall 1: Sign Convention Drift
**What goes wrong:** Frontend computes `eval / 100` to convert to pawns but forgets the user-color sign flip; eval shows the wrong sign for black.
**Why it happens:** The color-flip is invisible at the SQL/Python boundary if the backend already signed the value. The frontend assumes "eval is just a number."
**How to avoid:** Sign the eval **at the backend** before serializing — return `avg_eval_pawns` already signed (positive = user better). Document this in the OpeningWDL field comment. Verification in Wave 0: a parametric test for white/black with same opening, identical games, asserts `white.avg_eval_pawns == -black.avg_eval_pawns`.
**Warning signs:** Confidence pill says "high" but value lands in neutral zone (sign was wrong, magnitude was right).

### Pitfall 2: Mate Inflation in Mean
**What goes wrong:** A handful of `eval_mate` rows get their `eval_cp` left as NULL or treated as ±infinity, polluting the mean.
**Why it happens:** SQL writers think `COALESCE(eval_cp, eval_mate * 10000)` is a sensible mate handling.
**How to avoid:** Filter `WHERE gp.eval_cp IS NOT NULL` in the aggregation. Document `eval_n < total` is intentional. Verification: a unit test on a fixture where one game has `eval_mate=3` and others have `eval_cp` confirms `eval_n` excludes the mate game.
**Warning signs:** Avg eval values like ±1000+ pawns showing up in production for users with no real outliers.

### Pitfall 3: Window Function Hangs on Large Users
**What goes wrong:** A `ROW_NUMBER() OVER (PARTITION BY game_id ORDER BY ply) WHERE phase = 1` plan picks a Nested Loop on a heavy user and hangs.
**Why it happens:** Same family of bug as the historical incident in `query_clock_stats_rows` (per-class HAVING / IN-subquery cardinality misestimate, see comment at line 671).
**How to avoid:** Use the GROUP BY + JOIN pattern (the same shape `_any_endgame_ply_subquery` uses). Run EXPLAIN ANALYZE on a heavy user (Adrian) before merge.
**Warning signs:** Query latency varies by user; some users see 500 ms, others 60 s+.

### Pitfall 4: Filter Mismatch Between WDL and MG Metrics
**What goes wrong:** `query_position_wdl_batch` filters games by recency, but the new MG-metrics query forgets recency or uses different opponent-gap bounds. Result: total = 100 games, but `eval_n` somehow = 130. Debugging nightmare.
**Why it happens:** New repository function reimplements filter logic instead of reusing `apply_game_filters()`.
**How to avoid:** **Always** thread the filter params through `apply_game_filters()` (CLAUDE.md rule). Wave 0 fixture should exercise mismatched filter scenarios to catch this.
**Warning signs:** `eval_n > total` for any opening row.

### Pitfall 5: Clock at MG Entry is NULL
**What goes wrong:** Some games (particularly older lichess imports from chess.com) lack `clock_seconds` annotations. The MG-entry row has `clock_seconds IS NULL` and the diff computation produces NaN.
**Why it happens:** chess.com PGN exports may omit `%clk`; lichess always has it.
**How to avoid:** Filter `WHERE user_clock IS NOT NULL AND opp_clock IS NOT NULL` in the diff aggregation. Track `clock_diff_n` separately from `eval_n` so the UI can dim the cell when `clock_diff_n < N_min`.
**Warning signs:** Clock-diff values of NaN or wildly out-of-range %.

### Pitfall 6: CI Whisker Clipped at Domain Edge
**What goes wrong:** A row with mean=+50 cp and CI=[+45, +250] has its right whisker cap clipped at the domain edge (+100 cp).
**Why it happens:** No special handling for whisker overflow.
**How to avoid:** Visual: when `ciHigh > domain` or `ciLow < -domain`, render an open-ended whisker (no cap on the clipped side, like `[+45, →]`). Explicit affordance in `MiniBulletChart` extension. Wave 0 visual test for this case.
**Warning signs:** Tooltip says "+45 to +250 cp" but visually the whisker looks like "+45 to +100 cp" — mismatch.

### Pitfall 7: Stats Subtab Hide Misses Mobile / Other Subtabs
**What goes wrong:** The conditional that hides ChessBoard accidentally hides it on the Insights or Games subtab too, or mobile already-hidden behavior gets broken.
**Why it happens:** Mobile uses a different layout entirely; the desktop board is at line 1278 inside `<TabsContent>` parent flex container. Hiding requires conditional CSS class on the `w-[400px]` container, not removing the `<ChessBoard>` element.
**How to avoid:** Inspect line 1276-1316 of `Openings.tsx`. The flex parent at line 1276 wraps the board container (line 1277, `w-[400px] shrink-0`) and the tab content container (line 1317, `flex-1 min-w-0`). To hide the board on Stats subtab desktop: add `${activeTab === 'stats' ? 'hidden' : ''}` to the board container's class. Do NOT remove or reorder the JSX tree — `<ChessBoard>` instance preservation matters for chess.js state.
**Warning signs:** Move-list state resets when the user clicks Stats then back to Moves.

## Code Examples

### Color-flip + mate-aware aggregation in SQL

```sql
-- Per-game user-perspective eval at MG entry, mate-excluded
SELECT
  gp.full_hash,
  g.id AS game_id,
  CASE WHEN g.user_color = 'white' THEN 1 ELSE -1 END * gp_mg.eval_cp AS user_eval,
  gp_mg.eval_mate IS NOT NULL AS is_mate
FROM games g
JOIN game_positions gp ON gp.game_id = g.id  -- the opening hash row
JOIN mg_entry m ON m.game_id = g.id
JOIN game_positions gp_mg ON gp_mg.game_id = m.game_id AND gp_mg.ply = m.entry_ply
WHERE g.user_id = :user_id
  AND gp.full_hash IN :hashes
  AND gp_mg.eval_cp IS NOT NULL  -- mate AND null excluded from the mean
```

### MiniBulletChart whisker overlay (additive)

```tsx
// Source: extension of frontend/src/components/charts/MiniBulletChart.tsx
interface MiniBulletChartProps {
  value: number;
  neutralMin?: number;
  neutralMax?: number;
  domain?: number;
  /** Optional 95% CI lower bound (in domain units). */
  ciLow?: number;
  /** Optional 95% CI upper bound (in domain units). */
  ciHigh?: number;
  // ... existing props
}

// Inside the component, after the existing value bar div:
{ciLow !== undefined && ciHigh !== undefined && (() => {
  const ciLowClamped = Math.max(-domain, ciLow);
  const ciHighClamped = Math.min(domain, ciHigh);
  const lowOpen = ciLow < -domain;   // open-ended on the left
  const highOpen = ciHigh > domain;  // open-ended on the right
  const ciLowPct = toPct(ciLowClamped);
  const ciHighPct = toPct(ciHighClamped);
  return (
    <>
      {/* Whisker line */}
      <div
        className="absolute top-1/2 -translate-y-1/2 h-px bg-foreground/70"
        style={{ left: `${ciLowPct}%`, width: `${ciHighPct - ciLowPct}%` }}
      />
      {/* Left cap (suppressed when open-ended) */}
      {!lowOpen && (
        <div
          className="absolute top-1/4 bottom-1/4 w-px bg-foreground/70"
          style={{ left: `${ciLowPct}%` }}
        />
      )}
      {/* Right cap (suppressed when open-ended) */}
      {!highOpen && (
        <div
          className="absolute top-1/4 bottom-1/4 w-px bg-foreground/70"
          style={{ left: `${ciHighPct}%` }}
        />
      )}
    </>
  );
})()}
```

### Pydantic schema extension (additive)

```python
# app/schemas/stats.py
class OpeningWDL(BaseModel):
    # ... existing fields unchanged ...

    # Phase 80 additions — all optional so existing tests/clients keep working
    avg_eval_pawns: float | None = None  # signed, user-perspective; None when eval_n == 0
    eval_ci_low_pawns: float | None = None  # 95% CI lower bound; None when eval_n < 2
    eval_ci_high_pawns: float | None = None  # 95% CI upper bound
    eval_n: int = 0  # games used in the mean (mate-excluded, NULL-excluded)
    eval_p_value: float | None = None  # two-sided p-value vs zero
    eval_confidence: Literal["low", "medium", "high"] = "low"

    avg_clock_diff_pct: float | None = None  # signed % of base time; None when clock_diff_n == 0
    avg_clock_diff_seconds: float | None = None  # signed seconds
    clock_diff_n: int = 0  # games with both user and opp clock present at MG entry
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Material-imbalance + 4-ply persistence proxy for advantage | Stockfish eval at endgame entry / MG entry | v1.15 (2026-05-03) | All eval-driven analytics rely on the new column; Phase 80 is a downstream consumer |
| Per-game blunder localization (per-move eval) | Phase-transition eval (only entry/exit points eval'd) | Phase 79 design choice | Sufficient for "is the user better/worse at MG transition"; insufficient for blunder attribution |
| `ROW_NUMBER() OVER (PARTITION BY game_id) WHERE phase=1` window | `MIN(ply) GROUP BY game_id WHERE phase=1` (planned for Phase 80) | TBD by planner | Mirrors `_any_endgame_ply_subquery` pattern; lower planner risk |

**Deprecated/outdated:**
- `material_imbalance` proxy for endgame conv/recov — gone in v1.15 (Phase 78 REFAC-05).
- `/conv-recov-validation` skill — deleted 2026-05-03 (proxy gone, agreement metric undefined).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Two-sided p-value (vs one-sided) is the right framing for "avg eval differs from zero" | Standard Stack — Statistical Library Decision | If one-sided is preferred, the bucket numbers shift; cosmetic, not catastrophic. discuss-phase / planner to confirm |
| A2 | Stdlib `math.erfc` (Wald z) is acceptable instead of `scipy.stats.t` | Standard Stack — Statistical Library Decision | At N≥10 the difference is < 1% on p; if planner wants exact t, swap helper internals — public API unchanged |
| A3 | The `ConfidencePill` component already exists or has an extractable visual pattern | Pattern 3 + Pitfall 5 | If not, planner adds a small extraction task (~30 min) |
| A4 | The two LEFT JOIN approach for clock diff is faster than `array_agg` + Python walk | SQL Aggregation Pattern | Wave 0 EXPLAIN ANALYZE settles this; falling back to array_agg is a 10-line change |
| A5 | Adding new optional fields to `OpeningWDL` won't break TanStack Query cache or any frontend type guards | Code Examples — Pydantic schema | Verify in CI: TypeScript check + frontend tests; trivial to fix if it does |
| A6 | The 33.6% NULL-eval rate at MG entry on the benchmark DB is acceptable for the live UI (per-opening N counts will be reduced but still meaningful) | Mate Frequency at MG Entry | If users routinely see "N too low" for openings they play often, we may need to investigate why backfill missed those plies; not a Phase 80 blocker |
| A7 | The existing `(user_id, game_id, ply)` partial index covers most MG-entry queries efficiently | SQL Aggregation Pattern — Index check | If EXPLAIN ANALYZE shows a seq scan, planner adds a covering index migration (~15 min) |

## Open Questions

1. **Should the t-test use one-sided or two-sided framing?**
   - What we know: `score_confidence.compute_confidence_bucket` uses one-sided ("is score worse/better than 50%?"). For eval at MG entry, both directions are independently meaningful.
   - What's unclear: do users care about "I systematically enter MG worse" and "I systematically enter MG better" with the same threshold strictness?
   - Recommendation: two-sided. Planner / discuss-phase confirms.

2. **Does an `eval_n` cell-floor (e.g. < 5) suppress the bullet chart entirely, or just dim it?**
   - What we know: opening-insights cards mute the value when `confidence === "low"` per Phase 76 D-04 hotfix.
   - What's unclear: how does that translate to a chart? Render an empty box? An em-dash?
   - Recommendation: planner picks. Suggested: at `eval_n < 5` show "—" instead of the chart (the CI would span the entire domain anyway, conveying nothing).

3. **Sortability of the new columns.**
   - What we know: bookmarked/most-played tables are unsorted today; rows come back from the backend in a fixed order (most-played by game count, bookmarks by user-defined order).
   - What's unclear: does adding sort handles to 6 columns scope-creep into a UX redesign?
   - Recommendation: defer (CONTEXT.md "defer to planner"). Ship with no sort first; add sort as a v1.17 feature if users ask.

4. **Should the avg-eval column on bookmarked-openings rows respect the user's `match_side` (white_hash / black_hash) filter, or always use full_hash?**
   - What we know: bookmarks have a `match_side` column for "any match" / "system openings" filtering.
   - What's unclear: does the avg eval need to follow that filter?
   - Recommendation: planner confirms. Default: same as the WDL row's filter — whatever `query_position_wdl_batch` already does.

5. **NULL eval at MG entry rate (33.6%) — is this expected?**
   - What we know: 138K games have no eval anywhere (failed backfill or too-short games), 298K games have eval somewhere but not at MG-entry ply.
   - What's unclear: is the 298K residual a real bug, or expected (e.g., ply > eval window cap, or phase=1 row at ply 0 of a non-eval'd game)?
   - Recommendation: not a Phase 80 blocker — UI gracefully handles missing data. Surface `eval_n < total` honestly. If the rate is materially worse on prod (e.g. > 50%), file a follow-on debug task.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Backend | ✓ | 3.13.x | — |
| PostgreSQL 18 dev DB | Backend tests | ✓ (Docker) | 18 | `bin/reset_db.sh` if needed |
| Benchmark DB | Calibration (this research, not phase execution) | ✓ (Docker, healthy) | postgres:18-alpine on :5433 | — |
| Node 22 + Vite + Vitest | Frontend tests | ✓ | latest | — |
| `uv` | Dependency management | ✓ | latest | — |
| `scipy` | Statistical computation | ✗ | — | **Use `math.erfc` (stdlib)** — see Standard Stack |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** scipy (use stdlib).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 8.x + pytest-asyncio 0.23.x (`asyncio_mode = "auto"`) |
| Backend config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Backend quick run | `uv run pytest tests/services/test_stats_service.py tests/services/test_eval_confidence.py -x` |
| Backend full suite | `uv run pytest` |
| Frontend framework | Vitest + React Testing Library |
| Frontend quick run | `cd frontend && npm test -- src/components/charts/__tests__/MiniBulletChart.test.tsx` |
| Frontend full suite | `cd frontend && npm test` |
| Type check (CI gate) | `uv run ty check app/ tests/` (zero errors required) |
| Lint (CI gate) | `uv run ruff check . && uv run ruff format --check .` |
| Frontend lint | `cd frontend && npm run lint && npm run knip` |

### Phase Requirements → Test Map

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01 | Avg eval rendered as MiniBulletChart with signed pawn value | Unit (frontend) | `npm test -- src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx -t "avg eval"` | ❌ Wave 0 |
| D-02 | MiniBulletChart with `ciLow`/`ciHigh` props renders whisker; without props renders identically to v1.15 | Unit (frontend) | `npm test -- src/components/charts/__tests__/MiniBulletChart.test.tsx` | ❌ Wave 0 |
| D-02 (open-ended whisker) | Whisker without left cap when `ciLow < -domain` | Unit (frontend, visual-snapshot) | same as above | ❌ Wave 0 |
| D-03 | ChessBoard hidden on Stats subtab desktop, visible on Moves/Games/Insights | Integration (frontend) | `npm test -- src/pages/__tests__/Openings.stats-board.test.tsx` | ❌ Wave 0 |
| D-04 | Confidence pill: low (N<10) | Unit (backend) | `pytest tests/services/test_eval_confidence.py::test_low_when_n_below_min -x` | ❌ Wave 0 |
| D-04 | Confidence pill: high (N≥10, p<0.05) | Unit (backend) | `pytest tests/services/test_eval_confidence.py::test_high_when_p_below_005 -x` | ❌ Wave 0 |
| D-04 | Confidence pill: medium (N≥10, 0.05≤p<0.10) | Unit (backend) | `pytest tests/services/test_eval_confidence.py::test_medium_when_p_in_005_010 -x` | ❌ Wave 0 |
| D-04 | Edge: zero variance, mean≠0 → high; mean=0 → low | Unit (backend) | `pytest tests/services/test_eval_confidence.py::test_zero_variance_edges -x` | ❌ Wave 0 |
| D-05 | Clock diff at MG entry: user_clock at entry_ply, opp_clock at entry_ply+1 | Unit (backend) | `pytest tests/services/test_stats_service.py::test_mg_entry_clock_diff -x` | ❌ Wave 0 |
| D-06 | Mobile second-line stacks bullet → pill → clock diff | Unit (frontend) | `npm test -- src/components/stats/__tests__/MostPlayedOpeningsTable.mobile.test.tsx` | ❌ Wave 0 |
| D-07 | Neutral zone constant `[-0.30, +0.30]` and bullet domain `±1.00` referenced from theme/constants | Unit (frontend) | `npm test -- src/lib/__tests__/openingStatsZones.test.ts` | ❌ Wave 0 |
| sign correctness | white avg_eval = -black avg_eval for same opening + identical games | Integration (backend) | `pytest tests/services/test_stats_service.py::test_color_flip_symmetry -x` | ❌ Wave 0 |
| mate exclusion | `eval_n < total` when fixture has eval_mate row; mean unaffected | Unit (backend) | `pytest tests/services/test_stats_service.py::test_mate_excluded_from_mean -x` | ❌ Wave 0 |
| filter consistency | Recency / opponent-gap filters identical between WDL and MG metrics aggregations | Integration (backend) | `pytest tests/repositories/test_stats_repository.py::test_filter_consistency_wdl_vs_mg -x` | ❌ Wave 0 |
| ty compliance | All new helpers have explicit return types | CI gate | `uv run ty check app/ tests/` | ✅ existing |
| performance | EXPLAIN ANALYZE for the new aggregation < 1.5× the existing query on Adrian's user data | Manual (one-shot) | doc'd in plan; run pre-merge | n/a |

### Sampling Rate

- **Per task commit:** quick test run for the area touched (backend `test_eval_confidence.py` or frontend MiniBulletChart test).
- **Per wave merge:** full suite green (`uv run pytest && uv run ty check app/ tests/ && cd frontend && npm test`).
- **Phase gate:** full suite green + EXPLAIN ANALYZE perf check + manual UI smoke (board hidden on Stats; CI whisker visible at domain edges).

### Wave 0 Gaps

- [ ] `tests/services/test_eval_confidence.py` — covers D-04 (and Pitfall 1, 2)
- [ ] `tests/services/test_stats_service.py` (extend existing) — covers D-05, sign symmetry, mate exclusion, filter consistency. Add test fixtures for white/black symmetry.
- [ ] `tests/repositories/test_stats_repository.py` (extend existing) — covers SQL filter consistency
- [ ] `frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx` — covers D-02 including open-ended whisker
- [ ] `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx` — covers D-01, D-04 cell rendering
- [ ] `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.mobile.test.tsx` — covers D-06
- [ ] `frontend/src/pages/__tests__/Openings.stats-board.test.tsx` — covers D-03
- [ ] `frontend/src/lib/__tests__/openingStatsZones.test.ts` — covers D-07 constants

No new framework / config installs required.

## Security Domain

Phase 80 is read-only consumption of existing user data through the existing authenticated `/api/stats/most-played-openings` endpoint. No new attack surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (existing) | FastAPI-Users JWT — already enforced on the route |
| V3 Session Management | yes (existing) | Bearer JWT — already enforced |
| V4 Access Control | yes | Existing `current_user.id` filter — Phase 80 uses the same `user_id` scope; do NOT introduce a path that takes user_id from the request payload |
| V5 Input Validation | yes | Pydantic v2 query params (existing) — Phase 80 adds no new input |
| V6 Cryptography | no | No crypto; aggregations only |

### Known Threat Patterns for FastAPI + SQLAlchemy stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection on `hashes` IN clause | Tampering | SQLAlchemy parameterized queries via `.in_()` (existing); never f-string a hash list |
| Cross-user data leak via opening_hash collision | Information Disclosure | Always filter by `user_id` first, then `full_hash` IN(...) — existing pattern in `query_position_wdl_batch` |
| Performance DoS via heavy aggregation | DoS | EXPLAIN ANALYZE pre-merge; existing `apply_game_filters` keeps result sizes bounded |
| Eval data exposure through API | Information Disclosure | The eval is the user's own game data; existing access control already covers it |

## Sources

### Primary (HIGH confidence)
- `/home/aimfeld/Projects/Python/flawchess/.planning/phases/80-opening-stats-middlegame-entry-eval-and-clock-diff-columns/80-CONTEXT.md` — locked decisions and references
- `/home/aimfeld/Projects/Python/flawchess/CLAUDE.md` — project constraints (ty, async, Sentry, theme)
- `/home/aimfeld/Projects/Python/flawchess/app/services/score_confidence.py` — pattern to mirror
- `/home/aimfeld/Projects/Python/flawchess/app/services/opening_insights_constants.py` — confidence thresholds (verified values)
- `/home/aimfeld/Projects/Python/flawchess/app/services/endgame_service.py:164-211` — `_classify_endgame_bucket` color-flip helper, `EVAL_ADVANTAGE_THRESHOLD = 100`
- `/home/aimfeld/Projects/Python/flawchess/app/services/endgame_service.py:1121-1142` — `_extract_entry_clocks` reference for clock diff
- `/home/aimfeld/Projects/Python/flawchess/app/repositories/endgame_repository.py:626-735` — `query_clock_stats_rows` SQL pattern (array_agg + Python walk)
- `/home/aimfeld/Projects/Python/flawchess/app/repositories/stats_repository.py:338-415` — `query_position_wdl_batch` shape to mirror
- `/home/aimfeld/Projects/Python/flawchess/app/services/stats_service.py:240-373` — `get_most_played_openings` flow
- `/home/aimfeld/Projects/Python/flawchess/app/schemas/stats.py:41-65` — `OpeningWDL` schema to extend
- `/home/aimfeld/Projects/Python/flawchess/app/models/game_position.py` — column types and existing indexes
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/MiniBulletChart.tsx` — full API to extend
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/stats/MostPlayedOpeningsTable.tsx` — full structure to extend
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/components/charts/EndgameClockPressureSection.tsx:62-83, 226-380` — clock-diff formatter + mobile card pattern
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/pages/Openings.tsx:1276-1316, 1090-1152` — board container + Stats subtab structure
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/types/stats.ts` — frontend `OpeningWDL` to extend
- `/home/aimfeld/Projects/Python/flawchess/.claude/skills/benchmarks/SKILL.md` — calibration methodology + Cohen's d verdict thresholds + sparse-cell exclusion rule
- Benchmark DB queries (live, 2026-05-03) — distribution + collapse verdict (see `## Bullet Chart Zone Calibration`)

### Secondary (MEDIUM confidence)
- Cohen's d collapse verdict thresholds — derived from skill methodology, applied to live benchmark data
- ConfidencePill component existence — likely path inferred from CONTEXT.md (`OpeningFindingCard` reference); planner verifies

### Tertiary (LOW confidence)
- One-sided vs two-sided p-value framing for the t-test (A1) — needs user / planner confirmation
- 33.6% NULL-eval-at-MG-entry rate is acceptable (A6) — observed on benchmark DB; rate on prod for typical users may differ

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components already in use; stdlib-only path verified
- Architecture: HIGH — all integration points read directly from existing code; the SQL aggregation shape mirrors a battle-tested pattern
- Pitfalls: HIGH — sourced from in-repo bug-fix commit comments (e.g. `query_clock_stats_rows` historical bug at line 671)
- Bullet chart calibration: HIGH — live benchmark-DB queries with verified row counts, Cohen's d hand-computed
- Mate frequency: HIGH — verified count (4,457 mate / 1.3M MG-reaching games)
- Statistical helper: MEDIUM — z-approximation defensible, t-vs-z difference noted; one-sided/two-sided framing flagged for confirmation

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days; stable codebase, no upstream library churn expected)

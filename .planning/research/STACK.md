# Stack Research

**Domain:** Chess analytics platform — advanced analytics (ELO-adjusted endgame skill, cross-platform rating normalization, opening risk metrics)
**Researched:** 2026-04-04
**Confidence:** HIGH for computation approach; MEDIUM for lichess-to-chess.com normalization constants (empirical data varies)

---

## Scope Note

This document covers ONLY new capabilities needed for v1.8 (ELO-adjusted endgame skill, opening risk/volatility, statistical refinements).

The base stack (FastAPI, React 19, PostgreSQL, SQLAlchemy async, python-chess, TanStack Query, Recharts, Tailwind, shadcn/ui) is validated and in production.

**Bottom line: no new libraries needed.** All required computation can be done with Python's built-in `statistics` module and SQL aggregations.

---

## Recommended Stack

### Core Technologies (No Changes for v1.8)

All v1.8 features are implemented using existing dependencies:

| Technology | Version in Use | Relevant Capability for v1.8 |
|------------|---------------|------------------------------|
| Python 3.13 stdlib `statistics` | Built-in | `statistics.mean()`, `statistics.stdev()` for cross-game averages — no new dep |
| SQLAlchemy 2.x async | >=2.0.0 | `func.avg()`, `func.count()`, `func.sum()` in existing query patterns |
| PostgreSQL 18 | (Docker, pinned) | `AVG`, `CASE WHEN`, `FILTER` aggregate clauses for normalized rating computation |
| FastAPI | >=0.115.x | New or extended endpoint on `/api/endgames/performance` |
| Recharts | ^2.15.4 (frontend) | Existing `EndgameGauge` SVG component already handles any float value 0–100 |

### Supporting Libraries (No Additions)

| Library | Purpose | Notes |
|---------|---------|-------|
| Python `statistics` (stdlib) | Average opponent rating, standard deviation for confidence metrics | Already available; do NOT add numpy/scipy — overkill for simple mean computations over hundreds of rows |
| SQLAlchemy `func.avg()` | Average normalized opponent rating in SQL | Push aggregation to DB, return a single scalar — avoids loading all rows to Python |
| Recharts (existing) | ELO-adjusted skill timeline chart (single line) | Same `LineChart` pattern used in conv/recov timeline; reuse `EndgameConvRecovChart.tsx` or clone it |
| `EndgameGauge.tsx` (existing) | Display adjusted_endgame_skill score | Already accepts any `value: number`, `maxValue`, and `zones`; no component changes needed |

---

## ELO Adjustment — Implementation Approach

### Formula (from PROJECT.md backlog item 999.5)

```
adjusted_endgame_skill = raw_endgame_skill × (avg_normalized_opponent_rating / REFERENCE_RATING)
```

Where:
- `raw_endgame_skill` = existing `0.7 × conversion_pct + 0.3 × recovery_pct`
- `avg_normalized_opponent_rating` = average chess.com-equivalent opponent rating across filtered endgame conversion/recovery games
- `REFERENCE_RATING = 1500` (chess.com blitz baseline, fixed)

### Cross-Platform Rating Normalization

The backlog item specifies a tapered offset formula to convert lichess ratings to chess.com-equivalent:

```python
# Lichess → chess.com blitz equivalent
# offset tapers from ~350 at lichess 1400, reaching 0 at lichess ~2570
offset = max(0, 350 - (lichess_rating - 1400) * 0.3)
chesscom_equivalent = lichess_rating - offset
```

**Empirical verification:** ChessGoals.com cross-platform data (2,489 active players with RD < 150) supports the tapering-offset pattern:
- At lichess 1030 → chess.com ~500 (offset ≈ 530, but users this low are outside useful range)
- At lichess 1420 → chess.com ~1000 (offset ≈ 420)
- At lichess 1780 → chess.com ~1500 (offset ≈ 280)
- At lichess 2100 → chess.com ~2000 (offset ≈ 100)

The formula specified in the backlog item (`offset = max(0, 350 - (lichess_rating - 1400) × 0.3)`) is a reasonable approximation that tapers as expected. It is intentionally simple — the purpose is directional normalization, not a precise FIDE-style calculation.

**Why not a linear formula:** The regression formula `C = 1.138 × L - 665` (for blitz) requires a float multiplier and has higher error at the tails. The tapered-offset approach is more interpretable and already agreed upon in the backlog design.

**Confidence: MEDIUM** — empirical cross-platform data supports the direction and approximate magnitude, but the exact tapering constants should be validated against real FlawChess user data once the feature is live.

### Where to Compute Normalization

**In Python service layer, not SQL.** Reason: the normalization formula involves conditional logic (`max(0, ...)`) and the `platform` column is already available per-game. Compute `normalized_opponent_rating` per game row in Python before averaging. This keeps SQL simple and the formula easy to iterate on.

```python
def normalize_opponent_rating(rating: int, platform: str) -> float:
    """Convert opponent rating to chess.com-equivalent (blitz baseline)."""
    if platform == "lichess":
        offset = max(0, 350 - (rating - 1400) * 0.3)
        return rating - offset
    return float(rating)  # chess.com already on target scale
```

### What Data Is Already Available

The `games` table already stores:
- `white_rating`, `black_rating` — raw opponent rating in platform's native scale
- `platform` — "chess.com" or "lichess"
- `user_color` — needed to derive which rating is the opponent's

No new columns needed. The endgame entry rows already fetched by `query_endgame_entry_rows()` need to be joined with rating data, or a new variant query returns ratings alongside the existing columns.

---

## Opening Risk/Volatility — Implementation Approach

### Metric Definition (to be finalized in planning)

The most practical opening risk metric given available data is:

```
decisiveness = (wins + losses) / total_games  # fraction of decisive games, not draws
```

This is the user-data equivalent of opening sharpness: a 1. e4 Sicilian line with 80% decisive results is "sharp/risky" vs. a London System at 50% decisive that is "drawish/solid."

**Rationale for this approach over engine-based sharpness:**
- No local engine installed; per-position eval available for lichess analyzed games only (not all games)
- User-specific data: measures this player's actual decisive-game rate, not the theoretical sharpness
- Computable entirely from existing WDL data already computed for openings
- Matches how humans intuitively think about "is this opening risky for me?"

**Derived metrics** (all computable from existing WDL counts without new columns):
- `win_rate` = wins / total (already computed)
- `decisiveness` = (wins + losses) / total (new, but trivial addition to existing aggregation)
- `volatility` = how much win_rate varies game-to-game (needs rolling std dev — more complex)

**Recommendation:** Start with `decisiveness` (one new computed column in the response, no schema change). Defer volatility/std-dev metrics until decisiveness is validated as useful.

### No New Libraries for Statistical Aggregation

Python's `statistics.stdev()` handles per-opening win-rate standard deviation if needed. SQL `STDDEV_POP` / `STDDEV_SAMP` handles it at the database level. Both are available with zero new dependencies.

---

## New Schema Changes

### No New Columns Required for ELO-Adjusted Skill

All data needed is already present:
- `games.white_rating`, `games.black_rating` — opponent rating
- `games.platform` — needed for normalization formula
- `games.user_color` — needed to identify which rating is the opponent's
- Endgame entry rows (from `query_endgame_entry_rows`) already include `game_id` for joining back to `games`

**Optional: add `avg_normalized_opponent_rating` and `game_count` to `EndgamePerformanceResponse`** — surface this to the frontend for display alongside the adjusted score.

### New Schema Fields on Existing Pydantic Response

```python
# EndgamePerformanceResponse additions:
avg_normalized_opponent_rating: float | None  # None if no games with ratings
adjusted_endgame_skill: float                 # ELO-adjusted composite, 0-100 scale
```

The `endgame_skill` field stays as-is (raw, unadjusted) for continuity; `adjusted_endgame_skill` is the new value displayed in the gauge.

---

## Query Strategy

### Fetching Rating Data Alongside Endgame Entry Rows

**Option A (recommended): extend `query_endgame_entry_rows` to also return ratings**

Add `Game.white_rating`, `Game.black_rating`, `Game.platform`, and `Game.user_color` to the SELECT in the existing query. These are already on the joined `Game` row — no additional join needed. The service layer then:

1. Computes `normalized_opponent_rating` per row in Python
2. Averages over the conversion/recovery game subset
3. Applies the adjustment formula

**Option B: separate query for average normalized rating**

Push the average to SQL using `func.avg()` with a `CASE WHEN platform = 'lichess'` expression. Keeps the service layer simpler but embeds the normalization formula in SQL, making it harder to iterate on.

**Recommendation: Option A.** The normalization logic is already in the service layer and the `query_endgame_entry_rows` result set is already fetched (hundreds of rows maximum per user). No performance concern.

---

## Frontend: New Components Needed

### ELO-Adjusted Skill Gauge

**No new component.** The existing `EndgameGauge.tsx` already accepts:
- `value: number` — display `adjusted_endgame_skill`
- `maxValue?: number` — default 100 works
- `label: string` — "Endgame Skill (Adj.)" or similar
- `zones?: GaugeZone[]` — reuse `DEFAULT_GAUGE_ZONES` from `theme.ts`

The gauge already renders correctly for any float in [0, 100]. Swap the displayed value from `endgame_skill` to `adjusted_endgame_skill` when the API returns it.

### Endgame Skill Timeline Chart

**Reuse existing pattern.** The `EndgameConvRecovChart.tsx` renders a rolling-window LineChart from `ConvRecovTimelineResponse`. A new `EndgameSkillTimelineChart.tsx` component follows the same pattern but takes a simpler `{ date, value, game_count, window_size }[]` series.

No new charting library. Recharts `LineChart` + `Line` + `XAxis` + `YAxis` + `Tooltip` — all already imported elsewhere in the frontend.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `numpy` / `scipy` | Heavy ML-oriented dependencies for computing a simple mean across <1000 rows per user — massive overkill | Python `statistics.mean()` (stdlib) or `sum(vals) / len(vals)` |
| `statsmodels` | Even heavier; designed for regression/hypothesis testing, not plain average computation | Same — stdlib `statistics` |
| External rating API (chess-elo-converter, etc.) | External dep for what is a 2-line formula; network call adds latency and failure mode | Inline normalization function per formula in PROJECT.md backlog item |
| Server-side Elo performance rating | Defined differently than what's needed (requires game-by-game opponent rating AND result pairing, and has well-known baseline failure for material-up situations) | Tapering-offset normalization as specified |
| New Recharts chart type | All needed chart types (LineChart, RadialBarChart) already in use | Reuse existing EndgameConvRecovChart pattern |
| Adding `game_phase` or `endgame_class` derived columns to `games` table | Already encoded at position level in `game_positions`; duplicating to `games` creates redundancy | Query via existing endgame_repository patterns |
| SQL `STDDEV_POP` for rolling std dev | Rolling std dev over game history is complex in pure SQL; easier as Python post-processing | Python list comprehension over chronological rows, same pattern as `_compute_rolling_series` |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Tapered-offset normalization formula | Linear regression `C = 1.138 × L - 665` | Extrapolates poorly at low/high ratings; less interpretable; harder to explain to users |
| Python-layer normalization per row | SQL `CASE WHEN platform = 'lichess' THEN ...` computed column | Business logic belongs in Python, not SQL; formula is likely to be iterated on |
| Extend `EndgamePerformanceResponse` with `adjusted_endgame_skill` | New `/api/endgames/adjusted-skill` endpoint | One additional field on existing endpoint is simpler; same data lifecycle |
| `decisiveness = (wins + losses) / total` for opening risk | Engine-based WDL sharpness metric | Requires per-position engine eval (not available for chess.com; sparse for lichess); user's actual decisive-game rate is more actionable |
| Reuse `EndgameGauge.tsx` for adjusted score | New gauge component | Existing component is parameterized; value/label/zones all configurable without code duplication |

---

## Version Compatibility

| Package | Constraint | Notes |
|---------|------------|-------|
| Python `statistics` | 3.4+ (built-in) | `mean()`, `stdev()`, `pstdev()` all stable; no version concerns |
| SQLAlchemy | >=2.0.0 | `func.avg()` unchanged since 1.x; no compatibility issues |
| Recharts | ^2.15.4 | `LineChart`, `Line` components stable; no new API surface needed |
| PostgreSQL | 18 | `AVG()`, `CASE WHEN`, `FILTER` are standard SQL; all available since PG 9.4+ |

---

## Sources

- [ChessGoals.com Rating Comparison](https://chessgoals.com/rating-comparison/) — empirical cross-platform rating data (2,489 players, RD < 150), tapering offset pattern confirmed — MEDIUM confidence (community data, recent July 2025 update)
- [NoseKnowsAll Universal Rating Converter 2024](https://lichess.org/@/NoseKnowsAll/blog/introducing-a-universal-rating-converter-for-2024/X2QAH27t) — classical/rapid only; blitz excluded from universal converter — HIGH confidence (lichess official blog)
- [lichess forum: rating conversion formulae](https://lichess.org/forum/general-chess-discussion/rating-conversion-formulae-lichessorg--chesscom) — empirical linear regression formulas per time control — MEDIUM confidence (community, methodology unclear)
- [Python `statistics` module docs](https://docs.python.org/3/library/statistics.html) — stdlib `mean()`, `stdev()` available in Python 3.4+ — HIGH confidence (official)
- [shadcn/ui Radial Charts](https://ui.shadcn.com/charts/radial) — Recharts `RadialBarChart` gauge pattern via shadcn — HIGH confidence (official)
- [jk_182: Quantifying Volatility of Chess Games](https://lichess.org/@/jk_182/blog/quantifying-volatility-of-chess-games/H6MWvX98) — volatility metrics based on WDL and eval swings — MEDIUM confidence (community research)
- PROJECT.md backlog item 999.5 — normalization formula and adjustment design already decided — HIGH confidence (authoritative project decision)

---

*Stack research for: FlawChess v1.8 — advanced analytics (ELO-adjusted endgame skill, opening risk)*
*Researched: 2026-04-04*

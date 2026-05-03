# Phase 80: Opening stats — middlegame-entry eval and clock-diff columns - Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 9 (2 NEW, 7 MODIFIED)
**Analogs found:** 9 / 9 (all exact role + data-flow matches; downstream consumer phase, no greenfield surfaces)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/eval_confidence.py` (NEW) | service (statistical helper) | transform (pure fn) | `app/services/score_confidence.py` | exact |
| `tests/services/test_eval_confidence.py` (NEW) | test | transform | `tests/services/test_score_confidence.py` | exact |
| `app/repositories/stats_repository.py` (MOD) | repository | CRUD (read aggregation) | `app/repositories/stats_repository.py::query_position_wdl_batch` + `app/repositories/endgame_repository.py::query_clock_stats_rows` | exact (in-file extension + cross-file shape mirror) |
| `app/services/stats_service.py` (MOD) | service | request-response | `app/services/stats_service.py::get_most_played_openings` (current 240-373) | exact (in-file extension) |
| `app/schemas/stats.py` (MOD) | schema | model | `app/schemas/stats.py::OpeningWDL` (current 41-57) | exact (in-file extension) |
| `frontend/src/components/charts/MiniBulletChart.tsx` (MOD) | component | transform (presentational) | self (additive props) | exact |
| `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` (MOD) | component | request-response | self + `frontend/src/components/charts/EndgameClockPressureSection.tsx` (clock-diff cell + mobile cards) | exact (in-file extension + cross-file cell shape) |
| `frontend/src/types/stats.ts` (MOD) | types | model | self::`OpeningWDL` | exact |
| `frontend/src/pages/Openings.tsx` (MOD) | page | request-response | self::lines 1276-1290 (board container) | exact (single conditional class) |

## Pattern Assignments

### `app/services/eval_confidence.py` (NEW — statistical helper service)

**Analog:** `app/services/score_confidence.py` (exact mirror — sibling file, same module shape, different statistical procedure)

**Module docstring + imports pattern** (`score_confidence.py:1-33`):
```python
"""Wald p-value + N-gate confidence helper for chess score (W + 0.5*D)/N.

Shared between app.services.opening_insights_service.compute_insights and
app.services.openings_service.get_next_moves. Single source of truth for the
formula (Phase 75 D-07 anti-pattern lock; Phase 76 D-06 module split).

Bucketing rule:
  - n < 10                        -> "low"   (matches the unreliable-stats opacity dim)
  - n >= 10 and p_value < 0.05    -> "high"
  - n >= 10 and p_value < 0.10    -> "medium"
  - n >= 10 and p_value >= 0.10   -> "low"
...
"""

import math
from typing import Literal

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P as CONFIDENCE_HIGH_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P as CONFIDENCE_MEDIUM_MAX_P,
    OPENING_INSIGHTS_CONFIDENCE_MIN_N as CONFIDENCE_MIN_N,
    OPENING_INSIGHTS_SCORE_PIVOT as SCORE_PIVOT,
)
```
**Apply:** Same docstring shape (purpose, callers, bucketing rule). Same imports — keep `OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P / _MEDIUM_MAX_P / _MIN_N` aliases (drop `SCORE_PIVOT`; t-test pivot is fixed at 0.0). Add `import statistics` only if needed.

**Function signature + return-tuple pattern** (`score_confidence.py:36-39`):
```python
def compute_confidence_bucket(
    w: int, d: int, losses: int, n: int
) -> tuple[Literal["low", "medium", "high"], float, float]:
```
**Apply:** Mirror as `compute_eval_confidence_bucket(eval_sum: float, eval_sumsq: float, n: int) -> tuple[Literal["low", "medium", "high"], float, float, float]` (returning `(bucket, p_value, mean, ci_half_width)` per RESEARCH.md §Statistical Library Decision).

**N-gate + degenerate-SE handling pattern** (`score_confidence.py:78-110`):
```python
# MD-02 guard: callers today only pass rows with n >= 1, but openings_service.get_next_moves
# has an inconsistent `if gc > 0` guard on the score expression while passing gc here
# unconditionally. Defend against future contract drift...
if n <= 0:
    return "low", 0.5, 0.0
score = (w + 0.5 * d) / n
variance = (w + 0.25 * d) / n - score * score
variance = max(variance, 0.0)
se = math.sqrt(variance / n)

if se == 0.0:
    p_value = 0.5 if score == SCORE_PIVOT else 0.0
else:
    z = (score - SCORE_PIVOT) / se
    p_value = 0.5 * math.erfc(abs(z) / math.sqrt(2.0))

if n < CONFIDENCE_MIN_N:
    confidence: Literal["low", "medium", "high"] = "low"
elif p_value < CONFIDENCE_HIGH_MAX_P:
    confidence = "high"
elif p_value < CONFIDENCE_MEDIUM_MAX_P:
    confidence = "medium"
else:
    confidence = "low"
return confidence, p_value, se
```
**Apply:** Same skeleton. Replace the score/variance closed form with the t-test (Bessel-corrected) form: `mean = eval_sum / n`; `variance = max(0.0, (eval_sumsq - n * mean * mean) / (n - 1))` for `n >= 2`; `se = math.sqrt(variance / n)`; `ci_half_width = OPENING_INSIGHTS_CI_Z_95 * se` (already `1.96` in `opening_insights_constants.py`). Use **two-sided p**: `p_value = math.erfc(abs(z) / math.sqrt(2.0))` (no `0.5 *` factor; per RESEARCH §A1 — eval at MG entry is symmetric, both directions meaningful). Edge cases per RESEARCH lines 129-133: `n == 0 → ("low", 1.0, 0.0, 0.0)`; `n == 1 → ("low", 1.0, mean, 0.0)`; `se == 0` ⇒ `("high"|"low", 0.0|1.0, mean, 0.0)`.

---

### `tests/services/test_eval_confidence.py` (NEW — unit tests)

**Analog:** `tests/services/test_score_confidence.py` (exact mirror — same module-level docstring + section pattern)

**Section header + N-gate test pattern** (`test_score_confidence.py:26-53`):
```python
# --- N < 10 gate ---------------------------------------------------------


def test_n_below_gate_returns_low_even_with_strong_evidence() -> None:
    # n=9 all wins: p_value would be 0.0 (SE=0) but n<10 forces "low".
    confidence, p_value, _se = compute_confidence_bucket(w=9, d=0, losses=0, n=9)
    assert confidence == "low"
    assert p_value == 0.0


def test_n_zero_returns_low_half() -> None:
    """MD-02 guard: n<=0 returns ("low", 0.5, 0.0) without raising..."""
    confidence, p_value, se = compute_confidence_bucket(w=0, d=0, losses=0, n=0)
    assert confidence == "low"
    assert p_value == 0.5
    assert se == 0.0
```
**Apply:** Same `# --- Section header ---` separators (N-gate, p-value buckets, SE-zero edges, returned-tuple shape). Cover the test rows mandated in RESEARCH §Wave 0 Gaps:
- `test_low_when_n_below_min` (n=9 with strong mean → "low")
- `test_high_when_p_below_005` (n=400 with mean=+50 cp, sd=200 cp → p<0.05 → "high")
- `test_medium_when_p_in_005_010` (carefully tuned n + sumsq landing in [0.05, 0.10))
- `test_zero_variance_edges` (all-same-eval, mean≠0 → "high"; mean=0 → "low")
- `test_n_one_returns_low` (n=1 — variance undefined, gated to "low")
- `test_ci_half_width_matches_196_se` (returned `ci_half_width == 1.96 * se`)

**Use `pytest.approx(..., abs=1e-9)`** for float equality, mirroring `test_score_confidence.py:78`. Use plain `int` / `float` literals for `eval_sum` / `eval_sumsq` so the test math is hand-verifiable.

---

### `app/repositories/stats_repository.py` (MOD — add `query_opening_mg_metrics_batch`)

**Primary in-file analog:** `query_position_wdl_batch` (lines 338-415 — same module, same call shape, same hash-IN + apply_game_filters + DISTINCT subquery skeleton).
**Cross-file analog (clock-diff aggregation):** `app/repositories/endgame_repository.py::query_clock_stats_rows` (lines 626-741) — `array_agg(... ORDER BY ply)` + Python-side `_extract_entry_clocks` walk.

**Function signature pattern** (`stats_repository.py:338-350`):
```python
async def query_position_wdl_batch(
    session: AsyncSession,
    user_id: int,
    hashes: list[int],
    color: Literal["white", "black"] | None = None,
    time_control: Sequence[str] | None = None,
    platform: Sequence[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    recency_cutoff: datetime.datetime | None = None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> dict[int, PositionWDL]:
```
**Apply:** Identical signature for the new `query_opening_mg_metrics_batch`; only the return type changes (`dict[int, OpeningMgMetrics]` where `OpeningMgMetrics` is a tiny `__slots__` class living next to `PositionWDL`).

**Empty-input guard pattern** (`stats_repository.py:357-358`):
```python
if not hashes:
    return {}
```
**Apply:** Verbatim.

**DISTINCT-on-(full_hash, game_id) dedup + apply_game_filters pattern** (`stats_repository.py:360-387`):
```python
dedup = (
    select(
        GamePosition.full_hash,
        Game.id.label("game_id"),
        Game.result,
        Game.user_color,
    )
    .join(Game, GamePosition.game_id == Game.id)
    .where(
        GamePosition.user_id == user_id,
        GamePosition.full_hash.in_(hashes),
    )
    .distinct(GamePosition.full_hash, Game.id)
)
if color is not None:
    dedup = dedup.where(Game.user_color == color)
dedup = apply_game_filters(
    dedup,
    time_control,
    platform,
    rated,
    opponent_type,
    recency_cutoff,
    opponent_gap_min=opponent_gap_min,
    opponent_gap_max=opponent_gap_max,
)
dedup = dedup.subquery()
```
**Apply:** Verbatim. Add `Game.user_color`, `Game.base_time_seconds` to the SELECT list so the downstream JOIN can sign the eval per game and divide clock diffs by per-game base.

**MG-entry per-game subquery pattern** (mirrors `endgame_repository.py::query_clock_stats_rows:693-706`):
```python
# Source: endgame_repository.py:693-706 — the canonical "per-game array_agg with HAVING" shape
per_game_subq = (
    select(
        GamePosition.game_id.label("game_id"),
        ply_array_agg.label("ply_array"),
        clock_array_agg.label("clock_array"),
    )
    .where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    .group_by(GamePosition.game_id)
    .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
    .subquery("clock_per_game")
)
```
**Apply for MG entry:** Replace `endgame_class.isnot(None)` with `phase == 1`; drop the `HAVING count >= ENDGAME_PLY_THRESHOLD` (MG-entry just needs the existence of a phase=1 row). Aggregate `array_agg(ply ORDER BY ply)`, `array_agg(clock_seconds ORDER BY ply)`, plus `min(eval_cp) FILTER (WHERE eval_cp IS NOT NULL)` … or simpler: aggregate only `min(ply) FILTER (WHERE phase=1)` and JOIN the entry row back.

**Performance-critical comment to copy verbatim** (`endgame_repository.py:687-692`):
```python
# One row per game: aggregate all endgame plies (across all classes) and apply the
# whole-game ENDGAME_PLY_THRESHOLD via HAVING in the same pass. Equivalent to the
# game_id IN _any_endgame_ply_subquery filter used elsewhere, but folded into a
# single scan — the IN form caused the planner to misestimate cardinality (every
# row estimate at 1 vs ~110k actual) and pick a Nested Loop / Join Filter cross
# comparison that hung indefinitely on users with many endgame games.
```
**Apply:** Cite this comment in any new code that picks GROUP BY + JOIN over an `IN (subquery)` — the planner-hang pitfall is real on heavy users (RESEARCH Pitfall 3). Run EXPLAIN ANALYZE on Adrian's user pre-merge.

**Array_agg type-coercion pattern** (`endgame_repository.py:677-685`):
```python
ply_array_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.ply, GamePosition.ply.asc())),
    ARRAY(SmallIntegerType),
)
clock_array_agg = type_coerce(
    func.array_agg(aggregate_order_by(GamePosition.clock_seconds, GamePosition.ply.asc())),
    ARRAY(FloatType()),
)
```
**Apply:** Use **only if** the planner picks the array_agg+Python-walk path. RESEARCH §SQL Aggregation Pattern recommends two LEFT JOINs (entry_ply, entry_ply+1) instead — smaller wire payload, simpler. Decision deferred to planner per CONTEXT.md "Claude's Discretion — SQL aggregation pattern."

**Result-row → dict pattern** (`stats_repository.py:411-415`):
```python
result = await session.execute(stmt)
return {
    row[0]: PositionWDL(total=row[1], wins=row[2], draws=row[3], losses=row[4])
    for row in result.fetchall()
}
```
**Apply:** Same shape, return `dict[int, OpeningMgMetrics]`. Keep `__slots__` micro-optimization since this is in the per-row hot path of every Stats subtab fetch.

**Color-flip in SQL pattern** (RESEARCH §Code Examples lines 519-535, semantically `endgame_service.py:194-202`):
```python
# Sign the eval at SQL level (consistent with _classify_endgame_bucket convention):
sign_expr = case((Game.user_color == "white", 1), else_=-1)
user_eval_expr = sign_expr * GamePosition.eval_cp
```
**Apply:** Either sign in SQL (simpler accumulation) or sign in Python after fetching white-perspective `eval_cp`. CLAUDE.md: "do NOT invent a new sign convention." Use `1 if user_color == 'white' else -1`.

---

### `app/services/stats_service.py` (MOD — wire new fields into `get_most_played_openings`)

**In-file analog:** `get_most_played_openings` itself (lines 240-373) — extending the existing batch-call pattern.

**Existing batch-call + filter-threading pattern** (`stats_service.py:303-328`):
```python
# Row tuple shape: (eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)
white_position_wdl = await query_position_wdl_batch(
    session,
    user_id,
    [row[5] for row in white_rows if row[5] is not None],
    color="white",
    time_control=filter_params["time_control"],
    platform=filter_params["platform"],
    rated=filter_params["rated"],
    opponent_type=filter_params["opponent_type"],
    recency_cutoff=filter_params["recency_cutoff"],
    opponent_gap_min=filter_params["opponent_gap_min"],
    opponent_gap_max=filter_params["opponent_gap_max"],
)
```
**Apply:** Add `white_mg_metrics = await query_opening_mg_metrics_batch(...)` and `black_mg_metrics = ...` immediately after the WDL batch calls. Pass the **identical** `filter_params` (RESEARCH Pitfall 4: filter mismatch between WDL and MG metrics is a "debugging nightmare"). **Sequential awaits** in the same session — never `asyncio.gather` (CLAUDE.md Critical Constraint).

**Row-to-schema finalize pattern** (`stats_service.py:330-364`):
```python
def rows_to_openings(
    rows: list[Row[Any]],
    position_wdl: dict,
) -> list[OpeningWDL]:
    openings = []
    for eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses in rows:
        pos = position_wdl.get(full_hash) if full_hash else None
        if pos:
            total, wins, draws, losses = pos.total, pos.wins, pos.draws, pos.losses
        if total > 0:
            win_pct = round(wins / total * 100, 1)
            ...
        openings.append(
            OpeningWDL(
                opening_eco=eco,
                ...
                total=total,
                win_pct=win_pct,
                ...
            )
        )
    openings.sort(key=lambda o: o.total, reverse=True)
    return openings
```
**Apply:** Extend the closure signature to `rows_to_openings(rows, position_wdl, mg_metrics)`. After the WDL block, look up `mg = mg_metrics.get(full_hash)`; if present, call `compute_eval_confidence_bucket(mg.eval_sum, mg.eval_sumsq, mg.eval_n)` and compute `avg_eval_pawns = (mg.eval_sum / mg.eval_n) / 100.0` (sign already applied in SQL/python per `_classify_endgame_bucket` convention). Compute `eval_ci_low_pawns / eval_ci_high_pawns = avg_eval_pawns ∓ ci_half_width / 100.0`. For clock-diff: `avg_clock_diff_pct = (sum(diff_seconds) / sum(base_time_seconds)) * 100`, `avg_clock_diff_seconds = sum(diff_seconds) / clock_diff_n` (RESEARCH §Architecture Diagram lines 170-174). Default to `None` when `eval_n == 0` / `clock_diff_n == 0`.

**Sentry capture pattern (CLAUDE.md Error Handling rule):** Wrap any new non-trivial except blocks in `services/` with `sentry_sdk.capture_exception()`. The new helpers don't introduce new error sites (pure compute), but **do not** add bare `except Exception` swallows.

---

### `app/schemas/stats.py` (MOD — extend `OpeningWDL`)

**In-file analog:** `OpeningWDL` itself (lines 41-57).

**Existing schema pattern** (`schemas/stats.py:41-57`):
```python
class OpeningWDL(BaseModel):
    """WDL stats for a single opening, with ECO code, PGN, FEN, and display label."""

    opening_eco: str
    opening_name: str  # canonical name, used for FEN/bookmark lookups
    display_name: str  # canonical name with "vs. " prefix when off-color (PRE-01)
    label: str  # "Opening Name (ECO)" — precomputed for UI
    pgn: str
    fen: str
    full_hash: str
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float
```

**Apply (additive, all optional with defaults — RESEARCH Code Examples 588-605):**
```python
# Phase 80 additions — all optional so existing tests/clients keep working
avg_eval_pawns: float | None = None  # signed, user-perspective; None when eval_n == 0
eval_ci_low_pawns: float | None = None  # 95% CI lower bound; None when eval_n < 2
eval_ci_high_pawns: float | None = None
eval_n: int = 0  # games used in the mean (mate-excluded, NULL-excluded)
eval_p_value: float | None = None  # two-sided p-value vs zero
eval_confidence: Literal["low", "medium", "high"] = "low"

avg_clock_diff_pct: float | None = None  # signed % of base time
avg_clock_diff_seconds: float | None = None  # signed seconds
clock_diff_n: int = 0
```
**Type-safety note (CLAUDE.md):** Use `Literal["low", "medium", "high"]` not bare `str` (project rule). Add `from typing import Literal` to the imports.

---

### `frontend/src/components/charts/MiniBulletChart.tsx` (MOD — add CI whisker)

**Analog:** Self (extension only). The component is small, fully read in this pass.

**Existing prop interface pattern** (`MiniBulletChart.tsx:33-48`):
```typescript
interface MiniBulletChartProps {
  /** Signed difference to visualize (e.g. row_score - opponent_score). */
  value: number;
  /** Lower bound of the neutral zone. Default -0.10. */
  neutralMin?: number;
  /** Upper bound of the neutral zone. Default 0. */
  neutralMax?: number;
  /** Bar domain half-width (values beyond ±domain are clamped). Default 0.40. */
  domain?: number;
  /** Accessible label. Falls back to the signed numeric value. */
  ariaLabel?: string;
  /** Height class for the zone background, default h-5 (matches MiniWDLBar). */
  heightClass?: string;
  /** Height class for the foreground value bar, default h-2 (thinner than zones). */
  valueHeightClass?: string;
}
```
**Apply:** Add two optional props with the same JSDoc style:
```typescript
/** Optional 95% CI lower bound (in domain units). Renders a thin whisker over the value bar. */
ciLow?: number;
/** Optional 95% CI upper bound (in domain units). Renders a thin whisker over the value bar. */
ciHigh?: number;
```
**Behavior preserve:** When either is undefined, render unchanged (D-02 lock — must not affect Material Breakdown table call sites).

**Existing `toPct` + clamping pattern** (`MiniBulletChart.tsx:64-71`):
```typescript
const clamped = Math.max(-domain, Math.min(domain, value));
const toPct = (v: number): number => ((v + domain) / (2 * domain)) * 100;
const zeroPct = toPct(0);
const neutralMinPct = toPct(Math.max(-domain, neutralMin));
const neutralMaxPct = toPct(Math.min(domain, neutralMax));
const markerPct = toPct(clamped);
```
**Apply:** Use the same `toPct` for whisker positions. Detect open-ended whiskers via `lowOpen = ciLow < -domain`, `highOpen = ciHigh > domain` (RESEARCH §Code Examples whisker overlay).

**Existing absolute-positioned overlay pattern** (`MiniBulletChart.tsx:127-152`):
```typescript
{/* Zero reference line */}
<div
  className="absolute top-0 bottom-0 w-px bg-foreground/50"
  style={{ left: `${zeroPct}%` }}
/>
...
{/* Value fill bar — thinner than zones, vertically centered */}
<div
  className={`absolute top-1/2 -translate-y-1/2 ${valueHeightClass}`}
  style={{
    left: `${barLeft}%`,
    width: `${barWidth}%`,
    backgroundColor: fillColor,
  }}
/>
```
**Apply:** Whisker uses the same `absolute top-1/2 -translate-y-1/2` skeleton. Use `bg-foreground/70` for the line + caps (matches `bg-foreground/50` zero line, slightly stronger). Render after the value fill bar so caps overlay it. RESEARCH Pitfall 6: when clipped, suppress the cap on the clipped side (open-ended whisker affordance).

**Theme constants:** No new theme constants needed for the whisker (uses existing `foreground/70`). For consumer call sites (`MostPlayedOpeningsTable`), define new constants in a new module `frontend/src/lib/openingStatsZones.ts` — names per RESEARCH §Recommended Constants:
```typescript
export const EVAL_NEUTRAL_MIN_PAWNS = -0.30;  // half user-mean IQR
export const EVAL_NEUTRAL_MAX_PAWNS = +0.30;
export const EVAL_BULLET_DOMAIN_PAWNS = 1.00;  // ±1.00 pawns; caps just past p95
```
CLAUDE.md frontend rule: "all theme-relevant color constants … must be defined in `theme.ts`." These are zone *bounds*, not colors, so a sibling lib file is fine — but cite the source comment per CLAUDE.md "no magic numbers."

**`data-testid` rule (CLAUDE.md Browser Automation):** Add `data-testid="mini-bullet-whisker"` on the whisker line div. Existing `data-testid="mini-bullet-chart"` on root stays.

---

### `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` (MOD — three new columns + mobile second line)

**Primary in-file analog:** `OpeningRow` itself (lines 38-101).
**Cross-file analog (clock-diff cell):** `frontend/src/components/charts/EndgameClockPressureSection.tsx` lines 62-75 (formatters), 260-266 (desktop cell), 336-343 (mobile cell).
**Cross-file analog (confidence pill):** `frontend/src/components/insights/OpeningFindingCard.tsx` lines 106-127.

**Existing 3-col grid pattern** (`MostPlayedOpeningsTable.tsx:50-53`):
```tsx
<div
  className={`grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)] gap-2 items-center rounded px-2 py-1.5 hover:bg-white/5 transition-colors ${isEvenRow ? 'bg-white/[0.02]' : ''}`}
  data-testid={`${testIdPrefix}-row-${rowKey}`}
>
```
**Apply (desktop):** Extend the `sm:grid-cols-[...]` template to add three columns at the end: `minmax(120px,180px)_auto_minmax(80px,120px)` for [bullet | pill | clock-diff]. Keep mobile (`grid-cols-[1fr_auto_minmax(80px,140px)]`) unchanged on the **first row**; the new metrics become a **second line** below per D-06.

**Mobile second-line stack pattern** (`EndgameClockPressureSection.tsx:309-352` mobile cards — adapt to second-line stack):
```tsx
{/* Mobile: stacked cards */}
<div className="lg:hidden space-y-3" data-testid="clock-pressure-cards">
  {computedRows.map(({ row, diffColor }) => (
    <div className="rounded border border-border p-3 space-y-2" data-testid={`...`}>
      <div className="flex items-baseline justify-between">
        <div className="text-sm font-medium">{row.label}</div>
        <div className="text-xs tabular-nums text-muted-foreground">{row.total_endgame_games.toLocaleString()} games</div>
      </div>
      ...
    </div>
  ))}
</div>
```
**Apply:** D-06 requires "second line below the existing 3-col" — *not* a separate card. Inside the existing `OpeningRow` div, after the closing of the first `grid`, append a `sm:hidden` (mobile-only) second line: `<div className="sm:hidden mt-2 grid grid-cols-3 gap-2 items-center">` with bullet, pill, clock-diff in three cells. Keep the desktop reading these as added grid columns on the same row.

**Confidence pill rendering pattern** (`OpeningFindingCard.tsx:106-127`):
```tsx
const confidenceLine = (
  <p
    className="text-sm text-muted-foreground flex items-center gap-1"
    data-testid={`opening-finding-card-${idx}-confidence`}
  >
    Confidence:{' '}
    <Tooltip
      content={
        <ConfidenceTooltipContent
          level={finding.confidence}
          pValue={finding.p_value}
          score={finding.score}
          gameCount={finding.n_games}
        />
      }
    >
      <span className="font-medium" data-testid={`opening-finding-card-${idx}-confidence-info`}>
        {finding.confidence}
      </span>
    </Tooltip>
  </p>
);
```
**Apply:** No existing `ConfidencePill` component — pill is rendered inline via `<span className="font-medium">`. For the table cell, mirror the same shape: `<Tooltip content={<ConfidenceTooltipContent level={...} />}><span className="font-medium" data-testid="...">{o.eval_confidence}</span></Tooltip>`. RESEARCH §A3: planner can choose to **extract** a small `<ConfidencePill level={..} pValue={..} />` component to share between OpeningFindingCard and the new table cell (~30 min refactor; recommended over duplicating the inline JSX). Reuse `ConfidenceTooltipContent` from `frontend/src/components/insights/ConfidenceTooltipContent.tsx`.

**"Mute the value when confidence === 'low'" pattern** (`OpeningFindingCard.tsx:58-60`):
```tsx
const isUnreliable =
  finding.n_games < MIN_GAMES_FOR_RELIABLE_STATS || finding.confidence === 'low';
```
**Apply:** Same gate for the bullet chart cell — when `o.eval_confidence === "low"` or `o.eval_n < MIN_GAMES_FOR_RELIABLE_STATS`, dim the cell (e.g. `opacity: UNRELIABLE_OPACITY` from theme) per "muted gray" insights pattern. RESEARCH §Open Questions Q2: at `eval_n < 5`, render "—" instead of the chart (CI would span entire domain anyway).

**Clock-diff formatter import pattern** (`EndgameClockPressureSection.tsx:62-75`):
```tsx
function formatSignedSeconds(diff: number | null): string {
  if (diff === null) return '—';
  const rounded = Math.round(diff);
  if (rounded > 0) return `+${rounded}s`;
  return `${rounded}s`;
}

function formatSignedPct(userPct: number | null, oppPct: number | null): string {
  if (userPct === null || oppPct === null) return '—';
  const rounded = Math.round(userPct - oppPct);
  if (rounded > 0) return `+${rounded}%`;
  return `${rounded}%`;
}
```
**Apply:** RESEARCH §Don't Hand-Roll: extract `formatSignedSeconds` to a shared util (e.g. `frontend/src/lib/formatters.ts` or `frontend/src/lib/clockFormat.ts`) so the two clock-diff cells "read identically" (D-05). The pct formatter needs adapting since the new column gets a single signed pct value (not user vs opp); add `formatSignedPct1(pct: number | null): string` variant.

**Clock-diff cell pattern** (`EndgameClockPressureSection.tsx:260-266`):
```tsx
<td
  className="py-1.5 px-2 text-right text-sm tabular-nums"
  style={diffColor ? { color: diffColor } : undefined}
>
  {formatSignedPct(row.user_avg_pct, row.opp_avg_pct)}
  <span className="text-muted-foreground ml-1">({formatSignedSeconds(row.avg_clock_diff_seconds)})</span>
</td>
```
**Apply:** Same shape. Use a single signed pct (`+8.2%`) followed by absolute seconds in muted-foreground parentheses (`(+24s)`). Apply `ZONE_DANGER`/`ZONE_NEUTRAL`/`ZONE_SUCCESS` color via `style` prop following the existing `diffColor` ternary lines 180-187 of the same file.

**InfoPopover tooltip pattern** (CONTEXT.md "Claude's Discretion — Tooltip" + `EndgameClockPressureSection.tsx:154-166`):
```tsx
<InfoPopover ariaLabel="Clock pressure info" testId="clock-pressure-info" side="top">
  <p>Shows your clock situation when entering endgames, broken down by time control.</p>
  <p className="mt-1"><strong>Avg clock diff:</strong> difference between your average and your opponent's average remaining clock...</p>
</InfoPopover>
```
**Apply:** Add `<InfoPopover>` next to each new column header explaining: (1) "Avg eval at MG entry" — what positive/negative means, mate exclusion, why CI matters; (2) "Confidence" — t-test thresholds; (3) "Avg clock diff" — same wording as endgame popover.

**`data-testid` naming pattern** (CLAUDE.md Browser Automation):
- `${testIdPrefix}-bullet-${rowKey}` for the bullet chart cell
- `${testIdPrefix}-confidence-${rowKey}` for the pill
- `${testIdPrefix}-clock-diff-${rowKey}` for the clock cell

---

### `frontend/src/types/stats.ts` (MOD — mirror schema additions)

**In-file analog:** `OpeningWDL` interface (lines 28-44).

**Existing pattern** (`types/stats.ts:28-44`):
```typescript
export interface OpeningWDL {
  opening_eco: string;
  opening_name: string;
  /** Canonical name with "vs. " prefix when the opening is defined by the off-color (PRE-01). */
  display_name: string;
  label: string;
  pgn: string;
  fen: string;
  full_hash: string;
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}
```
**Apply:** Append the same nine optional fields as the Pydantic schema. Use `?:` (optional) syntax for fields that map to `T | None`:
```typescript
avg_eval_pawns?: number | null;
eval_ci_low_pawns?: number | null;
eval_ci_high_pawns?: number | null;
eval_n: number;
eval_p_value?: number | null;
eval_confidence: 'low' | 'medium' | 'high';
avg_clock_diff_pct?: number | null;
avg_clock_diff_seconds?: number | null;
clock_diff_n: number;
```
**Note:** `noUncheckedIndexedAccess` is on (CLAUDE.md frontend rule); `null`-aware typing is enforced. Use the discriminated union literal type (not bare `string`) for `eval_confidence` per CLAUDE.md.

---

### `frontend/src/pages/Openings.tsx` (MOD — hide ChessBoard on Stats subtab desktop)

**Analog:** Self (single conditional class change at lines 1276-1290).

**Existing flex-row layout pattern** (`Openings.tsx:1276-1290`):
```tsx
<div className="mt-4 flex flex-row items-start gap-6">
  <div className="flex flex-col gap-2 w-[400px] shrink-0">
    <ChessBoard
      position={chess.position}
      onPieceDrop={chess.makeMove}
      flipped={boardFlipped}
      lastMove={chess.lastMove}
      arrows={boardArrows}
    />
    <BoardControls ... />
    ...
    <MoveList ... />
  </div>
  <div className="flex-1 min-w-0">
    <TabsContent value="explorer">...</TabsContent>
    ...
  </div>
</div>
```

**`activeTab` derivation pattern** (`Openings.tsx:198-201`):
```tsx
const activeTab = location.pathname.includes('/games')
  ? 'games'
  : location.pathname.includes('/stats')
    ? 'stats'
    : ...;
```
**Apply:** `activeTab` is already in scope. Add a conditional `hidden` class to the **board container div** (line 1277) — *not* to `<ChessBoard>` itself (RESEARCH Pitfall 7: removing the JSX element resets chess.js state):
```tsx
<div className={`flex flex-col gap-2 w-[400px] shrink-0 ${activeTab === 'stats' ? 'hidden lg:hidden' : ''}`}>
```
Or alternatively `${activeTab === 'stats' ? 'lg:hidden' : ''}` — desktop only. Mobile already collapses the board area per CONTEXT D-03; verify by searching for the existing mobile hide and align with it.

**Anti-pattern (RESEARCH Pitfall 7):** Do NOT remove `<ChessBoard>` or reorder the JSX tree — instance preservation matters for chess.js state. Only toggle `hidden` on the container.

---

## Shared Patterns

### Authentication / Authorization

**Source:** existing `/api/stats/most-played-openings` route (FastAPI-Users JWT, `current_user.id` filter).
**Apply to:** No new routes added. Phase 80 piggybacks on the existing route — verify the new repository function takes `user_id: int` (not from request payload — RESEARCH §Security Domain V4 Access Control).

### Filter Threading (single source of truth)

**Source:** `app/repositories/query_utils.py::apply_game_filters` (CLAUDE.md: "Never duplicate filter logic in individual repositories.")

```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> Any:
```
**Apply to:** `query_opening_mg_metrics_batch` MUST thread filters through this helper using the **same `FilterParams` TypedDict** as the WDL batch call in `stats_service.py:292-300` (RESEARCH Pitfall 4 — filter mismatch between WDL and MG metrics is a "debugging nightmare"; surface check: assert `eval_n <= total` for every row).

### Sentry Capture

**Source:** CLAUDE.md "Always call `sentry_sdk.capture_exception()` in every non-trivial except block in `app/services/` and `app/routers/`."
**Apply to:** `eval_confidence.py` is pure compute (no exception handling needed). `stats_service.py` extension reuses the existing exception flow (no new try/except block introduced). If any new try/except is added, follow the variable-context rule:
```python
sentry_sdk.set_context("opening_mg_metrics", {"user_id": user_id, "n_hashes": len(hashes)})
sentry_sdk.capture_exception(exc)
```
Never embed `user_id` in the exception message (CLAUDE.md fragments Sentry grouping).

### Type Safety (`ty` compliance)

**Source:** CLAUDE.md "ty must pass with zero errors."
**Apply to:** All new functions get explicit return types. `eval_confidence.compute_eval_confidence_bucket` returns `tuple[Literal["low", "medium", "high"], float, float, float]`. `Sequence[str]` (not `list[str]`) for any param taking `list[Literal[...]]` values. Pydantic model at the boundary (`OpeningWDL`); TypedDict (`FilterParams`) for internal accumulators (already present at `stats_service.py:292`). New: a `MgMetricsAccumulator` TypedDict for the per-hash accumulator if used internally.

### Theme + No Magic Numbers

**Source:** CLAUDE.md "Theme constants in theme.ts" + "No magic numbers — extract thresholds, limits, and configuration values into named constants."
**Apply to:**
- `EVAL_NEUTRAL_MIN_PAWNS / EVAL_NEUTRAL_MAX_PAWNS / EVAL_BULLET_DOMAIN_PAWNS` in a new `frontend/src/lib/openingStatsZones.ts` (or `theme.ts` if planner prefers — they're zone *bounds*, not colors).
- WHISKER_OPACITY / cap-line color: reuse existing `bg-foreground/70` Tailwind class — no new constant needed.
- N-floor threshold: import `MIN_GAMES_FOR_RELIABLE_STATS` from existing insights theme/constants module (don't reinvent).

### `data-testid` Naming (CLAUDE.md Browser Automation)

**Source:** CLAUDE.md "Required on All New Frontend Code" — `data-testid` on every interactive element.
**Apply to:**
- `mini-bullet-whisker` (new whisker overlay)
- `${testIdPrefix}-bullet-${rowKey}`, `${testIdPrefix}-confidence-${rowKey}`, `${testIdPrefix}-clock-diff-${rowKey}` (cells)
- `opening-stats-eval-info` / `opening-stats-confidence-info` / `opening-stats-clock-diff-info` (column-header InfoPopovers)

### Sign Convention (single source of truth)

**Source:** `app/services/endgame_service.py:194` — `sign = 1 if user_color == "white" else -1; user_eval = sign * eval_cp`.
**Apply to:** Backend (`stats_repository.py` SQL or `stats_service.py` Python finalizer). RESEARCH Pitfall 1: sign at the backend, return `avg_eval_pawns` already signed. Verification test: white avg_eval == -black avg_eval for same opening + identical games (`tests/services/test_stats_service.py::test_color_flip_symmetry`).

### Confidence Threshold Constants (single source of truth)

**Source:** `app/services/opening_insights_constants.py` (lines 39-41, verified):
```python
OPENING_INSIGHTS_CONFIDENCE_MIN_N: int = 10
OPENING_INSIGHTS_CONFIDENCE_HIGH_MAX_P: float = 0.05
OPENING_INSIGHTS_CONFIDENCE_MEDIUM_MAX_P: float = 0.10
OPENING_INSIGHTS_CI_Z_95: float = 1.96
```
**Apply to:** `eval_confidence.py` imports these (CLAUDE.md "no magic numbers"; RESEARCH §Don't Hand-Roll). Note the comment at `opening_insights_constants.py:48-52` already anticipates this exact reuse: "the trinomial *Wald* p-value used by `score_confidence.compute_confidence_bucket` is a different statistical procedure and is not renamed" — implying additional consumers (eval_confidence) reuse the same `_HIGH_MAX_P` / `_MEDIUM_MAX_P` thresholds.

---

## No Analog Found

None — Phase 80 is a downstream consumer of Phase 79. Every new file has a precise existing analog in the codebase.

## Metadata

**Analog search scope:**
- `app/services/` (score_confidence, endgame_service, stats_service, opening_insights_constants)
- `app/repositories/` (stats_repository, endgame_repository, query_utils)
- `app/schemas/` (stats)
- `tests/services/` (test_score_confidence)
- `frontend/src/components/charts/` (MiniBulletChart, EndgameClockPressureSection)
- `frontend/src/components/stats/` (MostPlayedOpeningsTable)
- `frontend/src/components/insights/` (OpeningFindingCard, ConfidenceTooltipContent)
- `frontend/src/pages/` (Openings)
- `frontend/src/types/` (stats)

**Files scanned:** ~14 source files, all open at exact line ranges cited above.

**Pattern extraction date:** 2026-05-03

---

## PATTERN MAPPING COMPLETE

**Phase:** 80 - Opening stats: middlegame-entry eval and clock-diff columns
**Files classified:** 9 (2 NEW, 7 MODIFIED)
**Analogs found:** 9 / 9

### Coverage
- Files with exact analog: 9
- Files with role-match analog: 0
- Files with no analog: 0

### Key Patterns Identified
- **Statistical helper sibling pattern** — `compute_eval_confidence_bucket` mirrors `compute_confidence_bucket` shape (function signature, N-gate, SE-zero handling, returned-tuple convention) with t-test math swapped in for Wald score-binomial math; same threshold constants imported from `opening_insights_constants.py`.
- **Repository batch-aggregation pattern** — `query_opening_mg_metrics_batch` mirrors `query_position_wdl_batch` (DISTINCT-on-(full_hash, game_id) dedup + `apply_game_filters` threading + hash-IN clause) and adopts the `array_agg(... ORDER BY ply)` per-game subquery pattern from `endgame_repository.query_clock_stats_rows` for clock-diff at MG entry. Filter-params TypedDict threads through identically to avoid the `eval_n > total` debug nightmare.
- **Frontend additive prop extension** — `MiniBulletChart` gets two optional `ciLow?` / `ciHigh?` props with the same JSDoc style; existing call sites (Material Breakdown) untouched. Whisker uses the same `absolute top-1/2 -translate-y-1/2` overlay skeleton as the existing zero-line and value-fill bars.
- **Confidence pill is inline `<span>`, not a component** — no `ConfidencePill` exists today; `OpeningFindingCard.tsx:106-127` renders inline with `<Tooltip><span className="font-medium">{level}</span></Tooltip>`. Planner can extract a shared `<ConfidencePill>` component (~30 min) or duplicate the inline JSX. `ConfidenceTooltipContent` is already a reusable component and should be reused for the new column.
- **Mobile second-line pattern, not separate cards** — D-06 is a `sm:hidden mt-2 grid grid-cols-3` second line *inside* the existing `OpeningRow`, not the separate-card pattern from `EndgameClockPressureSection`. Keeps the row-as-row identity intact for collapse/expand state.
- **Sign at backend, never frontend** — Pitfall 1: backend signs `eval_cp` per user_color before serialization; frontend treats `avg_eval_pawns` as already-signed. Verification test asserts `white.avg_eval == -black.avg_eval` for identical games.

### File Created
`/home/aimfeld/Projects/Python/flawchess/.planning/phases/80-opening-stats-middlegame-entry-eval-and-clock-diff-columns/80-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference exact line numbers and idioms in PLAN.md files.

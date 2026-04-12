# Phase 54: Time Pressure — Clock Stats Table - Research

**Researched:** 2026-04-12
**Domain:** Endgame analytics — clock/time-pressure data, PostgreSQL window aggregation, React table UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None explicitly locked — discuss phase was skipped per user request.

### Claude's Discretion
All implementation choices are at Claude's discretion. Detailed specs are in
`docs/endgame-analysis-v2.md` section 3.1. Use ROADMAP phase goal, success criteria,
and codebase conventions to guide decisions.

### Deferred Ideas (OUT OF SCOPE)
None stated (discuss phase skipped).
</user_constraints>

---

## Summary

Phase 54 adds a "Time Pressure at Endgame Entry" table to the Endgames Stats page. For each time
control (bullet/blitz/rapid/classical), it shows: how many endgame games the user played, their
average clock at endgame entry (as % and absolute seconds), the opponent's average clock, the mean
clock diff, and a net timeout rate. Games without `clock_seconds` are excluded from time/clock
columns; the net timeout metric uses all endgame games.

The phase extends the existing `get_endgame_overview` pipeline: a new SQL query
(`query_clock_stats_rows`) fetches per-game clock data, a new pure-Python aggregator
(`_compute_clock_pressure`) computes the table rows, and the result is added to
`EndgameOverviewResponse` as `clock_pressure: ClockPressureResponse`. A new frontend component
(`EndgameClockPressureSection`) renders the table inside a new `charcoal-texture` container after
the Score Gap section.

**Primary recommendation:** Implement a separate `query_clock_stats_rows` repository function that
joins `game_positions` (for endgame entry clock) with `games` (for termination, time_control_bucket,
time_control_seconds), and compute the table rows in Python. Do not try to add clock columns to the
existing `query_endgame_entry_rows` — its array_agg pattern for material imbalance already produces
two complex aggregated columns and adding parity-filtered clock aggregation to the same subquery
would make it unmaintainable.

---

## Project Constraints (from CLAUDE.md)

- **Backend**: FastAPI 0.115.x, Python 3.13, SQLAlchemy 2.x async, Pydantic v2
- **Never use `asyncio.gather` on the same `AsyncSession`** — sequential query execution only
- **`ty` type-checker must pass with zero errors** — explicit return types, `Sequence[str]` for
  Literal list params, `# ty: ignore[rule-name]` with reason for suppressions
- **No SQL in services** — DB access only in `app/repositories/`
- **Router: no business logic** — only passes through to service
- **`apply_game_filters` in `query_utils.py`** — all standard filters go through this, never duplicated
- **Frontend `noUncheckedIndexedAccess`** — every array/Record index access needs narrowing
- **Theme constants in `theme.ts`** — semantic colors (win/loss) must come from there
- **`data-testid` on every interactive element** — tables, containers, and rows need testids
- **Sentry** — `capture_exception` in non-trivial service/router except blocks; no variable embedding
- **Knip in CI** — new exports must be actually imported somewhere

---

## Data Model (Verified)

### Relevant columns already present [VERIFIED: codebase grep]

**`game_positions`:**
- `ply` (SmallInteger) — half-move index; 0-based; even=white's move, odd=black's move
- `clock_seconds` (Float(24), nullable) — remaining clock from `%clk` PGN annotation
- `endgame_class` (SmallInteger, nullable) — 1–6; NULL for non-endgame positions

**`games`:**
- `user_color` (Enum: "white"|"black") — determines ply parity for user/opponent clock
- `time_control_bucket` (Enum: "bullet"|"blitz"|"rapid"|"classical", nullable)
- `time_control_seconds` (Integer, nullable) — estimated total game duration
- `termination` (Enum: "checkmate"|"resignation"|"timeout"|"draw"|"abandoned"|"unknown", nullable)
- `result` (Enum: "1-0"|"0-1"|"1/2-1/2")

### Clock parity rule [VERIFIED: docs/endgame-analysis-v2.md]
- `user_color = "white"` → user plies are **even** (0, 2, 4 …), opponent plies are **odd**
- `user_color = "black"` → user plies are **odd** (1, 3, 5 …), opponent plies are **even**
- The first user-ply in the endgame span is the endgame entry clock for the user
- The first opponent-ply in the endgame span is the endgame entry clock for the opponent

### Indexes relevant to the new query [VERIFIED: game_position.py]
```
ix_gp_user_endgame_game  ON game_positions (user_id, game_id, endgame_class, ply)
  WHERE endgame_class IS NOT NULL
  INCLUDE (material_imbalance)
```
This index currently includes `material_imbalance` but not `clock_seconds`. The new query needs
`clock_seconds` from `game_positions` filtered to the entry plies; it will use this index for the
span identification (user_id, game_id, endgame_class, ply) but will need a heap fetch for
`clock_seconds`. This is acceptable — clock_seconds is needed for relatively few rows (only the
entry-ply rows per span), not the full scan. No index change is required.

---

## Architecture Patterns

### Existing pattern: `query_endgame_entry_rows` [VERIFIED: endgame_repository.py]

The current approach uses a single subquery that groups `game_positions` by `(game_id, endgame_class)`,
applies `HAVING count(ply) >= 6`, and uses `array_agg(material_imbalance ORDER BY ply)[1]` to grab
the value at the minimum ply (endgame entry). This is efficient because it avoids a separate lookup join.

The new clock query needs the same span detection, but instead of a single value per span, it needs
**two values per span** (user's clock and opponent's clock at entry), where which ply is "user" vs
"opponent" depends on `games.user_color`. The parity logic is:
- user entry ply: the first ply in the span where `ply % 2 == (0 if user_color == "white" else 1)`
- opponent entry ply: the first ply in the span where `ply % 2 == (1 if user_color == "white" else 0)`

### Recommended SQL pattern for clock entry [ASSUMED — design decision]

The cleanest SQL approach: extend the span subquery to also aggregate `(ply, clock_seconds)` pairs
ordered by ply, then use CASE on parity to pull out the first user-ply and first opponent-ply.
However, doing this in a single subquery that also knows `user_color` (from the `games` table)
requires joining `games` inside the subquery or using a lateral join — adding complexity.

**Recommended alternative**: two `array_agg` calls ordered by ply to gather `clock_seconds` values
and their corresponding plies, then join `Game` to determine parity at the outer level.

Actually, the cleanest and most maintainable approach is: keep the span subquery as a pure
`game_positions` aggregation (no games join), get `array_agg(ply)` and `array_agg(clock_seconds)`
ordered by ply, then in the outer query join `Game` to compute parity-aware entry clock using CASE.

Specifically, since we need to find the *first ply of a given parity*, PostgreSQL does not have a
direct `first(x) FILTER (WHERE condition)` aggregate. Options:

**Option A: Two-step — subquery gets all ordered (ply, clock) arrays, Python extracts entry clocks**
- Subquery: `array_agg(ply ORDER BY ply)`, `array_agg(clock_seconds ORDER BY ply)` per span
- Outer query: join Game for user_color
- Python service: zip(plies, clocks) to find first user-ply and first opponent-ply

This is the most straightforward, avoids complex SQL, and fits the existing pattern of doing filtering
logic in Python after a DB fetch.

**Option B: SQL CASE on first-user-ply using FILTER-emulation with DISTINCT ON**
- More complex SQL, harder to read, doesn't add performance benefit

**Decision**: Use Option A — Python-side parity extraction after fetching ordered (ply, clock_seconds)
arrays per span. Consistent with the `array_agg ... ORDER BY ply` pattern already used in
`query_endgame_entry_rows`.

### Where clock_seconds may be NULL [VERIFIED: game_position.py, docs]

`clock_seconds` is nullable. The spec says games without clock data are excluded from time/clock
columns but still count for net timeout. A game has clock data if at least one position in its
endgame span has a non-NULL `clock_seconds`. In practice, either a game has full clock data (all
positions annotated with `%clk`) or none at all (no annotations). The Python aggregator should
treat a span as "has clock" only if both user_clock and opponent_clock were found (not None).

---

## Implementation Plan

### Backend

#### 1. New repository function: `query_clock_stats_rows` in `endgame_repository.py`

```python
# Returns one row per (game_id, endgame_class) span meeting ply threshold.
# Row shape: (game_id, time_control_bucket, time_control_seconds, termination,
#             result, user_color, plies_array, clock_seconds_array)
# where plies_array and clock_seconds_array are ordered by ply ascending.
#
# The service layer extracts the user/opponent entry clock from the arrays using parity.
```

The subquery is structurally identical to the span subquery in `query_endgame_entry_rows`,
except instead of `material_imbalance`, it aggregates `clock_seconds` (and `ply` for parity
lookup).

Columns needed from `Game`: `time_control_bucket`, `time_control_seconds`, `termination`,
`result`, `user_color`. These are all already on the Game model.

Standard game filters apply (platform, rated, opponent_type, recency, opponent_strength) — use
`apply_game_filters`.

**No time_control filter applied to the outer query**: the service layer groups all endgame games
by `time_control_bucket` and the time_control sidebar filter works differently for this section:
- No filter → show all rows (hide < 10 games rows)
- One selected → single row
- Multiple selected → selected rows only

Wait — `apply_game_filters` handles the time_control filter. Since the service layer needs to group
by `time_control_bucket` and the time_control filter restricts which games are included, the filter
should still be applied at the DB level as normal. The "no filter → all rows" behavior simply means
no time_control filter is passed (the query returns all time controls), and the service shows all
rows. When a filter is active, only the matching rows are returned from DB, and the service shows
only those.

#### 2. New schemas in `app/schemas/endgames.py`

```python
class ClockStatsRow(BaseModel):
    """One row in the Clock Stats table — one per time control."""
    time_control: str          # "bullet" | "blitz" | "rapid" | "classical"
    label: str                 # "Bullet" | "Blitz" | "Rapid" | "Classical"
    total_endgame_games: int   # all endgame games for this time control (for net timeout)
    clock_games: int           # endgame games with clock data (for time/diff columns)
    user_avg_pct: float | None       # mean (user_clock / time_control_seconds * 100), None if no clock data
    user_avg_seconds: float | None   # mean user_clock in seconds
    opp_avg_pct: float | None        # mean (opp_clock / time_control_seconds * 100)
    opp_avg_seconds: float | None    # mean opp_clock in seconds
    avg_clock_diff_seconds: float | None  # mean (user_clock - opp_clock) in seconds
    net_timeout_rate: float    # (timeout wins - timeout losses) / total_endgame_games * 100

class ClockPressureResponse(BaseModel):
    """Time Pressure at Endgame Entry — table broken down by time control."""
    rows: list[ClockStatsRow]
    total_clock_games: int     # total endgame games with clock data across all rows
    total_endgame_games: int   # total endgame games across all rows
```

#### 3. New service function: `_compute_clock_pressure` in `endgame_service.py`

Pure function, no DB calls. Input: list of rows from `query_clock_stats_rows`.

Algorithm:
1. Group rows by `time_control_bucket`
2. For each group:
   - Count `total_endgame_games` (deduplicated by game_id — same game may appear in multiple
     endgame_class spans)
   - For each span row, extract user entry clock and opponent entry clock using ply parity:
     - zip(plies_array, clock_seconds_array)
     - first entry where ply % 2 matches user_color parity = user_clock
     - first entry where ply % 2 matches opponent parity = opp_clock
   - Only include in clock averages if both user_clock and opp_clock are not None
   - Compute net timeout: games where termination == "timeout" and user won vs lost
     (game_id deduplicated, since the same game_id can appear in multiple endgame spans)
3. Hide rows where `total_endgame_games < MIN_GAMES_FOR_RELIABLE_STATS` (10)

**Deduplication note**: a single game can appear in multiple (game_id, endgame_class) spans. For
the clock stats table:
- `total_endgame_games`: count distinct game_ids
- Clock averages: per-span, not per-game; if game appears in 2 spans, its clock at the first ply
  of each span may differ (they can occur at different plies), so each span contributes
  independently. This is consistent with how material_imbalance is computed in Phase 53.
- Net timeout: per-game (a game either ends in timeout or it doesn't), so deduplicate by game_id.

#### 4. Extend `get_endgame_overview` in `endgame_service.py`

Add a `query_clock_stats_rows` call (sequential, after existing queries), compute
`_compute_clock_pressure`, and include `clock_pressure: ClockPressureResponse` in
`EndgameOverviewResponse`.

#### 5. Update `EndgameOverviewResponse` in `app/schemas/endgames.py`

```python
class EndgameOverviewResponse(BaseModel):
    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    conv_recov_timeline: ConvRecovTimelineResponse
    score_gap_material: ScoreGapMaterialResponse
    clock_pressure: ClockPressureResponse  # Phase 54: time pressure at endgame entry
```

### Frontend

#### 1. Extend `EndgameOverviewResponse` in `frontend/src/types/endgames.ts`

Add:
```typescript
export interface ClockStatsRow {
  time_control: string;       // "bullet" | "blitz" | "rapid" | "classical"
  label: string;              // "Bullet" | "Blitz" | "Rapid" | "Classical"
  total_endgame_games: number;
  clock_games: number;
  user_avg_pct: number | null;
  user_avg_seconds: number | null;
  opp_avg_pct: number | null;
  opp_avg_seconds: number | null;
  avg_clock_diff_seconds: number | null;
  net_timeout_rate: number;
}

export interface ClockPressureResponse {
  rows: ClockStatsRow[];
  total_clock_games: number;
  total_endgame_games: number;
}

// Add to EndgameOverviewResponse:
// clock_pressure: ClockPressureResponse;
```

#### 2. New component: `EndgameClockPressureSection.tsx`

Location: `frontend/src/components/charts/EndgameClockPressureSection.tsx`

Renders a table with columns: Time Control | Games | My avg time | Opp avg time | Avg clock diff | Net timeout rate.

- "My avg time" column: `"12% (7s)"` format — format function: `formatClock(pct, secs)`
- "Opp avg time" column: same format
- "Avg clock diff" column: signed seconds with + prefix for positive, e.g. `"+45s"` or `"-5s"`
- "Net timeout rate" column: signed percentage with + prefix
- Rows with `total_endgame_games < 10` are hidden (the backend already filters them, but
  verify client-side too for safety)
- No `clock_games` columns visible: instead, a note below the table: "Based on X of Y endgame games
  (Z% have clock data)." — uses `total_clock_games` and `total_endgame_games` from response.
- `data-testid="clock-pressure-section"` on container
- `data-testid="clock-pressure-table"` on table
- `data-testid={`clock-pressure-row-${row.time_control}`}` on each `<tr>`
- InfoPopover explaining what the columns mean

#### 3. Integrate in `Endgames.tsx`

Add `const clockPressureData = overviewData?.clock_pressure;` in the data extraction block.

Add the new section container after the `scoreGapData` container:
```tsx
{clockPressureData && clockPressureData.rows.length > 0 && (
  <div className="charcoal-texture rounded-md p-4">
    <EndgameClockPressureSection data={clockPressureData} />
  </div>
)}
```

Import `EndgameClockPressureSection` from `@/components/charts/EndgameClockPressureSection`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Game filter application | Custom filter logic | `apply_game_filters()` from `query_utils.py` |
| Array aggregation in SQL | Custom JOIN for entry ply | `array_agg(x ORDER BY ply)[1]` / Python parity extraction |
| Color constants | Hard-coded hex | `WDL_WIN`, `WDL_LOSS`, `GAUGE_WARNING` from `theme.ts` |
| TypedDicts for accumulators | dict[str, Any] | TypedDict per CLAUDE.md guidance |
| Array index access in TS | `arr[i]` without check | Assign to local variable, check undefined |

---

## Common Pitfalls

### Pitfall 1: Deduplication of multi-span games in clock averages
**What goes wrong:** A game reaching both rook and pawn endgame spans appears twice in the span
subquery result. If you compute clock averages without deduplication, you double-count that game's
clock data.
**Why it happens:** `query_clock_stats_rows` groups by `(game_id, endgame_class)`, so multi-class
games appear once per class.
**How to avoid:** For clock averages, each span is independent (different entry plies, different
clocks). This is intentional and consistent with how the existing material stats work. For net
timeout counting, deduplicate game_ids before checking termination.
**Warning signs:** Net timeout numerator/denominator is higher than total distinct games.

### Pitfall 2: NULL clock_seconds when one ply is annotated
**What goes wrong:** Some games have partial clock annotations (clock present on some plies but not
all). Checking only whether `clock_seconds_array[0]` is None may miss cases where the entry ply's
clock is present but no opponent-ply clock is in the span.
**How to avoid:** Extract both user_clock and opp_clock from the parity scan; only count a span as
"has clock data" if BOTH are not None.

### Pitfall 3: Confusing ply parity for white vs black
**What goes wrong:** Even plies (0, 2, 4…) are white's moves (white makes the first move). The
initial position (ply 0) is a special case — in the codebase, ply represents the board state BEFORE
the move `move_san`, so ply 0 is the starting position with white to move.
**How to avoid:** Verify against the `docs/endgame-analysis-v2.md` spec: "even ply if user_color =
white, odd ply if user_color = black". Test with a game where user_color = black.

### Pitfall 4: time_control_seconds = None
**What goes wrong:** `time_control_seconds` is nullable on `Game`. Division by zero or None when
computing `clock_seconds / time_control_seconds * 100`.
**How to avoid:** Skip the percentage computation (set to None) if `time_control_seconds` is None
or 0. Still include the raw `clock_seconds` value.

### Pitfall 5: Missing `clock_pressure` in `EndgameOverviewResponse` TypeScript type
**What goes wrong:** Adding the field to Python schema but forgetting to update the TypeScript type
causes `overviewData?.clock_pressure` to be typed as `undefined` even when the backend returns data.
**How to avoid:** Update `frontend/src/types/endgames.ts` as part of the same plan wave as the
backend schema change.

### Pitfall 6: `ty` type-check failures on array indexing
**What goes wrong:** Accessing `plies_array[i]` where `plies_array` is `list[int | None]` in a loop
may fail `ty` if the access isn't properly narrowed.
**How to avoid:** Use `for ply, clock in zip(plies_array, clocks_array): if ply is None or clock is None: continue`.

---

## Architecture Patterns — Codebase Specifics

### Existing `get_endgame_overview` query order [VERIFIED: endgame_service.py lines 986–1094]

Current query sequence:
1. `query_endgame_entry_rows` → entry_rows (used by stats, performance, score_gap_material)
2. `count_filtered_games` → total_games
3. `query_endgame_performance_rows` → endgame_rows, non_endgame_rows
4. `get_endgame_timeline` (calls `query_endgame_timeline_rows`)
5. `get_conv_recov_timeline` (calls `query_conv_recov_timeline_rows`)

New query inserts as step 6 (sequential, same session):
6. `query_clock_stats_rows` → clock_rows (new)

### `array_agg` pattern from existing code [VERIFIED: endgame_repository.py lines 105–125]

```python
from sqlalchemy import func, type_coerce
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by
from sqlalchemy.types import SmallInteger as SmallIntegerType

entry_imbalance_agg = type_coerce(
    func.array_agg(
        aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())
    ),
    ARRAY(SmallIntegerType),
)[1]
```

For the clock query, use `ARRAY(Float(24))` and `ARRAY(SmallIntegerType)` for clock_seconds and
plies respectively. Note: `[1]` is 1-indexed in PostgreSQL arrays; Python-side extraction will
use zero-indexed iteration.

For the new query, do NOT use `[1]` indexing in SQL — fetch the full arrays so Python can apply
parity filtering:

```python
from sqlalchemy.types import Float as FloatType

ply_array_agg = type_coerce(
    func.array_agg(
        aggregate_order_by(GamePosition.ply, GamePosition.ply.asc())
    ),
    ARRAY(SmallIntegerType),
)

clock_array_agg = type_coerce(
    func.array_agg(
        aggregate_order_by(GamePosition.clock_seconds, GamePosition.ply.asc())
    ),
    ARRAY(FloatType()),
)
```

### Service layer TypedDict pattern [VERIFIED: endgame_service.py _compute_score_gap_material]

The existing code uses per-bucket `dict[str, int]` accumulators. For the new function, use a
TypedDict for the per-time-control accumulator:

```python
from typing import TypedDict

class _ClockAccumulator(TypedDict):
    total_endgame_game_ids: set[int]     # for deduplication
    timeout_win_game_ids: set[int]       # for net timeout
    timeout_loss_game_ids: set[int]      # for net timeout
    clock_user_values: list[float]       # for averaging
    clock_opp_values: list[float]        # for averaging
    clock_diff_values: list[float]       # for averaging
    clock_pct_user_values: list[float]   # for pct averaging
    clock_pct_opp_values: list[float]    # for pct averaging
```

---

## Code Examples

### Python parity extraction (service layer)
```python
# Source: [ASSUMED — design decision consistent with docs/endgame-analysis-v2.md]
def _extract_entry_clocks(
    plies: list[int],
    clocks: list[float | None],
    user_color: str,
) -> tuple[float | None, float | None]:
    """Return (user_entry_clock, opp_entry_clock) at endgame entry.

    user_color determines ply parity: white=even, black=odd.
    Returns (None, None) if the expected entry plies have no clock data.
    """
    user_parity = 0 if user_color == "white" else 1
    user_clock: float | None = None
    opp_clock: float | None = None
    for ply, clock in zip(plies, clocks):
        if ply % 2 == user_parity and user_clock is None:
            user_clock = clock
        elif ply % 2 != user_parity and opp_clock is None:
            opp_clock = clock
        if user_clock is not None and opp_clock is not None:
            break
    return user_clock, opp_clock
```

### Frontend column format helper
```typescript
// Source: [ASSUMED — design decision per docs/endgame-analysis-v2.md]
function formatClockCell(pct: number | null, secs: number | null): string {
  if (pct === null || secs === null) return '—';
  return `${pct.toFixed(0)}% (${secs.toFixed(0)}s)`;
}

function formatSignedSeconds(diff: number | null): string {
  if (diff === null) return '—';
  const sign = diff >= 0 ? '+' : '';
  return `${sign}${diff.toFixed(0)}s`;
}

function formatNetTimeoutRate(rate: number): string {
  const sign = rate >= 0 ? '+' : '';
  return `${sign}${rate.toFixed(1)}%`;
}
```

### Backend schema for ClockStatsRow
```python
# Source: [ASSUMED — design decision consistent with docs/endgame-analysis-v2.md]
class ClockStatsRow(BaseModel):
    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    label: str
    total_endgame_games: int
    clock_games: int
    user_avg_pct: float | None
    user_avg_seconds: float | None
    opp_avg_pct: float | None
    opp_avg_seconds: float | None
    avg_clock_diff_seconds: float | None
    net_timeout_rate: float
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (async via pytest-asyncio) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_endgame_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Behavior | Test Type | File | Notes |
|----------|-----------|------|-------|
| `_extract_entry_clocks`: white user, even plies | unit | `test_endgame_service.py` | New test class |
| `_extract_entry_clocks`: black user, odd plies | unit | `test_endgame_service.py` | New test class |
| `_extract_entry_clocks`: NULL clock_seconds | unit | `test_endgame_service.py` | Returns (None, None) |
| `_compute_clock_pressure`: basic row building | unit | `test_endgame_service.py` | Uses mock rows |
| `_compute_clock_pressure`: deduplication for net timeout | unit | `test_endgame_service.py` | Multi-span games |
| `_compute_clock_pressure`: hide rows < 10 games | unit | `test_endgame_service.py` | Row filtering |
| `_compute_clock_pressure`: time_control_seconds = None | unit | `test_endgame_service.py` | pct = None |
| `query_clock_stats_rows`: returns rows with clock data | integration | `test_endgame_repository.py` | Needs `db_session` |
| `query_clock_stats_rows`: filters by game filters | integration | `test_endgame_repository.py` | Existing filter pattern |
| `get_endgame_overview`: includes clock_pressure field | smoke | `test_endgame_service.py` | mock patch |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_endgame_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + `uv run ty check app/ tests/` zero errors before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] New test class `TestExtractEntryClocks` in `tests/test_endgame_service.py`
- [ ] New test class `TestComputeClockPressure` in `tests/test_endgame_service.py`
- [ ] Integration test `test_query_clock_stats_rows_*` in `tests/test_endgame_repository.py`

---

## Environment Availability

Step 2.6: SKIPPED — this phase is code/config-only; no external dependencies beyond the existing
PostgreSQL dev container and npm/uv toolchain (both already in use).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `array_agg(clock_seconds ORDER BY ply)` returns elements in ply order with NULLs in position | Code Examples | Could silently return wrong entry clock; test would catch |
| A2 | Per-span (not per-game) averaging for clock stats is the right deduplication choice | Architecture | Could over/under-weight games with multiple endgame spans |
| A3 | `ARRAY(FloatType())` is the correct SQLAlchemy type for `clock_seconds` array cast | Standard Stack | ty check would fail; fix at implementation time |
| A4 | A row with `total_endgame_games < 10` should be hidden (not dimmed) per the spec | Architecture | Spec says "hide entire time control row" — confirmed in docs/endgame-analysis-v2.md §5 |
| A5 | Using a separate `query_clock_stats_rows` function (not extending `query_endgame_entry_rows`) is the right structure | Architecture | Slight code duplication; lower risk than complicating the existing query |

A4 is confirmed, not assumed: docs/endgame-analysis-v2.md §5: "For the summary table (section 3.1),
hide the entire time control row if total endgame games for that time control < 10."

---

## Open Questions (RESOLVED)

1. **Should the backend filter out rows with < 10 games, or return all rows and let the frontend filter?**
   - **RESOLVED:** Filter in the service layer (Python), not the DB. This mirrors the pattern in
     `_aggregate_endgame_stats` where filtering logic lives in the service. The frontend renders
     what it receives. Incorporated into Plan 54-01 Task 2.

2. **Should `clock_pressure` be `None` vs an empty `ClockPressureResponse` when there are no endgame games?**
   - **RESOLVED:** Always return a `ClockPressureResponse` (never None in the Pydantic model);
     the `rows` list will simply be empty. The frontend already handles empty lists consistently. Incorporated into Plan 54-01 Task 1.

3. **Row ordering in the frontend table?**
   - **RESOLVED:** Fixed order matching time control from fastest to slowest: bullet → blitz →
     rapid → classical. Backend service should sort rows in this order. Incorporated into Plan 54-01 Task 2.

---

## Sources

### Primary (HIGH confidence)
- `app/repositories/endgame_repository.py` — array_agg pattern, span subquery structure, filters
- `app/services/endgame_service.py` — service layer patterns, get_endgame_overview structure
- `app/schemas/endgames.py` — existing response types, EndgameOverviewResponse
- `app/models/game.py` — Game model columns (termination, time_control_bucket, etc.)
- `app/models/game_position.py` — GamePosition columns (ply, clock_seconds, endgame_class)
- `docs/endgame-analysis-v2.md` §3.1, §5 — full spec: formulas, column definitions, display rules
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — table styling pattern to follow
- `frontend/src/types/endgames.ts` — TypeScript type structure
- `frontend/src/pages/Endgames.tsx` — integration point for new section
- `frontend/src/lib/theme.ts` — color constants

### Secondary (MEDIUM confidence)
- `tests/test_endgame_service.py` — test patterns and fixtures
- `tests/test_endgame_repository.py` — integration test fixture patterns (`_seed_game`, `db_session`)
- `tests/conftest.py` — `ensure_test_user`, `db_session` fixture

---

## Metadata

**Confidence breakdown:**
- Data model: HIGH — verified from models and docs
- SQL pattern: HIGH — extends existing verified array_agg pattern
- Python service logic: HIGH — clear spec, straightforward aggregation
- Frontend component: HIGH — clear spec, existing table component as model
- Test requirements: HIGH — existing test file structure is clear

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable domain — schema doesn't change unless migrations run)

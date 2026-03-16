# Phase 12: Backend Next-Moves Endpoint - Research

**Researched:** 2026-03-16
**Domain:** FastAPI / SQLAlchemy async — aggregation query design for move explorer
**Confidence:** HIGH

## Summary

Phase 12 adds a single `POST /analysis/next-moves` endpoint on the existing `analysis` router. It aggregates next moves for a queried position hash, returning per-move W/D/L stats plus a position-level summary and per-move transposition counts. All existing filter parameters apply. The codebase already has the complete supporting infrastructure: `move_san` column, covering index `ix_gp_user_full_hash_move_san`, `_build_base_query` filter builder, `WDLStats` schema, `derive_user_result`, and `recency_cutoff` helpers.

The primary design challenge is writing two efficient aggregation queries: (1) the main next-moves query that groups by `move_san` and produces per-move W/D/L via `COUNT(DISTINCT game_id)`, and (2) the transposition-count query that, for each resulting position's `full_hash`, counts distinct games reaching it under the same filters. Both use `full_hash` exclusively — no `match_side` concept applies here.

The secondary challenge is W/D/L computation. The existing code pattern (fetch all `(result, user_color)` tuples and loop in Python) works for the position-stats summary but is inappropriate for per-move aggregation — that must be done in SQL using `CASE` expressions inside `COUNT(DISTINCT ...)` or a `FILTER` clause to avoid N+1 queries.

**Primary recommendation:** Write two targeted repository functions — `query_next_moves` and `query_transposition_counts` — each using a single database round-trip. Compose them in a new `get_next_moves` service function that also computes position_stats by reusing the existing `query_all_results` function.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Response contract**
- Dedicated `NextMovesRequest` schema (not extending AnalysisRequest) — same filter fields but no pagination (offset/limit)
- Each move entry includes: `move_san`, `game_count`, `wins`, `draws`, `losses`, `win_pct`, `draw_pct`, `loss_pct`, `result_hash` (resulting position's full_hash as string), `result_fen` (resulting board FEN), `transposition_count`
- Response includes top-level `position_stats` (total games, W/D/L for the queried position) alongside the moves list — avoids a separate /analysis/positions call

**Match side behavior**
- Next-moves endpoint uses `full_hash` only — no `match_side` parameter
- Both move aggregation and position_stats use full_hash exclusively
- White/black hash matching doesn't apply to move exploration (it's about exact positions)

**Transposition handling**
- `game_count` per move: `COUNT(DISTINCT game_id)` grouped by `move_san` — a game reaching the same position multiple times and playing the same move counts once for that move
- `transposition_count` per move: total distinct games where the resulting position's full_hash appears (via any move order), using the same active filters
- Computed eagerly for all moves in a single batch query (one extra DB round-trip, not lazy on hover)
- Frontend derives "reached via other moves" as `transposition_count - game_count`
- Transposition count respects active filters (consistent with move aggregation)

**Sort and limits**
- Default sort: by `game_count` descending (most-played moves first)
- Support `sort_by: 'frequency' | 'win_rate'` parameter, default `frequency`
- No limit on moves returned — return all distinct moves found (positions rarely have >30 legal moves)

### Claude's Discretion
- Exact SQL query structure and optimization approach
- Whether to use CTE, subquery, or separate queries for transposition counts
- Error handling for invalid hash values
- Test structure and fixture design

### Deferred Ideas (OUT OF SCOPE)
- Alphabetical sort option — excluded from sort_by for now, add if needed later
- MEXP-09: Show resulting position FEN/thumbnail on move hover — Phase 13 frontend concern (result_fen is already in the response)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEXP-04 | Backend endpoint returns next moves for a given position hash with game count and W/D/L stats per move, respecting all existing filters | `query_next_moves` repository function + `get_next_moves` service + router registration |
| MEXP-05 | Transpositions handled correctly — each game counted only once per move even if position reached via different move orders | `COUNT(DISTINCT game_id)` grouped by `move_san` in the aggregation query |
| MEXP-10 | Next-moves endpoint returns transposition count (total games reaching the resulting position via any move order) alongside direct game count | `query_transposition_counts` repository function using result_hash values from step one |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.x async | ORM + query builder for aggregation | Already in use; `func`, `case`, `label` support CTEs |
| FastAPI | 0.115.x | Router and dependency injection | Already in use |
| Pydantic v2 | 2.x | Request/response schemas | Already in use; `field_validator` for BigInt coercion |
| python-chess | 1.10.x | Compute `result_fen` from `result_hash` | Already imported in services |

### Key SQLAlchemy constructs needed

| Construct | Import | Purpose |
|-----------|--------|---------|
| `func.count` | `sqlalchemy.func` | COUNT(DISTINCT ...) aggregation |
| `case` | `sqlalchemy` | CASE WHEN for win/draw/loss per move |
| `func.round` | `sqlalchemy.func` | Round percentages at DB level (optional; Python is fine too) |
| `.label()` | query method | Named columns in result tuples |
| `.group_by()` | query method | GROUP BY move_san |
| `.in_()` | column method | Batch filter by result_hash list |

No new dependencies required. All needed libraries are already installed.

---

## Architecture Patterns

### File layout (additions only)
```
app/
├── repositories/
│   └── analysis_repository.py   # add query_next_moves, query_transposition_counts
├── services/
│   └── analysis_service.py      # add get_next_moves
├── schemas/
│   └── analysis.py              # add NextMovesRequest, NextMoveEntry, NextMovesResponse
└── routers/
    └── analysis.py              # add POST /analysis/next-moves handler
tests/
└── test_analysis_repository.py  # extend with TestNextMoves class
```

### Pattern 1: Main next-moves aggregation query

The core query joins `game_positions` to `games`, filters by `user_id` + `full_hash == target_hash`, groups by `move_san`, and uses conditional counting for W/D/L. The covering index `ix_gp_user_full_hash_move_san` makes this fast.

Transposition-safe counting uses `COUNT(DISTINCT gp.game_id)` in the group. A game that visits the queried position at two different plies and plays the same move is counted once for that move.

**Key insight on W/D/L in SQL for this pattern:**

Because W/D/L depends on both `result` (from `games`) and `user_color` (from `games`), the aggregation must be done with conditional counting. `CASE WHEN ... THEN game_id ELSE NULL END` inside `COUNT(DISTINCT ...)` is the standard PostgreSQL approach:

```python
# Source: verified against SQLAlchemy 2.x docs + PostgreSQL CASE syntax
from sqlalchemy import func, case, select
from app.models.game import Game
from app.models.game_position import GamePosition

win_condition = case(
    (
        ((Game.result == "1-0") & (Game.user_color == "white")) |
        ((Game.result == "0-1") & (Game.user_color == "black")),
        Game.id,
    ),
    else_=None,
)
draw_condition = case(
    (Game.result == "1/2-1/2", Game.id),
    else_=None,
)
loss_condition = case(
    (
        ((Game.result == "1-0") & (Game.user_color == "black")) |
        ((Game.result == "0-1") & (Game.user_color == "white")),
        Game.id,
    ),
    else_=None,
)

stmt = (
    select(
        GamePosition.move_san,
        func.count(Game.id.distinct()).label("game_count"),
        func.count(win_condition.distinct()).label("wins"),
        func.count(draw_condition.distinct()).label("draws"),
        func.count(loss_condition.distinct()).label("losses"),
    )
    .join(Game, Game.id == GamePosition.game_id)
    .where(
        GamePosition.user_id == user_id,
        GamePosition.full_hash == target_hash,
        GamePosition.move_san.isnot(None),
    )
    .group_by(GamePosition.move_san)
)
# ... apply filters, order_by game_count desc
```

**Important:** `move_san IS NOT NULL` filter required — the final ply row has `NULL` move_san and must be excluded.

**Important:** `func.count(win_condition.distinct())` in SQLAlchemy 2.x syntax requires care. The `DISTINCT` modifier inside `COUNT(CASE WHEN ...)` is supported by PostgreSQL and can be written as `func.count(win_condition.distinct())`. If that syntax causes issues, a safe alternative is `func.count(func.distinct(win_condition))` — verify during implementation.

### Pattern 2: Transposition count batch query

After the main query returns N move entries, each with a `result_hash` (the `full_hash` of the resulting position), run a single batch query to get transposition counts for all result hashes at once:

```python
# Source: SQLAlchemy 2.x select + group_by + in_() pattern
stmt = (
    select(
        GamePosition.full_hash.label("result_hash"),
        func.count(GamePosition.game_id.distinct()).label("transposition_count"),
    )
    .join(Game, Game.id == GamePosition.game_id)
    .where(
        GamePosition.user_id == user_id,
        GamePosition.full_hash.in_(result_hash_list),
    )
    .group_by(GamePosition.full_hash)
)
# apply same filters as main query
```

Returns a dict `{result_hash: transposition_count}` that is merged into move entries before response serialization.

The transposition count for a move is the total distinct games that ever reach the resulting position under the same filters — not just games that took the direct path. This is intentionally larger than or equal to `game_count`.

### Pattern 3: position_stats computation

Reuse `query_all_results` from the existing repository with `hash_column=GamePosition.full_hash` and `target_hash=target_hash`. Then loop over `(result, user_color)` tuples with `derive_user_result` (exactly as in `analyze()`). This produces the `WDLStats` for the top-level `position_stats` field.

No new DB function needed — this is direct reuse.

### Pattern 4: result_fen lookup

Each move entry needs `result_fen` (the board FEN of the resulting position). This cannot be computed purely from `result_hash` — it must be fetched from the DB or computed via python-chess.

Two approaches:
- **DB lookup (preferred):** `SELECT DISTINCT full_hash, board_fen FROM game_positions WHERE user_id=? AND full_hash IN (...)` — but `board_fen` is not stored in `game_positions`. Only hashes are stored.
- **Python-chess replay (correct approach):** `result_fen` is the FEN after the move is played. Since the endpoint already knows `target_hash` maps to a specific position, we need the FEN of the position *after* each move. This FEN is not stored anywhere.

**Resolution:** The only stored FEN information is via python-chess board state. The `result_fen` must be computed differently. Options:
1. Store `board_fen` in `game_positions` — out of scope for Phase 12.
2. Fetch one sample game that has both the source position and the target move, replay to get the result FEN.
3. Accept that `result_fen` may require a separate lookup and use a lightweight approach: query one `game_id` + `ply` pair where `full_hash == source_hash AND move_san == san`, then fetch that game's PGN and replay to ply+1.

Option 3 is complex. **Recommended approach for Phase 12:** For each distinct `(source_hash, move_san)` pair, query `game_positions` to find one row where `full_hash == result_hash`, then use a separate PGN query to get the FEN — OR store the result_fen via a simpler strategy:

**Simplest correct approach:** Query `game_positions` for one row per `result_hash` — joined to its game's PGN — and replay to find the FEN. This is O(N moves) PGN replays, but N is small (<30 moves per position) and it only runs once per request.

Actually, the simplest approach: for each move entry, we already have a `game_id` from the aggregation (not directly, but we can get one). Join `game_positions gp2` where `gp2.full_hash = result_hash` to get one sample `(game_id, ply)`, then replay that game's PGN to ply and extract FEN.

**Practical recommendation:** Implement `result_fen` via a batch query: for each `result_hash`, get one `(game_id, ply)` sample from `game_positions`, then fetch the PGN of those games and use python-chess to replay to the target ply. python-chess `board.board_fen()` at that ply gives the correct FEN. This requires one extra DB query (batch, not N+1) and one python-chess replay per distinct move (cheap).

Alternatively, since the CONTEXT.md says `result_fen` is "resulting board FEN", and python-chess is already in the stack, the cleanest approach is:

1. For each `result_hash`, query `SELECT game_id, ply FROM game_positions WHERE user_id=? AND full_hash=? LIMIT 1 FOR EACH result_hash` (use `DISTINCT ON (full_hash)` or a lateral join).
2. Batch fetch those game PGNs.
3. Replay with python-chess, `board.board_fen()` at the target ply.

This is one batch DB query + one PGN per distinct move, which is always <30 and typically <10.

### Anti-Patterns to Avoid

- **N+1 transposition queries:** never query transposition count per move in a loop — batch with `IN (...)` clause.
- **`COUNT(*)` for move aggregation:** use `COUNT(DISTINCT game_id)` — `COUNT(*)` double-counts transposed games.
- **Fetching `result_fen` per move in a loop:** use DISTINCT ON batch query for (result_hash → game_id/ply) mapping.
- **Replicating filter logic inline:** always route through `_build_base_query` pattern or extract the filter application into a shared helper to avoid drift between endpoints.
- **Including ply-0 or final-position rows in next-moves:** always filter `move_san IS NOT NULL` in the aggregation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Filter application | Custom WHERE builder | `_build_base_query` pattern or adapt it | All 6 filter types already handled, tested |
| W/D/L derivation | Custom result parsing | `derive_user_result` from `analysis_service` | Handles all 6 result×color combinations |
| Recency datetime | Custom timedelta math | `recency_cutoff` from `analysis_service` | Already maps all recency strings |
| BigInt coercion | Custom JSON parsing | `field_validator` from `AnalysisRequest` | Handles JS BigInt string → Python int |
| Position stats | New stats query | `query_all_results` + existing loop | Already tested, correct DISTINCT dedup |
| FEN computation | Custom board state replay | python-chess `board.board_fen()` | Correct; handles castling/en-passant exclusion |

---

## Common Pitfalls

### Pitfall 1: `move_san IS NULL` rows included in aggregation
**What goes wrong:** The final ply of every game has `move_san = NULL`. Including NULL in `GROUP BY move_san` creates a spurious `NULL` move entry in the response.
**Why it happens:** `GROUP BY` in PostgreSQL includes `NULL` as a distinct group.
**How to avoid:** Add `.where(GamePosition.move_san.isnot(None))` before grouping.
**Warning signs:** Response contains a move entry with `move_san: null`.

### Pitfall 2: `COUNT(DISTINCT ...)` with CASE WHEN returns 1 for NULL
**What goes wrong:** `COUNT(DISTINCT CASE WHEN condition THEN game_id ELSE NULL END)` counts NULL as 0 (PostgreSQL correctly ignores NULLs in COUNT), but this can be surprising if you use `COUNT(*)` instead.
**Why it happens:** `COUNT(*)` counts all rows including NULLs; `COUNT(expr)` skips NULLs.
**How to avoid:** Always use `func.count(expr)` not `func.count()` for conditional counts.
**Warning signs:** wins + draws + losses > game_count for a move entry.

### Pitfall 3: SQLAlchemy 2.x `DISTINCT` modifier inside aggregate
**What goes wrong:** `func.count(column.distinct())` syntax may generate `COUNT(DISTINCT column)` correctly, but `func.count(case_expr.distinct())` is less commonly tested. PostgreSQL supports `COUNT(DISTINCT expression)` where the expression is a CASE, but SQLAlchemy may need `.distinct()` called on the column before passing to `func.count`.
**Why it happens:** SQLAlchemy's `.distinct()` modifier behavior varies by expression type.
**How to avoid:** Test the generated SQL with `str(stmt.compile(dialect=postgresql.dialect()))` during development. If `func.count(case_expr.distinct())` is problematic, use a subquery approach or compute W/D/L in Python after fetching `(move_san, game_id, result, user_color)` rows.
**Warning signs:** SQLAlchemy compilation error or wrong counts in tests.

### Pitfall 4: Transposition count query not applying same filters
**What goes wrong:** `transposition_count` for a move reflects all games globally, not just filtered games.
**Why it happens:** The second batch query forgets to apply `time_control`, `rated`, `recency`, `color`, etc.
**How to avoid:** Pass all filter parameters to `query_transposition_counts` and apply the same WHERE clauses. The user-facing guarantee is: "all stats are consistent for your current filter selection."
**Warning signs:** `transposition_count < game_count` for any move (impossible if filters match).

### Pitfall 5: result_fen wrong when using `board.fen()` vs `board.board_fen()`
**What goes wrong:** `board.fen()` includes castling rights, en-passant square, halfmove clock — these differ across games even for the same piece position. Two games at the "same position" will show different FENs.
**Why it happens:** CLAUDE.md explicitly warns: "Use `board.board_fen()` (piece placement only) not `board.fen()`."
**How to avoid:** Always use `board.board_fen()` for any stored or returned FEN value.
**Warning signs:** Two different FENs returned for what appears to be the same position.

### Pitfall 6: user_id isolation — transposition count must filter by user_id
**What goes wrong:** `query_transposition_counts` returns game counts from other users' games.
**Why it happens:** Forgetting `WHERE user_id = ?` in the transposition batch query.
**How to avoid:** `game_positions.user_id` is denormalized for exactly this purpose — always include it.
**Warning signs:** `transposition_count` larger than user's total game count.

---

## Code Examples

### Full aggregation query sketch

```python
# Source: SQLAlchemy 2.x official docs — aggregate functions + CASE
from sqlalchemy import case, func, select
from app.models.game import Game
from app.models.game_position import GamePosition

def _win_expr(game_id_col, result_col, color_col):
    """CASE WHEN user won THEN game_id ELSE NULL — for COUNT(DISTINCT ...)."""
    return case(
        (
            ((result_col == "1-0") & (color_col == "white")) |
            ((result_col == "0-1") & (color_col == "black")),
            game_id_col,
        ),
        else_=None,
    )

def _draw_expr(game_id_col, result_col):
    return case((result_col == "1/2-1/2", game_id_col), else_=None)

def _loss_expr(game_id_col, result_col, color_col):
    return case(
        (
            ((result_col == "1-0") & (color_col == "black")) |
            ((result_col == "0-1") & (color_col == "white")),
            game_id_col,
        ),
        else_=None,
    )

# Main aggregation (apply filters + order_by after this base)
stmt = (
    select(
        GamePosition.move_san,
        GamePosition.full_hash.label("source_hash"),   # for reference
        func.count(Game.id.distinct()).label("game_count"),
        func.count(_win_expr(Game.id, Game.result, Game.user_color).distinct()).label("wins"),
        func.count(_draw_expr(Game.id, Game.result).distinct()).label("draws"),
        func.count(_loss_expr(Game.id, Game.result, Game.user_color).distinct()).label("losses"),
    )
    .join(Game, Game.id == GamePosition.game_id)
    .where(
        GamePosition.user_id == user_id,
        GamePosition.full_hash == target_hash,
        GamePosition.move_san.isnot(None),
    )
    .group_by(GamePosition.move_san)
    .order_by(func.count(Game.id.distinct()).desc())
)
```

### result_hash lookup (get full_hash of resulting position)

The resulting position's `full_hash` is not stored on the `game_positions` row for the source position. It must be obtained by joining to the next ply's row:

```python
# Self-join: gp1 is source, gp2 is resulting position (ply+1)
gp1 = aliased(GamePosition, name="gp1")
gp2 = aliased(GamePosition, name="gp2")

stmt = (
    select(
        gp1.move_san,
        gp2.full_hash.label("result_hash"),
        func.count(gp1.game_id.distinct()).label("game_count"),
        # ... win/draw/loss exprs using Game columns
    )
    .join(Game, Game.id == gp1.game_id)
    .join(gp2, (gp2.game_id == gp1.game_id) & (gp2.ply == gp1.ply + 1))
    .where(
        gp1.user_id == user_id,
        gp1.full_hash == target_hash,
        gp1.move_san.isnot(None),
    )
    .group_by(gp1.move_san, gp2.full_hash)
)
```

This self-join gives both `move_san` and `result_hash` from a single query. The covering index `ix_gp_user_full_hash_move_san` already exists on `(user_id, full_hash, move_san)` — the `gp2` join on `(game_id, ply)` benefits from the `game_id` index that exists on `game_positions`.

### result_fen retrieval (batch, one per result_hash)

```python
# Get one (game_id, ply) sample per result_hash using DISTINCT ON
from sqlalchemy.dialects.postgresql import aggregate_order_by

# Simpler: one subquery per result_hash using LIMIT 1 emulated via min(game_id)
stmt = (
    select(
        GamePosition.full_hash.label("result_hash"),
        func.min(GamePosition.game_id).label("sample_game_id"),
        func.min(GamePosition.ply).label("sample_ply"),  # ply for that game_id
    )
    .where(
        GamePosition.user_id == user_id,
        GamePosition.full_hash.in_(result_hashes),
    )
    .group_by(GamePosition.full_hash)
)
# Then: for each (sample_game_id, sample_ply) fetch PGN and replay
```

Note: `func.min(ply)` may not correspond to `func.min(game_id)` — use a DISTINCT ON approach or accept any sample row (any game that reached this position gives the same `board_fen`).

**Simplest correct version:** use a raw-ish query with `DISTINCT ON (full_hash)` via PostgreSQL-specific syntax, or accept one extra query per result_hash (there are <30). For Phase 12 correctness is more important than micro-optimization.

### Transposition count batch query

```python
# Source: analysis_repository.py pattern + SQLAlchemy in_() docs
stmt = (
    select(
        GamePosition.full_hash.label("result_hash"),
        func.count(GamePosition.game_id.distinct()).label("transposition_count"),
    )
    .join(Game, Game.id == GamePosition.game_id)
    .where(
        GamePosition.user_id == user_id,
        GamePosition.full_hash.in_(result_hash_list),
    )
    .group_by(GamePosition.full_hash)
)
# apply same filter clauses as main query
rows = await session.execute(stmt)
return {row.result_hash: row.transposition_count for row in rows}
```

### Schema design

```python
# Source: existing analysis.py schema patterns
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class NextMovesRequest(BaseModel):
    target_hash: int  # required — no None allowed (unlike AnalysisRequest)

    @field_validator("target_hash", mode="before")
    @classmethod
    def coerce_target_hash(cls, v: object) -> object:
        if isinstance(v, str):
            return int(v)
        return v

    # Filters — same as AnalysisRequest minus match_side and pagination
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    recency: Literal["week", "month", "3months", "6months", "year", "all"] | None = None
    color: Literal["white", "black"] | None = None
    sort_by: Literal["frequency", "win_rate"] = "frequency"


class NextMoveEntry(BaseModel):
    move_san: str
    game_count: int
    wins: int
    draws: int
    losses: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    result_hash: str     # BigInt as string for JS safety
    result_fen: str
    transposition_count: int


class NextMovesResponse(BaseModel):
    position_stats: WDLStats
    moves: list[NextMoveEntry]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python-side W/D/L aggregation (loop over rows) | SQL-side `COUNT(DISTINCT CASE WHEN ...)` | Phase 12 (new) | Avoids fetching potentially thousands of rows for per-move stats |
| Per-move transposition queries (N+1) | Batch `IN (...)` query for all result_hashes | Phase 12 (new) | Single round-trip for all transposition counts |

**Existing patterns to preserve:**
- `_build_base_query`: continue reusing its filter application logic
- `DISTINCT ON game_id` deduplication: carried forward in `COUNT(DISTINCT game_id)`
- POST for query endpoints: new endpoint follows this convention
- BigInt string coercion: `target_hash` in `NextMovesRequest` uses same validator pattern

---

## Open Questions

1. **SQLAlchemy `COUNT(DISTINCT CASE ...)` syntax verification**
   - What we know: PostgreSQL natively supports `COUNT(DISTINCT expression)` where expression is a CASE
   - What's unclear: Whether `func.count(case_expr.distinct())` generates the correct SQL in SQLAlchemy 2.x or needs an alternative formulation
   - Recommendation: Test with `str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))` during implementation. Fallback: fetch `(move_san, game_id, result, user_color)` tuples and aggregate W/D/L in Python (acceptable since results are grouped by move_san and there are <30 moves per position).

2. **result_fen retrieval complexity vs. correctness**
   - What we know: FEN must be computed via python-chess; `board_fen()` (not `board.fen()`) is required
   - What's unclear: The cleanest way to get one sample `(game_id, ply)` per `result_hash` in a batch
   - Recommendation: Use `DISTINCT ON (full_hash)` PostgreSQL extension via `select(...).distinct(GamePosition.full_hash).order_by(GamePosition.full_hash, GamePosition.game_id)` — this gives one row per result_hash efficiently. Then batch-fetch PGNs and replay.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode = "auto") |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_analysis_repository.py -x` |
| Full suite command | `uv run pytest -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEXP-04 | next-moves endpoint returns moves with W/D/L per move | integration | `uv run pytest tests/test_analysis_repository.py::TestNextMoves -x` | ❌ Wave 0 |
| MEXP-04 | filters reduce move list correctly | integration | `uv run pytest tests/test_analysis_repository.py::TestNextMovesFilters -x` | ❌ Wave 0 |
| MEXP-05 | game with same move_san at multiple plies counted once per move | integration | `uv run pytest tests/test_analysis_repository.py::TestNextMovesTranspositions -x` | ❌ Wave 0 |
| MEXP-10 | transposition_count >= game_count, equals total distinct games at result position | integration | `uv run pytest tests/test_analysis_repository.py::TestTranspositionCounts -x` | ❌ Wave 0 |
| MEXP-04 | service get_next_moves returns NextMovesResponse with position_stats + moves | integration | `uv run pytest tests/test_analysis_service.py::TestGetNextMoves -x` | ❌ Wave 0 |
| MEXP-04 | sort_by=win_rate reorders moves by win_pct descending | integration | `uv run pytest tests/test_analysis_service.py::TestNextMovesSorting -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_analysis_repository.py -x`
- **Per wave merge:** `uv run pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_analysis_repository.py` — extend with `TestNextMoves`, `TestNextMovesFilters`, `TestNextMovesTranspositions`, `TestTranspositionCounts` classes (no new file needed, extend existing)
- [ ] `tests/test_analysis_service.py` — extend with `TestGetNextMoves`, `TestNextMovesSorting` classes
- [ ] No new framework install needed — pytest-asyncio already configured

---

## Sources

### Primary (HIGH confidence)
- Direct codebase reading: `app/repositories/analysis_repository.py`, `app/services/analysis_service.py`, `app/schemas/analysis.py`, `app/routers/analysis.py`, `app/models/game_position.py`, `app/models/game.py`
- Direct codebase reading: `tests/conftest.py`, `tests/test_analysis_repository.py`, `tests/test_analysis_service.py`
- Direct codebase reading: `pyproject.toml` (pytest config), `.planning/config.json` (nyquist_validation)
- Project CONTEXT.md: All locked decisions are sourced from `12-CONTEXT.md`

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.x `func.count` + `case` pattern: established SQLAlchemy idiom, consistent with existing codebase usage of `func.count`, `func.date_trunc`, `.distinct()`
- PostgreSQL `COUNT(DISTINCT expression)` with CASE: standard PostgreSQL aggregate behavior, widely documented

### Tertiary (LOW confidence)
- `func.count(case_expr.distinct())` exact SQLAlchemy 2.x syntax: inferred from SQLAlchemy patterns, not verified against Context7 — flagged in Open Questions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, verified from codebase
- Architecture: HIGH — patterns directly read from existing repository/service/router/schema files
- SQL query design: MEDIUM — patterns correct for PostgreSQL, one SQLAlchemy syntax detail flagged for verification
- Pitfalls: HIGH — derived from direct code inspection and established project constraints (CLAUDE.md)
- result_fen approach: MEDIUM — python-chess approach is correct, exact batch query formulation needs implementation decision

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable stack, no fast-moving dependencies)

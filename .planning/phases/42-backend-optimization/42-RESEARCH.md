# Phase 42: Backend Optimization - Research

**Researched:** 2026-04-03
**Domain:** SQLAlchemy aggregations, Pydantic v2 response models, FastAPI typing
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Move pure W/D/L counting to SQL using `func.count().filter()` pattern (already established in `stats_repository.py`). Keep conversion/recovery logic in Python — it has complex conditional branching that doesn't belong in SQL.
- **D-02:** For endgame_service loops that mix W/D/L counting with conversion/recovery: split into SQL (W/D/L) + Python (conversion/recovery) where the split is clean. If splitting makes the code awkward, leave the dual-purpose loop intact.
- **D-03:** New aggregation queries stay in their owning repository (openings_repository.py, endgame_repository.py). stats_repository.py remains for cross-cutting stats only.
- **D-04:** Column types already satisfied. All `game_positions` columns already use appropriate types: SmallInteger for counts/flags, Float(24)/REAL for decimals, BigInteger only for 64-bit Zobrist hashes. Verify during planning and close this criterion.
- **D-05:** Create minimal Pydantic response models for the 4 bare-dict endpoints: `GET /users/games/count`, `DELETE /imports/games`, `GET /auth/google/available`, `GET /auth/google/authorize`.
- **D-06:** Also audit existing response models across all endpoints for: field naming consistency (snake_case patterns, abbreviation conventions), missing `response_model=` on route decorators, nested `dict[str, Any]` or untyped fields that should be typed sub-models.

### Claude's Discretion
- Exact Pydantic model names and field structures for the 4 new response schemas
- Which existing response models need changes based on the audit (within D-06 guidelines)
- Whether to split endgame loops or leave them based on code clarity (within D-02 guidelines)
- Test strategy for verifying SQL aggregation produces identical results to Python loops

### Deferred Ideas (OUT OF SCOPE)
- Bitboard storage for partial-position queries — Out of scope; new capability, not optimization of existing queries
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BOPT-01 | Identify and refactor inefficient DB queries (replace row-level processing with aggregations) | Two primary targets identified: `analyze()`/`get_next_moves()` W/D/L loops in openings_service.py (lines 116-124, 384-396); endgame `_build_wdl_summary()` loop (lines 406-432). Pattern: add `query_wdl_counts()` to owning repository using established `func.count().filter()` pattern from stats_repository.py |
| BOPT-02 | Optimize game_positions column types (BIGINT/DOUBLE → SmallInteger/REAL) | Already satisfied per D-04. Confirmed by reading game_position.py and game.py — column types are correct. Requires only verification documentation and closing the criterion. No migration needed. |
| BOPT-03 | Ensure consistent Pydantic response models across all API endpoints — no bare `dict` or untyped returns | 4 bare-dict endpoints found: `GET /users/games/count` → `dict[str, int]`, `DELETE /imports/games` → `dict`, `GET /auth/google/available` → `dict`, `GET /auth/google/authorize` → `dict`. All other router endpoints have typed `response_model=` decorators. |
</phase_requirements>

## Summary

Phase 42 has three work areas. Two are genuine refactoring tasks; one (BOPT-02) is already done and needs only documentation.

**BOPT-01 (SQL aggregation):** Two places in `openings_service.py` fetch (result, user_color) rows from DB and count W/D/L in Python loops (lines 116-124 in `analyze()`, lines 384-396 in `get_next_moves()`). These are both identical patterns that call `query_all_results()` and immediately loop over every row. The fix is to add a `query_wdl_counts()` function to `openings_repository.py` that uses the established `func.count().filter(win_cond)` pattern from `stats_repository.py:84-116`. The endgame `_build_wdl_summary()` function (lines 406-432 in `endgame_service.py`) is also a pure Python W/D/L loop — however, it is only called in `get_endgame_performance()` on rows that have already been fetched for the rolling-window timeline, so SQL aggregation would require a separate query. Per D-02, this should be evaluated for code clarity. The `_aggregate_endgame_stats()` function (lines 145-280) is explicitly out of scope — it mixes W/D/L with conversion/recovery logic and is correctly left in Python per D-01.

**BOPT-02 (column types):** Already satisfied. `game_positions` uses SmallInteger for ply/material_count/material_imbalance/piece_count/mixedness/eval_cp/eval_mate/endgame_class, Float(24)/REAL for clock_seconds, BigInteger only for the three 64-bit Zobrist hashes. `games` uses SmallInteger for acpl/inaccuracies/mistakes/blunders, Float(24) for accuracy. No migration needed. This task is verification + closing the criterion.

**BOPT-03 (response models):** Exactly 4 endpoints return bare dicts: `GET /users/games/count`, `DELETE /imports/games`, `GET /auth/google/available`, `GET /auth/google/authorize`. All other routers already use typed `response_model=` decorators. No existing response models have untyped `dict[str, Any]` fields that need sub-modeling — the existing Pydantic schemas are well-structured. The `google_callback` endpoint returns `RedirectResponse` which is correct and does not need a response model.

**Primary recommendation:** Start with BOPT-02 (1 plan, verify and close), then BOPT-01 (1 plan, add SQL aggregation to openings_repository), then BOPT-03 (1 plan, 4 new Pydantic models + router decorator updates).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.x async | ORM, query construction | Established in project; `select()` API already used |
| Pydantic | v2 | Response model definition, validation | Already used throughout `app/schemas/` |
| FastAPI | 0.115.x | `response_model=` decorator param | Already used in all properly-typed routers |

### Established Patterns
| Pattern | Location | How to Reuse |
|---------|----------|-------------|
| `func.count().filter(win_cond)` | `stats_repository.py:84-116` | Copy `win_cond`, `draw_cond`, `loss_cond` expressions verbatim |
| `or_(and_(...), and_(...))` win/loss condition | `stats_repository.py:84-92` | Standard condition structure for all new aggregation queries |
| `func.count().filter(draw_cond).label("draws")` | `stats_repository.py:98-100` | Label pattern for aggregated columns |
| Pydantic `BaseModel` response | `app/schemas/users.py`, `app/schemas/imports.py` | Add new simple models to existing schema files |

**No new dependencies needed.** All required tools are already in the stack.

## Architecture Patterns

### Pattern 1: SQL W/D/L Aggregation (the established template)
**What:** Replace Python loops over (result, user_color) row fetches with a single SQL aggregation that returns pre-computed counts.
**When to use:** Any query that fetches ALL rows solely to count outcomes — no per-row logic needed.
**Example (from stats_repository.py — HIGH confidence, directly readable in codebase):**
```python
win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)
draw_cond = Game.result == "1/2-1/2"
loss_cond = or_(
    and_(Game.result == "0-1", Game.user_color == "white"),
    and_(Game.result == "1-0", Game.user_color == "black"),
)

stmt = (
    select(
        func.count().label("total"),
        func.count().filter(win_cond).label("wins"),
        func.count().filter(draw_cond).label("draws"),
        func.count().filter(loss_cond).label("losses"),
    )
    .where(Game.user_id == user_id, ...)
    .group_by(...)  # only if grouping; omit for single-row aggregate
)
result = await session.execute(stmt)
row = result.one()  # or .one_or_none()
wins, draws, losses = row.wins, row.draws, row.losses
```

### Pattern 2: Aggregation with DISTINCT game deduplication
**What:** The openings queries use DISTINCT ON game.id to prevent transposition double-counting. When converting to SQL aggregation, the same DISTINCT must apply.
**When to use:** Queries that join game_positions → games where one game may appear at multiple plies.
**Approach:** Build on `_build_base_query()` in openings_repository.py which already handles the DISTINCT ON pattern. A new `query_wdl_counts()` can reuse this by wrapping it as a subquery and aggregating over it:
```python
# Subquery: deduplicated (result, user_color) pairs
dedup_subq = _build_base_query(
    select_entity=[Game.result, Game.user_color],
    ...
).subquery()

# Aggregate over the deduped rows
stmt = select(
    func.count().label("total"),
    func.count().filter(win_cond_on_subq).label("wins"),
    ...
).select_from(dedup_subq)
```

### Pattern 3: Minimal Pydantic Response Model
**What:** Replace `-> dict[str, T]` with a named Pydantic model with explicit fields.
**When to use:** Any endpoint returning a bare dict with a fixed schema.
**Example:**
```python
# In app/schemas/users.py
class GameCountResponse(BaseModel):
    """Response for GET /users/games/count."""
    count: int

# In app/routers/users.py
@router.get("/games/count", response_model=GameCountResponse)
async def get_game_count(...) -> GameCountResponse:
    count = await game_repository.count_games_for_user(session, user.id)
    return GameCountResponse(count=count)
```

### Anti-Patterns to Avoid
- **Pulling all rows to Python when SQL can aggregate:** The exact issue being fixed. `query_all_results()` returns `(result, user_color)` for every game just to count; this scales linearly with game count.
- **Duplicating win_cond/draw_cond/loss_cond:** These conditions must be identical everywhere. Copy from stats_repository.py, do not redefine.
- **Using `-> dict` return type without `response_model=`:** FastAPI uses `response_model=` for serialization/validation; the function return type annotation alone does not enable schema validation or OpenAPI docs.
- **Splitting `_aggregate_endgame_stats()` unnecessarily:** This function combines W/D/L with conversion/recovery in a single pass for a reason — splitting it would require re-iterating the rows. Per D-01/D-02, keep it in Python.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conditional COUNT in SQL | Custom CASE+SUM | `func.count().filter(condition)` | PostgreSQL supports `COUNT(*) FILTER (WHERE ...)` natively; SQLAlchemy exposes it via `.filter()` on `func.count()` |
| DISTINCT + aggregate | Separate dedup + count queries | Subquery wrapping existing `_build_base_query()` output | The DISTINCT ON pattern is already encapsulated; reuse it |

**Key insight:** `func.count().filter()` is a PostgreSQL aggregate filter (SQL standard since 2003, PostgreSQL 9.4+). It is more efficient than `CASE WHEN ... THEN 1 END` sums and more readable than separate subqueries.

## Detailed Target Analysis

### Target 1: openings_service.py `analyze()` — lines 116-124
**Current code:**
```python
all_rows = await query_all_results(...)  # returns list[(result, user_color)]
wins = draws = losses = 0
for result, user_color in all_rows:
    outcome = derive_user_result(result, user_color)
    if outcome == "win": wins += 1
    elif outcome == "draw": draws += 1
    else: losses += 1
```
**Fix:** Add `query_wdl_counts()` to `openings_repository.py` that returns a single `(total, wins, draws, losses)` row. The function must handle both cases: position-filtered (uses `_build_base_query` with target_hash) and all-games (no position filter). The `_build_base_query()` function already handles this via `target_hash is None` logic.

### Target 2: openings_service.py `get_next_moves()` — lines 384-396
**Same pattern as Target 1.** Called with `hash_column=GamePosition.full_hash` and `target_hash=request.target_hash`. Can reuse the same `query_wdl_counts()` function since parameters are identical.

### Target 3: endgame_service.py `_build_wdl_summary()` — lines 406-432
**Current usage:** Called in `get_endgame_performance()` on `endgame_rows` and `non_endgame_rows` which come from `query_endgame_performance_rows()`. Those rows are also used for timeline computation. The rows are fetched anyway for the rolling window — SQL aggregation would need a separate query OR the aggregation could be done in the repository.

**Decision required (per D-02):** If `query_endgame_performance_rows()` adds a parallel `query_endgame_performance_wdl()` function that does the aggregation in SQL, then `_build_wdl_summary()` calls can be replaced. If this makes `get_endgame_performance()` less clear (fetching same data twice), leave `_build_wdl_summary()` intact. This is a planner/implementor judgment call within D-02 guidance.

### BOPT-02 Verification Evidence
From `app/models/game_position.py` (confirmed by reading):
- `ply`: `SmallInteger` — correct (max ~600, fits in 32767)
- `full_hash`, `white_hash`, `black_hash`: `BigInteger` — correct (64-bit Zobrist hashes)
- `clock_seconds`: `Float(24)` = REAL — correct
- `material_count`, `material_imbalance`, `piece_count`, `mixedness`, `eval_cp`, `eval_mate`, `endgame_class`: all `SmallInteger` — correct
- `has_opposite_color_bishops`, `backrank_sparse`: `Boolean` — correct

From `app/models/game.py` (confirmed by reading):
- `white_acpl`, `black_acpl`, `white_inaccuracies`, etc.: `SmallInteger` — correct
- `white_accuracy`, `black_accuracy`: `Float(24)` = REAL — correct
- `time_control_seconds`: bare `int` (no column type specified) → PostgreSQL INTEGER (4 bytes) — appropriate for seconds

**BOPT-02 conclusion:** No migration needed. All types are already optimal.

### BOPT-03 Bare Dict Inventory (complete)
| Endpoint | Current return type | Current response_model | Target |
|----------|--------------------|-----------------------|--------|
| `GET /users/games/count` | `dict[str, int]` | None | `GameCountResponse(count: int)` |
| `DELETE /imports/games` | `dict` | None | `DeleteGamesResponse(deleted_count: int)` |
| `GET /auth/google/available` | `dict` | None | `GoogleOAuthAvailableResponse(available: bool)` |
| `GET /auth/google/authorize` | `dict` | None | `GoogleOAuthAuthorizeResponse(authorization_url: str)` |

**All other endpoints** (`/openings/*`, `/endgames/*`, `/stats/*`, `/position-bookmarks/*`, `/users/me/profile`, `/imports` POST/GET) already have typed `response_model=` decorators. The `google_callback` endpoint returns `RedirectResponse` — this is correct and not a bare dict.

**Schema file placement:**
- `GameCountResponse` → `app/schemas/users.py` (alongside `UserProfileResponse`)
- `DeleteGamesResponse` → `app/schemas/imports.py` (alongside `ImportStartedResponse`)
- `GoogleOAuthAvailableResponse`, `GoogleOAuthAuthorizeResponse` → new `app/schemas/auth.py` (no auth schemas file currently exists)

## Common Pitfalls

### Pitfall 1: DISTINCT ON breaks aggregate queries
**What goes wrong:** When `_build_base_query()` uses `DISTINCT ON (Game.id)`, wrapping it directly in `select(func.count())` will count the DISTINCT-ed rows. But adding aggregate functions to a query with `DISTINCT ON` produces a PostgreSQL error because `DISTINCT ON` and `GROUP BY` have conflicting semantics.
**Why it happens:** SQLAlchemy allows building invalid SQL by composing queries.
**How to avoid:** Always wrap the DISTINCT-based query as a subquery first, then aggregate over the subquery. This is already the pattern used in `query_matching_games()` (count_subq). Follow that exact pattern for `query_wdl_counts()`.
**Warning signs:** PostgreSQL error: `column "game.id" must appear in the GROUP BY clause or be used in an aggregate function`.

### Pitfall 2: win_cond / loss_cond mismatch
**What goes wrong:** Defining local `win_cond` expressions that differ from the established ones in stats_repository.py causes subtly wrong results (e.g., draws counted as losses or vice versa).
**Why it happens:** The conditions are two lines of code that look easy to write from memory but are asymmetric.
**How to avoid:** Copy the exact conditions from `stats_repository.py:84-92` verbatim. Consider extracting to `query_utils.py` as shared constants if used in 3+ places.

### Pitfall 3: ty compliance for new repository return types
**What goes wrong:** New `query_wdl_counts()` functions return `Row[Any]` — this is fine, but the service-layer call site must unpack named attributes, not positional indices, to avoid ty errors.
**Why it happens:** SQLAlchemy `Row` supports both `row[0]` and `row.wins`; ty may flag the index form.
**How to avoid:** Use named labels (`.label("wins")`) and access by attribute name (`row.wins`, `row.draws`, `row.losses`). This is already the pattern in `stats_repository.py`.

### Pitfall 4: Zero-results from aggregate queries
**What goes wrong:** `func.count().label("total")` returns `0` when no rows match, but aggregate queries without `GROUP BY` return exactly one row even when no games exist. `result.one()` works correctly. However, if the query uses `.one_or_none()` expecting `None` for no results, it will get a row with `total=0`.
**Why it happens:** SQL aggregate functions always return a value (0 for COUNT with no matching rows).
**How to avoid:** Use `result.one()` (not `one_or_none()`) for non-grouped aggregates. Guard against zero total before computing percentages (already done in `analyze()`).

### Pitfall 5: Missing `response_model=` still needed alongside typed return
**What goes wrong:** Adding `-> GameCountResponse` return annotation without `response_model=GameCountResponse` in the decorator means FastAPI does not validate or serialize via Pydantic. The OpenAPI schema also won't reflect the model.
**Why it happens:** FastAPI uses `response_model=` from the decorator, not the function return annotation, for serialization.
**How to avoid:** Always add both: `@router.get(..., response_model=Foo)` AND `-> Foo` return annotation.

## Code Examples

### Adding query_wdl_counts to openings_repository.py
```python
# Source: adapted from stats_repository.py:73-116 (established pattern)
async def query_wdl_counts(
    session: AsyncSession,
    user_id: int,
    hash_column: Any | None,
    target_hash: int | None,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
) -> Row[Any]:
    """Return a single (total, wins, draws, losses) aggregate row.

    Uses SQL-side COUNT().FILTER() — no Python-side row iteration needed.
    Wraps _build_base_query() as a subquery to preserve DISTINCT ON deduplication.
    """
    win_cond = or_(
        and_(dedup.c.result == "1-0", dedup.c.user_color == "white"),
        and_(dedup.c.result == "0-1", dedup.c.user_color == "black"),
    )
    draw_cond = dedup.c.result == "1/2-1/2"
    loss_cond = or_(
        and_(dedup.c.result == "0-1", dedup.c.user_color == "white"),
        and_(dedup.c.result == "1-0", dedup.c.user_color == "black"),
    )

    dedup = _build_base_query(
        select_entity=[Game.result, Game.user_color],
        user_id=user_id,
        hash_column=hash_column,
        target_hash=target_hash,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=recency_cutoff,
        color=color,
    ).subquery()

    stmt = select(
        func.count().label("total"),
        func.count().filter(win_cond).label("wins"),
        func.count().filter(draw_cond).label("draws"),
        func.count().filter(loss_cond).label("losses"),
    ).select_from(dedup)

    result = await session.execute(stmt)
    return result.one()
```

### New Pydantic models for BOPT-03

In `app/schemas/users.py`:
```python
class GameCountResponse(BaseModel):
    """Response for GET /users/games/count."""
    count: int
```

In `app/schemas/imports.py`:
```python
class DeleteGamesResponse(BaseModel):
    """Response for DELETE /imports/games."""
    deleted_count: int
```

New `app/schemas/auth.py`:
```python
"""Pydantic v2 schemas for auth API endpoints."""
from pydantic import BaseModel

class GoogleOAuthAvailableResponse(BaseModel):
    """Response for GET /auth/google/available."""
    available: bool

class GoogleOAuthAuthorizeResponse(BaseModel):
    """Response for GET /auth/google/authorize."""
    authorization_url: str
```

### Router update pattern
```python
# Before (users.py)
@router.get("/games/count")
async def get_game_count(...) -> dict[str, int]:
    count = await game_repository.count_games_for_user(session, user.id)
    return {"count": count}

# After
@router.get("/games/count", response_model=GameCountResponse)
async def get_game_count(...) -> GameCountResponse:
    count = await game_repository.count_games_for_user(session, user.id)
    return GameCountResponse(count=count)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Fetch all rows, count in Python | `COUNT(*) FILTER (WHERE ...)` in SQL | O(n) Python → O(1) data transfer for WDL stats |
| `-> dict` return type | Pydantic `BaseModel` response | OpenAPI schema, runtime validation, IDE completion |
| Bare `dict` without `response_model=` | `response_model=` decorator param | FastAPI validates and serializes; OpenAPI reflects schema |

**Note:** `func.count().filter()` maps to PostgreSQL's `COUNT(*) FILTER (WHERE condition)` syntax, available since PostgreSQL 9.4 (2014). The project uses PostgreSQL 18 — no compatibility concerns.

## Open Questions

1. **Should `_build_wdl_summary()` be SQL-aggregated or left in Python?**
   - What we know: It is called in `get_endgame_performance()` on rows that are also used for rolling timelines. A SQL version would require a separate query per group (endgame/non-endgame).
   - What's unclear: Whether the separate query is worth it given the rows are already in memory.
   - Recommendation: Leave `_build_wdl_summary()` in Python per D-02. The rows are fetched anyway; a second SQL round-trip adds latency without reducing data transfer. Document this decision explicitly in the plan.

2. **Should `win_cond`/`draw_cond`/`loss_cond` be extracted to `query_utils.py`?**
   - What we know: They are currently defined identically in `stats_repository.py` (3 uses) and `openings_repository.py` (already in `query_next_moves()`). Adding to `openings_repository.py` makes 2 uses there.
   - Recommendation: Extract to module-level constants in each repository file, or to `query_utils.py` if they will be used in 3+ repositories. This is a planner judgment call.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified — this phase is pure code/config changes).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/test_openings_service.py tests/test_openings_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BOPT-01 | SQL `query_wdl_counts()` produces identical W/D/L as Python loop for position-filtered and all-games cases | integration | `uv run pytest tests/test_openings_repository.py -x` | ✅ |
| BOPT-01 | `analyze()` uses SQL aggregation, service layer no longer contains W/D/L loop | unit | `uv run pytest tests/test_openings_service.py -x` | ✅ |
| BOPT-02 | Column type verification (documented, no runtime test) | manual | n/a | n/a |
| BOPT-03 | `GET /users/games/count` returns `{"count": N}` with correct status | integration | `uv run pytest tests/test_users_router.py -x` | ✅ |
| BOPT-03 | `DELETE /imports/games` returns `{"deleted_count": N}` | integration | `uv run pytest tests/test_imports_router.py -x` | ✅ |
| BOPT-03 | Auth endpoints return typed responses (smoke test via OpenAPI) | unit | `uv run pytest tests/test_auth.py -x` | ✅ |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_openings_service.py tests/test_openings_repository.py tests/test_users_router.py tests/test_imports_router.py tests/test_auth.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. New test cases should be added to existing test files rather than creating new ones.

## Sources

### Primary (HIGH confidence)
- Direct file reads: `app/services/openings_service.py`, `app/services/endgame_service.py`, `app/repositories/stats_repository.py`, `app/repositories/openings_repository.py`, `app/repositories/endgame_repository.py`
- Direct file reads: `app/routers/users.py`, `app/routers/imports.py`, `app/routers/auth.py`, all other routers
- Direct file reads: `app/models/game_position.py`, `app/models/game.py`
- Direct file reads: All `app/schemas/` files
- `app/schemas/` directory listing: confirmed no `auth.py` exists

### Secondary (MEDIUM confidence)
- n/a — all findings are from direct code inspection, no external research needed

### Tertiary (LOW confidence)
- n/a

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; verified by reading codebase
- Architecture: HIGH — established patterns confirmed from stats_repository.py; target locations confirmed from openings_service.py and endgame_service.py
- Pitfalls: HIGH — derived from direct code analysis (DISTINCT ON pattern in query_matching_games, aggregate query semantics)

**Research date:** 2026-04-03
**Valid until:** 2026-07-03 (stable codebase, no fast-moving dependencies)

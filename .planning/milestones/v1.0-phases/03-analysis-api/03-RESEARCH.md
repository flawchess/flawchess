# Phase 3: Analysis API - Research

**Researched:** 2026-03-11
**Domain:** FastAPI query endpoints with SQLAlchemy 2.x async, multi-filter JOIN queries, Pydantic v2 response schemas
**Confidence:** HIGH

## Summary

Phase 3 builds the read-side contract for the analysis feature: a single POST endpoint that accepts a Zobrist hash + match_side + optional filters and returns W/D/L aggregate stats plus a paginated game list. The entire infrastructure already exists — composite indexes are in place, all filter columns are on the `Game` model, and the `game_positions` table has the denormalized `user_id` needed to avoid joins on the hot path. This phase is pure application code (no migrations, no new models) following patterns already established in Phase 1 and Phase 2.

The core query pattern is: SELECT DISTINCT game_ids from `game_positions` matching the target hash (with deduplication if the same position appears at multiple plies), then JOIN to `games` for metadata and WHERE clauses for each optional filter. W/D/L aggregation and game-list projection are both derived from the same joined result set.

The main design decision delegated to Claude's discretion is endpoint shape (POST vs GET, unified vs split), pagination approach, and response schema structure. Based on the codebase, existing patterns, and the nature of the query, recommendations are documented below with rationale.

**Primary recommendation:** Single POST `/analysis/positions` endpoint returning W/D/L summary and paginated game list in one response; SQLAlchemy 2.x `select().distinct()` with dynamic `where()` clause building for filters; offset/limit pagination defaulting to 50 results.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
No decisions are locked by the user — all Phase 3 decisions were delegated to Claude's discretion.

### Claude's Discretion

**Endpoint design:**
- POST vs GET for analysis queries (consider query complexity and idempotency)
- Single unified endpoint vs separate endpoints for stats and game list
- Request schema: how target position hash, match_side (white/black/full), and optional filters are sent
- Hardcoded user_id=1 placeholder (same as import endpoints — real auth in Phase 4)

**Response shape:**
- W/D/L counts and percentages structure
- Game list structure: opponent name, result, date, time control, platform URL per game (RES-01, RES-02)
- Total games denominator — "X of Y games matched" (RES-03)
- Pagination approach for game lists (offset/limit, cursor, or return all)

**Query behavior:**
- match_side semantics: white_hash for "my white pieces only", black_hash for "my black pieces only", full_hash for "both sides" (ANL-02)
- Color filter (FLT-04) interaction with match_side — filter on Game.user_color
- Deduplication: a game should count once even if the target position appears at multiple plies
- Result interpretation: Game.result is white's perspective ("1-0"), Game.user_color determines the user's outcome (win/draw/loss)

**Filter implementation:**
- Time control filter using pre-computed Game.time_control_bucket column (FLT-01)
- Rated filter on Game.rated boolean (FLT-02)
- Recency filter on Game.played_at with predefined cutoffs: week, month, 3 months, 6 months, 1 year, all time (FLT-03)
- Color filter on Game.user_color (FLT-04)
- All filters optional — omitted means "no filter" (include all)

**Architecture:**
- Follow existing routers/services/repositories layering
- analysis_repository.py for DB queries (joins game_positions to games with filters)
- analysis_service.py for orchestration and result building
- analysis router registered in app/main.py
- Pydantic v2 schemas for request/response validation

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANL-02 | User can filter position matches by white pieces only, black pieces only, or both sides | `match_side` param maps to `white_hash`, `black_hash`, or `full_hash` column; all three are indexed with composite `(user_id, hash)` indexes |
| ANL-03 | User sees win/draw/loss counts and percentages for all matching games | Derived in Python from `Game.result` + `Game.user_color`; no DB aggregation needed at this scale |
| FLT-01 | User can filter analysis results by time control (bullet, blitz, rapid, classical) | `Game.time_control_bucket` column already pre-computed and stored; simple `WHERE IN (...)` |
| FLT-02 | User can filter analysis results by rated vs casual games | `Game.rated` boolean column; `WHERE rated = true/false` |
| FLT-03 | User can filter analysis results by game recency (week, month, 3 months, 6 months, 1 year, all time) | `Game.played_at` datetime column; `WHERE played_at >= cutoff` for non-"all time" values |
| FLT-04 | User can filter analysis results by color played (white or black) | `Game.user_color` column; `WHERE user_color = 'white'/'black'` |
| RES-01 | User sees a list of matching games showing opponent name, result, date, and time control | `Game.opponent_username`, `Game.result`, `Game.user_color`, `Game.played_at`, `Game.time_control_bucket` — all on the `games` table |
| RES-02 | Each matching game has a clickable link to the game on chess.com or lichess | `Game.platform_url` column already stored at import time |
| RES-03 | User always sees the total games denominator ("X of Y games matched") | Response includes both `matched_count` (after filters) and pagination metadata |
</phase_requirements>

---

## Standard Stack

### Core (no new dependencies needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x | Router, dependency injection, response models | Already in use |
| SQLAlchemy async | 2.x | `select().join().where()` query building | Already in use |
| asyncpg | 0.29.x | PostgreSQL async driver | Already in use |
| Pydantic v2 | 2.x | Request/response schema validation | Already in use |

No new packages. Phase 3 is pure application logic on top of the existing stack.

**Installation:** None required.

## Architecture Patterns

### Recommended Project Structure (new files only)
```
app/
├── routers/
│   └── analysis.py        # POST /analysis/positions — HTTP layer only
├── schemas/
│   └── analysis.py        # AnalysisRequest, AnalysisResponse, GameRecord
├── services/
│   └── analysis_service.py  # Orchestration: calls repo, builds W/D/L summary
└── repositories/
    └── analysis_repository.py  # DB query: distinct game_ids -> join games with filters
```

Register in `app/main.py`:
```python
from app.routers import analysis
app.include_router(analysis.router)
```

### Pattern 1: Endpoint — POST over GET for complex query parameters

**What:** Use `POST /analysis/positions` with a JSON body rather than `GET` with query params.

**Why POST here:** The request body includes a 64-bit integer hash (`target_hash`), a list of time control values (`["bullet", "blitz"]`), and structured filters. While GET is technically correct for reads, passing large structured filter objects as query params is awkward and fragile. The existing import router uses POST for operation-style requests. The analysis endpoint is functionally equivalent to a "search" operation — POST is conventional for search endpoints with complex bodies.

**Why not GET:** Query string encoding of arrays (`?time_control=bullet&time_control=blitz`) requires client-side encoding awareness. A JSON body is unambiguous and matches Phase 2 patterns.

**Request schema:**
```python
class AnalysisRequest(BaseModel):
    target_hash: int  # Zobrist hash — client computes from board position
    match_side: Literal["white", "black", "full"] = "full"
    # Optional filters — None means "no filter" (include all)
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    rated: bool | None = None
    recency: Literal["week", "month", "3months", "6months", "year", "all"] | None = None
    color: Literal["white", "black"] | None = None
    # Pagination
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)
```

### Pattern 2: Single unified endpoint

**What:** One endpoint returns both the W/D/L summary AND the game list.

**Why unified:** The frontend always needs both: the chart and the list come from the same position query. Splitting into two endpoints forces the client to make two requests with identical filter parameters, duplicating state and network round trips. The service layer computes both from the same query result.

**Response schema:**
```python
class WDLStats(BaseModel):
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float

class GameRecord(BaseModel):
    game_id: int
    opponent_username: str | None
    user_result: Literal["win", "draw", "loss"]  # derived from result + user_color
    played_at: datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None

class AnalysisResponse(BaseModel):
    stats: WDLStats
    games: list[GameRecord]
    matched_count: int   # total matching games (before pagination)
    offset: int
    limit: int
```

### Pattern 3: Repository — DISTINCT subquery + JOIN with dynamic filters

**What:** Use SQLAlchemy 2.x `select(Game).join(GamePosition).where(...)` with `.distinct(Game.id)` to deduplicate games that appear at multiple plies.

**Why DISTINCT on game_id:** A game reaching the target position at ply 4, ply 6, AND ply 8 (transposition) would otherwise appear 3 times in results. DISTINCT ensures each game is counted once in the W/D/L total.

**Dynamic filter building pattern** (matches existing `import_job_repository.py` style):
```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import datetime

async def query_matching_games(
    session: AsyncSession,
    user_id: int,
    hash_column,          # GamePosition.white_hash / black_hash / full_hash
    target_hash: int,
    time_control: list[str] | None,
    rated: bool | None,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Game], int]:
    base = (
        select(Game)
        .join(GamePosition, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            hash_column == target_hash,
        )
        .distinct()
    )
    if time_control is not None:
        base = base.where(Game.time_control_bucket.in_(time_control))
    if rated is not None:
        base = base.where(Game.rated == rated)
    if recency_cutoff is not None:
        base = base.where(Game.played_at >= recency_cutoff)
    if color is not None:
        base = base.where(Game.user_color == color)

    # Count query (same filters, no pagination)
    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Paginated results
    rows = await session.execute(
        base.order_by(Game.played_at.desc()).offset(offset).limit(limit)
    )
    return rows.scalars().all(), total
```

### Pattern 4: Service — W/D/L derivation from result + user_color

**What:** Convert `Game.result` ("1-0"/"0-1"/"1/2-1/2") and `Game.user_color` ("white"/"black") to user-perspective outcome.

**Logic:**
```python
def derive_user_result(result: str, user_color: str) -> Literal["win", "draw", "loss"]:
    if result == "1/2-1/2":
        return "draw"
    if (result == "1-0" and user_color == "white") or \
       (result == "0-1" and user_color == "black"):
        return "win"
    return "loss"
```

This runs in Python over the result set — no DB-level aggregation function needed.

### Pattern 5: match_side to hash column mapping

**What:** Map the `match_side` request field to the correct `GamePosition` column.

```python
HASH_COLUMN_MAP = {
    "white": GamePosition.white_hash,
    "black": GamePosition.black_hash,
    "full": GamePosition.full_hash,
}
hash_col = HASH_COLUMN_MAP[request.match_side]
```

### Pattern 6: Recency cutoff computation

**What:** Convert the `recency` string to a `datetime.datetime` cutoff for the `WHERE played_at >=` clause.

```python
import datetime

RECENCY_DELTAS = {
    "week":    datetime.timedelta(weeks=1),
    "month":   datetime.timedelta(days=30),
    "3months": datetime.timedelta(days=90),
    "6months": datetime.timedelta(days=180),
    "year":    datetime.timedelta(days=365),
}

def recency_cutoff(recency: str | None) -> datetime.datetime | None:
    if recency is None or recency == "all":
        return None
    return datetime.datetime.now(tz=datetime.timezone.utc) - RECENCY_DELTAS[recency]
```

### Anti-Patterns to Avoid

- **Raw SQL strings in services:** Keep SQL in `analysis_repository.py`. Service calls repo functions only.
- **Aggregating in Python over unfiltered rows:** Don't load all matching positions into memory to count W/D/L. Use the COUNT subquery in the repository.
- **Using `board.fen()` for hash lookup:** The hash was computed from `board.board_fen()` at import. The client must pass the same hash. Do not re-derive it in the API (the API is hash-in, stats-out).
- **Exposing internal hash values in responses:** API contract returns FEN-based display data only — hashes are request inputs, never output fields.
- **Forgetting DISTINCT:** Without `.distinct()`, a transposing game (same position reached via different move orders) counts multiple times in W/D/L totals.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async DB queries | Custom connection pool | `get_async_session` Depends() pattern | Already solved in `app/core/database.py` |
| Request validation | Manual type-checking | Pydantic v2 `BaseModel` with `Literal` | Zero-effort, consistent with all other schemas |
| Dynamic WHERE clauses | String concatenation | SQLAlchemy 2.x `.where()` chaining on `Select` objects | Type-safe, injection-proof, composable |
| Pagination | Custom cursor logic | Offset/limit with `.offset().limit()` | Sufficient for this data volume; cursor adds complexity with no benefit at this stage |
| Result counting | Python `len()` after loading all rows | `func.count()` subquery in repository | Avoids loading unbounded result sets |

**Key insight:** The composite indexes `(user_id, white_hash)`, `(user_id, black_hash)`, `(user_id, full_hash)` were explicitly created in Phase 1 for this query. The query plan is already optimal — no additional tuning needed.

## Common Pitfalls

### Pitfall 1: Double-counting transpositions
**What goes wrong:** A game where the target position appears at ply 4 AND ply 12 (via transposition) appears twice in W/D/L counts and twice in the game list.
**Why it happens:** The `game_positions` table has one row per ply. A JOIN without DISTINCT returns one row per matching ply, not per game.
**How to avoid:** Use `.distinct()` on the `Game.id` column in the SELECT (shown in Pattern 3). Verify with a test that seeds a single game with the same hash at multiple plies.
**Warning signs:** W/D/L total exceeds total game count; game appears multiple times in the list.

### Pitfall 2: match_side vs color filter interaction
**What goes wrong:** Confusing `match_side` (which hash column to use — determines WHAT position is compared) with `color` filter (which games to include based on which side the user played).
**Why it happens:** Both deal with "side," but they are independent dimensions. A user could query "where did my white pieces form this pattern" (`match_side=white`) in ALL games they played as black (`color=black`) — that's valid if they want to see how opponents reached a position.
**How to avoid:** Apply `match_side` to the hash column selection (determines JOIN condition). Apply `color` as a `WHERE Game.user_color = ...` filter independently. Document the semantic separation in the service function signature.
**Warning signs:** Zero results when both filters are applied together, even though games matching individually exist.

### Pitfall 3: Pagination count mismatch
**What goes wrong:** `matched_count` in the response does not match the actual number of games if the count query uses different filters from the paginated query.
**Why it happens:** Two separate query paths diverge when filters are added.
**How to avoid:** Build the base query once (with all filters) and derive both the count query and the paginated query from the same `base` Select object (shown in Pattern 3).
**Warning signs:** `matched_count` is constant regardless of filter changes; or `matched_count` < `offset + len(games)`.

### Pitfall 4: Percentages when total is zero
**What goes wrong:** Division by zero when `WDLStats.total == 0`.
**Why it happens:** No games matched the query — valid state.
**How to avoid:** Guard in the service: `win_pct = wins / total * 100 if total > 0 else 0.0`.
**Warning signs:** HTTP 500 with `ZeroDivisionError` when querying a rare or unplayed position.

### Pitfall 5: NULL played_at in recency filter
**What goes wrong:** Games with `played_at = NULL` are excluded by `WHERE played_at >= cutoff` even when they should arguably match (or the count is wrong).
**Why it happens:** SQL NULL comparisons: `NULL >= cutoff` is NULL (not TRUE), so NULLs silently drop out.
**How to avoid:** Document the decision: NULLs are excluded when a recency filter is applied (this is correct behavior — we can't date-filter undated games). No special handling needed, just ensure tests cover this expectation.
**Warning signs:** `matched_count` changes unexpectedly when switching from "all" to a recency filter by more than expected.

## Code Examples

### Full repository function skeleton
```python
# app/repositories/analysis_repository.py
# Source: SQLAlchemy 2.x async docs + existing game_repository.py pattern

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import datetime

from app.models.game import Game
from app.models.game_position import GamePosition


async def query_matching_games(
    session: AsyncSession,
    user_id: int,
    hash_column,
    target_hash: int,
    time_control: list[str] | None,
    rated: bool | None,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Game], int]:
    base = (
        select(Game)
        .join(GamePosition, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            hash_column == target_hash,
        )
        .distinct()
    )
    if time_control is not None:
        base = base.where(Game.time_control_bucket.in_(time_control))
    if rated is not None:
        base = base.where(Game.rated == rated)
    if recency_cutoff is not None:
        base = base.where(Game.played_at >= recency_cutoff)
    if color is not None:
        base = base.where(Game.user_color == color)

    count_q = select(func.count()).select_from(base.subquery())
    total: int = (await session.execute(count_q)).scalar_one()

    result = await session.execute(
        base.order_by(Game.played_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total
```

### Service W/D/L computation
```python
# app/services/analysis_service.py

def derive_user_result(result: str, user_color: str) -> str:
    if result == "1/2-1/2":
        return "draw"
    if (result == "1-0" and user_color == "white") or \
       (result == "0-1" and user_color == "black"):
        return "win"
    return "loss"

def build_wdl(games: list[Game]) -> dict:
    wins = sum(1 for g in games if derive_user_result(g.result, g.user_color) == "win")
    draws = sum(1 for g in games if derive_user_result(g.result, g.user_color) == "draw")
    losses = len(games) - wins - draws
    total = len(games)
    return {
        "wins": wins, "draws": draws, "losses": losses, "total": total,
        "win_pct": round(wins / total * 100, 1) if total else 0.0,
        "draw_pct": round(draws / total * 100, 1) if total else 0.0,
        "loss_pct": round(losses / total * 100, 1) if total else 0.0,
    }
```

**Note:** W/D/L stats are computed over the paginated result set when `matched_count` is returned. The `stats` block should reflect ALL matching games (not just the current page). This means the service must run two queries or compute stats over all matching game_ids separately. Simplest approach: run the count + paginated query for the list, and run a separate aggregation query for stats over all matched games. Document this in the service.

Actually the cleaner approach: load ALL matching game IDs + result + user_color for the stats query (lightweight — only two text columns), and load the full paginated Game objects for the list. Two queries, both using the same base filter. This avoids loading full Game objects for potentially thousands of rows.

### Router pattern (mirrors imports.py)
```python
# app/routers/analysis.py

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/positions", response_model=AnalysisResponse)
async def analyze_position(
    request: AnalysisRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AnalysisResponse:
    # TODO(phase-4): Replace hardcoded user_id=1 with real auth
    user_id = 1
    return await analysis_service.analyze(session, user_id, request)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x `session.query(Model)` | SQLAlchemy 2.x `select(Model)` | SQLAlchemy 2.0 (2023) | Fully async-compatible; already used in this codebase |
| Pydantic v1 `validator` | Pydantic v2 `field_validator` / `model_validator` | Pydantic v2 (2023) | Already used; `@field_validator` replaces `@validator` |
| `asyncio_mode = "auto"` missing | `asyncio_mode = "auto"` in pytest config | pytest-asyncio 0.21 | Already set in `pyproject.toml` — no async fixture wrappers needed |

**Deprecated/outdated:**
- `session.query(Model)` (SQLAlchemy 1.x legacy): Already excluded by this codebase — do not use.
- `requests` library: Already excluded by CLAUDE.md — all HTTP is `httpx.AsyncClient`.

## Open Questions

1. **Stats over all matches vs paginated slice**
   - What we know: The client needs W/D/L across ALL matching games, but the game list is paginated.
   - What's unclear: Whether to run one query + aggregate in Python vs two queries.
   - Recommendation: Two queries — one lightweight SELECT (game_id, result, user_color) for stats, one full SELECT with pagination for the list. Avoids loading full Game ORM objects for stats.

2. **Percentage rounding**
   - What we know: Floating-point percentages displayed to client.
   - What's unclear: One decimal (e.g., 33.3%) vs two (33.33%) vs integer.
   - Recommendation: One decimal (`round(x, 1)`). Consistent with chess platform conventions.

3. **Empty result behavior**
   - What we know: Must return total denominator even for zero matches (RES-03).
   - Recommendation: Return `stats` with all zeros, empty `games` list, `matched_count=0`. Do not return 404.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` |
| Quick run command | `uv run pytest tests/test_analysis_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANL-02 | `match_side=white` uses `white_hash` column; `black` uses `black_hash`; `full` uses `full_hash` | unit | `uv run pytest tests/test_analysis_repository.py::TestMatchSide -x` | Wave 0 |
| ANL-03 | W/D/L counts and percentages correct for known game set | unit | `uv run pytest tests/test_analysis_service.py::TestWDLStats -x` | Wave 0 |
| FLT-01 | Time control filter excludes games with non-matching bucket | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_time_control_filter -x` | Wave 0 |
| FLT-02 | Rated filter includes only rated=True or rated=False games | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_rated_filter -x` | Wave 0 |
| FLT-03 | Recency filter excludes games before cutoff; "all" applies no filter | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_recency_filter -x` | Wave 0 |
| FLT-04 | Color filter on `user_color` | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_color_filter -x` | Wave 0 |
| RES-01 | Game list includes opponent, result, date, time control | unit | `uv run pytest tests/test_analysis_service.py::TestGameRecord -x` | Wave 0 |
| RES-02 | `platform_url` present on each game record | unit | `uv run pytest tests/test_analysis_service.py::TestGameRecord::test_platform_url -x` | Wave 0 |
| RES-03 | `matched_count` equals total games matching filters (not just page size) | unit | `uv run pytest tests/test_analysis_service.py::TestPagination -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_analysis_repository.py tests/test_analysis_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_analysis_repository.py` — covers ANL-02, FLT-01 through FLT-04, deduplication/transposition
- [ ] `tests/test_analysis_service.py` — covers ANL-03, RES-01, RES-02, RES-03, zero-result edge case
- [ ] No new framework install needed — pytest + pytest-asyncio + `db_session` fixture already configured

## Sources

### Primary (HIGH confidence)
- Existing `app/models/game.py` — Game model columns confirmed by direct inspection
- Existing `app/models/game_position.py` — GamePosition model + composite indexes confirmed
- Existing `app/repositories/import_job_repository.py` — SQLAlchemy 2.x `select().where()` chaining pattern
- Existing `app/schemas/imports.py` — Pydantic v2 `BaseModel`/`Field`/`Literal` pattern
- Existing `app/routers/imports.py` — Router structure, `Depends(get_async_session)`, `user_id=1` placeholder
- Existing `tests/conftest.py` — `db_session` fixture (transaction rollback pattern)
- `pyproject.toml` — `asyncio_mode = "auto"`, confirmed pytest-asyncio in dev deps

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.x `select().distinct()` documented behavior: standard ORM query API, consistent with project use of `select()` throughout
- `func.count().select_from(subquery())` pattern for counting distinct records: standard SQLAlchemy aggregation pattern

### Tertiary (LOW confidence)
- None — all findings are derived from the project's own code or well-established SQLAlchemy patterns already in use.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; everything already in use
- Architecture: HIGH — directly derived from Phase 1/2 patterns in the codebase
- Query patterns: HIGH — SQLAlchemy 2.x `select()` + dynamic `.where()` chaining is the existing project pattern
- Pitfalls: HIGH — transposition deduplication and NULL played_at are verified edge cases specific to this data model

**Research date:** 2026-03-11
**Valid until:** 2026-06-11 (stable stack; no fast-moving dependencies)

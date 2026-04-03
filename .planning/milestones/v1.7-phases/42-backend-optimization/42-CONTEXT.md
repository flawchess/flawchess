# Phase 42: Backend Optimization - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize backend DB queries by replacing Python-side W/D/L counting loops with SQL aggregations, and ensure all API endpoints return typed Pydantic response models. Column type optimization (SC-2) is already satisfied — no BIGINT/DOUBLE misuse exists in the current schema.

Note: DB queries already perform well in production. This phase is about code quality (pushing logic to the right layer) and API schema consistency, not fixing performance issues.

</domain>

<decisions>
## Implementation Decisions

### SQL Aggregation Scope
- **D-01:** Move pure W/D/L counting to SQL using `func.count().filter()` pattern (already established in `stats_repository.py`). Keep conversion/recovery logic in Python — it has complex conditional branching that doesn't belong in SQL.
- **D-02:** For endgame_service loops that mix W/D/L counting with conversion/recovery: split into SQL (W/D/L) + Python (conversion/recovery) where the split is clean. If splitting makes the code awkward, leave the dual-purpose loop intact.
- **D-03:** New aggregation queries stay in their owning repository (openings_repository.py, endgame_repository.py). stats_repository.py remains for cross-cutting stats only.

### Column Type Migration (SC-2)
- **D-04:** Already satisfied. All `game_positions` columns already use appropriate types: SmallInteger for counts/flags, Float(24)/REAL for decimals, BigInteger only for 64-bit Zobrist hashes. Verify during planning and close this criterion.

### Response Model Scope
- **D-05:** Create minimal Pydantic response models for the 4 bare-dict endpoints: `GET /users/games/count`, `DELETE /imports/games`, `GET /auth/google/available`, `GET /auth/google/authorize`.
- **D-06:** Also audit existing response models across all endpoints for:
  - Field naming consistency (snake_case patterns, abbreviation conventions)
  - Missing `response_model=` on route decorators (some may have typed returns but no explicit decorator param)
  - Nested `dict[str, Any]` or untyped fields that should be typed sub-models

### Claude's Discretion
- Exact Pydantic model names and field structures for the 4 new response schemas
- Which existing response models need changes based on the audit (within D-06 guidelines)
- Whether to split endgame loops or leave them based on code clarity (within D-02 guidelines)
- Test strategy for verifying SQL aggregation produces identical results to Python loops

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### SQL aggregation (primary targets)
- `app/services/openings_service.py` — `analyze()` function with Python-side W/D/L counting loop (~line 116-124)
- `app/services/endgame_service.py` — W/D/L + conversion/recovery loops (~line 176-204, ~line 406-432 `_build_wdl_summary()`)
- `app/repositories/stats_repository.py` — Reference pattern for `func.count().filter()` SQL aggregation (~line 84-116)
- `app/repositories/openings_repository.py` — `query_all_results()` returns raw tuples; target for aggregation query
- `app/repositories/endgame_repository.py` — Endgame query functions returning raw rows

### Response models (targets)
- `app/routers/users.py` — `GET /games/count` bare dict return (~line 61)
- `app/routers/imports.py` — `DELETE /games` bare dict return (~line 162)
- `app/routers/auth.py` — `GET /auth/google/available` and `GET /auth/google/authorize` bare dict returns (~line 50, ~line 59)
- `app/schemas/` — All existing Pydantic response models (audit targets)

### Column types (verification only)
- `app/models/game_position.py` — Column type definitions (verify already optimized)
- `app/models/game.py` — Game model column types

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `stats_repository.py` lines 84-116: Established `func.count().filter(win_cond)` pattern with `win_cond`, `draw_cond`, `loss_cond` conditions
- `app/schemas/` directory: Well-structured Pydantic v2 response models across openings, endgames, stats, position_bookmarks
- `app/repositories/query_utils.py`: Shared `apply_game_filters()` for consistent filtering

### Established Patterns
- Repository layer: SQLAlchemy 2.x async `select()` API with typed models
- Services: Pydantic schemas for API responses via `app/schemas/`
- All routers use `APIRouter(prefix="/resource")` with relative paths
- Phase 40 conventions: Pydantic at system boundaries, TypedDicts for internal structures

### Integration Points
- Repository functions: New aggregation queries replace raw-tuple queries
- Service functions: Simplified logic after SQL handles counting
- Router decorators: Add `response_model=` parameter to 4 endpoints
- Schema files: New response model classes for auth, users, imports

</code_context>

<specifics>
## Specific Ideas

- DB queries already perform well in production — this is a code quality improvement, not a performance fix
- The `func.count().filter()` pattern in stats_repository.py is the template for all new aggregation queries
- Column types are already optimized — SC-2 should be verified and closed early in planning

</specifics>

<deferred>
## Deferred Ideas

- **Bitboard storage for partial-position queries** — Pending todo (database area) matched this phase but is about adding new columns, not optimizing existing ones. Remains a v2+ idea.

### Reviewed Todos (not folded)
- **Bitboard storage for partial-position queries** — Out of scope; new capability, not optimization of existing queries

</deferred>

---

*Phase: 42-backend-optimization*
*Context gathered: 2026-04-03*

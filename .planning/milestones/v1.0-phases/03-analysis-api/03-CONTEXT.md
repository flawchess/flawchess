# Phase 3: Analysis API - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Define and implement the backend analysis contract: API endpoints for querying win/draw/loss rates and matching game lists by position hash, with filtering by time control, rated/casual, recency, and color played. No frontend, no auth changes — just the API layer that any client can call.

Requirements: ANL-02, ANL-03, FLT-01, FLT-02, FLT-03, FLT-04, RES-01, RES-02, RES-03

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User delegated all Phase 3 decisions to Claude, consistent with Phase 1 and Phase 2. The following areas should be resolved during research and planning based on project requirements, existing codebase patterns, and best practices:

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

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User trusts Claude's technical judgment for this backend API phase, consistent with Phase 1 and Phase 2.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/models/game.py`: Game model with all filter columns (time_control_bucket, rated, played_at, user_color, result, opponent_username, platform, platform_game_id)
- `app/models/game_position.py`: GamePosition model with composite indexes on (user_id, full_hash), (user_id, white_hash), (user_id, black_hash)
- `app/repositories/import_job_repository.py`: SQLAlchemy 2.x async select()/where() query pattern to follow
- `app/schemas/imports.py`: Pydantic v2 schema pattern (BaseModel, Field, Literal)
- `app/core/database.py`: get_async_session dependency for router injection

### Established Patterns
- routers/services/repositories layering — no SQL in routers, no business logic in repositories
- SQLAlchemy 2.x async with select() API
- Pydantic v2 for all validation
- Depends(get_async_session) for session injection in routers

### Integration Points
- Register analysis router in app/main.py (alongside imports router)
- Query game_positions table using denormalized user_id + hash columns (composite indexes)
- Join to games table for metadata and filter columns
- Game.result stored as "1-0"/"0-1"/"1/2-1/2" — user outcome derived from user_color
- Platform URL already stored on Game model for RES-02

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-analysis-api*
*Context gathered: 2026-03-11*

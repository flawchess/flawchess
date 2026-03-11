# Phase 2: Import Pipeline - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Fetch user game histories from chess.com and lichess as background tasks, with incremental re-sync and visible progress. No frontend, no auth — just API endpoints and background workers. Consumes the schema and Zobrist module from Phase 1.

Requirements: IMP-01, IMP-02, IMP-03, IMP-04, INFRA-02

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User delegated all Phase 2 decisions to Claude. The following areas should be resolved during research and planning based on project requirements, CLAUDE.md constraints, and best practices:

**Import job tracking:**
- Background job management approach (in-memory vs DB-backed)
- Progress reporting mechanism (polling endpoint with job ID)
- Job state model (pending, in_progress, completed, failed)
- Concurrency handling (what if user triggers import while one is running)

**Error handling & resilience:**
- Platform API downtime and rate limiting strategy
- Retry policy for transient failures
- Partial success behavior (some games imported, then failure)
- User-facing error messages for invalid usernames, API errors, etc.
- PGN parsing failures for individual games (skip and continue)

**API endpoint design:**
- Endpoint structure (unified vs per-platform)
- Re-sync trigger mechanism (same endpoint, detects last import)
- Response shape for import initiation and status polling
- Progress granularity (games fetched count, total estimate if available)

**Platform normalization:**
- chess.com monthly archives API: sequential fetching with rate-limit delays, User-Agent header required
- lichess NDJSON streaming: line-by-line parsing
- Unified schema mapping from both platform formats to Game model
- Edge cases: missing fields, non-Standard variants (filter out), anonymous opponents
- Time control bucketing: <=180s bullet, <=600s blitz, <=1800s rapid, else classical
- lichess timestamps in milliseconds (not seconds)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User trusts Claude's technical judgment for this backend infrastructure phase.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/zobrist.py`: `hashes_for_game(pgn_text)` returns `[(ply, white_hash, black_hash, full_hash), ...]` — call this for each imported game
- `app/models/game.py`: `Game` model with all metadata fields, unique constraint on `(platform, platform_game_id)`
- `app/models/game_position.py`: `GamePosition` model with hash columns and denormalized `user_id`
- `app/models/base.py`: `Base` class with `int -> BIGINT` mapping and timezone-aware datetimes

### Established Patterns
- SQLAlchemy 2.x async with `select()` API
- Pydantic v2 for request/response schemas
- `httpx.AsyncClient` for all external HTTP (never `requests`)
- routers/services/repositories layering

### Integration Points
- Import service calls `hashes_for_game()` per game PGN to generate position rows
- Bulk insert `Game` + `GamePosition` rows using existing models
- `user_id` must be set on both `games` and `game_positions` (denormalized)
- Duplicate games handled by DB unique constraint `(platform, platform_game_id)`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-import-pipeline*
*Context gathered: 2026-03-11*

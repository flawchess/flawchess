# Phase 1: Data Foundation - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the database schema (`games`, `game_positions`, and supporting tables) and the Zobrist hash computation module. This is pure backend infrastructure — no API endpoints, no import logic, no frontend. Every subsequent phase depends on this being correct.

Requirements: INFRA-01, INFRA-03, IMP-05, IMP-06

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User delegated all Phase 1 decisions to Claude. The following areas should be resolved during research and planning based on project requirements and best practices:

**Game metadata fields (`games` table):**
- Store all available metadata from both platforms: PGN, time control string, estimated duration, rated flag, result, opponent username, user color, platform URL, platform game ID, platform name, timestamps (played_at, imported_at)
- Include opponent rating and user rating at time of game (available from both APIs, valuable for future analysis)
- Include opening name/ECO from platform as-is (informational only — not used for position matching, but useful for display)
- Variant column to filter Standard-only at query time (import should store the variant string)

**Zobrist hash approach:**
- Use python-chess's built-in `chess.polyglot.zobrist_hash()` for full_hash
- For white_hash and black_hash: compute custom hashes by iterating only over pieces of the target color using Zobrist piece-square tables
- Use consistent, deterministic hash tables (seed-based or hardcoded Polyglot-compatible values)
- All hashes stored as 64-bit signed integers (PostgreSQL `BIGINT`)

**Project bootstrapping:**
- Backend rooted at project root (not a subdirectory) — `app/` package with `main.py`
- Directory structure: `app/{routers,services,repositories,models,schemas,core}/`
- `pyproject.toml` with uv, ruff config, pytest config
- Alembic initialized with async PostgreSQL driver (asyncpg)
- `.env` for database URL and secrets (with `.env.example` committed)

**ID and key strategy:**
- `games.id`: auto-increment `BIGINT` primary key (simpler, faster joins than UUID)
- `game_positions`: composite index on `(user_id, full_hash)`, `(user_id, white_hash)`, `(user_id, black_hash)` for query performance
- `game_positions.id`: auto-increment `BIGINT` (needed for ORM, but queries use hash indexes)
- Hash columns: `BIGINT` (64-bit signed integer, matches Python's int representation of Zobrist hashes)
- Unique constraint: `(platform, platform_game_id)` on `games` table

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User is an experienced Python/FastAPI developer and trusts Claude's technical judgment for this infrastructure phase.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- CLAUDE.md defines the architecture: routers/services/repositories pattern
- SQLAlchemy 2.x async with `select()` API (not legacy 1.x)
- Pydantic v2 for all validation
- python-chess 1.10.x for chess logic

### Integration Points
- Schema must support Phase 2's import pipeline (bulk inserts of games + positions)
- Hash module must be importable by Phase 2's import service
- Schema must support Phase 3's analysis queries (indexed hash lookups with filters)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-foundation*
*Context gathered: 2026-03-11*

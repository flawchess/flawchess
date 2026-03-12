---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 04-03 complete
status: complete
stopped_at: Completed 04-03-PLAN.md — all UAT issues fixed, phase 4 complete
last_updated: "2026-03-12T10:55:13.368Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 11
  completed_plans: 11
---

# Project State: Chessalytics

## Current Phase
Phase: 04-frontend-and-auth
Status: Complete — 3/3 plans done, all UAT fixes applied
Current Plan: 04-03 complete
Stopped At: Completed 04-03-PLAN.md — all UAT issues fixed, phase 4 complete

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-11)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 4 - Frontend and Auth

## Phase Progress
| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Data Foundation | Complete | 2/2 |
| 2 | Import Pipeline | Complete | 4/4 |
| 3 | Analysis API | Complete | 2/2 |
| 4 | Frontend and Auth | Complete | 3/3 |

## Key Context
- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import

## Accumulated Context

### Key Decisions
- **AsyncAttrs import path**: Use `from sqlalchemy.ext.asyncio import AsyncAttrs` (not `sqlalchemy.orm`) in SQLAlchemy 2.0.x
- **user_id denormalized on game_positions**: Required for composite index lookups without joins on the analysis hot path
- **BIGINT type_annotation_map**: `Base` class maps `int -> BIGINT` so all `Mapped[int]` columns auto-resolve to BIGINT
- **server_default=func.now()**: Used for `imported_at` (not Python-evaluated `datetime.utcnow`)
- **Local PostgreSQL**: postgresql@17 installed via brew, database `chessalytics` created for development
- **Zobrist color_pivot**: 0 for WHITE, 1 for BLACK — matches polyglot standard (white = even indices per piece type, black = odd)
- **hashes_for_game empty list**: Returns [] for PGN with no mainline moves (garbage input); ply 0 only included when at least one move exists
- **Zobrist ply 0**: hashes_for_game includes ply 0 (initial position) before any move is played
- **bulk_insert_positions no RETURNING**: positions only inserted for new games returned by bulk_insert_games; no conflict handling needed
- **db_session fixture**: AsyncSession bound to connection-level transaction rolled back per-test for real-DB isolation without cleanup code
- **Time control bucketing**: estimated duration = base + increment*40; thresholds <=180 bullet, <=600 blitz, <=1800 rapid, else classical
- **chess.com incremental sync boundary**: archive skipped when archive_end (first day of next month) <= since_timestamp; current month always included
- **chess.com 429 backoff**: single 60s sleep + one retry (not exponential) for simplicity
- **lichess perfType filter**: ultraBullet,bullet,blitz,rapid,classical sent on every request; correspondence and unlimited excluded
- **lichess moves=false**: PGN available via pgnInJson=true so moves array field excluded from response
- **In-memory job registry + DB fallback**: Live job state in _jobs dict (zero-latency reads); DB queried only for historical/restarted jobs
- **PGN lookup via SELECT after bulk_insert**: Correctness over index-alignment — SELECT (id, pgn) for new game IDs handles ON CONFLICT gaps correctly
- **chess.com non-200 archives raises ValueError**: Any non-200/non-404 archives response raises ValueError with status code before .json() is called — consistent with job error contract
- **chess.com per-archive non-200 uses continue**: Partial archive failure uses continue not raise — one bad month should not abort the whole user import
- **Analysis DISTINCT by Game.id**: _build_base_query uses .distinct(Game.id) so a position appearing at multiple plies counts the game only once in W/D/L stats
- **Analysis two-query pattern**: query_all_results fetches lightweight (result, user_color) tuples for stats; query_matching_games fetches full Game objects for display — keeps stats accurate for total > limit
- **DISTINCT ON ORDER BY constraint**: PostgreSQL requires DISTINCT ON column to be first in ORDER BY — paginated analysis query uses order_by(Game.id, Game.played_at.desc())
- **select_entity list unpacking**: _build_base_query normalizes select_entity to list and unpacks via *entities — supports both single ORM entity and multi-column selects in query_all_results
- **FastAPI-Users IntegerIDMixin on UserManager**: IntegerIDMixin goes on UserManager class, not on the User model itself
- **asyncio_default_test_loop_scope=session**: App-level engine pool binds to first event loop; session scope prevents cross-test asyncpg RuntimeError
- **Auth test unique emails**: Users table persists across runs; tests use uuid4 email suffixes for idempotency
- **user_id before create_task**: Depends(current_active_user) only valid in request scope — extract user.id before asyncio.create_task
- **Vite proxy for API routing**: Frontend uses relative URLs (/auth, /analysis, /imports) forwarded to localhost:8000 via Vite server.proxy — no hardcoded backend URL
- **BigInt + string transport for Zobrist**: Hashes computed as BigInt throughout JS (avoids IEEE-754 precision loss), converted to decimal string for JSON; backend coerce_target_hash validator converts str->int
- **Zobrist JS uses dual indexing**: whiteHash/blackHash use color-relative pivot (white=0, black=1 matching _color_hash); fullHash uses ZobristHasher pivot (white=1, black=0) plus castling/EP/turn
- **Turn hash XOR on white to move**: chess.polyglot.zobrist_hash XORs index 780 when WHITE is to move — JS port matches this (not black)
- **shadcn/ui Nova preset, dark-only**: <html class="dark"> in index.html, Nova/Radix theme locked for frontend
- **react-chessboard v5 options API**: v5 changed from flat props to a single `options` object prop — `<Chessboard options={{ position, boardStyle, onPieceDrop }} />`
- **useChessGame replay approach**: goToMove replays from new Chess() rather than undoing — chess.js has no undo API; replay guarantees correctness
- **PieceDropHandlerArgs.targetSquare is string | null**: null when piece dropped off board — guard required before calling makeMove
- **Google OAuth SPA flow**: /callback redirects to FRONTEND_URL/auth/callback#token=JWT so SPA can read token from URL fragment without it appearing in server logs
- **ImportJobStatus mismatch**: backend uses 'completed'/'failed', not 'done'/'error' — was root cause of spinner never stopping + errors never showing
- **GET /games/count**: lightweight endpoint for dashboard empty-state CTA — avoids special-casing analysis endpoint with null hash
- **react-chessboard squareStyles**: prop name for per-square CSS overrides is `squareStyles` (not `customSquareStyles`)

### Performance Metrics
| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 5min | 2 | 18 |
| 01 | 02 | 3min | 3 | 4 |
| 02 | 01 | 6min | 2 | 10 |
| 02 | 02 | 3min | 2 | 4 |
| 02 | 03 | 3min | 2 | 5 |
| 02 | 04 | 2min | 2 | 2 |
| 03 | 01 | 2min | 2 | 5 |
| 03 | 02 | 4min | 2 | 3 |
| 04 | 01 | 10min | 2 | 12 |
| 04 | 02 | 15min | 3 | 20 |
| 04 | 03 | 45min | 3 | 27 |

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | can the coordinate numbers and letters be displayed outside of the board? | 2026-03-12 | b40ad87 | [1-can-the-coordinate-numbers-and-letters-b](.planning/quick/1-can-the-coordinate-numbers-and-letters-b/) |
| 2 | add platform filter in more filters section | 2026-03-12 | b5266a9 | [2-add-platform-filter-in-more-filters-sect](.planning/quick/2-add-platform-filter-in-more-filters-sect/) |

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions for querying pieces on specific squares
- **Display opening name from lichess chess-openings database** (ui) — Show ECO code + opening name on interactive board via prefix-match; optional backend Zobrist lookup

---
Last activity: 2026-03-12 - Completed quick task 2: add platform filter in more filters section

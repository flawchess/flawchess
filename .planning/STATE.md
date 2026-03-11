---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 02-03 complete
status: completed
stopped_at: Completed 02-04-PLAN.md
last_updated: "2026-03-11T14:15:31.336Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
---

# Project State: Chessalytics

## Current Phase
Phase: 02-import-pipeline
Status: Complete — all 4 plans done (4/4 plans)
Current Plan: 02-04 complete
Stopped At: Completed 02-04-PLAN.md

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-11)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 2 - Import Pipeline

## Phase Progress
| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Data Foundation | Complete | 2/2 |
| 2 | Import Pipeline | Complete | 4/4 |
| 3 | Analysis API | Pending | 0/0 |
| 4 | Frontend and Auth | Pending | 0/0 |

## Key Context
- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users
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
- **Import user_id=1 placeholder**: POST /imports uses hardcoded user_id=1 with TODO comment; real auth added in Phase 4 with FastAPI-Users
- **In-memory job registry + DB fallback**: Live job state in _jobs dict (zero-latency reads); DB queried only for historical/restarted jobs
- **PGN lookup via SELECT after bulk_insert**: Correctness over index-alignment — SELECT (id, pgn) for new game IDs handles ON CONFLICT gaps correctly
- **chess.com non-200 archives raises ValueError**: Any non-200/non-404 archives response raises ValueError with status code before .json() is called — consistent with job error contract
- **chess.com per-archive non-200 uses continue**: Partial archive failure uses continue not raise — one bad month should not abort the whole user import

### Performance Metrics
| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 5min | 2 | 18 |
| 01 | 02 | 3min | 3 | 4 |
| 02 | 01 | 6min | 2 | 10 |
| 02 | 02 | 3min | 2 | 4 |
| 02 | 03 | 3min | 2 | 5 |
| 02 | 04 | 2min | 2 | 2 |

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions for querying pieces on specific squares
- **Display opening name from lichess chess-openings database** (ui) — Show ECO code + opening name on interactive board via prefix-match; optional backend Zobrist lookup
- **Add users table and authentication** (database) — users table, FastAPI-Users integration, link chess.com + lichess to single user account

---
*Last updated: 2026-03-11 after 02-04 completion — Phase 2 Import Pipeline fully complete including UAT gap closure*

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 01-02 complete
status: executing
last_updated: "2026-03-11T12:42:07.025Z"
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
---

# Project State: Chessalytics

## Current Phase
Phase: 01-data-foundation
Status: In progress — Plan 02 complete (2/N plans)
Current Plan: 01-02 complete

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-11)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 1

## Phase Progress
| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Data Foundation | In Progress | 2/? |
| 2 | Import Pipeline | Pending | 0/0 |
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

### Performance Metrics
| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 5min | 2 | 18 |
| 01 | 02 | 3min | 3 | 4 |

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions for querying pieces on specific squares
- **Display opening name from lichess chess-openings database** (ui) — Show ECO code + opening name on interactive board via prefix-match; optional backend Zobrist lookup

---
*Last updated: 2026-03-11 after 01-02 completion*

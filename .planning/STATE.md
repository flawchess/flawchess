# Project State: Chessalytics

## Current Phase
Phase: 01-data-foundation
Status: In progress — Plan 01 complete (1/N plans)
Current Plan: 01-01 complete

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-11)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 1

## Phase Progress
| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Data Foundation | In Progress | 1/? |
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

### Performance Metrics
| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 5min | 2 | 18 |

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo

---
*Last updated: 2026-03-11 after 01-01 completion*

---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Consolidation, Tooling & Refactoring
status: verifying
last_updated: "2026-04-01T00:20:05.254Z"
last_activity: 2026-04-01
progress:
  total_phases: 8
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 50
---

# Project State: FlawChess

## Current Position

Phase: 40 (static-type-checking) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-04-01

Progress: [██████████] 100%

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.7 Consolidation, Tooling & Refactoring

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (2 vCPUs, 3.7 GB RAM + 2 GB swap)

## Accumulated Context

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)
- bulk_insert_positions chunk_size tuning required when adding columns — asyncpg 32767 arg limit

### Decisions Made (Phase 40)

- **Row[Any] return types in repositories** — Service layer will adopt TypedDicts/named tuples in Plan 02
- **isinstance(PositionBookmark) over hasattr()** — Type-safe ORM detection in model_validator
- **ty: ignore suppressions for FastAPI-Users** — Generic typing not resolved by ty beta; D-07 decision
- **cast() for API dict values to Literal types** — Narrow values from external API dicts without runtime overhead
- **NormalizedGame model_dump() in _flush_batch** — isinstance check maintains dict compat for test mocks

---
Last activity: 2026-04-01 - Phase 40 Plan 02 complete: service-layer typing, zero ty errors achieved

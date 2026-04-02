---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Consolidation, Tooling & Refactoring
status: executing
last_updated: "2026-04-02T19:53:36.554Z"
last_activity: 2026-04-02
progress:
  total_phases: 8
  completed_phases: 1
  total_plans: 6
  completed_plans: 3
  percent: 100
---

# Project State: FlawChess

## Current Position

Phase: 41 (code-quality-dead-code) — EXECUTING
Plan: 2 of 4
Status: Ready to execute
Last activity: 2026-04-02

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

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260402-psb | Fix frontend cache-busting so deployed updates reach users without manual refresh | 2026-04-02 | 85e7657 | [260402-psb-fix-frontend-cache-busting-so-deployed-u](./quick/260402-psb-fix-frontend-cache-busting-so-deployed-u/) |
| 260402-qms | Document Sentry access in CLAUDE.md and add error fingerprinting hooks for DB and HTTP errors | 2026-04-02 | d3bbe5f | [260402-qms-document-sentry-access-in-claude-md-and-](./quick/260402-qms-document-sentry-access-in-claude-md-and-/) |

### Decisions Made (Phase 40)

- **Row[Any] return types in repositories** — Service layer will adopt TypedDicts/named tuples in Plan 02
- **isinstance(PositionBookmark) over hasattr()** — Type-safe ORM detection in model_validator
- **ty: ignore suppressions for FastAPI-Users** — Generic typing not resolved by ty beta; D-07 decision
- **cast() for API dict values to Literal types** — Narrow values from external API dicts without runtime overhead
- **NormalizedGame model_dump() in _flush_batch** — isinstance check maintains dict compat for test mocks

### Decisions Made (Phase 41, Plan 01)

- **Minimal knip.json config** — Vite/Vitest plugins auto-activate from devDependencies; no explicit plugin config needed
- **CI step ordering: eslint -> build -> test -> knip** — type errors caught before test failures, dead code last
- **Knip exit 1 acceptable during Plan 01** — existing dead code will be cleaned up in Plan 03; CI gate enforces no new dead code after cleanup

---
Last activity: 2026-04-02 - Completed 41-01-PLAN.md: Install Knip and add frontend CI steps

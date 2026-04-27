---
phase: 70-backend-opening-insights-service
plan: "02"
subsystem: database-index
tags: [opening-insights, alembic, migration, performance, postgresql-concurrently]
dependency_graph:
  requires: []
  provides: [ix_gp_user_game_ply]
  affects:
    - alembic/versions/80e22b38993a_add_gp_user_game_ply_index.py
    - app/models/game_position.py
tech_stack:
  added: []
  patterns: [postgresql-concurrently, partial-covering-index, autocommit-block]
key_files:
  created:
    - alembic/versions/{ts}_80e22b38993a_add_gp_user_game_ply_index.py
  modified:
    - app/models/game_position.py
decisions:
  - "Column order (user_id, game_id, ply) is LOAD-BEARING — matches LAG window's PARTITION BY game_id ORDER BY ply within a per-user predicate so Postgres streams rows from the index without a re-sort"
  - "Partial predicate `ply BETWEEN 1 AND 17` keeps the index ~9% of table size (entry plies 3..16 plus the LAG-source ply 1)"
  - "INCLUDE (full_hash, move_san) keeps Index Only Scan with Heap Fetches: 0"
  - "First project use of postgresql_concurrently=True + autocommit_block — rationale captured inline so future maintainers don't reorder columns or drop the option"
metrics:
  shipped_in_pr: "#66 (df9b689)"
  migration_revision: "80e22b38993a"
  migration_lines: 61
  perf_hikaru_user: "5.7M positions: ~2.0 s → 816 ms"
  perf_median_user: "336k positions: 65 ms (Index Only Scan)"
ship_status: shipped
---

# Phase 70 Plan 02: Partial Composite Covering Index ix_gp_user_game_ply (retroactive summary)

**One-liner:** Added the database-side prerequisite for Plan 70-03's transition CTE — a partial composite covering index that turns the LAG-window scan into an Index Only Scan with Heap Fetches: 0.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | Alembic migration adding ix_gp_user_game_ply with postgresql_concurrently=True | alembic/versions/{ts}_80e22b38993a_add_gp_user_game_ply_index.py |
| 2 | Declarative Index() entry on GamePosition.__table_args__ to keep autogenerate clean | app/models/game_position.py |

## What Was Built

- New Alembic revision `80e22b38993a` (down_revision = `6809b7c79eb3`). Upgrade and downgrade both wrap their DDL in `op.get_context().autocommit_block()` so CONCURRENTLY can run outside a transaction. First migration in the project to use `postgresql_concurrently=True`.
- DDL: `CREATE INDEX ix_gp_user_game_ply ON game_positions(user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17`.
- Declarative `Index(...)` entry appended to `GamePosition.__table_args__` mirroring the migration so `alembic check` proposes no diff.
- Multi-line LOAD-BEARING rationale comments in BOTH the migration and the model entry so future autogenerate runs don't reorder columns "for symmetry" with sibling `ix_gp_user_*` indexes.

## Deviations from Plan

None — column order, predicate, and INCLUDE columns shipped exactly as planned.

## Verification

- `uv run alembic upgrade head` + `uv run alembic downgrade -1` round-trip cleanly on dev DB.
- `pg_indexes` confirms partial btree on `(user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ((ply >= 1) AND (ply <= 17))`.
- EXPLAIN (ANALYZE, BUFFERS) on the canonical Plan 70-03 query reports `Index Only Scan using ix_gp_user_game_ply` and `Heap Fetches: 0`.

## Production Deploy Note

First-deploy index build is non-blocking for reads/writes (CONCURRENTLY) but takes ~30-60s wall time on the heaviest user (Hikaru-class, 5.7M positions). The backend container's `entrypoint.sh` runs `alembic upgrade head` before starting Uvicorn, so the deploy job blocks for that duration on first apply.

## Follow-up

Phase 71 Plan 01 tightened the predicate by extending the partial-index range; see migration `{rev}_expand_ix_gp_user_game_ply_predicate_to_.py` shipped in PR #67. The two together form the locked-in shape for the openings-insights query path.

## Self-Check

- [x] Migration exists and uses `postgresql_concurrently=True` + `autocommit_block` in both directions
- [x] `GamePosition.__table_args__` contains `ix_gp_user_game_ply` declarative entry
- [x] `alembic heads` shows exactly one head
- [x] Shipped as part of PR #66 (df9b689)

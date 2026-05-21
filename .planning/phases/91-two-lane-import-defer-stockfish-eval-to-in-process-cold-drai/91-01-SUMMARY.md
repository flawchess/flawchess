---
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
plan: "01"
subsystem: backend-schema
tags:
  - schema
  - alembic
  - migration
  - eval-tracking
dependency_graph:
  requires: []
  provides:
    - "games.evals_completed_at TIMESTAMPTZ NULL column"
    - "ix_games_evals_pending partial index ON games(id) WHERE evals_completed_at IS NULL"
    - "Game.evals_completed_at ORM mapped column"
  affects:
    - "app/models/game.py (Game model)"
    - "alembic migration chain (new head: bd54be3a66bf)"
tech_stack:
  added: []
  patterns:
    - "Alembic migration with postgresql_where string-form partial index"
    - "Migration backfill via op.execute UPDATE with COALESCE"
    - "asyncio.to_thread for alembic commands inside async pytest tests"
key_files:
  created:
    - "alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py"
    - "tests/test_migration_91_evals_completed_at.py"
  modified:
    - "app/models/game.py"
decisions:
  - "Used asyncio.to_thread to run alembic commands inside async pytest session (alembic env.py calls asyncio.run internally)"
  - "Restored imported_at NOT NULL constraint after upgrade in test_backfill_uses_now_when_imported_at_null (must backfill NULL imported_at before SET NOT NULL)"
  - "COALESCE(imported_at, NOW()) confirmed as correct backfill expression (no updated_at/created_at on games table per RESEARCH OQ-3)"
metrics:
  duration: "8m"
  completed: "2026-05-21"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 1
---

# Phase 91 Plan 01: Schema Migration (evals_completed_at + partial index + backfill) Summary

**One-liner:** Schema foundation for Phase 91 eval tracking: nullable TIMESTAMPTZ column + `WHERE evals_completed_at IS NULL` partial index + COALESCE(imported_at, NOW()) backfill of 187,851 dev DB rows.

## What Was Built

Three artifacts deliver the persistence layer needed by all subsequent Phase 91 plans:

**1. ORM model update (`app/models/game.py`)**
Added `evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)` after `imported_at`. Explicit `sa.DateTime(timezone=True)` matches the TIMESTAMPTZ the migration creates. `ty check` passes with zero errors.

**2. Alembic migration (`alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py`)**
- `down_revision = "e925558020b9"` (previous head)
- Upgrade: add column, create `ix_games_evals_pending ON games(id) WHERE evals_completed_at IS NULL`, backfill via `UPDATE games SET evals_completed_at = COALESCE(imported_at, NOW()) WHERE evals_completed_at IS NULL`
- Downgrade: drop index, drop column
- Round-trip (`downgrade -1` then `upgrade head`) verified. Backfilled 187,851 rows on dev DB.

**3. Migration test suite (`tests/test_migration_91_evals_completed_at.py`)**
Four tests:
- `test_migration_adds_column_and_index`: down/up cycle verifies column + index presence/absence and index predicate
- `test_backfill_leaves_no_pending_rows`: 3 pre-inserted rows with known `imported_at` verified to have `evals_completed_at = imported_at` after upgrade; zero NULL rows
- `test_downgrade_removes_column_and_index`: column and index absent after downgrade
- `test_backfill_uses_now_when_imported_at_null`: `COALESCE` NOW() branch verified via temporary NOT NULL drop on `imported_at`

All 1,597 tests pass (including the full regression suite). `uv run ty check app/ tests/` exits 0.

## Key Decisions

- **Backfill expression:** `COALESCE(imported_at, NOW())` — `games` has no `updated_at` or `created_at` column (RESEARCH OQ-3). CONTEXT D-08 text was incorrect; the corrected expression is locked in RESEARCH and this plan.
- **Alembic async compatibility:** `alembic.command.upgrade/downgrade` call `asyncio.run()` internally via `env.py`. Running them inside an already-running pytest-asyncio session would raise `RuntimeError`. Used `asyncio.to_thread` in helper functions to run them in a thread pool.
- **Test: restoring NOT NULL after NOW() branch test:** After inserting a game with `imported_at = NULL`, the migration backfill sets `evals_completed_at = NOW()` but `imported_at` remains NULL. To restore the NOT NULL constraint, we must first update the NULL `imported_at` row, then run `ALTER TABLE ... SET NOT NULL`.

## Deviations from Plan

None - plan executed exactly as written with two minor implementation discoveries documented as decisions above.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond those in the plan's `<threat_model>`. The `evals_completed_at` column is not exposed in any response model (T-91-02 mitigated).

## Self-Check: PASSED

- `app/models/game.py` exists and contains `evals_completed_at`: confirmed
- `alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py` exists: confirmed
- `tests/test_migration_91_evals_completed_at.py` exists: confirmed
- Commit `9e27fe21` exists: confirmed (feat: ORM model)
- Commit `dd0abe37` exists: confirmed (feat: Alembic migration)
- Commit `f7518489` exists: confirmed (test: migration tests)
- `uv run pytest tests/test_migration_91_evals_completed_at.py -x`: 4/4 PASSED
- `uv run pytest -x -q`: 1597 passed, 6 skipped
- `uv run ty check app/ tests/`: All checks passed
- Backfill row count on dev DB: 187,851 rows (zero NULL rows post-upgrade)
- `down_revision = "e925558020b9"`: confirmed
- No `updated_at` or `created_at` in migration file: confirmed (0 matches)

---
phase: 117-priority-queue-flaw-integration
plan: "01"
subsystem: database-schema
tags: [migration, alembic, eval-queue, pv-capture, orm-models]
dependency_graph:
  requires: [116-all-ply-engine-core]
  provides: [eval_jobs-table, best_move-column, pv-column, lichess_evals_at-column, full_pv_completed_at-column]
  affects: [eval_drain, engine, flaws_service, normalization]
tech_stack:
  added: []
  patterns: [partial-unique-index-via-Index, BigInteger-autoincrement-PK, cascade-FK-ondelete]
key_files:
  created:
    - alembic/versions/20260613_120000_phase_117_queue_pv.py
    - app/models/eval_jobs.py
    - tests/test_migration_117.py
  modified:
    - app/models/game.py
    - app/models/game_position.py
    - app/models/__init__.py
decisions:
  - "Partial unique index via Index(postgresql_where=...) instead of UniqueConstraint to allow re-enqueue after completion (RESEARCH Open Question 1)"
  - "Tier constants TIER_EXPLICIT/TIER_AUTO_WINDOW/TIER_IDLE_BACKLOG defined in eval_jobs.py to avoid magic numbers in consumers"
  - "game_positions.best_move String(5) nullable (not String(4)) to cover promotions per D-117-03"
  - "Text import added to game_position.py imports for the new pv column"
metrics:
  duration: "~12 minutes"
  completed: "2026-06-13T09:12:51Z"
  tasks_completed: 3
  files_modified: 6
---

# Phase 117 Plan 01: Schema Foundation — Queue, PV Columns, Backfill Summary

**One-liner:** Alembic migration adding eval_jobs lease table, best_move/pv/lichess_evals_at/full_pv_completed_at columns, four partial indexes, and D-117-10 one-time lichess provenance backfill.

## What Was Built

The schema substrate for Phase 117's priority queue and PV capture:

**Migration** (`alembic/versions/20260613_120000_phase_117_queue_pv.py`):
- revision `20260613120000`, down_revision `20260612120000` (Phase 116 head, verified)
- Step 1: `game_positions.best_move VARCHAR(5)` + `game_positions.pv TEXT` (nullable, instant catalog ops on 44.4M-row table)
- Step 2: `games.lichess_evals_at TIMESTAMPTZ` + `games.full_pv_completed_at TIMESTAMPTZ` (nullable)
- Step 3: `ix_games_full_pv_pending` partial index on `games(id) WHERE full_pv_completed_at IS NULL`
- Step 4: `eval_jobs` table with id (BigSerial), tier (SmallInt), user_id FK CASCADE, game_id FK CASCADE, status varchar(20) server_default 'pending', leased_by, lease_expiry, created_at, completed_at; plus `uq_eval_jobs_game_active` (partial unique WHERE status IN ('pending','leased')), `ix_eval_jobs_pick`, `ix_eval_jobs_leased`
- Step 5: D-117-10 backfill `UPDATE games SET lichess_evals_at = COALESCE(imported_at, NOW()) WHERE white_blunders IS NOT NULL AND lichess_evals_at IS NULL` (runs last per Pitfall 5)
- `downgrade()` reverses in symmetric order; backfill is irreversible by design

**EvalJob ORM model** (`app/models/eval_jobs.py`):
- `__tablename__ = "eval_jobs"`, BigInteger PK, SmallInteger tier (with named constants TIER_EXPLICIT=1, TIER_AUTO_WINDOW=2, TIER_IDLE_BACKLOG=3)
- FK to `users.id` and `games.id` both with `ondelete="CASCADE"` (CLAUDE.md mandatory FK rule)
- `__table_args__` mirrors `game.py` tuple pattern with three partial indexes
- Registered in `app/models/__init__.py`

**Game model additions** (`app/models/game.py`):
- `lichess_evals_at` (D-117-06): provenance column, set ONLY at lichess import; NULL = engine-written, WR-02 transplant-safe
- `full_pv_completed_at` (D-117-12): second completion dimension parallel to `full_evals_completed_at`
- `is_analyzed` hybrid left untouched (D-117-09)

**GamePosition model additions** (`app/models/game_position.py`):
- `best_move String(5)` (D-117-01/03): UCI PV[0] for every evaluated position; 5-char cap covers promotions
- `pv Text` (D-117-02): flaw-adjacent refutation line, stored only at ply = flaw_ply + 1
- Added `Text` to SQLAlchemy imports

**Migration test** (`tests/test_migration_117.py`):
- 5 tests, all green
- Column/table/index existence (downgrade/upgrade cycle)
- D-117-10 backfill: white_blunders IS NOT NULL → lichess_evals_at set; white_blunders IS NULL → lichess_evals_at stays NULL
- Dedicated user ID range 999_200-999_299 to avoid FK collisions with 116 test suite

## Verification Results

- `uv run alembic upgrade head` → revision `20260613120000 (head)` — clean
- `uv run pytest tests/test_migration_117.py -x` — 5/5 passed (8.71s)
- `uv run ty check app/ tests/` — zero errors
- `uv run ruff check app/ tests/` — clean
- `uv run python -c "import app.models"` — EvalJob registered, no import errors

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. This plan adds schema only (columns, table, indexes, ORM models). No data wiring or UI is involved.

## Threat Flags

None. All new surface is server-internal (migration DDL + ORM models). The eval_jobs table is backend-only with FK cascade enforcement; no new network endpoints or auth paths introduced.

## Self-Check: PASSED

Files created/exist:
- /home/aimfeld/Projects/Python/flawchess/alembic/versions/20260613_120000_phase_117_queue_pv.py FOUND
- /home/aimfeld/Projects/Python/flawchess/app/models/eval_jobs.py FOUND
- /home/aimfeld/Projects/Python/flawchess/tests/test_migration_117.py FOUND

Commits exist:
- 4cad7acc: feat(117-01): EvalJob model + new columns on Game and GamePosition FOUND
- 5c228792: feat(117-01): Alembic migration — columns, eval_jobs table, indexes, D-117-10 backfill FOUND
- 4d1d5eff: test(117-01): Wave 0 migration test — column existence, eval_jobs table, D-117-10 backfill FOUND

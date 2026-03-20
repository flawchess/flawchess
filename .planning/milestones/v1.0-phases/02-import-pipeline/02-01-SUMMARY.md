---
phase: 02-import-pipeline
plan: "01"
subsystem: import-pipeline
tags: [normalization, repository, bulk-insert, import-jobs, alembic]
dependency_graph:
  requires: [01-01, 01-02]
  provides: [ImportJob model, game_repository, import_job_repository, normalization utilities, Pydantic import schemas]
  affects: [02-02, 02-03]
tech_stack:
  added: []
  patterns:
    - "ON CONFLICT DO NOTHING with RETURNING for idempotent bulk insert"
    - "Transaction-rollback pattern for real-DB test isolation"
    - "Estimated duration = base + increment*40 for time control bucketing"
key_files:
  created:
    - app/models/import_job.py
    - app/schemas/imports.py
    - app/services/normalization.py
    - app/repositories/game_repository.py
    - app/repositories/import_job_repository.py
    - alembic/versions/9e234104d7f2_add_import_jobs_table.py
    - tests/test_normalization.py
    - tests/test_game_repository.py
  modified:
    - app/models/__init__.py
    - tests/conftest.py
decisions:
  - "Timeout result fallback: when neither player has 'win' and neither has an explicit draw result, normalize_chesscom_result returns '1/2-1/2' as safe fallback"
  - "db_session fixture uses conn.begin() + conn.rollback() pattern binding AsyncSession to a connection-level transaction for real-DB isolation without cleanup code"
  - "bulk_insert_positions returns None (no RETURNING needed) - positions only inserted for new games"
metrics:
  duration_seconds: 375
  completed_date: "2026-03-11"
  tasks_completed: 2
  files_created: 8
  files_modified: 2
  tests_added: 62
---

# Phase 2 Plan 1: Data Contracts and Repository Layer Summary

**One-liner:** ImportJob model + migration, Pydantic import schemas, platform normalization utilities (parse_time_control, normalize_chesscom_game, normalize_lichess_game), and bulk-insert game/position repositories with ON CONFLICT DO NOTHING — all tested TDD against real PostgreSQL.

## What Was Built

### Task 1: ImportJob Model, Schemas, and Normalization (TDD)

**ImportJob SQLAlchemy model** (`app/models/import_job.py`):
- UUID string primary key, user_id (indexed), platform, username, status
- games_fetched, games_imported counters
- last_synced_at for incremental sync support
- started_at (server_default=func.now()), completed_at

**Pydantic schemas** (`app/schemas/imports.py`):
- `ImportRequest`: platform (Literal), username with length constraints
- `ImportStartedResponse`: job_id + status
- `ImportStatusResponse`: full job state + `from_dict()` convenience method

**Normalization module** (`app/services/normalization.py`):
- `parse_time_control()`: handles `base+increment` format, daily `1/N` format, edge cases. Estimated duration = `base + increment * 40`. Thresholds: ≤180 bullet, ≤600 blitz, ≤1800 rapid, else classical.
- `normalize_chesscom_game()`: maps chess.com JSON → Game dict. Filters `rules != "chess"`. Case-insensitive username comparison for user_color. Maps win/draw result strings. Extracts ECO code from URL with regex.
- `normalize_lichess_game()`: maps lichess NDJSON → Game dict. Filters `variant.key != "standard"`. Converts createdAt ms → datetime. Constructs platform_url. Handles missing clock gracefully.

**Alembic migration** `9e234104d7f2`: creates `import_jobs` table with `ix_import_jobs_user_id` index.

**49 normalization tests** covering all time control buckets, variant filtering, result mapping, field extraction.

### Task 2: Game Repository and Import Job Repository (TDD)

**game_repository** (`app/repositories/game_repository.py`):
- `bulk_insert_games()`: `pg_insert(Game).on_conflict_do_nothing(constraint="uq_games_platform_game_id").returning(Game.id)` — returns only newly inserted IDs
- `bulk_insert_positions()`: bulk insert GamePosition rows with `insert(GamePosition).values(...)`

**import_job_repository** (`app/repositories/import_job_repository.py`):
- `create_import_job()`: creates with status="pending"
- `update_import_job()`: kwargs-based field update via setattr
- `get_import_job()`: fetch by UUID
- `get_latest_for_user_platform()`: most recent completed job ordered by completed_at DESC

**db_session fixture** (`tests/conftest.py`):
- `AsyncSession(bind=conn)` where conn has an open transaction
- `conn.rollback()` in finally block ensures test isolation
- Uses real PostgreSQL — no mocking

**13 repository tests** covering bulk insert, duplicate skipping, empty list, position insertion, full CRUD, and incremental sync query.

## Success Criteria: All Met

1. ImportJob model defined and migration applied — `import_jobs` table exists in PostgreSQL.
2. `parse_time_control` correctly classifies all time control categories including increment-adjusted durations.
3. Both `normalize_chesscom_game` and `normalize_lichess_game` produce dicts matching Game model columns, filtering non-standard variants.
4. `bulk_insert_games` uses ON CONFLICT DO NOTHING and only returns IDs for newly inserted games.
5. All 78 tests pass: `uv run pytest -x` exits 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected test assertion for timeout result mapping**
- **Found during:** Task 1 GREEN phase
- **Issue:** Initial test had a contradictory comment asserting `"1-0"` for a case where black wins (white times out). The comment correctly explained it should be `"0-1"` but the assertion said `"1-0"`.
- **Fix:** Corrected test assertion to `result["result"] == "0-1"` to match correct chess notation (black wins = "0-1")
- **Files modified:** `tests/test_normalization.py`
- **Commit:** (included in 3e956bd)

**2. [Rule 2 - Missing validation] Fixed unused import lint errors**
- **Found during:** Final verification
- **Issue:** `pytest` and `pytest_asyncio` were imported but unused in test files
- **Fix:** Removed unused imports from both test files
- **Files modified:** `tests/test_normalization.py`, `tests/test_game_repository.py`
- **Commit:** 6fd7d3e

### Pre-existing Issues (Out of Scope)

Two F821 ruff errors in `app/models/game.py` and `app/models/game_position.py` for forward-reference strings (`"GamePosition"` and `"Game"`) already existed before this plan and already had `# type: ignore[name-defined]` comments. Not introduced by this plan, not fixed (out of scope).

## Commits

| Hash | Message |
|------|---------|
| c38e9d8 | test(02-01): add failing tests for normalization utilities |
| 3e956bd | feat(02-01): ImportJob model, schemas, normalization utilities, and migration |
| c718f56 | test(02-01): add failing tests for game and import job repositories |
| 70dff45 | feat(02-01): game repository, import job repository, and db_session test fixture |
| 6fd7d3e | fix(02-01): remove unused imports from test files |

## Self-Check: PASSED

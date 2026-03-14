---
phase: quick-14
plan: 01
subsystem: testing/database
tags: [testing, database, alembic, conftest, pytest]
dependency_graph:
  requires: []
  provides: [test-db-isolation, auto-migration]
  affects: [tests/conftest.py, app/core/config.py]
tech_stack:
  added: []
  patterns: [alembic-programmatic-upgrade, dependency_overrides-test-db, session-scoped-engine]
key_files:
  created: []
  modified:
    - app/core/config.py
    - .env.example
    - tests/conftest.py
decisions:
  - "Keep postgresql+asyncpg:// URL for alembic (env.py uses async_engine_from_config; psycopg2 not installed)"
  - "Patch settings.DATABASE_URL temporarily during alembic upgrade so env.py picks up test DB URL"
  - "Use engine.sync_engine.dispose() for teardown (no event loop in session fixture teardown)"
metrics:
  duration: 10min
  completed_date: 2026-03-14
---

# Quick Task 14: Set Up Separate Test Database with Auto-Migration Summary

**One-liner:** Dedicated chessalytics_test DB with Alembic auto-migration and FastAPI dependency override routes all test writes away from dev DB.

## What Was Built

All tests now run against `chessalytics_test` instead of the dev `chessalytics` database. Alembic migrations run automatically at pytest session start, and all FastAPI endpoint calls (including ASGITransport-based auth tests) use the test DB via `dependency_overrides[get_async_session]`.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add TEST_DATABASE_URL to config and env files | 0481a0b |
| 2 | Rewrite conftest.py with test engine, auto-migration, session override | c794390 |

## Key Changes

### app/core/config.py
Added `TEST_DATABASE_URL` field to `Settings` class pointing to `chessalytics_test`.

### tests/conftest.py
- **`test_engine` (session-scoped):** Runs `alembic_command.upgrade(cfg, "head")` against the test DB at session start, then creates an async engine. Temporarily patches `settings.DATABASE_URL` so `alembic/env.py`'s `config.set_main_option` picks up the test DB URL. Disposes engine via `engine.sync_engine.dispose()` at teardown.
- **`override_get_async_session` (session-scoped, autouse):** Sets `app.dependency_overrides[get_async_session]` to a generator backed by the test engine. Commit-after-yield (production behavior) so auth tests work correctly.
- **`db_session`:** Now accepts `test_engine` parameter instead of creating its own engine from `settings.DATABASE_URL`.
- **Unchanged:** `disable_dev_auth_bypass`, `starting_board`, `empty_board`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] asyncio.get_event_loop().run_until_complete() fails in teardown**
- **Found during:** Task 2 (first test run)
- **Issue:** Session fixture teardown has no event loop; `asyncio.get_event_loop().run_until_complete(engine.dispose())` raises RuntimeError
- **Fix:** Used `engine.sync_engine.dispose()` which is synchronous and doesn't require an event loop
- **Files modified:** tests/conftest.py

**2. [Rule 1 - Bug] Alembic used psycopg2 URL causing ModuleNotFoundError**
- **Found during:** Task 2 (second test run)
- **Issue:** Plan specified `replace("+asyncpg", "")` to create sync URL, but `alembic/env.py` uses `async_engine_from_config` (asyncpg driver). Only asyncpg is installed; psycopg2 is not.
- **Fix:** Keep `postgresql+asyncpg://` URL for alembic — the env.py handles async internally via `asyncio.run()`. Patch `settings.DATABASE_URL` temporarily so env.py picks up the test DB URL.
- **Files modified:** tests/conftest.py

## Verification

- All 249 tests pass: `uv run pytest tests/ -x -v` — 249 passed, 25 warnings
- Test users written to `chessalytics_test` after test run (confirmed via psql)
- Dev DB `chessalytics` received no new test users from the latest test run
- Test DB schema created by Alembic auto-migration at session start

## Self-Check: PASSED

- app/core/config.py — FOUND with TEST_DATABASE_URL
- .env.example — FOUND with TEST_DATABASE_URL
- tests/conftest.py — FOUND with alembic, test_engine, override_get_async_session
- Commit 0481a0b — FOUND
- Commit c794390 — FOUND

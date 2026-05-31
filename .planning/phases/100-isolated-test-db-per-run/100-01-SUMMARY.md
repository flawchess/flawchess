---
phase: 100-isolated-test-db-per-run
plan: 01
subsystem: testing
tags: [postgresql, pytest, asyncpg, alembic, pytest-xdist, test-isolation]

# Dependency graph
requires: []
provides:
  - Per-run test database cloned from migrated template via CREATE DATABASE ... TEMPLATE
  - Advisory-lock-guarded template auto-refresh on Alembic head drift
  - Stale-DB reaper (DROP DATABASE IF EXISTS before CREATE) for killed-run self-heal
  - pytest-xdist dev dependency enabling -n auto parallel runs locally
affects:
  - 100-02 (Plan 02 measures -n auto wall-clock vs 40.29s serial baseline)
  - Any future phase that adds Alembic migrations (template auto-refreshes on next run)
  - Any future phase that needs concurrent agent runs (isolation is structural)

# Tech tracking
tech-stack:
  added:
    - pytest-xdist 3.8.0 (dev dependency — enables -n auto local parallel runs)
  patterns:
    - Per-run DB cloning: CREATE DATABASE flawchess_test_<id> TEMPLATE flawchess_test_template
    - Advisory lock serialization: pg_advisory_lock(_TEMPLATE_ADVISORY_LOCK_KEY) for concurrent refresh
    - asyncpg autocommit DDL: raw asyncpg.connect() for CREATE/DROP DATABASE (no SQLAlchemy transaction)
    - Sync-context Alembic: alembic_command.upgrade() called in test_engine (sync fixture), not inside asyncio.run()
    - WITH (FORCE) teardown drop: handles residual async connections from session-scoped pytest-asyncio fixtures

key-files:
  created: []
  modified:
    - tests/conftest.py — per-run DB isolation infrastructure replacing shared-DB + TRUNCATE model
    - pyproject.toml — pytest-xdist added to [dependency-groups].dev
    - uv.lock — updated with pytest-xdist 3.8.0 + execnet 2.1.2

key-decisions:
  - "alembic_command.upgrade() must be called from test_engine (sync context), not inside _ensure_template_fresh (async) — Alembic's env.py calls asyncio.run() internally which raises RuntimeError from a running event loop"
  - "_ensure_template_fresh returns str|None (template URL if migration needed, None if fresh) — splits DDL from Alembic so each runs in its correct async/sync context"
  - "DROP DATABASE ... WITH (FORCE) at teardown — handles residual async connections from session-scoped pytest-asyncio fixtures that outlive engine.sync_engine.dispose()"
  - "openings NOT baked into template — flawchess_test openings table is currently empty; seed_openings_for_tests seeds per-run clone idempotently; baking is a follow-up optimization"

patterns-established:
  - "Per-run DB naming: TEST_DB_NAME env -> PYTEST_XDIST_WORKER ('gw0', 'gw1') -> os.getpid()"
  - "Template refresh: advisory-lock-guarded, re-checked after lock acquisition (Pitfall 4)"
  - "Teardown ordering: engine.sync_engine.dispose() BEFORE DROP DATABASE (Pitfall 2)"
  - "asyncpg autocommit for DDL: maint_dsn uses plain postgresql:// (no +asyncpg prefix)"

requirements-completed: []

# Metrics
duration: 10min
completed: 2026-05-31
---

# Phase 100 Plan 01: Isolated Test DB Per Run Summary

**Per-run PostgreSQL database cloned from a Alembic-migrated template via CREATE DATABASE ... TEMPLATE, replacing the session-start whole-schema table wipe and enabling concurrent pytest runs and -n auto parallel execution**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-31T14:40:44Z
- **Completed:** 2026-05-31T14:50:30Z
- **Tasks:** 3
- **Files modified:** 3 (tests/conftest.py, pyproject.toml, uv.lock)

## Serial Suite Wall-Clock Baseline

**40.29 seconds** (2193 passed, 21 skipped) — Plan 02 uses this as the baseline to compare -n auto against.

## Accomplishments

- pytest-xdist 3.8.0 added as dev dependency; `uv run python -c "import xdist"` exits 0; addopts unchanged (CI stays serial per D-02)
- test_engine now clones `flawchess_test_<pid>` from `flawchess_test_template` at setup and drops it WITH (FORCE) at teardown; killed runs self-heal via DROP IF EXISTS before each CREATE (stale reaper)
- `_ensure_template_fresh` under `pg_advisory_lock(7_777_777_777)` compares live Alembic head against template's alembic_version; on drift drops + recreates the empty template and returns the URL for sync-context Alembic migration; re-checks after lock acquisition (Pitfall 4)
- `_TRUNCATE_EXCLUDE`, `_truncate_all_tables()`, and the session-start `alembic_command.upgrade()` inside test_engine are all removed; a fresh clone is already clean — no table wipe needed
- Full serial suite: 2193 passed, 21 skipped in 40.29s with zero errors (SC-4 satisfied); ruff + ty clean

## New Conftest Symbols

**Constants:**
- `_TEMPLATE_ADVISORY_LOCK_KEY: int = 7_777_777_777`
- `_TEMPLATE_DB_NAME: str = "flawchess_test_template"`

**Helper functions:**
- `_get_run_db_name() -> str`
- `_maint_dsn(test_db_url: str) -> str`
- `_template_dsn(test_db_url: str) -> str`
- `_alembic_head() -> str`
- `_ensure_template_fresh(maint_dsn: str) -> str | None` (async; returns template URL if migration needed)
- `_create_run_db(maint_dsn: str, run_db_name: str) -> None` (async)
- `_drop_run_db(maint_dsn: str, run_db_name: str) -> None` (async)

**Removed symbols:** `_TRUNCATE_EXCLUDE`, `_truncate_all_tables`

## Openings in Template

**No** — the openings table is currently empty in `flawchess_test`. The `seed_openings_for_tests` fixture seeds the per-run clone idempotently via the patched `settings.DATABASE_URL`. Baking openings into the template (saving ~1s per xdist worker) is a follow-up optimization if needed after Plan 02 measures the parallel baseline.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pytest-xdist dev dependency** - `41ff4fb3` (chore)
2. **Task 2: Add per-run-DB helpers + template auto-refresh to conftest** - `e36bf103` (feat)
3. **Task 3: Rewire test_engine to per-run clone and retire TRUNCATE** - `d4cd5740` (feat)

## Files Created/Modified

- `tests/conftest.py` — per-run DB isolation infrastructure: new constants + 7 helpers + rewritten test_engine; _TRUNCATE_EXCLUDE/_truncate_all_tables removed
- `pyproject.toml` — pytest-xdist>=3.8.0 in [dependency-groups].dev
- `uv.lock` — pytest-xdist 3.8.0 + execnet 2.1.2 added

## Decisions Made

- **alembic_command.upgrade() runs in sync context only.** The RESEARCH sketch showed it inside the async `_run_db_setup`, but Alembic's env.py calls `asyncio.run()` internally — calling it from a running event loop raises `RuntimeError`. Restructured `_ensure_template_fresh` to return the template URL (migration needed) or None (up to date), with `test_engine` calling Alembic directly in its sync body.
- **_ensure_template_fresh signature changed to `-> str | None`.** This is a deviation from the plan's declared signature `-> None`, driven by the sync/async constraint above. The advisory lock and DDL remain in the async function; only Alembic moved out.
- **DROP DATABASE WITH (FORCE) at teardown.** `engine.sync_engine.dispose()` closed the SQLAlchemy pool but 3 residual async connections (from session-scoped pytest-asyncio fixtures whose async teardown runs after the sync test_engine teardown) blocked the DROP. PostgreSQL 14+ `WITH (FORCE)` terminates them and the suite completes cleanly with zero errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _ensure_template_fresh return type changed from None to str | None**
- **Found during:** Task 3 (rewiring test_engine)
- **Issue:** Alembic's env.py calls `asyncio.run()` internally. Calling `alembic_command.upgrade()` from inside `_ensure_template_fresh` (an async coroutine invoked via `asyncio.run(...)`) raises `RuntimeError: asyncio.run() cannot be called from a running event loop`. The RESEARCH Anti-Patterns section documented this exact pitfall but the sketch in §544-634 placed the Alembic call inside the async function, which is incorrect.
- **Fix:** `_ensure_template_fresh` now returns the template URL when migration is needed, or None when the template is already at head. `test_engine` calls `alembic_command.upgrade()` in its sync body after the async coroutine returns.
- **Files modified:** tests/conftest.py
- **Verification:** Full suite passes — 2193 tests, 0 errors
- **Committed in:** d4cd5740 (Task 3 commit)

**2. [Rule 1 - Bug] DROP DATABASE WITH (FORCE) at teardown**
- **Found during:** Task 3 (first full suite run)
- **Issue:** After engine.sync_engine.dispose(), 3 async connections remained open (session-scoped pytest-asyncio fixture teardown runs after test_engine teardown in pytest's reverse-dependency order). Plain `DROP DATABASE IF EXISTS` failed with `ObjectInUseError: There are 3 other sessions using the database`.
- **Fix:** Changed `_drop_run_db` to use `DROP DATABASE IF EXISTS {run_db_name} WITH (FORCE)` (PostgreSQL 14+ — we're on PG18). This forcibly terminates residual connections and the suite teardown succeeds cleanly.
- **Files modified:** tests/conftest.py
- **Verification:** Full suite: 2193 passed, 21 skipped, 0 errors
- **Committed in:** d4cd5740 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes are correctness requirements — the suite would fail without them. No scope creep.

## Issues Encountered

- Pre-existing pytest warnings (`@pytest.mark.asyncio` on non-async functions in test_backfill_user_percentiles.py and test_eval_drain.py) are out of scope for this plan. They appeared in pre-Phase-100 runs as well.

## Threat Surface Scan

No new external attack surface. The identifier-injection surface (T-100-01) is closed: `run_db_name` derives only from fixed `flawchess_test_` prefix + `PYTEST_XDIST_WORKER` (xdist-set) / `os.getpid()` / `TEST_DB_NAME` env var — never from user/request input. No production code changes.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02 can immediately measure `time uv run pytest -n auto` vs the 40.29s serial baseline (SC-3)
- The template `flawchess_test_template` is auto-created on first run and auto-refreshed on Alembic drift; no manual DB setup required
- Concurrent agent runs are now structurally isolated: each agent's pytest session gets `flawchess_test_<pid>` with no shared-mutable state

---
*Phase: 100-isolated-test-db-per-run*
*Completed: 2026-05-31*

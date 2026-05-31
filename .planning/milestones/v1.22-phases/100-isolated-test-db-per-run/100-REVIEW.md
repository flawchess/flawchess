---
phase: 100-isolated-test-db-per-run
reviewed: 2026-05-31T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - tests/conftest.py
  - tests/test_endgame_zones.py
  - pyproject.toml
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 100: Code Review Report

**Reviewed:** 2026-05-31
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Phase 100 replaces the old session-start `TRUNCATE … RESTART IDENTITY CASCADE` approach with a per-run database cloned from a migrated `flawchess_test_template` via `CREATE DATABASE … TEMPLATE`. The overall design is sound: the advisory-lock-guarded template refresh, `DROP DATABASE … WITH (FORCE)` teardown, and stale-DB self-heal via `DROP DATABASE IF EXISTS` before each clone are all well-conceived. `pyproject.toml` and `test_endgame_zones.py` are clean.

One genuine correctness bug exists in the concurrent xdist path: the `pg_advisory_lock` protecting template refresh is released **before** Alembic finishes migrating the template, so a second worker that unblocks during that window will see an unmigrated template and trigger a second drop+recreate cycle that destroys the first worker's migration target. A dead helper function and an unvalidated identifier are also present.

## Critical Issues

### CR-01: Advisory lock released before Alembic migration completes — concurrent workers race to destroy each other's template

**File:** `tests/conftest.py:162–207`

**Issue:** `pg_advisory_lock` is acquired inside `_ensure_template_fresh` and released in the `inner finally` block at line 204 — before the coroutine returns and, critically, before the **caller** (`test_engine`) runs `alembic_command.upgrade()`. Because `asyncio.run()` disposes the connection when it finishes, the advisory lock is also lost when `asyncio.run(_ensure_template_fresh(…))` returns. A second xdist worker that was blocking on `pg_advisory_lock` will unblock at that point, connect to the template, and call `SELECT version_num FROM alembic_version LIMIT 1` — which raises `UndefinedTableError` because the first worker has not yet finished migrating. The code treats `UndefinedTableError` as `tmpl_version = None`, concludes the template is stale, and **drops it** (line 196) — tearing down the exact database that the first worker's `alembic_command.upgrade()` is actively writing to. The first worker's migration then fails; both workers then attempt to migrate the same freshly created empty template concurrently.

The docstring explicitly describes the intended guarantee: "the others block on the lock, then re-check drift after acquiring it and find the template already up to date." That guarantee cannot be met because the critical section ends before the template is at the Alembic head.

In practice this race window is narrow and only opens on the first run after a schema change, so it manifests as flaky xdist failures — potentially hard to diagnose. Serial CI runs are unaffected.

**Fix:** Restructure so the advisory lock is held through the migration. The simplest compatible approach: have `_ensure_template_fresh` perform the migration itself by taking a boolean flag or by accepting a callback. The Alembic `asyncio.run()` constraint can be worked around by running `alembic_command.upgrade()` via `asyncio.get_event_loop().run_until_complete()` from inside the synchronous `asyncio.run()` throwaway loop — or by using `nest_asyncio`. Alternatively, hold the lock via a **separate, persistent asyncpg connection** that is not closed until after `alembic_command.upgrade()` returns:

```python
# In test_engine (sync fixture):
admin_conn = asyncio.run(_acquire_template_lock_and_prepare(maint))
# admin_conn is left OPEN, keeping the session-level advisory lock held.
try:
    if needs_migration:
        alembic_command.upgrade(alembic_cfg, "head")
finally:
    asyncio.run(_release_lock_and_close(admin_conn))
asyncio.run(_create_run_db(maint, run_db_name))
```

The exact shape depends on how the asyncpg connection lifetime is bridged across sync/async boundaries, but the invariant is: **no other worker may acquire the advisory lock until `alembic_command.upgrade()` returns successfully**.

---

## Warnings

### WR-01: `_template_dsn()` is dead code — defined but never called

**File:** `tests/conftest.py:116–119`

**Issue:** `_template_dsn(test_db_url)` constructs a `postgresql://…/flawchess_test_template` DSN. It is defined at module level but never called. All three places that need the template DSN reconstruct it inline (lines 171–178 pass keyword args directly to `asyncpg.connect`, and line 201 rebuilds the URL inline via `urllib.parse`). The function sits alongside `_maint_dsn` and creates a false impression that it is used symmetrically.

**Fix:** Remove the function. If inline template DSN construction is needed in multiple places in the future, re-introduce it then.

```python
# Delete lines 116–119 entirely:
# def _template_dsn(test_db_url: str) -> str:
#     """Return an asyncpg plain DSN pointing at the template database."""
#     p = urllib.parse.urlparse(test_db_url)
#     return f"postgresql://{p.username}:{p.password}@{p.hostname}:{p.port}/{_TEMPLATE_DB_NAME}"
```

---

### WR-02: `TEST_DB_NAME` env var interpolated directly into DDL without identifier validation

**File:** `tests/conftest.py:94–100` (name derivation) and `tests/conftest.py:220–221`, `237` (DDL usage)

**Issue:** When `TEST_DB_NAME` is set in the environment, its value is used verbatim as the database name in `DROP DATABASE IF EXISTS {run_db_name}` and `CREATE DATABASE {run_db_name} TEMPLATE …`. `asyncpg.execute()` uses PostgreSQL's simple query protocol, which accepts multiple semicolon-separated statements in a single string. A value like `x; DROP DATABASE flawchess_test_template; --` would execute three statements. The code comment correctly identifies this as developer-controlled infrastructure, but the threat model only covers the `PYTEST_XDIST_WORKER` and PID paths; the explicit `TEST_DB_NAME` override has no stated restriction in its docstring and no runtime guard.

A regex validation at the top of `_get_run_db_name()` prevents any accidental misuse (e.g., a CI environment variable containing unexpected characters) and documents the intent clearly:

**Fix:**
```python
import re

_SAFE_DB_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

def _get_run_db_name() -> str:
    explicit = os.environ.get("TEST_DB_NAME")
    if explicit:
        if not _SAFE_DB_NAME_RE.match(explicit):
            raise ValueError(
                f"TEST_DB_NAME {explicit!r} contains unsafe characters. "
                "Use only lowercase letters, digits, and underscores."
            )
        return explicit
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker:
        return f"flawchess_test_{worker}"
    return f"flawchess_test_{os.getpid()}"
```

---

## Info

### IN-01: Teardown lines in `test_engine` lack `try/finally` — `settings.DATABASE_URL` not restored if `dispose()` or `_drop_run_db()` raises

**File:** `tests/conftest.py:312–314`

**Issue:** The teardown block after `yield engine`:

```python
engine.sync_engine.dispose()
asyncio.run(_drop_run_db(maint, run_db_name))
settings.DATABASE_URL = original_url
```

has no `try/finally`. If `engine.sync_engine.dispose()` or `asyncio.run(_drop_run_db(…))` raises an exception, `settings.DATABASE_URL` is left set to `run_db_url` for the remainder of the (already-failing) session. In practice pytest teardown errors are surfaced as warnings and the session exits shortly after, so there is no second test run to be confused by the stale setting. The risk is near-zero in normal operation, but wrapping teardown in a `try/finally` is the hygienic pattern for session-scoped fixtures.

**Fix:**
```python
# Teardown
try:
    engine.sync_engine.dispose()
    asyncio.run(_drop_run_db(maint, run_db_name))
finally:
    settings.DATABASE_URL = original_url
```

---

_Reviewed: 2026-05-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

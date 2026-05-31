# Phase 100: Isolated Test DB Per Run — Research

**Researched:** 2026-05-31
**Domain:** PostgreSQL `CREATE DATABASE ... TEMPLATE`, asyncpg autocommit connections, pytest-xdist worker isolation, Alembic head-drift detection, advisory lock serialization
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01: Auto-refresh template on Alembic head drift**, guarded by `pg_advisory_lock`.
  `conftest` compares live `alembic head` vs template's `alembic_version`; on drift it
  drops + re-migrates `flawchess_test_template`. One run refreshes, others block only on
  the refresh path, not on every run.

- **D-02: Keep CI serial; enable `-n auto` locally only.**
  Per-worker DB mechanism is built regardless. CI keeps serial runs.

- **D-03: Leave benchmark suite (`tests/scripts/benchmarks`, port 5433) untouched.**
  Out of scope. Already `--ignore`'d, targets separate Postgres via read-only role.

### Claude's Discretion

- **DB create/drop mechanism:** dedicated asyncpg autocommit connection inside
  `conftest`'s `test_engine` fixture (connecting to `postgres` maintenance DB), not a
  separate `bin/` hook.
- **Per-run DB naming:** `TEST_DB_NAME` env → `PYTEST_XDIST_WORKER` (`gw0`, `gw1`, ...) →
  process PID. Example: `flawchess_test_gw0`, `flawchess_test_<pid>`.
- **Stale-DB reaper:** `DROP DATABASE IF EXISTS` before each create. Optional `bin/`
  helper not required.
- **xdist dependency:** add `pytest-xdist` as dev dependency.

### Deferred Ideas (OUT OF SCOPE)

- CI `-n auto` — deferred by D-02.
- `bin/` reaper for old `flawchess_test_*` DBs by age — optional nice-to-have.
- Lighter interim (per-session env var, zero source change) — explicitly not taken.

</user_constraints>

---

## Summary

The root cause is two coupled problems: (1) all `pytest` runs share a single `flawchess_test`
database and each run begins by truncating the entire schema with `ACCESS EXCLUSIVE` locks —
the most hostile lock in Postgres, blocking even `SELECT`; and (2) a few fixtures commit with
fixed IDs outside the rollback scope, so removing the truncate alone would downgrade
"deadlock" to "occasional PK collision," not to "safe." The fix must give each run its own
database with its own committed data.

The design chosen is: one migrated `flawchess_test_template` maintained in the dev Postgres,
with each run (and each xdist worker) cloning it via `CREATE DATABASE ... TEMPLATE` at session
start and dropping via `DROP DATABASE IF EXISTS` at teardown. Template refresh (on Alembic
head drift) is guarded by `pg_advisory_lock` so concurrent runs only block on the refresh
path, not on every clone. All of this happens in a dedicated asyncpg autocommit connection
inside the `test_engine` session fixture — no `bin/` pre-hook, no separate process.

**Key measurements confirmed in this session:** 66 migrations take ~1.7s to run against a
fresh empty DB. Cloning a migrated template takes ~0.09s. The current serial suite runs in
41.2s against a live 16-CPU dev box; with 16 xdist workers the theoretical optimum is ~2.5s,
with the realistic estimate (setup overhead + straggler tests) landing around 8–15s.
Baseline for Success Criteria #3 is 41.2s serial.

**Primary recommendation:** Implement per-run DB cloning entirely within `tests/conftest.py`
(~60 lines added, ~25 lines removed). The change surface is concentrated in one fixture
(`test_engine`) and involves no changes to individual test files.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Template creation + migration | pytest `test_engine` fixture (sync) | asyncpg autocommit connection | `CREATE DATABASE` and `alembic upgrade head` both require sync/autocommit context; fixture runs before any test loop starts |
| Per-run DB naming | conftest (OS env read) | None | `PYTEST_XDIST_WORKER` is set by xdist in each worker subprocess; PID fallback for serial runs |
| Advisory lock (template refresh) | asyncpg autocommit connection | None | Session-level advisory locks are per-Postgres-cluster, so any connection to any DB in the cluster works; using the maintenance `postgres` DB is convention |
| Template drift detection | Alembic `ScriptDirectory` (Python, sync) + asyncpg | None | `ScriptDirectory.get_current_head()` is pure-Python; template's `alembic_version` read via asyncpg on a short-lived connection |
| Per-run DB lifecycle (create + drop) | `test_engine` session fixture | asyncpg autocommit connection | Must wrap the full session: create at setup, drop at teardown after engine disposal |
| Connection routing | `override_get_async_session` (session fixture, autouse) | FastAPI DI override | Patches `async_session_maker` in all four modules; only the engine's target DB changes |
| Stale-DB reaper | `DROP DATABASE IF EXISTS` in `test_engine` setup | None | Runs before the new `CREATE`, so killed-run residue is cleaned without separate tooling |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncpg | 0.31.0 (installed) | Raw autocommit connections for `CREATE/DROP DATABASE` and advisory locks | Already a direct project dependency; asyncpg connections are autocommit by default — no `BEGIN` is injected, so DDL works natively [VERIFIED: installed] |
| pytest-asyncio | 1.4.0 (installed) | Session-scoped event loop for async fixtures | Already installed; `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=session` [VERIFIED: installed] |
| pytest-xdist | 3.8.0 (latest on PyPI) | `-n auto` parallel worker distribution | Canonical pytest parallel plugin; exposes `PYTEST_XDIST_WORKER` env var [VERIFIED: PyPI registry, github.com/pytest-dev/pytest-xdist] |
| Alembic `ScriptDirectory` | 1.13+ (installed via alembic) | Read the current migration head without running a process | `ScriptDirectory.from_config(cfg).get_current_head()` is a pure-Python call — no DB connection required [VERIFIED: confirmed working] |

### Installation

```bash
uv add --group dev pytest-xdist
```

---

## Package Legitimacy Audit

| Package | Registry | Source Repo | Disposition |
|---------|----------|-------------|-------------|
| pytest-xdist 3.8.0 | PyPI | github.com/pytest-dev/pytest-xdist | Approved — official pytest-dev org, 8+ years, widely used [VERIFIED: PyPI metadata] |

*slopcheck was unavailable in this environment; the package was verified against the official
pytest-dev GitHub organization and PyPI registry. No `postinstall` scripts. The pytest-dev
org is the canonical namespace for pytest plugins (`pytest-asyncio`, `pytest-cov`, etc. are
all in it).*

---

## Architecture Patterns

### System Architecture Diagram

```
pytest session start (per run / per xdist worker)
        |
        v
test_engine fixture (sync, session-scoped)
        |
        +--[asyncio.run]-->  admin_conn = asyncpg.connect(postgres)
        |                         |
        |                    pg_advisory_lock(TEMPLATE_LOCK_KEY)   ← blocks concurrent refreshes only
        |                         |
        |                    check pg_database for flawchess_test_template
        |                    compare template.alembic_version vs ScriptDirectory.get_current_head()
        |                         |
        |                    [DRIFT or MISSING] --> pg_terminate_backend on template
        |                                       --> DROP DATABASE IF EXISTS flawchess_test_template
        |                                       --> CREATE DATABASE flawchess_test_template TEMPLATE template1
        |                                       --> [patch settings.DATABASE_URL to template]
        |                                       --> alembic_command.upgrade(cfg, "head")  (sync, 66 migrations ~1.7s)
        |                                       --> asyncio.run(seed_openings())  [optional bake]
        |                                       --> [restore settings.DATABASE_URL]
        |                         |
        |                    pg_advisory_unlock(TEMPLATE_LOCK_KEY)
        |                         |
        |                    DROP DATABASE IF EXISTS flawchess_test_<id>   ← stale reaper
        |                    CREATE DATABASE flawchess_test_<id> TEMPLATE flawchess_test_template  (~0.09s)
        |                         |
        |                    admin_conn.close()
        |
        +--[patch settings.DATABASE_URL = run_db_url]
        |
        +--[create_async_engine(run_db_url)]  --> yield engine
        |
tests execute (rollback scope via db_session, or committed via fresh_test_user)
        |
teardown:
        +-- engine.sync_engine.dispose()   ← MUST happen before DROP DATABASE
        |
        +--[asyncio.run]-->  admin_conn = asyncpg.connect(postgres)
        |                    DROP DATABASE IF EXISTS flawchess_test_<id>
        |                    admin_conn.close()
        |
        +--[restore settings.DATABASE_URL]
```

### Recommended Project Structure Changes

```
tests/
├── conftest.py          # MODIFIED: test_engine + new _get_run_db_name + _ensure_template + _create_run_db + _drop_run_db
└── (all other files)    # UNCHANGED
```

### Pattern 1: asyncpg autocommit connection for DDL

asyncpg connections are autocommit by default — there is no implicit `BEGIN` injected. DDL
statements (`CREATE DATABASE`, `DROP DATABASE`) that require being outside a transaction block
work natively via `asyncpg.connect()`.

**Pitfall confirmed:** Using SQLAlchemy's `create_async_engine` with `engine.begin()` raises
`ActiveSQLTransactionError: CREATE DATABASE cannot run inside a transaction block` because
SQLAlchemy always opens an implicit transaction. [VERIFIED: reproduced error experimentally]

```python
# Source: verified experimentally against asyncpg 0.31.0
import asyncio
import asyncpg

async def _admin_ddl(maint_url: str, sql: str) -> None:
    """Run a DDL statement outside any transaction via raw asyncpg."""
    # asyncpg.connect() is autocommit by default — no BEGIN injected
    conn = await asyncpg.connect(maint_url)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()
```

The maintenance URL is derived from `settings.TEST_DATABASE_URL` by replacing the DB name
with `postgres`:

```python
import urllib.parse

def _maint_url(test_db_url: str) -> str:
    """Replace the DB name in TEST_DATABASE_URL with 'postgres' for DDL operations."""
    parsed = urllib.parse.urlparse(test_db_url)
    # Replace the asyncpg+ scheme prefix — asyncpg.connect() takes a plain postgresql:// URL
    # or accepts keyword args; simplest to just pass dsn without scheme prefix
    return f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"
```

### Pattern 2: Per-run DB naming

```python
# Source: CONTEXT.md Claude's Discretion + PYTEST_XDIST_WORKER documentation
import os

def _get_run_db_name() -> str:
    """Derive the per-run DB name from environment context."""
    explicit = os.environ.get("TEST_DB_NAME")
    if explicit:
        return explicit
    worker = os.environ.get("PYTEST_XDIST_WORKER")  # "gw0", "gw1", etc.
    if worker:
        return f"flawchess_test_{worker}"
    return f"flawchess_test_{os.getpid()}"
```

### Pattern 3: Template drift detection

```python
# Source: verified experimentally (ScriptDirectory.get_current_head and asyncpg query)
import asyncio
import asyncpg
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory

def _get_alembic_head() -> str:
    """Return the current alembic head revision from the migration scripts."""
    cfg = AlembicConfig("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    assert head is not None, "No alembic head found — broken migration chain"
    return head

async def _get_template_version(template_db_url: str) -> str | None:
    """Return the alembic_version in the template DB, or None if absent."""
    conn = await asyncpg.connect(template_db_url)
    try:
        return await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
    except asyncpg.UndefinedTableError:
        return None
    finally:
        await conn.close()

async def _template_needs_refresh(maint_url: str, template_name: str, head: str) -> bool:
    """Return True if template is missing or its alembic_version != head."""
    admin = await asyncpg.connect(maint_url)
    try:
        exists = await admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", template_name
        )
    finally:
        await admin.close()
    if not exists:
        return True
    # Template exists: connect to it and check its alembic_version
    parsed = urllib.parse.urlparse(maint_url)
    tmpl_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/{template_name}"
    version = await _get_template_version(tmpl_url)
    return version != head
```

### Pattern 4: Advisory lock for concurrent refresh serialization

`pg_advisory_lock(key)` is a session-level, cluster-wide (not per-database) exclusive lock.
It blocks until the lock is available, then returns. `pg_advisory_unlock(key)` releases it.
A connection close also releases all session-level advisory locks held by that connection.

```python
# Source: verified experimentally against asyncpg 0.31.0 on PostgreSQL 18
TEMPLATE_ADVISORY_LOCK_KEY: int = 7_777_777_777  # fixed constant; document in conftest

async def _ensure_template_fresh(maint_url: str) -> None:
    """Bootstrap or refresh flawchess_test_template under advisory lock."""
    head = _get_alembic_head()
    admin = await asyncpg.connect(maint_url)
    try:
        await admin.execute(f"SELECT pg_advisory_lock({TEMPLATE_ADVISORY_LOCK_KEY})")
        try:
            # Re-check AFTER lock in case another run refreshed while we waited
            needs_refresh = await _check_drift(admin, head)
            if needs_refresh:
                await _do_refresh(admin, head)  # terminate connections, drop, create, migrate
        finally:
            await admin.execute(f"SELECT pg_advisory_unlock({TEMPLATE_ADVISORY_LOCK_KEY})")
    finally:
        await admin.close()
```

**Important:** The re-check after acquiring the lock is required. Without it, N concurrent
runs that all see a stale template would each attempt to drop + remigrate it. [VERIFIED:
advisory lock behavior confirmed experimentally]

### Pattern 5: Terminating connections before DROP/CLONE

`DROP DATABASE` and `CREATE DATABASE ... TEMPLATE` both fail if connections to the source DB
exist. [VERIFIED: reproduced `ObjectInUseError` experimentally]

For the template (at refresh time only — the template should have no connections during normal
runs since only the `_ensure_template_fresh` function ever connects to it):

```python
async def _terminate_template_connections(admin: asyncpg.Connection, template_name: str) -> None:
    """Terminate all backends connected to the template DB before DROP/CLONE source."""
    await admin.execute(
        """SELECT pg_terminate_backend(pid)
           FROM pg_stat_activity
           WHERE datname = $1 AND pid <> pg_backend_pid()""",
        template_name,
    )
```

For the per-run DB at teardown: `engine.sync_engine.dispose()` closes SQLAlchemy's connection
pool (all connections to the per-run DB). After dispose, `DROP DATABASE IF EXISTS` succeeds.
[VERIFIED: engine dispose is the correct teardown ordering]

### Pattern 6: alembic upgrade against template requires `settings.DATABASE_URL` patch

**Critical finding confirmed experimentally.** `alembic/env.py` line 26 does:
```python
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```
This overwrites whatever URL was set on the `AlembicConfig` object before calling
`alembic_command.upgrade`. The existing `test_engine` fixture works because it patches
`settings.DATABASE_URL = settings.TEST_DATABASE_URL` before calling Alembic. To migrate the
template, the same pattern applies: temporarily patch `settings.DATABASE_URL` to the template
URL, run Alembic, then restore.

```python
# Correct pattern (mirrors existing conftest.py test_engine lines 90-94):
original_url = settings.DATABASE_URL
settings.DATABASE_URL = template_url  # e.g. .../flawchess_test_template
try:
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", template_url)
    alembic_command.upgrade(alembic_cfg, "head")
finally:
    settings.DATABASE_URL = original_url
```

**Do NOT skip the `settings.DATABASE_URL` patch** — Alembic's env.py will silently migrate
the wrong database (whatever `settings.DATABASE_URL` points to at call time). [VERIFIED:
experimentally confirmed wrong-DB migration when patch is absent]

### Pattern 7: asyncio.run() isolation for DDL and Alembic

All async DB work in `test_engine` (a sync fixture) runs via `asyncio.run()`. asyncpg
connections are event-loop-bound; each `asyncio.run()` call creates a fresh loop. The existing
conftest already uses this pattern for `_truncate_all_tables` with the note "asyncpg pools are
event-loop-bound." [VERIFIED: current conftest.py lines 98-101]

The new code wraps the full admin DDL sequence in a single `asyncio.run()` call:

```python
# test_engine fixture (sync):
asyncio.run(_bootstrap_run_db(maint_url, template_name, run_db_name, head))
# ... create engine ...
yield engine
# teardown:
engine.sync_engine.dispose()  # MUST dispose before drop
asyncio.run(_drop_run_db(maint_url, run_db_name))
```

### Pattern 8: xdist worker detection

`PYTEST_XDIST_WORKER` is set by pytest-xdist in each worker subprocess to values like `gw0`,
`gw1`, etc. It is `None` (unset) in the controller process and in serial (non-xdist) runs.
[ASSUMED — standard xdist behavior, not verified in this session against xdist 3.8.0 docs
specifically, but consistent with all known xdist versions]

With `asyncio_default_fixture_loop_scope = "session"` (set in `pyproject.toml`), each xdist
worker subprocess has its own pytest session, its own event loop, and its own
session-scoped fixtures. The `test_engine` fixture runs once per worker and creates a
separate per-worker DB. [VERIFIED: confirmed via analysis of subprocess isolation model]

### Anti-Patterns to Avoid

- **SQLAlchemy engine for CREATE/DROP DATABASE:** Always raises
  `ActiveSQLTransactionError: CREATE DATABASE cannot run inside a transaction block`
  because SQLAlchemy wraps every connection in a transaction. Use raw `asyncpg.connect()`
  instead. [VERIFIED: error reproduced experimentally]

- **Calling `alembic_command.upgrade()` from within a running asyncio event loop:**
  `alembic/env.py` calls `asyncio.run()` internally, which raises
  `RuntimeError: asyncio.run() cannot be called from a running event loop`. Alembic must
  be invoked from a sync context (the `test_engine` fixture is sync). [VERIFIED: error
  reproduced experimentally]

- **Not patching `settings.DATABASE_URL` before Alembic:** env.py overwrites the config
  URL with `settings.DATABASE_URL`. The patch is mandatory. [VERIFIED]

- **Dropping per-run DB before disposing the engine:** `DROP DATABASE` fails with
  `ObjectInUseError: database "X" is being accessed by other users`. The engine must be
  disposed first. [VERIFIED]

- **Cloning template while connections to template exist:** `CREATE DATABASE ... TEMPLATE`
  fails with `ObjectInUseError: source database "X" is being accessed by other users`.
  The template must have zero active connections before cloning. Since only
  `_ensure_template_fresh` ever connects to the template (and it closes its connection
  before the clone step), this is naturally satisfied as long as the advisory-lock pattern
  is respected. [VERIFIED]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel test distribution | Custom work-queue dispatcher | `pytest-xdist` `-n auto` | xdist handles worker process management, test assignment, `PYTEST_XDIST_WORKER` naming, session fixture lifecycle per worker |
| Mutual exclusion across processes | File locks, semaphores | `pg_advisory_lock` | Advisory locks are managed by the same Postgres that already holds the data; no external locking daemon needed |
| Template migration | Custom schema-copy SQL | `alembic_command.upgrade()` | Existing migration chain is the source of truth; re-running against a fresh DB is 1.7s and completely reliable |

---

## Common Pitfalls

### Pitfall 1: alembic env.py overwrites AlembicConfig URL

**What goes wrong:** You call `alembic_cfg.set_main_option("sqlalchemy.url", template_url)` and then `alembic_command.upgrade(alembic_cfg, "head")`, but migrations run against `settings.DATABASE_URL` (the dev DB), not the template. No error is raised; the wrong DB is silently migrated.

**Why it happens:** `alembic/env.py` line 26: `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)` executes at env.py load time and overwrites the config object.

**How to avoid:** Always patch `settings.DATABASE_URL` to the target URL before calling `alembic_command.upgrade()`, and restore it in a `finally` block. [VERIFIED]

**Warning signs:** Template has no tables after "successful" migration; or dev DB gets an extra empty-schema migration run.

### Pitfall 2: DROP DATABASE blocked by open connections

**What goes wrong:** Teardown issues `DROP DATABASE IF EXISTS flawchess_test_<id>` but the SQLAlchemy engine still has pool connections open, causing `ObjectInUseError`.

**Why it happens:** SQLAlchemy's async connection pool keeps idle connections alive until explicitly disposed.

**How to avoid:** Always call `engine.sync_engine.dispose()` before the DROP. The `test_engine` fixture teardown sequence must be: `(1) dispose engine, (2) DROP DATABASE`. [VERIFIED]

### Pitfall 3: CREATE DATABASE ... TEMPLATE fails when template has connections

**What goes wrong:** `ObjectInUseError: source database "flawchess_test_template" is being accessed by other users` during template clone.

**Why it happens:** If any process (a previous run that didn't close cleanly, a manual psql session, etc.) is connected to the template DB, Postgres refuses to clone it.

**How to avoid:** During template refresh, call `pg_terminate_backend` on all backends connected to the template before `DROP DATABASE` and `CREATE DATABASE`. During normal runs, the template should have no connections (only the `_ensure_template_fresh` function ever connects to it and it closes the connection before cloning). [VERIFIED: pg_terminate_backend approach confirmed working]

### Pitfall 4: Advisory lock not re-checked after acquisition

**What goes wrong:** N concurrent runs see a stale template, all acquire the advisory lock in sequence, and all try to drop + remigrate it — causing the second run to fail with `DROP DATABASE IF EXISTS` succeeding but `CREATE DATABASE` racing.

**Why it happens:** The drift check happened before the lock was acquired. By the time the lock is acquired, the first run may have already refreshed the template.

**How to avoid:** Re-check drift AFTER acquiring the advisory lock. If the re-check shows the template is now up to date, skip the refresh and proceed directly to cloning. [VERIFIED: advisory lock mutual exclusion confirmed]

### Pitfall 5: Module-scoped `seeded_user` fixture interacts with xdist module distribution

**What goes wrong:** With `--dist=load` (xdist default), tests from the same module generally land on the same worker. The `seeded_user` module-scoped fixture commits test data to the per-worker DB. This is safe: each worker has its own isolated DB. No collision.

**Why this is NOT a problem:** Each worker's per-run DB is completely separate. `seeded_user` data committed to worker `gw0`'s DB is invisible to `gw1`'s DB. The only case where this would be an issue is if the same module's tests somehow split across workers — but even then, each worker's seeded_user creates a fresh user with a unique UUID email.

**Warning signs:** Not applicable — this pattern is safe. Document it explicitly so implementers don't add unnecessary cross-worker coordination.

### Pitfall 6: `test_eval_drain.py` fixed user IDs with per-run DB

**What was a problem:** `_TEST_USER_ID = 99100` / `_TEST_USER_ID_2 = 99101` were fixed constants to avoid FK collisions between runs. With the old shared `flawchess_test` DB, these could collide across concurrent runs.

**How per-run DBs fix it:** Each run's DB is freshly cloned — no residue from previous runs. The fixed IDs are safe because no two runs share a DB. The startup `TRUNCATE ... CASCADE` was only needed to wipe these IDs between runs; with per-run DBs, the cleanup is structural.

**Action:** No change needed to `test_eval_drain.py`. The fixed IDs continue to work; they just can't collide anymore.

### Pitfall 7: `seed_openings_for_tests` runs with patched `settings.DATABASE_URL`

**What happens:** `seed_openings_for_tests` (session-scoped autouse in `test_seed_openings.py`) calls `asyncio.run(seed_openings())`, which uses `settings.DATABASE_URL`. Since `test_engine` patches `settings.DATABASE_URL` to the per-run DB URL, `seed_openings` seeds the per-run DB. This is correct behavior.

**Option (recommended):** Bake openings into the template at template creation time. Then the clone already has 3641 rows, and `seed_openings_for_tests` becomes a no-op idempotent call. Tests in `test_seed_openings.py` that check row counts will pass because the rows are already there.

**Why it's safe:** `seed_openings()` uses `INSERT ... ON CONFLICT DO UPDATE` — it is idempotent.

---

## Code Examples

### Full `test_engine` replacement sketch

```python
# Source: synthesized from verified patterns; exact implementation for planner reference

import asyncio
import os
import urllib.parse

import asyncpg
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# Fixed advisory lock key — reserved for flawchess test template refresh
_TEMPLATE_ADVISORY_LOCK_KEY: int = 7_777_777_777
_TEMPLATE_DB_NAME: str = "flawchess_test_template"


def _get_run_db_name() -> str:
    explicit = os.environ.get("TEST_DB_NAME")
    if explicit:
        return explicit
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker:
        return f"flawchess_test_{worker}"
    return f"flawchess_test_{os.getpid()}"


def _maint_dsn(test_db_url: str) -> str:
    """Return asyncpg DSN pointing at 'postgres' maintenance DB."""
    p = urllib.parse.urlparse(test_db_url)
    return f"postgresql://{p.username}:{p.password}@{p.hostname}:{p.port}/postgres"


def _template_dsn(test_db_url: str) -> str:
    p = urllib.parse.urlparse(test_db_url)
    return f"postgresql://{p.username}:{p.password}@{p.hostname}:{p.port}/{_TEMPLATE_DB_NAME}"


def _alembic_head() -> str:
    cfg = AlembicConfig("alembic.ini")
    head = ScriptDirectory.from_config(cfg).get_current_head()
    assert head is not None
    return head


async def _run_db_setup(maint_dsn: str, run_db_name: str) -> None:
    """Ensure template is fresh, then create per-run DB from it."""
    head = _alembic_head()
    admin = await asyncpg.connect(maint_dsn)
    try:
        # --- Template refresh under advisory lock ---
        await admin.execute(f"SELECT pg_advisory_lock({_TEMPLATE_ADVISORY_LOCK_KEY})")
        try:
            tmpl_exists = await admin.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", _TEMPLATE_DB_NAME
            )
            tmpl_version = None
            if tmpl_exists:
                p = urllib.parse.urlparse(maint_dsn)
                tmpl_conn = await asyncpg.connect(
                    host=p.hostname, port=p.port,
                    user=p.username, password=p.password,
                    database=_TEMPLATE_DB_NAME,
                )
                try:
                    tmpl_version = await tmpl_conn.fetchval(
                        "SELECT version_num FROM alembic_version LIMIT 1"
                    )
                except asyncpg.UndefinedTableError:
                    pass
                finally:
                    await tmpl_conn.close()

            if not tmpl_exists or tmpl_version != head:
                # Terminate any lingering connections to template, then drop+recreate
                await admin.execute(
                    """SELECT pg_terminate_backend(pid) FROM pg_stat_activity
                       WHERE datname = $1 AND pid <> pg_backend_pid()""",
                    _TEMPLATE_DB_NAME,
                )
                await admin.execute(f"DROP DATABASE IF EXISTS {_TEMPLATE_DB_NAME}")
                await admin.execute(
                    f"CREATE DATABASE {_TEMPLATE_DB_NAME} TEMPLATE template1"
                )
                # Migrate template (must patch settings.DATABASE_URL — see Pitfall 1)
                tmpl_url = _template_dsn_from_maint(maint_dsn)
                original = settings.DATABASE_URL
                settings.DATABASE_URL = tmpl_url
                try:
                    alembic_cfg = AlembicConfig("alembic.ini")
                    alembic_cfg.set_main_option("sqlalchemy.url", tmpl_url)
                    alembic_command.upgrade(alembic_cfg, "head")
                    # Optionally: asyncio.run(seed_openings()) here to bake openings
                finally:
                    settings.DATABASE_URL = original
        finally:
            await admin.execute(f"SELECT pg_advisory_unlock({_TEMPLATE_ADVISORY_LOCK_KEY})")

        # --- Per-run DB: stale reaper + create ---
        await admin.execute(f"DROP DATABASE IF EXISTS {run_db_name}")
        await admin.execute(
            f"CREATE DATABASE {run_db_name} TEMPLATE {_TEMPLATE_DB_NAME}"
        )
    finally:
        await admin.close()


async def _run_db_teardown(maint_dsn: str, run_db_name: str) -> None:
    admin = await asyncpg.connect(maint_dsn)
    try:
        await admin.execute(f"DROP DATABASE IF EXISTS {run_db_name}")
    finally:
        await admin.close()


@pytest.fixture(scope="session")
def test_engine():
    original_url = settings.DATABASE_URL
    run_db_name = _get_run_db_name()
    maint = _maint_dsn(settings.TEST_DATABASE_URL)

    # asyncpg is event-loop-bound; use a throwaway loop (same as old _truncate_all_tables)
    asyncio.run(_run_db_setup(maint, run_db_name))

    p = urllib.parse.urlparse(settings.TEST_DATABASE_URL)
    run_db_url = f"postgresql+asyncpg://{p.username}:{p.password}@{p.hostname}:{p.port}/{run_db_name}"

    settings.DATABASE_URL = run_db_url
    engine = create_async_engine(run_db_url, echo=False)

    yield engine

    engine.sync_engine.dispose()  # MUST precede DROP DATABASE
    asyncio.run(_run_db_teardown(maint, run_db_name))
    settings.DATABASE_URL = original_url
```

### Reading Alembic head (verified)

```python
# Source: verified against alembic 1.13+ installed in project
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory

cfg = AlembicConfig("alembic.ini")
head = ScriptDirectory.from_config(cfg).get_current_head()
# Returns: '02099d78ce65' (current head as of 2026-05-31)
```

### xdist per-worker DB name detection (confirmed pattern)

```python
# Source: CONTEXT.md, xdist documentation pattern [ASSUMED for exact env var name in xdist 3.8.0]
import os
worker = os.environ.get("PYTEST_XDIST_WORKER")  # "gw0", "gw1", ..., or None if serial
```

---

## Runtime State Inventory

Not applicable: greenfield addition to the test infra only. No data migration required.

The existing `flawchess_test` database remains intact and is NOT dropped or renamed — only the
conftest is updated to use per-run clones instead of it. After Phase 100 merges, `flawchess_test`
will no longer be used by the test suite (no test run points to it anymore), but it can be
left in place or manually dropped.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shared `flawchess_test` + startup TRUNCATE ... CASCADE | Per-run DB cloned from template | Phase 100 | Enables concurrent agent runs + `pytest -n auto`; removes ACCESS EXCLUSIVE contention |
| `RESTART IDENTITY CASCADE` to reset sequences | Fresh clone starts with clean sequences | Phase 100 | Deterministic IDs within a run without cross-run truncation |
| `_TRUNCATE_EXCLUDE` to preserve reference data | Reference data baked into template | Phase 100 | openings table in every per-run clone without separate seed step |

**Removed:**
- `_truncate_all_tables()` function and its `asyncio.run()` call in `test_engine`
- `_TRUNCATE_EXCLUDE` frozenset (no longer needed; reference data baked into template)
- `alembic_command.upgrade()` in `test_engine` (replaced by template bootstrap check)

**Added:**
- `_get_run_db_name()` helper
- `_run_db_setup()` async helper (template check + per-run clone)
- `_run_db_teardown()` async helper
- `TEMPLATE_ADVISORY_LOCK_KEY` constant
- `pytest-xdist` in `[dependency-groups.dev]`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.4.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest -x --tb=short -q` |
| Full suite command | `uv run pytest --tb=short` |
| Parallel run command | `uv run pytest -n auto` (after Phase 100) |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command |
|-----|----------|-----------|-------------------|
| SC-1 | Two concurrent `pytest` runs complete without deadlock or data corruption | Manual (run two terminals simultaneously) | n/a — HUMAN-UAT |
| SC-2 | `TRUNCATE ... RESTART IDENTITY CASCADE` removed; per-run DB created from template | Automated — run suite and verify no TRUNCATE in logs | `uv run pytest -x -q` (plus grep conftest for TRUNCATE: must be 0) |
| SC-3 | `pytest -n auto` runs green and faster than 41.2s baseline | Automated measurement | `time uv run pytest -n auto` — record wall clock vs 41.2s |
| SC-4 | ruff / ty / pytest all green | Automated | `uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -x` |
| SC-5 | Template refresh on Alembic drift documented | Manual review | Verify `_TEMPLATE_ADVISORY_LOCK_KEY` comment explains mechanism |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_zobrist.py -x -q` (fast, no DB)
- **Full suite:** `uv run pytest -x` (before wave merge)
- **Parallel gate:** `time uv run pytest -n auto` (once, records SC-3 wall clock)

### Wave 0 Gaps

No new test files needed — Phase 100 modifies `conftest.py` and its correctness is validated
by the existing 2211-test suite passing under the new infrastructure. The acceptance criteria
(SC-1 concurrent-run HUMAN-UAT; SC-3 wall-clock measurement) are verification steps, not
test files.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (Docker) | All DB operations | ✓ | 18 (via docker compose) | None — required |
| asyncpg | Admin DDL connections | ✓ | 0.31.0 | None — project dependency |
| pytest-asyncio | Session loop scope | ✓ | 1.4.0 | None — already installed |
| pytest-xdist | `-n auto` parallel runs | ✗ | — (not installed) | Serial runs still work; install via `uv add --group dev pytest-xdist` |
| Alembic `ScriptDirectory` | Drift detection | ✓ | alembic 1.13+ | None — project dependency |

**Missing dependencies with no fallback:** pytest-xdist (but the phase works in serial mode without it; only SC-3 parallel timing requires it).

---

## Security Domain

Not applicable. This is internal test infrastructure with no external attack surface, no
user data, and no production code changes.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `PYTEST_XDIST_WORKER` env var is set to `"gw0"`, `"gw1"`, etc. in xdist 3.8.0 workers | Pattern 2 (naming), Architecture Diagram | DB naming collision if env var name changed; unlikely given this is a stable xdist API |
| A2 | `pytest -n auto` respects module-scope boundaries sufficiently that `seeded_user` (module-scoped) does not get torn down and re-created mid-module | Architecture Patterns | If wrong, seeded_user tests would fail; fixable by switching to `--dist=loadscope` |
| A3 | `DROP DATABASE IF EXISTS` with `WITH (FORCE)` option (PG14+) is available if needed to forcibly terminate connections at drop time | Teardown | Not needed given engine.dispose() pattern; `WITH (FORCE)` is a nice-to-have fallback |

---

## Open Questions

1. **Baking openings into template — required or optional?**
   - What we know: `flawchess_test` currently has 3641 openings rows; `seed_openings_for_tests`
     seeds them per-session; the function is idempotent.
   - What's unclear: Whether the planner should bake openings into the template during
     `_run_db_setup` (by calling `seed_openings()` after Alembic against the template) or
     leave `seed_openings_for_tests` as-is (it will still fire per-worker and seed the
     per-run DB, which works fine).
   - Recommendation: Bake into template. It removes per-worker seed overhead (~1s/worker for
     16 workers = ~16s savings) and keeps the `_TRUNCATE_EXCLUDE` intent without the truncate.

2. **`WITH (FORCE)` on DROP DATABASE — needed?**
   - What we know: `DROP DATABASE IF EXISTS <name>` is sufficient when `engine.sync_engine.dispose()` is called first.
   - What's unclear: Whether a force-drop fallback is needed for edge cases (hung connections from killed workers).
   - Recommendation: Omit for now. The stale-DB reaper (`DROP IF EXISTS` at setup) handles killed runs. If `DROP` fails at teardown, the next run's reaper cleans it up.

---

## Sources

### Primary (HIGH confidence)

- Experimental verification on PostgreSQL 18 + asyncpg 0.31.0 running locally — all code
  patterns marked [VERIFIED] were executed and confirmed in this research session.
- `/home/aimfeld/Projects/Python/flawchess/tests/conftest.py` — existing fixture structure
  (lines 50-108 for test_engine and _truncate_all_tables patterns).
- `/home/aimfeld/Projects/Python/flawchess/alembic/env.py` — confirmed env.py overwrites
  `sqlalchemy.url` from `settings.DATABASE_URL` (line 26).
- `/home/aimfeld/Projects/Python/flawchess/app/core/config.py` — `TEST_DATABASE_URL` uses
  postgres superuser (no privilege gap for CREATE/DROP DATABASE).

### Secondary (MEDIUM confidence)

- SEED-031 spec — `.planning/seeds/SEED-031-isolated-test-db-per-run-for-concurrent-and-parallel-pytest.md`
- CONTEXT.md decisions — `.planning/phases/100-isolated-test-db-per-run/100-CONTEXT.md`
- PyPI registry for pytest-xdist 3.8.0 (github.com/pytest-dev/pytest-xdist) [VERIFIED: registry]

### Tertiary (LOW confidence)

- PYTEST_XDIST_WORKER env var name in xdist 3.8.0 [ASSUMED — consistent across all versions
  based on training data, but not verified against xdist 3.8.0 docs in this session]

---

## Metadata

**Confidence breakdown:**
- asyncpg autocommit DDL patterns: HIGH — experimentally verified
- Alembic env.py URL override: HIGH — experimentally verified
- Template clone timing (~0.09s): HIGH — measured on this machine
- Migration timing (~1.7s for 66 migrations): HIGH — measured
- xdist worker env var name: MEDIUM — training knowledge, consistent across versions
- `-n auto` wall-clock estimate (8–15s): LOW — SEED-031 estimate; must be measured per SC-3

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (stable infra; asyncpg 0.31.0 / pytest-asyncio 1.4.0 / xdist 3.8.0 are unlikely to change the relevant APIs)

---

## Project Constraints (from CLAUDE.md)

| Constraint | Impact on Phase 100 |
|------------|---------------------|
| No SQLite — asyncpg only | All test DB operations use asyncpg + PostgreSQL. The per-run DB mechanism uses raw asyncpg for DDL (CREATE/DROP DATABASE) and SQLAlchemy asyncpg dialect for test sessions. |
| "No dev DB reset in plans" (MEMORY.md) | Plans must not gate verification on `bin/reset_db.sh`. Phase 100 verification runs against the existing dev DB with the existing `flawchess_test` present; the new per-run DB mechanism creates separate `flawchess_test_<id>` DBs alongside it. |
| `uv run ty check` zero errors | New conftest code must include return type annotations on all functions. |
| `uv run ruff format + check` clean | New conftest code must be formatted before commit. |
| SQLAlchemy 2.x async API only | `create_async_engine`, `async_sessionmaker`, `AsyncSession` — no sync SQLAlchemy for DB operations (raw asyncpg is the exception for DDL only). |
| No magic numbers | `_TEMPLATE_ADVISORY_LOCK_KEY = 7_777_777_777` must be a named constant with a comment explaining its purpose. |
| Real-Postgres test policy | Confirmed: no SQLite, no in-memory substitutes. All tests continue to use the Docker PostgreSQL 18 instance on port 5432. |

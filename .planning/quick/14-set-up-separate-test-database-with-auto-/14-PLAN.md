---
phase: quick-14
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/core/config.py
  - .env
  - .env.example
  - tests/conftest.py
autonomous: true
requirements: [TEST-DB-01]

must_haves:
  truths:
    - "Tests run against chessalytics_test database, not chessalytics"
    - "Alembic migrations run automatically on test DB at session start"
    - "ASGITransport tests (auth/register) write to test DB, not dev DB"
    - "db_session fixture uses test DB engine with per-test rollback"
  artifacts:
    - path: "app/core/config.py"
      provides: "TEST_DATABASE_URL setting"
      contains: "TEST_DATABASE_URL"
    - path: ".env.example"
      provides: "TEST_DATABASE_URL example"
      contains: "TEST_DATABASE_URL"
    - path: "tests/conftest.py"
      provides: "Test DB engine, auto-migration, session override"
      contains: "alembic"
  key_links:
    - from: "tests/conftest.py"
      to: "app/core/config.py"
      via: "settings.TEST_DATABASE_URL"
      pattern: "settings\\.TEST_DATABASE_URL"
    - from: "tests/conftest.py"
      to: "app/core/database.py"
      via: "dependency_overrides[get_async_session]"
      pattern: "dependency_overrides.*get_async_session"
---

<objective>
Set up a separate test database (chessalytics_test) with automatic Alembic migration so integration tests never leak data into the dev database.

Purpose: Tests currently write to the dev DB (chessalytics) via ASGITransport — auth tests register real users that persist. This was the root cause of quick-13. A dedicated test DB with auto-migration solves this permanently.

Output: Updated config, .env files, and conftest.py that routes all test DB access to chessalytics_test.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/core/config.py
@app/core/database.py
@tests/conftest.py
@tests/test_auth.py
@alembic/env.py
@alembic.ini

<interfaces>
<!-- Key imports the executor needs -->

From app/core/config.py:
```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/chessalytics"
    # ... other fields
settings = Settings()
```

From app/core/database.py:
```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
        await session.commit()
```

From app/main.py:
```python
app  # FastAPI instance, used for dependency_overrides
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add TEST_DATABASE_URL to config and env files</name>
  <files>app/core/config.py, .env, .env.example</files>
  <action>
1. In `app/core/config.py`, add a `TEST_DATABASE_URL` field to the `Settings` class:
   ```python
   TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chessalytics_test"
   ```
   Place it right after `DATABASE_URL`.

2. In `.env`, add:
   ```
   TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/chessalytics_test
   ```

3. In `.env.example`, add:
   ```
   TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/chessalytics_test
   ```
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run python -c "from app.core.config import settings; assert 'chessalytics_test' in settings.TEST_DATABASE_URL; print('OK')"</automated>
  </verify>
  <done>Settings.TEST_DATABASE_URL is accessible and defaults to chessalytics_test DB</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite conftest.py to use test DB with auto-migration and session override</name>
  <files>tests/conftest.py</files>
  <action>
Rewrite `tests/conftest.py` to:

1. **Add a session-scoped `test_engine` fixture** that:
   - Creates an async engine from `settings.TEST_DATABASE_URL`
   - Runs `alembic.command.upgrade(alembic_cfg, "head")` programmatically against the test DB at session start (use `alembic.config.Config` pointed at the project's `alembic.ini`, override `sqlalchemy.url` with `settings.TEST_DATABASE_URL` — but use the NON-async URL variant `postgresql://` instead of `postgresql+asyncpg://` for alembic's sync migration runner)
   - Yields the engine
   - Disposes the engine at teardown

   For the Alembic migration, convert the URL: replace `postgresql+asyncpg://` with `postgresql://` since `alembic.command.upgrade` uses synchronous connections. Use:
   ```python
   from alembic.config import Config as AlembicConfig
   from alembic import command as alembic_command

   alembic_cfg = AlembicConfig("alembic.ini")
   sync_url = settings.TEST_DATABASE_URL.replace("+asyncpg", "")
   alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
   alembic_command.upgrade(alembic_cfg, "head")
   ```

2. **Add a session-scoped autouse `override_get_async_session` fixture** that:
   - Creates an `async_sessionmaker` bound to the test engine
   - Defines an async generator that yields a session from this maker (with commit after yield, matching production behavior)
   - Sets `app.dependency_overrides[get_async_session] = test_session_generator`
   - At teardown, removes the override
   - This ensures ALL FastAPI endpoint calls (including ASGITransport-based auth tests) use the test DB

3. **Update `db_session` fixture** to use the test engine (accept `test_engine` as parameter):
   - Same rollback-per-test pattern as before, but using `test_engine` instead of creating its own engine from `settings.DATABASE_URL`

4. **Keep existing fixtures unchanged**: `disable_dev_auth_bypass`, `starting_board`, `empty_board`

Important: The `override_get_async_session` fixture must import `get_async_session` from `app.core.database` and `app` from `app.main` — same imports used in the existing `disable_dev_auth_bypass` fixture.

Important: The session override generator must NOT use the rollback pattern (that's only for `db_session`). The override should behave like production — commit after yield — so that ASGITransport tests (register, login) work correctly with real DB writes to the test DB.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/ -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>All tests pass using chessalytics_test database. No writes to chessalytics dev DB. Auth tests register users in test DB only.</done>
</task>

</tasks>

<verification>
1. `uv run pytest tests/ -x -v` — all tests pass
2. After running tests, verify no new test users in dev DB: `psql chessalytics -c "SELECT id, email FROM \"user\" WHERE email LIKE '%@example.com' ORDER BY id DESC LIMIT 5;"` — should show no NEW entries (existing leaked ones from before are expected)
3. Verify test users exist in test DB: `psql chessalytics_test -c "SELECT id, email FROM \"user\" WHERE email LIKE '%@example.com' ORDER BY id DESC LIMIT 5;"` — should show recently created test users
</verification>

<success_criteria>
- TEST_DATABASE_URL setting exists and points to chessalytics_test
- Alembic migrations run automatically on test DB when pytest starts
- All existing tests pass without modification (except conftest.py)
- ASGITransport-based tests (test_auth.py) write to test DB, not dev DB
- db_session fixture uses test engine with per-test rollback
</success_criteria>

<output>
After completion, create `.planning/quick/14-set-up-separate-test-database-with-auto-/14-SUMMARY.md`
</output>

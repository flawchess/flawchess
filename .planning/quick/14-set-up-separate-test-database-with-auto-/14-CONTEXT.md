# Quick Task 14: Set up separate test database with auto-migration - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Task Boundary

Set up a separate test database (chessalytics_test) so integration tests don't leak data into the dev database. The test DB must be auto-migrated (alembic upgrade head) before tests run.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

**DB creation:** Add a TEST_DATABASE_URL setting defaulting to `postgresql+asyncpg://postgres:postgres@localhost:5432/chessalytics_test`. The test DB must be created manually once (`createdb chessalytics_test`), but migrations run automatically.

**Migration trigger:** Session-scoped async fixture in conftest.py that runs `alembic upgrade head` against the test DB at the start of the test session. This is the most Pythonic approach and integrates naturally with pytest.

**Test isolation:** The `db_session` fixture switches to use `TEST_DATABASE_URL`. For httpx.ASGITransport tests (auth/register), override `get_async_session` dependency to use the test DB engine so those writes also go to the test DB and don't leak.

</decisions>

<specifics>
## Specific Ideas

- Use `alembic.command.upgrade` programmatically with a config pointing to TEST_DATABASE_URL
- Override `get_async_session` in conftest.py so the FastAPI app's own session factory uses the test DB
- This also fixes the root cause of quick-13: test users will write to chessalytics_test, not chessalytics

</specifics>

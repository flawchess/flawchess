import asyncio
import os

# Disable Sentry before any app imports — must precede app.core.config which
# reads SENTRY_DSN from env/.env.  Without this, test-triggered exceptions
# (e.g. mocked ValueError in import tests) leak to the real Sentry project.
os.environ["SENTRY_DSN"] = ""

# Use a full-length (32-byte) SECRET_KEY for tests so PyJWT does not emit
# InsecureKeyLengthWarning on every encode/decode. The production default
# "change-me-in-production" is 23 bytes, below RFC 7518 §3.2 minimum for HS256.
os.environ["SECRET_KEY"] = "test-secret-key-32-bytes-exactly-ok-for-hs256-tests"

import chess
import pytest
import pytest_asyncio
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from collections.abc import AsyncGenerator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.user import User

# Phase 61: expose the seeded_user fixture without requiring test modules to
# import it by name (import + parameter-name pytest fixture use triggers
# ruff F811 "redefined unused import" otherwise).
pytest_plugins = ["tests.seed_fixtures"]

# Tables NEVER to truncate during test-session reset:
# - alembic_version: Alembic migration state. Truncating forces a re-migration
#   on next startup and breaks `alembic current`.
# - openings: reference data populated by scripts/seed_openings.py. Currently
#   empty in flawchess_test but excluded defensively so a future contributor
#   who seeds it for opening-classification tests does not see their seed
#   silently wiped on each pytest run.
_TRUNCATE_EXCLUDE = frozenset({"alembic_version", "openings"})


async def _truncate_all_tables(db_url: str) -> None:
    """Truncate every public-schema table except reference tables.

    Called ONCE per pytest session, after alembic migrations run and before
    the first test executes. Restarts identity columns so primary keys are
    deterministic within a run. Data from the *previous* session is wiped;
    data from the current session remains after teardown for inspection.

    Creates and disposes its own throwaway async engine inside the asyncio
    event loop spawned by asyncio.run() in the caller. This is required
    because asyncpg's connection pool is event-loop-bound — sharing the
    test session's engine here would attach it to a dead loop.
    """
    truncate_engine = create_async_engine(db_url, echo=False)
    try:
        async with truncate_engine.begin() as conn:
            rows = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            tables = [r[0] for r in rows if r[0] not in _TRUNCATE_EXCLUDE]
            if tables:
                await conn.execute(
                    text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE")
                )
    finally:
        await truncate_engine.dispose()


@pytest.fixture(scope="session")
def test_engine():
    """Create an async engine for the test DB and run Alembic migrations.

    Session-scoped: created once per test session, disposed at teardown.
    Runs alembic upgrade head against flawchess_test to ensure schema is current.
    Alembic uses a sync URL (postgresql://) because alembic.command.upgrade is synchronous.
    """
    # Patch settings.DATABASE_URL for the entire test session so that any code
    # creating its own DB connections (e.g. on_after_login callback) also hits
    # the test DB, not the dev DB which may lack tables.
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = settings.TEST_DATABASE_URL

    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.TEST_DATABASE_URL)
    alembic_command.upgrade(alembic_cfg, "head")

    # Phase 61: wipe residue from previous pytest runs before any test executes.
    # Preserves alembic_version + openings; everything else is truncated.
    # Runs in a throwaway event loop via asyncio.run(); the truncate helper
    # creates and disposes its own engine inside that loop because asyncpg
    # pools are event-loop-bound — reusing an engine across loops corrupts it.
    asyncio.run(_truncate_all_tables(settings.TEST_DATABASE_URL))

    # Create the async engine for the rest of the test session
    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False)
    yield engine
    # Dispose the engine synchronously at teardown
    engine.sync_engine.dispose()
    settings.DATABASE_URL = original_url


@pytest.fixture(autouse=True, scope="session")
def override_get_async_session(test_engine):
    """Route all DB sessions to the test DB.

    Session-scoped autouse: active for the entire test session.
    Overrides both the FastAPI DI dependency AND the module-level
    async_session_maker so that code bypassing DI (e.g. on_after_login)
    also hits the test DB.
    """
    import app.core.database as db_module
    import app.middleware.last_activity as activity_module
    import app.users as users_module
    from app.core.database import get_async_session
    from app.main import app as fastapi_app

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    # Patch async_session_maker everywhere it's imported, so non-DI code
    # (e.g. UserManager.on_after_login, LastActivityMiddleware) also uses the test DB.
    original_db_session_maker = db_module.async_session_maker
    original_users_session_maker = users_module.async_session_maker
    original_activity_session_maker = activity_module.async_session_maker
    db_module.async_session_maker = test_session_maker
    users_module.async_session_maker = test_session_maker
    activity_module.async_session_maker = test_session_maker

    async def _test_session_generator():
        async with test_session_maker() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_async_session] = _test_session_generator
    yield
    fastapi_app.dependency_overrides.pop(get_async_session, None)
    db_module.async_session_maker = original_db_session_maker
    users_module.async_session_maker = original_users_session_maker
    activity_module.async_session_maker = original_activity_session_maker


@pytest.fixture
def starting_board() -> chess.Board:
    """Return a fresh starting-position chess board."""
    return chess.Board()


@pytest.fixture
def empty_board() -> chess.Board:
    """Return an empty chess board (no pieces)."""
    board = chess.Board()
    board.clear()
    return board


async def ensure_test_user(session: AsyncSession, user_id: int) -> None:
    """Create a test user with the given ID if it doesn't already exist.

    Needed because user_id columns have FK constraints to the users table.
    """
    existing = (await session.execute(select(User).where(User.id == user_id))).unique()
    if existing.scalar_one_or_none() is None:
        session.add(
            User(id=user_id, email=f"test-{user_id}@example.com", hashed_password="fakehash")
        )
        await session.flush()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an AsyncSession wrapped in a transaction that is rolled back after each test.

    Uses the test DB engine (flawchess_test) bound by the test_engine fixture.
    Each test runs inside a transaction that is always rolled back, so tests
    do not pollute each other even without cleanup code.
    """
    async with test_engine.connect() as conn:
        # Begin a transaction that we'll roll back at the end
        await conn.begin()
        # Bind a session to this connection
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()

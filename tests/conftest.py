
import chess
import pytest
import pytest_asyncio
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.user import User


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
    import app.users as users_module
    from app.core.database import get_async_session
    from app.main import app as fastapi_app

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    # Patch async_session_maker everywhere it's imported, so non-DI code
    # (e.g. UserManager.on_after_login) also uses the test DB.
    original_db_session_maker = db_module.async_session_maker
    original_users_session_maker = users_module.async_session_maker
    db_module.async_session_maker = test_session_maker
    users_module.async_session_maker = test_session_maker

    async def _test_session_generator():
        async with test_session_maker() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_async_session] = _test_session_generator
    yield
    fastapi_app.dependency_overrides.pop(get_async_session, None)
    db_module.async_session_maker = original_db_session_maker
    users_module.async_session_maker = original_users_session_maker



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
        session.add(User(id=user_id, email=f"test-{user_id}@example.com", hashed_password="fakehash"))
        await session.flush()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
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

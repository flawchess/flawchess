import chess
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings


@pytest.fixture(autouse=True, scope="session")
def disable_dev_auth_bypass():
    """Force JWT auth in tests even when ENVIRONMENT=development.

    In development mode, app/users.py sets current_active_user = _dev_bypass_user
    at import time. This fixture overrides the FastAPI dependency so that tests
    correctly exercise JWT auth enforcement regardless of ENVIRONMENT setting.
    """
    from app.main import app as fastapi_app
    from app.users import _dev_bypass_user, _jwt_current_active_user

    fastapi_app.dependency_overrides[_dev_bypass_user] = _jwt_current_active_user
    yield
    fastapi_app.dependency_overrides.pop(_dev_bypass_user, None)


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


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Provide an AsyncSession wrapped in a transaction that is rolled back after each test.

    This uses the real PostgreSQL database (DATABASE_URL from settings/env).
    Each test runs inside a transaction that is always rolled back, so tests
    do not pollute each other even without cleanup code.
    """
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Begin a transaction that we'll roll back at the end
        await conn.begin()
        # Bind a session to this connection
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()

    await engine.dispose()

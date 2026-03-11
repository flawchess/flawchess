import chess
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings


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

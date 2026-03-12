"""Game repository: bulk insert with ON CONFLICT DO NOTHING and position insertion."""

from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition


async def bulk_insert_games(session: AsyncSession, game_rows: list[dict]) -> list[int]:
    """Insert games, skipping duplicates. Returns list of newly inserted game IDs.

    Uses ON CONFLICT DO NOTHING on the unique constraint (platform, platform_game_id).
    Only returns IDs for rows that were actually inserted (not skipped).

    Args:
        session: AsyncSession to use for the insert.
        game_rows: List of dicts matching Game model columns.

    Returns:
        List of integer IDs for newly inserted games. Empty list if all are duplicates.
    """
    if not game_rows:
        return []

    stmt = (
        pg_insert(Game)
        .values(game_rows)
        .on_conflict_do_nothing(constraint="uq_games_platform_game_id")
        .returning(Game.id)
    )
    result = await session.execute(stmt)
    await session.flush()
    return [row[0] for row in result.fetchall()]


async def count_games_for_user(session: AsyncSession, user_id: int) -> int:
    """Return total number of games imported by the given user."""
    result = await session.execute(select(func.count()).select_from(Game).where(Game.user_id == user_id))
    return result.scalar_one()


async def bulk_insert_positions(session: AsyncSession, position_rows: list[dict]) -> None:
    """Bulk insert GamePosition rows for the given game.

    Should only be called for game IDs returned by bulk_insert_games (new games only).
    No conflict handling — positions are only inserted for newly inserted games.

    Args:
        session: AsyncSession to use for the insert.
        position_rows: List of dicts with keys: game_id, user_id, ply,
                       full_hash, white_hash, black_hash.
    """
    if not position_rows:
        return

    stmt = insert(GamePosition).values(position_rows)
    await session.execute(stmt)
    await session.flush()

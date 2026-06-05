"""Flaws repository: DB queries for the flaw-detection service.

Functions:
- fetch_game_positions_ordered: all GamePosition rows for one game, ordered by ply ASC
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_position import GamePosition


async def fetch_game_positions_ordered(
    session: AsyncSession,
    game_id: int,
    user_id: int,
) -> list[GamePosition]:
    """Load all GamePosition rows for one game, ordered by ply ASC.

    user_id is included in the WHERE clause as an ownership guard — the
    composite PK is (game_id, user_id, ply), so this filter is index-backed.
    A different user_id returns an empty list, preventing cross-user data access
    (STRIDE T-105-03: Information Disclosure mitigation).

    No SQL string interpolation — all filters are parameterized SQLAlchemy binds
    (STRIDE T-105-04: Tampering via SQL injection mitigation).

    SQLAlchemy 2.x select() API only (no legacy session.query).
    """
    stmt = (
        select(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.user_id == user_id)
        .order_by(GamePosition.ply)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

"""Analysis repository: DB queries for position-based W/D/L lookups."""

import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition

# Maps match_side values to the corresponding GamePosition hash column.
HASH_COLUMN_MAP = {
    "white": GamePosition.white_hash,
    "black": GamePosition.black_hash,
    "full": GamePosition.full_hash,
}


def _build_base_query(
    select_entity: Any,
    user_id: int,
    hash_column: Any,
    target_hash: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
) -> Any:
    """Build a filtered SELECT that joins game_positions -> games.

    Uses DISTINCT ON game.id to avoid counting a game multiple times when the
    target hash appears at more than one ply.

    ``select_entity`` may be a single ORM entity/column or a list of columns.
    When a list is provided the columns are unpacked into ``select()``.
    """
    entities = select_entity if isinstance(select_entity, list) else [select_entity]
    base = (
        select(*entities)
        .join(GamePosition, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            hash_column == target_hash,
        )
        .distinct(Game.id)
    )

    if time_control is not None:
        base = base.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        base = base.where(Game.platform.in_(platform))
    if rated is not None:
        base = base.where(Game.rated == rated)
    if recency_cutoff is not None:
        base = base.where(Game.played_at >= recency_cutoff)
    if color is not None:
        base = base.where(Game.user_color == color)

    return base


async def query_all_results(
    session: AsyncSession,
    user_id: int,
    hash_column: Any,
    target_hash: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
) -> list[tuple[str, str]]:
    """Return (result, user_color) tuples for ALL matching games (for stats).

    Lightweight — only fetches the two columns needed for W/D/L computation.
    DISTINCT by game_id prevents transposition double-counting.
    """
    # Pass columns as a list so _build_base_query can splat them into select().
    stmt = _build_base_query(
        select_entity=[Game.result, Game.user_color],
        user_id=user_id,
        hash_column=hash_column,
        target_hash=target_hash,
        time_control=time_control,
        platform=platform,
        rated=rated,
        recency_cutoff=recency_cutoff,
        color=color,
    )
    rows = await session.execute(stmt)
    return list(rows.all())


async def query_matching_games(
    session: AsyncSession,
    user_id: int,
    hash_column: Any,
    target_hash: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Game], int]:
    """Return a paginated list of Game objects and the total matching count.

    The total count reflects all matches (before pagination) and is derived
    from the same filtered query so it stays consistent with the stats.
    """
    # Count subquery — wrap the deduplicated game IDs to count distinct games.
    count_subq = _build_base_query(
        select_entity=Game.id,
        user_id=user_id,
        hash_column=hash_column,
        target_hash=target_hash,
        time_control=time_control,
        platform=platform,
        rated=rated,
        recency_cutoff=recency_cutoff,
        color=color,
    ).subquery()
    count_stmt = select(func.count()).select_from(count_subq)
    total: int = (await session.execute(count_stmt)).scalar_one()

    # Paginated game objects, ordered most-recent first.
    # PostgreSQL requires DISTINCT ON expressions to appear first in ORDER BY,
    # so Game.id must precede played_at in the ORDER BY clause.
    page_stmt = (
        _build_base_query(
            select_entity=Game,
            user_id=user_id,
            hash_column=hash_column,
            target_hash=target_hash,
            time_control=time_control,
            platform=platform,
            rated=rated,
            recency_cutoff=recency_cutoff,
            color=color,
        )
        .order_by(Game.id, Game.played_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(page_stmt)
    games = list(result.scalars().all())

    return games, total

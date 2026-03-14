"""Stats repository: DB queries for rating history and global game stats."""

import datetime

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game


async def query_rating_history(
    session: AsyncSession,
    user_id: int,
    platform: str,
    recency_cutoff: datetime.datetime | None,
) -> list[tuple]:
    """Return per-game rating data points for a given platform.

    Each row is a (date, rating, time_control_bucket) tuple where date is a
    Python date object (UTC-normalized from the timestamptz column).

    Excludes games where the derived user_rating or played_at is NULL.
    Results are ordered chronologically by played_at.
    """
    user_rating_expr = case(
        (Game.user_color == "white", Game.white_rating),
        else_=Game.black_rating,
    ).label("user_rating")

    stmt = (
        select(
            cast(func.timezone("UTC", Game.played_at), Date),
            user_rating_expr,
            Game.time_control_bucket,
        )
        .where(
            Game.user_id == user_id,
            Game.platform == platform,
            user_rating_expr.is_not(None),
            Game.played_at.is_not(None),
        )
        .order_by(Game.played_at)
    )

    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_results_by_time_control(
    session: AsyncSession,
    user_id: int,
    recency_cutoff: datetime.datetime | None,
) -> list[tuple]:
    """Return (time_control_bucket, result, user_color) tuples for all games.

    Excludes games where time_control_bucket is NULL.
    """
    stmt = (
        select(
            Game.time_control_bucket,
            Game.result,
            Game.user_color,
        )
        .where(
            Game.user_id == user_id,
            Game.time_control_bucket.is_not(None),
        )
    )

    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_results_by_color(
    session: AsyncSession,
    user_id: int,
    recency_cutoff: datetime.datetime | None,
) -> list[tuple]:
    """Return (user_color, result) tuples for all games.

    Excludes games where user_color is NULL.
    """
    stmt = (
        select(
            Game.user_color,
            Game.result,
        )
        .where(
            Game.user_id == user_id,
            Game.user_color.is_not(None),
        )
    )

    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())

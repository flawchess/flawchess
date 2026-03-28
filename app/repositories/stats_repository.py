"""Stats repository: DB queries for rating history and global game stats."""

import datetime
from typing import Literal

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
    platform: str | None = None,
) -> list[tuple]:
    """Return (time_control_bucket, result, user_color) tuples for all games.

    Excludes games where time_control_bucket is NULL.
    Optionally filtered by platform (chess.com or lichess).
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

    if platform is not None:
        stmt = stmt.where(Game.platform == platform)

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_results_by_color(
    session: AsyncSession,
    user_id: int,
    recency_cutoff: datetime.datetime | None,
    platform: str | None = None,
) -> list[tuple]:
    """Return (user_color, result) tuples for all games.

    Excludes games where user_color is NULL.
    Optionally filtered by platform (chess.com or lichess).
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

    if platform is not None:
        stmt = stmt.where(Game.platform == platform)

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_top_openings_by_color(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    min_games: int,
    limit: int,
) -> list[tuple]:
    """Return (opening_eco, opening_name, result, user_color) tuples for top openings.

    Finds the top-N (eco, name) pairs by game count among games where the user
    played the given color, then fetches individual game rows for each of those
    top openings for Python-side WDL aggregation.

    Excludes games with NULL opening_eco or NULL opening_name.
    Excludes openings with fewer than min_games games.
    Returns at most limit distinct openings (by game count descending).
    """
    # Subquery: find top-N (eco, name) pairs by game count
    top_openings_subq = (
        select(
            Game.opening_eco.label("eco"),
            Game.opening_name.label("name"),
        )
        .where(
            Game.user_id == user_id,
            Game.user_color == color,
            Game.opening_eco.is_not(None),
            Game.opening_name.is_not(None),
        )
        .group_by(Game.opening_eco, Game.opening_name)
        .having(func.count() >= min_games)
        .order_by(func.count().desc())
        .limit(limit)
        .subquery()
    )

    # Main query: fetch individual game rows for the top openings
    stmt = (
        select(
            Game.opening_eco,
            Game.opening_name,
            Game.result,
            Game.user_color,
        )
        .join(
            top_openings_subq,
            (Game.opening_eco == top_openings_subq.c.eco)
            & (Game.opening_name == top_openings_subq.c.name),
        )
        .where(
            Game.user_id == user_id,
            Game.user_color == color,
        )
    )

    result = await session.execute(stmt)
    return list(result.fetchall())

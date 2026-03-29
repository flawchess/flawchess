"""Stats repository: DB queries for rating history and global game stats."""

import datetime
from typing import Literal

from sqlalchemy import BigInteger, Column, Date, MetaData, SmallInteger, String, Table, Text, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game

# Standalone MetaData (not Base.metadata) keeps the view invisible to Alembic autogenerate.
_openings_dedup = Table(
    "openings_dedup",
    MetaData(),
    Column("id"),
    Column("eco", String(10)),
    Column("name", String(200)),
    Column("pgn", Text),
    Column("ply_count", SmallInteger),
    Column("fen", String(100)),
    Column("full_hash", BigInteger),
    Column("white_hash", BigInteger),
    Column("black_hash", BigInteger),
)


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
    """Return (time_control_bucket, total, wins, draws, losses) via SQL aggregation.

    Excludes games where time_control_bucket is NULL.
    Optionally filtered by platform (chess.com or lichess).
    """
    win_cond = or_(
        and_(Game.result == "1-0", Game.user_color == "white"),
        and_(Game.result == "0-1", Game.user_color == "black"),
    )
    draw_cond = Game.result == "1/2-1/2"
    loss_cond = or_(
        and_(Game.result == "0-1", Game.user_color == "white"),
        and_(Game.result == "1-0", Game.user_color == "black"),
    )

    stmt = (
        select(
            Game.time_control_bucket,
            func.count().label("total"),
            func.count().filter(win_cond).label("wins"),
            func.count().filter(draw_cond).label("draws"),
            func.count().filter(loss_cond).label("losses"),
        )
        .where(
            Game.user_id == user_id,
            Game.time_control_bucket.is_not(None),
        )
        .group_by(Game.time_control_bucket)
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
    """Return (user_color, total, wins, draws, losses) via SQL aggregation.

    Excludes games where user_color is NULL.
    Optionally filtered by platform (chess.com or lichess).
    """
    win_cond = or_(
        and_(Game.result == "1-0", Game.user_color == "white"),
        and_(Game.result == "0-1", Game.user_color == "black"),
    )
    draw_cond = Game.result == "1/2-1/2"
    loss_cond = or_(
        and_(Game.result == "0-1", Game.user_color == "white"),
        and_(Game.result == "1-0", Game.user_color == "black"),
    )

    stmt = (
        select(
            Game.user_color,
            func.count().label("total"),
            func.count().filter(win_cond).label("wins"),
            func.count().filter(draw_cond).label("draws"),
            func.count().filter(loss_cond).label("losses"),
        )
        .where(
            Game.user_id == user_id,
            Game.user_color.is_not(None),
        )
        .group_by(Game.user_color)
    )

    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)

    if platform is not None:
        stmt = stmt.where(Game.platform == platform)

    result = await session.execute(stmt)
    return list(result.fetchall())


def _apply_game_filters(
    stmt,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
):
    """Apply standard game filter WHERE clauses to a statement."""
    if time_control is not None:
        stmt = stmt.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        stmt = stmt.where(Game.platform.in_(platform))
    if rated is not None:
        stmt = stmt.where(Game.rated == rated)
    if opponent_type == "human":
        stmt = stmt.where(Game.is_computer_game == False)  # noqa: E712
    elif opponent_type == "bot":
        stmt = stmt.where(Game.is_computer_game == True)  # noqa: E712
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    return stmt


async def query_top_openings_sql_wdl(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    min_games: int,
    limit: int,
    min_ply: int,
    recency_cutoff: datetime.datetime | None = None,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
) -> list[tuple]:
    """Return top openings with SQL-side WDL aggregation.

    JOINs games to openings_dedup to get pgn/fen and filter by min_ply.
    Returns (eco, name, pgn, fen, total, wins, draws, losses) tuples.
    Uses func.count().filter() for SQL-side WDL — no Python-side aggregation.
    """
    win_cond = or_(
        and_(Game.result == "1-0", Game.user_color == "white"),
        and_(Game.result == "0-1", Game.user_color == "black"),
    )
    draw_cond = Game.result == "1/2-1/2"
    loss_cond = or_(
        and_(Game.result == "0-1", Game.user_color == "white"),
        and_(Game.result == "1-0", Game.user_color == "black"),
    )

    stmt = (
        select(
            Game.opening_eco,
            Game.opening_name,
            _openings_dedup.c.pgn,
            _openings_dedup.c.fen,
            _openings_dedup.c.full_hash,
            func.count().label("total"),
            func.count().filter(win_cond).label("wins"),
            func.count().filter(draw_cond).label("draws"),
            func.count().filter(loss_cond).label("losses"),
        )
        .join(
            _openings_dedup,
            and_(
                Game.opening_eco == _openings_dedup.c.eco,
                Game.opening_name == _openings_dedup.c.name,
            ),
        )
        .where(
            Game.user_id == user_id,
            Game.user_color == color,
            Game.opening_eco.is_not(None),
            Game.opening_name.is_not(None),
            _openings_dedup.c.ply_count >= min_ply,
            # White openings end on odd ply (white's last move), black on even ply
            _openings_dedup.c.ply_count % 2 == (1 if color == "white" else 0),
        )
        .group_by(
            Game.opening_eco,
            Game.opening_name,
            _openings_dedup.c.pgn,
            _openings_dedup.c.fen,
            _openings_dedup.c.full_hash,
        )
        .having(func.count() >= min_games)
        .order_by(func.count().desc())
        .limit(limit)
    )

    stmt = _apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())

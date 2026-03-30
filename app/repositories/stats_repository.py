"""Stats repository: DB queries for rating history and global game stats."""

import datetime
from typing import Literal

from sqlalchemy import BigInteger, Column, Date, MetaData, SmallInteger, String, Table, Text, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition

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
    """Return one rating data point per (date, time_control_bucket) for a given platform.

    Each row is a (date, rating, time_control_bucket) tuple where date is a
    Python date object (UTC-normalized from the timestamptz column).

    Uses DISTINCT ON to keep only the last game's rating per day per time control,
    avoiding redundant per-game rows when multiple games are played on the same day.
    """
    user_rating_expr = case(
        (Game.user_color == "white", Game.white_rating),
        else_=Game.black_rating,
    ).label("user_rating")

    date_col = cast(func.timezone("UTC", Game.played_at), Date).label("date")

    stmt = (
        select(date_col, user_rating_expr, Game.time_control_bucket)
        .distinct(date_col, Game.time_control_bucket)
        .where(
            Game.user_id == user_id,
            Game.platform == platform,
            user_rating_expr.is_not(None),
            Game.played_at.is_not(None),
        )
        # DISTINCT ON requires ORDER BY to start with the same columns;
        # played_at DESC picks the last game of each day per time control.
        .order_by(date_col, Game.time_control_bucket, Game.played_at.desc())
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


class PositionWDL:
    """Position-based WDL stats for a single hash."""

    __slots__ = ("total", "wins", "draws", "losses")

    def __init__(self, total: int, wins: int, draws: int, losses: int):
        self.total = total
        self.wins = wins
        self.draws = draws
        self.losses = losses


async def query_position_wdl_batch(
    session: AsyncSession,
    user_id: int,
    hashes: list[int],
    color: Literal["white", "black"] | None = None,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    recency_cutoff: datetime.datetime | None = None,
) -> dict[int, PositionWDL]:
    """Return {full_hash: PositionWDL} for games passing through each position.

    Uses DISTINCT game_id per hash to avoid double-counting games where the
    same position appears at multiple plies. WDL computed SQL-side using the
    same conditions as query_top_openings_sql_wdl.
    """
    if not hashes:
        return {}

    # Deduplicate game_id per hash first (subquery), then aggregate WDL
    dedup = (
        select(
            GamePosition.full_hash,
            Game.id.label("game_id"),
            Game.result,
            Game.user_color,
        )
        .join(Game, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.full_hash.in_(hashes),
        )
        .distinct(GamePosition.full_hash, Game.id)
    )
    if color is not None:
        dedup = dedup.where(Game.user_color == color)
    dedup = _apply_game_filters(dedup, time_control, platform, rated, opponent_type, recency_cutoff)
    dedup = dedup.subquery()

    stmt = (
        select(
            dedup.c.full_hash,
            func.count().label("total"),
            func.count().filter(
                or_(
                    and_(dedup.c.result == "1-0", dedup.c.user_color == "white"),
                    and_(dedup.c.result == "0-1", dedup.c.user_color == "black"),
                )
            ).label("wins"),
            func.count().filter(dedup.c.result == "1/2-1/2").label("draws"),
            func.count().filter(
                or_(
                    and_(dedup.c.result == "0-1", dedup.c.user_color == "white"),
                    and_(dedup.c.result == "1-0", dedup.c.user_color == "black"),
                )
            ).label("losses"),
        )
        .group_by(dedup.c.full_hash)
    )

    result = await session.execute(stmt)
    return {
        row[0]: PositionWDL(total=row[1], wins=row[2], draws=row[3], losses=row[4])
        for row in result.fetchall()
    }

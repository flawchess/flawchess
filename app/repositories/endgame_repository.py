"""Endgame repository: DB queries for endgame analytics.

Functions:
- query_endgame_entry_rows: one row per (game, endgame_class) span meeting the ply threshold
- query_endgame_games: paginated Game objects for a given endgame class
- query_endgame_performance_rows: endgame and non-endgame game rows for performance comparison
- query_endgame_timeline_rows: rows for rolling-window time series, overall and per-type
"""

import datetime
from collections.abc import Sequence
from typing import Any

from sqlalchemy import case, func, select, type_coerce
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by
from sqlalchemy.engine import Row
from sqlalchemy.types import SmallInteger as SmallIntegerType
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.query_utils import apply_game_filters
from app.schemas.endgames import EndgameClass

# Piece-count threshold for endgame classification (Lichess definition).
# Positions with piece_count <= this value are classified as endgame phase.
# piece_count counts major and minor pieces (Q+R+B+N) for both sides combined,
# excluding kings and pawns.
# At threshold 6: KRR_KRR (4 pieces) = endgame; KQRBN_KQRBN (8 pieces) = NOT endgame.
# This correlates better with position complexity than centipawn value:
# Q vs Q (1800cp) and RB vs RN (1600cp) were previously excluded from endgames but are true endgames.
ENDGAME_PIECE_COUNT_THRESHOLD = 6

# Minimum plies a game must spend in an endgame class to count in that category.
# Filters out tactical transitions (piece sacrifices, quick class changes).
# 6 plies = 3 full moves of sustained endgame play. Per D-03.
ENDGAME_PLY_THRESHOLD = 6

# Number of plies after endgame entry to check for persistence of material imbalance.
# Filters out transient imbalances from piece trades at the endgame transition.
PERSISTENCE_PLIES = 4


async def count_filtered_games(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> int:
    """Count ALL games for the user matching the given filters.

    This counts total games regardless of whether they reached an endgame phase,
    used to provide context like "X of Y games reached an endgame".
    """
    stmt = select(func.count()).select_from(Game).where(Game.user_id == user_id)
    stmt = apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)
    result = await session.execute(stmt)
    return result.scalar_one()


async def query_endgame_entry_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> list[Row[Any]]:
    """Return one row per (game, endgame_class) span meeting the ply threshold.

    Per D-02: a game can appear in MULTIPLE endgame classes if it spent >= ENDGAME_PLY_THRESHOLD
    plies in each class. Per D-04: material_imbalance at the FIRST position of each class span
    determines conversion/recovery classification.

    Returns rows of: (game_id, endgame_class, result, user_color, user_material_imbalance, user_material_imbalance_after)
    where endgame_class is an integer (1-6, see EndgameClassInt).

    user_material_imbalance = material_imbalance if user_color == "white" else -material_imbalance.
    This sign flip normalizes to user perspective: positive = user has more material.

    user_material_imbalance_after = material_imbalance at entry + PERSISTENCE_PLIES (4 plies later).
    Used by the service layer for persistence check: both entry AND entry+4 must meet the threshold
    to count as conversion/recovery (filters transient trade imbalances).

    NO color filter is applied per D-02 — stats cover both white and black games.
    """
    # Single subquery: group by (game_id, endgame_class), count plies per span,
    # AND grab material_imbalance at entry ply via array_agg ordered by ply.
    # This eliminates a separate entry_pos subquery that caused a 5M+ row seq scan.
    # The INCLUDE(material_imbalance) on ix_gp_user_endgame_game enables index-only scans.
    #
    # (array_agg(material_imbalance ORDER BY ply))[1] gets the value at the min ply
    # without needing a separate lookup join.
    entry_imbalance_agg = type_coerce(
        func.array_agg(
            aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())
        ),
        ARRAY(SmallIntegerType),
    )[1]

    # Imbalance 4 plies after entry — used for persistence check.
    # Index [5] is safe because spans already require >= ENDGAME_PLY_THRESHOLD (6) plies.
    imbalance_after_persistence_agg = type_coerce(
        func.array_agg(
            aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())
        ),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    span_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.endgame_class.label("endgame_class"),
            entry_imbalance_agg.label("entry_imbalance"),
            imbalance_after_persistence_agg.label("entry_imbalance_after"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id, GamePosition.endgame_class)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("span")
    )

    # Sign flip for black: material_imbalance is always from white's perspective in DB.
    # Multiply by -1 when user is black so positive value = user has more material.
    color_sign = case(
        (Game.user_color == "white", 1),
        else_=-1,
    )

    # Main query: join Game -> span_subq (no second subquery needed).
    stmt = (
        select(
            Game.id.label("game_id"),
            span_subq.c.endgame_class,
            Game.result,
            Game.user_color,
            (span_subq.c.entry_imbalance * color_sign).label("user_material_imbalance"),
            (span_subq.c.entry_imbalance_after * color_sign).label("user_material_imbalance_after"),
        )
        .join(span_subq, Game.id == span_subq.c.game_id)
        .where(Game.user_id == user_id)
    )

    # Apply standard game filters
    stmt = apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_endgame_games(
    session: AsyncSession,
    user_id: int,
    endgame_class: EndgameClass,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    offset: int,
    limit: int,
) -> tuple[list[Game], int]:
    """Return paginated Game objects for games that spent >= ENDGAME_PLY_THRESHOLD plies
    in the given endgame class.

    Filters endgame_class by integer value directly in SQL (no Python classify loop).
    Returns (games_list, matched_count) for pagination.
    matched_count reflects all matching games (before offset/limit).
    """
    # Import here to avoid circular import at module level
    from app.services.endgame_service import _CLASS_TO_INT

    # KeyError for unknown class is intentional — callers pass validated EndgameClass values
    if endgame_class not in _CLASS_TO_INT:
        return [], 0

    class_int = _CLASS_TO_INT[endgame_class]

    # Subquery: game_ids that spent >= ENDGAME_PLY_THRESHOLD plies in the requested endgame class.
    # Filters by endgame_class integer directly in SQL — no Python-side classification.
    span_subq = (
        select(GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class == class_int,
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("span")
    )

    # Base: games matching the span subquery
    base_stmt = select(Game).where(
        Game.user_id == user_id,
        Game.id.in_(select(span_subq.c.game_id)),
    )
    base_stmt = apply_game_filters(base_stmt, time_control, platform, rated, opponent_type, recency_cutoff)

    # Count total matching games (before pagination)
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    count_result = await session.execute(count_stmt)
    matched_count = count_result.scalar_one()

    if matched_count == 0:
        return [], 0

    # Paginated game objects ordered most-recent first
    games_stmt = (
        base_stmt
        .order_by(Game.played_at.desc().nulls_last())
        .offset(offset)
        .limit(limit)
    )
    games_result = await session.execute(games_stmt)
    games = list(games_result.scalars().all())

    return games, matched_count


async def query_conv_recov_timeline_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> list[Row[Any]]:
    """Return rows for conversion/recovery timeline: all endgame games for persistence filtering.

    Returns ALL endgame games regardless of imbalance — the service layer applies the
    persistence filter (both entry AND entry+4 plies must meet the 100cp threshold).

    Returns rows of: (played_at, result, user_color, user_material_imbalance, user_material_imbalance_after)
    ordered by played_at ascending for chronological rolling-window computation.
    """
    # Minimum centipawn imbalance for a game to count as "significant advantage/disadvantage".
    # Lowered from 300cp to 100cp — persistence filter eliminates transient trade noise.
    SIGNIFICANT_IMBALANCE_CP = 100  # noqa: F841 — kept for documentation, filtering now in service

    # Single subquery: group + grab entry material_imbalance via array_agg.
    # Same pattern as query_endgame_entry_rows — eliminates 5M+ row seq scan.
    entry_imbalance_agg = type_coerce(
        func.array_agg(
            aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())
        ),
        ARRAY(SmallIntegerType),
    )[1]

    # Imbalance 4 plies after entry — used for persistence check in service layer.
    # Index [5] is safe because spans already require >= ENDGAME_PLY_THRESHOLD (6) plies.
    imbalance_after_persistence_agg = type_coerce(
        func.array_agg(
            aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())
        ),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    span_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            entry_imbalance_agg.label("entry_imbalance"),
            imbalance_after_persistence_agg.label("entry_imbalance_after"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id, GamePosition.endgame_class)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("span")
    )

    # Sign flip for black: positive = user has more material.
    color_sign = case(
        (Game.user_color == "white", 1),
        else_=-1,
    )

    # Main query: join Game -> span_subq only (no second subquery).
    # No imbalance filter here — service layer applies persistence check with 100cp threshold.
    stmt = (
        select(
            Game.played_at,
            Game.result,
            Game.user_color,
            (span_subq.c.entry_imbalance * color_sign).label("user_material_imbalance"),
            (span_subq.c.entry_imbalance_after * color_sign).label("user_material_imbalance_after"),
        )
        .join(span_subq, Game.id == span_subq.c.game_id)
        .where(
            Game.user_id == user_id,
            Game.played_at.isnot(None),
        )
        .order_by(Game.played_at.asc())
    )

    stmt = apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())


# Integer values for all six endgame classes — used in per-type timeline queries.
# Avoids importing from endgame_service which would create a circular import.
_ENDGAME_CLASS_INTS = range(1, 7)


async def query_endgame_performance_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> tuple[list[Row[Any]], list[Row[Any]]]:
    """Return endgame and non-endgame game rows for performance comparison.

    Endgame games: games where the user spent >= ENDGAME_PLY_THRESHOLD plies
    in any endgame class (endgame_class IS NOT NULL).

    Non-endgame games: all other games that did not meet the ply threshold
    in any endgame class.

    Returns: (endgame_rows, non_endgame_rows) where each row is
    (played_at, result, user_color).

    Rows are ordered by played_at ASC for chronological processing.
    """
    # Subquery: game_ids that spent >= ENDGAME_PLY_THRESHOLD plies in ANY endgame class
    endgame_game_ids_subq = (
        select(GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("endgame_game_ids")
    )

    # Base select for game rows — columns needed for WDL derivation and timeline
    game_cols = select(Game.played_at, Game.result, Game.user_color).where(
        Game.user_id == user_id,
        Game.played_at.isnot(None),
    )

    # Endgame games: id in the endgame subquery
    endgame_stmt = (
        game_cols.where(Game.id.in_(select(endgame_game_ids_subq.c.game_id)))
        .order_by(Game.played_at.asc())
    )
    endgame_stmt = apply_game_filters(
        endgame_stmt, time_control, platform, rated, opponent_type, recency_cutoff
    )

    # Non-endgame games: id NOT in the endgame subquery
    non_endgame_stmt = (
        game_cols.where(Game.id.notin_(select(endgame_game_ids_subq.c.game_id)))
        .order_by(Game.played_at.asc())
    )
    non_endgame_stmt = apply_game_filters(
        non_endgame_stmt, time_control, platform, rated, opponent_type, recency_cutoff
    )

    # Execute sequentially — AsyncSession is not safe for concurrent use from
    # multiple coroutines, and a single session uses one DB connection so there's
    # no concurrency benefit from asyncio.gather here.
    endgame_result = await session.execute(endgame_stmt)
    non_endgame_result = await session.execute(non_endgame_stmt)

    return list(endgame_result.fetchall()), list(non_endgame_result.fetchall())


async def query_endgame_timeline_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> tuple[list[Row[Any]], list[Row[Any]], dict[int, list[Row[Any]]]]:
    """Return rows for rolling-window time series (overall and per endgame class).

    Runs 8 queries sequentially (AsyncSession is not safe for concurrent use
    from multiple coroutines, and shares a single DB connection anyway).

    Returns: (endgame_rows, non_endgame_rows, per_type_rows)
    where per_type_rows is dict[class_int, list[(played_at, result, user_color)]].

    Each row is (played_at, result, user_color), ordered by played_at ASC.
    """
    # Subquery: game_ids reaching any endgame class (for overall split)
    endgame_game_ids_subq = (
        select(GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("endgame_game_ids")
    )

    game_cols = select(Game.played_at, Game.result, Game.user_color).where(
        Game.user_id == user_id,
        Game.played_at.isnot(None),
    )

    endgame_stmt = (
        game_cols.where(Game.id.in_(select(endgame_game_ids_subq.c.game_id)))
        .order_by(Game.played_at.asc())
    )
    endgame_stmt = apply_game_filters(
        endgame_stmt, time_control, platform, rated, opponent_type, recency_cutoff
    )

    non_endgame_stmt = (
        game_cols.where(Game.id.notin_(select(endgame_game_ids_subq.c.game_id)))
        .order_by(Game.played_at.asc())
    )
    non_endgame_stmt = apply_game_filters(
        non_endgame_stmt, time_control, platform, rated, opponent_type, recency_cutoff
    )

    # Per-type subqueries: one per endgame class integer
    def _per_class_stmt(class_int: int):
        per_class_game_ids_subq = (
            select(GamePosition.game_id)
            .where(
                GamePosition.user_id == user_id,
                GamePosition.endgame_class == class_int,
            )
            .group_by(GamePosition.game_id)
            .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
            .subquery(f"endgame_game_ids_{class_int}")
        )
        stmt = (
            game_cols.where(Game.id.in_(select(per_class_game_ids_subq.c.game_id)))
            .order_by(Game.played_at.asc())
        )
        return apply_game_filters(
            stmt, time_control, platform, rated, opponent_type, recency_cutoff
        )

    class_ints = list(_ENDGAME_CLASS_INTS)
    per_class_stmts = [_per_class_stmt(ci) for ci in class_ints]

    # Execute sequentially — AsyncSession is not safe for concurrent use.
    endgame_result = await session.execute(endgame_stmt)
    endgame_rows = list(endgame_result.fetchall())

    non_endgame_result = await session.execute(non_endgame_stmt)
    non_endgame_rows = list(non_endgame_result.fetchall())

    per_type_rows: dict[int, list[Row[Any]]] = {}
    for i, class_int in enumerate(class_ints):
        result = await session.execute(per_class_stmts[i])
        per_type_rows[class_int] = list(result.fetchall())

    return endgame_rows, non_endgame_rows, per_type_rows

"""Endgame repository: DB queries for endgame analytics.

Functions:
- query_endgame_entry_rows: one row per (game, endgame_class) span meeting the ply threshold
- query_endgame_games: paginated Game objects for a given endgame class
- query_endgame_performance_rows: endgame and non-endgame game rows for performance comparison
- query_endgame_timeline_rows: rows for rolling-window time series, overall and per-type
"""

import asyncio
import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
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


async def count_filtered_games(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> int:
    """Count ALL games for the user matching the given filters.

    This counts total games regardless of whether they reached an endgame phase,
    used to provide context like "X of Y games reached an endgame".
    """
    stmt = select(func.count()).select_from(Game).where(Game.user_id == user_id)
    stmt = _apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)
    result = await session.execute(stmt)
    return result.scalar_one()


async def query_endgame_entry_rows(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> list[tuple]:
    """Return one row per (game, endgame_class) span meeting the ply threshold.

    Per D-02: a game can appear in MULTIPLE endgame classes if it spent >= ENDGAME_PLY_THRESHOLD
    plies in each class. Per D-04: material_imbalance at the FIRST position of each class span
    determines conversion/recovery classification.

    Returns rows of: (game_id, endgame_class, result, user_color, user_material_imbalance)
    where endgame_class is an integer (1-6, see EndgameClassInt).

    user_material_imbalance = material_imbalance if user_color == "white" else -material_imbalance.
    This sign flip normalizes to user perspective: positive = user has more material.

    NO color filter is applied per D-02 — stats cover both white and black games.
    """
    # Subquery 1: group by (game_id, endgame_class), count plies per span, find entry ply.
    # HAVING filters out spans below the ply threshold — short tactical transitions ignored.
    span_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.endgame_class.label("endgame_class"),
            func.count(GamePosition.ply).label("ply_count"),
            func.min(GamePosition.ply).label("entry_ply"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id, GamePosition.endgame_class)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("span")
    )

    # Subquery 2: select (game_id, ply, material_imbalance) for looking up entry ply imbalance.
    entry_pos_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.ply.label("ply"),
            GamePosition.material_imbalance.label("material_imbalance"),
        )
        .where(GamePosition.user_id == user_id)
        .subquery("entry_pos")
    )

    # Sign flip for black: material_imbalance is always from white's perspective in DB.
    # Multiply by -1 when user is black so positive value = user has more material.
    color_sign = case(
        (Game.user_color == "white", 1),
        else_=-1,
    )

    # Main query: join Game -> span_subq -> entry_pos_subq.
    # entry_pos_subq joined on entry_ply to get material_imbalance at span start.
    stmt = (
        select(
            Game.id.label("game_id"),
            span_subq.c.endgame_class,
            Game.result,
            Game.user_color,
            (entry_pos_subq.c.material_imbalance * color_sign).label("user_material_imbalance"),
        )
        .join(span_subq, Game.id == span_subq.c.game_id)
        .join(
            entry_pos_subq,
            (entry_pos_subq.c.game_id == span_subq.c.game_id)
            & (entry_pos_subq.c.ply == span_subq.c.entry_ply),
        )
        .where(Game.user_id == user_id)
    )

    # Apply standard game filters
    stmt = _apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_endgame_games(
    session: AsyncSession,
    user_id: int,
    endgame_class: EndgameClass,
    time_control: list[str] | None,
    platform: list[str] | None,
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
    base_stmt = _apply_game_filters(base_stmt, time_control, platform, rated, opponent_type, recency_cutoff)

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
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> list[tuple]:
    """Return rows for conversion/recovery timeline: games with significant material imbalance.

    Only includes games where abs(material_imbalance) >= 300 at endgame entry
    (significant advantage or disadvantage of roughly 3+ pawns).

    Returns rows of: (played_at, result, user_color, user_material_imbalance)
    ordered by played_at ascending for chronological rolling-window computation.
    """
    # Minimum centipawn imbalance for a game to count as "significant advantage/disadvantage"
    SIGNIFICANT_IMBALANCE_CP = 300

    # Subquery 1: group by (game_id, endgame_class), count plies per span, find entry ply.
    span_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.endgame_class.label("endgame_class"),
            func.count(GamePosition.ply).label("ply_count"),
            func.min(GamePosition.ply).label("entry_ply"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id, GamePosition.endgame_class)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("span")
    )

    # Subquery 2: entry position material imbalance lookup.
    entry_pos_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.ply.label("ply"),
            GamePosition.material_imbalance.label("material_imbalance"),
        )
        .where(GamePosition.user_id == user_id)
        .subquery("entry_pos")
    )

    # Sign flip for black: positive = user has more material.
    color_sign = case(
        (Game.user_color == "white", 1),
        else_=-1,
    )

    # Main query: join Game -> span_subq -> entry_pos_subq.
    # Filter by abs(material_imbalance) >= 300 — works regardless of sign flip
    # since abs is symmetric. This keeps the query efficient by filtering in SQL.
    stmt = (
        select(
            Game.played_at,
            Game.result,
            Game.user_color,
            (entry_pos_subq.c.material_imbalance * color_sign).label("user_material_imbalance"),
        )
        .join(span_subq, Game.id == span_subq.c.game_id)
        .join(
            entry_pos_subq,
            (entry_pos_subq.c.game_id == span_subq.c.game_id)
            & (entry_pos_subq.c.ply == span_subq.c.entry_ply),
        )
        .where(
            Game.user_id == user_id,
            Game.played_at.isnot(None),
            func.abs(entry_pos_subq.c.material_imbalance) >= SIGNIFICANT_IMBALANCE_CP,
        )
        .order_by(Game.played_at.asc())
    )

    stmt = _apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)

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
    """Apply standard game filter WHERE clauses to a statement.

    Consistent with analysis_repository._apply_game_filters but without color filter
    (per D-02: no color filter on endgame endpoints).
    """
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
    # "both" = no filter
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    return stmt


# Integer values for all six endgame classes — used in per-type timeline queries.
# Avoids importing from endgame_service which would create a circular import.
_ENDGAME_CLASS_INTS = range(1, 7)


async def query_endgame_performance_rows(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> tuple[list[tuple], list[tuple]]:
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
    endgame_stmt = _apply_game_filters(
        endgame_stmt, time_control, platform, rated, opponent_type, recency_cutoff
    )

    # Non-endgame games: id NOT in the endgame subquery
    non_endgame_stmt = (
        game_cols.where(Game.id.notin_(select(endgame_game_ids_subq.c.game_id)))
        .order_by(Game.played_at.asc())
    )
    non_endgame_stmt = _apply_game_filters(
        non_endgame_stmt, time_control, platform, rated, opponent_type, recency_cutoff
    )

    endgame_result, non_endgame_result = await asyncio.gather(
        session.execute(endgame_stmt),
        session.execute(non_endgame_stmt),
    )

    return list(endgame_result.fetchall()), list(non_endgame_result.fetchall())


async def query_endgame_timeline_rows(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> tuple[list[tuple], list[tuple], dict[int, list[tuple]]]:
    """Return rows for rolling-window time series (overall and per endgame class).

    Runs 8 queries concurrently via asyncio.gather:
    - 2 overall queries (endgame games, non-endgame games)
    - 6 per-type queries (one per endgame class integer 1-6)

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
    endgame_stmt = _apply_game_filters(
        endgame_stmt, time_control, platform, rated, opponent_type, recency_cutoff
    )

    non_endgame_stmt = (
        game_cols.where(Game.id.notin_(select(endgame_game_ids_subq.c.game_id)))
        .order_by(Game.played_at.asc())
    )
    non_endgame_stmt = _apply_game_filters(
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
        return _apply_game_filters(
            stmt, time_control, platform, rated, opponent_type, recency_cutoff
        )

    class_ints = list(_ENDGAME_CLASS_INTS)
    per_class_stmts = [_per_class_stmt(ci) for ci in class_ints]

    # Run all 8 queries concurrently
    all_results = await asyncio.gather(
        session.execute(endgame_stmt),
        session.execute(non_endgame_stmt),
        *[session.execute(s) for s in per_class_stmts],
    )

    endgame_rows = list(all_results[0].fetchall())
    non_endgame_rows = list(all_results[1].fetchall())
    per_type_rows: dict[int, list[tuple]] = {
        class_int: list(all_results[2 + i].fetchall())
        for i, class_int in enumerate(class_ints)
    }

    return endgame_rows, non_endgame_rows, per_type_rows

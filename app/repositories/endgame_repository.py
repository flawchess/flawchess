"""Endgame repository: DB queries for endgame analytics.

Two functions:
- query_endgame_entry_rows: one row per game at the endgame transition point
- query_endgame_games: paginated Game objects for a given endgame class
"""

import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition

# material_count threshold for endgame classification.
# Positions with material_count strictly below this value are classified as endgame phase.
# The value 2600 corresponds to most major-piece endgames (full opening value is ~7800).
ENDGAME_MATERIAL_THRESHOLD = 2600


async def query_endgame_entry_rows(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> list[tuple]:
    """Return one row per game at the endgame transition point.

    The endgame transition point is the first position (MIN ply) per game where
    material_count < ENDGAME_MATERIAL_THRESHOLD. The material_signature and
    user_material_imbalance at that ply determine the endgame class and
    conversion/recovery classification.

    Returns rows of: (game_id, result, user_color, material_signature, user_material_imbalance)

    user_material_imbalance = material_imbalance if user_color == "white" else -material_imbalance.
    This sign flip normalizes to user perspective: positive = user has more material.

    NO color filter is applied per D-02 — stats cover both white and black games.
    """
    # Subquery: find MIN ply per game where material_count < threshold
    entry_ply_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            func.min(GamePosition.ply).label("entry_ply"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.material_count.isnot(None),
            GamePosition.material_count < ENDGAME_MATERIAL_THRESHOLD,
        )
        .group_by(GamePosition.game_id)
        .subquery("entry_ply")
    )

    # Sign flip for black: material_imbalance is always from white's perspective in DB.
    # Multiply by -1 when user is black so positive value = user has more material.
    color_sign = case(
        (Game.user_color == "white", 1),
        else_=-1,
    )

    # Join back to game_positions to get material_signature and imbalance at entry ply.
    # Then join to games for game metadata and filters.
    stmt = (
        select(
            Game.id.label("game_id"),
            Game.result,
            Game.user_color,
            GamePosition.material_signature,
            (GamePosition.material_imbalance * color_sign).label("user_material_imbalance"),
        )
        .join(
            entry_ply_subq,
            Game.id == entry_ply_subq.c.game_id,
        )
        .join(
            GamePosition,
            (GamePosition.game_id == Game.id)
            & (GamePosition.ply == entry_ply_subq.c.entry_ply)
            & (GamePosition.user_id == user_id),
        )
        .where(
            Game.user_id == user_id,
            GamePosition.material_signature.isnot(None),
        )
    )

    # Apply standard game filters
    stmt = _apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_endgame_games(
    session: AsyncSession,
    user_id: int,
    endgame_class: str,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    offset: int,
    limit: int,
) -> tuple[list[Game], int]:
    """Return paginated Game objects for games whose endgame entry point is the given class.

    Approach: fetch all entry rows, classify in Python (simpler and correct for expected
    data volumes of hundreds of games per user), then paginate.

    Returns (games_list, matched_count) for pagination.
    matched_count reflects all matching games (before offset/limit).
    """
    # Import here to avoid circular import at module level
    from app.services.endgame_service import classify_endgame_class

    # Fetch all entry rows for this user under the given filters
    all_rows = await query_endgame_entry_rows(
        session,
        user_id=user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=recency_cutoff,
    )

    # Filter game IDs matching the requested endgame class in Python
    matching_game_ids = [
        game_id
        for game_id, _result, _user_color, material_signature, _imbalance in all_rows
        if material_signature and classify_endgame_class(material_signature) == endgame_class
    ]

    matched_count = len(matching_game_ids)

    if matched_count == 0:
        return [], 0

    # Paginate: slice the game_id list (maintain most-recent order via DB sort below)
    page_ids = matching_game_ids[offset : offset + limit]

    if not page_ids:
        return [], matched_count

    # Fetch Game objects for the page, ordered most recent first
    games_stmt = (
        select(Game)
        .where(Game.id.in_(page_ids))
        .order_by(Game.played_at.desc().nulls_last())
    )
    games_result = await session.execute(games_stmt)
    games = list(games_result.scalars().all())

    return games, matched_count


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

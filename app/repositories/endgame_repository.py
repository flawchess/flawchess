"""Endgame repository: DB queries for endgame analytics.

Functions:
- query_endgame_entry_rows: one row per (game, endgame_class) span meeting the ply threshold
- query_endgame_games: paginated Game objects for a given endgame class
- query_endgame_performance_rows: endgame and non-endgame game rows for performance comparison
- query_endgame_timeline_rows: rows for rolling-window time series, overall and per-type
- query_clock_stats_rows: rows for time pressure at endgame entry (Phase 54)
- query_endgame_elo_timeline_rows: bucket + all-game rows per-combo for Phase 57 Endgame ELO timeline
"""

import datetime
from collections.abc import Sequence
from typing import Any

from sqlalchemy import case, func, select, type_coerce
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by
from sqlalchemy.engine import Row
from sqlalchemy.types import Float as FloatType
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


def _any_endgame_ply_subquery(user_id: int) -> Any:
    """Subquery returning game_ids that spent >= ENDGAME_PLY_THRESHOLD plies in any endgame class.

    Single source of truth for "game reached an endgame phase" across the entire endgame
    tab. A game qualifies if its TOTAL endgame plies (summed across all classes — e.g.
    3 plies in KP_KP plus 3 plies in KR_KR = 6) meet the threshold. This keeps the
    binary "has endgame" split consistent with the per-class stats: a game can no longer
    appear in the binary split without also being eligible for at least one per-class
    aggregate (possibly after splitting its plies across classes).

    Used by `count_endgame_games`, `query_endgame_performance_rows`, and indirectly by
    `query_endgame_bucket_rows` (which re-applies the same HAVING on its own subquery).
    Per quick-260414-ae4.
    """
    return (
        select(GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("any_endgame_game_ids")
    )


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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> int:
    """Count ALL games for the user matching the given filters.

    This counts total games regardless of whether they reached an endgame phase,
    used to provide context like "X of Y games reached an endgame".
    """
    stmt = select(func.count()).select_from(Game).where(Game.user_id == user_id)
    stmt = apply_game_filters(
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def count_endgame_games(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> int:
    """Count games that reached an endgame phase per the uniform ENDGAME_PLY_THRESHOLD rule.

    Delegates to `_any_endgame_ply_subquery`, so only games with at least
    ENDGAME_PLY_THRESHOLD total endgame plies are counted. Used for the summary line
    "X of Y games reached an endgame phase".
    """
    endgame_subq = _any_endgame_ply_subquery(user_id)
    stmt = (
        select(func.count())
        .select_from(Game)
        .where(
            Game.user_id == user_id,
            Game.id.in_(select(endgame_subq.c.game_id)),
        )
    )
    stmt = apply_game_filters(
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
        func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    # Imbalance 4 plies after entry — used for persistence check.
    # A game can exit and re-enter the same endgame class (e.g. via promotion),
    # making the GROUP BY (game_id, endgame_class) combine non-contiguous plies.
    # We must verify that the 5th ply is exactly 4 after the 1st (contiguous span);
    # otherwise the persistence value comes from a different game segment and is
    # meaningless. Returns NULL for non-contiguous spans, which the service layer's
    # "is not None" check correctly excludes from conversion/recovery.
    raw_imbalance_after = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    ply_at_persistence = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.ply, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    imbalance_after_persistence_agg = case(
        (ply_at_persistence == func.min(GamePosition.ply) + PERSISTENCE_PLIES, raw_imbalance_after),
        else_=None,
    )

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
    stmt = apply_game_filters(
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_endgame_bucket_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> list[Row[Any]]:
    """Return exactly one row per endgame game for conv/even/recov bucketing.

    Applies the uniform ENDGAME_PLY_THRESHOLD HAVING (per quick-260414-ae4) so the row
    set stays aligned with `_any_endgame_ply_subquery` — both the binary
    "has endgame" split and this per-game bucket query count the same population,
    preserving the invariant `sum(material_rows.games) == endgame_wdl.total` by
    construction.

    Returns rows of: (game_id, endgame_class, result, user_color,
    user_material_imbalance, user_material_imbalance_after)

    Tuple shape matches `query_endgame_entry_rows` so callers of
    `_compute_score_gap_material` can swap queries without change. The
    `endgame_class` column here is the class of the FIRST endgame position
    for the game (purely informational — bucketing is game-level and no
    longer tiebreaks on it).

    Semantics:
    - One row per endgame game (no per-class split).
    - `user_material_imbalance` = material_imbalance at the game's first
      endgame position, sign-flipped for black so positive = user ahead.
    - `user_material_imbalance_after` = material_imbalance 4 plies later in
      the SAME game, but only if that position ALSO has
      `endgame_class IS NOT NULL`. If the endgame ended (or the game
      ended) within 4 plies, this is NULL and the game routes to the
      "parity" bucket via the NULL-handling rule in
      `_compute_score_gap_material`.
    """
    # Single per-game aggregation: pull entry endgame_class, entry material_imbalance,
    # and material_imbalance at entry+PERSISTENCE_PLIES from one index-only scan over
    # ix_gp_user_endgame_game (which INCLUDEs material_imbalance).
    #
    # The previous form joined two GamePosition aliases (entry_pos, after_pos) on
    # (user_id, game_id, ply) and (user_id, game_id, ply+4). The planner could not
    # reliably push the join keys into the index conditions for after_pos — for
    # users with smaller endgame populations it fell back to scanning all of the
    # user's endgame rows per outer game (3000 loops × 110k rows = 340M heap fetches).
    # Same array_agg trick already used by `query_endgame_entry_rows` (see line 175).
    entry_imbalance_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    entry_endgame_class_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.endgame_class, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    raw_imbalance_after = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    ply_at_persistence = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.ply, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    # NULL when the (entry_ply + PERSISTENCE_PLIES) position is non-contiguous (i.e.
    # the game exited the endgame between MIN(ply) and MIN(ply)+4 and re-entered
    # later). The service layer's "is not None" check then routes such games to the
    # parity bucket — same semantics as the old `after_pos.endgame_class IS NOT NULL`
    # outer-join filter.
    imbalance_after_persistence_agg = case(
        (ply_at_persistence == func.min(GamePosition.ply) + PERSISTENCE_PLIES, raw_imbalance_after),
        else_=None,
    )

    span_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            entry_endgame_class_agg.label("endgame_class"),
            entry_imbalance_agg.label("entry_imbalance"),
            imbalance_after_persistence_agg.label("entry_imbalance_after"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("first_endgame")
    )

    color_sign = case(
        (Game.user_color == "white", 1),
        else_=-1,
    )

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

    stmt = apply_game_filters(
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
    base_stmt = apply_game_filters(
        base_stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # Count total matching games (before pagination)
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    count_result = await session.execute(count_stmt)
    matched_count = count_result.scalar_one()

    if matched_count == 0:
        return [], 0

    # Paginated game objects ordered most-recent first
    games_stmt = base_stmt.order_by(Game.played_at.desc().nulls_last()).offset(offset).limit(limit)
    games_result = await session.execute(games_stmt)
    games = list(games_result.scalars().all())

    return games, matched_count


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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> tuple[list[Row[Any]], list[Row[Any]]]:
    """Return endgame and non-endgame game rows for performance comparison.

    Endgame games: games that meet the uniform ENDGAME_PLY_THRESHOLD rule — i.e. spent
    at least that many plies in any endgame class. Both endgame_rows AND non_endgame_rows
    derive from `_any_endgame_ply_subquery`, so the split is consistent by construction:
    every game is in exactly one side of the split (per quick-260414-ae4).

    Non-endgame games: all other games (including games that briefly touched an endgame
    class for fewer than ENDGAME_PLY_THRESHOLD plies — they are treated as "no endgame"
    for this split).

    Returns: (endgame_rows, non_endgame_rows) where each row is
    (played_at, result, user_color).

    Rows are ordered by played_at ASC for chronological processing.
    """
    endgame_game_ids_subq = _any_endgame_ply_subquery(user_id)

    # Base select for game rows — columns needed for WDL derivation and timeline
    game_cols = select(Game.played_at, Game.result, Game.user_color).where(
        Game.user_id == user_id,
        Game.played_at.isnot(None),
    )

    # Endgame games: id in the endgame subquery
    endgame_stmt = game_cols.where(Game.id.in_(select(endgame_game_ids_subq.c.game_id))).order_by(
        Game.played_at.asc()
    )
    endgame_stmt = apply_game_filters(
        endgame_stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # Non-endgame games: id NOT in the endgame subquery
    non_endgame_stmt = game_cols.where(
        Game.id.notin_(select(endgame_game_ids_subq.c.game_id))
    ).order_by(Game.played_at.asc())
    non_endgame_stmt = apply_game_filters(
        non_endgame_stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> tuple[list[Row[Any]], list[Row[Any]], dict[int, list[Row[Any]]]]:
    """Return rows for rolling-window time series (overall and per endgame class).

    Issues exactly 2 queries against game_positions (sequential execution is
    mandatory on the same AsyncSession).

    Query A: one pass over game_positions grouped by (game_id, endgame_class) with
    HAVING count(ply) >= ENDGAME_PLY_THRESHOLD. Returns one row per qualifying
    (game, class) span including the endgame_class column so Python can bucket them.
    The overall endgame series is derived from these rows by deduplicating per game_id.

    Query B: non-endgame games (games never reaching any qualifying endgame span),
    derived via NOT IN on the game_ids projected from the SAME (game_id, endgame_class)
    subquery used by Query A — one shared scan, one consistent definition of
    "qualified for any endgame class".

    Returns: (endgame_rows, non_endgame_rows, per_type_rows)
    where per_type_rows is dict[class_int, list[(played_at, result, user_color)]].
    All lists in per_type_rows are ordered by played_at ASC.
    All 6 class integers (1..6) are initialized (to empty lists) for deterministic iteration.

    Each row in endgame_rows and non_endgame_rows is (played_at, result, user_color).
    """
    # --- Query A: one pass returns (game_id, endgame_class, played_at, result, user_color) ---
    # Subquery: (game_id, endgame_class) pairs with >= ENDGAME_PLY_THRESHOLD plies.
    # Uses ix_gp_user_endgame_game index for an Index Only Scan.
    per_class_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.endgame_class.label("endgame_class"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id, GamePosition.endgame_class)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("per_class_spans")
    )

    # Join Game to the per-class subquery; select game data + class column.
    per_class_stmt = (
        select(
            Game.id.label("game_id"),
            per_class_subq.c.endgame_class,
            Game.played_at,
            Game.result,
            Game.user_color,
        )
        .join(per_class_subq, Game.id == per_class_subq.c.game_id)
        .where(
            Game.user_id == user_id,
            Game.played_at.isnot(None),
        )
        .order_by(Game.played_at.asc())
    )
    per_class_stmt = apply_game_filters(
        per_class_stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # Execute sequentially — AsyncSession is not safe for concurrent use from
    # multiple coroutines, and a single session uses one DB connection so there's
    # no concurrency benefit from asyncio.gather here.
    per_class_result = await session.execute(per_class_stmt)
    per_class_raw = list(per_class_result.fetchall())

    # --- Python-side bucketing (no extra DB round trips) ---
    # Initialize all 6 class slots to empty lists so downstream callers can
    # iterate deterministically even when some classes have no data.
    per_type_rows: dict[int, list[Row[Any]]] = {ci: [] for ci in _ENDGAME_CLASS_INTS}

    # Deduplicate per game_id for the overall endgame series.
    # Walk rows once: bucket by class, and collect one (played_at, result, user_color)
    # row per distinct game_id (first seen = earliest class span, already ordered ASC).
    seen_game_ids: set[int] = set()
    endgame_rows_unsorted: list[tuple] = []

    for row in per_class_raw:
        game_id = row.game_id
        class_int = row.endgame_class
        # Strip endgame_class: service layer expects 3-tuple (played_at, result, user_color)
        three_tuple = (row.played_at, row.result, row.user_color)
        per_type_rows[class_int].append(three_tuple)  # ty: ignore[invalid-argument-type] — 3-tuple compatible with Row consumer
        if game_id not in seen_game_ids:
            seen_game_ids.add(game_id)
            endgame_rows_unsorted.append(three_tuple)

    # Sort the deduplicated overall series by played_at ASC (same ordering as Query B).
    endgame_rows: list[Row[Any]] = sorted(  # ty: ignore[invalid-assignment] — plain tuples are Row-compatible for service consumers
        endgame_rows_unsorted, key=lambda r: r[0]
    )

    # --- Query B: non-endgame games (games never reaching any qualifying span) ---
    # Reuse per_class_subq from Query A — its game_id column yields duplicates
    # across classes, but Game.id.notin_(...) handles that correctly. This
    # guarantees identical semantics (same HAVING, same class filter) with a
    # single GamePosition scan shared between the two branches.
    game_cols = select(Game.played_at, Game.result, Game.user_color).where(
        Game.user_id == user_id,
        Game.played_at.isnot(None),
    )

    non_endgame_stmt = game_cols.where(Game.id.notin_(select(per_class_subq.c.game_id))).order_by(
        Game.played_at.asc()
    )
    non_endgame_stmt = apply_game_filters(
        non_endgame_stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    non_endgame_result = await session.execute(non_endgame_stmt)
    non_endgame_rows: list[Row[Any]] = list(non_endgame_result.fetchall())

    return endgame_rows, non_endgame_rows, per_type_rows


async def query_clock_stats_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> list[Row[Any]]:
    """Return rows for Time Pressure at Endgame Entry and Time Pressure vs Performance.

    One row per GAME that reached an endgame phase under the whole-game rule:
    total endgame plies (across all classes combined) >= ENDGAME_PLY_THRESHOLD.

    This matches the definition used by count_endgame_games and
    query_endgame_performance_rows, so the Time Pressure sections include every game
    that the rest of the endgame tab counts as an endgame — even games whose plies
    are split across multiple classes (e.g. 4 in KP_KP plus 4 in KR_KR, neither of
    which hits the threshold alone).

    Returns rows of: (game_id, time_control_bucket, base_time_seconds, termination,
                      result, user_color, ply_array, clock_array, played_at)

    base_time_seconds: the actual starting clock for that game (e.g. 600 for 600+0,
    900 for 900+10). Used as the per-game denominator for % computations in
    _compute_clock_pressure and _compute_time_pressure_chart (quick-260414-smt).

    ply_array: array_agg(ply ORDER BY ply) — all endgame plies in the game
    clock_array: array_agg(clock_seconds ORDER BY ply) — clock at each endgame ply
    played_at: game start timestamp — consumed by _compute_clock_pressure_timeline
        to build a weekly rolling-window series (quick-260416-w3q). Unused by the
        existing table/chart consumers, which ignore trailing columns.

    Ordering by ply ensures _extract_entry_clocks finds the earliest user-parity and
    opp-parity clocks (the moment the game first reached an endgame phase, regardless
    of which endgame class came first).

    NO color filter is applied — stats cover both white and black games.

    Bug fix (quick-260414-pv4): previously this query grouped by (game_id,
    endgame_class) with a per-class HAVING count >= 6, which (1) excluded games whose
    endgame plies were split across classes and (2) returned multiple rows per game,
    leading to double-counting in _compute_time_pressure_chart and requiring a
    fragile Python-side collapse in _compute_clock_pressure. The whole-game rule via
    _any_endgame_ply_subquery matches the rest of the endgame tab and makes both
    consumers straight-through aggregations.
    """
    # Aggregate full ply and clock arrays ordered by ply ascending.
    # Using type_coerce with ARRAY types so SQLAlchemy returns Python lists.
    ply_array_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.ply, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )

    clock_array_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.clock_seconds, GamePosition.ply.asc())),
        ARRAY(FloatType()),
    )

    # One row per game: aggregate all endgame plies (across all classes) and apply the
    # whole-game ENDGAME_PLY_THRESHOLD via HAVING in the same pass. Equivalent to the
    # game_id IN _any_endgame_ply_subquery filter used elsewhere, but folded into a
    # single scan — the IN form caused the planner to misestimate cardinality (every
    # row estimate at 1 vs ~110k actual) and pick a Nested Loop / Join Filter cross
    # comparison that hung indefinitely on users with many endgame games.
    per_game_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            ply_array_agg.label("ply_array"),
            clock_array_agg.label("clock_array"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("clock_per_game")
    )

    # quick-260414-smt: replaced Game.time_control_seconds (bucket-first-seen estimate,
    # base + inc*40) with Game.base_time_seconds (actual per-game starting clock).
    # This gives an apples-to-apples % denominator within each time control bucket:
    # a 1800+0 and a 600+0 rapid game each divide by their own starting clock, not
    # a shared bucket estimate that could be 600 for both (producing 250%+ for 1800s games).
    stmt = (
        select(
            Game.id.label("game_id"),
            Game.time_control_bucket,
            Game.base_time_seconds,
            Game.termination,
            Game.result,
            Game.user_color,
            per_game_subq.c.ply_array,
            per_game_subq.c.clock_array,
            Game.played_at,
        )
        .join(per_game_subq, Game.id == per_game_subq.c.game_id)
        .where(Game.user_id == user_id)
    )

    stmt = apply_game_filters(
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_endgame_elo_timeline_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> tuple[list[Row[Any]], list[Row[Any]]]:
    """Return (bucket_rows, all_rows) for the Phase 57 Endgame ELO timeline.

    bucket_rows: one row per ENDGAME game (uniform 6-ply rule via entry_subq HAVING).
        Tuple shape:
            (played_at, platform, time_control_bucket, user_color,
             white_rating, black_rating,
             user_material_imbalance, user_material_imbalance_after, result)
        where user_material_imbalance is sign-flipped for black
        (mirrors query_endgame_bucket_rows). Drives per-window skill computation
        AND avg(opponent_rating).

    all_rows: one row per ALL user games (endgame + non-endgame) for the combo.
        Tuple shape:
            (played_at, platform, time_control_bucket, user_color,
             white_rating, black_rating)
        Drives per-window mean(user_rating) for the Actual ELO line (D-04).

    Both queries:
    - Filter by Game.user_id == user_id at the TOP LEVEL (user scoping).
    - Use apply_game_filters for time_control/platform/rated/opponent_type/
      recency_cutoff/opponent_gap_{min,max}. Never duplicate filter logic.
    - Exclude rows with NULL played_at.
    - Exclude rows where white_rating IS NULL OR black_rating IS NULL (needed
      for per-side Elo math; a game without ratings can't contribute).
    - ORDER BY played_at ASC for chronological walking by the service layer.
    - Execute sequentially on the same session (AsyncSession is not safe for
      gather; single connection anyway).

    The `recency_cutoff` param is deliberately forwarded to apply_game_filters
    but the orchestrator passes None so the rolling window pre-fills (Pitfall 2
    in 57-RESEARCH.md). Callers filter emitted timeline points afterwards.
    """
    # ── bucket_rows: one row per endgame game (uniform 6-ply rule) ─────────
    # Single per-game aggregation (mirrors query_endgame_bucket_rows / _entry_rows).
    # Avoids two GamePosition self-joins whose plan was unstable across users — the
    # planner couldn't reliably push (game_id, ply+4) into after_pos's index cond
    # and would scan the user's full endgame population per outer game.
    entry_imbalance_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    raw_imbalance_after = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.material_imbalance, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    ply_at_persistence = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.ply, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[PERSISTENCE_PLIES + 1]

    imbalance_after_persistence_agg = case(
        (ply_at_persistence == func.min(GamePosition.ply) + PERSISTENCE_PLIES, raw_imbalance_after),
        else_=None,
    )

    entry_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            entry_imbalance_agg.label("entry_imbalance"),
            imbalance_after_persistence_agg.label("entry_imbalance_after"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.endgame_class.isnot(None),
        )
        .group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("elo_entry")
    )

    color_sign = case(
        (Game.user_color == "white", 1),
        else_=-1,
    )

    bucket_stmt = (
        select(
            Game.played_at,
            Game.platform,
            Game.time_control_bucket,
            Game.user_color,
            Game.white_rating,
            Game.black_rating,
            (entry_subq.c.entry_imbalance * color_sign).label("user_material_imbalance"),
            (entry_subq.c.entry_imbalance_after * color_sign).label(
                "user_material_imbalance_after"
            ),
            Game.result,
        )
        .join(entry_subq, Game.id == entry_subq.c.game_id)
        .where(
            Game.user_id == user_id,
            Game.played_at.isnot(None),
            Game.white_rating.isnot(None),
            Game.black_rating.isnot(None),
        )
        .order_by(Game.played_at.asc())
    )
    bucket_stmt = apply_game_filters(
        bucket_stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # ── all_rows: one row per user game (endgame + non-endgame) ─────────────
    all_stmt = (
        select(
            Game.played_at,
            Game.platform,
            Game.time_control_bucket,
            Game.user_color,
            Game.white_rating,
            Game.black_rating,
        )
        .where(
            Game.user_id == user_id,
            Game.played_at.isnot(None),
            Game.white_rating.isnot(None),
            Game.black_rating.isnot(None),
        )
        .order_by(Game.played_at.asc())
    )
    all_stmt = apply_game_filters(
        all_stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    # Execute sequentially — AsyncSession is not safe for concurrent use from
    # multiple coroutines, and a single session uses one DB connection so
    # asyncio.gather provides no benefit (CLAUDE.md §Critical Constraints).
    bucket_result = await session.execute(bucket_stmt)
    all_result = await session.execute(all_stmt)
    return list(bucket_result.fetchall()), list(all_result.fetchall())

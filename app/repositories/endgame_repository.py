"""Endgame repository: DB queries for endgame analytics.

Functions:
- query_endgame_entry_rows: one row per (game, endgame_class) span meeting the ply threshold
- query_endgame_games: paginated Game objects for a given endgame class
- query_endgame_performance_rows: endgame and non-endgame game rows for performance comparison
- query_clock_stats_rows: rows for time pressure at endgame entry (Phase 54)
"""

import datetime
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, type_coerce
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by
from sqlalchemy.engine import Row
from sqlalchemy.types import Float as FloatType
from sqlalchemy.types import SmallInteger as SmallIntegerType
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.query_utils import apply_game_filters, game_ids_any_predicate
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


def _any_endgame_ply_subquery(user_id: int, game_ids: Sequence[int] | None = None) -> Any:
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

    Phase 238: `game_ids` (default None = unchanged SQL) additionally restricts the
    per-game aggregation to the given game ids, so the on-read ranked path scans only
    the ranked games' positions instead of every endgame position the user has. The
    HAVING counts rows within each retained game, so the restriction does not change
    any retained game's count.
    """
    stmt = select(GamePosition.game_id).where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    if game_ids is not None:
        stmt = stmt.where(game_ids_any_predicate(GamePosition.game_id, game_ids))
    return (
        stmt.group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("any_endgame_game_ids")
    )


async def count_filtered_games(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
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
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
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
    from_date: datetime.date | None,
    to_date: datetime.date | None,
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
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
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
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    game_ids: Sequence[int] | None = None,
) -> list[Row[Any]]:
    """Return one row per (game, endgame_class) span meeting the ply threshold.

    Per D-02: a game can appear in MULTIPLE endgame classes if it spent >= ENDGAME_PLY_THRESHOLD
    plies in each class. Per REFAC-02: eval_cp/eval_mate at the FIRST position of each class span
    determines conversion/recovery classification via _classify_endgame_bucket in the service layer.

    Returns rows of:
        (game_id, endgame_class, result, user_color,
         eval_cp, eval_mate, next_entry_eval_cp, next_entry_eval_mate, played_at,
         time_control_bucket)
    where endgame_class is an integer (1-6, see EndgameClassInt).

    Phase 98 fix: `time_control_bucket` (col 9) lets the per-(class × TC) type
    breakdown (`aggregate_endgame_stats_by_tc`) group these per-class spans by TC.
    The earlier implementation grouped `query_endgame_bucket_rows` (one row per
    game, class = first endgame position) which classified almost every game as
    "mixed", leaving the rook/minor/pawn/queen tiles empty.

    eval_cp and eval_mate are white-perspective Stockfish eval at the span-entry ply.
    NO sign flip in SQL — the service layer's _classify_endgame_bucket applies the
    user-color flip. NULL eval (engine error / not yet backfilled) is handled by the
    service layer as parity.

    Phase 87.1 (SEED-016 D-06): next_entry_eval_cp / next_entry_eval_mate are the
    span-entry eval of the NEXT span in the same game (ordered by span_min_ply ASC),
    computed via LEAD() window over (game_id, span_min_ply). For the LAST span in a
    game (terminal span), both fields are NULL — the service layer falls back to
    `(result, user_color)` for the exit score. The min(ply) used for ordering is
    computed during the existing GROUP BY at no extra scan cost, since ply is the
    sort key of the ix_gp_user_endgame_game index covering this query.

    NO color filter is applied per D-02 — stats cover both white and black games.

    Phase 238: `game_ids` (default None = unchanged SQL) restricts the rows, and the inner
    per-span aggregation, to the on-read ranked-sample game ids.
    """
    # Single subquery: group by (game_id, endgame_class), count plies per span,
    # AND grab eval_cp/eval_mate at entry ply via array_agg ordered by ply.
    # The INCLUDE(eval_cp, eval_mate) on ix_gp_user_endgame_game enables index-only scans
    # for array_agg(eval_cp ORDER BY ply) and array_agg(eval_mate ORDER BY ply).
    #
    # (array_agg(eval_cp ORDER BY ply))[1] gets the value at the min ply
    # without needing a separate lookup join.
    entry_eval_cp_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.eval_cp, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    entry_eval_mate_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.eval_mate, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    span_stmt = select(
        GamePosition.game_id.label("game_id"),
        GamePosition.endgame_class.label("endgame_class"),
        entry_eval_cp_agg.label("entry_eval_cp"),
        entry_eval_mate_agg.label("entry_eval_mate"),
        # Phase 87.1 (SEED-016 D-06): span_min_ply orders spans within a game
        # so the LEAD() window can look up the NEXT span's entry eval. Computed
        # during the existing GROUP BY at zero extra scan cost (ply is already
        # the sort key of ix_gp_user_endgame_game).
        func.min(GamePosition.ply).label("span_min_ply"),
    ).where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    if game_ids is not None:
        # Phase 238: aggregate only the ranked games' positions (bound-array ANY, never
        # an IN (subquery); see query_clock_stats_rows for the planner hang).
        span_stmt = span_stmt.where(game_ids_any_predicate(GamePosition.game_id, game_ids))
    span_subq = (
        span_stmt.group_by(GamePosition.game_id, GamePosition.endgame_class)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("span")
    )

    # Phase 87.1 (SEED-016 D-06): wrap span_subq with a LEAD() window so each span
    # row also carries the entry eval of the NEXT span in the same game (ordered by
    # span_min_ply ASC). Terminal spans (the last per game) get NULL on both new
    # columns — the service layer treats that as "use game result as exit score".
    # The window runs on the per-span result set (~ <=6 rows per game), so cost is
    # O(spans_per_game) and adds no extra scan over game_positions.
    span_with_next = select(
        span_subq.c.game_id,
        span_subq.c.endgame_class,
        span_subq.c.entry_eval_cp,
        span_subq.c.entry_eval_mate,
        span_subq.c.span_min_ply,
        func.lead(span_subq.c.entry_eval_cp)
        .over(
            partition_by=span_subq.c.game_id,
            order_by=span_subq.c.span_min_ply.asc(),
        )
        .label("next_entry_eval_cp"),
        func.lead(span_subq.c.entry_eval_mate)
        .over(
            partition_by=span_subq.c.game_id,
            order_by=span_subq.c.span_min_ply.asc(),
        )
        .label("next_entry_eval_mate"),
    ).subquery("span_with_next")

    # Main query: join Game -> span_with_next (no second subquery needed).
    # eval_cp and eval_mate are projected raw (white-perspective, no SQL color flip).
    # The service layer's _classify_endgame_bucket(eval_cp, eval_mate, user_color)
    # applies the sign flip at read time (REFAC-02).
    stmt = (
        select(
            Game.id.label("game_id"),
            span_with_next.c.endgame_class,
            Game.result,
            Game.user_color,
            span_with_next.c.entry_eval_cp.label("eval_cp"),
            span_with_next.c.entry_eval_mate.label("eval_mate"),
            # Phase 87.1 (SEED-016 D-06): next-span entry eval per game.
            # NULL for terminal spans — handled in service layer.
            span_with_next.c.next_entry_eval_cp.label("next_entry_eval_cp"),
            span_with_next.c.next_entry_eval_mate.label("next_entry_eval_mate"),
            # Quick task 260519-lu0: played_at for MAX(played_at) per category
            # (drives last_played_at in EndgameCategoryStats / PositionResultsPanel).
            Game.played_at.label("played_at"),
            # Phase 98 fix: per-(class × TC) type breakdown groups these per-class
            # spans by TC. Appended (col 9) so existing positional/test consumers of
            # cols 0-8 are unaffected; all prod consumers use named Row access.
            Game.time_control_bucket.label("time_control_bucket"),
        )
        .join(span_with_next, Game.id == span_with_next.c.game_id)
        .where(Game.user_id == user_id)
    )

    # Apply standard game filters
    stmt = apply_game_filters(
        stmt,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        game_ids=game_ids,
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
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    game_ids: Sequence[int] | None = None,
) -> list[Row[Any]]:
    """Return exactly one row per endgame game for conv/even/recov bucketing.

    Applies the uniform ENDGAME_PLY_THRESHOLD HAVING (per quick-260414-ae4) so the row
    set stays aligned with `_any_endgame_ply_subquery` — both the binary
    "has endgame" split and this per-game bucket query count the same population,
    preserving the invariant `sum(material_rows.games) == endgame_wdl.total` by
    construction.

    Returns rows of:
        (game_id, endgame_class, result, user_color, eval_cp, eval_mate,
         time_control_bucket, next_entry_eval_cp, next_entry_eval_mate)

    Tuple shape matches `query_endgame_entry_rows` for columns 0-5. Columns 6-8
    are additive and not consumed by existing callers (`_aggregate_bucket_counts`
    uses named attribute access on columns 0-5 only). The `endgame_class` column
    here is the class of the FIRST endgame position for the game (purely
    informational — bucketing is game-level and no longer tiebreaks on it).

    Phase 97: `time_control_bucket` (column 6) enables per-TC grouping in
    `_compute_per_tc_metric_cards`. `next_entry_eval_cp` / `next_entry_eval_mate`
    (columns 7-8) are LEAD() window columns mirroring `query_endgame_entry_rows`.
    Since this query groups by game_id (one row per game), the LEAD partition
    always contains a single row — both next-eval columns are always NULL,
    making every bucket row a "terminal span" that uses the game result as exit
    score in `compute_span_gap`. This is semantically correct for the per-game
    bucket aggregation.

    Semantics:
    - One row per endgame game (no per-class split).
    - `eval_cp` / `eval_mate` = Stockfish eval at the game's first endgame position
      (white-perspective raw). NO sign flip in SQL — the service layer's
      _classify_endgame_bucket applies the user-color flip (REFAC-02).
    - NULL eval (engine error / not yet backfilled) routes to the "parity" bucket
      via NULL-handling in _classify_endgame_bucket.

    Phase 238: `game_ids` (default None = unchanged SQL) restricts the rows, and the inner
    per-game aggregation, to the on-read ranked-sample game ids.
    """
    # Single per-game aggregation: pull entry endgame_class, eval_cp, eval_mate
    # from one index-only scan over ix_gp_user_endgame_game (INCLUDE(eval_cp, eval_mate)).
    # Same array_agg trick already used by `query_endgame_entry_rows` (see line 175).
    entry_endgame_class_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.endgame_class, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    entry_eval_cp_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.eval_cp, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    entry_eval_mate_agg = type_coerce(
        func.array_agg(aggregate_order_by(GamePosition.eval_mate, GamePosition.ply.asc())),
        ARRAY(SmallIntegerType),
    )[1]

    first_endgame_stmt = select(
        GamePosition.game_id.label("game_id"),
        entry_endgame_class_agg.label("endgame_class"),
        entry_eval_cp_agg.label("entry_eval_cp"),
        entry_eval_mate_agg.label("entry_eval_mate"),
        # Phase 97: span_min_ply used as the LEAD() window ordering key.
        # Since bucket_rows groups by game_id (one row per game), the LEAD
        # partition contains exactly one row so next_entry_eval_* are always
        # NULL — but the LEAD() syntax requires an ORDER BY column.
        func.min(GamePosition.ply).label("span_min_ply"),
    ).where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    if game_ids is not None:
        # Phase 238: aggregate only the ranked games' positions (bound-array ANY).
        first_endgame_stmt = first_endgame_stmt.where(
            game_ids_any_predicate(GamePosition.game_id, game_ids)
        )
    span_subq = (
        first_endgame_stmt.group_by(GamePosition.game_id)
        .having(func.count(GamePosition.ply) >= ENDGAME_PLY_THRESHOLD)
        .subquery("first_endgame")
    )

    # Phase 97: wrap span_subq with a LEAD() window to add next-eval columns,
    # mirroring the pattern in query_endgame_entry_rows (lines 226-244).
    # The partition is per game_id; since there is one row per game, LEAD always
    # returns NULL on both columns (terminal span semantics).
    span_with_next = select(
        span_subq.c.game_id,
        span_subq.c.endgame_class,
        span_subq.c.entry_eval_cp,
        span_subq.c.entry_eval_mate,
        func.lead(span_subq.c.entry_eval_cp)
        .over(
            partition_by=span_subq.c.game_id,
            order_by=span_subq.c.span_min_ply.asc(),
        )
        .label("next_entry_eval_cp"),
        func.lead(span_subq.c.entry_eval_mate)
        .over(
            partition_by=span_subq.c.game_id,
            order_by=span_subq.c.span_min_ply.asc(),
        )
        .label("next_entry_eval_mate"),
    ).subquery("bucket_with_next")

    # eval_cp and eval_mate are projected raw (white-perspective, no SQL color flip).
    # The service layer's _classify_endgame_bucket(eval_cp, eval_mate, user_color)
    # applies the sign flip at read time (REFAC-02).
    stmt = (
        select(
            Game.id.label("game_id"),
            span_with_next.c.endgame_class,
            Game.result,
            Game.user_color,
            span_with_next.c.entry_eval_cp.label("eval_cp"),
            span_with_next.c.entry_eval_mate.label("eval_mate"),
            # Phase 97: time_control_bucket (column 6) for per-TC grouping.
            Game.time_control_bucket,
            # Phase 97: LEAD next-entry-eval columns (columns 7-8) for span gap computation.
            # Always NULL for bucket_rows (one row per game -> terminal span).
            span_with_next.c.next_entry_eval_cp.label("next_entry_eval_cp"),
            span_with_next.c.next_entry_eval_mate.label("next_entry_eval_mate"),
        )
        .join(span_with_next, Game.id == span_with_next.c.game_id)
        .where(Game.user_id == user_id)
    )

    stmt = apply_game_filters(
        stmt,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        game_ids=game_ids,
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
    from_date: datetime.date | None,
    to_date: datetime.date | None,
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
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
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


async def query_endgame_performance_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    game_ids: Sequence[int] | None = None,
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
    (played_at, result, user_color, platform, time_control_bucket).

    The platform / time_control_bucket columns were added in Phase 87.5 so the
    orchestrator can partition both row streams per (platform, TC) combo before
    deriving the per-combo Endgame Score Gap series that drives the Endgame ELO
    timeline.

    Rows are ordered by played_at ASC for chronological processing.

    Phase 238: `game_ids` (default None) restricts both row sets, and the endgame
    subquery, to the given ranked-sample game ids.
    """
    endgame_game_ids_subq = _any_endgame_ply_subquery(user_id, game_ids)

    # Base select for game rows — columns needed for WDL derivation, timeline,
    # and (Phase 87.5) per-combo partitioning. Per-side opponent ratings are
    # NOT projected here: the Phase 87.6 amendment (logistic-anchored stretch
    # around Actual ELO) derives Endgame ELO directly from per-side score and
    # the asof-joined Actual ELO, so opponent ratings are never read.
    game_cols = select(
        Game.played_at,
        Game.result,
        Game.user_color,
        Game.platform,
        Game.time_control_bucket,
    ).where(
        Game.user_id == user_id,
        Game.played_at.isnot(None),
    )

    # Endgame games: id in the endgame subquery
    endgame_stmt = game_cols.where(Game.id.in_(select(endgame_game_ids_subq.c.game_id))).order_by(
        Game.played_at.asc()
    )
    endgame_stmt = apply_game_filters(
        endgame_stmt,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        game_ids=game_ids,
    )

    # Non-endgame games: id NOT in the endgame subquery
    non_endgame_stmt = game_cols.where(
        Game.id.notin_(select(endgame_game_ids_subq.c.game_id))
    ).order_by(Game.played_at.asc())
    non_endgame_stmt = apply_game_filters(
        non_endgame_stmt,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        game_ids=game_ids,
    )

    # Execute sequentially — AsyncSession is not safe for concurrent use from
    # multiple coroutines, and a single session uses one DB connection so there's
    # no concurrency benefit from asyncio.gather here.
    endgame_result = await session.execute(endgame_stmt)
    non_endgame_result = await session.execute(non_endgame_stmt)

    return list(endgame_result.fetchall()), list(non_endgame_result.fetchall())


async def query_clock_stats_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    game_ids: Sequence[int] | None = None,
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

    Ordering by ply ensures extract_entry_clocks finds the earliest user-parity and
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

    Phase 238: `game_ids` (default None = unchanged SQL) restricts the rows, and the inner
    per-game aggregation, to the on-read ranked-sample game ids.
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
    per_game_stmt = select(
        GamePosition.game_id.label("game_id"),
        ply_array_agg.label("ply_array"),
        clock_array_agg.label("clock_array"),
    ).where(
        GamePosition.user_id == user_id,
        GamePosition.endgame_class.isnot(None),
    )
    if game_ids is not None:
        # Phase 238: aggregate only the ranked games' positions. A bound-array ANY, not
        # the IN (subquery) form the comment above documents as hanging the planner.
        per_game_stmt = per_game_stmt.where(game_ids_any_predicate(GamePosition.game_id, game_ids))
    per_game_subq = (
        per_game_stmt.group_by(GamePosition.game_id)
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
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        game_ids=game_ids,
    )

    result = await session.execute(stmt)
    return list(result.fetchall())


# Phase 88.1 (D-07 supersedes D-05, REVIEW.md CR-01): query_cohort_clock_rows
# removed. The cohort layer was replaced by a same-game opponent-quintile split
# in endgame_service.iterate_clock_rows / build_quintile_bullets, which uses
# only the existing query_clock_stats_rows. See 88-CONTEXT.md D-07 for the design.

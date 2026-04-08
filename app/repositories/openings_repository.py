"""Openings repository: DB queries for position-based W/D/L lookups."""

import datetime
from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD, apply_game_filters

# Maps match_side values to the corresponding GamePosition hash column.
HASH_COLUMN_MAP = {
    "white": GamePosition.white_hash,
    "black": GamePosition.black_hash,
    "full": GamePosition.full_hash,
}


def _build_base_query(
    select_entity: Any,
    user_id: int,
    hash_column: Any | None,
    target_hash: int | None,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> Any:
    """Build a filtered SELECT that joins game_positions -> games.

    When ``target_hash`` is None, queries all games for the user directly from
    the ``games`` table without a position filter.  When ``target_hash`` is
    provided, joins ``game_positions`` and filters by hash, using DISTINCT ON
    game.id to avoid counting a game multiple times when the target hash appears
    at more than one ply.

    ``select_entity`` may be a single ORM entity/column or a list of columns.
    When a list is provided the columns are unpacked into ``select()``.
    """
    entities = select_entity if isinstance(select_entity, list) else [select_entity]

    if target_hash is not None and hash_column is not None:
        # Position-filtered query: join game_positions and filter by hash
        base = (
            select(*entities)
            .join(GamePosition, GamePosition.game_id == Game.id)
            .where(
                GamePosition.user_id == user_id,
                hash_column == target_hash,
            )
            .distinct(Game.id)
        )
    else:
        # All-games query: no position filter, query games table directly
        base = select(*entities).where(Game.user_id == user_id)

    if time_control is not None:
        base = base.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        base = base.where(Game.platform.in_(platform))
    if rated is not None:
        base = base.where(Game.rated == rated)
    if opponent_type == "human":
        base = base.where(Game.is_computer_game == False)  # noqa: E712
    elif opponent_type == "bot":
        base = base.where(Game.is_computer_game == True)  # noqa: E712
    # "both" = no filter
    if recency_cutoff is not None:
        base = base.where(Game.played_at >= recency_cutoff)
    if color is not None:
        base = base.where(Game.user_color == color)
    if opponent_strength != "any":
        user_rating = case(
            (Game.user_color == "white", Game.white_rating),
            else_=Game.black_rating,
        )
        opp_rating = case(
            (Game.user_color == "white", Game.black_rating),
            else_=Game.white_rating,
        )
        base = base.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
        if opponent_strength == "stronger":
            base = base.where(opp_rating >= user_rating + elo_threshold)
        elif opponent_strength == "similar":
            base = base.where(
                opp_rating > user_rating - elo_threshold,
                opp_rating < user_rating + elo_threshold,
            )
        elif opponent_strength == "weaker":
            base = base.where(opp_rating <= user_rating - elo_threshold)

    return base


async def query_time_series(
    session: AsyncSession,
    user_id: int,
    hash_column: Any,
    target_hash: int,
    color: str | None,
    time_control: Sequence[str] | None = None,
    platform: Sequence[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    recency_cutoff: datetime.datetime | None = None,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> list[Row[Any]]:
    """Return (played_at, result, user_color) tuples for matching games, ordered chronologically.

    Returns per-game rows ordered by played_at ASC so the service can compute
    rolling window win rates over trailing games.

    DISTINCT by Game.id prevents games with the target hash at multiple plies
    from being counted more than once.  Games without played_at are excluded.
    """
    stmt = (
        select(Game.played_at, Game.result, Game.user_color)
        .join(GamePosition, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            hash_column == target_hash,
            Game.played_at.isnot(None),
        )
        .distinct(Game.id)
        .order_by(Game.id, Game.played_at)
    )
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
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
    if opponent_strength != "any":
        user_rating = case(
            (Game.user_color == "white", Game.white_rating),
            else_=Game.black_rating,
        )
        opp_rating = case(
            (Game.user_color == "white", Game.black_rating),
            else_=Game.white_rating,
        )
        stmt = stmt.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
        if opponent_strength == "stronger":
            stmt = stmt.where(opp_rating >= user_rating + elo_threshold)
        elif opponent_strength == "similar":
            stmt = stmt.where(
                opp_rating > user_rating - elo_threshold,
                opp_rating < user_rating + elo_threshold,
            )
        elif opponent_strength == "weaker":
            stmt = stmt.where(opp_rating <= user_rating - elo_threshold)

    # Wrap in subquery so outer query can order by played_at ASC after DISTINCT ON Game.id
    subq = stmt.subquery()
    ordered = select(subq).order_by(subq.c.played_at.asc())
    rows = await session.execute(ordered)
    return list(rows.all())


async def query_all_results(
    session: AsyncSession,
    user_id: int,
    hash_column: Any | None,
    target_hash: int | None,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> list[Row[Any]]:
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
        opponent_type=opponent_type,
        recency_cutoff=recency_cutoff,
        color=color,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    rows = await session.execute(stmt)
    return list(rows.all())


async def query_wdl_counts(
    session: AsyncSession,
    user_id: int,
    hash_column: Any | None,
    target_hash: int | None,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> Row[Any]:
    """Return a single row (total, wins, draws, losses) via SQL aggregation.

    Wraps _build_base_query() as a subquery to get deduplicated (result,
    user_color) pairs, then applies func.count().filter() on the subquery
    columns to compute W/D/L counts in a single SQL round-trip.

    Always returns exactly one row even when no games match (all counts = 0).
    Uses the same win/draw/loss conditions as stats_repository.py to ensure
    consistent counting across all W/D/L aggregations in the codebase.
    """
    # Deduplicated (result, user_color) pairs — one row per game (DISTINCT by game_id)
    dedup = _build_base_query(
        select_entity=[Game.result, Game.user_color],
        user_id=user_id,
        hash_column=hash_column,
        target_hash=target_hash,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=recency_cutoff,
        color=color,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    ).subquery("dedup")

    # W/D/L conditions on the subquery columns (same logic as stats_repository.py)
    win_cond = or_(
        and_(dedup.c.result == "1-0", dedup.c.user_color == "white"),
        and_(dedup.c.result == "0-1", dedup.c.user_color == "black"),
    )
    draw_cond = dedup.c.result == "1/2-1/2"
    loss_cond = or_(
        and_(dedup.c.result == "0-1", dedup.c.user_color == "white"),
        and_(dedup.c.result == "1-0", dedup.c.user_color == "black"),
    )

    stmt = select(
        func.count().label("total"),
        func.count().filter(win_cond).label("wins"),
        func.count().filter(draw_cond).label("draws"),
        func.count().filter(loss_cond).label("losses"),
    ).select_from(dedup)

    result = await session.execute(stmt)
    return result.one()


async def query_matching_games(
    session: AsyncSession,
    user_id: int,
    hash_column: Any | None,
    target_hash: int | None,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    offset: int,
    limit: int,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
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
        opponent_type=opponent_type,
        recency_cutoff=recency_cutoff,
        color=color,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    ).subquery()
    count_stmt = select(func.count()).select_from(count_subq)
    total: int = (await session.execute(count_stmt)).scalar_one()

    # Paginated game objects, ordered most-recent first.
    # When DISTINCT ON is used (position-filtered queries), PostgreSQL requires
    # the DISTINCT ON expression first in ORDER BY, preventing direct date sorting.
    # Wrap as subquery to deduplicate first, then sort by played_at in outer query.
    dedup_subq = _build_base_query(
        select_entity=Game,
        user_id=user_id,
        hash_column=hash_column,
        target_hash=target_hash,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency_cutoff=recency_cutoff,
        color=color,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
    if target_hash is not None:
        # DISTINCT ON needs id-first ordering for dedup; outer query re-sorts
        dedup_subq = dedup_subq.order_by(Game.id)
        dedup_cte = dedup_subq.cte("deduped_games")
        page_stmt = (
            select(Game)
            .join(dedup_cte, Game.id == dedup_cte.c.id)
            .order_by(Game.played_at.desc())
            .offset(offset)
            .limit(limit)
        )
    else:
        page_stmt = (
            dedup_subq
            .order_by(Game.played_at.desc())
            .offset(offset)
            .limit(limit)
        )
    result = await session.execute(page_stmt)
    games = list(result.scalars().all())

    return games, total


async def query_next_moves(
    session: AsyncSession,
    user_id: int,
    target_hash: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> list[Any]:
    """Aggregate next moves for a given position with per-move W/D/L stats.

    Uses a self-join on game_positions (gp1=source, gp2=next ply) to obtain
    both move_san and the resulting position's full_hash in a single query.
    COUNT(DISTINCT game_id) with CASE WHEN handles transposition dedup and
    W/D/L categorization simultaneously.

    Returns a list of rows with columns:
        (move_san, result_hash, game_count, wins, draws, losses)
    Rows with NULL move_san (final position) are excluded.
    """
    gp1 = aliased(GamePosition, name="gp1")
    gp2 = aliased(GamePosition, name="gp2")

    # CASE expressions: yield Game.id when condition is true, else NULL.
    # COUNT(DISTINCT ...) counts distinct non-NULL values.
    win_case = case(
        (
            ((Game.result == "1-0") & (Game.user_color == "white"))
            | ((Game.result == "0-1") & (Game.user_color == "black")),
            Game.id,
        ),
        else_=None,
    )
    draw_case = case(
        (Game.result == "1/2-1/2", Game.id),
        else_=None,
    )
    loss_case = case(
        (
            ((Game.result == "1-0") & (Game.user_color == "black"))
            | ((Game.result == "0-1") & (Game.user_color == "white")),
            Game.id,
        ),
        else_=None,
    )

    stmt = (
        select(
            gp1.move_san,
            gp2.full_hash.label("result_hash"),
            func.count(Game.id.distinct()).label("game_count"),
            func.count(win_case.distinct()).label("wins"),
            func.count(draw_case.distinct()).label("draws"),
            func.count(loss_case.distinct()).label("losses"),
        )
        .join(Game, Game.id == gp1.game_id)
        .join(gp2, (gp2.game_id == gp1.game_id) & (gp2.ply == gp1.ply + 1))
        .where(
            gp1.user_id == user_id,
            gp1.full_hash == target_hash,
            gp1.move_san.isnot(None),
        )
        .group_by(gp1.move_san, gp2.full_hash)
    )

    stmt = apply_game_filters(
        stmt, time_control, platform, rated, opponent_type, recency_cutoff, color,
        opponent_strength=opponent_strength, elo_threshold=elo_threshold,
    )

    rows = await session.execute(stmt)
    return list(rows.all())


async def query_transposition_counts(
    session: AsyncSession,
    user_id: int,
    result_hash_list: list[int],
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = DEFAULT_ELO_THRESHOLD,
) -> dict[int, int]:
    """Return the total distinct games reaching each result_hash under the same filters.

    For each full_hash in result_hash_list, counts distinct game_ids that have
    a game_positions row with that full_hash (via any move order / transposition).
    Respects all filter parameters for consistent filtering with query_next_moves.

    Returns: {result_hash: transposition_count}
    Missing hashes (no games reached them under filters) are omitted from dict.
    """
    if not result_hash_list:
        return {}

    stmt = (
        select(
            GamePosition.full_hash.label("result_hash"),
            func.count(GamePosition.game_id.distinct()).label("transposition_count"),
        )
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.full_hash.in_(result_hash_list),
        )
        .group_by(GamePosition.full_hash)
    )

    stmt = apply_game_filters(
        stmt, time_control, platform, rated, opponent_type, recency_cutoff, color,
        opponent_strength=opponent_strength, elo_threshold=elo_threshold,
    )

    rows = await session.execute(stmt)
    return {row.result_hash: row.transposition_count for row in rows}

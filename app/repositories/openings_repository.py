"""Openings repository: DB queries for position-based W/D/L lookups."""

import ctypes
import datetime
from collections.abc import Sequence
from typing import Any, Literal

import chess
import chess.polyglot
from sqlalchemy import Float, and_, case, cast, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.opening import Opening
from app.repositories.query_utils import apply_game_filters
from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_MAX_ENTRY_PLY,
    OPENING_INSIGHTS_MIN_ENTRY_PLY,
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
    OPENING_INSIGHTS_MINOR_EFFECT,
    OPENING_INSIGHTS_SCORE_PIVOT,
)

# Note: the SQL gate below uses OPENING_INSIGHTS_MINOR_EFFECT only; the
# major-vs-minor distinction is applied downstream in
# opening_insights_service._classify_row (which uses MAJOR_EFFECT).

# Maps match_side values to the corresponding GamePosition hash column.
HASH_COLUMN_MAP = {
    "white": GamePosition.white_hash,
    "black": GamePosition.black_hash,
    "full": GamePosition.full_hash,
}

# Phase 71 hotfix (#71): opening insights replays entry_san_sequence from
# chess.Board(); games imported with a non-standard starting FEN
# (e.g. chess.com themed events / puzzles whose PGN carries [SetUp "1"][FEN ...])
# store a SAN prefix that is unreachable from the initial position and would
# 500 the endpoint when min(array_agg(...)) lexicographically picks such a
# chain over a legal one. We filter those games out of the CTE by checking
# the ply-0 full_hash against the standard initial-position Zobrist hash.
# Signed int64 conversion mirrors GamePosition.full_hash storage (see
# opening_insights_service._compute_prefix_hashes line 129).
STARTING_POSITION_HASH: int = ctypes.c_int64(chess.polyglot.zobrist_hash(chess.Board())).value


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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
    if opponent_gap_min is not None or opponent_gap_max is not None:
        user_rating = case(
            (Game.user_color == "white", Game.white_rating),
            else_=Game.black_rating,
        )
        opp_rating = case(
            (Game.user_color == "white", Game.black_rating),
            else_=Game.white_rating,
        )
        base = base.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
        gap = opp_rating - user_rating
        if opponent_gap_min is not None:
            base = base.where(gap >= opponent_gap_min)
        if opponent_gap_max is not None:
            base = base.where(gap <= opponent_gap_max)

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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
    if opponent_gap_min is not None or opponent_gap_max is not None:
        user_rating = case(
            (Game.user_color == "white", Game.white_rating),
            else_=Game.black_rating,
        )
        opp_rating = case(
            (Game.user_color == "white", Game.black_rating),
            else_=Game.white_rating,
        )
        stmt = stmt.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
        gap = opp_rating - user_rating
        if opponent_gap_min is not None:
            stmt = stmt.where(gap >= opponent_gap_min)
        if opponent_gap_max is not None:
            stmt = stmt.where(gap <= opponent_gap_max)

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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
        page_stmt = dedup_subq.order_by(Game.played_at.desc()).offset(offset).limit(limit)
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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        color,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
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
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
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
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        color,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    rows = await session.execute(stmt)
    return {row.result_hash: row.transposition_count for row in rows}


async def query_opening_transitions(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> list[Row[Any]]:
    """Aggregate (entry_hash, candidate_san) transitions for one user & color.

    Single CTE with a LAG window function derives entry_hash from the prior
    ply within each game. The outer query joins to games, applies user
    filters, groups by (entry_hash, candidate_san), and HAVING-filters to
    n>=10 candidates whose chess score (W + 0.5·D)/N is at most 0.45
    (weaknesses) or at least 0.55 (strengths). Phase 75 D-08; replaces the
    Phase 70 win_rate/loss_rate gate.

    Returns one Row per surviving (entry_hash, move_san) pair with attrs:
        entry_hash: int        (BIGINT in PG, never NULL in output)
        move_san: str          (the candidate move SAN, never NULL)
        resulting_full_hash: int  (candidate position's full_hash, for D-21 dedupe)
        entry_san_sequence: list[str]  (SAN tokens from start up to entry position,
                                        candidate move excluded; for D-34 FEN replay)
        n: int                 (count of distinct games)
        w: int, d: int, l: int (filtered counts)

    Returns [] when the user has no qualifying transitions. Uses
    PostgreSQL ix_gp_user_game_ply for an index-only scan (Heap Fetches: 0).
    See CONTEXT.md D-30, D-31, D-32, D-33 and RESEARCH.md Pattern 2.
    """
    # Phase 71 hotfix (#71): the entry position IS the current row's position.
    # GamePosition.move_san at ply X is "the move played FROM ply X to ply X+1"
    # (see app/services/zobrist.py and the GamePosition.move_san model docstring).
    # That means at row ply X, current row's full_hash IS the entry hash, current
    # row's move_san IS the candidate move played from entry, and the resulting
    # position's hash is at ply X+1 (LEAD). The original Phase 70 query used LAG
    # for entry_hash (one ply too shallow) — internally consistent against the
    # synthetic test factories but mis-aligned against real game_positions data.
    # That bug surfaced as `chess.IllegalMoveError` during Phase 71 UAT because
    # entry_san_sequence then started one move late and replay failed.
    #
    # Phase 71 hotfix (this commit): include only games whose ply-0 position
    # IS the standard starting position. Games imported from chess.com themed
    # events / puzzles carry [SetUp "1"][FEN ...] PGN headers and store a SAN
    # prefix that is unreachable from chess.Board(); this would crash the
    # replay in opening_insights_service._compute_prefix_hashes when
    # min(array_agg(...)) lexicographically picks such a chain. Games missing
    # a ply-0 row entirely (data corruption — should not occur) are also
    # excluded by the EXISTS predicate.
    gp_root = aliased(GamePosition, name="gp_root")
    has_standard_start = (
        select(1)
        .where(
            gp_root.game_id == GamePosition.game_id,
            gp_root.user_id == GamePosition.user_id,
            gp_root.ply == 0,
            gp_root.full_hash == STARTING_POSITION_HASH,
        )
        .exists()
    )
    transitions_cte = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.ply.label("ply"),
            GamePosition.move_san.label("move_san"),  # candidate move played from entry
            GamePosition.full_hash.label(
                "entry_hash"
            ),  # entry position hash IS the current row's hash
            func.lead(GamePosition.full_hash)
            .over(
                partition_by=GamePosition.game_id,
                order_by=GamePosition.ply,
            )
            .label("resulting_full_hash"),  # position after the candidate move (LEAD by one ply)
            # Per BLOCKER-1 / D-25 / D-34: the SAN tokens needed to replay the
            # entry position from the start of the game. At an entry row at
            # ply X, entry_san_sequence must contain the X moves played at
            # plies 0..X-1 (move_san at ply Y is the move played FROM ply Y).
            #
            # The CTE WHERE clause includes ply 0 — without it, the move played
            # from the start position (always White's first move) is missing
            # from the partition and `_replay_san_sequence` fails with
            # chess.IllegalMoveError on every finding.
            #
            # ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING covers all moves
            # up to (but not including) the current row — i.e. plies 0..X-1.
            # rows=(None, -1) maps to that boundary in SQLAlchemy.
            #
            # FILTER (WHERE move_san IS NOT NULL) guards against NULL entries
            # from corrupted imports: board.push_san(None) raises TypeError
            # (not InvalidMoveError), which would propagate as a 500.
            func.array_agg(GamePosition.move_san)
            .filter(GamePosition.move_san.isnot(None))
            .over(
                partition_by=GamePosition.game_id,
                order_by=GamePosition.ply,
                rows=(None, -1),
            )
            .label("entry_san_sequence"),
        )
        .where(
            GamePosition.user_id == user_id,
            # Need ply 0 for the partition (so its move_san enters entry_san_sequence)
            # and ply MAX_ENTRY_PLY+1 so LEAD has a row to read for entries at MAX_ENTRY_PLY.
            GamePosition.ply.between(0, OPENING_INSIGHTS_MAX_ENTRY_PLY + 1),
            # Phase 71 hotfix: include only games whose ply-0 position is the
            # standard starting position (chess.com [SetUp "1"] PGN tags etc.
            # are excluded) — their SAN prefix is unreachable from chess.Board()
            # and would crash the replay in opening_insights_service.
            has_standard_start,
        )
        .cte("transitions")
    )

    # Win/Loss/Draw conditions copied from stats_repository.query_top_openings_sql_wdl:240-248.
    win_cond = or_(
        and_(Game.result == "1-0", Game.user_color == "white"),
        and_(Game.result == "0-1", Game.user_color == "black"),
    )
    draw_cond = Game.result == "1/2-1/2"
    loss_cond = or_(
        and_(Game.result == "0-1", Game.user_color == "white"),
        and_(Game.result == "1-0", Game.user_color == "black"),
    )

    n_games = func.count(func.distinct(Game.id))
    wins = func.count(func.distinct(Game.id)).filter(win_cond)
    draws = func.count(func.distinct(Game.id)).filter(draw_cond)
    losses = func.count(func.distinct(Game.id)).filter(loss_cond)

    # Phase 75 D-08: score-based effect-size gate. score = (W + 0.5·D) / N.
    # Minor-effect threshold (0.05) drives the SQL gate; major findings
    # (effect >= 0.10, OPENING_INSIGHTS_MAJOR_EFFECT) are a post-filter
    # assertion in Python (_classify_row). Symmetric on both sides → the OR
    # keeps the gate simple. n_games >= 10 (was 20 in Phase 70).
    score_expr = (cast(wins, Float) + 0.5 * cast(draws, Float)) / cast(n_games, Float)
    weakness_threshold = OPENING_INSIGHTS_SCORE_PIVOT - OPENING_INSIGHTS_MINOR_EFFECT  # 0.45
    strength_threshold = OPENING_INSIGHTS_SCORE_PIVOT + OPENING_INSIGHTS_MINOR_EFFECT  # 0.55

    stmt = (
        select(
            transitions_cte.c.entry_hash.label("entry_hash"),
            transitions_cte.c.move_san.label("move_san"),
            # BLOCKER-6: pass through the candidate's full_hash for dedupe (D-21).
            # All games with the same (entry_hash, move_san) lead to the same resulting
            # position, so min() is a safe deterministic aggregate.
            func.min(transitions_cte.c.resulting_full_hash).label("resulting_full_hash"),
            # BLOCKER-1 / D-34: pass through the entry SAN sequence so the service
            # can both reconstruct entry_fen via python-chess replay AND walk the
            # parent-hash lineage when direct attribution misses. Aggregated at
            # GROUP BY level via min() — identical sequences across game instances
            # of the same (entry_hash, move_san) all share the same prefix.
            func.min(transitions_cte.c.entry_san_sequence).label("entry_san_sequence"),
            n_games.label("n"),
            wins.label("w"),
            draws.label("d"),
            losses.label("l"),
        )
        .select_from(transitions_cte)
        .join(Game, Game.id == transitions_cte.c.game_id)
        .where(
            Game.user_id == user_id,
            Game.user_color == color,  # explicit per-color filter (RESEARCH.md anti-pattern note)
            transitions_cte.c.move_san.is_not(
                None
            ),  # drops final-position rows (no candidate to count)
            transitions_cte.c.resulting_full_hash.is_not(
                None
            ),  # drops final-position rows where LEAD is NULL
            transitions_cte.c.ply.between(
                OPENING_INSIGHTS_MIN_ENTRY_PLY,  # entry ply 0..16 (current row IS entry)
                OPENING_INSIGHTS_MAX_ENTRY_PLY,
            ),
        )
        .group_by(transitions_cte.c.entry_hash, transitions_cte.c.move_san)
        .having(
            and_(
                n_games >= OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
                or_(
                    score_expr <= weakness_threshold,
                    score_expr >= strength_threshold,
                ),
            )
        )
    )
    # Embed shared filter helpers AFTER the join so user_color overlap doesn't double-filter.
    # color=None passed to apply_game_filters because per-color is already explicit above.
    stmt = apply_game_filters(
        stmt,
        time_control,
        platform,
        rated,
        opponent_type,
        recency_cutoff,
        color=None,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    result = await session.execute(stmt)
    return list(result.all())


async def query_openings_by_hashes(
    session: AsyncSession,
    full_hashes: list[int],
) -> dict[int, Opening]:
    """Return {full_hash: deepest matching Opening} for each input hash.

    "Deepest" = MAX(ply_count) among rows whose Opening.full_hash matches.
    Hashes with no match are absent from the result dict (the service
    falls back to lineage walk per D-23).

    See CONTEXT.md D-22, RESEARCH.md Pitfall 6 (NULL full_hash filter).
    """
    if not full_hashes:
        return {}
    stmt = select(Opening).where(
        Opening.full_hash.is_not(None),
        Opening.full_hash.in_(full_hashes),
    )
    rows = await session.execute(stmt)
    by_hash: dict[int, Opening] = {}
    for opening in rows.scalars():
        if opening.full_hash is None:
            continue  # should be unreachable given SQL IS NOT NULL filter; guard for ty narrowing
        existing = by_hash.get(opening.full_hash)
        if existing is None or opening.ply_count > existing.ply_count:
            by_hash[opening.full_hash] = opening
    return by_hash

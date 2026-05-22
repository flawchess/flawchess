"""Stats repository: DB queries for rating history and global game stats."""

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
    and_,
    case,
    cast,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.query_utils import apply_game_filters

# D-08: trim |eval_cp| >= 2000 (>= ±20 pawns) from eval mean. Decisive positions
# are statistically uninformative for "typical opening character".
EVAL_OUTLIER_TRIM_CP: int = 2000


@dataclass(slots=True)
class OpeningPhaseEntryMetrics:
    """Accumulated phase-entry metrics per opening (full_hash key) for
    middlegame entry (phase=1).

    Per-phase partition invariant: for every opening with at least one
    phase-entry row, ``eval_n + mate_n + null_eval_n + outlier_n`` equals the
    phase-entry-row count. The four buckets are mutually exclusive at the
    phase-entry row:

    - ``eval_n``      — eval_cp NOT NULL AND eval_mate IS NULL AND |eval_cp| < 2000 (continuous, in-domain)
    - ``mate_n``      — eval_mate IS NOT NULL (forced-mate; excluded from mean)
    - ``null_eval_n`` — eval_cp IS NULL AND eval_mate IS NULL (no score available)
    - ``outlier_n``   — eval_cp NOT NULL AND eval_mate IS NULL AND |eval_cp| >= 2000 (D-08 trim)

    Note: trimmed rows are NOT counted as null_eval; they are explicitly
    classified as outlier_n so the partition invariant remains testable.
    """

    # MG-entry pillar (D-01, D-04, D-08)
    eval_sum_mg: float  # signed user-perspective sum, in centipawns
    eval_sumsq_mg: float  # sum of squared signed eval_cp values
    eval_n_mg: int  # phase=1 rows with continuous in-domain eval
    mate_n_mg: int  # phase=1 rows with eval_mate IS NOT NULL
    null_eval_n_mg: int  # phase=1 rows with both eval_cp and eval_mate NULL
    outlier_n_mg: int  # phase=1 rows with |eval_cp| >= 2000 (D-08)


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
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    *,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> list[Row[Any]]:
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
            user_rating_expr.is_not(None),
            Game.played_at.is_not(None),
        )
        # DISTINCT ON requires ORDER BY to start with the same columns;
        # played_at DESC picks the last game of each day per time control.
        .order_by(date_col, Game.time_control_bucket, Game.played_at.desc())
    )

    # Use shared filter helper per CLAUDE.md "Shared Query Filters".
    # platform is wrapped in a single-element list because apply_game_filters
    # expects Sequence[str] | None for the platform arg.
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=[platform],
        rated=None,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_results_by_time_control(
    session: AsyncSession,
    user_id: int,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    platform: str | None = None,
    *,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> list[Row[Any]]:
    """Return (time_control_bucket, total, wins, draws, losses) via SQL aggregation.

    Excludes games where time_control_bucket is NULL.
    Optionally filtered by platform, from_date/to_date, opponent_type, and opponent gap.
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

    # Use shared filter helper per CLAUDE.md "Shared Query Filters".
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=[platform] if platform is not None else None,
        rated=None,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_results_by_color(
    session: AsyncSession,
    user_id: int,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    platform: str | None = None,
    *,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> list[Row[Any]]:
    """Return (user_color, total, wins, draws, losses) via SQL aggregation.

    Excludes games where user_color is NULL.
    Optionally filtered by platform, from_date/to_date, opponent_type, and opponent gap.
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

    # Use shared filter helper per CLAUDE.md "Shared Query Filters".
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=[platform] if platform is not None else None,
        rated=None,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )

    result = await session.execute(stmt)
    return list(result.fetchall())


async def query_top_openings_sql_wdl(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    min_games: int,
    limit: int,
    min_ply: int,
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    time_control: Sequence[str] | None = None,
    platform: Sequence[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> list[Row[Any]]:
    """Return top openings with SQL-side WDL aggregation, ranked by position count.

    Counts distinct games passing through each named opening's position
    (`game_positions.full_hash`), not games tagged with that opening name. This
    matches the count displayed in the UI (which is also position-based — see
    `query_position_wdl_batch` in the service layer) so ranking and display
    agree. Without this, the deepest-name-tag aggregation pre-PRE-01 happened
    to look right only because the parity filter coincidentally hid most deep
    sub-variation rows.

    Returns (eco, name, display_name, pgn, fen, full_hash, total, wins, draws, losses)
    tuples. `display_name` equals `name` when the opening's defining ply parity
    matches `color`, else `f"vs. {name}"`. WDL is COUNT(DISTINCT game_id) FILTER
    per condition — game-level columns are stable across a game's
    `game_positions` rows so DISTINCT collapses correctly.
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

    # 2026-04-26 (PRE-01): off-color rows are surfaced with `vs. ` prefix so
    # labels read naturally without dropping coverage. White openings end on
    # odd ply (white's last move), black on even ply.
    user_parity = 1 if color == "white" else 0
    display_name_col = case(
        (
            _openings_dedup.c.ply_count % 2 != user_parity,
            literal("vs. ") + _openings_dedup.c.name,
        ),
        else_=_openings_dedup.c.name,
    ).label("display_name")

    distinct_game_count = func.count(func.distinct(Game.id))

    stmt = (
        select(
            _openings_dedup.c.eco,
            _openings_dedup.c.name,
            display_name_col,
            _openings_dedup.c.pgn,
            _openings_dedup.c.fen,
            _openings_dedup.c.full_hash,
            distinct_game_count.label("total"),
            distinct_game_count.filter(win_cond).label("wins"),
            distinct_game_count.filter(draw_cond).label("draws"),
            distinct_game_count.filter(loss_cond).label("losses"),
        )
        .select_from(_openings_dedup)
        .join(
            GamePosition,
            and_(
                GamePosition.full_hash == _openings_dedup.c.full_hash,
                # Match the (user_id, full_hash) index — keeps the JOIN cheap.
                GamePosition.user_id == user_id,
            ),
        )
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            Game.user_id == user_id,
            Game.user_color == color,
            _openings_dedup.c.ply_count >= min_ply,
        )
        .group_by(
            _openings_dedup.c.eco,
            _openings_dedup.c.name,
            _openings_dedup.c.ply_count,
            _openings_dedup.c.pgn,
            _openings_dedup.c.fen,
            _openings_dedup.c.full_hash,
        )
        .having(distinct_game_count >= min_games)
        .order_by(distinct_game_count.desc())
        .limit(limit)
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
    return list(result.fetchall())


class PositionWDL:
    """Position-based WDL stats for a single hash."""

    __slots__ = ("total", "wins", "draws", "losses", "last_played_at")

    def __init__(
        self,
        total: int,
        wins: int,
        draws: int,
        losses: int,
        last_played_at: datetime.datetime | None = None,
    ):
        self.total = total
        self.wins = wins
        self.draws = draws
        self.losses = losses
        # MAX(games.played_at) for the games contributing to this (full_hash)
        # bucket; surfaces "Last played: <relative>" in the OpeningStatsCard
        # score-confidence popover. None when no contributing game has a
        # populated played_at (rare; column is nullable on Game).
        self.last_played_at = last_played_at


async def query_position_wdl_batch(
    session: AsyncSession,
    user_id: int,
    hashes: list[int],
    color: Literal["white", "black"] | None = None,
    time_control: Sequence[str] | None = None,
    platform: Sequence[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
) -> dict[int, PositionWDL]:
    """Return {full_hash: PositionWDL} for games passing through each position.

    Flat single-SELECT aggregation: COUNT(DISTINCT game_id) FILTER (...) handles
    transposition dedup (a game's same hash at multiple plies counts once) at
    aggregate level, so no dedup subquery is needed. Mirrors PR #90's
    query_opening_transitions shape, which proved consistently more
    plan-stable on PG 18 than wrapping a DISTINCT subquery.

    WDL conditions match query_top_openings_sql_wdl. ``total`` is computed
    in Python as ``wins + draws + losses`` (every game has exactly one result,
    so this equals COUNT(DISTINCT game_id) without a fourth aggregate).
    """
    if not hashes:
        return {}

    win_cond = or_(
        and_(Game.result == "1-0", Game.user_color == "white"),
        and_(Game.result == "0-1", Game.user_color == "black"),
    )
    draw_cond = Game.result == "1/2-1/2"
    loss_cond = or_(
        and_(Game.result == "0-1", Game.user_color == "white"),
        and_(Game.result == "1-0", Game.user_color == "black"),
    )

    distinct_game_count = func.count(func.distinct(Game.id))

    stmt = (
        select(
            GamePosition.full_hash,
            distinct_game_count.filter(win_cond).label("wins"),
            distinct_game_count.filter(draw_cond).label("draws"),
            distinct_game_count.filter(loss_cond).label("losses"),
            func.max(Game.played_at).label("last_played_at"),
        )
        .join(Game, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.full_hash.in_(hashes),
        )
        .group_by(GamePosition.full_hash)
    )

    if color is not None:
        stmt = stmt.where(Game.user_color == color)

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
    return {
        row[0]: PositionWDL(
            total=row[1] + row[2] + row[3],
            wins=row[1],
            draws=row[2],
            losses=row[3],
            last_played_at=row[4],
        )
        for row in result.fetchall()
    }


async def query_opening_phase_entry_metrics_batch(
    session: AsyncSession,
    user_id: int,
    hashes: list[int],
    color: Literal["white", "black"] | None = None,
    time_control: Sequence[str] | None = None,
    platform: Sequence[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    hash_column: Literal["full", "white", "black"] = "full",
) -> dict[int, OpeningPhaseEntryMetrics]:
    """Return {full_hash: OpeningPhaseEntryMetrics} for games passing through each position.

    Aggregates middlegame-entry (phase=1) eval metrics in a single SQL pass. The
    phase-entry row per game is identified via DISTINCT ON
    ``(game_id, phase ORDER BY ply)`` filtered to phase=1.

    Outlier trim: |eval_cp| >= EVAL_OUTLIER_TRIM_CP rows are excluded from the eval mean
    and counted separately as outlier_n (D-08). Mate rows (eval_mate IS NOT NULL) are
    excluded and counted as mate_n. This preserves the per-phase partition invariant:
    eval_n + mate_n + null_eval_n + outlier_n == phase_entry_row_count.

    Sign convention: eval_cp is signed at SQL level via ``case(user_color='white', 1, else=-1) * eval_cp``
    matching the endgame_service._classify_endgame_bucket convention.

    Performance note: uses GROUP BY + JOIN shape (not IN(subquery)) — the IN(subquery) form
    caused planner Nested Loop hangs on heavy users (see endgame_repository.py:687-692 for
    the original bug report and fix rationale). Run EXPLAIN ANALYZE on heavy users pre-merge.

    Uses apply_game_filters() from query_utils — same filter set as query_position_wdl_batch
    (CLAUDE.md "Shared Query Filters"). AsyncSession is not safe for concurrent use — callers
    must await this sequentially, not concurrently.
    """
    if not hashes:
        return {}

    # Resolve the hash column. Bookmark callers may filter by white_hash or
    # black_hash (match_side="mine"/"opponent"); most-played callers use full_hash.
    hash_col_map = {
        "full": GamePosition.full_hash,
        "white": GamePosition.white_hash,
        "black": GamePosition.black_hash,
    }
    hash_col = hash_col_map[hash_column]

    # Step 1: Dedup (hash, game_id) for the opening filter, materialized as a CTE so
    # Postgres only evaluates the user_id+hash scan once even though we reference it
    # from the phase_entry derivation below. DO NOT replace with .subquery() — when
    # referenced twice, a plain subquery is rendered as two independent inline derived
    # tables and PG does not CSE them, doubling the heavy DISTINCT-ON scan. PG 12+'s
    # CTE-inlining rules auto-materialize CTEs with >1 reference, which is exactly
    # what we want here. Measured on prod (25-hash batch, PR #93 verification):
    #   user 45 (39k games):  CTE 1298ms  vs  subquery 1527ms  (+18%, ~2x buffers)
    #   user 13 (22k games):  CTE  963ms  vs  subquery 1166ms  (+21%)
    #   user 43 ( 229 games): CTE   28ms  vs  subquery   41ms  (+45%, high variance)
    dedup_select = (
        select(
            hash_col.label("full_hash"),
            Game.id.label("game_id"),
            Game.user_color.label("user_color"),
        )
        .join(Game, GamePosition.game_id == Game.id)
        .where(
            GamePosition.user_id == user_id,
            hash_col.in_(hashes),
        )
        .distinct(hash_col, Game.id)
    )
    if color is not None:
        dedup_select = dedup_select.where(Game.user_color == color)
    dedup_select = apply_game_filters(
        dedup_select,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    dedup_subq = dedup_select.cte("dedup")

    # Step 2: Per-game phase-entry ROW (not just ply) via DISTINCT ON.
    # Inlines eval_cp / eval_mate into the phase_entry subquery so the heavy
    # gp_entry JOIN is eliminated entirely (was a Bitmap Heap Scan over
    # (game_id, ply) without a composite index — ~100k row scans for a heavy user).
    # Restricted to dedup's game_id set so the scan is ~10x smaller than the full
    # user partition.
    phase_entry_subq = (
        select(
            GamePosition.game_id.label("game_id"),
            GamePosition.eval_cp.label("eval_cp"),
            GamePosition.eval_mate.label("eval_mate"),
        )
        .where(
            GamePosition.phase == 1,
            GamePosition.game_id.in_(select(dedup_subq.c.game_id)),
        )
        .distinct(GamePosition.game_id)
        .order_by(GamePosition.game_id, GamePosition.ply)
    ).subquery("phase_entry")

    # Sign expression mirrors endgame_service._classify_endgame_bucket convention.
    sign_expr = case((dedup_subq.c.user_color == "white", 1), else_=-1)
    user_eval_expr = sign_expr * phase_entry_subq.c.eval_cp  # signed cp; NULL when eval_cp NULL

    # Eval-state predicates. Trim threshold = EVAL_OUTLIER_TRIM_CP (D-08).
    has_continuous_in_domain_eval = and_(
        phase_entry_subq.c.eval_cp.isnot(None),
        phase_entry_subq.c.eval_mate.is_(None),
        func.abs(phase_entry_subq.c.eval_cp) < EVAL_OUTLIER_TRIM_CP,
    )
    has_mate = phase_entry_subq.c.eval_mate.isnot(None)
    has_null_eval = and_(
        phase_entry_subq.c.eval_cp.is_(None),
        phase_entry_subq.c.eval_mate.is_(None),
    )
    has_outlier_eval = and_(
        phase_entry_subq.c.eval_cp.isnot(None),
        phase_entry_subq.c.eval_mate.is_(None),
        func.abs(phase_entry_subq.c.eval_cp) >= EVAL_OUTLIER_TRIM_CP,
    )

    agg_select = (
        select(
            dedup_subq.c.full_hash,
            # --- MG-entry aggregations (phase=1, filtered upstream) ---
            func.coalesce(
                func.sum(user_eval_expr).filter(has_continuous_in_domain_eval),
                0.0,
            ).label("eval_sum_mg"),
            func.coalesce(
                func.sum(user_eval_expr * user_eval_expr).filter(has_continuous_in_domain_eval),
                0.0,
            ).label("eval_sumsq_mg"),
            func.count().filter(has_continuous_in_domain_eval).label("eval_n_mg"),
            func.count().filter(has_mate).label("mate_n_mg"),
            func.count().filter(has_null_eval).label("null_eval_n_mg"),
            func.count().filter(has_outlier_eval).label("outlier_n_mg"),
        )
        .select_from(dedup_subq)
        .join(phase_entry_subq, phase_entry_subq.c.game_id == dedup_subq.c.game_id)
        .group_by(dedup_subq.c.full_hash)
    )

    result = await session.execute(agg_select)
    return {
        row[0]: OpeningPhaseEntryMetrics(
            eval_sum_mg=float(row[1]),
            eval_sumsq_mg=float(row[2]),
            eval_n_mg=int(row[3]),
            mate_n_mg=int(row[4]),
            null_eval_n_mg=int(row[5]),
            outlier_n_mg=int(row[6]),
        )
        for row in result.fetchall()
    }

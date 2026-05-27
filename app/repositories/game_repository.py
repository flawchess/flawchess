"""Game repository: bulk insert with ON CONFLICT DO NOTHING and position insertion."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition

# Explicit column list for asyncpg copy_records_to_table. Must be set-equal to
# {c.name for c in GamePosition.__table__.columns if c.name != "id"} — enforced
# by test_bulk_insert_positions_column_coverage. The ordering here is the
# functional contract: each row tuple is built by iterating over this tuple, so
# if a future column is added to GamePosition without updating this constant the
# CI test will fail and surfaced as a column-drift error before any data is written.
_POSITION_COPY_COLUMNS: tuple[str, ...] = (
    "game_id",
    "user_id",
    "ply",
    "full_hash",
    "white_hash",
    "black_hash",
    "move_san",
    "clock_seconds",
    "material_count",
    "material_signature",
    "material_imbalance",
    "has_opposite_color_bishops",
    "piece_count",
    "backrank_sparse",
    "mixedness",
    "phase",
    "eval_cp",
    "eval_mate",
    "endgame_class",
)


async def bulk_insert_games(session: AsyncSession, game_rows: list[dict]) -> list[int]:
    """Insert games, skipping duplicates. Returns list of newly inserted game IDs.

    Uses ON CONFLICT DO NOTHING on the unique constraint (user_id, platform, platform_game_id).
    Only returns IDs for rows that were actually inserted (not skipped).

    Args:
        session: AsyncSession to use for the insert.
        game_rows: List of dicts matching Game model columns.

    Returns:
        List of integer IDs for newly inserted games. Empty list if all are duplicates.
    """
    if not game_rows:
        return []

    stmt = (
        pg_insert(Game)
        .values(game_rows)
        .on_conflict_do_nothing(constraint="uq_games_user_platform_game_id")
        .returning(Game.id)
    )
    result = await session.execute(stmt)
    await session.flush()
    return [row[0] for row in result.fetchall()]


async def count_games_for_user(session: AsyncSession, user_id: int) -> int:
    """Return total number of games imported by the given user."""
    result = await session.execute(
        select(func.count()).select_from(Game).where(Game.user_id == user_id)
    )
    return result.scalar_one()


async def count_pending_evals(session: AsyncSession, user_id: int) -> int:
    """Return count of games not yet Stockfish-evaluated for the given user."""
    result = await session.execute(
        select(func.count())
        .select_from(Game)
        .where(Game.user_id == user_id, Game.evals_completed_at.is_(None))
    )
    return result.scalar_one()


async def users_with_zero_pending(
    session: AsyncSession,
    user_ids: Sequence[int],
) -> list[int]:
    """Return the subset of ``user_ids`` where:

    1. Pending-eval count is zero (no games with evals_completed_at IS NULL), AND
    2. No active (pending or in_progress) import_jobs row exists for the user.

    Both conditions must hold to fire Stage B (Plan 13 gap-closure). Without
    condition 2, Stage B fires multiple times during an active import as eval
    batches drain and the per-user pending-eval count flickers between zero and
    non-zero. Each re-fire produces a different intermediate value because the
    canonical-slice CTE input set has grown. User 28's achievable_score_gap was
    observed to flip between -0.0511 and +0.1204 in a 20-second window due to
    this re-fire pattern (documented in 94.1-13-PLAN.md gap_source).

    Issued as ONE aggregated SQL statement (WR-01 contract preserved). Construction:
    an inline VALUES table over ``user_ids``, WHERE NOT EXISTS (active import),
    LEFT JOIN'd to ``games`` on (uid = games.user_id AND
    games.evals_completed_at IS NULL), GROUP BY uid, HAVING count(games.id) = 0.

    Args:
        session: AsyncSession (read-only is fine).
        user_ids: Sequence of internal user PKs to check. Empty input
            short-circuits to ``[]`` without issuing any SQL (avoids a
            Postgres ``VALUES ()`` syntax error and an unnecessary round-trip).

    Returns:
        List of user_ids (subset of input) where both (eval drain done) AND
        (no active import) conditions hold. Order is unspecified.
        Empty list if no input users satisfy both conditions.
    """
    if not user_ids:
        return []

    from app.models.import_job import ImportJob

    uid_col = sa.column("uid", sa.Integer)
    uids_vt = sa.values(uid_col, name="input_uids").data([(int(u),) for u in user_ids])

    # Plan 13 Stage B gate: exclude users with an active (pending/in_progress) import.
    # Without this gate, Stage B fires during transient eval-drain states mid-import,
    # producing partial intermediate values visible on the chip (94.1-13-PLAN.md).
    active_import_exists = sa.exists(
        sa.select(sa.literal(1)).where(
            sa.and_(
                ImportJob.user_id == uid_col,
                ImportJob.status.in_(["pending", "in_progress"]),
            )
        )
    )

    # Inline values-table over the input user_ids. LEFT JOIN preserves users
    # who have no games at all (count(games.id) IS NULL → 0 via the outer agg).
    stmt = (
        sa.select(uid_col)
        .select_from(
            uids_vt.outerjoin(
                Game,
                sa.and_(
                    Game.user_id == uid_col,
                    Game.evals_completed_at.is_(None),
                ),
            )
        )
        .where(sa.not_(active_import_exists))
        .group_by(uid_col)
        .having(sa.func.count(Game.id) == 0)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_all_games_for_user(session: AsyncSession, user_id: int) -> int:
    """Delete all games and positions for the given user.

    Deletes game_positions first (child rows), then games. Returns the count of deleted games.

    Args:
        session: AsyncSession to use for the deletes.
        user_id: The user whose data should be deleted.

    Returns:
        Number of games deleted.
    """
    await session.execute(delete(GamePosition).where(GamePosition.user_id == user_id))
    result = await session.execute(delete(Game).where(Game.user_id == user_id).returning(Game.id))
    return len(result.fetchall())


async def count_games_by_platform(session: AsyncSession, user_id: int) -> dict[str, int]:
    """Return game counts grouped by platform for the given user."""
    result = await session.execute(
        select(Game.platform, func.count())
        .select_from(Game)
        .where(Game.user_id == user_id)
        .group_by(Game.platform)
    )
    return {row[0]: row[1] for row in result.all()}


async def bulk_insert_positions(session: AsyncSession, position_rows: list[dict]) -> None:
    """Bulk insert GamePosition rows via asyncpg's binary COPY protocol.

    Should only be called for game IDs returned by bulk_insert_games (new games only).
    No conflict handling — positions are only inserted for newly inserted games.

    Uses asyncpg's copy_records_to_table, which streams rows as a binary blob
    and runs with roughly constant per-backend Postgres parser/executor memory
    regardless of row count — unlike INSERT ... VALUES which materialises up to
    rows × columns bound parameters in Postgres memory.

    The COPY runs on the asyncpg Connection underlying the SQLAlchemy AsyncSession,
    so it participates in the session's active transaction. A session-level rollback
    after a successful COPY will undo the inserted rows.

    Chunking at chunk_size=1700 is retained to bound peak Python-side list memory
    and to give asyncio a yield point between chunks. The 32k-bound-parameter
    ceiling of INSERT ... VALUES does not apply to COPY.

    Args:
        session: AsyncSession to use for the insert.
        position_rows: List of dicts with keys matching _POSITION_COPY_COLUMNS.
                       Missing optional keys default to None.
    """
    if not position_rows:
        return

    sa_conn = await session.connection()
    raw_wrapper = await sa_conn.get_raw_connection()
    # driver_connection is the asyncpg.Connection inside SQLAlchemy's async wrapper.
    # It is always set after get_raw_connection() when using the asyncpg dialect.
    raw_conn = raw_wrapper.driver_connection
    assert raw_conn is not None, "asyncpg driver_connection must not be None"

    chunk_size = 1700
    for i in range(0, len(position_rows), chunk_size):
        chunk = position_rows[i : i + chunk_size]
        records = [tuple(row.get(col) for col in _POSITION_COPY_COLUMNS) for row in chunk]
        await raw_conn.copy_records_to_table(
            "game_positions",
            records=records,
            columns=_POSITION_COPY_COLUMNS,
        )
    await session.flush()

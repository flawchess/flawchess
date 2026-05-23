"""Game repository: bulk insert with ON CONFLICT DO NOTHING and position insertion."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition


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
    """Return the subset of ``user_ids`` whose pending-eval count is zero.

    Issued as ONE aggregated SQL statement (WR-01 fix, Phase 94.1-12). Replaces
    the per-user ``count_pending_evals`` loop in ``eval_drain.py`` post-commit
    Stage B fan-out. Construction: an inline VALUES table over ``user_ids``
    LEFT JOIN'd to ``games`` on (uid = games.user_id AND
    games.evals_completed_at IS NULL), GROUP BY uid, HAVING count(games.id) = 0.
    The LEFT JOIN guarantees users with zero rows in ``games`` at all are still
    returned (the outer count over a NULL games.id evaluates to 0).

    Args:
        session: AsyncSession (read-only is fine).
        user_ids: Sequence of internal user PKs to check. Empty input
            short-circuits to ``[]`` without issuing any SQL (avoids a
            Postgres ``VALUES ()`` syntax error and an unnecessary round-trip).

    Returns:
        List of user_ids (subset of input) where the count of games with
        ``evals_completed_at IS NULL`` is zero. Order is unspecified.
        Empty list if no input users have zero pending evals.
    """
    if not user_ids:
        return []

    # Inline values-table over the input user_ids. LEFT JOIN preserves users
    # who have no games at all (count(games.id) IS NULL → 0 via the outer agg).
    uid_col = sa.column("uid", sa.Integer)
    uids_vt = sa.values(uid_col, name="input_uids").data([(int(u),) for u in user_ids])
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
    """Bulk insert GamePosition rows for the given game.

    Should only be called for game IDs returned by bulk_insert_games (new games only).
    No conflict handling — positions are only inserted for newly inserted games.

    Args:
        session: AsyncSession to use for the insert.
        position_rows: List of dicts with keys: game_id, user_id, ply,
                       full_hash, white_hash, black_hash, move_san, clock_seconds,
                       and optionally: material_count, material_signature,
                       material_imbalance, has_opposite_color_bishops,
                       eval_cp, eval_mate, endgame_class, piece_count.
    """
    if not position_rows:
        return

    # PostgreSQL asyncpg limits query arguments to 32,767.
    # Each position row has 19 columns (8 original + 5 position metadata + 2 phase detection + 2 eval + 1 endgame_class + 1 piece_count),
    # so max rows per chunk = 32767 / 19 = 1724.
    # Use 1700 for safety margin.
    chunk_size = 1700
    for i in range(0, len(position_rows), chunk_size):
        chunk = position_rows[i : i + chunk_size]
        stmt = insert(GamePosition).values(chunk)
        await session.execute(stmt)
    await session.flush()

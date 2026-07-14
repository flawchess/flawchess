"""Game repository: bulk insert with ON CONFLICT DO NOTHING and position insertion."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import delete, func, select, update
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
# IN-01 fix: promote the chunk size to a module-level constant so the test file
# can import it instead of duplicating the literal (`_CHUNK_SIZE = 1700` in
# tests/test_game_repository_bulk_insert_positions.py). Keeps the chunking
# boundary test honest if this value is ever tuned.
_POSITION_CHUNK_SIZE: int = 1700

POSITION_COPY_COLUMNS: tuple[str, ...] = (
    "game_id",
    "user_id",
    "ply",
    "full_hash",
    "white_hash",
    "black_hash",
    "move_san",
    "clock_seconds",
    "phase",
    "eval_cp",
    "eval_mate",
    "best_move",
    "pv",
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


async def get_game_id_by_platform_game_id(
    session: AsyncSession,
    user_id: int,
    platform: str,
    platform_game_id: str,
) -> int | None:
    """Return the game id for (user_id, platform, platform_game_id), or None.

    Phase 167 (STORE-01/05): `_flush_batch` (bulk_insert_games's ON CONFLICT DO
    NOTHING path) returns only a *count* of newly inserted games, never an id —
    on EITHER the newly-inserted or the idempotent-duplicate path. This single
    lookup serves both: the caller always does one follow-up SELECT keyed on
    the uq_games_user_platform_game_id columns to get the id for the response
    and for the bot_game_settings insert (RESEARCH Pitfall 2).

    Args:
        session: AsyncSession to use.
        user_id: Internal user PK (scopes the lookup — never cross-user).
        platform: Platform string (e.g. "flawchess").
        platform_game_id: The platform-scoped game id (client UUID for bot games).

    Returns:
        The game's internal id, or None if no matching row exists.
    """
    result = await session.execute(
        select(Game.id).where(
            Game.user_id == user_id,
            Game.platform == platform,
            Game.platform_game_id == platform_game_id,
        )
    )
    return result.scalar_one_or_none()


async def update_game_pgn(session: AsyncSession, game_id: int, pgn: str) -> None:
    """Overwrite a single game row's stored `pgn` (quick-260714-qaj / D-07).

    The `Site` header of a stored bot game's PGN needs the row's own
    auto-increment `games.id`, which does not exist at `normalize_flawchess_
    game` time — so the header block is stamped in a second, targeted UPDATE
    after the INSERT. Does NOT commit — the caller owns the transaction
    (D-10).

    Args:
        session: AsyncSession to use.
        game_id: The row's internal id (already scoped to the caller's user
            by the preceding lookup).
        pgn: The fully re-serialized PGN string to write.
    """
    await session.execute(update(Game).where(Game.id == game_id).values(pgn=pgn))


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


async def count_fully_analyzed_games(session: AsyncSession, user_id: int) -> int:
    """Return count of games FlawChess has fully analyzed (full_evals_completed_at SET).

    Badge numerator for GET /imports/eval-coverage. This is the SAME definition the
    per-game Library cards use for `analysis_state` ("analyzed" → no "Analyze"
    button): ``full_evals_completed_at IS NOT NULL`` (see
    library_repository._analyzed_game_ids_subquery). Keeping the badge and the cards
    on one column is the point — otherwise they disagree.

    Why NOT Game.is_analyzed (white_blunders IS NOT NULL): a lichess game imported
    with an embedded `analysis` block gets white_blunders populated at import time
    (normalization.py), so it satisfies is_analyzed instantly — before FlawChess's
    own full-eval drain has touched it. The card still (correctly) shows "Analyze",
    but the old is_analyzed-based badge counted it as analyzed, so the badge read
    "X of X" while unanalyzed cards were plainly visible (the bug this fixes).

    X-of-X reachability is preserved: a permanently-degenerate game (too short /
    coverage-capped) still gets full_evals_completed_at stamped by the drain, so it
    counts here as analyzed — matching its card, which shows no "Analyze" button.
    """
    result = await session.execute(
        select(func.count())
        .select_from(Game)
        .where(Game.user_id == user_id, Game.full_evals_completed_at.isnot(None))
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


async def get_current_rating_by_platform(
    session: AsyncSession, user_id: int
) -> dict[str, int | None]:
    """Return each platform's rating from the user's most-recent game on that platform.

    MAIA-04 / D-07: feeds the free-play ELO-selector default so engaged users see
    a rating-based starting point instead of the flat 1500 fallback. Read-only,
    no migration, no write (see 151-03-PLAN.md threat T-151-06: ORDER BY
    played_at DESC rides ix_games_user_played_at, bounded to the user's own rows).

    Single query keyed on user_id, ordered by played_at DESC (index-backed on
    ix_games_user_played_at) — reduced to one row per platform in Python by
    keeping the FIRST (= most recent) row seen for each platform, instead of
    issuing one query per platform.

    The returned dict is insertion-ordered by recency: the first key inserted is
    the platform of the user's single most-recent game across ALL platforms
    (because that row is necessarily the first one scanned in DESC order, and
    also the first occurrence of its own platform). Callers wanting one scalar
    "current" rating — rather than a per-platform breakdown — should take
    `next(iter(ratings.values()), None)`; see routers/users.py.

    Args:
        session: AsyncSession to use.
        user_id: Internal user ID.

    Returns:
        Dict keyed by platform ("chess.com" / "lichess"), mapping to the rating
        (white_rating or black_rating, whichever matches the user's color on
        that game) of the most recent game on that platform. A platform maps to
        None if its most recent game has no rating for the user's color (e.g.
        an unrated game). Platforms the user has never played on are absent.
        Empty dict if the user has no games at all.
    """
    result = await session.execute(
        select(Game.platform, Game.user_color, Game.white_rating, Game.black_rating)
        .where(Game.user_id == user_id)
        .order_by(Game.played_at.desc())
    )
    ratings: dict[str, int | None] = {}
    for platform, user_color, white_rating, black_rating in result.all():
        if platform in ratings:
            continue
        ratings[platform] = white_rating if user_color == "white" else black_rating
    return ratings


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

    Chunking at _POSITION_CHUNK_SIZE (1700) is retained to bound peak Python-side list memory
    and to give asyncio a yield point between chunks. The 32k-bound-parameter
    ceiling of INSERT ... VALUES does not apply to COPY.

    Args:
        session: AsyncSession to use for the insert.
        position_rows: List of dicts with keys matching POSITION_COPY_COLUMNS.
                       Missing optional keys default to None.
    """
    if not position_rows:
        return

    sa_conn = await session.connection()
    raw_wrapper = await sa_conn.get_raw_connection()
    # driver_connection is the asyncpg.Connection inside SQLAlchemy's async wrapper.
    # It is always set after get_raw_connection() when using the asyncpg dialect.
    raw_conn = raw_wrapper.driver_connection
    # IN-03 fix: explicit runtime check (not `assert`) so the guard survives
    # `python -O` / `PYTHONOPTIMIZE=1`, which strips asserts. Under -O the
    # original `assert` would silently call `.copy_records_to_table` on None
    # and raise an unhelpful AttributeError. This branch should be unreachable
    # in practice (SQLAlchemy's asyncpg adapter always sets driver_connection
    # after get_raw_connection()), but if the adapter ever changes we get a
    # specific, debuggable error instead.
    if raw_conn is None:
        raise RuntimeError("asyncpg driver_connection is None — SQLAlchemy adapter changed")

    for i in range(0, len(position_rows), _POSITION_CHUNK_SIZE):
        chunk = position_rows[i : i + _POSITION_CHUNK_SIZE]
        records = [tuple(row.get(col) for col in POSITION_COPY_COLUMNS) for row in chunk]
        await raw_conn.copy_records_to_table(
            "game_positions",
            records=records,
            columns=POSITION_COPY_COLUMNS,
        )
    await session.flush()

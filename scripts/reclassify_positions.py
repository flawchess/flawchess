"""Reclassify existing game_positions rows with latest position metadata.

Replays stored PGN through chess.Board, calls classify_position() at each
ply, and UPDATEs all classification columns. No re-download needed — uses
PGN already stored in the games table.

Resumable: detects unprocessed games by checking for NULL values in any
classification column. Re-run after interruption to pick up where left off.

Usage:
    uv run python scripts/reclassify_positions.py --all --yes
    uv run python scripts/reclassify_positions.py --user-id 42
"""

import argparse
import asyncio
import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path so `app.*` imports work when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chess
import chess.pgn
import sentry_sdk
from sqlalchemy import distinct, func, select, text
from sqlalchemy import update as sa_update

from app.core.config import settings
from app.core.database import async_session_maker, engine
from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.position_classifier import PositionClassification, classify_position

_BATCH_SIZE = 10  # games per DB commit — OOM-safe (STATE.md critical constraint)
_PROGRESS_INTERVAL = 50  # print progress every N games

# Classification columns on GamePosition that correspond to PositionClassification fields.
# Used to detect unprocessed rows (any NULL → needs reclassification) and to build UPDATE values.
# Derived from PositionClassification fields so adding a new field there automatically includes it here.
_CLASSIFICATION_COLUMNS = [
    getattr(GamePosition, field)
    for field in PositionClassification.__dataclass_fields__
    if hasattr(GamePosition, field)
]


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill position classification for existing game_positions rows."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--user-id",
        type=int,
        metavar="N",
        help="Backfill positions for a single user with this ID.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        dest="all_users",
        help="Backfill positions for all users.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt and proceed immediately.",
    )
    return parser.parse_args()


def _any_classification_null():
    """Build an OR filter: any classification column IS NULL."""
    from sqlalchemy import or_
    return or_(*(col.is_(None) for col in _CLASSIFICATION_COLUMNS))


async def count_unprocessed(session, user_id: int | None) -> int:
    """Count games with at least one position missing any classification column."""
    stmt = (
        select(func.count(distinct(GamePosition.game_id)))
        .where(_any_classification_null())
    )
    if user_id is not None:
        stmt = stmt.where(GamePosition.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_unprocessed_game_ids(
    session, batch_size: int, exclude_ids: set[int], user_id: int | None
) -> list[int]:
    """Find game_ids with at least one NULL classification column.

    Checks all classification columns derived from PositionClassification —
    adding a new field to the dataclass automatically includes it here.
    """
    stmt = (
        select(distinct(GamePosition.game_id))
        .where(_any_classification_null())
        .limit(batch_size)
    )
    if user_id is not None:
        stmt = stmt.where(GamePosition.user_id == user_id)
    if exclude_ids:
        stmt = stmt.where(GamePosition.game_id.notin_(exclude_ids))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def backfill_game(session, game_id: int, pgn: str) -> int:
    """Classify all positions for a single game and UPDATE rows.

    Returns the number of positions updated.

    Board classification happens BEFORE board.push() — pre-move board state
    semantics, matching how position rows are stored at import time.
    """
    game_obj = chess.pgn.read_game(io.StringIO(pgn))
    if game_obj is None:
        return 0

    board = game_obj.board()
    nodes = list(game_obj.mainline())
    positions_updated = 0

    def _classification_values(board: chess.Board) -> dict:
        """Return all classification fields as a dict for UPDATE.

        Derives keys from PositionClassification fields, so adding a new
        field to the dataclass automatically includes it in backfill.
        """
        c = classify_position(board)
        return {
            field: getattr(c, field)
            for field in PositionClassification.__dataclass_fields__
            if hasattr(GamePosition, field)
        }

    for i, node in enumerate(nodes):
        # Classify BEFORE pushing the move (pre-move board state = ply i)
        await session.execute(
            sa_update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == i)
            .values(**_classification_values(board))
        )
        positions_updated += 1
        board.push(node.move)

    # Classify the final position (after last move, no move_san)
    await session.execute(
        sa_update(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.ply == len(nodes))
        .values(**_classification_values(board))
    )
    positions_updated += 1

    return positions_updated


async def run_vacuum() -> None:
    """Run VACUUM ANALYZE on game_positions outside a transaction.

    VACUUM cannot run inside a transaction block — use AUTOCOMMIT isolation.
    The execution_options() call must be made on the connection object before
    execute() — they cannot be chained in a single statement.
    """
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("VACUUM ANALYZE game_positions"))


async def main() -> None:
    """Run the full backfill: reclassify positions with any NULL classification column, then VACUUM."""
    # Initialize Sentry for error tracking
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    args = parse_args()
    user_id = args.user_id if not args.all_users else None
    target_label = f"user {user_id}" if user_id else "all users"

    # Count unprocessed games
    async with async_session_maker() as session:
        unprocessed = await count_unprocessed(session, user_id)

    if unprocessed == 0:
        _log(f"No unprocessed games found for {target_label}. Nothing to do.")
        return

    _log(f"Backfill target: {target_label}")
    _log(f"Games to process: {unprocessed}")
    _log(f"Batch size: {_BATCH_SIZE} games per commit")

    # Confirm before proceeding (unless --yes flag given)
    if not args.yes:
        response = input(
            f"This will reclassify all positions for {unprocessed} games ({target_label}). "
            f"Proceed? [y/N] "
        )
        if response.strip().lower() not in ("y", "yes"):
            _log("Aborted.")
            return

    start_time = time.time()
    total_games = 0
    total_positions = 0
    total_errors = 0
    # Track permanently-failing game IDs to prevent infinite loop
    skipped_ids: set[int] = set()

    _log("Starting position classification backfill...")

    while True:
        async with async_session_maker() as session:
            game_ids = await get_unprocessed_game_ids(
                session, _BATCH_SIZE, skipped_ids, user_id
            )
            if not game_ids:
                break

            # Fetch PGN for this batch
            result = await session.execute(
                select(Game.id, Game.pgn).where(Game.id.in_(game_ids))
            )
            id_pgn_pairs = result.fetchall()

            for game_id, pgn in id_pgn_pairs:
                if not pgn:
                    skipped_ids.add(game_id)
                    total_errors += 1
                    continue
                try:
                    positions = await backfill_game(session, game_id, pgn)
                    total_positions += positions
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    _log(f"ERROR: Failed to classify game_id={game_id}: {e}")
                    skipped_ids.add(game_id)
                    total_errors += 1
                    continue
                total_games += 1

                if total_games % _PROGRESS_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = total_games / elapsed if elapsed > 0 else 0
                    _log(
                        f"Progress: {total_games}/{unprocessed} games "
                        f"({total_games * 100 // unprocessed}%), "
                        f"{total_positions} positions, "
                        f"{total_errors} errors, "
                        f"{rate:.1f} games/s"
                    )

            # Commit batch (batch_size=10 games per commit)
            await session.commit()

    # VACUUM ANALYZE after completion
    _log("Running VACUUM ANALYZE game_positions...")
    try:
        await run_vacuum()
        _log("VACUUM ANALYZE complete.")
    except Exception as e:
        _log(f"WARNING: VACUUM ANALYZE failed: {e}")
        sentry_sdk.capture_exception(e)

    elapsed = time.time() - start_time
    rate = total_games / elapsed if elapsed > 0 else 0
    _log("")
    _log("Backfill complete:")
    _log(f"  Games processed: {total_games}")
    _log(f"  Positions updated: {total_positions}")
    _log(f"  Errors (skipped): {total_errors}")
    _log(f"  Duration: {elapsed:.1f}s ({rate:.1f} games/s)")


if __name__ == "__main__":
    asyncio.run(main())

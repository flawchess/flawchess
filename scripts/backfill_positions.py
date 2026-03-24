"""Backfill position metadata for all existing game_positions rows.

Re-parses stored PGN from the games table, replays each game through
chess.Board, calls classify_position() at each ply, and UPDATEs the 4
metadata columns on existing game_positions rows.

Resumable: queries for games with NULL material_count — re-run after
interruption to pick up where it left off.

Usage: uv run python scripts/backfill_positions.py
"""

import asyncio
import io
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path so `app.*` imports work when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chess
import chess.pgn
import sentry_sdk
from sqlalchemy import distinct, select, text
from sqlalchemy import update as sa_update

from app.core.config import settings
from app.core.database import async_session_maker, engine
from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.position_classifier import classify_position

_BATCH_SIZE = 10  # games per DB commit — OOM-safe (STATE.md critical constraint)
_PROGRESS_INTERVAL = 50  # print progress every N games


async def get_unprocessed_game_ids(
    session, batch_size: int, exclude_ids: set[int]
) -> list[int]:
    """Find game_ids with at least one NULL material_count position."""
    stmt = (
        select(distinct(GamePosition.game_id))
        .where(GamePosition.material_count.is_(None))
        .limit(batch_size)
    )
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

    for i, node in enumerate(nodes):
        # Classify BEFORE pushing the move (pre-move board state = ply i)
        classification = classify_position(board)
        await session.execute(
            sa_update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == i)
            .values(
                material_count=classification.material_count,
                material_signature=classification.material_signature,
                material_imbalance=classification.material_imbalance,
                has_opposite_color_bishops=classification.has_opposite_color_bishops,
            )
        )
        positions_updated += 1
        board.push(node.move)

    # Classify the final position (after last move, no move_san)
    classification = classify_position(board)
    await session.execute(
        sa_update(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.ply == len(nodes))
        .values(
            material_count=classification.material_count,
            material_signature=classification.material_signature,
            material_imbalance=classification.material_imbalance,
            has_opposite_color_bishops=classification.has_opposite_color_bishops,
        )
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
    """Run the full backfill: process all games with NULL material_count, then VACUUM."""
    # Initialize Sentry for error tracking
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    start_time = time.time()
    total_games = 0
    total_positions = 0
    total_errors = 0
    # Track permanently-failing game IDs to prevent infinite loop
    skipped_ids: set[int] = set()

    print("Starting position metadata backfill...")
    print(f"Batch size: {_BATCH_SIZE} games per commit")

    while True:
        async with async_session_maker() as session:
            game_ids = await get_unprocessed_game_ids(session, _BATCH_SIZE, skipped_ids)
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
                    print(f"ERROR: Failed to classify game_id={game_id}: {e}")
                    skipped_ids.add(game_id)
                    total_errors += 1
                    continue
                total_games += 1

                if total_games % _PROGRESS_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    print(
                        f"Progress: {total_games} games, {total_positions} positions updated, "
                        f"{total_errors} errors, {elapsed:.1f}s elapsed"
                    )

            # Commit batch (batch_size=10 games per commit)
            await session.commit()

    # VACUUM ANALYZE after completion
    print("Running VACUUM ANALYZE game_positions...")
    try:
        await run_vacuum()
        print("VACUUM ANALYZE complete.")
    except Exception as e:
        print(f"WARNING: VACUUM ANALYZE failed: {e}")
        sentry_sdk.capture_exception(e)

    elapsed = time.time() - start_time
    print("\nBackfill complete:")
    print(f"  Games processed: {total_games}")
    print(f"  Positions updated: {total_positions}")
    print(f"  Errors (skipped): {total_errors}")
    print(f"  Duration: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())

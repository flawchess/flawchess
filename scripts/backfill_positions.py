"""Backfill position metadata for all existing game_positions rows.

Re-parses stored PGN from the games table, replays each game through
chess.Board, calls classify_position() at each ply, and UPDATEs the 7
metadata columns on existing game_positions rows.

Resumable: queries for games with NULL game_phase — re-run after
interruption to pick up where it left off.

Usage: uv run python scripts/backfill_positions.py
"""

import asyncio
import io
import time

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
_PROGRESS_INTERVAL = 50  # print progress every N games (per D-09)


async def get_unprocessed_game_ids(
    session, batch_size: int, exclude_ids: set[int]
) -> list[int]:
    """Find game_ids with at least one NULL game_phase position."""
    stmt = (
        select(distinct(GamePosition.game_id))
        .where(GamePosition.game_phase.is_(None))
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
                game_phase=classification.game_phase,
                material_signature=classification.material_signature,
                material_imbalance=classification.material_imbalance,
                endgame_class=classification.endgame_class,
                has_bishop_pair_white=classification.has_bishop_pair_white,
                has_bishop_pair_black=classification.has_bishop_pair_black,
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
            game_phase=classification.game_phase,
            material_signature=classification.material_signature,
            material_imbalance=classification.material_imbalance,
            endgame_class=classification.endgame_class,
            has_bishop_pair_white=classification.has_bishop_pair_white,
            has_bishop_pair_black=classification.has_bishop_pair_black,
            has_opposite_color_bishops=classification.has_opposite_color_bishops,
        )
    )
    positions_updated += 1

    return positions_updated


async def run_vacuum() -> None:
    """Run VACUUM ANALYZE on game_positions outside a transaction (per D-07).

    VACUUM cannot run inside a transaction block — use AUTOCOMMIT isolation.
    The execution_options() call must be made on the connection object before
    execute() — they cannot be chained in a single statement.
    """
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        await conn.execute(text("VACUUM ANALYZE game_positions"))


async def main() -> None:
    """Run the full backfill: process all games with NULL game_phase, then VACUUM."""
    # Initialize Sentry for error tracking (per D-08)
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    start_time = time.time()
    total_games = 0
    total_positions = 0
    total_errors = 0
    # Track permanently-failing game IDs to prevent infinite loop (Pitfall 4)
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
                    # Per D-08: skip and log via Sentry, continue backfill
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

            # Commit batch (per D-04: batch_size=10 games per commit)
            await session.commit()

    # Per D-07: VACUUM ANALYZE after completion
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

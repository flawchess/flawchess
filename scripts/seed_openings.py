"""Idempotent seed script: populate openings table from app/data/openings.tsv.

Uses board.board_fen() (not board.fen()) per project convention.
Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
Run with: uv run python -m scripts.seed_openings
"""
import asyncio
import csv
import io
import logging
from pathlib import Path

import chess
import chess.pgn
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TSV_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "openings.tsv"


def pgn_to_fen_and_ply(pgn_str: str) -> tuple[str, int]:
    """Compute piece-placement FEN and ply count from a PGN move sequence.

    Uses board.board_fen() (not board.fen()) per project convention.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_str))
    if game is None:
        raise ValueError(f"Failed to parse PGN: {pgn_str!r}")
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
    return board.board_fen(), board.ply()


async def seed_openings() -> int:
    """Read TSV and insert rows into openings table. Returns count of inserted rows."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = 0
    skipped = 0
    errors = 0

    async with async_session() as session:
        with open(TSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row_num, row in enumerate(reader, start=2):
                eco = row["eco"]
                name = row["name"]
                pgn_str = row["pgn"]
                try:
                    fen, ply_count = pgn_to_fen_and_ply(pgn_str)
                except Exception:
                    logger.warning("Row %d: failed to parse PGN %r — skipping", row_num, pgn_str)
                    errors += 1
                    continue

                result = await session.execute(
                    text(
                        "INSERT INTO openings (eco, name, pgn, ply_count, fen) "
                        "VALUES (:eco, :name, :pgn, :ply_count, :fen) "
                        "ON CONFLICT ON CONSTRAINT uq_openings_eco_name_pgn DO NOTHING"
                    ),
                    {"eco": eco, "name": name, "pgn": pgn_str, "ply_count": ply_count, "fen": fen},
                )
                if result.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1

        await session.commit()

    await engine.dispose()
    logger.info("Seed complete: %d inserted, %d skipped (already exist), %d errors", inserted, skipped, errors)
    return inserted


if __name__ == "__main__":
    asyncio.run(seed_openings())

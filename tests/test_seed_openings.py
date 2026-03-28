"""Tests for the openings seed script and dedup view.

Coverage:
- pgn_to_fen_and_ply: correct FEN and ply for known openings
- seed_openings: inserts rows from TSV
- seed_openings: idempotent (running twice does not duplicate rows)
- openings_dedup: returns one row per (eco, name) pair
"""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opening import Opening
from scripts.seed_openings import pgn_to_fen_and_ply, seed_openings


@pytest.fixture(scope="session", autouse=True)
def seed_openings_for_tests(test_engine):
    """Seed the openings table in the test DB once per session.

    The migration (run by test_engine fixture) creates the schema; this fixture
    populates the data. Running seed_openings is idempotent so it is safe to
    call even if the table already has rows.
    """
    import asyncio

    # Run the seed against the test DB (settings.DATABASE_URL already patched to
    # TEST_DATABASE_URL by the conftest test_engine fixture).
    asyncio.run(seed_openings())


class TestPgnToFenAndPly:
    """Unit tests for pgn_to_fen_and_ply helper."""

    def test_single_move_opening(self) -> None:
        """1. e4 should produce ply_count=1 and correct FEN."""
        fen, ply = pgn_to_fen_and_ply("1. e4")
        assert ply == 1
        # After 1. e4, the board should have the pawn on e4
        assert "4P3" in fen  # e4 pawn in rank 4

    def test_two_move_opening(self) -> None:
        """1. e4 e5 should produce ply_count=2."""
        fen, ply = pgn_to_fen_and_ply("1. e4 e5")
        assert ply == 2

    def test_uses_board_fen_not_full_fen(self) -> None:
        """FEN must be piece-placement only (no castling/en passant/move counters)."""
        fen, _ = pgn_to_fen_and_ply("1. e4 e5")
        # board_fen() has exactly 7 slashes (8 ranks separated by /)
        assert fen.count("/") == 7
        # board_fen() does NOT contain spaces (full FEN has spaces for castling etc.)
        assert " " not in fen

    def test_invalid_pgn_raises(self) -> None:
        """Invalid PGN should raise ValueError."""
        with pytest.raises(ValueError, match="Failed to parse PGN"):
            pgn_to_fen_and_ply("")


@pytest.mark.asyncio(loop_scope="session")
class TestSeedOpeningsIntegration:
    """Integration tests verifying seed data exists in openings table.

    These tests rely on the seed script having been run during test setup
    (the migration + seed populate the openings table). They verify the
    data is correct, not the seed script execution itself.
    """

    async def test_openings_table_has_expected_row_count(self, db_session: AsyncSession) -> None:
        """openings table should have ~3641 rows from TSV."""
        result = await db_session.execute(select(func.count()).select_from(Opening))
        count = result.scalar_one()
        # Allow small tolerance for TSV updates, but should be close to 3641
        assert count >= 3600, f"Expected ~3641 rows, got {count}"

    async def test_opening_row_has_valid_fen_and_ply(self, db_session: AsyncSession) -> None:
        """Spot-check: a known opening has correct fen and ply_count."""
        result = await db_session.execute(
            select(Opening).where(Opening.eco == "B00", Opening.name == "King's Pawn Game")
        )
        opening = result.scalars().first()
        assert opening is not None
        assert opening.ply_count == 1  # 1. e4
        assert "4P3" in opening.fen  # pawn on e4

    async def test_seed_idempotent_no_duplicates(self, db_session: AsyncSession) -> None:
        """UniqueConstraint prevents duplicate (eco, name, pgn) rows."""
        # Count before — already seeded
        result = await db_session.execute(select(func.count()).select_from(Opening))
        count_before = result.scalar_one()
        assert count_before >= 3600

        # The UniqueConstraint ensures ON CONFLICT DO NOTHING works.
        # We verify by checking there are no duplicate (eco, name, pgn) triples.
        dup_result = await db_session.execute(
            text(
                "SELECT eco, name, pgn, COUNT(*) "
                "FROM openings GROUP BY eco, name, pgn HAVING COUNT(*) > 1"
            )
        )
        duplicates = dup_result.fetchall()
        assert len(duplicates) == 0, f"Found duplicate rows: {duplicates}"

    async def test_dedup_view_returns_fewer_rows(self, db_session: AsyncSession) -> None:
        """openings_dedup should have fewer rows than openings (collapses duplicate eco+name)."""
        total_result = await db_session.execute(select(func.count()).select_from(Opening))
        total = total_result.scalar_one()

        dedup_result = await db_session.execute(text("SELECT COUNT(*) FROM openings_dedup"))
        dedup_count = dedup_result.scalar_one()

        assert dedup_count < total, f"Dedup ({dedup_count}) should be < total ({total})"
        assert dedup_count >= 3200, f"Expected ~3301 dedup rows, got {dedup_count}"

    async def test_dedup_view_has_one_row_per_eco_name(self, db_session: AsyncSession) -> None:
        """Each (eco, name) pair appears exactly once in the dedup view."""
        result = await db_session.execute(
            text(
                "SELECT eco, name, COUNT(*) "
                "FROM openings_dedup GROUP BY eco, name HAVING COUNT(*) > 1"
            )
        )
        duplicates = result.fetchall()
        assert len(duplicates) == 0, f"Dedup view has duplicate (eco, name): {duplicates}"

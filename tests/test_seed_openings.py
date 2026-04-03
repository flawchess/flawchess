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
from scripts.seed_openings import pgn_to_fen_ply_hashes, seed_openings


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


class TestPgnToFenPlyHashes:
    """Unit tests for pgn_to_fen_ply_hashes helper."""

    def test_single_move_opening(self) -> None:
        """1. e4 should produce ply_count=1 and correct FEN."""
        fen, ply, wh, bh, fh = pgn_to_fen_ply_hashes("1. e4")
        assert ply == 1
        # After 1. e4, the board should have the pawn on e4
        assert "4P3" in fen  # e4 pawn in rank 4
        # Hashes should be non-zero integers
        assert isinstance(fh, int) and fh != 0
        assert isinstance(wh, int) and wh != 0
        assert isinstance(bh, int) and bh != 0

    def test_two_move_opening(self) -> None:
        """1. e4 e5 should produce ply_count=2."""
        fen, ply, _wh, _bh, _fh = pgn_to_fen_ply_hashes("1. e4 e5")
        assert ply == 2

    def test_uses_full_fen_with_metadata(self) -> None:
        """FEN must include side-to-move and castling — not board-only.

        Full FEN is needed so downstream consumers (bookmark creation, match_side
        toggling) can reconstruct an accurate Board for Zobrist hash computation.
        """
        fen, *_ = pgn_to_fen_ply_hashes("1. e4 e5")
        # Full FEN has spaces separating piece placement, side-to-move, castling, etc.
        assert " " in fen
        # After 1. e4 e5, it's white's turn
        assert " w " in fen

    def test_invalid_pgn_raises(self) -> None:
        """Invalid PGN should raise ValueError."""
        with pytest.raises(ValueError, match="Failed to parse PGN"):
            pgn_to_fen_ply_hashes("")

    def test_hashes_match_import_pipeline(self) -> None:
        """full_hash from seed must match what hashes_for_game produces during import."""
        from app.services.zobrist import hashes_for_game
        pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5"
        _fen, _ply, _wh, _bh, seed_full_hash = pgn_to_fen_ply_hashes(pgn)
        # hashes_for_game returns list of (ply, wh, bh, fh, move, clock) tuples
        hashes, _result_fen = hashes_for_game(pgn)
        # Last entry is the final position (ply 3)
        import_full_hash = hashes[-1][3]
        assert seed_full_hash == import_full_hash, (
            f"Seed hash {seed_full_hash} != import hash {import_full_hash}"
        )


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

    async def test_openings_have_zobrist_hashes(self, db_session: AsyncSession) -> None:
        """All openings should have non-null Zobrist hashes after seeding."""
        result = await db_session.execute(
            select(func.count()).select_from(Opening).where(Opening.full_hash.is_(None))
        )
        null_count = result.scalar_one()
        assert null_count == 0, f"{null_count} openings have NULL full_hash"

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

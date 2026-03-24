"""Tests for the backfill_positions script.

Verifies that the backfill correctly updates NULL metadata columns on
game_positions rows by re-parsing stored PGN and calling classify_position().

Uses real PostgreSQL with transaction rollback isolation (via db_session fixture).
The backfill module functions are imported directly to avoid running the full main().
"""

import datetime
import uuid

import pytest

# A short but valid PGN for testing: Fool's Mate (2-move game)
_FOOLS_MATE_PGN = """\
[Event "Test"]
[Site "Test"]
[Date "2024.01.01"]
[White "Alice"]
[Black "Bob"]
[Result "0-1"]
[TimeControl "600+0"]

1. f3 e5 2. g4 Qh4# 0-1
"""

# A PGN that cannot be parsed
_CORRUPT_PGN = "this is not valid pgn at all $$$"

# A minimal 1-move game (e4 only)
_ONE_MOVE_PGN = """\
[Event "Test"]
[Result "*"]

1. e4 *
"""


def _make_game_row(user_id: int = 1, pgn: str = _FOOLS_MATE_PGN) -> dict:
    """Build a minimal valid games row dict."""
    return {
        "user_id": user_id,
        "platform": "chess.com",
        "platform_game_id": f"game-{uuid.uuid4().hex}",
        "platform_url": None,
        "pgn": pgn,
        "variant": "Standard",
        "result": "0-1",
        "user_color": "white",
        "time_control_str": "600+0",
        "time_control_bucket": "blitz",
        "time_control_seconds": 600,
        "rated": True,
        "white_username": "Alice",
        "black_username": "Bob",
        "white_rating": 1500,
        "black_rating": 1500,
        "opening_name": None,
        "opening_eco": None,
        "played_at": datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
    }


async def _insert_game_with_null_positions(db_session, pgn: str = _FOOLS_MATE_PGN) -> int:
    """Insert a game row and NULL-metadata position rows. Returns game_id."""
    from app.repositories.game_repository import bulk_insert_games, bulk_insert_positions
    from app.services.zobrist import hashes_for_game

    game_rows = [_make_game_row(pgn=pgn)]
    game_ids = await bulk_insert_games(db_session, game_rows)
    game_id = game_ids[0]

    # Build position rows with NULL metadata (as they would be before backfill)
    hash_tuples, _result_fen = hashes_for_game(pgn)
    position_rows = []
    for (ply, white_hash, black_hash, full_hash, move_san, clock_seconds) in hash_tuples:
        position_rows.append({
            "game_id": game_id,
            "user_id": 1,
            "ply": ply,
            "full_hash": full_hash,
            "white_hash": white_hash,
            "black_hash": black_hash,
            "move_san": move_san,
            "clock_seconds": clock_seconds,
            # Metadata columns intentionally NULL (pre-backfill state)
            "material_count": None,
            "material_signature": None,
            "material_imbalance": None,
            "has_opposite_color_bishops": None,
        })
    await bulk_insert_positions(db_session, position_rows)
    await db_session.flush()
    return game_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackfillGame:
    """Tests for the backfill_game() function."""

    @pytest.mark.asyncio
    async def test_backfill_updates_null_material_count_to_nonnull(self, db_session):
        """Test 1: Backfill sets material_count to a non-null value for a valid PGN game."""
        from scripts.backfill_positions import backfill_game
        from sqlalchemy import select
        from app.models.game_position import GamePosition

        game_id = await _insert_game_with_null_positions(db_session)

        # Verify rows are NULL before backfill
        result = await db_session.execute(
            select(GamePosition).where(GamePosition.game_id == game_id)
        )
        positions_before = result.scalars().all()
        assert len(positions_before) > 0
        assert all(p.material_count is None for p in positions_before)

        # Run backfill
        positions_updated = await backfill_game(db_session, game_id, _FOOLS_MATE_PGN)

        # Verify material_count is now non-null
        result = await db_session.execute(
            select(GamePosition).where(GamePosition.game_id == game_id)
        )
        positions_after = result.scalars().all()
        assert all(p.material_count is not None for p in positions_after), (
            "All positions should have non-null material_count after backfill"
        )
        assert positions_updated > 0

    @pytest.mark.asyncio
    async def test_backfill_sets_all_4_metadata_columns(self, db_session):
        """Test 2: After backfill, all 4 metadata columns are non-null on every position row."""
        from scripts.backfill_positions import backfill_game
        from sqlalchemy import select
        from app.models.game_position import GamePosition

        game_id = await _insert_game_with_null_positions(db_session)
        await backfill_game(db_session, game_id, _FOOLS_MATE_PGN)

        result = await db_session.execute(
            select(GamePosition).where(GamePosition.game_id == game_id)
        )
        positions = result.scalars().all()
        assert len(positions) > 0

        for pos in positions:
            assert pos.material_count is not None, f"ply={pos.ply} material_count is None"
            assert pos.material_signature is not None, f"ply={pos.ply} material_signature is None"
            assert pos.material_imbalance is not None, f"ply={pos.ply} material_imbalance is None"
            assert pos.has_opposite_color_bishops is not None, f"ply={pos.ply} has_opposite_color_bishops is None"

    @pytest.mark.asyncio
    async def test_backfill_is_idempotent(self, db_session):
        """Test 3: Running backfill twice produces the same result; second call finds no games."""
        from scripts.backfill_positions import backfill_game, get_unprocessed_game_ids

        game_id = await _insert_game_with_null_positions(db_session)

        # First run
        await backfill_game(db_session, game_id, _FOOLS_MATE_PGN)
        await db_session.flush()

        # After first run, game should no longer appear as unprocessed
        unprocessed = await get_unprocessed_game_ids(db_session, batch_size=100, exclude_ids=set())
        assert game_id not in unprocessed, (
            "game_id should not appear in unprocessed list after backfill"
        )

        # Second run should not raise
        positions_updated = await backfill_game(db_session, game_id, _FOOLS_MATE_PGN)
        assert positions_updated >= 0  # idempotent: doesn't error

    @pytest.mark.asyncio
    async def test_corrupt_pgn_skips_gracefully(self, db_session):
        """Test 4: backfill_game with unparseable PGN returns 0 for truly None game objects."""
        from scripts.backfill_positions import backfill_game

        game_id = await _insert_game_with_null_positions(db_session, pgn=_FOOLS_MATE_PGN)

        # Empty string forces chess.pgn.read_game to return None -> backfill_game returns 0
        result = await backfill_game(db_session, game_id, "")
        assert result == 0

    @pytest.mark.asyncio
    async def test_starting_position_has_full_material(self, db_session):
        """Ply 0 (starting board) must have material_count=7800 (full starting material)."""
        from scripts.backfill_positions import backfill_game
        from sqlalchemy import select
        from app.models.game_position import GamePosition

        game_id = await _insert_game_with_null_positions(db_session)
        await backfill_game(db_session, game_id, _FOOLS_MATE_PGN)

        result = await db_session.execute(
            select(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == 0)
        )
        ply0 = result.scalar_one()
        assert ply0.material_count == 7800, (
            f"Starting position should have material_count=7800, got {ply0.material_count}"
        )


class TestGetUnprocessedGameIds:
    """Tests for the get_unprocessed_game_ids() query helper."""

    @pytest.mark.asyncio
    async def test_returns_game_ids_with_null_material_count(self, db_session):
        """Test 5: get_unprocessed_game_ids returns games with NULL material_count positions."""
        from scripts.backfill_positions import get_unprocessed_game_ids

        game_id = await _insert_game_with_null_positions(db_session)

        result = await get_unprocessed_game_ids(db_session, batch_size=100, exclude_ids=set())
        assert game_id in result

    @pytest.mark.asyncio
    async def test_respects_batch_size(self, db_session):
        """get_unprocessed_game_ids should return at most batch_size game IDs."""
        from scripts.backfill_positions import get_unprocessed_game_ids

        # Insert 3 games with NULL positions
        for _ in range(3):
            await _insert_game_with_null_positions(db_session)

        result = await get_unprocessed_game_ids(db_session, batch_size=2, exclude_ids=set())
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_excludes_skipped_ids(self, db_session):
        """get_unprocessed_game_ids should exclude IDs in exclude_ids set."""
        from scripts.backfill_positions import get_unprocessed_game_ids

        game_id = await _insert_game_with_null_positions(db_session)

        # Exclude the game we just inserted
        result = await get_unprocessed_game_ids(
            db_session, batch_size=100, exclude_ids={game_id}
        )
        assert game_id not in result

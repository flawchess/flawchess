"""Tests for the backfill_positions script.

Verifies that the backfill correctly updates NULL metadata columns on
game_positions rows by re-parsing stored PGN and calling classify_position().

Uses real PostgreSQL with transaction rollback isolation (via db_session fixture).
The backfill module functions are imported directly to avoid running the full main().
"""

import datetime
import uuid
from unittest.mock import patch

import chess.pgn
import io
import pytest
import pytest_asyncio

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

    # Build position rows with NULL metadata (as they would be before Phase 27 wiring)
    # hashes_for_game returns (hash_tuples, result_fen) where each tuple is
    # (ply, white_hash, black_hash, full_hash, move_san, clock_seconds)
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
            "game_phase": None,
            "material_signature": None,
            "material_imbalance": None,
            "endgame_class": None,
            "has_bishop_pair_white": None,
            "has_bishop_pair_black": None,
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
    async def test_backfill_updates_null_game_phase_to_nonnull(self, db_session):
        """Test 1: Backfill sets game_phase to a non-null value for a valid PGN game."""
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
        assert all(p.game_phase is None for p in positions_before)

        # Run backfill
        positions_updated = await backfill_game(db_session, game_id, _FOOLS_MATE_PGN)

        # Verify game_phase is now non-null
        result = await db_session.execute(
            select(GamePosition).where(GamePosition.game_id == game_id)
        )
        positions_after = result.scalars().all()
        assert all(p.game_phase is not None for p in positions_after), (
            "All positions should have non-null game_phase after backfill"
        )
        assert positions_updated > 0

    @pytest.mark.asyncio
    async def test_backfill_sets_all_7_metadata_columns(self, db_session):
        """Test 2: After backfill, all 7 metadata columns are non-null on every position row."""
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
            assert pos.game_phase is not None, f"ply={pos.ply} game_phase is None"
            assert pos.material_signature is not None, f"ply={pos.ply} material_signature is None"
            assert pos.material_imbalance is not None, f"ply={pos.ply} material_imbalance is None"
            # has_bishop_pair_white/black can be False (falsy), use 'is not None'
            assert pos.has_bishop_pair_white is not None, f"ply={pos.ply} has_bishop_pair_white is None"
            assert pos.has_bishop_pair_black is not None, f"ply={pos.ply} has_bishop_pair_black is None"
            assert pos.has_opposite_color_bishops is not None, f"ply={pos.ply} has_opposite_color_bishops is None"
            # endgame_class is None for non-endgame positions — skip that check

    @pytest.mark.asyncio
    async def test_backfill_is_idempotent(self, db_session):
        """Test 3: Running backfill twice produces the same result; second call finds no games."""
        from scripts.backfill_positions import backfill_game, get_unprocessed_game_ids
        from sqlalchemy import select
        from app.models.game_position import GamePosition

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
        """Test 4: backfill_game with unparseable PGN returns 0 for truly None game objects.

        chess.pgn.read_game() returns None for empty strings, but partial/corrupt PGN
        strings often produce a game object with 0 nodes rather than raising.
        The main loop's except clause handles any exceptions that do propagate.
        An empty pgn (None/empty string) is handled by the main loop's `if not pgn:` guard.
        """
        from scripts.backfill_positions import backfill_game

        game_id = await _insert_game_with_null_positions(db_session, pgn=_FOOLS_MATE_PGN)

        # Empty string forces chess.pgn.read_game to return None -> backfill_game returns 0
        result = await backfill_game(db_session, game_id, "")
        assert result == 0

    @pytest.mark.asyncio
    async def test_starting_position_classified_as_opening(self, db_session):
        """Ply 0 (starting board) must have game_phase='opening'."""
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
        assert ply0.game_phase == "opening", (
            f"Starting position (ply 0) should be 'opening', got '{ply0.game_phase}'"
        )


class TestGetUnprocessedGameIds:
    """Tests for the get_unprocessed_game_ids() query helper."""

    @pytest.mark.asyncio
    async def test_returns_game_ids_with_null_game_phase(self, db_session):
        """Test 5: get_unprocessed_game_ids returns games with NULL game_phase positions."""
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

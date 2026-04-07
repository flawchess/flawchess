"""Integration tests for the endgame repository.

All tests use a real PostgreSQL database through the db_session fixture,
which wraps each test in a rolled-back transaction for isolation.

Coverage:
- query_endgame_entry_rows: returns empty list for user with no endgame positions
- query_endgame_entry_rows: returns one row per (game_id, endgame_class) span with >= 6 plies
- query_endgame_entry_rows: ply threshold filters short spans (< 6 plies)
- query_endgame_entry_rows: multi-class per game — game counts in both rook and pawn categories
- query_endgame_entry_rows: material_imbalance from first ply of each span
- query_endgame_entry_rows: time_control filter returns only matching games
- query_endgame_entry_rows: platform filter returns only matching games
- query_endgame_games: returns paginated GameRecord-shaped rows for a given endgame class
- query_endgame_games: returns empty list for unknown endgame class
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition

# Import the threshold constants and repository functions.
from app.repositories.endgame_repository import (
    ENDGAME_PIECE_COUNT_THRESHOLD,
    ENDGAME_PLY_THRESHOLD,
    query_endgame_entry_rows,
    query_endgame_games,
)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _unique_game_id() -> str:
    """Return a unique platform_game_id for each call."""
    return str(uuid.uuid4())


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [2, 99999]:
        await ensure_test_user(db_session, uid)


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 99999,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    time_control_bucket: str | None = "blitz",
    played_at: datetime.datetime | None = None,
    rated: bool = True,
    is_computer_game: bool = False,
) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_game_id(),
        platform_url=f"https://{platform}/game/123",
        pgn="1. e4 e5 *",
        variant="Standard",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        is_computer_game=is_computer_game,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()
    return game


async def _seed_game_position(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    piece_count: int = 2,
    material_count: int = 1000,
    material_signature: str = "KR_KR",
    material_imbalance: int = 0,
    endgame_class: int | None = 1,  # Default 1 (rook) matching default material_signature KR_KR
) -> GamePosition:
    """Insert a GamePosition row with endgame-relevant metadata.

    piece_count defaults to 2 (KR_KR — rook endgame, safely below threshold of 6).
    endgame_class defaults to 1 (rook), matching the default material_signature KR_KR.
    Use endgame_class=None for non-endgame positions.
    """
    pos = GamePosition(
        game_id=game.id,
        user_id=game.user_id,
        ply=ply,
        full_hash=hash(f"{game.id}-{ply}"),  # deterministic unique hash
        white_hash=hash(f"w-{game.id}-{ply}"),
        black_hash=hash(f"b-{game.id}-{ply}"),
        move_san=None,
        piece_count=piece_count,
        material_count=material_count,
        material_signature=material_signature,
        material_imbalance=material_imbalance,
        endgame_class=endgame_class,
    )
    session.add(pos)
    await session.flush()
    return pos


# ---------------------------------------------------------------------------
# TestQueryEndgameEntryRows
# ---------------------------------------------------------------------------


class TestQueryEndgameEntryRows:
    """Tests for query_endgame_entry_rows repository function."""

    @pytest.mark.asyncio
    async def test_no_games_returns_empty(self, db_session: AsyncSession) -> None:
        """User with no games returns empty list."""
        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_no_endgame_positions_returns_empty(self, db_session: AsyncSession) -> None:
        """Game with no endgame_class positions returns empty (endgame_class=None filters out)."""
        game = await _seed_game(db_session)
        # Position with no endgame class — not counted
        await _seed_game_position(
            db_session,
            game=game,
            ply=10,
            piece_count=ENDGAME_PIECE_COUNT_THRESHOLD + 2,
            material_signature="KQRB_KQRB",
            endgame_class=None,
        )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_returns_one_row_per_game_class_span(self, db_session: AsyncSession) -> None:
        """A game with >= ENDGAME_PLY_THRESHOLD positions of one class returns exactly one row."""
        game = await _seed_game(db_session)
        # Seed exactly ENDGAME_PLY_THRESHOLD rook endgame positions
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        # Should return exactly one row for this (game, rook) span
        assert len(rows) == 1
        game_id, endgame_class, result, user_color, user_material_imbalance, user_material_imbalance_after = rows[0]
        assert game_id == game.id
        assert endgame_class == 1  # rook

    @pytest.mark.asyncio
    async def test_ply_threshold_filters_short_spans(self, db_session: AsyncSession) -> None:
        """A game with fewer than ENDGAME_PLY_THRESHOLD plies in a class is excluded."""
        game = await _seed_game(db_session)
        # Seed only ENDGAME_PLY_THRESHOLD - 2 rook positions (below threshold)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD - 2):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        # Short span filtered out by HAVING clause
        assert rows == []

    @pytest.mark.asyncio
    async def test_multi_class_per_game(self, db_session: AsyncSession) -> None:
        """A game with >= threshold plies in two classes returns TWO rows (one per class)."""
        game = await _seed_game(db_session)
        # 7 rook endgame positions (endgame_class=1)
        for ply in range(20, 27):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )
        # 6 pawn endgame positions (endgame_class=3)
        for ply in range(30, 36):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KPP_KP", endgame_class=3
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        # Should return two rows: one for rook span, one for pawn span
        assert len(rows) == 2
        classes = {r[1] for r in rows}  # endgame_class is index 1
        assert 1 in classes  # rook
        assert 3 in classes  # pawn
        # Both rows belong to the same game
        assert all(r[0] == game.id for r in rows)

    @pytest.mark.asyncio
    async def test_entry_imbalance_at_first_ply_of_span(self, db_session: AsyncSession) -> None:
        """material_imbalance at the first (MIN) ply of each span is used for conversion/recovery."""
        game = await _seed_game(db_session, user_color="white")
        # Seed 6 rook positions; first at ply=20 with imbalance=200, rest with different values
        await _seed_game_position(
            db_session, game=game, ply=20, material_signature="KR_KR",
            endgame_class=1, material_imbalance=200
        )
        for ply in range(21, 26):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR",
                endgame_class=1, material_imbalance=50  # different from entry ply
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        _game_id, _endgame_class, _result, user_color, user_material_imbalance, user_material_imbalance_after = rows[0]
        # For white user, user_material_imbalance = material_imbalance at entry ply (ply=20)
        assert user_color == "white"
        assert user_material_imbalance == 200  # from first ply of span
        # user_material_imbalance_after = imbalance at ply=24 (entry+4 = ply 20+4)
        # All plies 21-25 have imbalance=50, so after-value is 50
        assert user_material_imbalance_after == 50

    @pytest.mark.asyncio
    async def test_time_control_filter(self, db_session: AsyncSession) -> None:
        """time_control filter returns only games with matching time_control_bucket."""
        blitz_game = await _seed_game(db_session, time_control_bucket="blitz")
        rapid_game = await _seed_game(db_session, time_control_bucket="rapid")

        for game in [blitz_game, rapid_game]:
            for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
                await _seed_game_position(
                    db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
                )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=["blitz"],
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        game_ids = [r[0] for r in rows]
        assert blitz_game.id in game_ids
        assert rapid_game.id not in game_ids

    @pytest.mark.asyncio
    async def test_platform_filter(self, db_session: AsyncSession) -> None:
        """platform filter returns only games from the specified platform."""
        chesscom_game = await _seed_game(db_session, platform="chess.com")
        lichess_game = await _seed_game(db_session, platform="lichess")

        for game in [chesscom_game, lichess_game]:
            for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
                await _seed_game_position(
                    db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
                )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=["lichess"],
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        game_ids = [r[0] for r in rows]
        assert lichess_game.id in game_ids
        assert chesscom_game.id not in game_ids


# ---------------------------------------------------------------------------
# TestQueryEndgameGames
# ---------------------------------------------------------------------------


class TestQueryEndgameGames:
    """Tests for query_endgame_games repository function."""

    @pytest.mark.asyncio
    async def test_returns_games_for_rook_endgame(self, db_session: AsyncSession) -> None:
        """query_endgame_games returns Game objects for games with >= threshold rook plies."""
        game = await _seed_game(db_session)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        games, matched_count = await query_endgame_games(
            db_session,
            user_id=99999,
            endgame_class="rook",
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            offset=0,
            limit=20,
        )
        assert matched_count == 1
        assert len(games) == 1
        # Verify it returns game objects with expected attributes
        returned_game = games[0]
        assert returned_game.id == game.id

    @pytest.mark.asyncio
    async def test_unknown_endgame_class_returns_empty(self, db_session: AsyncSession) -> None:
        """Unknown endgame class (not rook/minor_piece/pawn/queen/mixed/pawnless) returns empty."""
        game = await _seed_game(db_session)
        for ply in range(30, 30 + ENDGAME_PLY_THRESHOLD):
            await _seed_game_position(
                db_session, game=game, ply=ply, material_signature="KR_KR", endgame_class=1
            )

        games, matched_count = await query_endgame_games(
            db_session,
            user_id=99999,
            endgame_class="nonexistent_class",  # ty: ignore[invalid-argument-type]  # intentionally testing invalid class
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            offset=0,
            limit=20,
        )
        assert matched_count == 0
        assert games == []

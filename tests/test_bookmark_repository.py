"""Integration tests for position bookmark repository.

Coverage:
- TestCRUD: BKM-01 - create, list, update, delete position bookmarks
- TestReorder: BKM-02 - drag-reorder support with sort_order reassignment
- TestIsolation: BKM-05 - per-user isolation enforced at repository layer
- TestSuggestions: AUTOBKM-01..04 - suggestion query, deduplication, match_side heuristic
- TestMatchSideUpdate: AUTOBKM-03 - update_match_side with target_hash recomputation
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.position_bookmark_repository import (
    create_bookmark,
    delete_bookmark,
    get_bookmarks,
    get_top_positions_for_color,
    reorder_bookmarks,
    suggest_match_side,
    update_bookmark,
    update_match_side,
)
from app.schemas.position_bookmarks import (
    BookmarkMatchSide,
    Color,
    PositionBookmarkCreate,
    PositionBookmarkUpdate,
)
from app.services.zobrist import compute_hashes

import chess


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_create(
    label: str = "Test Bookmark",
    target_hash: int = 1234567890,
    fen: str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    moves: list[str] | None = None,
    color: Color | None = "white",
    match_side: BookmarkMatchSide = "full",
) -> PositionBookmarkCreate:
    return PositionBookmarkCreate(
        label=label,
        target_hash=target_hash,
        fen=fen,
        moves=moves or ["e4"],
        color=color,
        match_side=match_side,
    )


# ---------------------------------------------------------------------------
# Ensure test users exist (FK constraints require valid user_id)
# ---------------------------------------------------------------------------

# All user IDs used across bookmark tests
_TEST_USER_IDS = [1, 2, 3, 10, 20, 99, 500, 501, 502, 503, 504, 505, 600, 601, 700, 701, 710]


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure all test user IDs exist in the users table before each test."""
    from tests.conftest import ensure_test_user
    for uid in _TEST_USER_IDS:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# TestCRUD — BKM-01
# ---------------------------------------------------------------------------


class TestCRUD:
    """Verify basic CRUD operations on position bookmarks."""

    @pytest.mark.asyncio
    async def test_create_bookmark(self, db_session: AsyncSession) -> None:
        """Creates a position bookmark and returns PositionBookmark ORM with id set."""
        data = _make_create(label="My Bookmark")
        bookmark = await create_bookmark(db_session, user_id=1, data=data)

        assert bookmark.id is not None
        assert bookmark.label == "My Bookmark"
        assert bookmark.user_id == 1
        assert bookmark.target_hash == 1234567890
        assert bookmark.color == "white"
        assert bookmark.match_side == "full"

    @pytest.mark.asyncio
    async def test_get_bookmarks(self, db_session: AsyncSession) -> None:
        """Lists position bookmarks ordered by sort_order ascending."""
        await create_bookmark(db_session, user_id=1, data=_make_create(label="C"))
        b2 = await create_bookmark(db_session, user_id=1, data=_make_create(label="B"))
        b3 = await create_bookmark(db_session, user_id=1, data=_make_create(label="A"))

        # Manually adjust sort_order to test ordering
        b2.sort_order = 5
        b3.sort_order = 10
        await db_session.flush()

        bookmarks = await get_bookmarks(db_session, user_id=1)
        # Should be ordered by sort_order ascending
        assert len(bookmarks) >= 3
        # Verify the last two we inserted are in order
        labels = [b.label for b in bookmarks]
        b2_idx = labels.index("B")
        b3_idx = labels.index("A")
        assert b2_idx < b3_idx

    @pytest.mark.asyncio
    async def test_update_label(self, db_session: AsyncSession) -> None:
        """Updates label field, other fields unchanged."""
        bookmark = await create_bookmark(
            db_session,
            user_id=1,
            data=_make_create(label="Original", match_side="mine"),
        )
        original_hash = bookmark.target_hash
        original_sort_order = bookmark.sort_order

        updated = await update_bookmark(
            db_session,
            user_id=1,
            bookmark_id=bookmark.id,
            data=PositionBookmarkUpdate(label="Updated"),
        )

        assert updated is not None
        assert updated.label == "Updated"
        assert updated.target_hash == original_hash  # unchanged
        assert updated.sort_order == original_sort_order  # unchanged
        assert updated.match_side == "mine"  # unchanged

    @pytest.mark.asyncio
    async def test_delete_bookmark(self, db_session: AsyncSession) -> None:
        """Removes position bookmark; subsequent get returns empty list."""
        bookmark = await create_bookmark(
            db_session, user_id=99, data=_make_create(label="ToDelete")
        )
        result = await delete_bookmark(db_session, user_id=99, bookmark_id=bookmark.id)

        assert result is True
        remaining = await get_bookmarks(db_session, user_id=99)
        assert len(remaining) == 0


# ---------------------------------------------------------------------------
# TestReorder — BKM-02
# ---------------------------------------------------------------------------


class TestReorder:
    """Verify drag-reorder sort_order reassignment."""

    @pytest.mark.asyncio
    async def test_reorder_assigns_zero_to_n(self, db_session: AsyncSession) -> None:
        """reorder([id3, id1, id2]) sets sort_order to [0, 1, 2] respectively."""
        b1 = await create_bookmark(db_session, user_id=2, data=_make_create(label="First"))
        b2 = await create_bookmark(db_session, user_id=2, data=_make_create(label="Second"))
        b3 = await create_bookmark(db_session, user_id=2, data=_make_create(label="Third"))

        # Reorder: b3, b1, b2
        reordered = await reorder_bookmarks(
            db_session,
            user_id=2,
            ordered_ids=[b3.id, b1.id, b2.id],
        )

        # Build id -> sort_order map
        order_map = {b.id: b.sort_order for b in reordered}
        assert order_map[b3.id] == 0
        assert order_map[b1.id] == 1
        assert order_map[b2.id] == 2

    @pytest.mark.asyncio
    async def test_reorder_after_delete(self, db_session: AsyncSession) -> None:
        """After deleting one bookmark, reorder with remaining IDs reassigns 0..N-1 without gaps."""
        b1 = await create_bookmark(db_session, user_id=3, data=_make_create(label="Keep1"))
        b2 = await create_bookmark(db_session, user_id=3, data=_make_create(label="Delete"))
        b3 = await create_bookmark(db_session, user_id=3, data=_make_create(label="Keep2"))

        # Delete b2
        await delete_bookmark(db_session, user_id=3, bookmark_id=b2.id)

        # Reorder remaining: b3, b1
        reordered = await reorder_bookmarks(
            db_session,
            user_id=3,
            ordered_ids=[b3.id, b1.id],
        )

        assert len(reordered) == 2
        order_map = {b.id: b.sort_order for b in reordered}
        assert order_map[b3.id] == 0
        assert order_map[b1.id] == 1


# ---------------------------------------------------------------------------
# TestIsolation — BKM-05
# ---------------------------------------------------------------------------


class TestIsolation:
    """Verify per-user isolation: users cannot see or modify each other's position bookmarks."""

    @pytest.mark.asyncio
    async def test_user_b_cannot_read_user_a(self, db_session: AsyncSession) -> None:
        """get_bookmarks(user_id=B) returns empty even when user A has bookmarks."""
        await create_bookmark(db_session, user_id=10, data=_make_create(label="UserA Bookmark"))

        bookmarks_b = await get_bookmarks(db_session, user_id=20)
        assert len(bookmarks_b) == 0

    @pytest.mark.asyncio
    async def test_update_wrong_user_returns_none(self, db_session: AsyncSession) -> None:
        """update_bookmark with wrong user_id returns None (no update)."""
        bookmark = await create_bookmark(
            db_session, user_id=10, data=_make_create(label="UserA Bookmark")
        )

        result = await update_bookmark(
            db_session,
            user_id=20,  # wrong user
            bookmark_id=bookmark.id,
            data=PositionBookmarkUpdate(label="Hacked"),
        )

        assert result is None

        # Verify original is unchanged
        originals = await get_bookmarks(db_session, user_id=10)
        assert originals[0].label == "UserA Bookmark"

    @pytest.mark.asyncio
    async def test_delete_wrong_user_returns_false(self, db_session: AsyncSession) -> None:
        """delete_bookmark with wrong user_id returns False."""
        bookmark = await create_bookmark(
            db_session, user_id=10, data=_make_create(label="UserA Bookmark")
        )

        result = await delete_bookmark(
            db_session,
            user_id=20,  # wrong user
            bookmark_id=bookmark.id,
        )

        assert result is False

        # Verify original still exists
        originals = await get_bookmarks(db_session, user_id=10)
        assert len(originals) == 1


# ---------------------------------------------------------------------------
# Helpers for suggestion/match_side tests
# ---------------------------------------------------------------------------


def _unique_platform_id() -> str:
    return str(uuid.uuid4())


async def _seed_game_with_positions(
    session: AsyncSession,
    *,
    user_id: int,
    user_color: str = "white",
    positions: list[dict],
) -> Game:
    """Insert a Game and one or more GamePosition rows, return the Game."""
    from tests.conftest import ensure_test_user
    await ensure_test_user(session, user_id)
    game = Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=_unique_platform_id(),
        pgn="1. e4 e5 *",
        variant="Standard",
        result="1-0",
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        white_username="testuser",
        black_username="opponent",
    )
    session.add(game)
    await session.flush()

    for pos in positions:
        gp = GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=pos["ply"],
            full_hash=pos["full_hash"],
            white_hash=pos["white_hash"],
            black_hash=pos["black_hash"],
        )
        session.add(gp)

    await session.flush()
    return game


# ---------------------------------------------------------------------------
# TestSuggestions — AUTOBKM-01, AUTOBKM-02, AUTOBKM-04
# ---------------------------------------------------------------------------


class TestSuggestions:
    """Verify get_top_positions_for_color and deduplication logic."""

    @pytest.mark.asyncio
    async def test_get_top_positions_returns_results(self, db_session: AsyncSession) -> None:
        """get_top_positions_for_color returns positions ordered by game_count DESC.

        Positions must have at least 2 games to appear in results (minimum game count filter).
        """
        uid = 500

        # Position A appears in 3 games (white_hash=2001, different full_hashes per game)
        for i in range(3):
            await _seed_game_with_positions(
                db_session,
                user_id=uid,
                user_color="white",
                positions=[{"ply": 8, "full_hash": 1001 + i, "white_hash": 2001, "black_hash": 3001 + i}],
            )

        # Position B appears in 2 games (white_hash=2002)
        for i in range(2):
            await _seed_game_with_positions(
                db_session,
                user_id=uid,
                user_color="white",
                positions=[{"ply": 10, "full_hash": 1010 + i, "white_hash": 2002, "black_hash": 3010 + i}],
            )

        results = await get_top_positions_for_color(
            db_session,
            user_id=uid,
            color="white",
            ply_min=6,
            ply_max=14,
            limit=5,
            exclude_target_hashes=set(),
        )

        # Both positions have >= 2 games and should appear
        assert len(results) >= 2
        assert len(results) <= 5

        # Results are deduplicated by white_hash (the target hash for white)
        white_hashes = [r[0] for r in results]
        assert 2001 in white_hashes  # Position A present
        assert 2002 in white_hashes  # Position B present

        # First result should have higher game_count (Position A with 3 games)
        assert results[0][3] >= results[1][3]  # game_count descending

    @pytest.mark.asyncio
    async def test_get_top_positions_excludes_hashes(self, db_session: AsyncSession) -> None:
        """get_top_positions_for_color excludes positions whose target hash (color hash) is in exclude_target_hashes."""
        uid = 501

        # Position A: white_hash=2101, Position B: white_hash=2102, both with 2 games
        for wh_offset in [0, 1]:
            for i in range(2):
                await _seed_game_with_positions(
                    db_session,
                    user_id=uid,
                    user_color="white",
                    positions=[{"ply": 8, "full_hash": 1100 + wh_offset * 10 + i, "white_hash": 2101 + wh_offset, "black_hash": 3100 + i}],
                )

        # Exclude position A by its target hash (white_hash for white color)
        results = await get_top_positions_for_color(
            db_session,
            user_id=uid,
            color="white",
            ply_min=6,
            ply_max=14,
            limit=5,
            exclude_target_hashes={2101},  # exclude by white_hash (target hash for white)
        )

        white_hashes = [r[0] for r in results]
        assert 2101 not in white_hashes  # Position A excluded
        assert 2102 in white_hashes      # Position B still present

    @pytest.mark.asyncio
    async def test_get_top_positions_respects_color_filter(self, db_session: AsyncSession) -> None:
        """get_top_positions_for_color only returns positions for the given user_color."""
        uid = 502

        # Insert white game with position at ply 8 (2 games to meet minimum)
        for _ in range(2):
            await _seed_game_with_positions(
                db_session,
                user_id=uid,
                user_color="white",
                positions=[{"ply": 8, "full_hash": 1201, "white_hash": 2201, "black_hash": 3201}],
            )

        # Query for black — should not include the white game's position
        results = await get_top_positions_for_color(
            db_session,
            user_id=uid,
            color="black",
            ply_min=6,
            ply_max=14,
            limit=5,
            exclude_target_hashes=set(),
        )

        white_hashes = [r[0] for r in results]
        assert 2201 not in white_hashes

    @pytest.mark.asyncio
    async def test_get_top_positions_minimum_two_games(self, db_session: AsyncSession) -> None:
        """Positions with only 1 game are excluded (minimum game count = 2)."""
        uid = 503

        # Position A: only 1 game — should be excluded
        await _seed_game_with_positions(
            db_session,
            user_id=uid,
            user_color="white",
            positions=[{"ply": 8, "full_hash": 1301, "white_hash": 2301, "black_hash": 3301}],
        )

        # Position B: 2 games — should be included
        for _ in range(2):
            await _seed_game_with_positions(
                db_session,
                user_id=uid,
                user_color="white",
                positions=[{"ply": 8, "full_hash": 1302, "white_hash": 2302, "black_hash": 3302}],
            )

        results = await get_top_positions_for_color(
            db_session,
            user_id=uid,
            color="white",
            ply_min=6,
            ply_max=14,
            limit=5,
            exclude_target_hashes=set(),
        )

        white_hashes = [r[0] for r in results]
        assert 2301 not in white_hashes  # 1-game position excluded
        assert 2302 in white_hashes       # 2-game position included

    @pytest.mark.asyncio
    async def test_get_top_positions_deduplicates_by_color_hash(self, db_session: AsyncSession) -> None:
        """Multiple full_hashes sharing the same white_hash produce only one result."""
        uid = 504

        # Same white_hash=2401 but different opponent responses (different full_hash each game)
        for i in range(3):
            await _seed_game_with_positions(
                db_session,
                user_id=uid,
                user_color="white",
                positions=[{"ply": 8, "full_hash": 1400 + i, "white_hash": 2401, "black_hash": 3400 + i}],
            )

        results = await get_top_positions_for_color(
            db_session,
            user_id=uid,
            color="white",
            ply_min=6,
            ply_max=14,
            limit=5,
            exclude_target_hashes=set(),
        )

        # Should produce exactly 1 result despite 3 different full_hashes
        white_hashes = [r[0] for r in results]
        assert white_hashes.count(2401) == 1


# ---------------------------------------------------------------------------
# TestMatchSideHeuristic — AUTOBKM-04
# ---------------------------------------------------------------------------


class TestMatchSideHeuristic:
    """Verify suggest_match_side returns correct recommendation.

    New heuristic: if my_hash_count > 2 * full_hash_count, suggest 'mine'
    (opponent varies); otherwise suggest 'both' (consistent exact position).
    """

    @pytest.mark.asyncio
    async def test_suggest_match_side_both_when_consistent(self, db_session: AsyncSession) -> None:
        """Returns 'both' when the exact full position matches all games (consistent opponent play).

        3 games with same white_hash AND same full_hash:
        - my_hash_count = 3 (games matching white_hash in ply range)
        - full_hash_count = 3 (games matching full_hash in ply range)
        - my_hash_count (3) NOT > 2 * full_hash_count (6) -> suggest 'both'
        """
        uid = 600
        wh = 9001
        fh = 7777

        for _ in range(3):
            await _seed_game_with_positions(
                db_session,
                user_id=uid,
                user_color="white",
                positions=[{"ply": 8, "full_hash": fh, "white_hash": wh, "black_hash": 8001}],
            )

        result = await suggest_match_side(
            db_session,
            user_id=uid,
            color="white",
            white_hash=wh,
            black_hash=8001,
            full_hash=fh,
            ply_min=6,
            ply_max=14,
        )

        assert result == "both"

    @pytest.mark.asyncio
    async def test_suggest_match_side_mine_when_opponent_varies(self, db_session: AsyncSession) -> None:
        """Returns 'mine' when opponents vary significantly across games.

        6 games share the same white_hash but only 1 game has this specific full_hash:
        - my_hash_count = 6
        - full_hash_count = 1
        - my_hash_count (6) > 2 * full_hash_count (2) -> suggest 'mine'
        """
        uid = 601
        wh = 9002
        target_fh = 6001  # only 1 game has this exact position

        # 1 game with the specific full_hash
        await _seed_game_with_positions(
            db_session,
            user_id=uid,
            user_color="white",
            positions=[{"ply": 8, "full_hash": target_fh, "white_hash": wh, "black_hash": 8100}],
        )

        # 5 more games with same white_hash but different full_hashes (opponent varied)
        for i in range(5):
            await _seed_game_with_positions(
                db_session,
                user_id=uid,
                user_color="white",
                positions=[{"ply": 8, "full_hash": 6010 + i, "white_hash": wh, "black_hash": 8200 + i}],
            )

        result = await suggest_match_side(
            db_session,
            user_id=uid,
            color="white",
            white_hash=wh,
            black_hash=8100,
            full_hash=target_fh,
            ply_min=6,
            ply_max=14,
        )

        assert result == "mine"


# ---------------------------------------------------------------------------
# TestMatchSideUpdate — AUTOBKM-03
# ---------------------------------------------------------------------------


class TestMatchSideUpdate:
    """Verify update_match_side recomputes target_hash correctly."""

    @pytest.mark.asyncio
    async def test_update_match_side_mine_sets_white_hash(self, db_session: AsyncSession) -> None:
        """Updating match_side to 'mine' for white bookmark sets target_hash to white_hash."""
        # Use starting position FEN for a real board
        board = chess.Board()
        board.push_san("e4")
        fen = board.fen()
        wh, bh, fh = compute_hashes(board)

        bookmark = await create_bookmark(
            db_session,
            user_id=700,
            data=PositionBookmarkCreate(
                label="Test Both",
                target_hash=fh,
                fen=fen,
                moves=["e4"],
                color="white",
                match_side="both",
            ),
        )

        # Initially target_hash should be full_hash
        assert bookmark.target_hash == fh

        updated = await update_match_side(db_session, bookmark.id, 700, "mine")

        assert updated is not None
        assert updated.match_side == "mine"
        assert updated.target_hash == wh  # white player -> white_hash

    @pytest.mark.asyncio
    async def test_update_match_side_both_sets_full_hash(self, db_session: AsyncSession) -> None:
        """Updating match_side to 'both' sets target_hash to full_hash."""
        board = chess.Board()
        board.push_san("e4")
        fen = board.fen()
        wh, bh, fh = compute_hashes(board)

        bookmark = await create_bookmark(
            db_session,
            user_id=701,
            data=PositionBookmarkCreate(
                label="Test Mine",
                target_hash=wh,
                fen=fen,
                moves=["e4"],
                color="white",
                match_side="mine",
            ),
        )

        updated = await update_match_side(db_session, bookmark.id, 701, "both")

        assert updated is not None
        assert updated.match_side == "both"
        assert updated.target_hash == fh  # full_hash

    @pytest.mark.asyncio
    async def test_update_match_side_wrong_user_returns_none(self, db_session: AsyncSession) -> None:
        """update_match_side returns None when bookmark belongs to another user."""
        board = chess.Board()
        fen = board.fen()
        _, _, fh = compute_hashes(board)

        bookmark = await create_bookmark(
            db_session,
            user_id=710,
            data=PositionBookmarkCreate(
                label="Private",
                target_hash=fh,
                fen=fen,
                moves=[],
                color="white",
                match_side="both",
            ),
        )

        result = await update_match_side(db_session, bookmark.id, 720, "mine")
        assert result is None

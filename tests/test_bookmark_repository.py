"""Integration tests for position bookmark repository.

Coverage:
- TestCRUD: BKM-01 - create, list, update, delete position bookmarks
- TestReorder: BKM-02 - drag-reorder support with sort_order reassignment
- TestIsolation: BKM-05 - per-user isolation enforced at repository layer
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.position_bookmark_repository import (
    create_bookmark,
    delete_bookmark,
    get_bookmarks,
    reorder_bookmarks,
    update_bookmark,
)
from app.schemas.position_bookmarks import PositionBookmarkCreate, PositionBookmarkReorderRequest, PositionBookmarkUpdate


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_create(
    label: str = "Test Bookmark",
    target_hash: str = "1234567890",
    fen: str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    moves: list[str] | None = None,
    color: str | None = "white",
    match_side: str = "full",
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
            data=_make_create(label="Original", match_side="white"),
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
        assert updated.match_side == "white"  # unchanged

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

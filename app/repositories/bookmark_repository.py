"""Bookmark repository: async DB operations for bookmark CRUD and reorder."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bookmark import Bookmark
from app.schemas.bookmarks import BookmarkCreate, BookmarkUpdate


async def get_bookmarks(session: AsyncSession, user_id: int) -> list[Bookmark]:
    """Return all bookmarks for a user, ordered by sort_order ascending."""
    stmt = (
        select(Bookmark)
        .where(Bookmark.user_id == user_id)
        .order_by(Bookmark.sort_order.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_bookmark(
    session: AsyncSession, user_id: int, bookmark_id: int
) -> Bookmark | None:
    """Return a single bookmark owned by the given user, or None."""
    stmt = select(Bookmark).where(
        Bookmark.id == bookmark_id,
        Bookmark.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_bookmark(
    session: AsyncSession, user_id: int, data: BookmarkCreate
) -> Bookmark:
    """Create and persist a new bookmark for the given user."""
    bookmark = Bookmark(
        user_id=user_id,
        label=data.label,
        target_hash=data.target_hash,
        fen=data.fen,
        moves=json.dumps(data.moves),  # serialize list[str] to JSON string
        color=data.color,
        match_side=data.match_side,
        sort_order=0,
    )
    session.add(bookmark)
    await session.flush()
    return bookmark


async def update_bookmark(
    session: AsyncSession,
    user_id: int,
    bookmark_id: int,
    data: BookmarkUpdate,
) -> Bookmark | None:
    """Update label and/or sort_order for a bookmark owned by the given user.

    Returns None if the bookmark does not exist or belongs to a different user.
    """
    bookmark = await get_bookmark(session, user_id, bookmark_id)
    if bookmark is None:
        return None

    if data.label is not None:
        bookmark.label = data.label
    if data.sort_order is not None:
        bookmark.sort_order = data.sort_order

    await session.flush()
    return bookmark


async def delete_bookmark(
    session: AsyncSession, user_id: int, bookmark_id: int
) -> bool:
    """Delete a bookmark owned by the given user.

    Returns False if the bookmark does not exist or belongs to a different user.
    """
    bookmark = await get_bookmark(session, user_id, bookmark_id)
    if bookmark is None:
        return False

    await session.delete(bookmark)
    await session.flush()
    return True


async def reorder_bookmarks(
    session: AsyncSession, user_id: int, ordered_ids: list[int]
) -> list[Bookmark]:
    """Reassign sort_order 0..N-1 to user's bookmarks in the given order.

    Only bookmarks matching ordered_ids that belong to user_id are updated.
    Returns the reordered bookmark list.
    """
    # Fetch all matching bookmarks owned by this user
    stmt = select(Bookmark).where(
        Bookmark.id.in_(ordered_ids),
        Bookmark.user_id == user_id,
    )
    result = await session.execute(stmt)
    bookmarks_map = {b.id: b for b in result.scalars().all()}

    # Assign sort_order in the provided order
    reordered: list[Bookmark] = []
    for position, bookmark_id in enumerate(ordered_ids):
        bookmark = bookmarks_map.get(bookmark_id)
        if bookmark is not None:
            bookmark.sort_order = position
            reordered.append(bookmark)

    await session.flush()
    return reordered

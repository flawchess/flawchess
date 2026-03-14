"""Position bookmark repository: async DB operations for position bookmark CRUD and reorder.

Exposes module-level async functions. PositionBookmarkRepository is a namespace alias
for the module (for import compatibility).
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position_bookmark import PositionBookmark
from app.schemas.position_bookmarks import PositionBookmarkCreate, PositionBookmarkUpdate


async def get_bookmarks(session: AsyncSession, user_id: int) -> list[PositionBookmark]:
    """Return all position bookmarks for a user, ordered by sort_order ascending."""
    stmt = (
        select(PositionBookmark)
        .where(PositionBookmark.user_id == user_id)
        .order_by(PositionBookmark.sort_order.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_bookmark(
    session: AsyncSession, user_id: int, bookmark_id: int
) -> PositionBookmark | None:
    """Return a single position bookmark owned by the given user, or None."""
    stmt = select(PositionBookmark).where(
        PositionBookmark.id == bookmark_id,
        PositionBookmark.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_bookmark(
    session: AsyncSession, user_id: int, data: PositionBookmarkCreate
) -> PositionBookmark:
    """Create and persist a new position bookmark for the given user."""
    bookmark = PositionBookmark(
        user_id=user_id,
        label=data.label,
        target_hash=data.target_hash,
        fen=data.fen,
        moves=json.dumps(data.moves),  # serialize list[str] to JSON string
        color=data.color,
        match_side=data.match_side,
        is_flipped=data.is_flipped,
        sort_order=0,
    )
    session.add(bookmark)
    await session.flush()
    return bookmark


async def update_bookmark(
    session: AsyncSession,
    user_id: int,
    bookmark_id: int,
    data: PositionBookmarkUpdate,
) -> PositionBookmark | None:
    """Update label and/or sort_order for a position bookmark owned by the given user.

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
    """Delete a position bookmark owned by the given user.

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
) -> list[PositionBookmark]:
    """Reassign sort_order 0..N-1 to user's position bookmarks in the given order.

    Only bookmarks matching ordered_ids that belong to user_id are updated.
    Returns the reordered bookmark list.
    """
    # Fetch all matching bookmarks owned by this user
    stmt = select(PositionBookmark).where(
        PositionBookmark.id.in_(ordered_ids),
        PositionBookmark.user_id == user_id,
    )
    result = await session.execute(stmt)
    bookmarks_map = {b.id: b for b in result.scalars().all()}

    # Assign sort_order in the provided order
    reordered: list[PositionBookmark] = []
    for position, bookmark_id in enumerate(ordered_ids):
        bookmark = bookmarks_map.get(bookmark_id)
        if bookmark is not None:
            bookmark.sort_order = position
            reordered.append(bookmark)

    await session.flush()
    return reordered


# Namespace alias — allows `from ... import PositionBookmarkRepository` in plan verification
import sys as _sys
PositionBookmarkRepository = _sys.modules[__name__]

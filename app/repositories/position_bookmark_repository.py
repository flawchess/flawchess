"""Position bookmark repository: async DB operations for position bookmark CRUD and reorder.

Exposes module-level async functions. PositionBookmarkRepository is a namespace alias
for the module (for import compatibility).
"""

import json
import sys as _sys

import chess
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.position_bookmark import PositionBookmark
from app.schemas.position_bookmarks import PositionBookmarkCreate, PositionBookmarkUpdate
from app.services.zobrist import compute_hashes


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
    """Create and persist a new position bookmark for the given user.

    sort_order is set to MAX(existing sort_order) + 1 so new bookmarks always
    appear at the end of the list rather than colliding at 0.
    """
    max_stmt = select(func.coalesce(func.max(PositionBookmark.sort_order), -1) + 1).where(
        PositionBookmark.user_id == user_id
    )
    next_order = (await session.execute(max_stmt)).scalar_one()

    bookmark = PositionBookmark(
        user_id=user_id,
        label=data.label,
        target_hash=data.target_hash,
        fen=data.fen,
        moves=json.dumps(data.moves),  # serialize list[str] to JSON string
        color=data.color,
        match_side=data.match_side,
        is_flipped=data.is_flipped,
        sort_order=next_order,
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


async def delete_bookmark(session: AsyncSession, user_id: int, bookmark_id: int) -> bool:
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


async def get_existing_target_hashes(session: AsyncSession, user_id: int) -> set[int]:
    """Return the set of target_hashes for all bookmarks already saved by the user.

    target_hash is the canonical identifier for a bookmark's position — it is already
    stored as the appropriate hash (white_hash for match_side="mine" on white,
    black_hash for "mine" on black, full_hash for "both", etc.).  Reading it directly
    avoids the earlier bug where full_hash was recomputed from FEN, causing "mine"
    bookmarks to slip through the exclusion filter.
    """
    stmt = select(PositionBookmark.target_hash).where(PositionBookmark.user_id == user_id)
    result = await session.execute(stmt)
    return {row.target_hash for row in result.all()}


async def get_top_positions_for_color(
    session: AsyncSession,
    user_id: int,
    color: str,
    ply_min: int,
    ply_max: int,
    limit: int,
    exclude_target_hashes: set[int],
) -> list[tuple[int, int, int, int]]:
    """Return top positions by game count for the given user color within the ply range.

    Groups by the user's color-specific hash only (white_hash for white, black_hash for
    black) so that opponent variations are merged under a single "my pieces" key.
    This prevents duplicate suggestions that share the same target hash.

    Requires at least 2 distinct games per position (user preference).
    Post-filters to exclude positions whose color hash is already in exclude_target_hashes.

    For each surviving color hash, fetches a representative row to obtain the full
    (white_hash, black_hash, full_hash) triple needed by the suggestion endpoint.

    Returns a list of (white_hash, black_hash, full_hash, game_count) tuples,
    ordered by game_count DESC, capped at limit entries.
    """
    color_hash_col = GamePosition.white_hash if color == "white" else GamePosition.black_hash
    over_fetch_limit = limit + len(exclude_target_hashes) + 10

    stmt = (
        select(
            color_hash_col.label("color_hash"),
            func.count(GamePosition.game_id.distinct()).label("game_count"),
        )
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.ply.between(ply_min, ply_max),
            Game.user_color == color,
        )
        .group_by(color_hash_col)
        .having(func.count(GamePosition.game_id.distinct()) >= 2)
        .order_by(func.count(GamePosition.game_id.distinct()).desc())
        .limit(over_fetch_limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    # Post-filter: exclude positions whose color hash is already bookmarked
    filtered_rows = [row for row in rows if row.color_hash not in exclude_target_hashes]

    # For each surviving color hash, fetch a representative (white_hash, black_hash, full_hash)
    results: list[tuple[int, int, int, int]] = []
    for row in filtered_rows:
        if len(results) >= limit:
            break
        rep_stmt = (
            select(GamePosition.white_hash, GamePosition.black_hash, GamePosition.full_hash)
            .where(
                GamePosition.user_id == user_id,
                color_hash_col == row.color_hash,
                GamePosition.ply.between(ply_min, ply_max),
            )
            .limit(1)
        )
        rep = await session.execute(rep_stmt)
        rep_row = rep.first()
        if rep_row:
            results.append(
                (rep_row.white_hash, rep_row.black_hash, rep_row.full_hash, row.game_count)
            )

    return results


async def suggest_match_side(
    session: AsyncSession,
    user_id: int,
    color: str,
    white_hash: int,
    black_hash: int,
    full_hash: int,
    ply_min: int,
    ply_max: int,
) -> str:
    """Suggest "mine" or "both" match_side using a two-granularity game count comparison.

    Compares:
    - my_hash_count: games where the user's color-specific hash matches (captures all
      opponent variations)
    - full_hash_count: games where the exact full position matches (both sides fixed)

    If my_hash_count > 2 * full_hash_count, the opponent varies significantly across
    games, so "mine" is recommended (matching only your pieces captures more games).
    Otherwise "both" is suggested (the full position is consistent across games).

    A ply constraint is applied so the counts are scoped to the suggestion ply range,
    avoiding pollution from unrelated game phases.
    """
    color_hash_col = GamePosition.white_hash if color == "white" else GamePosition.black_hash
    color_hash_val = white_hash if color == "white" else black_hash

    # Count games where the user's pieces are in this configuration
    my_stmt = select(func.count(GamePosition.game_id.distinct())).where(
        GamePosition.user_id == user_id,
        color_hash_col == color_hash_val,
        GamePosition.ply.between(ply_min, ply_max),
    )
    my_hash_count = (await session.execute(my_stmt)).scalar_one() or 0

    # Count games where the exact full position appears
    full_stmt = select(func.count(GamePosition.game_id.distinct())).where(
        GamePosition.user_id == user_id,
        GamePosition.full_hash == full_hash,
        GamePosition.ply.between(ply_min, ply_max),
    )
    full_hash_count = (await session.execute(full_stmt)).scalar_one() or 0

    # If "my pieces only" captures more than 2x games compared to exact full match,
    # the opponent varies a lot — suggest "mine" to cover more games.
    # Otherwise the position is consistent — suggest "both".
    if my_hash_count > 2 * full_hash_count:
        return "mine"
    return "both"


async def update_match_side(
    session: AsyncSession,
    bookmark_id: int,
    user_id: int,
    new_match_side: str,
) -> PositionBookmark | None:
    """Update match_side and recompute target_hash from the bookmark's stored FEN.

    Returns None if the bookmark does not exist or belongs to a different user.
    """
    bookmark = await get_bookmark(session, user_id, bookmark_id)
    if bookmark is None:
        return None

    board = chess.Board(bookmark.fen)
    white_hash, black_hash, full_hash = compute_hashes(board)

    # Resolve target_hash based on new match_side and bookmark color
    if new_match_side == "both":
        target_hash = full_hash
    elif new_match_side == "mine":
        target_hash = white_hash if bookmark.color == "white" else black_hash
    elif new_match_side == "opponent":
        target_hash = black_hash if bookmark.color == "white" else white_hash
    else:
        target_hash = full_hash

    bookmark.match_side = new_match_side
    bookmark.target_hash = target_hash

    await session.flush()
    return bookmark


# Namespace alias — allows `from ... import PositionBookmarkRepository` in plan verification
PositionBookmarkRepository = _sys.modules[__name__]

"""User repository: profile read/write and platform username update."""

import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


async def get_profile(session: AsyncSession, user_id: int) -> User:
    """Return the User row for the given user_id.

    Args:
        session: AsyncSession to use.
        user_id: Primary key of the user.

    Returns:
        The User ORM object.
    """
    result = await session.execute(select(User).where(User.id == user_id))
    return result.unique().scalar_one()


async def get_created_at(session: AsyncSession, user_id: int) -> datetime:
    """Return the user's account-creation timestamp.

    Phase 186 Plan 02 (IMPORT-02/IMPORT-03, D-02): this is the per-user import
    backlog anchor -- the forward pass never fetches before it (Pitfall 2) and
    the backward pass's per-(platform, TC) budget query is scoped to games
    played before it. Uses ``AsyncSession.get()`` (PK lookup) rather than
    ``get_profile``'s full SELECT -- this is called once per import job and
    only needs one column.

    Args:
        session: AsyncSession to use.
        user_id: Primary key of the user.

    Raises:
        ValueError: If no user with this id exists (should not happen for an
            authenticated, already-validated import job).
    """
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")
    return user.created_at


async def update_profile(session: AsyncSession, user_id: int, data: dict) -> User:
    """Update user profile fields and return the updated User.

    Args:
        session: AsyncSession to use.
        user_id: Primary key of the user.
        data: Dict of column names to new values (only non-None values applied).

    Returns:
        The updated User ORM object.
    """
    # Filter out keys with None values — only update explicitly provided fields
    updates = {k: v for k, v in data.items() if v is not None}
    if updates:
        await session.execute(update(User).where(User.id == user_id).values(**updates))
        await session.flush()
    return await get_profile(session, user_id)


async def update_platform_username(
    session: AsyncSession,
    user_id: int,
    platform: str,
    username: str,
) -> None:
    """Auto-save platform username to the user's profile after a successful import.

    Maps platform string to the appropriate column:
      "chess.com"  -> chess_com_username
      "lichess"    -> lichess_username

    Args:
        session: AsyncSession to use.
        user_id: Primary key of the user.
        platform: Platform identifier string.
        username: The username to save.
    """
    if platform == "chess.com":
        column_values = {"chess_com_username": username}
    elif platform == "lichess":
        column_values = {"lichess_username": username}
    else:
        logger.warning("update_platform_username: unknown platform %r, skipping", platform)
        return

    await session.execute(update(User).where(User.id == user_id).values(**column_values))
    await session.flush()

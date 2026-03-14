"""User repository: profile read/write and platform username update."""

import logging

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
        await session.execute(
            update(User).where(User.id == user_id).values(**updates)
        )
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

    await session.execute(
        update(User).where(User.id == user_id).values(**column_values)
    )
    await session.flush()

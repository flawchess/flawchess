"""Feedback repository: async DB operations for feedback persistence.

Exposes module-level async functions. Never calls session.commit() —
get_async_session auto-commits on success (Pitfall 3 from RESEARCH.md).
"""

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate


async def create_feedback(session: AsyncSession, user_id: int, data: FeedbackCreate) -> Feedback:
    """Persist a new feedback row for the given user.

    user_id is taken from the authenticated user (V4 access control) —
    never from the request body. PK is populated after flush().
    """
    feedback = Feedback(
        user_id=user_id,
        page_url=data.page_url,
        text=data.text,
        rating=data.rating,
        source=data.source,
    )
    session.add(feedback)
    await session.flush()  # commit happens in get_async_session on success
    return feedback


async def has_feedback(session: AsyncSession, user_id: int) -> bool:
    """True when the user has submitted feedback from any source (served by ix_feedback_user_id)."""
    result = await session.execute(select(exists().where(Feedback.user_id == user_id)))
    return bool(result.scalar_one())

"""Feedback router: POST /api/feedback endpoint.

HTTP layer only — validation, auth, rate check, repository call, response.
All derivation/Sentry logic lives in feedback_service.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.feedback_rate_limiter import feedback_limiter
from app.models.user import User
from app.repositories import feedback_repository
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services import feedback_service
from app.users import current_active_user

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    data: FeedbackCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> FeedbackResponse:
    """Submit user feedback.

    Accepts feedback from authenticated users (full and guest, per D-08).
    Rate-limited to 5 submissions per user per hour (D-07).
    user_id is derived from the authenticated JWT — never from the request body (V4).
    """
    if not feedback_limiter.is_allowed(str(user.id)):
        raise HTTPException(
            status_code=429, detail="Too many feedback submissions. Try again later."
        )

    fb = await feedback_repository.create_feedback(session, user.id, data)
    await feedback_service.push_sentry_signal(session, user, data)
    return FeedbackResponse.model_validate(fb)

"""Users router: profile GET/PUT endpoints.

HTTP layer only — all DB access via user_repository.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.repositories import game_repository, user_repository
from app.schemas.users import UserProfileResponse, UserProfileUpdate
from app.users import current_active_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> UserProfileResponse:
    """Return the authenticated user's platform usernames and game counts."""
    profile = await user_repository.get_profile(session, user.id)
    counts = await game_repository.count_games_by_platform(session, user.id)
    return UserProfileResponse(
        email=user.email,
        chess_com_username=profile.chess_com_username,
        lichess_username=profile.lichess_username,
        created_at=profile.created_at,
        last_login=profile.last_login,
        chess_com_game_count=counts.get("chess.com", 0),
        lichess_game_count=counts.get("lichess", 0),
    )


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_profile(
    body: UserProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> UserProfileResponse:
    """Update the authenticated user's platform usernames."""
    updated = await user_repository.update_profile(session, user.id, body.model_dump())
    counts = await game_repository.count_games_by_platform(session, user.id)
    return UserProfileResponse(
        email=user.email,
        chess_com_username=updated.chess_com_username,
        lichess_username=updated.lichess_username,
        created_at=updated.created_at,
        last_login=updated.last_login,
        chess_com_game_count=counts.get("chess.com", 0),
        lichess_game_count=counts.get("lichess", 0),
    )

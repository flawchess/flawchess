"""Users router: profile GET/PUT endpoints and user account stats.

HTTP layer only — all DB access via user_repository and game_repository.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_users.jwt import decode_jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.models.user import User
from app.repositories import game_repository, user_repository
from app.schemas.admin import ImpersonationContext
from app.schemas.users import GameCountResponse, UserProfileResponse, UserProfileUpdate
from app.users import current_active_user

router = APIRouter(prefix="/users", tags=["users"])

# Matches the audience baked into JWTStrategy (FastAPI-Users default).
_JWT_AUDIENCE = ["fastapi-users:auth"]


async def _get_impersonation_context(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImpersonationContext | None:
    """Re-decode the Authorization-header JWT and return impersonation context, or None.

    D-22 Option A (RESEARCH.md §"Detecting 'am I impersonating?'"): simpler
    than threading state through the auth strategy, and the decode cost is
    negligible compared to the DB round-trips already in /me/profile.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = decode_jwt(token, settings.SECRET_KEY, _JWT_AUDIENCE)
    except Exception:
        return None
    if not payload.get("is_impersonation"):
        return None
    admin_id = payload.get("admin_id")
    act_as = payload.get("act_as")
    if admin_id is None or act_as is None:
        return None
    target = await session.get(User, int(act_as))
    if target is None:
        return None
    return ImpersonationContext(admin_id=int(admin_id), target_email=target.email)


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    impersonation: Annotated[
        ImpersonationContext | None, Depends(_get_impersonation_context)
    ],
) -> UserProfileResponse:
    """Return the authenticated user's platform usernames and game counts.

    When the request carries an impersonation JWT, `impersonation` is populated
    with the admin_id and target_email so the frontend can render the pill (D-22).
    For regular + guest tokens, `impersonation` is null.
    """
    profile = await user_repository.get_profile(session, user.id)
    counts = await game_repository.count_games_by_platform(session, user.id)
    return UserProfileResponse(
        email=user.email,
        is_superuser=user.is_superuser,
        is_guest=user.is_guest,
        chess_com_username=profile.chess_com_username,
        lichess_username=profile.lichess_username,
        created_at=profile.created_at,
        last_login=profile.last_login,
        chess_com_game_count=counts.get("chess.com", 0),
        lichess_game_count=counts.get("lichess", 0),
        impersonation=impersonation,
        beta_enabled=user.beta_enabled,
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
        is_superuser=user.is_superuser,
        is_guest=user.is_guest,
        chess_com_username=updated.chess_com_username,
        lichess_username=updated.lichess_username,
        created_at=updated.created_at,
        last_login=updated.last_login,
        chess_com_game_count=counts.get("chess.com", 0),
        lichess_game_count=counts.get("lichess", 0),
        impersonation=None,
        beta_enabled=updated.beta_enabled,
    )


@router.get("/games/count", response_model=GameCountResponse)
async def get_game_count(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> GameCountResponse:
    """Return the total number of games imported by the current user."""
    count = await game_repository.count_games_for_user(session, user.id)
    return GameCountResponse(count=count)


@router.post("/sentry-test-error", status_code=500)
async def sentry_test_error(
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    """Superuser-only: raise an unhandled error to test Sentry backend reporting."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    raise RuntimeError("[Sentry Test] Backend error")

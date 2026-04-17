"""Admin-only endpoints (superuser-gated).

Phase 62: impersonation + user search. Per CLAUDE.md, 403/404s raised by
`current_superuser` or target lookups are EXPECTED conditions — do NOT wrap
in try/except + sentry_sdk.capture_exception (would fragment Sentry issues).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.admin import ImpersonateResponse
from app.users import current_superuser, get_impersonation_jwt_strategy

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/impersonate/{user_id}", response_model=ImpersonateResponse)
async def impersonate_user(
    user_id: int,
    admin: Annotated[User, Depends(current_superuser)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImpersonateResponse:
    """Issue a 1-hour impersonation JWT for `user_id`.

    Superuser-only. Rejects impersonating another superuser (D-05) and rejects
    nested impersonation (D-04 — enforced transparently: ClaimAwareJWTStrategy
    returns the non-superuser target for impersonation tokens, so the
    `current_superuser` dep 403s nested attempts).

    on_after_login is NOT invoked (D-06 by construction — we issue the token
    manually via strategy.write_impersonation_token, not via /auth/jwt/login).
    """
    target = await session.get(User, user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.is_superuser:
        # D-05
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot impersonate another superuser",
        )

    strategy = get_impersonation_jwt_strategy()
    token = await strategy.write_impersonation_token(admin, target)
    return ImpersonateResponse(
        access_token=token,
        token_type="bearer",
        target_email=target.email,
        target_id=target.id,
    )

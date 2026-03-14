"""FastAPI-Users configuration: UserManager, auth backend, and dependencies."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from httpx_oauth.clients.google import GoogleOAuth2
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.models.oauth_account import OAuthAccount
from app.models.user import User


# ---------------------------------------------------------------------------
# Google OAuth2 client
# ---------------------------------------------------------------------------

google_oauth_client = GoogleOAuth2(
    client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
    client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
)


# ---------------------------------------------------------------------------
# User database dependency
# ---------------------------------------------------------------------------


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


# ---------------------------------------------------------------------------
# UserManager
# ---------------------------------------------------------------------------


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


# ---------------------------------------------------------------------------
# Auth backend (JWT / Bearer)
# ---------------------------------------------------------------------------

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=604800)  # 7 days


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# ---------------------------------------------------------------------------
# FastAPIUsers instance
# ---------------------------------------------------------------------------

fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

# ---------------------------------------------------------------------------
# Current user dependency — supports dev-mode auth bypass
# ---------------------------------------------------------------------------

# Original JWT-based dependency
_jwt_current_active_user = fastapi_users.current_user(active=True)


async def _dev_bypass_user(
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """In development mode, return the first active user without requiring JWT auth."""
    from sqlalchemy import select as sa_select

    result = await session.execute(
        sa_select(User).where(User.is_active == True).order_by(User.id).limit(1)  # noqa: E712
    )
    user = result.unique().scalar_one_or_none()
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="No active user found (dev mode)")
    return user


if settings.ENVIRONMENT == "development":
    current_active_user = _dev_bypass_user
else:
    current_active_user = _jwt_current_active_user

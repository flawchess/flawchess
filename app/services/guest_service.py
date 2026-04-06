"""Guest user creation and token refresh service.

Provides functions to create anonymous guest accounts and issue/refresh
their 30-day JWT tokens. Guest accounts have sentinel emails in the form
`guest_<uuid>@guest.local` and are marked with `is_guest=True`.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.users import get_guest_jwt_strategy

_GUEST_EMAIL_DOMAIN = "@guest.local"


async def create_guest_user(session: AsyncSession) -> tuple[User, str]:
    """Create an anonymous guest user and return (user, jwt_token).

    The guest account is created with:
    - A sentinel email: guest_<uuid>@guest.local
    - An empty hashed_password (guest accounts cannot log in with a password)
    - is_active=True, is_verified=True so the JWT is accepted by current_active_user
    - is_guest=True to distinguish from registered users

    Returns a (User, token) tuple where token is a 30-day Bearer JWT.
    """
    email = f"guest_{uuid4().hex}{_GUEST_EMAIL_DOMAIN}"
    user = User(
        email=email,
        hashed_password="",
        is_active=True,
        is_verified=True,
        is_superuser=False,
        is_guest=True,
    )
    session.add(user)
    await session.flush()
    await session.commit()

    token: str = await get_guest_jwt_strategy().write_token(user)
    return user, token


async def refresh_guest_token(user: User) -> str:
    """Issue a fresh 30-day JWT for a guest user.

    Raises ValueError if the user is not a guest — callers must check is_guest
    before calling this function (or catch the error for a 403 response).
    """
    if not user.is_guest:
        raise ValueError("Not a guest user")

    token: str = await get_guest_jwt_strategy().write_token(user)
    return token

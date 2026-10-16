"""Guest user creation and token refresh service.

Provides functions to create anonymous guest accounts and issue/refresh
their 30-day JWT tokens. Guest accounts have sentinel emails in the form
`guest_<uuid>@guest.local` and are marked with `is_guest=True`.
"""

import asyncio
from uuid import uuid4

from fastapi_users.exceptions import InvalidPasswordException, UserAlreadyExists
from fastapi_users.password import PasswordHelper
from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.password_policy import password_policy_violation
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.users import auth_backend, get_guest_jwt_strategy

_GUEST_EMAIL_DOMAIN = "@guest.local"

_password_helper = PasswordHelper()


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
        last_login=func.now(),
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


async def promote_guest_with_password(
    session: AsyncSession,
    user: User,
    email: str,
    password: str,
) -> tuple[User, str]:
    """Promote a guest account to a full email/password account in-place.

    Updates the user row: sets is_guest=False, is_verified=False,
    promoted_at=now(), bumps token_version (revoking the guest JWT), stores the new
    email and an argon2id-hashed password.
    Issues a standard 7-day JWT via auth_backend (not the guest 30-day
    strategy).

    Raises:
        ValueError: if the user is not a guest
        InvalidPasswordException: if the password violates the password policy
        UserAlreadyExists: if the given email is already registered by another user
    """
    if not user.is_guest:
        raise ValueError("Not a guest user")

    # This path hashes the password itself instead of going through
    # UserManager.validate_password, so it must apply the same policy explicitly.
    reason = password_policy_violation(password)
    if reason is not None:
        raise InvalidPasswordException(reason=reason)

    # Check email uniqueness before updating. Case-insensitive, matching FastAPI-Users'
    # get_by_email: an exact-match check let a guest promote to "Victim@x.com" beside
    # "victim@x.com", after which every lookup of that email found two rows and the
    # victim's login, reset and Google sign-in 500'd (security review 2026-10-14).
    result = await session.execute(select(User).where(func.lower(User.email) == email.lower()))
    if result.unique().scalar_one_or_none() is not None:
        raise UserAlreadyExists()

    # SURGE-02 (Phase 209): the measured 65.9ms argon2id hash previously ran
    # synchronously on the single event loop, freezing every other request for
    # its duration. Moving it to a worker thread lets other requests proceed
    # while this one hashes. The algorithm and cost parameters are unchanged —
    # only the thread the call runs on changes.
    hashed_password = await asyncio.to_thread(_password_helper.hash, password)

    await session.execute(
        sa_update(User)
        .where(User.id == user.id)
        .values(
            email=email,
            hashed_password=hashed_password,
            is_guest=False,
            # Promotion can now start from any persisted guest_token (quick 261016-fwd),
            # so the long-lived (365-day) guest JWT must stop authenticating the
            # now-registered account. The refresh below gives the returned JWT the new
            # version.
            token_version=User.token_version + 1,
            # Security fix (review 2026-10-14): was True, but nothing proves the
            # promoting guest owns this address. An unverified account has its
            # password replaced if Google later links to it (UserManager.google_sign_in).
            is_verified=False,
            promoted_at=func.now(),
        )
    )
    await session.commit()

    # Re-fetch the updated user so callers see current field values
    # session.get returns User | None, but we just committed the update so the user exists
    updated = await session.get(User, user.id)
    assert updated is not None, f"User {user.id} not found after promotion commit"
    # BUG FIX: promoted_at=func.now() above is a SQL expression, not a Python
    # literal, so SQLAlchemy's session-sync ("evaluate") strategy cannot mirror
    # it onto the in-session identity-mapped object — it marks promoted_at
    # expired instead. A bare attribute read would then trigger a synchronous
    # lazy load and raise MissingGreenlet under AsyncSession. Refreshing here
    # makes every field on the returned object, including promoted_at, safe
    # for callers (and tests) to read directly.
    await session.refresh(updated)

    # Issue a standard 7-day JWT (not the guest 30-day strategy)
    strategy = auth_backend.get_strategy()
    token: str = await strategy.write_token(updated)  # ty: ignore[unresolved-attribute]  # FastAPI-Users generic typing not resolved by ty beta

    return updated, token


async def promote_guest_with_google(
    session: AsyncSession,
    user: User,
    account_id: str,
    account_email: str,
    access_token: str,
    expires_at: int | None,
    refresh_token: str | None,
) -> tuple[User, str]:
    """Promote a guest account to a Google-linked full account in-place.

    Updates the user row: sets is_guest=False, is_verified=True,
    promoted_at=now(), bumps token_version (revoking the guest JWT), stores the Google email, and clears hashed_password
    (Google users authenticate via OAuth only). Inserts an OAuthAccount row
    linking the Google account to this user's ID. Issues a standard 7-day
    JWT via auth_backend.

    Raises:
        ValueError: if the user is not a guest
        UserAlreadyExists: if account_email is already registered by another user
    """
    if not user.is_guest:
        raise ValueError("Not a guest user")

    # Check email uniqueness before updating — prevent silent account merge
    # Case-insensitive for the same reason as promote_guest_with_password.
    result = await session.execute(
        select(User).where(func.lower(User.email) == account_email.lower())
    )
    existing = result.unique().scalar_one_or_none()
    if existing is not None and existing.id != user.id:
        raise UserAlreadyExists()

    await session.execute(
        sa_update(User)
        .where(User.id == user.id)
        .values(
            email=account_email,
            hashed_password="",  # Google users have no password
            is_guest=False,
            # Revoke the long-lived guest JWT, same reason as promote_guest_with_password.
            token_version=User.token_version + 1,
            is_verified=True,
            promoted_at=func.now(),
        )
    )

    # Link Google OAuthAccount to this user's row
    # Wrap in try/except IntegrityError to handle double-submit race condition:
    # if two promotion requests race, the second INSERT may violate an index;
    # treat it as idempotent since the user row is already promoted.
    oauth_account = OAuthAccount(
        oauth_name="google",
        access_token=access_token,
        expires_at=expires_at,
        refresh_token=refresh_token,
        account_id=account_id,
        account_email=account_email,
        user_id=user.id,
    )
    session.add(oauth_account)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # Row already exists from a concurrent request — promotion is idempotent

    # Re-fetch the updated user so callers see current field values
    updated = await session.get(User, user.id)
    assert updated is not None, f"User {user.id} not found after Google promotion commit"
    # BUG FIX: promoted_at=func.now() above is a SQL expression, not a Python
    # literal, so SQLAlchemy's session-sync ("evaluate") strategy cannot mirror
    # it onto the in-session identity-mapped object — it marks promoted_at
    # expired instead. A bare attribute read would then trigger a synchronous
    # lazy load and raise MissingGreenlet under AsyncSession. Refreshing here
    # makes every field on the returned object, including promoted_at, safe
    # for callers (and tests) to read directly.
    await session.refresh(updated)

    # Issue a standard 7-day JWT (not the guest 30-day strategy)
    strategy = auth_backend.get_strategy()
    token: str = await strategy.write_token(updated)  # ty: ignore[unresolved-attribute]  # FastAPI-Users generic typing not resolved by ty beta

    return updated, token

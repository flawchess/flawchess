"""Auth router: register, JWT login/logout, Google OAuth, and guest session endpoints via FastAPI-Users."""

import json
import secrets
from typing import Annotated

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi_users import schemas as fapi_schemas
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.jwt import decode_jwt, generate_jwt
from sqlalchemy import func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker, get_async_session
from app.core.ip_rate_limiter import guest_create_limiter
from app.models.user import User
from app.schemas.auth import (
    GoogleOAuthAvailableResponse,
    GoogleOAuthAuthorizeResponse,
    GuestCreateResponse,
    GuestRefreshResponse,
)
from app.services import guest_service
from app.users import UserManager, auth_backend, current_active_user, fastapi_users, get_user_manager, google_oauth_client

router = APIRouter()

# JWT login / logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Registration
router.include_router(
    fastapi_users.get_register_router(fapi_schemas.BaseUser[int], fapi_schemas.BaseUserCreate),
    prefix="/auth",
    tags=["auth"],
)

# ── Google OAuth ──────────────────────────────────────────────────────────────
# Custom implementation that redirects to the SPA after successful OAuth.
#
# Flow:
#   1. GET /auth/google/authorize → {"authorization_url": "..."}
#   2. Frontend redirects user to authorization_url
#   3. Google sends GET /auth/google/callback?code=...&state=...
#   4. Backend issues JWT, redirects to FRONTEND_URL/auth/callback#token=JWT
#   5. Frontend /auth/callback page reads fragment and stores token

_CALLBACK_ROUTE_NAME = "google-oauth-callback"
_OAUTH_STATE_AUDIENCE = "fastapi-users:oauth-state"
_CSRF_COOKIE = "flawchess_oauth_csrf"


@router.get("/auth/google/available", tags=["auth"], response_model=GoogleOAuthAvailableResponse)
async def google_oauth_available() -> GoogleOAuthAvailableResponse:
    """Return whether Google OAuth is configured on this server."""
    available = bool(
        settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
    )
    return GoogleOAuthAvailableResponse(available=available)


@router.get("/auth/google/authorize", tags=["auth"], response_model=GoogleOAuthAuthorizeResponse)
async def google_authorize(request: Request, response: Response) -> GoogleOAuthAuthorizeResponse:
    """Return the Google OAuth authorization URL for the frontend to redirect to."""
    csrf_token = secrets.token_urlsafe(32)
    state_data = {"csrftoken": csrf_token, "aud": _OAUTH_STATE_AUDIENCE}
    state = generate_jwt(
        state_data,
        settings.SECRET_KEY,
        lifetime_seconds=600,
    )

    # Set CSRF cookie — double-submit cookie pattern (CVE-2025-68481 fix)
    # The same csrf_token is embedded in the state JWT and set as a httpOnly cookie.
    # The callback endpoint reads the cookie and compares it against the state JWT claim
    # using timing-safe comparison, preventing CSRF-based account takeover.
    response.set_cookie(
        _CSRF_COOKIE,
        csrf_token,
        max_age=600,  # matches state JWT lifetime
        httponly=True,  # not readable by JS (defense in depth)
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
    )

    # Build callback URL explicitly — request.url_for() picks up the Vite proxy host (port 5173)
    # which doesn't match Google's authorized redirect URI (port 8000)
    redirect_url = f"{settings.BACKEND_URL}/api/auth/google/callback"
    authorization_url = await google_oauth_client.get_authorization_url(
        redirect_url,
        state,
        scope=["openid", "email", "profile"],
    )

    return GoogleOAuthAuthorizeResponse(authorization_url=authorization_url)


@router.get("/auth/google/callback", name=_CALLBACK_ROUTE_NAME, tags=["auth"])
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user_manager: UserManager = Depends(get_user_manager),
):
    """Handle Google OAuth callback, issue JWT, and redirect to frontend.

    Exchanges the authorization code manually using BACKEND_URL instead of
    request.url_for() — the latter builds wrong URLs behind reverse proxies
    even with X-Forwarded headers, causing redirect_uri mismatch errors.
    """
    if error is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth error: {error}")

    if code is None or state is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state")

    # Validate state JWT and extract CSRF token before calling Google's token endpoint.
    # Fail fast on bad state/CSRF without wasting an external API call.
    try:
        state_data = decode_jwt(state, settings.SECRET_KEY, [_OAUTH_STATE_AUDIENCE])
    except Exception:
        sentry_sdk.set_tag("source", "auth")
        sentry_sdk.capture_exception()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    # Validate CSRF double-submit cookie (CVE-2025-68481 fix)
    # The authorize endpoint set this cookie; the callback must confirm they match.
    cookie_csrf = request.cookies.get(_CSRF_COOKIE)
    state_csrf = state_data.get("csrftoken")
    if not cookie_csrf or not state_csrf or not secrets.compare_digest(cookie_csrf, state_csrf):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSRF token",
        )

    # Exchange code for token using the same redirect_uri as the authorize step
    redirect_url = f"{settings.BACKEND_URL}/api/auth/google/callback"
    token = await google_oauth_client.get_access_token(code, redirect_url)

    # Decode id_token from Google (avoids People API dependency).
    # The id_token is a JWT — we only need the payload, Google already validated it.
    id_token = token.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No id_token in Google response",
        )
    # Decode payload without verification (token was just received over TLS from Google)
    import base64

    payload_b64 = id_token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)  # pad base64
    id_claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    account_id = id_claims["sub"]
    account_email = id_claims.get("email")

    if account_email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email returned from Google",
        )

    try:
        user = await user_manager.oauth_callback(  # ty: ignore[invalid-argument-type]  # FastAPI-Users generic typing not resolved by ty beta
            oauth_name=google_oauth_client.name,
            access_token=token["access_token"],
            account_id=account_id,
            account_email=account_email,
            expires_at=token.get("expires_at"),
            refresh_token=token.get("refresh_token"),
            request=request,
            associate_by_email=True,
            is_verified_by_default=True,
        )
    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists with a different OAuth account",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not active",
        )

    # Update last_login — on_after_login is not called for OAuth flow
    async with async_session_maker() as session:
        await session.execute(
            sa_update(User).where(User.id == user.id).values(last_login=func.now())
        )
        await session.commit()

    strategy = auth_backend.get_strategy()
    access_token = await strategy.write_token(user)  # ty: ignore[unresolved-attribute]  # FastAPI-Users generic typing not resolved by ty beta

    # Redirect to frontend callback page with token in fragment
    frontend_redirect = f"{settings.FRONTEND_URL}/auth/callback#token={access_token}"
    return RedirectResponse(url=frontend_redirect, status_code=status.HTTP_302_FOUND)


# -- Guest session endpoints ------------------------------------------------


@router.post("/auth/guest/create", tags=["auth"], response_model=GuestCreateResponse, status_code=201)
async def create_guest(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> GuestCreateResponse:
    """Create an anonymous guest user and return a 30-day Bearer JWT."""
    client_ip = request.client.host if request.client else "unknown"
    if not guest_create_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many guest accounts created from this IP",
        )
    user, token = await guest_service.create_guest_user(session)
    return GuestCreateResponse(access_token=token, token_type="bearer", is_guest=True)


@router.post("/auth/guest/refresh", tags=["auth"], response_model=GuestRefreshResponse)
async def refresh_guest_token(
    user: Annotated[User, Depends(current_active_user)],
) -> GuestRefreshResponse:
    """Issue a fresh 30-day JWT for the authenticated guest, extending their session expiry."""
    if not user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a guest user",
        )
    token = await guest_service.refresh_guest_token(user)
    return GuestRefreshResponse(access_token=token, token_type="bearer")

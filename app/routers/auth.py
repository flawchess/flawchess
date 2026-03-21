"""Auth router: register, JWT login/logout, and Google OAuth endpoints via FastAPI-Users."""

import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi_users import schemas as fapi_schemas
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.jwt import decode_jwt, generate_jwt
from httpx_oauth.oauth2 import OAuth2Token
from sqlalchemy import func, update as sa_update

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User
from app.users import UserManager, auth_backend, fastapi_users, get_user_manager, google_oauth_client

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


@router.get("/auth/google/available", tags=["auth"])
async def google_oauth_available() -> dict:
    """Return whether Google OAuth is configured on this server."""
    available = bool(
        settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
    )
    return {"available": available}


@router.get("/auth/google/authorize", tags=["auth"])
async def google_authorize(request: Request) -> dict:
    """Return the Google OAuth authorization URL for the frontend to redirect to."""
    csrf_token = secrets.token_urlsafe(32)
    state_data = {"csrftoken": csrf_token, "aud": _OAUTH_STATE_AUDIENCE}
    state = generate_jwt(
        state_data,
        settings.SECRET_KEY,
        lifetime_seconds=600,
    )

    # Build callback URL explicitly — request.url_for() picks up the Vite proxy host (port 5173)
    # which doesn't match Google's authorized redirect URI (port 8000)
    redirect_url = f"{settings.BACKEND_URL}/auth/google/callback"
    authorization_url = await google_oauth_client.get_authorization_url(
        redirect_url,
        state,
        scope=["openid", "email", "profile"],
    )

    response = {"authorization_url": authorization_url}
    return response


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

    # Exchange code for token using the same redirect_uri as the authorize step
    redirect_url = f"{settings.BACKEND_URL}/auth/google/callback"
    token = await google_oauth_client.get_access_token(code, redirect_url)

    if state is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state")

    # Validate state JWT
    try:
        decode_jwt(state, settings.SECRET_KEY, [_OAUTH_STATE_AUDIENCE])
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

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
        user = await user_manager.oauth_callback(
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
    access_token = await strategy.write_token(user)

    # Redirect to frontend callback page with token in fragment
    frontend_redirect = f"{settings.FRONTEND_URL}/auth/callback#token={access_token}"
    return RedirectResponse(url=frontend_redirect, status_code=status.HTTP_302_FOUND)

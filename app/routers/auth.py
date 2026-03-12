"""Auth router: register, JWT login/logout, and Google OAuth endpoints via FastAPI-Users."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi_users import schemas as fapi_schemas
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users.jwt import decode_jwt, generate_jwt
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallback
from httpx_oauth.oauth2 import OAuth2Token

from app.core.config import settings
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
_CSRF_COOKIE = "chessalytics_oauth_csrf"

oauth2_callback_dep = OAuth2AuthorizeCallback(
    google_oauth_client,
    route_name=_CALLBACK_ROUTE_NAME,
)


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
    state_data = {"csrftoken": csrf_token}
    state = generate_jwt(
        state_data,
        _STATE_SECRET := settings.SECRET_KEY,
        lifetime_seconds=600,
        audience=_OAUTH_STATE_AUDIENCE,
    )

    redirect_url = str(request.url_for(_CALLBACK_ROUTE_NAME))
    authorization_url = await google_oauth_client.get_authorization_url(
        redirect_url,
        state,
        scopes=["openid", "email", "profile"],
    )

    response = {"authorization_url": authorization_url}
    return response


@router.get("/auth/google/callback", name=_CALLBACK_ROUTE_NAME, tags=["auth"])
async def google_callback(
    request: Request,
    access_token_state: tuple[OAuth2Token, str] = Depends(oauth2_callback_dep),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Handle Google OAuth callback, issue JWT, and redirect to frontend."""
    token, state = access_token_state

    if state is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing state")

    # Validate state JWT
    try:
        decode_jwt(state, settings.SECRET_KEY, [_OAUTH_STATE_AUDIENCE])
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    account_id, account_email = await google_oauth_client.get_id_email(token["access_token"])

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

    strategy = auth_backend.get_strategy()
    access_token = await strategy.write_token(user)

    # Redirect to frontend callback page with token in fragment
    frontend_redirect = f"{settings.FRONTEND_URL}/auth/callback#token={access_token}"
    return RedirectResponse(url=frontend_redirect, status_code=status.HTTP_302_FOUND)

"""Middleware to track last_activity on authenticated requests.

Updates the users.last_activity column at most once per hour per user.
Uses an in-memory cache to avoid any DB hit during the throttle window,
and a single conditional UPDATE (no SELECT) when the window expires.

Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) to avoid
a deadlock: BaseHTTPMiddleware.call_next returns before DI cleanup commits
the route handler's session, so if both the handler and middleware UPDATE
the same User row, the middleware blocks on a row lock that never releases.
With a pure ASGI middleware, self.app() only returns after the full response
is sent and DI cleanup has completed, so the row lock is already released.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi_users.jwt import decode_jwt
from sqlalchemy import update as sa_update
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User

logger = logging.getLogger(__name__)

_ACTIVITY_THROTTLE = timedelta(hours=1)
_JWT_AUDIENCE = ["fastapi-users:auth"]

# In-memory throttle cache: user_id → last update time.
# Safe for single-instance deployments (FlawChess runs one backend).
_last_updated: dict[int, datetime] = {}


class LastActivityMiddleware:
    """Update User.last_activity on authenticated requests, throttled to once per hour."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract user_id from JWT before processing the request.
        request = Request(scope)
        user_id = _extract_user_id(request)

        # Capture the response status code from the response-start message.
        status_code: int | None = None

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status")
            await send(message)

        # Process the request. This only returns after the full response
        # (including body) is sent and DI dependency cleanup has completed.
        await self.app(scope, receive, send_wrapper)  # ty: ignore[invalid-argument-type] — send_wrapper matches the ASGI Send protocol

        # Now safe to UPDATE the same User row — the route handler's
        # transaction has already committed and released its row lock.
        if status_code is None or status_code >= 400 or user_id is None:
            return

        try:
            now = datetime.now(timezone.utc)
            last = _last_updated.get(user_id)
            if last is not None and (now - last) < _ACTIVITY_THROTTLE:
                return

            # Single UPDATE, no SELECT — the DB does the work
            async with async_session_maker() as session:
                await session.execute(
                    sa_update(User)
                    .where(User.id == user_id)
                    .values(last_activity=now)
                )
                await session.commit()
            _last_updated[user_id] = now
        except Exception:
            # Never let activity tracking break a request
            logger.debug("Failed to update last_activity for user %s", user_id, exc_info=True)


def _extract_user_id(request: Request) -> int | None:
    """Decode JWT from Authorization header and return user_id, or None."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = decode_jwt(token, settings.SECRET_KEY, _JWT_AUDIENCE)
        user_id_raw = payload.get("sub")
        if user_id_raw is not None:
            return int(user_id_raw)
    except Exception:
        pass
    return None

"""Middleware to track last_activity on authenticated requests.

Updates the users.last_activity column at most once per hour per user.
Uses an in-memory cache to avoid any DB hit during the throttle window,
and a single conditional UPDATE (no SELECT) when the window expires.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi_users.jwt import decode_jwt
from sqlalchemy import update as sa_update
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User

logger = logging.getLogger(__name__)

_ACTIVITY_THROTTLE = timedelta(hours=1)
_JWT_AUDIENCE = ["fastapi-users:auth"]

# In-memory throttle cache: user_id → last update time.
# Safe for single-instance deployments (FlawChess runs one backend).
_last_updated: dict[int, datetime] = {}


class LastActivityMiddleware(BaseHTTPMiddleware):
    """Update User.last_activity on authenticated requests, throttled to once per hour."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if response.status_code >= 400:
            return response

        user_id = _extract_user_id(request)
        if user_id is None:
            return response

        try:
            now = datetime.now(timezone.utc)
            last = _last_updated.get(user_id)
            if last is not None and (now - last) < _ACTIVITY_THROTTLE:
                return response

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

        return response


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

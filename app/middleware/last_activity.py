"""Middleware to track last_activity on authenticated requests.

Updates the users.last_activity column at most once per hour to avoid
excessive DB writes on every API call.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi_users.jwt import decode_jwt
from sqlalchemy import select
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


class LastActivityMiddleware(BaseHTTPMiddleware):
    """Update User.last_activity on authenticated requests, throttled to once per hour."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Only track activity on successful responses
        if response.status_code >= 400:
            return response

        # Extract user_id from Bearer JWT (lightweight — no DB user fetch)
        user_id = self._extract_user_id(request)
        if user_id is None:
            return response

        # Update last_activity with throttle
        try:
            await self._maybe_update_activity(user_id)
        except Exception:
            # Never let activity tracking break a request
            logger.debug("Failed to update last_activity for user %s", user_id, exc_info=True)

        return response

    @staticmethod
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

    @staticmethod
    async def _maybe_update_activity(user_id: int) -> None:
        """Update last_activity if NULL or older than _ACTIVITY_THROTTLE."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User.last_activity).where(User.id == user_id)
            )
            last_activity = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if last_activity is None or (now - last_activity) > _ACTIVITY_THROTTLE:
                await session.execute(
                    sa_update(User).where(User.id == user_id).values(last_activity=now)
                )
                await session.commit()

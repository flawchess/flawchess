---
phase: quick
plan: 260412-fis
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/user.py
  - app/users.py
  - app/services/guest_service.py
  - app/middleware/__init__.py
  - app/middleware/last_activity.py
  - app/main.py
  - alembic/versions/YYYYMMDD_HHMMSS_backfill_last_login_add_last_activity.py
  - tests/test_last_activity_middleware.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "All user creation paths set last_login to current timestamp (never NULL for new users)"
    - "Existing users with NULL last_login get backfilled to created_at via migration"
    - "last_activity column exists and is updated on authenticated requests, throttled to 1h"
  artifacts:
    - path: "app/models/user.py"
      provides: "last_activity column on User model"
      contains: "last_activity"
    - path: "app/middleware/last_activity.py"
      provides: "Middleware that updates last_activity throttled to 1 hour"
    - path: "alembic/versions/"
      provides: "Migration backfilling last_login and adding last_activity"
  key_links:
    - from: "app/middleware/last_activity.py"
      to: "app/main.py"
      via: "app.add_middleware or @app.middleware"
    - from: "app/services/guest_service.py"
      to: "app/models/user.py"
      via: "last_login=func.now() on User creation"
---

<objective>
Implement last_login defaults across all user creation paths, backfill existing NULL values, and add last_activity tracking with throttled middleware.

Purpose: Ensure last_login is never NULL for any user (new or existing) and track user activity for analytics/admin purposes.
Output: Updated User model, migration, middleware, and tests.
</objective>

<context>
@CLAUDE.md
@app/models/user.py
@app/users.py
@app/services/guest_service.py
@app/routers/auth.py
@app/main.py
@tests/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Set last_login at creation in all paths and add on_after_register hook</name>
  <files>app/services/guest_service.py, app/users.py</files>
  <action>
1. In `app/services/guest_service.py`, add `from sqlalchemy import func` and set `last_login=func.now()` in the User constructor at line 38-45 (inside `create_guest_user`).

2. In `app/users.py`, add an `on_after_register` hook to `UserManager` that sets `last_login = func.now()` for newly registered email users. This covers the FastAPI-Users register endpoint (POST /auth/register). Pattern:

```python
async def on_after_register(
    self,
    user: User,
    request: Request | None = None,
) -> None:
    """Set last_login on email registration so it's never NULL."""
    async with async_session_maker() as session:
        await session.execute(
            sa_update(User).where(User.id == user.id).values(last_login=func.now())
        )
        await session.commit()
```

Note: Google OAuth already sets last_login in `auth.py:200-205`. Guest promotion sets it at `auth.py:397-401`. Both are already handled. The two gaps are: (a) guest creation, (b) email registration.
  </action>
  <verify>uv run ruff check app/services/guest_service.py app/users.py && uv run ty check app/ tests/</verify>
  <done>Guest creation and email registration both set last_login at account creation time. No new user can have NULL last_login.</done>
</task>

<task type="auto">
  <name>Task 2: Migration to backfill last_login and add last_activity column</name>
  <files>app/models/user.py, alembic/versions/ (new migration file)</files>
  <action>
1. Update `app/models/user.py` — add `last_activity` column:

```python
last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Place it right after the `last_login` line. No server_default needed — new users will have NULL until their first authenticated request.

2. Generate the Alembic migration: `uv run alembic revision --autogenerate -m "backfill last_login add last_activity"`. This will auto-detect the new `last_activity` column.

3. Edit the generated migration to also include the backfill step. In the `upgrade()` function, BEFORE the `add_column` operation, add:

```python
# Backfill existing users: set last_login = created_at where NULL
op.execute(
    "UPDATE users SET last_login = created_at WHERE last_login IS NULL"
)
```

The `downgrade()` should drop the `last_activity` column. Do NOT undo the backfill in downgrade — that data correction is intentionally permanent.

4. Run the migration locally: `uv run alembic upgrade head`
  </action>
  <verify>uv run alembic upgrade head && uv run ty check app/ tests/</verify>
  <done>Migration runs cleanly. last_activity column exists on users table. All existing NULL last_login values are backfilled to created_at.</done>
</task>

<task type="auto">
  <name>Task 3: Add last_activity middleware with 1-hour throttle and tests</name>
  <files>app/middleware/__init__.py, app/middleware/last_activity.py, app/main.py, tests/test_last_activity_middleware.py, tests/conftest.py</files>
  <action>
1. Create `app/middleware/__init__.py` (empty file).

2. Create `app/middleware/last_activity.py` with a Starlette `BaseHTTPMiddleware` subclass:

```python
"""Middleware to track last_activity on authenticated requests.

Updates the users.last_activity column at most once per hour to avoid
excessive DB writes on every API call.
"""

from datetime import datetime, timedelta, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import update as sa_update

from app.core.database import async_session_maker
from app.models.user import User
from app.users import current_active_user

_ACTIVITY_THROTTLE = timedelta(hours=1)
```

The middleware should:
- Call `next(request)` first (response-after pattern — don't block the request).
- After the response, try to resolve `current_active_user` from the request's state. Since FastAPI-Users injects the user via Depends, the middleware can't directly access it. Instead, use a **lighter approach**: create a simple FastAPI dependency-free check:
  - Read the `Authorization` header. If missing, skip.
  - Decode the JWT using `fastapi_users_jwt.decode_jwt` with the app secret to get the user_id (`sub` field).
  - Query the user's `last_activity` from DB. If NULL or older than 1 hour, update it.

Actually, the simplest correct approach: use a **post-response background task** pattern. But the cleanest FastAPI-compatible approach is to add a lightweight dependency or hook. 

**Recommended approach — use `@app.middleware("http")` in main.py directly:**

In `app/middleware/last_activity.py`, create an async function:

```python
from datetime import datetime, timedelta, timezone
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from sqlalchemy import select, update as sa_update
from app.core.database import async_session_maker
from app.models.user import User

_ACTIVITY_THROTTLE = timedelta(hours=1)

class LastActivityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Only process successful authenticated requests
        if response.status_code >= 400:
            return response
        
        # Check if the request handler stored a user_id in request.state
        user_id: int | None = getattr(request.state, "_authenticated_user_id", None)
        if user_id is None:
            return response
        
        # Update last_activity, throttled to 1 hour
        try:
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
        except Exception:
            pass  # Never let activity tracking break a request
        
        return response
```

Then, to populate `request.state._authenticated_user_id`, create a lightweight FastAPI dependency in `app/middleware/last_activity.py`:

```python
from fastapi import Depends, Request
from app.users import current_active_user
from app.models.user import User

async def track_activity(request: Request, user: User = Depends(current_active_user)) -> None:
    """Dependency that tags the request with the authenticated user's ID for activity tracking."""
    request.state._authenticated_user_id = user.id
```

**Wait — this won't work because the dependency would need to be added to every route.**

**Better approach: decode JWT directly in middleware.** This avoids coupling to FastAPI's DI:

```python
import logging
from datetime import datetime, timedelta, timezone
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from fastapi_users.jwt import decode_jwt
from sqlalchemy import select, update as sa_update

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User

logger = logging.getLogger(__name__)

_ACTIVITY_THROTTLE = timedelta(hours=1)
_JWT_AUDIENCE = "fastapi-users:auth"

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
            payload = decode_jwt(token, settings.SECRET_KEY, [_JWT_AUDIENCE])
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
```

3. In `app/main.py`, add the middleware after CORS middleware:

```python
from app.middleware.last_activity import LastActivityMiddleware
# Add after the CORS middleware block
app.add_middleware(LastActivityMiddleware)
```

4. Also patch `async_session_maker` in `tests/conftest.py` for the middleware module. In the `override_get_async_session` fixture, add:

```python
import app.middleware.last_activity as activity_module
original_activity_session_maker = activity_module.async_session_maker
activity_module.async_session_maker = test_session_maker
# ... and restore in teardown
activity_module.async_session_maker = original_activity_session_maker
```

5. Create `tests/test_last_activity_middleware.py`:

Test `_extract_user_id` with valid JWT, invalid JWT, and missing header.
Test the throttle logic: create a user, make an authenticated request, verify last_activity is set. Make another request immediately, verify last_activity hasn't changed (throttle). Manually backdate last_activity by >1h, make another request, verify it updated.

Use `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` pattern from existing tests. Use the `/api/health` endpoint for unauthenticated baseline. For authenticated, register a user, login, and hit any authenticated endpoint.

Focus test on the middleware's `_extract_user_id` static method (unit test) and an integration test that verifies the full flow.
  </action>
  <verify>uv run pytest tests/test_last_activity_middleware.py -x && uv run ruff check app/middleware/ && uv run ty check app/ tests/</verify>
  <done>LastActivityMiddleware is registered in app, decodes JWT to get user_id, updates last_activity throttled to 1 hour. Tests pass for extract logic and throttle behavior.</done>
</task>

</tasks>

<verification>
1. `uv run ruff check .` — no lint errors
2. `uv run ty check app/ tests/` — zero type errors
3. `uv run alembic upgrade head` — migration runs cleanly
4. `uv run pytest -x` — all tests pass (existing + new)
5. Manual check: register a new user via API, confirm last_login is non-NULL; make an authenticated request, confirm last_activity is set
</verification>

<success_criteria>
- No user creation path leaves last_login as NULL
- Existing users with NULL last_login are backfilled to created_at
- last_activity column exists and is populated on authenticated API requests
- Activity writes are throttled to at most once per hour per user
- All linting, type checking, and tests pass
</success_criteria>

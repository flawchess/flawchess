# Phase 62: Admin user impersonation - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 18 new + 8 modified
**Analogs found:** 24 / 26

---

## File Classification

### Backend

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/routers/admin.py` (NEW) | router | request-response | `app/routers/users.py` + `app/routers/auth.py` (guest endpoints) | exact |
| `app/services/admin_service.py` (NEW) | service | CRUD (user search) | `app/services/guest_service.py` + `app/repositories/user_repository.py` | role-match |
| `app/schemas/admin.py` (NEW) | schema (Pydantic v2) | request-response | `app/schemas/auth.py` + `app/schemas/users.py` | exact |
| `app/users.py` (MODIFY) | auth config | request-response | `app/users.py` (self, existing `get_guest_jwt_strategy` pattern) | exact |
| `app/main.py` (MODIFY) | app bootstrap | config | `app/main.py` (self, lines 71-77) | exact |
| `app/middleware/last_activity.py` (MODIFY) | middleware | event-driven (ASGI) | `app/middleware/last_activity.py` (self, `_extract_user_id`) | exact |
| `app/schemas/users.py` (MODIFY) | schema | request-response | `app/schemas/users.py` (self) | exact |
| `app/routers/users.py` (MODIFY) | router | request-response | `app/routers/users.py` (self, `/me/profile`) | exact |
| `tests/test_admin_router.py` (NEW) | test (integration) | request-response | `tests/test_users_router.py` + `tests/test_auth.py` | exact |
| `tests/test_impersonation_strategy.py` (NEW) | test (unit) | pure function | `tests/test_last_activity_middleware.py::TestExtractUserId` | role-match |
| `tests/test_last_activity_middleware.py` (MODIFY) | test | ASGI middleware | `tests/test_last_activity_middleware.py` (self) | exact |
| `tests/test_users_router.py` (MODIFY) | test | request-response | `tests/test_users_router.py` (self) | exact |

### Frontend

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/pages/Admin.tsx` (NEW) | page | composition | `frontend/src/pages/GlobalStats.tsx` (layout) | partial |
| `frontend/src/components/admin/ImpersonationSelector.tsx` (NEW) | component (combobox) | event-driven + CRUD search | `frontend/src/components/ui/info-popover.tsx` (Popover), `frontend/src/pages/GlobalStats.tsx:95-100` (useQuery with filter params) | partial — no cmdk analog exists |
| `frontend/src/components/admin/ImpersonationPill.tsx` (NEW) | component (display) | pure | `frontend/src/App.tsx:122-131` (Guest badge block) | exact |
| `frontend/src/components/admin/SentryTestButtons.tsx` (NEW) | component | event-driven | `frontend/src/pages/GlobalStats.tsx:20-78` (verbatim extract) | exact |
| `frontend/src/components/ui/command.tsx` (NEW, shadcn) | ui primitive | — | none (new dep `cmdk`) | no analog |
| `frontend/src/components/ui/popover.tsx` (NEW, shadcn) | ui primitive | — | `frontend/src/components/ui/info-popover.tsx` (uses `radix-ui/Popover` directly) | partial |
| `frontend/src/types/admin.ts` (NEW) | type definitions | — | `frontend/src/types/users.ts` | exact |
| `frontend/src/hooks/useAuth.ts` (MODIFY) | hook (provider) | state | `frontend/src/hooks/useAuth.ts` (self, `login` method lines 40-64) | exact |
| `frontend/src/types/users.ts` (MODIFY) | type definitions | — | self | exact |
| `frontend/src/App.tsx` (MODIFY) | app shell | routing + nav | `frontend/src/App.tsx` (self) | exact |
| `frontend/src/pages/GlobalStats.tsx` (MODIFY) | page | removal | self (lines 18-85) | exact |
| `frontend/src/__tests__/.../ImpersonationSelector.test.tsx` (NEW) | test (component) | pure-function smoke | `frontend/src/lib/utils.test.ts` only — no component render test exists | **no analog — see gotcha** |
| `frontend/src/__tests__/.../ImpersonationPill.test.tsx` (NEW) | test (component) | pure-function smoke | (same as above) | **no analog — see gotcha** |

---

## Pattern Assignments

### Backend

#### `app/routers/admin.py` (NEW — router, request-response)

**Primary analog:** `app/routers/users.py` (for the prefix + `current_active_user` pattern) + `app/routers/auth.py:236-245` (for custom-issued-JWT response shape).

**Imports + router declaration** — copy from `app/routers/users.py:1-17`:

```python
# app/routers/users.py:1-17
"""Users router: profile GET/PUT endpoints and user account stats.

HTTP layer only — all DB access via user_repository and game_repository.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.repositories import game_repository, user_repository
from app.schemas.users import GameCountResponse, UserProfileResponse, UserProfileUpdate
from app.users import current_active_user

router = APIRouter(prefix="/users", tags=["users"])
```

New file uses `APIRouter(prefix="/admin", tags=["admin"])`. Per CLAUDE.md, routes use relative paths — never embed `/admin` in individual decorators.

**Endpoint handler (superuser-gated)** — `app/routers/users.py:73-80` shows the existing inline-check pattern for Sentry test:

```python
# app/routers/users.py:73-80
@router.post("/sentry-test-error", status_code=500)
async def sentry_test_error(
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    """Superuser-only: raise an unhandled error to test Sentry backend reporting."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    raise RuntimeError("[Sentry Test] Backend error")
```

**Follow-up for planner:** RESEARCH.md §"Admin router + superuser dependency" recommends using `fastapi_users.current_user(active=True, superuser=True)` as a dedicated dep instead of the inline check. Define once in `app/users.py`, use on every `/admin/*` route.

**Custom token-issuance response shape** — copy from `app/routers/auth.py:218-231`:

```python
# app/routers/auth.py:218-231
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
```

Apply the same `access_token` + `token_type="bearer"` response shape for `POST /admin/impersonate/{user_id}`.

**Error handling (HTTPException with status codes)** — `app/routers/auth.py:308-344` shows the 400/403/404 `HTTPException` + `sentry_sdk.set_tag()` + `capture_exception()` pattern. Per CLAUDE.md, **expected 403s (non-superuser hitting `/admin/*`) must NOT call `capture_exception`** — FastAPI-Users' `current_user(superuser=True)` dep raises its own HTTPException which is an expected condition.

---

#### `app/services/admin_service.py` (NEW — service, CRUD user search)

**Primary analog:** `app/services/guest_service.py` for the "issue a manual token bypassing `on_after_login`" pattern; `app/repositories/user_repository.py` for the `select()` + `session.execute` SQLAlchemy 2.x pattern.

**Manual token issuance pattern (bypasses `on_after_login` — satisfies D-06)** — copy from `app/services/guest_service.py:26-52`:

```python
# app/services/guest_service.py:26-52
async def create_guest_user(session: AsyncSession) -> tuple[User, str]:
    """Create an anonymous guest user and return (user, jwt_token).
    ...
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
```

**Key insight for D-06:** FastAPI-Users only calls `on_after_login` from its built-in auth router. Any custom endpoint issuing tokens via `strategy.write_token(...)` — like this `create_guest_user` — skips it. The impersonation endpoint should use the same `strategy.write_impersonation_token(admin, target)` pattern (see RESEARCH.md §"Recommended subclass shape").

**SQLAlchemy 2.x select + ILIKE search query** — derive from `app/services/guest_service.py:87-91` and `app/repositories/user_repository.py:22-24`:

```python
# app/services/guest_service.py:87-91 — ILIKE / uniqueness pattern
result = await session.execute(
    select(User).where(User.email == email)  # ty: ignore[invalid-argument-type]  # SQLAlchemy column comparisons return ColumnElement, not bool
)
if result.unique().scalar_one_or_none() is not None:
    raise UserAlreadyExists()
```

```python
# app/repositories/user_repository.py:13-24 — basic select + scalar_one
async def get_profile(session: AsyncSession, user_id: int) -> User:
    """Return the User row for the given user_id. ..."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.unique().scalar_one()
```

**Gotcha:** the `# ty: ignore[invalid-argument-type]` with comment "SQLAlchemy column comparisons return ColumnElement, not bool" is a mandatory pattern when `ty` stumbles on column equality. Apply the same suppression to the search service's `or_(...)` expression. Open Question #4 in RESEARCH.md flags `User.id == int(q) if q.isdigit() else False` — use `sa.false()` or build the clause conditionally rather than relying on the Python short-circuit.

**Search with limit + ordering** — no exact analog in repositories; closest is the ordering+limit pattern. Use `.order_by(User.last_login.desc().nullslast(), User.id.asc()).limit(USER_SEARCH_LIMIT)`. Define `USER_SEARCH_LIMIT = 20` as a module constant (CLAUDE.md no-magic-numbers rule).

---

#### `app/schemas/admin.py` (NEW — Pydantic v2 schemas)

**Primary analog:** `app/schemas/auth.py` (for `access_token` response) + `app/schemas/users.py` (for user-fields response).

**Imports + BaseModel style** — copy from `app/schemas/auth.py:1-16`:

```python
# app/schemas/auth.py:1-23
"""Pydantic v2 schemas for auth API endpoints."""

from pydantic import BaseModel, EmailStr


class GoogleOAuthAvailableResponse(BaseModel):
    """Response for GET /auth/google/available."""

    available: bool


class GuestCreateResponse(BaseModel):
    """Response for POST /auth/guest/create."""

    access_token: str
    token_type: str
    is_guest: bool
```

Apply the same pattern for `ImpersonateResponse`, `UserSearchResult`, `ImpersonationContext`.

**Field-type style (optional + datetime)** — from `app/schemas/users.py:8-19`:

```python
# app/schemas/users.py:8-19
class UserProfileResponse(BaseModel):
    """Response for GET/PUT /users/me/profile."""

    email: str
    is_superuser: bool
    is_guest: bool
    chess_com_username: str | None
    lichess_username: str | None
    created_at: datetime
    last_login: datetime | None
    chess_com_game_count: int
    lichess_game_count: int
```

**Per CLAUDE.md:** use `Literal["..."]` for fields with fixed values. Here `token_type: Literal["bearer"]` is optional but technically more correct than bare `str`.

---

#### `app/users.py` (MODIFY — add `ImpersonationJWTStrategy`, `ClaimAwareJWTStrategy`, `current_superuser`)

**Primary analog:** self — the existing `get_guest_jwt_strategy` at lines 88-96 is a direct pattern for variant-lifetime JWT strategies.

**Strategy factory with custom lifetime** — copy from `app/users.py:88-96`:

```python
# app/users.py:85-103
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=604800)  # 7 days


_GUEST_JWT_LIFETIME_SECONDS = 31536000  # 365 days


def get_guest_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=_GUEST_JWT_LIFETIME_SECONDS)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
```

Add `_IMPERSONATION_JWT_LIFETIME_SECONDS = 3600` (1 hour per D-03) and `get_impersonation_jwt_strategy()` returning `ImpersonationJWTStrategy(...)`. Wire `auth_backend`'s `get_strategy` to the new `ClaimAwareJWTStrategy` wrapper (RESEARCH.md §"Dispatching: one backend, claim-aware strategy").

**Superuser dependency pattern (new)** — per RESEARCH.md §"Superuser dependency (reusable)":

```python
# app/users.py (new addition, mirrors line 115)
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)  # NEW
```

---

#### `app/main.py` (MODIFY — include admin router)

**Analog:** self, lines 71-77:

```python
# app/main.py:69-77
app.add_middleware(LastActivityMiddleware)

app.include_router(auth.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(openings.router, prefix="/api")
app.include_router(position_bookmarks.router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(endgames_router, prefix="/api")
app.include_router(users_router, prefix="/api")
```

Add import `from app.routers.admin import router as admin_router` and `app.include_router(admin_router, prefix="/api")`.

---

#### `app/middleware/last_activity.py` (MODIFY — skip writes when `is_impersonation=true`)

**Analog:** self — the existing `_extract_user_id` at lines 91-104 is the exact function to extend. This is a **CRITICAL** change per RESEARCH.md §"CRITICAL STALE CLAIM" — CONTEXT.md D-08 is stale, D-07 must be implemented in this phase.

**Current function to extend** — `app/middleware/last_activity.py:91-104`:

```python
# app/middleware/last_activity.py:91-104
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
```

**Extension pattern:** return a tuple `(int | None, bool)` where the second element is `is_impersonation`. Short-circuit in `__call__` around line 68 before the throttle check:

```python
# app/middleware/last_activity.py:44-69 — callsite to modify
user_id = _extract_user_id(request)  # existing line 51 — change to unpack tuple

# ... existing status_code capture ...
await self.app(scope, receive, send_wrapper)

# D-07: skip last_activity writes when the request is authenticated via an
# impersonation token. Without this, an admin's impersonation session would
# silently bump the target user's activity counter.
if status_code is None or status_code >= 400 or user_id is None:
    return
```

---

#### `app/schemas/users.py` (MODIFY — add `impersonation` field to profile response)

**Analog:** self — extend `UserProfileResponse` with an optional `ImpersonationContext` nested model.

```python
# app/schemas/users.py — new additions following existing style
class ImpersonationContext(BaseModel):
    """Populated on /users/me/profile when the request carries an impersonation token."""

    admin_id: int
    target_email: str


class UserProfileResponse(BaseModel):
    # ... existing fields ...
    impersonation: ImpersonationContext | None = None
```

---

#### `app/routers/users.py` (MODIFY — populate `impersonation` on profile response)

**Analog:** self — `/me/profile` handler at lines 20-38 already demonstrates the constructor-style response composition.

**Pattern to follow** (lines 20-38):

```python
# app/routers/users.py:20-38
@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> UserProfileResponse:
    """Return the authenticated user's platform usernames and game counts."""
    profile = await user_repository.get_profile(session, user.id)
    counts = await game_repository.count_games_by_platform(session, user.id)
    return UserProfileResponse(
        email=user.email,
        is_superuser=user.is_superuser,
        is_guest=user.is_guest,
        chess_com_username=profile.chess_com_username,
        lichess_username=profile.lichess_username,
        created_at=profile.created_at,
        last_login=profile.last_login,
        chess_com_game_count=counts.get("chess.com", 0),
        lichess_game_count=counts.get("lichess", 0),
    )
```

**New addition:** inject `Request` and add a small helper dep `get_impersonation_context(request: Request) -> ImpersonationContext | None` that re-decodes the raw Authorization header (same pattern as `app/middleware/last_activity.py:_extract_user_id`), then pass `impersonation=context` to the response constructor (RESEARCH.md Open Question #1, Option A). The `target_email` comes from `user.email` (since `current_active_user` returns the *target* for impersonation tokens).

---

### Backend Tests

#### `tests/test_admin_router.py` (NEW — integration tests)

**Primary analog:** `tests/test_users_router.py` (whole-file pattern) + `tests/test_auth.py` (register/login helpers).

**Module structure — registration helpers + module-scoped auth fixture** — copy from `tests/test_users_router.py:1-53`:

```python
# tests/test_users_router.py:1-53
"""Integration tests for GET/PUT /users/me/profile endpoints.

Uses httpx.AsyncClient with ASGITransport to test the FastAPI app directly.
Each test class uses a module-scoped user so registration only happens once per module.
"""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app


def unique_email(prefix: str = "user") -> str:
    """Generate a unique email address for each test run."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def _register_and_login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Register a user and return their JWT access token."""
    await client.post("/api/auth/register", json={"email": email, "password": password})
    login_resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    return login_resp.json()["access_token"]


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers."""
    email = unique_email("profile")
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        token = await _register_and_login(client, email, password)

    return {"Authorization": f"Bearer {token}"}
```

**Extension for admin tests:** extend the helpers to:
1. Create a superuser (flip `is_superuser=True` directly in DB, or use the `seed_fixtures` module at `tests/seed_fixtures.py`).
2. Create a target non-superuser.
3. Call `POST /api/admin/impersonate/{target.id}` with superuser token to get impersonation token.

---

#### `tests/test_impersonation_strategy.py` (NEW — unit tests for claim-aware strategy)

**Primary analog:** `tests/test_last_activity_middleware.py::TestExtractUserId` (lines 50-101) — both test a function that decodes JWTs independently of the full app.

**Pattern — build a token then call the function under test** — from `tests/test_last_activity_middleware.py:81-101`:

```python
# tests/test_last_activity_middleware.py:81-101
@pytest.mark.asyncio
async def test_valid_token_returns_user_id(self):
    """A real JWT written by the app strategy decodes to an integer user_id."""
    # Create a mock user object with just the fields needed for write_token
    class _MockUser:
        id = 42

    strategy = auth_backend.get_strategy()
    token: str = await strategy.write_token(_MockUser())  # ty: ignore[unresolved-attribute]

    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/openings/positions",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    starlette_req = StarletteRequest(scope)
    result = _extract_user_id(starlette_req)
    assert result == 42
```

Apply this shape for each of the cases listed in RESEARCH.md §"Unit tests" (valid token, admin demoted, target promoted, expired, bad signature, non-impersonation fallthrough).

---

#### `tests/test_last_activity_middleware.py` (MODIFY — add impersonation-skip test)

**Analog:** self — extend `TestLastActivityIntegration` (lines 109-219). Build an impersonation token and assert `last_activity` of BOTH the admin and the target is unchanged after an authenticated request.

---

### Frontend

#### `frontend/src/pages/Admin.tsx` (NEW — page composition)

**Primary analog:** `frontend/src/pages/GlobalStats.tsx` — a straightforward page with sections. The Admin page is a simple composition of `<ImpersonationSelector>` + the relocated `<SentryTestButtons>`.

**Note for planner:** the existing "AdminTools" wrapper at `GlobalStats.tsx:81-85` has `if (!profile?.is_superuser) return null;` — that wrapper is DELETED in this phase (per D-19, the Admin tab itself is gated). The Admin page can assume the user is a superuser (route gate enforces it). But still add a defense-in-depth `is_superuser` check at the page level that redirects, per RESEARCH.md D-18.

---

#### `frontend/src/components/admin/ImpersonationSelector.tsx` (NEW — combobox)

**Primary analog:** no exact analog exists — `cmdk` is a new dependency. But the following existing patterns apply:

**Popover pattern** — `frontend/src/components/ui/info-popover.tsx:26-61` uses `radix-ui/Popover` directly. The new shadcn `popover.tsx` (added via `npx shadcn@latest add popover`) wraps the same primitive. The info-popover file is the closest "how do we build a Popover" example in this codebase.

**useQuery with debounced param** — use `useUserProfile` (lines 5-14) as the base useQuery shape, plus `useDebounce` from `frontend/src/hooks/useDebounce.ts:3-10`:

```typescript
// frontend/src/hooks/useUserProfile.ts:5-14
export function useUserProfile() {
  return useQuery<UserProfile>({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await apiClient.get<UserProfile>('/users/me/profile');
      return res.data;
    },
    staleTime: 300_000, // 5 minutes
  });
}
```

```typescript
// frontend/src/hooks/useDebounce.ts:3-10
export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```

**Combine** (per RESEARCH.md §"Pattern: debounced server-side combobox"): `useQuery({ enabled: debounced.length >= MIN_QUERY_LEN, staleTime: 10_000, ... })`.

**`data-testid` conventions** (per CLAUDE.md Browser Automation section):
- `data-testid="admin-combobox"` on the `Command` root
- `data-testid="admin-combobox-input"` on `CommandInput`
- `data-testid="admin-combobox-item-{user_id}"` per result row
- `data-testid="btn-impersonate-selector"` on the trigger button

**Button variant** (per CLAUDE.md): secondary action = `variant="brand-outline"`. The trigger button is a secondary action.

**Magic numbers** (per CLAUDE.md) — hoist to module constants:
```typescript
const MIN_QUERY_LEN = 2;   // D-12
const MAX_RESULTS = 20;    // D-13
const DEBOUNCE_MS = 250;
```

**Critical `cmdk` gotcha** — RESEARCH.md: must pass `shouldFilter={false}` to `<Command>` because we already filter server-side.

**Error branch** (per CLAUDE.md frontend rules "Always handle `isError` in data-loading ternary chains"):
```tsx
{isError && (
  <div className="p-2 text-xs text-destructive">
    Failed to load users. Something went wrong. Please try again in a moment.
  </div>
)}
```

---

#### `frontend/src/components/admin/ImpersonationPill.tsx` (NEW — header pill)

**Primary analog:** `frontend/src/App.tsx:122-131` — the existing guest badge has exactly the pattern needed (conditional render, theme badge, icon, `data-testid`, `aria-label`):

```tsx
// frontend/src/App.tsx:121-134
<div className="flex items-center gap-2">
  {profile?.is_guest && (
    <Badge
      className="bg-amber-500/15 text-amber-500 border-amber-500/30 text-xs"
      data-testid="nav-guest-badge"
      aria-label="Guest session"
    >
      <DoorOpen className="h-3 w-3 mr-1" />
      Guest
    </Badge>
  )}
  <Button variant="ghost" size="sm" onClick={logout} data-testid="nav-logout">
    Logout
  </Button>
</div>
```

**Replace amber Tailwind classes with theme constants** (per CLAUDE.md "Theme constants in theme.ts"). RESEARCH.md §"Theme tokens" proposes adding `IMPERSONATION_PILL_BG / FG / BORDER` to `frontend/src/lib/theme.ts`. Existing tokens in that file (see `theme.ts:17-40`) use `oklch(...)` strings — follow the same format.

**× button = logout** (per D-20) — use `useAuth().logout`. Icon is `X` from `lucide-react`:
```tsx
<button onClick={logout} aria-label="End impersonation session" data-testid="btn-impersonation-pill-logout">
  <X className="h-3 w-3" />
</button>
```

---

#### `frontend/src/components/admin/SentryTestButtons.tsx` (NEW — extracted from GlobalStats)

**Analog:** `frontend/src/pages/GlobalStats.tsx:20-78` — extract the component verbatim. No transformation beyond changing the import path in consumers.

---

#### `frontend/src/hooks/useAuth.ts` (MODIFY — add `impersonate(userId)`)

**Primary analog:** self — the existing `login` method at lines 40-64 is the exact pattern. The impersonate flow is "call an endpoint, get a token back, swap it in localStorage, clear cache".

**Pattern to copy** — `frontend/src/hooks/useAuth.ts:40-64`:

```typescript
// frontend/src/hooks/useAuth.ts:40-64
const login = async (email: string, password: string): Promise<void> => {
  setIsLoading(true);
  try {
    // FastAPI-Users JWT login uses form-encoded body with `username` field
    const params = new URLSearchParams();
    params.set('username', email);
    params.set('password', password);

    const response = await apiClient.post<LoginResponse>(
      '/auth/jwt/login',
      params,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    );

    const { access_token } = response.data;
    localStorage.setItem('auth_token', access_token);
    // Clear AFTER storing new token so any refetches triggered by the clear
    // use the new user's token, not the previous user's token.
    queryClient.clear();
    setToken(access_token);
    setUser(null); // user details fetched lazily if needed
  } finally {
    setIsLoading(false);
  }
};
```

**New `impersonate` method** — same sequence: POST → `access_token` → `localStorage.setItem('auth_token', ...)` → `queryClient.clear()` → `setToken(...)`. The "Clear AFTER storing new token" comment is a known bug-fix note; preserve that ordering.

**Also update the `AuthState` interface (lines 11-24)** to expose `impersonate` in the context value at line 149.

**Knip note** (per CLAUDE.md frontend rules): `impersonate` must be imported somewhere — it will be imported by the new `ImpersonationSelector.tsx`. Verify Knip passes after adding.

---

#### `frontend/src/types/users.ts` (MODIFY — add `impersonation` field)

**Analog:** self (lines 1-11). Add a nested type.

---

#### `frontend/src/App.tsx` (MODIFY — nav items, pill render, admin route)

**Primary analog:** self.

**Desktop nav items block — line 48-53**:
```typescript
const NAV_ITEMS = [
  { to: '/import', label: 'Import', Icon: DownloadIcon },
  { to: '/openings', label: 'Openings', Icon: BookOpenIcon },
  { to: '/endgames', label: 'Endgames', Icon: TrophyIcon },
  { to: '/global-stats', label: 'Global Stats', Icon: BarChart3Icon },
] as const;
```

**Modification approach** — keep `NAV_ITEMS` as baseline, but filter/append the admin item inside the rendering block based on `profile?.is_superuser`. Per RESEARCH.md Open Question #3, use `ShieldIcon` from `lucide-react`. `as const` enforces narrow literal types — adding a conditional item means building the list from the profile inside the render, which changes the type. Plan needs to pick: mutable `NAV_ITEMS` or render-time filter.

**Mobile More drawer — lines 236-252** — apply the same filter; CLAUDE.md rule "Always apply changes to mobile too" is binding.

**Protected route with superuser gate — lines 396-402**:
```typescript
// frontend/src/App.tsx:395-402
<Route element={<ProtectedLayout />}>
  <Route path="/import" element={<ImportPage ... />} />
  <Route path="/openings/*" element={<OpeningsPage />} />
  <Route path="/endgames/*" element={<EndgamesPage />} />
  <Route path="/rating" element={<Navigate to="/global-stats" replace />} />
  <Route path="/global-stats" element={<GlobalStatsPage />} />
</Route>
```

**New `/admin` route** wrapped in a small `<SuperuserRoute>` component that redirects non-superusers via `<Navigate to="/openings" replace />`. Copy the pattern from `ProtectedLayout` at lines 272-322 (the `if (!token) { return <Navigate to="/login" replace /> }` gate at line 303 is the exact shape).

**`ROUTE_TITLES` — line 62-67** — add `'/admin': 'Admin'`.

**Pill rendering in `NavHeader` (line 79-139) and `MobileHeader` (line 143-170)** — render `<ImpersonationPill>` conditionally on `profile?.impersonation`. RESEARCH.md §"Header pill placement" recommends hiding the desktop Logout button at line 132-134 during impersonation (pill × is the logout control per D-20).

**Token-change job reset** — RESEARCH.md §"TanStack Query cache reset" flags that `ImportJobWatcher` holds admin's job ids in state. The `restoredForTokenRef` block at lines 335-340 is the insertion point:

```typescript
// frontend/src/App.tsx:335-340
const restoredForTokenRef = useRef<string | null>(null);
// eslint-disable-next-line react-hooks/refs -- intentional: reset restoration guard on token change
if (restoredForTokenRef.current !== token) {
  restoredForTokenRef.current = token; // eslint-disable-line react-hooks/refs
  hasRestoredRef.current = false; // eslint-disable-line react-hooks/refs
}
```

Add `setActiveJobIds([]); setCompletedJobIds(new Set())` inside this block.

---

#### `frontend/src/pages/GlobalStats.tsx` (MODIFY — remove Sentry + AdminTools)

**Analog:** self, lines 18-85. Delete lines 18-85 (the `SentryTestButtons` function, its comment banners, and the `AdminTools` wrapper). Remove the `<AdminTools />` render site (locate via Grep after deletion). Knip will catch stray imports.

---

### Frontend Tests — **CRITICAL GOTCHA**

#### `frontend/src/__tests__/components/admin/ImpersonationSelector.test.tsx` + `ImpersonationPill.test.tsx` (NEW)

**No analog exists for component rendering tests.** All current vitest test files (`frontend/src/types/api.test.ts`, `lib/pgn.test.ts`, `lib/utils.test.ts`, `lib/zobrist.test.ts`, `lib/arrowColor.test.ts`) are pure-function tests.

**Missing dependencies** (verified from `frontend/package.json`):
- No `@testing-library/react`
- No `@testing-library/jest-dom`
- No `jsdom` or `happy-dom` (no DOM environment for vitest)
- No `vitest` config in `vite.config.ts` (so no `environment: 'jsdom'` setup)

**Planner decision required:** either
1. Add `@testing-library/react` + `happy-dom` + vitest `test.environment` config (new devDeps + vite.config.ts edit), OR
2. Write these as narrower unit tests of extracted pure helpers (e.g. extract a `matchesUser(query, user): boolean` pure function, test that; leave render paths to manual QA + Playwright/Cypress later).

RESEARCH.md Wave 0 Gaps assumes option (1) and states "No framework install needed — pytest + vitest already wired" — this claim is **incorrect for component-render tests**. Flag to planner.

**Closest pattern for pure-function vitest** — `frontend/src/lib/utils.test.ts:1-10`:

```typescript
// frontend/src/lib/utils.test.ts:1-10
import { describe, it, expect } from 'vitest';
import { createDateTickFormatter, formatDateWithYear } from './utils';

describe('createDateTickFormatter', () => {
  it('returns month+year format for a range greater than 18 months', () => {
    const dates = ['2022-01-01', '2023-10-01']; // ~21 months apart
    const formatter = createDateTickFormatter(dates);
    const result = formatter('2023-06-15');
    expect(result).toMatch(/^[A-Z][a-z]{2} '\d{2}$/);
    expect(result).toBe("Jun '23");
  });
```

Use this shape if the planner picks option (2).

---

## Shared Patterns

### Superuser Endpoint Gate

**Source:** existing inline check at `app/routers/users.py:78-79`; RESEARCH.md §"Superuser dependency (reusable)" recommends migrating to a `current_superuser` dep.

**Apply to:** every new route in `app/routers/admin.py` (`/admin/users/search`, `/admin/impersonate/{id}`).

**Preferred (new) pattern:**
```python
# app/users.py — NEW addition
current_superuser = fastapi_users.current_user(active=True, superuser=True)
```

```python
# app/routers/admin.py — consumption
@router.get("/users/search", response_model=list[UserSearchResult])
async def search_users(
    q: str,
    _admin: Annotated[User, Depends(current_superuser)],  # enforces 403 for non-superusers
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[UserSearchResult]:
    ...
```

**Sentry note** (per CLAUDE.md "Skip trivial/expected exceptions"): the 401/403 raised by `current_superuser` for non-superusers is an **expected** condition. Do NOT wrap these calls with `try/except + sentry_sdk.capture_exception()`. FastAPI's default exception handler returns the correct response.

---

### Manual JWT Token Issuance (bypasses `on_after_login`)

**Source:** `app/services/guest_service.py:51` and `app/routers/auth.py:208`.

**Apply to:** `app/services/admin_service.py` (or inline in router) when issuing the impersonation token. Satisfies D-06 (no last_login update for impersonated user) by construction.

```python
# Canonical pattern — see guest_service.py:51
token: str = await get_guest_jwt_strategy().write_token(user)
```

Replace `get_guest_jwt_strategy()` with `get_impersonation_jwt_strategy()` and call `write_impersonation_token(admin, target)` (custom method on the subclass per RESEARCH.md §"Recommended subclass shape").

---

### ty Suppression Pattern

**Source:** `app/services/guest_service.py:89`, `app/services/guest_service.py:115`, `app/middleware/last_activity.py:64`, `app/routers/auth.py:208`.

**Canonical suppressions:**

```python
# SQLAlchemy column comparison
select(User).where(User.email == email)  # ty: ignore[invalid-argument-type]  # SQLAlchemy column comparisons return ColumnElement, not bool

# FastAPI-Users generic strategy typing
token: str = await strategy.write_token(user)  # ty: ignore[unresolved-attribute]  # FastAPI-Users generic typing not resolved by ty beta

# ASGI Send protocol
await self.app(scope, receive, send_wrapper)  # ty: ignore[invalid-argument-type] — send_wrapper matches the ASGI Send protocol
```

**Apply to:** any new code that triggers `ty` errors in the same categories. Per CLAUDE.md "Always include the rule name and a brief reason."

---

### Frontend Token Swap + Cache Clear

**Source:** `frontend/src/hooks/useAuth.ts:54-60`.

**Apply to:** `useAuth.impersonate(userId)`.

```typescript
// Canonical sequence — order matters (RESEARCH.md confirms)
localStorage.setItem('auth_token', access_token);
// Clear AFTER storing new token so any refetches triggered by the clear
// use the new user's token, not the previous user's token.
queryClient.clear();
setToken(access_token);
setUser(null);
```

---

### `data-testid` Conventions (per CLAUDE.md Browser Automation section)

**Apply to:** every interactive element in new Admin components.

| Pattern | Example |
|---------|---------|
| `btn-{action}` | `btn-impersonate-selector`, `btn-impersonation-pill-logout` |
| `nav-{page}` | `nav-admin`, `mobile-nav-admin`, `drawer-nav-admin` |
| `{component}-{element}-{id?}` | `admin-combobox`, `admin-combobox-input`, `admin-combobox-item-42` |
| Page container | `admin-page` |

Icon-only buttons (e.g. pill ×) require `aria-label` (per CLAUDE.md rule 3).

---

### Theme Constants (per CLAUDE.md)

**Source:** `frontend/src/lib/theme.ts:17-72`. Existing `oklch(...)` format for all semantic colors.

**Apply to:** new `IMPERSONATION_PILL_BG / FG / BORDER` constants. Do NOT hardcode `bg-orange-500/15` Tailwind classes in the component — add named exports to `theme.ts` first, then consume.

---

### TanStack Query Error Handling

**Source:** CLAUDE.md §"Frontend Rules" + RESEARCH.md notes that the global `queryClient.ts` handlers already capture errors.

**Apply to:** the `useQuery` in `ImpersonationSelector.tsx` — do NOT add `Sentry.captureException` manually. The global `QueryCache.onError` in `frontend/src/lib/queryClient.ts` covers it. But DO handle the `isError` branch in the ternary chain with the canonical user-facing message:

```tsx
{isError && (
  <div className="p-2 text-xs text-destructive">
    Failed to load users. Something went wrong. Please try again in a moment.
  </div>
)}
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/components/ui/command.tsx` (shadcn) | ui primitive | event-driven (combobox) | `cmdk` dep does not exist in the codebase. Must be added via `npx shadcn@latest add command popover`. |
| `frontend/src/__tests__/components/admin/ImpersonationSelector.test.tsx` | component test | render + user-event | No `@testing-library/react`, no DOM env configured in vitest. See "CRITICAL GOTCHA" above. |
| `frontend/src/__tests__/components/admin/ImpersonationPill.test.tsx` | component test | render | Same as above. |

---

## Gotchas for the Planner

1. **CRITICAL STALE CLAIM in CONTEXT.md D-08** (already flagged in RESEARCH.md): `last_activity` IS written today by `LastActivityMiddleware`. The D-07 implementation MUST happen in this phase — the existing `_extract_user_id` helper at `app/middleware/last_activity.py:91-104` needs to return both user_id and is_impersonation. Not deferrable.

2. **Frontend component testing framework missing**: No `@testing-library/react`, no jsdom/happy-dom in `frontend/package.json`. RESEARCH.md Wave 0 Gaps item "No framework install needed — pytest + vitest already wired" is **wrong for component-render tests**. Planner must decide: add deps + configure `test.environment: 'happy-dom'` in `vite.config.ts`, OR rescope frontend tests to pure-function tests of extracted helpers.

3. **`cmdk` + `shouldFilter={false}`**: RESEARCH.md flags this — cmdk defaults to client-side fuzzy filtering. For server-side search, you MUST pass `shouldFilter={false}` on the `<Command>` root or results will be hidden.

4. **`ty` complaint on `or_(..., User.id == int(q) if q.isdigit() else False)`**: RESEARCH.md Open Question #4. Use `sa.false()` or conditionally build the clause, not the Python `False` literal.

5. **`as const` on `NAV_ITEMS`** makes it hard to add a conditional admin item: either switch to `readonly` without `as const`, or filter at render-time inside `NavHeader` and `MobileMoreDrawer`.

6. **Knip dead-export detection**: when relocating `SentryTestButtons` out of `GlobalStats.tsx` into `components/admin/SentryTestButtons.tsx`, Knip will flag the new export if nothing imports it. Make sure `Admin.tsx` imports it before running `npm run knip`.

7. **`data-testid` on every new interactive element** (CLAUDE.md hard rule) — every button, link, input, combobox item, pill, and page container needs one.

8. **Mobile parity rule** (CLAUDE.md "Always apply changes to mobile too"): every App.tsx change (nav item addition, pill render, logout-button hide) must be applied to BOTH `NavHeader` (desktop) AND `MobileHeader` + `MobileMoreDrawer` (mobile).

9. **Sentry capture rule** — expected 403s on `/admin/*` from non-superusers are NOT bugs. Do not wrap the FastAPI-Users `current_superuser` dep in try/except + `capture_exception`.

10. **Pre-existing `current_active_user` returns the impersonated user transparently** — this is the key insight of the claim-aware strategy (RESEARCH.md §"Dispatching: one backend"). No existing endpoint needs modification; the target user's data is returned automatically because the User row that `current_active_user` yields is the target, not the admin.

---

## Metadata

**Analog search scope:**
- Backend: `app/routers/`, `app/services/`, `app/repositories/`, `app/schemas/`, `app/middleware/`, `app/users.py`, `app/main.py`, `app/models/`, `tests/`
- Frontend: `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/api/`, `frontend/src/lib/`, `frontend/src/types/`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/components.json`

**Files scanned:** ~25 source files + 4 test files

**Pattern extraction date:** 2026-04-17

---

## PATTERN MAPPING COMPLETE

**Phase:** 62 - admin-user-impersonation
**Files classified:** 26 (18 new + 8 modified)
**Analogs found:** 24 / 26

### Coverage
- Files with exact analog: 18
- Files with role-match/partial analog: 6
- Files with no analog: 2 (shadcn cmdk primitive + component-render tests)

### Key Patterns Identified
- Manual JWT issuance via `strategy.write_token(user)` bypasses `on_after_login` by construction — same pattern used today by guest creation (`guest_service.py:51`) and OAuth callback (`auth.py:208`).
- `app/users.py` already has the exact shape for variant-lifetime JWT strategies (`get_guest_jwt_strategy` at lines 88-96) — adding `get_impersonation_jwt_strategy` is mechanical.
- `frontend/src/hooks/useAuth.ts:40-64` (`login`) is the canonical token-swap sequence — `impersonate` is a near-copy with a different endpoint.
- Middleware `_extract_user_id` at `app/middleware/last_activity.py:91-104` is the exact extension point for D-07 skip; the rest of the middleware needs no changes.
- `frontend/src/App.tsx:122-131` (Guest badge) is a near-exact analog for the impersonation pill.

### Frontend Component Testing Blocker
No `@testing-library/react`, no DOM env for vitest. RESEARCH.md's claim that vitest is "already wired" is correct for pure-function tests only. Planner must decide on deps + config OR rescope to pure-function helper tests.

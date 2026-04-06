# Stack Research

**Domain:** Guest access / anonymous user with account promotion — adding to existing FastAPI + React SPA
**Researched:** 2026-04-06
**Confidence:** HIGH

## Summary

This is subsequent-milestone research. The existing stack (FastAPI 0.115.x, FastAPI-Users 15.0.5, React 19,
Axios, PostgreSQL/asyncpg) is already in place. The goal is identifying the **minimal additions** needed for:

1. Anonymous guest user creation (cookie-based JWT, no signup form)
2. Full platform access as guest
3. Account promotion (email/password or Google SSO) that preserves all imported data

**Bottom line: no new Python or npm packages are required.** Everything needed is already present in
the existing dependencies. This is a configuration and schema extension problem.

---

## Scope Note

The base stack (FastAPI, React 19, PostgreSQL, SQLAlchemy async, TanStack Query, Tailwind, shadcn/ui) is
validated in production at v1.7. Only new capabilities for v1.8 Guest Access are documented here.

---

## Existing Auth State (Critical Context)

| Component | Current State |
|-----------|--------------|
| FastAPI-Users | 15.0.5, `[oauth,sqlalchemy]` extras, maintenance mode (security patches only) |
| Auth transport | `BearerTransport` only; JWT token stored in `localStorage` |
| Auth backend | Single `auth_backend` named `"jwt"` with 7-day JWT lifetime |
| `FastAPIUsers` instance | `FastAPIUsers[User, int](get_user_manager, [auth_backend])` |
| Frontend auth | `useAuth` context with `localStorage`-backed token, Bearer interceptor on `apiClient` |
| Google OAuth | Custom callback (`/auth/google/callback`) that issues Bearer JWT and redirects to frontend |
| CORS (dev) | `allow_credentials=False`, `allow_origins=["http://localhost:5173"]` |
| Production routing | Caddy: same origin — `flawchess.com` serves both frontend static and `/api/` reverse-proxy |

---

## What Changes Are Needed

### Backend

#### 1. Second Auth Backend: CookieTransport

Add a `cookie_auth_backend` alongside the existing bearer backend. FastAPI-Users evaluates backends
in registration order — the first to yield a valid user wins. No new library needed; `CookieTransport`
is already included in `fastapi-users[oauth,sqlalchemy]`.

```python
from fastapi_users.authentication import CookieTransport, AuthenticationBackend, JWTStrategy

cookie_transport = CookieTransport(
    cookie_name="flawchess_guest",
    cookie_max_age=2592000,    # 30 days; None would be session-only
    cookie_httponly=True,      # default — no JS access (XSS protection)
    cookie_secure=True,        # default — HTTPS only; set False in dev via settings
    cookie_samesite="lax",     # default — safe for same-origin SPA
)

# Shared JWT strategy — cookie and bearer can reuse the same signing key and lifetime
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=2592000)

cookie_auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# Register both — bearer checked first, then cookie
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [bearer_auth_backend, cookie_auth_backend],
)
```

**Why bearer first?** Existing full users always send `Authorization: Bearer ...`. Trying bearer first
keeps zero overhead for the common case. Guests only have a cookie, so they fall through to cookie check.

**Why not replace bearer with cookie?** The existing Google OAuth callback issues a Bearer JWT and
redirects to the frontend via a URL fragment (`#token=...`). Changing the primary transport would break
this flow and all existing login sessions.

**SameSite=Lax is sufficient security.** Production is same-origin (Caddy serves both frontend and
`/api` from `flawchess.com`). Development uses Vite proxy (`/api` → `localhost:8000`) which is also
same-origin from the browser's view. Cross-site forgery is not a meaningful attack surface here.
`SameSite=None` is only needed for cross-origin embeds, which this app does not do.

#### 2. `is_guest` Column on User Model (Alembic migration required)

```python
# app/models/user.py
from sqlalchemy import Boolean

is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
```

Keeping guest users in the same `users` table (not a separate table) means **no FK migration on
promotion** — the guest's `user_id` is preserved through the promotion transaction. All related rows
(`games`, `game_positions`, `import_jobs`, `position_bookmarks`) automatically belong to the promoted
user via existing cascade FKs.

Guest creation happens via a custom endpoint (not the standard `/auth/register`), so no changes to
`BaseUserCreate` or the FastAPI-Users schema pipeline are needed. The `is_guest` field is set
programmatically via `user_manager.create()`.

#### 3. Custom Endpoint: `POST /auth/guest`

Creates an anonymous user, issues a cookie-transport JWT. Implementation uses
`user_manager.create()` (already documented in FastAPI-Users cookbook). No new library needed.

```python
# Pseudocode — full implementation in planning
import uuid, secrets
from fastapi import Response

@router.post("/auth/guest")
async def create_guest(response: Response, user_manager = Depends(get_user_manager)):
    guest_email = f"guest_{uuid.uuid4().hex}@guest.flawchess.internal"
    guest_password = secrets.token_urlsafe(32)
    user = await user_manager.create(UserCreate(
        email=guest_email,
        password=guest_password,
        is_active=True,
        is_verified=True,    # skip verification; guest has no real email
        is_guest=True,
    ))
    # Write JWT into HttpOnly cookie via cookie_auth_backend
    token = await cookie_auth_backend.get_strategy().write_token(user)
    await cookie_transport.get_login_response(token, response)
    return {"status": "ok"}
```

The generated email is an internal sentinel, never displayed to users.

#### 4. `current_active_user` Dependency — No Change

The existing dependency `fastapi_users.current_user(active=True)` already works with multiple backends.
When a request arrives without a Bearer token but with the guest cookie, FastAPI-Users falls through
to the cookie backend and authenticates the guest user. All existing protected endpoints work for
guests without modification.

For endpoints that need to distinguish guest from full user (e.g., the import page info box):

```python
current_user_optional = fastapi_users.current_user(active=True, optional=True)
# Returns User or None — use for public endpoints that adjust behavior based on auth state
```

#### 5. Custom Endpoint: `POST /auth/promote`

Promotes a guest to a full account. Two sub-flows:

**Email/password promotion:**
- Validate the guest's cookie JWT to get the current `user_id`
- Check no account with the target email already exists
- `UPDATE users SET email=..., hashed_password=..., is_guest=false, is_verified=true WHERE id=...`
- Issue a new Bearer JWT (so the frontend can transition to bearer-based auth, cleaning up the cookie)

**Google SSO promotion:**
The existing custom OAuth callback in `app/routers/auth.py` is already fully custom. The promotion
flow passes the guest identity through the OAuth round-trip by embedding the guest cookie value (or
a signed reference to the guest `user_id`) in the OAuth `state` JWT. After Google returns:
1. Decode the `state` JWT to extract the guest `user_id`
2. Validate the guest cookie matches
3. Update the guest user with Google email + link the `OAuthAccount` row
4. Set `is_guest=False`, clear the guest cookie

No new library needed — the existing `generate_jwt` / `decode_jwt` from `fastapi_users.jwt` already
handles custom state claims (already used in the CSRF token pattern in the current callback).

### Frontend

#### 1. `withCredentials: true` on Axios

To send the HttpOnly guest cookie with API requests:

```typescript
// frontend/src/api/client.ts
export const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true,    // ADD THIS — sends cookies on all requests
  headers: { 'Content-Type': 'application/json' },
  paramsSerializer: { indexes: null },
});
```

This must be at the instance level so all requests (including those that currently use Bearer) also
send the cookie. When Bearer is present, it takes precedence (bearer backend is checked first).
When Bearer is absent (guest flow), the cookie is the auth credential.

**CORS consequence:** `withCredentials: true` requires `Access-Control-Allow-Credentials: true`
from the server. In dev (`ENVIRONMENT=development`), update `CORSMiddleware`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,    # ADD THIS — required when frontend sends withCredentials: true
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Production requires no CORS change — same-origin means the browser never issues a CORS preflight.

#### 2. Auth State Extension

The `useAuth` context needs the following additions (no new packages):

| Addition | Purpose |
|----------|---------|
| `isGuest: boolean` | Derived from `user.is_guest`; drives UI info box, promotion CTA |
| `loginAsGuest()` | `POST /api/auth/guest` — no token to store; browser stores HttpOnly cookie automatically |
| `promote(email, password)` | `POST /api/auth/promote` — transitions guest to full user |

The 401 response interceptor in `apiClient` currently redirects non-auth 401s to `/login`. When
a guest's cookie expires (after 30 days), the 401 should redirect to home (`/`) not login, since
the guest may not have credentials. A simple check: if the 401 happens and there is no `auth_token`
in localStorage, redirect to `/` with a "session expired" query param instead.

#### 3. No New Frontend Packages

| Considered | Verdict | Reason |
|------------|---------|--------|
| `js-cookie` | Not needed | Guest cookie is HttpOnly — JS cannot and should not read it |
| Cookie management library | Not needed | Browser handles HttpOnly cookies transparently |
| New auth library | Not needed | Existing `useAuth` context extended with two new methods |

---

## Recommended Stack (New Additions Only)

### No New Python Packages

| What | How | Version |
|------|-----|---------|
| `CookieTransport` | Already in `fastapi-users[oauth,sqlalchemy]` | 15.0.5 (current) |
| `is_guest` DB column | `Boolean` mapped column + Alembic migration | SQLAlchemy 2.x (current) |

### No New npm Packages

| What | How |
|------|-----|
| `withCredentials: true` | Axios config flag on existing instance |
| Guest login flow | New method in existing `useAuth` context |
| Promotion flow | New method in existing `useAuth` context |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Separate `GuestSession` table | Requires FK re-pointing on promotion; doubles schema; no advantage | `is_guest` bool on existing `User` table |
| `js-cookie` or any cookie library | Guest cookie is HttpOnly — JS cannot access it; cookie management is unnecessary | Let browser handle cookie transparently |
| Redis / session store | JWT is stateless; no server-side session needed | JWTStrategy (already in stack) |
| `starlette-csrf` or CSRF tokens | Unnecessary: SameSite=Lax on same-origin app is sufficient protection | SameSite=Lax (CookieTransport default) |
| `SameSite=None; Secure` cookies | Only needed for cross-origin embeds; adds complexity | `SameSite=Lax` — correct for this app's same-origin architecture |
| Separate Bearer JWT for guest (stored in localStorage) | Defeats XSS-protection purpose of HttpOnly | HttpOnly cookie via CookieTransport |
| Celery or background jobs | Promotion is a synchronous DB update; no async work needed | Inline SQLAlchemy update in promote endpoint |
| New user verification flow for guests | Guests have no real email; `is_verified=True` set at creation | Skip verification; set `is_verified=True` at guest creation |
| `itsdangerous` or custom signed cookies | Signing is already handled by JWTStrategy | JWTStrategy with existing `SECRET_KEY` |

---

## Alternatives Considered

| Decision | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Cookie transport | `CookieTransport` (fastapi-users built-in) | Custom middleware, session-based | CookieTransport integrates with existing UserManager pipeline; no new primitives |
| Guest identity storage | `is_guest` bool on `User` table | Separate `GuestSession` table | Same table = no FK migration on promotion; simpler queries everywhere |
| Data migration on promotion | None (same `user_id` preserved) | Copy rows to new user, delete old | Re-pointing all FKs across `games`, `game_positions`, `position_bookmarks`, `import_jobs` is error-prone and expensive |
| Google SSO promotion | `guest_user_id` embedded in OAuth `state` JWT | Separate post-SSO merge endpoint | State JWT approach avoids second round-trip; consistent with existing CSRF state pattern in `google_callback` |
| Guest sentinel email | `guest_{uuid}@guest.flawchess.internal` | NULL email | FastAPI-Users enforces non-null unique email; internal domain sentinel is invisible to users |
| 401 redirect for expired guest | Redirect to `/` | Redirect to `/login` | Guests have no credentials; `/login` is misleading; home page re-offers "Use as Guest" |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| `fastapi-users` | 15.0.5 (latest, 2026-04-06) | Maintenance mode — security patches only, no new features. `CookieTransport` stable since v10. Multiple backends supported since v10. |
| `CookieTransport` defaults | Any version >= 10 | `cookie_httponly=True`, `cookie_secure=True`, `cookie_samesite="lax"` — production-safe defaults |
| Multiple auth backends | Any version >= 10 | `FastAPIUsers(get_user_manager, [backend1, backend2])` — documented, stable API |
| `fastapi_users.current_user(optional=True)` | Any version >= 10 | Returns `None` instead of 401 for unauthenticated requests |
| `axios` | 1.13.6 (already installed) | `withCredentials` supported since v0.x — stable flag |
| `fastapi` CORSMiddleware | 0.115.x (current) | `allow_credentials=True` required when `withCredentials: true` — stable since Starlette 0.12 |

---

## Sources

- [FastAPI-Users CookieTransport docs](https://fastapi-users.github.io/fastapi-users/latest/configuration/authentication/transports/cookie/) — verified parameters and defaults (`httponly=True`, `secure=True`, `samesite="lax"`) — HIGH confidence
- [FastAPI-Users current user docs](https://fastapi-users.github.io/fastapi-users/latest/usage/current-user/) — verified `optional=True` parameter, multiple backend evaluation order — HIGH confidence
- [FastAPI-Users multiple backends discussion](https://github.com/fastapi-users/fastapi-users/discussions/989) — confirmed two backends on same `FastAPIUsers` instance, sequential evaluation — MEDIUM confidence (community discussion, matches documented API)
- [FastAPI-Users create user programmatically](https://fastapi-users.github.io/fastapi-users/latest/cookbook/create-user-programmatically/) — verified `user_manager.create()` pattern — HIGH confidence
- [fastapi-users PyPI](https://pypi.org/project/fastapi-users/) — verified 15.0.5 as current version, Python 3.10–3.14 support — HIGH confidence
- [MDN Set-Cookie / SameSite](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie) — verified SameSite=Lax behavior for same-origin requests — HIGH confidence
- Existing codebase (`app/users.py`, `app/routers/auth.py`, `app/main.py`, `frontend/src/api/client.ts`, `frontend/src/hooks/useAuth.ts`) — current auth state verified by direct inspection — HIGH confidence

---

*Stack research for: FlawChess v1.8 Guest Access*
*Researched: 2026-04-06*

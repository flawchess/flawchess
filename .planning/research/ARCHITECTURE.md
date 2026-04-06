# Architecture Research

**Domain:** Guest access (anonymous users with account promotion) on existing FastAPI-Users app
**Researched:** 2026-04-06
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌─────────────────────────────────────────┐  │
│  │  AuthContext      │  │  ProtectedLayout (token check)          │  │
│  │  - token (state)  │  │  - guests pass through (token exists)  │  │
│  │  + isGuest flag   │  │  - still redirects /login if no token  │  │
│  │  + promoteGuest() │  └─────────────────────────────────────────┘  │
│  └──────────────────┘                                                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  apiClient (axios)                                            │   │
│  │  Request: attach Bearer token from localStorage              │   │
│  │  Response 401: clear cache, redirect /login (unchanged)      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │ Bearer JWT in Authorization header
┌─────────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  POST /auth/guest/create  (NEW — no auth required)          │    │
│  │  Creates User(is_guest=True, email=<uuid>@guest.local)      │    │
│  │  Returns JWT token in response body (Bearer transport)      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  POST /auth/guest/promote  (NEW — requires current_user)    │    │
│  │  Validates email uniqueness                                 │    │
│  │  Updates user: email, hashed_password, is_guest=False       │    │
│  │  Returns new JWT for same user_id                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  GET  /auth/guest/promote/google/authorize (NEW)            │    │
│  │  GET  /auth/guest/promote/google/callback  (NEW)            │    │
│  │  Carries guest_user_id in OAuth state JWT                   │    │
│  │  On callback: UPDATE user, INSERT oauth_account             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  current_active_user dependency (FastAPI-Users, UNCHANGED)   │   │
│  │  Returns guest User or registered User identically           │   │
│  │  All data queries filter by user_id — no changes needed      │   │
│  └──────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        Database (PostgreSQL)                         │
│  ┌──────────────┐  ┌─────────────────────────────────────────────┐  │
│  │  users table  │  │  All user-owned tables (games, positions,  │  │
│  │  + is_guest   │  │  bookmarks, import_jobs) — UNCHANGED       │  │
│  │    column     │  │  All already FK CASCADE on user deletion   │  │
│  └──────────────┘  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `POST /auth/guest/create` | Create anonymous user, return JWT | NEW |
| `POST /auth/guest/promote` | Promote guest to email/password account | NEW |
| `GET /auth/guest/promote/google/authorize` | Start Google SSO promotion flow | NEW |
| `GET /auth/guest/promote/google/callback` | Complete Google SSO promotion, issue JWT | NEW |
| `User.is_guest` column | Flag distinguishing guest from registered users | NEW (migration) |
| `guest_service.py` | Guest creation and promotion business logic | NEW |
| `AuthContext.isGuest` | Frontend flag derived from user profile response | NEW |
| `GuestInfoBox` | Import page callout explaining signup benefits | NEW |
| `PromoteAccountModal` | UI for email/password and Google promotion | NEW |
| `current_active_user` | FastAPI-Users dependency — works for guests too | UNCHANGED |
| All routers (openings, imports, etc.) | Data queries by user_id — transparent to guest status | UNCHANGED |
| `apiClient` axios interceptor | Bearer token attach + 401 redirect | UNCHANGED |
| `ProtectedLayout` | Token presence check — guests have a token | UNCHANGED |
| `on_after_login` in `UserManager` | Updates last_login — still fires for regular logins | UNCHANGED |

## Recommended Project Structure

No new directories needed. New files follow existing conventions.

```
app/
├── routers/
│   └── auth.py               # MODIFY: add guest create + promote endpoints
├── services/
│   └── guest_service.py      # NEW: create_guest_user(), promote_guest(),
│                             #      promote_guest_google_callback()
├── models/
│   └── user.py               # MODIFY: add is_guest: Mapped[bool] column
├── schemas/
│   └── auth.py               # MODIFY: add GuestCreateResponse, GuestPromoteRequest,
│                             #         GuestPromoteResponse schemas
alembic/
└── versions/
    └── <date>_add_is_guest_to_users.py  # NEW migration

frontend/src/
├── hooks/
│   └── useAuth.ts            # MODIFY: add isGuest state + promoteGuest() action
├── types/
│   └── users.ts              # MODIFY: add is_guest: boolean to UserProfile
├── components/auth/
│   └── PromoteAccountModal.tsx  # NEW: email/password + Google promotion UI
└── pages/
    ├── Home.tsx              # MODIFY: add "Use as Guest" button in hero section
    └── Import.tsx            # MODIFY: add GuestInfoBox when isGuest=true
```

### Structure Rationale

- **`guest_service.py` as new file:** Guest creation and promotion logic involves creating DB records, hashing passwords via `UserManager.password_helper`, and issuing JWTs via `JWTStrategy`. This is non-trivial enough to warrant its own module rather than bloating `auth.py` with business logic.
- **`PromoteAccountModal.tsx` as new file:** Handles two distinct promotion paths (email/password + Google SSO), loading/error state per path, and conflict error handling. Separating it keeps `Import.tsx` focused.
- **No new router file:** Guest auth endpoints belong in `auth.py` alongside the existing JWT login, registration, and Google OAuth endpoints — they are auth operations.

## Architectural Patterns

### Pattern 1: Guest User as a First-Class User Record

**What:** Guest users are full `users` table rows with `is_guest=True`, a synthetic email of the form `guest_<uuid>@guest.local`, no password hash (empty string), `is_active=True`, `is_verified=False`. The JWT issued is structurally identical to a regular user JWT (same secret, same `sub` claim format).

**When to use:** Always, for this feature. The alternative — storing guest identity purely in a cookie without a DB row — cannot enforce FK constraints when games and positions are imported.

**Trade-offs:**
- Pro: Zero changes to any router, repository, or service downstream. `current_active_user` returns a guest `User` indistinguishably from a registered `User`. All data queries use `user_id`.
- Pro: Account promotion is an in-place UPDATE on the existing row. No data migration, no FK changes.
- Con: DB accumulates rows for abandoned guests. Mitigate with periodic cleanup (guests older than 30 days with no games) — defer to a future maintenance milestone.
- Con: Synthetic emails must never be displayed in the UI or passed to email delivery systems. Safeguard: `UserProfileResponse` should not expose the raw `email` field to the frontend when `is_guest=True`, or the frontend must check `isGuest` before displaying the email.

**Example:**
```python
async def create_guest_user(session: AsyncSession) -> tuple[User, str]:
    guest_email = f"guest_{uuid4().hex}@guest.local"
    user = User(
        email=guest_email,
        hashed_password="",
        is_active=True,
        is_verified=False,
        is_superuser=False,
        is_guest=True,
    )
    session.add(user)
    await session.flush()  # get user.id before commit
    await session.commit()
    strategy = get_jwt_strategy()
    token = await strategy.write_token(user)
    return user, token
```

### Pattern 2: Bearer Transport for Guests (same as registered users)

**What:** The milestone spec mentions "HttpOnly cookie JWT". The recommended approach is instead to return the guest JWT in the response body and store it in `localStorage`, exactly like regular login tokens.

**Why not HttpOnly cookie for this feature:**
- The existing `apiClient` uses `Authorization: Bearer` header exclusively. Switching guests to `CookieTransport` while keeping registered users on `BearerTransport` creates a dual-transport system.
- FastAPI-Users supports dual backends (confirmed via docs), but it requires: registering two backends, setting `credentials: true` on CORS for cookie paths, and adding CSRF double-submit protection for all state-changing cookie-authenticated endpoints.
- The security benefit of HttpOnly (XSS protection) already exists as a known accepted risk for the current Bearer-in-localStorage design for all users. Applying it only to guests creates an inconsistent security posture.
- **Recommendation:** Return guest JWT in response body, store in `localStorage`. The `apiClient` Bearer interceptor works without change. If HttpOnly cookies are adopted, do it uniformly for all users in a security hardening milestone.

**Trade-offs:**
- Pro: Zero changes to auth transport, axios interceptor, or CORS configuration.
- Pro: Guest 401 handling (redirect to /login) already works correctly.
- Con: localStorage-stored tokens are XSS-vulnerable — an accepted risk already present for all users.

### Pattern 3: Account Promotion via In-Place Row UPDATE

**What:** When a guest promotes to a full account, the backend updates the existing `users` row: sets `email` to the real email, sets `hashed_password` to the bcrypt hash, sets `is_guest=False`. A new JWT is issued for the same `user_id`. All existing games, positions, and bookmarks remain intact with their FK references unchanged.

**When to use:** Only for guest-to-registered promotion. Not for merging two independent registered accounts.

**Trade-offs:**
- Pro: Data continuity is automatic — no data copy, no FK updates, no migration step.
- Pro: Atomic single-row UPDATE.
- Con: Email uniqueness must be checked before the UPDATE. If a registered account already exists with the target email, return `409 Conflict` and present the user with "An account with this email already exists. Sign in instead."

**Example:**
```python
async def promote_guest(
    session: AsyncSession,
    guest_user: User,
    email: str,
    password: str,
    password_helper: PasswordHelperProtocol,
) -> str:
    # Check email uniqueness against existing non-guest users
    stmt = select(User).where(User.email == email, User.id != guest_user.id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise EmailAlreadyTakenError()

    hashed = password_helper.hash(password)
    await session.execute(
        update(User)
        .where(User.id == guest_user.id)
        .values(email=email, hashed_password=hashed, is_guest=False)
    )
    await session.commit()
    strategy = get_jwt_strategy()
    return await strategy.write_token(guest_user)
```

### Pattern 4: Google SSO Promotion via State-Carried Guest ID

**What:** Guest clicks "Continue with Google" in the promotion modal. The authorize endpoint encodes the guest `user_id` into the OAuth state JWT (alongside the existing CSRF token). The callback route reads the guest ID from state and performs an UPDATE (attach `OAuthAccount`, set `is_guest=False`) rather than a CREATE.

**Why this approach:** The existing Google callback route (`/auth/google/callback`) calls `user_manager.oauth_callback()` which creates a new user if none exists. For guest promotion, a separate callback route is needed that knows to UPDATE the existing guest row rather than create a new one.

**Trade-offs:**
- Pro: Reuses existing Google OAuth client, no new OAuth credentials needed.
- Pro: Same JWT signing infrastructure for state validation.
- Con: Two Google callback routes must both be registered in Google Cloud Console as authorized redirect URIs. Use a different path: `/api/auth/guest/promote/google/callback` distinct from the existing `/api/auth/google/callback`.
- Con: Must validate state JWT's `guest_user_id` matches the currently authenticated guest session to prevent CSRF guest-hijacking.

## Data Flow

### Guest Creation Flow

```
Homepage: "Use as Guest" button clicked
    ↓
POST /api/auth/guest/create  (no Authorization header)
    ↓
guest_service.create_guest_user(session)
    INSERT users (email=guest_<uuid>@guest.local, is_guest=True, is_active=True)
    generate JWT for new user.id via get_jwt_strategy()
    ↓
Response: { access_token: "...", token_type: "bearer", is_guest: true }
    ↓
Frontend:
    localStorage.setItem('auth_token', access_token)
    AuthContext: setToken(token), setIsGuest(true)
    Navigate to /import
```

### Authenticated Guest Request Flow

```
GET /api/openings/positions?...
    ↓
axios interceptor: Authorization: Bearer <guest_jwt>
    ↓
current_active_user (FastAPI-Users JWT decode, UNCHANGED)
    user_id = 42 (guest user)
    returns User(id=42, is_guest=True, is_active=True)
    ↓
openings_service.get_positions(session, user_id=42, filters)
    queries game_positions WHERE user_id = 42  (UNCHANGED)
    ↓
Response: WDL stats (same schema as for registered user)
```

### Email/Password Promotion Flow

```
Guest on Import page: clicks "Sign up" in GuestInfoBox
    ↓
PromoteAccountModal opens (email + password fields)
    ↓
POST /api/auth/guest/promote
    Body: { email, password }
    Header: Authorization: Bearer <guest_jwt>
    ↓
current_active_user → User(is_guest=True)
guest_service.promote_guest(session, user, email, password, password_helper)
    check uniqueness: SELECT users WHERE email=? AND id != guest_id
    UPDATE users SET email=?, hashed_password=?, is_guest=False WHERE id=?
    generate new JWT (same user_id, same token structure)
    ↓
Response: { access_token: "...", is_guest: false }
    ↓
Frontend:
    loginWithToken(new_token)  [existing AuthContext method — UNCHANGED]
    setIsGuest(false)
    toast("Account created successfully! All your data has been kept.")
```

### Google SSO Promotion Flow

```
Guest: clicks "Continue with Google" in PromoteAccountModal
    ↓
GET /api/auth/guest/promote/google/authorize
    Header: Authorization: Bearer <guest_jwt>
    current_active_user → User(is_guest=True)
    state_jwt = { guest_user_id: user.id, csrftoken: random }
    return { authorization_url }
    ↓
Frontend: window.location.href = authorization_url
    ↓
Google redirects to:
GET /api/auth/guest/promote/google/callback?code=...&state=...
    decode state JWT → guest_user_id
    exchange code for Google id_token
    extract account_id, account_email from id_token
    CHECK: is account_email already owned by a different registered user?
        YES → 409, redirect with error
        NO → proceed
    UPDATE users SET email=account_email, is_guest=False WHERE id=guest_user_id
    INSERT oauth_accounts (user_id=guest_user_id, oauth_name="google", ...)
    generate JWT for guest_user_id
    ↓
Redirect: FRONTEND_URL/auth/callback#token=JWT
    ↓
OAuthCallbackPage: loginWithToken(token)  [existing, UNCHANGED]
    setIsGuest(false) via profile refetch
```

### State Management

```
AuthContext (React)
    token: string | null        stored in localStorage
    isGuest: boolean            derived from /users/me/profile.is_guest
    isLoading: boolean
    login()                     UNCHANGED
    loginWithToken()            UNCHANGED — used after promotion
    register()                  UNCHANGED
    logout()                    UNCHANGED
    promoteGuest(email, pw)     NEW — calls POST /auth/guest/promote

isGuest is populated by reading the is_guest field from the UserProfile
response already fetched in useUserProfile() on app mount.
The UserProfile API call happens when token is set, so isGuest is available
before any protected page renders.
```

## Integration Points

### Modified Components

| Component | What Changes | Risk |
|-----------|-------------|------|
| `app/models/user.py` | Add `is_guest: Mapped[bool]` column with server default `false` | LOW — additive, non-breaking migration |
| `app/schemas/users.py` | Add `is_guest: bool` field to `UserProfileResponse` | LOW — additive field |
| `app/schemas/auth.py` | Add `GuestCreateResponse`, `GuestPromoteRequest`, `GuestPromoteResponse` | LOW — new schemas only |
| `app/routers/auth.py` | Add 4 new endpoints; all existing endpoints untouched | LOW |
| `frontend/src/hooks/useAuth.ts` | Add `isGuest: boolean` state + `promoteGuest()` action | MEDIUM — central auth hook |
| `frontend/src/types/users.ts` | Add `is_guest: boolean` to `UserProfile` interface | LOW |
| `frontend/src/pages/Home.tsx` | Add "Use as Guest" button in hero section | LOW |
| `frontend/src/pages/Import.tsx` | Add `GuestInfoBox` conditional on `isGuest` | LOW |
| `frontend/src/App.tsx` | No change expected; `ProtectedLayout` already works for guests | NONE |

### New Components

| Component | Type | Depends On |
|-----------|------|------------|
| `app/services/guest_service.py` | Backend service | `User` model, `JWTStrategy`, `password_helper` |
| `alembic/versions/<date>_add_is_guest_to_users.py` | DB migration | `users` table |
| `frontend/src/components/auth/PromoteAccountModal.tsx` | React component | `useAuth.promoteGuest`, Google authorize endpoint |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `auth.py` router ↔ `guest_service.py` | Direct function call | Router stays HTTP-only; all logic in service |
| `guest_service.py` ↔ `UserManager.password_helper` | Inject via `Depends(get_user_manager)` | Reuses existing password hashing infrastructure |
| `guest_service.py` ↔ `get_jwt_strategy()` | Direct call (no Depends needed) | `get_jwt_strategy()` is a plain factory function in `users.py` |
| `guest JWT` ↔ `current_active_user` | FastAPI-Users JWT decode | No change; guest users are active users with valid JWTs |
| `UserProfile.is_guest` ↔ `AuthContext.isGuest` | API field in `/users/me/profile` response | Frontend derives `isGuest` from this field; already fetched on app mount |
| Google promote callback ↔ existing OAuth infrastructure | Reuses `google_oauth_client.get_access_token()` | Different route path; must register new callback URL in Google Cloud Console |

## Build Order

Dependencies flow strictly top to bottom within each step.

**Step 1: DB migration**
Add `is_guest: bool` column to `users` with `server_default=false`. This is required by all subsequent steps. Run `alembic revision --autogenerate` then review the generated migration.

**Step 2: Backend model + schema additions**
- Add `is_guest: Mapped[bool]` to `User` model
- Add `is_guest: bool` to `UserProfileResponse` in `schemas/users.py`
- Add new schemas to `schemas/auth.py`: `GuestCreateResponse`, `GuestPromoteRequest`, `GuestPromoteResponse`
No router changes yet — just the data model and schemas.

**Step 3: `guest_service.py`**
Implement `create_guest_user()` and `promote_guest()`. These are pure service functions with no frontend dependency. Write unit tests for both (especially the email-uniqueness check).

**Step 4: Auth router — create and promote email endpoints**
Add `POST /auth/guest/create` and `POST /auth/guest/promote` to `auth.py`. Smoke test both with `curl` or the FastAPI `/docs` UI.

**Step 5: Frontend `useAuth.ts` + `types/users.ts`**
Add `isGuest` to `AuthState`, derive it from the `UserProfile.is_guest` field. Add `promoteGuest()` action. This is the frontend hub; import page and homepage depend on it.

**Step 6: Homepage "Use as Guest" button**
Add a secondary CTA button in `Home.tsx` hero section. Calls `POST /auth/guest/create`, stores token via `loginWithToken()`, navigates to `/import`.

**Step 7: `GuestInfoBox` on Import page**
Render a callout in `Import.tsx` when `isGuest=true`. Include a "Sign up to keep your data" message and a button that opens `PromoteAccountModal`.

**Step 8: `PromoteAccountModal` — email/password path**
Build the modal component with email/password fields. Call `promoteGuest()` from `useAuth`. Handle `409 Conflict` case ("Account exists — sign in instead").

**Step 9: Google SSO promotion endpoints**
Implement `guest_service.promote_guest_google_callback()`. Add the authorize and callback routes to `auth.py`. Register the new callback URL in Google Cloud Console.

**Step 10: `PromoteAccountModal` — Google path**
Add "Continue with Google" button to the modal. Wire to the new authorize endpoint. The existing `OAuthCallbackPage` handles the token from the redirect fragment — no change needed there.

## Anti-Patterns

### Anti-Pattern 1: Switching Guests to CookieTransport

**What people do:** Implement a second FastAPI-Users auth backend using `CookieTransport` for guests while keeping `BearerTransport` for registered users.

**Why it's wrong:** Dual-transport doubles backend auth complexity. The existing `apiClient` Bearer interceptor already handles all tokens uniformly. CORS must allow credentials for cookie requests. All state-changing endpoints need CSRF protection when cookie auth is possible. The XSS risk difference (HttpOnly vs localStorage) already exists for registered users and is not a guest-specific concern.

**Do this instead:** Return guest JWT in the response body. Store in `localStorage`. If HttpOnly cookies become a requirement, apply to all users uniformly in a dedicated security milestone.

### Anti-Pattern 2: Separate Guest Data Tables

**What people do:** Create a `guest_sessions` or `anonymous_data` table to avoid storing anonymous rows in `users`.

**Why it's wrong:** All 6+ existing repositories query by `user_id` with FK constraints. A separate table means duplicating all query logic or migrating FKs on promotion (updating `user_id` across `games`, `game_positions`, `position_bookmarks`, `import_jobs`).

**Do this instead:** Store guests in `users` with `is_guest=True`. Promotion is a single-row UPDATE; child table FK references never change.

### Anti-Pattern 3: Client-Side Guest Identity Generation

**What people do:** Generate a random guest ID in JavaScript and use it as a fake user identifier without a DB row.

**Why it's wrong:** No real DB row exists to enforce FK constraints. Games imported against a non-existent `user_id` violate referential integrity and the explicit project rule that all FK columns must have `ForeignKey()` constraints.

**Do this instead:** Always create a real `users` row server-side before returning any token. The DB row is the source of truth for the user's identity.

### Anti-Pattern 4: Allowing Promotion Without Email Uniqueness Check

**What people do:** Execute the `UPDATE users SET email=... WHERE id=guest_id` without first checking if the email is already registered to another account.

**Why it's wrong:** Violates the email uniqueness invariant. PostgreSQL will throw an integrity error, surfacing as a 500 rather than a clean 409. Worse, if the uniqueness constraint is not enforced at DB level (it is, via FastAPI-Users' `users` table DDL), this could silently create duplicate emails.

**Do this instead:** Always SELECT for an existing non-guest user with the same email before UPDATE. Return `409 Conflict` with a message guiding the user to sign in instead.

### Anti-Pattern 5: Exposing Synthetic Guest Email in the UI

**What people do:** Render `profile.email` in the mobile "More" drawer header or account settings for guest users, showing `guest_abc123@guest.local`.

**Why it's wrong:** Confuses users who see a nonsensical email address. May also cause support requests.

**Do this instead:** In `App.tsx` `MobileMoreDrawer` and anywhere `profile.email` is displayed, check `isGuest` and show "Guest" (or nothing) instead of the synthetic email. This is a frontend-only guard.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (< 1k registered users) | No changes — single-process, guest rows are negligible |
| 1k-10k users | Add periodic cleanup: DELETE users WHERE is_guest=true AND created_at < now() - interval '30 days' AND id NOT IN (SELECT DISTINCT user_id FROM games). Run as a startup task or APScheduler job. |
| 10k+ users | Guest account accumulation becomes non-trivial. Add `created_at` index to `users` for cleanup query performance. Consider shorter TTL (7 days) for guests with no games. |

Guest cleanup is not needed at current FlawChess scale. Defer to a future maintenance task.

## Sources

- [FastAPI-Users CookieTransport docs](https://fastapi-users.github.io/fastapi-users/10.3/configuration/authentication/transports/cookie/) — HIGH confidence (official docs, HttpOnly default confirmed)
- [FastAPI-Users multiple auth backends discussion](https://github.com/fastapi-users/fastapi-users/discussions/960) — HIGH confidence (maintainer confirms dual-backend works out of the box)
- [FastAPI-Users optional current_user](https://fastapi-users.github.io/fastapi-users/latest/usage/current-user/) — HIGH confidence (current official docs)
- [FusionAuth anonymous user pattern](https://fusionauth.io/blog/anonymous-user) — MEDIUM confidence (industry best-practices blog)
- Direct inspection of `app/users.py`, `app/models/user.py`, `app/routers/auth.py`, `frontend/src/hooks/useAuth.ts`, `frontend/src/api/client.ts` — HIGH confidence (live codebase)

---
*Architecture research for: FlawChess v1.8 Guest Access*
*Researched: 2026-04-06*

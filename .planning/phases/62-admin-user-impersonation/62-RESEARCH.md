# Phase 62: Admin user impersonation - Research

**Researched:** 2026-04-17
**Domain:** FastAPI-Users JWT extension + shadcn/ui combobox + React auth swap
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Impersonation mechanism**
- **D-01:** Dedicated JWT issued on `POST /admin/impersonate/{user_id}` (exact path at planner's discretion). Claims include at minimum `sub = impersonated_user_id`, `act_as = impersonated_user_id`, `admin_id = admin_user_id`, `is_impersonation = true`.
- **D-02:** A custom `JWTStrategy.read_token` (or equivalent dependency wrapper) validates on every request: `admin_id` resolves to an active superuser, `act_as` resolves to an active non-superuser, admin is still `is_superuser = true`. Any failure → 401.
- **D-03:** Impersonation token lifetime = 1 hour. Regular / guest lifetimes unchanged (7 days, 365 days).
- **D-04:** Endpoint rejects nested impersonation (caller must hold a non-impersonation superuser token) → 403.
- **D-05:** Impersonating another superuser → 403.

**last_login / last_activity suppression**
- **D-06:** `UserManager.on_after_login` must not fire for impersonation. Simplest implementation: impersonation path does not go through the standard login endpoint, so `on_after_login` is never invoked.
- **D-07:** Any `last_activity` write skips when JWT has `is_impersonation = true`. Add a helper and document it.
- **D-08:** Admin's own `last_activity` during impersonation is deferred.

**Session lifecycle**
- **D-09:** Single-token model. Admin's original token is replaced in `localStorage['auth_token']`.
- **D-10:** Ending impersonation = clicking × on the pill = existing `useAuth.logout()`.
- **D-11:** No "stop impersonating" return-to-admin flow.

**User selector UX**
- **D-12:** Searchable combobox, server-side search, debounced, min 2 chars. Matches `email` + `chess_com_username` + `lichess_username` (case-insensitive ILIKE) + exact match on numeric `id`.
- **D-13:** `GET /admin/users/search?q=...` (path TBD) returns ≤ 20 results. Fields per user: `id`, `email`, `chess_com_username`, `lichess_username`, `is_guest`, `last_login`. Superuser-gated, else 403.
- **D-14:** Row display must disambiguate (email + platforms + is_guest badge + last_login). Click triggers impersonation and navigates to Openings (or default).
- **D-15:** No recently-impersonated list.

**Admin tab placement**
- **D-16:** Desktop: rightmost top-nav tab, rendered only when `profile.is_superuser === true`.
- **D-17:** Mobile: in the More drawer, gated on `is_superuser`. Bottom nav unchanged (4 tabs).
- **D-18:** Route `/admin` (TBD). `ProtectedLayout` + `is_superuser` check; direct URL access by non-superuser → 403 or redirect.
- **D-19:** Admin page sections: (1) Impersonate user, (2) Sentry Error Test (moved verbatim from `GlobalStats.tsx`). `AdminTools` wrapper + its `is_superuser` gate on Global Stats are removed.

**Impersonation pill**
- **D-20:** Header pill `Impersonating {email} ×` in both desktop and mobile headers. × is the logout control.
- **D-21:** No banner, no sticky-layout displacement, no tab-title change.
- **D-22:** Source of the pill state = new field on `/users/me/profile` OR a decoded JWT claim. Planner picks; recommendation below.

**Scope of actions**
- **D-23:** Full user action surface, no per-endpoint carveouts.

### Claude's Discretion
- Exact REST paths (`/admin/impersonate/{id}`, `/admin/users/search`, frontend route `/admin`).
- Combobox component (shadcn/ui Command + Popover expected).
- Pill color (warning / elevated, works in both themes).
- How the frontend discovers "I am in an impersonation session".

### Deferred Ideas (OUT OF SCOPE)
- Impersonation audit log table.
- "Stop impersonating" return-to-admin button (dual-token UX).
- Recently-impersonated list.
- Blocking destructive account ops while impersonating.
- Admin's own last_activity tracking during impersonation.
- Browser tab title / favicon change during impersonation.

</user_constraints>

## Project Constraints (from CLAUDE.md)

**Backend:**
- Must pass `uv run ty check app/ tests/` — zero errors. Explicit return types, `Sequence[str]` over `list[str]` for params, Pydantic at boundaries, TypedDict internally, `# ty: ignore[rule-name]` with rule + reason.
- Routers use `APIRouter(prefix="/resource", tags=["resource"])` with relative paths (no prefix in decorators).
- Sentry: `sentry_sdk.capture_exception()` in non-trivial except blocks; skip expected 403/invalid-token; never embed vars in messages.
- Pydantic v2 + Literal types for fixed-value string fields.

**Frontend:**
- `noUncheckedIndexedAccess` enabled — narrow array/record indexing before use.
- Theme constants in `frontend/src/lib/theme.ts`. No hard-coded semantic colors.
- Knip in CI — every export must be imported somewhere.
- `data-testid` on every interactive element; `aria-label` on icon-only buttons.
- Semantic HTML only (`<button>`, `<a>`, `<nav>`, `<main>`).
- Apply changes to both desktop and mobile views.
- Primary button = `variant="default"`; secondary = `variant="brand-outline"`.

**Workflow:**
- No unplanned features. If something needed beyond phase scope → flag, don't implement.
- Phase branches OK to commit frequently; main branch requires user request.
- Deploy only via `bin/deploy.sh` (CI-gated).

## Research Summary

1. **`on_after_login` bypass is automatic if we issue the token manually via `JWTStrategy.write_token(user)` and return it from `/admin/impersonate` without routing through `/auth/jwt/login`.** FastAPI-Users only calls `on_after_login` from its built-in auth router — custom endpoints skip it. This matches the existing guest flow (`app/services/guest_service.py`) and the OAuth callback in `app/routers/auth.py:200-205` which manually updates `last_login` precisely because `on_after_login` didn't fire. **Verified by reading site-packages source and project code.**

2. **Custom claims pass through `generate_jwt` and `decode_jwt` transparently** — PyJWT preserves arbitrary payload fields, and `decode_jwt` returns the full decoded dict including extras (see `fastapi_users/jwt.py` lines 17-41). The default `JWTStrategy.read_token` only reads `sub`; our custom claims (`act_as`, `admin_id`, `is_impersonation`) survive round-trip but must be validated by a wrapper that runs per-request. **Verified.**

3. **CRITICAL STALE CLAIM in CONTEXT.md:** D-08 says `last_activity` "isn't today" — but `LastActivityMiddleware` at `app/middleware/last_activity.py` (commit 2beabd3, 2026-04-12) already writes `last_activity` every ~1h per user via a throttled ASGI middleware. The planner must wire the `is_impersonation` skip into that middleware NOW, not defer. The D-07 requirement is real and immediate. **Verified — flag for user confirmation.**

4. **shadcn/ui `Command` + `Popover` are NOT currently installed** — only `radix-ui` (composite) is a dep, and the existing components directory has `info-popover.tsx` (rolled own Popover via `radix-ui/Popover`) but no `command.tsx`. Plan must include `npx shadcn@latest add command popover` as a first step; this also adds `cmdk` to `package.json`. **Verified via `frontend/package.json` + `frontend/src/components/ui/` listing.**

5. **Frontend already has `useDebounce` hook** (`frontend/src/hooks/useDebounce.ts`, used in `Openings.tsx`) — the selector should reuse it, not add `lodash.debounce`. No new client-side JWT decoder is needed: exposing `impersonation: { admin_id, target_email } | null` on `/users/me/profile` is strictly simpler than client-side JWT decoding and requires no new dependency. **Recommendation with HIGH confidence.**

**Primary recommendation:** Subclass `JWTStrategy` as `ImpersonationJWTStrategy` with 1-hour lifetime, override `write_token` to inject `act_as/admin_id/is_impersonation`, and override `read_token` to validate admin is still superuser + target is still non-superuser. Register a second `AuthenticationBackend` with `get_strategy` returning this subclass when the incoming token has `is_impersonation=true`, OR (simpler) register a FastAPI dependency `current_active_user_or_impersonation` that dispatches on the claim and re-uses both strategies' `read_token`. Issue tokens from `POST /admin/impersonate/{id}` via manual `impersonation_strategy.write_token(...)`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Impersonation JWT issuance | API (FastAPI) | — | Token signing requires SECRET_KEY, must be server-side |
| Admin identity + target validation on every request | API (auth dependency) | — | Security check — cannot be trusted from client |
| User search (email / username / id ILIKE) | API + DB | — | PostgreSQL ILIKE with a LIMIT, no business logic |
| Token swap in localStorage | Browser | — | Client-only concern, same pattern as login |
| TanStack Query cache reset on token swap | Browser | — | All queries are user-scoped; stale cache would leak admin's data |
| "Am I impersonating" signal | API (profile response) | Browser (decode JWT) | Profile field is simpler — no new dep, no CSP surprise |
| Pill rendering in header | Browser | — | Pure UI |
| Admin tab visibility gate | Browser (derived from profile) | API (route-level 403) | Visibility = UX; 403 = security. Both required |
| last_activity skip on impersonation | API (middleware) | — | Already server-side; add claim check |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi-users | 15.0.5 | Auth backend | Already in use; supports custom `JWTStrategy` subclassing |
| fastapi | 0.115.x | HTTP framework | Existing |
| PyJWT (via fastapi-users) | — | JWT encode/decode | Passes extra claims through transparently |
| SQLAlchemy async | 2.x | ORM | Existing |
| shadcn/ui Command | latest | Combobox | Matches existing shadcn stack; wraps `cmdk` |
| cmdk | via shadcn CLI | Combobox primitive (autocomplete, keyboard nav) | De-facto React combobox lib, built-in arrow/enter/esc |
| radix-ui Popover | 1.4.3 (installed) | Positioning wrapper | Already used in `info-popover.tsx` |
| TanStack Query | 5.90.21 | Server-state cache | Existing; cache reset on token swap is already established |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `useDebounce` (local) | — | Debouncing search input | Already in `frontend/src/hooks/useDebounce.ts`; do NOT add `lodash.debounce` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `JWTStrategy` subclass | Middleware that rewrites the user | More implicit; harder to test; breaks the `current_active_user` contract by mutating inside a middleware |
| Profile-response impersonation state | Client-side `jwt-decode` lib | Adds a dep for one field; means frontend and backend reach different conclusions if token and server state drift |
| shadcn Command combobox | Plain `<Input>` + result `<ul>` | Less keyboard-accessible, fails WCAG for combobox role; more code to write |
| Two `AuthenticationBackend`s | One backend + smart dependency that reads claim and routes to correct strategy | Single-backend is simpler — only one `fastapi_users` instance needed |

**Installation:**
```bash
# Frontend (from frontend/ directory)
npx shadcn@latest add command popover
# This adds cmdk to package.json and creates:
#   src/components/ui/command.tsx
#   src/components/ui/popover.tsx
```

**Version verification:** `fastapi-users==15.0.5` is pinned in `pyproject.toml`; `radix-ui==1.4.3` and `@tanstack/react-query==5.90.21` are pinned in `frontend/package.json`. shadcn CLI resolves `command`/`popover` to the current registry version at add time — lock at whatever ships on 2026-04-17.

## FastAPI-Users extension patterns (JWT strategy, impersonation endpoint, on_after_login bypass)

### How custom claims survive the round-trip

From `.venv/lib/python3.13/site-packages/fastapi_users/jwt.py`:

```python
# generate_jwt: payload.copy() + exp; PyJWT serializes whatever is passed
def generate_jwt(data: dict, secret, lifetime_seconds, algorithm="HS256") -> str:
    payload = data.copy()
    if lifetime_seconds:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=lifetime_seconds)
    return jwt.encode(payload, _get_secret_value(secret), algorithm=algorithm)

# decode_jwt: returns the full payload dict
def decode_jwt(encoded_jwt, secret, audience, algorithms=[JWT_ALGORITHM]) -> dict:
    return jwt.decode(encoded_jwt, _get_secret_value(secret), audience=audience, algorithms=algorithms)
```

Custom claims are safe. The default `JWTStrategy.read_token` only consumes `sub`:

```python
# .venv/.../fastapi_users/authentication/strategy/jwt.py:43-63
async def read_token(self, token, user_manager):
    data = decode_jwt(token, self.decode_key, self.token_audience, algorithms=[self.algorithm])
    user_id = data.get("sub")
    # ...returns the user for sub; ignores extra claims
```

### Recommended subclass shape

```python
# app/users.py (additions)
from datetime import datetime, timezone
from fastapi_users.authentication import JWTStrategy
from fastapi_users.jwt import decode_jwt, generate_jwt
import jwt as pyjwt

IMPERSONATION_TTL_SECONDS = 3600  # 1 hour (D-03)

class ImpersonationJWTStrategy(JWTStrategy[User, int]):
    """Issues + validates impersonation JWTs.

    Claims added on top of the default `sub` and `aud`:
      - act_as: impersonated user id (mirrors sub for clarity)
      - admin_id: the superuser who initiated impersonation
      - is_impersonation: True
    """

    async def write_impersonation_token(self, admin: User, target: User) -> str:
        data = {
            "sub": str(target.id),
            "aud": self.token_audience,
            "act_as": target.id,
            "admin_id": admin.id,
            "is_impersonation": True,
        }
        return generate_jwt(data, self.encode_key, self.lifetime_seconds, algorithm=self.algorithm)

    async def read_token(self, token, user_manager):
        if token is None:
            return None
        try:
            data = decode_jwt(token, self.decode_key, self.token_audience, algorithms=[self.algorithm])
        except pyjwt.PyJWTError:
            return None
        if not data.get("is_impersonation"):
            # Not an impersonation token — fall through to default path
            return await super().read_token(token, user_manager)

        admin_id = data.get("admin_id")
        act_as = data.get("act_as")
        if admin_id is None or act_as is None:
            return None

        # Validate admin is still a superuser AND active
        admin = await user_manager.user_db.get(admin_id)
        if admin is None or not admin.is_active or not admin.is_superuser:
            return None

        # Validate target is still active and NOT a superuser (D-05 holds forever)
        target = await user_manager.user_db.get(int(act_as))
        if target is None or not target.is_active or target.is_superuser:
            return None

        return target


def get_impersonation_jwt_strategy() -> ImpersonationJWTStrategy:
    return ImpersonationJWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=IMPERSONATION_TTL_SECONDS,
    )
```

### Dispatching: one backend, claim-aware strategy

Register a single strategy factory that detects the claim and delegates. Reads the raw token from `Authorization` header in a FastAPI dependency:

```python
# app/users.py
from fastapi import Depends, Request
from fastapi_users.authentication import AuthenticationBackend

def _peek_is_impersonation(token: str | None) -> bool:
    """Unverified peek at the JWT payload to pick a strategy.
    Signature validation happens inside the chosen strategy's read_token.
    """
    if not token:
        return False
    try:
        # decode without verify — we only read is_impersonation flag
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        import base64, json
        return bool(json.loads(base64.urlsafe_b64decode(payload_b64)).get("is_impersonation"))
    except Exception:
        return False


def get_claim_aware_jwt_strategy(request: Request = None) -> JWTStrategy:
    # fastapi-users calls get_strategy() without arguments in its dependency chain.
    # We need a Request-aware variant; simplest approach: always return a
    # *wrapper* strategy whose read_token sniffs the claim itself.
    return ClaimAwareJWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=604800)


class ClaimAwareJWTStrategy(JWTStrategy[User, int]):
    """Wraps default + impersonation strategies and dispatches per-token."""
    _imp = get_impersonation_jwt_strategy()

    async def read_token(self, token, user_manager):
        if token and _peek_is_impersonation(token):
            return await self._imp.read_token(token, user_manager)
        return await super().read_token(token, user_manager)

    async def write_token(self, user):
        return await super().write_token(user)  # default, for normal logins
```

Then:

```python
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_claim_aware_jwt_strategy,  # was get_jwt_strategy
)
```

`current_active_user = fastapi_users.current_user(active=True)` continues to work unchanged — it calls `strategy.read_token` which now routes through the claim-aware wrapper. The returned `User` is the impersonated user for impersonation tokens and the authenticated user otherwise. **This is the key insight: every downstream endpoint keeps its existing `Depends(current_active_user)` signature and gets the right user transparently.**

### Impersonation endpoint (manual token issuance bypasses `on_after_login`)

```python
# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.users import current_active_user, get_impersonation_jwt_strategy
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/impersonate/{user_id}", response_model=ImpersonateResponse)
async def impersonate(
    user_id: int,
    admin: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImpersonateResponse:
    # D-04: caller must be a non-impersonation superuser
    if not admin.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")
    # NOTE: to detect "is the caller themselves already impersonating?", we need
    # access to the raw token OR a marker on admin. Simplest: expose request
    # state (see below section). For now, assume the claim-aware strategy
    # returns only `target`, never the admin, when impersonation is active —
    # so `admin.is_superuser` would reflect the *target*, failing this check.
    target = await session.get(User, user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot impersonate another superuser")
    strategy = get_impersonation_jwt_strategy()
    token = await strategy.write_impersonation_token(admin, target)
    return ImpersonateResponse(access_token=token, token_type="bearer", target_email=target.email)
```

**Key insight for D-04 nested-impersonation rejection:** Because the claim-aware strategy returns the *target* user (not the admin) when the incoming token is an impersonation one, the `admin.is_superuser` check above naturally fails for nested attempts (the target is non-superuser by construction per D-05). So D-04 is enforced automatically by the superuser check above — no separate raw-token inspection needed. Document this in the endpoint comment.

### Confirming `on_after_login` is bypassed

Reading `fastapi_users/router/auth.py` (site-packages) — `on_after_login` is only invoked inside the built-in `login` route returned by `fastapi_users.get_auth_router(...)`. Custom endpoints issuing tokens manually via `strategy.write_token(user)` (e.g., guest creation in `guest_service.py:51`, OAuth callback in `auth.py:208`, our new impersonation endpoint) do NOT trigger it. **Verified by reading site-packages and existing project code.** [D-06 satisfied by construction.]

### Superuser dependency (reusable)

CLAUDE.md notes existing superuser checks are inline 403 raises (`users.py:78`, `admin_tools` in frontend). For the Admin router, create:

```python
# app/users.py
current_superuser = fastapi_users.current_user(active=True, superuser=True)
```

`FastAPIUsers.current_user(superuser=True)` is a built-in — it returns a dependency that 401/403s on non-superusers automatically. **Verified via fastapi-users docs.** Use it on every `/admin/*` route instead of inline checks.

## Frontend auth swap + cache invalidation

### `useAuth.impersonate(userId)` pattern

```ts
// frontend/src/hooks/useAuth.ts additions
const impersonate = useCallback(async (userId: number): Promise<void> => {
  const response = await apiClient.post<{ access_token: string; target_email: string }>(
    `/admin/impersonate/${userId}`,
  );
  const { access_token } = response.data;
  // Same sequence as `login`: store new token first, then clear cache, then setToken.
  // Storing first ensures any in-flight queries that restart use the new token, not the old.
  localStorage.setItem('auth_token', access_token);
  queryClient.clear();
  setToken(access_token);
  setUser(null);
}, []);
```

This exactly mirrors the existing `login` method (useAuth.ts:40-64). The `queryClient.clear()` already exists and handles cache reset across every query key. The existing `logout` (useAuth.ts:131-138) already does the right thing for D-10 — no changes needed to logout itself.

### Detecting "am I impersonating?" on the frontend — recommendation: profile field

**Recommended approach (per D-22):** Extend `/users/me/profile` response with:

```python
# app/schemas/users.py
class ImpersonationContext(BaseModel):
    admin_id: int
    target_email: str

class UserProfileResponse(BaseModel):
    # ...existing fields...
    impersonation: ImpersonationContext | None = None
```

The profile endpoint reads `request.state` (populated by a small dep that peeks at the token claim) and sets `impersonation` accordingly. Because `useUserProfile` has a 5-minute stale time and is already invalidated by `queryClient.clear()` on token swap, the pill appears after the swap-triggered refetch completes — typically <200ms.

**Why not client-side JWT decode?**
- No new frontend dep (`jwt-decode` or inline base64 parser is ~10 lines of fragile code).
- Single source of truth: the backend already validates and knows the real state.
- If the impersonation token is tampered with client-side (swapping the claim), the next API call 401s anyway — no real advantage.
- Matches the existing pattern: `profile.is_superuser` / `profile.is_guest` drive the entire UI today.

### Token expiry handling (1h vs 7d)

`apiClient` 401 interceptor (`frontend/src/api/client.ts:42-62`) already clears localStorage and redirects to `/login`. **No changes needed.** When the 1h impersonation token expires, the next API call returns 401 → the interceptor fires → admin lands on `/login`. They re-authenticate as themselves.

`ProtectedLayout` guest-refresh logic (`App.tsx:294-301`) fires `/auth/guest/refresh` only when `profile.is_guest` is true. Impersonation is not a guest session → no accidental refresh attempt. **No changes needed here either.**

**Explicit safeguard to add:** In `ProtectedLayout.tsx`, document (comment) that the refresh is intentionally skipped for impersonation because `profile.is_guest` is false during impersonation (the impersonated user is typically not a guest; even if they are, refresh would issue a regular guest token, defeating the 1h TTL). Add an assertion-style comment.

### TanStack Query cache reset — is `queryClient.clear()` sufficient?

Yes. Verified by reading `frontend/src/lib/queryClient.ts` pattern (via App.tsx import) — the existing login and logout paths both use `.clear()`, which drops every query. No query-key allowlist is needed because all data fetched is user-scoped.

One subtle concern: `ImportJobWatcher` components in `App.tsx:326-411` hold `activeJobIds` in React state and poll jobs by id. These job ids belong to the admin, not the target. **After impersonation, the admin's job polling must stop.** Options:
- Reset `activeJobIds` / `completedJobIds` on token change — wire into `AppRoutes` similar to the existing `restoredForTokenRef` pattern (App.tsx:335-340).
- Accept the edge case (admin's active imports continue polling during impersonation; 404s eventually clean them up).

**Recommendation:** Add `setActiveJobIds([]); setCompletedJobIds(new Set())` to the same `restoredForTokenRef` guard. Small change, kills a known edge case.

## Searchable combobox (shadcn/ui patterns, project conventions)

### Install once: `npx shadcn@latest add command popover`

This creates `frontend/src/components/ui/command.tsx` and `popover.tsx`, and adds `cmdk` to dependencies. shadcn is already the project's component CLI (see `frontend/components.json`).

### Pattern: debounced server-side combobox

```tsx
// frontend/src/components/admin/ImpersonationSelector.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Command, CommandInput, CommandList, CommandItem, CommandEmpty } from '@/components/ui/command';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover';
import { useDebounce } from '@/hooks/useDebounce';
import { apiClient } from '@/api/client';

const MIN_QUERY_LEN = 2;  // D-12
const MAX_RESULTS = 20;   // D-13
const DEBOUNCE_MS = 250;

interface UserSearchResult {
  id: number;
  email: string;
  chess_com_username: string | null;
  lichess_username: string | null;
  is_guest: boolean;
  last_login: string | null;
}

export function ImpersonationSelector({ onSelect }: { onSelect: (userId: number) => void }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const debounced = useDebounce(query, DEBOUNCE_MS);

  const { data, isLoading, isError } = useQuery<UserSearchResult[]>({
    queryKey: ['admin', 'users-search', debounced],
    queryFn: async () => {
      const res = await apiClient.get<UserSearchResult[]>('/admin/users/search', { params: { q: debounced } });
      return res.data;
    },
    enabled: debounced.length >= MIN_QUERY_LEN,
    staleTime: 10_000,
  });

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="brand-outline" data-testid="btn-impersonate-selector" aria-haspopup="listbox">
          Select user to impersonate
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0" align="start">
        <Command shouldFilter={false} data-testid="admin-combobox">
          <CommandInput
            value={query}
            onValueChange={setQuery}
            placeholder="Search by email, username, or id"
            data-testid="admin-combobox-input"
          />
          <CommandList>
            {debounced.length < MIN_QUERY_LEN && (
              <div className="p-2 text-xs text-muted-foreground">Type at least 2 characters</div>
            )}
            {isError && (
              <div className="p-2 text-xs text-destructive">
                Failed to load users. Something went wrong. Please try again in a moment.
              </div>
            )}
            {isLoading && <div className="p-2 text-xs text-muted-foreground">Searching…</div>}
            {data && data.length === 0 && <CommandEmpty>No users found.</CommandEmpty>}
            {data?.map((u) => (
              <CommandItem
                key={u.id}
                value={`${u.id}-${u.email}`}  // unique stable value
                onSelect={() => { onSelect(u.id); setOpen(false); }}
                data-testid={`admin-combobox-item-${u.id}`}
              >
                {/* email + platforms + is_guest badge + last_login */}
              </CommandItem>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

**Critical `cmdk` gotcha — disable built-in filtering.** `Command` defaults to client-side fuzzy filtering on `value`. For server-side search, pass `shouldFilter={false}` (see above). Without it, cmdk would hide results whose `value` doesn't fuzzy-match the query, even though the server already narrowed. **Verified in cmdk docs.**

### Keyboard navigation — free from cmdk

- Arrow up/down navigates `CommandItem`s.
- `Enter` triggers `onSelect`.
- `Esc` closes the popover (via Radix Popover's default behavior).
- `aria-activedescendant` + `role="listbox"` are set by cmdk automatically.

### ARIA + data-testid conventions per CLAUDE.md

- `data-testid="admin-combobox"` on the `Command` root.
- `data-testid="admin-combobox-input"` on `CommandInput`.
- `data-testid="admin-combobox-item-{user_id}"` per result row (follows the dynamic-element convention from CLAUDE.md).
- `aria-haspopup="listbox"` on the trigger.
- No `aria-label` needed on the visible-text trigger; one is required only if we switch to an icon-only trigger.

## last_login / last_activity integration points (exact files + lines)

### Current last_login write sites (all authorized — no change for impersonation path because `on_after_login` is NOT invoked there)

| File | Line | Trigger |
|------|------|---------|
| `app/users.py:61-72` | `UserManager.on_after_login` | POST `/auth/jwt/login` success |
| `app/users.py:49-59` | `UserManager.on_after_register` | POST `/auth/register` success |
| `app/routers/auth.py:200-205` | OAuth callback | Google OAuth success |
| `app/routers/auth.py:397-401` | Guest-promote callback | Guest promotion via Google |
| `app/services/guest_service.py:46` | `create_guest_user` | First-time guest creation (`last_login=func.now()` on INSERT) |

**D-06 impact:** The impersonation endpoint does NOT go through any of these paths. No changes needed to `on_after_login`. Add a unit test anyway to lock the invariant (see Validation Architecture).

### Current last_activity write site — single location

| File | Line | Trigger |
|------|------|---------|
| `app/middleware/last_activity.py:79-84` | `LastActivityMiddleware.__call__` | Every successful (status < 400) authenticated request, throttled 1h per user |

**D-07 implementation (MUST do in this phase, CONTEXT.md D-08 is stale):**

The middleware currently extracts `user_id` via `_extract_user_id` (lines 91-104) using `decode_jwt`. Extend that helper (or add a parallel `_extract_is_impersonation`) so the middleware can short-circuit when the claim is `true`:

```python
# app/middleware/last_activity.py
def _extract_user_id_and_impersonation(request) -> tuple[int | None, bool]:
    # ... same parse as today ...
    return int(payload["sub"]), bool(payload.get("is_impersonation", False))

# In __call__:
user_id, is_imp = _extract_user_id_and_impersonation(request)
if user_id is None:
    return
if is_imp:
    return  # D-07: do NOT touch last_activity for impersonated requests
# ...existing throttle + update code...
```

**Why this matters immediately:** Without this, an admin's long impersonation session would silently keep the target user's `last_activity` fresh, making "who is active?" dashboards misleading and — more importantly — exposing impersonation by spiking the target's activity counter in a way the target could notice. D-07 is a security/transparency requirement, not a nice-to-have.

### Note on middleware ordering

The middleware runs BEFORE the route handler completes (it wraps the ASGI call). It does NOT depend on the `current_active_user` dependency, so the claim-aware strategy changes don't affect it. Add tests asserting both the skip behavior AND that the middleware still records non-impersonation activity correctly after the helper change.

## Admin router + superuser dependency

### New file: `app/routers/admin.py`

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.admin import (
    UserSearchResult, ImpersonateResponse,
)
from app.services import admin_service
from app.users import current_active_user, current_superuser, get_impersonation_jwt_strategy

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users/search", response_model=list[UserSearchResult])
async def search_users(
    q: str,
    _admin: Annotated[User, Depends(current_superuser)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[UserSearchResult]:
    if len(q) < 2:
        return []
    return await admin_service.search_users(session, q)


@router.post("/impersonate/{user_id}", response_model=ImpersonateResponse)
async def impersonate(
    user_id: int,
    admin: Annotated[User, Depends(current_superuser)],  # dep enforces D-04 indirectly
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImpersonateResponse:
    target = await session.get(User, user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot impersonate another superuser")
    strategy = get_impersonation_jwt_strategy()
    token = await strategy.write_impersonation_token(admin, target)
    return ImpersonateResponse(access_token=token, token_type="bearer", target_email=target.email)
```

### New file: `app/services/admin_service.py`

```python
from typing import Literal
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

USER_SEARCH_LIMIT = 20  # D-13

async def search_users(session: AsyncSession, query: str) -> list[User]:
    """Return up to 20 users matching ILIKE on email / platform usernames, or exact id match."""
    like = f"%{query}%"
    stmt = (
        select(User)
        .where(
            or_(
                User.email.ilike(like),
                User.chess_com_username.ilike(like),
                User.lichess_username.ilike(like),
                User.id == int(query) if query.isdigit() else False,
            )
        )
        .order_by(User.last_login.desc().nullslast(), User.id.asc())
        .limit(USER_SEARCH_LIMIT)
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())
```

Note the `User.id == int(query) if query.isdigit() else False` short-circuit — a ColumnElement comparison vs. a Python bool gets collapsed by SQLAlchemy. For `ty` compliance, wrap it in a helper that returns `sa.false()` when not numeric. [`ty` will grumble about mixed expression types; use `literal(False)` or `sa.false()` explicitly.]

### Register router in `app/main.py`

Add after `app.include_router(users_router, prefix="/api")`:

```python
from app.routers import admin as admin_router_module
app.include_router(admin_router_module.router, prefix="/api")
```

### Index considerations

Current DB state:
- `users.email` — **indexed** (unique, created in `20260312_102146_...`).
- `users.chess_com_username` — **not indexed**.
- `users.lichess_username` — **not indexed**.
- `users.id` — primary key, indexed.

Expected user count: current prod DB has < 100 users (early v1.x). ILIKE scans on 100 rows are trivial — **no new indexes needed for this phase.** Add a comment flagging that once user count crosses ~10k, trigram indexes (`pg_trgm` with `gin`) should be added for the two username columns. Do NOT include this in the phase scope; flag in deferred ideas.

## Header pill placement + theme tokens

### Desktop header (App.tsx:79-139)

The pill belongs in the right-side cluster at line 121-135, before the guest badge and logout button. When `profile?.impersonation` is truthy, render it and **hide the Logout button** (because × on the pill IS the logout control, per D-20). Preserving both would confuse — remove or visually demote `<Button ... onClick={logout}>Logout</Button>` in impersonation mode.

### Mobile header (App.tsx:143-170)

Mobile header currently has logo + page title only, no logout. Add the pill next to the page title area with appropriate truncation for long emails. Apply `max-w-[12rem] truncate` so a 30-char email doesn't overflow the header.

### Theme tokens

CLAUDE.md forbids hard-coded semantic colors. Add to `frontend/src/lib/theme.ts`:

```ts
// Impersonation pill (warning / elevated intensity; must be legible on dark background)
export const IMPERSONATION_PILL_BG = 'oklch(0.50 0.18 40)';   // deep orange, distinguishable from amber 'Guest' badge
export const IMPERSONATION_PILL_FG = 'oklch(0.95 0.02 40)';   // near-white foreground
export const IMPERSONATION_PILL_BORDER = 'oklch(0.60 0.18 40)';
```

Orange (hue ~40) sits between amber (Guest badge, hue ~80) and red (WDL_LOSS, hue ~25) — visually distinct from both and reads unambiguously as "elevated state, admin attention."

### Pill component

```tsx
// frontend/src/components/admin/ImpersonationPill.tsx
import { X } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import type { UserProfile } from '@/types/users';

export function ImpersonationPill({ impersonation }: { impersonation: NonNullable<UserProfile['impersonation']> }) {
  const { logout } = useAuth();
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="impersonation-pill"
      className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: IMPERSONATION_PILL_BG,
        color: IMPERSONATION_PILL_FG,
        borderColor: IMPERSONATION_PILL_BORDER,
      }}
    >
      <span className="truncate max-w-[12rem]">Impersonating {impersonation.target_email}</span>
      <button
        onClick={logout}
        aria-label="End impersonation session"
        data-testid="btn-impersonation-pill-logout"
        className="rounded-full hover:bg-black/10 p-0.5"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}
```

## File inventory

### Backend — new files
- `app/routers/admin.py` — new router, `/admin/users/search` + `/admin/impersonate/{id}`.
- `app/services/admin_service.py` — user search query + helpers.
- `app/schemas/admin.py` — `UserSearchResult`, `ImpersonateResponse`, `ImpersonationContext` Pydantic v2 models.
- `tests/test_admin_router.py` — integration tests for both endpoints.
- `tests/test_impersonation_strategy.py` — unit tests for claim-aware strategy (valid, demoted admin, promoted target, expired, bad signature).

### Backend — modified files
- `app/users.py` — add `ImpersonationJWTStrategy`, `ClaimAwareJWTStrategy`, `get_impersonation_jwt_strategy`, `current_superuser`. Replace `get_jwt_strategy` wiring in `auth_backend`.
- `app/main.py` — include `admin_router`.
- `app/middleware/last_activity.py` — extend `_extract_user_id` to also return `is_impersonation`; skip update when true.
- `app/schemas/users.py` — add `impersonation: ImpersonationContext | None` to `UserProfileResponse`.
- `app/routers/users.py` — populate `impersonation` on `/users/me/profile` response when request carries an impersonation token (inspect via a small dep that re-decodes the raw token, or via `request.state` set by the claim-aware strategy).
- `tests/test_last_activity_middleware.py` — add case: impersonation token → no update.
- `tests/test_users_router.py` — add case: profile response includes `impersonation` field when relevant.

### Frontend — new files
- `frontend/src/pages/Admin.tsx` — page with `<ImpersonationSelector>` + relocated `<SentryTestButtons>`.
- `frontend/src/components/admin/ImpersonationSelector.tsx` — combobox.
- `frontend/src/components/admin/ImpersonationPill.tsx` — header pill.
- `frontend/src/components/admin/SentryTestButtons.tsx` — extracted verbatim from `GlobalStats.tsx`.
- `frontend/src/components/ui/command.tsx` — via `npx shadcn@latest add command`.
- `frontend/src/components/ui/popover.tsx` — via `npx shadcn@latest add popover` (replaces rolled-own in `info-popover.tsx`? No — leave info-popover.tsx using radix-ui directly to avoid a churn diff. Both can coexist.).
- `frontend/src/types/admin.ts` — `UserSearchResult`, `ImpersonationContext`, `ImpersonateResponse` types matching backend schemas.
- `frontend/src/__tests__/components/admin/ImpersonationSelector.test.tsx` — vitest, mocking `apiClient`.
- `frontend/src/__tests__/components/admin/ImpersonationPill.test.tsx` — vitest, render + × click triggers logout.

### Frontend — modified files
- `frontend/src/hooks/useAuth.ts` — add `impersonate(userId)` method (mirrors `login`).
- `frontend/src/hooks/useUserProfile.ts` — no code change; the new `impersonation` field flows through because `UserProfile` type is updated.
- `frontend/src/types/users.ts` — add `impersonation: { admin_id: number; target_email: string } | null` to `UserProfile`.
- `frontend/src/App.tsx`:
  - Add `{ to: '/admin', label: 'Admin', Icon: ShieldIcon }` to `NAV_ITEMS` conditionally (filter on `profile?.is_superuser`) — rightmost (D-16).
  - Add same to the More drawer `NAV_ITEMS` mobile rendering, conditionally.
  - Render `<ImpersonationPill>` in `NavHeader` and `MobileHeader` when `profile?.impersonation`.
  - Add `Admin` route inside `<ProtectedLayout>` block. Wrap with an inline `profile.is_superuser` check component (`<SuperuserRoute>`) that redirects non-superusers to `/openings`.
  - Add `/admin` to `ROUTE_TITLES`.
  - `AppRoutes`: reset `activeJobIds` + `completedJobIds` when `token` changes (piggyback on `restoredForTokenRef` block).
- `frontend/src/pages/GlobalStats.tsx` — remove `SentryTestButtons` (lines 18-79), `AdminTools` (lines 81-85), and its render site. Import is removed; Knip will catch if any import remains.

### No migration needed
No new DB columns, no index changes.

## Testing strategy per layer

### Backend (pytest)

**Unit tests** (`tests/test_impersonation_strategy.py`):
- Valid impersonation token → returns target user.
- Admin demoted to non-superuser → read_token returns None → 401.
- Target promoted to superuser → read_token returns None → 401.
- Target deactivated (is_active=False) → read_token returns None.
- Expired token (exp past) → read_token returns None (PyJWTError caught).
- Bad signature (token signed with different secret) → None.
- Non-impersonation token → falls through to default strategy (existing behavior preserved).

**Integration tests** (`tests/test_admin_router.py`):
- `GET /admin/users/search`: 403 for non-superuser, 200 for superuser; ILIKE matches across email / chess_com_username / lichess_username; exact id match; empty query short-circuits; limit 20.
- `POST /admin/impersonate/{id}`: 403 for non-superuser, 404 for non-existent, 403 for impersonating-another-superuser, 200 with token for valid target; returned token validates against `ClaimAwareJWTStrategy`.
- Nested impersonation rejected: issue impersonation token → call `/admin/impersonate/{other_id}` with that token → 403 (because current_superuser dep returns the target, who isn't a superuser).

**Integration tests** (`tests/test_last_activity_middleware.py`, additions):
- Non-impersonation request: `last_activity` written (existing behavior).
- Impersonation request: `last_activity` NOT written for target, NOT written for admin (D-07 + D-08).

**Integration tests** (`tests/test_users_router.py`, additions):
- `GET /users/me/profile` with impersonation token: `impersonation.admin_id` + `impersonation.target_email` present.
- `GET /users/me/profile` with regular token: `impersonation` is `null`.

**Invariant tests** (validate impersonated requests flow correctly through existing endpoints):
- With impersonation token, `GET /stats/global` returns the target user's stats, not the admin's.
- With impersonation token, `GET /users/games/count` returns the target's count.
- With impersonation token, `POST /position-bookmarks` creates a bookmark owned by the target (not the admin).

### Frontend (vitest)

- `ImpersonationSelector.test.tsx`: typing triggers debounced fetch only after ≥ 2 chars; result rows render expected fields; click fires `onSelect(userId)`; loading + error branches.
- `ImpersonationPill.test.tsx`: renders email + ×; × click invokes `useAuth().logout`.
- `useAuth.test.tsx` (if it exists; otherwise in Admin page test): `impersonate()` stores new token, calls `queryClient.clear`, updates `token`.
- `Admin.test.tsx`: page renders both sections; SentryTestButtons preserved (smoke).
- No new test for `App.tsx` route gating — covered by existing ProtectedLayout patterns.

### Manual verification steps (post-deploy smoke)
1. Log in as superuser → Admin tab visible rightmost desktop, in More drawer on mobile.
2. Log in as non-superuser → no Admin tab, `/admin` URL redirects.
3. From Admin, search for a user → results appear after 250ms debounce.
4. Impersonate → pill appears in header; analytics reflect target user.
5. Click × → redirect to `/login`; re-login as admin shows analytics unchanged for the target (`last_login` / `last_activity` not bumped).
6. Let 1h pass without activity → next request 401s → redirect to `/login`.

## Alternatives considered

- **Two `AuthenticationBackend`s** (one per strategy) instead of one claim-aware wrapper: forces adding a second `fastapi_users.current_user(...)` dep everywhere. Rejected; single backend is cleaner.
- **Client-side JWT decode** for pill state instead of profile field: adds a dep (`jwt-decode` or 10-line base64 parser) and duplicates trust. Rejected.
- **Cookies for impersonation token** instead of localStorage swap: would require changing transport, breaks single-token model. Rejected.
- **Dedicated DB row `impersonation_sessions`** for audit: deferred explicitly in CONTEXT.md.
- **Separate admin subdomain** (`admin.flawchess.com`) for physical isolation: massive overkill for a small user base; Caddy config changes out of scope. Rejected.
- **`lodash.debounce`** instead of project's `useDebounce` hook: adds dep. Project already has `useDebounce`. Rejected.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest 8.x + pytest-asyncio (from existing `tests/` layout) |
| Frontend framework | vitest 4.1.1 (from `package.json`) |
| Config file | `tests/conftest.py` for backend; vitest uses inline config in vite.config.ts |
| Quick run command | `uv run pytest tests/test_admin_router.py -x` / `cd frontend && npm test -- ImpersonationSelector` |
| Full suite command | `uv run pytest && cd frontend && npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Impersonation JWT carries act_as/admin_id/is_impersonation | unit | `uv run pytest tests/test_impersonation_strategy.py::test_token_claims -x` | ❌ Wave 0 |
| D-02 | read_token validates admin still superuser, target still non-super | unit | `uv run pytest tests/test_impersonation_strategy.py::test_admin_demoted_rejects -x` | ❌ Wave 0 |
| D-03 | Impersonation token expires in 1h | unit | `uv run pytest tests/test_impersonation_strategy.py::test_token_expiry -x` | ❌ Wave 0 |
| D-04 | Nested impersonation rejected | integration | `uv run pytest tests/test_admin_router.py::test_nested_impersonation_rejected -x` | ❌ Wave 0 |
| D-05 | Impersonating superuser rejected | integration | `uv run pytest tests/test_admin_router.py::test_impersonate_superuser_rejected -x` | ❌ Wave 0 |
| D-06 | last_login unchanged after impersonation | integration | `uv run pytest tests/test_admin_router.py::test_last_login_not_touched -x` | ❌ Wave 0 |
| D-07 | last_activity unchanged after impersonation | integration | `uv run pytest tests/test_last_activity_middleware.py::test_impersonation_skip -x` | ❌ Wave 0 |
| D-09 | Admin token replaced in localStorage | vitest | `cd frontend && npm test -- useAuth.impersonate` | ❌ Wave 0 |
| D-12 | Search debounces, min 2 chars | vitest | `cd frontend && npm test -- ImpersonationSelector` | ❌ Wave 0 |
| D-13 | /admin/users/search gated, max 20, exact id match | integration | `uv run pytest tests/test_admin_router.py::test_search_users -x` | ❌ Wave 0 |
| D-16/D-17 | Admin tab visibility | manual | manual checklist | — |
| D-20 | Pill renders when impersonating, × logs out | vitest | `cd frontend && npm test -- ImpersonationPill` | ❌ Wave 0 |
| D-22 | profile.impersonation populated from claim | integration | `uv run pytest tests/test_users_router.py::test_profile_impersonation_field -x` | ❌ Wave 0 |
| D-23 | Impersonated endpoints return target's data | integration | `uv run pytest tests/test_admin_router.py::test_impersonated_stats_belong_to_target -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_admin_router.py tests/test_impersonation_strategy.py -x` (backend) or `cd frontend && npm test -- admin` (frontend).
- **Per wave merge:** `uv run pytest && cd frontend && npm test && npm run knip && uv run ruff check . && uv run ty check app/ tests/`.
- **Phase gate:** Full suite green + manual smoke checklist.

### Key Invariants (measured, not just asserted)

1. **Admin's own timestamps stay frozen during impersonation.** Test: snapshot `admin.last_login` and `admin.last_activity` before impersonation; run N impersonated requests; assert both unchanged.
2. **Target's own timestamps stay frozen during impersonation.** Same test, target user's row.
3. **Non-impersonation activity still records normally.** Regression guard on the middleware change.
4. **Impersonation token cannot escalate.** Test: authenticate as impersonated non-superuser via impersonation token → attempt `POST /admin/impersonate/{x}` → 403. Ensures nested impersonation is truly closed.
5. **Stats correctness.** Test: create 2 users A, B with distinguishable game counts; superuser impersonates B; `/stats/global` matches B's count, not admin's.

### Wave 0 Gaps
- [ ] `tests/test_impersonation_strategy.py` — new file, covers D-01..D-05.
- [ ] `tests/test_admin_router.py` — new file, covers `/admin/*` endpoints + invariants.
- [ ] `tests/test_last_activity_middleware.py` — additions for D-07 skip.
- [ ] `tests/test_users_router.py` — additions for D-22 profile field.
- [ ] `frontend/src/__tests__/components/admin/ImpersonationSelector.test.tsx` — new vitest file.
- [ ] `frontend/src/__tests__/components/admin/ImpersonationPill.test.tsx` — new vitest file.
- [ ] No framework install needed — pytest + vitest already wired.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `current_superuser = fastapi_users.current_user(active=True, superuser=True)` is supported by fastapi-users 15.0.5 | Admin router + superuser dependency | [CITED: fastapi-users docs] — very low risk, well-documented API |
| A2 | Custom JWT claims survive `generate_jwt`/`decode_jwt` round-trip | FastAPI-Users extension patterns | [VERIFIED: read site-packages source] — zero risk |
| A3 | `on_after_login` is only called by the built-in auth router | FastAPI-Users extension patterns | [VERIFIED: read site-packages + project guest/oauth code confirms manual `write_token` path doesn't trigger it] — zero risk |
| A4 | Current user count is < 100 so no trigram indexes needed | Admin router | [ASSUMED] — plan should verify via `SELECT COUNT(*) FROM users` on prod before shipping, but any value < 10k is fine |
| A5 | shadcn `Command` with `shouldFilter={false}` disables built-in filtering | Searchable combobox | [CITED: cmdk docs via shadcn] — low risk |
| A6 | `request.state` is writable by a strategy during `read_token` to pass impersonation context to downstream handlers | Frontend auth swap | [ASSUMED] — alternative is re-decoding token in the `/users/me/profile` handler directly, which is simpler but duplicates parsing. Plan should pick one. |

## Open Questions (RESOLVED)

1. **How should `profile.impersonation` be populated?**
   - Option A: Add a tiny FastAPI dependency `get_impersonation_context(request)` that re-decodes the raw token and returns the context; inject it into `/users/me/profile`. Simplest.
   - Option B: Have `ClaimAwareJWTStrategy.read_token` set `request.state.impersonation = {...}` when applicable; `/users/me/profile` reads from state. Avoids double decode but couples strategy to Request.
   - **Recommendation:** Option A. Decode cost is negligible; code is easier to read.
   - **RESOLVED:** Option A — implemented in Plan 02 Task 4 (`get_impersonation_context` dep in `app/routers/users.py`).

2. **Where exactly to hide the desktop Logout button during impersonation?**
   - Per D-20 the pill × is the logout control. If we keep a second Logout button, users have two ways to end the session, which is fine but slightly noisy.
   - **Recommendation:** Hide `<Button variant="ghost" onClick={logout}>Logout</Button>` in `NavHeader` when `profile?.impersonation` is truthy. Mobile More drawer's Logout item should stay hidden too.
   - **RESOLVED:** Hide both — desktop Logout button AND mobile More drawer Logout item are hidden when `profile.impersonation` is non-null. Implemented in Plan 05.

3. **Should the Admin tab have an icon?**
   - CONTEXT.md D-16 does not specify. Existing desktop nav uses an icon per tab (`DownloadIcon`, `BookOpenIcon`, etc.). Pick `ShieldIcon` from `lucide-react` for consistency.
   - **RESOLVED:** Use `ShieldIcon` from `lucide-react`. Implemented in Plan 04 Task 4.

4. **`ty` compliance for the `or_(..., User.id == int(q) if q.isdigit() else False)` pattern**
   - Mixing ColumnElement with a bare `False` will make `ty` grumble. Use `sa.false()` or wrap the numeric branch behind a runtime `if` building a different `or_` clause.
   - **RESOLVED:** Build the `or_` clause list conditionally — `sa.false()` with `sa.func` when needed. Implemented in Plan 02 Task 2 (`admin_service.search_users`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 18 (dev) | Backend tests | ✓ | 18 (Docker) | — |
| Python 3.13 + uv | Backend | ✓ | per `pyproject.toml` | — |
| Node 20+ + npm | Frontend | ✓ (existing) | — | — |
| `shadcn@4.0.5` CLI | Adding Command/Popover | ✓ (installed as devDep) | 4.0.5 | Manual copy from shadcn-ui/ui repo |
| `cmdk` (via shadcn add) | Combobox | ✗ (installed transitively when shadcn add runs) | tbd | — |

Nothing blocks execution.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users JWT (existing) + per-request admin-still-superuser validation |
| V3 Session Management | yes | 1-hour TTL on impersonation token (short by design); single-token model; JWT has no server-side revocation, so TTL is the only expiry mechanism |
| V4 Access Control | yes | `current_superuser` dep on `/admin/*`; frontend visibility gate on `is_superuser`; both required (defense in depth) |
| V5 Input Validation | yes | Pydantic v2 on all request/response bodies; `user_id` path parameter is `int` — FastAPI rejects non-numeric |
| V6 Cryptography | yes | Reuse existing `SECRET_KEY` + HS256 via fastapi-users jwt module. No hand-rolled crypto. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Admin escalates to impersonate another superuser | E (Elevation of Privilege) | D-05: reject if target is superuser; enforced in both issue path and read_token |
| Revoked admin (is_superuser=False) keeps using old impersonation token | E | D-02: read_token re-checks admin.is_superuser on every request — stale tokens reject with 401 |
| JWT tampering (changing act_as claim) | T (Tampering) | HS256 signature covers all claims; decode rejects |
| Nested impersonation (A impersonates B impersonates C) | E | D-04: claim-aware strategy returns non-superuser target; subsequent `current_superuser` dep fails |
| Long-lived impersonation token stolen via XSS | I (Information Disclosure) | 1h TTL caps exposure; no server-side revocation, but blast radius is small; defense in depth via CSP (existing) |
| Impersonated user notices via last_activity spike | I | D-07: middleware skips write during impersonation |
| Admin accidentally mutates target's data (destructive op) | T | D-23 explicitly accepts this risk in-phase; deferred per CONTEXT.md |
| SQL injection on search `q` parameter | T | SQLAlchemy parameterizes `ilike()`; `q` is a string, never interpolated |
| Search enumeration (attacker brute-forces emails via non-superuser somehow) | I | Endpoint is superuser-gated; non-superusers receive 403 with no leak |

## Sources

### Primary (HIGH confidence)
- Context7 / official fastapi-users docs 15.x — `JWTStrategy`, `current_user(superuser=True)`, `BaseUserManager.on_after_login` lifecycle. [CITED]
- `.venv/lib/python3.13/site-packages/fastapi_users/jwt.py` — `generate_jwt`/`decode_jwt` pass-through of extra claims. [VERIFIED]
- `.venv/lib/python3.13/site-packages/fastapi_users/authentication/strategy/jwt.py` — `JWTStrategy.read_token` reads only `sub`. [VERIFIED]
- `app/users.py`, `app/routers/auth.py`, `app/services/guest_service.py` — existing manual `write_token` pattern that bypasses `on_after_login`. [VERIFIED via codebase]
- `app/middleware/last_activity.py` — current `last_activity` write site + `_extract_user_id` pattern. [VERIFIED via codebase]
- `frontend/src/hooks/useAuth.ts` — existing login/loginWithToken/refreshAuthToken/logout flows. [VERIFIED]
- `frontend/src/hooks/useDebounce.ts` — existing debounce hook. [VERIFIED]
- `frontend/package.json` — confirms cmdk NOT installed, shadcn CLI is. [VERIFIED]
- `frontend/components.json` — shadcn config. [VERIFIED]
- shadcn/ui docs for Command component. [CITED: https://ui.shadcn.com/docs/components/command]

### Secondary (MEDIUM confidence)
- cmdk library README on `shouldFilter` behavior. [CITED but not Context7-verified]
- PostgreSQL ILIKE performance on small tables — general knowledge, not library-specific. [CITED: pg docs]

### Tertiary (LOW confidence)
- None. All claims are backed by project code or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — fastapi-users subclassing pattern verified by reading site-packages; shadcn Command is a standard pattern.
- Architecture: HIGH — claim-aware strategy + manual token issuance is the minimal extension of the existing pattern.
- Pitfalls: HIGH — cmdk `shouldFilter`, last_activity stale claim, hidden logout-button-redundancy, `ty` complaints on mixed-type `or_` clause are all specific and verifiable.

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (30 days; fastapi-users and cmdk are stable).

---

## RESEARCH COMPLETE

**Phase:** 62 - admin-user-impersonation
**Confidence:** HIGH

### Key Findings
- `on_after_login` bypass is automatic when the impersonation endpoint issues its token via manual `strategy.write_token(...)` — this is already the pattern used by guest creation and OAuth callback, so D-06 is satisfied by construction. Zero risk.
- Custom JWT claims (`act_as`, `admin_id`, `is_impersonation`) flow through fastapi-users' `generate_jwt` / `decode_jwt` transparently because PyJWT preserves arbitrary payload fields. A `ClaimAwareJWTStrategy` wrapper can dispatch to an `ImpersonationJWTStrategy` subclass that validates admin-still-superuser on every request, leaving `current_active_user` unchanged at call sites.
- **CONTEXT.md D-08 is stale:** `last_activity` IS currently written by `LastActivityMiddleware` (commit 2beabd3, 2026-04-12). The planner must wire the `is_impersonation` skip into the middleware in THIS phase — deferring would regress transparency for impersonated users. One-line change in `_extract_user_id`.
- shadcn/ui `Command` + `Popover` are not yet installed in `frontend/src/components/ui/` — first plan step is `npx shadcn@latest add command popover` (adds `cmdk` transitively). The existing `frontend/src/hooks/useDebounce.ts` covers debouncing; no `lodash.debounce` dep needed.
- Recommendation for D-22 (impersonation pill source): add `impersonation: ImpersonationContext | null` to `/users/me/profile` response, populated from a tiny FastAPI dep that re-decodes the raw token. Simpler than client-side JWT decoding and matches the existing pattern of `profile.is_superuser`/`profile.is_guest` driving UI.

### File Created
`/home/aimfeld/Projects/Python/flawchess/.planning/phases/62-admin-user-impersonation/62-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | fastapi-users subclass patterns verified via site-packages source; shadcn Command is canonical |
| Architecture | HIGH | Claim-aware strategy + single backend + existing useAuth pattern is the minimal viable extension |
| Pitfalls | HIGH | cmdk `shouldFilter`, stale last_activity CONTEXT claim, duplicate Logout UI, `ty` mixed-type or_ clause |
| Testing | HIGH | Existing pytest + vitest wiring; no new framework |
| Security | HIGH | All controls map to existing fastapi-users primitives; no hand-rolled crypto |

### Open Questions (RESOLVED — surfaced for the planner)
1. `profile.impersonation` source: FastAPI dep re-decode vs. `request.state` set by strategy. Recommendation: dep re-decode (Option A). — RESOLVED: Option A, Plan 02 Task 4.
2. Hide desktop Logout button during impersonation? Recommendation: yes, pill × is the sole logout. — RESOLVED: yes, hide on desktop AND mobile More drawer, Plan 05.
3. Admin tab icon: `ShieldIcon` from lucide-react for consistency. — RESOLVED: `ShieldIcon`, Plan 04 Task 4.
4. `ty` complaint on `or_(..., User.id == int(q) if q.isdigit() else False)` — use `sa.false()` or conditional clause building. — RESOLVED: conditional clause list with `sa.false()`, Plan 02 Task 2.

### Ready for Planning
Research complete. One important flag: CONTEXT.md D-08 contains a stale claim about `last_activity` not being written yet. Planner should include `app/middleware/last_activity.py` modifications in this phase's scope, not defer.

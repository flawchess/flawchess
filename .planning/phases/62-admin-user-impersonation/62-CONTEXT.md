# Phase 62: Admin user impersonation - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Superusers can log in as any non-superuser user, see analytics from that user's perspective, and perform any action the user can. The impersonated user's `last_login` / `last_activity` timestamps remain untouched. The session ends on logout.

A new **Admin** tab hosts the impersonation selector and absorbs the existing **Sentry Error Test** section currently shown at the bottom of the Global Stats page.

In scope:
- Backend: impersonation token issuance endpoint, JWT claim changes, user search endpoint
- Auth: suppress `last_login` / `last_activity` writes when the JWT is an impersonation token
- Frontend: Admin tab (desktop nav + mobile More drawer), user search combobox, impersonation pill in header, wiring the impersonation flow into `useAuth`
- Relocation: move the existing `SentryTestButtons` / `AdminTools` UI from `GlobalStats.tsx` into the new Admin tab

Out of scope (tracked below as deferred):
- Audit logging of impersonation sessions in a dedicated table
- Recently-impersonated history list
- Token revocation / blacklist infrastructure
- Blocking destructive account operations during impersonation (password change, account delete) — the phase spec says admin can do anything the user can

</domain>

<decisions>
## Implementation Decisions

### Impersonation mechanism
- **D-01:** Impersonation is carried by a **dedicated JWT** issued on `POST /admin/impersonate/{user_id}` (exact path TBD during planning). Token claims include at minimum: `sub = impersonated_user_id`, `act_as = impersonated_user_id`, `admin_id = admin_user_id`, `is_impersonation = true`. Rationale: reuses the existing FastAPI-Users Bearer + JWTStrategy stack, is auditable from the token alone, and keeps every downstream `current_active_user` dependency unchanged.
- **D-02:** A custom `JWTStrategy.read_token` (or equivalent dependency wrapper) validates: `admin_id` resolves to an active superuser, `act_as` resolves to an active non-superuser, and the admin is still `is_superuser = true` at request time. If any check fails → 401. This prevents "admin loses superuser flag" from silently continuing the session.
- **D-03:** Impersonation token lifetime = **1 hour**, independent of the regular 7-day JWT lifetime. Regular tokens and guest tokens keep their current lifetimes.
- **D-04:** The impersonation endpoint requires the caller's current JWT to be a normal (non-impersonation) superuser token. Nested impersonation is rejected with 403.
- **D-05:** Impersonating another superuser is rejected with 403.

### last_login / last_activity suppression
- **D-06:** `UserManager.on_after_login` must **not** update `last_login` when the login flow originates from impersonation. Since impersonation does not go through the standard login endpoint but through `/admin/impersonate`, the simplest implementation is: do NOT call `on_after_login` from the impersonation path, and only write `last_login` inside the existing login + OAuth flows.
- **D-07:** `last_activity` IS already tracked today via `LastActivityMiddleware` at `app/middleware/last_activity.py` (commit 2beabd3, 2026-04-12) — flagged by research after CONTEXT.md was first drafted. The middleware must be modified in THIS phase to skip the write when the request's JWT has `is_impersonation=true`. One-line change in `_extract_user_id` or equivalent. Not deferrable.
- **D-08:** We do NOT track the admin's own `last_activity` during impersonation in this phase. Deferred.

### Session lifecycle
- **D-09:** **Single-token model.** At impersonation start, the admin's own JWT in `localStorage['auth_token']` is replaced by the impersonation JWT. Admin does not keep their original token anywhere.
- **D-10:** Ending an impersonation session = **clicking the × in the impersonation pill = the existing `useAuth.logout()` path.** It clears `localStorage['auth_token']`, clears TanStack Query cache, redirects to `/login`. Admin must re-authenticate as themselves to start a new impersonation.
- **D-11:** No "Stop impersonating" return-to-admin flow. Matches the phase spec ("The impersonation session ends on logout") and avoids dual-token state management.

### User selector UX
- **D-12:** Searchable combobox with **server-side** search (debounced, min 2 chars). Match against `email` + `chess_com_username` + `lichess_username` (case-insensitive LIKE or ILIKE) + exact match on numeric `id`.
- **D-13:** New backend endpoint (path TBD during planning, e.g. `GET /admin/users/search?q=...`) returns a small list (cap at 20 results). Response includes per user: `id`, `email`, `chess_com_username`, `lichess_username`, `is_guest`, `last_login`. Gated on `current_active_user` + `is_superuser` check — reject 403 otherwise.
- **D-14:** Each result row displays enough to disambiguate (email + platforms + is_guest badge + last_login). Clicking a row triggers impersonation and navigates to the Openings (or default) tab as the impersonated user.
- **D-15:** No "recently impersonated" list in this phase — deferred.

### Admin tab placement
- **D-16:** Desktop: Admin is the **rightmost top-nav tab**, rendered only when `profile.is_superuser === true`. Non-superusers never see the tab (not just 403-guarded on the route).
- **D-17:** Mobile bottom nav stays 4 tabs (Import / Openings / Endgames / Global Stats). Admin lives in the **More drawer**, also gated on `is_superuser`.
- **D-18:** Route: `/admin` (exact path TBD during planning). Protected by the existing `ProtectedLayout` plus an additional `is_superuser` check — 403 / redirect for non-superusers who type the URL directly.
- **D-19:** Admin page contains two sections: (1) **Impersonate user** with the combobox + result list, (2) **Sentry Error Test** — the existing `SentryTestButtons` component moved verbatim from `GlobalStats.tsx`. The `AdminTools` wrapper and its `is_superuser` gate on the Global Stats page are removed, since the Admin tab itself is gated.

### Impersonation pill
- **D-20:** When an impersonation token is active, render a distinct-color pill in the header (both desktop and mobile header): `Impersonating {email} ×`. The × acts as the logout control for this session.
- **D-21:** No top banner. No sticky-layout displacement. No browser tab title change. The pill is the sole visual indicator.
- **D-22:** The pill is derived from a new field on `/users/me/profile` or a decoded JWT claim exposed to the frontend — planner to pick the cleanest approach. Most likely: add `impersonation: { admin_id, target_email }` to the profile response when the request's JWT has `is_impersonation=true`.

### Scope of actions
- **D-23:** While impersonating, admin has the **full user action surface**: create/delete bookmarks, trigger imports, delete games, etc. No per-endpoint carveouts for "admin destructive ops" in this phase.

### Claude's Discretion
- Exact REST paths (`/admin/impersonate/{id}`, `/admin/users/search`, frontend route `/admin`) — planner/implementation picks.
- Exact combobox component to use (shadcn/ui Command + Popover likely, since that's the existing stack).
- Pill color — pick something that reads as "warning / elevated" and works in both themes.
- How the frontend discovers "I am in an impersonation session" — whether via a JWT claim decoded client-side or via a field on the profile response.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### FastAPI-Users + auth stack
- `app/users.py` — existing `UserManager`, `BearerTransport`, `JWTStrategy`, `current_active_user`. Extension point for impersonation token lifetime + claims.
- `app/models/user.py` — User model, `is_superuser`, `is_guest`, `last_login`, `last_activity` fields.
- `app/routers/auth.py` — built-in FastAPI-Users auth router (`/auth/jwt/login`, `/auth/register`, `/auth/jwt/logout`).
- `app/routers/users.py` — `/users/me/profile` (line ~30), existing superuser-guarded `/users/sentry-test-error` (line ~78) — pattern to follow.

### Frontend auth + nav
- `frontend/src/hooks/useAuth.ts` — token in `localStorage['auth_token']`, `AuthProvider` context, `login / loginWithToken / logout / refreshAuthToken`. Impersonation flow likely hangs off a new `impersonate(userId)` method here.
- `frontend/src/hooks/useUserProfile.ts` — calls `/users/me/profile`, 5-minute cache. Needs to be invalidated on impersonation start/end.
- `frontend/src/App.tsx` — desktop nav (lines ~48-53, ~93-119), mobile bottom nav (~55-60, ~185-207), `ProtectedLayout` (~272-319), routes (~388-405). Admin tab added here.
- `frontend/src/pages/GlobalStats.tsx` — source of the `SentryTestButtons` (lines 18-79) and `AdminTools` wrapper (~81-85) being relocated.

### Project-level
- `CLAUDE.md` — communication style, no-scope-creep, theme constants in `frontend/src/lib/theme.ts`, `data-testid` / ARIA rules for new interactive elements, Sentry rules (expected errors like 403 on non-superuser attempts should NOT be captured).
- `.planning/PROJECT.md` — stack + key decisions.
- `.planning/STATE.md` — milestone context.

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`is_superuser` flag** on the User model is already wired end-to-end (DB column → `/users/me/profile` response → `profile.is_superuser` in the frontend). No schema change needed for the admin check itself.
- **`SentryTestButtons` component** (`GlobalStats.tsx:18-79`) is self-contained — can be extracted to its own file and imported by both the old location (during transition) and the new Admin page, or moved outright.
- **`AdminTools` gate pattern** (`GlobalStats.tsx:81-85`) demonstrates the `profile?.is_superuser` guard style; reuse for the Admin tab visibility and the Admin route guard.
- **`BearerTransport` + `JWTStrategy`** (`app/users.py` lines 85-103) already supports custom lifetimes (guest tokens use 365d). Adding a 1h lifetime variant is a known pattern.
- **`ProtectedLayout`** (`App.tsx:272-319`) wraps protected routes; Admin route can either wrap in an additional `SuperuserLayout` or inline-check inside the Admin page.
- **shadcn/ui Command / Popover** should be available given the existing stack — planner to confirm and use for the user search combobox.

### Established Patterns
- **Per-endpoint user scoping** — every stats/analysis endpoint uses `Depends(current_active_user)` and passes `user.id` to the service. Impersonation works transparently here because the dependency returns the impersonated User row.
- **JWT transport = Bearer, storage = localStorage** — no cookie/CSRF plumbing to touch.
- **No server-side session store, no token revocation** — we are keeping it that way; impersonation expiry is TTL-only.
- **Superuser-guarded endpoints** currently return 403 via inline check, not a dependency. We may want a small `current_superuser` dependency for the new admin endpoints — planner's call.

### Integration Points
- Backend: new `app/routers/admin.py` (or similar) for `/admin/*` endpoints.
- Backend: likely a new `app/services/admin_service.py` for user search + impersonation token issuance.
- Backend: `UserManager.on_after_login` — confirm it is NOT called from the impersonation path.
- Frontend: new `frontend/src/pages/Admin.tsx`, new `frontend/src/components/admin/ImpersonationSelector.tsx`, new `frontend/src/components/admin/ImpersonationPill.tsx` (or integrated into the header component).
- Frontend: `useAuth` gets a new `impersonate(userId)` method and a way to expose "currently impersonating" state to the UI.
- Frontend: `GlobalStats.tsx` loses `AdminTools` + `SentryTestButtons` rendering.

</code_context>

<specifics>
## Specific Ideas

- "Impersonating USER ×" pill is the sole indicator — no banner, no tab title change.
- Pill × is literally the logout control (single-token model, logout ends the session).
- User search results show enough metadata to disambiguate users with similar emails/usernames.
- 1-hour impersonation TTL is a deliberate security tradeoff — a leaked admin-issued impersonation token has a much smaller blast radius than the normal 7-day JWT.

</specifics>

<deferred>
## Deferred Ideas

- **Impersonation audit log** — dedicated table recording (admin_id, target_user_id, started_at, ended_at, request counts). Likely its own phase once this one ships and we see real usage. Would also be the right place to add per-request action logging.
- **"Stop impersonating" return-to-admin button** — dual-token UX. Not needed given the 1h TTL + easy re-login.
- **Recently impersonated list** on the Admin page — minor QoL.
- **Blocking destructive account ops while impersonating** (DELETE /users/me, change password). Phase spec explicitly says "any action the user can". Revisit if admin mistakes cause user data loss.
- **Admin's own last_activity tracking during impersonation** — once `last_activity` is actually being written somewhere (it isn't today), wire the impersonation-aware skip at the same time.
- **Browser tab title / favicon change during impersonation** — helpful with many open tabs, but cosmetic. Defer.

### Reviewed Todos (not folded)
- `2026-03-11-bitboard-storage-for-partial-position-queries` (area: database) — unrelated to impersonation; the todo matcher false-matched on the generic keywords "users" / "games". Stays in backlog.

</deferred>

---

*Phase: 62-admin-user-impersonation*
*Context gathered: 2026-04-17*

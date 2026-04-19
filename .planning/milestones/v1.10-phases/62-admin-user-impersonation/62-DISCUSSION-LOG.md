# Phase 62: Admin user impersonation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 62-admin-user-impersonation
**Areas discussed:** Impersonation mechanism, Session lifecycle, User selector UX, Admin tab + pill + safety

---

## Impersonation mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| JWT claims (Recommended) | Dedicated impersonation JWT with `sub`/`act_as`/`admin_id`/`is_impersonation` claims; reuses FastAPI-Users stack | ✓ |
| X-Act-As header | Admin keeps own JWT, sends `X-Act-As-User-ID` header; touches every endpoint dependency | |
| Session table | Server-side `impersonation_sessions` table with UUID token; most auditable but heavy | |

**User's choice:** JWT claims

---

## Last login / last activity handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip both (Recommended) | `UserManager.on_after_login` does NOT update `last_login` when JWT has `is_impersonation=true`; future `last_activity` tracking checks same flag | ✓ |
| Update admin's, skip user's | Bump admin's `last_activity` during impersonation, leave user's untouched | |
| You decide | Claude picks | |

**User's choice:** Skip both

---

## Session lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Dual-token, 'Stop impersonating' | Admin's original token kept in sessionStorage; Stop button restores it | |
| Single-token, logout-only (Recommended) | Impersonation JWT replaces admin JWT; logout clears it and redirects to /login | ✓ |
| Dual-token but no persistence | Admin's token in memory only; refresh drops it | |

**User's choice:** Single-token, logout-only

---

## Impersonation TTL

| Option | Description | Selected |
|--------|-------------|----------|
| Short (1 hour) (Recommended) | Impersonation JWTs expire after 1h regardless of admin's 7-day token | ✓ |
| Match regular (7 days) | Same lifetime as regular user JWTs | |
| You decide | Claude picks | |

**User's choice:** Short (1 hour)

---

## User selector UX

| Option | Description | Selected |
|--------|-------------|----------|
| Searchable combobox (Recommended) | Server-side search, debounced, min 2 chars; results drop down with metadata | ✓ |
| Paginated user table | Full table with columns + filters + per-row Impersonate button | |
| Combobox + recent list | Combobox plus localStorage-backed recent-impersonations list | |

**User's choice:** Searchable combobox

---

## Search match fields (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Email (Recommended) | Primary user identifier | ✓ |
| chess.com username | Users often identify by their chess.com handle | ✓ |
| lichess username | Same for lichess | ✓ |
| User ID | Exact numeric ID match, useful for Sentry issues | ✓ |

**User's choice:** All four

---

## Admin tab placement

| Option | Description | Selected |
|--------|-------------|----------|
| Last desktop tab + More drawer (Recommended) | Desktop: rightmost top-nav tab, is_superuser gated. Mobile: in More drawer, not bottom bar | ✓ |
| Last tab in desktop AND mobile bottom nav | Adds 5th icon to mobile bottom bar for superusers | |
| Dropdown off user menu | Requires adding a user menu dropdown first | |

**User's choice:** Last desktop tab + More drawer

---

## Impersonation indicator

| Option | Description | Selected |
|--------|-------------|----------|
| Top banner with Stop button (Recommended, initially) | Persistent banner at top of every protected page | (withdrawn after user flagged sticky-layout conflict) |
| Header color change + small pill | Less intrusive, easier to miss | |
| Banner + favicon/title change | Banner plus browser tab title swap | |

**User feedback on initial options:** asked how banner would interact with existing sticky containers (chessboard, sticky top row on mobile/desktop).

**Reformulated as pill-only options:**

| Option | Description | Selected |
|--------|-------------|----------|
| Header pill with Stop button (Recommended) | Compact pill in header (desktop + mobile): `Impersonating USER ×`. × is the logout control. Distinct color. No banner, sticky layouts unaffected | ✓ |
| Header pill, no stop button | Pill is purely informational; end via normal Logout | |
| Header pill + tab title prefix | Pill plus browser tab title becomes `[AS USER] FlawChess` | |

**User's choice:** Header pill with Stop button

---

## Safety rails (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Block impersonating other superusers (Recommended) | Reject if target.is_superuser is true | ✓ |
| Block nested impersonation (Recommended) | Reject /impersonate if caller's JWT is already impersonation | ✓ |
| All user actions available | Admin acting as user can do anything the user can | ✓ |
| Block destructive account ops | Block DELETE /users/me + change-password during impersonation | (not selected — conflicts with "all user actions" + phase spec) |

**User's choice:** Block other superusers + block nested impersonation + all user actions available

---

## Claude's Discretion

- Exact REST paths for the new admin endpoints
- Exact combobox component (likely shadcn/ui Command + Popover)
- Pill color
- How the frontend detects "I am impersonating" (JWT claim decoded client-side vs field on the profile response)

## Deferred Ideas

- Impersonation audit log table
- Dual-token "Stop impersonating" return-to-admin flow
- Recently-impersonated list
- Blocking destructive account ops during impersonation
- Admin's own last_activity tracking during impersonation
- Browser tab title / favicon change during impersonation

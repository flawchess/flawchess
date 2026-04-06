# Project Research Summary

**Project:** FlawChess v1.8 — Guest Access
**Domain:** Anonymous user / guest access with account promotion on existing FastAPI-Users app
**Researched:** 2026-04-06
**Confidence:** HIGH

## Executive Summary

FlawChess v1.8 adds guest access — letting visitors use the full platform without signing up and promoting to a full account at any time with all data preserved. The research is unambiguous: a read-only guest mode would be worthless (no imported games means no WDL stats, so guests experience zero value and have no reason to sign up). The only viable guest mode is full platform access backed by a real DB row per guest. The recommended approach is to create a `User` row with `is_guest=True` and a synthetic email, issue a standard Bearer JWT (stored in localStorage like all other sessions), and keep guests in the same `users` table so that account promotion is a single-row UPDATE with no FK migration needed.

No new Python or npm packages are required. The entire feature is built on existing infrastructure: FastAPI-Users 15.0.5 (already installed), SQLAlchemy async (existing ORM), the existing Bearer JWT strategy, and the existing `useAuth` context. The only schema addition is an `is_guest: bool` column on `users` (Alembic migration). The primary architecture decision confirmed by both ARCHITECTURE and PITFALLS research is to use Bearer transport for guest tokens — not `CookieTransport` — to avoid dual-transport complexity, CSRF requirements, and browser tracking-protection issues with HttpOnly cookies during the OAuth redirect round-trip.

The highest-risk item in the feature is the Google SSO promotion path. An existing CVE (CVE-2025-68481) in FastAPI-Users affects the current OAuth callback implementation in `app/routers/auth.py`, which lacks double-submit CSRF cookie validation. This must be fixed before adding the guest promotion Google SSO path. The Google SSO promotion also requires the guest `user_id` to be embedded in the OAuth `state` JWT so it survives the redirect round-trip — the guest cookie cannot be relied upon in the callback. These two requirements drive the recommended phase ordering below.

## Key Findings

### Recommended Stack

No new dependencies are needed. The v1.7 stack handles this feature entirely. The key insight from stack research is that `CookieTransport` from FastAPI-Users — while technically available — should NOT be used for guest sessions. Using it alongside the existing `BearerTransport` creates a dual-transport system requiring `allow_credentials=True` on CORS, CSRF protection on all state-changing endpoints, and introduces browser tracking-protection risks during OAuth. The simpler, safer path is to issue guest JWTs as Bearer tokens stored in localStorage, identical to registered user sessions.

**Core technologies (no additions — all existing):**
- `FastAPI-Users 15.0.5`: guest creation via `user_manager.create()`, existing Bearer JWT strategy reused for guest tokens
- `SQLAlchemy 2.x async`: `is_guest: Mapped[bool]` column added to `User` model via Alembic migration
- `Axios 1.13.6`: no changes; Bearer interceptor already handles guest JWTs transparently
- `React 19 / useAuth context`: extended with `isGuest: boolean` state and `promoteGuest()` action

### Expected Features

**Must have (table stakes — v1.8 launch):**
- "Use as Guest" button on homepage — single click, no form, no friction
- Persistent guest session (30-day JWT, real DB row) surviving page refresh
- Full platform access: import, move explorer, endgame analysis, bookmarks
- Non-dismissible guest status indicator in the header/navbar at all times
- Account promotion via email/password — atomic in-place row UPDATE, fresh JWT issued
- Account promotion via Google SSO — custom promotion path, not `user_manager.oauth_callback`
- Explicit "claim this guest data?" confirmation before promotion
- Import page info box explaining sign-up benefits (cross-device, no expiry, account recovery)
- Post-promotion redirect back to the page the user was on

**Should have (competitive differentiators — v1.8.x after validation):**
- Expiry countdown in guest banner (last 7 days only, avoid premature alarm)
- Context-sensitive promotion prompt triggered after first import completes
- Periodic cleanup job for expired guest accounts (40-day TTL)

**Defer (v2+):**
- Guest session analytics / conversion funnel metrics (requires Umami event tracking)
- "Share this position" feature gated behind promotion CTA

**Anti-features to explicitly avoid:**
- Read-only guest mode — defeats the purpose entirely; no value experienced = no conversion
- Mandatory email capture before guest access — disguised login wall
- Dismissible guest banner — causes surprise data loss; trust violation
- Silent data merge without confirmation — shared-device account takeover risk
- `CookieTransport` for guest sessions — dual-transport complexity and OAuth redirect issues

### Architecture Approach

The architecture follows a "guest user as first-class User record" pattern. Guests are full `users` table rows distinguished only by `is_guest=True`. Promotion is an in-place single-row `UPDATE` — no FK reassignment across child tables, no data migration. The `current_active_user` FastAPI-Users dependency works for guests without modification; all existing routers, repositories, and services are unchanged. New code is confined to a `guest_service.py` module, 4 new endpoints in `auth.py`, schema additions, and frontend additions to `useAuth.ts`, `Home.tsx`, `Import.tsx`, plus a new `PromoteAccountModal.tsx`.

**Major components:**

1. `POST /auth/guest/create` (new) — creates anonymous User row, returns Bearer JWT in response body; frontend stores in localStorage via existing `loginWithToken()`
2. `POST /auth/guest/promote` (new) — validates email uniqueness, updates User row in-place with `SELECT FOR UPDATE` lock, issues fresh JWT
3. `GET /auth/guest/promote/google/authorize` + `GET /auth/guest/promote/google/callback` (new) — separate from existing OAuth routes; embeds `guest_user_id` in state JWT; does NOT call `user_manager.oauth_callback`; requires new redirect URI registered in Google Cloud Console
4. `guest_service.py` (new) — all business logic for creation and promotion; `auth.py` stays HTTP-only
5. `PromoteAccountModal.tsx` (new) — two-path promotion UI (email/password + Google SSO); active import check before enabling Google button
6. `is_guest: Mapped[bool]` on `User` model + Alembic migration — foundational prerequisite for all other components

**Build dependency order:** DB migration → model/schema additions → `guest_service.py` → create/promote email endpoints → frontend `useAuth.ts` + types → homepage button → `GuestInfoBox` → `PromoteAccountModal` email path → Google SSO backend endpoints → `PromoteAccountModal` Google path.

### Critical Pitfalls

1. **CVE-2025-68481 — OAuth CSRF vulnerability in existing `google_callback`** — The current `app/routers/auth.py` implementation does not validate a CSRF cookie on the OAuth callback. Fix before adding any guest promotion OAuth route: implement the double-submit cookie pattern (`secrets.token_urlsafe(32)` set as `flawchess_oauth_csrf` HttpOnly cookie on authorize, validated on callback against a `csrftoken` claim in the state JWT). This patches the existing vulnerability AND is required by the new guest promote Google SSO route.

2. **Guest identity lost during Google OAuth redirect** — The OAuth callback is a GET from Google's redirect; it has no access to frontend state or the guest Bearer token. The guest `user_id` must be embedded as a claim in the `state` JWT by the authorize endpoint and extracted by the callback. Relying on any cookie being present in the callback fails in Safari/Firefox with Enhanced Tracking Protection enabled.

3. **`user_manager.oauth_callback` silently orphans guest data** — For Google SSO promotion, do NOT call `user_manager.oauth_callback(associate_by_email=True)`. It will create a new `User` row, logging the user into a fresh account with no game data. Write a custom `promote_guest_via_google()` function that updates the existing guest row and inserts into `oauth_accounts`.

4. **Email conflict during promotion must return 409, not 500** — Check for an existing user with the target email before executing the `UPDATE`. PostgreSQL's unique constraint produces a 500 if the pre-check is missing. Return `{"code": "email_exists"}` as HTTP 409; frontend shows "Email already registered — log in instead?"

5. **Active background import orphaned during Google SSO promotion** — If a guest starts an import and immediately uses Google SSO to promote, the OAuth redirect round-trip may cross a server restart boundary, orphaning the in-memory job. Disable or warn on the Google SSO promotion button when `GET /imports/active` returns active jobs.

6. **Old guest JWT remains valid after promotion** — JWT is stateless; updating the user row does not invalidate the prior token. Mitigate by issuing a fresh JWT in the promotion response and ensuring the frontend immediately replaces the stored token. Acceptable for v1.8 without a `token_version` claim since the user_id is unchanged and the security window is bounded to 7 days.

7. **Guest user accumulation without cleanup** — Every "Use as Guest" click creates DB rows with potentially large child data. Add `is_guest` flag and a composite index `(is_guest, created_at)` in the migration; write a cleanup script even if the cron job is deferred; add per-IP rate limiting on the guest creation endpoint.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation — DB Migration, OAuth CSRF Fix, and Guest Creation Backend

**Rationale:** The `is_guest` flag is the prerequisite for every subsequent phase. The OAuth CSRF fix (CVE-2025-68481) must ship before any Google SSO promotion route is added — patching an existing vulnerability in the same endpoint family is the right first action and blocks no other work. Guest creation backend is a pure backend phase with no frontend dependencies. Rate limiting and the DB index for cleanup queries also belong here because they are hardest to retrofit later.
**Delivers:** Alembic migration adding `is_guest` + composite index `(is_guest, created_at)`; CSRF double-submit cookie fix for existing `google_authorize` / `google_callback`; `guest_service.create_guest_user()`; `POST /auth/guest/create` endpoint; per-IP rate limit on guest creation
**Addresses:** Guest session creation (table stakes). Pitfall 1 (CVE-2025-68481), Pitfall 7 (guest accumulation), Pitfall 8 (transport decision locked in as Bearer-only)
**Avoids:** Building Google SSO promotion before the CSRF vulnerability is fixed

### Phase 2: Guest Frontend — Homepage CTA, Auth Context, and Guest Status Indicator

**Rationale:** With the guest creation endpoint live, the frontend can wire the "Use as Guest" button and extend the auth context. This phase produces a testable end-to-end guest session before adding the more complex promotion flows. The `isGuest` flag in auth context is required by the Import page info box and the promotion modal in later phases.
**Delivers:** `useAuth.ts` extended with `isGuest`, `loginAsGuest()`; `is_guest` added to `UserProfile` type and API schema; "Use as Guest" button on `Home.tsx`; non-dismissible guest indicator in header/navbar; synthetic guest email hidden in mobile "More" drawer and any profile display; mobile layout verified at 375px
**Addresses:** Guest session persistence on refresh, persistent status indicator, homepage entry point (table stakes). Pitfall — synthetic guest email must never be displayed in the UI
**Avoids:** Building promotion UI before guest state management is stable

### Phase 3: Account Promotion — Email/Password Path

**Rationale:** Email/password promotion is simpler than Google SSO (no OAuth redirect, no state JWT manipulation, no external redirect URI registration). Building and validating it first isolates the core promotion logic — in-place UPDATE, email uniqueness pre-check, fresh JWT issuance, frontend token replacement — before adding OAuth complexity. The `PromoteAccountModal` skeleton is built here with only the email/password tab.
**Delivers:** `guest_service.promote_guest()`; `POST /auth/guest/promote` endpoint with `SELECT FOR UPDATE` lock and 409 on email conflict; `GuestInfoBox` on Import page; `PromoteAccountModal.tsx` (email/password path); post-promotion redirect; frontend token replacement; Import page info box
**Addresses:** Email/password promotion, data preservation, confirmation step (table stakes). Pitfall 2 (stale JWT replaced), Pitfall 4 (concurrent race via row lock), Pitfall 5 (email conflict pre-check)
**Avoids:** Starting Google SSO promotion before the simpler path is proven

### Phase 4: Account Promotion — Google SSO Path

**Rationale:** The most complex phase, with the most pitfalls. By this point the CSRF fix (Phase 1), auth context (Phase 2), and promotion core logic (Phase 3) are all stable. This phase adds the custom Google SSO promotion routes, registers the new callback URI in Google Cloud Console, adds the active-import warning/block to the promotion modal, and validates in Safari and Firefox with ETP.
**Delivers:** `GET /auth/guest/promote/google/authorize` (embeds `guest_user_id` in state JWT, sets CSRF cookie); `GET /auth/guest/promote/google/callback` (custom `promote_guest_via_google()`, no `oauth_callback` call); "Continue with Google" button in `PromoteAccountModal`; active import check before Google SSO button; Google Cloud Console redirect URI registered; Safari + Firefox ETP tested
**Addresses:** Google SSO promotion (table stakes). Pitfall 3 (guest identity in state JWT), Pitfall 6 (active import warning), Pitfall 9 (cookie lost on redirect), Pitfall 10 (`associate_by_email` orphan risk)
**Avoids:** None — this is the final core phase; test thoroughly before shipping

### Phase 5 (Post-Launch): Conversion Optimization and Cleanup

**Rationale:** Defer non-essential conversion features until there is real usage data to guide decisions. The cleanup job needs the `is_guest` flag and index from Phase 1 already in place. This phase ships as a minor milestone after v1.8 is live and metrics are available.
**Delivers:** Expiry countdown in guest banner (last 7 days only); context-sensitive promotion prompt after import completion; periodic cleanup job for guest accounts older than 40 days
**Addresses:** Expiry countdown, context-sensitive prompt (differentiators). Pitfall 7 (long-term cleanup)

### Phase Ordering Rationale

- The CVE-2025-68481 CSRF fix must precede all OAuth promotion work — it patches the existing `google_callback` which the new promotion route shares infrastructure with. Shipping it in Phase 1 unblocks Phase 4 without creating a dependency chain that delays any other phase.
- DB migration is a hard prerequisite for every subsequent phase; shipping it first eliminates blocking dependencies.
- Email/password promotion before Google SSO promotion: simpler path, validates the core promotion logic (in-place UPDATE, JWT issuance, frontend token swap) before OAuth complexity is introduced.
- Conversion optimization deferred to post-launch: without real guest traffic data, the expiry countdown and context-sensitive prompt are speculative. Build them after the core flow ships and metrics are available.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Google SSO Promotion):** Complex OAuth state manipulation, two new redirect URIs, browser-specific cookie behavior in Safari/Firefox ETP. PITFALLS.md covers all the risks in detail. The ARCHITECTURE.md provides detailed pseudocode for the authorize/callback flows. No additional research needed — the implementation plan can be written directly from existing research.

Phases with standard patterns (skip additional research):
- **Phase 1 (Foundation):** DB migration is mechanical; CSRF fix implementation is fully documented in the CVE advisory and the official fix commit 7cf413c.
- **Phase 2 (Frontend):** Standard React context extension; well-documented patterns.
- **Phase 3 (Email/Password Promotion):** Standard REST endpoint pattern; email uniqueness pre-check is trivial SQLAlchemy.
- **Phase 5 (Cleanup):** Standard cron/startup task pattern; cleanup SQL is documented in PITFALLS.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new packages; all existing technology. Codebase directly inspected. FastAPI-Users 15.0.5 docs verified. Transport decision (Bearer only, no CookieTransport) confirmed by both STACK and ARCHITECTURE research independently. |
| Features | HIGH | Industry literature (Firebase, FusionAuth, NNGroup, Logto) consistent on all key decisions: full access vs read-only, 30-day TTL, non-dismissible indicator, data preservation on promotion. |
| Architecture | HIGH | Direct codebase inspection of `app/routers/auth.py`, `app/users.py`, `frontend/src/hooks/useAuth.ts`. Build order well-defined. Component boundaries clearly specified with minimal blast radius (existing routes/repos untouched). |
| Pitfalls | HIGH | CVE-2025-68481 verified via official GitHub advisory and fix commit. Codebase inspected to confirm current `google_callback` lacks CSRF cookie. All 10 pitfalls verified via multiple sources with specific warning signs and recovery strategies. |

**Overall confidence:** HIGH

### Gaps to Address

- **Google Cloud Console redirect URI registration:** The new callback path `/api/auth/guest/promote/google/callback` must be added as an authorized redirect URI in Google Cloud Console before Phase 4 can be tested end-to-end. This is an external manual action; flag for the user to complete before Phase 4 implementation begins.
- **`token_version` claim for JWT invalidation:** Research recommends issuing a fresh JWT on promotion (simpler, sufficient for v1.8) rather than implementing a `token_version` increment (robust full revocation). If the user wants full revocation, a migration and middleware change are needed. Flag as a decision point during Phase 3 planning.
- **Rate limiting dependency:** PITFALLS.md references `slowapi` for per-IP rate limiting on the guest creation endpoint. The codebase should be checked during Phase 1 planning for whether `slowapi` is already installed; if this would be the only use case, a lighter alternative (manual IP tracking with TTL) avoids a new dependency.
- **Guest email domain:** ARCHITECTURE.md recommends `@guest.local` while STACK.md recommends `@guest.flawchess.internal`. Align on one sentinel domain in Phase 1 planning — the difference is cosmetic but must be consistent across backend code, UI guards, and any email-sending paths.

## Sources

### Primary (HIGH confidence)
- FastAPI-Users 15.0.5 docs — CookieTransport, multiple auth backends, `user_manager.create()`, `optional=True` current_user
- CVE-2025-68481 GitHub Advisory (GHSA-5j53-63w8-8625) + fix commit 7cf413cd — OAuth CSRF double-submit cookie pattern
- Direct codebase inspection: `app/users.py`, `app/routers/auth.py`, `app/models/user.py`, `app/services/import_service.py`, `frontend/src/hooks/useAuth.ts`, `frontend/src/api/client.ts`
- Firebase best practices for anonymous authentication
- FusionAuth anonymous user patterns
- NNGroup: Login Walls Stop Users

### Secondary (MEDIUM confidence)
- FastAPI-Users multiple backends discussion (GitHub #989, #960) — dual-backend evaluation order confirmed by maintainer
- Logto: Implement Guest Mode — three-phase architecture (guest session, auth, merge)
- SuperTokens: Anonymous Sessions — 30-day TTL industry standard
- Auth0: SameSite Cookie Attribute Changes
- Audiobookshelf issue #5127 — Firefox bounce-tracking strips OIDC session cookie (real-world ETP issue)
- Curity: OAuth and Same Site Cookies best practices
- Authgear: Login and Signup UX Guide 2025

### Tertiary
- Eric Morgan: Guest Conversion Feature (Medium) — practitioner post confirming context-sensitive conversion patterns

---
*Research completed: 2026-04-06*
*Ready for roadmap: yes*

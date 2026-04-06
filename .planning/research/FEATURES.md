# Feature Research

**Domain:** Guest access / anonymous user flow for chess analysis web app
**Researched:** 2026-04-06
**Confidence:** HIGH (guest access patterns well-established in industry literature); MEDIUM (FastAPI-Users extension approach — no built-in guest mode, requires custom implementation on top of existing abstractions)

---

> This file covers features for v1.8: Guest Access.
> v1.0–v1.7 features are already shipped. Focus: letting visitors use FlawChess without signing up and promoting them to full accounts when ready.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any credible "try before you sign up" flow. Missing these = product feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| "Use as Guest" entry point on homepage | Users expect a frictionless trial path alongside sign-up. NNGroup research confirms login walls dramatically hurt adoption — users cannot judge value before they experience it | LOW | Button in homepage hero section alongside "Sign up free". No form, no friction, no modal. Single click starts a session. |
| Persistent guest session across page refreshes | Users expect their work to survive a tab reload. Losing progress on refresh destroys trust immediately and the app feels broken | MEDIUM | HttpOnly cookie with a guest JWT. `CookieTransport` in FastAPI-Users handles transport layer. A custom middleware or dependency creates the guest `User` row on first visit. Cookie must have `max_age` (not session-only) — 30 days is the industry standard (Firebase, FusionAuth, SuperTokens all converge here). |
| Full platform access as guest | Research consensus: read-only guest mode fails because users cannot experience core value. For FlawChess this means: no import = no WDL stats = nothing to try. Restricting to read-only is no different than a login wall | HIGH | Guests can import games and use the full move explorer, endgame analysis, and bookmarks. Same routes, same data isolation per user. Existing `current_active_user` dependency needs a parallel `current_user_or_guest` variant that also accepts the guest cookie transport. |
| Persistent guest status indicator | Users must know they are a guest at all times. A persistent non-dismissible badge prevents surprise when the session eventually expires. The car-maintenance app case study and Firebase's own guidance both confirm a top-of-screen reminder is the expected pattern | LOW | Non-blocking header badge or top banner. Must be visible at all times, not just on first visit. Should not be dismissible — see anti-features. |
| Account promotion: email/password | Email + password signup is the baseline promotion path users expect | MEDIUM | Existing FastAPI-Users `/auth/register` endpoint. Requires an atomic data migration step: all rows owned by the guest `user_id` are reassigned to the new registered `user_id` before the guest row is deleted. |
| Account promotion: Google SSO | Google login is expected alongside email — the app already supports it for registered users. Users who prefer Google will not accept a password-only promotion path | MEDIUM | Existing `/auth/google/callback` flow. Same atomic data migration requirement. Requires detecting the guest cookie inside the OAuth callback handler and routing to a merge path instead of a plain login. |
| Data preservation on promotion | Users expect everything they did as a guest — imported games, bookmarks — to carry over when they sign up. Data loss on promotion is a conversion killer and a trust violation | HIGH | The merge step is the most complex piece. All rows referencing the guest `user_id` must be re-pointed to the new registered `user_id` in a single DB transaction. Then the guest `User` row is deleted. |
| Clear explanation of sign-up benefits on import page | Guests using the Import page need to understand what they gain by creating an account. Without this, a "sign up" prompt feels like a nag rather than useful information | LOW | Info box on the Import page. Concrete benefits: cross-device access, no cookie dependency, no 30-day expiry, email-based account recovery. Tone: helpful, not pushy. |

### Differentiators (Competitive Advantage)

Features that meaningfully improve the guest-to-registered conversion funnel beyond the baseline. Not required for v1.8 launch, but worth considering.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Context-sensitive promotion prompt | Showing the sign-up nudge at peak-value moments (after first import completes, after position analysis yields useful results) converts better than a static nag. Progressive disclosure — reveal the "why sign up" message when the user has just experienced value | LOW | Trigger the prominent CTA after import completion success state, not on arrival. The always-visible guest badge handles baseline awareness. |
| "Your data expires in N days" countdown | Concrete consequence (not vague "sign up for more") motivates action. Expiry messaging converts better than benefit-only messaging | LOW | Show days-remaining in the guest banner when the cookie approaches expiry. Only show countdown in the last 7 days to avoid premature alarm that annoys users who just arrived. |
| Post-promotion redirect back to previous page | After signing up, landing on a generic dashboard instead of the page the user was on feels jarring. Returning them to their work is a small but noticeable quality signal | LOW | Store pre-promotion URL in session storage, redirect after promotion completes. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Read-only guest mode | Seems lower-risk: guests browse but cannot import | Defeats the purpose entirely. FlawChess has no value without imported games. No value experienced = no motivation to sign up. Firebase best-practices docs and the car-app case study both confirm this explicitly | Full access with persistent session |
| Mandatory email capture before guest access | Seems like a lead-gen opportunity | This is a disguised login wall. Asking for email before allowing access removes the "no commitment" promise of guest mode. It will reduce trial adoption, not increase it | Show email prompt only during explicit account promotion, never before |
| Dismissible guest banner | Seems less annoying to users | If users can dismiss the banner, a significant portion will forget they are a guest and be surprised when data disappears. Surprise = trust violation and support burden | Non-dismissible indicator — keep it small and unobtrusive. It should inform without annoying. |
| Silent data merge without confirmation | Seamless merge sounds ideal | If a shared device is involved (family computer, library), guest data from person A could be silently merged into person B's registered account. This is a documented account-takeover-via-shared-session risk | Explicit "claim this guest data?" confirmation step during promotion with a brief explanation of what will be merged |
| Unlimited guest session duration | More time = more value experienced | Stale guest accounts accumulate and bloat the database. Firebase, FusionAuth, and SuperTokens all converge on approximately 30 days as the right TTL | 30-day cookie + periodic cleanup job for expired unconverted guest users |
| Guest sharing or data export | Adds value for guests who want to share a position | Sharing requires a stable, addressable identity (email, URL tied to an account). Guests have no stable identity. This is one of Firebase's explicitly recommended trigger points for promotion | Show "create an account to share" CTA when the user attempts an action that requires identity |

---

## Feature Dependencies

```
[is_guest flag on User model]
    └──required_by──> [Guest user auto-creation middleware]
    └──required_by──> [Guest status indicator]
    └──required_by──> [Guest cleanup job]

[Guest user auto-creation (middleware + cookie)]
    └──requires──> [is_guest flag on User model]
    └──requires──> [CookieTransport added to FastAPI-Users auth backend]
    └──enables──> [Full platform access as guest]
    └──enables──> [Guest status indicator]
    └──enables──> [Import page info box]

[Full platform access as guest]
    └──requires──> [current_user_or_guest dependency variant]
    └──requires──> [Guest user auto-creation]

[Account promotion: email/password]
    └──requires──> [Guest session exists (cookie present)]
    └──requires──> [Atomic data migration (FK reassignment)]
    └──enables──> [Post-promotion redirect]

[Account promotion: Google SSO]
    └──requires──> [Guest session exists (cookie present)]
    └──requires──> [Atomic data migration (FK reassignment)]
    └──requires──> [Guest cookie detection inside OAuth callback]

[Atomic data migration (FK reassignment)]
    └──requires──> [All CASCADE FK tables identified]
    └──note──> Tables: games, import_jobs, position_bookmarks (game_positions cascades via game_id)

[Merge confirmation step]
    └──requires──> [Guest session exists]
    └──enhances──> [Account promotion: email/password]
    └──enhances──> [Account promotion: Google SSO]

[Expiry countdown in guest banner]
    └──requires──> [Guest session expiry date readable from DB or cookie]
    └──enhances──> [Guest status indicator]
    └──note──> Optional for v1.8; add if conversion metrics suggest it helps

[Guest cleanup job]
    └──requires──> [is_guest flag]
    └──requires──> [created_at on User model (already exists)]
    └──note──> Cron or background task; delete guest users older than 40 days (10-day buffer over 30-day cookie)
```

### Dependency Notes

- **`is_guest` flag is foundational:** The flag is the only reliable way to distinguish guest users from registered users at the DB layer. The JWT payload alone is insufficient without additional user-table data. Add `is_guest: bool` (default `False`) to the `User` model via Alembic migration. This is Phase 1.
- **Data migration must identify all FK tables first:** `games`, `import_jobs`, and `position_bookmarks` all have `ForeignKey("users.id", ondelete="CASCADE")`. `game_positions` links via `game_id`, so it cascades automatically when games are reassigned. `oauth_accounts` is managed by FastAPI-Users — guest users have no OAuth accounts, so nothing to reassign there. The migration runs `UPDATE games SET user_id = $new WHERE user_id = $guest`, etc., in a single transaction, then deletes the guest `User` row.
- **Google SSO promotion is the trickiest:** The current `google_callback` handler creates or retrieves a registered user. When a guest cookie is present during Google OAuth, the callback must detect it and route to the merge path instead of the standard login path. This requires the OAuth callback handler to read the guest cookie — new logic not currently present.
- **`current_user_or_guest` dependency must be added carefully:** Several endpoints (import, analysis) currently use `current_active_user` from FastAPI-Users, which requires a valid bearer token and returns 401 otherwise. Guest support requires adding a cookie-based fallback to these dependencies. This should be a new dependency, not a modification of `current_active_user`, to avoid breaking the existing registered-user flow.
- **CookieTransport and BearerTransport coexistence:** The current auth backend uses `BearerTransport` only. Adding `CookieTransport` for guest sessions requires a second `AuthenticationBackend` instance or a custom dependency that checks both transports. The two transports should be additive, not mutually exclusive.

---

## MVP Definition

### Launch With (v1.8)

Minimum viable to satisfy the milestone goal: visitors can use FlawChess without signing up and can promote to a full account at any time with all data preserved.

- [ ] `is_guest` boolean flag on `User` model (Alembic migration)
- [ ] Guest user auto-creation on first visit (middleware or startup hook) — HttpOnly cookie, 30-day TTL
- [ ] Full platform access for guest users (import, move explorer, endgame analysis, bookmarks)
- [ ] Persistent non-dismissible guest status indicator in header/navbar
- [ ] Account promotion via email/password — atomic FK reassignment, then cookie cleared
- [ ] Account promotion via Google SSO — same atomic FK reassignment path, triggered from OAuth callback on guest cookie detection
- [ ] Explicit "claim this guest data?" confirmation step before merge
- [ ] Import page info box explaining sign-up benefits
- [ ] Post-promotion redirect back to the page the user was on

### Add After Validation (v1.8.x)

Features to add once the core guest flow ships and conversion metrics are available.

- [ ] Expiry countdown in guest banner (last 7 days only)
- [ ] Context-sensitive promotion prompt triggered after import completion
- [ ] Periodic cleanup job for expired guest accounts (40-day TTL, 10-day buffer over cookie expiry)

### Future Consideration (v2+)

- [ ] Guest session analytics (how many guests convert, at what point in the funnel) — requires Umami events or custom event tracking
- [ ] "Share this position" feature gated behind promotion CTA — good differentiator, not MVP

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `is_guest` flag + Alembic migration | HIGH (enables everything else) | LOW | P1 |
| Guest user auto-creation + cookie | HIGH | MEDIUM | P1 |
| Full platform access as guest | HIGH | MEDIUM | P1 |
| Guest status indicator (header badge) | HIGH | LOW | P1 |
| Account promotion: email/password | HIGH | MEDIUM | P1 |
| Account promotion: Google SSO | HIGH | MEDIUM | P1 |
| Atomic FK reassignment on promotion | HIGH (data loss otherwise) | HIGH | P1 |
| Merge confirmation step | MEDIUM (security requirement) | LOW | P1 |
| Import page info box | MEDIUM | LOW | P1 |
| Post-promotion redirect | MEDIUM | LOW | P1 |
| Expiry countdown in guest banner | MEDIUM | LOW | P2 |
| Context-sensitive promotion prompt | MEDIUM | LOW | P2 |
| Guest cleanup job | LOW (needed at scale) | LOW | P2 |

**Priority key:**
- P1: Required for v1.8 launch
- P2: Add after v1.8 ships, before v1.9
- P3: Defer to v2+

---

## Competitor Feature Analysis

| Feature | Chess.com | Lichess | FlawChess plan |
|---------|-----------|---------|----------------|
| Use without account | Yes — "Guest Play" for online matches | Yes — anonymous play vs computer and friends | Full import + analysis access without account |
| Guest feature scope | Online play only; no game history, no analysis | Play only; preferences require login | Full import + WDL analysis (stronger than competitors) |
| Guest data persistence | No — each session is fresh | No — no history saved | Yes — 30-day cookie, DB-backed persistence |
| Account promotion preserves data | N/A (nothing to preserve) | N/A | Yes — atomic FK reassignment keeps all imported games and bookmarks |
| Guest indicator | Shown as "Guest" in UI | N/A | Non-dismissible header badge |

FlawChess's guest mode is meaningfully stronger than competitors: guests import and analyze real games rather than just playing one-off matches. This is possible because FlawChess is a single-user analytics tool with no multi-user interaction concerns that would complicate anonymous access (no chat, no matchmaking, no shared game rooms).

---

## Implementation Notes for Backend

### Existing auth system context

The current setup uses `BearerTransport` only (JWT in `Authorization` header, stored by the frontend in memory or localStorage). No `CookieTransport` is currently configured. Key file: `app/users.py`.

**Recommended guest architecture:**
1. Add a second `AuthenticationBackend` using `CookieTransport` specifically for guest sessions. Registered users continue using `BearerTransport`. The two backends coexist — FastAPI-Users supports multiple backends.
2. Add `is_guest: bool = False` to the `User` model. Guest users have `is_active=True`, `is_verified=False`, `is_guest=True`, and a null/placeholder email (auto-generated UUID-based address to satisfy the `email` unique constraint).
3. On promotion, run the merge transaction, then issue a new bearer token for the registered user, and clear the guest cookie. The frontend switches from cookie-based auth to bearer-based auth at this point.

### Data reassignment scope

Tables with `ForeignKey("users.id", ondelete="CASCADE")`:
- `games` — reassign `user_id`
- `import_jobs` — reassign `user_id`
- `position_bookmarks` — reassign `user_id`
- `oauth_accounts` — FastAPI-Users managed; guest users have none, nothing to reassign

`game_positions` links via `game_id` with `ondelete="CASCADE"`, so it is automatically covered when `games` rows are reassigned (the game_id values do not change).

### Email placeholder strategy for guest users

FastAPI-Users requires a unique `email` field. Guest users have no real email. Options:
- Auto-generate a UUID-based placeholder: `guest-{uuid}@guests.flawchess.com`. Must be filtered out of any display logic and email-sending paths.
- Set `is_active=True` but do not allow password reset or email verification for `is_guest=True` users — these endpoints should 403 for guests.

---

## Sources

- [FusionAuth: How to Support Anonymous User Accounts](https://fusionauth.io/blog/anonymous-user) — HIGH confidence
- [Firebase: Best Practices for Anonymous Authentication](https://firebase.blog/posts/2023/07/best-practices-for-anonymous-authentication) — HIGH confidence
- [Logto: Implement Guest Mode](https://blog.logto.io/implement-guest-mode-with-logto) — HIGH confidence (clean three-phase architecture: guest session, auth, merge)
- [NNGroup: Login Walls Stop Users](https://www.nngroup.com/articles/login-walls/) — HIGH confidence
- [UI Patterns: Lazy Registration](https://ui-patterns.com/patterns/LazyRegistration) — HIGH confidence
- [Eric Morgan: Guest Conversion Feature (Medium)](https://medium.com/@ericmorgan1/guest-conversion-feature-42c65bb320f) — MEDIUM confidence (practitioner post, not academic)
- [SuperTokens: Anonymous Sessions](https://supertokens.com/docs/thirdparty/common-customizations/sessions/anonymous-session) — MEDIUM confidence
- [FastAPI-Users CookieTransport documentation](https://fastapi-users.github.io/fastapi-users/10.3/configuration/authentication/transports/cookie/) — HIGH confidence
- [Authgear: Login and Signup UX Guide 2025](https://www.authgear.com/post/login-signup-ux-guide) — MEDIUM confidence

---

*Feature research for: FlawChess v1.8 — Guest Access (anonymous users with account promotion)*
*Researched: 2026-04-06*

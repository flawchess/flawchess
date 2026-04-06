# Pitfalls Research

**Domain:** Adding guest/anonymous user access with account promotion to an existing FastAPI-Users app
**Researched:** 2026-04-06
**Confidence:** HIGH (codebase verified, CVEs confirmed via official advisories, patterns confirmed via multiple sources)

---

## Critical Pitfalls

### Pitfall 1: CVE-2025-68481 — FastAPI-Users OAuth State Has No Session Binding

**What goes wrong:**
FastAPI-Users below version 15.0.2 generates OAuth state JWTs that are completely stateless — no per-request entropy, no session correlation. During guest-to-registered promotion via Google SSO, the `google_callback` route validates the state JWT's signature but cannot verify that the state belongs to the session that initiated the flow. An attacker can initiate an OAuth flow, capture the state token, and then trick a logged-in victim (including a guest user mid-promotion) into visiting the callback URL with the attacker's credentials. The victim's account becomes linked to the attacker's Google identity — account takeover.

This project already implements a custom `google_callback` handler in `app/routers/auth.py` that calls `decode_jwt(state, ...)` but does not set or validate a CSRF cookie. The existing implementation has the same vulnerability pattern that CVE-2025-68481 describes.

**Why it happens:**
The OAuth state JWT validates cryptographically (signature check passes) but provides no proof that the state was generated for the specific browser session that received the callback. Developers see the signature check and assume the state is secure.

**How to avoid:**
- Implement the double-submit cookie pattern: generate a random CSRF token alongside the state JWT, set it as a short-lived `HttpOnly; SameSite=Lax` cookie in the `/auth/google/authorize` response, and verify on callback that the cookie value matches the CSRF claim embedded in the state JWT.
- This must be done for the guest promotion Google SSO path too — if a guest user clicks "Sign in with Google" to promote, the authorize step must emit the CSRF cookie and the callback must validate it.
- Use `secrets.token_urlsafe(32)` for the CSRF token (already used in `auth.py` — but the cookie-writing and callback-validation steps are missing).
- The promotion flow must preserve the guest `user_id` in the state JWT so the callback can complete the promotion atomically.

**Warning signs:**
- `google_authorize` endpoint returns an `authorization_url` but sets no cookie in the response.
- `google_callback` validates `state` JWT but reads no cookie from the request.
- Sentry shows `InvalidOAuthStateError` or `CSRF validation failure` from a user who didn't initiate the flow.

**Phase to address:**
Guest creation backend — before the Google SSO promotion route exists. Fix the existing `google_authorize` / `google_callback` endpoints to use the double-submit cookie pattern, then reuse the same pattern for the guest promotion route.

---

### Pitfall 2: Guest JWT Still Valid After Promotion — Old Sessions Can Access the New Account

**What goes wrong:**
The plan promotes a guest by updating the existing `User` row in-place (email, hashed_password, is_verified, etc.). The guest JWT issued at guest creation time is valid for 7 days (`JWTStrategy(lifetime_seconds=604800)` in `app/users.py`). After promotion, the old JWT — which embeds the same `user_id` — continues to be accepted because the token validation only checks signature and expiry, not the user's `is_verified` or `hashed_password` fields. A guest user who promotes on device A can still use the old guest JWT from device B for up to 7 days without re-authenticating, operating under the promoted account's identity without having completed email verification.

This is not a data integrity problem (same user_id), but it means: (a) the guest JWT bypasses email verification intended for promoted accounts, and (b) if a guest account is compromised before promotion, the attacker retains access after promotion.

**Why it happens:**
JWT is stateless — there is no revocation mechanism in the current stack. Updating the user row doesn't invalidate previously issued tokens. Developers assume "promotion changes the user row" implies "old tokens are now invalid."

**How to avoid:**
- Issue a fresh JWT immediately after promotion completes and return it to the frontend in the same response. The frontend must store the new token and discard the old guest token.
- Add a `token_version: int` field to the `User` model. Increment it on promotion. Include `token_version` as a claim in JWTs. Validate `token_version` claim against the DB on each request. This is the only way to truly invalidate old guest JWTs without a blacklist.
- Simpler alternative (acceptable for v1.8): keep 7-day JWT lifetime, but issue a fresh JWT on promotion so the frontend immediately uses the promoted token. Document that old guest tokens expire within 7 days — the security window is bounded and the data is unchanged (same user_id).
- Do NOT implement a token blacklist — this adds Redis/DB overhead inconsistent with the current stateless JWT approach.

**Warning signs:**
- After promotion, the frontend still sends the original guest JWT (`Authorization: Bearer <guest_token>`).
- `GET /users/me/profile` returns `is_verified: false` for a promoted user who completed email verification.

**Phase to address:**
Account promotion endpoint — issue a fresh JWT in the promotion response and instruct the frontend to replace the stored token immediately.

---

### Pitfall 3: Google SSO Promotion Loses Guest Identity During the OAuth Redirect Round-Trip

**What goes wrong:**
When a guest user clicks "Sign in with Google" to promote, the flow leaves the app and goes to Google, then returns via `GET /auth/google/callback`. The guest's identity (their `user_id`) lives in the frontend auth store and the HttpOnly cookie — but neither is available inside the `google_callback` handler, which only sees the OAuth code and state. If the callback doesn't know this is a promotion (vs. a normal login), it will call `user_manager.oauth_callback(associate_by_email=True)` which either logs in an existing registered user (skipping promotion) or creates a brand-new user (losing all guest data).

The guest user_id must survive the redirect. The only mechanism available in the callback is the `state` JWT.

**Why it happens:**
The OAuth redirect breaks the request context. There is no session (the app is stateless), and HTTP redirects cannot carry custom request headers or body payloads. Developers assume the frontend can re-send the guest token on callback — but the callback is a GET from Google's redirect, not a frontend-controlled request.

**How to avoid:**
- Embed `guest_user_id` as a claim in the state JWT generated by `google_authorize`. The authorize endpoint must accept an optional `guest_user_id` parameter from the frontend (extracted from the current auth token).
- On callback, decode the state JWT and extract `guest_user_id`. If present, skip `user_manager.oauth_callback` and instead run the promotion logic: update the guest `User` row with the Google email and link the OAuth account.
- The CSRF cookie (see Pitfall 1) must be set regardless of whether this is a promotion or a normal OAuth login — same cookie, same callback validation.
- Validate that the `guest_user_id` in the state JWT corresponds to an actual guest user (not a registered user) before executing the promotion path.

**Warning signs:**
- Google SSO promotion creates a new account instead of updating the existing guest account.
- Guest data (imported games, bookmarks) is missing after "Sign in with Google."
- `google_callback` creates a duplicate user row with the same chess.com/lichess usernames as the guest row.

**Phase to address:**
Account promotion backend — modify `google_authorize` to accept and embed `guest_user_id`, modify `google_callback` to detect the promotion path and route accordingly.

---

### Pitfall 4: Concurrent Promotion Race — Two Requests Promote the Same Guest Simultaneously

**What goes wrong:**
If a guest user double-submits the promotion form or two tabs both trigger promotion at the same time, two concurrent requests both attempt to update the same guest `User` row. The first succeeds, setting `email`, `hashed_password`, and `is_verified`. The second reads the same guest row (before the first commit is visible), applies its own update, and either silently overwrites the first promotion's data or — if email uniqueness is enforced — raises a `UniqueViolationError` that produces a 500 response.

For Google SSO promotion, the race involves two calls to `user_manager.oauth_callback` with `associate_by_email=True`. If the Google email doesn't exist yet (first request mid-commit), the second might attempt to create a new user, violating the unique constraint on email and producing a 500.

**Why it happens:**
The promotion endpoint updates a row — this is not naturally idempotent. Without an explicit lock or idempotency check, concurrent requests both proceed past the "is this user a guest?" check and both attempt the mutation.

**How to avoid:**
- Use `SELECT ... FOR UPDATE` (PostgreSQL row-level lock) at the start of the promotion transaction to lock the guest user row. The second concurrent request blocks until the first commits, then retries and finds the user is already promoted (email is set), and returns a clear error: "Account already promoted."
- Alternatively, use `UPDATE users SET ... WHERE id = :user_id AND email IS NULL RETURNING id` — if 0 rows returned, the user was already promoted.
- Add a DB-level unique constraint on `email` (already present via FastAPI-Users' `SQLAlchemyBaseUserTable` base). This is the last-resort safety net, but catching a `UniqueViolationError` and returning 409 is better than a 500.

**Warning signs:**
- Sentry shows `UniqueViolationError` on the `users.email` column during promotion.
- Two JWT tokens are issued for the same `user_id` with different email claims.
- A user reports "Sign up failed" but finds themselves already signed up on retry.

**Phase to address:**
Account promotion endpoint — the UPDATE statement must include a WHERE condition that verifies guest state, making the operation atomic and idempotent.

---

### Pitfall 5: Email Already Registered Conflict During Promotion

**What goes wrong:**
A guest user enters an email address to promote their account. That email already exists in the `users` table because the same person previously registered with email/password (or because another user registered with that email). The promotion logic must NOT overwrite the existing registered account — that would be an account takeover. If the promotion endpoint calls `UPDATE users SET email = :email WHERE id = :guest_id` without first checking for email existence, PostgreSQL raises a `UniqueViolationError`, which is caught and shown as a generic 500 or a cryptic error.

The correct behavior: detect the conflict, inform the user "An account with this email already exists — please sign in instead," and offer a login flow that merges their guest data.

**Why it happens:**
Promotion is framed as "update the guest row" but email uniqueness enforcement is pushed to the DB layer. Without an application-level pre-check, the UX is a raw constraint error.

**How to avoid:**
- Before updating the guest user, query for an existing user with the same email.
- If found and it's a different `user_id`: return HTTP 409 with a specific error body `{"code": "email_exists"}`. The frontend displays "Email already registered — log in to link your data."
- If found and it's the same `user_id` (guest already promoted): return HTTP 200 — idempotent.
- Do NOT silently merge data from two different registered accounts — this is out of scope and a security boundary.
- For Google SSO promotion: `user_manager.oauth_callback(associate_by_email=True)` will automatically link the Google identity to the existing account. This is correct behavior for login, but NOT for promotion — when promoting a guest, the intent is to transform the guest row, not log into the pre-existing account and lose guest data.

**Warning signs:**
- Sentry shows `UniqueViolationError` on `users.email` with no corresponding 409 response.
- A user reports their imported games disappeared after promotion (because the callback logged them into their old account, abandoning the guest row).
- `GET /imports/active` shows 0 active imports for the promoted user despite the guest having completed imports.

**Phase to address:**
Account promotion endpoint — add pre-check for email existence before the UPDATE, with explicit 409 + error code for the frontend to handle.

---

### Pitfall 6: Active Background Import Orphaned When Guest Promotes

**What goes wrong:**
The import pipeline runs as a background `asyncio.create_task` that holds the `user_id` in its `JobState` dataclass (`_jobs` dict, `app/services/import_service.py`). When a guest promotes, the `user_id` does not change (in-place update). However, if the guest username is stored in `user_repository.update_platform_username` before promotion and the import task is running, the import task's `job.user_id` will still be the same integer — so the import data lands under the correct user. This is correct.

The problem is the import job status UI. The frontend polls `GET /imports/active` using the guest JWT. After promotion, the frontend switches to the new JWT (same user_id). The import job's `job_id` is a UUID string stored in `_jobs` keyed by `job_id`. This survives the JWT transition fine.

The real failure: if the guest starts an import, then promotes via Google SSO (which involves a full page redirect to Google and back), the in-memory `_jobs` dict still holds the job. The frontend callback page restores the new JWT and immediately redirects to the dashboard. The import continues correctly in the background. But if the backend restarts between the import start and the Google redirect return, the job is orphaned — the `cleanup_orphaned_jobs` startup function marks it failed. The user's games are not imported. They see "import failed" with no easy recovery path.

**Why it happens:**
The OAuth redirect is a multi-second flow that crosses a potential server restart boundary. The import service uses in-memory job state that does not survive restarts.

**How to avoid:**
- Show a warning on the import page: "Your import is in progress. Signing up now will not interrupt it, but if you use Google Sign-In, please wait until the import completes to avoid rare data loss on server restart."
- Better: disable the Google SSO promotion button while an import is active for the current guest.
- The import page already shows active import status — the promotion UI should check `GET /imports/active` and block or warn if any job is PENDING or IN_PROGRESS.

**Warning signs:**
- Sentry shows `cleanup_orphaned_jobs marked 1 jobs as failed` immediately followed by a guest promotion event.
- A user reports "started import, signed up with Google, now games are gone."

**Phase to address:**
Promotion UI — check for active imports before allowing Google SSO promotion and surface a clear warning or block.

---

### Pitfall 7: Guest Users Accumulate Without Cleanup — Table Bloat and Storage Costs

**What goes wrong:**
Every "Use as Guest" click creates a real `User` row (and potentially `import_job`, `games`, `game_positions`, and `position_bookmarks` rows). Guest users who import games and never promote will remain in the DB indefinitely. At even modest traffic (100 guest sessions/day), this is 36,500 guest users per year with their full game data — potentially millions of `game_positions` rows from non-converting users. PostgreSQL will slow on `VACUUM` over bloated tables. The 75 GB NVMe disk (currently adequate for registered users) can fill from abandoned guest data.

The milestone notes "30-day guest cleanup deferred" — but deferring with no mechanism in place means the cleanup is never implemented until a disk-full emergency forces it.

**Why it happens:**
Guest user creation is fast and low-friction by design. No natural cleanup mechanism exists because registered users are permanent. Adding cleanup later requires identifying which users are guests (no email, or `is_guest` flag) and ensuring CASCADE deletes propagate correctly without touching promoted users.

**How to avoid:**
- Add `is_guest: bool` (or `created_as_guest: bool`) and `created_at` (already present in the `User` model) to distinguish guest rows from registered rows.
- Add a DB index on `(is_guest, created_at)` for efficient batch cleanup queries.
- Even if the cron job is deferred, write the cleanup SQL in a script (like `scripts/`) and document the retention policy (e.g., delete guest users inactive > 30 days).
- Set a hard limit on guest accounts created per IP per hour using the existing rate-limiting pattern (slowapi or similar) — prevents cleanup debt from accumulating faster than the deferred job can handle.
- Ensure `ondelete="CASCADE"` is correct on all guest-owned tables (already correct for `games` → `game_positions` → etc.) so deleting a guest `User` row cascades completely.

**Warning signs:**
- `SELECT count(*) FROM users WHERE is_guest = true` grows unboundedly week-over-week.
- Disk usage on `/` (NVMe) trending upward faster than registered user game count explains.
- `autovacuum` running more frequently than usual (pg_stat_user_tables `n_dead_tup` high on `game_positions`).

**Phase to address:**
Guest creation backend — add `is_guest` flag and DB index in the same migration that adds the column. Write the cleanup script even if the cron job is deferred. Add per-IP rate limiting on the guest creation endpoint.

---

### Pitfall 8: HttpOnly Cookie Conflicts With Existing Bearer Token Auth

**What goes wrong:**
The current auth stack uses `BearerTransport` — the JWT lives in `localStorage` and is sent as `Authorization: Bearer <token>` on every API request. For guest users, the plan uses a separate HttpOnly cookie for the guest JWT. This creates two authentication mechanisms on the same API: Bearer token for registered users, cookie for guests.

If the auth middleware is not carefully ordered, a request with both a valid Bearer token and a valid guest cookie will produce undefined behavior — one middleware authenticates the registered user, another authenticates the guest. FastAPI-Users' `current_active_user` dependency resolves via the configured `auth_backend` (Bearer). If the guest cookie auth is added as a second backend, the dependency may use whichever backend resolves first, potentially mixing identities.

Additionally: after promotion, the frontend stores the new JWT as a Bearer token. If the guest cookie is not cleared server-side, subsequent requests may carry both. The guest cookie auth would resolve to the (now-promoted, same user_id) user, but the stale cookie could confuse logging and Sentry traces.

**Why it happens:**
Mixing CookieTransport with BearerTransport for different user types on the same endpoint is non-standard for FastAPI-Users. The framework is designed for one transport per auth backend.

**How to avoid:**
- Do NOT use FastAPI-Users' `CookieTransport` for guest tokens. Instead, issue the guest JWT as a normal Bearer token and store it in `localStorage` exactly like the registered user flow. The guest JWT contains a `user_id` that points to a real row in the `users` table — no special transport needed.
- The "HttpOnly cookie" approach is only necessary if the guest token must survive cross-origin requests without JavaScript access. For a same-origin SPA, Bearer token in `localStorage` is equivalent security-wise and eliminates the dual-transport problem.
- If HttpOnly cookie is required for security reasons (e.g., XSS resistance for guest data): implement a separate `/auth/guest/token` endpoint that sets the cookie and a dedicated `get_current_guest` dependency that reads the cookie. Never mix this with `current_active_user` on the same endpoint — use separate dependency chains.
- On promotion, explicitly clear the guest cookie (set `max_age=0`) in the promotion response, even if Bearer is the primary transport.

**Warning signs:**
- API request carries both `Authorization: Bearer <token>` and `Cookie: guest_token=<token>` simultaneously.
- `current_active_user` dependency resolves to different users on different requests from the same browser session.
- Sentry `user.id` alternates between guest_id and registered_id for the same session.

**Phase to address:**
Guest creation backend — decide the transport mechanism (Bearer preferred) before writing any code. If cookie transport is chosen, implement strict separation of dependency chains.

---

### Pitfall 9: SameSite=Lax Guest Cookie Lost on OAuth Redirect Return

**What goes wrong:**
If HttpOnly cookie transport IS chosen (despite Pitfall 8 above), `SameSite=Lax` is the correct setting for OAuth compatibility. However, some browsers (notably Safari) and Firefox's bounce-tracking protection strip cookies set during cross-site redirect chains. The Google OAuth flow is:

```
flawchess.com → accounts.google.com → flawchess.com/auth/google/callback
```

On the callback leg, the browser issues a cross-site GET to the backend. `SameSite=Lax` cookies ARE sent on top-level navigation GET requests — so the guest cookie should arrive at the callback. But Firefox's enhanced tracking protection may classify `accounts.google.com` as a bounce tracker and strip the guest cookie on the return.

If the guest cookie is lost, the callback cannot identify the guest user and cannot complete promotion — it falls back to creating a new registered user with no guest data.

**Why it happens:**
`SameSite=Lax` was chosen as a safe default for cross-site redirects, but browser-level tracking protection adds a layer of unpredictability that SameSite alone cannot address.

**How to avoid:**
- Do not rely on the guest cookie being present in the OAuth callback. Use the `state` JWT to carry the `guest_user_id` claim (see Pitfall 3). The state is a URL parameter, not a cookie — it survives any browser tracking protection.
- The guest cookie (if used) serves only for regular API calls from the frontend, not for the OAuth redirect round-trip.
- Test the promotion flow in Safari (iOS and macOS) and Firefox with Enhanced Tracking Protection enabled before shipping.

**Warning signs:**
- Google SSO promotion works in Chrome but fails in Safari or Firefox with ETP.
- Backend logs show `guest_user_id=None` in the callback despite the user being a guest.
- Users report "I signed in with Google but my imported games are gone" only in certain browsers.

**Phase to address:**
Account promotion backend — validate in Safari and Firefox before marking the phase complete. Explicitly test the promotion redirect flow in all three major browser engines.

---

### Pitfall 10: `associate_by_email=True` Silently Merges Guest Into Existing Google Account

**What goes wrong:**
The existing `google_callback` calls `user_manager.oauth_callback(associate_by_email=True, ...)`. This is correct for registered users — it links a Google identity to an existing account by matching email. For guest promotion, if a guest user clicks Google SSO and the backend does not intercept the promotion path (see Pitfall 3), `associate_by_email=True` will find the guest row has no email and create a new registered user row — abandoning the guest's data. If by some path the guest row has a matching email (impossible normally, but possible in edge cases), `associate_by_email=True` will link the Google OAuth account to the guest row and set `is_verified=True`. This is the correct outcome — but only if guest promotion logic explicitly controls the flow.

The silent failure mode: the callback creates a new `User` row for the Google account, logs the user into the new account, and the guest row remains in the DB indefinitely with all its data and no owner — a permanent data orphan.

**Why it happens:**
`user_manager.oauth_callback` is designed for login, not for promotion. Reusing it for promotion without modifying the guest row first causes it to create a new user.

**How to avoid:**
- For Google SSO promotion: do NOT call `user_manager.oauth_callback` on the guest promotion path. Instead, write a custom promotion function that: (1) verifies the Google identity via the OAuth access token, (2) updates the guest `User` row with the Google email and sets `is_verified=True`, (3) inserts a row into `oauth_accounts` linking the Google identity to the guest's `user_id`.
- Add an integration test that exercises the full Google SSO promotion path in isolation and asserts: one `User` row (the guest, now promoted), zero abandoned guest rows, correct `oauth_accounts` entry.

**Warning signs:**
- After Google SSO promotion, `SELECT count(*) FROM users WHERE is_guest = true AND email IS NULL` still contains the original guest row.
- The user is logged in with a new `user_id` that has no game data.
- `oauth_accounts` table has a row pointing to a new `user_id`, not the original guest `user_id`.

**Phase to address:**
Account promotion backend — write a dedicated `promote_guest_via_google` function rather than reusing `oauth_callback`. Cover with an integration test.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Defer guest cleanup cron job indefinitely | Simpler v1.8 scope | Table bloat, disk pressure, VACUUM overhead; retroactive cleanup is more complex than proactive | Acceptable only if a cleanup script exists, `is_guest` flag is set, and a backlog item is explicitly scheduled |
| Store guest JWT in localStorage (same as registered JWT) | No transport complexity | No practical downside for a same-origin SPA; this is actually the better choice | Always acceptable for same-origin SPA |
| Use `associate_by_email=True` for promotion without a custom path | Reuse existing OAuth logic | Silently creates new user on email mismatch; orphans guest data | Never for promotion — only valid for login |
| Skip `token_version` claim for JWT invalidation post-promotion | Simpler implementation | Old guest tokens valid for up to 7 days after promotion; acceptable if frontend replaces token immediately | Acceptable if fresh JWT is issued on promotion response |
| Validate OAuth CSRF only in state JWT without a cookie | Simpler than double-submit | Vulnerable to login CSRF (CVE-2025-68481 pattern); full account takeover risk | Never |
| Rate-limit guest creation by IP only | Simple to implement | Shared NAT IPs (offices, mobile carriers) get blocked while attackers use rotating proxies | Acceptable at MVP scale; revisit if abuse is observed |
| Promote by patching `is_guest` without clearing the flag atomically | Simpler update | Promoted user still appears as guest if the flag update fails mid-transaction | Never — use a DB transaction that updates all fields atomically or none |

---

## Integration Gotchas

Common mistakes when connecting to the existing FlawChess auth system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `current_active_user` dependency | Adding a second auth backend (CookieTransport) for guests alongside Bearer | Use a single Bearer transport for both guest and registered JWTs; differentiate by a `is_guest` claim in the JWT payload |
| `google_authorize` / `google_callback` | Not threading `guest_user_id` through the state JWT for promotion | Embed `guest_user_id` as an optional state claim; backend reads it on callback to choose promotion vs. normal login path |
| `user_manager.oauth_callback` | Calling it unchanged for promotion path | Do NOT call for promotion — write a custom `promote_guest_via_google` that updates the existing row and inserts into `oauth_accounts` |
| `import_service.run_import` | Assuming `user_id` changes during promotion (it does not with in-place update) | user_id is stable after in-place promotion — no import job re-association needed; but warn user to not use Google SSO while an import is running |
| `apply_game_filters` | Adding a `is_guest` filter to restrict certain endpoints for guest users | Add as an optional parameter with a default; do not hardcode guest checks inside the shared utility |
| `UserManager.on_after_login` | Not calling `on_after_login` after promotion (just as it is not called for OAuth flow today) | Manually update `last_login` in the promotion endpoint, the same way `google_callback` does it with `sa_update` |
| FastAPI-Users `SQLAlchemyBaseUserTable` | Assuming adding `is_guest` column is sufficient for query filtering | Also add a partial index `CREATE INDEX ... WHERE is_guest = true AND created_at < NOW() - INTERVAL '30 days'` for efficient cleanup queries |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No rate limiting on `POST /auth/guest/create` | Bots create thousands of guest accounts; disk fills; DB slows | Per-IP rate limit via slowapi (already used in project's async semaphore pattern); max 5 guest accounts per IP per hour | Noticeable at >100 bot requests/hour |
| Guest game data not cascade-deleted | Manual cleanup queries must enumerate child tables | Verify `ondelete="CASCADE"` on `games.user_id`, `game_positions.game_id`, `position_bookmarks.user_id`, `import_jobs.user_id` before shipping | 1,000+ accumulated guest users |
| Counting all guest users without an index | `SELECT count(*) FROM users WHERE is_guest = true` is a full table scan | Add `CREATE INDEX idx_users_is_guest_created_at ON users (is_guest, created_at)` in the migration | >50K user rows |
| Promotion endpoint without row-level lock | Concurrent promotions corrupt user row | Use `SELECT ... FOR UPDATE` or conditional `UPDATE WHERE email IS NULL` | Rare but catastrophic when it happens |
| Fetching full guest user list for cleanup script | Memory-intensive for large tables | Use keyset pagination: `WHERE is_guest = true AND created_at < cutoff AND id > :last_id LIMIT 100` | >10K guest rows to clean up |

---

## Security Mistakes

Domain-specific security issues for guest access and promotion.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No CSRF protection on OAuth state (CVE-2025-68481 pattern) | 1-click account takeover via login CSRF | Double-submit cookie: set `flawchess_oauth_csrf` cookie on authorize, validate on callback |
| Guest `user_id` accepted from request body in promotion endpoint | Attacker promotes someone else's guest account | Always derive `user_id` from the authenticated JWT, never from the request body |
| Email uniqueness checked only at DB level | 500 error on conflict instead of 409 with actionable message | Application-level pre-check: query for existing email before UPDATE; return 409 `{"code": "email_exists"}` |
| No validation that `guest_user_id` in OAuth state is actually a guest | Attacker embeds a registered user's `user_id` in the state, triggering a "promotion" that overwrites their account | Before executing promotion path, verify `User.is_guest == True` AND `User.email IS NULL` for the `guest_user_id` in the state claim |
| Guest accounts never expire | Unlimited data accumulation; privacy risk (GDPR: data must not be retained longer than necessary) | Set `is_guest = true` flag; delete after 30 days of inactivity (no login, no new games) |
| Promotion endpoint accessible without any auth | Anyone can call `POST /auth/promote` without a guest JWT | Require a valid JWT (guest or otherwise) — use `current_active_user` or equivalent dependency; promotion requires an authenticated session |

---

## UX Pitfalls

Common user experience mistakes for guest-to-registered flows.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No indication of guest status in the UI | User forgets they are a guest; imports games; closes tab; loses data | Show a persistent but non-intrusive banner: "You're using a guest account — sign up to save your data permanently" |
| Promotion form shows generic error on email conflict | User doesn't know whether to log in or try a different email | Return `{"code": "email_exists"}` from backend; frontend shows: "This email is already registered. Log in instead?" with a direct login link |
| Google SSO promotion button active while import is running | User promotes via Google, page redirect interrupts in-memory job, import fails | Disable or warn on the Google SSO button when `GET /imports/active` returns active jobs |
| After promotion, page shows guest info box again | User just promoted — showing "Sign up to save your data" is confusing | Immediately update auth state in the frontend after promotion response; hide guest-only UI elements reactively |
| No confirmation step before promotion | User accidentally promotes with wrong Google account | Show a confirmation step: "You're about to sign in as user@gmail.com — this will convert your guest account" |
| Promotion via email/password requires verification email before access is granted | User promotes, verification email goes to spam, they cannot use the app | Allow access with a "verification pending" state; show a persistent nudge to verify; do not block the full app behind verification |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Guest creation endpoint:** Rate limiting applied — verify `GET /auth/guest/create` (or equivalent) returns 429 after threshold from same IP.
- [ ] **OAuth CSRF protection:** `google_authorize` response sets `flawchess_oauth_csrf` cookie AND `google_callback` validates it — verify both sides, not just the state JWT signature check.
- [ ] **Google SSO promotion:** After flow completes, `SELECT * FROM users WHERE id = :guest_id` shows `email IS NOT NULL`, `is_guest = false` (or equivalent), and the guest row count has NOT increased.
- [ ] **Email conflict:** Promotion with an email that belongs to another user returns HTTP 409 with `{"code": "email_exists"}` — not 500 and not 200.
- [ ] **Old guest JWT after promotion:** Frontend stores the new JWT issued by the promotion response — verify via browser DevTools that `localStorage` no longer contains the pre-promotion token.
- [ ] **Active import during Google SSO promotion:** Start an import as a guest, then attempt Google SSO promotion — verify warning or block appears; verify import completes correctly.
- [ ] **Cascade delete:** Delete a promoted guest `User` row — verify all `games`, `game_positions`, `position_bookmarks`, and `import_jobs` rows are gone.
- [ ] **is_guest flag:** After promotion, `User.is_guest` (or equivalent field) is `false` — guest cleanup job would not target this user.
- [ ] **Mobile layout:** Guest info box and promotion CTA appear correctly at 375px — verify both the homepage "Use as Guest" button and the import page info box.
- [ ] **Safari / Firefox ETP:** Google SSO promotion tested in Safari (iOS + macOS) and Firefox with Enhanced Tracking Protection — promotion completes with guest data intact.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| OAuth CSRF vulnerability discovered post-ship | HIGH | Emergency deploy of double-submit cookie fix; rotate `SECRET_KEY` to invalidate all existing state JWTs; notify affected users if account linkage was observed |
| Guest data orphaned by failed Google SSO promotion | MEDIUM | Write a one-off script to reassociate `games.user_id` from the orphaned guest_id to the new registered user_id; verify uniqueness constraints don't block the update |
| Disk full from guest data accumulation | HIGH | Emergency cleanup: `DELETE FROM users WHERE is_guest = true AND created_at < NOW() - INTERVAL '7 days'` (aggressive; requires CASCADE on child tables to be confirmed first); expand disk on Hetzner |
| Concurrent promotion creates duplicate email | LOW | Catch `UniqueViolationError` at the endpoint; return 409; the second promotion attempt was redundant — user is already promoted |
| Old guest JWT used post-promotion for unauthorized access | LOW | No immediate recovery needed — same user_id, same data; wait for 7-day expiry; if urgent, implement token_version increment (requires migration + middleware change) |
| Google SSO creates new user instead of promoting guest | MEDIUM | Identify the orphaned guest row by `created_at` + `chess_com_username`/`lichess_username`; run SQL to update `games.user_id` to new user's id; delete orphaned guest row |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CVE-2025-68481 OAuth CSRF (Pitfall 1) | Guest creation backend — fix existing OAuth endpoints | `google_authorize` sets CSRF cookie; `google_callback` validates it; integration test passes |
| Guest JWT valid post-promotion (Pitfall 2) | Account promotion endpoint | Promotion response includes fresh JWT; frontend test confirms old token is replaced |
| Guest identity lost in OAuth redirect (Pitfall 3) | Account promotion backend — Google SSO path | `state` JWT contains `guest_user_id`; callback correctly routes to promotion path |
| Concurrent promotion race (Pitfall 4) | Account promotion endpoint | `UPDATE ... WHERE email IS NULL` or `SELECT FOR UPDATE` used; concurrent request returns 409 not 500 |
| Email conflict during promotion (Pitfall 5) | Account promotion endpoint | 409 with `email_exists` code returned; no 500 on duplicate email |
| Active import orphaned during Google SSO (Pitfall 6) | Promotion UI | Active import check before Google SSO button is enabled; warning displayed |
| Guest accumulation / table bloat (Pitfall 7) | Guest creation backend | `is_guest` flag set; DB index created; cleanup script written |
| HttpOnly cookie conflicts with Bearer (Pitfall 8) | Guest creation backend — transport decision | Single Bearer transport for all JWTs; no cookie transport mixed in |
| SameSite cookie lost on redirect (Pitfall 9) | Account promotion backend — Google SSO path | `guest_user_id` in state JWT, not in cookie; Safari + Firefox tested |
| `associate_by_email=True` orphans guest data (Pitfall 10) | Account promotion backend — Google SSO path | Custom `promote_guest_via_google` function; integration test confirms zero orphaned guest rows |

---

## Sources

- Codebase: `app/routers/auth.py`, `app/users.py`, `app/services/import_service.py`, `app/models/user.py`, `app/models/game.py` — HIGH confidence (direct inspection)
- [CVE-2025-68481: 1-click Account Takeover in Apps Using FastAPI SSO — GitHub Advisory](https://github.com/fastapi-users/fastapi-users/security/advisories/GHSA-5j53-63w8-8625) — HIGH confidence (official advisory)
- [CVE-2025-68481 — GitLab Advisory Database](https://advisories.gitlab.com/pkg/pypi/fastapi-users/CVE-2025-68481/) — HIGH confidence
- [Add a double-submit cookie in the OAuth flow — fastapi-users commit 7cf413c](https://github.com/fastapi-users/fastapi-users/commit/7cf413cd766b9cb0ab323ce424ddab2c0d235932) — HIGH confidence (official fix)
- [Auth0: SameSite Cookie Attribute Changes](https://auth0.com/docs/manage-users/cookies/samesite-cookie-attribute-changes) — MEDIUM confidence (authoritative vendor docs)
- [Gotchas With Same Site Strict Cookie and OAuth — hrishikeshpathak.com](https://hrishikeshpathak.com/blog/gotchas-with-same-site-strict-cookie-and-oauth/) — MEDIUM confidence
- [Audiobookshelf issue #5127 — Firefox bounce-tracking strips OIDC session cookie](https://github.com/advplyr/audiobookshelf/issues/5127) — MEDIUM confidence (real-world Firefox ETP issue)
- [Curity: OAuth and Same Site Cookies best practices](https://curity.io/resources/learn/oauth-cookie-best-practices/) — MEDIUM confidence
- [Stop Duplicate Records: Fix Race Conditions Using Unique Database Indexes](https://medium.com/@itsvinayc/race-conditions-in-web-apps-and-how-a-unique-index-can-save-you-736d682dabfb) — MEDIUM confidence
- [Descope: How to Invalidate a JWT Token After Logout](https://www.descope.com/blog/post/jwt-logout-risks-mitigations) — MEDIUM confidence

---
*Pitfalls research for: FlawChess v1.8 — Guest access with account promotion to existing FastAPI-Users system*
*Researched: 2026-04-06*

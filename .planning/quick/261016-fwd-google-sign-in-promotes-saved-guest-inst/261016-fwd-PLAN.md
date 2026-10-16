---
phase: quick-261016-fwd
plan: 01
quick_id: 261016-fwd
mode: quick
type: execute
wave: 1
depends_on: []
files_modified:
  - app/routers/auth.py
  - app/services/guest_service.py
  - tests/test_guest_google_promotion.py
  - tests/test_guest_auth.py
  - frontend/src/api/googleAuth.ts
  - frontend/src/api/__tests__/googleAuth.test.ts
  - frontend/src/hooks/useAuth.ts
  - frontend/src/hooks/__tests__/useAuth.test.tsx
  - frontend/src/App.tsx
  - frontend/src/components/library/NoEngineAnalysisFlawsState.tsx
  - frontend/src/components/library/__tests__/NoEngineAnalysisFlawsState.test.tsx
  - CHANGELOG.md
autonomous: true
requirements: ["QUICK-261016-fwd"]

estimate:
  tokens: 85000
  raw_tokens: 85000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A guest who logged out (auth_token cleared, guest_token kept) and clicks a Google button triggers GET /api/auth/google/authorize-promote with the guest Bearer token, so Google redirects back to /api/auth/google/callback-promote"
    - "Retrying Google sign-in after abandoning or back-buttoning the Google screen still uses the promote endpoint (nothing is consumed on the first attempt)"
    - "callback-promote with a Google identity that belongs to no account promotes the guest in place: same user id, is_guest False, redirect fragment carries promoted=1"
    - "callback-promote with a Google identity whose email (case-insensitive) or Google account id already belongs to a registered user signs THAT user in (token sub = existing id, no promoted=1, password_replaced=1 when it was an unverified password account) and leaves the guest row untouched, with no EMAIL_ALREADY_REGISTERED lockout"
    - "Bad CSRF or a wrong state audience on callback-promote is rejected with 400 before the Google code exchange and before any account lookup"
    - "After promotion (email or Google) the guest's old JWT returns 401, and the JWT returned by the promotion authenticates"
    - "authorize-promote answering 401 or 403 drops guest_token and falls back to plain /auth/google/authorize; any other failure (network, 5xx, timeout) rejects so the form shows 'Could not start Google sign-in. Please try again.' and guest_token is kept"
    - "The Flaws-tab guest 'Sign up free' button lands on the register tab instead of bouncing back to /"
  artifacts:
    - path: "app/routers/auth.py"
      provides: "_complete_google_sign_in (shared sign-in tail used by both Google callbacks) and _existing_google_user (oauth-account-or-email owner lookup); callback-promote signs existing accounts in instead of colliding"
      contains: "_existing_google_user"
    - path: "app/services/guest_service.py"
      provides: "token_version bump in both promotion UPDATEs (single-use guest JWT)"
      contains: "token_version=User.token_version + 1"
    - path: "frontend/src/api/googleAuth.ts"
      provides: "guest_token-driven promote routing with a 401/403-only plain fallback"
      exports: ["getGoogleAuthorizationUrl"]
    - path: "frontend/src/components/library/__tests__/NoEngineAnalysisFlawsState.test.tsx"
      provides: "CTA handoff test (logoutForPromotion + hard navigation)"
  key_links:
    - from: "app/routers/auth.py::google_callback_promote"
      to: "app/routers/auth.py::_complete_google_sign_in"
      via: "existing-account branch after _existing_google_user returns a user"
      pattern: "_complete_google_sign_in\\("
    - from: "app/routers/auth.py::google_callback"
      to: "app/routers/auth.py::_complete_google_sign_in"
      via: "plain callback tail, no duplicated sign-in logic"
      pattern: "_complete_google_sign_in\\("
    - from: "frontend/src/api/googleAuth.ts"
      to: "GET /api/auth/google/authorize-promote"
      via: "apiClient.get with Authorization Bearer guest_token whenever guest_token exists"
      pattern: "authorize-promote"
    - from: "frontend/src/components/library/NoEngineAnalysisFlawsState.tsx"
      to: "useAuth().logoutForPromotion"
      via: "onClick then window.location.href = '/login?tab=register'"
      pattern: "logoutForPromotion\\(\\)"
---

<objective>
Make Google sign-up after guest use promote the saved guest instead of creating a duplicate
account. The backend decides: whenever the SPA holds a persisted guest_token it starts the
promote flow, and `callback-promote` signs an already-registered Google identity into its
existing account (guest untouched) instead of colliding, so the 2026-06-23 lockout that the
one-shot frontend intent flag was guarding against can no longer happen. The intent flag is
then removed, promotion makes the old guest JWT single-use, and the dead Flaws-tab guest CTA
is fixed.

Purpose: since the 2026-06-23 fix, 20 registered accounts were created within 48h of a
same-username guest instead of promoting it (Umami-confirmed). Two causes, both closed here:
(1) logout clears the intent flag, so a logged-out guest's Google sign-up runs the plain flow
with no token and FastAPI-Users creates a fresh user; (2) the flag is consumed before the
Google round-trip, so an abandoned-and-retried Google sign-up also runs the plain flow.

Output: backend callback change + single-use guest token (Task 1, tracer), frontend routing +
dead-plumbing removal + CTA fix (Task 2), CHANGELOG + full pre-merge gate + browser UAT
description for the orchestrator (Task 3).

Locked design items (owner-approved, from the planning context) and where each is covered:

| Item | What | Task |
|------|------|------|
| A | callback-promote: existing Google identity (oauth account OR email) gets a normal sign-in via a shared helper; else promote; keep UserAlreadyExists race fallback | 1 |
| B | token_version bump in both promotion UPDATEs | 1 |
| C | googleAuth.ts: guest_token alone drives the promote endpoint; plain fallback only on 401/403; rethrow everything else | 2 |
| D | remove the dead intent-flag plumbing (useAuth, constant, App.tsx comment) | 2 |
| E | NoEngineAnalysisFlawsState CTA: logoutForPromotion + hard navigation | 2 |
| F | backend + frontend tests | 1, 2 |
| G | browser UAT (orchestrator runs it after execution) | 3 (human-check) |
| CHANGELOG | user-facing [Unreleased] bullet | 3 |

Out of scope (do NOT change; mention in SUMMARY as follow-ups if you notice them): the
duplicated state/CSRF validation at the top of both callbacks; the email sign-up path in
`frontend/src/components/auth/RegisterForm.tsx` that drops guest_token on any non-409/400 error;
the 401 response interceptor's `isAuthRoute` check in `frontend/src/api/client.ts`; the
IntegrityError rollback path in `promote_guest_with_google`.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/CLAUDE.md
@app/routers/auth.py
@app/services/guest_service.py
@frontend/src/api/googleAuth.ts

<interfaces>
Existing, verified against the current tree (do not re-explore):

app/routers/auth.py
- `_CSRF_COOKIE = "flawchess_oauth_csrf"`, `_OAUTH_STATE_AUDIENCE`, `_OAUTH_PROMOTE_STATE_AUDIENCE` (module constants).
- `async def _exchange_google_code(code: str, redirect_url: str) -> OAuth2Token | None` (None on a failed exchange; caller returns `_google_signin_failed_redirect(frontend_base)`).
- `def _google_identity(token: OAuth2Token) -> tuple[str, str]` returns `(account_id, account_email)`, raises 400 unless `email_verified`.
- `google_callback(request, code, state, error, user_manager: UserManager = Depends(get_user_manager)) -> RedirectResponse`: lines ~335-371 are the tail to extract (google_sign_in with `except UserAlreadyExists` -> 400 "User already exists with a different OAuth account"; `is_active` check -> 400; last_login UPDATE via `async_session_maker()`; `auth_backend.get_strategy().write_token(user)` with its existing `# ty: ignore[unresolved-attribute]`; redirect `{frontend_base}/auth/callback#token=...` plus `&password_replaced=1` when flagged).
- `google_callback_promote(request, session: Annotated[AsyncSession, Depends(get_async_session)], code, state, error) -> RedirectResponse`: validates state (promote audience) -> CSRF double-submit -> guest_user_id from state -> `session.get(User, guest_user_id)` must be a guest -> resolves bases -> exchange -> `_google_identity` -> `guest_service.promote_guest_with_google(...)` with `except UserAlreadyExists` -> redirect `#error=EMAIL_ALREADY_REGISTERED` and `except Exception` -> Sentry + 500 -> last_login UPDATE -> redirect `#token=...&promoted=1`.
- Current import: `from fastapi_users.exceptions import InvalidPasswordException, UserAlreadyExists`.

app/users.py
- `UserManager.google_sign_in(*, account_id, account_email, access_token, expires_at, refresh_token, request) -> tuple[User, bool]` (user, password_replaced). Replaces the password and bumps token_version when linking to an UNVERIFIED account.
- FastAPI-Users `UserManager.get_by_oauth_account(oauth: str, account_id: str)` and `UserManager.get_by_email(user_email: str)` both raise `fastapi_users.exceptions.UserNotExists`; `get_by_email` is case-insensitive (SQLAlchemyUserDatabase compares lowercased).
- `google_oauth_client.name == "google"` (already imported in auth.py).
- `get_user_manager` -> `get_user_db` -> `Depends(get_async_session)`: FastAPI caches the dependency per request, so the user manager shares the endpoint's `session`.
- `VersionedJWTStrategy.read_token` rejects a token whose `tv` claim differs from `User.token_version`; guest JWTs live 365 days (`_GUEST_JWT_LIFETIME_SECONDS`).

app/services/guest_service.py
- `promote_guest_with_password` and `promote_guest_with_google` each run one `sa_update(User).where(User.id == user.id).values(...)`, commit, then `session.get` + `session.refresh(updated)` BEFORE `write_token(updated)`. The refresh is what makes the returned JWT carry the bumped version; keep that order.

tests/test_guest_google_promotion.py
- Helpers: `unique_email(prefix)`, `register_user(client, email, password)` (response JSON has `id`), `make_fake_token_response(sub, email)` (id_token with `email_verified: True`).
- `class TestCallbackPromote` with `setup_method` clearing `guest_create_limiter._timestamps`, `_make_valid_state_jwt(guest_user_id, csrf_token)`, `_decode_user_id_from_token(token) -> int`. Tests use `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", cookies={_CSRF_COOKIE: csrf_token})` and patch `app.routers.auth.google_oauth_client.get_access_token` with `AsyncMock`.
- Existing tests to EXTEND or REWRITE: `test_callback_promote_with_mocked_google`, `test_callback_promote_email_collision` (its expectation is now wrong, see Task 1), `test_callback_promote_invalid_csrf`, `test_callback_promote_invalid_state_audience`.
- The file has no row-cleanup idiom: each pytest session clones its own DB, and these tests insert users only (no games), so they cannot leak into the eval lottery. Do NOT insert games; if you ever must, add a `finally` delete like `tests/test_guest_auth.py::test_train_state_preserved_after_promotion`.

frontend/src/api/client.ts
- Request interceptor overwrites `Authorization` with the stored `auth_token` when one exists.
- Response interceptor on 401 does not redirect when `window.location.pathname === '/login'`; both callers of `getGoogleAuthorizationUrl` (LoginForm, RegisterForm) render on `/login`, so a 401 from authorize-promote does not bounce the page. Do not change client.ts.

frontend tests
- `frontend/src/components/train/__tests__/SignupAskActions.test.tsx` is the pattern for a CTA handoff test: `vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ logoutForPromotion: mockLogoutForPromotion }) }))` and a `window.location` stub via `Object.defineProperty(window, 'location', { configurable: true, value: { ...originalLocation, href: '' } })` restored in `afterEach`.
- `frontend/src/pages/library/__tests__/FlawsTab.test.tsx` already mocks `useAuth` with `logoutForPromotion`, so FlawsTab keeps rendering once NoEngineAnalysisFlawsState calls `useAuth()`.
</interfaces>
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Backend decides: callback-promote signs existing Google accounts in, promotion kills the guest JWT</name>
  <files>app/routers/auth.py, app/services/guest_service.py, tests/test_guest_google_promotion.py, tests/test_guest_auth.py</files>
  <read_first>app/routers/auth.py (lines 138-205 helpers, 282-371 google_callback, 458-562 google_callback_promote), app/services/guest_service.py, tests/test_guest_google_promotion.py (lines 1-70 helpers, 449-689 TestCallbackPromote), tests/test_guest_auth.py (lines 536-595 TestGuestPromotion)</read_first>
  <precondition>Dev PostgreSQL is running (docker compose -f docker-compose.dev.yml -p flawchess-dev up -d) so pytest can clone its template database.</precondition>
  <behavior>
    In `TestCallbackPromote` (tests/test_guest_google_promotion.py), all via `/api/auth/google/callback-promote` with a mocked `get_access_token`:
    - (1) EXTEND `test_callback_promote_with_mocked_google`: new Google identity -> 302 with `promoted=1`; `_decode_user_id_from_token(new_token) == guest_user_id` (same row); profile with new token is 200 and `is_guest` False; profile with the ORIGINAL guest_token is now 401 (item B, Google path).
    - (2) REPLACE `test_callback_promote_email_collision` with `test_callback_promote_existing_email_signs_in_existing_account`: register `existing_email` via `register_user` (keep its `id`), create a guest, Google id_token email = `existing_email.upper()` (proves the case-insensitive lookup that the prod collision depended on). Expect 302 whose fragment has a `token` decoding to the EXISTING user's id, no `promoted` key, no `error` key, `password_replaced` == "1" (unverified password account protection still runs); profile with the guest_token is still 200 with `is_guest` True (guest untouched).
    - (3) NEW `test_callback_promote_linked_google_account_signs_in_owner`: guest A promoted through callback-promote with (sub S, email A); then guest B runs callback-promote with (sub S, a DIFFERENT fresh email B). Expect token sub == guest A's id, no `promoted`, no `password_replaced`, guest B profile (its guest_token) still 200 with `is_guest` True.
    - (4) EXTEND `test_callback_promote_invalid_csrf` and `test_callback_promote_invalid_state_audience`: wrap the request in patches of `app.routers.auth.google_oauth_client.get_access_token` and `app.routers.auth._existing_google_user` (both `AsyncMock`), keep the 400 assertion, and assert both mocks were NOT awaited (rejection happens before exchange and lookup).
    - (5) NEW `test_callback_promote_race_collision_still_redirects_email_already_registered`: register an email, patch `app.routers.auth._existing_google_user` to return None (simulates the account appearing between lookup and promotion), Google email = that email -> 302 location contains `EMAIL_ALREADY_REGISTERED` (kept fallback).
    In `TestGuestPromotion` (tests/test_guest_auth.py):
    - (6) NEW `test_guest_token_rejected_after_email_promotion`: create guest, promote via `/api/auth/guest/promote/email`; profile with the original guest_token -> 401; profile with the returned token -> 200, `is_guest` False (item B, email path).
  </behavior>
  <action>
    RED: write tests (2), (3), (6) and the new assertions in (1) first, run them, confirm they fail on the current code ((2) currently gets EMAIL_ALREADY_REGISTERED, (3) gets a collision or a promotion, (1)/(6) old guest token still returns 200). Do not over-assert on the race test (5) before the helper exists; add it together with GREEN.

    GREEN, router (app/routers/auth.py), per locked item A:
    - Import `UserNotExists` alongside `InvalidPasswordException, UserAlreadyExists` from `fastapi_users.exceptions`.
    - Add `async def _existing_google_user(user_manager: UserManager, account_id: str, account_email: str) -> User | None`: return `await user_manager.get_by_oauth_account(google_oauth_client.name, account_id)` if it does not raise `UserNotExists`, else `await user_manager.get_by_email(account_email)` if that does not raise, else None. Two flat try/except blocks with early returns, depth at most 2. Docstring: the account a Google identity already belongs to, by linked Google account id first, then by (case-insensitive) email.
    - Add `async def _complete_google_sign_in(request: Request, user_manager: UserManager, token: OAuth2Token, account_id: str, account_email: str, frontend_base: str) -> RedirectResponse` containing the body currently at the tail of `google_callback`, moved verbatim (google_sign_in call and its UserAlreadyExists -> 400, is_active -> 400, last_login UPDATE through `async_session_maker()`, write_token keeping its existing `# ty: ignore[unresolved-attribute]` comment with reason, redirect with `&password_replaced=1` when flagged, the existing explanatory comments). `google_callback` then ends with `account_id, account_email = _google_identity(token)` followed by returning `await _complete_google_sign_in(...)`. No duplicated sign-in logic anywhere.
    - In `google_callback_promote`, add `user_manager: Annotated[UserManager, Depends(get_user_manager)]` right after `session` (same per-request session via FastAPI's dependency cache). Leave state decode, CSRF double-submit check, guest_user_id extraction, the guest-row check, base resolution, the exchange and `_google_identity` exactly where they are. Directly after `_google_identity`, call `_existing_google_user`; if it returns a user, return `await _complete_google_sign_in(request, user_manager, token, account_id, account_email, frontend_base)` and do NOT touch the guest (no merge, no promotion, no `promoted=1`). Otherwise run the existing promotion block unchanged, keeping `except UserAlreadyExists -> EMAIL_ALREADY_REGISTERED` (now the race fallback) and the generic `except Exception` Sentry capture.
    - Fix-site comment above the new branch (CLAUDE.md "comment bug fixes"): what broke (since the 2026-06-23 fix, guest promotion was gated on a one-shot frontend flag; logging out or retrying an abandoned Google screen lost it and the plain flow created duplicate accounts, 20 in prod) and why this is safe. Security rationale, keep all points: the branch grants nothing beyond what plain `/callback` already grants to whoever completes Google auth for that identity; the promote state JWT stays audience-separated (`_OAUTH_PROMOTE_STATE_AUDIENCE`) and the CSRF double-submit is validated BEFORE any lookup; guest_user_id comes only from the server-signed state; `_google_identity` still requires `email_verified`; unverified email/password accounts keep the password-replacement protection because the same `google_sign_in` runs. Also note this is what lets the SPA start promotion from a stale guest_token without locking a returning registered user out.
    - Update the `google_callback_promote` docstring: existing Google identity -> normal sign-in of that account (guest untouched); otherwise in-place promotion with `promoted=1`; `EMAIL_ALREADY_REGISTERED` only on a lookup/promotion race.
    - No new Sentry capture is needed: `UserNotExists` is an expected condition. No variables in any new error message.

    GREEN, service (app/services/guest_service.py), per locked item B: in BOTH `promote_guest_with_password` and `promote_guest_with_google`, add `token_version=User.token_version + 1` to the existing `.values(...)` of the UPDATE that flips `is_guest` (same statement, not a second UPDATE). Short comment at each site: promotion is now started by the mere presence of a persisted guest_token, so the long-lived (365-day) guest JWT must stop authenticating the now-registered account; the refresh below makes the returned JWT carry the new version. Update both docstrings' "Updates the user row" sentence to mention the bump. Keep `session.refresh(updated)` before `write_token`.

    Run the full set in verify (the plain-callback regression suite `tests/test_google_link_takeover.py` proves the extraction changed nothing for `/callback`; `tests/test_impersonation.py` and `tests/test_email_case_uniqueness.py` must still pass). Before committing, confirm `git branch --show-current` prints `main` (the GSD commit helper can recreate a phase branch under branching_strategy phase).

    Commit: `fix(auth): Google callback-promote signs existing accounts in and promotion revokes the guest JWT (quick 261016-fwd)`.
  </action>
  <verify>
    <automated>uv run pytest tests/test_guest_google_promotion.py tests/test_guest_auth.py tests/test_google_link_takeover.py tests/test_email_case_uniqueness.py tests/test_impersonation.py -n auto -q && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && uv run ty check app/ tests/ && uv run ruff check app/ tests/ && test "$(grep -c 'token_version=User.token_version + 1' app/services/guest_service.py)" -ge 2 && test "$(grep -c '_complete_google_sign_in(' app/routers/auth.py)" -ge 3</automated>
  </verify>
  <done>Tests (1)-(6) pass and the five listed test files are green; callback-promote signs an existing Google identity (by email, case-insensitive, or by linked account id) into its account with the guest left a guest; new identities still promote in place; bad CSRF/audience is rejected before exchange and lookup; old guest JWTs die at promotion on both paths; depth gate, ty and ruff clean; committed on main.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Frontend: guest_token alone routes Google to promotion, dead intent plumbing removed, Flaws CTA fixed</name>
  <files>frontend/src/api/googleAuth.ts, frontend/src/api/__tests__/googleAuth.test.ts, frontend/src/hooks/useAuth.ts, frontend/src/hooks/__tests__/useAuth.test.tsx, frontend/src/App.tsx, frontend/src/components/library/NoEngineAnalysisFlawsState.tsx, frontend/src/components/library/__tests__/NoEngineAnalysisFlawsState.test.tsx</files>
  <read_first>frontend/src/api/googleAuth.ts, frontend/src/api/__tests__/googleAuth.test.ts, frontend/src/hooks/useAuth.ts (lines 180-243), frontend/src/hooks/__tests__/useAuth.test.tsx (lines 1-160), frontend/src/App.tsx (lines 795-806), frontend/src/components/library/NoEngineAnalysisFlawsState.tsx, frontend/src/components/library/EvalCoverageBadge.tsx (lines 14-35, the working CTA), frontend/src/components/train/__tests__/SignupAskActions.test.tsx (lines 1-50)</read_first>
  <behavior>
    googleAuth.test.ts (rewrite for the new contract; keep the existing `vi.mock('@/api/client', ...)` shape and PROMOTE_URL/PLAIN_URL constants):
    - guest_token present, no other setup -> exactly one GET to a path containing `/auth/google/authorize-promote` with config `{ headers: { Authorization: 'Bearer <guest_token>' } }`; resolves PROMOTE_URL; guest_token still stored.
    - `it.each([401, 403])`: promote GET rejects with an AxiosError carrying that response status -> guest_token removed, second GET is plain `/auth/google/authorize` (not authorize-promote), resolves PLAIN_URL.
    - promote GET rejects with an AxiosError with response status 500, and separately with a network AxiosError (code `ERR_NETWORK`, no response) -> the promise rejects, only ONE GET was made, guest_token is still stored.
    - no guest_token -> one plain GET, resolves PLAIN_URL.
    Build errors with a small local helper using `AxiosError` and `AxiosHeaders` from `axios` (response object `{ status, statusText: '', headers: {}, config: { headers: new AxiosHeaders() }, data: {} }`), since googleAuth.ts reads the real `axios.isAxiosError`.
    useAuth.test.tsx:
    - `logoutForPromotion` tests (both the top-level one and the one in "admin stash hygiene") assert auth_token cleared, guest_token kept ('guest-token-value'), admin stash removed where applicable, and `window.location.href` still '' (no navigation). Rename the test titles to drop the intent wording. No assertion may reference the removed storage key.
    NoEngineAnalysisFlawsState.test.tsx (new, jsdom, SignupAskActions pattern, render inside `MemoryRouter`):
    - guest: clicking `btn-signup-for-analysis-flaws` calls the mocked `logoutForPromotion` once and sets `window.location.href` to '/login?tab=register'; the button keeps `data-umami-event="signup-cta"` and `data-umami-event-source="flaws-no-analysis"`.
    - non-guest: renders `btn-go-to-games` and no `btn-signup-for-analysis-flaws`.
  </behavior>
  <action>
    RED: rewrite googleAuth.test.ts, update useAuth.test.tsx and create NoEngineAnalysisFlawsState.test.tsx per the behavior block; run them and confirm the new googleAuth cases (promote without intent, 403 fallback, 500/network rethrow) and the CTA test fail.

    GREEN, frontend/src/api/googleAuth.ts (locked item C):
    - Delete the `PROMOTE_INTENT_KEY` constant and every read/write of the sessionStorage intent key.
    - Add `import axios from 'axios'` and a named constant `GUEST_TOKEN_REJECTED_STATUSES: ReadonlySet<number> = new Set([401, 403])` with a one-line comment (401 = guest token invalid or expired, 403 = the account is no longer a guest, i.e. already promoted). Add an unexported `isRejectedGuestToken(err: unknown): boolean` that is true only for an AxiosError whose `response` exists and whose status is in that set.
    - `getGoogleAuthorizationUrl()`: if `localStorage.guest_token` exists, GET `/auth/google/authorize-promote?origin=${origin}` with `headers: { Authorization: 'Bearer ' + guestToken }` and return its `authorization_url`. In the catch: if `isRejectedGuestToken(err)` remove guest_token and fall through to the plain call; otherwise re-throw so the caller's existing catch shows "Could not start Google sign-in. Please try again." No guest_token: plain `/auth/google/authorize?origin=...` as today. Explicit return type, nesting depth at most 3.
    - Comment at the request call: the apiClient request interceptor overwrites Authorization with `auth_token` when one is stored; that only happens for a logged-in guest, whose auth_token is the same guest account, so the promote request still authenticates as that guest. Comment at the rethrow: falling back to the plain flow on a transient error is exactly what orphaned guests (plain flow creates a new account), so only a definitive rejection may fall back.
    - Rewrite the long doc comment to the new contract: a persisted guest_token always starts the promote flow; the backend then signs the Google identity into its existing account when it already has one (guest untouched) and promotes the guest in place otherwise, so a stale guest_token can no longer lock a returning registered user out (the 2026-06-23 regression stays fixed, now server-side); nothing is consumed before the Google round-trip, so a retried sign-up still promotes; the plain endpoint remains guest-aware for a logged-in guest. Describe the old mechanism by concept only (for example "the old one-shot sign-up intent flag"), never by its storage key name.

    GREEN, dead plumbing (locked item D):
    - frontend/src/hooks/useAuth.ts: in `logout`, delete the sessionStorage removal and its comment. In `logoutForPromotion`, delete the sessionStorage write and replace its comment with a short one: guest_token is preserved so the register flow (email or Google) promotes the saved guest in place; the backend signs a returning user into their existing account instead (see getGoogleAuthorizationUrl). Keep `logoutForPromotion` itself, its `useCallback`, and the "No redirect, caller navigates" note.
    - frontend/src/App.tsx (~line 800): reword the HANDOFF-02/D-12 comment so it no longer references googleAuth.ts or the removed flag; keep its substance (capture the desktop-to-phone QR handoff marker on first load because ProtectedLayout is the stable mount point that sees the raw URL before Google's redirect chain strips the query string).
    <!-- planner-discipline-allow: promote_intent -->
    - After these edits `grep -rni 'promote_intent' frontend/src` must print nothing, including tests and comments.

    GREEN, frontend/src/components/library/NoEngineAnalysisFlawsState.tsx (locked item E): import `useAuth` from `@/hooks/useAuth`, take `logoutForPromotion` from it, and change the guest button's onClick to call `logoutForPromotion()` then set `window.location.href = '/login?tab=register'`, exactly like `CoverageSignupButton` in EvalCoverageBadge.tsx. Keep the umami attributes, testid, aria-label and variant. Drop `useNavigate` from the react-router import (keep `Link`, still used by the non-guest branch). Add a fix-site comment: the old client-side navigate ran while the guest JWT was still stored, so AuthPage treated the guest as signed in and bounced them to `/` (dead button); dropping auth_token first (guest_token kept for promotion) and doing a full-page navigation matches the working CTAs. Update the component docblock's guest bullet accordingly.

    Before committing, confirm `git branch --show-current` prints `main`.

    Commit: `fix(auth): guest_token alone routes Google sign-up to promotion; fix Flaws guest sign-up CTA (quick 261016-fwd)`.
  </action>
  <verify>
    <automated>npm --prefix frontend test -- src/api/__tests__/googleAuth.test.ts src/hooks/__tests__/useAuth.test.tsx src/components/library/__tests__/NoEngineAnalysisFlawsState.test.tsx src/pages/library/__tests__/FlawsTab.test.tsx && npm --prefix frontend run lint && npm --prefix frontend run build && npm --prefix frontend run knip && ! grep -rni 'promote_intent' frontend/src</automated>
  </verify>
  <done>All four vitest files pass; googleAuth routes to authorize-promote whenever guest_token exists, falls back to plain only on 401/403 (dropping guest_token) and rethrows network/5xx with guest_token kept; no trace of the intent flag remains in frontend/src; the Flaws-tab guest CTA calls logoutForPromotion and hard-navigates to the register tab; lint (max-depth), tsc -b build and knip clean; committed on main.</done>
</task>

<task type="auto">
  <name>Task 3: CHANGELOG, full pre-merge gate, and browser UAT checkpoint (orchestrator-run)</name>
  <files>CHANGELOG.md</files>
  <read_first>CHANGELOG.md (lines 1-60, the [Unreleased] section and its ### Fixed list)</read_first>
  <precondition>Dev PostgreSQL is running (docker compose -f docker-compose.dev.yml -p flawchess-dev up -d).</precondition>
  <action>
    Append two bullets to the END of the `### Fixed` list under `## [Unreleased]` in CHANGELOG.md (plain words, no em-dash):
    - "Signing up with Google after using FlawChess as a guest now keeps your guest data even if you logged out first or retried the Google sign-in."
    - "Library: the guest "Sign up free" button on the Flaws tab now opens the sign-up form instead of doing nothing."

    Then run the full pre-merge gate from CLAUDE.md (the verify command below), each step in the foreground with a 600000 ms Bash timeout. Never background a command (a backgrounded run dies with the executor). If ty reports unresolved imports in maia_engine.py in a fresh worktree, run `uv sync --group maia-inference` and re-run. Fix every failure; if a formatter or autofix rewrites files, commit those with a `style(...)` or `chore(...)` prefix. Do not use prettier on the frontend.

    Commit the CHANGELOG: `docs(changelog): Google sign-up keeps guest data (quick 261016-fwd)`. Before committing, confirm `git branch --show-current` prints `main`.

    The browser UAT below is run by the orchestrator in Chrome after execution; the executor does not pause for it. Make sure the SUMMARY lists it verbatim as pending orchestrator UAT.
  </action>
  <verify>
    <automated>uv run ruff format app/ tests/ scripts/ analysis/ && uv run ruff check . --fix && uv run ty check app/ tests/ scripts/ && uv run --project analysis --with ty ty check analysis/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && uv run pytest -n auto -x && ( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )</automated>
    <human-check>
      Browser UAT on the dev build at http://localhost:5173 (backend on :8000), run by the orchestrator in Chrome. Real Google OAuth cannot be completed headlessly; the callback leg is covered by Task 1's endpoint tests. Use the network log (main-thread fetches are visible) or, if the Google button is hidden because Google OAuth is not configured in dev, import `/src/api/googleAuth.ts` through Vite in the page and call `getGoogleAuthorizationUrl()` directly as evidence.
      (a) Fresh storage, click "Use as Guest" (`btn-guest`) so localStorage holds guest_token and auth_token. Log out, confirm auth_token is gone and guest_token remains. Open /login?tab=register and click "Sign up with Google" (`btn-register-google`). Expect GET /api/auth/google/authorize-promote?origin=... with `Authorization: Bearer <guest_token>`, status 200, and the returned authorization_url's `redirect_uri` ending in `/api/auth/google/callback-promote`. No request to the plain /api/auth/google/authorize.
      (b) Go back from the Google screen (or reload /login?tab=register) and click the Google button again: again authorize-promote with the guest Bearer, not the plain endpoint. Repeat once via a CTA path: as a guest click a "Sign up free" CTA, go back from Google, retry, same result.
      (c) As a guest with imported but unanalyzed games, open Library, Flaws tab: the "Sign up free" button (`btn-signup-for-analysis-flaws`) lands on /login?tab=register showing the Create Account form, not bounced to /.
      (d) Set localStorage guest_token to an invalid string and click the Google button: authorize-promote returns 401, then a plain /api/auth/google/authorize request follows, guest_token is removed from localStorage, and the page is not redirected to a bare /login loop.
      (e) Clear storage entirely: the Google button calls only the plain /api/auth/google/authorize.
    </human-check>
  </verify>
  <done>CHANGELOG has both bullets under [Unreleased] / Fixed; every pre-merge gate step passes (ruff format/check, ty for app/tests/scripts and analysis, depth gate, full pytest -n auto -x, frontend lint, build, vitest, knip); all work committed on main; SUMMARY lists the browser UAT (a)-(e) as pending orchestrator verification.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Google -> GET /api/auth/google/callback-promote | Untrusted browser redirect carrying `code` and `state`; identity comes from Google's token endpoint over TLS |
| SPA -> GET /api/auth/google/authorize-promote | Bearer guest_token from localStorage, possibly stale, invalid, or belonging to an already-promoted account |
| Stored guest JWT -> any authenticated endpoint | 365-day credential that used to keep working after its account was promoted |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fwd-01 | Spoofing / Elevation | google_callback_promote existing-account branch | high | mitigate | Branch runs only after the promote-audience state JWT decodes (`_OAUTH_PROMOTE_STATE_AUDIENCE`) and the CSRF double-submit cookie matches; it calls the same `_complete_google_sign_in` as plain `/callback`, so it grants exactly what completing Google auth for that identity already grants. Test (4) asserts rejection happens before the exchange and before `_existing_google_user`. |
| T-fwd-02 | Spoofing | pre-registered unverified email/password account (account takeover via Google link) | high | mitigate | Existing-account branch runs `UserManager.google_sign_in`, which replaces the unverified account's password and bumps its token_version; `_google_identity` still requires `email_verified`. Test (2) asserts `password_replaced=1`. |
| T-fwd-03 | Elevation of privilege | guest JWT after promotion | medium | mitigate | `token_version = User.token_version + 1` in both promotion UPDATEs; `VersionedJWTStrategy.read_token` rejects the old guest JWT. Tests (1) and (6) assert 401 for the old token and 200 for the new one. |
| T-fwd-04 | Tampering | guest_user_id selection | medium | mitigate | guest_user_id is read only from the server-signed state JWT, never from the query string; the guest row must still be `is_guest` before any exchange (unchanged code). |
| T-fwd-05 | Tampering (data integrity) | guest data orphaned by a transient frontend error | medium | mitigate | googleAuth.ts falls back to the plain flow only on 401/403 (`GUEST_TOKEN_REJECTED_STATUSES`); network/5xx errors rethrow and keep guest_token. Vitest cases cover 401, 403, 500 and network. |
| T-fwd-06 | Information disclosure | guest data attached to a different user's account | low | accept | Existing-account branch never merges or moves guest rows; the guest stays a separate guest (test (2)/(3) assert it is still `is_guest`). |
| T-fwd-07 | Denial of service | lookup/promotion race | low | accept | If an account with the Google email appears between the lookup and promotion, the kept `UserAlreadyExists -> EMAIL_ALREADY_REGISTERED` fallback redirects with a retryable error; the next attempt takes the existing-account branch. Test (5). |
| T-fwd-SC | Tampering | npm/pip installs | low | accept | No package installs in this task (`axios` is already a frontend dependency). |
</threat_model>

<verification>
- Record `BASE=$(git rev-parse HEAD)` before Task 1. At the end, `git diff --stat $BASE..HEAD` lists only the files in `files_modified` (plus formatter-only changes, if any, committed with a style/chore prefix).
- `grep -n "_existing_google_user\|_complete_google_sign_in" app/routers/auth.py` shows both helpers, the plain callback calling `_complete_google_sign_in`, and the promote callback calling both.
- `grep -n 'token_version=User.token_version + 1' app/services/guest_service.py` shows one line inside `promote_guest_with_password` and one inside `promote_guest_with_google`.
- `grep -rni 'promote_intent' frontend/src` prints nothing.
- Mutation spot-checks (feedback memory: prove gap closures by reverting): temporarily remove the existing-account branch in `google_callback_promote` and confirm tests (2) and (3) fail; temporarily remove one `token_version` bump and confirm (1) or (6) fails; temporarily make googleAuth.ts fall back on every error and confirm the 500/network vitest cases fail. Restore before committing; do not commit the mutations.
- Full pre-merge gate (Task 3 verify) green.
</verification>

<success_criteria>
- A logged-out or retrying guest's Google sign-up goes through authorize-promote and callback-promote, so the guest is promoted in place instead of a duplicate account being created.
- A returning registered user with a stale guest_token signs straight into their existing account through the promote callback; the guest stays untouched; no EMAIL_ALREADY_REGISTERED lockout.
- Promotion revokes the old guest JWT on both paths.
- No intent-flag code or comments remain in the frontend; the Flaws-tab guest CTA works.
- CHANGELOG updated; full pre-merge gate green; browser UAT (a)-(e) handed to the orchestrator.
</success_criteria>

<output>
Create `.planning/quick/261016-fwd-google-sign-in-promotes-saved-guest-inst/261016-fwd-SUMMARY.md` when done, including the pending browser UAT list (a)-(e) and the out-of-scope follow-ups named in the objective.
Before each commit, confirm `git branch --show-current` prints `main` (the GSD commit helper can recreate a phase branch under `branching_strategy: phase`).
</output>

---
quick_id: 261016-fwd
status: complete
date: 2026-10-16
commits: [29aeb84f0, 862a181fc, 6f7081b4e, daabb0e4c]
---

# Quick 261016-fwd: Google sign-in promotes the saved guest instead of creating a duplicate account

## Why
Prod had 20 registrations since 2026-06-23 that followed a same-username guest within 48h instead of promoting it (vs 132 correct promotions); 10 of those guests had imported games that were orphaned. Umami confirmed two mechanisms: a guest logged out and then signed up with Google (the one-shot `promote_intent` flag was cleared by logout), and a guest who backed out of the Google screen and retried (the flag was consumed before the redirect).

## What changed
- **Backend decides** (`app/routers/auth.py`): `/auth/google/callback-promote` now checks whether the Google identity already has an account (linked Google sub, then case-insensitive email). If so, it runs the exact plain-`/callback` sign-in (shared `_complete_google_sign_in` helper) and leaves the guest untouched; otherwise it promotes the guest in place. `EMAIL_ALREADY_REGISTERED` is now only the lookup/promotion race fallback. This removes the 2026-06-23 lockout that the intent flag existed for.
- **Guest JWT revoked at promotion** (`app/services/guest_service.py`): both promotion paths bump `token_version`, so the 365-day guest JWT stops authenticating the registered account.
- **Frontend** (`frontend/src/api/googleAuth.ts`): any saved `guest_token` routes Google sign-in through `authorize-promote`. Falls back to plain sign-in only on 401 or our own 403 "Not a guest user"; network errors, 5xx and foreign 403s are re-thrown (falling back is what orphaned guests). `promote_intent` plumbing removed from `useAuth.ts`/`App.tsx`.
- **Dead CTA fixed**: `NoEngineAnalysisFlawsState` guest "Sign up free" now calls `logoutForPromotion()` and hard-navigates (it used to bounce the still-authenticated guest back to `/`).
- CHANGELOG `[Unreleased] / Fixed`: two bullets.

## Verification
- Backend full suite: 5493 passed, 19 skipped. Frontend full suite: 5645 passed. ruff, ty (app/tests/scripts + analysis), depth gate, eslint, `tsc -b` build, knip all clean.
- Mutation checks: reverting the existing-account branch and the `token_version` bumps fails 4 new backend tests; reverting `googleAuth.ts` fails 3 frontend tests; reverting the CTA fails its new test.
- Browser UAT (Chrome, dev build, real Google OAuth since the profile is signed into Google):
  - Guest 153 → Logout → header "Sign up free" → "Sign up with Google": `authorize-promote` (200) with redirect_uri `/callback-promote`; Google completed; signed into the existing account 28 (Google identity already registered), guest 153 still `is_guest`, no new user row.
  - Guest resumed → `/welcome` "Sign up free" (logoutForPromotion) → register tab; two consecutive `getGoogleAuthorizationUrl()` calls (simulated abandon + retry) both resolved to `/callback-promote`; real Google leg again signed into account 28, guest untouched.
  - Invalid saved guest token → plain `/callback`, token dropped.
  - Not covered in browser: promoting with a NEW Google identity (only one Google account available) and the Flaws-tab CTA (needs a guest with imported but unanalyzed games); both covered by tests.
- Adversarial security review (independent agent): no account takeover or merge into a registered account; audience separation and CSRF run before any lookup/exchange; existing-account branch grants nothing beyond plain `/callback`; token_version bump safe for impersonation and password reset. Its robustness finding (foreign 403 dropped the guest token) was fixed in daabb0e4c.

## Accepted trade-off (owner decision 2026-10-16)
On a shared device, a person who signs up with a new Google account inherits a guest account someone else left there (that person loses access via the token revocation). Email sign-up already behaved this way; owner chose to accept it rather than add a confirmation step.

## Follow-ups (not done, out of scope)
- `oauth_account` lacks `UniqueConstraint(oauth_name, account_id)` (pre-existing; concurrent promotions of one Google sub could duplicate rows and 500 later sign-ins; the `except IntegrityError` branch in `promote_guest_with_google` is effectively dead).
- `client.ts` 401 interceptor `isAuthRoute` check never matches (`config.url` has no `/api` prefix); a revoked guest token now 401s on `/auth/guest/refresh` and can trigger a janky redirect in cross-storage-context cases (e.g. iOS PWA).
- When callback-promote signs into an existing account, the SPA gets no signal that the guest data was not carried over (no `guest_kept` toast).
- callback-promote returns raw JSON 400 when the guest was promoted/deleted within the 10-minute state window.
- `RegisterForm.tsx` email path still drops `guest_token` on any non-409/400 error (same orphaning shape on network/5xx).
- Guests promoted before this change keep a working guest JWT until expiry.
- Stale "30-day" guest JWT docstrings in `guest_service.py` (actual lifetime 365 days).

---
quick_id: 260623-o4f
title: Fix guest-account promotion so Google OAuth never orphans a guest
status: complete
date: 2026-06-23
commit: f51e8fed
---

# Quick Task 260623-o4f — Summary

## What changed

Closed the guest-orphaning gap that produced prod users 198 (guest, 5965 games)
and 199 (registered Google, same 5965 re-imported). A guest who signed in with
Google got a brand-new account instead of an in-place promotion, because the
guest→registered linkage lived only in the frontend's choice of OAuth endpoint
and the backend had no fallback.

Two layers, both landed:

1. **Frontend — single guest-aware path.** New `frontend/src/api/googleAuth.ts`
   `getGoogleAuthorizationUrl()` encapsulates the `guest_token` branch (route to
   `/auth/google/authorize-promote` with the token as a Bearer header; fall back
   to plain authorize; drop a stale token). Both `LoginForm` and `RegisterForm`
   now call it, so the two Google buttons can never drift apart again — the
   divergence (LoginForm had no promote branch) was the proximate cause.

2. **Backend — server-side safety net.** `/auth/google/authorize` gained an
   OPTIONAL authenticated-user dependency (`current_active_user_optional` in
   `app/users.py`). When the caller is an active guest, the endpoint builds a
   promote-audience state JWT with `guest_user_id` and points Google's
   `redirect_uri` at the existing `callback-promote` route, so an authenticated
   guest is promoted in place no matter which entry point started the flow.

## Deviation from the brief

The task text said "have the plain `/auth/google/callback` promote the guest."
Instead, guests are routed through the existing, already-tested `callback-promote`
handler (reused, not duplicated). Same outcome (in-place promotion), no new Google
redirect URI to register, and no second promotion branch to maintain inside the
plain callback. The plain `oauth_callback` path is unchanged for genuine new users.

## Files

- `app/users.py` — added `current_active_user_optional`.
- `app/routers/auth.py` — guest-aware `google_authorize` (promote-audience state +
  `callback-promote` redirect for guests; plain flow otherwise).
- `frontend/src/api/googleAuth.ts` — new shared helper.
- `frontend/src/components/auth/LoginForm.tsx`, `RegisterForm.tsx` — use the helper.
- `tests/test_guest_google_promotion.py` — `TestAuthorizeGuestPromotion`
  (guest → promote routing; anonymous + registered → plain flow).
- `frontend/src/api/__tests__/googleAuth.test.ts` — helper unit tests
  (promote-with-header / plain / stale-token fallback).
- `CHANGELOG.md` — Unreleased › Fixed bullet.

## Verification

- Backend: `ruff format` ✓, `ruff check` ✓, `ty check app/ tests/` zero errors ✓,
  `pytest -n auto` → 2875 passed, 18 skipped ✓.
- Frontend: `tsc -b` ✓, `lint` 0 errors ✓, `knip` clean ✓, `npm test` → 1096 passed ✓.

## Out of scope (not done)

- Cleaning up the existing orphaned prod guest 198 (user 199 already holds all its
  data plus 4814 full evals). Safe to delete via `ON DELETE CASCADE`, but left for
  explicit user approval.
- Removing the now partly-redundant `authorize-promote` endpoint (kept; still used
  by the logged-out-guest path).

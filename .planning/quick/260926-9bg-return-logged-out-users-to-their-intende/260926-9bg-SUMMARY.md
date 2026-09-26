---
quick_id: 260926-9bg
status: complete
commit: 5cee05817
---

# Quick 260926-9bg Summary: Return signed-out visitors to their intended page

Executed inline (small frontend change, no subagents).

## Done
- `lib/returnTo.ts` (new): sessionStorage-backed `stashReturnTo` / `peekReturnTo` / `clearReturnTo` + `sanitizeReturnTo` (same-origin paths only; rejects `//`, `/\`, `/`, `/login`, `/auth/*`; storage errors swallowed).
- `App.tsx` ProtectedLayout: no token → stash `pathname + search` and redirect to `/` (was `/login`); with token → clear the stash in an effect.
- `pages/Home.tsx` HomePage authenticated branch: stashed path wins over the `/library/games` / `/library/import` default. Single read site, since guest start, login, register and the Google callback all land on `/`.
- `api/client.ts` 401 interceptor: stashes the current page before its `/login` redirect (expired session returns to the page), and now only fires when the failed request carried a token.
- CHANGELOG `[Unreleased] → Changed` bullet.

## Deviation from the sketch
- sessionStorage instead of a `?next=` query param: same behavior, no threading through Auth tabs, forms or the Google round-trip.

## Found in browser UAT (fixed, commit 5cee05817)
- `useUserProfile` has no `enabled` guard, so ProtectedLayout fired a tokenless profile request before its redirect; the interceptor treated that 401 as an expired session and hard-redirected to `/login`, defeating the home landing. Interceptor now ignores 401s from requests without an `Authorization` header.

## Verification
- New tests: `lib/__tests__/returnTo.test.ts`, 3 cases in `pages/__tests__/Home.redirect.test.tsx`, `api/__tests__/client.unauthorized.test.ts`. Reverting the Home read and the `sentToken` guard each makes the new tests fail.
- `npm run lint`, `npm test -- --run` (272 files / 4370 tests), `npm run build`, `npm run knip`: clean.
- Browser (dev, 127.0.0.1 origin): stale token on `/train` → `/login` with `/train` stashed; signed-out `/train` → home with guest buttons, stash `/train`; Use as Guest → `/train`, stash cleared.

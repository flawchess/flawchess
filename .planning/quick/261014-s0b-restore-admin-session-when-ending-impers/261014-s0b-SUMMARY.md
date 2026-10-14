---
phase: quick-261014-s0b
plan: 01
subsystem: frontend-auth
tags: [impersonation, auth, admin]
key-files:
  created:
    - frontend/src/components/admin/__tests__/ImpersonationPill.test.tsx
  modified:
    - frontend/src/lib/impersonation.ts
    - frontend/src/hooks/useAuth.ts
    - frontend/src/components/admin/ImpersonationPill.tsx
    - frontend/src/api/client.ts
    - frontend/src/hooks/__tests__/useAuth.test.tsx
    - frontend/src/api/__tests__/client.unauthorized.test.ts
    - CHANGELOG.md
decisions:
  - "Admin JWT stashed in localStorage (admin_return_token) after successful impersonate POST, absent-only; restored by endImpersonation; no backend change (Phase 62 D-03)"
status: complete
commits: 2
plan_head_before: 1402fc3441fd11c3b9c5013bda00e51542a4d983
plan_head_after: e3e3a55427890621c0ab6e10605a9a07c87d198d
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
---

# Quick 261014-s0b: Restore admin session when ending impersonation

The impersonation pill's x now returns the superuser to their own session on /admin instead of signing them out, purely in the frontend.

## What changed

- `lib/impersonation.ts`: exported `ADMIN_RETURN_TOKEN_STORAGE_KEY` (`admin_return_token`).
- `useAuth.ts`: `impersonate()` stashes the current auth_token after the POST succeeds and only if no stash exists. New `endImpersonation()` restores the stash, clears the query cache, and hard-navigates to `/admin`; with no stash it falls back to `logout()`. `logout`, `logoutForPromotion`, `login` and `loginWithToken` remove the stash. `refreshAuthToken` leaves it.
- `ImpersonationPill.tsx`: x calls `endImpersonation`; aria-label and testid unchanged.
- `api/client.ts`: token-bearing 401 also removes the stash.
- Tests: useAuth round-trip and stash hygiene, new ImpersonationPill test, 401 interceptor stash test. CHANGELOG Fixed bullet added.

## Deviations from Plan

The stash removals in logout/logoutForPromotion/login/loginWithToken (planned for Task 2) were made in the same edit pass as Task 1, so they and their useAuth tests landed in the Task 1 commit. Task 2's commit holds the client.ts interceptor change, its test and the CHANGELOG. No behavioral deviation.

## Verification

- Targeted tests (useAuth, ImpersonationPill, client.unauthorized): 3 files, 17 tests passed.
- `npm run lint`: clean. `npm run build`: success. `npm test -- --run`: 330 files, 5605 tests passed. `npm run knip`: exit 0 (two pre-existing configuration hints only).
- `grep -c ADMIN_RETURN_TOKEN_STORAGE_KEY`: useAuth.ts 10, client.ts 2.
- `git diff --name-only main...HEAD -- app/ tests/ alembic/`: empty.

## Out of scope (untouched)

Guest-impersonation token refresh in App.tsx (GUEST-05 effect) left as is.

## Known Stubs

None.

## Self-Check: PASSED

---
phase: 62-admin-user-impersonation
verified: 2026-04-17T20:15:00Z
status: human_needed
score: 23/23
overrides_applied: 0
human_verification:
  - test: "As a superuser, log in, open /admin — verify the Admin tab appears as the rightmost desktop nav entry and in the mobile More drawer. Log in as a non-superuser and confirm no Admin tab appears in either location."
    expected: "Admin tab visible to superuser only; non-superuser sees no Admin tab on desktop or in mobile More drawer."
    why_human: "Frontend conditional rendering based on profile.is_superuser — cannot verify visual display programmatically."
  - test: "As a non-superuser, type /admin directly in the URL bar."
    expected: "Redirected to /openings — SuperuserRoute guard fires."
    why_human: "Client-side routing redirect cannot be verified without a running browser."
  - test: "As a superuser on /admin, open the combobox, type a 1-char query and then a 2-char query, observe results."
    expected: "1-char: hint text only, no API call. 2+ chars: results appear after ~250ms debounce from the live search endpoint."
    why_human: "Debounce timing and network behavior require a running browser."
  - test: "Click a result in the combobox — verify POST /api/admin/impersonate/{id} fires, the impersonation pill appears in both desktop header and mobile header, the Logout button disappears, and the page data reflects the target user."
    expected: "Pill shows 'Impersonating {email} ×'; Logout hidden; Openings data is the target user's data, not the admin's."
    why_human: "Full end-to-end impersonation flow requires a live stack."
  - test: "Click × on the impersonation pill."
    expected: "Session ends, redirected to /login. Verify target user's last_login and last_activity are unchanged via MCP query."
    why_human: "Requires a running app and database access to confirm timestamp invariants."
  - test: "During an impersonation session, open the mobile More drawer."
    expected: "No Logout button and no divider above where Logout would have been."
    why_human: "Mobile drawer rendering requires a browser viewport."
  - test: "Verify the Admin page renders two sections: 'Impersonate user' with the combobox and 'Sentry Error Test' with buttons."
    expected: "Both sections render correctly; no AdminTools or SentryTestButtons visible on the Global Stats page."
    why_human: "Visual layout verification requires a running browser."
---

# Phase 62: Admin User Impersonation Verification Report

**Phase Goal:** Superusers can log in as any user and see stats + perform actions from that user's perspective, with the session ending on logout and without updating last_login/last_activity timestamps. Introduce a new Admin tab that hosts the impersonation selector and the existing Sentry Error Test section (moved out of the global-stats page).

**Verified:** 2026-04-17T20:15:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Superuser can POST /api/admin/impersonate/{id} and receive a 1h impersonation JWT with is_impersonation/act_as/admin_id claims | VERIFIED | `app/routers/admin.py` POST endpoint uses `write_impersonation_token`; `ImpersonationJWTStrategy` sets all claims; `_IMPERSONATION_JWT_LIFETIME_SECONDS = 3600` in `app/users.py`; `test_impersonate_issues_token_with_claims` passes |
| 2 | Impersonation JWT is accepted by `Depends(current_active_user)` and returns the target user to downstream handlers | VERIFIED | `ClaimAwareJWTStrategy.read_token` dispatches to `ImpersonationJWTStrategy` for tokens with `is_impersonation=True`, which returns the target user; `test_impersonation_token_returns_target_user` passes |
| 3 | Regular 7d JWTs continue to work unchanged for non-admin users | VERIFIED | `test_regular_jwt_still_works` passes; `ClaimAwareJWTStrategy` falls through to `super().read_token` for non-impersonation tokens |
| 4 | Non-superuser calling /api/admin/* receives 403 | VERIFIED | `Depends(current_superuser)` on all admin routes; `test_impersonate_rejects_non_superuser` and `test_search_requires_superuser` pass |
| 5 | Impersonating a superuser returns 403 | VERIFIED | Endpoint checks `target.is_superuser` and raises 403; `test_impersonate_rejects_target_superuser` passes |
| 6 | Admin who lost is_superuser=True can no longer use an existing impersonation token | VERIFIED | `ImpersonationJWTStrategy.read_token` re-validates admin on every request; `test_admin_demoted_invalidates_token` passes |
| 7 | Nested impersonation is rejected | VERIFIED | Impersonation token resolves to non-superuser target so `current_superuser` dep 403s; `test_nested_impersonation_rejected` passes |
| 8 | Issuing the impersonation token does NOT update last_login for admin or target | VERIFIED | Token issued via `write_impersonation_token` bypassing `on_after_login`; `test_impersonation_does_not_update_last_login` passes |
| 9 | Superuser can GET /api/admin/users/search?q= and receive ≤20 non-superuser matches for email/username ILIKE or exact numeric id | VERIFIED | `app/services/admin_service.py` implements ILIKE + id match with `USER_SEARCH_LIMIT=20`; 9 search tests pass |
| 10 | Queries shorter than 2 characters return empty list | VERIFIED | `USER_SEARCH_MIN_QUERY_LEN=2` guard in `search_users`; `test_search_short_query_returns_empty` passes |
| 11 | Superusers never appear in search results | VERIFIED | `User.is_superuser == sa_false()` WHERE clause; `test_search_excludes_superusers` passes |
| 12 | LastActivityMiddleware does NOT update last_activity during impersonation | VERIFIED | `_extract_user_id_and_impersonation` returns `is_impersonation` flag; `__call__` short-circuits on `or is_impersonation`; `test_impersonation_skips_target_last_activity` and `test_impersonation_skips_admin_last_activity` pass |
| 13 | Non-impersonation requests still update last_activity | VERIFIED | `test_non_impersonation_still_writes_last_activity` passes |
| 14 | GET /api/users/me/profile returns impersonation context when JWT is impersonation token | VERIFIED | `_get_impersonation_context` dep re-decodes JWT; `UserProfileResponse.impersonation: ImpersonationContext | None = None`; `test_profile_impersonation_populated_when_impersonating` passes |
| 15 | GET /api/users/me/profile returns null impersonation for regular + guest tokens | VERIFIED | `test_profile_impersonation_null_for_regular_token` and `test_profile_impersonation_null_for_guest_token` pass |
| 16 | shadcn Command + Popover components installed and importable | VERIFIED | `frontend/src/components/ui/command.tsx` and `popover.tsx` exist; `cmdk ^1.1.1` in `package.json`; `tsc` clean |
| 17 | useAuth exposes `impersonate(userId)` with correct token-swap ordering | VERIFIED | `const impersonate = useCallback` in `useAuth.ts`; `localStorage.setItem` before `queryClient.clear()` before `setToken`; TypeScript clean |
| 18 | UserProfile type includes impersonation field; admin types file exists | VERIFIED | `impersonation: ImpersonationContext \| null` in `frontend/src/types/users.ts`; `frontend/src/types/admin.ts` exports `UserSearchResult`, `ImpersonateResponse`, `ImpersonationContext` |
| 19 | theme.ts exports IMPERSONATION_PILL_BG/FG/BORDER | VERIFIED | All three tokens present as `oklch()` strings in `frontend/src/lib/theme.ts` |
| 20 | isImpersonating(profile) pure helper is exported and tested | VERIFIED | `export function isImpersonating` in `frontend/src/lib/impersonation.ts`; 4 vitest unit tests pass |
| 21 | Admin tab and route exist, gated on is_superuser; mobile bottom bar unchanged at 4 tabs; SentryTestButtons moved from GlobalStats | VERIFIED | `ADMIN_NAV_ITEM`, `SuperuserRoute`, `path="/admin"` in `App.tsx`; `BOTTOM_NAV_ITEMS` has 4 entries; `SentryTestButtons` extracted to `components/admin/`; no `AdminTools`/`SentryTestButtons` function in `GlobalStats.tsx` |
| 22 | ImpersonationSelector calls search endpoint with shouldFilter=false, debounced 250ms, min 2 chars | VERIFIED | `shouldFilter={false}`, `MIN_QUERY_LEN = 2`, `DEBOUNCE_MS = 250`, `/admin/users/search` call in `ImpersonationSelector.tsx`; clicking row calls `impersonate(userId)` and navigates to `/openings` |
| 23 | ImpersonationPill renders in both headers, × triggers logout; Logout buttons hidden during impersonation | VERIFIED | `ImpersonationPill` imported and rendered in `NavHeader` and `MobileHeader` in `App.tsx`; `!isImpersonating(profile)` guards on `nav-logout` and `drawer-logout`; `IMPERSONATION_PILL_BG/FG/BORDER` used (no hardcoded colors); `data-testid="impersonation-pill"`, `data-testid="btn-impersonation-pill-logout"`, `aria-label="End impersonation session"` present |

**Score:** 23/23 truths verified (automated)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/users.py` | ImpersonationJWTStrategy, ClaimAwareJWTStrategy, get_impersonation_jwt_strategy, current_superuser | VERIFIED | All classes/functions present; `get_strategy=get_claim_aware_jwt_strategy` wired |
| `app/routers/admin.py` | POST /impersonate/{user_id}, GET /users/search | VERIFIED | Both endpoints present; `Depends(current_superuser)` on both |
| `app/schemas/admin.py` | ImpersonateResponse, ImpersonationContext, UserSearchResult | VERIFIED | All three Pydantic v2 models present |
| `app/main.py` | admin_router registered under /api | VERIFIED | `include_router(admin_router, prefix="/api")` at line 79 |
| `app/services/admin_service.py` | search_users with USER_SEARCH_LIMIT=20, USER_SEARCH_MIN_QUERY_LEN=2 | VERIFIED | Constants and function present; real DB query with ILIKE + exclusion |
| `app/middleware/last_activity.py` | _extract_user_id_and_impersonation, or is_impersonation guard | VERIFIED | Extended function and guard present |
| `app/schemas/users.py` | UserProfileResponse.impersonation field | VERIFIED | `impersonation: ImpersonationContext \| None = None` at line 24 |
| `app/routers/users.py` | _get_impersonation_context dep wired | VERIFIED | Dep defined and injected into `get_profile` |
| `tests/test_impersonation.py` | 11 tests including key stubs | VERIFIED | All 11 tests collected and pass |
| `tests/test_admin_users_search.py` | 9 search tests | VERIFIED | All 9 tests collected and pass |
| `tests/test_last_activity_middleware.py` | 3 new impersonation-skip tests | VERIFIED | `TestImpersonationSkip` class with 3 tests, all pass |
| `tests/test_users_profile_impersonation_field.py` | 3 D-22 profile tests | VERIFIED | All 3 tests collected and pass |
| `frontend/src/components/ui/command.tsx` | shadcn Command primitive | VERIFIED | File exists; `CommandInput` present |
| `frontend/src/components/ui/popover.tsx` | shadcn Popover primitive | VERIFIED | File exists; `PopoverContent` present |
| `frontend/src/lib/theme.ts` | IMPERSONATION_PILL_* tokens | VERIFIED | All 3 oklch() tokens present |
| `frontend/src/hooks/useAuth.ts` | impersonate(userId) method | VERIFIED | `const impersonate = useCallback`, correct token-swap ordering |
| `frontend/src/types/users.ts` | UserProfile.impersonation field | VERIFIED | `impersonation: ImpersonationContext \| null` present |
| `frontend/src/types/admin.ts` | UserSearchResult, ImpersonateResponse, ImpersonationContext | VERIFIED | All three interfaces exported |
| `frontend/src/lib/impersonation.ts` | isImpersonating helper | VERIFIED | `export function isImpersonating` present |
| `frontend/src/lib/impersonation.test.ts` | 4 vitest tests | VERIFIED | All 4 pass |
| `frontend/src/components/admin/SentryTestButtons.tsx` | Extracted from GlobalStats | VERIFIED | File exists; `export function SentryTestButtons`; `btn-sentry-test-event` and `btn-sentry-test-backend` test IDs present |
| `frontend/src/components/admin/ImpersonationSelector.tsx` | Combobox with shouldFilter=false | VERIFIED | File exists; `shouldFilter={false}`, `MIN_QUERY_LEN = 2`, `DEBOUNCE_MS = 250`, navigates to /openings on select |
| `frontend/src/pages/Admin.tsx` | Admin page composing selector + SentryTestButtons | VERIFIED | `export function AdminPage`; both components composed; `data-testid="admin-page"` |
| `frontend/src/pages/GlobalStats.tsx` | AdminTools + SentryTestButtons REMOVED | VERIFIED | Neither `function SentryTestButtons` nor `function AdminTools` present in file |
| `frontend/src/components/admin/ImpersonationPill.tsx` | Pill with theme tokens + ARIA | VERIFIED | Uses IMPERSONATION_PILL_BG/FG/BORDER; `data-testid="impersonation-pill"`, `data-testid="btn-impersonation-pill-logout"`, `aria-label="End impersonation session"` |
| `frontend/src/App.tsx` | Admin route, SuperuserRoute, pill in headers, logout hidden | VERIFIED | All elements present; `ImpersonationPill` rendered in NavHeader and MobileHeader; `!isImpersonating(profile)` on both logout buttons; BOTTOM_NAV_ITEMS unchanged (4 items) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/admin.py` | `app/users.py::current_superuser` | `Depends(current_superuser)` | WIRED | Both POST /impersonate and GET /users/search use the dep |
| `app/users.py::ClaimAwareJWTStrategy.read_token` | `ImpersonationJWTStrategy.read_token` | claim-based dispatch on `is_impersonation` | WIRED | `_peek_is_impersonation` routes to `self._impersonation.read_token` |
| `app/main.py` | `app/routers/admin.py` | `app.include_router` | WIRED | Line 79: `app.include_router(admin_router, prefix="/api")` |
| `app/routers/admin.py::search_users` | `app/services/admin_service.py::search_users` | service call | WIRED | `await admin_service.search_users(session, q)` |
| `app/middleware/last_activity.py::__call__` | JWT is_impersonation claim | short-circuit | WIRED | `or is_impersonation` in guard at line 78 |
| `app/routers/users.py::get_profile` | `ImpersonationContext` | `_get_impersonation_context` dep | WIRED | Dep injected as parameter; `impersonation=impersonation` in response |
| `frontend/src/hooks/useAuth.ts::impersonate` | `POST /api/admin/impersonate/{userId}` | `apiClient.post` | WIRED | `/admin/impersonate/${userId}` call present |
| `frontend/src/types/users.ts::UserProfile` | `frontend/src/types/admin.ts::ImpersonationContext` | type import | WIRED | `import type { ImpersonationContext } from '@/types/admin'` |
| `frontend/src/pages/Admin.tsx` | `ImpersonationSelector` | component import | WIRED | Import and render of `<ImpersonationSelector />` |
| `frontend/src/components/admin/ImpersonationSelector.tsx` | `useAuth.impersonate` | hook call | WIRED | `const { impersonate } = useAuth()` then `await impersonate(userId)` |
| `frontend/src/App.tsx::NavHeader` | `ImpersonationPill` | component render | WIRED | `{profile?.impersonation && <ImpersonationPill ...>}` at line 145 |
| `frontend/src/App.tsx::MobileHeader` | `ImpersonationPill` | component render | WIRED | `<ImpersonationPill ... emailMaxWidthClass="max-w-[8rem]">` at line 182 |
| `frontend/src/components/admin/ImpersonationPill.tsx::×` | `useAuth().logout` | hook call | WIRED | `const { logout } = useAuth()` then `onClick={logout}` |
| `frontend/src/App.tsx` | `/admin route` | react-router Route | WIRED | `<Route path="/admin" element={<SuperuserRoute>...}` at line 456 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ImpersonationSelector.tsx` | `data` (UserSearchResult[]) | `GET /api/admin/users/search` → `admin_service.search_users` → SQLAlchemy ILIKE query | Yes — real DB query via `result.scalars().unique().all()` | FLOWING |
| `ImpersonationPill.tsx` | `impersonation` prop | `UserProfile.impersonation` from `/users/me/profile` → `_get_impersonation_context` dep re-decodes JWT | Yes — DB lookup via `session.get(User, int(act_as))` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend impersonation tests (32 tests) | `uv run pytest tests/test_impersonation.py tests/test_admin_users_search.py tests/test_users_profile_impersonation_field.py tests/test_last_activity_middleware.py` | 32 passed in 5.87s | PASS |
| Frontend unit tests (77 tests, incl. 4 isImpersonating) | `cd frontend && npm test -- --run` | 77 passed | PASS |
| Backend type check | `uv run ty check app/ tests/` | All checks passed | PASS |
| Backend lint | `uv run ruff check app/ tests/` | All checks passed | PASS |
| Frontend TypeScript | `cd frontend && npx tsc -b --noEmit` | 0 errors | PASS |
| Frontend lint | `cd frontend && npm run lint` | 0 errors (3 pre-existing coverage/ warnings) | PASS |
| Frontend knip | `cd frontend && npm run knip` | Clean (0 issues) | PASS |

### Requirements Coverage

Requirements D-01..D-23 from `62-CONTEXT.md` — no separate REQUIREMENTS.md file maps these to plan IDs; coverage drawn from PLAN frontmatter `requirements:` fields:

| Requirement | Source Plan | Description | Status |
|-------------|------------|-------------|--------|
| D-01 | 62-01 | Impersonation JWT claims (sub, act_as, admin_id, is_impersonation) | SATISFIED |
| D-02 | 62-01 | Per-request admin re-validation | SATISFIED |
| D-03 | 62-01 | Impersonation token TTL = 1 hour | SATISFIED |
| D-04 | 62-01 | Nested impersonation rejected | SATISFIED |
| D-05 | 62-01 | Cannot impersonate a superuser | SATISFIED |
| D-06 | 62-01 | on_after_login not called for impersonation | SATISFIED |
| D-07 | 62-02 | last_activity not updated during impersonation | SATISFIED |
| D-08 | 62-02 | admin last_activity not updated during impersonation (defensive) | SATISFIED |
| D-09 | 62-03 | Single-token model, impersonate() swaps token | SATISFIED |
| D-10 | 62-05 | × on pill triggers logout | SATISFIED |
| D-11 | 62-05 | No "stop impersonating" return flow (absence requirement) | SATISFIED — no such feature exists |
| D-12 | 62-02, 62-03, 62-04 | Min 2-char search query | SATISFIED (backend + frontend) |
| D-13 | 62-02, 62-03, 62-04 | Search endpoint capped at 20, superuser-only | SATISFIED |
| D-14 | 62-04 | Result row shows email + platforms + is_guest + last_login; clicking triggers impersonation + navigate | SATISFIED |
| D-15 | N/A | No recently-impersonated list (absence requirement, deferred) | SATISFIED — not present |
| D-16 | 62-04 | Admin tab rightmost in desktop nav, superuser-only | SATISFIED (pending human visual verification) |
| D-17 | 62-04 | Mobile bottom bar stays 4 tabs; Admin in More drawer | SATISFIED — BOTTOM_NAV_ITEMS confirmed 4 items |
| D-18 | 62-04 | /admin route protected by SuperuserRoute | SATISFIED — SuperuserRoute guard present |
| D-19 | 62-04 | Admin page has impersonation + Sentry sections; GlobalStats scrubbed | SATISFIED |
| D-20 | 62-05 | Impersonation pill in header; × is sole logout; standalone Logout hidden | SATISFIED (pending human visual verification) |
| D-21 | 62-05 | No banner, no sticky-layout displacement, no tab title change | SATISFIED — only the pill is added |
| D-22 | 62-02, 62-03, 62-05 | Profile response includes impersonation context; pill derived from it | SATISFIED |
| D-23 | 62-01 | Full user action surface during impersonation (no carveouts) | SATISFIED — ClaimAwareJWTStrategy returns target to all existing endpoints |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `frontend/src/hooks/useAuth.ts` + `ImpersonationSelector.tsx` | `impersonate()` error not caught or Sentry-captured (WR-01 from code review) | Warning | CLAUDE.md requires `Sentry.captureException` for manual axios calls that fail; unhandled rejection also means no user-facing error message when impersonation fails |
| `app/users.py::_peek_is_impersonation` | `except Exception: return False` is too broad (WR-02 from code review) | Info | Not exploitable (signature verification still gates acceptance); maintenance risk only — narrow exception types or add test |

### Human Verification Required

**These items require a running dev stack (backend + frontend) to verify.**

### 1. Admin Tab Visibility (D-16, D-17)

**Test:** Log in as a superuser — confirm Admin tab appears as rightmost entry in desktop top nav. Switch to a 375px viewport, open the More drawer — confirm Admin is listed. Log in as a non-superuser — confirm no Admin tab on desktop or in the More drawer.
**Expected:** Tab conditionally shown/hidden based on `profile.is_superuser`.
**Why human:** Frontend conditional rendering cannot be verified without a running browser.

### 2. Non-superuser Direct URL Access (D-18)

**Test:** While logged in as a non-superuser, navigate to `/admin` directly.
**Expected:** Redirected to `/openings`.
**Why human:** Client-side routing requires a running browser.

### 3. Search Debounce and Min-Char Behavior (D-12)

**Test:** Open the combobox on /admin, type a single character — observe no results fetched. Type a second character — observe search fires after ~250ms with results.
**Expected:** 1-char input shows hint only; 2-char input triggers API call after debounce.
**Why human:** Debounce timing and network calls require a running app.

### 4. Full Impersonation Flow (D-01..D-10, D-14, D-20, D-22)

**Test:** As a superuser on /admin, search for a non-superuser, click their row. Confirm:
- POST /api/admin/impersonate/{id} fires
- Orange pill `Impersonating {email} ×` appears in desktop header
- Same pill appears in mobile header
- Desktop Logout button is gone
- Mobile drawer Logout and its divider are absent
- Openings data reflects the target user (not the admin)

**Expected:** End-to-end impersonation session starts; all visual indicators correct.
**Why human:** Full flow requires a live stack; visual layout requires a browser.

### 5. Impersonation Session End (D-10) and Timestamp Invariants (D-06, D-07)

**Test:** Click × on the pill. Confirm redirected to /login, token cleared. After re-logging in as the target user or querying the DB directly, confirm `last_login` and `last_activity` on the target user are unchanged from before the impersonation session.
**Expected:** Session ends cleanly; no timestamp pollution.
**Why human:** Timestamp verification requires DB access; redirect behavior requires a browser.

### 6. Admin Page Layout (D-19)

**Test:** Navigate to /admin as a superuser. Confirm two sections: "Impersonate user" (combobox at top) and "Sentry Error Test" (buttons at bottom). Navigate to /global-stats — confirm no AdminTools or Sentry section.
**Expected:** Clean section separation; GlobalStats page simplified.
**Why human:** Visual layout requires a browser.

---

## Gaps Summary

No automated gaps. All 23 observable truths verified in code. All 32 backend tests and 77 frontend tests pass. TypeScript, ruff, knip, and ty all clean.

Two code review warnings (WR-01: Sentry not captured on impersonation API failure; WR-02: overly broad exception handler in `_peek_is_impersonation`) are notable but do not prevent the phase goal from being achieved. They are tracked in `62-REVIEW.md` and could be addressed as a follow-up.

Status is `human_needed` because full end-to-end browser verification (admin tab visibility, impersonation flow, pill rendering, mobile parity, timestamp invariants) cannot be verified programmatically without a running stack.

---

_Verified: 2026-04-17T20:15:00Z_
_Verifier: Claude (gsd-verifier)_

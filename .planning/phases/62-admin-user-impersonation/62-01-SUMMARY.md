---
phase: 62-admin-user-impersonation
plan: 01
subsystem: auth
tags: [auth, fastapi-users, jwt, security, impersonation, pydantic-v2]

requires:
  - phase: 44-guest-access
    provides: fastapi-users JWT strategy + manual write_token pattern (get_guest_jwt_strategy) reused for impersonation
provides:
  - ImpersonationJWTStrategy with act_as/admin_id/is_impersonation claims and 1h TTL
  - ClaimAwareJWTStrategy routing impersonation tokens transparently to downstream current_active_user
  - current_superuser dep for /admin/* gating
  - POST /api/admin/impersonate/{user_id} endpoint returning ImpersonateResponse
  - Pydantic schemas (ImpersonateResponse, ImpersonationContext, UserSearchResult) for later plans in the phase
affects: [62-02-admin-search, 62-03-profile-impersonation-context, 62-04-frontend-admin-page, 62-05-frontend-pill]

tech-stack:
  added: []
  patterns:
    - "Claim-aware JWTStrategy wrapper: single auth_backend dispatches per-token to impersonation vs default strategy based on unverified payload peek (signature check still happens inside the chosen strategy's read_token)"
    - "Per-request re-validation of admin superuser + target non-superuser in ImpersonationJWTStrategy.read_token — no server-side token revocation needed"
    - "Manual strategy.write_impersonation_token bypasses UserManager.on_after_login, satisfying D-06 by construction"

key-files:
  created:
    - app/schemas/admin.py
    - app/routers/admin.py
    - tests/test_impersonation.py
  modified:
    - app/users.py
    - app/main.py

key-decisions:
  - "Single auth_backend + ClaimAwareJWTStrategy wrapper — keeps every Depends(current_active_user) call site unchanged (returns target for impersonation tokens)"
  - "D-04 (nested impersonation) enforced indirectly via current_superuser dep — impersonation token resolves to non-superuser target, so the dep 403s without any raw-token inspection in the endpoint"
  - "Endpoint response includes target_id (in addition to target_email) to remove round-trip guessing in the frontend flow"

patterns-established:
  - "Admin/superuser-only routes use Depends(current_superuser) instead of inline is_superuser checks"
  - "Expected 403/404 from current_superuser or target lookups are NOT wrapped in sentry_sdk.capture_exception per CLAUDE.md rules"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-23]

duration: 32min
completed: 2026-04-17
---

# Phase 62 Plan 01: Admin Impersonation Backend Core Summary

**1h impersonation JWT with act_as/admin_id/is_impersonation claims, a ClaimAwareJWTStrategy wrapper that keeps every Depends(current_active_user) call site unchanged, and POST /api/admin/impersonate/{user_id} superuser-gated endpoint — all 11 integration + unit tests green.**

## Performance

- **Duration:** ~32 min
- **Started:** 2026-04-17T17:10Z
- **Completed:** 2026-04-17T17:42Z
- **Tasks:** 3
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- ImpersonationJWTStrategy issuing 1h tokens with sub/act_as/admin_id/is_impersonation claims (D-01, D-03)
- Per-request re-validation: admin must still be active + is_superuser=True, target must still be active + is_superuser=False (D-02, D-05)
- ClaimAwareJWTStrategy wrapper wired into auth_backend.get_strategy — transparently returns the impersonated target for impersonation tokens so no downstream endpoint needs modification (D-23)
- POST /api/admin/impersonate/{user_id} endpoint — superuser-only via current_superuser dep, 404 for missing/inactive, 403 for target-superuser, 1h JWT on success
- D-04 (nested impersonation rejected) enforced indirectly — impersonation tokens resolve to a non-superuser target, so the current_superuser dep 403s without extra raw-token inspection
- D-06 satisfied by construction — strategy.write_impersonation_token bypasses UserManager.on_after_login so neither admin.last_login nor target.last_login is touched
- 11 new tests in tests/test_impersonation.py cover the full threat model (token claims, TTL, non-superuser rejection, target-superuser rejection, missing/inactive 404, downstream target resolution, nested rejection, admin-demoted invalidation, target-promoted invalidation, regular-JWT regression guard, last_login freeze invariant)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Wave 0 test scaffold — tests/test_impersonation.py with failing stubs** — `0c89dae` (test)
2. **Task 2: Implement ImpersonationJWTStrategy + ClaimAwareJWTStrategy + current_superuser in app/users.py** — `e414ca7` (feat)
3. **Task 3: Create app/schemas/admin.py + app/routers/admin.py + register in app/main.py** — `d8565cd` (feat)

## Files Created/Modified

- `tests/test_impersonation.py` (created) — 11 async integration tests covering D-01..D-06 and D-23
- `app/users.py` (modified) — added ImpersonationJWTStrategy, _peek_is_impersonation, ClaimAwareJWTStrategy, get_impersonation_jwt_strategy, get_claim_aware_jwt_strategy, current_superuser; rewired auth_backend to use get_claim_aware_jwt_strategy (get_jwt_strategy kept for backward compat)
- `app/schemas/admin.py` (created) — ImpersonateResponse, ImpersonationContext, UserSearchResult Pydantic v2 schemas
- `app/routers/admin.py` (created) — APIRouter(prefix="/admin", tags=["admin"]) + POST /impersonate/{user_id}
- `app/main.py` (modified) — imported admin_router and called app.include_router(admin_router, prefix="/api")

## Decisions Made

- Chose the single-backend ClaimAwareJWTStrategy wrapper over two separate AuthenticationBackends (RESEARCH §"Dispatching: one backend, claim-aware strategy"). Rationale: keeps the fastapi_users instance config unchanged, every existing Depends(current_active_user) returns the right user transparently, no ripple through call sites.
- D-04 enforcement is implicit via current_superuser dep rather than explicit raw-token inspection in the endpoint. Rationale: the claim-aware strategy guarantees impersonation tokens resolve to the non-superuser target, so the dep's own superuser check is sufficient. Removes a duplicate validation path and possible drift between endpoint and strategy.
- target_id added to ImpersonateResponse in addition to target_email. Rationale: frontend flows (Plan 04/05) will want to reference the numeric id for cache invalidation and URL construction without re-deriving it from email.

## Deviations from Plan

None — plan executed exactly as written. Minor note: the Task 2 `<action>` block in the plan suggested `# ty: ignore[unresolved-attribute]` suppressions on `user_manager.user_db.get(...)` calls inside `ImpersonationJWTStrategy.read_token`. `ty` did not raise on those calls in practice, and adding the suppressions triggered `unused-ignore-comment` warnings. The suppressions were therefore omitted (mirrors CLAUDE.md: only add suppressions when `ty` actually complains). Not classified as a deviation — it is an explicit ty-compliance instruction within the plan.

## Issues Encountered

None. All 795 existing backend tests remained green throughout; no regression introduced by the new claim-aware strategy.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Plan 02 (admin user search) can consume `current_superuser` from `app/users.py` and `UserSearchResult` from `app/schemas/admin.py` unchanged. Plan 03 (profile impersonation context) can read the `is_impersonation` + `admin_id` claims from an Authorization header using the same `decode_jwt`/`_JWT_AUDIENCE` contract exercised in `tests/test_impersonation.py`. No blockers.

## Self-Check: PASSED

Verified files exist:
- tests/test_impersonation.py — FOUND
- app/schemas/admin.py — FOUND
- app/routers/admin.py — FOUND
- app/users.py — FOUND (modified)
- app/main.py — FOUND (modified)

Verified commits exist (via `git log --oneline -5`):
- 0c89dae — FOUND (test(62-01): add failing tests for admin impersonation)
- e414ca7 — FOUND (feat(62-01): add impersonation + claim-aware JWT strategies)
- d8565cd — FOUND (feat(62-01): add admin router + impersonate endpoint)

Verified gates:
- `uv run pytest tests/test_impersonation.py -x` — 11 passed
- `uv run pytest` — 795 passed (no regression)
- `uv run ty check app/ tests/` — all checks passed
- `uv run ruff check .` — all checks passed

---
*Phase: 62-admin-user-impersonation*
*Plan: 01*
*Completed: 2026-04-17*

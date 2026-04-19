---
phase: 62-admin-user-impersonation
plan: 02
subsystem: auth
tags: [auth, search, middleware, profile, security, sqlalchemy, pydantic-v2]

requires:
  - phase: 62-admin-user-impersonation
    plan: 01
    provides: "current_superuser dep, ImpersonationContext + UserSearchResult schemas, impersonation JWT issuance via POST /admin/impersonate/{id}"
provides:
  - "GET /api/admin/users/search — superuser-gated user lookup (≤20 non-superuser rows, ILIKE on email/chess_com/lichess, exact numeric id match)"
  - "admin_service.search_users — service function with USER_SEARCH_LIMIT=20 + USER_SEARCH_MIN_QUERY_LEN=2 constants"
  - "LastActivityMiddleware skip on is_impersonation tokens — target + admin last_activity untouched during impersonation"
  - "_extract_user_id_and_impersonation helper returning (user_id, is_impersonation)"
  - "UserProfileResponse.impersonation: ImpersonationContext | None — surfaces impersonation context on /users/me/profile (D-22)"
  - "_get_impersonation_context FastAPI dep — re-decodes raw JWT (Option A, RESEARCH.md Open Q #1)"
affects: [62-03-frontend-admin-page, 62-04-frontend-pill]

tech-stack:
  added: []
  patterns:
    - "ILIKE user search with conditional id-match clause — avoids Python False literal inside or_ (RESEARCH.md Open Q #4 resolution)"
    - "Superuser exclusion via User.is_superuser == sa.false() — hygiene so a compromised admin session cannot enumerate the admin roster via search"
    - "Middleware short-circuit on impersonation — extended _extract_user_id to return the impersonation flag, added to the existing status/user_id guard"
    - "Profile impersonation context via FastAPI dep that re-decodes the raw Authorization header — zero coupling to auth strategy"
    - "ty suppression: unresolved-attribute on first .ilike() call + invalid-argument-type on User.is_superuser == sa_false() — added only where ty actually complains (per CLAUDE.md)"

key-files:
  created:
    - app/services/admin_service.py
    - tests/test_admin_users_search.py
    - tests/test_users_profile_impersonation_field.py
  modified:
    - app/routers/admin.py
    - app/middleware/last_activity.py
    - app/schemas/users.py
    - app/routers/users.py
    - tests/test_last_activity_middleware.py

key-decisions:
  - "Middleware helper renamed to _extract_user_id_and_impersonation; kept _extract_user_id as a thin wrapper so TestExtractUserId (and any downstream imports) continue to work unchanged"
  - "Search endpoint excludes superusers in the SQL WHERE clause, not post-filter — keeps result-count accurate with the 20-row LIMIT"
  - "Impersonation context on profile uses Option A (FastAPI dep re-decoding raw JWT) over Option B (threading through strategy.read_token). Simpler and decouples schema from auth strategy"
  - "PUT /me/profile response explicitly sets impersonation=None (out of scope for the impersonation flow) — keeps schema consistent for any caller that re-renders from the PUT response"

patterns-established:
  - "Admin service layer with explicit limit + min-query-length constants (no magic numbers per CLAUDE.md)"
  - "Conditional or_ clause building: list[Any] + append for numeric-only id match, avoids Python False → ColumnElement mixing"
  - "Middleware test pattern for impersonation: _last_updated.pop() to bypass throttle cache between sub-cases"

requirements-completed: [D-07, D-08, D-12, D-13, D-22]

duration: 24min
completed: 2026-04-17
---

# Phase 62 Plan 02: Admin Search + Middleware Skip + Profile Field Summary

**Superuser-gated user search (ILIKE + numeric id, 20-row cap, superusers excluded), LastActivityMiddleware short-circuit on is_impersonation tokens, and a new `impersonation: {admin_id, target_email} | null` field on /users/me/profile — 21 new tests green plus no regressions across 810 backend tests.**

## Performance

- **Duration:** ~24 min
- **Started:** 2026-04-17T (worktree base d7e2b93)
- **Tasks:** 4
- **Files modified:** 8 (3 created, 5 modified)
- **Tests added:** 15 new (9 search + 3 middleware skip + 3 profile field)

## Accomplishments

- GET /api/admin/users/search returns ≤20 non-superuser matches for email / chess_com_username / lichess_username ILIKE, plus exact match on numeric id (D-12, D-13)
- Queries shorter than 2 characters return an empty list (D-12)
- Superusers are excluded from search results — hygiene for D-05 (they cannot be impersonated) and reduces blast radius if an admin session is compromised
- LastActivityMiddleware does NOT update `last_activity` on either the target or the admin row when the request's JWT has `is_impersonation=true` (D-07, D-08 defensive)
- Non-impersonation requests still update `last_activity` correctly (regression guard in `test_non_impersonation_still_writes_last_activity`)
- GET /api/users/me/profile returns `impersonation: { admin_id, target_email }` when the request's JWT has is_impersonation=true; null for regular + guest tokens (D-22)
- All 21 new tests green; 810-test backend suite passes (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Wave 0 failing tests** — `5fcd313` (test)
2. **Task 2 (GREEN): admin_service.search_users + GET /admin/users/search** — `feb7860` (feat)
3. **Task 3 (GREEN): LastActivityMiddleware impersonation skip (D-07)** — `bfcf61f` (feat)
4. **Task 4 (GREEN): /users/me/profile.impersonation field (D-22)** — `1abb700` (feat)

## Files Created/Modified

Created:
- `app/services/admin_service.py` — `search_users(session, query)` with `USER_SEARCH_LIMIT=20` + `USER_SEARCH_MIN_QUERY_LEN=2` constants. Conditional `or_` clause list, `User.is_superuser == sa_false()` exclusion, ordered by `last_login desc nullslast, id asc`.
- `tests/test_admin_users_search.py` — 9 integration tests covering superuser guard, min-length, ILIKE match across three fields, numeric id match, superuser exclusion, 20-row limit, response shape.
- `tests/test_users_profile_impersonation_field.py` — 3 integration tests covering D-22 (populated when impersonating, null for regular, null for guest).

Modified:
- `app/routers/admin.py` — added `GET /users/search` endpoint wired to `admin_service.search_users`, uses `current_superuser` dep.
- `app/middleware/last_activity.py` — added `_extract_user_id_and_impersonation() -> tuple[int | None, bool]`, kept `_extract_user_id` as a thin wrapper for existing tests. `__call__` short-circuits on `is_impersonation`.
- `app/schemas/users.py` — added `impersonation: ImpersonationContext | None = None` to `UserProfileResponse` (imports from `app.schemas.admin`, no circular).
- `app/routers/users.py` — added `_get_impersonation_context` FastAPI dep that re-decodes the Authorization header; wired into `get_profile`; `update_profile` returns `impersonation=None` explicitly.
- `tests/test_last_activity_middleware.py` — added `TestImpersonationSkip` class with 3 tests (target-skip, admin-skip, non-impersonation-regression).

## Decisions Made

- **Kept `_extract_user_id` as a thin wrapper over `_extract_user_id_and_impersonation`.** Rationale: the existing `TestExtractUserId::test_valid_token_returns_user_id` and `test_invalid_token_returns_none` + `test_missing_auth_header_returns_none` import and call `_extract_user_id` directly. Preserving the old symbol keeps those tests green with no edits and signals that renaming is not required for the D-07 fix.
- **Excluded superusers in SQL, not post-filter.** Putting the `is_superuser == false()` condition in the WHERE clause keeps the 20-row LIMIT accurate. Post-filtering would potentially return <20 rows even when 20+ non-superuser matches exist.
- **Option A (FastAPI dep re-decodes JWT) over Option B (strategy.read_token sets request.state).** The dep is 15 lines, has no coupling to `ClaimAwareJWTStrategy`, and the double-decode cost is trivial next to the DB round-trips already in `/me/profile`. Option B would couple the schema package to auth internals.
- **Explicit `impersonation=None` on PUT /me/profile response.** Keeps the response schema identical to GET for any client that re-renders from the mutation result, and signals (via the explicit None) that the settings-update path is deliberately out of scope for impersonation state.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected ty suppression rule names**
- **Found during:** Task 2 (verify gate — `uv run ty check`)
- **Issue:** The plan's `<action>` block suggested `# ty: ignore[invalid-argument-type]` on `.ilike()` calls and on the numeric id-match branch. In practice, ty raised:
  - `unresolved-attribute` on the first `.ilike()` (only — ty somehow resolves the other two columns despite identical typing)
  - `invalid-argument-type` on `User.is_superuser == sa_false()` passed as an argument to `.where()` (not on `User.id == int(q)` or the other `.ilike` calls)
- **Fix:** Used the rule names ty actually raises, removed unused suppressions (which themselves trigger `unused-ignore-comment` warnings). Mirrors Plan 01's deviation note — CLAUDE.md says "always include the rule name" and avoiding noise requires adding them only where ty actually flags.
- **Files modified:** `app/services/admin_service.py`
- **Commit:** feb7860

No other deviations. Plan executed exactly as written otherwise.

## Issues Encountered

None blocking. Minor iteration on ty suppression rule names (above).

Two pre-existing project conventions worth noting (not deviations, not actions taken):
- `uv run ruff format --check .` reports 85 pre-existing files unformatted, including 5 Plan-02 files that followed the same style. CI runs only `uv run ruff check .` (which passes). Leaving the new files consistent with the existing style — no format sweep.
- The `.planning/phases/62-admin-user-impersonation/.gitkeep` untracked marker is left alone (belongs to a sibling wave and is not part of this plan).

## User Setup Required

None. No migrations, no env vars, no service configuration.

## Next Phase Readiness

Plan 03 (frontend admin page) can consume:
- `GET /api/admin/users/search?q=...` — superuser-only, ≤20 non-superuser rows
- `GET /api/users/me/profile` returns `impersonation: {admin_id, target_email} | null`
- The backend will not pollute `last_activity` during impersonation — frontend does not need to be aware

No blockers. Wave 2 backend surface complete.

## Threat Flags

None. All new surface was already enumerated in the plan's `<threat_model>` (T-62-05 through T-62-10). Implementation honored every mitigation:
- T-62-05 (E): `current_superuser` dep on GET /admin/users/search (test_search_requires_superuser)
- T-62-06 (I): superuser-gated + ≤20 rows + superuser exclusion (test_search_excludes_superusers)
- T-62-07: no try/except around current_superuser; FastAPI default handler returns 403 without Sentry
- T-62-09 (I): middleware short-circuits on is_impersonation (test_impersonation_skips_target_last_activity + test_impersonation_skips_admin_last_activity)
- T-62-10 (T): SQLAlchemy `.ilike()` parameterizes `q`; never interpolated

## Self-Check: PASSED

Verified files exist (via `ls`):
- `app/services/admin_service.py` — FOUND
- `app/routers/admin.py` — FOUND (modified, has `router.get("/users/search"`)
- `app/middleware/last_activity.py` — FOUND (modified, has `_extract_user_id_and_impersonation`)
- `app/schemas/users.py` — FOUND (modified, has `impersonation: ImpersonationContext | None`)
- `app/routers/users.py` — FOUND (modified, has `_get_impersonation_context` + `impersonation=impersonation`)
- `tests/test_admin_users_search.py` — FOUND
- `tests/test_users_profile_impersonation_field.py` — FOUND
- `tests/test_last_activity_middleware.py` — FOUND (modified, has `TestImpersonationSkip`)

Verified commits exist (via `git log --oneline -6`):
- 5fcd313 — FOUND (test(62-02): add failing tests for admin search + middleware skip + profile field)
- feb7860 — FOUND (feat(62-02): add admin_service.search_users + GET /admin/users/search)
- bfcf61f — FOUND (feat(62-02): skip last_activity writes on impersonation tokens (D-07))
- 1abb700 — FOUND (feat(62-02): add impersonation context to /users/me/profile (D-22))

Verified gates:
- `uv run pytest tests/test_admin_users_search.py tests/test_last_activity_middleware.py tests/test_users_profile_impersonation_field.py` — 21 passed
- `uv run pytest -x` — 810 passed (full backend suite, no regression)
- `uv run ty check app/ tests/` — All checks passed
- `uv run ruff check .` — All checks passed

---
*Phase: 62-admin-user-impersonation*
*Plan: 02*
*Completed: 2026-04-17*

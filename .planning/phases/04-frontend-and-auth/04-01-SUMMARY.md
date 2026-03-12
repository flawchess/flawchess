---
phase: 04-frontend-and-auth
plan: 01
subsystem: auth
tags: [fastapi-users, jwt, bearer-token, sqlalchemy, alembic, cors, postgresql]

# Dependency graph
requires:
  - phase: 03-analysis-api
    provides: Analysis and import routers with hardcoded user_id=1 placeholders

provides:
  - FastAPI-Users JWT authentication with integer user IDs
  - User registration (POST /auth/register) and login (POST /auth/jwt/login)
  - Protected analysis and import endpoints via Depends(current_active_user)
  - Users table in PostgreSQL via Alembic migration
  - CORS middleware for localhost:5173
affects:
  - 04-02 (frontend auth flows will use these endpoints)
  - 04-03 (any further backend features using current_active_user)

# Tech tracking
tech-stack:
  added:
    - fastapi-users 15.0.4 (SQLAlchemy + OAuth extras)
    - httpx-oauth 0.16.1
    - bcrypt (transitive — password hashing)
    - pyjwt (transitive — JWT signing)
  patterns:
    - "FastAPI-Users IntegerIDMixin on UserManager (not on the model)"
    - "current_active_user = fastapi_users.current_user(active=True) as Depends()"
    - "user_id extracted before asyncio.create_task in imports router (request scope boundary)"
    - "asyncio_default_test_loop_scope = session to prevent cross-test event loop errors"

key-files:
  created:
    - app/models/user.py
    - app/users.py
    - app/routers/auth.py
    - alembic/versions/ea8ca9526dcf_add_users_table.py
    - tests/test_auth.py
  modified:
    - app/core/config.py
    - app/main.py
    - app/routers/analysis.py
    - app/routers/imports.py
    - alembic/env.py
    - tests/test_imports_router.py
    - pyproject.toml

key-decisions:
  - "FastAPI-Users 15.x register router uses get_register_router(user_schema, user_create_schema) — BaseUser[int] and BaseUserCreate from fastapi_users.schemas"
  - "asyncio_default_test_loop_scope=session required — app-level connection pool ties to first event loop, per-function loops cause asyncpg RuntimeError"
  - "Auth integration tests use unique emails per run (uuid4 suffix) — users table persists across test runs, no rollback fixture"
  - "user_id extracted before asyncio.create_task in imports router — Depends(current_active_user) only valid within request scope"
  - "Google OAuth gated behind GOOGLE_OAUTH_CLIENT_ID env var — not wired in auth router (requires httpx-oauth client setup; deferred)"
  - "JWT lifetime 604800 seconds (7 days) — simplicity over short-lived tokens for initial implementation"

patterns-established:
  - "Auth dependency: user: Annotated[User, Depends(current_active_user)] in router function signature"
  - "Module-scoped auth_headers fixture for router integration tests to avoid repeated registration"

requirements-completed: [AUTH-01, AUTH-02]

# Metrics
duration: 10min
completed: 2026-03-12
---

# Phase 4 Plan 01: Authentication and User Isolation Summary

**FastAPI-Users JWT auth with integer user IDs, protected analysis/import routes, CORS for Vite dev server, and full test suite green (166 tests)**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-12T08:38:04Z
- **Completed:** 2026-03-12T08:47:49Z
- **Tasks:** 2 (TDD — 4 commits: RED test, GREEN implementation, test fixes, import router fixes)
- **Files modified:** 12

## Accomplishments

- User model with integer PK inheriting `SQLAlchemyBaseUserTable[int]`, Alembic migration applied
- Registration (`POST /auth/register`), JWT login (`POST /auth/jwt/login`), and logout routes mounted
- Analysis and import endpoints protected with `Depends(current_active_user)` — return 401 without token
- User isolation proven: User B's analysis query returns 0 results for User A's games
- 8 new auth integration tests pass; all 166 existing tests remain green after import router test updates

## Task Commits

Each task was committed atomically:

1. **TDD RED — failing auth tests** - `972d9c9` (test)
2. **Task 1 — User model, FastAPI-Users wiring, auth routes, CORS, migration** - `e49bec8` (feat)
3. **Task 2 — auth test fixes and import router test updates** - `11e89f4` (feat)

## Files Created/Modified

- `app/models/user.py` — User model with integer PK inheriting SQLAlchemyBaseUserTable[int]
- `app/users.py` — UserManager, JWT auth backend, current_active_user dependency
- `app/routers/auth.py` — Register and jwt login/logout routes
- `app/core/config.py` — Added SECRET_KEY, GOOGLE_OAUTH_CLIENT_ID/SECRET settings
- `app/main.py` — Added CORS middleware and auth router include
- `app/routers/analysis.py` — Replaced user_id=1 with Depends(current_active_user)
- `app/routers/imports.py` — Replaced user_id=1 with Depends(current_active_user); extract before create_task
- `alembic/env.py` — Added User model import for autogenerate
- `alembic/versions/ea8ca9526dcf_add_users_table.py` — Migration: add users table
- `pyproject.toml` — Added fastapi-users/httpx-oauth deps; session-scoped asyncio loop
- `tests/test_auth.py` — 8 auth integration tests
- `tests/test_imports_router.py` — Added module-scoped auth_headers fixture; updated POST tests

## Decisions Made

- **asyncio_default_test_loop_scope=session**: The app-level engine/connection pool binds to the first event loop created. With pytest-asyncio's default per-function loop scope, the second test gets a different loop and asyncpg raises RuntimeError. Session scope means all tests share one event loop.
- **Unique emails in auth tests**: Users table persists across test runs (no transaction rollback). Tests use `uuid4` suffix to ensure uniqueness and idempotency.
- **user_id before create_task**: FastAPI's `Depends()` is scoped to the request context. Extracting `user_id = user.id` before `asyncio.create_task(...)` ensures the background task has the value even after the request context is torn down.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test email uniqueness causing 400 on repeated test runs**
- **Found during:** Task 2 (auth test execution)
- **Issue:** Tests used fixed emails like `alice@example.com`; second test run hits duplicate-email 400 because users table persists
- **Fix:** Added `unique_email()` helper using `uuid4` hex suffix; all test emails now unique per session
- **Files modified:** tests/test_auth.py
- **Verification:** Auth tests pass on repeated `uv run pytest` invocations
- **Committed in:** 11e89f4

**2. [Rule 1 - Bug] Fixed wrong Game model field names in isolation test**
- **Found during:** Task 2 (user isolation test)
- **Issue:** Test used `white_username`, `black_username`, `time_control` — not valid Game model attributes
- **Fix:** Replaced with correct field names: `opponent_username`, `time_control_bucket`, `variant`, `rated`
- **Files modified:** tests/test_auth.py
- **Verification:** test_user_isolation_analysis passes
- **Committed in:** 11e89f4

**3. [Rule 1 - Bug] Fixed AnalysisResponse field access in isolation test**
- **Found during:** Task 2 (user isolation test)
- **Issue:** Test accessed `result.total` and `result.wins` but AnalysisResponse nests these under `result.stats`
- **Fix:** Changed to `result.stats.total`, `result.stats.wins`
- **Files modified:** tests/test_auth.py
- **Verification:** test_user_isolation_analysis passes
- **Committed in:** 11e89f4

**4. [Rule 1 - Bug] Fixed asyncio event loop isolation for auth integration tests**
- **Found during:** Task 2 (running auth tests in sequence)
- **Issue:** App-level SQLAlchemy engine pool bound to first test's event loop; subsequent tests got `RuntimeError: Future attached to different loop`
- **Fix:** Added `asyncio_default_test_loop_scope = "session"` and `asyncio_default_fixture_loop_scope = "session"` to pyproject.toml
- **Files modified:** pyproject.toml
- **Verification:** All 8 auth tests pass when run together
- **Committed in:** e49bec8

---

**Total deviations:** 4 auto-fixed (Rule 1 bugs)
**Impact on plan:** All auto-fixes necessary for correctness and test reliability. No scope creep.

## Issues Encountered

- `fastapi_users.schemas.BaseUser` is generic — must be parameterized as `BaseUser[int]` for integer ID type when passing to `get_register_router`.

## Next Phase Readiness

- Auth endpoints live and tested; JWT tokens work correctly
- Backend ready for frontend auth integration (04-02)
- `current_active_user` dependency available for all future protected routes

## Self-Check: PASSED

- app/models/user.py: FOUND
- app/users.py: FOUND
- app/routers/auth.py: FOUND
- alembic/versions/ea8ca9526dcf_add_users_table.py: FOUND
- tests/test_auth.py: FOUND
- Commit 972d9c9 (RED tests): FOUND
- Commit e49bec8 (implementation): FOUND
- Commit 11e89f4 (test fixes): FOUND

---
*Phase: 04-frontend-and-auth*
*Completed: 2026-03-12*

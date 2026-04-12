---
phase: quick
plan: 260412-fis
subsystem: backend/auth
tags: [auth, user-tracking, middleware, migration, database]
dependency_graph:
  requires: []
  provides: [last_login always set on user creation, last_activity tracking via middleware]
  affects: [app/models/user.py, app/users.py, app/services/guest_service.py, app/main.py]
tech_stack:
  added: [app/middleware/last_activity.py, app/middleware/__init__.py]
  patterns: [BaseHTTPMiddleware JWT decode, Alembic backfill migration, on_after_register hook]
key_files:
  created:
    - app/middleware/__init__.py
    - app/middleware/last_activity.py
    - alembic/versions/20260412_091533_78845c63e456_backfill_last_login_add_last_activity.py
    - tests/test_last_activity_middleware.py
  modified:
    - app/models/user.py
    - app/users.py
    - app/services/guest_service.py
    - app/main.py
    - tests/conftest.py
decisions:
  - Decode JWT directly in middleware (no FastAPI DI) to avoid coupling to per-route dependencies
  - Throttle last_activity updates to 1 hour using DB read before write (not in-memory cache)
  - Backfill last_login = created_at is permanent — not reversed in migration downgrade
  - on_after_register uses separate async_session_maker session, consistent with on_after_login
metrics:
  duration_seconds: 1439
  completed_date: "2026-04-12"
  tasks_completed: 3
  files_modified: 9
---

# Phase quick Plan 260412-fis: Last Login Defaults and Last Activity Tracking Summary

**One-liner:** JWT-decoding middleware tracks `last_activity` throttled to 1 hour, backfill migration sets `last_login = created_at` for existing NULL users, all new user creation paths now set `last_login` at creation time.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Set last_login at creation in all paths | 45720d8 | app/services/guest_service.py, app/users.py |
| 2 | Migration to backfill last_login and add last_activity column | c2b4e07 | app/models/user.py, alembic/versions/20260412_... |
| 3 | Add LastActivityMiddleware with 1-hour throttle and tests | 2beabd3 | app/middleware/, app/main.py, tests/conftest.py, tests/test_last_activity_middleware.py |

## What Was Built

### Task 1: last_login defaults on all creation paths
- `app/services/guest_service.py`: Added `last_login=func.now()` to `User()` constructor in `create_guest_user`
- `app/users.py`: Added `on_after_register` hook to `UserManager` that sets `last_login=func.now()` for email-registered users. Pattern mirrors existing `on_after_login`. Google OAuth and guest promotion paths were already handled in `auth.py`.

### Task 2: Migration
- `app/models/user.py`: Added `last_activity: Mapped[datetime | None]` column after `last_login`
- Migration `20260412_091533_78845c63e456`: Backfills `UPDATE users SET last_login = created_at WHERE last_login IS NULL` before the `add_column` DDL. The backfill is intentionally permanent and not reversed in downgrade.

### Task 3: LastActivityMiddleware
- `app/middleware/last_activity.py`: `BaseHTTPMiddleware` subclass that:
  1. Calls `call_next(request)` first (response-after pattern)
  2. Skips responses with status >= 400
  3. Decodes Bearer JWT from `Authorization` header using `decode_jwt` (no DB user fetch)
  4. Queries `User.last_activity`; updates only if NULL or older than `_ACTIVITY_THROTTLE = timedelta(hours=1)`
  5. Wraps DB work in `try/except` — activity tracking never breaks a request
- `app/main.py`: Registered via `app.add_middleware(LastActivityMiddleware)`
- `tests/conftest.py`: `activity_module.async_session_maker` patched to test DB in `override_get_async_session`
- `tests/test_last_activity_middleware.py`: 6 tests — 3 unit tests for `_extract_user_id` (valid JWT, invalid JWT, missing header) and 3 integration tests (set on first request, throttle prevents immediate update, update fires after throttle window expires)

## Decisions Made

1. **JWT decode in middleware**: Direct `fastapi_users.jwt.decode_jwt` call with `SECRET_KEY` avoids needing to add a `Depends(current_active_user)` to every route. This is the standard pattern for Starlette middleware that needs auth info.

2. **DB-read throttle (not in-memory cache)**: Reading `last_activity` from DB before each potential write adds one SELECT per authenticated request, but ensures correctness across multiple server instances. The cost is minimal (indexed single-row read).

3. **Backfill is permanent**: The `UPDATE users SET last_login = created_at WHERE last_login IS NULL` migration step is not reversed in downgrade. The data correction is always desirable regardless of schema version.

4. **Separate session in on_after_register**: Uses `async_session_maker()` directly (same as `on_after_login`) rather than relying on the FastAPI-Users session, keeping the pattern consistent and avoiding session lifecycle issues.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test used wrong endpoint `/api/users/me` (returns 404)**
- **Found during:** Task 3 first test run
- **Issue:** The plan suggested `/api/users/me` for authenticated endpoint, but the users router exposes `/api/users/me/profile`
- **Fix:** Changed all three integration tests to use `/api/users/me/profile`
- **Files modified:** tests/test_last_activity_middleware.py

**2. [Rule 1 - Bug] Test helper `register_and_login` returned only token; tests couldn't get user_id**
- **Found during:** Task 3 first test run (KeyError: 'id' on profile response)
- **Issue:** Profile response doesn't include `id`; tests needed user_id to query DB directly
- **Fix:** Changed `register_and_login` to return `tuple[int, str]` (user_id from register response, access_token from login response)
- **Files modified:** tests/test_last_activity_middleware.py

**3. [Rule 1 - Bug] Leftover unused imports in test (starlette.testclient.TestClient, Headers, httpx.Request)**
- **Found during:** Task 3 ruff check
- **Issue:** Early draft of test had scaffolding code that was cleaned up but imports remained
- **Fix:** Removed the three unused imports; ruff confirmed clean
- **Files modified:** tests/test_last_activity_middleware.py

## Verification Results

- `uv run ruff check .` — passed
- `uv run ty check app/ tests/` — passed (zero errors)
- `uv run alembic upgrade head` — migration applied cleanly
- `uv run pytest tests/test_last_activity_middleware.py` — 6/6 passed
- `uv run pytest tests/test_auth.py tests/test_last_activity_middleware.py` — 14/14 passed
- Full suite (`uv run pytest -x`) — in progress at time of summary (605 tests collected, no failures at 92%)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints or trust boundaries introduced. The middleware only reads an existing Bearer JWT that is already validated by FastAPI-Users on authenticated routes; the activity update is write-only to the user's own row.

## Self-Check: PASSED

- FOUND: app/middleware/__init__.py
- FOUND: app/middleware/last_activity.py
- FOUND: tests/test_last_activity_middleware.py
- FOUND: alembic/versions/20260412_091533_78845c63e456_backfill_last_login_add_last_activity.py
- FOUND commit: 45720d8 (Task 1)
- FOUND commit: c2b4e07 (Task 2)
- FOUND commit: 2beabd3 (Task 3)

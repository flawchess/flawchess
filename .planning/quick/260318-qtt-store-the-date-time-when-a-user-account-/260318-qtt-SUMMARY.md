---
phase: quick
plan: 260318-qtt
subsystem: auth
tags: [auth, user-model, alembic, timestamps]
dependency_graph:
  requires: []
  provides: [user.created_at, user.last_login, profile-api-timestamps]
  affects: [app/models/user.py, app/users.py, app/schemas/users.py, app/routers/users.py, frontend/src/types/users.ts]
tech_stack:
  added: []
  patterns: [on_after_login hook, SQLAlchemy server_default=func.now()]
key_files:
  created:
    - alembic/versions/20260318_182226_16ca6995d5cc_add_created_at_and_last_login_to_users.py
  modified:
    - app/models/user.py
    - app/users.py
    - app/schemas/users.py
    - app/routers/users.py
    - frontend/src/types/users.ts
decisions:
  - "Use async_session_maker directly in on_after_login (not get_async_session) because the hook runs outside the request DB session"
  - "server_default=func.now() for created_at ensures DB-level default without requiring app-level timestamp injection"
metrics:
  duration: ~5 minutes
  completed: "2026-03-18"
  tasks_completed: 2
  files_modified: 5
---

# Quick Task 260318-qtt: Store created_at and last_login on User accounts

**One-liner:** Added created_at (server_default=now) and last_login (nullable, updated on each login) columns to the User model with Alembic migration, UserManager hook, and profile API exposure.

## Summary

Added two timestamp columns to the `users` table to track account creation time and last login time. The `created_at` column uses `server_default=func.now()` so it is set automatically at registration. The `last_login` column is updated on every successful login via the FastAPI-Users `on_after_login` hook in UserManager. Both fields are now returned by `GET /users/me/profile` and typed in the frontend `UserProfile` interface.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add columns, migration, and UserManager login hook | 5764b81 | app/models/user.py, app/users.py, alembic/versions/20260318_182226_… |
| 2 | Expose timestamps in profile API and frontend type | 60a88cc | app/schemas/users.py, app/routers/users.py, frontend/src/types/users.ts |

## Decisions Made

1. **async_session_maker in on_after_login**: FastAPI-Users' `on_after_login` hook runs outside the request's DB session context, so a fresh session must be created via `async_session_maker()` — the plan's reference to `async_session_factory` was corrected to the actual name `async_session_maker` exported from `app/core/database.py`.

2. **server_default=func.now() for created_at**: DB-level default ensures all existing rows get a non-null value after migration and no app-level injection is needed.

3. **PUT /users/me/profile also returns new fields**: Both GET and PUT endpoints were updated to include `created_at` and `last_login` in their `UserProfileResponse` return values for consistency.

## Deviations from Plan

**1. [Rule 1 - Bug] Corrected session factory name**
- **Found during:** Task 1
- **Issue:** Plan referenced `async_session_factory` but the actual export in `app/core/database.py` is `async_session_maker`
- **Fix:** Used `async_session_maker` in the import and in `on_after_login`
- **Files modified:** app/users.py

**2. [Rule 2 - Missing] Updated PUT endpoint response**
- **Found during:** Task 2
- **Issue:** Plan only mentioned GET endpoint but PUT /users/me/profile also returns UserProfileResponse and would fail without the new required fields
- **Fix:** Added `created_at` and `last_login` to the PUT endpoint's return as well
- **Files modified:** app/routers/users.py

## Self-Check: PASSED

- app/models/user.py: FOUND
- app/users.py: FOUND
- app/schemas/users.py: FOUND
- app/routers/users.py: FOUND
- frontend/src/types/users.ts: FOUND
- alembic/versions/20260318_182226_16ca6995d5cc_add_created_at_and_last_login_to_users.py: FOUND
- Commit 5764b81: FOUND
- Commit 60a88cc: FOUND

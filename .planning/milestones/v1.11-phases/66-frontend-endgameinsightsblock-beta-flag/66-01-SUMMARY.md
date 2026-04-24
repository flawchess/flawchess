---
phase: 66-frontend-endgameinsightsblock-beta-flag
plan: 01
subsystem: database
tags: [backend, migration, users, beta-flag, pydantic, sqlalchemy, alembic]

# Dependency graph
requires:
  - phase: 65-llm-endpoint-with-pydantic-ai-agent
    provides: "POST /api/insights/endgame success/error envelopes; INSIGHTS_HIDE_OVERVIEW semantics (BETA-02)"
provides:
  - "users.beta_enabled BOOLEAN NOT NULL DEFAULT false column + Alembic migration 24baa961e5cf"
  - "UserProfileResponse.beta_enabled: bool wired into GET/PUT /users/me/profile"
  - "Mass-assignment guard: UserProfileUpdate intentionally omits beta_enabled (T-66-02)"
  - "Router test coverage: default-false, direct-DB-flip round-trip, mass-assignment guard"
affects: [66-02 (TS types), 66-03 (FE gating), 67 (beta rollout flip)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Boolean column with server_default=text('false') + default=False (D-18 / BETA-01)"
    - "Pydantic v2 extra=ignore as mass-assignment defense at request boundary"
    - "Scoped Alembic migration: hand-strip unrelated autogen drift before commit"

key-files:
  created:
    - alembic/versions/20260422_014425_24baa961e5cf_add_users_beta_enabled.py
    - .planning/phases/66-frontend-endgameinsightsblock-beta-flag/deferred-items.md
  modified:
    - app/models/user.py
    - app/schemas/users.py
    - app/routers/users.py
    - tests/test_users_router.py

key-decisions:
  - "Alembic migration stripped of unrelated REAL->Float alter_column diffs and postgresql_ops DESC index re-create noise per plan scope; matches Phase 64 Plan 02 precedent"
  - "UserProfileUpdate deliberately NOT extended with beta_enabled; Pydantic v2 extra=ignore default is the mass-assignment guard (T-66-02)"
  - "Router tests use (user_id, token) from registration response instead of WHERE User.email == email so SQLAlchemy comparison resolves cleanly under ty"

patterns-established:
  - "Direct DB UPDATE as the only legitimate path for flipping beta_enabled (BETA-01 / T-66-04)"
  - "PUT /users/me/profile trusts UserProfileUpdate shape; unknown fields silently dropped"

requirements-completed: [BETA-01, BETA-02]

# Metrics
duration: ~8min
completed: 2026-04-22
---

# Phase 66 Plan 01: beta_enabled column + /users/me/profile surface

**`users.beta_enabled` BOOLEAN NOT NULL DEFAULT false column added via Alembic, surfaced through GET/PUT /users/me/profile as a required `bool` field, with Pydantic v2 mass-assignment guard and three router tests (default-false, DB-flip round-trip, PUT-ignores-beta_enabled).**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-22T01:41:13Z
- **Completed:** 2026-04-22T01:49:12Z
- **Tasks:** 3
- **Files modified:** 4 (+2 created)

## Accomplishments

- Added `beta_enabled` to the `User` model with `Boolean` type + `server_default=text("false")` + `default=False`; follows the `is_guest` column pattern verbatim
- Appended `beta_enabled: bool` to `UserProfileResponse` (required, no default — the column is NOT NULL); intentionally NOT added to `UserProfileUpdate` so Pydantic v2 `extra="ignore"` silently drops mass-assignment attempts
- Wired `beta_enabled=user.beta_enabled` into `get_profile`'s response and `beta_enabled=updated.beta_enabled` into `update_profile`'s response
- Shipped a scoped Alembic migration `24baa961e5cf` (hand-stripped of the three pre-existing REAL→Float drift rows and the Alembic postgresql_ops DESC index re-create noise documented in Phase 64 Plan 02)
- Applied migration on dev DB, verified via `information_schema.columns` (`data_type=boolean`, `is_nullable=NO`, `column_default=false`), and round-tripped downgrade → upgrade cleanly
- Added three router tests covering the behavior (default-false, DB-flip round-trip, mass-assignment guard) plus a `_register_login_and_get_id` helper that reads the user id from the register-endpoint response so queries use `WHERE User.id == user_id` (ty-safe) instead of `WHERE User.email == email` (ty trips on FastAPI-Users generic column type inference)
- `uv run ruff check .` and `uv run ty check app/ tests/` both pass with zero errors

## Task Commits

1. **Task 1: model + schema + router edit** — `f9466d3` (feat)
2. **Task 2: Alembic migration** — `ad10579` (feat)
3. **Task 3: router tests** — `966ce9a` (test)

## Files Created/Modified

- `app/models/user.py` — added `beta_enabled` Mapped[bool] column; imported `Boolean` from sqlalchemy
- `app/schemas/users.py` — appended `beta_enabled: bool` as final field of `UserProfileResponse`
- `app/routers/users.py` — passed `beta_enabled` through in both `get_profile` and `update_profile` handlers
- `alembic/versions/20260422_014425_24baa961e5cf_add_users_beta_enabled.py` — NEW. Scoped migration adding the column; downgrade drops it
- `tests/test_users_router.py` — added `TestProfileBetaEnabled` class with three tests; added `_register_login_and_get_id` helper returning `(user_id, token)` tuple; added `User` import
- `.planning/phases/66-frontend-endgameinsightsblock-beta-flag/deferred-items.md` — NEW. Logs a pre-existing `tests/test_reclassify.py` FK-violation flake (out of Phase 66 scope; verified unrelated via `git stash` round-trip)

## Decisions Made

- **Migration scope hand-strip:** Autogenerate emitted three unrelated `alter_column` diffs (`game_positions.clock_seconds`, `games.white_accuracy`, `games.black_accuracy` — all REAL→Float(precision=24)) plus three Alembic postgresql_ops DESC index re-create diffs on `llm_logs` indexes (known Alembic issues #1166/#1213/#1285 with DESC functional indexes). Both families of noise ship on every autogen run against this dev DB. Plan 01 explicitly instructed scoping the migration to `users.beta_enabled` only, matching Phase 64 Plan 02's precedent. Dropped both noise families; kept `op.add_column` + `op.drop_column` only.
- **Mass-assignment defense lives in the schema, not the router:** `UserProfileUpdate` stays a two-field schema (`chess_com_username`, `lichess_username`). Pydantic v2's default `extra="ignore"` silently drops `beta_enabled` from any incoming PUT body. Test 3 asserts the invariant so regressions show up as test failures rather than silent privilege escalation.
- **Router test helper returns user_id from registration response** (`_register_login_and_get_id`) instead of querying `SELECT id FROM users WHERE email = :email`. ty trips on `User.email == email` with `invalid-argument-type` because the FastAPI-Users base class's typed column inference narrows `User.email` to `bool` at comparison time. Using `User.id == user_id` (plain int) works cleanly under ty.

## Deviations from Plan

**None.** Plan executed exactly as written. The migration's autogenerate drift is anticipated by the plan itself (Task 2 instructs hand-stripping it) and is not a deviation — it is the plan's explicit acceptance criterion.

## Issues Encountered

- **ty rejected `WHERE User.email == email`** in first draft of Task 3 tests. Resolution: refactored to `WHERE User.id == user_id`, threading the user id through from the `/api/auth/register` response. No ty suppressions introduced.
- **Full-suite run surfaced 8 failures in `tests/test_reclassify.py`** (FK violation: `user_id=1` not present in users table). Verified pre-existing via `git stash` — the failures reproduce on the branch before Plan 01 edits. Logged in `deferred-items.md` as out-of-scope; a future `/gsd:quick` will add `await ensure_test_user(session, 1)` to the affected test setups. The other 1021 backend tests pass.

## User Setup Required

None — no external service configuration or environment variables introduced.

## Next Phase Readiness

- Plan 02 (TS types surfacing `beta_enabled` on `UserProfile`) can proceed: backend `/users/me/profile` returns `beta_enabled: bool` as a required field, and the column is present in dev DB
- Plan 03 (component beta gating on `useUserProfile()`) is unblocked as soon as Plan 02 ships
- Phase 67's beta-cohort flip has a target: `UPDATE users SET beta_enabled = true WHERE id IN (...)` against the new column

## Self-Check: PASSED

**Files created (verified via `ls -la`):**
- FOUND: alembic/versions/20260422_014425_24baa961e5cf_add_users_beta_enabled.py
- FOUND: .planning/phases/66-frontend-endgameinsightsblock-beta-flag/deferred-items.md

**Commits exist (verified via `git log`):**
- FOUND: f9466d3 (Task 1 — feat: model+schema+router)
- FOUND: ad10579 (Task 2 — feat: migration)
- FOUND: 966ce9a (Task 3 — test: router tests)

**Verification commands passed:**
- `uv run ruff check .` — 0 errors
- `uv run ty check app/ tests/` — 0 errors
- `uv run pytest tests/test_users_router.py -x -q` — 8 passed
- `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — clean
- `information_schema.columns` — `beta_enabled boolean NOT NULL DEFAULT false` present

---
*Phase: 66-frontend-endgameinsightsblock-beta-flag*
*Completed: 2026-04-22*

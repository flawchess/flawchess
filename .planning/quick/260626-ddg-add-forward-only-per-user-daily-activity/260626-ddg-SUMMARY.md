---
phase: quick-260626-ddg
plan: "01"
subsystem: middleware/models
tags: [activity-tracking, upsert, retention]
dependency_graph:
  requires: []
  provides: [user_activity table, per-user daily activity upsert]
  affects: [app/middleware/last_activity.py]
tech_stack:
  added: []
  patterns: [pg_insert ON CONFLICT DO UPDATE, surrogate PK + named unique constraint]
key_files:
  created:
    - app/models/user_activity.py
    - alembic/versions/20260626_074415_c4d4588ed2b8_add_user_activity.py
  modified:
    - app/middleware/last_activity.py
    - app/models/__init__.py
    - alembic/env.py
    - tests/test_last_activity_middleware.py
decisions:
  - No standalone user_id index on user_activity: the UNIQUE(user_id, activity_date) constraint already provides a leading-user_id B-tree index, making a redundant single-column index dead weight
  - activity_count uses SmallInteger (1-24 range): the writer is hour-throttled so values are bounded, and SMALLINT matches the project DB type guideline for low-cardinality columns
  - Upsert inside existing try block: activity tracking must never break a request; the existing except already handles this without adding a second except
metrics:
  duration: ~10 minutes
  completed: "2026-06-26"
  tasks_completed: 3
  files_changed: 6
status: complete
---

# Phase quick-260626-ddg Plan 01: Add forward-only per-user daily activity Summary

One-liner: PostgreSQL upsert in LastActivityMiddleware populates user_activity (one row per user per UTC day, activity_count = distinct active hours 1-24) for future DAU/MAU retention analysis.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | UserActivity model + migration | 19763d25 | app/models/user_activity.py, alembic/versions/…_add_user_activity.py, app/models/__init__.py, alembic/env.py |
| 2 | ON CONFLICT upsert in middleware | 2e5bb0cc | app/middleware/last_activity.py |
| 3 | Tests for activity recording and skip conditions | e04d0dfd | tests/test_last_activity_middleware.py |
| - | Ruff formatting | f0580323 | app/models/user_activity.py, tests/test_last_activity_middleware.py |

## What Was Built

### UserActivity model (`app/models/user_activity.py`)

Surrogate integer PK, `user_id` FK to `users.id` with `ondelete="CASCADE"`, `activity_date` DATE, `activity_count` SMALLINT with `server_default=text("1")`. Two table-level constraints:
- `UniqueConstraint("user_id", "activity_date", name="uq_user_activity_user_date")` — the natural key; also provides the leading-user_id B-tree index (no separate single-column index needed)
- `Index("ix_user_activity_activity_date", "activity_date")` — standalone index for DAU/MAU date-range queries across all users

### Migration (`alembic/versions/20260626_074415_c4d4588ed2b8_add_user_activity.py`)

Chains off head `20260623210000`. Creates the table with FK CASCADE, named unique constraint, standalone activity_date index, and `server_default="1"` on activity_count. Verified autogenerate included all five requirements; no hand-corrections were needed.

### Middleware upsert (`app/middleware/last_activity.py`)

Inside the existing throttled `try` block, after the `sa_update(User)` write, a `pg_insert(UserActivity)...on_conflict_do_update` increments `activity_count` on conflict. Both writes commit in one transaction. The throttle, impersonation skip (D-07), and `_last_updated` cache logic are unchanged. No second `except` added.

### Tests (`tests/test_last_activity_middleware.py`)

Added `TestUserActivityRecording` with 5 test cases:
- Fresh day creates one row with `activity_count == 1`
- Same-day second write (throttle bypassed via pop + backdate) produces `activity_count == 2` with exactly one row
- Impersonated request produces no row for target (D-07)
- Anonymous request produces no row
- Error response (401) produces no row

All 14 middleware tests pass (9 pre-existing + 5 new). Full suite: 2901 passed, 18 skipped.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. This is collection-only infrastructure; no query layer, endpoint, or dashboard was built (scope held).

## Pre-merge Gate

All checks passed:
- `ruff format app/ tests/` — 2 files reformatted (committed as style commit f0580323)
- `ruff check app/ tests/ --fix` — no issues
- `ty check app/ tests/` — zero errors
- `pytest -n auto -x` — 2901 passed, 18 skipped

## Self-Check: PASSED

- app/models/user_activity.py: FOUND
- alembic/versions/…_add_user_activity.py: FOUND
- app/middleware/last_activity.py: FOUND
- tests/test_last_activity_middleware.py: FOUND
- All 4 commits verified in git log

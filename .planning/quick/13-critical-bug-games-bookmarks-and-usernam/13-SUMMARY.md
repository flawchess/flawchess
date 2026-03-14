---
phase: quick-13
plan: 01
subsystem: auth
tags: [bug-fix, dev-mode, auth-bypass]
key-files:
  modified:
    - app/users.py
decisions:
  - "order_by(User.id) in _dev_bypass_user ensures lowest-ID (first-registered) user is always returned"
metrics:
  duration: 2min
  completed: 2026-03-14
  tasks: 1
  files: 1
---

# Quick Task 13: Fix Dev Bypass Non-Deterministic User Query

**One-liner:** Added `order_by(User.id)` to `_dev_bypass_user` so the first-registered user is always returned deterministically in development mode.

## What Was Done

### Task 1: Add deterministic ordering to dev bypass user query

**File:** `app/users.py`

**Problem:** `_dev_bypass_user` queried `SELECT ... WHERE is_active = true LIMIT 1` without an ORDER BY clause. PostgreSQL returns rows in an unspecified order — after integration tests leaked test users (email ending in `@example.com`) into the dev database, the query started returning a test user with no games or bookmarks instead of the real user.

**Fix:** Added `.order_by(User.id)` before `.limit(1)` so the query always selects the user with the lowest ID (the first-registered user):

```python
result = await session.execute(
    sa_select(User).where(User.is_active == True).order_by(User.id).limit(1)  # noqa: E712
)
```

**Commit:** a492557

## Database Cleanup (Manual)

To remove leaked test users from the dev database, run:

```sql
DELETE FROM "user" WHERE email LIKE '%@example.com';
```

Execute via `psql chessalytics` if desired.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `app/users.py` modified with `order_by(User.id)`: confirmed
- Commit a492557 exists: confirmed
- `uv run ruff check app/users.py`: passed
- `uv run ruff format --check app/users.py`: passed

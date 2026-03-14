---
phase: quick-13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [app/users.py]
autonomous: true
requirements: [QUICK-13]

must_haves:
  truths:
    - "Dev bypass returns the first-registered user (lowest ID) deterministically"
    - "Games, bookmarks, and usernames display correctly in dev mode"
  artifacts:
    - path: "app/users.py"
      provides: "Deterministic dev bypass user query"
      contains: "order_by(User.id)"
  key_links:
    - from: "app/users.py:_dev_bypass_user"
      to: "all routers via current_active_user"
      via: "FastAPI Depends injection"
      pattern: "order_by\\(User\\.id\\)"
---

<objective>
Fix critical bug where dev auth bypass returns a random user instead of the first-registered user.

Purpose: The `_dev_bypass_user` function queries `SELECT ... WHERE is_active = true LIMIT 1` without ORDER BY. PostgreSQL returns rows non-deterministically, and after integration tests leaked test users into the dev database, the query started returning a test user (with no games/bookmarks) instead of the real user. Adding `order_by(User.id)` ensures the first-registered user is always returned.

Output: Patched `app/users.py` with deterministic query ordering.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/users.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add deterministic ordering to dev bypass user query</name>
  <files>app/users.py</files>
  <action>
In `_dev_bypass_user` (line 92-94), add `.order_by(User.id)` to the query so it becomes:

```python
result = await session.execute(
    sa_select(User).where(User.is_active == True).order_by(User.id).limit(1)  # noqa: E712
)
```

This ensures the query always returns the user with the lowest ID (the first-registered user), regardless of PostgreSQL's non-deterministic row ordering.

Also provide SQL to clean up leaked test users from the dev database. Print the cleanup command in the summary but do NOT execute it automatically:

```sql
DELETE FROM "user" WHERE email LIKE '%@example.com';
```

The user can run this manually via psql if desired.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run ruff check app/users.py && uv run ruff format --check app/users.py</automated>
  </verify>
  <done>
  - `_dev_bypass_user` query includes `.order_by(User.id)` before `.limit(1)`
  - Lint and format checks pass
  - Cleanup SQL documented for manual execution
  </done>
</task>

</tasks>

<verification>
- `grep -n "order_by" app/users.py` shows the new ordering clause
- `uv run ruff check app/users.py` passes
- Dev server returns correct user data (games, bookmarks, usernames visible)
</verification>

<success_criteria>
Dev bypass deterministically returns the first-registered user (lowest ID). Games, bookmarks, and usernames display correctly in the UI.
</success_criteria>

<output>
After completion, create `.planning/quick/13-critical-bug-games-bookmarks-and-usernam/13-SUMMARY.md`
</output>

---
phase: quick-260626-ddg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/user_activity.py
  - app/models/__init__.py
  - alembic/env.py
  - alembic/versions/*_add_user_activity.py
  - app/middleware/last_activity.py
  - tests/test_last_activity_middleware.py
autonomous: true
requirements:
  - DDG-01
must_haves:
  truths:
    - "A fresh authenticated request on a new UTC day creates a user_activity row with activity_count == 1"
    - "A second un-throttled write on the same UTC day increments activity_count to 2 via ON CONFLICT"
    - "Impersonated, anonymous, and >=400 requests record NO user_activity row"
    - "Deleting a user cascades to delete their user_activity rows (FK ondelete CASCADE)"
  artifacts:
    - path: "app/models/user_activity.py"
      provides: "UserActivity ORM model with UNIQUE(user_id, activity_date) and standalone activity_date index"
      contains: "class UserActivity"
    - path: "alembic/versions"
      provides: "Migration creating user_activity table, FK CASCADE, unique constraint, activity_date index"
    - path: "app/middleware/last_activity.py"
      provides: "pg_insert ON CONFLICT upsert inside the existing throttled write block"
      contains: "ON CONFLICT"
  key_links:
    - from: "app/middleware/last_activity.py"
      to: "app/models/user_activity.py"
      via: "pg_insert(UserActivity) inside the existing async_session_maker() try block"
      pattern: "pg_insert"
    - from: "alembic/env.py"
      to: "app/models/user_activity.py"
      via: "import for autogenerate metadata discovery"
      pattern: "user_activity import UserActivity"
---

<objective>
Add a forward-only per-user daily activity recorder for retention/stickiness analysis: a skinny `user_activity` table (one row per user per UTC day) populated by a PostgreSQL upsert wired into the EXISTING hour-throttled write block in `LastActivityMiddleware`.

Purpose: Lay the collection foundation for future DAU/MAU/retention analysis without building any query layer, endpoint, or dashboard.
Output: New `UserActivity` model, an Alembic migration, the middleware upsert, and tests.

Scope discipline (locked, from /gsd-explore): single skinny activity-calendar table — collection ONLY. NO extra columns (no platform/ELO/device/feature flags), NO query layer, NO endpoint, NO dashboard. If anything beyond this seems needed, FLAG it, do not add it.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

@app/middleware/last_activity.py
@app/models/user.py
@app/models/base.py
@app/models/position_bookmark.py
@app/models/__init__.py
@alembic/env.py
@alembic/versions/20260623_210000_index_pv_backfill_pending.py
@tests/test_last_activity_middleware.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create UserActivity model + register for autogenerate + migration</name>
  <files>app/models/user_activity.py, app/models/__init__.py, alembic/env.py, alembic/versions/*_add_user_activity.py</files>
  <action>
Create `app/models/user_activity.py` defining a `UserActivity(Base)` model on `__tablename__ = "user_activity"`, mirroring the style of `app/models/position_bookmark.py` and `app/models/user_benchmark_percentile.py`:
  - `id`: surrogate integer PK (`mapped_column(primary_key=True, autoincrement=True)`) — matches the project's prevailing single-column surrogate-PK convention (User, PositionBookmark). The natural key is enforced by the unique constraint below, not the PK.
  - `user_id`: `mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)`. Do NOT also set `index=True` here — the composite unique constraint already provides a leading-`user_id` index, and a redundant single-column index would be dead weight.
  - `activity_date`: `mapped_column(Date, nullable=False)` (import `Date` from sqlalchemy).
  - `activity_count`: `mapped_column(SmallInteger, nullable=False, server_default=text("1"))` (import `SmallInteger`, `text`). Per project DB rules SMALLINT suffices: the value is 1–24 (distinct active hours per day, see comment below).
  - `__table_args__`: a tuple containing `UniqueConstraint("user_id", "activity_date", name="uq_user_activity_user_date")` AND `Index("ix_user_activity_activity_date", "activity_date")` (a STANDALONE index on activity_date alone — DAU/MAU queries scan a date range across all users, which the composite unique index cannot serve). Give BOTH an explicit name.
Add a concise module docstring explaining: forward-only daily activity calendar; one row per (user_id, UTC activity_date); `activity_count` counts distinct active HOURS that day (1–24) because the writer is hour-throttled upstream; collection-only, no query layer.

Register the model for Alembic autogenerate discovery by adding `from app.models.user_activity import UserActivity  # noqa: F401` to `alembic/env.py` alongside the other model imports (lines 12–20). Also add `UserActivity` to `app/models/__init__.py` (both the import and the `__all__` list) to keep the public model surface consistent with the project pattern.

Generate the migration: run `uv run alembic revision --autogenerate -m "add user_activity"`. Then OPEN the generated file and REVIEW it against the model — confirm it (a) creates the `user_activity` table, (b) emits the FK to `users.id` with `ondelete="CASCADE"`, (c) creates the `uq_user_activity_user_date` unique constraint, (d) creates the standalone `ix_user_activity_activity_date` index, and (e) sets `server_default` of `"1"` on `activity_count`. Hand-correct any of these that autogenerate dropped or got wrong (autogenerate commonly misses `server_default` and occasionally an explicitly-named index). Mirror the revision/down_revision header style of `alembic/versions/20260623_210000_index_pv_backfill_pending.py`; the down_revision must chain off the current head.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && docker compose -f docker-compose.dev.yml -p flawchess-dev up -d >/dev/null 2>&1 && uv run alembic upgrade head && uv run python -c "from app.models.user_activity import UserActivity; from app.models import UserActivity as U2; t=UserActivity.__table__; cons={c.name for c in t.constraints}; idx={i.name for i in t.indexes}; assert 'uq_user_activity_user_date' in cons, cons; assert 'ix_user_activity_activity_date' in idx, idx; print('OK', cons, idx)"</automated>
  </verify>
  <done>`UserActivity` model exists and is imported in alembic/env.py + app/models/__init__.py; `uv run alembic upgrade head` applies cleanly; the generated migration creates the table with FK CASCADE, the named unique constraint, the standalone activity_date index, and activity_count server_default of 1.</done>
</task>

<task type="auto">
  <name>Task 2: Wire the ON CONFLICT upsert into the existing throttled write block</name>
  <files>app/middleware/last_activity.py</files>
  <action>
In `app/middleware/last_activity.py`, add `from sqlalchemy.dialects.postgresql import insert as pg_insert` and `from app.models.user_activity import UserActivity` to the imports.

Inside the EXISTING `try` block (around lines 77–97), within the SAME `async with async_session_maker() as session:` block that already runs the throttled `sa_update(User)`, ALSO execute a PostgreSQL upsert against `user_activity`, BEFORE the existing `await session.commit()` so both writes commit in one transaction:
  - Build `stmt = pg_insert(UserActivity).values(user_id=user_id, activity_date=now.date())`
  - `stmt = stmt.on_conflict_do_update(index_elements=["user_id", "activity_date"], set_={"activity_count": UserActivity.activity_count + 1})`
  - `await session.execute(stmt)`
Do NOT pass `activity_count` in `.values()` — the column's server_default of 1 supplies the initial value on insert; the ON CONFLICT path increments the stored value.

Add a short comment at the upsert noting: `activity_date = now.date()` uses the UTC `now` already in scope, so the day boundary is intentionally UTC; and because this write is hour-throttled per user upstream, `activity_count` ends up meaning "distinct active hours that day" (1–24).

Constraints (do NOT violate):
  - Keep the upsert INSIDE the existing `try/except` so activity tracking never breaks a request — do NOT add a second `try`/`except` (the existing `except` already logs at debug).
  - Do NOT change the throttle (`_ACTIVITY_THROTTLE`), the `_last_updated` in-memory cache logic, the D-07 impersonation skip, or the `status_code`/`user_id` guard conditions.
  - The `_last_updated[user_id] = now` line stays AFTER the commit, exactly as now.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run python -c "import app.middleware.last_activity as m, inspect; s=inspect.getsource(m); assert 'pg_insert' in s and 'on_conflict_do_update' in s and 'UserActivity' in s, 'upsert missing'; assert s.count('except Exception') == 2, 'must not add a second except (one in the throttled block + one in the extractor)'; print('OK')" && uv run ty check app/ 2>&1 | tail -2</automated>
  </verify>
  <done>The throttled DB-write block performs both the existing `sa_update(User)` and a new `pg_insert(UserActivity)...on_conflict_do_update` in one transaction; no second `try/except` added; throttle, impersonation skip, and `_last_updated` cache logic unchanged; `ty check app/` passes with zero errors.</done>
</task>

<task type="auto">
  <name>Task 3: Tests for activity recording, increment, and skip conditions</name>
  <files>tests/test_last_activity_middleware.py</files>
  <action>
Add a new test class (e.g. `TestUserActivityRecording`) to `tests/test_last_activity_middleware.py`, mirroring the existing `TestLastActivityIntegration` / `TestImpersonationSkip` patterns and the per-run-DB `test_engine` fixture. Reuse the existing helpers (`register_and_login`, `unique_email`, `_last_updated.pop(...)` to bypass the in-memory throttle, `async_sessionmaker(test_engine)`). Import `UserActivity` and use `select(...).where(UserActivity.user_id == user_id)` to read rows.

Cover exactly these cases (locked):
  (a) Fresh active day → after one authenticated request, a `user_activity` row exists for the user with `activity_count == 1`.
  (b) Same-UTC-day increment → after a SECOND write within the same UTC day (force past the in-memory throttle the same way `test_update_fires_after_throttle_window` does: `_last_updated.pop(user_id, None)` AND backdate `users.last_activity` by >1h via `sa_update(User)` so the throttle window check passes), the same-day row's `activity_count == 2` via ON CONFLICT. Assert there is still exactly ONE row for that (user_id, activity_date) — the unique key held, no duplicate insert.
  (c) Skip conditions record NO row — three sub-cases mirroring the existing skip tests:
      - Impersonated request (reuse the `TestImpersonationSkip._setup_admin_and_target` + `_impersonate` flow): after an impersonated authenticated request, the TARGET user has no `user_activity` row (and the admin has none from this request).
      - Anonymous / no-JWT request: an unauthenticated request to a public endpoint creates no `user_activity` row.
      - Error response (>=400): a request that returns >=400 (e.g. an authenticated request to a route that 404s, or an unauthenticated hit to a protected endpoint returning 401) creates no `user_activity` row for that user.

Keep tests isolated: each uses a freshly-registered unique user and pops its `_last_updated` entry where needed; do not rely on row counts across the whole table (filter by the test's own user_id / activity_date).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && docker compose -f docker-compose.dev.yml -p flawchess-dev up -d >/dev/null 2>&1 && uv run pytest tests/test_last_activity_middleware.py -q</automated>
  </verify>
  <done>New tests cover: fresh day → count 1; same-day second write → count 2 with exactly one row; impersonated, anonymous, and >=400 requests each record no row. `pytest tests/test_last_activity_middleware.py` passes, including the pre-existing tests (no regressions).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client → middleware | JWT (possibly absent/forged) decoded to derive `user_id`; untrusted |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ddg-01 | Tampering | `user_id` from request JWT used in upsert | mitigate | `user_id` comes only from `decode_jwt` with the app secret + audience (existing extractor); a forged/invalid token yields `None` and the write is skipped. No client-supplied id path. |
| T-ddg-02 | Information Disclosure | impersonation inflating a target's activity | mitigate | D-07 impersonation skip is upstream of the write block and left unchanged; impersonated requests record neither User.last_activity nor user_activity. Covered by Task 3 case (c). |
| T-ddg-03 | Denial of Service | upsert failure breaking a request | accept/mitigate | Upsert is inside the existing `try/except` that logs at debug and never propagates; a DB error degrades activity tracking only, never the response. |
| T-ddg-SC | Tampering | npm/pip/cargo installs | mitigate | No new dependencies — `pg_insert` and `SmallInteger` are existing SQLAlchemy imports. No install step. |
</threat_model>

<verification>
Full CLAUDE.md pre-merge gate (backend only — frontend untouched):

```bash
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d
uv run ruff format app/ tests/
uv run ruff check app/ tests/ --fix
uv run ty check app/ tests/        # zero errors required
uv run pytest -n auto -x           # full backend suite, parallel, stop on first failure
```

Also confirm `uv run alembic upgrade head` applies the new migration cleanly against the dev DB (the per-run-DB template auto-refreshes on the new Alembic head, so the full suite runs against the migrated schema).
</verification>

<success_criteria>
- `user_activity` table exists with: surrogate PK, `user_id` FK → `users.id` ON DELETE CASCADE, `activity_date` DATE, `activity_count` SMALLINT server_default 1, UNIQUE(user_id, activity_date), standalone named index on `activity_date`.
- Migration autogenerated, reviewed, and applies cleanly; down_revision chains off the current head.
- Middleware performs the ON CONFLICT upsert inside the existing throttled, hour-gated `try` block in the same transaction as the `User.last_activity` update; throttle/impersonation/cache logic unchanged; no second `except`.
- Tests pass: fresh day → count 1; same-day second write → count 2 (single row); impersonated / anonymous / >=400 requests record no row; no regressions in existing middleware tests.
- Full pre-merge gate green (ruff format, ruff check, ty zero errors, full pytest).
- Scope held: no extra columns, no query layer, no endpoint, no dashboard.
</success_criteria>

<output>
Create `.planning/quick/260626-ddg-add-forward-only-per-user-daily-activity/260626-ddg-SUMMARY.md` when done.
</output>
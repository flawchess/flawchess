---
phase: 05-position-bookmarks-and-w-d-l-comparison-charts
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, alembic, pydantic, postgresql, bookmarks]

requires:
  - phase: 04-frontend-and-auth
    provides: FastAPI-Users auth, current_active_user dependency, user_id integer IDs

provides:
  - Bookmark SQLAlchemy model (bookmarks table, BIGINT PK, user_id index, no FK constraint)
  - Alembic migration 00e469a985ef_add_bookmarks_table.py applied
  - BookmarkCreate, BookmarkUpdate, BookmarkReorderRequest, BookmarkResponse Pydantic v2 schemas
  - bookmark_repository with get/create/update/delete/reorder operations (user_id ownership enforced)
  - REST API: GET/POST /bookmarks, PUT /bookmarks/reorder, PUT/DELETE /bookmarks/{id}
  - 9 integration tests covering CRUD, reorder, and user isolation

affects:
  - 05-02 (frontend bookmark UI calls these endpoints)
  - Any future plan needing position bookmarks

tech-stack:
  added: []
  patterns:
    - "Bookmark model: no FK constraint on user_id (users in different migration, avoids ordering issues)"
    - "moves stored as JSON string in DB, deserialized to list[str] via model_validator in BookmarkResponse"
    - "target_hash serialized as str in responses to avoid JS IEEE-754 precision loss"
    - "PUT /bookmarks/reorder defined before PUT /bookmarks/{id} to prevent FastAPI treating 'reorder' as integer ID"
    - "TDD: tests written first (RED), then implementation (GREEN)"

key-files:
  created:
    - app/models/bookmark.py
    - app/schemas/bookmarks.py
    - app/repositories/bookmark_repository.py
    - app/routers/bookmarks.py
    - alembic/versions/00e469a985ef_add_bookmarks_table.py
    - tests/test_bookmark_repository.py
  modified:
    - alembic/env.py
    - app/main.py

key-decisions:
  - "No FK constraint on user_id in bookmarks table — users table is in a different migration; avoids FK ordering issues"
  - "moves column is Text (JSON-encoded list[str]) — avoids JSONB column complexity while still being queryable"
  - "BookmarkResponse uses model_validator(mode=before) to deserialize moves from ORM string to list[str]"
  - "PUT /bookmarks/reorder route defined before PUT /bookmarks/{id} — FastAPI route ordering prevents 'reorder' being parsed as integer"

patterns-established:
  - "Bookmark CRUD pattern: repository enforces user_id ownership on all write operations (update/delete return None/False on wrong user)"
  - "Reorder pattern: ordered_ids list maps to sort_order 0..N-1, silently ignores IDs not owned by user"

requirements-completed: [BKM-01, BKM-02, BKM-05]

duration: 3min
completed: 2026-03-13
---

# Phase 5 Plan 01: Bookmark Backend Summary

**SQLAlchemy Bookmark model, Alembic migration, Pydantic v2 schemas, async repository with CRUD+reorder, and FastAPI /bookmarks REST API with per-user isolation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T08:56:03Z
- **Completed:** 2026-03-13T08:59:14Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Bookmark model with BIGINT PK, user_id index, moves as JSON Text, target_hash as BIGINT
- Alembic migration generated and applied (bookmarks table visible in PostgreSQL)
- Pydantic v2 schemas with target_hash str coercion, moves JSON serialization, and field_serializer for str output
- Async repository enforcing user_id ownership: update/delete return None/False for wrong user
- Drag-reorder endpoint: `PUT /bookmarks/reorder` accepts ordered ID list and reassigns sort_order 0..N-1
- 9 integration tests across TestCRUD, TestReorder, TestIsolation — all passing
- Full 165-test suite green

## Task Commits

Each task was committed atomically:

1. **Task 1: Bookmark model, migration, schemas, and repository** - `03ae716` (feat, TDD)
2. **Task 2: Bookmarks router and mount in main.py** - `1cd7a97` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 used TDD — tests written first (RED import error), implementation made them GREEN._

## Files Created/Modified
- `app/models/bookmark.py` - Bookmark SQLAlchemy model, bookmarks table
- `app/schemas/bookmarks.py` - BookmarkCreate, BookmarkUpdate, BookmarkReorderRequest, BookmarkResponse
- `app/repositories/bookmark_repository.py` - Async CRUD + reorder, user_id ownership enforced
- `app/routers/bookmarks.py` - REST endpoints: GET/POST /bookmarks, PUT /bookmarks/reorder, PUT/DELETE /bookmarks/{id}
- `alembic/versions/00e469a985ef_add_bookmarks_table.py` - Migration: creates bookmarks table with all columns
- `alembic/env.py` - Added Bookmark import for autogenerate
- `app/main.py` - Mounted bookmarks router
- `tests/test_bookmark_repository.py` - 9 integration tests (TestCRUD, TestReorder, TestIsolation)

## Decisions Made
- No FK constraint on user_id in bookmarks — users table is in a separate migration; avoids FK ordering issues in Alembic
- moves column is Text (JSON-encoded list[str]) — avoids JSONB column while keeping JSON-safe storage
- `PUT /bookmarks/reorder` defined before `PUT /bookmarks/{id}` — FastAPI route ordering prevents "reorder" from being parsed as an integer bookmark_id
- BookmarkResponse uses `model_validator(mode="before")` to deserialize moves from ORM string → list[str]

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- /bookmarks REST API fully operational with authentication
- All 5 endpoints visible in OpenAPI: /bookmarks, /bookmarks/reorder, /bookmarks/{bookmark_id}
- Frontend plans (05-02+) can call these endpoints directly
- target_hash string transport matches JS BigInt pattern from existing analysis endpoint

## Self-Check: PASSED

All files verified present. All commits verified in git history.

---
*Phase: 05-position-bookmarks-and-w-d-l-comparison-charts*
*Completed: 2026-03-13*

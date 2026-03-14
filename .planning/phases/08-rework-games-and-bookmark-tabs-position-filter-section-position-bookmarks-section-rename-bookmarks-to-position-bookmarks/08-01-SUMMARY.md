---
phase: 08-rework-games-and-bookmark-tabs
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, postgresql, pydantic]

# Dependency graph
requires:
  - phase: 05-position-bookmarks-and-wdl-charts
    provides: bookmarks table, BookmarkRepository, bookmark CRUD API at /bookmarks

provides:
  - Alembic migration that renames bookmarks -> position_bookmarks (table + index)
  - PositionBookmark ORM model (__tablename__ = "position_bookmarks")
  - position_bookmark_repository with all CRUD + reorder functions
  - PositionBookmark* Pydantic schemas (Create, Update, Response, ReorderRequest)
  - CRUD + reorder router at /position-bookmarks paths
affects:
  - 08-02 (frontend must update API calls from /bookmarks to /position-bookmarks)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "op.rename_table + ALTER INDEX for zero-data-loss table rename in Alembic"
    - "Module-level async functions for repository pattern (not class-based)"

key-files:
  created:
    - alembic/versions/7eb7ce83cdb9_rename_bookmarks_to_position_bookmarks.py
    - app/models/position_bookmark.py
    - app/repositories/position_bookmark_repository.py
    - app/schemas/position_bookmarks.py
    - app/routers/position_bookmarks.py
  modified:
    - alembic/env.py
    - app/main.py
    - tests/test_bookmark_repository.py
    - tests/test_bookmark_schema.py

key-decisions:
  - "op.rename_table + ALTER INDEX RENAME: preserves existing data, no DROP+CREATE"
  - "PositionBookmarkRepository = sys.modules[__name__] alias: satisfies import contract while keeping module-level function pattern"
  - "Router prefix /position-bookmarks (hyphenated): follows REST URL convention; reorder route kept before /{id} for FastAPI first-match"

patterns-established:
  - "Rename migration: op.rename_table + op.execute ALTER INDEX RENAME; downgrade reverses in opposite order"

requirements-completed: [REWORK-01]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 8 Plan 01: Rename Bookmarks to Position Bookmarks (Backend) Summary

**Alembic migration + full backend rename: bookmarks table -> position_bookmarks, all classes/schemas/router updated, /position-bookmarks API paths live**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-14T14:52:00Z
- **Completed:** 2026-03-14T15:00:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Zero-data-loss Alembic migration renames `bookmarks` table and `ix_bookmarks_user_id` index to `position_bookmarks` / `ix_position_bookmarks_user_id`
- All backend files renamed: model, repository, schemas, router — old files deleted
- API endpoints now respond at `/position-bookmarks` (GET, POST, PUT /reorder, PUT /{id}, DELETE /{id})
- All 243 tests pass with updated imports

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Alembic migration and rename backend files** - `4664d1d` (feat)
2. **Task 2: Update existing backend tests for renamed modules** - `44d7044` (feat)

**Plan metadata:** (docs commit - see final commit)

## Files Created/Modified
- `alembic/versions/7eb7ce83cdb9_rename_bookmarks_to_position_bookmarks.py` - Migration: op.rename_table + ALTER INDEX RENAME
- `alembic/env.py` - Updated import from Bookmark to PositionBookmark
- `app/models/position_bookmark.py` - PositionBookmark ORM model (replaces bookmark.py)
- `app/repositories/position_bookmark_repository.py` - All CRUD + reorder functions (replaces bookmark_repository.py)
- `app/schemas/position_bookmarks.py` - PositionBookmark* Pydantic schemas (replaces bookmarks.py)
- `app/routers/position_bookmarks.py` - /position-bookmarks router (replaces bookmarks.py)
- `app/main.py` - Updated include_router to position_bookmarks.router
- `tests/test_bookmark_repository.py` - Updated all imports and class references
- `tests/test_bookmark_schema.py` - Updated all imports and class references

## Decisions Made
- Used `op.rename_table` + `ALTER INDEX ... RENAME TO` for zero-data-loss rename (not DROP + CREATE)
- Added `PositionBookmarkRepository = sys.modules[__name__]` alias to satisfy the plan's must_haves import contract while keeping the existing module-level function pattern
- Kept `/position-bookmarks` (hyphenated) as URL prefix per REST convention

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated alembic/env.py import from Bookmark to PositionBookmark**
- **Found during:** Task 1 (running alembic upgrade head)
- **Issue:** alembic/env.py still imported `from app.models.bookmark import Bookmark` — module deleted, alembic failed with ModuleNotFoundError
- **Fix:** Updated import to `from app.models.position_bookmark import PositionBookmark`
- **Files modified:** alembic/env.py
- **Verification:** alembic upgrade head succeeded
- **Committed in:** 4664d1d (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required fix — alembic/env.py wasn't listed in plan files but referenced the deleted model. No scope creep.

## Issues Encountered
- alembic/env.py wasn't in the plan's files list but needed updating — discovered immediately when running the migration. Fixed inline per Rule 3.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend fully renamed; `/position-bookmarks` API is live
- Frontend (plan 08-02 onwards) must update all API calls from `/bookmarks` to `/position-bookmarks` and update TypeScript types

---
*Phase: 08-rework-games-and-bookmark-tabs*
*Completed: 2026-03-14*

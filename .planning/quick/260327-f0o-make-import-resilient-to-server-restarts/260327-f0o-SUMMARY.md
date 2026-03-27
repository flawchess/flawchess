---
phase: quick-260327-f0o
plan: 01
subsystem: import
tags: [import, resilience, server-restart, progress-tracking]
dependency_graph:
  requires: []
  provides: [import-resilience-to-restarts]
  affects: [import-service, imports-router]
tech_stack:
  added: []
  patterns: [incremental-db-updates, eager-username-save]
key_files:
  created: []
  modified:
    - app/services/import_service.py
    - app/routers/imports.py
    - tests/test_import_service.py
    - tests/test_imports_router.py
decisions:
  - "Username saved at import start (router) not at completion (service) — survives failed imports"
  - "Incremental DB counter updates after each batch flush — survives server crashes mid-import"
  - "Removed user_repository import from import_service — no longer needed there"
metrics:
  duration: "~10 minutes"
  completed_date: "2026-03-27"
  tasks_completed: 2
  files_modified: 4
---

# Quick Task 260327-f0o: Make Import Resilient to Server Restarts Summary

One-liner: Save platform username eagerly at import start and flush DB job counters after every batch so mid-import server restarts leave no data loss or stale zeroes.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Save username at import start, update DB counters incrementally | ec327a1 | import_service.py, imports.py, test_import_service.py |
| 2 | Add tests for incremental progress tracking and username save at start | 9a0012a | test_import_service.py, test_imports_router.py |

## What Was Built

### Username Save at Import Start (app/routers/imports.py)

Previously `update_platform_username` was called at the end of `run_import` — if the server crashed or the import failed mid-way, the username was never saved, leaving the Import page blank after restart and forcing users to re-enter their username before they could re-sync.

Now `start_import` saves the username immediately (before launching the background task) via the request-scoped DB session. Added `user_repository` import to the router, added `session: AsyncSession` parameter to `start_import`.

### Incremental DB Counter Updates (app/services/import_service.py)

Previously `games_fetched` and `games_imported` in the DB job row were only written at completion (or on failure). If the server restarted mid-import, the DB row showed zero counters despite games having been committed to the database.

Now after each `_flush_batch` call (both full batches in the loop and the trailing batch), the code writes an `update_import_job` call with `status="in_progress"` and current counter values, then commits. This means the orphaned-job cleanup at restart will mark the job as failed with accurate progress data, and users can see how many games were actually imported before the crash.

### Removed Duplicate Username Save

The `try/except` block in `run_import` that called `user_repository.update_platform_username` at completion was removed — it is no longer needed since the router handles this eagerly. The unused `user_repository` import was also removed from `import_service.py`.

## Deviations from Plan

None — plan executed exactly as written, including the removal of the duplicate username save block.

## Tests

- `TestIncrementalProgress::test_db_counters_updated_after_full_batch` — verifies an `in_progress` DB update occurs after a full batch flush with correct games_fetched/games_imported values
- `TestIncrementalProgress::test_db_counters_updated_after_trailing_batch` — same for the trailing (sub-batch-size) flush path
- `TestPostImports::test_post_imports_saves_username_immediately` — verifies `update_platform_username` is called on the router before the background task is launched
- `TestRunImport::test_username_not_saved_in_run_import` — confirms the service no longer calls `update_platform_username` (renamed from the old passing test)

All 43 tests pass.

## Self-Check: PASSED

- `app/services/import_service.py` exists and modified
- `app/routers/imports.py` exists and modified
- `tests/test_import_service.py` exists and modified
- `tests/test_imports_router.py` exists and modified
- Commits ec327a1 and 9a0012a exist in git log

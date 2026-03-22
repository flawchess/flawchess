---
phase: 23-launch-readiness
plan: 02
subsystem: backend-import-pipeline
tags: [rate-limiting, concurrency, timeout, api]
dependency_graph:
  requires: []
  provides: [STAB-01]
  affects: [import-service, chesscom-client, lichess-client, imports-router]
tech_stack:
  added: []
  patterns: [asyncio.Semaphore lazy-init, asyncio.timeout, TimeoutError-before-Exception ordering]
key_files:
  created:
    - app/core/rate_limiters.py
  modified:
    - app/services/chesscom_client.py
    - app/services/lichess_client.py
    - app/services/import_service.py
    - app/schemas/imports.py
    - app/routers/imports.py
    - frontend/src/types/api.ts
decisions:
  - "Semaphore lazy-init at call time (not module load) avoids asyncio event loop not started error (Python 3.10+)"
  - "Lichess semaphore held for entire stream duration — one connection per job, so semaphore limits connections not requests"
  - "TimeoutError caught before Exception — in Python 3.11+ TimeoutError is BaseException subclass of Exception, ordering matters"
  - "other_importers=0 for DB fallback jobs (completed/failed) — count irrelevant for non-active jobs"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_modified: 7
---

# Phase 23 Plan 02: Import Rate Limiting and Timeout Summary

Shared per-platform semaphores, 3-hour import timeout, and concurrent importer count added to the backend import pipeline.

## What Was Built

**Task 1 — Rate limiter module + platform client integration**

Created `app/core/rate_limiters.py` with lazy-initialized module-level `asyncio.Semaphore` instances:
- `CHESSCOM_SEMAPHORE_LIMIT = 2` — limits concurrent archive fetches across all users
- `LICHESS_SEMAPHORE_LIMIT = 3` — limits concurrent lichess streaming connections

Integrated into platform clients:
- `chesscom_client.py`: semaphore wraps the sleep + HTTP request + retry block per archive URL
- `lichess_client.py`: semaphore wraps entire `client.stream()` context manager (held for full stream)

**Task 2 — Timeout, concurrent count, API field**

- `run_import()` wrapped with `asyncio.timeout(IMPORT_TIMEOUT_SECONDS)` (3 hours)
- `TimeoutError` caught before `except Exception` to prevent swallowing (Python 3.11+ ordering)
- On timeout: job marked FAILED with message "Import timed out — re-sync to continue where it left off"
- New function `count_active_platform_jobs(platform, exclude_user_id)` counts active jobs from other users
- `ImportStatusResponse` schema gains `other_importers: int = 0`
- Both `get_import_status()` and `get_active_imports()` populate `other_importers` from in-memory registry
- Frontend `ImportStatusResponse` interface updated with `other_importers: number`

## Deviations from Plan

None — plan executed exactly as written.

## Verification

All 57 tests pass:
- `tests/test_chesscom_client.py` — 17 tests
- `tests/test_lichess_client.py` — 9 tests
- `tests/test_import_service.py` — 21 tests
- `tests/test_imports_router.py` — 10 tests

## Known Stubs

None.

## Self-Check: PASSED

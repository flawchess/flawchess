---
phase: 02-import-pipeline
plan: "03"
subsystem: api
tags: [fastapi, asyncio, chess.com, lichess, zobrist, postgresql, sqlalchemy, httpx, pydantic]

# Dependency graph
requires:
  - phase: 02-import-pipeline/02-01
    provides: "DB models, schemas, game_repository, import_job_repository"
  - phase: 02-import-pipeline/02-02
    provides: "fetch_chesscom_games, fetch_lichess_games async iterators"
  - phase: 01-data-foundation
    provides: "hashes_for_game Zobrist hash function"
provides:
  - "POST /imports — non-blocking import trigger returning job_id immediately"
  - "GET /imports/{job_id} — live progress polling with games_fetched/games_imported"
  - "Background import orchestrator via asyncio.create_task"
  - "In-memory job registry with duplicate import prevention"
  - "Incremental sync via last_synced_at from previous completed jobs"
  - "Zobrist hash computation and bulk position storage for every imported game"
affects: [03-analysis-api, 04-frontend-auth]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "In-memory job registry (module-level dict) for live job state, DB as historical fallback"
    - "asyncio.create_task fires background import without blocking HTTP response"
    - "Async generator iteration with batch flushing (batch size 50)"
    - "Failure isolation: background tasks catch all exceptions, job always reaches terminal state"

key-files:
  created:
    - app/services/import_service.py
    - app/routers/imports.py
    - tests/test_import_service.py
    - tests/test_imports_router.py
  modified:
    - app/main.py

key-decisions:
  - "Hardcoded user_id=1 in POST /imports with TODO comment — auth wired in Phase 4 with FastAPI-Users"
  - "In-memory registry is source of truth for live jobs; DB queried only as fallback for historical jobs"
  - "Failure state persisted to DB in a separate session to survive the main session rollback"
  - "SELECT query to match new game IDs to PGNs after bulk_insert_games (not pre-matched by array index) for correctness"

patterns-established:
  - "Router: HTTP layer only, delegates all logic to import_service"
  - "Service: orchestration logic, no SQL — delegates to repositories"
  - "Repository: DB access only — no business logic"

requirements-completed: [IMP-01, IMP-02, IMP-03, IMP-04, INFRA-02]

# Metrics
duration: 3min
completed: 2026-03-11
---

# Phase 2 Plan 3: Import Service and API Router Summary

**Non-blocking import pipeline via asyncio.create_task: POST /imports returns job_id immediately while background job fetches games, computes Zobrist hashes, and bulk inserts positions**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-11T13:38:49Z
- **Completed:** 2026-03-11T13:42:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Import service with in-memory job registry (create_job, get_job, find_active_job) and background orchestrator (run_import)
- POST /imports returns 201 immediately with job_id; duplicate check returns existing active job with 200
- GET /imports/{job_id} returns live progress from memory, falls back to DB for historical jobs
- Incremental sync: reads last_synced_at from previous completed job, passes since_timestamp (chess.com) or since_ms (lichess)
- Batch flushing (50 games): bulk_insert_games -> SELECT PGNs -> hashes_for_game -> bulk_insert_positions
- 28 total tests (18 service + 10 router) — all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Import service with job registry and background orchestrator** - `0e68bd5` (feat)
2. **Task 2: Import router endpoints and FastAPI wiring** - `471afaf` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/services/import_service.py` — JobState dataclass, JobStatus enum, _jobs registry, create_job/get_job/find_active_job, run_import background orchestrator, _flush_batch helper
- `app/routers/imports.py` — POST /imports and GET /imports/{job_id} endpoints, imports router
- `app/main.py` — Added `app.include_router(imports.router)`
- `tests/test_import_service.py` — 18 unit tests for job lifecycle, orchestration, incremental sync, error handling
- `tests/test_imports_router.py` — 10 integration tests using httpx ASGITransport

## Decisions Made
- **user_id=1 hardcoded**: Phase 4 adds FastAPI-Users auth; TODO comment marks the placeholder.
- **In-memory + DB duality**: In-memory registry gives zero-latency live updates; DB fallback covers restarts and historical lookups.
- **Failure DB persistence in separate session**: The primary session may have failed; a fresh session captures the error state independently.
- **PGN lookup via SELECT after bulk_insert**: Rather than assuming batch index alignment with returned IDs, we SELECT the actual (id, pgn) pairs for newly inserted games — correct even when duplicates cause gaps in the returned ID list.

## Deviations from Plan

None - plan executed exactly as written. The SELECT-based PGN lookup (vs. index-based) was an implementation detail not specified in the plan but is architecturally correct given how bulk_insert_games works with ON CONFLICT DO NOTHING.

## Issues Encountered
- Unused imports (`asyncio`, `dataclasses.field`) introduced during initial coding — cleaned up immediately via ruff before the commit. Pre-existing ruff F821 errors in `app/models/game.py` and `app/models/game_position.py` are out of scope.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full import pipeline is operational end-to-end: trigger import -> background fetch -> hash compute -> DB persist -> poll progress
- Phase 3 (Analysis API) can query `game_positions` table using Zobrist hashes computed during import
- Phase 4 (Frontend + Auth) needs to replace hardcoded `user_id=1` with real FastAPI-Users auth context

## Self-Check: PASSED

All files verified present:
- FOUND: app/services/import_service.py
- FOUND: app/routers/imports.py
- FOUND: tests/test_import_service.py
- FOUND: tests/test_imports_router.py
- FOUND: 02-03-SUMMARY.md

All commits verified:
- FOUND: 0e68bd5 (feat: import service with job registry and background orchestrator)
- FOUND: 471afaf (feat: import router endpoints and FastAPI wiring)

---
*Phase: 02-import-pipeline*
*Completed: 2026-03-11*

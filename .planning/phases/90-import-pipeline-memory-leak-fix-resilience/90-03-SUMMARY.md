---
phase: 90-import-pipeline-memory-leak-fix-resilience
plan: 03
subsystem: api
tags: [resilience, background-task, asyncio, sqlalchemy, reaper, retry, sentry, postgresql]

requires:
  - phase: 90-import-pipeline-memory-leak-fix-resilience/90-01
    provides: Stage 5 executemany rewrite (same file, parallel wave)

provides:
  - Periodic orphan-job reaper (run_periodic_reaper, every 5 min with 3h age threshold)
  - Bounded failure-state retry helper (_record_failure_with_retry, 5 attempts, 2/4/8/16/30s)
  - fail_orphaned_jobs extended with optional orphan_age_threshold parameter
  - Lifespan-wired reaper task in app/main.py with clean cancel-and-await on shutdown

affects:
  - import-pipeline
  - ops-runbooks

tech-stack:
  added: []
  patterns:
    - "Periodic background task via asyncio.create_task + while-True sleep loop wired in FastAPI lifespan"
    - "Bounded retry with exponential backoff mirroring lichess_client.py (for-loop, no tenacity)"
    - "Sentry capture once on final retry exhaustion (CLAUDE.md last-attempt-only rule)"
    - "Age-threshold filter on bulk UPDATE via Python-computed cutoff bound as parameter (not NOW() SQL func)"

key-files:
  created: []
  modified:
    - app/repositories/import_job_repository.py
    - app/services/import_service.py
    - app/main.py
    - tests/test_import_service.py

key-decisions:
  - "Catch sqlalchemy.exc.OperationalError (not raw asyncpg types) — Assumption A3: SQLAlchemy wraps asyncpg connection errors in OperationalError, confirmed by code inspection and pitfall analysis in 90-RESEARCH.md"
  - "Sleep-before-first-cleanup in run_periodic_reaper so startup cleanup_orphaned_jobs() handles T=0"
  - "orphan_age_threshold defaults to None (no threshold) to preserve startup semantics; periodic caller passes timedelta(seconds=IMPORT_TIMEOUT_SECONDS)"
  - "No shared _DB_TRANSIENT_ERRORS constant for Phase 90 scope — duplicate per research open question 1, refactor later"

requirements-completed: []

duration: 30min
completed: 2026-05-20
---

# Phase 90 Plan 03: Periodic Reaper + Failure-State Retry Summary

**Periodic orphan-job reaper (5 min interval, 3h age threshold) and bounded failure-state UPDATE retry (5 attempts, ~60s budget) so a Postgres-only restart never strands import jobs in in_progress indefinitely**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-20T16:20:00Z
- **Completed:** 2026-05-20T16:50:29Z
- **Tasks:** 2 (TDD: Wave 0 scaffold + implementation)
- **Files modified:** 4

## Accomplishments

- Extended `fail_orphaned_jobs` with optional `orphan_age_threshold: timedelta | None = None`; when provided, only reaps jobs with `started_at < NOW() - threshold`, preventing the periodic reaper from killing live healthy imports (Pitfall 3 fix)
- Added `run_periodic_reaper` coroutine that sleeps first then calls `cleanup_orphaned_jobs(orphan_age_threshold=timedelta(seconds=IMPORT_TIMEOUT_SECONDS))` every 5 min; catches all exceptions, Sentry-captures, and continues without crashing the task
- Added `_record_failure_with_retry` helper that wraps the job failure-state UPDATE in a 5-attempt loop with 2/4/8/16/30s exponential backoff on `OperationalError`; Sentry-captures only on final exhaustion per CLAUDE.md; non-transient errors fail fast
- Replaced both `except TimeoutError` and `except Exception` inline try/except blocks in `run_import` with single `_record_failure_with_retry` calls, eliminating duplicated retry logic
- Wired reaper task in `app/main.py` lifespan with `asyncio.create_task` on startup and clean `cancel + await + swallow CancelledError` on shutdown
- All 10 new tests pass (3 DB-backed age-threshold tests, 3 mocked reaper tests, 4 mocked retry tests); ruff + ty clean

## Task Commits

1. **Task 1: Wave 0 — scaffold three test classes (xfail)** - `2c4b2663` (test)
2. **Task 2: Implement + wire all components, flip xfail markers** - `99527235` (feat)

## Files Created/Modified

- `app/repositories/import_job_repository.py` - Extended `fail_orphaned_jobs` with `orphan_age_threshold: timedelta | None = None` parameter and age-filter WHERE clause
- `app/services/import_service.py` - Added 4 module constants, extended `cleanup_orphaned_jobs`, added `run_periodic_reaper` and `_record_failure_with_retry`, replaced inline try/except in `run_import` exception branches; added `timedelta` and `OperationalError` imports
- `app/main.py` - Added `import asyncio`, imported `run_periodic_reaper`, wired reaper task in lifespan with cancel-and-await on shutdown
- `tests/test_import_service.py` - Added 10 new tests across `TestFailOrphanedJobsAgeThreshold`, `TestPeriodicReaper`, `TestRecordFailureWithRetry`

## Decisions Made

- **Assumption A3 (catch class):** Caught `sqlalchemy.exc.OperationalError` rather than raw asyncpg types. SQLAlchemy wraps `CannotConnectNowError`/`ConnectionDoesNotExistError` in `OperationalError`, so catching `OperationalError` is both simpler and correct (mirrors the finding in `app/main.py:_sentry_before_send` which walks `__cause__` for the same types). Documented in the test file comment block above the three new classes.
- **Sleep-first ordering in reaper:** `run_periodic_reaper` sleeps before the first cleanup call so the startup `await cleanup_orphaned_jobs()` in `lifespan` handles T=0 and the reaper handles T+5min, T+10min, etc. This avoids double-reaping at startup.
- **Backoff schedule:** 2/4/8/16/30s (capped) = ~60s total budget. The 2026-05-16 Postgres crash-recovery window was ~2s (per debug note), so this is generous.
- **No tenacity:** hand-rolled loop mirroring `lichess_client.py:_retry_loop` per research recommendation — one new dependency avoided.

## Deviations from Plan

None - plan executed exactly as written.

## Assumption Verification Results

### A1 (asyncio.create_task + sleep loop)
VERIFIED: Plain `asyncio.create_task` + `while True: await asyncio.sleep(N)` works as expected in the lifespan context. Three `TestPeriodicReaper` tests (interval, threshold, survive-exception) all pass, confirming the pattern works under monkeypatching and coroutine cancellation.

### A3 (OperationalError is correct catch class)
VERIFIED by code inspection and research: SQLAlchemy wraps asyncpg connection exceptions in `sqlalchemy.exc.OperationalError` (which is a subclass of `DBAPIError`). `TestRecordFailureWithRetry::test_retries_on_operational_error_then_succeeds` confirms the retry loop fires on `OperationalError`. Documented in the test file comment block preceding the three new classes.

## Issues Encountered

One minor issue: `# ty: ignore[unknown-argument]` placement — ty reports the error on the kwarg line, not on the `await` call line. Fixed by placing the suppression on the specific argument line. All ty suppressions were removed in Task 2 once the implementation provided the real signatures.

## Manual Verification (deferred to phase-level gate)

Per 90-VALIDATION.md "Manual-Only Verifications": the scenario where Postgres is killed mid-import (backend survives) must be verified manually:

```bash
# While a large import is running:
docker compose -f docker-compose.dev.yml -p flawchess-dev kill postgres
# Wait ~2 seconds
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d postgres

# Expected outcomes:
# (a) If import is still alive: _record_failure_with_retry rides out recovery window
#     and records the failed status (~2s delay, within ~60s budget)
# (b) If import died with backend: within 5 min after backend recovery,
#     run_periodic_reaper marks orphaned job failed (3h threshold not reached)
```

## Next Phase Readiness

- Plan 90-03 complete — resilience defects from SEED-017 are fixed
- Plans 90-01 (Stage 5 executemany rewrite) and 90-03 (resilience) run in Wave 2 in parallel
- Plan 90-02 (session-recycle restructure) is the remaining Wave 2 plan
- Phase gate: full test suite + manual RSS observation on 5k+ game import

---
*Phase: 90-import-pipeline-memory-leak-fix-resilience*
*Completed: 2026-05-20*

## Self-Check: PASSED

**Files verified:**
- `app/repositories/import_job_repository.py` — FOUND (orphan_age_threshold parameter confirmed)
- `app/services/import_service.py` — FOUND (run_periodic_reaper, _record_failure_with_retry, 4 constants confirmed)
- `app/main.py` — FOUND (asyncio.create_task(run_periodic_reaper(), reaper_task.cancel() confirmed)
- `tests/test_import_service.py` — FOUND (47 tests, 10 new, all passing)

**Commits verified:**
- `2c4b2663` — test(90-03): Wave 0 scaffold — FOUND
- `99527235` — feat(90-03): periodic reaper + retry helper + lifespan wiring — FOUND

---
phase: 149-retire-prune
plan: 05
subsystem: api
tags: [postgres, alembic, sqlalchemy, fastapi, partial-unique-index, concurrency]

# Dependency graph
requires:
  - phase: 149-01
    provides: worker_heartbeats migration (established the current alembic head this plan chains from)
provides:
  - Partial unique index uq_import_jobs_user_platform_active on import_jobs(user_id, platform) WHERE status IN ('pending', 'in_progress')
  - Durable import_jobs row creation moved from the background task into the request handler
  - get_active_job_for_user_platform repository query
  - discard_job in-memory registry cleanup helper
affects: [150-consolidate-write-path]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "IntegrityError-as-idempotency (existing guest_service.py precedent) applied to import-job concurrency guard"
    - "Partial unique index via Index(..., postgresql_where=...) declared in __table_args__ for autogenerate parity, DDL owned by a dedicated migration"

key-files:
  created:
    - alembic/versions/20260704_123013_12d3df9c5373_import_jobs_partial_unique_index.py
  modified:
    - app/models/import_job.py
    - app/repositories/import_job_repository.py
    - app/routers/imports.py
    - app/services/import_service.py
    - tests/test_import_service.py
    - tests/test_imports_router.py
    - tests/test_game_repository.py

key-decisions:
  - "Durable import_jobs INSERT moved from _bootstrap_import_job (background task, runs after the HTTP response) into start_import (before asyncio.create_task) — closes the actual TOCTOU race, per RESEARCH Pitfall 3"
  - "IntegrityError from the partial unique index is caught, rolled back, and returns the existing active job with 200 — never capture_exception'd (expected race, not a bug)"
  - "Added discard_job() to remove the losing request's orphaned in-memory JobState — otherwise it would linger as a permanently-stuck duplicate in find_active_jobs_for_user/count_active_platform_jobs (Rule 1 auto-fix, not in the original plan text)"

requirements-completed: [PRUNE-05]

coverage:
  - id: D1
    description: "Partial unique index uq_import_jobs_user_platform_active enforced at the DB level; migration is reversible and chains as a single alembic head"
    requirement: "PRUNE-05"
    verification:
      - kind: unit
        ref: "tests/test_import_service.py::TestImportJobsPartialUniqueIndex#test_second_active_insert_for_same_user_platform_raises_integrity_error"
        status: pass
      - kind: unit
        ref: "tests/test_import_service.py::TestImportJobsPartialUniqueIndex#test_completed_job_does_not_block_reimport"
        status: pass
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic heads (single head)"
        status: pass
    human_judgment: false
  - id: D2
    description: "get_active_job_for_user_platform re-fetch is scoped by user_id + platform — no cross-user job leak (ASVS V4 / IDOR)"
    requirement: "PRUNE-05"
    verification:
      - kind: unit
        ref: "tests/test_import_service.py::TestImportJobsPartialUniqueIndex#test_get_active_job_for_user_platform_scoped_to_requesting_user"
        status: pass
    human_judgment: false
  - id: D3
    description: "A concurrent duplicate start_import request is caught via IntegrityError and returns the existing active job with HTTP 200 (dedup contract preserved, never 409)"
    requirement: "PRUNE-05"
    verification:
      - kind: integration
        ref: "tests/test_imports_router.py::TestPostImports#test_concurrent_duplicate_import_returns_existing_job_with_200"
        status: pass
    human_judgment: false
  - id: D4
    description: "_bootstrap_import_job no longer creates the import_jobs row (moved to start_import); previous-job lookup for the incremental-sync cursor is retained"
    requirement: "PRUNE-05"
    verification:
      - kind: unit
        ref: "tests/test_import_service.py::TestRunImport (full class, exercises run_import/_bootstrap_import_job end to end)"
        status: pass
      - kind: other
        ref: "grep -c create_import_job app/services/import_service.py == 0"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-04
status: complete
---

# Phase 149 Plan 5: Durable Import-Job Concurrency Guard Summary

**Moved the import_jobs row INSERT from the fire-and-forget background task into the start_import request handler, backed by a new Postgres partial unique index on (user_id, platform), closing the TOCTOU race where two concurrent imports could both pass the in-memory duplicate check.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-04T12:27:55Z
- **Completed:** 2026-07-04T12:48:37Z
- **Tasks:** 2
- **Files modified:** 7 (1 new migration, 6 modified)

## Accomplishments
- New Alembic migration creates `uq_import_jobs_user_platform_active` on `import_jobs(user_id, platform) WHERE status IN ('pending', 'in_progress')`, reversible up/down, chained as the single alembic head after Wave-1's `worker_heartbeats` migration.
- `ImportJob.__table_args__` declares the same index for autogenerate parity (confirmed a no-op diff against the migration).
- New `get_active_job_for_user_platform` repository query with a predicate textually identical to the index (drift-prevention).
- `start_import` now creates the durable `import_jobs` row synchronously, before `asyncio.create_task`, inside a `try/except IntegrityError` that rolls back, discards the orphaned in-memory job, and returns the winning job with HTTP 200 (scoped by user_id + platform — no cross-user leak).
- `_bootstrap_import_job` no longer creates the row — the DB insert lives in exactly one place now.

## Task Commits

Each task was committed atomically (Task 2 followed the TDD RED/GREEN gate sequence, plus two test-collision fixups discovered while running the full suite):

1. **Task 1: Partial unique index migration + get_active_job_for_user_platform query** - `6e2aaca5` (feat)
2. **Task 1 fallout fix: reaper age-threshold test fixtures** - `ebb8a85e` (fix) — collision with the new index, unrelated to Task 2's behavior
3. **Task 2 RED: failing race tests** - `59e2f6cc` (test)
4. **Task 2 GREEN: move the durable INSERT into start_import** - `90a41048` (feat)
5. **Task 2 fallout fix: serialize test_get_latest_for_user_platform's seeded jobs** - `576b3d8e` (fix)

_Note: Task 2 (tdd="true") followed test → feat; no refactor commit was needed._

## Files Created/Modified
- `alembic/versions/20260704_123013_12d3df9c5373_import_jobs_partial_unique_index.py` - New reversible migration for the partial unique index
- `app/models/import_job.py` - `__table_args__` declares the index for model/DB parity
- `app/repositories/import_job_repository.py` - New `get_active_job_for_user_platform`
- `app/routers/imports.py` - `start_import` creates the durable row + IntegrityError idempotency handler
- `app/services/import_service.py` - `_bootstrap_import_job` no longer inserts the row; new `discard_job` helper
- `tests/test_import_service.py` - New `TestImportJobsPartialUniqueIndex` class; fixed two pre-existing tests that seeded colliding active rows
- `tests/test_imports_router.py` - New race regression test + DB-row cleanup fixture (module-scoped `auth_headers` now shares real durable rows across tests)
- `tests/test_game_repository.py` - Fixed a pre-existing test that seeded two simultaneously-pending rows for the same user+platform

## Decisions Made
- Durable row creation moved into `start_import`, not merely reordered around an existing call (RESEARCH Pitfall 3: `_bootstrap_import_job`, not `create_job`, was the actual pre-existing DB call site).
- IntegrityError is never `capture_exception`'d — it's the expected race path, matching `guest_service.py`'s existing Google-promotion double-submit precedent (CLAUDE.md skip-trivial-exceptions rule).
- Added `discard_job()` (Rule 1 auto-fix, not in the original plan text): without it, a losing concurrent request's in-memory `JobState` would never get scheduled via `asyncio.create_task` yet would remain in the `_jobs` registry forever, showing up as a permanently-stuck duplicate import in `find_active_jobs_for_user` / `count_active_platform_jobs`.
- The `existing_row is not None` re-fetch guard uses an `assert` (mirroring `guest_service.py`'s own `assert updated is not None` pattern) rather than a defensive 409, since the plan explicitly prohibits returning 409 on the routine duplicate-race path; the assert only fires in the astronomically rare case where the winning job resolved to a terminal state between the IntegrityError and the re-fetch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two pre-existing tests seeded colliding active import_jobs rows**
- **Found during:** Running the full backend suite after Task 1's migration landed
- **Issue:** `TestFailOrphanedJobsAgeThreshold` (test_import_service.py) and `TestImportJobRepository::test_get_latest_for_user_platform` (test_game_repository.py) each seeded two simultaneously-"pending"/"in_progress" `ImportJob` rows for the same `(user_id, platform)` — a scenario the new partial unique index makes structurally impossible going forward, and which is orthogonal to what those tests actually exercise (reaper age-threshold filtering; "latest completed job" lookup).
- **Fix:** Gave the reaper test's seed helper a `platform` parameter and used two different platforms for its two rows; serialized the repository test so job 1 is transitioned to "completed" before job 2 is created.
- **Files modified:** `tests/test_import_service.py`, `tests/test_game_repository.py`
- **Verification:** Both test files pass individually and as part of the full suite.
- **Committed in:** `ebb8a85e`, `576b3d8e`

**2. [Rule 1 - Bug] Module-scoped `auth_headers` fixture leaked durable import_jobs rows across router tests**
- **Found during:** Task 2 GREEN verification (`tests/test_imports_router.py`)
- **Issue:** `auth_headers` registers one real user per test module and is shared across `TestPostImports`/`TestGetImportStatus`. Before this plan, `POST /imports` never durably wrote to the DB in these tests (the no-op'd background task owned that insert), so the shared user's `import_jobs` rows never accumulated. Now that `start_import` writes the row synchronously, a leftover "pending" row from an earlier test collided with `uq_import_jobs_user_platform_active` on the next same-platform POST for the same shared user.
- **Fix:** Added an autouse async fixture (`clear_import_job_rows`) that deletes all `ImportJob` rows before/after each test in the module, complementing the existing in-memory `clear_jobs` fixture.
- **Files modified:** `tests/test_imports_router.py`
- **Verification:** All 71 pre-existing + 1 new test in the file pass.
- **Committed in:** `90a41048`

**3. [Rule 1 - Bug] Orphaned in-memory JobState on the losing side of a race**
- **Found during:** Task 2 implementation (writing the IntegrityError handler)
- **Issue:** The plan's target code shape registers the in-memory `JobState` via `create_job()` before attempting the durable insert. If that insert loses the race, the plan's shape as written would leave that `JobState` in `_jobs` forever (never scheduled, never progressing) — polluting `find_active_jobs_for_user`/`count_active_platform_jobs` for that user.
- **Fix:** Added `import_service.discard_job(job_id)`, called from the IntegrityError branch, to pop the orphaned entry.
- **Files modified:** `app/services/import_service.py`, `app/routers/imports.py`
- **Verification:** Covered indirectly by the new race test (job_id in the response is the winner's, not a stray extra entry); no dedicated unit test for `discard_job` itself (it's a one-line `dict.pop`).
- **Committed in:** `90a41048`

---

**Total deviations:** 3 auto-fixed (2 Rule 1 pre-existing test collisions caused by the new DB constraint, 1 Rule 1 correctness gap in the plan's own target shape)
**Impact on plan:** All three were necessary for correctness or full-suite greenness. No scope creep — no behavior outside PRUNE-05's stated scope was touched.

## Issues Encountered
- The TDD RED/GREEN split required temporarily stashing the already-drafted implementation to genuinely observe the router-level race test fail against the pre-existing code, then popping the stash back for GREEN. No lasting issue — documented here for audit-trail transparency since the commit sequence (test-only, then feat) reflects a real fail-first verification, not just a labeling convention.
- `create_import_job`'s `session.flush()` raises `IntegrityError` immediately (not deferred to `session.commit()`), which the repository-level regression test initially got wrong; fixed by wrapping the second insert in `db_session.begin_nested()` (a SAVEPOINT) so only the failing insert unwinds, leaving the first insert visible within the same test transaction.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PRUNE-05 complete. Phase 150 (Consolidate Write Path) can proceed — no further import-job concurrency work outstanding.
- Full backend suite green: 3162 passed, 18 skipped.
- `uv run ty check app/ tests/`: zero errors.
- `uv run alembic upgrade head && downgrade -1 && upgrade head`: reversible; `uv run alembic heads` reports exactly one head.

---
*Phase: 149-retire-prune*
*Completed: 2026-07-04*

## Self-Check: PASSED

All created/modified files exist on disk; all 5 task/fixup commit hashes (6e2aaca5, ebb8a85e, 59e2f6cc, 90a41048, 576b3d8e) verified present in `git log --oneline --all`.

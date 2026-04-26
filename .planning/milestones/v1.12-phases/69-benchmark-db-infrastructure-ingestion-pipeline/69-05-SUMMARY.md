---
phase: 69
plan: "05"
subsystem: benchmark-ingestion
tags: [benchmark, ingestion, orchestrator, lichess, checkpoint, tdd]
dependency_graph:
  requires: [69-04]
  provides: [scripts/import_benchmark_users.py, app/models/benchmark_ingest_checkpoint.py]
  affects: [benchmark_ingest_checkpoints table, users table (stub rows), import_jobs table (synthetic rows)]
tech_stack:
  added: []
  patterns:
    - "Synthetic import_jobs pre-seeding to control since_ms via existing run_import pipeline"
    - "SIGINT-safe outer-loop checkpoint with terminal status resume"
    - "Stub User row pattern (is_active=False, non-bcrypt sentinel password) for benchmark auth isolation"
key_files:
  created:
    - app/models/benchmark_ingest_checkpoint.py
    - scripts/import_benchmark_users.py
  modified:
    - tests/test_benchmark_ingest.py
decisions:
  - "Moved argparse before safety check so --help works without triggering DB URL validation"
  - "Computed 36-month window offset without dateutil (not in project deps); pure datetime arithmetic"
  - "Removed unused since_ms local variable -- window_start passed directly to ImportJob.last_synced_at"
metrics:
  duration_minutes: 6
  completed_date: "2026-04-26"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 69 Plan 05: Benchmark User Ingestion Orchestrator Summary

Benchmark ingestion orchestrator with per-user outer-loop checkpointing, idempotent stub User creation, synthetic import_jobs pre-seeding for 36-month window control, SIGINT-safe shutdown, 20k outlier hard-skip, and DATABASE_URL safety check.

## Tasks Completed

| Task | Type | Commit | Description |
|------|------|--------|-------------|
| 05-01 | TDD RED | 6f8aca3 | BenchmarkIngestCheckpoint ORM + 3 failing tests |
| 05-02 | TDD GREEN | d52de73 | scripts/import_benchmark_users.py -- 9/9 tests pass |

## Artifacts Produced

### `app/models/benchmark_ingest_checkpoint.py`

ORM for `benchmark_ingest_checkpoints` table. Status lifecycle: `pending` -> `completed` | `skipped` | `failed`. Benchmark-only table created via `Base.metadata.create_all()` (not Alembic). FK to `users.id` with `ondelete="SET NULL"` so user deletion preserves audit rows.

### `scripts/import_benchmark_users.py`

Ingestion orchestrator. Key public API:

- `create_stub_user(session, lichess_username) -> int` -- async, idempotent
- `_should_hard_skip(games_count: int) -> bool` -- pure, threshold = 20,000 (D-14)
- `compute_deficit_users(pool, completed, target_n) -> list[str]` -- pure, returns next deficit usernames in pool order

Orchestration flow per user:

1. Insert/update checkpoint row to `status='pending'`
2. `create_stub_user` (idempotent -- returns existing id if already created)
3. Insert synthetic `ImportJob` row with `last_synced_at = snapshot_month_end - 36 months` (D-13) so `run_import` derives `since_ms` correctly via `get_latest_for_user_platform`
4. `create_job` + `await run_import(job_id)` (sequential, no asyncio.gather)
5. Inspect `get_job(job_id).games_imported`: if >= 20,000 -> `status='skipped'`, else `status='completed'` or `'failed'`
6. Sentry `set_context` + `capture_exception` at outer-per-user boundary only

Safety: startup refuses DATABASE_URL not containing `5433` and `flawchess_benchmark`.

SIGINT: sets `_stop_requested` flag; loop checks between users; current user completes before exit.

## Verification Results

```
uv run pytest tests/test_benchmark_ingest.py   -> 9/9 PASSED
uv run python scripts/import_benchmark_users.py --help  -> exit 0
uv run ty check app/ tests/   -> All checks passed!
uv run ruff check .   -> All checks passed!
uv run python -c "import scripts.import_benchmark_users"  -> exit 0
```

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | 6f8aca3 | Confirmed -- 3 new tests failed with ModuleNotFoundError |
| GREEN (feat commit) | d52de73 | Confirmed -- 9/9 tests pass |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `dateutil` not available in project deps**

- **Found during:** Task 05-02 implementation
- **Issue:** Plan suggested using `relativedelta` from `python-dateutil` to subtract 36 months. `python-dateutil` is not in the project's uv lock file.
- **Fix:** Replaced with pure datetime arithmetic: subtract `WINDOW_MONTHS // 12` years and `WINDOW_MONTHS % 12` months, rolling over year if month goes non-positive.
- **Files modified:** scripts/import_benchmark_users.py
- **Commit:** d52de73

**2. [Rule 1 - Bug] `--help` blocked by DATABASE_URL safety check**

- **Found during:** Task 05-02 verification
- **Issue:** Safety check ran before argparse, so `--help` raised `RuntimeError` instead of printing usage.
- **Fix:** Moved `parse_args()` call before the safety check in `main()`. `argparse` calls `sys.exit(0)` on `--help`, so the safety check is never reached.
- **Files modified:** scripts/import_benchmark_users.py
- **Commit:** d52de73

**3. [Rule 1 - Bug] ty errors in test file from `MagicMock` typed as `object`**

- **Found during:** Task 05-02 `ty check` verification
- **Issue:** `added_user: dict[str, object]` typed the captured mock as `object`, causing unresolved-attribute errors on `.email`, `.lichess_username`, etc.
- **Fix:** Changed type to `dict[str, User]` and `_capture` parameter to `User`. Removed `# type: ignore` comments (not ty syntax); the ty-valid pattern does not need any suppression.
- **Files modified:** tests/test_benchmark_ingest.py
- **Commit:** d52de73

## Threat Surface Scan

No new network endpoints or auth paths introduced. The script creates stub `User` rows in the benchmark DB only; the safety check (`5433` + `flawchess_benchmark` in DATABASE_URL) mitigates T-69-01. All three threat mitigations from the plan's STRIDE register are implemented:

| Threat | Mitigation Applied |
|--------|--------------------|
| T-69-01 (wrong DB) | Startup safety check implemented |
| T-69-stub (stub auth) | is_active=False, STUB_PASSWORD not a valid bcrypt hash |
| T-69-06 (outlier pollution) | _should_hard_skip(>=20_000) -> status='skipped' |

## Self-Check: PASSED

- `app/models/benchmark_ingest_checkpoint.py` -- FOUND
- `scripts/import_benchmark_users.py` -- FOUND
- Commit 6f8aca3 -- FOUND
- Commit d52de73 -- FOUND

---
phase: 90
plan: "02"
subsystem: import-pipeline
tags:
  - sqlalchemy
  - asyncsession
  - session-lifecycle
  - background-task
  - memory-leak
  - bug-fix
dependency_graph:
  requires:
    - "90-01: _flush_batch Stage 5 executemany rewrite (same file)"
  provides:
    - "run_import three-scope session lifecycle (bootstrap / per-batch / completion)"
    - "previous_last_synced_at scalar extraction inside bootstrap scope"
    - "TestRunImportSessionPerBatch Wave 0 unit tests (5 tests)"
  affects:
    - "app/services/import_service.py::run_import"
    - "app/services/import_service.py::_make_game_iterator"
    - "tests/test_import_service.py"
tech_stack:
  added: []
  patterns:
    - "Per-batch AsyncSession scope in background workers (SQLAlchemy 2.x async guidance)"
    - "Scalar extraction inside bootstrap session scope before close (Pitfall 2 mitigation)"
key_files:
  created: []
  modified:
    - path: app/services/import_service.py
      lines: "418-557 (run_import restructure), 560-605 (_make_game_iterator rewrite)"
      description: "Three session scopes; _make_game_iterator accepts scalar instead of ORM instance"
    - path: tests/test_import_service.py
      lines: "2155-2640 (TestRunImportSessionPerBatch, 5 tests)"
      description: "Wave 0 session-lifecycle tests; xfail markers removed after Task 2"
decisions:
  - "Bootstrap session closes before the httpx.AsyncClient and batch loop open — only previous_last_synced_at (datetime | None) crosses the boundary, not the ImportJob ORM instance"
  - "_make_game_iterator parameter renamed from previous_job: Any to previous_last_synced_at: datetime | None — the single previous_job. attribute access (last_synced_at extraction) happens inside the bootstrap scope, not inside _make_game_iterator"
  - "Per-batch session structure: full batch and trailing batch each open their own async_session_maker() scope, eliminating cross-batch identity-map and statement-cache accumulation"
  - "Completion scope uses a fresh session separate from the last batch's session, matching the plan spec"
  - "xfail(strict=True) markers on Tests 2-5 removed after Task 2 flip — all 5 now pass unconditionally"
metrics:
  duration: "~35 minutes"
  completed: "2026-05-20"
  tasks_completed: 2
  files_modified: 2
---

# Phase 90 Plan 02: Session-Recycle Restructure Summary

One-liner: Restructure `run_import`'s single long-lived `AsyncSession` into three distinct scopes (bootstrap / per-batch / completion) to cap identity-map and statement-cache accumulation at one batch's worth of state, closing the secondary accumulation surface alongside the Stage 5 leak fix from Plan 90-01.

## What Was Built

### Task 1 (TDD RED): TestRunImportSessionPerBatch Wave 0 tests

Added `class TestRunImportSessionPerBatch` to `tests/test_import_service.py` (~line 2155):

| Test | Name | Status vs. pre-Task-2 code | Status after Task 2 |
|------|------|---------------------------|---------------------|
| 1 | `test_previous_job_last_synced_at_scalar_survives_close` | PASS | PASS |
| 2 | `test_one_session_per_batch` | XFAIL (strict=True) | PASS |
| 3 | `test_bootstrap_session_closed_before_loop` | XFAIL (strict=True) | PASS |
| 4 | `test_completion_session_separate_from_batch` | XFAIL (strict=True) | PASS |
| 5 | `test_run_import_e2e_smoke` | XFAIL (strict=True) | PASS |

### Task 2 (TDD GREEN): Three-scope session restructure

`app/services/import_service.py` lines 418-557 (`run_import`) and 560-605 (`_make_game_iterator`):

**Bootstrap scope** (replaces lines 418-446):
```python
async with async_session_maker() as bootstrap_session:
    previous_job = await import_job_repository.get_latest_for_user_platform(...)
    previous_last_synced_at: datetime | None = (
        previous_job.last_synced_at if previous_job is not None else None
    )
    await import_job_repository.create_import_job(bootstrap_session, ...)
    await bootstrap_session.commit()
# bootstrap_session closed — only scalar crosses boundary
```

**Per-batch scope** (each full batch and trailing batch):
```python
async with async_session_maker() as session:
    imported = await _flush_batch(session, batch, job.user_id)
    await import_job_repository.update_import_job(session, ..., status="in_progress", ...)
    await session.commit()
```

**Completion scope**:
```python
async with async_session_maker() as session:
    await import_job_repository.update_import_job(session, ..., status="completed", ...)
    await session.commit()
```

**`_make_game_iterator` signature change**:
- Old: `previous_job: Any` — passed ORM instance cross-scope
- New: `previous_last_synced_at: datetime | None` — plain scalar extracted inside bootstrap

## Assumption Verification

### A2 (previous_job.last_synced_at scalar accessible after session close)
VERIFIED: Test 1 (`test_previous_job_last_synced_at_scalar_survives_close`) PASSED before and after Task 2.
The extracted scalar (`previous_last_synced_at`) is accessible after the bootstrap session closes.
The scalar extraction is performed unconditionally inside the bootstrap scope as a defensive measure — regardless of whether SQLAlchemy would lazy-load the attribute (with `expire_on_commit=False`, it would not).

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `app/services/import_service.py` | 416-557 | `run_import` restructured into 3 session scopes |
| `app/services/import_service.py` | 560-605 | `_make_game_iterator` signature: previous_job → previous_last_synced_at |
| `tests/test_import_service.py` | 2155-2640 | Added `TestRunImportSessionPerBatch` (5 tests); xfail markers removed |

## Test Summary

```
uv run pytest tests/test_import_service.py::TestRunImportSessionPerBatch -v
5 passed in 0.15s

uv run pytest tests/test_import_service.py -x -q
52 passed in 0.24s
```

New tests: 5 (all in TestRunImportSessionPerBatch)
xfail-to-pass flips: 4 (Tests 2-5)
Regressions: 0 (all existing TestRunImport + TestIncrementalProgress + TestFlushBatchStage5 + resilience tests pass)

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| `grep -c "async with async_session_maker() as"` ≥ 5 | 6 (bootstrap + 2 per-batch + completion + 2 except-block sessions) |
| `grep -c "previous_last_synced_at"` ≥ 3 | 9 |
| `grep -c "previous_job\."` ≤ 1 | 1 (extraction line only) |
| `_make_game_iterator` uses `previous_last_synced_at: datetime | None` | Confirmed |
| All 5 `TestRunImportSessionPerBatch` tests PASS | Confirmed |
| All existing `TestRunImport` + `TestIncrementalProgress` tests pass | Confirmed |
| `ruff check` exits 0 | Confirmed |
| `ty check` exits 0 | Confirmed |
| `run_import` logic LOC ≤ 200 | ~120 logic LOC (lines 409-557 including comments/blanks) |

## Session Count Verification

For N=30 games at `_BATCH_SIZE=12`:
- 2 full batches (12 + 12) + 1 trailing batch (6) = 3 per-batch sessions
- 1 bootstrap + 1 completion = 2 additional sessions
- **Total: 5 sessions** (pinned by Test 2)

For N=0 games (empty import — no batches):
- 1 bootstrap + 0 per-batch + 1 completion = 2 sessions

## Deviations from Plan

None — plan executed exactly as written.

The only minor implementation decision: Test 5 (`test_run_import_e2e_smoke`) was originally designed around `kwargs` but `_make_game_iterator` is called with positional args. The test was updated to capture `args[2]` (the third positional argument, `previous_last_synced_at`) instead of looking for a keyword argument. The spirit of the test is identical — it verifies the scalar (not the ORM instance) is passed.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access, or schema changes.

The per-batch session restructure is internal to the import worker; the external API surface (POST /imports, GET /imports/{job_id}) is unchanged.

## Task Commits

| Task | Name | Commit | Type |
|------|------|--------|------|
| 1 | Wave 0 — TestRunImportSessionPerBatch scaffold | `fe6897ce` | test |
| 2 | Restructure run_import three session scopes + flip xfail | `86054a67` | feat |

## Self-Check: PASSED

- [x] `app/services/import_service.py` contains `async with async_session_maker() as bootstrap_session:`
- [x] `app/services/import_service.py` contains `previous_last_synced_at: datetime | None`
- [x] `tests/test_import_service.py` contains `class TestRunImportSessionPerBatch`
- [x] Commit `fe6897ce` (Task 1 TDD RED) exists
- [x] Commit `86054a67` (Task 2 TDD GREEN) exists
- [x] 52 tests pass, ruff clean, ty clean

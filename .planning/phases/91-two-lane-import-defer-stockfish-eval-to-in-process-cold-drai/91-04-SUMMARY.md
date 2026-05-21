---
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
plan: "04"
subsystem: backend-api
tags:
  - api
  - endpoint
  - eval-coverage
  - imports
dependency_graph:
  requires:
    - "91-01 (evals_completed_at column and migration)"
  provides:
    - "GET /api/imports/eval-coverage endpoint"
    - "EvalCoverageResponse Pydantic schema"
    - "count_pending_evals repository function"
  affects:
    - "frontend useEvalCoverage hook (91-06)"
tech_stack:
  added: []
  patterns:
    - "Authenticated GET endpoint with session dependency injection"
    - "Per-user COUNT query with IS NULL partial-index predicate"
    - "Pydantic v2 response schema with integer fields"
key_files:
  created:
    - tests/routers/test_imports_eval_coverage.py
    - alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py
  modified:
    - app/schemas/imports.py
    - app/repositories/game_repository.py
    - app/routers/imports.py
    - app/models/game.py
decisions:
  - "D-01 honoured: dedicated GET /imports/eval-coverage endpoint, not an extension of /imports/active"
  - "D-04 honoured: response keys are exactly pending_count, total_count, pct_complete"
  - "Zero-game edge case returns pct_complete=100 to avoid division-by-zero"
  - "Route placed before /{job_id} in imports router to prevent path-parameter shadowing"
  - "Copied Plan 91-01 migration file to this worktree for test DB schema compatibility"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-21"
  tasks_completed: 3
  files_changed: 6
---

# Phase 91 Plan 04: GET /imports/eval-coverage Endpoint Summary

**One-liner:** New `GET /imports/eval-coverage` endpoint returns `{pending_count, total_count, pct_complete}` per authenticated user using `count_pending_evals()` querying `games.evals_completed_at IS NULL`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 4.1 | EvalCoverageResponse schema + count_pending_evals | 7647da90 | app/schemas/imports.py, app/repositories/game_repository.py, app/models/game.py |
| 4.2 | GET /imports/eval-coverage route | bfe4a59a | app/routers/imports.py |
| 4.3 | Integration tests | ee3de97d | tests/routers/test_imports_eval_coverage.py, alembic migration |

## Endpoint Details

**URL:** `GET /api/imports/eval-coverage`

**Response model fields:**
- `pending_count: int` — games with `evals_completed_at IS NULL`
- `total_count: int` — all games for the authenticated user
- `pct_complete: int` — `round(100 * (total - pending) / total)`, or 100 when total is 0

**Route position:** After `GET /imports/active`, before `GET /imports/{job_id}` (line 127 vs 148) — prevents path-parameter shadowing.

## Integration Tests

File: `tests/routers/test_imports_eval_coverage.py`

| Test Function | Line | Coverage |
|---------------|------|----------|
| `test_eval_coverage_requires_auth` | ~107 | T-91-14: unauthenticated returns 401 |
| `test_eval_coverage_zero_games` | ~118 | zero-games user returns pct_complete=100 |
| `test_eval_coverage_all_complete` | ~130 | all evaluated: pending_count=0, pct_complete=100 |
| `test_eval_coverage_partial` | ~148 | PARTIAL_PENDING_COUNT=3, PARTIAL_TOTAL_COUNT=10, PARTIAL_EXPECTED_PCT=70 |
| `test_eval_coverage_scoped_to_user` | ~170 | T-91-15: User A's pending count not visible to User B |

## Deviations from Plan

### Migration File Copied from Plan 91-01

- **Found during:** Task 4.3 (running tests)
- **Issue:** Plan 91-01 runs in parallel Wave 1 and adds the `evals_completed_at` migration. When this plan's tests run, the test DB already has the column (applied by 91-01's worktree), but alembic in this worktree could not find the revision `bd54be3a66bf`. This broke pytest's `alembic upgrade head` in conftest.
- **Fix:** Copied `20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py` from Plan 91-01's worktree into this worktree's `alembic/versions/`. This is the same file that 91-01 committed — when the two worktrees are merged, it will appear once (identical files merge cleanly).
- **Files modified:** `alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py`
- **Commit:** ee3de97d

### Game.evals_completed_at Added to Model

- **Found during:** Task 4.1 (ty check would fail without it)
- **Issue:** `count_pending_evals` references `Game.evals_completed_at.is_(None)` which requires the ORM column to exist. Plan 91-01 adds this in parallel, but this worktree's tests need it immediately.
- **Fix:** Added `evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)` to `app/models/game.py`. This is the same change Plan 91-01 makes — merge will be clean.
- **Files modified:** `app/models/game.py`
- **Commit:** 7647da90

## Known Stubs

None. The endpoint queries real DB data. Tests use committed sessions with real game rows.

## Threat Flags

None. All threat surfaces are covered by the plan's threat model:
- T-91-14 (unauthenticated access): mitigated via `current_active_user` dependency
- T-91-15 (cross-user disclosure): mitigated via `WHERE user_id = :uid` in both COUNT queries

## Self-Check: PASSED

Files verified:
- `app/schemas/imports.py`: `EvalCoverageResponse` class present
- `app/repositories/game_repository.py`: `count_pending_evals` function present
- `app/routers/imports.py`: `/eval-coverage` route registered before `/{job_id}`
- `tests/routers/test_imports_eval_coverage.py`: 5 tests, all passing

Commits verified:
- 7647da90 (schema + repo + model)
- bfe4a59a (router endpoint)
- ee3de97d (integration tests + migration)

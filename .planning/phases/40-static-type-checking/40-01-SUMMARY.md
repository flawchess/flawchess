---
phase: 40-static-type-checking
plan: 01
subsystem: backend/tooling
tags: [ty, type-checking, ci, repositories, models, schemas]
dependency_graph:
  requires: []
  provides: [TOOL-01]
  affects: [backend]
tech_stack:
  added: [ty>=0.0.26]
  patterns:
    - "ty: ignore[unresolved-reference] for SQLAlchemy forward references"
    - "Row[Any] return types on all repository query functions"
    - "isinstance(PositionBookmark) for ORM object detection in validators"
    - "CursorResult[Any] suppressed with ty: ignore[unresolved-attribute]"
key_files:
  created: []
  modified:
    - pyproject.toml
    - .github/workflows/ci.yml
    - app/models/game.py
    - app/models/game_position.py
    - app/models/user.py
    - app/repositories/analysis_repository.py
    - app/repositories/endgame_repository.py
    - app/repositories/stats_repository.py
    - app/repositories/import_job_repository.py
    - app/routers/auth.py
    - app/schemas/position_bookmarks.py
    - app/services/lichess_client.py
    - tests/test_bookmark_schema.py
decisions:
  - "Used ty: ignore[unresolved-reference] for SQLAlchemy forward references instead of type: ignore[name-defined]"
  - "Row[Any] return types on repository functions — service layer will adopt TypedDicts in Plan 02"
  - "isinstance(PositionBookmark) replaces hasattr() for ORM detection in model_validator"
  - "lichess_client last_attempt_error initialized as Exception sentinel (not None) to fix invalid-raise"
  - "Test updated to use real PositionBookmark instead of MagicMock after isinstance fix"
metrics:
  duration: "~9 minutes"
  completed: "2026-03-31T20:03:28Z"
  tasks_completed: 2
  files_modified: 13
---

# Phase 40 Plan 01: ty Infrastructure and Mechanical Type Error Fixes Summary

ty type checker configured in CI and all mechanical type errors in models, repositories, schemas, routers, and lichess_client resolved — 35 of 69 errors fixed, enabling Plan 02 to focus on service-layer TypedDict work.

## Tasks Completed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Configure ty in pyproject.toml, migrate dev dependencies, add CI step | Done | f3fc264 |
| 2 | Fix all mechanical type errors in models, repositories, schemas, routers, and lichess_client | Done | 2e19d91 |

## What Was Built

### Task 1: ty Infrastructure
- Migrated `[tool.uv] dev-dependencies` to `[dependency-groups]` format (non-deprecated)
- Added `[tool.ty.rules]` section with `unused-ignore-comment = "warn"` to detect stale suppressions
- Added `Type check (ty)` CI step between ruff and pytest in `.github/workflows/ci.yml`
- Verified `uv sync --locked` still works after format migration

### Task 2: Mechanical Type Error Fixes

**Category A — Model forward-reference suppressions (3 errors fixed):**
- `app/models/game.py`: `# type: ignore[name-defined]` → `# ty: ignore[unresolved-reference]`
- `app/models/game_position.py`: same migration
- `app/models/user.py`: `# noqa: F821` → `# ty: ignore[unresolved-reference]`

**Category B — Repository return types (11+ errors fixed):**
- Added `from sqlalchemy.engine import Row` and `Row[Any]` return types to:
  - `analysis_repository.py`: `query_time_series`, `query_all_results`
  - `endgame_repository.py`: `query_endgame_entry_rows`, `query_conv_recov_timeline_rows`, `query_endgame_performance_rows`, `query_endgame_timeline_rows`, `per_type_rows` dict annotation
  - `stats_repository.py`: `query_rating_history`, `query_results_by_time_control`, `query_results_by_color`, `query_top_openings_sql_wdl`
  - `import_job_repository.py`: suppressed `rowcount` attribute error with `ty: ignore`

**Category C — Schema position_bookmarks (8-9 errors fixed):**
- Replaced `hasattr(data, "moves")` with `isinstance(data, PositionBookmark)` in `model_validator`
- Added `from app.models.position_bookmark import PositionBookmark` import
- Suppressed remaining `dict[Unknown, Unknown]` key access error with `ty: ignore`
- Updated `tests/test_bookmark_schema.py` to use real `PositionBookmark` instead of `MagicMock`

**Category D — FastAPI-Users write_token (1 error suppressed per D-07):**
- `auth.py:170`: `# ty: ignore[unresolved-attribute]` on `strategy.write_token(user)`
- Also suppressed `oauth_callback` `invalid-argument-type` (same FastAPI-Users generic typing issue)

**Category E — Real bug fix in lichess_client (1 error fixed):**
- `last_attempt_error` was initialized as `None` — `raise last_attempt_error` at line 124 would raise `None` if all retries exhausted without capturing an error
- Fixed: initialized as `Exception("Exhausted retries without capturing an error")` sentinel
- Removed old `# type: ignore[misc]` comment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test to use real PositionBookmark instead of MagicMock**
- **Found during:** Task 2, Category C verification
- **Issue:** After changing `hasattr(data, "moves")` → `isinstance(data, PositionBookmark)`, test `test_model_validate_with_int_target_hash_succeeds` failed because `MagicMock()` is not a `PositionBookmark` instance
- **Fix:** Updated `_make_orm_bookmark()` helper to use `PositionBookmark()` directly instead of `MagicMock()`. Added comment explaining why MagicMock was replaced
- **Files modified:** `tests/test_bookmark_schema.py`
- **Commit:** 2e19d91

**2. [Rule 2 - Missing fix] Fixed additional stats_repository functions missing Row[Any]**
- **Found during:** Task 2, ty check after Category B fixes
- **Issue:** Plan mentioned `query_rating_history` but ty also flagged `query_results_by_time_control`, `query_results_by_color`, and `query_top_openings_sql_wdl` in same file
- **Fix:** Applied `Row[Any]` return types to all four functions in stats_repository.py
- **Files modified:** `app/repositories/stats_repository.py`
- **Commit:** 2e19d91

**3. [Rule 2 - Missing fix] Added oauth_callback ty suppression in auth.py**
- **Found during:** Task 2, ty check after Category D fix
- **Issue:** Plan only mentioned `write_token` suppression but ty also reported `invalid-argument-type` on `oauth_callback` call — same FastAPI-Users generic typing limitation
- **Fix:** Added `# ty: ignore[invalid-argument-type]` comment on `oauth_callback` call
- **Files modified:** `app/routers/auth.py`
- **Commit:** 2e19d91

## Verification Results

- `grep -q "dependency-groups" pyproject.toml` — PASS
- `grep -q "tool.ty" pyproject.toml` — PASS
- `grep -q "ty check" .github/workflows/ci.yml` — PASS
- `uv run ty check app/models/ app/repositories/ app/routers/ app/schemas/ app/services/lichess_client.py` — 0 errors
- `uv run pytest -x` — 473 passed, 0 failures

## Remaining ty Errors (Plan 02)

55 errors remain, all in service layer or tests:
- `app/services/analysis_service.py` — Literal list vs Sequence argument types (TypedDict work)
- `app/services/stats_service.py` — FilterParams argument types
- `app/services/endgame_service.py` — no-matching-overload, invalid-argument types
- `tests/` — None guards (game.mainline(), job.games_fetched), follow-on fixes

## Self-Check: PASSED

- SUMMARY.md: FOUND at `.planning/phases/40-static-type-checking/40-01-SUMMARY.md`
- Commit f3fc264 (Task 1): FOUND
- Commit 2e19d91 (Task 2): FOUND
- All 473 tests passing
- 0 ty errors in target scope (models, repositories, routers, schemas, lichess_client)

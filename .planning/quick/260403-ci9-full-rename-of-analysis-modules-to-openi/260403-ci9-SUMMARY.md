---
phase: quick
plan: 260403-ci9
subsystem: backend, frontend, tests
tags: [refactor, rename, openings, naming-consistency]
dependency_graph:
  requires: [260403-c83]
  provides: [consistent openings naming across all code layers]
  affects: [app/routers, app/services, app/repositories, app/schemas, frontend/src/hooks, frontend/src/types, tests]
tech_stack:
  added: []
  patterns: [git mv for history-preserving renames, replace_all for bulk identifier updates]
key_files:
  created: []
  modified:
    - app/routers/openings.py
    - app/services/openings_service.py
    - app/repositories/openings_repository.py
    - app/schemas/openings.py
    - app/main.py
    - app/services/stats_service.py
    - app/services/endgame_service.py
    - app/schemas/endgames.py
    - app/routers/endgames.py
    - frontend/src/hooks/useOpenings.ts
    - frontend/src/types/api.ts
    - frontend/src/pages/Openings.tsx
    - frontend/src/hooks/useChessGame.ts
    - frontend/src/lib/zobrist.ts
    - tests/test_openings_repository.py
    - tests/test_openings_service.py
    - tests/test_auth.py
decisions:
  - "Renamed AnalysisRequest -> OpeningsRequest and AnalysisResponse -> OpeningsResponse (schema classes aligned with module name)"
  - "Updated /api/analysis/positions URL references in test_auth.py to /api/openings/positions (router prefix changed in Task 1)"
  - "Updated endgame_service.py comment referencing analysis_service.get_time_series to openings_service.get_time_series"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 17
---

# Quick Task 260403-ci9: Full Rename of Analysis Modules to Openings — Summary

**One-liner:** Renamed all 7 analysis module files and all internal identifiers (imports, types, variables, comments) to openings, completing the naming consistency started by 260403-c83.

## What Was Done

Preceded by quick/260403-c83 which renamed the `/api/analysis/*` URL to `/api/openings/*`, this task renamed all internal code references so the codebase is fully consistent: no more "analysis" where "openings" is meant.

### Task 1: Backend File Renames

Renamed via `git mv` (history preserved):
- `app/routers/analysis.py` -> `app/routers/openings.py`
- `app/services/analysis_service.py` -> `app/services/openings_service.py`
- `app/repositories/analysis_repository.py` -> `app/repositories/openings_repository.py`
- `app/schemas/analysis.py` -> `app/schemas/openings.py`

Schema class renames:
- `AnalysisRequest` -> `OpeningsRequest`
- `AnalysisResponse` -> `OpeningsResponse`

Updated all imports and docstrings in:
- `app/main.py` — import openings router, include openings.router
- `app/services/stats_service.py` — import recency_cutoff from openings_service
- `app/services/endgame_service.py` — import GameRecord, derive_user_result, recency_cutoff from openings modules
- `app/schemas/endgames.py` — import GameRecord from schemas.openings
- `app/routers/endgames.py` — update comment referencing openings endpoints

### Task 2: Frontend and Test File Renames

Frontend hook renamed via `git mv`:
- `frontend/src/hooks/useAnalysis.ts` -> `frontend/src/hooks/useOpenings.ts`

Frontend identifier renames:
- `usePositionAnalysisQuery` -> `useOpeningsPositionQuery`
- Query key `positionAnalysis` -> `openingsPosition`
- `AnalysisResponse` -> `OpeningsResponse` (in `frontend/src/types/api.ts`)
- `getHashForAnalysis` -> `getHashForOpenings` (in `useChessGame.ts` + `Openings.tsx`)
- Comment in `zobrist.ts`: `AnalysisRequest.target_hash` -> `OpeningsRequest.target_hash`

Test files renamed via `git mv`:
- `tests/test_analysis_repository.py` -> `tests/test_openings_repository.py`
- `tests/test_analysis_service.py` -> `tests/test_openings_service.py`

Updated all imports in test files. In `tests/test_auth.py`:
- Test method names: `test_analysis_requires_auth` -> `test_openings_requires_auth`, etc.
- API URL paths: `/api/analysis/positions` -> `/api/openings/positions`

## Verification Results

- `uv run ruff check .` — PASS
- `uv run ty check app/ tests/` — PASS (0 errors)
- `uv run pytest` — PASS (473/473)
- `npm run build` — PASS (clean build)
- `npm run lint` — PASS

Stale reference grep: zero hits for all old identifiers.

## Deviations from Plan

### Auto-addressed — not technically deviations

The plan mentioned updating test_auth.py API URL paths in the docstrings — the actual `client.post()` call targets also needed updating (from `/api/analysis/positions` to `/api/openings/positions`) since the router prefix was already changed in Task 1. This was the correct fix to keep tests valid.

Otherwise: plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- All 17 files modified confirmed present
- Commits verified:
  - `b86627a` — Task 1: backend file renames
  - `f1cf997` — Task 2: frontend hook and test file renames
- Zero grep hits for stale identifiers
- 473 tests pass

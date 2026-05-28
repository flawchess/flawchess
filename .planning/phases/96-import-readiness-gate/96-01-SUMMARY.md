---
phase: 96-import-readiness-gate
plan: "01"
subsystem: import-readiness
tags: [backend, frontend, api, repository, hook, tdd]
dependency_graph:
  requires: []
  provides:
    - GET /imports/readiness endpoint returning {tier1, tier2, pending_count, total_count}
    - has_any_rows repository helper for UserBenchmarkPercentile existence check
    - ReadinessResponse Pydantic schema
    - ReadinessResponse TypeScript interface in frontend/src/types/api.ts
    - useReadiness polling hook with 3s interval, stops on tier2=true
  affects:
    - app/repositories/user_benchmark_percentiles_repository.py
    - app/schemas/imports.py
    - app/routers/imports.py
    - frontend/src/types/api.ts
tech_stack:
  added: []
  patterns:
    - bounded-count SELECT with LIMIT 1 for existence check
    - sequential await pattern on one AsyncSession (no asyncio.gather)
    - TanStack Query refetchInterval conditional stop on tier2
key_files:
  created:
    - app/schemas/imports.py (ReadinessResponse class added)
    - app/repositories/user_benchmark_percentiles_repository.py (has_any_rows added)
    - app/routers/imports.py (GET /readiness endpoint added)
    - tests/routers/test_imports_readiness.py
    - frontend/src/hooks/useReadiness.ts
    - frontend/src/hooks/__tests__/useReadiness.test.tsx
    - frontend/src/types/api.ts (ReadinessResponse interface added)
  modified:
    - tests/repositories/test_user_benchmark_percentiles_repository.py (has_any_rows tests added)
decisions:
  - "Bounded-count query SELECT COUNT(user_id) ... LIMIT 1 for has_any_rows — exits after first row, not a full table scan"
  - "Sequential awaits on one AsyncSession throughout get_readiness (no asyncio.gather per CLAUDE.md hard rule)"
  - "Short-circuit: skip count_pending_evals when tier1=False; skip has_any_rows when total==0 (below-floor escape, Pitfall 1)"
  - "In-memory job registry only for Tier-1 — orphaned DB jobs post-restart are out of scope (RESEARCH A3)"
  - "No window.location.reload in useReadiness — consumers react via toast/notification instead (Constraint 4)"
metrics:
  duration: ~25 minutes
  completed_date: "2026-05-28"
  tasks_completed: 3
  files_modified: 7
---

# Phase 96 Plan 01: Import Readiness Gate Contract Layer Summary

Two-tier readiness endpoint and frontend poll hook: `GET /imports/readiness` returns `{tier1, tier2, pending_count, total_count}`, backed by a `has_any_rows` existence helper on `user_benchmark_percentiles`, with a `useReadiness` hook that polls at 3s and stops when `tier2=true`.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 RED | Failing tests for has_any_rows | 6e27b93c | Done |
| 1 GREEN | has_any_rows helper + ReadinessResponse schema | 38f48770 | Done |
| 2 RED | Failing tests for GET /imports/readiness | 9dbb0c90 | Done |
| 2 GREEN | GET /imports/readiness endpoint | 0c43ad0f | Done |
| 3 RED | Failing frontend tests for useReadiness | 08f9223e | Done |
| 3 GREEN | ReadinessResponse TS type + useReadiness hook | 8e9e34f3 | Done |

## Implementation Details

### Task 1: has_any_rows + ReadinessResponse schema

`has_any_rows(session, *, user_id: int) -> bool` uses a bounded-count query:
```python
select(func.count(UserBenchmarkPercentile.user_id))
    .where(UserBenchmarkPercentile.user_id == user_id)
    .limit(1)
```
Returns `(result.scalar() or 0) > 0`. The `LIMIT 1` bound ensures PostgreSQL exits after the first matching row rather than counting the full user partition.

`ReadinessResponse` mirrors `EvalCoverageResponse` style with four fields and a docstring recording the tier semantics and below-floor escape.

### Task 2: GET /imports/readiness endpoint

Endpoint at relative path `/readiness` (router prefix `/imports` produces the full `/api/imports/readiness` path). Sequential read pattern:

1. `find_active_jobs_for_user(user.id)` — in-memory only, no DB query
2. `count_games_for_user(session, user.id)` — always needed for total_count
3. `count_pending_evals(session, user.id)` — skipped when `tier1=False`
4. `has_any_rows(session, user_id=user.id)` — skipped when `total==0` or `tier1=False`

Max 3 DB queries per request; min 1.

### Task 3: useReadiness hook

`refetchInterval: (query) => query.state.data?.tier2 ? false : READINESS_POLL_INTERVAL_MS`

Returns `{ tier1: false, tier2: false, pendingCount: 0, totalCount: 0, isLoading }` before first fetch. No `useRef`, no `useEffect`, no `window.location.reload`.

## Verification Results

- `uv run ty check app/ tests/` — 0 errors
- `uv run ruff check app/ tests/` — clean
- `uv run ruff format --check app/ tests/` — 185 files already formatted
- `uv run pytest tests/routers/test_imports_readiness.py -v` — 6/6 passed
- `uv run pytest tests/repositories/test_user_benchmark_percentiles_repository.py` — all passed
- `cd frontend && npm test -- --run useReadiness` — 4/4 passed
- `cd frontend && npm run lint` — clean
- `cd frontend && npm run knip` — clean
- `grep asyncio.gather app/routers/imports.py` — only in docstring (no code usage)

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints beyond the planned `GET /imports/readiness`. No new auth paths. No schema changes. Threat mitigations T-96-01/02/03 all implemented as planned:
- T-96-01 (IDOR): `user.id` from `Depends(current_active_user)` only; `has_any_rows` takes keyword-only `user_id`; covered by `test_readiness_scoped_to_user`
- T-96-02 (DoS/Tampering): sequential awaits, no `asyncio.gather`, short-circuits bound query count ≤3; `asyncio.gather` absence confirmed by grep
- T-96-03 (Spoofing): `current_active_user` dep rejects anonymous requests; covered by `test_readiness_requires_auth`

## Self-Check: PASSED

Files exist:
- `app/repositories/user_benchmark_percentiles_repository.py` — has_any_rows: FOUND
- `app/schemas/imports.py` — ReadinessResponse: FOUND
- `app/routers/imports.py` — get_readiness: FOUND
- `tests/routers/test_imports_readiness.py` — FOUND
- `frontend/src/hooks/useReadiness.ts` — FOUND
- `frontend/src/types/api.ts` — ReadinessResponse: FOUND

Commits verified:
- 6e27b93c — test(96-01): add failing tests for has_any_rows
- 38f48770 — feat(96-01): add has_any_rows helper and ReadinessResponse schema
- 9dbb0c90 — test(96-01): add failing tests for GET /imports/readiness
- 0c43ad0f — feat(96-01): add GET /imports/readiness endpoint
- 08f9223e — test(96-01): add failing frontend tests for useReadiness
- 8e9e34f3 — feat(96-01): add ReadinessResponse TS type and useReadiness hook

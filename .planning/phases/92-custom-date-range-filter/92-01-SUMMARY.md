---
phase: 92-custom-date-range-filter
plan: "01"
subsystem: backend-schema, backend-service, backend-repo, frontend-types
tags: [recency, timeseries, cleanup, d19, tdd]
dependency_graph:
  requires: []
  provides: [TimeSeriesRequest-recency-free]
  affects:
    - app/schemas/openings.py
    - app/services/openings_service.py
    - app/repositories/openings_repository.py
    - frontend/src/types/position_bookmarks.ts
    - tests/test_openings_time_series.py
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN on Pydantic model_fields assertion
    - D-19 date-filter-free time-series (service-layer recency removal)
key_files:
  created: []
  modified:
    - app/schemas/openings.py
    - app/services/openings_service.py
    - app/repositories/openings_repository.py
    - frontend/src/types/position_bookmarks.ts
    - tests/test_openings_time_series.py
decisions:
  - D-19 confirmed: TimeSeriesRequest has no recency field; time-series endpoint is date-filter-free
  - recency filtering was done in Python service layer (not SQL); removed post-processing block in get_time_series
  - TestRecencyFilter class removed as it tested behavior being deleted
metrics:
  duration: ~25 minutes
  completed: "2026-05-21"
  tasks_completed: 1
  files_modified: 5
---

# Phase 92 Plan 01: Drop recency from TimeSeriesRequest (D-19 pre-work) Summary

Dropped the unused `recency` field from the bookmark time-series request shape on both the Pydantic and TypeScript sides, plus the matching service-layer Python filtering.

## Tasks

### Task 1: Remove recency from TimeSeriesRequest (both stacks) + drop pass-through in service/repo

**Status:** DONE

**Commits:**
- `1e0ece00` — test(92-01): add failing test for TimeSeriesRequest recency removal (D-19) [RED]
- `ecda1a50` — feat(92-01): remove recency from TimeSeriesRequest on both stacks (D-19) [GREEN]

**What was done:**

1. `app/schemas/openings.py` — Removed `recency: Literal[...] | None` field from `TimeSeriesRequest`. Added a docstring explaining the D-19 rationale (date-filter-free time-series). Updated `BookmarkTimeSeries.last_played_at` comment to remove "recency window" reference. `OpeningsRequest.recency` (line 39) and `NextMovesRequest.recency` (line 218) are untouched — those are handled in Plan 02.

2. `app/services/openings_service.py` — Removed `cutoff = recency_cutoff(request.recency)` and `cutoff_str = ...` from `get_time_series`. Removed the Python-side post-processing block that filtered data points and recomputed totals based on `cutoff_str`. The repo call was already passing `recency_cutoff=None`; removed that keyword arg too. `RECENCY_DELTAS`, `recency_cutoff()` helper, and all other callsites remain untouched (still used by `analyze()` and `get_next_moves()` for OpeningsRequest/NextMovesRequest, handled in Plan 02).

3. `app/repositories/openings_repository.py` — Removed `recency_cutoff: datetime.datetime | None = None` parameter from `query_time_series`. Removed the `if recency_cutoff is not None: stmt = stmt.where(...)` branch. All other repository functions retaining `recency_cutoff` are untouched (Plan 02).

4. `frontend/src/types/position_bookmarks.ts` — Removed `recency?: 'week' | ... | null` field from `TimeSeriesRequest` interface. Updated `BookmarkTimeSeries.last_played_at` comment to remove "recency window" reference. No other TypeScript changes.

5. `tests/test_openings_time_series.py` — Added `TestTimeSeriesRequestSchema.test_no_recency_field_in_schema` (the RED gate). Removed `TestRecencyFilter` class (two tests that verified recency-trimming behavior now deleted). Updated `_make_request` helper to remove `recency` param. Updated module docstring and removed unused `_USER_RECENCY` constant.

## Verification

All acceptance criteria confirmed passing:

- `grep -n "recency" app/schemas/openings.py` — matches at lines 39, 218 (OpeningsRequest, NextMovesRequest — expected), and line 146 (docstring comment). No match inside `TimeSeriesRequest` class body.
- `grep -n "recency" frontend/src/types/position_bookmarks.ts` — no matches.
- `grep -n "recency_cutoff\|recency=" app/services/openings_service.py` — no matches inside `get_time_series` function.
- `grep -n "recency_cutoff" app/repositories/openings_repository.py` — matches only in functions other than `query_time_series` (expected — Plan 02).
- `uv run pytest tests/test_openings_time_series.py -x` — 8 passed.
- `uv run ty check app/ tests/` — All checks passed.
- `cd frontend && npx tsc --noEmit` — passes (no output).
- `cd frontend && npm run lint` — passes.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (`test(...)`) | `1e0ece00` | PASS — test failed before implementation |
| GREEN (`feat(...)`) | `ecda1a50` | PASS — all 8 tests pass |
| REFACTOR | N/A — no refactor needed | N/A |

## Deviations from Plan

None — plan executed exactly as written.

The service-layer Python filtering (the `if cutoff_str:` block in `get_time_series`) was more than just "removing the recency_cutoff arg from repo call" — the service was actually doing the recency filtering itself in Python (not via SQL). This was visible from code inspection but the plan's action description ("remove the `recency_cutoff` argument from any call into the time-series repository function") was accurate at the conceptual level: removing recency from the request naturally meant cleaning up all recency-related code in the service, which included both the cutoff computation and the Python-side filtering block.

## Known Stubs

None.

## Threat Flags

None — removing a field reduces attack surface. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/flawchess/.claude/worktrees/agent-af97468de921e6c74/tests/test_openings_time_series.py` — FOUND
- `/home/aimfeld/Projects/Python/flawchess/.claude/worktrees/agent-af97468de921e6c74/app/schemas/openings.py` — FOUND (modified)
- `/home/aimfeld/Projects/Python/flawchess/.claude/worktrees/agent-af97468de921e6c74/app/services/openings_service.py` — FOUND (modified)
- `/home/aimfeld/Projects/Python/flawchess/.claude/worktrees/agent-af97468de921e6c74/app/repositories/openings_repository.py` — FOUND (modified)
- `/home/aimfeld/Projects/Python/flawchess/.claude/worktrees/agent-af97468de921e6c74/frontend/src/types/position_bookmarks.ts` — FOUND (modified)
- Commit `1e0ece00` — FOUND
- Commit `ecda1a50` — FOUND

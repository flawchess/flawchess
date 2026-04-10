---
phase: 51-stats-subtab-homepage-global-stats
plan: 01
subsystem: backend-stats-api, frontend-stats-hooks
tags: [filters, opponent-type, opponent-strength, stats, global-stats, rating-history, tdd]
dependency_graph:
  requires: []
  provides: [opponent_type+opponent_strength wired through /stats/global and /stats/rating-history end-to-end]
  affects: [GlobalStats.tsx, useStats.ts, statsApi, stats_service, stats_repository]
tech_stack:
  added: []
  patterns: [apply_game_filters single source of truth for all filter logic, TDD RED-GREEN cycle]
key_files:
  created: []
  modified:
    - app/routers/stats.py
    - app/services/stats_service.py
    - app/repositories/stats_repository.py
    - frontend/src/api/client.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/pages/GlobalStats.tsx
    - tests/test_stats_router.py
decisions:
  - "opponent_type defaults to 'human' on Global Stats (D-21): bot games excluded by default — visible behavior change from previous all-games inclusion"
  - "Repository refactor uses apply_game_filters as single source of truth (CLAUDE.md Shared Query Filters rule), removing duplicated manual recency/platform WHERE clauses"
  - "New query params match /stats/most-played-openings pattern exactly (D-18/D-22 narrow backend exception)"
metrics:
  duration: ~30 minutes
  completed: "2026-04-10T14:31:32Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 7
---

# Phase 51 Plan 01: Global Stats Opponent Filter Wiring Summary

## One-liner

Wired `opponent_type` + `opponent_strength` end-to-end through `/stats/global` and `/stats/rating-history` backend endpoints and the React hooks/API client layer, so Global Stats now defaults to excluding bot games.

## What Was Built

### Task 1: Backend (TDD)
Added `opponent_type` and `opponent_strength` Query params to `/stats/global` and `/stats/rating-history` — mirroring the existing `/stats/most-played-openings` pattern exactly. The service layer (`get_global_stats`, `get_rating_history`) accepts the two new keyword-only args and passes them down. The repository layer was refactored from duplicated manual `WHERE` clauses to the shared `apply_game_filters()` helper per CLAUDE.md's "Shared Query Filters" rule.

6 new integration tests (3 per endpoint): `accepts_opponent_type`, `accepts_opponent_strength`, `rejects_invalid_opponent_strength` — all pass.

### Task 2: Frontend
Extended `statsApi.getRatingHistory` and `statsApi.getGlobalStats` to accept `opponentType` and `opponentStrength` arguments (delegating to `buildFilterParams`). Extended `useRatingHistory` and `useGlobalStats` hooks with 4-arg signatures including both new params in the TanStack Query `queryKey`. Minimally wired `GlobalStats.tsx` to pass `filters.opponentType` and `filters.opponentStrength` from the shared filter store to both hooks.

## Visible Behavior Change

The Global Stats page now defaults to excluding bot games (`opponentType='human'` from `DEFAULT_FILTERS`). Previously the endpoint ignored opponent filters so bot games were always included in global WDL and rating history. This matches user expectation but must be called out in the PR description per D-21.

## Decisions Made

1. **opponent_type defaults to 'human'** — matches `DEFAULT_FILTERS` in `FilterPanel.tsx`. Bot games are excluded from Global Stats by default. This is a visible behavior change.
2. **Repository refactor uses apply_game_filters** — removed duplicated manual `recency_cutoff` and `platform` WHERE clauses from `query_rating_history`, `query_results_by_time_control`, `query_results_by_color`. `apply_game_filters` is now the single source of truth per CLAUDE.md.
3. **No new imports needed** — `Literal` already imported in router and service; `apply_game_filters` already imported in repository; `OpponentStrength` already exported from `types/api.ts`.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

T-51-01 mitigated: `opponent_strength` uses `Literal["any", "stronger", "similar", "weaker"]` — FastAPI returns 422 on invalid values (proven by test). No new security surface introduced beyond what was planned.

## Self-Check: PASSED

- All 7 modified files exist on disk
- Commit `5cfe3db` (Task 1 backend) exists
- Commit `6ab4dcb` (Task 2 frontend) exists

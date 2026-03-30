---
phase: 36-most-played-openings
plan: "01"
subsystem: stats
tags: [backend, frontend, openings, wdl, statistics]
dependency_graph:
  requires: []
  provides: [most-played-openings-endpoint, most-played-openings-ui]
  affects: [openings-statistics-tab]
tech_stack:
  added: []
  patterns: [subquery-join-for-top-n, python-side-wdl-aggregation, structural-duck-typing]
key_files:
  created: []
  modified:
    - app/schemas/stats.py
    - app/repositories/stats_repository.py
    - app/services/stats_service.py
    - app/routers/stats.py
    - tests/test_stats_repository.py
    - tests/test_stats_router.py
    - frontend/src/types/stats.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/pages/Openings.tsx
decisions:
  - "Subquery-join pattern for top-N openings: SELECT top ECOs by COUNT HAVING >= min_games, then JOIN back to fetch individual game rows for Python WDL aggregation — consistent with existing stats_repository query patterns"
  - "OpeningWDL structurally satisfies WDLRowData via duck typing (Phase 35 decision) — no explicit implements needed"
  - "Most Played Openings uses all-time data (no filter params) per Phase 36 research recommendation"
metrics:
  duration_minutes: 6
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_modified: 10
---

# Phase 36 Plan 01: Most Played Openings Backend + Frontend Summary

Most-played openings endpoint (GET /stats/most-played-openings) and UI section — top 5 openings per color (White/Black) with WDL stats, displayed as WDLChartRow components at the top of the Opening Statistics subtab.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Backend: schema, repository, service, router, and tests | 550da6e |
| 2 | Frontend: types, API client, hook, and Openings.tsx rendering | 9772cc1 |

## What Was Built

### Backend

**Schema (`app/schemas/stats.py`):**
- `OpeningWDL` — WDL stats for a single opening with ECO code, display label, and percentage fields
- `MostPlayedOpeningsResponse` — top openings grouped by `white` and `black` color

**Repository (`app/repositories/stats_repository.py`):**
- `query_top_openings_by_color()` — uses a subquery to find top-N (eco, name) pairs by game count (HAVING >= min_games), then JOINs back to fetch individual game rows for Python-side WDL aggregation
- Excludes NULL opening_eco/opening_name rows via `is_not(None)` filters
- Returns `(opening_eco, opening_name, result, user_color)` tuples

**Service (`app/services/stats_service.py`):**
- `MIN_GAMES_FOR_OPENING = 10` and `TOP_OPENINGS_LIMIT = 5` named constants
- `_aggregate_top_openings()` helper groups rows by (eco, name), counts WDL, computes percentages, builds label as `"{name} ({eco})"`
- `get_most_played_openings()` calls repository for both colors, aggregates, returns response

**Router (`app/routers/stats.py`):**
- `GET /stats/most-played-openings` endpoint with `response_model=MostPlayedOpeningsResponse`
- No filter parameters — all-time top 5 per color

**Tests:**
- `TestQueryTopOpeningsByColor` (4 tests): top-N by game count, excludes below min_games, excludes NULL eco/name, filters by color
- `TestGetMostPlayedOpenings` (2 tests): 401 without auth, 200 with white/black structure

### Frontend

**Types (`frontend/src/types/stats.ts`):** `OpeningWDL` and `MostPlayedOpeningsResponse` interfaces

**API client (`frontend/src/api/client.ts`):** `getMostPlayedOpenings()` in `statsApi`

**Hook (`frontend/src/hooks/useStats.ts`):** `useMostPlayedOpenings()` with `queryKey: ['mostPlayedOpenings']`

**Openings.tsx:** Most Played Openings section rendered at top of `statisticsContent` (shared variable propagates to both desktop and mobile TabsContent automatically) with:
- Charcoal container with `data-testid="most-played-openings"`
- White and Black subsections with color dot indicators
- WDLChartRow for each opening with proportional game count bar
- Empty state hidden (section only shown when at least one color has data)

## Verification

- `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x -v` — 39 tests pass
- `uv run pytest` — 457 tests pass (no regressions)
- `npm run build` — TypeScript compiles without errors

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — the endpoint returns live data from the games table. The UI section is hidden when no openings meet the 10-game threshold (not a stub, correct empty state behavior).

## Self-Check: PASSED

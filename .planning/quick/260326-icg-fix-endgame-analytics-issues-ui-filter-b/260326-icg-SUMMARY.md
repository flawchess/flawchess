---
phase: quick
plan: 260326-icg
subsystem: ui, api
tags: [axios, fastapi, endgame-analytics, react, tanstack-query]

requires:
  - phase: 29-endgame-analytics
    provides: "Endgame analytics backend and frontend"
provides:
  - "Working filter reactivity on endgame GET endpoints"
  - "Total games context (X of Y games reached endgame)"
  - "Low sample size warnings for categories < 10 games"
  - "Q vs Q exclusion explanation in info tooltip"
affects: []

tech-stack:
  added: []
  patterns:
    - "axios paramsSerializer indexes:null for FastAPI array query params"
    - "MIN_GAMES_FOR_RELIABLE_STATS constant for sample size threshold"

key-files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/types/endgames.ts
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - app/repositories/endgame_repository.py

key-decisions:
  - "Root cause of filter bug: axios bracket notation for arrays (time_control[]=blitz) not parsed by FastAPI — fixed globally with paramsSerializer indexes:null"
  - "endgame_games computed as sum of category totals (no extra DB query) since rows are already fetched"

requirements-completed: []

duration: 5min
completed: 2026-03-26
---

# Quick Task 260326-icg: Fix Endgame Analytics Issues Summary

**Fixed axios array param serialization bug breaking all GET endpoint filters, added total games context, sample size warnings, and Q vs Q tooltip**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T12:16:23Z
- **Completed:** 2026-03-26T12:21:20Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Fixed critical filter bug: axios was serializing arrays with bracket notation (time_control[]=blitz) which FastAPI silently ignores — all GET endpoint filters were non-functional
- Added total_games and endgame_games fields to EndgameStatsResponse with count_filtered_games repository function
- Added "X of Y games (Z%) reached an endgame phase" summary line above the chart
- Added "(low sample)" warning and dimmed WDL bars for categories with < 10 games
- Added 1500cp threshold and Q vs Q exclusion explanation to the info tooltip

## Task Commits

Each task was committed atomically:

1. **Task 1: Debug and fix filter reactivity bug + add total games context to backend** - `8356da3` (fix)
2. **Task 2: Frontend total games summary, sample size warnings, and tooltip update** - `5ac4c3c` (feat)

## Files Created/Modified
- `frontend/src/api/client.ts` - Added paramsSerializer config for FastAPI-compatible array params
- `frontend/src/pages/Endgames.tsx` - Added endgame summary line above chart
- `frontend/src/components/charts/EndgameWDLChart.tsx` - Sample size warnings, dimmed bars, updated tooltip
- `frontend/src/types/endgames.ts` - Added total_games and endgame_games to EndgameStatsResponse
- `app/schemas/endgames.py` - Added total_games and endgame_games fields
- `app/services/endgame_service.py` - Compute total_games via count_filtered_games, endgame_games as category sum
- `app/repositories/endgame_repository.py` - New count_filtered_games function

## Decisions Made
- Root cause of filter bug was axios's default array serialization using bracket notation, which FastAPI does not parse. Fixed globally on the axios instance (not per-request) since all GET endpoints should use repeated-key format.
- endgame_games computed as sum of category totals rather than a separate DB query, since the aggregation already processes all matching rows.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Axios array param serialization incompatible with FastAPI**
- **Found during:** Task 1 (filter bug investigation)
- **Issue:** Plan suggested the bug might be in useDebounce or TanStack Query key deduplication. Actual root cause was axios serializing arrays as `time_control[]=blitz` (bracket notation) which FastAPI silently ignores, receiving `None` for all array params. This meant ALL GET endpoint filters (time_control, platform) were completely non-functional.
- **Fix:** Added `paramsSerializer: { indexes: null }` to the global axios instance, which produces `time_control=blitz&time_control=rapid` (repeated keys) that FastAPI correctly parses.
- **Files modified:** `frontend/src/api/client.ts`
- **Verification:** `node -e` confirmed axios now produces correct query string format
- **Committed in:** 8356da3 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The actual root cause differed from plan's hypotheses but the fix is simpler and more correct (global fix vs per-endpoint workaround). No scope creep.

## Issues Encountered
None beyond the filter bug root cause analysis described above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all features are fully wired to real data.

---
*Quick task: 260326-icg*
*Completed: 2026-03-26*

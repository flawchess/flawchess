---
phase: 15-enhanced-game-import-data
plan: 03
subsystem: ui, api
tags: [react, fastapi, tanstack-query, axios, typescript, normalization]

# Dependency graph
requires:
  - phase: 15-enhanced-game-import-data
    provides: auth fixes and GameRecord enrichment from 15-02

provides:
  - Consistent time_control_str without +0 suffix on both platforms
  - Human-readable time control display in GameCard (minutes not seconds)
  - Shared QueryClient singleton in frontend/src/lib/queryClient.ts
  - queryClient.clear() on all auth transitions (login, logout, 401)

affects: [frontend auth, game card display, data isolation between users]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_normalize_tc_str helper: strip +0 suffix for zero-increment time controls"
    - "Shared QueryClient singleton: imported by non-React modules (api/client.ts) for cache clearing"
    - "Cache clear on all auth transitions: login, logout, and 401 interceptor"

key-files:
  created:
    - frontend/src/lib/queryClient.ts
  modified:
    - app/services/normalization.py
    - tests/test_normalization.py
    - frontend/src/components/results/GameCard.tsx
    - frontend/src/App.tsx
    - frontend/src/api/client.ts
    - frontend/src/hooks/useAuth.ts

key-decisions:
  - "_normalize_tc_str helper called by both normalizers: DRY approach for consistent +0 stripping"
  - "formatTimeControl in GameCard converts seconds to minutes for human-readable display"
  - "QueryClient extracted to lib/queryClient.ts: required because api/client.ts is not a React component and cannot use useQueryClient hook"
  - "queryClient.clear() before login(): prevents residual data from previous user session on shared browsers"

patterns-established:
  - "formatTimeControl: converts stored seconds-based tc_str to display minutes (e.g. 600+5 -> 10+5)"
  - "shared queryClient singleton: importable from non-React modules for cache clearing"

requirements-completed: [EIGD-07, EIGD-05]

# Metrics
duration: 15min
completed: 2026-03-18
---

# Phase 15 Plan 03: Gap Closure (Time Control + Data Isolation) Summary

**Consistent time_control_str without +0 suffix, human-readable GameCard display (10+5 not 600+5), and queryClient.clear() on all auth transitions via shared QueryClient singleton**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-18T20:00:00Z
- **Completed:** 2026-03-18T20:15:00Z
- **Tasks:** 2
- **Files modified:** 6 (1 created)

## Accomplishments
- Backend: `_normalize_tc_str` helper strips `+0` suffix for both chess.com and lichess normalizers
- Frontend: `formatTimeControl` in GameCard converts raw seconds to minutes for human-readable display (e.g., "Blitz . 10+5" not "Blitz . 600+5")
- Frontend: Extracted `QueryClient` to `frontend/src/lib/queryClient.ts` singleton — importable from non-React modules
- Frontend: `queryClient.clear()` now fires on all auth transitions: login(), logout(), and 401 interceptor

## Task Commits

Each task was committed atomically:

1. **Task 1: Normalize time_control_str and format display** - `4597256` (feat)
2. **Task 2: Fix 401 interceptor and login cache clearing** - `58bb061` (feat)

## Files Created/Modified
- `app/services/normalization.py` - Added `_normalize_tc_str` helper; applied in both normalizers
- `tests/test_normalization.py` - Added `TestNormalizeTcStr` and `TestTcStrConsistency` test classes; updated existing test
- `frontend/src/components/results/GameCard.tsx` - Added `formatTimeControl` function; applied to time control display
- `frontend/src/lib/queryClient.ts` - New: shared QueryClient singleton
- `frontend/src/App.tsx` - Removed inline QueryClient; imports from shared module
- `frontend/src/api/client.ts` - Added `queryClient.clear()` in 401 interceptor
- `frontend/src/hooks/useAuth.ts` - Removed `useQueryClient` hook; uses shared singleton; added `queryClient.clear()` in login()

## Decisions Made
- `_normalize_tc_str` called by both normalizers rather than inlining the logic — keeps normalization DRY and testable
- `formatTimeControl` placed in GameCard.tsx (not a shared utility) — only used there
- `queryClient.clear()` fires at the start of `login()` before the API call — clears any residual cache before authenticating, not after

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test expecting "+0" suffix**
- **Found during:** Task 1 (Normalize time_control_str)
- **Issue:** `test_time_control_parsed` in `TestNormalizeChesscomGame` expected `time_control_str == "600+0"` which would fail after the normalization change
- **Fix:** Updated assertion to expect `"600"` and added explanatory comment
- **Files modified:** tests/test_normalization.py
- **Verification:** All 76 normalization tests pass
- **Committed in:** 4597256 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - existing test expected old behavior)
**Impact on plan:** Required fix — existing test asserted the behavior we were changing. No scope creep.

## Issues Encountered
None.

## Next Phase Readiness
- Phase 15 gap closure complete — all UAT gaps addressed
- Time control display is human-readable on GameCard
- Data isolation between user sessions is enforced at all auth transitions

---
*Phase: 15-enhanced-game-import-data*
*Completed: 2026-03-18*

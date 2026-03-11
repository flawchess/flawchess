---
phase: 02-import-pipeline
plan: "04"
subsystem: api
tags: [httpx, chess.com, error-handling, testing]

# Dependency graph
requires:
  - phase: 02-import-pipeline
    provides: chesscom_client.py async generator for fetching games
provides:
  - Hardened chess.com HTTP client with status-code guards before every .json() call
  - Regression test coverage for 410/403/500 archives errors and per-archive skip behavior
affects: [analysis-api, import-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [status-code guard before .json(), graceful continue on non-200 per-archive response]

key-files:
  created: []
  modified:
    - app/services/chesscom_client.py
    - tests/test_chesscom_client.py

key-decisions:
  - "Non-200/non-404 archives response raises ValueError with status code in message — consistent with job error contract"
  - "Per-archive non-200 uses continue rather than raising — partial failure should not abort the whole import"

patterns-established:
  - "Status-code guard: always check status_code != 200 before calling .json() on external API responses"
  - "TDD sequence: write failing tests first, commit RED, then implement GREEN"

requirements-completed: [IMP-01]

# Metrics
duration: 2min
completed: 2026-03-11
---

# Phase 2 Plan 04: chess.com Client HTTP Error Hardening Summary

**Status-code guards added before every `.json()` call in chesscom_client.py, fixing JSONDecodeError crash on 410/403/500 archives responses and enabling graceful skip of failed per-archive fetches**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-11T14:12:44Z
- **Completed:** 2026-03-11T14:14:27Z
- **Tasks:** 2 (TDD: RED then GREEN)
- **Files modified:** 2

## Accomplishments
- Five regression tests cover 410, 403, 500 on archives endpoint and 500/410 on per-archive fetches
- Archives endpoint: any non-200/non-404 status raises `ValueError("chess.com request failed (status N) for user '...'")` before `.json()` is called
- Per-archive endpoint: any non-200 after 429 retry logic triggers `continue`, skipping the archive without crashing the generator
- UAT gap closed: email-format usernames (chess.com returns 410) now produce a `status: "failed"` job with readable error, not an unhandled JSONDecodeError

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Regression tests for non-200 error paths** - `2d41b17` (test)
2. **Task 2: GREEN — Harden chesscom_client status-code checks** - `e87b739` (feat)

**Plan metadata:** (docs commit pending)

_Note: TDD tasks have two commits: test (RED) then feat (GREEN)_

## Files Created/Modified
- `app/services/chesscom_client.py` - Added non-200 guard after 404 check on archives endpoint; added non-200 continue guard before `resp.json()` in per-archive loop
- `tests/test_chesscom_client.py` - Added 5 new test methods covering 410/403/500 archives errors and 500/410 per-archive skip behavior (8 → 13 tests in TestFetchChesscomGames)

## Decisions Made
- Non-200/non-404 archives raises ValueError with status code included in message — makes the job error message diagnostic without exposing internals
- Per-archive non-200 uses `continue` not raise — partial failure (one bad month) should not abort the whole user import

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 Import Pipeline is now complete with all UAT gaps addressed
- Phase 3 Analysis API can proceed: import pipeline is hardened and all 132 tests pass

## Self-Check: PASSED

All expected files and commits verified present.

---
*Phase: 02-import-pipeline*
*Completed: 2026-03-11*

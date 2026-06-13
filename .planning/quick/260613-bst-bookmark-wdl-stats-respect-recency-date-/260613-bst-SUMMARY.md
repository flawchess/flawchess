---
phase: quick-260613-bst
plan: "01"
subsystem: openings
tags: [bookmark, time-series, recency, date-filter, tdd]
dependency_graph:
  requires: []
  provides: [time-series-date-windowing, bookmark-empty-state]
  affects: [openings-stats-tab, bookmark-wdl-card]
tech_stack:
  added: []
  patterns: [date-windowed-rolling-average, warm-up-preserved-rolling-window, empty-state-guard]
key_files:
  created: []
  modified:
    - app/schemas/openings.py
    - app/services/openings_service.py
    - tests/test_openings_time_series.py
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
    - CHANGELOG.md
    - .planning/milestones/v1.18-phases/92-custom-date-range-filter/92-CONTEXT.md
decisions:
  - "D-19 amendment: TimeSeriesRequest now accepts from_date/to_date; emitted points + WDL totals are date-windowed while the rolling average warms from pre-window games"
  - "Repo not date-filtered: full chronological history loaded for warm-up correctness"
  - "_in_window() helper uses played_at.date() for comparison (strips time component)"
  - "Empty state guarded purely on opening.total === 0; wdlLine and linksRow count constants cover both mobile and desktop layouts"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-13T06:44:28Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 9
---

# Phase quick-260613-bst Plan 01: Bookmark WDL Stats Respect Recency Date Summary

Fixes the Openings Stats bookmark card so its WDL bar, game count, and Score % respond to the recency/date filter by date-windowing `POST /openings/time-series` emitted points and WDL totals, while preserving rolling-average warm-up from pre-window games. Adds an empty state for zero-match windows.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend: date-window time-series totals + warm-up rolling emission | d6640124 | app/schemas/openings.py, app/services/openings_service.py, tests/test_openings_time_series.py, 92-CONTEXT.md |
| 2 | Frontend: wire recency into time-series + empty state + CHANGELOG | 24936db4 | frontend/src/types/position_bookmarks.ts, frontend/src/pages/Openings.tsx, frontend/src/components/stats/OpeningStatsCard.tsx, OpeningStatsCard.test.tsx, CHANGELOG.md |

## What Was Built

**Backend (Task 1 — TDD):**

- `TimeSeriesRequest` schema: added optional `from_date: datetime.date | None` and `to_date: datetime.date | None` with `_check_date_range` model_validator (mirrors `OpeningsRequest`). Updated docstring to describe the D-19 amendment.
- `_in_window()` helper in `openings_service.py`: pure predicate comparing `played_at.date()` against optional bounds; open-bound semantics when either is `None`.
- `get_time_series()` refactored: full chronological history is still loaded from the repo (no SQL date filter — warm-up preserved). Per-game loop gates emission into `data_by_date` AND totals increment on `_in_window(played_at, from_date, to_date)`. `last_played_at` only updates for in-window games.
- 17 tests pass (5 new date-windowed tests + updated schema assertions; 12 existing tests untouched).

**Frontend (Task 2):**

- `TimeSeriesRequest` TypeScript interface: added `from_date?: string` and `to_date?: string`.
- `Openings.tsx` `timeSeriesRequest` useMemo: imported `resolveDateRange` and `dateRangeToWireParams` from `@/lib/recency`; spread `dateRangeToWireParams(resolveDateRange(debouncedFilters))` into the request object. Replaced stale D-19 comment.
- `OpeningStatsCard.tsx`: `wdlLine` now renders `<div data-testid="${cardTestId}-empty">No matching games</div>` when `opening.total === 0`; games count button shows `'—'` (em dash) when `opening.total === 0`. Both mobile (`sm:hidden`) and desktop (`hidden sm:flex`) blocks use the shared `wdlLine` and `linksRow` constants, so both layouts are covered.
- 20 tests pass (18 existing + 2 new empty-state tests).

## Decisions Made

1. **Repo not date-filtered.** The plan explicitly requires full-history loading for warm-up. `query_time_series` receives no `from_date`/`to_date` — only the service gates which rows are emitted and counted.
2. **`_in_window()` on `played_at.date()`.** Strips the time component so "end of day to_date" semantics are consistent with the D-10 repository convention without timezone math on the server.
3. **Empty state guards on `total === 0` only.** Most Played Openings rows always have games; the guard is de-facto bookmark-only but expressed cleanly without coupling to context.
4. **Shared constants for mobile/desktop parity.** `wdlLine` and `linksRow` are declared once and used in both the `sm:hidden` and `hidden sm:flex` blocks — one change covers both layouts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test warm-up scenario used January day numbers > 31**

- **Found during:** Task 1 GREEN phase
- **Issue:** `test_warm_up_preserved_at_window_boundary` seeded `ROLLING_WINDOW_SIZE` (50) games in January using `day` 1..50, but January has only 31 days — `datetime.datetime(2026, 1, 32, ...)` raises `ValueError`.
- **Fix:** Spread the 50 pre-window games across January 2025 (days 1-28, cycling) and February 2025 (remaining 22 games, days 1-22), using hour/minute offsets for unique timestamps. The in-window game moved to March 1 2026.
- **Files modified:** `tests/test_openings_time_series.py`
- **Commit:** d6640124 (included in Task 1 commit)

None — plan executed as written otherwise.

## Known Stubs

None. The date-windowed backend now feeds real data to the bookmark card; no stubs or placeholders.

## Threat Flags

None. No new network endpoints or auth paths introduced. The `from_date`/`to_date` fields are optional scalar date fields passed through the existing time-series endpoint with server-side validation (Pydantic model_validator).

## Self-Check: PASSED

- `app/schemas/openings.py` — modified, from_date/to_date in TimeSeriesRequest
- `app/services/openings_service.py` — modified, _in_window() helper + windowed emission
- `tests/test_openings_time_series.py` — modified, 17 tests pass
- `frontend/src/types/position_bookmarks.ts` — modified, from_date/to_date in interface
- `frontend/src/pages/Openings.tsx` — modified, dateRangeToWireParams wired
- `frontend/src/components/stats/OpeningStatsCard.tsx` — modified, empty state
- `frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx` — modified, 20 tests pass
- `CHANGELOG.md` — modified, Fixed bullet added
- `.planning/milestones/v1.18-phases/92-custom-date-range-filter/92-CONTEXT.md` — amended D-19
- Commits d6640124 and 24936db4 verified in git log

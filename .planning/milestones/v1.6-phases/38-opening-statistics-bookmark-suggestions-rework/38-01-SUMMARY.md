---
phase: 38-opening-statistics-bookmark-suggestions-rework
plan: 01
subsystem: ui, api
tags: [react, fastapi, zobrist, typescript, pydantic, chess]

# Dependency graph
requires:
  - phase: 37-openings-reference-table-redesign
    provides: MostPlayedOpeningsTable component, most-played openings endpoint, SQL-side WDL
  - phase: 36-most-played-openings
    provides: GET /stats/most-played-openings endpoint, useMostPlayedOpenings hook
provides:
  - full_hash field on OpeningWDL backend response (enables synthetic bookmark construction)
  - Statistics tab sections reordered: Results by Opening, Win Rate Over Time, Most Played White, Most Played Black
  - Default chart data from top 3 most-played openings per color when user has no bookmarks
affects: 38-02

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Synthetic PositionBookmarkResponse entries from OpeningWDL for chart reuse without real bookmarks
    - chartBookmarks pattern: real bookmarks or most-played defaults depending on bookmark count

key-files:
  created: []
  modified:
    - app/schemas/stats.py
    - app/services/stats_service.py
    - frontend/src/types/stats.ts
    - frontend/src/pages/Openings.tsx
    - tests/test_stats_router.py

key-decisions:
  - "full_hash computed server-side from FEN using python-chess Board + compute_hashes — avoids duplicate Zobrist logic on frontend"
  - "DEFAULT_CHART_LIMIT = 3 openings per color as default chart data — balances chart readability and data richness"
  - "chartBookmarks = bookmarks.length > 0 ? bookmarks : defaultChartEntries — clean fallback with no empty state message"
  - "Synthetic bookmark IDs use negative integers (-(i+1)) to avoid collision with real bookmark IDs"

patterns-established:
  - "Pattern: synthetic PositionBookmarkResponse from OpeningWDL — construct entries with negative IDs, full_hash as target_hash, match_side='both'"

requirements-completed: [STAT-01, STAT-02]

# Metrics
duration: 12min
completed: 2026-03-29
---

# Phase 38 Plan 01: Opening Statistics & Bookmark Suggestions Rework Summary

**`full_hash` added to OpeningWDL backend response; Statistics tab reordered with charts populated from top 3 most-played openings per color when no bookmarks exist**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-29T09:30:00Z
- **Completed:** 2026-03-29T09:42:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Backend `OpeningWDL` Pydantic schema and TypeScript interface both include `full_hash: str` field computed from the FEN via `compute_hashes`
- Statistics tab sections reordered to: Results by Opening, Win Rate Over Time, Most Played as White, Most Played as Black
- When user has no bookmarks, top 3 white + top 3 black most-played openings become synthetic `PositionBookmarkResponse` entries driving both the WDL bar chart and Win Rate Over Time chart
- "No bookmarks yet" empty state removed — charts now always show data (from bookmarks or defaults)
- All 471 backend tests pass, TypeScript build succeeds

## Task Commits

1. **Task 1: Add full_hash to OpeningWDL backend response** - `dced612` (feat)
2. **Task 2: Reorder Statistics sections and implement default chart data** - `00d09f5` (feat)

## Files Created/Modified
- `app/schemas/stats.py` - Added `full_hash: str` field to `OpeningWDL` Pydantic model
- `app/services/stats_service.py` - Added `chess_lib` and `compute_hashes` imports; computes full_hash from FEN in `rows_to_openings()`
- `frontend/src/types/stats.ts` - Added `full_hash: string` to `OpeningWDL` TypeScript interface
- `frontend/src/pages/Openings.tsx` - Added `DEFAULT_CHART_LIMIT`, `defaultChartEntries`, `chartBookmarks`; updated `timeSeriesRequest`; reordered `statisticsContent`; renamed section headings
- `tests/test_stats_router.py` - Added `full_hash` field assertions to `test_most_played_openings_includes_pgn_fen`

## Decisions Made
- `full_hash` computed server-side from FEN using `chess.Board(fen)` + `compute_hashes()` — avoids any Zobrist logic duplication on the frontend
- `DEFAULT_CHART_LIMIT = 3` openings per color as default chart data — balances readability with coverage
- Synthetic bookmark IDs use negative integers `-(i+1)` to avoid collision with real bookmark IDs from the database
- `chartBookmarks` pattern: clean conditional with no empty state — charts always render something meaningful

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `full_hash` on `OpeningWDL` is now available for Plan 02 (bookmark suggestions rework), which uses it to construct suggestion entries
- Statistics tab section order and default chart data behavior are in place

---
*Phase: 38-opening-statistics-bookmark-suggestions-rework*
*Completed: 2026-03-29*

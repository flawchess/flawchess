---
phase: 38-opening-statistics-bookmark-suggestions-rework
plan: 02
subsystem: ui
tags: [react, typescript, localStorage, position-bookmarks, chess]

# Dependency graph
requires:
  - phase: 38-01
    provides: full_hash on OpeningWDL, mostPlayedData in Openings.tsx, defaultChartEntries pattern
provides:
  - SuggestionsModal derives suggestions client-side from mostPlayedData (no backend call)
  - PositionBookmarkCard with chart-enable toggle, 72px minimap, button row below piece filter
  - chartEnabledMap persisted in localStorage, filters chartBookmarks in Statistics tab
  - Position Bookmarks popover updated with Piece filter and chart toggle explanations
  - Dead frontend suggestion code removed (usePositionSuggestions, getSuggestions, PositionSuggestion type)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - localStorage per-bookmark toggle with version counter to trigger useMemo recompute
    - Client-side suggestion filtering by comparing full_hash against existing bookmark target_hash

key-files:
  created: []
  modified:
    - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/hooks/usePositionBookmarks.ts
    - frontend/src/api/client.ts
    - frontend/src/types/position_bookmarks.ts

key-decisions:
  - "SuggestionsModal uses mostPlayedData prop directly — no backend suggestions endpoint call"
  - "chartToggleVersion state counter forces chartEnabledMap useMemo recompute without storing toggle state in React state"
  - "Dashboard.tsx wired with same chart toggle pattern (Rule 3 fix) to satisfy PositionBookmarkList prop contract"

patterns-established:
  - "Pattern: localStorage version counter — increment counter state to re-trigger useMemo that reads localStorage values"

requirements-completed: [STAT-03, STAT-04, STAT-05, STAT-06]

# Metrics
duration: 25min
completed: 2026-03-29
---

# Phase 38 Plan 02: Opening Statistics & Bookmark Suggestions Rework Summary

**SuggestionsModal reworked to use mostPlayedData client-side; bookmark cards redesigned with chart-enable toggle (72px minimap, button row), toggle state persisted in localStorage**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-29T10:00:00Z
- **Completed:** 2026-03-29T10:25:00Z
- **Tasks:** 2 completed (Task 3 awaiting human verification)
- **Files modified:** 8

## Accomplishments
- SuggestionsModal now derives suggestions from `mostPlayedData` prop, filtering already-bookmarked positions by `full_hash` — no backend API call on open
- PositionBookmarkCard redesigned: MiniBoard enlarged from 60px to 72px, stacked load/delete removed, new button row (chart toggle, load, delete) added below piece filter
- Chart-enable toggle persists per bookmark in localStorage; `chartBookmarks` in Openings.tsx filters by `chartEnabledMap` when real bookmarks exist
- `useDeletePositionBookmark` cleans up localStorage on delete so re-created bookmarks default to enabled
- Dead frontend suggestion code removed: `usePositionSuggestions`, `getSuggestions`, `PositionSuggestion`, `SuggestionsResponse`
- Build and lint pass cleanly

## Task Commits

1. **Task 1: Rework SuggestionsModal, add chart-enable toggle to bookmark cards, redesign card layout** - `fe486b9` (feat)
2. **Task 2: Remove dead suggestion code from frontend** - `41e8823` (feat)
3. **Task 3: Visual verification of all changes** — checkpoint: awaiting human verification

## Files Created/Modified
- `frontend/src/components/position-bookmarks/SuggestionsModal.tsx` - Rewritten to accept `mostPlayedData` and `bookmarks` props; derives suggestions client-side; filters already-bookmarked openings
- `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` - Added `chartEnabled`/`onChartEnabledChange` props; MiniBoard 72px; button row with chart toggle, load, delete
- `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` - Added `chartEnabledMap` and `onChartEnabledChange` props; passes them to each card
- `frontend/src/pages/Openings.tsx` - Added localStorage helpers, `chartToggleVersion`, `chartEnabledMap`, `handleChartEnabledChange`; updated `chartBookmarks` filter; updated SuggestionsModal and PositionBookmarkList props; updated both desktop and mobile popover text
- `frontend/src/pages/Dashboard.tsx` - Wired `chartEnabledMap` and `handleChartEnabledChange` to satisfy PositionBookmarkList props (Rule 3 fix)
- `frontend/src/hooks/usePositionBookmarks.ts` - Added localStorage.removeItem in useDeletePositionBookmark; removed usePositionSuggestions
- `frontend/src/api/client.ts` - Removed getSuggestions from positionBookmarksApi; removed SuggestionsResponse import
- `frontend/src/types/position_bookmarks.ts` - Removed PositionSuggestion and SuggestionsResponse interfaces

## Decisions Made
- Suggestions derived client-side from `mostPlayedData` prop — avoids backend round-trip; data is already fetched for Statistics tab
- `chartToggleVersion` counter triggers `useMemo` recompute without duplicating toggle state in React state
- Dashboard.tsx needed the same chart toggle wiring to compile — kept implementation minimal (Rule 3 fix, no feature scope added)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wired chartEnabledMap in Dashboard.tsx**
- **Found during:** Task 1 (build verification)
- **Issue:** `PositionBookmarkList` is also used in `Dashboard.tsx` (not in plan's files list). The new required props `chartEnabledMap` and `onChartEnabledChange` caused a TypeScript build error.
- **Fix:** Added the same `getChartEnabled`/`setChartEnabledStorage` helpers, `chartToggleVersion` state, `chartEnabledMap` useMemo, and `handleChartEnabledChange` callback to Dashboard.tsx; passed props to PositionBookmarkList.
- **Files modified:** `frontend/src/pages/Dashboard.tsx`
- **Verification:** `npm run build` succeeded after fix
- **Committed in:** `fe486b9` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary fix for build correctness. No scope creep — same pattern as Openings.tsx, no extra features.

## Issues Encountered
- Worktree was missing 38-01 commits at start. Resolved by merging the `gsd/phase-38-opening-statistics-bookmark-suggestions-rework` branch into the worktree branch before proceeding.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All STAT-03 through STAT-06 requirements implemented
- Task 3 (visual verification) is a checkpoint awaiting human approval
- Once approved, Phase 38 is complete

---
*Phase: 38-opening-statistics-bookmark-suggestions-rework*
*Completed: 2026-03-29*

## Self-Check: PASSED

- FOUND: frontend/src/components/position-bookmarks/SuggestionsModal.tsx
- FOUND: frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
- FOUND: frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
- FOUND: frontend/src/pages/Openings.tsx
- FOUND commit fe486b9 (Task 1)
- FOUND commit 41e8823 (Task 2)

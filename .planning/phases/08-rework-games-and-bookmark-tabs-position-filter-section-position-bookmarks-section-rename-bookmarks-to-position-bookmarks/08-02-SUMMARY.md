---
phase: 08-rework-games-and-bookmark-tabs
plan: 02
subsystem: ui
tags: [react, typescript, position-bookmarks, charts, dnd-kit]

# Dependency graph
requires: []
provides:
  - "PositionBookmarkResponse, PositionBookmarkCreate, PositionBookmarkUpdate types in position_bookmarks.ts"
  - "usePositionBookmarks, useCreatePositionBookmark, useDeletePositionBookmark hooks in usePositionBookmarks.ts"
  - "positionBookmarksApi at /position-bookmarks path in api/client.ts"
  - "PositionBookmarkCard: compact single-row card with drag handle, editable label, Load and Delete buttons"
  - "PositionBookmarkList: DnD list with onLoad callback prop (no wdlStatsMap)"
  - "WinRateChart and WDLBarChart relocated to components/charts/"
affects: [08-03, 08-04, 08-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "position-bookmarks query key replaces bookmarks for TanStack Query cache"
    - "onLoad callback on PositionBookmarkCard instead of navigate() side effect"
    - "compact single-row bookmark card layout (no MiniBoard, no WDL)"

key-files:
  created:
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/hooks/usePositionBookmarks.ts
    - frontend/src/components/charts/WinRateChart.tsx
    - frontend/src/components/charts/WDLBarChart.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/pages/Bookmarks.tsx
    - frontend/src/pages/Stats.tsx

key-decisions:
  - "PositionBookmarkCard uses onLoad(bookmark) callback instead of navigate() — consumer decides navigation behavior"
  - "WinRateChart and WDLBarChart use PositionBookmarkResponse type from position_bookmarks.ts"
  - "Bookmarks.tsx simplified to minimal stub (full rework in 08-03)"
  - "Stats.tsx dead code imports updated to new paths to keep build passing"

patterns-established:
  - "position-bookmarks/ component directory for all position bookmark UI components"
  - "charts/ component directory for shared chart components"

requirements-completed: [REWORK-01, REWORK-04]

# Metrics
duration: 6min
completed: 2026-03-14
---

# Phase 08 Plan 02: Frontend Position-Bookmarks Rename Summary

**All frontend bookmark references renamed to position-bookmarks with relocated charts and simplified PositionBookmarkCard (no MiniBoard, no WDL bar)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-14T13:52:45Z
- **Completed:** 2026-03-14T13:58:35Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Created `position_bookmarks.ts` with renamed types and `usePositionBookmarks.ts` with renamed hooks using `position-bookmarks` query key
- Renamed `bookmarksApi` to `positionBookmarksApi` in api/client.ts with `/position-bookmarks` API paths
- Relocated WinRateChart and WDLBarChart from `components/bookmarks/` to `components/charts/` and updated type imports
- Created `PositionBookmarkCard`: compact single-row card (drag handle + editable label + Load + Delete, no MiniBoard or WDL)
- Created `PositionBookmarkList` with `onLoad` callback prop replacing `wdlStatsMap`
- Deleted all old files: bookmarks.ts, useBookmarks.ts, BookmarkCard.tsx, BookmarkList.tsx, old chart files, empty bookmarks/ directory

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename types, hooks, API client, and relocate chart components** - `a894428` (feat)
2. **Task 2: Rename and simplify PositionBookmarkCard and PositionBookmarkList components** - `97eaca2` (feat)

**Plan metadata:** (see final docs commit)

## Files Created/Modified
- `frontend/src/types/position_bookmarks.ts` - Renamed types: PositionBookmarkResponse, PositionBookmarkCreate, etc.
- `frontend/src/hooks/usePositionBookmarks.ts` - Renamed hooks with position-bookmarks query keys
- `frontend/src/api/client.ts` - positionBookmarksApi at /position-bookmarks paths
- `frontend/src/components/charts/WinRateChart.tsx` - Relocated chart, updated to PositionBookmarkResponse
- `frontend/src/components/charts/WDLBarChart.tsx` - Relocated chart, updated to PositionBookmarkResponse
- `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` - Simplified card: drag + label + Load + Delete
- `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` - DnD list with onLoad callback
- `frontend/src/pages/Openings.tsx` - Updated imports to new hook/chart paths
- `frontend/src/pages/Dashboard.tsx` - useCreateBookmark -> useCreatePositionBookmark (auto-fix)
- `frontend/src/pages/Bookmarks.tsx` - Simplified stub using new components (full rework in 08-03)
- `frontend/src/pages/Stats.tsx` - Dead code imports updated to new paths (auto-fix)

## Decisions Made
- PositionBookmarkCard uses `onLoad(bookmark)` callback instead of navigate() — makes the card reusable and decouples navigation from the card component
- WinRateChart and WDLBarChart use `PositionBookmarkResponse` type; they are now in `components/charts/` as shared chart components
- Stats.tsx dead code imports updated rather than deleted (deletion deferred to later cleanup)
- Bookmarks.tsx simplified to minimal stub for now — plan 08-03 will do the full rework

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated Dashboard.tsx import from deleted useBookmarks hook**
- **Found during:** Task 1 (types/hooks/API rename)
- **Issue:** Dashboard.tsx imported `useCreateBookmark` from `@/hooks/useBookmarks` which was being deleted
- **Fix:** Updated to `useCreatePositionBookmark` from `@/hooks/usePositionBookmarks`
- **Files modified:** frontend/src/pages/Dashboard.tsx
- **Verification:** npm run build passes
- **Committed in:** a894428 (Task 1 commit)

**2. [Rule 3 - Blocking] Updated Stats.tsx dead code imports from deleted modules**
- **Found during:** Task 1 (types/hooks/API rename)
- **Issue:** Stats.tsx (dead code) imported from @/hooks/useBookmarks, @/types/bookmarks, @/components/bookmarks/WinRateChart — all being deleted
- **Fix:** Updated all imports to use new position-bookmarks paths
- **Files modified:** frontend/src/pages/Stats.tsx
- **Verification:** npm run build passes
- **Committed in:** a894428 (Task 1 commit)

**3. [Rule 3 - Blocking] Simplified Bookmarks.tsx to remove dead wdlStatsMap logic**
- **Found during:** Task 2 (PositionBookmarkList no longer takes wdlStatsMap)
- **Issue:** Bookmarks.tsx had unused wdlStatsMap computation causing TypeScript TS6133 error
- **Fix:** Simplified Bookmarks.tsx to remove wdlStatsMap, timeSeriesRequest, and tsData (all unused now); full rework in 08-03
- **Files modified:** frontend/src/pages/Bookmarks.tsx
- **Verification:** npm run build passes with zero errors
- **Committed in:** 97eaca2 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 3 - blocking import fixes from deleted files)
**Impact on plan:** All auto-fixes required to keep build passing after file deletions. No scope creep.

## Issues Encountered
None — auto-fixes were straightforward import path updates.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All frontend types, hooks, and API client use `position-bookmarks` naming consistently
- PositionBookmarkCard and PositionBookmarkList ready for integration in 08-03
- WinRateChart and WDLBarChart ready for use from `components/charts/`
- Bookmarks.tsx is a minimal stub — plan 08-03 will fully rework the page

---
*Phase: 08-rework-games-and-bookmark-tabs*
*Completed: 2026-03-14*

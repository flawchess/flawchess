---
phase: 05-position-bookmarks-and-w-d-l-comparison-charts
plan: "04"
subsystem: frontend
tags: [react, typescript, dnd-kit, tanstack-query, react-router, bookmarks]

requires:
  - phase: 05-01
    provides: Bookmark backend REST API (GET/POST/PUT/DELETE /bookmarks, PUT /bookmarks/reorder)
  - phase: 05-03
    provides: useBookmarks hooks, BookmarkResponse types, useChessGame.loadMoves

provides:
  - NavHeader with Analysis/Bookmarks tabs; active tab highlighted via useLocation()
  - /bookmarks route protected via ProtectedLayout with React Router Outlet
  - BookmarksPage: loading state, empty state (with link to Analysis), bookmark list
  - BookmarkList: @dnd-kit/sortable drag-and-drop with optimistic reorder + server sync
  - BookmarkRow: drag handle, inline label edit, [Load] navigation, [X] delete, optional WDL bar

affects:
  - 05-05 (WinRateChart will wire actual WDL stats into BookmarkRow.stats prop)

tech-stack:
  added:
    - "@dnd-kit/sortable@10.0.0"
  patterns:
    - "ProtectedLayout + Outlet pattern: NavHeader rendered once above Outlet, ProtectedLayout checks auth"
    - "Blur race condition fix: isDirtyRef tracks cancel state; onMouseDown preventDefault on action buttons"
    - "Optimistic reorder: BookmarkList maintains local items state, updates optimistically on drag, syncs from server via useEffect"
    - "loadMoves prerequisite: 05-03 loadMoves implemented inline before 05-04 tasks"

key-files:
  created:
    - frontend/src/pages/Bookmarks.tsx
    - frontend/src/components/bookmarks/BookmarkList.tsx
    - frontend/src/components/bookmarks/BookmarkRow.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/hooks/useChessGame.ts
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/hooks/useBookmarks.ts

key-decisions:
  - "ProtectedLayout replaces ProtectedRoute wrapper: single layout component with NavHeader + Outlet avoids duplicating header in each page"
  - "isDirtyRef for blur cancellation: a ref (not state) avoids re-renders; set true on Escape or action button mousedown, checked in onBlur to skip save"
  - "WDLBar stats prop optional: plan 05 will wire actual stats; BookmarkRow renders placeholder-free (no stats = no bar) until then"
  - "05-03 loadMoves implemented as prerequisite: useChessGame.loadMoves and Dashboard Bookmark button were missing from 05-03; implemented before 05-04 tasks"

patterns-established:
  - "NavHeader active tab: useLocation().pathname compared to route path, border-b-2 border-primary applied to active tab Button"
  - "Inline label edit: isEditing state + autoFocus input, save on blur unless isDirtyRef is true"

requirements-completed: [BKM-02, BKM-06, BKM-07]

duration: 5min
completed: 2026-03-13
---

# Phase 5 Plan 04: Bookmarks UI Summary

**Full /bookmarks page with NavHeader routing, @dnd-kit drag-and-drop sortable list, inline label editing, blur race condition handling, [Load] navigation to Analysis board, and [X] delete**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T09:05:04Z
- **Completed:** 2026-03-13T09:13:07Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Installed `@dnd-kit/sortable` (v10.0.0) as explicit dependency
- Updated `App.tsx` with `ProtectedLayout` component containing `NavHeader` + `<Outlet />` for both protected routes
- `NavHeader` renders Analysis and Bookmarks tabs; active tab uses `useLocation()` for highlight
- Created `BookmarksPage` with loading/empty states; empty state links back to Analysis
- Created `BookmarkList` with `DndContext` + `SortableContext`; optimistic drag reorder calls `onReorder`; `useEffect` syncs items when server refetches
- Created `BookmarkRow` with drag handle (`☰`), inline label edit, `[Load]` and `[X]` buttons
- Blur race condition handled via `isDirtyRef` + `onMouseDown preventDefault` on action buttons
- `[Load]` navigates to `/` with `location.state.bookmark` including moves, color, matchSide
- `[X]` calls `useDeleteBookmark().mutate(id)` directly without confirmation

## Prerequisite Work (05-03 incomplete)

Before executing 05-04, completed missing 05-03 items:
- Added `loadMoves(sans: string[])` to `ChessGameState` interface and `useChessGame` hook implementation
- Added `handleBookmark` callback + `activeBookmarkId` state + `★ Bookmark / Save` button to `DashboardPage`
- Added `useEffect` to hydrate board from `location.state.bookmark` on mount

## Task Commits

Each task committed atomically:

1. **Prerequisite: 05-03 missing loadMoves + Dashboard Bookmark button** - `41bba6e`
2. **Task 1: @dnd-kit/sortable install, App.tsx routing/nav, BookmarksPage shell** - `715a92b`
3. **Task 2: BookmarkList and BookmarkRow** - `7f826b8`

## Files Created/Modified

- `frontend/src/App.tsx` - ProtectedLayout + NavHeader + /bookmarks route via Outlet pattern
- `frontend/src/pages/Bookmarks.tsx` - BookmarksPage with loading/empty states
- `frontend/src/components/bookmarks/BookmarkList.tsx` - DndContext sortable list with optimistic reorder
- `frontend/src/components/bookmarks/BookmarkRow.tsx` - Drag handle, inline edit, Load/Delete, optional WDL bar
- `frontend/src/hooks/useChessGame.ts` - Added loadMoves method (05-03 prerequisite)
- `frontend/src/pages/Dashboard.tsx` - Added Bookmark button and bookmark state (05-03 prerequisite)

## Decisions Made

- **ProtectedLayout + Outlet**: Cleaner than per-page NavHeader duplication; auth check in single location
- **isDirtyRef for blur cancel**: Ref prevents re-renders; set on Escape key or action button mousedown; checked in onBlur to skip save API call
- **WDL stats optional**: No stats rendered until plan 05-05 wires `POST /analysis/time-series` data
- **05-03 prerequisite implemented inline**: useChessGame.loadMoves and Dashboard Bookmark button were not committed in 05-03 SUMMARY; implemented before 05-04 tasks with separate commits

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 05-03 prerequisites missing**
- **Found during:** Pre-execution check of 05-04 dependencies
- **Issue:** `useChessGame.loadMoves` and Dashboard Bookmark button were absent (05-03 work was partially committed but incomplete); 05-04 depends on these for [Load] navigation
- **Fix:** Implemented `loadMoves` in `useChessGame.ts` and full Bookmark button logic in `Dashboard.tsx` before starting 05-04 tasks
- **Files modified:** `frontend/src/hooks/useChessGame.ts`, `frontend/src/pages/Dashboard.tsx`
- **Commit:** `41bba6e`

## Issues Encountered
None in 05-04 tasks. Pre-existing lint errors in shadcn/ui files (`button.tsx`, `badge.tsx`, etc.) are out-of-scope.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `/bookmarks` page accessible from NavHeader with working navigation
- Drag-and-drop reorder calls `PUT /bookmarks/reorder` via `useReorderBookmarks`
- Inline label edit calls `PUT /bookmarks/{id}` via `useUpdateBookmarkLabel`
- `[Load]` wires bookmark to Analysis board via `location.state`
- `BookmarkRow.stats` prop ready for plan 05-05 to inject WDL stats

## Self-Check: PASSED

All files verified:
- FOUND: frontend/src/pages/Bookmarks.tsx
- FOUND: frontend/src/components/bookmarks/BookmarkList.tsx
- FOUND: frontend/src/components/bookmarks/BookmarkRow.tsx

All commits verified:
- FOUND: 41bba6e (feat: 05-03 prerequisites — loadMoves + Dashboard Bookmark button)
- FOUND: 715a92b (feat: Task 1 — @dnd-kit/sortable + routing + BookmarksPage shell)
- FOUND: 7f826b8 (feat: Task 2 — BookmarkList and BookmarkRow)

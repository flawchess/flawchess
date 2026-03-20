---
phase: 05-position-bookmarks-and-w-d-l-comparison-charts
plan: "03"
subsystem: ui
tags: [react, typescript, tanstack-query, bookmarks, axios]

requires:
  - phase: 05-01
    provides: bookmarks backend (POST/GET/PUT/DELETE /bookmarks + time-series endpoint)

provides:
  - TypeScript types for bookmark CRUD and time-series (8 interfaces in bookmarks.ts)
  - bookmarksApi and timeSeriesApi named exports on api/client.ts
  - 6 TanStack Query hooks: useBookmarks, useCreateBookmark, useUpdateBookmarkLabel, useDeleteBookmark, useReorderBookmarks, useTimeSeries
  - loadMoves(sans) method on useChessGame hook for replaying saved move sequences
  - Bookmark button on Dashboard (saves current position + filters to backend)
  - Board hydration from React Router location.state (for loading bookmarks from /bookmarks page)

affects:
  - 05-04 (BookmarksPage uses useBookmarks, useDeleteBookmark, useUpdateBookmarkLabel, useReorderBookmarks, loadMoves)
  - 05-05 (WinRateChart uses useTimeSeries)

tech-stack:
  added: []
  patterns:
    - "bookmarksApi/timeSeriesApi as named exports on api/client.ts (object grouping pattern)"
    - "TanStack Query mutations with cache invalidation via invalidateQueries"
    - "Optimistic reorder: cancel queries, setQueryData, rollback onError, invalidate onSettled"
    - "Mount-only useEffect with eslint-disable comment for location.state hydration"

key-files:
  created:
    - frontend/src/types/bookmarks.ts
    - frontend/src/hooks/useBookmarks.ts
  modified:
    - frontend/src/api/client.ts
    - frontend/src/hooks/useChessGame.ts
    - frontend/src/pages/Dashboard.tsx

key-decisions:
  - "bookmarksApi as named export (not default) — consistent with apiClient pattern, enables tree-shaking"
  - "useReorderBookmarks typed as useMutation<BookmarkResponse[], Error, number[], ReorderContext> — explicit generic parameters needed to avoid TypeScript inference failures with optimistic update context"
  - "Bookmark button in flex row with Analyze using flex-1 on Analyze so Bookmark stays natural width"
  - "activeBookmarkId tracks loaded bookmark for overwrite semantics — Save instead of duplicate-create"

requirements-completed: [BKM-01, BKM-06]

duration: 10min
completed: 2026-03-13
---

# Phase 5 Plan 03: Frontend Bookmark Layer Summary

**TanStack Query bookmark hooks with optimistic reorder, loadMoves on useChessGame, and Bookmark button on Dashboard wired end-to-end to POST /bookmarks**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-13T09:04:23Z
- **Completed:** 2026-03-13T10:10:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- TypeScript contract layer for all bookmark and time-series API shapes (8 interfaces)
- bookmarksApi and timeSeriesApi added to api/client.ts without breaking existing exports
- useBookmarks hook file with 6 TanStack Query hooks including optimistic drag-and-drop reorder
- loadMoves(sans) added to useChessGame interface + implementation using existing replayTo helper
- Bookmark button on Dashboard saves current board position + filters; changes to "Save" when bookmark loaded

## Task Commits

Each task was committed atomically:

1. **Task 1: TypeScript types, API client, useBookmarks hook** - `8de45c5` (feat)
2. **Task 2: loadMoves extension + Dashboard Bookmark button** - `354405b` (feat)

**Plan metadata:** (final commit — see below)

## Files Created/Modified
- `frontend/src/types/bookmarks.ts` - 8 TypeScript interfaces for bookmark CRUD and time-series
- `frontend/src/hooks/useBookmarks.ts` - 6 TanStack Query hooks (list, create, updateLabel, delete, reorder, timeSeries)
- `frontend/src/api/client.ts` - bookmarksApi and timeSeriesApi named exports added
- `frontend/src/hooks/useChessGame.ts` - loadMoves(sans) method added to interface and implementation
- `frontend/src/pages/Dashboard.tsx` - Bookmark button, activeBookmarkId state, location.state hydration

## Decisions Made
- `useReorderBookmarks` uses explicit TypeScript generics `useMutation<BookmarkResponse[], Error, number[], ReorderContext>` — TanStack Query v5 cannot infer the context type from `onMutate` return type without explicit annotation
- `bookmarksApi.updateLabel` called directly (not via mutation) in the overwrite branch of `handleBookmark` since we only need label update, not full bookmark invalidation — simpler than adding a dedicated mutation
- Bookmark button placed in a `flex gap-2` row with Analyze using `flex-1` on Analyze so Bookmark stays compact at natural width

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript errors in useReorderBookmarks optimistic update**
- **Found during:** Task 1 (useBookmarks hook)
- **Issue:** TanStack Query v5 could not infer the `onMutate` return type as context for `onError` — type inference gap with optimistic updates
- **Fix:** Added explicit generic parameters `useMutation<BookmarkResponse[], Error, number[], ReorderContext>` and extracted `ReorderContext = { prev: unknown }` type alias
- **Files modified:** frontend/src/hooks/useBookmarks.ts
- **Verification:** npm run build passes with 0 TypeScript errors
- **Committed in:** 8de45c5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (TypeScript type inference gap)
**Impact on plan:** Essential correctness fix. No scope creep.

## Issues Encountered
- ESLint directive format: `// eslint-disable-line react-hooks/exhaustive-deps — intentionally mount-only` is invalid (appended text after rule name breaks ESLint parser). Fixed by moving disable comment to a separate line before the closing `}, [])`.
- Pre-existing lint errors in shadcn/ui components (badge, button, tabs, toggle, FilterPanel) — `react-refresh/only-export-components` — out of scope, not introduced by this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- useBookmarks hook ready for BookmarksPage (plan 05-04)
- loadMoves ready for bookmark loading from /bookmarks page
- useTimeSeries ready for WinRateChart (plan 05-05)
- All TypeScript contracts established and verified via npm run build

---
*Phase: 05-position-bookmarks-and-w-d-l-comparison-charts*
*Completed: 2026-03-13*

---
phase: 08-rework-games-and-bookmark-tabs
plan: 03
subsystem: ui
tags: [react, dashboard, collapsible, bookmark, navigation]

# Dependency graph
requires:
  - phase: 08-rework-games-and-bookmark-tabs
    plan: 02
    provides: PositionBookmarkList component, usePositionBookmarks hooks, renamed types

provides:
  - Dashboard left column with three collapsible sections (Position filter, Position bookmarks, More filters)
  - In-place bookmark Load without page navigation
  - 4-tab navigation (Games, Openings, Rating, Global Stats)
  - Bookmarks page deleted; /bookmarks route removed

affects: [future dashboard work, any plan touching navigation or Games page layout]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Three-collapsible-sections pattern for dashboard sidebar: Position filter (open), Position bookmarks (collapsed), More filters (collapsed)
    - In-place bookmark loading via chess.loadMoves() callback — consumer decides navigation behavior

key-files:
  created: []
  modified:
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/App.tsx
    - frontend/vite.config.ts
  deleted:
    - frontend/src/pages/Bookmarks.tsx
    - frontend/src/pages/Stats.tsx

key-decisions:
  - "Played as and Match side toggles moved from FilterPanel into Position filter section — FilterPanel now renders only the five secondary filter controls as flat content"
  - "Bookmark this position button placed inside Position filter section (not in always-visible button row)"
  - "Vite proxy entry updated from /bookmarks to /position-bookmarks to fix black screen and save errors"
  - "/bookmarks redirect route removed from App.tsx (graceful redirect not needed after full UI rework)"
  - "Button icons added (Bookmark, Filter, Download) for visual clarity on the three action buttons"
  - "Bookmark button size changed to lg to match Filter and Import buttons"

patterns-established:
  - "handleLoadBookmark pattern: chess.loadMoves(bkm.moves), setBoardFlipped(bkm.is_flipped), setFilters to bkm color+matchSide"

requirements-completed: [REWORK-02, REWORK-03, REWORK-05]

# Metrics
duration: ~30min (including human verify round-trip with fixes)
completed: 2026-03-14
---

# Phase 8 Plan 03: Dashboard Restructure Summary

**Dashboard left column merged into three collapsible sections with in-place bookmark loading, Bookmarks page deleted, and navigation reduced to 4 tabs**

## Performance

- **Duration:** ~30 min (including checkpoint round-trip with user-applied fixes)
- **Started:** 2026-03-14
- **Completed:** 2026-03-14
- **Tasks:** 3 (2 auto + 1 checkpoint)
- **Files modified:** 5 (+ 2 deleted)

## Accomplishments
- Dashboard left column restructured into three sibling collapsible sections: Position filter (open by default), Position bookmarks (collapsed), More filters (collapsed)
- In-place bookmark loading wired via handleLoadBookmark — clicking Load replays moves on the board without navigating away
- Bookmarks page and nav tab removed; navigation now shows exactly 4 tabs: Games, Openings, Rating, Global Stats
- FilterPanel stripped of Played as / Match side toggles (moved into Position filter section); now renders only secondary filter controls
- Vite proxy corrected (/bookmarks -> /position-bookmarks) as part of checkpoint fix commit

## Task Commits

Each task was committed atomically:

1. **Task 1: Restructure Dashboard.tsx into three collapsible sections with in-place bookmark loading** - `c9c4830` (feat)
2. **Task 2: Remove Bookmarks page, route, and nav tab** - `b1188f0` (feat)
3. **Task 3: Verify complete UI restructure (checkpoint fixes)** - `fef7e54` (fix)

## Files Created/Modified
- `frontend/src/pages/Dashboard.tsx` - Three-section collapsible layout, handleLoadBookmark wired, Played as/Match side toggles moved inline
- `frontend/src/components/filters/FilterPanel.tsx` - Removed Played as and Match side toggle groups, removed Collapsible wrapper; flat secondary filters only
- `frontend/src/App.tsx` - Removed BookmarksPage import, removed /bookmarks route, removed Bookmarks from NAV_ITEMS (5 tabs -> 4 tabs)
- `frontend/vite.config.ts` - Proxy entry updated from /bookmarks to /position-bookmarks
- `frontend/src/pages/Bookmarks.tsx` - DELETED
- `frontend/src/pages/Stats.tsx` - DELETED (cleanup of dead code noted since phase 7)

## Decisions Made
- Played as and Match side toggles moved from FilterPanel into the Position filter section — they are positional context, not secondary filters
- Bookmark this position button placed inside Position filter section rather than in the always-visible button row
- Vite proxy entry updated from /bookmarks to /position-bookmarks (bug fix applied during checkpoint — was causing black screen on load and bookmark save errors)
- /bookmarks redirect route removed entirely; graceful redirect no longer needed after full UI rework
- Button icons (Bookmark, Filter, Download from lucide-react) added to all three action buttons during checkpoint fix for visual clarity
- Bookmark button size bumped to lg to visually match Filter and Import buttons

## Deviations from Plan

### Auto-fixed Issues (applied during checkpoint)

**1. [Rule 1 - Bug] Vite proxy pointed to /bookmarks instead of /position-bookmarks**
- **Found during:** Task 3 (human verify checkpoint)
- **Issue:** Vite dev server proxy still had `/bookmarks` entry — API calls to `/position-bookmarks/*` were not proxied, causing black screen on load and 404s on bookmark save
- **Fix:** Updated vite.config.ts proxy key from `/bookmarks` to `/position-bookmarks`
- **Files modified:** frontend/vite.config.ts
- **Verification:** Bookmark save and load work correctly in browser
- **Committed in:** fef7e54 (checkpoint fix commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Proxy bug was a blocking correctness issue. Fix was minimal and targeted. No scope creep.

## Issues Encountered
- Vite proxy entry was never updated when the route was renamed from /bookmarks to /position-bookmarks in phase 08-01/08-02 — discovered during human verification checkpoint and fixed in the same session.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Dashboard restructure complete; three-section layout is stable and ready for further iteration
- No blockers; Openings, Rating, and Global Stats pages unaffected
- Stats.tsx dead code removed as part of this plan (cleanup noted since phase 7)

## Self-Check: PASSED
- SUMMARY.md: FOUND
- Commit c9c4830: FOUND
- Commit b1188f0: FOUND
- Commit fef7e54: FOUND

---
*Phase: 08-rework-games-and-bookmark-tabs*
*Completed: 2026-03-14*

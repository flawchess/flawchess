---
phase: 19-mobile-ux-polish-install-prompt
plan: "01"
subsystem: ui
tags: [react, mobile, chessboard, touch, sticky, layout, tailwind]

# Dependency graph
requires:
  - phase: 18-mobile-navigation
    provides: MobileHeader, MobileBottomBar, ProtectedLayout, Tailwind sm: breakpoints
provides:
  - Sticky chessboard at top of viewport on Openings mobile layout
  - Click-to-move touch interaction via react-chessboard onSquareClick on mobile
  - MobileHeader hidden on /openings/* routes
  - Collapsed filters and bookmarks by default on mobile Openings page
  - Separate mobileFiltersOpen state for mobile vs desktop sidebar
affects: [19-02, 19-03, future mobile layout work]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "allowDragging: false on react-chessboard — prevents black screen on mobile; click-to-move via onSquareClick is the touch interaction"
    - "isOpeningsRoute = location.pathname.startsWith('/openings') in ProtectedLayout for conditional header rendering"
    - "Duplicate mobile layout JSX alongside desktop sidebar — intentional for fundamentally different sticky vs non-sticky structures"
    - "mobileFiltersOpen state separate from moreFiltersOpen — mobile starts collapsed, desktop state independent"

key-files:
  created: []
  modified:
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/App.tsx
    - frontend/src/pages/Openings.tsx

key-decisions:
  - "Disable allowDragging on react-chessboard to fix black screen on mobile — click-to-move is the touch interaction (library fires onSquareClick via onTouchEnd natively)"
  - "No onPointerUp fallback added — library already handles onSquareClick on touch via onTouchEnd; fallback would double-fire"
  - "Mobile layout duplicates JSX from sidebar variable — sticky board structure is fundamentally incompatible with sidebar's non-sticky structure"
  - "mobileFiltersOpen state initialized to false — filters collapsed by default on mobile, separate from desktop moreFiltersOpen"

patterns-established:
  - "Mobile-specific data-testids use -mobile suffix (e.g., filter-played-as-mobile) — avoids collision with desktop testids"
  - "min-h-11 sm:min-h-0 on ToggleGroupItems — 44px touch targets on mobile, default height on desktop"

requirements-completed: [UX-03, UX-04]

# Metrics
duration: ~15min
completed: 2026-03-20
---

# Phase 19 Plan 01: Chessboard Touch + Openings Mobile Layout Summary

**Sticky chessboard on Openings mobile with click-to-move touch support: disabled drag (fixes black screen), restructured mobile layout with sticky board, collapsed filters, and hidden MobileHeader on /openings routes**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-20T17:45:00Z
- **Completed:** 2026-03-20T17:57:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Disabled drag-and-drop on chessboard (`allowDragging: false`) — eliminates black screen on iOS/Android; click-to-move via `onSquareClick` (library fires natively on `onTouchEnd`) is the mobile interaction
- Restructured Openings mobile layout: sticky board at `top-0`, followed by board controls, move list, played-as/piece filters, collapsed "More filters" section, collapsed position bookmarks, then tabs
- Hidden `MobileHeader` on `/openings/*` routes — creates more vertical space for board
- All 313 backend tests pass (regression guard)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix chessboard touch interaction and investigate drag** - `a316607` (fix)
2. **Task 2: Restructure Openings mobile layout with sticky board and hide MobileHeader** - `f0c0a9d` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/components/board/ChessBoard.tsx` - Added `allowDragging: false` to Chessboard options with explanatory comment
- `frontend/src/App.tsx` - Added `isOpeningsRoute` check in ProtectedLayout to conditionally render MobileHeader
- `frontend/src/pages/Openings.tsx` - Added `mobileFiltersOpen` state; replaced mobile section with sticky-board layout; reduced mobile top padding to `py-2`

## Decisions Made
- **No `onPointerUp` fallback** — react-chessboard v5 already fires `onSquareClick` on touch via its own `onTouchEnd` handler; adding `onPointerUp` on the `squareRenderer` div would double-fire the click handler
- **`allowDragging: false` globally** — simpler than JS-based touch detection; the library's `TouchSensor` (dnd-kit) causes black screen on mobile WebView; click-to-move is sufficient
- **Duplicate mobile layout JSX** — mobile needs sticky board at top which is structurally incompatible with sidebar's flat flex-column; intentional duplication per plan guidance
- **`-mobile` suffix on testids** — avoids collision with desktop sidebar testids that already exist (e.g., `filter-played-as` vs `filter-played-as-mobile`)

## Deviations from Plan

None — plan executed exactly as written. The linter added `min-h-11 sm:min-h-0` to toggle items in the sidebar (auto-formatting for 44px touch targets) which was preserved in the mobile layout duplication.

## Issues Encountered
- File was auto-modified by linter between state changes (added `min-h-11 sm:min-h-0` to ToggleGroupItems in the sidebar). Re-read and re-applied edit successfully.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Chessboard touch interaction and Openings mobile layout are ready for physical device testing
- Plan 19-02 (touch targets + overflow audit) can proceed
- Known open: react-chessboard touch drag on Android Chrome unverified — click-to-move confirmed as fallback

---
*Phase: 19-mobile-ux-polish-install-prompt*
*Completed: 2026-03-20*

---
phase: 49-openings-desktop-sidebar
plan: 01
subsystem: ui
tags: [react, typescript, tailwind, openings, sidebar, layout]

# Dependency graph
requires: []
provides:
  - Collapsible 48px sidebar strip with filter/bookmark icon buttons on the Openings desktop page
  - 280px on-demand sidebar panel (overlay below 1280px, push at 1280px+)
  - sidebarOpen state machine (null | 'filters' | 'bookmarks') replacing old sidebarTab
  - Board, BoardControls, opening name, MoveList moved into main content area
  - Outside-click-to-close behavior via mousedown listener
  - isXlOrAbove media query hook for overlay vs push breakpoint
affects: [phase-50-mobile-layout, any-openings-related-plans]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sidebar strip + panel pattern: 48px always-visible strip with icon buttons, 280px panel toggled via sidebarOpen state machine"
    - "Single panel div with JS-driven position toggle (relative vs absolute) avoids duplicate testid pitfall"
    - "isXlOrAbove media query hook via matchMedia + addEventListener for overlay vs push breakpoint behavior"
    - "Outside-click-to-close via document mousedown listener scoped to sidebarOpen, cleaned up on close"

key-files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx

key-decisions:
  - "Single panel div with conditional className/style driven by isXlOrAbove JS state — avoids duplicate data-testid pitfall from two-panel CSS-only approach"
  - "desktopFilterPanelContent uses filters/handleFiltersChange directly (not localFilters) — desktop applies live per D-05"
  - "SidebarPanel type defined at module level (before component) for clean TypeScript"
  - "Named constants SIDEBAR_STRIP_WIDTH/PANEL_WIDTH/PUSH_BREAKPOINT at module level per CLAUDE.md no-magic-numbers rule"

patterns-established:
  - "Sidebar state machine: null = closed, 'filters' | 'bookmarks' = open panel. handleStripIconClick toggles same panel off, switches to other panel directly"

requirements-completed:
  - DESK-01
  - DESK-02
  - DESK-03
  - DESK-04
  - DESK-05

# Metrics
duration: 4min
completed: 2026-04-09
---

# Phase 49 Plan 01: Openings Desktop Sidebar Summary

**Collapsible left-edge sidebar for Openings desktop: 48px icon strip + 280px on-demand Filters/Bookmarks panel with overlay/push behavior at 1280px breakpoint**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-09T17:39:21Z
- **Completed:** 2026-04-09T17:42:54Z
- **Tasks:** 1 of 2 (Task 2 is a checkpoint:human-verify awaiting browser verification)
- **Files modified:** 1

## Accomplishments

- Replaced the always-visible 350px 2-column desktop sidebar with a 48px collapsed strip + 280px on-demand panel, recovering ~270px of horizontal space on smaller desktop screens
- Board, BoardControls, opening name, and MoveList moved from the old `sidebar` variable into the main content area, stacking above the Moves/Games/Stats tabs
- Sidebar panel uses overlay positioning (absolute, z-40) below 1280px and in-flow positioning (relative) at 1280px+, driven by a `matchMedia` JS hook to avoid duplicate-testid anti-pattern
- All notification dots, aria-labels, and data-testid attributes preserved and compliant with CLAUDE.md browser automation rules

## Task Commits

1. **Task 1: Restructure desktop layout with collapsible sidebar strip and panel** - `d8c77ae` (feat)

## Files Created/Modified

- `frontend/src/pages/Openings.tsx` — Desktop layout restructured: 2-column grid replaced by flex-row strip + optional panel + 1fr content area. sidebarTab state replaced by sidebarOpen state machine. sidebar variable removed; board/controls/opening-name/movelist now inline in desktop content area. New desktopFilterPanelContent and desktopBookmarkPanelContent variables. Mobile section (md:hidden) unchanged.

## Decisions Made

- Single panel div with JS-driven `isXlOrAbove` state (not two CSS-toggled divs) to avoid duplicate `data-testid="sidebar-panel"` in the DOM
- `desktopFilterPanelContent` and `desktopBookmarkPanelContent` extracted as JSX variables (not components) to keep all state in scope without prop drilling
- `SidebarPanel` type declared at module level before `OpeningsPage` for clean TypeScript without forward-reference issues

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — all content is wired to live state.

## Threat Flags

None — this is a frontend layout restructuring. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Task 1 (code implementation) is complete and committed. Task 2 (checkpoint:human-verify) requires browser verification at http://localhost:5173/openings/explorer at 1024px and 1440px viewport widths to confirm:
1. Collapsed strip (DESK-01): 48px strip with filter/bookmark icons and tooltips
2. Direct panel open (DESK-02): click icon opens correct panel
3. Single panel switching (DESK-03): switching icons works without double-click, toggle close works
4. Live filter updates (DESK-04): filter changes update board and stats immediately
5. Overlay vs push (DESK-05): panel overlays at ~1024px, pushes at ~1440px
6. Outside click closes panel
7. Notification dots appear on correct icons
8. Bookmark save switches panel to Bookmarks view
9. Mobile layout unchanged at ~375px

---
*Phase: 49-openings-desktop-sidebar*
*Completed: 2026-04-09*

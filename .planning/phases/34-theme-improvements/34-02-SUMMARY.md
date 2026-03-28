---
phase: 34-theme-improvements
plan: 02
subsystem: ui
tags: [tailwind, css-variables, react, typescript, navigation, theme]

# Dependency graph
requires:
  - 34-01 (CSS vars, charcoal-texture class, tabs brand variant)
provides:
  - Charcoal containers with noise texture on Dashboard, Openings, Endgames, Import pages
  - Collapsible sections unified as charcoal containers (header + content in one block)
  - Brand brown active subtab highlighting on Openings and Endgames (variant="brand")
  - Nav header without bottom border, active tab with bg-white/10 highlight
  - Logo and FlawChess text link to homepage (desktop and mobile)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "charcoal-texture applied as wrapper div around Collapsible blocks for unified dark container look"
    - "variant='brand' on TabsList activates brand-brown active subtab from Plan 01 infrastructure"
    - "bg-white/10 for active nav tab — subtle full-height background instead of underline"

key-files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/Import.tsx

key-decisions:
  - "Nav active tab uses bg-white/10 (subtle lighter background) instead of border-b-2 underline per D-11"
  - "Mobile brand wrapped in Link component (not span) to enable homepage navigation per D-13"
  - "charcoal-texture wraps each Collapsible block as a sibling div (not the Collapsible itself) for correct rounded container rendering"
  - "Import platform cards: border removed, replaced with charcoal-texture providing visual distinction"
  - "Endgames chart sections individually wrapped in charcoal-texture to avoid nesting issues with chart components"

requirements-completed: [THEME-02, THEME-05]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 34 Plan 02: Theme Application Summary

**Charcoal containers on all pages, brand subtab highlighting, nav header polish — visual consistency across Dashboard, Openings, Endgames, and Import**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-28T11:01:28Z
- **Completed:** 2026-03-28T11:06:30Z
- **Tasks:** 1 of 2 (Task 2 is human-verify checkpoint)
- **Files modified:** 5

## Accomplishments

### Task 1: Navigation header polish + charcoal containers on all pages (committed `47dd209`)

**App.tsx (NavHeader + MobileHeader):**
- Removed `border-b border-border` from both NavHeader and MobileHeader `<header>` elements (D-12)
- Changed active tab className from `border-b-2 border-primary rounded-none font-medium` to `self-stretch rounded-none font-medium bg-white/10` (D-11)
- Wrapped logo img + "FlawChess" span in `<Link to="/" data-testid="nav-home">` on desktop (D-13)
- Replaced `<span data-testid="mobile-header-brand">` with `<Link to="/" data-testid="nav-home-mobile">` on mobile (D-13)

**Dashboard.tsx:**
- Wrapped all 3 Collapsibles (Position filter, Position bookmarks, More filters) in `<div className="charcoal-texture rounded-md p-2">` (D-03, D-14, D-15)

**Openings.tsx:**
- Wrapped desktop Position bookmarks Collapsible in charcoal-texture container; removed `bg-muted/50 hover:bg-muted! border border-border/40` from trigger button
- Wrapped desktop More filters Collapsible in charcoal-texture container; removed `bg-muted/50` styling from trigger
- Wrapped mobile More filters and Position bookmarks Collapsibles in charcoal-texture containers; updated trigger button classes
- Added `variant="brand"` to both desktop and mobile `<TabsList>` (D-09, D-10)

**Endgames.tsx:**
- Added `variant="brand"` to both desktop and mobile `<TabsList>` (D-09, D-10)
- Changed Accordion AccordionItem from `border rounded-md border-border px-4` to `charcoal-texture rounded-md px-4`
- Wrapped each chart section (EndgamePerformanceSection, EndgameConvRecovTimelineChart, EndgameWDLChart, EndgameConvRecovChart, EndgameTimelineChart) in `<div className="charcoal-texture rounded-md">` (D-03)

**Import.tsx:**
- Changed both platform card divs (chess.com and lichess) from `rounded-md border px-3 py-2` to `charcoal-texture space-y-2 rounded-md px-3 py-2` (D-03)

## Task Commits

1. **Task 1: Nav header polish + charcoal containers on all pages** - `47dd209` (feat)

## Files Created/Modified

- `frontend/src/App.tsx` - NavHeader border removed, active tab bg-white/10, logo+brand wrapped in Link; MobileHeader border removed, brand wrapped in Link
- `frontend/src/pages/Dashboard.tsx` - All 3 Collapsibles wrapped in charcoal-texture containers
- `frontend/src/pages/Openings.tsx` - Collapsibles in charcoal-texture (desktop+mobile), bg-muted/50 removed from triggers, TabsList variant="brand" (desktop+mobile)
- `frontend/src/pages/Endgames.tsx` - TabsList variant="brand" (desktop+mobile), Accordion + chart sections in charcoal-texture
- `frontend/src/pages/Import.tsx` - Platform cards use charcoal-texture (border removed)

## Decisions Made

- Nav active tab uses `bg-white/10` (subtle lighter background) per D-11 — replaces `border-b-2` underline
- Mobile header brand wrapped in `<Link>` component (not span) per D-13
- Import platform cards: border removed in favor of charcoal-texture visual separation
- Endgames: each chart section wrapped individually to allow conditional rendering to work correctly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None.

## Current Status

Paused at **Task 2: Visual verification of all theme changes** (checkpoint:human-verify).

Run `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run dev` and visually verify:
1. Dashboard collapsibles have charcoal background with noise texture
2. Openings active subtab has brand brown (#8B5E3C) background with white text
3. Endgames active subtab has brand brown background
4. Import platform cards have charcoal background
5. Nav header has no white border at bottom; active tab shows lighter background (not underline)
6. Logo and "FlawChess" text link to homepage on desktop and mobile

## Known Stubs

None.

## Self-Check: PASSED

Files verified:
- `frontend/src/App.tsx` — exists, contains `bg-white/10`, `to="/" data-testid="nav-home"`, no `border-b border-border` in header
- `frontend/src/pages/Dashboard.tsx` — exists, contains 3x `charcoal-texture`
- `frontend/src/pages/Openings.tsx` — exists, contains 4x `charcoal-texture`, 2x `variant="brand"`
- `frontend/src/pages/Endgames.tsx` — exists, contains 6x `charcoal-texture`, 2x `variant="brand"`
- `frontend/src/pages/Import.tsx` — exists, contains 2x `charcoal-texture`
- Commit `47dd209` verified in git log

---
*Phase: 34-theme-improvements*
*Completed: 2026-03-28*

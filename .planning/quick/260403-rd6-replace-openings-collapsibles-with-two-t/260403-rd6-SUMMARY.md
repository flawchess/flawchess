---
phase: quick
plan: 260403-rd6
subsystem: frontend
tags: [openings, sidebar, tabs, ux]
dependency_graph:
  requires: []
  provides: [openings-sidebar-tabs]
  affects: [openings-page]
tech_stack:
  added: []
  patterns: [brand-variant Tabs replacing Collapsible sections]
key_files:
  modified:
    - frontend/src/pages/Openings.tsx
decisions:
  - InfoPopover for bookmarks moved to Save/Suggest buttons row (inline icon) rather than a header, keeping it compact
metrics:
  duration: "~8 minutes"
  completed: "2026-04-03T17:46:50Z"
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 260403-rd6: Replace Openings Collapsibles with Two-Tab Sidebar

**One-liner:** Desktop Openings sidebar collapsibles replaced with brand-variant Filters/Bookmarks tabs, exposing all controls in a single click.

## Objective

Replace the two collapsible sections (More Filters, Position Bookmarks) and the always-visible Played-as/Piece-filter toggles in the Openings desktop sidebar with a two-tab view. The Filters tab combines Played-as, Piece filter, and all FilterPanel controls. The Bookmarks tab holds the Save/Suggest buttons and bookmark list.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace desktop sidebar collapsibles with Filters/Bookmarks tabs | b20e01c | frontend/src/pages/Openings.tsx |

## Changes Made

### Task 1: Replace desktop sidebar collapsibles with Filters/Bookmarks tabs

**State changes:**
- Removed `positionBookmarksOpen` / `setPositionBookmarksOpen` state (no longer needed)
- Removed `moreFiltersOpen` / `setMoreFiltersOpen` state (no longer needed)
- Added `sidebarTab` state (default: `'filters'`) for tab selection

**Import changes:**
- Removed `Collapsible`, `CollapsibleTrigger`, `CollapsibleContent` (completely unused now)
- Removed `ChevronUp`, `ChevronDown` from lucide-react (completely unused now)

**Desktop sidebar restructure:**
- Removed: charcoal box with Played-as + Piece filter toggles (always-visible)
- Removed: "More filters" Collapsible containing FilterPanel
- Removed: separator between the two collapsibles
- Removed: "Position bookmarks" Collapsible containing Save/Suggest/list
- Added: brand-variant `Tabs` component with two tabs below the MoveList separator
  - **Filters tab** (`data-testid="sidebar-tab-filters"`): Played-as toggle, Piece filter toggle (with InfoPopover), separator, FilterPanel — all visible without expanding anything
  - **Bookmarks tab** (`data-testid="sidebar-tab-bookmarks"`): Save button, Suggest button, InfoPopover icon, PositionBookmarkList

**Mobile layout:** Completely untouched — still uses Drawer components for both filters and bookmarks.

**Verification:** `npm run build` passes, `npm run lint` clean, `npm run knip` clean.

## Deviations from Plan

### Minor Adjustments

**InfoPopover placement in Bookmarks tab:**
- Plan suggested placing the InfoPopover "as a small info icon next to the Save/Suggest buttons row or as a header line"
- Implemented as an icon button directly in the buttons row after the two brand buttons — compact and consistent with the mobile drawer pattern

No other deviations. Plan executed as written.

## Known Stubs

None.

## Self-Check: PASSED

- [x] `frontend/src/pages/Openings.tsx` modified (verified via git status)
- [x] Commit b20e01c exists and includes the changes
- [x] Build passes, lint clean, knip clean
- [x] Collapsible imports fully removed
- [x] ChevronUp/ChevronDown imports fully removed
- [x] Mobile layout (lines 826+) unchanged

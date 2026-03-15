---
phase: quick-22
plan: 01
subsystem: frontend
tags: [filter, ui, board-orientation]
dependency_graph:
  requires: []
  provides: [simplified-color-filter, board-auto-flip]
  affects: [Dashboard.tsx, FilterPanel.tsx]
tech_stack:
  added: []
  patterns: [non-nullable-filter-state, color-to-board-sync]
key_files:
  created: []
  modified:
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/components/filters/FilterPanel.tsx
decisions:
  - "Color filter is non-nullable (Color type, not Color | null) — Any option removed entirely"
  - "Board orientation synced to color filter: black=flipped, white=not flipped"
  - "handleLoadBookmark falls back to 'white' for legacy bookmarks with null color"
metrics:
  duration: 5min
  completed: "2026-03-15"
  tasks: 1
  files: 2
---

# Phase quick-22 Plan 01: Remove Any Option from Played as Filter Summary

**One-liner:** Simplified Played as filter to White/Black only with automatic board flip on color change.

## What Was Built

Removed the "Any" option from the Played as toggle filter and made color non-nullable throughout the filter state. The board now automatically flips to match the selected color (White = not flipped, Black = flipped) whenever the user changes the Played as filter.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove Any option from Played as filter and auto-flip board | a778447 | Dashboard.tsx, FilterPanel.tsx |

## Changes Made

### FilterPanel.tsx
- Changed `FilterState.color` from `Color | null` to `Color` (removed null union and `// null = any` comment)
- Changed `DEFAULT_FILTERS.color` from `null` to `'white'`

### Dashboard.tsx
- Removed `<ToggleGroupItem value="any" data-testid="filter-played-as-any">Any</ToggleGroupItem>`
- Updated ToggleGroup `value` prop from `filters.color ?? 'any'` to `filters.color`
- Updated `onValueChange` handler to set color AND call `setBoardFlipped(color === 'black')`
- Fixed `handleLoadBookmark`: changed `bkm.color ?? null` to `bkm.color ?? 'white'` for legacy bookmark support

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx tsc --noEmit`: passed (no type errors)
- `npm run build`: succeeded
- `npm run lint`: 5 pre-existing errors (shadcn/ui files + FilterPanel dual-export pattern, none introduced by this task)

## Self-Check: PASSED

- [x] `frontend/src/pages/Dashboard.tsx` — exists and modified
- [x] `frontend/src/components/filters/FilterPanel.tsx` — exists and modified
- [x] Commit a778447 — exists in git log

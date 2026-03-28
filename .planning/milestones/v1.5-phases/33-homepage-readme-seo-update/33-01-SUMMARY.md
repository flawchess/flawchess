---
phase: 33-homepage-readme-seo-update
plan: "01"
subsystem: frontend
tags: [homepage, content, ux, seo]
dependency_graph:
  requires: []
  provides: [restructured-homepage-5-sections, endgame-analytics-faq]
  affects: [frontend/src/pages/Home.tsx]
tech_stack:
  added: []
  patterns: [lucide-icons, tailwind-responsive-grid, shadcn-accordion]
key_files:
  created: []
  modified:
    - frontend/src/pages/Home.tsx
decisions:
  - "Removed SlidersHorizontal icon import (was used for filters section, now merged into cross-platform)"
  - "orientation field removed from FEATURES type — all sections now landscape with fixed 2fr/3fr grid ratio"
  - "gridCols computed from imagePosition alone — no conditional gridColsFlipped variable needed"
metrics:
  duration: "2m 29s"
  completed: "2026-03-27"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 33 Plan 01: Homepage Restructure Summary

Homepage restructured to showcase v1.5 endgame analytics alongside existing opening analysis — 5 consolidated feature sections, simplified layout, broadened hero copy, and new endgame FAQ.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Restructure FEATURES array and simplify layout | 47aa8e4 | frontend/src/pages/Home.tsx |

## What Was Built

### FEATURES array: 6 sections -> 5 consolidated sections

| Old | New |
|-----|-----|
| move-explorer | opening-explorer (merges move-explorer + scout) |
| scout | (merged into opening-explorer) |
| weaknesses | opening-comparison |
| filters | (merged into cross-platform) |
| system-openings | system-openings |
| (new) | endgame-analysis |
| cross-platform | cross-platform (with filters description) |

### Layout simplification

Removed `orientation` field from FEATURES type and all associated conditional grid logic (`isLandscape`, `gridCols`/`gridColsFlipped` pair, `max-w-xs` cap on portrait images). All 5 sections now use a single `gridCols` derived from `imagePosition`.

### Content updates

- Hero subtitle broadened from opening-only to mention endgame performance and cross-platform import
- Added "Endgame analytics" callout pill (4th pill)
- Added `faq-item-endgames` accordion item with endgame analytics description

### Icon changes

- Removed: `Eye` (scout section gone), `SlidersHorizontal` (filters section merged)
- Added: `BarChart2` for endgame-analysis section

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused SlidersHorizontal import**
- **Found during:** Task 1
- **Issue:** After removing the `filters` section from FEATURES, `SlidersHorizontal` was imported but not used — TypeScript build would have warned/failed
- **Fix:** Removed `SlidersHorizontal` from lucide-react import line
- **Files modified:** frontend/src/pages/Home.tsx
- **Commit:** 47aa8e4

## Known Stubs

The following screenshot paths are referenced in FEATURES but the actual PNG files do not yet exist (screenshots to be captured by human):

| Path | Section |
|------|---------|
| /screenshots/opening-explorer.png | Interactive Opening Explorer |
| /screenshots/opening-comparison.png | Opening Comparison and Tracking |
| /screenshots/system-openings.png | System Opening Grouping |
| /screenshots/endgame-analysis.png | Endgame Analysis |
| /screenshots/cross-platform.png | Cross-Platform with Powerful Filters |

These are intentional stubs per the research plan — the site loads with broken images during development. Screenshot capture is a human deliverable. Old screenshot files (board-and-move-explorer.png, chess-board-and-moves.png, win-rate-over-time.png, filters.png, position-bookmarks.png, game-import.png) can be removed once new screenshots are in place.

## Verification Results

- `npx tsc --noEmit` — passed
- `npm run build` — passed (exit 0, prerendered 2 pages)
- `grep -c "isLandscape\|orientation" Home.tsx` — 1 (only in a code comment, not executable code)
- `grep "endgame-analysis" Home.tsx` — found (slug + screenshot src)
- FEATURES entries: 5 (slugs: opening-explorer, opening-comparison, system-openings, endgame-analysis, cross-platform)

## Self-Check: PASSED

- frontend/src/pages/Home.tsx exists and modified
- Commit 47aa8e4 exists in git log

---
phase: quick
plan: 260327-mjt
subsystem: frontend
tags: [mobile-ux, sticky, filters, endgames, statistics]
dependency_graph:
  requires: []
  provides: [sticky-mobile-filters-endgames, sticky-filters-statistics]
  affects: [frontend/src/pages/Endgames.tsx, frontend/src/pages/GlobalStats.tsx]
tech_stack:
  added: []
  patterns: [sticky-top-0, bg-background-bleed]
key_files:
  created: []
  modified:
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/GlobalStats.tsx
decisions:
  - Tabs component lifted to wrap entire mobile section so TabsList can share Tabs context with TabsContent while being inside the sticky wrapper
  - Used -mx-6 px-6 on Statistics sticky bar to extend background color to full page width, preventing edge gaps during scroll
metrics:
  duration: ~10 min
  completed: 2026-03-27
---

# Phase quick Plan 260327-mjt: Sticky Filter Dropdowns for Endgame and Statistics Pages Summary

Sticky mobile filters for Endgames (Collapsible + TabsList) and sticky filter bar for Statistics page, plus removal of redundant Statistics h1 heading.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Make Endgames mobile filters and tab bar sticky | 47a8ed3 | frontend/src/pages/Endgames.tsx |
| 2 | Remove Statistics h1 and make filter section sticky | 22ceb5d | frontend/src/pages/GlobalStats.tsx |

## What Was Built

### Task 1 — Endgames mobile sticky bar
Restructured the mobile section of `Endgames.tsx` to lift the `<Tabs>` component to wrap the entire mobile layout. A `sticky top-0 z-20 bg-background pb-2` div now wraps the Collapsible filter, the divider, and the TabsList together. The TabsContent siblings remain outside the sticky wrapper so they scroll freely. The outer div lost its `gap-2` (the sticky wrapper manages its own internal spacing via `flex flex-col gap-2`).

### Task 2 — Statistics sticky filters and heading removal
In `GlobalStats.tsx`, the `<h1>Statistics</h1>` heading was deleted (redundant with the mobile header bar and desktop nav tab). The filter div was wrapped in `sticky top-0 z-10 bg-background pb-2 -mx-6 px-6 pt-1` — the negative horizontal margin trick extends the background color to the full page width so no content bleeds through at the edges during scroll.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `frontend/src/pages/Endgames.tsx` — modified, exists
- `frontend/src/pages/GlobalStats.tsx` — modified, exists
- Commit 47a8ed3 — verified in git log
- Commit 22ceb5d — verified in git log
- TypeScript: no errors
- Build: successful

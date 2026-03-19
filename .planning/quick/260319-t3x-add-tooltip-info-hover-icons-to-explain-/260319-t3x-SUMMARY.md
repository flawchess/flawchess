---
phase: quick
plan: 260319-t3x
subsystem: frontend
tags: [ui, tooltip, openings, ux]
dependency_graph:
  requires: []
  provides: [move-arrows-info-tooltip, position-bookmarks-info-tooltip]
  affects: [frontend/src/pages/Openings.tsx]
tech_stack:
  added: []
  patterns: [TooltipProvider/Tooltip/TooltipTrigger/TooltipContent pattern (matches existing Piece filter info icon)]
key_files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx
decisions:
  - span with role="button" used inside CollapsibleTrigger Button to avoid nested button elements; onClick stopPropagation prevents collapsible toggle on icon click
metrics:
  duration: ~5 minutes
  completed: "2026-03-19"
  tasks_completed: 1
  tasks_total: 1
---

# Quick Task 260319-t3x: Add tooltip info hover icons to explain move arrows and bookmarks

One-liner: Two Info icon tooltips added to Openings.tsx — one explaining arrow thickness/color encoding (frequency + win/loss thresholds), one explaining bookmark-to-statistics relationship.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add info tooltip to Moves tab and Position bookmarks section | 5eb3c22 | frontend/src/pages/Openings.tsx |

## What Was Built

**Move arrows info icon** — placed at the top of `moveExplorerContent` in a small header row (`"Move arrows"` label + Info icon). Tooltip text: explains thicker arrows = more games, green = 60%+ win rate, red = 60%+ loss rate, grey = default or under 10 games.

**Position bookmarks info icon** — placed inside the CollapsibleTrigger Button for "Position bookmarks", wrapped with the label in a flex span. Uses `span[role="button"]` (not `button`) to avoid nested interactive elements, with `onClick={e => e.stopPropagation()}` to prevent the collapsible from toggling on icon interaction. Tooltip text: explains bookmarks appear in Statistics tab charts as win/draw/loss entries.

Both follow the exact same visual pattern as the existing Piece filter info icon (h-3.5 w-3.5 Info icon, TooltipContent with max-w-xs text-sm, muted-foreground button styling).

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `frontend/src/pages/Openings.tsx` modified with both tooltips
- [x] Commit 5eb3c22 exists
- [x] TypeScript compiles without errors (`npx tsc --noEmit` clean)
- [x] data-testid="move-arrows-info" and data-testid="position-bookmarks-info" present
- [x] aria-label on both info trigger elements

## Self-Check: PASSED

---
phase: quick
plan: 260318-pp5
subsystem: frontend
tags: [ui, filters, tooltip, openings]
dependency_graph:
  requires: []
  provides: [always-enabled-filters, piece-filter-info-tooltip]
  affects: [frontend/src/pages/Openings.tsx]
tech_stack:
  added: []
  patterns: [lucide Info icon, TooltipProvider per-component]
key_files:
  modified:
    - frontend/src/pages/Openings.tsx
decisions:
  - TooltipProvider scoped to the info icon button rather than wrapping the entire filter section — cleaner and self-contained
metrics:
  duration: "~5 minutes"
  completed: "2026-03-18"
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 260318-pp5: Add hover info icon to Piece filter with always-enabled filters

**One-liner:** Removed tab-based filter disabling and added a lucide Info icon with explanatory tooltip next to the Piece filter label in Openings.tsx.

## What Was Done

Both "Played as" and "Piece filter" controls were previously greyed out (opacity-50, disabled attribute) depending on the active tab. This confused users about the filter state. The fix removes all tab-aware disabling so both controls are always interactive.

In addition, a small `Info` icon (lucide-react) was added next to the "Piece filter" label. Hovering it reveals a tooltip explaining:
- What the piece filter does (match your pieces, opponent's pieces, or both)
- That it applies to Games and Statistics tabs but not Moves

## Tasks

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Remove filter disabling and add info tooltip to Piece filter | 679a315 | frontend/src/pages/Openings.tsx |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] frontend/src/pages/Openings.tsx modified
- [x] Commit 679a315 exists
- [x] No references to `pieceFilterDisabled` or `playedAsDisabled` remain
- [x] TypeScript check passed (no errors)
- [x] Production build succeeded

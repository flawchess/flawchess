---
phase: quick-16
plan: 1
subsystem: frontend
tags: [ux, dashboard, import]
dependency_graph:
  requires: []
  provides: [relocated-import-button]
  affects: [Dashboard.tsx]
tech_stack:
  added: []
  patterns: []
key_files:
  modified:
    - frontend/src/pages/Dashboard.tsx
decisions:
  - "Import button moved to right column top (right-aligned) for better discoverability next to the games list it populates"
  - "games-imported count text removed as it was redundant with GameCardList pagination info"
metrics:
  duration: 1min
  completed: 2026-03-14
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 16: Move Import Button to Top of Games List — Summary

**One-liner:** Relocated Import button from left column action bar to top-right of right column, and removed redundant games-imported count text.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Relocate Import button and remove games-imported indicator | 8333f9b | Done |

## Changes Made

### frontend/src/pages/Dashboard.tsx

- **Removed** Import button (`btn-import`) from the left column "Always-visible action buttons" `div.flex.gap-2` — Filter button now sole occupant, retains `flex-1` for full-width stretch
- **Added** Import button at top of `rightColumn`, wrapped in `div.flex.justify-end` so it appears right-aligned above both the position-filtered view and the default games list
- **Removed** `<p className="text-sm text-muted-foreground">{defaultGames.data.matched_count.toLocaleString()} games imported</p>` from the default games data branch
- **Preserved** `importButton` variable (used for empty-state CTAs in both filtered and unfiltered views)
- **Preserved** `Download` icon import (used by the new right column Import button)

## Deviations from Plan

None — plan executed exactly as written.

## Pre-existing Lint Issues (Out of Scope)

Five pre-existing `react-refresh/only-export-components` errors in unrelated shadcn/ui component files (badge.tsx, button.tsx, tabs.tsx, toggle.tsx) and FilterPanel.tsx were present before this task and are not caused by these changes. Logged here for awareness; not fixed per scope boundary rules.

## Self-Check: PASSED

- FOUND: frontend/src/pages/Dashboard.tsx
- FOUND: commit 8333f9b

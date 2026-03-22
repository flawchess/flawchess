---
phase: quick
plan: 260322-lh2
subsystem: frontend
tags: [bug-fix, ui, openings, wdl-bar]
dependency_graph:
  requires: []
  provides: [consistent-moves-tab-wdl-bar]
  affects: [frontend/src/pages/Openings.tsx]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx
decisions:
  - "Moves tab WDL bar uses nextMoves.data.position_stats (fullHash/Both) instead of gamesQuery.data.stats (piece-filter-dependent)"
metrics:
  duration: "5m"
  completed: "2026-03-22"
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 260322-lh2: Moves Tab WDL Bar Always Uses Full-Position (Both) Stats

**One-liner:** Fixed Moves tab WDL bar to use nextMoves.data.position_stats (fullHash) instead of gamesQuery.data.stats, eliminating inconsistency when piece filter is set to Mine or Opponent.

## What Was Done

The WDL summary bar in the Moves tab (moveExplorerContent) was previously sourcing its stats from `gamesQuery.data.stats`, which respects the user's piece filter selection (Mine/Opponent/Both). This caused an inconsistency: the MoveExplorer move rows always show WDL bars computed from fullHash (Both pieces), but the summary bar above could show different stats when the piece filter was set to Mine or Opponent.

The fix replaces the data source with `nextMoves.data.position_stats`, which is always computed from fullHash regardless of piece filter. This matches how the individual move rows are computed, making the summary bar consistent with the move list below it.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix Moves tab WDL bar data source | 7b037ad | frontend/src/pages/Openings.tsx |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `npx tsc --noEmit` passed with no errors
- No remaining `gamesQuery.data.stats` usage in moveExplorerContent (confirmed via grep)
- `npm run build` succeeded

## Self-Check: PASSED

- File exists: frontend/src/pages/Openings.tsx — FOUND
- Commit 7b037ad — FOUND

---
phase: quick
plan: 260320-eeo
subsystem: frontend
tags: [ui, tooltip, move-explorer, openings]
dependency_graph:
  requires: []
  provides: [chessboard-info-icon, shortened-move-tooltip]
  affects: [frontend/src/components/move-explorer/MoveExplorer.tsx, frontend/src/pages/Openings.tsx]
tech_stack:
  added: []
  patterns: [tooltip-with-info-icon]
key_files:
  modified:
    - frontend/src/components/move-explorer/MoveExplorer.tsx
    - frontend/src/pages/Openings.tsx
decisions:
  - Arrow explanation moved to chessboard info icon below board, not in Move tab header
metrics:
  duration: ~5 min
  completed: "2026-03-20"
---

# Quick Task 260320-eeo: Remove Arrow Explanation from Move Tooltip Summary

**One-liner:** Moved arrow color/thickness explanation out of Move column tooltip into a new info icon next to the opening name below the chessboard.

## What Was Done

### Task 1: Shorten Move tooltip and add chessboard info icon

**MoveExplorer.tsx** — Shortened the Move column tooltip to only the first sentence describing what the listed moves represent. Removed the second paragraph about arrow color and thickness semantics.

**Openings.tsx** — Replaced the opening name div + empty spacer pattern with a unified flex row (`flex items-center gap-2 px-1 text-sm min-h-[1.25rem]`) that contains:
- The opening name (ECO code + name) on the left, shown conditionally
- A new info icon button (`data-testid="chessboard-info"`) always visible on the right via `ml-auto`
- The info icon tooltip explains: (1) how to play moves (drag or click), (2) arrow color and thickness semantics

## Commits

| Hash | Message |
|------|---------|
| 6ae1562 | feat(quick-260320-eeo): move arrow explanation from Move tooltip to chessboard info icon |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/components/move-explorer/MoveExplorer.tsx` - modified, committed in 6ae1562
- `frontend/src/pages/Openings.tsx` - modified, committed in 6ae1562
- TypeScript compilation: no errors

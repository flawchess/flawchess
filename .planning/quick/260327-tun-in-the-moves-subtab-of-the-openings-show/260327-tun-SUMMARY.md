---
phase: quick
plan: 260327-tun
subsystem: frontend
tags: [move-explorer, ux, opacity, theme]
key-files:
  modified:
    - frontend/src/components/move-explorer/MoveExplorer.tsx
decisions:
  - Applied opacity at the <tr> level so move name, game count, and WDL bar are all dimmed as a unit
metrics:
  duration: "< 5 minutes"
  completed: "2026-03-27"
  tasks: 1
  files: 1
---

# Quick Task 260327-tun Summary

## One-liner

Mute MoveExplorer rows at 50% opacity when game_count < MIN_GAMES_FOR_RELIABLE_STATS (10) using existing theme constants.

## What Was Done

Applied `UNRELIABLE_OPACITY` (0.5) as inline `style` on the `<tr>` element in `MoveRow` when `entry.game_count < MIN_GAMES_FOR_RELIABLE_STATS` (10). This visually signals unreliable WDL statistics without hiding or disabling the row.

- Imported `MIN_GAMES_FOR_RELIABLE_STATS` and `UNRELIABLE_OPACITY` from `@/lib/theme` (added to existing import line)
- Computed `isBelowThreshold` flag in `MoveRow`
- Applied `style={isBelowThreshold ? { opacity: UNRELIABLE_OPACITY } : undefined}` on `<tr>`
- Rows remain fully clickable and show the WDL popover on hover

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- File exists: `frontend/src/components/move-explorer/MoveExplorer.tsx` — FOUND
- Commit 3ffca51 exists — FOUND
- TypeScript compiles without errors — PASSED

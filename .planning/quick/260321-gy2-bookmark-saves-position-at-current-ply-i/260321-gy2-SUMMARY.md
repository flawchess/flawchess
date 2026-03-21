---
phase: quick-260321-gy2
plan: "01"
subsystem: ui

# Dependency graph
requires: []
provides:
  - Bookmark save truncates moveHistory to currentPly
  - Default bookmark label uses currentPly count
affects: []
---

# Summary: Bookmark saves displayed position

## One-liner
Fixed bookmark save to store moves only up to the currently displayed position, not the full move history.

## What changed
- `Openings.tsx:handleBookmarkSave` — `chess.moveHistory` → `chess.moveHistory.slice(0, chess.currentPly)`
- `Openings.tsx:openBookmarkDialog` — default label uses `chess.currentPly` instead of `chess.moveHistory.length`

## Why
When a user navigated back in the move list (e.g., viewing ply 5 of 10 moves), the bookmark was saving all 10 moves, resulting in a bookmark for the final position rather than the displayed one. Now only moves up to the current ply are saved.

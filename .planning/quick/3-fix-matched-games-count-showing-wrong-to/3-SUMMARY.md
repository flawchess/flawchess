---
phase: quick-3
plan: "01"
subsystem: frontend
tags: [bugfix, dashboard, analysis, ux]
dependency_graph:
  requires: []
  provides: [correct-matched-games-count, board-reset-clears-analysis]
  affects: [Dashboard.tsx]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - frontend/src/pages/Dashboard.tsx
decisions:
  - "Use totalGames ?? analysisResult.stats.total as safe fallback so GameTable shows correct total when /games/count query is still loading"
metrics:
  duration: 3min
  completed_date: "2026-03-12"
---

# Quick Task 3: Fix matched games count and board reset clears analysis — Summary

**One-liner:** Fixed GameTable totalGames source from stats.total (matched count) to /games/count result, and board reset now clears stale analysis panel.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix totalGames source and board-reset clears analysis | d6fadbc | frontend/src/pages/Dashboard.tsx |

## Changes Made

### Fix 1 — totalGames prop (GameTable)

`GameTable` was receiving `totalGames={analysisResult.stats.total}`, which mirrors `matched_count` — causing the display to read "N of N games matched" instead of "N of M games matched". Changed to `totalGames={totalGames ?? analysisResult.stats.total}` where `totalGames` comes from the pre-existing `/games/count` query result.

### Fix 2 — Board reset clears analysis panel

`BoardControls onReset` was wired directly to `chess.reset`. After reset, the board returned to the starting position but the right panel retained stale analysis results. Replaced with an inline handler that calls `chess.reset()`, `setAnalysisResult(null)`, and `setAnalysisOffset(0)` — returning the panel to the initial "Play moves and click Analyze" state.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npm run build` exits 0 with no TypeScript errors
- GameTable totalGames prop: `totalGames ?? analysisResult.stats.total`
- BoardControls onReset: calls chess.reset(), setAnalysisResult(null), setAnalysisOffset(0)

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/chessalytics/frontend/src/pages/Dashboard.tsx` — modified and committed
- Commit `d6fadbc` exists in git log

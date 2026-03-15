---
phase: quick-20
plan: 01
subsystem: frontend, backend
tags: [delete, games, modal, dashboard, import]
dependency_graph:
  requires: []
  provides: [DELETE /imports/games endpoint, delete-games-button]
  affects: [Dashboard.tsx, game_repository, imports router]
tech_stack:
  added: []
  patterns: [confirmation modal pattern, useCallback for async handler]
key_files:
  created: []
  modified:
    - app/repositories/game_repository.py
    - app/routers/imports.py
    - frontend/src/pages/Dashboard.tsx
decisions:
  - Delete positions before games (FK child rows first)
  - Also delete import_jobs for clean slate
  - Reset all analysis state after deletion (positionFilterActive, analysisResult, offsets)
  - Reuse existing Dialog import in Dashboard (already present for bookmark dialog)
metrics:
  duration: 5min
  completed: 2026-03-15
  tasks_completed: 2
  files_modified: 3
---

# Phase quick-20 Plan 01: Add Delete All Games Button Summary

**One-liner:** Delete All Games button with confirmation modal that calls DELETE /imports/games and resets Dashboard state.

## What Was Built

Added a "Delete" button to the left of the "Import" button in the games list header. Clicking it opens a confirmation modal warning the user that the action is permanent. Confirming calls the new `DELETE /imports/games` backend endpoint which removes all game_positions, games, and import_jobs for the authenticated user, then refreshes the game list and total count.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add backend DELETE endpoint and repository function | 41de50a | app/repositories/game_repository.py, app/routers/imports.py |
| 2 | Add delete button with confirmation modal to Dashboard | 5367704 | frontend/src/pages/Dashboard.tsx |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- app/repositories/game_repository.py: FOUND
- app/routers/imports.py: FOUND
- frontend/src/pages/Dashboard.tsx: FOUND
- Commit 41de50a: FOUND
- Commit 5367704: FOUND

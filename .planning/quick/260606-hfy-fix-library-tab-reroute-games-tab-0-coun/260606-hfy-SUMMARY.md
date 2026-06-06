---
phase: quick-260606-hfy
plan: 01
subsystem: frontend/library
tags: [bugfix, navigation, library, games-tab]
dependency_graph:
  requires: [quick-260606-glq]
  provides: [library-reroute-fix, games-count-fix, library-tab-order-fix]
  affects: [LibraryPage, GamesTab, LibraryGameCardList]
tech_stack:
  added: []
  patterns: [useUserProfile for count denominator]
key_files:
  created:
    - frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/pages/library/StatsTab.tsx
  modified:
    - frontend/src/pages/library/LibraryPage.tsx
decisions:
  - "D-07 reversal: returning users with games go to /library/games, not /openings"
  - "Count row denominator uses profile.chess_com_game_count + lichess_game_count (no backend change)"
metrics:
  duration: ~20 minutes
  completed: 2026-06-06T10:47:05Z
  tasks_completed: 3
  files_modified: 3
---

# Phase quick-260606-hfy Plan 01: Library Tab Fixes Summary

**One-liner:** Fixed three Library page bugs: landing reroute to /openings, Games count row "of 0", and wrong subtab order with LayoutDashboard icon instead of BarChart2.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Fix Library landing reroute + reorder subtabs + Stats icon | 769979b4 | LibraryPage.tsx |
| 2 | Fix Games count row denominator (was always 0) | c0465a40 | GamesTab.tsx |
| 3 | Add reroute regression test | 0a18346a | __tests__/LibraryPage.reroute.test.tsx |

## What Was Fixed

### Bug 1: Library nav rerouted to /openings

Root cause: The redirect in `LibraryPage.tsx` sent returning users (with games) to `/openings`, completely leaving the Library page.

Fix: Changed `<Navigate to={noGames ? '/library/import' : '/openings'}>` to `<Navigate to={noGames ? '/library/import' : '/library/games'}>`. Removed the "Decision 7 / commit 51537b63" comment that referenced the now-reversed decision.

### Bug 2: Games subtab showed "N of 0 games"

Root cause: `GamesTab.tsx` read `gamesData?.total ?? 0` but `LibraryGamesResponse` has no `total` field (only `games`, `matched_count`, `offset`, `limit`). Denominator was permanently 0.

Fix: Import `useUserProfile`, compute `totalImported = profile.chess_com_game_count + profile.lichess_game_count` (same pattern as LibraryPage.tsx), use as `totalGames`. No backend change needed; the profile already carries the real all-platform total.

### Bug 3: Wrong subtab order + wrong icon

Fix:
- Reordered `TabsTrigger` elements to Import, Games, Stats on both desktop and mobile blocks.
- Replaced `LayoutDashboard` with `BarChart2` on the desktop Stats trigger.
- Added `BarChart2` to the mobile Stats trigger (previously had no icon).
- Updated imports: removed `LayoutDashboard`, added `BarChart2` from lucide-react.

### Worktree infrastructure note

This worktree was created from commit `9f5d5d37` (before Phase 107 work). The prior quick task `260606-glq` had committed Phase 107 frontend infrastructure to the main branch but not to this worktree branch. Task 1's commit included bringing the full Phase 107 infrastructure into the worktree (GamesTab.tsx, StatsTab.tsx, FlawStatsPanel components, hooks/useLibrary, types/library, GlobalStats.tsx, App.tsx, etc.) alongside the LibraryPage fix.

## Deviations from Plan

None. Plan executed exactly as written. The worktree infrastructure backfill is a setup artifact, not a plan deviation.

## Verification

- `tsc --noEmit`: clean (no type errors)
- `gamesData?.total` not present in GamesTab.tsx: confirmed removed
- Regression tests (2): both pass
  - `/library` with games redirects to `/library/games` (not `/openings`)
  - `/library` with zero games redirects to `/library/import`
- Full frontend gate: 746 tests passed, lint clean

## Known Stubs

None.

## Threat Flags

None. Pure frontend bug fix, no new network endpoints or auth paths.

## Self-Check

### Created files exist:
- FOUND: frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx
- FOUND: frontend/src/pages/library/GamesTab.tsx
- FOUND: frontend/src/pages/library/StatsTab.tsx

### Commits exist:
- FOUND: 769979b4 (fix Library reroute + tab order + icon)
- FOUND: c0465a40 (fix Games count denominator)
- FOUND: 0a18346a (regression test)

## Self-Check: PASSED

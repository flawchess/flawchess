---
phase: 246-train-subnav-split
plan: 03
subsystem: frontend/train
tags: [train, streak-card, schedule-card, analytics]
requires: [246-02, 246-08]
provides:
  - TrainRankLine on the streak card (links to /train/leaderboard)
  - TrainStreakCard pointsToday prop
  - Always-open TrainScheduleSettings
affects: [246-05]
tech-stack:
  added: []
  patterns: [reserved pending row to avoid fallback flash, nav-click via trackFeature on router Link]
key-files:
  created: []
  modified:
    - frontend/src/components/train/TrainStreakCard.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/TrainScheduleSettings.tsx
    - frontend/src/lib/analytics.ts
    - frontend/src/components/train/__tests__/TrainStreakCard.test.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
  deleted:
    - frontend/src/components/train/TrainStatsCard.tsx
    - frontend/src/components/train/__tests__/TrainStatsCard.test.tsx
key-decisions:
  - "Rank line reads points.viewer.rank from the landing leaderboard query (shared cache key with the Leaderboard tab)"
  - "nav-click with value train-rank-line registered in NAV_SOURCES"
  - "'train-schedule' panel-open target removed with the collapsible (removal, no Umami rename)"
status: complete
commits: 3
plan_head_before: fcfb5988c2a6e079d107bb14a0e01c92fadb8592
plan_head_after: 2a369f617
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
---

# Phase 246 Plan 03: Rank line, Points today, full schedule card Summary

The Today tab's streak card now shows the viewer's Points rank (`#4 this week`, or `See this week's leaderboard`) as a client-side link to the Leaderboard tab, carries `Points today: N/M` on the completed landing, and sits above an always-open schedule card; `TrainStatsCard` is gone.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Tracer: rank line, query, link, nav-click | 8304a1039 |
| 2 | Points today on the streak card; delete TrainStatsCard | 990621038 |
| 3 | Full schedule card, collapsible removed | 2a369f617 |

## Verification

- Targeted vitest suites (StreakCard, StartScreen, ScheduleSettings, analytics, Train.solveLoop) pass.
- `npm run lint`, `npm run build`, `npm run knip` clean (knip prints two pre-existing config hints only).
- `grep -rl TrainStatsCard frontend/src` prints nothing.
- Tracer mutation check: forcing the `isPending` branch off made `shows nothing while the leaderboard is pending (no fallback flash)` fail; restored before commit.

## Deviations from Plan

1. **[Rule 3 - Blocking] Plan-HEAD ledger not written.** The harness refuses writes to the shared `.git/worktrees/` dir from a worktree agent, so `gsd-plan-head-before-246-03` was not persisted. `plan_head_before` is the known spawn base (`fcfb5988c`) and `commits: 3` was measured with `git rev-list --count fcfb5988c..HEAD`.
2. **Slider-burst Umami test.** It relied on collapsing the card to unmount the slider and flush the debounced event. With no collapse, it now calls `cleanup()` to unmount, keeping the burst-debounce coverage instead of deleting it. The plan only said to delete the panel-open test.
3. **Landing-order assertion.** `TrainStartScreen.test.tsx` mocks the leaderboard hook as pending, so the rank line is absent there. Points today ordering is asserted against `train-shield-row` there; the full rank-line, points, shield ordering is asserted in `TrainStreakCard.test.tsx`.

## Known Stubs

None.

## Threat Flags

None. `train-rank-line` is a registered literal in `NAV_SOURCES` (T-246-13).

## Self-Check: PASSED

- Commits 8304a1039, 990621038, 2a369f617 present on the branch.
- TrainStatsCard.tsx and its test removed; TrainStreakCard.tsx contains `train-rank-line` and `train-points-today`.

---
phase: 241-codebase-cleanup
plan: 57
subsystem: frontend-train
tags: [cleanup, naming, renames]
requires: [241-02, 241-03, 241-04, 241-30, 241-34, 241-36, 241-37, 241-45, 241-47, 241-48, 241-50, 241-51]
provides: ["Train component names that match what the code is (INVENTORY section 5 fe-components-train-analysis-bots)"]
affects: [frontend/src/components/train, frontend/src/components/admin, frontend/src/hooks, frontend/src/lib]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-57.tsv
  modified:
    - frontend/src/components/train/useTrainReminderSlot.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainLeaderboardCard.tsx
    - frontend/src/lib/trainBotCopy.ts
decisions:
  - "Locals at TrainLeaderboardCard ~315/~416 stay `remaining` (D-08 optional); only the view prop became `secondsRemaining`"
status: complete
commits: 5
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: cf6fa8e655a924ffce1edf356990d424133a7e18
actuals:
  tokens: 30000
  tasks: 3
  commits: 5
---

# Phase 241 Plan 57: Train component renames Summary

Five INVENTORY section 5 renames in the Train components, one `refactor(naming)` commit each: a hook module named for the hook it exports, a landing-host component, the reveal gate flag, a unit-bearing countdown prop, and a tier-typed parameter. No behavior change.

## Renames

| # | Old | New | Commit | Files touched |
| - | --- | --- | ------ | ------------- |
| 1 | `TrainReminderButton.tsx` (+ test file) | `useTrainReminderSlot.tsx` (+ `useTrainReminderSlot.test.tsx`) | 519c42cc8 | git-detected rename (R) of both files; imports in TrainScoreScreen.tsx and TrainReminderResurfaceBanner.tsx; `vi.mock` path in TrainScoreScreen.test.tsx; comment references in TrainInstallQr, TrainScheduleSettings (+ test), TrainReminderTestCard.test, useTrainSettings, usePushCapability, useReminderResurface, useInstallPrompt (+ test), lib/push.ts, lib/reminderSlotState.ts |
| 2 | `TrainHeader` | `TrainLandingHost` | 8f483ef85 | TrainStartScreen.tsx |
| 3 | `showResultRow` | `showReveal` | d816a413d | TrainSolveScreen.tsx (comment above the flag rewritten: it gates TrainReveal, the eval bar and the action bars), pages/__tests__/Train.solveLoop.test.tsx (comment) |
| 4 | `remaining` prop (TrainLeaderboardCardView) | `secondsRemaining` | f6af036ba | TrainLeaderboardCard.tsx, admin/LeaderboardMedalsDemo.tsx, TrainLeaderboardCard.test.tsx |
| 5 | `moveQuality` param (trainBotCopy verdict helpers) | `moveTier` | cf6fa8e65 | lib/trainBotCopy.ts |

All touched files were in `files_modified`; no unlisted file needed an edit.

## Notes

- Comment wording was adjusted where a mechanical replace read badly: `<TrainReminderButton />` became "a wrapper component" in TrainScoreScreen.tsx and its test, and `TrainReminderButton's useTrainReminderSlot()` became `useTrainReminderSlot()` in useInstallPrompt.ts.
- Testids (`train-landing-host`, `qr-handoff-*`), Umami attributes and the `move_quality` wire field are unchanged. The unrelated `lib/moveQuality.ts` module and its imports were not touched.
- rename-maps/241-57.tsv holds the five rows (file-stem row first); the last two commits each added only their own row.

## Results

- `npm --prefix frontend run build` (tsc -b + vite): 0 TS errors after each rename. `npm run lint`: clean. `npm run knip`: no findings (same two configuration hints as the untouched baseline).
- Tests: train, admin and useInstallPrompt suites passed (713 tests); the Train page/solve-loop, TrainLeaderboardCard, admin and trainBotCopy suites passed. `source_scan_tests.sh`: 131 frontend tests passed.
- `cleanup.py absent --map rename-maps/241-57.tsv`: 0 hits. `cleanup.py diff --plan 241-57` on each rename's files: exit 0.

## Deviations from Plan

None - plan executed as written, with one process note: the full train/admin/hooks test run in Task 1 showed one failure in `TrainStreakCard.test.tsx` (an animation counter assertion, file not touched by this plan) under 30 parallel workers; it passed 24/24 when rerun alone, so it is a load-related timing flake, not caused by this plan.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- FOUND: frontend/src/components/train/useTrainReminderSlot.tsx, frontend/src/components/train/__tests__/useTrainReminderSlot.test.tsx, .planning/phases/241-codebase-cleanup/rename-maps/241-57.tsv
- FOUND commits: 519c42cc8, 8f483ef85, d816a413d, f6af036ba, cf6fa8e65

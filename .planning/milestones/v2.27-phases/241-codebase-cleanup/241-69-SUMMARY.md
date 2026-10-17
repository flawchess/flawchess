---
phase: 241-codebase-cleanup
plan: 69
subsystem: frontend-train
tags: [naming, refactor, train, tour]
requires: [241-04, 241-30, 241-57, 241-68]
provides:
  - "frontend internal vocabulary walkthrough -> tour (D-05)"
  - "D-16 frontend sweep result (no production finds)"
affects: [frontend/src/hooks/useTrainTour.ts, frontend/src/components/train, frontend/src/lib/trainBotCopy.ts]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-69.tsv
  modified:
    - frontend/src/hooks/useTrainTour.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/animatedScroll.ts
    - frontend/src/hooks/useTrainPuzzleTelemetry.ts
key-decisions:
  - "Persisted ReviewCounters.walkthrough / ReviewTelemetrySnapshot.walkthrough stay (sessionStorage reveal cache + review_walkthrough wire mapping, D-17)"
requirements-completed: [D-01, D-02, D-05, D-16, D-17]
duration: 15 min
completed: 2026-10-16
status: complete
commits: 1
plan_head_before: 0794c22717bf6be20e6ebcc024500b66f368fd96
plan_head_after: 03d352275d7d40fa48571bd2fd2eb2b681b90bde
actuals:
  tokens: 14000
  tasks: 2
  commits: 1
---

# Phase 241 Plan 69: walkthrough -> tour Summary

The frontend now says "tour" everywhere for the first-reveal tour (hook file, types, constants, props, refs, prose), in one `refactor(naming)` commit with every testid, wire field and persisted key unchanged.

## Accomplishments

- D-05: `useTrainWalkthrough.ts` git-mv'd to `useTrainTour.ts` and all compound identifiers renamed (table below); local `walkthrough` in TrainSolveScreen.tsx became `tour`; comments, JSDoc and test titles that mean the feature now say tour.
- D-16 frontend sweep ran (result below).

## D-05 rename table (old -> new)

| Old | New |
|-----|-----|
| useTrainWalkthrough.ts | useTrainTour.ts |
| useTrainWalkthrough | useTrainTour |
| UseTrainWalkthroughInput / Result | UseTrainTourInput / Result |
| WalkthroughTarget / Context / StepCopy | TourTarget / TourContext / TourStepCopy |
| WALKTHROUGH_CHIPS / STEP / BOARD / UNDERSTAND | TOUR_CHIPS / STEP / BOARD / UNDERSTAND |
| WALKTHROUGH_SCROLL_TARGETS / GAP_PX / DURATION_MS | TOUR_SCROLL_TARGETS / GAP_PX / DURATION_MS |
| walkthroughTarget (TrainReveal prop + locals) | tourTarget |
| walkthroughHideRef / walkthroughActive | tourHideRef / tourActive |
| markWalkthroughActive | markTourActive |
| local `walkthrough` (TrainSolveScreen.tsx) | `tour` |

Commit: `03d352275` (`refactor(naming): walkthrough → tour`, shown by git as a rename of the hook file).

## Contract-token count

`git grep -o -e train-bot-walkthrough -e review_walkthrough -e reveal_walkthrough -- frontend/src`: 33 lines at HEAD~1, 33 after. Only the persisted `walkthrough` counter/snapshot field remains in trainTelemetry.ts, useTrainPuzzleTelemetry.ts and its test (residual-spelling gate passes with no other file left).

## D-16 frontend sweep

No finds. The probe over `frontend/src` (excluding `generated/`) returned only `preSeed119Verdict` (test-local); no tag-shaped production identifier, so no D-16 commits.

## Tagged test-local names (owner decides)

- `preSeed119Verdict` in `frontend/src/lib/__tests__/trainRevealCache.test.ts` (lines 187, 188, 191). Not renamed.

## D-16 cross-layer candidates

None.

## Verification

- `npm run build`, `npm run lint`, `npm run knip` pass (knip prints only two pre-existing config hints).
- Vitest: src/components/train, useTrainPuzzleTelemetry, trainBotCopy, trainRevealCache: 29 files / 853 tests pass; source_scan_tests.sh: 9 files / 131 tests pass.
- `cleanup.py absent --map rename-maps/241-69.tsv`: 18 rows, 0 hits. `cleanup.py diff --plan 241-69 ...`: no residue lines.

## Deviations from Plan

None - plan executed exactly as written. (The planning-time `walkthroughTreeStepRef` comment no longer existed in the file, so no prose fix was needed there. Backend app/ and tests/ untouched. STATE.md/ROADMAP.md left to the orchestrator per worktree-mode instructions.)

## Known Stubs

None.

## Self-Check: PASSED

- useTrainTour.ts exists, useTrainWalkthrough.ts gone, 241-69.tsv exists.
- Commit 03d352275 is an ancestor of HEAD.

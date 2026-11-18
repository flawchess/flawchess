---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 10
subsystem: ui
tags: [train, blunder-check, feature-route, discovery-dot, score-screen, react]

requires:
  - phase: 251-02
    provides: owner decision on the feature-route step ID (`blunder-check`)
  - phase: 251-07
    provides: TrainTodayActionsContext (startPuzzles, startBlunderCheck), drill host under Today
  - phase: 251-13
    provides: TrainModeLauncherRow and the per-mode progress rows
  - phase: 255
    provides: feature-discovery dot route (FEATURE_ROUTE, useRouteDot, useRecordFeatureRoute)
provides:
  - "ContinueAction + useContinueAction: both score screens hand off to the other mode while it is pending or in progress (D-12)"
  - "TrainScoreScreenView optional continueAction prop (primary button, Done drops to brand-outline)"
  - "blunder-check feature-route step appended last on both sides, control slot train-blunder-check-start (D-21)"
  - "Discovery dot on the Blunder Check Start and the D-19 pitch line under that row"
affects: [251-11]

plan_head_before: 60945645ff1448881d37e4350f88c41078953337
plan_head_after: b9950d628f66b55d5da58b593a425c268cb23234

actuals:
  tokens: 14000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Score-screen hand-off is one shared hook (useContinueAction) reading the progress cache and the page's actions context; it returns undefined outside the Train page"
    - "Feature-route step appended at the end, mirrored on both sides and pinned by the paired list tests"

key-files:
  created: []
  modified:
    - app/schemas/feature_route.py
    - tests/test_feature_route.py
    - frontend/src/types/users.ts
    - frontend/src/lib/featureRoute.ts
    - frontend/src/lib/__tests__/featureRoute.test.ts
    - frontend/src/pages/Train.tsx
    - frontend/src/pages/__tests__/Train.blunderCheckToday.test.tsx
    - frontend/src/components/train/trainTodayActions.ts
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckEndScreen.tsx
    - frontend/src/components/train/TrainModeLauncherRow.tsx
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckEndScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainModeLauncherRow.test.tsx

key-decisions:
  - "useContinueAction lives in trainTodayActions.ts (not in the screens) and reads the context with plain useContext, so a screen rendered outside the Train page (admin demo, older tests) simply shows no continue button instead of throwing"
  - "The continue button sits above the Done / Remind me row, full width and primary; Done becomes brand-outline"
  - "showBlunderCheckRouteDot is an optional context field (absent reads as false) so the five existing provider sites need no change"
  - "recordRouteStep for blunder-check fires in startBlunderCheck, so the score-screen hand-off also completes the step; the server and the cached-state check make the repeat a no-op"
  - "The pitch shows in every row state while first_session_done is false (including off); the row wraps itself in a column only when the pitch is shown, so the card DOM is unchanged afterwards"

requirements-completed: []

coverage:
  - id: D1
    description: "Finishing puzzles offers Continue with Blunder Check while it is pending or in progress, and finishing Blunder Check offers Continue with Puzzles; done, off and not-yet-loaded progress show none; Done stays"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx (D-12 describe)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/blunder-check/__tests__/BlunderCheckEndScreen.test.tsx (D-12 describe)"
        status: pass
    human_judgment: false
  - id: D2
    description: "blunder-check is the last FeatureRouteStepId on both sides, with nav /train, Today subtab, control train-blunder-check-start, completes on use"
    verification:
      - kind: unit
        ref: "tests/test_feature_route.py#test_step_ids_are_pinned_in_d06_order"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/featureRoute.test.ts (blunder-check step describe, registry list)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The dot renders on the Blunder Check Start when the route sits there, and pressing Start posts done for blunder-check"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Train.blunderCheckToday.test.tsx (discovery dot describe)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainModeLauncherRow.test.tsx (route dot describe)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The one-line pitch shows under the Blunder Check row until first_session_done and never on the puzzles row"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainModeLauncherRow.test.tsx (pitch line describe)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Visual layout of the continue button, the dot corner and the pitch line on desktop and phone"
    verification: []
    human_judgment: true
    rationale: "No test judges spacing, button emphasis or how the pitch wraps on a 360px screen"

duration: 40min
completed: 2026-11-19
status: complete
---

# Phase 251 Plan 10: Mode hand-off, blunder-check discovery dot and pitch Summary

**Both score screens now offer "Continue with <other mode>" as the primary button while that mode is still owed, `blunder-check` is appended as the last feature-route step on both sides with its own dot on the Blunder Check Start, and the launcher row carries the D-19 pitch line until the first completed session.**

## Accomplishments

- `useContinueAction(other)` (in `trainTodayActions.ts`): reads the shared progress query and the page actions, returns `{label, testId, onClick}` when the other mode is `pending` or `in_progress`, else `undefined`. `TrainScoreScreen` passes `useContinueAction('blunder_check')`, `BlunderCheckEndScreen` passes `useContinueAction('puzzles')`. `TrainScoreScreenView` renders it as a full-width primary button above the Done row and drops Done to `brand-outline`; without it the view is unchanged (admin demo untouched).
- Feature route: `blunder-check` appended last in `FeatureRouteStepId` (backend Literal and frontend union) and `FEATURE_ROUTE` (nav `/train`, Today subtab, control `train-blunder-check-start`, completion `used`, `requiresGames: false`).
- `Train.tsx` reads `useRouteDot('control:train-blunder-check-start')`, exposes it as `showBlunderCheckRouteDot` in the actions context, and `startBlunderCheck` records `{action: 'done', step: 'blunder-check'}` first.
- `TrainModeLauncherRow`: `RouteDot` (corner, testid `train-blunder-check-notification-dot`) on the Blunder Check Start when the flag is set; `train-launcher-pitch-blunder-check` under the row while `first_session_done` is false.

## Task Commits

1. **Task 1 (tracer): score screens hand off to the other mode** - `0d952b470` (feat)
2. **Task 2 RED** - `9cd3c0804` (test); **GREEN** - `cea3a89a8` (feat)
3. **Task 3 RED** - `7034b3272` (test); **GREEN** - `2c738a258` (feat)

Tracer gate: the tracer's automated verify (both screen suites, admin, plus the page and reminder suites, lint and build) passed after the commit, so expansion proceeded.

## TDD Gate Compliance

- **Task 2 RED** (`9cd3c0804`): backend `test_step_ids_are_pinned_in_d06_order` failed on the tuple mismatch (no `blunder-check`); frontend: registry order test, `unknown route step blunder-check` and `expected null to be 'nav:/train'`. All planned assertions, no collection or fixture faults. `gsd_run check tdd-red-evidence` was not run (plan type is `execute`; reporter output inspected directly).
- **Task 2 GREEN** (`cea3a89a8`): both paired list tests and the placement tests pass. One of my own RED tests was wrong (it asserted `planRouteWrites` is empty, but the arbiter legitimately stamps `current`); fixed in the GREEN commit to assert no `done` write via the existing `doneWrites` helper.
- **Task 3 RED** (`7034b3272`): three failures on the planned assertions (dot element absent, pitch element absent, no POST); the other new cases passed as regression guards for the absent state.
- **Task 3 GREEN** (`2c738a258`): all pass. Bite check by mutation: removing the `recordRouteStep` line in `startBlunderCheck` fails the page test; restored.
- No REFACTOR commits.

## Deviations from Plan

**1. [Rule 3 - Blocking] Shared hook instead of per-screen wiring, no new context provider requirement**
- **Found during:** Task 1
- **Issue:** Both screens' existing suites render them without a `TrainTodayActionsContext` provider (and without a `QueryClientProvider`); a throwing `useTrainTodayActions()` would have broken them all.
- **Fix:** `useContinueAction` uses plain `useContext` (null gives no button) and the two suites mock `useTrainProgress`. The hook sits in `trainTodayActions.ts`, which the plan lists only for Task 3, because the type and the hook belong with the context.
- **Committed in:** `0d952b470`

**2. [Rule 3 - Blocking] Page test file added to Task 3**
- The plan names only the row test; the "Start records the step" behavior lives in `Train.tsx`, so it is tested in `Train.blunderCheckToday.test.tsx` (the plan's verify command already runs `src/pages/__tests__`). Its profile mock became mutable (`vi.hoisted` state) to seed a route state.

**Total deviations:** 2 (both blocking-test-shape, no scope change).

## Issues Encountered

None. From `frontend/`: `npm run lint`, `npm run build` (`tsc -b` + vite), `npx vitest run` (373 files, 6605 tests) and `npm run knip` (exit 0, two pre-existing configuration hints) pass. Backend: `uv run pytest tests/test_feature_route.py` (23 passed), `ruff format`, `ruff check` and `ty check app/ tests/ scripts/` clean.

The per-plan commit ledger file under the shared git dir could not be written from inside the worktree (path guard), so `plan_head_before` is the spawn-time HEAD recorded at start; `git rev-list --count` over it gives 5 commits.

## Known Stubs

None.

## Threat Flags

None. T-251-28 is mitigated by the existing server-side `FeatureRouteStepId` Literal on the `extra="forbid"` request model, which now accepts `blunder-check` and rejects everything else (paired list test). No new endpoint, no package installs.

## Self-Check: PASSED

- Commits `0d952b470`, `9cd3c0804`, `cea3a89a8`, `7034b3272`, `2c738a258`, `b9950d628` are ancestors of HEAD.
- Acceptance greps: `btn-train-continue-blunder-check` / `btn-train-continue-puzzles` in `trainTodayActions.ts` (`CONTINUE_COPY`) and named in a comment in each screen (a docs commit `b9950d628` added the comments so the plan grep finds them); `train-launcher-pitch-blunder-check` in `TrainModeLauncherRow.tsx`; `control:train-blunder-check-start` in `Train.tsx`; `train-blunder-check-start` in `featureRoute.ts` (slot union and route step).

---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 07
subsystem: ui
tags: [train, blunder-check, react, today-card, routing]

requires:
  - phase: 251-06
    provides: GET /train/progress modes / day_complete / pending_count / blunder_check_notice
  - phase: 251-04
    provides: blunder_check_per_session / blunder_check_level settings
  - phase: 251-05
    provides: BlunderCheckEndScreen
provides:
  - "TrainTodayActionsContext / useTrainTodayActions (startPuzzles, startBlunderCheck)"
  - "BlunderCheckTab as a drill host under Today (composes on mount, onExit prop)"
  - "Blunder Check Start/Resume row on the Today card (btn-train-blunder-check-start)"
  - "Subnav Today / Leaderboard / Archive for every user; /train/blunder-check retired"
  - "Frontend types for per-mode progress and the blunder-check settings fields"
affects: [251-08, 251-09, 251-10, 251-13]

plan_head_before: 7e5ac966ef4409b98f3c046209ab247669e67cec
plan_head_after: 30d052a9acb9ca48cd46a6052541483da16a9b0f

actuals:
  tokens: 36000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Page-provided actions context so the Today card starts a mode without a prop chain"
    - "Drill host mounts only while blunderCheckActive on Today; leaving Today ends it (render-time state reset, as in useTrainLoop)"

key-files:
  created:
    - frontend/src/components/train/trainTodayActions.ts
    - frontend/src/components/train/__tests__/trainProgressFixtures.ts
    - frontend/src/pages/__tests__/Train.blunderCheckToday.test.tsx
  modified:
    - frontend/src/types/train.ts
    - frontend/src/pages/Train.tsx
    - frontend/src/components/train/TrainStreakCard.tsx
    - frontend/src/components/train/TrainSubnav.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
    - frontend/src/lib/trainRoute.ts
    - frontend/src/lib/__tests__/trainRoute.test.ts
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
    - frontend/src/pages/__tests__/Train.subnav.test.tsx
    - frontend/src/components/train/__tests__/TrainStreakCard.test.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx

key-decisions:
  - "idle (the composing wait and its failure) is an immersive host phase, so the subnav does not flash between the Start tap and the first window"
  - "A stale restored solution calls onExit (back to Today) instead of falling back to a start screen"
  - "Leaving Today while the host is active clears blunderCheckActive, so a hidden drill never keeps its timers running; the open session resumes on the next Start"
  - "exitBlunderCheck invalidates the shared train progress query so the card shows the new remaining / done state on return"
  - "The card row is hidden at state off and shows a recap (no button) at done; plan 13 builds the full launcher rows and the Turn on state around the kept testid"

requirements-completed: []

coverage:
  - id: D1
    description: "Any user (non-beta included) starts blunder check from the Today card; the drill is immersive under Today and returns to the card"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Train.blunderCheckToday.test.tsx (3 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Blunder Check tab, its route, beta gate and the Phase 249 start screen are gone; old link lands on Today; subnav is three tabs"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Train.subnav.test.tsx (beta=false/true) and frontend/src/lib/__tests__/trainRoute.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Host composes once on mount (StrictMode safe), 409 and error Back exit, stale restored solution exits, Done exits"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx (50 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Visual layout of the Blunder Check row on the Today card (desktop and phone)"
    human_judgment: true
    rationale: "Minimal placeholder row inside the streak card; no test judges spacing or look, and plan 13 replaces it with the launcher rows"

duration: 55min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 07: Blunder check from the Today card Summary

**Blunder check now starts from a Start/Resume button on the Today card for every user: a page-provided actions context mounts the drill host under Today (immersive, composing on mount, `onExit` back to the card), and the beta tab, its `/train/blunder-check` route, the beta redirect and the Phase 249 start screen are removed.**

## Performance

- **Duration:** about 55 min
- **Tasks:** 2 (1 tracer, 1 auto)
- **Commits:** 2 measured from `plan_head_before`
- **Files:** 15 (3 created, 12 modified)

## Accomplishments

- `trainTodayActions.ts`: `TrainTodayActions`, `TrainTodayActionsContext`, `useTrainTodayActions()` (throws outside a provider). `Train.tsx` provides `startPuzzles` (the existing `handleEnterLoop`, which also clears `blunderCheckActive`) and `startBlunderCheck` (`unlockAudio()` synchronously in the tap, `loop.returnToLanding()` only when leaving the loop / score screen / a restored reveal, then `blunderCheckActive = true`).
- `Train.tsx`: no `beta_enabled` read, no beta redirect, no `/train/blunder-check` panel. The host mounts on Today while `blunderCheckActive` (initially true when a Analyze -> Back solution cache exists), hides the landing while mounted, and `pageImmersive` keys on it. `exitBlunderCheck` clears the flag and invalidates `TRAIN_PROGRESS_QUERY_KEY`.
- `BlunderCheckTab.tsx`: StartScreen and its copy removed; composes on mount through `handleStart` (the `startInFlight` guard kept, StrictMode safe, skipped when mounting into a restored solution); idle shows "Preparing your blunder check..." or the compose failure (409 "no sequences available" message / generic `LoadError`) with a Back button; `onExit` is called from the end screen's Done, the error Back, the compose-failure Back and a stale restored solution.
- `TrainStreakCard.tsx`: Blunder Check row with a Start / Resume button (`btn-train-blunder-check-start`, Resume while `modes.blunder_check.state === 'in_progress'`), "N sequences left" / "Done today, N points" status, hidden at `off`.
- `TrainSubnav.tsx` / `trainRoute.ts`: `showBlunderCheck`, the fourth tab and the `blunder-check` route member removed; `/train/blunder-check` parses as unknown and redirects to Today.
- `types/train.ts`: `TrainModeState`, `TrainModeProgress`, `TrainBlunderCheckModeProgress`, `TrainModesProgress`, the four new `TrainProgressResponse` fields, `BlunderCheckLevel`, `blunder_check_per_session` / `blunder_check_level` on `TrainSettingsResponse` (optional on `TrainSettingsUpdate`).

## Task Commits

1. **Task 1 (tracer): Start on the card runs the drill and returns to Today** - `3f3bcb794` (feat)
2. **Task 2: subnav and route cleanup** - `30d052a9a` (feat)

## Removed Phase 249 start-screen copy (for plan 251-09 to re-home)

Idea paragraph (`blunder-check-idea`):

> Most games are decided by blunders, not brilliancies. Strong players avoid them by checking every move before they play it. This drill turns that check into a habit.

"How it works" bullets (`blunder-check-how-it-works`):

- You replay short sequences from real games, your own and those of similarly rated players. Each of your moves is shown as an arrow, and you judge it against the clock.
- The blunders are ones a player at your level should spot, including missed chances to punish the opponent.
- Some sequences have no blunder at all, so you can never tell when one is coming.

Pot rule bullets (`blunder-check-pot-rule`):

- Every correct Good call adds a point to the sequence's pot.
- Catch the blunder for bonus points, then find a better move for more.
- Miss the blunder and the pot is lost. Running out of time on a good move costs a point.
- A false alarm ends the sequence, but you keep the pot.

Also removed: the "Blunder Check" heading with a "Beta" badge, the tagline "Check each move before it is played: Good move or blunder?", and the "Session in progress: sequence N of M" line (the card's Resume now carries that state).

## Pre-existing tests changed

- `Train.solveLoop.test.tsx`, `Train.subnav.test.tsx`, `TrainStreakCard.test.tsx`, `TrainStartScreen.test.tsx`: progress fixtures gain the plan 06 fields through the shared `trainProgressFixtures.ts` (`PHASE_251_PROGRESS_FIELDS`). The card and start-screen render helpers are wrapped in a `TrainTodayActionsContext` provider with `vi.fn()` actions; `TrainStreakCard.test.tsx` gains four Blunder Check row cases.
- `Train.subnav.test.tsx`: the "beta-only Blunder check tab (D-01)" block is replaced by one parameterized test (beta true/false: exactly the three tabs, old path lands on `/train`).
- `BlunderCheckTab.test.tsx`: start-screen, double-click and Back-to-start cases replaced by compose-on-mount, single-compose under StrictMode, 409/non-409 Back, error Back, immersive-from-first-paint, stale-restore exit and Done-calls-onExit cases; drill and restore cases keep their assertions with the Start click removed (compose is automatic). The Phase 249 D-19 analytics-import scan, with the 251-05 `BlunderCheckEndScreen.tsx` exemption, is unchanged and passes.
- `trainRoute.test.ts`: the blunder-check path now parses as unknown; the tab-path list is asserted to be exactly today / leaderboard / archive.
- `TrainArchiveTab.test.tsx` was left untouched: its progress fixture is an untyped `as const` object the Archive tab never feeds into the card.

## Deviations from Plan

None - plan executed as written. (Judgment calls inside the plan's latitude, all listed under key-decisions: idle counts as immersive, a stale restore calls `onExit`, leaving Today resets the active flag, the card row hides at `off`.)

## Issues Encountered

None. From `frontend/`: `npm run lint`, `npm run build` (`tsc -b` + vite), `npx vitest run` (369 files, 6520 tests) and `npm run knip` (exit 0) all pass. Note `tsconfig.app.json` excludes test files, so `npm run build` does not type-check the tests.

## Known Stubs

None. The card row is intentionally minimal (Start / Resume, sequences-left or done recap, hidden at off); the "Turn on" state, pending badge and the other launcher-row states are plan 13's scope, not a stub that blocks this plan's goal.

## Threat Flags

None. T-251-21: the restored-solution ownership check is kept (stale entry now calls `onExit` after `RESET`; tested). T-251-22: the synchronous `startInFlight` guard is kept and a StrictMode double effect run sends one compose (tested). T-251-SC: no packages installed.

## Self-Check: PASSED

- Created files exist: `trainTodayActions.ts`, `trainProgressFixtures.ts`, `Train.blunderCheckToday.test.tsx`, this SUMMARY.
- Commits `3f3bcb794` and `30d052a9a` are ancestors of HEAD.
- Acceptance greps: `useTrainTodayActions` in `trainTodayActions.ts` (3), `TrainTodayActionsContext.Provider` in `Train.tsx` (2 lines, open and close), `beta_enabled` in `Train.tsx` (0), `blunder-check-start-screen` in `BlunderCheckTab.tsx` (0), `showBlunderCheck` in `TrainSubnav.tsx` and `Train.tsx` (0), `'blunder-check'` in `trainRoute.ts` (0).

---
*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d*
*Completed: 2026-11-18*

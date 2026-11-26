---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 13
subsystem: ui
tags: [train, today-card, launcher-rows, nav-badge, analytics, react]

requires:
  - phase: 251-07
    provides: TrainTodayActionsContext / useTrainTodayActions, the card's Blunder Check Start, drill host under Today
  - phase: 251-06
    provides: GET /train/progress modes / pending_count / day_complete
  - phase: 251-04
    provides: optional blunder_check_per_session / blunder_check_level PUT fields
provides:
  - "TrainModeLauncherRow: one launcher row in the four D-09 states (pending, in progress, done, off)"
  - "Today card (TrainStreakCard) with flame, freeze meter and both launcher rows; rendered in every landing state"
  - "Train nav badge = pending_count (both modes)"
  - "Progress query invalidated after blunder-check compose and finish"
  - "TrainSettingsDraft optional blunderCheckPerSession / blunderCheckLevel"
  - "Analytics targets for plans 08 and 09 registered as literal unions"
affects: [251-08, 251-09, 251-10]

plan_head_before: f1eb3266a372b1328bcf498c811ce6ced8d82230
plan_head_after: f9784a0051c546c40d15ec5dfb75968e7d4cdc85

actuals:
  tokens: 14000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Landing session overrides the server's puzzles mode estimate for the row (PuzzlesLanding), server off always wins"
    - "Row reads Start / Resume from useTrainTodayActions, so TrainStartScreen no longer takes onEnterLoop"

key-files:
  created:
    - frontend/src/components/train/TrainModeLauncherRow.tsx
    - frontend/src/components/train/__tests__/TrainModeLauncherRow.test.tsx
    - frontend/src/hooks/__tests__/useBlunderCheckSession.test.ts
  modified:
    - frontend/src/components/train/TrainStreakCard.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/pages/Train.tsx
    - frontend/src/App.tsx
    - frontend/src/hooks/useBlunderCheckSession.ts
    - frontend/src/hooks/useTrainSettings.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/App.test.tsx
    - frontend/src/components/train/__tests__/TrainStreakCard.test.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
    - frontend/src/hooks/__tests__/useTrainSettings.test.ts
    - frontend/src/lib/__tests__/analytics.test.ts

key-decisions:
  - "The puzzles row takes its state and count from the landing session (fresh/warmup pending, resume in progress, completed done) because the session response decides what Start does; without a landing the server's waiting_count estimate is capped at the session size. A server `off` always wins."
  - "Badge shows the count left while in progress, and while pending only when the server counts it toward the nav badge (pending > 0), so off-day rows show Start without a badge"
  - "Puzzle Start / Resume are short labels (Start, Resume) with the count on the status line; the old 'Start session - N puzzles' copy and 'Points today: N/M' line are gone (the done line is 'Done today, N points')"
  - "Empty landing renders the Today card too (puzzles Start disabled) so Blunder Check stays reachable; with puzzles off it shows the card and the schedule settings instead of the no-puzzles copy"
  - "Badge red reuses ROUTE_DOT_COLOR_CLASS from theme.ts (the nav TrainBadge's bg-red-500)"

patterns-established:
  - "Launcher row testids: train-launcher-row-{puzzles|blunder-check}, -badge-, -status-, -done-, -check-, btn-train-launcher-turn-on-"

requirements-completed: []

coverage:
  - id: D1
    description: "Today card renders a launcher row per mode in all four D-09 states, Start/Resume call the page actions"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainModeLauncherRow.test.tsx (18 tests)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainStreakCard.test.tsx (launcher rows describe)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Landing renders the card in every state; puzzles off never shows the no-puzzles copy; empty keeps Blunder Check reachable"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainStartScreen.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Train nav badge reads pending_count and stays hidden for guests and locked-nav accounts"
    requirement: ""
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx (nav badge cases)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Compose and finish refresh the train progress query"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBlunderCheckSession.test.ts"
        status: pass
    human_judgment: false
  - id: D5
    description: "Settings hook sends the optional blunder-check fields only when defined (0 included); analytics targets registered"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainSettings.test.ts and frontend/src/lib/__tests__/analytics.test.ts"
        status: pass
    human_judgment: false
  - id: D6
    description: "Visual layout and spacing of the launcher rows on desktop and phone, badge and Start button proportions"
    verification: []
    human_judgment: true
    rationale: "No test judges spacing, badge size or the above-the-fold fit on a phone"

duration: 50min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 13: Launcher rows, pending_count badge, settings fields Summary

**The Today card is now sketch 014 variant B's launcher: flame, freeze meter and one row per mode (name, red count badge, status line, Start / Resume, checkmark when done, Turn on when off) in every landing state, the Train nav badge sums both modes via `pending_count`, compose and finish refresh the card, and the settings hook and analytics registry carry the fields and targets plans 08 and 09 consume.**

## Performance

- **Duration:** about 50 min
- **Completed:** 2026-11-18T22:34Z
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files:** 17 (3 created, 14 modified)
- **Commits:** 3 measured from `plan_head_before`

## Accomplishments

- `TrainModeLauncherRow` renders the D-09 states for both modes. Start / Resume come from `useTrainTodayActions`; puzzles keeps `btn-train-start` / `btn-train-resume` and the `train-start-notification-dot` route dot, Blunder Check keeps `btn-train-blunder-check-start`. Turn on renders only when `onTurnOn` is passed.
- `TrainStreakCard` drops the `action` slot and `pointsToday`, renders both rows, accepts `puzzlesLanding`, `puzzlesStartDisabled`, `showRouteDot`, `onTurnOn`.
- `TrainStartScreen` renders the same card in fresh, warmup, resume, completed and empty states; the `onEnterLoop` prop is removed (Train.tsx call site updated).
- `App.tsx` nav badge uses `pending_count`; guest and locked-nav gating and the 99+ cap are unchanged.
- `useBlunderCheckSession` invalidates `TRAIN_PROGRESS_QUERY_KEY` alongside the open-session query after compose and finish.
- `useTrainSettings` sends `blunder_check_per_session` / `blunder_check_level` only when defined; analytics registry gets `'0'` for puzzles size, `TRAIN_BLUNDER_CHECK_PER_SESSION_VALUES`, the two option targets and three action targets.

## Task Commits

1. **Task 1 (tracer): launcher rows and pending_count badge** - `7a50b3ef3` (feat)
2. **Task 2 RED** - `678e2cfb7` (test); **GREEN** - `f9784a005` (feat)

Tracer gate: the tracer's automated verify (row, card, landing, App, page and blunder-check tests, lint, build) was re-run after the commit and again as part of the full suite; it passes, so expansion proceeded.

## TDD Gate Compliance

- **RED** (`678e2cfb7`): `sends blunder_check_per_session and blunder_check_level when the draft sets them` failed with `expected undefined to be 9`, `sends a zero blunderCheckPerSession` failed with `expected undefined to be +0`; the registry test failed with `expected [...] to include 'train-blunder-check-per-session'`. These are the planned assertions, no collection or fixture faults. The "neither key" case passed immediately and is a regression guard for the absent-keeps-stored-value contract. `gsd_run check tdd-red-evidence` was not run (plan type is `execute`; vitest default reporter output was inspected directly).
- **GREEN** (`f9784a005`): all three files pass; full suite 371 files / 6548 tests.
- No REFACTOR commit.

## Decisions Made

See key-decisions. Notably the puzzles row prefers the landing session over the server's per-mode estimate, because `waiting_count` is an upper-bound signal that is 0 for warm-up-only accounts that still have a startable session.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing tests outside the plan's audit list updated**
- **Found during:** Task 1
- **Issue:** `Train.solveLoop.test.tsx` pinned `'Resume session — 7 of 12 done'` and `'Points today: 14/18'`; `TrainScheduleSettings.test.tsx`'s drift guard pinned the tracked puzzles-size list to the slider grid, which now also carries `'0'`.
- **Fix:** solveLoop assertions moved to the row copy (`Resume`, `5 puzzles left`, `Done today, 14 points`); the drift guard prepends `'0'` only while the slider grid lacks it, so it stays valid once plan 251-09 lowers the slider minimum.
- **Files modified:** `frontend/src/pages/__tests__/Train.solveLoop.test.tsx`, `frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx`
- **Committed in:** `7a50b3ef3`, `f9784a005`

**2. [Rule 3 - Blocking] `onEnterLoop` prop removed from TrainStartScreen, `Train.tsx` touched**
- **Found during:** Task 1
- **Issue:** The plan has Start / Resume call `startPuzzles` from the context, which makes `onEnterLoop` dead (lint unused, and a second path to the same action).
- **Fix:** Removed the prop and its one call site in `Train.tsx` (`handleEnterLoop` is still the context's `startPuzzles`); tests assert `startPuzzles` from the provider.
- **Committed in:** `7a50b3ef3`

**3. [Rule 2 - Missing critical] Hook invalidation test added**
- **Issue:** The "card refreshes after compose / finish" truth had no test.
- **Fix:** New `useBlunderCheckSession.test.ts` (2 tests) spying on `invalidateQueries`.
- **Committed in:** `7a50b3ef3`

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 missing critical). **Impact:** no scope creep; all required to keep the suite green or to prove a stated truth.

## Pre-existing tests changed

- `App.test.tsx`: nav-badge fixtures rewritten from `{waiting_count, badge_visible}` to `{pending_count}`; the off-day and badge_visible-omitted cases became "legacy fields ignored" and "payload without pending_count fails closed". Guest and locked-nav gating cases kept.
- `TrainStreakCard.test.tsx`: `renderWithClient(action, pointsToday)` replaced by a props object; the action-slot and Points today cases removed; the plan 07 Blunder Check row cases replaced by a launcher-rows block.
- `TrainStartScreen.test.tsx`: `onEnterLoop` assertions moved to the context's `startPuzzles`; label assertions moved to the row copy; empty and `no_material` cases now expect the card with the puzzles Start disabled; a puzzles-off empty case added.
- `Train.solveLoop.test.tsx`, `TrainScheduleSettings.test.tsx`: see deviation 1.

## Issues Encountered

None. From `frontend/`: `npm run lint`, `npm run build` (`tsc -b` + vite), `npx vitest run` (371 files, 6548 tests) and `npm run knip` (exit 0, two pre-existing configuration hints) pass. `tsconfig.app.json` excludes test files, so `npm run build` does not type-check them.

## Known Stubs

None. `onTurnOn` is intentionally not wired by `TrainStartScreen` yet: plan 251-09 restructures the settings rows and wires Turn on, so an off row shows "Off" without a button until then (documented in the plan).

## Threat Flags

None. T-251-23: only enumerated literal targets and values were registered (no ids, FENs or names). T-251-33: the settings hook adds the new keys only when defined and only as a number or the `BlunderCheckLevel` literal union. T-251-SC: no packages installed.

## Next Phase Readiness

Plans 251-08, -09 and -10 can consume `TrainSettingsDraft.blunderCheckPerSession` / `.blunderCheckLevel`, the analytics targets, and `TrainStreakCard`'s `onTurnOn`. Plan 09 should lower the puzzles slider minimum to 0 (the drift guard already accepts that) and pass `onTurnOn` from `TrainStartScreen`.

## Self-Check: PASSED

- Created files exist: `TrainModeLauncherRow.tsx`, its test, `useBlunderCheckSession.test.ts`, this SUMMARY.
- Commits `7a50b3ef3`, `678e2cfb7`, `f9784a005` are ancestors of HEAD.
- Acceptance greps: `train-launcher-row-` in `TrainModeLauncherRow.tsx` (1 line, template), `pending_count` in `App.tsx` (line 195), the four analytics targets in `analytics.ts`, `blunderCheckPerSession` in `useTrainSettings.ts` (3).

---
*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d*
*Completed: 2026-11-18*

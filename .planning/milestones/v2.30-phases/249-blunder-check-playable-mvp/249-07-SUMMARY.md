---
phase: 249-blunder-check-playable-mvp
plan: 07
subsystem: blunder-check-frontend
tags: [blunder-check, train, drill, timer, vitest, tdd]
status: complete

requires:
  - phase: 249-06
    provides: drill reducer, useBlunderCheckSession, BlunderCheckTab shell with the empty drill area
provides:
  - BlunderCheckDrill: window load, lead-in replay, arrow prompt, Safe/Blunder, move + reply, outcome panel, effects and countdown
  - useMoveTimer: deadline-based countdown that fires the timeout once
  - BlunderCheckPointsFlash and the animate-blunder-check-forfeit animation
  - BlunderCheckEndScreen and the finish step with retry
affects: [249-08]

tech-stack:
  added: []
  patterns:
    - "Effects keyed on the reducer phase, each in a small named hook (useLeadInTicks, useAfterAnswerTicks, useWindowLoader, useAnswering, useFinishSession); timers cleared on phase change and unmount"
    - "Timer reading is stored per promptKey and derived at render, so a new prompt shows its full duration before the first tick without an effect"
    - "Fake-timer tests advance one tick per act() scope: a tick's timer is scheduled by an effect after a render, so one big advance only fires the first timer"

key-files:
  created:
    - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckPointsFlash.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckEndScreen.tsx
    - frontend/src/hooks/useMoveTimer.ts
    - frontend/src/hooks/__tests__/useMoveTimer.test.ts
  modified:
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
    - frontend/src/lib/blunderCheckDrill.ts
    - frontend/src/lib/__tests__/blunderCheckDrill.test.ts
    - frontend/src/index.css
    - frontend/src/pages/Train.tsx
    - frontend/src/pages/__tests__/Train.subnav.test.tsx

key-decisions:
  - "Stale prompt recovery: the reducer accepts WINDOW_LOADED from the grading phase and goes straight to the prompt (never a lead-in replay, which would burn real countdown time); server timer and points win"
  - "The flash is derived from the graded answer through feedback, advancing and window_over (flashFor exported from the reducer) so the 2.4 s pop is not cut at the 900 ms feedback hold; a zero amount shows no flash"
  - "The prompt arrow uses chipArrowColor(['your'], null), i.e. the played-move fill from lib/trainArrows.ts (no new colour constant). It is the light green of an unrated played move; the owner may want a neutral colour if it biases answers"
  - "loading_window counts as immersive so the tab bar does not flash between two windows"
  - "The end screen has no session header (it carries its own points and Score %)"

requirements-completed: [D-09, D-12, D-13, D-14, D-18, D-19]

actuals:
  tokens: 22000
  tasks: 3
  commits: 4
plan_head_before: be617304b4c52d9df6747b33d353727c560a366a
plan_head_after: 8fa179f17fe078fb00b53ed95c51085df8aa905c
---

# Phase 249 Plan 07: Playable blunder-check drill Summary

A beta user can play a whole blunder-check session in the browser: fixed-pace lead-in replay, an arrow prompt with the piece still on its source square, a server-graded Safe that plays the move and the opponent's reply, a 15 s countdown seeded by the server's `timer_remaining_ms`, +N / -N flashes with Train sounds, reload resume, stale-prompt recovery and an end screen with the server's points and Score %.

## Tasks

1. **Task 1 (tracer)**, commit `ec7597bc4`: `BlunderCheckDrill` (window load, lead-in ticks, arrow prompt, Safe/Blunder with `brand-outline`, move + reply ticks, outcome panel with Clear/Caught/Missed/False alarm and Next), rendered by `BlunderCheckTab`. Tests: lead-in then arrow, graded Safe then move then reply then next arrow, window-ended outcome panel then Next starts the next window, no "your move" copy.
2. **Task 2 (TDD)**, RED `3de82412d`, GREEN `acd4961a8`: `useMoveTimer`, timeouts (once), points flash and forfeit animation, sounds by server result, resume with the server's remaining time, zero-time resume, 409 `stale_prompt` recovery.
3. **Task 3**, commit `8fa179f17`: `BlunderCheckEndScreen` (TrainScoreBadge, "N of M points", per-window list, Done), the finish step with retry copy, shared `WINDOW_OUTCOME_LABELS`.

## TDD (Task 2)

- **RED:** `useMoveTimer.test.ts` against an inert stub hook (returns the duration, no countdown), the tab tests and two reducer tests. `vitest --reporter=tap` exit 1; failing targets were all assertion failures on the planned behavior (e.g. "a prompt left alone for 15 s posts a timeout once": `answer` called 0 times; "counts down while running": remaining stayed 15000; reducer: `WINDOW_LOADED` ignored from `grading`). 15 failing tests, none import, syntax or fixture errors. I did not run `gsd_run check tdd-red-evidence`: this is a task-level `tdd="true"` task in an `execute` plan, not a `type: tdd` plan, so no evidence record was authored. Semantic assessment: the targets executed and failed on the planned assertion for the intended reason.
- **GREEN:** the hook, drill wiring, flash, sounds, stale handling; 53 targeted tests pass. A mutation check (making `isStalePromptError` always false) fails the stale-prompt test, then was reverted.
- **REFACTOR:** none separate. One lint fix inside GREEN (`prefer-const` in the hook, restructured so the interval handle is a const).

## Verification

From `frontend/`: `npm run lint` clean, `npm run build` (tsc -b + vite) clean, `npm test -- --run` 6150 tests passed, `npm run knip` clean (only the two pre-existing configuration hints). `grep -rnE "trackFeature|trackEvent|data-umami-event"` over the blunder-check folder, `useBlunderCheckSession.ts`, `useMoveTimer.ts` and `blunderCheckDrill.ts` prints nothing; the D-19 source-scan test now also covers `useMoveTimer.ts`. `grep -c "blunder-check-forfeit" index.css` = 3, no colour literals in `BlunderCheckPointsFlash.tsx`.

## Deviations from Plan

**1. [Rule 3 - Blocking] Reducer extended for stale-prompt recovery**
- **Issue:** the plan says re-fetch via start and dispatch WINDOW_LOADED, but the 06 reducer only accepted WINDOW_LOADED in `loading_window`; in `grading` it was a no-op.
- **Fix:** `windowLoaded` also accepts `grading` and goes straight to `prompt`; two reducer tests added. `flashFor` is now exported (used by the drill after the feedback phase). `WINDOW_OUTCOME_LABELS` added for the outcome panel and end screen.
- **Files:** `frontend/src/lib/blunderCheckDrill.ts`, `frontend/src/lib/__tests__/blunderCheckDrill.test.ts`

**2. [Rule 3 - Blocking] `Train.tsx` padding and subnav test mock**
- 06 handed the immersive padding to this plan. `trainPageClass(showLoop || blunderImmersive, restoredActive)` drops the phone top padding while the drill runs (the drill calls `useMarkPlayActive`, which hides the phone header). `Train.subnav.test.tsx`'s `startWindow` mock now stays pending, because the drill really calls it after Start. Neither file is in the plan's `files_modified`.

**3. [Scope note] `loading_window` is immersive** (`IMMERSIVE_PHASES` in the tab), otherwise the subnav flashes between windows.

**4. [Scope note] No `.planning/WINDOWS.md` entries**; the ledger is optional and no new stub was left. The git commit ledger file was not written (as in 06); `commits: 4` was counted with `git rev-list --count be617304b..HEAD`, the SUMMARY commit follows and is not counted.

## Known Stubs

None. The drill area is fully wired. The window_over panel intentionally ends at Next for a caught window; plan 08 inserts the better-move step and solution screen in front of it.

## Hand-off notes for plan 08

- `window_over` still renders the board at `window.shownUcis`, which does not include the final prompted move or reply; for a `caught` outcome the arrow stays drawn. `graded.better_move` is on the state.
- The outcome panel lives in `BlunderCheckDrill.tsx` (`OutcomePanel`, props `outcome`, `windowPoints`, `onNext`); insert the better-move step before `onNext` there or in a new reducer phase. A 0-amount flash is suppressed; sounds fire in `postAnswer` from the server result.
- `useFinishSession` in the tab runs whenever the phase is `finishing` (including the "all windows ended" resume case) and is safe to re-run because the server's finish is idempotent.
- Pacing (D-12 discretion): lead-in 400 + N*700 ms, feedback 900 ms, move 600 ms, reply 600 ms (all in `blunderCheckDrill.ts`), 15 s countdown turning red at 5 s (`MOVE_TIMER_WARN_MS` in the drill). The prompt arrow colour is a judgement call, see key-decisions.
- Not covered by any test: real browser feel (arrow visibility, flash animations, sound playback) and a physical-phone layout; the board uses the width-only sizing (max 480 px), no viewport-height fit.

## Threat Flags

None beyond the plan's threat model. T-249-20 (client shows server numbers, resume countdown is the server's remaining time) and T-249-21 (no analytics, grep and scan test) hold.

## Self-Check: PASSED

- Files exist: all five created and seven modified files listed above.
- Commits `ec7597bc4`, `3de82412d`, `acd4961a8`, `8fa179f17` are ancestors of HEAD.

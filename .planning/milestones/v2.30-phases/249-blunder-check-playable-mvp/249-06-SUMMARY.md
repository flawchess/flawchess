---
phase: 249-blunder-check-playable-mvp
plan: 06
subsystem: blunder-check-frontend
tags: [blunder-check, train, beta-gate, reducer, tanstack-query, vitest]
status: complete

requires:
  - phase: 249-04
    provides: server-graded drill endpoints (start, answers, finish) and the wire schemas
provides:
  - beta-only fourth Train tab at /train/blunder-check with a redirect for non-beta users
  - frontend/src/types/blunderCheck.ts (TypeScript mirror of the plan 02/04 wire contract)
  - blunderCheckApi (getOpenSession, composeOrResumeSession, startWindow, answer, finishSession) and useBlunderCheckSession
  - frontend/src/lib/blunderCheckDrill.ts (pure drill reducer, applyUcis, animation constants)
  - BlunderCheckTab (start screen, session header, drill host owning the reducer)
affects: [249-07, 249-08]

tech-stack:
  added: []
  patterns:
    - "Pure drill reducer: no timers or I/O, one small handler per event, phase guards make out-of-phase events a same-object no-op"
    - "Synchronous useRef in-flight guard next to a disabled button (mutation.isPending flips a render late)"
    - "Source-text scan test for the no-analytics rule, needles built from parts so the test does not contain what it forbids"

key-files:
  created:
    - frontend/src/types/blunderCheck.ts
    - frontend/src/hooks/useBlunderCheckSession.ts
    - frontend/src/lib/blunderCheckDrill.ts
    - frontend/src/lib/__tests__/blunderCheckDrill.test.ts
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
  modified:
    - frontend/src/lib/trainRoute.ts
    - frontend/src/lib/__tests__/trainRoute.test.ts
    - frontend/src/components/train/TrainSubnav.tsx
    - frontend/src/pages/Train.tsx
    - frontend/src/pages/__tests__/Train.subnav.test.tsx
    - frontend/src/api/client.ts

key-decisions:
  - "Lead-in replay takes N+1 ticks: one per ply, then a final tick that hands over to the prompt (a window with zero plies prompts on the first tick). With LEAD_IN_PLIES = 3 this is 400 + 3 * 700 = 2500 ms, under the 3000 ms budget"
  - "The after-answer path is feedback (900 ms), first advance tick plays the move (+600), second tick plays the reply and opens the next prompt (+600): 2100 ms, under 3000 ms"
  - "A session whose windows have all ended but is not finished goes SESSION_READY -> finishing directly (current_position null), instead of loading a window"
  - "A graded window_ended answer with a null outcome, or a continuing window without next_prompt, goes to the error phase rather than fabricating an outcome or prompt"
  - "The page goes immersive for a running drill by reusing trainPageClass(showLoop, restoredActive) unchanged, so the phone top padding stays; plan 07 owns useMarkPlayActive and any padding change"

patterns-established:
  - "Beta gating on the Train page reads useUserProfile().data.beta_enabled; the redirect sits after the profile-loading early return, hooks stay above"

requirements-completed: [D-01, D-12, D-18, D-19]

actuals:
  tokens: 21000
  tasks: 3
  commits: 4
plan_head_before: ccf303990fb9a54992b69b5dc78778c8d4547679
plan_head_after: 86ba9e27b6cec88dd58d391c1d273ac639503a34
---

# Phase 249 Plan 06: Blunder-check tab, API client and drill state machine Summary

A beta user gets a fourth "Blunder check" Train tab whose Start (or Resume) button composes a session through the real API client and shows "Window N of M" with the server's points, backed by a pure, tested drill reducer (lead-in, prompt, grading, feedback, move + reply, window end, resume, session end) whose animations fit the server's 3 s allowance.

## Tasks

1. **Task 1 (tracer)**, commit `4f560dae2`: route + tab (`'blunder-check'` in `trainRoute.ts`, `showBlunderCheck` on `TrainSubnav`), beta gate and `blunderImmersive` flag in `Train.tsx`, wire types, `blunderCheckApi`, `useBlunderCheckSession`, the `DrillState`/`DrillEvent` unions with the session-level events, and `BlunderCheckTab`'s start screen. End-to-end test in `Train.subnav.test.tsx`: a beta profile sees the tab, one Start click makes one compose call and the panel shows "Window 1 of 6" and "Points: 0". The non-beta redirect and the Today-latch tests (Task 3 items) were written in the same file here and pass.
2. **Task 2 (TDD)**, RED `cfe9f0e30`, GREEN `a298700a1`: 20 reducer tests. GREEN implemented every window transition, `applyUcis` and the five animation constants. No refactor commit was needed.
3. **Task 3**, commit `86ba9e27b`: `trainRoute` parse cases, `BlunderCheckTab` tests (Start, Resume + counter/points after resume, 409 copy, non-409 and open-session failure copy, error-phase Back to start, double click, immersive reporting) and the D-19 source scan.

## TDD (Task 2)

- **RED:** `blunderCheckDrill.test.ts` committed with the window transitions unimplemented. Evidence from `vitest --reporter=tap` (exit 1, 15 of 20 failing, `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK`, reason `target_test_failed`). Target test "shows no ply on load, then one more per tick, then the prompt" failed on `expected 'loading_window' to be 'lead_in'`. Semantic assessment: the target executed and failed on the planned phase assertion; the reducer ignored WINDOW_LOADED. The 5 tests that passed at RED are the session-level events and two "ignored when out of phase" guards that hold vacuously until the transitions exist; the single-answer guard was mutation-checked after GREEN (see below).
- **GREEN:** one handler per event (`windowLoaded`, `leadInTick`, `answerSubmitted`, `answerGraded`, `feedbackDone`, `advanceTick`, `nextWindow`, `sessionFinished`); 20/20 pass.
- **REFACTOR:** none.

## Verification

- From `frontend/`: `npm run lint` clean (max-depth), `npm run build` (tsc -b + vite) clean, `npm run knip` clean (only the two pre-existing configuration hints), full `npm test -- --run`: 358 files, 6124 tests passed.
- `grep -rnE "trackFeature|trackEvent|data-umami-event"` over the blunder-check components, hook and reducer prints nothing (D-19).
- Mutation checks, each reverted afterwards: letting `answerSubmitted` also accept the `grading` phase fails "ignores a late timeout after the click"; removing the `startInFlight` ref guard fails the double-click test (a sync double click otherwise sends two requests because `isPending` flips a render late).

## Deviations from Plan

### Auto-fixed / judgement calls

**1. [Rule 3 - Blocking] Error phase reached through a mocked initial state in the test**
- **Issue:** nothing dispatches FAILED until plan 07's drill component exists, so the "Back to start" test has no UI path into the error phase.
- **Fix:** `BlunderCheckTab.test.tsx` mocks `initialDrillState` with a getter returning an error state for that one test; RESET still returns the real idle state.
- **Files:** `frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx`

**2. [Scope note] Task 3's `Train.subnav.test.tsx` cases landed in the Task 1 commit**
- The non-beta redirect and Today-latch tests live in the file Task 1 already had to extend, so they were committed with the tracer. Nothing is missing.

**3. [Scope note] The git ledger file `gsd-plan-head-before-249-06` could not be written**
- The worktree git dir sits under the shared checkout path, which the sandbox refuses to write from this agent. `plan_head_before` is the dispatch base `ccf303990`, and `commits: 4` was counted from it with `git log ccf303990..HEAD`. The SUMMARY commit follows and is not counted.

**4. [Scope note] `.planning/WINDOWS.md` was not touched**
- The ledger is optional and plan 05 runs in parallel; the only stub is listed below.

## Known Stubs

| File | Reason |
|------|--------|
| `frontend/src/components/train/blunder-check/BlunderCheckTab.tsx` (`blunder-check-drill-area`) | Intentional empty drill area. After Start the tab shows only the header (loading_window); nothing calls `startWindow` yet. Plan 07 adds the board loop, timer, effects that start the window and schedule the ticks, the end screen and the FAILED dispatches. |

## Hand-off notes for plan 07 and 08

- `BlunderCheckTab` owns `useReducer(drillReducer, initialDrillState)`; render the drill in the `blunder-check-drill-area` slot (pass `state` and `dispatch`). Compose and window mutations come from `useBlunderCheckSession()` (`startWindow`, `answer`, `finish`); extend the hook rather than adding a second one.
- Tick scheduling: first lead-in tick after `LEAD_IN_START_DELAY_MS`, then every `LEAD_IN_PLY_INTERVAL_MS` until the reducer reaches `prompt` (N+1 ticks, the last is the hand-over). After `ANSWER_GRADED`, `FEEDBACK_DONE` after `FEEDBACK_DISPLAY_MS`, then `ADVANCE_TICK` after each `MOVE_REPLY_DELAY_MS` (two ticks; the second opens the next prompt). A window-ending answer goes `FEEDBACK_DONE` -> `window_over`.
- The `window_over` state keeps `graded` (including `better_move`, `reply_uci`) for plan 08; `window.shownUcis` there does not yet include the final prompted move or reply.
- Immersive: `BlunderCheckTab` reports `onImmersiveChange(true)` for lead_in, prompt, grading, feedback, advancing, window_over. `Train.tsx` hides the subnav and medal host then; it does not drop the phone top padding (no `useMarkPlayActive` yet).
- 409 `stale_prompt` on an answer should re-fetch via `startWindow`; no handling exists yet.
- The finishing state also covers the "all windows ended but not finished" resume case; plan 07 must call `finish` whenever the phase is `finishing`.

## Threat Flags

None beyond the plan's threat model. T-249-19 (non-beta redirect, tested) and T-249-29 (Start disabled plus a synchronous in-flight guard, tested and mutation-checked) are mitigated.

## Self-Check: PASSED

- Files exist: all six created and six modified files listed above.
- Commits `4f560dae2`, `cfe9f0e30`, `a298700a1`, `86ba9e27b` are ancestors of HEAD.

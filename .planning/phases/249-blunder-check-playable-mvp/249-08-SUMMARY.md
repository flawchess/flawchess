---
phase: 249-blunder-check-playable-mvp
plan: 08
subsystem: blunder-check-frontend
tags: [blunder-check, train, better-move, solution, vitest, tdd]
status: complete

requires:
  - phase: 249-05
    provides: better-move and solution endpoints (BetterMoveResponse, discriminated WindowSolution)
  - phase: 249-07
    provides: playable drill, window_over panel, useFinishSession
provides:
  - BlunderCheckBetterMove: playable pre-blunder board, server-decided tier for key and server-graded moves, browser-engine grade for off-key moves with Retry, +2/+1/+0 flash and Train sounds
  - BlunderCheckSolution: blunder (Your/Best/Game chips with line exploration), herring and false-alarm views, Analyze deep link, Next / See results
  - BlunderCheckGameFooter: own library line (with isError branch), foreign neutral line from game_info
  - Reducer phases better_move, better_move_grading, better_move_feedback, solution_loading, solution (window_over retired)
affects: [249-09]

tech-stack:
  added: []
  patterns:
    - "One session-scoped useTrainGradingEngine owned by the tab, enabled only once the drill has started"
    - "Line searches run one after another through an async runner (searchLinesInOrder); a failed search marks only its own chip"
    - "Hooks cannot be conditional, so own vs foreign footer is two components (OwnGameFooter calls useLibraryGame, ForeignGameFooter never does)"

key-files:
  created:
    - frontend/src/components/train/blunder-check/BlunderCheckBetterMove.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckGameFooter.tsx
    - frontend/src/lib/blunderCheckSolution.ts
    - frontend/src/lib/__tests__/blunderCheckSolution.test.ts
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx
  modified:
    - frontend/src/types/blunderCheck.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useBlunderCheckSession.ts
    - frontend/src/lib/blunderCheckDrill.ts
    - frontend/src/lib/__tests__/blunderCheckDrill.test.ts
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx

key-decisions:
  - "Better-move feedback is its own reducer phase (better_move_feedback, reusing FEEDBACK_DONE) so the server's totals update the header at once and the +N flash holds for the same 900 ms as an answer; a better-move step has no timer"
  - "A better-move post failure ends the drill in the error phase (same as an answer failure); only a grading failure gets Retry, because only that one has no server state yet"
  - "A failed solution fetch keeps the screen with a Retry (the window already ended and its points are banked), instead of the error phase"
  - "The solution's reveal engine (useTrainRevealTree) stays disabled until the line searches settle, so it never competes with them"
  - "The answer's own points flash is not carried across into the better-move board: the feedback hold (900 ms) ends it, the better-move step shows its own flash"
  - "Analyze navigates with plain react-router navigate; after Back the tab remounts idle and offers Resume (the next window), the better-move/solution state is not restored"

requirements-completed: [D-09, D-10, D-12, D-14, D-16, D-17, D-19]

actuals:
  tokens: 36000
  tasks: 3
  commits: 5
plan_head_before: a4e812205521496059e7213727a795bf940ffc6c
plan_head_after: f4a91d1e7bb594984959785a4148ba0479891865
---

# Phase 249 Plan 08: Better move and solution screens Summary

Every blunder-check window now ends on a solution screen built from the personalized-puzzle pieces: a caught blunder first asks for a better move on the pre-blunder board (graded by the server key, the server's own graded moves or the browser engine, scored +2/+1/+0 with the Train sounds), then every outcome (caught, missed, cleared, false alarm) lands on its solution with copy that never says "your move" on a stranger's game.

## Tasks

1. **Task 1 (tracer)**, commit `fda8ead74`: types, API client methods, hook mutations; reducer phases `better_move`, `better_move_grading`, `better_move_feedback`, `solution_loading`, `solution` replace the interim `window_over` panel; `BlunderCheckBetterMove` (drag-drop and click-click through `ChessBoard`, `startGrading` on entry, server tier posted at once for the key and server-graded moves, `gradeMove` otherwise with "Couldn't check your move." + Retry that restarts a dead engine first, +N flash and sounds); a blunder-only `BlunderCheckSolution` (heading, SAN sentence, Analyze, Next / See results); the tab owns one grading engine, enabled only once the drill started. Tab tests for the whole chain plus the reducer tests adapted to the new path.
2. **Task 2 (TDD)**, RED `74ee92752`, GREEN `c13a8348f`: `blunderCheckSolution.ts` chip model (search order key, better move, blunder; role merging; quality by tier), `useTrainRevealTree` + `TrainLineChips` + `TrainMoveTreeList` wiring, sequential line searches, lit-chip arrow, reveal engine gated on the searches.
3. **Task 3 (TDD)**, RED `aeb0a32db`, GREEN `f4a91d1e7`: `BlunderCheckGameFooter` (own library line with `isError`, foreign "player rated" line), herring ("All safe") and false-alarm ("False alarm", flagged arrow only) views, own vs foreign copy, hidden Analyze and footer when the game is gone.

## TDD notes

- **RED (task 2):** inert stub `blunderCheckSolution.ts` (returns `[]`) and a Solution without chips. 15 failing tests, all assertion or element-not-found failures on the planned behavior (e.g. "expected [] to deeply equal ['d2d4','b1c3','g1f3']", "Unable to find train-chip-your", "expected startGameMoveSearch to be called 1 times, but got 0"). `vitest --reporter=tap` exit 1. The reducer tests written in this task pass immediately: the plan puts the reducer implementation in the tracer (task 1), so they are characterization tests of already-green code, not RED. I did not run `gsd_run check tdd-red-evidence` (task-level `tdd="true"` in an `execute` plan, not a `type: tdd` plan).
- **RED (task 3):** inert footer stub; 6 failing tests (footer missing, "All safe" and "False alarm" headings missing, load-error copy missing); the absence-only tests pass trivially against the stub, which is expected.
- **Mutation checks:** running the line searches in parallel fails the sequential-order test and the failed-search test; forcing "You played" for a foreign window fails the foreign copy tests. Both were reverted.
- Two fixture bugs found and fixed in the tests before the GREEN commit (not behavior changes): a refutation `e5e4` that is illegal after 1. e4 e5 2. Nf3 (the pawn is blocked; now `d7d5`), and `formatTimeControl('600+0')` is "10+0", not "10".

## Verification

From `frontend/`: `npm run lint` clean, `npm run build` (tsc -b + vite) clean, `npm test -- --run` 361 files / 6195 tests passed, `npm run knip` clean (only the two pre-existing configuration hints). `grep -rnE "trackFeature|trackEvent|data-umami-event"` over the blunder-check folder, `useBlunderCheckSession.ts`, `blunderCheckDrill.ts` and `blunderCheckSolution.ts` prints nothing (D-19); the existing source-scan test also still passes. `Train.subnav.test.tsx` stays green, so a tab visit before Start still constructs no Worker.

## Deviations from Plan

**1. [Scope note] Reducer event `BETTER_MOVE_SUBMITTED` added.** The plan names `BETTER_MOVE_GRADED` and `SOLUTION_LOADED`; moving from `better_move` to `better_move_grading` needs a third event for the played move. `FEEDBACK_DONE` is reused for the better-move feedback hold, and a phase `better_move_feedback` exists (the plan's behavior text lists a "feedback" step in the chain).

**2. [Scope note] Two files outside `files_modified`:** `frontend/src/lib/blunderCheckSolution.ts` (pure chip model, so the logic is unit-testable) and its test `frontend/src/lib/__tests__/blunderCheckSolution.test.ts`. `BlunderCheckDrill.tsx` also changed (it renders the new phases), and `BLUNDER_CHECK_BOARD_MAX_WIDTH_PX` moved from the drill to `lib/blunderCheckDrill.ts` because three components share it.

**3. [Scope note] The git commit ledger file was not written** (the Write tool refuses paths inside the shared `.git`, same as in 06/07). `commits: 5` was counted with `git rev-list --count a4e812205..HEAD`; the SUMMARY commit follows and is not counted.

## Known behavior and limits

- A reload during the better-move step resumes on the next window, so that better move earns nothing (recorded in the plan and in the component docstring).
- Analyze then Back lands on the idle tab with Resume (the next window); the solution state is not restored.
- The answer's +N flash is cut when the answer feedback hold (900 ms) ends and the better-move board mounts; a better-move step shows its own flash.
- The solution board draws an arrow only at the puzzle position for the lit chip; below the root it shows the tree's last-move highlight and sideline markers but not the engine arrows TrainSolveScreen draws.
- Not covered by any test: real browser feel (flash animation, sounds, Stockfish Worker timing, board click-click through the real `ChessBoard`) and a physical-phone layout. The tab tests drive the board through the captured `onPieceDrop`.

## Known Stubs

None. Both RED-commit stubs (`blunderCheckSolution.ts`, `BlunderCheckGameFooter.tsx`) were replaced in their GREEN commits.

## Threat Flags

None beyond the plan's threat model. T-249-22 (client_tier on an off-key move is asserted by the phone; key and server-graded moves are decided by the server, points always come from the response), T-249-23 (foreign footer renders only `game_info`, never fetches the card, copy says "The player", asserted by test) and T-249-24 (false alarm renders only the flagged move, no Analyze or footer) hold.

## Self-Check: PASSED

- Files exist: all six created and eight modified files listed above.
- Commits `fda8ead74`, `74ee92752`, `c13a8348f`, `aeb0a32db`, `f4a91d1e7` are ancestors of HEAD.

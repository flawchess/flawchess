---
phase: 240-train-first-session-onboarding-load
plan: 04
subsystem: ui
tags: [react, typescript, train, onboarding, reveal-tour, vitest]

requires:
  - phase: 240-train-first-session-onboarding-load
    provides: "three-part tour model, useTrainWalkthrough latch and leave stamp, spotlit() helper and openReveal() (plan 03)"
provides:
  - "Parts 2 and 3 of the reveal tour proven end to end through the real solve screen, including the Analyze-button leave that part 1 never reaches"
  - "Per-reveal rules pinned by tests: latch against a mid-reveal stage write, restored reveal starts no part, a half-left part replays from 1 / n"
  - "Complete D-19 tour copy matrix (24 contexts x 7 steps) with the 145-char budget, no em-dash, no scoring word, no card / Solution / eval bar"
  - "Overlay and stampOnboarding docstrings describing the three-part tour and the five step names"
affects: [240-06, 240-07, train-frontend]

requirements-completed: [D-05, D-06, D-07, D-08, D-19, D-23]

actuals:
  tokens: 7500
  tasks: 2
  commits: 2
plan_head_before: 473007f40397f57e713034f3dc3cc52fc91e2b74
plan_head_after: fea19c33fd08365e701b2910f71bb0e5cfd65f92

tech-stack:
  added: []
  patterns:
    - "A test that rewrites the TanStack cache must wait one macrotask (setTimeout 20 inside act) before asserting: observer notifications are deferred, so a bare `await act(async () => {})` asserts against a screen that has not seen the write"
    - "Board-row spotlight asserted by walking the chessboard's ancestors through spotlit(), so plan 06 still swaps only the helper body"

key-files:
  created: []
  modified:
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/components/train/TrainTourOverlay.tsx
    - frontend/src/api/client.ts

key-decisions:
  - "renderScreen takes an optional trailing QueryClient so the latch case can rewrite the train settings cache; no other caller changes"
  - "Phone scroll cases stub Element.prototype.getBoundingClientRect before the reveal mounts, because the chips step is now part 2's FIRST step and its scroll fires as the verdict lands"
  - "Raw copy length (icon tokens included) is asserted against STEPPER_COPY_MAX_CHARS: stricter than rendered length, and every step passes"

patterns-established:
  - "Mutation-prove every new invariant case by reverting the production line it guards"

duration: 9min
completed: 2026-10-15
status: complete
---

# Phase 240 Plan 04: Tour Parts 2 and 3 Proof and Copy Matrix Summary

**Parts 2 (chips, stepping) and 3 (sidelines, understand, Analyze) are proven on consecutive reveals through the real solve screen, with the latch, restored-reveal and abandon/replay rules pinned and the whole D-19 tour copy checked against the 145-character budget; no production behavior changed.**

## Performance

- **Duration:** ~9 min
- **Completed:** 2026-10-15
- **Tasks:** 2
- **Files modified:** 4 (two test files, two docstrings)

## Accomplishments

- Stage 1 reveal: chips "1 / 2" (row not spotlit), then stepping "2 / 2" (list spotlit, bar icons, phone and desktop variants); the second bar Next stamps `reveal_tour_2` exactly once and flushes Next once.
- Stage 2 reveal: sidelines "1 / 3" (board spotlit, rewind icon), understand "2 / 3", Analyze "3 / 3" (bar not spotlit); `reveal_tour_3` is stamped exactly once through the bar Next AND through the Analyze button (the leave path part 1 never reaches), with the Analyze exit cached and no Next flush. The Analyze copy is checked for both analyze targets (game, position).
- Merged-chip sentences (Move = Best and Move = Game), icon tokens, desktop variants, arrow-set invariance across parts 2 and 3, and the three phone scroll cases are carried over from the retired walkthrough describe.
- Per-reveal rules: a stage write landing mid-reveal never switches the part and the leave still stamps `reveal_tour_1`; a restored reveal at stage 0 shows no overlay and stamps nothing; unmounting on part 3's last step stamps nothing and the next reveal replays "1 / 3"; Analyze from a middle step stamps nothing.
- Hide-on-interaction and Hilda's reopen badge on parts 1, 2 and 3 (chip tap, list tap, board touch, strip expand, fork, desktop).
- trainBotCopy.test.ts `reveal tour parts`: step map, stage map, answer kind, both Analyze strings, today's chips / stepping / sidelines / understand strings, target map, and the 7 x 24 context matrix (budget, no em-dash, no points or scoring word, no card, Solution button or eval bar).
- Docstrings: TrainTourOverlay (three parts, per-part counter "1 / 2") and `stampOnboarding` (five step names, forward-only `reveal_tour_stage`, stale "three" and "Plan 02" wording dropped).

## Task Commits

1. **Task 1: Parts 2 and 3 end to end (tracer)** - `1dc239b21` (test)
2. **Task 2: One part per reveal, abandon replay, hide and reopen, copy matrix, docstrings** - `fea19c33f` (test)

**Plan metadata:** committed separately after this file (docs).

## Verification

- `npm test -- --run`: 5649 tests passed (332 files). `-t "split reveal tour"`: 28 passed. `-t "reveal tour parts"`: 9 passed. Whole TrainSolveScreen file: green.
- `npm run build` (tsc -b + vite) exit 0; `npm run lint` clean; `npm run knip` exit 0 (two pre-existing `knip.json` configuration hints, unrelated).
- `grep -rn "reveal_walkthrough" frontend/src` prints nothing; `reveal_tour_2` x2 and `reveal_tour_3` x4 in the solve-screen test; `reveal_tour_3` and `1 / 2` present in client.ts and the overlay docstrings.
- Mutation checks (production line reverted, case must fail, then restored): removing `walkthrough.leave()` from `handleAnalyzeFromReveal` fails the Analyze-leave case; dropping the `isRestored` guard fails the restored-reveal case; letting `leave` stamp from any step fails the Analyze-from-a-middle-step case; replacing the latch (`latchedPart ?? livePart`) with `livePart` fails the latch case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Latch case was vacuous on first write**
- **Found during:** Task 2 mutation check
- **Issue:** With the latch removed the case still passed. `setQueryData` notifies TanStack observers on a deferred macrotask, so `await act(async () => {})` asserted before the screen had seen stage 1.
- **Fix:** wait one macrotask (`setTimeout` 20 ms inside `act`) after the cache write; re-ran the mutation and the case now fails without the latch.
- **Files modified:** frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
- **Commit:** fea19c33f (same commit as the case, never committed in its vacuous form)

**Plan-03 defects exposed:** none. Every new case passed against plan 03's hook and wiring unchanged, so no production code was touched.

**Total deviations:** 1 auto-fixed (a test written too weakly, fixed before commit). **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. T-240-17 is mitigated (latch, restored-reveal cases, each mutation-proven); T-240-18 is accepted by design and pinned by the abandon case.

## Issues Encountered

None. Note for plan 06: the board-row spotlight is read by walking the chessboard's ancestors through `spotlit()`, and the tree spotlight through `train-tree-tour-ring`; both flow through the one `spotlit()` helper body.

## Self-Check: PASSED

- FOUND: the four modified files; FOUND commits `1dc239b21`, `fea19c33f` (ancestors of HEAD); all `<acceptance_criteria>` greps and the full frontend chain re-run green.

---
phase: 236-train-phone-grade-instant-verdict
plan: 04
subsystem: frontend-train
tags: [train, stockfish-wasm, grading-engine, seed-193, serialization]
requires:
  - "Plan 02: GradeResult.phoneReading, gradeMoveInner exits"
provides:
  - "gradingSettledRef: startGameMoveSearch queues behind an in-flight gradeMove"
  - "GradeMoveOptions.onKeyLine / gradeMove(fen, uci, options?)"
affects:
  - "Plan 05 (instant branch overlaps reveal with grading), plan 06 (solution card from onKeyLine)"
tech-stack:
  added: []
  patterns:
    - "single queue slot as a settled-either-way promise ref, reset on generation bump"
key-files:
  created: []
  modified:
    - frontend/src/hooks/useTrainGradingEngine.ts
    - frontend/src/hooks/trainGradingSupport.ts
    - frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts
decisions:
  - "GradeMoveOptions is not re-exported from the hook (knip would flag it unused until plan 05/06 imports it); consumers import it from trainGradingSupport"
  - "The game-move == key shortcut moved inside the raced work, after the await, so it also reads an anchor that has settled"
metrics:
  tasks: 2
  completed: 2026-10-08
status: complete
actuals:
  tokens: 20000
  tasks: 2
  commits: 3
plan_head_before: 730136d3e82012a14ca337d014aeb348c719fa87
---

# Phase 236 Plan 04: Grading Worker serialization and early key line Summary

A reveal game-move search started while `gradeMove` is in flight now waits for it instead of `stop`ping it, and `gradeMove` can hand the think-time key line over via `onKeyLine` the moment the anchor settles.

## What was built

- **Task 1 (tracer), commit c97149ca8**: `gradingSettledRef` (a never-rejecting promise of the whole `gradeMoveInner`, anchor wait plus after-played search). `gradeMove` sets it; `startGrading` and `abortGrading` reset it to a settled promise. `startGameMoveSearch` keeps its synchronous engine-error and illegal-move rejections, and now does the anchor lookup, the game == key shortcut and the search inside the raced work after `await gradingSettledRef.current` plus a generation check that throws `'Reveal search superseded by a newer puzzle'`. Its own `TRAIN_GRADING_TIMEOUT_MS` race still bounds the total wait (T-236-14).
- **Task 2, commit 65edb50a0**: `GradeMoveOptions { onKeyLine? }` in `trainGradingSupport.ts`; `gradeMove(fen, uci, options?)` forwards it to `gradeMoveInner`, which calls `onKeyLine(anchor.keyLine)` once after the anchor checks pass, keyed anchors only, before the played == key and after-played exits.

## Tests

New describes in `useTrainGradingEngine.test.ts`: instant-path serialization (queued behind the played search then runs after grading resolves with `phoneReading` intact; fast mover gives anchor -> played -> game with zero `stop`; superseded while waiting never dispatches the old FEN and rejects) and `onKeyLine` (keyed fires once before the played result, played == key fires once, legacy never fires, no-options unchanged). The file went from 48 to 59 tests; every pre-existing test passes unmodified. Full frontend suite: 5259 passed. `npm run lint`, `npm run build`, `npm run knip` clean.

## Mutation proof (reverted afterwards)

Deleting `await gradingSettledRef.current` in `startGameMoveSearch`: the serialization test and the fast-mover test FAILED (2 failures, a `stop` posted / game `go` dispatched before the played bestmove); the superseded test still passed (it asserts rejection and no old-FEN dispatch, which the generation check also covers). Restored, 55/55 green.

## Deviations from Plan

None - plan executed as written.

## Notes

- `plan_head_before` is the worktree spawn base from the dispatch (the per-plan ledger file cannot be written under `.git/worktrees/` in this sandbox, same as plan 02). `commits: 3` counts the two task commits plus this SUMMARY commit.
- Behavior change to be aware of for plan 05: `startGameMoveSearch` is now always asynchronous, including the game == key shortcut (previously an already-resolved promise).

## Known Stubs

None.

## Threat Flags

None. T-236-14 is mitigated as planned (own timeout race, slot reset on `startGrading`/`abortGrading`).

## Self-Check: PASSED

- FOUND: `await gradingSettledRef.current` in `startGameMoveSearch`; `gradingSettledRef.current = ` appears 3 times; `export interface GradeMoveOptions` in `trainGradingSupport.ts`
- FOUND commits: c97149ca8, 65edb50a0

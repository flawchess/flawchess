---
phase: 236-train-phone-grade-instant-verdict
plan: 02
subsystem: frontend-train
tags: [train, phone-grade, seed-193, recheck, stockfish-wasm]
requires:
  - "Plan 01 wire contract: app/schemas/train.py PhoneGrade (six keys, extra forbid)"
provides:
  - "lib/trainPhoneGrade.ts: PhoneReading, buildPhoneGradePayload"
  - "GradeResult.phoneReading on every gradeMoveInner exit"
  - "SolveRequest.phone_grade on keyed solves (frozen with the payload)"
  - "TrainPuzzle.server_graded_moves typed, single read site in TrainSolveScreen"
  - "shouldRecheck D-11 exclusion via serverGradedUcis"
affects:
  - "Plan 05 (instant path builds on phoneReading and serverGradedMoves)"
tech-stack:
  added: []
  patterns:
    - "module-local schema version const mirrored from the server (RECHECK precedent)"
    - "optional field on GradeResult so restored reveal-cache entries stay valid"
key-files:
  created:
    - frontend/src/lib/trainPhoneGrade.ts
    - frontend/src/lib/__tests__/trainPhoneGrade.test.ts
  modified:
    - frontend/src/types/train.ts
    - frontend/src/hooks/trainGradingSupport.ts
    - frontend/src/hooks/useTrainGradingEngine.ts
    - frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/lib/trainRecheck.ts
    - frontend/src/lib/__tests__/trainRecheck.test.ts
decisions:
  - "PhoneReading lives in lib/trainPhoneGrade.ts and is imported as a type by the hook support file, so lib never imports from hooks"
  - "phoneReading is optional on GradeResult: reveal-cache entries predate it and a re-check's replacement grade carries none"
metrics:
  tasks: 2
  completed: 2026-10-08
status: complete
actuals:
  tokens: 30000
  tasks: 2
  commits: 3
plan_head_before: 4c0c4997abf2917d1efca21500f8ad23fc9c354a
plan_head_after: c888f89c9f94d51838848eb7bf983201e67c35c8
---

# Phase 236 Plan 02: Client phone_grade record and D-11 re-check exclusion Summary

The phone's 1.5 s after-key / after-played reading (tier, expected scores, depths) is now POSTed as a six-key `phone_grade` record on every keyed solve, and a move in the puzzle's server-graded set is never re-checked at 3 s.

## What was built

- **Task 1 (tracer)**: `buildPhoneGradePayload` (null depth sent as 0), `PhoneGrade` / `SolveRequest.phone_grade` types, `GradeResult.phoneReading`, the after-played exit of `gradeMoveInner` filling it (null on a legacy anchor), and `gradeAndSolve` capturing it before `runRecheck` and spreading it into the solve body. Commit a3f24baae.
- **Task 2**: every other `gradeMoveInner` exit: played == key records a good tier with an equal pair from the think-time anchor (D-05), the anchor-mismatch and illegal-move fallbacks and the legacy anchor record nothing (D-06). `ServerGradedMove` / `TrainPuzzle.server_graded_moves` typed; `serverGradedMoves` memo is the single read site and `serverGradedUcis` feeds `shouldRecheck`, which returns false for any played move in the set (D-11). Commit c888f89c9.

## Tests

- New `trainPhoneGrade.test.ts` (field map, null depth to 0, exactly six keys, D-07).
- Hook describe for D-04/D-05/D-06 (key pair equal, off-key pair from anchor and after-played search, legacy anchor, both fallbacks).
- `trainRecheck.test.ts`: `BASE` gets `serverGradedUcis: []`; new D-11 describe.
- `TrainSolveScreen.test.tsx`: D-01/D-13 off-key POST, D-05 key, D-06 no-key, D-04 re-check keeps the 1.5 s reading (tier inaccuracy while move_quality is good), D-13 retry resends the identical body with phone_grade, D-11 server-graded move dispatches no 3 s search and posts no recheck.
- Full frontend suite: 5252 passed. `npm run lint`, `npm run build`, `npm run knip` clean.
- D-03 grep gate prints exactly `TrainSolveScreen.tsx` and `types/train.ts`; `grep -c "phoneReading:"` in the hook prints 4.

## Mutation proof (each reverted afterwards, tree clean)

| Mutation | Result |
| --- | --- |
| (a) capture `phoneReading` after `runRecheck` | D-04 component test FAILED (1 failure) |
| (b) drop the `anchor.legacy ? null :` guard on the after-played exit | D-06 hook test FAILED (1 failure) |
| (c) remove the `serverGradedUcis` check | 3 D-11 shouldRecheck cases and the D-11 component test FAILED (4 failures) |

## Deviations from Plan

None - plan executed as written.

## Notes

- The per-plan commit ledger file could not be written under `.git/worktrees/` (the sandbox blocks writes there), so `plan_head_before` is the worktree spawn base recorded in the dispatch (4c0c4997a). `commits: 3` counts the two task commits plus this SUMMARY commit.
- `shouldRecheck`'s server-graded exclusion is the pure-rule guarantee; after plan 05 a non-key server-graded move will take the instant path and never reach `runRecheck` at all.

## Known Stubs

None.

## Threat Flags

None. The client-built `phone_grade` (T-236-07) is validated server-side by plan 01; the single `server_graded_moves` read site (T-236-08) is enforced by the grep gate above.

## Self-Check: PASSED

- FOUND: frontend/src/lib/trainPhoneGrade.ts, frontend/src/lib/__tests__/trainPhoneGrade.test.ts
- FOUND commits: a3f24baae, c888f89c9

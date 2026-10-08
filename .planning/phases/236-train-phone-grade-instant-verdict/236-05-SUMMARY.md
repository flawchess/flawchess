---
phase: 236-train-phone-grade-instant-verdict
plan: 05
subsystem: frontend-train
tags: [train, instant-verdict, phone-grade, seed-193, telemetry]
requires:
  - "Plan 02: PhoneReading, buildPhoneGradePayload, serverGradedMoves memo, GradeResult.phoneReading"
  - "Plan 03: TrainPuzzle.server_graded_moves populated by the compose route"
  - "Plan 04: startGameMoveSearch queues behind the in-flight grade (gradingSettledRef)"
provides:
  - "instantServerTier(moves, playedUci, keyUci)"
  - "Instant branch in TrainSolveScreen: solveInstantly + gradeInBackground + instantAttemptRef"
  - "useTrainPuzzleTelemetry.setLatePhoneGrade; phone_grade on both review flush bodies"
  - "ReviewRequest type; postReviewKeepalive(body: ReviewRequest)"
affects:
  - "Plan 06 (loading/failed line cards render on top of this path)"
tech-stack:
  added: []
  patterns:
    - "attempt-counter ref guard for background work on a component reused across puzzles"
    - "late-record slot keyed by the telemetry hook's own (session, position) key"
key-files:
  created: []
  modified:
    - frontend/src/lib/trainPhoneGrade.ts
    - frontend/src/lib/__tests__/trainPhoneGrade.test.ts
    - frontend/src/types/train.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useTrainPuzzleTelemetry.ts
    - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
decisions:
  - "Played == key stays on the graded path even though the key is listed for soft/herring puzzles (instantServerTier returns null), so its D-05 record still rides the POST"
  - "isGrading is never set on the instant path; the bubble keeps the move prompt for the round trip (plan 06 adds the copy-less spinner)"
metrics:
  tasks: 2
  completed: 2026-10-08
status: complete
actuals:
  tokens: 40000
  tasks: 2
  commits: 3
plan_head_before: 086966c73c3655194c0c96084c92b8fd25e0631e
---

# Phase 236 Plan 05: Instant server-graded verdict with late phone_grade Summary

A played non-key move from the puzzle's `server_graded_moves` now POSTs immediately with the payload tier and renders its verdict after one round trip, while the phone's 1.5 s after-move search keeps running in the background and its reading rides the next review flush.

## What was built

- **Task 1 (tracer), commit 9ccad20c4**
  - `instantServerTier` (lib): null for a null key or played == key, else the tier of the first matching entry.
  - `ReviewRequest extends ReviewTelemetry { phone_grade? }` in `types/train.ts`; `postReviewKeepalive` takes it.
  - `useTrainPuzzleTelemetry`: `latePhoneGradeRef` (cleared with the other per-puzzle refs on a key change), `setLatePhoneGrade(sessionId, position, record)` which stores only when `${sessionId ?? 'none'}:${position}` equals the current key, and a shared `buildReviewBody` used by both `flushReviewNonNext` and `flushReviewOnNext`.
  - `TrainSolveScreen`: `instantAttemptRef` (bumped in the per-puzzle reset effect), a branch at the top of `gradeAndSolve`, `solveInstantly` (starts the background grade before the POST, no phone_grade, no recheck, never sets `isGrading`) and `gradeInBackground` (guarded by the attempt counter; success sets `gradeResult` and the late record; rejection is silent).
- **Task 2, commit 7726e2167**: component and telemetry tests for Pitfall 1, D-15, Pitfall 4 and the late-record slot (production code unchanged).

## Tests

- `trainPhoneGrade.test.ts`: six `instantServerTier` cases (key null, played == key while listed, listed non-key, first match wins, unlisted, empty list).
- `TrainSolveScreen.test.tsx`: `HeldPositionWorker` (holds searches on a given FEN, releases on `stop`, counts stops that arrive while a search is held), a `gradeMoveOverride` Harness prop, and five instant-path tests: tracer (POST at once with `move_quality: 'good'`, no `phone_grade`/`recheck`, no grading indicator, Next flush carries the full `phone_grade`), key path keeps the POST record, Pitfall 1 end to end, D-15 rejection, Pitfall 4 stale grade. The Your-move wait asserts "present and no `-loading` child" so plan 06 needs no rewrite.
- `useTrainPuzzleTelemetry.test.ts`: six late-record cases (Next flush, hidden flush, no record -> no key, flush before the record carries none, stale (session, position) ignored, position change clears).
- Full frontend suite: 314 files, 5276 tests passed. `npm run lint`, `npm run build`, `npm run knip` clean. D-03 read-site gate prints exactly `TrainSolveScreen.tsx` and `types/train.ts`.

## Mutation proof (each reverted afterwards)

| Mutation | Result |
|----------|--------|
| (a) delete `await gradingSettledRef.current` in `useTrainGradingEngine.ts` | component Pitfall 1 test FAILED (`heldCount` 0: the reveal search's `stop` released the held background search) |
| (b) drop `attempt !== instantAttemptRef.current` in `gradeInBackground` | component Pitfall 4 test FAILED (the stale grade's Your-move box appeared on puzzle B) |
| (c) drop the key comparison in `setLatePhoneGrade` | telemetry "record for a puzzle the user already left" test FAILED |

After (a), `git diff --quiet -- frontend/src/hooks/useTrainGradingEngine.ts` exits 0 (this plan does not change that file).

## Deviations from Plan

None - plan executed as written. The telemetry hook tests listed under Task 2 were written during Task 1 and committed with Task 2.

## Notes

- `plan_head_before` is the worktree spawn base from the dispatch; `commits: 3` counts the two task commits plus this SUMMARY commit.
- `grade.phoneReading == null` (loose) is used in `gradeInBackground` to cover both `null` and the optional `undefined` of restored/legacy results.

## Known Stubs

None.

## Threat Flags

None. T-236-12 (set read only after the move, D-03 grep gate passes), T-236-13 (attempt guard plus key comparison, both mutation-proven), T-236-15 accepted as planned.

## Self-Check: PASSED

- FOUND: `export function instantServerTier`, `export interface ReviewRequest extends ReviewTelemetry`, `body: ReviewRequest`, `setLatePhoneGrade` (interface, definition, memo), `async function solveInstantly`, `function gradeInBackground`, `instantAttemptRef`
- FOUND commits: 9ccad20c4, 7726e2167

---
phase: 236-train-phone-grade-instant-verdict
plan: 06
subsystem: frontend-train
tags: [train, instant-verdict, reveal, seed-193, changelog]
requires:
  - "Plan 04: gradeMove onKeyLine option, serialized game-move search"
  - "Plan 05: solveInstantly / gradeInBackground / instantAttemptRef"
provides:
  - "InstantGradeState / InstantGradeStatus (trainGradingSupport.ts)"
  - "TrainReveal instantGrade prop, LineBox.pending, PendingLineCard, revealBestUciOf helper"
  - "TrainSolveScreen instantGrade + isSubmitting state, revealBestUci, gated showEvalBar"
  - "trainBubbleState { kind: 'submitting' } and train-submitting-indicator"
affects: []
tech-stack:
  added: []
  patterns:
    - "primitive effect dep (revealBestUci) instead of an object dep so a pending->landed swap does not re-dispatch an effect"
key-files:
  created: []
  modified:
    - frontend/src/hooks/trainGradingSupport.ts
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/trainBubbleState.ts
    - frontend/src/components/train/__tests__/trainBubbleState.test.ts
    - CHANGELOG.md
decisions:
  - "Eval bar is gated off while the background search is pending (RESEARCH Pitfall 2), so its Worker cannot compete with the phone reading that becomes the phone_grade record"
  - "revealBestUciOf is a module-level helper in TrainReveal so the your/best/effect sites share one definition"
  - "Analyze before the background grade lands is an accepted gap (RESEARCH A2), documented at handleAnalyzeClick"
metrics:
  tasks: 3
  completed: 2026-10-08
status: complete
actuals:
  tokens: 45000
  tasks: 3
  commits: 4
plan_head_before: d8fe2fad94bd832650fedf91e458f7bd83a7612d
plan_head_after: d09f691623fabf7377b10349194e6a3b07fd90c7
---

# Phase 236 Plan 06: Instant reveal states, board fallbacks, changelog and phase gate Summary

On a server-graded move the reveal now opens on the verdict with a loading Your-move card, the solution card shows the key line as soon as the anchor settles, a failed background search leaves a header-only card, and the badge, arrows, bubble and eval bar all read from the server verdict and the key while the phone grade is pending.

## What was built

- **Task 1 (tracer), commit c596d8ba8**
  - `InstantGradeStatus` / `InstantGradeState { status, keyUci, keyLine }` in `trainGradingSupport.ts`.
  - `TrainReveal`: `instantGrade` prop; `LineBox.pending: 'loading' | 'failed' | null`; `buildLineBoxes` takes `instantGrade` (your role exists from the verdict alone, best UCI and line fall back to the key and the early key line); `PendingLineCard` (same Card shell, header and spotlight handlers; 'loading' body copies the `train-game-line-loading` markup under `${testid}-loading`; 'failed' is the header alone with `data-line-status="failed"`); the game-search effect depends on the primitive `revealBestUci`, not the `gradeResult` object (Pitfall 5).
  - `TrainSolveScreen`: `instantGrade` state (reset per puzzle); `solveInstantly` takes the non-null key and sets `pending`; `gradeInBackground` passes `onKeyLine` (attempt-guarded), clears `instantGrade` on success and sets `failed` on rejection (still no gradingError, no record).
- **Task 2, commit f7cd3b181**
  - `trainBubbleState`: `{ kind: 'submitting' }` and `isSubmitting` input, precedence verdict > grading > submitting > move > intro > drop-nudge > prompt. `train-submitting-indicator` is a Loader2 with `aria-label="Saving your move"` and no visible text.
  - `TrainSolveScreen`: `isSubmitting` around the instant POST (`finally` clears it); `revealBestUci = gradeResult?.bestMoveUci ?? instantGrade?.keyUci ?? null` feeds the overlay best arrow (so the key is never an Also-fine arrow), the pristine set, `gameMoveQuality` and `playedMoveQuality`; `playedMoveQuality` follows the server `graded_es_*` pair without a `gradeResult`; `revealOverlay.playedMove` no longer needs `gradeResult`; `showEvalBar = showResultRow && instantGrade?.status !== 'pending'`; documented comments at `handleAnalyzeClick` (A2 gap), `freePlaySeedEval` and `pristineOverlayUcis`.
- **Task 3, commit d09f69162**: CHANGELOG `[Unreleased]` / Changed bullet, then the full phase-wide gate.

## Tests

- `TrainReveal.test.tsx`: new `instant-path line cards` describe (5 tests): both cards loading, key line early with the Your-move card still loading, failed header-only card, landed grade renders both ready, grade landing with the same best UCI calls `startGameMoveSearch` exactly once.
- `TrainSolveScreen.test.tsx`: D-14 loading-then-fills, D-16 copy-less spinner for the held POST, D-16 server-pair badge + key arrow + eval bar waiting for the grade, D-09 payload tier `inaccuracy` never rendered (points flash and Your-move chip match the server `good`). Plan 05's Pitfall 4 test now asserts puzzle B's Your-move card is loading (A's grade never lands on B); the D-15 test also asserts `data-line-status="failed"` and no `train-game-line-error`. The plan 05 wait helper already required "present and no `-loading` child", so the tracer and Pitfall 1 tests passed unchanged.
- `trainBubbleState.test.ts`: submitting rows (alone, loses to verdict and grading, beats move/intro/drop-nudge).

## Mutation proof (each reverted afterwards)

| Mutation | Result |
|----------|--------|
| (a) drop the `instantGrade?.keyUci` fallback from `revealBestUci` | D-16 arrows test FAILED (`expected ['e2e4'] to include 'd2d4'`) |
| (b) restore `showEvalBar = showResultRow` | D-16 test FAILED (eval-bar placeholder assertion) |
| (c) `setIsGrading(true)` instead of `setIsSubmitting(true)` around the POST | spinner test FAILED (plus the other instant-path tests, which then hang on a never-cleared grading state) |
| bonus: add `gradeResult` back to the game-search effect deps | Pitfall 5 test FAILED (`startGameMoveSearch` called 2 times) |

## Gate results (plans 01-06 applied)

- `ruff format` (no changes), `ruff check --fix` clean, `ty check app/ tests/ scripts/` clean, analysis `ty` clean, `check_function_size.py --fail-over-depth 4` OK (1163 functions).
- `uv run pytest -n auto -x`: 5436 passed, 19 skipped.
- Serial train backend files: 498 passed.
- Frontend: `npm run lint`, `npm run build`, `npm test -- --run` (5288 passed), `npm run knip` all clean.
- Phase 235 gate A grep prints exactly `TrainReveal.tsx`, `TrainSolveScreen.tsx`, `types/train.ts`.

## Deviations from Plan

None - plan executed as written. The three task commits are split by file/hunk after the fact: the working tree was built in one pass, then Task 2's hunks were temporarily stripped to commit the Task 1 tracer state on its own (lint, tsc and the train vitest suite were green on that intermediate state).

## Manual browser UAT (pending for /gsd-verify-work)

1. Desktop Chrome, a soft SR puzzle or herring with a known "also fine" alternative: play that alternative. Verdict within about one round trip, no "Checking your move…" copy, Your-move card shows "Loading…" then fills about 1.5 s later, eval bar appears after it, Next works.
2. `SELECT move_quality, phone_grade, played_move FROM drill_solves WHERE user_id = <dev user> ORDER BY solved_at DESC LIMIT 3`: phone_grade object for the instant solve (review flush) and for a normal keyed solve (POST), SQL NULL for a legacy no-key solve.
3. A sharp SR puzzle: play a listed server-graded wrong move: verdict immediate, graded "wrong" by the server.
4. Report-only: real-phone timing and eval-bar contention; inspect prod phone_grade depths after release.

## Known Stubs

None.

## Threat Flags

None. T-236-16 (the key feeds only overlay/pristine/quality memos that render after `verdict !== null`; Phase 235 gate A grep unchanged), T-236-17 (D-09 component test).

## Self-Check: PASSED

- FOUND: `export interface InstantGradeState`, `function PendingLineCard`, `revealBestUciOf`, `kind: 'submitting'`, `data-testid="train-submitting-indicator"`, `status !== 'pending'`, `onKeyLine` in TrainSolveScreen, CHANGELOG bullet under `[Unreleased]`
- FOUND commits: c596d8ba8, f7cd3b181, d09f69162

---
phase: 235-train-grading-server-answer-key
fixed_at: 2026-10-07T22:10:00Z
review_path: .planning/phases/235-train-grading-server-answer-key/235-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 235: Code Review Fix Report

**Fixed at:** 2026-10-07
**Source review:** .planning/phases/235-train-grading-server-answer-key/235-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, WR-02; Info findings out of scope)
- Fixed: 2
- Skipped: 0

Verification ran in the main checkout (`workflow.use_worktrees` unset and the caller required gates from `frontend/`, which a fresh worktree cannot run without `node_modules`), on branch `gsd/phase-235-train-grading-server-answer-key`. Gates after each fix: `npm run lint`, `npm run build` (tsc -b), `npx vitest run src/hooks src/components/train src/lib` (189 files, 3503 tests passed). After WR-02 also `npm run knip` (clean apart from a pre-existing `.css` configuration hint).

## Fixed Issues

### WR-01: A re-check that outlives its timeout keeps driving the engine and can starve the reveal search

**Files modified:** `frontend/src/hooks/useTrainGradingEngine.ts`, `frontend/src/hooks/__tests__/useTrainGradingEngine.test.ts`
**Commit:** 6fba4d350
**Applied fix:** `recheckMove` creates an `AbortController` and aborts it in the timeout callback. `recheckMoveInner` takes the signal and returns null before dispatching the second (played) search if it is aborted, with a comment at the fix site explaining what broke. The generation was deliberately NOT bumped on timeout, because that would invalidate the anchor the reveal still needs. New test `(d2)` proves the late key answer after the timeout posts no further `go`; reverting the guard makes it fail (`expected 4 to be 3`), re-confirmed after the WR-02 refactor.

### WR-02: `useTrainGradingEngine` hook body has grown to roughly 790 lines

**Files modified:** `frontend/src/hooks/useTrainGradingEngine.ts`, `frontend/src/hooks/trainGradingSupport.ts` (new)
**Commit:** b1b7c9819
**Applied fix:** Behavior-preserving extraction into a new sibling module `trainGradingSupport.ts` (pure, React-free):
- `raceWithTimeout(work, ms, timeoutMessage, failureMessage)`: one shared settle-once race, replacing the three hand-rolled `settled`/timer wrappers in `gradeMove`, `recheckMove` and `startGameMoveSearch`. It aborts a signal on timeout, which is what carries the WR-01 guard. `recheckMove` keeps its never-rejects semantics by mapping rejection to null after the race, and the anchor swap still happens only on success.
- `planRecheck` / `finishRecheck`: the re-check precondition check and the grade/record/anchor build, so `recheckMoveInner` is now just plan, two searches, finish.
- `buildSearchResult`: the bestmove MultiPV commit, called from the UCI `bestmove` branch.
- The search/grade types and pure helpers (`terminalSearchResult`, `keyedAnchorFrom`, `legacyAnchorFrom`, `clampLineEvalToBest`, `fenAfterUciMove`) moved over; the hook re-exports `GradeResult`, `RecheckResult`, `TrainEngineLine` so no importer changed.

The hook file went from 1251 to 902 lines; the support module is 468 lines. The hook function itself is still long.

**Not done (judgement call, recorded rather than forced):** the UCI `handleLine` dispatcher was not moved out of the hook. It mutates nine hook refs (state, stop-pending, queued dispatch, pending, ready-dispatch, pvMap, ready flag), `setIsReady` and `dispatchNow`; extracting it would need a context object of refs that always run together, which the task said to avoid. Only its pure bestmove-commit seam was extracted. The Worker lifecycle effect and the `search`/`dispatchNow` state machine also stay in the hook for the same cohesion reason. Further shrinking would need a separate decision (for example a `useStockfishWorker` hook owning the state machine), which is outside this review fix.

---

_Fixed: 2026-10-07_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

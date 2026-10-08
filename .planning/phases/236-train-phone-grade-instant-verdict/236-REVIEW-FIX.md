---
phase: 236-train-phone-grade-instant-verdict
fixed_at: 2026-10-08T22:15:00Z
review_path: /home/aimfeld/Projects/Python/flawchess/.planning/phases/236-train-phone-grade-instant-verdict/236-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: partial
---

# Phase 236: Code Review Fix Report

**Fixed at:** 2026-10-08T22:15:00Z
**Source review:** /home/aimfeld/Projects/Python/flawchess/.planning/phases/236-train-phone-grade-instant-verdict/236-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, WR-02; Info findings out of scope)
- Fixed: 2 (WR-02 only in part, see below)
- Skipped: 0 whole findings; one sub-option of WR-02 (option b, Next) skipped with reasoning
- Status is `partial` because WR-02 option (b) was not implemented.

**Verification environment:** the main checkout on branch `gsd/phase-236-train-phone-grade-instant-verdict`, not an isolated worktree. The caller directed commits on the current branch and the npm gates, and a hand-rolled worktree has no `node_modules`. Gates run after both fixes: `npm run lint` clean, `npx tsc -b` clean, `npm run knip` clean, `npm test -- --run src/components/train src/hooks src/lib` 190 files / 3563 tests passed.

## Fixed Issues

### WR-01: A grading-engine Worker error after the verdict hides the verdict bubble and its Next button (violates D-15)

**Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`, `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`
**Commit:** 222f9efcb
**Applied fix:** The engine-error branch and the engine-loading branch now apply only while `verdict === null` (`engineFailed && verdict === null`, `!isReady && verdict === null`), so a landed verdict bubble with its Solution/Analyze/Next row is never displaced. Bug-fix comment at the site. Regression test `WR-01/D-15`: on the instant path with the background search held, the real hook's `worker.onerror` is fired after the verdict; asserts no `train-engine-error` / `btn-train-engine-retry` and that `train-verdict-guess` and `btn-train-next` are still rendered.
**Proof the test bites:** with `TrainSolveScreen.tsx` reverted (git stash), the test failed at `expect(train-engine-error).toBeNull()`; with the fix restored it passes. Full `TrainSolveScreen.test.tsx` 133/133 afterwards.
**Note:** requires human verification of one side effect. The loading gate also changed for restored reveals (verdict present, engine not yet ready): the bubble now shows instead of "Loading engine…". This follows the review's suggested gating and no existing test depends on the old behavior.

### WR-02: Analyze or Next pressed before the background grade lands (Analyze half fixed)

**Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`, `frontend/src/hooks/trainGradingSupport.ts`, `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`
**Commits:** 86a545512 (fix and tests), 1f99cfedc (documents the remaining gap at the code site)
**Applied fix (option a, Analyze):** `handleAnalyzeClick` no longer bails when `gradeResult === null` on the instant path. A new pure helper `gradeFromServerPair(verdict, instantGrade)` builds a stand-in `GradeResult` from the verdict's server graded pair (`graded_es_before/after`, real numbers, no fabricated 0.5), the key as `bestMoveUci`, the think-time key line when the anchor had settled, an empty played line, and `phoneReading: null`. It returns null when the verdict has no server pair, in which case the old no-cache behavior is kept rather than caching invented numbers. Browser Back now restores the solved reveal with a header-only Your-move card (the D-15 failed look).
**Tests:** `WR-02` caches from the server pair and survives a restore round trip (cleanup, remount with `restoredSolve = readTrainRevealCache()`, verdict and best-move card render, no grading error); `WR-02` without a server pair caches nothing. Proof: with the source reverted the first test failed (`expected null not to be null`); restored it passes.

## Skipped Issues

### WR-02 option (b): trailing review flush for Next pressed before the grade lands

**File:** `frontend/src/components/train/TrainSolveScreen.tsx:1231-1250` (`gradeInBackground`)
**Reason:** Not implementable cleanly, and the review's premise does not hold. Pressing Next advances `puzzle.fen`, whose effect cleanup calls `abortGrading()` and then `startGrading()` for the next puzzle. The grading engine is a single Worker, and `startGrading` bumps the generation, so the in-flight played-move search is superseded and never produces a reading. There is therefore nothing to flush when "the in-flight grade settles"; a trailing flush for the captured `(sessionId, position)` would only ever carry a rejection. Recovering the reading would require holding the puzzle transition until the grade settles (bounded by `TRAIN_GRADING_TIMEOUT_MS`), which adds latency to Next and works against the phase's instant-verdict goal, or running a second grading Worker (a large restructure and a memory risk on phones, a known project failure class). Both are owner decisions, not review-fix scope.
**What was done instead:** the gap and its selection bias (fast Next presses are under-sampled, so the audit is skewed toward fast or patient users) are documented in the `gradeInBackground` docblock (commit 1f99cfedc). The review's minimum ask, recording the sizing assumption and bias caveat, should also go into the SEED-193 follow-up so the audit is not read as unbiased; that planning-doc edit was not made here.
**Original issue:** Next pressed before the background grade lands silently drops the phone_grade record, biasing the audit toward fast devices.

---

_Fixed: 2026-10-08T22:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

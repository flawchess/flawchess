---
phase: 237-train-reveal-chips-move-tree
fixed_at: 2026-10-09T00:00:00Z
review_path: .planning/phases/237-train-reveal-chips-move-tree/237-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 237: Code Review Fix Report

**Fixed at:** 2026-10-09
**Source review:** .planning/phases/237-train-reveal-chips-move-tree/237-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01..WR-04; IN-* out of scope for `critical_warning`)
- Fixed: 4
- Skipped: 0

**Verification location:** all gates ran in the MAIN checkout (no worktree). The orchestrator asked for commits directly on `gsd/phase-237-train-reveal-chips-move-tree`, and a fresh worktree has no `node_modules` for the frontend gates. No recovery sentinel or temp branch was created.

**Gates after the last fix:** `npm run lint` clean, `npx tsc -b --noEmit` clean, `npm run knip` clean. The fixer's first full `npx vitest run` showed one failure, `TrainReveal.test.tsx > a rejecting game-move search reports the error state...`. It reported this as pre-existing, but the orchestrator found the test passes at the pre-fix base (`eae0c5163`). WR-01 caused it: the fixture paired the default `bestMoveUci: 'e2e4'` (which equals the game move) with `bestLine: ['g1f3']`. The fixture now sets `bestMoveUci: 'g1f3'` (358f21567). Full suite after that: 320 files, 5424 tests passed.

## Fixed Issues

### WR-01: Restored reveal from the Analyze stand-in grade shows a permanent "…" eval pill and can lose the Best chip

**Files modified:** `frontend/src/lib/trainRevealLines.ts`, `frontend/src/components/train/TrainLineChips.tsx`, `frontend/src/components/train/TrainSolveScreen.tsx`, `frontend/src/lib/__tests__/trainRevealLines.test.ts`, `frontend/src/components/train/__tests__/TrainLineChips.test.tsx`
**Commit:** e6e27ad71
**Applied fix:**
- `revealBestUciOf` now reads `gradeResult.bestMoveUci` (falling back to `instantGrade.keyUci`) instead of `bestLine.moves[0]`.
- `TrainSolveScreen.revealBestUci` now calls `revealBestUciOf`, so the predicate exists once.
- `ChipEval` hides the pill when the line has neither `evalCp` nor `evalMate`.
- Added tests for an empty stand-in `bestLine` (the Best chip still exists) and for the hidden pill. Reverting the `revealBestUciOf` change makes the new test fail.

### WR-02: Reveal action bar mounted twice (duplicate testids)

**Files modified:** `frontend/src/hooks/useIsDesktop.ts`, `frontend/src/components/train/TrainSolveScreen.tsx`, `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`, `frontend/src/pages/__tests__/Train.solveLoop.test.tsx`
**Commit:** 24ba06770
**Applied fix:**
- Added `useIsSmUp()` (640px, the Tailwind `sm` breakpoint) to `useIsDesktop.ts`. A shared private `useMinWidth` now backs both it and `useIsDesktop`.
- The in-flow `TrainRevealActionBar` mounts only when `isSmUp`. Its `hidden sm:flex` CSS is replaced by `w-full`.
- `mobileBoardControls` is published only when `!isSmUp`, so the fixed bottom bar exists only on phones. Exactly one instance of each bar testid is ever in the DOM.
- Test changes:
  - `TrainSolveScreen.test.tsx`: the matchMedia stub is now query-aware, with a separate `smUpMatches` flag. The probe-based tests render as phone width. The `mbc-analyze-to` assertion now compares to `buildGameAnalysisUrl(100, 19)` and checks that `btn-train-analyze` is absent.
  - `Train.solveLoop.test.tsx`: stubs a tablet width (sm up, below lg).

### WR-03: Game-footer Analyze link bypasses `walkthrough.leave()`

**Files modified:** `frontend/src/components/train/TrainSolveScreen.tsx`
**Commit:** 996042af5
**Applied fix:** `TrainReveal` now receives `onAnalyzeClick={handleAnalyzeFromReveal}`, so both Analyze controls run the same handler (walkthrough stamp, then `handleAnalyzeClick`). A comment at the fix site explains why. No new test was added, because the existing suites cover the handler path.

### WR-04: Tapping the already-shown move counts as a line step

**Files modified:** `frontend/src/hooks/useTrainRevealTree.ts`, `frontend/src/hooks/__tests__/useTrainRevealTree.test.ts`
**Commit:** b36fe01ae
**Applied fix:** `goToNode` returns early when `currentNodeId === id`, as well as when the node is unknown. A new test checks that a repeated `goToNode` on the same node reports one step, not two. Reverting the guard makes that test fail.

---

_Fixed: 2026-10-09_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

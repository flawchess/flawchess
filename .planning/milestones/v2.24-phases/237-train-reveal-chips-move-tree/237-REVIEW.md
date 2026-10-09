---
phase: 237-train-reveal-chips-move-tree
reviewed: 2026-10-09T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - app/schemas/train.py
  - frontend/src/App.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/board/boardMarkers.tsx
  - frontend/src/components/board/ChessBoard.tsx
  - frontend/src/components/train/TrainLineChips.tsx
  - frontend/src/components/train/TrainMoveTreeList.tsx
  - frontend/src/components/train/TrainRevealActionBar.tsx
  - frontend/src/components/train/TrainRevealGameFooter.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainVerdictDetails.tsx
  - frontend/src/components/train/TrainVerdictStrip.tsx
  - frontend/src/hooks/useAnalysisBoard.ts
  - frontend/src/hooks/useBoardNavigationInput.ts
  - frontend/src/hooks/useTrainPuzzleTelemetry.ts
  - frontend/src/hooks/useTrainRevealTree.ts
  - frontend/src/hooks/useTrainWalkthrough.ts
  - frontend/src/hooks/useTreeMoveGrading.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/mobileBoardControls.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainArrows.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/trainRevealCache.ts
  - frontend/src/lib/trainRevealLines.ts
  - frontend/src/lib/trainTelemetry.ts
  - frontend/src/types/train.ts
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 237: Code Review Report

**Reviewed:** 2026-10-09
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Reviewed the phase diff (`4e05ef4b5..HEAD`) for the Train reveal rewrite: chips row, single move tree, tree grading, verdict strip/details, reveal action bar, telemetry v2 and the walkthrough rewrite. TrainSolveScreen and useAnalysisBoard were reviewed through their diffs plus surrounding context. `eslint` over the touched train files and `npm run knip` are both clean.

The core design holds up under adversarial tracing. I found no correctness-breaking defect or security issue:

- The answer lines stay gated behind the verdict. The tree, engine, chips, navigation input and the reveal GET are all inactive until `verdict !== null`.
- Late and extending lines are grafted non-navigating and reuse children. The best line is `anchor.keyLine`, so lines only extend.
- The restore snapshot is shape-validated and replayed through chess.js with caps.
- The backend `v1`/`v2` key-set validator is sound.
- The grading logic lifted from `useTrainFreePlay` is behaviorally equivalent. The deliberate additions are the seed-vs-live guard and the staleness guard.

The issues found are edge-path inconsistencies, one duplicated-DOM concern, and telemetry or tour accuracy problems. There are no blockers.

## Warnings

### WR-01: A restored reveal built from the Analyze "stand-in" grade shows a permanent "…" eval pill and can lose the Best chip

**File:** `frontend/src/components/train/TrainLineChips.tsx:43-52` (with `frontend/src/lib/trainRevealLines.ts:121-126, 147-148` and `frontend/src/hooks/trainGradingSupport.ts:168-180`)

**Issue:** `gradeFromServerPair` (used when Analyze is clicked before the instant path's background grade lands) builds a `GradeResult` with `playedLine = { moves: [], evalCp: null, evalMate: null }`. Its `bestLine` is `{ moves: [], ... }` when the anchor had not settled. After Back, the restored reveal has `instantGrade === null` and this `gradeResult`, which causes two inconsistencies.

1. `resolveChipLine` returns the non-null empty line. `resolveChipPending` therefore returns `null` (line is not null). `ChipEval` then renders `formatScore(null, null)`, which is the literal string `"…"`, in an eval pill that never resolves. The old design degraded to a header-only card. The chip code only hides the pill for `pending === 'failed'` or `line === null`.
2. `revealBestUciOf(gradeResult, null)` reads `gradeResult.bestLine.moves[0]`, which is `undefined` for the empty stand-in line. So `uciByRole.best` is never set and no Best chip exists when the played move differs from the key. `TrainSolveScreen` computes `revealBestUci` from `gradeResult.bestMoveUci` (= `instant.keyUci`), which is non-null. The board overlay therefore still draws the best arrow, and `playedIsBest` still says "best move" when played equals key. This breaks the D-06 invariant that the clause and the chips use one predicate.

**Fix:**
```ts
// TrainLineChips.tsx: treat an eval-less line like a failed one
if (chip.pending === 'failed' || chip.line === null) return null;
if (chip.line.evalCp === null && chip.line.evalMate === null) return null;

// trainRevealLines.ts: one best-UCI source, matching TrainSolveScreen
export function revealBestUciOf(gradeResult, instantGrade) {
  return gradeResult?.bestMoveUci ?? instantGrade?.keyUci ?? null;
}
```
`capLineUcis` already falls back to `[uci]` when `line.moves[0] !== uci`, so the pre-load stays safe. Also have `TrainSolveScreen.revealBestUci` call `revealBestUciOf` so the two cannot drift again.

### WR-02: The reveal action bar is mounted twice, duplicating `btn-train-next`, `btn-train-analyze` and `train-reveal-action-bar`

**File:** `frontend/src/components/train/TrainSolveScreen.tsx:1881-1897` and `frontend/src/App.tsx:481-538` (`renderBoardControlsBar` / `MobileBottomBar`)

**Issue:** The in-flow instance (`hidden sm:flex`) and the fixed phone instance (`sm:hidden`) are both rendered into the DOM, and each carries the same `data-testid`s. CSS hides one at each width, but the other still exists. `frontend/CLAUDE.md` requires stable testids for the Chrome-extension and automation hooks. A `btn-train-next` lookup can resolve to the `display:none` copy: first in DOM order on a phone, or the fixed bar on desktop. Only one `BoardControls` instance used to coexist with the page content. Nothing prevents this from drifting, because both copies take their handlers from different paths (the published payload versus props).

**Fix:** Mount exactly one instance by breakpoint rather than hiding by CSS. For example, render the in-flow bar only when `useIsDesktop()` or a `sm`+ media-query hook is true, and publish `mobileBoardControls` only when it is false. Alternatively, suffix the fixed bar's testids (`btn-train-next-mobile`) so every id is unique.

### WR-03: The game-footer Analyze link bypasses `walkthrough.leave()`, so the first-reveal tour is not stamped on that exit

**File:** `frontend/src/components/train/TrainSolveScreen.tsx:1988` (vs `:1714-1717`)

**Issue:** The action bar's Analyze goes through `handleAnalyzeFromReveal`, which calls `walkthrough.leave()` and then `handleAnalyzeClick()`. `TrainReveal` is given `onAnalyzeClick={handleAnalyzeClick}` directly, and `TrainRevealGameFooter` fires it from its search-icon link (`TrainRevealGameFooter.tsx:106`). A user on the tour's last step who leaves through the footer link never stamps `reveal_walkthrough`, so the tour replays on the next reveal. The comment in `TrainRevealGameFooter` says the two Analyze controls must stay in sync, but only the cache write was kept in sync.

**Fix:** Pass `onAnalyzeClick={handleAnalyzeFromReveal}` to `TrainReveal` (or route it through `handleBarAnalyzeClick`) so both Analyze controls run the same handler.

### WR-04: Tapping the already-shown move counts as a line step and advances the tour

**File:** `frontend/src/hooks/useTrainRevealTree.ts:482-489`

**Issue:** `goToNode` calls `boardGoToNode(id)` and then `onUserStepRef.current?.()` for any existing node, including the node the board is already on. `useAnalysisBoard.goToNode` is a no-op in that case, but the callback still fires. The effects are:

- `review_line_steps` is inflated by a tap that moved nothing.
- The walkthrough's "stepping" step (`notifyTreeStep`) auto-advances on a no-op tap.

`goBack` and `goForward` guard this correctly (an early return on no node or no target).

**Fix:**
```ts
const goToNode = useCallback((id: NodeId): void => {
  const live = latestRef.current;
  if (!live.nodes.has(id) || live.currentNodeId === id) return;
  boardGoToNode(id);
  onUserStepRef.current?.();
}, [boardGoToNode]);
```

## Info

### IN-01: `VerdictCopy.clause` and `verdictClause` are dead in production

**File:** `frontend/src/lib/trainBotCopy.ts:447-481`

**Issue:** The UI now renders the clause from `verdictClauseParts` (`TrainVerdictDetails`) and `verdictStripLine`. `verdictCopy()` still builds the bracketed `clause` string, but nothing outside tests reads `.clause` (grep confirms). It is a second copy of the vocabulary that D-06 says should exist once, and knip cannot flag a dead object field.

**Fix:** Drop `clause` from `VerdictCopy` and delete `verdictClause`, or have a real consumer use it.

### IN-02: Stale references to the deleted `TrainLineStepper` in `useAnalysisBoard.ts`

**File:** `frontend/src/hooks/useAnalysisBoard.ts:166, 183`

**Issue:** The doc comments for the sound-taxonomy and tree-depth helpers still say they mirror `TrainLineStepper`, which this phase deleted. This misleads the next reader.

**Fix:** Reword to name `useTrainRevealTree` and `TrainMoveTreeList` as the consumers, or drop the reference.

### IN-03: A restored `rootFocus` is not checked against the chips that exist after the restore

**File:** `frontend/src/hooks/useTrainRevealTree.ts:341-348` (validation in `frontend/src/lib/trainRevealCache.ts:~150`)

**Issue:** `isRevealTreeSnapshot` only checks that `rootFocus` is one of the three role keys. If the saved focus was `'game'` and the game chip is absent after the restore (the reveal GET failed, or the game move now coincides with another role), then `deriveActiveChip` returns null. Every arrow dims and the list is empty. `goToRoot` only restores the default focus when `rootFocus === null`, so the stale value is not self-healing. The user can still tap a chip, so the effect is cosmetic.

**Fix:** In `deriveActiveChip`, or at the restore, fall back to `DEFAULT_ROOT_FOCUS` when the stored focus is not among `specs`.

---

_Reviewed: 2026-10-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

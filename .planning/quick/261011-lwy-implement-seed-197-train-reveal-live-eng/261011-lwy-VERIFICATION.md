---
phase: quick-261011-lwy
verified: 2026-10-11T16:50:00Z
status: human_needed
score: 7/7 must-haves verified
covered_files:
  - .planning/quick/261011-lwy-implement-seed-197-train-reveal-live-eng/261011-lwy-PLAN.md
  - .planning/quick/261011-lwy-implement-seed-197-train-reveal-live-eng/261011-lwy-SUMMARY.md
  - frontend/src/components/analysis/EngineLines.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/board/HorizontalMoveList.tsx
  - frontend/src/components/train/TrainLineChips.tsx
  - frontend/src/components/train/TrainMoveTreeList.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/hooks/useRevealPreview.ts
  - frontend/src/hooks/useTrainRevealTree.ts
  - frontend/src/lib/trainArrows.ts
  - frontend/src/lib/trainRevealLines.ts
  - frontend/src/lib/trainRevealPreview.ts
covered_digest: "v3:sha256:7837f1f31f9067e18b072a7e5c62f662c57092b64bfb5a278ce30c3ce87188cb"
behavior_unverified: 0
human_verification:
  - test: "Open a Train reveal on desktop and a phone-width viewport. Look at the move list right after open."
    expected: "First move of the active chip followed by a faded preview of at most 6 plies led by a blue live eval pill. On the two-row mobile list the preview wraps and the list stays readable, and the current node stays in view."
    why_human: "Layout/fit and visual dimming cannot be judged by jsdom (CONTEXT 'Mobile fit' says settle by look)."
  - test: "Press forward / ArrowRight repeatedly, then pause. Tap a faded token mid-preview, including from the puzzle position."
    expected: "Each press commits one node instantly with no flicker. After a pause the faded line refines once the engine passes depth 10 and committed nodes never change. A token tap commits that many plies."
    why_human: "Real engine timing and perceived stepping speed need a live Stockfish."
  - test: "Create a sideline leaf, check preview placement, then delete it with the x."
    expected: "Preview sits inside the parentheses before ')' and the delete x. The x still deletes the line."
    why_human: "Inline visual placement of ')' and x relative to faded tokens."
  - test: "Stockfish row at a leaf vs a node with children; confirm sfArrows=0 behaviour."
    expected: "Row starts at 'Line 2' at a previewed leaf and 'Line 1' elsewhere, the reserved height does not jump. With Stockfish arrows = 0 the solid pointer still draws (executor judgement call, flagged for owner)."
    why_human: "Owner preference on the sfArrows=0 pointer, and visual layout stability."
---

# Quick 261011-lwy: SEED-197 Train reveal live engine preview - Verification Report

**Goal:** Chips own only their first move; everything after is a free node; a dimmed live-engine preview sits at the end of the current branch and is committed on forward / ArrowRight / token tap. Frontend only.
**Verified:** 2026-10-11
**Status:** human_needed (all automated checks pass; visual/interactive items remain)
**Re-verification:** No, initial verification

## Gate results (run by the verifier, not copied from SUMMARY)

| Check | Result |
| ----- | ------ |
| Targeted vitest (7 files: trainRevealPreview, trainRevealLines, useTrainRevealTree, TrainMoveTreeList, TrainSolveScreen, VariationTree, EngineLines) | 7 files / 364 tests passed |
| `npm run build` (tsc -b + vite) | passes |
| `npm run knip` | clean (only the pre-existing `.css` config hint) |
| `npm run lint` | clean |
| Dead code grep (`dropLineMove`, `allSecondary`, `capLineUcis`, `MAX_LINE_PLIES`) in `src/` | no matches, including tests |
| Branch / tree state | on `quick/seed-197-live-engine-preview`, only the untracked SUMMARY.md outside commits; mutations below were reverted (git status clean) |

## Observable Truths

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | Reveal open: chip contributes only its first move, list shows it plus a dimmed preview of at most `TRAIN_PREVIEW_MAX_PLIES` (6) seeded from the graded line | VERIFIED | `chipPreviewSeed` / `buildPreviewSeeds` / `buildSteps` clip in `lib/trainRevealPreview.ts`; `resolvePreviewAnchor` falls back to the active chip's first-move node at the puzzle position; `VariationTree` renders `variation-preview-N` tokens. Mutation: removing the clip failed "truncates at first illegal move and clips" and "caps the displayed preview ... lets the user keep committing past it". |
| 2 | Forward/ArrowRight at a leaf commits the preview's next move as a real node; token i commits i+1 plies (chip move first at the puzzle position); committed nodes never change | VERIFIED | `goForward` falls back to `commitPreview(1)` when `resolveForwardTarget` is null; `commitPreview` plays `[chipUci, ...steps]` via `boardPlayUciLine` when `fromRoot`; `toVariationPreview` wires `onTokenClick(i) -> commitPreview(i+1)`. Tests "forward at the root enters the chip node and commits nothing; forward at that leaf commits exactly one node" and the ArrowRight test pass; both failed under the depth/clip mutation. |
| 3 | Leaf shows its own live PV only at depth >= `TRAIN_LIVE_ALT_MIN_DEPTH` (10) with a legal first move, else the nearest matching ancestor's remaining tail | VERIFIED | `liveCandidate` depth guard, `resolvePreview` precedence live/stored/seed/inherited, `inheritedCandidate` ancestor walk. Mutation removing the depth guard failed "needs depth TRAIN_LIVE_ALT_MIN_DEPTH" and "a live PV below ... does not replace the tail". |
| 4 | No preview when the node has children or at mate/stalemate; preview never stored in tree or Analyze snapshot; snapshot round trip keeps main line | VERIFIED | `resolvePreviewAnchor` returns null on `hasChildren` or `terminalPositionEval` non-null; preview lives only in `useRevealPreview` state; test "snapshot never contains the preview, and a restore regenerates it" passes. |
| 5 | Preview-committed moves are never graded; hand-played moves still are | VERIFIED | `isFreeNode = !knownIds.has(id) && !committedIds.has(id)`; ids recorded synchronously in `commitPreview` via `markCommitted(liveNextId + i)`. Mutation dropping `!committedIds.has(id)` failed "a preview-committed node gets no marker while a hand-played fork still does"; "a board move equal to the preview next move is not a fork ... both are graded" passes. |
| 6 | Stockfish row shows lines 2..N with true rank at a previewed leaf, all N elsewhere; solid blue pointer is the preview's next move | VERIFIED | `TrainStockfishRow`: `tree.pvLines.slice(1, sfLines)` + `rankOffset={1}` when `preview.anchorId === currentNodeId`; `EngineLines` `rankOffset` replaces `allSecondary`; `resolveRevealBoardOverlay` keys `buildTrainStepOverlayArrows` on `preview.steps[0].uci`. TrainMoveTreeList/EngineLines/TrainSolveScreen tests pass. |
| 7 | Chip eval stays frozen graded reading with "Graded eval" label; live eval badge in `formatScore` styling leads the preview | VERIFIED | `TrainLineChips.ChipEval` has `title="Graded eval"` + `aria-label`; `PreviewEvalPill` (`variation-preview-eval`) fed from `formatScore(preview.evalCp, preview.evalMate)`; `TrainLineChips.test` and `VariationTree.test` cover both. |

**Score:** 7/7 truths verified; 0 behavior-unverified (behavior-dependent truths 2, 3, 5 each have a passing behavioral test that was shown to fail under mutation).

### Requirements Coverage

| Requirement | Status | Evidence |
| ----------- | ------ | -------- |
| SEED-197 design items 1-9 | SATISFIED (automated) | See truths 1-7. Item 8 (different move just commits, new sideline) is covered by the "board move equal to / different from the preview" hook test. Item 9 `MAX_LINE_PLIES` removed, clip applies to preview only. |

### Key links

| From | To | Status |
| ---- | -- | ------ |
| `useTrainRevealTree.goForward` -> `commitPreview` -> `boardPlayUciLine` | WIRED |
| `useRevealPreview` -> `resolvePreviewAnchor` / `resolvePreview` | WIRED |
| `TrainMoveTreeList` -> `VariationTree preview` -> `tree.commitPreview` | WIRED |
| `TrainSolveScreen.resolveRevealBoardOverlay` -> `buildTrainStepOverlayArrows` | WIRED |
| `useTrainRevealTree.isFreeNode` -> grading (`useTreeMoveGrading`) | WIRED |

### Anti-patterns

No TBD/FIXME/XXX markers introduced in the covered files, no dead exports (knip clean), no stubs found. Minor note: `aria-label` is placed on a plain `<span>` in `ChipEval` (no role), which some a11y linters treat as ineffective; not a goal blocker.

### Scope notes

- Executor judgement call, flagged for the owner: with Stockfish arrows = 0 the solid preview pointer still draws (plan said "always the preview's next move"). Folded into human item 4.
- A node with children now shows the engine's own blue arrows rather than the next line move (consistent with seed item 5); acceptable.
- Backend untouched (frontend-only as scoped). CHANGELOG `[Unreleased]` bullet added and the superseded sentence replaced.

## Gaps Summary

None. All must-haves hold in the code and are exercised by passing tests that fail when the relevant logic is reverted. Remaining items are visual/interactive (mobile fit, stepping feel with a real engine, sideline placement, sfArrows=0 preference) and need a browser.

---

_Verified: 2026-10-11_
_Verifier: Claude (gsd-verifier)_

## Orchestrator browser UAT (2026-10-11)

Human-verification items 1-4 were driven in Chrome against the worktree dev build (:5174); see 261011-lwy-SUMMARY.md "Browser UAT". All passed after one fix (`6d15ebdc0`, mobile scroll tail). Remaining for the owner: real-device feel on a phone, and the sfArrows = 0 pointer preference. Status stays human_needed for those two only.

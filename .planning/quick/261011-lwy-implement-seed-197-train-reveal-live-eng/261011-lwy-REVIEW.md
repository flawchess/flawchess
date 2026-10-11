---
phase: 261011-lwy-seed-197-train-reveal-live-engine-preview
reviewed: 2026-10-11T00:00:00Z
depth: quick (plus concrete trace of the commitPreview id assumption)
files_reviewed: 12
files_reviewed_list:
  - CHANGELOG.md
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
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# SEED-197: Code Review Report

**Reviewed:** 2026-10-11
**Depth:** quick, plus a concrete trace of `commitPreview` against `useAnalysisBoard.playUciLine`
**Status:** issues_found (no blockers)

## Summary

Mechanical gates in the worktree: `eslint` on the touched dirs is clean, `tsc -b` is clean, `knip` is clean, and the 45 touched or related vitest files (1108 tests) pass. No dead `dropLineMove` / `allSecondary` / `stepInfo` / `isOffLine` / `MAX_LINE_PLIES` references remain outside tests.

**commitPreview id assumption: verified correct on every path I could construct.** I read `useAnalysisBoard.ts`:
- `nextId` is monotonic. `loadMainLine` resets it, but only at a tree reset, and the committed set is keyed by the same `resetKey`. `deleteSubtree` never touches it, so a tree with deleted nodes still numbers new nodes from `nextId`.
- `playUciLine` (661-701) assigns `id = prev.nextId` and increments only when `findChildBySquares` finds no existing child. A preview only exists on a LEAF (`resolvePreviewAnchor` returns null when `hasChildren`), so every `stepUcis` move is a brand-new node numbered `nextId + i`.
- Root path (`fromRoot`): `[nodeUci(anchor), ...stepUcis]` is played from `currentNodeId === null`. The first UCI reuses the existing chip first-move node (it consumes no id), then the steps get `nextId + i`. The code marks only `stepUcis`, so it is right. The chip node is also in `knownIds`, so it is never graded anyway.
- Leaf deep in a sideline: `atAnchor`, all steps new, correct.
- Legality parity: `buildSteps` validates through `replayPvLine` (chess.js, promotion char passed through). `playUciLine` uses the same chess.js move call, so a step shown in the preview cannot be silently skipped (an id gap) while later ids shift.
- Stale `latestRef` (rapid presses): keydown and wheel go through `useBoardNavigationInput`, which throttles. Discrete events flush render and effects synchronously, so `latestRef.preview` / `nextId` are fresh at each press. Token taps also read `latestRef`, not the tapped closure, so the commit uses the preview currently shown. If a stale second commit did occur, the stale steps replayed from the new current node are illegal (the mover's from-square is already vacated), so it is a no-op and the stale ids it would mark equal ids already marked. It is harmless today, but see WR-01.

The remaining issues are about robustness and edge consistency, not the headline risk.

## Warnings

### WR-01: Committed ids are predicted, not observed (silent coupling to `playUciLine` internals)

**File:** `frontend/src/hooks/useTrainRevealTree.ts:632-651` (`commitPreview`), `frontend/src/hooks/useRevealPreview.ts:140-160`
**Issue:** `markCommitted(stepUcis.map((_, i) => liveNextId + i))` is correct today only because (a) the anchor is a leaf, (b) `playUciLine` consumes exactly one id per new node, and (c) `latestRef.nextId` is fresh. Nothing asserts any of this. If `playUciLine` changes (for example it starts reusing promotion variants, or skips a step), or `commitPreview` is ever invoked twice in one batch, the wrong ids get marked. The failure is silent and in the dangerous direction: a preview move gets graded, or a hand-played move is excluded from grading (the exact risk named in the brief). The only test coverage is the happy path.
**Fix:** Derive the ids from the result rather than predicting them. Options, in order of preference:
1. Have the board hook report what it grafted, e.g. `playUciLine(uciMoves, onGrafted?: (ids: NodeId[]) => void)`, or compute the committed set inside the `setState` updater.
2. Cheaper: in `commitPreview`, add a cheap guard that the anchor has no children in `latestRef.nodes` and that `plies <= shown.steps.length`, plus a test with two `commitPreview` calls inside one `act()` to pin the behavior.

### WR-02: Preview-committed nodes lose their "never graded" status across Analyze -> Back

**File:** `frontend/src/lib/trainRevealLines.ts:`buildRevealTreeSnapshot` (snapshot builder), `frontend/src/hooks/useTrainRevealTree.ts:` restore effect (~330-345)
**Issue:** CONTEXT locks "do NOT grade moves committed from the preview". The snapshot persists committed continuations as plain UCI paths, and the restore replays them with `graftLine` as ordinary nodes. `committedIds` lives in component state and is not part of the snapshot, so after Analyze -> Back every restored engine move is a "free" node. `useTreeMoveGrading` then grades it as soon as the user steps onto it (the engine caches each shown position's eval). Engine moves therefore pick up `best` / `good` / `inaccuracy` badges and quality-colored last-move highlights after a round trip, but not before. That contradicts the locked behavior and is user-visible. (Hand-played restored sidelines getting regraded was already true before this change, so only the engine-committed part is new.)
**Fix:** Persist the committed paths in the snapshot (e.g. `committedPaths: string[][]`, or a per-node flag in the path list), and on restore resolve the nodes with `walkLinePath` and call `markCommitted`. Alternatively document it as accepted and add a test that states the accepted behavior.

### WR-03: Keyed ephemeral state can resurrect across a deactivate/reactivate of the SAME puzzle FEN

**File:** `frontend/src/hooks/useRevealPreview.ts:79-81, 150-160` (also `storedState`)
**Issue:** `stored` and `committedIds` are read as `state.key === resetKey ? state.x : EMPTY` and are only reset lazily on write. `resetKey` goes `fen -> null -> fen` when `active` toggles (the tree itself restarts node ids at 0 via `loadMainLine`). When the same FEN re-activates in the same mounted `TrainSolveScreen` (`pages/Train.tsx:231,242` render it with no per-puzzle `key`), the old key matches again and the previous reveal's `committedIds` and stored live lines come back. These are node-id keyed, and ids restart at 0 and are reused. A stale committed id then suppresses grading of an unrelated hand-played node with the same id, and a stale stored line is applied to a different node. It is rare (it needs the same FEN twice in one mount), and the same pattern already exists in `useTreeMoveGrading.qualityState`, but this change adds two more instances of it.
**Fix:** Reset eagerly instead of by key comparison, e.g. an effect that `setState` to an empty value on `resetKey` change, or fold the reset into the same place `loadMainLine` runs. Alternatively key the state by a monotonically increasing "tree generation" counter, not by FEN.

## Info

### IN-01: Stockfish row hides engine line 1 even when the preview is not the engine's line

**File:** `frontend/src/components/train/TrainMoveTreeList.tsx:61-62`
**Issue:** `isPreviewedLeaf` is true for any preview, including `seed`, `stored` and `inherited` sources, so engine line 1 is dropped from the row (and the CHANGELOG says the preview "already shows it"). Below depth 10, or after the user deviated from the inherited tail, the preview and the engine's actual top line can differ, and the row then omits the real top line. This follows the locked "at a leaf lines 2..N" rule, so it is a note rather than a defect.
**Fix:** If the lock is ever relaxed, key the row on `preview.source === 'live'` (or on the preview's first move equalling `pvLines[0].moves[0]`).

### IN-02: Live always overwrites a deeper stored line

**File:** `frontend/src/lib/trainRevealPreview.ts:157-161`, `frontend/src/hooks/useRevealPreview.ts:104-115`
**Issue:** Precedence is live > stored. On revisiting a leaf the engine restarts at depth 1. When it reaches `TRAIN_LIVE_ALT_MIN_DEPTH` the shallow depth-10 line replaces the stored deeper line, and the equality-guarded store then overwrites it, so refined lines get worse (and visibly swap) on each revisit. `PreviewLine` does not carry a depth, so this cannot be guarded today.
**Fix:** Carry `depth` on `PreviewLine` and only replace/store when the live depth is >= the stored depth.

### IN-03: `EngineLines` row keys are `lineIndex`, expand state sticks to a slot when `rankOffset` toggles

**File:** `frontend/src/components/analysis/EngineLines.tsx:437` (`key={lineIndex}`)
**Issue:** The per-row `expanded` state is keyed by slot. Moving between a previewed leaf (rows are lines 2..N) and another node (rows are 1..N) re-uses slot 0 for a different engine line, so a line the user expanded stays "expanded" when it becomes a different line.
**Fix:** Key rows by `lineIndex + rankOffset`.

### IN-04: Presentation nits in the preview rendering

**File:** `frontend/src/components/analysis/VariationTree.tsx:741-766`; `frontend/src/components/board/HorizontalMoveList.tsx`
**Issue:**
- `ply: -1 - i` is a magic sentinel ("unused: onSelect owns the click"). Make `ply` optional on `HorizontalMoveItem` when `onSelect` is set, or name the constant.
- The first preview token after a white anchor renders a black "N..." label, while real main-line and sideline black replies carry no label (`isWhite ? label : null`), so the preview reads slightly differently from committed moves.
- The auto-scroll keys on the current item only, so up to 6 preview tokens plus the pill can sit below the fold in the 2-row mobile list (the spec's "current node stays visible" is met, the preview itself may not be).
- The `leading:` line (~757) and the reflowed `trainArrows.ts` comment (~316-318, a 150+ column run) are badly wrapped.
**Fix:** Cosmetic, address opportunistically.

### IN-05: Frozen graded-eval label is not reachable on touch or announced reliably

**File:** `frontend/src/components/train/TrainLineChips.tsx:55-58`
**Issue:** `title="Graded eval"` never shows on touch, and `aria-label` on a plain `<span>` is not announced consistently (ARIA prohibits naming a generic role). The "graded eval" disclosure CONTEXT asks for is therefore effectively desktop-hover only.
**Fix:** Add visually hidden text (`<span className="sr-only">Graded eval </span>`) or `role="img"` / `role="status"` as appropriate, and consider a visible short label.

---

_Reviewed: 2026-10-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick (+ targeted trace of commitPreview ids)_

## Fixes applied

- WR-02 3e4867134: `committedPaths` in `RevealTreeSnapshot` (optional, validated in the reveal cache), re-marked on restore.
- WR-03 efae4adc9: `useRevealPreview` replaces both keyed states with empty ones when `resetKey` changes (including to null).
- WR-01 65e9c1a39: stale repeat `commitPreview` within one event is ignored (pending-next-id guard); id bookkeeping tests added.
- IN-05 c03fb3b3c: sr-only "Graded eval" text in the chip pill; title kept.
- IN-03 c7bd22191: EngineLines rows keyed by `lineIndex + rankOffset`.

---
phase: 139-tactic-mode-overlay-phase-135-subsume
plan: "01"
subsystem: frontend
status: complete
tags: [tactic-mode, analysis, overlay, phase-135-parity, tdd]
dependency_graph:
  requires:
    - "138: Analysis page free-play shell"
    - "135: TacticLineExplorer modal (source of port)"
  provides:
    - "TacticModeOverlay component with buildRootArrows/buildPvArrow exports"
    - "Analysis.tsx tactic-mode wiring: param read, useTacticLines, seeding, arrows, overlay"
    - "goToRoot on useAnalysisBoard"
    - "Regression test suite for Phase 135 behaviors A-D"
  affects:
    - "139-02: entry-point repointing (game card → /analysis URL)"
    - "139-03: TacticLineExplorer deletion (gated on this plan's tests)"
tech_stack:
  added:
    - "TacticModeOverlay.tsx — tactic chrome panel for /analysis page (Phase 139)"
  patterns:
    - "Re-seed useEffect keyed on positionFen + resolvedOrientation (D-5 pattern)"
    - "D-03 board-arrow source toggle: stored-PV arrows on-line, engine arrow off-line"
    - "resolveVisibleTactic + useFlawFilterStore for filter-gated chip visibility"
    - "goToRoot() minimal hook addition (sets currentNodeId=null, preserves tree)"
key_files:
  created:
    - "frontend/src/components/analysis/TacticModeOverlay.tsx"
    - "frontend/src/pages/__tests__/Analysis.tactic.test.tsx"
  modified:
    - "frontend/src/pages/Analysis.tsx"
    - "frontend/src/hooks/useAnalysisBoard.ts"
    - "frontend/src/hooks/__tests__/useAnalysisBoard.test.ts"
    - "frontend/src/pages/__tests__/Analysis.test.tsx"
    - "frontend/eslint.config.js"
decisions:
  - "goToRoot sets currentNodeId=null without clearing nodes/mainLine — landing at decision position after D-5 re-seed"
  - "TacticModeOverlay exports buildRootArrows/buildPvArrow as named exports so Analysis.tsx can drive ChessBoard arrows without file indirection"
  - "ESLint analysis/** override added (mirrors ui/** and filters/**) for co-exported arrow helpers alongside component"
  - "In tactic mode, Reset calls goToRoot (not loadMainLine([],...)) to preserve the seeded PV while returning to decision position"
metrics:
  duration: "45min"
  completed: "2026-06-26"
  tasks: 3
  files: 7
---

# Phase 139 Plan 01: Tactic Mode Overlay — Port + Wire Summary

One-liner: TacticModeOverlay ports Phase 135 tactic chrome (motif chips, eval badge, depth counter, D-03 arrow-source toggle, HorizontalMoveList) into Analysis.tsx tactic mode with full re-seed logic and 4 regression behavior tests as the Plan 03 deletion gate.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create TacticModeOverlay.tsx — port chrome + arrow helpers | 123915c5 | TacticModeOverlay.tsx, eslint.config.js |
| 2 | Wire Analysis.tsx tactic mode + add goToRoot | 2c9f16c8 | Analysis.tsx, useAnalysisBoard.ts, useAnalysisBoard.test.ts, Analysis.test.tsx |
| 3 | Regression tests for 4 Phase 135 behaviors | 7ac8354a | Analysis.tactic.test.tsx |

## What Was Built

### Task 1 — TacticModeOverlay.tsx

New component exported from `frontend/src/components/analysis/TacticModeOverlay.tsx`:

**Exports:**
- `isBlackToMove(fen)` — ported unchanged from TacticLineExplorer; used by Analysis.tsx for board flip default
- `buildRootArrows(positionFen, bestMoveUci, flawMoveSan, missedDepthLabel, allowedDepthLabel)` — builds blue best-move + red flaw-move arrows for the decision position (ply 0)
- `buildPvArrow(lastMove, displayDepth, isPayoff, orientation, isFlawLeadIn)` — builds single PV arrow for ply 1+ steps
- `TacticModeOverlay` (default component) — the tactic chrome panel

**TacticModeOverlay props:** `data, resolvedOrientation, currentPly, displayDepth, isPayoff, arrowSource, showArrowSourceToggle, onOrientationChange, onArrowSourceChange, onMoveClick`

**TacticModeOverlay renders:**
- Motif chip row: `TacticMotifChip` instances with `testId="tactic-toggle-missed"` / `testId="tactic-toggle-allowed"` when both lines present (showSwitch); single non-interactive chip when only one line
- White-POV eval badge (`data-testid="tactic-eval"`) using `formatFlawEvalPart` + `mateAtPly`
- Depth-to-punchline counter (`data-testid="tactic-depth-counter"`) using `toDisplayDepthForOrientation`
- D-03 arrow-source segmented toggle (`data-testid="tactic-arrow-source-stored"`, `data-testid="tactic-arrow-source-engine"`)
- `HorizontalMoveList` (`testId="tactic-san-ladder"`) with `moveLabel(flaw_ply, i)` for real-game-ply numbering (Behavior C)
- All filter gating via `resolveVisibleTactic(orientation, motif, depth, flawFilter)` exactly as the modal

**ESLint override added:** `src/components/analysis/**` files disable `react-refresh/only-export-components` to allow the arrow helper functions to co-exist with the component in one file. Matches the pattern already in place for `ui/**` and `filters/**`.

### Task 2 — Analysis.tsx tactic-mode wiring + goToRoot

**URL param reading (T-139-01, T-139-02):**
- `gameId = Number(gameIdRaw)` with `Number.isNaN` guard → null for malformed input
- `flawPly` same pattern
- `orientation` cast to `TacticDepthOrientation`, defaulting `'missed'`
- `isTacticMode = gameId != null && flawPly != null`

**New hooks called unconditionally:**
- `useTacticLines(gameId, flawPly, isTacticMode)` — enabled only in tactic mode
- `useFlawFilterStore()` — for resolveVisibleTactic gating

**D-5 re-seed effect (Behavior D):** keyed on `[positionFen, resolvedOrientation, isTacticMode]`:
```ts
loadMainLine(activeMoves, positionFen);
goToRoot();
```

**Board flip effect:** `isBlackToMove(positionFen)` per flaw entry, preserving manual flips.

**ArrowSource reset effect:** resets to `'stored'` on flaw change.

**Derived tactic values:**
- `tacticPly = currentNodeId === null ? 0 : mainLine.indexOf(currentNodeId) + 1`
- `rootDisplayDepth = toDisplayDepthForOrientation(activeDepthRaw, resolvedOrientation)`
- `displayDepth = max(0, rootDisplayDepth - tacticPly)`, `isPayoff = tacticPly > rootDisplayDepth`

**Board arrows (D-03):**
- On-line + stored source → `buildRootArrows` (ply 0) or `buildPvArrow` (ply 1+)
- Off-line OR engine source → live engine best-move arrow from `engine.pvLines[0]?.moves[0]`
- Arrow-source toggle shown only when `onMainLine`

**TacticModeOverlay rendered in side panel** above EngineLines; EvalBar + EngineLines stay live throughout.

**goToRoot added to useAnalysisBoard:**
- Interface: `goToRoot: () => void` with jsdoc
- Implementation: `setState((prev) => ({ ...prev, currentNodeId: null }))`
- Unit test: verifies `currentNodeId=null` after `goToRoot`, nodes and mainLine unchanged

### Task 3 — Regression test suite (Phase 135 behaviors A-D)

`frontend/src/pages/__tests__/Analysis.tactic.test.tsx` — 4 tests, 0 failures:

| Behavior | Test | Assertion |
|----------|------|-----------|
| A — depth-0 no crash | "Behavior A: depth-0 tactic renders overlay without crashing" | `getByTestId('tactic-mode-overlay')` present, `analysis-page` intact |
| B — allowed +1 offset | "Behavior B: allowed orientation shows display depth 2 for raw depth 0" | `tactic-depth-counter.textContent` contains '2', not '/ 1' |
| C — real-game-ply numbering | "Behavior C: move labels use real game ply (flaw_ply=42 → move 22, not move 1)" | `tactic-san-ladder.textContent` contains '22.', not '1.' |
| D — re-seed on orientation change | "Behavior D: clicking the allowed toggle re-seeds the move list" | After click: `tactic-san-move-42.textContent` contains 'e5' not 'Nf6' |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ESLint `react-refresh/only-export-components` on TacticModeOverlay arrow helpers**
- **Found during:** Task 1 lint check
- **Issue:** TacticModeOverlay exports `isBlackToMove`, `buildRootArrows`, `buildPvArrow` alongside the `TacticModeOverlay` component. The `react-refresh/only-export-components` rule fired on lines 55, 66, 108 (3 errors).
- **Fix:** Added ESLint config override for `src/components/analysis/**` in `eslint.config.js`, matching the existing `ui/**` and `filters/**` overrides. Arrow helpers are stable always-present exports (not conditional components), so Fast Refresh safety is unaffected.
- **Files modified:** `frontend/eslint.config.js`
- **Commit:** 123915c5

**2. [Rule 1 - Bug] `engine` declared after `boardArrows` in first Analysis.tsx draft**
- **Found during:** Task 2 TypeScript check
- **Issue:** Initial draft of Analysis.tsx referenced `engine.pvLines` before the `engine` variable was declared (hooks called after derived values).
- **Fix:** Rewrote Analysis.tsx with correct React hook ordering — all hooks unconditionally first, then derived values and board arrow computation.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Commit:** 2c9f16c8

**3. [Rule 1 - Bug] Existing Analysis.test.tsx tests failed after useTacticLines added**
- **Found during:** Task 2 verification
- **Issue:** `useTacticLines` calls `useQuery` which requires `QueryClientProvider`. Existing 5 tests crashed with "No QueryClient set".
- **Fix:** Added `QueryClientProvider` wrapper, mocked `useTacticLines` (returns `{ data: undefined }`) and `useFlawFilterStore` (returns default filter) in `Analysis.test.tsx`.
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Commit:** 2c9f16c8

**4. [Rule 1 - Bug] Behavior C test asserted `textContent` on the wrong element**
- **Found during:** Task 3 test run
- **Issue:** `numberLabel` is rendered in a `<span>` BEFORE the move button, not inside it. Asserting `.textContent` on the `data-testid` button element only shows the SAN text.
- **Fix:** Changed the Behavior C assertion to use `tactic-san-ladder.textContent` (the outer scroll container), which includes all number labels and SAN text.
- **Files modified:** `frontend/src/pages/__tests__/Analysis.tactic.test.tsx`
- **Commit:** 7ac8354a

## Test Results

```
Test Files  105 passed (105)
     Tests  1222 passed (1222)
```

All tests pass including:
- `useAnalysisBoard.test.ts` — 7/7 (6 original + 1 new goToRoot)
- `Analysis.test.tsx` — 5/5 (all original passing after QueryClientProvider fix)
- `Analysis.tactic.test.tsx` — 4/4 (Behaviors A, B, C, D)

## Known Stubs

None. The overlay renders real data from the `useTacticLines` response. All behavior logic (depth math, filter gating, move labeling) uses production utilities, not placeholders.

## Threat Flags

No new network endpoints or auth paths introduced. `TacticModeOverlay` is a pure React component consuming already-fetched data. T-139-01 (NaN guard on params) and T-139-02 (orientation fallback) are implemented as planned.

## Self-Check: PASSED

- `frontend/src/components/analysis/TacticModeOverlay.tsx` exists: FOUND
- `frontend/src/pages/__tests__/Analysis.tactic.test.tsx` exists: FOUND
- Commit 123915c5 exists: FOUND
- Commit 2c9f16c8 exists: FOUND
- Commit 7ac8354a exists: FOUND
- `tsc -b` exits 0: PASSED
- `npm run lint` 0 errors: PASSED
- All 1222 tests pass: PASSED

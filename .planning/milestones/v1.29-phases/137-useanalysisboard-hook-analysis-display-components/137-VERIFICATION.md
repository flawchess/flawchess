---
phase: 137-useanalysisboard-hook-analysis-display-components
verified: 2026-06-26T17:20:00Z
status: passed
human_verified: 2026-06-26T17:40:00Z
human_verified_note: "Desktop VariationTree auto-scroll accepted via UAT (137-UAT.md) on code-review grounds; real-browser exercise deferred to Phase 138 route wiring."
score: 14/14
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "Drag-drop and click-to-click touch move input both work; the board can be flipped at any point"
    addressed_in: "Phase 138"
    evidence: "D-01 explicitly defers board wiring and board flip to Phase 138 Analysis.tsx; Phase 137 delivers makeMove(from, to) as the input-agnostic hook entry point only"
  - truth: "Board/variation state is encoded in the URL so the position is shareable and bookmarkable with no server-side persistence"
    addressed_in: "Phase 138"
    evidence: "D-01 states 'read-only entry-point only; entry-point param reading is Phase 138 Analysis.tsx'; Phase 137 delivers loadMainLine/rootFen seeding (the hook side) with NO write-back; URL encode/decode is Phase 138"
behavior_unverified_items:
  - truth: "The active node is auto-scrolled into view on currentNodeId change"
    test: "Change currentNodeId in VariationTree and verify the active node button is scrolled into the visible viewport"
    expected: "The button for the new active node scrolls into view smoothly (scrollIntoView called on the correct element)"
    why_human: "jsdom stubs scrollIntoView; the test uses vi.fn() to prevent throw but does not assert it was called on the active element after a currentNodeId change — actual scroll behavior requires a real browser"
human_verification:
  - test: "Load VariationTree with multiple nodes, change currentNodeId to a node outside the visible area, confirm the active node button scrolls into view"
    expected: "The active move in the desktop vertical list scrolls smoothly into the visible area without manual user scroll"
    why_human: "jsdom's scrollIntoView stub cannot verify real DOM scrolling; requires a real browser environment"
---

# Phase 137: `useAnalysisBoard` Hook + Analysis Display Components — Verification Report

**Phase Goal:** The branching move tree and all analysis display components (EvalBar, EngineLines, VariationTree) are built and unit-testable in isolation; `useChessGame.ts` is unmodified
**Verified:** 2026-06-26T17:20:00Z
**Status:** passed (human verification completed 2026-06-26 via 137-UAT.md)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Source | Status | Evidence |
|---|-------|--------|--------|----------|
| T1 | A move made at any node (including mid-line) creates a new CHILD node; the main line is not truncated | Plan 01 | VERIFIED | `makeMove` appends a new MoveNode parented to `currentNodeId` regardless of existing children; test "mid-line fork" asserts `nodes.size + 1`, `parentId === midNodeId`, `mainLine` unchanged |
| T2 | goBack / goForward / goToNode change currentNodeId and position correctly; going back from a root-level node returns to rootFen (reset-to-start) | Plan 01 | VERIFIED | All navigation paths tested: goBack at null → position === ROOT_FEN; goForward at childless node → no-op; goToNode jumps to correct nodeId; 6/6 tests pass |
| T3 | goToNode reads the stored FEN directly (O(1)) without replaying moves from root | Plan 01 | VERIFIED | `goToNode` implementation is `setState((prev) => ({ ...prev, currentNodeId: id }))` with no for/while loop; FEN derived from `nodes.get(currentNodeId).fen` in `getPosition()` helper; test asserts `position === storedFen` |
| T4 | loadMainLine seeds rootFen + mainLine; isOnMainLine returns true for seeded node IDs and false for forked nodes | Plan 01 | VERIFIED | Test verifies: `mainLine.length === MAIN_LINE_SANS.length`; `isOnMainLine(id) === true` for all seeded IDs; `isOnMainLine(forkedId) === false` after makeMove from a mid-line node |
| T5 | The hook adds no sessionStorage persistence and no URL write-back (D-01) | Plan 01 | VERIFIED | `grep -c 'sessionStorage\.(set\|get)Item' src/hooks/useAnalysisBoard.ts` → 0; `grep -c 'history\.(push\|replace)State\|location\.search *=\|searchParams\.set' src/hooks/useAnalysisBoard.ts` → 0; `grep -c 'useChessGame' src/hooks/useAnalysisBoard.ts` → 0 |
| T6 | EvalBar renders a white-POV vertical fill whose white fraction follows the sigmoid of evalCp (white always on top, never flips — D-04) | Plan 02 | VERIFIED | `EvalBarProps` has no `orientation` field; white fill div always `top-0`, black fill div always `bottom-0`; `SIGMOID_SCALE = 400` const used in formula; 7 render tests pass verifying fill fraction changes with evalCp |
| T7 | EvalBar shows the mate label only when evalMate !== null AND depth >= 8 (D-04) | Plan 02 | VERIFIED | `computeWhiteFraction` gates mate-specific fraction on `depth >= 8`; `showMateLabel = evalMate !== null && depth >= 8`; test asserts M-label present at depth=10 and absent at depth=5 |
| T8 | EngineLines renders up to 2 PV lines, each with its own score, a single depth badge, and clickable move chips | Plan 02 | VERIFIED | `MAX_LINES = 2`; `MAX_PLIES = 5`; depth badge shown only when `lineIndex === 0`; `PvLineRow` renders per-line `formatScore(line.evalCp, line.evalMate)`; 10 render tests pass |
| T9 | Clicking a PV move chip calls onMoveClick(from, to) with from/to derived from the UCI string (D-03) | Plan 02 | VERIFIED | `from = uciMove.slice(0,2)`, `to = uciMove.slice(2,4)`; `onClick={() => onMoveClick(from, to)}`; test verifies `onMoveClick("e2","e4")` fires on `engine-line-0-move-0` click via `vi.fn()` |
| T10 | EngineLines shows the Analyzing indicator only when isAnalyzing && pvLines.length === 0 | Plan 02 | VERIFIED | Spinner rendered in `{isAnalyzing && pvLines.length === 0 && ...}` branch only; `data-testid="engine-lines-analyzing"`; test asserts indicator present when `isAnalyzing=true && pvLines=[]`, absent when `pvLines` non-empty |
| T11 | VariationTree renders the flat main line plus the single active variation (BOARD-05 — full nested tree is v2) | Plan 03 | VERIFIED | `buildVariationChain` walks `parentId` chain to find variation nodes; test renders fixture with `mainLine=[1,2,3]` and `variation id=4`, asserts node-4 button appears |
| T12 | Clicking any move node calls onNodeClick(nodeId); the active node (currentNodeId) is highlighted and gets aria-current=step | Plan 03 | VERIFIED | Every button has `onClick={() => onNodeClick(nodeId)}` and `aria-current={isCurrent ? 'step' : undefined}`; tests verify: click on node-3 → `onNodeClick(3)`, click on variation node-4 → `onNodeClick(4)`, active node has `aria-current="step"`, non-active nodes do not |
| T13 | Mobile renders via the extended HorizontalMoveList; desktop renders a new vertical paired (N. white black) list; the responsive split is Tailwind dual-DOM (D-02) | Plan 03 | VERIFIED | `grep -c 'sm:hidden' VariationTree.tsx` → 2; `grep -c 'hidden sm:block' VariationTree.tsx` → 2; `grep -c 'useMediaQuery' VariationTree.tsx` → 0; both `variation-tree-mobile` and `variation-tree-desktop` testids present in DOM |
| T14 | The active node is auto-scrolled into view on currentNodeId change | Plan 03 | PRESENT_BEHAVIOR_UNVERIFIED | `useEffect(() => activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), [currentNodeId])` is present and `activeRef` is set on the active button; however jsdom stubs `scrollIntoView = vi.fn()` — actual scroll behavior requires a real browser |

**Score:** 13/14 truths verified (1 present, behavior-unverified)

### Deferred Items

Items intentionally not implemented in Phase 137 — explicitly addressed in Phase 138.

| # | Item | Addressed In | Evidence |
|---|------|-------------|---------|
| 1 | Drag-drop and click-to-click touch move input both work; board can be flipped | Phase 138 | D-01: "board wiring is Phase 138"; Phase 137 delivers `makeMove(from, to)` hook entry point only; board flip is Phase 138 board component responsibility |
| 2 | Board/variation state is encoded in the URL so the position is shareable and bookmarkable | Phase 138 | D-01: "read-only entry-point only; entry-point param reading is Phase 138 Analysis.tsx"; Phase 137 delivers `loadMainLine`/`rootFen` seeding (hook receives state) with NO URL write-back |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/hooks/useAnalysisBoard.ts` | Hook + MoveNode/NodeId/AnalysisBoardState/AnalysisBoardReturn types; 120+ lines | VERIFIED | 293 lines; exports `useAnalysisBoard`, `MoveNode`, `NodeId`, `AnalysisBoardState`, `AnalysisBoardReturn`; full 13-field return contract |
| `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` | Hook behavior tests; all 4 D-05 behaviors covered | VERIFIED | 209 lines; 6 tests (4 required + 2 boundary); all pass |
| `frontend/src/lib/theme.ts` | EVAL_BAR_WHITE / EVAL_BAR_BLACK semantic re-exports | VERIFIED | Lines 54-55: `EVAL_BAR_WHITE = EVAL_CHART_AREA_WHITE_AHEAD`, `EVAL_BAR_BLACK = EVAL_CHART_AREA_BLACK_AHEAD` |
| `frontend/src/components/analysis/EvalBar.tsx` | White-POV sigmoid eval bar; exports EvalBar | VERIFIED | Exports `EvalBar`, `EvalBarProps`; `SIGMOID_SCALE = 400` const; mate label depth-gated; `data-testid="analysis-eval-bar"` |
| `frontend/src/components/analysis/EngineLines.tsx` | Top 1-2 PV lines with score, depth badge, chips; exports EngineLines | VERIFIED | Exports `EngineLines`, `EngineLinesProps`; `MAX_LINES = 2`, `MAX_PLIES = 5`; reads `pvLines[i].evalCp/.evalMate`; all required testids present |
| `frontend/src/components/analysis/__tests__/EvalBar.test.tsx` | Render tests for EvalBar | VERIFIED | 7 tests; all pass |
| `frontend/src/components/analysis/__tests__/EngineLines.test.tsx` | Render tests for EngineLines | VERIFIED | 10 tests; all pass |
| `frontend/src/components/analysis/VariationTree.tsx` | Responsive move list; 60+ lines; exports VariationTree | VERIFIED | Exports `VariationTree`, `VariationTreeProps`; dual-DOM; MobileTree + DesktopTree subcomponents |
| `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` | Render tests against mainLine + one variation fixture | VERIFIED | 8 tests; all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `useAnalysisBoard.ts` | `chess.js` | `new Chess(parentFen).move(...)` inside `makeMove` | VERIFIED | `new Chess(` present; chess.js validates legality and returns null for illegal moves |
| `useAnalysisBoard.ts (goToNode)` | `nodes Map` | `nodes.get(id).fen` read with no replay loop | VERIFIED | `goToNode` is a pure `setState` functional updater; no for/while loop in the callback; FEN derived from `getPosition(state)` reading `nodes.get(s.currentNodeId)` |
| `EvalBar.tsx` | `theme.ts` | `import { EVAL_BAR_WHITE, EVAL_BAR_BLACK }` | VERIFIED | `grep -c 'EVAL_BAR_WHITE' EvalBar.tsx` → 1; `grep -c 'EVAL_CHART_AREA' EvalBar.tsx` → 0 |
| `EngineLines.tsx` | `PvLine.evalCp / .evalMate` | reads per-line score from `pvLines[i].evalCp/.evalMate` | VERIFIED | `grep -cE '\.evalCp\|\.evalMate' EngineLines.tsx` → 2; `grep -c 'pvLine\.score\|\.score\b' EngineLines.tsx` → 0 |
| `VariationTree.tsx` | `useAnalysisBoard.ts` | `import type { MoveNode, NodeId }` | VERIFIED | Line 13: `import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard'` |
| `VariationTree node chip onClick` | `onNodeClick prop` | `onClick={() => onNodeClick(nodeId)}` | VERIFIED | All move buttons use `onClick={() => onNodeClick(nodeId)}`; tests verify correct nodeId passed |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 31 phase 137 tests pass | `npx vitest run useAnalysisBoard.test.ts EvalBar.test.tsx EngineLines.test.tsx VariationTree.test.tsx` | 4 test files, 31 tests — all pass | PASS |
| TypeScript builds clean | `npx tsc -b` | No output (zero errors) | PASS |
| No dead exports (knip) | `npm run knip` | No knip output (zero issues) | PASS |
| No sessionStorage in hook | `grep -c 'sessionStorage' useAnalysisBoard.ts` | 0 | PASS |
| No URL write-back in hook | `grep -c 'history\.(push\|replace)State' useAnalysisBoard.ts` | 0 | PASS |
| No useChessGame import | `grep -c 'useChessGame' useAnalysisBoard.ts` | 0 | PASS |
| EvalBar uses theme constants not chart constants | `grep -c 'EVAL_CHART_AREA' EvalBar.tsx` | 0 | PASS |
| EvalBar no oklch literals | `grep -c 'oklch' EvalBar.tsx` | 0 | PASS |
| EvalBarProps has no orientation field | Interface inspection: `{ evalCp, evalMate, depth, className? }` | No orientation field | PASS |
| EngineLines reads per-line evalCp/.evalMate | `grep -cE '\.evalCp\|\.evalMate' EngineLines.tsx` | 2 | PASS |
| EngineLines reads no .score field | `grep -c 'pvLine\.score\|\.score\b' EngineLines.tsx` | 0 | PASS |
| No div/span onClick in EngineLines | `grep -cE '<(div\|span)[^>]*onClick' EngineLines.tsx` | 0 | PASS |
| VariationTree no useMediaQuery | `grep -c 'useMediaQuery' VariationTree.tsx` | 0 | PASS |
| VariationTree sm:hidden present | `grep -c 'sm:hidden' VariationTree.tsx` | 2 | PASS |
| VariationTree no dangerouslySetInnerHTML | `grep -c 'dangerouslySetInnerHTML' VariationTree.tsx` | 0 | PASS |
| useChessGame.ts unmodified (git) | Phase 137 commits: none touch useChessGame.ts | 8 commits — none modified useChessGame.ts | PASS |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `EvalBar.tsx` | 3, 54 | `orientation` appears in comments | Info | Plan acceptance criterion `grep -c 'orientation' EvalBar.tsx` expected 0 but returns 2 — both occurrences are in JSDoc comments explaining that there is NO orientation prop. The `EvalBarProps` interface has no `orientation` field and the component never flips. Goal is met; literal grep proxy test fails on comments only. |

### Requirements Coverage

| Requirement | Plans | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| BOARD-01 | 01 | User can make any legal move; mid-line move forks variation, not rejected | SATISFIED | `makeMove` forks new child node; T1 VERIFIED; test: mid-line fork asserts child created, mainLine unchanged |
| BOARD-02 | 01, 02, 03 | Navigate move tree (back/forward/jump/reset) and flip board | SATISFIED (Phase 137 scope) | Navigation hook fully implemented (T2, T3 VERIFIED); EvalBar white-POV for D-04; board flip deferred to Phase 138 per D-01 |
| BOARD-03 | 01, 02 | Drag-drop and click-to-click move input | SATISFIED (Phase 137 scope) | `makeMove(from, to)` is the input-agnostic entry point (BOARD-03); EngineLines PV chips call `onMoveClick(from, to)` (T9 VERIFIED); board wiring deferred to Phase 138 |
| BOARD-04 | 01 | URL-encoded shareable position; no server-side persistence | PARTIAL — Phase 137 scope only | `loadMainLine`/`rootFen` seeding implemented (T4 VERIFIED); no sessionStorage, no URL write-back (T5 VERIFIED); URL encoding/read-back deferred to Phase 138 per D-01 |
| BOARD-05 | 03 | Move list shows main line + single active variation; click to jump | SATISFIED | VariationTree renders flat main line + single active variation; click calls `onNodeClick(nodeId)` → `goToNode`; T11, T12 VERIFIED |

### Human Verification Required

#### 1. Desktop auto-scroll for active move node

**Test:** Load the analysis board with a long move tree (10+ moves). Navigate to a node that is off-screen in the desktop vertical move list (e.g. move 15). Verify the move list container scrolls to show the active node without manual user scroll.

**Expected:** The active move node is smoothly scrolled into view in the desktop `variation-tree-desktop` container. The `scrollIntoView({ block: 'nearest', behavior: 'smooth' })` call targets the active button element.

**Why human:** jsdom stubs `Element.prototype.scrollIntoView = vi.fn()` to prevent test throws but does not verify the call was made on the correct element after a `currentNodeId` change. Actual scroll behavior requires a real browser with layout. The code pattern is correct — `activeRef` is assigned to the active button via `ref={isCurrent ? activeRef : undefined}` and `useEffect` fires on `[currentNodeId]` — but runtime verification is needed.

---

_Verified: 2026-06-26T17:20:00Z_
_Verifier: Claude (gsd-verifier)_

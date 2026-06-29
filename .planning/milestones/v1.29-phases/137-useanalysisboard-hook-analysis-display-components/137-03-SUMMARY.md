---
phase: 137-useanalysisboard-hook-analysis-display-components
plan: "03"
subsystem: frontend/analysis
tags: [react, typescript, chess, analysis, move-list, responsive]
dependency_graph:
  requires:
    - "137-01 (MoveNode, NodeId types from useAnalysisBoard)"
    - "frontend/src/components/board/HorizontalMoveList.tsx"
    - "frontend/src/lib/moveNumberLabel.ts"
  provides:
    - "VariationTree component (mobile HorizontalMoveList + desktop vertical paired list)"
    - "Co-located Vitest render test with dual-DOM, variation, aria, click, and empty-state coverage"
  affects:
    - "Phase 138 (Analysis page composition — will import VariationTree alongside the board)"
tech_stack:
  added: []
  patterns:
    - "Tailwind dual-DOM responsive split (sm:hidden / hidden sm:block) — no media-query hook"
    - "HorizontalMoveItem ply=nodeId trick for bridging NodeId to onMoveClick callback"
    - "buildVariationChain O(n) walk via parentId to find active variation + fork point"
    - "Render functions (renderMoveButton, renderDesktopRow) as closures in DesktopTree for clean JSX"
key_files:
  created:
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
  modified: []
decisions:
  - "v1 paren placement inside HorizontalMoveItem trailing slot (inside button) rather than as adjacent non-button spans — avoids custom container reimplementation while preserving HorizontalMoveList auto-scroll delegation"
  - "Extracted buildVariationChain, buildDesktopRows, buildVariationRows as pure helpers outside subcomponents to keep MobileTree/DesktopTree logic shallow"
  - "MobileTree and DesktopTree as named function subcomponents (not inline renderers) to stay within CLAUDE.md soft LOC/nesting limits"
metrics:
  duration: "13 minutes"
  completed: "2026-06-26"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
status: complete
---

# Phase 137 Plan 03: VariationTree Component Summary

Responsive move-list component (mobile HorizontalMoveList + desktop vertical paired list) showing the flat main line plus the single active variation (BOARD-05), with click-to-jump via `onNodeClick`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | VariationTree component — mobile + desktop dual-DOM | `7cf55db2` | `VariationTree.tsx` |
| 2 | VariationTree render test (mainLine + one variation fixture) | `a06b46d2` | `VariationTree.test.tsx` |

## What Was Built

### `VariationTree.tsx`

Exports `VariationTree` — a single component wrapping two subcomponents in a Tailwind dual-DOM (`sm:hidden` / `hidden sm:block`) responsive split:

**MobileTree** — calls `HorizontalMoveList` with a computed `HorizontalMoveItem[]`:
- Main-line nodes map to chips (ply = nodeId, so `onMoveClick(ply) → onNodeClick(nodeId)`).
- Move-number labels use `moveLabel(rootPly, idx)` for white moves only (same as `MoveList.tsx`).
- At the fork node, a `(` trailing span is added inside the button.
- Active variation nodes are inserted after the fork chip; the last variation chip gets a `)` trailing span.
- Main-line moves after the fork are rendered with `dimmed: true`.
- Auto-scroll and empty-state are delegated to `HorizontalMoveList` (no reimplementation).

**DesktopTree** — new vertical paired N. white black list:
- `buildDesktopRows` pairs main-line nodes into `{moveNumber, whiteNodeId, blackNodeId}` rows, handling odd `rootPly` (black to move at root).
- `buildVariationRows` builds the same paired structure for the active variation chain.
- Variation rows are rendered with `ml-8` indentation after the row containing the fork parent.
- Active button: `bg-primary text-primary-foreground hover:bg-primary/90`. Inactive variation chips: `text-muted-foreground`.
- `activeRef` + `useEffect(() => scrollIntoView, [currentNodeId])` for auto-scroll.
- Empty state: `<p className="text-sm text-muted-foreground p-2">No moves yet</p>`.

**Outer container** (`data-testid="analysis-variation-tree"`) carries `aria-label="Move list"` and `role="navigation"`.

### `VariationTree.test.tsx`

8 tests covering:
1. Both `variation-tree-mobile` and `variation-tree-desktop` testids present in the document (dual-DOM always in the DOM, hidden by CSS only).
2. Main-line buttons render with correct `data-testid="variation-node-{id}"` and SAN text.
3. Variation node (id=4, "d5", `parentId=1`) renders when `currentNodeId=4` (BOARD-05).
4. Active node has `aria-current="step"`; non-active nodes do not.
5. Clicking a main-line button calls `onNodeClick(nodeId)`.
6. Clicking the variation button calls `onNodeClick(4)`.
7. Empty state shows "No moves yet".

Stubs: `Element.prototype.scrollIntoView`, `matchMedia`, `ResizeObserver` (same pattern as `EngineLines.test.tsx`).

## Verification Gate Results

| Gate | Result |
|------|--------|
| `npx tsc -b` | PASS (zero errors) |
| `npx vitest run VariationTree.test.tsx` | PASS (8/8 tests) |
| `npm run knip` | PASS (no dead exports) |
| `npm run lint` | PASS (0 errors; 3 pre-existing warnings in `coverage/` — gitignored) |
| No `dangerouslySetInnerHTML` | PASS (grep returns 0) |
| No media-query hook (`useMediaQuery`) | PASS (grep returns 0) |
| `sm:hidden` dual-DOM present | PASS (2 occurrences) |
| `hidden sm:block` dual-DOM present | PASS (2 occurrences) |
| All testids present | PASS (`analysis-variation-tree`, `variation-tree-mobile`, `variation-tree-desktop`, `variation-node-${id}`) |
| No `<div onClick>` / `<span onClick>` | PASS (grep returns 0) |
| No `text-xs` | PASS (grep returns 0) |

## Deviations from Plan

### Auto-fixed Issues

None.

### Deliberate Adjustments

**1. [Rule 2 - Design clarity] Paren placement in mobile path**
- **Found during:** Task 1 implementation.
- **Plan said:** "render the parens via the chip item `trailing` slot or as adjacent non-button spans".
- **Chosen:** `trailing` slot (parens inside the fork/last-variation buttons) rather than adjacent non-button spans.
- **Why:** The alternative (custom container replicating HorizontalMoveList's styling) would require reimplementing auto-scroll and empty-state, which the plan explicitly forbids for the mobile path ("HorizontalMoveList already provides auto-scroll + the empty box — do NOT reimplement either for mobile"). v1 simplification acknowledged; the spec explicitly allowed either approach.
- **Files modified:** `VariationTree.tsx` (MobileTree).

**2. [Rule 2 - Readability] Comment phrasing adjusted**
- **Why:** The acceptance criteria uses literal `grep -c` checks for "useMediaQuery" and "dangerouslySetInnerHTML" returning 0. Initial JSDoc comments mentioned these terms (documenting their absence). Rephrased to "no media-query hook" and "no unsafe HTML injection" to satisfy the literal greps without losing intent.

## Known Stubs

None. Component renders real data from the `nodes` Map and `mainLine` array passed by the parent. No placeholder text or hardcoded empty values flow to the UI.

## Threat Flags

None. `VariationTree` is a pure presentational component with no network calls, no storage access, and no user-typed input. The only external data is `node.san` (chess.js-validated move SAN strings), rendered as normal JSX children (T-137-05 mitigated — React auto-escapes all JSX text children).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `frontend/src/components/analysis/VariationTree.tsx` | FOUND |
| `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` | FOUND |
| `.planning/phases/137-.../137-03-SUMMARY.md` | FOUND |
| Commit `7cf55db2` (Task 1) | FOUND |
| Commit `a06b46d2` (Task 2) | FOUND |

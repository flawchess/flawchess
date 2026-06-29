---
phase: 137-useanalysisboard-hook-analysis-display-components
reviewed: 2026-06-26T15:30:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - frontend/src/hooks/useAnalysisBoard.ts
  - frontend/src/components/analysis/EvalBar.tsx
  - frontend/src/components/analysis/EngineLines.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/lib/theme.ts
  - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts
  - frontend/src/components/analysis/__tests__/EvalBar.test.tsx
  - frontend/src/components/analysis/__tests__/EngineLines.test.tsx
  - frontend/src/components/analysis/__tests__/VariationTree.test.tsx
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 137: Code Review Report

**Reviewed:** 2026-06-26T15:30:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 137 delivers a branching move-tree hook (`useAnalysisBoard`), two engine-output display components (`EvalBar`, `EngineLines`), and a responsive move list (`VariationTree`). The overall implementation is solid: types are correct, the O(1) FEN-per-node design is intact, ARIA attributes are broadly present, and the no-sessionStorage / no-URL-write-back constraints are respected. Four warnings were found: one is a concrete crash path (`loadMainLine` missing try-catch while chess.js 1.x always throws for invalid SANs), one is an accessibility inconsistency in `EvalBar`'s aria-label, one is a structural stale-ref concern in `makeMove`, and one is a nested landmark violation in `VariationTree`. Four info items cover dead code and minor style issues.

No security vulnerabilities were found. All engine strings flow through React JSX children (auto-escaped). No `dangerouslySetInnerHTML`, no `eval`, no hardcoded credentials.

## Warnings

### WR-01: `loadMainLine` missing try-catch — chess.js 1.x always throws for invalid SANs

**File:** `frontend/src/hooks/useAnalysisBoard.ts:226-230`

**Issue:** The `loadMainLine` callback calls `chess.move(san)` without a try-catch, relying on `if (!move) break` to handle illegal SANs. Chess.js 1.x (confirmed from the installed `dist/esm/chess.js`) always throws `Error: Invalid move: <san>` when a SAN string is invalid — it never returns null. The null guard is therefore dead code and offers no protection. By contrast, `makeMove` correctly wraps `chess.move()` in try-catch. If Phase 138 passes a malformed PGN line to `loadMainLine` (e.g., a non-standard variant move or a parsing bug), the uncaught exception propagates through the useCallback, crashes the caller, and may bring down the surrounding component tree.

**Fix:**
```ts
for (const san of sans) {
  let move: ReturnType<typeof chess.move> | null = null;
  try {
    move = chess.move(san);
  } catch {
    break; // stop on illegal SAN (chess.js throws, never returns null)
  }
  if (!move) break; // defensive: belt-and-suspenders in case future versions return null
  const node = buildNode(id, move.san, chess.fen(), move.from, move.to, prevId);
  newNodes.set(id, node);
  newMainLine.push(id);
  prevId = id;
  id++;
}
```

---

### WR-02: `EvalBar` aria-label shows mate text regardless of depth gate — screen reader inconsistency

**File:** `frontend/src/components/analysis/EvalBar.tsx:36-46, 72`

**Issue:** `scoreText(evalCp, evalMate)` returns mate notation (e.g., `M3`) whenever `evalMate !== null`, regardless of depth. But the visual mate label and the full-bar fraction are only applied when `depth >= 8`. When `evalMate !== null && depth < 8`, the visual bar shows a centipawn fill (or 0.5 if evalCp is also null) with no label, but the `aria-label` announces `"Engine evaluation: M3"`. Screen reader users are told about a mate the visual component is intentionally suppressing, which is misleading.

**Fix:** Pass `depth` into `scoreText` and apply the same gate:

```ts
function scoreText(
  evalCp: number | null,
  evalMate: number | null,
  depth: number,
): string {
  if (evalMate !== null && depth >= 8) {
    return evalMate >= 0 ? `M${evalMate}` : `-M${Math.abs(evalMate)}`;
  }
  if (evalCp !== null) {
    const cp = evalCp / 100;
    return cp >= 0 ? `+${cp.toFixed(2)}` : cp.toFixed(2);
  }
  return '0.00';
}
// usage:
aria-label={`Engine evaluation: ${scoreText(evalCp, evalMate, depth)}`}
```

---

### WR-03: `makeMove` reads `nextId` and `currentNodeId` from stale `stateRef` — node ID collision on rapid successive calls

**File:** `frontend/src/hooks/useAnalysisBoard.ts:145-173`

**Issue:** `makeMove` snapshots `nextId` and `currentNodeId` from `stateRef.current` synchronously, then builds the new node with those values before calling `setState`. `stateRef` is only synced via `useEffect` — it is NOT updated until after the render that follows the setState call. If `makeMove` is called programmatically in a tight sequence (e.g., from a `useEffect` that calls `loadMainLine` then immediately `makeMove`, or from a test that fires two makeMoves in the same microtask without awaiting a render), both calls read the same `nextId` from the stale ref. The first call's node (id=N) is then silently overwritten by the second call's node (also id=N) in the Map inside the functional setState updater.

In normal UI usage (board click/drag) this cannot happen because each user action is separated by a render. The risk window is programmatic call sites in Phase 138, particularly effects that need to seed the board and then advance the position.

**Fix:** Move `nextId` (and `currentNodeId` for `parentId`) inside the functional setState updater. The `parentFen` computation still needs to happen before the setter (chess.js must run first to compute the result), but the node assignment can use `prev.nextId`:

```ts
const makeMove = useCallback((from: string, to: string): boolean => {
  const { currentNodeId, nodes, rootFen } = stateRef.current;
  const parentFen =
    currentNodeId !== null ? (nodes.get(currentNodeId)?.fen ?? rootFen) : rootFen;

  const chess = new Chess(parentFen);
  let result: ReturnType<typeof chess.move>;
  try {
    result = chess.move({ from, to, promotion: 'q' });
  } catch {
    return false;
  }
  if (!result) return false;

  const san = result.san;
  const fen = chess.fen();
  const moveFrom = result.from;
  const moveTo = result.to;

  setState((prev) => {
    // Read nextId from prev, not stateRef, to avoid stale-ID collisions.
    const newNode = buildNode(prev.nextId, san, fen, moveFrom, moveTo, prev.currentNodeId);
    const newNodes = new Map(prev.nodes);
    newNodes.set(newNode.id, newNode);
    return { ...prev, nodes: newNodes, currentNodeId: newNode.id, nextId: prev.nextId + 1 };
  });

  return true;
}, []);
```

Note: `currentNodeId` for `parentFen` is still read from `stateRef` (required to compute `parentFen` before `setState`). The `prev.currentNodeId` inside the setter is used only for `parentId` on the new node — these will agree in all single-move-per-render cases. The collision risk (duplicate IDs) is fully eliminated by using `prev.nextId` inside the setter.

---

### WR-04: Nested `role="navigation"` in `VariationTree` — duplicate landmarks for screen readers

**File:** `frontend/src/components/analysis/VariationTree.tsx:343, 311`

**Issue:** The outer `VariationTree` wrapper div declares `role="navigation" aria-label="Move list"`. `DesktopTree`'s container div also declares `role="navigation" aria-label="Move list"`. On desktop (where the `hidden sm:block` wrapper is visible), both regions are present in the accessibility tree simultaneously. Screen readers that navigate by landmarks (NVDA Ins+F7, VoiceOver Rotor) announce two "Move list navigation" regions with identical names — a WCAG 4.1.2 violation. The mobile path does not have this issue because `HorizontalMoveList` does not add a `role="navigation"`.

**Fix:** Remove `role="navigation"` and `aria-label` from the outer `VariationTree` wrapper (it is a structural container, not a semantic landmark). Let `DesktopTree`'s container carry the single landmark:

```tsx
export function VariationTree(props: VariationTreeProps) {
  return (
    <div data-testid="analysis-variation-tree">
      <div className="sm:hidden">
        <MobileTree {...props} />
      </div>
      <div className="hidden sm:block">
        <DesktopTree {...props} />
      </div>
    </div>
  );
}
```

`DesktopTree` retains its `role="navigation" aria-label="Move list"` (and the empty-state branch also retains it). The mobile path (`HorizontalMoveList`) carries no navigation role and is consistent with its existing landmark-free design.

---

## Info

### IN-01: Dead ternary in `moveLabel` call — both branches identical

**File:** `frontend/src/components/analysis/EngineLines.tsx:108`

**Issue:** `moveLabel(startPly, lineIndex === 0 ? moveIndex : moveIndex)` — the ternary evaluates to `moveIndex` in both branches, making the condition entirely meaningless. Looks like an unfinished refactor or copy-paste error.

**Fix:** Simplify to `moveLabel(startPly, moveIndex)`.

---

### IN-02: `visibleLines.map((_, lineIndex)` discards direct element then re-indexes

**File:** `frontend/src/components/analysis/EngineLines.tsx:167-170`

**Issue:**
```tsx
{visibleLines.map((_, lineIndex) => {
  const line = visibleLines[lineIndex];
  if (!line) return null;
```
The `_` discards the mapped element, then re-indexes `visibleLines[lineIndex]` to get it back (required only because `noUncheckedIndexedAccess` types array subscripts as `T | undefined`). The `if (!line) return null` can never be true: `lineIndex` is always a valid index produced by iterating the same array. The convoluted pattern also adds confusion about intent.

**Fix:** Map the element directly. TypeScript types `.map`'s callback parameter as the element type (not `T | undefined`), so the null check is unnecessary:
```tsx
{visibleLines.map((line, lineIndex) => (
  <PvLineRow
    key={lineIndex}
    line={line}
    ...
  />
))}
```

---

### IN-03: Non-null assertions on `evalMate!` in `EvalBar` — prefer narrowed local variable

**File:** `frontend/src/components/analysis/EvalBar.tsx:66, 98`

**Issue:** `mateIsWhiteWinning = showMateLabel && evalMate! > 0` and `M{Math.abs(evalMate!)}` use non-null assertions. Both are runtime-safe (guarded by `showMateLabel`), but the pattern relies on the reader trusting the `showMateLabel` compound boolean rather than type narrowing. An alternative is to produce a narrowed variable early:

```tsx
const resolvedMate = evalMate !== null && depth >= 8 ? evalMate : null;
const showMateLabel = resolvedMate !== null;
const mateIsWhiteWinning = resolvedMate !== null && resolvedMate > 0;
// later:
M{Math.abs(resolvedMate)}  // no assertion needed; TypeScript narrows to number
```

This also fixes WR-02 naturally since `resolvedMate` already incorporates the depth gate.

---

### IN-04: `MobileTree` default `heightClass` includes unused `sm:h-20` modifier

**File:** `frontend/src/components/analysis/VariationTree.tsx:214`

**Issue:** `heightClass ?? 'h-20 sm:h-20'` — the `sm:h-20` Tailwind class applies at the `sm` breakpoint, but `MobileTree` renders inside `<div className="sm:hidden">`, so it is never visible at `sm+`. The `sm:h-20` portion is dead.

**Fix:** Use `'h-20'` as the default (no breakpoint modifier needed):
```tsx
heightClass={heightClass ?? 'h-20'}
```

---

_Reviewed: 2026-06-26T15:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

# Phase 137: `useAnalysisBoard` Hook + Analysis Display Components - Pattern Map

**Mapped:** 2026-06-26
**Files analyzed:** 7 (4 source + 2 test groups + 1 modify)
**Analogs found:** 6 / 7 (EvalBar has no direct render analog — viz primitive)

> No RESEARCH.md for this phase. Technical approach comes from `.planning/research/ARCHITECTURE.md`
> (Pattern 3 / Pattern 5 / component contract table) and `137-UI-SPEC.md` (full component contracts).
> All analogs below were read in full from the live codebase.

---

## CRITICAL CONTRACT MISMATCH (planner must resolve)

The UI-SPEC's EngineLines section (137-UI-SPEC.md line 209) says *"Use `pvLine.score` from the
engine hook's `PvLine` type."* **This field does not exist.** The real Phase 136 `PvLine`
(`frontend/src/hooks/uciParser.ts` lines 14-24) is:

```typescript
export interface PvLine {
  multipv: number;          // 1-based MultiPV index
  depth: number;
  moves: string[];          // UCI strings, e.g. ['e2e4', 'd7d5']
  evalCp: number | null;    // centipawns, white-POV; null if mate
  evalMate: number | null;  // mate in N; null if cp score
}
```

There is no `score` field — each line carries its own `evalCp` / `evalMate`. The planner must
specify EngineLines reads `pvLine.evalCp` / `pvLine.evalMate` per line (not a top-level
`evalCp`/`evalMate` prop) for the per-line score. The component's top-level `evalCp`/`evalMate`
props in the UI-SPEC `EngineLinesProps` are redundant with `pvLines[i].evalCp/evalMate` — flag
this duplication; prefer reading per-line values from `pvLines`.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/hooks/useAnalysisBoard.ts` | hook | transform / event-driven (move tree + nav) | `frontend/src/hooks/useTacticLine.ts` | role-match (stepper→tree) |
| `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` | test | — | `frontend/src/hooks/__tests__/useTacticLine.test.tsx` | exact |
| `frontend/src/components/analysis/EvalBar.tsx` | component | request-response (props→render) | (none — new viz primitive) | no-analog |
| `frontend/src/components/analysis/EngineLines.tsx` | component | request-response | `frontend/src/components/board/HorizontalMoveList.tsx` (chip) | role-match |
| `frontend/src/components/analysis/VariationTree.tsx` | component | request-response | `HorizontalMoveList.tsx` + `board/MoveList.tsx` | exact (mobile) / role-match (desktop) |
| `frontend/src/components/analysis/__tests__/*.test.tsx` | test | — | `components/charts/__tests__/PercentileChip.test.tsx` | exact |
| `frontend/src/lib/theme.ts` | config | — | self (existing eval-chart constants at lines 48-49) | exact |

---

## Pattern Assignments

### `frontend/src/hooks/useAnalysisBoard.ts` (hook, branching move tree)

**Primary analog:** `frontend/src/hooks/useTacticLine.ts` (Phase 135) — the closest structural
match. It is the cloned-from-`useChessGame` ephemeral stepper with NO sessionStorage / NO Zobrist /
NO opening lookup, and the **container-scoped keyboard handler** that ARCHITECTURE Pattern 3
mandates. `useAnalysisBoard` extends this from a *linear stepper* to a *branching tree* (FEN per node).
**Do NOT modify `useChessGame.ts`** (ARCHITECTURE "do not modify", line 191).

**Container-scoped keyboard pattern — copy from `useTacticLine.ts` lines 181-197** (NOT
`useChessGame`'s window-level handler at lines 263-279):
```typescript
const containerRef = useRef<HTMLDivElement | null>(null);
// ...
useEffect(() => {
  const container = containerRef.current;
  if (!container) return;
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft') { e.preventDefault(); goBack(); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); goForward(); }
  };
  container.addEventListener('keydown', handleKeyDown);
  return () => container.removeEventListener('keydown', handleKeyDown);
}, [goBack, goForward]);
```

**Stale-closure-safe nav callbacks — copy the ref-sync pattern from `useTacticLine.ts` lines 99-110.**
The container-scoped keydown handler is NOT recreated on every state change, so `goForward`/`goBack`
must read latest values from refs updated each render, not close over stale state:
```typescript
const currentNodeIdRef = useRef<NodeId | null>(null);
useEffect(() => { currentNodeIdRef.current = currentNodeId; });
```

**makeMove fork behavior — adapt from `useChessGame.ts` lines 162-203 BUT invert the truncation.**
`useChessGame.makeMove` truncates future history when moving mid-line (lines 187-189). The analysis
hook must do the opposite: fork a child node. Use the chess.js move shape exactly as `useChessGame`
does (lines 170-180):
```typescript
const result = chess.move({ from: sourceSquare, to: targetSquare, promotion: 'q' });
if (!result) return false;
const san = result.san; const from = result.from; const to = result.to;
```
Fork construction follows ARCHITECTURE Pattern 3 (lines 224-243): build `Chess(parentFen)`, move,
store `{ id, san, fen: chess.fen(), from, to, parentId: currentNodeId }`, advance `nextId`, set
`currentNodeId = newNode.id`. **Key win over `useChessGame`:** store FEN per node so `goToNode(id)`
is O(1) (`nodes.get(id).fen`) — no replay-from-root (ARCHITECTURE lines 208-209).

**MoveNode / state shape — copy verbatim from ARCHITECTURE Pattern 3 (lines 196-219):**
```typescript
type NodeId = number;
interface MoveNode { id: NodeId; san: string; fen: string; from: string; to: string; parentId: NodeId | null; }
// state: nodes: Map<NodeId, MoveNode>; currentNodeId: NodeId | null; mainLine: NodeId[]; rootFen: string; nextId: number;
```

**loadMainLine — adapt the replay loop from `useChessGame.loadMoves` (lines 234-240) /
`useTacticLine.replayTo` (lines 117-136)**, but instead of a flat history, create one MoveNode per
SAN and record their IDs into `mainLine`. Seed `rootFen` from the arg (like `useTacticLine` starts
from `rootFen`, not the chess start position — lines 92, 119).

**Return contract (from CONTEXT line 15 / ARCHITECTURE line 427):**
`{ position, currentNodeId, nodes, mainLine, rootFen, lastMove, makeMove, goBack, goForward, goToNode, loadMainLine, isOnMainLine, containerRef }`.
`isOnMainLine(nodeId)` = `mainLine.includes(nodeId)` (ARCHITECTURE line 253).

**No URL write-back (D-01):** the hook reads no URL itself in 137 — entry-point param reading is
Phase 138's `Analysis.tsx`. Do NOT add sessionStorage (ARCHITECTURE line 257), Zobrist, or opening
lookup (line 259) — these are exactly what `useTacticLine` already drops vs `useChessGame`.

**`noUncheckedIndexedAccess` narrowing — copy the `hist[i]!` / loop-bound-comment idiom** from
`useTacticLine.ts` line 124 / `useChessGame.ts` line 149 (`// safe: loop bound ensures i < ply`).

---

### `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` (hook test)

**Analog:** `frontend/src/hooks/__tests__/useTacticLine.test.tsx` (read lines 1-58).

**Setup pattern (copy lines 1, 17-30):**
```typescript
// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAnalysisBoard } from '../useAnalysisBoard';

// Legal FEN + chess.js-verified SAN moves (mirror useTacticLine's ROOT_FEN/MOVES constants)
const ROOT_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
```

**Assertion idiom (copy lines 32-58):** `renderHook(() => useAnalysisBoard(...))`, mutate via
`act(() => { result.current.makeMove('e2','e4'); })`, assert on `result.current.*`.

**Required behaviors (D-05, CONTEXT lines 65-70) — one `it()` each:**
- mid-line `makeMove` creates a CHILD node (nodes.size grows, mainLine NOT truncated)
- `goBack`/`goForward`/`goToNode` navigation correctness
- `goToNode` is O(1) — position equals `nodes.get(id).fen` with no root replay (assert FEN match)
- `loadMainLine` seeds `mainLine` + `isOnMainLine` returns true for seeded IDs, false for forks

**Note:** unlike `useTacticLine.test.tsx` (`.tsx`), CONTEXT names this file `.test.ts` (no JSX in a
pure hook test). Keep `// @vitest-environment jsdom` regardless (renderHook needs a DOM).

---

### `frontend/src/components/analysis/EvalBar.tsx` (component, no render analog)

**No direct analog** — this is a new vertical-bar viz primitive. The only reuse is **theme
constants** (see Shared Patterns → EvalBar Colors). Build straight from UI-SPEC lines 131-184:
- Container `relative flex flex-col border border-border rounded overflow-hidden w-4`.
- Two absolutely-positioned fill divs; `height = whiteFraction * 100%` (white, top) / remainder
  (black, bottom); backgrounds via inline `style={{ background: EVAL_BAR_WHITE }}` /
  `EVAL_BAR_BLACK` (theme imports, NOT hard-coded oklch).
- Sigmoid `cpToFraction` (UI-SPEC lines 142-147) lives in the component, not the hook.
- Mate label gate `evalMate !== null && depth >= 8` (D-04).
- `data-testid="analysis-eval-bar"`, `role="img"`, dynamic `aria-label`.

**`noUncheckedIndexedAccess`:** no array indexing here, but extract `SIGMOID_SCALE = 400` as a named
const (CLAUDE.md no-magic-numbers) — UI-SPEC already names it.

---

### `frontend/src/components/analysis/EngineLines.tsx` (component, PV display)

**Analog:** `frontend/src/components/board/HorizontalMoveList.tsx` — copy the **chip button class
string** (lines 100-104) for PV move buttons:
```typescript
'inline-flex items-center gap-0.5 rounded px-1 py-0.5 font-mono transition-colors hover:bg-accent'
```
PV chips get NO active highlight (UI-SPEC line 227) — they are suggestions, not the board position.

**Per-line score:** read `pvLine.evalCp` / `pvLine.evalMate` (see CRITICAL CONTRACT MISMATCH above),
NOT a `pvLine.score`. Format per UI-SPEC lines 203-208.

**Move chip = `<button>`** (semantic HTML, CLAUDE.md), `onClick={() => onMoveClick(from, to)}` where
`from`/`to` are derived from UCI: `move.slice(0,2)` / `move.slice(2,4)`, promotion = `move[4]`
(UI-SPEC line 224). `data-testid={`engine-line-${lineIndex}-move-${moveIndex}`}`.

**`noUncheckedIndexedAccess` (CLAUDE.md, hard rule):** narrow every PV access —
`const line = pvLines[0]; if (!line) return null;` — never bare `pvLines[i]`. The loop-bound `!`
idiom from `useTacticLine.ts` line 124 applies when index is provably in range.

**Analyzing state (UI-SPEC lines 213-219):** lucide `Loader2` + "Analyzing…" only when
`isAnalyzing && pvLines.length === 0`. Wrap the icon for a11y per Accessibility Contract line 399.

**Move-number labels:** `moveLabel(startPly, index)` from `lib/moveNumberLabel.ts` (read in full;
the helper is `moveLabel(flawPly, index)` returning `"12."` / `"12..."`). `startPly` optional, default 0.

---

### `frontend/src/components/analysis/VariationTree.tsx` (component, branching move list)

**Mobile path — EXTEND `HorizontalMoveList.tsx` (exact analog).** Build a flat
`HorizontalMoveItem[]` exactly as `board/MoveList.tsx` does (read in full, lines 14-29):
```typescript
const items: HorizontalMoveItem[] = mainLine.map((nodeId, idx) => {
  const node = nodes.get(nodeId);          // narrow: noUncheckedIndexedAccess
  if (!node) return null;                   // (filter nulls after map)
  return {
    key: nodeId,
    ply: nodeId,                            // onMoveClick(ply) → goToNode(nodeId)
    numberLabel: /* moveLabel(rootPly, idx) — white only, like MoveList line 21 */,
    san: node.san,
    isCurrent: nodeId === currentNodeId,
    testId: `variation-node-${nodeId}`,
    ariaLabel: `Move ${label} ${node.san}`,
  };
});
```
`HorizontalMoveItem` already supports everything needed for variations: `dimmed` (main line after
fork point, UI-SPEC line 280), `trailing` ReactNode (closing paren), `color`. The parenthesis spans
use `text-muted-foreground select-none` (UI-SPEC line 119) — render as adjacent non-button spans /
via the `trailing` slot. Pass `heightClass="h-20 sm:h-20"` (UI-SPEC line 284, overrides the default
`h-12 sm:h-18` at HorizontalMoveList line 53). `data-testid="variation-tree-mobile"`.

**`HorizontalMoveList` already provides auto-scroll** (lines 57-64, keyed on the current item's key) —
the mobile path inherits it for free; do NOT reimplement.

**Desktop path — NEW vertical paired list** (no exact analog; build per UI-SPEC lines 286-322).
Reuse the SAME chip classes from `HorizontalMoveList` lines 100-104 for cell buttons; active cell
`bg-primary text-primary-foreground hover:bg-primary/90`. Auto-scroll: replicate the
`HorizontalMoveList` effect (lines 57-64) on an `activeRef` →
`scrollIntoView({ block: 'nearest', behavior: 'smooth' })`; container `overflow-y-auto`.

**Responsive split** (UI-SPEC lines 262-269): dual-DOM `<div className="sm:hidden">` /
`<div className="hidden sm:block">`. NOTE: there is **no `useMediaQuery` hook in the codebase**
(grep confirmed — only `useRevealOnOpen`/`useInstallPrompt` call `matchMedia` inline). Prefer the
Tailwind dual-DOM approach over introducing a new hook.

**Empty state:** mobile passes `emptyText="No moves yet"` to `HorizontalMoveList` (it renders the
empty box itself, lines 66-78); desktop renders `<p className="text-sm text-muted-foreground p-2">No moves yet</p>`.

---

### `frontend/src/components/analysis/__tests__/{EvalBar,EngineLines,VariationTree}.test.tsx`

**Analog:** `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` (read lines 1-50).

**Setup (copy lines 1, 26-50):**
```typescript
// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
afterEach(cleanup);
```
Include the `matchMedia` + `ResizeObserver` stubs (PercentileChip lines 29-49) — VariationTree's
responsive split and any scrollIntoView usage need a jsdom-friendly window. `scrollIntoView` is not
implemented in jsdom; stub it (`Element.prototype.scrollIntoView = vi.fn()`) in VariationTree's test.

**Assert against fixture props** (D-05): EvalBar (eval/mate/depth tuples → fill fraction, mate-label
gate at depth 8), EngineLines (PvLine[] fixtures → chip count, score text, `onMoveClick` fires with
derived from/to via `fireEvent.click`), VariationTree (a mainLine + one variation → active chip,
`onNodeClick` fires nodeId). Query by `data-testid` per the UI-SPEC naming table (lines 408-419).

---

### `frontend/src/lib/theme.ts` (MODIFY — add EvalBar re-exports)

The two source constants already exist (confirmed at lines 48-49):
```typescript
export const EVAL_CHART_AREA_WHITE_AHEAD = 'oklch(0.78 0 0)';
export const EVAL_CHART_AREA_BLACK_AHEAD = 'oklch(0.32 0 0)';
```
Append the two semantic aliases verbatim from UI-SPEC lines 88-93 / 437-441:
```typescript
// EvalBar semantic re-exports — same oklch values as the eval chart area fills
// so the two surfaces share one palette entry and branding changes need one edit.
export const EVAL_BAR_WHITE = EVAL_CHART_AREA_WHITE_AHEAD; // 'oklch(0.78 0 0)'
export const EVAL_BAR_BLACK = EVAL_CHART_AREA_BLACK_AHEAD; // 'oklch(0.32 0 0)'
```
EvalBar imports `EVAL_BAR_WHITE`/`EVAL_BAR_BLACK` only — never the chart constants directly.
**knip note (CLAUDE.md):** these new exports must be imported by EvalBar in the same phase or knip
fails CI.

---

## Shared Patterns

### Move chip class string (THE shared visual token)
**Source:** `frontend/src/components/board/HorizontalMoveList.tsx` lines 100-104.
**Apply to:** EngineLines PV chips, VariationTree desktop cells (mobile inherits via HorizontalMoveList).
```typescript
// inactive chip
'inline-flex items-center gap-0.5 rounded px-1 py-0.5 font-mono transition-colors hover:bg-accent'
// active chip (VariationTree only; EngineLines PV chips never active)
'bg-primary text-primary-foreground hover:bg-primary/90'
// dimmed (non-active, context) chip
'text-muted-foreground'
```

### Auto-scroll to active node
**Source:** `HorizontalMoveList.tsx` lines 57-64.
**Apply to:** VariationTree desktop (mobile inherits it). `activeRef` on the current button,
`useEffect(() => activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), [currentKey])`.

### Container-scoped keyboard (NOT window-level)
**Source:** `frontend/src/hooks/useTacticLine.ts` lines 181-197 (NOT `useChessGame.ts` 263-279).
**Apply to:** `useAnalysisBoard` (the components install no keyboard handlers — UI-SPEC line 389).

### Move-number labels
**Source:** `frontend/src/lib/moveNumberLabel.ts` — `moveLabel(startPly, index)` → `"12."`/`"12..."`.
**Apply to:** EngineLines (PV line labels) and VariationTree (mainLine labels), both with a
`rootPly`/`startPly` prop defaulting to 0.

### chess.js move-making
**Source:** `useChessGame.ts` lines 170-180 (move shape) + the ARCHITECTURE Pattern 3 fork snippet.
**Apply to:** `useAnalysisBoard.makeMove`. `{ from, to, promotion: 'q' }`; read `result.san/from/to`.

### `noUncheckedIndexedAccess` narrowing (CLAUDE.md hard rule)
**Source idioms:** loop-bound `hist[i]!` with `// safe: loop bound` comment (`useTacticLine.ts` 124);
`const node = nodes.get(id); if (!node) return null;` for Map/array reads.
**Apply to:** every `pvLines[i]`, `moves[j]`, `nodes.get(id)`, `mainLine[idx]` access.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/components/analysis/EvalBar.tsx` | component | request-response | No vertical-bar / gauge primitive exists. Build from UI-SPEC lines 131-184; only shared dependency is `theme.ts` EvalBar constants. The chart components in `components/charts/` are all Recharts SVG, not absolute-positioned fill bars — not a usable analog. |

---

## Metadata

**Analog search scope:** `frontend/src/hooks/`, `frontend/src/hooks/__tests__/`,
`frontend/src/components/board/`, `frontend/src/components/charts/__tests__/`, `frontend/src/lib/`.
**Files read in full:** `HorizontalMoveList.tsx`, `MoveList.tsx`, `useTacticLine.ts`,
`useChessGame.ts`, `tacticDepth.ts`, `moveNumberLabel.ts`, `useTacticLine.test.tsx` (head),
`PercentileChip.test.tsx` (head); targeted reads: `uciParser.ts` (PvLine), `theme.ts` (eval consts),
`useStockfishEngine.ts` (return shape).
**Pattern extraction date:** 2026-06-26

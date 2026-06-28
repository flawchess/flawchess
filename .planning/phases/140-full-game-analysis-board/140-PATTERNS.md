# Phase 140: Full-Game Analysis Board - Pattern Map

**Mapped:** 2026-06-27
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/hooks/useAnalysisBoard.ts` | hook | event-driven (state machine) | itself (existing methods) | self-extension |
| `frontend/src/components/analysis/VariationTree.tsx` | component | transform | itself (existing single-level) | self-extension |
| `frontend/src/components/analysis/TacticModeOverlay.tsx` | component | request-response | `Analysis.tsx` isTacticMode block | role-match |
| `frontend/src/pages/Analysis.tsx` | page | request-response | itself (existing isTacticMode/useTacticLines block) | self-extension |
| `frontend/src/components/results/LibraryGameCard.tsx` | component | CRUD | itself (existing `renderDesktopExploreButton`) | self-extension |
| `frontend/src/components/library/FlawCard.tsx` | component | CRUD | `LibraryGameCard.tsx` button/asChild pattern | exact |
| `frontend/src/lib/analysisUrl.ts` | utility | transform | itself (`buildAnalysisUrl`) | self-extension |
| `frontend/src/components/library/EvalChart.tsx` | component | event-driven | itself (existing optional props) | self-extension |
| `frontend/src/lib/theme.ts` | config | transform | itself (existing TAC_* constants) | self-extension |
| `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` | test | — | itself (existing hook tests) | exact |

---

## Pattern Assignments

### `frontend/src/hooks/useAnalysisBoard.ts` (hook, state machine)

**Analog:** itself — graft three new methods using the same single-`setState` idiom as the existing methods.

**State extension pattern** — add `pvLine: NodeId[]` to `AnalysisBoardState` (lines 33-39):
```typescript
export interface AnalysisBoardState {
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  mainLine: NodeId[];
  pvLine: NodeId[];      // ADD: nodes grafted by insertPvLine, ordered fork→end
  rootFen: string;
  nextId: number;
}
```

**Return interface extension** — add to `AnalysisBoardReturn` (lines 42-63) following the same pattern as `isOnMainLine`:
```typescript
pvLine: NodeId[];
insertPvLine: (pvSans: string[], forkNodeId: NodeId) => void;
clearPvLine: () => void;
isOnPvLine: (nodeId: NodeId) => boolean;
```

**`insertPvLine` pattern** — MUST do everything in ONE `setState` call (same reason as `loadMainLine`, lines 226-252: `stateRef.current` syncs only after render; sequential `makeMove` calls all read the same stale parent). Copy the `loadMainLine` batch-build loop:
```typescript
// loadMainLine batch pattern (lines 226-252) — replicate for insertPvLine:
const loadMainLine = useCallback((sans: string[], newRootFen: string): void => {
  const newNodes = new Map<NodeId, MoveNode>();
  const newMainLine: NodeId[] = [];
  const chess = new Chess(newRootFen);
  let prevId: NodeId | null = null;
  let id = 0;
  for (const san of sans) {
    const move = chess.move(san);
    if (!move) break;
    const node = buildNode(id, move.san, chess.fen(), move.from, move.to, prevId);
    newNodes.set(id, node);
    newMainLine.push(id);
    prevId = id;
    id++;
  }
  // ... single setState call
}, []);
```

`insertPvLine` replaces `newNodes` with `new Map(prev.nodes)` (graft, not reset), starts `id` at `prev.nextId`, and chains from `forkNodeId` as the first `prevId`. Sets `pvLine` to the new PV ids, leaves `mainLine` unchanged, navigates `currentNodeId` to `forkNodeId` (not the first PV move).

**`clearPvLine` pattern** — functional `setState` updater, same shape as `goBack` (lines 187-194):
```typescript
const goBack = useCallback((): void => {
  setState((prev) => {
    if (prev.currentNodeId === null) return prev;
    const node = prev.nodes.get(prev.currentNodeId);
    if (!node) return prev;
    return { ...prev, currentNodeId: node.parentId };
  });
}, []);
```
`clearPvLine` does: delete pvLine node ids from `new Map(prev.nodes)`, clear `pvLine: []`, set `currentNodeId` to the fork mainLine node (recover by walking parentId up until hitting `mainLine`).

**`isOnPvLine` pattern** — copy `isOnMainLine` (lines 268-270):
```typescript
const isOnMainLine = useCallback((nodeId: NodeId): boolean => {
  return stateRef.current.mainLine.includes(nodeId);
}, []);
// isOnPvLine: replace .mainLine with .pvLine
```

**`makeInitialState` update** — add `pvLine: []` to the returned object (line 113-121):
```typescript
function makeInitialState(rootFen: string): AnalysisBoardState {
  return {
    nodes: new Map<NodeId, MoveNode>(),
    currentNodeId: null,
    mainLine: [],
    rootFen,
    nextId: 0,
  };
}
```

---

### `frontend/src/components/analysis/VariationTree.tsx` (component, transform)

**Analog:** itself — extend `buildVariationChain` and `DesktopTree` to support two nesting levels.

**Props extension** (lines 21-39 — add after `decorations`):
```typescript
export interface VariationTreeProps {
  // ... existing props unchanged ...
  decorations?: Map<NodeId, string>;
  // ADD:
  pvLine?: NodeId[];
  flawMarkerByNodeId?: Map<NodeId, { missedMotif: string | null; allowedMotif: string | null }>;
  onPvChipClick?: (nodeId: NodeId, flaw: { ply: number; orientation: 'missed' | 'allowed' }) => void;
  activePvNodeId?: NodeId | null;
}
```

**`VariationChain` extension** (lines 43-46):
```typescript
interface VariationChain {
  forkParentId: NodeId | null;
  chain: NodeId[];
  level: 0 | 1 | 2;  // 0=main line, 1=pvLine, 2=forked from pvLine
}
```

**`buildVariationChain` extension** (lines 53-70) — add `pvLine` parameter and level detection. Existing walk pattern to copy:
```typescript
function buildVariationChain(
  nodes: Map<NodeId, MoveNode>,
  mainLine: NodeId[],
  currentNodeId: NodeId | null,
): VariationChain {
  if (currentNodeId === null) return { forkParentId: null, chain: [], level: 0 };
  const mainLineSet = new Set(mainLine);
  if (mainLineSet.has(currentNodeId)) return { forkParentId: null, chain: [], level: 0 };

  const reversed: NodeId[] = [];
  let id: NodeId | null = currentNodeId;
  while (id !== null && !mainLineSet.has(id)) {
    reversed.push(id);
    const node = nodes.get(id);
    id = node?.parentId ?? null;
  }
  return { forkParentId: id, chain: reversed.reverse() };
}
```
Extended version: before the walk, check if `currentNodeId` is in `pvLine`; during the walk, if the walker hits a pvLine node before a mainLine node, level is 2.

**`DesktopTree` two-level indent pattern** — the existing single-level block (lines 333-340):
```tsx
{rowIdx === forkRowIdx && varRows.length > 0 && (
  <div className="ml-8">
    {varRows.map((vRow, vIdx) => (
      <Fragment key={vIdx}>{renderDesktopRow(vRow, true)}</Fragment>
    ))}
  </div>
)}
```
Level-2 sub-PV block nests inside level-1 block:
```tsx
// Level-1 PV block:
<div data-testid="variation-pv-section" className="ml-8 border-l-2 border-muted/40 pl-2">
  {pvRows.map(...)}
  {/* Level-2 sub-PV block (only when level===2): */}
  {level === 2 && subPvRows.length > 0 && (
    <div data-testid="variation-subpv-section" className="ml-8 border-l-2 border-muted/30 pl-2">
      {subPvRows.map(...)}
    </div>
  )}
</div>
```

**`renderMoveButton` inline chip extension** (lines 276-301) — inline flaw pill chips are added as siblings to the `<button>` element INSIDE the row `<div>`, NOT inside the `<button>`. Pattern for the chip sibling:
```tsx
const renderMoveButton = (nodeId: NodeId, label: string, isVariation: boolean): ReactNode => {
  const node = nodes.get(nodeId);
  if (!node) return null;
  const isCurrent = nodeId === currentNodeId;
  const decoColor = !isCurrent ? decorations?.get(nodeId) : undefined;
  return (
    <>
      <button
        ref={isCurrent ? activeRef : undefined}
        data-testid={`variation-node-${nodeId}`}
        aria-label={`Move ${label} ${node.san}`}
        aria-current={isCurrent ? 'step' : undefined}
        onClick={() => onNodeClick(nodeId)}
        className={cn(
          'text-sm font-mono px-1 py-0.5 rounded transition-colors hover:bg-accent',
          isCurrent && 'bg-primary text-primary-foreground hover:bg-primary/90',
          // ...
        )}
        style={decoColor ? { color: decoColor } : undefined}
      >
        {node.san}
      </button>
      {/* ADD: flaw pill chip as sibling, only on mainLine nodes with tactic motif */}
      {flawMarkerByNodeId?.get(nodeId) != null && /* render FlawPillChip */}
    </>
  );
};
```

**`MobileTree` double-paren pattern** — extend the existing `(` / `)` paren pattern (lines 174-202) to `((` / `))` for level-2. Existing pattern to copy:
```tsx
trailing:
  isFork && chain.length > 0 ? (
    <span className="text-muted-foreground select-none ml-0.5">(</span>
  ) : undefined,
// closing paren:
trailing: isLast ? (
  <span className="text-muted-foreground select-none">)</span>
) : undefined,
```

---

### Inline flaw-tag pill chip (new component inside `VariationTree.tsx`)

**Analog:** `frontend/src/components/library/TacticMotifChip.tsx`

**Color/border pattern** (lines 180-189) — the new pill chip uses the same TAC_MISSED / TAC_ALLOWED theme constants and the same `border` derivation pattern:
```typescript
const color =
  orientation === 'missed' ? TAC_MISSED : TAC_ALLOWED;
const bg =
  orientation === 'missed' ? TAC_MISSED_BG : TAC_ALLOWED_BG;
// TAC_MISSED_BORDER must be added to theme.ts first (see theme.ts section below):
const border = orientation === 'missed' ? TAC_MISSED_BORDER : TAC_ALLOWED_BORDER;
```

**`ACTIVE_FILTER_RING_CLASS` ring pattern** (lines 198-199 of TacticMotifChip):
```tsx
<span
  className={cn(
    'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold',
    isActive && ACTIVE_FILTER_RING_CLASS,
  )}
  style={{ color, backgroundColor: bg, borderColor: border }}
  role="button"
  tabIndex={0}
  aria-label={ariaLabel}
  data-testid={testId}
  onClick={...}
>
  {label}
</span>
```

The new `FlawPillChip` for the move list is simpler (no hover cycle, no filter store subscription, no count). It renders "Missed" or "Allowed" label, triggers `onPvChipClick`, and shows a spinner or error state when the PV fetch is loading/errored.

---

### `frontend/src/components/analysis/TacticModeOverlay.tsx` (component, contextual activation)

No edits to the component itself. The wiring changes are in `Analysis.tsx`.

**Existing activation block in `Analysis.tsx`** (lines 437-448 — the pattern to replicate for contextual path):
```tsx
{isTacticMode && tacticData != null && (
  <TacticModeOverlay
    data={tacticData}
    resolvedOrientation={resolvedOrientation}
    currentPly={tacticPly}
    onStoredLine={onMainLine}
    onOrientationChange={handleOrientationChange}
    onMoveClick={(ply) => {
      const nodeId = mainLine[ply - 1];
      if (nodeId !== undefined) goToNode(nodeId);
    }}
  />
)}
```
Contextual path replicates this block with `contextualTacticData`, `activePvFlaw.orientation` as `resolvedOrientation`, `isOnPvLine(currentNodeId)` as `onStoredLine`, and `pvLine[ply - 1]` as the `onMoveClick` navigation target.

**Two unconditional `useTacticLines` calls pattern** (line 144 — existing call):
```typescript
// EXISTING (line 144):
const { data: tacticData } = useTacticLines(gameId, flawPly, isTacticMode);
// ADD second call (unconditional — React hooks rules):
const { data: contextualTacticData } = useTacticLines(
  gameId,
  activePvFlaw?.ply ?? null,
  activePvFlaw != null,
);
```

---

### `frontend/src/pages/Analysis.tsx` (page, request-response)

**Analog:** itself — all edit seams are extensions of existing patterns.

**URL param NaN-guard pattern** (lines 97-101 — copy for `ply` param):
```typescript
const gameIdRaw = searchParams.get('game_id');
const flawPlyRaw = searchParams.get('flaw_ply');
const gameId: number | null =
  gameIdRaw != null && !Number.isNaN(Number(gameIdRaw)) ? Number(gameIdRaw) : null;
const flawPly: number | null =
  flawPlyRaw != null && !Number.isNaN(Number(flawPlyRaw)) ? Number(flawPlyRaw) : null;
const isTacticMode = gameId != null && flawPly != null;
// ADD for game mode:
const plyRaw = searchParams.get('ply');
const initialPly: number | null =
  plyRaw != null && !Number.isNaN(Number(plyRaw)) ? Number(plyRaw) : null;
const isGameMode = gameId != null && initialPly != null;
```

**`noUncheckedIndexedAccess` guard pattern** (line 445 — copy at every new `mainLine[i]` / `pvLine[i]` access):
```typescript
onMoveClick={(ply) => {
  const nodeId = mainLine[ply - 1];
  if (nodeId !== undefined) goToNode(nodeId);
}}
```

**`useEffect` for seeding board** (lines 183-198 — the D-5 re-seed effect to copy):
```typescript
useEffect(() => {
  if (!isTacticMode || positionFen == null) return;
  const moves = /* ... */;
  loadMainLine(moves, positionFen);
  goToRoot();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [positionFen, resolvedOrientation, isTacticMode]);
```
Game mode seeds with `gameData.moves` in a similar effect:
```typescript
useEffect(() => {
  if (!isGameMode || gameData?.moves == null) return;
  loadMainLine(gameData.moves, STARTING_FEN);
  // noUncheckedIndexedAccess guard:
  const nodeId = mainLine[initialPly ?? 0];
  if (nodeId !== undefined) goToNode(nodeId);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [gameData, isGameMode]);
```
Note from RESEARCH.md: `loadMainLine` is synchronous state update (batched) and `mainLine` in scope at the `goToNode` call reflects the PREVIOUS state. Use a separate `useEffect` watching `mainLine.length` to navigate to `initialPly` after the tree is seeded.

**`handleReset` branch extension** (lines 356-358):
```typescript
const handleReset = isTacticMode
  ? () => goToRoot()
  : () => loadMainLine([], rootFen);
// ADD game mode branch:
const handleReset = isTacticMode
  ? () => goToRoot()
  : isGameMode
    ? () => {
        clearPvLine();
        setActivePvFlaw(null);
        const nodeId = mainLine[initialPly ?? 0];
        if (nodeId !== undefined) goToNode(nodeId);
      }
    : () => loadMainLine([], rootFen);
```

**`BoardControls` relocation** — move from board column (lines 409-431) to bottom of right column (after `VariationTree`, lines 477-484). Props are unchanged; just move the JSX block.

---

### `frontend/src/components/results/LibraryGameCard.tsx` (component, CRUD)

**Analog:** itself — `renderDesktopExploreButton()` (lines 896-963).

**`Button asChild` + `Link` pattern** (lines 903-919 — the exact idiom to replicate for the new unified Analyze button):
```tsx
<Button asChild variant="brand-outline" className="w-full">
  <Link
    to={
      '/analysis?game_id=' +
      game.game_id +
      '&flaw_ply=' +
      hoverPly +
      '&orientation=' +
      exploreOri
    }
    data-testid="game-card-btn-explore"
    aria-label="Explore tactic line for selected flaw"
  >
    <Search className="h-4 w-4 mr-1" />
    Explore
  </Link>
</Button>
```

**New unified Analyze button** replaces both the Explore and Analyze-position buttons in BOTH `renderDesktopExploreButton()` and the mobile `<div className="md:hidden flex gap-2">` block (CLAUDE.md mobile-parity rule). Uses `buildGameAnalysisUrl` from `@/lib/analysisUrl`:
```tsx
{game.analysis_state === 'analyzed' && (
  <Button asChild variant="brand-outline" className="w-full">
    <Link
      to={buildGameAnalysisUrl(game.game_id, hoverPly ?? lastEvalPly ?? 0)}
      data-testid="btn-library-game-analyze"
      aria-label="Analyze game"
    >
      <Search className="h-4 w-4 mr-1" />
      Analyze
    </Link>
  </Button>
)}
```

**`isAnalyzed` gate pattern** (line 232):
```typescript
const isAnalyzed = game.analysis_state === 'analyzed';
```

**`hoverPly` / `lastEvalPly` availability** (lines 218, 249-257): both are already declared and in scope at the button render site. No new state needed.

---

### `frontend/src/components/library/FlawCard.tsx` (component, CRUD)

**Analog:** `LibraryGameCard.tsx` button/asChild pattern above.

**New `buttonRow` replacement** (replaces lines 257-293 per RESEARCH.md):
```tsx
const buttonRow = (
  <div className="flex gap-2">
    <Button asChild variant="brand-outline" className="flex-1">
      <Link
        to={buildGameAnalysisUrl(flaw.game_id, flaw.ply)}
        data-testid="btn-flaw-analyze"
        aria-label="Analyze game"
      >
        <Search className="h-4 w-4 mr-1" />
        Analyze
      </Link>
    </Button>
  </div>
);
```

**Imports to delete** per RESEARCH.md lines 420-427: `Swords`, `Loader2`, `X`, `Dialog`, `DialogContent`, `DialogTitle`, `Drawer`, `DrawerContent`, `DrawerHeader`, `DrawerTitle`, `DrawerClose`, `LoadError`, `LibraryGameCard`, `useLibraryGame`, `useFlawFilterStore`, `MOBILE_BREAKPOINT_PX`, `useIsMobile`.

**Import to add:** `buildGameAnalysisUrl` from `@/lib/analysisUrl`.

---

### `frontend/src/lib/analysisUrl.ts` (utility, transform)

**Analog:** itself — `buildAnalysisUrl` (lines 19-21).

**Existing function pattern to replicate:**
```typescript
const ANALYSIS_PATH = '/analysis';
const FEN_PARAM = 'fen';

export function buildAnalysisUrl(fen: string): string {
  return `${ANALYSIS_PATH}?${FEN_PARAM}=${encodeURIComponent(fen)}`;
}
```

**New function** (numeric params — no encoding needed):
```typescript
const GAME_ID_PARAM = 'game_id';
const PLY_PARAM = 'ply';

export function buildGameAnalysisUrl(gameId: number, ply: number): string {
  return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}&${PLY_PARAM}=${ply}`;
}
```

---

### `frontend/src/components/library/EvalChart.tsx` (component, event-driven)

**Analog:** itself — existing optional props with defaults.

The existing `heightClass?: string` (line 67 per RESEARCH.md) demonstrates the optional-prop-with-default pattern used here. Add two new optional props:

```typescript
// ADD to EvalChart props:
sliderTestId?: string;    // defaults to `eval-slider-${gameId}`
sliderDisabled?: boolean; // defaults to false
```

Wiring:
- `sliderTestId` replaces the hardcoded `data-testid={eval-slider-${gameId}}` at line 1001.
- `sliderDisabled` gates `disabled` attribute + `opacity-40 pointer-events-none` on the `<input>` element at line 1001. Title attribute `"Return to main game line to scrub"` added conditionally when `sliderDisabled`.

Callers in `LibraryGameCard.tsx` pass neither prop — zero change (defaults preserve existing behavior).

---

### `frontend/src/lib/theme.ts` (config)

**Analog:** itself — existing `TAC_ALLOWED_BORDER` (line 158).

**Missing constant to add** after `TAC_MISSED_BG` (line 152):
```typescript
// EXISTING (line 151-152):
export const TAC_MISSED = 'oklch(0.70 0.15 258)';
export const TAC_MISSED_BG = 'oklch(0.70 0.15 258 / 0.15)';
// ADD (line 153):
export const TAC_MISSED_BORDER = 'oklch(0.70 0.15 258 / 0.30)';
// EXISTING (line 156-158):
export const TAC_ALLOWED = 'oklch(0.70 0.15 25)';
export const TAC_ALLOWED_BG = 'oklch(0.70 0.15 25 / 0.15)';
export const TAC_ALLOWED_BORDER = 'oklch(0.70 0.15 25 / 0.30)';
```

This is a prerequisite task — `VariationTree.tsx` imports `TAC_MISSED_BORDER` from `@/lib/theme`.

**Blunder/mistake icon colors** (already present — planner picks icon glyphs from lucide):
```typescript
export const SEV_BLUNDER = 'oklch(0.58 0.19 25)';  // line 31 — red
export const SEV_MISTAKE = 'oklch(0.70 0.16 55)';  // line 32 — amber
```
`BlunderIcon` / `MistakeIcon` already exist in `frontend/src/components/icons/SeverityGlyphIcon.tsx` and are already imported in `TacticModeOverlay.tsx` (line 21). Import them directly into `VariationTree.tsx` for D-02 non-tactic markers.

---

## Tests

### `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` (test, hook)

**Analog:** itself (lines 1-233).

**Test harness idiom** (lines 1-15):
```typescript
// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAnalysisBoard } from '../useAnalysisBoard';
import type { MoveNode, NodeId, AnalysisBoardState } from '../useAnalysisBoard';
```

**Invariant test structure** (lines 42-73 — mid-line fork test):
```typescript
it('invariant description', () => {
  const { result } = renderHook(() => useAnalysisBoard(ROOT_FEN));
  act(() => { result.current.loadMainLine(MAIN_LINE_SANS, ROOT_FEN); });
  // ... act blocks for each state transition
  expect(result.current.pvLine).toHaveLength(pvSans.length);
  expect(result.current.isOnPvLine(result.current.pvLine[0]!)).toBe(true);
  expect(result.current.isOnMainLine(result.current.pvLine[0]!)).toBe(false);
});
```

**New tests to add** for Phase 140 invariants (from RESEARCH.md Validation Architecture):
1. `insertPvLine(pvSans, forkNodeId)` — `pvLine.length === pvSans.length`, all pvLine nodes chain back to `forkNodeId`, `mainLine` unchanged, `isOnPvLine(pvLine[0]!)` true, `isOnMainLine(pvLine[0]!)` false.
2. `clearPvLine()` — `pvLine.length === 0`, no pvLine ids remain in `nodes`, `currentNodeId` back on mainLine.
3. User forks within PV (makeMove while on pvLine node) — new node NOT in `pvLine`, `buildVariationChain` returns `level: 2`.

### `frontend/src/lib/analysisUrl.test.ts` (test, utility)

**Analog:** itself (lines 1-31).

**Test structure to copy** for `buildGameAnalysisUrl`:
```typescript
import { describe, it, expect } from 'vitest';
import { buildGameAnalysisUrl } from './analysisUrl';

describe('buildGameAnalysisUrl', () => {
  it('returns /analysis?game_id={id}&ply={ply}', () => {
    const result = buildGameAnalysisUrl(42, 10);
    expect(result).toBe('/analysis?game_id=42&ply=10');
  });
  it('starts with /analysis?game_id=', () => {
    expect(buildGameAnalysisUrl(1, 0).startsWith('/analysis?game_id=')).toBe(true);
  });
});
```

---

## Shared Patterns

### `Button asChild + Link`
**Source:** `frontend/src/components/results/LibraryGameCard.tsx` lines 903-919
**Apply to:** `LibraryGameCard.tsx` (new Analyze button), `FlawCard.tsx` (new Analyze button)
```tsx
<Button asChild variant="brand-outline" className="...">
  <Link to={url} data-testid="..." aria-label="...">
    <Search className="h-4 w-4 mr-1" />
    Analyze
  </Link>
</Button>
```

### `noUncheckedIndexedAccess` guard
**Source:** `frontend/src/pages/Analysis.tsx` line 445
**Apply to:** Every new `mainLine[i]` and `pvLine[i]` access in `Analysis.tsx`, `VariationTree.tsx`, `useAnalysisBoard.ts`
```typescript
const nodeId = mainLine[ply - 1];
if (nodeId !== undefined) goToNode(nodeId);
```

### Single-`setState` batch update (PV insert)
**Source:** `frontend/src/hooks/useAnalysisBoard.ts` lines 226-252 (`loadMainLine`)
**Apply to:** `insertPvLine` in `useAnalysisBoard.ts`
Critical: NEVER call `makeMove` in a loop — it reads stale `stateRef.current`. All PV node creation must happen in a single `setState((prev) => { ... })` call.

### Dual-DOM responsive split
**Source:** `frontend/src/components/analysis/VariationTree.tsx` lines 358-367
**Apply to:** Any new mobile/desktop split in `VariationTree.tsx`
```tsx
<div className="sm:hidden"><MobileTree ... /></div>
<div className="hidden sm:block"><DesktopTree ... /></div>
```

### `isError` ternary branch (CLAUDE.md rule)
**Apply to:** On-demand PV fetch in `VariationTree.tsx` (pill chip loading/error state)
Error branch copy: `"Tactic line not available for this flaw."` (exact string per CONTEXT.md).

---

## No Analog Found

None — all files have direct analogs or are self-extensions of existing files.

---

## Metadata

**Analog search scope:** `frontend/src/hooks/`, `frontend/src/components/analysis/`, `frontend/src/components/library/`, `frontend/src/components/results/`, `frontend/src/pages/`, `frontend/src/lib/`
**Files scanned:** 14 (per RESEARCH.md sources table, all read directly)
**Pattern extraction date:** 2026-06-27

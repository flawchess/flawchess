# Phase 140: Full-Game Analysis Board — Research

**Researched:** 2026-06-27
**Domain:** Frontend React/TypeScript — chess board state, variation trees, URL routing, component wiring
**Confidence:** HIGH (all findings from direct codebase read; no training assumptions)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Expanded PV state is ephemeral in-memory. URL carries only `game_id + ply`. Refresh returns to collapsed main line. The `?fen=` free-play variation URL remains unchanged.
- D-02: Two distinct move-list marker types — tactic flaws (`missed_tactic_motif` / `allowed_tactic_motif` set on `FlawMarker`) render inline Missed/Allowed pill chips; non-tactic blunder/mistake render a distinct blunder-vs-mistake icon marker.
- D-03: Inaccuracies get NO marker.
- D-04: Blunder/mistake icon has no special click behavior — row click navigates board normally.
- D-05: Main-line move click syncs board + move-list highlight + eval-chart slider. On sideline the slider parks at fork ply, disabled/dimmed (`opacity-40`, tooltip "Return to main game line to scrub").
- D-06: Analyze button shown on analyzed games only (`analysis_state === 'analyzed'`). Icon = `Search` (lucide). Replaces Explore + Analyze position pair. Opens `/analysis?game_id=X&ply=Y`.
- D-07: Un-analyzed games keep the existing `Cpu`-icon "Analyze" button in `NoAnalysisState.tsx` unchanged.
- D-08: D-06/D-07 supersede UI-SPEC lines about "always enabled", `Activity` icon, and "navigates to free-play mode" for un-analyzed games. UI-SPEC testids and copy still apply for the page-opening button.
- D-09: FlawCard `Game` modal path deleted entirely — Dialog/Drawer + inline `LibraryGameCard` + `useLibraryGame` + related imports all removed.

### Claude's Discretion
- On-demand PV fetch UX: exact loading/error affordance (spinner-on-chip vs other). Requirement: loading state shown during `tactic-lines` fetch, error/empty case follows CLAUDE.md `isError` pattern: "Tactic line not available for this flaw."
- Blunder vs mistake icon glyph/color: specific icons/colors the planner's call, drawn from `theme.ts` semantic colors. Two visually distinct treatments.

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope. `?fen=` free-play and backward-compat `?game_id&flaw_ply` tactic-only URL are explicitly unchanged, not deferred.
</user_constraints>

---

## Summary

Phase 140 refines the existing v1.29 `/analysis` board. The three hardest parts are: (1) two-level variation nesting in `useAnalysisBoard` + `VariationTree`, (2) contextual `TacticModeOverlay` wiring, and (3) the new game-by-id fetch on the `/analysis` route. The research below maps every real symbol, signature, and edit seam from a direct codebase read.

All data for the new game mode is already available via `useLibraryGame` / `GameFlawCard` (the same hook/type `LibraryGameCard` uses). No new backend endpoint is needed. The biggest structural change is adding `pvLine: NodeId[]` state to `useAnalysisBoard` and an `insertPvLine` method — the existing parentId-based tree supports arbitrary nesting, but the rendering and "which level am I on" logic requires this explicit tracker.

---

## Hardest Part 1: Two-Level Variation Nesting

### Current state

**`frontend/src/hooks/useAnalysisBoard.ts`**

Data structure (lines 23-38):
```typescript
export interface MoveNode {
  id: NodeId;          // auto-incrementing integer
  san: string;
  fen: string;         // O(1) navigation — no replay needed
  from: string;
  to: string;
  parentId: NodeId | null;
}
export interface AnalysisBoardState {
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  mainLine: NodeId[];   // IDs seeded by loadMainLine, in order
  rootFen: string;
  nextId: number;
}
```

Key methods (return type `AnalysisBoardReturn`, lines 42-63):
- `loadMainLine(sans: string[], newRootFen: string): void` — resets the ENTIRE tree, builds a fresh `nodes` map + `mainLine` array. Called once for game load.
- `makeMove(from: string, to: string): boolean` — grafts a new child node under `currentNodeId`. Reads FEN from `stateRef.current` (safe for single-call use; NOT safe for sequential batch calls because `stateRef` syncs only after render).
- `goToNode(id: NodeId): void` — O(1) jump to any node.
- `goToRoot(): void` — sets `currentNodeId = null` (lands at `rootFen`).
- `isOnMainLine(nodeId: NodeId): boolean` — checks `mainLine.includes(nodeId)`.

**`frontend/src/components/analysis/VariationTree.tsx`**

`buildVariationChain` (lines 53-70): walks from `currentNodeId` backwards via `parentId` until hitting a `mainLine` node. Returns `{ forkParentId, chain }`.

`DesktopTree` (lines 231-344): renders `mainRows` then, at the fork row index, inserts a `<div className="ml-8">` with `varRows`. Single indent level only.

`MobileTree` (lines 141-227): inserts variation items between fork node and rest of main line, using `(` / `)` parentheses. Single level only.

Props (`VariationTreeProps`, lines 21-39):
```typescript
interface VariationTreeProps {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  currentNodeId: NodeId | null;
  rootPly?: number;
  onNodeClick: (nodeId: NodeId) => void;
  heightClass?: string;
  decorations?: Map<NodeId, string>;  // per-node text color for tactic highlights
}
```

### What must change

**`useAnalysisBoard.ts` — add `pvLine` state and methods:**

The tree's `Map<NodeId, MoveNode>` with `parentId` links already supports arbitrary nesting. What's missing is a way to distinguish level-1 (PV sideline nodes) from level-2 (user forks within PV). Add to `AnalysisBoardState`:

```typescript
pvLine: NodeId[];  // nodes grafted from a tactic chip click, ordered
```

New method `insertPvLine(pvSans: string[], forkNodeId: NodeId): void` — does everything in ONE `setState` call (critical: `makeMove` cannot be called in a loop because `stateRef.current` syncs only after render, so sequential `makeMove` calls all read the same stale parent). The method replays `pvSans` from `nodes.get(forkNodeId).fen`, creates child nodes under `forkNodeId`, stores them in a new `pvLine` array, adds them to `nodes`, and navigates `currentNodeId` to `forkNodeId` (the fork position, not the first PV move — per "no auto-expand").

New method `clearPvLine(): void` — removes PV-only nodes from `nodes`, clears `pvLine`, returns to `mainLine` at the fork point.

New method `isOnPvLine(nodeId: NodeId): boolean` — checks `pvLine.includes(nodeId)`.

Updated `AnalysisBoardReturn` interface adds these three methods plus `pvLine: NodeId[]`.

**`VariationTree.tsx` — extend to two levels:**

Add `pvLine?: NodeId[]` prop.

Extend `buildVariationChain` to return level information:

```typescript
interface VariationChain {
  forkParentId: NodeId | null;
  chain: NodeId[];
  level: 0 | 1 | 2;  // 0 = on main line; 1 = in pvLine; 2 = forked from pvLine
}
```

Logic: walk from `currentNodeId` backwards. If the walk hits a `pvLine` node before hitting a `mainLine` node, the fork is level-2 (forked from PV). If it hits `mainLine` directly, it's level-1. If `currentNodeId` is in `pvLine`, level is 1. If `currentNodeId` is in `mainLine`, level is 0.

`DesktopTree` rendering extends from one `<div className="ml-8">` to potentially two nested indented blocks:
- Level-1 PV block: `<div data-testid="variation-pv-section" className="ml-8 border-l-2 border-muted/40 pl-2">` 
- Level-2 sub-PV block (nested inside): `<div data-testid="variation-subpv-section" className="ml-16 border-l-2 border-muted/30 pl-2">`

The inline flaw tag chips are added inside `renderMoveButton` as siblings to the SAN button, NOT inside the `<button>` element. They are rendered for `mainLine` nodes whose `flaw_markers` have a tactic motif. This requires passing `flawMarkers` (or a Map keyed by nodeId) to `VariationTree`.

**New prop needed on VariationTree:**
```typescript
flawMarkerByNodeId?: Map<NodeId, { missedMotif: string | null; allowedMotif: string | null }>;
onPvChipClick?: (nodeId: NodeId, flaw: { ply: number; orientation: 'missed' | 'allowed' }) => void;
activePvNodeId?: NodeId | null;  // the node whose chip is currently expanded
```

`MobileTree` extends to double-paren for level-2: `((N. sub1 sub2 ...))`. No inline chips on mobile.

### Risk: `buildVariationChain` and off-tree navigation

`buildVariationChain` is called with the LIVE `currentNodeId`. When the user navigates back from a PV into main-line territory, `currentNodeId` is a `mainLine` node and level returns to 0 — the PV block collapses. This is correct behavior. No special case needed; the tree structure handles it.

### Risk: `noUncheckedIndexedAccess` on `mainLine[ply]`

When the `EvalChart.onPlyChange` callback calls `goToNode(mainLine[ply])`, `mainLine[ply]` returns `NodeId | undefined`. The callback must guard:

```typescript
const nodeId = mainLine[ply];
if (nodeId !== undefined) goToNode(nodeId);
```

This pattern must appear in `Analysis.tsx` — the planner must NOT write `goToNode(mainLine[ply]!)` unless provably in-bounds.

---

## Hardest Part 2: Contextual TacticModeOverlay

### Current state

**`frontend/src/components/analysis/TacticModeOverlay.tsx`**

Props (lines 142-165):
```typescript
interface TacticModeOverlayProps {
  data: TacticLinesResponse;
  resolvedOrientation: TacticDepthOrientation;
  currentPly: number;          // 0 = root, 1+ = PV steps
  onStoredLine: boolean;        // true when on the seeded mainLine
  onOrientationChange: (next: TacticDepthOrientation) => void;
  onMoveClick: (ply: number) => void;
}
```

Exports:
- `buildRootArrows(positionFen, bestMoveUci, flawMoveSan, missedDepthLabel, allowedDepthLabel): BoardArrow[]`
- `buildPvArrow(lastMove, displayDepth, isPayoff, orientation, isFlawLeadIn): BoardArrow[]`
- `isBlackToMove(fen: string): boolean`

**`frontend/src/pages/Analysis.tsx`** (lines 95-144, 437-448)

Current activation:
```typescript
const isTacticMode = gameId != null && flawPly != null;
// ...
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

`tacticData` is fetched via `useTacticLines(gameId, flawPly, isTacticMode)` (line 144).

`onMainLine = currentNodeId === null || isOnMainLine(currentNodeId)` (line 223).

`tacticPly = currentNodeId === null ? 0 : mainLine.indexOf(currentNodeId) + 1` (line 211).

### What must change

Add state in `Analysis.tsx`:
```typescript
const [activePvFlaw, setActivePvFlaw] = useState<{
  ply: number;
  orientation: 'missed' | 'allowed';
} | null>(null);
```

Add a second `useTacticLines` call for the contextual path (React hooks rules — both calls must be unconditional):
```typescript
const { data: contextualTacticData } = useTacticLines(
  gameId,
  activePvFlaw?.ply ?? null,
  activePvFlaw != null,
);
```

Derive `isTacticModeContextual = activePvFlaw != null && contextualTacticData != null`.

The overlay is shown for EITHER activation:
```typescript
{(isTacticMode && tacticData != null) && <TacticModeOverlay data={tacticData} ... />}
{isTacticModeContextual && contextualTacticData != null && !isTacticMode && (
  <TacticModeOverlay data={contextualTacticData} ... />
)}
```

Or more cleanly, resolve a single `activeOverlayData` and `activeOverlayOrientation` that merges both paths.

For the contextual path:
- `resolvedOrientation`: from `activePvFlaw.orientation`
- `onStoredLine`: `isOnPvLine(currentNodeId)` (new hook method)
- `currentPly`: `currentNodeId === null ? 0 : pvLine.indexOf(currentNodeId) + 1`
- `onMoveClick`: navigate to the PV node at `pvLine[ply - 1]`

The board arrows for the contextual path follow the same `buildRootArrows` / `buildPvArrow` logic — no changes to these exported functions.

**Show/hide logic:**
- Overlay HIDDEN when: user navigates back to main line (`activePvFlaw` cleared by `clearPvLine` call), or user clicks the active chip again (toggle off).
- Overlay SHOWN: while `activePvFlaw != null` (a chip has been clicked and the PV is inserted).

The `Analysis.tsx` `handleReset` in game mode (not tactic mode) should also call `clearPvLine()` and `setActivePvFlaw(null)`.

---

## Hardest Part 3: Game-by-id Fetch on /analysis Route

### Current state

**`frontend/src/hooks/useLibrary.ts` — `useLibraryGame`** (lines 193-218):
```typescript
export function useLibraryGame(
  gameId: number | null,
  flawFilter?: FlawFilterState,
): ReturnType<typeof useQuery<GameFlawCard>>
```
Query key: `['library-game', gameId, severity, tacticFamily, tacticOrientation, depthParam]`
Returns: `GameFlawCard` (full shape in `frontend/src/types/library.ts` lines 58-92)

**`GameFlawCard` fields needed for Phase 140:**
```typescript
game_id: number
moves: string[] | null        // SAN array, moves[i] = move at ply i
eval_series: EvalPoint[] | null
flaw_markers: FlawMarker[] | null
phase_transitions: PhaseTransitions | null
analysis_state: AnalysisState  // 'analyzed' | 'no_engine_analysis'
user_color: string
```

**`FlawMarker`** (lines 111-129):
```typescript
interface FlawMarker {
  ply: number;
  severity: FlawSeverity;   // 'inaccuracy' | 'mistake' | 'blunder'
  tags: FlawTag[];
  is_user: boolean;
  move_san: string | null;
  allowed_tactic_motif: string | null;
  missed_tactic_motif: string | null;
  // ...depth/confidence fields
}
```

`useTacticLines(gameId, ply, enabled)` (lines 228-240): existing hook, keyed `['tactic-lines', gameId, ply]`. Returns `TacticLinesResponse`. Already called in `Analysis.tsx` for tactic mode.

**`hoverPly` / `lastEvalPly` in `LibraryGameCard.tsx`:**
- `hoverPly: number | null` — state set by `EvalChart.onHoverPlyChange`, represents the slider's active ply.
- `lastEvalPly: number | null` — derived at lines 249-257 as the last `EvalPoint` with `es != null` from `eval_series`.
- The Analyze button URL (D-06): `/analysis?game_id={game.game_id}&ply={hoverPly ?? lastEvalPly ?? 0}`.

### What must change in Analysis.tsx

Parse new URL params:
```typescript
const plyRaw = searchParams.get('ply');
const initialPly: number | null =
  plyRaw != null && !Number.isNaN(Number(plyRaw)) ? Number(plyRaw) : null;
const isGameMode = gameId != null && initialPly != null;
```

Backward-compat tactic mode stays (`isTacticMode = gameId != null && flawPly != null`).

Fetch game data (unconditional hook call, enabled when `isGameMode`):
```typescript
const { data: gameData, isError: gameError } = useLibraryGame(
  isGameMode ? gameId : null,
);
```

On `gameData` arrival, seed the board with a `useEffect`:
```typescript
useEffect(() => {
  if (!isGameMode || gameData?.moves == null) return;
  loadMainLine(gameData.moves, STARTING_FEN);
  // Navigate to initialPly
  // mainLine[initialPly] is the node after initialPly moves — noUncheckedIndexedAccess guard:
  const nodeId = mainLine[initialPly ?? 0];
  if (nodeId !== undefined) goToNode(nodeId);
}, [gameData, isGameMode]);
```

Note: `mainLine` is set by `loadMainLine` in the same effect — the planner must sequence correctly. The `loadMainLine` call is synchronous state update (batched); the `goToNode` should be called in a subsequent effect or after a setState callback. The safest pattern is a separate `useEffect` that watches `mainLine.length > 0` and navigates.

**D-4 compliance:** No new backend endpoint. `useLibraryGame` calls `GET /api/library/games/{gameId}` (existing endpoint). Confirmed: `flawFilter` passed as `undefined` returns the full game with all tactic slots (the "all-inclusive default" per the code comment at line 194).

---

## Smaller Seams

### EvalChart.tsx — Props Analysis

File: `frontend/src/components/library/EvalChart.tsx`

Existing props (lines 67-127) — all needed for analysis page are present:
- `initialPly?: number | null` — slider opens here (the `ply` URL param)
- `onHoverPlyChange?: (ply: number | null) => void` — callback to sync board
- `heightClass?: string` — pass `"h-[120px]"` (UI-SPEC)

**Missing for analysis page:**
- `analysis-eval-chart` testid: current outer `data-testid` is `eval-chart-${gameId}` (line 725). UI-SPEC says "pass via `gameId` prop or wrap". The wrap approach works for the outer div but NOT for the slider testid.
- `analysis-eval-chart-slider` testid: current slider testid is `eval-slider-${gameId}` (line 1001). The UI-SPEC requires a separate testid for the analysis-page slider.

**Resolution needed by planner:** Add an optional `sliderTestId?: string` prop to `EvalChart`, defaulting to `eval-slider-${gameId}`. This is the minimal backward-compatible change. The outer testid can be handled by wrapping `<EvalChart>` with `<div data-testid="analysis-eval-chart">` in `Analysis.tsx`. The UI-SPEC says "reused without modification" — adding two optional props with defaults satisfies this intent without behavioral change.

**Sideline parking:** The slider's `disabled` state + `opacity-40` + `pointer-events-none` + tooltip `"Return to main game line to scrub"` need to be wired from `Analysis.tsx` via a `disabled` prop on the slider. Currently `EvalChart` has no `disabled` prop — the planner must add `sliderDisabled?: boolean` to EvalChart props, which gates the `disabled` HTML attribute and the opacity class on the `<input>`. The title attribute for the tooltip can be added conditionally. This is another minimal prop addition.

**When the slider is disabled:** The EvalChart's `onHoverPlyChange` should NOT drive `goToNode` — `Analysis.tsx` should only wire `goToNode` on the `onHoverPlyChange` callback when the user is on the main line.

### LibraryGameCard.tsx — Button Row Change

File: `frontend/src/components/results/LibraryGameCard.tsx`

Current button row (desktop: `renderDesktopExploreButton()` at lines 896-963; mobile duplicate at lines 1027-1092):
- `Explore` button: `data-testid="game-card-btn-explore"`, `Search` icon, `brand-outline`, conditional on `isTaggedFlaw`, links to `/analysis?game_id=X&flaw_ply=Y&orientation=Z`
- `Analyze position` button: `data-testid="game-card-btn-analyze-position"`, `Activity` icon, `brand-outline`, links to `/analysis?fen=FEN`

**What the planner replaces both with:**
- Single `Analyze` button, `data-testid="btn-library-game-analyze"`, `Search` icon, `brand-outline`, `aria-label="Analyze game"` 
- Navigation: `/analysis?game_id={game.game_id}&ply={hoverPly ?? lastEvalPly ?? 0}` — use `buildGameAnalysisUrl` (new function in `analysisUrl.ts`)
- Shown only when `game.analysis_state === 'analyzed'` (D-06)
- Rendered as `<Button asChild ...><Link to={...} ...>` pattern (same as existing `Explore`)
- Size: `default` (h-8) — same as current buttons

**`hoverPly` at button render time:** `hoverPly` is the `useState<number | null>` declared at line 218. `lastEvalPly` is derived at lines 249-257 from `game.eval_series`. Both are already in scope for the button render. No new state needed.

**Import changes:** `Activity` icon import (line 4) can be removed after this change. `Search` icon stays. `buildGameAnalysisUrl` needs a new import from `@/lib/analysisUrl`.

**BOTH desktop and mobile button rows must be replaced** — the desktop version is inside `renderDesktopExploreButton()` called at line 1188; the mobile version is the `<div className="md:hidden flex gap-2">` block at lines 1027-1092. Replace both independently (CLAUDE.md mobile-parity rule).

### FlawCard.tsx — Unified Analyze + Modal Deletion

File: `frontend/src/components/library/FlawCard.tsx`

**Items to delete entirely:**

State:
- `open` state (line 141): `const [open, setOpen] = useState(false);`
- `isMobile` via `useIsMobile()` (line 142 — look for `const isMobile = useIsMobile()`)

Hook call:
- `const { data, isLoading, isError } = useLibraryGame(open ? flaw.game_id : null, flawFilter);` (line 163)
- `const [flawFilter] = useFlawFilterStore();` (line 162) — only used for `useLibraryGame`; check if it's also used elsewhere in the file before deleting (it IS used in the `ori` derivation — no, `ori` is derived from `flaw` and `tacticOrientation` prop, not from `flawFilter`; so `flawFilter` and `useFlawFilterStore` import can be removed)

JSX blocks:
- `gameBody` (lines 477-493)
- `gameCloseLabel`, `gameView` (lines 495-538)
- `{gameView}` reference at line 591

`buttonRow` const (lines 257-293): replace `Explore + Game` with single `Analyze` button:
```typescript
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

**Imports to remove:**
- `Swords`, `Loader2`, `X` from `lucide-react` (line 11-12)
- `Dialog`, `DialogContent`, `DialogTitle` from `@/components/ui/dialog` (line 23)
- `Drawer`, `DrawerContent`, `DrawerHeader`, `DrawerTitle`, `DrawerClose` from `@/components/ui/drawer` (lines 26-30)
- `LoadError` from `@/components/ui/load-error` (line 31)
- `LibraryGameCard` from `@/components/results/LibraryGameCard` (line 35)
- `useLibraryGame` from `@/hooks/useLibrary` (line 43)
- `useFlawFilterStore` from `@/hooks/useFlawFilterStore` (line 44)
- `MOBILE_BREAKPOINT_PX` constant and `useIsMobile` hook (lines 59-78)

**Imports to add:**
- `buildGameAnalysisUrl` from `@/lib/analysisUrl`

**The `isTagged` check and `ori` derivation** (lines 144-157) can be removed since neither feeds into the new single `Analyze` button.

### NoAnalysisState.tsx — Confirmed Unchanged (D-07)

File: `frontend/src/components/library/NoAnalysisState.tsx`

Existing button (lines 88-107):
```typescript
<Button
  variant="brand-outline"
  size="sm"
  data-testid={`btn-analyze-game-${gameId}`}
  aria-label="Analyze this game with Stockfish"
  onClick={...}
>
  <Cpu className="h-4 w-4 shrink-0 mr-1.5" aria-hidden="true" />
  Analyze
</Button>
```

**Zero changes** — this is the un-analyzed game path (D-07). The Phase 140 `Analyze` button (D-06) is shown ONLY on analyzed games; unanalyzed games show this `NoAnalysisState` button. The two never coexist on the same card.

### analysisUrl.ts — New Builder

File: `frontend/src/lib/analysisUrl.ts`

Current:
```typescript
const ANALYSIS_PATH = '/analysis';
const FEN_PARAM = 'fen';
export function buildAnalysisUrl(fen: string): string { ... }
```

Add:
```typescript
const GAME_ID_PARAM = 'game_id';
const PLY_PARAM = 'ply';

export function buildGameAnalysisUrl(gameId: number, ply: number): string {
  return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}&${PLY_PARAM}=${ply}`;
}
```

No URL encoding needed — numeric values only.

### theme.ts — Color Audit

File: `frontend/src/lib/theme.ts`

Confirmed existing:
- `TAC_MISSED = 'oklch(0.70 0.15 258)'` (line 151) ✓
- `TAC_MISSED_BG = 'oklch(0.70 0.15 258 / 0.15)'` (line 152) ✓
- `TAC_ALLOWED = 'oklch(0.70 0.15 25)'` (line 156) ✓
- `TAC_ALLOWED_BG = 'oklch(0.70 0.15 25 / 0.15)'` (line 157) ✓
- `TAC_ALLOWED_BORDER = 'oklch(0.70 0.15 25 / 0.30)'` (line 158) ✓
- `ACTIVE_FILTER_RING_CLASS = 'ring-2 ring-offset-1'` (line 177) ✓
- `SEV_BLUNDER = 'oklch(0.58 0.19 25)'` (line 31) ✓ — for blunder icon
- `SEV_MISTAKE = 'oklch(0.70 0.16 55)'` (line 32) ✓ — for mistake icon

**MISSING — must add:**
- `TAC_MISSED_BORDER` — the UI-SPEC specifies `TAC_MISSED/0.30` for the inline chip border. `TAC_ALLOWED_BORDER` exists; the symmetric constant for missed does not. Add:
  ```typescript
  export const TAC_MISSED_BORDER = 'oklch(0.70 0.15 258 / 0.30)';
  ```
  After line 152 in theme.ts.

**Pre-existing severity icons** (`SeverityGlyphIcon.tsx`): `BlunderIcon` and `MistakeIcon` are already exported and already imported in `TacticModeOverlay.tsx` (line 21). For D-02 move-list non-tactic markers, the planner imports them directly into `VariationTree.tsx`. No new icon components needed.

### BoardControls Relocation

File: `frontend/src/components/board/BoardControls.tsx`

`BoardControls` is purely presentational (no internal state). Its current location in `Analysis.tsx` (lines 408-430) is inside the board column:

```tsx
<div className="flex flex-col gap-2 w-full lg:w-[508px] shrink-0">
  <div className="flex flex-row items-stretch gap-2">
    {/* Board + EvalBar */}
  </div>
  <BoardControls  {/* ← currently here */}
    infoSlot={<Button ... data-testid="btn-analysis-engine-toggle">...</Button>}
    ...
  />
</div>
```

Target location (bottom of right column in `Analysis.tsx`, lines 434-485):
```tsx
<div className="flex flex-1 flex-col gap-4 min-w-0">
  {/* TacticModeOverlay */}
  {/* EngineLines */}
  <VariationTree ... />
  <BoardControls {/* ← move here */} ... />
</div>
```

The `infoSlot` (engine toggle, `data-testid="btn-analysis-engine-toggle"`) moves with `BoardControls` as-is — no prop changes. The component's `size` prop can be left at default (`sm`).

For mobile, the stacking order becomes: Board+EvalBar → EvalChart → TacticModeOverlay → EngineLines → VariationTree → BoardControls. This matches the UI-SPEC mobile layout exactly.

---

## Landmines and Contradictions

### L-1: `loadMainLine` resets the ENTIRE tree

`loadMainLine` (line 226) does a full tree reset: it creates a new `nodes` Map, new `mainLine` array, and overwrites everything. In Phase 139 tactic mode, this was correct — it seeds the PV as the only content.

For Phase 140 full-game mode, `loadMainLine` is used to load the game mainLine. The PV must then be GRAFTED as a sideline using the new `insertPvLine` method. If `loadMainLine` is ever called after `insertPvLine`, all PV nodes are wiped. The planner must ensure `loadMainLine` is called ONLY ONCE on game data arrival, and NEVER called when clicking a tactic chip — chips use `insertPvLine`.

### L-2: `isTacticMode` gating is URL-based; Phase 140 adds `isGameMode`

Currently many derived values in `Analysis.tsx` are gated on `isTacticMode = gameId != null && flawPly != null`. Phase 140 adds `isGameMode = gameId != null && initialPly != null`. These two modes are mutually exclusive (a URL cannot have both `flaw_ply` and `ply`), but the planner must clearly distinguish them. The tactic mode derived vars (`tacticPly`, `onMainLine`, `tacticNodeColors`, board arrow logic) remain gated on `isTacticMode`. The new game-mode logic is gated on `isGameMode`.

The existing backward-compat `?game_id&flaw_ply` URL entry (Phase 139 tactic mode) is unchanged — it keeps `isTacticMode` behavior exactly. Only the new `?game_id&ply` URL triggers `isGameMode`.

### L-3: Two `useTacticLines` calls in Analysis.tsx

Phase 140 adds a second `useTacticLines` call for the contextual overlay path. Both calls must be unconditional (React hooks rules). The existing call (line 144): `useTacticLines(gameId, flawPly, isTacticMode)` stays. The new call: `useTacticLines(gameId, activePvFlaw?.ply ?? null, activePvFlaw != null)`. Both are in scope at the top of the component — React rules satisfied.

### L-4: EvalChart requires two new optional props

Despite the UI-SPEC saying "reused without modification", two props are functionally required:
- `sliderTestId?: string` — for the `analysis-eval-chart-slider` testid requirement
- `sliderDisabled?: boolean` — for the "slider parks at fork" behavior (D-05)

These are backward-compatible additions (optional, defaulting to current behavior). The planner should add them to `EvalChart.tsx` and document the rationale. The "without modification" intent is satisfied — existing `LibraryGameCard` callers pass neither prop and see zero change.

### L-5: `handleReset` must clear PV state in game mode

Currently `handleReset` in `Analysis.tsx`:
- Tactic mode: `goToRoot()`
- Otherwise: `loadMainLine([], rootFen)` (clears to empty board)

In Phase 140 game mode, Reset should: (a) call `clearPvLine()`, (b) call `setActivePvFlaw(null)`, (c) navigate to the URL-initial ply (`goToNode(mainLine[initialPly])`). The planner must add this branch to `handleReset`. If `initialPly` is `null` (shouldn't happen in game mode but guard), default to `goToNode(mainLine[0])` or `goToRoot()`.

### L-6: `TAC_MISSED_BORDER` is missing from theme.ts

The inline flaw tag chip border in the UI-SPEC requires `TAC_MISSED/0.30`. `TAC_ALLOWED_BORDER` exists at line 158 of `theme.ts`. `TAC_MISSED_BORDER` does NOT exist. The planner must add it as `'oklch(0.70 0.15 258 / 0.30)'` immediately after `TAC_MISSED_BG` in theme.ts — this is a required theme.ts edit, not a VariationTree decision.

### L-7: `makeMove` batch call limitation

`makeMove` reads `stateRef.current` for the parent FEN. `stateRef.current` syncs only in `useEffect(() => { stateRef.current = state; })` — i.e., after the render following a state update. Calling `makeMove` N times in a loop from a click handler would replay all N moves from the SAME stateRef (all creating children of the same parent). The planner MUST NOT use `makeMove` for PV insertion. Use a new `insertPvLine` method that builds all PV nodes in a single `setState` call.

### L-8: `noUncheckedIndexedAccess` at mainLine/pvLine index sites

`mainLine[i]` and `pvLine[i]` return `NodeId | undefined` (tsconfig `noUncheckedIndexedAccess`). Every index access in new code must have an explicit undefined guard. The pattern in existing code (e.g., `Analysis.tsx` line 445: `const nodeId = mainLine[ply - 1]; if (nodeId !== undefined) goToNode(nodeId);`) is the correct template. The planner should follow this pattern consistently for all new index accesses on `mainLine`, `pvLine`, and `game.moves`.

### L-9: `TAC_ALLOWED_BORDER` exists but `TAC_MISSED_BORDER` not yet in any import map

When `VariationTree.tsx` imports `TAC_MISSED_BORDER` for the inline chip border, it must come from `@/lib/theme`. Since the constant doesn't exist yet, adding it to theme.ts is a prerequisite task in Wave 0 or the first task that touches the chip rendering.

---

## Validation Architecture

Two natural test seams exist for Nyquist validation:

### Move-tree nesting invariants (`useAnalysisBoard`)

After `insertPvLine(pvSans, forkNodeId)`:
- `pvLine.length === pvSans.length` (all PV moves inserted)
- Every `pvLine` node has `parentId` that chains back to `forkNodeId`
- `mainLine` is unchanged (no mutation)
- `isOnPvLine(pvLine[0]!)` returns `true`
- `isOnMainLine(pvLine[0]!)` returns `false`

After `clearPvLine()`:
- `pvLine.length === 0`
- No pvLine node IDs remain in `nodes`
- `currentNodeId` is back on `mainLine` (at the fork node or its ancestor)

After user forks within PV (calls `makeMove` while `currentNodeId` is a PV node):
- The new node is NOT in `pvLine` (was not seeded there)
- `buildVariationChain` returns `level: 2` for this node

### Slider park/sync behavior

When `currentNodeId` is NOT in `mainLine` (on PV or sub-PV):
- The `sliderDisabled` prop passed to EvalChart is `true`
- The slider's `<input>` has `disabled` attribute
- The slider value stays at the fork ply (not updated by navigation within PV)

When user returns to `mainLine` (goBack to main line):
- `sliderDisabled` becomes `false`
- Slider value updates to `currentNodeId`'s position in `mainLine`

These invariants can be covered with vitest unit tests on the hook and snapshot tests on VariationTree. Both are fast (<30s) and fit the existing test infrastructure.

---

## Sources

All findings are from direct file reads of the production codebase. No web searches or training-data assumptions used.

| File | Lines read | Key finding |
|------|-----------|-------------|
| `frontend/src/hooks/useAnalysisBoard.ts` | 1-311 | Full MoveNode/AnalysisBoardState shape; loadMainLine batch-reset behavior; stateRef sync limitation |
| `frontend/src/components/analysis/VariationTree.tsx` | 1-368 | buildVariationChain; DesktopTree single-indent; MobileTree paren pattern |
| `frontend/src/components/analysis/TacticModeOverlay.tsx` | 1-339 | Props shape; activation condition; exported arrow builders |
| `frontend/src/pages/Analysis.tsx` | 1-491 | URL param parsing; isTacticMode derivation; layout structure; current BoardControls location |
| `frontend/src/hooks/useLibrary.ts` | 1-280 | useLibraryGame signature; useTacticLines signature; query key structure |
| `frontend/src/types/library.ts` | 1-402 | GameFlawCard full shape; FlawMarker shape; FlawSeverity union |
| `frontend/src/components/library/EvalChart.tsx` | 1-1025 | All props; testid patterns; slider implementation |
| `frontend/src/components/results/LibraryGameCard.tsx` | 1-1192 | hoverPly/lastEvalPly availability; current button row structure |
| `frontend/src/components/library/FlawCard.tsx` | 1-594 | All modal imports; buttonRow structure; useLibraryGame usage |
| `frontend/src/components/library/NoAnalysisState.tsx` | 1-108 | btn-analyze-game-{gameId} testid; confirmed unchanged |
| `frontend/src/lib/analysisUrl.ts` | 1-21 | Current buildAnalysisUrl; what buildGameAnalysisUrl needs |
| `frontend/src/lib/theme.ts` | 1-200 | TAC_MISSED/ALLOWED/BG/BORDER; ACTIVE_FILTER_RING_CLASS; SEV_ colors; TAC_MISSED_BORDER absence |
| `frontend/src/components/board/BoardControls.tsx` | 1-104 | Pure presentational; safe to relocate; infoSlot prop |
| `frontend/src/components/icons/SeverityGlyphIcon.tsx` | 1-84 | BlunderIcon/MistakeIcon already exist and are already imported in TacticModeOverlay |

**Confidence:** HIGH — all claims verified by reading the actual source files.

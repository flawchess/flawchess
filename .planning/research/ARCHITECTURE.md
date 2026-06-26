# Architecture Research: Live-Engine Analysis Board (v1.29)

**Domain:** React SPA — WASM chess engine integration, branching move tree, tactic-mode overlay
**Researched:** 2026-06-26
**Confidence:** HIGH (based on direct code inspection of all named files + confirmed npm package landscape)

---

## System Overview

The analysis board sits entirely in the frontend. The backend is untouched for v1 (locked D-4). The key architectural challenge is wiring three subsystems cleanly: a live WASM engine in a Web Worker, a branching move tree that forks on mid-line moves, and a tactic-mode overlay that seeds the initial line from stored PVs. These three subsystems compose into a single `/analysis` page.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   /analysis (lazy-loaded page)                       │
│                                                                      │
│  ┌──────────────────────────┐   ┌────────────────────────────────┐  │
│  │   useAnalysisBoard       │   │   useStockfishEngine           │  │
│  │  (branching move tree)   │   │   (worker lifecycle + UCI)     │  │
│  │  ┌────────────────────┐  │   │  ┌──────────────────────────┐  │  │
│  │  │ nodes: Map<id,Node>│  │   │  │ workerRef: Worker        │  │  │
│  │  │ currentNodeId      │  │   │  │ debounce 150ms           │  │  │
│  │  │ mainLine: NodeId[] │  │   │  │ stop-pending flag        │  │  │
│  │  │ rootFen            │  │   │  │ evalCp / pv / depth      │  │  │
│  │  └────────────────────┘  │   │  └──────────────────────────┘  │  │
│  └──────────────────────────┘   └──────────────┬───────────────┘  │
│                │                               │                    │
│                │ position, lastMove            │ eval, pv lines     │
│                ↓                               ↓                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Analysis page layout                            │    │
│  │  ┌──────────┐  ┌──────────────────────┐  ┌──────────────┐  │    │
│  │  │ EvalBar  │  │ ChessBoard (existing) │  │ EngineLines  │  │    │
│  │  │ (new)    │  │ + ArrowOverlay        │  │ (new)        │  │    │
│  │  └──────────┘  └──────────────────────┘  └──────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │ BoardControls (existing, infoSlot = depth/eval text) │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │ VariationTree (new: branching move list)             │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │ TacticModeOverlay (new, conditional on tactic mode)  │   │    │
│  │  │  TacticMotifChip (existing) + missed/allowed toggle  │   │    │
│  │  │  + next/prev-tactic rail                             │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    postMessage (UCI strings)
                                │
┌───────────────────────────────▼───────────────────────────────────┐
│      Web Worker: stockfish-18-lite-single.js (from public/)        │
│      Single-thread WASM Stockfish 18 (lite, ~7MB)                 │
│      No SharedArrayBuffer, no COOP/COEP headers required           │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Map: New vs Modified vs Deleted vs Unchanged

### New files

| File | Purpose |
|------|---------|
| `src/hooks/useStockfishEngine.ts` | Worker lifecycle, UCI protocol, debounce, stale-result cancellation, MultiPV |
| `src/hooks/useAnalysisBoard.ts` | Branching move tree (new hook, not a variant of useChessGame), URL param sync |
| `src/pages/Analysis.tsx` | `/analysis` page shell (lazy-loaded via React.lazy) |
| `src/components/analysis/EvalBar.tsx` | Vertical centipawn bar (white-POV, gradient, mate display) |
| `src/components/analysis/EngineLines.tsx` | Top 1-2 PV lines with depth and score readout |
| `src/components/analysis/VariationTree.tsx` | Move list that shows branching — main line + variations |
| `src/components/analysis/TacticModeOverlay.tsx` | Tactic chrome: motif chip, missed/allowed toggle, next/prev-tactic nav rail |

### Modified files

| File | Change |
|------|--------|
| `src/App.tsx` | Add `React.lazy` import for `AnalysisPage`, add `/analysis` route inside `ProtectedLayout`, update `ROUTE_TITLES` |
| `src/components/library/FlawCard.tsx` | Phase 4: change "Explore" button from `setExploreOpen(true)` to `navigate('/analysis?game_id=X&flaw_ply=Y')` |
| `src/components/results/LibraryGameCard.tsx` | Phase 4: same "Explore" button wiring change |

### Deleted files (Phase 4, after parity verified)

| File | Reason |
|------|--------|
| `src/components/library/TacticLineExplorer.tsx` | Subsumed into `TacticModeOverlay` on the analysis page |
| `src/hooks/useTacticLine.ts` | Replaced by `useAnalysisBoard` + tactic-mode seeding |

### Unchanged (reused as-is)

`ChessBoard.tsx`, `BoardControls.tsx`, `HorizontalMoveList.tsx`, `TacticMotifChip.tsx`,
`tacticDepth.ts`, `tacticComparisonMeta.ts`, `resolveVisibleTactic`, `arrowColor.ts`,
`theme.ts`, `useLibrary.ts` (including `useTacticLines`), `arrowGeometry.ts`,
`sanToSquares.ts`, `moveNumberLabel.ts`, `formatFlawEval.ts`

---

## Architectural Patterns

### Pattern 1: Worker Lifecycle Owned by the Hook

**What:** `useStockfishEngine` creates one `Worker` on mount and terminates it on unmount. The worker is never shared across mounts or pages.

**Why single per-mount, not global singleton:** The analysis page is lazy-loaded. A global singleton would force the WASM binary to load at app start. Per-mount creation/destruction keeps the ~7MB WASM load deferred until the user actually visits `/analysis`. Worker re-creation on re-visit is acceptable (takes ~1-2 seconds for NNUE init; show a "loading engine" indicator during this window).

**Worker creation:** The `stockfish.js` npm package (nmrugg, Stockfish 18) ships `stockfish-18-lite-single.js` and `stockfish-18-lite-single.wasm` as paired files. Copy both into `public/` so Vite serves them as static assets. The hook creates a classic Worker pointing at the public URL:

```typescript
// In useStockfishEngine, inside useEffect([]):
const worker = new Worker('/stockfish-18-lite-single.js');
worker.postMessage('uci');
worker.postMessage('setoption name MultiPV value 2');
worker.postMessage('isready');
worker.onmessage = handleMessage;
workerRef.current = worker;

return () => {
  worker.postMessage('stop');
  worker.terminate();
  workerRef.current = null;
};
```

Note: the `.wasm` file must sit beside the `.js` file in `public/` — the JS loader resolves its sibling by relative URL. Do not process these files through Vite's bundler.

**Engine state tracking:** Maintain `isAnalyzingRef: boolean` so the hook knows whether to send `stop` before a new position. The worker emits a stale `bestmove` immediately when stopped; this must be discarded (see Pattern 2).

**UCI init sequence:** After creating the worker, send `uci` and wait for `uciok`, then send `setoption name MultiPV value 2`, then `isready` and wait for `readyok` before starting any analysis. Track this with an `isReady: boolean` state so `analyze()` queues until ready.

### Pattern 2: Debounce + Stale-Result Cancellation for Rapid Position Changes

**Problem:** User navigates backward/forward rapidly. Each position change triggers a new analysis. Without cancellation, late-arriving results from old positions update the displayed eval with stale data.

**Solution — two-layer guard:**

Layer A (debounce): Wait 150ms after the last position change before sending any UCI commands. This prevents sending stop/go for every ply during fast navigation.

Layer B (stop-pending flag): When `stop` is sent to interrupt an in-flight analysis, the engine emits a `bestmove` immediately (the termination response). That bestmove is stale and must be discarded. Track this with a `stopPendingRef: boolean` flag.

```typescript
const stopPendingRef = useRef(false);
const isAnalyzingRef = useRef(false);

function analyze(fen: string) {
  // Layer A: debounce handles calling this only after 150ms quiesce
  const worker = workerRef.current;
  if (!worker || !isReady) return;

  if (isAnalyzingRef.current) {
    worker.postMessage('stop');
    stopPendingRef.current = true; // next bestmove is the stale stop-result
    isAnalyzingRef.current = false;
  }

  worker.postMessage(`position fen ${fen}`);
  worker.postMessage(`go nodes 500000`);
  isAnalyzingRef.current = true;
}

// In worker.onmessage:
if (line.startsWith('bestmove')) {
  if (stopPendingRef.current) {
    stopPendingRef.current = false;
    isAnalyzingRef.current = false;
    return; // discard stale stop-bestmove
  }
  isAnalyzingRef.current = false;
  // update state with fresh result
}
```

**Node cap vs depth:** Use `go nodes 500000` rather than `go depth N` or `go movetime N`. Node count gives more consistent performance across hardware: fast desktop searches deeper, slow phone searches shallower, but both finish in roughly the same wall time. Cap at 500k-1M nodes for interactive use; expose the depth reached in the `info` callback.

**Hook return shape:**
```typescript
interface EngineState {
  evalCp: number | null;     // centipawns, white-POV (positive = white ahead)
  evalMate: number | null;   // mate in N (positive = white mates)
  pvLines: PvLine[];         // up to 2 lines, each with { moves: string[], score }
  depth: number;             // depth reached so far
  isAnalyzing: boolean;
  isReady: boolean;
}
```

### Pattern 3: Branching Move Tree in `useAnalysisBoard`

**What:** A new hook, independent of `useChessGame`. Making a move at any node (including mid-line) creates a new child node (fork) rather than truncating the main line.

**Critically: do not modify `useChessGame`.** That hook's truncation behavior at line 183-189 is correct for the Openings board. `useAnalysisBoard` is a separate hook for the analysis page only. The two hooks share no runtime code.

**Why not extend useChessGame:** `useChessGame` has sessionStorage persistence, Zobrist hashing, opening lookup, `MAX_EXPLORER_PLY` cap, and window-level keyboard handling — none of which are wanted on the analysis board. The shared logic (chess.js move-making, position replay) is small enough that writing a new hook costs less than coupling two features with incompatible contracts.

**Tree node shape:**
```typescript
type NodeId = number; // auto-incrementing integer

interface MoveNode {
  id: NodeId;
  san: string;          // SAN of the move that reached this position
  fen: string;          // Full FEN of this position (stored, not replayed)
  from: string;         // Source square (for board highlighting)
  to: string;           // Target square
  parentId: NodeId | null; // null means the parent is rootFen
}
```

**Why store FEN per node:** The `replayTo` pattern in `useChessGame` replays the full move history from position 0 on every navigation. For a linear list this is fine. For arbitrary tree traversal, replaying from root is O(depth). Storing FEN per node makes `goToNode(id)` O(1): read `nodes.get(id).fen`, set board state directly. The `Chess` instance only needs to be live for making new moves (initialized from the parent node's FEN).

**Tree state:**
```typescript
interface AnalysisBoardState {
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null; // null = at root (rootFen)
  mainLine: NodeId[];           // IDs of the initial PV from loadMainLine()
  rootFen: string;              // Starting position (may not be chess start)
  nextId: number;               // Auto-increment for new nodes
}
```

**Making a move (the fork behavior):**
```typescript
function makeMove(from: string, to: string): boolean {
  const parentFen = currentNodeId != null
    ? nodes.get(currentNodeId)!.fen
    : rootFen;
  const chess = new Chess(parentFen);
  const result = chess.move({ from, to, promotion: 'q' });
  if (!result) return false;

  const newNode: MoveNode = {
    id: nextId,
    san: result.san,
    fen: chess.fen(),
    from: result.from,
    to: result.to,
    parentId: currentNodeId,
  };
  // Insert into map, advance nextId, set currentNodeId = newNode.id
  return true;
}
```

The fork happens naturally: the new node is parented to `currentNodeId` regardless of whether that node already has children in other branches.

**Navigation:**
- `goBack()` → `nodes.get(currentNodeId).parentId` or null (root)
- `goForward()` → first child of `currentNodeId` in insertion order
- `goToNode(id)` → set `currentNodeId = id` directly; position = `nodes.get(id).fen`
- `loadMainLine(sans: string[], rootFen: string)` → replay the SAN array into the tree, storing one node per move as the `mainLine` NodeId array

**Helper: `isOnMainLine(nodeId)`** — `mainLine.includes(nodeId)`. Used by `TacticModeOverlay` and the variation tree to distinguish the stored PV from user variations.

**Keyboard handler:** Scoped to a `containerRef` div (same pattern as `useTacticLine`, not window-level like `useChessGame`) to avoid clashing with page-level shortcuts.

**Session storage:** Deliberately omitted. Analysis board state is URL-encoded (see Pattern 5). No sessionStorage coupling.

**Opening lookup + Zobrist hashing:** Both omitted. Not needed on the analysis board (no API calls from the board; stored PVs come from URL params).

### Pattern 4: Tactic Mode as a Conditional Overlay

**What:** When the `/analysis` page receives `?game_id=X&flaw_ply=Y` (or `&orientation=missed|allowed`) in the URL, it enters tactic mode. This is a mode flag on the page, not a separate component tree.

**Why not a separate page/component:** The analysis board is identical between free-play and tactic mode — same hooks, same board, same controls. Only the chrome around it differs (motif chip, orientation toggle, next/prev-tactic rail). Tactic mode adds the `TacticModeOverlay` and seeds the initial mainline from the stored PV; everything else is shared.

**Tactic mode seeding:**
1. URL params `game_id` + `flaw_ply` trigger `useTacticLines(gameId, ply)` (the same TanStack Query hook already used in Phase 135, unchanged in `useLibrary.ts`)
2. On data load: `loadMainLine(data.missed_moves, data.position_fen)` seeds `useAnalysisBoard`
3. The `position_fen` from the response becomes `rootFen`
4. Orientation toggle switches between `missed_moves` and `allowed_moves`, calling `loadMainLine` again

**Live engine handoff:** The engine analyses every position the user navigates to, including positions within the stored mainLine. When the user makes a move that creates a new node (forking off the mainLine), the engine output is the only guidance. When on the mainLine, both stored-PV arrows and engine arrows are shown.

**Arrow strategy in tactic mode:**
- At root (ply 0): same `buildRootArrows` logic as `TacticLineExplorer` — best-move blue arrow + flaw-move red arrow
- Stepping within mainLine: `buildPvArrow` logic — colored arrow on the last move, depth countdown badge
- After forking off mainLine: engine `pvLines[0].moves[0]` drives a blue best-move arrow only

**Parity with Phase 135 TacticLineExplorer:**
- Depth counter: `toDisplayDepthForOrientation()` from `tacticDepth.ts` — same math, same inputs
- `isPayoff`: `currentPly > rootDisplayDepth`, where `currentPly` = index of `currentNodeId` in `mainLine`
- `TacticMotifChip`, `HorizontalMoveList`, `moveNumberLabel`: reused directly without change
- `resolveVisibleTactic` from `tacticComparisonMeta.ts`: same usage, same flaw filter gate
- `formatFlawEval`, `mateAtPly`, `isBlackToMove`: reused directly

**Entry point change (Phase 4):** FlawCard and LibraryGameCard "Explore" buttons navigate to `/analysis?game_id=X&flaw_ply=Y&orientation=missed` instead of opening a modal. The modal (`TacticLineExplorer`) is deleted only after the Phase 135 UAT checklist passes against the new analysis page.

### Pattern 5: URL State for Entry Points

**URL param design:**

| Entry point | URL params | Who sets them |
|-------------|------------|--------------|
| Tactic mode | `?game_id=123&flaw_ply=45&orientation=missed` | FlawCard / LibraryGameCard navigate call |
| Game review ply | `?game_id=123&ply=30` | (future) game review entry |
| Opening position | `?fen=<url-encoded-FEN>` | (future) Openings page deep-link |

For v1, implement only tactic-mode params (`game_id`, `flaw_ply`, `orientation`) and plain `fen`.

**Reading params in `Analysis.tsx`:**
```typescript
const [searchParams] = useSearchParams();
const gameId = searchParams.get('game_id') ? Number(searchParams.get('game_id')) : null;
const flawPly = searchParams.get('flaw_ply') ? Number(searchParams.get('flaw_ply')) : null;
const orientation = (searchParams.get('orientation') ?? 'missed') as TacticDepthOrientation;
const startFen = searchParams.get('fen') ?? undefined;
const isTacticMode = gameId != null && flawPly != null;
```

**No URL write-back:** The analysis board does NOT update the URL as the user navigates. The URL is read-only (entry point encoding). This avoids complex history management and the confusing behavior of browser Back/Forward changing the position instead of the route. Variation exploration is ephemeral per D-4.

### Pattern 6: Code-Splitting / Lazy-Load Boundary

**Problem:** `stockfish-18-lite-single.wasm` (~7MB) must not inflate the initial page load or any route other than `/analysis`.

**Solution — two-layer isolation:**

Layer A (page-level code split): `Analysis.tsx` is imported via `React.lazy` in `App.tsx`. Vite emits it as a separate JS chunk fetched only when the router matches `/analysis`. All `analysis/` component imports are inside this chunk.

```typescript
// In App.tsx — add alongside existing page imports:
const AnalysisPage = React.lazy(() => import('./pages/Analysis'));

// In AppRoutes, inside ProtectedLayout:
<Route
  path="/analysis"
  element={
    <Suspense fallback={
      <div className="p-6 text-muted-foreground">Loading analysis board...</div>
    }>
      <AnalysisPage />
    </Suspense>
  }
/>
```

Layer B (WASM deferred to worker creation): `stockfish-18-lite-single.js` and `.wasm` live in `public/` (not bundled). The worker is created inside `useStockfishEngine`'s `useEffect` (runs after mount). Even if `Analysis.tsx` is pre-fetched, the WASM is only fetched when the hook mounts and `new Worker('/stockfish-18-lite-single.js')` executes.

**Vite config:** No `manualChunks` change needed. `React.lazy` + dynamic `import()` is Vite's built-in code-split mechanism. The `analysis/` components (EvalBar, EngineLines, VariationTree, TacticModeOverlay) are all inside the Analysis chunk automatically.

**Public file placement:** Add to project docs: copy `stockfish-18-lite-single.js` and `stockfish-18-lite-single.wasm` from `node_modules/stockfish.js/` to `public/` as part of setup (or automate via a Vite plugin hook). Do NOT import them through Vite — they must remain unprocessed static files.

**PWA service worker:** The `runtimeCaching` in `vite.config.ts` uses `NetworkOnly` for `/api/`. The WASM file at `/stockfish-18-lite-single.wasm` will be cached by the browser's HTTP cache (by default) but NOT by Workbox's service-worker cache. This is fine for v1 — the browser HTTP cache is sufficient for a file that changes only with app upgrades.

---

## Data Flow

### Normal analysis flow (free-play mode)

```
User drags piece on ChessBoard (or click-to-move via onPointerUp)
    ↓
ChessBoard.onPieceDrop(from, to)
    ↓
useAnalysisBoard.makeMove(from, to)
  → creates new MoveNode, sets currentNodeId
    ↓
React re-render: position = nodes.get(currentNodeId).fen
    ↓
useStockfishEngine detects position change (useEffect dependency on position)
  → debounce 150ms
  → if analyzing: send 'stop', set stopPendingRef = true
  → send 'position fen <new-fen>'
  → send 'go nodes 500000'
  → isAnalyzingRef = true
    ↓
Worker (stockfish-18-lite-single.js) begins search
  → emits 'info depth N score cp X pv e2e4 ...' lines (MultiPV 2)
  → emits 'bestmove e2e4 ponder d7d5'
    ↓
worker.onmessage parses lines:
  info lines → update { evalCp, evalMate, pvLines, depth } state
  bestmove → clear isAnalyzingRef; if stopPendingRef → discard; else accept
    ↓
EvalBar, EngineLines, BoardArrows re-render with new eval
```

### Tactic mode entry flow

```
User clicks "Explore" on FlawCard (Phase 4)
    ↓
navigate('/analysis?game_id=123&flaw_ply=45&orientation=missed')
    ↓
Analysis.tsx mounts (lazy-loaded on first visit to /analysis)
  → reads game_id=123, flaw_ply=45, orientation='missed' from useSearchParams
  → isTacticMode = true
    ↓
useTacticLines(123, 45, true) fetch (TanStack Query, existing endpoint)
    ↓
On data: useAnalysisBoard.loadMainLine(data.missed_moves, data.position_fen)
  → creates MoveNode chain for the stored PV as mainLine NodeIds
  → currentNodeId = null (root = position_fen)
    ↓
TacticModeOverlay renders:
  - Motif chip (TacticMotifChip, existing)
  - Orientation toggle (missed/allowed)
  - Next/prev-tactic rail
Board renders with root-position arrows (best-move blue + flaw-move red)
Engine starts analyzing position_fen live
```

### Tactic-mode deviation flow (user forks off stored PV)

```
User makes a move NOT matching the stored mainLine's next node
    ↓
useAnalysisBoard.makeMove creates a new MoveNode (child of current)
  → this node is NOT in mainLine[]
  → isOnMainLine(newNodeId) = false
    ↓
TacticModeOverlay: stored-PV arrows not shown (off-line)
Engine arrows (live best-move from pvLines) take over as the only guide
displayDepth counter: derived from ply offset (continues showing)
isPayoff: recalculated from currentNodeId vs mainLine[rootDisplayDepth]
```

---

## Component Responsibilities

| Component / Hook | Responsibility | Communication |
|-----------------|----------------|--------------|
| `useStockfishEngine` | Worker lifecycle, UCI, debounce, stale-result cancellation | Returns `{ evalCp, evalMate, pvLines, depth, isAnalyzing, isReady }` |
| `useAnalysisBoard` | Branching tree, makeMove, navigation, URL seeding, mainLine tracking | Returns `{ position, currentNodeId, nodes, mainLine, rootFen, lastMove, makeMove, goBack, goForward, goToNode, loadMainLine, isOnMainLine }` |
| `Analysis.tsx` | Page shell: reads URL params, composes hooks, decides tactic/free mode | Passes props down to all sub-components |
| `EvalBar` | Vertical centipawn bar, gradient shading, mate label | Props: `evalCp`, `evalMate` |
| `EngineLines` | Top 1-2 PV lines with depth and score | Props: `pvLines`, `depth`, `isAnalyzing` |
| `VariationTree` | Move list showing tree; clicking a node calls `goToNode` | Props: `nodes`, `mainLine`, `currentNodeId`, `onNodeClick` |
| `TacticModeOverlay` | Motif chip, orientation toggle, next/prev-tactic rail | Props: tactic data, orientation, `onOrientationChange`, `onNextTactic`, `onPrevTactic` |
| `ChessBoard` (existing) | Board rendering, drag-drop, click-to-move | No changes; receives `position`, `onPieceDrop`, `arrows`, `lastMove`, `id="analysis-board"` |
| `BoardControls` (existing) | Back/forward/reset/flip; `infoSlot` for depth/eval readout | No changes; callbacks from `useAnalysisBoard` |

---

## Integration Points with Existing Code

### `useChessGame.ts` — do not modify

`useChessGame`'s `makeMove` at line 183-189 truncates future history when the user moves at a non-terminal ply. This is the correct behavior for the Openings board. `useAnalysisBoard` is a parallel implementation. The two hooks share no code and have no runtime coupling. The analysis board will not cause any regressions in the Openings board.

### `ChessBoard.tsx` — no changes required

Already supports multiple boards in the same DOM via the `id` prop (added in Phase 135). Pass `id="analysis-board"` in `Analysis.tsx`. The `onPieceDrop(sourceSquare, targetSquare): boolean` signature matches `useAnalysisBoard.makeMove` directly.

The `arrows?: BoardArrow[]` prop carries both stored-PV arrows (tactic mode, while on mainLine) and engine best-move arrows. Arrow-building helpers (`buildRootArrows`, `buildPvArrow`) move from `TacticLineExplorer` into `TacticModeOverlay` with no signature changes.

### `BoardControls.tsx` — no changes required

The `infoSlot?: React.ReactNode` prop is the slot for the engine eval readout. Pass a small inline element showing depth and centipawn score. The `vertical` and `size` props are ready for responsive layout on the analysis page.

### `HorizontalMoveList.tsx` + `TacticMotifChip.tsx` — reused as-is

`VariationTree` can use `HorizontalMoveList` for the mainLine segment and a secondary list for user variations below. `TacticModeOverlay` directly reuses `TacticMotifChip` with no changes.

### `useTacticLines` in `useLibrary.ts` — unchanged

Called from `Analysis.tsx` in tactic mode. `TacticLineExplorer` deletion in Phase 4 removes the only other call site; `Analysis.tsx` / `TacticModeOverlay` become the new callers. The hook signature and query key are unchanged.

### `tacticDepth.ts` — unchanged

`toDisplayDepthForOrientation`, `DEPTH_DISPLAY_OFFSET`, `ALLOWED_DECISION_DEPTH_OFFSET` all stay as-is. `TacticModeOverlay` imports them directly, same as `TacticLineExplorer` did.

### `resolveVisibleTactic` in `tacticComparisonMeta.ts` — unchanged

Used in `TacticModeOverlay` to gate depth labels on the live flaw filter. Identical usage to `TacticLineExplorer`.

### `App.tsx` — minimal change

Add `const AnalysisPage = React.lazy(() => import('./pages/Analysis'))` alongside existing imports. Add one `<Route path="/analysis" ...>` inside `ProtectedLayout`. Add `'/analysis': 'Analysis'` to `ROUTE_TITLES`. The nav bar does not need an "Analysis" item — the page is reachable via entry points, not top navigation (consistent with the existing design where analysis is a contextual action, not a primary destination).

---

## Recommended Project Structure (new files only)

```
frontend/src/
├── hooks/
│   ├── useAnalysisBoard.ts        # NEW — branching move tree
│   └── useStockfishEngine.ts      # NEW — worker lifecycle + UCI
├── components/
│   └── analysis/                  # NEW directory
│       ├── EvalBar.tsx            # NEW — vertical centipawn bar
│       ├── EngineLines.tsx        # NEW — top 1-2 PV display
│       ├── VariationTree.tsx      # NEW — branching move list
│       └── TacticModeOverlay.tsx  # NEW — tactic chrome
├── pages/
│   └── Analysis.tsx               # NEW — lazy-loaded page
public/
├── stockfish-18-lite-single.js    # COPIED from node_modules/stockfish.js/
└── stockfish-18-lite-single.wasm  # COPIED from node_modules/stockfish.js/
```

---

## Dependency-Ordered Build Sequence

The seed's 5-phase shape is validated against the real code. Dependencies flow strictly left to right.

### Phase 1 — `useStockfishEngine` + WASM setup

Dependencies: none (fully standalone)

Deliverables:
- Add `stockfish.js` to `package.json`; copy `stockfish-18-lite-single.js` + `.wasm` to `public/`
- `src/hooks/useStockfishEngine.ts`: worker creation/termination in `useEffect([], [])`, UCI init sequence (`uci` → `uciok` → `setoption MultiPV 2` → `isready` → `readyok`), `analyze(fen)` function with 150ms debounce + stop-pending flag, parse `info` lines into `{ evalCp, evalMate, pvLines, depth }`, parse `bestmove`
- Exported types: `EngineEval`, `PvLine`
- Test: unit test the pure UCI line parser; integration test confirms worker terminates on unmount (inspect `worker.terminate` called)

### Phase 2 — `useAnalysisBoard` + analysis display components

Dependencies: Phase 1 types (for optional `engineEval` per node in future, not required in v1)

Deliverables:
- `src/hooks/useAnalysisBoard.ts`: `MoveNode` type, `nodes: Map`, `makeMove` fork behavior, `goBack/goForward/goToNode`, `loadMainLine`, `isOnMainLine(nodeId)`, `containerRef` keyboard handler scoped to container
- `src/components/analysis/EvalBar.tsx`: vertical bar with gradient, white-POV convention, mate label
- `src/components/analysis/EngineLines.tsx`: PV line text, depth badge, "thinking" indicator
- `src/components/analysis/VariationTree.tsx`: move list rendering `nodes` + `mainLine`, click-to-navigate
- URL param helpers: `useSearchParams` reading for `fen`, `game_id`, `flaw_ply`, `orientation`
- Note: `Analysis.tsx` does NOT exist yet; test these components individually with Vitest

### Phase 3 — `/analysis` page + router wiring + entry points

Dependencies: Phases 1 and 2 complete

Deliverables:
- `src/pages/Analysis.tsx`: compose all hooks and components, determine tactic/free mode from URL params, responsive layout (eval bar left of board on desktop, below board on mobile)
- `src/App.tsx`: add `React.lazy` import, add `/analysis` route inside `ProtectedLayout`, wrap with `<Suspense>`
- Entry points wired (free-play mode only; tactic entry comes in Phase 4):
  - Openings page: "Analyze position" or "Open in Analysis" button encodes `?fen=<current-FEN>`
  - Nav: add `'/analysis': 'Analysis'` to `ROUTE_TITLES`
- `data-testid` attributes: `data-testid="analysis-page"`, `data-testid="analysis-eval-bar"`, `data-testid="analysis-engine-lines"`, `data-testid="analysis-variation-tree"`, `data-testid="analysis-board"` (via `id="analysis-board"` on ChessBoard)
- Verify WASM lazy-loads: check Network tab — no stockfish fetch on `/library`, `/openings`, `/endgames`

### Phase 4 — Tactic mode overlay + retire TacticLineExplorer

Dependencies: Phase 3 (`Analysis.tsx` exists and is routable)

Deliverables:
- `src/components/analysis/TacticModeOverlay.tsx`: render when `isTacticMode`, motif chip row, orientation toggle, next/prev-tactic navigation
- Wire `useTacticLines` into `Analysis.tsx` for tactic mode; call `loadMainLine` on data
- Port `buildRootArrows` and `buildPvArrow` logic from `TacticLineExplorer` into `TacticModeOverlay`
- Port `isPayoff` and `displayDepth` logic using `tacticDepth.ts` (same math, same inputs)
- Verify Phase 135 UAT bar: depth-0 highlight, missed/allowed offset, real-game-ply numbering, next-tactic nav, eval badge, flaw-severity glyph on allowed lead-in
- **Only after UAT passes:** change `FlawCard` and `LibraryGameCard` "Explore" buttons to `navigate('/analysis?...')`, delete `TacticLineExplorer.tsx` and `useTacticLine.ts`
- Run `npm run knip` after deletion to confirm no dead exports remain

### Phase 5 — Backend (effectively none for v1)

Per locked decision D-4: no schema, no migration, no new backend endpoints. The `tactic-lines` endpoint from Phase 135 already surfaces the stored PVs. Phase 5 is a placeholder for any minor polish (e.g., a loading-engine skeleton UX, mobile layout tweaks) that surfaces during Phases 1-4 UAT.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Modifying `useChessGame` to Support Branching

**What people do:** Add a `branching?: boolean` prop to `useChessGame` and conditionally skip truncation.
**Why it's wrong:** `useChessGame` serves the Openings board (heavily used, tested). Adding a flag makes two incompatible behaviors share state, raises regression risk, and makes the hook harder to reason about. The two behaviors have entirely different contracts: one needs sessionStorage, Zobrist, opening lookup, `MAX_EXPLORER_PLY`; the other needs none of these.
**Do this instead:** Write `useAnalysisBoard` as a separate hook. The shared logic is small enough that duplication is cheaper than coupling.

### Anti-Pattern 2: Global Worker Singleton

**What people do:** Create the Stockfish worker once at app start and share it across components.
**Why it's wrong:** Forces the ~7MB WASM to load on every page load, defeating the lazy-load strategy. Creates lifecycle complexity (who owns teardown? what happens on re-visit?).
**Do this instead:** Create the worker in `useStockfishEngine`'s `useEffect` (per mount) and terminate on cleanup. Browser HTTP cache ensures re-visits are fast.

### Anti-Pattern 3: COOP/COEP Headers for Multi-Threading

**What people do:** Add `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` site-wide to enable `SharedArrayBuffer` for the multi-thread Stockfish build.
**Why it's wrong:** `COOP: same-origin` breaks Google OAuth popups (requires `same-origin-allow-popups`, which does NOT grant cross-origin isolation). `COEP: credentialless` is not reliably supported on iOS Safari. Cross-origin isolation is a document property — it cannot be toggled per-route in an SPA. This is locked decision D-3.
**Do this instead:** Single-thread `stockfish-18-lite-single.js`. Depth 20-25 in seconds is more than sufficient for human comprehension. Multi-thread is a deferred desktop-only enhancement requiring a separately hard-loaded document.

### Anti-Pattern 4: Unbounded Engine Search

**What people do:** Use `go infinite` or `go depth 20` and let the engine run until stopped manually.
**Why it's wrong:** `go infinite` pegs the single CPU core indefinitely on low-end phones. `go depth 20` takes milliseconds on a fast desktop but minutes on weak hardware, creating unpredictable UX.
**Do this instead:** Use `go nodes 500000`. Consistent wall-clock performance across hardware. Depth is shown as it progresses; the user sees analysis improving in real time.

### Anti-Pattern 5: Serializing Variation State in the URL

**What people do:** Base64-encode the full branching tree into the URL on every navigation so any analysis state is bookmarkable.
**Why it's wrong:** Overwrites the browser back/forward stack with every position change, making navigation confusing. Produces very long URLs that break PWA share sheets. High implementation complexity for v1 value.
**Do this instead:** URL encodes only the entry point (starting FEN or tactic reference). Variations are ephemeral per D-4. The user can share the starting position; variations are re-explored manually.

---

## Scaling Considerations

| Concern | Now | Future |
|---------|-----|--------|
| Engine memory (WASM) | ~50-100MB for lite build per tab | Not a scaling issue — one engine per user, in-browser |
| WASM load time | ~1-2s first visit; browser HTTP cache on subsequent visits | Add `<link rel="prefetch">` hint on hover of analysis entry points |
| Tree size (nodes Map) | Grows with user exploration; fine to ~10k nodes | No concern; GC handles it on unmount |
| Backend load | Zero additional load per D-4 | No change; `tactic-lines` endpoint already exists |
| Mobile CPU | Single-thread node cap keeps CPU reasonable | Consider lower node count on slow devices (navigator.hardwareConcurrency === 1) |

---

## Sources

- Direct code inspection: `useChessGame.ts`, `useTacticLine.ts`, `ChessBoard.tsx`, `BoardControls.tsx`, `TacticLineExplorer.tsx`, `tacticDepth.ts`, `App.tsx`, `vite.config.ts`, `Analysis.tsx` (the existing pages structure and router), `FlawCard.tsx`, `LibraryGameCard.tsx` — all read in full for this research session
- SEED-066 locked design decisions (D-1 through D-5)
- npmjs.com `stockfish.js` package (nmrugg, Stockfish 18) — ships `stockfish-18-lite-single.js` + `.wasm` (~7MB each), single-thread, runs without CORS headers, UCI via `worker.postMessage(string)` — **recommended package**
- GitHub lichess-org/stockfish.wasm — passively maintained, multi-thread, no NNUE; recommends stockfish-web as successor
- GitHub lichess-org/stockfish-web — not straight-forward for direct browser use; not recommended for v1

---

*Architecture research for: v1.29 Live-Engine Analysis Board (FlawChess)*
*Researched: 2026-06-26*

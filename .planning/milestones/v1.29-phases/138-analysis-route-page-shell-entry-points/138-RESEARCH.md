# Phase 138: `/analysis` Route + Page Shell + Entry Points - Research

**Researched:** 2026-06-26
**Domain:** Frontend composition — React 19 + React Router v6 lazy route, WASM-worker hook wiring, URL entry-point param reading
**Confidence:** HIGH (all signatures verified by direct source inspection of the real Phase 136/137 deliverables)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (carried, Phase 137):** URL is **read-only entry-point encoding** — no write-back; live navigation/forks are ephemeral. The opening-position entry encodes only the *starting* FEN.
- **D-02:** **Opening-position entry is in scope for 138.** Surface: an "Analyze position" action on the Openings page (Explorer tab) that carries the **current Explorer board position** (the `position` FEN already held by `pages/Openings.tsx` / `ExplorerTab`) to `/analysis?fen=…`. Button placement/label is Claude's discretion; lives where the user is already looking at a position. Reuses the v1 `fen` param — no new reader, no backend (D-4).
- **D-03:** **Game-review-ply entry point is DESCOPED from Phase 138 and folded into Phase 139.** The `?game_id=&ply=` reader is NOT built here. Only the opening-position entry + route + page shell are in scope.
- **D-04:** **ROADMAP Phase 138 title and ROUTE-02 wording are left untouched** ("game-review ply" still appears). The descope is recorded in CONTEXT only — no unrequested ROADMAP/REQUIREMENTS edits.
- **D-4 (milestone-level):** No backend work. Frontend-only phase.
- **D-05:** **No nav-bar "Analysis" item.** `/analysis` is reachable via entry points and by typing the URL; a blank-board free-play (no params) is a valid, reachable state (empty `fen` → standard start position).
- **D-06:** **Engine on by default** on page mount; the "Loading engine…" / "analyzing" state shows in the eval area during WASM init while the board/stepper stay interactive (SC#3). Toggle-off available per ENGINE-04.
- **D-07:** **Lazy-load boundary is the acceptance spine** (SC#1): `React.lazy` page split keeps the stockfish JS/WASM off every other route. Verify via Network tab — no stockfish fetch on `/library`, `/openings`, `/endgames`. `window.crossOriginIsolated === false` on `/analysis`; Google OAuth flow completes from any page (SC#4, PLAT-01 — already CI-guarded in 136).

### Claude's Discretion
- **Page shell layout** — responsive composition (lichess/chess.com convention: eval bar beside the board on desktop, stacked below on mobile; EngineLines + VariationTree placement; board sizing). Reuse existing `ChessBoard` (`id`/`data-testid="analysis-board"`), `theme.ts` tokens, `text-sm` floor, `data-testid` on interactive elements.
- **"Analyze position" button** — exact placement on the Openings Explorer tab, label, icon, and `Button` variant (`brand-outline` per CLAUDE.md secondary-action rule unless it reads as the primary CTA there). Apply to mobile + desktop surfaces (CLAUDE.md parity rule).
- **Suspense fallback copy** and the engine-loading indicator wording/visual.
- Whether the blank free-play state needs any onboarding affordance, or just renders the start position silently (lean: silent, no extra chrome).

### Deferred Ideas (OUT OF SCOPE)
- **Game-review-ply entry point** — descoped from 138 (D-03), folded into Phase 139.
- **ROADMAP/ROUTE-02 wording cleanup** — adjust at milestone close or when 139 absorbs the entry (D-04).
- **On-demand "copy position link"** — v2, alongside nested-tree work.
- **Paste-a-FEN / paste-PGN entry box** — BOARD-V2-01, v2.
- Tactic-mode overlay + chrome + stored-PV seeding, retiring `TacticLineExplorer`/`useTacticLine` — Phase 139.
- URL write-back / live variation serialization — D-01, never in v1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROUTE-01 | User can reach a standalone `/analysis` page, lazy-loaded so the engine bundle is fetched only on this route | Pattern 6 (React.lazy + Suspense in `App.tsx`); engine files already in `public/engine/` (unbundled); worker created lazily inside `useStockfishEngine` effect → WASM fetch deferred to first mount. Verification: build-chunk inspection + Network tab. |
| ROUTE-02 | User can open the analysis board pre-loaded from a tactic card, a **game-review ply**, and an **opening position**, carrying the relevant position and context | **Only the opening-position entry is in scope** (D-02/D-03). `?fen=<url-encoded FEN>` reader in `Analysis.tsx`; "Analyze position" button on Openings Explorer reads `chess.position` (full FEN) and `navigate('/analysis?fen=…')`. Tactic + game-review entries are Phase 139. |
</phase_requirements>

## Summary

Phase 138 is **pure composition + wiring** — it writes one new page (`src/pages/Analysis.tsx`), adds three lines to `App.tsx` (lazy import + `<Route>` + `ROUTE_TITLES` entry), and adds one "Analyze position" button to the Openings Explorer. All the hard parts (the WASM worker lifecycle, the UCI state machine, the branching tree, the eval/engine-line/variation-tree rendering) are already built and unit-tested in Phases 136 and 137. There are **zero new npm packages** — `stockfish` 18.0.8 is already a dependency and the engine binaries already sit in `frontend/public/engine/`.

The single highest-value output of this research is the **exact composition contract**: the verified return shapes of `useStockfishEngine` and `useAnalysisBoard`, and the exact prop names of `EvalBar`, `EngineLines`, `VariationTree`. These are recorded below from direct source reads (not from CONTEXT memory) so the planner can wire them without guessing. The second-highest is the **lazy-load mechanics**: `App.tsx` currently lazy-loads nothing, so this introduces the first `React.lazy` + `<Suspense>` boundary; the engine binaries are already correctly placed in `public/` and excluded from Vite's optimizer, so the lazy boundary is the only new isolation work.

**Primary recommendation:** Mount both hooks unconditionally in `Analysis.tsx`; drive the engine's `fen` from `analysisBoard.position` (gated by an `engineEnabled` state defaulting `true`); render `EvalBar`/`EngineLines` from the engine state and `ChessBoard`/`VariationTree` from the board state; show a "Loading engine…" indicator in the eval area while `engine.isReady === false`. Read `?fen=` once as the `useAnalysisBoard` initial root FEN (empty → standard start).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `/analysis` route + lazy boundary | Browser / Client (SPA router) | — | Client-side routing; D-05 keeps it out of nav, reachable by URL/entry-point |
| WASM engine execution | Browser / Web Worker | — | Single-thread Stockfish in a Worker; no backend (D-4); no SAB/COOP/COEP |
| Branching move tree state | Browser / Client | — | `useAnalysisBoard` is in-memory, ephemeral, no persistence (D-01) |
| Entry-point FEN transport | Browser / Client (URL query) | — | Read-only `?fen=` param; no backend round-trip (D-02) |
| Engine binary delivery | CDN / Static (`public/engine/`) | Browser HTTP cache | Unbundled static asset; HTTP cache, never SW-precached (iOS 50 MB limit) |
| Auth gate for `/analysis` | Frontend Server / Client guard | — | `ProtectedLayout` (`token` check) — authenticated users only (SC#1) |

## Standard Stack

**No new packages.** Phase 138 composes existing dependencies only.

### Already-present (verified) building blocks
| Module | Path | Role in Phase 138 |
|--------|------|-------------------|
| `useStockfishEngine` | `frontend/src/hooks/useStockfishEngine.ts` | Engine state source (`evalCp`, `evalMate`, `pvLines`, `depth`, `isAnalyzing`, `isReady`) |
| `useAnalysisBoard` | `frontend/src/hooks/useAnalysisBoard.ts` | Board/tree state + navigation |
| `EvalBar` | `frontend/src/components/analysis/EvalBar.tsx` | Vertical white-POV eval bar |
| `EngineLines` | `frontend/src/components/analysis/EngineLines.tsx` | Top-2 PV lines + clickable chips |
| `VariationTree` | `frontend/src/components/analysis/VariationTree.tsx` | Branching move list |
| `ChessBoard` | `frontend/src/components/board/ChessBoard.tsx` | Board render + drag/click-to-move |
| `BoardControls` | `frontend/src/components/board/BoardControls.tsx` | back/forward/reset/flip (`infoSlot` available) |
| `stockfish` (npm) | `package.json` `"stockfish": "18.0.8"` | Engine binaries copied to `public/engine/` |

### Verified engine binary placement
```
frontend/public/engine/stockfish-18-lite-single.js     (21 KB loader)
frontend/public/engine/stockfish-18-lite-single.wasm   (7.3 MB)
```
`useStockfishEngine` loads `new Worker('/engine/stockfish-18-lite-single.js')` (`ENGINE_PATH` constant). Note: ARCHITECTURE.md drafts say `/stockfish-…` at root, but the **real, shipped path is `/engine/…`** — use that. `[VERIFIED: codebase grep]`

**Installation:** none. `npm install` already covers it. The engine files are committed under `public/engine/`. Do not re-copy or re-add.

## Package Legitimacy Audit

> Phase 138 installs **no external packages**. The only engine dependency (`stockfish` 18.0.8) was vetted and installed in Phase 136 and its binaries are already committed under `public/engine/`.

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none) | — | No new packages this phase |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Exact Composition Contract (the load-bearing section)

> All signatures below are copied from the real source files in this session — **not** from CONTEXT.md memory. `[VERIFIED: codebase read]`

### `useStockfishEngine(options) → StockfishEngineState`
```ts
// Input
interface UseStockfishEngineOptions {
  fen: string | null;   // current board FEN; null keeps engine idle (no `go` sent)
  enabled: boolean;     // false ⇒ Worker is NOT created and analysis does not run
}
// Output
interface StockfishEngineState {
  evalCp: number | null;    // centipawns, white-POV; null while loading or if score is mate
  evalMate: number | null;  // mate in N (+ = white winning); null if cp score
  pvLines: PvLine[];        // up to MULTIPV(=2) lines, sorted by multipv index
  depth: number;            // depth of last committed analysis
  isAnalyzing: boolean;     // true while searching current position
  isReady: boolean;         // true once UCI init (uciok + readyok) completes
}
```
**Wiring notes (verified from source):**
- Pass `fen={engineEnabled ? analysisBoard.position : null}` and `enabled={engineEnabled}`. When `enabled` flips `true→false` the effect cleanup runs `stop` + `worker.terminate()` (battery-safe). Flipping back `false→true` recreates the worker (~1–2 s NNUE re-init; show loading state again).
- The hook **already owns** the 150 ms debounce, the stop/bestmove stale-eval guard (Pitfall 3), tab-hide pause, MultiPV ordering, and `bound==='exact'` filtering. Phase 138 does **not** re-implement any of these.
- `evalCp`/`evalMate` are both `null` until the first `bestmove` commits — `EvalBar` renders the 0.50 midpoint gracefully in that window.

### `useAnalysisBoard(initialRootFen?) → AnalysisBoardReturn`
```ts
function useAnalysisBoard(initialRootFen?: string): AnalysisBoardReturn
// default initialRootFen = STARTING_FEN ('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

interface AnalysisBoardReturn {
  position: string;                                  // current node FEN (or rootFen at root)
  currentNodeId: NodeId | null;                      // null = at root
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  rootFen: string;
  lastMove: { from: string; to: string } | null;
  makeMove: (from: string, to: string) => boolean;   // input-agnostic; forks mid-line
  goBack: () => void;
  goForward: () => void;
  goToNode: (id: NodeId) => void;
  loadMainLine: (sans: string[], newRootFen: string) => void;  // resets whole tree
  isOnMainLine: (nodeId: NodeId) => boolean;
  containerRef: RefObject<HTMLDivElement | null>;    // attach to wrapper div for ←/→ keys
}
```
**Wiring notes (verified from source):**
- `initialRootFen` is consumed **only** in the `useState` initializer — it is **not** reactive. If the `?fen=` param changes while the component stays mounted (e.g. a second entry-point navigation to `/analysis?fen=Y` without unmount), the board will NOT reset. See Pitfall 2 below for the fix.
- There is **no `reset()` method**. `BoardControls.onReset` must be wired to `() => loadMainLine([], analysisBoard.rootFen)` (clears the tree back to root) — `loadMainLine` with an empty SAN array resets `nodes`/`mainLine` and sets `currentNodeId = null`. `[VERIFIED: source — loadMainLine sets currentNodeId to null when newMainLine is empty]`
- `containerRef` must be attached to a wrapper `<div>` around the board for the container-scoped ArrowLeft/ArrowRight handler to fire. The handler listens on the container element; it only receives `keydown` once a focusable child (a board square button) has focus — the same working pattern as `TacticLineExplorer` (no explicit `tabIndex` needed because `ChessBoard` squares are focusable and events bubble).

### `<EvalBar>` props
```ts
interface EvalBarProps {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
  className?: string;   // caller overrides width/height (Phase 138 layout)
}
// data-testid="analysis-eval-bar". White always at TOP regardless of board orientation (no `orientation` prop).
```

### `<EngineLines>` props
```ts
interface EngineLinesProps {
  pvLines: PvLine[];
  depth: number;
  isAnalyzing: boolean;
  startPly?: number;                               // default 0 — for move-number labels
  onMoveClick: (from: string, to: string) => void; // wire to analysisBoard.makeMove
}
// data-testid="analysis-engine-lines".
// Renders its own "Analyzing…" spinner when (isAnalyzing && pvLines.length===0).
// Renders EMPTY when (!isAnalyzing && pvLines.length===0) — its comment explicitly says
// "Phase 138 handles engine-loading chrome", i.e. the "Loading engine…" state is the page's job.
```

### `<VariationTree>` props
```ts
interface VariationTreeProps {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
  currentNodeId: NodeId | null;
  rootPly?: number;                  // default 0 — move-number labels
  onNodeClick: (nodeId: NodeId) => void;  // wire to analysisBoard.goToNode
  heightClass?: string;              // mobile HorizontalMoveList height override
}
// data-testid="analysis-variation-tree". Responsive: sm:hidden mobile horizontal list / hidden sm:block desktop list — self-contained, no media-query hook needed.
```

### `<ChessBoard>` props (existing, no change)
```ts
position: string;                                            // = analysisBoard.position
onPieceDrop: (sourceSquare, targetSquare) => boolean;        // = analysisBoard.makeMove
flipped?: boolean;                                           // local flip state
lastMove?: { from: string; to: string } | null;             // = analysisBoard.lastMove
arrows?: BoardArrow[];                                        // optional engine best-move arrow (discretion)
id?: string;                                                 // pass id="analysis-board" (drives square testids + data-testid)
```

### Move-number anchoring (`startPly` / `rootPly`)
`moveLabel(flawPly, index)` in `lib/moveNumberLabel.ts` anchors full-move numbers. For the **standard start** the anchor is `0`. For an **opening-position FEN** entry, the correct anchor is derived from the FEN's side-to-move + fullmove number:
```ts
// rootPly = (fullmoveNumber - 1) * 2 + (sideToMove === 'b' ? 1 : 0)
const [, side, , , , fullmove] = fen.split(' ');
const rootPly = (Number(fullmove) - 1) * 2 + (side === 'b' ? 1 : 0);
```
Pass this `rootPly` to `VariationTree` and as `startPly` to `EngineLines` so move numbers match the real position, not "1." `[ASSUMED]` — formula is standard FEN arithmetic; confirm visually during UAT. For v1 a simpler `rootPly={0}` is acceptable if move-number fidelity from arbitrary FENs is deemed out of scope (flag to user).

## Architecture Patterns

### System Architecture Diagram
```
 Openings Explorer (chess.position = full FEN)
        │  click "Analyze position"
        ▼
 navigate(`/analysis?fen=${encodeURIComponent(chess.position)}`)
        │
        ▼
 React Router matches /analysis  ──►  <Suspense fallback="Loading analysis board…">
        │                                    │  (first match triggers lazy chunk fetch)
        ▼                                    ▼
 AnalysisPage = React.lazy(() => import('./pages/Analysis'))   [separate JS chunk]
        │
        ▼
 Analysis.tsx
   ├─ const [params] = useSearchParams(); fen = params.get('fen') ?? undefined
   ├─ const board  = useAnalysisBoard(fen)              // initial root = fen or STARTING_FEN
   ├─ const [engineEnabled, setEngineEnabled] = useState(true)   // D-06
   ├─ const engine = useStockfishEngine({ fen: engineEnabled ? board.position : null,
   │                                       enabled: engineEnabled })
   │        │  enabled=true ⇒ effect runs new Worker('/engine/stockfish-18-lite-single.js')
   │        ▼  ⇒ first /engine/*.wasm fetch happens HERE, only on /analysis  (Layer B isolation)
   ├─ layout:
   │    EvalBar(engine.evalCp, engine.evalMate, engine.depth)
   │    ChessBoard(board.position, board.makeMove, board.lastMove, id="analysis-board")  ← wrapped in board.containerRef div
   │    EngineLines(engine.pvLines, engine.depth, engine.isAnalyzing, onMoveClick=board.makeMove)
   │    VariationTree(board.nodes, board.mainLine, board.currentNodeId, onNodeClick=board.goToNode)
   │    BoardControls(onBack=board.goBack, onForward=board.goForward,
   │                  onReset=()=>board.loadMainLine([], board.rootFen), onFlip=…)
   └─ if (engineEnabled && !engine.isReady) → "Loading engine…" indicator in eval area
```

### Pattern A: First `React.lazy` + `<Suspense>` boundary in the app
`App.tsx` currently imports every page eagerly (`import { OpeningsPage } from '@/pages/Openings'`). Add the lazy boundary **without** touching the other imports:
```ts
import { lazy, Suspense } from 'react';
const AnalysisPage = lazy(() => import('./pages/Analysis'));   // default export required

// Inside <Route element={<ProtectedLayout />}> … add:
<Route
  path="/analysis"
  element={
    <Suspense fallback={<div className="p-6 text-muted-foreground" data-testid="analysis-loading">Loading analysis board…</div>}>
      <AnalysisPage />
    </Suspense>
  }
/>
// And add to ROUTE_TITLES:  '/analysis': 'Analysis',
```
- **`Analysis.tsx` must `export default`** for `React.lazy` to resolve. (Every existing page uses a *named* export — this page differs.) `[VERIFIED: source — App.tsx uses named imports for all current pages]`
- Place the route **inside** `<Route element={<ProtectedLayout />}>` (authenticated users, SC#1). Do **not** wrap in `ImportRequiredRoute` — `/analysis` should work for any authenticated user with or without imported games (free-play is valid per D-05). Confirm this with the user if uncertain; the safe default is auth-only, no import gate.
- No nav item (D-05). `ROUTE_TITLES` only drives the mobile header title text.
- `ROUTE_TITLES` lookup in `MobileHeader` uses `pathname.startsWith(path)` — `'/analysis'` is unambiguous, no conflict with existing keys.

### Pattern B: Engine on by default + "Loading engine…" while board stays live (D-06, SC#3)
- `engineEnabled` state defaults `true`. The toggle (ENGINE-04) flips it; pass it as both `enabled` and the `fen` gate.
- The board, move stepper, `VariationTree`, and `BoardControls` are driven **entirely by `useAnalysisBoard`** and never block on the engine — they are interactive immediately (SC#3).
- The **only** region that shows a loading state is the eval area: render `"Loading engine…"` when `engineEnabled && !engine.isReady`. Once `isReady`, `EngineLines` shows its own internal "Analyzing…" spinner while `pvLines` is empty, then the lines. `EvalBar` shows the midpoint until the first eval commits.

### Pattern C: Opening-position entry (D-02)
Source of the FEN: `OpeningsPage` holds `const chess = useChessGame()`; `chess.position` is the **full current FEN** (verified: `useChessGame` returns `position: chess.fen()`). It is already passed to `ExplorerTab` as the `position` prop. The button can read either `chess.position` (in `Openings.tsx`) — preferred — or thread a callback into `ExplorerTab`.
```ts
// In Openings.tsx (has navigate + chess in scope):
const handleAnalyzePosition = useCallback(() => {
  navigate(`/analysis?fen=${encodeURIComponent(chess.position)}`);
}, [navigate, chess.position]);
```
- `encodeURIComponent` is required — FENs contain spaces and `/`.
- Reading side: `const fen = searchParams.get('fen') ?? undefined;` then `useAnalysisBoard(fen)`. `searchParams.get` already returns the decoded value (React Router decodes). Empty/missing → `undefined` → `useAnalysisBoard` defaults to `STARTING_FEN` (D-05 blank free-play).
- **Placement (discretion):** the Explorer tab already has a board-adjacent area on both desktop (`openings-board-container`) and mobile (settings column / below board). Put the button near the board controls so it reads as "take this position to analysis." Use `Button variant="brand-outline"` (secondary action per CLAUDE.md) unless it reads as the primary CTA. Apply to **both** desktop and mobile surfaces (parity rule) with distinct `data-testid`s (e.g. `btn-analyze-position`, `btn-analyze-position-mobile`).

### Recommended file changes
```
frontend/src/pages/Analysis.tsx          NEW  (default export; composes hooks + components)
frontend/src/App.tsx                      EDIT (lazy import + <Route> + ROUTE_TITLES entry)
frontend/src/pages/Openings.tsx           EDIT (one "Analyze position" handler + button ×2 surfaces)
frontend/src/pages/__tests__/Analysis.test.tsx   NEW  (Wave-0 test, see Validation Architecture)
```

### Anti-Patterns to Avoid
- **Re-implementing the debounce / stop-go state machine in `Analysis.tsx`.** It lives in `useStockfishEngine`. The page only feeds it `fen` + `enabled`.
- **Conditionally mounting `useStockfishEngine` behind an `if`.** Hooks cannot be conditional. Toggle via the `enabled` arg, never by skipping the hook call.
- **Gating the board render on `engine.isReady`.** That reintroduces Pitfall 10 (frozen board). Board renders immediately; only the eval area waits.
- **Adding COOP/COEP headers or a multi-thread engine build.** PLAT-01 / Pitfall 8 — CI-guarded. Single-thread only; `window.crossOriginIsolated` must stay `false`.
- **Re-copying engine binaries or editing `vite.config.ts` `optimizeDeps`.** Already done in Phase 136.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UCI stop/go/bestmove ordering | A new message queue in the page | `useStockfishEngine` (built) | Stale-eval race already solved (Pitfall 3) |
| Eval-bar fraction / mate display | Custom sigmoid in the page | `EvalBar` (built) | Depth-gated mate label, white-POV convention done |
| PV line rendering + clickable chips | Map over `pvLines` inline | `EngineLines` (built) | MultiPV slice, score format, spinner gate done |
| Branching move list | A tree renderer in the page | `VariationTree` (built) | Responsive desktop/mobile split + variation chain done |
| Code-splitting config | `manualChunks` in vite | `React.lazy(() => import(...))` | Vite's built-in dynamic-import split; no config (Pattern 6) |
| FEN side/move parsing for the board | Manual FEN mutation | `chess.js` (already in `useAnalysisBoard`) | The hook owns all chess.js calls |

**Key insight:** Phase 138 is a layout + 5-line-of-glue exercise. If a task description contains engine logic, parsing, or tree math, it is mis-scoped — that work shipped in 136/137.

## Common Pitfalls

### Pitfall 1: `Analysis.tsx` uses a named export → `React.lazy` resolves `undefined`
**What goes wrong:** `lazy(() => import('./pages/Analysis'))` requires a **default** export. Every other page in this codebase uses named exports, so muscle-memory produces `export function AnalysisPage()` and the route renders blank/throws.
**How to avoid:** `export default function Analysis() {…}` (or `export default Analysis`). Add a render smoke test (Wave 0) that mounts the lazy route and asserts `analysis-page` testid appears.
**Warning signs:** Suspense fallback never resolves; console "Element type is invalid… got: undefined."

### Pitfall 2: `?fen=` is read only at initial mount — second entry-point navigation won't reset the board
**What goes wrong:** `useAnalysisBoard(initialRootFen)` consumes `initialRootFen` only in its `useState` initializer (verified). Navigating `/analysis?fen=A` → `/analysis?fen=B` reuses the same mounted component, so the board stays on FEN A.
**How to avoid:** Either (a) **key the lazy route element by the fen** so React remounts on param change: `<AnalysisPage key={searchParams.get('fen') ?? 'start'} />` (simplest, recommended for v1), or (b) add a `useEffect` in `Analysis.tsx` that calls `board.loadMainLine([], fen)` when the `fen` param changes. Option (a) is cleaner and also resets the engine worker. Flag to planner: pick one; (a) preferred.
**Warning signs:** clicking "Analyze position" from two different Openings positions in one session shows the first position both times.

### Pitfall 3: Worker not terminated on route exit (battery/memory drain)
**What goes wrong:** Navigating away from `/analysis` must terminate the Worker. `useStockfishEngine` already does this in its effect cleanup (`stop` + `terminate`), but only if the hook actually unmounts.
**How to avoid:** Because `/analysis` is a normal route element (not kept-alive), React unmounts `Analysis.tsx` on navigation and the cleanup fires. Do **not** hoist `useStockfishEngine` above the route or memo-cache the page. Verify with Chrome DevTools → Task Manager: no "Dedicated Worker" after leaving `/analysis`.

### Pitfall 4: `BoardControls.onReset` has no hook method
**What goes wrong:** `useAnalysisBoard` exposes no `reset()`. Wiring `onReset={board.reset}` is `undefined`.
**How to avoid:** `onReset={() => board.loadMainLine([], board.rootFen)}` — empty SAN array clears the tree and returns to root. `canGoBack`/`canGoForward` for the controls derive from `board.currentNodeId !== null` (back) and "current node has a child" (forward); a simple `canGoBack = board.currentNodeId !== null` is correct, and `canGoForward` can be left always-enabled or computed via `findFirstChild` parity (the hook no-ops if there is no child).

### Pitfall 5: Container keyboard nav silently dead
**What goes wrong:** `board.containerRef` must wrap the board; arrow keys only fire after a focusable child has focus. If the ref is attached to a non-wrapping element or the board has no focusable child in view, ←/→ do nothing.
**How to avoid:** Attach `ref={board.containerRef}` to the `<div>` that contains `<ChessBoard>`. This mirrors the working `TacticLineExplorer` pattern. No explicit `tabIndex` is required (board squares are focusable buttons), but a `tabIndex={0}` on the wrapper is a cheap safety net if UAT shows keys not registering until a square is clicked.

### Pitfall 6: Layout collapses the eval bar on mobile / loses `text-sm` floor
**What goes wrong:** Naively reusing the lichess desktop layout (eval bar beside board) on mobile squeezes the board. CLAUDE.md forbids `text-xs` in new code (except opt-in tooltips).
**How to avoid:** Desktop: `EvalBar` adjacent to the board (use its `className` to set height to match the board). Mobile: stack the eval readout below/above the board (or render a thin horizontal variant via `className`). Keep all labels `text-sm`+. Use `theme.ts` tokens (the components already import `EVAL_BAR_WHITE/BLACK`); the page must not hard-code semantic colors.

## Runtime State Inventory

Phase 138 is **greenfield composition** — it adds a route and a page, renames/migrates nothing.
- **Stored data:** None — no DB, no persistence (D-01 ephemeral; D-4 no backend). Verified: `useAnalysisBoard` has "No session-storage persistence" in its header comment.
- **Live service config:** None.
- **OS-registered state:** None.
- **Secrets/env vars:** None.
- **Build artifacts:** None new. Engine binaries already committed in `public/engine/` (Phase 136); not rebuilt here.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `stockfish` npm | Engine binaries (already copied) | ✓ | 18.0.8 | — |
| `public/engine/stockfish-18-lite-single.{js,wasm}` | Worker load on `/analysis` | ✓ | committed | — |
| Vite 8 dynamic-import code-split | Lazy boundary | ✓ | (project) | — |
| react-router-dom v6 (`useSearchParams`, `lazy` route) | Route + param read | ✓ | (project) | — |

**Missing dependencies with no fallback:** none. This is a code-only phase against an already-prepared environment.

## Code Examples

### Reading the entry-point FEN (Analysis.tsx)
```ts
// Source: react-router-dom v6 useSearchParams (project convention)
import { useSearchParams } from 'react-router-dom';

const [searchParams] = useSearchParams();
const fenParam = searchParams.get('fen') ?? undefined;   // already URL-decoded
const board = useAnalysisBoard(fenParam);                // undefined → STARTING_FEN
```

### Engine wiring with on/off toggle (D-06 / ENGINE-04)
```ts
const [engineEnabled, setEngineEnabled] = useState(true);
const engine = useStockfishEngine({
  fen: engineEnabled ? board.position : null,
  enabled: engineEnabled,
});
const engineLoading = engineEnabled && !engine.isReady;   // drives "Loading engine…" in eval area
```

### Navigating from Openings (Pattern C)
```ts
// Source: Openings.tsx already has `navigate` + `chess` in scope
const handleAnalyzePosition = () =>
  navigate(`/analysis?fen=${encodeURIComponent(chess.position)}`);
// <Button variant="brand-outline" data-testid="btn-analyze-position" onClick={handleAnalyzePosition}>Analyze</Button>
```

## State of the Art

| Old Approach | Current Approach | When | Impact |
|--------------|------------------|------|--------|
| All pages eagerly imported in `App.tsx` | First `React.lazy` + `<Suspense>` boundary (`/analysis`) | Phase 138 | Engine chunk + WASM stay off other routes (ROUTE-01) |
| Tactic exploration via `TacticLineExplorer` modal | Standalone `/analysis` route | 138 (route) / 139 (tactic subsume) | Shared board surface; modal retired in 139 |

**Deprecated/outdated:** ARCHITECTURE.md's `new Worker('/stockfish-18-lite-single.js')` (root path) — superseded by the shipped `/engine/stockfish-18-lite-single.js`. Use the `/engine/` path.

## Validation Architecture

> `workflow.nyquist_validation: true` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.x (jsdom) |
| Config file | `frontend/vite.config.ts` (vitest via Vite) / project convention |
| Quick run command | `cd frontend && npm test -- --run src/pages/__tests__/Analysis.test.tsx` |
| Full suite command | `cd frontend && npm test -- --run` |
| Type/lint gate | `cd frontend && npx tsc -b && npm run lint && npm run knip` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| ROUTE-01 | Lazy chunk: stockfish JS/WASM not referenced by non-analysis chunks | build-output assertion | `npm run build` then grep `dist/assets` — `stockfish`/engine refs only in the Analysis chunk | ❌ Wave 0 (optional script) |
| ROUTE-01 | `/analysis` renders shell with all testids | unit (jsdom, mocked engine) | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | ❌ Wave 0 |
| ROUTE-02 | `?fen=` seeds board root; empty → start | unit | same file | ❌ Wave 0 |
| ROUTE-02 | "Analyze position" navigates with encoded FEN | unit (Openings) | `npm test -- --run src/pages/__tests__/Openings*.test.tsx` | ⚠️ extend existing Openings test |
| ENGINE-04/D-06 | board interactive while `isReady===false`; "Loading engine…" shown | unit (mock engine `isReady:false`) | Analysis.test.tsx | ❌ Wave 0 |
| PLAT-01/SC#4 | no COOP/COEP headers; WASM MIME `application/wasm` | CI (already present) | `.github/workflows/ci.yml` "No COOP/COEP header guard + WASM MIME check" | ✅ exists (Phase 136) |

**jsdom note:** jsdom has no real `Worker` for the classic engine file. The page test **must mock `useStockfishEngine`** (e.g. `vi.mock('@/hooks/useStockfishEngine', …)` returning a fixed `StockfishEngineState`) to drive `isReady`/`pvLines` states deterministically. The real worker is exercised by Phase 136's integration test, not here.

### Sampling Rate
- **Per task commit:** `npm test -- --run src/pages/__tests__/Analysis.test.tsx` + `npx tsc -b`
- **Per wave merge:** full frontend suite + `npm run lint` + `npm run knip`
- **Phase gate:** pre-merge gate (CLAUDE.md): `npm run lint && npm test -- --run` green; **plus** the manual UAT gate below.

### Wave 0 Gaps
- [ ] `frontend/src/pages/__tests__/Analysis.test.tsx` — covers ROUTE-01/02, D-06 (mock engine + MemoryRouter). Use existing page tests (`Endgames.readinessGate.test.tsx`, `Openings.statsBoard.test.tsx`) as the harness pattern (`MemoryRouter` + `QueryClientProvider`).
- [ ] (optional) a build-grep assertion or documented manual Network-tab check for the lazy boundary (ROUTE-01 SC#1) — jsdom cannot prove lazy fetch.
- [ ] Extend an Openings test (or add one) asserting the "Analyze position" button calls `navigate` with `/analysis?fen=<encoded>`.

### Manual UAT gate (carried from Phase 137, this is 138's gate)
- **On-device eyeballing (iOS Safari / low-end Android):** render `/analysis`, confirm `EvalBar`/`EngineLines`/`VariationTree` display correctly, board+stepper interactive during WASM init, engine eval updates within ~3 s (D-06, SC#3). Deferred from 137 → **owned by 138**.
- **Lazy-boundary Network check (SC#1):** DevTools Network tab — visit `/library`, `/openings`, `/endgames`; confirm **no** request for `stockfish-18-lite-single.js` or `.wasm`; then visit `/analysis` and confirm the engine fetches fire exactly once.
- **`window.crossOriginIsolated === false` on `/analysis`** (SC#4) — type it in the console.
- **Full Google OAuth sign-in** completes from any page (SC#4 / PLAT-01) — the CI header guard covers the static check; the live OAuth flow is a manual confirm.

## Security Domain

> `security_enforcement` default-enabled. Frontend-only, no new attack surface beyond a URL param.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `?fen=` is untrusted input. `useAnalysisBoard` passes it to `new Chess(fen)` (chess.js) which **throws on malformed FEN**. Wrap the initial parse / guard so a bad `fen` param degrades to `STARTING_FEN` instead of crashing the page. `makeMove` already try/catches chess.js. |
| V5 Output Encoding (XSS) | yes | All engine/SAN strings render as React children (auto-escaped). `EngineLines`/`VariationTree` headers note this (T-137-03 mitigated). No `dangerouslySetInnerHTML`. |
| V4 Access Control | yes | Route inside `ProtectedLayout` (token gate). No new endpoint. |
| V2/V3 Auth/Session | no | Reuses existing auth; PLAT-01 ensures COOP/COEP absence keeps OAuth working. |
| V6 Cryptography | no | None. |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed `?fen=` crashes page | Denial of Service | Validate/guard FEN → fallback to `STARTING_FEN`; wrap `new Chess(fen)` |
| Engine PV / SAN string injection | Tampering/XSS | React auto-escaping (already in 137 components) — do not bypass |
| Accidental SAB/COOP/COEP regression | Spoofing OAuth/iOS breakage | Single-thread engine; CI header guard (PLAT-01) — do not add headers |

**Action for planner:** add an explicit FEN-guard task — `Analysis.tsx` should validate the `fen` param (try `new Chess(fen)` once, catch → `undefined`) before handing it to `useAnalysisBoard`, so a hand-typed bad URL renders the standard start, not a crash. `[VERIFIED: useAnalysisBoard constructs Chess(initialRootFen) lazily only inside makeMove/loadMainLine, but getPosition returns rootFen directly — an invalid rootFen would surface to ChessBoard/react-chessboard and likely throw at render]`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rootPly` from FEN = `(fullmove-1)*2 + (side==='b'?1:0)` is the right move-number anchor for opening-position entries | Composition Contract | Move numbers in `VariationTree`/`EngineLines` mislabeled; cosmetic, caught in UAT. Fallback `rootPly={0}` if deemed out of scope. |
| A2 | `/analysis` should be auth-only (inside `ProtectedLayout`) and NOT behind `ImportRequiredRoute` | Pattern A | If wrong, zero-game users are blocked from free-play analysis. Confirm with user; safe default = auth-only. |
| A3 | Keying the lazy route element by `fen` (Pitfall 2 option a) is acceptable to force board reset on re-entry | Pitfall 2 | If the team prefers a `useEffect` reset, swap approach; both are correct. |
| A4 | An invalid `?fen=` would throw at render via react-chessboard, so a guard is needed | Security Domain | If react-chessboard tolerates bad FENs silently, the guard is belt-and-suspenders (still recommended). |

**Note:** A1–A4 are implementation-shape choices, not blocking unknowns. None require a backend or external confirmation; all are resolvable by the planner + UAT.

## Open Questions (RESOLVED)

Both questions were implementation-shape choices, not blocking unknowns. Resolved during planning (Plan 138-02):

1. **Engine best-move arrow on the board (discretion).** RESOLVED → planned as an OPTIONAL discretion task in Plan 138-02 ("ship only if cheap"), not a gate. ARCHITECTURE.md mentions an engine PV arrow via `ChessBoard.arrows`; `engine.pvLines[0].moves[0]` is the best move (UCI). Low cost (slice `pvLines[0].moves[0]`). Tactic-mode arrows remain explicitly Phase 139.

2. **Move-number fidelity from arbitrary opening FENs (A1).** RESOLVED → Plan 138-02 ships the **FEN-derived `rootPly`** (small, correct) rather than the `rootPly={0}` shortcut. Cosmetic-only if wrong, caught at UAT.

## Sources

### Primary (HIGH confidence — direct source reads this session)
- `frontend/src/hooks/useStockfishEngine.ts` — full return shape, `fen`/`enabled` inputs, `/engine/` path, lifecycle
- `frontend/src/hooks/useAnalysisBoard.ts` — full return contract, non-reactive `initialRootFen`, no `reset()`, `loadMainLine([], fen)` reset behavior, `containerRef`
- `frontend/src/components/analysis/{EvalBar,EngineLines,VariationTree}.tsx` — exact props + testids + "Phase 138 handles engine-loading chrome" comment
- `frontend/src/components/board/ChessBoard.tsx` — `id`/arrows/props
- `frontend/src/pages/Openings.tsx` + `openings/ExplorerTab.tsx` — `chess.position` source, button surfaces
- `frontend/src/App.tsx` — routing, `ProtectedLayout`, `ROUTE_TITLES`, all-named-exports fact
- `frontend/vite.config.ts` — `optimizeDeps.exclude: ['stockfish']`, PWA `globIgnores: ['**/*.wasm']`
- `.github/workflows/ci.yml` — COOP/COEP + WASM MIME guard (PLAT-01)
- `frontend/public/engine/` — verified binaries present
- `.planning/REQUIREMENTS.md` — ROUTE-01/02, PLAT-01, ENGINE-04 status

### Secondary (project research docs)
- `.planning/research/ARCHITECTURE.md` §Pattern 5, §Pattern 6, App.tsx minimal-change note, Phase-3 build sequence
- `.planning/research/PITFALLS.md` Pitfalls 3, 4, 8, 10 (engine lifecycle, lazy-load UX, COOP/COEP)
- `.planning/phases/138-…/138-CONTEXT.md` (locked decisions)

## Metadata

**Confidence breakdown:**
- Composition contract: HIGH — every signature read from source this session
- Architecture (lazy/Suspense, entry point): HIGH — App.tsx + Openings.tsx inspected; mechanism is standard Vite/React Router
- Pitfalls: HIGH — derived from the actual hook implementations (non-reactive initialRootFen, missing reset, container focus) + verified PITFALLS.md

**Research date:** 2026-06-26
**Valid until:** ~2026-07-26 (stable; only invalidated if 136/137 deliverable signatures change before 138 executes)
</content>
</invoke>

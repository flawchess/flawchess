# Phase 138: `/analysis` Route + Page Shell + Entry Points - Pattern Map

**Mapped:** 2026-06-26
**Files analyzed:** 4 (2 new, 2 modified)
**Analogs found:** 4 / 4 (all role-matched; one with a deliberate export/lazy divergence flagged)

> RESEARCH.md already contains the verified composition contract (hook/component signatures) and
> a "Prior-art in the codebase" list. This map does NOT re-derive those. It pins the **concrete
> existing files + line ranges** the new code copies its *shape* from: page layout, the
> secondary-button + `navigate()` idiom, the route-registration block, and the full-page test
> harness. For prop wiring, defer to RESEARCH.md "Exact Composition Contract".

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/pages/Analysis.tsx` | page (component) | event-driven (engine stream) + request-response (URL param) | `pages/Openings.tsx` (board+controls+side-panel column layout) | role-match (see export divergence) |
| `frontend/src/App.tsx` | route / config | request-response (router) | `frontend/src/App.tsx` itself (existing `<Route>` + `ROUTE_TITLES` blocks) | exact (self) — **no lazy analog exists** |
| `frontend/src/pages/Openings.tsx` | page (entry button) | request-response (`navigate`) | same file — existing `variant="brand-outline"` `<Button onClick={navigate(...)}>` idiom | exact (in-file) |
| `frontend/src/pages/__tests__/Analysis.test.tsx` | test | n/a (jsdom render) | `pages/__tests__/Endgames.readinessGate.test.tsx` | exact (full-page harness) |

---

## Pattern Assignments

### `frontend/src/pages/Analysis.tsx` (page, event-driven + request-response) — NEW

**Analog:** `frontend/src/pages/Openings.tsx` (board column structure) + `frontend/src/pages/Endgames.tsx` (page wrapper container).

> The actual hook/component prop wiring is in RESEARCH.md §"Exact Composition Contract" and
> §"System Architecture Diagram" — copy from there, not from memory. This section pins the
> **layout shape** and the local idioms (page wrapper, board-in-ref-div, BoardControls reset
> wiring, secondary-button placement) from real files.

**CRITICAL export divergence (Pitfall 1):** every existing page uses a **named** export
(`export function OpeningsPage()`, `export function EndgamesPage()` — see `App.tsx:24-31`
import block). `Analysis.tsx` MUST `export default` for `React.lazy` to resolve. This is the
one place where copying the page analog's surface verbatim is wrong.

**Page wrapper container pattern** — copy from `Endgames.tsx:810-812`:
```tsx
return (
  <div data-testid="endgames-page" className="flex min-h-0 flex-1 flex-col bg-background">
    <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6">
```
For Analysis: use `data-testid="analysis-page"` (the Wave-0 smoke test asserts this testid; see
Pitfall 1 in RESEARCH).

**Board + controls column pattern** — copy the structure from `Openings.tsx:917-954` (desktop)
and `Openings.tsx:1042-1060` (mobile board+controls stack). Note how `ChessBoard` and
`BoardControls` are siblings inside a `flex flex-col` column, with the explorer/side panel as a
sibling `flex-1 min-w-0` column:
```tsx
<div className="flex flex-row items-start gap-6">
  <div className={getBoardContainerClassName(activeTab)} data-testid="openings-board-container">
    <ChessBoard
      position={chess.position}
      onPieceDrop={chess.makeMove}
      flipped={boardFlipped}
      lastMove={chess.lastMove}
      arrows={boardArrows}
    />
    <BoardControls
      onBack={chess.goBack}
      onForward={chess.goForward}
      onReset={() => { chess.reset(); setGamesOffset(0); }}
      onFlip={() => setBoardFlipped((f) => !f)}
      canGoBack={chess.currentPly > 0}
      canGoForward={chess.currentPly < chess.moveHistory.length}
      infoSlot={ /* optional InfoPopover */ }
    />
    ...
  </div>
  <div className="flex-1 min-w-0"> {/* side panel: EngineLines + VariationTree */} </div>
</div>
```
**Divergence for Analysis (from RESEARCH Pitfall 4):** `useAnalysisBoard` has **no `reset()`** and
**no `currentPly`/`moveHistory`**. Adapt the `BoardControls` wiring to:
```tsx
onReset={() => board.loadMainLine([], board.rootFen)}   // empty SAN array = reset to root
canGoBack={board.currentNodeId !== null}
canGoForward={/* leave true or compute child parity; hook no-ops with no child */}
```
And wrap the board in `ref={board.containerRef}` for the ArrowLeft/Right keys (RESEARCH Pitfall 5)
— `Openings` does not use this ref, so this is a `useAnalysisBoard`-specific addition.

**`BoardControls` interface** (`components/board/BoardControls.tsx:5-22`) — reuse as-is, has
`infoSlot`, `vertical`, `size`, `buttonClassName`; testids `board-btn-{reset,back,forward,flip}`
are already set. No new board-control component needed.

**EvalBar / EngineLines / VariationTree** — props verified in RESEARCH §"Exact Composition
Contract". Real testids confirmed from source: `EvalBar.tsx:70` → `data-testid="analysis-eval-bar"`
(white always top, `className` overridable for layout — `EvalBar.tsx:48-54`); `EngineLines.tsx`
header comment (lines 9-13) explicitly states **"Phase 138 handles engine-loading chrome"** —
i.e. the `"Loading engine…"` state when `engineEnabled && !engine.isReady` is the page's job, not
the component's. `EngineLines` renders empty when `!isAnalyzing && pvLines.length === 0`.

**Theme tokens:** `EvalBar` already imports `EVAL_BAR_WHITE/BLACK` from `@/lib/theme`
(`EvalBar.tsx:11`). The page must not hard-code semantic colors (CLAUDE.md) — use `theme.ts`
tokens or `text-muted-foreground` utility classes (as `App.tsx:489` does for loading states).

**Security guard (RESEARCH §Security Domain):** wrap the `?fen=` param in a `try { new Chess(fen) }
catch → undefined` before passing to `useAnalysisBoard`, so a malformed hand-typed FEN degrades to
`STARTING_FEN` instead of throwing at render. `Openings.tsx:241` shows the `new Chess(chess.position)`
construction idiom (chess.js already a dep).

---

### `frontend/src/App.tsx` (route / config) — MODIFIED

**Analog:** the file itself. **No `React.lazy`/`Suspense` exists anywhere in the app yet — this is
the first lazy boundary (confirmed: `App.tsx:24-35` imports every page eagerly with named
imports).** Flag for planner: there is no in-repo lazy analog to copy; follow RESEARCH §"Pattern A"
which gives the exact snippet.

**Existing eager-import block** (`App.tsx:24-31`) — shows the named-export convention the new lazy
import deliberately breaks from:
```tsx
import { OpeningsPage } from '@/pages/Openings';
import { EndgamesPage } from '@/pages/Endgames';
import { AdminPage } from '@/pages/Admin';
```
Add (per RESEARCH Pattern A — do NOT convert these existing imports):
```tsx
import { lazy, Suspense } from 'react';
const AnalysisPage = lazy(() => import('./pages/Analysis'));  // default export required
```

**`ROUTE_TITLES` block** (`App.tsx:78-83`) — add one entry:
```tsx
const ROUTE_TITLES: Record<string, string> = {
  '/library': 'Library',
  '/openings': 'Openings',
  '/endgames': 'Endgames',
  '/admin': 'Admin',
  '/analysis': 'Analysis',   // ← add
};
```
Lookup in `MobileHeader` (`App.tsx:207-209`) uses `pathname.startsWith(path)` — `/analysis` is
unambiguous. **No nav item** (D-05): do NOT add to `NAV_ITEMS` (`App.tsx:60-64`),
`BOTTOM_NAV_ITEMS`, or the `isActive` helper (`App.tsx:87-92`).

**Route registration block** (`App.tsx:608-618`, inside `<Route element={<ProtectedLayout />}>`):
```tsx
<Route element={<ProtectedLayout />}>
  <Route path="/library/*" element={<LibraryPage .../>} />
  ...
  <Route path="/openings/*" element={<ImportRequiredRoute><OpeningsPage /></ImportRequiredRoute>} />
  <Route path="/endgames/*" element={<ImportRequiredRoute><EndgamesPage /></ImportRequiredRoute>} />
  <Route path="/admin" element={<SuperuserRoute><AdminPage /></SuperuserRoute>} />
</Route>
```
Add `/analysis` here, **inside** `ProtectedLayout` but **NOT** wrapped in `ImportRequiredRoute`
(RESEARCH A2: free-play is valid for zero-game users), wrapped in `<Suspense>`:
```tsx
<Route
  path="/analysis"
  element={
    <Suspense fallback={<div className="p-6 text-muted-foreground" data-testid="analysis-loading">Loading analysis board…</div>}>
      <AnalysisPage key={searchParams.get('fen') ?? 'start'} />   {/* key = Pitfall 2 remount-on-reentry */}
    </Suspense>
  }
/>
```
The `fallback` div copies the exact loading-state idiom already used in this file at `App.tsx:489`
(`ImportRequiredRoute` loading) and `App.tsx:507` (`SuperuserRoute` loading):
`className="p-6 text-muted-foreground"` + a `data-testid`.

---

### `frontend/src/pages/Openings.tsx` (entry button) — MODIFIED

**Analog:** the same file's existing `variant="brand-outline"` secondary button + `navigate()`
idiom. `navigate` is already in scope (`Openings.tsx:115` `const navigate = useNavigate()`);
`chess.position` is the live full FEN (`Openings.tsx:132` `const chess = useChessGame()`, used at
`:920`, `:1045`). **Place the button in `Openings.tsx`, not `ExplorerTab.tsx`** —
`ExplorerTab.tsx` is a pure presentational child (`pages/openings/ExplorerTab.tsx:1-63`, no
`navigate`/`chess` in scope); threading a callback through it adds a prop for no benefit. The
board + `BoardControls` already live in `Openings.tsx` on both surfaces.

**Secondary-button idiom** (real instances in-file: `Openings.tsx:637-639`, `:1025-1026`,
`:1232-1234`):
```tsx
<Button
  variant="brand-outline"      // CLAUDE.md: secondary action = brand-outline (NOT variant="secondary")
  className="relative"
  onClick={openFilterSidebar}
  data-testid="subnav-filter-button"
  aria-label="Open filters"
>
  <SlidersHorizontal className="mr-2 h-4 w-4" />
  Filters
</Button>
```
**Navigate handler** — copy the encode idiom from RESEARCH §"Pattern C" (the only correct form;
FENs contain spaces and `/`):
```tsx
const handleAnalyzePosition = useCallback(() =>
  navigate(`/analysis?fen=${encodeURIComponent(chess.position)}`),
  [navigate, chess.position]);
```

**Mobile + desktop parity (CLAUDE.md):** the board appears on two surfaces in this file —
desktop board column (`Openings.tsx:917-954`) and the mobile board+settings-column block
(`Openings.tsx:1042-1115`, the `lg:hidden` branch at `:966`). Add the button to **both**, near the
board controls, with distinct testids (`btn-analyze-position`, `btn-analyze-position-mobile`). Icon
from `lucide-react` (the file already imports icons at `Openings.tsx:15`); a `Swords`/`Sparkles`
icon is already imported there. Only render on the explorer tab surface (the position-bearing tab).

---

### `frontend/src/pages/__tests__/Analysis.test.tsx` (test) — NEW

**Analog:** `frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx` — the canonical
full-page render harness (MemoryRouter + mock-every-heavy-hook). `Openings.statsBoard.test.tsx`
is NOT a full-page render (it tests extracted sub-trees because Openings needs 15+ hook mocks) —
use it only as a secondary reference for the `getByTestId`/`aria-label` assertion style.

**File-level pragma + imports** (`Endgames.readinessGate.test.tsx:1-14`):
```tsx
// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TooltipProvider } from '@/components/ui/tooltip';
```

**Mock the engine hook** (RESEARCH §"jsdom note": jsdom has no real `Worker`) — follow the
`vi.mock` shape from `Endgames.readinessGate.test.tsx:31-67`. Return a fixed
`StockfishEngineState` so `isReady`/`pvLines` are deterministic:
```tsx
// Drive engine states from a mutable object reset in afterEach (the readinessState idiom, :17-33).
const engineState = { evalCp: null, evalMate: null, pvLines: [], depth: 0, isAnalyzing: false, isReady: false };
vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: () => ({ ...engineState }),
}));
```

**jsdom shims** — copy verbatim from `Endgames.readinessGate.test.tsx:130-155`
(`matchMedia`, `ResizeObserverStub`, `window.scrollTo`). `react-chessboard` / responsive
components need these.

**afterEach reset** (`Endgames.readinessGate.test.tsx:157-165`): `cleanup()` + reset the mutable
mock-state object to defaults.

**Render helper + MemoryRouter initialEntries** (`Endgames.readinessGate.test.tsx:170-178`) — this
is how you seed the `?fen=` param for the ROUTE-02 test:
```tsx
function renderAnalysis(initialPath = '/analysis') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <TooltipProvider>
        <AnalysisPage />
      </TooltipProvider>
    </MemoryRouter>,
  );
}
// ROUTE-02: renderAnalysis('/analysis?fen=' + encodeURIComponent(someFen))
```
Import the page AFTER the mocks (`Endgames.readinessGate.test.tsx:167` imports `EndgamesPage`
after all `vi.mock` calls — vitest hoists `vi.mock` but the explicit late import keeps ordering
obvious). Since `Analysis.tsx` is a default export, import as
`import AnalysisPage from '../Analysis'`.

**Assertion style** (`Endgames.readinessGate.test.tsx:183-206`): `screen.getByTestId('analysis-page')`,
`screen.getByTestId('analysis-eval-bar')`, etc. For the entry-button navigation test (ROUTE-02,
Openings side) the RESEARCH map suggests extending an Openings test; assert `navigate` is called
with `/analysis?fen=<encoded>` (mock `useNavigate` from `react-router-dom`).

---

## Shared Patterns

### Loading / Suspense fallback styling
**Source:** `App.tsx:489` & `:507` (`ImportRequiredRoute` / `SuperuserRoute` loading states).
**Apply to:** the `<Suspense fallback>` in `App.tsx` and the in-page `"Loading engine…"` indicator.
```tsx
<div className="p-6 text-muted-foreground" data-testid="...-loading">Loading...</div>
```
Keep all copy `text-sm`+ (CLAUDE.md floor). The Suspense fallback gets `data-testid="analysis-loading"`.

### Secondary action button
**Source:** `Openings.tsx:637`, `:1025`, `:1232` + CLAUDE.md Frontend §"Primary vs secondary".
**Apply to:** the "Analyze position" entry button (both surfaces).
`variant="brand-outline"` — never `variant="secondary"` (reserved for neutral chips), never
hand-rolled `bg-*`/`className` colors.

### data-testid on interactive elements (Browser Automation Rules)
**Source:** every `<Button>`/`<Link>` in `App.tsx` + `Openings.tsx` carries kebab-case,
component-prefixed `data-testid` (e.g. `nav-openings`, `subnav-filter-button`, `board-btn-flip`).
**Apply to:** all new interactive elements — `btn-analyze-position`, `btn-analyze-position-mobile`,
`analysis-board` (board `id` + `data-testid`, per CLAUDE.md chess-board rule), the engine toggle,
and the page container `analysis-page`. Icon-only buttons need `aria-label` (`BoardControls.tsx:54,67,81,92`).

### Page wrapper + responsive main
**Source:** `Endgames.tsx:810-812`.
**Apply to:** `Analysis.tsx` root container (`data-testid="analysis-page"`, flex-col, max-w-7xl main).

---

## No Analog Found

| File / Concern | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `React.lazy` + `<Suspense>` boundary in `App.tsx` | route/config | request-response | **No page is currently lazy-loaded** (`App.tsx:24-35` all eager named imports). First lazy boundary in the app — no in-repo analog; follow RESEARCH §"Pattern A" exact snippet. |
| Default-exported page (`Analysis.tsx`) | page | — | Every existing page is a **named** export (`App.tsx:24-31`). `React.lazy` requires `export default` — deliberate divergence, not a copyable analog. Wave-0 smoke test guards it (Pitfall 1). |
| `useAnalysisBoard` ref + `loadMainLine([], rootFen)` reset wiring | page glue | event-driven | `Openings.tsx` board uses `useChessGame` (`reset()`, `currentPly`, `moveHistory`) — a *different* hook. The `BoardControls` reset/back/forward wiring must be adapted to the `useAnalysisBoard` contract (RESEARCH Pitfalls 4 & 5), not copied verbatim. |

---

## Metadata

**Analog search scope:** `frontend/src/pages/`, `frontend/src/pages/openings/`,
`frontend/src/pages/__tests__/`, `frontend/src/components/board/`, `frontend/src/components/analysis/`.
**Files scanned:** App.tsx, Openings.tsx, Endgames.tsx, openings/ExplorerTab.tsx,
__tests__/Endgames.readinessGate.test.tsx, __tests__/Openings.statsBoard.test.tsx,
components/board/BoardControls.tsx, components/analysis/EvalBar.tsx, components/analysis/EngineLines.tsx
(props/headers), plus directory listings of analysis/ and board/.
**Pattern extraction date:** 2026-06-26
</content>
</invoke>

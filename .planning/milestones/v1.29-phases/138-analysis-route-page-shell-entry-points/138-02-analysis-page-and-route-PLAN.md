---
phase: 138-analysis-route-page-shell-entry-points
plan: 02
type: execute
wave: 1
depends_on: [138-01]
files_modified:
  - frontend/src/pages/Analysis.tsx
  - frontend/src/App.tsx
autonomous: true
requirements: [ROUTE-01, ROUTE-02]

must_haves:
  truths:
    - "An authenticated user can reach a standalone /analysis page (inside ProtectedLayout, not behind ImportRequiredRoute)"
    - "Visiting /analysis with no params silently renders the standard start position (D-05 blank free-play)"
    - "Visiting /analysis?fen=<valid> seeds the board root to that position (SC#2)"
    - "A malformed ?fen= degrades to the standard start position without crashing the page (security FEN-guard, T-138-01)"
    - "The eval area shows 'Loading engine…' while engineEnabled && !engine.isReady; the board, move stepper, VariationTree, and BoardControls are interactive during that window (SC#3 / D-06)"
    - "MANUAL UAT — no stockfish JS/WASM network fetch on /library, /openings, /endgames; the engine fetches fire exactly once on /analysis (SC#1, lazy boundary)"
    - "MANUAL UAT — window.crossOriginIsolated === false on /analysis and the full Google OAuth flow completes from any page (SC#4 / PLAT-01)"
  artifacts:
    - path: "frontend/src/pages/Analysis.tsx"
      provides: "Default-exported Analysis page composing useStockfishEngine + useAnalysisBoard + EvalBar/EngineLines/VariationTree/ChessBoard/BoardControls with FEN-guard, engine-loading chrome, and responsive layout"
      exports: ["default"]
      contains: "export default"
      min_lines: 80
    - path: "frontend/src/App.tsx"
      provides: "First React.lazy + Suspense route boundary, /analysis route inside ProtectedLayout, and the '/analysis': 'Analysis' ROUTE_TITLES entry"
      contains: "lazy(() => import('./pages/Analysis'))"
  key_links:
    - from: "frontend/src/App.tsx"
      to: "frontend/src/pages/Analysis.tsx"
      via: "React.lazy dynamic import of the default export (Pitfall 1)"
      pattern: "lazy\\(\\(\\) => import\\('\\./pages/Analysis'\\)\\)"
    - from: "frontend/src/pages/Analysis.tsx"
      to: "frontend/src/hooks/useStockfishEngine.ts"
      via: "useStockfishEngine({ fen: engineEnabled ? board.position : null, enabled: engineEnabled })"
      pattern: "useStockfishEngine\\("
    - from: "frontend/src/pages/Analysis.tsx"
      to: "frontend/src/hooks/useAnalysisBoard.ts"
      via: "useAnalysisBoard(guardedFen) — FEN-guarded root seed"
      pattern: "useAnalysisBoard\\("
---

<objective>
Build the standalone `/analysis` page (`frontend/src/pages/Analysis.tsx`, default export) by composing the already-built Phase 136/137 pieces, and wire it into the router (`frontend/src/App.tsx`) as the app's FIRST `React.lazy` + `<Suspense>` boundary so the stockfish bundle stays off every other route (ROUTE-01). The page reads the `?fen=` entry param (FEN-guarded), seeds the board, runs the engine on by default with a "Loading engine…" state in the eval area while WASM initializes, and keeps the board fully interactive throughout (ROUTE-02, SC#2/SC#3, D-05/D-06).

Purpose: This is the phase's load-bearing deliverable — it finally renders the engine output on a real route and carries the on-device verification gate deferred from Phase 137.
Output: `Analysis.tsx` (new, default export) + three localized edits to `App.tsx`. Turns Plan 01's test scaffold green.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-RESEARCH.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-PATTERNS.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-UI-SPEC.md
@frontend/src/hooks/useStockfishEngine.ts
@frontend/src/hooks/useAnalysisBoard.ts
@frontend/src/components/analysis/EvalBar.tsx
@frontend/src/components/analysis/EngineLines.tsx
@frontend/src/components/analysis/VariationTree.tsx
@frontend/src/components/board/ChessBoard.tsx
@frontend/src/components/board/BoardControls.tsx
</context>

<artifacts_produced>
NEW symbols/files created by this plan (exclude from drift verification):
- `frontend/src/pages/Analysis.tsx` — new, **default-exported** `Analysis` page component. Owns testids `analysis-page`, `analysis-board` (+ `id="analysis-board"`), `analysis-engine-loading`, `btn-analysis-engine-toggle` (and re-uses child testids `analysis-eval-bar`, `analysis-engine-lines`, `analysis-variation-tree`, `board-btn-*`).
- In `frontend/src/App.tsx`: the `AnalysisPage = lazy(() => import('./pages/Analysis'))` binding, the new `<Route path="/analysis">` element (Suspense fallback testid `analysis-loading`), an `AnalysisRoute` wrapper component (reads `useSearchParams`, keys the page by `fen` per Pitfall 2), and the `'/analysis': 'Analysis'` `ROUTE_TITLES` entry.
- No new npm packages; no nav-bar item (D-05).
</artifacts_produced>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Build the Analysis page shell (default export, composition + FEN-guard + engine-loading)</name>
  <files>frontend/src/pages/Analysis.tsx</files>
  <behavior>
    - Renders `analysis-page`, `analysis-board`, `analysis-eval-bar` on a no-param visit, showing the standard start position (D-05).
    - `?fen=<valid>` seeds the board root to that FEN; `?fen=<malformed>` falls back to the standard start with no throw (T-138-01).
    - With engine `isReady === false`, `analysis-engine-loading` ("Loading engine…") is shown in the eval area while `analysis-board` stays present and interactive (SC#3 / D-06).
    - These are exactly the cases asserted by `frontend/src/pages/__tests__/Analysis.test.tsx` (Plan 01) — this task turns that file green.
  </behavior>
  <read_first>
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-RESEARCH.md` §"Exact Composition Contract" (the verified return shapes + prop names — copy wiring from here, NOT memory), §"System Architecture Diagram" (the exact compose order), §"Common Pitfalls" 1-6, and §"Security Domain" (the FEN-guard requirement + the `(fullmove-1)*2 + (side==='b'?1:0)` rootPly formula).
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-PATTERNS.md` §"frontend/src/pages/Analysis.tsx" (page-wrapper from `Endgames.tsx:810-812`; board+controls column from `Openings.tsx:917-954`; the `useAnalysisBoard`-specific reset/ref divergences; the FEN-guard idiom `Openings.tsx:241`).
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-UI-SPEC.md` §"Page Composition Contract" (desktop vs mobile layout), §"Engine-loading & on/off states", §"Copywriting Contract" (exact copy: "Loading engine…", "Engine off"), §"Interaction & Accessibility Contract" (testid + aria table).
    - `frontend/src/hooks/useStockfishEngine.ts` and `frontend/src/hooks/useAnalysisBoard.ts` (the real return contracts — note: no `reset()`, non-reactive `initialRootFen`, `containerRef`).
    - `frontend/src/components/board/BoardControls.tsx` (the `infoSlot`/`vertical`/`size` props + existing `board-btn-*` testids).
  </read_first>
  <action>
    Create `Analysis.tsx` and `export default function Analysis()` — a DEFAULT export (every other page is a named export; `React.lazy` resolves only a default — Pitfall 1). Read the entry param with `useSearchParams`: `const fenParam = searchParams.get('fen') ?? undefined` (React Router returns the decoded value).

    Apply the security FEN-guard BEFORE handing the param to the board: attempt `new Chess(fenParam)` inside a try/catch when `fenParam` is set; on throw, fall back to `undefined` so `useAnalysisBoard` defaults to its `STARTING_FEN` (T-138-01 — a malformed hand-typed URL must render the start position, never crash at render). chess.js is already a dependency. Pass the guarded value to `useAnalysisBoard(guardedFen)`.

    Mount both hooks unconditionally (hooks cannot be conditional — toggle via args, never by skipping the call). Hold `const [engineEnabled, setEngineEnabled] = useState(true)` (D-06 engine on by default). Call `useStockfishEngine({ fen: engineEnabled ? board.position : null, enabled: engineEnabled })`. Derive `const engineLoading = engineEnabled && !engine.isReady`. Do NOT re-implement the debounce, stop/go, MultiPV, or stale-eval logic — those live in the hook (anti-pattern to duplicate).

    Compose the layout per the UI-SPEC Page Composition Contract:
    - Root wrapper: a `<main>` landmark with `data-testid="analysis-page"`, the `Endgames.tsx` page-wrapper container classes (flex-col, `max-w-7xl`, responsive padding). Do NOT render an `<h1>` analysis title (D-05; `ROUTE_TITLES` drives the mobile header).
    - `EvalBar` (props `evalCp`, `evalMate`, `depth` from `engine`; `className` to match board height on desktop / a thin variant on mobile). White always at top (no `orientation` prop). Desktop: flush-left of the board, `gap-2`. Mobile: stacked above the board, reduced height (Pitfall 6 — never beside the board on mobile).
    - `ChessBoard` with `id="analysis-board"` and `data-testid="analysis-board"` (CLAUDE.md board rule — drives stable square ids + drag/click moves), `position={board.position}`, `onPieceDrop={board.makeMove}`, `lastMove={board.lastMove}`, `flipped` from a local flip state. WRAP the board in a `<div ref={board.containerRef} tabIndex={0}>` so the container-scoped ArrowLeft/ArrowRight handler fires (Pitfall 5 — `tabIndex={0}` is the cheap safety net).
    - `BoardControls` directly under the board: `onBack={board.goBack}`, `onForward={board.goForward}`, `onReset={() => board.loadMainLine([], board.rootFen)}` (Pitfall 4 — there is NO `reset()`; empty SAN array clears the tree to root), `canGoBack={board.currentNodeId !== null}`, `canGoForward` left enabled (the hook no-ops with no child), `onFlip` toggling the local flip state. Put the engine on/off toggle in the `infoSlot`: an icon-only button with `data-testid="btn-analysis-engine-toggle"`, `aria-label="Toggle engine"`, `aria-pressed={engineEnabled}`, calling `setEngineEnabled(v => !v)`. Use `Button` variants from `components/ui/button.tsx` — never hand-rolled colors.
    - Side panel (desktop right column, `--card` surface, `gap-4`; mobile below the controls): `EngineLines` (`pvLines`, `depth`, `isAnalyzing` from `engine`; `startPly={rootPly}`; `onMoveClick={board.makeMove}`) above `VariationTree` (`nodes`, `mainLine`, `currentNodeId` from `board`; `rootPly`; `onNodeClick={board.goToNode}`). Both components self-handle their own responsive desktop/mobile rendering.
    - Engine-area state machine: render `analysis-engine-loading` with the exact copy "Loading engine…" (`text-sm text-muted-foreground`, optional `Loader2` `animate-spin`) when `engineLoading`; render a calm "Engine off" rest text (no spinner) when `!engineEnabled`; otherwise let `EngineLines` show its own internal "Analyzing…" spinner / lines. The "Loading engine…" chrome is the PAGE's job (EngineLines renders empty when `!isAnalyzing && pvLines.length===0`).

    Derive `rootPly` from the guarded FEN with the standard formula: split the FEN, take side-to-move and fullmove, `rootPly = (Number(fullmove) - 1) * 2 + (side === 'b' ? 1 : 0)`; default `0` for the standard start. Pass `rootPly` to `VariationTree` (`rootPly`) and `EngineLines` (`startPly`) so move numbers match an opening-position entry. If parsing yields `NaN`, fall back to `0`.

    Honor CLAUDE.md frontend rules throughout: `noUncheckedIndexedAccess` (narrow every FEN-split index access before use), `text-sm` floor on all copy, theme tokens / `text-muted-foreground` only — no hard-coded semantic colors (EvalBar/board already own their palettes), semantic `<button>`/`<main>`, `data-testid` on every interactive element. OPTIONAL discretion (not a gate): an engine best-move arrow via `ChessBoard.arrows` from `engine.pvLines[0].moves[0]` (sliced UCI → from/to) — ship only if cheap; tactic-mode arrows are explicitly Phase 139.
  </action>
  <acceptance_criteria>
    - `frontend/src/pages/Analysis.tsx` contains `export default` (grep: `export default`), and does NOT use a bare named `export function AnalysisPage`.
    - The FEN-guard exists: a `new Chess(` call inside a try/catch guarding `fenParam` before `useAnalysisBoard`; malformed FEN path resolves to `undefined`/start (Plan 01 malformed-FEN test passes).
    - `useStockfishEngine` is called once with `fen: engineEnabled ? board.position : null` and `enabled: engineEnabled` (engine never conditionally mounted).
    - `BoardControls onReset` calls `board.loadMainLine([], board.rootFen)` (grep: `loadMainLine\(\[\], `); there is no reference to a non-existent `board.reset`.
    - The board is wrapped in a `ref={board.containerRef}` div; `id="analysis-board"` and `data-testid="analysis-board"` both present.
    - Engine toggle button has `data-testid="btn-analysis-engine-toggle"`, `aria-label`, and `aria-pressed`.
    - `analysis-engine-loading` renders "Loading engine…" only when `engineEnabled && !engine.isReady`; board renders regardless of `isReady`.
    - `cd frontend && npm test -- --run src/pages/__tests__/Analysis.test.tsx` is GREEN (all Plan 01 cases pass).
    - `cd frontend && npx tsc -b` passes with zero errors; `npm run lint` and `npm run knip` clean (the default export IS imported by App.tsx Task 2 — no dead export).
  </acceptance_criteria>
  <verify>
    <automated>cd frontend && npm test -- --run src/pages/__tests__/Analysis.test.tsx && npx tsc -b</automated>
  </verify>
  <done>The `/analysis` page renders the composed shell; `?fen=` seeds the board, malformed `?fen=` degrades to start, and the engine-loading chrome shows while the board stays interactive. Plan 01's scaffold is fully green and `tsc -b` is clean.</done>
</task>

<task type="auto">
  <name>Task 2: Wire /analysis into the router as the first lazy + Suspense boundary</name>
  <files>frontend/src/App.tsx</files>
  <read_first>
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-PATTERNS.md` §"frontend/src/App.tsx" — the exact edit points: eager-import block (`App.tsx:24-31`, the named-export convention this lazy import deliberately breaks), `ROUTE_TITLES` block (`App.tsx:78-83`), the route-registration block inside `<Route element={<ProtectedLayout />}>` (`App.tsx:608-618`), and the loading-state idiom (`App.tsx:489`, `:507`) the Suspense fallback copies.
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-RESEARCH.md` §"Pattern A" (the lazy/Suspense snippet, auth-only placement, no `ImportRequiredRoute`, no nav item) and §"Pitfall 2" (key the route element by `fen` so re-entry remounts).
    - `frontend/src/App.tsx` lines 517-630 (`AppRoutes()` renders `<Routes>` at ~598; note `useSearchParams` is NOT currently in scope there).
  </read_first>
  <action>
    Make three localized edits to `App.tsx`; do NOT convert the existing eager page imports.

    1. Add `import { lazy, Suspense } from 'react'` (merge into the existing react import if present) and, near the other page bindings, `const AnalysisPage = lazy(() => import('./pages/Analysis'))`. This is the app's first lazy boundary and the phase's acceptance spine (D-07) — the engine chunk + WASM ride inside the Analysis chunk and stay off every other route (ROUTE-01 / SC#1). Do not add `manualChunks` or touch `vite.config.ts`.

    2. Add `'/analysis': 'Analysis'` to the `ROUTE_TITLES` map. Do NOT add `/analysis` to `NAV_ITEMS`, `BOTTOM_NAV_ITEMS`, or the `isActive` helper (D-05 — no nav item; `ROUTE_TITLES` only drives the mobile header title).

    3. Register the route INSIDE `<Route element={<ProtectedLayout />}>` (authenticated users — SC#1) but NOT wrapped in `ImportRequiredRoute` (free-play is valid for zero-game users — D-05/RESEARCH A2) and NOT in `SuperuserRoute`. Wrap the element in `<Suspense>` with a fallback `<div className="p-6 text-sm text-muted-foreground" data-testid="analysis-loading">Loading analysis board…</div>` (copies the existing loading-state idiom). To satisfy Pitfall 2 (re-entry from a second `?fen=` must remount because `useAnalysisBoard`'s `initialRootFen` is non-reactive), key the page by the fen param. Because `useSearchParams` is not in scope at the `<Routes>` site, introduce a tiny local wrapper component (e.g. `AnalysisRoute`) that calls `const [params] = useSearchParams()` and renders `<Suspense fallback=…><AnalysisPage key={params.get('fen') ?? 'start'} /></Suspense>`, then use `element={<AnalysisRoute />}` for `path="/analysis"`. The scoped wrapper keeps the param-driven re-render off the other routes. Do NOT add COOP/COEP headers or a multi-thread engine build (PLAT-01 — CI-guarded; `window.crossOriginIsolated` must stay false).
  </action>
  <acceptance_criteria>
    - `App.tsx` contains `lazy(() => import('./pages/Analysis'))` and `import { lazy, Suspense }` (or merged) — grep both.
    - `ROUTE_TITLES` contains `'/analysis': 'Analysis'`; `NAV_ITEMS`/`BOTTOM_NAV_ITEMS` do NOT contain `/analysis` (D-05).
    - The `/analysis` `<Route>` is inside the `ProtectedLayout` block, wrapped in `<Suspense>` with fallback testid `analysis-loading`, and is NOT wrapped in `ImportRequiredRoute` or `SuperuserRoute`.
    - The route element is keyed by the `fen` search param (grep: `key={` near `AnalysisPage`); a wrapper component or in-scope `useSearchParams` provides it.
    - No COOP/COEP header added; no `vite.config.ts` / `manualChunks` change in this plan.
    - `cd frontend && npx tsc -b && npm run lint && npm run knip` all clean.
  </acceptance_criteria>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm run knip</automated>
    <human-check>
      Real-browser UAT gate (jsdom cannot prove these — run before /gsd-verify-work):
      - SC#1 lazy boundary: DevTools → Network, visit /library, /openings, /endgames → NO `stockfish-18-lite-single.js`/`.wasm` request; then /analysis → engine `.js` + `.wasm` fetch fire exactly once.
      - SC#3 + carried-from-137 on-device eyeball: first /analysis load shows "Loading engine…" in the eval area while board, stepper, VariationTree, BoardControls are immediately interactive and eval updates within ~3s; EvalBar/EngineLines/VariationTree render legibly on iOS Safari / low-end Android (text-sm floor).
      - SC#2 entry: /analysis?fen=<url-encoded mid-opening FEN> loads that position; a malformed ?fen= silently renders the start, no crash.
      - SC#4 / PLAT-01: console `window.crossOriginIsolated` is `false` on /analysis; full Google OAuth sign-in completes from /analysis and one other page.
    </human-check>
  </verify>
  <done>`/analysis` is a reachable, auth-only, lazy-loaded route with a Suspense fallback and a fen-keyed remount; no nav item, no header regression, no bundler change. Manual UAT gate (SC#1/#3/#4) documented for /gsd-verify-work.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| URL query → page | The `?fen=` param is untrusted, hand-editable input crossing into `useAnalysisBoard` → react-chessboard render. |
| Web Worker → DOM | Engine PV/SAN strings flow from the Stockfish Worker into rendered React children. |
| Site headers → browser isolation | COOP/COEP presence toggles `crossOriginIsolated`, which gates SharedArrayBuffer and breaks Google OAuth + iOS Safari. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-138-01 | Denial of Service | `?fen=` param → `Analysis.tsx` render | mitigate | Guard the param with `try { new Chess(fenParam) } catch → undefined` before `useAnalysisBoard`, so a malformed FEN renders the standard start position instead of throwing at render. Asserted by Plan 01's malformed-FEN test (automated) + checkpoint step 4. |
| T-138-02 | Tampering / XSS | Engine PV/SAN strings in `EngineLines`/`VariationTree` | mitigate | Render all engine/SAN strings as React children (auto-escaped); no `dangerouslySetInnerHTML`. Inherited from the Phase 137 components (T-137-03) — do not bypass. |
| T-138-03 | Spoofing (OAuth) / DoS (iOS) | `App.tsx` route + any header change | mitigate | Single-thread engine only; add no COOP/COEP headers and no multi-thread build. `window.crossOriginIsolated` must stay `false`; the Phase-136 CI header guard (PLAT-01) stays green. Verified by checkpoint step 5. |
| T-138-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs this phase — verified RESEARCH.md §"Package Legitimacy Audit" (zero new packages; `stockfish` 18.0.8 vetted in Phase 136, binaries already committed). No legitimacy checkpoint required. |
</threat_model>

<verification>
- Automated: `npm test -- --run src/pages/__tests__/Analysis.test.tsx` green; `npx tsc -b && npm run lint && npm run knip` clean.
- Manual (checkpoint): SC#1 lazy-fetch boundary, SC#3 on-device interactivity + engine-loading, SC#2 entry seeding, SC#4 `crossOriginIsolated===false` + OAuth.
</verification>

<success_criteria>
- ROUTE-01: `/analysis` reachable by authenticated users; stockfish JS/WASM fetched only on this route (manual Network confirm).
- ROUTE-02 (opening-position scope): `?fen=` seeds the board to the supplied position; empty/malformed → standard start.
- SC#3 / D-06: engine on by default; "Loading engine…" in the eval area while WASM inits; board + stepper interactive throughout.
- SC#4 / PLAT-01: `crossOriginIsolated === false`; OAuth completes; no headers added.
</success_criteria>

<output>
Create `.planning/phases/138-analysis-route-page-shell-entry-points/138-02-SUMMARY.md` when done.
</output>

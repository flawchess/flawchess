# Project Research Summary

**Project:** FlawChess v1.29 — Live-Engine Analysis Page
**Domain:** In-browser single-thread WASM Stockfish, branching move tree, tactic-mode overlay
**Researched:** 2026-06-26
**Confidence:** HIGH

## Executive Summary

v1.29 adds a standalone `/analysis` page backed by a live in-browser Stockfish engine running as a Web Worker. All four research files agree on the convergent architecture: `stockfish` npm v18 (`stockfish-18-lite-single.js` + `.wasm`, ~7 MB, single-thread NNUE, no CORS headers required), vendored into `public/engine/` as static assets (not processed by Vite), loaded via plain `new Worker('/engine/stockfish-18-lite-single.js')`. This is the only build that gives NNUE strength in a single-thread form that works on iOS Safari without COOP/COEP headers. The full single-thread build is ~30-100 MB and has no NNUE (HCE only), making it paradoxically weaker than the lite build despite its size.

The feature is almost entirely frontend. The backend is explicitly locked out (D-4): no schema, no migration, no new endpoints beyond the Phase 135 `tactic-lines` endpoint that already surfaces stored PVs. The two novel frontend pieces are `useStockfishEngine` (Worker lifecycle, UCI protocol, debounce, stale-result cancellation) and `useAnalysisBoard` (branching move tree, FEN-per-node, O(1) navigation). These are written as new hooks alongside `useChessGame` — NOT modifications of it. A conditional `TacticModeOverlay` on the same page subsumes Phase 135's `TacticLineExplorer` modal once parity is verified; retiring the modal is a gated final phase.

The highest-severity risk is Pitfall 8: accidentally enabling `SharedArrayBuffer` / COOP+COEP headers site-wide, which breaks Google OAuth and iOS asset loading. The second-highest is the subsume-without-regression risk for four specific Phase 135 behaviors (depth-0 highlight, missed/allowed +1 offset, real-game-ply move numbering, tactic-rail state persistence). Both are preventable with the patterns documented in PITFALLS.md and must be addressed as first-class design concerns in their respective phases, not retrofitted.

---

## Key Findings

### Recommended Stack

No new backend dependencies. The only new frontend runtime dependency is `stockfish` npm v18.0.8 (nmrugg / Chess.com, GPLv3). The optional dev dependency `vite-plugin-static-copy` automates copying the two engine files from `node_modules/stockfish/src/` to `dist/engine/` at build time; manually copying to `public/engine/` is equally valid and simpler for v1.

The critical Vite wiring rule: both `stockfish-18-lite-single.js` and `stockfish-18-lite-single.wasm` must sit together in `public/engine/` and be served verbatim. Never process them through Vite's bundler (`?worker`, `?url`, esbuild optimizer). Add `optimizeDeps: { exclude: ['stockfish'] }` to `vite.config.ts` before writing any UCI code — the WASM URL resolution break in Vite's pre-bundler is silent in `vite dev` and only surfaces in `npm run build`.

**Core new technologies:**
- `stockfish` npm v18.0.8, `stockfish-18-lite-single.{js,wasm}` — single-thread WASM Stockfish with small embedded NNUE, ~7 MB total, no CORS headers. The correct build; others are either weaker or unsafe.
- `vite-plugin-static-copy` v2.x (optional) — copies engine files from `node_modules/` to `dist/engine/` at build time, keeping binaries out of git.
- Plain `new Worker('/engine/stockfish-18-lite-single.js')` — standard DOM Worker API, no Vite magic, already typed in TypeScript 6 `lib.dom.d.ts`.
- `React.lazy` + `Suspense` — code-splits `AnalysisPage` from the main bundle so the engine chunk is never fetched until the user navigates to `/analysis`.
- `go movetime 1500` (primary search bound) — wall-clock cap gives consistent UX on heterogeneous hardware; `go nodes 2000000` as secondary safety valve. Replaces the server-side `nodes 1000000` budget which is too slow for low-end mobile.

**License:** Stockfish is GPLv3. Distribution of the WASM binary requires a source pointer. FlawChess is already open-source; add an acknowledgement in README. The Worker thread boundary means GPL does not infect FlawChess's own code.

### Expected Features

Research confirms a clear MVP that closes the "go to lichess for analysis" gap, plus FlawChess-specific differentiators that neither lichess nor chess.com offer.

**Must have (table stakes):**
- Live eval bar (graphical centipawn bar, sigmoid-mapped, white-POV, mate-in-N display)
- Numeric eval + depth indicator ("Depth 18", "thinking...")
- Top 1-2 PV lines (MultiPV=2), clickable to navigate to that position
- Engine start/stop toggle
- Branching move tree — fork on deviation rather than reject the move
- Drag-drop + click-to-click move input (already in `ChessBoard.tsx`)
- Flip board, back/forward navigation, reset to root
- Eval arrow on board highlighting engine best move
- URL-encoded position state for sharing/bookmarking (root FEN + move sequence, not full tree)
- Debounced engine re-analysis on position change (150-300ms)
- "Loading engine" state while WASM initializes (board + PV stepper remain interactive)

**Should have (FlawChess differentiators):**
- Stored PV as initial mainline (D-5) — board opens pre-seeded with the Phase 135 PV; live engine supplements and takes over on deviation. Unique to FlawChess.
- Tactic mode overlay — motif badge, missed/allowed toggle, depth-to-punchline counter, next/prev tactic rail. Neither lichess nor chess.com integrate analysis with personal game flaw history this way.
- Context-aware entry points — tactic cards, game-review ply, and opening positions each pre-load the relevant position with relevant context.
- Engine on/off with visible "analyzing" state chip

**Defer (v2+ or post-launch):**
- Paste-a-FEN / paste-PGN input (the three typed entry points cover 100% of in-product use cases)
- Variation tree display with fork points shown inline in the move list
- Full SF18 single-thread option (HCE, no NNUE — actually weaker than lite)
- Multi-thread WASM engine (D-3 locked out; requires hard-loaded isolated document)
- Tablebase integration, promote/demote variation, save named analyses, annotation symbols

**Anti-features (explicitly omit):**
- SharedArrayBuffer / COOP+COEP headers (breaks Google OAuth + iOS)
- Cloud eval API (stored PVs already serve this role)
- Server-side analysis persistence (D-4 locked out)
- PGN annotation / comment system
- Social sharing buttons beyond copy-URL

### Architecture Approach

The analysis board composes two new independent hooks — `useStockfishEngine` (Worker lifecycle + UCI state machine) and `useAnalysisBoard` (FEN-per-node branching tree) — into a new `Analysis.tsx` page shell, lazy-loaded via `React.lazy`. The existing `ChessBoard.tsx`, `BoardControls.tsx`, `ArrowOverlay`, and `TacticMotifChip` are reused unchanged. Tactic mode is a conditional overlay (`TacticModeOverlay`) activated by URL params. Phase 135's `useTacticLines` query hook (in `useLibrary.ts`) is called from `Analysis.tsx` in tactic mode; the standalone `TacticLineExplorer.tsx` and `useTacticLine.ts` are retired only after parity is verified.

**Major components:**
1. `useStockfishEngine` — Worker lifecycle (create on mount, terminate on unmount), UCI protocol (uci/uciok/setoption/isready/readyok/analyze loop), 150ms debounce + stop-pending flag to discard stale `bestmove`, `go movetime 1500` cap, MultiPV state map keyed by `multipv` index. Returns `{ evalCp, evalMate, pvLines, depth, isAnalyzing, isReady }`.
2. `useAnalysisBoard` — Branching tree with `Map<NodeId, MoveNode>` where each `MoveNode` stores its own FEN (O(1) navigation). `makeMove` forks naturally at any node. `loadMainLine(sans, rootFen)` seeds the stored PV as the `mainLine` NodeId array. `isOnMainLine(nodeId)` gates tactic mode arrow logic. Keyboard handler scoped to `containerRef`, no sessionStorage, no Zobrist hashing.
3. `Analysis.tsx` — Lazy-loaded page shell. Reads URL params (`game_id`, `flaw_ply`, `orientation`, `fen`), composes both hooks, determines tactic/free mode, responsive layout (eval bar left of board on desktop, below board on mobile).
4. `EvalBar.tsx` — Vertical centipawn bar, sigmoid-mapped, mate label. Only shown from depth 8+ to avoid shallow misleading evals.
5. `EngineLines.tsx` — Top 1-2 PV lines as clickable SAN sequences with depth badge.
6. `VariationTree.tsx` — Move list rendering `nodes` + `mainLine`, click-to-navigate via `goToNode`.
7. `TacticModeOverlay.tsx` — Conditional tactic chrome: `TacticMotifChip`, missed/allowed toggle, next/prev-tactic rail. Arrow logic ported from `TacticLineExplorer` unchanged.

**Key pattern: FEN-per-node branching.** Storing FEN at each `MoveNode` makes `goToNode(id)` O(1) and eliminates the replay-from-root overhead of `useChessGame`'s `replayTo` pattern.

**Key pattern: stop-pending flag.** When `stop` is sent to the engine, it always responds with a `bestmove` (the termination result). This stale `bestmove` must be discarded via `stopPendingRef: boolean`.

### Critical Pitfalls

All 10 pitfalls are documented in detail in PITFALLS.md. The top 5 by severity:

1. **Accidental COOP/COEP headers (Pitfall 8)** — Highest severity. If any dependency introduces `SharedArrayBuffer`, browsers require cross-origin isolation, severing Google OAuth and breaking iOS assets. Prevention: lock `vite.config.ts` and Caddy config with explicit no-COOP/COEP comment citing D-3; add CI `curl -I` check; verify `window.crossOriginIsolated === false` after deploy.

2. **Subsume-without-regression (Pitfall 9)** — Four Phase 135 behaviors at high silent-regression risk: depth-0 highlight (empty PV crash), missed/allowed +1 ply offset (`tacticDepth.ts`), real-game-ply move numbering, and tactic-rail state resetting on route re-entry. Prevention: write regression tests for all four behaviors against `TacticLineExplorer` BEFORE touching Phase 135 code.

3. **Stale-eval race (Pitfall 3)** — `stop` always produces a `bestmove`; receiving it and treating it as the current result corrupts the eval display. Prevention: implement `stopPendingRef` boolean + discard the `bestmove` that immediately follows `stop`. Two-layer guard: 150ms debounce (Layer A) + stop-pending flag (Layer B).

4. **Vite esbuild optimizer breaks WASM URL resolution (Pitfall 1)** — If stockfish is not excluded from `optimizeDeps`, Vite relocates the JS to `.vite/deps/` while WASM stays in `node_modules/`, breaking relative path resolution. Silently works in `vite dev`, breaks in `npm run build`. Prevention: `optimizeDeps: { exclude: ['stockfish'] }` + files in `public/engine/` + verify with `npm run build && npx serve dist`.

5. **iOS 50 MB Cache API limit (Pitfall 2)** — iOS Safari's `CacheStorage` is hard-capped at ~50 MB. The full SF18 single-thread WASM exceeds this; a Workbox `CacheFirst` precache throws `QuotaExceededError` on SW installation, which can break the entire PWA shell. Prevention: use the lite build (~7 MB); exclude `*.wasm` from Workbox `globPatterns`; serve with `Cache-Control: max-age=31536000, immutable`.

---

## Implications for Roadmap

The four research files validate the seed's 5-phase shape. Dependencies flow strictly in order: engine hook before board components, board before page, page before tactic overlay, tactic subsume last.

### Phase 1: `useStockfishEngine` Hook + WASM Setup

**Rationale:** Entirely standalone; no dependencies on anything else in v1.29. The engine hook is the novel risk — every other piece extends well-understood existing code. Front-loading it surfaces platform/Vite issues before they entangle with board logic. All critical pitfalls (1, 2, 3, 4, 5, 6, 7, 8) are in scope here.
**Delivers:** `stockfish` npm installed; engine files vendored to `public/engine/`; `useStockfishEngine.ts` with Worker lifecycle, UCI state machine (`idle | thinking | stopping`), 150ms debounce, stop-pending flag, MultiPV map keyed by `multipv` index, `go movetime 1500` primary cap; UCI parser unit tests for lowerbound/upperbound, `mate 0`, and MultiPV interleaved sequences.
**Avoids:** Pitfalls 1, 2, 3, 4, 5, 6, 7, 8 — all verified before board or page code is written.
**Verification gate:** `npm run build && npx serve dist` (not just `vite dev`); iOS Simulator (no `QuotaExceededError`); Chrome DevTools Task Manager (no worker leak on nav away); `curl -I` for COOP/COEP absence and `application/wasm` MIME type.

### Phase 2: `useAnalysisBoard` Hook + Analysis Display Components

**Rationale:** Depends only on Phase 1 types. Building the branching tree and display components (EvalBar, EngineLines, VariationTree) before the page shell allows unit-testing each piece in isolation with Vitest. The branching tree is the second high-complexity item; isolating it here means regressions can be bisected cleanly.
**Delivers:** `useAnalysisBoard.ts` (MoveNode type, `nodes: Map`, `makeMove` fork, `goBack/goForward/goToNode`, `loadMainLine`, `isOnMainLine`, containerRef keyboard handler); `EvalBar.tsx`; `EngineLines.tsx`; `VariationTree.tsx`; URL param reading helpers.
**Key constraint:** `useAnalysisBoard` must NOT modify `useChessGame.ts`. The Openings board must be regression-free throughout.

### Phase 3: `/analysis` Route + Page Shell + Free-Play Entry Points

**Rationale:** Composes the two hooks and all display components into a working page. Wires free-play entry points and adds the `/analysis` route to `App.tsx`. Tactic mode is deferred to the next phase to make regressions easier to bisect.
**Delivers:** `src/pages/Analysis.tsx` (lazy-loaded via `React.lazy`, `<Suspense>` wrapper, responsive layout); `/analysis` route in `App.tsx`; `ROUTE_TITLES` entry; `data-testid` on all interactive elements; "Loading engine..." state in eval area (board and PV stepper remain interactive while engine initializes).
**Verification gate:** Network tab confirms no stockfish fetch on non-analysis routes; full Google OAuth flow unbroken; `window.crossOriginIsolated === false`.

### Phase 4: Tactic Mode Overlay + Phase 135 Subsume

**Rationale:** Highest regression risk. Requires Phase 3 before tactic mode can be wired. The Phase 135 regression test suite is the acceptance bar; standalone `TacticLineExplorer` is deleted only after all four regression behaviors pass.
**Delivers:** `TacticModeOverlay.tsx` (motif chip, orientation toggle, next/prev-tactic rail); `useTacticLines` wired into `Analysis.tsx` for tactic mode; `loadMainLine` seeding from stored PV (D-5); `buildRootArrows` / `buildPvArrow` ported from `TacticLineExplorer`; `FlawCard` and `LibraryGameCard` "Explore" buttons changed to `navigate('/analysis?...')`; `TacticLineExplorer.tsx` and `useTacticLine.ts` deleted; `npm run knip` clean.
**Regression gate (must pass before deletion):** depth-0 highlight, missed/allowed +1 offset, real-game-ply move numbering, tactic-rail state persistence on route re-entry.
**Avoids:** Pitfall 9 subsume regressions (Behavior A-D).

### Phase 5: Polish + PWA Audit

**Rationale:** Per D-4, no backend work is required. Phase 5 catches mobile layout tweaks, loading-engine skeleton UX improvements, and any polish from Phases 1-4 UAT. Also the correct place for the PWA service-worker audit.
**Delivers:** Mobile layout tweaks as needed; `visibilitychange` engine pause on tab hide; PWA `globPatterns` audit (confirm `*.wasm` excluded from Workbox precache); post-deploy `curl -I` MIME type verification.

### Phase Ordering Rationale

- Engine hook first: only fully standalone piece, highest novel risk, allows all platform pitfalls to be caught in isolation.
- Board hook + components second: depends only on engine hook types, not runtime behavior; isolating it enables clean unit testing.
- Page shell third: requires both hooks and all components to compose.
- Tactic subsume last: highest regression risk; requires the full page; separating it from the board phase means any Phase 4 regression can be bisected to the subsume.
- No backend phase: the `tactic-lines` endpoint from Phase 135 is the only API dependency and is already live.

### Research Flags

**Phase 1 (Engine hook): All resolved by this research session.** The WASM build choice, Vite wiring, iOS Cache limit, COOP/COEP risk, UCI state machine, and `go movetime` tradeoffs are fully documented. PLAN.md can be written directly from STACK.md + PITFALLS.md without additional research.

**Phase 2 (Board hook + components): Standard patterns, well-documented.** FEN-per-node branching tree and fork behavior are fully specified in ARCHITECTURE.md. No additional research needed unless `VariationTree` UI needs a specific design decision.

**Phase 3 (Page + route): Standard, no research needed.** React Router lazy-load, Suspense, and responsive layout patterns are established in the codebase.

**Phase 4 (Tactic subsume): No research needed; high execution discipline required.** Architecture is fully documented. Risk is regression testing discipline — tests must precede any Phase 135 code changes.

**Phase 5 (Polish): No research needed.** Standard PWA audit and mobile testing.

### Open Questions (Surface During Planning)

1. **Real-device `movetime` calibration:** The 1500ms wall-clock budget is well-reasoned but unvalidated on actual low-end Android hardware. Smoke-test during Phase 1 and adjust if needed.

2. **Branching tree UI depth for v1:** How much branching depth to show in the v1 `VariationTree` is a product decision (flat secondary list vs. inline indented). Data model supports either; choose during Phase 2 planning.

3. **PWA service-worker `*.wasm` glob audit:** Verify the existing `vite.config.ts` `globPatterns` or `globIgnores` does not match `*.wasm` before Phase 1 is declared done.

4. **Engine files: committed vs. plugin-generated:** Both options (commit to `public/engine/` or use `vite-plugin-static-copy`) are valid. Make the call during Phase 1 planning based on preference for simplicity vs. keeping binaries out of git.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Package details from web + npm registry; Vite 8 patterns from official docs. Build file names and sizes cross-referenced from GitHub but not directly fetched. Core recommendation (lite-single, public/ placement, optimizeDeps.exclude) convergent across all sources. |
| Features | HIGH | Analysis-board patterns well-established across lichess/chess.com; reuse map verified against direct codebase inspection of all named files. Feature table stakes unambiguous. Anti-features locked by D-1..D-5. |
| Architecture | HIGH | Based on direct code inspection of all named files (useChessGame.ts, useTacticLine.ts, ChessBoard.tsx, BoardControls.tsx, TacticLineExplorer.tsx, tacticDepth.ts, App.tsx, vite.config.ts). Component boundaries, hook contracts, and data flow diagrams grounded in actual implementation. |
| Pitfalls | HIGH | Codebase verified + cross-checked against official Vite docs, UCI specification, iOS Safari platform notes, stockfish npm package. All 10 pitfalls include prevention patterns and detection warning signs. |

**Overall confidence: HIGH**

### Gaps to Address

- **Real-device `movetime` calibration (Phase 1):** The 1500ms budget is well-reasoned but needs one smoke test on a budget Android during Phase 1 to confirm. Not a research gap; an empirical validation step.

- **`VariationTree` v1 UI presentation (Phase 2):** How many branching levels to show in v1 is a product decision not resolved in research. The data model supports any presentation; defer to Phase 2 planning.

- **Engine file placement (Phase 1):** Commit to `public/engine/` or use `vite-plugin-static-copy` — both documented, both valid. Decide during Phase 1 planning.

---

## Sources

### Primary (HIGH confidence — project-internal)
- SEED-066 locked design decisions D-1 through D-5 — single-thread rationale, ephemeral state, stored-PV handoff, subsume strategy
- SEED-012 amendment 2026-06-12 — COOP/COEP + iOS Safari research (prior milestone)
- Direct codebase inspection: `useChessGame.ts`, `useTacticLine.ts`, `ChessBoard.tsx`, `BoardControls.tsx`, `TacticLineExplorer.tsx`, `tacticDepth.ts`, `App.tsx`, `vite.config.ts`, `FlawCard.tsx`, `LibraryGameCard.tsx`
- UCI specification (official Stockfish docs) — lowerbound/upperbound, MultiPV ordering, `mate 0` semantics

### Secondary (MEDIUM confidence)
- Vite Features docs (vite.dev/guide/features) — `?worker`, `public/` asset serving, `optimizeDeps.exclude`
- Vite 8 announcement (vite.dev) — Rolldown integration, no breaking changes to `public/` serving
- Vite issues #8427 and #10837 — esbuild optimizer breaks `new URL()` in pre-bundled dependencies
- stockfish npm package (npmjs.com, nmrugg) — version 18.0.8, build file names, single-thread NNUE confirmation
- lichess-org/stockfish-web (GitHub) — multi-thread only, PTHREAD_POOL_SIZE requirement
- iOS Safari Cache API 50 MB limit (love2dev.com, cross-referenced with web.dev)
- lichess.org/analysis — feature reference for table stakes (eval bar, variation tree, URL state)

### Tertiary (LOW confidence — supporting context)
- nmrugg/stockfish.js GitHub — build variants, file names, UCI usage
- Stockfish vs ChessBase FOSSA — GPLv3 distribution requirements
- WebAssembly MIME type / Caddy behavior — `application/wasm` content-type serving

---
*Research completed: 2026-06-26*
*Ready for roadmap: yes*

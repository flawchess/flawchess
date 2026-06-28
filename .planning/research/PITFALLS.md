# Pitfalls Research

**Domain:** Adding a live in-browser single-thread WASM Stockfish analysis board to an existing mobile-first React 19 + Vite 8 PWA (FlawChess v1.29)
**Researched:** 2026-06-26
**Confidence:** HIGH — codebase verified + cross-checked against official Vite docs, stockfish npm package READMEs, iOS Safari platform notes, UCI specification, and Phase 135 source

---

## Critical Pitfalls

### Pitfall 1: Vite Esbuild Optimization Breaks WASM URL Resolution in Pre-Bundled Dependencies

**What goes wrong:**
When a stockfish npm package (e.g. the `stockfish` npm package) uses `new URL('stockfish.wasm', import.meta.url)` internally to locate its WASM file, Vite's esbuild optimizer rewrites the package entry point from `node_modules/stockfish/stockfish-18-single.js` to `node_modules/.vite/deps/stockfish.js`. The `import.meta.url` inside that module now resolves to the `.vite/deps/` directory — so the WASM file is looked for in `.vite/deps/stockfish-18-single.wasm`, which does not exist. The result: `404 Not Found` for the WASM in development, and either a silent failure or build-time error in production. This manifests as the engine appearing to load but never responding to `uci`, or a `CompileError: invalid magic number` from `WebAssembly.instantiate`.

**Why it happens:**
Vite's esbuild pre-bundling is designed for pure JS modules. It does not understand `new URL(asset, import.meta.url)` patterns inside dependencies — it physically relocates the JS file but leaves the WASM binary in `node_modules/`, breaking relative paths. This is a known Vite issue (vitejs/vite #8427, #10837); a partial fix landed via PR #17837 but it is not complete for all patterns. Developers hit this because the engine works fine in isolation (node, direct browser) but breaks under Vite's optimizer.

**How to avoid:**
- Add the stockfish package to `optimizeDeps.exclude` in `vite.config.ts`:
  ```ts
  optimizeDeps: { exclude: ['stockfish'] }
  ```
  This forces Vite to load it as-is from `node_modules/`, preserving the relative WASM path.
- Copy the `.js` and `.wasm` files into `public/` (or `public/engine/`) and instantiate the worker via a URL string pointing to the public path: `new Worker('/engine/stockfish-18-single.js')`. This fully bypasses Vite's asset pipeline for the engine and is the simplest production-safe pattern.
- Do NOT use `?worker` suffix on a file inside `node_modules/` — the suffix is only supported for files Vite owns.
- Do NOT use `vite-plugin-wasm` as a substitute — it targets your own WASM files imported via `import foo from './foo.wasm'`, not the engine's self-loading pattern.

**Warning signs:**
- Engine loads in `vite dev` but produces a 404 for the `.wasm` file in `vite build` output.
- `WebAssembly.instantiate` throws `CompileError: invalid magic number` — the JS shim loaded but the WASM was 404'd and the response is HTML.
- No UCI `uciok` response after posting `uci` to the worker.
- DevTools Network tab shows the WASM request going to `.vite/deps/` instead of `node_modules/`.

**Phase to address:**
Engine hook phase (Phase 136) — resolve this before writing any UCI logic; verify with `npm run build && npx serve dist` locally, not just `vite dev`.

---

### Pitfall 2: iOS PWA Standalone Mode Has a 50 MB Cache API Limit — The Full SF18 NNUE Net Cannot Be Cached

**What goes wrong:**
iOS Safari's Cache API (used by service workers) is capped at approximately 50 MB per partition for PWAs in standalone mode (installed to home screen). The full Stockfish 18 single-thread NNUE binary (`stockfish-18-single.wasm`) exceeds this limit. The service worker silently fails to cache it — no error is surfaced to the user — and on the next offline visit the engine is unavailable. Worse, a Workbox `CacheFirst` strategy that attempts to pre-cache the WASM throws `QuotaExceededError` during SW installation, which can abort the service worker registration entirely, breaking the PWA's offline shell as a side effect.

**Why it happens:**
The 50 MB limit is a hard platform constraint on iOS Safari's `CacheStorage`, not a Workbox or app-level setting. Developers familiar with desktop Chrome (which has generous quota) don't discover this until testing on an actual iPhone. The PWA's existing service worker (already shipping in v1.2) will try to cache whatever files are listed in its precache manifest if you add the WASM to the build output.

**How to avoid:**
- Use `stockfish-18-lite-single.js` / `stockfish-18-lite-single.wasm` (~7 MB each) instead of the full NNUE build. The lite build reaches depth 18–20 in under 2 seconds on desktop and is far weaker than the full build only in tactical depth — not relevant for human comprehension of a position.
- Never add the WASM file to the Workbox precache manifest. Instead, serve it with strong HTTP cache headers (`Cache-Control: max-age=31536000, immutable`) from the origin. The browser's native HTTP cache handles it; no SW involvement needed.
- If the full NNUE is ever desired for desktop: gate the fetch behind `navigator.deviceMemory > 4 && !navigator.userAgentData?.mobile` and skip iOS entirely. Do not attempt to cache it in the SW regardless.
- Audit the existing Vite PWA plugin config: ensure `globPatterns` or `runtimeCaching` in `vite.config.ts` does not match `*.wasm`.

**Warning signs:**
- SW installation fails on iOS with `QuotaExceededError` in Safari DevTools.
- PWA shell stops working on iOS after adding the engine.
- Network tab shows the engine WASM fetched fresh on every `/analysis` visit (HTTP 200, not 304 or from cache).

**Phase to address:**
Engine hook phase (Phase 136) — choose the lite build from the start; verify on an iOS device (or Simulator) before declaring the phase done.

---

### Pitfall 3: Stale Eval Race — `stop` / `bestmove` / `go` Message Ordering

**What goes wrong:**
The UCI flow is asynchronous. When the user makes a move, the hook must: (1) send `stop` to halt the running search, (2) wait for `bestmove` (Stockfish always emits `bestmove` after `stop`, even mid-search), (3) send `position fen <new-fen> go nodes <N>`. If you skip step 2 and send `position fen ... go ...` immediately after `stop`, the engine may process the new `go` while still finalizing its response to `stop`. The result: the hook receives a `bestmove` from the previous search, mistakes it for the current search's result, and displays the wrong move/eval for the new position. This is the most common UCI race condition in browser chess implementations.

A related variant: the hook debounces position changes (correct), but cancels the debounce on unmount without sending `stop`. The engine continues running, and when `bestmove` arrives after the component has unmounted, the hook's state setter fires on an unmounted component — React's stale-closure warning.

**Why it happens:**
Developers model the UCI exchange as request/response, but it is actually a state machine: the engine has states (`ready`, `thinking`, `stopping`) and must receive commands in the right sequence. Sending `go` without waiting for the previous search to conclude is undefined behavior in the UCI spec.

**How to avoid:**
- Implement a message-queue state machine in `useStockfishEngine`:
  - States: `idle | thinking | stopping`
  - On position change: if `idle`, immediately send `position fen ... go ...` (→ `thinking`). If `thinking`, send `stop` (→ `stopping`) and enqueue the new `go` command.
  - On `bestmove` received: if `stopping`, dequeue and send the pending `position fen ... go ...` (→ `thinking`). If `thinking`, update eval state (→ `idle`).
- Use a sequence counter (integer, incremented on each `go`). When `bestmove` arrives, only accept it if the sequence counter matches the expected value; discard stale results.
- In the `useEffect` cleanup: send `stop`, set a `cancelled` flag to discard any subsequent `bestmove`, then call `worker.terminate()`.

**Warning signs:**
- Eval bar flickers back to the previous position's eval when moving quickly.
- `bestmove` arrives with a move that's illegal in the current position.
- React warns about `setState` on an unmounted component from the engine callback.

**Phase to address:**
Engine hook phase (Phase 136) — the state machine must be part of the hook's initial design, not retrofitted. Write a unit test for the stop/go sequence using a mock worker before integrating a real engine.

---

### Pitfall 4: Web Worker Leak on Route Navigation — Engine Keeps Running After `/analysis` Exit

**What goes wrong:**
When the user navigates away from `/analysis` (e.g. back to Openings), React unmounts the analysis board component. If the `useEffect` that created the Web Worker does not call `worker.terminate()` in its cleanup return, the worker continues running in the background — evaluating the last position at full CPU, draining battery, and holding the WASM linear memory allocation. On iOS, the WASM memory is not freed until the browser explicitly closes the worker or the tab is killed. Because the WASM engine allocates tens of MB of linear memory at startup, this is a real battery and memory drain on mobile.

A subtler variant: the worker is instantiated at the module level (outside React's lifecycle) as a singleton for reuse. If the singleton is not explicitly stopped when no component is consuming it, it runs indefinitely during the entire session.

**Why it happens:**
Web Workers are not tied to the DOM — they survive component unmounts unless explicitly terminated. React's `useEffect` cleanup is the only hook point; developers often add `worker.terminate()` but forget to also send `stop` first, leaving the engine in a half-terminated state that can cause a crash log on some platforms.

**How to avoid:**
- In `useStockfishEngine`, always return a cleanup function from `useEffect`:
  ```ts
  useEffect(() => {
    const worker = new Worker(engineUrl);
    // ... setup
    return () => {
      worker.postMessage('stop');
      worker.terminate();
    };
  }, []);
  ```
- If using a singleton worker (to avoid the ~200 ms re-init cost on repeated visits): implement an explicit `pause()` call when the analysis page unmounts that sends `stop` and sets the worker to idle. Resume on re-mount. This is more complex; the component-scoped worker with terminate-on-unmount is simpler and safe enough for v1.
- Keep `/analysis`'s lazy chunk boundary tight so the engine worker module only loads when the route is active (React Router lazy + Suspense).

**Warning signs:**
- CPU usage stays elevated (top-of-screen Activity Monitor on iOS, or `chrome://sys-internals`) after navigating away from `/analysis`.
- Mobile device warms up noticeably while browsing other pages of the app.
- JS heap in Chrome DevTools grows by ~50–100 MB whenever `/analysis` is visited and does not release on navigation.

**Phase to address:**
Engine hook phase (Phase 136) — terminate pattern is a first-class design concern of `useStockfishEngine`, not a polish item. Verify with Chrome DevTools Memory profiler: take a snapshot before visiting `/analysis`, after, and after navigating away — heap must return to baseline.

---

### Pitfall 5: Single-Thread Thermal Throttle on Low-End Android — Unbounded Search Hangs the Device

**What goes wrong:**
Without a hard node or time limit, a single-threaded WASM Stockfish can search indefinitely. On a low-end Android (Snapdragon 4xx series, ~150–250k nps single-thread), reaching depth 18 on a complex middlegame takes 15–30 seconds. The device's thermal governor reduces clock speed after sustained load, cutting nps further. Users experience: the "thinking" indicator spins for 30+ seconds with no eval update; tapping other UI elements is sluggish due to the Worker consuming the single JS thread's scheduling budget (even though Workers run off the main thread, they compete for the same CPU core on single-core-equivalent devices). Battery drains visibly.

**Why it happens:**
Desktop-calibrated node limits (e.g. 1,000,000 nodes — the server-side lichess budget) are appropriate for the server (Stockfish native binary) but too high for mobile WASM at single-thread. Lichess's browser analysis uses `go movetime` (time-based) rather than `go nodes` for exactly this reason — it's a better UX guarantee on heterogeneous hardware.

**How to avoid:**
- Use `go movetime 1500` (1.5 seconds) as the primary budget instead of `go nodes N`. This gives a consistent UX: the eval refreshes in ~1.5s on every device, and users can see depth improving over time.
- As a safety cap, also set `go movetime 1500 nodes 2000000` — whichever limit is hit first ends the search. This prevents runaway searches if the movetime calculation drifts.
- Monitor reported `nps` in incoming `info` lines. If `nps < 30000` (severe throttling indicator — the WASM engine itself is seeing thermal throttle), reduce the next movetime budget to 1000ms and surface a subtle "device is warm" indicator if desired.
- Never use `go infinite` in the analysis UI — always bound the search. `go infinite` is for engine tournaments, not interactive analysis.

**Warning signs:**
- `bestmove` arrives more than 5 seconds after `go movetime 1500` was sent (indicates the worker's event loop is itself starved or the device clock is throttled).
- Users report "the board is frozen" after making a move.
- `info` lines report `nps` values dropping over successive searches (thermal throttle signature).

**Phase to address:**
Engine hook phase (Phase 136) — hardcode `movetime` limit in `useStockfishEngine` from day one. Do not expose it as a user-configurable option in v1; choose a sensible default. Add a mobile smoke test: open `/analysis` on a budget Android device (or Chrome DevTools throttling at 4x slowdown) and confirm eval updates arrive within 3 seconds.

---

### Pitfall 6: WASM `Content-Type: application/wasm` Not Served by Caddy — `instantiateStreaming` Throws

**What goes wrong:**
`WebAssembly.instantiateStreaming(fetch('/engine/stockfish.wasm'))` requires the server to respond with `Content-Type: application/wasm`. If Caddy (or any proxy in the chain) serves the `.wasm` file as `application/octet-stream` or — worse — as `text/html` (a catch-all for unknown extensions), `instantiateStreaming` throws `TypeError: Failed to execute 'compile' on 'WebAssembly': Incorrect response MIME type`. The engine falls back to `WebAssembly.instantiate(arrayBuffer)` if your code handles the error, which is 30–40% slower to parse. If your code does not handle the error, the engine silently fails to load.

**Why it happens:**
Caddy 2 includes `application/wasm` for `.wasm` in its built-in MIME types (since Caddy ~2.3), so this should not be an issue for FlawChess's Caddy 2.11.2 setup — but only for files Caddy serves directly. If the WASM is bundled into a Vite asset chunk that gets inlined (base64) or renamed without a `.wasm` extension, Caddy never sees the extension. Additionally, if a CDN or Cloudflare proxy sits in front of Caddy and strips or overrides content types, `application/wasm` may not reach the browser.

**How to avoid:**
- Place the WASM in `public/engine/` and reference it as a static path. Caddy serves `public/` directly with correct MIME types.
- After the first production deploy, run: `curl -I https://flawchess.com/engine/stockfish-18-lite-single.wasm | grep content-type` and confirm `content-type: application/wasm`.
- If using the Cloudflare tunnel or Cloudflare proxy: verify Cloudflare does not re-serve the WASM with an overridden MIME type (Cloudflare generally preserves origin MIME types for non-HTML resources).
- In `vite.config.ts`, ensure the `.wasm` file is NOT captured by `assetsInlineLimit` (set `assetsInlineLimit: 0` for `.wasm` files to keep them as separate fetched resources):
  ```ts
  build: {
    assetsInlineLimit: (filePath) => filePath.endsWith('.wasm') ? 0 : 4096
  }
  ```

**Warning signs:**
- DevTools Network tab shows the `.wasm` request returning `Content-Type: application/octet-stream`.
- Console logs `TypeError: Failed to execute 'compile' on 'WebAssembly': Incorrect response MIME type`.
- Engine takes noticeably longer to start (falling back to `instantiate(arrayBuffer)` path).

**Phase to address:**
Engine hook phase (Phase 136) — add a MIME type verification step to the deployment checklist for this phase.

---

### Pitfall 7: UCI Score Parsing — Lowerbound/Upperbound, Mate-0, and MultiPV Ordering Mistakes

**What goes wrong:**
Three specific UCI parsing mistakes corrupt the displayed eval:

**Lowerbound/Upperbound:** During alpha-beta search, the engine emits `info score cp N lowerbound` or `info score cp N upperbound` when the score is a hash table estimate, not the true eval. Displaying these directly causes the eval bar to jump erratically as bounds tighten. Many hobbyist implementations ignore the flags and display every `info` line — this looks correct at depth 1 but produces jittery, wrong evals at depth 10+.

**Mate scores with N=0:** `score mate 0` means the position is already checkmate (the side to move is mated). Some parsers crash or display `M0` as `M∞`. Negative mate scores (`score mate -3`) mean the side to move is losing by forced mate in 3 — the engine is reporting that the position is a loss, not that it is checkmating in 3.

**MultiPV ordering:** With `MultiPV 2`, the engine sends interleaved `info multipv 1` and `info multipv 2` lines, but they arrive out of order — the engine may finish multipv 2 before multipv 1 at the same depth, then finish multipv 1 later. A naive "last info line wins" approach picks the wrong PV. The `bestmove` corresponds to multipv 1 always, but the `info` lines need the `multipv N` tag to sort correctly. With `go movetime`, the final info lines before `bestmove` are the deepest available — but across multipv slots, they may be at different depths.

**Why it happens:**
The UCI spec describes these behaviors but most browser engine wrappers are written from lichess's JavaScript analysis code, which handles them correctly. When rolling a custom parser, developers skip the spec's edge cases because the common path (exact score, single PV, not mate) covers 95% of positions.

**How to avoid:**
- Parse every `info` line into a structured object with explicit fields: `{depth, seldepth, multipv, score: {type:'cp'|'mate', value:number, bound:'exact'|'lower'|'upper'}, nodes, nps, pv}`.
- Only display scores where `bound === 'exact'`. Buffer `lowerbound` / `upperbound` scores as "last known bound" but never display them as the current eval.
- For mate scores: render `M0` as "Checkmate" (game over), `M-N` as "Losing M-in-N", `M+N` as "Winning M-in-N". Handle `mate 0` explicitly as a terminal state.
- For MultiPV: maintain a `Map<number, PVLine>` keyed by `multipv` index. Update on every `info` line. On `bestmove`, take the map's current state as the final eval. Do not assume arrival order.

**Warning signs:**
- Eval bar jumps to extreme values during normal play and then snaps back.
- PV display shows the second-best line instead of the best.
- The UI shows "Mate in 0" or crashes on positions where the game is already over.
- MultiPV 2 lines swap positions randomly.

**Phase to address:**
Engine hook phase (Phase 136) — write a standalone UCI parser with unit tests for all three edge cases before integrating it with the worker. Test inputs: an `info` line with `lowerbound`, a `score mate 0` line, and an interleaved MultiPV sequence.

---

### Pitfall 8: Accidental Multi-Thread — Slipping `SharedArrayBuffer` or COOP/COEP Headers Site-Wide

**What goes wrong:**
If any future change introduces `SharedArrayBuffer` (e.g. choosing a multi-thread engine build, using `Atomics`, or referencing a dependency that requires it), the browser requires Cross-Origin Isolation: `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` (or `credentialless`). Setting these site-wide on FlawChess breaks three things simultaneously:

1. **Google OAuth popup**: `COOP: same-origin` severs `window.opener`, so the OAuth callback cannot communicate back to the opener tab. Google Sign-In silently fails.
2. **iOS Safari COEP**: iOS Safari only honors `COEP: require-corp`, not `credentialless`. Any cross-origin asset without `Cross-Origin-Resource-Policy: cross-origin` (e.g. user avatars from chess.com CDNs, analytics scripts) is blocked with a network error.
3. **React Router SPA cannot isolate per-route**: Cross-origin isolation is a property of the HTML document set at load time; client-side navigation reuses the same document. You cannot enable isolation only on `/analysis` without making it a hard-navigated separate document with no shared JS context.

The trap is subtle: a new npm dependency (e.g. a WASM-based chess engine with threading enabled) may bundle a build that uses `SharedArrayBuffer` without advertising it prominently. The engine appears to work on desktop Chrome, but fails on Google OAuth and iOS instantly.

**Why it happens:**
Multi-thread WASM engines are a natural upgrade path — lichess uses them, and the perf difference on desktop is real. When performance concerns arise in v1 testing, the "obvious fix" is to switch to the multi-thread build. But the full COOP/COEP impact is invisible until it breaks OAuth or iOS.

**How to avoid:**
- Lock in `vite.config.ts` and the Caddy config: no `Cross-Origin-Opener-Policy` or `Cross-Origin-Embedder-Policy` headers anywhere on the site. Add a comment citing D-3 and this pitfall.
- In `useStockfishEngine`, document explicitly:
  ```ts
  // Single-thread WASM only — do NOT replace with a SharedArrayBuffer-requiring build.
  // Multi-thread is deferred (SEED-066 D-3). Changing this requires full COOP/COEP analysis.
  ```
- If v1 desktop performance is genuinely insufficient (unlikely), the correct path is a separate hard-navigated `/analysis-desktop` document with its own HTML entry point and no OAuth — not site-wide headers. This requires a Vite multi-page setup and explicit Caddy routing. Open this path only via a dedicated `/gsd-explore` session on D-3.
- Test: after every CI build, run `curl -I https://flawchess.com | grep -i 'cross-origin'` and fail the build if any COOP/COEP headers appear.

**Warning signs:**
- Engine package README mentions "SharedArrayBuffer" or "Threads > 1" requirement.
- A dependency update makes Google Sign-In fail silently.
- iOS users report that profile images or certain analytics fail to load after an update.
- `window.crossOriginIsolated` returns `true` in the browser console — this should always be `false` for FlawChess.

**Phase to address:**
Engine hook phase (Phase 136) — enforce the single-thread package choice from the start. Add a CI check for COOP/COEP headers. Revisit only if v1 ships and desktop performance is genuinely inadequate, via a new discuss session.

---

### Pitfall 9: Subsume-Without-Regression — Four Phase 135 Behaviors That Break During the Refactor

**What goes wrong:**
The subsume refactor folds the Phase 135 `TacticLineExplorer` modal into the new analysis board as a "tactic mode." Four specific behaviors are at high risk of silent regression:

**Behavior A — Depth-0 highlight:** When `currentDepth === 0` in `useTacticLine`, the flaw move itself is highlighted on the board (no PV to step through). If the new analysis board's `useChessGame` variant starts at the flaw position and the tactic mode overlay doesn't check `depth === 0` separately, it attempts to step the PV and shows the wrong position or crashes on an empty PV array.

**Behavior B — Missed/Allowed +1 offset (`tacticDepth.ts`):** `tacticDepth.ts` computes the correct starting PV depending on orientation: missed = PV from the flaw position (the best reply the user should have played); allowed = PV from the position after the opponent's flaw move (+1 ply, the user's response). If the analysis board's `loadMoves()` call receives the PV anchored at the wrong ply, every subsequent step is off by one and the user sees the opponent's moves instead of their own.

**Behavior C — Real-game-ply move numbering:** The tactic context knows the original `game_ply` (e.g. ply 42 = White's 22nd move). The tactic line display shows full-move numbers anchored to the game's ply, not restarted from 1. If the analysis board's `useChessGame` variant initializes its internal `currentPly` counter from 0 when a FEN is loaded, displayed move numbers will be "1. e4 e5" instead of "22. Nxf7 Rxf7" — confusing in tactic context.

**Behavior D — Next/prev-tactic navigation rail:** The next-tactic rail in the tactic overlay must survive re-mounting as an overlay on the shared board (instead of the old modal). If the rail's state (which tactic index) is stored inside `TacticLineExplorer`'s local state, it resets to 0 every time the analysis board re-mounts (e.g. on route re-entry). It needs to be lifted to the URL or a calling context.

**Why it happens:**
The subsume is framed as a "refactor" but involves significant structural changes to where state lives. Each of the four behaviors was implicit in the old component's architecture; moving to a composition model exposes the implicit dependencies.

**How to avoid:**
- Write regression tests for all four behaviors BEFORE touching any Phase 135 code. Pin the tests to `TacticLineExplorer`'s current behavior (mounting at a known FEN + PV and asserting move numbers, highlight squares, PV advancement). These tests become the acceptance bar.
- Keep `tacticDepth.ts` untouched during the subsume. The analysis board accepts a `tacticSeed` prop (FEN, PV, orientation, game-ply-offset, motif) and the overlay reads from it — no internal recalculation of the offset logic.
- For Behavior C: the `useChessGame` branching variant must accept an optional `startingPly` parameter that offsets its internal ply counter. When loading a tactic from ply 42, pass `startingPly={42}`.
- For Behavior D: lift the current tactic index to URL state (`/analysis?tacticId=<id>`) so it survives route re-entries and is shareable.
- Run the tactic overlay against the existing dev database's tactic flaws before calling the subsume complete.

**Warning signs:**
- Stepping a tactic line shows the opponent's moves instead of the user's recommended moves.
- Move numbers displayed as "1. ..." instead of the game's actual move number.
- The first step of a depth-0 tactic crashes (trying to advance an empty PV).
- Next-tactic resets to tactic #1 every time the user returns to `/analysis`.

**Phase to address:**
Subsume phase (Phase 139, the last phase of v1.29) — this is explicitly the highest-regression-risk phase. Allocate extra time; treat it as a refactor with the Phase 135 test suite as the gate. Do NOT ship the subsume in the same phase as the engine hook or analysis board — separate phases allow bisecting regressions cleanly.

---

### Pitfall 10: WASM Bundle Lazy-Loading UX — "Loading Engine" State Missing or Blocking Navigation

**What goes wrong:**
The WASM engine binary (even the lite ~7 MB build) takes 200–800 ms to fetch, instantiate, and initialize UCI on a fast connection. On a slow mobile connection (3G, 50kbps effective in subway), it can take 30+ seconds. If the component renders the board immediately but blocks user interaction waiting for `uciok`, the board appears frozen — no "loading" indicator, no moves accepted. If instead the component shows a loading overlay, but the overlay covers the board completely and doesn't allow position navigation (e.g. stepping a loaded PV), the UX degrades: users can't explore the stored line while the engine loads.

The complementary mistake: the WASM is NOT lazy-loaded. If the engine chunk is included in the main bundle (or even the lazy analysis chunk includes it as a synchronous import), it delays the initial parse of the JS for the entire `/analysis` route.

**Why it happens:**
Engine initialization is asynchronous but the board and PV stepper don't require the engine. Developers block everything on `uciok` because it's the simplest model.

**How to avoid:**
- Split engine loading from board rendering. The board, PV stepper, stored evals, and tactic overlay all work without a live engine — show them immediately.
- Only the "live eval" area (eval bar, top lines, depth readout) is in a loading state until `uciok` arrives. Use a skeleton/spinner specifically in that region.
- Send `uci` to the worker immediately on mount (not on first position change). Initialize in the background; show the eval area as "loading engine…" during this time.
- Use React Router's lazy() + Suspense for the entire `/analysis` chunk. The WASM binary must NOT be a static import at the app entry point — it must only load when the route is visited.
- On slow connections: show a progress estimate. The WASM file fetch can be tracked via `fetch()` with `ReadableStream` — not required for v1 but worth noting as a future UX polish.

**Warning signs:**
- Board appears blank for 1–2 seconds when navigating to `/analysis` even on fast Wi-Fi (WASM being parsed synchronously on the main chunk).
- No loading indicator in the eval area — board just looks "not working."
- Mobile users report that chess analysis "doesn't do anything" (engine loaded but no visible feedback during analysis).

**Phase to address:**
Analysis board phase (Phase 137) — the board + PV stepper must be independently renderable. Engine loading state integration is part of the route phase (Phase 138) where the full UX composition comes together.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use full NNUE SF18 build (~40+ MB) for "better analysis" | Higher depth on desktop | Breaks iOS Cache API (50 MB limit), slow on mobile, fails the PWA install flow | Never for v1; only on desktop-isolated progressive enhancement path |
| `go infinite` with a user-facing "Stop" button | Familiar lichess UX | Requires the user to manually stop; engine runs forever if user navigates away without stopping; battery drain | Never — always bound with `movetime` |
| Skip the stop/bestmove handshake, send `go` immediately after position change | Simpler code | Stale-eval race: bestmove from previous search displayed for new position | Never |
| Module-level singleton worker (one instance for the entire session) | Avoids re-init cost (~200ms) | Must implement explicit pause/resume; harder to test; worker errors affect all uses | Acceptable if paired with explicit `pause()` on route unmount; not recommended for v1 |
| Display all `info` lines including lowerbound/upperbound scores | Simpler parsing | Eval bar appears jittery; wrong score displayed during search | Never — filter to `exact` scores only |
| Keep `TacticLineExplorer` as a separate component alongside the new analysis board | Avoids subsume risk | Code duplication forever; two separate board instances maintained; users see inconsistent behavior between tactic and free analysis | Only during Phase 135→136 transition; must complete subsume before v1.29 closes |

---

## Integration Gotchas

Common mistakes when integrating the live engine with existing FlawChess components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `useChessGame` clone for analysis | Copy `useChessGame` and add branching; now two copies diverge | Fork `useChessGame` into `useAnalysisGame` with a clear composition boundary; shared logic extracted to utils; no state duplication |
| `tacticDepth.ts` import | Reimplementing the offset logic in the new analysis hook | Import `tacticDepth.ts` unchanged; the analysis board's `loadTacticSeed()` calls it to compute the correct PV anchor |
| `ArrowOverlay` + engine arrows | Adding engine top-line arrows on top of existing tactic arrows; both sets render | Engine arrows and tactic arrows are mutually exclusive: tactic mode shows tactic arrows (best-move highlight); free analysis mode shows engine PV arrows. Gate via mode prop |
| PWA service worker + WASM | Workbox `generateSW` auto-precaches everything in `dist/` including the new WASM | Explicitly exclude WASM from precache glob pattern: `globIgnores: ['**/*.wasm']`; let HTTP cache handle it |
| URL state encoding for FEN/PGN | URL-encoding a full PGN string in query params; URLs become 1000+ chars, break sharing | Encode only the FEN for the current position + move list as UCI notation (compact); decode on mount |
| Vite `optimizeDeps.exclude` for stockfish | Forgetting to exclude causes dep-optimization breakage in dev | Add `optimizeDeps: { exclude: ['stockfish'] }` before writing any engine code |

---

## Performance Traps

Patterns that work at small scale but fail under realistic mobile conditions.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `go nodes 1000000` (server-side budget) in browser | 10–30s waits on mobile, device heats up | Use `go movetime 1500` as the primary bound; nodes as secondary cap | Any device below flagship Android |
| Re-creating the worker on every position change | 200ms stutter on each move; "loading engine" flashes every time | Create the worker once on mount, reuse via `stop`/`go` sequence; terminate only on unmount | Always noticeable; especially bad on mobile |
| Sending `setoption name MultiPV value 2` unconditionally | 2x analysis cost; slower depth progression; on mobile this doubles movetime | Only enable MultiPV 2 when the UI is actually rendering a second line (analysis mode); use MultiPV 1 for tactic mode where only the best reply matters | Low-end mobile; analysis takes 2× as long |
| Not debouncing position changes | Rapid PV stepping floods the worker with stop/go cycles; `bestmove` responses pile up | Debounce position changes by 150ms before sending `go`; this is especially important when the user holds down the forward key | Any fast PV stepping in the tactic stepper |
| Parsing info lines in the main thread via heavy regex | Jank on info-line bursts (Stockfish emits many lines/second) | Parse in the Worker itself and postMessage only the structured result; the Worker thread is off the main thread but still reduce postMessage volume | High-depth analysis; info lines arrive ~10/sec |

---

## UX Pitfalls

Common user experience mistakes specific to this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No "loading engine" state — board appears frozen | User thinks the page is broken; may reload, losing their position | Show a spinner in the eval area immediately; board and PV stepper are interactive while engine loads |
| Showing engine eval before the engine is confident (depth < 8) | Shallow evals show highly misleading scores (±500 cp swings); users distrust the feature | Show eval only from depth 8+; until then show "Analyzing…" with a depth counter |
| Eval bar updating every `info` line (30+ updates/second) | Rapid flicker; mobile renders can't keep up; perceived jitter | Throttle eval bar updates to every 300ms or on depth change; debounce with `requestAnimationFrame` |
| No explanation when engine is unavailable (browser blocking WASM, or download fails) | User sees a dead eval bar with no explanation | Catch `WebAssembly.instantiate` errors; show "Engine unavailable. Try refreshing or using a supported browser." |
| Tactic mode drops users into free analysis without warning | User stepped off the tactic line and suddenly has no guided content | Show a subtle "Exploring off-line — engine is analyzing freely" chip when the user deviates from the stored PV in tactic mode |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Vite dev vs prod parity:** Verify the engine loads in `npm run build && npx serve dist` on the same machine before testing on mobile — dev (`vite dev`) may succeed while `build` 404s the WASM.
- [ ] **iOS Cache quota:** On an iPhone (or iOS Simulator), open `/analysis` in Safari standalone PWA mode; confirm no `QuotaExceededError` in the Web Inspector console and no SW registration failure.
- [ ] **Worker terminate on unmount:** Navigate to `/analysis`, let the engine start, then navigate away. Open Chrome DevTools Task Manager; confirm no "Dedicated Worker" process remains.
- [ ] **Stale-eval race:** Move rapidly through a PV (6+ moves in 2 seconds); confirm the displayed eval and best-move arrow correspond to the final position, not an intermediate one.
- [ ] **Mate display:** Navigate to a checkmated position; confirm the UI shows "Checkmate" (not "Mate in 0" or a crash).
- [ ] **MultiPV ordering:** With MultiPV 2 enabled, confirm the displayed second line is actually the second-best move, not a random line from an interleaved info sequence.
- [ ] **Tactic mode Behavior A (depth-0):** Open a depth-0 tactic from a flaw card; confirm the flaw move square is highlighted and no PV step crash occurs.
- [ ] **Tactic mode Behavior B (+1 offset):** For an "allowed" tactic (opponent's flaw), confirm the first PV move shown is your best response to the opponent's blunder, not the opponent's move itself.
- [ ] **Tactic mode Behavior C (move numbers):** Open a tactic from ply 42; confirm the displayed move counter starts at move 22, not move 1.
- [ ] **COOP/COEP header check:** After deploy, run `curl -I https://flawchess.com | grep -i cross-origin` — no COOP or COEP headers should be present.
- [ ] **Google OAuth unbroken:** After adding the analysis page, complete a full Google Sign-In flow; confirm it still works (COOP accidental slip is silent until OAuth is tested).

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Vite WASM URL broken in prod | LOW | Move engine files to `public/engine/`; update Worker instantiation URL; redeploy |
| iOS Cache quota exceeded; SW broken | MEDIUM | Remove WASM from SW precache; bump SW version to force re-registration; redeploy; no data loss |
| Worker leak discovered post-ship | LOW | Add `worker.terminate()` to `useEffect` cleanup; redeploy — one-line fix, but mobile users need to reload the app |
| Stale-eval race producing wrong bestmove | MEDIUM | Add sequence counter to UCI parser; requires refactoring the hook's message handler; no data loss |
| COOP/COEP headers accidentally set site-wide | HIGH | Emergency revert of header config; Google OAuth and iOS assets broken for all users until deploy; prioritize immediately |
| Phase 135 tactic behavior regressed in subsume | MEDIUM | Revert the subsume PR; keep `TacticLineExplorer` as a separate component temporarily; re-approach with the regression tests in place |
| Full SF18 NNUE accidentally shipped (large build) | LOW | Swap to lite build in config; redeploy; no data loss — only a bundle-size regression until fixed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Vite WASM URL resolution (Pitfall 1) | Phase 136 — Engine hook | `npm run build && npx serve dist`: WASM 200, correct Content-Type |
| iOS 50 MB Cache limit / lite build (Pitfall 2) | Phase 136 — Engine hook | iOS Simulator: no QuotaExceededError; SW registers cleanly |
| Stale-eval race / stop-bestmove-go ordering (Pitfall 3) | Phase 136 — Engine hook | Unit test: mock worker state machine; rapid move test in browser |
| Worker leak on route change (Pitfall 4) | Phase 136 — Engine hook | Chrome DevTools Task Manager: no lingering workers after nav away |
| Thermal throttle / unbounded search (Pitfall 5) | Phase 136 — Engine hook | `go movetime 1500` hardcoded; test on 4x throttled Chrome DevTools |
| WASM MIME type on Caddy (Pitfall 6) | Phase 136 — Engine hook | Post-deploy `curl -I` check on `.wasm` URL |
| UCI score parsing edge cases (Pitfall 7) | Phase 136 — Engine hook | Unit tests: lowerbound line, `mate 0`, MultiPV interleaved sequence |
| Accidental multi-thread / COOP+COEP (Pitfall 8) | Phase 136 — Engine hook | CI: `curl -I` check; package lock audit for SharedArrayBuffer deps |
| Subsume regression (Behavior A–D) (Pitfall 9) | Phase 139 — Subsume | Regression tests on depth-0, +1 offset, move numbers, tactic rail state |
| Engine loading UX / lazy load (Pitfall 10) | Phase 137–138 — Board + route | Lighthouse: analysis route doesn't add to main bundle; loading state visible in eval area |

---

## Sources

- Codebase: `frontend/src/hooks/useChessGame.ts`, `frontend/src/lib/tacticDepth.ts`, `frontend/src/components/board/` — HIGH confidence (direct inspection)
- `.planning/seeds/SEED-066-live-engine-analysis-page.md` (Risks / watch-outs, D-3 reasoning) — HIGH confidence (project document)
- `.planning/seeds/SEED-012-client-side-stockfish-tactics.md` (Prerequisite 1: COOP/COEP + iOS Safari research) — HIGH confidence (project document)
- [Vite Features: Web Workers](https://vite.dev/guide/features) — MEDIUM confidence (official docs, cross-checked)
- [Vite issue #8427: new URL() in pre-bundled deps](https://github.com/vitejs/vite/issues/8427) — MEDIUM confidence (verified issue, known pattern)
- [Vite issue #10837: ?url / ?worker inside 3rd-party modules](https://github.com/vitejs/vite/issues/10837) — MEDIUM confidence (verified issue)
- [stockfish npm package README](https://www.npmjs.com/package/stockfish) — MEDIUM confidence (official package)
- [Godot issue #70621: WASM 2GB memory → OOM on iOS](https://github.com/godotengine/godot/issues/70621) — MEDIUM confidence (real-world platform report)
- [iOS Safari Cache API 50MB limit — love2dev.com](https://love2dev.com/blog/what-is-the-service-worker-cache-storage-limit/) — MEDIUM confidence (cross-referenced with web.dev storage docs)
- [UCI specification](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-&-Commands.html) — HIGH confidence (official Stockfish documentation)
- [WebAssembly MIME type / nginx issue](https://trac.nginx.org/test/ticket/1606) — MEDIUM confidence (known nginx pattern, applies to Caddy equally)
- [WASM not working: MIME type requirements — fixdevs.com](https://fixdevs.com/blog/wasm-not-working/) — LOW confidence (cross-checked with official Rust/WASM deployment docs)

---
*Pitfalls research for: FlawChess v1.29 — Live WASM Stockfish analysis board on mobile-first PWA*
*Researched: 2026-06-26*

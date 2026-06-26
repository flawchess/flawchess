# Stack Research

**Domain:** In-browser single-thread WASM Stockfish — additions to existing React 19 + Vite 8 PWA
**Researched:** 2026-06-26
**Confidence:** MEDIUM (package details from web + npm registry; Vite 8 patterns from official docs)

## Scope Note

This is subsequent-milestone (v1.29) research. The base stack (React 19, TypeScript 6, Vite 8,
react-chessboard 5.x, chess.js, TanStack Query, Tailwind, FastAPI) is validated in production.
Only **new capabilities** for the live engine are documented here. Backend is untouched (D-4 locked).

---

## Recommended Stack (New Additions Only)

### Core: The Engine Package

**Use `stockfish` npm package v18.0.8.**

Maintained by nmrugg / Chess.com, GPLv3. This is the right package for the D-3 constraint
(single-thread only, no SharedArrayBuffer). It ships five builds — only one is relevant for v1:

| Build file | Size | Threading | NNUE | CORS headers needed |
|------------|------|-----------|------|---------------------|
| `stockfish-18.js` + `.wasm` | >100 MB | multi (SharedArrayBuffer) | full 85 MB embedded | yes (`COOP`+`COEP`) |
| `stockfish-18-single.js` + `.wasm` | large (~30–100 MB) | single | none (HCE only) | no |
| `stockfish-18-lite.js` + `.wasm` | ~7 MB | multi (SharedArrayBuffer) | small NNUE embedded | yes (`COOP`+`COEP`) |
| **`stockfish-18-lite-single.js` + `.wasm`** | **~7 MB** | **single** | **small NNUE embedded** | **no** |
| `stockfish-18-asm.js` | ~10 MB | single | none | no |

**Why lite-single wins:** The only single-thread build with a neural-network evaluation is
`stockfish-18-lite-single`. The full single-thread (`stockfish-18-single`) ships *without NNUE*
and falls back to classical HCE evaluation — paradoxically making it weaker than the 7 MB lite
build. The lite-single embeds a small NNUE (likely the threat-small/sscg13 family) directly in
the `.wasm` binary, so no separate network file is fetched. "Quite a bit weaker" is relative to
Stockfish's 3600+ ELO ceiling; the lite-single is still far stronger than any human and more than
sufficient for comprehension-level analysis.

### NNUE File Situation

No separate NNUE file to host or download. The small neural-network weights are compiled into
the `.wasm` binary itself. Total transfer for first engine load is ~7 MB across both files
(`stockfish-18-lite-single.js` + `stockfish-18-lite-single.wasm`). The browser's HTTP cache
plus the existing PWA service worker (Workbox, already in the project) handle subsequent visits:
configure `CacheFirst` for `/engine/*` assets in the Workbox config so the 7 MB is fetched once
and cached indefinitely. No `Cache-Control` header gymnastics required — stable filenames in
`public/engine/` get cached on first visit.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `vite-plugin-static-copy` | 2.x | Copy engine files from `node_modules/stockfish/src/` to `dist/engine/` at build time | Use this instead of committing the ~7 MB binary to `public/` manually |

`vite-plugin-static-copy` is the only new dev dependency. It keeps binary engine files out of
git by pulling them from the npm package at build/dev time. Alternatively, manually copy the
two files to `public/engine/` and skip the plugin — simpler, acceptable for v1 if you don't
want the plugin dependency.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Browser DevTools Performance tab | Verify engine thread isolation, measure analysis latency | Worker runs in a separate thread; main thread should not stall |
| Lighthouse / PWA audit | Confirm engine assets are cached by service worker | Check `/engine/` routes appear in the precache manifest |

---

## Installation

```bash
# Runtime (engine — goes to node_modules but engine files are served from public/)
npm install stockfish

# Dev — copies engine files to dist/ at build time (skip if manually copying to public/)
npm install -D vite-plugin-static-copy
```

---

## Vite 8 Wiring Pattern

### Problem: Emscripten constraint

The Emscripten-compiled `stockfish-18-lite-single.js` fetches its `.wasm` companion by
*relative path* — it assumes `stockfish-18-lite-single.wasm` is at the same URL directory as
the `.js` file. This means:

- Both files **must** be served from the same path prefix.
- Vite's `?worker` bundling is **not suitable** here — Vite would hash and relocate the
  `.js` file, severing the relative `.wasm` reference.
- Vite's `?url` on the `.wasm` alone doesn't help because the `.js` glue doesn't use that URL.

### Recommended: `public/engine/` placement

Place both engine files under `public/engine/` (either committed or copied by `vite-plugin-static-copy`).
Files in `public/` are served verbatim at their path prefix with no hashing, no bundling, no
module-system involvement. This is the pattern the Stockfish.js documentation recommends for
browser integration.

**`vite.config.ts` addition (if using `vite-plugin-static-copy`):**

```typescript
import { viteStaticCopy } from 'vite-plugin-static-copy'

export default defineConfig({
  plugins: [
    // ... existing plugins
    viteStaticCopy({
      targets: [
        {
          src: 'node_modules/stockfish/src/stockfish-18-lite-single.{js,wasm}',
          dest: 'engine',
        },
      ],
    }),
  ],
})
```

This copies both files to `dist/engine/` on build and makes them available at `/engine/` in dev
via the dev server.

### Worker creation in `useStockfishEngine`

```typescript
// Only called when the hook mounts — which only happens on the /analysis route
const worker = new Worker('/engine/stockfish-18-lite-single.js')
```

Do not use `new URL('/engine/...', import.meta.url)` — that pattern is for Vite-bundled worker
scripts and triggers module resolution. A plain string path for a `public/` file is correct and
stable across dev/build.

### Code-split / lazy-load on the `/analysis` route

The engine worker is **only instantiated when `useStockfishEngine` mounts**, which only happens
inside `AnalysisPage`. Lazy-load the route component via `React.lazy`:

```typescript
// In your router (e.g. App.tsx)
const AnalysisPage = React.lazy(() => import('./pages/AnalysisPage'))
```

This ensures:
- `AnalysisPage.tsx` and its imports (including `useStockfishEngine`) are code-split into a
  separate chunk and not fetched until the user navigates to `/analysis`.
- The `Worker` constructor (and the 7 MB fetch) is deferred until page mount.
- The main-app bundle is not affected.

The `/engine/*.js` and `/engine/*.wasm` files are **not** in any JS bundle — they're fetched
by the browser only when `new Worker(...)` runs.

### TypeScript worker types

In the `useStockfishEngine` hook file, `new Worker(path)` is standard DOM and already typed in
TypeScript 6's lib. No extra `@types` needed. The worker itself (the engine's JS file) is not
edited, so no `/// <reference lib="webworker" />` directive is needed in project code.

For the thin UCI wrapper layer that runs *in the main thread* and talks to the worker via
`postMessage`/`onmessage`, standard `Worker` typing is sufficient.

---

## UCI Integration Pattern

The engine exposes a UCI protocol via `postMessage` / `onmessage`. Minimal pattern:

```typescript
worker.postMessage('uci')         // -> "uciok" when ready
worker.postMessage('isready')     // -> "readyok"
worker.postMessage('setoption name Threads value 1')  // single-thread: 1 (already default)
worker.postMessage('setoption name MultiPV value 2')  // top-2 lines
worker.postMessage(`position fen ${fen}`)
worker.postMessage('go nodes 1000000')               // 1M nodes (Lichess parity budget)
// -> "info depth N score cp N pv <moves>" (streaming)
// -> "bestmove <move>" (done)

// Before new position:
worker.postMessage('stop')
```

**Debounce position changes** by ~200ms to avoid flooding the engine when a user clicks rapidly
through moves. The `stop` + new `go` pattern is safe — the engine processes commands sequentially.

**Cap for mobile:** On low-end phones, `go movetime 3000` (3 second wall-clock cap) is safer
than unbounded `go nodes`. Use `go movetime 3000` as the default and offer a `go nodes 1000000`
mode for desktop. Show a visible "thinking..." indicator between `go` and `bestmove`.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `@lichess-org/stockfish-web` | Multi-thread optimized (PTHREAD_POOL_SIZE), requires SharedArrayBuffer. Its own README recommends `stockfish.js` for non-lichess browser use. | `stockfish` npm package (lite-single build) |
| `stockfish.wasm` (lichess older package) | Multi-thread only, **no NNUE**. Much weaker than lite-single despite larger complexity. | `stockfish` npm package (lite-single build) |
| `stockfish-18-single.js` (full single-thread) | Large (30–100 MB), **no NNUE** (HCE only). Weaker than the 7 MB lite-single. | `stockfish-18-lite-single.js` |
| `stockfish-18.js` (full multi-thread) | >100 MB, requires SharedArrayBuffer — violates D-3 | `stockfish-18-lite-single.js` |
| `vite-plugin-wasm` | Handles `import foo.wasm` as ES module — irrelevant for Emscripten-compiled engines that self-load their WASM. | None; engine self-loads via relative URL |
| `SharedArrayBuffer` / COOP+COEP headers | Violates D-3; breaks Google OAuth popup; unreliable on iOS Safari. | Single-thread path with no headers |
| Cloud eval API (chessdb.cn, lichess cloud eval) | External dependency, out of scope for v1 per D-5. | Stored PVs from `tactic-lines` endpoint |
| Separate NNUE network file hosting | Unnecessary — lite-single embeds weights in `.wasm`. | Nothing; weights are bundled |

---

## Alternatives Considered

| Decision | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Engine package | `stockfish` npm (nmrugg) lite-single | `@lichess-org/stockfish-web` | lichess package is multi-thread only; explicitly recommends stockfish.js for simpler use |
| Engine files location | `public/engine/` (verbatim serving) | Bundle via `?worker` | Emscripten WASM relative-path assumption breaks when Vite hashes the JS glue file |
| Engine files in git | Via `vite-plugin-static-copy` from npm | Commit binaries to `public/` | npm-sourced keeps git lean; both are valid for v1 |
| Analysis throttle | `go movetime 3000` on mobile | `go nodes 1000000` | Node count is hardware-dependent; wall-clock cap is safer on constrained devices |
| Multi-thread engine | Deferred to v2 (separate hard-loaded `/analysis` document) | Enable for v1 with site-wide COOP+COEP | Breaks Google OAuth popup; unreliable on iOS Safari; SPA documents can't isolate per-route |

---

## Version Compatibility

| Package | Version | Notes |
|---------|---------|-------|
| `stockfish` (nmrugg) | 18.0.8 | GPLv3. Current as of 2026-06-26. Lite-single build files: `src/stockfish-18-lite-single.{js,wasm}`. |
| `vite-plugin-static-copy` | 2.x | Compatible with Vite 8 (Rolldown-based). Check peer deps when installing. |
| Vite 8 (Rolldown) | Already in project (v1.22 Phase 101) | No breaking changes to `?worker` or `public/` asset serving vs Vite 7. Rolldown replaces esbuild/Rollup for bundling but does not affect how `public/` files are served. |
| TypeScript 6 | Already in project (v1.22 Phase 101) | `Worker` DOM type already in `lib.dom.d.ts`. No additional `@types` needed for the UCI wrapper. |
| React 19 | Already in project | `React.lazy` + `Suspense` for route-level code splitting is unchanged in React 19. |
| iOS Safari | 16+ required (as stated in stockfish.js docs) | Single-thread WASM with no SharedArrayBuffer works on iOS 16+. PWA install supported. |

---

## License Implications

Stockfish is GPLv3. Distributing the WASM binary (which includes compiled Stockfish code)
requires providing the corresponding source code or a pointer to it.

**FlawChess is already open-source**, so compliance is straightforward:
- Add a note in `README.md` or an `ACKNOWLEDGEMENTS` section: "Chess analysis powered by
  Stockfish (GPLv3). Source: https://github.com/official-stockfish/Stockfish".
- Do **not** modify the Stockfish source code (use the npm package unmodified).
- If any Stockfish source is ever modified, those changes must also be released under GPLv3.

FlawChess's own codebase license is independent — GPL does not "infect" FlawChess's own code
because Stockfish runs in a separate Worker thread (not linked into the same binary/module).
This is the same model used by Chess.com, lichess, and countless other open platforms.

---

## Sources

- [stockfish npm package (nmrugg)](https://www.npmjs.com/package/stockfish) — version 18.0.8, build file names, size descriptions — LOW confidence (403 on direct fetch; cross-referenced via GitHub and web search)
- [nmrugg/stockfish.js GitHub](https://github.com/nmrugg/stockfish.js/) — build variants, file names, UCI usage, license (GPLv3 / Chess.com) — LOW confidence (web)
- [lichess-org/stockfish-web GitHub](https://github.com/lichess-org/stockfish-web) — NNUE file names (nn-c288c895ea92.nnue, nn-37f18f62d772.nnue), multi-thread only, pkg name `@lichess-org/stockfish-web` — LOW confidence (web)
- [Vite Features docs — Web Workers + WASM](https://vite.dev/guide/features) — `?worker`, `?worker&url`, `new Worker(new URL(...))`, `.wasm?init`, `.wasm?url` patterns — MEDIUM confidence (official docs via WebFetch)
- [Vite 8 announcement](https://vite.dev/blog/announcing-vite8) — Rolldown integration, no breaking changes to `public/` serving or worker patterns — MEDIUM confidence (official docs)
- [Stockfish vs ChessBase — FOSSA](https://fossa.com/blog/stockfish-vs-chessbase-gpl-v3/) — GPLv3 distribution requirements for binary distributions — LOW confidence (web)
- SEED-066 locked decisions (D-3, D-4, D-5) — single-thread constraint rationale, ephemeral state, stored-PV handoff — HIGH confidence (project-internal)
- SEED-012 amendment 2026-06-12 — COOP/COEP + iOS Safari analysis already researched; single-thread = no COOP/COEP needed — HIGH confidence (project-internal)

---

*Stack research for: FlawChess v1.29 Live-Engine Analysis Page*
*Researched: 2026-06-26*

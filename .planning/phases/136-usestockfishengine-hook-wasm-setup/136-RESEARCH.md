# Phase 136: `useStockfishEngine` Hook + WASM Setup — Research

**Researched:** 2026-06-26
**Domain:** In-browser single-thread WASM Stockfish 18 (lite-single), React hook, Vite 8 PWA wiring, Worker lifecycle, UCI state machine
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 136 ships **tests only, no user-visible UI.** Deliverables: `useStockfishEngine.ts`, Vitest UCI-parser unit tests, and **one** headless Worker integration test that drives a single fixed FEN through the real engine and asserts a sane `evalCp`/`pvLines`/`bestmove` come back. No route, no dev harness, no temporary toggle on existing boards.
- **D-02:** Human-in-the-loop / on-device (iOS Safari, low-end Android) eyeball verification is **deferred to Phase 138** when the `/analysis` page first renders engine output.
- **D-03:** Commit the two engine files (`stockfish-18-lite-single.js` + `stockfish-18-lite-single.wasm`, ~7 MB total) directly into `public/engine/` and check them into git. No `vite-plugin-static-copy`, no extra dev dependency. Worker instantiated via `new Worker('/engine/stockfish-18-lite-single.js')`. `optimizeDeps: { exclude: ['stockfish'] }` still required in `vite.config.ts`.
- **D-04:** On `visibilitychange → hidden`, send `stop` to the engine but keep the Worker alive. On `visibilitychange → visible`, **automatically re-`go`** on the current position.
- **Locked upstream:** `stockfish-18-lite-single.{js,wasm}` (~7 MB, single-thread NNUE). Search cap: `go movetime 1500` (primary, locked). `go nodes 2000000` permitted only as secondary safety valve. MultiPV = 2. Debounce = 150ms. Two-layer stale-eval guard: debounce (Layer A) + `stopPendingRef` (Layer B). **No `SharedArrayBuffer` / COOP / COEP headers anywhere.** CI `curl -I` guard. PWA SW must NOT precache `*.wasm`. No backend work.

### Claude's Discretion

- UCI state-machine internal representation (`idle | thinking | stopping` enum naming), MultiPV map keying, exact debounce/stop wiring, and the secondary `go nodes` valve are the planner's/executor's call within the locked bounds above.
- Tab-hide pause implementation detail (whether resume reuses the last `go` params verbatim or recomputes) is discretionary, as long as D-04's auto-resume behavior holds.

### Deferred Ideas (OUT OF SCOPE)

- On-device (iOS Safari / low-end Android) manual verification — deferred to Phase 138.
- Real-device `movetime` calibration — deferred to Phase 138/UAT.
- `go nodes` desktop mode / adjustable strength — secondary valve only in 136; user-facing strength control is out of v1.29 scope.
- Multi-thread WASM engine (ENGINE-V2-01, D-3) — deferred to v2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGINE-01 | User sees a live evaluation (eval bar + numeric cp/mate) computed in-browser by WASM Stockfish | Hook returns `evalCp: number \| null` and `evalMate: number \| null`; Phases 137/138 render these |
| ENGINE-02 | User sees top 1–2 candidate lines (MultiPV) as SAN sequences with depth indicator | Hook returns `pvLines: PvLine[]` (MultiPV=2); depth in `depth: number` |
| ENGINE-03 | User sees engine best move as a board arrow | Hook returns `pvLines[0].moves[0]` (UCI move string); Phase 137 converts to arrow |
| ENGINE-04 | User can toggle engine on/off with visible loading/analyzing state; board stays interactive during WASM init | Hook returns `isReady: boolean`, `isAnalyzing: boolean`; expose `enable()`/`disable()` or `enabled` prop |
| ENGINE-05 | Engine re-analyzes automatically (debounced) when position changes, bounded by movetime/node cap | 150ms debounce + `go movetime 1500 nodes 2000000`; `stopPendingRef` guard |
| PLAT-01 | No COOP/COEP headers; Google OAuth and iOS Safari stay unaffected; absence CI-guarded | `optimizeDeps.exclude`, no SharedArrayBuffer, CI `curl -I` guard added to `ci.yml` |
| PLAT-02 | Engine WASM/NNUE assets load efficiently on mobile (lite ~7 MB, iOS Cache-API safe, SW `*.wasm` handling verified); tab-hide pause | `globIgnores: ['**/*.wasm']` in Workbox config; `visibilitychange` handler in hook |
</phase_requirements>

---

## Summary

Phase 136 is the most technically novel phase of v1.29. Everything else in this milestone builds on well-understood existing code; this phase introduces the only genuinely new technology: a single-thread WASM chess engine running in a Web Worker, managed by a React hook. The prior milestone research (STACK.md, PITFALLS.md, ARCHITECTURE.md) already resolved the big decisions. This research confirms the concrete implementation details the planner needs.

The `stockfish` npm package v18.0.8 ships its files in `node_modules/stockfish/src/`. The exact files to vendor are `stockfish-18-lite-single.js` and `stockfish-18-lite-single.wasm`, together ~7 MB. These are copied to `public/engine/` and committed per D-03. The Worker is instantiated as a classic (non-module) Worker from `/engine/stockfish-18-lite-single.js`. Messages are plain UCI strings via `worker.postMessage(str)` and `worker.onmessage = (e) => handleLine(e.data)`.

The critical `RESEARCH FLAG` from D-01 is resolved: the recommended integration test harness is the `stockfish` package's own Node.js entry point — `initEngine('lite-single')` from `index.js` — run in a `// @vitest-environment node` test file. This avoids all Worker URL/WASM path complexity in CI while testing against the real WASM binary. Output is received via `engine.listener = (line) => { ... }`, input via `engine.sendCommand(cmd)`. The test asserts `bestmove` for a known mate-in-1 FEN (deterministic regardless of eval_cp value). `@vitest/web-worker` is explicitly ruled out due to a known WASM import bug (vitest#6118). `node:worker_threads` direct is ruled out due to browser-API vs worker_threads-API mismatch.

The no-COOP/COEP CI guard is a new step in `ci.yml`: after `npm run build`, run `npm run preview` in background and `curl -I` to assert zero `Cross-Origin-*` headers on the page and `application/wasm` on the engine asset.

**Primary recommendation:** Write `useStockfishEngine.ts` as a UCI state machine (`idle | thinking | stopping`) with a `stopPendingRef` guard and 150ms debounced `go movetime 1500`. Vendor the engine binaries, wire Vite config, add CI guard, and cover all UCI edge cases in unit tests before touching any UI code.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| WASM engine execution | Browser Worker thread | — | Keeps JS main thread free for UI; Worker is terminated on unmount |
| UCI state machine | Frontend (hook) | — | `useStockfishEngine.ts` owns all Worker lifecycle and UCI protocol |
| Eval data (cp/mate/pv/depth) | Frontend (hook return) | — | Plain data; Phases 137/138 render it |
| Debounce + stale-eval guard | Frontend (hook internal) | — | Must live inside the hook, not the consumer |
| WASM file serving | CDN/Static (public/) | — | Files in `public/engine/` served verbatim by Vite/Caddy |
| PWA SW exclusion | Frontend (vite.config.ts) | — | `globIgnores` prevents iOS Cache-API overflow |
| COOP/COEP absence guard | CI (ci.yml) | — | Automated curl check catches accidental header additions |
| Tab-hide pause | Frontend (hook internal) | — | `visibilitychange` listener inside `useStockfishEngine` |
| Backend | None | — | D-4 locked: no schema, no migration, no new endpoints |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `stockfish` | 18.0.8 | WASM Stockfish 18 lite-single engine | Only single-thread build with NNUE; no COOP/COEP; maintained by Chess.com; ~7 MB |

**Note:** `stockfish` v18.0.8 is flagged **SUS** by the package legitimacy gate (reason: `too-new` — published 2026-06-15, two weeks ago). This is a version-date artifact: the package itself (`nmrugg/stockfish.js`) has existed since Stockfish 11, with 29k weekly downloads and an authoritative GitHub repo. The planner must add a `checkpoint:human-verify` task before the `npm install stockfish` step per SUS protocol.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `useDebounce` | existing (src/hooks/) | 150ms debounce of FEN changes before sending `go` | Reuse vs inline is planner's call; the existing utility matches the contract |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `stockfish` npm (nmrugg) | `@lichess-org/stockfish-web` | lichess package multi-thread only; requires COOP/COEP; violates D-3 |
| Vendor to `public/engine/` | `vite-plugin-static-copy` | Plugin automates copy from `node_modules/`; D-03 locked: commit directly, no plugin |
| `go movetime 1500` | `go nodes 2000000` | Node count is hardware-dependent; wall-clock cap gives consistent UX; both locked as dual bounds |

**Installation (after `checkpoint:human-verify`):**
```bash
cd frontend && npm install stockfish
```

**Version verification:**
```bash
npm view stockfish version  # returns 18.0.8
npm view stockfish dist.unpackedSize  # returns 251054382 (~251 MB — all 5 build variants)
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `stockfish` | npm | v18.0.8 published 2026-06-15 (package exists since SF11) | 29,525/wk | github.com/nmrugg/stockfish.js | SUS (too-new v18.0.8) | Flagged — planner adds checkpoint:human-verify before install |

**Packages removed due to [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** `stockfish` — the `too-new` flag is a version-date artifact (v18.0.8 published 2 weeks ago). The package is the long-running nmrugg/stockfish.js project with 29k weekly downloads and an authoritative source repo. Postinstall script (`node scripts/postinstall.js`) only creates filesystem symlinks — no network calls. Planner must gate `npm install stockfish` behind a `checkpoint:human-verify` task.

---

## Architecture Patterns

### System Architecture Diagram

Data flow for Phase 136 scope (hook + WASM wiring only):

```
Position FEN (string)
       |
       | (prop from future Analysis.tsx — Phase 138)
       v
[useStockfishEngine hook]  — mounts only on /analysis route
       |
       |-- on mount ---> new Worker('/engine/stockfish-18-lite-single.js')
       |                  (classic Worker, not module Worker)
       |                  -> postMessage('uci')
       |                  -> waits for 'uciok' in onmessage
       |                  -> postMessage('setoption name MultiPV value 2')
       |                  -> postMessage('isready')
       |                  -> waits for 'readyok'
       |                  -> isReady = true  [state update]
       |
       |-- FEN change ----> debounce 150ms
       |   (Layer A)         -> if state == 'thinking':
       |                          postMessage('stop')
       |                          stopPendingRef.current = true  (Layer B)
       |                          state = 'stopping'
       |                       -> postMessage('position fen <FEN>')
       |                       -> postMessage('go movetime 1500 nodes 2000000')
       |                       -> state = 'thinking', isAnalyzing = true
       |
       |-- worker.onmessage:
       |   'info depth N multipv M score cp C [exact] pv m1 m2...'
       |                  -> pvMap.set(M, {moves, score})
       |                  -> depth = N, evalCp = C (only if bound='exact')
       |   'info ... score mate N [exact]'
       |                  -> evalMate = N
       |   'bestmove m1 ponder m2'
       |                  -> if stopPendingRef.current:
       |                          stopPendingRef.current = false  [discard]
       |                          state = 'idle'
       |                       else:
       |                          pvLines = [...pvMap.values()]
       |                          isAnalyzing = false
       |                          state = 'idle'
       |
       |-- visibilitychange 'hidden':
       |                  -> postMessage('stop')
       |                  -> stopPendingRef.current = true
       |
       |-- visibilitychange 'visible':
       |                  -> if currentFen != null: re-go on currentFen
       |
       |-- on unmount --> postMessage('stop')
                          worker.terminate()
                          workerRef.current = null
       |
       v
Returns: {
  evalCp: number | null,     // centipawns, white-POV (null while loading/mate)
  evalMate: number | null,   // mate in N; positive=winning, negative=losing
  pvLines: PvLine[],         // up to 2 entries, sorted by multipv index
  depth: number,             // depth of last completed search
  isAnalyzing: boolean,
  isReady: boolean,
}

Worker thread (separate from main thread):
[stockfish-18-lite-single.js] + [stockfish-18-lite-single.wasm]
  - ~7 MB single-thread WASM Stockfish 18 lite
  - Communicates via postMessage strings (UCI protocol)
  - No SharedArrayBuffer, no COOP/COEP required
```

### Recommended Project Structure (new files only)

```
frontend/
├── public/
│   └── engine/
│       ├── stockfish-18-lite-single.js    # COMMIT (from node_modules/stockfish/src/)
│       └── stockfish-18-lite-single.wasm  # COMMIT (from node_modules/stockfish/src/)
├── src/
│   ├── hooks/
│   │   └── useStockfishEngine.ts          # NEW — Phase 136 primary deliverable
│   └── hooks/__tests__/
│       ├── uciParser.test.ts              # NEW — pure UCI parser unit tests
│       └── useStockfishEngine.integration.test.ts  # NEW — initEngine FEN→bestmove
├── vite.config.ts                         # MODIFY — add optimizeDeps.exclude + globIgnores
└── (package.json — add stockfish dep)
.github/workflows/ci.yml                   # MODIFY — add no-COOP/COEP guard step
```

### Pattern 1: UCI State Machine

**What:** `useStockfishEngine` uses three internal states (`idle | thinking | stopping`) to sequence UCI commands correctly. A `stopPendingRef` (boolean) tracks that the next `bestmove` event is a stale termination result and must be discarded.

**When to use:** Any time the user changes position while the engine is mid-search.

```typescript
// Source: ARCHITECTURE.md + UCI specification (official-stockfish.github.io)

type EngineState = 'idle' | 'thinking' | 'stopping';

const stateRef = useRef<EngineState>('idle');
const stopPendingRef = useRef(false);
const currentFenRef = useRef<string | null>(null);

function analyze(fen: string) {
  // Called after 150ms debounce
  const worker = workerRef.current;
  if (!worker || !isReady) return;

  currentFenRef.current = fen;

  if (stateRef.current === 'thinking') {
    worker.postMessage('stop');
    stopPendingRef.current = true;
    stateRef.current = 'stopping';
    // new go will be sent once bestmove (stale) arrives
    return;
  }

  // idle or stopping-but-waiting: safe to send directly
  worker.postMessage(`position fen ${fen}`);
  worker.postMessage('go movetime 1500 nodes 2000000');
  stateRef.current = 'thinking';
  setIsAnalyzing(true);
}

// In worker.onmessage handler:
function handleLine(line: string) {
  if (line.startsWith('info ')) {
    // Parse and update pvMap — always (even while stopping)
    // Only commit to state on 'exact' score bound
  } else if (line.startsWith('bestmove')) {
    if (stopPendingRef.current) {
      stopPendingRef.current = false;
      stateRef.current = 'idle';
      // Re-send go for the queued FEN that arrived while stopping
      if (currentFenRef.current) analyze(currentFenRef.current);
      return; // discard stale result
    }
    stateRef.current = 'idle';
    setIsAnalyzing(false);
    // commit pvMap snapshot to pvLines state
  }
}
```

### Pattern 2: UCI Parser (Pure Function)

**What:** Extract the UCI parser into a pure function tested independently of the Worker. This enables full unit-test coverage of all edge cases before wiring the real engine.

```typescript
// Source: UCI specification (official-stockfish.github.io/docs/stockfish-wiki/UCI-&-Commands.html)

export interface PvLine {
  multipv: number;        // 1-based
  depth: number;
  moves: string[];        // UCI move strings, e.g. ['e2e4', 'd7d5']
  evalCp: number | null;  // centipawns, white-POV; null if mate
  evalMate: number | null; // mate in N; null if centipawn
}

export type UCIScoreBound = 'exact' | 'lowerbound' | 'upperbound';

export interface ParsedInfoLine {
  depth: number;
  multipv: number;
  scoreCp: number | null;
  scoreMate: number | null;
  bound: UCIScoreBound;
  pv: string[];
}

export function parseInfoLine(line: string): ParsedInfoLine | null {
  if (!line.startsWith('info ')) return null;
  // Extract tokens: depth, multipv, score cp/mate, lowerbound/upperbound, pv
  // noUncheckedIndexedAccess: always assign to const before use
  // Return null if any required field is missing
}
```

### Pattern 3: Worker Lifecycle in `useEffect`

**What:** Worker is created on mount, terminated on unmount. Never a global singleton.

```typescript
// Source: PITFALLS.md Pitfall 4 (worker leak) + ARCHITECTURE.md Pattern 1

useEffect(() => {
  const worker = new Worker('/engine/stockfish-18-lite-single.js');
  workerRef.current = worker;

  worker.onmessage = (e: MessageEvent<string>) => {
    handleLine(e.data);
  };

  // UCI init sequence: uci → uciok → setoption MultiPV → isready → readyok
  worker.postMessage('uci');
  // Wait for 'uciok' in handleLine, then send setoption + isready

  return () => {
    worker.postMessage('stop');
    worker.terminate();
    workerRef.current = null;
  };
}, []); // mount only — worker is per-mount
```

**Important:** The Worker is a **classic** (non-module) Worker. The `stockfish-18-lite-single.js` is an Emscripten output that uses `self.onmessage` / `self.postMessage` internally. Do NOT pass `{ type: 'module' }` as the second argument to `new Worker(...)`.

### Pattern 4: Tab-Hide Pause (D-04)

**What:** `visibilitychange` listener sends `stop` on hidden, re-sends `go` on visible.

```typescript
// Source: D-04 locked decision, CONTEXT.md

useEffect(() => {
  const handleVisibility = () => {
    const worker = workerRef.current;
    if (!worker || !isReadyRef.current) return;

    if (document.visibilityState === 'hidden') {
      if (stateRef.current === 'thinking') {
        worker.postMessage('stop');
        stopPendingRef.current = true;
        stateRef.current = 'stopping';
      }
    } else {
      // visible: re-analyze current position
      if (currentFenRef.current) {
        // analyze() handles idle/stopping state correctly
        debouncedAnalyze(currentFenRef.current);
      }
    }
  };

  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, [isReady, debouncedAnalyze]);
```

### Pattern 5: Workbox WASM Exclusion

**What:** `globIgnores` in the VitePWA Workbox config explicitly prevents WASM files from being added to the service-worker precache manifest.

```typescript
// Source: vite.config.ts (existing, to be modified)
// Based on PITFALLS.md Pitfall 2 (iOS 50 MB Cache API limit)

VitePWA({
  // ... existing manifest config ...
  workbox: {
    navigateFallback: null,
    // Explicitly exclude WASM from SW precache (iOS Cache API ~50 MB limit).
    // The browser HTTP cache handles engine file caching instead.
    // See: SEED-066 D-3 / PITFALLS.md Pitfall 2.
    globIgnores: ['**/*.wasm'],
    runtimeCaching: [
      {
        urlPattern: /^\/api\//,
        handler: 'NetworkOnly',
      },
    ],
  },
}),
```

**Also add at the top level of `defineConfig`:**
```typescript
// Prevent Vite's esbuild optimizer from relocating the stockfish
// package JS to .vite/deps/, which would break its relative WASM path.
// The engine files live in public/engine/ and are served verbatim.
// See: PITFALLS.md Pitfall 1.
optimizeDeps: {
  exclude: ['stockfish'],
},
```

### Anti-Patterns to Avoid

- **Module Worker for Emscripten build:** `new Worker('/engine/...', { type: 'module' })` breaks the Emscripten module system. Use classic Worker (no second arg or `{ type: 'classic' }`).
- **Import stockfish through bundler:** `import Stockfish from 'stockfish'` in any frontend module routes through Vite's bundler, triggering Pitfall 1. Never import the package in frontend source — only use it for the Node.js integration test and for copying the binary files.
- **Display lowerbound/upperbound scores:** Eval bar must only update on `bound === 'exact'` info lines. Displaying intermediate bounds causes erratic jitter.
- **Send `go` without waiting for stop-pending to clear:** The two-layer guard must be implemented; skipping it produces stale bestmove display on rapid position changes.
- **Global Worker singleton:** Creates lazy-load bypass and lifecycle complexity. Per-mount is correct.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UCI state machine timing | Custom `setTimeout` retry loops | `stopPendingRef` + state enum | Race between stop/bestmove/go is subtle; the ref-based pattern handles it cleanly |
| WASM loading in browser | Custom fetch + `WebAssembly.instantiate` | Let the Emscripten JS glue handle it | The `stockfish-18-lite-single.js` already handles WASM instantiation, fallback, split-file assembly |
| Debounce | Custom `setTimeout`/`clearTimeout` wrapper | `useDebounce` (existing in `src/hooks/`) | The existing utility covers the 150ms case; planner decides reuse vs inline |
| UCI output parsing for tests | Mock responses | `initEngine('lite-single')` in a Node test | Real WASM validates correctness that a mock cannot |

**Key insight:** The Emscripten WASM module is a complete black box from the React side. The hook's job is to manage the message protocol, not the engine internals.

---

## RESEARCH FLAG Resolution: Integration Test Harness

**The critical question from D-01:** Which harness actually works for booting the ~7 MB single-thread WASM and asserting one FEN → bestmove end-to-end in CI?

### Decision: Use `stockfish` package's Node.js `initEngine('lite-single')`

**How it works:**
```typescript
// Source: examples/node_module.js + examples/node_direct.js (nmrugg/stockfish.js GitHub)
// @vitest-environment node

import { describe, it, expect } from 'vitest';

describe('Stockfish WASM integration (node entry point)', () => {
  it('returns bestmove for a mate-in-1 FEN', async () => {
    // initEngine is the stockfish package's index.js export.
    // 'lite-single' keyword loads stockfish-18-lite-single.{js,wasm} from src/.
    // initEngine handles uciok internally before resolving.
    const initEngine = (await import('stockfish')).default;
    const engine = await new Promise<{ sendCommand: (cmd: string) => void; listener: ((line: string) => void) | null; terminate: () => void }>((resolve, reject) => {
      const e = initEngine('lite-single', (err: Error | null) => {
        if (err) reject(err);
        else resolve(e);
      });
    });

    // Mate-in-1: Qxf7# (h5f7). Engine must return bestmove h5f7.
    // FEN: after 1.e4 e5 2.Bc4 Nc6 3.Qh5 (classical Scholar's attack pre-mate).
    const MATE_IN_1_FEN = 'r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4';

    const lines: string[] = [];
    let bestmoveLine = '';

    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('engine timeout')), 8000);

      engine.listener = (line: string) => {
        lines.push(line);
        if (line.startsWith('bestmove')) {
          bestmoveLine = line;
          clearTimeout(timeout);
          resolve();
        }
      };

      engine.sendCommand(`position fen ${MATE_IN_1_FEN}`);
      engine.sendCommand('go movetime 500');
    });

    engine.terminate();

    // Assert bestmove is the winning queen capture
    expect(bestmoveLine).toMatch(/^bestmove h5f7/);
    // Also assert we received at least one info line with a positive score
    const evalLine = lines.find(l => l.includes('score cp') && l.includes('pv'));
    expect(evalLine).toBeDefined();
  }, 10_000); // 10s timeout covers WASM init + 500ms search
});
```

**Why `initEngine` wins:**
- `index.js` is designed for Node.js; handles WASM loading from `node_modules/stockfish/src/` directly
- No Worker URL resolution (no `new Worker('/engine/...')` in Node context)
- Real WASM executes: tests that NNUE evaluates correctly, UCI protocol works end-to-end
- `engine.listener = fn` / `engine.sendCommand(cmd)` is the documented Node.js API
- Works in `// @vitest-environment node` (no jsdom needed)
- `initEngine` already handles `uci`/`uciok`/`isready`/`readyok` internally before callback fires — commands can be sent immediately after callback

**Why NOT `@vitest/web-worker`:**
- Known WASM import bug: `@vitest/web-worker` does not transform `.wasm?url` in Worker imports (vitest-dev/vitest issue #6118) [CITED: github.com/vitest-dev/vitest/issues/6118]
- Simulates Worker in the same thread — not real isolation
- WASM path resolution is fragile under the shim

**Why NOT `node:worker_threads` direct:**
- `stockfish-18-lite-single.js` is an Emscripten module that uses `self.postMessage()` / `self.onmessage` (browser Worker API)
- `node:worker_threads` uses `parentPort.postMessage()` / `workerData` — API mismatch
- Would require monkey-patching `self` inside the worker thread context — fragile

**What the integration test does NOT cover (and what covers it instead):**

| Gap | Coverage mechanism |
|-----|-------------------|
| `new Worker('/engine/...')` URL resolution | `npm run build && vite preview` smoke check (see CI guard below) |
| Worker postMessage boundary (serialization) | Build smoke check |
| MIME type `application/wasm` on Caddy | Post-deploy `curl -I` check (deployment checklist) |

**Acceptable fallback (if `initEngine` proves flaky in CI):**
UCI parser unit tests at full coverage + integration test gated with:
```typescript
it.skipIf(process.env.CI === 'true')('FEN→bestmove integration', ...)
```
plus explicit `npm run build && npx vite preview` smoke step in CI.

---

## Common Pitfalls

### Pitfall 1: Vite esbuild Optimizer Breaks WASM URL Resolution
**What goes wrong:** If `stockfish` is not in `optimizeDeps.exclude`, Vite relocates the package JS to `.vite/deps/` while WASM stays in `node_modules/`. Breaks silently in `vite dev`, loudly in `npm run build`.
**How to avoid:** Add `optimizeDeps: { exclude: ['stockfish'] }` FIRST THING before writing any hook code. Moot if the package is never imported in frontend source (it shouldn't be), but required as a guard.
**Verify:** `npm run build` without errors; `dist/engine/` contains both files; no `vite-deps` references in network tab.

### Pitfall 2: iOS 50 MB Cache API Limit
**What goes wrong:** Workbox precaching `*.wasm` throws `QuotaExceededError` on iOS Safari during SW installation, breaking the entire PWA shell.
**How to avoid:** Add `globIgnores: ['**/*.wasm']` to Workbox config. Use the lite-single build (~7 MB), not the full single (30–100 MB, HCE-only and weaker).
**Warning sign:** Default `vite-plugin-pwa` `globPatterns` does NOT include `.wasm` — but verify with `npm run build` output to confirm `dist/sw.js` does not reference the WASM.

### Pitfall 3: Stale Eval Race — Stop/Bestmove/Go Ordering
**What goes wrong:** `stop` always produces a `bestmove` (termination response). If that `bestmove` is treated as the current position's result, the eval bar shows the wrong move.
**How to avoid:** Two-layer guard: 150ms debounce (Layer A) + `stopPendingRef.current = true` when stop is sent (Layer B). On `bestmove` arrival, if `stopPendingRef.current`, discard and re-queue the pending `go`.
**Test:** Rapid FEN changes (6+ in 2 seconds) must show only the final position's eval.

### Pitfall 4: Worker Leak on Route Navigation
**What goes wrong:** Worker keeps running after component unmounts. CPU/battery drain on mobile.
**How to avoid:** `useEffect` cleanup always calls `worker.postMessage('stop'); worker.terminate()`.
**Verify:** Chrome DevTools Task Manager shows no "Dedicated Worker" process after navigating away from `/analysis`.

### Pitfall 5: Displaying Lowerbound/Upperbound Scores
**What goes wrong:** Alpha-beta search emits `info score cp N lowerbound` during search. Displaying these causes eval bar to jump to extreme values and snap back.
**How to avoid:** Only commit to state when `bound === 'exact'`. Buffer bounds as "last seen" but never surface them as the current eval.

### Pitfall 6: MIME Type `application/wasm` Not Served
**What goes wrong:** Caddy or a proxy serves `stockfish-18-lite-single.wasm` as `application/octet-stream`. `WebAssembly.instantiateStreaming` throws `TypeError: Incorrect response MIME type`. Engine silently fails or is 30–40% slower.
**How to avoid:** Caddy 2.11.2 already includes `application/wasm` in its built-in MIME types for `.wasm` extension. Files in `public/engine/` are served directly with correct type. Post-deploy verify: `curl -I https://flawchess.com/engine/stockfish-18-lite-single.wasm | grep content-type`.

### Pitfall 7: UCI Score Parsing Edge Cases
**What goes wrong:** Three specific parsing failures:
1. `score mate 0` → game is already checkmate; naive code shows "Mate in 0" or crashes
2. `score mate -3` → losing by mate in 3 (NOT engine checkmating in 3)
3. Interleaved MultiPV `info` lines arrive out of order by multipv index

**How to avoid:** Maintain `Map<number, PvLine>` keyed by `multipv`. Update on every exact info line. On `bestmove`, snapshot the map as `pvLines`. Handle `mate 0` as terminal state. Handle negative mate scores as "side-to-move is losing".

### Pitfall 8: Accidental COOP/COEP Headers Site-Wide
**What goes wrong:** Site-wide `Cross-Origin-Opener-Policy: same-origin` severs Google OAuth popups. `Cross-Origin-Embedder-Policy: require-corp` blocks cross-origin assets on iOS Safari.
**How to avoid:** Lock `vite.config.ts` and Caddy config: zero COOP/COEP headers. CI guard (see below) catches any accidental addition. `window.crossOriginIsolated` must remain `false`.

---

## Code Examples

### Worker Instantiation (Production Path)

```typescript
// Source: ARCHITECTURE.md Pattern 1 + STACK.md Vite Wiring Pattern
// In useStockfishEngine.ts, inside useEffect([]):
//
// Single-thread WASM only — do NOT replace with a SharedArrayBuffer-requiring build.
// Multi-thread is deferred (SEED-066 D-3). Changing this requires full COOP/COEP analysis.
const worker = new Worker('/engine/stockfish-18-lite-single.js');
// Classic (non-module) Worker — Emscripten output uses self.postMessage / self.onmessage.
// Do NOT pass { type: 'module' }.
```

### UCI Init Sequence

```typescript
// Source: UCI specification (official-stockfish.github.io)
// After Worker creation:
worker.postMessage('uci');
// Wait for 'uciok' in onmessage before proceeding
// Then:
worker.postMessage('setoption name MultiPV value 2');
worker.postMessage('isready');
// Wait for 'readyok' — then setIsReady(true)
```

### Vendor Copy Command

```bash
# Source: stockfish npm package structure (node_modules/stockfish/src/)
# Run once after npm install stockfish, then commit both files:
cp node_modules/stockfish/src/stockfish-18-lite-single.js  public/engine/
cp node_modules/stockfish/src/stockfish-18-lite-single.wasm public/engine/
git add public/engine/stockfish-18-lite-single.{js,wasm}
```

### CI No-COOP/COEP Guard

The new CI step to add to `.github/workflows/ci.yml` after the `npm run build` step:

```yaml
- name: No COOP/COEP header guard + WASM MIME check
  run: |
    # Start vite preview in background (serves dist/)
    npm run preview -- --port 4173 &
    PREVIEW_PID=$!
    sleep 3

    FAIL=0

    # Assert no cross-origin isolation headers on the page
    PAGE_HEADERS=$(curl -sf -I http://localhost:4173/ 2>&1)
    echo "Page headers:"
    echo "$PAGE_HEADERS"
    if echo "$PAGE_HEADERS" | grep -qi 'cross-origin-opener-policy\|cross-origin-embedder-policy'; then
      echo "FAIL: COOP/COEP header found on page — breaks Google OAuth and iOS Safari"
      FAIL=1
    else
      echo "PASS: No COOP/COEP headers on page"
    fi

    # Assert engine WASM served with correct MIME type
    WASM_HEADERS=$(curl -sf -I http://localhost:4173/engine/stockfish-18-lite-single.wasm 2>&1)
    echo "WASM headers:"
    echo "$WASM_HEADERS"
    if echo "$WASM_HEADERS" | grep -qi 'content-type.*application/wasm'; then
      echo "PASS: WASM MIME type is application/wasm"
    else
      echo "FAIL: WASM MIME type incorrect (expected application/wasm)"
      FAIL=1
    fi

    kill "$PREVIEW_PID" 2>/dev/null || true
    exit $FAIL
  working-directory: frontend
```

### UCI Parser Unit Test Inputs

```typescript
// Source: UCI specification (official-stockfish.github.io)

// Lowerbound (MUST NOT update displayed eval):
'info depth 12 multipv 1 score cp 45 lowerbound nodes 12000 pv e2e4 e7e5'

// Upperbound (MUST NOT update displayed eval):
'info depth 12 multipv 1 score cp 60 upperbound nodes 14000 pv d2d4 d7d5'

// Exact (MUST update displayed eval):
'info depth 14 multipv 1 score cp 52 nodes 30000 pv e2e4 e7e5 g1f3'

// Mate-in-1 (positive = winning):
'info depth 1 multipv 1 score mate 1 nodes 100 pv h5f7'

// Mate-0 = checkmate already (terminal state):
'info depth 0 multipv 1 score mate 0 nodes 1 pv '

// Losing mate (negative = side-to-move is losing):
'info depth 5 multipv 1 score mate -3 nodes 5000 pv e8f7 d1f3 f7e8 f3f7'

// MultiPV interleaved — two lines at same depth (may arrive out of order):
'info depth 15 multipv 2 score cp 18 nodes 45000 pv d2d4 d7d5'
'info depth 15 multipv 1 score cp 52 nodes 48000 pv e2e4 e7e5 g1f3'

// Bestmove (signals search complete):
'bestmove h5f7 ponder d8h4'

// Stop-result bestmove (arrive immediately after 'stop', must be discarded):
// Indistinguishable from a real bestmove — only stopPendingRef distinguishes them
'bestmove e2e4 ponder e7e5'
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `go nodes 1000000` (server-side budget) | `go movetime 1500` as primary bound | SF17+ lichess analysis | Consistent wall-clock UX on heterogeneous hardware |
| Full SF18 single-thread (HCE, ~30-100 MB) | `stockfish-18-lite-single` (NNUE, ~7 MB) | SF18 release | Smaller AND stronger than full single-thread |
| Manually download WASM binary | npm package `stockfish` ships built binaries | SF17 era | Version-pinned, reproducible |
| Module Worker (`{ type: 'module' }`) | Classic Worker (no option) | — | Emscripten output requires classic; module Worker breaks self-bootstrapping |

**Deprecated/outdated:**
- `stockfish.wasm` (lichess older npm package): multi-thread only, no NNUE, passively maintained — do not use
- `@lichess-org/stockfish-web`: multi-thread only, requires SharedArrayBuffer — violates D-3
- `stockfish-18-single.js` (full single-thread): ~30-100 MB, HCE-only (no NNUE), paradoxically weaker — do not use

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `stockfish-18-lite-single.{js,wasm}` combined size is ~7 MB | Standard Stack / Summary | If the lite-single WASM has grown significantly, the iOS Cache-API limit calculation changes; verify at copy time |
| A2 | `initEngine('lite-single')` callback fires AFTER uciok/readyok (engine fully ready) | RESEARCH FLAG / Code Examples | If not ready, commands sent immediately after init may be queued or lost; add `readyok` listen in the Node test as a fallback |
| A3 | `vite preview` serves WASM with `Content-Type: application/wasm` | CI Guard code | If not, the CI MIME check will report false positives; verify by running `npm run build && npm run preview` locally first |
| A4 | Default `vite-plugin-pwa` `globPatterns` does NOT include `.wasm` extension | Pattern 5 | If the default includes `.wasm`, the Workbox exclusion is critical not just defensive; verify with `npm run build` and inspect `dist/sw.js` |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed. (This table is NOT empty — A1–A4 need verification during execution.)

---

## Open Questions

1. **`initEngine` output API — `listener` vs `onmessage` vs something else**
   - What we know: `examples/node_module.js` shows `engine.listener = function(line) {...}` receiving raw UCI string lines; `examples/node_direct.js` shows `engine.listener = function onLog(line) {...}`. Both are consistent.
   - What's unclear: Whether the `listener` property name is stable across v18 minor updates.
   - Recommendation: Use `engine.listener = fn` as documented in the examples. If initialization fails, check the current `node_modules/stockfish/index.js` for the exact property name.

2. **`globPatterns` default in `vite-plugin-pwa` v1.3.0**
   - What we know: PITFALLS.md says "audit the existing `vite.config.ts` `globPatterns` or `globIgnores`"; current config has neither.
   - What's unclear: The exact default `globPatterns` for `vite-plugin-pwa@1.3.0`.
   - Recommendation: After `npm run build`, inspect `dist/sw.js` for any `*.wasm` precache entry. Add `globIgnores: ['**/*.wasm']` regardless — it's defensive and documents intent.

3. **CI preview server availability after build**
   - What we know: `npm run preview` exists in `package.json`; `vite preview` serves `dist/` on port 4173.
   - What's unclear: Whether `vite preview` needs `--outDir frontend/dist` when run from project root vs from `frontend/`.
   - Recommendation: Run the CI guard step with `working-directory: frontend` and `npm run preview -- --port 4173`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js 24 | Integration test (`initEngine`) + CI | Yes | v24.14.0 | — |
| npm | `npm install stockfish` | Yes | 11.9.0 | — |
| Vitest | Unit + integration tests | Yes | 4.1.7 | — |
| `vite preview` | CI COOP/COEP guard | Yes (part of vite@8) | 8.0.14 | `npx serve dist` (no MIME guarantee) |
| curl | CI header checks | Yes (ubuntu-latest) | system | — |
| `stockfish` npm pkg | Integration test WASM | Not yet installed | 18.0.8 | — |

**Missing dependencies with no fallback:**
- `stockfish` npm package (not yet in `package.json`) — must be installed before the integration test can run.

**Missing dependencies with fallback:**
- None beyond the above.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.7 |
| Config file | none (default from vite.config.ts, test key absent — uses defaults) |
| Quick run command | `npm test` (from `frontend/`) |
| Full suite command | `npm test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGINE-01 | `evalCp` / `evalMate` emitted for a FEN | integration | `npm test -- --reporter=verbose src/hooks/__tests__/useStockfishEngine.integration.test.ts` | No — Wave 0 |
| ENGINE-02 | `pvLines` has 2 entries with moves after search | integration | same | No — Wave 0 |
| ENGINE-03 | `pvLines[0].moves[0]` is a valid UCI move string | integration | same | No — Wave 0 |
| ENGINE-04 | `isReady` transitions false→true after init | integration | same | No — Wave 0 |
| ENGINE-05 | Debounce: rapid FEN changes do not flood engine | unit (mock worker) | `npm test -- src/hooks/__tests__/uciParser.test.ts` | No — Wave 0 |
| PLAT-01 | No COOP/COEP headers in build output | CI guard (curl) | CI `ci.yml` step | No — Wave 0 |
| PLAT-02 | `globIgnores` excludes WASM from SW manifest | unit (vite config) | inspect `dist/sw.js` post-build | No — Wave 0 |

**UCI parser unit tests (no req ID but foundational):**

| Behavior | Test Type | Command |
|----------|-----------|---------|
| `lowerbound` line does NOT update evalCp | unit | `npm test` |
| `upperbound` line does NOT update evalCp | unit | `npm test` |
| `score mate 0` returns `evalMate = 0` (terminal) | unit | `npm test` |
| `score mate -3` returns `evalMate = -3` (losing) | unit | `npm test` |
| Interleaved MultiPV produces correct `pvLines[1]` | unit | `npm test` |
| `bestmove` with `stopPendingRef = true` is discarded | unit (mock) | `npm test` |

### Sampling Rate
- **Per task commit:** `npm test`
- **Per wave merge:** `npm test` + `npm run build` + `npm run lint` + `npx tsc -b`
- **Phase gate:** Full pre-merge gate: `npm run build && npm run lint && npm test && npm run knip`

### Wave 0 Gaps

- [ ] `src/hooks/__tests__/uciParser.test.ts` — UCI parser unit tests (covers lowerbound/upperbound, mate 0, mate -N, MultiPV interleaving, bestmove)
- [ ] `src/hooks/__tests__/useStockfishEngine.integration.test.ts` — `initEngine('lite-single')` FEN→bestmove end-to-end
- [ ] `src/hooks/useStockfishEngine.ts` — the hook itself (RED → GREEN flow)
- [ ] `public/engine/stockfish-18-lite-single.js` + `.wasm` — vendor files (binary, not source)
- [ ] Vitest environment for integration test: `// @vitest-environment node` in the integration test file (the rest of the suite uses `// @vitest-environment jsdom`)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in Phase 136 |
| V3 Session Management | No | Hook is stateless per-session |
| V4 Access Control | No | No endpoint in this phase |
| V5 Input Validation | Yes (limited) | UCI output from Worker is trusted (same origin); FEN strings passed to engine are user-controlled but Emscripten sandboxed — no injection risk |
| V6 Cryptography | No | No crypto in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidental COOP/COEP enables SharedArrayBuffer | Elevation of Privilege (OAuth bypass) | CI `curl -I` guard; `optimizeDeps.exclude` prevents bundler from introducing SAB deps |
| Malicious postinstall script in `stockfish` pkg | Tampering | checkpoint:human-verify before install; postinstall is symlink-only (verified via `npm view stockfish scripts.postinstall`) |
| WASM binary tampering (supply chain) | Tampering | Committed to git (D-03): SHA verified at commit time; no runtime fetch of engine binary |

---

## Sources

### Primary (HIGH confidence — project-internal)
- `.planning/phases/136-usestockfishengine-hook-wasm-setup/136-CONTEXT.md` — locked decisions D-01..D-04, phase boundary, specifics
- `.planning/research/PITFALLS.md` — all 10 pitfalls; Pitfalls 1–8 directly apply to Phase 136
- `.planning/research/STACK.md` — Vite wiring, `optimizeDeps.exclude`, `public/engine/`, UCI pattern
- `.planning/research/ARCHITECTURE.md` — `useStockfishEngine` hook contract, state machine, stop-pending pattern
- `.planning/research/SUMMARY.md` — executive summary, open questions, confidence assessment
- `.planning/REQUIREMENTS.md` — ENGINE-01..05, PLAT-01/02 requirement text
- `frontend/vite.config.ts` — existing VitePWA / Workbox config (direct inspection)
- `frontend/src/hooks/useDebounce.ts` — existing debounce utility (direct inspection)
- `frontend/src/hooks/useTacticLine.ts` — hook convention reference (direct inspection)
- `.github/workflows/ci.yml` — existing CI workflow structure (direct inspection)

### Secondary (MEDIUM confidence — web-verified)
- [stockfish npm registry](https://registry.npmjs.org/stockfish/18.0.8) — v18.0.8 publish date, maintainer, bin, main field
- [nmrugg/stockfish.js examples/node_module.js](https://github.com/nmrugg/stockfish.js/blob/master/examples/node_module.js) — `engine.listener` API and Node.js usage pattern
- [nmrugg/stockfish.js examples/node_direct.js](https://github.com/nmrugg/stockfish.js/blob/master/examples/node_direct.js) — `engine.listener` confirmed in direct WASM example
- [nmrugg/stockfish.js scripts/postinstall.js](https://github.com/nmrugg/stockfish.js/blob/master/scripts/postinstall.js) — confirms postinstall is symlink-only, no network access
- [stockfish npm WebSearch](https://www.npmjs.com/package/stockfish) — file layout in `src/` directory confirmed, lite-single files confirmed
- [vitest-dev/vitest issue #6118](https://github.com/vitest-dev/vitest/issues/6118) — `@vitest/web-worker` WASM import failure confirmed

### Tertiary (LOW confidence — context only)
- [stockfish npm @vitest/web-worker](https://www.npmjs.com/package/@vitest/web-worker) — simulates Worker in same thread; MessageChannel-based
- [UCI specification](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-&-Commands.html) — lowerbound/upperbound semantics, mate 0, multipv behavior

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — `stockfish` v18.0.8 confirmed on npm registry; file layout confirmed via WebSearch; API confirmed via GitHub examples (not direct install)
- Architecture: HIGH — based on prior milestone research (STACK.md, PITFALLS.md, ARCHITECTURE.md) with codebase-verified integration points; plus this session's Node.js API verification
- Integration test harness: MEDIUM — `initEngine` + `engine.listener` API confirmed from official examples; specific v18 behavior not directly tested in this session
- Pitfalls: HIGH — directly from PITFALLS.md (codebase-verified + official docs cross-checked)
- CI guard: MEDIUM — CI workflow structure confirmed; `vite preview` approach is well-established but not CI-tested for this specific project

**Research date:** 2026-06-26
**Valid until:** 2026-07-26 (stockfish v18.0.8 is very new; check for patch releases before committing binaries)

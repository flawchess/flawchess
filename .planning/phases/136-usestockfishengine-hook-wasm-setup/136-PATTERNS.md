# Phase 136: `useStockfishEngine` Hook + WASM Setup - Pattern Map

**Mapped:** 2026-06-26
**Files analyzed:** 7 new/modified files
**Analogs found:** 5 / 7 (2 flagged as no-analog)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/hooks/useStockfishEngine.ts` | hook | event-driven | `frontend/src/hooks/useTacticLine.ts` | role-match (no worker-lifecycle analog exists) |
| `frontend/src/hooks/__tests__/uciParser.test.ts` | test | transform | `frontend/src/hooks/__tests__/useScrollDirection.test.ts` | role-match |
| `frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts` | test | event-driven | none — node-env integration test is a first in this codebase | no-analog |
| `frontend/vite.config.ts` | config | — | self (modify in-place) | exact |
| `frontend/public/engine/` (binary assets) | static asset | — | `frontend/public/openings.tsv` (verbatim static file reference pattern) | partial |
| `.github/workflows/ci.yml` | CI config | — | self (modify in-place) | exact |
| `frontend/package.json` + `README` | config/docs | — | self (modify in-place) | exact |

---

## Pattern Assignments

### `frontend/src/hooks/useStockfishEngine.ts` (hook, event-driven)

**Analog:** `frontend/src/hooks/useTacticLine.ts`

**NOTE — No worker-lifecycle analog exists in this codebase.** This is the first `new Worker(...)` call anywhere in the frontend. The patterns below are extracted from the closest hook analog (useTacticLine) for conventions; the worker-specific patterns come from RESEARCH.md and are quoted here for planner reference.

**Imports pattern** (`useTacticLine.ts` lines 19-22):
```typescript
import { useRef, useState, useCallback, useEffect } from 'react';
```
For `useStockfishEngine.ts`, add `useRef` (for `workerRef`, `stopPendingRef`, `stateRef`, `currentFenRef`, `isReadyRef`) and `useState` (for `evalCp`, `evalMate`, `pvLines`, `depth`, `isAnalyzing`, `isReady`). No `useCallback` needed unless expose control functions.

**Interface / return-type pattern** (`useTacticLine.ts` lines 26-80):
```typescript
// Declare input options interface first, then return-value interface, then the hook.
export interface UseStockfishEngineOptions {
  fen: string | null;  // null = engine idle (not yet on analysis page)
  enabled: boolean;
}

export interface StockfishEngineState {
  evalCp: number | null;
  evalMate: number | null;
  pvLines: PvLine[];
  depth: number;
  isAnalyzing: boolean;
  isReady: boolean;
}
```

**Ref-for-latest-value pattern** (`useTacticLine.ts` lines 99-110):
```typescript
// Mutable refs updated each render so callbacks always see the latest values
// without closing over stale state.
const historyRef = useRef<string[]>(history);
const currentPlyRef = useRef<number>(0);
useEffect(() => {
  historyRef.current = history;
  currentPlyRef.current = currentPly;
});
```
Apply the same pattern for `currentFenRef`, `isReadyRef`, and `stateRef` in `useStockfishEngine`.

**Event listener teardown pattern** (`useTacticLine.ts` lines 183-197):
```typescript
useEffect(() => {
  const container = containerRef.current;
  if (!container) return;
  const handleKeyDown = (e: KeyboardEvent) => { ... };
  container.addEventListener('keydown', handleKeyDown);
  return () => container.removeEventListener('keydown', handleKeyDown);
}, [goBack, goForward]);
```
Mirror for `visibilitychange`:
```typescript
useEffect(() => {
  const handleVisibility = () => { ... };
  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, []);  // stable refs — no deps needed if wired through refs
```

**Worker lifecycle (no codebase analog — from RESEARCH.md Pattern 3):**
```typescript
// Mount: create classic (non-module) Worker; Emscripten requires no { type: 'module' }.
useEffect(() => {
  const worker = new Worker('/engine/stockfish-18-lite-single.js');
  workerRef.current = worker;
  worker.onmessage = (e: MessageEvent<string>) => { handleLine(e.data); };
  worker.postMessage('uci');
  // handleLine transitions to setoption + isready after 'uciok'
  return () => {
    worker.postMessage('stop');
    worker.terminate();
    workerRef.current = null;
  };
}, []); // mount only
```

**Debounce reuse** (`frontend/src/hooks/useDebounce.ts` lines 1-10):
```typescript
export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```
Use `const debouncedFen = useDebounce(fen, 150)` then `useEffect` on `debouncedFen` to fire `analyze()`. This is the Layer A debounce guard (RESEARCH.md locked: 150ms).

**noUncheckedIndexedAccess guard** (`useTacticLine.ts` line 124):
```typescript
// Use non-null assertion with a comment when the index is provably in bounds:
const move = chess.move(hist[i]!);
// Or assign to const and check:
const token = tokens[idx];
if (token === undefined) return null;
```
UCI token parsing (`parseInfoLine`) reads array indices — apply the same narrowing: assign each token to a `const`, check `=== undefined` before use, and only then parse to number.

---

### `frontend/src/hooks/__tests__/uciParser.test.ts` (test, transform)

**Analog:** `frontend/src/hooks/__tests__/useScrollDirection.test.ts`

**File header pattern** (lines 1-6):
```typescript
// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
```
For the UCI parser (a pure function — no DOM needed), use:
```typescript
// @vitest-environment node
import { describe, it, expect } from 'vitest';
import { parseInfoLine } from '../uciParser';  // or wherever the module lives
```

**Test structure pattern** (`useScrollDirection.test.ts` lines 22-107):
```typescript
describe('useScrollDirection', () => {
  it('returns "up" initially (at top of page)', () => { ... });
  it('returns "down" when scrollY increases past threshold', () => { ... });
  // One it() per behavior
});
```
Mirror for UCI parser:
```typescript
describe('parseInfoLine', () => {
  it('returns null for non-info lines', () => { ... });
  it('lowerbound line does NOT set bound="exact"', () => { ... });
  it('upperbound line does NOT set bound="exact"', () => { ... });
  it('exact score cp line returns scoreCp and bound="exact"', () => { ... });
  it('score mate 1 (winning)', () => { ... });
  it('score mate 0 (terminal — already checkmate)', () => { ... });
  it('score mate -3 (losing) returns scoreMate=-3', () => { ... });
  it('multipv 2 line extracts multipv index correctly', () => { ... });
  it('interleaved multipv lines: both parsed independently', () => { ... });
});
```

**Test input strings** (from RESEARCH.md Code Examples — UCI Parser Unit Test Inputs):
```
'info depth 12 multipv 1 score cp 45 lowerbound nodes 12000 pv e2e4 e7e5'
'info depth 12 multipv 1 score cp 60 upperbound nodes 14000 pv d2d4 d7d5'
'info depth 14 multipv 1 score cp 52 nodes 30000 pv e2e4 e7e5 g1f3'
'info depth 1 multipv 1 score mate 1 nodes 100 pv h5f7'
'info depth 0 multipv 1 score mate 0 nodes 1 pv '
'info depth 5 multipv 1 score mate -3 nodes 5000 pv e8f7 d1f3 f7e8 f3f7'
'info depth 15 multipv 2 score cp 18 nodes 45000 pv d2d4 d7d5'
'info depth 15 multipv 1 score cp 52 nodes 48000 pv e2e4 e7e5 g1f3'
'bestmove h5f7 ponder d8h4'
```

---

### `frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts` (test, event-driven)

**Analog:** None — this is the first `// @vitest-environment node` integration test that boots a real WASM binary. No existing precedent in `frontend/src/hooks/__tests__/`.

**Pattern from RESEARCH.md** (Integration Test Harness section):
```typescript
// @vitest-environment node

import { describe, it, expect } from 'vitest';

describe('Stockfish WASM integration (node entry point)', () => {
  it('returns bestmove for a mate-in-1 FEN', async () => {
    const initEngine = (await import('stockfish')).default;
    // ... initEngine('lite-single', callback) pattern
    // engine.listener = (line: string) => { ... }
    // engine.sendCommand(cmd)
    // Assert: bestmoveLine matches /^bestmove h5f7/
  }, 10_000); // 10s timeout for WASM init + 500ms search
});
```

**Key conventions to adopt:**
- `// @vitest-environment node` directive at top (not jsdom — no DOM APIs needed, WASM runs in Node)
- Dynamic `import('stockfish')` to avoid bundler touching the package
- 10_000ms timeout override (engine boot is slow)
- Assert `bestmove` for a **mate-in-1 FEN** (deterministic regardless of `eval_cp` hardware variance — see memory: eval non-determinism)
- Acceptable fallback: add `it.skipIf(process.env.CI === 'true')` wrapper if `initEngine` proves flaky in CI

---

### `frontend/vite.config.ts` (config, modify in-place)

**Analog:** Self

**Current VitePWA/Workbox block** (`vite.config.ts` lines 83-95):
```typescript
workbox: {
  navigateFallback: null,
  runtimeCaching: [
    {
      urlPattern: /^\/api\//,
      handler: 'NetworkOnly',
    },
  ],
},
```

**Required additions:**

1. Top-level `optimizeDeps` (add inside `defineConfig({...})`):
```typescript
optimizeDeps: {
  // Prevent Vite's esbuild optimizer from relocating the stockfish package JS
  // to .vite/deps/, which would break its relative WASM path.
  // Engine files live in public/engine/ and are served verbatim.
  // See: PITFALLS.md Pitfall 1.
  exclude: ['stockfish'],
},
```

2. Add `globIgnores` to the existing `workbox:` block:
```typescript
workbox: {
  navigateFallback: null,
  // Explicitly exclude WASM from SW precache (iOS Cache API ~50 MB limit).
  // The browser HTTP cache handles engine file caching instead.
  // See: PITFALLS.md Pitfall 2.
  globIgnores: ['**/*.wasm'],
  runtimeCaching: [
    {
      urlPattern: /^\/api\//,
      handler: 'NetworkOnly',
    },
  ],
},
```

**Existing plugin ordering to preserve** (`vite.config.ts` lines 41-98): `ogImageHashPlugin` → `react` → `tailwindcss` → `vitePrerenderPlugin` → `VitePWA` → `forceExitAfterBuild`. Do not reorder.

---

### `frontend/public/engine/` (static assets)

**Analog:** `frontend/public/openings.tsv` (verbatim static file referenced at runtime)

**Pattern:** Files in `frontend/public/` are served verbatim by Vite dev server and copied to `dist/` on build, accessible at the root URL path. No import statement; referenced by URL string in source.

```
frontend/public/openings.tsv  → served at /openings.tsv
frontend/public/engine/stockfish-18-lite-single.js   → served at /engine/stockfish-18-lite-single.js
frontend/public/engine/stockfish-18-lite-single.wasm → served at /engine/stockfish-18-lite-single.wasm
```

Worker instantiation uses the URL path:
```typescript
new Worker('/engine/stockfish-18-lite-single.js')
// Classic Worker — no { type: 'module' } argument.
```

Copy commands (run once after `npm install stockfish`, then commit):
```bash
mkdir -p frontend/public/engine
cp node_modules/stockfish/src/stockfish-18-lite-single.js  frontend/public/engine/
cp node_modules/stockfish/src/stockfish-18-lite-single.wasm frontend/public/engine/
git add frontend/public/engine/
```

---

### `.github/workflows/ci.yml` (CI config, modify in-place)

**Analog:** Self

**Insertion point:** After the `Run tests (vitest)` step (line 128) and before `Dead code check (knip)` (line 130). The guard requires a built `dist/` which is already produced by the preceding `Type check and build (tsc + vite)` step (line 124).

**Current step sequence** (`ci.yml` lines 122-133):
```yaml
- name: Type check and build (tsc + vite)
  run: npm run build
  working-directory: frontend

- name: Run tests (vitest)
  run: npm test
  working-directory: frontend

- name: Dead code check (knip)
  run: npm run knip
  working-directory: frontend
```

**New step to insert after `Run tests (vitest)`** (from RESEARCH.md CI Guard):
```yaml
- name: No COOP/COEP header guard + WASM MIME check
  run: |
    npm run preview -- --port 4173 &
    PREVIEW_PID=$!
    sleep 3

    FAIL=0

    PAGE_HEADERS=$(curl -sf -I http://localhost:4173/ 2>&1)
    echo "Page headers:"
    echo "$PAGE_HEADERS"
    if echo "$PAGE_HEADERS" | grep -qi 'cross-origin-opener-policy\|cross-origin-embedder-policy'; then
      echo "FAIL: COOP/COEP header found on page — breaks Google OAuth and iOS Safari"
      FAIL=1
    else
      echo "PASS: No COOP/COEP headers on page"
    fi

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

---

### `frontend/package.json` + `README` (modify in-place)

**Analog:** Self

**package.json:** After `checkpoint:human-verify` approval, add `"stockfish": "18.0.8"` under `"dependencies"`. The exact location in the sorted deps list follows alphabetical convention (after `react-*`, before `tailwind-*` — verify alphabetical order in the file).

**README:** Add a GPLv3 provenance note. Pattern: short prose note near the "Tech Stack" or "Dependencies" section. The Worker boundary keeps the GPL non-infective for the FlawChess application code (dynamic linking exception). Record:
- Package: `stockfish` v18.0.8 (nmrugg/stockfish.js)
- Files vendored: `stockfish-18-lite-single.js`, `stockfish-18-lite-single.wasm`
- License: GPLv3
- Source: `https://github.com/nmrugg/stockfish.js`

---

## Shared Patterns

### Hook ref-for-latest-value (avoids stale closure in event callbacks)
**Source:** `frontend/src/hooks/useTacticLine.ts` lines 99-110
**Apply to:** `useStockfishEngine.ts` — all `useRef` values accessed from `worker.onmessage` and `visibilitychange` handler
```typescript
// Sync refs to latest values each render — safe in useEffect (no render-phase mutation)
useEffect(() => {
  historyRef.current = history;
  currentPlyRef.current = currentPly;
});
```

### Event listener add/remove teardown
**Source:** `frontend/src/hooks/useTacticLine.ts` lines 183-197
**Apply to:** `useStockfishEngine.ts` — `visibilitychange` listener
```typescript
useEffect(() => {
  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, []);
```

### noUncheckedIndexedAccess narrowing
**Source:** `frontend/src/hooks/useTacticLine.ts` line 124
**Apply to:** `uciParser.ts` — all `tokens[i]` accesses
```typescript
// Pattern A: non-null assertion with provably-in-bounds access
const move = chess.move(hist[i]!);

// Pattern B: assign and narrow (preferred when bound is not proven)
const token = tokens[idx];
if (token === undefined) return null;
const value = parseInt(token, 10);
```

### Test file header
**Source:** `frontend/src/hooks/__tests__/useScrollDirection.test.ts` line 1, `useTacticLine.test.tsx` line 1
**Apply to:** all new test files
```typescript
// @vitest-environment jsdom   ← for hook tests using renderHook / DOM
// @vitest-environment node    ← for pure-function tests and WASM integration test
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/hooks/useStockfishEngine.ts` (worker lifecycle) | hook | event-driven | No existing `new Worker(...)` in the app. Worker create/message/terminate is a first. Establish the pattern here; Phases 137+ reference it. |
| `frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts` | test | event-driven | No `// @vitest-environment node` integration test that boots a real binary exists. All current tests in `__tests__/` use jsdom. This is a new test tier. |

---

## Metadata

**Analog search scope:** `frontend/src/hooks/`, `frontend/src/hooks/__tests__/`, `frontend/vite.config.ts`, `.github/workflows/ci.yml`, `frontend/public/`
**Files read:** 7 (useTacticLine.ts, useDebounce.ts, vite.config.ts, ci.yml, useTacticLine.test.tsx, useScrollDirection.test.ts, CONTEXT.md, RESEARCH.md)
**Pattern extraction date:** 2026-06-26

# Phase 154: Real Providers (Stockfish Worker Pool + Maia Queue) - Pattern Map

**Mapped:** 2026-07-06
**Files analyzed:** 4 (2 new source, 2 new test)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/lib/engine/workerPool.ts` | service (non-React worker orchestrator) | event-driven (Worker postMessage/onmessage) + request-response (`grade()` promise) | `frontend/src/hooks/useStockfishGradingEngine.ts` | exact (state machine + parsing), role-diff (hook vs plain module) |
| `frontend/src/lib/engine/maiaQueue.ts` | service (non-React worker orchestrator) | event-driven + request-response (`policy()` promise) | `frontend/src/hooks/useMaiaEngine.ts` | exact (protocol), role-diff (hook vs plain module) |
| `frontend/src/lib/engine/__tests__/workerPool.test.ts` | test | unit (mock Worker) | `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts` (if present) else `useMaiaEngine.test.ts` pattern | role-match |
| `frontend/src/lib/engine/__tests__/maiaQueue.test.ts` | test | unit (mock Worker) | `useMaiaEngine.test.ts` (mock Worker / `vi.stubGlobal`) | role-match |

Both new files consume the frozen `EngineProviders` contract in `frontend/src/lib/engine/types.ts` (not modified) and are plain TypeScript modules — **not** React hooks — so the analogs' React-specific plumbing (`useState`/`useEffect`/refs-as-render-sync) must be stripped down to plain closures/module-level state holding the same underlying state machine.

## Pattern Assignments

### `frontend/src/lib/engine/workerPool.ts` (service, event-driven/request-response)

**Analog:** `frontend/src/hooks/useStockfishGradingEngine.ts` (423 lines) — generalize its single-worker state machine into N independent instances behind a priority queue. Do not rewrite the grading protocol; copy it per-slot.

**Imports pattern** (lines 28-32):
```typescript
import { Chess } from 'chess.js';
import { parseInfoLine } from './uciParser';
import { sanToUci, uciToSquares } from '@/lib/sanToSquares';
import type { MoveGrade } from '@/lib/moveQuality';
```
For the pool, drop the React imports (`useCallback`, `useEffect`, `useMemo`, `useRef`, `useState`) entirely — this is a plain module, not a hook. Import `MoveGrade` from `@/lib/engine/types` instead (the frozen re-export), and add:
```typescript
import type { MoveGrade } from './types';
```

**Constants pattern** (lines 34-49) — copy the naming/tunable-constant convention exactly:
```typescript
const ENGINE_PATH = '/engine/stockfish-18-lite-single.js';
const GRADING_TARGET_DEPTH = 14;
const GRADING_MOVETIME_SAFETY_CAP_MS = 2500;
```
Add new pool-specific tunables per RESEARCH.md Pattern 4 (D-01 sizing):
```typescript
const DESKTOP_POOL_MIN = 2;
const DESKTOP_POOL_MAX = 4;
const DESKTOP_HEADROOM_CORES = 2;
const MOBILE_POOL_SIZE = 2;
const MOBILE_CORE_THRESHOLD = 4;
```
Also cap each worker's `Hash` UCI option low (Pitfall 1 mitigation, e.g. `setoption name Hash value 8`).

**Per-worker state-machine pattern** (lines 53-54, 106-137, 190-239, 286-384) — the core pattern to replicate N times:
```typescript
type EngineState = 'idle' | 'thinking' | 'stopping';

interface PoolWorkerSlot {
  worker: Worker;
  state: EngineState;
  stopPending: boolean;
  isReady: boolean;
  current: GradeRequest | null; // the in-flight request, or null when free
}
```
The `prepareSearch`-equivalent per-slot dispatch function must reproduce the exact stop-before-go dance (lines 190-239): if `state === 'thinking'`, send `stop` and mark `stopPending`/`stopping` — never send a new `position`/`go` while a stop is outstanding (FLAWCHESS-7V guard). The worker lifecycle block (lines 286-384) is the template for `createWorkerSlot()`/teardown: `new Worker(ENGINE_PATH)`, `worker.postMessage('uci')` on init, `worker.postMessage('stop'); worker.terminate();` on teardown.

**Core MultiPV send** (lines 232-236) — copy verbatim, parameterized by the slot's assigned request:
```typescript
worker.postMessage(`setoption name MultiPV value ${candidateUcis.length}`);
worker.postMessage(`position fen ${fenToGrade}`);
worker.postMessage(
  `go depth ${GRADING_TARGET_DEPTH} searchmoves ${candidateUcis.join(' ')} movetime ${GRADING_MOVETIME_SAFETY_CAP_MS}`,
);
```

**pv[0]-keying / white-POV normalization pattern** (lines 309-348) — this is the SC5 grep-audit-critical section, copy exactly:
```typescript
const parsed = parseInfoLine(line);
if (parsed === null) return;
const uci = parsed.pv[0];              // NEVER parsed.multipv
if (uci === undefined) return;
const whitePovSign = gradingSideRef.current === 'b' ? -1 : 1;
const toWhitePov = (v: number | null): number | null => (v === null ? null : v * whitePovSign);
// grade keyed by uci (pv[0]) directly for workerPool.ts — no SAN roundtrip needed
// since D-08 requires UCI-keyed grade() output (types.ts EngineProviders.grade).
```
Note: unlike the analog (which converts back to SAN for display via `sanFromUci`), `workerPool.ts`'s `grade()` must return `Map<string, MoveGrade>` keyed by the **UCI** string directly (`parsed.pv[0]`) per the frozen `EngineProviders` contract (D-08) — do not roundtrip through SAN.

**Cache pattern** (lines 126-127, 329-338) — single pool-level `Map<string, Map<string, MoveGrade>>` (per-FEN, not per-worker; per Anti-Patterns in RESEARCH.md), same FIFO eviction:
```typescript
const cacheRef = new Map<string, Map<string, MoveGrade>>();
// ...
if (cache.size > GRADE_CACHE_MAX) {
  const oldest = cache.keys().next().value;
  if (oldest !== undefined) cache.delete(oldest);
}
```

**Error handling / lifecycle** — no explicit try/catch in the analog (Worker messages are strings, not thrown exceptions); the equivalent containment is the `stopPendingRef`/state-machine discipline itself, plus the try/catch-return-null convention from `sanToUci`/`uciToSquares` at every worker-output boundary parsing a move string.

**New: priority queue (POOL-02)** — no direct analog; build per RESEARCH.md Pattern 2 (`.planning/phases/154.../154-RESEARCH.md` lines 273-320), a plain array + linear max-scan, tie-broken by depth then UCI string — matches the project's established "never insertion order" tie-break convention already used in `select.ts`'s canonical tie-breaking (see Phase 153 code).

**New: adaptive pool sizing (D-01)** — no direct analog (existing `useIsMobile`-style hooks are React-reactive; this must be a plain function computed once at lazy-spawn time per RESEARCH.md Pattern 4):
```typescript
function computePoolSize(): number {
  const cores = navigator.hardwareConcurrency || DESKTOP_POOL_MIN;
  const isCoarsePointer =
    typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches;
  const isMobile = cores <= MOBILE_CORE_THRESHOLD || isCoarsePointer;
  if (isMobile) return MOBILE_POOL_SIZE;
  return Math.min(DESKTOP_POOL_MAX, Math.max(DESKTOP_POOL_MIN, cores - DESKTOP_HEADROOM_CORES));
}
```

**Abort/lifecycle surface (D-03/Open Question 1)** — expose both an optional `AbortSignal` param on `grade()` (mirrors the frozen `SearchRunner` signature's own `signal` parameter from Phase 153's `guardrail.ts`/`mctsSearch.ts`) and a `pool.stopAll()`/`terminate()` method mirroring the analog's unmount cleanup (lines 378-383):
```typescript
return () => {
  worker.postMessage('stop');
  worker.terminate();
  workerRef.current = null;
};
```

---

### `frontend/src/lib/engine/maiaQueue.ts` (service, event-driven/request-response)

**Analog:** `frontend/src/hooks/useMaiaEngine.ts` (335 lines) — fork its single-worker `{type:'analyze', fen, eloInputs}` protocol into a non-React, per-node-narrow-ELO queue.

**Imports pattern** (lines 21-24), adapted (drop React, keep Sentry + encoding + new UCI helper):
```typescript
import * as Sentry from '@sentry/react';
import { maskAndSoftmax, MAIA_ELO_LADDER } from '../lib/maiaEncoding';
import { sanToUci } from '@/lib/sanToSquares';
```
(`softmaxWdl`/`expectedScore` are NOT needed — `policy()` only returns move probabilities per the frozen contract, no WDL.)

**Constants pattern** (lines 28-35):
```typescript
const ENGINE_PATH = '/maia/maia-worker.js';
const MAIA_CACHE_MAX = 256; // (fen, elo)-keyed, separate cache from useMaiaEngine's — D-04
```

**Worker protocol / message shape** (lines 73-85) — reuse verbatim, this is the wire contract `maia-worker.js` already implements:
```typescript
interface WorkerResultMessage {
  type: 'result';
  fen: string;
  rawPolicyByElo: { elo: number; policy: Float32Array }[];
  wdlByElo: { elo: number; wdl: Float32Array }[];
  backend: 'webgpu' | 'wasm';
}
type WorkerMessage =
  | { type: 'ready'; backend: 'webgpu' | 'wasm' }
  | WorkerResultMessage
  | { type: 'error'; message: string };
```

**Request send pattern** (line 180), adapted for D-04's narrow `eloInputs`:
```typescript
worker.postMessage({ type: 'analyze', fen: fenToAnalyze, eloInputs: dedupedElos }); // [eloW, eloB] or [elo], NOT MAIA_ELO_LADDER
```

**Deduping + batching (D-04)** — no direct analog (existing hook always requests the full ladder); build fresh per RESEARCH.md Pattern 3 (lines 322-370):
```typescript
async function requestPolicy(fen: string, elo: number, side: Side): Promise<Record<string, number>> {
  void side; // side is implicit in fen's own 'w'/'b' field (D-08)
  const cacheKey = `${fen}|${elo}`;
  const cached = cache.get(cacheKey);
  if (cached) return cached;
  const rawPolicy = await runMaiaAnalyze(fen, [elo]);
  const sanKeyed = maskAndSoftmax(rawPolicy, fen);
  const uciKeyed: Record<string, number> = {};
  for (const [san, prob] of Object.entries(sanKeyed)) {
    const uci = sanToUci(fen, san);
    if (uci !== null) uciKeyed[uci] = prob; // matches WR-07 drop-on-null convention
  }
  cache.set(cacheKey, uciKeyed);
  return uciKeyed;
}
```
**IMPORTANT deviation from the analog:** per RESEARCH.md Open Question 2, `maiaQueue` must NOT adopt `useMaiaEngine`'s single-in-flight-drop discipline (lines 169-183: "Keep a single inference in flight... Drop the request here"). Every `policy()` call issued by `mctsSearch.ts` needs an answer — use a **proper async FIFO queue** instead (queue requests, process one ONNX inference at a time, resolve each caller's own promise) so no expansion's `policy()` call is ever silently dropped/superseded.

**Sentry error forwarding pattern** (lines 268-277) — copy verbatim, this is the ONLY way Maia worker errors reach Sentry:
```typescript
Sentry.captureException(new Error(`Maia worker error: ${msg.message}`), {
  tags: { source: 'maia-worker', backend: backendRef.current ?? 'unknown' },
});
```
Use a distinct `source` tag value (e.g. `'maia-queue-worker'`) to distinguish from the chart's `'maia-worker'` tag per CLAUDE.md's "use tags for filterable dimensions" rule.

**Worker lifecycle** (lines 228-287) — same classic `new Worker(ENGINE_PATH)` + `{type:'init'}`/`{type:'terminate'}` handshake; lazy-spawn per D-02 (create on first `request()` call, not eagerly).

**Cache FIFO pattern** (lines 141-148) — copy verbatim, keyed by `${fen}|${elo}` instead of `fen` alone (D-04's separate `(fen, elo)`-keyed cache):
```typescript
const cacheResult = (key: string, result: T): void => {
  cache.set(key, result);
  if (cache.size > MAIA_CACHE_MAX) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
};
```

---

### `frontend/src/lib/engine/__tests__/workerPool.test.ts` / `maiaQueue.test.ts` (test)

**Analog:** existing Vitest mock-Worker pattern already used across `useMaiaEngine`'s and `useStockfishGradingEngine`'s test suites (and every `useIsMobile`-consuming component test for `navigator.hardwareConcurrency`/`matchMedia` stubbing) — reuse `vi.stubGlobal('Worker', MockWorker)` and `vi.stubGlobal('navigator', {...})`/`Object.defineProperty(window, 'matchMedia', ...)`. No new test infra needed.

**Priority-ordering test** (RESEARCH.md Code Examples, verifies POOL-02) — copy this shape directly:
```typescript
it('dequeues the higher-priority request first, regardless of enqueue order', () => {
  const pending: QueuedGradeRequest[] = [];
  enqueue(pending, { fen: FEN_A, candidateUcis: ['e2e4'], priority: 0.2, depth: 3, resolve: vi.fn() });
  enqueue(pending, { fen: FEN_B, candidateUcis: ['d7d5'], priority: 0.8, depth: 3, resolve: vi.fn() });
  const next = dequeueHighestPriority(pending);
  expect(next?.fen).toBe(FEN_B);
});
```

**Dedup test** (verifies D-04):
```typescript
it('requests only the distinct ELOs needed, not the full ladder', async () => {
  await Promise.all([
    maiaQueue.request(FEN, 1500, 'w'),
    maiaQueue.request(FEN, 1500, 'b'),
  ]);
  const analyzeCalls = mockWorker.messages.filter((m) => m.type === 'analyze');
  expect(analyzeCalls).toHaveLength(1);
  expect(analyzeCalls[0].eloInputs).toEqual([1500]);
});
```

**SC5 grep-audit smoke check** (not a vitest test, a CI/manual grep):
```bash
grep -rn "\.multipv" frontend/src/lib/engine/workerPool.ts   # expect no output
```

## Shared Patterns

### Classic (non-module) Worker lifecycle
**Source:** `useStockfishGradingEngine.ts` lines 286-384, `useMaiaEngine.ts` lines 228-287
**Apply to:** both `workerPool.ts` (N instances) and `maiaQueue.ts` (1 instance)
```typescript
const worker = new Worker(ENGINE_PATH); // classic, non-module — NOT `new Worker(url, {type:'module'})`
worker.onmessage = (e) => { /* handle */ };
worker.postMessage(/* init handshake */);
// teardown:
worker.postMessage('stop' /* or {type:'terminate'} */);
worker.terminate();
```

### Stop-before-go / stopPending serialization
**Source:** `useStockfishGradingEngine.ts` lines 190-239, 351-368
**Apply to:** every worker slot in `workerPool.ts`
```typescript
if (stateRef.current === 'thinking') {
  worker.postMessage('stop');
  stopPendingRef.current = true;
  stateRef.current = 'stopping';
  return;
}
if (stateRef.current === 'stopping') {
  return; // FLAWCHESS-7V guard — never race a stop in flight
}
```

### pv[0]-keying (never `.multipv`)
**Source:** `useStockfishGradingEngine.ts` lines 309-322, `uciParser.ts` `ParsedInfoLine.pv`
**Apply to:** `workerPool.ts` exclusively (only file that touches MultiPV `info` lines)
```typescript
const parsed = parseInfoLine(line);
const uci = parsed?.pv[0]; // the move identity — multipv is an eval RANK, reorders across depths
```

### try/catch-return-null at every worker-output move-string boundary
**Source:** `sanToSquares.ts` (`sanToUci`, `uciToSquares`, `fenAfterMove`)
**Apply to:** both new files, whenever converting SAN<->UCI or applying an untrusted move string
```typescript
export function sanToUci(fen: string, san: string): string | null {
  try {
    const chess = new Chess(fen);
    const move = chess.move(san);
    return `${move.from}${move.to}${move.promotion ?? ''}`;
  } catch {
    return null;
  }
}
```

### FIFO cache-cap eviction
**Source:** `useStockfishGradingEngine.ts` lines 329-338, `useMaiaEngine.ts` lines 141-148
**Apply to:** both files' internal caches (pool-level pv[0] grade cache; maiaQueue's `(fen, elo)` cache)
```typescript
cache.set(key, result);
if (cache.size > CACHE_MAX) {
  const oldest = cache.keys().next().value;
  if (oldest !== undefined) cache.delete(oldest);
}
```

### Sentry manual forwarding for classic-Worker errors
**Source:** `useMaiaEngine.ts` lines 268-277
**Apply to:** `maiaQueue.ts` (the Maia worker has no Sentry init; classic Worker errors never throw catchable exceptions on the main thread)
```typescript
Sentry.captureException(new Error(`Maia worker error: ${msg.message}`), {
  tags: { source: 'maia-queue-worker', backend: backendRef.current ?? 'unknown' },
});
```

## No Analog Found

| File/Concern | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Priority queue (POOL-02) | utility | transform/batch | No prior priority-queue code exists in the codebase — build fresh per RESEARCH.md Pattern 2 (plain array + linear max-scan, no library) |
| Adaptive pool sizing as a plain (non-hook) function (D-01) | utility | transform | Existing `useIsMobile()`-style device detection is React-reactive; this phase's non-hook constraint means a fresh plain-function equivalent, computed once at lazy-spawn time (RESEARCH.md Pattern 4) |
| N-worker pool coordination / slot assignment | service | event-driven | No existing pool abstraction in the codebase; genuinely new structural generalization of the single-worker state machine (RESEARCH.md Pattern 1) |

## Metadata

**Analog search scope:** `frontend/src/hooks/` (worker-wrapping hooks), `frontend/src/lib/engine/` (Phase 153 frozen core + types), `frontend/src/lib/` (maiaEncoding.ts, sanToSquares.ts)
**Files scanned:** `useStockfishGradingEngine.ts`, `useMaiaEngine.ts`, `uciParser.ts`, `maiaEncoding.ts`, `sanToSquares.ts`, `types.ts`, `mctsSearch.ts` (contract-consumer context)
**Pattern extraction date:** 2026-07-06

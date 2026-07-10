# Phase 154: Real Providers (Stockfish Worker Pool + Maia Queue) - Research

**Researched:** 2026-07-06
**Domain:** Client-side Web Worker pooling (Stockfish.wasm grading pool + dedicated Maia ONNX queue) implementing a frozen `EngineProviders` contract
**Confidence:** HIGH — grounded in direct reads of the shipped codebase (`useStockfishGradingEngine.ts`, `useMaiaEngine.ts`, `maia-worker.js`, `mctsSearch.ts`, `select.ts`, `types.ts`) plus milestone-level pre-phase research (`.planning/research/ARCHITECTURE.md`, `STACK.md`, `PITFALLS.md`) that already scoped this exact phase's design before the roadmap split it out. No new npm dependency and no external ecosystem research was needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Adaptive pool sizing (POOL-01, POOL-04)**
- **D-01 Cap + mobile floor:** Desktop pool size = `clamp(navigator.hardwareConcurrency − 2, 2, 4)`;
  mobile = 2 workers. "Mobile" is detected by `hardwareConcurrency ≤ 4` **OR**
  `matchMedia('(pointer: coarse)')` — deliberately NOT UA sniffing (brittle) and NOT
  `navigator.deviceMemory` (unavailable/coarse on Safari). Pool size and both detection
  thresholds are named tunable constants, revisited after the real-device UAT (SC4).

**Worker warm-up / lifecycle (POOL-01, POOL-04)**
- **D-02 Lazy spawn on first request:** The 2–4 SF workers and the Maia ONNX worker are
  created on the first engine search (via an `enabled`-style gate, mirroring the existing
  `useStockfishGradingEngine`/`useMaiaEngine` worker lifecycle), and terminated on
  idle/unmount. Keeps idle memory low — the binding concern on mobile Safari — at the cost
  of a slightly slower first result (WASM + ONNX load). No eager page-load spawn.

**Eval-bar mutual exclusion (POOL-04)**
- **D-03 Engine wins; the "engine busy" gate is wired in Phase 155:** When the FlawChess
  Engine pool runs a position, the standalone `useStockfishEngine` eval bar pauses on that
  same position (the engine already computes an objective root eval, so the bar is redundant
  during the run). **Phase 154's obligation:** make the pool cleanly startable / stoppable /
  abortable (per-worker stop-before-go, drop-in-flight on navigation) so a caller can gate
  it. The actual shared "engine active" signal that pauses the eval bar lives in the Phase
  155 hook — **flagged for the researcher** (see Open Questions below). 154 exposes the
  abort/lifecycle surface; it does not itself reach into the eval-bar hook.

**Maia inference granularity (POOL-03)**
- **D-04 Only needed ELOs, own cache:** Per node, `maiaQueue` requests only the distinct
  ELOs the search needs — the per-side pair `{w, b}` from `budget.elo`, deduped (often 2,
  sometimes 1) — NOT the full 600–2600 ladder. The worker already takes an `eloInputs`
  array, so pass `[eloW, eloB]` (deduped); minimal worker change. Cache is keyed by
  `(fen, elo)` and is **fully separate** from the standalone Maia chart's cache (the roadmap
  already locks a separate worker instance). No shared-cache coupling with `useMaiaEngine`.

### Claude's Discretion
- **SAN↔UCI at the Maia boundary:** `maskAndSoftmax` currently emits SAN-keyed probabilities,
  but `policy()` must return UCI-keyed (D-08 from Phase 153). Convert at the `maiaQueue`
  boundary (or add a UCI-emitting variant) — implementation detail, researcher/planner's call.
- **Priority queue internals (POOL-02):** the exact scheduling data structure and how
  "nodes under the currently-highest-scoring root line" is expressed as a priority key —
  researcher territory. Requirement: verified by a queue-ordering test (not FIFO/arrival).
- **grade() → worker mapping:** one `grade(fen, ucis)` call maps to one worker's
  `searchmoves`-restricted MultiPV search; pool parallelism comes from multiple concurrent
  `grade()` calls (the `budget.concurrency` in-flight expansions from D-03/Phase 153).
  Exact dispatch/queueing across the pool is Claude's discretion.
- Per-worker abort/navigation handling reuses the established stop-before-go / stopPending
  dance from `useStockfishGradingEngine`; grade-depth / movetime-cap constants carry over.
- Worker init/error handling, Sentry forwarding for the Maia worker (classic Worker, no
  Sentry init — forward via message, per `useMaiaEngine`), and cache cap sizes.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (SharedArrayBuffer multithreading, per-ELO
calibrated sigmoids, time-pressure conditioning, and Maia-2 dual-skill adoption remain
formally deferred in REQUIREMENTS.md → Future Requirements. The React hook, anytime UI,
board arrows, and game-review overlay are Phases 155–157.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POOL-01 | Stockfish child/leaf grading runs across a pool of 2–4 single-threaded Stockfish.wasm workers in parallel, no SharedArrayBuffer, no site-wide COOP/COEP | Pattern 1 (N-worker pool generalizing `useStockfishGradingEngine`), Standard Stack, Don't Hand-Roll |
| POOL-02 | A node-evaluation priority queue schedules grading work toward the currently-best root lines | Pattern 2 (priority queue design), Code Examples, verified by an explicit queue-ordering test |
| POOL-03 | Maia move-probability distributions per node, per-side ELO parameter, from a dedicated Maia worker reusing v1.32 client-side inference | Pattern 3 (`maiaQueue.ts`), SAN→UCI boundary conversion, D-04 minimal-eloInputs reuse |
| POOL-04 | Stockfish pool size adapts to device (memory ceiling), never runs concurrently with the standalone eval bar on the same position | Pattern 4 (adaptive sizing), Runtime State Inventory n/a (no persisted state), Common Pitfalls 1/2, Open Question 1 (eval-bar gate surface) |
</phase_requirements>

## Summary

Phase 154 has almost no algorithmic risk left — the genuinely novel logic (backup rule,
selection, guardrail contract) was locked and tested in Phase 153. This phase is **pure
generalization of an already-shipped, already-tested pattern**: `useStockfishGradingEngine.ts`
(Phase 151.1) is a complete, working single-worker implementation of exactly the grading
operation `EngineProviders.grade()` needs (`searchmoves`-restricted MultiPV, pv[0]-keyed
results, white-POV normalization, stop-before-go serialization, tab-hide pause). `workerPool.ts`
is `N` structurally-identical copies of that state machine, coordinated by a priority queue
instead of one FEN's request/response cycle. Likewise, `useMaiaEngine.ts` (Phase 151) is a
complete working single-instance wrapper around the `{type:'analyze', fen, eloInputs}` Maia
worker protocol; `maiaQueue.ts` is a non-React fork of it that requests only the two ELOs a
node needs (not the full ladder) and emits UCI-keyed (not SAN-keyed) probabilities.

Both new files are plain TypeScript modules in `lib/engine/` (NOT React hooks — that's
explicitly Phase 155). No new npm dependency: `stockfish@18.0.8` and `onnxruntime-web@1.27.0`
are already pinned and vendored; no maintained "Stockfish worker pool" or MCTS-priority-queue
library exists on npm, and at this workload's scale (hundreds of pending grades per search,
not millions) a hand-rolled array + linear max-scan priority queue is both correct and fast
enough — do not add `tinyqueue`/`heap-js`/`comlink`/`workerpool`.

The one real risk this phase carries is **mobile Safari's WASM memory ceiling** (~100MB
iPhone / ~200MB iPad for an entire page): a 2–4-worker Stockfish pool plus one Maia ONNX
session plus the existing `useStockfishEngine` eval bar can hold 3-6 independent WASM/ONNX
heaps concurrently, and the failure mode is a silent tab reload/crash with no catchable JS
exception. D-01 (adaptive pool sizing) and D-02 (lazy spawn) are both defenses against this,
not performance tuning — treat POOL-04's real-device UAT (SC4) as the actual gate, not the
unit tests.

**Primary recommendation:** Build `workerPool.ts` as N independent copies of
`useStockfishGradingEngine`'s worker state machine (one `idle`/`thinking`/`stopping` machine
per Worker instance) fed by a plain array-based priority queue (linear max-scan is correct at
this scale — no heap library), and build `maiaQueue.ts` as a single-instance, non-React fork
of `useMaiaEngine`'s `{type:'analyze', fen, eloInputs}` protocol requesting only
`[eloW, eloB]` deduped, converting `maskAndSoftmax`'s SAN keys to UCI at the boundary via the
already-existing `sanToUci()` helper.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stockfish grading pool (`workerPool.ts`) | Browser / Client (Web Worker) | Browser / Client (pure lib orchestration) | Heavy WASM compute must live off the main thread; the pool's dispatch/queue bookkeeping is cheap main-thread orchestration calling into N Worker instances |
| Node-evaluation priority queue (POOL-02) | Browser / Client (pure lib) | — | Pure in-memory scheduling logic, no I/O; lives inside `workerPool.ts`, not a separate service |
| Maia policy queue (`maiaQueue.ts`) | Browser / Client (Web Worker) | Browser / Client (pure lib orchestration) | Same rationale as the SF pool — ONNX inference is a Worker; queue/dedup logic is main-thread bookkeeping |
| Device-adaptive pool sizing (D-01) | Browser / Client (pure lib, computed once at lazy-spawn time) | — | Reads `navigator.hardwareConcurrency`/`matchMedia` — browser globals, no React state needed since it's computed once per pool lifetime, not reactively |
| Eval-bar mutual exclusion (POOL-04's "never concurrent" guarantee) | Browser / Client (React hook, Phase 155) | Browser / Client (lib abort surface, this phase) | The shared "engine active" signal is a cross-hook coordination concern — belongs in `useFlawChessEngine.ts` (Phase 155), not in this phase's Worker-facing lib code; this phase only guarantees the pool is cleanly start/stop/abortable |
| `EngineProviders` contract (`policy`/`grade` shapes) | Browser / Client (pure lib) | — | FROZEN in Phase 153's `types.ts` — this phase implements it, does not modify it |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `stockfish` (npm, vendors `stockfish-18-lite-single.{js,wasm}`) | 18.0.8 [VERIFIED: npm registry] | Leaf/candidate-move grading engine — the pool's Worker payload | Already vendored to `frontend/public/engine/`, non-bundler-processed classic Worker; confirmed latest on npm as of the Phase 153 milestone research (2026-06-15); no reason to bump mid-phase |
| `onnxruntime-web` | 1.27.0 [VERIFIED: npm registry] | Maia-3 ONNX inference runtime — the `maiaQueue` worker's payload | Already pinned in `package.json`; confirmed latest as of milestone research (2026-06-19); `maia-worker.js` already forces `ort.env.wasm.numThreads = 1` (Phase 136 D-3, no cross-origin isolation) |
| `chess.js` | ^1.4.0 [VERIFIED: npm registry] | Legal-move / FEN application, used identically to Phase 153's core | Already the sole external dependency the engine core touches; no new usage pattern needed |

### Supporting

None. No new dependency is required for this phase.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled N-Worker pool (structural copies of `useStockfishGradingEngine`'s state machine) | `workerpool` (npm, 10.0.3) / `comlink` (4.4.2) / `threads.js` (1.7.0) | **Rejected.** None of these fit a streaming, cancelable, stateful UCI session (`stop`/`bestmove` interleaving, stale-result discarding) — every existing engine hook in this codebase already solved that with a hand-rolled `idle`/`thinking`/`stopping` state machine + `stopPendingRef`. A wrapper library would fight that pattern (proxying, promise-per-call) rather than help it. |
| Plain array + linear max-scan priority queue | `tinyqueue` (3.0.0) / `heap-js` (2.7.1) | **Rejected at this scale.** SEED-082's node budgets are hundreds of pending grades per search, not tens of thousands — a binary heap's O(log n) insert/extract buys nothing measurable over O(n) linear scan at n≈dozens, and the plain array is trivially unit-testable for the POOL-02 ordering test. Revisit only if real budgets grow by 1-2 orders of magnitude. |
| `maiaQueue` requesting only `[eloW, eloB]` deduped (D-04) | Full `MAIA_ELO_LADDER` sweep per node (mirrors `useMaiaEngine`) | **Rejected by CONTEXT.md D-04.** The chart needs the full ladder for its curve; the search only ever consumes the two ELOs `budget.elo` specifies — sweeping 21 rungs per node would be ~10x wasted inference for no consumer. |
| No app-level Zobrist/transposition cache spanning pool workers | Per-worker or pool-shared position cache beyond the existing per-FEN `Map` | **Rejected — already decided in SEED-082/Phase 153/154 CONTEXT.** Positions diverge too fast in this MCTS tree to pay off; Stockfish's own internal TT (`Hash` UCI option, kept small — 8–16MB per instance) already gives partial reuse for free within one grading search. |

**Installation:**

No new packages. All dependencies (`stockfish`, `onnxruntime-web`, `chess.js`) are already
installed. Verify no drift before starting:

```bash
cd frontend && npm ls stockfish onnxruntime-web chess.js
```

**Version verification:** Ran `npm view` against the frontend's installed versions during
this research session — `stockfish@18.0.8` and `onnxruntime-web@1.27.0` are pinned exactly as
recorded in the milestone-level `STACK.md` research (dated 2026-07-05, itself npm-registry
verified). No further action needed; do not bump either during this phase.

## Package Legitimacy Audit

No new external packages are introduced in this phase — `workerPool.ts` and `maiaQueue.ts`
are new first-party TypeScript modules consuming already-vendored/already-pinned
dependencies (`stockfish`, `onnxruntime-web`, `chess.js`, all present in `package-lock.json`
since Phase 136/151). The Package Legitimacy Gate is not applicable; no `npm install` runs as
part of this phase's plan.

**Packages removed due to [SLOP] verdict:** none (no new packages)
**Packages flagged as suspicious [SUS]:** none (no new packages)

## Architecture Patterns

### System Architecture Diagram

```
                         Browser (main thread)
┌──────────────────────────────────────────────────────────────────────────┐
│  mctsSearch.ts (Phase 153, unmodified orchestrator)                       │
│    dispatchExpansion(leaf, path, budget, providers)                       │
│         │                                    │                            │
│         │ providers.policy(fen, elo, side)   │ providers.grade(fen, ucis) │
│         ▼                                    ▼                            │
│  ┌─────────────────────────┐      ┌──────────────────────────────────┐   │
│  │ lib/engine/maiaQueue.ts  │      │ lib/engine/workerPool.ts          │   │
│  │  - request(fen, elo,side)│      │  - grade(fen, candidateUcis)      │   │
│  │  - dedup {eloW, eloB}    │      │  - priority queue (POOL-02):      │   │
│  │  - cache (fen, elo)      │      │    enqueue({fen, ucis, priority}) │   │
│  │  - SAN→UCI at boundary   │      │    dequeue → highest-priority-    │   │
│  │    (sanToUci)            │      │    root-line-first, ties by       │   │
│  │  single in-flight        │      │    shallower depth then UCI       │   │
│  │  request (mirrors        │      │  - assigns each dequeued request  │   │
│  │  useMaiaEngine)          │      │    to the next FREE worker slot   │   │
│  └───────────┬──────────────┘      │  - per-worker idle/thinking/      │   │
│              │                     │    stopping state machine (N      │   │
│              │                     │    copies of useStockfishGrading  │   │
│              │                     │    Engine's stop-before-go dance) │   │
│              │                     └───────────┬────────────────────────┘  │
└──────────────┼─────────────────────────────────┼───────────────────────────┘
               ▼                                  ▼ (2-4 concurrent workers)
   ┌─────────────────────────┐       ┌─────────────────────────────────────┐
   │ Web Worker (1 instance)  │       │ Web Worker × N (2-4 instances)       │
   │ /maia/maia-worker.js      │       │ /engine/stockfish-18-lite-single.js  │
   │ onnxruntime-web, same      │       │ same vendored binary as              │
   │ binary as useMaiaEngine,   │       │ useStockfishGradingEngine, N          │
   │ SEPARATE instance/cache    │       │ SEPARATE instances/no shared state    │
   └───────────────────────────┘       └───────────────────────────────────────┘
```

No server round-trip anywhere in this diagram. No SharedArrayBuffer: every Stockfish worker
is single-threaded and independent (embarrassingly-parallel leaf grading — each `grade()`
call is ONE worker's full MultiPV search, not one search split across workers).

### Recommended Project Structure

```
frontend/src/lib/engine/
├── types.ts                 # EXISTING (Phase 153, frozen) — EngineProviders/SearchBudget/etc.
├── guardrail.ts              # EXISTING (Phase 153, frozen) — SearchRunner type
├── mctsSearch.ts / select.ts / backup.ts / leafScore.ts / treeCommon.ts / fallbackExpectimax.ts
│                              # EXISTING (Phase 153) — UNTOUCHED this phase
├── workerPool.ts              # NEW — implements EngineProviders.grade(); N-worker pool + priority queue
├── maiaQueue.ts                # NEW — implements EngineProviders.policy(); dedicated Maia worker
└── __tests__/
    ├── backup.test.ts / mctsSearch.test.ts / select.test.ts / fallbackExpectimax.test.ts / leafScore.test.ts
    │                          # EXISTING — unmodified
    ├── workerPool.test.ts      # NEW — mock-Worker unit tests (pool dispatch, priority ordering, lifecycle)
    └── maiaQueue.test.ts        # NEW — mock-Worker unit tests (dedup, cache, SAN→UCI, protocol)
```

No new top-level directory. `workerPool.ts`/`maiaQueue.ts` land beside the existing pure core
files in `lib/engine/` — they are the ONLY two files in that subsystem allowed to touch
`Worker`/`postMessage` (everything else stays worker-free per Phase 153's design).

### Pattern 1: N-worker pool as structural copies of an already-shipped single-worker state machine

**What:** `workerPool.ts` is `N` (2–4) independent instances of exactly the state machine
`useStockfishGradingEngine.ts` already implements: same `ENGINE_PATH`
(`/engine/stockfish-18-lite-single.js`), same classic (non-module) `new Worker(...)` load,
same `idle`/`thinking`/`stopping` machine, same `stopPendingRef` stale-bestmove guard, same
`pv[0]`-keyed (never `multipv`-rank-keyed) result parsing via `parseInfoLine`, same white-POV
sign normalization, same legal-only `searchmoves` construction. Do not invent a new worker
protocol — generalize the proven one.

**When to use:** Whenever an already-tested single-instance Worker wrapper needs to become a
parallel pool of independent instances doing the SAME operation on DIFFERENT inputs
(embarrassingly parallel — no shared state, no cross-worker coordination needed at the
protocol level).

**Example (per-worker slot shape, adapted from `useStockfishGradingEngine`'s ref-based state):**
```typescript
// Source: generalizing frontend/src/hooks/useStockfishGradingEngine.ts's proven pattern
interface PoolWorkerSlot {
  worker: Worker;
  state: 'idle' | 'thinking' | 'stopping';
  stopPending: boolean;
  isReady: boolean;
  /** The request currently assigned to this slot, or null when free. */
  current: GradeRequest | null;
}

function createWorkerSlot(): PoolWorkerSlot {
  const worker = new Worker(ENGINE_PATH); // same classic, non-module load as the grading hook
  const slot: PoolWorkerSlot = { worker, state: 'idle', stopPending: false, isReady: false, current: null };
  worker.postMessage('uci');
  worker.onmessage = (e: MessageEvent<string>) => handlePoolWorkerLine(slot, e.data);
  return slot;
}
```

### Pattern 2: Node-evaluation priority queue — plain array, linear max-scan (POOL-02)

**What:** A pending-request array of `{ requestId, fen, candidateUcis, priority, resolve, reject }`
entries. `priority` is derived from the CURRENT backed-up value of the root ancestor a
request's leaf descends from — nodes under the currently-highest-`practicalScore` root child
dequeue first; ties broken by shallower depth-from-root, then canonical ascending UCI-string
order (matching every other tie-break in the Phase 153 core — never insertion/arrival order).
On every worker-free event, scan the pending array for the max-priority entry and assign it
to that worker (O(n) scan, n = pending count, which at SEED-082's node-budget scale is at
most dozens — a heap buys nothing measurable here per `STACK.md`'s own sizing analysis).

**When to use:** Any time total pending work (mid-search grading requests) exceeds available
parallel workers (2–4) and requests are NOT equally valuable — the anytime/live-refining UX
needs the currently-best line to sharpen fastest.

**Example:**
```typescript
// Source: original — no maintained priority-queue library at this workload scale (STACK.md Q1)
interface QueuedGradeRequest {
  fen: string;
  candidateUcis: string[];
  /** Higher = more urgent. Derived by the caller from the root ancestor's current practicalScore. */
  priority: number;
  /** Tie-break 2: shallower depth-from-root wins. */
  depth: number;
  resolve: (grades: Map<string, MoveGrade>) => void;
}

function dequeueHighestPriority(pending: QueuedGradeRequest[]): QueuedGradeRequest | undefined {
  let best: QueuedGradeRequest | undefined;
  let bestIdx = -1;
  pending.forEach((req, i) => {
    const better =
      best === undefined ||
      req.priority > best.priority ||
      (req.priority === best.priority && req.depth < best.depth) ||
      (req.priority === best.priority && req.depth === best.depth &&
        (req.candidateUcis[0] ?? '') < (best.candidateUcis[0] ?? ''));
    if (better) { best = req; bestIdx = i; }
  });
  if (bestIdx >= 0) pending.splice(bestIdx, 1);
  return best;
}
```
**Verification requirement (POOL-02):** a dedicated `workerPool.test.ts` case must enqueue
requests in a DELIBERATELY non-priority arrival order (e.g. low-priority request first, then
a higher-priority one) and assert the higher-priority request is dispatched to the next free
worker FIRST — proving the ordering is priority-driven, not FIFO.

### Pattern 3: Dedicated single-instance Maia queue, forked (not shared) from `useMaiaEngine`

**What:** `maiaQueue.ts` owns ONE `new Worker('/maia/maia-worker.js')` instance — completely
separate from `useMaiaEngine`'s instance (SC3-style isolation, the same precedent
`useStockfishGradingEngine` already established relative to `useStockfishEngine`). Its
`request(fen, elo, side)` (implementing `EngineProviders.policy`) sends
`{type:'analyze', fen, eloInputs: dedupedElos}` where `dedupedElos` is `[budget.elo.w,
budget.elo.b]` deduped to `Set` size 1 or 2 (D-04) — NOT the full `MAIA_ELO_LADDER`. The
worker returns RAW policy/WDL logits exactly as it does today; `maiaQueue.ts` applies
`maskAndSoftmax` (from `maiaEncoding.ts`, same single source `useMaiaEngine` uses) to get
SAN-keyed probabilities for the REQUESTED elo rung, then converts every key to UCI via the
already-existing `sanToUci(fen, san)` helper before returning
`Promise<Record<string, number>>` (D-08's UCI-everywhere contract).

**When to use:** Whenever a new consumer needs the SAME underlying WASM/ONNX binary but has a
fundamentally different call pattern than the existing hook (chart wants the full ELO-ladder
curve in one shot; the search wants a narrow `{w,b}` pair per node, many times) — give it its
own worker instance and its own cache rather than retrofitting the existing hook's shape.

**Example:**
```typescript
// Source: forking frontend/src/hooks/useMaiaEngine.ts's protocol + frontend/src/lib/sanToSquares.ts's sanToUci
import { sanToUci } from '@/lib/sanToSquares';
import { maskAndSoftmax } from '@/lib/maiaEncoding';

async function requestPolicy(fen: string, elo: number, side: Side): Promise<Record<string, number>> {
  void side; // side is implicit in fen's own 'w'/'b' field (D-08); elo already picked by caller
  const cacheKey = `${fen}|${elo}`;
  const cached = cache.get(cacheKey);
  if (cached) return cached;

  const rawPolicy = await runMaiaAnalyze(fen, [elo]); // single-elo batch — worker already supports eloInputs.length===1
  const sanKeyed = maskAndSoftmax(rawPolicy, fen);
  const uciKeyed: Record<string, number> = {};
  for (const [san, prob] of Object.entries(sanKeyed)) {
    const uci = sanToUci(fen, san);
    if (uci !== null) uciKeyed[uci] = prob; // WR-07-style deterministic drop of any unconvertible SAN
  }
  cache.set(cacheKey, uciKeyed); // FIFO cap, mirrors MAIA_CACHE_MAX pattern
  return uciKeyed;
}
```
**Batching caveat:** when `mctsSearch.ts` needs BOTH `elo.w` and `elo.b` at the SAME node
(shouldn't happen structurally — `policy()` is called with exactly one `elo`/`side` per call,
per the frozen `EngineProviders` signature — see Code Context), `maiaQueue` still benefits
from batching the TWO distinct elos the search will need across a round of concurrent
expansions into one `eloInputs: [eloW, eloB]` inference when both are pending simultaneously,
rather than two serial single-elo inferences — this is an internal dispatch optimization
(Claude's Discretion), not a contract change.

### Pattern 4: Adaptive pool sizing as a plain function, not a React hook

**What:** Because `workerPool.ts` is explicitly NOT a React hook (no hook in this phase — that's
Phase 155), pool sizing (D-01) is a plain, non-reactive function computed ONCE at
lazy-spawn time (D-02), not a `useIsMobile()`-style hook with re-render-on-resize semantics
(the pattern used elsewhere in this codebase, e.g. `TagChip.tsx`, `ScoreChart.tsx`, but those
are all React components — this module has none). Compute it inside the pool's own
create-workers function.

**Example:**
```typescript
// Source: original — CONTEXT.md D-01's formula, expressed as a plain function
const DESKTOP_POOL_MIN = 2;
const DESKTOP_POOL_MAX = 4;
const DESKTOP_HEADROOM_CORES = 2; // reserve 2 cores for the main thread + Maia worker
const MOBILE_POOL_SIZE = 2;
const MOBILE_CORE_THRESHOLD = 4; // hardwareConcurrency <= this counts as "mobile"

function computePoolSize(): number {
  const cores = navigator.hardwareConcurrency || DESKTOP_POOL_MIN;
  const isCoarsePointer =
    typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches;
  const isMobile = cores <= MOBILE_CORE_THRESHOLD || isCoarsePointer;
  if (isMobile) return MOBILE_POOL_SIZE;
  return Math.min(DESKTOP_POOL_MAX, Math.max(DESKTOP_POOL_MIN, cores - DESKTOP_HEADROOM_CORES));
}
```
**Test note:** `navigator.hardwareConcurrency` and `window.matchMedia` must both be
stubbable in `workerPool.test.ts` (vitest `vi.stubGlobal`/`Object.defineProperty`, same
pattern already used across the frontend's existing `useIsMobile`-consuming component tests)
to cover the desktop/mobile/coarse-pointer branches deterministically.

### Anti-Patterns to Avoid

- **Splitting one `grade()` call's MultiPV search across multiple workers:** pool parallelism
  comes from multiple CONCURRENT `grade()` calls (one per in-flight expansion, up to
  `budget.concurrency`), each handled by ONE worker doing its own full
  `searchmoves`-restricted MultiPV search — never partition a single grade request's
  candidate set across workers.
- **A pool-shared cache fragmented per-worker:** the `pv[0]`-keyed grade cache is
  position-only (ELO-independent) and should be a SINGLE pool-level `Map`, not one cache per
  worker instance — a position graded by worker #2 must be servable from cache even if
  worker #0 is idle next time the same FEN is requested.
  (Note: some early milestone research suggested a fully shared cache across ALL pending
  requests; the D-04 boundary for `maiaQueue`'s cache is `(fen, elo)`-keyed and explicitly
  separate from `useMaiaEngine`'s cache — do not conflate the two caches.)
- **Feeding search results back into a Maia query to "sharpen" the prior:** `maiaQueue`'s
  `request()` must remain a pure function of `(fen, elo, side)` — never pass search state
  (visit counts, backed-up values, partial tree structure) into the Maia worker. This is the
  confirmed MCTS-degrades-Maia-accuracy pitfall from SEED-082's prior-art survey.
- **Applying worker-arrival order directly to caller state:** exactly as Phase 153's
  `mctsSearch.ts` already buffers-then-applies in canonical dispatch order (`Promise.all`),
  `workerPool.ts`'s own internal bookkeeping (which worker finished, in what order) must never
  leak non-determinism into the RETURNED `grade()` promise resolution beyond normal async
  ordering — the CALLER (mctsSearch) already handles determinism; the pool itself just needs
  to not introduce additional cross-request coupling.
- **UA-sniffing or `navigator.deviceMemory` for mobile detection:** explicitly rejected by
  D-01 — UA strings are brittle and `deviceMemory` is unavailable/coarse on Safari. Use
  `hardwareConcurrency` + `matchMedia('(pointer: coarse)')` only.
- **Eager page-load worker spawn:** explicitly rejected by D-02 — spawn lazily on first
  request, terminate on idle/unmount, to keep idle memory low (the binding mobile-Safari
  concern per `PITFALLS.md` Pitfall 1).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UCI `info` line parsing (depth/multipv/score/pv) | A new parser inside `workerPool.ts` | `parseInfoLine`/`parseBestmove` from `frontend/src/hooks/uciParser.ts` | Already pv[0]-keyed, already handles the lowerbound/upperbound bound-filtering pitfall; a second parser risks silently diverging on an edge case |
| SAN↔UCI conversion at the Maia boundary | A hand-rolled square-index/promotion parser in `maiaQueue.ts` | `sanToUci(fen, san)` / `uciToSquares(uci)` from `frontend/src/lib/sanToSquares.ts` | Already exists, already used by `useStockfishGradingEngine.ts` for the mirror-direction conversion; try/catch-return-null convention matches every other helper in this file |
| Maia board→tensor encoding, softmax, ELO ladder | Re-deriving the encoding math inside `maiaQueue.ts`'s worker-facing code | `maskAndSoftmax`/`MAIA_ELO_LADDER`/`softmaxWdl`/`expectedScore` from `frontend/src/lib/maiaEncoding.ts` | Single confirmed-contract source (151-MAIA-CONTRACT.md); the worker itself (`maia-worker.js`) intentionally does NOT replicate masking/softmax — only the main-thread caller applies it, exactly once, from this file |
| Priority-queue / heap data structure | `tinyqueue`/`heap-js`/a custom binary heap | Plain array + linear max-scan (Pattern 2) | At SEED-082's node-budget scale (hundreds of pending grades per search), O(n) linear scan is both correct and fast enough; a heap library is unjustified complexity for this workload |
| Worker RPC / message-passing wrapper | `comlink`/`workerpool`/`threads.js` | Raw `worker.postMessage`/`onmessage` + hand-rolled state machine | None of these libraries fit a streaming, cancelable, stateful UCI session (`stop`/`bestmove` interleaving); every existing engine hook in this codebase already solved this without a wrapper — following suit avoids fighting the abstraction |
| Eval→expected-score sigmoid | A new leaf-scoring formula inside pool/queue code | `leafExpectedScore`/`evalToExpectedScore` (already wired via `lib/engine/leafScore.ts` in Phase 153) | Not this phase's concern at all — `workerPool.ts`/`maiaQueue.ts` only produce raw `MoveGrade`/policy distributions; the sigmoid conversion happens in `mctsSearch.ts`, unchanged |
| App-level position/transposition cache spanning the whole tree | A Zobrist-hash-keyed cache shared across all pool workers | Stockfish's own internal `Hash` UCI option (small, e.g. 8–16MB per instance) + the existing per-FEN pv[0]-keyed grade cache pattern | Already explicitly rejected in SEED-082 — positions diverge too fast in MCTS for a transposition cache to pay off; don't reintroduce it here |

**Key insight:** every piece of "new" logic this phase needs already exists somewhere in the
codebase in single-instance form (grading state machine, Maia protocol, UCI parsing, SAN↔UCI
conversion, sigmoid). The entire phase is disciplined reuse plus one genuinely new piece (the
priority queue) that is intentionally small and hand-rolled because no library fits the exact
shape and the workload doesn't need one.

## Runtime State Inventory

Not applicable — this is a greenfield phase (two new pure-client files with no persisted
state, no database, no renamed identifiers). Skipped per protocol.

## Common Pitfalls

### Pitfall 1: Stockfish pool + Maia session exceed mobile Safari's memory ceiling

**What goes wrong:** Each Stockfish.wasm worker loads its own NNUE net into its own WASM
linear memory (no sharing across workers — that's what "no SharedArrayBuffer" means). A
2–4-worker pool plus one onnxruntime-web Maia session plus the pre-existing
`useStockfishEngine` eval bar (already running on `/analysis`) means the page can hold 3–6
independent WASM/ONNX heaps concurrently. Mobile Safari's observed hard ceiling is ~100MB
(iPhone) / ~200MB (iPad) for an ENTIRE page — far below WASM's theoretical 4GB limit — and
multiple WebKit bugs confirm memory growth is not released within a page's lifetime, so
repeated re-analysis across positions in a review session accumulates toward the ceiling
rather than plateauing.

**Why it happens:** Desktop Chrome development masks this completely (effectively unbounded
WASM memory in practice) — a design that "works great" locally can silently fail only for the
iOS Safari / installed-PWA segment, discovered late or never if the team dev-tests primarily
on desktop Chrome.

**How to avoid:**
- D-01's adaptive sizing (mobile = 2, desktop = clamp(cores-2, 2, 4)) and D-02's lazy
  spawn/idle-teardown are the primary mitigations — both already locked, implement exactly as
  specified.
- Cap each Stockfish worker's `Hash` UCI option low (e.g. 8–16MB) — MultiPV/searchmoves-
  restricted shallow grading doesn't benefit from a large hash table, and 4 workers at
  default Hash settings multiplies memory pressure for no search-quality gain.
- On iOS Safari, prefer the non-JSEP plain WASM execution provider for `onnxruntime-web` over
  WebGPU/JSEP if a choice arises — but `maiaQueue.ts` should reuse `maia-worker.js`'s EXISTING
  `initSession()` fallback logic verbatim (it already tries WebGPU with a warmup-run
  shader-failure guard, falling back to WASM) rather than reimplementing backend selection.
- Add a graceful-degradation floor: if pool/worker creation or first-inference fails, fall
  back to a smaller pool (down to 1) rather than crashing — flag this explicitly for the
  planner as a POOL-01/POOL-04 error-handling task, not an afterthought.

**Warning signs:** Chrome DevTools memory profile showing linear, non-decreasing WASM heap
growth across repeated grading cycles instead of a plateau; Sentry frontend errors spiking
from iOS Safari user agents with no clear JS stack (page-reload crashes often produce no
catchable exception — look for session/pageview drop-off filtered to iOS in analytics, not
Sentry alone).

**Phase-scope note:** SC4 ("on a real iPhone and a real mid-tier Android device...without the
browser tab reloading or crashing") is this pitfall's actual acceptance gate — treat it as a
mandatory HUMAN-UAT step in the plan, not something automatable in CI.

### Pitfall 2: Multipv-as-identity landmine (recurrence risk, already fixed once)

**What goes wrong:** Keying a grading result by the UCI `info` line's `multipv` field (a
1-based EVAL RANK that reorders as search depth climbs) instead of `pv[0]` (the actual move)
silently corrupts which move a grade belongs to — confirmed on the real binary during Phase
151.1's spike (151.1-01-SUMMARY.md).

**Why it happens:** `multipv` LOOKS like a stable per-move identity because it's an integer
index, but Stockfish reorders which move holds `multipv=1` as deeper iterative-deepening
passes change the ranking — a naive `results[multipv]` write is silently wrong the moment two
lines swap rank between depths.

**How to avoid:** Every new MultiPV consumption path in `workerPool.ts` must key by
`parsed.pv[0]`, using the SAME `parseInfoLine` from `uciParser.ts` that
`useStockfishGradingEngine.ts` already uses correctly — never re-derive parsing, never key by
`parsed.multipv`.

**Warning signs / verification:** the phase's own SC5 success criterion is a grep audit
(`grep -rn "\.multipv" frontend/src/lib/engine/`, or similar) confirming no new file reads
`.multipv` as a lookup key. A cheap regression test (already suggested in the milestone
research): assert that a synthetic sequence of `info` lines where `multipv` values for two
lines swap between two depths still produces grades keyed correctly by move, not by rank.

### Pitfall 3: Applying pool/worker results in raw arrival order

**What goes wrong:** If `workerPool.ts` resolves its returned `grade()` promise the instant
"whichever worker happens to finish first" completes, in a way that leaks into shared
mutable state (e.g. a naive global "last completed" pointer), non-determinism can enter
`mctsSearch.ts`'s ENGINE-07 bit-identical-output guarantee even though `mctsSearch.ts` itself
already buffers-then-applies via `Promise.all`'s order-preserving resolution.

**Why it happens:** `Promise.all` guarantees the ARRAY comes back in input order regardless
of resolution order — but only if `workerPool.ts`'s own dispatch code doesn't introduce a
SEPARATE side channel (e.g. writing to a shared cache keyed by insertion order, or mutating
shared queue state) that a later request could observe differently depending on real-world
timing.

**How to avoid:** Keep `workerPool.ts`'s per-request promise resolution fully independent —
each `grade(fen, ucis)` call returns its OWN promise tied to its OWN worker slot's result;
never let one request's completion order affect another's returned VALUE (only its dispatch
TIMING, which is fine — `mctsSearch.ts` already handles timing via `Promise.all`).

**Warning signs:** A determinism test (mirroring `mctsSearch.test.ts`'s existing
concurrency=2 ENGINE-07 test) that passes when run alone but flakes when the pool's internal
dispatch order is perturbed (e.g. by adding an artificial delay to one worker in a test).

### Pitfall 4: `sanToUci` failures silently shrinking the policy distribution

**What goes wrong:** `maskAndSoftmax` returns a SAN-keyed `Record<string, number>` for every
LEGAL move (verified via chess.js) — but `sanToUci(fen, san)` internally re-parses via
`chess.move(san)` and returns `null` on ANY unexpected failure. If this happens for even one
move, `maiaQueue`'s UCI-keyed output silently drops that move's probability mass, subtly
skewing `truncateAndRenormalize`'s top-k cut in `select.ts`.

**Why it happens:** `sanToUci` is a defensive try/catch-return-null helper (matches the
project's established style) — it was never exercised against a FULL legal-move enumeration
before (its existing callers pass a small candidate set from Phase 151.1's grading UI, not
every legal move at a position).

**How to avoid:** Add a `maiaQueue.test.ts` case asserting that for a representative set of
test positions (including promotions, castling, en passant), the UCI-keyed output has the
SAME number of entries as `maskAndSoftmax`'s SAN-keyed input (no silent drops) — this
functions as an implicit regression test for `sanToUci`'s coverage against the FULL legal-move
set, not just Phase 151.1's narrower candidate subset.

**Warning signs:** `Object.keys(uciPolicy).length !== Object.keys(sanPolicy).length` for any
FEN in a test fixture set.

## Code Examples

### Priority-queue ordering test (verifies POOL-02)

```typescript
// Source: original — the phase's own explicit "queue-ordering test" requirement
import { describe, it, expect } from 'vitest';

it('dequeues the higher-priority request first, regardless of enqueue order', () => {
  const pending: QueuedGradeRequest[] = [];
  enqueue(pending, { fen: FEN_A, candidateUcis: ['e2e4'], priority: 0.2, depth: 3, resolve: vi.fn() });
  enqueue(pending, { fen: FEN_B, candidateUcis: ['d7d5'], priority: 0.8, depth: 3, resolve: vi.fn() });
  // FEN_A was enqueued FIRST (would win under FIFO) but has LOWER priority.
  const next = dequeueHighestPriority(pending);
  expect(next?.fen).toBe(FEN_B); // priority wins, not arrival order
});
```

### Deduped ELO request (verifies D-04)

```typescript
// Source: original — CONTEXT.md D-04's "distinct ELOs only" requirement
it('requests only the distinct ELOs needed, not the full ladder', async () => {
  await Promise.all([
    maiaQueue.request(FEN, 1500, 'w'),
    maiaQueue.request(FEN, 1500, 'b'), // same numeric ELO as w — dedup collapses to ONE analyze call
  ]);
  const analyzeCalls = mockWorker.messages.filter((m) => m.type === 'analyze');
  expect(analyzeCalls).toHaveLength(1);
  expect(analyzeCalls[0].eloInputs).toEqual([1500]); // deduped, not [1500, 1500]
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Single grading worker, one FEN's candidate set at a time (`useStockfishGradingEngine`, Phase 151.1) | N-worker pool with priority-queued concurrent grading (`workerPool.ts`, this phase) | Phase 154 | The MCTS search core (Phase 153) needs many INDEPENDENT leaf evaluations across the tree per iteration; sequential grading would serialize the whole search behind one WASM instance |
| Full-ELO-ladder Maia sweep per FEN (`useMaiaEngine`, Phase 151) | Narrow `{eloW, eloB}`-only requests per node (`maiaQueue.ts`, this phase) | Phase 154 (D-04) | ~10x fewer wasted inferences per node — the search only ever consumes the two ELOs the budget specifies, never the full 21-rung ladder |

**Deprecated/outdated:** none — this phase does not deprecate any existing hook; both
`useStockfishGradingEngine.ts` and `useMaiaEngine.ts` remain in active use for the existing
Moves-by-Rating chart / grading UI, untouched.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Mobile Safari's page-level WASM memory ceiling is ~100MB (iPhone) / ~200MB (iPad) | Common Pitfalls 1 | This figure is carried from the milestone-level `PITFALLS.md` research (MEDIUM confidence there — cross-checked third-party sources, not FlawChess-device-measured). If the real ceiling differs materially, D-01's pool-size constants may need retuning after the SC4 real-device UAT — which is exactly why CONTEXT.md marks those constants "revisited after the real-device UAT" |
| A2 | A plain array + linear max-scan priority queue is fast enough at this phase's node-budget scale | Standard Stack (Alternatives), Don't Hand-Roll | If a later phase's SearchBudget.maxNodes grows by 1-2 orders of magnitude beyond SEED-082's stated scale, the O(n) scan could become a measurable bottleneck — revisit with a heap (`tinyqueue`) only if profiling shows this |
| A3 | `sanToUci` correctly round-trips every legal move (including promotions/castling/en passant) at the full-legal-move scale `maiaQueue` needs (not just the narrower candidate subset its existing caller passes) | Common Pitfalls 4 | Untested at full scale as of this research session — Pitfall 4's recommended coverage test closes this gap during implementation, not before |

**If this table is empty:** N/A — see above; A1/A2 carry from prior verified-but-not-project-measured research, A3 is a genuinely new-to-this-phase claim needing a same-phase test to confirm.

## Open Questions (RESOLVED)

1. **Where exactly does the "engine active" signal that pauses the standalone eval bar live?**
   - What we know: CONTEXT.md D-03 explicitly assigns this to Phase 155 (`useFlawChessEngine.ts`
     hook), and states Phase 154's obligation is only to make the pool "cleanly startable /
     stoppable / abortable (per-worker stop-before-go, drop-in-flight on navigation)."
   - What's unclear: the exact shape of the abort/lifecycle surface `workerPool.ts` must
     expose for Phase 155 to consume (a single `AbortController`-accepting `grade()` overload?
     a `pool.stopAll()` method? both?).
   - Recommendation: expose BOTH — accept an optional `AbortSignal` per `grade()` call
     (mirrors the frozen `SearchRunner` signature's own `signal` parameter, so
     `mctsSearch.ts`'s existing abort plumbing threads straight through with no new concept),
     AND a `pool.stopAll()` / `pool.terminate()` lifecycle method for Phase 155's mount/unmount
     and navigation-triggered teardown. Document this explicitly as the interface Phase 155
     will import, even though wiring the actual "pause the eval bar" signal is out of THIS
     phase's scope.

2. **Does `maiaQueue`'s single-in-flight-inference discipline (mirrored from `useMaiaEngine`) limit pool throughput under `budget.concurrency > 1`?**
   - What we know: `useMaiaEngine.ts` deliberately allows only ONE `analyze` in flight at a
     time (the ONNX runtime can't cancel a running inference) and drops/re-issues rather than
     queuing a backlog. `mctsSearch.ts` can dispatch UP TO `budget.concurrency` expansions
     concurrently, each needing its own `policy()` call.
   - What's unclear: whether `maiaQueue` should adopt the SAME single-in-flight-drop
     discipline (risking a policy() call silently never resolving for a superseded request)
     or a proper FIFO/async queue (never drops, but can build a backlog if ONNX inference is
     slower than the pool's grading throughput).
   - Recommendation: use a proper async queue (not a drop-and-reissue discipline) for
     `maiaQueue` — unlike `useMaiaEngine`'s UI-driven "always show the LATEST position"
     requirement, `mctsSearch.ts` needs an answer for EVERY dispatched expansion's `policy()`
     call (dropping one would leave a `Promise` unresolved, hanging that expansion forever).
     `.planning/research/ARCHITECTURE.md`'s Pattern 4/Concurrency section already calls this
     out: "`maiaQueue.ts` stays simple FIFO since ... each request is for a DIFFERENT position
     (no meaningful reordering benefit)" — confirms FIFO, not priority, and not drop-discard,
     for the Maia queue specifically (POOL-02's priority queue is SF-pool-only).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `stockfish` npm package (vendors the WASM binary) | POOL-01 | Yes | 18.0.8 [VERIFIED: npm registry] | — (already vendored to `public/engine/`) |
| `onnxruntime-web` | POOL-03 | Yes | 1.27.0 [VERIFIED: npm registry] | — (already vendored to `public/maia/`) |
| `chess.js` | policy/grade FEN handling | Yes | ^1.4.0 [VERIFIED: npm registry] | — |
| Web Worker API (classic, non-module) | POOL-01/POOL-03 | Yes (jsdom mock in tests; real in browser) | Browser built-in | Vitest unit tests use `vi.stubGlobal('Worker', MockWorker)`, same pattern as `useMaiaEngine.test.ts`/existing grading-engine tests |
| `navigator.hardwareConcurrency` | D-01 pool sizing | Yes (widely supported; Safari included) | Browser built-in | Falls back to `DESKTOP_POOL_MIN` (2) if `undefined`/`0` |
| `window.matchMedia('(pointer: coarse)')` | D-01 mobile detection | Yes (all modern browsers incl. Safari) | Browser built-in | Guarded with `typeof window.matchMedia === 'function'` (jsdom lacks it by default — every existing `useIsMobile`-consuming test in this codebase already stubs it) |
| Real iPhone + real mid-tier Android device | SC4 (POOL-04 UAT) | Not automatable in CI | — | HUMAN-UAT gate — plan must include an explicit manual verification step, not a substitute automated test |

**Missing dependencies with no fallback:**
- Real-device access for SC4's UAT gate (Pitfall 1's actual acceptance criterion) — this is a
  process/plan requirement (schedule a manual verification step), not a code fallback.

**Missing dependencies with fallback:** none blocking — all code-level dependencies are
already present and pinned.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest ^4.1.7 (existing, `frontend/vitest.config.ts` / `package.json` `test`/`test:watch` scripts) |
| Config file | `frontend/vitest.config.ts` (existing — no change needed) |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/__tests__/workerPool.test.ts src/lib/engine/__tests__/maiaQueue.test.ts` |
| Full suite command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POOL-01 | Pool creates 2–4 workers (device-dependent), each doing an independent `searchmoves`-restricted MultiPV search, no SAB usage | unit | `npx vitest run src/lib/engine/__tests__/workerPool.test.ts -t "pool size"` | ❌ Wave 0 |
| POOL-01 | `grade(fen, ucis)` returns a `Map<uci, MoveGrade>` keyed by `pv[0]`, white-POV normalized | unit | `npx vitest run src/lib/engine/__tests__/workerPool.test.ts -t "grade"` | ❌ Wave 0 |
| POOL-02 | A higher-priority pending request dequeues before a lower-priority one enqueued earlier (not FIFO) | unit | `npx vitest run src/lib/engine/__tests__/workerPool.test.ts -t "priority"` | ❌ Wave 0 |
| POOL-03 | `maiaQueue.request(fen, elo, side)` returns UCI-keyed probabilities, requesting only the distinct `{w,b}` ELOs (D-04, deduped) | unit | `npx vitest run src/lib/engine/__tests__/maiaQueue.test.ts -t "dedup"` | ❌ Wave 0 |
| POOL-04 | Pool size computed from `hardwareConcurrency`/`matchMedia` per D-01's formula across desktop/mobile/coarse-pointer branches | unit | `npx vitest run src/lib/engine/__tests__/workerPool.test.ts -t "computePoolSize"` | ❌ Wave 0 |
| POOL-04 | Pool exposes a clean stop/abort surface (per-worker stop-before-go, drop-in-flight) | unit | `npx vitest run src/lib/engine/__tests__/workerPool.test.ts -t "abort"` | ❌ Wave 0 |
| POOL-04 (SC4) | No tab reload/crash on a real iPhone + real mid-tier Android during a multi-position review session | manual | N/A — HUMAN-UAT | ❌ Wave 0 (process step, not code) |
| SC5 (multipv-as-identity grep audit) | No new file reads `.multipv` as a lookup key | smoke | `grep -rn "\.multipv" frontend/src/lib/engine/workerPool.ts` (expect no output) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd frontend && npx vitest run src/lib/engine/__tests__/workerPool.test.ts src/lib/engine/__tests__/maiaQueue.test.ts`
- **Per wave merge:** `cd frontend && npm test -- --run` (full frontend suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`; SC4's real-device manual pass
  recorded explicitly in the phase's UAT artifact (cannot be automated).

### Wave 0 Gaps

- [ ] `frontend/src/lib/engine/__tests__/workerPool.test.ts` — mock-Worker unit tests covering
      pool creation/sizing, priority-ordering, grade() correctness, stop/abort lifecycle
- [ ] `frontend/src/lib/engine/__tests__/maiaQueue.test.ts` — mock-Worker unit tests covering
      dedup, cache, SAN→UCI conversion coverage (Pitfall 4), protocol shape
- [ ] No new shared fixtures needed — reuse the existing `mockWorker`/`vi.stubGlobal('Worker', ...)`
      pattern already established in `useMaiaEngine.test.ts` and
      `useStockfishGradingEngine.test.ts`
- [ ] No framework install needed — Vitest already configured

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json`, so this section is
included per protocol. This phase remains, like Phase 153, a client-side-only computation
subsystem with no new network surface, no new user input surface, and no persistence — most
ASVS categories remain not-directly-applicable. The one new consideration versus Phase 153 is
that this phase DOES load and execute vendored WASM/ONNX binaries via `new Worker(...)`, which
is a supply-chain (not injection) concern.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surface in this phase |
| V3 Session Management | No | No session state introduced |
| V4 Access Control | No | No access-controlled resource |
| V5 Input Validation | Partial | `applyUciMoveFen`/`sanToUci`'s existing try/catch-return-null containment already handles malformed/illegal UCI from a worker boundary (WR-07, Phase 153); this phase's new files must preserve that same defensive style at the pool/queue boundary rather than trusting worker output blindly |
| V6 Cryptography | No | No cryptographic operation in this phase |
| V10 (Malicious Code / Supply Chain, ASVS 4.0 renumbering) | Yes | The vendored `stockfish-18-lite-single.{js,wasm}` and Maia ONNX/onnxruntime-web assets are already pinned/vendored (Phase 136/151); this phase adds no NEW vendored asset, just more Worker instances loading the SAME already-audited binaries — no new supply-chain surface, but worth noting explicitly since it was flagged as a forward-looking item in Phase 153's own RESEARCH.md |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/adversarial UCI move string from a compromised or buggy worker (e.g. a move legal in a DIFFERENT position) crashing the main thread | Tampering / Denial of Service | `chess.js`'s `.move()` throws on illegal input; `applyUciMoveFen`/`sanToUci` already contain this via try/catch-return-null (Phase 153 WR-07) — this phase's new pool/queue code must apply the SAME containment at every worker-output boundary, never assume worker output is well-formed |
| Uncontrolled worker/memory growth causing a denial-of-service against the user's OWN browser tab (not a remote attacker, but a real availability failure) | Denial of Service (self-inflicted) | D-01 adaptive sizing + D-02 lazy spawn/idle teardown (Common Pitfalls 1) — this is the PRIMARY security-adjacent risk this phase carries, even though it's framed as a performance/UX concern rather than a classic ASVS category |
| SharedArrayBuffer / cross-origin isolation requirement reintroducing the COOP `same-origin` header that breaks the existing Google OAuth popup flow | Tampering (via header misconfiguration) | Explicitly out of scope — POOL-01 requires "no SharedArrayBuffer, no site-wide COOP/COEP"; do not add multi-threaded WASM or any header change in this phase (locked D-3 from Phase 136, reaffirmed by this phase's own success criteria) |

## Sources

### Primary (HIGH confidence)

- Direct codebase reads: `frontend/src/lib/engine/types.ts`, `guardrail.ts`, `mctsSearch.ts`,
  `select.ts`, `backup.ts`, `treeCommon.ts` (Phase 153, frozen contract)
- Direct codebase reads: `frontend/src/hooks/useStockfishGradingEngine.ts`,
  `frontend/src/hooks/useMaiaEngine.ts`, `frontend/src/hooks/uciParser.ts`,
  `frontend/src/lib/maiaEncoding.ts`, `frontend/src/lib/sanToSquares.ts`,
  `frontend/public/maia/maia-worker.js` (the exact protocols/patterns generalized this phase)
- `.planning/phases/154-real-providers-stockfish-worker-pool-maia-queue/154-CONTEXT.md` — locked
  decisions D-01..D-04, discretion areas, canonical refs
- `.planning/phases/153-pure-search-core-guardrail-backup-mcts-fallback/153-CONTEXT.md` and
  `153-RESEARCH.md` — the frozen upstream contract and its own flagged Phase-154 forward notes
  (SAN→UCI conversion needed, `.multipv` grep-audit requirement)
- `.planning/REQUIREMENTS.md` — POOL-01..04 verbatim requirement text, Out of Scope table
- `npm view stockfish version` / `npm view onnxruntime-web version` — confirmed pinned versions
  match `frontend/package.json` exactly (18.0.8 / 1.27.0)

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md`, `.planning/research/STACK.md`,
  `.planning/research/PITFALLS.md` — milestone-level pre-phase research (2026-07-05) that
  already scoped this exact phase's design (Patterns 1-5, Pitfall 1's mobile-memory sizing,
  the priority-queue/library-rejection analysis) before the roadmap split it into Phase 154;
  cross-checked against the current codebase state during this session and found still
  accurate (no drift since 2026-07-05)
- Mobile Safari WASM memory ceiling figures (~100MB iPhone / ~200MB iPad) — carried from
  `PITFALLS.md`, itself citing lapcatsoftware.com (2026) + WebKit/emscripten bug reports;
  MEDIUM confidence there (third-party, not FlawChess-device-measured) — flagged in
  Assumptions Log A1

### Tertiary (LOW confidence)

- None used directly in this research session — all claims trace to either direct codebase
  reads or the already-vetted milestone-level research artifacts above.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency, exact versions confirmed against `package.json` and npm registry
- Architecture: HIGH — this phase's design was already fully scoped at the milestone-planning stage (`ARCHITECTURE.md`), cross-checked against the actual shipped Phase 151/151.1/153 code during this session
- Pitfalls: MEDIUM-HIGH — the multipv-as-identity and worker-arrival-order pitfalls are HIGH confidence (already proven/fixed once in this exact codebase); the mobile-memory ceiling figures are MEDIUM (third-party, not device-measured by this project yet — SC4's real-device UAT is the actual verification)

**Research date:** 2026-07-06
**Valid until:** 30 days (stable — no fast-moving dependency in this phase; re-verify `stockfish`/`onnxruntime-web` versions if this phase's planning is delayed past that window)

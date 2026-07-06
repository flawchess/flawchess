---
phase: 154-real-providers-stockfish-worker-pool-maia-queue
reviewed: 2026-07-06T14:51:35Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - frontend/src/lib/engine/workerPool.ts
  - frontend/src/lib/engine/__tests__/workerPool.test.ts
  - frontend/src/lib/engine/maiaQueue.ts
  - frontend/src/lib/engine/__tests__/maiaQueue.test.ts
findings:
  critical: 3
  warning: 5
  info: 5
  total: 13
status: issues_found
---

# Phase 154: Code Review Report

**Reviewed:** 2026-07-06T14:51:35Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the two real provider implementations (workerPool.ts for `EngineProviders.grade`, maiaQueue.ts for `EngineProviders.policy`) plus their test suites, cross-referencing types.ts (frozen contract), mctsSearch.ts (consumer), useStockfishGradingEngine.ts / useMaiaEngine.ts (mirrored state machines), uciParser.ts, and public/maia/maia-worker.js (wire contract).

The pv[0]-keying (SC5), white-POV normalization, stop-before-go serialization, FEN-batching/ELO-dedup (D-04), and lazy spawn (D-02) are all correctly implemented and well tested (39/39 green, knip clean). However, **three verified promise-hang defects** exist, all in lifecycle/error paths. Each was reproduced with a scratch test against the actual code during this review (not hypothesized): `stopAll()` and `terminate()` leave in-flight `grade()` promises hanging forever, and a Maia worker init error leaves every current and future `policy()` promise hanging forever. Because `mctsSearch.dispatchExpansion` awaits both providers per expansion, any of these deadlocks the entire engine search silently. Additionally, POOL-02 priority scheduling is unreachable through the public surface (priority is hardcoded to 0 with no caller channel).

## Critical Issues

### CR-01: `stopAll()` leaves in-flight `grade()` promises hanging forever

**File:** `frontend/src/lib/engine/workerPool.ts:361-375` (and the discard path at `253-264`)
**Issue:** `stopAll()` resolves only the queued (`pending`) requests. A request already dispatched to a slot (`slot.current`) is never settled: `stopAll` sends `stop` and sets `stopPending`, and when the terminal `bestmove` arrives, the FLAWCHESS-7V discard branch (`handleLine`, line 255) clears the slot **without resolving `slot.current`'s promise**. The comment there claims "the request was already settled elsewhere (abort path, Task 3) or will be re-dispatched" — that is true only for the AbortSignal path; for `stopAll` it is false: the request is neither settled nor re-dispatched. Reproduced: after `grade()` → dispatch → `stopAll()` → `bestmove`, the promise never resolves. Any Phase 155 caller that awaits `grade()` (as `mctsSearch.dispatchExpansion` does) and calls `stopAll()` mid-search deadlocks permanently. The existing test at `workerPool.test.ts:331-344` sidesteps this with `void second;` — the in-flight promise is deliberately never awaited because it would hang.
**Fix:** Settle in-flight requests in `stopAll()` before entering the stopping state:
```typescript
function stopAll(): void {
  for (const slot of slots) {
    if (slot.state === 'thinking') {
      slot.worker.postMessage('stop');
      slot.stopPending = true;
      slot.state = 'stopping';
      // Settle the in-flight request — its bestmove will be discarded by the
      // stopPending guard, so nothing else will ever resolve it.
      slot.current?.resolve(new Map());
      slot.current = null;
    }
  }
  ...
}
```
(The discard branch in `handleLine` already tolerates `slot.current === null`.) Then strengthen the test to `await expect(second).resolves.toEqual(new Map())`.

### CR-02: `terminate()` leaves in-flight `grade()` promises hanging forever

**File:** `frontend/src/lib/engine/workerPool.ts:377-388`
**Issue:** `terminate()` drains only the `pending` queue. A request in flight on a slot (`slot.current`) is never resolved, and since `worker.terminate()` kills the worker, no `bestmove` will ever arrive to trigger any cleanup path. Reproduced: `grade()` → dispatch → `terminate()` → promise hangs forever. Note the asymmetry: `maiaQueue.terminate()` (maiaQueue.ts:221-233) gets this right by folding `currentBatch` into the unresolved set — workerPool's `terminate()` must do the same for `slot.current`.
**Fix:**
```typescript
function terminate(): void {
  for (const slot of slots) {
    slot.worker.postMessage('stop');
    slot.worker.terminate();
    slot.current?.resolve(new Map());
    slot.current = null;
  }
  ...
}
```

### CR-03: maiaQueue — a worker init error hangs every current and future `policy()` promise

**File:** `frontend/src/lib/engine/maiaQueue.ts:161-187` (error branch) with `113-116` (`processQueue` ready-gate)
**Issue:** The `{type:'error'}` branch settles only `currentBatch`. If the worker errors **during init** — a real path: `maia-worker.js` wraps `initSession()` in try/catch and posts `{type:'error'}` on ONNX session/model-load failure (maia-worker.js:205-233), the exact failure class already seen in the field (FLAWCHESS WebGPU/onnx errors) — then `currentBatch` is `null`, `isReady` is still `false`, and the trailing `processQueue()` no-ops on the `!isReady` gate. Every request sitting in `pending` hangs forever. Worse, `worker` stays non-null, so every **subsequent** `policy()` call also queues behind the permanently-dead worker and hangs. Reproduced both behaviors. This directly contradicts the module docstring's guarantee (lines 26-29: "a construction failure or a worker error settles every affected promise instead of leaving it hanging") and deadlocks `mctsSearch` on its first expansion.
**Fix:** In the error branch, when the error arrives pre-ready (or unconditionally, as a conservative floor), also drain `pending`, and mark the worker dead so later calls fail fast:
```typescript
const failedBatch = currentBatch;
currentBatch = null;
if (failedBatch) for (const req of failedBatch) req.resolve({});
if (!isReady) {
  // Init failed: nothing will ever dispatch. Settle the whole queue and
  // drop the dead worker so a later policy() re-attempts a spawn.
  const stranded = pending.splice(0, pending.length);
  for (const req of stranded) req.resolve({});
  worker?.terminate();
  worker = null;
  return;
}
processQueue();
```

## Warnings

### WR-01: An already-aborted `AbortSignal` is silently ignored by `grade()`

**File:** `frontend/src/lib/engine/workerPool.ts:329-355`
**Issue:** `grade()` only calls `signal.addEventListener('abort', ...)`. The `abort` event fires solely on the aborted-state *transition* — a listener added to an already-aborted signal is never invoked. Reproduced: `controller.abort()` before `grade(fen, ucis, controller.signal)` still enqueues, dispatches, and runs the full search (the promise eventually resolves with real grades instead of the documented empty Map). Phase 155 threads the SearchRunner's signal straight through; a search aborted between expansions will keep burning worker time on every subsequent `grade()` call.
**Fix:** Check the flag first:
```typescript
if (signal?.aborted) return Promise.resolve(new Map());
```
before the cache lookup (or at minimum before `enqueue`).

### WR-02: POOL-02 priority scheduling is unreachable — `priority`/`depth` are hardcoded to 0 with no caller channel

**File:** `frontend/src/lib/engine/workerPool.ts:326` (also `58-66`, `102-139`)
**Issue:** `grade()` constructs every request as `{ priority: 0, depth: 0 }`. The `QueuedGradeRequest.priority` doc says it is "Derived by the caller from the root ancestor's current practicalScore (POOL-02)", but the public surface is the frozen 2-arg `EngineProviders.grade(fen, candidateUcis)` (+ optional signal) — no caller can ever supply a priority or depth, and the pool's internal `pending` array is closed over (the exported `enqueue`/`dequeueHighestPriority` operate on caller-owned arrays, not the pool's). Net effect: in the integrated path, dispatch order degenerates to ascending `candidateUcis[0]` string comparison — an arbitrary alphabetical order, not "toward the currently-highest-scoring root line first" as the module header (lines 4-5) and the plan's success criterion claim. The priority machinery is correct and tested in isolation but is dead code end-to-end. If the wiring is deferred to Phase 155, there is still no mechanism to defer *to* under the frozen contract.
**Fix:** Add a priority channel that doesn't break the frozen contract — e.g. an optional options bag (`grade(fen, ucis, signal?, hints?: { priority?: number; depth?: number })`, still structurally assignable to the 2-arg contract) or a pool-level `setPriorityHint(fen, priority)` map the MCTS orchestrator updates per root line. Alternatively, document explicitly that POOL-02 runtime scheduling lands in Phase 155 and how — the current header/docstrings claim behavior the module cannot exhibit.

### WR-03: No handling of asynchronous Worker load failure — hung promises, no Sentry (both modules)

**File:** `frontend/src/lib/engine/workerPool.ts:276-305`; `frontend/src/lib/engine/maiaQueue.ts:190-206`
**Issue:** Neither module sets `worker.onerror`. A Worker whose script fails to load (404, syntax error, CSP) does **not** throw from `new Worker(...)` — it fires an asynchronous `error` event. So workerPool's `try { slots.push(createSlot()) } catch { continue }` floor catches essentially nothing in practice: on a broken deploy, every slot exists but never reaches `readyok`, every queued `grade()` promise hangs forever, and no Sentry event is emitted. Relatedly, if *all* constructions do throw synchronously, `slots` is empty and `grade()` still enqueues into a queue nothing will ever service — the plan's "graceful-degradation floor... down to 1" (154-01-PLAN Task 3) has an actual floor of 0 with a silent hang. maiaQueue has the same script-load blind spot (its handled error path covers only messages the worker successfully posts).
**Fix:** In both `createSlot()`/`ensureSpawned()`, attach `worker.onerror = () => { ... }` that captures to Sentry (tagged `source`), marks the slot/worker dead, and — when no live ready slot remains — drains `pending`/`slot.current` with empty results. In workerPool's `ensureSpawned()`, if `slots.length === 0` after the spawn loop, resolve all pending requests empty instead of enqueueing into a dead queue.

### WR-04: Empty `catch { continue; }` swallows worker construction failures with no Sentry capture

**File:** `frontend/src/lib/engine/workerPool.ts:299-303`
**Issue:** The construction-failure catch block discards the error entirely. maiaQueue's equivalent path (`ensureSpawned`, maiaQueue.ts:197-205) captures the exception to Sentry with a source tag; workerPool imports no Sentry at all. A degraded pool (e.g. 2 of 4 slots on a memory-pressured mobile device) is exactly the signal the SC4 soak/UAT gate needs visibility into, and per project convention non-trivial catch blocks must capture.
**Fix:**
```typescript
} catch (err) {
  Sentry.captureException(err instanceof Error ? err : new Error(String(err)), {
    tags: { source: 'stockfish-worker-pool' },
  });
  continue;
}
```

### WR-05: `grade()` with an empty `candidateUcis` array is unguarded and emits malformed UCI

**File:** `frontend/src/lib/engine/workerPool.ts:194-203, 307-321`
**Issue:** With `candidateUcis = []`: (a) the cache check `[].every(...)` is vacuously true, so any previously-cached FEN "hits" and returns an empty Map (fine); but (b) on a cache miss the request dispatches `setoption name MultiPV value 0` plus `go depth 14 searchmoves  movetime 2500` — an empty `searchmoves` list, which Stockfish treats as "search all moves". The slot then burns up to the full movetime on an unrestricted search, and `cacheGrades` stores grades for moves nobody requested. The only current consumer (`mctsSearch.dispatchExpansion:306-312`) guards against this, but the pool is the public `EngineProviders.grade` surface and Phase 155+ adds more callers.
**Fix:** Early-return at the top of `grade()`:
```typescript
if (candidateUcis.length === 0) return Promise.resolve(new Map());
```

## Info

### IN-01: `cacheGrades` overwrites a FEN's richer cache entry instead of merging

**File:** `frontend/src/lib/engine/workerPool.ts:185-192, 268-270`
**Issue:** Each completed search replaces the FEN's whole cache entry with the latest accumulator. `grade(fen, [a,b,c])` then `grade(fen, [a,d])` discards the paid-for `b`/`c` grades. The mirrored `useStockfishGradingEngine` searches the union of already-graded + new SANs precisely to keep one coherent, growing per-FEN entry (useStockfishGradingEngine.ts:221-227). Never returns wrong data (cache hits require full candidate coverage) — just re-buys grades.
**Fix:** Merge into the existing entry (`const entry = cache.get(fen) ?? new Map(); for (const [k, v] of grades) entry.set(k, v);`), or union the search like the hook does.

### IN-02: Cached containers are shared by reference with callers

**File:** `frontend/src/lib/engine/workerPool.ts:269-270`; `frontend/src/lib/engine/maiaQueue.ts:154-155, 211-212`
**Issue:** workerPool resolves the same `Map` instance it caches (`slot.accumulator`), and maiaQueue both caches and resolves (and on cache hit, re-resolves) the same `Record` object. Any consumer that mutates its result corrupts the cache for all later callers. `mctsSearch` is currently read-only, so this is latent.
**Fix:** Resolve a copy (`new Map(slot.accumulator)` / `{ ...cached }`), or document the containers as frozen/read-only.

### IN-03: `computePoolSize()` undefined/0-cores fallback actually takes the mobile branch, not `DESKTOP_POOL_MIN`

**File:** `frontend/src/lib/engine/workerPool.ts:40-41, 156-163`; test `workerPool.test.ts:187-191`
**Issue:** With `hardwareConcurrency` 0/undefined, `cores` becomes `DESKTOP_POOL_MIN` (2), which then satisfies `cores <= MOBILE_CORE_THRESHOLD` and returns `MOBILE_POOL_SIZE`. The constant doc ("also the... undefined-cores fallback") and the test name ("falls back to DESKTOP_POOL_MIN") describe the desktop path; both only hold because `MOBILE_POOL_SIZE === DESKTOP_POOL_MIN === 2` today. These are documented as independently tunable knobs — tuning either silently changes fallback semantics while the test keeps passing or fails confusingly.
**Fix:** Make the unknown-cores fallback explicit (`if (!navigator.hardwareConcurrency) return MOBILE_POOL_SIZE;` — unknown hardware should get the conservative size) and align the doc/test naming.

### IN-04: Test quality — `void second;` hides the CR-01 hang; stale test-file header

**File:** `frontend/src/lib/engine/__tests__/workerPool.test.ts:334-344, 4-7`
**Issue:** The `stopAll()` test dispatches `second` in-flight and then discards its promise with `void second;` instead of asserting it settles — which is exactly the assertion that would have caught CR-01 (it can't be awaited today because it hangs). Similarly, no test covers `terminate()` with an in-flight request (CR-02) or a pre-aborted signal (WR-01). Also the file header still says "Task 1 covers the pure priority-queue... no Worker instantiation needed yet" although the file now covers dispatch and lifecycle (Tasks 2-3).
**Fix:** After fixing CR-01/CR-02: `await expect(second).resolves.toEqual(new Map())` in the stopAll test, add a terminate-with-in-flight test and a pre-aborted-signal test, and refresh the header.

### IN-05: maiaQueue caches `{}` permanently when the worker omits a requested ELO

**File:** `frontend/src/lib/engine/maiaQueue.ts:148, 154`
**Issue:** `sanByElo.get(req.elo) ?? {}` resolves and **caches** an empty policy for `(fen, elo)` if the worker's `rawPolicyByElo` lacks that ELO. The current maia-worker.js echoes `eloInputs` verbatim (verified, maia-worker.js:193-198), so this cannot fire today — but if the worker ever snaps/clamps ELOs to ladder rungs, the mismatch would silently poison the cache with permanent empty policies (no Sentry, no re-request). Defensive gap only.
**Fix:** Skip caching (and optionally Sentry-tag) when the requested ELO is missing from the result: `const sanKeyed = sanByElo.get(req.elo); if (!sanKeyed) { req.resolve({}); continue; }`.

---

_Reviewed: 2026-07-06T14:51:35Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

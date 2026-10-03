#!/usr/bin/env node
/**
 * stockfish-pool.mjs — N-process Stockfish pool (Phase 168, Plan 03, Task 1),
 * mirroring `frontend/src/lib/engine/workerPool.ts`'s free-slot queue over
 * `node:child_process` instances instead of Web Workers.
 *
 * The CAL-03 spike (168-02-SUMMARY.md) found the bottleneck is `grade()`
 * serialization inside `mctsSearch` under a SINGLE shared Stockfish process
 * (`SEARCH_CONCURRENCY=1`), NOT Maia/ONNX inference (168-RESEARCH.md
 * Pitfall 3). The fix is N independently-spawned Stockfish processes so
 * `mctsSearch` can dispatch up to `size` concurrent `grade()` calls — each
 * individual process STILL serves only one `go` at a time (never overlapping
 * `go`s on the SAME process); throughput comes from parallelizing ACROSS
 * processes, not from multiplexing one.
 *
 * Every request (bot grading, Stockfish-skill anchor moves, adjudication
 * evals) reuses the existing per-engine UCI logic
 * (`calibration-providers.mjs`'s `nodeGrade`/`evalPositionCp`,
 * `calibration-anchors.mjs`'s `stockfishSkillMove`) — each of which already
 * resets every option it depends on (Skill Level/UCI_LimitStrength/MultiPV)
 * immediately before its own `go` (Pitfall 2). Routing those same functions
 * through this pool's acquire/release preserves that per-call reset
 * discipline PER PROCESS: a weakened Skill Level set on one engine for an
 * anchor move can never leak into a different engine's bot-grading `go`.
 *
 * D-11 (168.5-02, Task 2): `withEngine` also retries a timed-out `go` in
 * place up to `ENGINE_RETRY_ATTEMPTS` times via `runWithRetry`, reusing
 * `stopAndSync()` between attempts, so a single slow reply degrades to a
 * retry rather than aborting the whole multi-hour sweep.
 *
 * BUG FIX (SEED-145 Stage B, 2026-08-23): D-11's retry-in-place assumed the
 * engine was slow, never gone. When a child process actually EXITS, retrying
 * on it is hopeless and the pool used to keep it forever — one crashed child
 * poisoned the pool for the rest of the run, costing every request routed to
 * it `ENGINE_RETRY_ATTEMPTS` x the 30 s watchdog before failing. Sweep workers
 * 4 and 10 ledgered 1,098 positions as bogus `Stockfish response timeout`
 * errors that way. The pool now EVICTS a dead engine on release and respawns a
 * replacement into its place (`replaceDeadEngine`), so a lost child costs one
 * position instead of a partition.
 */
import { spawnStockfish, STOCKFISH_INIT_TIMEOUT_MS } from './node-engine-providers.mjs';
import { nodeGrade, evalPositionCp, evalPositionCpWithBest } from './calibration-providers.mjs';
import { stockfishSkillMove } from './calibration-anchors.mjs';

/** Default pool size — mirrors `workerPool.ts`'s `DESKTOP_POOL_MAX` order of magnitude. */
export const STOCKFISH_POOL_DEFAULT_SIZE = 4;

/**
 * Retry attempts (D-11) after a `waitFor` watchdog timeout on a grading or
 * adjudication `go` — a single late reply must not abort a multi-hour sweep.
 * 2 retries = 3 total attempts (initial + 2). Engine restart is NOT
 * attempted here as a further fallback — the harness's existing per-cell
 * failure path is the last resort once retries are exhausted.
 */
export const ENGINE_RETRY_ATTEMPTS = 2;

/** Matches `StockfishUciEngine.waitFor`'s rejection message — the only error class D-11 retries. */
const TIMEOUT_ERROR_PATTERN = /Stockfish response timeout after/;

/** Respawn attempts for a replacement engine before the slot is written off. */
const ENGINE_RESPAWN_ATTEMPTS = 3;
/** Backoff between respawn attempts — a box that just OOM-killed a child needs a moment. */
const ENGINE_RESPAWN_BACKOFF_MS = 2_000;

/**
 * Acquires the next free engine, or queues the caller until one is released
 * (mirrors `workerPool.ts`'s pending-array + `dispatchNext` free-slot scan,
 * generalized to one FIFO waiter list since every request here is a single
 * atomic `go` round-trip, not a priority-ordered MCTS grade queue).
 */
function acquireEngine(pool, onQueued) {
  if (pool.fatal) return Promise.reject(pool.fatal);
  const free = pool.engines.find((engine) => !engine.dead && !pool.busy.get(engine));
  if (free !== undefined) {
    pool.busy.set(free, true);
    return Promise.resolve(free);
  }
  // No free engine right now. This also covers the transient window where every
  // engine died and its replacement is still spawning — the waiter is served by
  // `replaceDeadEngine`'s release, or rejected if the pool can't be rebuilt.
  return new Promise((resolve, reject) => {
    const waiter = { resolve, reject };
    pool.waiters.push(waiter);
    onQueued?.(waiter); // lets `withEngine` pull this entry back out if its caller aborts while queued
  });
}

/**
 * Counts engines that are neither dead nor currently busy (Phase 226 D-08).
 * This is the pool's own definition of "free" for both the public
 * `freeCount()` surface and `splitAcrossFreeEngines`'s internal premise check
 * — a single definition so the two can never silently disagree.
 */
function countFreeEngines(pool) {
  return pool.engines.filter((engine) => !engine.dead && !pool.busy.get(engine)).length;
}

/**
 * True when no request can still be running or waiting: every live engine is free, nobody is
 * queued, and no dead-engine replacement is mid-respawn (Phase 227 D-09 `whenIdle`).
 */
function isPoolIdle(pool) {
  const live = pool.engines.filter((engine) => !engine.dead).length;
  return countFreeEngines(pool) === live && pool.waiters.length === 0 && pool.respawning === 0;
}

/** Resolves every `whenIdle()` caller once the pool is idle. Called wherever an engine frees up or a respawn settles. */
function notifyIdle(pool) {
  if (pool.idleResolvers.length === 0 || !isPoolIdle(pool)) return;
  for (const resolve of pool.idleResolvers.splice(0)) resolve();
}

/**
 * Releases an engine back to the pool — hands it directly to the next FIFO
 * waiter if one is queued. A DEAD engine is never handed on: it is evicted and
 * asynchronously replaced (see the bug-fix note in this file's header).
 */
function releaseEngine(pool, engine) {
  if (engine.dead) {
    void replaceDeadEngine(pool, engine);
    return;
  }
  const nextWaiter = pool.waiters.shift();
  if (nextWaiter !== undefined) {
    nextWaiter.resolve(engine); // stays "busy": handed straight to the waiting request.
    return;
  }
  pool.busy.set(engine, false);
  notifyIdle(pool);
}

/**
 * Spawn one engine and apply the pool's per-engine UCI configuration.
 *
 * `hashMb` exists because the measurement harnesses that mirror
 * `workerPool.ts` must pin Hash to the browser worker's `WORKER_HASH_MB`;
 * Stockfish's own default would silently change the transposition-table size
 * out from under a harness whose whole point is to reproduce shipped behavior.
 * It is applied HERE rather than at the call site so a respawned replacement is
 * configured identically — a pool that heals into a differently-configured
 * engine mid-run is worse than one that never heals, because the divergence is
 * invisible in the output.
 *
 * `sendObserver` (Phase 226 D-03/D-08, optional), when provided, is wrapped
 * around the engine's `send` HERE — at spawn AND at every respawn inside
 * `replaceDeadEngine` — for the same "configured identically after a respawn"
 * reason `hashMb` is. Every line this engine ever sends (including the
 * `Hash`/`isready` bring-up lines below) passes through the observer BEFORE
 * `child.stdin.write` actually fires, so a caller building a Clear-Hash send
 * spy (`stockfish-pool.check.mjs`) sees the true wire order.
 */
async function spawnConfigured(hashMb, sendObserver = null) {
  const engine = await spawnStockfish();
  if (sendObserver) {
    const rawSend = engine.send.bind(engine);
    engine.send = (command) => {
      sendObserver(command);
      rawSend(command);
    };
  }
  if (hashMb === null) return engine;
  try {
    engine.send(`setoption name Hash value ${hashMb}`);
    engine.send('isready');
    await engine.waitFor((line) => line === 'readyok', STOCKFISH_INIT_TIMEOUT_MS);
  } catch (err) {
    engine.terminate(); // never leak a live child whose configuration failed
    throw err;
  }
  return engine;
}

/**
 * Replaces an engine the moment it dies, rather than waiting for a release.
 *
 * An engine that dies while BUSY is caught by the release path anyway (its
 * in-flight caller is rejected, then releases it). An engine that dies while
 * IDLE is not: `acquireEngine` skips dead engines, so it would never be
 * acquired, never released, and never replaced — the pool would quietly run at
 * reduced size for the rest of a multi-day sweep with nothing in the output
 * saying so. `replaceDeadEngine` is idempotent (it no-ops once the engine is out
 * of `pool.engines`), so a death that fires both paths still replaces once.
 */
function watchForDeath(pool, engine) {
  engine.onDeath(() => void replaceDeadEngine(pool, engine));
}

/**
 * Drops `dead` out of the pool and spawns a replacement into it, retrying a few
 * times with backoff. Slot ORDER is irrelevant (acquire does a free-scan, not an
 * index lookup), so this removes and re-pushes rather than juggling indices.
 *
 * If every respawn attempt fails and no engine is left, the pool is marked fatal
 * and every queued waiter is rejected — a caller blocking forever on a pool that
 * can never serve it again is strictly worse than a loud failure, and for the
 * sweep it means the worker exits and the supervisor respawns it fresh.
 */
async function replaceDeadEngine(pool, dead) {
  if (pool.shuttingDown) return;
  const slot = pool.engines.indexOf(dead);
  if (slot === -1) return; // already evicted by a concurrent release or its death hook
  pool.engines.splice(slot, 1);
  pool.busy.delete(dead);
  dead.terminate(); // idempotent: reaps the child (if any) and unlinks its temp .cjs/.wasm

  // `whenIdle` must not report idle while a replacement is still being spawned.
  pool.respawning++;
  try {
    await respawnInto(pool, dead);
  } finally {
    pool.respawning--;
    notifyIdle(pool);
  }
}

/** The respawn-with-backoff loop of `replaceDeadEngine` (kept separate so its `respawning` accounting has one exit). */
async function respawnInto(pool, dead) {
  for (let attempt = 1; attempt <= ENGINE_RESPAWN_ATTEMPTS; attempt++) {
    try {
      const fresh = await spawnConfigured(pool.hashMb, pool.sendObserver);
      if (pool.shuttingDown) {
        // quitAll() ran while this spawn was in flight. Pushing now would leak a
        // live child (spawn is not detached, but the parent exits right after
        // quitAll, so the child is merely reparented, not reaped) plus its temp
        // .cjs/.wasm copies.
        fresh.terminate();
        return;
      }
      pool.engines.push(fresh);
      watchForDeath(pool, fresh);
      pool.busy.set(fresh, true); // released immediately below, straight to a waiter if one is queued
      console.warn(
        `[stockfish-pool] replaced dead engine (${dead.deadReason ?? 'unknown cause'}) — ` +
          `${pool.engines.length} engine(s) in pool`,
      );
      releaseEngine(pool, fresh);
      return;
    } catch (err) {
      if (attempt < ENGINE_RESPAWN_ATTEMPTS) {
        await new Promise((resolve) => setTimeout(resolve, ENGINE_RESPAWN_BACKOFF_MS));
        continue;
      }
      console.warn(`[stockfish-pool] respawn failed ${ENGINE_RESPAWN_ATTEMPTS}x: ${err.message}`);
      if (pool.engines.length === 0) {
        pool.fatal = new Error(`Stockfish pool is empty — every engine died and respawn failed: ${err.message}`);
        for (const waiter of pool.waiters.splice(0)) waiter.reject(pool.fatal);
      }
      return;
    }
  }
}

/**
 * D-11: runs `fn(engine)`, retrying the SAME operation in place up to
 * `ENGINE_RETRY_ATTEMPTS` times when it rejects with a `waitFor` watchdog
 * timeout — a single late reply must not fail the whole cell. Between
 * attempts, `stopAndSync()` resyncs the engine to quiescent (reused verbatim
 * from `node-engine-providers.mjs`, not reimplemented). Only the timeout
 * error class is retried: illegal-move/parse errors are deterministic and
 * would loop forever without ever succeeding.
 */
async function runWithRetry(engine, fn) {
  let lastErr;
  for (let attempt = 0; attempt <= ENGINE_RETRY_ATTEMPTS; attempt++) {
    try {
      return await fn(engine);
    } catch (err) {
      lastErr = err;
      const isTimeout = err instanceof Error && TIMEOUT_ERROR_PATTERN.test(err.message);
      // A dead engine can't answer a retry — `stopAndSync` below would throw and
      // every attempt would just burn another watchdog. Surface it now so
      // `withEngine`'s release path evicts and replaces the engine.
      if (!isTimeout || engine.dead || attempt === ENGINE_RETRY_ATTEMPTS) throw err;
      await engine.stopAndSync();
    }
  }
  throw lastErr; // unreachable — the loop above always returns or throws
}

/**
 * Runs `fn` against a free engine, always releasing it back to the pool afterward (success or throw).
 *
 * Phase 227 D-09 / N-2: with a `signal`, mirrors `workerPoolDispatch.ts`'s `submitGradeRequest`
 * abort handling. A request aborted before it starts never reaches an engine; one aborted while
 * queued leaves `pool.waiters`; one aborted in flight sends `stop` to its engine. In every case the
 * caller settles with `abortValue` at once, and an in-flight engine is released only after `fn`
 * settles on the engine's own `bestmove`, so a still-searching engine is never handed on. The abort
 * listener is `{ once: true }` AND removed on every settle path (the browser pool's 400-listener
 * accumulation lesson: mctsSearch threads ONE signal through every grade of a search).
 */
function withEngine(pool, fn, signal, abortValue) {
  if (signal === undefined || signal === null) return runOnEngine(pool, fn); // no signal: exactly the pre-227 path
  if (signal.aborted) return Promise.resolve(abortValue);

  return new Promise((resolve, reject) => {
    let settled = false;
    let queuedWaiter = null;
    let runningEngine = null;
    const settle = (finish, value) => {
      if (settled) return;
      settled = true;
      signal.removeEventListener('abort', onAbort);
      finish(value);
    };
    const onAbort = () => {
      if (queuedWaiter !== null) {
        const idx = pool.waiters.indexOf(queuedWaiter);
        if (idx >= 0) pool.waiters.splice(idx, 1);
      }
      if (runningEngine !== null && !runningEngine.dead) {
        try {
          runningEngine.send('stop'); // `fn` finishes on the resulting bestmove; its result is discarded
        } catch {
          // the engine died between the check and the write: its own death path replaces it
        }
      }
      settle(resolve, abortValue);
    };
    signal.addEventListener('abort', onAbort, { once: true });

    acquireEngine(pool, (waiter) => {
      queuedWaiter = waiter;
    }).then(
      async (engine) => {
        queuedWaiter = null;
        if (settled) {
          // Aborted in the gap between the engine being handed over and this continuation running.
          releaseEngine(pool, engine);
          return;
        }
        runningEngine = engine;
        try {
          settle(resolve, await runWithRetry(engine, fn));
        } catch (err) {
          // WR-01: see `runOnEngine`: resync the engine quiescent before releasing it.
          if (!engine.dead) await engine.stopAndSync().catch(() => {});
          settle(reject, err); // a no-op when the caller already settled via abort
        } finally {
          releaseEngine(pool, engine);
        }
      },
      (err) => settle(reject, err),
    );
  });
}

/** Signal-free `withEngine` body: acquire, run with retry, release. */
async function runOnEngine(pool, fn) {
  const engine = await acquireEngine(pool);
  try {
    return await runWithRetry(engine, fn);
  } catch (err) {
    // WR-01: `fn` (nodeGrade/evalPositionCp/stockfishSkillMove) rejecting most
    // often means its `waitFor` timed out while the engine was still mid-search
    // — releasing it as-is would hand a still-searching engine straight to the
    // next waiter/free-scan. Resync it quiescent first (mirrors
    // gem-elo-calibration.mjs's per-position catch block); swallow a failed
    // resync here since the engine's own error/exit handlers already surface
    // an unrecoverable process death, and this path must not mask `err`.
    if (!engine.dead) await engine.stopAndSync().catch(() => {});
    throw err;
  } finally {
    releaseEngine(pool, engine);
  }
}

/**
 * Module specifier for the (currently unbuilt, Plan 226-10) pure root-split
 * helpers — `partitionCandidates`, `mergeShardGrades`, `ROOT_SPLIT_MAX_SHARDS`.
 * Named as a constant so `splitAcrossFreeEngines` below and
 * `stockfish-pool.check.mjs`'s `--root-split` section reference the exact
 * same string, never two hand-typed copies that could drift.
 */
export const ROOT_SPLIT_MODULE_SPECIFIER = '@/lib/engine/rootSplit';

/**
 * Thrown by `splitAcrossFreeEngines` when `ROOT_SPLIT_MODULE_SPECIFIER`
 * cannot be resolved — the expected outcome at every arm before A21S
 * (Plan 226-10 has not landed `frontend/src/lib/engine/rootSplit.ts` yet).
 * `stockfish-pool.check.mjs --root-split` matches this string verbatim and
 * exits 3, rather than treating it as a genuine check failure.
 */
export const ROOT_SPLIT_ABSENT_MESSAGE = 'rootSplit module absent (pre-A21S arm)';

/**
 * Fans a root grade request out across the free engines a caller can see
 * RIGHT NOW (Phase 226 D-18 harness side; D-08 tripwire). Dormant until
 * A21S's engine actually calls `mctsSearch`'s `gradeRoot` provider — every
 * arm before that never reaches the `k > 1` branch below, so the (currently
 * absent) `rootSplit.ts` module is never imported by any arm A0..A21.
 *
 * `freeCount`/`size` are passed in (not read off a closed-over `pool`) so
 * this function stays usable by every harness pool shape RESEARCH Pattern 1
 * lists (`stockfish-pool.mjs`, `createGradePool`, the depth-ab closures),
 * not just this file's own pool.
 *
 * D-08 tripwire: in the harness, round 1 of every search sees the WHOLE pool
 * idle (every caller awaits `Promise.all` before its next round — F-4). A
 * `freeCount() !== size` at a `gradeRoot` call therefore means some OTHER
 * consumer holds a slot — the premise this file's harness bit-identity
 * argument depends on — so it is counted, never silently ignored.
 *
 * `k <= 1` (only one or zero free engines) or a single candidate takes the
 * plain, undivided `runShard(candidateUcis)` path WITHOUT importing
 * `rootSplit.ts` at all — this is what keeps every arm before A21S from ever
 * touching the absent module. A shard that fails propagates as a throw
 * (never a partial merged Map — `mctsSearch.ts`'s harness-mirrored L-2
 * semantics: an incomplete root grade must resolve empty or throw, never
 * silently drop candidates).
 */
export async function splitAcrossFreeEngines({ freeCount, size, stats, candidateUcis, runShard }) {
  stats.calls++;
  const k = freeCount();
  if (k !== size) stats.premiseViolations++;
  if (k <= 1 || candidateUcis.length <= 1) {
    return runShard(candidateUcis);
  }

  let rootSplitModule;
  try {
    rootSplitModule = await import(ROOT_SPLIT_MODULE_SPECIFIER);
  } catch (err) {
    // `frontend-alias-hook.mjs`'s `@/` resolve branch always returns a URL
    // regardless of whether the target file exists (it has no `fs.existsSync`
    // guard, unlike its extensionless-relative branch), so an absent
    // `rootSplit.ts` fails at the LOAD stage as a raw `ENOENT`, never at
    // resolve as `ERR_MODULE_NOT_FOUND`/`MODULE_NOT_FOUND` — those two codes
    // are kept for portability (a caller running this without the alias hook,
    // or a future hook fix, would surface the standard Node code instead).
    if (err instanceof Error && (err.code === 'ERR_MODULE_NOT_FOUND' || err.code === 'MODULE_NOT_FOUND' || err.code === 'ENOENT')) {
      throw new Error(ROOT_SPLIT_ABSENT_MESSAGE);
    }
    throw err; // an unrelated import-time failure (e.g. a syntax error in a landed module) must not be masked as "absent"
  }
  const { partitionCandidates, mergeShardGrades, ROOT_SPLIT_MAX_SHARDS } = rootSplitModule;
  const shards = partitionCandidates(candidateUcis, Math.min(k, ROOT_SPLIT_MAX_SHARDS));
  const parts = await Promise.all(shards.map((shard) => runShard(shard)));
  stats.splits++;
  return mergeShardGrades(candidateUcis, parts);
}

/**
 * Spawns `size` independent Stockfish processes and returns the pool's public
 * surface: `grade`/`evalPosition`/`skillMove` (each acquire-run-release over
 * a free engine; `grade`/`gradeRoot`/`run` honor an AbortSignal, Phase 227 D-09),
 * `whenIdle`, `newGameAll` (D-09 determinism: clears every engine's
 * transposition table at a game boundary), and `quitAll`.
 */
export async function createStockfishPool({
  size = STOCKFISH_POOL_DEFAULT_SIZE,
  hashMb = null,
  clearHash = true,
  sendObserver = null,
} = {}) {
  if (!Number.isInteger(size) || size < 1) {
    throw new Error(`createStockfishPool: size must be a positive integer, got ${JSON.stringify(size)}`);
  }
  if (hashMb !== null && (!Number.isInteger(hashMb) || hashMb < 1)) {
    throw new Error(`createStockfishPool: hashMb must be a positive integer or null, got ${JSON.stringify(hashMb)}`);
  }
  if (sendObserver !== null && typeof sendObserver !== 'function') {
    throw new Error(`createStockfishPool: sendObserver must be a function or null, got ${JSON.stringify(sendObserver)}`);
  }
  // CR-02: Promise.all rejects on the FIRST failing spawnStockfish(), which
  // would silently discard every OTHER already-spawned sibling engine (live
  // child process, UCI handshake done) with no reference left to terminate
  // it. Promise.allSettled lets us inspect every outcome and terminate every
  // fulfilled engine before rethrowing the first rejection.
  const results = await Promise.allSettled(
    Array.from({ length: size }, () => spawnConfigured(hashMb, sendObserver)),
  );
  const failed = results.find((r) => r.status === 'rejected');
  if (failed) {
    for (const r of results) {
      if (r.status === 'fulfilled') r.value.terminate();
    }
    throw failed.reason;
  }
  const engines = results.map((r) => r.value);
  // `fatal` latches once the pool can no longer be rebuilt (see `replaceDeadEngine`);
  // `shuttingDown` stops an in-flight respawn from leaking a child past quitAll().
  // `clearHash`/`sendObserver` are pinned here next to `hashMb` for the exact
  // same reason: a respawned replacement engine (`replaceDeadEngine`) must be
  // configured identically, never silently drop the pool's Clear-Hash policy
  // or its send observer mid-run. `splitStats` is this pool's D-08 tripwire
  // accumulator for `gradeRoot`/`rootSplitStats()` below.
  const pool = {
    engines,
    busy: new Map(engines.map((engine) => [engine, false])),
    waiters: [],
    idleResolvers: [],
    respawning: 0,
    fatal: null,
    shuttingDown: false,
    hashMb,
    clearHash,
    sendObserver,
    splitStats: { calls: 0, splits: 0, premiseViolations: 0 },
  };
  for (const engine of engines) watchForDeath(pool, engine);

  return {
    size,

    /**
     * `EngineProviders.grade` shape (UCI-keyed, searchmoves-restricted,
     * depth-carrying — D-08). Declares all four parameters `mctsSearch`'s
     * `dispatchExpansion` now passes (`fen, candidateUcis, signal,
     * gradingDepth`) and forwards `gradingDepth` into `nodeGrade`.
     *
     * BUG FIX (Phase 195, T-195-09): this closure previously declared only
     * `(fen, candidateUcis)` — two parameters. JavaScript silently discards
     * extra arguments passed to a function with fewer declared parameters, so
     * once Plan 01's `dispatchExpansion` started passing a 4th depth
     * argument, this pool (the one Phase 199's recalibration sweep actually
     * runs against) would have graded every node at one flat depth while the
     * shipped browser ran the real ladder — with nothing in the sweep's own
     * output showing it. Widening the closure and forwarding the depth closes
     * that gap.
     *
     * Phase 227 N-2 (fix site): the Node pools used to IGNORE `signal`, so continuous
     * dispatch's D-09 cancellation never happened in Node: stale grades kept engines busy into
     * the next position's timing window, and the root-split premise counter fired. `signal` is
     * now honored exactly like the browser WorkerPool: an unstarted request is dropped, an
     * in-flight one gets `stop` and settles an empty Map at once, and its engine is freed only
     * after `bestmove` (see `withEngine`).
     *
     * Phase 226 D-03: forwards `{ clearHash: pool.clearHash }` into `nodeGrade`
     * so a grading-only pool built with `createStockfishPool({ clearHash: false })`
     * (the D-03 warm arm) actually skips the per-grade `Clear Hash` send — the
     * pool's configured policy, not a per-call override.
     */
    grade: (fen, candidateUcis, signal, gradingDepth) =>
      withEngine(
        pool,
        (engine) => nodeGrade(engine, fen, candidateUcis, gradingDepth, { clearHash: pool.clearHash }),
        signal,
        new Map(),
      ),

    /**
     * `clearHash` (Phase 226 D-03): exposes this pool's configured Clear-Hash
     * policy so a caller building a grading-only pool can confirm which mode
     * it got, without reaching into internal pool state.
     */
    clearHash: pool.clearHash,

    /**
     * Count of engines that are neither dead nor currently busy (Phase 226
     * D-08 premise instrument) — `splitAcrossFreeEngines`'s own tripwire uses
     * this same definition internally (`countFreeEngines`); exposed here so a
     * caller (a check script, or a future harness tool) can read it directly.
     */
    freeCount: () => countFreeEngines(pool),

    /**
     * Root grade fan-out (Phase 226 D-18/D-08), dormant until arm A21S's
     * `mctsSearch.ts` actually routes a root's grade call here — see
     * `splitAcrossFreeEngines`'s own doc comment above for the full contract.
     * `runShard` reuses this pool's own `clearHash` policy per shard, exactly
     * like `grade` above, so a warm-hash gradeRoot never silently reverts to
     * Clear-Hash grading.
     */
    gradeRoot: async (fen, candidateUcis, signal, gradingDepth) => {
      if (signal?.aborted) return new Map();
      let merged;
      try {
        merged = await splitAcrossFreeEngines({
          freeCount: () => countFreeEngines(pool),
          size,
          stats: pool.splitStats,
          candidateUcis,
          runShard: (shard) =>
            withEngine(
              pool,
              (engine) => nodeGrade(engine, fen, shard, gradingDepth, { clearHash: pool.clearHash }),
              signal,
              new Map(),
            ),
        });
      } catch (err) {
        // L-2: a root grade aborted mid-fan-out leaves some shards empty, which the shard merge may
        // reject as incomplete. An abort is not a failure: resolve empty, never throw or merge partially.
        if (signal?.aborted) return new Map();
        throw err;
      }
      // L-2: shards that settled empty because of the abort must never be merged into a partial result.
      return signal?.aborted ? new Map() : merged;
    },

    /**
     * Resolves once every live engine is free, no request is queued, and no dead-engine
     * replacement is mid-respawn (Phase 227 D-09). Gate scripts await it after cancelling grades so
     * the previous position's stopped searches have quiesced before the next position's timer starts.
     * Stockfish only: it says nothing about Maia, so gate scripts also await `whenMaiaIdle()`
     * (`scripts/lib/calibration-providers.mjs`) before it.
     */
    whenIdle: () =>
      isPoolIdle(pool)
        ? Promise.resolve()
        : new Promise((resolve) => {
            pool.idleResolvers.push(resolve);
          }),

    /** Requests currently waiting for an engine (read-only instrument, like `freeCount`; used by the abort check). */
    queuedCount: () => pool.waiters.length,

    /** Copy of this pool's `gradeRoot` tripwire accumulator — never the live mutable object. */
    rootSplitStats: () => ({ ...pool.splitStats }),

    /** Single-line white-POV cp eval for D-10 cutoff 2 (adjudication). */
    evalPosition: (fen) => withEngine(pool, (engine) => evalPositionCp(engine, fen)),

    /**
     * White-POV cp eval + the engine's own `bestmove` byproduct (Phase 180
     * near-free SF-agreement). Same single `go` as `evalPosition` — the
     * `bestmove` line is already awaited, so this adds ZERO extra engine work.
     */
    evalPositionWithBest: (fen) => withEngine(pool, (engine) => evalPositionCpWithBest(engine, fen)),

    /**
     * Escape hatch: run arbitrary UCI work against a pooled engine, with the
     * pool's acquire/release, timeout retry, and dead-engine eviction applied.
     *
     * The named wrappers above cover the shipped call shapes. Harnesses that
     * measure something else — an UNRESTRICTED `go`, a same-engine hash probe
     * that issues two searches, a bespoke depth-15 scan — used to hand-roll a
     * private acquire/release pool over `spawnStockfish` instead, which is what
     * left five scripts without any dead-engine recovery. Reach for this rather
     * than building a sixth.
     *
     * `fn` receives a `StockfishUciEngine` and must leave it quiescent (its own
     * `go` awaited to `bestmove`); `withEngine` resyncs on the throw path, but
     * a resolved `fn` that left a search running would corrupt the next caller.
     * `fn` may be re-invoked from the start on a `waitFor` timeout (D-11), so
     * keep any accumulator it owns inside the function body.
     *
     * Phase 227 D-09: optional `signal` + `abortValue` give `run` the same abort semantics as
     * `grade` (see `withEngine`); on abort the caller settles with `abortValue` while `fn` is left
     * to finish on its engine's own `bestmove`, so `fn` must not start a further search by itself
     * after its first one returns early.
     */
    run: (fn, signal, abortValue) => withEngine(pool, fn, signal, abortValue),

    /** Stockfish-skill anchor move at `skillLevel` (D-07 anchor). */
    skillMove: (fen, skillLevel) => withEngine(pool, (engine) => stockfishSkillMove(engine, fen, skillLevel)),

    /** Clears every engine's transposition table at a game boundary (D-09 determinism — Plan 02's fix, pool-wide). */
    async newGameAll() {
      // Snapshot: `pool.engines` is mutated live by `replaceDeadEngine`. A
      // replacement engine is born with an empty transposition table anyway, so
      // missing one mid-respawn cannot break D-09 determinism.
      await Promise.all(
        [...pool.engines].map(async (engine) => {
          if (engine.dead) return;
          engine.send('ucinewgame');
          engine.send('isready');
          await engine.waitFor((line) => line === 'readyok', STOCKFISH_INIT_TIMEOUT_MS);
        }),
      );
    },

    /** Terminates every process in the pool and stops any in-flight respawn. */
    quitAll() {
      pool.shuttingDown = true;
      for (const engine of [...pool.engines]) engine.terminate();
    },
  };
}

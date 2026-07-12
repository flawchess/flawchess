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
 */
import { spawnStockfish, STOCKFISH_INIT_TIMEOUT_MS } from './node-engine-providers.mjs';
import { nodeGrade, evalPositionCp } from './calibration-providers.mjs';
import { stockfishSkillMove } from './calibration-anchors.mjs';

/** Default pool size — mirrors `workerPool.ts`'s `DESKTOP_POOL_MAX` order of magnitude. */
export const STOCKFISH_POOL_DEFAULT_SIZE = 4;

/**
 * Acquires the next free engine, or queues the caller until one is released
 * (mirrors `workerPool.ts`'s pending-array + `dispatchNext` free-slot scan,
 * generalized to one FIFO waiter list since every request here is a single
 * atomic `go` round-trip, not a priority-ordered MCTS grade queue).
 */
function acquireEngine(pool) {
  const free = pool.engines.find((engine) => !pool.busy.get(engine));
  if (free !== undefined) {
    pool.busy.set(free, true);
    return Promise.resolve(free);
  }
  return new Promise((resolve) => pool.waiters.push(resolve));
}

/** Releases an engine back to the pool — hands it directly to the next FIFO waiter if one is queued. */
function releaseEngine(pool, engine) {
  const nextWaiter = pool.waiters.shift();
  if (nextWaiter !== undefined) {
    nextWaiter(engine); // stays "busy": handed straight to the waiting request.
    return;
  }
  pool.busy.set(engine, false);
}

/** Runs `fn` against a free engine, always releasing it back to the pool afterward (success or throw). */
async function withEngine(pool, fn) {
  const engine = await acquireEngine(pool);
  try {
    return await fn(engine);
  } catch (err) {
    // WR-01: `fn` (nodeGrade/evalPositionCp/stockfishSkillMove) rejecting most
    // often means its `waitFor` timed out while the engine was still mid-search
    // — releasing it as-is would hand a still-searching engine straight to the
    // next waiter/free-scan. Resync it quiescent first (mirrors
    // gem-elo-calibration.mjs's per-position catch block); swallow a failed
    // resync here since the engine's own error/exit handlers already surface
    // an unrecoverable process death, and this path must not mask `err`.
    await engine.stopAndSync().catch(() => {});
    throw err;
  } finally {
    releaseEngine(pool, engine);
  }
}

/**
 * Spawns `size` independent Stockfish processes and returns the pool's public
 * surface: `grade`/`evalPosition`/`skillMove` (each acquire-run-release over
 * a free engine), `newGameAll` (D-09 determinism: clears every engine's
 * transposition table at a game boundary), and `quitAll`.
 */
export async function createStockfishPool({ size = STOCKFISH_POOL_DEFAULT_SIZE } = {}) {
  if (!Number.isInteger(size) || size < 1) {
    throw new Error(`createStockfishPool: size must be a positive integer, got ${JSON.stringify(size)}`);
  }
  // CR-02: Promise.all rejects on the FIRST failing spawnStockfish(), which
  // would silently discard every OTHER already-spawned sibling engine (live
  // child process, UCI handshake done) with no reference left to terminate
  // it. Promise.allSettled lets us inspect every outcome and terminate every
  // fulfilled engine before rethrowing the first rejection.
  const results = await Promise.allSettled(Array.from({ length: size }, () => spawnStockfish()));
  const failed = results.find((r) => r.status === 'rejected');
  if (failed) {
    for (const r of results) {
      if (r.status === 'fulfilled') r.value.terminate();
    }
    throw failed.reason;
  }
  const engines = results.map((r) => r.value);
  const pool = { engines, busy: new Map(engines.map((engine) => [engine, false])), waiters: [] };

  return {
    size,

    /** `EngineProviders.grade` shape (UCI-keyed, searchmoves-restricted, depth-carrying — D-08). */
    grade: (fen, candidateUcis) => withEngine(pool, (engine) => nodeGrade(engine, fen, candidateUcis)),

    /** Single-line white-POV cp eval for D-10 cutoff 2 (adjudication). */
    evalPosition: (fen) => withEngine(pool, (engine) => evalPositionCp(engine, fen)),

    /** Stockfish-skill anchor move at `skillLevel` (D-07 anchor). */
    skillMove: (fen, skillLevel) => withEngine(pool, (engine) => stockfishSkillMove(engine, fen, skillLevel)),

    /** Clears every engine's transposition table at a game boundary (D-09 determinism — Plan 02's fix, pool-wide). */
    async newGameAll() {
      await Promise.all(
        engines.map(async (engine) => {
          engine.send('ucinewgame');
          engine.send('isready');
          await engine.waitFor((line) => line === 'readyok', STOCKFISH_INIT_TIMEOUT_MS);
        }),
      );
    },

    /** Terminates every process in the pool. */
    quitAll() {
      for (const engine of engines) engine.terminate();
    },
  };
}

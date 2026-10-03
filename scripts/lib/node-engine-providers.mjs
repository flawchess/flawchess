#!/usr/bin/env node
/**
 * node-engine-providers.mjs — shared Maia ONNX session + Stockfish UCI process
 * bring-up (Phase 168, CAL-02 no-duplication discipline).
 *
 * Extracted VERBATIM out of `scripts/gem-elo-calibration.mjs` (Phase 165) so
 * BOTH that harness and the new calibration harness (Phase 168) import the
 * exact same bring-up code — never a second hand-rolled copy of the Maia
 * session loader or the Stockfish WASM-over-UCI spawn trick. This is a
 * behavior-preserving mechanical refactor: gem-elo-calibration.mjs re-imports
 * these symbols and runs unchanged.
 *
 * Pitfall 5 (168-RESEARCH.md): the vendored Stockfish's Emscripten glue
 * locates its `.wasm` binary at `path.join(__dirname, basename(__filename,
 * ext) + '.wasm')` — i.e. same directory, SAME basename minus extension. The
 * `.cjs`/`.wasm` temp-file copy-then-rename logic below MUST stay byte-for-
 * byte identical to the original, or the spawned process silently hangs
 * waiting for `uciok`.
 *
 * Usage: node --import ./scripts/lib/frontend-alias-hook.mjs <script.mjs>
 * (resolveFrontendModule needs no `@/` alias itself — it resolves bare
 * package specifiers straight out of frontend/node_modules via createRequire.)
 */
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';
import { Worker } from 'node:worker_threads';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';

// ─── Path resolution (this file lives in scripts/lib/, one level deeper than
// scripts/gem-elo-calibration.mjs — REPO_ROOT/FRONTEND_DIR are re-derived
// relative to THIS file's own location, not inherited from the caller) ────────

// fileURLToPath (not URL.pathname): URL.pathname yields '/C:/...' on Windows,
// which path.resolve then mangles — the Stage B sweep runs on a Windows laptop.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');
export const FRONTEND_DIR = path.resolve(REPO_ROOT, 'frontend');

/** Wall-clock timeout (ms) for the Stockfish `uci`/`isready` init handshake. */
export const STOCKFISH_INIT_TIMEOUT_MS = 30_000;

/** Wall-clock ceiling (ms) for the Maia worker thread to load the model and report `ready`. */
export const MAIA_WORKER_READY_TIMEOUT_MS = 60_000;

/**
 * Process exit code used when the Maia worker thread dies unexpectedly (Phase 227 D-18). Distinct
 * from 0 (success), 1 (generic failure), 3 (stockfish-pool.check --root-split "module absent") and
 * 42 (worktree base mismatch), so a supervisor log line can tell a worker death from a script bug.
 */
export const MAIA_WORKER_DIED_EXIT_CODE = 70;

/**
 * Fixed message for every request rejected by a dead Maia worker. No interpolated variables (CLAUDE.md
 * error-message rule): the underlying cause rides on the Error's `cause` property.
 */
export const MAIA_WORKER_FAILED_MESSAGE = 'Maia worker thread failed';

/** Characters of child stderr kept for the death reason (enough for a wasm stack trace). */
const STDERR_TAIL_CHARS = 4_000;

// ─── Resolve frontend-vendored runtime deps (onnxruntime-web, chess.js) ────────
// scripts/*.mjs is NOT under frontend/src, so bare package specifiers don't
// resolve from the repo root (no root node_modules). Mirror
// scripts/inspect_maia_onnx.mjs's createRequire-from-frontend recipe.

export async function resolveFrontendModule(packageName) {
  const requireFromFrontend = createRequire(path.join(FRONTEND_DIR, 'package.json'));
  const resolved = requireFromFrontend.resolve(packageName);
  return import(pathToFileURL(resolved).href);
}

// ─── Maia (onnxruntime) — loaded ONCE, reused across all positions ────────────

/**
 * `backend: 'wasm'` (default) is onnxruntime-web, app-faithful but leaks the
 * wasm arena (~"memory access out of bounds" after ~1,250 sweep positions —
 * ort-web internal, SEED-113 already disposes everything we own; both the
 * frontend maiaWorkerHost and the sweep supervisor mitigate by respawn).
 *
 * `offThread` (default true, wasm backend only; Phase 227 D-18) runs the wasm
 * session inside a `worker_threads` worker (`maia-worker-thread.mjs`) behind a
 * proxy with the same `run(feeds)` contract, so one inference no longer blocks
 * the harness event loop. `offThread: false` returns the original main-thread
 * session unchanged: the parity reference and the escape hatch.
 *
 * `backend: 'native'` is onnxruntime-node from scripts/package.json: no wasm
 * heap (the OOB crash class disappears) and ~2x faster single-threaded.
 * PINNED 1.21.1 — ort >= 1.22 SEGFAULTS loading this model (same pin as
 * pyproject's onnxruntime==1.20.1, scripts/maia_parity_spike.py Pitfall 2).
 * Pinned single-threaded: sweep workers are process-sharded, so intra-op
 * threads would only oversubscribe the box; measured backend parity is
 * |d expectedScore| <= ~1e-3 (same order as native's own thread-count
 * nondeterminism, an order below E-08's accepted @100-vs-@400 budget error).
 * It also blocks the event loop (about 179 ms max lag measured) and is not
 * app-faithful.
 * NEVER mix backends within one study dataset without recording which rows
 * used which (the Stage B ledger stores `ort_backend` per row).
 */
export async function createMaiaSession({ backend = 'wasm', offThread = true } = {}) {
  const modelPath = path.resolve(FRONTEND_DIR, 'public/maia/maia3_simplified.onnx');
  if (backend === 'native') {
    const requireFromScripts = createRequire(path.join(__dirname, '..', 'package.json'));
    let ort;
    try {
      ort = requireFromScripts('onnxruntime-node');
    } catch {
      throw new Error("backend 'native' needs onnxruntime-node: run `npm install` in scripts/ first");
    }
    const session = await ort.InferenceSession.create(modelPath, {
      executionProviders: ['cpu'],
      intraOpNumThreads: 1,
      interOpNumThreads: 1,
    });
    return { ort, session };
  }
  const ort = (await resolveFrontendModule('onnxruntime-web')).default;
  // One wasm thread. The trailing comment on the next line ("the browser worker's no-COOP/COEP
  // posture") is stale: the cross-origin-isolated browser worker runs wasm Maia at 4 threads
  // (Plan 227-08 legs), so harness Maia is about 2 times slower per inference than the browser's
  // and sees almost no Maia-versus-Stockfish CPU contention (design.md section 3.6). Kept at 1 so
  // gate P stays comparable to the 226 a21s data.
  ort.env.wasm.numThreads = 1; // matches the browser worker's no-COOP/COEP posture
  // Phase 227 D-18 fix site: the main-thread wasm session blocked the event loop for its whole
  // inference (about 94 ms) and FIFO-chained inferences let no macrotask run (0 timer ticks over a
  // 373 ms 4-request burst), so Stockfish stdout went unprocessed while Maia worked. The browser
  // runs Maia in a worker, so the harness now does too.
  if (offThread) return createWorkerMaiaSession(ort, modelPath);
  const modelBytes = fs.readFileSync(modelPath);
  const session = await ort.InferenceSession.create(modelBytes, { executionProviders: ['wasm'] });
  return { ort, session };
}

/**
 * Spawns the Maia worker thread, awaits its `ready`, and returns `{ ort, session }` where `session`
 * is a proxy exposing `inputNames`, `outputNames`, `run(feeds)` and `close()` (plus a non-enumerable,
 * check-only `_worker`). `ort` stays the main-thread onnxruntime-web module: callers build their
 * `ort.Tensor` feeds with it and the proxy serializes them across the thread boundary.
 */
async function createWorkerMaiaSession(ort, modelPath) {
  // `execArgv: []`: a worker inherits the parent's execArgv by default, which re-registers the `@/`
  // alias hook (not needed: the worker imports no frontend TS) and breaks outright under
  // `--input-type=module -e` ("--input-type can only be used with string input"), the form the
  // worker-death check uses.
  const worker = new Worker(new URL('./maia-worker-thread.mjs', import.meta.url), {
    workerData: { modelPath },
    execArgv: [],
  });
  /** In-flight requests by id: `{ resolve, reject }`. */
  const pending = new Map();
  let nextId = 0;
  let closing = false;
  let ready = false;

  // Node's process 'exit' fires BEFORE it tears workers down, so a script ending by itself (or via
  // process.exit) must not see the worker's teardown 'exit' as a death and rewrite its exit code.
  process.once('exit', () => {
    closing = true;
  });

  const { inputNames, outputNames } = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      void worker.terminate();
      reject(new Error(MAIA_WORKER_FAILED_MESSAGE, { cause: new Error('timed out waiting for ready') }));
    }, MAIA_WORKER_READY_TIMEOUT_MS);
    const fail = (cause) => {
      clearTimeout(timer);
      reject(new Error(MAIA_WORKER_FAILED_MESSAGE, { cause }));
    };
    worker.once('error', fail);
    worker.once('exit', (code) => fail(new Error(`worker exited with code ${code} before ready`)));
    worker.on('message', function onReady(msg) {
      if (msg?.type !== 'ready') return;
      clearTimeout(timer);
      worker.off('message', onReady);
      worker.off('error', fail);
      resolve(msg);
    });
  });
  ready = true;
  worker.unref(); // an idle worker must not keep a script alive; re-ref'd while a request is in flight

  /** Keeps the process alive exactly while at least one request is in flight. */
  const syncRef = () => {
    if (pending.size > 0) worker.ref();
    else worker.unref();
  };

  // D-15: an unexpected worker death must END THE PROCESS, not degrade. The app-faithful Maia FIFO
  // (calibration-providers.mjs maiaFifoProcess) resolves `{}` on a rejected inference, so a dead worker
  // would otherwise turn every later policy call into an empty policy and silently corrupt hours of
  // sweep games. Today the same wasm out-of-bounds failure crashes the main-thread process and
  // `bin/preset-supervisor.sh` resumes the sweep; exiting here keeps exactly that behavior.
  const die = (cause) => {
    if (closing || !ready) return;
    ready = false;
    const failure = new Error(MAIA_WORKER_FAILED_MESSAGE, { cause });
    for (const { reject } of pending.values()) reject(failure);
    pending.clear();
    console.error(`[maia-worker] ${MAIA_WORKER_FAILED_MESSAGE}; exiting with code ${MAIA_WORKER_DIED_EXIT_CODE}`);
    process.exit(MAIA_WORKER_DIED_EXIT_CODE);
  };
  worker.on('error', (err) => die(err));
  worker.on('exit', (code) => die(new Error(`worker exited with code ${code}`)));
  worker.on('message', (msg) => {
    const request = pending.get(msg?.id);
    if (request === undefined) return;
    pending.delete(msg.id);
    syncRef();
    if (msg.type === 'result') {
      const outputs = {};
      for (const [name, out] of Object.entries(msg.outputs)) {
        outputs[name] = { type: out.type, data: out.data, dims: out.dims, dispose() {} };
      }
      request.resolve(outputs);
    } else {
      request.reject(new Error(MAIA_WORKER_FAILED_MESSAGE, { cause: new Error(msg.message) }));
    }
  });

  const session = {
    inputNames,
    outputNames,
    run(feeds) {
      return new Promise((resolve, reject) => {
        const id = nextId++;
        const serialized = {};
        const transfer = [];
        for (const [name, tensor] of Object.entries(feeds)) {
          const data = tensor.data.slice(); // copy: the caller disposes its tensor right after run()
          serialized[name] = { type: tensor.type, data, dims: [...tensor.dims] };
          transfer.push(data.buffer);
        }
        pending.set(id, { resolve, reject });
        syncRef();
        worker.postMessage({ type: 'run', id, feeds: serialized }, transfer);
      });
    },
    async close() {
      closing = true;
      await worker.terminate();
    },
  };
  Object.defineProperty(session, '_worker', { value: worker, enumerable: false });
  return { ort, session };
}

// ─── Stockfish (vendored WASM over UCI) — spawned ONCE, reused across positions ─

/** Thin line-buffered UCI stdin/stdout wrapper around the spawned Stockfish child process. */
export class StockfishUciEngine {
  /** Guards `#die`'s listener notification so one death notifies subscribers once. */
  #notifiedDeath = false;

  /**
   * `tempFilePaths` (WR-04): the `.cjs`/`.wasm` temp copies `spawnStockfish`
   * made for this process — retained here (not just at spawn time) so
   * `terminate()` can delete them; nothing else keeps a reference.
   */
  constructor(child, tempFilePaths = []) {
    this.child = child;
    this.buffer = '';
    this.lineListeners = new Set();
    this.tempFilePaths = tempFilePaths;
    this.quitting = false; // set by terminate() so the exit handler below doesn't treat a clean quit as a crash
    /**
     * Set once this engine's child process is gone (crash, unexpected exit, or
     * our own terminate()). A dead engine can never serve another `go`, so both
     * `send()` below and `stockfish-pool.mjs` check this flag: the pool evicts
     * and replaces the engine instead of handing the corpse to the next caller.
     *
     * BUG (SEED-145 Stage B, 2026-08-23): without this flag a child that exited
     * mid-sweep stayed in the pool forever. `child.stdin.write()` on a destroyed
     * stream neither throws nor delivers, so every subsequent request waited out
     * the full `waitFor` watchdog (30 s), x ENGINE_RETRY_ATTEMPTS, and then
     * failed the position. Workers 4 and 10 lost 1,098 positions that way;
     * worker 10 had no self-recycle left and ground to ~30 s/position for the
     * rest of its partition.
     */
    this.dead = false;
    /** Human-readable cause of death, used as the message when `send()` refuses to write. */
    this.deadReason = null;
    /**
     * Callbacks fired by `#die` (crash paths only — NOT an intentional
     * `terminate()`). `stockfish-pool.mjs` subscribes so it can replace an
     * engine that dies while IDLE: such an engine is never acquired again, so
     * it would never reach the release path that normally triggers eviction,
     * and the pool would silently shrink for the rest of the run.
     */
    this.deathListeners = new Set();
    this.#notifiedDeath = false;
    // WR-03: reject-with-cleanup callbacks for every in-flight waitFor(), so an
    // unexpected process death fails the pending caller immediately instead of
    // surfacing as an unhandled 'error' event or a full timeoutMs wait.
    this.pendingWaiters = new Set();

    this.child.stdout.on('data', (chunk) => {
      this.buffer += chunk.toString('utf8');
      const lines = this.buffer.split('\n');
      this.buffer = lines.pop() ?? '';
      for (const line of lines) {
        for (const listener of this.lineListeners) listener(line);
      }
    });
    this.child.on('error', (err) => {
      this.#die(`Stockfish process error: ${err.message}`);
    });
    // Phase 226-07: stderr was piped but never read, so two fixture-build runs
    // died with "exited unexpectedly (code=7)" (node's exit code when an
    // uncaughtException handler itself throws, as Emscripten's does) and no cause
    // on record; a third identical run passed. Keep a bounded tail and put it in
    // the death reason so the next such crash names its cause.
    this.stderrTail = '';
    this.child.stderr?.on('data', (chunk) => {
      this.stderrTail = (this.stderrTail + chunk.toString('utf8')).slice(-STDERR_TAIL_CHARS);
    });
    this.child.on('exit', (code, signal) => {
      if (this.quitting) {
        this.dead = true; // expected shutdown: still unusable, but not a crash to report
        return;
      }
      const stderr = this.stderrTail.trim();
      this.#die(`Stockfish process exited unexpectedly (code=${code}, signal=${signal})${stderr ? `; stderr tail: ${stderr}` : ''}`);
    });
    this.child.stdin.on('error', (err) => {
      this.#die(`Stockfish stdin error (process likely exited): ${err.message}`);
    });
  }

  /** Marks the engine unusable, fails every in-flight waitFor(), and notifies death listeners. */
  #die(reason) {
    this.dead = true;
    this.deadReason ??= reason;
    this.#failPendingWaiters(new Error(reason));
    // One death fires several handlers ('exit' plus a stdin EPIPE, typically) —
    // notify subscribers exactly once so the pool never respawns two replacements.
    if (this.#notifiedDeath) return;
    this.#notifiedDeath = true;
    for (const listener of [...this.deathListeners]) listener(this);
  }

  /**
   * Subscribes to this engine's unexpected death. Fires immediately if it is
   * already dead, so a subscriber can never miss a death that raced its own
   * registration. Returns an unsubscribe function.
   */
  onDeath(listener) {
    if (this.dead) {
      listener(this);
      return () => {};
    }
    this.deathListeners.add(listener);
    return () => this.deathListeners.delete(listener);
  }

  #failPendingWaiters(err) {
    for (const rejectWithCleanup of [...this.pendingWaiters]) rejectWithCleanup(err);
  }

  /**
   * Throws immediately on a dead engine rather than writing into a destroyed
   * stdin. That write is silently discarded by Node, so the caller's `waitFor`
   * would otherwise block for the full watchdog before failing — see the `dead`
   * doc comment above for what that cost the SEED-145 sweep.
   */
  send(command) {
    if (this.dead) throw new Error(this.deadReason ?? 'Stockfish process is dead');
    this.child.stdin.write(`${command}\n`);
  }

  onLine(listener) {
    this.lineListeners.add(listener);
    return () => this.lineListeners.delete(listener);
  }

  waitFor(predicate, timeoutMs) {
    return new Promise((resolve, reject) => {
      const cleanup = () => {
        clearTimeout(timer);
        off();
        this.pendingWaiters.delete(rejectWithCleanup);
      };
      const rejectWithCleanup = (err) => {
        cleanup();
        reject(err);
      };
      const timer = setTimeout(() => {
        rejectWithCleanup(new Error(`Stockfish response timeout after ${timeoutMs}ms`));
      }, timeoutMs);
      const off = this.onLine((line) => {
        if (predicate(line)) {
          cleanup();
          resolve(line);
        }
      });
      this.pendingWaiters.add(rejectWithCleanup);
    });
  }

  async init() {
    this.send('uci');
    await this.waitFor((line) => line === 'uciok', STOCKFISH_INIT_TIMEOUT_MS);
    this.send('isready');
    await this.waitFor((line) => line === 'readyok', STOCKFISH_INIT_TIMEOUT_MS);
  }

  /**
   * WR-01: after a position's `go` search times out (waitFor rejected), the
   * engine is still searching. Sending the next `position`/`go` on top of a live
   * search corrupts subsequent grades. Stop the search and block on `readyok` so
   * the engine is quiescent before the next position — lets the run skip one bad
   * position and continue instead of aborting the whole multi-hour sweep.
   */
  async stopAndSync() {
    this.send('stop');
    this.send('isready');
    await this.waitFor((line) => line === 'readyok', STOCKFISH_INIT_TIMEOUT_MS);
  }

  /** Kills the process AND deletes its temp `.cjs`/`.wasm` copies (WR-04) — always safe to call more than once. */
  terminate() {
    this.quitting = true; // WR-03: tells the 'exit' handler this shutdown is expected, not a crash
    if (!this.dead) this.send('quit'); // send() throws on a dead engine; a corpse needs no `quit`
    this.dead = true;
    this.deadReason ??= 'Stockfish engine was terminated';
    this.child.kill();
    for (const filePath of this.tempFilePaths) {
      fs.rmSync(filePath, { force: true });
    }
  }
}

/** Monotonic per-process spawn counter — see the `runId` comment in `spawnStockfish`. */
let spawnCounter = 0;

export async function spawnStockfish() {
  const engineDir = path.resolve(FRONTEND_DIR, 'public/engine');
  const srcJsPath = path.join(engineDir, 'stockfish-18-lite-single.js');
  const srcWasmPath = path.join(engineDir, 'stockfish-18-lite-single.wasm');

  // Copy to a non-ESM .cjs so it auto-starts a UCI CLI on stdin/stdout under Node
  // (memory note project_headless_stockfish_wasm_verification). The Emscripten
  // glue locates its .wasm binary at `path.join(__dirname, basename(__filename,
  // ext) + '.wasm')` — i.e. same directory, SAME basename minus extension — so
  // the .wasm copy must be renamed to match the .cjs basename exactly, not just
  // co-located under its original name.
  // The counter matters as much as the timestamp: the pool respawns replacement
  // engines, and two respawns in the same millisecond would otherwise share a
  // temp basename and clobber each other's .cjs/.wasm copies.
  const runId = `node-engine-providers-stockfish-${process.pid}-${Date.now()}-${spawnCounter++}`;
  const cjsPath = path.join(os.tmpdir(), `${runId}.cjs`);
  const wasmPath = path.join(os.tmpdir(), `${runId}.wasm`);
  fs.copyFileSync(srcJsPath, cjsPath);
  fs.copyFileSync(srcWasmPath, wasmPath);

  const child = spawn('node', [cjsPath], { stdio: ['pipe', 'pipe', 'pipe'] });
  const engine = new StockfishUciEngine(child, [cjsPath, wasmPath]);
  try {
    await engine.init();
  } catch (err) {
    // CR-02: the child process (and its temp file copies) must not leak if the
    // UCI handshake itself fails/times out — terminate() kills the process AND
    // unlinks the temp files even though init() never completed.
    engine.terminate();
    throw err;
  }
  return engine;
}

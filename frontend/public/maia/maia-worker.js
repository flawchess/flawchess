/**
 * maia-worker.js — classic (non-module) Web Worker running Maia-3 ("Chessformer")
 * ONNX inference via onnxruntime-web, with WebGPU-preferred / single-thread-WASM
 * fallback execution-provider selection (MAIA-02, MAIA-06, D-09).
 *
 * Served verbatim from public/maia/ (no Vite bundler processing), mirroring the
 * public/engine/ Stockfish Worker precedent (Phase 136). This is a CLASSIC Worker
 * (`new Worker('/maia/maia-worker.js')`, no `{ type: 'module' }`) so it can use
 * `importScripts()` to load onnxruntime-web's UMD-style dist bundles, which define
 * a global `ort` — the same reason the Stockfish worker glue is not an ES module.
 *
 * Message protocol (structured objects, not UCI text — this is not Stockfish):
 *   in:  { type: 'init' }
 *        { type: 'analyze', fen: string, eloInputs: number[] }
 *        { type: 'terminate' }
 *   out: { type: 'ready', backend: 'webgpu' | 'wasm' }
 *        { type: 'result', fen, rawPolicyByElo: {elo, policy: Float32Array}[],
 *                           wdlByElo: {elo, wdl: Float32Array}[], backend }
 *        { type: 'error', message: string }
 *
 * Board encoding: this worker REPLICATES the pure board->tensor functions from
 * `frontend/src/lib/maiaEncoding.ts` (a classic Worker cannot `import` a
 * TypeScript ES module without a build step it deliberately opts out of, per the
 * Stockfish precedent). If the encoding algorithm in maiaEncoding.ts changes,
 * mirror the change here — do NOT let the two diverge (151-04-PLAN.md Task 2).
 * Legal-move masking + softmax (which need chess.js) are intentionally NOT
 * replicated here: this worker returns RAW policy/WDL logits, and the main-thread
 * hook (useMaiaEngine.ts) applies maskAndSoftmax/expectedScore from the single
 * maiaEncoding.ts source — one implementation of that math, not two.
 *
 * Confirmed contract: .planning/phases/151-maia-in-the-browser-all-position-surfaces/151-MAIA-CONTRACT.md
 */

'use strict';

// ─── Asset paths (served verbatim, absolute so worker-relative resolution never matters) ──

const MODEL_PATH = '/maia/maia3_simplified.onnx';

/** WASM-CPU-only bundle (small, mobile-Safari-safe) — matches the ort-wasm-simd-threaded.{mjs,wasm} pair. */
const WASM_ONLY_RUNTIME_PATH = '/maia/ort.wasm.min.js';

/** WebGPU+WASM bundle — internally requires the ort-wasm-simd-threaded.asyncify.{mjs,wasm} pair
 *  (confirmed by inspecting the vendored v1.27.0 dist bundle; NOT the .jsep pair some
 *  onnxruntime-web docs reference for older/different bundle combinations). */
const WEBGPU_RUNTIME_PATH = '/maia/ort.webgpu.min.js';

/** Prefix onnxruntime-web appends its build-specific .wasm/.mjs filename to. */
const WASM_ASSET_PREFIX = '/maia/';

// ─── Board encoding constants (mirrors maiaEncoding.ts — see file header) ─────────────────

const NUM_SQUARES_PER_SIDE = 8;
const NUM_SQUARES = 64;
const PLANES_PER_SQUARE = 12;
const POLICY_VOCAB_SIZE = 4352;
const WDL_SIZE = 3;

/** Warmup inference (startpos, single ELO) run under the WebGPU try/catch so lazily-
 *  compiled compute shaders (e.g. the `Clip` node) are exercised BEFORE we commit to
 *  the webgpu backend — see initSession. */
const WARMUP_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const WARMUP_ELO = 1500;

/** Confirmed 12-plane order (CONTRACT §a): white P,N,B,R,Q,K, black p,n,b,r,q,k. */
const PIECE_PLANE_ORDER = ['P', 'N', 'B', 'R', 'Q', 'K', 'p', 'n', 'b', 'r', 'q', 'k'];

/**
 * Mirrors a FEN piece-placement field: flips ranks top-to-bottom and swaps piece
 * colors, so the side to move is always presented as "White" (CONTRACT §a).
 */
function mirrorPiecePlacement(piecePlacement) {
  const ranks = piecePlacement.split('/');
  return ranks
    .slice()
    .reverse()
    .map((row) => row.replace(/[a-zA-Z]/g, (c) => (c === c.toUpperCase() ? c.toLowerCase() : c.toUpperCase())))
    .join('/');
}

/** Encodes a (possibly-mirrored) piece-placement field into a flat (64*12) tensor. */
function encodePiecePlacement(piecePlacement) {
  const tokens = new Float32Array(NUM_SQUARES * PLANES_PER_SQUARE);
  const rows = piecePlacement.split('/'); // rows[0] = rank8 ... rows[7] = rank1
  for (let rowFromTop = 0; rowFromTop < NUM_SQUARES_PER_SIDE; rowFromTop++) {
    const row = NUM_SQUARES_PER_SIDE - 1 - rowFromTop; // rank8 -> row7, rank1 -> row0
    let file = 0;
    const rowStr = rows[rowFromTop] || '';
    for (const char of rowStr) {
      const emptyCount = Number.parseInt(char, 10);
      if (Number.isNaN(emptyCount)) {
        const planeIdx = PIECE_PLANE_ORDER.indexOf(char);
        if (planeIdx >= 0) {
          tokens[(row * NUM_SQUARES_PER_SIDE + file) * PLANES_PER_SQUARE + planeIdx] = 1.0;
        }
        file += 1;
      } else {
        file += emptyCount;
      }
    }
  }
  return tokens;
}

/** Encodes a full FEN into the `tokens[64,12]` input tensor, mirroring on Black-to-move. */
function encodeBoardTokens(fen) {
  const parts = fen.split(' ');
  const piecePlacement = parts[0];
  const isBlackToMove = parts[1] === 'b';
  const framed = isBlackToMove ? mirrorPiecePlacement(piecePlacement) : piecePlacement;
  return encodePiecePlacement(framed);
}

// ─── Session lifecycle ──────────────────────────────────────────────────────────────────

/** @type {import('onnxruntime-web').InferenceSession | null} */
let session = null;
/** @type {'webgpu' | 'wasm' | null} */
let backend = null;

/**
 * Feature-detects WebGPU and attempts a WebGPU session; falls back to single-thread
 * WASM on ANY failure (no GPU adapter, session-create failure, or an unsupported op
 * — Pitfall 4). `ort.env.wasm.numThreads` is forced to 1 on EVERY path before any
 * session is created: this site ships no cross-origin-isolation headers (locked
 * Phase 136 D-3, CI-guarded), so multi-thread WASM (which needs SharedArrayBuffer)
 * must never be attempted, regardless of which execution provider ends up active.
 */
async function initSession() {
  let gpuAdapter = null;
  try {
    gpuAdapter = self.navigator && self.navigator.gpu ? await navigator.gpu.requestAdapter() : null;
  } catch {
    gpuAdapter = null;
  }

  if (gpuAdapter) {
    try {
      importScripts(WEBGPU_RUNTIME_PATH);
      ort.env.wasm.numThreads = 1;
      ort.env.wasm.wasmPaths = WASM_ASSET_PREFIX;
      session = await ort.InferenceSession.create(MODEL_PATH, { executionProviders: ['webgpu'] });
      // BUG FIX: WebGPU compiles compute shaders LAZILY on first run, not at create().
      // On Firefox/Windows the `Clip` shader ("ShaderModule with 'Clip' label is invalid",
      // sequential_executor.cc ExecuteKernel) fails only at run time, so wrapping create()
      // alone let a broken webgpu session slip through — the first real analyze() then threw
      // and Maia died with no WASM fallback. A warmup run inside this try surfaces the shader
      // failure here so the catch below falls through to WASM.
      await analyze(WARMUP_FEN, [WARMUP_ELO]);
      backend = 'webgpu';
      return;
    } catch {
      // WebGPU session-create, op-support, or lazy shader-compile failure (Pitfall 4) —
      // fall through to WASM.
      session = null;
    }
  }

  importScripts(WASM_ONLY_RUNTIME_PATH);
  ort.env.wasm.numThreads = 1; // NEVER > 1 — no cross-origin isolation (Phase 136 D-3)
  ort.env.wasm.wasmPaths = WASM_ASSET_PREFIX;
  session = await ort.InferenceSession.create(MODEL_PATH, { executionProviders: ['wasm'] });
  backend = 'wasm';
}

/**
 * Runs ONE batched inference across the ELO ladder for a fixed FEN: the same board
 * tensor is repeated B times, only elo_self/elo_oppo vary per batch item
 * (CONTRACT §f — batch dimension confirmed usable). elo_self === elo_oppo per rung,
 * mirroring the symmetric-strength sweep 151-01 validated (both sides rated the
 * same, to answer "how would a player of rating X play this position").
 */
async function analyze(fen, eloInputs) {
  const batchSize = eloInputs.length;
  const boardTokens = encodeBoardTokens(fen);
  const tokens = new Float32Array(batchSize * NUM_SQUARES * PLANES_PER_SQUARE);
  for (let b = 0; b < batchSize; b++) {
    tokens.set(boardTokens, b * NUM_SQUARES * PLANES_PER_SQUARE);
  }
  const eloSelf = Float32Array.from(eloInputs);
  const eloOppo = Float32Array.from(eloInputs);

  const feeds = {
    tokens: new ort.Tensor('float32', tokens, [batchSize, NUM_SQUARES, PLANES_PER_SQUARE]),
    elo_self: new ort.Tensor('float32', eloSelf, [batchSize]),
    elo_oppo: new ort.Tensor('float32', eloOppo, [batchSize]),
  };

  let outputs;
  try {
    outputs = await session.run(feeds);
    const policyFlat = outputs.logits_move.data;
    const wdlFlat = outputs.logits_value.data;

    // `.slice()` copies the logits out of wasm memory, so the tensors can be disposed
    // in `finally` below without invalidating what we return.
    const rawPolicyByElo = eloInputs.map((elo, i) => ({
      elo,
      policy: policyFlat.slice(i * POLICY_VOCAB_SIZE, (i + 1) * POLICY_VOCAB_SIZE),
    }));
    const wdlByElo = eloInputs.map((elo, i) => ({
      elo,
      wdl: wdlFlat.slice(i * WDL_SIZE, (i + 1) * WDL_SIZE),
    }));

    return { rawPolicyByElo, wdlByElo };
  } finally {
    // BUG FIX (SEED-113, 2026-07-21): onnxruntime-web ort.Tensor buffers live in the wasm
    // linear heap and MUST be disposed, or every inference leaks them. The same omission in
    // the calibration harness grew the heap until it threw "memory access out of bounds"
    // mid-run (~270k policy calls); only a fresh process cleared it. Exposure here is much
    // lower (per-tab session, WebGPU preferred), but a marathon wasm-only mobile session
    // hits the same wall. Disposing inputs + outputs per call keeps the heap flat.
    // Optional-chained to stay safe across ORT backends/versions lacking dispose().
    for (const t of Object.values(feeds)) t.dispose?.();
    if (outputs) for (const t of Object.values(outputs)) t.dispose?.();
  }
}

// ─── Message handling ───────────────────────────────────────────────────────────────────

self.onmessage = async (e) => {
  const msg = e.data || {};
  try {
    if (msg.type === 'init') {
      await initSession();
      self.postMessage({ type: 'ready', backend });
      return;
    }

    if (msg.type === 'analyze') {
      if (!session) {
        throw new Error('maia-worker: analyze received before session init completed');
      }
      const { rawPolicyByElo, wdlByElo } = await analyze(msg.fen, msg.eloInputs);
      self.postMessage({ type: 'result', fen: msg.fen, rawPolicyByElo, wdlByElo, backend });
      return;
    }

    if (msg.type === 'terminate') {
      session = null;
      self.close();
      return;
    }
  } catch (err) {
    self.postMessage({ type: 'error', message: err && err.message ? err.message : String(err) });
  }
};

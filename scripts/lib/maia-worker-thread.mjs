#!/usr/bin/env node
/**
 * maia-worker-thread.mjs — `node:worker_threads` entry that holds the harness's
 * onnxruntime-web Maia session (Phase 227 D-18).
 *
 * WHY: the main-thread wasm session blocks the harness event loop for its whole
 * inference (~94 ms measured) and FIFO-chained inferences let no macrotask run
 * (0 timer ticks over a 373 ms 4-request burst), so Stockfish stdout went
 * unprocessed while Maia worked. The browser runs Maia in a Web Worker
 * (`frontend/src/lib/engine/maiaWorkerHost.ts`); the harness now does too. This
 * file only moves WHERE the inference runs: same model bytes, same numThreads 1,
 * same feeds, so outputs are byte-identical to the main-thread session.
 *
 * Protocol (mirrors maiaWorkerHost's ready/result/error shape):
 *   worker -> main  { type: 'ready', inputNames, outputNames }
 *   main -> worker  { type: 'run', id, feeds: { [name]: { type, data, dims } } }
 *   worker -> main  { type: 'result', id, outputs: { [name]: { type, data, dims } } }
 *                   (data buffers are transferred, not copied)
 *   worker -> main  { type: 'error', id, message }
 *
 * Only `createMaiaSession` in node-engine-providers.mjs spawns this file.
 */
import { parentPort, workerData } from 'node:worker_threads';
import fs from 'node:fs';

import { resolveFrontendModule } from './node-engine-providers.mjs';

async function main() {
  const ort = (await resolveFrontendModule('onnxruntime-web')).default;
  ort.env.wasm.numThreads = 1; // identical to createMaiaSession's main-thread session
  const modelBytes = fs.readFileSync(workerData.modelPath);
  const session = await ort.InferenceSession.create(modelBytes, { executionProviders: ['wasm'] });

  /** Runs one request; every tensor this call creates is disposed in `finally` (SEED-113). */
  async function runOne(feedSpecs) {
    const feeds = {};
    for (const [name, spec] of Object.entries(feedSpecs)) {
      feeds[name] = new ort.Tensor(spec.type, spec.data, spec.dims);
    }
    let result;
    try {
      result = await session.run(feeds);
      const outputs = {};
      for (const [name, tensor] of Object.entries(result)) {
        // `.slice()` copies out of the wasm heap BEFORE the output tensor is disposed below.
        outputs[name] = { type: tensor.type, data: tensor.data.slice(), dims: [...tensor.dims] };
      }
      return outputs;
    } finally {
      // BUG FIX (SEED-113): ort-web tensors live in the wasm linear heap and must be disposed,
      // or every inference leaks them. Same discipline as runMaia's finally in
      // calibration-providers.mjs, kept here because the tensors this worker creates are its own.
      for (const t of Object.values(feeds)) t.dispose?.();
      if (result) for (const t of Object.values(result)) t.dispose?.();
    }
  }

  // One request at a time: chain every message onto the previous one so two
  // posted runs can never overlap inside the single wasm instance.
  let chain = Promise.resolve();
  parentPort.on('message', (msg) => {
    if (msg?.type !== 'run') return;
    chain = chain.then(async () => {
      try {
        const outputs = await runOne(msg.feeds);
        const transfer = Object.values(outputs).map((o) => o.data.buffer);
        parentPort.postMessage({ type: 'result', id: msg.id, outputs }, transfer);
      } catch (err) {
        // Never let an exception escape the handler: the caller needs its request id back.
        parentPort.postMessage({ type: 'error', id: msg.id, message: err instanceof Error ? err.message : String(err) });
      }
    });
  });

  parentPort.postMessage({ type: 'ready', inputNames: [...session.inputNames], outputNames: [...session.outputNames] });
}

// A failure before 'ready' (model load, ort import) rejects here, becomes an uncaught error in the
// worker, and reaches the parent's 'error' listener, which rejects createMaiaSession() with it.
await main();

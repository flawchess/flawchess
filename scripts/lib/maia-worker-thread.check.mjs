#!/usr/bin/env node
/**
 * maia-worker-thread.check.mjs — proves the Phase 227 D-18 worker-thread Maia session
 * (`createMaiaSession()` default) is faithful AND actually off the event loop.
 *
 * Sections:
 *   (a) PARITY: for >= 6 FENs x MAIA_PARITY_ELOS, `logits_move` and `logits_value` bytes from the
 *       worker session are identical to the `offThread: false` main-thread session (T-227-01).
 *   (b) EVENT LOOP: a MAIA_BURST-request app-faithful FIFO burst through `makeNodeProviders` on the
 *       worker session keeps the main thread servicing timers (max loop delay below
 *       MAIA_WORKER_MAX_LOOP_LAG_MS, tick count within TICK_SLACK of burstMs / LOOP_TICK_MS). The
 *       identical burst on the main-thread session MUST fail that bound (negative control: proves the
 *       assertion discriminates; research measured ~94 ms per inference).
 *   (c) WORKER DEATH: a child process that kills its Maia worker mid-request must exit with
 *       MAIA_WORKER_DIED_EXIT_CODE (never hang or exit 0 into empty policies).
 *   (d) The worker session is never `close()`d: this script must exit by itself (ref/unref handling).
 *       Run it under `timeout`: an exit 124 means the process did not exit on its own.
 *
 * Run via:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/maia-worker-thread.check.mjs
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  createMaiaSession,
  MAIA_WORKER_DIED_EXIT_CODE,
  FRONTEND_DIR,
} from './node-engine-providers.mjs';
import { makeNodeProviders, resetMaiaRunMemo } from './calibration-providers.mjs';
import { encodeBoard, eloToInput, NUM_SQUARES, PLANES_PER_SQUARE } from '@/lib/maiaEncoding';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');

/** ELO inputs the parity section runs every FEN at (both players use the same value). */
const MAIA_PARITY_ELOS = [1100, 1900];
/** Minimum FEN count for the parity section (first fixture rows plus the start position). */
const MIN_PARITY_FENS = 6;
/** Requests in the FIFO burst of section (b). */
const MAIA_BURST = 4;
/** Resolution (ms) of the tick counter that proves timers keep firing. */
const LOOP_TICK_MS = 10;
/** Max event-loop delay (ms) tolerated while the worker session runs the burst. Research: main-thread ~94 ms. */
const MAIA_WORKER_MAX_LOOP_LAG_MS = 30;
/** Ticks the worker burst may lose versus `floor(burstMs / LOOP_TICK_MS)` (message handling, softmax, SAN to UCI). */
const TICK_SLACK = 5;
/** Wall-clock ceiling (ms) for the death-section child process. */
const DEATH_CHILD_TIMEOUT_MS = 60_000;

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const WARMUP_FEN = 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4';
const FIXTURE_PATH = path.resolve(REPO_ROOT, 'fixtures/engine/move-quality-226.tsv');
const BURST_SIDE = 'w';
const BURST_ELO = 1500;

let ok = true;
function check(cond, label) {
  if (cond) {
    console.log(`PASS: ${label}`);
  } else {
    console.error(`FAIL: ${label}`);
    ok = false;
  }
}

/** First `count` data rows' FENs of the move-quality fixture (comment lines and the header are skipped). */
function fixtureFens(count) {
  const rows = fs
    .readFileSync(FIXTURE_PATH, 'utf8')
    .split('\n')
    .filter((line) => line !== '' && !line.startsWith('#') && !line.startsWith('id\t'));
  return rows.slice(0, count).map((line) => line.split('\t')[1]);
}

/** The exact feeds `runMaia` builds (calibration-providers.mjs), so parity covers the real call shape. */
function buildFeeds(ort, fen, elo) {
  return {
    tokens: new ort.Tensor('float32', encodeBoard(fen), [1, NUM_SQUARES, PLANES_PER_SQUARE]),
    elo_self: new ort.Tensor('float32', Float32Array.of(eloToInput(elo)), [1]),
    elo_oppo: new ort.Tensor('float32', Float32Array.of(eloToInput(elo)), [1]),
  };
}

/** Runs one inference and returns copies of the two output heads as raw byte Buffers. */
async function runHeads(session, ort, fen, elo) {
  const feeds = buildFeeds(ort, fen, elo);
  let result;
  try {
    result = await session.run(feeds);
    const bytesOf = (t) => Buffer.from(t.data.slice().buffer);
    return { move: bytesOf(result.logits_move), value: bytesOf(result.logits_value) };
  } finally {
    for (const t of Object.values(feeds)) t.dispose?.();
    if (result) for (const t of Object.values(result)) t.dispose?.();
  }
}

async function checkParity(worker, main) {
  const fens = [START_FEN, ...fixtureFens(MIN_PARITY_FENS)];
  let identical = 0;
  let total = 0;
  for (const fen of fens) {
    for (const elo of MAIA_PARITY_ELOS) {
      const fromWorker = await runHeads(worker.session, worker.ort, fen, elo);
      const fromMain = await runHeads(main.session, main.ort, fen, elo);
      total++;
      const same = fromWorker.move.equals(fromMain.move) && fromWorker.value.equals(fromMain.value);
      if (same) identical++;
      else console.error(`  mismatch: ${fen} @ ${elo}`);
    }
  }
  check(
    total >= MIN_PARITY_FENS * MAIA_PARITY_ELOS.length && identical === total,
    `(a) worker output byte-identical to the main-thread session on ${identical}/${total} (FEN, ELO) pairs`,
  );
}

/**
 * Fires one FIFO burst and reports the worst event-loop lag and the tick count over its wall time.
 * Lag is measured with a self-timed interval (gap between consecutive ticks minus the tick period),
 * NOT `monitorEventLoopDelay`: that histogram read 1.1 ms over a burst whose timer never fired once
 * (0 ticks in ~370 ms), so it cannot serve as the negative control's instrument.
 */
async function measureBurst(session, ort, burstFens) {
  resetMaiaRunMemo();
  const providers = makeNodeProviders(session, ort, async () => new Map(), { maiaFifo: true });
  let ticks = 0;
  let maxLagMs = 0;
  let lastTickAt = performance.now();
  const interval = setInterval(() => {
    const now = performance.now();
    maxLagMs = Math.max(maxLagMs, now - lastTickAt - LOOP_TICK_MS);
    lastTickAt = now;
    ticks++;
  }, LOOP_TICK_MS);
  const startedAt = performance.now();
  try {
    const results = await Promise.all(burstFens.map((fen) => providers.policy(fen, BURST_ELO, BURST_SIDE)));
    const burstMs = performance.now() - startedAt;
    const ticksDuringBurst = ticks;
    // A starved timer only reveals its lag when it finally fires: let one tick through before
    // reading `maxLagMs`, otherwise a fully blocked burst would read as 0 ms.
    await new Promise((resolve) => setTimeout(resolve, LOOP_TICK_MS * 2));
    const nonEmpty = results.every((r) => Object.keys(r).length > 0);
    return { burstMs, maxLagMs, ticks: ticksDuringBurst, nonEmpty };
  } finally {
    clearInterval(interval);
  }
}

async function checkEventLoop(worker, main) {
  const burstFens = fixtureFens(MAIA_BURST);
  // Warm both sessions on a FEN outside the burst so first-inference wasm warm-up is not measured.
  for (const s of [worker, main]) {
    resetMaiaRunMemo();
    await runHeads(s.session, s.ort, WARMUP_FEN, BURST_ELO);
  }

  const w = await measureBurst(worker.session, worker.ort, burstFens);
  const minTicks = Math.floor(w.burstMs / LOOP_TICK_MS) - TICK_SLACK;
  check(w.nonEmpty, '(b) worker-session burst returned a non-empty policy for every request');
  check(
    w.maxLagMs < MAIA_WORKER_MAX_LOOP_LAG_MS,
    `(b) worker session: max event-loop lag ${w.maxLagMs.toFixed(1)} ms < ${MAIA_WORKER_MAX_LOOP_LAG_MS} ms over a ${w.burstMs.toFixed(0)} ms burst`,
  );
  check(
    w.ticks >= minTicks,
    `(b) worker session: ${w.ticks} timer ticks >= ${minTicks} (burst ${w.burstMs.toFixed(0)} ms / ${LOOP_TICK_MS} ms tick - ${TICK_SLACK} slack)`,
  );

  // Negative control: the identical burst on the main-thread session must break the same bound.
  const m = await measureBurst(main.session, main.ort, burstFens);
  check(
    m.maxLagMs >= MAIA_WORKER_MAX_LOOP_LAG_MS,
    `(b) negative control: main-thread session max event-loop lag ${m.maxLagMs.toFixed(1)} ms >= ${MAIA_WORKER_MAX_LOOP_LAG_MS} ms (${m.ticks} ticks over ${m.burstMs.toFixed(0)} ms)`,
  );
  console.log(
    `MEASURED: worker max lag ${w.maxLagMs.toFixed(1)} ms (${w.ticks} ticks / ${w.burstMs.toFixed(0)} ms); ` +
      `main-thread max lag ${m.maxLagMs.toFixed(1)} ms (${m.ticks} ticks / ${m.burstMs.toFixed(0)} ms)`,
  );
}

/** Source of the child process: opens a worker session, starts a run, then kills the worker. */
function deathChildSource() {
  const providers = pathToFileURL(path.join(__dirname, 'node-engine-providers.mjs')).href;
  const encoding = pathToFileURL(path.join(FRONTEND_DIR, 'src/lib/maiaEncoding.ts')).href;
  return `
    import { createMaiaSession } from ${JSON.stringify(providers)};
    import { encodeBoard, eloToInput, NUM_SQUARES, PLANES_PER_SQUARE } from ${JSON.stringify(encoding)};
    const { ort, session } = await createMaiaSession();
    const feeds = {
      tokens: new ort.Tensor('float32', encodeBoard(${JSON.stringify(START_FEN)}), [1, NUM_SQUARES, PLANES_PER_SQUARE]),
      elo_self: new ort.Tensor('float32', Float32Array.of(eloToInput(1500)), [1]),
      elo_oppo: new ort.Tensor('float32', Float32Array.of(eloToInput(1500)), [1]),
    };
    session.run(feeds).catch(() => {});
    await session._worker.terminate();
    // If the worker death handler ended the process we never get here; a hang or a clean exit is the bug.
    await new Promise((resolve) => setTimeout(resolve, 5000));
  `;
}

function checkWorkerDeath() {
  const hook = path.join(__dirname, 'frontend-alias-hook.mjs');
  const child = spawnSync(
    process.execPath,
    ['--import', hook, '--input-type=module', '-e', deathChildSource()],
    { cwd: REPO_ROOT, encoding: 'utf8', timeout: DEATH_CHILD_TIMEOUT_MS },
  );
  check(
    child.status === MAIA_WORKER_DIED_EXIT_CODE,
    `(c) a killed Maia worker ends the process with exit code ${MAIA_WORKER_DIED_EXIT_CODE} (got status=${child.status}, signal=${child.signal})`,
  );
  if (child.status !== MAIA_WORKER_DIED_EXIT_CODE) console.error(child.stderr);
}

async function main() {
  const worker = await createMaiaSession();
  const main = await createMaiaSession({ offThread: false });
  check(
    Array.isArray(worker.session.inputNames) && worker.session.inputNames.length === 3 && worker.session.outputNames.includes('logits_move'),
    `worker session proxy exposes inputNames (${worker.session.inputNames.join(',')}) and outputNames (${worker.session.outputNames.join(',')})`,
  );
  check(!Object.keys(worker.session).includes('_worker'), 'worker session _worker is non-enumerable (check-only handle)');

  await checkParity(worker, main);
  await checkEventLoop(worker, main);
  checkWorkerDeath();

  if (ok) console.log('MAIA-WORKER-CHECK PASS');
  else console.error('MAIA-WORKER-CHECK FAIL');
  process.exitCode = ok ? 0 : 1;
  // (d) deliberately NO worker.session.close() and NO process.exit(): the process must end by itself.
}

main().catch((err) => {
  console.error(`FAIL: unexpected error — ${err.stack ?? err}`);
  process.exit(1);
});

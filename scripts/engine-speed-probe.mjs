#!/usr/bin/env node
/**
 * engine-speed-probe.mjs — external machine-speed probe for Phase 227's
 * interleaved throughput gate (D-17).
 *
 * Why this exists: Phase 226's raw-wall throughput gate failed its underfill on
 * machine drift between runs (about +/-12% run to run on this box). D-17 judges
 * the interleaved A1/A0 raw-wall ratio NORMALIZED BY an external machine-speed
 * reading, not by the arm's own grade time (which a faster dispatch loop would
 * shrink too, hiding exactly the effect being measured). This script is that
 * reading: a fixed, arm-independent workload whose wall time moves with the
 * machine and nothing else.
 *
 * Workload (fixed, frozen by the accept rule):
 *   1. Stockfish: one engine (Hash = WORKER_HASH_MB), `go nodes PROBE_SF_NODES`
 *      from each of PROBE_FENS (`ucinewgame` + `isready` before each), timed in
 *      total as sf_ms. Node-count searches are deterministic work, so the wall
 *      time is machine speed.
 *   2. Maia: PROBE_MAIA_INFERENCES real `policy()` calls through
 *      `makeNodeProviders` at PROBE_MAIA_ELO (worker-thread session, the same
 *      one the gate scripts use), `resetMaiaRunMemo()` before each so every call
 *      is a real inference, timed in total as maia_ms.
 *   Both stages run after an untimed warm-up (wasm JIT, model load) so the
 *   reading is steady-state.
 *
 * Output: exactly one stdout line
 *   SPEED-PROBE sf_ms=<float> maia_ms=<float> total_ms=<float>
 * and exit 0. Any failure exits non-zero with no SPEED-PROBE line.
 *
 * Usage: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-speed-probe.mjs
 */
import { performance } from 'node:perf_hooks';
import { pathToFileURL } from 'node:url';

import { createMaiaSession, spawnStockfish } from './lib/node-engine-providers.mjs';
import { makeNodeProviders, resetMaiaRunMemo } from './lib/calibration-providers.mjs';

import { WORKER_HASH_MB } from '@/lib/engine/workerPoolState';

/** Probe positions: varied middlegame/endgame shapes so neither stage times a single trivial tree. */
export const PROBE_FENS = Object.freeze([
  'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3',
  'r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 7',
  'r2q1rk1/pp2bppp/2n1pn2/3p4/3P1B2/2N1PN2/PP3PPP/R2QKB1R w KQ - 3 9',
  '2r2rk1/pp1bqppp/2n1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/2KR1B1R w - - 1 11',
  '8/5pk1/6p1/3P4/2K3P1/8/5P2/8 w - - 0 1',
]);

/** Stockfish node budget per probe FEN. Chosen so the whole probe takes 10-20 s on this box. */
export const PROBE_SF_NODES = 1_800_000;

/** Number of timed Maia inferences (cycled over PROBE_FENS). */
export const PROBE_MAIA_INFERENCES = 60;

/** Neutral ELO the probe infers at (same for both sides). */
export const PROBE_MAIA_ELO = 1500;

/** Untimed Stockfish warm-up node budget (wasm JIT). */
const WARMUP_SF_NODES = 20_000;

/** Per-search watchdog; a probe node search takes about two seconds, so this only fires on a hung engine. */
const SF_SEARCH_TIMEOUT_MS = 120_000;

/** Stockfish `go nodes` searches over every PROBE_FENS entry, awaiting `bestmove`. */
async function runStockfishSearches(engine, nodes) {
  for (const fen of PROBE_FENS) {
    engine.send('ucinewgame');
    engine.send('isready');
    await engine.waitFor((line) => line === 'readyok', SF_SEARCH_TIMEOUT_MS);
    engine.send(`position fen ${fen}`);
    engine.send(`go nodes ${nodes}`);
    await engine.waitFor((line) => line.startsWith('bestmove'), SF_SEARCH_TIMEOUT_MS);
  }
}

/** Times the Stockfish stage in ms (after an untimed warm-up pass). */
async function timeStockfish() {
  const engine = await spawnStockfish();
  try {
    engine.send(`setoption name Hash value ${WORKER_HASH_MB}`);
    engine.send('isready');
    await engine.waitFor((line) => line === 'readyok', SF_SEARCH_TIMEOUT_MS);
    await runStockfishSearches(engine, WARMUP_SF_NODES);
    const start = performance.now();
    await runStockfishSearches(engine, PROBE_SF_NODES);
    return performance.now() - start;
  } finally {
    engine.terminate();
  }
}

/** Times PROBE_MAIA_INFERENCES real Maia policy() calls in ms (after one untimed warm-up call). */
async function timeMaia() {
  const { session, ort } = await createMaiaSession();
  try {
    const providers = makeNodeProviders(session, ort, async () => new Map());
    resetMaiaRunMemo();
    await providers.policy(PROBE_FENS[0], PROBE_MAIA_ELO, 'w');
    const start = performance.now();
    for (let i = 0; i < PROBE_MAIA_INFERENCES; i++) {
      resetMaiaRunMemo(); // every call must be a real inference, never a memo hit
      await providers.policy(PROBE_FENS[i % PROBE_FENS.length], PROBE_MAIA_ELO, 'w');
    }
    return performance.now() - start;
  } finally {
    await session.close?.();
  }
}

async function main() {
  const sfMs = await timeStockfish();
  const maiaMs = await timeMaia();
  const totalMs = sfMs + maiaMs;
  process.stdout.write(
    `SPEED-PROBE sf_ms=${sfMs.toFixed(1)} maia_ms=${maiaMs.toFixed(1)} total_ms=${totalMs.toFixed(1)}\n`,
    () => process.exit(0),
  );
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error(`SPEED-PROBE-FAILED: ${err instanceof Error ? err.message : String(err)}`);
    process.exit(1);
  });
}

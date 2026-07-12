#!/usr/bin/env node
/**
 * calibration-determinism.check.mjs — D-09 seeded-reproducibility assertion
 * (Phase 168, Plan 02, Task 2).
 *
 * Runs `playGame()` from `../calibration-harness.mjs` TWICE against REAL
 * engines (Maia ONNX + Stockfish WASM — unlike the stub-provider
 * `calibration-parity.check.mjs`, this is a real-engine check) with the
 * IDENTICAL seed/opening/color, for a full `blend=1` game, and asserts
 * (`node:assert/strict`) the two resulting `moveUcis` sequences are
 * byte-identical.
 *
 * The anchor is a raw-Maia-argmax anchor (`maia1500`), deliberately NOT a
 * Stockfish-skill anchor — Stockfish's own `Skill Level` weakening injects
 * engine-internal randomness that would confound this test with a source of
 * nondeterminism unrelated to the harness's OWN seeded `mulberry32` rng
 * (D-09's actual subject: `selectBotMove`'s deterministic `blend=1` argmax
 * regime + the seeded rng plumbing, not Stockfish's skill-level noise).
 *
 * This check overrides `playGame`'s D-11 budget down to a small
 * `DETERMINISM_MAX_NODES`/`DETERMINISM_MAX_PLIES` — reproducibility is a
 * structural property of the seeded `mulberry32` rng + `argmaxLine`'s
 * canonical tie-break (D-06/D-09), which does not depend on budget size, and
 * the CAL-03 spike (168-02 Task 2) already independently measured that the
 * real D-11 budget (400 nodes) costs ~170s/move under WASM+single-Stockfish —
 * running this check at that full cost would take this determinism proof
 * ~2 hours instead of the ~1-2 minutes RESEARCH.md's Sampling Rate section
 * expects of a per-wave-merge check.
 *
 * Plan 03 note (investigated during Task 1): under real machine load, a
 * `grade()` call can exceed its `GRADING_MOVETIME_SAFETY_CAP_MS + SLACK_MS`
 * (5000ms) response-wait ceiling, which THROWS (not silently degrades) and
 * aborts the whole check with a "Stockfish response timeout" error — this is
 * a PRE-EXISTING fragility of the movetime-capped grading design inherited
 * from Plan 01/02, confirmed via an A/B test that reproduced the IDENTICAL
 * timeout on the untouched pre-pool (Plan 02) code on the same loaded
 * machine — NOT a regression introduced by the Stockfish pool. It surfaces
 * as either a hard timeout (as above) or, more subtly, a byte-level replay
 * divergence: if a `movetime`-bounded search doesn't reach
 * `GRADING_TARGET_DEPTH` identically in both runs (because real elapsed time
 * relative to the 2500ms cap differs run-to-run under load), the returned
 * eval can differ by a few centipawns, which `mctsSearch`'s own
 * deterministic-per-concurrency-level node-selection (mctsSearch.ts's module
 * header) then legitimately propagates into a different move choice — this
 * applies at ANY pool size, including 1, since it is a property of the
 * ENGINE's real-time response, not of routing across independent pool
 * engines. On a quiet machine this check passes reliably (confirmed on this
 * pool-backed code at `--stockfish-procs 2`); flag a failure here as
 * "retry on a quieter machine" before treating it as a regression.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs
 */
import assert from 'node:assert/strict';

import { setupHarnessEngines, playGame, parseAnchorSpec } from '../calibration-harness.mjs';
import { OPENING_BOOK } from './calibration-openings.mjs';
import { mulberry32 } from '@/lib/engine/botSampling';

const DETERMINISM_SEED = 42;
const DETERMINISM_ELO = 1500;
const DETERMINISM_BLEND = 1; // full-Stockfish argmax — the deterministic regime this check must prove reproducible
const DETERMINISM_BOT_IS_WHITE = true;
/** Small budget override (see module doc comment) — NOT the D-11 fixed grid constant. */
const DETERMINISM_MAX_NODES = 20;
const DETERMINISM_MAX_PLIES = 8;

const opening = OPENING_BOOK[0];
const anchorSpec = parseAnchorSpec('maia1500');

/** Small pool for the determinism check — 2 processes exercises the real acquire/release path, not just a trivial size-1 pass-through. */
const DETERMINISM_STOCKFISH_PROCS = 2;

const { providers, pool, Chess } = await setupHarnessEngines({ stockfishProcs: DETERMINISM_STOCKFISH_PROCS });

try {
  const gameRng1 = mulberry32(DETERMINISM_SEED);
  const result1 = await playGame({
    Chess,
    providers,
    pool,
    botElo: DETERMINISM_ELO,
    botBlend: DETERMINISM_BLEND,
    anchorSpec,
    startFen: opening.fen,
    botIsWhite: DETERMINISM_BOT_IS_WHITE,
    gameRng: gameRng1,
    maxNodes: DETERMINISM_MAX_NODES,
    maxPlies: DETERMINISM_MAX_PLIES,
  });

  const gameRng2 = mulberry32(DETERMINISM_SEED);
  const result2 = await playGame({
    Chess,
    providers,
    pool,
    botElo: DETERMINISM_ELO,
    botBlend: DETERMINISM_BLEND,
    anchorSpec,
    startFen: opening.fen,
    botIsWhite: DETERMINISM_BOT_IS_WHITE,
    gameRng: gameRng2,
    maxNodes: DETERMINISM_MAX_NODES,
    maxPlies: DETERMINISM_MAX_PLIES,
  });

  assert.deepEqual(
    result2.moveUcis,
    result1.moveUcis,
    'same --seed must reproduce a byte-identical blend=1 game (D-09)',
  );

  console.log(
    `PASS: calibration determinism — same seed reproduced an identical ${result1.moveUcis.length}-ply blend=1 game ` +
      `(result=${result1.result}, reason=${result1.reason}, stockfish-procs=${DETERMINISM_STOCKFISH_PROCS})`,
  );
} finally {
  pool.quitAll();
}

process.exit(0);

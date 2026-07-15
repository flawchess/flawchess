#!/usr/bin/env node
/**
 * calibration-determinism.check.mjs — D-09 seeded-reproducibility assertion
 * (Phase 168, Plan 02, Task 2; re-budgeted Phase 168.5, Plan 05, Task 3, SC5).
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
 * **Phase 168.5-05 SC5 re-budget:** this check now runs `playGame` at its
 * DEFAULT budget — i.e. no `maxNodes`/`maxPlies` override — which resolves to
 * the actual SHIPPED bot budget (`FLAWCHESS_BOT_MAX_NODES`=50/
 * `FLAWCHESS_BOT_MAX_PLIES`=8), and `playGame` has ALWAYS unconditionally
 * carried `stopRule: FLAWCHESS_BOT_STOP_RULE` + the pinned
 * `FLAWCHESS_BOT_CONCURRENCY` since 168.5-04 Task 2 (there is no override
 * knob for those two — they are not parameters `playGame` accepts). The old
 * `DETERMINISM_MAX_NODES=20` override (a Plan 02 artifact, back when the D-11
 * budget was still 400 nodes and a full-cost run took ~170s/move) is REMOVED
 * — Plan 04's real-engine measurement (`168.5-04-SUMMARY.md`) found the
 * SHIPPED 50-node/stop-rule-gated budget already costs only ~5.4s median/
 * ~12.7s worst-case per move, so there is no longer a reason to run this
 * proof at an artificially reduced budget: SC5 requires proving determinism
 * of the bot that ships, and the real budget is now cheap enough to just use
 * directly (see the imported `FLAWCHESS_BOT_*` constants below).
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
 * engines. Phase 168.5-02 (D-10) fixed this at the root (depth-only `go` +
 * `Clear Hash` per grading/adjudication call, load-independent by
 * construction) — this note is kept as history; a recurrence here would be a
 * regression, not an expected flake.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs
 */
import assert from 'node:assert/strict';

import {
  setupHarnessEngines,
  playGame,
  parseAnchorSpec,
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_STOP_RULE,
  FLAWCHESS_BOT_CONCURRENCY,
} from '../calibration-harness.mjs';
import { OPENING_BOOK } from './calibration-openings.mjs';
import { mulberry32 } from '@/lib/engine/botSampling';

const DETERMINISM_SEED = 42;
const DETERMINISM_ELO = 1500;
const DETERMINISM_BLEND = 1; // full-Stockfish argmax — the deterministic regime this check must prove reproducible
const DETERMINISM_BOT_IS_WHITE = true;

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
    // No maxNodes/maxPlies override (Phase 168.5-05 SC5 re-budget, see module
    // doc comment) — defaults to FLAWCHESS_BOT_MAX_NODES/_MAX_PLIES, the
    // ACTUAL shipped bot budget; stopRule/concurrency are already always
    // FLAWCHESS_BOT_STOP_RULE/_CONCURRENCY inside playGame unconditionally.
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
    // Same rationale as gameRng1's call above.
  });

  assert.deepEqual(
    result2.moveUcis,
    result1.moveUcis,
    'same --seed must reproduce a byte-identical blend=1 game (D-09)',
  );

  console.log(
    `PASS: calibration determinism — same seed reproduced an identical ${result1.moveUcis.length}-ply blend=1 game ` +
      `(result=${result1.result}, reason=${result1.reason}, stockfish-procs=${DETERMINISM_STOCKFISH_PROCS}, ` +
      `budget: FLAWCHESS_BOT_MAX_NODES=${FLAWCHESS_BOT_MAX_NODES} FLAWCHESS_BOT_MAX_PLIES=${FLAWCHESS_BOT_MAX_PLIES} ` +
      `FLAWCHESS_BOT_CONCURRENCY=${FLAWCHESS_BOT_CONCURRENCY} FLAWCHESS_BOT_STOP_RULE=${JSON.stringify(FLAWCHESS_BOT_STOP_RULE)})`,
  );
} finally {
  pool.quitAll();
}

process.exit(0);

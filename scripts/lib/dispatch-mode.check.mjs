#!/usr/bin/env node
/**
 * dispatch-mode.check.mjs — Phase 227 D-14 probe check: the harness dispatch-mode
 * flag is a code-path switch, not a label (the Phase 198 failure mode).
 *
 * Flags: `--mode round|continuous` (default round).
 *   --mode round:       exit 0 iff the real mctsSearch observably ran the round loop.
 *   --mode continuous:  exit 0 iff it observably ran continuous dispatch; if the
 *                       continuous loop were missing (as before Plan 227-10) the probe
 *                       would observe round, print CONTINUOUS-NOT-IMPLEMENTED and exit 3.
 * Output line: `DISPATCH-PROBE <requested> -> <observed>`.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/dispatch-mode.check.mjs [--mode round|continuous]
 */
import assert from 'node:assert/strict';

import { FLAWCHESS_DISPATCH_MODE } from '@/lib/engine/botBudget';
import { mctsSearch } from '@/lib/engine/mctsSearch';

import {
  DISPATCH_MODES,
  DISPATCH_MODE_NOT_LIVE_EXIT,
  DISPATCH_MODE_NOT_LIVE_MESSAGE,
  assertDispatchModeLive,
  defaultDispatchMode,
  parseDispatchModeFlag,
  probeDispatchMode,
} from './dispatch-mode.mjs';

/** Exit code for any check failure other than the expected continuous-not-live outcome. */
const CHECK_FAILURE_EXIT = 1;

/** Read `--mode <value>` from argv (default round); an invalid value throws via parseDispatchModeFlag. */
function requestedModeFromArgv(argv) {
  const idx = argv.indexOf('--mode');
  if (idx === -1) return 'round';
  return parseDispatchModeFlag(argv[idx + 1] ?? '');
}

/** Structural assertions that do not need the engine. */
function assertFlagContract() {
  assert.deepEqual([...DISPATCH_MODES], ['round', 'continuous']);
  assert.equal(defaultDispatchMode(), FLAWCHESS_DISPATCH_MODE, 'default must be the shared app constant');
  assert.throws(() => parseDispatchModeFlag('Round'), /Invalid dispatch mode/);
  assert.throws(() => parseDispatchModeFlag(''), /Invalid dispatch mode/);
  assert.equal(parseDispatchModeFlag('round'), 'round');
  assert.equal(parseDispatchModeFlag('continuous'), 'continuous');
}

/**
 * Synthetic searches that dispatch the two ways by construction, so the probe's
 * `'continuous'` verdict is exercised today (the real continuous loop lands in
 * Plan 227-10). Each asks for the root grade, then fans out two child grades.
 */
function syntheticSearch(continuous) {
  return async (fen, budget, providers) => {
    await providers.grade(fen, ['a'], undefined, 0); // root
    const inFlight = [providers.grade(fen, ['b'], undefined, 0), providers.grade(fen, ['c'], undefined, 0)];
    if (continuous) {
      // Dispatch the next expansion as soon as ANY in-flight grade settles.
      await Promise.race(inFlight);
      await providers.grade(fen, ['d'], undefined, 0);
    } else {
      await Promise.all(inFlight); // barrier: nothing new until the whole round settled
      await providers.grade(fen, ['d'], undefined, 0);
    }
    await Promise.all(inFlight);
  };
}

async function assertProbeDistinguishesModes() {
  assert.equal(await probeDispatchMode(syntheticSearch(false), 'round'), 'round');
  assert.equal(await probeDispatchMode(syntheticSearch(true), 'continuous'), 'continuous');
  await assert.rejects(
    () => assertDispatchModeLive(syntheticSearch(true), 'round'),
    (err) => err.exitCode === 1,
  );
}

async function main() {
  const requested = requestedModeFromArgv(process.argv.slice(2));
  assertFlagContract();
  await assertProbeDistinguishesModes();
  const first = await probeDispatchMode(mctsSearch, requested);
  const second = await probeDispatchMode(mctsSearch, requested);
  assert.equal(first, second, 'the probe must give the same answer on repeat');
  console.log(`DISPATCH-PROBE ${requested} -> ${first}`);
  if (requested === first) return 0;
  if (requested === 'continuous') {
    console.log(DISPATCH_MODE_NOT_LIVE_MESSAGE);
    console.log('CONTINUOUS-NOT-IMPLEMENTED');
    return DISPATCH_MODE_NOT_LIVE_EXIT;
  }
  return CHECK_FAILURE_EXIT;
}

main().then(
  (code) => process.exit(code),
  (err) => {
    console.error(err instanceof Error ? err.message : err);
    process.exit(typeof err?.exitCode === 'number' ? err.exitCode : CHECK_FAILURE_EXIT);
  },
);

#!/usr/bin/env node
/**
 * calibration-pruning.check.mjs — D-15 anchor-pruning skip-log + --resume
 * round-trip assertion (Phase 168.5, Plan 05, Task 2).
 *
 * Unlike `calibration-determinism.check.mjs`, this is a STRUCTURAL check of
 * the TSV schema + `loadPriorSweep`'s guard logic against a small
 * SYNTHESIZED fixture — no real engines, no game-playing. It verifies:
 *
 *   (a) every `gridKey` has a row, and every pruned (`games=0`) row carries
 *       a non-empty `skip_reason` — D-15's "no silent coverage gaps"
 *       requirement (168.5-RESEARCH.md Pitfall 4).
 *   (b) feeding that fixture TSV back through `calibration-harness.mjs`'s
 *       exported `loadPriorSweep`, with the SAME grid + budget, does NOT
 *       throw the "not in the current grid" / games-count-mismatch /
 *       budget-mismatch guards — a D-15-pruned run still round-trips
 *       through `--resume` (the grid-membership invariant survives
 *       pruning).
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-pruning.check.mjs
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import {
  mainTsvColumns,
  mainTsvRowLine,
  newCellTally,
  isUnanimousWin,
  isUnanimousLoss,
  cellKey,
  loadPriorSweep,
  parseAnchorSpec,
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  SKIP_REASON_OUT_OF_WINDOW,
  SKIP_REASON_LOST_CUTOFF,
  SKIP_REASON_WON_CUTOFF,
} from '../calibration-harness.mjs';

const FIXTURE_SEED = 7;
const FIXTURE_GAMES_PER_CELL = 2;
const FIXTURE_STOCKFISH_PROCS = 4;
const FIXTURE_BOT_ELO = 1500;
const FIXTURE_BOT_BLEND = 1;
const FIXTURE_GIT_SHA = 'fixturesha';

/** One PLAYED cell's row (games=FIXTURE_GAMES_PER_CELL, skip_reason=''). */
function playedRow(anchorLabel) {
  const tally = newCellTally();
  tally.games = FIXTURE_GAMES_PER_CELL;
  tally.wins = 1;
  tally.draws = 1;
  tally.white = { games: 1, wins: 1, draws: 0, losses: 0 };
  tally.black = { games: 1, wins: 0, draws: 1, losses: 0 };
  return {
    botElo: FIXTURE_BOT_ELO,
    botBlend: FIXTURE_BOT_BLEND,
    anchor: anchorLabel,
    anchorSpec: parseAnchorSpec(anchorLabel),
    tally,
    seed: FIXTURE_SEED,
    maxNodes: FLAWCHESS_BOT_MAX_NODES,
    maxPlies: FLAWCHESS_BOT_MAX_PLIES,
    stockfishProcs: FIXTURE_STOCKFISH_PROCS,
    gitSha: FIXTURE_GIT_SHA,
    skipReason: '',
  };
}

/** One SKIPPED (pruned) cell's row (games=0, skip_reason populated — D-15 Pitfall 4). */
function skippedRow(anchorLabel, skipReason) {
  return {
    botElo: FIXTURE_BOT_ELO,
    botBlend: FIXTURE_BOT_BLEND,
    anchor: anchorLabel,
    anchorSpec: parseAnchorSpec(anchorLabel),
    tally: newCellTally(),
    seed: FIXTURE_SEED,
    maxNodes: FLAWCHESS_BOT_MAX_NODES,
    maxPlies: FLAWCHESS_BOT_MAX_PLIES,
    stockfishProcs: FIXTURE_STOCKFISH_PROCS,
    gitSha: FIXTURE_GIT_SHA,
    skipReason,
  };
}

// --- unanimity cutoff trigger: only an all-win / all-loss cell is decided ---
// A single draw or loss must NOT trip a cutoff (the "won_cutoff/lost_cutoff
// but no results" bug: a 9W/1D near-sweep used to prune its neighbour to
// games=0 instead of playing it out).
function tallyOf(games, wins, draws, losses) {
  const tally = newCellTally();
  Object.assign(tally, { games, wins, draws, losses });
  return tally;
}
assert.equal(isUnanimousWin(tallyOf(10, 10, 0, 0)), true, 'all-win (10W) is a unanimous win');
assert.equal(isUnanimousWin(tallyOf(10, 9, 1, 0)), false, '9W/1D (near-sweep) is NOT a unanimous win');
assert.equal(isUnanimousWin(tallyOf(0, 0, 0, 0)), false, 'empty tally is never a unanimous win');
assert.equal(isUnanimousLoss(tallyOf(10, 0, 0, 10)), true, 'all-loss (10L) is a unanimous loss');
assert.equal(isUnanimousLoss(tallyOf(10, 0, 1, 9)), false, '9L/1D (near-shutout) is NOT a unanimous loss');
assert.equal(isUnanimousLoss(tallyOf(0, 0, 0, 0)), false, 'empty tally is never a unanimous loss');
console.log('PASS: unanimity cutoff trigger — only all-win / all-loss cells are decided (draws/splits play out)');

// The fixture cell's anchor AXIS, declared independently of `fixtureRows`
// — `gridKeys` is derived from THIS list (mirroring how the real sweep
// builds its grid from CLI axes, never from emitted rows), so the coverage
// assertion below is a genuine two-set comparison. Deriving gridKeys from
// fixtureRows made the membership assertion tautological (unfalsifiable).
const FIXTURE_ANCHORS = ['maia1500', 'sf5', 'maia2500', 'maia700'];

// A small (botElo=1500, botBlend=1) bot-cell's anchor grid: one anchor
// actually played, and one skip per D-15 mechanism/direction — mirrors the
// three skip_reason markers the real sweep loop can emit.
const fixtureRows = [
  playedRow('maia1500'), // in-window, played
  skippedRow('sf5', SKIP_REASON_OUT_OF_WINDOW), // mechanism 1: static bracketing
  skippedRow('maia2500', SKIP_REASON_LOST_CUTOFF), // mechanism 2: stronger-side cutoff
  skippedRow('maia700', SKIP_REASON_WON_CUTOFF), // mechanism 2: weaker-side cutoff
];

const gridKeys = new Set(FIXTURE_ANCHORS.map((anchor) => cellKey(FIXTURE_BOT_ELO, FIXTURE_BOT_BLEND, anchor)));

// --- (a) rows cover gridKeys EXACTLY (both directions); every games=0 row has a non-empty skip_reason ---
const rowKeys = new Set(fixtureRows.map((row) => cellKey(row.botElo, row.botBlend, row.anchor)));
assert.equal(rowKeys.size, fixtureRows.length, 'fixture rows must have unique cell keys');
for (const key of gridKeys) {
  assert.ok(rowKeys.has(key), `gridKey ${key} has no fixture row (silent coverage gap — D-15 Pitfall 4)`);
}
for (const key of rowKeys) {
  assert.ok(gridKeys.has(key), `fixture row ${key} is not a member of gridKeys`);
}
for (const row of fixtureRows) {
  const key = cellKey(row.botElo, row.botBlend, row.anchor);
  if (row.tally.games === 0) {
    assert.ok(
      row.skipReason.length > 0,
      `pruned row ${key} (games=0) must carry a non-empty skip_reason (D-15 no silent coverage gaps)`,
    );
  } else {
    assert.equal(row.skipReason, '', `played row ${key} must have an EMPTY skip_reason`);
  }
}
console.log(
  `PASS: skip_reason coverage — rows cover the axis-derived gridKeys exactly (${rowKeys.size}/${gridKeys.size}), every pruned row logged ` +
    `(${fixtureRows.filter((row) => row.skipReason).length} pruned, ${fixtureRows.filter((row) => !row.skipReason).length} played)`,
);

// --- write the fixture to a real on-disk TSV (mirrors a real sweep's shape) ---
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'calibration-pruning-check-'));
const fixturePath = path.join(tmpDir, 'fixture.tsv');
try {
  const lines = [mainTsvColumns().join('\t'), ...fixtureRows.map((row) => mainTsvRowLine(row))];
  fs.writeFileSync(fixturePath, `${lines.join('\n')}\n`, 'utf8');

  // --- (b) loadPriorSweep must accept the pruned TSV without throwing (Pitfall 4) ---
  const args = { gamesPerCell: FIXTURE_GAMES_PER_CELL, seed: FIXTURE_SEED };
  let result;
  assert.doesNotThrow(() => {
    result = loadPriorSweep(fixturePath, args, gridKeys);
  }, '--resume must round-trip a D-15-pruned TSV without a grid-membership/budget-mismatch error');

  assert.equal(
    result.completedKeys.size,
    gridKeys.size,
    'every gridKey (played AND pruned) must be marked complete on reload',
  );
  for (const row of fixtureRows) {
    const key = cellKey(row.botElo, row.botBlend, row.anchor);
    const reloaded = result.rowByKey.get(key);
    assert.ok(reloaded, `reloaded row missing for ${key}`);
    assert.equal(reloaded.tally.games, row.tally.games, `reloaded games mismatch for ${key}`);
    assert.equal(reloaded.skipReason, row.skipReason, `reloaded skip_reason mismatch for ${key}`);
  }

  console.log(
    `PASS: --resume round-trip — a D-15-pruned fixture TSV (${fixtureRows.length} rows, ` +
      `${fixtureRows.filter((row) => row.skipReason).length} pruned) reloaded via loadPriorSweep ` +
      'without a grid-membership/budget-mismatch error',
  );
} finally {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}

process.exit(0);

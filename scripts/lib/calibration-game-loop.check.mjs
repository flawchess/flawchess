#!/usr/bin/env node
/**
 * calibration-game-loop.check.mjs — structural check that the extracted
 * mover-agnostic two-mover game loop (Phase 173, Plan 01, D-08) produces
 * correct WHITE-POV color-keyed terminal/adjudication decisions. No real
 * engines — SYNTHESIZED deterministic in-memory movers and a stub pool,
 * mirroring `calibration-pruning.check.mjs`'s structural-fixture style.
 *
 * Covers three canned games:
 *   (a) a scripted white checkmate (Fool's-mate-shaped) -> `black_win`
 *   (b) a scripted stalemate -> `draw`
 *   (c) a scripted sequence where the stub pool's eval stays past
 *       `ADJUDICATION_CP_THRESHOLD` for `ADJUDICATION_SUSTAIN_PLIES`
 *       consecutive plies -> an `adjudicated_eval` cutoff, favoring the
 *       side the stub eval sign indicates, BEFORE any real terminal state.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-game-loop.check.mjs
 */
import assert from 'node:assert/strict';

import { playTwoMoverGame } from './calibration-game-loop.mjs';
import { resolveFrontendModule } from './node-engine-providers.mjs';
import { ADJUDICATION_SUSTAIN_PLIES, ADJUDICATION_CP_THRESHOLD } from '../calibration-harness.mjs';

const { Chess } = await resolveFrontendModule('chess.js');

/** A stub pool whose newGameAll/evalPosition are no-ops except for a caller-supplied fixed white-POV cp. */
function makeStubPool(fixedWhitePovCp = 0) {
  return {
    async newGameAll() {},
    async evalPosition() {
      return fixedWhitePovCp;
    },
  };
}

/** A deterministic scripted mover: replays a fixed UCI sequence, one move per call. */
function scriptedMover(uciScript) {
  let i = 0;
  return async () => {
    const uci = uciScript[i];
    assert.ok(uci !== undefined, `scriptedMover exhausted its script at call ${i}`);
    i++;
    return uci;
  };
}

// ─── (a) Fool's-mate-shaped scripted checkmate: white is checkmated -> black_win ──
// 1. f3 e5 2. g4 Qh4# (white's own moves are dumb enough to get mated;
// black delivers checkmate on move 2, so the checkmated side is WHITE).

async function playScriptedGame(whiteUcis, blackUcis, { pool = makeStubPool(0), maxPlies } = {}) {
  const chess = new Chess();
  const moverWhite = scriptedMover(whiteUcis);
  const moverBlack = scriptedMover(blackUcis);
  return playTwoMoverGame({
    Chess,
    pool,
    moverWhite,
    moverBlack,
    startFen: chess.fen(),
    gameRng: () => 0,
    maxPlies,
  });
}

const foolsMate = await playScriptedGame(['f2f3', 'g2g4'], ['e7e5', 'd8h4']);
assert.equal(foolsMate.result, 'black_win', `Fool's-mate-shaped checkmate must be black_win, got ${foolsMate.result}`);
assert.equal(foolsMate.reason, 'checkmate', `Fool's-mate-shaped result reason must be checkmate, got ${foolsMate.reason}`);
assert.equal(foolsMate.plies, 4, `Fool's-mate-shaped game must be exactly 4 plies, got ${foolsMate.plies}`);
assert.deepEqual(
  foolsMate.moveUcis,
  ['f2f3', 'e7e5', 'g2g4', 'd8h4'],
  `Fool's-mate-shaped moveUcis must interleave white/black in play order, got ${JSON.stringify(foolsMate.moveUcis)}`,
);
console.log('PASS: scripted checkmate (white checkmated) -> black_win, reason=checkmate, plies=4');

// ─── (b) Scripted stalemate: a well-known minimal stalemate position, reached by moves ──
// Fastest known stalemate is 10 plies (e.g. 1. e3 a5 2. Qh5 Ra6 3. Qxa5 h5
// 4. Qxc7 Rah6 5. h4 f6 6. Qxd7+ Kf7 7. Qxb7 Qd3 8. Qxb8 Qh7 9. Qxc8 Kg6
// 10. Qe6). We use that exact canonical 10-ply sequence.
const stalemateWhite = ['e2e3', 'd1h5', 'h5a5', 'a5c7', 'h2h4', 'c7d7', 'd7b7', 'b7b8', 'b8c8', 'c8e6'];
const stalemateBlack = ['a7a5', 'a8a6', 'h7h5', 'a6h6', 'f7f6', 'e8f7', 'd8d3', 'd3h7', 'f7g6'];
const stalemate = await playScriptedGame(stalemateWhite, stalemateBlack);
assert.equal(stalemate.result, 'draw', `canonical fastest-stalemate script must be draw, got ${stalemate.result}`);
assert.equal(stalemate.reason, 'stalemate', `canonical fastest-stalemate reason must be stalemate, got ${stalemate.reason}`);
assert.equal(stalemate.plies, 19, `canonical fastest-stalemate script must be exactly 19 plies, got ${stalemate.plies}`);
console.log('PASS: scripted stalemate (canonical fastest-stalemate line) -> draw, reason=stalemate, plies=19');

// ─── (c) Adjudication cutoff: stub eval stays past threshold for ADJUDICATION_SUSTAIN_PLIES ──
// Both movers play harmless legal shuffling moves (knight out-and-back) so
// the game never hits a REAL terminal state — only the stub pool's fixed
// eval (held above ADJUDICATION_CP_THRESHOLD for every ply) can end it.
{
  const shuffleWhite = [];
  const shuffleBlack = [];
  for (let i = 0; i < ADJUDICATION_SUSTAIN_PLIES + 2; i++) {
    shuffleWhite.push(i % 2 === 0 ? 'g1f3' : 'f3g1');
    shuffleBlack.push(i % 2 === 0 ? 'g8f6' : 'f6g8');
  }
  const decisiveWhitePovCp = ADJUDICATION_CP_THRESHOLD + 100; // sustained favoring WHITE
  const adjudicated = await playScriptedGame(shuffleWhite, shuffleBlack, {
    pool: makeStubPool(decisiveWhitePovCp),
  });
  assert.equal(
    adjudicated.result,
    'white_win',
    `a sustained-past-threshold white-favoring eval must adjudicate white_win, got ${adjudicated.result}`,
  );
  assert.equal(
    adjudicated.reason,
    'adjudicated_eval',
    `adjudication cutoff reason must be adjudicated_eval, got ${adjudicated.reason}`,
  );
  assert.equal(
    adjudicated.plies,
    ADJUDICATION_SUSTAIN_PLIES,
    `adjudication must trigger at exactly ADJUDICATION_SUSTAIN_PLIES (${ADJUDICATION_SUSTAIN_PLIES}) plies, got ${adjudicated.plies}`,
  );
  console.log(
    `PASS: adjudication cutoff — sustained eval past threshold for ${ADJUDICATION_SUSTAIN_PLIES} plies -> ` +
      `white_win, reason=adjudicated_eval, plies=${adjudicated.plies}`,
  );
}

process.exit(0);

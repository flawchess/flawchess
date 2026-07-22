#!/usr/bin/env node
/**
 * calibration-near-free-metrics.check.mjs — pure-logic assertion for the
 * Phase-180 near-free metric accumulator (SEED-102): draw rate, mean game
 * length, ACPL, blunder rate, SF-agreement, Maia-agreement. No real engines and
 * no filesystem — the metric math is fed a FABRICATED deterministic eval/policy
 * fixture (a canned white-POV cp sequence + canned bestmove / Maia-argmax UCIs),
 * exactly the `onPly` extension the harness drives with real engine output.
 * Mirrors `calibration-anchor-schedule.check.mjs`'s canned-fixture style.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-near-free-metrics.check.mjs
 */
import assert from 'node:assert/strict';
import {
  newNearFreeGameStats,
  recordBotMoveEval,
  recordBotMoveSfAgreement,
  recordBotMoveMaiaAgreement,
  newNearFreeCellStats,
  foldNearFreeGame,
  finalizeNearFreeMetrics,
} from '../calibration-harness.mjs';

// ─── Fabricated single game: bot is WHITE, three of its moves scored ─────────
// A canned white-POV cp sequence (before → after each bot move) plus canned
// bestmove / Maia-argmax UCIs — no real Maia/Stockfish is ever consulted.

const gameA = newNearFreeGameStats();

// move 1: +50 → +40 : cpLoss 10, tiny ES drop → NOT a blunder
recordBotMoveEval(gameA, { evalBeforeWhiteCp: 50, evalAfterWhiteCp: 40, botIsWhite: true });
// move 2: +300 → -290 : cpLoss 590, huge ES drop → blunder
recordBotMoveEval(gameA, { evalBeforeWhiteCp: 300, evalAfterWhiteCp: -290, botIsWhite: true });
// move 3: -40 → -40 : cpLoss clamped to 0 (no worsening), NOT a blunder
recordBotMoveEval(gameA, { evalBeforeWhiteCp: -40, evalAfterWhiteCp: -40, botIsWhite: true });
// a null-eval move (ply-1 pre-move eval / terminal post-move eval) must be skipped
recordBotMoveEval(gameA, { evalBeforeWhiteCp: null, evalAfterWhiteCp: 20, botIsWhite: true });
recordBotMoveEval(gameA, { evalBeforeWhiteCp: 20, evalAfterWhiteCp: null, botIsWhite: true });

assert.equal(gameA.botEvalCount, 3, `only the 3 fully-evaluated bot moves count, got ${gameA.botEvalCount}`);
assert.equal(gameA.cpLossSum, 600, `cpLossSum must be 10 + 590 + 0 = 600, got ${gameA.cpLossSum}`);
assert.equal(gameA.blunderCount, 1, `exactly the +300→-290 move is a blunder, got ${gameA.blunderCount}`);
console.log('PASS: recordBotMoveEval — cpLoss clamps at 0, null evals skipped, ES-drop blunder graded via liveFlaw');

// SF-agreement: bot move vs the pre-move adjudication bestmove (null = ply 1, skipped)
recordBotMoveSfAgreement(gameA, { botUci: 'e2e4', preMoveBestUci: 'e2e4' }); // match
recordBotMoveSfAgreement(gameA, { botUci: 'g1f3', preMoveBestUci: 'b1c3' }); // miss
recordBotMoveSfAgreement(gameA, { botUci: 'd2d4', preMoveBestUci: null }); // ply 1 — not comparable
recordBotMoveSfAgreement(gameA, { botUci: 'e2e4', preMoveBestUci: 'e2e4' }); // match
assert.equal(gameA.sfComparable, 3, `null pre-move best is not comparable, got ${gameA.sfComparable}`);
assert.equal(gameA.sfAgree, 2, `2 of 3 comparable bot moves matched Stockfish, got ${gameA.sfAgree}`);
console.log('PASS: recordBotMoveSfAgreement — counts matches only over comparable bot moves');

// Maia-agreement: bot move vs raw-Maia argmax at the bot's own ELO
recordBotMoveMaiaAgreement(gameA, { botUci: 'e2e4', maiaArgmaxUci: 'e2e4' }); // match
recordBotMoveMaiaAgreement(gameA, { botUci: 'g1f3', maiaArgmaxUci: 'g1f3' }); // match
recordBotMoveMaiaAgreement(gameA, { botUci: 'd2d4', maiaArgmaxUci: 'd2d3' }); // miss
assert.equal(gameA.maiaComparable, 3, `every bot move has a Maia argmax, got ${gameA.maiaComparable}`);
assert.equal(gameA.maiaAgree, 2, `2 of 3 bot moves matched Maia argmax, got ${gameA.maiaAgree}`);
console.log('PASS: recordBotMoveMaiaAgreement — counts matches over every bot move');

// ─── Cell-level aggregation across two games → the six finalized metrics ─────
// gameA (40 plies, a DRAW) carries all the scored moves; gameB (60 plies, a
// decisive game) contributes only to draw rate + mean game length.
const gameB = newNearFreeGameStats();

const cell = newNearFreeCellStats();
foldNearFreeGame(cell, gameA, 40);
foldNearFreeGame(cell, gameB, 60);

const metrics = finalizeNearFreeMetrics(cell, { games: 2, draws: 1 });
assert.equal(metrics.drawRate, 0.5, `draw rate = 1/2 draws, got ${metrics.drawRate}`);
assert.equal(metrics.meanGameLength, 50, `mean game length = (40+60)/2, got ${metrics.meanGameLength}`);
assert.equal(metrics.acpl, 200, `ACPL = 600 cpLoss / 3 bot moves, got ${metrics.acpl}`);
assert.ok(Math.abs(metrics.blunderRate - 1 / 3) < 1e-12, `blunder rate = 1/3, got ${metrics.blunderRate}`);
assert.ok(Math.abs(metrics.sfAgreement - 2 / 3) < 1e-12, `SF-agreement = 2/3, got ${metrics.sfAgreement}`);
assert.ok(Math.abs(metrics.maiaAgreement - 2 / 3) < 1e-12, `Maia-agreement = 2/3, got ${metrics.maiaAgreement}`);
console.log('PASS: finalizeNearFreeMetrics — all six metrics aggregate correctly across games');

// ─── Empty cell: every metric is null (empty denominator, never a misleading 0) ──
const emptyMetrics = finalizeNearFreeMetrics(newNearFreeCellStats(), { games: 0, draws: 0 });
for (const [name, value] of Object.entries(emptyMetrics)) {
  assert.equal(value, null, `empty-cell ${name} must be null (0 denominator), got ${value}`);
}
console.log('PASS: finalizeNearFreeMetrics — empty cell yields null (empty) metrics, not 0');

console.log('PASS: calibration-near-free-metrics — six near-free metrics correct on fabricated eval/policy fixtures');
process.exit(0);

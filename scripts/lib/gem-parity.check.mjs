#!/usr/bin/env node
/**
 * gem-parity.check.mjs — Wave 0 gem-logic parity assertion (Phase 165 Task 1).
 *
 * Imports the REAL `classifyGem`/`summarizeForGem` (from `@/lib/gemMove`),
 * `evalToExpectedScore`/`sideToMoveFromFen` (from `@/lib/liveFlaw`), and the
 * generated `MISTAKE_DROP` (from `@/generated/flawThresholds`) THROUGH the
 * `@/` alias resolve hook — never re-derived (D-03 zero-drift). Asserts the
 * imported gem pipeline reproduces hand-derived classifyGem booleans for a
 * fixed fixture, catching wiring bugs (white-POV sign, SAN canonicalization)
 * before any real calibration run.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/gem-parity.check.mjs
 */
import assert from 'node:assert/strict';
import { classifyGem, summarizeForGem, GEM_MAIA_MAX_PROB } from '@/lib/gemMove';
import { evalToExpectedScore, sideToMoveFromFen } from '@/lib/liveFlaw';
import { MISTAKE_DROP } from '@/generated/flawThresholds';

// Tolerance for floating-point expected-score comparisons (sigmoid output).
const ES_TOLERANCE = 1e-9;

function assertClose(actual, expected, message) {
  assert.ok(
    Math.abs(actual - expected) < ES_TOLERANCE,
    `${message} (actual=${actual}, expected=${expected})`,
  );
}

// ─── Zero-drift tripwire: the module's own contract, not a re-derived literal ──

assert.equal(MISTAKE_DROP, 0.1, 'MISTAKE_DROP must equal the documented 0.1 gap contract');

// ─── Fixture: a mid-game white-to-move FEN with a clearly-best move ────────────

const FIXTURE_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

assert.equal(
  sideToMoveFromFen(FIXTURE_FEN),
  'white',
  'sideToMoveFromFen must read "white" from a "w" FEN side-to-move field',
);
assert.equal(
  sideToMoveFromFen(FIXTURE_FEN.replace(' w ', ' b ')),
  'black',
  'sideToMoveFromFen must read "black" from a "b" FEN side-to-move field',
);

const mover = sideToMoveFromFen(FIXTURE_FEN);

// Hand-derived white-POV grades: 'e4' is decisively best (+500cp), 'd4' is the
// runner-up (-500cp) — the expected-score gap comfortably exceeds MISTAKE_DROP.
const gradeBySan = new Map([
  ['e4', { evalCp: 500, evalMate: null }],
  ['d4', { evalCp: -500, evalMate: null }],
  ['Nf3', { evalCp: null, evalMate: null }], // ungraded entry — must be skipped (163-REVIEW WR-02)
]);

const expectedBestEs = evalToExpectedScore(500, null, mover);
const expectedSecondBestEs = evalToExpectedScore(-500, null, mover);
assert.ok(
  expectedBestEs - expectedSecondBestEs >= MISTAKE_DROP,
  'fixture gap must exceed MISTAKE_DROP for this parity check to be meaningful',
);

const summary = summarizeForGem(gradeBySan, mover);
assert.equal(summary.bestSan, 'e4', 'summarizeForGem must pick the higher-ES move as bestSan');
assertClose(summary.bestEs, expectedBestEs, 'summarizeForGem bestEs must match the hand-derived sigmoid value');
assertClose(
  summary.secondBestEs,
  expectedSecondBestEs,
  'summarizeForGem secondBestEs must match the hand-derived sigmoid value (ungraded Nf3 skipped)',
);

const playedIsBest = summary.bestSan === 'e4';

// ─── classifyGem: C1 (Maia prob <= ceiling) AND C2 (best + gap) ────────────────

assert.equal(
  classifyGem({
    maiaProbability: 0.05,
    playedIsBest,
    bestEs: summary.bestEs,
    secondBestEs: summary.secondBestEs,
  }),
  true,
  'classifyGem must return true when maiaProbability <= GEM_MAIA_MAX_PROB, playedIsBest, and the ES gap clears MISTAKE_DROP',
);

assert.equal(
  classifyGem({
    maiaProbability: 0.5,
    playedIsBest,
    bestEs: summary.bestEs,
    secondBestEs: summary.secondBestEs,
  }),
  false,
  'classifyGem must return false when maiaProbability exceeds GEM_MAIA_MAX_PROB',
);

assert.equal(
  classifyGem({
    maiaProbability: 0.05,
    playedIsBest: false,
    bestEs: summary.bestEs,
    secondBestEs: summary.secondBestEs,
  }),
  false,
  'classifyGem must return false when the played move is not the graded best',
);

assert.equal(
  classifyGem({
    maiaProbability: 0.05,
    playedIsBest: true,
    bestEs: 0.55,
    secondBestEs: 0.5, // gap of 0.05 < MISTAKE_DROP (0.1)
  }),
  false,
  'classifyGem must return false when the best/second-best ES gap is below MISTAKE_DROP',
);

// Sanity check on the ceiling constant itself — a future edit changing this
// away from a flat cutoff (D-08 ELO-scaled ceiling) must not silently pass.
assert.equal(GEM_MAIA_MAX_PROB, 0.1, 'GEM_MAIA_MAX_PROB must remain the flat v1 ceiling (D-08 deferred)');

console.log('PASS: gem-parity check — imported classifyGem/summarizeForGem/evalToExpectedScore reproduce hand-derived fixture results.');
process.exit(0);

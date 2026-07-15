#!/usr/bin/env node
/**
 * calibration-elo.check.mjs — pure-math assertion for the D-05 anchor-logistic
 * ELO inversion (Phase 168, Plan 03, Task 3). No engines/network — mirrors
 * `gem-parity.check.mjs`'s canned-fixture assertion style.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-elo.check.mjs
 */
import assert from 'node:assert/strict';
import { invertAnchorElo, combineAnchorEstimates } from './calibration-elo.mjs';

/** log10(1/0.5 - 1) === log10(1) === 0, so a 50% score must invert to EXACTLY the anchor rating (modulo fp noise). */
const TOLERANCE_ELO = 1e-6;

// ─── invertAnchorElo(0.5, R, games) ~= R — a 50% score means "same strength" ───

const estimateAtHalf = invertAnchorElo(0.5, 1500, 20);
assert.ok(
  Math.abs(estimateAtHalf - 1500) < TOLERANCE_ELO,
  `invertAnchorElo(0.5, 1500, 20) must be ~1500 (same strength as the anchor), got ${estimateAtHalf}`,
);

// ─── Pitfall 4: a 0/N or N/N observed score must clamp to a FINITE estimate ────

const estimateAtZero = invertAnchorElo(0, 1500, 20);
assert.ok(
  Number.isFinite(estimateAtZero),
  `invertAnchorElo(0, 1500, 20) (a shutout loss) must clamp to a finite estimate, got ${estimateAtZero}`,
);

const estimateAtOne = invertAnchorElo(1, 1500, 20);
assert.ok(
  Number.isFinite(estimateAtOne),
  `invertAnchorElo(1, 1500, 20) (a shutout win) must clamp to a finite estimate, got ${estimateAtOne}`,
);
assert.ok(
  estimateAtOne > estimateAtZero,
  `a shutout WIN must invert to a HIGHER estimate than a shutout LOSS (got ${estimateAtOne} <= ${estimateAtZero})`,
);

// ─── combineAnchorEstimates: finite for a mixed synthetic anchor set, null for none ─

const combined = combineAnchorEstimates([
  { score: 0.9, games: 20, anchorRating: 1100 },
  { score: 0.5, games: 20, anchorRating: 1500 },
  { score: 0.1, games: 20, anchorRating: 1900 },
]);
assert.ok(Number.isFinite(combined), `combineAnchorEstimates must return a finite estimate for a mixed anchor set, got ${combined}`);

assert.equal(
  combineAnchorEstimates([]),
  null,
  'combineAnchorEstimates must return null when there is nothing to combine (empty anchor set)',
);

console.log(
  'PASS: calibration-elo — invertAnchorElo/combineAnchorEstimates finite and correctly signed for canned inputs',
);
process.exit(0);

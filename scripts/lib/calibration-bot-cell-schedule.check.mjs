#!/usr/bin/env node
/**
 * calibration-bot-cell-schedule.check.mjs — pure-logic assertion for the
 * bot-cell two-pass scheduler (Phase 180, Plan 01, D-07 / D-02a). No
 * engines/network — mirrors `calibration-anchor-schedule.check.mjs`'s
 * canned-fixture assertion style. Every fixture is fabricated; the module
 * under test performs no engine, filesystem, or network access.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-bot-cell-schedule.check.mjs
 */
import assert from 'node:assert/strict';
import {
  internalRatingFor,
  pickLocateAnchors,
  locateEstimate,
  selectMeasureBracket,
  bracketBeyondLadder,
  DEFAULT_BRACKET_SIZE,
  MIN_BRACKET_PER_FAMILY,
} from './calibration-bot-cell-schedule.mjs';

// ─── Fabricated anchor-spec fixtures (D-02a: no real Maia/Stockfish) ───────

function maiaSpec(rungElo) {
  return { kind: 'maia', label: `maia${rungElo}`, rungElo };
}
function sfSpec(skillLevel) {
  return { kind: 'sf', label: `sf${skillLevel}`, skillLevel };
}

const TEN_ANCHOR_SET = [
  maiaSpec(700),
  maiaSpec(1100),
  maiaSpec(1500),
  maiaSpec(1900),
  maiaSpec(2300),
  sfSpec(0),
  sfSpec(3),
  sfSpec(5),
  sfSpec(8),
  sfSpec(10),
];

const isMaia = (spec) => spec.kind === 'maia';
const familyCount = (specs, wantMaia) => specs.filter((s) => isMaia(s) === wantMaia).length;

// Measured internal-scale endpoints (from calibration-internal-scale.mjs).
const SF10_INTERNAL = 1907.93; // ladder ceiling
const MAIA1500_INTERNAL = 1500.0;

// ─── internalRatingFor: correct lookup + fail-loud on unmeasured token ─────

assert.equal(internalRatingFor(maiaSpec(1500)), MAIA1500_INTERNAL, 'maia1500 must resolve to its measured internal rating 1500.00');
assert.throws(
  () => internalRatingFor(maiaSpec(1300)),
  /INTERNAL_RATING/,
  'an unmeasured token (maia1300) must throw fail-loud, never fall back to a nominal rating',
);
console.log('PASS: internalRatingFor — measured lookup correct, throws on an unmeasured token (Pitfall 1)');

// ─── pickLocateAnchors: weakest + strongest by INTERNAL rating ─────────────

const [weakest, strongest] = pickLocateAnchors(TEN_ANCHOR_SET);
assert.equal(weakest.label, 'sf0', 'the weakest locate anchor must be sf0 (lowest internal rating 1069.33)');
assert.equal(strongest.label, 'sf10', 'the strongest locate anchor must be sf10 (highest internal rating 1907.93)');
console.log('PASS: pickLocateAnchors — returns sf0 (weakest) + sf10 (strongest) by internal rating');

// ─── locateEstimate: informative-band anchor drives the estimate ───────────

// sf0 crushed (score 1.0, out of band) must NOT distort the estimate; only the
// in-band sf10 result (score 0.5 → inverts to exactly its internal rating) counts.
const locateResults = [
  { anchorSpec: sfSpec(0), score: 1.0, games: 8 },
  { anchorSpec: sfSpec(10), score: 0.5, games: 8 },
];
const estimate = locateEstimate(locateResults);
assert.ok(
  Math.abs(estimate - SF10_INTERNAL) < 1e-6,
  `an out-of-band locate anchor must be excluded — estimate should be ~${SF10_INTERNAL} (sf10 at 0.5), got ${estimate}`,
);
console.log('PASS: locateEstimate — in-band anchor drives the estimate, out-of-band anchor excluded (D-01 reuse)');

// ─── selectMeasureBracket: nearest-to-estimate + cross-family floor ────────

// Estimate at maia1500's internal rating: the 4 nearest by distance are 3 Maia
// + 1 SF (SF under-represented) — the cross-family floor must swap an SF in.
const rawNearestFour = [...TEN_ANCHOR_SET]
  .sort((a, b) => Math.abs(internalRatingFor(a) - MAIA1500_INTERNAL) - Math.abs(internalRatingFor(b) - MAIA1500_INTERNAL))
  .slice(0, DEFAULT_BRACKET_SIZE);
assert.ok(
  familyCount(rawNearestFour, false) < MIN_BRACKET_PER_FAMILY,
  'precondition: the raw 4-nearest bracket is same-family-skewed (< 2 SF) so the floor is genuinely exercised',
);

const bracket = selectMeasureBracket(TEN_ANCHOR_SET, MAIA1500_INTERNAL);
assert.equal(bracket.length, DEFAULT_BRACKET_SIZE, `bracket must hold exactly ${DEFAULT_BRACKET_SIZE} anchors`);
assert.ok(familyCount(bracket, true) >= MIN_BRACKET_PER_FAMILY, `bracket must keep >= ${MIN_BRACKET_PER_FAMILY} Maia anchors`);
assert.ok(familyCount(bracket, false) >= MIN_BRACKET_PER_FAMILY, `bracket must keep >= ${MIN_BRACKET_PER_FAMILY} SF anchors`);
console.log('PASS: selectMeasureBracket — cross-family floor forces >= 2 Maia AND >= 2 SF even when the 4-nearest were Maia-skewed');

// ─── bracketBeyondLadder: warn-and-flag past a ladder edge ─────────────────

// A cell estimated ABOVE the sf10 ceiling: every bracket anchor is below it.
const overCeilingEstimate = SF10_INTERNAL + 100;
const ceilingBracket = selectMeasureBracket(TEN_ANCHOR_SET, overCeilingEstimate);
assert.equal(
  bracketBeyondLadder(overCeilingEstimate, ceilingBracket),
  true,
  'an estimate above the sf10 ceiling has an all-below bracket → beyond_ladder true (Pitfall 4 warn-and-proceed)',
);
assert.equal(
  bracketBeyondLadder(MAIA1500_INTERNAL, bracket),
  false,
  'an in-range estimate has anchors both above and below → beyond_ladder false',
);
console.log('PASS: bracketBeyondLadder — true past the sf10 ceiling, false for an in-range estimate');

console.log('PASS: calibration-bot-cell-schedule — two-pass scheduler correct on fabricated fixtures');
process.exit(0);

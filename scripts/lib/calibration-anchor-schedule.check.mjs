#!/usr/bin/env node
/**
 * calibration-anchor-schedule.check.mjs — pure-logic assertion for the
 * D-01/D-02/D-04 probe→measure gate + connectivity guard (Phase 173,
 * Plan 02, Task 1). No engines/network — mirrors `calibration-elo.check.mjs`'s
 * canned-fixture assertion style.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchor-schedule.check.mjs
 */
import assert from 'node:assert/strict';
import {
  scoreInInformativeBand,
  bandDistance,
  buildCandidateGraph,
  checkConnectivity,
  rescueConnectivity,
  selectMeasurePairs,
  canonicalPair,
  pairKey,
} from './calibration-anchor-schedule.mjs';

// ─── scoreInInformativeBand: [0.2, 0.8] inclusive, everything else excluded ──

assert.equal(scoreInInformativeBand(0.5), true, 'a 0.5 probe score must be inside the informative band');
assert.equal(scoreInInformativeBand(0.2), true, 'the 0.2 lower bound must be inside the informative band (inclusive)');
assert.equal(scoreInInformativeBand(0.8), true, 'the 0.8 upper bound must be inside the informative band (inclusive)');
assert.equal(scoreInInformativeBand(0.95), false, 'a 0.95 probe score must be OUTSIDE the informative band (D-01 drop)');
assert.equal(scoreInInformativeBand(0.05), false, 'a 0.05 probe score must be OUTSIDE the informative band (D-01 drop)');
console.log('PASS: scoreInInformativeBand — [0.2, 0.8] inclusive boundaries correct');

// ─── buildCandidateGraph: the 10-anchor default set (D-02) ─────────────────

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

const candidatePairs = buildCandidateGraph(TEN_ANCHOR_SET);

const adjacentMaiaPairs = candidatePairs.filter(([a, b]) => a.startsWith('maia') && b.startsWith('maia'));
const adjacentSfPairs = candidatePairs.filter(([a, b]) => a.startsWith('sf') && b.startsWith('sf'));
const crossFamilyPairs = candidatePairs.filter(([a, b]) => a.startsWith('maia') !== b.startsWith('maia'));

assert.equal(adjacentMaiaPairs.length, 4, `expected 4 adjacent-maia edges (700-1100-1500-1900-2300), got ${adjacentMaiaPairs.length}`);
assert.equal(adjacentSfPairs.length, 4, `expected 4 adjacent-sf edges (0-3-5-8-10), got ${adjacentSfPairs.length}`);
assert.ok(crossFamilyPairs.length >= 2, `expected >= 2 initial cross-family candidates, got ${crossFamilyPairs.length}`);

const seenKeys = new Set();
for (const [a, b] of candidatePairs) {
  const key = pairKey(a, b);
  assert.ok(!seenKeys.has(key), `duplicate pair ${key} present (a reverse (y,x) of an existing (x,y)?)`);
  seenKeys.add(key);
  assert.deepEqual(canonicalPair(a, b), [a, b], `pair [${a}, ${b}] is not canonically ordered`);
}
console.log(
  `PASS: buildCandidateGraph — 4 adjacent-maia + 4 adjacent-sf + ${crossFamilyPairs.length} cross-family candidates, ` +
    'all canonically ordered and de-duplicated',
);

// ─── checkConnectivity: BFS + cross-family-edge count guard (D-04) ─────────

const CONN_ANCHORS = ['maia1100', 'maia1500', 'sf0', 'sf3'];
const maiaPair = canonicalPair('maia1100', 'maia1500');
const sfPair = canonicalPair('sf0', 'sf3');
const crossPair1 = canonicalPair('maia1500', 'sf0');
const crossPair2 = canonicalPair('maia1100', 'sf3');

assert.throws(
  () => checkConnectivity([maiaPair, sfPair], CONN_ANCHORS),
  /disconnected/,
  'a maia-only + sf-only graph with ZERO cross links must throw (disconnected)',
);

assert.throws(
  () => checkConnectivity([maiaPair, sfPair, crossPair1], CONN_ANCHORS),
  /cross-family/,
  'a graph with exactly 1 cross link must throw (D-04 needs >= 2)',
);

assert.doesNotThrow(
  () => checkConnectivity([maiaPair, sfPair, crossPair1, crossPair2], CONN_ANCHORS),
  'a connected graph with 2 cross links must NOT throw',
);
console.log('PASS: checkConnectivity — throws on 0/1 cross-family links, passes on 2 (D-04)');

// ─── selectMeasurePairs: keep in-band, drop out-of-band ────────────────────

const probeScoreByPair = {
  [pairKey('maia1500', 'sf0')]: 0.95,
  [pairKey('maia1100', 'maia1500')]: 0.5,
};
const { kept, dropped } = selectMeasurePairs(probeScoreByPair);
assert.ok(kept.includes(pairKey('maia1100', 'maia1500')), 'a 0.5 pair must be KEPT (informative)');
assert.ok(dropped.includes(pairKey('maia1500', 'sf0')), 'a 0.95 pair must be DROPPED (not informative)');
console.log('PASS: selectMeasurePairs — drops a 0.95 pair, keeps a 0.5 pair');

// ─── rescueConnectivity: band-relaxing D-04 fallback ───────────────────────

assert.equal(bandDistance(0.5), 0, 'an in-band score must have zero band distance');
assert.ok(Math.abs(bandDistance(0.875) - 0.075) < 1e-12, 'bandDistance(0.875) must be 0.075 (above the 0.8 bound)');
assert.ok(Math.abs(bandDistance(0.0625) - 0.1375) < 1e-12, 'bandDistance(0.0625) must be 0.1375 (below the 0.2 bound)');

// The live 2026-07-15 dead-end in miniature: {maia700, sf0} and {maia1100, sf3}
// are two informative islands; the only bridges are out-of-band probed edges.
const RESCUE_ANCHORS = ['maia700', 'maia1100', 'sf0', 'sf3'];
const rescueKept = [pairKey('maia700', 'sf0'), pairKey('maia1100', 'sf3')];
const rescueScores = {
  [pairKey('maia700', 'sf0')]: 0.5,
  [pairKey('maia1100', 'sf3')]: 0.5,
  [pairKey('maia700', 'maia1100')]: 0.875, // closest to band — must be the rescue pick
  [pairKey('sf0', 'sf3')]: 0.0625, // farther from band — must NOT be picked
};
const rescue = rescueConnectivity(rescueKept, rescueScores, RESCUE_ANCHORS);
assert.deepEqual(
  rescue.rescued,
  [pairKey('maia1100', 'maia700')],
  'rescue must add back exactly the dropped bridging edge CLOSEST to the band',
);
assert.doesNotThrow(
  () => checkConnectivity(rescue.kept.map((key) => key.split('|')), RESCUE_ANCHORS),
  'the rescued graph must pass the D-04 guard (connected, 2 cross-family links)',
);

const alreadyConnected = rescueConnectivity(rescue.kept, rescueScores, RESCUE_ANCHORS);
assert.equal(alreadyConnected.rescued.length, 0, 'an already-connected graph must trigger no rescue');

const unbridgeable = rescueConnectivity([pairKey('maia700', 'sf0')], { [pairKey('maia700', 'sf0')]: 0.5 }, RESCUE_ANCHORS);
assert.equal(unbridgeable.rescued.length, 0, 'with no probed bridging edge, rescue must give up (caller fail-louds)');
console.log('PASS: rescueConnectivity — picks the nearest-to-band bridge, no-ops when connected, gives up when unbridgeable');

console.log('PASS: calibration-anchor-schedule — probe/measure gate + connectivity guard correct on canned fixtures');
process.exit(0);

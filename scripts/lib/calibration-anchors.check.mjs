#!/usr/bin/env node
/**
 * calibration-anchors.check.mjs — D-09 sf8/sf10 anchor-table extension
 * assertion (Phase 173, Plan 01, Task 1). No engines/network — mirrors
 * `calibration-elo.check.mjs`'s canned-fixture assertion style.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchors.check.mjs
 */
import assert from 'node:assert/strict';
import { SF_SKILL_ELO, anchorRatingFor } from './calibration-anchors.mjs';
import { parseAnchorSpec } from '../calibration-harness.mjs';

// ─── SF_SKILL_ELO gains numeric 8/10 entries (D-09) ────────────────────────

assert.equal(typeof SF_SKILL_ELO[8], 'number', 'SF_SKILL_ELO must have a numeric entry for key 8');
assert.equal(typeof SF_SKILL_ELO[10], 'number', 'SF_SKILL_ELO must have a numeric entry for key 10');
assert.equal(SF_SKILL_ELO[8], 2600, 'SF_SKILL_ELO[8] must be 2600 (173-RESEARCH.md Assumption A1)');
assert.equal(SF_SKILL_ELO[10], 2800, 'SF_SKILL_ELO[10] must be 2800 (173-RESEARCH.md Assumption A1)');

// ─── parseAnchorSpec accepts sf8/sf10 without throwing (the SF_SKILL_ELO gate now passes) ─

const sf8Spec = parseAnchorSpec('sf8');
assert.deepEqual(
  { kind: sf8Spec.kind, skillLevel: sf8Spec.skillLevel },
  { kind: 'sf', skillLevel: 8 },
  `parseAnchorSpec('sf8') must return { kind: 'sf', skillLevel: 8 }, got ${JSON.stringify(sf8Spec)}`,
);

const sf10Spec = parseAnchorSpec('sf10');
assert.deepEqual(
  { kind: sf10Spec.kind, skillLevel: sf10Spec.skillLevel },
  { kind: 'sf', skillLevel: 10 },
  `parseAnchorSpec('sf10') must return { kind: 'sf', skillLevel: 10 }, got ${JSON.stringify(sf10Spec)}`,
);

// ─── anchorRatingFor resolves the parsed specs to the new table entries ────

assert.equal(anchorRatingFor(sf8Spec), 2600, 'anchorRatingFor(sf8) must be 2600');
assert.equal(anchorRatingFor(sf10Spec), 2800, 'anchorRatingFor(sf10) must be 2800');

// ─── a pre-existing token still parses correctly (no regression) ──────────

const maia1500Spec = parseAnchorSpec('maia1500');
assert.deepEqual(
  { kind: maia1500Spec.kind, rungElo: maia1500Spec.rungElo },
  { kind: 'maia', rungElo: 1500 },
  `parseAnchorSpec('maia1500') must still return { kind: 'maia', rungElo: 1500 }, got ${JSON.stringify(maia1500Spec)}`,
);

console.log(
  'PASS: calibration-anchors — SF_SKILL_ELO[8]=2600/[10]=2800, parseAnchorSpec(sf8/sf10/maia1500) all correct',
);
process.exit(0);

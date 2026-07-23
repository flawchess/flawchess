#!/usr/bin/env node
/**
 * calibration-persona-cell-schedule.check.mjs — pure-logic fixture test for
 * the PersonaId-keyed persona-cell schedule (Phase 184, Plan 01, Task 3).
 * No engines, no network, no filesystem — every assertion runs against the
 * REAL `PERSONA_REGISTRY` + `BOT_STRENGTH_LOOKUP` data (imported live via
 * the `@/` alias hook, never re-derived), mirroring
 * `calibration-bot-cell-schedule.check.mjs`'s canned-fixture assertion
 * style. Not part of `npm test`/CI — manually invoked.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-persona-cell-schedule.check.mjs
 */
import assert from 'node:assert/strict';
import {
  ALL_PERSONA_CELLS,
  personaCellKey,
  retargetedBotEloFor,
  presetNameForBlend,
} from './calibration-persona-cell-schedule.mjs';

// ─── (1) Exactly 24 PersonaId-keyed cells, no silent drops ─────────────────

assert.equal(ALL_PERSONA_CELLS.length, 24, 'ALL_PERSONA_CELLS must hold exactly 24 entries (4 styles x 6 rungs)');
const uniquePersonaIds = new Set(ALL_PERSONA_CELLS.map((cell) => cell.personaId));
assert.equal(uniquePersonaIds.size, 24, 'every cell must have a distinct personaId — no duplicate/dropped slots');
console.log('PASS: ALL_PERSONA_CELLS — exactly 24 entries, 24 distinct personaId values');

// ─── (2) Pitfall 1 collision regression guard: rung 1800 (all 4 styles) ────
// shares an identical retargeted (botElo, blend) pair, yet MUST still
// produce 4 DISTINCT persona-cell keys.

/** Mirrors calibration-harness.mjs's cellKey(botElo, botBlend, anchorLabel) —
 * the NAIVE (botElo, blend)-based key personaCellKey must never regress to.
 * Defined locally (not imported from calibration-harness.mjs) so this
 * fixture stays pure/no-engine, per the Task 3 convention. */
function naiveBotCellKey(botElo, botBlend, anchorLabel) {
  return `${botElo}|${botBlend}|${anchorLabel}`;
}

const rung1800Cells = ALL_PERSONA_CELLS.filter((cell) => cell.rung === 1800);
assert.equal(rung1800Cells.length, 4, 'expected all 4 styles represented at rung 1800');

// Precondition: the 4 rung-1800 personas really DO collide on (botElo, blend)
// after D-01 retargeting — otherwise this fixture would not actually
// exercise Pitfall 1 (Deep preset's rung "1800" lookup entry is shared by
// every style, per bot-strength-lookup.json).
const naiveKeys = new Set(rung1800Cells.map((cell) => naiveBotCellKey(cell.botElo, cell.blend, 'maia1500')));
assert.equal(
  naiveKeys.size,
  1,
  'precondition: rung-1800 cells must share the SAME (botElo, blend) pair after retargeting (Pitfall 1) — ' +
    'if this fails, the fixture itself is stale, not the code under test',
);

// The actual guard: personaCellKey must still produce 4 DISTINCT keys even
// though the naive (botElo, blend) key collapses all 4 to a single value.
const personaKeys = new Set(rung1800Cells.map((cell) => personaCellKey(cell.personaId, 'maia1500')));
assert.equal(
  personaKeys.size,
  4,
  'personaCellKey must key strictly by PersonaId, never (botElo, blend) — collision regression (Pitfall 1). ' +
    'Reverting the key to (botElo, blend) collapses this to 1, same as naiveKeys above.',
);
console.log(
  'PASS: rung-1800 cells (all 4 styles) collide on (botElo=2300, blend=DEEP_BLEND) yet personaCellKey keeps 4 distinct keys',
);

// ─── (3) retargetedBotEloFor: CAL-04b styled overrides — Human-1200 -> 1500, ──
// Human-800 -> 700 ────────────────────────────────────────────────────────────
// The style-less BOT_STRENGTH_LOOKUP would give Human-1200 -> 1900 and clamp
// Human-800 -> 1100, but that stranded the botElo 700/1500 tiers and left the
// measured (with-style) ladder with gaps at ~800 and ~1200. STYLED_BOTELO_OVERRIDES
// (probe-validated: botElo 700 -> ~907, 1500 -> ~1278 with a style bundle) routes
// these two human rungs onto the validated tiers. This guards that override.

const HUMAN_BLEND_FIXTURE = 0; // mirrors playStyle.ts's HUMAN_BLEND — the Human preset's blend value

let human1200BotElo;
assert.doesNotThrow(() => {
  human1200BotElo = retargetedBotEloFor({ blend: HUMAN_BLEND_FIXTURE, rung: 1200 });
}, 'retargetedBotEloFor must not throw for an ordinary in-range rung');
assert.equal(
  human1200BotElo,
  1500,
  'a Human rung-1200 persona must retarget to botElo=1500 (STYLED_BOTELO_OVERRIDES.human[1200], ' +
    'the CAL-04b ~1200-gap fix), not the style-less lookup value 1900',
);

let human800BotElo;
assert.doesNotThrow(() => {
  human800BotElo = retargetedBotEloFor({ blend: HUMAN_BLEND_FIXTURE, rung: 800 });
}, 'retargetedBotEloFor must not throw for the 800-rung override case');
assert.equal(
  human800BotElo,
  700,
  'the 800 rung must retarget to botElo=700 (STYLED_BOTELO_OVERRIDES.human[800], the CAL-04b ~800-gap ' +
    'fix, ~907 measured), not the style-less floor clamp 1100',
);

// Cross-check against the real registry-derived cells (ALL_PERSONA_CELLS
// applies retargetedBotEloFor to every actual persona, not just this fixture).
const humanRung1200Cell = ALL_PERSONA_CELLS.find((cell) => cell.rung === 1200 && cell.style === 'Attacker');
assert.ok(humanRung1200Cell, 'expected an attacker-1200 (Human preset) cell to exist');
assert.equal(humanRung1200Cell.botElo, 1500, 'attacker-1200 (a real registry entry) must match the fixture above');

const humanRung800Cell = ALL_PERSONA_CELLS.find((cell) => cell.rung === 800 && cell.style === 'Attacker');
assert.ok(humanRung800Cell, 'expected an attacker-800 (Human preset) cell to exist');
assert.equal(humanRung800Cell.botElo, 700, 'attacker-800 (a real registry entry) must match the fixture above');

console.log('PASS: retargetedBotEloFor — CAL-04b overrides Human-1200 -> 1500, Human-800 -> 700, never throws');

// ─── (4) presetNameForBlend: fail-loud on an unknown blend value ──────────

assert.throws(
  () => presetNameForBlend(0.99),
  /does not match any of the 3 named presets/,
  'presetNameForBlend must throw fail-loud on a blend value that is not human(0)/light(0.05)/deep(0.5)',
);
console.log('PASS: presetNameForBlend — throws fail-loud on an unrecognized blend value (0.99)');

// ─── (5) The module imports (does not redefine) the bot-cell primitives ───

assert.equal(typeof personaCellKey, 'function', 'personaCellKey must be exported');
assert.equal(typeof retargetedBotEloFor, 'function', 'retargetedBotEloFor must be exported');
assert.equal(typeof presetNameForBlend, 'function', 'presetNameForBlend must be exported');

console.log('PASS: calibration-persona-cell-schedule — PersonaId-keyed schedule correct on the real registry data');
process.exit(0);

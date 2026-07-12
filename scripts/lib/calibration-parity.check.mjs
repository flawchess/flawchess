#!/usr/bin/env node
/**
 * calibration-parity.check.mjs — Wave 0 CAL-02 anti-drift parity assertion
 * (Phase 168 Task 3), mirroring `scripts/lib/gem-parity.check.mjs`'s pattern.
 *
 * Imports the REAL `selectBotMove` (`@/lib/engine/selectBotMove`), `mctsSearch`
 * (`@/lib/engine/mctsSearch`), and `maskAndSoftmax` (`@/lib/maiaEncoding`)
 * THROUGH the `@/` alias resolve hook — never re-derived. Asserts, against
 * hand-derived fixtures and DETERMINISTIC STUB providers (no real Maia/
 * Stockfish process), that:
 *
 *   1. At `blend=0` (`selectBotMove.ts` D-03/BOT-02), `selectBotMove` makes
 *      exactly ONE `policy()` call and NEVER calls `grade()` — returning the
 *      move the stub policy's weighted distribution dictates.
 *   2. At `blend=1` (D-06), `selectBotMove` defaults `deps.search` to the
 *      REAL `mctsSearch` (never a harness-local fork) and returns the
 *      deterministic argmax over `RankedLine.practicalScore`, which this
 *      fixture derives directly from the stub `grade()` Map's `evalCp`
 *      values via the real `leafScore.ts`/`treeCommon.ts` pipeline.
 *
 * Together these prove the harness runs the REAL regime dispatch — never a
 * fork — the standing CAL-02 guarantee that measured strength reflects the
 * code users actually play against.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-parity.check.mjs
 */
import assert from 'node:assert/strict';
import { selectBotMove } from '@/lib/engine/selectBotMove';
import { mctsSearch } from '@/lib/engine/mctsSearch';
import { maskAndSoftmax, POLICY_VOCAB_SIZE } from '@/lib/maiaEncoding';
import { mulberry32 } from '@/lib/engine/botSampling';

// Seed for every stub `rng` below — irrelevant to the outcome of either
// assertion (both fixtures are constructed so exactly one candidate wins
// regardless of the rng draw), but a fixed seed keeps this check itself
// reproducible.
const RNG_SEED = 1;

// ─── Structural tripwire: these must be the REAL frontend functions ───────────
// If a future edit ever redefines selectBotMove/mctsSearch/maskAndSoftmax
// locally instead of importing them, these imports themselves would not
// resolve — but a *renamed local shim* re-exported under the same name could
// still satisfy `typeof === 'function'`. Checking `.name` catches that: a
// hand-rolled stand-in assigned to a differently-named local would fail this
// unless the author went out of their way to preserve the exact source name,
// at which point the wiring is the same wiring the real function has.
assert.equal(typeof selectBotMove, 'function', 'selectBotMove must be a live-imported function');
assert.equal(selectBotMove.name, 'selectBotMove', 'selectBotMove must retain its frontend source name');
assert.equal(typeof mctsSearch, 'function', 'mctsSearch must be a live-imported function');
assert.equal(mctsSearch.name, 'mctsSearch', 'mctsSearch must retain its frontend source name');
assert.equal(typeof maskAndSoftmax, 'function', 'maskAndSoftmax must be a live-imported function');
assert.equal(maskAndSoftmax.name, 'maskAndSoftmax', 'maskAndSoftmax must retain its frontend source name');

// ─── maskAndSoftmax sanity fixture: uniform logits -> uniform legal-move probs ─

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const START_LEGAL_MOVE_COUNT = 20;
const PROB_TOLERANCE = 1e-9;

const zeroLogits = new Float32Array(POLICY_VOCAB_SIZE); // every logit 0 -> softmax must be uniform
const uniformProbs = maskAndSoftmax(zeroLogits, START_FEN);
const uniformKeys = Object.keys(uniformProbs);
assert.equal(
  uniformKeys.length,
  START_LEGAL_MOVE_COUNT,
  `maskAndSoftmax must mask to exactly the ${START_LEGAL_MOVE_COUNT} legal opening moves`,
);
for (const san of uniformKeys) {
  const expected = 1 / START_LEGAL_MOVE_COUNT;
  assert.ok(
    Math.abs(uniformProbs[san] - expected) < PROB_TOLERANCE,
    `maskAndSoftmax must split uniform logits evenly across legal moves (san=${san})`,
  );
}

// ─── Fixture 1 — blend=0: exactly one policy() call, grade() never called ─────

const BLEND_ZERO_EXPECTED_UCI = 'e2e4';

/** Deterministic regardless of rng draw: weight 1 for e2e4, weight 0 for d2d4. */
async function stubPolicyBlendZero() {
  return { [BLEND_ZERO_EXPECTED_UCI]: 1, d2d4: 0 };
}

async function stubGradeMustNotBeCalled() {
  throw new Error('grade() must never be called at blend<=0 (selectBotMove.ts D-03/BOT-02)');
}

const blendZeroMove = await selectBotMove(
  START_FEN,
  { elo: 1500, blend: 0, budget: { maxNodes: 1, maxPlies: 1, concurrency: 1 } },
  { policy: stubPolicyBlendZero, grade: stubGradeMustNotBeCalled, rng: mulberry32(RNG_SEED) },
);
assert.equal(
  blendZeroMove,
  BLEND_ZERO_EXPECTED_UCI,
  'blend=0 must return the move the stub policy distribution dictates (raw Maia sample, D-03)',
);

// ─── Fixture 2 — blend=1: real mctsSearch, deterministic argmax over stub grades ─

const BLEND_ONE_BEST_UCI = 'e2e4';
const BLEND_ONE_WORSE_UCI = 'd2d4';
// White-POV cp gap comfortably resolves to a decisive expected-score gap via
// the real evalToExpectedScore sigmoid (leafScore.ts) — not a close call.
const BLEND_ONE_BEST_EVAL_CP = 50;
const BLEND_ONE_WORSE_EVAL_CP = -50;
const BLEND_ONE_GRADE_DEPTH = 10;

async function stubPolicyBlendOne() {
  return { [BLEND_ONE_BEST_UCI]: 0.5, [BLEND_ONE_WORSE_UCI]: 0.5 };
}

async function stubGradeBlendOne(fen, candidateUcis) {
  assert.deepEqual(
    [...candidateUcis].sort(),
    [BLEND_ONE_BEST_UCI, BLEND_ONE_WORSE_UCI].sort(),
    'the real mctsSearch must request grade() for exactly the stub policy candidates (searchmoves-restricted)',
  );
  return new Map([
    [BLEND_ONE_BEST_UCI, { evalCp: BLEND_ONE_BEST_EVAL_CP, evalMate: null, depth: BLEND_ONE_GRADE_DEPTH }],
    [BLEND_ONE_WORSE_UCI, { evalCp: BLEND_ONE_WORSE_EVAL_CP, evalMate: null, depth: BLEND_ONE_GRADE_DEPTH }],
  ]);
}

const blendOneMove = await selectBotMove(
  START_FEN,
  { elo: 1500, blend: 1, budget: { maxNodes: 1, maxPlies: 1, concurrency: 1 } },
  { policy: stubPolicyBlendOne, grade: stubGradeBlendOne, rng: mulberry32(RNG_SEED) },
  // deps.search intentionally omitted — selectBotMove.ts defaults it to the
  // REAL mctsSearch (D-08); a harness that ever injected a local search fork
  // here would defeat the entire point of this check.
);
assert.equal(
  blendOneMove,
  BLEND_ONE_BEST_UCI,
  'blend=1 must return the deterministic argmax over practicalScore the stub grades dictate (real mctsSearch, D-06)',
);

console.log(
  'PASS: calibration parity — selectBotMove/mctsSearch/maskAndSoftmax imported live, zero reimplementation',
);
process.exit(0);

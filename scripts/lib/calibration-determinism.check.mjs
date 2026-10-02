#!/usr/bin/env node
/**
 * calibration-determinism.check.mjs — D-09 seeded-reproducibility assertion
 * (Phase 168, Plan 02, Task 2; re-budgeted Phase 168.5, Plan 05, Task 3, SC5).
 *
 * Runs `playGame()` from `../calibration-harness.mjs` TWICE against REAL
 * engines (Maia ONNX + Stockfish WASM — unlike the stub-provider
 * `calibration-parity.check.mjs`, this is a real-engine check) with the
 * IDENTICAL seed/opening/color, for a full `blend=1` game, and asserts
 * (`node:assert/strict`) the two resulting `moveUcis` sequences are
 * byte-identical.
 *
 * The anchor is a raw-Maia-argmax anchor (`maia1500`), deliberately NOT a
 * Stockfish-skill anchor — Stockfish's own `Skill Level` weakening injects
 * engine-internal randomness that would confound this test with a source of
 * nondeterminism unrelated to the harness's OWN seeded `mulberry32` rng
 * (D-09's actual subject: `selectBotMove`'s deterministic `blend=1` argmax
 * regime + the seeded rng plumbing, not Stockfish's skill-level noise).
 *
 * **Phase 168.5-05 SC5 re-budget:** this check now runs `playGame` at its
 * DEFAULT budget — i.e. no `maxNodes`/`maxPlies` override — which resolves to
 * the actual SHIPPED bot budget (`FLAWCHESS_BOT_MAX_NODES`=50/
 * `FLAWCHESS_BOT_MAX_PLIES`=8), and `playGame` has ALWAYS unconditionally
 * carried `stopRule: FLAWCHESS_BOT_STOP_RULE` + the pinned
 * `FLAWCHESS_BOT_CONCURRENCY` since 168.5-04 Task 2 (there is no override
 * knob for those two — they are not parameters `playGame` accepts). The old
 * `DETERMINISM_MAX_NODES=20` override (a Plan 02 artifact, back when the D-11
 * budget was still 400 nodes and a full-cost run took ~170s/move) is REMOVED
 * — Plan 04's real-engine measurement (`168.5-04-SUMMARY.md`) found the
 * SHIPPED 50-node/stop-rule-gated budget already costs only ~5.4s median/
 * ~12.7s worst-case per move, so there is no longer a reason to run this
 * proof at an artificially reduced budget: SC5 requires proving determinism
 * of the bot that ships, and the real budget is now cheap enough to just use
 * directly (see the imported `FLAWCHESS_BOT_*` constants below).
 *
 * Plan 03 note (investigated during Task 1): under real machine load, a
 * `grade()` call can exceed its `GRADING_MOVETIME_SAFETY_CAP_MS + SLACK_MS`
 * (5000ms) response-wait ceiling, which THROWS (not silently degrades) and
 * aborts the whole check with a "Stockfish response timeout" error — this is
 * a PRE-EXISTING fragility of the movetime-capped grading design inherited
 * from Plan 01/02, confirmed via an A/B test that reproduced the IDENTICAL
 * timeout on the untouched pre-pool (Plan 02) code on the same loaded
 * machine — NOT a regression introduced by the Stockfish pool. It surfaces
 * as either a hard timeout (as above) or, more subtly, a byte-level replay
 * divergence: if a `movetime`-bounded search doesn't reach the grading target
 * depth (the flat constant this file's era used, now `GRADING_ROOT_DEPTH`)
 * identically in both runs (because real elapsed time
 * relative to the 2500ms cap differs run-to-run under load), the returned
 * eval can differ by a few centipawns, which `mctsSearch`'s own
 * deterministic-per-concurrency-level node-selection (mctsSearch.ts's module
 * header) then legitimately propagates into a different move choice — this
 * applies at ANY pool size, including 1, since it is a property of the
 * ENGINE's real-time response, not of routing across independent pool
 * engines. Phase 168.5-02 (D-10) fixed this at the root (depth-only `go` +
 * `Clear Hash` per grading/adjudication call, load-independent by
 * construction) — this note is kept as history; a recurrence here would be a
 * regression, not an expected flake.
 *
 * Phase 184 (CAL-04) extension: `playGame` gained an optional `style` param
 * (`BotStyleParams`, forwarded into `selectBotMove`'s `BotSettings.style`
 * ONLY when defined — a conditional spread, never a literal `style:
 * undefined` key). Two additional assertions below cover the new seam:
 *
 *   1. STYLE-05 absent-style byte-identity (real engines): a `playGame` run
 *      that OMITS `style` entirely must be byte-identical to one that passes
 *      `style: undefined` explicitly, under the same seed — proving the
 *      conditional spread genuinely leaves `BotSettings` structurally
 *      unchanged, not just "usually produces the same move".
 *   2. A DEFINED style bundle reaches `selectBotMove` and changes its
 *      output. This assertion calls the REAL `selectBotMove` directly with
 *      DETERMINISTIC STUB `policy`/`grade` providers and a fixed `rng`
 *      (mirrors `calibration-parity.check.mjs`'s stub-provider convention)
 *      rather than playing a second/third full real-engine game — a fixed
 *      `rng` and hand-derived cumulative weights make the flip
 *      deterministic and fast, instead of relying on a real Maia policy
 *      distribution to probabilistically diverge over a multi-ply game.
 *
 * Phase 226 D-03 addition: `--no-clear-hash` skips the two blocks above
 * entirely and runs a DIFFERENT proof — the "warm arm" — over a grading-only
 * pool built with `clearHash: false` (RESEARCH Pattern 5). The blocks above
 * prove the load-independent Clear-Hash regime this file has always measured
 * is reproducible; the warm arm proves the OPPOSITE regime — the one that
 * actually ships (F-5: the browser worker's 8 MB Hash table is set once at
 * `uciok` and never cleared again) — is NOT bit-reproducible, and reports HOW
 * MUCH it diverges. This is the shipped-configuration noise floor Phase 227's
 * D-06 tolerance anchors to, and D-16 uses it as the warm-hash comparison
 * point for the root split's own grade-content bound. `--games N` (default 1)
 * and `--out-dir DIR` (optional per-ply TSV) are ONLY meaningful with
 * `--no-clear-hash`; omitting all three flags reproduces today's behavior
 * byte-for-byte.
 *
 * Run via:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-determinism.check.mjs \
 *     --no-clear-hash [--games N] [--out-dir reports/data]
 */
import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs';

import {
  setupHarnessEngines,
  playGame,
  parseAnchorSpec,
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_STOP_RULE,
  FLAWCHESS_BOT_CONCURRENCY,
} from '../calibration-harness.mjs';
import { OPENING_BOOK } from './calibration-openings.mjs';
import { createStockfishPool } from './stockfish-pool.mjs';
import { makeNodeProviders } from './calibration-providers.mjs';
import { applyUciMove } from './calibration-game-loop.mjs';
import { mulberry32 } from '@/lib/engine/botSampling';
import { selectBotMove } from '@/lib/engine/selectBotMove';
import { ATTACKER_STYLE } from '@/lib/engine/botStyleBundles';
import { evalToExpectedScore } from '@/lib/liveFlaw';
import { WORKER_HASH_MB, DESKTOP_POOL_MAX } from '@/lib/engine/workerPoolState';

const DETERMINISM_SEED = 42;
const DETERMINISM_ELO = 1500;
const DETERMINISM_BLEND = 1; // full-Stockfish argmax — the deterministic regime this check must prove reproducible
const DETERMINISM_BOT_IS_WHITE = true;

const opening = OPENING_BOOK[0];
const anchorSpec = parseAnchorSpec('maia1500');

/** Small pool for the determinism check — 2 processes exercises the real acquire/release path, not just a trivial size-1 pass-through. */
const DETERMINISM_STOCKFISH_PROCS = 2;

// ─── Phase 226 D-03: warm-arm (no-Clear-Hash) constants ────────────────────

/** Grading-only pool size for the warm arm — sized to the shipped desktop pool ceiling, not the small 2-process determinism pool above. */
const WARM_ARM_GRADING_PROCS = DESKTOP_POOL_MAX;

/** Regrade depth for comparing the two runs' picks (RESEARCH Pattern 2/5: mirrors engine-move-quality.mjs's gradePair d18+ re-grade). */
const WARM_ARM_REGRADE_DEPTH = 18;

/** Default `--games` value when the flag is omitted. */
const WARM_ARM_DEFAULT_GAMES = 1;

/** Exact UCI command `nodeGrade` sends to clear the transposition table — the warm arm's send-spy watches for this string verbatim. */
const CLEAR_HASH_COMMAND = 'setoption name Clear Hash';

/** Decimal places for the WARM-ARM SUMMARY line's expected-score numbers — readable, not spuriously precise. */
const WARM_ARM_ES_DECIMALS = 4;

// ─── CLI flag parsing (Phase 226 D-03) ─────────────────────────────────────

/**
 * Parses `--no-clear-hash`, `--games N`, `--out-dir DIR`. Rejects any other
 * token with a usage message (acceptance criterion: an unknown flag must
 * exit non-zero, not silently no-op). No flags at all yields
 * `{ noClearHash: false, games: WARM_ARM_DEFAULT_GAMES, outDir: null }` —
 * exactly today's behavior, since `games`/`outDir` are read ONLY inside the
 * warm arm.
 */
export function parseArgs(argv) {
  const args = { noClearHash: false, games: WARM_ARM_DEFAULT_GAMES, outDir: null };
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    switch (token) {
      case '--no-clear-hash':
        args.noClearHash = true;
        break;
      case '--games': {
        const value = argv[++i];
        const parsed = Number.parseInt(value, 10);
        if (!Number.isInteger(parsed) || parsed < 1) {
          throw new Error(`Invalid --games value ${JSON.stringify(value)}: expected a positive integer`);
        }
        args.games = parsed;
        break;
      }
      case '--out-dir':
        args.outDir = argv[++i];
        if (!args.outDir) throw new Error('--out-dir requires a directory path argument');
        break;
      default:
        throw new Error(
          `Unknown flag ${JSON.stringify(token)}. Usage: calibration-determinism.check.mjs [--no-clear-hash] [--games N] [--out-dir DIR]`,
        );
    }
  }
  return args;
}

// ─── Default arm: today's Clear-Hash bit-identity assertions (D-08 unchanged) ─

/**
 * Everything this check has proven since Phase 168 (D-09 seeded
 * reproducibility + Phase 184's STYLE-03/STYLE-05 assertions), unchanged —
 * see the module doc comment above. Runs ONLY when `--no-clear-hash` is
 * absent.
 */
async function runDefaultArm() {
  // ─── Phase 184: defined style bundle reaches selectBotMove (deterministic stub) ─

  // A position where the SAME pawn has both a capture and a quiet-advance
  // candidate move, so Attacker's featureMultipliers (isCapture=1.5,
  // isPawnAdvance=1.1, isPawnStorm=1.6 applied identically to both — a common
  // factor that cancels out of the RELATIVE ordering) cleanly separate the two
  // moves' reweighted mass. Position: 1.e4 d5, White to move.
  const STYLE_CHECK_FEN = 'rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2';
  const STYLE_CHECK_CAPTURE_UCI = 'e4d5'; // pawn takes pawn: isCapture + isExchange + isPawnStorm
  const STYLE_CHECK_ADVANCE_UCI = 'e4e5'; // quiet push: isPawnAdvance + isPawnStorm

  /** Equal raw mass on both candidates — any divergence in the picked move is
   * caused ENTIRELY by the style reweighting, never by an unequal starting prior. */
  async function stubPolicyStyleCheck() {
    return { [STYLE_CHECK_CAPTURE_UCI]: 0.5, [STYLE_CHECK_ADVANCE_UCI]: 0.5 };
  }

  async function stubGradeMustNotBeCalledStyle() {
    throw new Error('grade() must never be called at blend<=0 (selectBotMove.ts D-03/BOT-02)');
  }

  /** Fixed, non-random draw (D-10's `rng` contract is just `() => number`) — makes
   * `botSampling.ts`'s `weightedPick` cumulative-sum comparison fully deterministic. */
  const FIXED_DRAW = () => 0.5;

  const unstyledPick = await selectBotMove(
    STYLE_CHECK_FEN,
    { elo: 1500, blend: 0, budget: { maxNodes: 1, maxPlies: 1, concurrency: 1 } },
    { policy: stubPolicyStyleCheck, grade: stubGradeMustNotBeCalledStyle, rng: FIXED_DRAW },
  );
  assert.equal(
    unstyledPick,
    STYLE_CHECK_ADVANCE_UCI,
    `precondition: with equal raw weights and a fixed 0.5 draw, the UNSTYLED pick must be the alphabetically-second candidate (${STYLE_CHECK_ADVANCE_UCI})`,
  );

  const styledPick = await selectBotMove(
    STYLE_CHECK_FEN,
    { elo: 1500, blend: 0, budget: { maxNodes: 1, maxPlies: 1, concurrency: 1 }, style: ATTACKER_STYLE },
    { policy: stubPolicyStyleCheck, grade: stubGradeMustNotBeCalledStyle, rng: FIXED_DRAW },
  );
  assert.equal(
    styledPick,
    STYLE_CHECK_CAPTURE_UCI,
    'a defined style bundle (ATTACKER_STYLE) must reach selectBotMove\'s prior-reweighting branch and flip the ' +
      `pick to the capture (${STYLE_CHECK_CAPTURE_UCI}) under the SAME fixed draw and raw weights (STYLE-03)`,
  );
  console.log(
    'PASS: a defined style bundle reaches selectBotMove and changes its output (STYLE-03 prior reweighting, deterministic stub)',
  );

  const { providers, pool, Chess } = await setupHarnessEngines({ stockfishProcs: DETERMINISM_STOCKFISH_PROCS });

  try {
    const gameRng1 = mulberry32(DETERMINISM_SEED);
    const result1 = await playGame({
      Chess,
      providers,
      pool,
      botElo: DETERMINISM_ELO,
      botBlend: DETERMINISM_BLEND,
      anchorSpec,
      startFen: opening.fen,
      botIsWhite: DETERMINISM_BOT_IS_WHITE,
      gameRng: gameRng1,
      // No maxNodes/maxPlies override (Phase 168.5-05 SC5 re-budget, see module
      // doc comment) — defaults to FLAWCHESS_BOT_MAX_NODES/_MAX_PLIES, the
      // ACTUAL shipped bot budget; stopRule/concurrency are already always
      // FLAWCHESS_BOT_STOP_RULE/_CONCURRENCY inside playGame unconditionally.
    });

    const gameRng2 = mulberry32(DETERMINISM_SEED);
    const result2 = await playGame({
      Chess,
      providers,
      pool,
      botElo: DETERMINISM_ELO,
      botBlend: DETERMINISM_BLEND,
      anchorSpec,
      startFen: opening.fen,
      botIsWhite: DETERMINISM_BOT_IS_WHITE,
      gameRng: gameRng2,
      // Same rationale as gameRng1's call above.
    });

    assert.deepEqual(
      result2.moveUcis,
      result1.moveUcis,
      'same --seed must reproduce a byte-identical blend=1 game (D-09)',
    );

    // ─── Phase 184: absent style === `style: undefined` (STYLE-05) ────────────
    // `result1` above OMITS `style` entirely. This third run passes `style:
    // undefined` EXPLICITLY under the identical seed/settings — proving the
    // conditional spread inside `selectBotMoveOnce` (`...(style !== undefined ?
    // { style } : {})`) genuinely produces the same BotSettings object shape
    // either way, not merely a coincidentally-identical move in this one game.
    const gameRng3 = mulberry32(DETERMINISM_SEED);
    const result3 = await playGame({
      Chess,
      providers,
      pool,
      botElo: DETERMINISM_ELO,
      botBlend: DETERMINISM_BLEND,
      anchorSpec,
      startFen: opening.fen,
      botIsWhite: DETERMINISM_BOT_IS_WHITE,
      gameRng: gameRng3,
      style: undefined,
    });

    assert.deepEqual(
      result3.moveUcis,
      result1.moveUcis,
      'omitting `style` and passing `style: undefined` explicitly must produce byte-identical games (STYLE-05 absent-style invariant)',
    );
    console.log(
      'PASS: omitting `style` vs explicit `style: undefined` produce a byte-identical game (STYLE-05 absent-style invariant)',
    );

    console.log(
      `PASS: calibration determinism — same seed reproduced an identical ${result1.moveUcis.length}-ply blend=1 game ` +
        `(result=${result1.result}, reason=${result1.reason}, stockfish-procs=${DETERMINISM_STOCKFISH_PROCS}, ` +
        `budget: FLAWCHESS_BOT_MAX_NODES=${FLAWCHESS_BOT_MAX_NODES} FLAWCHESS_BOT_MAX_PLIES=${FLAWCHESS_BOT_MAX_PLIES} ` +
        `FLAWCHESS_BOT_CONCURRENCY=${FLAWCHESS_BOT_CONCURRENCY} FLAWCHESS_BOT_STOP_RULE=${JSON.stringify(FLAWCHESS_BOT_STOP_RULE)})`,
    );
  } finally {
    pool.quitAll();
  }

  process.exit(0);
}

// ─── Warm arm (Phase 226 D-03): shipped no-Clear-Hash noise floor ──────────

/**
 * Re-grades `uciA` and `uciB` at `WARM_ARM_REGRADE_DEPTH` on a SEPARATE
 * Clear-Hash pool (never one of the two warm grading pools under
 * measurement), converting each to a mover-POV expected score — mirrors
 * `engine-move-quality.mjs`'s `gradePair` (same dedup-and-convert shape, a
 * different pool/depth). Either or both may come back `null` if the engine
 * never returned an exact info line for that candidate (should not normally
 * occur at a fixed depth on legal moves).
 */
async function regradeBothPicks(regradePool, fen, uciA, uciB) {
  const candidateUcis = [...new Set([uciA, uciB])];
  const grades = await regradePool.grade(fen, candidateUcis, undefined, WARM_ARM_REGRADE_DEPTH);
  const mover = fen.split(' ')[1] === 'b' ? 'black' : 'white';
  const esFor = (uci) => {
    const grade = grades.get(uci);
    if (grade === undefined) return null;
    return evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
  };
  return { esA: esFor(uciA), esB: esFor(uciB) };
}

/**
 * Plays ONE warm-arm game pair: run 1 is a full seeded game on a fresh
 * `clearHash: false` grading pool; run 2 replays run 1's exact positions
 * (never its own picks — this is what keeps both runs on identical FENs) on
 * a SECOND fresh `clearHash: false` grading pool, calling the real
 * `selectBotMove` at every bot ply with a fresh `mulberry32(seed)` stream
 * (RESEARCH Pattern 5). Both grading pools assert (fail loudly) zero
 * `Clear Hash` sends over their whole lifetime — the structural half of what
 * this arm proves; the reported per-ply divergence is the measured half.
 */
async function playWarmArmGamePair({ index, adjudicationPool, Chess, maiaCtx }) {
  const seed = DETERMINISM_SEED + index;

  // Run 1: full seeded game on a fresh warm (no-Clear-Hash) grading pool.
  const run1ClearHashLines = { count: 0 };
  let gradingPool1;
  let run1;
  try {
    gradingPool1 = await createStockfishPool({
      size: WARM_ARM_GRADING_PROCS,
      hashMb: WORKER_HASH_MB,
      clearHash: false,
      sendObserver: (command) => {
        if (command === CLEAR_HASH_COMMAND) run1ClearHashLines.count++;
      },
    });
    const providers1 = makeNodeProviders(maiaCtx.session, maiaCtx.ort, gradingPool1.grade);
    run1 = await playGame({
      Chess,
      providers: providers1,
      pool: adjudicationPool,
      botElo: DETERMINISM_ELO,
      botBlend: DETERMINISM_BLEND,
      anchorSpec,
      startFen: opening.fen,
      botIsWhite: DETERMINISM_BOT_IS_WHITE,
      gameRng: mulberry32(seed),
    });
  } finally {
    gradingPool1?.quitAll();
  }
  assert.equal(
    run1ClearHashLines.count,
    0,
    `warm arm game ${index}: run 1's grading pool must never send "${CLEAR_HASH_COMMAND}" (D-03)`,
  );

  // Run 2: replay run 1's exact positions on a SECOND fresh warm grading
  // pool, calling the real bot move selection at every bot ply — but always
  // APPLYING run 1's recorded move to advance, so both runs see identical
  // positions and differ only through warm-table scheduling.
  const run2ClearHashLines = { count: 0 };
  let gradingPool2;
  const rows = [];
  let differingCount = 0;
  let firstDivergencePly = null;

  try {
    gradingPool2 = await createStockfishPool({
      size: WARM_ARM_GRADING_PROCS,
      hashMb: WORKER_HASH_MB,
      clearHash: false,
      sendObserver: (command) => {
        if (command === CLEAR_HASH_COMMAND) run2ClearHashLines.count++;
      },
    });
    const providers2 = makeNodeProviders(maiaCtx.session, maiaCtx.ort, gradingPool2.grade);
    const gameRng2 = mulberry32(seed);
    const chess = new Chess(opening.fen);

    for (let plyIndex = 0; plyIndex < run1.moveUcis.length; plyIndex++) {
      const fen = chess.fen();
      const whiteToMove = fen.split(' ')[1] !== 'b';
      const botToMove = whiteToMove === DETERMINISM_BOT_IS_WHITE;
      const uci1 = run1.moveUcis[plyIndex];

      if (botToMove) {
        const uci2 = await selectBotMove(
          fen,
          {
            elo: DETERMINISM_ELO,
            blend: DETERMINISM_BLEND,
            budget: {
              maxNodes: FLAWCHESS_BOT_MAX_NODES,
              maxPlies: FLAWCHESS_BOT_MAX_PLIES,
              concurrency: FLAWCHESS_BOT_CONCURRENCY,
              stopRule: FLAWCHESS_BOT_STOP_RULE,
            },
          },
          { policy: providers2.policy, grade: providers2.grade, rng: gameRng2 },
        );
        const { esA, esB } = await regradeBothPicks(adjudicationPool, fen, uci1, uci2);
        const absDes = esA !== null && esB !== null ? Math.abs(esA - esB) : null;
        if (uci2 !== uci1) {
          differingCount++;
          if (firstDivergencePly === null) firstDivergencePly = plyIndex + 1; // 1-indexed ply
        }
        rows.push({
          game: index,
          seed,
          ply: plyIndex + 1,
          fen,
          pickRun1: uci1,
          pickRun2: uci2,
          esRun1: esA,
          esRun2: esB,
          absDes,
        });
      }

      applyUciMove(chess, uci1);
    }
  } finally {
    gradingPool2?.quitAll();
  }
  assert.equal(
    run2ClearHashLines.count,
    0,
    `warm arm game ${index}: run 2's grading pool must never send "${CLEAR_HASH_COMMAND}" (D-03)`,
  );

  console.log(
    `WARM-ARM game=${index} plies=${rows.length} differing=${differingCount} ` +
      `first_divergence_ply=${firstDivergencePly ?? 'none'}`,
  );

  return rows;
}

/** Writes the per-ply warm-arm TSV (nine named columns) to `outDir`, creating it if needed. */
function writeWarmArmTsv(outDir, rows) {
  fs.mkdirSync(outDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filePath = path.join(outDir, `calibration-determinism-warm-${stamp}.tsv`);
  const header = ['game', 'seed', 'ply', 'fen', 'pick_run1', 'pick_run2', 'es_run1', 'es_run2', 'abs_des'];
  const lines = [header.join('\t')];
  for (const row of rows) {
    lines.push(
      [
        row.game,
        row.seed,
        row.ply,
        row.fen,
        row.pickRun1,
        row.pickRun2,
        row.esRun1 ?? '',
        row.esRun2 ?? '',
        row.absDes ?? '',
      ].join('\t'),
    );
  }
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
  console.log(`WARM-ARM wrote ${rows.length} row(s) to ${filePath}`);
}

/**
 * Runs `games` warm-arm game pairs and prints the final `WARM-ARM SUMMARY`
 * line. Structure-only assertions (zero Clear Hash on either grading pool)
 * happen per-game inside `playWarmArmGamePair`; this function only
 * aggregates and reports divergence — it never asserts bit-identity
 * (RESEARCH Pattern 5: the warm arm's whole point is that divergence is
 * EXPECTED, not a failure).
 */
async function runWarmArm({ games, outDir }) {
  const { pool: adjudicationPool, Chess, maiaCtx } = await setupHarnessEngines({
    stockfishProcs: DETERMINISM_STOCKFISH_PROCS,
  });

  const allRows = [];
  try {
    for (let index = 0; index < games; index++) {
      const rows = await playWarmArmGamePair({ index, adjudicationPool, Chess, maiaCtx });
      allRows.push(...rows);
    }
  } finally {
    adjudicationPool.quitAll();
  }

  const pliesCompared = allRows.length;
  const pliesDiffering = allRows.filter((row) => row.pickRun2 !== row.pickRun1).length;
  const absDesValues = allRows.map((row) => row.absDes).filter((value) => value !== null);
  const meanAbsDes =
    absDesValues.length > 0 ? absDesValues.reduce((sum, value) => sum + value, 0) / absDesValues.length : 0;
  const maxAbsDes = absDesValues.length > 0 ? Math.max(...absDesValues) : 0;

  console.log(
    `WARM-ARM SUMMARY games=${games} plies_compared=${pliesCompared} plies_differing=${pliesDiffering} ` +
      `mean_abs_des=${meanAbsDes.toFixed(WARM_ARM_ES_DECIMALS)} max_abs_des=${maxAbsDes.toFixed(WARM_ARM_ES_DECIMALS)}`,
  );

  if (outDir) writeWarmArmTsv(outDir, allRows);

  process.exit(0);
}

// ─── Entry point ────────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.noClearHash) {
    await runWarmArm(args);
  } else {
    await runDefaultArm();
  }
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});

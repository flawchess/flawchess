#!/usr/bin/env node
/**
 * style-lever-measurement.mjs — D-11 headless style-lever measurement
 * script (Phase 182, STYLE-01..04).
 *
 * Measures how much each of the 4 named `BOT_STYLE_BUNDLES` styles
 * (Attacker / Trickster / Grinder / Wall) shifts move-feature frequency vs
 * an unstyled baseline, across a fixed seeded set of mid-opening FENs. Two
 * independent levers are measured, matching the two engine seams
 * `botStyle.ts` exposes:
 *
 *   - `prior_reweighting` (STYLE-03, Human rungs): a REAL Maia policy
 *     forward pass at a single representative ELO rung (`--elo`) is
 *     reweighted via the LIVE `applyStylePriorReweighting`. The metric is
 *     the EXPECTED per-feature frequency under the resulting distribution —
 *     i.e. `sum(weight_i * feature_i) / sum(weight_i)` over legal moves,
 *     classified via the LIVE `classifyMoveFeatures` — which is exactly the
 *     long-run share of moves `botSampling.ts`'s LIVE `samplePolicy`
 *     (`weightedPick` under the hood) would draw for that feature, without
 *     needing to actually draw thousands of samples per position.
 *   - `score_shaping` (STYLE-04, Light/Deep rungs): since a full MCTS
 *     search is out of scope for a fast headless measurement pass, this
 *     lane SYNTHESIZES a `RankedLine[]` fixture from the same real Maia
 *     policy call — `practicalScore` is the move's raw policy probability
 *     (a legitimate 0-1 proxy, though semantically a probability rather
 *     than a true search-derived expected score) and `childScoreSpread` is
 *     a documented, hand-picked "tactical vs quiet" proxy keyed off the
 *     move's own classified features (see `synthesizedChildScoreSpread`
 *     below) — NOT a real search statistic. The LIVE `applyStyleScoreShaping`
 *     reshapes it, then the SAME expected-frequency technique is applied
 *     using the identical softmax weighting formula
 *     `sampleRankedLines`/`selectBotMove.ts` use (`exp((score-max)/tau)`,
 *     `tau` = `SCORE_SHAPING_TAU`, a representative point in the Light/Deep
 *     `TAU_MAX * (1 - blend)` band) — never calling `sampleRankedLines`
 *     itself, since that draws exactly one sample rather than reporting the
 *     distribution the tuning loop needs to see.
 *
 * Zero reimplementation (D-11 must-have): `applyStylePriorReweighting`,
 * `applyStyleScoreShaping`, `classifyMoveFeatures`, and `BOT_STYLE_BUNDLES`
 * are all IMPORTED from the live frontend source via the `@/` alias
 * resolve hook (`scripts/lib/frontend-alias-hook.mjs`) — never re-derived.
 * `mulberry32` is likewise imported from the live `botSampling.ts`, not
 * hand-rolled, mirroring `gem-elo-calibration.mjs`'s WR-05 discipline. Only
 * the softmax WEIGHT-COMPUTATION formula (not sampling itself, and not one
 * of the 3 prohibited functions) is replicated locally, because computing
 * an expectation needs the full weight vector, and no live export returns
 * that vector directly. Emits a TSV of style x lever x feature baseline/
 * styled/delta frequencies to `reports/data/`.
 *
 * Usage:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/style-lever-measurement.mjs \
 *     [--n 100] [--seed 1] [--elo 1000] [--out-dir reports/data]
 */
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

import { createMaiaSession, resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { OPENING_BOOK } from './lib/calibration-openings.mjs';

// ─── Imports from LIVE frontend source (via the @/ alias hook) — D-11 ─────────
import {
  encodeBoard,
  maskAndSoftmax,
  eloToInput,
  MAIA_ELO_LADDER,
  NUM_SQUARES,
  PLANES_PER_SQUARE,
  POLICY_VOCAB_SIZE,
} from '@/lib/maiaEncoding';
import {
  applyStylePriorReweighting,
  applyStyleScoreShaping,
  classifyMoveFeatures,
} from '@/lib/engine/botStyle';
import { BOT_STYLE_BUNDLES } from '@/lib/engine/botStyleBundles';
import { mulberry32 } from '@/lib/engine/botSampling';

// ─── Constants (no magic numbers) ──────────────────────────────────────────────

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');

const DEFAULT_SAMPLE_SIZE = 100;
const DEFAULT_SEED = 1;
/** A representative Human-rung Maia ELO (mid `MAIA_ELO_LADDER`) — prior
 * reweighting (STYLE-03) is a Human-rung (blend<=0) lever, so the measured
 * policy should come from a rung inside that band, not an arbitrary one. */
const DEFAULT_MEASUREMENT_ELO = 1000;
const DEFAULT_OUT_DIR = path.join(REPO_ROOT, 'reports/data');

/** The 6 `MoveFeatures` flags this script tallies, in TSV column order. */
const FEATURE_KEYS = [
  'isCheck',
  'isCapture',
  'isPawnAdvance',
  'isPawnStorm',
  'isExchange',
  'isRetreat',
];

/** The two levers measured, matching `botStyle.ts`'s two style seams. */
const LEVERS = ['prior_reweighting', 'score_shaping'];

/** Softmax sharpness for the score_shaping lane's expected-frequency
 * weighting — a representative midpoint of `selectBotMove.ts`'s
 * `TAU_MAX * (1 - blend)` band across the Light (blend=0.05, tau≈0.095) and
 * Deep (blend=0.5, tau≈0.05) presets (`frontend/src/lib/playStyle.ts`). Not
 * itself imported (it's a private `selectBotMove.ts` module constant), but
 * the VALUE is cited here with its provenance rather than an unexplained
 * magic number. */
const SCORE_SHAPING_TAU = 0.075;

/** Synthesized `childScoreSpread` proxy (score_shaping lane only — see the
 * module header) for a move classified as tactical (check/capture/storm):
 * a wide grandchild-score spread is plausible for a position that just
 * became sharp. [ASSUMED], not measured. */
const HIGH_SPREAD_PROXY = 0.3;
/** Synthesized proxy for a move that is neither tactical nor simplifying
 * (a quiet developing move). [ASSUMED], not measured. */
const MID_SPREAD_PROXY = 0.1;
/** Synthesized proxy for a move classified as simplifying (exchange/
 * retreat): a narrow grandchild-score spread is plausible for a position
 * that just got flatter/quieter. [ASSUMED], not measured. */
const LOW_SPREAD_PROXY = 0.02;

// ─── CLI parsing (WR-02 discipline: every flag that consumes a value MUST
// validate it — mirrors gem-elo-calibration.mjs's requireFlagValue/
// parsePositiveIntFlag pattern) ─────────────────────────────────────────────

function requireFlagValue(value, key) {
  if (value === undefined || value.startsWith('--')) {
    throw new Error(`Missing value for --${key}`);
  }
  return value;
}

function parsePositiveIntFlag(value, key, min = 1) {
  const raw = requireFlagValue(value, key);
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isInteger(parsed) || parsed < min) {
    throw new Error(`Invalid --${key} value ${JSON.stringify(raw)}: expected an integer >= ${min}`);
  }
  return parsed;
}

function parseArgs(argv) {
  const args = {
    n: DEFAULT_SAMPLE_SIZE,
    seed: DEFAULT_SEED,
    elo: DEFAULT_MEASUREMENT_ELO,
    outDir: DEFAULT_OUT_DIR,
  };
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[i + 1];
    switch (key) {
      case 'n':
        args.n = parsePositiveIntFlag(value, key);
        i++;
        break;
      case 'seed': {
        const raw = requireFlagValue(value, key);
        const parsed = Number.parseInt(raw, 10);
        if (!Number.isInteger(parsed)) {
          throw new Error(`Invalid --seed value ${JSON.stringify(raw)}: expected an integer`);
        }
        args.seed = parsed;
        i++;
        break;
      }
      case 'elo':
        args.elo = parsePositiveIntFlag(value, key);
        i++;
        break;
      case 'out-dir':
        args.outDir = path.resolve(requireFlagValue(value, key));
        i++;
        break;
      default:
        throw new Error(`Unknown flag --${key}`);
    }
  }
  if (!MAIA_ELO_LADDER.includes(args.elo)) {
    throw new Error(`Invalid --elo value ${args.elo}: not a member of MAIA_ELO_LADDER (${MAIA_ELO_LADDER.join(',')})`);
  }
  return args;
}

// ─── Position sampling (mulberry32-seeded, with replacement) ──────────────────

/** Draws `n` FENs from the curated `OPENING_BOOK` corpus, seeded via the
 * LIVE `mulberry32` PRNG. Sampled WITH replacement — the corpus (33 entries
 * as of Phase 182) is smaller than a realistic tuning `n`, and the
 * per-position measurement below is order-independent, so repeats are
 * harmless (a frequency measure, not a coverage sweep). */
function samplePositions(n, seed) {
  const random = mulberry32(seed);
  const positions = [];
  for (let i = 0; i < n; i++) {
    const idx = Math.floor(random() * OPENING_BOOK.length);
    const opening = OPENING_BOOK[idx];
    positions.push(opening.fen);
  }
  return positions;
}

// ─── Maia policy (single ELO rung, batch of 1) ─────────────────────────────────

/** One Maia forward pass for `fen` at `elo`, returning the raw UCI-keyed
 * policy (`applyStylePriorReweighting`'s expected shape) plus the chess.js
 * verbose legal-move list (reused by both measurement lanes below). */
async function maiaPolicyForFen({ ort, session }, fen, elo, Chess) {
  const boardTokens = encodeBoard(fen);
  const eloInput = Float32Array.from([eloToInput(elo)]);
  const feeds = {
    tokens: new ort.Tensor('float32', boardTokens, [1, NUM_SQUARES, PLANES_PER_SQUARE]),
    elo_self: new ort.Tensor('float32', eloInput, [1]),
    elo_oppo: new ort.Tensor('float32', eloInput, [1]),
  };
  const result = await session.run(feeds);
  const policyFlat = result.logits_move.data.slice(0, POLICY_VOCAB_SIZE);
  const probsBySan = maskAndSoftmax(policyFlat, fen);

  const chess = new Chess(fen);
  const legalMoves = chess.moves({ verbose: true });
  const rawPolicyByUci = {};
  for (const move of legalMoves) {
    rawPolicyByUci[move.lan] = probsBySan[move.san] ?? 0;
  }
  return { rawPolicyByUci, legalMoves };
}

// ─── Expected feature frequency under a weighted distribution ─────────────────

/**
 * `sum(weight_i * feature_i) / sum(weight_i)` per `FEATURE_KEYS` flag, over
 * `legalMoves` classified via the LIVE `classifyMoveFeatures` — the
 * closed-form expectation of what `weightedPick`'s (`samplePolicy`'s
 * internal helper) long-run draws would show for each feature, computed
 * directly rather than by drawing thousands of samples. Returns `null` for
 * a degenerate (empty/all-non-positive/non-finite) weight total, mirroring
 * `weightedPick`'s own degenerate-signal convention — a position this
 * happens for is simply excluded from that lever/key's average rather than
 * corrupting it with a 0/0 frequency.
 */
function weightedFeatureFrequencies(weightsByUci, legalMoves) {
  const weightedSums = {};
  for (const feature of FEATURE_KEYS) weightedSums[feature] = 0;
  let totalWeight = 0;

  for (const move of legalMoves) {
    const weight = weightsByUci[move.lan] ?? 0;
    if (!Number.isFinite(weight) || weight <= 0) continue;
    totalWeight += weight;
    const features = classifyMoveFeatures(move);
    for (const feature of FEATURE_KEYS) {
      if (features[feature]) weightedSums[feature] += weight;
    }
  }
  if (!Number.isFinite(totalWeight) || totalWeight <= 0) return null;

  const frequencies = {};
  for (const feature of FEATURE_KEYS) frequencies[feature] = weightedSums[feature] / totalWeight;
  return frequencies;
}

/** Softmax weights over `RankedLine.practicalScore` at `tau`, keyed by
 * `rootMove` (UCI) — the same max-subtraction-stable formula
 * `sampleRankedLines` uses internally (`botSampling.ts`), replicated here
 * only because that function returns a single drawn sample, not the
 * weight vector an expectation needs. */
function softmaxWeightsByUci(lines, tau) {
  const weights = {};
  if (lines.length === 0) return weights;
  const maxScore = Math.max(...lines.map((line) => line.practicalScore));
  for (const line of lines) {
    weights[line.rootMove] = Math.exp((line.practicalScore - maxScore) / tau);
  }
  return weights;
}

/**
 * Bug fix (found during Task 3 tuning): `isExchange` moves are ALWAYS also
 * `isCapture` (`classifyMoveFeatures`: `isExchange = isCapture && ...`), so
 * checking `isCapture` before `isExchange` made every simplifying trade
 * fall through to the tactical `HIGH_SPREAD_PROXY` branch — the intended
 * `LOW_SPREAD_PROXY` branch for exchanges was unreachable. `isExchange` is
 * now checked FIRST so a roughly-even trade is treated as quiet/simplifying
 * even though it is technically also a capture.
 */
function synthesizedChildScoreSpread(features) {
  if (features.isExchange) return LOW_SPREAD_PROXY;
  if (features.isCheck || features.isCapture || features.isPawnStorm) return HIGH_SPREAD_PROXY;
  if (features.isRetreat) return LOW_SPREAD_PROXY;
  return MID_SPREAD_PROXY;
}

/** Builds the score_shaping lane's synthesized `RankedLine[]` fixture — see
 * the module header for what is real (Maia policy) vs synthesized
 * (childScoreSpread) here. */
function buildSynthesizedLines(legalMoves, rawPolicyByUci) {
  return legalMoves.map((move) => {
    const features = classifyMoveFeatures(move);
    return {
      rootMove: move.lan,
      practicalScore: rawPolicyByUci[move.lan] ?? 0,
      objectiveEvalCp: null,
      objectiveEvalMate: null,
      modalPath: [],
      modalStats: [],
      visits: 0,
      childScoreSpread: synthesizedChildScoreSpread(features),
    };
  });
}

// ─── Accumulation across sampled positions ─────────────────────────────────────

function zeroFeatureSums() {
  const sums = {};
  for (const feature of FEATURE_KEYS) sums[feature] = 0;
  return sums;
}

function initAccumulator(styleNames) {
  const sums = {};
  const validCounts = {};
  for (const lever of LEVERS) {
    sums[lever] = { baseline: zeroFeatureSums() };
    validCounts[lever] = { baseline: 0 };
    for (const styleName of styleNames) {
      sums[lever][styleName] = zeroFeatureSums();
      validCounts[lever][styleName] = 0;
    }
  }
  return { sums, validCounts };
}

/** Folds one position's per-feature frequency vector (or `null`, skipped)
 * into the running `(lever, key)` average. */
function recordFrequency(accumulator, lever, key, frequencies) {
  if (frequencies === null) return;
  const bucket = accumulator.sums[lever][key];
  for (const feature of FEATURE_KEYS) bucket[feature] += frequencies[feature];
  accumulator.validCounts[lever][key] += 1;
}

/** Measures one sampled position across both levers and all 4 styles,
 * folding expected per-feature frequencies into `accumulator`. Extracted so
 * `main`'s loop body stays flat (nesting-depth discipline). */
async function measurePosition({ maiaCtx, Chess, fen, elo, styleNames, accumulator }) {
  const { rawPolicyByUci, legalMoves } = await maiaPolicyForFen(maiaCtx, fen, elo, Chess);
  if (legalMoves.length === 0) return; // defensive: terminal FEN in the opening corpus should not occur

  // Lane 1: prior reweighting (STYLE-03).
  recordFrequency(
    accumulator,
    'prior_reweighting',
    'baseline',
    weightedFeatureFrequencies(rawPolicyByUci, legalMoves),
  );
  for (const styleName of styleNames) {
    const style = BOT_STYLE_BUNDLES[styleName];
    const reweighted = applyStylePriorReweighting(rawPolicyByUci, fen, style);
    recordFrequency(
      accumulator,
      'prior_reweighting',
      styleName,
      weightedFeatureFrequencies(reweighted, legalMoves),
    );
  }

  // Lane 2: score shaping (STYLE-04), synthesized RankedLine[] fixture.
  const lines = buildSynthesizedLines(legalMoves, rawPolicyByUci);
  const baselineWeights = softmaxWeightsByUci(lines, SCORE_SHAPING_TAU);
  recordFrequency(
    accumulator,
    'score_shaping',
    'baseline',
    weightedFeatureFrequencies(baselineWeights, legalMoves),
  );
  for (const styleName of styleNames) {
    const style = BOT_STYLE_BUNDLES[styleName];
    const shaped = applyStyleScoreShaping(lines, style);
    const styledWeights = softmaxWeightsByUci(shaped, SCORE_SHAPING_TAU);
    recordFrequency(
      accumulator,
      'score_shaping',
      styleName,
      weightedFeatureFrequencies(styledWeights, legalMoves),
    );
  }
}

// ─── TSV emission ───────────────────────────────────────────────────────────────

function buildTimestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function averageOrZero(sum, validCount) {
  return validCount > 0 ? sum / validCount : 0;
}

function buildTsvRows(accumulator, styleNames) {
  const rows = [];
  for (const lever of LEVERS) {
    for (const styleName of styleNames) {
      for (const feature of FEATURE_KEYS) {
        const baselineFreq = averageOrZero(
          accumulator.sums[lever].baseline[feature],
          accumulator.validCounts[lever].baseline,
        );
        const styledFreq = averageOrZero(
          accumulator.sums[lever][styleName][feature],
          accumulator.validCounts[lever][styleName],
        );
        rows.push({
          style: styleName,
          lever,
          feature,
          baselineFreq: Number.parseFloat(baselineFreq.toFixed(4)),
          styledFreq: Number.parseFloat(styledFreq.toFixed(4)),
          delta: Number.parseFloat((styledFreq - baselineFreq).toFixed(4)),
        });
      }
    }
  }
  return rows;
}

function writeTsv(rows, outDir, n, elo, seed) {
  const timestamp = buildTimestamp();
  const tsvPath = path.join(outDir, `style-lever-measurement-${timestamp}.tsv`);
  fs.mkdirSync(outDir, { recursive: true });

  const lines = ['style\tlever\tfeature\tbaseline_freq\tstyled_freq\tdelta'];
  for (const row of rows) {
    lines.push([row.style, row.lever, row.feature, row.baselineFreq, row.styledFreq, row.delta].join('\t'));
  }
  lines.push('');
  lines.push(`# sampled_positions=${n} elo=${elo} seed=${seed} score_shaping_tau=${SCORE_SHAPING_TAU}`);

  fs.writeFileSync(tsvPath, `${lines.join('\n')}\n`, 'utf8');
  return tsvPath;
}

// ─── Main orchestration ────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { Chess } = await resolveFrontendModule('chess.js');

  console.log(
    `[style-lever-measurement] sampling ${args.n} positions from the opening-book corpus (seed=${args.seed})...`,
  );
  const positions = samplePositions(args.n, args.seed);

  console.log('[style-lever-measurement] loading Maia onnxruntime-web session...');
  const maiaCtx = await createMaiaSession();

  const styleNames = Object.keys(BOT_STYLE_BUNDLES);
  const accumulator = initAccumulator(styleNames);

  for (let i = 0; i < positions.length; i++) {
    process.stdout.write(`\r[style-lever-measurement] measuring position ${i + 1}/${positions.length}...`);
    await measurePosition({ maiaCtx, Chess, fen: positions[i], elo: args.elo, styleNames, accumulator });
  }
  process.stdout.write('\n');

  const rows = buildTsvRows(accumulator, styleNames);
  const tsvPath = writeTsv(rows, args.outDir, positions.length, args.elo, args.seed);

  console.log(`[style-lever-measurement] wrote ${tsvPath} (${rows.length} rows over ${positions.length} sampled positions)`);
  for (const lever of LEVERS) {
    console.log(`\n=== per-style identity-feature delta (${lever} lane) ===`);
    for (const styleName of styleNames) {
      const deltas = rows
        .filter((r) => r.style === styleName && r.lever === lever)
        .map((r) => `${r.feature}=${r.delta >= 0 ? '+' : ''}${r.delta}`)
        .join(' ');
      console.log(`${styleName}: ${deltas}`);
    }
  }
}

main().catch((err) => {
  console.error('[style-lever-measurement] FAILED:', err);
  process.exitCode = 1;
});

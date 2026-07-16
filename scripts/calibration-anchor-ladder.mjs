#!/usr/bin/env node
/**
 * calibration-anchor-ladder.mjs — anchor-vs-anchor two-pass adaptive
 * calibration orchestrator (Phase 173, Plan 02, D-08 standalone script; NOT
 * a mode inside `calibration-harness.mjs` — the bot harness is shaped around
 * bot cells, its static/dynamic anchor-window pruning mechanism, and
 * bot-cell resume keys, none of which apply here).
 *
 * Plays known-strength anchors (raw-Maia argmax rungs, Stockfish Skill-Level
 * moves) against EACH OTHER — never the bot — via the mover-agnostic
 * `playTwoMoverGame` (Phase 173 Plan 01) with two anchor movers, one per
 * color. Drives a two-pass adaptive schedule (D-01): a cheap PROBE pass
 * (`--games-per-probe`, default 8) places every D-02 candidate pair
 * provisionally, `selectMeasurePairs` keeps only pairs whose probe score
 * sits in the informative [0.2, 0.8] band, `checkConnectivity` (D-04)
 * enforces the played graph stays connected with >= 2 cross-family links
 * (re-targeting a lopsided cross-family probe to the next-nearer Maia rung
 * rather than dropping the only links joining the two families), and the
 * MEASURE pass extends every surviving pair from its 8 probe games to
 * `--games-per-measure` (default 24) total — reusing the probe games as the
 * first 8, never replaying a fresh 24 (D-01's info-efficiency directive).
 *
 * Writes a two-tier durable TSV (Pattern 3, WR-01): a raw per-game ledger
 * (`reports/data/anchor-ladder-<ts>.tsv`, one row streamed the instant each
 * game finishes — probe and measure both) plus a derived per-pair aggregate
 * (`-pairs.tsv` sibling) carrying the D-13 "internal scale — NOT human ELO"
 * caveat in its metadata footer. `--resume <prior-ledger.tsv>` reconstructs
 * per-pair progress by replaying the raw ledger (the resumable unit is ONE
 * (anchor_a, anchor_b) pair's played games so far, NOT a bot harness fixed
 * grid cell — 173-RESEARCH.md Pitfall 4) and fast-forwards the global
 * `gameIndex` through exactly the already-logged games so a resumed run's
 * remaining games keep the seeded RNG/opening/color sequence a from-scratch
 * run would have produced.
 *
 * D-11: the actual multi-hour run against this script is Plan 04's job —
 * this script is the tooling, proven here only for syntax + import
 * correctness (no real engines in this plan's `<verify>`).
 *
 * Usage:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-anchor-ladder.mjs \
 *     [--anchors maia700,maia1100,maia1500,maia1900,maia2300,sf0,sf3,sf5,sf8,sf10] \
 *     [--games-per-probe 8] [--games-per-measure 24] [--seed 1] \
 *     [--stockfish-procs 4] [--out-dir reports/data] \
 *     [--resume reports/data/anchor-ladder-<ts>.tsv]
 */
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

import {
  setupHarnessEngines,
  requireFlagValue,
  parsePositiveIntFlag,
  parseAnchorSpec,
  deriveGameSeed,
  resolveGitSha,
  buildTimestamp,
} from './calibration-harness.mjs';
import { STOCKFISH_POOL_DEFAULT_SIZE } from './lib/stockfish-pool.mjs';
import { playTwoMoverGame } from './lib/calibration-game-loop.mjs';
import { maiaArgmaxMove, anchorRatingFor } from './lib/calibration-anchors.mjs';
import { OPENING_BOOK, assertOpeningBookUciPrefixes } from './lib/calibration-openings.mjs';
import {
  buildCandidateGraph,
  checkConnectivity,
  rescueConnectivity,
  scoreInInformativeBand,
  selectMeasurePairs,
  canonicalPair,
  pairKey,
  isCrossFamilyPair,
} from './lib/calibration-anchor-schedule.mjs';

import { mulberry32 } from '@/lib/engine/botSampling';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(__dirname, '..');

// ─── D-01/D-02/D-03 CLI defaults ────────────────────────────────────────────

const DEFAULT_ANCHOR_TOKENS = [
  'maia700',
  'maia1100',
  'maia1500',
  'maia1900',
  'maia2300',
  'sf0',
  'sf3',
  'sf5',
  'sf8',
  'sf10',
];
/** D-01: ~8 games to provisionally place a candidate pair before deciding whether it's worth measuring. */
const DEFAULT_GAMES_PER_PROBE = 8;
/** D-03: 24 games per measured pair (SE ~= +/-71; the joint fit pools all pairs for per-anchor precision). */
const DEFAULT_GAMES_PER_MEASURE = 24;
const DEFAULT_SEED = 1;
const DEFAULT_OUT_DIR = path.join(REPO_ROOT, 'reports/data');

/** Bounded re-target attempts (D-04 fallback) before failing loud on a disconnected/under-cross-linked graph. */
const MAX_RETARGET_ROUNDS = 3;

/** D-13: verbatim caveat carried into every artifact this script produces. */
const D13_CAVEAT = 'internal scale — NOT human ELO; downstream fit fixes maia1500 = 1500';

// ─── CLI parsing (WR-02 discipline, reusing the harness's fail-loud helpers) ─

export function parseArgs(argv) {
  const args = {
    anchors: DEFAULT_ANCHOR_TOKENS,
    gamesPerProbe: DEFAULT_GAMES_PER_PROBE,
    gamesPerMeasure: DEFAULT_GAMES_PER_MEASURE,
    seed: DEFAULT_SEED,
    stockfishProcs: STOCKFISH_POOL_DEFAULT_SIZE,
    outDir: DEFAULT_OUT_DIR,
    resume: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[i + 1];
    switch (key) {
      case 'anchors':
        args.anchors = requireFlagValue(value, key)
          .split(',')
          .map((s) => s.trim());
        i++;
        break;
      case 'games-per-probe':
        args.gamesPerProbe = parsePositiveIntFlag(value, key);
        i++;
        break;
      case 'games-per-measure':
        args.gamesPerMeasure = parsePositiveIntFlag(value, key);
        i++;
        break;
      case 'stockfish-procs':
        args.stockfishProcs = parsePositiveIntFlag(value, key);
        i++;
        break;
      case 'out-dir':
        args.outDir = path.resolve(requireFlagValue(value, key));
        i++;
        break;
      case 'resume': {
        const resumePath = path.resolve(requireFlagValue(value, key));
        if (!resumePath.endsWith('.tsv')) {
          throw new Error(
            `--resume: expected a .tsv file, got ${resumePath} — the pairs sibling path is derived by extension`,
          );
        }
        args.resume = resumePath;
        i++;
        break;
      }
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
      default:
        throw new Error(`Unknown flag --${key}`);
    }
  }
  return args;
}

// ─── Anchor mover dispatch (reuses calibration-anchors.mjs verbatim) ────────

/** Builds a `(fen, rng) => Promise<uci>` mover closure for one anchor — same functions BOTH sides call. */
function buildMover(providers, pool, anchorSpec) {
  if (anchorSpec.kind === 'maia') {
    return (fen, rng) => maiaArgmaxMove(providers, fen, anchorSpec.rungElo, rng);
  }
  return (fen) => pool.skillMove(fen, anchorSpec.skillLevel);
}

// ─── Raw per-game ledger (D-12 artifact 1, WR-01 durability) ───────────────

/** Shared column contract with Plan 03's `load_games` (173-02-PLAN.md) — clean header, no leading comment. */
const RAW_LEDGER_COLUMNS = [
  'pass',
  'anchor_white',
  'anchor_black',
  'result',
  'reason',
  'plies',
  'game_index',
  'opening',
  'seed',
  'git_sha',
];

function ledgerRowLine(row) {
  return [row.pass, row.anchorWhite, row.anchorBlack, row.result, row.reason, row.plies, row.gameIndex, row.opening, row.seed, row.gitSha].join(
    '\t',
  );
}

/** Opens the raw ledger writer — one durable `writeRow` per completed game, both probe and measure. */
function openLedgerWriter(filePath, { append = false } = {}) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const stream = fs.createWriteStream(filePath, { encoding: 'utf8', flags: append ? 'a' : 'w' });
  if (!append) stream.write(`${RAW_LEDGER_COLUMNS.join('\t')}\n`);
  return {
    writeRow(row) {
      stream.write(`${ledgerRowLine(row)}\n`);
    },
    close() {
      return new Promise((resolve, reject) => {
        stream.end((err) => (err ? reject(err) : resolve()));
      });
    },
  };
}

// ─── One game between two anchors, color-assigned by the global game index ─

/**
 * Plays `count` NEW games between `anchorA`/`anchorB` (canonical pair
 * order), continuing the shared `state.gameIndex` counter (D-09-style
 * seeded determinism: color/opening/PRNG all derive from this single global
 * index, so `--resume` fast-forwarding it reproduces byte-identical games).
 * Tallies wins from `anchorA`'s POV and streams every game's row to the
 * ledger the instant it finishes (WR-01).
 */
async function playPairGames({ Chess, pool, providers, anchorA, anchorB, count, pass, args, gitSha, state, ledgerWriter }) {
  const moverA = buildMover(providers, pool, anchorA);
  const moverB = buildMover(providers, pool, anchorB);
  let aWins = 0;
  let draws = 0;
  let bWins = 0;

  for (let i = 0; i < count; i++) {
    const idx = state.gameIndex;
    const opening = OPENING_BOOK[idx % OPENING_BOOK.length];
    const aIsWhite = idx % 2 === 0;
    const gameRng = mulberry32(deriveGameSeed(args.seed, idx));
    const moverWhite = aIsWhite ? moverA : moverB;
    const moverBlack = aIsWhite ? moverB : moverA;

    console.log(
      `[calibration-anchor-ladder] game ${idx}: pass=${pass} ${anchorA.label} vs ${anchorB.label} ` +
        `opening=${opening.name} aIsWhite=${aIsWhite}`,
    );
    const result = await playTwoMoverGame({ Chess, pool, moverWhite, moverBlack, startFen: opening.fen, gameRng });
    console.log(`[calibration-anchor-ladder]   result=${result.result} reason=${result.reason} plies=${result.plies}`);

    const anchorWhite = aIsWhite ? anchorA.label : anchorB.label;
    const anchorBlack = aIsWhite ? anchorB.label : anchorA.label;
    ledgerWriter.writeRow({
      pass,
      anchorWhite,
      anchorBlack,
      result: result.result,
      reason: result.reason,
      plies: result.plies,
      gameIndex: idx,
      opening: opening.name,
      seed: args.seed,
      gitSha,
    });

    if (result.result === 'draw') {
      draws++;
    } else {
      const aWon = (result.result === 'white_win') === aIsWhite;
      if (aWon) aWins++;
      else bWins++;
    }
    state.gameIndex++;
  }

  return { aWins, draws, bWins, games: count };
}

// ─── Per-pair stat accumulation (probe + measure games, anchor_a POV) ──────

export function ensurePairStats(pairStats, key, a, b) {
  let stats = pairStats.get(key);
  if (!stats) {
    stats = { anchorA: a, anchorB: b, games: 0, aWins: 0, draws: 0, bWins: 0, probeGames: 0, measureGames: 0 };
    pairStats.set(key, stats);
  }
  return stats;
}

export function mergeDeltaIntoStats(stats, delta, passField) {
  stats.games += delta.games;
  stats.aWins += delta.aWins;
  stats.draws += delta.draws;
  stats.bWins += delta.bWins;
  stats[passField] += delta.games;
}

export function buildScoreMap(pairStats) {
  const scoreByPair = {};
  for (const [key, stats] of pairStats.entries()) {
    if (stats.games === 0) continue;
    scoreByPair[key] = (stats.aWins + 0.5 * stats.draws) / stats.games;
  }
  return scoreByPair;
}

// ─── D-01 PROBE pass: play games-per-probe on every not-yet-probed candidate ─

async function probePass({ Chess, pool, providers, pairs, specByLabel, args, gitSha, state, ledgerWriter, pairStats }) {
  for (const [a, b] of pairs) {
    const key = pairKey(a, b);
    const stats = ensurePairStats(pairStats, key, a, b);
    const remaining = args.gamesPerProbe - stats.probeGames;
    if (remaining <= 0) continue; // already probed (e.g. resumed from a prior run)
    const delta = await playPairGames({
      Chess,
      pool,
      providers,
      anchorA: specByLabel.get(a),
      anchorB: specByLabel.get(b),
      count: remaining,
      pass: 'probe',
      args,
      gitSha,
      state,
      ledgerWriter,
    });
    mergeDeltaIntoStats(stats, delta, 'probeGames');
  }
}

// ─── D-04 re-target fallback: next-nearer untried Maia rung for a dropped SF pair ─

export function buildTriedMaiaMap(pairs) {
  const tried = new Map();
  for (const [a, b] of pairs) {
    if (!isCrossFamilyPair(a, b)) continue;
    const sfLabel = a.startsWith('maia') ? b : a;
    const maiaLabel = a.startsWith('maia') ? a : b;
    if (!tried.has(sfLabel)) tried.set(sfLabel, new Set());
    tried.get(sfLabel).add(maiaLabel);
  }
  return tried;
}

/** For every dropped cross-family pair, propose the next-nearest UNTRIED Maia rung for that SF anchor (D-04). */
export function computeRetargets(droppedKeys, specByLabel, anchorSpecs, triedMaiaForSf) {
  const maiaAnchors = anchorSpecs.filter((spec) => spec.kind === 'maia');
  const retargets = [];
  for (const key of droppedKeys) {
    const [a, b] = key.split('|');
    if (!isCrossFamilyPair(a, b)) continue;
    const sfLabel = a.startsWith('maia') ? b : a;
    const sfSpec = specByLabel.get(sfLabel);
    const tried = triedMaiaForSf.get(sfLabel) ?? new Set();
    const nextMaia = maiaAnchors
      .filter((maia) => !tried.has(maia.label))
      .sort((m1, m2) => Math.abs(anchorRatingFor(m1) - anchorRatingFor(sfSpec)) - Math.abs(anchorRatingFor(m2) - anchorRatingFor(sfSpec)))[0];
    if (nextMaia) {
      tried.add(nextMaia.label);
      triedMaiaForSf.set(sfLabel, tried);
      retargets.push(canonicalPair(sfLabel, nextMaia.label));
    }
  }
  return retargets;
}

export function mergeUniquePairs(...pairLists) {
  const seen = new Set();
  const merged = [];
  for (const pairs of pairLists) {
    for (const [a, b] of pairs) {
      const key = pairKey(a, b);
      if (seen.has(key)) continue;
      seen.add(key);
      merged.push([a, b]);
    }
  }
  return merged;
}

export function isGraphConnected(keptPairKeys, allLabels) {
  try {
    checkConnectivity(
      keptPairKeys.map((key) => key.split('|')),
      allLabels,
    );
    return true;
  } catch {
    return false;
  }
}

/**
 * D-01/D-02/D-04: builds the candidate graph, probes it, gates via
 * `selectMeasurePairs`, and re-targets dropped cross-family pairs (probing
 * the next-nearer untried Maia rung) until the KEPT set is connected with
 * >= 2 cross-family links — or the re-target budget is exhausted, in which
 * case `checkConnectivity` throws (Pitfall 1: never proceed on a
 * disconnected/under-cross-linked graph). `checkConnectivity` runs BEFORE
 * any measure-pass game is played (D-04's stated ordering).
 */
async function scheduleGraph({ Chess, pool, providers, anchorSpecs, args, gitSha, state, ledgerWriter, pairStats, extraPairs }) {
  const specByLabel = new Map(anchorSpecs.map((spec) => [spec.label, spec]));
  const allLabels = anchorSpecs.map((spec) => spec.label);
  const baseCandidatePairs = buildCandidateGraph(anchorSpecs);
  const triedMaiaForSf = buildTriedMaiaMap([...baseCandidatePairs, ...extraPairs]);

  let pairsToProbe = mergeUniquePairs(baseCandidatePairs, extraPairs);
  let kept = [];

  for (let round = 0; round <= MAX_RETARGET_ROUNDS; round++) {
    await probePass({ Chess, pool, providers, pairs: pairsToProbe, specByLabel, args, gitSha, state, ledgerWriter, pairStats });

    const gate = selectMeasurePairs(buildScoreMap(pairStats));
    kept = gate.kept;
    const retargets = computeRetargets(gate.dropped, specByLabel, anchorSpecs, triedMaiaForSf);
    const connected = isGraphConnected(kept, allLabels);

    if (connected && retargets.length === 0) {
      return { kept, specByLabel };
    }
    if (retargets.length === 0) {
      // No more re-target candidates left — band-relaxing rescue, then fail loud if still broken (Pitfall 1).
      return { kept: rescueKeptOrFail(kept, pairStats, allLabels), specByLabel };
    }
    pairsToProbe = retargets;
  }

  // Re-target budget exhausted — rescue, then final fail-loud connectivity check (never proceed silently).
  return { kept: rescueKeptOrFail(kept, pairStats, allLabels), specByLabel };
}

/**
 * D-04 rescue wrapper: when re-targeting is exhausted but the kept graph is
 * disconnected, add back the dropped probed edges closest to the informative
 * band until connected (they get the full measure budget like any kept
 * pair), then run the fail-loud guard. Added after the 2026-07-15 run burned
 * its whole probe budget and died here: {maia700, sf0} had no informative
 * link outward and no nearer rung to re-target to.
 */
function rescueKeptOrFail(kept, pairStats, allLabels) {
  const rescue = rescueConnectivity(kept, buildScoreMap(pairStats), allLabels);
  if (rescue.rescued.length > 0) {
    console.log(
      `[calibration-anchor-ladder] connectivity rescue: keeping out-of-band pair(s) ${rescue.rescued.join(', ')} to reconnect the anchor graph (D-04 fallback)`,
    );
  }
  checkConnectivity(
    rescue.kept.map((key) => key.split('|')),
    allLabels,
  );
  return rescue.kept;
}

// ─── D-03/D-01 MEASURE pass: extend each kept pair from probe to 24 total ──

/** Extends every kept pair from its already-played (probe) games to `args.gamesPerMeasure` total — never a fresh 24. */
async function measurePass({ Chess, pool, providers, kept, specByLabel, args, gitSha, state, ledgerWriter, pairStats }) {
  for (const key of kept) {
    const stats = pairStats.get(key);
    const remaining = args.gamesPerMeasure - stats.games;
    if (remaining <= 0) continue;
    const delta = await playPairGames({
      Chess,
      pool,
      providers,
      anchorA: specByLabel.get(stats.anchorA),
      anchorB: specByLabel.get(stats.anchorB),
      count: remaining,
      pass: 'measure',
      args,
      gitSha,
      state,
      ledgerWriter,
    });
    mergeDeltaIntoStats(stats, delta, 'measureGames');
  }
}

// ─── Per-pair aggregate TSV (D-12 artifact 1, D-13 caveat) ──────────────────

const PAIRS_COLUMNS = ['anchor_a', 'anchor_b', 'games', 'a_wins', 'draws', 'b_wins', 'score_a', 'pass', 'informative'];

export function pairsAggregateRows(pairStats, keptSet) {
  const rows = [];
  for (const stats of pairStats.values()) {
    const scoreA = stats.games > 0 ? (stats.aWins + 0.5 * stats.draws) / stats.games : 0;
    const key = pairKey(stats.anchorA, stats.anchorB);
    rows.push({
      anchorA: stats.anchorA,
      anchorB: stats.anchorB,
      games: stats.games,
      aWins: stats.aWins,
      draws: stats.draws,
      bWins: stats.bWins,
      scoreA,
      pass: keptSet.has(key) ? 'measure' : 'probe',
      informative: scoreInInformativeBand(scoreA),
    });
  }
  return rows;
}

function writePairsAggregateFile(filePath, rows, meta) {
  const lines = [PAIRS_COLUMNS.join('\t')];
  for (const row of rows) {
    lines.push(
      [row.anchorA, row.anchorB, row.games, row.aWins, row.draws, row.bWins, row.scoreA.toFixed(4), row.pass, row.informative].join('\t'),
    );
  }
  lines.push('');
  lines.push('metadata\tvalue');
  lines.push(`seed\t${meta.seed}`);
  lines.push(`stockfish_procs\t${meta.stockfishProcs}`);
  lines.push(`git_sha\t${meta.gitSha}`);
  lines.push(`caveat\t${D13_CAVEAT}`);

  const content = `${lines.join('\n')}\n`;
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf8');

  console.log(`\n=== per-pair aggregate (D-13: ${D13_CAVEAT}) ===`);
  console.log(content);
}

// ─── --resume: replay the raw ledger, keyed on pair identity (Pitfall 4) ───

function parsePriorLedgerRow(line, filePath) {
  const cells = line.split('\t');
  if (cells.length !== RAW_LEDGER_COLUMNS.length) {
    throw new Error(`--resume: malformed row in ${filePath} (${cells.length} columns): ${line}`);
  }
  const [pass, anchorWhite, anchorBlack, result, reason, plies, gameIndex, opening, seed, gitSha] = cells;
  return {
    pass,
    anchorWhite,
    anchorBlack,
    result,
    reason,
    plies: Number.parseInt(plies, 10),
    gameIndex: Number.parseInt(gameIndex, 10),
    opening,
    seed: Number.parseInt(seed, 10),
    gitSha,
  };
}

/** Reads + validates a prior raw ledger — refuses (WR-02) a truncated final line or a schema mismatch. */
function readPriorLedgerRows(filePath) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new Error(`--resume: cannot read prior TSV ${filePath}: ${err.message}`);
  }
  if (!content.endsWith('\n')) {
    throw new Error(`--resume: prior TSV ${filePath} has a truncated final line (no trailing newline) — cannot safely resume`);
  }
  const lines = content.split('\n').filter((line) => line.length > 0);
  if (lines.length === 0) throw new Error(`--resume: prior TSV ${filePath} is empty`);

  const header = lines[0].split('\t');
  if (header.length !== RAW_LEDGER_COLUMNS.length || RAW_LEDGER_COLUMNS.some((col, i) => header[i] !== col)) {
    throw new Error(`--resume: prior TSV ${filePath} header does not match the current schema`);
  }
  return lines.slice(1).map((line) => parsePriorLedgerRow(line, filePath));
}

function validateResumeSeed(rows, seed) {
  for (const row of rows) {
    if (row.seed !== seed) {
      throw new Error(`--resume: prior seed=${row.seed} differs from current --seed=${seed} — refusing to resume a different experiment`);
    }
  }
}

/** Reconstructs `pairStats` + fast-forwards `state.gameIndex` from a prior ledger's already-logged games. */
export function applyPriorRowsToState(rows, pairStats, state) {
  let maxGameIndex = -1;
  for (const row of rows) {
    const [a, b] = canonicalPair(row.anchorWhite, row.anchorBlack);
    const key = pairKey(a, b);
    const stats = ensurePairStats(pairStats, key, a, b);
    stats.games++;
    if (row.pass === 'probe') stats.probeGames++;
    else stats.measureGames++;

    if (row.result === 'draw') {
      stats.draws++;
    } else {
      const aIsWhite = row.anchorWhite === a;
      const aWon = (row.result === 'white_win') === aIsWhite;
      if (aWon) stats.aWins++;
      else stats.bWins++;
    }
    if (row.gameIndex > maxGameIndex) maxGameIndex = row.gameIndex;
  }
  state.gameIndex = maxGameIndex + 1;
}

export function pairsFromRows(rows) {
  const seen = new Set();
  const pairs = [];
  for (const row of rows) {
    const [a, b] = canonicalPair(row.anchorWhite, row.anchorBlack);
    const key = pairKey(a, b);
    if (seen.has(key)) continue;
    seen.add(key);
    pairs.push([a, b]);
  }
  return pairs;
}

// ─── Main orchestration ─────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const anchorSpecs = args.anchors.map(parseAnchorSpec);
  const gitSha = resolveGitSha();

  const timestamp = buildTimestamp();
  const ledgerPath = args.resume ?? path.join(args.outDir, `anchor-ladder-${timestamp}.tsv`);
  const pairsPath = ledgerPath.replace(/\.tsv$/, '-pairs.tsv');

  let priorRows = [];
  if (args.resume) {
    priorRows = readPriorLedgerRows(args.resume);
    validateResumeSeed(priorRows, args.seed);
    console.log(`[calibration-anchor-ladder] --resume ${args.resume}: replaying ${priorRows.length} already-logged games`);
  }

  // CR-01: guard the entire bring-up sequence (pool spawn through ledger-writer
  // creation) in one try/catch — an `openLedgerWriter` failure after the pool
  // spawned must still terminate the already-live Stockfish processes.
  let pool;
  let providers;
  let Chess;
  let ledgerWriter;
  try {
    ({ providers, pool, Chess } = await setupHarnessEngines({ stockfishProcs: args.stockfishProcs }));
    assertOpeningBookUciPrefixes(Chess);
    ledgerWriter = openLedgerWriter(ledgerPath, { append: Boolean(args.resume) });
  } catch (err) {
    pool?.quitAll();
    throw err;
  }

  const state = { gameIndex: 0 };
  const pairStats = new Map();
  applyPriorRowsToState(priorRows, pairStats, state);
  const extraPairs = pairsFromRows(priorRows);

  try {
    const { kept, specByLabel } = await scheduleGraph({
      Chess,
      pool,
      providers,
      anchorSpecs,
      args,
      gitSha,
      state,
      ledgerWriter,
      pairStats,
      extraPairs,
    });
    await measurePass({ Chess, pool, providers, kept, specByLabel, args, gitSha, state, ledgerWriter, pairStats });

    const rows = pairsAggregateRows(pairStats, new Set(kept));
    writePairsAggregateFile(pairsPath, rows, { seed: args.seed, stockfishProcs: args.stockfishProcs, gitSha });
    console.log(`[calibration-anchor-ladder] wrote ${ledgerPath}`);
    console.log(`[calibration-anchor-ladder] wrote ${pairsPath}`);
  } finally {
    pool.quitAll();
    await ledgerWriter.close();
  }
}

// Only auto-run when executed directly (not when imported, e.g. by a future check/fit script).
if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error('[calibration-anchor-ladder] FAILED:', err);
    process.exitCode = 1;
  });
}

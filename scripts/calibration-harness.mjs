#!/usr/bin/env node
/**
 * calibration-harness.mjs — bot-vs-anchor game loop, pool-backed grid sweep,
 * and durable strength-map TSV emission (Phase 168, Plans 02/03).
 *
 * The bot's ENTIRE move selection is one call to the LIVE `selectBotMove`
 * (`@/lib/engine/selectBotMove`, imported via the `@/` alias hook) with
 * `deps.search` OMITTED so it defaults to the real `mctsSearch` — identical
 * wiring to the app (CAL-02). This file never branches on `blend` and never
 * reimplements any search/argmax/sampling logic for the bot's own moves; the
 * only "local" move-choosing logic here is the ANCHOR movers
 * (`scripts/lib/calibration-anchors.mjs`), which are a structurally different
 * concern — known-strength opponents the bot plays AGAINST, not the bot's own
 * regime dispatch.
 *
 * D-10 bounds every game with three cutoffs, checked in this order after
 * every ply: (1) chess.js terminal conditions (mate/stalemate/threefold/
 * fifty-move/insufficient material), (2) a single-line Stockfish adjudication
 * eval sustained past `ADJUDICATION_CP_THRESHOLD` for `ADJUDICATION_SUSTAIN_PLIES`
 * consecutive plies, (3) a hard `PLY_CAP` (adjudicated by the last eval sign,
 * draw if inside the threshold). D-11 fixes the per-move search budget as a
 * harness constant mirroring the app's own `useFlawChessEngine.ts` defaults.
 *
 * **Re-scoped by Plan 03 (168-03-PLAN.md, spike go/no-go D-03):** the CAL-03
 * spike found `grade()` serialization on a SINGLE shared Stockfish process is
 * the throughput bottleneck (168-RESEARCH.md Pitfall 3), not Maia/ONNX. This
 * file now grades/anchors/adjudicates through an N-process
 * `scripts/lib/stockfish-pool.mjs` pool (`--stockfish-procs`, default
 * `STOCKFISH_POOL_DEFAULT_SIZE=4`) — `SearchBudget.concurrency` is set to the
 * pool size (`pool.size`), superseding Plan 02's `SEARCH_CONCURRENCY=1`
 * (that constant existed only because there was a single shared process; with
 * N independent processes, concurrency > 1 is safe — each process still
 * serves only one `go` at a time).
 *
 * 168-RESEARCH.md Pitfall 2: every engine drawn from the pool still serves
 * multiple roles (bot grading / anchor moves / adjudication) over its own
 * lifetime — every `go` any caller sends resets every option it depends on
 * first (Skill Level/UCI_LimitStrength/MultiPV), so a prior anchor's weakened
 * skill level can never leak into a grading or adjudication `go` on that same
 * engine.
 *
 * This plan (03) owns the pool + the outer grid sweep + TSV emission
 * (CAL-01), gated by Plan 02's D-03 throughput spike + this plan's own
 * pool re-measurement.
 *
 * Usage:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs \
 *     [--elo 1100,1500,1900] [--blends 0,0.5,1] \
 *     [--anchors maia1100,maia1300,maia1500,maia1700,maia1900,sf0,sf3,sf5] \
 *     [--games-per-cell 20] [--seed 1] [--out-dir reports/data] [--stockfish-procs 4] \
 *     [--resume reports/data/calibration-harness-<ts>.tsv]
 *
 * **SEED-097 resumability:** a killed sweep leaves a durable prior TSV whose
 * completed `(bot_elo, bot_blend, anchor)` cells form a grid-order prefix (one
 * `writeRow` per cell, WR-01). `--resume <prior.tsv>` re-invokes the SAME
 * command, reads that file, skips every already-swept cell, and APPENDS the
 * remaining cells to the same file so the finished map is byte-identical to an
 * uninterrupted run. The skip fast-forwards the GLOBAL `gameIndex` through each
 * skipped cell (never resets it) so every remaining cell keeps the opening/
 * color/seed it would have had in a from-scratch run (D-09). Resuming refuses
 * (throws) on any mismatch of `--games-per-cell`, `--seed`, the D-11 budget, or
 * the grid axes vs the prior TSV — a changed experiment is a footgun, not a
 * feature.
 */
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

import { createMaiaSession, resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { createStockfishPool, STOCKFISH_POOL_DEFAULT_SIZE } from './lib/stockfish-pool.mjs';
import { makeNodeProviders, adjudicationFallbackStats } from './lib/calibration-providers.mjs';
import { maiaArgmaxMove, SF_SKILL_ELO, anchorRatingFor } from './lib/calibration-anchors.mjs';
import { OPENING_BOOK, assertOpeningBookUciPrefixes } from './lib/calibration-openings.mjs';
import { combineAnchorEstimates, wasScoreClamped } from './lib/calibration-elo.mjs';

import { selectBotMove } from '@/lib/engine/selectBotMove';
import { mulberry32 } from '@/lib/engine/botSampling';
import {
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_CONCURRENCY,
  FLAWCHESS_BOT_STOP_RULE,
} from '@/lib/engine/botBudget';
import { uciToSquares } from '@/lib/sanToSquares';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(__dirname, '..');

// ─── D-11: fixed per-move search budget (mirrors useFlawChessEngine.ts) ────────

/** Node-expansion budget (mirrors `FLAWCHESS_ENGINE_MAX_NODES` — useFlawChessEngine.ts line 39). */
export const FLAWCHESS_ENGINE_MAX_NODES = 400;

/**
 * Base of the per-game analyze deep-link. `?line=` replays UCI moves from the
 * STANDARD start (analysisUrl.ts) — and `?fen=` wins over `?line=` (they never
 * compose) — so the link must be the opening-book uci prefix + the game's own
 * moves, never the game moves alone (games start from mid-opening book FENs).
 */
const ANALYSIS_LINE_URL_BASE = 'https://flawchess.com/analysis?line=';

/** flawchess.com deep-link replaying the full game (opening prefix + played moves) from move 1. */
function analysisLineUrl(opening, moveUcis) {
  return `${ANALYSIS_LINE_URL_BASE}${[...opening.uci, ...moveUcis].join(',')}`;
}

/** Search-tree ply depth cap (mirrors `FLAWCHESS_ENGINE_MAX_PLIES` — useFlawChessEngine.ts line 45). */
export const FLAWCHESS_ENGINE_MAX_PLIES = 8;

// ─── Phase 168.5 D-05/D-07/D-09: bot-play budget (shared with the app) ────────
//
// Imported above from `@/lib/engine/botBudget` — the SAME module the app's
// `useFlawChessEngine.ts` re-exports — replacing the former hand-maintained
// mirror block: a one-sided retune of either side calibrated a bot that does
// not ship (T-168.5-04-01). Re-exported so the determinism/pruning checks
// keep importing them from this module.
export { FLAWCHESS_BOT_MAX_NODES, FLAWCHESS_BOT_MAX_PLIES, FLAWCHESS_BOT_CONCURRENCY, FLAWCHESS_BOT_STOP_RULE };

// ─── D-10: three cost cutoffs (all named constants, tunable/[ASSUMED] per 168-RESEARCH.md Open Question 3) ─

/** |white-POV cp| at/above which one side is considered "sustained decisive" for adjudication. */
export const ADJUDICATION_CP_THRESHOLD = 600;

/** Consecutive plies the SAME side must stay past the threshold before adjudicating (avoids a transient tactical spike). */
export const ADJUDICATION_SUSTAIN_PLIES = 4;

/** Hard ply cap — adjudicated by the final eval sign (draw if inside the threshold) if reached first. */
export const PLY_CAP = 120;

// ─── D-09: seeded per-game PRNG derivation + opening/color assignment ──────────

/** Prime multiplier spacing adjacent game indices into well-separated mulberry32 seeds. */
const SEED_GAME_INDEX_MULTIPLIER = 1_000_003;

function deriveGameSeed(seed, gameIndex) {
  return (seed + gameIndex * SEED_GAME_INDEX_MULTIPLIER) >>> 0;
}

// ─── Anchor token prefixes (declared before DEFAULT_ANCHOR_TOKENS builds the maia ladder) ──

const SF_ANCHOR_PREFIX = 'sf';
const MAIA_ANCHOR_PREFIX = 'maia';

// ─── D-07 default grid (CLI defaults AND the CAL-03 spike's projection basis) ──

const DEFAULT_BOT_ELOS = [1100, 1500, 1900];
const DEFAULT_BOT_BLENDS = [0, 0.5, 1];
// Maia human-imitation ladder sampled every 200 ELO (maia600, 800, .. 2600 —
// every other 100-rung of MAIA_ELO_LADDER) plus three Stockfish rungs for the
// superhuman end Maia can't reach. The 200-ELO spacing keeps the anchor count
// manageable; the ANCHOR_ELO_WINDOW + dynamic-cutoff pruning further trim
// anchors too far from each bot cell to be informative.
const ANCHOR_MAIA_ELO_STEP = 200;
const DEFAULT_ANCHOR_TOKENS = [
  ...MAIA_ELO_LADDER.filter((elo) => (elo - MAIA_ELO_LADDER[0]) % ANCHOR_MAIA_ELO_STEP === 0).map(
    (elo) => `${MAIA_ANCHOR_PREFIX}${elo}`,
  ),
  'sf0',
  'sf3',
  'sf5',
];
const DEFAULT_GAMES_PER_CELL = 20;
const DEFAULT_SEED = 1;
const DEFAULT_OUT_DIR = path.join(REPO_ROOT, 'reports/data');

/** D-03: the WASM-vs-fallback go/no-go budget — tunable/[ASSUMED], Claude's discretion. */
const WASM_WALL_CLOCK_BUDGET_HOURS = 8;

const SECONDS_PER_HOUR = 3600;

// ─── CLI parsing (WR-02 discipline: every value-consuming flag validates) ──────

/** Returns the flag's value, or throws if it's missing (absent or itself a --flag). */
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

function parseIntList(raw, key) {
  return raw.split(',').map((token) => {
    const parsed = Number.parseInt(token.trim(), 10);
    if (!Number.isInteger(parsed)) {
      throw new Error(`Invalid --${key} entry ${JSON.stringify(token)}: expected an integer`);
    }
    return parsed;
  });
}

function parseFloatList(raw, key) {
  return raw.split(',').map((token) => {
    const parsed = Number.parseFloat(token.trim());
    if (!Number.isFinite(parsed)) {
      throw new Error(`Invalid --${key} entry ${JSON.stringify(token)}: expected a number`);
    }
    return parsed;
  });
}

function parseArgs(argv) {
  const args = {
    elo: DEFAULT_BOT_ELOS,
    blends: DEFAULT_BOT_BLENDS,
    anchors: DEFAULT_ANCHOR_TOKENS,
    gamesPerCell: DEFAULT_GAMES_PER_CELL,
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
      case 'elo':
        args.elo = parseIntList(requireFlagValue(value, key), key);
        i++;
        break;
      case 'blends':
        args.blends = parseFloatList(requireFlagValue(value, key), key);
        i++;
        break;
      case 'anchors':
        args.anchors = requireFlagValue(value, key)
          .split(',')
          .map((s) => s.trim());
        i++;
        break;
      case 'games-per-cell':
        args.gamesPerCell = parsePositiveIntFlag(value, key);
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
        // The summary sibling path is derived in main() by replacing the
        // `.tsv` extension; on a non-.tsv resume path that replace is a
        // no-op, summaryPath === mainTsvPath, and emitEloSummary would
        // TRUNCATE the just-appended primary results file. Refuse up front.
        const resumePath = path.resolve(requireFlagValue(value, key));
        if (!resumePath.endsWith('.tsv')) {
          throw new Error(
            `--resume: expected a .tsv file, got ${resumePath} — the summary sibling path is derived by extension`,
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

function validateEloRungs(elos) {
  for (const elo of elos) {
    if (!MAIA_ELO_LADDER.includes(elo)) {
      throw new Error(`Invalid --elo value ${elo}: not a member of MAIA_ELO_LADDER (${MAIA_ELO_LADDER.join(',')})`);
    }
  }
}

function validateBlends(blends) {
  for (const blend of blends) {
    if (!(blend >= 0 && blend <= 1)) {
      throw new Error(`Invalid --blends value ${blend}: expected a number in [0,1]`);
    }
  }
}

/** Parses one `--anchors` token into `{ kind: 'sf', skillLevel }` or `{ kind: 'maia', rungElo }`. */
export function parseAnchorSpec(token) {
  if (token.startsWith(SF_ANCHOR_PREFIX)) {
    const skillLevel = Number.parseInt(token.slice(SF_ANCHOR_PREFIX.length), 10);
    if (!Number.isInteger(skillLevel) || !(skillLevel in SF_SKILL_ELO)) {
      throw new Error(`Invalid --anchors token ${JSON.stringify(token)}: unknown Stockfish skill level`);
    }
    return { kind: 'sf', skillLevel, label: token };
  }
  if (token.startsWith(MAIA_ANCHOR_PREFIX)) {
    const rungElo = Number.parseInt(token.slice(MAIA_ANCHOR_PREFIX.length), 10);
    if (!MAIA_ELO_LADDER.includes(rungElo)) {
      throw new Error(`Invalid --anchors token ${JSON.stringify(token)}: ${rungElo} not a member of MAIA_ELO_LADDER`);
    }
    return { kind: 'maia', rungElo, label: token };
  }
  throw new Error(`Invalid --anchors token ${JSON.stringify(token)}: expected 'sf<N>' or 'maia<ELO>'`);
}

// ─── Engine bring-up (shared by main() and the determinism check) ─────────────

/**
 * Loads Maia + spawns an N-process Stockfish pool + resolves chess.js +
 * builds the Node EngineProviders adapter — ONCE per harness run.
 * `stockfishProcs` sizes the pool (Plan 03 Task 1); `providers.grade` is
 * `pool.grade`, so `mctsSearch`'s concurrent `grade()` dispatch fans out
 * across the pool's independent processes instead of serializing on one.
 */
export async function setupHarnessEngines({ stockfishProcs = STOCKFISH_POOL_DEFAULT_SIZE } = {}) {
  const maiaCtx = await createMaiaSession();
  const pool = await createStockfishPool({ size: stockfishProcs });
  // Same seam class as main()'s CR-01 and createStockfishPool's CR-02: if a
  // later bring-up step throws AFTER the pool spawned, this function never
  // returns, so no caller holds a reference to quit the N live Stockfish
  // children — their stdio handles keep the event loop alive (hang + leak).
  try {
    const { Chess } = await resolveFrontendModule('chess.js');
    const providers = makeNodeProviders(maiaCtx.session, maiaCtx.ort, pool.grade);
    return { providers, pool, Chess, maiaCtx };
  } catch (err) {
    pool.quitAll();
    throw err;
  }
}

// ─── D-10 cutoff 1: chess.js terminal-state classification ────────────────────

/** Classifies a chess.js game-over position into a bot-relative W/D/L result, or null if not over. */
function classifyTerminalResult(chess, botIsWhite) {
  if (!chess.isGameOver()) return null;
  if (chess.isCheckmate()) {
    // The side to move IS the checkmated side (chess.turn() already knows it).
    const checkmatedIsWhite = chess.turn() === 'w';
    const botWon = checkmatedIsWhite !== botIsWhite;
    return { result: botWon ? 'win' : 'loss', reason: 'checkmate' };
  }
  if (chess.isStalemate()) return { result: 'draw', reason: 'stalemate' };
  if (chess.isThreefoldRepetition()) return { result: 'draw', reason: 'threefold_repetition' };
  if (chess.isInsufficientMaterial()) return { result: 'draw', reason: 'insufficient_material' };
  if (chess.isDrawByFiftyMoves()) return { result: 'draw', reason: 'fifty_move_rule' };
  return { result: 'draw', reason: 'draw_other' }; // defensive: isDraw()-true but unclassified above
}

// ─── D-10 cutoff 2/3: Stockfish adjudication eval + ply cap ────────────────────
// The single-line white-POV cp eval itself lives in calibration-providers.mjs's
// `evalPositionCp` (engine-parameterized so stockfish-pool.mjs can route it
// through any free pool engine, Plan 03 Task 1) — this file only calls it via
// `pool.evalPosition(fen)` and tracks the sustained-favored-side/ply-cap tally.

/** Updates the sustained-favored-side tracker; returns the favored side once sustained past the threshold. */
function updateSustainState(sustainState, whitePovCp) {
  const isBeyondThreshold = Math.abs(whitePovCp) >= ADJUDICATION_CP_THRESHOLD;
  if (!isBeyondThreshold) {
    sustainState.side = null;
    sustainState.count = 0;
    return null;
  }
  const favoredSide = whitePovCp > 0 ? 'w' : 'b';
  sustainState.count = sustainState.side === favoredSide ? sustainState.count + 1 : 1;
  sustainState.side = favoredSide;
  return sustainState.count >= ADJUDICATION_SUSTAIN_PLIES ? favoredSide : null;
}

function adjudicatedResult(favoredSide, botIsWhite, reason) {
  const botFavored = (favoredSide === 'w') === botIsWhite;
  return { result: botFavored ? 'win' : 'loss', reason };
}

/** D-10 cutoffs 2+3, run only when the position is NOT already chess.js-terminal. Returns null to continue play. */
async function evaluateNonTerminalCutoffs({ pool, fen, botIsWhite, ply, sustainState }) {
  const whitePovCp = await pool.evalPosition(fen);

  const sustainedFavoredSide = updateSustainState(sustainState, whitePovCp);
  if (sustainedFavoredSide !== null) {
    return adjudicatedResult(sustainedFavoredSide, botIsWhite, 'adjudicated_eval');
  }

  if (ply >= PLY_CAP) {
    if (Math.abs(whitePovCp) < ADJUDICATION_CP_THRESHOLD) {
      return { result: 'draw', reason: 'ply_cap_draw' };
    }
    const favoredSide = whitePovCp > 0 ? 'w' : 'b';
    return adjudicatedResult(favoredSide, botIsWhite, 'ply_cap_decisive');
  }

  return null;
}

// ─── Anchor dispatch + move application ────────────────────────────────────────

async function playAnchorMove({ providers, pool, anchorSpec, fen, gameRng }) {
  if (anchorSpec.kind === 'maia') {
    return maiaArgmaxMove(providers, fen, anchorSpec.rungElo, gameRng);
  }
  return pool.skillMove(fen, anchorSpec.skillLevel);
}

/** Applies a UCI move to a chess.js instance IN PLACE (mirrors treeCommon.ts's applyUciMoveFen move-object shape). */
function applyUciMove(chess, uci) {
  const squares = uciToSquares(uci);
  chess.move({
    from: squares?.from ?? uci.slice(0, 2),
    to: squares?.to ?? uci.slice(2, 4),
    promotion: uci.length > 4 ? uci[4] : undefined,
  });
}

// ─── The bot-vs-anchor game loop (Task 1) ──────────────────────────────────────

/**
 * Plays ONE bot-vs-anchor game from `startFen` to a terminal/adjudicated/
 * ply-capped result. The bot's move is ALWAYS the live `selectBotMove` with
 * `deps.search` omitted (CAL-02) — this function never branches on `botBlend`
 * itself, it only forwards it into `settings.blend`.
 *
 * `onPly` (optional, defaults to a no-op) fires after every applied move with
 * `{ ply, mover, uci, moveMs }` — CAL-03 observability: at the `blend=1`
 * full-Stockfish-grading cell a single move's `mctsSearch` can legitimately
 * take minutes (Pitfall 3), so a multi-game spike run needs per-move progress
 * visibility rather than only a final report a killed/timed-out run would
 * never reach.
 *
 * `maxNodes`/`maxPlies` (optional) override the Phase 168.5 D-05/D-07/D-09
 * bot-play budget defaults — ONLY for structural checks (e.g.
 * `calibration-determinism.check.mjs`) that need to prove the
 * seeded-rng/argmax reproducibility property, which does NOT depend on
 * budget size, without paying the full budget's real cost. Every actual
 * calibration run (`main()` below) always uses the fixed
 * `FLAWCHESS_BOT_MAX_NODES`/`FLAWCHESS_BOT_MAX_PLIES` defaults — grid-wide
 * comparability requirement is about calibration runs, not about this
 * determinism-only escape hatch. The `SearchBudget` also always carries
 * `stopRule: FLAWCHESS_BOT_STOP_RULE` and the pinned `FLAWCHESS_BOT_CONCURRENCY`
 * (168.5-04 Task 2) — this measures the shipped bot, not the old
 * full-budget-no-stop-rule search (T-168.5-04-02).
 */
export async function playGame({
  Chess,
  providers,
  pool,
  botElo,
  botBlend,
  anchorSpec,
  startFen,
  botIsWhite,
  gameRng,
  onPly,
  maxNodes = FLAWCHESS_BOT_MAX_NODES,
  maxPlies = FLAWCHESS_BOT_MAX_PLIES,
}) {
  const notifyPly = onPly ?? (() => {});

  // [Rule 1 bug fix, Plan 02]: no engine's transposition table is ever cleared
  // between games otherwise (every engine is reused across the whole grid
  // sweep — 168-RESEARCH.md's explicit design). Without `ucinewgame`, a fresh
  // game's early-ply searches can hit/collide with TT entries left over from
  // an ENTIRELY DIFFERENT earlier game's exploration, silently perturbing
  // `grade()`'s returned eval/PV for what is otherwise an identical
  // (fen, candidateUcis) input — breaking D-09's seeded byte-identical-replay
  // guarantee even though `selectBotMove`'s own rng/argmax logic is fully
  // deterministic. Plan 03: `pool.newGameAll()` clears EVERY engine in the
  // pool, not just one — a bot move can land on any free engine.
  await pool.newGameAll();

  const chess = new Chess(startFen);
  const moveUcis = [];
  const sustainState = { side: null, count: 0 };
  let ply = 0;

  for (;;) {
    const fen = chess.fen();
    const whiteToMove = fen.split(' ')[1] !== 'b';
    const botToMove = whiteToMove === botIsWhite;

    const moveStartMs = performance.now();
    const uci = botToMove
      ? await selectBotMove(
          fen,
          {
            elo: botElo,
            blend: botBlend,
            budget: {
              maxNodes,
              maxPlies,
              // Phase 168.5 D-09 (supersedes Plan 03's `pool.size`): the bot's
              // own concurrency is PINNED to FLAWCHESS_BOT_CONCURRENCY, not
              // the pool's own process count — app == harness determinism
              // requires the exact same fixed value on both sides, not a
              // value that silently tracks `--stockfish-procs` (T-168.5-04-01).
              concurrency: FLAWCHESS_BOT_CONCURRENCY,
              // Phase 168.5 D-05/D-06 (Task 2): without this the sweep would
              // measure a bot without the early-stop rule (T-168.5-04-02).
              stopRule: FLAWCHESS_BOT_STOP_RULE,
            },
          },
          { policy: providers.policy, grade: providers.grade, rng: gameRng },
          // deps.search intentionally omitted (CAL-02) — defaults to the real mctsSearch.
        )
      : await playAnchorMove({ providers, pool, anchorSpec, fen, gameRng });
    const moveMs = performance.now() - moveStartMs;

    try {
      applyUciMove(chess, uci);
    } catch (err) {
      throw new Error(`playGame: illegal move ${uci} at ply ${ply + 1} (fen=${fen}): ${err.message}`);
    }
    moveUcis.push(uci);
    ply++;
    notifyPly({ ply, mover: botToMove ? 'bot' : 'anchor', uci, moveMs });

    const terminal = classifyTerminalResult(chess, botIsWhite);
    if (terminal !== null) {
      return { ...terminal, plies: ply, moveUcis };
    }

    const cutoff = await evaluateNonTerminalCutoffs({ pool, fen: chess.fen(), botIsWhite, ply, sustainState });
    if (cutoff !== null) {
      return { ...cutoff, plies: ply, moveUcis };
    }
  }
}

// ─── D-04/D-06: per-cell (bot-cell x anchor) tally + durable main results TSV ──
// One TSV row represents a full (botElo, botBlend, anchor) cell — games,
// W/D/L, score, and the as-White/as-Black split accumulated across that
// cell's `--games-per-cell` games. The writer is opened ONCE per run
// (header written immediately) and `writeRow` is called as soon as a cell's
// LAST game completes — i.e. durably, incrementally, DURING the sweep, not
// buffered until the whole multi-cell grid finishes (WR-01/D-06): a crash
// mid-sweep still keeps every already-completed cell's row on disk.

export function newCellTally() {
  return {
    games: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    white: { games: 0, wins: 0, draws: 0, losses: 0 },
    black: { games: 0, wins: 0, draws: 0, losses: 0 },
  };
}

/** Folds one completed game's result into a cell tally (overall + color-split). */
function tallyGameResult(tally, result, botIsWhite) {
  const side = botIsWhite ? tally.white : tally.black;
  for (const bucket of [tally, side]) {
    bucket.games++;
    if (result === 'win') bucket.wins++;
    else if (result === 'draw') bucket.draws++;
    else bucket.losses++;
  }
}

/** Points/games score (draw = 0.5 point) — 0 for an empty tally (no games played). */
export function tallyScore(tally) {
  return tally.games > 0 ? (tally.wins + 0.5 * tally.draws) / tally.games : 0;
}

/**
 * A cell the bot swept — won EVERY game, no draws and no losses. This is the
 * ONLY result that establishes a weaker-side won-cutoff: a single draw or loss
 * (e.g. 9W/1D, score 0.95) is NOT a sweep, so the next weaker anchor is still
 * played out rather than pruned to games=0. Mirror of `isUnanimousLoss`.
 */
export function isUnanimousWin(tally) {
  return tally.games > 0 && tally.wins === tally.games;
}

/**
 * A cell the bot was swept in — lost EVERY game, no draws and no wins. The ONLY
 * result that establishes a stronger-side lost-cutoff (see `isUnanimousWin`).
 */
export function isUnanimousLoss(tally) {
  return tally.games > 0 && tally.losses === tally.games;
}

/** Short git SHA of the working tree HEAD — `'unknown'` if git is unavailable (never fatal, WR-01 spirit). */
function resolveGitSha() {
  try {
    return execFileSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function buildTimestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

export function mainTsvColumns() {
  return [
    'bot_elo',
    'bot_blend',
    'anchor',
    'games',
    'wins',
    'draws',
    'losses',
    'score',
    'white_games',
    'white_wins',
    'white_draws',
    'white_losses',
    'white_score',
    'black_games',
    'black_wins',
    'black_draws',
    'black_losses',
    'black_score',
    'seed',
    'max_nodes',
    'max_plies',
    'stockfish_procs',
    'git_sha',
    // Phase 168.5-05 D-15: empty for every played cell; populated with a
    // skip-reason marker (SKIP_REASON_OUT_OF_WINDOW/_LOST_CUTOFF/_WON_CUTOFF)
    // for a pruned cell (games=0) — every skipped anchor is still a REAL row
    // here (Pitfall 4), never a silently absent one.
    'skip_reason',
  ];
}

/** One (botElo, botBlend, anchor) cell row, rendered as a tab-joined TSV line (D-04 schema). */
export function mainTsvRowLine(row) {
  const cells = [
    row.botElo,
    row.botBlend,
    row.anchor,
    row.tally.games,
    row.tally.wins,
    row.tally.draws,
    row.tally.losses,
    tallyScore(row.tally).toFixed(4),
    row.tally.white.games,
    row.tally.white.wins,
    row.tally.white.draws,
    row.tally.white.losses,
    tallyScore(row.tally.white).toFixed(4),
    row.tally.black.games,
    row.tally.black.wins,
    row.tally.black.draws,
    row.tally.black.losses,
    tallyScore(row.tally.black).toFixed(4),
    row.seed,
    row.maxNodes,
    row.maxPlies,
    row.stockfishProcs,
    row.gitSha,
    row.skipReason ?? '',
  ];
  return cells.join('\t');
}

/**
 * Opens the main TSV and returns a durable per-row-append handle (mirrors
 * gem-elo's openTsvWriter). Fresh runs (`append=false`) truncate and write the
 * header; a `--resume` run (`append=true`, SEED-097) opens in append mode and
 * does NOT re-write the header — new cell rows are streamed onto the prior
 * file's completed grid-order prefix.
 */
function openMainTsvWriter(filePath, { append = false } = {}) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const stream = fs.createWriteStream(filePath, { encoding: 'utf8', flags: append ? 'a' : 'w' });
  if (!append) stream.write(`${mainTsvColumns().join('\t')}\n`);
  return {
    writeRow(row) {
      stream.write(`${mainTsvRowLine(row)}\n`);
    },
    close() {
      return new Promise((resolve, reject) => {
        stream.end((err) => (err ? reject(err) : resolve()));
      });
    },
  };
}

// ─── D-05: advisory per-cell ELO-estimate summary TSV (SEED-091 caveat) ────────
// Post-processing step (RESEARCH.md's Architecture Diagram): per (botElo,
// botBlend) bot-cell, combine every anchor's observed score into ONE advisory
// Elo estimate via `combineAnchorEstimates` (weighted-mean anchor-logistic
// inversion). Write-once (like gem-elo's `emitSummary`), not per-row-durable
// like the main TSV — this is a small DERIVED artifact, not the primary
// results matrix.

/** Groups the flat `cellRows` list (one per bot-cell x anchor) by (botElo, botBlend) bot-cell. */
function groupRowsByCell(cellRows) {
  const groups = new Map();
  for (const row of cellRows) {
    const key = `${row.botElo}|${row.botBlend}`;
    if (!groups.has(key)) groups.set(key, { botElo: row.botElo, botBlend: row.botBlend, rows: [] });
    groups.get(key).rows.push(row);
  }
  return [...groups.values()];
}

/** Combines one bot-cell's per-anchor rows into an advisory Elo estimate + a clamped-flag (Pitfall 4). */
function summaryRowForCellGroup(group) {
  const perAnchor = group.rows.map((row) => ({
    score: tallyScore(row.tally),
    games: row.tally.games,
    anchorRating: anchorRatingFor(row.anchorSpec),
  }));
  const eloEstimate = combineAnchorEstimates(perAnchor);
  const anyClamped = perAnchor.some(({ score, games }) => wasScoreClamped(score, games));
  return { botElo: group.botElo, botBlend: group.botBlend, eloEstimate, anyClamped };
}

/** Writes the sibling `-summary.tsv`: one row per bot-cell's advisory Elo estimate, plus the SEED-091 caveat in metadata. */
function emitEloSummary(filePath, cellRows, meta) {
  const lines = [];
  lines.push(['bot_elo', 'bot_blend', 'elo_estimate', 'any_clamped'].join('\t'));

  for (const group of groupRowsByCell(cellRows)) {
    const { botElo, botBlend, eloEstimate, anyClamped } = summaryRowForCellGroup(group);
    lines.push([botElo, botBlend, eloEstimate === null ? '' : eloEstimate.toFixed(1), anyClamped].join('\t'));
  }

  lines.push('');
  lines.push('metadata\tvalue');
  lines.push(`seed\t${meta.seed}`);
  lines.push(`stockfish_procs\t${meta.stockfishProcs}`);
  lines.push(`git_sha\t${meta.gitSha}`);
  lines.push(
    'caveat\tSEED-091: this is a COARSE ADVISORY estimate only, never a precise ELO — anchors themselves are ' +
      'approximate (esp. Stockfish Skill Level -> Elo, 168-RESEARCH.md Open Question 2). The primary, ' +
      'caveat-free artifact is the main results-matrix TSV (D-04), not this summary.',
  );

  const content = `${lines.join('\n')}\n`;
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf8');

  console.log('\n=== advisory per-cell ELO estimate summary (D-05, SEED-091 caveat) ===');
  console.log(content);
}

// ─── Throughput spike report (Task 2, CAL-03) ──────────────────────────────────

function printSpikeReport({ totalGames, totalMoves, elapsedSec, stockfishProcs }) {
  const movesPerSec = totalMoves / elapsedSec;
  const meanSecPerGame = elapsedSec / totalGames;
  const projectedGames =
    DEFAULT_BOT_ELOS.length * DEFAULT_BOT_BLENDS.length * DEFAULT_ANCHOR_TOKENS.length * DEFAULT_GAMES_PER_CELL;
  const projectedSeconds = projectedGames * meanSecPerGame;
  const projectedHours = projectedSeconds / SECONDS_PER_HOUR;

  console.log('\n=== throughput report (pool-backed, Plan 03) ===');
  console.log(`stockfish-procs:                 ${stockfishProcs}`);
  console.log(`games played:                    ${totalGames}`);
  console.log(`total moves (plies):             ${totalMoves}`);
  console.log(`elapsed:                         ${elapsedSec.toFixed(1)}s`);
  console.log(`moves/sec:                       ${movesPerSec.toFixed(3)}`);
  console.log(`mean seconds/game:               ${meanSecPerGame.toFixed(1)}s`);
  // WR-06: surface how often adjudication silently fell back to a neutral 0 cp
  // (no exact info line seen) — a systematic occurrence degrades D-10 cutoff 2
  // accuracy for the whole sweep.
  console.log(`adjudication neutral fallbacks:  ${adjudicationFallbackStats.neutralFallbackCount}`);
  console.log(
    `projected full default-grid wall-clock:  ${projectedHours.toFixed(2)}h ` +
      `(${projectedGames} games @ default grid ${DEFAULT_BOT_ELOS.length}x${DEFAULT_BOT_BLENDS.length} bot-cells ` +
      `x ${DEFAULT_ANCHOR_TOKENS.length} anchors x ${DEFAULT_GAMES_PER_CELL} games/cell — this projection is informational; ` +
      `Plan 03's actual CLI defaults are a bounded first sweep, per 168-03-PLAN.md's re-scope)`,
  );

  const recommendation =
    projectedHours <= WASM_WALL_CLOCK_BUDGET_HOURS
      ? `within budget — projected ${projectedHours.toFixed(2)}h is inside the ${WASM_WALL_CLOCK_BUDGET_HOURS}h ` +
        `reference budget at ${stockfishProcs} stockfish-procs.`
      : `exceeds the ${WASM_WALL_CLOCK_BUDGET_HOURS}h reference budget at ${stockfishProcs} stockfish-procs — ` +
        `raise --stockfish-procs (bounded by available cores) or reduce --games-per-cell/grid axes for a full run.`;
  console.log(`note:                            ${recommendation}`);
}

// ─── SEED-097: --resume (skip already-swept cells, continue the same sweep) ────
// Reads a prior durable TSV, validates it is the SAME experiment (grid + seed +
// budget + games-per-cell), and returns the set of completed cell keys plus the
// reconstructed per-cell rows (so the end-of-run advisory ELO summary can span
// the whole grid, landmine #2). The four landmines are handled here and at the
// grid-loop skip in main().

/** Cell identity key — the first three TSV columns `(bot_elo, bot_blend, anchor)` (landmine #3). */
export function cellKey(botElo, botBlend, anchorLabel) {
  return `${botElo}|${botBlend}|${anchorLabel}`;
}

/** Splits a clean prior TSV into `{ dataLines, colIndex }`, refusing a truncated/schema-mismatched file. */
function readPriorTsvLines(filePath) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new Error(`--resume: cannot read prior TSV ${filePath}: ${err.message}`);
  }
  // Every durable writeRow (and the header) ends with '\n'. A missing trailing
  // newline means the crash cut the last row mid-line — appending after it would
  // splice two rows together, so refuse rather than silently corrupt the map.
  if (!content.endsWith('\n')) {
    throw new Error(
      `--resume: prior TSV ${filePath} has a truncated final line (no trailing newline) — cannot safely resume`,
    );
  }
  const lines = content.split('\n').filter((line) => line.length > 0);
  if (lines.length === 0) throw new Error(`--resume: prior TSV ${filePath} is empty`);

  const header = lines[0].split('\t');
  const expected = mainTsvColumns();
  if (header.length !== expected.length || expected.some((col, i) => header[i] !== col)) {
    throw new Error(`--resume: prior TSV ${filePath} header does not match the current schema`);
  }
  const colIndex = new Map(header.map((name, i) => [name, i]));
  return { dataLines: lines.slice(1), colIndex };
}

/** Parses one prior TSV data line into a reconstructed cell row (same shape main() pushes to cellRows). */
function parsePriorRow(line, colIndex, filePath) {
  const cells = line.split('\t');
  if (cells.length !== mainTsvColumns().length) {
    throw new Error(`--resume: malformed row in ${filePath} (${cells.length} columns): ${line}`);
  }
  const int = (name) => Number.parseInt(cells[colIndex.get(name)], 10);
  const anchor = cells[colIndex.get('anchor')];
  const tally = {
    games: int('games'),
    wins: int('wins'),
    draws: int('draws'),
    losses: int('losses'),
    white: { games: int('white_games'), wins: int('white_wins'), draws: int('white_draws'), losses: int('white_losses') },
    black: { games: int('black_games'), wins: int('black_wins'), draws: int('black_draws'), losses: int('black_losses') },
  };
  // Phase 168.5-05 D-15: absent column index (older, pre-D-15 TSV) can never
  // happen here — readPriorTsvLines already refused a header mismatch before
  // this runs — but `?? ''` keeps this defensive rather than reading `undefined`.
  const skipReasonIdx = colIndex.get('skip_reason');
  const skipReason = skipReasonIdx === undefined ? '' : (cells[skipReasonIdx] ?? '');
  return {
    botElo: int('bot_elo'),
    botBlend: Number.parseFloat(cells[colIndex.get('bot_blend')]),
    anchor,
    anchorSpec: parseAnchorSpec(anchor),
    tally,
    games: tally.games,
    seed: int('seed'),
    maxNodes: int('max_nodes'),
    maxPlies: int('max_plies'),
    skipReason,
  };
}

/**
 * Loads + validates a prior sweep for `--resume`. Throws (WR-02 discipline) on
 * any mismatch that would make the skipped cells a DIFFERENT experiment than the
 * ones we'd play now: games-per-cell (landmine #3), seed / D-11 budget
 * (landmine #4), or a grid axis (a prior cell absent from the current grid).
 */
export function loadPriorSweep(filePath, args, gridKeys) {
  const { dataLines, colIndex } = readPriorTsvLines(filePath);
  const completedKeys = new Set();
  const rowByKey = new Map();

  for (const line of dataLines) {
    const row = parsePriorRow(line, colIndex, filePath);
    // Phase 168.5-05 D-15 (Pitfall 4): a pruned cell's row is a REAL row
    // (games=0, skip_reason populated) but it never played --games-per-cell
    // games by design — the games-count invariant only applies to PLAYED
    // rows. A skip row with a nonzero-but-mismatched games count is still a
    // corruption signal (a skip row must always be games=0), so that case
    // is checked separately rather than silently accepted.
    const isSkipped = row.skipReason !== '';
    if (isSkipped) {
      if (row.games !== 0) {
        throw new Error(
          `--resume: prior cell ${row.anchor} has skip_reason=${row.skipReason} but games=${row.games} (expected 0) — file is corrupt`,
        );
      }
    } else if (row.games !== args.gamesPerCell) {
      throw new Error(
        `--resume: prior cell ${row.anchor} has games=${row.games}, current --games-per-cell=${args.gamesPerCell} — refusing to mix grids`,
      );
    }
    if (row.seed !== args.seed) {
      throw new Error(
        `--resume: prior seed=${row.seed} differs from current --seed=${args.seed} — refusing to resume a different experiment`,
      );
    }
    // Phase 168.5 Task 2: checks against the BOT budget (not the retired
    // analysis-board FLAWCHESS_ENGINE_MAX_* mirrors) — a resumed sweep must
    // refuse to mix a prior run's old 400-node budget with the new bot budget.
    if (row.maxNodes !== FLAWCHESS_BOT_MAX_NODES || row.maxPlies !== FLAWCHESS_BOT_MAX_PLIES) {
      throw new Error(
        `--resume: prior budget (nodes=${row.maxNodes}, plies=${row.maxPlies}) differs from current ` +
          `(nodes=${FLAWCHESS_BOT_MAX_NODES}, plies=${FLAWCHESS_BOT_MAX_PLIES}) — refusing to resume`,
      );
    }
    const key = cellKey(row.botElo, row.botBlend, row.anchor);
    if (!gridKeys.has(key)) {
      throw new Error(
        `--resume: prior cell (elo=${row.botElo}, blend=${row.botBlend}, anchor=${row.anchor}) is not in the current grid — refusing to resume a changed grid`,
      );
    }
    if (completedKeys.has(key)) {
      throw new Error(`--resume: duplicate cell ${key} in prior TSV — file is corrupt`);
    }
    completedKeys.add(key);
    rowByKey.set(key, row);
  }
  return { completedKeys, rowByKey };
}

// ─── Phase 168.5-05 D-15: anchor pruning (static window + dynamic cutoff) ──────
// Two independent mechanisms narrow a coarse-grid sweep's wall-clock cost
// WITHOUT ever shrinking `gridKeys` at runtime (Pitfall 4): every anchor a
// bot-cell would otherwise play still gets a real TSV row — pruned ones as
// `games=0` with a populated `skip_reason` — so `--resume`'s grid-membership
// guard and the "no silent coverage gaps" requirement both hold.

/** Static bracketing (D-15 mechanism 1): an anchor rated more than this many
 * Elo from a bot-cell's own nominal rating is skipped outright — a
 * Stockfish-2200 anchor vs a 1100-rated bot (or the reverse) tells the coarse
 * map nothing "Super strong Stockfish anchors vs weak FlawChess bots doesn't
 * make any sense" (CONTEXT.md specifics) already predicts. */
export const ANCHOR_ELO_WINDOW = 400;

/** D-15 mechanism 2 (dynamic cutoff): a cell is only treated as a decided
 * direction on a UNANIMOUS result — the bot won every game or lost every game
 * (see `isUnanimousWin`/`isUnanimousLoss`). Anchors further out in that SAME
 * direction (weaker after an all-win sweep, stronger after an all-loss sweep)
 * are then pruned rather than played, since the trend is settled. A cell with
 * any draw or split (e.g. 9W/1D) is NOT decided and its neighbour is played
 * out. Stronger anchors are pruned ONLY after an all-loss cell; an all-win
 * cell never stops the climb — it keeps going until the bot is swept. */

/** D-15 mechanism 1: an anchor fell outside the bot-cell's `ANCHOR_ELO_WINDOW`. */
export const SKIP_REASON_OUT_OF_WINDOW = 'out_of_window';
/** D-15 mechanism 2: a stronger-side anchor pruned after an all-loss sweep against a closer, weaker-rated anchor on that same side. */
export const SKIP_REASON_LOST_CUTOFF = 'lost_cutoff';
/** D-15 mechanism 2: a weaker-side anchor pruned after an all-win sweep against a closer, stronger-rated anchor on that same side. */
export const SKIP_REASON_WON_CUTOFF = 'won_cutoff';

/** Splits a bot-cell's anchor list into in-window / out-of-window (D-15 mechanism 1). */
function partitionAnchorsByWindow(anchorSpecs, botElo) {
  const inWindow = [];
  const outOfWindow = [];
  for (const anchorSpec of anchorSpecs) {
    const withinWindow = Math.abs(anchorRatingFor(anchorSpec) - botElo) <= ANCHOR_ELO_WINDOW;
    (withinWindow ? inWindow : outOfWindow).push(anchorSpec);
  }
  return { inWindow, outOfWindow };
}

/**
 * D-15 mechanism 2 traversal order. Splits the in-window anchors at the
 * bot-cell's own nominal rating and walks EACH side outward (bot-adjacent
 * anchor first) — this is what makes BOTH halves of D-15's stated cutoff
 * meaningful: a single whole-window ascending pass would make the "skip
 * weaker" half vacuous, since every weaker anchor would already have been
 * played by the time a sweep is detected against a stronger one. Splitting
 * at the bot's own rating and expanding outward on each side means a
 * decisive result on one side prunes the anchors further out on THAT side,
 * which have genuinely not been played yet (Claude's Discretion, resolving
 * an ambiguity CONTEXT.md leaves open — see the 168.5-05-SUMMARY.md
 * Decisions section for the full rationale).
 *
 * `weakerOutward` walks anchors rated below the bot (closest first,
 * descending); `strongerOutward` walks anchors rated at/above the bot
 * (closest first, ascending) — each independently ascending in DISTANCE
 * from the bot's own rating, which is the sense in which D-15's "ascending
 * strength order" is honored here.
 */
function orderAnchorsForDynamicCutoff(inWindowAnchors, botElo) {
  const weakerOutward = inWindowAnchors
    .filter((anchorSpec) => anchorRatingFor(anchorSpec) < botElo)
    .sort((a, b) => anchorRatingFor(b) - anchorRatingFor(a));
  const strongerOutward = inWindowAnchors
    .filter((anchorSpec) => anchorRatingFor(anchorSpec) >= botElo)
    .sort((a, b) => anchorRatingFor(a) - anchorRatingFor(b));
  return { weakerOutward, strongerOutward };
}

/** Builds a pruned (games=0) row for a skipped anchor — a real TSV row, never a silently absent one. */
function buildSkipRow({ botElo, botBlend, anchorSpec, args, gitSha, skipReason }) {
  return {
    botElo,
    botBlend,
    anchor: anchorSpecLabel(anchorSpec),
    anchorSpec,
    tally: newCellTally(),
    seed: args.seed,
    maxNodes: FLAWCHESS_BOT_MAX_NODES,
    maxPlies: FLAWCHESS_BOT_MAX_PLIES,
    stockfishProcs: args.stockfishProcs,
    gitSha,
    skipReason,
  };
}

/**
 * Processes ONE (botElo, botBlend, anchor) cell: reuses a completed `--resume`
 * row verbatim, writes a pruned `games=0` row if `skipReasonIfPruned` is set
 * (and no prior row exists), or actually plays the cell via `playCell`.
 * Always returns the row that was written/reused so the caller's dynamic-
 * cutoff state can inspect its score, and the gameIndex delta the caller must
 * apply — a pruned/reused-skip row consumes ZERO gameIndex slices (D-09), a
 * reused PLAYED row consumes exactly the games it recorded (never a blind
 * `args.gamesPerCell`, which would over-advance past a pruned resume row).
 */
async function processCellAnchor({
  Chess,
  providers,
  pool,
  botElo,
  botBlend,
  anchorSpec,
  args,
  gameIndex,
  priorSweep,
  tsvWriter,
  gitSha,
  skipReasonIfPruned,
}) {
  const key = cellKey(botElo, botBlend, anchorSpecLabel(anchorSpec));

  if (priorSweep.completedKeys.has(key)) {
    // Landmine #1 (SEED-097) + D-15: the prior row's OWN games count is the
    // truth for how far to fast-forward — a pruned prior row is games=0 and
    // must not advance gameIndex at all.
    const row = priorSweep.rowByKey.get(key);
    return { row, nextGameIndex: gameIndex + row.tally.games, cellMoves: 0, gamesPlayed: 0 };
  }

  if (skipReasonIfPruned) {
    const row = buildSkipRow({ botElo, botBlend, anchorSpec, args, gitSha, skipReason: skipReasonIfPruned });
    tsvWriter.writeRow(row);
    return { row, nextGameIndex: gameIndex, cellMoves: 0, gamesPlayed: 0 };
  }

  const { tally, cellMoves, gamesPlayed, nextGameIndex } = await playCell({
    Chess,
    providers,
    pool,
    botElo,
    botBlend,
    anchorSpec,
    args,
    gameIndex,
  });
  const row = {
    botElo,
    botBlend,
    anchor: anchorSpecLabel(anchorSpec),
    anchorSpec,
    tally,
    seed: args.seed,
    // Phase 168.5 Task 2: TSV records the ACTUAL budget playGame used
    // (the bot budget, not the retired analysis-board mirrors).
    maxNodes: FLAWCHESS_BOT_MAX_NODES,
    maxPlies: FLAWCHESS_BOT_MAX_PLIES,
    stockfishProcs: args.stockfishProcs,
    gitSha,
    skipReason: '',
  };
  // WR-01/D-06: durable — this cell's row is streamed to disk as soon as its
  // games-per-cell games complete, not buffered until the whole sweep finishes.
  tsvWriter.writeRow(row);
  return { row, nextGameIndex, cellMoves, gamesPlayed };
}

// ─── Main orchestration ────────────────────────────────────────────────────────

function anchorSpecLabel(anchorSpec) {
  return anchorSpec.label;
}

/**
 * Plays one full (botElo, botBlend, anchor) cell's `--games-per-cell` games,
 * tallying results — extracted so `main()`'s own loop nesting stays shallow
 * (bot-cell x anchor only; the per-game loop lives here).
 */
async function playCell({ Chess, providers, pool, botElo, botBlend, anchorSpec, args, gameIndex }) {
  const tally = newCellTally();
  let idx = gameIndex;
  let cellMoves = 0;

  for (let g = 0; g < args.gamesPerCell; g++) {
    const opening = OPENING_BOOK[idx % OPENING_BOOK.length];
    const botIsWhite = idx % 2 === 0;
    const gameRng = mulberry32(deriveGameSeed(args.seed, idx));

    console.log(
      `[calibration-harness] game ${idx + 1}: elo=${botElo} blend=${botBlend} ` +
        `anchor=${anchorSpecLabel(anchorSpec)} opening=${opening.name} botIsWhite=${botIsWhite}`,
    );
    const result = await playGame({
      Chess,
      providers,
      pool,
      botElo,
      botBlend,
      anchorSpec,
      startFen: opening.fen,
      botIsWhite,
      gameRng,
      onPly: (p) =>
        console.log(`[calibration-harness]   ply ${p.ply} (${p.mover}) ${p.uci} took ${(p.moveMs / 1000).toFixed(2)}s`),
    });
    console.log(`[calibration-harness] result=${result.result} reason=${result.reason} plies=${result.plies}`);
    console.log(`[calibration-harness] analyze: ${analysisLineUrl(opening, result.moveUcis)}`);

    tallyGameResult(tally, result.result, botIsWhite);
    cellMoves += result.plies;
    idx++;
  }

  return { tally, cellMoves, gamesPlayed: args.gamesPerCell, nextGameIndex: idx };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  validateEloRungs(args.elo);
  validateBlends(args.blends);
  const anchorSpecs = args.anchors.map(parseAnchorSpec);
  const gitSha = resolveGitSha();

  // Current grid's cell keys — the resume grid-change guard checks every prior
  // cell against this set, and the grid loop skips any key already completed.
  const gridKeys = new Set();
  for (const botElo of args.elo) {
    for (const botBlend of args.blends) {
      for (const anchorSpec of anchorSpecs) {
        gridKeys.add(cellKey(botElo, botBlend, anchorSpec.label));
      }
    }
  }

  let priorSweep = { completedKeys: new Set(), rowByKey: new Map() };
  if (args.resume) {
    priorSweep = loadPriorSweep(args.resume, args, gridKeys);
    console.log(
      `[calibration-harness] --resume ${args.resume}: ${priorSweep.completedKeys.size}/${gridKeys.size} cells ` +
        `already complete, appending the remaining ${gridKeys.size - priorSweep.completedKeys.size}`,
    );
  }

  console.log(`[calibration-harness] loading Maia session + spawning a ${args.stockfishProcs}-process Stockfish pool...`);

  const timestamp = buildTimestamp();
  // On --resume, append to the prior file itself so the finished artifact is one
  // byte-identical map; a fresh run opens a new timestamped file as before.
  const mainTsvPath = args.resume ?? path.join(args.outDir, `calibration-harness-${timestamp}.tsv`);

  // CR-01: guard the ENTIRE bring-up sequence (pool spawn through TSV-writer
  // creation) in one try/catch. Without this, an `openMainTsvWriter` failure
  // (e.g. --out-dir not writable) would leave the already-spawned `pool` (N
  // real Stockfish processes) with no reference anywhere to terminate it —
  // `main().catch()` below only logs the error, it never calls `pool.quitAll()`.
  let pool;
  let providers;
  let Chess;
  let tsvWriter;
  try {
    ({ providers, pool, Chess } = await setupHarnessEngines({ stockfishProcs: args.stockfishProcs }));
    // Fail fast (before any game is played) if an opening's uci prefix no
    // longer replays to its committed FEN — a drifted prefix would emit
    // analyze links to the wrong position for every game of that opening.
    assertOpeningBookUciPrefixes(Chess);
    tsvWriter = openMainTsvWriter(mainTsvPath, { append: Boolean(args.resume) });
  } catch (err) {
    pool?.quitAll();
    throw err;
  }

  const startTimeMs = performance.now();
  let totalMoves = 0;
  let totalGames = 0;
  let gameIndex = 0;
  /** Per-cell rows kept in memory for Task 3's advisory per-cell ELO summary (grouped by botElo+botBlend). */
  const cellRows = [];

  try {
    for (const botElo of args.elo) {
      for (const botBlend of args.blends) {
        const { inWindow, outOfWindow } = partitionAnchorsByWindow(anchorSpecs, botElo);

        // D-15 mechanism 1 (static bracketing): every out-of-window anchor is
        // pruned unconditionally — no dynamic-cutoff state to track, since
        // this decision never depends on any other cell's outcome.
        for (const anchorSpec of outOfWindow) {
          const outcome = await processCellAnchor({
            Chess,
            providers,
            pool,
            botElo,
            botBlend,
            anchorSpec,
            args,
            gameIndex,
            priorSweep,
            tsvWriter,
            gitSha,
            skipReasonIfPruned: SKIP_REASON_OUT_OF_WINDOW,
          });
          gameIndex = outcome.nextGameIndex;
          totalMoves += outcome.cellMoves;
          totalGames += outcome.gamesPlayed;
          cellRows.push(outcome.row);
        }

        // D-15 mechanism 2 (dynamic cutoff): each side of the in-window
        // anchor list is walked outward from the bot-cell's own rating,
        // independently — see `orderAnchorsForDynamicCutoff`'s doc comment.
        const { weakerOutward, strongerOutward } = orderAnchorsForDynamicCutoff(inWindow, botElo);

        let wonCutoff = false;
        for (const anchorSpec of weakerOutward) {
          const outcome = await processCellAnchor({
            Chess,
            providers,
            pool,
            botElo,
            botBlend,
            anchorSpec,
            args,
            gameIndex,
            priorSweep,
            tsvWriter,
            gitSha,
            skipReasonIfPruned: wonCutoff ? SKIP_REASON_WON_CUTOFF : null,
          });
          gameIndex = outcome.nextGameIndex;
          totalMoves += outcome.cellMoves;
          totalGames += outcome.gamesPlayed;
          cellRows.push(outcome.row);
          // Only a UNANIMOUS win (every game won, no draws/losses) establishes
          // the weaker-side cutoff — a split or drawn cell leaves the next
          // weaker anchor to be played out. `isUnanimousWin` already guards
          // games>0, so a games=0 pruned row can never be misread as a sweep.
          if (!wonCutoff && isUnanimousWin(outcome.row.tally)) {
            wonCutoff = true;
          }
        }

        let lostCutoff = false;
        for (const anchorSpec of strongerOutward) {
          const outcome = await processCellAnchor({
            Chess,
            providers,
            pool,
            botElo,
            botBlend,
            anchorSpec,
            args,
            gameIndex,
            priorSweep,
            tsvWriter,
            gitSha,
            skipReasonIfPruned: lostCutoff ? SKIP_REASON_LOST_CUTOFF : null,
          });
          gameIndex = outcome.nextGameIndex;
          totalMoves += outcome.cellMoves;
          totalGames += outcome.gamesPlayed;
          cellRows.push(outcome.row);
          // Only a UNANIMOUS loss (every game lost) stops the climb to stronger
          // anchors; an all-win or split cell keeps climbing until the bot is
          // swept (per the stronger-side rule).
          if (!lostCutoff && isUnanimousLoss(outcome.row.tally)) {
            lostCutoff = true;
          }
        }
      }
    }
  } finally {
    pool.quitAll();
    await tsvWriter.close();
  }

  const elapsedSec = (performance.now() - startTimeMs) / 1000;
  if (totalGames > 0) {
    printSpikeReport({ totalGames, totalMoves, elapsedSec, stockfishProcs: args.stockfishProcs });
  } else {
    // --resume where every grid cell was already complete: nothing was played,
    // so the throughput report would divide by zero. Still emit the summary.
    console.log('\n=== --resume: all grid cells already complete, no games played this run ===');
  }
  console.log(`[calibration-harness] wrote ${mainTsvPath} (${cellRows.length} cell rows)`);

  // Sibling summary derived from the main path (fresh: -${timestamp}-summary.tsv;
  // resume: the prior file's -summary.tsv sibling, spanning the whole grid).
  const summaryPath = mainTsvPath.replace(/\.tsv$/, '-summary.tsv');
  emitEloSummary(summaryPath, cellRows, { seed: args.seed, stockfishProcs: args.stockfishProcs, gitSha });
  console.log(`[calibration-harness] wrote ${summaryPath}`);

  return { cellRows, outDir: args.outDir, timestamp, gitSha };
}

// Only auto-run when executed directly (not when imported by the determinism check).
if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error('[calibration-harness] FAILED:', err);
    process.exitCode = 1;
  });
}

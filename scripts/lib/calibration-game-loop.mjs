#!/usr/bin/env node
/**
 * calibration-game-loop.mjs — mover-agnostic two-mover game loop (Phase 173,
 * Plan 01, D-08). Extracted from `calibration-harness.mjs`'s bot-vs-anchor
 * `playGame` so any script can drive a game between two arbitrary
 * `(fen, rng) => Promise<uci>` movers, one per color — not just the bot's
 * own `selectBotMove` vs an anchor. `calibration-harness.mjs`'s own
 * `playGame` is now a thin wrapper around `playTwoMoverGame` (D-10: NO
 * behavior change), and Phase 173 Plan 02's anchor-ladder orchestrator
 * drives it directly with two anchor movers, one per color.
 *
 * The three D-10 adjudication constants (`ADJUDICATION_CP_THRESHOLD`,
 * `ADJUDICATION_SUSTAIN_PLIES`, `PLY_CAP`) are imported from
 * `../calibration-harness.mjs` rather than redeclared here — single source
 * of truth (D-10 "keep harness conventions"). This creates a circular
 * import (`calibration-harness.mjs` imports `playTwoMoverGame` from this
 * module) that is safe ONLY because those constants are read exclusively
 * inside function bodies below, never at this module's own top level —
 * by the time any exported function here actually runs, both modules have
 * finished their top-level evaluation.
 *
 * Every result/reason below is WHITE-POV color-keyed (`white_win`/
 * `black_win`/`draw`) rather than bot-relative (`win`/`loss`/`draw`) — an
 * anchor-vs-anchor game has no "bot" side to be relative to. Callers that
 * need a bot-relative result (the existing bot harness) map the color-keyed
 * result back themselves (see `calibration-harness.mjs`'s `playGame`).
 */
import { uciToSquares } from '@/lib/sanToSquares';
import { ADJUDICATION_CP_THRESHOLD, ADJUDICATION_SUSTAIN_PLIES, PLY_CAP } from '../calibration-harness.mjs';

// ─── D-10 cutoff 1: chess.js terminal-state classification (color-keyed) ──────

/** Classifies a chess.js game-over position into a WHITE-POV color-keyed result, or null if not over. */
export function classifyTerminalResultWhitePov(chess) {
  if (!chess.isGameOver()) return null;
  if (chess.isCheckmate()) {
    // The side to move IS the checkmated side (chess.turn() already knows it).
    const checkmatedIsWhite = chess.turn() === 'w';
    return { result: checkmatedIsWhite ? 'black_win' : 'white_win', reason: 'checkmate' };
  }
  if (chess.isStalemate()) return { result: 'draw', reason: 'stalemate' };
  if (chess.isThreefoldRepetition()) return { result: 'draw', reason: 'threefold_repetition' };
  if (chess.isInsufficientMaterial()) return { result: 'draw', reason: 'insufficient_material' };
  if (chess.isDrawByFiftyMoves()) return { result: 'draw', reason: 'fifty_move_rule' };
  return { result: 'draw', reason: 'draw_other' }; // defensive: isDraw()-true but unclassified above
}

// ─── D-10 cutoff 2/3: Stockfish adjudication eval + ply cap (color-keyed) ─────
// The single-line white-POV cp eval itself lives in calibration-providers.mjs's
// `evalPositionCp` (engine-parameterized so stockfish-pool.mjs can route it
// through any free pool engine) — this module only calls it via
// `pool.evalPosition(fen)` and tracks the sustained-favored-side/ply-cap tally.

/** Updates the sustained-favored-side tracker; returns the favored side once sustained past the threshold. */
export function updateSustainState(sustainState, whitePovCp) {
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

/** Maps a favored side ('w'/'b') to a WHITE-POV color-keyed adjudicated result. */
function adjudicatedResultWhitePov(favoredSide, reason) {
  return { result: favoredSide === 'w' ? 'white_win' : 'black_win', reason };
}

/** D-10 cutoffs 2+3, run only when the position is NOT already chess.js-terminal. Returns null to continue play. */
export async function evaluateNonTerminalCutoffsWhitePov({ pool, fen, ply, sustainState, maxPlies = PLY_CAP }) {
  const whitePovCp = await pool.evalPosition(fen);

  const sustainedFavoredSide = updateSustainState(sustainState, whitePovCp);
  if (sustainedFavoredSide !== null) {
    return adjudicatedResultWhitePov(sustainedFavoredSide, 'adjudicated_eval');
  }

  if (ply >= maxPlies) {
    if (Math.abs(whitePovCp) < ADJUDICATION_CP_THRESHOLD) {
      return { result: 'draw', reason: 'ply_cap_draw' };
    }
    const favoredSide = whitePovCp > 0 ? 'w' : 'b';
    return adjudicatedResultWhitePov(favoredSide, 'ply_cap_decisive');
  }

  return null;
}

// ─── Move application ──────────────────────────────────────────────────────

/** Applies a UCI move to a chess.js instance IN PLACE (mirrors treeCommon.ts's applyUciMoveFen move-object shape). */
export function applyUciMove(chess, uci) {
  const squares = uciToSquares(uci);
  chess.move({
    from: squares?.from ?? uci.slice(0, 2),
    to: squares?.to ?? uci.slice(2, 4),
    promotion: uci.length > 4 ? uci[4] : undefined,
  });
}

// ─── The mover-agnostic two-mover game loop ────────────────────────────────

/**
 * Plays ONE game from `startFen` to a terminal/adjudicated/ply-capped
 * result, dispatching each ply to `moverWhite` or `moverBlack` by the side
 * to move — never by a "bot vs anchor" role (D-08: any two movers, one per
 * color). Each mover is `(fen, gameRng) => Promise<uci>`.
 *
 * `onPly` (optional, defaults to a no-op) fires after every applied move
 * with `{ ply, mover: 'white'|'black', uci, moveMs }`.
 *
 * `maxPlies` (optional, defaults to `PLY_CAP`) is the D-10 cutoff-3 hard ply
 * cap for THIS GAME (not to be confused with a caller's own search-tree
 * depth budget, an unrelated concept some movers close over internally) —
 * callers can override it for structural checks that need a bounded
 * synthesized fixture without waiting out the full `PLY_CAP`.
 *
 * Returns `{ result: 'white_win'|'black_win'|'draw', reason, plies, moveUcis }`.
 */
export async function playTwoMoverGame({ Chess, pool, moverWhite, moverBlack, startFen, gameRng, onPly, maxPlies = PLY_CAP }) {
  const notifyPly = onPly ?? (() => {});

  // [Rule 1 bug fix, Plan 02 of Phase 168]: no engine's transposition table is
  // ever cleared between games otherwise (every engine is reused across the
  // whole grid sweep). Without `ucinewgame`, a fresh game's early-ply
  // searches can hit/collide with TT entries left over from an ENTIRELY
  // DIFFERENT earlier game's exploration. `pool.newGameAll()` clears EVERY
  // engine in the pool, not just one.
  await pool.newGameAll();

  const chess = new Chess(startFen);
  const moveUcis = [];
  const sustainState = { side: null, count: 0 };
  let ply = 0;

  for (;;) {
    const fen = chess.fen();
    const whiteToMove = fen.split(' ')[1] !== 'b';

    const moveStartMs = performance.now();
    const uci = whiteToMove ? await moverWhite(fen, gameRng) : await moverBlack(fen, gameRng);
    const moveMs = performance.now() - moveStartMs;

    try {
      applyUciMove(chess, uci);
    } catch (err) {
      throw new Error(`playTwoMoverGame: illegal move ${uci} at ply ${ply + 1} (fen=${fen}): ${err.message}`);
    }
    moveUcis.push(uci);
    ply++;
    notifyPly({ ply, mover: whiteToMove ? 'white' : 'black', uci, moveMs });

    const terminal = classifyTerminalResultWhitePov(chess);
    if (terminal !== null) {
      return { ...terminal, plies: ply, moveUcis };
    }

    const cutoff = await evaluateNonTerminalCutoffsWhitePov({ pool, fen: chess.fen(), ply, sustainState, maxPlies });
    if (cutoff !== null) {
      return { ...cutoff, plies: ply, moveUcis };
    }
  }
}

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

/**
 * Single white-POV cp eval + the engine's `bestmove` byproduct, degrading to a
 * cp-only pool (`pool.evalPosition`, `bestUci: null`) when
 * `pool.evalPositionWithBest` is absent — the game-loop `.check.mjs` stub pool
 * only defines `evalPosition`, so this keeps that structural check passing while
 * the real pool (Phase 180) surfaces the `bestmove` for the near-free
 * SF-agreement metric at ZERO extra engine cost (same single `go`).
 */
async function evalWhitePovWithOptionalBest(pool, fen) {
  if (typeof pool.evalPositionWithBest === 'function') {
    const { cp, bestUci } = await pool.evalPositionWithBest(fen);
    return { whitePovCp: cp, bestUci: bestUci ?? null };
  }
  return { whitePovCp: await pool.evalPosition(fen), bestUci: null };
}

/**
 * D-10 cutoffs 2+3, run only when the position is NOT already chess.js-terminal.
 * Returns `{ cutoff, whitePovCp, bestUci }`: `cutoff` is the adjudicated/ply-cap
 * color-keyed result (or `null` to continue play — the pre-Phase-180 return
 * value), and `whitePovCp`/`bestUci` are the post-move eval + engine best move
 * surfaced to `onPly` for the Phase-180 near-free metrics (ACPL / blunder rate /
 * SF-agreement). The eval is computed ONCE and reused for both the cutoff
 * decision and the metric surface — no extra engine call.
 */
export async function evaluateNonTerminalCutoffsWhitePov({ pool, fen, ply, sustainState, maxPlies = PLY_CAP }) {
  const { whitePovCp, bestUci } = await evalWhitePovWithOptionalBest(pool, fen);

  const sustainedFavoredSide = updateSustainState(sustainState, whitePovCp);
  let cutoff = null;
  if (sustainedFavoredSide !== null) {
    cutoff = adjudicatedResultWhitePov(sustainedFavoredSide, 'adjudicated_eval');
  } else if (ply >= maxPlies) {
    cutoff =
      Math.abs(whitePovCp) < ADJUDICATION_CP_THRESHOLD
        ? { result: 'draw', reason: 'ply_cap_draw' }
        : adjudicatedResultWhitePov(whitePovCp > 0 ? 'w' : 'b', 'ply_cap_decisive');
  }

  return { cutoff, whitePovCp, bestUci };
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
 * with `{ ply, mover: 'white'|'black', uci, moveMs, evalCp, bestUci }`.
 * `evalCp` is the POST-move white-POV cp eval and `bestUci` the engine's best
 * move in the resulting position (both `null` on a terminal ply, where no
 * adjudication eval runs, or when the pool has no `evalPositionWithBest`) —
 * the Phase-180 near-free metric hook. It fires AFTER the adjudication eval so
 * that eval can be surfaced without a second engine call.
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
    const mover = whiteToMove ? 'white' : 'black';

    const terminal = classifyTerminalResultWhitePov(chess);
    if (terminal !== null) {
      // Terminal ply: no adjudication eval runs, so the near-free eval/best are
      // null. Still fire onPly so a caller's move log/counter stays complete.
      notifyPly({ ply, mover, uci, moveMs, evalCp: null, bestUci: null });
      return { ...terminal, plies: ply, moveUcis };
    }

    const { cutoff, whitePovCp, bestUci } = await evaluateNonTerminalCutoffsWhitePov({
      pool,
      fen: chess.fen(),
      ply,
      sustainState,
      maxPlies,
    });
    // Fire onPly AFTER the eval so the post-move cp + best move ride along (the
    // Phase-180 near-free hook) without a second engine call.
    notifyPly({ ply, mover, uci, moveMs, evalCp: whitePovCp, bestUci });
    if (cutoff !== null) {
      return { ...cutoff, plies: ply, moveUcis };
    }
  }
}

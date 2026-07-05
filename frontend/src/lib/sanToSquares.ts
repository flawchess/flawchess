import { Chess } from 'chess.js';

export interface MoveSquares {
  from: string;
  to: string;
}

/**
 * Convert a SAN move string into its from/to squares relative to a given FEN.
 *
 * `fen` is the position BEFORE the move (i.e. `finding.entry_fen` from the
 * Insights API). `san` is the candidate move SAN ("Be2", "Nxd4", "O-O", etc.).
 *
 * chess.js v1.x throws on illegal moves and on malformed FENs. We swallow
 * everything and return `null` so callers (e.g. OpeningFindingCard) can simply
 * fall back to "no arrow" without try/catch boilerplate at every call site.
 */
export function sanToSquares(fen: string, san: string): MoveSquares | null {
  try {
    const chess = new Chess(fen);
    const move = chess.move(san);
    return { from: move.from, to: move.to };
  } catch {
    return null;
  }
}

/**
 * Convert a UCI move string ("e2e4", "e7e8q") into its from/to squares.
 *
 * UCI already encodes the squares positionally (chars 0-1 = from, 2-3 = to, an
 * optional 5th char = promotion piece), so unlike `sanToSquares` this needs no
 * board context. Returns `null` for malformed input (shorter than 4 chars) so
 * callers can fall back to "no arrow".
 */
export function uciToSquares(uci: string | null): MoveSquares | null {
  if (!uci || uci.length < 4) return null;
  return { from: uci.slice(0, 2), to: uci.slice(2, 4) };
}

/**
 * Apply `san` to `fen` and return the resulting full FEN, or `null` if the move
 * is illegal or the FEN is malformed. Render-time safe — never throws. Used by
 * OpeningFindingCard to also show the troll-opening watermark when the
 * candidate move's target position matches a troll line.
 */
export function fenAfterMove(fen: string, san: string): string | null {
  try {
    const chess = new Chess(fen);
    chess.move(san);
    return chess.fen();
  } catch {
    return null;
  }
}

/**
 * Convert a SAN move (relative to `fen`) into its UCI string (e.g. "e2e4",
 * "e7e8q" for a promotion), or `null` on illegal/malformed input. Used to
 * build the grading search's `searchmoves` list (Phase 151.1 SC3) — mirrors
 * `sanToSquares`'s try/catch-return-null style, never throws.
 */
export function sanToUci(fen: string, san: string): string | null {
  try {
    const chess = new Chess(fen);
    const move = chess.move(san);
    return `${move.from}${move.to}${move.promotion ?? ''}`;
  } catch {
    return null;
  }
}

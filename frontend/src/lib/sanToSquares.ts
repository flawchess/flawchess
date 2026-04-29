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

import type { Color } from '@/types/api';
import { WHITE_TROLL_KEYS, BLACK_TROLL_KEYS } from '@/data/trollOpenings';

/**
 * Derive a deterministic user-side-only key from a board FEN.
 *
 * Accepts either a full FEN ("rnbq.../w KQkq -") or a piece-placement-only FEN
 * ("rnbq..."). Strips opponent pieces, re-canonicalizes empty-square runs, and
 * returns the rejoined 8-rank string. Stable across opponent variations.
 */
export function deriveUserSideKey(fen: string, side: Color): string {
  // safe: split with limit=1 always returns at least one element
  const placement = fen.split(' ', 1)[0]!;
  const ranks = placement.split('/');
  if (ranks.length !== 8) {
    throw new Error(`Invalid FEN piece-placement: expected 8 ranks, got ${ranks.length}`);
  }
  const stripPattern = side === 'white' ? /[a-z]/ : /[A-Z]/;
  return ranks.map((rank) => canonicalizeRank(rank, stripPattern)).join('/');
}

function canonicalizeRank(rank: string, stripPattern: RegExp): string {
  let out = '';
  let emptyRun = 0;
  for (const ch of rank) {
    if (/\d/.test(ch)) {
      emptyRun += parseInt(ch, 10);
    } else if (stripPattern.test(ch)) {
      emptyRun += 1;
    } else {
      if (emptyRun > 0) {
        out += String(emptyRun);
        emptyRun = 0;
      }
      out += ch;
    }
  }
  if (emptyRun > 0) out += String(emptyRun);
  return out;
}

/**
 * Returns true iff the user-side-only key derived from `fen` is in the curated
 * troll-opening set for `side`. Pure synchronous lookup; safe to call inline
 * (no useMemo needed).
 */
export function isTrollPosition(fen: string, side: Color): boolean {
  const key = deriveUserSideKey(fen, side);
  return side === 'white' ? WHITE_TROLL_KEYS.has(key) : BLACK_TROLL_KEYS.has(key);
}

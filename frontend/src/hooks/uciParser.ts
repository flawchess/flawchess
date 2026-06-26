/**
 * Pure UCI parser for Stockfish output — no React, no Worker dependency.
 *
 * Exports parseInfoLine and parseBestmove as the primary public API.
 * Source: UCI specification (official-stockfish.github.io)
 *
 * noUncheckedIndexedAccess: every tokens[i] is assigned to a const
 * and narrowed before use (never accessed directly without a check).
 */

// ─── Types ───────────────────────────────────────────────────────────────────

/** A single candidate line returned by MultiPV search. */
export interface PvLine {
  /** 1-based MultiPV index. */
  multipv: number;
  depth: number;
  /** UCI move strings, e.g. ['e2e4', 'd7d5']. */
  moves: string[];
  /** Centipawns, white-POV; null if the score is a mate distance. */
  evalCp: number | null;
  /** Mate in N; positive=winning, negative=losing; null if centipawn score. */
  evalMate: number | null;
}

/**
 * Whether the info line's score is a definitive (exact) measurement or a
 * search bound that must not be displayed.
 *
 * Pitfall 5: lowerbound/upperbound scores from alpha-beta cause eval jitter
 * if displayed — only commit to state on 'exact'.
 */
export type UCIScoreBound = 'exact' | 'lowerbound' | 'upperbound';

/** Structured representation of a parsed `info depth ...` UCI line. */
export interface ParsedInfoLine {
  depth: number;
  /** 1-based MultiPV index (defaults to 1 for engines not sending multipv). */
  multipv: number;
  /** Centipawns from white's perspective; null if score is a mate distance. */
  scoreCp: number | null;
  /** Mate distance; positive=winning, 0=terminal, negative=losing; null if cp. */
  scoreMate: number | null;
  bound: UCIScoreBound;
  /** UCI move strings following the `pv` keyword. */
  pv: string[];
}

// ─── Parser ──────────────────────────────────────────────────────────────────

/**
 * Parse a Stockfish UCI `info` line into a structured object.
 *
 * Returns null for any line not starting with `info ` (with trailing space),
 * and for any `info` line that lacks required fields.
 *
 * Token scanning (O(n)) reads keywords sequentially. The `pv` keyword
 * terminates the keyword section — everything after it is move strings.
 */
export function parseInfoLine(line: string): ParsedInfoLine | null {
  if (!line.startsWith('info ')) return null;

  const tokens = line.split(' ');
  let depth = 0;
  let multipv = 1;
  let scoreCp: number | null = null;
  let scoreMate: number | null = null;
  let bound: UCIScoreBound = 'exact';
  const pv: string[] = [];

  let i = 1; // skip leading 'info'
  while (i < tokens.length) {
    const token = tokens[i];
    if (token === undefined) break;

    if (token === 'depth') {
      const val = tokens[i + 1];
      if (val !== undefined) {
        depth = parseInt(val, 10);
        i += 2;
        continue;
      }
    } else if (token === 'multipv') {
      const val = tokens[i + 1];
      if (val !== undefined) {
        multipv = parseInt(val, 10);
        i += 2;
        continue;
      }
    } else if (token === 'score') {
      const type = tokens[i + 1];
      const value = tokens[i + 2];
      if (type !== undefined && value !== undefined) {
        if (type === 'cp') {
          scoreCp = parseInt(value, 10);
          scoreMate = null;
        } else if (type === 'mate') {
          scoreMate = parseInt(value, 10);
          scoreCp = null;
        }
        // Check for optional bound modifier immediately after the score value.
        // Pitfall 5: lowerbound/upperbound must not be committed to displayed eval.
        const boundToken = tokens[i + 3];
        if (boundToken === 'lowerbound') {
          bound = 'lowerbound';
          i += 4;
        } else if (boundToken === 'upperbound') {
          bound = 'upperbound';
          i += 4;
        } else {
          i += 3;
        }
        continue;
      }
    } else if (token === 'pv') {
      // Everything after 'pv' is the principal variation (move strings).
      // Break out of the main loop and collect all remaining non-empty tokens.
      i += 1;
      while (i < tokens.length) {
        const move = tokens[i];
        if (move !== undefined && move.length > 0) {
          pv.push(move);
        }
        i += 1;
      }
      continue;
    }

    i += 1;
  }

  return { depth, multipv, scoreCp, scoreMate, bound, pv };
}

/**
 * Parse a Stockfish `bestmove` line and return the best move token.
 *
 * Returns null if the line is not a bestmove line, or if the engine
 * reports `(none)` (no legal moves / position already terminal).
 *
 * Example: 'bestmove h5f7 ponder d8h4' → 'h5f7'
 */
export function parseBestmove(line: string): string | null {
  if (!line.startsWith('bestmove ')) return null;
  const tokens = line.split(' ');
  const move = tokens[1];
  if (move === undefined || move === '(none)') return null;
  return move;
}

/**
 * useLiveMoveFlaw — live blunder/mistake/inaccuracy classification for a freely-played
 * move on the analysis board (Quick w8k item 4).
 *
 * The precomputed overlay (useGameOverlay) only covers the game's main line. For any
 * other move — a what-if on a game, or any move in free-play mode — this hook grades
 * the move from the live engine: the parent position's completed eval (captured while
 * the board sat there) vs the child position's current engine eval, both routed through
 * the same expected-score method the backend flaw classifier uses (lib/liveFlaw).
 *
 * Caveats (accepted by the user when choosing live classification): the icon appears
 * only once the engine has reported both positions, so it lags the move, and a shallow
 * search can grade slightly differently from the game's stored classification.
 */

import { useMemo } from 'react';

import type { SquareMarker } from '@/components/board/ChessBoard';
import type { FlawSeverity } from '@/types/library';
import {
  MOVE_HIGHLIGHT_GOOD,
  MOVE_HIGHLIGHT_BLUNDER,
  MOVE_HIGHLIGHT_MISTAKE,
  MOVE_HIGHLIGHT_SQUARE,
} from '@/lib/theme';
import { classifyLiveSeverity, evalToExpectedScore, sideToMoveFromFen } from '@/lib/liveFlaw';

// Severity → last-move square overlay color (mirrors useGameOverlay): inaccuracy keeps
// the translucent yellow, blunder/mistake get their red/orange at the same alpha.
const MOVE_HIGHLIGHT_SEVERITY: Record<FlawSeverity, string> = {
  blunder: MOVE_HIGHLIGHT_BLUNDER,
  mistake: MOVE_HIGHLIGHT_MISTAKE,
  inaccuracy: MOVE_HIGHLIGHT_SQUARE,
};

export interface LiveMoveFlaw {
  /** Severity glyph marker for the played move (empty when no classification applies). */
  squareMarkers: SquareMarker[];
  /** Severity-coded last-move overlay color, or undefined when not classified. */
  lastMoveHighlightColor: string | undefined;
}

export interface UseLiveMoveFlawParams {
  /** Only attempt classification when off the precomputed line (else precomputed wins). */
  active: boolean;
  /** FEN of the position before the played move (drives the mover color + best-before eval). */
  parentFen: string | null;
  /** Completed engine eval of the parent position, captured from the eval cache. */
  parentEval: { cp: number | null; mate: number | null } | null | undefined;
  /** Current live engine eval of the position after the move (white POV). */
  childEvalCp: number | null;
  childEvalMate: number | null;
  /** From/to of the played move (the glyph rides its target square). */
  lastMove: { from: string; to: string } | null;
}

const EMPTY: LiveMoveFlaw = { squareMarkers: [], lastMoveHighlightColor: undefined };

export function useLiveMoveFlaw(params: UseLiveMoveFlawParams): LiveMoveFlaw {
  const { active, parentFen, parentEval, childEvalCp, childEvalMate, lastMove } = params;

  return useMemo<LiveMoveFlaw>(() => {
    if (!active || !lastMove || !parentFen || parentEval == null) return EMPTY;
    if (parentEval.cp == null && parentEval.mate == null) return EMPTY;
    // Child not yet evaluated by the live engine — wait (the move is unclassified).
    if (childEvalCp == null && childEvalMate == null) return EMPTY;

    const mover = sideToMoveFromFen(parentFen);
    const esBefore = evalToExpectedScore(parentEval.cp, parentEval.mate, mover);
    const esAfter = evalToExpectedScore(childEvalCp, childEvalMate, mover);
    const severity = classifyLiveSeverity(esBefore, esAfter);

    if (severity == null) {
      // A clean freely-played move reads green, matching the main-line behaviour.
      return { squareMarkers: [], lastMoveHighlightColor: MOVE_HIGHLIGHT_GOOD };
    }
    return {
      squareMarkers: [{ square: lastMove.to, severity }],
      lastMoveHighlightColor: MOVE_HIGHLIGHT_SEVERITY[severity],
    };
  }, [active, parentFen, parentEval, childEvalCp, childEvalMate, lastMove]);
}

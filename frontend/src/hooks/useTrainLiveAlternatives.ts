import { useMemo, useState } from 'react';
import type { PvLine } from '@/hooks/uciParser';
import { buildTrainLiveAlternatives } from '@/lib/trainArrows';
import type { TrainFineMove, TrainLiveAlternativeContext } from '@/lib/trainArrows';

/** Stable empty list, so an idle screen hands consumers the same identity. */
const NO_ALTERNATIVES: readonly TrainFineMove[] = Object.freeze([]);

interface LiveAlternativesLatch {
  fen: string;
  moves: readonly TrainFineMove[];
}

function sameMoves(a: readonly TrainFineMove[], b: readonly TrainFineMove[]): boolean {
  return a.length === b.length && a.every((move, index) => move.uci === b[index]?.uci);
}

/**
 * Quick 261010-e5l: a soft puzzle's live engine alternatives at the puzzle
 * position, for the board arrows AND the "Also fine" text. The reveal engine
 * only searches the shown position, so the root's lines are gone as soon as
 * the user steps into a line; the last settled root list is latched per
 * puzzle FEN so the text does not empty out while stepping, and returning to
 * the root does not flash the arrows off while the search restarts. A root
 * search that is not yet deep enough (null from the builder) never replaces a
 * settled list.
 */
export function useTrainLiveAlternatives(
  context: TrainLiveAlternativeContext,
  isAtRoot: boolean,
  pvLines: readonly PvLine[],
): readonly TrainFineMove[] {
  const { puzzleType, puzzleFen, bestMoveUci, playedMoveUci, drawnAlternatives } = context;
  const rootResult = useMemo(
    () =>
      isAtRoot
        ? buildTrainLiveAlternatives(
            { puzzleType, puzzleFen, bestMoveUci, playedMoveUci, drawnAlternatives },
            pvLines,
          )
        : null,
    [isAtRoot, puzzleType, puzzleFen, bestMoveUci, playedMoveUci, drawnAlternatives, pvLines],
  );

  const [latch, setLatch] = useState<LiveAlternativesLatch>({ fen: puzzleFen, moves: NO_ALTERNATIVES });
  // Adjust state during render (React's "storing information from previous
  // renders" pattern): guarded so it settles after one extra render.
  if (latch.fen !== puzzleFen) {
    setLatch({ fen: puzzleFen, moves: rootResult ?? NO_ALTERNATIVES });
  } else if (rootResult !== null && !sameMoves(rootResult, latch.moves)) {
    setLatch({ fen: puzzleFen, moves: rootResult });
  }
  return latch.fen === puzzleFen ? latch.moves : NO_ALTERNATIVES;
}

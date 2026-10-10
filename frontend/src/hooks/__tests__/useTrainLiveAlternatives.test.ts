// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useTrainLiveAlternatives } from '@/hooks/useTrainLiveAlternatives';
import type { PvLine } from '@/hooks/uciParser';
import { TRAIN_LIVE_ALT_MIN_DEPTH } from '@/lib/trainArrows';
import type { TrainFineMove, TrainLiveAlternativeContext } from '@/lib/trainArrows';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const OTHER_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';
const NO_SERVER_ALTERNATIVES: TrainFineMove[] = [];

function line(multipv: number, move: string, evalCp: number, depth = TRAIN_LIVE_ALT_MIN_DEPTH): PvLine {
  return { multipv, depth, moves: [move], evalCp, evalMate: null };
}

const SETTLED: PvLine[] = [line(1, 'e2e4', 20), line(2, 'd2d4', 15), line(3, 'g1f3', 15)];
const SHALLOW: PvLine[] = [line(1, 'e2e4', 20, 1), line(2, 'c2c4', 15, 1)];

interface Props {
  fen: string;
  isAtRoot: boolean;
  pvLines: PvLine[];
}

function render(initial: Props) {
  return renderHook(
    ({ fen, isAtRoot, pvLines }: Props) => {
      const context: TrainLiveAlternativeContext = {
        puzzleType: 'soft',
        puzzleFen: fen,
        bestMoveUci: 'e2e4',
        playedMoveUci: null,
        drawnAlternatives: NO_SERVER_ALTERNATIVES,
      };
      return useTrainLiveAlternatives(context, isAtRoot, pvLines);
    },
    { initialProps: initial },
  );
}

const ucis = (moves: readonly TrainFineMove[]) => moves.map((m) => m.uci);

describe('useTrainLiveAlternatives (quick 261010-e5l)', () => {
  it('keeps the settled root list while a line is stepped and while the root search restarts', () => {
    const { result, rerender } = render({ fen: START_FEN, isAtRoot: true, pvLines: SETTLED });
    expect(ucis(result.current)).toEqual(['d2d4', 'g1f3']);
    // Stepped into a line: the engine now reports another position's lines.
    rerender({ fen: START_FEN, isAtRoot: false, pvLines: [line(1, 'e7e5', 0)] });
    expect(ucis(result.current)).toEqual(['d2d4', 'g1f3']);
    // Back at the root, the restarted search is still shallow: no flash.
    rerender({ fen: START_FEN, isAtRoot: true, pvLines: SHALLOW });
    expect(ucis(result.current)).toEqual(['d2d4', 'g1f3']);
  });

  it('replaces the list once the root search settles on a different set', () => {
    const { result, rerender } = render({ fen: START_FEN, isAtRoot: true, pvLines: SETTLED });
    rerender({ fen: START_FEN, isAtRoot: true, pvLines: [line(1, 'e2e4', 20), line(2, 'c2c4', 15)] });
    expect(ucis(result.current)).toEqual(['c2c4']);
  });

  it('drops the latched list for a new puzzle', () => {
    const { result, rerender } = render({ fen: START_FEN, isAtRoot: true, pvLines: SETTLED });
    rerender({ fen: OTHER_FEN, isAtRoot: false, pvLines: [] });
    expect(result.current).toEqual([]);
  });
});

// @vitest-environment jsdom
/**
 * Phase 237 Plan 04: the tracer harness. The REAL buildChipGroups feeds the REAL
 * useTrainRevealTree, which drives TrainLineChips and TrainMoveTreeList together
 * (no mock of either module), so the chip -> tree -> list path is proven as one
 * slice before the reveal screen mounts it.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { Chess } from 'chess.js';

import { useTrainRevealTree } from '@/hooks/useTrainRevealTree';
import type { GradeResult, TrainEngineLine } from '@/hooks/useTrainGradingEngine';
import { buildChipGroups } from '@/lib/trainRevealLines';
import { TrainLineChips } from '@/components/train/TrainLineChips';
import { TrainMoveTreeList } from '@/components/train/TrainMoveTreeList';
import { TooltipProvider } from '@/components/ui/tooltip';
import { STOCKFISH_BADGE_SECONDARY } from '@/lib/theme';

vi.mock('@/lib/sounds', () => ({
  playSound: vi.fn(),
  unlockAudio: vi.fn(),
}));

// The tree hook owns the reveal's one Stockfish engine (plan 06). jsdom has no
// Worker, so drive it with a mutable state object (the useTrainRevealTree test's
// pattern): one PV line whose first move is `engineState.pvFirstMove`.
const engineState = { pvFirstMove: 'e7e5' };
vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: (options: { fen: string | null; enabled: boolean; multiPv: number }) => {
    const live = options.fen !== null && options.enabled;
    return {
      evalCp: live ? 20 : null,
      evalMate: null,
      pvLines: live
        ? [{ multipv: 1, depth: 10, moves: [engineState.pvFirstMove], evalCp: 20, evalMate: null }]
        : [],
      depth: live ? 10 : 0,
      isAnalyzing: false,
      isReady: true,
      currentFen: live ? options.fen : null,
    };
  },
}));

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function fenAfter(...sans: string[]): string {
  const chess = new Chess(START_FEN);
  sans.forEach((san) => chess.move(san));
  return chess.fen();
}

function line(moves: string[], evalCp: number): TrainEngineLine {
  return { moves, evalCp, evalMate: null };
}

const GRADE: GradeResult = {
  moveTier: 'good',
  bestMoveUci: 'd2d4',
  esBefore: 0.5,
  esAfter: 0.5,
  bestLine: line(['d2d4', 'd7d5', 'c2c4'], 40),
  playedLine: line(['e2e4', 'e7e5', 'g1f3'], 30),
};

function Harness() {
  const chips = buildChipGroups({
    puzzleFen: START_FEN,
    playedMoveUci: 'e2e4',
    gradeResult: GRADE,
    instantGrade: null,
    gameMoveUci: null,
    gameMoveLine: { status: 'idle' },
    playedMoveQuality: 'good',
    gameMoveQuality: null,
  });
  const tree = useTrainRevealTree({ startFen: START_FEN, active: true, chips });
  return (
    <>
      <TrainLineChips
        chips={chips}
        activeChip={tree.activeChip}
        onSelect={tree.selectChip}
        sanOnlyGameMove={null}
      />
      <TrainMoveTreeList tree={tree} flipped={false} />
      <output data-testid="harness-fen">{tree.fen}</output>
      {/* A hand-played move that no chip line carries (a fork), via the hook's playMove. */}
      <button type="button" data-testid="harness-play-nc3" onClick={() => tree.playMove('b1', 'c3')} />
    </>
  );
}

beforeAll(() => {
  // jsdom does not implement scrollIntoView (HorizontalMoveList auto-scroll).
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
  engineState.pvFirstMove = 'e7e5';
});

describe('TrainLineChips + TrainMoveTreeList over the real tree hook', () => {
  it('tracer: a chip tap switches the list to its line and a list tap moves the tree', () => {
    render(<Harness />);
    const list = () => screen.getByTestId('train-move-tree');

    expect(screen.getByTestId('train-chip-your').getAttribute('aria-pressed')).toBe('true');
    expect(within(list()).getByText('e4')).toBeTruthy();
    expect(within(list()).getByText('e5')).toBeTruthy();
    expect(within(list()).getByText('Nf3')).toBeTruthy();

    fireEvent.click(within(list()).getByText('e5'));
    expect(screen.getByTestId('harness-fen').textContent).toBe(fenAfter('e4', 'e5'));

    // D-01: a chip tap from another chip's line returns to the puzzle position.
    fireEvent.click(screen.getByTestId('train-chip-best'));
    expect(screen.getByTestId('harness-fen').textContent).toBe(START_FEN);
    expect(screen.getByTestId('train-chip-best').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('train-chip-your').getAttribute('aria-pressed')).toBe('false');
    expect(within(list()).getByText('d4')).toBeTruthy();
    expect(within(list()).getByText('d5')).toBeTruthy();
    expect(within(list()).getByText('c4')).toBeTruthy();
    expect(within(list()).queryByText('Nf3')).toBeNull();

    fireEvent.click(within(list()).getByText('d5'));
    expect(screen.getByTestId('harness-fen').textContent).toBe(fenAfter('d4', 'd5'));
  });

  it('quick 261009-por: stepping a known line renders the Stockfish row; the puzzle position does not', () => {
    render(
      <TooltipProvider>
        <Harness />
      </TooltipProvider>,
    );
    expect(screen.queryByTestId('train-sf-row')).toBeNull();
    fireEvent.click(within(screen.getByTestId('train-move-tree')).getByText('e5'));
    expect(screen.getByTestId('train-sf-row')).toBeTruthy();
  });

  it("quick 261009-por: on a stepped chip line the row hides the engine line that repeats the line's next move and draws the rest secondary", () => {
    const { rerender } = render(
      <TooltipProvider>
        <Harness />
      </TooltipProvider>,
    );
    // Step to 1. e4: the Move line continues 1... e5, which the engine also plays.
    engineState.pvFirstMove = 'e7e5';
    fireEvent.click(within(screen.getByTestId('train-move-tree')).getByText('e4'));
    expect(screen.getByTestId('train-sf-row')).toBeTruthy();
    expect(screen.queryAllByLabelText(/^Line \d+:/)).toHaveLength(0);
    expect(screen.queryByTestId('engine-lines-analyzing')).toBeNull();

    // The engine disagrees (1... c5): its line shows, with a secondary badge.
    engineState.pvFirstMove = 'c7c5';
    rerender(
      <TooltipProvider>
        <Harness />
      </TooltipProvider>,
    );
    const badges = screen.getAllByLabelText(/^Line \d+:/);
    expect(badges).toHaveLength(1);
    expect(badges[0]!.style.backgroundColor).toBe(STOCKFISH_BADGE_SECONDARY);
  });

  it('a hand-played fork off the known lines renders the Stockfish row', () => {
    render(
      <TooltipProvider>
        <Harness />
      </TooltipProvider>,
    );
    // At the puzzle position the row is absent.
    expect(screen.queryByTestId('train-sf-row')).toBeNull();

    // Nc3 matches no chip line (Move = e4, Best = d4), so it forks a sideline.
    fireEvent.click(screen.getByTestId('harness-play-nc3'));
    expect(screen.getByTestId('train-sf-row')).toBeTruthy();
    // The row is a sibling of the list wrapper, so list queries never see its moves.
    expect(within(screen.getByTestId('train-move-tree')).queryByTestId('train-sf-row')).toBeNull();
  });
});

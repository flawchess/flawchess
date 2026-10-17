// @vitest-environment jsdom
/**
 * The tracer harness. The REAL buildChipGroups feeds the REAL
 * useTrainRevealTree, which drives TrainLineChips and TrainMoveTreeList together
 * (no mock of either module), so the chip -> tree -> list path is proven as one
 * slice before the reveal screen mounts it.
 *
 * Each chip owns only its first move; the rest of its graded line is the
 * dimmed preview at the end of the list, and the Stockfish row drops the top engine
 * line at a previewed leaf.
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

vi.mock('@/lib/sounds', () => ({
  playSound: vi.fn(),
  unlockAudio: vi.fn(),
}));

// The tree hook owns the reveal's one Stockfish engine. jsdom has no
// Worker, so drive it with a mutable state object (the useTrainRevealTree test's
// pattern): `lineCount` PV lines, the first starting with `engineState.pvFirstMove`.
const SECONDARY_ENGINE_MOVES = ['c7c5', 'e7e6', 'd7d5', 'c7c6'];
const engineState = { pvFirstMove: 'e7e5', lineCount: 3 };
vi.mock('@/hooks/useStockfishEngine', () => ({
  useStockfishEngine: (options: { fen: string | null; enabled: boolean; multiPv: number }) => {
    const live = options.fen !== null && options.enabled;
    return {
      evalCp: live ? 20 : null,
      evalMate: null,
      pvLines: live
        ? Array.from({ length: engineState.lineCount }, (_, i) => ({
            multipv: i + 1,
            depth: 10,
            moves: [i === 0 ? engineState.pvFirstMove : (SECONDARY_ENGINE_MOVES[i - 1] ?? 'a7a6')],
            evalCp: 20,
            evalMate: null,
          }))
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
  engineState.lineCount = 3;
});

/** The "Line N" prefix of every engine row badge, in render order. */
function rowRanks(): string[] {
  return screen.queryAllByLabelText(/^Line \d+:/).map((el) => (el.getAttribute('aria-label') ?? '').split(':')[0]!);
}

function renderHarness() {
  return render(
    <TooltipProvider>
      <Harness />
    </TooltipProvider>,
  );
}

describe('TrainLineChips + TrainMoveTreeList over the real tree hook', () => {
  it('tracer: the list shows the chip move plus a dimmed preview; a preview tap commits it', () => {
    renderHarness();
    const list = () => screen.getByTestId('train-move-tree');

    expect(screen.getByTestId('train-chip-your').getAttribute('aria-pressed')).toBe('true');
    // Seed item 1: e4 is the only real node, e5/Nf3 are the preview of the graded line.
    expect(within(list()).getByText('e4').closest('[data-testid^="variation-node-"]')).toBeTruthy();
    expect(screen.getByTestId('variation-preview-0').textContent).toContain('e5');
    expect(screen.getByTestId('variation-preview-1').textContent).toContain('Nf3');
    expect(within(list()).queryByTestId('variation-preview-2')).toBeNull();
    // No eval pill in the move list; the chip keeps the frozen graded eval.
    expect(screen.queryByTestId('variation-preview-eval')).toBeNull();
    expect(screen.getByTestId('train-chip-your-eval').getAttribute('title')).toBe('Graded eval');

    // Tapping the e5 preview token commits it: the board moves and e5 becomes a real node.
    fireEvent.click(screen.getByTestId('variation-preview-0'));
    expect(screen.getByTestId('harness-fen').textContent).toBe(fenAfter('e4', 'e5'));
    expect(within(list()).getByText('e5').closest('[data-testid^="variation-node-"]')).toBeTruthy();

    // A chip tap from another chip's line returns to the puzzle position.
    fireEvent.click(screen.getByTestId('train-chip-best'));
    expect(screen.getByTestId('harness-fen').textContent).toBe(START_FEN);
    expect(screen.getByTestId('train-chip-best').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('train-chip-your').getAttribute('aria-pressed')).toBe('false');
    expect(within(list()).getByText('d4')).toBeTruthy();
    expect(screen.getByTestId('variation-preview-0').textContent).toContain('d5');
    expect(screen.getByTestId('variation-preview-1').textContent).toContain('c4');
    expect(within(list()).queryByText('Nf3')).toBeNull();

    fireEvent.click(within(list()).getByText('d4'));
    expect(screen.getByTestId('harness-fen').textContent).toBe(fenAfter('d4'));
  });

  it('a preview token tap at the puzzle position plays the chip move plus the tapped plies', () => {
    renderHarness();
    fireEvent.click(screen.getByTestId('variation-preview-1'));
    expect(screen.getByTestId('harness-fen').textContent).toBe(fenAfter('e4', 'e5', 'Nf3'));
  });

  it('the Stockfish row is absent at the puzzle position and shown after stepping onto a node', () => {
    renderHarness();
    expect(screen.queryByTestId('train-sf-row')).toBeNull();
    fireEvent.click(within(screen.getByTestId('train-move-tree')).getByText('e4'));
    expect(screen.getByTestId('train-sf-row')).toBeTruthy();
  });

  it('the row shows all lines from Line 1 at a previewed leaf and on a node with children', () => {
    renderHarness();
    const list = () => screen.getByTestId('train-move-tree');

    // e4 is a leaf with a preview. The row still leads with Line 1 (the
    // solid-blue best line carrying the live eval) next to the dimmed preview.
    fireEvent.click(within(list()).getByText('e4'));
    expect(screen.getByTestId('variation-preview-0')).toBeTruthy();
    expect(rowRanks()).toEqual(['Line 1', 'Line 2']);
    expect(screen.getByTestId('engine-line-0-move-0')).toBeTruthy();

    // Commit the preview move, then step back: e4 now has a child, so no preview.
    fireEvent.click(screen.getByTestId('variation-preview-0'));
    // After 1.e4 e5 the row numbers from the shown position ("2."), not from a fresh
    // game ("1.", the bug before startPly was passed).
    const row = screen.getByTestId('train-sf-row');
    expect(within(row).queryAllByText('2.').length).toBeGreaterThan(0);
    expect(within(row).queryAllByText('1.')).toHaveLength(0);
    fireEvent.click(within(list()).getByText('e4'));
    expect(screen.queryByTestId('variation-preview-0')).toBeNull();
    expect(rowRanks()).toEqual(['Line 1', 'Line 2']);
  });

  it('a hand-played fork off the first moves renders the Stockfish row', () => {
    renderHarness();
    // At the puzzle position the row is absent.
    expect(screen.queryByTestId('train-sf-row')).toBeNull();

    // Nc3 matches no chip first move (Move = e4, Best = d4), so it forks a sideline.
    fireEvent.click(screen.getByTestId('harness-play-nc3'));
    expect(screen.getByTestId('train-sf-row')).toBeTruthy();
    // The row is a sibling of the list wrapper, so list queries never see its moves.
    expect(within(screen.getByTestId('train-move-tree')).queryByTestId('train-sf-row')).toBeNull();
  });
});

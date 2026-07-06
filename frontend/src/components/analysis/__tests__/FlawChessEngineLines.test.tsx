// @vitest-environment jsdom
/**
 * Phase 155 Plan 03 — FlawChessEngineLines render tests.
 * Replaces the Plan 01 Wave 0 `it.todo` scaffolds with real assertions,
 * mirroring EngineLines.test.tsx's chip-rendering + score-badge assertion
 * style against a `RankedLine[]` fixture instead of `PvLine[]`.
 *
 * Verifies:
 *  - MAX_LINES=3 row cap from a 4-line fixture (D-08)
 *  - modalPath renders SAN chips, first 5 visible + expand for a >5-ply path
 *    (DISPLAY-02)
 *  - the brown practical badge shows the practical (expected-score-derived,
 *    white-POV cp) number, and the blue objective eval next to it shows the
 *    (white-POV cp) eval of the same move, for a known fixture (DISPLAY-03)
 *  - clicking a chip calls onMoveClick with the expected UCI prefix (D-10)
 *  - a null objectiveEvalCp renders the "…" placeholder without crashing
 *  - no rendered string contains "best move" unqualified (D-06/ARROW-04)
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { FlawChessEngineLines } from '../FlawChessEngineLines';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { RankedLine } from '@/lib/engine/types';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ─── Fixtures ─────────────────────────────────────────────────────────────────

// Ruy Lopez opening — 7 plies, valid from START_FEN, so replayPvLine produces
// real SAN for every move (needed to exercise the >5-ply expand chevron).
const LINE_1: RankedLine = {
  rootMove: 'e2e4',
  practicalScore: 0.9, // white rootMover → expectedScoreToWhitePovCp ≈ +596.7cp → "+6.0"
  objectiveEvalCp: 300, // → "+3.0"
  modalPath: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6', 'b5a4'],
  visits: 120,
};

const LINE_2: RankedLine = {
  rootMove: 'd2d4',
  practicalScore: 0.6,
  objectiveEvalCp: 50, // → "+0.5"
  modalPath: ['d2d4', 'd7d5'],
  visits: 80,
};

const LINE_3: RankedLine = {
  rootMove: 'c2c4',
  practicalScore: 0.5,
  objectiveEvalCp: null, // → "…" placeholder
  modalPath: ['c2c4'],
  visits: 40,
};

const LINE_4: RankedLine = {
  rootMove: 'g1f3',
  practicalScore: 0.4,
  objectiveEvalCp: -20,
  modalPath: ['g1f3'],
  visits: 20,
};

const FOUR_LINES: RankedLine[] = [LINE_1, LINE_2, LINE_3, LINE_4];

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('FlawChessEngineLines', () => {
  it('renders exactly 3 rows from a 4-line fixture (MAX_LINES=3, D-08)', () => {
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={FOUR_LINES}
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={vi.fn()}
        />
      </TooltipProvider>,
    );

    // Lines 0-2 render (their first move chip is present)...
    expect(screen.getByTestId('flawchess-line-0-move-0')).toBeTruthy();
    expect(screen.getByTestId('flawchess-line-1-move-0')).toBeTruthy();
    expect(screen.getByTestId('flawchess-line-2-move-0')).toBeTruthy();
    // ...line 3 (the 4th fixture) does not.
    expect(screen.queryByTestId('flawchess-line-3-move-0')).toBeNull();
  });

  it('renders modalPath as SAN chips, first MAX_PLIES=5 plies + expand chevron (DISPLAY-02)', () => {
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={[LINE_1]}
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={vi.fn()}
        />
      </TooltipProvider>,
    );

    // Collapsed: first 5 plies visible, plies 5 and 6 are not.
    expect(screen.getByTestId('flawchess-line-0-move-0')).toBeTruthy();
    expect(screen.getByTestId('flawchess-line-0-move-4')).toBeTruthy();
    expect(screen.queryByTestId('flawchess-line-0-move-5')).toBeNull();

    fireEvent.click(screen.getByTestId('flawchess-line-0-expand'));

    // Expanded: the remaining plies are now rendered.
    expect(screen.getByTestId('flawchess-line-0-move-5')).toBeTruthy();
    expect(screen.getByTestId('flawchess-line-0-move-6')).toBeTruthy();
  });

  it('no chevron when the modal path is <= 5 plies', () => {
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={[LINE_2]} // 2 plies
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.queryByTestId('flawchess-line-0-expand')).toBeNull();
  });

  it('renders the objective/practical score pair per line (DISPLAY-03)', () => {
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={[LINE_1]}
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={vi.fn()}
        />
      </TooltipProvider>,
    );

    // Practical: practicalScore=0.9, rootMover=white → expectedScoreToWhitePovCp
    // ≈ +596.7cp → formatScore → "+6.0" (the brown practical badge).
    expect(screen.getByText('+6.0')).toBeTruthy();
    // Objective: 300cp white-POV → "+3.0", rendered in Stockfish blue next to the badge.
    expect(screen.getByText('+3.0')).toBeTruthy();
    // Accessible label frames it as practical "for you" / objective — never the
    // bare phrase "best move" unqualified (D-06/ARROW-04).
    expect(
      screen.getByLabelText('Line 1: practically +6.0 for you, objectively +3.0'),
    ).toBeTruthy();
  });

  it('a null objectiveEvalCp renders the "…" placeholder without crashing', () => {
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={[LINE_3]}
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.getByText('…')).toBeTruthy();
  });

  it('clicking a modal-path chip calls onMoveClick with the expected UCI prefix (D-10)', () => {
    const onMoveClick = vi.fn();
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={[LINE_1]}
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={onMoveClick}
        />
      </TooltipProvider>,
    );

    // Clicking move index 2 (g1f3) grafts the whole prefix up to it, not just
    // the single clicked move.
    fireEvent.click(screen.getByTestId('flawchess-line-0-move-2'));
    expect(onMoveClick).toHaveBeenCalledTimes(1);
    expect(onMoveClick).toHaveBeenCalledWith(['e2e4', 'e7e5', 'g1f3']);
  });

  it('move chips are <button> elements (semantic HTML)', () => {
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={[LINE_1]}
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={vi.fn()}
        />
      </TooltipProvider>,
    );
    const chip = screen.getByTestId('flawchess-line-0-move-0');
    expect(chip.tagName.toLowerCase()).toBe('button');
  });

  it('isSearching && empty rankedLines → shows the 3-row skeleton', () => {
    render(
      <FlawChessEngineLines
        rankedLines={[]}
        isSearching={true}
        baseFen={START_FEN}
        rootMover="white"
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getByTestId('analysis-flawchess-loading')).toBeTruthy();
  });

  it('!isSearching && empty rankedLines → renders no rows and no skeleton', () => {
    render(
      <FlawChessEngineLines
        rankedLines={[]}
        isSearching={false}
        baseFen={START_FEN}
        rootMover="white"
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('analysis-flawchess-loading')).toBeNull();
    expect(screen.queryByTestId('flawchess-line-0-move-0')).toBeNull();
  });

  it('never renders the bare phrase "best move" unqualified anywhere', () => {
    render(
      <TooltipProvider>
        <FlawChessEngineLines
          rankedLines={FOUR_LINES}
          isSearching={false}
          baseFen={START_FEN}
          rootMover="white"
          onMoveClick={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.queryByText(/best move/i)).toBeNull();
  });
});

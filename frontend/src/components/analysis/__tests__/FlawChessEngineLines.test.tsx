// @vitest-environment jsdom
/**
 * Phase 155 Plan 03 — FlawChessEngineLines render tests.
 * Replaces the Plan 01 Wave 0 `it.todo` scaffolds with real assertions,
 * mirroring EngineLines.test.tsx's chip-rendering + score-badge assertion
 * style against a `RankedLine[]` fixture instead of `PvLine[]`.
 *
 * Verifies:
 *  - MAX_LINES=2 row cap from a 4-line fixture (D-08)
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
// real SAN for every move (needed to exercise the >4-ply expand chevron).
const LINE_1: RankedLine = {
  rootMove: 'e2e4',
  practicalScore: 0.9, // white rootMover → expectedScoreToWhitePovCp ≈ +596.7cp → "+6.0"
  objectiveEvalCp: 300, // → "+3.0"
  modalPath: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6', 'b5a4'],
  // Per-ply hover-header stats, index-aligned with modalPath. First ply:
  // +0.2 eval, 45% Maia — asserted by the hover-header test below.
  modalStats: [
    { objectiveEvalCp: 20, maiaProb: 0.45 },
    { objectiveEvalCp: -10, maiaProb: 0.38 },
    { objectiveEvalCp: 15, maiaProb: 0.5 },
    { objectiveEvalCp: 5, maiaProb: 0.2 },
    { objectiveEvalCp: 25, maiaProb: 0.6 },
    { objectiveEvalCp: 30, maiaProb: 0.55 },
    { objectiveEvalCp: 40, maiaProb: 0.7 },
  ],
  visits: 120,
};

const LINE_2: RankedLine = {
  rootMove: 'd2d4',
  practicalScore: 0.6,
  objectiveEvalCp: 50, // → "+0.5"
  modalPath: ['d2d4', 'd7d5'],
  modalStats: [
    { objectiveEvalCp: 40, maiaProb: 0.35 },
    { objectiveEvalCp: 45, maiaProb: 0.42 },
  ],
  visits: 80,
};

const LINE_3: RankedLine = {
  rootMove: 'c2c4',
  practicalScore: 0.5,
  objectiveEvalCp: null, // → "…" placeholder
  modalPath: ['c2c4'],
  modalStats: [{ objectiveEvalCp: null, maiaProb: null }],
  visits: 40,
};

const LINE_4: RankedLine = {
  rootMove: 'g1f3',
  practicalScore: 0.4,
  objectiveEvalCp: -20,
  modalPath: ['g1f3'],
  modalStats: [{ objectiveEvalCp: -20, maiaProb: 0.15 }],
  visits: 20,
};

const FOUR_LINES: RankedLine[] = [LINE_1, LINE_2, LINE_3, LINE_4];

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('FlawChessEngineLines', () => {
  it('renders exactly 2 rows from a 4-line fixture (MAX_LINES=2, D-08)', () => {
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

    // Lines 0-1 render (their first move chip is present)...
    expect(screen.getByTestId('flawchess-line-0-move-0')).toBeTruthy();
    expect(screen.getByTestId('flawchess-line-1-move-0')).toBeTruthy();
    // ...lines 2 and 3 (the 3rd/4th fixtures) do not.
    expect(screen.queryByTestId('flawchess-line-2-move-0')).toBeNull();
    expect(screen.queryByTestId('flawchess-line-3-move-0')).toBeNull();
  });

  it('renders modalPath as SAN chips, first MAX_PLIES=4 plies + expand chevron (DISPLAY-02)', () => {
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

    // Collapsed: first 4 plies visible, plies 4+ are not (one fewer than the
    // Stockfish card — the objective-eval aside makes this row wider, so 4 is
    // what fits on a single line).
    expect(screen.getByTestId('flawchess-line-0-move-0')).toBeTruthy();
    expect(screen.getByTestId('flawchess-line-0-move-3')).toBeTruthy();
    expect(screen.queryByTestId('flawchess-line-0-move-4')).toBeNull();

    fireEvent.click(screen.getByTestId('flawchess-line-0-expand'));

    // Expanded: the remaining plies are now rendered.
    expect(screen.getByTestId('flawchess-line-0-move-4')).toBeTruthy();
    expect(screen.getByTestId('flawchess-line-0-move-6')).toBeTruthy();
  });

  it('no chevron when the modal path is <= 4 plies', () => {
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

  it('move hover header shows the ply Stockfish eval (left) + raw Maia probability (right)', async () => {
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
    // Focus opens the Radix tooltip instantly (no hover delay). LINE_1's first
    // ply stat is { objectiveEvalCp: 20, maiaProb: 0.45 } → "+0.2" and "45%".
    // Radix renders a visually-hidden accessible duplicate of the content, so
    // each label appears more than once — assert at least one match.
    fireEvent.focus(screen.getByTestId('flawchess-line-0-move-0'));
    expect((await screen.findAllByLabelText('Stockfish evaluation +0.2')).length).toBeGreaterThan(0);
    expect((await screen.findAllByLabelText('Maia probability 45%')).length).toBeGreaterThan(0);
  });

  it('move hover header falls back to the placeholder glyph when a ply has no stats', async () => {
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
    // LINE_3's only ply has null eval + null Maia → both slots show "…".
    fireEvent.focus(screen.getByTestId('flawchess-line-0-move-0'));
    expect((await screen.findAllByLabelText('Stockfish evaluation …')).length).toBeGreaterThan(0);
    expect((await screen.findAllByLabelText('Maia probability …')).length).toBeGreaterThan(0);
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

  it('on touch, the first tap reveals the preview and the second tap plays the move', async () => {
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
    const chip = screen.getByTestId('flawchess-line-0-move-0');

    // First tap: a real pointer click (detail 1) with the preview closed at
    // pointerdown → reveals the preview, does NOT play.
    fireEvent.pointerDown(chip, { pointerType: 'touch' });
    fireEvent.click(chip, { detail: 1 });
    expect(onMoveClick).not.toHaveBeenCalled();
    expect((await screen.findAllByLabelText('Stockfish evaluation +0.2')).length).toBeGreaterThan(0);

    // Second tap: pointerdown now sees the preview already open → plays the move
    // (the one-move prefix for chip index 0).
    fireEvent.pointerDown(chip, { pointerType: 'touch' });
    fireEvent.click(chip, { detail: 1 });
    expect(onMoveClick).toHaveBeenCalledTimes(1);
    expect(onMoveClick).toHaveBeenCalledWith(['e2e4']);
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

  it('isSearching && empty rankedLines → shows the 2-row skeleton', () => {
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

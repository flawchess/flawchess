// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { MoveExplorer } from '../MoveExplorer';
import type { NextMoveEntry } from '@/types/api';

// Vitest 4 does not auto-cleanup RTL mounts — rendered DOM from a previous
// test bleeds into the next one's screen queries if we don't explicitly unmount.
afterEach(() => {
  cleanup();
});

// Starting position FEN — chess.js can compute legal moves from this without
// any history. The three SAN tokens below (e4, d4, Nf3) are all legal first
// moves so they survive MoveExplorer's moveMap filter.
const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
// A position one ply later — used to trigger the position-change reset path.
const AFTER_E4_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';

function makeEntry(overrides: Partial<NextMoveEntry> & Pick<NextMoveEntry, 'move_san'>): NextMoveEntry {
  return {
    move_san: overrides.move_san,
    game_count: 100,
    wins: 50,
    draws: 25,
    losses: 25,
    win_pct: 50,
    draw_pct: 25,
    loss_pct: 25,
    result_hash: '0',
    result_fen: '',
    transposition_count: 100,
    ...overrides,
  };
}

function makeMoves(): NextMoveEntry[] {
  return [makeEntry({ move_san: 'e4' }), makeEntry({ move_san: 'd4' }), makeEntry({ move_san: 'Nf3' })];
}

// jsdom does not implement Element.prototype.scrollIntoView. Stub before each
// test so MoveExplorer's effect can call it without throwing, and we can assert
// call counts.
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe('MoveExplorer — highlightedMove prop', () => {
  it('renders without highlight: no inline background tint on any row', () => {
    render(
      <MoveExplorer
        moves={makeMoves()}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const row = screen.getByTestId('move-explorer-row-e4');
    expect(row.style.backgroundColor || '').toBe('');
  });

  it('renders severity-tinted background on the matching row', () => {
    render(
      <MoveExplorer
        moves={makeMoves()}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
        highlightedMove={{ san: 'e4', color: '#ff0000', pulse: true }}
      />,
    );
    const matched = screen.getByTestId('move-explorer-row-e4');
    const other = screen.getByTestId('move-explorer-row-d4');
    // jsdom normalizes #ff000026 to rgba(255, 0, 0, 0.149).
    expect(matched.style.backgroundColor.toLowerCase()).toContain('rgba(255, 0, 0');
    expect(other.style.backgroundColor || '').toBe('');
  });

  it('does NOT scroll the matching row into view (deeplinks scroll to top instead)', () => {
    render(
      <MoveExplorer
        moves={makeMoves()}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
        highlightedMove={{ san: 'd4', color: '#00ff00', pulse: true }}
      />,
    );
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });

  it('fires onHighlightConsumed once when position changes while a highlight is active', () => {
    const onHighlightConsumed = vi.fn();
    const { rerender } = render(
      <MoveExplorer
        moves={makeMoves()}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
        highlightedMove={{ san: 'e4', color: '#ff0000', pulse: true }}
        onHighlightConsumed={onHighlightConsumed}
      />,
    );
    expect(onHighlightConsumed).not.toHaveBeenCalled();
    rerender(
      <MoveExplorer
        moves={makeMoves()}
        isLoading={false}
        isError={false}
        position={AFTER_E4_FEN}
        onMoveClick={() => {}}
        highlightedMove={{ san: 'e4', color: '#ff0000', pulse: true }}
        onHighlightConsumed={onHighlightConsumed}
      />,
    );
    expect(onHighlightConsumed).toHaveBeenCalledTimes(1);
  });

  it('does NOT fire onHighlightConsumed when only the moves array identity changes (e.g. query resolution)', () => {
    // Regression: TanStack Query swaps the moves reference when the next-moves
    // request resolves on a freshly-mounted explorer tab. Treating that as a
    // clear signal cut off deep-link arrow pulses mid-animation.
    const onHighlightConsumed = vi.fn();
    const movesA = makeMoves();
    const movesB = makeMoves();  // different reference, same shape
    const { rerender } = render(
      <MoveExplorer
        moves={movesA}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
        highlightedMove={{ san: 'e4', color: '#ff0000', pulse: true }}
        onHighlightConsumed={onHighlightConsumed}
      />,
    );
    expect(onHighlightConsumed).not.toHaveBeenCalled();
    rerender(
      <MoveExplorer
        moves={movesB}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
        highlightedMove={{ san: 'e4', color: '#ff0000', pulse: true }}
        onHighlightConsumed={onHighlightConsumed}
      />,
    );
    expect(onHighlightConsumed).not.toHaveBeenCalled();
  });

  it('fires onHighlightConsumed once when any row is clicked while a highlight is active', () => {
    const onHighlightConsumed = vi.fn();
    render(
      <MoveExplorer
        moves={makeMoves()}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
        highlightedMove={{ san: 'e4', color: '#ff0000', pulse: true }}
        onHighlightConsumed={onHighlightConsumed}
      />,
    );
    fireEvent.click(screen.getByTestId('move-explorer-row-d4'));
    expect(onHighlightConsumed).toHaveBeenCalledTimes(1);
  });
});

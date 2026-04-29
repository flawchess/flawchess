// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import type * as React from 'react';

// Stub Tooltip so renders don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => children,
}));

// Phase 77: stub curated data — sentinel key matches the WHITE-only
// derivation of RESULT_FEN_AFTER_E5 below (post-1.e4 e5 board FEN with
// black pieces stripped). BLACK_TROLL_KEYS stays empty so the side-routing
// test can assert "same result_fen but black-to-move => no icon".
vi.mock('@/data/trollOpenings', () => ({
  WHITE_TROLL_KEYS: new Set(['8/8/8/8/4P3/8/PPPP1PPP/RNBQKBNR']),
  BLACK_TROLL_KEYS: new Set<string>(),
}));

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
// Board FEN after 1.e4 e5 — when stripped to white-only, derives to the
// WHITE_TROLL_KEYS sentinel '8/8/8/8/4P3/8/PPPP1PPP/RNBQKBNR'.
const RESULT_FEN_AFTER_E5 = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR';
// Board FEN of the starting position — derives to a non-troll key.
const RESULT_FEN_NOT_TROLL = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR';

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
    // Phase 77: must be a valid 8-rank board FEN — MoveExplorer now calls
    // isTrollPosition(result_fen, side) which throws on malformed input. The
    // starting-position board FEN is a safe non-troll default; tests that
    // exercise the troll path override this explicitly.
    result_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR',
    transposition_count: 100,
    score: 0.625,           // Phase 76 D-05
    confidence: 'high',     // Phase 76 D-05
    p_value: 0.05,          // Phase 76 D-05
    ...overrides,
  };
}

// Use score: 0.50 (neutral) so the severity-tint path produces GREY and the
// existing highlightedMove tests can assert "no background tint" cleanly.
function makeMoves(): NextMoveEntry[] {
  return [
    makeEntry({ move_san: 'e4', score: 0.50 }),
    makeEntry({ move_san: 'd4', score: 0.50 }),
    makeEntry({ move_san: 'Nf3', score: 0.50 }),
  ];
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

describe('Phase 76 — Conf column + mute extension', () => {
  it('renders the Conf header cell with data-testid="move-explorer-th-conf"', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4' })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const th = screen.getByTestId('move-explorer-th-conf');
    expect(th.textContent?.trim()).toBe('Conf');
  });

  it('renders "low" / "med" / "high" labels per entry.confidence when the effect is of interest', () => {
    render(
      <MoveExplorer
        moves={[
          makeEntry({ move_san: 'e4', confidence: 'low', score: 0.625 }),
          makeEntry({ move_san: 'd4', confidence: 'medium', score: 0.625 }),
          makeEntry({ move_san: 'c4', confidence: 'high', score: 0.625 }),
        ]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    expect(screen.getByTestId('move-explorer-row-e4').textContent).toContain('low');
    expect(screen.getByTestId('move-explorer-row-d4').textContent).toContain('med');
    expect(screen.getByTestId('move-explorer-row-c4').textContent).toContain('high');
  });

  it('hides the confidence indicator when |score - 0.5| < 0.05 (effect below interest threshold)', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', confidence: 'high', game_count: 100, score: 0.52 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const row = screen.getByTestId('move-explorer-row-e4');
    // The "high" confidence label must not render — only the move SAN, game count, and (empty) WDL bar remain.
    expect(row.textContent).not.toContain('high');
    expect(row.textContent).not.toContain('med');
    expect(row.textContent).not.toContain('low');
  });

  it('hides the confidence indicator when game_count < 10', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', confidence: 'high', game_count: 9, score: 0.625 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const row = screen.getByTestId('move-explorer-row-e4');
    expect(row.textContent).not.toContain('high');
  });

  it('does NOT mute the row based on confidence alone when game_count >= 10', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', confidence: 'low', game_count: 100 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const row = screen.getByTestId('move-explorer-row-e4');
    expect(row.getAttribute('style') ?? '').not.toMatch(/opacity:\s*0\.5/);
  });

  it('mutes the row when entry.game_count < 10', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', confidence: 'high', game_count: 9 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const row = screen.getByTestId('move-explorer-row-e4');
    expect(row.getAttribute('style')).toMatch(/opacity:\s*0\.5/);
  });

  it('does NOT mute the row when game_count >= 10', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', confidence: 'high', game_count: 50 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const row = screen.getByTestId('move-explorer-row-e4');
    expect(row.getAttribute('style') ?? '').not.toMatch(/opacity:\s*0\.5/);
  });
});

describe('Phase 77 — Troll-opening inline icon', () => {
  it('renders troll icon when result_fen matches WHITE_TROLL_KEYS and parent is white-to-move', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', result_fen: RESULT_FEN_AFTER_E5 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}      // white to move => sideJustMoved = 'white'
        onMoveClick={() => {}}
      />,
    );
    const icon = screen.getByTestId('move-list-row-e4-troll-icon');
    expect(icon.tagName.toLowerCase()).toBe('svg');
  });

  it('does not render troll icon when result_fen is not in the troll set', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'd4', result_fen: RESULT_FEN_NOT_TROLL })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    expect(screen.queryByTestId('move-list-row-d4-troll-icon')).toBeNull();
  });

  it('routes to BLACK_TROLL_KEYS when parent position is black-to-move (D-10)', () => {
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e5', result_fen: RESULT_FEN_AFTER_E5 })]}
        isLoading={false}
        isError={false}
        position={AFTER_E4_FEN}   // black to move => sideJustMoved = 'black'
        onMoveClick={() => {}}
      />,
    );
    // BLACK_TROLL_KEYS is empty in the mock; even though result_fen would
    // hit the white set sentinel, the white set is NOT consulted, so no
    // icon should render.
    expect(screen.queryByTestId('move-list-row-e5-troll-icon')).toBeNull();
  });

  it('icon renders on mobile and desktop with muted-foreground tint', () => {
    // D-07 reversed (post-77 polish): the smiley now shows on mobile too,
    // tinted to text-muted-foreground to match the confidence column.
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', result_fen: RESULT_FEN_AFTER_E5 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const icon = screen.getByTestId('move-list-row-e4-troll-icon');
    // SVG `.className` is an SVGAnimatedString — read the raw class attribute instead.
    const classes = icon.getAttribute('class') ?? '';
    expect(classes).toContain('inline-block');
    expect(classes).not.toContain('hidden');
    expect(classes).toContain('text-muted-foreground');
  });

  it('throws when position is a board-only FEN with no side-to-move token (Pitfall 7)', () => {
    // Suppress React's error-boundary logging for this assertion.
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() =>
      render(
        <MoveExplorer
          moves={[makeEntry({ move_san: 'e4', result_fen: RESULT_FEN_AFTER_E5 })]}
          isLoading={false}
          isError={false}
          position="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"  // no side-to-move token
          onMoveClick={() => {}}
        />,
      ),
    ).toThrow(/must be a full FEN with side-to-move/);
    consoleErrorSpy.mockRestore();
  });

  it('icon is exposed to assistive tech with role and label', () => {
    // Tooltip is visual-only, so the SVG itself carries role="img" + aria-label
    // for screen readers (commit d2983dc).
    render(
      <MoveExplorer
        moves={[makeEntry({ move_san: 'e4', result_fen: RESULT_FEN_AFTER_E5 })]}
        isLoading={false}
        isError={false}
        position={START_FEN}
        onMoveClick={() => {}}
      />,
    );
    const icon = screen.getByTestId('move-list-row-e4-troll-icon');
    expect(icon.getAttribute('role')).toBe('img');
    expect(icon.getAttribute('aria-label')).toBe('Considered a troll opening');
  });
});

// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';

// IntersectionObserver is not available in jsdom. Stub it as a class
// constructor that fires the callback synchronously on observe() so
// LazyMiniBoard mounts MiniBoard immediately and the arrow overlay renders
// without us having to mock LazyMiniBoard itself. (Quick task 260429-gmj —
// before this fix, `visible` stayed `false` and MiniBoard never mounted, so
// arrow-overlay assertions could not work.)
class MockIntersectionObserver {
  private cb: IntersectionObserverCallback;
  constructor(cb: IntersectionObserverCallback) {
    this.cb = cb;
  }
  observe = (el: Element) => {
    this.cb(
      [{ isIntersecting: true, target: el } as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    );
  };
  disconnect = vi.fn();
  unobserve = vi.fn();
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

// Mock react-chessboard to avoid SVG/canvas rendering in test environment
vi.mock('react-chessboard', () => ({
  Chessboard: vi.fn(() => null),
}));

// Stub the Tooltip primitive so renders don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => children,
}));

// useEvalCoverage calls useQuery which requires a QueryClientProvider.
// Return safe defaults so the component renders without a provider.
vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({ isPending: false, pendingCount: 0, pct: 100, totalCount: 0, isLoading: false }),
}));

import type * as React from 'react';

import { OpeningFindingCard } from './OpeningFindingCard';
import type { OpeningInsightFinding } from '@/types/insights';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

function makeFinding(overrides: Partial<OpeningInsightFinding> = {}): OpeningInsightFinding {
  return {
    color: 'black',
    classification: 'weakness',
    severity: 'major',
    opening_name: 'Sicilian Defense: Najdorf',
    opening_eco: 'B90',
    display_name: 'Sicilian Defense: Najdorf',
    entry_fen: 'rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6',
    entry_san_sequence: ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3', 'a6'],
    entry_full_hash: '111',
    candidate_move_san: 'Be2',
    resulting_full_hash: '222',
    n_games: 18,
    wins: 4,
    draws: 3,
    losses: 11,
    score: 0.30,            // gives clean "30%" prose
    confidence: 'medium',   // Phase 76 D-21
    p_value: 0.05,          // Phase 76 D-21
    ci_low: 0.25,
    ci_high: 0.35,
    // MG-entry eval fields (quick task 260506-u2b)
    avg_eval_pawns: 0.5,
    eval_n: 18,
    eval_ci_low_pawns: 0.2,
    eval_ci_high_pawns: 0.8,
    eval_p_value: 0.05,
    eval_confidence: 'medium',
    ...overrides,
  };
}

function renderCard(props: {
  finding: OpeningInsightFinding;
  idx?: number;
  evalBaselinePawns?: number;
  onFindingClick?: (f: OpeningInsightFinding) => void;
  onOpenGames?: (f: OpeningInsightFinding) => void;
}) {
  const {
    finding,
    idx = 0,
    evalBaselinePawns = 0.25,
    onFindingClick = () => {},
    onOpenGames = () => {},
  } = props;
  return render(
    <OpeningFindingCard
      finding={finding}
      idx={idx}
      evalBaselinePawns={evalBaselinePawns}
      onFindingClick={onFindingClick}
      onOpenGames={onOpenGames}
    />,
  );
}

afterEach(() => {
  cleanup();
});

describe('OpeningFindingCard', () => {
  it('renders score percent and "after <move>" caption (260507-t4r: prose replaced by bullet + caption)', () => {
    // The "Score X% after [move]" prose line is gone. Score is shown in the score bullet row;
    // the move anchor is a small caption under the miniboard.
    const finding = makeFinding({ classification: 'weakness', color: 'black', score: 0.30 });
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    // Score percent still appears in the score-text element
    expect(text).toMatch(/30%/);
    // Move anchor still appears as a caption under the miniboard
    expect(text).toMatch(/after/);
    // No "You score" / "as Black/White" (was already gone before this task)
    expect(text).not.toMatch(/You score/);
    expect(text).not.toMatch(/as Black/);
    expect(text).not.toMatch(/as White/);
  });

  it('renders score percent and "after <move>" caption for strength section', () => {
    const finding = makeFinding({ classification: 'strength', color: 'white', score: 0.58 });
    renderCard({ finding, idx: 1 });
    const card = screen.getByTestId('opening-finding-card-1');
    const text = card.textContent ?? '';
    expect(text).toMatch(/58%/);
    expect(text).toMatch(/after/);
    expect(text).not.toMatch(/You score/);
  });

  it('does NOT render "lose" or "win" verbs in prose (Phase 76 D-02)', () => {
    const finding = makeFinding();
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    expect(text).not.toMatch(/You lose/);
    expect(text).not.toMatch(/You win/);
  });

  it('score bullet row shows percent rounded to integer (no .toFixed precision in score-text)', () => {
    // 260507-t4r: the proseLine with .toFixed(1) fallback is gone.
    // The score-text element uses Math.round(score * 100)%.
    // At score=0.499, Math.round(49.9) = 50 — acceptable since the prose contradiction
    // guard was prose-specific and is no longer needed.
    const finding = makeFinding({ classification: 'weakness', score: 0.499 });
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    // Score shown as integer percent (50% is valid — contradiction guard was prose-only)
    expect(text).toMatch(/\d+%/);
  });

  it('applies ZONE_DANGER (red) border-left when score <= 0.45', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', score: 0.30 })}
        idx={2}
        evalBaselinePawns={0.25}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-2');
    expect(normalizeColor(card.style.borderLeftColor)).toBe(normalizeColor(ZONE_DANGER));
  });

  it('applies ZONE_NEUTRAL (blue) border-left when score sits in the 45-55% band', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', score: 0.49 })}
        idx={3}
        evalBaselinePawns={0.25}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-3');
    expect(normalizeColor(card.style.borderLeftColor)).toBe(normalizeColor(ZONE_NEUTRAL));
  });

  it('applies ZONE_SUCCESS (green) border-left when score >= 0.55', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'strength', score: 0.60 })}
        idx={4}
        evalBaselinePawns={0.25}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-4');
    expect(normalizeColor(card.style.borderLeftColor)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('Moves link calls onFindingClick with the finding', () => {
    const onFindingClick = vi.fn();
    const finding = makeFinding();
    render(
      <OpeningFindingCard
        finding={finding}
        idx={6}
        evalBaselinePawns={0.25}
        onFindingClick={onFindingClick}
        onOpenGames={() => {}}
      />,
    );
    // Dual layout: testid is duplicated across mobile + desktop blocks.
    const movesBtn = screen.getAllByTestId('opening-finding-card-6-moves')[0]!;
    fireEvent.click(movesBtn);
    expect(onFindingClick).toHaveBeenCalledWith(finding);
  });

  it('Games link calls onOpenGames with the finding and shows the n_games count', () => {
    const onOpenGames = vi.fn();
    const finding = makeFinding({ n_games: 42 });
    render(
      <OpeningFindingCard
        finding={finding}
        idx={7}
        evalBaselinePawns={0.25}
        onFindingClick={() => {}}
        onOpenGames={onOpenGames}
      />,
    );
    // Dual layout: testid is duplicated across mobile + desktop blocks.
    const gamesBtn = screen.getAllByTestId('opening-finding-card-7-games')[0]!;
    expect(gamesBtn.textContent).toMatch(/42/);
    expect(gamesBtn.textContent).toMatch(/Games/);
    fireEvent.click(gamesBtn);
    expect(onOpenGames).toHaveBeenCalledWith(finding);
  });

  it('clicking the card body itself does not trigger any callbacks (no whole-card deeplink)', () => {
    const onFindingClick = vi.fn();
    const onOpenGames = vi.fn();
    render(
      <OpeningFindingCard
        finding={makeFinding()}
        idx={8}
        evalBaselinePawns={0.25}
        onFindingClick={onFindingClick}
        onOpenGames={onOpenGames}
      />,
    );
    fireEvent.click(screen.getByTestId('opening-finding-card-8'));
    expect(onFindingClick).not.toHaveBeenCalled();
    expect(onOpenGames).not.toHaveBeenCalled();
  });

  it('renders the display_name + ECO in the header line', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ display_name: 'Caro-Kann Defense', opening_eco: 'B10' })}
        idx={9}
        evalBaselinePawns={0.25}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-9');
    expect(card.textContent).toContain('Caro-Kann Defense');
    expect(card.textContent).toContain('B10');
  });

  it('renders <unnamed line> sentinel as italic muted text (defensive)', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({
          opening_name: '<unnamed line>',
          display_name: '<unnamed line>',
        })}
        idx={10}
        evalBaselinePawns={0.25}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-10');
    const italicEl = card.querySelector('.italic');
    expect(italicEl).not.toBeNull();
    expect(italicEl?.textContent).toContain('<unnamed line>');
  });

  it('renders only the candidate move with PGN move-number notation in the prose', () => {
    const finding = makeFinding({
      entry_san_sequence: ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'],
      candidate_move_san: 'Nxd4',
    });
    render(
      <OpeningFindingCard
        finding={finding}
        idx={11}
        evalBaselinePawns={0.25}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const text = screen.getByTestId('opening-finding-card-11').textContent ?? '';
    expect(text).toContain('4.Nxd4');
    // Earlier entry plys should no longer appear in the rendered prose.
    expect(text).not.toContain('3.d4 cxd4');
  });

  describe('WDL bar row + eval bullet row (quick task 260506-u2b)', () => {
    it('renders the WDL chart row', () => {
      const finding = makeFinding({ confidence: 'medium' });
      renderCard({ finding, idx: 3 });
      // Dual layout: testid is duplicated across mobile + desktop blocks.
      const wdlRows = screen.getAllByTestId('opening-finding-card-3-wdl');
      expect(wdlRows.length).toBeGreaterThanOrEqual(1);
    });

    it('renders the score-bullet row (260507-t4r: score bullet added to Insights cards)', () => {
      const finding = makeFinding({ confidence: 'medium' });
      renderCard({ finding, idx: 3 });
      expect(screen.queryAllByTestId('opening-finding-card-3-score-bullet').length).toBeGreaterThanOrEqual(1);
    });

    it('does NOT render the legacy confidence-info testid', () => {
      const finding = makeFinding({ confidence: 'medium' });
      renderCard({ finding, idx: 3 });
      expect(screen.queryAllByTestId('opening-finding-card-3-confidence-info').length).toBe(0);
    });

    it('renders eval bullet container when eval_n > 0', () => {
      const finding = makeFinding({ eval_n: 18, avg_eval_pawns: 0.5 });
      renderCard({ finding, idx: 5 });
      // Dual layout: testid is duplicated across mobile + desktop blocks.
      const bullet = screen.getAllByTestId('opening-finding-card-5-bullet')[0]!;
      expect(bullet.querySelector('[data-testid="mini-bullet-chart"]')).not.toBeNull();
    });

    it('renders em-dash fallback in eval bullet when eval_n === 0', () => {
      const finding = makeFinding({ eval_n: 0, avg_eval_pawns: null });
      renderCard({ finding, idx: 5 });
      // Dual layout: testid is duplicated across mobile + desktop blocks.
      const evalText = screen.getAllByTestId('opening-finding-card-5-eval-text')[0]!;
      expect(evalText.textContent).toContain('—');
    });

    it('renders BulletConfidencePopover trigger when eval_n > 0', () => {
      const finding = makeFinding({ eval_n: 18, avg_eval_pawns: 0.5, eval_confidence: 'medium' });
      renderCard({ finding, idx: 5 });
      // Dual layout: testid is duplicated across mobile + desktop blocks.
      const popovers = screen.getAllByTestId('opening-finding-card-5-bullet-popover');
      expect(popovers.length).toBeGreaterThanOrEqual(1);
    });

    it('does NOT render the legacy Confidence: <level> text line', () => {
      const finding = makeFinding({ confidence: 'medium' });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.textContent ?? '').not.toMatch(/Confidence:/);
    });

    it('applies UNRELIABLE_OPACITY when finding.confidence === "low"', () => {
      const finding = makeFinding({ confidence: 'low', n_games: 100 });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.getAttribute('style')).toMatch(/opacity:\s*0\.5/);
    });

    it('applies UNRELIABLE_OPACITY when finding.n_games < 10', () => {
      const finding = makeFinding({ confidence: 'high', n_games: 9 });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.getAttribute('style')).toMatch(/opacity:\s*0\.5/);
    });

    it('does NOT apply UNRELIABLE_OPACITY when n_games >= 10 AND confidence !== "low"', () => {
      const finding = makeFinding({ confidence: 'high', n_games: 100 });
      renderCard({ finding, idx: 0 });
      const card = screen.getByTestId('opening-finding-card-0');
      expect(card.getAttribute('style') ?? '').not.toMatch(/opacity:\s*0\.5/);
    });
  });

  describe('Quick task 260429-gmj — score-colored after-move arrow', () => {
    // Test A: arrow overlay renders in both mobile + desktop layouts.
    it('renders <svg data-testid="mini-board-arrow-overlay"> in both mobile and desktop layouts', () => {
      const finding = makeFinding({
        entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        candidate_move_san: 'e4',
      });
      renderCard({ finding, idx: 0 });
      const overlays = screen.getAllByTestId('mini-board-arrow-overlay');
      expect(overlays.length).toBe(2); // one in sm:hidden, one in hidden sm:flex
    });

    // Test B: arrow color is driven by score zone (matches Moves-tab scoreZoneColor).
    it.each([
      [0.30, ZONE_DANGER] as const,    // <= 0.45 → red
      [0.45, ZONE_DANGER] as const,    // boundary inclusive
      [0.49, ZONE_NEUTRAL] as const,   // in-between band → blue
      [0.55, ZONE_SUCCESS] as const,   // boundary inclusive
      [0.70, ZONE_SUCCESS] as const,   // >= 0.55 → green
    ])(
      'arrow path fill matches scoreZoneColor for score=%s',
      (score, expectedColor) => {
        const finding = makeFinding({
          score,
          entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
          candidate_move_san: 'e4',
        });
        renderCard({ finding, idx: 0 });
        const overlays = screen.getAllByTestId('mini-board-arrow-overlay');
        const path = overlays[0]!.querySelector('path');
        expect(path).not.toBeNull();
        expect(normalizeColor(path!.getAttribute('fill') ?? '')).toBe(normalizeColor(expectedColor));
      },
    );

    // Test C: illegal/unparseable SAN gracefully degrades to no arrow.
    it('does not render the arrow overlay when candidate_move_san is illegal in entry_fen', () => {
      const finding = makeFinding({
        entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
        candidate_move_san: 'Zz9',
      });
      renderCard({ finding, idx: 0 });
      // Card should still render without throwing.
      expect(screen.getByTestId('opening-finding-card-0')).toBeTruthy();
      expect(screen.queryAllByTestId('mini-board-arrow-overlay').length).toBe(0);
    });

    // Test D: arrow renders for both color sides (board flipped for black).
    it('renders the arrow overlay when finding.color === "black" (flipped board)', () => {
      const finding = makeFinding({
        color: 'black',
        // Position after 1.e4 — black to move. e5 is legal here.
        entry_fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
        candidate_move_san: 'e5',
      });
      renderCard({ finding, idx: 0 });
      const overlays = screen.getAllByTestId('mini-board-arrow-overlay');
      expect(overlays.length).toBe(2); // dual layout: one board per block
    });
  });
});

/**
 * jsdom normalizes CSS colors when round-tripped through `style.*` (e.g.
 * `oklch(0.50 0.14 260)` → `oklch(0.5 0.14 260)`). Strip whitespace + collapse
 * trailing zeros so test comparisons are insensitive to that normalization.
 */
function normalizeColor(value: string): string {
  // Strip trailing zeros from decimals (oklch(0.50 ...) ↔ oklch(0.5 ...)).
  return value.replace(/(\.\d*?)0+(?=\D|$)/g, '$1');
}

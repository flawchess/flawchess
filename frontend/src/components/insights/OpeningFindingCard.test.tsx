// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';

// IntersectionObserver is not available in jsdom — stub it as a class constructor.
class MockIntersectionObserver {
  observe = vi.fn();
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
import type * as React from 'react';

import { OpeningFindingCard } from './OpeningFindingCard';
import type { OpeningInsightFinding } from '@/types/insights';
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';

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
    ...overrides,
  };
}

function renderCard(props: { finding: OpeningInsightFinding; idx?: number }) {
  const { finding, idx = 0 } = props;
  return render(
    <OpeningFindingCard
      finding={finding}
      idx={idx}
      onFindingClick={() => {}}
      onOpenGames={() => {}}
    />,
  );
}

afterEach(() => {
  cleanup();
});

describe('OpeningFindingCard', () => {
  it('renders "You score X% as Black" prose for weakness section', () => {
    const finding = makeFinding({ classification: 'weakness', color: 'black', score: 0.30 });
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    // Both mobile + desktop branches render — text content includes both; check it contains the right pieces
    expect(text).toMatch(/You score/);
    expect(text).toMatch(/30%/);
    expect(text).toMatch(/Black/);
    expect(text).not.toMatch(/You lose/);
    expect(text).not.toMatch(/You win/);
  });

  it('renders "You score X% as White" prose for strength section', () => {
    const finding = makeFinding({ classification: 'strength', color: 'white', score: 0.58 });
    renderCard({ finding, idx: 1 });
    const card = screen.getByTestId('opening-finding-card-1');
    const text = card.textContent ?? '';
    expect(text).toMatch(/You score/);
    expect(text).toMatch(/58%/);
    expect(text).toMatch(/White/);
    expect(text).not.toMatch(/You lose/);
    expect(text).not.toMatch(/You win/);
  });

  it('does NOT render "lose" or "win" verbs in prose (Phase 76 D-02)', () => {
    const finding = makeFinding();
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    expect(text).not.toMatch(/You lose/);
    expect(text).not.toMatch(/You win/);
  });

  it('falls back to .toFixed(1) when rounded percent contradicts the section title', () => {
    // weakness with score = 0.499 would round to 50% (contradicts weakness label)
    const finding = makeFinding({ classification: 'weakness', score: 0.499 });
    renderCard({ finding, idx: 0 });
    const card = screen.getByTestId('opening-finding-card-0');
    const text = card.textContent ?? '';
    expect(text).toMatch(/49\.9%/);
    expect(text).not.toMatch(/\b50%/);
  });

  it('applies DARK_RED border-left for major weakness', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', severity: 'major' })}
        idx={2}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-2');
    expect(card.style.borderLeftColor).toBe(hexToRgb(DARK_RED));
  });

  it('applies LIGHT_RED border-left for minor weakness', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', severity: 'minor' })}
        idx={3}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-3');
    expect(card.style.borderLeftColor).toBe(hexToRgb(LIGHT_RED));
  });

  it('applies DARK_GREEN border-left for major strength', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'strength', severity: 'major' })}
        idx={4}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-4');
    expect(card.style.borderLeftColor).toBe(hexToRgb(DARK_GREEN));
  });

  it('applies LIGHT_GREEN border-left for minor strength', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'strength', severity: 'minor' })}
        idx={5}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-5');
    expect(card.style.borderLeftColor).toBe(hexToRgb(LIGHT_GREEN));
  });

  it('Moves link calls onFindingClick with the finding', () => {
    const onFindingClick = vi.fn();
    const finding = makeFinding();
    render(
      <OpeningFindingCard
        finding={finding}
        idx={6}
        onFindingClick={onFindingClick}
        onOpenGames={() => {}}
      />,
    );
    // Two layouts (mobile + desktop) both render — query all matching test ids and click the first.
    const movesBtns = screen.getAllByTestId('opening-finding-card-6-moves');
    fireEvent.click(movesBtns[0]!);
    expect(onFindingClick).toHaveBeenCalledWith(finding);
  });

  it('Games link calls onOpenGames with the finding and shows the n_games count', () => {
    const onOpenGames = vi.fn();
    const finding = makeFinding({ n_games: 42 });
    render(
      <OpeningFindingCard
        finding={finding}
        idx={7}
        onFindingClick={() => {}}
        onOpenGames={onOpenGames}
      />,
    );
    const gamesBtns = screen.getAllByTestId('opening-finding-card-7-games');
    expect(gamesBtns[0]!.textContent).toMatch(/42/);
    expect(gamesBtns[0]!.textContent).toMatch(/Games/);
    fireEvent.click(gamesBtns[0]!);
    expect(onOpenGames).toHaveBeenCalledWith(finding);
  });

  it('clicking the card body itself does not trigger any callbacks (no whole-card deeplink)', () => {
    const onFindingClick = vi.fn();
    const onOpenGames = vi.fn();
    render(
      <OpeningFindingCard
        finding={makeFinding()}
        idx={8}
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
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-10');
    const italicEl = card.querySelector('.italic');
    expect(italicEl).not.toBeNull();
    expect(italicEl?.textContent).toContain('<unnamed line>');
  });

  it('renders the trimmed SAN sequence (D-05) in the prose', () => {
    const finding = makeFinding({
      entry_san_sequence: ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'],
      candidate_move_san: 'Nxd4',
    });
    render(
      <OpeningFindingCard
        finding={finding}
        idx={11}
        onFindingClick={() => {}}
        onOpenGames={() => {}}
      />,
    );
    const text = screen.getByTestId('opening-finding-card-11').textContent ?? '';
    expect(text).toContain('...3.d4 cxd4 4.Nxd4');
  });

  describe('Phase 76 — Confidence indicator + mute', () => {
    it('renders Confidence: <level> line with the right data-testid', () => {
      const finding = makeFinding({ confidence: 'medium' });
      renderCard({ finding, idx: 3 });
      // Both mobile + desktop branches render confidence lines with same testid.
      // getAllByTestId returns both; check text content of the first.
      const lines = screen.getAllByTestId('opening-finding-card-3-confidence');
      expect(lines.length).toBeGreaterThanOrEqual(1);
      expect(lines[0]!.textContent).toMatch(/Confidence:\s*medium/);
    });

    it('renders all three confidence levels as full words (low/medium/high)', () => {
      for (const level of ['low', 'medium', 'high'] as const) {
        const finding = makeFinding({ confidence: level });
        renderCard({ finding, idx: 0 });
        const lines = screen.getAllByTestId('opening-finding-card-0-confidence');
        expect(lines[0]!.textContent).toMatch(new RegExp(level));
        cleanup();
      }
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
});

/**
 * jsdom returns inline style colors as rgb() strings, not the original hex.
 * Helper converts a hex like "#9B1C1C" to "rgb(155, 28, 28)".
 */
function hexToRgb(hex: string): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgb(${r}, ${g}, ${b})`;
}

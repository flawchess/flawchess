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
    win_rate: 4 / 18,
    loss_rate: 11 / 18,
    score: 5.5 / 18,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
});

describe('OpeningFindingCard', () => {
  it('renders weakness prose: "You lose {rate}% as {Color} after {seq} (n={n})"', () => {
    const finding = makeFinding({
      classification: 'weakness',
      color: 'black',
      loss_rate: 0.62,
      n_games: 18,
    });
    render(<OpeningFindingCard finding={finding} idx={0} onFindingClick={() => {}} />);
    // Prose contains "lose", "62%", "Black", "(n=18)"
    const text = screen.getByTestId('opening-finding-card-0').textContent ?? '';
    expect(text).toMatch(/lose/i);
    expect(text).toMatch(/62%/);
    expect(text).toMatch(/Black/);
    expect(text).toMatch(/\(n=18\)/);
  });

  it('renders strength prose: "You win {rate}% as {Color} after {seq} (n={n})"', () => {
    const finding = makeFinding({
      classification: 'strength',
      severity: 'minor',
      color: 'white',
      win_rate: 0.58,
      n_games: 25,
    });
    render(<OpeningFindingCard finding={finding} idx={1} onFindingClick={() => {}} />);
    const text = screen.getByTestId('opening-finding-card-1').textContent ?? '';
    expect(text).toMatch(/win/i);
    expect(text).toMatch(/58%/);
    expect(text).toMatch(/White/);
    expect(text).toMatch(/\(n=25\)/);
  });

  it('applies DARK_RED border-left for major weakness', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', severity: 'major' })}
        idx={2}
        onFindingClick={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-2');
    // borderLeftColor inline style is the hex from arrowColor.ts
    expect(card.style.borderLeftColor).toBe(hexToRgb(DARK_RED));
  });

  it('applies LIGHT_RED border-left for minor weakness', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ classification: 'weakness', severity: 'minor' })}
        idx={3}
        onFindingClick={() => {}}
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
      />,
    );
    const card = screen.getByTestId('opening-finding-card-5');
    expect(card.style.borderLeftColor).toBe(hexToRgb(LIGHT_GREEN));
  });

  it('calls onFindingClick with the finding when clicked, prevents default navigation', () => {
    const handleClick = vi.fn();
    const finding = makeFinding();
    render(<OpeningFindingCard finding={finding} idx={6} onFindingClick={handleClick} />);
    const card = screen.getByTestId('opening-finding-card-6');
    fireEvent.click(card);
    expect(handleClick).toHaveBeenCalledWith(finding);
  });

  it('renders the display_name + ECO in the header line', () => {
    render(
      <OpeningFindingCard
        finding={makeFinding({ display_name: 'Caro-Kann Defense', opening_eco: 'B10' })}
        idx={7}
        onFindingClick={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-7');
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
        idx={8}
        onFindingClick={() => {}}
      />,
    );
    const card = screen.getByTestId('opening-finding-card-8');
    const italicEl = card.querySelector('.italic');
    expect(italicEl).not.toBeNull();
    expect(italicEl?.textContent).toContain('<unnamed line>');
  });

  it('has aria-label naming the deep-link target', () => {
    const finding = makeFinding({
      display_name: 'Sicilian Defense',
      candidate_move_san: 'Nxd4',
    });
    render(<OpeningFindingCard finding={finding} idx={9} onFindingClick={() => {}} />);
    const card = screen.getByTestId('opening-finding-card-9');
    expect(card.getAttribute('aria-label')).toBe(
      'Open Sicilian Defense (Nxd4) in Move Explorer',
    );
  });

  it('renders the trimmed SAN sequence (D-05) in the prose', () => {
    const finding = makeFinding({
      entry_san_sequence: ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'],
      candidate_move_san: 'Nxd4',
    });
    render(<OpeningFindingCard finding={finding} idx={10} onFindingClick={() => {}} />);
    const text = screen.getByTestId('opening-finding-card-10').textContent ?? '';
    // trimMoveSequence yields "...3.d4 cxd4 4.Nxd4"
    expect(text).toContain('...3.d4 cxd4 4.Nxd4');
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

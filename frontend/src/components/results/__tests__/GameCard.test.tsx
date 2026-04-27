// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import type { ReactNode } from 'react';

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

// Stub Tooltip so tests don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
}));

import type { GameRecord } from '@/types/api';
import { GameCard } from '../GameCard';

afterEach(() => {
  cleanup();
});

const mockGame: GameRecord = {
  game_id: 1,
  platform: 'chess.com',
  platform_url: 'https://chess.com/game/abc123',
  white_username: 'Alice',
  black_username: 'Bob',
  white_rating: 1500,
  black_rating: 1600,
  user_color: 'white',
  user_result: 'win',
  opening_name: 'Sicilian Defense',
  opening_eco: 'B20',
  result_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  played_at: '2024-01-01T12:00:00Z',
  time_control_bucket: 'blitz',
  time_control_str: '300+3',
  termination: 'resignation',
  move_count: 40,
};

describe('GameCard', () => {
  it('renders without errors', () => {
    const { getByTestId } = render(<GameCard game={mockGame} />);
    expect(getByTestId(`game-card-${mockGame.game_id}`)).toBeDefined();
  });

  it('renders opening name in both mobile and desktop layouts', () => {
    const { getAllByTestId } = render(<GameCard game={mockGame} />);
    const openingElements = getAllByTestId(`game-card-opening-${mockGame.game_id}`);
    expect(openingElements.length).toBeGreaterThan(0);
    openingElements.forEach((el) => {
      expect(el.textContent).toBe('Sicilian Defense');
    });
  });

  it('renders time control bucket in both mobile and desktop layouts', () => {
    const { getAllByTestId } = render(<GameCard game={mockGame} />);
    const tcElements = getAllByTestId(`game-card-tc-${mockGame.game_id}`);
    expect(tcElements.length).toBeGreaterThan(0);
    tcElements.forEach((el) => {
      expect(el.textContent).toContain('blitz');
    });
  });
});

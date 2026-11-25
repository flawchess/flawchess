// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';

class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

vi.mock('react-chessboard', () => ({ Chessboard: vi.fn(() => null) }));
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
}));

import type { GameRecord } from '@/types/api';
import { GameCardList } from '../GameCardList';

const game: GameRecord = {
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
  ply_count: 80,
};

afterEach(cleanup);

function renderList(multiColumn?: boolean): { grid: HTMLElement; card: HTMLElement } {
  render(
    <GameCardList
      games={[game]}
      matchedCount={1}
      totalGames={1}
      offset={0}
      limit={24}
      onPageChange={vi.fn()}
      multiColumn={multiColumn}
    />,
  );
  return { grid: screen.getByTestId('game-card-grid'), card: screen.getByTestId('game-card-1') };
}

describe('GameCardList multiColumn', () => {
  it('lays compact cards out in columns sized by the list width', () => {
    const { grid, card } = renderList(true);
    expect(grid.className).toContain('auto-fill');
    // Compact: one body and the two-line header at every width, no one-line "vs" header.
    expect(screen.getAllByTestId('game-card-opening-1')).toHaveLength(1);
    expect(card.textContent).not.toContain('vs');
    expect(card.textContent).not.toContain('Moves');
    expect(card.querySelector('[class*="sm:hidden"]')).toBeNull();
  });

  it('stays a single column of full cards by default (Openings)', () => {
    const { grid, card } = renderList();
    expect(grid.className).not.toContain('grid-cols');
    expect(screen.getAllByTestId('game-card-opening-1')).toHaveLength(2);
    expect(card.textContent).toContain('vs');
    expect(card.textContent).toContain('Moves');
    expect(card.querySelectorAll('[class*="sm:hidden"]')).toHaveLength(2);
  });
});

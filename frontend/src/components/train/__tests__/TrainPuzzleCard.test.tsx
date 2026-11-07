// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type { TrainArchiveItem } from '@/types/train';

// Expose the props the card hands to the board, so the spoiler-free contract
// (pre-mistake FEN, no arrows) is asserted on the real call, not on pixels.
const boardProps = vi.fn();
vi.mock('@/components/board/LazyMiniBoard', () => ({
  LazyMiniBoard: (props: Record<string, unknown>) => {
    boardProps(props);
    return <div data-testid="mock-mini-board" />;
  },
}));

const trackFeature = vi.fn();
vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return {
    ...actual,
    trackFeature: (...args: unknown[]) => trackFeature(...args),
  };
});

import { TrainPuzzleCard } from '../TrainPuzzleCard';

const FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2';

function makeItem(overrides: Partial<TrainArchiveItem> = {}): TrainArchiveItem {
  return {
    game_id: 100,
    ply: 20,
    fen: FEN,
    last_move_uci: 'g1f3',
    user_color: 'white',
    last_solved_at: '2026-10-03T12:00:00Z',
    fail_count: 4,
    white_username: 'alice',
    black_username: 'bob',
    white_rating: 1500,
    black_rating: 1620,
    played_at: '2026-09-20T12:00:00Z',
    time_control_bucket: 'blitz',
    time_control_str: '600',
    ...overrides,
  };
}

// Globals are off, so testing-library does not auto-clean between tests.
afterEach(cleanup);

function renderCard(item: TrainArchiveItem, list: 'mastered' | 'parked' = 'mastered') {
  return render(
    <MemoryRouter>
      <TrainPuzzleCard item={item} list={list} />
    </MemoryRouter>,
  );
}

describe('TrainPuzzleCard board', () => {
  beforeEach(() => {
    boardProps.mockClear();
    trackFeature.mockClear();
  });

  it.each(['mastered', 'parked'] as const)(
    'gives the board the pre-mistake FEN, the arriving move and no arrows on the %s list',
    (list) => {
      renderCard(makeItem(), list);
      expect(boardProps).toHaveBeenCalled();
      const props = boardProps.mock.calls[0]![0] as Record<string, unknown>;
      expect(props.fen).toBe(FEN);
      expect(props.lastMove).toEqual({ from: 'g1', to: 'f3' });
      expect(props.flipped).toBe(false);
      expect('arrows' in props).toBe(false);
    },
  );

  it('flips the board for a black user', () => {
    renderCard(makeItem({ user_color: 'black' }));
    const props = boardProps.mock.calls[0]![0] as Record<string, unknown>;
    expect(props.flipped).toBe(true);
  });

  it('renders the empty board slot for an unreplayable PGN and keeps Analyze working', () => {
    renderCard(makeItem({ fen: null, last_move_uci: null }));
    expect(screen.getByTestId('train-puzzle-board-unavailable')).toBeTruthy();
    expect(screen.queryByTestId('mock-mini-board')).toBeNull();
    expect(screen.getByTestId('btn-train-puzzle-analyze').getAttribute('href')).toBe(
      '/analysis?game_id=100&ply=19',
    );
  });
});

describe('TrainPuzzleCard Analyze', () => {
  beforeEach(() => {
    trackFeature.mockClear();
  });

  it('links to the puzzle position with ply - 1', () => {
    renderCard(makeItem({ game_id: 100, ply: 20 }));
    expect(screen.getByTestId('btn-train-puzzle-analyze').getAttribute('href')).toBe(
      '/analysis?game_id=100&ply=19',
    );
  });

  it('tracks one analyze action per click', () => {
    renderCard(makeItem());
    fireEvent.click(screen.getByTestId('btn-train-puzzle-analyze'));
    expect(trackFeature).toHaveBeenCalledTimes(1);
    expect(trackFeature).toHaveBeenCalledWith('action', { target: 'analyze' });
  });
});

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

describe('TrainPuzzleCard game details', () => {
  it('shows the black player as opponent for a white user, with rating', () => {
    renderCard(makeItem({ user_color: 'white' }));
    expect(text('train-puzzle-opponent')).toBe('bob (1620)');
  });

  it('shows the white player as opponent for a black user, with rating', () => {
    renderCard(makeItem({ user_color: 'black' }));
    expect(text('train-puzzle-opponent')).toBe('alice (1500)');
  });

  it('renders ? for a null name and no parentheses for a null rating', () => {
    renderCard(makeItem({ black_username: null, black_rating: null }));
    expect(text('train-puzzle-opponent')).toBe('?');
  });

  it('formats the game date as MMM d, yyyy and omits it when null', () => {
    renderCard(makeItem({ played_at: '2026-10-03T12:00:00Z' }));
    expect(text('train-puzzle-date')).toBe('Oct 3, 2026');
    cleanup();
    renderCard(makeItem({ played_at: null }));
    expect(screen.queryByTestId('train-puzzle-date')).toBeNull();
  });

  it('formats the time control from bucket and string and omits it for a null bucket', () => {
    renderCard(makeItem({ time_control_bucket: 'blitz', time_control_str: '600' }));
    expect(text('train-puzzle-time-control')).toBe('Blitz 10');
    cleanup();
    renderCard(makeItem({ time_control_bucket: null, time_control_str: null }));
    expect(screen.queryByTestId('train-puzzle-time-control')).toBeNull();
  });
});

describe('TrainPuzzleCard status line', () => {
  const SOLVED_AT = '2026-10-03T12:00:00Z';

  it('shows Mastered with the date and never a miss count', () => {
    renderCard(makeItem({ last_solved_at: SOLVED_AT, fail_count: 4 }), 'mastered');
    expect(text('train-puzzle-status')).toBe('Mastered Oct 3, 2026');
  });

  it('shows Parked with the date and a plural miss count', () => {
    renderCard(makeItem({ last_solved_at: SOLVED_AT, fail_count: 4 }), 'parked');
    expect(text('train-puzzle-status')).toBe('Parked Oct 3, 2026 · 4 misses');
  });

  it('uses 1 miss in the singular', () => {
    renderCard(makeItem({ last_solved_at: SOLVED_AT, fail_count: 1 }), 'parked');
    expect(text('train-puzzle-status')).toBe('Parked Oct 3, 2026 · 1 miss');
  });

  it('drops the date when last_solved_at is null', () => {
    renderCard(makeItem({ last_solved_at: null, fail_count: 4 }), 'mastered');
    expect(text('train-puzzle-status')).toBe('Mastered');
    cleanup();
    renderCard(makeItem({ last_solved_at: null, fail_count: 4 }), 'parked');
    expect(text('train-puzzle-status')).toBe('Parked · 4 misses');
  });
});

describe('TrainPuzzleCard spoiler-free contract (D-08)', () => {
  it('holds no SAN move, motif or severity text', () => {
    renderCard(makeItem(), 'parked');
    const content = screen.getByTestId('train-puzzle-card-100-20').textContent ?? '';
    // SAN token: a piece move (Nf3, Qxd5), castling, or a pawn move (e4, exd5).
    const SAN_TOKEN = /\b([KQRBN][a-h]?[1-8]?x?[a-h][1-8]|O-O(-O)?|[a-h]x?[a-h]?[1-8])\b/;
    expect(content).not.toMatch(SAN_TOKEN);
    expect(content).not.toMatch(/blunder|mistake|inaccuracy|fork|pin|skewer|retry/i);
    expect(screen.queryByTestId('train-puzzle-retry')).toBeNull();
  });
});

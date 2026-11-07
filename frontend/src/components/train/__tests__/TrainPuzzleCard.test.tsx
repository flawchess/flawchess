// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type { TrainArchiveItem } from '@/types/train';

// Expose the props the card hands to the board, so the contract (pre-mistake FEN,
// the played move as the only arrow) is asserted on the real call, not on pixels.
const boardProps = vi.fn();
vi.mock('@/components/board/LazyMiniBoard', () => ({
  LazyMiniBoard: (props: Record<string, unknown>) => {
    boardProps(props);
    return <div data-testid="mock-mini-board" />;
  },
}));

// The Library's severity filter, narrowed by one test to prove the card ignores it.
const flawFilter = vi.hoisted(() => ({ severity: [] as ('blunder' | 'mistake')[] }));
vi.mock('@/hooks/useFlawFilterStore', () => ({
  useFlawFilterStore: () => [flawFilter],
}));

const trackFeature = vi.fn();
vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return {
    ...actual,
    trackFeature: (...args: unknown[]) => trackFeature(...args),
  };
});

import { FLAW_FIXED_BRONZE, SEV_BLUNDER, SEV_MISTAKE } from '@/lib/theme';
import { TrainPuzzleCard } from '../TrainPuzzleCard';

const FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2';

function makeItem(overrides: Partial<TrainArchiveItem> = {}): TrainArchiveItem {
  return {
    game_id: 100,
    ply: 20,
    fen: FEN,
    last_move_uci: 'g1f3',
    played_move_uci: 'b8c6',
    played_move_san: 'Nc6',
    severity: 'blunder',
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

  describe('board size', () => {
    const originalInnerWidth = window.innerWidth;
    afterEach(() => {
      window.innerWidth = originalInnerWidth;
    });

    // 639 is the regression: an uncapped 50vw gave 320px just below the sm breakpoint.
    it.each([
      [320, 160],
      [400, 200],
      [639, 200],
      [640, 200],
    ])('at a %ipx viewport the board is %ipx', (viewport, expected) => {
      window.innerWidth = viewport;
      renderCard(makeItem());
      const props = boardProps.mock.calls[0]![0] as Record<string, unknown>;
      expect(props.size).toBe(expected);
    });
  });

  it.each(['mastered', 'parked'] as const)(
    'gives the board the pre-mistake FEN, the arriving move and only the played move on the %s list',
    (list) => {
      renderCard(makeItem(), list);
      expect(boardProps).toHaveBeenCalled();
      const props = boardProps.mock.calls[0]![0] as Record<string, unknown>;
      expect(props.fen).toBe(FEN);
      expect(props.lastMove).toEqual({ from: 'g1', to: 'f3' });
      expect(props.flipped).toBe(false);
      // Exactly one arrow: a second one would be the best move, which stays hidden.
      expect(props.arrows).toEqual([{ from: 'b8', to: 'c6', color: SEV_BLUNDER }]);
    },
  );

  it('colors the played-move arrow by severity', () => {
    renderCard(makeItem({ severity: 'mistake' }));
    const props = boardProps.mock.calls[0]![0] as Record<string, unknown>;
    expect(props.arrows).toEqual([{ from: 'b8', to: 'c6', color: SEV_MISTAKE }]);
  });

  it('draws no arrow for an evicted puzzle with no severity', () => {
    renderCard(makeItem({ severity: null }));
    const props = boardProps.mock.calls[0]![0] as Record<string, unknown>;
    expect(props.arrows).toBeUndefined();
  });

  it('flips the board for a black user', () => {
    renderCard(makeItem({ user_color: 'black' }));
    const props = boardProps.mock.calls[0]![0] as Record<string, unknown>;
    expect(props.flipped).toBe(true);
  });

  it('renders the empty board slot for an unreplayable PGN and keeps Analyze working', () => {
    renderCard(
      makeItem({ fen: null, last_move_uci: null, played_move_uci: null, played_move_san: null }),
    );
    expect(screen.getByTestId('train-puzzle-board-unavailable')).toBeTruthy();
    expect(screen.queryByTestId('mock-mini-board')).toBeNull();
    expect(screen.getByTestId('btn-train-puzzle-analyze').getAttribute('href')).toBe(
      '/analysis?game_id=100&ply=19',
    );
  });
});

describe('TrainPuzzleCard played move', () => {
  it.each([
    [20, 'Nc6', '11. Nc6'],
    [21, 'Nc6', '11... Nc6'],
  ])('at ply %i shows %s as %s', (ply, san, expected) => {
    renderCard(makeItem({ ply, played_move_san: san }));
    expect(screen.getByTestId('train-puzzle-played-move').textContent).toBe(expected);
  });

  it.each(['mistake', 'blunder'] as const)('shows the %s badge on a parked card', (severity) => {
    renderCard(makeItem({ severity }), 'parked');
    expect(screen.getByTestId(`severity-${severity}-100`)).toBeTruthy();
    expect(screen.queryByTestId('train-puzzle-severity-icon')).toBeNull();
  });

  it.each([
    ['mistake', 'Mistake'],
    ['blunder', 'Blunder'],
  ] as const)('shows the %s quality icon instead of the tag on a mastered card', (severity, label) => {
    renderCard(makeItem({ severity }), 'mastered');
    const icon = screen.getByTestId('train-puzzle-severity-icon');
    expect(icon.getAttribute('aria-label')).toBe(label);
    expect(icon.querySelector('svg')).toBeTruthy();
    expect(screen.queryByTestId(`severity-${severity}-100`)).toBeNull();
  });

  it('puts the move first in the details beside the board on a mastered card', () => {
    renderCard(makeItem(), 'mastered');
    const move = screen.getByTestId('train-puzzle-played-move');
    const opponent = screen.getByTestId('train-puzzle-opponent');
    expect(move.compareDocumentPosition(opponent) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const board = screen.getByTestId('mock-mini-board');
    expect(board.compareDocumentPosition(move) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const heading = screen.getByTestId('train-puzzle-flaw-fixed');
    expect(heading.compareDocumentPosition(board) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows neither move nor badge for an evicted puzzle with no severity', () => {
    renderCard(makeItem({ severity: null }));
    expect(screen.queryByTestId('train-puzzle-played-move')).toBeNull();
    expect(screen.queryByTestId('severity-blunder-100')).toBeNull();
    expect(screen.queryByTestId('severity-mistake-100')).toBeNull();
  });

  it('omits the move and the badge when the PGN cannot be replayed', () => {
    renderCard(makeItem({ fen: null, played_move_uci: null, played_move_san: null }));
    expect(screen.queryByTestId('train-puzzle-played-move')).toBeNull();
    expect(screen.queryByTestId('severity-blunder-100')).toBeNull();
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

  it('shows the mastered date alone under the Flaw fixed heading, with no miss count', () => {
    renderCard(makeItem({ last_solved_at: SOLVED_AT, fail_count: 4 }), 'mastered');
    expect(text('train-puzzle-status')).toBe('Oct 3, 2026');
  });

  it('shows Parked with the date and no miss count', () => {
    renderCard(makeItem({ last_solved_at: SOLVED_AT, fail_count: 4 }), 'parked');
    expect(text('train-puzzle-status')).toBe('Parked Oct 3, 2026');
  });

  it('drops the date when last_solved_at is null', () => {
    renderCard(makeItem({ last_solved_at: null, fail_count: 4 }), 'mastered');
    expect(text('train-puzzle-flaw-fixed')).toBe('Flaw fixed');
    expect(screen.queryByTestId('train-puzzle-status')).toBeNull();
    cleanup();
    renderCard(makeItem({ last_solved_at: null, fail_count: 4 }), 'parked');
    expect(text('train-puzzle-status')).toBe('Parked');
  });
});

describe('TrainPuzzleCard mastered look', () => {
  const card = (): HTMLElement => screen.getByTestId('train-puzzle-card-100-20');

  it('gives a mastered card the Flaw fixed heading, bronze spine and glow', () => {
    renderCard(makeItem(), 'mastered');
    expect(text('train-puzzle-flaw-fixed')).toBe('Flaw fixed');
    expect(card().className).toContain('shadow-');
    expect(card().style.borderLeftColor).toBe(FLAW_FIXED_BRONZE);
  });

  it('keeps the bronze look on an evicted mastered puzzle with no severity', () => {
    renderCard(makeItem({ severity: null }), 'mastered');
    expect(text('train-puzzle-flaw-fixed')).toBe('Flaw fixed');
    expect(card().style.borderLeftColor).toBe(FLAW_FIXED_BRONZE);
  });

  it('keeps the played mistake and its severity color on a mastered card', () => {
    renderCard(makeItem(), 'mastered');
    expect(text('train-puzzle-played-move')).toBe('11. Nc6');
    expect(screen.getByTestId('train-puzzle-severity-icon')).toBeTruthy();
    const props = boardProps.mock.lastCall![0] as Record<string, unknown>;
    expect(props.arrows).toEqual([{ from: 'b8', to: 'c6', color: SEV_BLUNDER }]);
  });

  it('leaves a parked card without the heading, bronze spine or glow', () => {
    renderCard(makeItem(), 'parked');
    expect(screen.queryByTestId('train-puzzle-flaw-fixed')).toBeNull();
    expect(card().className).not.toContain('shadow-');
    expect(card().style.borderLeftColor).not.toBe(FLAW_FIXED_BRONZE);
  });
});

describe('TrainPuzzleCard keeps the answer hidden', () => {
  it('names only the played move, with no motif', () => {
    renderCard(makeItem(), 'parked');
    const content = screen.getByTestId('train-puzzle-card-100-20').textContent ?? '';
    // SAN token: a piece move (Nf3, Qxd5), castling, or a pawn move (e4, exd5).
    const SAN_TOKEN = /\b([KQRBN][a-h]?[1-8]?x?[a-h][1-8]|O-O(-O)?|[a-h]x?[a-h]?[1-8])\b/;
    const playedMove = text('train-puzzle-played-move');
    expect(playedMove).toBe('11. Nc6');
    expect(content.replace(playedMove, '')).not.toMatch(SAN_TOKEN);
    expect(content).not.toMatch(/fork|pin|skewer|retry/i);
    expect(screen.queryByTestId('train-puzzle-retry')).toBeNull();
  });

  it('ignores the Library severity filter, so the badge never rings', () => {
    flawFilter.severity = ['blunder'];
    renderCard(makeItem({ severity: 'blunder' }), 'parked');
    expect(screen.getByTestId('severity-blunder-100').className).not.toContain('ring');
    flawFilter.severity = [];
  });
});

// @vitest-environment jsdom
/**
 * TrainScoreRankLines.test.tsx — Phase 230 score-screen rank lines (D-11, D-12).
 *
 * Spies on the real axios instance (`apiClient.get`) so client.ts, the hook and
 * the component are exercised together; wire fixtures mirror app/schemas/train.py.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { TrainScoreRankLines } from '@/components/train/TrainScoreRankLines';
import type {
  LeaderboardBoard,
  LeaderboardViewer,
  TrainLeaderboardResponse,
} from '@/types/train';

const EMPTY_BOARD: LeaderboardBoard = { rows: [], viewer: null, pass_target: null };

function makeViewer(overrides: Partial<LeaderboardViewer> = {}): LeaderboardViewer {
  return {
    rank: 4,
    rank_without_session: null,
    tentative: false,
    puzzles_to_qualify: 0,
    visibility: 'public',
    ...overrides,
  };
}

function makeResponse(
  points: Partial<LeaderboardBoard> = {},
  accuracy: Partial<LeaderboardBoard> = {},
): TrainLeaderboardResponse {
  return {
    week_start: '2032-01-05',
    week_end: '2032-01-12',
    seconds_remaining: 388800,
    points: { ...EMPTY_BOARD, ...points },
    accuracy: { ...EMPTY_BOARD, ...accuracy },
  };
}

let getSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  getSpy = vi.spyOn(apiClient, 'get');
});

afterEach(() => {
  cleanup();
  getSpy.mockRestore();
});

function renderLines(sessionId: number | null): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  render(<TrainScoreRankLines sessionId={sessionId} />, { wrapper: Wrapper });
}

function respondWith(data: TrainLeaderboardResponse): void {
  getSpy.mockResolvedValue({ data });
}

describe('TrainScoreRankLines (public viewer)', () => {
  it('asks the server for this session and renders "#N (up M)"', async () => {
    respondWith(makeResponse({ viewer: makeViewer({ rank: 4, rank_without_session: 7 }) }));
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-points').textContent).toBe('Points board: #4 (up 3)');
    });
    expect(getSpy).toHaveBeenCalledWith('/train/leaderboard', { params: { session_id: 42 } });
    expect(getSpy).toHaveBeenCalledTimes(1);
  });

  it('first session of the week reads "#N this week"', async () => {
    respondWith(makeResponse({ viewer: makeViewer({ rank: 4, rank_without_session: null }) }));
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-points').textContent).toBe('Points board: #4 this week');
    });
  });

  it('an unchanged rank shows the plain rank', async () => {
    respondWith(makeResponse({ viewer: makeViewer({ rank: 4, rank_without_session: 4 }) }));
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-points').textContent).toBe('Points board: #4');
    });
  });

  it('a null session id renders nothing and sends no request', () => {
    renderLines(null);
    expect(screen.queryByTestId('train-score-rank-lines')).toBeNull();
    expect(getSpy).not.toHaveBeenCalled();
  });
});

describe('TrainScoreRankLines variants (D-17, D-18, D-19)', () => {
  it('a guest reads "You\'d be #N" and the lines hold no button (D-17)', async () => {
    respondWith(
      makeResponse({ viewer: makeViewer({ rank: 7, rank_without_session: 9, visibility: 'guest' }) }),
    );
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-points').textContent).toBe("Points board: You'd be #7");
    });
    expect(screen.getByTestId('train-score-rank-lines').querySelector('button')).toBeNull();
  });

  it('a tentative Accuracy viewer reads "(tentative)"', async () => {
    respondWith(
      makeResponse(
        { viewer: makeViewer({ rank: 2, rank_without_session: 2 }) },
        { viewer: makeViewer({ rank: 4, rank_without_session: 4, tentative: true, puzzles_to_qualify: 8 }) },
      ),
    );
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-accuracy').textContent).toBe('Accuracy: #4 (tentative)');
    });
  });

  it('a worse Accuracy rank shows the plain rank, never a down delta (D-18)', async () => {
    respondWith(
      makeResponse(
        { viewer: makeViewer({ rank: 2, rank_without_session: 3 }) },
        { viewer: makeViewer({ rank: 5, rank_without_session: 3 }) },
      ),
    );
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-accuracy').textContent).toBe('Accuracy: #5');
    });
    expect(screen.getByTestId('train-score-rank-lines').textContent?.toLowerCase()).not.toContain('down');
  });

  it('a viewer with Points but no Accuracy entry gets the not-entered line (D-19)', async () => {
    respondWith(makeResponse({ viewer: makeViewer({ rank: 2, rank_without_session: 3 }) }));
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-accuracy').textContent).toBe(
        "Accuracy: not on this board yet (tactics puzzles don't count)",
      );
    });
  });

  it('a hidden viewer gets the "Hidden from others" line', async () => {
    respondWith(makeResponse({ viewer: makeViewer({ rank: 2, rank_without_session: 3, visibility: 'hidden' }) }));
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-hidden').textContent).toBe('Hidden from others');
    });
  });

  it('a failed request shows the exact LoadError sentence', async () => {
    getSpy.mockRejectedValue(new Error('boom'));
    renderLines(42);
    await waitFor(() => {
      expect(screen.getByTestId('train-score-rank-error')).not.toBeNull();
    });
    expect(
      screen.getByText('Failed to load your leaderboard rank. Something went wrong. Please try again in a moment.'),
    ).not.toBeNull();
  });
});

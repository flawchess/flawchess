// @vitest-environment jsdom
/**
 * TrainLeaderboardCard.test.tsx — Phase 230 weekly leaderboard card.
 *
 * Spies on the real axios instance (`apiClient.get`) so client.ts, the hook
 * and the card are all exercised together; the wire fixtures mirror
 * app/schemas/train.py.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';

const mockLogoutForPromotion = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ logoutForPromotion: mockLogoutForPromotion }),
}));

const trackFeature = vi.fn();
vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return { ...actual, trackFeature: (...args: unknown[]) => trackFeature(...args) };
});

import { apiClient } from '@/api/client';
import { TrainLeaderboardCard } from '@/components/train/TrainLeaderboardCard';
import { ROLLOVER_MAX_RETRIES, ROLLOVER_RETRY_MS } from '@/lib/trainLeaderboard';
import type {
  LeaderboardBoard,
  LeaderboardRow,
  TrainLeaderboardResponse,
} from '@/types/train';

const EMPTY_BOARD: LeaderboardBoard = { rows: [], viewer: null, pass_target: null };

function makeRow(overrides: Partial<LeaderboardRow> = {}): LeaderboardRow {
  return {
    rank: 1,
    name: 'magnus',
    value: 12,
    puzzles: 4,
    tentative: false,
    is_viewer: false,
    visibility: 'public',
    gap_before: false,
    ...overrides,
  };
}

function makeResponse(overrides: Partial<TrainLeaderboardResponse> = {}): TrainLeaderboardResponse {
  return {
    week_start: '2032-01-05',
    week_end: '2032-01-12',
    seconds_remaining: 388800,
    points: EMPTY_BOARD,
    accuracy: EMPTY_BOARD,
    ...overrides,
  };
}

let getSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  getSpy = vi.spyOn(apiClient, 'get');
});

afterEach(() => {
  cleanup();
  getSpy.mockRestore();
  mockLogoutForPromotion.mockReset();
  trackFeature.mockReset();
  localStorage.clear();
});

function renderCard(isGuest = false): QueryClient {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }
  render(<TrainLeaderboardCard isGuest={isGuest} />, { wrapper: Wrapper });
  return client;
}

function respondWith(data: TrainLeaderboardResponse): void {
  getSpy.mockResolvedValue({ data });
}

describe('TrainLeaderboardCard (Points board)', () => {
  it('loading: renders the card shell and a loading block', () => {
    getSpy.mockReturnValue(new Promise(() => undefined));
    renderCard();
    expect(screen.getByTestId('train-leaderboard-card')).not.toBeNull();
    expect(screen.getByTestId('train-leaderboard-loading')).not.toBeNull();
    expect(screen.queryByTestId('train-leaderboard-rows')).toBeNull();
  });

  it('error: renders the exact LoadError sentence and no rows', async () => {
    getSpy.mockRejectedValue(new Error('boom'));
    renderCard();
    await waitFor(() => {
      expect(screen.getByTestId('train-leaderboard-error')).not.toBeNull();
    });
    expect(
      screen.getByText('Failed to load the leaderboard. Something went wrong. Please try again in a moment.'),
    ).not.toBeNull();
    expect(screen.queryByTestId('train-leaderboard-rows')).toBeNull();
  });

  it('requests GET /train/leaderboard with no session_id param', async () => {
    respondWith(makeResponse());
    renderCard();
    await waitFor(() => {
      expect(getSpy).toHaveBeenCalled();
    });
    expect(getSpy).toHaveBeenCalledTimes(1);
    const [path, config] = getSpy.mock.calls[0] as [string, { params?: unknown } | undefined];
    expect(path).toBe('/train/leaderboard');
    expect(config?.params).toBeUndefined();
  });

  it('renders rows in server order with shared ranks, name, value and puzzle count', async () => {
    respondWith(
      makeResponse({
        points: {
          rows: [
            makeRow({ rank: 1, name: 'alice', value: 20, puzzles: 8 }),
            makeRow({ rank: 2, name: 'bob', value: 15, puzzles: 7 }),
            makeRow({ rank: 2, name: 'carol', value: 15, puzzles: 5 }),
            makeRow({ rank: 4, name: 'dave', value: 9, puzzles: 1 }),
          ],
          viewer: null,
          pass_target: null,
        },
      }),
    );
    renderCard();
    const list = await screen.findByTestId('train-leaderboard-rows');
    const rows = within(list).getAllByRole('listitem');
    expect(rows.map((r) => r.textContent)).toEqual([
      '#1alice20 pts8 puzzles',
      '#2bob15 pts7 puzzles',
      '#2carol15 pts5 puzzles',
      '#4dave9 pts1 puzzle',
    ]);
  });

  it('marks only the viewer row with data-viewer and aria-current', async () => {
    respondWith(
      makeResponse({
        points: {
          rows: [makeRow({ rank: 1 }), makeRow({ rank: 2, name: 'me', is_viewer: true })],
          viewer: null,
          pass_target: null,
        },
      }),
    );
    renderCard();
    const viewer = await screen.findByTestId('train-leaderboard-row-1');
    expect(viewer.getAttribute('data-viewer')).toBe('true');
    expect(viewer.getAttribute('aria-current')).toBe('true');
    expect(screen.getByTestId('train-leaderboard-row-0').getAttribute('data-viewer')).toBeNull();
  });

  it('renders a hidden gap marker before a gap_before row', async () => {
    respondWith(
      makeResponse({
        points: {
          rows: [
            makeRow({ rank: 1 }),
            makeRow({ rank: 9, name: 'me', is_viewer: true, gap_before: true }),
          ],
          viewer: null,
          pass_target: null,
        },
      }),
    );
    renderCard();
    const gap = await screen.findByTestId('train-leaderboard-gap');
    expect(gap.getAttribute('aria-hidden')).toBe('true');
    const items = within(screen.getByTestId('train-leaderboard-rows')).getAllByRole('listitem', { hidden: true });
    expect(items.indexOf(gap)).toBe(1);
  });

  it('guest: shows the claim-your-spot nudge with the shared sign-up pair (train-leaderboard source)', async () => {
    respondWith(makeResponse({ points: { rows: [makeRow()], viewer: null, pass_target: null } }));
    renderCard(true);
    const cta = await screen.findByTestId('train-leaderboard-guest-cta');
    expect(cta.textContent).toContain('Sign up to claim your spot');
    expect(screen.getByTestId('btn-signup-why-train-leaderboard')).not.toBeNull();
    const free = screen.getByTestId('btn-signup-free-train-leaderboard');
    expect(free.getAttribute('data-umami-event-source')).toBe('train-leaderboard');
  });

  it('registered user: renders no sign-up element', async () => {
    respondWith(makeResponse({ points: { rows: [makeRow()], viewer: null, pass_target: null } }));
    renderCard(false);
    await screen.findByTestId('train-leaderboard-rows');
    expect(document.querySelectorAll('[data-testid^="btn-signup-"]')).toHaveLength(0);
    expect(screen.queryByTestId('train-leaderboard-guest-cta')).toBeNull();
  });
});

const VIEWER = {
  rank: 3,
  rank_without_session: null,
  tentative: false,
  puzzles_to_qualify: 0,
  visibility: 'public' as const,
};

const TABBED_RESPONSE = makeResponse({
  points: {
    rows: [makeRow({ rank: 1, name: 'alice', value: 20, puzzles: 8 })],
    viewer: VIEWER,
    pass_target: { name: 'alice', points_needed: 4 },
  },
  accuracy: {
    rows: [
      makeRow({ rank: 1, name: 'zed', value: 95, puzzles: 30 }),
      makeRow({ rank: 2, name: 'yan', value: 80, puzzles: 5, tentative: true }),
    ],
    viewer: { ...VIEWER, tentative: true, puzzles_to_qualify: 18 },
    pass_target: null,
  },
});

describe('TrainLeaderboardCard tabs (D-07, D-09, D-10)', () => {
  it('opens on Points on first render, with the Accuracy helper hidden', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.getByTestId('train-leaderboard-tab-points').getAttribute('data-state')).toBe('on');
    expect(screen.getByText('alice')).not.toBeNull();
    expect(screen.queryByTestId('train-leaderboard-accuracy-helper')).toBeNull();
  });

  it('shows ONE card with both tabs', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(document.querySelectorAll('[data-testid="train-leaderboard-card"]')).toHaveLength(1);
    expect(screen.getByTestId('train-leaderboard-tab-accuracy').textContent).toBe('Accuracy');
    expect(screen.getByTestId('train-leaderboard-tab-points').textContent).toBe('Points');
  });

  it('clicking Accuracy shows % rows, the tentative marker and the helper line', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    const rows = screen.getByTestId('train-leaderboard-rows');
    expect(within(rows).getByText('95%')).not.toBeNull();
    expect(within(rows).getByText('(tentative)')).not.toBeNull();
    expect(within(rows).getAllByText('(tentative)')).toHaveLength(1);
    expect(screen.getByTestId('train-leaderboard-accuracy-helper').textContent).toContain('20+ puzzles to qualify');
    expect(screen.getByTestId('train-leaderboard-accuracy-helper').textContent).toContain("Tactics puzzles don't count");
  });

  it('remembers the tab across a remount via localStorage', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    cleanup();

    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.getByTestId('train-leaderboard-tab-accuracy').getAttribute('data-state')).toBe('on');
    expect(screen.getByText('zed')).not.toBeNull();
  });

  it('opens on Accuracy when it is stored and sends no analytics event for the restore', async () => {
    localStorage.setItem('flawchess_train_leaderboard_tab', 'accuracy');
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.getByTestId('train-leaderboard-tab-accuracy').getAttribute('data-state')).toBe('on');
    expect(trackFeature).not.toHaveBeenCalled();
  });

  it('falls back to Points for an unknown stored value', async () => {
    localStorage.setItem('flawchess_train_leaderboard_tab', 'skill');
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.getByTestId('train-leaderboard-tab-points').getAttribute('data-state')).toBe('on');
  });

  it('renders an invitation for an empty Points board and a plain line for an empty Accuracy board', async () => {
    respondWith(makeResponse());
    renderCard();
    expect((await screen.findByTestId('train-leaderboard-empty')).textContent).toBe(
      'No one has trained yet this week. Be the first.',
    );
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(screen.getByTestId('train-leaderboard-empty').textContent).toBe('No accuracy entries yet this week.');
  });

  it('viewer hints: pass target on Points, qualifier count on Accuracy', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.getByTestId('train-leaderboard-pass-target').textContent).toBe('4 points to pass alice');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(screen.getByTestId('train-leaderboard-qualify').textContent).toBe('18 more puzzles to qualify');
    expect(screen.queryByTestId('train-leaderboard-pass-target')).toBeNull();
  });

  it('D-19: a viewer with Points entries but no Accuracy entry gets the not-entered line', async () => {
    respondWith(
      makeResponse({
        points: { rows: [makeRow()], viewer: VIEWER, pass_target: null },
      }),
    );
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(screen.getByTestId('train-leaderboard-accuracy-not-entered').textContent).toContain(
      "tactics puzzles don't count",
    );
    expect(screen.queryByTestId('train-leaderboard-qualify')).toBeNull();
  });

  it('never frames the board as ability: no "skill" anywhere in the rendered card', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(screen.getByTestId('train-leaderboard-card').textContent?.toLowerCase()).not.toContain('skill');
  });
});

describe('TrainLeaderboardCard Umami tab-switch (Phase 229 registry)', () => {
  it('a hand switch sends tab-switch once with the leaderboard target', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(trackFeature).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(trackFeature).toHaveBeenCalledTimes(1);
    expect(trackFeature).toHaveBeenCalledWith('tab-switch', { target: 'leaderboard-accuracy' });
  });

  it('re-tapping the active tab sends nothing', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-points'));
    expect(trackFeature).not.toHaveBeenCalled();
    expect(screen.getByTestId('train-leaderboard-tab-points').getAttribute('data-state')).toBe('on');
  });
});

describe('TrainLeaderboardCard countdown and private rows (D-02, D-13, D-14)', () => {
  it('shows the server remainder in the header right after load', async () => {
    respondWith(makeResponse({ seconds_remaining: 388800 }));
    renderCard();
    const countdown = await screen.findByTestId('train-leaderboard-countdown');
    expect(countdown.textContent).toBe('ends in 4d 12h');
  });

  it('invalidates the leaderboard query exactly once at the deadline, without looping', async () => {
    respondWith(makeResponse({ seconds_remaining: 0 }));
    const client = renderCard();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    await waitFor(() => {
      expect(invalidate).toHaveBeenCalledTimes(1);
    });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['train', 'leaderboard'] });
    expect((await screen.findByTestId('train-leaderboard-countdown')).textContent).toBe('ending now');
    // The refetch comes back with the same week_end: no second invalidation.
    await waitFor(() => {
      expect(getSpy).toHaveBeenCalledTimes(2);
    });
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(invalidate).toHaveBeenCalledTimes(1);
  });

  it('retries the rollover while the refetch still carries the old week, then stops on the new week (WR-03)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const stuck = makeResponse({ seconds_remaining: 0 });
      const nextWeek = makeResponse({
        week_start: '2032-01-12',
        week_end: '2032-01-19',
        seconds_remaining: 604800,
      });
      // Initial load + first rollover refetch both land before the server's reset.
      getSpy.mockResolvedValueOnce({ data: stuck }).mockResolvedValueOnce({ data: stuck });
      getSpy.mockResolvedValue({ data: nextWeek });
      const client = renderCard();
      const invalidate = vi.spyOn(client, 'invalidateQueries');
      await waitFor(() => {
        expect(getSpy).toHaveBeenCalledTimes(2);
      });
      expect(invalidate).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(ROLLOVER_RETRY_MS);
      await waitFor(() => {
        expect(screen.getByTestId('train-leaderboard-countdown').textContent).toBe('ends in 7d 0h');
      });
      expect(invalidate).toHaveBeenCalledTimes(2);
      // The new week is current: no further invalidation.
      await vi.advanceTimersByTimeAsync(ROLLOVER_RETRY_MS * 2);
      expect(invalidate).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it('caps the rollover retries when the server keeps returning the old week (WR-03)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      respondWith(makeResponse({ seconds_remaining: 0 }));
      const client = renderCard();
      const invalidate = vi.spyOn(client, 'invalidateQueries');
      await waitFor(() => {
        expect(getSpy).toHaveBeenCalledTimes(2);
      });
      for (let i = 0; i < ROLLOVER_MAX_RETRIES + 2; i++) {
        await vi.advanceTimersByTimeAsync(ROLLOVER_RETRY_MS);
      }
      expect(invalidate).toHaveBeenCalledTimes(1 + ROLLOVER_MAX_RETRIES);
    } finally {
      vi.useRealTimers();
    }
  });

  it('a hidden viewer row shows the name plus "Hidden from others"', async () => {
    respondWith(
      makeResponse({
        points: {
          rows: [makeRow({ rank: 5, name: 'me', is_viewer: true, visibility: 'hidden' })],
          viewer: { ...VIEWER, visibility: 'hidden' },
          pass_target: null,
        },
      }),
    );
    renderCard();
    const row = await screen.findByTestId('train-leaderboard-row-0');
    expect(row.textContent).toContain('me');
    expect(row.textContent).toContain('Hidden from others');
  });

  it('a guest viewer row reads "You (guest)" instead of the server name', async () => {
    respondWith(
      makeResponse({
        points: {
          rows: [makeRow({ rank: 5, name: 'Anonymous', is_viewer: true, visibility: 'guest' })],
          viewer: { ...VIEWER, visibility: 'guest' },
          pass_target: null,
        },
      }),
    );
    renderCard(true);
    const row = await screen.findByTestId('train-leaderboard-row-0');
    expect(row.textContent).toContain('You (guest)');
    expect(row.textContent).not.toContain('Anonymous');
  });

  it('renders users without a username as the server-sent "Anonymous"', async () => {
    respondWith(makeResponse({ points: { rows: [makeRow({ name: 'Anonymous' })], viewer: null, pass_target: null } }));
    renderCard();
    expect((await screen.findByTestId('train-leaderboard-row-0')).textContent).toContain('Anonymous');
  });
});

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
import { TrainLeaderboardCard, TrainLeaderboardCardView } from '@/components/train/TrainLeaderboardCard';
import { ROLLOVER_MAX_RETRIES, ROLLOVER_RETRY_MS } from '@/lib/trainLeaderboard';
import type {
  LeaderboardBoard,
  LeaderboardLastWeek,
  LeaderboardRow,
  TrainLeaderboardResponse,
} from '@/types/train';

const EMPTY_BOARD: LeaderboardBoard = { rows: [], viewer: null, pass_target: null, last_week: null };

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
    medals: { gold: 0, silver: 0, bronze: 0 },
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
    expect(screen.queryByTestId('train-leaderboard-rows')).toBeNull();    expect(screen.getByTestId('train-leaderboard-info')).not.toBeNull();
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
          last_week: null,
        },
      }),
    );
    renderCard();
    const list = await screen.findByTestId('train-leaderboard-rows');
    const rows = within(list).getAllByRole('listitem');
    expect(rows.map((r) => r.textContent)).toEqual([
      '#1alice20 pts8',
      '#2bob15 pts7',
      '#2carol15 pts5',
      '#4dave9 pts1',
    ]);
    // The puzzle count is an icon plus the number; the accessible name keeps the word.
    expect(screen.getByTestId('train-leaderboard-row-0-puzzles').getAttribute('aria-label')).toBe('8 puzzles');
    expect(screen.getByTestId('train-leaderboard-row-3-puzzles').getAttribute('aria-label')).toBe('1 puzzle');
    expect(screen.getByTestId('train-leaderboard-row-0-puzzles').getAttribute('role')).toBe('img');
    expect(screen.getByTestId('train-leaderboard-row-0-puzzles').querySelector('svg')).not.toBeNull();
  });

  it('marks only the viewer row with data-viewer and aria-current', async () => {
    respondWith(
      makeResponse({
        points: {
          rows: [makeRow({ rank: 1 }), makeRow({ rank: 2, name: 'me', is_viewer: true })],
          viewer: null,
          pass_target: null,
          last_week: null,
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
          last_week: null,
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
    respondWith(makeResponse({ points: { rows: [makeRow()], viewer: null, pass_target: null, last_week: null } }));
    renderCard(true);
    const cta = await screen.findByTestId('train-leaderboard-guest-cta');
    expect(cta.textContent).toContain('Sign up to claim your spot');
    expect(screen.getByTestId('btn-signup-why-train-leaderboard')).not.toBeNull();
    const free = screen.getByTestId('btn-signup-free-train-leaderboard');
    expect(free.getAttribute('data-umami-event-source')).toBe('train-leaderboard');
  });

  it('registered user: renders no sign-up element', async () => {
    respondWith(makeResponse({ points: { rows: [makeRow()], viewer: null, pass_target: null, last_week: null } }));
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
    last_week: null,
  },
  accuracy: {
    rows: [
      makeRow({ rank: 1, name: 'zed', value: 95, puzzles: 30 }),
      makeRow({ rank: null, name: 'yan', value: 80, puzzles: 5, tentative: true }),
      makeRow({ rank: null, name: 'xia', value: 100, puzzles: 2, tentative: true }),
    ],
    viewer: { ...VIEWER, rank: null, tentative: true, puzzles_to_qualify: 18 },
    pass_target: null,
    last_week: null,
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

  it('clicking Accuracy shows % rows, one qualify divider with the threshold and rank-less tentative rows', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    const rows = screen.getByTestId('train-leaderboard-rows');
    expect(within(rows).getByText('95%')).not.toBeNull();
    const dividers = screen.getAllByTestId('train-leaderboard-qualify-divider');
    expect(dividers).toHaveLength(1);
    const divider = dividers[0];
    expect(divider?.textContent).toBe('Not yet qualified (20+ puzzles)');
    expect(divider?.nextElementSibling).toBe(screen.getByTestId('train-leaderboard-row-1'));
    expect(screen.getByTestId('train-leaderboard-row-0').textContent).toContain('#1');
    expect(screen.getByTestId('train-leaderboard-row-1').textContent).not.toContain('#');
    expect(screen.getByTestId('train-leaderboard-row-2').textContent).not.toContain('#');
    expect(within(rows).queryByText('(tentative)')).toBeNull();
    expect(screen.getByTestId('train-leaderboard-row-1-puzzles').getAttribute('aria-label')).toBe('5 puzzles');
    expect(screen.queryByTestId('train-leaderboard-accuracy-helper')).toBeNull();
  });

  it('the Points tab renders no qualify divider', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.queryByTestId('train-leaderboard-qualify-divider')).toBeNull();
  });

  it('renders the gap marker, then the divider, then the row when one row is both', async () => {
    respondWith(
      makeResponse({
        points: { rows: [makeRow()], viewer: null, pass_target: null, last_week: null },
        accuracy: {
          rows: [
            makeRow({ rank: 1, name: 'zed', value: 95, puzzles: 30 }),
            makeRow({ rank: null, name: 'yan', value: 80, puzzles: 5, tentative: true, gap_before: true }),
          ],
          viewer: null,
          pass_target: null,
          last_week: null,
        },
      }),
    );
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    const gap = screen.getByTestId('train-leaderboard-gap');
    const divider = screen.getByTestId('train-leaderboard-qualify-divider');
    const row = screen.getByTestId('train-leaderboard-row-1');
    expect(gap.nextElementSibling).toBe(divider);
    expect(divider.nextElementSibling).toBe(row);
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

  it('viewer hints: pass target on Points, none for a tentative viewer on Accuracy', async () => {
    respondWith(TABBED_RESPONSE);
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.getByTestId('train-leaderboard-pass-target').textContent).toBe('4 points to pass alice');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(screen.queryByTestId('train-leaderboard-qualify')).toBeNull();
    expect(screen.queryByTestId('train-leaderboard-pass-target')).toBeNull();
  });

  it('D-19: a viewer with Points entries but no Accuracy entry gets the not-entered line', async () => {
    respondWith(
      makeResponse({
        points: { rows: [makeRow()], viewer: VIEWER, pass_target: null, last_week: null },
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

  it('puts the info popover next to the title, before the countdown, and explains both boards', async () => {
    respondWith(makeResponse({ seconds_remaining: 388800 }));
    renderCard();
    const countdown = await screen.findByTestId('train-leaderboard-countdown');
    const info = screen.getByTestId('train-leaderboard-info');
    expect(info.getAttribute('aria-label')).toBe('About the weekly leaderboards');
    expect(info.compareDocumentPosition(countdown) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(info.parentElement?.querySelector('h2')?.textContent).toBe('This week');
    fireEvent.click(info);
    expect(await screen.findByText('Points mainly rewards how many puzzles you solve.')).not.toBeNull();
    expect(
      screen.getByText('Accuracy is your average session score: it rewards how carefully you solve, not how many.'),
    ).not.toBeNull();
    expect(trackFeature).toHaveBeenCalledWith('popover-open', { target: 'train-leaderboard-info' });
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
          last_week: null,
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
          last_week: null,
        },
      }),
    );
    renderCard(true);
    const row = await screen.findByTestId('train-leaderboard-row-0');
    expect(row.textContent).toContain('You (guest)');
    expect(row.textContent).not.toContain('Anonymous');
  });

  it('renders users without a username as the server-sent "Anonymous"', async () => {
    respondWith(makeResponse({ points: { rows: [makeRow({ name: 'Anonymous' })], viewer: null, pass_target: null, last_week: null } }));
    renderCard();
    expect((await screen.findByTestId('train-leaderboard-row-0')).textContent).toContain('Anonymous');
  });
});

const LAST_WEEK_START = '2032-01-05';

function lastWeekOf(
  podium: LeaderboardLastWeek['podium'],
  viewerFinalRank: number | null = null,
): LeaderboardLastWeek {
  return { week_start: LAST_WEEK_START, podium, viewer_final_rank: viewerFinalRank };
}

describe('TrainLeaderboardCard last-week podium (Phase 231, D-07..D-09)', () => {
  it('lists every podium entry in server order after the "Last week:" label', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow()],
          last_week: lastWeekOf([
            { medal: 'gold', name: 'alice', is_viewer: false },
            { medal: 'silver', name: 'bob', is_viewer: false },
            { medal: 'silver', name: 'dave', is_viewer: false },
          ]),
        },
      }),
    );
    renderCard();
    const podium = await screen.findByTestId('train-leaderboard-podium');
    expect(podium.textContent).toContain('Last week:');
    expect(screen.getByTestId('train-leaderboard-podium-entry-0').textContent).toContain('alice');
    expect(screen.getByTestId('train-leaderboard-podium-entry-1').textContent).toContain('bob');
    expect(screen.getByTestId('train-leaderboard-podium-entry-2').textContent).toContain('dave');
  });

  it('on the Accuracy tab the podium precedes the Accuracy helper', async () => {
    respondWith(
      makeResponse({
        points: { ...EMPTY_BOARD, rows: [makeRow()] },
        accuracy: {
          ...EMPTY_BOARD,
          rows: [makeRow({ value: 90, puzzles: 30 })],
          last_week: lastWeekOf([{ medal: 'gold', name: 'zed', is_viewer: false }]),
        },
      }),
    );
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    const podium = screen.getByTestId('train-leaderboard-podium');
    const rows = screen.getByTestId('train-leaderboard-rows');
    expect(podium.compareDocumentPosition(rows) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows the podium of the active tab only', async () => {
    respondWith(
      makeResponse({
        points: { ...EMPTY_BOARD, rows: [makeRow()], last_week: lastWeekOf([{ medal: 'gold', name: 'pointsy', is_viewer: false }]) },
        accuracy: { ...EMPTY_BOARD, rows: [makeRow()], last_week: lastWeekOf([{ medal: 'gold', name: 'accy', is_viewer: false }]) },
      }),
    );
    renderCard();
    await screen.findByTestId('train-leaderboard-podium');
    expect(screen.getByTestId('train-leaderboard-podium').textContent).toContain('pointsy');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(screen.getByTestId('train-leaderboard-podium').textContent).toContain('accy');
  });

  it('renders no podium when last_week is null (D-08)', async () => {
    respondWith(makeResponse({ points: { ...EMPTY_BOARD, rows: [makeRow()] } }));
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.queryByTestId('train-leaderboard-podium')).toBeNull();
  });

  it('renders no podium when the podium is empty, even with a viewer_final_rank (D-07)', async () => {
    respondWith(
      makeResponse({ points: { ...EMPTY_BOARD, rows: [makeRow()], last_week: lastWeekOf([], 4) } }),
    );
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    expect(screen.queryByTestId('train-leaderboard-podium')).toBeNull();
  });

  it('renders a name containing markup as literal text (T-231-14)', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow()],
          last_week: lastWeekOf([{ medal: 'gold', name: '<b>x</b>', is_viewer: false }]),
        },
      }),
    );
    renderCard();
    const entry = await screen.findByTestId('train-leaderboard-podium-entry-0');
    expect(entry.textContent).toContain('<b>x</b>');
    expect(entry.querySelector('b')).toBeNull();
  });
});

describe('TrainLeaderboardCardView (Phase 231 seam)', () => {
  it('renders the podium and rows from props alone, with no fetching and no query client', () => {
    const data = makeResponse({
      points: {
        ...EMPTY_BOARD,
        rows: [makeRow({ name: 'alice' })],
        last_week: lastWeekOf([{ medal: 'gold', name: 'carol', is_viewer: false }]),
      },
    });
    render(
      <TrainLeaderboardCardView
        data={data}
        isPending={false}
        isError={false}
        remaining={3600}
        tab="points"
        onTabChange={() => undefined}
        isGuest={false}
      />,
    );
    expect(screen.getByTestId('train-leaderboard-podium').textContent).toContain('carol');
    expect(screen.getByTestId('train-leaderboard-row-0').textContent).toContain('alice');
    expect(screen.getByTestId('train-leaderboard-countdown')).not.toBeNull();
    expect(getSpy).not.toHaveBeenCalled();
  });
});

describe('TrainLeaderboardCard lifetime medal tally (Phase 231)', () => {
  it('sits inside the name block after the name and before the hidden cue', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [
            makeRow({
              name: 'me',
              is_viewer: true,
              visibility: 'hidden',
              medals: { gold: 2, silver: 0, bronze: 1 },
            }),
          ],
          viewer: VIEWER,
        },
      }),
    );
    renderCard();
    const tally = await screen.findByTestId('train-leaderboard-row-0-medals');
    const row = screen.getByTestId('train-leaderboard-row-0');
    const nameBlock = tally.parentElement;
    expect(nameBlock).not.toBeNull();
    expect(row.contains(nameBlock)).toBe(true);
    expect(nameBlock?.className).toContain('flex-wrap');
    const cue = within(row).getByText('Hidden from others');
    expect(nameBlock?.contains(cue)).toBe(true);
    expect(tally.compareDocumentPosition(cue) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(nameBlock?.firstElementChild?.textContent).toBe('me');
    expect(tally.getAttribute('aria-label')).toBe('2 gold, 1 bronze Points medals');
  });

  it('renders no tally for a row without medals', async () => {
    respondWith(makeResponse({ points: { ...EMPTY_BOARD, rows: [makeRow()] } }));
    renderCard();
    await screen.findByTestId('train-leaderboard-row-0');
    expect(screen.queryByTestId('train-leaderboard-row-0-medals')).toBeNull();
  });

  it('shows the tally on a tentative Accuracy row and on an Anonymous row', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow({ name: 'Anonymous', medals: { gold: 1, silver: 0, bronze: 0 } })],
        },
        accuracy: {
          ...EMPTY_BOARD,
          rows: [makeRow({ rank: null, tentative: true, value: 80, medals: { gold: 0, silver: 4, bronze: 0 } })],
        },
      }),
    );
    renderCard();
    const anon = await screen.findByTestId('train-leaderboard-row-0-medals');
    expect(anon.getAttribute('aria-label')).toBe('1 gold Points medal');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    const tentative = screen.getByTestId('train-leaderboard-row-0-medals');
    expect(tentative.getAttribute('aria-label')).toBe('4 silver Accuracy medals');
  });

  it('shows no tally on the guest ghost row (zero medals)', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow({ name: 'Anonymous', is_viewer: true, visibility: 'guest' })],
          viewer: { ...VIEWER, visibility: 'guest' },
        },
      }),
    );
    renderCard(true);
    await screen.findByTestId('train-leaderboard-row-0');
    expect(screen.queryByTestId('train-leaderboard-row-0-medals')).toBeNull();
  });

  it('shows each board its own tally', async () => {
    respondWith(
      makeResponse({
        points: { ...EMPTY_BOARD, rows: [makeRow({ medals: { gold: 3, silver: 0, bronze: 0 } })] },
        accuracy: { ...EMPTY_BOARD, rows: [makeRow({ medals: { gold: 0, silver: 0, bronze: 7 } })] },
      }),
    );
    renderCard();
    const points = await screen.findByTestId('train-leaderboard-row-0-medals');
    expect(points.getAttribute('aria-label')).toBe('3 gold Points medals');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    expect(screen.getByTestId('train-leaderboard-row-0-medals').getAttribute('aria-label')).toBe(
      '7 bronze Accuracy medals',
    );
  });
});

describe('TrainLeaderboardCard last-week finish line (Phase 231, D-03)', () => {
  it('sits below this week\'s hint on the Points tab', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow()],
          viewer: VIEWER,
          pass_target: { name: 'alice', points_needed: 4 },
          last_week: lastWeekOf([{ medal: 'gold', name: 'alice', is_viewer: false }], 12),
        },
      }),
    );
    renderCard();
    const finish = await screen.findByTestId('train-leaderboard-last-week-finish');
    const hint = screen.getByTestId('train-leaderboard-pass-target');
    expect(finish.textContent).toBe('You finished #12 last week');
    expect(hint.compareDocumentPosition(finish) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(hint.textContent).toBe('4 points to pass alice');
  });

  it('sits below this week\'s hint on the Accuracy tab, using that board\'s rank', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow()],
          viewer: VIEWER,
          last_week: lastWeekOf([{ medal: 'gold', name: 'alice', is_viewer: false }], 12),
        },
        accuracy: {
          ...EMPTY_BOARD,
          rows: [makeRow({ value: 90, puzzles: 30 })],
          last_week: lastWeekOf([{ medal: 'gold', name: 'zed', is_viewer: false }], 5),
        },
      }),
    );
    renderCard();
    await screen.findByTestId('train-leaderboard-rows');
    fireEvent.click(screen.getByTestId('train-leaderboard-tab-accuracy'));
    const hint = screen.getByTestId('train-leaderboard-accuracy-not-entered');
    const finish = screen.getByTestId('train-leaderboard-last-week-finish');
    expect(finish.textContent).toBe('You finished #5 last week');
    expect(hint.compareDocumentPosition(finish) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('renders alone when there is no current hint', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow()],
          viewer: VIEWER,
          pass_target: null,
          last_week: lastWeekOf([], 9),
        },
      }),
    );
    renderCard();
    const finish = await screen.findByTestId('train-leaderboard-last-week-finish');
    expect(finish.textContent).toBe('You finished #9 last week');
    expect(finish.className).toContain('mt-2');
  });

  it('renders nothing extra when viewer_final_rank is null', async () => {
    respondWith(
      makeResponse({
        points: {
          ...EMPTY_BOARD,
          rows: [makeRow()],
          viewer: VIEWER,
          pass_target: { name: 'alice', points_needed: 4 },
          last_week: lastWeekOf([{ medal: 'gold', name: 'alice', is_viewer: false }], null),
        },
      }),
    );
    renderCard();
    await screen.findByTestId('train-leaderboard-pass-target');
    expect(screen.queryByTestId('train-leaderboard-last-week-finish')).toBeNull();
  });
});

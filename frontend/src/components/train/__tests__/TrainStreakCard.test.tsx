// @vitest-environment jsdom
/**
 * TrainStreakCard.test.tsx — the Train landing's streak hero:
 * the streak inside a 3-layer flame, the 0-7 buffer as snowflake freezes, the
 * weekly tally, the optional Start/Resume slot, and the one-shot arrival
 * animations driven by the per-device last-seen snapshot.
 * Mocks `@/api/client` the way `useReadiness.test.tsx` does, wrapped in a
 * QueryClientProvider with `retry: false`.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useLocation } from 'react-router';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      getProgress: vi.fn(),
      getLeaderboard: vi.fn(),
    },
  };
});

vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return { ...actual, trackFeature: vi.fn() };
});

vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({ data: { email: 'user@example.com' }, isPending: false, isError: false }),
}));

import { trainApi } from '@/api/client';
import { trackFeature } from '@/lib/analytics';
import { TrainStreakCard } from '@/components/train/TrainStreakCard';
import { FREEZE_CAP, readStreakLastSeen, writeStreakLastSeen } from '@/lib/streakArrival';
import type {
  LeaderboardViewer,
  LeaderboardVisibility,
  TrainLeaderboardResponse,
  TrainProgressResponse,
} from '@/types/train';

const OWNER = 'user@example.com';

// Fake-clock time that covers StreakFlame's count-up (450 ms delay + 500 ms
// run) and the earned-freeze pop-in delay, with headroom.
const ARRIVAL_ANIMATIONS_SETTLE_MS = 2000;

beforeEach(() => {
  localStorage.clear();
  // Default: the leaderboard never resolves, so tests that do not care about
  // the rank line see only its reserved (invisible) pending row.
  vi.mocked(trainApi.getLeaderboard).mockReturnValue(new Promise(() => undefined));
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
  vi.mocked(trainApi.getProgress).mockReset();
  vi.mocked(trainApi.getLeaderboard).mockReset();
  vi.mocked(trackFeature).mockReset();
  vi.unstubAllGlobals();
});

function LocationProbe(): ReactNode {
  return <span data-testid="location-probe">{useLocation().pathname}</span>;
}

function renderWithClient(action?: ReactNode, pointsToday?: { total: number; max: number }): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/train']}>
          {children}
          <LocationProbe />
        </MemoryRouter>
      </QueryClientProvider>
    );
  }
  render(<TrainStreakCard action={action} pointsToday={pointsToday} />, { wrapper: Wrapper });
}

const BASE: TrainProgressResponse = {
  session_streak_count: 3,
  shield_level: 5,
  current_week_completed: 1,
  current_week_required: 2,
  streak_reset_notice: false,
  mastered_count: 5,
  parked_count: 2,
  waiting_count: 0,
  pool_state: 'available',
  next_due_date: null,
  badge_visible: false,
};

async function renderPopulated(
  overrides: Partial<TrainProgressResponse> = {},
  action?: ReactNode,
): Promise<void> {
  vi.mocked(trainApi.getProgress).mockResolvedValue({ ...BASE, ...overrides });
  renderWithClient(action);
  await waitFor(() => expect(screen.getByTestId('train-streak-flame')).not.toBeNull());
}

function filledSlots(): HTMLElement[] {
  return screen.getAllByTestId('train-freeze-slot').filter((el) => el.dataset.filled === 'true');
}

function crackingHalves(): number {
  return document.body.querySelectorAll('.train-freeze-half-left').length;
}

describe('TrainStreakCard', () => {
  it('loading: renders the loading slot with no numeric text', () => {
    vi.mocked(trainApi.getProgress).mockReturnValue(new Promise(() => undefined));
    renderWithClient();

    expect(screen.getByTestId('train-progress-loading')).not.toBeNull();
    expect(screen.queryByTestId('train-streak-flame')).toBeNull();
    expect(screen.queryByTestId('train-shield-meter')).toBeNull();
    expect(screen.queryByText(/\d/)).toBeNull();
  });

  it('error: renders the exact CLAUDE.md copy, no flame or meter', async () => {
    vi.mocked(trainApi.getProgress).mockRejectedValue(new Error('boom'));
    renderWithClient();

    await waitFor(() => expect(screen.getByTestId('train-progress-error')).not.toBeNull());
    expect(
      screen.getByText('Failed to load your progress. Something went wrong. Please try again in a moment.'),
    ).not.toBeNull();
    expect(screen.queryByTestId('train-streak-flame')).toBeNull();
    expect(screen.queryByTestId('train-shield-meter')).toBeNull();
  });

  describe('streak flame', () => {
    it.each([1, 42, 365])('shows %i inside a lit flame', async (n) => {
      await renderPopulated({ session_streak_count: n });
      expect(screen.getByTestId('train-streak-count').textContent).toBe(String(n));
      expect(screen.getByTestId('train-streak-flame').dataset.lit).toBe('true');
    });

    it('shows 0 in an unlit flame — never hidden at a broken streak', async () => {
      await renderPopulated({ session_streak_count: 0 });
      expect(screen.getByTestId('train-streak-count').textContent).toBe('0');
      expect(screen.getByTestId('train-streak-flame').dataset.lit).toBe('false');
    });

    it('names the streak for assistive tech', async () => {
      await renderPopulated({ session_streak_count: 7 });
      expect(screen.getByRole('img', { name: 'Session streak: 7' })).not.toBeNull();
    });
  });

  describe('freeze meter', () => {
    it.each([0, 5, 7])('shield_level %i fills exactly that many of the 7 freezes', async (level) => {
      await renderPopulated({ shield_level: level });
      expect(screen.getAllByTestId('train-freeze-slot')).toHaveLength(FREEZE_CAP);
      expect(filledSlots()).toHaveLength(level);
      expect(screen.getByTestId('train-shield-meter').dataset.filledCount).toBe(String(level));
    });

    it('sits in its own "Freezes" row with a "Freezes: N of 7" label', async () => {
      await renderPopulated({ shield_level: 4 });
      expect(screen.getByTestId('train-shield-row').textContent).toContain('Freezes');
      expect(screen.getByRole('img', { name: 'Freezes: 4 of 7' })).not.toBeNull();
    });
  });

  describe('this-week caption', () => {
    it('shows "N of M this week" when days are scheduled', async () => {
      await renderPopulated({ current_week_completed: 3, current_week_required: 7 });
      expect(screen.getByTestId('train-this-week').textContent).toBe('3 of 7 this week');
    });

    it('drops the denominator in "train anytime" mode', async () => {
      await renderPopulated({ current_week_completed: 1, current_week_required: null });
      expect(screen.getByTestId('train-this-week').textContent).toBe('1 this week');
    });
  });

  describe('rank line', () => {
    function leaderboard(viewer: Partial<LeaderboardViewer> | null): TrainLeaderboardResponse {
      const full: LeaderboardViewer | null =
        viewer === null
          ? null
          : {
              rank: 4,
              rank_without_session: null,
              tentative: false,
              puzzles_to_qualify: 0,
              visibility: 'public',
              ...viewer,
            };
      return {
        points: { rows: [], viewer: full, last_week: null },
        accuracy: { rows: [], viewer: null, last_week: null },
      } as unknown as TrainLeaderboardResponse;
    }

    it('shows the Points rank as a link to the leaderboard tab', async () => {
      vi.mocked(trainApi.getLeaderboard).mockResolvedValue(leaderboard({ rank: 4 }));
      await renderPopulated();
      const link = await screen.findByTestId('train-rank-line');
      expect(link.textContent).toBe('#4 this week');
      expect(link.getAttribute('href')).toBe('/train/leaderboard');
    });

    it('renders no line when the viewer has no Points rank', async () => {
      vi.mocked(trainApi.getLeaderboard).mockResolvedValue(leaderboard(null));
      await renderPopulated();
      await waitFor(() => expect(screen.queryByTestId('train-rank-line-pending')).toBeNull());
      expect(screen.queryByTestId('train-rank-line')).toBeNull();
    });

    it('reserves the row and shows no link while the leaderboard is pending', async () => {
      // getLeaderboard never resolves (default mock).
      await renderPopulated();
      expect(screen.getByTestId('train-rank-line-pending')).not.toBeNull();
      expect(screen.queryByTestId('train-rank-line')).toBeNull();
    });

    it('renders no line when the leaderboard query fails', async () => {
      vi.mocked(trainApi.getLeaderboard).mockRejectedValue(new Error('boom'));
      await renderPopulated();
      await waitFor(() => expect(screen.queryByTestId('train-rank-line-pending')).toBeNull());
      expect(screen.queryByTestId('train-rank-line')).toBeNull();
    });

    it.each<LeaderboardVisibility>(['hidden', 'guest'])('a %s viewer reads like any other', async (visibility) => {
      vi.mocked(trainApi.getLeaderboard).mockResolvedValue(leaderboard({ rank: 2, visibility }));
      await renderPopulated();
      const link = await screen.findByTestId('train-rank-line');
      expect(link.textContent).toBe('#2 this week');
    });

    it('a tap navigates client-side to the leaderboard and tracks one nav-click', async () => {
      vi.mocked(trainApi.getLeaderboard).mockResolvedValue(leaderboard({ rank: 4 }));
      await renderPopulated();
      fireEvent.click(await screen.findByTestId('train-rank-line'));

      expect(screen.getByTestId('location-probe').textContent).toBe('/train/leaderboard');
      expect(trackFeature).toHaveBeenCalledTimes(1);
      expect(trackFeature).toHaveBeenCalledWith('nav-click', { target: 'train', value: 'train-rank-line' });
    });

    it('sits after the week caption and before the freeze row', async () => {
      vi.mocked(trainApi.getLeaderboard).mockResolvedValue(leaderboard({ rank: 4 }));
      await renderPopulated();
      const week = screen.getByTestId('train-this-week');
      const rank = await screen.findByTestId('train-rank-line');
      const shield = screen.getByTestId('train-shield-row');
      expect(week.compareDocumentPosition(rank) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(rank.compareDocumentPosition(shield) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
  });

  describe('points today', () => {
    it('absent unless the pointsToday prop is passed', async () => {
      await renderPopulated();
      expect(screen.queryByTestId('train-points-today')).toBeNull();
    });

    it('renders "Points today: 5/9" after the rank line and before the freeze row', async () => {
      vi.mocked(trainApi.getProgress).mockResolvedValue(BASE);
      vi.mocked(trainApi.getLeaderboard).mockResolvedValue({
        points: { rows: [], viewer: { rank: 4 }, last_week: null },
      } as unknown as TrainLeaderboardResponse);
      renderWithClient(undefined, { total: 5, max: 9 });
      const rank = await screen.findByTestId('train-rank-line');
      const points = await screen.findByTestId('train-points-today');
      const shield = await screen.findByTestId('train-shield-row');
      expect(points.textContent).toBe('Points today: 5/9');
      expect(rank.compareDocumentPosition(points) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(points.compareDocumentPosition(shield) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
  });

  describe('streak reset notice', () => {
    it('absent when streak_reset_notice is false, even with no freezes', async () => {
      await renderPopulated({ shield_level: 0, streak_reset_notice: false });
      expect(screen.queryByTestId('train-streak-reset-notice')).toBeNull();
    });

    it('present when streak_reset_notice is true', async () => {
      await renderPopulated({ session_streak_count: 0, shield_level: 0, streak_reset_notice: true });
      expect(screen.getByTestId('train-streak-reset-notice').textContent).toBe(
        'Streak reset. Complete a session to start a new one.',
      );
    });
  });

  it('renders the action slot (the Start/Resume button) inside the hero', async () => {
    await renderPopulated({}, <button data-testid="btn-train-start">Start</button>);
    const card = screen.getByTestId('train-streak-card');
    expect(card.contains(screen.getByTestId('btn-train-start'))).toBe(true);
  });

  describe('explainer popover', () => {
    it('stays out of the card body until the trigger is opened, then states the freeze rules', async () => {
      await renderPopulated();
      expect(screen.queryByText(/earns a freeze/)).toBeNull();

      fireEvent.click(screen.getByTestId('train-shield-explainer'));
      await waitFor(() => expect(screen.getByText(/earns a freeze/)).not.toBeNull());
      const body = screen.getByText(/earns a freeze/).textContent ?? '';
      expect(body).toContain('streak goes up by 1');
      expect(body).toContain(`(${FREEZE_CAP} max)`);
      expect(body).toContain('missed scheduled day uses one');
      expect(body).toContain('resets to 0');
    });

    it('the trigger is present even while progress is loading', () => {
      vi.mocked(trainApi.getProgress).mockReturnValue(new Promise(() => undefined));
      renderWithClient();
      expect(screen.getByTestId('train-shield-explainer')).not.toBeNull();
    });
  });

  describe('arrival animations (last-seen diff)', () => {
    it('first visit: no animation, and the snapshot is stored', async () => {
      await renderPopulated({ session_streak_count: 52, shield_level: 5 });
      expect(screen.getByTestId('train-streak-flame').classList.contains('train-flame-ignite')).toBe(false);
      expect(readStreakLastSeen(OWNER)).toEqual({ streak: 52, freezes: 5 });
    });

    it('streak up: the flame ignites and counts up from the last-seen value; the earned freeze pops in', async () => {
      // Fake clock: on real timers the count-up raced the test under CPU load
      // (it read 50/51 after a 3 s waitFor). Only timers and frames are faked,
      // so the mocked query still resolves through microtasks.
      vi.useFakeTimers({
        toFake: ['setTimeout', 'clearTimeout', 'requestAnimationFrame', 'cancelAnimationFrame', 'performance'],
      });
      writeStreakLastSeen(OWNER, { streak: 51, freezes: 4 });
      vi.mocked(trainApi.getProgress).mockResolvedValue({ ...BASE, session_streak_count: 52, shield_level: 5 });
      renderWithClient();
      // Fire only the timers due now (the query's notify batch), not the count-up.
      await act(() => vi.advanceTimersByTimeAsync(0));

      expect(screen.getByTestId('train-streak-flame').classList.contains('train-flame-ignite')).toBe(true);
      expect(screen.getByTestId('train-streak-count').textContent).toBe('51');
      await act(() => vi.advanceTimersByTimeAsync(ARRIVAL_ANIMATIONS_SETTLE_MS));
      expect(screen.getByTestId('train-streak-count').textContent).toBe('52');
      const popped = screen
        .getAllByTestId('train-freeze-slot')
        .filter((el) => el.classList.contains('train-freeze-popin'));
      expect(popped).toHaveLength(1);
      expect(readStreakLastSeen(OWNER)).toEqual({ streak: 52, freezes: 5 });
    });

    it('freezes used: each spent freeze cracks and the flame frosts but stays lit', async () => {
      writeStreakLastSeen(OWNER, { streak: 52, freezes: 5 });
      await renderPopulated({ session_streak_count: 52, shield_level: 3 });

      const flame = screen.getByTestId('train-streak-flame');
      expect(flame.classList.contains('train-flame-ignite')).toBe(false);
      expect(flame.classList.contains('train-flame-frosted')).toBe(true);
      expect(flame.dataset.lit).toBe('true');
      expect(crackingHalves()).toBe(2);
    });

    it('streak reset: the old lit flame goes out, leaving the unlit 0; the last freeze cracks first', async () => {
      writeStreakLastSeen(OWNER, { streak: 52, freezes: 1 });
      await renderPopulated({ session_streak_count: 0, shield_level: 0, streak_reset_notice: true });

      const flame = screen.getByTestId('train-streak-flame');
      expect(flame.dataset.lit).toBe('false');
      expect(flame.classList.contains('train-flame-extinguished')).toBe(true);
      expect(flame.classList.contains('train-flame-ignite')).toBe(false);
      expect(flame.classList.contains('train-flame-frosted')).toBe(false);
      expect(screen.getByTestId('train-streak-extinguish').textContent).toBe('52');
      expect(screen.getByTestId('train-streak-count').textContent).toBe('0');
      expect(crackingHalves()).toBe(1);
    });

    it('prefers-reduced-motion: final state only, no animation classes', async () => {
      vi.stubGlobal('matchMedia', (query: string) => ({
        matches: query.includes('reduce'),
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }));
      writeStreakLastSeen(OWNER, { streak: 51, freezes: 6 });
      await renderPopulated({ session_streak_count: 52, shield_level: 5 });

      expect(screen.getByTestId('train-streak-flame').classList.contains('train-flame-ignite')).toBe(false);
      expect(screen.getByTestId('train-streak-count').textContent).toBe('52');
      expect(crackingHalves()).toBe(0);
    });

    it('prefers-reduced-motion: a reset shows the unlit 0 with no extinguish overlay', async () => {
      vi.stubGlobal('matchMedia', (query: string) => ({
        matches: query.includes('reduce'),
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }));
      writeStreakLastSeen(OWNER, { streak: 52, freezes: 1 });
      await renderPopulated({ session_streak_count: 0, shield_level: 0 });

      expect(screen.queryByTestId('train-streak-extinguish')).toBeNull();
      expect(screen.getByTestId('train-streak-count').textContent).toBe('0');
    });
  });
});

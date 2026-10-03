// @vitest-environment jsdom
/**
 * TrainStreakCard.test.tsx — the Train landing's streak hero (SEED-181):
 * the streak inside a 3-layer flame, the 0-7 buffer as snowflake freezes, the
 * weekly tally, the optional Start/Resume slot, and the one-shot arrival
 * animations driven by the per-device last-seen snapshot.
 * Mocks `@/api/client` the way `useReadiness.test.tsx` does, wrapped in a
 * QueryClientProvider with `retry: false`.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      getProgress: vi.fn(),
    },
  };
});

vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({ data: { email: 'user@example.com' }, isPending: false, isError: false }),
}));

import { trainApi } from '@/api/client';
import { TrainStreakCard } from '@/components/train/TrainStreakCard';
import { FREEZE_CAP, readStreakLastSeen, writeStreakLastSeen } from '@/lib/streakArrival';
import type { TrainProgressResponse } from '@/types/train';

const OWNER = 'user@example.com';

beforeEach(() => localStorage.clear());

afterEach(() => {
  cleanup();
  vi.mocked(trainApi.getProgress).mockReset();
  vi.unstubAllGlobals();
});

function renderWithClient(action?: ReactNode): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  render(<TrainStreakCard action={action} />, { wrapper: Wrapper });
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
      writeStreakLastSeen(OWNER, { streak: 51, freezes: 4 });
      await renderPopulated({ session_streak_count: 52, shield_level: 5 });

      expect(screen.getByTestId('train-streak-flame').classList.contains('train-flame-ignite')).toBe(true);
      expect(screen.getByTestId('train-streak-count').textContent).toBe('51');
      await waitFor(() => expect(screen.getByTestId('train-streak-count').textContent).toBe('52'), {
        timeout: 3000,
      });
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

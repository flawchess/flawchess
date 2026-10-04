// @vitest-environment jsdom
/**
 * TrainMedalDialogHost.test.tsx — Phase 231 landing host (D-10, D-13,
 * RESEARCH Pitfall 6). Spies on the real axios instance (apiClient.get /
 * apiClient.post) so client.ts, the hooks and the host are exercised together.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// The host reads `impersonation` from the cached profile; a mutable module
// object lets each test pick the profile (undefined = still loading).
let profileMock: { data: { impersonation: unknown } | undefined } = { data: { impersonation: null } };
vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => profileMock,
}));

const unlockAudio = vi.fn();
const playSound = vi.fn();
vi.mock('@/lib/sounds', () => ({
  unlockAudio: (...args: unknown[]) => unlockAudio(...args),
  playSound: (...args: unknown[]) => playSound(...args),
  useMuted: () => false,
}));

const fireWinConfetti = vi.fn();
vi.mock('@/lib/confetti', () => ({
  fireWinConfetti: (...args: unknown[]) => fireWinConfetti(...args),
  prefersReducedMotion: () => false,
}));

// No Umami event for Claim or dismiss (locked): the registry must stay untouched.
const trackFeature = vi.fn();
const trackEvent = vi.fn();
vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return {
    ...actual,
    trackFeature: (...args: unknown[]) => trackFeature(...args),
    trackEvent: (...args: unknown[]) => trackEvent(...args),
  };
});

import { apiClient } from '@/api/client';
import { TrainMedalDialogHost } from '@/components/train/medals/TrainMedalDialogHost';
import { TRAIN_UNCLAIMED_MEDALS_QUERY_KEY } from '@/hooks/useTrainMedals';
import type { UnclaimedMedal, UnclaimedMedalsResponse } from '@/types/train';

const TWO_MEDALS: UnclaimedMedal[] = [
  { week_start: '2032-01-05', board: 'points', medal: 'gold', value: 412, shared: false },
  { week_start: '2032-01-05', board: 'accuracy', medal: 'bronze', value: 87, shared: true },
];
const TWO_KEYS = [
  { week_start: '2032-01-05', board: 'points' },
  { week_start: '2032-01-05', board: 'accuracy' },
];

let getSpy: ReturnType<typeof vi.spyOn>;
let postSpy: ReturnType<typeof vi.spyOn>;
let serverMedals: UnclaimedMedal[];

beforeEach(() => {
  profileMock = { data: { impersonation: null } };
  serverMedals = TWO_MEDALS;
  getSpy = vi
    .spyOn(apiClient, 'get')
    .mockImplementation(async () => ({ data: { medals: serverMedals } satisfies UnclaimedMedalsResponse }));
  postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: undefined });
});

afterEach(() => {
  cleanup();
  getSpy.mockRestore();
  postSpy.mockRestore();
  unlockAudio.mockReset();
  playSound.mockReset();
  fireWinConfetti.mockReset();
  trackFeature.mockReset();
  trackEvent.mockReset();
});

function renderHost(isGuest = false, client?: QueryClient): QueryClient {
  const queryClient = client ?? new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  render(<TrainMedalDialogHost isGuest={isGuest} />, { wrapper: Wrapper });
  return queryClient;
}

describe('TrainMedalDialogHost', () => {
  it('shows the dialog for a registered user with unclaimed medals', async () => {
    renderHost();
    await waitFor(() => expect(screen.getByTestId('train-medal-dialog')).not.toBeNull());
    expect(screen.getByText('You won 2 medals!')).not.toBeNull();
    expect(getSpy).toHaveBeenCalledWith('/train/medals/unclaimed');
  });

  it('Claim posts the shown keys once, closes, and does not reopen after an invalidation', async () => {
    const client = renderHost();
    await waitFor(() => expect(screen.getByTestId('btn-train-medal-claim')).not.toBeNull());

    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));

    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));
    expect(postSpy).toHaveBeenCalledWith('/train/medals/claim', { medals: TWO_KEYS });
    await waitFor(() => expect(screen.queryByTestId('train-medal-dialog')).toBeNull());

    // The server still reports both medals (e.g. a late refetch): the per-mount
    // closed state keeps the dialog shut for this visit.
    const getCallsBefore = getSpy.mock.calls.length;
    await act(async () => {
      await client.invalidateQueries({ queryKey: TRAIN_UNCLAIMED_MEDALS_QUERY_KEY });
    });
    expect(getSpy.mock.calls.length).toBeGreaterThan(getCallsBefore);
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
    expect(postSpy).toHaveBeenCalledTimes(1);
  });

  it('keeps showing the original medals while the dialog fades out after the claim prunes the cache', async () => {
    // jsdom has no CSS animations, so Radix Presence unmounts at once. Fake an
    // exit animation on closed content so the dialog stays mounted, as it does
    // for the real 100 ms fade-out.
    const realGetComputedStyle = window.getComputedStyle.bind(window);
    const styleSpy = vi.spyOn(window, 'getComputedStyle').mockImplementation((element, pseudo) => {
      const style = realGetComputedStyle(element, pseudo);
      // Radix keeps this live style object, so data-state is read lazily per access.
      return new Proxy(style, {
        get: (target, prop) => {
          if (prop === 'animationName') {
            return element.getAttribute('data-state') === 'closed' ? 'fake-exit' : 'none';
          }
          const value = Reflect.get(target, prop, target);
          return typeof value === 'function' ? value.bind(target) : value;
        },
      });
    });
    try {
      const client = renderHost();
      await waitFor(() => expect(screen.getByTestId('btn-train-medal-claim')).not.toBeNull());

      fireEvent.click(screen.getByTestId('btn-train-medal-claim'));

      // The POST resolves and onSuccess prunes both claimed keys from the cache.
      await waitFor(() => expect(client.getQueryData<UnclaimedMedalsResponse>(TRAIN_UNCLAIMED_MEDALS_QUERY_KEY)?.medals).toEqual([]));
      await act(async () => {});

      // Still mid-exit: the content is mounted and must not have gone empty.
      expect(screen.getByTestId('train-medal-dialog').getAttribute('data-state')).toBe('closed');
      expect(screen.getByText('You won 2 medals!')).not.toBeNull();
      expect(screen.queryByText('You won 0 medals!')).toBeNull();
      expect(screen.getByTestId('train-medal-dialog-entry-1')).not.toBeNull();
    } finally {
      styleSpy.mockRestore();
    }
  });

  it('dismiss posts the shown keys once with no sound and no confetti', async () => {
    renderHost();
    await waitFor(() => expect(screen.getByTestId('btn-train-medal-dialog-close')).not.toBeNull());

    fireEvent.click(screen.getByTestId('btn-train-medal-dialog-close'));

    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));
    expect(postSpy).toHaveBeenCalledWith('/train/medals/claim', { medals: TWO_KEYS });
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
    expect(unlockAudio).not.toHaveBeenCalled();
    expect(playSound).not.toHaveBeenCalled();
    expect(fireWinConfetti).not.toHaveBeenCalled();
  });

  it('fires no analytics event for Claim or dismiss', async () => {
    renderHost();
    await waitFor(() => expect(screen.getByTestId('btn-train-medal-claim')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-medal-claim'));
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));
    expect(trackFeature).not.toHaveBeenCalled();
    expect(trackEvent).not.toHaveBeenCalled();
  });

  it('a guest triggers no GET and shows nothing', async () => {
    renderHost(true);
    await act(async () => {});
    expect(getSpy).not.toHaveBeenCalled();
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
  });

  it('an impersonating admin triggers no GET and shows nothing (T-231-16)', async () => {
    profileMock = { data: { impersonation: { admin_email: 'admin@example.com' } } };
    renderHost();
    await act(async () => {});
    expect(getSpy).not.toHaveBeenCalled();
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
  });

  it('waits for the profile before fetching', async () => {
    profileMock = { data: undefined };
    renderHost();
    await act(async () => {});
    expect(getSpy).not.toHaveBeenCalled();
  });

  it('an empty list opens nothing', async () => {
    serverMedals = [];
    renderHost();
    await waitFor(() => expect(getSpy).toHaveBeenCalled());
    await act(async () => {});
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
    expect(postSpy).not.toHaveBeenCalled();
  });

  it('a pre-seeded cache with medals plus a GET returning [] never opens the dialog', async () => {
    serverMedals = [];
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData<UnclaimedMedalsResponse>(TRAIN_UNCLAIMED_MEDALS_QUERY_KEY, { medals: TWO_MEDALS });
    renderHost(false, client);
    // Stale cache entry present from the first render: not shown (not fetched after mount).
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
    await waitFor(() => expect(getSpy).toHaveBeenCalled());
    await act(async () => {});
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
  });
});

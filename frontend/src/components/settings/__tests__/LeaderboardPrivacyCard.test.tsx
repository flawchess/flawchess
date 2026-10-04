// @vitest-environment jsdom
/**
 * LeaderboardPrivacyCard.test.tsx: Phase 230 D-16. The card reads the profile
 * from the server, writes the flag through PUT /users/me/profile and refreshes
 * the profile cache and the weekly boards from the response. Spies on the real
 * axios instance so card, hook and cache are covered together.
 */
import type { ReactNode } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { LeaderboardPrivacyCard } from '@/components/settings/LeaderboardPrivacyCard';
import { resetAllSettings } from '@/lib/engineSettings';
import type { UserProfile } from '@/types/users';

const PROFILE: UserProfile = {
  email: 'player@example.com',
  is_superuser: false,
  is_guest: false,
  chess_com_username: null,
  lichess_username: 'player',
  created_at: '2026-01-01T00:00:00Z',
  last_login: null,
  chess_com_game_count: 0,
  lichess_game_count: 10,
  chess_com_last_sync_at: null,
  lichess_last_sync_at: null,
  impersonation: null,
  beta_enabled: false,
  leaderboard_hidden: false,
  current_strength: null,
};

const SWITCH_ID = 'settings-leaderboard-hidden-switch';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderCard(client: QueryClient = makeClient()): QueryClient {
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  render(<LeaderboardPrivacyCard />, { wrapper: Wrapper });
  return client;
}

/** A promise the test settles by hand, to hold the PUT in flight. */
function deferred<T>(): { promise: Promise<T>; resolve: (v: T) => void; reject: (e: Error) => void } {
  let resolve!: (v: T) => void;
  let reject!: (e: Error) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}


describe('LeaderboardPrivacyCard', () => {
  it('saves the flag through the profile PUT, adopts the response and refreshes the boards', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: PROFILE });
    const put = vi
      .spyOn(apiClient, 'put')
      .mockResolvedValue({ data: { ...PROFILE, leaderboard_hidden: true } });

    const client = makeClient();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    renderCard(client);

    const toggle = await screen.findByTestId('settings-leaderboard-hidden-switch');
    expect(toggle.getAttribute('aria-checked')).toBe('false');

    fireEvent.click(toggle);

    await waitFor(() =>
      expect(
        screen.getByTestId('settings-leaderboard-hidden-switch').getAttribute('aria-checked'),
      ).toBe('true'),
    );
    expect(put).toHaveBeenCalledTimes(1);
    expect(put).toHaveBeenCalledWith('/users/me/profile', { leaderboard_hidden: true });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['train', 'leaderboard'] });
  });

  it('renders nothing for a guest profile', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: { ...PROFILE, is_guest: true } });
    renderCard();
    await waitFor(() => expect(get).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByTestId('settings-section-privacy')).toBeNull());
    expect(screen.queryByTestId(SWITCH_ID)).toBeNull();
  });

  it('shows the load-error copy when the profile request fails', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('boom'));
    renderCard();
    const error = await screen.findByTestId('settings-section-privacy-error');
    expect(error.textContent).toBe(
      'Failed to load your privacy setting. Something went wrong. Please try again in a moment.',
    );
  });

  it('disables the switch and shows the requested state while the PUT is pending', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: PROFILE });
    const pending = deferred<{ data: UserProfile }>();
    vi.spyOn(apiClient, 'put').mockReturnValue(pending.promise);
    renderCard();

    fireEvent.click(await screen.findByTestId(SWITCH_ID));

    await waitFor(() => expect(screen.getByTestId(SWITCH_ID).hasAttribute('disabled')).toBe(true));
    expect(screen.getByTestId(SWITCH_ID).getAttribute('aria-checked')).toBe('true');

    pending.resolve({ data: { ...PROFILE, leaderboard_hidden: true } });
    await waitFor(() => expect(screen.getByTestId(SWITCH_ID).hasAttribute('disabled')).toBe(false));
  });

  it('shows the save error and falls back to the stored value when the PUT is rejected', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: PROFILE });
    vi.spyOn(apiClient, 'put').mockRejectedValue(new Error('nope'));
    renderCard();

    fireEvent.click(await screen.findByTestId(SWITCH_ID));

    const error = await screen.findByTestId('settings-leaderboard-hidden-error');
    expect(error.textContent).toBe("Couldn't save this setting. Please try again.");
    expect(screen.getByTestId(SWITCH_ID).getAttribute('aria-checked')).toBe('false');
  });

  it('keeps the hidden choice when Reset to defaults runs and sends no PUT', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: { ...PROFILE, leaderboard_hidden: true },
    });
    const put = vi.spyOn(apiClient, 'put');
    renderCard();
    const toggle = await screen.findByTestId(SWITCH_ID);
    expect(toggle.getAttribute('aria-checked')).toBe('true');

    resetAllSettings();

    expect(screen.getByTestId(SWITCH_ID).getAttribute('aria-checked')).toBe('true');
    expect(put).not.toHaveBeenCalled();
  });

  it('sends no analytics event when the switch is flipped (database-landing write)', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: PROFILE });
    vi.spyOn(apiClient, 'put').mockResolvedValue({ data: { ...PROFILE, leaderboard_hidden: true } });
    const track = vi.fn();
    window.umami = { track, identify: vi.fn() };
    renderCard();

    fireEvent.click(await screen.findByTestId(SWITCH_ID));
    await waitFor(() => expect(screen.getByTestId(SWITCH_ID).getAttribute('aria-checked')).toBe('true'));

    expect(track).not.toHaveBeenCalled();
    window.umami = undefined;
  });
});

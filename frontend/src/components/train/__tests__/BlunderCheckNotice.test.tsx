// @vitest-environment jsdom
/**
 * BlunderCheckNotice.test.tsx — the Blunder Check launch notice (Phase 251 D-21) above the mode
 * cards: shown while the server flag is set, dismissed optimistically, then re-read from the server.
 */
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      getProgress: vi.fn(),
      dismissBlunderCheckNotice: vi.fn(),
    },
  };
});

vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return { ...actual, trackFeature: vi.fn() };
});

import { trainApi } from '@/api/client';
import { trackFeature } from '@/lib/analytics';
import { BlunderCheckNotice } from '@/components/train/BlunderCheckNotice';
import type { TrainProgressResponse } from '@/types/train';
import { PHASE_251_PROGRESS_FIELDS } from '@/components/train/__tests__/trainProgressFixtures';

const NOTICE_COPY =
  'New: Blunder Check. Call each move of a real game before it is played: good or blunder? It now counts toward your streak, and you can set the amount or turn it off in the Blunder Check settings.';

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
  ...PHASE_251_PROGRESS_FIELDS,
};

afterEach(() => {
  cleanup();
  vi.mocked(trainApi.getProgress).mockReset();
  vi.mocked(trainApi.dismissBlunderCheckNotice).mockReset();
  vi.mocked(trackFeature).mockReset();
});

async function renderNotice(flag: boolean): Promise<void> {
  vi.mocked(trainApi.getProgress).mockResolvedValue({ ...BASE, blunder_check_notice: flag });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  render(<BlunderCheckNotice />, { wrapper: Wrapper });
  await waitFor(() => expect(trainApi.getProgress).toHaveBeenCalled());
}

describe('BlunderCheckNotice (Phase 251 D-21)', () => {
  it('shows the D-21 sentence while the server reports the notice', async () => {
    await renderNotice(true);

    const notice = await screen.findByTestId('train-blunder-check-notice');
    expect(notice.textContent).toContain(NOTICE_COPY);
    expect(
      screen.getByTestId('btn-train-blunder-check-notice-dismiss').getAttribute('aria-label'),
    ).toBe('Dismiss');
  });

  it('shows no notice when the server flag is false (new user, guest, expired, dismissed)', async () => {
    await renderNotice(false);

    expect(screen.queryByTestId('train-blunder-check-notice')).toBeNull();
  });

  it('dismiss hides the notice at once, tells the server and tracks it', async () => {
    // The server call never settles: the notice must go away optimistically.
    vi.mocked(trainApi.dismissBlunderCheckNotice).mockReturnValue(new Promise(() => undefined));
    await renderNotice(true);

    fireEvent.click(await screen.findByTestId('btn-train-blunder-check-notice-dismiss'));

    await waitFor(() => expect(screen.queryByTestId('train-blunder-check-notice')).toBeNull());
    expect(trainApi.dismissBlunderCheckNotice).toHaveBeenCalledTimes(1);
    expect(trackFeature).toHaveBeenCalledWith('action', {
      target: 'train-blunder-check-notice-dismiss',
    });
  });

  it('invalidates the progress query once the dismissal settles', async () => {
    vi.mocked(trainApi.dismissBlunderCheckNotice).mockResolvedValue(undefined);
    await renderNotice(true);
    await screen.findByTestId('train-blunder-check-notice');
    expect(trainApi.getProgress).toHaveBeenCalledTimes(1);
    vi.mocked(trainApi.getProgress).mockResolvedValue({ ...BASE, blunder_check_notice: false });

    fireEvent.click(screen.getByTestId('btn-train-blunder-check-notice-dismiss'));

    await waitFor(() => expect(trainApi.getProgress).toHaveBeenCalledTimes(2));
    expect(screen.queryByTestId('train-blunder-check-notice')).toBeNull();
  });
});

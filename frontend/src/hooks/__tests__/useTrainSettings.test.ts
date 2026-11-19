// @vitest-environment jsdom
/**
 * useTrainSettings.test.ts — regression coverage for the guest 403.
 *
 * `useReminderResurface` mounts this hook app-wide via `ProtectedLayout`
 * (App.tsx) with no gate, so a guest account got a guaranteed 403 from
 * `_reject_guest` on `GET /train/settings` on every protected page view and
 * window refocus, each captured by the global `QueryCache.onError` Sentry
 * reporter. Covers the fix: `options.enabled` gates the query off entirely,
 * mirroring `useTrainProgress`'s existing pattern.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactNode } from 'react';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      getSettings: vi.fn(),
      updateSettings: vi.fn(),
    },
  };
});

import { trainApi } from '@/api/client';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import type { TrainSettingsDraft } from '@/hooks/useTrainSettings';
import type { TrainSettingsResponse } from '@/types/train';

const SETTINGS: TrainSettingsResponse = {
  timezone: 'UTC',
  weekday_mask: 5,
  puzzles_per_session: 12,
  reminder_enabled: false,
  reminder_hour: 18,
  reminder_intent_at: null,
};

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return createElement(QueryClientProvider, { client }, children);
  };
}

describe('useTrainSettings — enabled gate (regression)', () => {
  afterEach(() => {
    vi.mocked(trainApi.getSettings).mockReset();
  });

  it('does NOT fire GET /train/settings when enabled: false (the guest case)', async () => {
    vi.mocked(trainApi.getSettings).mockResolvedValue(SETTINGS);

    renderHook(() => useTrainSettings({ enabled: false }), { wrapper: makeWrapper() });

    // Give any accidental fetch a couple of ticks to have started.
    await Promise.resolve();
    await Promise.resolve();
    expect(trainApi.getSettings).not.toHaveBeenCalled();
  });

  it('fires GET /train/settings when enabled: true', async () => {
    vi.mocked(trainApi.getSettings).mockResolvedValue(SETTINGS);

    const { result } = renderHook(() => useTrainSettings({ enabled: true }), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual(SETTINGS);
    });
    expect(trainApi.getSettings).toHaveBeenCalledTimes(1);
  });

  it('fires GET /train/settings when no options are passed at all (the two pre-existing call sites)', async () => {
    vi.mocked(trainApi.getSettings).mockResolvedValue(SETTINGS);

    const { result } = renderHook(() => useTrainSettings(), { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(result.current.data).toEqual(SETTINGS);
    });
    expect(trainApi.getSettings).toHaveBeenCalledTimes(1);
  });
});

describe('useTrainSettings — optional blunder-check fields (plan 04 PUT contract)', () => {
  const DRAFT: TrainSettingsDraft = {
    weekdayMask: 5,
    puzzlesPerSession: 12,
    reminderEnabled: false,
    reminderHour: 18,
    reminderIntentAt: null,
  };

  afterEach(() => {
    vi.mocked(trainApi.getSettings).mockReset();
    vi.mocked(trainApi.updateSettings).mockReset();
  });

  async function saveDraft(draft: TrainSettingsDraft): Promise<Record<string, unknown>> {
    vi.mocked(trainApi.getSettings).mockResolvedValue(SETTINGS);
    vi.mocked(trainApi.updateSettings).mockResolvedValue(SETTINGS);
    const { result } = renderHook(() => useTrainSettings(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.data).toEqual(SETTINGS));

    act(() => {
      result.current.save(draft);
    });

    await waitFor(() => expect(trainApi.updateSettings).toHaveBeenCalledTimes(1));
    return vi.mocked(trainApi.updateSettings).mock.calls[0]![0] as unknown as Record<string, unknown>;
  }

  it('sends blunder_check_per_session and blunder_check_level when the draft sets them', async () => {
    const body = await saveDraft({ ...DRAFT, blunderCheckPerSession: 9, blunderCheckLevel: 'advanced' });

    expect(body.blunder_check_per_session).toBe(9);
    expect(body.blunder_check_level).toBe('advanced');
  });

  it('sends a zero blunderCheckPerSession (the mode off), not omits it', async () => {
    const body = await saveDraft({ ...DRAFT, blunderCheckPerSession: 0 });

    expect(body.blunder_check_per_session).toBe(0);
    expect('blunder_check_level' in body).toBe(false);
  });

  it('sends neither key when the draft omits them (absent keeps the stored value)', async () => {
    const body = await saveDraft(DRAFT);

    expect('blunder_check_per_session' in body).toBe(false);
    expect('blunder_check_level' in body).toBe(false);
    expect(body.puzzles_per_session).toBe(12);
  });
});

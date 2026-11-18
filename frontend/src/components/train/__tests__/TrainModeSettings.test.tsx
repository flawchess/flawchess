// @vitest-environment jsdom
/**
 * TrainModeSettings.test.tsx — the per-mode settings rows under the Today card (sketch 014
 * variant B, D-08). Rendered through a harness that owns the one shared settings draft the
 * way `TrainStartScreen` does, next to the schedule card, so "one draft, one PUT" is tested
 * across the two components. Real timers (see TrainScheduleSettings.test.tsx for why).
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      getSettings: vi.fn(),
      updateSettings: vi.fn(),
    },
    pushApi: {
      ...actual.pushApi,
      getVapidPublicKey: vi.fn(),
      subscribe: vi.fn(),
    },
  };
});

vi.mock('@/hooks/useInstallPrompt', () => ({
  useInstallPrompt: vi.fn(),
}));

import { trainApi } from '@/api/client';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';
import { TrainModeSettings } from '@/components/train/TrainModeSettings';
import { TrainScheduleSettings } from '@/components/train/TrainScheduleSettings';
import { TRAIN_SETTINGS_SAVE_DEBOUNCE_MS, useTrainSettingsDraft } from '@/hooks/useTrainSettingsDraft';
import type { TrainSettingsResponse, TrainSettingsUpdate } from '@/types/train';

const BASE_SETTINGS: TrainSettingsResponse = {
  timezone: 'UTC',
  weekday_mask: 5,
  puzzles_per_session: 12,
  reminder_enabled: false,
  reminder_hour: 18,
  reminder_intent_at: '2026-08-02T12:00:00Z',
  blunder_check_per_session: 6,
  blunder_check_level: null,
};

function Harness() {
  const settingsDraft = useTrainSettingsDraft();
  return (
    <>
      <TrainModeSettings settingsDraft={settingsDraft} />
      <TrainScheduleSettings settingsDraft={settingsDraft} isGuest={true} />
    </>
  );
}

function renderHarness(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  render(<Harness />, { wrapper: Wrapper });
}

async function advanceDebounce(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, TRAIN_SETTINGS_SAVE_DEBOUNCE_MS + 100));
  });
}

async function openRow(slug: 'puzzles' | 'blunder-check'): Promise<void> {
  await waitFor(() => {
    expect(screen.getByTestId('filter-weekday-mo').hasAttribute('disabled')).toBe(false);
  });
  fireEvent.click(screen.getByTestId(`btn-train-mode-settings-${slug}`));
}

beforeEach(() => {
  vi.mocked(useInstallPrompt).mockReturnValue({
    showAndroidPrompt: false,
    showIOSBanner: false,
    canInstall: false,
    isIOS: false,
    isStandalone: false,
    isMobile: false,
    triggerInstall: vi.fn(),
    dismissAndroid: vi.fn(),
    dismissIOS: vi.fn(),
  });
  vi.mocked(trainApi.getSettings).mockResolvedValue(BASE_SETTINGS);
});

afterEach(() => {
  cleanup();
  vi.mocked(trainApi.getSettings).mockReset();
  vi.mocked(trainApi.updateSettings).mockReset();
  vi.mocked(useInstallPrompt).mockReset();
});

describe('TrainModeSettings (tracer): the size slider saves through the shared draft', () => {
  it('renders both rows collapsed, with no slider until a row is opened (D-08)', async () => {
    renderHarness();
    await waitFor(() => {
      expect(screen.getByTestId('filter-weekday-mo').hasAttribute('disabled')).toBe(false);
    });
    expect(screen.getByTestId('train-mode-settings-puzzles')).not.toBeNull();
    expect(screen.getByTestId('train-mode-settings-blunder-check')).not.toBeNull();
    expect(screen.queryByTestId('filter-puzzles-per-session')).toBeNull();
    expect(screen.queryByTestId('filter-blunder-check-per-session')).toBeNull();
  });

  it('moving the blunder-check slider to 9 sends one PUT with blunder_check_per_session 9 and the unchanged puzzles size', async () => {
    vi.mocked(trainApi.updateSettings).mockResolvedValue({ ...BASE_SETTINGS, blunder_check_per_session: 9 });
    renderHarness();
    await openRow('blunder-check');

    const thumb = screen.getByRole('slider', { name: 'Blunder check sequences per session' });
    expect(thumb.getAttribute('aria-valuenow')).toBe('6');
    fireEvent.keyDown(thumb, { key: 'ArrowRight' });
    expect(screen.getByTestId('train-blunder-check-per-session-value').textContent).toBe('9');
    await advanceDebounce();

    expect(trainApi.updateSettings).toHaveBeenCalledTimes(1);
    const body = vi.mocked(trainApi.updateSettings).mock.calls[0]?.[0] as TrainSettingsUpdate;
    expect(body.blunder_check_per_session).toBe(9);
    expect(body.puzzles_per_session).toBe(BASE_SETTINGS.puzzles_per_session);
    // No level was chosen, so the key is omitted and the stored value is kept.
    expect(body).not.toHaveProperty('blunder_check_level');
  });

  it('a days edit made in the same burst rides the same PUT (one draft, no lost edit)', async () => {
    vi.mocked(trainApi.updateSettings).mockResolvedValue({
      ...BASE_SETTINGS,
      weekday_mask: 21,
      blunder_check_per_session: 9,
    });
    renderHarness();
    await openRow('blunder-check');

    fireEvent.click(screen.getByTestId('filter-weekday-fr'));
    fireEvent.keyDown(screen.getByRole('slider', { name: 'Blunder check sequences per session' }), {
      key: 'ArrowRight',
    });
    await advanceDebounce();

    expect(trainApi.updateSettings).toHaveBeenCalledTimes(1);
    const body = vi.mocked(trainApi.updateSettings).mock.calls[0]?.[0] as TrainSettingsUpdate;
    expect(body.weekday_mask).toBe(5 | (1 << 4));
    expect(body.blunder_check_per_session).toBe(9);
  });

  it('mount and opening a row send no PUT', async () => {
    renderHarness();
    await openRow('blunder-check');
    await advanceDebounce();
    expect(trainApi.updateSettings).not.toHaveBeenCalled();
  });
});

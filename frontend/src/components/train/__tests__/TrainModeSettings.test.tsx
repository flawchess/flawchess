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

// The rows read the per-mode progress (first_session_done, has_rated_games). A mutable
// module-level object lets each test pick the progress; the rest of the module (the query
// key `useTrainSettings` invalidates) stays real.
let progressMock: { data: TrainProgressResponse | undefined; isPending: boolean; isError: boolean };
vi.mock('@/hooks/useTrainProgress', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useTrainProgress')>('@/hooks/useTrainProgress');
  return { ...actual, useTrainProgress: () => progressMock };
});

import { trainApi } from '@/api/client';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';
import { TrainModeSettings } from '@/components/train/TrainModeSettings';
import { TrainScheduleSettings } from '@/components/train/TrainScheduleSettings';
import { TRAIN_SETTINGS_SAVE_DEBOUNCE_MS, useTrainSettingsDraft } from '@/hooks/useTrainSettingsDraft';
import {
  BLUNDER_CHECK_MODE,
  PHASE_251_PROGRESS_FIELDS,
  PUZZLES_MODE,
} from '@/components/train/__tests__/trainProgressFixtures';
import {
  BLUNDER_CHECK_PER_SESSION_MAX,
  BLUNDER_CHECK_PER_SESSION_MIN,
  BLUNDER_CHECK_PER_SESSION_STEP,
  PUZZLES_PER_SESSION_MAX,
  PUZZLES_PER_SESSION_MIN,
  PUZZLES_PER_SESSION_STEP,
} from '@/components/train/TrainModeSettings';
import { TRAIN_BLUNDER_CHECK_PER_SESSION_VALUES, TRAIN_PUZZLES_PER_SESSION_VALUES } from '@/lib/analytics';
import type {
  TrainBlunderCheckModeProgress,
  TrainModeProgress,
  TrainProgressResponse,
  TrainSettingsResponse,
  TrainSettingsUpdate,
} from '@/types/train';

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

function progressData(
  puzzles: Partial<TrainModeProgress> = {},
  blunderCheck: Partial<TrainBlunderCheckModeProgress> = {},
): TrainProgressResponse {
  return {
    session_streak_count: 0,
    shield_level: 0,
    current_week_completed: 0,
    current_week_required: null,
    streak_reset_notice: false,
    mastered_count: 0,
    parked_count: 0,
    waiting_count: 0,
    pool_state: 'available',
    next_due_date: null,
    badge_visible: false,
    ...PHASE_251_PROGRESS_FIELDS,
    modes: {
      puzzles: { ...PUZZLES_MODE, ...puzzles },
      blunder_check: { ...BLUNDER_CHECK_MODE, ...blunderCheck },
    },
  };
}

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
  progressMock = { data: progressData(), isPending: false, isError: false };
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

function mockSettings(overrides: Partial<TrainSettingsResponse>): void {
  vi.mocked(trainApi.getSettings).mockResolvedValue({ ...BASE_SETTINGS, ...overrides });
}

function sizeThumb(slug: 'puzzles' | 'blunder-check'): HTMLElement {
  const name = slug === 'puzzles' ? 'Puzzles per session' : 'Blunder check sequences per session';
  return screen.getByRole('slider', { name });
}

/**
 * Drives a real pointer drag on the Radix slider (jsdom has no layout, so the track rect and
 * pointer capture are stubbed): the track spans 0..TRACK_WIDTH_PX, so clientX maps linearly
 * onto the slider's min..max.
 */
const TRACK_WIDTH_PX = 1000;

function stubPointerLayout(slug: 'puzzles' | 'blunder-check'): HTMLElement {
  const slider = screen.getByTestId(
    slug === 'puzzles' ? 'filter-puzzles-per-session' : 'filter-blunder-check-per-session',
  );
  slider.getBoundingClientRect = () =>
    ({ left: 0, right: TRACK_WIDTH_PX, width: TRACK_WIDTH_PX, top: 0, bottom: 20, height: 20, x: 0, y: 0 }) as DOMRect;
  slider.setPointerCapture = vi.fn();
  slider.releasePointerCapture = vi.fn();
  slider.hasPointerCapture = () => true;
  return slider;
}

describe('size slider saves on release (WR-03, D-06)', () => {
  let track: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    track = vi.fn();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/train');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  it('an intermediate drag position never reaches the draft or the PUT; release sends one PUT with the final value', async () => {
    vi.mocked(trainApi.updateSettings).mockResolvedValue({ ...BASE_SETTINGS, blunder_check_per_session: 18 });
    renderHarness();
    await openRow('blunder-check');
    const slider = stubPointerLayout('blunder-check');

    // Slider range is 0..18; clientX 500 of 1000 is 9, 1000 is 18.
    fireEvent.pointerDown(slider, { pointerId: 1, clientX: 500, button: 0 });
    expect(screen.getByTestId('train-blunder-check-per-session-value').textContent).toBe('9');
    // Rest on the intermediate value well past the save debounce: nothing may be sent.
    await advanceDebounce();
    expect(trainApi.updateSettings).not.toHaveBeenCalled();
    // The collapsed summary reads the draft, which still holds the stored size.
    expect(screen.getByTestId('btn-train-mode-settings-blunder-check').textContent).toContain('6 per session');

    fireEvent.pointerMove(slider, { pointerId: 1, clientX: 1000 });
    expect(screen.getByTestId('train-blunder-check-per-session-value').textContent).toBe('18');
    expect(track.mock.calls).toEqual([]);
    fireEvent.pointerUp(slider, { pointerId: 1, clientX: 1000 });
    await advanceDebounce();

    expect(trainApi.updateSettings).toHaveBeenCalledTimes(1);
    const body = vi.mocked(trainApi.updateSettings).mock.calls[0]?.[0] as TrainSettingsUpdate;
    expect(body.blunder_check_per_session).toBe(18);
    // Unmounting flushes the debounced option-change: exactly one event, the final value.
    cleanup();
    expect(track.mock.calls).toEqual([
      ['option-change', { page: 'train', target: 'train-blunder-check-per-session', value: '18' }],
    ]);
  });

  it('keeps the never-both-off clamp: the last active slider cannot be committed to 0', async () => {
    mockSettings({ puzzles_per_session: 3, blunder_check_per_session: 0 });
    renderHarness();
    await openRow('puzzles');
    const slider = stubPointerLayout('puzzles');

    fireEvent.pointerDown(slider, { pointerId: 1, clientX: 0, button: 0 });
    fireEvent.pointerUp(slider, { pointerId: 1, clientX: 0 });
    await advanceDebounce();

    expect(sizeThumb('puzzles').getAttribute('aria-valuenow')).toBe('3');
    expect(trainApi.updateSettings).not.toHaveBeenCalled();
  });
});

describe('slider grids (drift guard)', () => {
  it('the tracked value lists match the slider grids, 0 (Off) included', () => {
    const puzzles: string[] = [];
    for (let n = PUZZLES_PER_SESSION_MIN; n <= PUZZLES_PER_SESSION_MAX; n += PUZZLES_PER_SESSION_STEP) {
      puzzles.push(String(n));
    }
    const blunderCheck: string[] = [];
    for (
      let n = BLUNDER_CHECK_PER_SESSION_MIN;
      n <= BLUNDER_CHECK_PER_SESSION_MAX;
      n += BLUNDER_CHECK_PER_SESSION_STEP
    ) {
      blunderCheck.push(String(n));
    }
    expect(PUZZLES_PER_SESSION_MIN).toBe(0);
    expect(BLUNDER_CHECK_PER_SESSION_MIN).toBe(0);
    expect(PUZZLES_PER_SESSION_MAX).toBe(30);
    expect(BLUNDER_CHECK_PER_SESSION_MAX).toBe(18);
    expect([...TRAIN_PUZZLES_PER_SESSION_VALUES]).toEqual(puzzles);
    expect([...TRAIN_BLUNDER_CHECK_PER_SESSION_VALUES]).toEqual(blunderCheck);
  });
});

describe('Off at 0 and the never-both-off clamp (D-04, D-05)', () => {
  it('dragging the puzzles slider to 0 shows Off on the value and the collapsed summary, and saves 0', async () => {
    mockSettings({ puzzles_per_session: 3 });
    vi.mocked(trainApi.updateSettings).mockResolvedValue({ ...BASE_SETTINGS, puzzles_per_session: 0 });
    renderHarness();
    await openRow('puzzles');

    expect(sizeThumb('puzzles').getAttribute('aria-valuemin')).toBe('0');
    fireEvent.keyDown(sizeThumb('puzzles'), { key: 'Home' });

    expect(screen.getByTestId('train-puzzles-per-session-value').textContent).toBe('Off');
    fireEvent.click(screen.getByTestId('btn-train-mode-settings-puzzles'));
    expect(screen.getByTestId('btn-train-mode-settings-puzzles').textContent).toContain('Off');
    await advanceDebounce();

    expect(trainApi.updateSettings).toHaveBeenCalledTimes(1);
    const body = vi.mocked(trainApi.updateSettings).mock.calls[0]?.[0] as TrainSettingsUpdate;
    expect(body.puzzles_per_session).toBe(0);
    expect(body.blunder_check_per_session).toBe(6);
  });

  it('the collapsed summary reads "N per session" when the mode is on', async () => {
    renderHarness();
    await waitFor(() => {
      expect(screen.getByTestId('btn-train-mode-settings-puzzles').textContent).toContain('12 per session');
    });
    expect(screen.getByTestId('btn-train-mode-settings-blunder-check').textContent).toContain('6 per session');
  });

  it('with blunder check off, the puzzles slider stops at 3 and shows the break hint', async () => {
    mockSettings({ blunder_check_per_session: 0 });
    renderHarness();
    await openRow('puzzles');

    expect(sizeThumb('puzzles').getAttribute('aria-valuemin')).toBe('3');
    expect(screen.getByTestId('train-mode-break-hint-puzzles').textContent).toBe(
      'To take a break, untick days in the schedule.',
    );
    // The other row is the one that is off: its own slider may go to 0 and has no hint.
    fireEvent.click(screen.getByTestId('btn-train-mode-settings-blunder-check'));
    expect(sizeThumb('blunder-check').getAttribute('aria-valuemin')).toBe('0');
    expect(screen.queryByTestId('train-mode-break-hint-blunder-check')).toBeNull();
    expect(screen.getByTestId('train-blunder-check-per-session-value').textContent).toBe('Off');
  });

  it('with puzzles off, the blunder-check slider stops at 3 and shows the break hint', async () => {
    mockSettings({ puzzles_per_session: 0 });
    renderHarness();
    await openRow('blunder-check');

    expect(sizeThumb('blunder-check').getAttribute('aria-valuemin')).toBe('3');
    expect(screen.getByTestId('train-mode-break-hint-blunder-check')).not.toBeNull();
  });

  it('Home on the last active slider never saves 0 (the UI cannot send both sizes at 0)', async () => {
    mockSettings({ puzzles_per_session: 3, blunder_check_per_session: 0 });
    renderHarness();
    await openRow('puzzles');

    fireEvent.keyDown(sizeThumb('puzzles'), { key: 'Home' });
    fireEvent.keyDown(sizeThumb('puzzles'), { key: 'ArrowLeft' });
    expect(sizeThumb('puzzles').getAttribute('aria-valuenow')).toBe('3');
    await advanceDebounce();
    expect(trainApi.updateSettings).not.toHaveBeenCalled();
  });
});

describe('How it works (D-10)', () => {
  it('is open until the first completed session in that mode, collapsed after it, per mode', async () => {
    progressMock = {
      data: progressData({ first_session_done: false }, { first_session_done: true }),
      isPending: false,
      isError: false,
    };
    renderHarness();
    await openRow('puzzles');
    fireEvent.click(screen.getByTestId('btn-train-mode-settings-blunder-check'));

    expect(screen.getByTestId('btn-train-mode-how-puzzles').getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByTestId('btn-train-mode-how-blunder-check').getAttribute('aria-expanded')).toBe('false');
    expect(screen.getByTestId('train-mode-how-puzzles').textContent).toContain(
      'Puzzles come from mistakes and blunders in your imported games.',
    );
    expect(screen.queryByText(/A false alarm ends the sequence/)).toBeNull();
  });

  it('the user can open a collapsed How it works and it then shows the blunder-check rules', async () => {
    progressMock = {
      data: progressData({}, { first_session_done: true }),
      isPending: false,
      isError: false,
    };
    renderHarness();
    await openRow('blunder-check');

    fireEvent.click(screen.getByTestId('btn-train-mode-how-blunder-check'));
    expect(screen.getByTestId('btn-train-mode-how-blunder-check').getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByText(/A false alarm ends the sequence, but you keep the pot\./)).not.toBeNull();
  });
});

describe('level picker (D-17)', () => {
  let track: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    track = vi.fn();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/train');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  it('shows only for a user without rated games, with Intermediate selected when no level is stored', async () => {
    progressMock = { data: progressData({}, { has_rated_games: false }), isPending: false, isError: false };
    renderHarness();
    await openRow('blunder-check');

    expect(screen.getByTestId('btn-train-level-intermediate').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('btn-train-level-beginner').getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByTestId('btn-train-level-advanced').getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByText('Your level (sets how hard the blunders are)')).not.toBeNull();
  });

  it('is absent for a user with rated games', async () => {
    progressMock = { data: progressData({}, { has_rated_games: true }), isPending: false, isError: false };
    renderHarness();
    await openRow('blunder-check');

    expect(screen.queryByTestId('btn-train-level-beginner')).toBeNull();
    expect(screen.queryByText('Your level (sets how hard the blunders are)')).toBeNull();
  });

  it('preselects the stored level', async () => {
    mockSettings({ blunder_check_level: 'advanced' });
    progressMock = { data: progressData({}, { has_rated_games: false }), isPending: false, isError: false };
    renderHarness();
    await openRow('blunder-check');

    expect(screen.getByTestId('btn-train-level-advanced').getAttribute('aria-pressed')).toBe('true');
  });

  it('picking Beginner sends blunder_check_level in the next save and one option-change event', async () => {
    progressMock = { data: progressData({}, { has_rated_games: false }), isPending: false, isError: false };
    vi.mocked(trainApi.updateSettings).mockResolvedValue({ ...BASE_SETTINGS, blunder_check_level: 'beginner' });
    renderHarness();
    await openRow('blunder-check');

    fireEvent.click(screen.getByTestId('btn-train-level-beginner'));
    fireEvent.click(screen.getByTestId('btn-train-level-beginner'));
    expect(screen.getByTestId('btn-train-level-beginner').getAttribute('aria-pressed')).toBe('true');
    expect(track.mock.calls).toEqual([
      ['option-change', { page: 'train', target: 'train-blunder-check-level', value: 'beginner' }],
    ]);
    await advanceDebounce();

    expect(trainApi.updateSettings).toHaveBeenCalledTimes(1);
    const body = vi.mocked(trainApi.updateSettings).mock.calls[0]?.[0] as TrainSettingsUpdate;
    expect(body.blunder_check_level).toBe('beginner');
  });
});

describe('Umami tracking of the size sliders', () => {
  let track: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    track = vi.fn();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/train');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  it('a puzzles slider burst sends exactly one debounced option-change with the final grid value', async () => {
    vi.mocked(trainApi.updateSettings).mockResolvedValue({ ...BASE_SETTINGS, puzzles_per_session: 18 });
    renderHarness();
    await openRow('puzzles');

    fireEvent.keyDown(sizeThumb('puzzles'), { key: 'ArrowRight' });
    fireEvent.keyDown(sizeThumb('puzzles'), { key: 'ArrowRight' });
    expect(track.mock.calls).toEqual([]);

    // Unmounting flushes the pending event.
    cleanup();
    expect(track.mock.calls).toEqual([
      ['option-change', { page: 'train', target: 'train-puzzles-per-session', value: '18' }],
    ]);
  });

  it('a blunder-check slider burst tracks its own target, and 0 is a registered value', async () => {
    renderHarness();
    await openRow('blunder-check');

    fireEvent.keyDown(sizeThumb('blunder-check'), { key: 'Home' });
    cleanup();
    expect(track.mock.calls).toEqual([
      ['option-change', { page: 'train', target: 'train-blunder-check-per-session', value: '0' }],
    ]);
  });

  it('mount, opening a row and settings load send no events', async () => {
    renderHarness();
    await openRow('puzzles');
    await advanceDebounce();
    expect(track.mock.calls).toEqual([]);
  });
});

// @vitest-environment jsdom
/**
 * SetupScreen.tsx tests (Phase 171 Plan 05, V-07/V-08/V-09/V-13).
 *
 * @sentry/react is mocked (its ESM module namespace is not configurable, so
 * a real import would break any spying) — mirrors botSetupSettings.test.ts.
 * jsdom supplies a real `localStorage`.
 */
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';

import { SetupScreen } from '../SetupScreen';
import {
  readSetupSettings,
  writeSetupSettings,
  DEFAULT_BOT_SETUP_SETTINGS,
} from '@/lib/botSetupSettings';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function eloThumb(): HTMLElement {
  return within(screen.getByTestId('setup-elo')).getByRole('slider');
}

describe('SetupScreen — defaults (V-13 setup half)', () => {
  it('mounts with a normalized rating and no saved settings: ELO snaps to the ladder, blend/TC/color are the defaults', () => {
    render(<SetupScreen ownerKey={null} normalizedRating={1650} onStart={vi.fn()} />);

    // resolveDefaultBotElo(1650) snaps to 1700 (Plan 04's pinned rounding).
    expect(screen.getByTestId('analysis-elo-selector-value').textContent).toBe('1700');
    // Default play-style preset is Light (blend 0.05).
    expect(screen.getByTestId('setup-play-style-summary').textContent).toBe(
      'Light — calculates a little',
    );
    expect(screen.getByTestId('setup-play-style-preset-light').getAttribute('aria-pressed')).toBe(
      'true',
    );
    expect(screen.getByTestId('setup-tc-rapid-10-0').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId(`setup-color-${DEFAULT_BOT_SETUP_SETTINGS.colorPreference}`).getAttribute('aria-pressed')).toBe(
      'true',
    );
  });

  it('normalizedRating null (no anchor) falls back to the 1500 default', () => {
    render(<SetupScreen ownerKey={null} normalizedRating={null} onStart={vi.fn()} />);
    expect(screen.getByTestId('analysis-elo-selector-value').textContent).toBe('1500');
  });

  it('the ELO ladder is the full 600-2600 range, not a narrowed band', () => {
    render(<SetupScreen ownerKey={null} normalizedRating={1650} onStart={vi.fn()} />);
    const thumb = eloThumb();
    expect(thumb.getAttribute('aria-valuemin')).toBe('600');
    expect(thumb.getAttribute('aria-valuemax')).toBe('2600');
  });
});

describe('SetupScreen — prefill from persisted settings', () => {
  it('every control prefills from a saved settings blob for the same ownerKey, overriding the profile default', () => {
    writeSetupSettings('owner-a', {
      botElo: 1800,
      blend: 0.05,
      baseSeconds: 300,
      incrementSeconds: 3,
      colorPreference: 'black',
    });

    render(<SetupScreen ownerKey="owner-a" normalizedRating={1200} onStart={vi.fn()} />);

    // The saved ELO (1800) wins over the profile-derived default for 1200.
    expect(screen.getByTestId('analysis-elo-selector-value').textContent).toBe('1800');
    expect(screen.getByTestId('setup-play-style-preset-light').getAttribute('aria-pressed')).toBe(
      'true',
    );
    expect(screen.getByTestId('setup-tc-blitz-5-3').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('setup-color-black').getAttribute('aria-pressed')).toBe('true');
  });
});

describe('SetupScreen — Start emits a fully-resolved BotGameSettings (V-07)', () => {
  it('selecting the 15+10 chip converts to seconds — no "15+10" string ever reaches the emitted object', () => {
    const onStart = vi.fn();
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={onStart} />);

    fireEvent.click(screen.getByTestId('setup-tc-rapid-15-10'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    expect(onStart).toHaveBeenCalledTimes(1);
    const emitted = onStart.mock.calls[0]?.[0];
    expect(emitted).toEqual(expect.objectContaining({ baseSeconds: 900, incrementSeconds: 10 }));
    expect(JSON.stringify(emitted)).not.toContain('15+10');
  });

  it('the Human preset makes Start emit blend: 0', () => {
    const onStart = vi.fn();
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={onStart} />);

    fireEvent.click(screen.getByTestId('setup-play-style-preset-human'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ blend: 0 }));
  });
});

describe('SetupScreen — Random resolves to a concrete color at Start (D-12, V-08)', () => {
  it('a Math.random stub < 0.5 resolves to "white"', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.1);
    const onStart = vi.fn();
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={onStart} />);

    fireEvent.click(screen.getByTestId('setup-color-random'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ userColor: 'white' }));
  });

  it('a Math.random stub >= 0.5 resolves to "black"', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.9);
    const onStart = vi.fn();
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={onStart} />);

    fireEvent.click(screen.getByTestId('setup-color-random'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ userColor: 'black' }));
  });

  it('without a stub, the emitted userColor is always "white" or "black", never "random"', () => {
    const onStart = vi.fn();
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={onStart} />);

    fireEvent.click(screen.getByTestId('setup-color-random'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    const emitted = onStart.mock.calls[0]?.[0] as { userColor: string };
    expect(['white', 'black']).toContain(emitted.userColor);
  });

  it('persists the UNRESOLVED "random" preference — a returning Random user stays Random', () => {
    const onStart = vi.fn();
    render(<SetupScreen ownerKey="owner-b" normalizedRating={1500} onStart={onStart} />);

    fireEvent.click(screen.getByTestId('setup-color-random'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    expect(readSetupSettings('owner-b')?.colorPreference).toBe('random');
  });
});

describe('SetupScreen — D-10 round-trip prefill', () => {
  it('unmounting and remounting with the same ownerKey prefills every control, including Random staying Random', () => {
    const { unmount } = render(
      <SetupScreen ownerKey="owner-c" normalizedRating={1500} onStart={vi.fn()} />,
    );
    fireEvent.click(screen.getByTestId('setup-tc-classical-30-20'));
    fireEvent.click(screen.getByTestId('btn-start-game'));
    unmount();

    render(<SetupScreen ownerKey="owner-c" normalizedRating={1500} onStart={vi.fn()} />);
    expect(screen.getByTestId('setup-tc-classical-30-20').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('setup-color-random').getAttribute('aria-pressed')).toBe('true');
  });
});

describe('SetupScreen — bottom-nav clearance (171 UAT gap 3, Task 1)', () => {
  it('the setup-screen root carries pb-20 sm:pb-4 so the fixed bottom nav never occludes Start', () => {
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={vi.fn()} />);
    const className = screen.getByTestId('setup-screen').className;
    expect(className).toContain('pb-20');
    expect(className).toContain('sm:pb-4');
  });
});

describe('mobile density (171 UAT gap 3, Task 2)', () => {
  it('the Start button is h-12 (48px) — the tallest control on the screen', () => {
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={vi.fn()} />);
    expect(screen.getByTestId('btn-start-game').className).toContain('h-12');
  });

  it('a TC chip is h-10 (40px), not h-11 (44px) — the density floor, not the old 44px height', () => {
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={vi.fn()} />);
    const className = screen.getByTestId('setup-tc-rapid-10-0').className;
    expect(className).toContain('h-10');
    expect(className).not.toContain('h-11');
  });

  it('all three TC bucket sub-headers render inline, and all three TC groups survive (not collapsed into one grid)', () => {
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={vi.fn()} />);
    expect(screen.getByText('Blitz')).toBeTruthy();
    expect(screen.getByText('Rapid')).toBeTruthy();
    expect(screen.getByText('Classical')).toBeTruthy();
    expect(screen.getByTestId('setup-tc-blitz-3-0')).toBeTruthy();
    expect(screen.getByTestId('setup-tc-rapid-10-0')).toBeTruthy();
    expect(screen.getByTestId('setup-tc-classical-30-0')).toBeTruthy();
  });
});

describe('SetupScreen — ELO info popover (D-05)', () => {
  it('renders the bot-specific honesty caveat copy', async () => {
    render(<SetupScreen ownerKey={null} normalizedRating={1500} onStart={vi.fn()} />);
    const trigger = screen.getByTestId('setup-elo-info');

    vi.useFakeTimers();
    try {
      fireEvent.mouseEnter(trigger);
      act(() => {
        vi.advanceTimersByTime(200);
      });
    } finally {
      vi.useRealTimers();
    }
    await waitFor(() => screen.getByText(/rating band whose/i));
    expect(screen.getByText(/Calibration is still in progress/i)).toBeTruthy();
  });
});

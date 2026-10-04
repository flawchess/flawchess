// @vitest-environment jsdom
/**
 * SettingsSheetButton.test.tsx: Phase 228 D-06 contract. The trigger opens a
 * sheet holding the FULL SettingsPanel, changes persist live, close works, and
 * nothing navigates.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SettingsSheetButton } from '@/components/settings/SettingsSheetButton';
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';

// Phase 230 D-16: the real card needs a QueryClientProvider; this suite renders the panel bare.
vi.mock('@/components/settings/LeaderboardPrivacyCard', () => ({
  LeaderboardPrivacyCard: () => null,
}));

// jsdom shims required by vaul's Drawer (copied from App.test.tsx).
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

if (!('scrollTo' in window) || typeof window.scrollTo !== 'function') {
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
}

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe('SettingsSheetButton', () => {
  it('renders an accessible trigger and no sheet before the click', () => {
    render(<SettingsSheetButton testId="btn-test-settings" />);
    const trigger = screen.getByTestId('btn-test-settings');
    expect(trigger.getAttribute('aria-label')).toBe('Settings');
    expect(trigger.getAttribute('title')).toBe('Settings');
    expect(screen.queryByTestId('settings-sheet')).toBeNull();
  });

  it('opens the full panel (all three sections) in the sheet', async () => {
    render(<SettingsSheetButton testId="btn-test-settings" />);
    fireEvent.click(screen.getByTestId('btn-test-settings'));

    const sheet = await screen.findByTestId('settings-sheet');
    expect(sheet.querySelector('[data-testid="settings-panel"]')).not.toBeNull();
    expect(screen.getByTestId('settings-section-sound')).toBeTruthy();
    expect(screen.getByTestId('settings-section-flawchess')).toBeTruthy();
    expect(screen.getByTestId('settings-section-stockfish')).toBeTruthy();
  });

  it('marks the open sheet as a modal dialog so board arrow-key navigation stays off', async () => {
    render(<SettingsSheetButton testId="btn-test-settings" />);
    fireEvent.click(screen.getByTestId('btn-test-settings'));

    await screen.findByTestId('settings-sheet');
    // The exact selector useBoardNavigationInput uses to suppress board stepping.
    expect(
      document.querySelector('[role="dialog"][aria-modal="true"][data-state="open"]'),
    ).not.toBeNull();
  });

  it('persists a change made inside the sheet immediately', async () => {
    render(<SettingsSheetButton testId="btn-test-settings" />);
    fireEvent.click(screen.getByTestId('btn-test-settings'));
    await screen.findByTestId('settings-sheet');

    fireEvent.click(screen.getByTestId('settings-sf-arrows-0'));
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.sfArrows)).toBe('0');
  });

  it('closes via the close button', async () => {
    render(<SettingsSheetButton testId="btn-test-settings" />);
    fireEvent.click(screen.getByTestId('btn-test-settings'));
    await screen.findByTestId('settings-sheet');

    fireEvent.click(screen.getByTestId('btn-settings-sheet-close'));
    await waitFor(() => expect(screen.queryByTestId('settings-sheet')).toBeNull());
  });

  it('returns keyboard focus to the cogwheel when the sheet closes', async () => {
    render(<SettingsSheetButton testId="btn-test-settings" />);
    const trigger = screen.getByTestId('btn-test-settings');
    trigger.focus();
    fireEvent.click(trigger);
    await screen.findByTestId('settings-sheet');

    // A keyboard user tabs into the sheet before closing it, so focus has left the
    // cogwheel and something must actively hand it back.
    const close = screen.getByTestId('btn-settings-sheet-close');
    close.focus();
    expect(document.activeElement).toBe(close);
    fireEvent.click(close);
    await waitFor(() => expect(screen.queryByTestId('settings-sheet')).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  describe('panel-open tracking', () => {
    const track = vi.fn();

    beforeEach(() => {
      track.mockClear();
      window.umami = { track, identify: vi.fn() };
      window.history.pushState({}, '', '/analysis');
    });

    afterEach(() => {
      delete window.umami;
      window.history.pushState({}, '', '/');
    });

    it('sends one panel-open settings when the trigger opens the sheet, none on mount', async () => {
      render(<SettingsSheetButton testId="btn-test-settings" />);
      expect(track).not.toHaveBeenCalled();

      fireEvent.click(screen.getByTestId('btn-test-settings'));
      await screen.findByTestId('settings-sheet');
      expect(track).toHaveBeenCalledTimes(1);
      expect(track).toHaveBeenCalledWith('panel-open', { page: 'analysis', target: 'settings' });
    });
  });
});

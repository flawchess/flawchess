// @vitest-environment jsdom
/**
 * SettingsPanel.test.tsx: Phase 228 panel contract (D-07..D-10), including the
 * pre-Phase-223 persisted mute value and the Umami once-per-real-change rule.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SettingsPanel } from '@/components/settings/SettingsPanel';
import { SETTINGS_STORAGE_KEYS } from '@/lib/engineSettings';
import { MUTE_KEY } from '@/lib/sounds';

const { trackEventMock } = vi.hoisted(() => ({ trackEventMock: vi.fn() }));
vi.mock('@/lib/analytics', () => ({ trackEvent: trackEventMock }));

beforeEach(() => {
  trackEventMock.mockClear();
});

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe('SettingsPanel layout (D-07, D-09)', () => {
  it('renders the three sections in order Sound, FlawChess engine, Stockfish', () => {
    render(<SettingsPanel />);
    const sound = screen.getByTestId('settings-section-sound');
    const fc = screen.getByTestId('settings-section-flawchess');
    const sf = screen.getByTestId('settings-section-stockfish');
    const follows = (a: HTMLElement, b: HTMLElement): boolean =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(follows(sound, fc)).toBe(true);
    expect(follows(fc, sf)).toBe(true);
    expect(screen.queryByRole('button', { name: /save/i })).toBeNull();
  });

  it('offers line buttons 1..5 and arrow buttons 0..3 for both engines', () => {
    render(<SettingsPanel />);
    for (const prefix of ['settings-fc', 'settings-sf']) {
      [1, 2, 3, 4, 5].forEach((n) => expect(screen.getByTestId(`${prefix}-lines-${n}`)).toBeTruthy());
      expect(screen.queryByTestId(`${prefix}-lines-0`)).toBeNull();
      [0, 1, 2, 3].forEach((n) => expect(screen.getByTestId(`${prefix}-arrows-${n}`)).toBeTruthy());
      expect(screen.queryByTestId(`${prefix}-arrows-4`)).toBeNull();
    }
  });
});

describe('Sound switch (legacy mute key)', () => {
  it('reads a pre-set muted value as off, and toggles the locked key', () => {
    localStorage.setItem(MUTE_KEY, '1');
    render(<SettingsPanel />);
    const sw = screen.getByTestId('settings-sound-switch');
    expect(sw.getAttribute('aria-checked')).toBe('false');

    fireEvent.click(sw);
    expect(localStorage.getItem(MUTE_KEY)).toBe('0');
    expect(trackEventMock).toHaveBeenCalledWith('settings-change', { setting: 'sound', value: 'on' });

    fireEvent.click(sw);
    expect(localStorage.getItem(MUTE_KEY)).toBe('1');
    expect(trackEventMock).toHaveBeenLastCalledWith('settings-change', { setting: 'sound', value: 'off' });
  });
});

describe('count controls (D-08, D-10)', () => {
  it('persists a change and fires settings-change exactly once; a re-tap does nothing', () => {
    render(<SettingsPanel />);
    fireEvent.click(screen.getByTestId('settings-fc-arrows-3'));
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.fcArrows)).toBe('3');
    expect(trackEventMock).toHaveBeenCalledTimes(1);
    expect(trackEventMock).toHaveBeenCalledWith('settings-change', { setting: 'fcArrows', value: '3' });

    // Re-tap the active item: Radix emits '' and the guard swallows it.
    localStorage.removeItem(SETTINGS_STORAGE_KEYS.fcArrows);
    fireEvent.click(screen.getByTestId('settings-fc-arrows-3'));
    expect(trackEventMock).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.fcArrows)).toBeNull();
  });

  it('does not fire when tapping the already-default value', () => {
    render(<SettingsPanel />);
    fireEvent.click(screen.getByTestId('settings-sf-lines-2'));
    expect(trackEventMock).not.toHaveBeenCalled();
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.sfLines)).toBeNull();
  });
});

describe('Reset to defaults (D-09, D-10)', () => {
  it('is disabled at defaults, enabled after a change, and restores everything with one event', () => {
    localStorage.setItem(MUTE_KEY, '1');
    render(<SettingsPanel />);
    const reset = screen.getByTestId('btn-settings-reset') as HTMLButtonElement;
    // Muted counts as a change from defaults.
    expect(reset.disabled).toBe(false);

    fireEvent.click(screen.getByTestId('settings-sf-lines-5'));
    fireEvent.click(screen.getByTestId('settings-fc-arrows-0'));
    trackEventMock.mockClear();

    fireEvent.click(reset);

    expect(trackEventMock).toHaveBeenCalledTimes(1);
    expect(trackEventMock).toHaveBeenCalledWith('settings-reset');
    expect(screen.getByTestId('settings-fc-lines-2').getAttribute('data-state')).toBe('on');
    expect(screen.getByTestId('settings-fc-arrows-1').getAttribute('data-state')).toBe('on');
    expect(screen.getByTestId('settings-sf-lines-2').getAttribute('data-state')).toBe('on');
    expect(screen.getByTestId('settings-sf-arrows-1').getAttribute('data-state')).toBe('on');
    expect(screen.getByTestId('settings-sound-switch').getAttribute('aria-checked')).toBe('true');
    expect((screen.getByTestId('btn-settings-reset') as HTMLButtonElement).disabled).toBe(true);
  });

  it('is disabled with an untouched store', () => {
    render(<SettingsPanel />);
    expect((screen.getByTestId('btn-settings-reset') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByTestId('settings-sf-arrows-2'));
    expect((screen.getByTestId('btn-settings-reset') as HTMLButtonElement).disabled).toBe(false);
  });
});

// @vitest-environment jsdom
/**
 * engineSettings.test.ts: Phase 228 store contract. Defaults with empty storage,
 * round trip with subscriber re-render (D-08), tamper-safe reads (T-228-01),
 * invalid writes refused, and reset of all five settings (D-09).
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  resetAllSettings,
  setCountSetting,
  SETTINGS_STORAGE_KEYS,
  useEngineDisplaySettings,
} from '@/lib/engineSettings';
import { MUTE_KEY, setMuted, useMuted } from '@/lib/sounds';

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('useEngineDisplaySettings', () => {
  it('returns the locked defaults with empty localStorage', () => {
    const { result } = renderHook(() => useEngineDisplaySettings());
    expect(result.current).toEqual({ fcLines: 2, fcArrows: 1, sfLines: 2, sfArrows: 1 });
  });

  it('round-trips setCountSetting and re-renders a mounted subscriber', () => {
    const { result } = renderHook(() => useEngineDisplaySettings());
    act(() => setCountSetting('sfLines', 4));
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.sfLines)).toBe('4');
    expect(result.current.sfLines).toBe(4);
  });

  it.each(['0', '6', '2.5', 'abc', '', '-1'])('reads stored %j for fcLines as the default', (raw) => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.fcLines, raw);
    const { result } = renderHook(() => useEngineDisplaySettings());
    expect(result.current.fcLines).toBe(2);
  });

  it.each(['0', '6', '2.5', 'abc', '', '-1'])('reads stored %j for sfLines as the default', (raw) => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.sfLines, raw);
    const { result } = renderHook(() => useEngineDisplaySettings());
    expect(result.current.sfLines).toBe(2);
  });

  it('accepts 0 as a valid arrow count and rejects out-of-range arrow values', () => {
    localStorage.setItem(SETTINGS_STORAGE_KEYS.sfArrows, '0');
    localStorage.setItem(SETTINGS_STORAGE_KEYS.fcArrows, '4');
    const { result } = renderHook(() => useEngineDisplaySettings());
    expect(result.current.sfArrows).toBe(0);
    expect(result.current.fcArrows).toBe(1);
  });

  it('yields the defaults when localStorage.getItem throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied');
    });
    const { result } = renderHook(() => useEngineDisplaySettings());
    expect(result.current).toEqual({ fcLines: 2, fcArrows: 1, sfLines: 2, sfArrows: 1 });
  });
});

describe('setCountSetting', () => {
  it('ignores invalid values without writing', () => {
    setCountSetting('fcArrows', 4);
    setCountSetting('sfLines', 0);
    setCountSetting('sfLines', 2.5);
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.fcArrows)).toBeNull();
    expect(localStorage.getItem(SETTINGS_STORAGE_KEYS.sfLines)).toBeNull();
  });

  it('does not throw when localStorage.setItem throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota');
    });
    expect(() => setCountSetting('fcLines', 3)).not.toThrow();
  });
});

describe('resetAllSettings', () => {
  it('removes the four count keys and unmutes sound', () => {
    setCountSetting('fcLines', 5);
    setCountSetting('fcArrows', 3);
    setCountSetting('sfLines', 4);
    setCountSetting('sfArrows', 0);
    setMuted(true);
    expect(localStorage.getItem(MUTE_KEY)).toBe('1');

    const settings = renderHook(() => useEngineDisplaySettings());
    const muted = renderHook(() => useMuted());
    expect(muted.result.current).toBe(true);

    act(() => resetAllSettings());

    Object.values(SETTINGS_STORAGE_KEYS).forEach((key) => {
      expect(localStorage.getItem(key)).toBeNull();
    });
    expect(settings.result.current).toEqual({ fcLines: 2, fcArrows: 1, sfLines: 2, sfArrows: 1 });
    expect(muted.result.current).toBe(false);
  });
});

// @vitest-environment jsdom
/**
 * botPersonaSetupSettings.ts unit tests (Phase 183, D-05).
 *
 * jsdom supplies a real `localStorage`; @sentry/react is mocked (mirrors
 * botSetupSettings.test.ts — the ESM module namespace is not configurable).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as Sentry from '@sentry/react';
import {
  readPersonaSetupSettings,
  writePersonaSetupSettings,
  BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX,
  DEFAULT_PERSONA_SETUP_SETTINGS,
  type BotPersonaSetupSettings,
} from '../botPersonaSetupSettings';
import { BOT_SETUP_SETTINGS_KEY_PREFIX } from '../../botSetupSettings';
import { BOT_GAME_SNAPSHOT_KEY_PREFIX } from '../../botGameSnapshot';
import { BOT_PENDING_STORE_KEY_PREFIX } from '../../botPendingStore';
import { DEFAULT_TC_PRESET_LABEL } from '../../botTimeControlPresets';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

const SETTINGS: BotPersonaSetupSettings = {
  colorPreference: 'white',
  tcLabel: '10+5',
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe('key distinctness', () => {
  it('the persona settings key prefix differs from every sibling bot-* key prefix', () => {
    expect(BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX).not.toBe(BOT_SETUP_SETTINGS_KEY_PREFIX);
    expect(BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX).not.toBe(BOT_GAME_SNAPSHOT_KEY_PREFIX);
    expect(BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX).not.toBe(BOT_PENDING_STORE_KEY_PREFIX);
  });

  it('the written key is exactly flawchess_bot_persona_settings:{owner}', () => {
    writePersonaSetupSettings('a@b.com', SETTINGS);
    expect(localStorage.getItem(`${BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX}a@b.com`)).not.toBeNull();
  });
});

describe('round-trip', () => {
  it('writeThenRead round-trips a {colorPreference, tcLabel} object under the new key for a given ownerKey', () => {
    writePersonaSetupSettings('a@b.com', SETTINGS);
    expect(readPersonaSetupSettings('a@b.com')).toEqual(SETTINGS);
  });

  it('a different owner reads null — settings are owner-scoped', () => {
    writePersonaSetupSettings('a@b.com', SETTINGS);
    expect(readPersonaSetupSettings('other@b.com')).toBeNull();
  });

  it('a null owner key uses the anon suffix, matching sibling key conventions', () => {
    writePersonaSetupSettings(null, SETTINGS);
    expect(readPersonaSetupSettings(undefined)).toEqual(SETTINGS);
    expect(localStorage.getItem(`${BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX}anon`)).not.toBeNull();
  });
});

describe('corruption recovery', () => {
  it('a garbage (non-JSON) blob reads back as null, clears the key, and captures to Sentry once', () => {
    const key = `${BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX}anon`;
    localStorage.setItem(key, 'not json');

    expect(readPersonaSetupSettings(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
    const call = vi.mocked(Sentry.captureException).mock.calls[0];
    expect(call?.[1]).toEqual({ tags: { source: 'bot-persona-setup-settings' } });
  });

  it('a well-formed-JSON but wrong-shaped blob reads back as null, clears the key, no throw', () => {
    const key = `${BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX}anon`;
    localStorage.setItem(key, JSON.stringify({ pgn: '...' }));

    expect(() => readPersonaSetupSettings(undefined)).not.toThrow();
    expect(readPersonaSetupSettings(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
  });

  it('an invalid colorPreference is treated as corruption: cleared + Sentry captured once, read returns null', () => {
    const key = `${BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX}anon`;
    localStorage.setItem(key, JSON.stringify({ colorPreference: 'purple', tcLabel: '10+0' }));

    expect(readPersonaSetupSettings(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  });

  it('accepts every valid colorPreference enum value', () => {
    for (const colorPreference of ['white', 'black', 'random'] as const) {
      const settings: BotPersonaSetupSettings = { colorPreference, tcLabel: '5+0' };
      writePersonaSetupSettings(undefined, settings);
      expect(readPersonaSetupSettings(undefined)).toEqual(settings);
    }
  });
});

describe('tcLabel tolerance', () => {
  it('an unrecognized tcLabel does NOT hard-fail the shape validator — it round-trips as-is for the caller to re-resolve', () => {
    const settings: BotPersonaSetupSettings = { colorPreference: 'black', tcLabel: '999+999' };
    writePersonaSetupSettings('a@b.com', settings);
    expect(readPersonaSetupSettings('a@b.com')).toEqual(settings);
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });
});

describe('SSR / storage-throw degradation', () => {
  it('readPersonaSetupSettings degrades to null when localStorage is undefined (SSR)', () => {
    const original = globalThis.localStorage;
    // @ts-expect-error -- simulate SSR by deleting the global
    delete globalThis.localStorage;
    try {
      expect(readPersonaSetupSettings('a@b.com')).toBeNull();
    } finally {
      globalThis.localStorage = original;
    }
  });

  it('writePersonaSetupSettings silently no-ops when localStorage is undefined (SSR)', () => {
    const original = globalThis.localStorage;
    // @ts-expect-error -- simulate SSR by deleting the global
    delete globalThis.localStorage;
    try {
      expect(() => writePersonaSetupSettings('a@b.com', SETTINGS)).not.toThrow();
    } finally {
      globalThis.localStorage = original;
    }
  });

  it('readPersonaSetupSettings degrades to null when localStorage.getItem throws', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable');
    });
    try {
      expect(readPersonaSetupSettings('a@b.com')).toBeNull();
    } finally {
      spy.mockRestore();
    }
  });

  it('writePersonaSetupSettings silently no-ops when localStorage.setItem throws', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    try {
      expect(() => writePersonaSetupSettings('a@b.com', SETTINGS)).not.toThrow();
    } finally {
      spy.mockRestore();
    }
  });
});

describe('does not clobber sibling keys', () => {
  it('writing persona settings leaves the sibling setup-settings key untouched', () => {
    localStorage.setItem(`${BOT_SETUP_SETTINGS_KEY_PREFIX}a@b.com`, JSON.stringify({ marker: 'sibling' }));
    writePersonaSetupSettings('a@b.com', SETTINGS);
    expect(localStorage.getItem(`${BOT_SETUP_SETTINGS_KEY_PREFIX}a@b.com`)).toBe(
      JSON.stringify({ marker: 'sibling' }),
    );
  });
});

describe('DEFAULT_PERSONA_SETUP_SETTINGS', () => {
  it('defaults to random color and the default TC preset label', () => {
    expect(DEFAULT_PERSONA_SETUP_SETTINGS.colorPreference).toBe('random');
    expect(DEFAULT_PERSONA_SETUP_SETTINGS.tcLabel).toBe(DEFAULT_TC_PRESET_LABEL);
  });
});

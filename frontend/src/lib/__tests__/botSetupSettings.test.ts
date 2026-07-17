// @vitest-environment jsdom
/**
 * botSetupSettings.ts unit tests (Phase 171 Plan 04, D-10/V-10).
 *
 * jsdom supplies a real `localStorage`; @sentry/react is mocked (mirrors
 * botGameSnapshot.test.ts — the ESM module namespace is not configurable).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as Sentry from '@sentry/react';
import {
  readSetupSettings,
  writeSetupSettings,
  BOT_SETUP_SETTINGS_KEY_PREFIX,
  BOT_SETUP_DEFAULT_ELO,
  DEFAULT_BOT_SETUP_SETTINGS,
  resolveDefaultBotElo,
  type BotSetupSettings,
} from '../botSetupSettings';
import { BOT_GAME_SNAPSHOT_KEY_PREFIX, writeSnapshot, readSnapshot } from '../botGameSnapshot';
import { BOT_PENDING_STORE_KEY_PREFIX, enqueuePendingStore, listPendingStore } from '../botPendingStore';
import { PLAY_STYLE_DEFAULT_BLEND } from '../playStyle';
import { MAIA_ELO_LADDER } from '../maiaEncoding';
import { Chess } from 'chess.js';

/** Ladder bounds, read from the ladder itself — the WR-02 test must not
 * re-hard-code the very literals the fix removed. */
const LADDER_MIN = MAIA_ELO_LADDER[0] ?? 0;
const LADDER_MAX = MAIA_ELO_LADDER[MAIA_ELO_LADDER.length - 1] ?? 0;

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

const SETTINGS: BotSetupSettings = {
  botElo: 1600,
  blend: 0.3,
  baseSeconds: 300,
  incrementSeconds: 3,
  colorPreference: 'white',
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe('key distinctness (T-171-04-03)', () => {
  it('the three owner-scoped key prefixes are pairwise distinct (imported constants, not hard-coded strings)', () => {
    expect(BOT_SETUP_SETTINGS_KEY_PREFIX).not.toBe(BOT_GAME_SNAPSHOT_KEY_PREFIX);
    expect(BOT_SETUP_SETTINGS_KEY_PREFIX).not.toBe(BOT_PENDING_STORE_KEY_PREFIX);
    expect(BOT_GAME_SNAPSHOT_KEY_PREFIX).not.toBe(BOT_PENDING_STORE_KEY_PREFIX);
  });

  it('the written key is exactly flawchess_bot_setup_settings:{owner}', () => {
    writeSetupSettings('a@b.com', SETTINGS);
    expect(localStorage.getItem(`${BOT_SETUP_SETTINGS_KEY_PREFIX}a@b.com`)).not.toBeNull();
  });
});

describe('round-trip', () => {
  it('writeSetupSettings then readSetupSettings for the same owner returns the same settings', () => {
    writeSetupSettings('a@b.com', SETTINGS);
    expect(readSetupSettings('a@b.com')).toEqual(SETTINGS);
  });

  it('a different owner reads null — settings are owner-scoped', () => {
    writeSetupSettings('a@b.com', SETTINGS);
    expect(readSetupSettings('other@b.com')).toBeNull();
  });

  it('a null owner key uses the anon suffix, matching botGameSnapshot convention', () => {
    writeSetupSettings(null, SETTINGS);
    expect(readSetupSettings(undefined)).toEqual(SETTINGS);
    expect(localStorage.getItem(`${BOT_SETUP_SETTINGS_KEY_PREFIX}anon`)).not.toBeNull();
  });
});

describe('does not clobber sibling keys', () => {
  it('writing settings leaves an existing snapshot and pending-store entry for the same owner intact', () => {
    const snapshotSettings = {
      botElo: 1500,
      blend: 0.5,
      baseSeconds: 300,
      incrementSeconds: 3,
      userColor: 'white' as const,
    };
    writeSnapshot('a@b.com', {
      version: 1,
      gameUuid: 'snap-1',
      settings: snapshotSettings,
      pgn: new Chess().pgn(),
      whiteClockMs: 300_000,
      blackClockMs: 300_000,
      movesSinceLastDecline: 0,
      hasLeftBook: false,
      hasFiredLowTime: false,
      savedAt: Date.now(),
    });
    enqueuePendingStore('a@b.com', {
      gameUuid: 'pending-1',
      pgn: new Chess().pgn(),
      settings: snapshotSettings,
      enqueuedAt: Date.now(),
    });

    writeSetupSettings('a@b.com', SETTINGS);

    expect(readSnapshot('a@b.com')?.gameUuid).toBe('snap-1');
    expect(listPendingStore('a@b.com')).toHaveLength(1);
    expect(listPendingStore('a@b.com')[0]?.gameUuid).toBe('pending-1');
  });
});

describe('corruption recovery', () => {
  it('a garbage (non-JSON) blob reads back as null, clears the key, and captures to Sentry once', () => {
    const key = `${BOT_SETUP_SETTINGS_KEY_PREFIX}anon`;
    localStorage.setItem(key, 'not json');

    expect(readSetupSettings(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  });

  it('a well-formed-JSON but wrong-shaped blob reads back as null, clears the key, no throw', () => {
    const key = `${BOT_SETUP_SETTINGS_KEY_PREFIX}anon`;
    localStorage.setItem(key, JSON.stringify({ pgn: '...' }));

    expect(() => readSetupSettings(undefined)).not.toThrow();
    expect(readSetupSettings(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
  });

  // WR-01 regression: a correctly-TYPED but out-of-RANGE blob used to validate
  // clean and reach the setup screen, `selectBotMove` (negative tau for
  // blend > 1), and finally the backend, whose Field bounds 422 it — which the
  // drain reads as "remove", silently discarding the finished game. These are
  // corruption and must take the clear-and-Sentry path.
  it.each([
    ['botElo above the ladder max', { ...SETTINGS, botElo: 40_000 }],
    ['botElo below the ladder min', { ...SETTINGS, botElo: 100 }],
    ['blend above BLEND_MAX', { ...SETTINGS, blend: 5 }],
    ['blend below HUMAN_BLEND', { ...SETTINGS, blend: -1 }],
    ['a NaN botElo', { ...SETTINGS, botElo: Number.NaN }],
  ])('rejects an out-of-range blob (%s): reads null, clears the key, captures once', (_label, blob) => {
    const key = `${BOT_SETUP_SETTINGS_KEY_PREFIX}anon`;
    localStorage.setItem(key, JSON.stringify(blob));

    expect(readSetupSettings(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  });

  it('accepts the ladder/blend boundary values (the bounds are INCLUSIVE)', () => {
    const atBounds: BotSetupSettings = { ...SETTINGS, botElo: 2600, blend: 1 };
    writeSetupSettings(undefined, atBounds);
    expect(readSetupSettings(undefined)).toEqual(atBounds);

    const atOtherBounds: BotSetupSettings = { ...SETTINGS, botElo: 600, blend: 0 };
    writeSetupSettings(undefined, atOtherBounds);
    expect(readSetupSettings(undefined)).toEqual(atOtherBounds);
  });
});

describe('resolveDefaultBotElo', () => {
  it('snaps a mid-rung rating to the nearest 100-Elo rung', () => {
    expect(resolveDefaultBotElo(1650)).toBe(1700);
  });

  it('falls back to 1500 for null', () => {
    expect(resolveDefaultBotElo(null)).toBe(1500);
  });

  it('falls back to 1500 for undefined', () => {
    expect(resolveDefaultBotElo(undefined)).toBe(1500);
  });

  it('falls back to 1500 for a non-finite value', () => {
    expect(resolveDefaultBotElo(Number.NaN)).toBe(1500);
  });

  it('clamps a below-ladder rating to the ladder minimum (600)', () => {
    expect(resolveDefaultBotElo(120)).toBe(600);
  });

  it('clamps an above-ladder rating to the ladder maximum (2600)', () => {
    expect(resolveDefaultBotElo(3400)).toBe(2600);
  });

  // WR-02 regression: the snap used a bare `step = 100` literal decoupled from
  // the ladder it snaps to, so a ladder revision would have produced values
  // that are NOT rungs — which EloSelector's prop contract forbids. Pin the
  // invariant itself (result ∈ ladder) rather than the arithmetic.
  it('always returns an ACTUAL ladder rung, for every rating across and beyond the ladder', () => {
    for (let rating = LADDER_MIN - 200; rating <= LADDER_MAX + 200; rating += 17) {
      expect(MAIA_ELO_LADDER).toContain(resolveDefaultBotElo(rating));
    }
  });
});

describe('DEFAULT_BOT_SETUP_SETTINGS', () => {
  it('pins the default blend, TC preset seconds, and color preference', () => {
    expect(DEFAULT_BOT_SETUP_SETTINGS.blend).toBe(PLAY_STYLE_DEFAULT_BLEND);
    expect(DEFAULT_BOT_SETUP_SETTINGS.baseSeconds).toBe(600);
    expect(DEFAULT_BOT_SETUP_SETTINGS.incrementSeconds).toBe(0);
    expect(DEFAULT_BOT_SETUP_SETTINGS.colorPreference).toBe('random');
    expect(DEFAULT_BOT_SETUP_SETTINGS.botElo).toBe(BOT_SETUP_DEFAULT_ELO);
  });
});

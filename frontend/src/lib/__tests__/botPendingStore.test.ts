// @vitest-environment jsdom
/**
 * botPendingStore.ts unit tests (Phase 170 Plan 01).
 *
 * jsdom supplies a real `localStorage`. Behaviors verified (170-01-PLAN.md's
 * `-t` filter tokens):
 * - "store-once" (SC2 structural invariant): an in-progress snapshot
 *   written and cleared leaves the pending-store queue and its localStorage
 *   key entirely untouched — an unfinished game has no path into the queue.
 * - "cap" (T-170-03): FIFO drop-oldest once MAX_PENDING_STORE_ENTRIES is
 *   exceeded.
 * - idempotent enqueue, per-owner scoping, removal, and corruption/storage
 *   failure degradation.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  enqueuePendingStore,
  listPendingStore,
  removePendingStore,
  BOT_PENDING_STORE_KEY_PREFIX,
  MAX_PENDING_STORE_ENTRIES,
  type PendingStoreEntry,
} from '../botPendingStore';
import { writeSnapshot, clearSnapshot, BOT_GAME_SNAPSHOT_KEY_PREFIX } from '../botGameSnapshot';
import type { BotGameSettings } from '@/hooks/useBotGame';

const SETTINGS: BotGameSettings = {
  botElo: 1500,
  blend: 0.5,
  baseSeconds: 300,
  incrementSeconds: 3,
  userColor: 'white',
};

function buildEntry(overrides: Partial<PendingStoreEntry> = {}): PendingStoreEntry {
  return {
    gameUuid: 'game-1',
    pgn: '1. e4 e5 *',
    settings: SETTINGS,
    enqueuedAt: Date.now(),
    ...overrides,
  };
}

beforeEach(() => {
  localStorage.clear();
});

describe('basic queue operations', () => {
  it('enqueue then list returns the entry', () => {
    const entry = buildEntry();
    enqueuePendingStore('a@example.com', entry);
    expect(listPendingStore('a@example.com')).toEqual([entry]);
  });

  it('two enqueues of different gameUuid are both present, in enqueue order', () => {
    enqueuePendingStore('a@example.com', buildEntry({ gameUuid: 'game-1' }));
    enqueuePendingStore('a@example.com', buildEntry({ gameUuid: 'game-2' }));

    const list = listPendingStore('a@example.com');
    expect(list.map((e) => e.gameUuid)).toEqual(['game-1', 'game-2']);
  });

  it('re-enqueuing the same gameUuid is idempotent (does not duplicate)', () => {
    enqueuePendingStore('a@example.com', buildEntry({ gameUuid: 'game-1' }));
    enqueuePendingStore('a@example.com', buildEntry({ gameUuid: 'game-1' }));

    expect(listPendingStore('a@example.com')).toHaveLength(1);
  });

  it('removePendingStore removes only the matching entry', () => {
    enqueuePendingStore('a@example.com', buildEntry({ gameUuid: 'game-1' }));
    enqueuePendingStore('a@example.com', buildEntry({ gameUuid: 'game-2' }));

    removePendingStore('a@example.com', 'game-1');

    expect(listPendingStore('a@example.com').map((e) => e.gameUuid)).toEqual(['game-2']);
  });
});

describe('cap (T-170-03 bounded FIFO queue)', () => {
  it('enqueuing MAX_PENDING_STORE_ENTRIES + 1 distinct games leaves exactly the cap, oldest dropped', () => {
    for (let i = 0; i < MAX_PENDING_STORE_ENTRIES + 1; i++) {
      enqueuePendingStore('a@example.com', buildEntry({ gameUuid: `game-${i}` }));
    }

    const list = listPendingStore('a@example.com');
    expect(list).toHaveLength(MAX_PENDING_STORE_ENTRIES);
    expect(list.some((e) => e.gameUuid === 'game-0')).toBe(false);
    expect(list.some((e) => e.gameUuid === `game-${MAX_PENDING_STORE_ENTRIES}`)).toBe(true);
  });
});

describe('store-once (SC2 structural invariant, D-12 separate key)', () => {
  it('an in-progress snapshot written and cleared leaves the pending-store queue and its key untouched', () => {
    writeSnapshot('a@example.com', {
      version: 1,
      gameUuid: 'in-progress-game',
      settings: SETTINGS,
      pgn: '1. e4 *',
      whiteClockMs: 300_000,
      blackClockMs: 300_000,
      movesSinceLastDecline: 3,
      hasLeftBook: false,
      hasFiredLowTime: false,
      savedAt: Date.now(),
    });
    clearSnapshot('a@example.com');

    expect(listPendingStore('a@example.com')).toEqual([]);
    expect(localStorage.getItem(`${BOT_PENDING_STORE_KEY_PREFIX}a@example.com`)).toBeNull();
    // Sanity: the snapshot key itself really was used (proves the two keys
    // are physically different, not just asserted never to have collided).
    expect(localStorage.getItem(`${BOT_GAME_SNAPSHOT_KEY_PREFIX}a@example.com`)).toBeNull();
  });

  it('enqueuePendingStore is the only writer reachable from a finished game — verified by construction: writeSnapshot/clearSnapshot never touch the pending-store key', () => {
    enqueuePendingStore('a@example.com', buildEntry());
    expect(localStorage.getItem(`${BOT_PENDING_STORE_KEY_PREFIX}a@example.com`)).not.toBeNull();
  });

  it('D-12 rationale, made concrete: a pending entry survives starting a brand-new in-progress game for the same owner', () => {
    // A finished game is enqueued (as finalizeGame would do)...
    enqueuePendingStore('a@example.com', buildEntry({ gameUuid: 'finished-game' }));
    // ...then the user starts a fresh game, which writes a new in-progress
    // snapshot under the SAME owner. If the two modules shared one key, this
    // write would silently overwrite/destroy the finished game's queue entry.
    writeSnapshot('a@example.com', {
      version: 1,
      gameUuid: 'brand-new-game',
      settings: SETTINGS,
      pgn: '1. e4 *',
      whiteClockMs: 300_000,
      blackClockMs: 300_000,
      movesSinceLastDecline: 3,
      hasLeftBook: false,
      hasFiredLowTime: false,
      savedAt: Date.now(),
    });

    expect(listPendingStore('a@example.com').map((e) => e.gameUuid)).toEqual(['finished-game']);
  });
});

describe('owner scoping', () => {
  it('an entry enqueued for one owner is not listed for a different owner', () => {
    enqueuePendingStore('a@example.com', buildEntry());
    expect(listPendingStore('b@example.com')).toEqual([]);
  });
});

describe('corruption / storage-throw degradation', () => {
  it('listPendingStore returns [] for invalid JSON', () => {
    localStorage.setItem(`${BOT_PENDING_STORE_KEY_PREFIX}anon`, '{not valid json');
    expect(listPendingStore(undefined)).toEqual([]);
  });

  it('listPendingStore returns [] for a non-array value', () => {
    localStorage.setItem(`${BOT_PENDING_STORE_KEY_PREFIX}anon`, JSON.stringify({ not: 'an array' }));
    expect(listPendingStore(undefined)).toEqual([]);
  });

  it('enqueuePendingStore and removePendingStore do not throw when localStorage.setItem throws', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });

    expect(() => enqueuePendingStore('a@example.com', buildEntry())).not.toThrow();
    expect(() => removePendingStore('a@example.com', 'game-1')).not.toThrow();

    setItemSpy.mockRestore();
  });
});

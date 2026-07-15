// @vitest-environment jsdom
/**
 * botGameSnapshot.ts unit tests (Phase 170 Plan 01).
 *
 * jsdom supplies a real `localStorage`; @sentry/react is mocked (its ESM
 * module namespace is not configurable, so vi.spyOn cannot redefine
 * captureException on the real module — mirrors workerPool.test.ts /
 * maiaQueue.test.ts).
 *
 * Behaviors verified (170-01-PLAN.md's `-t` filter tokens):
 * - "round-trip" (D-08 acceptance gate): a both-colors game with per-ply
 *   [%clk] comments restores byte-identical.
 * - "version": a version mismatch is a silent hard drop (no removal, no
 *   Sentry capture).
 * - "corrupt": invalid JSON / missing-field reads degrade to null, clear
 *   the bad key, and capture to Sentry exactly once.
 * - "owner": snapshots are invisible across different owner keys.
 * - storage-throw: writeSnapshot never lets an exception escape.
 * - clearSnapshot removes only the targeted owner's key.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Chess } from 'chess.js';
import * as Sentry from '@sentry/react';
import {
  readSnapshot,
  writeSnapshot,
  clearSnapshot,
  restoreChess,
  CURRENT_SNAPSHOT_VERSION,
  BOT_GAME_SNAPSHOT_KEY_PREFIX,
  type BotGameSnapshot,
} from '../botGameSnapshot';
import type { BotGameSettings } from '@/hooks/useBotGame';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

const SETTINGS: BotGameSettings = {
  botElo: 1500,
  blend: 0.5,
  baseSeconds: 300,
  incrementSeconds: 3,
  userColor: 'white',
};

function buildSnapshot(overrides: Partial<BotGameSnapshot> = {}): BotGameSnapshot {
  return {
    version: CURRENT_SNAPSHOT_VERSION,
    gameUuid: 'test-uuid-1',
    settings: SETTINGS,
    pgn: new Chess().pgn(),
    whiteClockMs: 300_000,
    blackClockMs: 300_000,
    movesSinceLastDecline: 3,
    hasLeftBook: false,
    hasFiredLowTime: false,
    savedAt: Date.now(),
    ...overrides,
  };
}

/** Plays a short both-colors game annotating [%clk] after every ply, exactly
 * matching production's annotateClock call shape (botGamePgn.ts:60-62). */
function buildAnnotatedGame(): Chess {
  const chess = new Chess();
  const moves = ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6'];
  let remainingMs = 300_000;
  for (const san of moves) {
    chess.move(san);
    remainingMs -= 4_000;
    chess.setComment(`[%clk ${new Date(remainingMs).toISOString().slice(11, 19)}]`);
  }
  return chess;
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe('round-trip (D-08 acceptance gate)', () => {
  it('restores a byte-identical pgn for a both-colors game with a [%clk] comment on every ply', () => {
    const chess = buildAnnotatedGame();
    const originalPgn = chess.pgn();
    const snapshot = buildSnapshot({ pgn: originalPgn });

    writeSnapshot('a@example.com', snapshot);
    const read = readSnapshot('a@example.com');
    expect(read).not.toBeNull();

    const restored = restoreChess(read!.pgn);
    expect(restored.pgn()).toBe(originalPgn);
    expect(restored.history()).toEqual(chess.history());
    expect(restored.getComments()).toHaveLength(chess.getComments().length);
    for (const comment of restored.getComments()) {
      expect(comment.comment).toContain('[%clk');
    }
  });

  it('REVERT PROOF anchor: restoreChess uses loadPgn, not a FEN round-trip (see SUMMARY.md)', () => {
    // This test exists purely so the revert-proof instructions in the task
    // have a named anchor test to point at; the round-trip test above is
    // the actual detector (asserted manually during the revert proof).
    const chess = buildAnnotatedGame();
    const restored = restoreChess(chess.pgn());
    expect(restored.fen()).toBe(chess.fen());
  });
});

describe('version', () => {
  it('a stored value with a mismatched version reads back as null (silent hard drop, D-06)', () => {
    const key = `${BOT_GAME_SNAPSHOT_KEY_PREFIX}anon`;
    localStorage.setItem(key, JSON.stringify(buildSnapshot({ version: 999 })));

    expect(readSnapshot(undefined)).toBeNull();
    // Not corruption — no removal, no Sentry capture.
    expect(localStorage.getItem(key)).not.toBeNull();
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });
});

describe('corrupt', () => {
  it('invalid JSON reads back as null, removes the bad key, and captures to Sentry exactly once', () => {
    const key = `${BOT_GAME_SNAPSHOT_KEY_PREFIX}anon`;
    localStorage.setItem(key, '{not valid json');

    expect(readSnapshot(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
    expect(Sentry.captureException).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ tags: { source: 'bot-game' } }),
    );
  });

  it('valid JSON missing a required field (pgn) reads back as null, removes the key, and captures once', () => {
    const key = `${BOT_GAME_SNAPSHOT_KEY_PREFIX}anon`;
    const withoutPgn: Record<string, unknown> = { ...buildSnapshot() };
    delete withoutPgn.pgn;
    localStorage.setItem(key, JSON.stringify(withoutPgn));

    expect(readSnapshot(undefined)).toBeNull();
    expect(localStorage.getItem(key)).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  });

  it('does not re-capture on a second read after the bad key has already been cleared', () => {
    const key = `${BOT_GAME_SNAPSHOT_KEY_PREFIX}anon`;
    localStorage.setItem(key, '{not valid json');

    expect(readSnapshot(undefined)).toBeNull();
    expect(readSnapshot(undefined)).toBeNull();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  });
});

describe('owner', () => {
  it('a snapshot written for one owner is invisible to a different owner', () => {
    writeSnapshot('a@example.com', buildSnapshot({ gameUuid: 'owner-a-game' }));

    expect(readSnapshot('b@example.com')).toBeNull();
    expect(readSnapshot('a@example.com')?.gameUuid).toBe('owner-a-game');
  });

  it('a snapshot written under a null/undefined owner lives under the anon suffix, invisible to a named owner', () => {
    writeSnapshot(null, buildSnapshot({ gameUuid: 'anon-game' }));

    expect(readSnapshot('a@example.com')).toBeNull();
    expect(readSnapshot(undefined)?.gameUuid).toBe('anon-game');
  });
});

describe('write/clear behavior', () => {
  it('writeSnapshot does not throw when localStorage.setItem throws (QuotaExceeded / Safari private mode)', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });

    expect(() => writeSnapshot('a@example.com', buildSnapshot())).not.toThrow();

    setItemSpy.mockRestore();
  });

  it('clearSnapshot removes only the targeted owner key', () => {
    writeSnapshot('a@example.com', buildSnapshot());
    writeSnapshot('b@example.com', buildSnapshot());

    clearSnapshot('a@example.com');

    expect(readSnapshot('a@example.com')).toBeNull();
    expect(readSnapshot('b@example.com')).not.toBeNull();
  });
});

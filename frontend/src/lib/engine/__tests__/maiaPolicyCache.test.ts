/**
 * maiaPolicyCache.ts unit tests — the shared, module-scoped, LRU `fen|elo`
 * policy cache (Phase 194 CACHE-01/02/05).
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  getCachedPolicy,
  setCachedPolicy,
  clearMaiaPolicyCache,
  markPolicyPending,
  getPendingPolicy,
  failPolicyPending,
  MAIA_POLICY_CACHE_MAX,
} from '../maiaPolicyCache';

const FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
const FEN_2 = 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1';

/** A FEN differing from `FEN` ONLY in the halfmove/fullmove counters (8XN-4). */
const FEN_COUNTER_VARIANT = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 12 40';

const BOARD_FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'] as const;
const ALL_SQUARES: string[] = BOARD_FILES.flatMap((file) =>
  Array.from({ length: 8 }, (_, i) => `${file}${i + 1}`),
);

function fileIndex(square: string): number {
  return BOARD_FILES.indexOf(square[0] as (typeof BOARD_FILES)[number]);
}

function kingChebyshevDistance(a: string, b: string): number {
  return Math.max(Math.abs(fileIndex(a) - fileIndex(b)), Math.abs(Number(a[1]) - Number(b[1])));
}

/** Kings-only board FEN for a (white king, black king) square pair, white to move. */
function kingsOnlyFen(whiteSq: string, blackSq: string): string {
  const board: (string | null)[][] = Array.from({ length: 8 }, () => Array<string | null>(8).fill(null));
  const place = (square: string, piece: string): void => {
    const rank = board[Number(square[1]) - 1];
    if (rank) rank[fileIndex(square)] = piece;
  };
  place(whiteSq, 'K');
  place(blackSq, 'k');
  const rows: string[] = [];
  for (let rank = 7; rank >= 0; rank -= 1) {
    let empty = 0;
    let row = '';
    for (let file = 0; file < 8; file += 1) {
      const piece = board[rank]?.[file];
      if (piece) {
        if (empty > 0) {
          row += String(empty);
          empty = 0;
        }
        row += piece;
      } else {
        empty += 1;
      }
    }
    if (empty > 0) row += String(empty);
    rows.push(row);
  }
  return `${rows.join('/')} w - - 0 1`;
}

/**
 * A valid, distinct FEN whose BOARD field varies (8XN-4 collapsed the cache
 * key to the first four FEN fields, so a fullmove-only variant is no longer a
 * distinct key). Enumerates non-adjacent (white king, black king) square
 * pairs in a fixed deterministic order — roughly 3600 such pairs exist,
 * comfortably past `MAIA_POLICY_CACHE_MAX + 1`, and every resulting position
 * is chess.js-parseable with at least one legal move for White.
 */
function fenVariant(n: number): string {
  let count = 0;
  for (const whiteSq of ALL_SQUARES) {
    for (const blackSq of ALL_SQUARES) {
      if (whiteSq === blackSq || kingChebyshevDistance(whiteSq, blackSq) <= 1) continue;
      if (count === n) return kingsOnlyFen(whiteSq, blackSq);
      count += 1;
    }
  }
  throw new Error(`fenVariant: exhausted king-pair space before reaching index ${n}`);
}

describe('maiaPolicyCache', () => {
  beforeEach(() => {
    clearMaiaPolicyCache();
  });

  it('getCachedPolicy returns undefined for a key never set', () => {
    expect(getCachedPolicy(FEN, 1500)).toBeUndefined();
  });

  it('getCachedPolicy returns the stored record for a key that was set', () => {
    const record = { e2e4: 0.6, d2d4: 0.4 };
    setCachedPolicy(FEN, 1500, record);
    expect(getCachedPolicy(FEN, 1500)).toEqual(record);
  });

  it('two different ELOs at the same FEN are two independent entries', () => {
    setCachedPolicy(FEN, 1200, { e2e4: 0.9 });
    setCachedPolicy(FEN, 2000, { d2d4: 0.9 });
    expect(getCachedPolicy(FEN, 1200)).toEqual({ e2e4: 0.9 });
    expect(getCachedPolicy(FEN, 2000)).toEqual({ d2d4: 0.9 });
    // A lookup at one ELO never returns the other's value.
    expect(getCachedPolicy(FEN, 1200)).not.toEqual({ d2d4: 0.9 });
  });

  it('the same ELO at two different FENs are two independent entries', () => {
    setCachedPolicy(FEN, 1500, { e2e4: 1 });
    setCachedPolicy(FEN_2, 1500, { d2d4: 1 });
    expect(getCachedPolicy(FEN, 1500)).toEqual({ e2e4: 1 });
    expect(getCachedPolicy(FEN_2, 1500)).toEqual({ d2d4: 1 });
  });

  it('clearMaiaPolicyCache() empties the cache', () => {
    setCachedPolicy(FEN, 1500, { e2e4: 1 });
    clearMaiaPolicyCache();
    expect(getCachedPolicy(FEN, 1500)).toBeUndefined();
  });

  // ─── 8XN-4: cache key normalized to the first four FEN fields ───────────

  describe('8XN-4 position-keyed cache (halfmove/fullmove-counter-insensitive)', () => {
    const FEN_CASTLING_VARIANT = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b Qkq e3 0 1';
    const FEN_EP_VARIANT = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';

    it('set under one halfmove/fullmove-counter pair, get under another, returns the same entry', () => {
      setCachedPolicy(FEN, 1500, { e2e4: 1 });
      expect(getCachedPolicy(FEN_COUNTER_VARIANT, 1500)).toEqual({ e2e4: 1 });
    });

    it('a differing castling field is an independent entry', () => {
      setCachedPolicy(FEN, 1500, { e2e4: 1 });
      expect(getCachedPolicy(FEN_CASTLING_VARIANT, 1500)).toBeUndefined();
    });

    it('a differing en-passant field is an independent entry', () => {
      setCachedPolicy(FEN, 1500, { e2e4: 1 });
      expect(getCachedPolicy(FEN_EP_VARIANT, 1500)).toBeUndefined();
    });

    it('markPolicyPending(fenA) makes getPendingPolicy return the same promise for a counter-variant FEN', () => {
      markPolicyPending(FEN, 1500);
      const viaFenA = getPendingPolicy(FEN, 1500);
      const viaVariant = getPendingPolicy(FEN_COUNTER_VARIANT, 1500);
      expect(viaVariant).toBe(viaFenA);
    });

    it('setCachedPolicy on the counter variant resolves the original FEN\'s pending waiter', async () => {
      markPolicyPending(FEN, 1500);
      const waiter = getPendingPolicy(FEN, 1500);
      setCachedPolicy(FEN_COUNTER_VARIANT, 1500, { d2d4: 1 });
      await expect(waiter).resolves.toEqual({ d2d4: 1 });
      expect(getCachedPolicy(FEN, 1500)).toEqual({ d2d4: 1 });
    });

    it('failPolicyPending on the counter variant rejects the original FEN\'s pending waiter', async () => {
      markPolicyPending(FEN, 1500);
      const waiter = getPendingPolicy(FEN, 1500);
      failPolicyPending(FEN_COUNTER_VARIANT, 1500, new Error('worker died'));
      await expect(waiter).rejects.toThrow('worker died');
      expect(getPendingPolicy(FEN, 1500)).toBeUndefined();
    });
  });

  // ─── Pending registry (quick 260906-gu2) ────────────────────────────────

  it('getPendingPolicy is undefined until a producer marks the key pending', () => {
    expect(getPendingPolicy(FEN, 1500)).toBeUndefined();
    markPolicyPending(FEN, 1500);
    expect(getPendingPolicy(FEN, 1500)).toBeInstanceOf(Promise);
    expect(getPendingPolicy(FEN, 1600)).toBeUndefined();
    expect(getPendingPolicy(FEN_2, 1500)).toBeUndefined();
  });

  it('setCachedPolicy resolves the pending promise with the stored policy and clears the pending entry', async () => {
    markPolicyPending(FEN, 1500);
    const waiter = getPendingPolicy(FEN, 1500);
    setCachedPolicy(FEN, 1500, { e2e4: 0.7, d2d4: 0.3 });
    await expect(waiter).resolves.toEqual({ e2e4: 0.7, d2d4: 0.3 });
    expect(getPendingPolicy(FEN, 1500)).toBeUndefined();
    expect(getCachedPolicy(FEN, 1500)).toEqual({ e2e4: 0.7, d2d4: 0.3 });
  });

  it('failPolicyPending rejects the pending promise and clears the entry; a later mark starts fresh', async () => {
    markPolicyPending(FEN, 1500);
    const waiter = getPendingPolicy(FEN, 1500);
    failPolicyPending(FEN, 1500, new Error('worker died'));
    await expect(waiter).rejects.toThrow('worker died');
    expect(getPendingPolicy(FEN, 1500)).toBeUndefined();
    markPolicyPending(FEN, 1500);
    expect(getPendingPolicy(FEN, 1500)).toBeInstanceOf(Promise);
  });

  it('markPolicyPending is a no-op for an already-cached or already-pending key', () => {
    setCachedPolicy(FEN, 1500, { e2e4: 1 });
    markPolicyPending(FEN, 1500);
    expect(getPendingPolicy(FEN, 1500)).toBeUndefined();

    markPolicyPending(FEN_2, 1500);
    const first = getPendingPolicy(FEN_2, 1500);
    markPolicyPending(FEN_2, 1500);
    expect(getPendingPolicy(FEN_2, 1500)).toBe(first);
  });

  it('failPolicyPending on a key that is not pending is a no-op', () => {
    expect(() => failPolicyPending(FEN, 1500, new Error('x'))).not.toThrow();
  });

  it('clearMaiaPolicyCache() rejects and drops pending entries too', async () => {
    markPolicyPending(FEN, 1500);
    const waiter = getPendingPolicy(FEN, 1500);
    clearMaiaPolicyCache();
    await expect(waiter).rejects.toThrow();
    expect(getPendingPolicy(FEN, 1500)).toBeUndefined();
  });

  it(
    'LRU (CACHE-01/02): filling to exactly MAIA_POLICY_CACHE_MAX evicts nothing; reading an entry then forcing one eviction spares it and evicts a never-read entry — fails under FIFO',
    () => {
      for (let i = 0; i < MAIA_POLICY_CACHE_MAX; i++) {
        setCachedPolicy(fenVariant(i), 1500, { e2e4: i });
      }
      // No eviction yet: the very first entry is still present.
      expect(getCachedPolicy(fenVariant(0), 1500)).toEqual({ e2e4: 0 });
      // Reading it above already touched it (MRU). Read it once more so the
      // assertion below is unambiguous even if a future refactor changes
      // getCachedPolicy's touch semantics.
      expect(getCachedPolicy(fenVariant(0), 1500)).toEqual({ e2e4: 0 });

      // One more distinct entry forces exactly one eviction.
      setCachedPolicy(fenVariant(MAIA_POLICY_CACHE_MAX), 1500, { e2e4: -1 });

      // fenVariant(0) was just touched -> must survive.
      expect(getCachedPolicy(fenVariant(0), 1500)).toEqual({ e2e4: 0 });
      // fenVariant(1) was never touched after its initial insert -> it is
      // the true least-recently-used entry and must have been evicted.
      // Under the previous FIFO implementation this assertion would fail,
      // because fenVariant(0) (inserted first) would have been evicted, not
      // fenVariant(1).
      expect(getCachedPolicy(fenVariant(1), 1500)).toBeUndefined();
    },
    15000,
  );

  it(
    'LRU (CACHE-02): a WRITE to an already-present key counts as a use — re-setting an entry spares it from the next eviction (fails when setCachedPolicy omits the delete-then-reinsert touch)',
    () => {
      for (let i = 0; i < MAIA_POLICY_CACHE_MAX; i++) {
        setCachedPolicy(fenVariant(i), 1500, { e2e4: i });
      }
      // Re-set (not read) the oldest entry. `Map.set` on an existing key does
      // NOT reorder it, so without an explicit delete-then-reinsert this write
      // leaves fenVariant(0) at the head of the eviction order.
      setCachedPolicy(fenVariant(0), 1500, { e2e4: 100 });

      // One more distinct entry forces exactly one eviction.
      setCachedPolicy(fenVariant(MAIA_POLICY_CACHE_MAX), 1500, { e2e4: -1 });

      // fenVariant(0) was just written -> most-recently-used -> must survive.
      expect(getCachedPolicy(fenVariant(0), 1500)).toEqual({ e2e4: 100 });
      // fenVariant(1) is now the true least-recently-used entry.
      expect(getCachedPolicy(fenVariant(1), 1500)).toBeUndefined();
    },
    15000,
  );
});

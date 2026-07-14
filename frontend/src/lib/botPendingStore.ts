/**
 * botPendingStore — the bounded, owner-scoped finished-bot-game queue
 * (Phase 170, RESUME-02).
 *
 * A finished game is enqueued here by `finalizeGame` and POSTed to
 * `/bots/games` on the next `/bots` mount (D-13's drain loop); the entry is
 * removed only on a confirmed 2xx. This module is a SIBLING of
 * `botGameSnapshot.ts`, not a dependent — it reuses the same
 * guard/try-catch/owner-scoping shape but lives on a physically SEPARATE
 * localStorage key (D-12): sharing one key with the in-progress snapshot
 * would mean a failed store followed by a new game silently overwrites and
 * loses the finished game forever. `enqueuePendingStore` is the ONLY
 * function in the codebase that writes a game into this queue — nothing in
 * `botGameSnapshot.ts` can reach this key, which is what makes RESUME-02's
 * "an abandoned game never reaches the server" structural rather than
 * convention-enforced.
 */

import type { BotGameSettings } from '@/hooks/useBotGame';

export const BOT_PENDING_STORE_KEY_PREFIX = 'flawchess_bot_pending_store:';

/** Bounds localStorage growth if the server is unreachable for a long
 * stretch: 10 finished games is far more than a single browser accumulates
 * between visits, and each entry is ~2 KB (170-RESEARCH.md payload-size
 * measurement). FIFO drop-oldest once exceeded (T-170-03). */
export const MAX_PENDING_STORE_ENTRIES = 10;

function pendingStoreKey(ownerKey: string | null | undefined): string {
  return `${BOT_PENDING_STORE_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}

export interface PendingStoreEntry {
  gameUuid: string;
  pgn: string;
  settings: BotGameSettings;
  enqueuedAt: number;
}

function isValidSettingsShape(value: unknown): value is BotGameSettings {
  if (typeof value !== 'object' || value === null) return false;
  const s = value as Record<string, unknown>;
  return (
    typeof s.botElo === 'number' &&
    typeof s.blend === 'number' &&
    typeof s.baseSeconds === 'number' &&
    typeof s.incrementSeconds === 'number' &&
    (s.userColor === 'white' || s.userColor === 'black')
  );
}

function isValidPendingEntry(value: unknown): value is PendingStoreEntry {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.gameUuid === 'string' &&
    typeof v.pgn === 'string' &&
    isValidSettingsShape(v.settings) &&
    typeof v.enqueuedAt === 'number'
  );
}

/** Reads the pending-store queue for `ownerKey`. Any failure (SSR, storage
 * throw, JSON.parse failure, a non-array value, or an element that is not a
 * well-shaped entry) degrades to `[]` — never a throw. A malformed array as
 * a whole is discarded wholesale rather than partially salvaged, matching
 * the simpler of the two options RESEARCH.md leaves as acceptable. */
export function listPendingStore(ownerKey: string | null | undefined): PendingStoreEntry[] {
  if (typeof localStorage === 'undefined') return [];
  try {
    const raw = localStorage.getItem(pendingStoreKey(ownerKey));
    if (raw === null) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed) || !parsed.every(isValidPendingEntry)) return [];
    return parsed;
  } catch {
    return [];
  }
}

function writePendingStore(ownerKey: string | null | undefined, entries: PendingStoreEntry[]): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(pendingStoreKey(ownerKey), JSON.stringify(entries));
  } catch {
    // QuotaExceededError / Safari private mode — degrade silently
  }
}

/** Enqueues a finished game. Idempotent by `gameUuid` (a second finalize of
 * the same game must not queue it twice) and FIFO-bounded at
 * `MAX_PENDING_STORE_ENTRIES` (T-170-03) — the oldest entry is dropped when
 * the cap is exceeded. Silent no-op on any storage failure. */
export function enqueuePendingStore(
  ownerKey: string | null | undefined,
  entry: PendingStoreEntry,
): void {
  const current = listPendingStore(ownerKey);
  if (current.some((e) => e.gameUuid === entry.gameUuid)) return;

  const next = [...current, entry];
  while (next.length > MAX_PENDING_STORE_ENTRIES) {
    next.shift();
  }
  writePendingStore(ownerKey, next);
}

/** Removes the entry matching `gameUuid` for `ownerKey`, if present. Silent
 * no-op on any storage failure. */
export function removePendingStore(
  ownerKey: string | null | undefined,
  gameUuid: string,
): void {
  const current = listPendingStore(ownerKey);
  const next = current.filter((e) => e.gameUuid !== gameUuid);
  writePendingStore(ownerKey, next);
}

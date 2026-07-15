/**
 * botGameSnapshot — the versioned, owner-scoped in-progress bot-game
 * localStorage snapshot (Phase 170, RESUME-01).
 *
 * Pure module, no React import (mirrors welcomeDismissal.ts's zero-React
 * shape — Bots.tsx reads this once on mount, no live-subscription
 * requirement). Persists `chess.pgn()` as the move/clock source of truth
 * (D-08 RESOLVED: chess.js 1.4.0 round-trips `{[%clk ...]}` comments through
 * `pgn() -> loadPgn() -> pgn()` losslessly — verified in 170-RESEARCH.md).
 * Do NOT swap this for a FEN or a bare SAN list: a FEN loses the move stack
 * (breaks 169.5's `resolveBookMove`, which requires `chess.history()`), and
 * a bare SAN list loses every `[%clk]` comment (`annotateClock` writes them
 * into chess.js's own comment store, not a parallel structure).
 *
 * Every read/write is guarded against the two localStorage failure modes
 * (`welcomeDismissal.ts`'s SSR guard + `useUserFlag.ts`'s try/catch shape):
 * an SSR/prerender environment with no `localStorage`, and a storage-API
 * throw (QuotaExceededError, Safari private mode). Both degrade to "no
 * resumable snapshot" — never a throw, never a crash (T-170-02).
 *
 * Owner scoping (T-170-04): the key is suffixed by the caller's email (or
 * 'anon'), copying `useUserFlag.ts`'s `storageKey` precedent verbatim — a
 * shared browser cannot bleed one account's resumable game into another's.
 */

import { Chess } from 'chess.js';
import * as Sentry from '@sentry/react';

import type { BotGameSettings } from '@/hooks/useBotGame';

/** Bumping this invalidates every existing snapshot (D-06: a schema-version
 * change is a silent hard drop, never a migration). */
export const CURRENT_SNAPSHOT_VERSION = 1;

export const BOT_GAME_SNAPSHOT_KEY_PREFIX = 'flawchess_bot_game:';

/** Owner-scoped key, copied from `useUserFlag.ts`'s `storageKey` — a
 * different key per account means a cross-user resume is structurally
 * impossible, not merely guard-enforced (T-170-04). */
function snapshotKey(ownerKey: string | null | undefined): string {
  return `${BOT_GAME_SNAPSHOT_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}

export interface BotGameSnapshot {
  version: number;
  gameUuid: string;
  settings: BotGameSettings;
  /** `chess.pgn()` at snapshot time — carries every `[%clk]` comment
   * losslessly (D-08 RESOLVED). The ONLY move/clock source of truth. */
  pgn: string;
  whiteClockMs: number;
  blackClockMs: number;
  movesSinceLastDecline: number;
  /** 169.5 D-03 one-way latch — cannot be re-derived from move history, a
   * fresh latch on resume would silently re-enter the book mid-game. */
  hasLeftBook: boolean;
  hasFiredLowTime: boolean;
  /** `Date.now()` at write time, for D-06's "2 days ago" age display. */
  savedAt: number;
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

/** Full shape/version type guard — call ONLY after a version match has
 * already been confirmed by the caller (see readSnapshot), so a clean
 * version-mismatch drop never routes through the corruption/Sentry path. */
function isValidSnapshotShape(value: unknown): value is BotGameSnapshot {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    v.version === CURRENT_SNAPSHOT_VERSION &&
    typeof v.gameUuid === 'string' &&
    isValidSettingsShape(v.settings) &&
    typeof v.pgn === 'string' &&
    typeof v.whiteClockMs === 'number' &&
    typeof v.blackClockMs === 'number' &&
    typeof v.movesSinceLastDecline === 'number' &&
    typeof v.hasLeftBook === 'boolean' &&
    typeof v.hasFiredLowTime === 'boolean' &&
    typeof v.savedAt === 'number'
  );
}

/** T-170-02: clears the bad key immediately so subsequent reads on the same
 * visit see a clean "no snapshot" state, and captures to Sentry exactly
 * ONCE at that clear point — otherwise a persistently-corrupted value would
 * spam Sentry on every `/bots` mount. */
function clearCorruptSnapshot(key: string, err: unknown): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // best-effort — nothing more to do if removal itself fails
  }
  Sentry.captureException(err, { tags: { source: 'bot-game' } });
}

/**
 * Reads and validates the in-progress snapshot for `ownerKey`. Any failure
 * (SSR, storage throw, JSON.parse failure, missing/mistyped field, or a
 * version mismatch) degrades to `null` — "no resumable snapshot". A parse
 * or shape-validation failure additionally clears the bad key and captures
 * to Sentry once; a clean version mismatch (D-06) is a silent hard drop
 * with no removal and no capture — it is expected schema evolution, not
 * corruption.
 */
export function readSnapshot(ownerKey: string | null | undefined): BotGameSnapshot | null {
  if (typeof localStorage === 'undefined') return null;

  const key = snapshotKey(ownerKey);
  let raw: string | null;
  try {
    raw = localStorage.getItem(key);
  } catch {
    return null;
  }
  if (raw === null) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    clearCorruptSnapshot(key, err);
    return null;
  }

  if (typeof parsed !== 'object' || parsed === null) {
    clearCorruptSnapshot(key, new Error('bot game snapshot is not an object'));
    return null;
  }

  const version = (parsed as Record<string, unknown>).version;
  if (version !== CURRENT_SNAPSHOT_VERSION) {
    return null;
  }

  if (!isValidSnapshotShape(parsed)) {
    clearCorruptSnapshot(key, new Error('bot game snapshot has an invalid shape'));
    return null;
  }

  return parsed;
}

/** Writes the in-progress snapshot for `ownerKey`. Silently no-ops on an
 * SSR environment or a storage throw (QuotaExceeded / Safari private mode)
 * — degrade, never crash the game. */
export function writeSnapshot(
  ownerKey: string | null | undefined,
  snapshot: BotGameSnapshot,
): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(snapshotKey(ownerKey), JSON.stringify(snapshot));
  } catch {
    // QuotaExceededError / Safari private mode — degrade to no-resume
  }
}

/** Removes the in-progress snapshot for `ownerKey` only. */
export function clearSnapshot(ownerKey: string | null | undefined): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.removeItem(snapshotKey(ownerKey));
  } catch {
    // best-effort
  }
}

/**
 * The ONLY snapshot->board replay path in the codebase (D-08). Do NOT add a
 * parallel SAN-replay helper: 169.5's `resolveBookMove` requires a board
 * with real pushed moves (`chess.history()`), which `loadPgn` satisfies for
 * free — a `new Chess(fen)` board silently matches the wrong ECO prefixes.
 */
export function restoreChess(pgn: string): Chess {
  const chess = new Chess();
  chess.loadPgn(pgn);
  return chess;
}

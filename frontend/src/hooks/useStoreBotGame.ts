/**
 * useStoreBotGame — the frontend's first call site of the shipped Phase 167
 * `POST /bots/games` endpoint, and the pending-store drain loop that decides
 * — per HTTP outcome — whether a queued finished game survives to the next
 * page visit (Phase 170 Plan 02, RESUME-02).
 *
 * `useDrainPendingStore` is the ONLY consumer of `botPendingStore.removePendingStore`
 * — the queue entry's life is decided in exactly one place.
 *
 * No `Sentry.captureException` is added here. The global `MutationCache.onError`
 * (`lib/queryClient.ts`) already captures every TanStack mutation failure with
 * `tags: { source: 'tanstack-mutation' }`; a second capture in this file would
 * violate CLAUDE.md's no-duplicate-capture rule and double-report every 422.
 */

import { useCallback } from 'react';
import axios from 'axios';
import { useMutation, type UseMutationResult } from '@tanstack/react-query';

import { botsApi } from '@/api/client';
import type { StoreBotGameRequest, StoreBotGameResponse } from '@/types/bots';
import { toBackendTcStr } from '@/lib/botGamePgn';
import { listPendingStore, removePendingStore, type PendingStoreEntry } from '@/lib/botPendingStore';

/** Bounded in-session retries for a transient (network/5xx) store failure. A
 * pending entry blocks nothing — the real retry is "the user's next visit"
 * (the drain loop, not this count), so a low number is right. */
export const MAX_STORE_RETRIES = 2;

/** HTTP status the server returns for an invalid PGN (a client bug) — never
 * worth retrying, in-session or across visits. */
const STATUS_UNPROCESSABLE = 422;

/**
 * Pure mapper from a queued entry to the wire request. Extracted so the
 * `tc_preset` invariant (base-SECONDS, D-14 corrected) is directly unit
 * testable without mounting a hook.
 */
export function toStoreRequest(entry: PendingStoreEntry): StoreBotGameRequest {
  return {
    game_uuid: entry.gameUuid,
    pgn: entry.pgn,
    user_color: entry.settings.userColor,
    bot_elo: entry.settings.botElo,
    play_style_blend: entry.settings.blend,
    tc_preset: toBackendTcStr(entry.settings.baseSeconds, entry.settings.incrementSeconds),
  };
}

/**
 * In-flight retry predicate for a single `mutate()` call (D-13). Extracted
 * as a pure, directly-testable function — mirrors `toStoreRequest`'s
 * testability rationale. 422 (invalid PGN) never retries; EVERY other failure
 * (401, network, 5xx) gets a BOUNDED retry.
 *
 * Bug fix (Phase 171 code review, CR-01): this predicate used to return `true`
 * UNCONDITIONALLY for a 401, with no `failureCount` bound. TanStack Query
 * treats an always-true `retry` predicate as an unbounded retry loop, so once
 * Phase 171 gave the hook its first component call site (`Bots.tsx`'s D-21
 * finish-time store), a finished game POSTed with an expired/absent token
 * would re-issue `POST /bots/games` forever (~every 30s, `retryDelay`'s cap)
 * for as long as the result screen stayed mounted. Worse, the mutation never
 * settled as errored, so the global `MutationCache.onError` never fired
 * (nothing reached Sentry) and `isSuccess` never flipped (the user saw no
 * signal at all). An unbounded in-flight retry also bought nothing: the
 * pending-store queue + next-visit drain IS the "retry once authenticated"
 * mechanism (D-13), and it is durable across reloads, which an in-flight loop
 * is not.
 *
 * This predicate only governs in-flight retries of ONE `mutate()` call —
 * whether a queue entry survives to the NEXT page visit is the drain loop's
 * decision (`useDrainPendingStore`), not this predicate's. A 401 keeps its
 * entry there, which is what makes the bound here safe.
 */
export function shouldRetryStore(failureCount: number, error: unknown): boolean {
  if (!axios.isAxiosError(error)) return failureCount < MAX_STORE_RETRIES;
  const status = error.response?.status;
  if (status === STATUS_UNPROCESSABLE) return false;
  return failureCount < MAX_STORE_RETRIES;
}

/**
 * TanStack mutation wrapping `botsApi.storeGame`. No `onSuccess` cache
 * invalidation (this is a queue-drain call site, not a query-backed list)
 * and no `Sentry.captureException` (see file header).
 */
export function useStoreBotGame(): UseMutationResult<
  StoreBotGameResponse,
  Error,
  StoreBotGameRequest
> {
  return useMutation<StoreBotGameResponse, Error, StoreBotGameRequest>({
    mutationFn: botsApi.storeGame,
    retry: shouldRetryStore,
  });
}

/**
 * Drains the pending-store queue for `ownerKey`: POSTs each entry to
 * `/bots/games` sequentially and decides per-outcome whether the entry
 * survives.
 *
 * - Any 2xx (`created: true` OR `false`) -> remove. `false` means the server
 *   already has it, which IS the success we want (safe to re-drain a
 *   resumed-then-finished game).
 * - 422 (invalid PGN, a client bug) -> remove. It can never succeed and
 *   would otherwise pin a permanent pending record. The global
 *   `MutationCache.onError` has already captured it to Sentry.
 * - 401 / 5xx / network error / anything else -> keep for the next visit.
 *
 * Entries are drained sequentially (`for...of` + `await`), not via
 * `Promise.all` — the queue is capped at `MAX_PENDING_STORE_ENTRIES`, so
 * serial is fine and it keeps each entry's outcome unambiguous. A single bad
 * entry never aborts the drain of the others, and `drain()` never rethrows
 * (it is called fire-and-forget from a mount effect).
 *
 * Uses its own `useMutation` — deliberately WITHOUT `shouldRetryStore` —
 * rather than `useStoreBotGame()`. The drain's real "retry" IS the next
 * `/bots` mount (D-13), so exactly ONE attempt per entry per drain is what we
 * want; the predicate's bounded in-flight retries would just multiply the
 * HTTP calls of a drain pass (up to `MAX_STORE_RETRIES + 1` per entry) while
 * a whole queue is being walked, for no durability gain. (Before CR-01 this
 * paragraph read "`shouldRetryStore` retries a 401 forever, which would hang
 * this loop" — that unbounded 401 branch is gone, so the reason to keep the
 * predicate out of the drain is now cost, not a hang.)
 */
export function useDrainPendingStore(ownerKey: string | null | undefined): {
  drain: () => Promise<void>;
} {
  const { mutateAsync } = useMutation<StoreBotGameResponse, Error, StoreBotGameRequest>({
    mutationFn: botsApi.storeGame,
  });

  const drain = useCallback(async (): Promise<void> => {
    const entries = listPendingStore(ownerKey);
    for (const entry of entries) {
      try {
        await mutateAsync(toStoreRequest(entry));
        removePendingStore(ownerKey, entry.gameUuid);
      } catch (err) {
        const status = axios.isAxiosError(err) ? err.response?.status : undefined;
        if (status === STATUS_UNPROCESSABLE) {
          removePendingStore(ownerKey, entry.gameUuid);
        }
        // 401 / 5xx / network / non-axios: keep the entry, retry next visit.
      }
    }
  }, [ownerKey, mutateAsync]);

  return { drain };
}

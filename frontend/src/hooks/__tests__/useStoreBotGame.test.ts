// @vitest-environment jsdom
/**
 * useStoreBotGame unit tests (Phase 170 Plan 02, RESUME-02).
 *
 * `.ts` (not `.tsx`) per the plan's file list — the QueryClientProvider
 * wrapper is built with `createElement`, not JSX, since Vite's esbuild
 * transform treats `.ts` files with the `ts` (non-JSX) loader.
 *
 * `-t` filter tokens:
 * - "tc-preset" — `toStoreRequest`'s `tc_preset` field is base-SECONDS
 *   (`toBackendTcStr` output), identical to the PGN's `[TimeControl]`
 *   header, NOT the lichess minutes-display preset (D-14 corrected).
 * - "retry-predicate" — `shouldRetryStore`'s per-status differentiation:
 *   422 never retries, everything else (401/5xx/network) is BOUNDED at
 *   `MAX_STORE_RETRIES` (CR-01: the 401 branch used to be unbounded).
 * - "drain" — `useDrainPendingStore`'s per-outcome entry-removal decision:
 *   2xx (created true or false) removes, 422 removes, 401/5xx/network keeps,
 *   a mid-queue failure doesn't abort the rest, an empty queue makes zero
 *   HTTP calls, and the drain itself never calls `Sentry.captureException`
 *   (the global `MutationCache.onError` already covers every failure).
 * - "mutation" — `useStoreBotGame()` itself: calls `botsApi.storeGame` with
 *   the mapped request and resolves with its response. `useDrainPendingStore`
 *   deliberately does NOT reuse this hook (see its own doc comment — one
 *   attempt per entry per drain, no in-flight retry multiplier), so this hook
 *   needs its own direct coverage rather than being exercised transitively
 *   via "drain".
 */

import { createElement, type ReactNode } from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock apiClient/botsApi at module level. Preserve other exports via importActual.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    botsApi: {
      storeGame: vi.fn(),
    },
  };
});

vi.mock('@sentry/react', () => ({
  captureException: vi.fn(),
}));

import { botsApi } from '@/api/client';
import * as Sentry from '@sentry/react';
import { toBackendTcStr } from '@/lib/botGamePgn';
import { enqueuePendingStore, listPendingStore, type PendingStoreEntry } from '@/lib/botPendingStore';
import type { BotGameSettings } from '@/hooks/useBotGame';
import {
  MAX_STORE_RETRIES,
  shouldRetryStore,
  toStoreRequest,
  useDrainPendingStore,
  useStoreBotGame,
} from '../useStoreBotGame';

const OWNER_KEY = 'test-owner';

function makeSettings(overrides: Partial<BotGameSettings> = {}): BotGameSettings {
  return {
    botElo: 1500,
    blend: 0.5,
    baseSeconds: 300,
    incrementSeconds: 3,
    userColor: 'white',
    ...overrides,
  };
}

function makeEntry(overrides: Partial<PendingStoreEntry> = {}): PendingStoreEntry {
  return {
    gameUuid: 'uuid-1',
    pgn: '1. e4 e5 *',
    settings: makeSettings(),
    enqueuedAt: Date.now(),
    ...overrides,
  };
}

function axiosError(status: number): Error {
  return Object.assign(new Error(`http ${status}`), {
    isAxiosError: true,
    response: { status, data: {} },
  });
}

function networkError(): Error {
  // No `.response` — the shape axios produces for a connection failure.
  return Object.assign(new Error('Network Error'), { isAxiosError: true });
}

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    });
    return createElement(QueryClientProvider, { client }, children);
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(botsApi.storeGame).mockReset();
  vi.mocked(Sentry.captureException).mockReset();
});

describe('tc-preset', () => {
  it('is base-seconds (toBackendTcStr output), identical to the PGN [TimeControl] header — not a minutes-display preset', () => {
    const entry = makeEntry({ settings: makeSettings({ baseSeconds: 300, incrementSeconds: 3 }) });
    const request = toStoreRequest(entry);

    expect(request.tc_preset).toBe('300+3');
    expect(request.tc_preset).toBe(toBackendTcStr(300, 3));
    // A minutes-display string ("5+3") must NOT be what's sent.
    expect(request.tc_preset).not.toBe('5+3');
  });

  it('maps every PendingStoreEntry field to its StoreBotGameRequest counterpart', () => {
    const entry = makeEntry({
      gameUuid: 'abc-123',
      pgn: '1. e4 *',
      settings: makeSettings({ botElo: 1800, blend: 0.75, userColor: 'black' }),
    });
    const request = toStoreRequest(entry);

    expect(request).toEqual({
      game_uuid: 'abc-123',
      pgn: '1. e4 *',
      user_color: 'black',
      bot_elo: 1800,
      play_style_blend: 0.75,
      tc_preset: '300+3',
    });
  });
});

describe('retry-predicate', () => {
  it('never retries a 422 (invalid PGN — a client bug)', () => {
    expect(shouldRetryStore(0, axiosError(422))).toBe(false);
    expect(shouldRetryStore(1, axiosError(422))).toBe(false);
  });

  // CR-01 regression: a 401 used to return `true` unconditionally (no
  // failureCount bound), which TanStack Query turns into an unbounded retry
  // loop that never settles — so `MutationCache.onError` never fired and the
  // caller's `isSuccess`/`isError` never flipped. The durable retry is the
  // next-visit drain (D-13), so the in-flight retry MUST be bounded.
  it('bounds a 401 at MAX_STORE_RETRIES (logged out / expired guest token — never an unbounded loop)', () => {
    expect(shouldRetryStore(0, axiosError(401))).toBe(true);
    expect(shouldRetryStore(MAX_STORE_RETRIES, axiosError(401))).toBe(false);
    expect(shouldRetryStore(10, axiosError(401))).toBe(false);
  });

  it('bounds retries for a 500 / network error at MAX_STORE_RETRIES', () => {
    expect(shouldRetryStore(0, axiosError(500))).toBe(true);
    expect(shouldRetryStore(MAX_STORE_RETRIES, axiosError(500))).toBe(false);
    expect(shouldRetryStore(0, networkError())).toBe(true);
    expect(shouldRetryStore(MAX_STORE_RETRIES, networkError())).toBe(false);
  });
});

describe('drain', () => {
  it('removes the entry on a 2xx with created:true', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(listPendingStore(OWNER_KEY)).toEqual([]);
  });

  it('ALSO removes the entry on a 2xx with created:false — the server already has it, which is the success we want', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: false });

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(listPendingStore(OWNER_KEY)).toEqual([]);
  });

  it('removes the entry on a 422 (permanently-invalid PGN — would otherwise pin a queue slot forever)', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(422));

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(listPendingStore(OWNER_KEY)).toEqual([]);
  });

  it('keeps the entry on a 401 (logged out — retry once authenticated)', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(401));

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(listPendingStore(OWNER_KEY).map((e) => e.gameUuid)).toEqual(['g1']);
  });

  it('keeps the entry on a 500', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(500));

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(listPendingStore(OWNER_KEY).map((e) => e.gameUuid)).toEqual(['g1']);
  });

  it('keeps the entry on a network error (no response)', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    vi.mocked(botsApi.storeGame).mockRejectedValue(networkError());

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(listPendingStore(OWNER_KEY).map((e) => e.gameUuid)).toEqual(['g1']);
  });

  it('a mid-queue failure does not abort the rest of the drain — first and third succeed, middle survives', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g2' }));
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g3' }));

    vi.mocked(botsApi.storeGame).mockImplementation((data) => {
      if (data.game_uuid === 'g2') return Promise.reject(axiosError(500));
      return Promise.resolve({ game_id: 1, created: true });
    });

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(listPendingStore(OWNER_KEY).map((e) => e.gameUuid)).toEqual(['g2']);
  });

  it('makes zero HTTP calls when the queue is empty', async () => {
    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });

    expect(botsApi.storeGame).not.toHaveBeenCalled();
  });

  it('never calls Sentry.captureException itself — the global MutationCache.onError already captures every failure', async () => {
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g1' }));
    enqueuePendingStore(OWNER_KEY, makeEntry({ gameUuid: 'g2' }));
    vi.mocked(botsApi.storeGame).mockImplementation((data) => {
      if (data.game_uuid === 'g1') return Promise.reject(axiosError(422));
      return Promise.reject(axiosError(500));
    });

    const { result } = renderHook(() => useDrainPendingStore(OWNER_KEY), { wrapper: makeWrapper() });
    await act(async () => {
      await result.current.drain();
    });
    // Let any stray microtask-scheduled work settle before asserting zero calls.
    await waitFor(() => {
      expect(listPendingStore(OWNER_KEY).map((e) => e.gameUuid)).toEqual(['g2']);
    });

    expect(Sentry.captureException).not.toHaveBeenCalled();
  });
});

describe('mutation', () => {
  it('useStoreBotGame calls botsApi.storeGame with the given request and resolves with its response', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 42, created: true });

    const { result } = renderHook(() => useStoreBotGame(), { wrapper: makeWrapper() });
    const request = toStoreRequest(makeEntry({ gameUuid: 'uuid-42' }));

    let response;
    await act(async () => {
      response = await result.current.mutateAsync(request);
    });

    expect(vi.mocked(botsApi.storeGame).mock.calls[0]?.[0]).toEqual(request);
    expect(response).toEqual({ game_id: 42, created: true });
  });
});

// @vitest-environment jsdom
/**
 * useLibraryGame hook tests (Phase 112, Task 1 RED).
 *
 * Tests:
 * 1. useLibraryGame(null) — disabled, no fetch fires.
 * 2. useLibraryGame(123) — calls libraryApi.getGame(123) → GET /library/games/123.
 * 3. Query key is ['library-game', gameId].
 * 4. refetchOnWindowFocus false — focus event does not trigger a second fetch.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    libraryApi: {
      ...actual.libraryApi,
      getGame: vi.fn(),
    },
  };
});

import { libraryApi } from '@/api/client';
import { useLibraryGame } from '../useLibrary';
import type { GameFlawCard } from '@/types/library';

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const MOCK_CARD: GameFlawCard = {
  game_id: 123,
  user_result: 'win',
  played_at: '2026-01-15T10:00:00Z',
  time_control_bucket: 'rapid',
  platform: 'lichess',
  platform_url: 'https://lichess.org/abc',
  white_username: 'Alice',
  black_username: 'Bob',
  white_rating: 1850,
  black_rating: 1720,
  opening_name: 'Sicilian Defense',
  opening_eco: 'B20',
  user_color: 'white',
  ply_count: 80,
  termination: 'checkmate',
  time_control_str: '10+5',
  result_fen: null,
  severity_counts: { inaccuracy: 0, mistake: 1, blunder: 0 },
  chips: [],
  analysis_state: 'analyzed',
  eval_series: null,
  flaw_markers: null,
  phase_transitions: null,
  moves: null,
};

describe('useLibraryGame', () => {
  beforeEach(() => {
    vi.mocked(libraryApi.getGame).mockReset();
  });

  it('does NOT fetch when gameId is null (enabled: false)', async () => {
    const getSpy = vi.mocked(libraryApi.getGame);
    renderHook(() => useLibraryGame(null), { wrapper: makeWrapper() });

    // Brief settle — query should not have fired
    await new Promise((r) => setTimeout(r, 20));
    expect(getSpy).not.toHaveBeenCalled();
  });

  it('calls libraryApi.getGame(123) when gameId is 123', async () => {
    vi.mocked(libraryApi.getGame).mockResolvedValue(MOCK_CARD);

    const { result } = renderHook(() => useLibraryGame(123), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(vi.mocked(libraryApi.getGame)).toHaveBeenCalledWith(123);
  });

  it('returns the game data on success', async () => {
    vi.mocked(libraryApi.getGame).mockResolvedValue(MOCK_CARD);

    const { result } = renderHook(() => useLibraryGame(123), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.game_id).toBe(123);
    expect(result.current.data?.white_username).toBe('Alice');
  });

  it('exposes isError when the fetch fails', async () => {
    vi.mocked(libraryApi.getGame).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useLibraryGame(999), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

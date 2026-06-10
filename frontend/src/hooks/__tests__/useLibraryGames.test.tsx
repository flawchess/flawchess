// @vitest-environment jsdom
/**
 * useLibraryGames hook tests — default-flaw-filter regression (quick-260610-vru).
 *
 * Bug: the default flaw filter (severity = blunder+mistake, no tags) was sent
 * to GET /library/games, where the backend's severity EXISTS excludes every
 * game without engine analysis — users with only unanalyzed games saw
 * "0 games matched" with no filters set.
 *
 * Tests:
 * 1. Default flaw filter → severity/tag are NOT sent (plain archive query).
 * 2. Non-default severity → severity IS sent.
 * 3. Default severity + a tag selected → both severity and tag are sent.
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
      getGames: vi.fn(),
    },
  };
});

import { libraryApi } from '@/api/client';
import { useLibraryGames } from '../useLibrary';
import { DEFAULT_FLAW_FILTER } from '@/hooks/useFlawFilterStore';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const EMPTY_RESPONSE = { games: [], matched_count: 0, total: 0 };

describe('useLibraryGames flaw-filter params', () => {
  beforeEach(() => {
    vi.mocked(libraryApi.getGames).mockReset();
    vi.mocked(libraryApi.getGames).mockResolvedValue(EMPTY_RESPONSE);
  });

  it('omits severity and tag when the flaw filter is at its default', async () => {
    renderHook(() => useLibraryGames(DEFAULT_FILTERS, { ...DEFAULT_FLAW_FILTER }, 0, 20), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.severity).toBeUndefined();
    expect(params.tag).toBeUndefined();
  });

  it('sends severity when the user narrowed it from the default', async () => {
    renderHook(
      () => useLibraryGames(DEFAULT_FILTERS, { severity: ['blunder'], tags: [] }, 0, 20),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.severity).toEqual(['blunder']);
    expect(params.tag).toBeUndefined();
  });

  it('sends severity and tag when a tag is selected (default severity kept)', async () => {
    renderHook(
      () =>
        useLibraryGames(
          DEFAULT_FILTERS,
          { severity: ['blunder', 'mistake'], tags: ['miss'] },
          0,
          20,
        ),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.severity).toEqual(['blunder', 'mistake']);
    expect(params.tag).toEqual(['miss']);
  });
});

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

  // Quick 260620-pza: tactic filters threaded to the Games tab.
  // Quick 260621-sm8: depth + orientation are independently meaningful, so they
  // are always sent (the all-inclusive default is a backend no-op). Family is sent
  // only when ≥1 is selected. Previously all three were gated behind family, so a
  // depth-only/orientation-only filter never reached the backend (the bug).
  it('sends orientation and depth (not family) at the default flaw filter', async () => {
    renderHook(() => useLibraryGames(DEFAULT_FILTERS, { ...DEFAULT_FLAW_FILTER }, 0, 20), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.tactic_family).toBeUndefined();
    expect(params.tactic_orientation).toBe('either');
    // Default depth is the full High range; bounds are still sent (backend no-op).
    expect(params.min_tactic_depth).toBe(DEFAULT_FLAW_FILTER.tacticDepthMin);
    expect(params.max_tactic_depth).toBe(DEFAULT_FLAW_FILTER.tacticDepthMax);
  });

  it('sends a depth range with no family selected (depth-only filter)', async () => {
    renderHook(
      () =>
        useLibraryGames(
          DEFAULT_FILTERS,
          { ...DEFAULT_FLAW_FILTER, tacticDepthMin: 1, tacticDepthMax: 2 },
          0,
          20,
        ),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.tactic_family).toBeUndefined();
    expect(params.tactic_orientation).toBe('either');
    expect(params.min_tactic_depth).toBe(1);
    expect(params.max_tactic_depth).toBe(2);
  });

  it('sends tactic family, orientation and depth when a family is selected', async () => {
    renderHook(
      () =>
        useLibraryGames(
          DEFAULT_FILTERS,
          {
            ...DEFAULT_FLAW_FILTER,
            tacticFamilies: ['fork'],
            tacticOrientation: 'missed',
            tacticDepthMin: 0,
            tacticDepthMax: 5,
          },
          0,
          20,
        ),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.tactic_family).toEqual(['fork']);
    expect(params.tactic_orientation).toEqual('missed');
    expect(params.min_tactic_depth).toBe(0);
    expect(params.max_tactic_depth).toBe(5);
  });
});

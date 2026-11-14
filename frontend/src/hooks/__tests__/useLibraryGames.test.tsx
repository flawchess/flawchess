// @vitest-environment jsdom
/**
 * useLibraryGames hook tests — default-flaw-filter regression.
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
      getFlaws: vi.fn(),
    },
  };
});

import { libraryApi } from '@/api/client';
import { useLibraryFlaws, useLibraryGames } from '../useLibrary';
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

  // Tactic filters threaded to the Games tab.
  // Depth + orientation are independently meaningful, so they
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

const EMPTY_FLAWS_RESPONSE = { flaws: [], matched_count: 0, total: 0 };

describe('useLibraryFlaws facepalm params', () => {
  beforeEach(() => {
    vi.mocked(libraryApi.getFlaws).mockReset();
    vi.mocked(libraryApi.getFlaws).mockResolvedValue(
      EMPTY_FLAWS_RESPONSE as unknown as Awaited<ReturnType<typeof libraryApi.getFlaws>>,
    );
  });

  it('sends no facepalm keys at the default flaw filter (D-04)', async () => {
    renderHook(() => useLibraryFlaws(DEFAULT_FILTERS, { ...DEFAULT_FLAW_FILTER }, 0, 20), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(vi.mocked(libraryApi.getFlaws)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getFlaws).mock.calls[0]![0];
    expect('min_facepalm_pct' in params).toBe(false);
    expect('max_facepalm_pct' in params).toBe(false);
  });

  it('sends 70 and 100 for the High range', async () => {
    renderHook(
      () =>
        useLibraryFlaws(
          DEFAULT_FILTERS,
          { ...DEFAULT_FLAW_FILTER, facepalmMin: 70, facepalmMax: 100 },
          0,
          20,
        ),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getFlaws)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getFlaws).mock.calls[0]![0];
    expect(params.min_facepalm_pct).toBe(70);
    expect(params.max_facepalm_pct).toBe(100);
  });

  it('sends 0 and 29 for the Low range (handles 0/25)', async () => {
    renderHook(
      () =>
        useLibraryFlaws(
          DEFAULT_FILTERS,
          { ...DEFAULT_FLAW_FILTER, facepalmMin: 0, facepalmMax: 25 },
          0,
          20,
        ),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getFlaws)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getFlaws).mock.calls[0]![0];
    expect(params.min_facepalm_pct).toBe(0);
    expect(params.max_facepalm_pct).toBe(29);
  });
});

describe('useLibraryGames facepalm params', () => {
  beforeEach(() => {
    vi.mocked(libraryApi.getGames).mockReset();
    vi.mocked(libraryApi.getGames).mockResolvedValue(EMPTY_RESPONSE);
  });

  it('sends no facepalm keys at the default flaw filter (D-04)', async () => {
    renderHook(() => useLibraryGames(DEFAULT_FILTERS, { ...DEFAULT_FLAW_FILTER }, 0, 20), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect('min_facepalm_pct' in params).toBe(false);
    expect('max_facepalm_pct' in params).toBe(false);
  });

  it('sends 70 and 100 for the High range', async () => {
    renderHook(
      () =>
        useLibraryGames(
          DEFAULT_FILTERS,
          { ...DEFAULT_FLAW_FILTER, facepalmMin: 70, facepalmMax: 100 },
          0,
          20,
        ),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.min_facepalm_pct).toBe(70);
    expect(params.max_facepalm_pct).toBe(100);
  });

  it('sends 30 and 69 for the Mid range (handles 30/65)', async () => {
    renderHook(
      () =>
        useLibraryGames(
          DEFAULT_FILTERS,
          { ...DEFAULT_FLAW_FILTER, facepalmMin: 30, facepalmMax: 65 },
          0,
          20,
        ),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalled());
    const params = vi.mocked(libraryApi.getGames).mock.calls[0]![0];
    expect(params.min_facepalm_pct).toBe(30);
    expect(params.max_facepalm_pct).toBe(69);
  });

  it('refetches when only the facepalm range changes (query key)', async () => {
    // One shared client: makeWrapper() builds a fresh client per render, which would
    // refetch on rerender regardless of the query key and make this test vacuous.
    const sharedClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const sharedWrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={sharedClient}>{children}</QueryClientProvider>
    );
    const { rerender } = renderHook(
      ({ flawFilter }) => useLibraryGames(DEFAULT_FILTERS, flawFilter, 0, 20),
      {
        wrapper: sharedWrapper,
        initialProps: { flawFilter: { ...DEFAULT_FLAW_FILTER } },
      },
    );

    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalledTimes(1));
    rerender({ flawFilter: { ...DEFAULT_FLAW_FILTER, facepalmMin: 70, facepalmMax: 100 } });
    await waitFor(() => expect(vi.mocked(libraryApi.getGames)).toHaveBeenCalledTimes(2));
  });
});

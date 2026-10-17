// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock endgameApi at module level. Preserve other exports via importActual.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    endgameApi: {
      ...actual.endgameApi,
      getStats: vi.fn(),
    },
  };
});

import { endgameApi } from '@/api/client';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { FilterState } from '@/components/filters/FilterPanel';
import { useEndgameStats } from '../useEndgames';

function makeClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function makeWrapper(
  client: QueryClient = makeClient(),
): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const FILTERED: FilterState = {
  ...DEFAULT_FILTERS,
  timeControls: ['blitz'],
  platforms: ['lichess'],
  rated: true,
};

async function flush(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
  });
}

describe('useEndgameStats', () => {
  beforeEach(() => {
    vi.mocked(endgameApi.getStats).mockReset();
    vi.mocked(endgameApi.getStats).mockResolvedValue({} as never);
  });

  // While the endgame page is locked (tier2=false) the stats
  // must NOT fetch — a fetch during the locked phase caches a pre-Stage-B
  // response that the 5min staleTime then keeps serving after the unlock.
  it('does NOT fetch while disabled (page locked, tier2=false)', async () => {
    renderHook(() => useEndgameStats(DEFAULT_FILTERS, { enabled: false }), {
      wrapper: makeWrapper(),
    });
    await flush();
    expect(endgameApi.getStats).not.toHaveBeenCalled();
  });

  it('defaults to enabled when no options are passed', async () => {
    renderHook(() => useEndgameStats(DEFAULT_FILTERS), { wrapper: makeWrapper() });
    await flush();
    expect(endgameApi.getStats).toHaveBeenCalledTimes(1);
  });

  it('fetches only after enabled flips false to true (the unlock transition)', async () => {
    const { rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => useEndgameStats(DEFAULT_FILTERS, { enabled }),
      { wrapper: makeWrapper(), initialProps: { enabled: false } },
    );
    await flush();
    expect(endgameApi.getStats).not.toHaveBeenCalled();

    rerender({ enabled: true });
    await flush();
    expect(endgameApi.getStats).toHaveBeenCalledTimes(1);
  });

  it('forwards the applied filters as endgame request params', async () => {
    renderHook(() => useEndgameStats(FILTERED), { wrapper: makeWrapper() });
    await flush();

    expect(endgameApi.getStats).toHaveBeenCalledTimes(1);
    const params = vi.mocked(endgameApi.getStats).mock.calls[0]![0];
    expect(params).toMatchObject({
      time_control: ['blitz'],
      platform: ['lichess'],
      rated: true,
      opponent_type: FILTERED.opponentType,
    });
    // No color: endgame queries are color-agnostic.
    expect(params).not.toHaveProperty('color');
  });

  it("caches under the ['endgameOverview', 'stats'] prefix so import invalidations match", async () => {
    const client = makeClient();
    renderHook(() => useEndgameStats(DEFAULT_FILTERS), { wrapper: makeWrapper(client) });
    await flush();

    const keys = client.getQueryCache().getAll().map((q) => q.queryKey);
    expect(keys).toHaveLength(1);
    expect(keys[0]!.slice(0, 2)).toEqual(['endgameOverview', 'stats']);
  });
});

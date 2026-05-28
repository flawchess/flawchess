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
      getOverview: vi.fn(),
    },
  };
});

import { endgameApi } from '@/api/client';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { useEndgameOverview } from '../useEndgames';

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useEndgameOverview', () => {
  beforeEach(() => {
    vi.mocked(endgameApi.getOverview).mockReset();
    vi.mocked(endgameApi.getOverview).mockResolvedValue({} as never);
  });

  // Quick 260529-015: while the endgame page is locked (tier2=false), the
  // overview must NOT fetch — a fetch during the locked phase caches a
  // pre-Stage-B response and the 5min staleTime then serves that stale cache
  // when the page reactively unlocks, so eval-dependent badges only appear
  // after a manual reload.
  it('does NOT fetch while disabled (page locked, tier2=false)', async () => {
    renderHook(() => useEndgameOverview(DEFAULT_FILTERS, { enabled: false }), {
      wrapper: makeWrapper(),
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(endgameApi.getOverview).not.toHaveBeenCalled();
  });

  it('fetches once enabled (page unlocked, tier2=true)', async () => {
    renderHook(() => useEndgameOverview(DEFAULT_FILTERS, { enabled: true }), {
      wrapper: makeWrapper(),
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(endgameApi.getOverview).toHaveBeenCalledTimes(1);
  });

  it('defaults to enabled when no options are passed', async () => {
    renderHook(() => useEndgameOverview(DEFAULT_FILTERS), { wrapper: makeWrapper() });

    await act(async () => {
      await Promise.resolve();
    });

    expect(endgameApi.getOverview).toHaveBeenCalledTimes(1);
  });

  it('fetches only after enabled flips false→true (the unlock transition)', async () => {
    const { rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) =>
        useEndgameOverview(DEFAULT_FILTERS, { enabled }),
      { wrapper: makeWrapper(), initialProps: { enabled: false } },
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(endgameApi.getOverview).not.toHaveBeenCalled();

    rerender({ enabled: true });
    await act(async () => {
      await Promise.resolve();
    });
    expect(endgameApi.getOverview).toHaveBeenCalledTimes(1);
  });
});

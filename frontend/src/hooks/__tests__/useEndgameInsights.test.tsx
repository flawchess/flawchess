// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useCachedEndgameInsights, useEndgameInsights } from '../useEndgameInsights';

// Mock apiClient.post / .get at the module level.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    apiClient: {
      post: vi.fn(),
      get: vi.fn(),
    },
  };
});

import { apiClient } from '@/api/client';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useEndgameInsights', () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
    vi.mocked(apiClient.get).mockReset();
  });

  it('POSTs to /insights/endgame with no query params (filter-free, D-04)', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        report: {
          overview: 'Overview text.',
          sections: [],
          model_used: 'anthropic:claude-haiku-4-5-20251001',
          prompt_version: 'endgame_v1',
        },
        status: 'fresh',
      },
    });

    const { result } = renderHook(() => useEndgameInsights(), { wrapper });
    await result.current.mutateAsync();

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    const call = vi.mocked(apiClient.post).mock.calls[0]!;
    // No body and no request config: nothing filter-shaped can reach the wire.
    expect(call).toEqual(['/insights/endgame']);
  });

  it('writes a successful Generate result into the cached-report query (FE-WR-01)', async () => {
    const generated = {
      report: {
        overview: 'Fresh overview.',
        sections: [],
        model_used: 'anthropic:claude-haiku-4-5-20251001',
        prompt_version: 'endgame_v48',
      },
      status: 'fresh',
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: generated });
    const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    // A remounted Stats tab reads this key; before the fix it kept the pre-Generate value.
    client.setQueryData(['endgame-insights', 'cached'], null);
    const localWrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useEndgameInsights(), { wrapper: localWrapper });
    await result.current.mutateAsync();

    expect(client.getQueryData(['endgame-insights', 'cached'])).toEqual(generated);
  });

  it('useCachedEndgameInsights returns the cached response on 200', async () => {
    const cached = {
      report: {
        overview: 'Overview text.',
        sections: [],
        model_used: 'anthropic:claude-haiku-4-5-20251001',
        prompt_version: 'endgame_v22',
      },
      status: 'cache_hit',
    };
    vi.mocked(apiClient.get).mockResolvedValue({ data: cached });

    const { result } = renderHook(() => useCachedEndgameInsights(), { wrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(cached);
    expect(apiClient.get).toHaveBeenCalledTimes(1);
    // The GET carries no query params either (D-04).
    expect(vi.mocked(apiClient.get).mock.calls[0]).toEqual(['/insights/endgame/cached']);
  });

  it('useCachedEndgameInsights uses one constant query key', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: null });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const keyedWrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useCachedEndgameInsights(), { wrapper: keyedWrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const keys = client.getQueryCache().getAll().map((q) => q.queryKey);
    expect(keys).toEqual([['endgame-insights', 'cached']]);
  });

  it('useCachedEndgameInsights returns null on 404 (no error)', async () => {
    const axios404 = Object.assign(new Error('404'), {
      isAxiosError: true,
      response: { status: 404, data: { detail: 'no_cached_report' } },
    });
    vi.mocked(apiClient.get).mockRejectedValue(axios404);

    const { result } = renderHook(() => useCachedEndgameInsights(), { wrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
  });

  it('surfaces AxiosError on mutation failure (502 provider_error)', async () => {
    const axiosError = Object.assign(new Error('502'), {
      isAxiosError: true,
      response: {
        status: 502,
        data: { error: 'provider_error' },
      },
    });
    vi.mocked(apiClient.post).mockRejectedValue(axiosError);

    const { result } = renderHook(() => useEndgameInsights(), { wrapper });
    await expect(result.current.mutateAsync()).rejects.toBe(axiosError);

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

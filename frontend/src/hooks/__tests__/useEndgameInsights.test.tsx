// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { FilterState } from '@/components/filters/FilterPanel';
import { useCachedEndgameInsights, useEndgameInsights } from '../useEndgameInsights';

// Mock apiClient.post / .get at the module level. Use importActual so
// buildFilterParams (real export) is preserved — the hooks import it
// alongside apiClient.
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

const BASE_FILTERS: FilterState = {
  matchSide: 'both',
  timeControls: ['blitz', 'rapid'],
  platforms: ['chess.com'],
  rated: true,
  opponentType: 'human',
  opponentStrength: { min: -50, max: 50 },
  recency: 'month',
  customRange: null,
  color: 'white',
};

describe('useEndgameInsights', () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
  });

  it('POSTs to /insights/endgame with serialized params', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        report: {
          overview: 'Overview text.',
          sections: [],
          model_used: 'anthropic:claude-haiku-4-5-20251001',
          prompt_version: 'endgame_v1',
        },
        status: 'fresh',
        stale_filters: null,
      },
    });

    const { result } = renderHook(() => useEndgameInsights(), { wrapper });
    await result.current.mutateAsync(BASE_FILTERS);

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    const call = vi.mocked(apiClient.post).mock.calls[0]!;
    const [url, body, config] = call;
    expect(url).toBe('/insights/endgame');
    expect(body).toBeNull();
    const params = (config as { params: Record<string, unknown> }).params;
    // Wire format uses from_date/to_date instead of recency preset.
    expect(params).toMatchObject({
      time_control: ['blitz', 'rapid'],
      platform: ['chess.com'],
      rated: true,
      opponent_gap_min: -50,
      opponent_gap_max: 50,
      color: 'white',
    });
    expect(params).not.toHaveProperty('recency');
    expect(params).toHaveProperty('from_date');
    expect(params).toHaveProperty('to_date');
  });

  it('does NOT pass opponent_type to insights endpoint (Pitfall 1)', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        report: { overview: '', sections: [], model_used: 'm', prompt_version: 'v' },
        status: 'fresh',
        stale_filters: null,
      },
    });

    const { result } = renderHook(() => useEndgameInsights(), { wrapper });
    // Non-default opponentType — would be passed through by buildFilterParams if we used opponent_type.
    await result.current.mutateAsync({ ...BASE_FILTERS, opponentType: 'computer' });

    const call = vi.mocked(apiClient.post).mock.calls[0]!;
    const [, , config] = call;
    const params = (config as { params: Record<string, unknown> }).params;
    expect(params).not.toHaveProperty('opponent_type');
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
      stale_filters: null,
    };
    vi.mocked(apiClient.get).mockResolvedValue({ data: cached });

    const { result } = renderHook(() => useCachedEndgameInsights(BASE_FILTERS), { wrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(cached);
    expect(apiClient.get).toHaveBeenCalledTimes(1);
    const [url, config] = vi.mocked(apiClient.get).mock.calls[0]!;
    expect(url).toBe('/insights/endgame/cached');
    const params = (config as { params: Record<string, unknown> }).params;
    // Wire format uses from_date/to_date instead of recency preset.
    expect(params).toMatchObject({
      time_control: ['blitz', 'rapid'],
      platform: ['chess.com'],
      rated: true,
      opponent_gap_min: -50,
      opponent_gap_max: 50,
      color: 'white',
    });
    expect(params).not.toHaveProperty('recency');
    expect(params).toHaveProperty('from_date');
    expect(params).toHaveProperty('to_date');
    expect(params).not.toHaveProperty('opponent_type');
  });

  it('useCachedEndgameInsights returns null on 404 (no error)', async () => {
    const axios404 = Object.assign(new Error('404'), {
      isAxiosError: true,
      response: { status: 404, data: { detail: 'no_cached_report' } },
    });
    vi.mocked(apiClient.get).mockRejectedValue(axios404);

    const { result } = renderHook(() => useCachedEndgameInsights(BASE_FILTERS), { wrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
  });

  it('surfaces AxiosError on mutation failure', async () => {
    const axiosError = Object.assign(new Error('429'), {
      isAxiosError: true,
      response: {
        status: 429,
        data: { error: 'rate_limit_exceeded', retry_after_seconds: 180 },
      },
    });
    vi.mocked(apiClient.post).mockRejectedValue(axiosError);

    const { result } = renderHook(() => useEndgameInsights(), { wrapper });
    await expect(result.current.mutateAsync(BASE_FILTERS)).rejects.toBe(axiosError);

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

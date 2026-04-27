// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    apiClient: { post: vi.fn() },
  };
});
import { apiClient } from '@/api/client';
import { useOpeningInsights } from '../useOpeningInsights';

const EMPTY_RESPONSE = {
  white_weaknesses: [],
  black_weaknesses: [],
  white_strengths: [],
  black_strengths: [],
};

function createWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useOpeningInsights', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: EMPTY_RESPONSE });
  });

  it('POSTs to /insights/openings with color: "all" regardless of input filter color (D-02)', async () => {
    renderHook(
      () =>
        useOpeningInsights({
          recency: 'year',
          timeControls: ['blitz', 'rapid'],
          platforms: ['chess.com'],
          rated: true,
          opponentType: 'human',
          opponentStrength: 'similar',
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalled();
    });

    const [url, body] = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0]!;
    expect(url).toBe('/insights/openings');
    expect(body).toMatchObject({
      color: 'all',
      recency: 'year',
      time_control: ['blitz', 'rapid'],
      platform: ['chess.com'],
      rated: true,
      opponent_type: 'human',
      opponent_strength: 'similar',
    });
  });

  it('normalizes recency: "all" to undefined/null in the body', async () => {
    renderHook(
      () =>
        useOpeningInsights({
          recency: 'all',
          timeControls: null,
          platforms: null,
          rated: null,
          opponentType: 'human',
          opponentStrength: 'any',
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalled();
    });

    const [, body] = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0]!;
    // recency 'all' must NOT propagate as 'all' (backend doesn't accept 'all' in this field directly via this hook's normalization)
    expect(body.recency).not.toBe('all');
  });

  it('refetches when filter input changes (query key reactivity)', async () => {
    const wrapper = createWrapper();
    const { rerender } = renderHook(
      ({ recency }: { recency: 'year' | 'month' }) =>
        useOpeningInsights({
          recency,
          timeControls: null,
          platforms: null,
          rated: null,
          opponentType: 'human',
          opponentStrength: 'any',
        }),
      { wrapper, initialProps: { recency: 'year' as const } },
    );

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledTimes(1);
    });

    rerender({ recency: 'month' });

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledTimes(2);
    });
  });

  it('returns the response data on the query result', async () => {
    const populated = {
      ...EMPTY_RESPONSE,
      white_weaknesses: [
        {
          color: 'white',
          classification: 'weakness',
          severity: 'major',
          opening_name: 'Test',
          opening_eco: 'A00',
          display_name: 'Test',
          entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
          entry_san_sequence: ['e4', 'c5', 'Nf3'],
          entry_full_hash: '123',
          candidate_move_san: 'd4',
          resulting_full_hash: '456',
          n_games: 25,
          wins: 5,
          draws: 5,
          losses: 15,
          win_rate: 0.20,
          loss_rate: 0.60,
          score: 0.30,
        },
      ],
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: populated });

    const { result } = renderHook(
      () =>
        useOpeningInsights({
          recency: null,
          timeControls: null,
          platforms: null,
          rated: null,
          opponentType: 'human',
          opponentStrength: 'any',
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.data).toEqual(populated);
    });
  });
});

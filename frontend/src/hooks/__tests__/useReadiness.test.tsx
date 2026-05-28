// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock apiClient at module level. Preserve other exports via importActual.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
    },
  };
});

import { apiClient } from '@/api/client';
import { useReadiness } from '../useReadiness';

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useReadiness', () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns safe default values (tier1=false, tier2=false) before first fetch resolves', async () => {
    // Never resolve the fetch — simulates loading state
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => undefined));

    const { result } = renderHook(() => useReadiness(), { wrapper: makeWrapper() });

    // Before fetch resolves: defaults must prevent content flash
    expect(result.current.tier1).toBe(false);
    expect(result.current.tier2).toBe(false);
    expect(result.current.pendingCount).toBe(0);
    expect(result.current.totalCount).toBe(0);
  });

  it('polls at 3s interval when tier2 is false', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { tier1: true, tier2: false, pending_count: 5, total_count: 10 },
    });

    renderHook(() => useReadiness(), { wrapper: makeWrapper() });

    // Flush the initial fetch (microtasks only — don't run refetch timers yet)
    await act(async () => {
      await Promise.resolve();
    });

    const callCountAfterFirst = vi.mocked(apiClient.get).mock.calls.length;
    expect(callCountAfterFirst).toBeGreaterThanOrEqual(1);

    // Advance 3s to trigger first poll, then flush its promise
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    await act(async () => {
      await Promise.resolve();
    });

    // Advance 3s to trigger second poll, then flush
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(vi.mocked(apiClient.get).mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  it('stops polling once tier2 is true', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { tier1: true, tier2: true, pending_count: 0, total_count: 10 },
    });

    renderHook(() => useReadiness(), { wrapper: makeWrapper() });

    // Flush the initial fetch
    await act(async () => {
      await Promise.resolve();
    });

    const callCountAfterFirst = vi.mocked(apiClient.get).mock.calls.length;
    expect(callCountAfterFirst).toBe(1);

    // Advance 30s — should NOT trigger more polls since tier2 is true
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(vi.mocked(apiClient.get).mock.calls.length).toBe(1);
  });

  it('maps response fields: pending_count → pendingCount, total_count → totalCount', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { tier1: true, tier2: false, pending_count: 7, total_count: 15 },
    });

    const { result } = renderHook(() => useReadiness(), { wrapper: makeWrapper() });

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.tier1).toBe(true);
    expect(result.current.tier2).toBe(false);
    expect(result.current.pendingCount).toBe(7);
    expect(result.current.totalCount).toBe(15);
  });
});

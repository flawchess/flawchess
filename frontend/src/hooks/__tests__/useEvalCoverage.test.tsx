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
import { useEvalCoverage } from '../useEvalCoverage';

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

describe('useEvalCoverage', () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('polls at interval when pending', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { pending_count: 5, total_count: 10, pct_complete: 50 },
    });

    renderHook(() => useEvalCoverage(), { wrapper: makeWrapper() });

    // Flush the initial fetch (microtasks only — don't run refetch timers yet)
    await act(async () => {
      await Promise.resolve();
    });

    const callCountAfterFirst = vi.mocked(apiClient.get).mock.calls.length;
    expect(callCountAfterFirst).toBeGreaterThanOrEqual(1);

    // Advance 10s to trigger first poll, then flush its promise
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    await act(async () => {
      await Promise.resolve();
    });

    // Advance 10s to trigger second poll, then flush its promise
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(vi.mocked(apiClient.get).mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  it('stops polling at 100% complete', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { pending_count: 0, total_count: 10, pct_complete: 100 },
    });

    renderHook(() => useEvalCoverage(), { wrapper: makeWrapper() });

    // Flush the initial fetch
    await act(async () => {
      await Promise.resolve();
    });

    const callCountAfterFirst = vi.mocked(apiClient.get).mock.calls.length;
    expect(callCountAfterFirst).toBe(1);

    // Advance 30s — should NOT trigger more polls since pct_complete === 100 AND total_count > 0
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(vi.mocked(apiClient.get).mock.calls.length).toBe(1);
  });

  it('keeps polling when total_count=0 (new user / pre-import lands on /import)', async () => {
    // Backend short-circuits to pct=100 when the user has no games. Without
    // continued polling, the header would never appear once an in-flight
    // import starts landing rows.
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { pending_count: 0, total_count: 0, pct_complete: 100 },
    });

    renderHook(() => useEvalCoverage(), { wrapper: makeWrapper() });

    await act(async () => {
      await Promise.resolve();
    });
    const callCountAfterFirst = vi.mocked(apiClient.get).mock.calls.length;
    expect(callCountAfterFirst).toBe(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(vi.mocked(apiClient.get).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it('returns safe default values before first fetch resolves', async () => {
    // Never resolve the fetch — simulates loading state
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => undefined));

    const { result } = renderHook(() => useEvalCoverage(), { wrapper: makeWrapper() });

    // Before fetch resolves: defaults must prevent flashing the caveat
    expect(result.current.pct).toBe(100);
    expect(result.current.isPending).toBe(false);
    expect(result.current.pendingCount).toBe(0);
    expect(result.current.totalCount).toBe(0);
  });
});

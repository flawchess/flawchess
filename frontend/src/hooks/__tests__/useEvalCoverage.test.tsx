// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach, afterAll } from 'vitest';
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

// Spy on window.location.reload to assert it is never called (Phase 96 Plan 03,
// Constraint 4 / SC-5: auto-reload has been removed from useEvalCoverage).
const reloadSpy = vi.fn();
const originalLocation = window.location;
beforeEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...originalLocation, reload: reloadSpy },
  });
});
afterAll(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: originalLocation,
  });
});

describe('useEvalCoverage', () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
    reloadSpy.mockReset();
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

  it('returns analyzedCount from the response (defaulting to 0 when absent)', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        pending_count: 2,
        total_count: 10,
        pct_complete: 80,
        analyzed_count: 7,
      },
    });

    const { result } = renderHook(() => useEvalCoverage(), { wrapper: makeWrapper() });

    // Flush the initial fetch via advanceTimersByTime(0) which flushes pending microtasks
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(result.current.analyzedCount).toBe(7);
    // inFlightCount is removed — verify it is no longer in the return value
    expect('inFlightCount' in result.current).toBe(false);
  });

  it('defaults analyzedCount to 0 when field is absent', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { pending_count: 0, total_count: 10, pct_complete: 100 },
    });

    const { result } = renderHook(() => useEvalCoverage(), { wrapper: makeWrapper() });

    // Before fetch resolves: defaults
    expect(result.current.analyzedCount).toBe(0);
  });

  it('does NOT call window.location.reload after a pending→done transition (Phase 96 Constraint 4)', async () => {
    // Simulate: first fetch returns pending=50%, then resolves to 100%.
    // Auto-reload was removed in Phase 96 Plan 03; reactive reveal via
    // useReadiness.tier2 replaces the forced full-page reload.
    let callCount = 0;
    vi.mocked(apiClient.get).mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({ data: { pending_count: 5, total_count: 10, pct_complete: 50 } });
      }
      return Promise.resolve({ data: { pending_count: 0, total_count: 10, pct_complete: 100 } });
    });

    renderHook(() => useEvalCoverage(), { wrapper: makeWrapper() });

    // Flush initial fetch (pending state)
    await act(async () => { await Promise.resolve(); });

    // Advance timer to trigger the poll that resolves to 100%
    await act(async () => { await vi.advanceTimersByTimeAsync(3_000); });
    await act(async () => { await Promise.resolve(); });

    expect(reloadSpy).not.toHaveBeenCalled();
  });

  // ── trackFullAnalysis: live background-progress counter ────────────────────

  it('trackFullAnalysis: keeps polling while analyzed_count < total_count and rising', async () => {
    // pct=100 (default would stop), but full analysis is incomplete and
    // the background drain keeps analyzing more games each poll → keep polling.
    let analyzed = 5;
    vi.mocked(apiClient.get).mockImplementation(() => {
      const data = {
        pending_count: 0,
        total_count: 10,
        pct_complete: 100,
        analyzed_count: analyzed,
      };
      analyzed += 1; // background drain makes progress every poll
      return Promise.resolve({ data });
    });

    renderHook(() => useEvalCoverage({ trackFullAnalysis: true }), { wrapper: makeWrapper() });

    await act(async () => {
      await Promise.resolve();
    });

    for (let i = 0; i < 3; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3_000);
      });
      await act(async () => {
        await Promise.resolve();
      });
    }

    expect(vi.mocked(apiClient.get).mock.calls.length).toBeGreaterThanOrEqual(4);
  });

  it('trackFullAnalysis: stops after the stall backstop when no new games analyze', async () => {
    // Incomplete (5 of 10) but the count never moves → a stuck game. Must back off
    // after the stall window instead of polling forever.
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        pending_count: 0,
        total_count: 10,
        pct_complete: 100,
        analyzed_count: 5,
      },
    });

    renderHook(() => useEvalCoverage({ trackFullAnalysis: true }), { wrapper: makeWrapper() });

    await act(async () => {
      await Promise.resolve();
    });

    // Advance well past the stall backstop (MAX_STALL_POLLS = 5).
    for (let i = 0; i < 8; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3_000);
      });
      await act(async () => {
        await Promise.resolve();
      });
    }
    const countAfterStall = vi.mocked(apiClient.get).mock.calls.length;
    expect(countAfterStall).toBeLessThanOrEqual(7); // 1 initial + ≤5 stall polls + slack

    // Further time advances must not poll again (polling has stopped).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(vi.mocked(apiClient.get).mock.calls.length).toBe(countAfterStall);
  });

  it('trackFullAnalysis: stops immediately when fully analyzed', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        pending_count: 0,
        total_count: 10,
        pct_complete: 100,
        analyzed_count: 10,
      },
    });

    renderHook(() => useEvalCoverage({ trackFullAnalysis: true }), { wrapper: makeWrapper() });

    await act(async () => {
      await Promise.resolve();
    });
    expect(vi.mocked(apiClient.get).mock.calls.length).toBe(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(vi.mocked(apiClient.get).mock.calls.length).toBe(1);
  });
});

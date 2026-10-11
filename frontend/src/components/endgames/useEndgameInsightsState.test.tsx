// @vitest-environment jsdom
/**
 * 238 UAT: the Stats tab auto-generates a missing insights report. One empty
 * cache result buys exactly one LLM call, even with the tab mounted twice
 * (desktop + mobile), and never while an import runs or without ranked games.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, renderHook } from '@testing-library/react';

const { mutateAsync, cacheState, jobsState } = vi.hoisted(() => ({
  mutateAsync: vi.fn(() => Promise.resolve()),
  cacheState: { isSuccess: true, data: null as unknown, dataUpdatedAt: 0 },
  jobsState: { data: [] as unknown[] },
}));

vi.mock('@/hooks/useEndgameInsights', () => ({
  useEndgameInsightsGenerating: () => false,
  useCachedEndgameInsights: () => cacheState,
  useEndgameInsights: () => ({ mutateAsync, isPending: false, isError: false }),
}));

vi.mock('@/hooks/useImport', () => ({
  useActiveJobs: () => jobsState,
}));

import { useEndgameInsightsState } from './useEndgameInsightsState';

// The once-per-fetch guard is module-level, so every test uses a fresh fetch time.
let fetchTime = 1000;

beforeEach(() => {
  mutateAsync.mockClear();
  fetchTime += 1;
  cacheState.isSuccess = true;
  cacheState.data = null;
  cacheState.dataUpdatedAt = fetchTime;
  jobsState.data = [];
});

afterEach(() => {
  cleanup();
});

describe('useEndgameInsightsState auto-generate', () => {
  it('generates once for an empty cache, even with two mounted instances', () => {
    renderHook(() => useEndgameInsightsState({ autoGenerate: true }));
    renderHook(() => useEndgameInsightsState({ autoGenerate: true }));
    expect(mutateAsync).toHaveBeenCalledTimes(1);
  });

  it('does not generate again on remount for the same cache result', () => {
    const first = renderHook(() => useEndgameInsightsState({ autoGenerate: true }));
    first.unmount();
    renderHook(() => useEndgameInsightsState({ autoGenerate: true }));
    expect(mutateAsync).toHaveBeenCalledTimes(1);
  });

  it('does not generate when a cached report exists', () => {
    cacheState.data = { report: { sections: [] }, status: 'cache_hit' };
    renderHook(() => useEndgameInsightsState({ autoGenerate: true }));
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('does not generate while an import runs or without ranked games', () => {
    jobsState.data = [{ job_id: 'j1' }];
    renderHook(() => useEndgameInsightsState({ autoGenerate: true }));
    jobsState.data = [];
    renderHook(() => useEndgameInsightsState({ autoGenerate: false }));
    expect(mutateAsync).not.toHaveBeenCalled();
  });
});

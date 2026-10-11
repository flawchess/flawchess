// @vitest-environment jsdom
/**
 * Phase 238 D-12 / D-13 / D-14: default TC, localStorage persistence and the
 * shared (synced) selection store. The store is module-level state, so each
 * test loads a fresh copy of the module.
 */

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { buildRankedTc } from '@/components/endgames/stats/rankedFixtures';
import type { RankedTcStats } from '@/types/endgames';

type StoreModule = typeof import('../useEndgameStatsTc');

let store: StoreModule;

beforeEach(async () => {
  vi.resetModules();
  localStorage.clear();
  store = await import('../useEndgameStatsTc');
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('pickDefaultTc (D-12)', () => {
  it('picks the TC with the most ranked games', () => {
    const tcs = [
      buildRankedTc('blitz', { ranked_games: 180 }),
      buildRankedTc('rapid', { ranked_games: 871 }),
    ];
    expect(store.pickDefaultTc(tcs)).toBe('rapid');
  });

  it('breaks ties toward the faster TC', () => {
    const tcs = [
      buildRankedTc('rapid', { ranked_games: 200 }),
      buildRankedTc('blitz', { ranked_games: 200 }),
      buildRankedTc('classical', { ranked_games: 200 }),
    ];
    expect(store.pickDefaultTc(tcs)).toBe('blitz');
  });

  it('prefers an above-floor TC over a bigger below-floor TC', () => {
    const tcs = [
      buildRankedTc('bullet', { ranked_games: 500, anchor_games: 18, anchor_min_games: 30 }),
      buildRankedTc('rapid', { ranked_games: 60, anchor_games: 55, anchor_min_games: 30 }),
    ];
    expect(store.pickDefaultTc(tcs)).toBe('rapid');
  });

  it('falls back to any TC when none is above the floor', () => {
    const tcs = [
      buildRankedTc('bullet', { ranked_games: 10, anchor_games: 10, anchor_min_games: 30 }),
      buildRankedTc('blitz', { ranked_games: 25, anchor_games: 25, anchor_min_games: 30 }),
    ];
    expect(store.pickDefaultTc(tcs)).toBe('blitz');
  });

  it('returns null for an empty ranked sample', () => {
    expect(store.pickDefaultTc([])).toBeNull();
  });
});

describe('useEndgameStatsTc (D-13, D-14)', () => {
  const tcs: RankedTcStats[] = [
    buildRankedTc('blitz', { ranked_games: 180 }),
    buildRankedTc('rapid', { ranked_games: 871 }),
  ];

  it('defaults to the D-12 TC when nothing is stored', () => {
    const { result } = renderHook(() => store.useEndgameStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('restores a stored TC that still has ranked games', () => {
    localStorage.setItem(store.ENDGAME_STATS_TC_STORAGE_KEY, 'blitz');
    const { result } = renderHook(() => store.useEndgameStatsTc(tcs));
    expect(result.current[0]).toBe('blitz');
  });

  it('ignores a stored TC that is absent from the payload', () => {
    localStorage.setItem(store.ENDGAME_STATS_TC_STORAGE_KEY, 'bullet');
    const { result } = renderHook(() => store.useEndgameStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('ignores a corrupt stored value', () => {
    localStorage.setItem(store.ENDGAME_STATS_TC_STORAGE_KEY, 'not-a-tc');
    const { result } = renderHook(() => store.useEndgameStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('still renders the default when localStorage.getItem throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable');
    });
    const { result } = renderHook(() => store.useEndgameStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('keeps the in-session choice when localStorage.setItem throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });
    const { result } = renderHook(() => store.useEndgameStatsTc(tcs));
    act(() => result.current[1]('blitz'));
    expect(result.current[0]).toBe('blitz');
  });

  it('persists the choice to localStorage', () => {
    const { result } = renderHook(() => store.useEndgameStatsTc(tcs));
    act(() => result.current[1]('blitz'));
    expect(localStorage.getItem(store.ENDGAME_STATS_TC_STORAGE_KEY)).toBe('blitz');
  });

  it('keeps the un-chosen default when a refetch makes another TC the leader (FE-IN-05)', () => {
    const { result, rerender } = renderHook(({ list }) => store.useEndgameStatsTc(list), {
      initialProps: { list: tcs },
    });
    expect(result.current[0]).toBe('rapid');
    const afterImport = [
      buildRankedTc('blitz', { ranked_games: 1200 }),
      buildRankedTc('rapid', { ranked_games: 880 }),
    ];
    rerender({ list: afterImport });
    expect(result.current[0]).toBe('rapid');
    // Recomputed once the pinned TC leaves the payload.
    rerender({ list: [buildRankedTc('blitz', { ranked_games: 1200 })] });
    expect(result.current[0]).toBe('blitz');
  });

  it('keeps two hook instances in sync after one setter call', () => {
    const first = renderHook(() => store.useEndgameStatsTc(tcs));
    const second = renderHook(() => store.useEndgameStatsTc(tcs));
    expect(first.result.current[0]).toBe('rapid');
    expect(second.result.current[0]).toBe('rapid');
    act(() => first.result.current[1]('blitz'));
    expect(first.result.current[0]).toBe('blitz');
    expect(second.result.current[0]).toBe('blitz');
  });
});

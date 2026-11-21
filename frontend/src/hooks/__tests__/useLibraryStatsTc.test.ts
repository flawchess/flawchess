// @vitest-environment jsdom
/**
 * The Library default TC, its own localStorage key and the shared
 * (synced) selection store. The store is module-level state, so each test loads a fresh
 * copy of both hook modules (the dynamic imports live in beforeEach, never in a test body).
 */

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { buildRankedTc } from '@/components/endgames/stats/rankedFixtures';
import type { TimeControlBucket } from '@/types/endgames';
import type { LibraryTcCount } from '../useLibraryStatsTc';

type LibraryModule = typeof import('../useLibraryStatsTc');
type EndgameModule = typeof import('../useEndgameStatsTc');

let library: LibraryModule;
let endgame: EndgameModule;

beforeEach(async () => {
  vi.resetModules();
  localStorage.clear();
  library = await import('../useLibraryStatsTc');
  endgame = await import('../useEndgameStatsTc');
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

function lib(
  tc: TimeControlBucket,
  analyzed_n: number,
  below_gate = false,
  total_n?: number,
  history_analyzed_n?: number,
): LibraryTcCount {
  return { tc, analyzed_n, below_gate, total_n, history_analyzed_n };
}

/** A TC with games in the filters but none in the recent window (258 D-15). */
function quiet(tc: TimeControlBucket, history_analyzed_n: number): LibraryTcCount {
  return lib(tc, 0, true, 0, history_analyzed_n);
}

describe('pickDefaultLibraryTc', () => {
  it('picks the TC with the most analyzed games', () => {
    expect(library.pickDefaultLibraryTc([lib('blitz', 180), lib('rapid', 871)])).toBe('rapid');
  });

  it('breaks ties toward the faster TC', () => {
    const tcs = [lib('rapid', 200), lib('blitz', 200), lib('classical', 200)];
    expect(library.pickDefaultLibraryTc(tcs)).toBe('blitz');
  });

  it('prefers an at-or-above-gate TC over a bigger below-gate TC', () => {
    const tcs = [lib('bullet', 19, true), lib('rapid', 20)];
    expect(library.pickDefaultLibraryTc(tcs)).toBe('rapid');
  });

  it('falls back to all TCs when every TC is below the gate', () => {
    const tcs = [lib('bullet', 5, true), lib('blitz', 12, true)];
    expect(library.pickDefaultLibraryTc(tcs)).toBe('blitz');
  });

  it('returns null for an empty list', () => {
    expect(library.pickDefaultLibraryTc([])).toBeNull();
  });

  it('picks the quiet TC with the most history when every TC is quiet', () => {
    expect(library.pickDefaultLibraryTc([quiet('blitz', 300), quiet('rapid', 900)])).toBe('rapid');
  });

  it('breaks an all-quiet history tie toward the faster TC', () => {
    expect(library.pickDefaultLibraryTc([quiet('rapid', 300), quiet('blitz', 300)])).toBe('blitz');
  });

  it('never picks a quiet TC over a TC with recent games, however large its history', () => {
    const tcs = [quiet('blitz', 5000), lib('rapid', 3, true, 4, 3)];
    expect(library.pickDefaultLibraryTc(tcs)).toBe('rapid');
  });

  it('keeps today\'s ranking for entries without total_n', () => {
    expect(library.pickDefaultLibraryTc([lib('blitz', 180), lib('rapid', 871)])).toBe('rapid');
  });
});

describe('useLibraryStatsTc', () => {
  const tcs: LibraryTcCount[] = [lib('blitz', 180), lib('rapid', 871)];

  it('uses its own storage key', () => {
    expect(library.LIBRARY_STATS_TC_STORAGE_KEY).toBe('library_stats_tc');
    expect(library.LIBRARY_STATS_TC_STORAGE_KEY).not.toBe(endgame.ENDGAME_STATS_TC_STORAGE_KEY);
  });

  it('defaults to the most-analyzed TC when nothing is stored', () => {
    const { result } = renderHook(() => library.useLibraryStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('restores a stored TC that is offered', () => {
    localStorage.setItem(library.LIBRARY_STATS_TC_STORAGE_KEY, 'blitz');
    const { result } = renderHook(() => library.useLibraryStatsTc(tcs));
    expect(result.current[0]).toBe('blitz');
  });

  it('keeps a remembered quiet TC selected while it is offered', () => {
    localStorage.setItem(library.LIBRARY_STATS_TC_STORAGE_KEY, 'blitz');
    const withQuiet = [quiet('blitz', 300), lib('rapid', 871)];
    const { result } = renderHook(() => library.useLibraryStatsTc(withQuiet));
    expect(result.current[0]).toBe('blitz');
  });

  it('defaults to the TC with recent games when another TC is quiet', () => {
    const withQuiet = [quiet('blitz', 5000), lib('rapid', 871)];
    const { result } = renderHook(() => library.useLibraryStatsTc(withQuiet));
    expect(result.current[0]).toBe('rapid');
  });

  it('drops a pinned default that turned quiet when cached filters come back', () => {
    // All time: blitz is quiet, rapid has recent games. Then a Recency period (new query
    // key, empty list, blitz leads). Then back to the cached All-time list.
    const allTime = [quiet('blitz', 5000), lib('rapid', 871)];
    const fiveYears = [lib('blitz', 900), lib('rapid', 871)];
    const loading: LibraryTcCount[] = [];
    const { result, rerender } = renderHook(
      ({ list }: { list: LibraryTcCount[] }) => library.useLibraryStatsTc(list),
      { initialProps: { list: allTime } },
    );
    expect(result.current[0]).toBe('rapid');
    rerender({ list: loading });
    rerender({ list: fiveYears });
    expect(result.current[0]).toBe('blitz');
    rerender({ list: allTime });
    expect(result.current[0]).toBe('rapid');
  });

  it('keeps a pinned quiet default when every TC is quiet', () => {
    const allQuiet = [quiet('blitz', 300), quiet('rapid', 900)];
    const { result, rerender } = renderHook(
      ({ list }: { list: LibraryTcCount[] }) => library.useLibraryStatsTc(list),
      { initialProps: { list: allQuiet } },
    );
    expect(result.current[0]).toBe('rapid');
    rerender({ list: [quiet('blitz', 2000), quiet('rapid', 900)] });
    expect(result.current[0]).toBe('rapid');
  });

  it('ignores a stored TC that is not offered', () => {
    localStorage.setItem(library.LIBRARY_STATS_TC_STORAGE_KEY, 'bullet');
    const { result } = renderHook(() => library.useLibraryStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('ignores a tampered stored value', () => {
    localStorage.setItem(library.LIBRARY_STATS_TC_STORAGE_KEY, '<script>');
    const { result } = renderHook(() => library.useLibraryStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('still renders the default when localStorage.getItem throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable');
    });
    const { result } = renderHook(() => library.useLibraryStatsTc(tcs));
    expect(result.current[0]).toBe('rapid');
  });

  it('keeps the in-session choice when localStorage.setItem throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded');
    });
    const { result } = renderHook(() => library.useLibraryStatsTc(tcs));
    act(() => result.current[1]('blitz'));
    expect(result.current[0]).toBe('blitz');
  });

  it('persists the choice under library_stats_tc and leaves endgame_stats_tc untouched', () => {
    const { result } = renderHook(() => library.useLibraryStatsTc(tcs));
    act(() => result.current[1]('blitz'));
    expect(localStorage.getItem('library_stats_tc')).toBe('blitz');
    expect(localStorage.getItem('endgame_stats_tc')).toBeNull();
  });

  it('persists an Endgame choice under endgame_stats_tc and leaves library_stats_tc untouched', () => {
    const endgameTcs = [
      buildRankedTc('blitz', { ranked_games: 180 }),
      buildRankedTc('rapid', { ranked_games: 871 }),
    ];
    const { result } = renderHook(() => endgame.useEndgameStatsTc(endgameTcs));
    act(() => result.current[1]('blitz'));
    expect(localStorage.getItem('endgame_stats_tc')).toBe('blitz');
    expect(localStorage.getItem('library_stats_tc')).toBeNull();
  });

  it('does not let a Library choice change the Endgame selection in memory', () => {
    const endgameTcs = [
      buildRankedTc('blitz', { ranked_games: 180 }),
      buildRankedTc('rapid', { ranked_games: 871 }),
    ];
    const libraryHook = renderHook(() => library.useLibraryStatsTc(tcs));
    const endgameHook = renderHook(() => endgame.useEndgameStatsTc(endgameTcs));
    act(() => libraryHook.result.current[1]('blitz'));
    expect(libraryHook.result.current[0]).toBe('blitz');
    expect(endgameHook.result.current[0]).toBe('rapid');
  });

  it('keeps the un-chosen default when a refetch makes another TC the leader', () => {
    const { result, rerender } = renderHook(({ list }) => library.useLibraryStatsTc(list), {
      initialProps: { list: tcs },
    });
    expect(result.current[0]).toBe('rapid');
    rerender({ list: [lib('blitz', 1200), lib('rapid', 880)] });
    expect(result.current[0]).toBe('rapid');
    // Recomputed once the pinned TC leaves the offered list.
    rerender({ list: [lib('blitz', 1200)] });
    expect(result.current[0]).toBe('blitz');
  });

  it('keeps two hook instances in sync after one setter call', () => {
    const first = renderHook(() => library.useLibraryStatsTc(tcs));
    const second = renderHook(() => library.useLibraryStatsTc(tcs));
    act(() => first.result.current[1]('blitz'));
    expect(first.result.current[0]).toBe('blitz');
    expect(second.result.current[0]).toBe('blitz');
  });
});

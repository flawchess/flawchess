// @vitest-environment jsdom
/**
 * useStockfishGradingEngine mock-Worker unit tests.
 *
 * Mirrors useStockfishEngine.test.ts's MockWorker harness (no real WASM — that
 * is Plan 01's spike + Plan 04's SC3 HUMAN-UAT). Behaviors verified:
 * 1. Init: uci -> uciok -> isready -> readyok -> isReady false->true.
 * 2. Search command: setoption name MultiPV value <N> + go depth 14
 *    searchmoves <ucis> movetime 2500 for a settled (fen, candidateSans).
 * 3. pv[0] keying: two info lines report the SAME multipv index but
 *    DIFFERENT pv[0] moves — both must appear as distinct grade-map keys
 *    (Pitfall 1 — never key by multipv index).
 * 4. White-POV normalization: a black-to-move FEN's `score cp` info line is
 *    negated in the committed grade.
 * 5. Cache short-circuit (Pitfall 2): re-rendering with an already-graded
 *    subset of the same FEN's candidates sends NO new go.
 * 6. Stale-guard (FLAWCHESS-7V): a new FEN while thinking sends stop and
 *    defers the re-go until the stale bestmove arrives.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStockfishGradingEngine } from '../useStockfishGradingEngine';

// ─── Mock Worker ─────────────────────────────────────────────────────────────

class MockWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  messages: string[] = [];
  terminated = false;

  postMessage(msg: string): void {
    this.messages.push(msg);
  }

  terminate(): void {
    this.terminated = true;
  }

  /** Fire the onmessage handler with a synthetic UCI line. */
  simulateMessage(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

let mockWorker: MockWorker;

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Drive the mock engine through the full UCI init sequence (uciok -> readyok). */
function driveInit(worker: MockWorker): void {
  act(() => {
    worker.simulateMessage('uciok');
  });
  act(() => {
    worker.simulateMessage('readyok');
  });
}

// Black-to-move FENs after a single white opening move — e5/c5/e6 (single-
// token SAN, unambiguous) remain legal black replies in all three.
const TEST_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'; // 1. e4
const TEST_FEN_2 = 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1'; // 1. d4

const CANDIDATES = ['e5', 'c5', 'e6'];

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('useStockfishGradingEngine', () => {
  beforeEach(() => {
    // Deterministic fake clock — mirrors useStockfishEngine.test.ts's setup.
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    // Use a regular function (not arrow) so `new Worker(url)` works.
    vi.stubGlobal('Worker', vi.fn(function () { return mockWorker; }));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('creates a classic Worker — no module option — as a SEPARATE instance from the primary engine path', () => {
    renderHook(() =>
      useStockfishGradingEngine({ fen: null, candidateSans: [], enabled: true }),
    );
    const WorkerCtor = vi.mocked(globalThis.Worker as new (url: string) => Worker);
    expect(WorkerCtor).toHaveBeenCalledWith('/engine/stockfish-18-lite-single.js');
    expect(WorkerCtor).toHaveBeenCalledTimes(1);
  });

  it('sends uci as the first command on mount', () => {
    renderHook(() =>
      useStockfishGradingEngine({ fen: null, candidateSans: [], enabled: true }),
    );
    expect(mockWorker.messages[0]).toBe('uci');
  });

  it('init: uciok -> isready -> readyok flips isReady false->true (no setoption at init)', () => {
    const { result } = renderHook(() =>
      useStockfishGradingEngine({ fen: null, candidateSans: [], enabled: true }),
    );
    expect(result.current.isReady).toBe(false);

    act(() => {
      mockWorker.simulateMessage('uciok');
    });
    // MultiPV is set dynamically PER SEARCH (candidate count varies), not once
    // at init — the init sequence sends isready directly.
    expect(mockWorker.messages).toContain('isready');
    expect(mockWorker.messages.some((m) => m.startsWith('setoption'))).toBe(false);

    act(() => {
      mockWorker.simulateMessage('readyok');
    });
    expect(result.current.isReady).toBe(true);
  });

  it('search command: setoption MultiPV value 3 + go depth 14 searchmoves <3 ucis> movetime 2500', async () => {
    renderHook(() =>
      useStockfishGradingEngine({ fen: TEST_FEN, candidateSans: CANDIDATES, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200); // past RAPID_STEP_DEBOUNCE_MS
    });

    expect(mockWorker.messages).toContain('setoption name MultiPV value 3');
    expect(mockWorker.messages).toContain(`position fen ${TEST_FEN}`);

    const goCmd = mockWorker.messages.find((m) => m.startsWith('go '));
    expect(goCmd).toBeDefined();
    expect(goCmd).toContain('depth 14');
    expect(goCmd).toContain('movetime 2500');
    // Candidate SANs converted to UCI in order (e5->e7e5, c5->c7c5, e6->e7e6).
    expect(goCmd).toContain('searchmoves e7e5 c7c5 e7e6');
  });

  it('pv[0] keying: same multipv index reporting DIFFERENT pv[0] moves produces distinct grade-map keys', async () => {
    const { result } = renderHook(() =>
      useStockfishGradingEngine({ fen: TEST_FEN, candidateSans: CANDIDATES, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Confirmed-on-the-real-binary reordering scenario (151.1-01-SUMMARY.md
    // Caveat 2): multipv 1 first reports e5 at a shallow depth, then later
    // reports a DIFFERENT move (c5) at a deeper depth — as would happen when
    // the restricted search's eval ranking reorders as depth climbs.
    act(() => {
      mockWorker.simulateMessage(
        'info depth 8 multipv 1 score cp -20 nodes 1000 pv e7e5',
      );
    });
    act(() => {
      mockWorker.simulateMessage(
        'info depth 10 multipv 1 score cp -15 nodes 2000 pv c7c5',
      );
    });

    // Both moves must appear as their OWN key — pv[0] identity, not multipv
    // index, which would have collapsed both updates onto one entry.
    expect(result.current.gradeMap.has('e5')).toBe(true);
    expect(result.current.gradeMap.has('c5')).toBe(true);
    expect(result.current.gradeMap.get('e5')?.depth).toBe(8);
    expect(result.current.gradeMap.get('c5')?.depth).toBe(10);
  });

  it('white-POV normalization: black-to-move FEN negates a positive (mover-POV) score cp', async () => {
    const { result } = renderHook(() =>
      useStockfishGradingEngine({ fen: TEST_FEN, candidateSans: CANDIDATES, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // TEST_FEN is black-to-move: UCI score cp 50 (mover=black POV, favors
    // black) must be negated to white-POV = -50.
    act(() => {
      mockWorker.simulateMessage(
        'info depth 10 multipv 1 score cp 50 nodes 1000 pv e7e5',
      );
    });

    expect(result.current.gradeMap.get('e5')?.evalCp).toBe(-50);
  });

  it('cache short-circuit: re-rendering with an already-graded subset sends NO new go', async () => {
    const { rerender, result } = renderHook(
      ({ candidateSans }: { candidateSans: string[] }) =>
        useStockfishGradingEngine({ fen: TEST_FEN, candidateSans, enabled: true }),
      { initialProps: { candidateSans: CANDIDATES } },
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);

    // Grade all 3 candidates, then settle the search with bestmove so the
    // engine returns to 'idle' (a genuinely completed grading pass).
    act(() => {
      mockWorker.simulateMessage('info depth 14 multipv 1 score cp -10 nodes 1000 pv e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 14 multipv 2 score cp -20 nodes 1000 pv c7c5');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 14 multipv 3 score cp -30 nodes 1000 pv e7e6');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e7e5');
    });

    // Re-render with a SUBSET of the same candidates for the SAME fen (the
    // ELO-slider-drag case) — every requested SAN is already cached.
    rerender({ candidateSans: ['e5', 'c5'] });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Still exactly 1 go command — the subset was served entirely from cache.
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);
    // The displayed gradeMap reflects only the requested subset.
    expect([...result.current.gradeMap.keys()].sort()).toEqual(['c5', 'e5']);
  });

  it('stale-guard: a new FEN while thinking sends stop; deferred re-go fires only after the stale bestmove', async () => {
    const { rerender } = renderHook(
      ({ fen }: { fen: string }) =>
        useStockfishGradingEngine({ fen, candidateSans: CANDIDATES, enabled: true }),
      { initialProps: { fen: TEST_FEN } },
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // First search in flight for TEST_FEN.
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);

    // New FEN while thinking.
    rerender({ fen: TEST_FEN_2 });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(mockWorker.messages).toContain('stop');
    // No new go yet — the stale-guard defers until the stale bestmove arrives.
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);
    expect(mockWorker.messages).not.toContain(`position fen ${TEST_FEN_2}`);

    // The stale bestmove (from the TEST_FEN search) arrives — discarded, then
    // triggers the deferred re-go for the LATEST fen (TEST_FEN_2).
    act(() => {
      mockWorker.simulateMessage('bestmove e7e5');
    });

    expect(mockWorker.messages).toContain(`position fen ${TEST_FEN_2}`);
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(2);
  });

  it('unmount sends stop and terminates the Worker (no leak)', () => {
    const { unmount } = renderHook(() =>
      useStockfishGradingEngine({ fen: null, candidateSans: [], enabled: true }),
    );

    unmount();

    expect(mockWorker.messages).toContain('stop');
    expect(mockWorker.terminated).toBe(true);
  });

  it('visibility hidden sends stop without terminating the Worker (while a search is in flight)', async () => {
    renderHook(() =>
      useStockfishGradingEngine({ fen: TEST_FEN, candidateSans: CANDIDATES, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    const stopsBefore = mockWorker.messages.filter((m) => m === 'stop').length;

    act(() => {
      Object.defineProperty(document, 'visibilityState', {
        value: 'hidden',
        configurable: true,
        writable: true,
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });

    const stopsAfter = mockWorker.messages.filter((m) => m === 'stop').length;
    expect(stopsAfter).toBeGreaterThan(stopsBefore);
    expect(mockWorker.terminated).toBe(false);
  });
});

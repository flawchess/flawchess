// @vitest-environment jsdom
/**
 * useStockfishEngine mock-Worker unit tests.
 *
 * Behaviors verified:
 * 1. Classic Worker instantiation (no { type: 'module' }).
 * 2. UCI init: uci → setoption MultiPV value 2 → isready → isReady false→true.
 * 3. Debounce: FEN sent only after DEBOUNCE_MS.
 * 4. Search command contains movetime 1500 and nodes 2000000.
 * 5. Stop-pending discard: stale bestmove is discarded; only final FEN result committed.
 * 6. lowerbound/upperbound lines do NOT update evalCp (Pitfall 5).
 * 7. Exact info line + bestmove commits evalCp to state.
 * 8. Visibility hidden → stop sent, worker NOT terminated.
 * 9. Unmount → stop + terminate.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStockfishEngine } from '../useStockfishEngine';

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

/** Drive the mock engine through the full UCI init sequence (uciok → readyok). */
function driveInit(worker: MockWorker): void {
  act(() => {
    worker.simulateMessage('uciok');
  });
  act(() => {
    worker.simulateMessage('readyok');
  });
}

const TEST_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
const TEST_FEN_2 = 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1';

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('useStockfishEngine', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockWorker = new MockWorker();
    // Use a regular function (not arrow) so `new Worker(url)` works.
    // A constructor that returns a plain object has that object override `this`.
    vi.stubGlobal('Worker', vi.fn(function () { return mockWorker; }));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('creates a classic Worker — no module option', () => {
    renderHook(() => useStockfishEngine({ fen: null, enabled: true }));
    // The Worker constructor must be called with only the engine path.
    // A second argument ({ type: 'module' }) would break the Emscripten glue.
    const WorkerCtor = vi.mocked(globalThis.Worker as new (url: string) => Worker);
    expect(WorkerCtor).toHaveBeenCalledWith('/engine/stockfish-18-lite-single.js');
    expect(WorkerCtor).toHaveBeenCalledTimes(1);
  });

  it('sends uci as the first command on mount', () => {
    renderHook(() => useStockfishEngine({ fen: null, enabled: true }));
    expect(mockWorker.messages[0]).toBe('uci');
  });

  it('setoption MultiPV uses value 2', () => {
    renderHook(() => useStockfishEngine({ fen: null, enabled: true }));
    act(() => {
      mockWorker.simulateMessage('uciok');
    });
    expect(mockWorker.messages).toContain('setoption name MultiPV value 2');
  });

  it('sends isready after setoption and transitions isReady false→true on readyok', () => {
    const { result } = renderHook(() =>
      useStockfishEngine({ fen: null, enabled: true }),
    );
    expect(result.current.isReady).toBe(false);

    act(() => {
      mockWorker.simulateMessage('uciok');
    });
    expect(mockWorker.messages).toContain('isready');

    act(() => {
      mockWorker.simulateMessage('readyok');
    });
    expect(result.current.isReady).toBe(true);
  });

  it('does not send go before the debounce delay (150 ms)', async () => {
    renderHook(() => useStockfishEngine({ fen: TEST_FEN, enabled: true }));
    driveInit(mockWorker);

    // Just before debounce fires
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(mockWorker.messages.some((m) => m.startsWith('go '))).toBe(false);
  });

  it('sends position + go after the debounce delay', async () => {
    const { result } = renderHook(() =>
      useStockfishEngine({ fen: TEST_FEN, enabled: true }),
    );
    driveInit(mockWorker);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200); // past 150 ms
    });

    expect(mockWorker.messages).toContain(`position fen ${TEST_FEN}`);
    expect(mockWorker.messages.some((m) => m.startsWith('go '))).toBe(true);
    expect(result.current.isAnalyzing).toBe(true);
  });

  it('search command contains movetime 1500 and nodes 2000000', async () => {
    renderHook(() => useStockfishEngine({ fen: TEST_FEN, enabled: true }));
    driveInit(mockWorker);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    const goCmd = mockWorker.messages.find((m) => m.startsWith('go '));
    expect(goCmd).toBeDefined();
    expect(goCmd).toContain('movetime 1500');
    expect(goCmd).toContain('nodes 2000000');
  });

  it('lowerbound info line does NOT update evalCp (Pitfall 5)', async () => {
    const { result } = renderHook(() =>
      useStockfishEngine({ fen: TEST_FEN, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    act(() => {
      mockWorker.simulateMessage(
        'info depth 12 multipv 1 score cp 45 lowerbound nodes 12000 pv e2e4 e7e5',
      );
    });

    expect(result.current.evalCp).toBeNull();
  });

  it('upperbound info line does NOT update evalCp (Pitfall 5)', async () => {
    const { result } = renderHook(() =>
      useStockfishEngine({ fen: TEST_FEN, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    act(() => {
      mockWorker.simulateMessage(
        'info depth 12 multipv 1 score cp 60 upperbound nodes 14000 pv d2d4 d7d5',
      );
    });

    expect(result.current.evalCp).toBeNull();
  });

  it('exact info line + bestmove commits evalCp to state', async () => {
    const { result } = renderHook(() =>
      useStockfishEngine({ fen: TEST_FEN, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    act(() => {
      mockWorker.simulateMessage(
        'info depth 14 multipv 1 score cp 52 nodes 30000 pv e2e4 e7e5 g1f3',
      );
      mockWorker.simulateMessage('bestmove e2e4 ponder e7e5');
    });

    expect(result.current.evalCp).toBe(52);
    expect(result.current.isAnalyzing).toBe(false);
  });

  it('stop-pending bestmove is discarded — rapid FEN changes show only final result', async () => {
    const { rerender, result } = renderHook(
      ({ fen }: { fen: string }) =>
        useStockfishEngine({ fen, enabled: true }),
      { initialProps: { fen: TEST_FEN } },
    );

    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Engine is analyzing TEST_FEN
    expect(result.current.isAnalyzing).toBe(true);

    // Receive an exact info line for TEST_FEN (would be committed on normal bestmove)
    act(() => {
      mockWorker.simulateMessage(
        'info depth 14 multipv 1 score cp 52 nodes 30000 pv e2e4 e7e5',
      );
    });

    // Change FEN while thinking — hook must send stop
    rerender({ fen: TEST_FEN_2 });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200); // debounce fires for TEST_FEN_2
    });

    expect(mockWorker.messages).toContain('stop');

    // Stale bestmove arrives (from TEST_FEN search) — must be DISCARDED
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4 ponder e7e5');
    });

    // pvLines must remain empty — the TEST_FEN result was discarded
    expect(result.current.pvLines).toHaveLength(0);
    // evalCp must still be null (stale result not committed)
    expect(result.current.evalCp).toBeNull();
  });

  it('visibility hidden sends stop without terminating the Worker', async () => {
    renderHook(() => useStockfishEngine({ fen: TEST_FEN, enabled: true }));
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Engine is now analyzing (stateRef === 'thinking')
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

  it('unmount sends stop and terminates the Worker (no leak)', () => {
    const { unmount } = renderHook(() =>
      useStockfishEngine({ fen: null, enabled: true }),
    );

    unmount();

    expect(mockWorker.messages).toContain('stop');
    expect(mockWorker.terminated).toBe(true);
  });
});

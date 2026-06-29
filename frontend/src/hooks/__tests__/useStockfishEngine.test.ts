// @vitest-environment jsdom
/**
 * useStockfishEngine mock-Worker unit tests.
 *
 * Behaviors verified:
 * 1. Classic Worker instantiation (no { type: 'module' }).
 * 2. UCI init: uci → setoption MultiPV value 2 → isready → isReady false→true.
 * 3. Adaptive debounce: settled move fires immediately; rapid steps coalesce.
 * 4. Search command contains movetime 1500 and nodes 2000000.
 * 5. Stop-pending discard: stale bestmove is discarded; only final FEN result committed.
 * 6. lowerbound/upperbound info lines DO paint evalCp live (relaxed bound).
 * 7. Exact info line paints evalCp before bestmove; bestmove confirms + stops analysis.
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
    // Initialize the fake clock at epoch 0 so Date.now() is deterministic.
    // This ensures sinceLast = Date.now() - lastFenChangeAtRef.current is predictable:
    // first FEN at t=0 gives sinceLast=0 (debounce path), and the "settled move"
    // test explicitly advances past 150ms before rendering to trigger the immediate path.
    vi.useFakeTimers({ now: 0 });
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

  it('settled first move fires the search near-instantly (no fixed delay)', () => {
    // Advance fake time past RAPID_STEP_DEBOUNCE_MS (150ms) so Date.now() >> 0.
    // lastFenChangeAtRef is initialized to 0, so sinceLast = 200 - 0 = 200 > 150,
    // which triggers the immediate (non-debounced) path.
    vi.advanceTimersByTime(200);

    renderHook(() => useStockfishEngine({ fen: TEST_FEN, enabled: true }));
    driveInit(mockWorker);

    // debouncedFen was set synchronously during mount, and the debouncedFen+isReady
    // effect fired when readyok set isReady=true — so go was sent during driveInit.
    expect(mockWorker.messages.some((m) => m.startsWith('go '))).toBe(true);
  });

  it('rapid successive FEN changes coalesce — only the final FEN is searched', async () => {
    // Start at fake time 0: first FEN change gives sinceLast = 0 < 150 → debounce path.
    const { rerender } = renderHook(
      ({ fen }: { fen: string }) => useStockfishEngine({ fen, enabled: true }),
      { initialProps: { fen: TEST_FEN } },
    );
    driveInit(mockWorker);

    // Advance to 140ms — just before the TEST_FEN debounce fires at 150ms.
    // This ensures React effects are flushed in their own act before we rerender.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(140);
    });

    // Rerender within the debounce window (140ms < 150ms since TEST_FEN).
    // The FEN-effect cleanup cancels the TEST_FEN timer synchronously.
    rerender({ fen: TEST_FEN_2 });

    // Advance 200ms more — TEST_FEN_2 debounce fires at 140+150=290ms.
    // The original TEST_FEN timer (at 150ms) was cancelled; only TEST_FEN_2 fires.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Only one go command should have been sent, for the final FEN.
    const goCommands = mockWorker.messages.filter((m) => m.startsWith('go '));
    expect(goCommands).toHaveLength(1);
    expect(mockWorker.messages).toContain(`position fen ${TEST_FEN_2}`);
    expect(mockWorker.messages).not.toContain(`position fen ${TEST_FEN}`);
  });

  it('sends position + go after the debounce delay (rapid-succession path)', async () => {
    const { result } = renderHook(() =>
      useStockfishEngine({ fen: TEST_FEN, enabled: true }),
    );
    driveInit(mockWorker);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(200); // past 150 ms debounce
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

  it('lowerbound info line paints evalCp live (relaxed bound, lichess-style)', async () => {
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

    // Lowerbound info lines now paint immediately (relaxed bound for live first-paint).
    // TEST_FEN is black-to-move: UCI +45 (mover POV) → white-POV = -45.
    expect(result.current.evalCp).toBe(-45);
  });

  it('upperbound info line paints evalCp live (relaxed bound, lichess-style)', async () => {
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

    // Upperbound info lines now paint immediately (relaxed bound for live first-paint).
    // TEST_FEN is black-to-move: UCI +60 (mover POV) → white-POV = -60.
    expect(result.current.evalCp).toBe(-60);
  });

  it('exact info line already paints evalCp; bestmove confirms and stops analysis', async () => {
    const { result } = renderHook(() =>
      useStockfishEngine({ fen: TEST_FEN, enabled: true }),
    );
    driveInit(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Info line arrives during search — should paint evalCp immediately.
    act(() => {
      mockWorker.simulateMessage(
        'info depth 14 multipv 1 score cp 52 nodes 30000 pv e2e4 e7e5 g1f3',
      );
    });

    // TEST_FEN is black-to-move, so UCI's +52 (mover POV) is normalized to
    // white-POV = -52. This is set BEFORE the bestmove (live painting).
    expect(result.current.evalCp).toBe(-52);
    expect(result.current.isAnalyzing).toBe(true); // still analyzing

    // Bestmove confirms the final result and stops analysis.
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4 ponder e7e5');
    });

    expect(result.current.evalCp).toBe(-52);
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

    // Receive an info line for TEST_FEN — committed immediately via live painting.
    act(() => {
      mockWorker.simulateMessage(
        'info depth 14 multipv 1 score cp 52 nodes 30000 pv e2e4 e7e5',
      );
    });

    // Change FEN while thinking — adaptive debounce fires immediately (fake time 200
    // vs. lastFenChangeAtRef 0 → sinceLast=200 > 150), so stop is sent synchronously
    // during the rerender. The FEN effect also clears pvLines/evalCp.
    rerender({ fen: TEST_FEN_2 });

    await act(async () => {
      // No pending debounce timer (immediate fire path); advance is a no-op here.
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(mockWorker.messages).toContain('stop');

    // Stale bestmove arrives (from TEST_FEN search) — must be DISCARDED
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4 ponder e7e5');
    });

    // pvLines must remain empty — TEST_FEN result was cleared by the FEN effect
    // and the stale bestmove was discarded without committing.
    expect(result.current.pvLines).toHaveLength(0);
    // evalCp must still be null (cleared by FEN effect; stale result not committed)
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

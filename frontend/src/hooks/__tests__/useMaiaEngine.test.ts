// @vitest-environment jsdom
/**
 * useMaiaEngine mock-Worker unit tests.
 *
 * Behaviors verified (151-04-PLAN.md Task 3):
 * 1. Idle (no Worker) until enabled.
 * 2. Classic Worker instantiation + init message.
 * 3. isReady flips false->true on the 'ready' message.
 * 4. Adaptive debounce: settled FEN fires analyze with the full MAIA_ELO_LADDER.
 * 5. Rapid successive FEN changes coalesce to one analyze for the final FEN.
 * 6. Stale-result discard: a result for a superseded FEN is ignored.
 * 7. Cache hit for a previously-seen FEN skips a second worker round-trip.
 * 8. Tab-hide pause: no analyze while hidden; re-analyzes on visible.
 * 9. Unmount sends terminate and terminates the Worker.
 * 10. wdl / expectedScoreAtSelectedElo derive from the ladder rung nearest selectedElo.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMaiaEngine } from '../useMaiaEngine';
import { MAIA_ELO_LADDER, POLICY_VOCAB_SIZE } from '../../lib/maiaEncoding';

// ─── Mock Worker ─────────────────────────────────────────────────────────────

interface WorkerMessageLike {
  type: string;
  [key: string]: unknown;
}

class MockWorker {
  onmessage: ((e: MessageEvent<WorkerMessageLike>) => void) | null = null;
  messages: WorkerMessageLike[] = [];
  terminated = false;

  postMessage(msg: WorkerMessageLike): void {
    this.messages.push(msg);
  }

  terminate(): void {
    this.terminated = true;
  }

  /** Fire the onmessage handler with a synthetic structured message. */
  simulateMessage(data: WorkerMessageLike): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

let mockWorker: MockWorker;

// ─── Helpers ─────────────────────────────────────────────────────────────────

const TEST_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
const TEST_FEN_2 = 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1';

function driveReady(worker: MockWorker): void {
  act(() => {
    worker.simulateMessage({ type: 'ready', backend: 'wasm' });
  });
}

function analyzeMessages(worker: MockWorker): WorkerMessageLike[] {
  return worker.messages.filter((m) => m.type === 'analyze');
}

/** Builds a synthetic worker 'result' message for the given FEN (all-zero logits). */
function buildResultMessage(fen: string): WorkerMessageLike {
  const rawPolicyByElo = MAIA_ELO_LADDER.map((elo) => ({
    elo,
    policy: new Float32Array(POLICY_VOCAB_SIZE),
  }));
  const wdlByElo = MAIA_ELO_LADDER.map((elo) => ({ elo, wdl: Float32Array.from([0, 0, 0]) }));
  return { type: 'result', fen, rawPolicyByElo, wdlByElo, backend: 'wasm' };
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('useMaiaEngine', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function () {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('does not create a Worker until enabled', () => {
    renderHook(() => useMaiaEngine({ fen: null, enabled: false, selectedElo: 1500 }));
    const WorkerCtor = vi.mocked(globalThis.Worker as new (url: string) => Worker);
    expect(WorkerCtor).not.toHaveBeenCalled();
  });

  it('creates a classic Worker and sends init when enabled', () => {
    renderHook(() => useMaiaEngine({ fen: null, enabled: true, selectedElo: 1500 }));
    const WorkerCtor = vi.mocked(globalThis.Worker as new (url: string) => Worker);
    expect(WorkerCtor).toHaveBeenCalledWith('/maia/maia-worker.js');
    expect(mockWorker.messages).toContainEqual({ type: 'init' });
  });

  it('isReady flips false->true on the ready message', () => {
    const { result } = renderHook(() => useMaiaEngine({ fen: null, enabled: true, selectedElo: 1500 }));
    expect(result.current.isReady).toBe(false);
    driveReady(mockWorker);
    expect(result.current.isReady).toBe(true);
  });

  it('settled FEN fires analyze with the full ELO ladder once ready', async () => {
    vi.advanceTimersByTime(200); // Date.now() >> 0 so the first FEN is a "settled move".
    renderHook(() => useMaiaEngine({ fen: TEST_FEN, enabled: true, selectedElo: 1500 }));
    driveReady(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    const msgs = analyzeMessages(mockWorker);
    expect(msgs).toHaveLength(1);
    expect(msgs[0]?.fen).toBe(TEST_FEN);
    expect(msgs[0]?.eloInputs).toEqual(MAIA_ELO_LADDER);
  });

  it('rapid successive FEN changes coalesce — only the final FEN is analyzed', async () => {
    const { rerender } = renderHook(
      ({ fen }: { fen: string }) => useMaiaEngine({ fen, enabled: true, selectedElo: 1500 }),
      { initialProps: { fen: TEST_FEN } },
    );
    driveReady(mockWorker);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(140); // before the 150ms debounce fires
    });
    rerender({ fen: TEST_FEN_2 });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    const msgs = analyzeMessages(mockWorker);
    expect(msgs).toHaveLength(1);
    expect(msgs[0]?.fen).toBe(TEST_FEN_2);
  });

  it('discards a stale result whose fen no longer matches the current position', async () => {
    const { rerender, result } = renderHook(
      ({ fen }: { fen: string }) => useMaiaEngine({ fen, enabled: true, selectedElo: 1500 }),
      { initialProps: { fen: TEST_FEN } },
    );
    driveReady(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    expect(result.current.isAnalyzing).toBe(true);

    // FEN changes (immediate-fire path — sinceLast > 150ms) before TEST_FEN's result arrives.
    rerender({ fen: TEST_FEN_2 });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Stale result for the OLD fen arrives — must be discarded.
    act(() => {
      mockWorker.simulateMessage(buildResultMessage(TEST_FEN));
    });
    expect(result.current.perElo).toHaveLength(0);
  });

  it('a cache hit for a previously-seen FEN skips a second worker round-trip', async () => {
    const { rerender, result } = renderHook(
      ({ fen }: { fen: string }) => useMaiaEngine({ fen, enabled: true, selectedElo: 1500 }),
      { initialProps: { fen: TEST_FEN } },
    );
    driveReady(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    act(() => {
      mockWorker.simulateMessage(buildResultMessage(TEST_FEN));
    });
    expect(result.current.perElo.length).toBe(MAIA_ELO_LADDER.length);

    const countBefore = analyzeMessages(mockWorker).length;

    // Navigate away, then back to TEST_FEN (now cached).
    rerender({ fen: TEST_FEN_2 });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    rerender({ fen: TEST_FEN });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    // Only ONE new analyze was sent (for TEST_FEN_2) — the TEST_FEN revisit is a cache hit.
    expect(analyzeMessages(mockWorker)).toHaveLength(countBefore + 1);
    expect(result.current.perElo.length).toBe(MAIA_ELO_LADDER.length);
  });

  it('does not analyze while hidden; re-analyzes the current FEN on visible', async () => {
    renderHook(() => useMaiaEngine({ fen: TEST_FEN, enabled: true, selectedElo: 1500 }));
    driveReady(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });
    const countBeforeHide = analyzeMessages(mockWorker).length;
    expect(countBeforeHide).toBe(1);

    act(() => {
      Object.defineProperty(document, 'visibilityState', {
        value: 'hidden',
        configurable: true,
        writable: true,
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(analyzeMessages(mockWorker)).toHaveLength(countBeforeHide);

    act(() => {
      Object.defineProperty(document, 'visibilityState', {
        value: 'visible',
        configurable: true,
        writable: true,
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(analyzeMessages(mockWorker)).toHaveLength(countBeforeHide + 1);
  });

  it('unmount sends terminate and terminates the Worker (no leak)', () => {
    const { unmount } = renderHook(() => useMaiaEngine({ fen: null, enabled: true, selectedElo: 1500 }));
    unmount();
    expect(mockWorker.messages).toContainEqual({ type: 'terminate' });
    expect(mockWorker.terminated).toBe(true);
  });

  it('wdl / expectedScoreAtSelectedElo derive from the ladder rung nearest selectedElo', async () => {
    const { result } = renderHook(() => useMaiaEngine({ fen: TEST_FEN, enabled: true, selectedElo: 1550 }));
    driveReady(mockWorker);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200);
    });

    const msg = buildResultMessage(TEST_FEN);
    const wdlByElo = msg.wdlByElo as { elo: number; wdl: Float32Array }[];
    // Give the 1500 rung (nearest to selectedElo=1550, ties broken toward the
    // lower/earlier rung) a clearly winning WDL logit set.
    msg.wdlByElo = wdlByElo.map((entry) =>
      entry.elo === 1500 ? { ...entry, wdl: Float32Array.from([0, 0, 10]) } : entry,
    );
    act(() => {
      mockWorker.simulateMessage(msg);
    });

    expect(result.current.wdl?.win).toBeGreaterThan(0.9);
    expect(result.current.expectedScoreAtSelectedElo).toBeGreaterThan(0.9);
  });
});

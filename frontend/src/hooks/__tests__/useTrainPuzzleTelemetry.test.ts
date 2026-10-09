// @vitest-environment jsdom
import { createElement, useEffect, type ReactNode } from 'react';
import { act, cleanup, configure, render, renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTrainPuzzleTelemetry } from '@/hooks/useTrainPuzzleTelemetry';
import type { PhoneGrade } from '@/types/train';
import {
  THINK_MARKER_STORAGE_KEY,
  TELEMETRY_DURATION_CAP_MS,
  type ReviewTelemetrySnapshot,
} from '@/lib/trainTelemetry';

// Every flush goes through the one keepalive transport (233 review fix WR-02).
// The mock splits it by the body's `exit` so tests can assert the Next path
// (nextFlush) and the non-Next path (exitFlush) separately.
const { nextFlush, exitFlush, postReviewKeepalive, updateTrainRevealCacheReview } = vi.hoisted(() => {
  const next = vi.fn<(sessionId: number, position: number, body: unknown) => void>();
  const exit = vi.fn<(sessionId: number, position: number, body: unknown) => void>();
  return {
    updateTrainRevealCacheReview: vi.fn<(sessionId: number, position: number, snapshot: unknown) => void>(),
    nextFlush: next,
    exitFlush: exit,
    postReviewKeepalive: vi.fn((sessionId: number, position: number, body: unknown): void => {
      const target = (body as { exit?: string }).exit === 'next' ? next : exit;
      target(sessionId, position, body);
    }),
  };
});

vi.mock('@/lib/trainRevealCache', () => ({ updateTrainRevealCacheReview }));

vi.mock('@/api/client', () => ({ postReviewKeepalive }));

interface HookProps {
  sessionId: number | null;
  position: number;
  isReady: boolean;
  isRestored: boolean;
  hasVerdict: boolean;
  restoredReview: ReviewTelemetrySnapshot | undefined;
}

const BASE_PROPS: HookProps = {
  sessionId: 7,
  position: 0,
  isReady: true,
  isRestored: false,
  hasVerdict: false,
  restoredReview: undefined,
};
const REVIEW_PROPS: HookProps = { ...BASE_PROPS, hasVerdict: true };
const TWO_HOURS_MS = 2 * 60 * 60 * 1000;
/** The engagement keys of a flush body with no interaction recorded (D-14). */
const ZERO_ENGAGEMENT = {
  review_line_steps: 0,
  review_explored: false,
  review_explore_moves: 0,
  review_board_moves: 0,
  review_analyze_opened: false,
  review_walkthrough: false,
  review_chips_selected: 0,
  review_chips_total: 0,
  review_strip_expanded: false,
};

function setVisibility(state: 'visible' | 'hidden'): void {
  Object.defineProperty(document, 'visibilityState', { value: state, configurable: true, writable: true });
}

function fireVisibility(state: 'visible' | 'hidden'): void {
  setVisibility(state);
  act(() => {
    document.dispatchEvent(new Event('visibilitychange'));
  });
}

/** useMutation runs mutationFn in a microtask; vitest fake timers do not fake it. */
async function flushMicrotasks(): Promise<void> {
  await act(async () => {});
}

function firePageHide(): void {
  act(() => {
    window.dispatchEvent(new Event('pagehide'));
  });
}

function advance(ms: number): void {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

// One client per test (created in beforeEach): a client built inside the wrapper
// would be replaced on every render and drop the mutation observer.
let testClient: QueryClient;

function QueryWrapper({ children }: { children: ReactNode }) {
  return createElement(QueryClientProvider, { client: testClient }, children);
}

/**
 * StrictMode only double-invokes effects when it is the OUTERMOST element of the
 * mount: nested inside a wrapper component the simulated unmount never happens
 * and the test would silently stop covering it. RTL's `reactStrictMode` option
 * puts it at the root, so StrictMode tests flip it on around the render.
 */
function renderHookStrict(props: HookProps) {
  configure({ reactStrictMode: true });
  try {
    return renderHook((p: HookProps) => useTrainPuzzleTelemetry(p), { initialProps: props, wrapper: QueryWrapper });
  } finally {
    configure({ reactStrictMode: false });
  }
}

function mountHook(props: HookProps = BASE_PROPS) {
  return renderHook((p: HookProps) => useTrainPuzzleTelemetry(p), { initialProps: props, wrapper: QueryWrapper });
}

describe('useTrainPuzzleTelemetry', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setVisibility('visible');
    sessionStorage.clear();
    nextFlush.mockClear();
    exitFlush.mockClear();
    updateTrainRevealCacheReview.mockClear();
    postReviewKeepalive.mockClear();
    testClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  });

  afterEach(async () => {
    // Unmount every hook this test left mounted so its window/document listeners
    // cannot fire in the next test (no vitest globals, so RTL does not auto-clean).
    cleanup();
    await flushMicrotasks();
    vi.useRealTimers();
    setVisibility('visible');
    sessionStorage.clear();
  });

  it('think: the timer stays stopped while the engine is not ready', () => {
    const { result, rerender } = mountHook({ ...BASE_PROPS, isReady: false });
    advance(10_000);
    rerender({ ...BASE_PROPS, isReady: true });
    advance(2000);
    act(() => result.current.markGuess());
    advance(3000);
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toMatchObject({ guess_ms: 2000, move_ms: 3000 });
  });

  it('think: guess_ms is mount-to-guess and move_ms is guess-to-move', () => {
    const { result } = mountHook();
    advance(2000);
    act(() => result.current.markGuess());
    advance(3000);
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toEqual({
      v: 1,
      client: 'desktop',
      guess_ms: 2000,
      move_ms: 3000,
      think_hidden_ms: 0,
      resumed: false,
    });
  });

  it('think: a hidden span is excluded from move_ms and lands in think_hidden_ms', () => {
    const { result } = mountHook();
    advance(2000);
    act(() => result.current.markGuess());
    advance(1000);
    fireVisibility('hidden');
    advance(5000);
    fireVisibility('visible');
    advance(2000);
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toMatchObject({
      guess_ms: 2000,
      move_ms: 3000,
      think_hidden_ms: 5000,
    });
  });

  it('think: a duplicate hidden event does not re-baseline the hidden span', () => {
    const { result } = mountHook();
    advance(1000);
    fireVisibility('hidden');
    advance(2000);
    fireVisibility('hidden');
    advance(2000);
    fireVisibility('visible');
    act(() => result.current.markGuess());
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toMatchObject({ guess_ms: 1000, think_hidden_ms: 4000 });
  });

  it('think: mounting into a hidden tab starts paused', () => {
    setVisibility('hidden');
    const { result } = mountHook();
    advance(4000);
    fireVisibility('visible');
    advance(1000);
    act(() => result.current.markGuess());
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toMatchObject({ guess_ms: 1000, think_hidden_ms: 4000 });
  });

  it('think: durations are capped at TELEMETRY_DURATION_CAP_MS', () => {
    const { result } = mountHook();
    advance(TWO_HOURS_MS);
    act(() => result.current.markGuess());
    advance(TWO_HOURS_MS);
    act(() => result.current.markMove());
    const telemetry = result.current.solveTelemetry();
    expect(telemetry?.guess_ms).toBe(TELEMETRY_DURATION_CAP_MS);
    expect(telemetry?.move_ms).toBe(TELEMETRY_DURATION_CAP_MS);
  });

  it('think: the snapshot is frozen at the first markMove and never recomputed', () => {
    const { result } = mountHook();
    advance(1000);
    act(() => result.current.markGuess());
    advance(1000);
    act(() => result.current.markMove());
    const first = result.current.solveTelemetry();
    const firstCopy = { ...first };
    advance(9000);
    act(() => result.current.markGuess());
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toBe(first);
    expect(result.current.solveTelemetry()).toEqual(firstCopy);
  });

  it('think: a restored reveal starts no timer and writes no marker', () => {
    const { result } = mountHook({ ...BASE_PROPS, isRestored: true });
    advance(1000);
    act(() => result.current.markGuess());
    act(() => result.current.markMove());
    expect(sessionStorage.getItem(THINK_MARKER_STORAGE_KEY)).toBeNull();
    expect(result.current.solveTelemetry()).toEqual({ v: 1, client: 'desktop', resumed: false });
  });

  it('think: a fresh instance for the same puzzle is resumed, a different position is not', () => {
    const first = mountHook();
    first.unmount();

    const same = mountHook();
    act(() => same.result.current.markMove());
    expect(same.result.current.solveTelemetry()?.resumed).toBe(true);
    same.unmount();

    const other = mountHook({ ...BASE_PROPS, position: 1 });
    act(() => other.result.current.markMove());
    expect(other.result.current.solveTelemetry()?.resumed).toBe(false);
  });

  it('think: a first mount under React StrictMode is not resumed', () => {
    const { result } = renderHookStrict(BASE_PROPS);
    advance(1500);
    act(() => result.current.markGuess());
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toMatchObject({ resumed: false, guess_ms: 1500 });
  });

  it('think: advancing to the next puzzle resets the snapshot and the timer', () => {
    const { result, rerender } = mountHook();
    advance(1000);
    act(() => result.current.markGuess());
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toBeDefined();

    rerender({ ...BASE_PROPS, position: 1 });
    expect(result.current.solveTelemetry()).toBeUndefined();
    advance(500);
    act(() => result.current.markGuess());
    advance(250);
    act(() => result.current.markMove());
    expect(result.current.solveTelemetry()).toMatchObject({ guess_ms: 500, move_ms: 250, resumed: false });
  });

  it('review: no timer before the verdict, then visible time minus the hidden span is sent on Next', async () => {
    const { result, rerender } = mountHook();
    advance(10_000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).not.toHaveBeenCalled();

    rerender(REVIEW_PROPS);
    advance(4000);
    fireVisibility('hidden');
    advance(2000);
    fireVisibility('visible');
    advance(1000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();

    expect(nextFlush).toHaveBeenCalledTimes(1);
    expect(nextFlush).toHaveBeenCalledWith(7, 0, {
      v: 2,
      exit: 'next',
      review_ms: 5000,
      review_hidden_ms: 2000,
      ...ZERO_ENGAGEMENT,
    });
  });

  it('review: a second flushReviewOnNext is a no-op', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    advance(1000);
    act(() => result.current.flushReviewOnNext());
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledTimes(1);
  });

  it('review: a null session id sends nothing', async () => {
    const { result } = mountHook({ ...REVIEW_PROPS, sessionId: null });
    advance(1000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).not.toHaveBeenCalled();
  });

  it('review: a new puzzle key resets the Next-flushed guard and the timer', async () => {
    const { result, rerender } = mountHook(REVIEW_PROPS);
    advance(3000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledTimes(1);

    rerender({ ...BASE_PROPS, position: 1 });
    advance(500);
    rerender({ ...REVIEW_PROPS, position: 1 });
    advance(700);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();

    expect(nextFlush).toHaveBeenCalledTimes(2);
    expect(nextFlush).toHaveBeenLastCalledWith(7, 1, expect.objectContaining({ exit: 'next', review_ms: 700 }));
  });

  it('exit: unmount of an open reveal sends one keepalive flush', async () => {
    const { unmount } = mountHook(REVIEW_PROPS);
    advance(4000);
    unmount();
    await flushMicrotasks();
    expect(exitFlush).toHaveBeenCalledTimes(1);
    expect(exitFlush).toHaveBeenCalledWith(7, 0, {
      v: 2,
      exit: 'pagehide',
      review_ms: 4000,
      review_hidden_ms: 0,
      ...ZERO_ENGAGEMENT,
    });
    expect(nextFlush).not.toHaveBeenCalled();
  });

  it('exit: the page turning hidden sends one keepalive flush', () => {
    mountHook(REVIEW_PROPS);
    advance(3000);
    fireVisibility('hidden');
    expect(exitFlush).toHaveBeenCalledTimes(1);
    expect(exitFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ exit: 'pagehide', review_ms: 3000 }));
  });

  it('exit: hidden then pagehide in the same hidden span sends one flush', () => {
    mountHook(REVIEW_PROPS);
    advance(3000);
    fireVisibility('hidden');
    firePageHide();
    expect(exitFlush).toHaveBeenCalledTimes(1);
  });

  it('exit: hidden, visible, then Next still sends the larger Next flush', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    advance(3000);
    fireVisibility('hidden');
    advance(4000);
    fireVisibility('visible');
    advance(2000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();

    expect(exitFlush).toHaveBeenCalledTimes(1);
    expect(nextFlush).toHaveBeenCalledTimes(1);
    expect(nextFlush).toHaveBeenCalledWith(7, 0, {
      v: 2,
      exit: 'next',
      review_ms: 5000,
      review_hidden_ms: 4000,
      ...ZERO_ENGAGEMENT,
    });
  });

  it('exit: a second hidden span flushes again with the updated totals', () => {
    mountHook(REVIEW_PROPS);
    advance(3000);
    fireVisibility('hidden');
    fireVisibility('visible');
    advance(2000);
    fireVisibility('hidden');
    expect(exitFlush).toHaveBeenCalledTimes(2);
    expect(exitFlush).toHaveBeenNthCalledWith(1, 7, 0, expect.objectContaining({ review_ms: 3000 }));
    expect(exitFlush).toHaveBeenNthCalledWith(2, 7, 0, expect.objectContaining({ review_ms: 5000 }));
  });

  it('exit: Next then unmount sends nothing, and neither does Next then hidden then pagehide', async () => {
    const first = mountHook(REVIEW_PROPS);
    advance(1000);
    act(() => first.result.current.flushReviewOnNext());
    first.unmount();
    await flushMicrotasks();
    expect(exitFlush).not.toHaveBeenCalled();

    const second = mountHook({ ...REVIEW_PROPS, position: 1 });
    advance(1000);
    act(() => second.result.current.flushReviewOnNext());
    fireVisibility('hidden');
    firePageHide();
    expect(exitFlush).not.toHaveBeenCalled();
  });

  it('exit: pagehide while visible sends one keepalive flush', () => {
    mountHook(REVIEW_PROPS);
    advance(2500);
    firePageHide();
    expect(exitFlush).toHaveBeenCalledTimes(1);
    expect(exitFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ exit: 'pagehide', review_ms: 2500 }));
  });

  it('exit: StrictMode double effect sends nothing, a later real unmount sends one', async () => {
    const { unmount } = renderHookStrict(REVIEW_PROPS);
    await flushMicrotasks();
    expect(exitFlush).not.toHaveBeenCalled();

    unmount();
    await flushMicrotasks();
    expect(exitFlush).toHaveBeenCalledTimes(1);
  });

  it('exit: nothing is sent before the verdict, or without a session id', async () => {
    const early = mountHook(BASE_PROPS);
    fireVisibility('hidden');
    firePageHide();
    early.unmount();
    await flushMicrotasks();
    fireVisibility('visible');

    const noSession = mountHook({ ...REVIEW_PROPS, sessionId: null });
    fireVisibility('hidden');
    firePageHide();
    noSession.unmount();
    await flushMicrotasks();

    expect(exitFlush).not.toHaveBeenCalled();
  });

  it('analyze: snapshotReviewForAnalyze returns the totals and leaves the timer running', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    advance(4000);
    expect(result.current.snapshotReviewForAnalyze()).toEqual({
      visibleMs: 4000,
      hiddenMs: 0,
      lineSteps: 0,
      exploreMoves: 0,
      boardMoves: 0,
      analyzeOpened: true,
      walkthrough: false,
      forked: false,
      chipKeys: [],
      chipsTotal: 0,
      stripExpanded: false,
    });
    advance(1000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ review_ms: 5000 }));
  });

  it('analyze: unmount mirrors the flushed snapshot into the reveal cache', async () => {
    const { result, unmount } = mountHook(REVIEW_PROPS);
    advance(4000);
    expect(result.current.snapshotReviewForAnalyze()).toMatchObject({ visibleMs: 4000, hiddenMs: 0 });
    advance(300);
    unmount();
    await flushMicrotasks();

    expect(exitFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ review_ms: 4300 }));
    expect(updateTrainRevealCacheReview).toHaveBeenCalledTimes(1);
    expect(updateTrainRevealCacheReview).toHaveBeenCalledWith(7, 0, expect.objectContaining({ visibleMs: 4300, hiddenMs: 0 }));
  });

  it('analyze: a hidden-tab flush also mirrors its snapshot', () => {
    mountHook(REVIEW_PROPS);
    advance(2000);
    fireVisibility('hidden');
    expect(updateTrainRevealCacheReview).toHaveBeenCalledWith(7, 0, expect.objectContaining({ visibleMs: 2000 }));
  });

  it('analyze: a restored reveal continues one timer from the persisted totals', async () => {
    const { result } = mountHook({
      ...REVIEW_PROPS,
      isRestored: true,
      restoredReview: { visibleMs: 7000, hiddenMs: 1000 },
    });
    advance(3000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(7, 0, {
      v: 2,
      exit: 'next',
      review_ms: 10000,
      review_hidden_ms: 1000,
      ...ZERO_ENGAGEMENT,
    });
  });

  it.each([
    { visibleMs: -1, hiddenMs: 0 },
    { visibleMs: Number.NaN, hiddenMs: 0 },
    { visibleMs: 5, hiddenMs: Number.POSITIVE_INFINITY },
  ])('analyze: an unusable restoredReview %j is ignored (fresh timer)', async (restoredReview) => {
    const { result } = mountHook({ ...REVIEW_PROPS, isRestored: true, restoredReview });
    advance(2000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ review_ms: 2000, review_hidden_ms: 0 }));
  });

  it('counters: no interaction flushes zero counters and false flags', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    advance(1000);
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining(ZERO_ENGAGEMENT));
  });

  it('counters: 60 line steps flush review_line_steps capped at 50', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    for (let i = 0; i < 60; i++) act(() => result.current.onLineUserStep());
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ review_line_steps: 50 }));
  });

  it('counters: 3 forking explore moves flush review_explored true and review_explore_moves 3', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    for (let i = 0; i < 3; i++) act(() => result.current.onExploreMove('board', true));
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(
      7,
      0,
      expect.objectContaining({ review_explored: true, review_explore_moves: 3 }),
    );
  });

  it('counters: review_board_moves counts board moves only, review_explore_moves counts both sources', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onExploreMove('board', true));
    act(() => result.current.onExploreMove('engine-line', true));
    act(() => result.current.onExploreMove('engine-line', true));
    act(() => result.current.onExploreMove('board', true));
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(
      7,
      0,
      expect.objectContaining({ review_explored: true, review_explore_moves: 4, review_board_moves: 2 }),
    );
  });

  it('counters: explore and board moves cap at 50', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    for (let i = 0; i < 55; i++) act(() => result.current.onExploreMove('board', true));
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(
      7,
      0,
      expect.objectContaining({ review_explore_moves: 50, review_board_moves: 50 }),
    );
  });

  it('counters: the Analyze snapshot carries the counters and a restored hook continues them cumulatively', async () => {
    const first = mountHook(REVIEW_PROPS);
    advance(1000);
    act(() => first.result.current.onLineUserStep());
    act(() => first.result.current.onExploreMove('board', true));
    act(() => first.result.current.onExploreMove('engine-line', true));
    act(() => first.result.current.markWalkthroughActive());
    const snapshot = first.result.current.snapshotReviewForAnalyze();
    expect(snapshot).toMatchObject({
      lineSteps: 1,
      exploreMoves: 2,
      boardMoves: 1,
      analyzeOpened: true,
      walkthrough: true,
    });
    first.unmount();
    await flushMicrotasks();

    const restored = mountHook({ ...REVIEW_PROPS, isRestored: true, restoredReview: snapshot });
    act(() => restored.result.current.onLineUserStep());
    act(() => restored.result.current.onExploreMove('board', true));
    act(() => restored.result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(
      7,
      0,
      expect.objectContaining({
        review_line_steps: 2,
        review_explored: true,
        review_explore_moves: 3,
        review_board_moves: 2,
        review_analyze_opened: true,
        review_walkthrough: true,
      }),
    );
  });

  it('counters: markWalkthroughActive makes review_walkthrough true for that puzzle only', async () => {
    const { result, rerender } = mountHook(REVIEW_PROPS);
    act(() => result.current.markWalkthroughActive());
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenLastCalledWith(7, 0, expect.objectContaining({ review_walkthrough: true }));

    rerender({ ...REVIEW_PROPS, position: 1 });
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenLastCalledWith(7, 1, expect.objectContaining({ review_walkthrough: false }));
  });

  it('counters: a non-Next flush and a later Next flush carry non-decreasing totals', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onLineUserStep());
    fireVisibility('hidden');
    expect(exitFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ review_line_steps: 1 }));
    fireVisibility('visible');
    act(() => result.current.onLineUserStep());
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    expect(nextFlush).toHaveBeenCalledWith(7, 0, expect.objectContaining({ review_line_steps: 2 }));
  });

  it('counters: Analyze then unmount sends the keepalive flush with review_analyze_opened and mirrors it', async () => {
    const { result, unmount } = mountHook(REVIEW_PROPS);
    act(() => result.current.onLineUserStep());
    act(() => result.current.onLineUserStep());
    act(() => {
      result.current.snapshotReviewForAnalyze();
    });
    unmount();
    await flushMicrotasks();

    expect(exitFlush).toHaveBeenCalledTimes(1);
    expect(exitFlush).toHaveBeenCalledWith(
      7,
      0,
      expect.objectContaining({ exit: 'pagehide', review_analyze_opened: true, review_line_steps: 2 }),
    );
    expect(updateTrainRevealCacheReview).toHaveBeenCalledWith(
      7,
      0,
      expect.objectContaining({ analyzeOpened: true, lineSteps: 2 }),
    );
  });

  async function nextBody(result: { current: { flushReviewOnNext: () => void } }): Promise<Record<string, unknown>> {
    act(() => result.current.flushReviewOnNext());
    await flushMicrotasks();
    return nextFlush.mock.calls.at(-1)?.[2] as Record<string, unknown>;
  }

  it('chips: the default You chip is never counted, re-tapping it adds nothing', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onChipSelect('your'));
    act(() => result.current.onChipSelect('your'));
    expect((await nextBody(result)).review_chips_selected).toBe(0);
  });

  it('chips: each distinct non-default chip counts once', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onChipSelect('best'));
    act(() => result.current.onChipSelect('best'));
    act(() => result.current.onChipSelect('your'));
    act(() => result.current.onChipSelect('game'));
    expect((await nextBody(result)).review_chips_selected).toBe(2);
  });

  it('chips: chips total keeps the maximum reported', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onChipsTotalChange(2));
    act(() => result.current.onChipsTotalChange(3));
    act(() => result.current.onChipsTotalChange(1));
    expect((await nextBody(result)).review_chips_total).toBe(3);
  });

  it('chips: 12 reported chips flush review_chips_total capped at 10', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onChipsTotalChange(12));
    expect((await nextBody(result)).review_chips_total).toBe(10);
  });

  it('chips: a key change clears the chip counters for the next puzzle', async () => {
    const { result, rerender } = mountHook(REVIEW_PROPS);
    act(() => result.current.onChipSelect('best'));
    act(() => result.current.onChipsTotalChange(3));
    act(() => result.current.markStripExpanded());
    rerender({ ...REVIEW_PROPS, position: 1 });
    const body = await nextBody(result);
    expect(body).toMatchObject({ review_chips_selected: 0, review_chips_total: 0, review_strip_expanded: false });
  });

  it('strip: markStripExpanded makes review_strip_expanded true, sticky across flushes', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    fireVisibility('hidden');
    expect(exitFlush).toHaveBeenLastCalledWith(7, 0, expect.objectContaining({ review_strip_expanded: false }));
    fireVisibility('visible');
    act(() => result.current.markStripExpanded());
    act(() => result.current.markStripExpanded());
    fireVisibility('hidden');
    expect(exitFlush).toHaveBeenLastCalledWith(7, 0, expect.objectContaining({ review_strip_expanded: true }));
    fireVisibility('visible');
    expect((await nextBody(result)).review_strip_expanded).toBe(true);
  });

  it('fork (D-13): a board move that does not fork leaves review_explored false but is still counted', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onExploreMove('board', false));
    const body = await nextBody(result);
    expect(body).toMatchObject({ review_explored: false, review_explore_moves: 1, review_board_moves: 1 });
  });

  it('fork (D-13): one forking move among non-forking ones sets review_explored, sticky', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    act(() => result.current.onExploreMove('board', false));
    act(() => result.current.onExploreMove('engine-line', true));
    act(() => result.current.onExploreMove('board', false));
    expect(await nextBody(result)).toMatchObject({ review_explored: true, review_explore_moves: 3 });
  });

  it('chips: the Analyze snapshot carries chips, strip and fork, which a restored hook continues', async () => {
    const first = mountHook(REVIEW_PROPS);
    act(() => first.result.current.onChipsTotalChange(3));
    act(() => first.result.current.onChipSelect('best'));
    act(() => first.result.current.markStripExpanded());
    act(() => first.result.current.onExploreMove('board', true));
    const snapshot = first.result.current.snapshotReviewForAnalyze();
    expect(snapshot).toMatchObject({
      chipKeys: ['best'],
      chipsTotal: 3,
      stripExpanded: true,
      forked: true,
    });
    first.unmount();
    await flushMicrotasks();

    const restored = mountHook({ ...REVIEW_PROPS, isRestored: true, restoredReview: snapshot });
    act(() => restored.result.current.onChipSelect('best'));
    act(() => restored.result.current.onChipSelect('game'));
    const body = await nextBody(restored.result);
    expect(body).toMatchObject({
      review_chips_selected: 2,
      review_chips_total: 3,
      review_strip_expanded: true,
      review_explored: true,
    });
  });

  it('chips: a legacy v1 snapshot (card keys, no chip fields) still seeds the timer and ignores the card keys', async () => {
    const legacy = { visibleMs: 3000, hiddenMs: 0, cardKeys: ['card-a'], cardsTotal: 4 } as ReviewTelemetrySnapshot;
    const { result } = mountHook({ ...REVIEW_PROPS, isRestored: true, restoredReview: legacy });
    const body = await nextBody(result);
    expect(body).toMatchObject({ review_ms: 3000, review_chips_selected: 0, review_chips_total: 0 });
    expect(body).not.toHaveProperty('review_cards_opened');
  });

  it("chips: a total reported by a parent-screen effect on the first mount survives", async () => {
    // The screen reports its chip total in an effect declared after the hook's own
    // effects; a first-mount reset would wipe a count reported before them.
    const captured: { current: ReturnType<typeof useTrainPuzzleTelemetry> | null } = { current: null };
    function Child({ report }: { report: (total: number) => void }) {
      useEffect(() => {
        report(3);
      }, [report]);
      return null;
    }
    function Parent() {
      const telemetry = useTrainPuzzleTelemetry(REVIEW_PROPS);
      useEffect(() => {
        captured.current = telemetry;
      }, [telemetry]);
      return createElement(Child, { report: telemetry.onChipsTotalChange });
    }
    render(createElement(QueryWrapper, null, createElement(Parent)));
    act(() => captured.current!.flushReviewOnNext());
    await flushMicrotasks();
    expect((nextFlush.mock.calls.at(-1)?.[2] as Record<string, unknown>).review_chips_total).toBe(3);
  });

  it('closed set: a flush body has exactly the v2 keys (D-12) and no card keys', async () => {
    const { result } = mountHook(REVIEW_PROPS);
    advance(1000);
    const body = await nextBody(result);
    expect(Object.keys(body).sort()).toEqual(
      [
        'v',
        'exit',
        'review_ms',
        'review_hidden_ms',
        'review_chips_selected',
        'review_chips_total',
        'review_strip_expanded',
        'review_line_steps',
        'review_explored',
        'review_explore_moves',
        'review_board_moves',
        'review_analyze_opened',
        'review_walkthrough',
      ].sort(),
    );
  });

  describe('late phone_grade record (Phase 236 D-12)', () => {
    const RECORD: PhoneGrade = { v: 1, tier: 'good', key_es: 0.6, played_es: 0.58, key_depth: 10, played_depth: 10 };

    it('a record set for the current puzzle rides the Next flush', async () => {
      const { result } = mountHook(REVIEW_PROPS);
      advance(1000);
      act(() => result.current.setLatePhoneGrade(7, 0, RECORD));
      const body = await nextBody(result);
      expect(body.phone_grade).toEqual(RECORD);
      expect(body).toMatchObject({ v: 2, exit: 'next' });
    });

    it('a record set before a hidden tab rides the pagehide-style flush', () => {
      const { result } = mountHook(REVIEW_PROPS);
      advance(1000);
      act(() => result.current.setLatePhoneGrade(7, 0, RECORD));
      fireVisibility('hidden');
      expect(exitFlush).toHaveBeenCalledTimes(1);
      expect((exitFlush.mock.calls[0]?.[2] as Record<string, unknown>).phone_grade).toEqual(RECORD);
    });

    it('without a record the flush body has no phone_grade key', async () => {
      const { result } = mountHook(REVIEW_PROPS);
      advance(1000);
      const body = await nextBody(result);
      expect(body).not.toHaveProperty('phone_grade');
    });

    it('a flush sent before the record arrived carries none, the later Next flush carries it', async () => {
      const { result } = mountHook(REVIEW_PROPS);
      advance(1000);
      fireVisibility('hidden');
      expect(exitFlush).toHaveBeenCalledTimes(1);
      expect(exitFlush.mock.calls[0]?.[2]).not.toHaveProperty('phone_grade');
      fireVisibility('visible');
      act(() => result.current.setLatePhoneGrade(7, 0, RECORD));
      const body = await nextBody(result);
      expect(body.phone_grade).toEqual(RECORD);
    });

    it('a record for a puzzle the user already left is ignored (Pitfall 4)', async () => {
      const { result, rerender } = mountHook(REVIEW_PROPS);
      rerender({ ...REVIEW_PROPS, position: 1 });
      advance(1000);
      // The background grade of position 0 settles after the key moved to position 1.
      act(() => result.current.setLatePhoneGrade(7, 0, RECORD));
      const body = await nextBody(result);
      expect(nextFlush).toHaveBeenLastCalledWith(7, 1, expect.anything());
      expect(body).not.toHaveProperty('phone_grade');
    });

    it('a position change clears a stored record', async () => {
      const { result, rerender } = mountHook(REVIEW_PROPS);
      act(() => result.current.setLatePhoneGrade(7, 0, RECORD));
      rerender({ ...BASE_PROPS, position: 1 });
      rerender({ ...REVIEW_PROPS, position: 1 });
      advance(1000);
      const body = await nextBody(result);
      expect(body).not.toHaveProperty('phone_grade');
    });
  });
});

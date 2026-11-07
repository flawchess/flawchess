// @vitest-environment jsdom
/**
 * useTrainLoop: the pure immersive rule (`resolveTrainImmersive`) and the
 * hook-level latch / deferred re-read behaviour. The session and engine hooks
 * are mocked so only useTrainLoop's own logic is under test.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import type { CachedTrainReveal } from '@/lib/trainRevealCache';
import type { TrainSessionResponse } from '@/types/train';

const mocks = vi.hoisted(() => ({
  startSession: vi.fn(),
  resetSolve: vi.fn(),
  markSessionEntered: vi.fn(),
  engineEnabled: vi.fn(),
}));

vi.mock('@/hooks/useTrainSession', () => ({
  useTrainSession: () => ({
    session: null,
    currentPuzzle: null,
    isSessionError: false,
    isSessionPending: false,
    lastSolveResponse: null,
    advance: vi.fn(),
    startSession: mocks.startSession,
    resetSolve: mocks.resetSolve,
    markSessionEntered: mocks.markSessionEntered,
  }),
}));

vi.mock('@/hooks/useTrainGradingEngine', () => ({
  useTrainGradingEngine: (opts: { enabled: boolean }) => {
    mocks.engineEnabled(opts.enabled);
    return {};
  },
}));

import { resolveTrainImmersive, useTrainLoop } from '@/hooks/useTrainLoop';

const REVEAL = { sessionId: 7 } as CachedTrainReveal;
const SESSION_7 = { session_id: 7 } as TrainSessionResponse;
const SESSION_8 = { session_id: 8 } as TrainSessionResponse;

type ImmersiveInput = Parameters<typeof resolveTrainImmersive>[0];
const BASE: ImmersiveInput = {
  isToday: true,
  showLoop: false,
  showScoreScreen: false,
  restoredReveal: null,
  session: null,
  isSessionError: false,
};

describe('resolveTrainImmersive', () => {
  it.each<[string, Partial<ImmersiveInput>, boolean]>([
    ['not Today is always false, even mid-loop', { isToday: false, showLoop: true }, false],
    ['not Today is false with a cached reveal and no session', { isToday: false, restoredReveal: REVEAL }, false],
    ['the solve loop is immersive', { showLoop: true }, true],
    ['the score screen is immersive', { showScoreScreen: true }, true],
    ['a cached reveal with no session yet is immersive (first paint)', { restoredReveal: REVEAL }, true],
    ['a cached reveal with a matching session is immersive', { restoredReveal: REVEAL, session: SESSION_7 }, true],
    ['a cached reveal with a mismatching session is not', { restoredReveal: REVEAL, session: SESSION_8 }, false],
    ['a cached reveal with a session error is not', { restoredReveal: REVEAL, isSessionError: true }, false],
    ['no reveal and no loop is not', {}, false],
  ])('%s', (_label, override, expected) => {
    expect(resolveTrainImmersive({ ...BASE, ...override })).toBe(expected);
  });
});

describe('useTrainLoop', () => {
  beforeEach(() => {
    mocks.startSession.mockClear();
    mocks.resetSolve.mockClear();
    mocks.engineEnabled.mockClear();
  });
  afterEach(() => {
    cleanup();
    sessionStorage.clear();
  });

  it('does not read the session or enable the engine until Today is visited', () => {
    const { rerender } = renderHook((props) => useTrainLoop(props), {
      initialProps: { isToday: false, canTrain: true },
    });
    expect(mocks.startSession).not.toHaveBeenCalled();
    expect(mocks.engineEnabled).toHaveBeenLastCalledWith(false);

    rerender({ isToday: true, canTrain: true });
    expect(mocks.startSession).toHaveBeenCalledTimes(1);
    expect(mocks.engineEnabled).toHaveBeenLastCalledWith(true);

    // One-way: leaving Today neither re-reads nor disables the engine.
    rerender({ isToday: false, canTrain: true });
    expect(mocks.startSession).toHaveBeenCalledTimes(1);
    expect(mocks.engineEnabled).toHaveBeenLastCalledWith(true);
  });

  it('keeps one requestSessionReread identity across renders', () => {
    const { result, rerender } = renderHook((props) => useTrainLoop(props), {
      initialProps: { isToday: true, canTrain: true },
    });
    const first = result.current.requestSessionReread;
    rerender({ isToday: true, canTrain: true });
    rerender({ isToday: false, canTrain: true });
    expect(result.current.requestSessionReread).toBe(first);
  });

  it('defers a requested re-read until Today is active again', () => {
    const { result, rerender } = renderHook((props) => useTrainLoop(props), {
      initialProps: { isToday: true, canTrain: true },
    });
    expect(mocks.startSession).toHaveBeenCalledTimes(1);
    rerender({ isToday: false, canTrain: true });
    mocks.startSession.mockClear();

    act(() => result.current.requestSessionReread());
    expect(mocks.startSession).toHaveBeenCalledTimes(0);

    rerender({ isToday: true, canTrain: true });
    expect(mocks.startSession).toHaveBeenCalledTimes(1);
    expect(mocks.resetSolve).toHaveBeenCalledTimes(1);

    // The flag is consumed: a further render does not re-read.
    rerender({ isToday: true, canTrain: true });
    expect(mocks.startSession).toHaveBeenCalledTimes(1);
  });
});

// @vitest-environment jsdom
/**
 * useWinCelebrationHold.ts unit tests (Quick 260723-tqn).
 *
 * Behaviors verified:
 * 1. Returns false for a null outcome.
 * 2. Returns false for a loss outcome (winner !== userColor).
 * 3. Returns false for a draw outcome.
 * 4. On a fresh human-win outcome with NOT reduced-motion: returns true
 *    immediately, then false after WIN_CELEBRATION_HOLD_MS (fake timers).
 * 5. On a human win WITH reduced-motion: returns false (no hold).
 * 6. Clears its timeout on unmount.
 * 7. Resets (no re-trigger) once outcome goes back to null then a new win.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import type { MoverColor } from '@/lib/liveFlaw';

const prefersReducedMotionMock = vi.fn(() => false);

vi.mock('@/lib/confetti', () => ({
  prefersReducedMotion: () => prefersReducedMotionMock(),
}));

import {
  useWinCelebrationHold,
  WIN_CELEBRATION_HOLD_MS,
} from '../useWinCelebrationHold';

const USER_COLOR: MoverColor = 'white';
const WIN_OUTCOME: BotGameOutcome = { reason: 'checkmate', winner: 'white' };
const LOSS_OUTCOME: BotGameOutcome = { reason: 'checkmate', winner: 'black' };
const DRAW_OUTCOME: BotGameOutcome = { reason: 'draw', drawReason: 'stalemate' };

beforeEach(() => {
  prefersReducedMotionMock.mockReturnValue(false);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useWinCelebrationHold', () => {
  it('returns false for a null outcome', () => {
    const { result } = renderHook(() => useWinCelebrationHold(null, USER_COLOR));
    expect(result.current).toBe(false);
  });

  it('returns false for a loss outcome', () => {
    const { result } = renderHook(() =>
      useWinCelebrationHold(LOSS_OUTCOME, USER_COLOR),
    );
    expect(result.current).toBe(false);
  });

  it('returns false for a draw outcome', () => {
    const { result } = renderHook(() =>
      useWinCelebrationHold(DRAW_OUTCOME, USER_COLOR),
    );
    expect(result.current).toBe(false);
  });

  it('holds true on a fresh human win (not reduced-motion), then flips false after the delay', () => {
    const { result, rerender } = renderHook(
      ({ outcome }: { outcome: BotGameOutcome | null }) =>
        useWinCelebrationHold(outcome, USER_COLOR),
      { initialProps: { outcome: null as BotGameOutcome | null } },
    );
    expect(result.current).toBe(false);

    rerender({ outcome: WIN_OUTCOME });
    expect(result.current).toBe(true);

    act(() => {
      vi.advanceTimersByTime(WIN_CELEBRATION_HOLD_MS - 1);
    });
    expect(result.current).toBe(true);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe(false);
  });

  it('returns false (no hold) on a human win with reduced-motion', () => {
    prefersReducedMotionMock.mockReturnValue(true);
    const { result, rerender } = renderHook(
      ({ outcome }: { outcome: BotGameOutcome | null }) =>
        useWinCelebrationHold(outcome, USER_COLOR),
      { initialProps: { outcome: null as BotGameOutcome | null } },
    );

    rerender({ outcome: WIN_OUTCOME });
    expect(result.current).toBe(false);

    act(() => {
      vi.advanceTimersByTime(WIN_CELEBRATION_HOLD_MS);
    });
    expect(result.current).toBe(false);
  });

  it('clears its timeout on unmount without throwing', () => {
    const { rerender, unmount } = renderHook(
      ({ outcome }: { outcome: BotGameOutcome | null }) =>
        useWinCelebrationHold(outcome, USER_COLOR),
      { initialProps: { outcome: null as BotGameOutcome | null } },
    );
    rerender({ outcome: WIN_OUTCOME });
    expect(() => unmount()).not.toThrow();
    expect(() =>
      act(() => {
        vi.advanceTimersByTime(WIN_CELEBRATION_HOLD_MS);
      }),
    ).not.toThrow();
  });

  it('resets and re-triggers on a fresh win after outcome returns to null', () => {
    const { result, rerender } = renderHook(
      ({ outcome }: { outcome: BotGameOutcome | null }) =>
        useWinCelebrationHold(outcome, USER_COLOR),
      { initialProps: { outcome: null as BotGameOutcome | null } },
    );

    rerender({ outcome: WIN_OUTCOME });
    expect(result.current).toBe(true);
    act(() => {
      vi.advanceTimersByTime(WIN_CELEBRATION_HOLD_MS);
    });
    expect(result.current).toBe(false);

    // New game: outcome resets to null, then a fresh win outcome arrives.
    rerender({ outcome: null });
    expect(result.current).toBe(false);

    rerender({ outcome: { reason: 'checkmate', winner: 'white' } });
    expect(result.current).toBe(true);
    act(() => {
      vi.advanceTimersByTime(WIN_CELEBRATION_HOLD_MS);
    });
    expect(result.current).toBe(false);
  });
});

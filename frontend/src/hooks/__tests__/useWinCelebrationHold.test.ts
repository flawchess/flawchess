// @vitest-environment jsdom
/**
 * useWinCelebrationHold.ts unit tests (Quick 260723-tqn; retimed in Phase
 * 223 UAT to the real confetti lifetime).
 *
 * Behaviors verified:
 * 1. Returns false for a null outcome.
 * 2. A win holds for the FULL confetti lifetime (CONFETTI_DURATION_MS), not
 *    a shorter guess — the UAT regression this rewrite fixes.
 * 3. A loss and a draw do NOT hold: no confetti is playing, and the bot's
 *    terminal line now lives inside the dialog rather than behind it.
 * 4. A win WITH reduced-motion does not hold either (no burst).
 * 5. Clears its timeout on unmount.
 * 6. Resets (and re-triggers) once outcome goes back to null then a new win.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import type { MoverColor } from '@/lib/liveFlaw';

const prefersReducedMotionMock = vi.fn(() => false);
const CONFETTI_DURATION_MS = 3000;

vi.mock('@/lib/confetti', () => ({
  prefersReducedMotion: () => prefersReducedMotionMock(),
  CONFETTI_DURATION_MS: 3000,
}));

import { useWinCelebrationHold } from '../useWinCelebrationHold';

const USER_COLOR: MoverColor = 'white';
const WIN_OUTCOME: BotGameOutcome = { reason: 'checkmate', winner: 'white' };
const LOSS_OUTCOME: BotGameOutcome = { reason: 'checkmate', winner: 'black' };
const DRAW_OUTCOME: BotGameOutcome = { reason: 'draw', drawReason: 'stalemate' };

/** Mounts the hook with no outcome, then lands `outcome` as a fresh one —
 * the only transition the hook actually starts a hold on. */
function renderWithOutcome(outcome: BotGameOutcome) {
  const view = renderHook(
    ({ o }: { o: BotGameOutcome | null }) => useWinCelebrationHold(o, USER_COLOR),
    { initialProps: { o: null as BotGameOutcome | null } },
  );
  view.rerender({ o: outcome });
  return view;
}

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

  it('holds a win for the full confetti lifetime, not a shorter guess', () => {
    const { result } = renderWithOutcome(WIN_OUTCOME);
    expect(result.current).toBe(true);

    // The regression guard: the burst is still on screen at the OLD 1300ms
    // hold, and at every moment before CONFETTI_DURATION_MS.
    act(() => {
      vi.advanceTimersByTime(CONFETTI_DURATION_MS - 1);
    });
    expect(result.current).toBe(true);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe(false);
  });

  it.each([
    ['loss', LOSS_OUTCOME],
    ['draw', DRAW_OUTCOME],
  ])('does not hold on a %s — no confetti to wait out', (_label, outcome) => {
    const { result } = renderWithOutcome(outcome);
    expect(result.current).toBe(false);

    act(() => {
      vi.advanceTimersByTime(CONFETTI_DURATION_MS);
    });
    expect(result.current).toBe(false);
  });

  it('does not hold a reduced-motion win', () => {
    prefersReducedMotionMock.mockReturnValue(true);
    const { result } = renderWithOutcome(WIN_OUTCOME);
    expect(result.current).toBe(false);

    act(() => {
      vi.advanceTimersByTime(CONFETTI_DURATION_MS);
    });
    expect(result.current).toBe(false);
  });

  it('clears its timeout on unmount without throwing', () => {
    const { unmount } = renderWithOutcome(WIN_OUTCOME);
    expect(() => unmount()).not.toThrow();
    expect(() =>
      act(() => {
        vi.advanceTimersByTime(CONFETTI_DURATION_MS);
      }),
    ).not.toThrow();
  });

  it('resets and re-triggers on a fresh win after outcome returns to null', () => {
    const { result, rerender } = renderHook(
      ({ o }: { o: BotGameOutcome | null }) => useWinCelebrationHold(o, USER_COLOR),
      { initialProps: { o: null as BotGameOutcome | null } },
    );

    rerender({ o: WIN_OUTCOME });
    expect(result.current).toBe(true);
    act(() => {
      vi.advanceTimersByTime(CONFETTI_DURATION_MS);
    });
    expect(result.current).toBe(false);

    // New game: outcome resets to null, then a fresh win outcome arrives.
    rerender({ o: null });
    expect(result.current).toBe(false);

    rerender({ o: { reason: 'checkmate', winner: 'white' } });
    expect(result.current).toBe(true);
    act(() => {
      vi.advanceTimersByTime(CONFETTI_DURATION_MS);
    });
    expect(result.current).toBe(false);
  });
});

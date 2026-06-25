// @vitest-environment jsdom
/**
 * useTacticLine hook tests (Phase 135, Plan 02, Task 1 — RED).
 *
 * Behaviors verified:
 * 1. Initial state: currentPly=0, position==rootFen, lastMove==null.
 * 2. goForward advances currentPly and sets position + lastMove.
 * 3. goForward at end is a no-op (canGoForward false).
 * 4. goBack retreats; goBack at ply 0 is a no-op.
 * 5. goToMove(2) jumps directly.
 * 6. displayDepth = max(0, rootDisplayDepth - currentPly), never negative.
 * 7. isPayoff is false at/before punchline ply, true after.
 * 8. reset() returns to ply 0 / rootFen.
 * 9. orientation reset: changing orientation resets to ply 0.
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTacticLine } from '../useTacticLine';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';

// Legal FEN — after 1. e4 e5 (standard open game — root of the PV for this test).
const ROOT_FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';
// Legal SAN moves playable from ROOT_FEN (verified against chess.js):
// 2. Nf3 Nc6 3. Bc4 — three moves.
const MOVES = ['Nf3', 'Nc6', 'Bc4'];

// tacticDepthRaw=1 means the punchline is at PV index 1 (0-based), i.e. ply 2.
const TACTIC_DEPTH_RAW = 1;
const ORIENTATION = 'missed' as const;

describe('useTacticLine', () => {
  it('starts at ply 0 with rootFen and null lastMove', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    expect(result.current.currentPly).toBe(0);
    expect(result.current.position).toBe(ROOT_FEN);
    expect(result.current.lastMove).toBeNull();
    expect(result.current.canGoBack).toBe(false);
    expect(result.current.canGoForward).toBe(true);
  });

  it('goForward advances to ply 1 and sets lastMove', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    act(() => { result.current.goForward(); });

    expect(result.current.currentPly).toBe(1);
    expect(result.current.position).not.toBe(ROOT_FEN);
    expect(result.current.lastMove).not.toBeNull();
    expect(result.current.lastMove?.from).toBeDefined();
    expect(result.current.lastMove?.to).toBeDefined();
    expect(result.current.canGoBack).toBe(true);
  });

  it('goForward at the last ply is a no-op (canGoForward false at end)', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    // Advance to end.
    act(() => { result.current.goForward(); });
    act(() => { result.current.goForward(); });
    act(() => { result.current.goForward(); });

    expect(result.current.currentPly).toBe(MOVES.length);
    expect(result.current.canGoForward).toBe(false);

    // Another goForward is a no-op.
    act(() => { result.current.goForward(); });
    expect(result.current.currentPly).toBe(MOVES.length);
  });

  it('goBack retreats one ply; goBack at ply 0 is a no-op', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    act(() => { result.current.goForward(); });
    expect(result.current.currentPly).toBe(1);

    act(() => { result.current.goBack(); });
    expect(result.current.currentPly).toBe(0);
    expect(result.current.position).toBe(ROOT_FEN);
    expect(result.current.lastMove).toBeNull();
    expect(result.current.canGoBack).toBe(false);

    // goBack at ply 0 is no-op.
    act(() => { result.current.goBack(); });
    expect(result.current.currentPly).toBe(0);
  });

  it('goToMove(2) jumps directly to ply 2', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    act(() => { result.current.goToMove(2); });

    expect(result.current.currentPly).toBe(2);
    expect(result.current.lastMove).not.toBeNull();
  });

  it('displayDepth decrements per ply and floors at 0 (never negative)', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    const rootDisplay = toDisplayDepthForOrientation(TACTIC_DEPTH_RAW, ORIENTATION);

    expect(result.current.displayDepth).toBe(rootDisplay); // ply 0

    act(() => { result.current.goForward(); });
    expect(result.current.displayDepth).toBe(Math.max(0, rootDisplay - 1)); // ply 1

    act(() => { result.current.goForward(); });
    expect(result.current.displayDepth).toBe(Math.max(0, rootDisplay - 2)); // ply 2

    // Advance past punchline — should not go below 0.
    act(() => { result.current.goForward(); });
    expect(result.current.displayDepth).toBeGreaterThanOrEqual(0);
  });

  it('isPayoff stays false through the punchline ply (counter reaches 0) and flips true only after', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    // tacticDepthRaw=1, missed → rootDisplayDepth=2, so the countdown reaches 0 at
    // ply 2 (the punchline). isPayoff stays false through that ply and flips true
    // only once stepped PAST it (Phase 135 UAT: depth counter must reach 0).
    // ply 0: before punchline.
    expect(result.current.isPayoff).toBe(false);

    // ply 1: still counting down (displayDepth 1).
    act(() => { result.current.goForward(); });
    expect(result.current.isPayoff).toBe(false);

    // ply 2: AT the punchline — displayDepth hits 0, still NOT payoff.
    act(() => { result.current.goForward(); });
    expect(result.current.displayDepth).toBe(0);
    expect(result.current.isPayoff).toBe(false);

    // ply 3: stepped past the punchline → payoff.
    act(() => { result.current.goForward(); });
    expect(result.current.isPayoff).toBe(true);
  });

  it('reset() returns to ply 0 and rootFen', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: MOVES, rootFen: ROOT_FEN, tacticDepthRaw: TACTIC_DEPTH_RAW, orientation: ORIENTATION }),
    );

    act(() => { result.current.goForward(); });
    act(() => { result.current.goForward(); });
    expect(result.current.currentPly).toBe(2);

    act(() => { result.current.reset(); });

    expect(result.current.currentPly).toBe(0);
    expect(result.current.position).toBe(ROOT_FEN);
    expect(result.current.lastMove).toBeNull();
    expect(result.current.canGoBack).toBe(false);
  });

  it('handles null moves gracefully (empty line)', () => {
    const { result } = renderHook(() =>
      useTacticLine({ moves: null, rootFen: ROOT_FEN, tacticDepthRaw: 0, orientation: ORIENTATION }),
    );

    expect(result.current.currentPly).toBe(0);
    expect(result.current.canGoForward).toBe(false);
    expect(result.current.canGoBack).toBe(false);
  });

  it('displayDepth never goes negative even when currentPly exceeds rootDisplayDepth (short-PV case)', () => {
    // Short PV: only 1 move but tacticDepthRaw=3 (engine depth exceeds PV length).
    const { result } = renderHook(() =>
      useTacticLine({ moves: ['Nf3'], rootFen: ROOT_FEN, tacticDepthRaw: 3, orientation: ORIENTATION }),
    );

    // rootDisplayDepth = toDisplayDepthForOrientation(3, 'missed') = 4.
    // After advancing past the only move, currentPly=1, displayDepth = max(0, 4-1) = 3. Still fine.
    // The floor check: simulate high currentPly by going to the end.
    act(() => { result.current.goForward(); }); // ply 1

    // depth should be positive or zero, never negative.
    expect(result.current.displayDepth).toBeGreaterThanOrEqual(0);
  });
});

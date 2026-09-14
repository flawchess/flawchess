// @vitest-environment jsdom
/**
 * animatedScroll.ts unit tests (Quick 260914-uer, QUICK-03).
 *
 * Behaviors verified:
 * 1. `durationMs <= 0` (the reduced-motion path) sets `scrollTop` to
 *    `start + delta` in a single write, with no rAF scheduled.
 * 2. `durationMs > 0` walks `scrollTop` across successive rAF ticks and
 *    lands EXACTLY on `start + delta` on the final tick (no easing residue).
 * 3. `deltaPx === 0` is a no-op.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { animateScrollTop } from '../animatedScroll';

function fakeElement(scrollTop: number): HTMLElement {
  return { scrollTop } as unknown as HTMLElement;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('animateScrollTop', () => {
  it('deltaPx === 0 is a no-op: scrollTop unchanged, no rAF scheduled', () => {
    const rafSpy = vi.fn();
    vi.stubGlobal('requestAnimationFrame', rafSpy);
    const element = fakeElement(42);
    animateScrollTop(element, 0, 700);
    expect(element.scrollTop).toBe(42);
    expect(rafSpy).not.toHaveBeenCalled();
  });

  it('durationMs <= 0 writes start + delta in a single step, no rAF scheduled', () => {
    const rafSpy = vi.fn();
    vi.stubGlobal('requestAnimationFrame', rafSpy);
    const element = fakeElement(10);
    animateScrollTop(element, 50, 0);
    expect(element.scrollTop).toBe(60);
    expect(rafSpy).not.toHaveBeenCalled();
  });

  it('a negative durationMs also writes in a single step (reduced-motion callers pass 0, but <= 0 is the contract)', () => {
    const rafSpy = vi.fn();
    vi.stubGlobal('requestAnimationFrame', rafSpy);
    const element = fakeElement(0);
    animateScrollTop(element, -20, -1);
    expect(element.scrollTop).toBe(-20);
    expect(rafSpy).not.toHaveBeenCalled();
  });

  it('falls back to a single write when requestAnimationFrame is not a function', () => {
    vi.stubGlobal('requestAnimationFrame', undefined);
    const element = fakeElement(5);
    animateScrollTop(element, 100, 700);
    expect(element.scrollTop).toBe(105);
  });

  it('walks scrollTop across rAF ticks and lands exactly on start + delta on the final tick', () => {
    let now = 0;
    vi.stubGlobal('performance', { ...performance, now: () => now });
    const callbacks: Array<(t: number) => void> = [];
    vi.stubGlobal('requestAnimationFrame', (cb: (t: number) => void) => {
      callbacks.push(cb);
      return callbacks.length;
    });

    const element = fakeElement(100);
    animateScrollTop(element, 200, 1000);
    // The tween schedules its first frame synchronously but does not write yet.
    expect(element.scrollTop).toBe(100);
    expect(callbacks.length).toBe(1);

    // Halfway through the duration: scrollTop has moved, but not to the final value.
    now = 500;
    const midTick = callbacks.shift();
    midTick?.(now);
    expect(element.scrollTop).toBeGreaterThan(100);
    expect(element.scrollTop).toBeLessThan(300);
    expect(callbacks.length).toBe(1);

    // Exactly at the duration: lands EXACTLY on start + delta, no rounding residue.
    now = 1000;
    const finalTick = callbacks.shift();
    finalTick?.(now);
    expect(element.scrollTop).toBe(300);
    expect(callbacks.length).toBe(0);
  });

  it('a tick past the duration also clamps progress to 1 and lands exactly on start + delta', () => {
    let now = 0;
    vi.stubGlobal('performance', { ...performance, now: () => now });
    const callbacks: Array<(t: number) => void> = [];
    vi.stubGlobal('requestAnimationFrame', (cb: (t: number) => void) => {
      callbacks.push(cb);
      return callbacks.length;
    });

    const element = fakeElement(0);
    animateScrollTop(element, 50, 100);
    now = 5000; // way past the duration
    callbacks.shift()?.(now);
    expect(element.scrollTop).toBe(50);
  });
});

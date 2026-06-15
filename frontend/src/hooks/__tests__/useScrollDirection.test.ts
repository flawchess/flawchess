// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { useScrollDirection } from '../useScrollDirection';

describe('useScrollDirection', () => {
  beforeEach(() => {
    // Reset scrollY to 0 before each test
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true });
    // Make requestAnimationFrame synchronous so scroll events fire immediately in tests.
    // Without this, rAF callbacks are deferred and act() can't flush them.
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0);
      return 0;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns "up" initially (at top of page)', () => {
    const { result } = renderHook(() => useScrollDirection());
    expect(result.current).toBe('up');
  });

  it('returns "up" when scrollY is 0', () => {
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true });
    const { result } = renderHook(() => useScrollDirection());
    expect(result.current).toBe('up');
  });

  it('returns "down" when scrollY increases past threshold', () => {
    const { result } = renderHook(() => useScrollDirection());

    act(() => {
      // Simulate scrolling down past threshold (SCROLL_DELTA_THRESHOLD = 8)
      Object.defineProperty(window, 'scrollY', { value: 100, writable: true });
      window.dispatchEvent(new Event('scroll'));
    });

    expect(result.current).toBe('down');
  });

  it('returns "up" when scrollY decreases after scrolling down', () => {
    const { result } = renderHook(() => useScrollDirection());

    act(() => {
      // First scroll down
      Object.defineProperty(window, 'scrollY', { value: 200, writable: true });
      window.dispatchEvent(new Event('scroll'));
    });

    expect(result.current).toBe('down');

    act(() => {
      // Then scroll up past threshold
      Object.defineProperty(window, 'scrollY', { value: 180, writable: true });
      window.dispatchEvent(new Event('scroll'));
    });

    expect(result.current).toBe('up');
  });

  it('returns "up" when back at top (scrollY near 0)', () => {
    const { result } = renderHook(() => useScrollDirection());

    act(() => {
      // Scroll down
      Object.defineProperty(window, 'scrollY', { value: 300, writable: true });
      window.dispatchEvent(new Event('scroll'));
    });

    expect(result.current).toBe('down');

    act(() => {
      // Return to top
      Object.defineProperty(window, 'scrollY', { value: 0, writable: true });
      window.dispatchEvent(new Event('scroll'));
    });

    // At top, always "up"
    expect(result.current).toBe('up');
  });

  it('ignores scroll deltas below threshold', () => {
    const { result } = renderHook(() => useScrollDirection());

    act(() => {
      // First scroll down a lot to establish "down" state
      Object.defineProperty(window, 'scrollY', { value: 100, writable: true });
      window.dispatchEvent(new Event('scroll'));
    });

    expect(result.current).toBe('down');

    act(() => {
      // Jitter: small scroll up below threshold (< 8px) — should stay "down"
      Object.defineProperty(window, 'scrollY', { value: 97, writable: true });
      window.dispatchEvent(new Event('scroll'));
    });

    // Sub-threshold delta should not flip direction
    expect(result.current).toBe('down');
  });
});

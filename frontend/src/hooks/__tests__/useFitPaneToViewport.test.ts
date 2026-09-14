// @vitest-environment jsdom
/**
 * useFitPaneToViewport.ts unit tests (Quick 260914-uer, QUICK-04).
 *
 * Behaviors verified:
 * 4. With a stubbed viewport and stubbed pane/body rects, the returned max
 *    height is `clientHeight - paneTopDoc - chromeBelow - gutterPx`.
 * 5. The result never drops below `minPx`.
 * 6. Before the ref is attached (pane not mounted) the hook returns `null`
 *    (= "no cap yet").
 *
 * Uses `renderHook` (no JSX component under test — see
 * `useWinCelebrationHold.test.ts` for the local idiom) and manually attaches
 * a real, detached `<div>` to the hook's `paneRef.current` outside of
 * render, then fires a `window` resize event to drive the hook's own resize
 * listener — this exercises the exact re-measurement path a real mount +
 * layout pass would, without a wrapper component whose render would
 * otherwise need to mutate outside state (a React purity violation the
 * project's `react-hooks` lint config gates on).
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, fireEvent } from '@testing-library/react';
import { useFitPaneToViewport } from '../useFitPaneToViewport';

// jsdom has no ResizeObserver; same per-file stub precedent as
// TrainSolveScreen.test.tsx.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
  ResizeObserverStub;

const GUTTER_PX = 8;
const MIN_PX = 160;
const CLIENT_HEIGHT = 800;

function rect(partial: Partial<DOMRect>): DOMRect {
  return {
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    toJSON: () => ({}),
    ...partial,
  } as DOMRect;
}

beforeEach(() => {
  Object.defineProperty(document.documentElement, 'clientHeight', {
    configurable: true,
    value: CLIENT_HEIGHT,
  });
});

afterEach(() => {
  Reflect.deleteProperty(document.documentElement, 'clientHeight');
});

describe('useFitPaneToViewport', () => {
  it('computes maxHeightPx = clientHeight - paneTopDoc - chromeBelow - gutterPx', () => {
    const { result } = renderHook(() => useFitPaneToViewport({ gutterPx: GUTTER_PX, minPx: MIN_PX }));

    const pane = document.createElement('div');
    // paneTop (document-relative, window.scrollY defaults to 0) = 100.
    pane.getBoundingClientRect = () => rect({ top: 100, bottom: 500 });
    result.current.paneRef.current = pane;
    // chromeBelow = body.bottom (550) - pane.bottom (500) = 50.
    document.body.getBoundingClientRect = () => rect({ bottom: 550 });

    // Re-measure: the hook listens for window resize.
    fireEvent(window, new Event('resize'));

    // available = 800 - 100 - 50 - 8 = 642.
    expect(result.current.maxHeightPx).toBe(642);
  });

  it('never drops below minPx even when the computed available space is smaller', () => {
    const { result } = renderHook(() => useFitPaneToViewport({ gutterPx: GUTTER_PX, minPx: MIN_PX }));

    Object.defineProperty(document.documentElement, 'clientHeight', {
      configurable: true,
      value: 200,
    });
    const pane = document.createElement('div');
    pane.getBoundingClientRect = () => rect({ top: 100, bottom: 150 });
    result.current.paneRef.current = pane;
    document.body.getBoundingClientRect = () => rect({ bottom: 200 });

    fireEvent(window, new Event('resize'));

    // available = 200 - 100 - 50 - 8 = 42, floored at minPx (160).
    expect(result.current.maxHeightPx).toBe(MIN_PX);
  });

  it('returns null before the pane ref is attached (pane not mounted)', () => {
    const { result } = renderHook(() => useFitPaneToViewport({ gutterPx: GUTTER_PX, minPx: MIN_PX }));
    expect(result.current.maxHeightPx).toBeNull();

    // Even a resize event is a no-op with nothing attached to the ref.
    fireEvent(window, new Event('resize'));
    expect(result.current.maxHeightPx).toBeNull();
  });
});

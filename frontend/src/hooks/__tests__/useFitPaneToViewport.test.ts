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
 * `.ts` (not `.tsx`, per the plan's file list) — no JSX literals, so DOM
 * nodes are built with `React.createElement` instead.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { render, cleanup, fireEvent, screen } from '@testing-library/react';
import { useFitPaneToViewport } from '../useFitPaneToViewport';
import type { FitPaneToViewport, FitPaneToViewportOptions } from '../useFitPaneToViewport';

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

let latestResult: FitPaneToViewport | null = null;

function Harness({ options }: { options: FitPaneToViewportOptions }): ReactElement {
  const result = useFitPaneToViewport(options);
  latestResult = result;
  return createElement('div', { ref: result.paneRef, 'data-testid': 'pane' });
}

function HarnessNoPane({ options }: { options: FitPaneToViewportOptions }): ReactElement | null {
  const result = useFitPaneToViewport(options);
  latestResult = result;
  return null;
}

beforeEach(() => {
  latestResult = null;
  Object.defineProperty(document.documentElement, 'clientHeight', {
    configurable: true,
    value: CLIENT_HEIGHT,
  });
});

afterEach(() => {
  cleanup();
  Reflect.deleteProperty(document.documentElement, 'clientHeight');
});

describe('useFitPaneToViewport', () => {
  it('computes maxHeightPx = clientHeight - paneTopDoc - chromeBelow - gutterPx', () => {
    render(createElement(Harness, { options: { gutterPx: GUTTER_PX, minPx: MIN_PX } }));
    const pane = screen.getByTestId('pane');

    // paneTop (document-relative, window.scrollY defaults to 0) = 100.
    pane.getBoundingClientRect = () => rect({ top: 100, bottom: 500 });
    // chromeBelow = body.bottom (550) - pane.bottom (500) = 50.
    document.body.getBoundingClientRect = () => rect({ bottom: 550 });

    // Re-measure: the hook listens for window resize.
    fireEvent(window, new Event('resize'));

    // available = 800 - 100 - 50 - 8 = 642.
    expect(latestResult?.maxHeightPx).toBe(642);
  });

  it('never drops below minPx even when the computed available space is smaller', () => {
    render(createElement(Harness, { options: { gutterPx: GUTTER_PX, minPx: MIN_PX } }));
    const pane = screen.getByTestId('pane');

    Object.defineProperty(document.documentElement, 'clientHeight', {
      configurable: true,
      value: 200,
    });
    pane.getBoundingClientRect = () => rect({ top: 100, bottom: 150 });
    document.body.getBoundingClientRect = () => rect({ bottom: 200 });

    fireEvent(window, new Event('resize'));

    // available = 200 - 100 - 50 - 8 = 42, floored at minPx (160).
    expect(latestResult?.maxHeightPx).toBe(MIN_PX);
  });

  it('returns null before the pane ref is attached (pane not mounted)', () => {
    render(createElement(HarnessNoPane, { options: { gutterPx: GUTTER_PX, minPx: MIN_PX } }));
    expect(latestResult?.maxHeightPx).toBeNull();

    // Even a resize event is a no-op with nothing mounted.
    fireEvent(window, new Event('resize'));
    expect(latestResult?.maxHeightPx).toBeNull();
  });
});

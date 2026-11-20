// @vitest-environment jsdom
/** The Flaws Timeline: the 257 D-17 facepalm band inside the Blunders area, its tooltip line and toggle. */
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';

const mocks = vi.hoisted(() => ({ trackFeature: vi.fn() }));

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver; in jsdom the parent
// has zero size and the chart refuses to render. Stub it with a fixed-size wrapper (same
// pattern as EndgameClockDiffOverTimeChart.test.tsx).
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <div style={{ width: 800, height: 400 }}>
        {isValidElement(children)
          ? cloneElement(children as ReactElement<{ width?: number; height?: number }>, {
              width: 800,
              height: 400,
            })
          : children}
      </div>
    ),
  };
});

vi.mock('@/lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/analytics')>()),
  trackFeature: mocks.trackFeature,
}));

import { FlawTrendChart, TrendTooltipBody } from '../FlawTrendChart';
import { toChartPoint } from '../flawTrendBands';
import { makeTrendPoint } from '../stats/__tests__/flawStatsFixtures';

beforeAll(() => {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  mocks.trackFeature.mockReset();
});

const NO_HIDDEN = new Set<never>();

/** A trend point as a backend without the facepalm fields sends it (mid-deploy). */
function makeLegacyTrendPoint() {
  const point = makeTrendPoint('2026-03-02');
  delete point.facepalm_rate;
  delete point.facepalm_share;
  return point;
}

describe('toChartPoint', () => {
  it('splits the Blunders rate into a facepalm band and the rest, summing to the line', () => {
    const point = toChartPoint(makeTrendPoint('2026-03-02', { blunder_rate: 5, facepalm_rate: 1.25 }));
    expect(point.facepalm_band).toBe(1.25);
    expect(point.other_band).toBe(3.75);
    expect((point.facepalm_band ?? 0) + (point.other_band ?? 0)).toBe(point.blunder_rate);
  });

  it('floors the upper band at zero when the facepalm rate pokes above the line', () => {
    const point = toChartPoint(makeTrendPoint('2026-03-02', { blunder_rate: 1, facepalm_rate: 1.1 }));
    expect(point.other_band).toBe(0);
  });

  it('leaves both bands out where the rate is null (too few scored blunders)', () => {
    const point = toChartPoint(makeTrendPoint('2026-03-02', { facepalm_rate: null, facepalm_share: null }));
    expect(point.facepalm_band).toBeUndefined();
    expect(point.other_band).toBeUndefined();
  });

  it('leaves both bands out where the facepalm fields are absent (older backend)', () => {
    const legacy = makeLegacyTrendPoint();
    const point = toChartPoint(legacy);
    expect(point.facepalm_band).toBeUndefined();
    expect(point.other_band).toBeUndefined();
  });
});

describe('TrendTooltipBody', () => {
  it('shows the facepalm rate and its share of blunders right under the Blunders line', () => {
    render(
      <TrendTooltipBody point={makeTrendPoint('2026-03-02')} label="2026-03-02" hiddenKeys={NO_HIDDEN} />,
    );
    const blunders = screen.getByText('Blunders: 5.00 / 100');
    const facepalm = screen.getByText('Facepalm: 1.25 / 100 (25% of blunders)');
    const mistakes = screen.getByText('Mistakes: 7.00 / 100');
    expect(blunders.compareDocumentPosition(facepalm) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(facepalm.compareDocumentPosition(mistakes) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('drops the share when there is none, and the whole line without a rate', () => {
    render(
      <TrendTooltipBody
        point={makeTrendPoint('2026-03-02', { facepalm_share: null })}
        label="2026-03-02"
        hiddenKeys={NO_HIDDEN}
      />,
    );
    expect(screen.getByText('Facepalm: 1.25 / 100')).not.toBeNull();
    cleanup();
    render(
      <TrendTooltipBody
        point={makeTrendPoint('2026-03-02', { facepalm_rate: null, facepalm_share: null })}
        label="2026-03-02"
        hiddenKeys={NO_HIDDEN}
      />,
    );
    expect(screen.queryByText(/^Facepalm/)).toBeNull();
  });

  it('renders without the facepalm line when the fields are absent (older backend)', () => {
    const legacy = makeLegacyTrendPoint();
    render(<TrendTooltipBody point={legacy} label="2026-03-02" hiddenKeys={NO_HIDDEN} />);
    expect(screen.getByText('Blunders: 5.00 / 100')).not.toBeNull();
    expect(screen.queryByText(/^Facepalm/)).toBeNull();
  });

  it('hides the facepalm line with the Facepalm or the Blunders legend entry', () => {
    for (const hidden of ['facepalm', 'blunder_rate'] as const) {
      render(
        <TrendTooltipBody
          point={makeTrendPoint('2026-03-02')}
          label="2026-03-02"
          hiddenKeys={new Set([hidden])}
        />,
      );
      expect(screen.queryByText(/^Facepalm/)).toBeNull();
      cleanup();
    }
  });
});

describe('FlawTrendChart', () => {
  const TREND = [makeTrendPoint('2026-03-02'), makeTrendPoint('2026-03-09')];

  it('turns the Facepalm legend entry off and inert while Blunders is hidden', () => {
    render(<FlawTrendChart trend={TREND} windowSize={100} />);
    const facepalm = screen.getByTestId('flaw-trend-legend-facepalm') as HTMLButtonElement;
    const blunders = screen.getByTestId('flaw-trend-legend-blunder_rate');
    fireEvent.click(blunders);
    expect(facepalm.getAttribute('aria-pressed')).toBe('false');
    expect(facepalm.disabled).toBe(true);
    // Showing Blunders again restores the entry's own (shown) state.
    fireEvent.click(blunders);
    expect(facepalm.getAttribute('aria-pressed')).toBe('true');
    expect(facepalm.disabled).toBe(false);
  });

  it('leads the legend with Facepalm (severity order), shown by default, and tracks its toggle', () => {
    render(<FlawTrendChart trend={TREND} windowSize={100} />);
    const legend = screen.getByTestId('flaw-trend-legend-facepalm');
    const blunders = screen.getByTestId('flaw-trend-legend-blunder_rate');
    expect(legend.previousElementSibling).toBeNull();
    expect(legend.nextElementSibling).toBe(blunders);
    expect(legend.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(legend);
    expect(legend.getAttribute('aria-pressed')).toBe('false');
    expect(mocks.trackFeature).toHaveBeenCalledWith('toggle', {
      target: 'flaw-trend-legend',
      value: 'off',
    });
  });

  it('hides Mistakes and Inaccuracies by default and keeps Blunders shown', () => {
    render(<FlawTrendChart trend={TREND} windowSize={100} />);
    const pressed = (key: string) =>
      screen.getByTestId(`flaw-trend-legend-${key}`).getAttribute('aria-pressed');
    expect(pressed('blunder_rate')).toBe('true');
    expect(pressed('mistake_rate')).toBe('false');
    expect(pressed('inaccuracy_rate')).toBe('false');
  });

  it('explains facepalm blunders and the training in the header popover', () => {
    render(<FlawTrendChart trend={TREND} windowSize={100} />);
    fireEvent.click(screen.getByTestId('flaw-trend-facepalm-info'));
    expect(screen.getByText(/^The darker band shows facepalm blunders/).textContent).toBe(
      'The darker band shows facepalm blunders: blunders that should have been easy to see for a player at your level (facepalm score of 70% or more). Blunder Check trains you to spot them before you move.',
    );
  });
});

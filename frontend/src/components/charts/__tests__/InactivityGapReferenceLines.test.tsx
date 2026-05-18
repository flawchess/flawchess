// @vitest-environment jsdom
/**
 * Unit and render tests for the shared inactivityGapReferenceLines helper (SC-4).
 *
 * Pure cases (empty/single/short arrays) assert on the returned array length
 * directly without mounting. Render cases mount a minimal ComposedChart and
 * assert on data-testid anchors so the tests stay independent of lucide's
 * internal class names and Recharts' SVG internals.
 */
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver;
// in jsdom the parent has zero dimensions so the inner chart refuses to render
// and downstream queries fail. Swap it for a fixed-size wrapper that injects
// explicit width/height into the chart child so Recharts skips its sizing guard.
// (Same pattern as EndgameScoreOverTimeChart.test.tsx.)
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

import { ComposedChart, XAxis, YAxis } from 'recharts';
import { inactivityGapReferenceLines } from '../InactivityGapReferenceLines';

beforeAll(() => {
  // jsdom ships without window.matchMedia; stub it before any render.
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
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
});

// ---------------------------------------------------------------------------
// Pure / unit cases: no rendering needed
// ---------------------------------------------------------------------------

describe('inactivityGapReferenceLines — pure cases', () => {
  it('returns [] for empty dates', () => {
    expect(inactivityGapReferenceLines({ dates: [] }).length).toBe(0);
  });

  it('returns [] for a single date (no pair)', () => {
    expect(inactivityGapReferenceLines({ dates: ['2024-01-01'] }).length).toBe(0);
  });

  it('returns [] when all consecutive pairs are <= 56 days apart', () => {
    const dates = ['2024-01-01', '2024-01-08', '2024-02-01', '2024-02-15'];
    expect(inactivityGapReferenceLines({ dates }).length).toBe(0);
  });

  it('returns one element for exactly one >56-day gap', () => {
    const dates = ['2024-01-01', '2024-03-01']; // 60 days apart
    expect(inactivityGapReferenceLines({ dates }).length).toBe(1);
  });

  it('returns two elements for two >56-day gaps', () => {
    const dates = ['2024-01-01', '2024-03-01', '2024-06-01']; // 60 + 92 days
    expect(inactivityGapReferenceLines({ dates }).length).toBe(2);
  });

  it('returned elements have stable React keys derived from gap.afterIndex', () => {
    const dates = ['2024-01-01', '2024-03-01']; // gap at afterIndex=0
    const elements = inactivityGapReferenceLines({ dates });
    expect(elements.length).toBe(1);
    // React key is set as a prop — accessible via element.key
    expect(elements[0]?.key).toBe('inactivity-gap-0');
  });
});

// ---------------------------------------------------------------------------
// Render cases: mount a minimal chart and assert on data-testid anchors
// ---------------------------------------------------------------------------

/** Build a chart data array from an array of date strings (score is irrelevant for gap tests). */
function makeChartData(dates: string[]): { date: string; value: number }[] {
  return dates.map((date) => ({ date, value: 50 }));
}

/** Fixture with a >56-day gap between index 0 and 1 (60 days). */
const GAP_DATES = ['2024-01-01', '2024-03-01', '2024-03-08'];

/** Fixture where all consecutive pairs are 7 days apart — no gap. */
const NO_GAP_DATES = ['2024-01-01', '2024-01-08', '2024-01-15', '2024-01-22'];

describe('inactivityGapReferenceLines — render cases (no yAxisId)', () => {
  it('renders data-testid="inactivity-gap-label" for a gap fixture', () => {
    const { container } = render(
      <ComposedChart width={800} height={400} data={makeChartData(GAP_DATES)}>
        <XAxis dataKey="date" />
        <YAxis />
        {inactivityGapReferenceLines({ dates: GAP_DATES })}
      </ComposedChart>,
    );
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders data-testid="inactivity-gap-glyph" (Palmtree icon) for a gap fixture', () => {
    const { container } = render(
      <ComposedChart width={800} height={400} data={makeChartData(GAP_DATES)}>
        <XAxis dataKey="date" />
        <YAxis />
        {inactivityGapReferenceLines({ dates: GAP_DATES })}
      </ComposedChart>,
    );
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).not.toBeNull();
  });

  it('renders a label text containing the ≈ inactive string for a gap fixture', () => {
    render(
      <ComposedChart width={800} height={400} data={makeChartData(GAP_DATES)}>
        <XAxis dataKey="date" />
        <YAxis />
        {inactivityGapReferenceLines({ dates: GAP_DATES })}
      </ComposedChart>,
    );
    // computeInactivityGaps labels gaps < 365 days as "≈Nmo inactive"
    expect(screen.getByText(/≈.*inactive/)).toBeTruthy();
  });

  it('renders no gap label for a gap-free fixture', () => {
    const { container } = render(
      <ComposedChart width={800} height={400} data={makeChartData(NO_GAP_DATES)}>
        <XAxis dataKey="date" />
        <YAxis />
        {inactivityGapReferenceLines({ dates: NO_GAP_DATES })}
      </ComposedChart>,
    );
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).toBeNull();
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).toBeNull();
  });
});

describe('inactivityGapReferenceLines — yAxisId forwarding', () => {
  it('yAxisId prop is forwarded to the returned ReferenceLine element', () => {
    const dates = ['2024-01-01', '2024-03-01'];
    const elements = inactivityGapReferenceLines({ dates, yAxisId: 'elo' });
    expect(elements.length).toBe(1);
    // The yAxisId prop should be present on the ReactElement props
    const props = elements[0]?.props as { yAxisId?: string } | undefined;
    expect(props?.yAxisId).toBe('elo');
  });

  it('yAxisId is absent from the ReferenceLine element when not provided', () => {
    const dates = ['2024-01-01', '2024-03-01'];
    const elements = inactivityGapReferenceLines({ dates });
    expect(elements.length).toBe(1);
    const props = elements[0]?.props as { yAxisId?: string } | undefined;
    expect(props?.yAxisId).toBeUndefined();
  });
});

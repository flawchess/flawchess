// @vitest-environment jsdom
/**
 * Regression tests for RatingChart.
 *
 * 1. Inactivity-gap annotation (SC-4 Task 3): Palmtree break annotation for >90-day
 *    gaps, no-op for gap-free fixtures, and out-of-order date handling.
 *
 * 2. Empty-series omission (#260606-jvg Task 1): series and legend entries for TCs
 *    with no data points are omitted; filter prop (enabledTimeControls) still wins
 *    even when data for the filtered TC exists.
 */
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';

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

import { RatingChart } from '../RatingChart';
import type { RatingDataPoint } from '@/types/stats';

beforeAll(() => {
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

function makePoint(date: string, rating: number = 1500, tc: RatingDataPoint['time_control_bucket'] = 'blitz'): RatingDataPoint {
  return { date, rating, time_control_bucket: tc };
}

/** Dates with a >90-day gap between index 0 and 1 (121 days). */
const GAP_DATA: RatingDataPoint[] = [
  makePoint('2024-01-01', 1500),
  makePoint('2024-05-01', 1510), // 121 days — exceeds threshold
  makePoint('2024-05-08', 1520),
];

/** Dates with all consecutive pairs 7 days apart — no gap. */
const NO_GAP_DATA: RatingDataPoint[] = [
  makePoint('2024-01-01', 1500),
  makePoint('2024-01-08', 1505),
  makePoint('2024-01-15', 1510),
  makePoint('2024-01-22', 1515),
];

/** Dates that arrive out of order — the defensive sort must handle this. */
const OUT_OF_ORDER_GAP_DATA: RatingDataPoint[] = [
  makePoint('2024-05-01', 1510),
  makePoint('2024-01-01', 1500), // earlier date listed second
  makePoint('2024-05-08', 1520),
];

describe('RatingChart inactivity gap annotations', () => {
  it('renders inactivity-gap-label for a >90-day gap fixture', () => {
    const { container } = render(<RatingChart data={GAP_DATA} platform="chess.com" />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders inactivity-gap-glyph (Palmtree) for a >90-day gap fixture', () => {
    const { container } = render(<RatingChart data={GAP_DATA} platform="chess.com" />);
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).not.toBeNull();
  });

  it('renders no inactivity-gap annotation for a gap-free fixture', () => {
    const { container } = render(<RatingChart data={NO_GAP_DATA} platform="lichess" />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).toBeNull();
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).toBeNull();
  });

  it('renders empty-state message for empty data (no crash, no annotation)', () => {
    render(<RatingChart data={[]} platform="chess.com" />);
    expect(screen.getByText(/No chess\.com games imported/i)).toBeTruthy();
  });

  it('renders annotation when input dates arrive out of order (defensive sort)', () => {
    // The defensive sort in sortedGapDates must reorder the dates so the 121-day
    // gap between 2024-01-01 and 2024-05-01 is detected by computeInactivityGaps.
    // Without the sort, the earliest date second would compute a negative gap and
    // miss the annotation.
    const { container } = render(
      <RatingChart data={OUT_OF_ORDER_GAP_DATA} platform="lichess" />,
    );
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });
});

// ── Empty-series omission (#260606-jvg Task 1) ─────────────────────────────

/** Blitz and Rapid data only — no Bullet or Classical points. */
const BLITZ_RAPID_DATA: RatingDataPoint[] = [
  makePoint('2024-01-01', 1500, 'blitz'),
  makePoint('2024-01-08', 1510, 'blitz'),
  makePoint('2024-01-01', 1600, 'rapid'),
  makePoint('2024-01-08', 1610, 'rapid'),
];

/** All four TCs present. */
const ALL_TC_DATA: RatingDataPoint[] = [
  makePoint('2024-01-01', 1200, 'bullet'),
  makePoint('2024-01-01', 1500, 'blitz'),
  makePoint('2024-01-01', 1600, 'rapid'),
  makePoint('2024-01-01', 1800, 'classical'),
];

describe('RatingChart empty-series omission', () => {
  it('omits Bullet Line when no bullet data points exist', () => {
    const { container } = render(<RatingChart data={BLITZ_RAPID_DATA} platform="chess.com" />);
    // recharts adds class "recharts-line" to each rendered Line group; the count
    // must equal the number of TCs with data (2: blitz, rapid).
    const lines = container.querySelectorAll('.recharts-line');
    expect(lines.length).toBe(2);
  });

  it('renders Blitz and Rapid Lines when only blitz/rapid data exists', () => {
    const { container } = render(<RatingChart data={BLITZ_RAPID_DATA} platform="lichess" />);
    const lines = container.querySelectorAll('.recharts-line');
    expect(lines.length).toBe(2);
  });

  it('filter prop wins: bullet data present but enabledTimeControls=["blitz"] omits bullet Line', () => {
    const { container } = render(
      <RatingChart data={ALL_TC_DATA} platform="chess.com" enabledTimeControls={['blitz']} />,
    );
    const lines = container.querySelectorAll('.recharts-line');
    expect(lines.length).toBe(1);
  });

  it('renders all four Lines when all TCs have data and no filter', () => {
    const { container } = render(<RatingChart data={ALL_TC_DATA} platform="chess.com" />);
    const lines = container.querySelectorAll('.recharts-line');
    expect(lines.length).toBe(4);
  });

  it('renders all four Lines when enabledTimeControls is null (all enabled)', () => {
    const { container } = render(
      <RatingChart data={ALL_TC_DATA} platform="chess.com" enabledTimeControls={null} />,
    );
    const lines = container.querySelectorAll('.recharts-line');
    expect(lines.length).toBe(4);
  });
});

// @vitest-environment jsdom
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';
import type { ClockDiffTimelinePoint } from '@/types/endgames';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver;
// in jsdom the parent has zero dimensions so the inner chart refuses to render
// and downstream queries fail. Stub it with a fixed-size wrapper that injects
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

import { EndgameClockDiffOverTimeChart } from '../EndgameClockDiffOverTimeChart';

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

function makePoint(
  date: string,
  avg_clock_diff_pct: number,
  opts: { game_count?: number; per_week_game_count?: number } = {},
): ClockDiffTimelinePoint {
  return {
    date,
    avg_clock_diff_pct,
    game_count: opts.game_count ?? 10,
    per_week_game_count: opts.per_week_game_count ?? 3,
  };
}

const THREE_POINT_FIXTURE: ClockDiffTimelinePoint[] = [
  makePoint('2025-01-06', 10.0, { game_count: 5, per_week_game_count: 5 }),
  makePoint('2025-01-13', -5.0, { game_count: 12, per_week_game_count: 7 }),
  makePoint('2025-01-20', 2.5, { game_count: 18, per_week_game_count: 6 }),
];

describe('EndgameClockDiffOverTimeChart', () => {
  it('returns null on empty timeline', () => {
    const { container } = render(<EndgameClockDiffOverTimeChart timeline={[]} />);
    // No content rendered for empty input — the page-level integration also
    // guards on empty, this is belt-and-suspenders.
    expect(container.querySelector('[data-testid="clock-diff-over-time-chart"]')).toBeNull();
  });

  it('renders the chart container and title for non-empty timeline', () => {
    render(<EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />);
    expect(screen.getByTestId('clock-diff-over-time-chart')).toBeTruthy();
    expect(screen.getByText('Average Clock Difference over Time')).toBeTruthy();
  });

  it('renders one bar rectangle per timeline entry', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    // Recharts emits one <rect> per Bar datum inside the <Bar> SVG layer.
    // We use a stable class on the Bar layer to anchor the count.
    const bars = container.querySelectorAll('.recharts-bar-rectangle');
    expect(bars.length).toBe(THREE_POINT_FIXTURE.length);
  });

  it('renders Y axis tick labels at −30, 0, +30', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    // Recharts renders tick labels as <text> nodes inside .recharts-cartesian-axis-tick.
    // The fixed Y domain pins these three ticks for the line chart Y axis.
    const tickTexts = Array.from(
      container.querySelectorAll('.recharts-yAxis .recharts-cartesian-axis-tick-value'),
    )
      .map((n) => n.textContent ?? '')
      .map((s) => s.replace(/\s/g, ''));
    expect(tickTexts).toEqual(expect.arrayContaining(['-30%', '0%', '30%']));
  });

  it('renders the InfoPopover trigger with the correct aria-label', () => {
    render(<EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />);
    // The trigger is button-shaped and reachable by aria-label.
    expect(
      screen.getByLabelText('Average clock difference over time info'),
    ).toBeTruthy();
  });

  it('renders zone-tinted ReferenceArea bands for above/below thresholds', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    // Recharts ReferenceArea renders SVG <rect> elements with class
    // .recharts-reference-area-rect. With two bands (one above the neutral
    // threshold, one below the negated threshold) we expect 2 rects total.
    const bands = container.querySelectorAll('.recharts-reference-area-rect');
    expect(bands.length).toBe(2);
  });
});

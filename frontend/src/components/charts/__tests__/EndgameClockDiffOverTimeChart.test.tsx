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

  it('does not clip values outside the ±30% Y envelope (REVIEW.md WR-02)', () => {
    // Real rapid/classical users can legitimately exceed ±30%; the previous
    // `allowDataOverflow={false}` silently flattened those points to the axis
    // edge. With overflow allowed, the line plot still emits a dot whose
    // Y-coordinate is computed proportionally to the out-of-band value — it
    // ends up rendered above the visible viewbox rather than pinned at +30%.
    const OVERFLOW_FIXTURE: ClockDiffTimelinePoint[] = [
      makePoint('2025-01-06', 10.0, { game_count: 5, per_week_game_count: 5 }),
      // 42% is well outside the ±30% envelope.
      makePoint('2025-01-13', 42.0, { game_count: 12, per_week_game_count: 7 }),
      makePoint('2025-01-20', 2.5, { game_count: 18, per_week_game_count: 6 }),
    ];
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={OVERFLOW_FIXTURE} />,
    );
    // Recharts emits one <circle> dot per Line datum at class .recharts-line-dot.
    // All three should render — none silently dropped.
    const dots = container.querySelectorAll('.recharts-line-dot');
    expect(dots.length).toBe(OVERFLOW_FIXTURE.length);
    // The 42% point should not share the same Y-coord as the +30% Y-tick.
    // We extract the second dot (the 42% one — Recharts orders by data index)
    // and the +30% tick text and confirm the dot's cy is strictly less than
    // the +30% tick's y (smaller cy = higher on the SVG canvas = above the
    // visible band, exactly what allowDataOverflow={true} permits).
    const dot42 = dots[1] as SVGCircleElement;
    const tick30 = Array.from(
      container.querySelectorAll('.recharts-yAxis .recharts-cartesian-axis-tick'),
    ).find((el) => (el.textContent ?? '').replace(/\s/g, '') === '30%');
    expect(dot42).toBeTruthy();
    expect(tick30).toBeTruthy();
    const dotCy = parseFloat(dot42.getAttribute('cy') ?? 'NaN');
    const tickY = parseFloat(
      tick30!.querySelector('text')?.getAttribute('y') ?? 'NaN',
    );
    // Both must be finite numbers, and the 42% dot must sit above the +30%
    // tick (smaller y in SVG coordinate space).
    expect(Number.isFinite(dotCy)).toBe(true);
    expect(Number.isFinite(tickY)).toBe(true);
    expect(dotCy).toBeLessThan(tickY);
  });
});

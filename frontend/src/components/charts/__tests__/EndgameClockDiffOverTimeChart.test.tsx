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
    expect(screen.getByText('Clock Gap at Endgame Entry')).toBeTruthy();
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

  it('renders Y axis tick labels at −30, 0, +30 (signed for positives)', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    // Recharts renders tick labels as <text> nodes inside .recharts-cartesian-axis-tick.
    // The Y domain pins ticks at every 10% across [-30, +30]; positives are
    // signed (+10%, +20%, +30%) per the tick formatter.
    const tickTexts = Array.from(
      container.querySelectorAll('.recharts-yAxis .recharts-cartesian-axis-tick-value'),
    )
      .map((n) => n.textContent ?? '')
      .map((s) => s.replace(/\s/g, ''));
    expect(tickTexts).toEqual(expect.arrayContaining(['-30%', '0%', '+30%']));
  });

  it('renders the InfoPopover trigger with the correct aria-label', () => {
    render(<EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />);
    // The trigger is button-shaped and reachable by aria-label.
    expect(
      screen.getByLabelText('Clock gap at endgame entry info'),
    ).toBeTruthy();
  });

  it('renders three zone-tinted ReferenceArea bands (danger / neutral / success)', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    // Post-UAT: the neutral middle band (blue) was missing from the first
    // restore pass. Now we render three bands — danger (below -threshold),
    // neutral (within ±threshold), success (above +threshold). Recharts emits
    // one SVG rect per ReferenceArea at .recharts-reference-area-rect.
    const bands = container.querySelectorAll('.recharts-reference-area-rect');
    expect(bands.length).toBe(3);
  });

  it('expands Y domain to include values outside the ±30% envelope', () => {
    // Real rapid/classical users can legitimately exceed ±30%. Instead of
    // `allowDataOverflow={true}` (which keeps the +30 tick at the edge and
    // lets the dot escape), we expand the domain so the axis itself includes
    // the outlier. The point still renders inside the visible viewbox.
    const OVERFLOW_FIXTURE: ClockDiffTimelinePoint[] = [
      makePoint('2025-01-06', 10.0, { game_count: 5, per_week_game_count: 5 }),
      // 42% is well outside the ±30% baseline envelope.
      makePoint('2025-01-13', 42.0, { game_count: 12, per_week_game_count: 7 }),
      makePoint('2025-01-20', 2.5, { game_count: 18, per_week_game_count: 6 }),
    ];
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={OVERFLOW_FIXTURE} />,
    );
    // All three dots are emitted via a custom `dot` render function returning
    // raw <circle> elements. Locate them via the chart line layer.
    const dots = container.querySelectorAll('.recharts-line circle');
    expect(dots.length).toBe(OVERFLOW_FIXTURE.length);
    // The 42% dot sits above the +30% tick (smaller cy = higher on the SVG
    // canvas), proving the domain expanded to admit it.
    const dot42 = dots[1] as SVGCircleElement;
    const tick30 = Array.from(
      container.querySelectorAll('.recharts-yAxis .recharts-cartesian-axis-tick'),
    ).find((el) => (el.textContent ?? '').replace(/\s/g, '') === '+30%');
    expect(dot42).toBeTruthy();
    expect(tick30).toBeTruthy();
    const dotCy = parseFloat(dot42.getAttribute('cy') ?? 'NaN');
    const tickY = parseFloat(
      tick30!.querySelector('text')?.getAttribute('y') ?? 'NaN',
    );
    expect(Number.isFinite(dotCy)).toBe(true);
    expect(Number.isFinite(tickY)).toBe(true);
    expect(dotCy).toBeLessThan(tickY);
  });

  it('uses a white line stroke', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    // Post-UAT: the visible line uses a white stroke; per-point dots carry
    // the zone color. Recharts emits the Line's path under .recharts-line-curve.
    const linePath = container.querySelector('.recharts-line-curve');
    expect(linePath).not.toBeNull();
    expect(linePath?.getAttribute('stroke')).toBe('white');
  });

  it('renders the vertical "Clock Gap" Y-axis label on desktop', () => {
    // matchMedia is stubbed to always return matches=false → desktop path.
    render(<EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />);
    // The label is plain HTML text rotated via CSS, so screen.getByText works.
    expect(screen.getByText('Clock Gap')).toBeTruthy();
  });
});

describe('EndgameClockDiffOverTimeChart — inactivity gap annotations', () => {
  /** Timeline with a >56-day gap between index 0 and 1 (90 days). */
  const GAP_FIXTURE: ClockDiffTimelinePoint[] = [
    makePoint('2025-01-06', 5.0),
    makePoint('2025-04-06', 3.0), // 90 days later — exceeds the 56-day threshold
    makePoint('2025-04-13', 2.0),
  ];

  /** Timeline with all consecutive points 7 days apart — no gap. */
  const NO_GAP_FIXTURE: ClockDiffTimelinePoint[] = [
    makePoint('2025-01-06', 5.0),
    makePoint('2025-01-13', 3.0),
    makePoint('2025-01-20', 2.0),
    makePoint('2025-01-27', 1.0),
  ];

  it('renders inactivity-gap-label for a >56-day gap fixture', () => {
    const { container } = render(<EndgameClockDiffOverTimeChart timeline={GAP_FIXTURE} />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders inactivity-gap-glyph (Palmtree) for a >56-day gap fixture', () => {
    const { container } = render(<EndgameClockDiffOverTimeChart timeline={GAP_FIXTURE} />);
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).not.toBeNull();
  });

  it('renders no inactivity-gap annotation for a gap-free fixture', () => {
    const { container } = render(<EndgameClockDiffOverTimeChart timeline={NO_GAP_FIXTURE} />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).toBeNull();
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).toBeNull();
  });

  it('the y=0 baseline ReferenceLine still renders alongside the gap annotation (no regression)', () => {
    // The existing y=0 baseline is a horizontal reference line; the gap annotations
    // are vertical x= lines. They are independent and must coexist.
    const { container } = render(<EndgameClockDiffOverTimeChart timeline={GAP_FIXTURE} />);
    // y=0 baseline: look for recharts-reference-line elements — there should be at
    // least 2: one horizontal baseline + one vertical gap line
    const refLines = container.querySelectorAll('.recharts-reference-line');
    expect(refLines.length).toBeGreaterThanOrEqual(2);
  });
});

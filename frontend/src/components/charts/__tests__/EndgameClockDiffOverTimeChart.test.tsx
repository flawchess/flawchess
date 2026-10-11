// @vitest-environment jsdom
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
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

import {
  ClockGapTooltipContent,
  EndgameClockDiffOverTimeChart,
  computeYDomain,
} from '../EndgameClockDiffOverTimeChart';
import {
  NEUTRAL_SERIES_COLOR,
  TYPICAL_BAND_FILL,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from '@/lib/theme';
import { NEUTRAL_PCT_THRESHOLD } from '@/generated/endgameZones';

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
    // recharts 3: tick labels are rendered in a separate zIndex layer (recharts-zIndex-layer_2000)
    // as children of recharts-yAxis-tick-labels, NOT as children of .recharts-yAxis.
    // The Y domain pins ticks at every 10% across [-30, +30]; positives are
    // signed (+10%, +20%, +30%) per the tick formatter.
    const tickTexts = Array.from(
      container.querySelectorAll('.recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value'),
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

  it('renders exactly one grey typical-band ReferenceArea (D-00f)', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    const bands = container.querySelectorAll('.recharts-reference-area-rect');
    expect(bands.length, 'one typical band instead of three zone bands').toBe(1);
    expect(bands[0]?.getAttribute('fill')).toBe(TYPICAL_BAND_FILL);
  });

  it('the typical band spans ±NEUTRAL_PCT_THRESHOLD around zero', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    const band = container.querySelector<SVGRectElement>('.recharts-reference-area-rect');
    expect(band, 'band rect present').not.toBeNull();
    const bandHeight = parseFloat(band?.getAttribute('height') ?? '0');
    // Horizontal grid lines sit on the ticks -30..+30, so their pixel span is the 60-point domain.
    const gridYs = Array.from(
      container.querySelectorAll('.recharts-cartesian-grid-horizontal line'),
    ).map((line) => parseFloat(line.getAttribute('y1') ?? '0'));
    const domainPixels = Math.max(...gridYs) - Math.min(...gridYs);
    const domainSpan = 60;
    expect(bandHeight / domainPixels).toBeCloseTo((2 * NEUTRAL_PCT_THRESHOLD) / domainSpan, 2);
  });

  it('expands Y domain to include values outside the ±30% envelope', () => {
    // recharts 3 changed how custom dots and tick positions are rendered in jsdom
    // (portals/zIndex layers make SVG pixel-position comparisons impossible without
    // a real browser layout engine). Test the domain-expansion logic via the exported
    // computeYDomain helper instead — this is the actual behavior being guarded.
    // A 42% value must expand the domain past the ±30 baseline.
    expect(computeYDomain([10, 42, 2.5])).toEqual([-30, 42]);
    // Values within the baseline — domain should stay at [-30, 30].
    expect(computeYDomain([10, -5, 2.5])).toEqual([-30, 30]);
    // Values below the baseline — domain should expand downward.
    expect(computeYDomain([-45, 5])).toEqual([-45, 30]);
  });

  it('draws a neutral line with zone-colored dots (238 UAT)', () => {
    const { container } = render(
      <EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />,
    );
    const linePath = container.querySelector('.recharts-line-curve');
    expect(linePath, 'line path present').not.toBeNull();
    expect(linePath?.getAttribute('stroke')).toBe(NEUTRAL_SERIES_COLOR);
    // Fixture holds +10 (above the ±5 band), -5 (on its edge, still typical) and +2.5.
    const dots = Array.from(container.querySelectorAll('.recharts-line-dots circle'));
    expect(dots.length, 'one dot per point').toBe(THREE_POINT_FIXTURE.length);
    expect(dots.map((dot) => dot.getAttribute('fill'))).toEqual([
      ZONE_SUCCESS,
      ZONE_NEUTRAL,
      ZONE_NEUTRAL,
    ]);
  });

  it.each([
    [10, ZONE_SUCCESS],
    [-8, ZONE_DANGER],
    [2.5, ZONE_NEUTRAL],
  ])('tooltip swatch is zone-colored for a %s point', (value, expected) => {
    const { getByTestId } = render(
      <ClockGapTooltipContent
        point={{
          date: '2025-01-06',
          avg_clock_diff_pct: value,
          game_count: 10,
          per_week_game_count: 3,
        }}
        label="2025-01-06"
      />,
    );
    expect(getByTestId('clock-diff-tooltip-swatch').style.backgroundColor).not.toBe('');
    const swatch = getByTestId('clock-diff-tooltip-swatch');
    // jsdom normalizes oklch to its own string; compare with a reference element.
    const reference = document.createElement('div');
    reference.style.backgroundColor = expected;
    expect(swatch.style.backgroundColor).toBe(reference.style.backgroundColor);
  });

  it('the info popover copy describes the grey typical band and the dot colors', () => {
    render(<EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />);
    fireEvent.click(screen.getByLabelText('Clock gap at endgame entry info'));
    const bandCopy = screen.getByText(/grey band marks the typical range/i);
    const popoverCopy = bandCopy.parentElement?.textContent ?? '';
    expect(popoverCopy).toContain('Positive means you arrived with more time left');
    expect(popoverCopy).toMatch(/green above it, red below it and blue inside it/);
  });

  it('renders the vertical "Clock Gap" Y-axis label on desktop', () => {
    // matchMedia is stubbed to always return matches=false → desktop path.
    render(<EndgameClockDiffOverTimeChart timeline={THREE_POINT_FIXTURE} />);
    // The label is plain HTML text rotated via CSS, so screen.getByText works.
    expect(screen.getByText('Clock Gap')).toBeTruthy();
  });
});

describe('EndgameClockDiffOverTimeChart — inactivity gap annotations', () => {
  /** Timeline with a >90-day gap between index 0 and 1 (120 days). */
  const GAP_FIXTURE: ClockDiffTimelinePoint[] = [
    makePoint('2025-01-06', 5.0),
    makePoint('2025-05-06', 3.0), // 120 days later — exceeds the 90-day threshold
    makePoint('2025-05-13', 2.0),
  ];

  /** Timeline with all consecutive points 7 days apart — no gap. */
  const NO_GAP_FIXTURE: ClockDiffTimelinePoint[] = [
    makePoint('2025-01-06', 5.0),
    makePoint('2025-01-13', 3.0),
    makePoint('2025-01-20', 2.0),
    makePoint('2025-01-27', 1.0),
  ];

  it('renders inactivity-gap-label for a >90-day gap fixture', () => {
    const { container } = render(<EndgameClockDiffOverTimeChart timeline={GAP_FIXTURE} />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders inactivity-gap-glyph (Palmtree) for a >90-day gap fixture', () => {
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

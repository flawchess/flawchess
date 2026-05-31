// @vitest-environment jsdom
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';
import type { PressureQuintileBullet } from '@/types/endgames';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver;
// in jsdom the parent has zero dimensions so the inner chart refuses to render
// and downstream queries fail. Stub it with a fixed-size wrapper that injects
// explicit width/height into the chart child so Recharts skips its sizing guard.
// (Same pattern as EndgameClockDiffOverTimeChart.test.tsx.)
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
  ScoreGapByTimePressureChart,
  ScoreGapTooltipContent,
  PRESSURE_SCORE_GAP_NEUTRAL_MIN,
  PRESSURE_SCORE_GAP_NEUTRAL_MAX,
} from '../ScoreGapByTimePressureChart';
import {
  computeScoreGapYAxis,
  type ScoreGapAxisPoint,
} from '@/lib/pressureBulletConfig';

// Minimal axis-point factory — computeScoreGapYAxis only reads delta + ciError.
function pt(delta: number, ciError?: [number, number]): ScoreGapAxisPoint {
  return { delta, ciError };
}

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

function makeBin(
  quintile_index: 0 | 1 | 2 | 3 | 4,
  opts: {
    n?: number;
    n_opp?: number;
    delta?: number;
    ci_low?: number | null;
    ci_high?: number | null;
    opp_score?: number | null;
    p_value?: number | null;
  } = {},
): PressureQuintileBullet {
  const labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'] as const;
  const n = opts.n ?? 40;
  return {
    quintile_index,
    quintile_label: labels[quintile_index]!,
    n,
    n_opp: opts.n_opp ?? n,
    delta: opts.delta ?? 0.0,
    p_value: opts.p_value !== undefined ? opts.p_value : 0.5,
    ci_low: opts.ci_low !== undefined ? opts.ci_low : (n > 0 ? -0.02 : null),
    ci_high: opts.ci_high !== undefined ? opts.ci_high : (n > 0 ? 0.02 : null),
    opp_score: opts.opp_score !== undefined ? opts.opp_score : (n > 0 ? 0.5 : null),
  };
}

// 5 bins Q0..Q4 all with n > 0 — Q4 should be filtered out by the chart.
const FOUR_BIN_FIXTURE: PressureQuintileBullet[] = [
  makeBin(0),
  makeBin(1),
  makeBin(2),
  makeBin(3),
  makeBin(4),
];

describe('ScoreGapByTimePressureChart', () => {
  // Test 1: chart root testid
  it('renders the chart root testid score-gap-by-time-pressure-chart-bullet for tc=bullet', () => {
    render(<ScoreGapByTimePressureChart quintiles={FOUR_BIN_FIXTURE} tc="bullet" />);
    expect(screen.getByTestId('score-gap-by-time-pressure-chart-bullet')).toBeTruthy();
  });

  // Test 2: exactly 3 zone bands
  it('renders exactly 3 zone-band ReferenceArea elements', () => {
    const { container } = render(
      <ScoreGapByTimePressureChart quintiles={FOUR_BIN_FIXTURE} tc="bullet" />,
    );
    const bands = container.querySelectorAll('.recharts-reference-area-rect');
    expect(bands.length).toBe(3);
  });

  // Test 2b: zone bands span the full chart width (recharts 3 regression guard — D-01 Wave 6 UAT)
  //
  // The hidden "bleed" XAxis requires dataKey="__bleed__" in recharts 3 so that
  // combineAxisDomain does NOT fall into the early-return "isCategorical && dataKey==null"
  // branch (which yields range(0, dataLength) instead of the user's [0,1] domain).
  // Without it the bands map x1=0→x2=1 to category indices 0→1 ("10%"→"30%"),
  // coloring only the left third. With it, x1=0 maps to the plot left edge and
  // x2=1 maps to the plot right edge, making the bands full-bleed.
  //
  // We verify: every band rect starts at x<80 (close to the left edge of a 800px
  // mock chart) and has width>600 (covers most of the plot area). This catches a
  // return to the "left-third" regression without testing exact pixel values.
  it('zone bands span the full chart width, not just the left third (recharts 3 bleed-axis fix)', () => {
    const { container } = render(
      <ScoreGapByTimePressureChart quintiles={FOUR_BIN_FIXTURE} tc="bullet" />,
    );
    const bands = container.querySelectorAll<SVGRectElement>('.recharts-reference-area-rect');
    expect(bands.length).toBe(3);
    for (const band of bands) {
      const x = parseFloat(band.getAttribute('x') ?? '0');
      const width = parseFloat(band.getAttribute('width') ?? '0');
      // Band must start near the left edge (x < 80 in an 800px-wide mock chart).
      expect(x).toBeLessThan(80);
      // Band must be wide (>600px) — the "left-third" bug produces ~220px.
      expect(width).toBeGreaterThan(600);
    }
  });

  // Test 3: white line stroke
  it('renders the line with white stroke', () => {
    const { container } = render(
      <ScoreGapByTimePressureChart quintiles={FOUR_BIN_FIXTURE} tc="bullet" />,
    );
    const linePath = container.querySelector('.recharts-line-curve');
    expect(linePath).not.toBeNull();
    expect(linePath?.getAttribute('stroke')).toBe('white');
  });

  // Test 4: 4-bin fixture (Q0..Q4 all n>0) → exactly 4 rendered data dots (Q4 filtered out)
  it('renders exactly 4 dots for a 5-bin fixture where Q4 is filtered out', () => {
    const { container } = render(
      <ScoreGapByTimePressureChart quintiles={FOUR_BIN_FIXTURE} tc="bullet" />,
    );
    // recharts 3: dots are rendered in a separate zIndex layer (recharts-line-dots)
    // as siblings of .recharts-line, not as its descendants. Query .recharts-line-dots.
    const dots = container.querySelectorAll('.recharts-line-dots circle');
    expect(dots.length).toBe(4);
  });

  // Test 5: ErrorBar renders for bins with non-null CI
  it('renders ErrorBar whiskers for bins with non-null CI (4 bins with CI)', () => {
    const { container } = render(
      <ScoreGapByTimePressureChart quintiles={FOUR_BIN_FIXTURE} tc="bullet" />,
    );
    // Recharts ErrorBar renders SVG line elements inside .recharts-errorBar
    const errorBars = container.querySelectorAll('.recharts-errorBar');
    // All 4 visible bins have ci_low/ci_high set, so 4 error bars expected
    expect(errorBars.length).toBe(4);
  });

  // Test 6: zero-n bin omitted — only 3 data dots render and no whisker at that position
  it('omits a zero-n bin from the chart (produces a line gap): 3 dots for fixture with Q1 n=0', () => {
    const sparseFixture: PressureQuintileBullet[] = [
      makeBin(0),
      makeBin(1, { n: 0, ci_low: null, ci_high: null, opp_score: null }),
      makeBin(2),
      makeBin(3),
      makeBin(4),
    ];
    const { container } = render(
      <ScoreGapByTimePressureChart quintiles={sparseFixture} tc="blitz" />,
    );
    // recharts 3: dots are in .recharts-line-dots (separate zIndex layer from .recharts-line)
    const dots = container.querySelectorAll('.recharts-line-dots circle');
    expect(dots.length).toBe(3);
    // ErrorBars only for bins with non-null CI (Q0, Q2, Q3 = 3 error bars)
    const errorBars = container.querySelectorAll('.recharts-errorBar');
    expect(errorBars.length).toBe(3);
  });

  // Test 7: collapsed neutral band constant assertion
  it('exports PRESSURE_SCORE_GAP_NEUTRAL_MIN = -0.06', () => {
    expect(PRESSURE_SCORE_GAP_NEUTRAL_MIN).toBe(-0.06);
  });

  it('exports PRESSURE_SCORE_GAP_NEUTRAL_MAX = 0.06', () => {
    expect(PRESSURE_SCORE_GAP_NEUTRAL_MAX).toBe(0.06);
  });

  // Test 8: tooltip surfaces per-bucket stats — renders the REAL exported
  // production tooltip (no reimplementation). Fixes REVIEW.md IN-01 tautology.
  it('tooltip: range header, two-line You/Opponents split, conclusion, italic test+CI', () => {
    const { getByTestId, getByText } = render(
      <ScoreGapTooltipContent
        point={{
          label: '10%',
          rangeLabel: '0-20%',
          delta: -0.17,
          n: 40,
          n_opp: 37,
          opp_score: 0.55,
          p_value: 0.03,
          ci_low: -0.02,
          ci_high: 0.02,
        }}
      />,
    );
    const tooltip = getByTestId('score-gap-tooltip');
    expect(tooltip).toBeTruthy();
    // Compact text-xs body, matching the Average Clock Gap chart tooltip.
    expect(tooltip.className).toContain('text-xs');
    // Header is the full bucket RANGE, not the axis center value.
    expect(tooltip.textContent).toContain('Time Bucket: 0-20%');
    expect(tooltip.textContent).toContain('Score gap: -17.0%');
    // Two separate lines, each with its own independent game count:
    // userScore = opp_score + delta = 0.55 + (-0.17) = 0.38.
    expect(tooltip.textContent).toContain('You: 38.0% (40 games)');
    expect(tooltip.textContent).toContain('Opp: 55.0% (37 games)');
    expect(tooltip.textContent).not.toContain('n = 40');
    // Conclusion: p=0.03 → medium → "Possibly"; delta ≤ -0.06 → weakness.
    // No confidence-label clause (dropped per UAT) — p-value only.
    expect(tooltip.textContent).toContain(
      'Possibly a real weakness (p = 0.030)',
    );
    expect(tooltip.textContent).not.toContain('confidence');
    // p-value appears exactly once (conclusion line) — NOT repeated in the
    // italic test footnote.
    const testFootnote = getByText('Independent two-sample test.');
    expect(testFootnote.className).toContain('italic');
    expect(testFootnote.textContent).not.toContain('p = ');
    // CI is on its own italic line.
    const ciFootnote = getByText('95% CI [-2.0%, +2.0%]');
    expect(ciFootnote.className).toContain('italic');
    expect(
      tooltip.textContent?.match(/p = 0\.030/g)?.length,
    ).toBe(1);
  });

  it('tooltip degrades gracefully when opp_score / p_value / CI are null', () => {
    const { getByTestId } = render(
      <ScoreGapTooltipContent
        point={{
          label: '30%',
          rangeLabel: '20-40%',
          delta: 0.04,
          n: 7,
          n_opp: 5,
          opp_score: null,
          p_value: null,
          ci_low: null,
          ci_high: null,
        }}
      />,
    );
    const tooltip = getByTestId('score-gap-tooltip');
    expect(tooltip.textContent).toContain('Time Bucket: 20-40%');
    expect(tooltip.textContent).toContain('You: n/a (7 games)');
    expect(tooltip.textContent).toContain('Opp: n/a (5 games)');
    expect(tooltip.textContent).toContain('Score gap: +4.0%');
    // n < 10 gate → low → "Inconclusive", no confidence label, no p segment.
    expect(tooltip.textContent).toContain('Inconclusive');
    expect(tooltip.textContent).not.toContain('confidence');
    expect(tooltip.textContent).not.toContain('p = ');
    // CI falls back to the methodology phrase.
    expect(tooltip.textContent).toContain('95% normal-approx CI');
  });
});

describe('ScoreGapByTimePressureChart — computeScoreGapYAxis (post-UAT 88.4)', () => {
  const approx = (xs: number[]) => xs.map((v) => Math.round(v * 1e6) / 1e6);

  it('keeps the ±30% envelope and 10% ticks when no point clips', () => {
    const { domain, ticks } = computeScoreGapYAxis([pt(-0.17), pt(0.04), pt(0.22)]);
    expect(approx(domain)).toEqual([-0.3, 0.3]);
    expect(approx(ticks)).toEqual([-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3]);
  });

  it('returns the base envelope for an empty dataset', () => {
    const { domain, ticks } = computeScoreGapYAxis([]);
    expect(approx(domain)).toEqual([-0.3, 0.3]);
    expect(approx(ticks)).toEqual([-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3]);
  });

  it('expands DOWN to the next 10% step for a sub -30% datapoint', () => {
    const { domain, ticks } = computeScoreGapYAxis([pt(-0.42), pt(0.05)]);
    expect(approx(domain)).toEqual([-0.5, 0.3]);
    expect(approx(ticks)).toEqual([
      -0.5, -0.4, -0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3,
    ]);
  });

  it('expands UP when a CI whisker (not just the dot) exceeds +30%', () => {
    // dot at +0.20 is inside, but the upper whisker reaches +0.45.
    const { domain, ticks } = computeScoreGapYAxis([pt(0.2, [0.0, 0.25])]);
    expect(approx(domain)).toEqual([-0.3, 0.5]);
    expect(approx(ticks)).toEqual([
      -0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5,
    ]);
  });

  it('a value sitting exactly on ±30% does NOT over-expand the axis', () => {
    const { domain } = computeScoreGapYAxis([pt(0.3), pt(-0.3)]);
    expect(approx(domain)).toEqual([-0.3, 0.3]);
  });

  it('ticks are equidistant at exactly 10% and always include 0', () => {
    const { ticks } = computeScoreGapYAxis([pt(-0.61), pt(0.37)]);
    expect(ticks).toContain(0);
    for (let i = 1; i < ticks.length; i += 1) {
      const a = ticks[i]!;
      const b = ticks[i - 1]!;
      expect(Math.round((a - b) * 1e6) / 1e6).toBe(0.1);
    }
  });
});

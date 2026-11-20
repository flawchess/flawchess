// @vitest-environment jsdom
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';

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

import { FacepalmShareChart, FacepalmShareTooltipBody } from '../FacepalmShareChart';
import { makeTrendPoint } from '../stats/__tests__/flawStatsFixtures';

const WINDOW_SIZE = 100;

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
});

const SHARED_POINTS = [
  makeTrendPoint('2026-03-02', { facepalm_share: 0.2 }),
  makeTrendPoint('2026-03-09', { facepalm_share: 0.25 }),
  makeTrendPoint('2026-03-16', { facepalm_share: 0.3 }),
];

describe('FacepalmShareChart', () => {
  it('shows the title, the 70% subtitle, the chart and the window caption', () => {
    render(<FacepalmShareChart trend={SHARED_POINTS} windowSize={WINDOW_SIZE} />);
    expect(screen.getByTestId('facepalm-share-chart')).not.toBeNull();
    expect(screen.getByText('Facepalm share of blunders')).not.toBeNull();
    expect(screen.getByText(/70%/)).not.toBeNull();
    expect(screen.getByTestId('facepalm-share-composed-chart')).not.toBeNull();
    expect(screen.getByText('last 100 games · rolling window')).not.toBeNull();
    expect(screen.queryByTestId('facepalm-share-empty')).toBeNull();
  });

  it('falls back to text when fewer than two points carry a share', () => {
    const trend = [
      makeTrendPoint('2026-03-02', { facepalm_share: null }),
      makeTrendPoint('2026-03-09', { facepalm_share: 0.25 }),
      makeTrendPoint('2026-03-16', { facepalm_share: null }),
      makeTrendPoint('2026-03-23', { facepalm_share: null }),
    ];
    render(<FacepalmShareChart trend={trend} windowSize={WINDOW_SIZE} />);
    expect(screen.getByTestId('facepalm-share-empty').textContent).toBe(
      'Not enough scored blunders to show a trend',
    );
    expect(screen.queryByTestId('facepalm-share-composed-chart')).toBeNull();
  });

  it('still draws the chart when only some points are null (a gap, not a fallback)', () => {
    const trend = [
      makeTrendPoint('2026-03-02', { facepalm_share: null }),
      makeTrendPoint('2026-03-09', { facepalm_share: 0.25 }),
      makeTrendPoint('2026-03-16', { facepalm_share: 0.3 }),
    ];
    render(<FacepalmShareChart trend={trend} windowSize={WINDOW_SIZE} />);
    expect(screen.getByTestId('facepalm-share-composed-chart')).not.toBeNull();
  });

  it('uses no probability wording anywhere in the chart', () => {
    const { container } = render(
      <FacepalmShareChart trend={SHARED_POINTS} windowSize={WINDOW_SIZE} />,
    );
    expect(container.textContent ?? '').not.toMatch(/chance|probab|likel/i);
  });
});

describe('FacepalmShareTooltipBody', () => {
  it('rounds the share to the nearest percent and names both counts', () => {
    const point = makeTrendPoint('2026-03-09', {
      facepalm_share: 0.266,
      facepalm_in_window: 25,
      scored_blunders_in_window: 94,
    });
    render(<FacepalmShareTooltipBody point={point} label="2026-03-09" />);
    const body = screen.getByTestId('facepalm-share-tooltip').textContent ?? '';
    expect(body).toContain('27%');
    expect(body).toContain('25 of 94 scored blunders');
    expect(body).toContain('4 games this week · 20 in window');
  });

  it('says there are too few scored blunders for a null share', () => {
    const point = makeTrendPoint('2026-03-09', {
      facepalm_share: null,
      facepalm_in_window: 3,
      scored_blunders_in_window: 12,
    });
    render(<FacepalmShareTooltipBody point={point} label="2026-03-09" />);
    const body = screen.getByTestId('facepalm-share-tooltip').textContent ?? '';
    expect(body).toContain('Too few scored blunders');
    expect(body).not.toContain('%');
  });
});

// @vitest-environment jsdom
/**
 * ScoreChart (single opening series, optional weekly volume bars) and the inactivity-gap
 * annotation it shares with the other ordinal-axis timeline charts.
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

import { ScoreChart } from '../ScoreChart';
import type { BookmarkTimeSeries } from '@/types/position_bookmarks';

const CHART_HEIGHT_PX = 400;
/** The tallest weekly bar fills the bottom 20% of the canvas. */
const TALLEST_BAR_MAX_SHARE = 0.2;
const TALLEST_BAR_MIN_SHARE = 0.1;

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

function makeSeries(dates: string[], perWeekGames: number[] = []): BookmarkTimeSeries {
  return {
    bookmark_id: 0,
    total_wins: dates.length * 5,
    total_draws: dates.length * 2,
    total_losses: dates.length * 3,
    total_games: dates.length * 10,
    score: 0.55,
    score_confidence: 'low',
    score_p_value: 0.2,
    score_ci_low: 0.4,
    score_ci_high: 0.7,
    is_current: true,
    data: dates.map((date, i) => ({
      date,
      score: 0.55,
      game_count: 10,
      window_size: 50,
      per_week_games: perWeekGames[i] ?? 1,
    })),
  };
}

/** Twelve consecutive Mondays. */
const WEEKLY_DATES = Array.from({ length: 12 }, (_, i) => {
  const d = new Date(Date.UTC(2024, 0, 1 + i * 7));
  return d.toISOString().slice(0, 10);
});

/** Dates with a >90-day gap between index 0 and 1 (121 days). */
const GAP_DATES = ['2024-01-01', '2024-05-01', '2024-05-08'];

/** Dates with all consecutive pairs 7 days apart, no gap. */
const NO_GAP_DATES = ['2024-01-01', '2024-01-08', '2024-01-15', '2024-01-22'];

function barHeights(container: HTMLElement): number[] {
  return Array.from(container.querySelectorAll('.recharts-bar-rectangle path')).map((el) =>
    Number(el.getAttribute('height')),
  );
}

describe('ScoreChart volume bars', () => {
  it('renders weekly volume bars when showVolume is set, tallest in the bottom 20%', () => {
    const perWeek = [1, 2, 3, 4, 5, 10, 2, 1, 3, 2, 4, 1];
    const { container } = render(
      <ScoreChart series={makeSeries(WEEKLY_DATES, perWeek)} showVolume />,
    );
    const heights = barHeights(container);
    expect(heights).toHaveLength(12);
    expect(container.querySelector('[data-testid="score-chart-volume-bars"]')).not.toBeNull();
    const tallest = Math.max(...heights);
    expect(tallest).toBeLessThanOrEqual(CHART_HEIGHT_PX * TALLEST_BAR_MAX_SHARE);
    expect(tallest).toBeGreaterThan(CHART_HEIGHT_PX * TALLEST_BAR_MIN_SHARE);
    // Bar heights are proportional to the weekly game counts (1 game vs 10 games).
    expect(tallest / (heights[0] as number)).toBeCloseTo(10, 0);
  });

  it('renders no volume bars without showVolume', () => {
    const { container } = render(<ScoreChart series={makeSeries(WEEKLY_DATES)} />);
    expect(container.querySelectorAll('.recharts-bar-rectangle')).toHaveLength(0);
    expect(container.querySelector('[data-testid="score-chart-volume-bars"]')).toBeNull();
  });
});

describe('ScoreChart inactivity gap annotations', () => {
  it('renders inactivity-gap-label for a >90-day gap fixture', () => {
    const { container } = render(<ScoreChart series={makeSeries(GAP_DATES)} />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders inactivity-gap-glyph (Palmtree) for a >90-day gap fixture', () => {
    const { container } = render(<ScoreChart series={makeSeries(GAP_DATES)} />);
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).not.toBeNull();
  });

  it('renders no inactivity-gap annotation for a gap-free fixture', () => {
    const { container } = render(<ScoreChart series={makeSeries(NO_GAP_DATES)} />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).toBeNull();
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).toBeNull();
  });
});

describe('ScoreChart empty state', () => {
  it('renders the empty-state message and no chart for an empty series', () => {
    const { container } = render(<ScoreChart series={makeSeries([])} showVolume />);
    expect(screen.getByText(/Not enough games in this opening for a score line yet/i)).toBeTruthy();
    expect(container.querySelector('.recharts-wrapper')).toBeNull();
  });
});

describe('ScoreChart typical band', () => {
  it('draws the labelled grey 45-55% typical band', () => {
    const { container } = render(<ScoreChart series={makeSeries(WEEKLY_DATES)} />);
    expect(container.querySelector('.recharts-reference-area')).not.toBeNull();
    expect(screen.getByText('typical')).toBeTruthy();
  });
});

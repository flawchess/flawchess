// @vitest-environment jsdom
/**
 * Regression tests for ScoreChart inactivity-gap annotation (SC-4 Task 3).
 *
 * Asserts that the shared inactivityGapReferenceLines helper renders the
 * Palmtree break annotation for a >90-day gap fixture and no-ops gracefully
 * for a gap-free fixture and an empty series.
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
import type { PositionBookmarkResponse, BookmarkTimeSeries } from '@/types/position_bookmarks';

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

function makeBookmark(id: number): PositionBookmarkResponse {
  return {
    id,
    label: `Bookmark ${id}`,
    target_hash: `hash_${id}`,
    fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -',
    moves: [],
    color: null,
    match_side: 'both',
    is_flipped: false,
    sort_order: id,
  };
}

function makeSeries(bookmark_id: number, dates: string[]): BookmarkTimeSeries {
  return {
    bookmark_id,
    total_wins: dates.length * 5,
    total_draws: dates.length * 2,
    total_losses: dates.length * 3,
    total_games: dates.length * 10,
    data: dates.map((date) => ({
      date,
      score: 0.55,
      game_count: 10,
      window_size: 50,
    })),
  };
}

/** Dates with a >90-day gap between index 0 and 1 (121 days). */
const GAP_DATES = ['2024-01-01', '2024-05-01', '2024-05-08'];

/** Dates with all consecutive pairs 7 days apart — no gap. */
const NO_GAP_DATES = ['2024-01-01', '2024-01-08', '2024-01-15', '2024-01-22'];

describe('ScoreChart inactivity gap annotations', () => {
  it('renders inactivity-gap-label for a >90-day gap fixture', () => {
    const bookmarks = [makeBookmark(1)];
    const series = [makeSeries(1, GAP_DATES)];
    const { container } = render(<ScoreChart bookmarks={bookmarks} series={series} />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders inactivity-gap-glyph (Palmtree) for a >90-day gap fixture', () => {
    const bookmarks = [makeBookmark(1)];
    const series = [makeSeries(1, GAP_DATES)];
    const { container } = render(<ScoreChart bookmarks={bookmarks} series={series} />);
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).not.toBeNull();
  });

  it('renders no inactivity-gap annotation for a gap-free fixture', () => {
    const bookmarks = [makeBookmark(1)];
    const series = [makeSeries(1, NO_GAP_DATES)];
    const { container } = render(<ScoreChart bookmarks={bookmarks} series={series} />);
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).toBeNull();
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).toBeNull();
  });

  it('renders the empty-state message for empty series (no crash, no annotation)', () => {
    render(<ScoreChart bookmarks={[]} series={[]} />);
    expect(screen.getByText(/No game history available/i)).toBeTruthy();
  });
});

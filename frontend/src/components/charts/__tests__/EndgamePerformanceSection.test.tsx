// @vitest-environment jsdom
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';
import type { ScoreGapTimelinePoint } from '@/types/endgames';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver;
// in jsdom the parent has zero dimensions so the inner chart refuses to
// render and all the downstream testids (score-band-above/below, axes) are
// missing. Swap it for a fixed-size wrapper in tests that injects explicit
// width/height into the chart child so Recharts skips its sizing guard.
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
  EndgameScoreOverTimeChart,
  SCORE_BAND_ABOVE_CLASS,
  SCORE_BAND_BELOW_CLASS,
} from '../EndgamePerformanceSection';

// Band presence is detected via the dedicated className on the rendered
// Recharts <Area> layer. Querying by className (rather than by testid on a
// wrapping <g>) is required because a plain <g> wrapper would hide the
// <Area> from Recharts' `findAllByType` child scan and the band would never
// actually render — see the diagnosis comment on EndgameScoreOverTimeChart.
function queryBandAbove(container: HTMLElement): Element | null {
  return container.querySelector(`.${SCORE_BAND_ABOVE_CLASS}`);
}
function queryBandBelow(container: HTMLElement): Element | null {
  return container.querySelector(`.${SCORE_BAND_BELOW_CLASS}`);
}

// jsdom ships without window.matchMedia; useIsMobile() inside the component
// calls it synchronously at mount. Stub it before any render. Same deal with
// ResizeObserver — Recharts' ResponsiveContainer relies on it at effect time.
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

// Vitest 4 does not auto-cleanup RTL mounts — rendered DOM from a previous
// test bleeds into the next one's screen queries if we don't explicitly unmount.
afterEach(() => {
  cleanup();
});

// Fixture helpers — build ScoreGapTimelinePoint arrays with controlled
// endgame_score / non_endgame_score patterns so shading-band tests can
// assert on a deterministic sign sequence.
function makePoint(
  date: string,
  endgame_score: number,
  non_endgame_score: number,
  counts: { endgame_game_count?: number; non_endgame_game_count?: number; per_week_total_games?: number } = {},
): ScoreGapTimelinePoint {
  return {
    date,
    endgame_score,
    non_endgame_score,
    score_difference: endgame_score - non_endgame_score,
    endgame_game_count: counts.endgame_game_count ?? 20,
    non_endgame_game_count: counts.non_endgame_game_count ?? 20,
    per_week_total_games: counts.per_week_total_games ?? 5,
  };
}

// Endgame leads non-endgame by >1% on every point.
const ENDGAME_LEADS_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.60, 0.50),
  makePoint('2025-01-13', 0.62, 0.51),
  makePoint('2025-01-20', 0.58, 0.52),
  makePoint('2025-01-27', 0.59, 0.50),
];

// Endgame trails non-endgame by >1% on every point.
const ENDGAME_TRAILS_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.45, 0.55),
  makePoint('2025-01-13', 0.44, 0.56),
  makePoint('2025-01-20', 0.46, 0.54),
  makePoint('2025-01-27', 0.43, 0.55),
];

// Endgame leads in first half, trails in second half — both bands should render.
const MIXED_SIGN_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.60, 0.50),
  makePoint('2025-01-13', 0.62, 0.51),
  makePoint('2025-01-20', 0.58, 0.52),
  makePoint('2025-01-27', 0.45, 0.55),
  makePoint('2025-02-03', 0.44, 0.56),
  makePoint('2025-02-10', 0.43, 0.55),
];

// |endgame - non_endgame| <= 1% on every point — neither band should render.
const EPSILON_NEUTRAL_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.500, 0.500),
  makePoint('2025-01-13', 0.505, 0.500),
  makePoint('2025-01-20', 0.500, 0.505),
  makePoint('2025-01-27', 0.500, 0.500),
];

describe('EndgameScoreOverTimeChart', () => {
  it('renders container and title', () => {
    render(<EndgameScoreOverTimeChart timeline={ENDGAME_LEADS_FIXTURE} window={100} />);
    expect(screen.getByTestId('endgame-score-timeline-chart')).toBeTruthy();
    expect(screen.getByText('Endgame vs Non-Endgame Score over Time')).toBeTruthy();
  });

  it('renders both shaded bands for mixed-sign fixture', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={MIXED_SIGN_FIXTURE} window={100} />,
    );
    expect(queryBandAbove(container)).not.toBeNull();
    expect(queryBandBelow(container)).not.toBeNull();
  });

  it('renders only the above band when endgame leads throughout', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={ENDGAME_LEADS_FIXTURE} window={100} />,
    );
    expect(queryBandAbove(container)).not.toBeNull();
    expect(queryBandBelow(container)).toBeNull();
  });

  it('renders only the below band when endgame trails throughout', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={ENDGAME_TRAILS_FIXTURE} window={100} />,
    );
    expect(queryBandBelow(container)).not.toBeNull();
    expect(queryBandAbove(container)).toBeNull();
  });

  it('renders neither band when all points are within ±1% epsilon', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={EPSILON_NEUTRAL_FIXTURE} window={100} />,
    );
    expect(queryBandAbove(container)).toBeNull();
    expect(queryBandBelow(container)).toBeNull();
  });

  it('emits an SVG <path> inside each rendered band (regression: g-wrapper blocked Recharts discovery)', () => {
    // Regression guard: earlier, each <Area> was wrapped in <g data-testid>
    // which hid the Area from Recharts' `findAllByType` scan and the band
    // never produced a <path>. Tests passed on the <g> wrapper alone. This
    // test fails fast if that regression ever returns.
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={MIXED_SIGN_FIXTURE} window={100} />,
    );
    const aboveLayer = queryBandAbove(container);
    const belowLayer = queryBandBelow(container);
    expect(aboveLayer).not.toBeNull();
    expect(belowLayer).not.toBeNull();
    // Each rendered Area layer must contain at least one <path> — that is
    // the SVG output Recharts emits for the band fill.
    expect(aboveLayer?.querySelector('path')).not.toBeNull();
    expect(belowLayer?.querySelector('path')).not.toBeNull();
  });

  it('renders legend entries for both series', () => {
    render(<EndgameScoreOverTimeChart timeline={MIXED_SIGN_FIXTURE} window={100} />);
    expect(screen.getByTestId('chart-legend-endgame')).toBeTruthy();
    expect(screen.getByTestId('chart-legend-non-endgame')).toBeTruthy();
  });

  it('renders the info popover with shading-explanation sentence and without legacy caveat', async () => {
    render(<EndgameScoreOverTimeChart timeline={MIXED_SIGN_FIXTURE} window={100} />);
    // Radix Popover only mounts Portal content when open. The trigger listens
    // for pointer events; mousedown+pointerdown+click drives the open state.
    const trigger = screen.getByTestId('score-timeline-info');
    await act(async () => {
      fireEvent.pointerDown(trigger, { button: 0, pointerType: 'mouse' });
      fireEvent.mouseDown(trigger, { button: 0 });
      fireEvent.click(trigger);
    });
    // Positive assertion — new sentence present.
    expect(
      await screen.findByText(/green when your endgame Score leads/i),
    ).toBeTruthy();
    // Negative assertion — removed caveat is gone.
    expect(
      screen.queryByText(/Score Gap is a comparison, not an absolute measure/i),
    ).toBeNull();
  });

  it('returns null when timeline is empty', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={[]} window={100} />,
    );
    expect(container.querySelector('[data-testid="endgame-score-timeline-chart"]')).toBeNull();
  });
});

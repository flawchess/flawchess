// @vitest-environment jsdom
import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';
import type { ScoreGapTimelinePoint } from '@/types/endgames';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver;
// in jsdom the parent has zero dimensions so the inner chart refuses to
// render and all the downstream testids (score-band, axes) are missing. Swap
// it for a fixed-size wrapper in tests that injects explicit width/height
// into the chart child so Recharts skips its sizing guard.
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
  SCORE_BAND_CLASS,
} from '../EndgamePerformanceSection';
import {
  SCORE_TIMELINE_FILL_ABOVE,
  SCORE_TIMELINE_FILL_BELOW,
} from '@/lib/theme';

// Band presence is detected via the dedicated className on the rendered
// Recharts <Area> layer. Querying by className (rather than by testid on a
// wrapping <g>) is required because a plain <g> wrapper would hide the
// <Area> from Recharts' `findAllByType` child scan and the band would never
// actually render — see the diagnosis comment on EndgameScoreOverTimeChart.
function queryBand(container: HTMLElement): Element | null {
  return container.querySelector(`.${SCORE_BAND_CLASS}`);
}

function gradientStopColors(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('linearGradient stop')).map(
    (s) => s.getAttribute('stop-color') ?? '',
  );
}

function gradientStops(container: HTMLElement): Array<{ offset: string; color: string }> {
  return Array.from(container.querySelectorAll('linearGradient stop')).map((s) => ({
    offset: s.getAttribute('offset') ?? '',
    color: s.getAttribute('stop-color') ?? '',
  }));
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

// Endgame leads non-endgame throughout.
const ENDGAME_LEADS_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.60, 0.50),
  makePoint('2025-01-13', 0.62, 0.51),
  makePoint('2025-01-20', 0.58, 0.52),
  makePoint('2025-01-27', 0.59, 0.50),
];

// Endgame trails non-endgame throughout.
const ENDGAME_TRAILS_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.45, 0.55),
  makePoint('2025-01-13', 0.44, 0.56),
  makePoint('2025-01-20', 0.46, 0.54),
  makePoint('2025-01-27', 0.43, 0.55),
];

// Endgame leads in first half, trails in second half — gradient should carry
// both colors and flip once.
const MIXED_SIGN_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.60, 0.50),
  makePoint('2025-01-13', 0.62, 0.51),
  makePoint('2025-01-20', 0.58, 0.52),
  makePoint('2025-01-27', 0.45, 0.55),
  makePoint('2025-02-03', 0.44, 0.56),
  makePoint('2025-02-10', 0.43, 0.55),
];

// Gradual crossover: diff sequence +5pp, +0.5pp (rounds to 0, still green side),
// −0.5pp (rounds to 0, crossover consumed), −5pp. Guards against the previous
// epsilon-based gap right around the crossover.
const GRADUAL_CROSSOVER_FIXTURE: ScoreGapTimelinePoint[] = [
  makePoint('2025-01-06', 0.55, 0.50),
  makePoint('2025-01-13', 0.51, 0.50),
  makePoint('2025-01-20', 0.49, 0.50),
  makePoint('2025-01-27', 0.45, 0.50),
];

describe('EndgameScoreOverTimeChart', () => {
  it('renders container and title', () => {
    render(<EndgameScoreOverTimeChart timeline={ENDGAME_LEADS_FIXTURE} window={100} />);
    expect(screen.getByTestId('endgame-score-timeline-chart')).toBeTruthy();
    expect(screen.getByText('Endgame vs Non-Endgame Score over Time')).toBeTruthy();
  });

  it('renders a single shaded band layer and gradient carries both colors for mixed-sign fixture', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={MIXED_SIGN_FIXTURE} window={100} />,
    );
    expect(queryBand(container)).not.toBeNull();
    const colors = gradientStopColors(container);
    expect(colors).toContain(SCORE_TIMELINE_FILL_ABOVE);
    expect(colors).toContain(SCORE_TIMELINE_FILL_BELOW);
  });

  it('gradient has only the leads color when endgame leads throughout', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={ENDGAME_LEADS_FIXTURE} window={100} />,
    );
    expect(queryBand(container)).not.toBeNull();
    const colors = gradientStopColors(container);
    expect(colors.length).toBeGreaterThan(0);
    expect(new Set(colors)).toEqual(new Set([SCORE_TIMELINE_FILL_ABOVE]));
  });

  it('gradient has only the trails color when endgame trails throughout', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={ENDGAME_TRAILS_FIXTURE} window={100} />,
    );
    expect(queryBand(container)).not.toBeNull();
    const colors = gradientStopColors(container);
    expect(colors.length).toBeGreaterThan(0);
    expect(new Set(colors)).toEqual(new Set([SCORE_TIMELINE_FILL_BELOW]));
  });

  it('gradient emits instant-flip stop pair at the crossover (no unshaded gap)', () => {
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={GRADUAL_CROSSOVER_FIXTURE} window={100} />,
    );
    // An "instant flip" is two consecutive stops at the same offset with
    // different colors. That is the mechanism that closes the previous
    // epsilon-band gap at the crossover.
    const stops = gradientStops(container);
    const flipPair = stops.find(
      (s, i) =>
        i > 0
        && stops[i - 1]!.offset === s.offset
        && stops[i - 1]!.color !== s.color,
    );
    expect(flipPair).toBeDefined();
    // And both color ends of the flip must be the configured fill colors.
    const colors = new Set(stops.map((s) => s.color));
    expect(colors.has(SCORE_TIMELINE_FILL_ABOVE)).toBe(true);
    expect(colors.has(SCORE_TIMELINE_FILL_BELOW)).toBe(true);
  });

  it('emits an SVG <path> inside the band layer (regression: g-wrapper blocked Recharts discovery)', () => {
    // Regression guard: earlier, each <Area> was wrapped in <g data-testid>
    // which hid the Area from Recharts' `findAllByType` scan and the band
    // never produced a <path>. Tests passed on the <g> wrapper alone. This
    // test fails fast if that regression ever returns.
    const { container } = render(
      <EndgameScoreOverTimeChart timeline={MIXED_SIGN_FIXTURE} window={100} />,
    );
    const bandLayer = queryBand(container);
    expect(bandLayer).not.toBeNull();
    expect(bandLayer?.querySelector('path')).not.toBeNull();
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

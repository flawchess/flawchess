// @vitest-environment jsdom
/**
 * Phase 81 Plan 04 — page-level integration tests for the Endgames page after
 * `EndgameStartVsEndSection` is wired in.
 *
 * Strategy: full-page render of `<EndgamesPage />` is heavy (15+ hooks), so
 * we mock the data hooks with a complete `EndgameOverviewResponse` fixture
 * and stub out the chart sub-components that don't participate in the
 * assertions of this plan (Conv/Recov, Score Gap, Clock Pressure, Time
 * Pressure, ELO timeline, WDL chart, GameCardList, Insights block).
 *
 * The two components the test cares about, `EndgameStartVsEndSection` and
 * `EndgamePerformanceSection` (incl. `EndgameScoreOverTimeChart`), render
 * for real so DOM-order, accordion paragraph order, and D-21 negative-scope
 * testid presence can all be asserted directly against the rendered tree.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ReactElement } from 'react';
import { cloneElement, isValidElement } from 'react';
import type {
  EndgameOverviewResponse,
  EndgamePerformanceResponse,
  EndgameWDLSummary,
} from '@/types/endgames';

// ── Recharts: jsdom has zero-size parents; ResponsiveContainer would refuse
// to render. Replace it with a fixed-size shim so EndgameScoreOverTimeChart
// (which renders inside the Endgames page when score-gap data has a timeline)
// produces its testids.
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <div style={{ width: 800, height: 400 }}>
        {isValidElement(children)
          ? cloneElement(
              children as ReactElement<{ width?: number; height?: number }>,
              { width: 800, height: 400 },
            )
          : children}
      </div>
    ),
  };
});

// ── Mock heavy chart components / hooks that don't participate in the
// assertions. Everything stubbed here renders a single <div> with a stable
// testid so we can still detect "the section was rendered" if needed.
vi.mock('@/components/charts/EndgameWDLChart', () => ({
  EndgameWDLChart: () => <div data-testid="mock-endgame-wdl-chart" />,
}));
vi.mock('@/components/charts/EndgameConvRecovChart', () => ({
  EndgameConvRecovChart: () => <div data-testid="mock-endgame-conv-recov-chart" />,
}));
vi.mock('@/components/charts/EndgameScoreGapSection', () => ({
  EndgameScoreGapSection: () => <div data-testid="mock-endgame-score-gap-section" />,
}));
vi.mock('@/components/charts/EndgameClockPressureSection', () => ({
  EndgameClockPressureSection: () => <div data-testid="mock-endgame-clock-pressure-section" />,
  ClockDiffTimelineChart: () => <div data-testid="mock-clock-diff-timeline" />,
}));
vi.mock('@/components/charts/EndgameTimePressureSection', () => ({
  EndgameTimePressureSection: () => <div data-testid="mock-endgame-time-pressure-section" />,
}));
vi.mock('@/components/charts/EndgameEloTimelineSection', () => ({
  EndgameEloTimelineSection: () => <div data-testid="mock-endgame-elo-timeline-section" />,
}));
vi.mock('@/components/results/GameCardList', () => ({
  GameCardList: () => <div data-testid="mock-game-card-list" />,
}));
vi.mock('@/components/insights/EndgameInsightsBlock', () => ({
  EndgameInsightsBlock: () => <div data-testid="mock-endgame-insights-block" />,
}));

// ── Mock data hooks. The Endgames page consumes useEndgameOverview,
// useEndgameGames, useCachedEndgameInsights, useEndgameInsights, useActiveJobs,
// and useFilterStore. Each returns a stable fixture; tests that need to
// override a field use buildOverview(...).
const overviewState: { data: EndgameOverviewResponse | null } = { data: null };

vi.mock('@/hooks/useEndgames', () => ({
  useEndgameOverview: () => ({
    data: overviewState.data,
    isLoading: false,
    isError: false,
  }),
  useEndgameGames: () => ({
    data: { games: [], matched_count: 0, offset: 0, limit: 20 },
    isLoading: false,
    isError: false,
  }),
}));

vi.mock('@/hooks/useEndgameInsights', () => ({
  useCachedEndgameInsights: () => ({ data: null, isLoading: false, isError: false }),
  useEndgameInsights: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  }),
}));

vi.mock('@/hooks/useImport', () => ({
  useActiveJobs: () => ({ data: [], isLoading: false, isError: false }),
}));

// jsdom shims required by the existing component (matchMedia for radix popovers,
// ResizeObserver for recharts, scrollTo for category-select handler).
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
  if (!('scrollTo' in window) || typeof window.scrollTo !== 'function') {
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  }
});

afterEach(() => {
  cleanup();
});

// Import the page after the mocks above are registered.
import { EndgamesPage } from '../Endgames';

// ── Fixture builders ──────────────────────────────────────────────────────
function buildWdl(
  wins: number,
  draws: number,
  losses: number,
  total = wins + draws + losses,
): EndgameWDLSummary {
  const safeTotal = total === 0 ? 1 : total;
  return {
    wins,
    draws,
    losses,
    total,
    win_pct: (wins / safeTotal) * 100,
    draw_pct: (draws / safeTotal) * 100,
    loss_pct: (losses / safeTotal) * 100,
  };
}

function buildPerf(
  overrides?: Partial<EndgamePerformanceResponse>,
): EndgamePerformanceResponse {
  return {
    endgame_wdl: buildWdl(25, 10, 15),
    non_endgame_wdl: buildWdl(20, 8, 12),
    endgame_win_rate: 0.5,
    entry_eval_mean_pawns: 0.4,
    entry_eval_n: 50,
    entry_eval_p_value: 0.001,
    endgame_score_p_value: 0.001,
    entry_eval_ci_low_pawns: 0.1,
    entry_eval_ci_high_pawns: 0.7,
    ...overrides,
  };
}

function buildOverview(overrides?: {
  performance?: Partial<EndgamePerformanceResponse>;
}): EndgameOverviewResponse {
  return {
    stats: {
      total_games: 100,
      endgame_games: 50,
      categories: [
        {
          endgame_class: 'mixed',
          label: 'Mixed',
          wins: 25,
          draws: 10,
          losses: 15,
          total: 50,
          win_pct: 50,
          draw_pct: 20,
          loss_pct: 30,
          conversion: {
            conversion_pct: 60,
            conversion_games: 20,
            conversion_wins: 12,
            conversion_draws: 4,
            conversion_losses: 4,
            recovery_pct: 30,
            recovery_games: 10,
            recovery_saves: 3,
            recovery_wins: 1,
            recovery_draws: 2,
          },
        },
      ],
    },
    performance: buildPerf(overrides?.performance),
    timeline: { overall: [], per_type: {}, window: 100 },
    score_gap_material: {
      endgame_score: 0.55,
      non_endgame_score: 0.50,
      score_difference: 0.05,
      material_rows: [],
      timeline: [
        // Single timeline point is sufficient to make the score-over-time
        // chart render its outermost <div data-testid="endgame-score-timeline-chart">.
        {
          date: '2026-01-05',
          score_difference: 0.05,
          endgame_game_count: 25,
          non_endgame_game_count: 25,
          per_week_total_games: 50,
          endgame_score: 0.55,
          non_endgame_score: 0.50,
        },
      ],
      timeline_window: 100,
    },
    clock_pressure: {
      rows: [],
      total_clock_games: 0,
      total_endgame_games: 50,
      timeline: [],
      timeline_window: 100,
    },
    time_pressure_chart: {
      user_series: [],
      opp_series: [],
      total_endgame_games: 0,
    },
    endgame_elo_timeline: { combos: [], timeline_window: 100 },
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/endgames/stats']}>
      <EndgamesPage />
    </MemoryRouter>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────
describe('Endgames page — Phase 81 Plan 04 wire-up', () => {
  it('renders EndgameStartVsEndSection before EndgamePerformanceSection (D-01)', () => {
    overviewState.data = buildOverview();
    const { container } = renderPage();
    const startVsEnd = container.querySelector(
      '[data-testid="endgame-start-vs-end-section"]',
    );
    const perfSection = container.querySelector(
      '[data-testid="endgame-performance-section"]',
    );
    expect(startVsEnd).not.toBeNull();
    expect(perfSection).not.toBeNull();
    // DOCUMENT_POSITION_FOLLOWING = 4: startVsEnd is followed by perfSection.
    // eslint-disable-next-line no-bitwise
    const followingMask =
      startVsEnd!.compareDocumentPosition(perfSection!) &
      Node.DOCUMENT_POSITION_FOLLOWING;
    expect(followingMask).toBeTruthy();
  });

  it('does NOT render the start-vs-end section when no endgame games (showPerfSection false)', () => {
    overviewState.data = buildOverview({
      performance: { endgame_wdl: buildWdl(0, 0, 0) },
    });
    const { container } = renderPage();
    expect(
      container.querySelector('[data-testid="endgame-start-vs-end-section"]'),
    ).toBeNull();
  });

  it('contains both new accordion paragraphs ("Avg eval at endgame entry" + "Absolute endgame score") (D-13)', () => {
    overviewState.data = buildOverview();
    renderPage();
    expect(screen.getByText(/Avg eval at endgame entry:/)).toBeTruthy();
    expect(screen.getByText(/Absolute endgame score:/)).toBeTruthy();
  });

  it('places the 2 new accordion paragraphs AFTER Recovery and BEFORE the rating-changes caveat (D-14)', () => {
    overviewState.data = buildOverview();
    const { container } = renderPage();
    const accordionContent = container.querySelector(
      '[data-testid="endgame-concepts-trigger"]',
    );
    expect(accordionContent).not.toBeNull();
    // Read all <p> blocks inside the accordion's content area; jsdom renders
    // them all because radix's <Accordion> mounts content as hidden when
    // collapsed, but it is still part of the DOM.
    const paragraphs = Array.from(
      accordionContent!.querySelectorAll('p'),
    ) as HTMLParagraphElement[];
    const text = paragraphs.map((p) => p.textContent ?? '');
    const recoveryIdx = text.findIndex((t) => /Recovery:/.test(t));
    const entryEvalIdx = text.findIndex((t) => /Avg eval at endgame entry:/.test(t));
    const endgameScoreIdx = text.findIndex((t) =>
      /Absolute endgame score:/.test(t),
    );
    const ratingChangesIdx = text.findIndex((t) =>
      /usually reflect your performance against opponents at your rating/.test(t),
    );
    expect(recoveryIdx).toBeGreaterThanOrEqual(0);
    expect(entryEvalIdx).toBeGreaterThan(recoveryIdx);
    expect(endgameScoreIdx).toBeGreaterThan(entryEvalIdx);
    expect(ratingChangesIdx).toBeGreaterThan(endgameScoreIdx);
  });

  it('preserves existing WDL table, Score Gap, and timeline chart (D-21 negative scope)', () => {
    overviewState.data = buildOverview();
    const { container } = renderPage();
    // perf-wdl-table (desktop) OR perf-wdl-cards (mobile); both render in
    // jsdom because we don't simulate a viewport. Either is acceptable.
    expect(
      container.querySelector('[data-testid="perf-wdl-table"]') ||
        container.querySelector('[data-testid="perf-wdl-cards"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-testid="score-gap-difference"]') ||
        container.querySelector('[data-testid="score-gap-difference-mobile"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-testid="endgame-score-timeline-chart"]'),
    ).not.toBeNull();
  });

  it('references the Opponent Strength filter as plain text in the new accordion paragraphs (D-13)', () => {
    overviewState.data = buildOverview();
    renderPage();
    expect(screen.getByText(/Opponent Strength filter/)).toBeTruthy();
  });
});

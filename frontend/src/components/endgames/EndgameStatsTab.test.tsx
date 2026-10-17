// @vitest-environment jsdom
/**
 * Empty ranked sample, filter-free ranked hook and one synced TC across every
 * section, plus the per-TC
 * timelines. The ranked hook is mocked.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type { EndgameRankedStatsResponse } from '@/types/endgames';
import { buildRankedResponse, buildRankedTc, buildWdl } from './stats/rankedFixtures';

const { rankedHook, rankedState } = vi.hoisted(() => {
  const state: { data: EndgameRankedStatsResponse | null } = { data: null };
  return {
    rankedState: state,
    rankedHook: vi.fn<
      (options?: { enabled?: boolean }) => {
        data: EndgameRankedStatsResponse | null;
        isLoading: boolean;
        isError: boolean;
      }
    >(() => ({
      data: state.data,
      isLoading: false,
      isError: false,
    })),
  };
});

vi.mock('@/hooks/useEndgames', () => ({
  useEndgameRankedStats: rankedHook,
}));

vi.mock('@/hooks/useEndgameInsights', () => ({
  useEndgameInsightsGenerating: () => false,
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

vi.mock('@/components/insights/EndgameInsightsBlock', () => ({
  EndgameInsightsBlock: () => <div data-testid="mock-endgame-insights-block" />,
}));

// The charts keep their own tests; here they only expose the series they were given.
vi.mock('@/components/charts/EndgameScoreOverTimeChart', () => ({
  EndgameScoreOverTimeChart: ({ timeline, windowSize }: { timeline: unknown[]; windowSize: number }) => (
    <div
      data-testid="mock-score-chart"
      data-points={timeline.length}
      data-window={windowSize}
    />
  ),
}));
vi.mock('@/components/charts/EndgameClockDiffOverTimeChart', () => ({
  EndgameClockDiffOverTimeChart: () => <div data-testid="mock-clock-timeline" />,
}));
vi.mock('@/components/charts/ScoreGapByTimePressureChart', () => ({
  ScoreGapByTimePressureChart: () => <div data-testid="mock-pressure-curve" />,
}));
vi.mock('@/components/charts/EndgameEloTimelineSection', () => ({
  EndgameEloTimelineSection: ({
    data,
  }: {
    data: { combos: unknown[]; timeline_window: number };
  }) => (
    <div
      data-testid="mock-elo-timeline"
      data-combos={data.combos.length}
      data-window={data.timeline_window}
    />
  ),
}));

type TabModule = typeof import('./EndgameStatsTab');
let EndgameStatsTab: TabModule['EndgameStatsTab'];

beforeEach(async () => {
  // The TC selection is module-level state: load a fresh copy per test.
  vi.resetModules();
  localStorage.clear();
  rankedHook.mockClear();
  ({ EndgameStatsTab } = await import('./EndgameStatsTab'));
});

afterEach(cleanup);

function renderTab() {
  return render(
    <MemoryRouter>
      <EndgameStatsTab tier2 onCategorySelect={vi.fn()} />
    </MemoryRouter>,
  );
}

function byId(testId: string): HTMLElement {
  const element = screen.queryByTestId(testId);
  expect(element, `element ${testId} present`).not.toBeNull();
  return element as HTMLElement;
}

const BLITZ_POINT = {
  date: '2026-01-05',
  score_difference: 0.05,
  endgame_game_count: 25,
  non_endgame_game_count: 25,
  per_week_total_games: 50,
  per_week_endgame_games: 25,
  endgame_score: 0.55,
  non_endgame_score: 0.5,
  endgame_opp_rating_avg: 1500,
  non_endgame_opp_rating_avg: 1500,
};

describe('EndgameStatsTab empty ranked sample', () => {
  it('shows exactly one empty state that names what qualifies and links to the Games tab', () => {
    rankedState.data = buildRankedResponse([]);
    const { container } = renderTab();
    expect(container.querySelectorAll('[data-testid="endgame-stats-empty-state"]')).toHaveLength(1);
    const text = byId('endgame-stats-empty-state').textContent ?? '';
    expect(text).toContain('rated');
    expect(text).toContain('human');
    expect(text).toContain('±100 Elo');
    expect(text).toContain('36 months');
    const link = byId('btn-empty-see-endgame-games');
    expect(link.getAttribute('href')).toBe('/endgames/games');
    expect(screen.queryByTestId('endgame-overall-section')).toBeNull();
  });
});

describe('EndgameStatsTab with a ranked payload', () => {
  beforeEach(() => {
    rankedState.data = buildRankedResponse([
      buildRankedTc('blitz', {
        ranked_games: 180,
        overall: {
          endgame_wdl: buildWdl(50, 0, 50),
          non_endgame_wdl: buildWdl(60, 0, 40),
          entry_flow: {
            entry_eval_mean_pawns: 0.2,
            entry_eval_n: 10,
            expected_score: 0.5,
            actual_score: 0.5,
            n: 10,
          },
        },
        score_gap_timeline: [BLITZ_POINT],
        score_gap_timeline_window: 100,
        elo_timeline: [],
        elo_timeline_window: 80,
      }),
      buildRankedTc('rapid', { ranked_games: 871, score_gap_timeline: [], elo_timeline_window: 100 }),
    ]);
  });

  it('renders the Overall section for the default TC', () => {
    renderTab();
    byId('endgame-overall-section');
    expect(byId('tc-switch-endgame-stats-rapid').getAttribute('aria-pressed')).toBe('true');
  });

  it('calls the ranked hook without any filter argument', () => {
    renderTab();
    expect(rankedHook).toHaveBeenCalled();
    for (const call of rankedHook.mock.calls) {
      expect(call).toHaveLength(1);
      expect(Object.keys(call[0] ?? {})).toEqual(['enabled']);
    }
  });

  it('switches every section from the one sticky switch', () => {
    renderTab();
    for (const section of [
      'endgame-overall-section',
      'endgame-metrics-tc-section',
      'endgame-time-pressure-section',
      'endgame-type-breakdown-section',
    ]) {
      byId(section);
    }
    // One switch for the tab, inside the sticky bar; no section carries its own.
    expect(screen.getAllByRole('group', { name: 'Time control' })).toHaveLength(1);
    expect(byId('endgame-stats-tc-bar').contains(byId('tc-switch-endgame-stats'))).toBe(true);
    expect(byId('endgame-overall-no-endgame-score').textContent).toBe('59.0%');

    fireEvent.click(byId('tc-switch-endgame-stats-blitz'));

    expect(byId('tc-switch-endgame-stats-blitz').getAttribute('aria-pressed')).toBe('true');
    // Blitz fixture: no-endgame 60W/40L -> 60.0%, endgame 50W/50L -> 50.0%.
    expect(byId('endgame-overall-no-endgame-score').textContent).toBe('60.0%');
    expect(byId('endgame-overall-endgame-score').textContent).toBe('50.0%');
    expect(byId('endgame-time-pressure-section').getAttribute('aria-label')).toBe(
      'Time Pressure, Blitz',
    );
    expect(byId('endgame-metrics-tc-section').getAttribute('aria-label')).toBe(
      'Endgame Metrics, Blitz',
    );
  });

  it('feeds the timelines from the selected TC', () => {
    renderTab();
    // Rapid is the default TC and has no score-gap series: the chart hides.
    expect(screen.queryByTestId('mock-score-chart')).toBeNull();
    expect(byId('mock-elo-timeline').getAttribute('data-window')).toBe('100');

    fireEvent.click(byId('tc-switch-endgame-stats-blitz'));

    expect(byId('mock-score-chart').getAttribute('data-points')).toBe('1');
    expect(byId('mock-score-chart').getAttribute('data-window')).toBe('100');
    expect(byId('mock-elo-timeline').getAttribute('data-window')).toBe('80');
  });
});

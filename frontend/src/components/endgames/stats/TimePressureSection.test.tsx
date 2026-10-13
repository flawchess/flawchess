// @vitest-environment jsdom
/**
 * Phase 238 validation rows D-06 / D-00f: the Time Pressure section follows the
 * synced TC switch, shows the clock timeline and the score-vs-clock curve from the
 * selected TC's ranked data, and carries three percentile rows.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/react';
import type { PressureQuintileBullet } from '@/types/endgames';
import { buildRankedTc } from './rankedFixtures';

// The charts keep their own tests; here they only expose what they were given.
vi.mock('@/components/charts/EndgameClockDiffOverTimeChart', () => ({
  EndgameClockDiffOverTimeChart: ({ timeline }: { timeline: unknown[] }) => (
    <div data-testid="mock-clock-timeline" data-points={timeline.length} />
  ),
}));
vi.mock('@/components/charts/ScoreGapByTimePressureChart', () => ({
  ScoreGapByTimePressureChart: ({ quintiles, tc }: { quintiles: unknown[]; tc: string }) => (
    <div data-testid="mock-pressure-curve" data-quintiles={quintiles.length} data-tc={tc} />
  ),
}));

type SectionModule = typeof import('./TimePressureSection');
let TimePressureSection: SectionModule['TimePressureSection'];
// The page's one switch (the section carries none); loaded from the same fresh module graph.
let TcSwitch: typeof import('./TcSwitch')['TcSwitch'];

beforeEach(async () => {
  // The TC selection is module-level state: load a fresh copy per test.
  vi.resetModules();
  localStorage.clear();
  ({ TimePressureSection } = await import('./TimePressureSection'));
  ({ TcSwitch } = await import('./TcSwitch'));
});

afterEach(cleanup);

function bin(index: number): PressureQuintileBullet {
  return {
    quintile_index: index,
    quintile_label: `${index * 20}-${index * 20 + 20}%`,
    n: 30,
    n_opp: 30,
    delta: 0,
    p_value: 0.5,
    ci_low: -0.1,
    ci_high: 0.1,
    opp_score: 0.5,
  };
}

const POINT = { date: '2026-01-05', avg_clock_diff_pct: 4, game_count: 40, per_week_game_count: 5 };
const FIVE_BINS = [0, 1, 2, 3, 4].map(bin);

const BLITZ = buildRankedTc('blitz', {
  ranked_games: 200,
  clock_diff_timeline: [POINT, POINT, POINT],
  time_pressure: { quintiles: FIVE_BINS },
});
const RAPID = buildRankedTc('rapid', {
  ranked_games: 400,
  clock_diff_timeline: [],
  time_pressure: { quintiles: FIVE_BINS.slice(0, 4) },
});

function byId(root: HTMLElement, testId: string): HTMLElement {
  const element = root.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
  expect(element, `element ${testId} present`).not.toBeNull();
  return element as HTMLElement;
}

function queryId(root: HTMLElement, testId: string): HTMLElement | null {
  return root.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
}

describe('TimePressureSection', () => {
  it('renders the selected TC: timeline, curve and the three percentile rows', () => {
    // Blitz is the only TC: no default-TC ambiguity.
    const { container } = render(<TimePressureSection tcs={[BLITZ]} />);
    expect(byId(container, 'mock-clock-timeline').getAttribute('data-points')).toBe('3');
    const curve = byId(container, 'mock-pressure-curve');
    expect(curve.getAttribute('data-quintiles')).toBe('5');
    expect(curve.getAttribute('data-tc')).toBe('blitz');
    expect(byId(container, 'time-pressure-clock-gap').textContent).toContain('Clock Gap at entry');
    expect(byId(container, 'time-pressure-net-flag-rate').textContent).toContain('Net Flag Rate');
    expect(byId(container, 'time-pressure-score-gap').textContent).toContain(
      'Score under time pressure',
    );
  });

  it('hides the clock timeline card when the TC has no clock points', () => {
    const { container } = render(<TimePressureSection tcs={[RAPID]} />);
    expect(queryId(container, 'mock-clock-timeline')).toBeNull();
    expect(queryId(container, 'time-pressure-clock-card')).toBeNull();
    // The curve and the percentile rows stay.
    expect(byId(container, 'mock-pressure-curve').getAttribute('data-tc')).toBe('rapid');
  });

  it('follows the synced TC switch', () => {
    const { container } = render(
      <>
        <TcSwitch sectionId="endgame-stats" tcs={[BLITZ, RAPID]} />
        <TimePressureSection tcs={[BLITZ, RAPID]} />
      </>,
    );
    // Rapid has more ranked games, so it is the D-12 default.
    expect(byId(container, 'mock-pressure-curve').getAttribute('data-tc')).toBe('rapid');
    fireEvent.click(byId(container, 'tc-switch-endgame-stats-blitz'));
    expect(byId(container, 'mock-pressure-curve').getAttribute('data-tc')).toBe('blitz');
    expect(byId(container, 'mock-clock-timeline').getAttribute('data-points')).toBe('3');
  });

  it('carries the section anchor id the peer card links to', () => {
    const { container } = render(<TimePressureSection tcs={[BLITZ]} />);
    expect(container.querySelector('#endgame-section-time-pressure')).not.toBeNull();
  });
});

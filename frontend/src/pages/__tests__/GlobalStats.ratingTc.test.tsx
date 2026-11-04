// @vitest-environment jsdom
/**
 * Wiring test: the ELO charts follow the sticky Library Stats TC switch, not only the
 * sidebar filter. RatingChart's own unit tests cannot see this: they passed while the
 * page fed the chart the wrong source.
 */
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { render, screen, cleanup, within } from '@testing-library/react';
import type { ReactNode } from 'react';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { TimeControl } from '@/types/api';
import type { TimeControlBucket } from '@/types/endgames';

const mocks = vi.hoisted(() => ({
  selectedTc: null as TimeControlBucket | null,
  filters: null as FilterState | null,
}));

vi.mock('@/hooks/useLibraryStatsTc', () => ({
  useSelectedLibraryStatsTc: () => mocks.selectedTc,
}));
vi.mock('@/hooks/useFilterStore', () => ({
  useFilterStore: () => [mocks.filters, vi.fn()],
}));
vi.mock('@/hooks/useStats', () => ({
  useRatingHistory: () => ({ data: { chess_com: [], lichess: [] }, isLoading: false }),
  useGlobalStats: () => ({ data: undefined, isLoading: false }),
}));
vi.mock('@/hooks/useGameCount', () => ({ useGameCountValue: () => 0 }));
vi.mock('@/hooks/useUserProfile', () => ({ useUserProfile: () => ({ data: undefined }) }));
vi.mock('@/components/EvalCoverageHeader', () => ({ EvalCoverageHeader: () => null }));
vi.mock('@/components/stats/GlobalStatsCharts', () => ({ GlobalStatsCharts: () => null }));
vi.mock('@/components/layout/SidebarLayout', () => ({
  SidebarLayout: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock('@/components/library/stats/LibraryStatsSections', () => ({
  LibraryStatsTcSwitch: () => null,
  LibraryStatsSections: ({ children }: { children?: ReactNode }) => (
    <div data-testid="sticky-tc-wrapper">{children}</div>
  ),
}));
vi.mock('@/components/stats/RatingChart', () => ({
  RatingChart: ({
    platform,
    enabledTimeControls,
  }: {
    platform: string;
    enabledTimeControls?: TimeControl[] | null;
  }) => <div data-testid={`chart-${platform}`}>{JSON.stringify(enabledTimeControls)}</div>,
}));

import { GlobalStatsPage } from '../GlobalStats';

beforeEach(() => {
  mocks.selectedTc = null;
  mocks.filters = DEFAULT_FILTERS;
});

afterEach(cleanup);

// The page mounts its content twice (desktop and CSS-hidden mobile); both copies must agree.
function chartValues(platform: string): string[] {
  return screen.getAllByTestId(`chart-${platform}`).map((el) => el.textContent ?? '');
}

describe('GlobalStatsPage ELO charts and the TC switch', () => {
  it('starts both charts on the TC selected in the switch', () => {
    mocks.selectedTc = 'blitz';
    render(<GlobalStatsPage />);
    expect(new Set(chartValues('Chess.com'))).toEqual(new Set(['["blitz"]']));
    expect(new Set(chartValues('Lichess'))).toEqual(new Set(['["blitz"]']));
  });

  it('the switch wins over the sidebar filter', () => {
    mocks.selectedTc = 'rapid';
    mocks.filters = { ...DEFAULT_FILTERS, timeControls: ['blitz', 'rapid'] };
    render(<GlobalStatsPage />);
    expect(new Set(chartValues('Chess.com'))).toEqual(new Set(['["rapid"]']));
  });

  it('falls back to the sidebar filter when the switch has no selection', () => {
    mocks.filters = { ...DEFAULT_FILTERS, timeControls: ['bullet', 'classical'] };
    render(<GlobalStatsPage />);
    expect(new Set(chartValues('Lichess'))).toEqual(new Set(['["bullet","classical"]']));
  });

  it('keeps the ELO section inside the sticky switch wrapper', () => {
    render(<GlobalStatsPage />);
    for (const wrapper of screen.getAllByTestId('sticky-tc-wrapper')) {
      expect(within(wrapper).getByTestId('elo-ratings-section')).toBeTruthy();
    }
  });
});

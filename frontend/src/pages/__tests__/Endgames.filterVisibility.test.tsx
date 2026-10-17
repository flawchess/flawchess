// @vitest-environment jsdom
/**
 * Endgames filter visibility.
 *
 * The filter UI (desktop sidebar strip + panel, mobile Filters button + drawer) is
 * hidden while the Stats tab is active and comes back on the Games tab. Hiding it
 * must never touch the applied filters: the shared store value is referentially
 * equal after a Stats round trip, and a half-edited pending draft is discarded
 * rather than committed. The Games tab reads GET /endgames/stats.
 */

import { useEffect } from 'react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { FilterState } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import type { EndgameStatsResponse } from '@/types/endgames';

// ── Data hooks: the Games tab data comes from useEndgameStats.
const statsHookSpy = vi.fn();
const STATS: EndgameStatsResponse = {
  total_games: 100,
  endgame_games: 50,
  categories: [
    {
      endgame_class: 'mixed',
      label: 'Mixed',
      total: 50,
    },
  ],
} as unknown as EndgameStatsResponse;

vi.mock('@/hooks/useEndgames', () => ({
  useEndgameStats: (filters: FilterState, options: { enabled?: boolean }) => {
    statsHookSpy(filters, options);
    return { data: STATS, isLoading: false, isError: false };
  },
  useEndgameRankedStats: () => ({ data: { tcs: [] }, isLoading: false, isError: false }),
  useEndgameGames: () => ({
    data: { games: [{ id: 1 }], matched_count: 12, offset: 0, limit: 20 },
    isLoading: false,
    isError: false,
  }),
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

vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({
    pendingCount: 0,
    totalCount: 0,
    pct: 100,
    hasPendingEvals: false,
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({
    tier1: true,
    tier2: true,
    pendingCount: 0,
    totalCount: 0,
    isLoading: false,
    isError: false,
  }),
}));

// Heavy children that do not take part in the assertions.
vi.mock('@/components/results/GameCardList', () => ({
  GameCardList: ({ matchLabel }: { matchLabel?: React.ReactNode }) => (
    <div data-testid="mock-game-card-list">{matchLabel}</div>
  ),
}));
vi.mock('@/components/charts/PositionResultsPanel', () => ({
  PositionResultsPanel: ({ label }: { label: string }) => (
    <div data-testid="mock-position-results-panel">{label}</div>
  ),
}));
vi.mock('@/components/insights/EndgameInsightsBlock', () => ({
  EndgameInsightsBlock: () => <div data-testid="mock-endgame-insights-block" />,
}));

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
  window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
});

afterEach(() => {
  cleanup();
  statsHookSpy.mockReset();
});

import { EndgamesPage } from '../Endgames';

// ── Harness ────────────────────────────────────────────────────────────────────

interface StoreProbe {
  applied: FilterState;
  setApplied: (next: FilterState) => void;
}
const probe = {} as StoreProbe;

/** Captures the shared filter store so tests can read and seed the applied value. */
function StoreProbeComponent() {
  const [applied, setApplied] = useFilterStore();
  useEffect(() => {
    probe.applied = applied;
    probe.setApplied = setApplied;
  }, [applied, setApplied]);
  return null;
}

/** In-test navigation, standing in for a tab click or browser back/forward. */
function NavButtons() {
  const navigate = useNavigate();
  return (
    <>
      <button type="button" data-testid="test-go-stats" onClick={() => navigate('/endgames/stats')} />
      <button type="button" data-testid="test-go-games" onClick={() => navigate('/endgames/games')} />
    </>
  );
}

function renderAt(path: '/endgames/stats' | '/endgames/games') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <TooltipProvider>
        <StoreProbeComponent />
        <NavButtons />
        <EndgamesPage />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

function go(testId: 'test-go-stats' | 'test-go-games') {
  act(() => {
    fireEvent.click(screen.getByTestId(testId));
  });
}

const SEEDED: FilterState = {
  ...DEFAULT_FILTERS,
  timeControls: ['blitz'],
  rated: true,
};

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('Endgames filter visibility', () => {
  it('renders no filter UI on the Stats tab', () => {
    renderAt('/endgames/stats');
    expect(screen.queryByTestId('btn-open-filter-drawer')).toBeNull();
    expect(screen.queryByTestId('drawer-filter-sidebar')).toBeNull();
    expect(screen.queryByTestId('sidebar-strip')).toBeNull();
    expect(screen.queryByTestId('sidebar-strip-btn-filters')).toBeNull();
  });

  it('renders the desktop strip icon and the mobile Filters button on the Games tab', () => {
    renderAt('/endgames/games');
    expect(screen.getByTestId('btn-open-filter-drawer')).toBeTruthy();
    expect(screen.getByTestId('sidebar-strip-btn-filters')).toBeTruthy();
  });

  it('hides the filter UI on a Games to Stats switch and restores it on the way back', () => {
    renderAt('/endgames/games');
    go('test-go-stats');
    expect(screen.queryByTestId('btn-open-filter-drawer')).toBeNull();
    expect(screen.queryByTestId('sidebar-strip-btn-filters')).toBeNull();

    go('test-go-games');
    expect(screen.getByTestId('btn-open-filter-drawer')).toBeTruthy();
    expect(screen.getByTestId('sidebar-strip-btn-filters')).toBeTruthy();
  });

  it('keeps the applied filters referentially equal across a Stats round trip', () => {
    renderAt('/endgames/games');
    act(() => probe.setApplied(SEEDED));
    const before = probe.applied;
    expect(before).toBe(SEEDED);

    go('test-go-stats');
    go('test-go-games');

    expect(probe.applied).toBe(before);
  });

  it('closes the open desktop panel on the way to Stats without committing the draft', () => {
    renderAt('/endgames/games');
    act(() => probe.setApplied(SEEDED));

    fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
    expect(screen.getByTestId('sidebar-panel')).toBeTruthy();
    // Edit the pending draft (not yet applied).
    fireEvent.click(screen.getByTestId('filter-rated-casual'));
    expect(probe.applied).toBe(SEEDED);

    go('test-go-stats');
    expect(screen.queryByTestId('sidebar-panel')).toBeNull();
    expect(probe.applied).toBe(SEEDED);

    // Back on Games the panel stays closed (it does not silently reopen).
    go('test-go-games');
    expect(screen.queryByTestId('sidebar-panel')).toBeNull();
    expect(probe.applied).toBe(SEEDED);
  });

  it('closes the open mobile drawer on the way to Stats without committing the draft', () => {
    renderAt('/endgames/games');
    act(() => probe.setApplied(SEEDED));

    fireEvent.click(screen.getByTestId('btn-open-filter-drawer'));
    expect(screen.getByTestId('drawer-filter-sidebar')).toBeTruthy();
    fireEvent.click(screen.getByTestId('filter-rated-casual'));
    expect(probe.applied).toBe(SEEDED);

    go('test-go-stats');
    expect(screen.queryByTestId('drawer-filter-sidebar')).toBeNull();
    expect(probe.applied).toBe(SEEDED);

    go('test-go-games');
    expect(screen.queryByTestId('drawer-filter-sidebar')).toBeNull();
    expect(probe.applied).toBe(SEEDED);
  });
});

describe('Endgames Games tab data', () => {
  it('requests the filtered stats with the applied filters and the Tier-2 gate', () => {
    renderAt('/endgames/games');
    act(() => probe.setApplied(SEEDED));

    const lastCall = statsHookSpy.mock.calls.at(-1)!;
    expect(lastCall[0]).toBe(SEEDED);
    expect(lastCall[1]).toEqual({ enabled: true });
  });

  it('does not fire the Games-tab stats query while the Stats tab is active', () => {
    renderAt('/endgames/stats');
    expect(statsHookSpy.mock.calls.at(-1)![1]).toEqual({ enabled: false });
    go('test-go-games');
    expect(statsHookSpy.mock.calls.at(-1)![1]).toEqual({ enabled: true });
  });

  it("renders the selected category's results panel and the match label", () => {
    renderAt('/endgames/games');
    expect(screen.getAllByTestId('mock-position-results-panel')[0]!.textContent).toBe('Mixed Endgame Results');
    const list = screen.getAllByTestId('mock-game-card-list')[0]!;
    expect(list.textContent).toContain('12 of 50');
    expect(list.textContent).toContain('games with an endgame matched');
  });
});

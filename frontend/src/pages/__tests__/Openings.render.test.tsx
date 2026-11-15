// @vitest-environment jsdom
/**
 * Openings.tsx render-level characterization test.
 *
 * This is the FIRST render-level oracle for OpeningsPage. No other test file
 * in the repository mounts `OpeningsPage` — `Openings.statsBoard.test.tsx`
 * deliberately avoids a full-page render (see its own header comment) and
 * only exercises `getBoardContainerClassName` in isolation.
 *
 * Mirrors `Analysis.test.tsx`'s provider stack (MemoryRouter +
 * QueryClientProvider + TooltipProvider), its single-mutable-state-object
 * mock convention, and its jsdom shims (matchMedia / ResizeObserver /
 * scrollTo / scrollIntoView). `ChessBoard` is mocked to a stub div, matching
 * `Bots.test.tsx`'s precedent — board mechanics are out of scope here.
 *
 * The desktop layout (`hidden lg:flex`) and the mobile layout (`lg:hidden`)
 * are BOTH unconditionally present in the React tree — jsdom does not
 * evaluate the Tailwind breakpoint classes, so both are always mounted
 * simultaneously and queryable, regardless of window size. Only the
 * SidebarLayout desktop panel content and the mobile MobileFilterDrawer
 * content are conditionally mounted (on `activePanel`/`open`), so the tests
 * below open each affordance before asserting on its content, and scope
 * queries with `within(...)` since the desktop `FilterPanel` and the mobile
 * `FilterPanel` share the same non-suffixed testids (e.g. `filter-recency`)
 * and could otherwise collide if both are open at once.
 */

import { useEffect } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';
import { OpeningsPage } from '@/pages/Openings';
import { apiClient } from '@/api/client';
import { useFilterStore } from '@/hooks/useFilterStore';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { FeatureRouteState } from '@/types/users';

// ── Mock ChessBoard: jsdom has no real board-gesture layer, and board
// mechanics are not what this test guards (mirrors Bots.test.tsx). ─────────
vi.mock('@/components/board/ChessBoard', () => ({
  ChessBoard: () => <div data-testid="chessboard" />,
}));

// ── Single-mutable-state-object mocks for the page's data hooks (Analysis.
// test.tsx convention). Each hook returns a fixed, minimal shape — this test
// asserts render/testid presence, not data-driven behavior. ────────────────
interface TestProfile {
  chess_com_game_count: number;
  lichess_game_count: number;
  feature_route?: FeatureRouteState | null;
  impersonation: null;
}
const DEFAULT_PROFILE: TestProfile = {
  chess_com_game_count: 10,
  lichess_game_count: 0,
  impersonation: null,
};
const profileState: { data: TestProfile | undefined } = { data: DEFAULT_PROFILE };
// Partial mock: hasImportedGames (used by the route hooks) stays real, only the
// profile query is replaced.
vi.mock('@/hooks/useUserProfile', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/hooks/useUserProfile')>()),
  useUserProfile: () => ({ data: profileState.data }),
}));

vi.mock('@/hooks/useNextMoves', () => ({
  useNextMoves: () => ({ data: undefined, isLoading: false, isError: false }),
}));

vi.mock('@/hooks/useOpenings', () => ({
  useOpeningsPositionQuery: () => ({ data: undefined, isLoading: false, isError: false }),
}));

const bookmarksState: { data: unknown[] } = { data: [] };
vi.mock('@/hooks/usePositionBookmarks', () => ({
  usePositionBookmarks: () => ({ data: bookmarksState.data }),
  useCreatePositionBookmark: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateMatchSide: () => ({ mutate: vi.fn() }),
  useTimeSeries: () => ({ data: undefined }),
  // Consumed by useOpeningsHandlers.ts, not Openings.tsx directly — this
  // module mock applies to every importer, so it must be provided too.
  useReorderPositionBookmarks: () => ({ mutate: vi.fn() }),
}));

vi.mock('@/hooks/useOutOfOpeningStats', () => ({
  useOutOfOpeningStats: () => ({ data: undefined, isError: false }),
}));

vi.mock('@/hooks/useStats', () => ({
  useMostPlayedOpenings: () => ({ data: undefined, isLoading: false, isError: false }),
  useBookmarkPhaseEntryMetrics: () => ({ data: undefined }),
}));

// ── apiClient: used directly by Openings.tsx (gameCount query) and
// indirectly by useEvalCoverage/useReadiness (EvalCoverageHeader /
// PositionResultsPanel). A single generic response satisfies every consumer
// via their own `?? default` fallbacks — none of them crash on extra or
// missing fields. ────────────────────────────────────────────────────────
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({
      data: {
        count: 0,
        pending_count: 0,
        total_count: 0,
        pct_complete: 100,
        analyzed_count: 0,
        tier1: true,
        tier2: true,
      },
    }),
    // POST bodies by endpoint: the feature-route mutation writes its response into the
    // query cache, so it must be a valid FeatureRouteState; the Stats tab renders the
    // insights response, so it must carry its four (empty) lists; anything else gets
    // the generic empty body.
    post: vi.fn().mockImplementation((url: string) => {
      const bodies: Record<string, unknown> = {
        '/users/me/feature-route': { steps: {}, current: null },
        '/insights/openings': {
          white_weaknesses: [],
          black_weaknesses: [],
          white_strengths: [],
          black_strengths: [],
        },
      };
      return Promise.resolve({ data: bodies[url] ?? {} });
    }),
  },
}));

// jsdom shims required by react-chessboard-adjacent code and responsive
// components (mirrors Analysis.test.tsx / Bots.test.tsx precedent).
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
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = vi.fn();
}

// The filter store is module-level and survives across tests, so a handle on its setter
// lets a case modify the filters and lets afterEach restore the defaults.
let setStoreFilters: ReturnType<typeof useFilterStore>[1] | null = null;
function StoreHandle() {
  const [, set] = useFilterStore();
  useEffect(() => {
    setStoreFilters = set;
  }, [set]);
  return null;
}

afterEach(() => {
  act(() => {
    setStoreFilters?.({ ...DEFAULT_FILTERS });
  });
  cleanup();
  setStoreFilters = null;
  profileState.data = DEFAULT_PROFILE;
  bookmarksState.data = [];
  vi.mocked(apiClient.post).mockClear();
  localStorage.clear();
});

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location-probe">{location.pathname}</div>;
}

function renderOpeningsPage(initialPath = '/openings/explorer') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <LocationProbe />
          <StoreHandle />
          <OpeningsPage />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('OpeningsPage render characterization', () => {
  it('renders the page shell and both tab strips (desktop + mobile)', () => {
    renderOpeningsPage();
    expect(screen.getByTestId('openings-page')).toBeTruthy();

    // Desktop tab strip
    const desktopTabs = screen.getByTestId('openings-tabs');
    expect(within(desktopTabs).getByTestId('tab-move-explorer')).toBeTruthy();
    expect(within(desktopTabs).getByTestId('tab-games')).toBeTruthy();
    expect(within(desktopTabs).getByTestId('tab-stats')).toBeTruthy();
    // The Insights subtab was merged into Stats (Phase 242, D-00): it is gone.
    expect(screen.queryByTestId('tab-insights')).toBeNull();

    // Mobile tab strip — both layouts are unconditionally in the tree (only
    // CSS-hidden via `hidden lg:flex` / `lg:hidden`, which jsdom ignores).
    const mobileTabs = screen.getByTestId('openings-tabs-mobile');
    expect(within(mobileTabs).getByTestId('tab-move-explorer-mobile')).toBeTruthy();
    expect(within(mobileTabs).getByTestId('tab-games-mobile')).toBeTruthy();
    expect(within(mobileTabs).getByTestId('tab-stats-mobile')).toBeTruthy();
    expect(screen.queryByTestId('tab-insights-mobile')).toBeNull();
  });

  it('redirects the legacy /openings/insights URL to the Stats tab with a replace (D-15)', async () => {
    renderOpeningsPage('/openings/insights');

    await waitFor(() => {
      expect(screen.getByTestId('location-probe').textContent).toBe('/openings/stats');
    });
    // Stats is the active tab (not a 404 and not the Moves tab) and its content renders.
    expect(screen.getByTestId('tab-stats').getAttribute('data-state')).toBe('active');
    expect(screen.getByTestId('tab-move-explorer').getAttribute('data-state')).toBe('inactive');
    expect(screen.getAllByTestId('opening-stats-color-bar').length).toBeGreaterThan(0);
  });

  it('desktop sidebar filters panel renders the desktop piece-filter testids and FilterPanel', async () => {
    renderOpeningsPage();
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));

    const panel = await waitFor(() => screen.getByTestId('sidebar-panel'));
    expect(within(panel).getByTestId('filter-piece-filter')).toBeTruthy();
    expect(within(panel).getByTestId('filter-piece-filter-mine')).toBeTruthy();
    expect(within(panel).getByTestId('filter-piece-filter-opponent')).toBeTruthy();
    expect(within(panel).getByTestId('filter-piece-filter-both')).toBeTruthy();
    // FilterPanel itself rendered inside the desktop panel (unsuffixed testid).
    expect(within(panel).getByTestId('filter-recency')).toBeTruthy();
  });

  it('desktop sidebar bookmarks panel renders the bookmark list', async () => {
    renderOpeningsPage();
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-bookmarks'));

    const panel = await waitFor(() => screen.getByTestId('sidebar-panel'));
    expect(within(panel).getByTestId('btn-bookmark')).toBeTruthy();
    expect(within(panel).getByTestId('btn-suggest-bookmarks')).toBeTruthy();
  });

  it('mobile filter drawer renders the -sidebar-suffixed piece-filter testids and FilterPanel', async () => {
    renderOpeningsPage();
    fireEvent.click(screen.getByTestId('subnav-filter-button'));

    const drawer = await waitFor(() => screen.getByTestId('drawer-filter-sidebar'));
    expect(within(drawer).getByTestId('filter-piece-filter-sidebar')).toBeTruthy();
    expect(within(drawer).getByTestId('filter-piece-filter-mine-sidebar')).toBeTruthy();
    expect(within(drawer).getByTestId('filter-piece-filter-opponent-sidebar')).toBeTruthy();
    expect(within(drawer).getByTestId('filter-piece-filter-both-sidebar')).toBeTruthy();
    // FilterPanel itself rendered inside the mobile drawer (unsuffixed testid).
    expect(within(drawer).getByTestId('filter-recency')).toBeTruthy();
  });

  it('mobile bookmarks drawer renders', async () => {
    renderOpeningsPage();
    fireEvent.click(screen.getByTestId('btn-open-bookmark-sidebar'));

    const drawer = await waitFor(() => screen.getByTestId('drawer-bookmark-sidebar'));
    expect(within(drawer).getByTestId('btn-bookmark-sidebar')).toBeTruthy();
    expect(within(drawer).getByTestId('btn-suggest-bookmarks-sidebar')).toBeTruthy();
  });

  it('desktop and mobile piece-filter testid sets are simultaneously distinct DOM nodes', async () => {
    renderOpeningsPage();
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
    await waitFor(() => screen.getByTestId('sidebar-panel'));
    fireEvent.click(screen.getByTestId('subnav-filter-button'));
    await waitFor(() => screen.getByTestId('drawer-filter-sidebar'));

    // Both open at once — the desktop and `-sidebar` testids are different
    // strings by design and must coexist.
    expect(screen.getByTestId('filter-piece-filter')).toBeTruthy();
    expect(screen.getByTestId('filter-piece-filter-sidebar')).toBeTruthy();
    expect(screen.getByTestId('filter-piece-filter')).not.toBe(
      screen.getByTestId('filter-piece-filter-sidebar'),
    );
  });

  it('closing the desktop filters panel unmounts its content (mutation-sensitive: guards the open/close affordance itself)', async () => {
    renderOpeningsPage();
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
    await waitFor(() => screen.getByTestId('sidebar-panel'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
    });
    await waitFor(() => {
      expect(screen.queryByTestId('sidebar-panel')).toBeNull();
    });
  });
});

// ── Route dot on the Openings subtabs and controls (phase 255, D-03, D-07) ─────

const ROUTE_PATH = '/users/me/feature-route';
const STEP_RECORD = { status: 'done', date: '2026-11-01', with_dot: false } as const;

/** A route state with the given steps done and no stamped current step. */
function routeWithDone(ids: readonly string[]): FeatureRouteState {
  return {
    steps: Object.fromEntries(ids.map((id) => [id, STEP_RECORD])),
    current: null,
  };
}

/** Sets the profile route state; the profile always has games (nav unlocked once readiness answers). */
function setRoute(featureRoute: FeatureRouteState | null): void {
  profileState.data = { ...DEFAULT_PROFILE, feature_route: featureRoute };
}

const THROUGH_OPENINGS = ['import', 'train', 'bots', 'openings'];
const THROUGH_PLAYED_AS = [...THROUGH_OPENINGS, 'openings-played-as'];
const THROUGH_FILTERS = [...THROUGH_PLAYED_AS, 'openings-filters'];

describe('OpeningsPage route dot on the Stats subtab', () => {
  it('puts the openings-stats dot on the Stats tab off /openings/stats, desktop and mobile', async () => {
    setRoute(routeWithDone(THROUGH_FILTERS));
    renderOpeningsPage('/openings/explorer');

    await waitFor(() => {
      expect(
        within(screen.getByTestId('tab-stats')).getByTestId('openings-stats-notification-dot'),
      ).toBeTruthy();
    });
    expect(
      within(screen.getByTestId('tab-stats-mobile')).getByTestId(
        'openings-stats-notification-dot-mobile',
      ),
    ).toBeTruthy();
  });

  it('shows no openings-stats dot on /openings/stats itself', async () => {
    setRoute(routeWithDone(THROUGH_FILTERS));
    renderOpeningsPage('/openings/stats');

    // Readiness resolves asynchronously; give the arbiter time to unlock, then assert absence.
    await waitFor(() => {
      expect(screen.getByTestId('tab-stats').getAttribute('data-state')).toBe('active');
    });
    expect(screen.queryByTestId('openings-stats-notification-dot')).toBeNull();
    expect(screen.queryByTestId('openings-stats-notification-dot-mobile')).toBeNull();
  });
});

/** The `{ action, step }` bodies posted to the feature-route endpoint so far. */
function routePosts(): unknown[] {
  return vi
    .mocked(apiClient.post)
    .mock.calls.filter(([url]) => url === ROUTE_PATH)
    .map(([, body]) => body);
}

/** Lets any fire-and-forget mutation reach the mocked client (for absence assertions). */
async function flushMutations(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

const DONE_PLAYED_AS = { action: 'done', step: 'openings-played-as' };
const DONE_FILTERS = { action: 'done', step: 'openings-filters' };

describe('OpeningsPage played-as route step', () => {
  it('puts the dot on the desktop strip colour button and the mobile toggle', async () => {
    setRoute(routeWithDone(THROUGH_OPENINGS));
    renderOpeningsPage('/openings/explorer');

    await waitFor(() => {
      expect(
        within(screen.getByTestId('sidebar-strip-btn-color')).getByTestId('played-as-notification-dot'),
      ).toBeTruthy();
    });
    expect(
      within(screen.getByTestId('btn-toggle-played-as')).getByTestId('played-as-notification-dot-mobile'),
    ).toBeTruthy();
    expect(screen.queryByTestId('filters-notification-dot')).toBeNull();
  });

  it('puts a mobile dot next to the Stats colour switch on /openings/stats', async () => {
    setRoute(routeWithDone(THROUGH_OPENINGS));
    renderOpeningsPage('/openings/stats');

    const dot = await waitFor(() => screen.getByTestId('played-as-notification-dot-mobile'));
    expect(screen.getByTestId('opening-color-switch-mobile').parentElement?.contains(dot)).toBe(true);
    expect(screen.getByTestId('played-as-notification-dot')).toBeTruthy();
  });

  it('records done when the desktop strip colour button is clicked', async () => {
    setRoute(routeWithDone(THROUGH_OPENINGS));
    renderOpeningsPage('/openings/explorer');
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-color'));
    await waitFor(() => expect(routePosts()).toContainEqual(DONE_PLAYED_AS));
  });

  it('records done when the mobile Moves/Games toggle is clicked', async () => {
    setRoute(routeWithDone(THROUGH_OPENINGS));
    renderOpeningsPage('/openings/explorer');
    fireEvent.click(screen.getByTestId('btn-toggle-played-as'));
    await waitFor(() => expect(routePosts()).toContainEqual(DONE_PLAYED_AS));
  });

  it('records done on a real colour switch on the mobile Stats switch', async () => {
    setRoute(routeWithDone(THROUGH_OPENINGS));
    renderOpeningsPage('/openings/stats');
    fireEvent.click(screen.getByTestId('opening-color-switch-mobile-black'));
    await waitFor(() => expect(routePosts()).toContainEqual(DONE_PLAYED_AS));
    expect(screen.getByTestId('opening-color-switch-mobile-black').getAttribute('aria-pressed')).toBe('true');
  });

  it('records done on a click of the already selected colour and leaves the colour alone', async () => {
    setRoute(routeWithDone(THROUGH_OPENINGS));
    renderOpeningsPage('/openings/stats');
    fireEvent.click(screen.getByTestId('opening-color-switch-mobile-white'));
    await waitFor(() => expect(routePosts()).toContainEqual(DONE_PLAYED_AS));
    expect(screen.getByTestId('opening-color-switch-mobile-white').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('opening-color-switch-mobile-black').getAttribute('aria-pressed')).toBe('false');
  });

  it('records the step even when the dot is on another step (D-15)', async () => {
    setRoute(routeWithDone(['import']));
    renderOpeningsPage('/openings/explorer');
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-color'));
    await waitFor(() => expect(routePosts()).toContainEqual(DONE_PLAYED_AS));
  });

  it('posts nothing for a profile without feature_route', async () => {
    setRoute(null);
    renderOpeningsPage('/openings/explorer');
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-color'));
    fireEvent.click(screen.getByTestId('btn-toggle-played-as'));
    await flushMutations();
    expect(routePosts()).toEqual([]);
  });
});

describe('OpeningsPage filters route step', () => {
  it('puts the dot on the desktop strip Filters button and the mobile Filters button', async () => {
    setRoute(routeWithDone(THROUGH_PLAYED_AS));
    renderOpeningsPage('/openings/explorer');

    await waitFor(() => {
      expect(
        within(screen.getByTestId('sidebar-strip-btn-filters')).getByTestId('filters-notification-dot'),
      ).toBeTruthy();
    });
    expect(
      within(screen.getByTestId('subnav-filter-button')).getByTestId('filters-notification-dot-mobile'),
    ).toBeTruthy();
    expect(screen.queryByTestId('played-as-notification-dot')).toBeNull();
  });

  it('puts the dot on the sticky Filters button on the mobile Stats subtab', async () => {
    setRoute(routeWithDone(THROUGH_PLAYED_AS));
    renderOpeningsPage('/openings/stats');
    await waitFor(() => {
      expect(
        within(screen.getByTestId('subnav-filter-button')).getByTestId('filters-notification-dot-mobile'),
      ).toBeTruthy();
    });
  });

  it('the red route dot wins over the brown modified-filters dot on the mobile Filters button (D-02)', async () => {
    setRoute(routeWithDone(THROUGH_PLAYED_AS));
    renderOpeningsPage('/openings/explorer');
    act(() => {
      setStoreFilters?.({ ...DEFAULT_FILTERS, rated: false });
    });
    await waitFor(() => {
      expect(screen.getByTestId('filters-notification-dot-mobile')).toBeTruthy();
    });
    expect(screen.queryByTestId('filters-modified-dot-mobile')).toBeNull();
  });

  it('records done when Apply is clicked in the desktop filters panel', async () => {
    setRoute(routeWithDone(THROUGH_PLAYED_AS));
    renderOpeningsPage('/openings/explorer');
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
    const panel = await waitFor(() => screen.getByTestId('sidebar-panel'));
    fireEvent.click(within(panel).getByTestId('btn-filter-apply'));
    await waitFor(() => expect(routePosts()).toContainEqual(DONE_FILTERS));
  });

  it('records done when Apply is clicked in the mobile filter drawer', async () => {
    setRoute(routeWithDone(THROUGH_PLAYED_AS));
    renderOpeningsPage('/openings/explorer');
    fireEvent.click(screen.getByTestId('subnav-filter-button'));
    const drawer = await waitFor(() => screen.getByTestId('drawer-filter-sidebar'));
    fireEvent.click(within(drawer).getByTestId('btn-filter-apply'));
    await waitFor(() => expect(routePosts()).toContainEqual(DONE_FILTERS));
  });

  it('posts nothing on Apply for a profile without feature_route', async () => {
    setRoute(null);
    renderOpeningsPage('/openings/explorer');
    fireEvent.click(screen.getByTestId('sidebar-strip-btn-filters'));
    const panel = await waitFor(() => screen.getByTestId('sidebar-panel'));
    fireEvent.click(within(panel).getByTestId('btn-filter-apply'));
    await flushMutations();
    expect(routePosts()).toEqual([]);
  });
});

describe('OpeningsPage bookmarks dot is gone (D-07)', () => {
  it('renders no bookmarks notification dot in any route state', async () => {
    // The retired localStorage hints used to unlock this dot; they must no longer matter.
    localStorage.setItem('played-as-hint-dismissed', 'true');
    localStorage.setItem('filters-hint-dismissed', 'true');
    for (const route of [null, routeWithDone(THROUGH_FILTERS), routeWithDone([])]) {
      setRoute(route);
      const { unmount } = renderOpeningsPage('/openings/explorer');
      await flushMutations();
      expect(screen.queryByTestId('bookmarks-notification-dot')).toBeNull();
      expect(screen.queryByTestId('bookmarks-notification-dot-mobile')).toBeNull();
      unmount();
    }
  });
});

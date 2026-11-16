// @vitest-environment jsdom
/**
 * Regression test for the Library landing redirect.
 *
 * Bug: /library with games redirected to /openings (outside the Library page).
 * Fix: redirect to /library/games for returning users, /library/import for new.
 *
 * Child components (ImportTab, GamesTab, StatsTab) are stubbed to isolate the
 * redirect logic from their data dependencies.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LibraryPage } from '../LibraryPage';
import type { FeatureRouteState } from '@/types/users';

// ── Stub heavy child components ───────────────────────────────────────────────

vi.mock('@/pages/library/ImportTab', () => ({
  ImportTab: () => <div data-testid="stub-import-tab" />,
}));
vi.mock('@/pages/library/GamesTab', () => ({
  GamesTab: () => <div data-testid="stub-games-tab" />,
}));
vi.mock('@/pages/library/StatsTab', () => ({
  StatsTab: () => <div data-testid="stub-stats-tab" />,
}));

// ── Controllable useUserProfile mock ──────────────────────────────────────────

const profileState: {
  chess_com_game_count: number;
  lichess_game_count: number;
  feature_route?: FeatureRouteState | null;
  impersonation: null;
} = { chess_com_game_count: 0, lichess_game_count: 0, impersonation: null };

// Partial mock: hasImportedGames (used by the route hooks) stays real, only the
// profile query is replaced.
vi.mock('@/hooks/useUserProfile', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/hooks/useUserProfile')>()),
  useUserProfile: () => ({
    data: { ...profileState },
  }),
}));

// No real readiness request: the route arbiter needs tier1 for the nav-unlock rule.
let tier1State = true;
vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({
    tier1: tier1State,
    tier2: true,
    pendingCount: 0,
    totalCount: 0,
    isLoading: false,
  }),
}));

afterEach(() => {
  cleanup();
  profileState.chess_com_game_count = 0;
  profileState.lichess_game_count = 0;
  profileState.feature_route = undefined;
  tier1State = true;
});

// ── Location spy ──────────────────────────────────────────────────────────────

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

// ── Render helper ─────────────────────────────────────────────────────────────

function renderLibrary(initialPath = '/library') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/library/*"
            element={
              <LibraryPage
                onImportStarted={vi.fn()}
                activeJobIds={[]}
                onJobDismissed={vi.fn()}
              />
            }
          />
          <Route path="*" element={<LocationDisplay />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('LibraryPage landing redirect', () => {
  it('with games, /library redirects to /library/games (not /openings)', () => {
    profileState.chess_com_game_count = 10;
    profileState.lichess_game_count = 0;

    renderLibrary('/library');

    // The library-page renders (not redirected away from the Library domain).
    expect(screen.getByTestId('library-page')).not.toBeNull();
    // Games tab content is present — LibraryPage renders desktop+mobile Tabs sections,
    // each containing all TabsContent blocks; getAllByTestId finds both instances.
    expect(screen.getAllByTestId('stub-games-tab').length).toBeGreaterThan(0);
    // Must NOT have redirected to /openings.
    // LocationDisplay renders only for paths outside /library/* — absent = good.
    const locationEl = screen.queryByTestId('location');
    expect(locationEl).toBeNull();
  });

  it('with zero games, /library redirects to /library/import', () => {
    profileState.chess_com_game_count = 0;
    profileState.lichess_game_count = 0;

    renderLibrary('/library');

    expect(screen.getByTestId('library-page')).not.toBeNull();
    expect(screen.getAllByTestId('stub-import-tab').length).toBeGreaterThan(0);
  });
});

// ── Route dot on the Library subtabs (phase 255, D-03) ────────────────────────

const STEP_RECORD = { status: 'done', date: '2026-11-01', with_dot: false } as const;

/** A route state with the given steps done and no stamped current step. */
function routeWithDone(ids: readonly string[]): FeatureRouteState {
  return {
    steps: Object.fromEntries(ids.map((id) => [id, STEP_RECORD])),
    current: null,
  };
}

const ALL_BUT_LIBRARY_STATS = [
  'import',
  'train',
  'bots',
  'openings',
  'openings-played-as',
  'openings-filters',
  'openings-stats',
  'endgames',
];

describe('LibraryPage route dot', () => {
  it('puts the import dot on the Import tab, desktop and mobile', () => {
    profileState.chess_com_game_count = 10;
    profileState.feature_route = routeWithDone([]);

    renderLibrary('/library/games');

    expect(
      within(screen.getByTestId('tab-import')).getByTestId('library-import-notification-dot'),
    ).not.toBeNull();
    expect(
      within(screen.getByTestId('tab-import-mobile')).getByTestId(
        'library-import-notification-dot-mobile',
      ),
    ).not.toBeNull();
    expect(screen.queryByTestId('library-stats-notification-dot')).toBeNull();
  });

  it('puts the library-stats dot on the Stats tab off /library/stats, desktop and mobile', () => {
    profileState.chess_com_game_count = 10;
    profileState.feature_route = routeWithDone(ALL_BUT_LIBRARY_STATS);

    renderLibrary('/library/games');

    expect(
      within(screen.getByTestId('tab-stats')).getByTestId('library-stats-notification-dot'),
    ).not.toBeNull();
    expect(
      within(screen.getByTestId('tab-stats-mobile')).getByTestId(
        'library-stats-notification-dot-mobile',
      ),
    ).not.toBeNull();
    expect(screen.queryByTestId('library-import-notification-dot')).toBeNull();
  });

  it('shows no dot on /library/stats itself (the visit completes the step)', () => {
    profileState.chess_com_game_count = 10;
    profileState.feature_route = routeWithDone(ALL_BUT_LIBRARY_STATS);

    renderLibrary('/library/stats');

    expect(screen.queryByTestId('library-stats-notification-dot')).toBeNull();
    expect(screen.queryByTestId('library-stats-notification-dot-mobile')).toBeNull();
  });

  it('shows no subtab dot with zero games and only library-stats unresolved (D-23 pause)', () => {
    profileState.feature_route = routeWithDone(ALL_BUT_LIBRARY_STATS);

    renderLibrary('/library/import');

    expect(screen.queryByTestId('library-stats-notification-dot')).toBeNull();
    expect(screen.queryByTestId('library-import-notification-dot')).toBeNull();
  });

  it('fails closed: a profile without feature_route has no subtab dot', () => {
    profileState.chess_com_game_count = 10;
    profileState.feature_route = null;

    renderLibrary('/library/games');

    expect(screen.queryByTestId('library-import-notification-dot')).toBeNull();
    expect(screen.queryByTestId('library-stats-notification-dot')).toBeNull();
  });
});

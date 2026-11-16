// @vitest-environment jsdom
/**
 * Tracer check for the feature-discovery route: the real useUserProfile, the
 * recorder and the read hooks wired together over a mocked API. A zero-game
 * signup opening /library/import is only stamped current (no dot, no done); once
 * the profile reports imported games, `import` is stored through
 * POST /users/me/feature-route and the dot hops to the Train nav item
 * (D-14 overruled by the owner on 2026-11-16).
 *
 * Assertions use toHaveBeenCalledWith / not.toHaveBeenCalledWith on specific
 * payloads, never an exact count of all calls, so later plans that add further
 * writes (the `current` stamp) keep these cases valid. The resend cases (h to m)
 * count the sends of one specific request (postCount), which stays valid too.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useNavigate } from 'react-router';
import type { FeatureRouteActionRequest, FeatureRouteState, UserProfile } from '@/types/users';

const apiGet = vi.fn();
const apiPost = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => apiGet(...args),
    post: (...args: unknown[]) => apiPost(...args),
  },
}));

let tier1State = true;
vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({ tier1: tier1State, tier2: false, pendingCount: 0, totalCount: 0, isLoading: false }),
}));

import { FeatureRouteRecorder } from '@/components/feature-route/FeatureRouteRecorder';
import { useRouteDot, useRouteDotPlacement } from '@/hooks/useFeatureRoute';
import { USER_PROFILE_QUERY_KEY, useUserProfile } from '@/hooks/useUserProfile';
import { applyRouteWrite } from '@/lib/featureRoute';

const FEATURE_ROUTE_PATH = '/users/me/feature-route';
const PROFILE_PATH = '/users/me/profile';
const FAKE_TODAY = '2026-11-15';
/** Longer than any resend cooldown of the recorder, so a clock jump of this size always clears it. */
const ONE_HOUR_MS = 3_600_000;
const IMPORTED_GAME_COUNT = 42;
/** Response time of the slow fake server, and how long a test watches for a POST loop. */
const SLOW_POST_MS = 30;
const LOOP_WATCH_MS = 400;

function Probe() {
  const placement = useRouteDotPlacement();
  const trainDot = useRouteDot('nav:/train');
  const navigate = useNavigate();
  const { data: profile } = useUserProfile();
  return (
    <>
      <span data-testid="route-probe">{placement?.slot ?? 'none'}</span>
      <span data-testid="route-probe-train">{String(trainDot)}</span>
      {/* A non-route profile field, to see whether a refetched profile reaches the cache. */}
      <span data-testid="route-probe-games">{profile == null ? 'loading' : String(profile.chess_com_game_count)}</span>
      <button type="button" data-testid="route-probe-go-bots" onClick={() => navigate('/bots')} />
      <button type="button" data-testid="route-probe-go-games" onClick={() => navigate('/library/games')} />
    </>
  );
}

function makeProfile(overrides: Partial<UserProfile>): UserProfile {
  return {
    email: 'route@example.com',
    is_superuser: false,
    is_guest: false,
    chess_com_username: null,
    lichess_username: null,
    created_at: '2026-11-15T00:00:00Z',
    last_login: null,
    chess_com_game_count: 0,
    lichess_game_count: 0,
    chess_com_last_sync_at: null,
    lichess_last_sync_at: null,
    impersonation: null,
    beta_enabled: false,
    leaderboard_hidden: false,
    current_strength: null,
    active_days: 1,
    feedback_ask: { active: false },
    feature_route: { steps: {}, current: null },
    ...overrides,
  } as UserProfile;
}

function doneRecord(): FeatureRouteState['steps'][string] {
  return { status: 'done', date: '2026-11-15', with_dot: false };
}

function mockProfile(profile: UserProfile, postResponse: FeatureRouteState | null = null): void {
  apiGet.mockImplementation(async (url: string) => {
    if (url === '/users/me/profile') return { data: profile };
    throw new Error(`unexpected GET ${url}`);
  });
  apiPost.mockImplementation(async (url: string) => {
    if (url === FEATURE_ROUTE_PATH) return { data: postResponse };
    throw new Error(`unexpected POST ${url}`);
  });
}

interface FakeServer {
  profile: UserProfile;
  /** When true the next feature-route POST rejects (once), like a network blip. */
  failNextPost: boolean;
}

/** A server that stores the route like the real one, so a refetch returns what the POSTs wrote. */
function mockStatefulServer(profile: UserProfile): FakeServer {
  const server: FakeServer = { profile, failNextPost: false };
  apiGet.mockImplementation(async (url: string) => {
    if (url === PROFILE_PATH) return { data: server.profile };
    throw new Error(`unexpected GET ${url}`);
  });
  apiPost.mockImplementation(async (url: string, request: FeatureRouteActionRequest) => {
    if (url !== FEATURE_ROUTE_PATH) throw new Error(`unexpected POST ${url}`);
    if (server.failNextPost) {
      server.failNextPost = false;
      throw new Error('network down');
    }
    const stored = server.profile.feature_route;
    if (stored == null) return { data: null };
    const next = applyRouteWrite(stored, request, { today: FAKE_TODAY, activeDays: server.profile.active_days });
    server.profile = { ...server.profile, feature_route: next };
    return { data: next };
  });
  return server;
}

/** How often exactly this request was POSTed. */
function postCount(request: FeatureRouteActionRequest): number {
  return apiPost.mock.calls.filter(([url, body]) => {
    const sent = body as FeatureRouteActionRequest;
    return url === FEATURE_ROUTE_PATH && sent.action === request.action && sent.step === request.step;
  }).length;
}

/** The probe's game count: 'loading' until the profile has loaded. */
function gameCountText(): string | null {
  return screen.getByTestId('route-probe-games').textContent;
}

/** Lets pending effects, mutation callbacks and mocked responses run. */
async function flushAsync(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function goTo(testid: 'route-probe-go-bots' | 'route-probe-go-games'): void {
  fireEvent.click(screen.getByTestId(testid));
}

function renderAt(path: string): { queryClient: QueryClient } {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <FeatureRouteRecorder />
        <Probe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { queryClient };
}

beforeEach(() => {
  apiGet.mockReset();
  apiPost.mockReset();
  tier1State = true;
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe('FeatureRouteRecorder', () => {
  it('(a) a zero-game signup on /library/import is stamped, not completed; the first imported games complete import and the dot hops to Train', async () => {
    tier1State = false;
    const server = mockStatefulServer(makeProfile({ feature_route: { steps: {}, current: null } }));
    const { queryClient } = renderAt('/library/import');

    // Phase 1: no games yet. Import is stamped current so the D-10 clock runs, but is not done.
    await waitFor(() => expect(gameCountText()).toBe('0'));
    await waitFor(() => expect(postCount({ action: 'current', step: 'import' })).toBe(1));
    await flushAsync();
    expect(apiPost).not.toHaveBeenCalledWith(FEATURE_ROUTE_PATH, { action: 'done', step: 'import' });
    expect(screen.getByTestId('route-probe').textContent).toBe('none');

    // Phase 2: the import delivers games (the nav is still locked, tier1 not finished).
    server.profile = { ...server.profile, chess_com_game_count: IMPORTED_GAME_COUNT };
    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
    });

    await waitFor(() =>
      expect(apiPost).toHaveBeenCalledWith(FEATURE_ROUTE_PATH, { action: 'done', step: 'import' }),
    );
    await waitFor(() => expect(screen.getByTestId('route-probe').textContent).toBe('nav:/train'));
    expect(screen.getByTestId('route-probe-train').textContent).toBe('true');
    expect(server.profile.feature_route?.steps.import?.status).toBe('done');
  });

  it('(b) visiting /train does not complete the train step (it completes on use, D-21)', async () => {
    mockProfile(makeProfile({ feature_route: { steps: { import: doneRecord() }, current: null } }));
    renderAt('/train');

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('route-probe').textContent).toBe('control:train-start'));
    expect(apiPost).not.toHaveBeenCalledWith(FEATURE_ROUTE_PATH, { action: 'done', step: 'train' });
  });

  it('(c) an impersonated session never writes', async () => {
    mockProfile(
      makeProfile({
        feature_route: { steps: {}, current: null },
        impersonation: { target_user_id: 5, target_email: 't@example.com' } as unknown as UserProfile['impersonation'],
      }),
    );
    renderAt('/library/import');

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('route-probe')).toBeTruthy());
    expect(apiPost).not.toHaveBeenCalled();
  });

  it('(d) a corrupt (null) feature_route shows no dot and posts nothing', async () => {
    mockProfile(makeProfile({ feature_route: null }));
    // /library/games, not the Import subtab: an empty route would put the dot on the
    // Import subtab and stamp `import` here, so both assertions below can fail.
    renderAt('/library/games');

    // Bug fix (WR-04): the test used to wait only for the profile GET to be called, so
    // both assertions ran before the profile reached the recorder and held trivially.
    // Wait for the loaded profile to render, then let any write go out.
    await waitFor(() => expect(gameCountText()).toBe('0'));
    await flushAsync();
    expect(screen.getByTestId('route-probe').textContent).toBe('none');
    expect(apiPost).not.toHaveBeenCalled();
  });

  it('(e) a zero-game account on /openings does not complete openings (A-2)', async () => {
    tier1State = false;
    mockProfile(
      makeProfile({
        feature_route: { steps: { import: doneRecord(), train: doneRecord(), bots: doneRecord() }, current: null },
      }),
    );
    renderAt('/openings');

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('route-probe')).toBeTruthy());
    expect(apiPost).not.toHaveBeenCalledWith(FEATURE_ROUTE_PATH, { action: 'done', step: 'openings' });
  });

  it('(f) the first unresolved step is stamped current and an expired one is skipped (D-10)', async () => {
    mockProfile(
      makeProfile({
        active_days: 5,
        feature_route: { steps: { import: doneRecord() }, current: { step: 'train', since_days: 2 } },
      }),
    );
    renderAt('/library/games');

    await waitFor(() => expect(apiPost).toHaveBeenCalledWith(FEATURE_ROUTE_PATH, { action: 'skip', step: 'train' }));
    await waitFor(() => expect(apiPost).toHaveBeenCalledWith(FEATURE_ROUTE_PATH, { action: 'current', step: 'bots' }));
  });

  it('(g) a locked first unresolved step is neither stamped nor skipped (D-23)', async () => {
    tier1State = false;
    mockProfile(
      makeProfile({
        active_days: 9,
        feature_route: {
          steps: { import: doneRecord(), train: doneRecord(), bots: doneRecord() },
          current: { step: 'openings', since_days: 2 },
        },
      }),
    );
    renderAt('/library/games');

    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('route-probe').textContent).toBe('none'));
    expect(apiPost).not.toHaveBeenCalled();
  });

  it('(h) a failed done POST is retried on a later visit, not at once (WR-01)', async () => {
    // Only Date is faked: the cooldown reads Date.now(), everything else keeps real timers.
    vi.useFakeTimers({ toFake: ['Date'] });
    tier1State = false; // openings stays locked, so the only route write in play is done:bots
    const doneBots: FeatureRouteActionRequest = { action: 'done', step: 'bots' };
    const server = mockStatefulServer(
      makeProfile({
        feature_route: { steps: { import: doneRecord(), train: doneRecord() }, current: { step: 'bots', since_days: 1 } },
      }),
    );
    server.failNextPost = true;
    const { queryClient } = renderAt('/bots');

    await waitFor(() => expect(postCount(doneBots)).toBe(1));
    await flushAsync();

    // The profile refetch brings the unresolved step back: the dot returns to Bots.
    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
    });
    goTo('route-probe-go-games');
    await waitFor(() => expect(screen.getByTestId('route-probe').textContent).toBe('nav:/bots'));

    // No tight loop: a revisit right after the failure does not resend.
    goTo('route-probe-go-bots');
    await flushAsync();
    expect(postCount(doneBots)).toBe(1);

    // A later visit retries the write, and the dot leaves Bots for good.
    vi.setSystemTime(Date.now() + ONE_HOUR_MS);
    goTo('route-probe-go-games');
    goTo('route-probe-go-bots');
    await waitFor(() => expect(postCount(doneBots)).toBe(2));
    await flushAsync();
    goTo('route-probe-go-games');
    await waitFor(() => expect(screen.getByTestId('route-probe').textContent).toBe('none'));
    expect(server.profile.feature_route?.steps.bots?.status).toBe('done');
  });

  describe('profile refetches around a route write (WR-02)', () => {
    const doneBots: FeatureRouteActionRequest = { action: 'done', step: 'bots' };

    function botsCurrentServer(): FakeServer {
      return mockStatefulServer(
        makeProfile({
          feature_route: { steps: { import: doneRecord(), train: doneRecord() }, current: { step: 'bots', since_days: 1 } },
        }),
      );
    }

    // invalidate: the stale path every caller in the app takes (App.tsx handleJobDone,
    // Import.tsx). refetch: a fetch on a profile that still counts as fresh.
    it.each(['invalidate', 'refetch'] as const)(
      '(i) repeats a profile refetch (%s) that the write cancelled',
      async (trigger) => {
        const server = botsCurrentServer();
        const { queryClient } = renderAt('/library/games');
        await waitFor(() => expect(gameCountText()).toBe('0'));

        // An import finished: the profile is fetched again and its GET is slow.
        server.profile = { ...server.profile, chess_com_game_count: IMPORTED_GAME_COUNT };
        let releaseSlowGet: () => void = () => {};
        const slowGet = new Promise<void>((resolve) => {
          releaseSlowGet = resolve;
        });
        apiGet.mockImplementationOnce(async () => {
          await slowGet;
          return { data: server.profile };
        });
        act(() => {
          if (trigger === 'invalidate') void queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
          else void queryClient.refetchQueries({ queryKey: USER_PROFILE_QUERY_KEY });
        });

        // Opening /bots posts done:bots while that GET is in flight, which cancels it.
        goTo('route-probe-go-bots');
        await waitFor(() => expect(postCount(doneBots)).toBe(1));
        await flushAsync();
        releaseSlowGet();

        await waitFor(() => expect(gameCountText()).toBe(String(IMPORTED_GAME_COUNT)));
      },
    );

    it('(j) refetches a profile that was already stale instead of marking it fresh', async () => {
      vi.useFakeTimers({ toFake: ['Date'] });
      const server = botsCurrentServer();
      renderAt('/library/games');
      await waitFor(() => expect(gameCountText()).toBe('0'));

      // The profile ages past its stale time; nothing has refetched it yet.
      server.profile = { ...server.profile, chess_com_game_count: IMPORTED_GAME_COUNT };
      vi.setSystemTime(Date.now() + ONE_HOUR_MS);

      goTo('route-probe-go-bots');
      await waitFor(() => expect(postCount(doneBots)).toBe(1));
      await waitFor(() => expect(gameCountText()).toBe(String(IMPORTED_GAME_COUNT)));
    });

    it('(k) waits for the last queued write before it refetches', async () => {
      vi.useFakeTimers({ toFake: ['Date'] });
      const currentOpenings: FeatureRouteActionRequest = { action: 'current', step: 'openings' };
      const server = botsCurrentServer();
      server.profile = { ...server.profile, chess_com_game_count: IMPORTED_GAME_COUNT };
      // Hold the second write (the current stamp) until the test releases it.
      const storeWrite = apiPost.getMockImplementation();
      let releaseStamp: () => void = () => {};
      const stampHeld = new Promise<void>((resolve) => {
        releaseStamp = resolve;
      });
      apiPost.mockImplementation(async (url: string, request: FeatureRouteActionRequest) => {
        if (request.action === 'current') await stampHeld;
        return storeWrite?.(url, request);
      });
      renderAt('/library/games');
      await waitFor(() => expect(gameCountText()).toBe(String(IMPORTED_GAME_COUNT)));
      const getsBeforeWrites = apiGet.mock.calls.length;

      // Stale profile, then /bots: done:bots and current:openings are queued in one effect.
      vi.setSystemTime(Date.now() + ONE_HOUR_MS);
      goTo('route-probe-go-bots');
      await waitFor(() => expect(postCount(currentOpenings)).toBe(1));
      await flushAsync();
      // The first write has settled, the second is still on its way: no refetch yet.
      expect(postCount(doneBots)).toBe(1);
      expect(apiGet.mock.calls.length).toBe(getsBeforeWrites);

      releaseStamp();
      await waitFor(() => expect(apiGet.mock.calls.length).toBe(getsBeforeWrites + 1));
      expect(server.profile.feature_route?.current?.step).toBe('openings');
    });
  });

  it('(l) a current stamp the server does not confirm is not re-POSTed at network speed (WR-03)', async () => {
    const currentTrain: FeatureRouteActionRequest = { action: 'current', step: 'train' };
    const unstamped: FeatureRouteState = { steps: { import: doneRecord() }, current: null };
    mockProfile(makeProfile({ feature_route: unstamped }));
    // Every write is answered late and with the unchanged state: the stamp never sticks.
    apiPost.mockImplementation(async () => {
      await new Promise((resolve) => setTimeout(resolve, SLOW_POST_MS));
      return { data: unstamped };
    });
    renderAt('/library/games');

    await waitFor(() => expect(postCount(currentTrain)).toBe(1));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, LOOP_WATCH_MS));
    });
    expect(postCount(currentTrain)).toBe(1);
  });

  it('(m) a stamp removed by delete-all-games is set again on unlock in the same session (D-23)', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    const currentOpenings: FeatureRouteActionRequest = { action: 'current', step: 'openings' };
    const steps = { import: doneRecord(), train: doneRecord(), bots: doneRecord() };
    const server = mockStatefulServer(
      makeProfile({ chess_com_game_count: IMPORTED_GAME_COUNT, feature_route: { steps, current: null } }),
    );
    const { queryClient } = renderAt('/library/games');
    const refetchProfile = (): Promise<void> =>
      act(async () => {
        await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      });

    await waitFor(() => expect(postCount(currentOpenings)).toBe(1));
    await waitFor(() => expect(server.profile.feature_route?.current?.step).toBe('openings'));
    await flushAsync();

    // Delete all games: the server drops the stamp and the nav locks, so the route pauses.
    server.profile = { ...server.profile, chess_com_game_count: 0, feature_route: { steps, current: null } };
    await refetchProfile();
    await waitFor(() => expect(screen.getByTestId('route-probe').textContent).toBe('none'));
    await flushAsync();
    expect(postCount(currentOpenings)).toBe(1);

    // A later re-import unlocks the nav: the step is stamped afresh.
    vi.setSystemTime(Date.now() + ONE_HOUR_MS);
    server.profile = { ...server.profile, chess_com_game_count: IMPORTED_GAME_COUNT };
    await refetchProfile();
    await waitFor(() => expect(postCount(currentOpenings)).toBe(2));
    await waitFor(() => expect(server.profile.feature_route?.current?.step).toBe('openings'));
  });
});

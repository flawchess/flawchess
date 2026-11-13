// @vitest-environment jsdom
/**
 * Train.subnav.test.tsx — page-level coverage of the /train layout: the
 * URL-routed tabs, and the D-06 / D-15 / D-16 rules that keep a visit to
 * Leaderboard from creating a session or loading the engine.
 *
 * Mocks mirror Train.solveLoop.test.tsx (profile, ChessBoard, trainApi,
 * FakeWorker). `Worker` is a counting `vi.fn` constructor so a test can assert
 * how many grading engines a visit constructed.
 */
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  act,
  cleanup,
  configure,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { useEffect } from 'react';
import type { ComponentType } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useLocation, useNavigate } from 'react-router';
import type { NavigateFunction } from 'react-router';
import { waitForReveal } from '@/components/train/__tests__/revealTestUtils';
import { saveTrainRevealCache } from '@/lib/trainRevealCache';
import { readStreakLastSeen } from '@/lib/streakArrival';
import { landingHost } from '@/lib/trainBotCopy';
import type { CachedTrainReveal } from '@/lib/trainRevealCache';
import { TooltipProvider } from '@/components/ui/tooltip';
import type {
  TrainSessionResponse,
  TrainProgressResponse,
  TrainArchiveItem,
  TrainArchiveResponse,
  TrainSettingsResponse,
  UnclaimedMedal,
} from '@/types/train';
import type { UserProfile } from '@/types/users';
import type { BlunderCheckSessionResponse } from '@/types/blunderCheck';

// Mutable profile flags: hasImportedGames reads `profileState.hasGames`.
const profileState = vi.hoisted(() => ({ hasGames: true, beta: false }));

/** The profile's email keys the streak snapshot; `feedback_ask` activates Hilda's ask. */
const PROFILE_EMAIL = 'runner@example.com';
const FEEDBACK_ASK_ACTIVE_DAYS = 12;
const PROFILE = {
  is_guest: false,
  email: PROFILE_EMAIL,
  feedback_ask: { active: true },
  active_days: FEEDBACK_ASK_ACTIVE_DAYS,
} as unknown as UserProfile;
/** Stable identity (the page reads the profile every render): the beta variant of PROFILE. */
const BETA_PROFILE = { ...PROFILE, beta_enabled: true } as UserProfile;

vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({
    data: profileState.beta ? BETA_PROFILE : PROFILE,
    isPending: false,
    isError: false,
  }),
  hasImportedGames: () => profileState.hasGames,
}));

// A hoisted spy for the feedback-ask mutation: the bubble POSTs a 'view' on mount.
const feedbackAskMutate = vi.hoisted(() => vi.fn());
vi.mock('@/hooks/useFeedbackAsk', () => ({
  useFeedbackAsk: () => ({ mutate: feedbackAskMutate }),
}));

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
  ResizeObserverStub;

vi.mock('@/components/board/ChessBoard', () => ({
  ChessBoard: ({ position }: { position: string }) => (
    <div data-testid="chessboard" data-position={position} />
  ),
}));

// The medal dialog fires confetti on open; jsdom has no canvas.
vi.mock('@/lib/confetti', async () => {
  const actual = await vi.importActual<typeof import('@/lib/confetti')>('@/lib/confetti');
  return { ...actual, fireWinConfetti: vi.fn(), firePartialConfetti: vi.fn() };
});

configure({ asyncUtilTimeout: 10000 });

// ─── trainApi mock ──────────────────────────────────────────────────────────

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const SESSION_RESPONSE: TrainSessionResponse = {
  session_id: 1,
  session_date: '2026-07-25',
  expires_on: '2026-07-26',
  puzzle_count: 1,
  requested_count: 1,
  solved_count: 0,
  blob_pending_count: 0,
  puzzles: [
    { position: 1, game_id: 100, ply: 20, fen: START_FEN, side_to_move: 'white', last_move_uci: 'd7d5' },
  ],
  solved_results: [],
  is_warmup: false,
};

const SETTINGS_RESPONSE: TrainSettingsResponse = {
  timezone: 'UTC',
  weekday_mask: 127,
  puzzles_per_session: 5,
  reminder_enabled: false,
  reminder_hour: 9,
  reminder_intent_at: null,
  intro_seen_at: '2026-01-01T00:00:00Z',
  reveal_tour_stage: 3,
  sr_explained_at: '2026-01-01T00:00:00Z',
  has_mobile_subscription: false,
};

const DEFAULT_TRAIN_PROGRESS: TrainProgressResponse = {
  session_streak_count: 0,
  shield_level: 0,
  current_week_completed: 0,
  current_week_required: null,
  streak_reset_notice: false,
  mastered_count: 0,
  parked_count: 0,
  waiting_count: 0,
  pool_state: 'available',
  next_due_date: null,
  badge_visible: false,
};

const composeOrResumeSession = vi.fn(async (): Promise<TrainSessionResponse> => SESSION_RESPONSE);
const markSessionEntered = vi.fn<(sessionId: number) => Promise<void>>(async () => undefined);
const OPEN_BLUNDER_SESSION = null;
const BLUNDER_SESSION_RESPONSE: BlunderCheckSessionResponse = {
  session_id: 7,
  window_count: 6,
  current_position: 0,
  session_points: 0,
  windows: [],
};
const blunderGetOpenSession = vi.fn(
  async (): Promise<BlunderCheckSessionResponse | null> => OPEN_BLUNDER_SESSION,
);
const blunderComposeOrResume = vi.fn(
  async (): Promise<BlunderCheckSessionResponse> => BLUNDER_SESSION_RESPONSE,
);
const getSettings = vi.fn(async () => SETTINGS_RESPONSE);
const getProgress = vi.fn(async () => DEFAULT_TRAIN_PROGRESS);
const EMPTY_LEADERBOARD_BOARD = { rows: [], viewer: null, last_week: null };
const getLeaderboard = vi.fn(async () => ({
  week_start: '2032-01-05',
  week_end: '2032-01-12',
  seconds_remaining: 388800,
  points: EMPTY_LEADERBOARD_BOARD,
  accuracy: EMPTY_LEADERBOARD_BOARD,
}));
/** One mastered puzzle at ply 20, so its Analyze link lands on ply 19. */
const ARCHIVE_ITEM: TrainArchiveItem = {
  game_id: 100,
  ply: 20,
  fen: START_FEN,
  last_move_uci: 'd7d5',
  played_move_uci: 'g1f3',
  played_move_san: 'Nf3',
  severity: 'blunder',
  user_color: 'white',
  last_solved_at: '2026-10-03T10:00:00Z',
  fail_count: 0,
  white_username: 'me',
  black_username: 'rival',
  white_rating: 1500,
  black_rating: 1480,
  played_at: '2026-09-30T10:00:00Z',
  time_control_bucket: 'blitz',
  time_control_str: '600+0',
};
const ARCHIVE_PAGE_SIZE_UNDER_TEST = 24;
const getArchive = vi.fn<
  (params: { list: string; limit: number; offset: number }) => Promise<TrainArchiveResponse>
>(async () => ({ items: [ARCHIVE_ITEM], total: 1 }));
const getUnclaimedMedals = vi.fn<() => Promise<{ medals: UnclaimedMedal[] }>>(async () => ({
  medals: [],
}));
const TWO_MEDALS: UnclaimedMedal[] = [
  { week_start: '2032-01-05', board: 'points', medal: 'gold', value: 412, shared: false },
  { week_start: '2032-01-05', board: 'accuracy', medal: 'bronze', value: 87, shared: true },
];
const stampOnboarding = vi.fn<(step: string) => Promise<TrainSettingsResponse>>(
  async () => SETTINGS_RESPONSE,
);

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      composeOrResumeSession: () => composeOrResumeSession(),
      markSessionEntered: (sessionId: number) => markSessionEntered(sessionId),
      solvePuzzle: vi.fn(),
      revealPuzzle: vi.fn(),
      getSettings: () => getSettings(),
      updateSettings: vi.fn(),
      getProgress: () => getProgress(),
      getLeaderboard: () => getLeaderboard(),
      getArchive: (params: { list: string; limit: number; offset: number }) => getArchive(params),
      getUnclaimedMedals: () => getUnclaimedMedals(),
      claimMedals: vi.fn(),
      stampOnboarding: (step: string) => stampOnboarding(step),
    },
    blunderCheckApi: {
      getOpenSession: () => blunderGetOpenSession(),
      composeOrResumeSession: () => blunderComposeOrResume(),
      // The window request stays pending: this file only checks the tab shell.
      startWindow: () => new Promise(() => {}),
      answer: vi.fn(),
      finishSession: vi.fn(),
    },
    postReviewKeepalive: vi.fn(),
    libraryApi: {
      ...actual.libraryApi,
      getGame: vi.fn().mockRejectedValue(new Error('not exercised')),
      getTacticLines: vi.fn().mockRejectedValue(new Error('not exercised')),
    },
  };
});

// ─── Fake Worker ────────────────────────────────────────────────────────────

class FakeWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  terminated = false;

  postMessage(msg: string | { progressPort: unknown }): void {
    if (typeof msg !== 'string') return;
    if (msg === 'uci') {
      this.emit('uciok');
    } else if (msg === 'isready') {
      this.emit('readyok');
    } else if (msg.startsWith('go ')) {
      queueMicrotask(() => {
        this.emit('info depth 10 multipv 1 score cp 20 nodes 1000 pv e2e4');
        this.emit('bestmove e2e4');
      });
    }
  }

  terminate(): void {
    this.terminated = true;
  }

  private emit(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

let WorkerCtor: ReturnType<typeof vi.fn>;

// ─── Render helper ──────────────────────────────────────────────────────────

let TrainPage: ComponentType;

/** Holds the router's `navigate`, to simulate browser Back. */
const navigateRef: { current: NavigateFunction | null } = { current: null };

/** Exposes the current location and captures `navigate`. */
function LocationProbe() {
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    navigateRef.current = navigate;
  }, [navigate]);
  return <div data-testid="location-probe">{location.pathname + location.search}</div>;
}

function renderTrainPage(initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <LocationProbe />
          <TrainPage />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function clickTab(testId: string): void {
  // Radix tab triggers ignore a plain click; they select on mousedown.
  fireEvent.mouseDown(screen.getByTestId(testId), { button: 0, ctrlKey: false });
}

function currentPath(): string {
  return screen.getByTestId('location-probe').textContent ?? '';
}

/** The Leaderboard tab's own card (Today no longer renders one). */
function leaderboardPanelCard(): HTMLElement {
  return within(screen.getByTestId('train-leaderboard-panel')).getByTestId('train-leaderboard-card');
}

beforeAll(async () => {
  TrainPage = (await import('@/pages/Train')).default;
});

beforeEach(() => {
  profileState.hasGames = true;
  profileState.beta = false;
  navigateRef.current = null;
  blunderGetOpenSession.mockClear();
  blunderComposeOrResume.mockClear();
  WorkerCtor = vi.fn(function (this: unknown) {
    return new FakeWorker();
  });
  vi.stubGlobal('Worker', WorkerCtor);
  vi.stubGlobal('scrollTo', vi.fn());
  // LazyMiniBoard (the Archive cards) waits for an intersection before it
  // renders its board; fire it at once. Stubbed here, not at module level,
  // because afterEach's unstubAllGlobals would drop a module-level stub.
  vi.stubGlobal(
    'IntersectionObserver',
    class {
      constructor(private callback: (entries: { isIntersecting: boolean }[]) => void) {}
      observe(): void {
        this.callback([{ isIntersecting: true }]);
      }
      unobserve(): void {}
      disconnect(): void {}
    },
  );
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation((query: string) => ({
      matches: query === '(min-width: 640px)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
  composeOrResumeSession.mockReset();
  composeOrResumeSession.mockImplementation(async () => SESSION_RESPONSE);
  markSessionEntered.mockClear();
  getSettings.mockClear();
  getSettings.mockImplementation(async () => SETTINGS_RESPONSE);
  getArchive.mockReset();
  getArchive.mockImplementation(async () => ({ items: [ARCHIVE_ITEM], total: 1 }));
  stampOnboarding.mockClear();
  feedbackAskMutate.mockClear();
  getUnclaimedMedals.mockReset();
  getUnclaimedMedals.mockImplementation(async () => ({ medals: [] }));
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  sessionStorage.clear();
  localStorage.clear();
});

describe('Train layout: tabs and D-06 session rules', () => {
  it('a /train/leaderboard deep link shows the tabs and board with no session POST and no Worker', async () => {
    renderTrainPage(['/train/leaderboard']);

    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    // Let any would-be effect settle before asserting a count of zero.
    await act(async () => {});
    expect(composeOrResumeSession).toHaveBeenCalledTimes(0);
    expect(WorkerCtor).toHaveBeenCalledTimes(0);
    expect(screen.queryByTestId('train-start-screen')).toBeNull();
  });

  it('/train fires one POST and constructs one Worker', async () => {
    renderTrainPage(['/train']);

    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    await waitFor(() => expect(WorkerCtor).toHaveBeenCalledTimes(1));
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);
  });

  it('Today -> Leaderboard -> Today keeps one POST and one Worker, with no Loading flash on return', async () => {
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    await waitFor(() => expect(WorkerCtor).toHaveBeenCalledTimes(1));

    clickTab('tab-train-leaderboard');
    expect(currentPath()).toBe('/train/leaderboard');
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());

    clickTab('tab-train-today');
    expect(currentPath()).toBe('/train');
    expect(screen.queryByTestId('train-session-loading')).toBeNull();
    expect(screen.getByTestId('btn-train-start')).not.toBeNull();

    await act(async () => {});
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);
    expect(WorkerCtor).toHaveBeenCalledTimes(1);
  });

  it('redirects an unknown /train/* path to /train', async () => {
    renderTrainPage(['/train/foo']);

    await waitFor(() => expect(currentPath()).toBe('/train'));
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
  });

  it('a tab click navigates to that tab path', async () => {
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());

    clickTab('tab-train-leaderboard');
    expect(currentPath()).toBe('/train/leaderboard');
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0 });
  });
});

describe('Train layout: beta-only Blunder check tab (D-01)', () => {
  it('a beta user sees the tab; Start composes one session and shows the counter and points', async () => {
    profileState.beta = true;
    renderTrainPage(['/train/blunder-check']);

    await waitFor(() => expect(screen.getByTestId('train-blunder-check-panel')).not.toBeNull());
    expect(screen.getByTestId('tab-train-blunder-check')).not.toBeNull();
    fireEvent.click(await screen.findByTestId('blunder-check-btn-start'));

    await waitFor(() =>
      expect(screen.getByTestId('blunder-check-window-counter').textContent).toBe('1 of 6'),
    );
    expect(screen.getByTestId('blunder-check-points').textContent).toBe('0 pts');
    expect(blunderComposeOrResume).toHaveBeenCalledTimes(1);
  });

  it('a non-beta user sees three tabs and /train/blunder-check lands on /train', async () => {
    renderTrainPage(['/train/blunder-check']);

    await waitFor(() => expect(currentPath()).toBe('/train'));
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.queryByTestId('tab-train-blunder-check')).toBeNull();
    expect(screen.queryByTestId('train-blunder-check-panel')).toBeNull();
    expect(screen.getByTestId('tab-train-archive')).not.toBeNull();
  });

  it('a beta blunder-check visit constructs no Worker and composes no Today session (Today latch)', async () => {
    profileState.beta = true;
    renderTrainPage(['/train/blunder-check']);

    await waitFor(() => expect(screen.getByTestId('train-blunder-check-panel')).not.toBeNull());
    await screen.findByTestId('blunder-check-btn-start');
    await act(async () => {});
    expect(WorkerCtor).toHaveBeenCalledTimes(0);
    expect(composeOrResumeSession).toHaveBeenCalledTimes(0);
    expect(blunderComposeOrResume).toHaveBeenCalledTimes(0);
    expect(screen.queryByTestId('train-start-screen')).toBeNull();
  });
});

describe('Train layout: D-15 wrapper width', () => {
  it('keeps the same max-w-7xl wrapper class on Today, Leaderboard and Archive', async () => {
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    const todayClass = screen.getByTestId('train-page').className;
    expect(todayClass).toContain('max-w-7xl');

    clickTab('tab-train-leaderboard');
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    expect(screen.getByTestId('train-page').className).toBe(todayClass);

    clickTab('tab-train-archive');
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    expect(screen.getByTestId('train-page').className).toBe(todayClass);
    // Archive uses the full width: no narrow column around the grid.
    expect(screen.getByTestId('train-archive-panel').className).not.toContain('max-w-');
  });
});

// ─── Immersive first paint, Back out of the loop, deferred re-read ──────────

const RESTORE_SESSION_ID = 4;
const RESTORE_REMAINING_FEN = 'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3';

function makeCachedReveal(sessionId: number): CachedTrainReveal {
  return {
    sessionId,
    puzzle: {
      position: 1,
      game_id: 100,
      ply: 20,
      fen: START_FEN,
      side_to_move: 'white',
      last_move_uci: 'd7d5',
    },
    verdict: {
      correct_guess: true,
      correct_move: false,
      move_quality: 'wrong',
      puzzle_type: 'sharp',
      item_status: 'active',
      streak: 0,
      due_date: null,
      session_complete: false,
    },
    guess: 'critical',
    playedMoveUci: 'g1f3',
    gradeResult: {
      moveTier: 'wrong',
      bestMoveUci: 'e2e4',
      esBefore: 0.55,
      esAfter: 0.48,
      bestLine: { moves: ['e2e4', 'e7e5'], evalCp: 30, evalMate: null },
      playedLine: { moves: ['g1f3', 'd7d5'], evalCp: -10, evalMate: null },
    },
  };
}

/** The resumed session a real Analyze -> Back lands in: only the unsolved puzzle remains. */
const RESTORE_SESSION: TrainSessionResponse = {
  session_id: RESTORE_SESSION_ID,
  session_date: '2026-07-25',
  expires_on: '2026-07-26',
  puzzle_count: 2,
  requested_count: 2,
  solved_count: 1,
  blob_pending_count: 0,
  puzzles: [
    { position: 2, game_id: 200, ply: 30, fen: RESTORE_REMAINING_FEN, side_to_move: 'white', last_move_uci: 'c8e6' },
  ],
  solved_results: [
    { correct_guess: true, move_quality: 'wrong', source: 'sr_item', item_status: 'active', due_date: '2026-07-28' },
  ],
  is_warmup: false,
};

/** Holds the next session compose open until `resolve` is called. */
function holdNextCompose(): { resolve: (session: TrainSessionResponse) => void } {
  let resolve: (session: TrainSessionResponse) => void = () => undefined;
  // The executor runs synchronously, so `resolve` is bound before the mutation
  // (which calls its mutationFn asynchronously) ever asks for the promise.
  const pending = new Promise<TrainSessionResponse>((res) => {
    resolve = res;
  });
  composeOrResumeSession.mockImplementationOnce(() => pending);
  return { resolve };
}

function navigateTo(to: string | number): void {
  act(() => {
    // `number` is history delta (Back); the overloads need separate calls.
    if (typeof to === 'number') navigateRef.current?.(to);
    else navigateRef.current?.(to);
  });
}

describe('Train layout: D-06 immersive states', () => {
  it('shows no tabs on the first paint of a cached reveal, and keeps them hidden once the session matches', async () => {
    saveTrainRevealCache(makeCachedReveal(RESTORE_SESSION_ID));
    const held = holdNextCompose();
    renderTrainPage(['/train']);

    // First paint, session unresolved: the subnav must not flash.
    expect(screen.queryByTestId('train-tabs')).toBeNull();
    await act(async () => {
      held.resolve(RESTORE_SESSION);
    });
    await waitForReveal();
    expect(screen.queryByTestId('train-tabs')).toBeNull();
  });

  it('shows the tabs and clears the cache when the cached reveal belongs to another session', async () => {
    saveTrainRevealCache(makeCachedReveal(999));
    const held = holdNextCompose();
    renderTrainPage(['/train']);

    expect(screen.queryByTestId('train-tabs')).toBeNull();
    await act(async () => {
      held.resolve(SESSION_RESPONSE);
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    expect(sessionStorage.getItem('train_reveal_cache')).toBeNull();
  });

  it('shows the tabs for a cached reveal on /train/leaderboard, with no POST', async () => {
    saveTrainRevealCache(makeCachedReveal(RESTORE_SESSION_ID));
    renderTrainPage(['/train/leaderboard']);

    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    await act(async () => {});
    expect(composeOrResumeSession).toHaveBeenCalledTimes(0);
  });

  it('restored reveal, then Leaderboard: the solve screen is gone and the card shows', async () => {
    saveTrainRevealCache(makeCachedReveal(RESTORE_SESSION_ID));
    composeOrResumeSession.mockImplementationOnce(async () => RESTORE_SESSION);
    renderTrainPage(['/train']);
    await waitForReveal();

    navigateTo('/train/leaderboard');

    await waitFor(() => expect(currentPath()).toBe('/train/leaderboard'));
    expect(screen.queryByTestId('train-reveal')).toBeNull();
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
  });

  it('hides the tabs after Start', async () => {
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();

    fireEvent.click(screen.getByTestId('btn-train-start'));

    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
    expect(screen.queryByTestId('train-tabs')).toBeNull();
  });

  it('Back out of a running loop removes the solve screen with no POST, and the return re-reads once', async () => {
    renderTrainPage(['/train/leaderboard']);
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());

    clickTab('tab-train-today');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-start'));
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);

    navigateTo(-1);

    await waitFor(() => expect(currentPath()).toBe('/train/leaderboard'));
    expect(screen.queryByTestId('chessboard')).toBeNull();
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    await act(async () => {});
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);

    navigateTo('/train');

    await waitFor(() => expect(composeOrResumeSession).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.queryByTestId('chessboard')).toBeNull();
  });

  it('the first click from Leaderboard to Today never paints an empty state before the loading state', async () => {
    renderTrainPage(['/train/leaderboard']);
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    const held = holdNextCompose();

    // act() flushes the mount effect before the test can look, so the first
    // commit is only observable through the DOM mutations it made.
    const observer = new MutationObserver(() => undefined);
    observer.observe(document.body, { childList: true, subtree: true });
    clickTab('tab-train-today');
    const painted = observer
      .takeRecords()
      .flatMap((record) => Array.from(record.addedNodes))
      .filter((node): node is Element => node instanceof Element)
      .flatMap((el) => [el, ...Array.from(el.querySelectorAll('[data-testid]'))])
      .map((el) => el.getAttribute('data-testid'));
    observer.disconnect();

    expect(painted).toContain('train-session-loading');
    expect(painted).not.toContain('train-start-screen');
    expect(screen.getByTestId('train-session-loading')).not.toBeNull();
    await act(async () => {
      held.resolve(SESSION_RESPONSE);
    });
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
  });
});

describe('Train layout: D-16 tabs on the landing states', () => {
  it('shows the tabs during the first-visit intro', async () => {
    getSettings.mockImplementation(async () => ({ ...SETTINGS_RESPONSE, intro_seen_at: null }));
    renderTrainPage(['/train']);

    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
  });

  it('shows the tabs in the no-games state', async () => {
    profileState.hasGames = false;
    renderTrainPage(['/train']);

    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
  });

  it('shows the tabs in the empty state', async () => {
    getProgress.mockImplementation(async () => ({ ...DEFAULT_TRAIN_PROGRESS, pool_state: 'no_material' }));
    composeOrResumeSession.mockImplementationOnce(async () => ({
      ...SESSION_RESPONSE,
      session_id: null,
      puzzle_count: 0,
      requested_count: 0,
      puzzles: [],
    }));
    renderTrainPage(['/train']);

    await waitFor(() => expect(screen.getByTestId('train-empty-no-material')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
  });

  it('shows the tabs on a session error', async () => {
    composeOrResumeSession.mockImplementationOnce(async () => {
      throw new Error('compose failed');
    });
    renderTrainPage(['/train']);

    await waitFor(() => expect(screen.getByTestId('train-start-screen')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
  });

  it('shows the tabs on the Archive while its request fails', async () => {
    getArchive.mockImplementation(async () => {
      throw new Error('archive failed');
    });
    renderTrainPage(['/train/archive']);

    await waitFor(() => expect(screen.getByTestId('train-archive-error')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
  });
});

// ─── Hidden landing records nothing, and the first-visit intro on tabs ──────

describe('Train layout: D-06 a landing the player cannot see records nothing', () => {
  it('first Today visit left for Leaderboard before the session resolves: no view, no snapshot, both on return', async () => {
    const held = holdNextCompose();
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('train-today-panel')).not.toBeNull());

    clickTab('tab-train-leaderboard');
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    await act(async () => {
      held.resolve(SESSION_RESPONSE);
    });
    // The schedule card is the landing's one child that mounts while hidden.
    await waitFor(() => expect(screen.getByTestId('train-schedule-settings')).not.toBeNull());
    await act(async () => {});

    // Counts first, so each gate's mutation fails on the effect it guards.
    expect(feedbackAskMutate).toHaveBeenCalledTimes(0);
    expect(readStreakLastSeen(PROFILE_EMAIL)).toBeNull();
    expect(screen.queryByTestId('train-landing-host')).toBeNull();
    expect(screen.queryByTestId('train-streak-card')).toBeNull();

    clickTab('tab-train-today');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.getByTestId('train-landing-host')).not.toBeNull();
    expect(screen.getByTestId('train-streak-card')).not.toBeNull();
    expect(feedbackAskMutate).toHaveBeenCalledTimes(1);
    expect(feedbackAskMutate).toHaveBeenCalledWith('view');
    await waitFor(() => expect(readStreakLastSeen(PROFILE_EMAIL)).not.toBeNull());
  });

  it('Back out of the loop first-mounts the landing while hidden: nothing recorded until Today is visible', async () => {
    renderTrainPage(['/train/leaderboard']);
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    clickTab('tab-train-today');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-start'));
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
    feedbackAskMutate.mockClear();

    navigateTo(-1);

    await waitFor(() => expect(currentPath()).toBe('/train/leaderboard'));
    await act(async () => {});
    expect(screen.queryByTestId('chessboard')).toBeNull();
    expect(screen.queryByTestId('train-landing-host')).toBeNull();
    expect(screen.queryByTestId('train-streak-card')).toBeNull();
    expect(feedbackAskMutate).toHaveBeenCalledTimes(0);

    navigateTo('/train');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.getByTestId('train-landing-host')).not.toBeNull();
    expect(screen.getByTestId('train-streak-card')).not.toBeNull();
  });
});

describe('Train layout: D-16 tabs during the first-visit intro', () => {
  it("Tank's landing intro keeps the tabs and shows the same copy after a tab switch", async () => {
    getSettings.mockImplementation(async () => ({ ...SETTINGS_RESPONSE, intro_seen_at: null }));
    const tankCopy = landingHost({ sessionDate: SESSION_RESPONSE.session_date, introSeenAt: null }).copy;
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('train-tagline').textContent).toBe(tankCopy));
    const before = screen.getByTestId('train-tagline').textContent;

    clickTab('tab-train-leaderboard');
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    expect(screen.queryByTestId('train-landing-host')).toBeNull();

    clickTab('tab-train-today');
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    await waitFor(() => expect(screen.getByTestId('train-tagline')).not.toBeNull());
    expect(screen.getByTestId('train-tagline').textContent).toBe(before);
  });

  it('the intro stepper has no tabs; Back out stamps nothing and the next Start replays step one', async () => {
    getSettings.mockImplementation(async () => ({ ...SETTINGS_RESPONSE, intro_seen_at: null }));
    renderTrainPage(['/train/leaderboard']);
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    clickTab('tab-train-today');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-start'));

    await waitFor(() => expect(screen.getByTestId('btn-train-bot-step-next')).not.toBeNull());
    expect(screen.queryByTestId('train-tabs')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-train-bot-step-next'));
    await waitFor(() => expect(screen.getByTestId('btn-train-guess-critical')).not.toBeNull());

    navigateTo(-1);

    await waitFor(() => expect(currentPath()).toBe('/train/leaderboard'));
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    expect(screen.queryByTestId('chessboard')).toBeNull();
    expect(stampOnboarding).toHaveBeenCalledTimes(0);

    navigateTo('/train');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-start'));
    await waitFor(() => expect(screen.getByTestId('btn-train-bot-step-next')).not.toBeNull());
    expect(screen.queryByTestId('btn-train-guess-critical')).toBeNull();
    expect(stampOnboarding).toHaveBeenCalledTimes(0);
  });
});

// ─── Medal dialog host in the layout, leaderboard card only on its tab ──────

describe('Train layout: D-06 medal dialog host', () => {
  it('opens on a /train/leaderboard deep link and stays closed after a dismissal and a tab round trip', async () => {
    getUnclaimedMedals.mockImplementation(async () => ({ medals: TWO_MEDALS }));
    renderTrainPage(['/train/leaderboard']);

    await waitFor(() => expect(screen.getByTestId('train-medal-dialog')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-medal-dialog-close'));
    await waitFor(() => expect(screen.queryByTestId('train-medal-dialog')).toBeNull());

    clickTab('tab-train-today');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    clickTab('tab-train-leaderboard');
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    await act(async () => {});
    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
  });

  it('shows no dialog once the loop is entered, even when the medals arrive after Start', async () => {
    let resolveMedals: (value: { medals: UnclaimedMedal[] }) => void = () => undefined;
    const pending = new Promise<{ medals: UnclaimedMedal[] }>((res) => {
      resolveMedals = res;
    });
    getUnclaimedMedals.mockImplementationOnce(() => pending);
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-start'));
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());

    await act(async () => {
      resolveMedals({ medals: TWO_MEDALS });
    });
    await act(async () => {});

    expect(screen.queryByTestId('train-medal-dialog')).toBeNull();
  });
});

describe('Train layout: D-03 the leaderboard card lives only on its tab', () => {
  it('/train has no leaderboard card, /train/leaderboard has exactly one, also after a Today visit', async () => {
    renderTrainPage(['/train']);
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    expect(screen.queryByTestId('train-leaderboard-card')).toBeNull();

    clickTab('tab-train-leaderboard');
    await waitFor(() => expect(leaderboardPanelCard()).not.toBeNull());
    // getByTestId throws on a second match, so this also proves the hidden
    // Today panel holds none.
    expect(screen.getByTestId('train-leaderboard-card')).toBe(leaderboardPanelCard());
  });
});

describe('Train layout: the Archive tab', () => {
  it('a /train/archive deep link lists the card with no session POST and no Worker', async () => {
    renderTrainPage(['/train/archive']);

    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    expect(getArchive).toHaveBeenCalledWith({
      list: 'mastered',
      limit: ARCHIVE_PAGE_SIZE_UNDER_TEST,
      offset: 0,
    });
    await act(async () => {});
    expect(composeOrResumeSession).toHaveBeenCalledTimes(0);
    expect(WorkerCtor).toHaveBeenCalledTimes(0);
    // The card is a puzzle at ply 20: Analyze lands on the position before it.
    const analyze = screen.getByTestId('btn-train-puzzle-analyze');
    expect(analyze.getAttribute('href')).toBe('/analysis?game_id=100&ply=19');
  });

  it('Archive -> Today -> Start, then Back, leaves no solve screen and no extra POST', async () => {
    renderTrainPage(['/train/archive']);
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());

    clickTab('tab-train-today');
    await waitFor(() => expect(screen.getByTestId('btn-train-start')).not.toBeNull());
    fireEvent.click(screen.getByTestId('btn-train-start'));
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);

    navigateTo(-1);

    await waitFor(() => expect(currentPath()).toBe('/train/archive'));
    expect(screen.queryByTestId('chessboard')).toBeNull();
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    await act(async () => {});
    expect(composeOrResumeSession).toHaveBeenCalledTimes(1);
  });

  it('/train/archive/parked?page=2 asks for parked at offset 24, and a remount repeats it with no session', async () => {
    getArchive.mockImplementation(async () => ({ items: [ARCHIVE_ITEM], total: 25 }));
    const first = renderTrainPage(['/train/archive/parked?page=2']);

    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    expect(getArchive).toHaveBeenLastCalledWith({
      list: 'parked',
      limit: ARCHIVE_PAGE_SIZE_UNDER_TEST,
      offset: ARCHIVE_PAGE_SIZE_UNDER_TEST,
    });
    const callsBefore = getArchive.mock.calls.length;

    // Back from Analysis remounts the page at the same URL with a fresh client.
    first.unmount();
    renderTrainPage(['/train/archive/parked?page=2']);

    await waitFor(() => expect(getArchive.mock.calls.length).toBeGreaterThan(callsBefore));
    expect(getArchive).toHaveBeenLastCalledWith({
      list: 'parked',
      limit: ARCHIVE_PAGE_SIZE_UNDER_TEST,
      offset: ARCHIVE_PAGE_SIZE_UNDER_TEST,
    });
    await act(async () => {});
    expect(composeOrResumeSession).toHaveBeenCalledTimes(0);
    expect(WorkerCtor).toHaveBeenCalledTimes(0);
  });
});

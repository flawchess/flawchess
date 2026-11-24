// @vitest-environment jsdom
/**
 * Train.blunderCheckToday.test.tsx — the Phase 251 tracer: Start on the Today card's Blunder
 * Check row runs the drill under Today for any user (no beta gate, no tab), the drill takes
 * the page over, and finishing returns to the card.
 *
 * Mocks mirror Train.subnav.test.tsx (profile, ChessBoard, api client, FakeWorker).
 */
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, configure, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ComponentType } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import { PHASE_251_PROGRESS_FIELDS } from '@/components/train/__tests__/trainProgressFixtures';
import type { BlunderCheckSessionResponse, SessionResultResponse } from '@/types/blunderCheck';
import type {
  TrainProgressResponse,
  TrainSessionResponse,
  TrainSettingsResponse,
} from '@/types/train';
import type { UserProfile } from '@/types/users';

/** A registered user without the beta flag: the card must still offer the drill (D-18). */
const PROFILE = {
  is_guest: false,
  beta_enabled: false,
  email: 'runner@example.com',
  feedback_ask: { active: false },
  active_days: 1,
  impersonation: null,
  feature_route: null,
} as unknown as UserProfile;

// Mutable so the D-21 cases can put the discovery dot on the Blunder Check Start.
const profileState = vi.hoisted(() => ({ featureRoute: null as UserProfile['feature_route'] }));

vi.mock('@/hooks/useUserProfile', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/hooks/useUserProfile')>()),
  useUserProfile: () => ({
    data: { ...PROFILE, feature_route: profileState.featureRoute },
    isPending: false,
    isError: false,
  }),
  hasImportedGames: () => true,
}));

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({ tier1: true, tier2: true }),
}));

vi.mock('@/hooks/useFeedbackAsk', () => ({
  useFeedbackAsk: () => ({ mutate: vi.fn() }),
}));

// The audio unlock must run synchronously inside the Start tap (the lead-in plays from timers).
const unlockAudio = vi.hoisted(() => vi.fn());
vi.mock('@/lib/sounds', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/sounds')>()),
  unlockAudio,
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

vi.mock('@/lib/confetti', async () => {
  const actual = await vi.importActual<typeof import('@/lib/confetti')>('@/lib/confetti');
  return { ...actual, fireWinConfetti: vi.fn(), firePartialConfetti: vi.fn() };
});

configure({ asyncUtilTimeout: 10000 });

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

const PUZZLE_SESSION: TrainSessionResponse = {
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
  own_puzzle_count: 5,
};

const SETTINGS: TrainSettingsResponse = {
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
  blunder_check_per_session: 6,
  blunder_check_level: null,
};

const PROGRESS: TrainProgressResponse = {
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
  ...PHASE_251_PROGRESS_FIELDS,
};

const BLUNDER_SESSION: BlunderCheckSessionResponse = {
  session_id: 7,
  window_count: 6,
  current_position: 0,
  session_points: 0,
  windows: [],
};
/** Every window already ended: the host goes straight to finishing and the end screen. */
const FINISHED_SESSION: BlunderCheckSessionResponse = { ...BLUNDER_SESSION, current_position: null };
const RESULT: SessionResultResponse = {
  session_id: 7,
  session_points: 20,
  points_possible: 30,
  score_pct: 67,
  windows: [],
};

const getProgress = vi.fn(async () => PROGRESS);
const blunderCompose = vi.fn(async (): Promise<BlunderCheckSessionResponse> => BLUNDER_SESSION);
const blunderFinish = vi.fn(async (): Promise<SessionResultResponse> => RESULT);

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      composeOrResumeSession: async () => PUZZLE_SESSION,
      markSessionEntered: async () => undefined,
      solvePuzzle: vi.fn(),
      revealPuzzle: vi.fn(),
      getSettings: async () => SETTINGS,
      updateSettings: vi.fn(),
      getProgress: () => getProgress(),
      getLeaderboard: async () => ({
        week_start: '2032-01-05',
        week_end: '2032-01-12',
        seconds_remaining: 388800,
        points: { rows: [], viewer: null, last_week: null },
        accuracy: { rows: [], viewer: null, last_week: null },
      }),
      getArchive: async () => ({ items: [], total: 0 }),
      getUnclaimedMedals: async () => ({ medals: [] }),
      claimMedals: vi.fn(),
      stampOnboarding: async () => SETTINGS,
    },
    blunderCheckApi: {
      getOpenSession: async () => null,
      composeOrResumeSession: () => blunderCompose(),
      // The window request stays pending: the test only needs the drill shell on screen.
      startWindow: () => new Promise(() => {}),
      answer: vi.fn(),
      finishSession: () => blunderFinish(),
    },
    postReviewKeepalive: vi.fn(),
  };
});

class FakeWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;

  postMessage(msg: string | { progressPort: unknown }): void {
    if (typeof msg !== 'string') return;
    if (msg === 'uci') this.emit('uciok');
    else if (msg === 'isready') this.emit('readyok');
  }

  terminate(): void {}

  private emit(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

let TrainPage: ComponentType;

function renderTrainPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={['/train']}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <TrainPage />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

beforeAll(async () => {
  TrainPage = (await import('@/pages/Train')).default;
});

beforeEach(() => {
  vi.stubGlobal(
    'Worker',
    vi.fn(function (this: unknown) {
      return new FakeWorker();
    }),
  );
  vi.stubGlobal('scrollTo', vi.fn());
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation((query: string) => ({
      matches: query === '(min-width: 640px)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
  getProgress.mockClear();
  blunderCompose.mockClear();
  blunderCompose.mockImplementation(async () => BLUNDER_SESSION);
  blunderFinish.mockClear();
  unlockAudio.mockClear();
  localStorage.clear();
});

afterEach(() => {
  profileState.featureRoute = null;
  vi.restoreAllMocks();
  cleanup();
  vi.unstubAllGlobals();
  sessionStorage.clear();
  localStorage.clear();
});

describe('Train: blunder check from the Today card (D-11, D-18, D-20)', () => {
  it('Start on the card runs the drill immersive under Today for a non-beta user', async () => {
    renderTrainPage();

    const start = await screen.findByTestId('btn-train-blunder-check-start');
    expect(screen.getByTestId('tab-train-today')).not.toBeNull();
    fireEvent.click(start);

    // Audio unlocks inside the tap; the host composes once and the drill takes the page over.
    expect(unlockAudio).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getByTestId('blunder-check-session')).not.toBeNull());
    expect(blunderCompose).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('train-tabs')).toBeNull();
    expect(screen.queryByTestId('btn-train-blunder-check-start')).toBeNull();
  });

  it('finishing returns to the Today card and refreshes its progress', async () => {
    blunderCompose.mockImplementation(async () => FINISHED_SESSION);
    renderTrainPage();
    fireEvent.click(await screen.findByTestId('btn-train-blunder-check-start'));

    await waitFor(() => expect(screen.getByTestId('blunder-check-end-screen')).not.toBeNull());
    expect(blunderFinish).toHaveBeenCalledTimes(1);
    const progressReadsBeforeDone = getProgress.mock.calls.length;

    fireEvent.click(screen.getByTestId('btn-train-done'));

    await waitFor(() => expect(screen.getByTestId('btn-train-blunder-check-start')).not.toBeNull());
    expect(screen.queryByTestId('blunder-check-end-screen')).toBeNull();
    expect(screen.getByTestId('train-tabs')).not.toBeNull();
    await waitFor(() => expect(getProgress.mock.calls.length).toBeGreaterThan(progressReadsBeforeDone));
  });

  it('a 409 from compose shows the none-available message and Back returns to the card', async () => {
    blunderCompose.mockImplementation(async () => {
      throw Object.assign(new Error('conflict'), {
        isAxiosError: true,
        response: { status: 409 },
      });
    });
    renderTrainPage();
    fireEvent.click(await screen.findByTestId('btn-train-blunder-check-start'));

    await waitFor(() => expect(screen.getByTestId('blunder-check-none-available')).not.toBeNull());
    fireEvent.click(screen.getByTestId('blunder-check-btn-back'));

    await waitFor(() => expect(screen.getByTestId('btn-train-blunder-check-start')).not.toBeNull());
  });
});

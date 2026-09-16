// @vitest-environment jsdom
/**
 * Bots.test.tsx (Phase 171 Plan 06, V-11 + Plan 07, V-14/V-15) — pins the
 * three-way convergence on the setup screen (D-09/D-11/D-13): a fresh visit
 * with no snapshot, a Discard from the resume gate, and "New game" from both
 * result surfaces all land on `SetupScreen` — never on an auto-started game.
 * Plan 07 adds the D-21 store-on-finish flow: a finished game POSTs
 * immediately (V-14) and a subsequent `/bots` mount's drain does not re-POST
 * it (V-15, the double-POST regression).
 *
 * `useBotGame` is mocked WHOLESALE — the real hook boots a WorkerPool and a
 * Maia queue and has no place in a page test (RESEARCH.md precedent from
 * useBotGame.test.ts). The mock keeps its own `outcome`/`pgn`/`live` React
 * state so a test can drive them (`fakeGame.setOutcome`, `fakeGame.setPgn`,
 * `fakeGame.confirmLive`) and observe `BotsGame` re-render, without any real
 * engine machinery.
 *
 * `@/hooks/useStoreBotGame` is NOT mocked (Plan 06 had stubbed
 * `useDrainPendingStore` as a no-op — Plan 07 replaces that with the real
 * hook, exercising the actual finish-time-store + mount-drain interaction
 * against a mocked `botsApi.storeGame`, since the whole point of V-15 is
 * that the two store paths interact correctly through the SAME
 * localStorage queue).
 *
 * `@sentry/react` is mocked (its ESM module namespace is not configurable) —
 * mirrors SetupScreen.test.tsx; `botGameSnapshot.ts` calls
 * `Sentry.captureException` on a corrupt snapshot, which none of these tests
 * exercise, but the import must resolve.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
import { useState } from 'react';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';

// Flake fix: this file's raised per-test timeouts do NOT cover testing-library's
// async utilities, which have their own independent 1000ms `waitFor` ceiling.
// Under the full parallel `vitest run` on a loaded box a single waitFor can blow
// while the test still has seconds of budget left, surfacing as a bare waitFor
// stack with no assertion message. Give the async utils matching headroom.
const ASYNC_UTIL_TIMEOUT_MS = 10000;
configure({ asyncUtilTimeout: ASYNC_UTIL_TIMEOUT_MS });

// 171-08 (B-1): spy on navigation so the Analyze CTA's URL can be asserted.
// `renderBots()` mounts a bare `MemoryRouter` with no `<Routes>`, so there is
// no route to probe — the navigate() call itself is the only observable.
// `importOriginal` preserves `MemoryRouter` (imported from this module above).
const navigateSpy = vi.fn();
vi.mock('react-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router')>()),
  useNavigate: () => navigateSpy,
}));

import type { BotGameSettings } from '@/hooks/useBotGame';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import {
  BOT_GAME_SNAPSHOT_KEY_PREFIX,
  CURRENT_SNAPSHOT_VERSION,
  type BotGameSnapshot,
} from '@/lib/botGameSnapshot';
import { BOT_PENDING_STORE_KEY_PREFIX, enqueuePendingStore } from '@/lib/botPendingStore';
import { MAX_STORE_RETRIES } from '@/hooks/useStoreBotGame';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

// `botsApi.storeGame` is the D-21 finish-time store's and the D-13 mount
// drain's SHARED HTTP call site — mocking it here (module-level, `importActual`
// preserving everything else) is what lets both real hooks
// (`useStoreBotGame`/`useDrainPendingStore`, unmocked) run against the same
// fake network boundary in the tests below.
//
// Quick 260714-rj5: also mock `apiClient.post` — `useTier1EnqueueForGame`
// (unmocked, real hook) POSTs `/imports/eval/tier1/{id}` through it, and the
// "one-click tier-1 enqueue" describe block below needs to control/observe
// that call the same way the store tests control `botsApi.storeGame`.
// CR-01: `getPersonaWins` is also mocked here (not left as `...actual.botsApi`)
// so the "store on finish" tests below can assert the win-star cache actually
// refetches after a successful store, rather than falling through to the
// real (network-hitting) implementation.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    botsApi: {
      ...actual.botsApi,
      storeGame: vi.fn(),
      getPersonaWins: vi.fn(),
    },
    apiClient: {
      ...actual.apiClient,
      post: vi.fn(),
    },
  };
});

// ─── Controllable fake useBotGame ───────────────────────────────────────────

/** Stable per the fake hook's `gameUuid` — used by Plan 07's store-on-finish
 * tests to seed/inspect the matching pending-store queue entry. */
const FAKE_GAME_UUID = 'fake-game-uuid';

interface FakeGameHandle {
  setOutcome: (outcome: BotGameOutcome | null) => void;
  /** Plan 07: the real hook sets `outcome` and `pgn` together at finish
   * (`finalizeGame`); tests drive them independently so the D-21 effect's
   * `game.pgn === null` guard can be exercised deliberately. */
  setPgn: (pgn: string | null) => void;
  newGame: ReturnType<typeof vi.fn>;
  lastSettings: BotGameSettings | null;
  /** 171-08 (B-1): settable so a test can prove the Analyze CTA's URL
   * actually carries the played move list, not just the orientation param. */
  moveHistory: string[];
  /** 171-09 (gap 2): settable so a test can prove the ChessBoard consumer
   * actually reads game.lastMove, not just that the hook exposes it. */
  lastMove: { from: string; to: string } | null;
  /** Phase 183 Plan 05 (D-07): settable so a test can drive the bot's
   * outgoing draw-offer banner without any real grade-callback machinery. */
  setBotDrawOffer: (offer: boolean) => void;
  acceptBotDraw: ReturnType<typeof vi.fn>;
  offerDraw: ReturnType<typeof vi.fn>;
  declineBotDraw: ReturnType<typeof vi.fn>;
}

const fakeGame: FakeGameHandle = {
  setOutcome: () => {},
  setPgn: () => {},
  newGame: vi.fn(),
  lastSettings: null,
  moveHistory: [],
  lastMove: null,
  setBotDrawOffer: () => {},
  acceptBotDraw: vi.fn(),
  offerDraw: vi.fn(),
  declineBotDraw: vi.fn(),
};

vi.mock('@/hooks/useBotGame', () => ({
  useBotGame: (settings: BotGameSettings, resume?: unknown) => {
    const [outcome, setOutcome] = useState<BotGameOutcome | null>(null);
    const [pgn, setPgn] = useState<string | null>(null);
    // Mirrors the real hook's D-03 contract: fresh (resume undefined) games
    // are live from mount; a resumed snapshot starts NOT live until
    // confirmLive() fires — needed here only so `ResumeGate`'s
    // `resume !== null && !game.live` render gate stays honest.
    const [live, setLive] = useState<boolean>(resume === undefined);
    const [botDrawOffer, setBotDrawOffer] = useState(false);

    fakeGame.setOutcome = setOutcome;
    fakeGame.setPgn = setPgn;
    fakeGame.lastSettings = settings;
    fakeGame.setBotDrawOffer = setBotDrawOffer;

    return {
      position: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      lastMove: fakeGame.lastMove,
      moveHistory: fakeGame.moveHistory,
      liveGamePly: 0,
      viewedPly: 0,
      isBotThinking: false,
      whiteClockMs: settings.baseSeconds * 1000,
      blackClockMs: settings.baseSeconds * 1000,
      activeColor: 'white' as const,
      outcome,
      pgn,
      drawOfferPending: false,
      canOfferDraw: true,
      botDrawOffer,
      acceptBotDraw: fakeGame.acceptBotDraw,
      declineBotDraw: fakeGame.declineBotDraw,
      gameUuid: FAKE_GAME_UUID,
      live,
      confirmLive: () => setLive(true),
      attemptMove: vi.fn(() => false),
      viewPly: vi.fn(),
      returnToLive: vi.fn(),
      resign: vi.fn(),
      offerDraw: fakeGame.offerDraw,
      newGame: fakeGame.newGame,
      // Phase 223 (BOTVOICE-01/02): an untyped object literal, so a missing
      // field here would silently yield `undefined` at runtime rather than
      // a compile error (RESEARCH Pitfall 12) — added deliberately.
      botLine: null,
    };
  },
}));

// ─── Controllable fake useUserProfile ───────────────────────────────────────

interface FakeProfile {
  email: string | null;
  is_guest: boolean;
  current_strength: {
    rating: number;
    source: 'recent_games' | 'rating_anchor';
    rung: {
      platform: 'chess.com' | 'lichess';
      time_control_bucket: 'bullet' | 'blitz' | 'rapid' | 'classical';
      n_games: number;
      window_days: number;
      converted: boolean;
    } | null;
  } | null;
}

const profileState: { data: FakeProfile | undefined; isLoading: boolean; isError: boolean } = {
  data: {
    email: 'user@example.com',
    is_guest: false,
    current_strength: {
      rating: 1600,
      source: 'recent_games',
      rung: {
        platform: 'lichess',
        time_control_bucket: 'blitz',
        n_games: 40,
        window_days: 90,
        converted: false,
      },
    },
  },
  isLoading: false,
  isError: false,
};

vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({
    data: profileState.data,
    isLoading: profileState.isLoading,
    isError: profileState.isError,
  }),
}));

// Quick 260723-tqn: the celebration-hold delay is covered by its own
// dedicated unit test (useWinCelebrationHold.test.ts, fake timers). Mocked
// here to `false` (no hold) so this file's existing result-dialog assertions
// (which use real timers) aren't coupled to the ~1.3s WIN_CELEBRATION_HOLD_MS
// window.
vi.mock('@/hooks/useWinCelebrationHold', () => ({
  useWinCelebrationHold: () => false,
}));

// 171-09 (gap 2): a minimal ChessBoard stub exposing the lastMove prop as a
// data attribute, so the last-move-highlight tests can assert on the wiring
// boundary without pulling in real react-chessboard rendering. Safe here:
// this file queries no board internals today (confirmed: zero `square-` /
// `data-testid="chessboard"` hits before this mock was added).
vi.mock('@/components/board/ChessBoard', () => ({
  ChessBoard: ({ lastMove }: { lastMove: { from: string; to: string } | null }) => (
    <div
      data-testid="chessboard"
      data-last-move={lastMove ? `${lastMove.from}${lastMove.to}` : ''}
    />
  ),
}));

// jsdom shims required by react-chessboard and responsive components
// (mirrors Analysis.test.tsx / SetupScreen.test.tsx precedent).
//
// Phase 223 (BOTVOICE-05): extracted to a named installer, not just an
// inline `Object.defineProperty` call, so the desktop-mode describe block
// below can flip `matches` to `true` for its own tests and restore this
// file's mobile-reporting default afterward — every other suite in this file
// relies on `useIsDesktop()` reporting `false`.
function installMatchMediaStub(matches: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}
installMatchMediaStub(false);

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

import { botsApi, apiClient } from '@/api/client';
import BotsPage from '../Bots';

// ─── Test helpers ────────────────────────────────────────────────────────────

/** Matches `useStoreBotGame.test.ts`'s helper shape — `shouldRetryStore`
 * reads `error.isAxiosError` + `error.response.status`. */
function axiosError(status: number): Error {
  return Object.assign(new Error(`http ${status}`), {
    isAxiosError: true,
    response: { status, data: {} },
  });
}

/** Collapses TanStack's default exponential mutation backoff (1s, 2s, 4s…) to
 * a flat 10ms. Load-bearing for the CR-01 test below: with the real backoff a
 * 4th attempt would only land ~4s after the 3rd, so a "count is frozen" probe
 * a few hundred ms after the 3rd call would pass even for an UNBOUNDED retry
 * loop — the exact bug it exists to catch. At 10ms the same probe spans ~30
 * would-be retry windows, so an unbounded loop fails it loudly. */
const MUTATION_RETRY_DELAY_MS = 10;

function renderBots() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retryDelay: MUTATION_RETRY_DELAY_MS },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/bots']}>
        <TooltipProvider>
          <BotsPage />
        </TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function buildSnapshot(overrides: Partial<BotGameSnapshot> = {}): BotGameSnapshot {
  return {
    version: CURRENT_SNAPSHOT_VERSION,
    gameUuid: 'existing-game-uuid',
    settings: {
      botElo: 1500,
      blend: 0.5,
      baseSeconds: 300,
      incrementSeconds: 3,
      userColor: 'white',
    },
    pgn: '1. e4 e5',
    whiteClockMs: 250_000,
    blackClockMs: 260_000,
    movesSinceLastDecline: 0,
    hasLeftBook: false,
    hasFiredLowTime: false,
    savedAt: Date.now(),
    ...overrides,
  };
}

function snapshotKeyFor(ownerKey: string | null): string {
  return `${BOT_GAME_SNAPSHOT_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}

function pendingStoreKeyFor(ownerKey: string | null): string {
  return `${BOT_PENDING_STORE_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}

/** Phase 183: the default setup view is now `PersonaGrid`, not `SetupScreen`
 * directly (PERS-01/PERS-04) — this helper routes through the Custom entry
 * first, so every pre-existing SetupScreen-driven test below keeps working
 * unchanged from that point on. */
async function startFromSetup(colorTestId = 'setup-color-white', tcTestId = 'setup-tc-blitz-5-3') {
  await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
  fireEvent.click(screen.getByTestId('bots-persona-custom'));
  await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
  fireEvent.click(screen.getByTestId(colorTestId));
  fireEvent.click(screen.getByTestId(tcTestId));
  fireEvent.click(screen.getByTestId('btn-start-game'));
  await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
}

beforeEach(() => {
  localStorage.clear();
  fakeGame.newGame.mockClear();
  fakeGame.moveHistory = [];
  fakeGame.lastMove = null;
  fakeGame.acceptBotDraw.mockClear();
  fakeGame.offerDraw.mockClear();
  fakeGame.declineBotDraw.mockClear();
  navigateSpy.mockClear();
  vi.mocked(botsApi.storeGame).mockReset();
  // CR-01: a benign default so `useBotPersonaWins`'s mount-time fetch resolves
  // rather than hanging — tests that assert on refetch counts override this.
  vi.mocked(botsApi.getPersonaWins).mockReset();
  vi.mocked(botsApi.getPersonaWins).mockResolvedValue({});
  // A safe default: the D-13 mount-drain effect fires on EVERY BotsPage
  // mount now that `useDrainPendingStore` is unmocked (Plan 07). Tests that
  // don't care about the store (e.g. the D-11 setup/discard convergence
  // suite above) must not have a stray seeded pending-store entry silently
  // consumed by an unconfigured mock resolving `undefined` as if it were a
  // 2xx. Tests that DO care about the store override this explicitly.
  vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(500));
  // Quick 260714-rj5: apiClient.post backs useTier1EnqueueForGame's real
  // (unmocked) mutation. A benign default resolve — tests that exercise the
  // enqueue path override this explicitly.
  vi.mocked(apiClient.post).mockReset();
  vi.mocked(apiClient.post).mockResolvedValue({
    data: { status: 'enqueued', game_id: 0 },
  });
  profileState.data = {
    email: 'user@example.com',
    is_guest: false,
    current_strength: {
      rating: 1600,
      source: 'recent_games',
      rung: {
        platform: 'lichess',
        time_control_bucket: 'blitz',
        n_games: 40,
        window_days: 90,
        converted: false,
      },
    },
  };
  profileState.isLoading = false;
  profileState.isError = false;
});

afterEach(() => {
  cleanup();
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe('Bots — profile fetch failure (WR-08)', () => {
  it('renders the error branch and never boots into the shared anon bucket', async () => {
    // A settled-but-failed profile query: isLoading false, data undefined —
    // which used to look exactly like "no profile", so the page booted with
    // ownerKey = null and read/wrote the shared `…:anon` keys.
    profileState.data = undefined;
    profileState.isLoading = false;
    profileState.isError = true;

    // A game parked in the ANON bucket (e.g. left by a previous browser user).
    // A logged-in user whose profile fetch failed must never see it.
    localStorage.setItem(snapshotKeyFor(null), JSON.stringify(buildSnapshot()));

    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-page-error')).toBeTruthy());
    expect(screen.getByTestId('bots-page-error').textContent).toContain('Something went wrong');

    // Not the game, not the setup view (grid or Custom), and NOT stuck on
    // the loading branch.
    expect(screen.queryByTestId('bots-page')).toBeNull();
    expect(screen.queryByTestId('bots-persona-grid')).toBeNull();
    expect(screen.queryByTestId('setup-screen')).toBeNull();
    expect(screen.queryByTestId('bots-page-loading')).toBeNull();

    // The anon snapshot was never consumed, and the mount-drain never fired
    // against the anon queue.
    expect(screen.queryByTestId('resume-gate')).toBeNull();
    expect(botsApi.storeGame).not.toHaveBeenCalled();
  });
});

describe('Bots — setup/resume/new-game convergence (V-11)', () => {
  it('renders the persona grid (not SetupScreen) when there is no snapshot (Phase 183, PERS-01)', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    expect(screen.queryByTestId('setup-screen')).toBeNull();
    expect(screen.queryByTestId('bots-page')).toBeNull();
  });

  it('selecting the Custom entry renders the unchanged SetupScreen (Phase 183, PERS-04)', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-custom'));

    await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
    expect(screen.queryByTestId('bots-persona-grid')).toBeNull();
  });

  it('selecting a persona opens the detail surface, whose Play routes through the single handleStart entry (Phase 183, PERS-02)', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-card-attacker-800'));

    await waitFor(() => expect(screen.getByTestId('persona-detail-surface')).toBeTruthy());
    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));

    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
    expect(fakeGame.lastSettings).not.toBeNull();
    const settings = fakeGame.lastSettings as BotGameSettings;
    expect(settings.personaId).toBe('attacker-800');
    expect(settings.userColor).toBe('white');
  });

  it('mounts the game with the settings chosen at setup', async () => {
    renderBots();

    await startFromSetup('setup-color-white', 'setup-tc-blitz-5-3');

    expect(fakeGame.lastSettings).not.toBeNull();
    const settings = fakeGame.lastSettings as BotGameSettings;
    // A concrete color, never 'random' (D-12) — the setup screen resolves
    // it before onStart fires.
    expect(settings.userColor === 'white' || settings.userColor === 'black').toBe(true);
    expect(settings.userColor).toBe('white');
    // Seconds-based clocks, not a display-label string (the 5+3 blitz preset).
    expect(settings.baseSeconds).toBe(300);
    expect(settings.incrementSeconds).toBe(3);
  });

  it('snapshot beats setup — neither the persona grid nor SetupScreen render when a snapshot is present', async () => {
    localStorage.setItem(snapshotKeyFor('user@example.com'), JSON.stringify(buildSnapshot()));

    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
    expect(screen.getByTestId('resume-gate')).toBeTruthy();
    expect(screen.queryByTestId('bots-persona-grid')).toBeNull();
    expect(screen.queryByTestId('setup-screen')).toBeNull();
  });

  it('discard falls through to setup, clearing only the snapshot key (170 D-05)', async () => {
    const ownerKey = 'user@example.com';
    localStorage.setItem(snapshotKeyFor(ownerKey), JSON.stringify(buildSnapshot()));
    const pendingStoreValue = JSON.stringify([
      { gameUuid: 'finished-1', pgn: '1. e4 e5', settings: buildSnapshot().settings, enqueuedAt: Date.now() },
    ]);
    localStorage.setItem(pendingStoreKeyFor(ownerKey), pendingStoreValue);

    renderBots();

    await waitFor(() => expect(screen.getByTestId('resume-gate')).toBeTruthy());
    fireEvent.click(screen.getByTestId('btn-discard'));
    fireEvent.click(screen.getByTestId('btn-discard-confirm'));

    // Falls through to the setup view's default (Phase 183: the persona
    // grid, not SetupScreen directly).
    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    expect(screen.queryByTestId('bots-page')).toBeNull();
    expect(localStorage.getItem(snapshotKeyFor(ownerKey))).toBeNull();
    // 170 D-05: discard never touches the pending-store queue.
    expect(localStorage.getItem(pendingStoreKeyFor(ownerKey))).toBe(pendingStoreValue);
  });

  it('new game returns to setup, not an instant restart (D-11)', async () => {
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });

    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());
    fireEvent.click(screen.getByTestId('btn-new-game'));

    // Falls through to the setup view's default (Phase 183: the persona
    // grid, not SetupScreen directly).
    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    expect(screen.queryByTestId('bots-page')).toBeNull();
    // The load-bearing negative assertion (D-11): the old wiring called
    // game.newGame() and restarted in place with the same settings — a test
    // that only checks for the setup view would also pass against that wiring.
    expect(fakeGame.newGame).not.toHaveBeenCalled();
  });

  it('dismissing the result dialog returns to the roster, without calling newGame', async () => {
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });
    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());

    // Dismissing without choosing an action (the Dialog primitive's own close
    // button) routes back to the roster — it no longer leaves a result strip
    // parked over the finished board.
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    expect(screen.queryByTestId('bots-page')).toBeNull();
    expect(fakeGame.newGame).not.toHaveBeenCalled();
  });

  it('guest reaches setup — no email, is_guest, Start still works', async () => {
    profileState.data = {
      email: null,
      is_guest: true,
      current_strength: null,
    };

    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-custom'));
    await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
    fireEvent.click(screen.getByTestId('setup-color-black'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
    expect(fakeGame.lastSettings?.userColor).toBe('black');
  });
});

describe('Bots — mobile player rows (Phase 223 UAT: same rows as the analysis board)', () => {
  it('renders the bot row (name + calibrated label) and the user row on mobile for a persona game', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-card-attacker-800'));

    await waitFor(() => expect(screen.getByTestId('persona-detail-surface')).toBeTruthy());
    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));

    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());

    // This suite renders the mobile layout by default (the matchMedia stub
    // above reports a non-matching query); the retired nameless clock strip
    // is gone from the tree.
    expect(screen.queryByTestId('bot-clock-strip')).toBeNull();

    const botRow = screen.getByTestId('clock-bot');
    expect(botRow.textContent).toContain('Ziggy the Wasp');
    expect(botRow.textContent).toContain('~800');
    const userRow = screen.getByTestId('clock-user');
    expect(userRow.textContent).toContain('You');
    expect(userRow.textContent).toContain('~1600');
  });

  it('renders both rows on mobile for a Custom game with the generic bot name and no bot rating label', async () => {
    renderBots();
    await startFromSetup();

    const botRow = screen.getByTestId('clock-bot');
    expect(botRow.textContent).toContain('FlawChess Bot');
    expect(botRow.textContent).not.toContain('~');
    expect(screen.getByTestId('clock-user')).toBeTruthy();
  });

  it('shows the clock icon only on the row of the side to move', async () => {
    renderBots();
    await startFromSetup();

    // fakeGame's activeColor is 'white' and the user plays white here.
    expect(screen.getByTestId('clock-user-clock-icon').getAttribute('class')).not.toContain('invisible');
    expect(screen.getByTestId('clock-bot-clock-icon').getAttribute('class')).toContain('invisible');
  });
});

describe('Bots — in-game bubble wiring (Phase 223, BOTVOICE-01/02)', () => {
  it('renders the bubble with its copy node for a persona game', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-card-attacker-800'));
    await waitFor(() => expect(screen.getByTestId('persona-detail-surface')).toBeTruthy());
    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));

    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
    expect(screen.getByTestId('bot-game-bubble')).toBeTruthy();
    expect(screen.getByTestId('bot-game-bubble-copy')).toBeTruthy();
  });
});

describe('Bots — bot draw-offer actions render inside the bubble (Phase 223, BOTVOICE-05, D-12)', () => {
  it('renders Accept/Decline inside the bubble for a persona game and both call through to the hook', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-card-attacker-800'));
    await waitFor(() => expect(screen.getByTestId('persona-detail-surface')).toBeTruthy());
    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));
    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());

    // The retired banner is gone entirely — the offer now renders inside
    // `BotGameBubble`'s actions slot instead.
    expect(screen.queryByTestId('btn-accept-bot-draw')).toBeNull();
    expect(screen.queryByTestId('btn-decline-bot-draw')).toBeNull();

    act(() => {
      fakeGame.setBotDrawOffer(true);
    });

    const bubble = screen.getByTestId('bot-game-bubble');
    const acceptBtn = within(bubble).getByTestId('btn-accept-bot-draw');
    const declineBtn = within(bubble).getByTestId('btn-decline-bot-draw');

    fireEvent.click(acceptBtn);
    expect(fakeGame.acceptBotDraw).toHaveBeenCalledTimes(1);

    fireEvent.click(declineBtn);
    expect(fakeGame.declineBotDraw).toHaveBeenCalledTimes(1);
  });

  it('renders the generic fallback offer copy plus both preserved testids for a Custom game (no persona)', async () => {
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setBotDrawOffer(true);
    });

    const bubble = screen.getByTestId('bot-game-bubble');
    expect(bubble.textContent).toContain('The bot offers a draw');

    const acceptBtn = within(bubble).getByTestId('btn-accept-bot-draw');
    const declineBtn = within(bubble).getByTestId('btn-decline-bot-draw');

    fireEvent.click(acceptBtn);
    expect(fakeGame.acceptBotDraw).toHaveBeenCalledTimes(1);

    fireEvent.click(declineBtn);
    expect(fakeGame.declineBotDraw).toHaveBeenCalledTimes(1);
  });
});

describe('Bots — mobile chrome removed, back arrow wired (Phase 223, BOTVOICE-05, D-10/D-12/SC7)', () => {
  it('renders no in-page board-control row, resign row, offer-draw button or mute button on mobile', async () => {
    renderBots();
    await startFromSetup();

    // `BoardControls` (desktop-only "xl" row, incl. its view-Reset button)
    // and `GameControls` (desktop-only resign row) are not rendered inside
    // this suite's mobile layout at all — their mobile equivalents live in
    // `BotGameMobileBar`, mounted from `App.tsx` above the router, which
    // this page-level render tree never reaches.
    expect(screen.queryByTestId('board-btn-reset')).toBeNull();
    expect(screen.queryByTestId('board-btn-resign')).toBeNull();
    expect(screen.queryByTestId('resign-confirm-dialog')).toBeNull();
    // The user-side Draw button (back since quick 260916) lives in the same
    // desktop-only `GameControls` row / mobile `BotGameMobileBar` as Resign,
    // so it is absent from this page-level mobile tree for the same reason.
    // The in-game mute toggle is gone entirely (D-10/D-12/SC7).
    expect(screen.queryByTestId('board-btn-offer-draw')).toBeNull();
    expect(screen.queryByTestId('board-btn-mute')).toBeNull();
  });

  it('the mobile back arrow calls the new handler and returns to the roster without an instant restart', async () => {
    renderBots();
    await startFromSetup();

    fireEvent.click(screen.getByTestId('bots-back'));

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    expect(screen.queryByTestId('bots-page')).toBeNull();
    // Mechanically the same non-instant-restart contract as "New game"
    // (D-11): the back arrow never calls game.newGame() to restart in place.
    expect(fakeGame.newGame).not.toHaveBeenCalled();
  });
});

describe('Bots — desktop layout (Phase 223, BOTVOICE-05, D-11/D-12)', () => {
  beforeEach(() => {
    installMatchMediaStub(true);
  });

  afterEach(() => {
    // Restore this file's mobile-reporting default for every other suite.
    installMatchMediaStub(false);
  });

  it('renders two player rows: the bot with its name and calibrated label, the player with its name and rounded estimate', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-card-attacker-800'));
    await waitFor(() => expect(screen.getByTestId('persona-detail-surface')).toBeTruthy());
    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));
    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());

    // D-11: the honest tilde-prefixed calibrated label, never a
    // parenthesised integer — attacker-800's PERSONA_CALIBRATION label.
    const botRow = screen.getByTestId('clock-bot');
    expect(botRow.textContent).toContain('Ziggy the Wasp');
    expect(botRow.textContent).toContain('~800');
    expect(botRow.textContent).not.toContain('(800)');

    // The player's own rounded, tilde-prefixed estimate — same expression
    // the roster row renders (profileState's current_strength.rating is 1600).
    const userRow = screen.getByTestId('clock-user');
    expect(userRow.textContent).toContain('You');
    expect(userRow.textContent).toContain('~1600');
  });

  it('renders the user row with a name and no rating text for a guest (no currentStrength)', async () => {
    profileState.data = { email: null, is_guest: true, current_strength: null };
    renderBots();
    await startFromSetup();

    const userRow = screen.getByTestId('clock-user');
    expect(userRow.textContent).toContain('You');
    expect(userRow.textContent).not.toContain('~');
    expect(userRow.textContent).not.toContain('(');
  });

  it('renders the bubble at the top of the side column, above the move list', async () => {
    renderBots();

    // A persona game — a Custom game's bubble renders nothing at all while
    // no draw offer is live (BotGameBubble.tsx: `persona === null && actions
    // === undefined` returns null), so this needs a persona to have
    // anything to assert the position of.
    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-card-attacker-800'));
    await waitFor(() => expect(screen.getByTestId('persona-detail-surface')).toBeTruthy());
    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));
    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());

    const bubble = screen.getByTestId('bot-game-bubble');
    expect(bubble.parentElement?.firstElementChild).toBe(bubble);
  });

  it('renders the draw offer Accept/Decline buttons inside the bubble and both call through', async () => {
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setBotDrawOffer(true);
    });

    const bubble = screen.getByTestId('bot-game-bubble');
    const acceptBtn = within(bubble).getByTestId('btn-accept-bot-draw');
    const declineBtn = within(bubble).getByTestId('btn-decline-bot-draw');

    fireEvent.click(acceptBtn);
    expect(fakeGame.acceptBotDraw).toHaveBeenCalledTimes(1);

    fireEvent.click(declineBtn);
    expect(fakeGame.declineBotDraw).toHaveBeenCalledTimes(1);
  });

  it('renders no in-page mute control on this breakpoint either', async () => {
    renderBots();
    await startFromSetup();

    expect(screen.queryByTestId('board-btn-mute')).toBeNull();
  });

  // Quick 260916: the user's own draw offer is back, behind a confirm dialog.
  it('the Draw button opens a confirm dialog whose confirm calls offerDraw, and is disabled while the bot\'s own offer is live', async () => {
    renderBots();
    await startFromSetup();

    const drawBtn = screen.getByTestId('board-btn-offer-draw');
    expect(drawBtn).toHaveProperty('disabled', false);

    fireEvent.click(drawBtn);
    expect(screen.getByTestId('draw-offer-confirm-dialog')).toBeTruthy();
    expect(fakeGame.offerDraw).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('board-btn-offer-draw-confirm'));
    expect(fakeGame.offerDraw).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('draw-offer-confirm-dialog')).toBeNull();

    act(() => {
      fakeGame.setBotDrawOffer(true);
    });
    expect(screen.getByTestId('board-btn-offer-draw')).toHaveProperty('disabled', true);
  });
});

describe('Bots — Rematch/New opponent (Phase 183, D-06/D-08)', () => {
  async function startPersonaGame(): Promise<void> {
    renderBots();
    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    fireEvent.click(screen.getByTestId('bots-persona-card-attacker-800'));
    await waitFor(() => expect(screen.getByTestId('persona-detail-surface')).toBeTruthy());
    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));
    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
  }

  it('names the persona in the result dialog title and Rematch starts a fresh game with the SAME pinned settings', async () => {
    await startPersonaGame();

    act(() => {
      fakeGame.setOutcome({ reason: 'checkmate', winner: 'black' });
    });
    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());
    expect(screen.getByTestId('result-dialog').textContent).toContain('Ziggy the Wasp wins — checkmate');

    const rematchBtn = screen.getByTestId('btn-rematch');
    expect(rematchBtn.textContent).toBe('Rematch Ziggy the Wasp');

    const firstSettings = fakeGame.lastSettings;
    fireEvent.click(rematchBtn);

    // Rematch remounts BotsGame (a fresh game, outcome reset to null) with the
    // EXACT SAME pinned settings object — via the single existing handleStart
    // path (never a second start path, never game.newGame()).
    await waitFor(() => expect(screen.queryByTestId('result-dialog')).toBeNull());
    expect(fakeGame.lastSettings).toBe(firstSettings);
    expect(fakeGame.lastSettings?.personaId).toBe('attacker-800');
    expect(fakeGame.newGame).not.toHaveBeenCalled();
  });

  it('dismissing a persona game\'s result dialog routes to the roster (no result strip)', async () => {
    await startPersonaGame();

    act(() => {
      fakeGame.setOutcome({ reason: 'checkmate', winner: 'black' });
    });
    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    await waitFor(() => expect(screen.getByTestId('bots-persona-grid')).toBeTruthy());
    // The load-bearing negative: the dismissed-dialog surface is gone entirely,
    // not merely hidden behind the roster.
    expect(screen.queryByTestId('result-strip')).toBeNull();
    expect(fakeGame.newGame).not.toHaveBeenCalled();
  });

  it('a Custom game shows generic result copy and no Rematch button (New opponent only)', async () => {
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });
    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());

    expect(screen.queryByTestId('btn-rematch')).toBeNull();
    expect(screen.getByTestId('btn-new-game').textContent).toBe('New opponent');
  });
});

describe('store on finish (D-21)', () => {
  const OWNER_KEY = 'user@example.com';
  const SAMPLE_PGN = '1. e4 e5 2. Nf3 *';

  /** Settings shape a seeded pending-store queue entry needs to satisfy
   * `isValidPendingEntry` (botPendingStore.ts) — mirrors `buildSnapshot`'s
   * settings shape used elsewhere in this file. */
  const ENTRY_SETTINGS: BotGameSettings = {
    botElo: 1500,
    blend: 0.5,
    baseSeconds: 300,
    incrementSeconds: 3,
    userColor: 'white',
  };

  /** Mirrors what the REAL `finalizeGame` (useBotGame.ts) does atomically at
   * finish: enqueue to localStorage AND set `outcome`/`pgn` together. Our
   * fake `useBotGame` mock never calls `enqueuePendingStore` itself (it has
   * no finalize logic), so tests that need a queue entry present AT finish
   * time (not before) call this instead of pre-seeding localStorage — pre-
   * seeding before the game even starts would let the FIRST mount's own
   * D-13 drain consume it before the game finishes, corrupting the call
   * count this describe block exists to pin. */
  function finishAndEnqueue(gameUuid: string): void {
    act(() => {
      enqueuePendingStore(OWNER_KEY, {
        gameUuid,
        pgn: SAMPLE_PGN,
        settings: ENTRY_SETTINGS,
        enqueuedAt: Date.now(),
      });
      fakeGame.setPgn(SAMPLE_PGN);
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });
  }

  function pendingEntryCount(): number {
    const raw = localStorage.getItem(pendingStoreKeyFor(OWNER_KEY));
    if (raw === null) return 0;
    return (JSON.parse(raw) as unknown[]).length;
  }

  // FLAWCHESS-64: the finish-time store only fires for a game BOTH colors moved
  // in, so every test here needs a move history matching SAMPLE_PGN. The outer
  // `beforeEach` resets this to [] (which is the unstorable case, pinned by its
  // own test at the end of this block).
  beforeEach(() => {
    fakeGame.moveHistory = ['e4', 'e5', 'Nf3'];
  });

  it('POSTs exactly once when outcome transitions null -> finished, with a matching game_uuid (V-14)', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });
    renderBots();
    await startFromSetup();

    expect(botsApi.storeGame).not.toHaveBeenCalled();

    act(() => {
      fakeGame.setPgn(SAMPLE_PGN);
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });

    await waitFor(() => expect(botsApi.storeGame).toHaveBeenCalledTimes(1));
    expect(vi.mocked(botsApi.storeGame).mock.calls[0]?.[0]).toMatchObject({
      game_uuid: FAKE_GAME_UUID,
      pgn: SAMPLE_PGN,
    });

    // A re-render driven by a NEW `outcome` object reference (same values) —
    // the fire-once latch is keyed on `gameUuid` (a ref), not on the effect
    // simply not re-running.
    act(() => {
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });
    await waitFor(() => expect(botsApi.storeGame).toHaveBeenCalledTimes(1));
  });

  // FLAWCHESS-64: the server's both-colors [%clk] gate rejects any game that
  // ended before both sides moved. Those games used to be POSTed anyway, 422 on
  // every attempt, and reach the user as nothing but a missing Library row.
  it.each([
    ['no moves at all (flagged before moving)', [] as string[]],
    ['one ply (resigned before the bot replied)', ['e4']],
  ])('does not POST a game the server can never accept: %s', async (_label, history) => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });
    renderBots();
    await startFromSetup();

    fakeGame.moveHistory = history;
    act(() => {
      fakeGame.setPgn(SAMPLE_PGN);
      fakeGame.setOutcome({ reason: 'resignation', winner: 'black' });
    });

    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(botsApi.storeGame).not.toHaveBeenCalled();
  });

  it('leaves Analyze usable for an unstorable game instead of spinning forever', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });
    renderBots();
    await startFromSetup();

    fakeGame.moveHistory = ['e4'];
    act(() => {
      fakeGame.setPgn(SAMPLE_PGN);
      fakeGame.setOutcome({ reason: 'resignation', winner: 'black' });
    });

    // `analyzeBusy` is derived from the store mutation settling; with no
    // mutation fired it would stay pending forever without the isStorable
    // short-circuit, leaving the CTA permanently disabled.
    const analyze = await screen.findByTestId('btn-analyze-game');
    await waitFor(() => expect(analyze.hasAttribute('disabled')).toBe(false));
    fireEvent.click(analyze);
    await waitFor(() => expect(navigateSpy).toHaveBeenCalled());
  });

  it('does not POST while pgn is still null (a finished game always has a PGN, but the guard stays honest)', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });

    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());
    expect(botsApi.storeGame).not.toHaveBeenCalled();
  });

  it('finish -> store succeeds -> remount does NOT re-POST (V-15, the double-POST regression)', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });

    const { unmount } = renderBots();
    await startFromSetup();

    finishAndEnqueue(FAKE_GAME_UUID);

    await waitFor(() => expect(botsApi.storeGame).toHaveBeenCalledTimes(1));
    // The dedupe fix: the mutation's onSuccess removes the queue entry.
    await waitFor(() => expect(pendingEntryCount()).toBe(0));

    unmount();
    renderBots();

    // The remount's D-13 mount-drain effect runs `useDrainPendingStore`'s
    // `drain()` against an EMPTY queue — total call count stays at 1. Give
    // the drain effect a moment to run before asserting the negative.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(botsApi.storeGame).toHaveBeenCalledTimes(1);
  });

  it('a FAILED finish-time store leaves the pending entry intact for the next mount to retry', async () => {
    vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(500));

    const { unmount } = renderBots();
    await startFromSetup();

    finishAndEnqueue(FAKE_GAME_UUID);

    // `shouldRetryStore` bounds a 500 at MAX_STORE_RETRIES (2) in-flight
    // retries -> 3 total attempts before the mutation settles as failed.
    await waitFor(() => expect(botsApi.storeGame).toHaveBeenCalledTimes(3), { timeout: 8000 });
    const countAfterFinish = vi.mocked(botsApi.storeGame).mock.calls.length;

    // onSuccess (the ONLY removal site) never fired — the entry SURVIVES.
    expect(pendingEntryCount()).toBe(1);

    unmount();
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });
    renderBots();

    // The next mount's drain DOES attempt the surviving entry — proving the
    // dedupe (onSuccess-only removal) did not cannibalize the durability
    // fallback.
    await waitFor(() => expect(botsApi.storeGame.mock.calls.length).toBeGreaterThan(countAfterFinish));
    await waitFor(() => expect(pendingEntryCount()).toBe(0));
  }, 15000);

  // CR-01 regression (the reason `shouldRetryStore` no longer returns `true`
  // unconditionally for a 401): `Bots.tsx` is the predicate's first PRODUCTION
  // call site, so an unbounded 401 retry here meant `POST /bots/games` re-issued
  // forever while the result screen stayed mounted — never settling, so
  // `MutationCache.onError` never reached Sentry and `store.isSuccess` never
  // flipped. The 401's durable retry is the next mount's drain (D-13), which
  // this test also pins by asserting the pending entry SURVIVES.
  it('a 401 finish-time store is BOUNDED (no unbounded retry loop) and leaves the pending entry for the next mount', async () => {
    vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(401));

    renderBots();
    await startFromSetup();

    finishAndEnqueue(FAKE_GAME_UUID);

    // Bounded at MAX_STORE_RETRIES in-flight retries -> MAX_STORE_RETRIES + 1
    // total attempts, then the mutation SETTLES as errored.
    await waitFor(
      () => expect(botsApi.storeGame).toHaveBeenCalledTimes(MAX_STORE_RETRIES + 1),
      { timeout: 8000 },
    );

    // The loop is over: wait ~30 retry windows (MUTATION_RETRY_DELAY_MS) and
    // assert the count is FROZEN. An unbounded 401 loop would have fired many
    // more calls by now.
    await new Promise((resolve) => setTimeout(resolve, MUTATION_RETRY_DELAY_MS * 30));
    expect(botsApi.storeGame).toHaveBeenCalledTimes(MAX_STORE_RETRIES + 1);

    // onSuccess never fired — the entry survives for the D-13 next-visit drain.
    expect(pendingEntryCount()).toBe(1);
  }, 15000);

  // CR-01: without the finish-time store's onSuccess invalidation, this
  // second call never happens — `useBotPersonaWins`'s 5-minute staleTime
  // query instance (mounted once at BotsPage level, never unmounted across
  // this cycle) would keep serving its pre-game win counts.
  it('invalidates the persona-wins cache after a successful finish-time store, forcing a refetch (CR-01)', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({ game_id: 1, created: true });
    renderBots();
    await startFromSetup();

    await waitFor(() => expect(botsApi.getPersonaWins).toHaveBeenCalledTimes(1));

    finishAndEnqueue(FAKE_GAME_UUID);

    await waitFor(() => expect(botsApi.storeGame).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(botsApi.getPersonaWins).toHaveBeenCalledTimes(2));
  });
});

describe('Analyze CTA carries the played colour (171 UAT gap 1)', () => {
  /**
   * B-1: the JOINING LINE ITSELF. `analysisUrl.test.ts` tests a pure function
   * that never renders `Bots`; `Analysis.test.tsx` feeds `/analysis?…` URLs
   * in directly and never renders `Bots`. So nothing but THIS test exercises
   * `Bots.tsx`'s free-play fallback branch (storedGameId === null) — the one
   * line that passes `settings.userColor` into `buildAnalysisLineUrl`.
   * Deleting that 2nd arg must turn these red.
   *
   * Quick 260714-rj5: Analyze is now store-gated (disabled while
   * `analyzeBusy`). The default `beforeEach` mocks `botsApi.storeGame` to
   * reject with a 500, so the store settles as ERRORED after
   * `MAX_STORE_RETRIES` bounded in-flight retries — the free-play fallback
   * path this test exercises. Waiting for the button to become enabled
   * before clicking is load-bearing: clicking a disabled button is a no-op.
   */
  async function finishGameAndClickAnalyze(colorTestId: string): Promise<void> {
    fakeGame.moveHistory = ['e4', 'e5'];
    renderBots();
    await startFromSetup(colorTestId);

    act(() => {
      fakeGame.setPgn('1. e4 e5 *');
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });

    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());
    await waitFor(() =>
      expect((screen.getByTestId('btn-analyze-game') as HTMLButtonElement).disabled).toBe(false),
    );
    fireEvent.click(screen.getByTestId('btn-analyze-game'));
  }

  it('navigates to a URL carrying orientation=black for a game played as Black', async () => {
    await finishGameAndClickAnalyze('setup-color-black');

    expect(navigateSpy).toHaveBeenCalledTimes(1);
    const url = navigateSpy.mock.calls[0]?.[0] as string;
    expect(url).toContain('orientation=black');
    expect(url).toContain('line=e2e4,e7e5');
  });

  it('navigates to a URL carrying orientation=white for a game played as White', async () => {
    await finishGameAndClickAnalyze('setup-color-white');

    expect(navigateSpy).toHaveBeenCalledTimes(1);
    const url = navigateSpy.mock.calls[0]?.[0] as string;
    expect(url).toContain('orientation=white');
    expect(url).toContain('line=e2e4,e7e5');
  });
});

// Quick 260714-rj5 — one-click Analyze: store confirms -> tier-1 enqueue ->
// /analysis?game_id=X. `apiClient.post` (mocked at module level above) backs
// `useTier1EnqueueForGame`'s real, unmocked mutation.
describe('Analyze CTA — one-click tier-1 enqueue (Quick 260714-rj5)', () => {
  const STORED_GAME_ID = 42;

  async function finishGame(): Promise<void> {
    fakeGame.moveHistory = ['e4', 'e5'];
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setPgn('1. e4 e5 *');
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });

    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());
  }

  it('Analyze is disabled while the store mutation is still settling', async () => {
    // Store never resolves during this test — analyzeBusy must stay true.
    vi.mocked(botsApi.storeGame).mockReturnValue(new Promise(() => undefined));

    await finishGame();

    const btn = screen.getByTestId('btn-analyze-game') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('store succeeds -> click Analyze -> POSTs tier1 enqueue with the store-returned game_id, then navigates to /analysis?game_id=X', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({
      game_id: STORED_GAME_ID,
      created: true,
    });

    await finishGame();
    await waitFor(() =>
      expect((screen.getByTestId('btn-analyze-game') as HTMLButtonElement).disabled).toBe(false),
    );

    fireEvent.click(screen.getByTestId('btn-analyze-game'));

    await waitFor(() => expect(apiClient.post).toHaveBeenCalledTimes(1));
    expect(apiClient.post).toHaveBeenCalledWith(`/imports/eval/tier1/${STORED_GAME_ID}`);

    await waitFor(() => expect(navigateSpy).toHaveBeenCalledTimes(1));
    const url = navigateSpy.mock.calls[0]?.[0] as string;
    expect(url).toBe(`/analysis?game_id=${STORED_GAME_ID}`);
  });

  it('store errors (retries exhausted) -> click Analyze -> navigates to the free-play ?line= URL WITHOUT attempting a tier1 enqueue', async () => {
    vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(500));

    await finishGame();
    // Bounded MAX_STORE_RETRIES in-flight retries -> the store settles as
    // errored, re-enabling the button for the fallback path.
    await waitFor(
      () => expect((screen.getByTestId('btn-analyze-game') as HTMLButtonElement).disabled).toBe(false),
      { timeout: 8000 },
    );

    fireEvent.click(screen.getByTestId('btn-analyze-game'));

    await waitFor(() => expect(navigateSpy).toHaveBeenCalledTimes(1));
    const url = navigateSpy.mock.calls[0]?.[0] as string;
    expect(url).toContain('line=e2e4,e7e5');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('a tier1 enqueue in flight keeps Analyze disabled, then navigates once the enqueue SETTLES even on error — the user is never stranded', async () => {
    vi.mocked(botsApi.storeGame).mockResolvedValue({
      game_id: STORED_GAME_ID,
      created: true,
    });
    let rejectEnqueue: ((err: unknown) => void) | undefined;
    vi.mocked(apiClient.post).mockReturnValue(
      new Promise((_resolve, reject) => {
        rejectEnqueue = reject;
      }),
    );

    await finishGame();
    await waitFor(() =>
      expect((screen.getByTestId('btn-analyze-game') as HTMLButtonElement).disabled).toBe(false),
    );

    fireEvent.click(screen.getByTestId('btn-analyze-game'));

    // The enqueue is now in flight — the button must go back to disabled and
    // navigation must NOT have fired yet.
    await waitFor(() =>
      expect((screen.getByTestId('btn-analyze-game') as HTMLButtonElement).disabled).toBe(true),
    );
    expect(navigateSpy).not.toHaveBeenCalled();

    // The enqueue fails — onSettled still opens the game-mode board (never
    // stranding the user on the result screen), and the Sentry report is left
    // to the global MutationCache.onError (no duplicate capture here).
    rejectEnqueue?.(axiosError(500));

    await waitFor(() => expect(navigateSpy).toHaveBeenCalledTimes(1));
    const url = navigateSpy.mock.calls[0]?.[0] as string;
    expect(url).toBe(`/analysis?game_id=${STORED_GAME_ID}`);
  });
});

describe('Bot board passes lastMove through to ChessBoard (171 UAT gap 2)', () => {
  it('passes the from/to squares when the hook reports a lastMove', async () => {
    fakeGame.lastMove = { from: 'e2', to: 'e4' };
    renderBots();
    await startFromSetup();

    expect(screen.getByTestId('chessboard').getAttribute('data-last-move')).toBe('e2e4');
  });

  it('passes null through (no highlight) when the hook reports no lastMove', async () => {
    fakeGame.lastMove = null;
    renderBots();
    await startFromSetup();

    expect(screen.getByTestId('chessboard').getAttribute('data-last-move')).toBe('');
  });
});

describe('BotsGame — bottom-nav clearance (171 UAT gap 3, Task 1)', () => {
  // The clearance is a two-site invariant: SetupScreen's root AND the in-game
  // BotsGame root both need it. SetupScreen's half is pinned in
  // SetupScreen.test.tsx; this is the other half. Without it, dropping pb-20
  // from Bots.tsx left the whole suite green (found by code review, WR-01).
  it('the bots-page root carries pb-20 sm:pb-4 so the fixed bottom nav never occludes the board', async () => {
    renderBots();
    await startFromSetup();

    const className = screen.getByTestId('bots-page').className;
    expect(className).toContain('pb-20');
    expect(className).toContain('sm:pb-4');
  });
});

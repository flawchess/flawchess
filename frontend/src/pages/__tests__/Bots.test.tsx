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
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';

// 171-08 (B-1): spy on navigation so the Analyze CTA's URL can be asserted.
// `renderBots()` mounts a bare `MemoryRouter` with no `<Routes>`, so there is
// no route to probe — the navigate() call itself is the only observable.
// `importOriginal` preserves `MemoryRouter` (imported from this module above).
const navigateSpy = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
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
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    botsApi: {
      ...actual.botsApi,
      storeGame: vi.fn(),
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
}

const fakeGame: FakeGameHandle = {
  setOutcome: () => {},
  setPgn: () => {},
  newGame: vi.fn(),
  lastSettings: null,
  moveHistory: [],
  lastMove: null,
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

    fakeGame.setOutcome = setOutcome;
    fakeGame.setPgn = setPgn;
    fakeGame.lastSettings = settings;

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
      gameUuid: FAKE_GAME_UUID,
      live,
      confirmLive: () => setLive(true),
      attemptMove: vi.fn(() => false),
      viewPly: vi.fn(),
      returnToLive: vi.fn(),
      resign: vi.fn(),
      offerDraw: vi.fn(),
      newGame: fakeGame.newGame,
    };
  },
}));

// ─── Controllable fake useUserProfile ───────────────────────────────────────

interface FakeProfile {
  email: string | null;
  is_guest: boolean;
  lichess_blitz_equivalent_rating: number | null;
}

const profileState: { data: FakeProfile | undefined; isLoading: boolean; isError: boolean } = {
  data: { email: 'user@example.com', is_guest: false, lichess_blitz_equivalent_rating: 1600 },
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

import { botsApi } from '@/api/client';
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

async function startFromSetup(colorTestId = 'setup-color-white', tcTestId = 'setup-tc-blitz-5-3') {
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
  navigateSpy.mockClear();
  vi.mocked(botsApi.storeGame).mockReset();
  // A safe default: the D-13 mount-drain effect fires on EVERY BotsPage
  // mount now that `useDrainPendingStore` is unmocked (Plan 07). Tests that
  // don't care about the store (e.g. the D-11 setup/discard convergence
  // suite above) must not have a stray seeded pending-store entry silently
  // consumed by an unconfigured mock resolving `undefined` as if it were a
  // 2xx. Tests that DO care about the store override this explicitly.
  vi.mocked(botsApi.storeGame).mockRejectedValue(axiosError(500));
  profileState.data = {
    email: 'user@example.com',
    is_guest: false,
    lichess_blitz_equivalent_rating: 1600,
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

    // Not the game, not the setup screen, and NOT stuck on the loading branch.
    expect(screen.queryByTestId('bots-page')).toBeNull();
    expect(screen.queryByTestId('setup-screen')).toBeNull();
    expect(screen.queryByTestId('bots-page-loading')).toBeNull();

    // The anon snapshot was never consumed, and the mount-drain never fired
    // against the anon queue.
    expect(screen.queryByTestId('resume-gate')).toBeNull();
    expect(botsApi.storeGame).not.toHaveBeenCalled();
  });
});

describe('Bots — setup/resume/new-game convergence (V-11)', () => {
  it('renders the setup screen when there is no snapshot', async () => {
    renderBots();

    await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
    expect(screen.queryByTestId('bots-page')).toBeNull();
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

  it('snapshot beats setup — setup-screen is absent when a snapshot is present', async () => {
    localStorage.setItem(snapshotKeyFor('user@example.com'), JSON.stringify(buildSnapshot()));

    renderBots();

    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
    expect(screen.getByTestId('resume-gate')).toBeTruthy();
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

    await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
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

    await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
    expect(screen.queryByTestId('bots-page')).toBeNull();
    // The load-bearing negative assertion (D-11): the old wiring called
    // game.newGame() and restarted in place with the same settings — a test
    // that only checks for setup-screen would also pass against that wiring.
    expect(fakeGame.newGame).not.toHaveBeenCalled();
  });

  it('new game from the result strip also returns to setup, without calling newGame', async () => {
    renderBots();
    await startFromSetup();

    act(() => {
      fakeGame.setOutcome({ reason: 'resignation', winner: 'white' });
    });
    await waitFor(() => expect(screen.getByTestId('result-dialog')).toBeTruthy());

    // Dismiss the dialog (the Dialog primitive's own close button) to reveal
    // the persistent result strip in its place (GamePanel's showResultStrip).
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    await waitFor(() => expect(screen.getByTestId('strip-btn-new-game')).toBeTruthy());

    fireEvent.click(screen.getByTestId('strip-btn-new-game'));

    await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
    expect(screen.queryByTestId('bots-page')).toBeNull();
    expect(fakeGame.newGame).not.toHaveBeenCalled();
  });

  it('guest reaches setup — no email, is_guest, Start still works', async () => {
    profileState.data = {
      email: null,
      is_guest: true,
      lichess_blitz_equivalent_rating: null,
    };

    renderBots();

    await waitFor(() => expect(screen.getByTestId('setup-screen')).toBeTruthy());
    fireEvent.click(screen.getByTestId('setup-color-black'));
    fireEvent.click(screen.getByTestId('btn-start-game'));

    await waitFor(() => expect(screen.getByTestId('bots-page')).toBeTruthy());
    expect(fakeGame.lastSettings?.userColor).toBe('black');
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
});

describe('Analyze CTA carries the played colour (171 UAT gap 1)', () => {
  /**
   * B-1: the JOINING LINE ITSELF. `analysisUrl.test.ts` tests a pure function
   * that never renders `Bots`; `Analysis.test.tsx` feeds `/analysis?…` URLs
   * in directly and never renders `Bots`. So nothing but THIS test exercises
   * `Bots.tsx:310` — the one line that passes `settings.userColor` into
   * `buildAnalysisLineUrl`. Deleting that 2nd arg must turn these red.
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

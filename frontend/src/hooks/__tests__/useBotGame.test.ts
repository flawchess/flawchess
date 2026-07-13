// @vitest-environment jsdom
/**
 * useBotGame unit tests (Phase 169 Plan 04, amended by Plan 09's gap closure).
 *
 * `selectBotMove`, `createDeadlineSearch`, `wouldBotAcceptDraw`, the provider
 * factories (`createWorkerPool`/`createMaiaQueue`), and `@/lib/sounds` are
 * all mocked so no real Stockfish worker/ONNX session spawns and no jsdom
 * Audio machinery is needed. Time is driven entirely by
 * `vi.useFakeTimers({ now: 0 })` + `advanceTimersByTimeAsync` — no real
 * setTimeout waits.
 *
 * Behaviors verified (RESEARCH.md's exact `-t` filter tokens):
 * 1. "turn-gate" (PLAY-03) — attemptMove rejects an off-turn move and an
 *    off-live-position move; accepts a legal user move, applying the
 *    Fischer increment.
 * 2. "pacing" (PLAY-04/05, D-15) — the bot's clock ticks down in real time
 *    during its think, and the eventual debit is the REAL elapsed wall-clock
 *    time of the turn (the honest-clock model this plan restores — a clamp
 *    keeping the bot's clock artificially positive is the SUPERSEDED model
 *    the pre-gap-closure suite asserted).
 * 3. "end-conditions" (PLAY-06) — checkmate (with correct winner),
 *    threefold repetition, and flag-on-time all produce the right outcome.
 *    (Stalemate/fifty-move/insufficient-material detection itself is
 *    exhaustively fixture-tested against chess.js directly in
 *    botGameEnd.test.ts — Plan 02; this suite only needs to prove the single
 *    detectEndCondition call site wires through correctly, which the
 *    checkmate + threefold cases already demonstrate for both the decisive
 *    and non-decisive shapes.)
 * 4. "resign-draw" (PLAY-07) — resign() ends with 'resignation'; offerDraw()
 *    is blocked by the D-04 cooldown after a decline; a queens-off position
 *    satisfying wouldBotAcceptDraw's gate yields a 'draw'/'agreement' outcome.
 * 5. "pgn-export" (PLAY-09) — the finished PGN carries {[%clk ...]} for both
 *    colors and the correct [Termination]/[Result] headers.
 * 6. "bot-clock" (D-15/D-16/D-18, amended SC1) — a bot whose think outlasts
 *    its remaining clock flags a timeout LOSS for the bot (winner = user);
 *    the D-16 think deadline is wired into selectBotMove's deps.search via
 *    createDeadlineSearch, using the reused D-18 node floor
 *    (BOT_MIN_SEARCH_NODES), never a smaller ad-hoc number. Plan 10 gap
 *    closure (CR-02) adds two commit-path flag tests, constructed via
 *    `vi.setSystemTime` so the 100 ms tick provably cannot be the detector:
 *    a bot search resolving after its clock has run out (bot flags, no move
 *    commits), and a user move attempted after their own clock has run out
 *    (commitMove is shared, so the same enforcement applies to the user).
 * 7. "cancel" (D-17) — a cancel (resign) during the bot's think discards the
 *    turn even if the mocked search later resolves.
 * 8. "hidden-tab" (D-20/WR-02, amended SC2) — hidden-tab time during the
 *    bot's think is excluded from its COMMITTED debit; a move committing
 *    while the tab is still hidden can never produce a future-dated anchor
 *    (phantom time) on resume. Plan 10 gap closure (CR-01) adds a test
 *    asserting on the DEBIT itself (not just the anchor) for a bot move
 *    resolving WHILE STILL HIDDEN, plus two tests proving the 100 ms tick
 *    cannot flag either side purely from hidden wall-clock time.
 * 9. "finalize-idempotency" (WR-03) — a stale draw-accept resolving after a
 *    bot move has already delivered checkmate cannot overwrite the outcome.
 *
 * Scripted move sequences (verified via a direct chess.js run before writing
 * these tests, not hand-derived from memory):
 * - Checkmate: Fool's mate (f3 e5 g4 Qh4#) — white mated after 4 plies.
 * - Threefold: Nf3 Nf6 Ng1 Ng8 Nf3 Nf6 Ng1 Ng8 — the start position recurs a
 *   third time after 8 plies.
 * - Queens-off (for the draw-accept gate): e4 e5 Qh5 Qh4 Qxh4 g5 Nf3 gxh4 —
 *   both queens are captured within 8 plies, satisfying wouldBotAcceptDraw's
 *   endgame gate without needing 40 fullmoves or risking an accidental
 *   threefold/insufficient-material short-circuit.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ─── Mocks ───────────────────────────────────────────────────────────────────

const mockSelectBotMove = vi.fn();
vi.mock('@/lib/engine/selectBotMove', () => ({
  selectBotMove: (...args: unknown[]) => mockSelectBotMove(...args),
}));

// D-16 wiring spy — `selectBotMove` itself stays mocked above (so the real
// wrapper never runs here; its cut/floor/cancel BEHAVIOR is covered by plan
// 08's deadlineSearch.test.ts), but we still need the REAL BOT_MIN_SEARCH_NODES
// export for assertions, so this is a passthrough-with-spy, not a full mock.
const mockCreateDeadlineSearch = vi.fn(() => vi.fn());
vi.mock('@/lib/engine/deadlineSearch', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/engine/deadlineSearch')>();
  return {
    ...actual,
    createDeadlineSearch: (...args: Parameters<typeof actual.createDeadlineSearch>) =>
      mockCreateDeadlineSearch(...args),
  };
});

// D-01 accept-gate override — defaults to the REAL wouldBotAcceptDraw (so
// the existing queens-off/cooldown tests are unaffected); Test G sets
// `acceptDrawOverride.value = true` to force the accept branch regardless of
// the real board/score, since the Fool's-mate script never satisfies the
// real endgame gate. A plain mutable object (not a `vi.fn()`) so the
// factory below never eagerly touches a hoisted `const` — only a deferred
// closure reads it, at actual call time, well after the test file's own
// top-level code has run (vi.mock factories run as part of resolving
// useBotGame.ts's import graph, which happens BEFORE this file's own
// top-level `const` statements — a `vi.fn()` mutated eagerly inside the
// factory body would trip a TDZ ReferenceError here).
const acceptDrawOverride: { value: boolean | null } = { value: null };
vi.mock('@/lib/botDrawGate', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/botDrawGate')>();
  return {
    ...actual,
    wouldBotAcceptDraw: (...args: Parameters<typeof actual.wouldBotAcceptDraw>) =>
      acceptDrawOverride.value !== null ? acceptDrawOverride.value : actual.wouldBotAcceptDraw(...args),
  };
});

const mockGrade = vi.fn();
const mockPoolTerminate = vi.fn();
const mockCreateWorkerPool = vi.fn(() => ({
  grade: mockGrade,
  terminate: mockPoolTerminate,
}));
vi.mock('@/lib/engine/workerPool', () => ({
  createWorkerPool: () => mockCreateWorkerPool(),
}));

const mockPolicy = vi.fn();
const mockQueueTerminate = vi.fn();
const mockCreateMaiaQueue = vi.fn(() => ({
  policy: mockPolicy,
  terminate: mockQueueTerminate,
}));
vi.mock('@/lib/engine/maiaQueue', () => ({
  createMaiaQueue: () => mockCreateMaiaQueue(),
}));

const mockPlaySound = vi.fn();
const mockUnlockAudio = vi.fn();
vi.mock('@/lib/sounds', () => ({
  playSound: (...args: unknown[]) => mockPlaySound(...args),
  unlockAudio: () => mockUnlockAudio(),
}));

const mockCaptureException = vi.fn();
vi.mock('@sentry/react', () => ({
  captureException: (...args: unknown[]) => mockCaptureException(...args),
}));

import { useBotGame, type BotGameSettings } from '../useBotGame';
import { computeThinkDeadlineMs } from '@/lib/chessClock';
import { BOT_MIN_SEARCH_NODES } from '@/lib/engine/deadlineSearch';

// ─── Fixtures ────────────────────────────────────────────────────────────────

const DEFAULT_SETTINGS: BotGameSettings = {
  botElo: 1500,
  blend: 0.5,
  baseSeconds: 300,
  incrementSeconds: 0,
  userColor: 'white',
};

/** Advances the fake clock (wrapped in act so React flushes the resulting
 * state updates), the standard way every test lets a bot think/reveal-delay
 * resolve without a real setTimeout wait. */
async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

/** Flips jsdom's `document.visibilityState` and dispatches the
 * `visibilitychange` event `useBotGame`'s hidden-tab-pause effect listens
 * for (D-20/WR-02 tests) — jsdom does not implement tab visibility itself,
 * so the property must be redefined per 169-RESEARCH.md's documented
 * technique. */
function setHidden(hidden: boolean): void {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => (hidden ? 'hidden' : 'visible'),
  });
  document.dispatchEvent(new Event('visibilitychange'));
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('useBotGame', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockSelectBotMove.mockReset();
    // Default: never resolves — tests that don't care about the bot's reply
    // (e.g. pure turn-gate/off-turn checks) don't need it to settle.
    mockSelectBotMove.mockImplementation(() => new Promise(() => {}));
    mockCreateDeadlineSearch.mockClear();
    acceptDrawOverride.value = null;
    mockGrade.mockReset().mockResolvedValue(new Map());
    mockPoolTerminate.mockReset();
    mockCreateWorkerPool.mockClear();
    mockPolicy.mockReset();
    mockQueueTerminate.mockReset();
    mockCreateMaiaQueue.mockClear();
    mockPlaySound.mockReset();
    mockUnlockAudio.mockReset();
    mockCaptureException.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    // Undo the jsdom visibilityState redefinition so it never leaks across
    // tests/files.
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'visible',
    });
  });

  describe('turn-gate', () => {
    it('rejects an off-turn move (userColor=black while white is to move)', () => {
      const { result } = renderHook(() =>
        useBotGame({ ...DEFAULT_SETTINGS, userColor: 'black' }),
      );

      let success: boolean | undefined;
      act(() => {
        success = result.current.attemptMove('e7', 'e5');
      });

      expect(success).toBe(false);
      expect(result.current.moveHistory).toEqual([]);
    });

    it('rejects an off-live-position move (view-only mode after navigating back)', async () => {
      mockSelectBotMove.mockResolvedValueOnce('e7e5');
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });
      await advance(2000);
      expect(result.current.moveHistory).toEqual(['e4', 'e5']);

      act(() => {
        result.current.viewPly(0);
      });
      expect(result.current.viewedPly).toBe(0);

      let success: boolean | undefined;
      act(() => {
        success = result.current.attemptMove('d2', 'd4');
      });

      expect(success).toBe(false);
      expect(result.current.moveHistory).toEqual(['e4', 'e5']); // unchanged
    });

    it('accepts a legal user move, applying the Fischer increment', () => {
      const { result } = renderHook(() =>
        useBotGame({ ...DEFAULT_SETTINGS, incrementSeconds: 5 }),
      );

      let success: boolean | undefined;
      act(() => {
        success = result.current.attemptMove('e2', 'e4');
      });

      expect(success).toBe(true);
      expect(result.current.moveHistory).toEqual(['e4']);
      // No time elapsed (fake clock frozen at mount) + a 5s increment.
      expect(result.current.whiteClockMs).toBe(300_000 + 5_000);
    });
  });

  describe('pacing', () => {
    it('ticks the bot clock down in real time during a long think, and debits the REAL elapsed time on commit (D-15 honest clock)', async () => {
      mockSelectBotMove.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve('e7e5'), 8000)),
      );
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });

      // Partway through the bot's think — the clock has visibly ticked down,
      // isBotThinking reflects the real in-flight promise (Pitfall 3).
      await advance(4000);
      expect(result.current.isBotThinking).toBe(true);
      expect(result.current.blackClockMs).toBeLessThan(300_000);
      expect(result.current.blackClockMs).toBeGreaterThan(0);

      // Let the search + reveal-delay floor both resolve (Promise.all,
      // Pattern 3 — never a race).
      await advance(6000);
      expect(result.current.isBotThinking).toBe(false);
      expect(result.current.moveHistory).toEqual(['e4', 'e5']);
      // D-15: the debit is the REAL elapsed wall-clock time of the ~8s
      // think (plus effect-dispatch/scheduling slack), not a synthetic
      // fraction-of-remaining schedule — a band around 8-10s proves the
      // honest-clock model, distinct from the old synthetic formula
      // (remaining/20 + increment*0.9 = 15000ms here, which this range
      // excludes).
      expect(result.current.blackClockMs).toBeLessThan(300_000 - 7000);
      expect(result.current.blackClockMs).toBeGreaterThan(300_000 - 11000);
    });
  });

  describe('end-conditions', () => {
    it('detects checkmate with the correct winner (Fool\'s mate)', async () => {
      mockSelectBotMove.mockResolvedValueOnce('e7e5').mockResolvedValueOnce('d8h4');
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('f2', 'f3');
      });
      await advance(2000);
      act(() => {
        result.current.attemptMove('g2', 'g4');
      });
      await advance(2000);

      expect(result.current.moveHistory).toEqual(['f3', 'e5', 'g4', 'Qh4#']);
      expect(result.current.outcome).toEqual({ reason: 'checkmate', winner: 'black' });
    });

    it('detects a draw by threefold repetition', async () => {
      mockSelectBotMove
        .mockResolvedValueOnce('g8f6')
        .mockResolvedValueOnce('f6g8')
        .mockResolvedValueOnce('g8f6')
        .mockResolvedValueOnce('f6g8');
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      const userMoves: [string, string][] = [
        ['g1', 'f3'],
        ['f3', 'g1'],
        ['g1', 'f3'],
        ['f3', 'g1'],
      ];
      for (const [from, to] of userMoves) {
        act(() => {
          result.current.attemptMove(from, to);
        });
        await advance(2000);
      }

      expect(result.current.outcome).toEqual({ reason: 'draw', drawReason: 'threefold' });
    });

    it('ends the game with a timeout when the active side\'s clock reaches zero', async () => {
      const { result } = renderHook(() =>
        useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 1 }),
      );

      // White (the user) never moves — its own clock (the only ticking one)
      // runs out first.
      await advance(1100);

      expect(result.current.outcome).toEqual({ reason: 'timeout', winner: 'black' });
      expect(result.current.whiteClockMs).toBe(0);
    });
  });

  describe('bot clock (D-15/D-16/D-18, amended SC1)', () => {
    it('bot flags on time: a think longer than its remaining clock produces a timeout LOSS for the bot, winner = user', async () => {
      const LOW_BASE_SECONDS = 2; // 2000ms — the bot's whole clock
      // Never resolves within the window — the bot's clock alone decides.
      mockSelectBotMove.mockImplementation(() => new Promise(() => {}));
      const { result } = renderHook(() =>
        useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: LOW_BASE_SECONDS }),
      );

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });

      // The bot's whole clock (2000ms) elapses without its think ever
      // resolving.
      await advance(2100);

      expect(result.current.outcome).toEqual({ reason: 'timeout', winner: 'white' });
      expect(result.current.moveHistory).toEqual(['e4']); // bot's move never committed
    });

    it('wires the D-16 think deadline into deps.search via createDeadlineSearch, using the D-18 node floor, and a resolved (deadline-cut) search still commits', async () => {
      mockSelectBotMove.mockResolvedValueOnce('e7e5');
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });
      await advance(2000);

      expect(mockSelectBotMove).toHaveBeenCalledTimes(1);
      const depsArg = mockSelectBotMove.mock.calls[0]?.[2] as { search?: unknown };
      expect(depsArg?.search).toBeDefined();

      // DEFAULT_SETTINGS: 300s base clock, 0 increment.
      expect(mockCreateDeadlineSearch).toHaveBeenCalledWith({
        deadlineMs: computeThinkDeadlineMs(300_000, 0),
        minNodes: BOT_MIN_SEARCH_NODES,
      });

      // A resolved search (whether cut by the deadline or finished on its
      // own budget — indistinguishable from this wiring test's vantage
      // point) still COMMITS the move; the turn is not discarded.
      expect(result.current.moveHistory).toEqual(['e4', 'e5']);
    });

    it('the node floor stays BOT_MIN_SEARCH_NODES even when the bot is low on time — never configured smaller under a tight deadline', async () => {
      mockSelectBotMove.mockResolvedValueOnce('e7e5');
      const LOW_BASE_SECONDS = 3; // 3000ms — yields a small D-16 deadline
      const { result } = renderHook(() =>
        useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: LOW_BASE_SECONDS }),
      );

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });
      await advance(2000);

      const call = mockCreateDeadlineSearch.mock.calls[0]?.[0] as {
        minNodes?: number;
        deadlineMs?: number;
      };
      expect(call?.minNodes).toBe(BOT_MIN_SEARCH_NODES);
      expect(call?.deadlineMs).toBe(computeThinkDeadlineMs(3000, 0));
    });

    it('a bot search resolving after its clock has already run out flags the bot (timeout, winner = user) and commits NO move — the commit path is the flag detector, not the tick', async () => {
      let resolveSearch: ((uci: string) => void) | undefined;
      mockSelectBotMove.mockImplementation(
        () =>
          new Promise<string>((resolve) => {
            resolveSearch = resolve;
          }),
      );
      const { result } = renderHook(() =>
        useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 3, incrementSeconds: 2 }),
      );

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });
      // Clears the D-16 reveal-delay floor (clamped to the ~1500ms deadline
      // at this clock/increment: 3000/30 + 2000*0.7 = 1500) — black is left
      // with ~1400ms remaining, not yet flagged.
      await advance(1600);
      expect(result.current.outcome).toBeNull();

      // Move Date.now() forward WITHOUT advancing any fake timer — the
      // pending 100ms interval is NOT fired, so it provably cannot be the
      // flag detector for what follows. Only the commit path (which reads
      // Date.now() directly via chargeableElapsedMs) can see this jump.
      vi.setSystemTime(6600);

      resolveSearch?.('e7e5');
      await advance(0);

      expect(result.current.outcome).toEqual({ reason: 'timeout', winner: 'white' });
      expect(result.current.moveHistory).toEqual(['e4']); // bot's move never committed
      expect(result.current.blackClockMs).toBe(0);
    });

    it('a user move attempted after their own clock has already run out flags the user (timeout, winner = bot) and commits NO move', () => {
      const { result } = renderHook(() =>
        useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 3, incrementSeconds: 2 }),
      );

      // Advance NO timers at all — the tick provably cannot be the
      // detector — only Date.now() is moved.
      vi.setSystemTime(5000);

      let success: boolean | undefined;
      act(() => {
        success = result.current.attemptMove('e2', 'e4');
      });

      expect(success).toBe(false);
      expect(result.current.outcome).toEqual({ reason: 'timeout', winner: 'black' });
      expect(result.current.moveHistory).toEqual([]);
      expect(result.current.whiteClockMs).toBe(0);
    });
  });

  describe('cancel (D-17)', () => {
    it('a cancel during the bot think (resign) discards the turn even after the search later resolves', async () => {
      let resolveSearch: ((uci: string) => void) | undefined;
      mockSelectBotMove.mockImplementation(
        () =>
          new Promise<string>((resolve) => {
            resolveSearch = resolve;
          }),
      );
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });
      await advance(1000);

      act(() => {
        result.current.resign();
      });
      expect(result.current.outcome).toEqual({ reason: 'resignation', winner: 'black' });

      // The mocked search resolves AFTER the cancel — must not commit.
      await act(async () => {
        resolveSearch?.('e7e5');
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(result.current.moveHistory).toEqual(['e4']); // bot's move never committed
      expect(result.current.outcome).toEqual({ reason: 'resignation', winner: 'black' }); // unchanged
    });
  });

  describe('hidden-tab time (D-20/WR-02, amended SC2)', () => {
    it('hidden-tab time during the bot think is not charged to its committed debit', async () => {
      let resolveSearch: ((uci: string) => void) | undefined;
      mockSelectBotMove.mockImplementation(
        () =>
          new Promise<string>((resolve) => {
            resolveSearch = resolve;
          }),
      );
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });

      // Hide the tab immediately as the bot's think begins, and leave it
      // hidden for a LONG interval.
      setHidden(true);
      await advance(5000);

      // Resume, let the reveal-delay floor clear, then let the bot reply.
      setHidden(false);
      await advance(1500);
      resolveSearch?.('e7e5');
      await advance(500);

      expect(result.current.moveHistory).toEqual(['e4', 'e5']);
      const debited = 300_000 - result.current.blackClockMs; // incrementSeconds=0
      // Only the ~2000ms VISIBLE interval is charged — the 5000ms hidden
      // interval must not reach the committed debit. A pre-D-20-fix dispatch
      // -time snapshot would charge the FULL ~7000ms+ elapsed instead.
      expect(debited).toBeGreaterThan(0);
      expect(debited).toBeLessThan(3000);
    });

    it('a bot move committed while the tab is still hidden cannot produce a future-dated anchor on resume (WR-02) — no phantom time credited', async () => {
      let resolveSearch: ((uci: string) => void) | undefined;
      mockSelectBotMove.mockImplementation(
        () =>
          new Promise<string>((resolve) => {
            resolveSearch = resolve;
          }),
      );
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });

      setHidden(true);
      await advance(1500); // clears the reveal-delay floor, still hidden
      resolveSearch?.('e7e5');
      await advance(500); // the bot's move commits WHILE STILL HIDDEN

      expect(result.current.moveHistory).toEqual(['e4', 'e5']);
      const whiteBaseMs = DEFAULT_SETTINGS.baseSeconds * 1000; // incrementSeconds=0, untouched by black's move

      // A further hidden interval, THEN resume — the buggy pre-fix anchor
      // (pausedAtRef stuck at the ORIGINAL hide time instead of re-baselined
      // to the commit instant) would land in the future here, producing a
      // negative elapsed and crediting white (the now-active side) phantom
      // time on the very next tick — pushing its clock ABOVE its own base.
      // This is the actual bug signature: NOT merely "higher than some
      // earlier hidden-interval reading" (the display legitimately keeps
      // ticking down while hidden, then correctly jumps back up at resume
      // once the pause discount applies) but literally exceeding the base.
      await advance(3000); // still hidden
      setHidden(false);
      await advance(200); // let the resume handler's shift + the next tick apply

      expect(result.current.whiteClockMs).toBeLessThanOrEqual(whiteBaseMs);
      expect(result.current.whiteClockMs).toBeGreaterThan(0);
    });

    it('a bot move committing WHILE THE TAB IS STILL HIDDEN debits only the pre-hide visible time — the hidden interval never reaches the committed debit', async () => {
      let resolveSearch: ((uci: string) => void) | undefined;
      mockSelectBotMove.mockImplementation(
        () =>
          new Promise<string>((resolve) => {
            resolveSearch = resolve;
          }),
      );
      // DEFAULT_SETTINGS: 300s base clock, so the tick cannot flag — this
      // isolates the assertion to the DEBIT, not a timeout.
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });
      await advance(2000); // visible think time before hiding
      setHidden(true);
      await advance(30000); // long hidden interval, still hidden

      // The bot's move commits WHILE STILL HIDDEN — the common case, since
      // Web Workers keep searching in the background. The existing
      // 'hidden-tab time during the bot think is not charged...' test above
      // resolves AFTER un-hiding and never asserts on the debit itself —
      // this is the hole that test leaves open.
      resolveSearch?.('e7e5');
      await advance(0);

      expect(result.current.moveHistory).toEqual(['e4', 'e5']);
      expect(result.current.outcome).toBeNull();
      const debited = 300_000 - result.current.blackClockMs; // incrementSeconds=0
      // Only the ~2000ms VISIBLE portion is charged. Un-fixed, the debit is
      // ~32000ms (the full visible+hidden elapsed reaching the commit).
      expect(debited).toBeGreaterThan(0);
      expect(debited).toBeLessThan(3000);
    });

    it('the 100 ms tick cannot flag the user while the tab is hidden', async () => {
      const { result } = renderHook(() => useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 3 }));

      setHidden(true);
      await advance(30000);

      expect(result.current.outcome).toBeNull();
      expect(result.current.whiteClockMs).toBe(3000); // elapsed frozen at the pause instant

      setHidden(false);
      await advance(200);

      // The resume-edge shift discounted the whole hidden window.
      expect(result.current.whiteClockMs).toBeLessThanOrEqual(3000);
      expect(result.current.whiteClockMs).toBeGreaterThan(0);
    });

    it('the 100 ms tick cannot flag the bot while the tab is hidden during its think', async () => {
      // The default mock (see beforeEach): selectBotMove never resolves.
      const { result } = renderHook(() => useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 3 }));

      act(() => {
        result.current.attemptMove('e2', 'e4');
      });

      setHidden(true);
      await advance(30000);

      expect(result.current.outcome).toBeNull();
      expect(result.current.blackClockMs).toBe(3000);
      expect(result.current.moveHistory).toEqual(['e4']);
    });

    it('a game mounting into an ALREADY-hidden tab charges no background time and never flags', async () => {
      // `visibilitychange` fires only on a transition, so the hidden state must be
      // in place BEFORE renderHook — this is the background-tab-open / session-restore
      // path, and the one the other hidden-tab tests cannot reach.
      setHidden(true);

      const { result } = renderHook(() => useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 3 }));
      await advance(30000);

      expect(result.current.outcome).toBeNull();
      expect(result.current.whiteClockMs).toBe(3000);

      // And the resume edge still discounts the whole hidden window rather than
      // leaving the anchor stranded.
      setHidden(false);
      await advance(200);

      expect(result.current.whiteClockMs).toBeLessThanOrEqual(3000);
      expect(result.current.whiteClockMs).toBeGreaterThan(0);
    });

    it('a duplicate hidden event does not re-baseline an in-progress pause forward', async () => {
      const { result } = renderHook(() => useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 3 }));

      setHidden(true);
      await advance(10000);
      // Safari re-fires visibilitychange while already hidden (pagehide / bfcache).
      // A second `hidden` write would move the pause instant to now, charging the
      // 10s that just elapsed.
      setHidden(true);
      await advance(10000);

      expect(result.current.outcome).toBeNull();
      expect(result.current.whiteClockMs).toBe(3000);
    });
  });

  describe('resign-draw', () => {
    it('resign() ends the game with a resignation outcome (the user loses; the bot never resigns)', () => {
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.resign();
      });

      expect(result.current.outcome).toEqual({ reason: 'resignation', winner: 'black' });
    });

    it('offerDraw() is blocked by the D-04 cooldown immediately after a decline', async () => {
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      // Early in the game (no queens off, moveNumber low) the accept-gate is
      // false regardless of score, so this offer resolves to a decline.
      expect(result.current.canOfferDraw).toBe(true); // offerable from the start
      act(() => {
        result.current.offerDraw();
      });
      await advance(0); // flush the drawOfferPending resolution effect

      expect(mockPlaySound).toHaveBeenCalledWith('draw-declined');
      expect(result.current.outcome).toBeNull();
      expect(result.current.canOfferDraw).toBe(false); // cooldown now active

      act(() => {
        result.current.offerDraw(); // blocked — no-op
      });
      expect(result.current.drawOfferPending).toBe(false);
    });

    it('a queens-off position satisfying wouldBotAcceptDraw yields a draw-by-agreement outcome', async () => {
      mockSelectBotMove
        .mockResolvedValueOnce('e7e5')
        .mockResolvedValueOnce('d8h4')
        .mockResolvedValueOnce('g7g5')
        .mockResolvedValueOnce('g5h4');
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      const userMoves: [string, string][] = [
        ['e2', 'e4'],
        ['d1', 'h5'],
        ['h5', 'h4'],
        ['g1', 'f3'],
      ];
      for (const [from, to] of userMoves) {
        act(() => {
          result.current.attemptMove(from, to);
        });
        await advance(2000);
      }

      expect(result.current.moveHistory).toEqual([
        'e4',
        'e5',
        'Qh5',
        'Qh4',
        'Qxh4',
        'g5',
        'Nf3',
        'gxh4',
      ]);

      act(() => {
        result.current.offerDraw();
      });
      await advance(0);

      expect(result.current.outcome).toEqual({ reason: 'draw', drawReason: 'agreement' });
    });
  });

  describe('finalize idempotency (WR-03)', () => {
    it('a stale draw-accept resolving after a bot move already delivered checkmate does not overwrite the outcome', async () => {
      // Forces the accept branch regardless of the real board/score — the
      // Fool's-mate script keeps queens on the board and the move number
      // low, so the REAL gate would decline anyway, masking the bug this
      // test targets (finalizeGame's own idempotency, not the gate).
      acceptDrawOverride.value = true;
      mockSelectBotMove.mockResolvedValueOnce('e7e5').mockResolvedValueOnce('d8h4');
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      // Captured BEFORE the checkmate lands — simulates an async
      // continuation (or a stale closure under rapid updates, per
      // 169-REVIEW.md WR-03) that still believes the game is in progress:
      // this closure's own `outcome` check reads null, bypassing offerDraw's
      // OWN (pre-existing, correctly-fresh) guard.
      const staleOfferDraw = result.current.offerDraw;

      act(() => {
        result.current.attemptMove('f2', 'f3');
      });
      await advance(2000);
      act(() => {
        result.current.attemptMove('g2', 'g4');
      });
      await advance(2000);

      expect(result.current.outcome).toEqual({ reason: 'checkmate', winner: 'black' });
      const pgnAfterMate = result.current.pgn;
      mockPlaySound.mockClear();

      act(() => {
        staleOfferDraw();
      });
      await advance(0);

      expect(result.current.outcome).toEqual({ reason: 'checkmate', winner: 'black' }); // unchanged
      expect(result.current.pgn).toBe(pgnAfterMate); // not regenerated
      expect(mockPlaySound).not.toHaveBeenCalledWith('game-end'); // no duplicate finalize
      expect(result.current.drawOfferPending).toBe(false); // effect still clears the pending flag
    });
  });

  describe('pgn-export', () => {
    it('produces a finished PGN with both-color [%clk] annotations and the correct Termination/Result', async () => {
      mockSelectBotMove.mockResolvedValueOnce('e7e5').mockResolvedValueOnce('d8h4');
      const { result } = renderHook(() => useBotGame(DEFAULT_SETTINGS));

      act(() => {
        result.current.attemptMove('f2', 'f3');
      });
      await advance(2000);
      act(() => {
        result.current.attemptMove('g2', 'g4');
      });
      await advance(2000);

      expect(result.current.outcome).toEqual({ reason: 'checkmate', winner: 'black' });
      const pgn = result.current.pgn ?? '';
      expect(pgn.length).toBeGreaterThan(0);

      const clkMatches = pgn.match(/\{\[%clk \d+:\d{2}:\d{2}\]\}/g) ?? [];
      // One [%clk] comment per ply (2 white + 2 black) — proves both colors
      // are annotated, not just one (STORE-02's per-color presence gate).
      expect(clkMatches.length).toBe(4);

      expect(pgn).toContain('[Termination "checkmate"]');
      expect(pgn).toContain('[Result "0-1"]');
    });
  });
});

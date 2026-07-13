/**
 * useBotGame — the orchestrating game-loop hook for clocked bot play (Phase
 * 169). Composes the plan-01/02/03 pure modules (chessClock, botGameEnd,
 * botDrawGate, botGamePgn, sounds) with the frozen `selectBotMove` engine core
 * (Phase 166/168.5) and chess.js. This is pure orchestration — chess.js owns
 * rules/legality/end-conditions, `selectBotMove` owns move selection, the
 * plan-01/02/03 modules own timing/end-detection/draw-gate/PGN/sound. This
 * hook wires them and exposes the stable state+callbacks contract Phases 170
 * (localStorage resume) and 171 (setup screen + store-on-finish) build on.
 *
 * `viewedPly` and `liveGamePly` are modeled as two SEPARATE numbers (D-13,
 * 169-RESEARCH.md Pitfall 5's two-independent-state-pieces lesson applied to
 * viewing-vs-live state) — `liveGamePly` is always `moveHistory.length`;
 * `viewedPly` is the ply the board currently displays (view-only when it
 * differs from `liveGamePly`).
 *
 * CLOCK MODEL (D-15/D-16, 2026-07-13 gap closure — supersedes the original
 * 168.5 never-flag model this hook shipped with): the bot's clock is HONEST.
 * On commit it is debited exactly the real wall-clock time its turn consumed
 * (search + reveal delay), plus the Fischer increment — the same rule the
 * user's clock obeys. There is no synthetic fraction-of-remaining debit and
 * no never-flag clamp anywhere in this file; the bot CAN lose on time
 * (amended ROADMAP SC1), and that invariant is ENFORCED at the commit site —
 * `hasFlaggedOnDebit` (chessClock.ts), called via the `flagIfOutOfTime`
 * helper before the move is applied in both `attemptMove` and `runBotTurn` —
 * not merely absent from this file (Plan 10 gap closure, CR-02). Because a
 * fixed search budget under an honest clock is degenerate (the bot would
 * bleed net time every move), the bot manages its own pace via a per-move
 * think deadline (`computeThinkDeadlineMs`, chessClock.ts D-16) injected
 * into `selectBotMove` through the `deps.search` seam
 * (`createDeadlineSearch`, deadlineSearch.ts) — a deadline cut returns the
 * search's best-so-far move (D-17); it never discards the turn. Only a
 * genuine CANCEL (resign / new game / unmount / bot flagged) discards a
 * turn. D-19: this means the bot's calibrated ELO (measured at the full
 * node budget) holds only when it is NOT low on its own clock — a
 * deadline-cut bot in time trouble plays materially weaker than advertised,
 * by design (humans get worse in time trouble too).
 *
 * D-20/WR-02 (hidden-tab hardening, Plan 10 gap closure CR-01): every
 * elapsed-time consumer in this file — the clock tick's flag check, the
 * bot's committed debit, and the user's move debit — reads through the ONE
 * pause-aware `chargeableElapsedMs` helper (wrapping chessClock.ts's
 * `computeChargeableElapsedMs`), so a hidden interval reaches neither the
 * tick's flag check nor the committed debit, for either side. The
 * anchor-reset helper (`resetTurnAnchor`) still re-baselines an in-progress
 * pause alongside the turn anchor on every commit, so a move committing
 * while the tab is hidden can never produce a future-dated anchor on
 * resume.
 *
 * WR-03/WR-05 (finalize idempotency, scroll-back preservation): `finalizeGame`
 * is latched by `outcomeRef` — the first outcome wins, and every caller
 * (including the async draw-resolution effect, which can run after the game
 * has already ended) checks it before doing anything. `commitMove` snaps
 * `viewedPly` to the live position only when the viewer was already live (or
 * the mover is the user, who can only move from the live position anyway) —
 * a bot move no longer ejects the user from D-13 scroll-back.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Chess, type Move } from 'chess.js';
import * as Sentry from '@sentry/react';

import type { MoverColor } from '@/lib/liveFlaw';
import { evalToExpectedScore } from '@/lib/liveFlaw';
import {
  applyIncrementMs,
  computeChargeableElapsedMs,
  hasFlaggedOnDebit,
  shiftAnchorForPause,
  computeThinkDeadlineMs,
  computeRevealDelayMs,
  isLowTime,
} from '@/lib/chessClock';
import { detectEndCondition, type BotGameOutcome } from '@/lib/botGameEnd';
import {
  canOfferDraw as canOfferDrawGate,
  wouldBotAcceptDraw,
  DRAW_OFFER_COOLDOWN_MOVES,
} from '@/lib/botDrawGate';
import { annotateClock, finalizeBotPgn, toBackendTcStr } from '@/lib/botGamePgn';
import { playSound, unlockAudio } from '@/lib/sounds';
import { createWorkerPool, type WorkerPool } from '@/lib/engine/workerPool';
import { createMaiaQueue, type MaiaQueue } from '@/lib/engine/maiaQueue';
import { selectBotMove, type BotMoveDeps } from '@/lib/engine/selectBotMove';
import { selectBookMove } from '@/lib/engine/openingBook';
import { loadOpeningPrefixSet } from '@/lib/openings';
import { createDeadlineSearch, BOT_MIN_SEARCH_NODES } from '@/lib/engine/deadlineSearch';
import {
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_CONCURRENCY,
  FLAWCHESS_BOT_STOP_RULE,
} from '@/lib/engine/botBudget';
import type { SearchBudget, Side } from '@/lib/engine/types';

// ─── Named constants ─────────────────────────────────────────────────────────

/** Display-clock recompute cadence (PLAY-04) — matches lichess-style clocks;
 * the displayed value is always recomputed from a wall-clock anchor, never
 * accumulated from this interval's tick count. */
const CLOCK_TICK_INTERVAL_MS = 100;

/**
 * The bot's fixed NODE budget (168.5, locked) — assembled once here from
 * `botBudget.ts`'s shipped constants (imported directly, never via
 * `useFlawChessEngine.ts`'s re-export — Pitfall 6). This is the search's
 * upper bound, unrelated to and unchanged by the D-16 think deadline below —
 * the deadline can CUT a search short of this budget in time trouble
 * (D-19), it never raises it. `elo`/`policyTemperature` are supplied
 * per-call by `selectBotMove` itself (D-02/D-07), never here.
 */
const BOT_SEARCH_BUDGET: Omit<SearchBudget, 'elo' | 'policyTemperature'> = {
  maxNodes: FLAWCHESS_BOT_MAX_NODES,
  maxPlies: FLAWCHESS_BOT_MAX_PLIES,
  concurrency: FLAWCHESS_BOT_CONCURRENCY,
  stopRule: FLAWCHESS_BOT_STOP_RULE,
};

// ─── Types ───────────────────────────────────────────────────────────────────

/** The bot's own play settings for one game (Claude's-discretion shape). */
export interface BotGameSettings {
  /** The bot's own ELO (BOT-03) — see selectBotMove.ts's D-07 invariant. */
  botElo: number;
  /** 0 = full-human, 1 = full-stockfish (selectBotMove's regime blend). */
  blend: number;
  /** Starting clock time for both sides, in seconds. */
  baseSeconds: number;
  /** Fischer increment applied to the mover after each move, in seconds. */
  incrementSeconds: number;
  /** Which color the human player is playing. */
  userColor: MoverColor;
}

/** The full state + callback contract this hook exposes. Serializable aside
 * from callback identities — Phase 170 snapshots the state fields directly. */
export interface UseBotGameState {
  /** FEN of the position currently DISPLAYED (viewedPly), not necessarily live. */
  position: string;
  /** SAN move history of the live game. */
  moveHistory: string[];
  /** The live game's current ply (== moveHistory.length). */
  liveGamePly: number;
  /** The ply currently displayed; board input is disabled unless this equals liveGamePly. */
  viewedPly: number;
  /** True while the bot's selectBotMove think is in flight. */
  isBotThinking: boolean;
  /** White's remaining clock time, ms, recomputed from a wall-clock anchor. */
  whiteClockMs: number;
  /** Black's remaining clock time, ms, recomputed from a wall-clock anchor. */
  blackClockMs: number;
  /** Whose turn it currently is in the live game. */
  activeColor: MoverColor;
  /** Set once the game has ended; null while in progress. */
  outcome: BotGameOutcome | null;
  /** The finished game's PGN (both-color [%clk] + Termination/Result), set on game end. */
  pgn: string | null;
  /** True while a user-initiated draw offer is being resolved. */
  drawOfferPending: boolean;
  /** Whether the "Offer draw" button is currently clickable (D-04 throttle). */
  canOfferDraw: boolean;
  /** Attempt a user move; returns false (board snaps back) if illegal, off-turn, or off-live-position. */
  attemptMove: (from: string, to: string) => boolean;
  /** View a historical ply (board becomes read-only until returnToLive()). */
  viewPly: (ply: number) => void;
  /** Snap the viewed ply back to the live game position. */
  returnToLive: () => void;
  /** Confirmed resignation — ends the game with the user losing. */
  resign: () => void;
  /** Offer a draw to the bot, subject to the D-04 cooldown throttle. */
  offerDraw: () => void;
  /** Reset to a fresh game with the same settings. */
  newGame: () => void;
}

// ─── Pure helpers ────────────────────────────────────────────────────────────

/** Replays SAN moves [0, ply) on a fresh board to compute the FEN at that ply. */
function fenAtPly(moveHistory: string[], ply: number): string {
  const chess = new Chess();
  for (let i = 0; i < ply; i++) {
    // safe: loop bound ensures i < ply <= moveHistory.length
    chess.move(moveHistory[i]!);
  }
  return chess.fen();
}

function freshClockBase(baseSeconds: number): { white: number; black: number } {
  const ms = baseSeconds * 1000;
  return { white: ms, black: ms };
}

/** The D-03 reveal-delay floor as a plain awaitable (Pattern 3 — run via
 * Promise.all alongside selectBotMove, never sequentially awaited). */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Assembles the deps object passed to `selectBotMove` for one bot turn — the
 * ONLY wiring point where the D-16 think deadline reaches the engine, via
 * the injectable `deps.search` seam (Phase 166 D-08). Extracted out of
 * `runBotTurn`'s async body (that body is already dense — CLAUDE.md
 * nesting/logic-LOC limits) so the deadline wiring is isolated and easy to
 * audit in one place.
 */
function buildBotMoveDeps(deadlineMs: number, queue: MaiaQueue, pool: WorkerPool): BotMoveDeps {
  return {
    policy: queue.policy,
    grade: pool.grade,
    rng: Math.random,
    search: createDeadlineSearch({ deadlineMs, minNodes: BOT_MIN_SEARCH_NODES }),
  };
}

/**
 * Resolves the bot's opening-book move for this turn (169.5, PLAY-11), or
 * `null` meaning "leave book" — the caller latches `hasLeftBookRef` on `null`
 * and falls through to `selectBotMove`.
 *
 * A book ply costs exactly ONE Maia policy eval (~100ms) and ZERO Stockfish
 * searches (D-02) — which is the whole point: it is near-instant, clock-cheap,
 * and it warms Maia by necessity. Extracted to module scope (beside
 * `buildBotMoveDeps`) so `runBotTurn`'s async body does not grow past
 * CLAUDE.md's nesting/logic-LOC limits.
 *
 * The book is wired HERE, in the hook, and never inside `selectBotMove` —
 * `scripts/calibration-harness.mjs` imports `selectBotMove` directly and has
 * its own game loop that never touches this hook, so the harness staying
 * book-free is STRUCTURAL, not guard-based. Its anchor games already start
 * from mid-opening FENs (D-04) and a book would corrupt them.
 */
async function resolveBookMove(
  chess: Chess,
  botElo: number,
  policy: MaiaQueue['policy'],
): Promise<string | null> {
  let prefixSet: ReadonlySet<string>;
  try {
    prefixSet = await loadOpeningPrefixSet();
  } catch (err: unknown) {
    // The static ECO asset failed to load (404 / offline). Honest degradation:
    // report it, leave book for the rest of the game, and just search.
    Sentry.captureException(err, { tags: { source: 'bot-game' } });
    return null;
  }

  // The SAN history MUST come from the live board that has the moves pushed. A
  // `new Chess(fen)` has an EMPTY history, which would make the book treat every
  // position as the start position and match the wrong prefixes — the one
  // silent-failure trap on this path (it still yields legal moves, so nothing
  // would visibly break).
  const moveHistorySan = chess.history();
  // Carries both .san and .lan, so no SAN<->UCI conversion is needed anywhere.
  const legalMoves = chess.moves({ verbose: true });
  const side: Side = chess.turn();

  const rawPolicy = await policy(chess.fen(), botElo, side);

  // Default weighting only (D-06: the BookWeightingFn seam exists for a future
  // persona, which this phase deliberately does not build).
  return selectBookMove(moveHistorySan, legalMoves, prefixSet, rawPolicy, Math.random);
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useBotGame(settings: BotGameSettings): UseBotGameState {
  // ─── Refs ──────────────────────────────────────────────────────────────────

  const chessRef = useRef<Chess>(new Chess());
  const clockBaseRef = useRef<{ white: number; black: number }>(
    freshClockBase(settings.baseSeconds),
  );
  /** Wall-clock anchor for the current turn. Set to the real `Date.now()` by
   * the mount effect below (react-hooks/purity forbids calling `Date.now()`
   * directly as a `useRef` initializer, since that reads impure state during
   * render) — the effect runs before the clock-tick effect's first `tick()`
   * call, so this placeholder value is never actually read. */
  const turnStartedAtRef = useRef<number>(0);
  const pausedAtRef = useRef<number | null>(null);
  /** WR-05: the ply currently displayed, kept in sync with the `viewedPly`
   * state via `updateViewedPly` below — read by `commitMove` (a stable
   * memoized callback that does not depend on `viewedPly` state) to decide
   * whether a bot move should snap the view to live. */
  const viewedPlyRef = useRef(0);
  /** The live game's ply BEFORE the in-flight commit, kept in sync with
   * `moveHistory.length` by the effect below. Read alongside `viewedPlyRef`
   * to compute "was the viewer already at the live position" without
   * `commitMove` depending on `moveHistory` itself. */
  const liveGamePlyRef = useRef(0);
  /** WR-03 idempotency latch — the FIRST outcome wins. `finalizeGame` is
   * called from async continuations (bot-turn resolution) and effects
   * (draw-offer resolution, clock tick) that can run with a stale render
   * closure, so this must be a ref (checked/set synchronously the instant
   * the game ends), not the `outcome` state (whose latest value those
   * callers cannot reliably observe). */
  const outcomeRef = useRef<BotGameOutcome | null>(null);

  /** Assigned below to the real provider bring-up + D-15/D-16 honest-clock,
   * deadline-managed dispatch; called with the fixed BOT_SEARCH_BUDGET
   * whenever it becomes the bot's turn. */
  const runBotTurnRef = useRef<
    ((budget: Omit<SearchBudget, 'elo' | 'policyTemperature'>) => void) | null
  >(null);

  // ─── Providers, abort, draw-accept score, one-shot guards ────────────────

  const poolRef = useRef<WorkerPool | null>(null);
  const queueRef = useRef<MaiaQueue | null>(null);
  /** Fresh per bot turn (RESEARCH.md Anti-Pattern: never one shared controller
   * across turns) — aborted on resign/new-game/unmount/bot-flagged. This is
   * the OUTER signal (D-17): a cancel aborts it, but a D-16 deadline cut
   * never does — that lives entirely on an INNER controller inside
   * `createDeadlineSearch`, invisible here. */
  const abortControllerRef = useRef<AbortController | null>(null);
  /** D-01: the bot's best-effort "how good is my position" score, used only
   * by wouldBotAcceptDraw's near-equal check. Updated best-effort from
   * `pool.grade` after each SEARCHED bot move (D-01's "reuse the grading
   * provider it already has").
   *
   * `null` is a SENTINEL meaning *no eval has been computed yet this game* —
   * it is not a neutral score, and `wouldBotAcceptDraw` refuses on it
   * outright. This ref therefore only ever holds a score the bot actually
   * computed. Do NOT "helpfully" restore a numeric default (169.5): the book
   * runs zero Stockfish evals for its whole window, and a 0.5 default would
   * sit dead-center in DRAW_ACCEPT_SCORE_BAND while the draw gate's endgame
   * condition opens on queens-off ALONE — so the bot would accept a draw in a
   * queens-off book position it never evaluated. (The old comment here claimed
   * the 0.5 default "correctly falls through to the endgame gate rather than
   * ever masking it"; that reasoning was wrong — the default SATISFIES both
   * conditions rather than deferring to either.) */
  const lastRootPracticalScoreRef = useRef<number | null>(null);
  /** D-03 (169.5) ONE-WAY leave-book latch, mirroring `outcomeRef`'s
   * latch-in-a-ref shape. Once the bot leaves book (floor-miss, ply cap, no
   * candidates, degenerate policy, or a failed prefix-set fetch) it searches
   * for the rest of the game. This CANNOT be derived from move history: ECO's
   * 3,641 lines cover nearly every sane early position, so a game can wander
   * back onto a cataloged prefix after the bot has already started searching,
   * and a history-derived check would silently re-enter the book. Reset only
   * in `newGame()`. */
  const hasLeftBookRef = useRef(false);
  /** D-09: the user's low-time sound fires exactly once per game. */
  const hasFiredLowTimeRef = useRef(false);
  /** Pitfall 4 (iOS autoplay unlock) — fires once, from the first user gesture. */
  const hasUnlockedAudioRef = useRef(false);

  // ─── State ─────────────────────────────────────────────────────────────────

  const [moveHistory, setMoveHistory] = useState<string[]>([]);
  const [viewedPly, setViewedPly] = useState(0);
  const [activeColor, setActiveColor] = useState<MoverColor>('white');
  const [whiteClockMs, setWhiteClockMs] = useState(settings.baseSeconds * 1000);
  const [blackClockMs, setBlackClockMs] = useState(settings.baseSeconds * 1000);
  const [outcome, setOutcome] = useState<BotGameOutcome | null>(null);
  const [pgn, setPgn] = useState<string | null>(null);
  const [isBotThinking, setIsBotThinking] = useState(false);
  const [drawOfferPending, setDrawOfferPending] = useState(false);
  /** D-04 throttle counter — initialized at the cooldown value so a draw can
   * be offered from the very start of a fresh game (no prior decline yet). */
  const [movesSinceLastDecline, setMovesSinceLastDecline] = useState(DRAW_OFFER_COOLDOWN_MOVES);

  const liveGamePly = moveHistory.length;

  const position = useMemo(() => fenAtPly(moveHistory, viewedPly), [moveHistory, viewedPly]);

  const canOfferDrawNow = canOfferDrawGate(movesSinceLastDecline);

  // ─── Keep liveGamePlyRef in sync (WR-05) ─────────────────────────────────
  //
  // Runs as a passive effect AFTER each render, so by the time the NEXT
  // commitMove call happens (always triggered by a subsequent user action or
  // the bot-turn effect, both of which run after this effect has flushed),
  // `liveGamePlyRef.current` reflects the live ply BEFORE that next commit —
  // exactly the "prev.length" a setMoveHistory updater would have seen.

  useEffect(() => {
    liveGamePlyRef.current = liveGamePly;
  }, [liveGamePly]);

  /** Sets `viewedPly` state AND keeps `viewedPlyRef` synchronously in sync
   * (WR-05) — every place `viewedPly` changes goes through this. */
  const updateViewedPly = useCallback((ply: number): void => {
    viewedPlyRef.current = ply;
    setViewedPly(ply);
  }, []);

  /**
   * D-20/WR-02: resets the turn anchor to now — and, if a pause is currently
   * in progress (the tab is hidden right now), re-baselines the pause
   * timestamp to the SAME instant. Without the second half, a move
   * committing while the tab is hidden (a bot's think resolving in the
   * background) lets the eventual resume handler shift the fresh anchor by
   * the FULL pre-commit hidden duration, landing it in the future and
   * crediting the next mover phantom time (a negative elapsed reading).
   * Used everywhere the anchor is reset: `commitMove` and `newGame`.
   */
  const resetTurnAnchor = useCallback((): void => {
    const now = Date.now();
    turnStartedAtRef.current = now;
    if (pausedAtRef.current !== null) pausedAtRef.current = now;
  }, []);

  /**
   * D-20/CR-01 (Plan 10 gap closure): the SINGLE pause-aware elapsed-time
   * source for this hook. `pausedAtRef` was written on hide but read only on
   * the resume edge (the visibility effect's `shiftAnchorForPause` call
   * below), so a tick or a bot-commit landing DURING the hidden period
   * charged raw background wall-clock time — the anchor shift is
   * retroactive and cannot help those callers. Every elapsed-time consumer
   * in this hook (the tick's flag check, the bot's committed debit, the
   * user's move debit) MUST call this instead of a raw now-minus-anchor
   * read, so a future call site cannot silently reintroduce the bypass.
   */
  const chargeableElapsedMs = useCallback((): number => {
    return computeChargeableElapsedMs(turnStartedAtRef.current, pausedAtRef.current, Date.now());
  }, []);

  // ─── End-of-game finalization ───────────────────────────────────────────────
  //
  // Sets `outcome` (stopping the clock tick via its outcome guard, see
  // below), computes the finished PGN via botGamePgn's finalizeBotPgn
  // (PLAY-09), and fires the game-end sound (D-09). WR-03: the FIRST outcome
  // wins — every caller (tick timeout, board end-detection, resign,
  // draw-accept) can reach this concurrently or from a stale closure, so the
  // `outcomeRef` latch (not the async `outcome` state) is the single source
  // of truth for "has the game already ended."

  const finalizeGame = useCallback(
    (finished: BotGameOutcome): void => {
      if (outcomeRef.current) return; // WR-03: first outcome wins, no-op after
      outcomeRef.current = finished;
      abortControllerRef.current?.abort();
      setOutcome(finished);
      setIsBotThinking(false);
      const tcStr = toBackendTcStr(settings.baseSeconds, settings.incrementSeconds);
      setPgn(finalizeBotPgn(chessRef.current, finished, tcStr));
      playSound('game-end');
    },
    [settings.baseSeconds, settings.incrementSeconds],
  );

  /**
   * D-15/CR-02 (Plan 10 gap closure): the commit-time flag test. The 100 ms
   * tick was the ONLY flag detector before this gap closure, so whether an
   * overrunning mover actually lost on time was a race — and a D-18
   * node-floor overrun (or a grading call outlasting a tight D-16 deadline)
   * makes an overrun routine, not theoretical, for a low-clock bot. Both
   * move paths (`attemptMove`, `runBotTurn`) MUST call this BEFORE applying
   * the move, and treat a `true` return as "the move must not commit."
   */
  const flagIfOutOfTime = useCallback(
    (mover: MoverColor, debitMs: number): boolean => {
      if (!hasFlaggedOnDebit(clockBaseRef.current[mover], debitMs)) return false;
      clockBaseRef.current[mover] = 0;
      if (mover === 'white') setWhiteClockMs(0);
      else setBlackClockMs(0);
      const winner: MoverColor = mover === 'white' ? 'black' : 'white';
      finalizeGame({ reason: 'timeout', winner });
      return true;
    },
    [finalizeGame],
  );

  // ─── Move commit (shared by the user move path and the bot move path) ────
  //
  // `debitMs` is the wall-clock elapsed time for a user move, or the D-15
  // honest elapsed-time debit for a bot move — the caller decides which;
  // this function only ever applies whatever it's given.

  const commitMove = useCallback(
    (move: Move, mover: MoverColor, debitMs: number): void => {
      const chess = chessRef.current;
      const incrementMs = settings.incrementSeconds * 1000;

      // CR-02 fix: a plain subtraction, no floor-at-zero. By construction
      // both callers (attemptMove, runBotTurn) already call
      // flagIfOutOfTime before reaching this point, so debitMs never
      // exceeds the mover's remaining time here — this value is always
      // strictly positive. The old clamp forgave an overrun and then
      // topped the flagged mover back up to exactly the Fischer increment,
      // an unlabelled duplicate of the never-flag pattern D-15 deleted from
      // chessClock.ts. Callers MUST call flagIfOutOfTime before applying a
      // move; do not reintroduce a floor here.
      const remainingBeforeIncrement = clockBaseRef.current[mover] - debitMs;
      const remainingAfterIncrement = applyIncrementMs(remainingBeforeIncrement, incrementMs);
      clockBaseRef.current[mover] = remainingAfterIncrement;
      if (mover === 'white') setWhiteClockMs(remainingAfterIncrement);
      else setBlackClockMs(remainingAfterIncrement);

      annotateClock(chess, remainingAfterIncrement);

      // WR-05: capture whether the viewer was at the live position BEFORE
      // this commit, via refs (not the render-closure `moveHistory`/
      // `viewedPly` state — this memoized callback does not depend on
      // either and would otherwise read stale values). `setViewedPly` is
      // called AFTER `setMoveHistory`, as its own top-level statement —
      // never from inside the updater — because invoking a state setter
      // from within another setter's updater violates updater purity
      // (React may invoke updaters twice).
      const wasLive = viewedPlyRef.current === liveGamePlyRef.current;
      const newLivePly = liveGamePlyRef.current + 1;

      setMoveHistory((prev) => [...prev, move.san]);
      // D-13: the user's own move can only ever be made from the live
      // position (attemptMove's off-live-position gate), so it always
      // snaps. A bot move committed while the user is reviewing an earlier
      // ply must NOT eject them from scroll-back (WR-05) — snap only if
      // they were already live.
      if (wasLive || mover === settings.userColor) {
        updateViewedPly(newLivePly);
      }

      const end = detectEndCondition(chess);
      if (end) {
        finalizeGame(end);
        return;
      }

      // Sounds (D-09): check takes priority over capture over a plain move —
      // the game-end sound (played by finalizeGame above) already covers the
      // terminal case, so this branch only runs while the game continues.
      if (chess.inCheck()) playSound('check');
      else if (move.captured) playSound('capture');
      else playSound('move');

      const nextColor: MoverColor = mover === 'white' ? 'black' : 'white';
      setActiveColor(nextColor);
      // D-20/WR-02: re-baseline the turn anchor (and, if a pause is
      // currently in progress, the pause baseline too) — see
      // resetTurnAnchor's doc comment for why the two must travel together.
      resetTurnAnchor();
    },
    [settings.incrementSeconds, settings.userColor, finalizeGame, resetTurnAnchor, updateViewedPly],
  );

  // ─── User move (PLAY-03: turn-gate + auto-queen + Fischer increment) ──────

  const attemptMove = useCallback(
    (from: string, to: string): boolean => {
      // Pitfall 4: unlock audio playback from the first real user gesture,
      // regardless of whether this particular attempt turns out legal.
      if (!hasUnlockedAudioRef.current) {
        hasUnlockedAudioRef.current = true;
        unlockAudio();
      }

      if (outcome) return false;
      if (viewedPly !== liveGamePly) return false; // view-only mode (D-13)

      const chess = chessRef.current;
      const mover: MoverColor = chess.turn() === 'w' ? 'white' : 'black';
      if (mover !== settings.userColor) return false; // not the user's turn

      // CR-02: the overrun check MUST run BEFORE chess.move() — a flagged
      // mover's move must never reach chessRef.current or the exported PGN.
      const elapsedMs = chargeableElapsedMs();
      if (flagIfOutOfTime(mover, elapsedMs)) return false;

      let move: Move;
      try {
        move = chess.move({ from, to, promotion: 'q' }); // auto-queen (Pitfall 2)
      } catch {
        return false;
      }
      if (!move) return false;

      commitMove(move, mover, elapsedMs);
      // D-04: only the user's OWN moves count toward the draw-offer cooldown.
      setMovesSinceLastDecline((prev) => prev + 1);
      return true;
    },
    [
      outcome,
      viewedPly,
      liveGamePly,
      settings.userColor,
      chargeableElapsedMs,
      flagIfOutOfTime,
      commitMove,
    ],
  );

  // ─── View-only ply navigation (D-13) ───────────────────────────────────────

  const viewPly = useCallback(
    (ply: number): void => {
      updateViewedPly(Math.max(0, Math.min(ply, liveGamePly)));
    },
    [liveGamePly, updateViewedPly],
  );

  const returnToLive = useCallback((): void => {
    updateViewedPly(liveGamePly);
  }, [liveGamePly, updateViewedPly]);

  // ─── Resign / draw (D-01..D-04 — the bot never resigns/offers, D-02/D-03) ─

  const resign = useCallback((): void => {
    if (outcome) return;
    // D-04: a CONFIRMED resign (the confirm UI is a later plan's job) — this
    // is the post-confirm action, aborting any in-flight bot think.
    const winner: MoverColor = settings.userColor === 'white' ? 'black' : 'white';
    finalizeGame({ reason: 'resignation', winner });
  }, [outcome, settings.userColor, finalizeGame]);

  /** D-01: resolves the ALREADY-set `drawOfferPending` flag — accept ends the
   * game, decline resets the cooldown counter and fires the notification
   * sound. Split from `offerDraw` so `drawOfferPending` is real, observable
   * state (not collapsed into the same synchronous call). WR-03: this effect
   * can fire AFTER the game has already ended (e.g. a bot move delivering
   * mate while the offer was pending) — it must bail via `outcomeRef` (not
   * the `outcome` state, which this effect's own closure could hold stale)
   * before ever evaluating `wouldBotAcceptDraw`, so a late accept can never
   * overwrite the real outcome. */
  useEffect(() => {
    if (!drawOfferPending) return;
    if (outcomeRef.current) {
      setDrawOfferPending(false);
      return;
    }
    // Sentinel contract (169.5): a `null` score means the bot has evaluated
    // nothing this game (e.g. it is still in book, which runs zero Stockfish
    // evals) and `wouldBotAcceptDraw` refuses outright — the bot never accepts
    // a draw off an evaluation it did not run.
    const accepts = wouldBotAcceptDraw(lastRootPracticalScoreRef.current, chessRef.current);
    if (accepts) {
      finalizeGame({ reason: 'draw', drawReason: 'agreement' });
    } else {
      setMovesSinceLastDecline(0);
      playSound('draw-declined');
    }
    setDrawOfferPending(false);
  }, [drawOfferPending, finalizeGame]);

  const offerDraw = useCallback((): void => {
    if (outcome) return;
    if (!canOfferDrawNow) return; // D-04 throttle gates the button itself
    setDrawOfferPending(true);
  }, [outcome, canOfferDrawNow]);

  // ─── New game ───────────────────────────────────────────────────────────────

  const newGame = useCallback((): void => {
    abortControllerRef.current?.abort();
    chessRef.current = new Chess();
    clockBaseRef.current = freshClockBase(settings.baseSeconds);
    pausedAtRef.current = null;
    resetTurnAnchor();
    outcomeRef.current = null;
    // Back to the not-yet-evaluated sentinel — a fresh game has evaluated nothing.
    lastRootPracticalScoreRef.current = null;
    // SC4: a fresh game re-enters the book.
    hasLeftBookRef.current = false;
    hasFiredLowTimeRef.current = false;
    setMoveHistory([]);
    updateViewedPly(0);
    setActiveColor('white');
    setWhiteClockMs(clockBaseRef.current.white);
    setBlackClockMs(clockBaseRef.current.black);
    setOutcome(null);
    setPgn(null);
    setIsBotThinking(false);
    setDrawOfferPending(false);
    setMovesSinceLastDecline(DRAW_OFFER_COOLDOWN_MOVES);
  }, [settings.baseSeconds, resetTurnAnchor, updateViewedPly]);

  // ─── Turn-anchor mount init ─────────────────────────────────────────────────
  //
  // Sets the real wall-clock anchor once on mount (react-hooks/purity forbids
  // `Date.now()` inside the `turnStartedAtRef` useRef initializer above).
  // Declared BEFORE the clock-tick effect so it runs first within the same
  // commit — React runs passive effects in declaration order.

  useEffect(() => {
    const now = Date.now();
    turnStartedAtRef.current = now;
    // CR-01 (bug fix): `visibilitychange` fires only on a TRANSITION, so a game
    // mounting into an ALREADY-hidden tab (background-tab open, session restore,
    // prerender, bfcache) never ran the hidden branch below — `pausedAtRef` stayed
    // null, `chargeableElapsedMs` degraded to a raw now-minus-anchor read, and the
    // tick flagged the active side on pure background wall-clock time. The resume
    // handler could not undo it either: its `!== null` guard fails, so the anchor
    // shift never runs and the overcharge is permanent. Seed the pause from the
    // INITIAL visibility state.
    if (document.visibilityState === 'hidden') pausedAtRef.current = now;
  }, []);

  // ─── Clock tick (PLAY-04: wall-clock delta, never accumulated ticks) ──────
  //
  // The ACTIVE side's displayed clock is recomputed from the pause-aware
  // chargeableElapsedMs helper on every tick — flag-on-time (the only
  // loop-owned end condition) fires here.

  useEffect(() => {
    if (outcome) return;

    const tick = (): void => {
      const elapsed = chargeableElapsedMs();
      // Display-only floor (never applied to clockBaseRef.current itself) —
      // the tick's own remaining<=0 check below is what actually ends the
      // game; this only keeps the shown value from going negative for one
      // render.
      const rawRemaining = clockBaseRef.current[activeColor] - elapsed;
      const remaining = Math.max(0, rawRemaining);

      if (activeColor === 'white') setWhiteClockMs(remaining);
      else setBlackClockMs(remaining);

      // D-09: the user's low-time sound fires exactly once at the threshold
      // crossing, on the user's own clock only — not a repeating tick.
      if (
        activeColor === settings.userColor &&
        !hasFiredLowTimeRef.current &&
        isLowTime(remaining)
      ) {
        hasFiredLowTimeRef.current = true;
        playSound('low-time');
      }

      if (remaining <= 0) {
        // D-15/amended SC1: this check is INTENTIONALLY ungated by color —
        // the bot can now lose on time exactly like the user. Do NOT add an
        // `activeColor === settings.userColor` guard here.
        // 169-VERIFICATION.md suggested exactly that fix under the
        // superseded never-flag model; 169-CONTEXT.md's "Decision
        // Amendments" section explicitly reverses it (D-15/D-16/D-18). A bot
        // whose deadline-cut think still outlasts its remaining clock flags,
        // and the user wins — that is intended behavior, not a bug.
        const winner: MoverColor = activeColor === 'white' ? 'black' : 'white';
        finalizeGame({ reason: 'timeout', winner });
      }
    };

    tick();
    const id = setInterval(tick, CLOCK_TICK_INTERVAL_MS);
    return () => clearInterval(id);
  }, [activeColor, outcome, finalizeGame, settings.userColor, chargeableElapsedMs]);

  // ─── Hidden-tab pause (PLAY-04, matters most during the bot's think) ──────

  useEffect(() => {
    const handleVisibility = (): void => {
      if (document.visibilityState === 'hidden') {
        // Idempotent: a duplicate 'hidden' event (Safari fires visibilitychange
        // alongside pagehide, and again on bfcache restore) must not re-baseline
        // an in-progress pause forward — that would silently charge the interval
        // between the two events.
        if (pausedAtRef.current === null) pausedAtRef.current = Date.now();
      } else if (pausedAtRef.current !== null) {
        const pausedForMs = Date.now() - pausedAtRef.current;
        turnStartedAtRef.current = shiftAnchorForPause(turnStartedAtRef.current, pausedForMs);
        pausedAtRef.current = null;
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  // ─── Provider bring-up (Pattern 1 — once per game, NOT re-run per FEN) ────

  useEffect(() => {
    const pool = createWorkerPool();
    const queue = createMaiaQueue();
    poolRef.current = pool;
    queueRef.current = queue;
    // SC5 (169.5): spawn both engines NOW, during the book window, so the
    // book's near-instant plies pay the worker-spawn cost instead of the first
    // move the bot actually has to search — which, under the book, is the first
    // move OUT of book and exactly the one we least want cold. Both are
    // idempotent (they forward to each provider's own lazy `ensureSpawned()`),
    // so a re-running effect cannot spawn a second pool. NB: `pool.grade(fen,
    // [])` would NOT work here — it returns on the WR-05 empty-candidates guard
    // before spawning anything.
    pool.warm();
    queue.warm();
    // Get the ECO asset fetch in flight before the bot's first turn; the book
    // helper awaits the same cached promise. Fire-and-forget: a rejection is
    // handled (and reported) there, on the path that actually needs it.
    void loadOpeningPrefixSet().catch(() => {});
    return () => {
      pool.terminate();
      queue.terminate();
      poolRef.current = null;
      queueRef.current = null;
    };
  }, []);

  // ─── Bot turn dispatch (D-16: per-move think deadline via deps.search;
  // D-03/D-16 reveal-delay floor clamped to the same deadline, run via
  // Promise.all alongside the search — never Promise.race, Pattern 3) ───────

  const runBotTurn = useCallback(
    (budget: Omit<SearchBudget, 'elo' | 'policyTemperature'>): void => {
      const pool = poolRef.current;
      const queue = queueRef.current;
      if (!pool || !queue) return;

      // Pattern 2: a fresh AbortController every turn, never one shared
      // across turns.
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const chess = chessRef.current;
      const fen = chess.fen();
      const mover: MoverColor = chess.turn() === 'w' ? 'white' : 'black';

      // D-16: the per-move think deadline, derived from the bot's OWN
      // remaining clock at dispatch time (its clock does not move again
      // until this turn resolves). This deadline reaches the engine through
      // exactly ONE seam: `deps.search` (buildBotMoveDeps), the injectable
      // SearchRunner Phase 166 D-08 defined for exactly this purpose.
      const incrementMs = settings.incrementSeconds * 1000;
      const deadlineMs = computeThinkDeadlineMs(clockBaseRef.current[mover], incrementMs);
      const deps = buildBotMoveDeps(deadlineMs, queue, pool);

      // Pitfall 3: isBotThinking is derived from this real in-flight promise,
      // never a fixed-duration animation — a 12s contested think genuinely
      // shows 12s of thinking, not a premature "done" flicker.
      setIsBotThinking(true);

      void (async () => {
        // 169.5: while in book, the bot answers from the ECO book — ONE Maia
        // policy eval, ZERO Stockfish searches, `selectBotMove` never called. A
        // `null` from the book (floor-miss, ply cap, no candidates, degenerate
        // policy, or a failed asset fetch) is its leave-book signal: the ONE-WAY
        // latch fires HERE, at the single decline point, and the bot searches
        // for the rest of the game.
        const resolveMove = async (): Promise<{ uci: string; fromBook: boolean }> => {
          if (!hasLeftBookRef.current) {
            const bookUci = await resolveBookMove(chess, settings.botElo, queue.policy);
            if (bookUci !== null) return { uci: bookUci, fromBook: true };
            hasLeftBookRef.current = true;
          }
          const searchedUci = await selectBotMove(
            fen,
            { elo: settings.botElo, blend: settings.blend, budget },
            deps,
            controller.signal,
          );
          return { uci: searchedUci, fromBook: false };
        };

        let resolved: { uci: string; fromBook: boolean };
        try {
          [resolved] = await Promise.all([
            resolveMove(),
            // The reveal delay is still a floor run alongside the search — but
            // clamped to the SAME deadline (D-16) so it can never itself push a
            // low-clock bot past its own deadline. It is also what puts a
            // near-instant BOOK move inside the reveal band instead of snapping
            // back at zero latency.
            delay(Math.min(computeRevealDelayMs(Math.random), deadlineMs)),
          ]);
        } catch (err: unknown) {
          // D-17: `controller.signal` is the OUTER signal. A D-16 deadline
          // cut never reaches this catch — `createDeadlineSearch` isolates
          // it on an INNER controller, and `selectBotMove` resolves normally
          // with its best-so-far move for that case. So
          // `controller.signal.aborted` here means exactly one thing: a
          // CANCEL (resign / new game / unmount / bot flagged) — discard the
          // turn, as before.
          if (controller.signal.aborted) return;
          Sentry.captureException(err, { tags: { source: 'bot-game' } });
          setIsBotThinking(false);
          return;
        }

        // Same two-signal contract as the catch above — a cancel that lands
        // exactly as the deadline-cut search resolves still discards the turn.
        if (controller.signal.aborted) return;

        const { uci, fromBook } = resolved;

        // D-15/D-20/CR-01 (Plan 10 gap closure): the bot's debit is the
        // honest, real elapsed wall-clock time of this turn (search + reveal
        // delay), read through the pause-aware `chargeableElapsedMs` helper
        // — never a raw now-minus-anchor read, which would charge any
        // hidden background time the search ran through (the common case,
        // since Web Workers keep executing when backgrounded).
        const debitMs = chargeableElapsedMs();

        // CR-02: the overrun check MUST run BEFORE chess.move() — a flagged
        // bot's move must never reach chessRef.current or the exported PGN,
        // and no best-effort grade should run for a discarded turn.
        // `finalizeGame` (called inside `flagIfOutOfTime`) already aborts
        // the controller and clears `isBotThinking`, so no extra
        // bookkeeping is needed here.
        if (flagIfOutOfTime(mover, debitMs)) return;

        const from = uci.slice(0, 2);
        const to = uci.slice(2, 4);
        const promotion = uci.length > 4 ? uci.slice(4, 5) : 'q';

        let move: Move;
        try {
          move = chess.move({ from, to, promotion });
        } catch (err: unknown) {
          // selectBotMove is trusted to return a legal move for `fen` — a
          // mismatch here is a genuine bug, not an expected abort.
          Sentry.captureException(err, { tags: { source: 'bot-game' } });
          setIsBotThinking(false);
          return;
        }
        if (!move) {
          setIsBotThinking(false);
          return;
        }

        setIsBotThinking(false);
        // A book move is CHEAP, not FREE: it reaches this same commit through
        // the same chargeableElapsedMs() -> flagIfOutOfTime() -> commitMove()
        // pipeline as a searched move (169 D-15/D-16/D-20), so it is debited its
        // real elapsed time (the Maia eval + the reveal delay), it gets the
        // Fischer increment, and a bot already down to nothing can still flag on
        // it. There is deliberately no second commit path and no untimed book
        // bypass.
        commitMove(move, mover, debitMs);

        // D-01: best-effort refresh of the draw-accept score from the position
        // the bot's own move reached (reuses the grading provider it already
        // has) — never blocks the move commit above.
        //
        // 169.5: SUPPRESSED on book plies, so SC1's "no Stockfish evals while in
        // book" holds literally. `lastRootPracticalScoreRef` therefore stays at
        // its not-yet-evaluated `null` sentinel for the whole book window —
        // which is safe ONLY because `wouldBotAcceptDraw` refuses on that
        // sentinel. Do NOT "helpfully" restore a numeric default to that ref: a
        // book line can legally reach a QUEENS-OFF position inside the ply cap
        // (openings.tsv:1065 trades queens by ply 9) and the draw gate's endgame
        // condition opens on queens-off ALONE — so a 0.5 default would make the
        // bot accept a draw in a position it never evaluated.
        if (fromBook) return;
        pool
          .grade(fen, [uci])
          .then((gradeMap) => {
            const grade = gradeMap.get(uci);
            if (grade) {
              lastRootPracticalScoreRef.current = evalToExpectedScore(
                grade.evalCp,
                grade.evalMate,
                mover,
              );
            }
          })
          .catch(() => {
            // Best-effort only — a failed grade leaves the prior score in place.
          });
      })();
    },
    [
      settings.botElo,
      settings.blend,
      settings.incrementSeconds,
      chargeableElapsedMs,
      flagIfOutOfTime,
      commitMove,
    ],
  );

  useEffect(() => {
    runBotTurnRef.current = runBotTurn;
  }, [runBotTurn]);

  // ─── Abort-on-unmount (Pattern 2) ───────────────────────────────────────────

  useEffect(() => {
    return () => abortControllerRef.current?.abort();
  }, []);

  // ─── Bot-turn trigger ────────────────────────────────────────────────────────
  //
  // Depends on the `moveHistory` array REFERENCE (not just its length) so a
  // newGame() reset (same activeColor value as a just-finished game can
  // coincidentally have) still re-triggers via the fresh empty-array identity.

  useEffect(() => {
    if (outcome) return;
    if (activeColor === settings.userColor) return;
    runBotTurnRef.current?.(BOT_SEARCH_BUDGET);
  }, [moveHistory, activeColor, outcome, settings.userColor]);

  // ─── Return ────────────────────────────────────────────────────────────────

  return {
    position,
    moveHistory,
    liveGamePly,
    viewedPly,
    isBotThinking,
    whiteClockMs,
    blackClockMs,
    activeColor,
    outcome,
    pgn,
    drawOfferPending,
    canOfferDraw: canOfferDrawNow,
    attemptMove,
    viewPly,
    returnToLive,
    resign,
    offerDraw,
    newGame,
  };
}

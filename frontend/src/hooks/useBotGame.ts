/**
 * useBotGame — the orchestrating game-loop hook for clocked bot play. Composes
 * the pure modules (chessClock, botGameEnd, botDrawGate, botGamePgn, sounds)
 * with the frozen `selectBotMove` engine core and chess.js. This is pure
 * orchestration — chess.js owns rules/legality/end-conditions,
 * `selectBotMove` owns move selection, and the pure modules own
 * timing/end-detection/draw-gate/PGN/sound. This hook and its sub-hooks wire
 * them and expose the stable state+callbacks contract the resume flow
 * (localStorage) and the setup screen + store-on-finish build on.
 *
 * Where each piece lives: the clock (`clockBaseRef`, `chargeableElapsedMs`,
 * `flagIfOutOfTime`) in `useBotGameClock`; `commitMove`/`attemptMove`/
 * `viewPly`/`resign` in `useBotGameMoves`; `runBotTurn` and the engine
 * providers in `useBotGameEngineDispatch`; `finalizeGame`/`buildSnapshot` in
 * `useBotGameSnapshot`; the draw-offer state in `useBotGameDrawOffer`; the
 * speech-bubble line in `useBotGameVoice`. This file keeps the shared state,
 * `newGame`, the hidden-tab snapshot write and the bot-turn trigger.
 *
 * `viewedPly` and `liveGamePly` are modeled as two SEPARATE numbers (two
 * independent pieces of viewing-vs-live state) — `liveGamePly` is always
 * `moveHistory.length`; `viewedPly` is the ply the board currently displays
 * (view-only when it differs from `liveGamePly`).
 *
 * CLOCK MODEL: the bot's clock is HONEST. On commit it is debited exactly the
 * real wall-clock time its turn consumed (search + reveal delay), plus the
 * Fischer increment — the same rule the user's clock obeys. There is no
 * synthetic fraction-of-remaining debit and no never-flag clamp in the
 * bot-game hooks; the bot CAN lose on time, and that invariant is ENFORCED at
 * the commit site — `hasFlaggedOnDebit` (chessClock.ts), called via the
 * `flagIfOutOfTime` helper before the move is applied in both `attemptMove`
 * and `runBotTurn` — not merely absent from the code. Because a fixed search
 * budget under an honest clock is degenerate (the bot would bleed net time
 * every move), the bot manages its own pace via a per-move think deadline
 * (`computeThinkDeadlineMs`, chessClock.ts) injected into `selectBotMove`
 * through the `deps.search` seam (`createDeadlineSearch`, deadlineSearch.ts)
 * — a deadline cut returns the search's best-so-far move; it never discards
 * the turn. Only a genuine CANCEL (resign / new game / unmount / bot flagged)
 * discards a turn. This means the bot's calibrated ELO (measured at the full
 * node budget) holds only when it is NOT low on its own clock — a
 * deadline-cut bot in time trouble plays materially weaker than advertised,
 * by design (humans get worse in time trouble too).
 *
 * Hidden-tab hardening: every elapsed-time consumer — the clock tick's flag
 * check, the bot's committed debit, and the user's move debit — reads through
 * the ONE pause-aware `chargeableElapsedMs` helper (wrapping chessClock.ts's
 * `computeChargeableElapsedMs`), so a hidden interval reaches neither the
 * tick's flag check nor the committed debit, for either side. The
 * anchor-reset helper (`resetTurnAnchor`) re-baselines an in-progress pause
 * alongside the turn anchor on every commit, so a move committing while the
 * tab is hidden can never produce a future-dated anchor on resume.
 *
 * Finalize idempotency and scroll-back preservation: `finalizeGame` is
 * latched by `outcomeRef` — the first outcome wins, and every caller
 * (including the async draw-resolution effect, which can run after the game
 * has already ended) checks it before doing anything. `commitMove` snaps
 * `viewedPly` to the live position only when the viewer was already live (or
 * the mover is the user, who can only move from the live position anyway) —
 * a bot move does not eject the user from scroll-back.
 *
 * RESUME SEAM + LIVE GATE: an optional `resume` argument lazily seeds every
 * ref/state value below from a `BotGameSnapshot` instead of a fresh-game
 * default — ONE hook, ONE game loop, no second restore path. A resumed game
 * mounts with `live: false`: the provider bring-up effect (pool/queue warm)
 * still fires unconditionally, but the turn-anchor, clock-tick, and
 * bot-turn-trigger effects wait for the caller to call `confirmLive()` (from
 * the resume gate's Resume button) before any clock runs or search starts —
 * nobody pays for the engine cold-start, and no away-time is billed.
 * `gameUuid` is minted once at game start, carried through a resume
 * unchanged, and re-minted ONLY by `newGame()` — this is what keeps the
 * server's `uq_games_user_platform_game_id` idempotency reachable across a
 * resume.
 *
 * PERSISTENCE: this hook and its sub-hooks own every localStorage write for
 * the in-progress snapshot and the finished-game pending-store queue, at
 * exactly FOUR call sites: (1) `commitMove` (useBotGameMoves) writes a fresh
 * snapshot after every committed move (no fold — the base is already
 * settled); (2) a dedicated tab-hide/`pagehide` effect in this file writes a
 * snapshot with the clock fold applied (bills the user's in-turn think time,
 * refunds the bot's interrupted one); (3) `finalizeGame` (useBotGameSnapshot)
 * enqueues the finished game to `flawchess_bot_pending_store` and clears the
 * in-progress snapshot; (4) `newGame` clears the in-progress snapshot only.
 * Call site (3) is the ONLY `enqueuePendingStore` call site in the codebase —
 * this is what makes "an abandoned game leaves no server trace" STRUCTURAL:
 * the POST that eventually drains the queue can only ever be fed by a
 * FINISHED game, because nothing else ever writes into that queue.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Chess } from 'chess.js';

import type { MoverColor } from '@/lib/liveFlaw';
import { foldClockBasesForSnapshot } from '@/lib/chessClock';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import { canOfferDraw as canOfferDrawGate, DRAW_OFFER_COOLDOWN_MOVES } from '@/lib/botDrawGate';
import type { BotStyleParams } from '@/lib/engine/botStyle';
import type { PersonaId } from '@/lib/personas/personaRegistry';
import { engineGateRequired } from '@/lib/engine/engineAssetProgress';
import {
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_CONCURRENCY,
  FLAWCHESS_BOT_STOP_RULE,
  FLAWCHESS_DISPATCH_MODE,
} from '@/lib/engine/botBudget';
import type { SearchBudget } from '@/lib/engine/types';
import { restoreChess, writeSnapshot, clearSnapshot, type BotGameSnapshot } from '@/lib/botGameSnapshot';
import { useBotGameClock } from '@/hooks/useBotGameClock';
import { useBotGameDrawOffer } from '@/hooks/useBotGameDrawOffer';
import { useBotGameEngineDispatch } from '@/hooks/useBotGameEngineDispatch';
import { useBotGameSnapshot } from '@/hooks/useBotGameSnapshot';
import { useBotGameMoves } from '@/hooks/useBotGameMoves';
import { useBotGameVoice } from '@/hooks/useBotGameVoice';
import type { BotLineKey } from '@/lib/botGameCopy';

// ─── Named constants ─────────────────────────────────────────────────────────

/**
 * The bot's fixed NODE budget — assembled once here from `botBudget.ts`'s
 * shipped constants (imported directly, never via `useFlawChessEngine.ts`'s
 * re-export). This is the search's upper bound, unrelated to and unchanged by
 * the think deadline — the deadline can CUT a search short of this budget in
 * time trouble, it never raises it. `elo`/`policyTemperature` are supplied
 * per-call by `selectBotMove` itself, never here.
 */
const BOT_SEARCH_BUDGET: Omit<SearchBudget, 'elo' | 'policyTemperature'> = {
  maxNodes: FLAWCHESS_BOT_MAX_NODES,
  maxPlies: FLAWCHESS_BOT_MAX_PLIES,
  concurrency: FLAWCHESS_BOT_CONCURRENCY,
  stopRule: FLAWCHESS_BOT_STOP_RULE,
  // The shared dispatch-mode constant ('continuous'; the same constant feeds
  // the analysis budget).
  dispatchMode: FLAWCHESS_DISPATCH_MODE,
};

// ─── Types ───────────────────────────────────────────────────────────────────

/** The bot's own play settings for one game. */
export interface BotGameSettings {
  /** The bot's own ELO, its only strength input (symmetric, never
   * player-derived) — see selectBotMove.ts's module header. */
  botElo: number;
  /**
   * REGIME DISPATCH, not a mix (selectBotMove's three-way blend): `0` runs a
   * single Maia policy call with no MCTS search and is therefore EXEMPT from
   * the think deadline in chessClock.ts (the deadline is computed and built
   * unconditionally, but never consulted at this setting); anything `> 0`
   * runs the full search under that deadline.
   * Pinned by `selectBotMove.test.ts`'s blend=0 "deps.search zero times" test.
   */
  blend: number;
  /** Starting clock time for both sides, in seconds. */
  baseSeconds: number;
  /** Fischer increment applied to the mover after each move, in seconds. */
  incrementSeconds: number;
  /** Which color the human player is playing. */
  userColor: MoverColor;
  /**
   * Optional bot-only style layer. The SAME bare `BotStyleParams` object
   * `selectBotMove.ts`'s `BotSettings.style` accepts — never player-derived,
   * never a style NAME. `undefined` runs the unstyled code path everywhere it
   * is consumed: the default `maiaPolicyWeighting` book, the standard draw
   * gate (contempt 0), and the bot never resigns. Threaded into three seams
   * below: the book-weighting call (`resolveBookMove`), the draw-accept
   * contempt shift, and the resign-hysteresis check — plus `selectBotMove`'s
   * own `style`-gated regime hooks, reached via the same object at the
   * `runBotTurn` search call site.
   */
  style?: BotStyleParams;
  /**
   * Optional persona identity. Mirrors `style?`'s optional-everywhere
   * contract exactly: `undefined` means a Custom-mode game (the Custom setup
   * flow never sets this field) and runs the persona-less code path
   * everywhere it is consumed. Only the id STRING is ever carried here — the
   * full `Persona` object (and by extension its resolved `style` bundle) is
   * looked up ONCE, on demand, via `PERSONA_REGISTRY`/`personaForId`
   * (`@/lib/personas/personaRegistry`) wherever a component needs it (e.g.
   * the draw-offer banner, a persona badge) — never re-serialized or spread
   * into this settings object or the snapshot. `personaId` is an INDEPENDENT
   * field, never derived from `settings.style` via a reverse lookup: 6
   * personas share one style bundle by reference, so a style-to-persona
   * reverse lookup cannot disambiguate which rung produced it.
   */
  personaId?: PersonaId;
}

/** The full state + callback contract this hook exposes. Serializable aside
 * from callback identities — the snapshot writers read the state fields
 * directly. */
export interface UseBotGameState {
  /** FEN of the position currently DISPLAYED (viewedPly), not necessarily live. */
  position: string;
  /** The from/to squares of the move leading to the DISPLAYED ply (viewedPly), or null at
   * ply 0. Derived from viewedPly — NOT the live tail — so scrubbing the move list moves the
   * highlight with it instead of leaving a stale one on the live position. */
  lastMove: { from: string; to: string } | null;
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
  /** Whether the "Offer draw" button is currently clickable (cooldown throttle). */
  canOfferDraw: boolean;
  /**
   * True while the BOT has a live OUTGOING draw offer — the counterpart to
   * `drawOfferPending`, which tracks the user-initiated direction. Computed at
   * the same `pool.grade().then()` seam as `wouldBotResign`, gated by
   * `settings.style`. Auto-clears on the user's next committed move (the
   * offer expires on the user's next move).
   */
  botDrawOfferPending: boolean;
  /** Accepts the bot's own outgoing draw offer — ends the game as an agreed draw. */
  acceptBotDraw: () => void;
  /** Dismisses the bot's own outgoing draw offer without ending the game;
   * the own-offer cooldown already restarted when the offer was raised. */
  declineBotDraw: () => void;
  /** Stable per-game identifier: minted once via `crypto.randomUUID()` at
   * game start, carried unchanged through a resume, and re-minted ONLY by
   * `newGame()`. This is what keeps the server's
   * `uq_games_user_platform_game_id` idempotency reachable across a resume. */
  gameUuid: string;
  /** False only for a resumed-but-unconfirmed game, or a fresh game whose
   * engine assets are still a cache-miss — the turn-anchor, clock-tick, and
   * bot-turn-trigger effects wait for `confirmLive()` before running. True
   * from mount for a fresh (`resume === undefined`) game with its engine
   * assets cached. */
  live: boolean;
  /** Confirms a game is ready to become live — call from the resume gate's
   * Resume button or the engine-ready gate's Start button. No-op (already
   * true) for a game that is already live. */
  confirmLive: () => void;
  /**
   * The manual-retry seam behind `EngineReadyGate`'s Retry
   * button. After a terminal download failure the shared Maia worker was
   * dropped by `maiaWorkerHost` (see `failAllLeasesAndDropWorker`), so
   * re-triggering `warm()` here re-enters the SAME self-heal path the
   * bring-up effect in useBotGameEngineDispatch already uses:
   * `queue.warm()`/`pool.warm()` forward to `ensureLease()`/`ensureSpawned()`,
   * which lazily spawns a fresh worker. `pool.warm()` is a no-op when the
   * pool is already spawned — the Stockfish pool self-heals through its own
   * `replaceDeadSlot()` and needs no explicit retry call here; it is included
   * anyway because every persona needs both assets.
   */
  retryEngineWarm: () => void;
  /** Attempt a user move; returns false (board snaps back) if illegal, off-turn, or off-live-position. */
  attemptMove: (from: string, to: string) => boolean;
  /** View a historical ply (board becomes read-only until returnToLive()). */
  viewPly: (ply: number) => void;
  /** Snap the viewed ply back to the live game position. */
  returnToLive: () => void;
  /** Confirmed resignation — ends the game with the user losing. */
  resign: () => void;
  /** Offer a draw to the bot, subject to the cooldown throttle. */
  offerDraw: () => void;
  /** Reset to a fresh game with the same settings. */
  newGame: () => void;
  /** The in-game speech bubble's current line key, or `null` for an empty
   * (but still reserved-height) slot. A line is shown only right after the
   * bot's own move and about board-truth already cashed in; it clears the
   * instant the player commits a move, never on a timer. */
  botLine: BotLineKey | null;
}

// ─── Pure helpers ────────────────────────────────────────────────────────────

/** Replays SAN moves [0, ply) on a fresh board to compute the FEN at that ply,
 * along with the from/to squares of the move that produced it (or `null` at
 * ply 0). Mirrors useChessGame.ts's computeInitialChessState replay loop. */
function replayToPly(
  moveHistory: string[],
  ply: number,
): { fen: string; lastMove: { from: string; to: string } | null } {
  const chess = new Chess();
  let lastMove: { from: string; to: string } | null = null;
  // chess.js 1.4 move() throws on illegal SAN, and moveHistory is restored
  // from localStorage (the resume path), so a stale or corrupted payload would
  // crash the Bots page on mount. Stop at the last legal ply and return that
  // position.
  for (let i = 0; i < ply; i++) {
    try {
      // safe: loop bound ensures i < ply <= moveHistory.length
      const move = chess.move(moveHistory[i]!);
      lastMove = { from: move.from, to: move.to };
    } catch {
      break;
    }
  }
  return { fen: chess.fen(), lastMove };
}

/**
 * The SINGLE snapshot->board replay call site. Several of
 * the hook's lazy initializers need the restored board's `Chess` instance
 * and its `history()` — calling `restoreChess` from each one separately
 * would build several distinct boards for one resume. Callers cache this
 * result once per mount (see the `restoredRef` lazy-ref pattern below) so a
 * resume replays the PGN exactly once, not once per re-render.
 */
function initFromResume(resume: BotGameSnapshot | undefined): { chess: Chess; history: string[] } {
  if (resume === undefined) return { chess: new Chess(), history: [] };
  const chess = restoreChess(resume.pgn);
  return { chess, history: chess.history() };
}

// ─── Hook ────────────────────────────────────────────────────────────────────

/**
 * @param settings The bot's own play settings for this game.
 * @param resume An optional snapshot to restore from — the ONE resume seam
 *   into this hook's game loop. `undefined` for a fresh game.
 * @param ownerKey The localStorage owner scope (the user's email, or null
 *   for anon) — see botGameSnapshot.ts. Threaded through to every
 *   persistence call site: the every-move snapshot write, the
 *   tab-hide/pagehide fold write, the finished-game enqueue, and the
 *   new-game snapshot clear.
 */
export function useBotGame(
  settings: BotGameSettings,
  resume?: BotGameSnapshot,
  ownerKey?: string | null,
): UseBotGameState {
  // ─── Resume seam: replay the snapshot's PGN exactly ONCE per mount ───────
  //
  // `initFromResume` builds a Chess board (and its history()) from the
  // snapshot's PGN — expensive enough (full PGN replay) that it must not run
  // on every re-render (this hook re-renders on every 100ms clock tick). A
  // lazy `useState` initializer (not a manually-cached ref — react-hooks/refs
  // forbids reading `.current` during render, and every seed below IS read
  // during render) computes this exactly once, on the very first render,
  // then every seed below reads the same cached STATE value.

  const [restored] = useState(() => initFromResume(resume));
  const { chess: restoredChess, history: restoredHistory } = restored;
  const restoredLivePly = restoredHistory.length;

  // ─── Refs ──────────────────────────────────────────────────────────────────

  const chessRef = useRef<Chess>(restoredChess);
  /** The live game's ply BEFORE the in-flight commit, kept in sync with
   * `moveHistory.length` by the effect below. Read alongside `viewedPlyRef`
   * to compute "was the viewer already at the live position" without
   * `commitMove` depending on `moveHistory` itself. Seeded on a resume so it
   * is correct before the sync effect below has run for the first time. */
  const liveGamePlyRef = useRef(restoredLivePly);
  /** Idempotency latch — the FIRST outcome wins. `finalizeGame` is
   * called from async continuations (bot-turn resolution) and effects
   * (draw-offer resolution, clock tick) that can run with a stale render
   * closure, so this must be a ref (checked/set synchronously the instant
   * the game ends), not the `outcome` state (whose latest value those
   * callers cannot reliably observe). */
  const outcomeRef = useRef<BotGameOutcome | null>(null);

  // ─── Abort controller ─────────────────────────────────────────────────────

  /** Fresh per bot turn (never one shared controller across turns) — aborted
   * on resign/new-game/unmount/bot-flagged. This is the OUTER signal: a
   * cancel aborts it, but a think-deadline cut never does — that lives
   * entirely on an INNER controller inside `createDeadlineSearch`, invisible
   * here. Owned here (not in useBotGameEngineDispatch) so
   * `finalizeGame`/`newGame` can abort it via plain same-scope `useRef`
   * access — see useBotGameEngineDispatch.ts's file header for why (breaking
   * a circular option dependency on `finalizeGame`). Passed into
   * useBotGameEngineDispatch (and useBotGameSnapshot) as an option. */
  const abortControllerRef = useRef<AbortController | null>(null);

  // ─── State ─────────────────────────────────────────────────────────────────

  const [moveHistory, setMoveHistory] = useState<string[]>(restoredHistory);
  const [viewedPly, setViewedPly] = useState(restoredLivePly);
  const [activeColor, setActiveColor] = useState<MoverColor>(
    restoredLivePly % 2 === 0 ? 'white' : 'black',
  );
  const [outcome, setOutcome] = useState<BotGameOutcome | null>(null);
  const [pgn, setPgn] = useState<string | null>(null);
  const [isBotThinking, setIsBotThinking] = useState(false);
  /** Draw-offer throttle counter — initialized at the cooldown value so a
   * draw can be offered from the very start of a fresh game (no prior decline
   * yet). Seeded from `resume.movesSinceLastDecline` on a resume so a refresh
   * cannot reset the draw-offer cooldown and let it be spammed. */
  const [movesSinceLastDecline, setMovesSinceLastDecline] = useState(
    resume?.movesSinceLastDecline ?? DRAW_OFFER_COOLDOWN_MOVES,
  );
  /** False for a resumed-but-unconfirmed game, OR for a fresh game whose
   * required engine assets (the unconditional maia-model + stockfish-wasm
   * bundle, every persona alike) are still a cache-miss
   * (`engineGateRequired`, evaluated once at mount) — see
   * `UseBotGameState.live`. `confirmLive()` (below) is the SAME single start
   * path both the resume gate's Resume button and the engine-ready gate's
   * Start button call: nobody pays for the engine cold-start, in the resume
   * case or any other. */
  const [live, setLive] = useState(() => resume === undefined && !engineGateRequired());
  /** Minted once at game start, carried unchanged through a resume,
   * re-minted ONLY by `newGame()` — see `UseBotGameState.gameUuid`.
   * State (not a ref) because it is read in the render-phase return value
   * below (react-hooks/refs forbids reading `.current` during render). */
  const [gameUuid, setGameUuid] = useState<string>(() => resume?.gameUuid ?? crypto.randomUUID());

  // ─── Snapshot/finalization sub-hook ───────────────────────────────────────
  //
  // Called FIRST among the sub-hooks — useBotGameClock/useBotGameDrawOffer/
  // useBotGameEngineDispatch all need `finalizeGame` as an option, so this
  // hook's output must exist before any of them are wired. See
  // useBotGameSnapshot.ts's file header for why abortControllerRef/
  // setIsBotThinking/setOutcome/setPgn flow IN as options instead of being
  // owned there.

  const { finalizeGame, buildSnapshot, hasLeftBookRef, hasFiredLowTimeRef, lastRootPracticalScoreRef } =
    useBotGameSnapshot({
      resume,
      chessRef,
      outcomeRef,
      abortControllerRef,
      setIsBotThinking,
      setOutcome,
      setPgn,
      gameUuid,
      ownerKey,
      settings,
    });

  const liveGamePly = moveHistory.length;

  const { fen: position, lastMove } = useMemo(
    () => replayToPly(moveHistory, viewedPly),
    [moveHistory, viewedPly],
  );

  const canOfferDrawNow = canOfferDrawGate(movesSinceLastDecline);

  /** Confirms a game is ready to go live — the resume gate's Resume button
   * and the engine-ready gate's Start button call this. Sets `live`
   * unconditionally true; a no-op re-render for an already-live game. */
  const confirmLive = useCallback((): void => {
    setLive(true);
  }, []);

  // ─── Keep liveGamePlyRef in sync ──────────────────────────────────────────
  //
  // Runs as a passive effect AFTER each render, so by the time the NEXT
  // commitMove call happens (always triggered by a subsequent user action or
  // the bot-turn effect, both of which run after this effect has flushed),
  // `liveGamePlyRef.current` reflects the live ply BEFORE that next commit —
  // exactly the "prev.length" a setMoveHistory updater would have seen.

  useEffect(() => {
    liveGamePlyRef.current = liveGamePly;
  }, [liveGamePly]);

  // ─── Clock sub-hook ─────────────────────────────────────────────────────────
  //
  // Wired immediately after `finalizeGame`, its last dependency:
  // flagIfOutOfTime (internal to useBotGameClock) depends on finalizeGame, so
  // the clock sub-hook cannot be called any earlier than this point.

  const {
    whiteClockMs,
    blackClockMs,
    resetTurnAnchor,
    chargeableElapsedMs,
    flagIfOutOfTime,
    applyMoveDebit,
    resetClock,
    getClockBase,
  } = useBotGameClock({
    resume,
    baseSeconds: settings.baseSeconds,
    userColor: settings.userColor,
    live,
    activeColor,
    outcome,
    hasFiredLowTimeRef,
    finalizeGame,
  });

  // ─── Draw-offer sub-hook ──────────────────────────────────────────────────
  //
  // Wired BEFORE useBotGameEngineDispatch (below) — see
  // useBotGameDrawOffer.ts's file header for why: runBotTurn's grade
  // continuation calls bumpConsecutiveLowScoreTurns/applyDrawOfferUpdate,
  // both returned by this hook.

  const {
    drawOfferPending,
    botDrawOfferPending,
    botDrawOfferPendingRef,
    setBotDrawOfferPending,
    movesSinceLastDeclineRef,
    offerDraw,
    acceptBotDraw,
    declineBotDraw,
    resetDrawOfferState,
    bumpConsecutiveLowScoreTurns,
    applyDrawOfferUpdate,
  } = useBotGameDrawOffer({
    resume,
    outcome,
    outcomeRef,
    canOfferDraw: canOfferDrawNow,
    chessRef,
    lastRootPracticalScoreRef,
    style: settings.style,
    finalizeGame,
    setMovesSinceLastDecline,
    movesSinceLastDecline,
  });

  // buildSnapshot (from useBotGameSnapshot) takes movesSinceLastDecline as a
  // plain call-time argument instead of closing over
  // movesSinceLastDeclineRef — see useBotGameSnapshot.ts's file header for
  // why (breaking a circular hook-call dependency between this hook and
  // useBotGameDrawOffer).

  // ─── Voice sub-hook ───────────────────────────────────────────────────────
  //
  // Wired AFTER useBotGameDrawOffer (feeds it the live `botDrawOfferPending` flag
  // from there — the draw-offer arm and its immediate-fire effect) and
  // BEFORE useBotGameMoves (which needs `onMoveCommitted`) and therefore
  // before useBotGameEngineDispatch (which needs `onBotMoveGraded`).
  // `outcome` (state, above) feeds the terminal arm and its own effect —
  // both the async grade seam AND a game ending with no grade in flight at
  // all (a flag, a resignation, a stalemate).

  const { botLine, onMoveCommitted, onBotMoveGraded } = useBotGameVoice({
    userColor: settings.userColor,
    initialPly: restoredLivePly,
    live,
    botDrawOfferPending,
    outcome,
  });

  // ─── Move-commit sub-hook ─────────────────────────────────────────────────
  //
  // Wired after useBotGameSnapshot/useBotGameClock/useBotGameDrawOffer (all
  // three of whose outputs commitMove needs) and BEFORE
  // useBotGameEngineDispatch (below), which needs commitMove as an option.

  const { updateViewedPly, commitMove, attemptMove, viewPly, returnToLive, resign } = useBotGameMoves({
    chessRef,
    liveGamePlyRef,
    initialViewedPly: restoredLivePly,
    outcomeRef,
    outcome,
    viewedPly,
    liveGamePly,
    live,
    userColor: settings.userColor,
    incrementSeconds: settings.incrementSeconds,
    ownerKey,
    setViewedPly,
    setMoveHistory,
    setActiveColor,
    setMovesSinceLastDecline,
    finalizeGame,
    buildSnapshot,
    applyMoveDebit,
    getClockBase,
    resetTurnAnchor,
    chargeableElapsedMs,
    flagIfOutOfTime,
    botDrawOfferPendingRef,
    setBotDrawOfferPending,
    movesSinceLastDeclineRef,
    onMoveCommitted,
  });

  // ─── New game ───────────────────────────────────────────────────────────────

  const newGame = useCallback((): void => {
    abortControllerRef.current?.abort();
    chessRef.current = new Chess();
    // resetClock() (useBotGameClock) resets the clock bases, any in-progress
    // pause and the turn anchor in one call.
    resetClock();
    outcomeRef.current = null;
    // Back to the not-yet-evaluated sentinel — a fresh game has evaluated nothing.
    lastRootPracticalScoreRef.current = null;
    // resetDrawOfferState() (useBotGameDrawOffer) resets the resign-hysteresis
    // counter, the bot's outgoing offer, the own-offer cooldown and the
    // pending flag in one call.
    resetDrawOfferState();
    // A fresh game re-enters the book.
    hasLeftBookRef.current = false;
    hasFiredLowTimeRef.current = false;
    // A new game is a new game — reusing the prior uuid would make the
    // server silently treat it as a duplicate of the game just discarded.
    setGameUuid(crypto.randomUUID());
    setMoveHistory([]);
    updateViewedPly(0);
    setActiveColor('white');
    setOutcome(null);
    setPgn(null);
    setIsBotThinking(false);
    setMovesSinceLastDecline(DRAW_OFFER_COOLDOWN_MOVES);
    // A fresh game after a discard must start immediately.
    setLive(true);
    // Clear the (now-abandoned) in-progress snapshot — a fresh game has
    // nothing to resume into. Deliberately does NOT touch the pending-store
    // queue (no `removePendingStore` call): the queue is a separate key that
    // only `finalizeGame` writes to, and a finished-but-not-yet-stored game
    // must survive starting a new one — if a new game could drop a queued
    // entry, a failed store followed by `newGame()` would silently destroy
    // that finished game forever.
    clearSnapshot(ownerKey);
    // lastRootPracticalScoreRef/hasLeftBookRef/hasFiredLowTimeRef are stable
    // props from useBotGameSnapshot (ref identity never changes) — listing
    // them changes nothing about when newGame is recreated.
  }, [
    resetClock,
    resetDrawOfferState,
    updateViewedPly,
    ownerKey,
    lastRootPracticalScoreRef,
    hasLeftBookRef,
    hasFiredLowTimeRef,
  ]);

  // ─── Snapshot write on tab-hide/pagehide, with the clock fold ──────────────
  //
  // A SEPARATE effect from useBotGameClock's pause-bookkeeping one —
  // deliberately NOT bolted onto that `[]`-deps handler. This handler needs
  // to READ `activeColor`/`settings.userColor`/`chargeableElapsedMs` to
  // build a snapshot; a `[]`-deps closure would silently freeze those at
  // their first-mount values for the rest of the game (a "half-invariant":
  // a rule enforced in one place, bypassed via a stale closure in another,
  // invisible to tsc/eslint/knip/a passing suite). useBotGameClock() is
  // called earlier in this hook, so its `visibilitychange` listener
  // registers first (DOM listeners for the same event run in registration
  // order) and `pausedAtRef` is already set when this handler runs —
  // `chargeableElapsedMs()` below is then correctly clamped to the instant
  // of hiding, not a later read.

  useEffect(() => {
    const writeHideTimeSnapshot = (): void => {
      // No resumable snapshot to overwrite for a dormant (not-yet-confirmed)
      // resumed game, and a terminal game's persistence is already owned by
      // `finalizeGame`'s enqueue-and-clear — not this write.
      if (!live || outcomeRef.current) return;
      const folded = foldClockBasesForSnapshot(
        getClockBase(),
        activeColor,
        settings.userColor,
        chargeableElapsedMs(),
      );
      writeSnapshot(ownerKey, buildSnapshot(folded, movesSinceLastDeclineRef.current));
    };
    const handleVisibilityHide = (): void => {
      if (document.visibilityState === 'hidden') writeHideTimeSnapshot();
    };
    // `pagehide` is registered as an additional fallback for hard
    // navigations / bfcache paths that don't always fire `visibilitychange`
    // first — never `beforeunload`/`unload`, which are unreliable on mobile
    // Safari and disable the bfcache in Chromium/Firefox merely by being
    // registered.
    document.addEventListener('visibilitychange', handleVisibilityHide);
    window.addEventListener('pagehide', writeHideTimeSnapshot);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityHide);
      window.removeEventListener('pagehide', writeHideTimeSnapshot);
    };
    // getClockBase and movesSinceLastDeclineRef are stable props (ref
    // identity/[] deps never change) — listing them does not change when
    // this effect re-runs.
  }, [
    live,
    activeColor,
    settings.userColor,
    ownerKey,
    chargeableElapsedMs,
    buildSnapshot,
    getClockBase,
    movesSinceLastDeclineRef,
  ]);

  // ─── Engine-dispatch sub-hook ─────────────────────────────────────────────
  //
  // Wired after commitMove/finalizeGame/the clock and draw-offer sub-hooks —
  // its last dependency (commitMove) is defined just above. Owns the
  // provider bring-up/teardown effect, runBotTurn (honest-clock dispatch),
  // the runBotTurnRef assignment effect and the abort-on-unmount effect —
  // see useBotGameEngineDispatch.ts's file header for the ref-indirection
  // contract the bot-turn-trigger effect below relies on.

  const { runBotTurnRef, retryEngineWarm } = useBotGameEngineDispatch({
    chessRef,
    outcomeRef,
    hasLeftBookRef,
    lastRootPracticalScoreRef,
    abortControllerRef,
    setIsBotThinking,
    botElo: settings.botElo,
    blend: settings.blend,
    incrementSeconds: settings.incrementSeconds,
    style: settings.style,
    userColor: settings.userColor,
    chargeableElapsedMs,
    flagIfOutOfTime,
    getClockBase,
    commitMove,
    finalizeGame,
    bumpConsecutiveLowScoreTurns,
    applyDrawOfferUpdate,
    onBotMoveGraded,
  });

  // ─── Bot-turn trigger ────────────────────────────────────────────────────────
  //
  // Depends on the `moveHistory` array REFERENCE (not just its length) so a
  // newGame() reset (same activeColor value as a just-finished game can
  // coincidentally have) still re-triggers via the fresh empty-array identity.
  //
  // Gated by `live` — without this guard, a snapshot resumed
  // on the BOT's turn would start a real search (and commit a think-deadline
  // clock anchor) the instant this hook mounts, i.e. before the user has
  // agreed to resume at all.

  useEffect(() => {
    if (!live) return;
    if (outcome) return;
    if (activeColor === settings.userColor) return;
    runBotTurnRef.current?.(BOT_SEARCH_BUDGET);
    // runBotTurnRef is a stable prop from useBotGameEngineDispatch (ref
    // identity never changes) — listing it changes nothing about when this
    // effect re-runs. Reading through the ref (not a captured runBotTurn) is
    // the required "always call the latest closure" indirection.
  }, [live, moveHistory, activeColor, outcome, settings.userColor, runBotTurnRef]);

  // ─── Return ────────────────────────────────────────────────────────────────

  return {
    position,
    lastMove,
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
    botDrawOfferPending,
    gameUuid,
    live,
    confirmLive,
    retryEngineWarm,
    attemptMove,
    viewPly,
    returnToLive,
    resign,
    offerDraw,
    acceptBotDraw,
    declineBotDraw,
    newGame,
    botLine,
  };
}

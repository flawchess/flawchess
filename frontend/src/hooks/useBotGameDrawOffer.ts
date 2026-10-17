/**
 * useBotGameDrawOffer — draw-offer sub-hook of useBotGame. Owns both
 * directions of the bot-game draw exchange: the user-initiated
 * `drawOfferPending` resolution (accept/decline against the bot's
 * `wouldBotAcceptDraw` gate) and the bot's own OUTGOING draw offer
 * (`botDrawOfferPending`/`acceptBotDraw`/`declineBotDraw`), plus the per-game
 * resign-hysteresis counter (`consecutiveLowScoreTurnsRef`) that shares the
 * same `pool.grade().then()` seam in `runBotTurn`.
 *
 * `resolveBotDrawOfferUpdate` stays non-exported: its only reader is
 * `applyDrawOfferUpdate` below.
 *
 * `bumpConsecutiveLowScoreTurns`/`applyDrawOfferUpdate` are the two seams
 * `useBotGameEngineDispatch.ts`'s `runBotTurn` calls into from its
 * `pool.grade().then()` continuation — the resign-check (which needs the
 * bumped counter) and the draw-offer check share one grade callback and
 * are call-ordered (resign first, since a resignation makes
 * `gameAlreadyOver` true for the draw-offer check that follows), so
 * `useBotGame.ts` wires `useBotGameDrawOffer()` BEFORE
 * `useBotGameEngineDispatch()` and passes these two functions in as
 * options.
 *
 * Encapsulation follows useBotGameClock.ts, except that the refs which need
 * cross-boundary access (`botDrawOfferPendingRef` for `commitMove`'s
 * clear-on-user-move check, `movesSinceLastDeclineRef` for the snapshot
 * writers) are returned directly. `react-hooks/exhaustive-deps` cannot prove
 * a returned ref stable, so every such caller lists that ref in its
 * dependency array (behaviorally inert: ref identity never changes).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, RefObject, SetStateAction } from 'react';
import type { Chess } from 'chess.js';

import { wouldBotAcceptDraw, wouldBotOfferDraw, DRAW_OFFER_COOLDOWN_MOVES } from '@/lib/botDrawGate';
import { playSound } from '@/lib/sounds';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import type { BotStyleParams } from '@/lib/engine/botStyle';
import type { BotGameSnapshot } from '@/lib/botGameSnapshot';

/**
 * Pure decision + counter update for the bot's own outgoing draw offer,
 * extracted out of the `pool.grade().then()` callback
 * (already dense — CLAUDE.md nesting/logic-LOC limits) so this one seam is
 * isolated and easy to audit. Mirrors `wouldBotResign`'s caller-owned
 * counter discipline: this function holds no state itself — the caller
 * (`applyDrawOfferUpdate` below) applies the returned mutation to its own
 * refs.
 *
 * When an offer is already live or the game just ended (e.g. this same
 * grade turn resigned), the cooldown counter is simply advanced — never
 * reset — and no new offer is raised, even if `wouldBotOfferDraw` would
 * otherwise say yes. Raising a fresh offer always resets the counter to 0
 * (the cooldown restarts).
 */
function resolveBotDrawOfferUpdate(
  score: number,
  chess: Chess,
  style: BotStyleParams,
  movesSinceOwnOffer: number,
  offerAlreadyLive: boolean,
  gameAlreadyOver: boolean,
): { raiseOffer: boolean; nextMovesSinceOwnOffer: number } {
  if (offerAlreadyLive || gameAlreadyOver) {
    return { raiseOffer: false, nextMovesSinceOwnOffer: movesSinceOwnOffer + 1 };
  }
  const offers = wouldBotOfferDraw(score, chess, style.contempt, movesSinceOwnOffer);
  return offers
    ? { raiseOffer: true, nextMovesSinceOwnOffer: 0 }
    : { raiseOffer: false, nextMovesSinceOwnOffer: movesSinceOwnOffer + 1 };
}

export interface UseBotGameDrawOfferOptions {
  /** An optional snapshot to seed movesSinceLastDeclineRef from. */
  resume?: BotGameSnapshot;
  /** Set once the game has ended; null while in progress — `offerDraw`'s guard. */
  outcome: BotGameOutcome | null;
  /** Idempotency latch, read via ref for stale-closure safety — the
   * resolution effect and `acceptBotDraw` both bail out if already set. */
  outcomeRef: RefObject<BotGameOutcome | null>;
  /** Draw-offer throttle — precomputed by `useBotGame.ts` from
   * `movesSinceLastDecline` state (which stays there; `attemptMove`,
   * `newGame` and this hook all touch it). */
  canOfferDraw: boolean;
  chessRef: RefObject<Chess>;
  /** Best-effort draw-accept score, owned by `useBotGameSnapshot`; passed
   * through here for `wouldBotAcceptDraw`'s near-equal check. */
  lastRootPracticalScoreRef: RefObject<number | null>;
  style?: BotStyleParams;
  finalizeGame: (finished: BotGameOutcome) => void;
  /** Setter for `movesSinceLastDecline` (state, owned by `useBotGame.ts` —
   * also incremented by `attemptMove` and reset by `newGame`) — the
   * resolution effect resets it to 0 on a bot decline. */
  setMovesSinceLastDecline: Dispatch<SetStateAction<number>>;
  /** The `movesSinceLastDecline` state value itself — kept in sync onto
   * `movesSinceLastDeclineRef` by an internal effect, since the ref lives
   * here while the state stays in `useBotGame.ts`. */
  movesSinceLastDecline: number;
}

export interface UseBotGameDrawOfferResult {
  /** True while a user-initiated draw offer is being resolved. */
  drawOfferPending: boolean;
  /** True while the BOT has a live OUTGOING draw offer. */
  botDrawOfferPending: boolean;
  /** Source-of-truth latch for `botDrawOfferPending`, read directly (never
   * `botDrawOfferPending` state) by `commitMove`'s stale-closure-safe clear check. */
  botDrawOfferPendingRef: RefObject<boolean>;
  setBotDrawOfferPending: Dispatch<SetStateAction<boolean>>;
  /** Mirror of `movesSinceLastDecline` state, read outside render by the
   * snapshot writers (`commitMove`, the hide-time write), which pass it to
   * `buildSnapshot`. */
  movesSinceLastDeclineRef: RefObject<number>;
  offerDraw: () => void;
  acceptBotDraw: () => void;
  declineBotDraw: () => void;
  /** Resets every per-game draw-offer/resign-hysteresis latch. Called from
   * `newGame()`. */
  resetDrawOfferState: () => void;
  /** Bumps (or, on a non-hit, resets) the resign-hysteresis counter and
   * returns its new value — called from `runBotTurn`'s
   * `pool.grade().then()` continuation, BEFORE `applyDrawOfferUpdate` (a
   * resignation there can end the game, which `applyDrawOfferUpdate`'s
   * `gameAlreadyOver` parameter must see). */
  bumpConsecutiveLowScoreTurns: (scoreAtOrBelowThreshold: boolean) => number;
  /** Applies one `pool.grade()`-seeded draw-offer decision (the ref and state
   * writes behind `resolveBotDrawOfferUpdate`). Called from `runBotTurn`. */
  applyDrawOfferUpdate: (
    score: number,
    chess: Chess,
    style: BotStyleParams,
    gameAlreadyOver: boolean,
  ) => void;
}

/**
 * Draw-offer sub-hook of `useBotGame`. See file header.
 */
export function useBotGameDrawOffer(options: UseBotGameDrawOfferOptions): UseBotGameDrawOfferResult {
  const {
    resume,
    outcome,
    outcomeRef,
    canOfferDraw,
    chessRef,
    lastRootPracticalScoreRef,
    style,
    finalizeGame,
    setMovesSinceLastDecline,
    movesSinceLastDecline,
  } = options;

  const botDrawOfferPendingRef = useRef(false);
  const movesSinceOwnOfferRef = useRef(0);
  const movesSinceLastDeclineRef = useRef(resume?.movesSinceLastDecline ?? DRAW_OFFER_COOLDOWN_MOVES);

  /** Mirror of `movesSinceLastDecline` state, kept fresh by this sync
   * effect — the snapshot writers (`commitMove`, the hide-time write in
   * `useBotGame.ts`) need a fresh read of this value from an event handler
   * that does not want to depend on (and re-run per) the state itself. The
   * ref and its sync effect must live together. */
  useEffect(() => {
    movesSinceLastDeclineRef.current = movesSinceLastDecline;
  }, [movesSinceLastDecline]);
  /** Per-game hysteresis counter for a styled bot's resign check —
   * consecutive OWN turns (not plies) whose FRESH practicalScore graded
   * at/below `settings.style.threshold`. Mutated ONLY via
   * `bumpConsecutiveLowScoreTurns`, called from the same
   * `pool.grade(...).then(...)` callback that updates
   * `lastRootPracticalScoreRef`. Reset to 0 by `resetDrawOfferState()`
   * (`newGame()`). */
  const consecutiveLowScoreTurnsRef = useRef(0);

  const [drawOfferPending, setDrawOfferPending] = useState(false);
  /** Render-facing mirror of `botDrawOfferPendingRef`. */
  const [botDrawOfferPending, setBotDrawOfferPending] = useState(false);

  /** Resolves the ALREADY-set `drawOfferPending` flag — accept ends the
   * game, decline resets the cooldown counter and fires the notification
   * sound. Split from `offerDraw` so `drawOfferPending` is real, observable
   * state (not collapsed into the same synchronous call). This effect
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
    // Sentinel contract: a `null` score means the bot has evaluated
    // nothing this game (e.g. it is still in book, which runs zero Stockfish
    // evals) and `wouldBotAcceptDraw` refuses outright — the bot never accepts
    // a draw off an evaluation it did not run.
    // Undefined style ⇒ contempt 0 ⇒ the standard accept target (0.5) for
    // every unstyled caller.
    const contempt = style?.contempt ?? 0;
    const accepts = wouldBotAcceptDraw(lastRootPracticalScoreRef.current, chessRef.current, contempt);
    if (accepts) {
      finalizeGame({ reason: 'draw', drawReason: 'agreement' });
    } else {
      setMovesSinceLastDecline(0);
      playSound('draw-declined');
    }
    setDrawOfferPending(false);
    // outcomeRef/chessRef/lastRootPracticalScoreRef/setMovesSinceLastDecline
    // are stable cross-hook props (refs/setters never change identity) —
    // listing them changes nothing about when this effect re-runs.
  }, [
    drawOfferPending,
    finalizeGame,
    style,
    outcomeRef,
    chessRef,
    lastRootPracticalScoreRef,
    setMovesSinceLastDecline,
  ]);

  const offerDraw = useCallback((): void => {
    if (outcome) return;
    if (!canOfferDraw) return; // the cooldown throttle gates the button itself
    setDrawOfferPending(true);
  }, [outcome, canOfferDraw]);

  /** Accepts the bot's own outgoing draw offer. Guards on
   * `outcomeRef` first, mirroring the user-offer resolution effect above —
   * a stale accept firing after the game already ended some other way
   * (e.g. the user flagged, or the offer itself is stale UI) is a no-op. */
  const acceptBotDraw = useCallback((): void => {
    if (outcomeRef.current) return;
    botDrawOfferPendingRef.current = false;
    setBotDrawOfferPending(false);
    finalizeGame({ reason: 'draw', drawReason: 'agreement' });
    // outcomeRef is listed for exhaustive-deps — see the resolution effect's
    // comment.
  }, [finalizeGame, outcomeRef]);

  /** Dismisses the bot's own outgoing draw offer without
   * ending the game. The own-offer cooldown already restarted (reset to 0)
   * the moment the offer was raised, so declining only needs to clear the
   * pending flag — no separate cooldown reset here. */
  const declineBotDraw = useCallback((): void => {
    botDrawOfferPendingRef.current = false;
    setBotDrawOfferPending(false);
  }, []);

  /** See `UseBotGameDrawOfferResult.resetDrawOfferState`. All independent
   * setState/ref writes, batched into the same commit. */
  const resetDrawOfferState = useCallback((): void => {
    // A fresh game's resign hysteresis starts clean — never leaks a prior
    // game's consecutive-low-score streak.
    consecutiveLowScoreTurnsRef.current = 0;
    // A fresh game has no live bot offer and no leaked own-offer cooldown
    // streak.
    botDrawOfferPendingRef.current = false;
    setBotDrawOfferPending(false);
    movesSinceOwnOfferRef.current = 0;
    setDrawOfferPending(false);
  }, []);

  /** See `UseBotGameDrawOfferResult.bumpConsecutiveLowScoreTurns`. */
  const bumpConsecutiveLowScoreTurns = useCallback((scoreAtOrBelowThreshold: boolean): number => {
    consecutiveLowScoreTurnsRef.current = scoreAtOrBelowThreshold
      ? consecutiveLowScoreTurnsRef.current + 1
      : 0;
    return consecutiveLowScoreTurnsRef.current;
  }, []);

  /** See `UseBotGameDrawOfferResult.applyDrawOfferUpdate`. */
  const applyDrawOfferUpdate = useCallback(
    (score: number, chess: Chess, drawStyle: BotStyleParams, gameAlreadyOver: boolean): void => {
      // The bot's own OUTGOING draw offer, checked at the same grade seam
      // runBotTurn already computed a fresh score from — never a second
      // pool.grade() call site. If a resignation just ended the game,
      // `gameAlreadyOver` (outcomeRef.current !== null, read by the caller)
      // is already true, so `resolveBotDrawOfferUpdate` naturally refuses to
      // raise an offer on the same turn.
      const offerUpdate = resolveBotDrawOfferUpdate(
        score,
        chess,
        drawStyle,
        movesSinceOwnOfferRef.current,
        botDrawOfferPendingRef.current,
        gameAlreadyOver,
      );
      movesSinceOwnOfferRef.current = offerUpdate.nextMovesSinceOwnOffer;
      if (offerUpdate.raiseOffer) {
        botDrawOfferPendingRef.current = true;
        setBotDrawOfferPending(true);
      }
    },
    [],
  );

  return {
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
  };
}

/**
 * useBotGameVoice — bubble-state sub-hook of useBotGame (Phase 223,
 * BOTVOICE-01/02/03). Owns the in-game speech-bubble line: the one-time
 * game-start greeting, the clear-on-player-commit seam (D-07), the async
 * graded-score seam that produces swing lines (D-01/D-02/D-03/D-04), the draw-offer and
 * terminal effects, and the pacing gate that keeps the bot from chattering.
 * Modeled on `useBotGameDrawOffer.ts`'s shape: it owns its own state and
 * returns the callbacks the other sub-hooks take as options.
 *
 * D-07 is enforced structurally in this file: no timer-based scheduling of
 * any kind (delayed callback, repeating callback, or animation-frame
 * callback) and no CSS transition/animation utility anywhere — the
 * bubble's content changes only in direct response to a commit, a grade
 * resolving, an outcome landing, or a draw offer being raised, never on a
 * clock tick.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Move } from 'chess.js';

import type { MoverColor } from '@/lib/liveFlaw';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import type { BotLineKey } from '@/lib/botGameCopy';
import {
  resolveBotLine,
  resolveRegretPunishKey,
  isRegretSwing,
  type ResolveBotLineInput,
  BOT_LINE_MIN_SPACING_MOVES,
  BOT_LINE_PAIR_PLY_SPAN,
} from '@/lib/botLineTrigger';

export interface UseBotGameVoiceOptions {
  userColor: MoverColor;
  /** The resumed game's ply count at mount (0 for a fresh game). A resumed
   * game (`initialPly > 0`) never greets — D-06's game-start line is pure
   * voice for a game that has not started, and a resumed game already has. */
  initialPly: number;
  /** Phase 170 D-03 `live` gate — mirrors every other sub-hook's contract:
   * the greeting effect waits for `confirmLive()` exactly like the
   * turn-anchor/clock-tick/bot-turn-trigger effects in `useBotGame.ts` do. */
  live: boolean;
  /** Phase 183 D-07's live outgoing offer, forwarded from
   * `useBotGameDrawOffer` via `useBotGame.ts` — feeds the resolver's
   * draw-offer arm (BOTVOICE-02) both from `onBotMoveGraded` and from the
   * dedicated immediate-fire effect below. */
  botDrawOffer: boolean;
  /** Set once the game has ended; `null` while in progress — feeds the
   * resolver's terminal arm both from `onBotMoveGraded` and from the
   * dedicated terminal effect below, since a game can end (flag,
   * resignation, stalemate) with no grade in flight at all. */
  outcome: BotGameOutcome | null;
}

export interface UseBotGameVoiceResult {
  /** The bubble's current line key, or `null` for an empty (but still
   * reserved-height, D-07) slot. */
  botLine: BotLineKey | null;
  /** Supplied to `useBotGameMoves`'s `commitMove` (seam A) — fires for
   * every committed move, player and bot alike. Narrower than the seam's own
   * 3-arg prop type (which still passes the post-move `Chess`): this hook
   * stopped reading the board when the `'player-threat'` probe was retired,
   * and a 2-arg function is assignable to the 3-arg prop. */
  onMoveCommitted: (move: Move, mover: MoverColor) => void;
  /** Supplied to `useBotGameEngineDispatch`'s grade continuation (seam B) —
   * fires once per SEARCHED (non-book) bot move whose grade resolved, with
   * that move's bot-POV clamped centipawn score (`clampedMoverPovCp`) and
   * the ply it was played at. This hook keeps the previous value itself, so
   * the caller no longer has to read-before-overwrite a shared ref. */
  onBotMoveGraded: (cp: number, ply: number) => void;
}

/** A fully-populated `ResolveBotLineInput` with every flag at its
 * structurally-inert default, overridden per call site — mirrors
 * `trainBubbleState.ts`'s pattern of always passing the complete input
 * shape. Used by the three single-signal effects below (greeting, terminal,
 * draw offer); `onBotMoveGraded` builds its own full input directly, since
 * every field there is a real, currently-latched value. */
function defaultResolveBotLineInput(): ResolveBotLineInput {
  return {
    gameStartPending: false,
    swingCp: null,
    recoveryCp: null,
    firstCapturePending: false,
    drawOfferLive: false,
    outcomeKind: null,
    botMovesSinceLastLine: BOT_LINE_MIN_SPACING_MOVES,
  };
}

/** Resolves a finished game's `BotGameOutcome` to the resolver's
 * `outcomeKind` shape, from `userColor`'s point of view — `null` while the
 * game continues, `'draw'` for any draw reason, else `'loss'` when the
 * winner is the USER (the bot lost) and `'win'` when it is not (the bot
 * won). Mirrors `botGameEnd.ts`'s own `userWon` framing. */
function outcomeKindFor(
  outcome: BotGameOutcome | null,
  userColor: MoverColor,
): 'win' | 'loss' | 'draw' | null {
  if (outcome === null) return null;
  if (outcome.reason === 'draw') return 'draw';
  return outcome.winner === userColor ? 'loss' : 'win';
}

/**
 * Bubble-state sub-hook of `useBotGame` (Phase 223). See file header.
 */
export function useBotGameVoice(options: UseBotGameVoiceOptions): UseBotGameVoiceResult {
  const { userColor, initialPly, live, botDrawOffer, outcome } = options;

  const [botLine, setBotLine] = useState<BotLineKey | null>(null);

  /** One-shot latch for the game-start greeting effect below — set the
   * FIRST time the effect actually runs (regardless of outcome), so a
   * resumed-but-not-yet-live game that later confirms live still greets
   * (or not) exactly once, never on a later re-render. */
  const gameStartLatchRef = useRef(false);

  /** D-01/BOTVOICE-03: the ply the last SEARCHED bot grade was recorded
   * at — `null` until the first grade resolves this game. Read (never
   * written) outside `onBotMoveGraded`. */
  const lastGradedPlyRef = useRef<number | null>(null);

  /** The bot-POV clamped centipawn score of that same last graded ply, so a
   * swing delta is a difference between two values this hook latched at the
   * same moment as the plies they belong to. Owned here rather than shared
   * with the draw gate's `lastRootPracticalScoreRef`: that ref carries
   * expected score for a different consumer, and the two must not be
   * conflated. */
  const lastGradedCpRef = useRef<number | null>(null);

  /**
   * The regret latch (Phase 223 UAT): the bot-POV clamped centipawn score at
   * the moment the bot's own graded move dropped the position by a full
   * threshold, or `null` when nothing is outstanding. Set instead of
   * speaking, so the bot never announces its own blunder before the player
   * has had a move; consumed by whichever comes first — the player's
   * capturing reply (`onMoveCommitted`) or the bot's next grade
   * (`onBotMoveGraded`). See `botLineTrigger.ts`'s timing-model header.
   */
  const regretCpRef = useRef<number | null>(null);
  /** Latched true the first time either side captures this game; consumed
   * (never reset back to false) once the first-capture line has fired —
   * see `firstCaptureAnnouncedRef`. */
  const firstCaptureSeenRef = useRef(false);
  /** BOTVOICE-02: set true once the `'first-capture'` key has actually
   * fired, so `firstCapturePending` (seen-but-not-announced) can never
   * re-trigger the same fact twice. */
  const firstCaptureAnnouncedRef = useRef(false);

  /** Claude's Discretion (223-CONTEXT.md): bot moves elapsed since the last
   * NON-terminal line fired. Initialized at `BOT_LINE_MIN_SPACING_MOVES` —
   * "already spaced enough" — mirroring `movesSinceLastDecline`'s own init
   * convention (`DRAW_OFFER_COOLDOWN_MOVES`), so nothing needs to wait
   * before the first line a fresh game could ever fire. Incremented on
   * every bot commit (`onMoveCommitted`'s bot branch, including book
   * moves); reset to 0 whenever `resolveBotLine` returns ANY key. */
  const botMovesSinceLastLineRef = useRef(BOT_LINE_MIN_SPACING_MOVES);

  /** One-shot latch for the terminal effect below — the first outcome wins
   * (mirrors `outcomeRef`'s WR-03 pattern one layer up in `useBotGame.ts`,
   * though this hook only ever needs single-fire, not idempotency across
   * async races). */
  const outcomeLineLatchRef = useRef(false);

  // ─── Game-start greeting (fires at most once per game) ────────────────

  useEffect(() => {
    if (!live) return;
    if (gameStartLatchRef.current) return;
    gameStartLatchRef.current = true;
    if (initialPly !== 0) return;
    const line = resolveBotLine({ ...defaultResolveBotLineInput(), gameStartPending: true });
    if (line !== null) setBotLine(line);
  }, [live, initialPly]);

  // ─── Terminal effect (BOTVOICE-02): fires once, with or without a grade ─
  //
  // A game can end on a flag, a resignation, or a stalemate with no grade
  // in flight at all — the terminal key must still appear, so this effect
  // bypasses the async grade seam entirely rather than waiting for
  // `onBotMoveGraded` to happen to fire again.

  useEffect(() => {
    if (outcome === null) return;
    if (outcomeLineLatchRef.current) return;
    outcomeLineLatchRef.current = true;
    // Phase 223 UAT: the 223-02 trade-off that let this line go unread on a
    // loss or a draw is gone — `useWinCelebrationHold` now holds
    // `GameResultDialog` closed after EVERY ending (the confetti lifetime on
    // a win, a shorter read window otherwise), so the terminal line below is
    // on screen before the dialog covers it in all three cases.
    const kind = outcomeKindFor(outcome, userColor);
    if (kind === null) return;
    const line = resolveBotLine({ ...defaultResolveBotLineInput(), outcomeKind: kind });
    if (line !== null) setBotLine(line);
  }, [outcome, userColor]);

  // ─── Draw-offer effect (BOTVOICE-02, D-12): fires the moment the offer
  // exists, rather than waiting for the next grade ─────────────────────────

  useEffect(() => {
    if (!botDrawOffer) return;
    const line = resolveBotLine({ ...defaultResolveBotLineInput(), drawOfferLive: true });
    if (line !== null) setBotLine(line);
  }, [botDrawOffer]);

  // ─── Seam A: commit callback — clears on the player's own move (D-07),
  // latches the board-truth facts each arm needs ─────────────────────────
  //
  // Two guard clauses, never nested: the player branch clears the bubble and
  // re-latches the capture facts for the CURRENT move pair; the bot branch
  // advances the pacing counter.

  const onMoveCommitted = useCallback(
    (move: Move, mover: MoverColor): void => {
      if (mover === userColor) {
        const captured = move.captured !== undefined;
        if (captured) firstCaptureSeenRef.current = true;
        // Phase 223 UAT: the ONE line that fires on the player's own move.
        // The bot owns up the moment its outstanding blunder is actually
        // taken — the beat a human opponent would react on, and the beat the
        // engine can never put a swing on (the capture itself moves the eval
        // by almost nothing; the drop was already priced when the piece was
        // hung). Ungated by pacing: it answers the player directly.
        const punishKey = resolveRegretPunishKey(regretCpRef.current !== null, captured);
        if (punishKey !== null) {
          regretCpRef.current = null;
          botMovesSinceLastLineRef.current = 0;
          setBotLine(punishKey);
          return;
        }
        setBotLine(null);
        return;
      }
      if (move.captured) firstCaptureSeenRef.current = true;
      botMovesSinceLastLineRef.current += 1;
    },
    [userColor],
  );

  // ─── Seam B: the async graded-score path (BOTVOICE-03) ─────────────────

  const onBotMoveGraded = useCallback(
    (cp: number, ply: number): void => {
      const lastGradedPly = lastGradedPlyRef.current;
      const lastGradedCp = lastGradedCpRef.current;
      let swingCp: number | null = null;
      if (lastGradedCp !== null && lastGradedPly !== null && ply - lastGradedPly === BOT_LINE_PAIR_PLY_SPAN) {
        swingCp = cp - lastGradedCp;
      }
      const regretCp = regretCpRef.current;
      const recoveryCp = regretCp === null ? null : cp - regretCp;
      const line = resolveBotLine({
        gameStartPending: false,
        swingCp,
        recoveryCp,
        firstCapturePending: firstCaptureSeenRef.current && !firstCaptureAnnouncedRef.current,
        drawOfferLive: botDrawOffer,
        outcomeKind: outcomeKindFor(outcome, userColor),
        botMovesSinceLastLine: botMovesSinceLastLineRef.current,
      });
      // An outstanding latch settles on THIS grade: the resolver always
      // yields a key for a live latch and never paces it (223-REVIEW CR-01),
      // so clearing here cannot drop a line. Re-arming afterwards is
      // deliberate: a bot that blunders again on the very move that answered
      // its last blunder gets a fresh latch rather than silence.
      if (recoveryCp !== null) regretCpRef.current = null;
      if (isRegretSwing(swingCp)) regretCpRef.current = cp;
      if (line !== null) {
        setBotLine(line);
        botMovesSinceLastLineRef.current = 0;
        // Consume the once-per-game latch so the SAME fact cannot fire twice.
        if (line === 'first-capture') firstCaptureAnnouncedRef.current = true;
      }
      lastGradedPlyRef.current = ply;
      lastGradedCpRef.current = cp;
    },
    [botDrawOffer, outcome, userColor],
  );

  return {
    botLine,
    onMoveCommitted,
    onBotMoveGraded,
  };
}

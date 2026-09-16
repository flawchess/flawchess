/**
 * useWinCelebrationHold — holds the bot-game result modal closed for a short
 * window after certain endings, so the board is seen before the dialog
 * covers it (Quick 260723-tqn; retimed in Phase 223 UAT; checkmate arm
 * added 2026-09-16).
 *
 * Two endings hold, each for its own reason and its own length:
 *
 *  - A HUMAN WIN with motion enabled holds for `CONFETTI_DURATION_MS`,
 *    imported from the module that fires the burst (fired from
 *    `useBotGame`'s `finalizeGame`) rather than guessed at — the previous
 *    1300ms was a guess and expired with roughly half the burst still in
 *    the air. A reduced-motion win fires no confetti and so does not hold.
 *  - A BOT CHECKMATE holds for `BOT_CHECKMATE_VIEW_HOLD_MS`. The bot's
 *    mating move lands and the dialog opened on the same frame, so the
 *    player never saw the checkmating position at all — only "Butch won by
 *    checkmate" over a board they could not inspect. This is a read window,
 *    not an animation, so it is deliberately NOT gated on reduced motion.
 *
 * Nothing else holds: a loss on time or by resignation, and every draw, show
 * a board the player already understands, so a held blank board would be a
 * stall, not a beat. The bot's own terminal line is NOT a reason to hold
 * either — as of Phase 223 UAT it is rendered inside `GameResultDialog`
 * (with the persona's avatar) and the board-side bubble goes silent at game
 * end, so the line is read in the dialog, not behind it.
 *
 * `null` (no outcome yet) returns `false` — nothing to hold.
 */

import { useEffect, useRef, useState } from 'react';

import type { BotGameOutcome } from '@/lib/botGameEnd';
import type { MoverColor } from '@/lib/liveFlaw';
import { CONFETTI_DURATION_MS, prefersReducedMotion } from '@/lib/confetti';

function isHumanWin(outcome: BotGameOutcome | null, userColor: MoverColor): boolean {
  if (outcome === null) return false;
  if (outcome.reason === 'draw') return false;
  return outcome.winner === userColor;
}

function isBotCheckmate(outcome: BotGameOutcome | null, userColor: MoverColor): boolean {
  if (outcome === null) return false;
  if (outcome.reason !== 'checkmate') return false;
  return outcome.winner !== userColor;
}

/**
 * How long the result dialog stays closed after the bot delivers checkmate,
 * so the player can actually see the mating position before it is covered.
 * Long enough to read a board, short enough not to feel like the dialog
 * failed to open.
 */
export const BOT_CHECKMATE_VIEW_HOLD_MS = 2500;

/**
 * The hold length a fresh outcome earns, or `0` for "open the dialog now".
 * The human-win arm is checked first: it is the longer of the two and the
 * two conditions are mutually exclusive anyway (a human win is never a bot
 * checkmate).
 */
function holdDurationMs(outcome: BotGameOutcome, userColor: MoverColor): number {
  if (isHumanWin(outcome, userColor)) return prefersReducedMotion() ? 0 : CONFETTI_DURATION_MS;
  if (isBotCheckmate(outcome, userColor)) return BOT_CHECKMATE_VIEW_HOLD_MS;
  return 0;
}

/**
 * Returns `true` for the hold window right after a fresh outcome that earns
 * one arrives (a human win with motion enabled, or a bot checkmate); `false`
 * otherwise (no outcome, a reduced-motion win, a loss on time or by
 * resignation, or a draw).
 */
export function useWinCelebrationHold(
  outcome: BotGameOutcome | null,
  userColor: MoverColor,
): boolean {
  const [held, setHeld] = useState(false);
  // Tracks the outcome reference we've already started a hold for, so a
  // re-render with the SAME outcome object never re-triggers the timer, but a
  // fresh outcome (including after a reset to null) always does.
  const startedForRef = useRef<BotGameOutcome | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (outcome === null) {
      startedForRef.current = null;
      setHeld(false);
      return;
    }
    if (startedForRef.current === outcome) return; // already handled this outcome
    startedForRef.current = outcome;

    const durationMs = holdDurationMs(outcome, userColor);
    if (durationMs === 0) {
      setHeld(false);
      return;
    }

    setHeld(true);
    timeoutRef.current = setTimeout(() => {
      setHeld(false);
    }, durationMs);

    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [outcome, userColor]);

  return held;
}

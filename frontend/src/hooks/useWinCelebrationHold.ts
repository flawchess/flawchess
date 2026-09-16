/**
 * useWinCelebrationHold — holds the bot-game result modal closed for exactly
 * as long as the confetti burst (fired from `useBotGame`'s `finalizeGame`)
 * is on screen, so the celebration plays out over the board instead of being
 * covered mid-flight (Quick 260723-tqn; retimed in Phase 223 UAT).
 *
 * The hold length is `CONFETTI_DURATION_MS`, imported from the module that
 * fires the burst rather than guessed at — the previous 1300ms was a guess
 * and expired with roughly half the burst still in the air.
 *
 * Only a human win with motion enabled holds. A loss, a draw, and a
 * reduced-motion win all fire no confetti, so there is nothing to wait out:
 * a briefly-held blank board would be a stall, not a beat. The bot's own
 * terminal line is NOT a reason to hold either — as of this same UAT round
 * it is rendered inside `GameResultDialog` (with the persona's avatar) and
 * the board-side bubble goes silent at game end, so the line is read in the
 * dialog, not behind it.
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

/**
 * Returns `true` for `CONFETTI_DURATION_MS` right after a fresh human-win
 * outcome arrives with motion enabled; `false` otherwise (no outcome, loss,
 * draw, or reduced-motion).
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

    if (!isHumanWin(outcome, userColor) || prefersReducedMotion()) {
      setHeld(false);
      return;
    }

    setHeld(true);
    timeoutRef.current = setTimeout(() => {
      setHeld(false);
    }, CONFETTI_DURATION_MS);

    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [outcome, userColor]);

  return held;
}

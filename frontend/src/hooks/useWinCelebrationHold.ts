/**
 * useWinCelebrationHold — holds the bot-game result modal closed for a short
 * window after a human win, so the confetti burst (fired from
 * `useBotGame`'s `finalizeGame`) plays over the board before the modal
 * covers it (Quick 260723-tqn).
 *
 * Loss/draw/no-outcome all return `false` immediately (no hold — the modal
 * opens right away, matching pre-existing behavior). Reduced-motion users
 * also get `false` immediately: no confetti means no reason to delay the
 * modal either.
 */

import { useEffect, useRef, useState } from 'react';

import type { BotGameOutcome } from '@/lib/botGameEnd';
import type { MoverColor } from '@/lib/liveFlaw';
import { prefersReducedMotion } from '@/lib/confetti';

/** How long the result modal stays held closed after a human win, so the
 * confetti burst has time to read before the modal covers the board.
 * ~1.3s comfortably outlasts fireWinConfetti's short two-burst animation. */
export const WIN_CELEBRATION_HOLD_MS = 1300;

function isHumanWin(outcome: BotGameOutcome | null, userColor: MoverColor): boolean {
  if (outcome === null) return false;
  if (outcome.reason === 'draw') return false;
  return outcome.winner === userColor;
}

/**
 * Returns `true` only for the duration of `WIN_CELEBRATION_HOLD_MS` right
 * after a fresh human-win outcome arrives (and only when NOT
 * reduced-motion); `false` otherwise (no outcome, loss, draw, or
 * reduced-motion win).
 */
export function useWinCelebrationHold(
  outcome: BotGameOutcome | null,
  userColor: MoverColor,
): boolean {
  const [held, setHeld] = useState(false);
  // Tracks the outcome reference we've already started (or decided not to
  // start) a hold for, so a re-render with the SAME outcome object never
  // re-triggers the timer, but a fresh outcome (including after a reset to
  // null) always does.
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
    }, WIN_CELEBRATION_HOLD_MS);

    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [outcome, userColor]);

  return held;
}

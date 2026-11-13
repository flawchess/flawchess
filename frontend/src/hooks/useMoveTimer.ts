/**
 * useMoveTimer: the per-prompt countdown of the blunder-check drill (Phase 249, D-13, D-18).
 *
 * Deadline-based: the deadline is captured when the countdown starts and every tick
 * re-derives the remaining time from the clock, so a throttled background tab cannot make
 * the countdown drift. `durationMs` is the SERVER's timer_remaining_ms (about 10 s for a
 * fresh prompt, the real remaining time for a resumed one), so a reload never buys time.
 * Grading, forfeits and timeouts stay server-side; this hook only drives the display and
 * asks the caller to submit a timeout once.
 */

import { useEffect, useRef, useState } from 'react';

/** How often the displayed remaining time and the deadline check refresh. */
export const MOVE_TIMER_TICK_MS = 100;

interface UseMoveTimerOptions {
  /** The countdown's length, started when `running` becomes true. */
  durationMs: number;
  /** False freezes the countdown (and shows the full duration before it ever ran). */
  running: boolean;
  /** Identifies the prompt; a new key restarts the countdown. */
  promptKey: string;
  /** Called once when the countdown reaches zero. */
  onTimeout: () => void;
}

interface TimerReading {
  key: string;
  remainingMs: number;
}

export function useMoveTimer({
  durationMs,
  running,
  promptKey,
  onTimeout,
}: UseMoveTimerOptions): { remainingMs: number } {
  const [reading, setReading] = useState<TimerReading | null>(null);
  // The latest callback, so a re-render with a new closure never restarts the countdown.
  const onTimeoutRef = useRef(onTimeout);
  useEffect(() => {
    onTimeoutRef.current = onTimeout;
  });

  useEffect(() => {
    if (!running) return;
    const deadline = performance.now() + durationMs;
    // Refreshes the reading; returns true once the deadline has passed and the timeout fired.
    const step = (): boolean => {
      const remainingMs = Math.max(0, deadline - performance.now());
      setReading({ key: promptKey, remainingMs });
      if (remainingMs > 0) return false;
      onTimeoutRef.current();
      return true;
    };
    // A prompt with no time left times out immediately instead of one tick later.
    if (durationMs <= 0) {
      step();
      return;
    }
    const interval = setInterval(() => {
      if (step()) clearInterval(interval);
    }, MOVE_TIMER_TICK_MS);
    return () => clearInterval(interval);
  }, [running, promptKey, durationMs]);

  // A reading belongs to one prompt: before the first tick of a new key the full duration shows.
  const remainingMs = reading !== null && reading.key === promptKey ? reading.remainingMs : durationMs;
  return { remainingMs };
}

/** The puzzles launcher row's view of today's session (shared by the landing and the mode cards). */
import type { TrainModeProgress, TrainModeState } from '@/types/train';

/**
 * What the landing knows about today's puzzle session. The session response is the
 * authority for what the Start button does (fresh, resume or done) and for the count
 * left, so it overrides the server's per-mode estimate for the puzzles row. A server
 * `off` (session size 0) always wins.
 */
export interface PuzzlesLanding {
  state: TrainModeState;
  /** Puzzles left in today's session. */
  left: number;
  /** Points scored in today's session, shown once it is done. */
  pointsToday: number;
}

/**
 * The puzzles row's progress. Without a landing the count left is the server's
 * `waiting_count` estimate, an upper bound that can exceed one session, so it is capped
 * at the session size.
 */
export function puzzlesRowProgress(
  server: TrainModeProgress,
  landing: PuzzlesLanding | undefined,
): TrainModeProgress {
  if (server.state === 'off') return server;
  if (landing === undefined) return { ...server, remaining: Math.min(server.remaining, server.size) };
  return { ...server, state: landing.state, remaining: landing.left };
}

/**
 * Clock-context line for the Train reveal (quick 261015-s05): "Played after 13s,
 * with 3:56 left." Tells the solver the clock situation they made the flawed move in.
 *
 * Both inputs come from `GameFlawCard.eval_series` (the point at the puzzle's flaw
 * ply), computed server-side in `_build_eval_series`: `clock_seconds` is the mover's
 * remaining clock after the move, `move_seconds` is the increment-corrected think
 * time. Both are null for daily/correspondence games and games without %clk data.
 * The clock formatter mirrors FlawCard's floor m:ss.
 */

const SECONDS_PER_MINUTE = 60;
/** padStart width for the minutes/seconds fields of the clock. */
const CLOCK_FIELD_WIDTH = 2;

/** Think time: whole seconds below a minute ("13s"), else "1m 20s". */
function formatThinkTime(moveSeconds: number): string {
  // Round BEFORE splitting so 59.6 gives "1m", never "60s".
  const total = Math.max(0, Math.round(moveSeconds));
  if (total < SECONDS_PER_MINUTE) return `${total}s`;
  return `${Math.floor(total / SECONDS_PER_MINUTE)}m ${total % SECONDS_PER_MINUTE}s`;
}

/** Remaining clock: floored m:ss. */
function formatClockRemaining(clockSeconds: number): string {
  const total = Math.max(0, Math.floor(clockSeconds));
  const minutes = Math.floor(total / SECONDS_PER_MINUTE);
  const seconds = String(total % SECONDS_PER_MINUTE).padStart(CLOCK_FIELD_WIDTH, '0');
  return `${minutes}:${seconds}`;
}

export function clockContextLine(
  clockSeconds: number | null,
  moveSeconds: number | null,
): string | null {
  if (clockSeconds === null || moveSeconds === null) return null;
  return `Played after ${formatThinkTime(moveSeconds)}, with ${formatClockRemaining(clockSeconds)} left.`;
}

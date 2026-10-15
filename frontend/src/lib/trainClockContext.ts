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
const SECONDS_PER_HOUR = 3600;
/** padStart width for the minutes/seconds fields of the clock. */
const CLOCK_FIELD_WIDTH = 2;

/** Think time: whole seconds below a minute ("13s"), else "1m 20s" ("2m" on an exact minute). */
function formatThinkTime(moveSeconds: number): string {
  // Round BEFORE splitting so 59.6 gives "1m", never "60s".
  const total = Math.max(0, Math.round(moveSeconds));
  if (total < SECONDS_PER_MINUTE) return `${total}s`;
  const minutes = Math.floor(total / SECONDS_PER_MINUTE);
  const seconds = total % SECONDS_PER_MINUTE;
  return seconds === 0 ? `${minutes}m` : `${minutes}m ${seconds}s`;
}

function padClockField(value: number): string {
  return String(value).padStart(CLOCK_FIELD_WIDTH, '0');
}

/** Remaining clock: floored m:ss, h:mm:ss from one hour on. */
function formatClockRemaining(clockSeconds: number): string {
  const total = Math.max(0, Math.floor(clockSeconds));
  const seconds = padClockField(total % SECONDS_PER_MINUTE);
  if (total >= SECONDS_PER_HOUR) {
    const hours = Math.floor(total / SECONDS_PER_HOUR);
    const minutes = padClockField(Math.floor((total % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE));
    return `${hours}:${minutes}:${seconds}`;
  }
  return `${Math.floor(total / SECONDS_PER_MINUTE)}:${seconds}`;
}

/** "Played after 13s, with 3:56 left." with fallbacks; null when neither value is known. */
export function clockContextLine(
  clockSeconds: number | null,
  moveSeconds: number | null,
): string | null {
  if (clockSeconds === null) {
    return moveSeconds === null ? null : `Played after ${formatThinkTime(moveSeconds)}.`;
  }
  const clock = formatClockRemaining(clockSeconds);
  if (moveSeconds === null) return `Played with ${clock} left.`;
  return `Played after ${formatThinkTime(moveSeconds)}, with ${clock} left.`;
}

/**
 * Shared signed-clock formatters used by EndgameClockPressureSection (Phase 54)
 * and MostPlayedOpeningsTable (Phase 80, D-05) so the two clock-diff cells
 * "read identically across the app."
 *
 * Zero convention: formatSignedPct1(0) returns '0.0%' (no '+' prefix) since
 * zero clock advantage is neutral — neither positive nor negative.
 */

/**
 * Format a signed seconds value as '+Xs', '-Xs', or '0s'.
 * Returns '—' if the value is null.
 */
export function formatSignedSeconds(seconds: number | null): string {
  if (seconds === null) return '—';
  const rounded = Math.round(seconds);
  if (rounded > 0) return `+${rounded}s`;
  return `${rounded}s`;
}

/**
 * Format a signed percent value (pre-computed difference) to one decimal place.
 * Returns '+X.X%', '-X.X%', '0.0%', or '—' for null.
 *
 * Note: formatSignedPct in EndgameClockPressureSection takes (userPct, oppPct)
 * and computes the difference; this function takes the pre-computed diff directly.
 */
export function formatSignedPct1(pct: number | null): string {
  if (pct === null) return '—';
  const rounded = Math.round(pct * 10) / 10;
  if (rounded > 0) return `+${rounded.toFixed(1)}%`;
  return `${rounded.toFixed(1)}%`;
}

/**
 * Format signed eval in pawns to one decimal place with explicit sign.
 *
 * Examples: 2.13 -> '+2.1', -0.47 -> '-0.5', 0 -> '+0.0'.
 * Used for the "MG eval" text column in MostPlayedOpeningsTable (Phase 80).
 */
export function formatSignedEvalPawns(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}`;
}

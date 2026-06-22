/**
 * Format a raw PGN time-control string for display on game cards.
 *
 * Shared by GameCard and LibraryGameCard (previously duplicated verbatim in
 * each — extracted here as a pure util, the same placement as primaryTc.ts).
 *
 * Handled forms:
 *   "1/259200" → "3d"   (daily/correspondence: seconds-per-move)
 *   "180+2"    → "3+2"   (base minutes + increment seconds)
 *   "30+0"     → "30s"   (hyperbullet base rounds to 0 min — show seconds)
 *   "15+1"     → "15s+1"
 *   "600"      → "10"    (no increment, minute+ base)
 *   "30"       → "30s"   (no increment, sub-minute base)
 */
const SECONDS_PER_DAY = 86400;
const SECONDS_PER_MINUTE = 60;

export function formatTimeControl(tcStr: string): string {
  // PGN daily/correspondence format: "1/{seconds_per_move}" (e.g. "1/259200" = 3 days/move).
  // Used by chess.com daily and lichess correspondence. Render as "Nd".
  // Previously fell through to Number("1/259200") = NaN, producing "Classical · NaN".
  if (tcStr.startsWith('1/')) {
    const secondsPerMove = Number(tcStr.slice(2));
    const days = Math.round(secondsPerMove / SECONDS_PER_DAY);
    return `${days}d`;
  }
  if (tcStr.includes('+')) {
    const [baseSec, inc] = tcStr.split('+');
    const baseSecNum = Number(baseSec);
    // Hyperbullet (<1min base) rounded to "0" min, rendering e.g. "Bullet 0".
    // Show the base in seconds instead: "30s" (with increment, "15s+1").
    if (baseSecNum < SECONDS_PER_MINUTE) {
      return Number(inc) > 0 ? `${baseSecNum}s+${inc}` : `${baseSecNum}s`;
    }
    return `${Math.floor(baseSecNum / SECONDS_PER_MINUTE)}+${inc}`;
  }
  // No increment — sub-minute shows seconds, otherwise convert to minutes.
  const baseSec = Number(tcStr);
  if (baseSec < SECONDS_PER_MINUTE) return `${baseSec}s`;
  return String(Math.floor(baseSec / SECONDS_PER_MINUTE));
}

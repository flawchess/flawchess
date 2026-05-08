/**
 * Relative-date formatter for the WDL confidence tooltip "Last played: ..." line.
 *
 * Converts an ISO 8601 timestamp into short human prose ("Just now",
 * "5 minutes ago", "3 days ago", "2 years ago"). The companion
 * `formatAbsoluteDate` helper renders a localized full timestamp suitable for
 * the title attribute (hover reveals the precise date).
 *
 * Quick task 260508-r61.
 */

// Threshold under which we render "Just now" rather than counting individual
// seconds. Avoids visual jitter for clocks that are slightly out of sync.
const JUST_NOW_THRESHOLD_SECONDS = 30;

const SECONDS_IN_MINUTE = 60;
const MINUTES_IN_HOUR = 60;
const HOURS_IN_DAY = 24;
const DAYS_IN_WEEK = 7;
// Approximations are deliberate: chess games are timestamped to the second but
// the tooltip line is purely cosmetic ("X months ago"). Using calendar-aware
// math (e.g. date-fns) would add a dependency for no user-visible benefit.
const DAYS_IN_MONTH = 30;
const DAYS_IN_YEAR = 365;

const SECONDS_IN_HOUR = SECONDS_IN_MINUTE * MINUTES_IN_HOUR;
const SECONDS_IN_DAY = SECONDS_IN_HOUR * HOURS_IN_DAY;
const SECONDS_IN_WEEK = SECONDS_IN_DAY * DAYS_IN_WEEK;
const SECONDS_IN_MONTH = SECONDS_IN_DAY * DAYS_IN_MONTH;
const SECONDS_IN_YEAR = SECONDS_IN_DAY * DAYS_IN_YEAR;

function pluralize(count: number, unit: string): string {
  return `${count} ${unit}${count === 1 ? '' : 's'} ago`;
}

/**
 * Render an ISO 8601 timestamp as a short relative label. Future timestamps
 * (clock skew, bad data) clamp to "Just now" — we never render "in 5 minutes".
 *
 * @param iso  ISO 8601 timestamp (UTC offset preserved by Date.parse).
 * @param now  Override for tests; defaults to Date.now().
 */
export function formatRelativeDate(iso: string, now: Date = new Date()): string {
  const then = new Date(iso).getTime();
  const diffSeconds = Math.max(0, Math.floor((now.getTime() - then) / 1000));

  if (diffSeconds < JUST_NOW_THRESHOLD_SECONDS) return 'Just now';
  if (diffSeconds < SECONDS_IN_HOUR) {
    const minutes = Math.floor(diffSeconds / SECONDS_IN_MINUTE);
    return pluralize(Math.max(1, minutes), 'minute');
  }
  if (diffSeconds < SECONDS_IN_DAY) {
    const hours = Math.floor(diffSeconds / SECONDS_IN_HOUR);
    return pluralize(hours, 'hour');
  }
  if (diffSeconds < SECONDS_IN_WEEK) {
    const days = Math.floor(diffSeconds / SECONDS_IN_DAY);
    return pluralize(days, 'day');
  }
  if (diffSeconds < SECONDS_IN_MONTH) {
    const weeks = Math.floor(diffSeconds / SECONDS_IN_WEEK);
    return pluralize(weeks, 'week');
  }
  if (diffSeconds < SECONDS_IN_YEAR) {
    const months = Math.floor(diffSeconds / SECONDS_IN_MONTH);
    return pluralize(months, 'month');
  }
  const years = Math.floor(diffSeconds / SECONDS_IN_YEAR);
  return pluralize(years, 'year');
}

/**
 * Render an ISO 8601 timestamp as a localized full timestamp for the title
 * attribute (e.g. "12/1/2024, 7:14:38 PM"). Falls back to the input string if
 * Date parsing fails so we never crash a tooltip render.
 */
export function formatAbsoluteDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

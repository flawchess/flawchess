import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Parse a "YYYY-MM-DD" string (a full ISO 8601 timestamp also works — its
 * time part is ignored) into a Date (local time). */
function parseDate(d: string): Date {
  // Bug fix: callers pass full ISO timestamps too (e.g.
  // games.played_at "2026-07-20T12:00:00Z"); splitting the raw string on '-'
  // made the day component "20T12:00:00Z" -> NaN -> "Invalid Date".
  const datePart = d.split('T')[0] ?? d;
  const [year, month, day] = datePart.split('-');
  return new Date(Number(year), Number(month) - 1, Number(day));
}

/** Days between first and last date in a sorted YYYY-MM-DD array. */
function dateRangeDays(dates: string[]): number {
  if (dates.length < 2) return 0;
  // safe: length check above guarantees both indices are in bounds
  const first = parseDate(dates[0]!);
  const last = parseDate(dates[dates.length - 1]!);
  return Math.round((last.getTime() - first.getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * Returns a tick formatter that adapts to the date range:
 * - > 18 months: "Jan '24" (month + abbreviated year)
 * - > 2 months:  "Jan 5"   (month + day)
 * - <= 2 months: "Jan 5"   (month + day)
 */
export function createDateTickFormatter(sortedDates: string[]): (d: string) => string {
  const span = dateRangeDays(sortedDates);
  const EIGHTEEN_MONTHS = 18 * 30;

  if (span > EIGHTEEN_MONTHS) {
    return (d: string) => {
      const date = parseDate(d);
      const month = date.toLocaleDateString('en-US', { month: 'short' });
      const year = String(date.getFullYear()).slice(2);
      return `${month} '${year}`;
    };
  }

  return (d: string) => {
    return parseDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
}

/** Format a YYYY-MM-DD date with full year for tooltips. */
export function formatDateWithYear(d: string): string {
  return parseDate(d).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// Score over time charts share at least this range, so two openings' charts are drawn on the same
// scale and a quiet opening's wobbles are not stretched to fill the height. The axis widens in
// whole steps only when a line (or the baseline) goes outside it.
const Y_AXIS_MIN_RANGE_PCT: [number, number] = [30, 70];
const Y_AXIS_STEP_PCT = 10;
const PCT = 100;
const Y_AXIS_ROUNDING = 1e6;

/** Y-axis for score values in 0..1: at least 30-70%, widened in 10-point steps to fit the data. */
export function scoreOverTimeAxis(values: number[]): { domain: [number, number]; ticks: number[] } {
  const [minLo, minHi] = Y_AXIS_MIN_RANGE_PCT;
  // Round away float error first: 0.7 * 100 is 70.00000000000001, which would ceil to 80.
  const toSteps = (v: number): number =>
    Math.round(v * PCT * Y_AXIS_ROUNDING) / Y_AXIS_ROUNDING / Y_AXIS_STEP_PCT;
  const dataLo = Math.floor(toSteps(Math.min(...values, 1))) * Y_AXIS_STEP_PCT;
  const dataHi = Math.ceil(toSteps(Math.max(...values, 0))) * Y_AXIS_STEP_PCT;
  const lo = Math.max(0, Math.min(minLo, dataLo));
  const hi = Math.min(PCT, Math.max(minHi, dataHi));
  const ticks: number[] = [];
  for (let pct = lo; pct <= hi; pct += Y_AXIS_STEP_PCT) ticks.push(pct / PCT);
  return { domain: [lo / PCT, hi / PCT], ticks };
}

/**
 * Compute a nice y-axis domain and evenly-spaced ticks for Elo rating data.
 * Uses step candidates [50, 100, 200, 500]; picks the largest step where
 * range / step >= 4 (aim for 4-8 ticks).
 *
 * Fallbacks:
 * - empty values: { domain: ['auto', 'auto'], ticks: undefined } (Recharts auto-scale).
 * - all values equal: expand min -= 50, max += 50 so ticks are meaningful.
 */
export function niceEloAxis(
  values: number[],
): { domain: [number, number] | ['auto', 'auto']; ticks: number[] | undefined } {
  if (values.length === 0) {
    return { domain: ['auto', 'auto'], ticks: undefined };
  }

  let min = Math.min(...values);
  let max = Math.max(...values);

  // All values equal -> pad so ticks render.
  if (min === max) {
    min -= 50;
    max += 50;
  }

  const range = max - min;

  // Pick the largest step where range/step >= 4.
  const STEP_CANDIDATES = [50, 100, 200, 500];
  // Start at 50 (smallest) to avoid noUncheckedIndexedAccess widening.
  let step = 50;
  for (const candidate of STEP_CANDIDATES) {
    if (range / candidate >= 4) {
      step = candidate;
    }
  }

  const domainMin = Math.floor(min / step) * step;
  const domainMax = Math.ceil(max / step) * step;

  const ticks: number[] = [];
  for (let t = domainMin; t <= domainMax; t += step) {
    ticks.push(t);
  }

  return { domain: [domainMin, domainMax], ticks };
}

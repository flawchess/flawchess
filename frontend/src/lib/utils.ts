import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Parse a "YYYY-MM-DD" string into a Date (local time). */
function parseDate(d: string): Date {
  const [year, month, day] = d.split('-');
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

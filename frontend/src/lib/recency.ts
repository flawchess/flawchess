/**
 * Preset-to-date-range conversion utilities for the recency filter (Phase 92).
 *
 * The `Recency` closed string union has been renamed `RecencyPreset` to emphasise
 * that it is UI-only — the API wire shape uses `from_date`/`to_date` strings
 * instead of preset labels. Frontend owns "now" and converts preset names to
 * date bounds in the user's local timezone.
 *
 * Memoization rationale: `presetToDates` is called inside TanStack Query hook
 * bodies. If it returned a new `Date` object on every call, the serialised
 * queryKey would change on every render (millisecond precision), triggering
 * continuous refetches. Memoising on `(preset, today-as-YYYY-MM-DD-local)`
 * keeps query keys stable within a calendar day and produces a new key only
 * at midnight (Phase 92 §Pitfall 1).
 */

import {
  format,
  startOfDay,
  endOfDay,
  subWeeks,
  subMonths,
  subYears,
} from 'date-fns';
import type { RecencyPreset } from '@/types/api';

// Module-level cache: key = "${preset}|${YYYY-MM-DD}", value = date range.
// Intentionally unbounded — there are at most 8 presets × 1 key per calendar
// day, so the map never grows beyond a few dozen entries during a session.
const _cache = new Map<string, { from?: Date; to?: Date }>();

// Presets that map to a concrete sub-duration (excludes 'all' which means no filter).
type RangedPreset = Exclude<RecencyPreset, 'all'>;

/**
 * Map a RangedPreset to the sub-function result relative to `now`.
 * Exhaustive switch: adding a new preset without updating this function
 * is a TypeScript compile error (the `_exhaustive: never` catch-all fires).
 */
function _subForPreset(preset: RangedPreset, now: Date): Date {
  switch (preset) {
    case 'week':
      return subWeeks(now, 1);
    case 'month':
      return subMonths(now, 1);
    case '3months':
      return subMonths(now, 3);
    case '6months':
      return subMonths(now, 6);
    case 'year':
      return subYears(now, 1);
    case '3years':
      return subYears(now, 3);
    case '5years':
      return subYears(now, 5);
    default: {
      const _exhaustive: never = preset;
      return _exhaustive;
    }
  }
}

/**
 * Convert a RecencyPreset (or null) into a `{ from?, to? }` date range.
 *
 * Returns `{}` when `preset === null` or `preset === 'all'` (= no date filter).
 * Otherwise computes `from = startOfDay(now - delta)` and `to = endOfDay(now)`
 * in user-local timezone.
 *
 * Results are memoised on `(preset, today-YYYY-MM-DD-local)` so query keys are
 * stable within a calendar day.
 */
export function presetToDates(
  preset: RecencyPreset | null,
  now: Date = new Date(),
): { from?: Date; to?: Date } {
  if (preset === null || preset === 'all') return {};

  const todayKey = format(now, 'yyyy-MM-dd');
  const cacheKey = `${preset}|${todayKey}`;
  const cached = _cache.get(cacheKey);
  if (cached !== undefined) return cached;

  const to = endOfDay(now);
  const from = startOfDay(_subForPreset(preset, now));
  const result = { from, to };
  _cache.set(cacheKey, result);
  return result;
}

/**
 * Format a Date to the ISO `YYYY-MM-DD` wire string the backend expects.
 * Uses `date-fns` `format` which respects the user's local timezone — no
 * UTC drift. Returns `undefined` when the input is undefined.
 */
export function dateToWire(d: Date | undefined): string | undefined {
  if (d === undefined) return undefined;
  return format(d, 'yyyy-MM-dd');
}

/**
 * Build the `{ from_date?, to_date? }` wire params from a date range.
 * Omits keys whose value is undefined so the API never receives empty strings.
 * Mirrors `rangeToQueryParams` from `opponentStrength.ts`.
 */
export function dateRangeToWireParams(
  range: { from?: Date; to?: Date },
): { from_date?: string; to_date?: string } {
  const params: { from_date?: string; to_date?: string } = {};
  const fromWire = dateToWire(range.from);
  const toWire = dateToWire(range.to);
  if (fromWire !== undefined) params.from_date = fromWire;
  if (toWire !== undefined) params.to_date = toWire;
  return params;
}

// resolveDateRange is defined in Task 2 after FilterState gains the
// customRange field. It will be added to this file via Task 2's migration
// so that all consumers can import it from @/lib/recency.

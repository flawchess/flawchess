/**
 * Selection helpers for the three Flaws filter tags (facepalm / blunder / mistake).
 *
 * Deliberately NOT in hooks/useFlawFilterStore.ts: many component tests stub that module with
 * a factory exporting only `useFlawFilterStore`, so a helper exported from it would be
 * undefined in those tests as soon as a component imports it. This module is pure and never
 * mocked.
 */
import type { FlawSeverityFilter } from '@/types/library';

/** The three tags in display order (D-08): Facepalm, Blunder, Mistake. */
export const FLAW_SEVERITY_FILTER_VALUES: readonly FlawSeverityFilter[] = [
  'facepalm',
  'blunder',
  'mistake',
];

/**
 * True when the selection actually narrows the result set: at least one tag is selected and at
 * least one is not. Nothing selected and all three selected both show everything, so neither
 * lights the filter dot, gates the Games-tab request or reaches the Flaws-tab URL.
 */
export function isSeverityNarrowed(selection: readonly FlawSeverityFilter[]): boolean {
  const selected = FLAW_SEVERITY_FILTER_VALUES.filter((v) => selection.includes(v));
  return selected.length > 0 && selected.length < FLAW_SEVERITY_FILTER_VALUES.length;
}

/**
 * Keep only known tag values from raw (URL) input, de-duplicated, in input order. A stale or
 * hand-edited `?severity=` value never reaches the API.
 */
export function parseSeverityFilterParams(values: readonly string[]): FlawSeverityFilter[] {
  const out: FlawSeverityFilter[] = [];
  for (const value of values) {
    const known = FLAW_SEVERITY_FILTER_VALUES.find((v) => v === value);
    if (known && !out.includes(known)) out.push(known);
  }
  return out;
}

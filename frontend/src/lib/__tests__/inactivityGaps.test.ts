/**
 * Vitest unit tests for the computeInactivityGaps helper.
 *
 * Covers all behavior-block cases from 88.3-01-PLAN.md Task 1.
 * Pure function tests — no DOM environment needed.
 */

import { describe, it, expect } from 'vitest';
import { computeInactivityGaps, INACTIVITY_GAP_THRESHOLD_DAYS } from '../inactivityGaps';

// Helper: return an ISO YYYY-MM-DD string offset by n days from base.
function addDays(base: string, n: number): string {
  const d = new Date(base);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

const BASE = '2024-01-01';

describe('computeInactivityGaps', () => {
  it('returns [] for empty input', () => {
    expect(computeInactivityGaps([])).toEqual([]);
  });

  it('returns [] for a single date', () => {
    expect(computeInactivityGaps([BASE])).toEqual([]);
  });

  it('returns [] when all consecutive gaps are below the threshold (7 days apart)', () => {
    const dates = [
      BASE,
      addDays(BASE, 7),
      addDays(BASE, 14),
      addDays(BASE, 21),
    ];
    expect(computeInactivityGaps(dates)).toEqual([]);
  });

  it('returns one gap when exactly one pair is 57 days apart (above 56-day threshold)', () => {
    const dates = [BASE, addDays(BASE, 57)];
    const result = computeInactivityGaps(dates);
    expect(result).toHaveLength(1);
    expect(result[0]?.afterIndex).toBe(0);
    expect(result[0]?.gapDays).toBe(57);
  });

  it('does not return a gap when exactly at the threshold (56 days apart)', () => {
    const dates = [BASE, addDays(BASE, 56)];
    const result = computeInactivityGaps(dates);
    expect(result).toHaveLength(0);
  });

  it('label matches /^≈\\d+(\\.\\d)?y inactive$/ for gaps >= 365 days', () => {
    const dates = [BASE, addDays(BASE, 365)];
    const result = computeInactivityGaps(dates);
    expect(result).toHaveLength(1);
    expect(result[0]?.label).toMatch(/^≈\d+(\.\d)?y inactive$/);
  });

  it('label for exactly 365-day gap reads ≈1.0y inactive', () => {
    const dates = [BASE, addDays(BASE, 365)];
    const result = computeInactivityGaps(dates);
    expect(result[0]?.label).toBe('≈1.0y inactive');
  });

  it('label matches /^≈\\d+mo inactive$/ for gaps < 365 days and > threshold', () => {
    // 4 months ≈ 120 days
    const dates = [BASE, addDays(BASE, 120)];
    const result = computeInactivityGaps(dates);
    expect(result).toHaveLength(1);
    expect(result[0]?.label).toMatch(/^≈\d+mo inactive$/);
  });

  it('label for ~60 days reads ≈2mo inactive', () => {
    const dates = [BASE, addDays(BASE, 60)];
    const result = computeInactivityGaps(dates);
    expect(result[0]?.label).toBe('≈2mo inactive');
  });

  it('afterIndex always points to the date BEFORE the gap', () => {
    const dates = [
      BASE,
      addDays(BASE, 7),
      addDays(BASE, 7 + 180),  // gap after index 1
      addDays(BASE, 7 + 180 + 7),
    ];
    const result = computeInactivityGaps(dates);
    expect(result).toHaveLength(1);
    expect(result[0]?.afterIndex).toBe(1);
  });

  it('custom thresholdDays argument overrides the default constant', () => {
    // Use thresholdDays=10 so a 14-day gap is above threshold
    const dates = [BASE, addDays(BASE, 14)];
    const withDefault = computeInactivityGaps(dates);
    const withCustom = computeInactivityGaps(dates, 10);
    expect(withDefault).toHaveLength(0);  // 14 <= 56 default
    expect(withCustom).toHaveLength(1);   // 14 > 10 custom
  });

  it('INACTIVITY_GAP_THRESHOLD_DAYS constant is exported and equals 56', () => {
    expect(INACTIVITY_GAP_THRESHOLD_DAYS).toBe(56);
  });

  it('detects multiple gaps in a series', () => {
    const dates = [
      BASE,
      addDays(BASE, 7),
      addDays(BASE, 7 + 100),    // gap after index 1
      addDays(BASE, 7 + 100 + 7),
      addDays(BASE, 7 + 100 + 7 + 400),  // gap after index 3
    ];
    const result = computeInactivityGaps(dates);
    expect(result).toHaveLength(2);
    expect(result[0]?.afterIndex).toBe(1);
    expect(result[1]?.afterIndex).toBe(3);
  });
});

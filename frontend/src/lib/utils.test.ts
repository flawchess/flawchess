import { describe, it, expect } from 'vitest';
import { createDateTickFormatter, formatDateWithYear } from './utils';

describe('createDateTickFormatter', () => {
  // ── Long range (> 18 months) — format "Jan '24" ───────────────────────────
  it('returns month+year format for a range greater than 18 months', () => {
    const dates = ['2022-01-01', '2023-10-01']; // ~21 months apart
    const formatter = createDateTickFormatter(dates);
    const result = formatter('2023-06-15');
    // Should match "Mon 'YY" pattern
    expect(result).toMatch(/^[A-Z][a-z]{2} '\d{2}$/);
    expect(result).toBe("Jun '23");
  });

  it('formats January correctly in long-range mode', () => {
    const dates = ['2021-06-01', '2023-09-01']; // > 18 months
    const formatter = createDateTickFormatter(dates);
    expect(formatter('2024-01-01')).toBe("Jan '24");
  });

  it('uses abbreviated 2-digit year in long-range mode', () => {
    const dates = ['2020-01-01', '2022-05-01']; // > 18 months
    const formatter = createDateTickFormatter(dates);
    const result = formatter('2021-12-01');
    expect(result).toBe("Dec '21");
  });

  // ── Short range (<= 18 months) — format "Jan 5" ───────────────────────────
  it('returns month+day format for a range at the 18-month boundary (540 days)', () => {
    // The threshold is 18 * 30 = 540 days. A range of exactly 540 days is NOT > 540,
    // so it falls into the short format. 2023-01-01 to 2024-06-23 = exactly 540 days.
    const dates = ['2023-01-01', '2024-06-23']; // exactly 540 days (at boundary — short format)
    const formatter = createDateTickFormatter(dates);
    const result = formatter('2023-06-15');
    // Should match "Mon D" pattern (no year)
    expect(result).toMatch(/^[A-Z][a-z]{2} \d{1,2}$/);
    expect(result).toBe('Jun 15');
  });

  it('returns month+day format for a range less than 18 months', () => {
    const dates = ['2023-01-01', '2023-06-01']; // ~5 months
    const formatter = createDateTickFormatter(dates);
    expect(formatter('2023-03-07')).toBe('Mar 7');
  });

  // ── Edge cases ────────────────────────────────────────────────────────────
  it('returns short format for a single-element array (0-day span)', () => {
    const dates = ['2024-04-15'];
    const formatter = createDateTickFormatter(dates);
    expect(formatter('2024-04-15')).toBe('Apr 15');
  });

  it('does not throw for an empty array', () => {
    expect(() => {
      const formatter = createDateTickFormatter([]);
      formatter('2024-01-01');
    }).not.toThrow();
  });

  it('returns short format for empty array (0-day span defaults to short)', () => {
    const formatter = createDateTickFormatter([]);
    expect(formatter('2024-08-20')).toBe('Aug 20');
  });
});

describe('formatDateWithYear', () => {
  it('formats a known date as "Mon DD, YYYY"', () => {
    expect(formatDateWithYear('2024-06-15')).toBe('Jun 15, 2024');
  });

  it('formats January 1st correctly', () => {
    expect(formatDateWithYear('2023-01-01')).toBe('Jan 1, 2023');
  });

  it('formats December 31st correctly', () => {
    expect(formatDateWithYear('2022-12-31')).toBe('Dec 31, 2022');
  });
});

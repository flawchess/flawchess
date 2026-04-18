import { describe, it, expect } from 'vitest';
import { createDateTickFormatter, formatDateWithYear, niceEloAxis } from './utils';

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

describe('niceEloAxis', () => {
  it('returns auto domain and undefined ticks for empty input', () => {
    const result = niceEloAxis([]);
    expect(result.domain).toEqual(['auto', 'auto']);
    expect(result.ticks).toBeUndefined();
  });

  it('expands by +/-50 when all values are equal', () => {
    const result = niceEloAxis([1500, 1500, 1500]);
    // min=1450, max=1550 -> range=100 -> smallest step (50) gives 3 ticks at [1450,1500,1550]
    expect(result.domain).toEqual([1450, 1550]);
    expect(result.ticks).toEqual([1450, 1500, 1550]);
  });

  it('picks step=50 for small ranges (200 Elo)', () => {
    // values span 200 Elo -> 200 / 50 = 4 ticks, step=50 wins.
    const result = niceEloAxis([1400, 1500, 1600]);
    expect(result.domain).toEqual([1400, 1600]);
    expect(result.ticks).toEqual([1400, 1450, 1500, 1550, 1600]);
  });

  it('picks step=100 for medium ranges (~500 Elo)', () => {
    // range ~= 500 -> 500/100 = 5 (>=4, so step=100 picked over step=200 which would give 2.5).
    const result = niceEloAxis([1300, 1500, 1700, 1800]);
    // domainMin floor(1300/100)*100 = 1300, domainMax ceil(1800/100)*100 = 1800
    expect(result.domain).toEqual([1300, 1800]);
    expect(result.ticks).toEqual([1300, 1400, 1500, 1600, 1700, 1800]);
  });

  it('picks step=200 for large ranges (~1200 Elo)', () => {
    // range ~= 1200 -> 1200/200 = 6 (>=4); 1200/500 = 2.4 (<4); so step=200 wins.
    const result = niceEloAxis([1000, 2200]);
    expect(result.domain).toEqual([1000, 2200]);
    expect(result.ticks).toEqual([1000, 1200, 1400, 1600, 1800, 2000, 2200]);
  });

  it('handles non-aligned values by flooring/ceiling to step boundaries', () => {
    // 1347 and 1823 -> step=100 -> domain [1300, 1900].
    const result = niceEloAxis([1347, 1823]);
    expect(result.domain).toEqual([1300, 1900]);
    expect(result.ticks).toEqual([1300, 1400, 1500, 1600, 1700, 1800, 1900]);
  });
});

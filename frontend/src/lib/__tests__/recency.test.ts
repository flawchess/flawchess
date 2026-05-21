import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  presetToDates,
  dateToWire,
  dateRangeToWireParams,
} from '../recency';

// Restore real timers after each test that uses fake timers.
afterEach(() => {
  vi.useRealTimers();
});

describe('presetToDates', () => {
  it('Test 1: "week" returns from=startOfDay(now-1week) and to=endOfDay(now)', () => {
    const now = new Date(2026, 4, 21, 12, 0, 0); // 2026-05-21 12:00:00 local
    const result = presetToDates('week', now);
    expect(result.from).toBeDefined();
    expect(result.to).toBeDefined();
    // from should be start of day 7 days back
    const from = result.from!;
    expect(from.getHours()).toBe(0);
    expect(from.getMinutes()).toBe(0);
    expect(from.getSeconds()).toBe(0);
    expect(from.getMilliseconds()).toBe(0);
    // to should be end of day today
    const to = result.to!;
    expect(to.getHours()).toBe(23);
    expect(to.getMinutes()).toBe(59);
    expect(to.getSeconds()).toBe(59);
  });

  it('Test 2: "all" returns {}', () => {
    const result = presetToDates('all');
    expect(result).toEqual({});
    expect(result.from).toBeUndefined();
    expect(result.to).toBeUndefined();
  });

  it('Test 3: null returns {}', () => {
    const result = presetToDates(null);
    expect(result).toEqual({});
    expect(result.from).toBeUndefined();
    expect(result.to).toBeUndefined();
  });

  it('Test 4: two calls within the same calendar day return the same object reference (cache hit)', () => {
    const now1 = new Date(2026, 4, 21, 10, 0, 0);
    const now2 = new Date(2026, 4, 21, 18, 0, 0);
    const result1 = presetToDates('week', now1);
    const result2 = presetToDates('week', now2);
    // Same calendar day => same object reference
    expect(result1).toBe(result2);
  });

  it('Test 5: calls across different calendar days return different object references (cache miss)', () => {
    const day1 = new Date(2026, 4, 21, 12, 0, 0); // 2026-05-21
    const day2 = new Date(2026, 4, 22, 12, 0, 0); // 2026-05-22
    const result1 = presetToDates('week', day1);
    const result2 = presetToDates('week', day2);
    expect(result1).not.toBe(result2);
  });
});

describe('dateToWire', () => {
  it('Test 6: undefined returns undefined', () => {
    expect(dateToWire(undefined)).toBeUndefined();
  });

  it('Test 7: new Date(2026, 2, 1) returns "2026-03-01" (local-day format, no timezone leak)', () => {
    const d = new Date(2026, 2, 1); // March 1, 2026 in local time
    expect(dateToWire(d)).toBe('2026-03-01');
  });
});

describe('dateRangeToWireParams', () => {
  it('Test 8: {} returns {} (omits both keys when no bounds)', () => {
    const result = dateRangeToWireParams({});
    expect(result).toEqual({});
    expect(Object.keys(result)).toHaveLength(0);
  });

  it('Test 9: { from: new Date(2026, 2, 1) } returns { from_date: "2026-03-01" } with no to_date key', () => {
    const result = dateRangeToWireParams({ from: new Date(2026, 2, 1) });
    expect(result).toEqual({ from_date: '2026-03-01' });
    expect(result).not.toHaveProperty('to_date');
  });

  it('Test 10: { from, to } returns both from_date and to_date', () => {
    const result = dateRangeToWireParams({
      from: new Date(2026, 2, 1),
      to: new Date(2026, 3, 1),
    });
    expect(result).toEqual({
      from_date: '2026-03-01',
      to_date: '2026-04-01',
    });
  });
});

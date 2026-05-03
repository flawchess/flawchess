import { describe, it, expect } from 'vitest';
import { formatSignedSeconds, formatSignedPct1 } from '../clockFormat';

describe('formatSignedSeconds', () => {
  it('returns em-dash for null', () => {
    expect(formatSignedSeconds(null)).toBe('—');
  });

  it('returns +Xs for positive values (rounds)', () => {
    expect(formatSignedSeconds(24.4)).toBe('+24s');
    expect(formatSignedSeconds(24.6)).toBe('+25s');
    expect(formatSignedSeconds(-12.7)).toBe('-13s');
  });

  it('returns 0s for zero', () => {
    expect(formatSignedSeconds(0)).toBe('0s');
  });

  it('returns -Xs for negative values', () => {
    expect(formatSignedSeconds(-5)).toBe('-5s');
  });
});

describe('formatSignedPct1', () => {
  it('returns em-dash for null', () => {
    expect(formatSignedPct1(null)).toBe('—');
  });

  it('returns +X.X% for positive values', () => {
    expect(formatSignedPct1(8.234)).toBe('+8.2%');
    expect(formatSignedPct1(3.16)).toBe('+3.2%');
  });

  it('returns -X.X% for negative values', () => {
    expect(formatSignedPct1(-3.16)).toBe('-3.2%');
  });

  it('returns 0.0% for zero (no plus sign)', () => {
    // Choice: zero returns '0.0%' (not '+0.0%') — matches convention where
    // zero is neutral (neither positive nor negative clock advantage).
    expect(formatSignedPct1(0)).toBe('0.0%');
  });
});

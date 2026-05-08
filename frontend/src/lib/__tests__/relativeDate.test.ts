import { describe, it, expect } from 'vitest';
import { formatRelativeDate, formatAbsoluteDate } from '@/lib/relativeDate';

const NOW = new Date('2026-05-08T12:00:00Z');

function isoMinusSeconds(seconds: number): string {
  return new Date(NOW.getTime() - seconds * 1000).toISOString();
}

describe('formatRelativeDate', () => {
  it('renders "Just now" for sub-30-second deltas', () => {
    expect(formatRelativeDate(isoMinusSeconds(0), NOW)).toBe('Just now');
    expect(formatRelativeDate(isoMinusSeconds(29), NOW)).toBe('Just now');
  });

  it('clamps future timestamps to "Just now" (clock skew)', () => {
    const future = new Date(NOW.getTime() + 60 * 1000).toISOString();
    expect(formatRelativeDate(future, NOW)).toBe('Just now');
  });

  it('renders minutes with correct pluralisation', () => {
    // 31s under-renders to "1 minute" (Math.max(1, 0))
    expect(formatRelativeDate(isoMinusSeconds(31), NOW)).toBe('1 minute ago');
    expect(formatRelativeDate(isoMinusSeconds(60), NOW)).toBe('1 minute ago');
    expect(formatRelativeDate(isoMinusSeconds(5 * 60), NOW)).toBe('5 minutes ago');
  });

  it('renders hours', () => {
    expect(formatRelativeDate(isoMinusSeconds(60 * 60), NOW)).toBe('1 hour ago');
    expect(formatRelativeDate(isoMinusSeconds(3 * 60 * 60), NOW)).toBe('3 hours ago');
  });

  it('renders days', () => {
    expect(formatRelativeDate(isoMinusSeconds(24 * 60 * 60), NOW)).toBe('1 day ago');
    expect(formatRelativeDate(isoMinusSeconds(3 * 24 * 60 * 60), NOW)).toBe('3 days ago');
  });

  it('renders weeks', () => {
    expect(formatRelativeDate(isoMinusSeconds(7 * 24 * 60 * 60), NOW)).toBe('1 week ago');
    expect(formatRelativeDate(isoMinusSeconds(3 * 7 * 24 * 60 * 60), NOW)).toBe('3 weeks ago');
  });

  it('renders months', () => {
    expect(formatRelativeDate(isoMinusSeconds(30 * 24 * 60 * 60), NOW)).toBe('1 month ago');
    expect(formatRelativeDate(isoMinusSeconds(6 * 30 * 24 * 60 * 60), NOW)).toBe('6 months ago');
  });

  it('renders years', () => {
    expect(formatRelativeDate(isoMinusSeconds(365 * 24 * 60 * 60), NOW)).toBe('1 year ago');
    expect(formatRelativeDate(isoMinusSeconds(2 * 365 * 24 * 60 * 60), NOW)).toBe('2 years ago');
  });
});

describe('formatAbsoluteDate', () => {
  it('returns a non-empty localized string for a valid ISO timestamp', () => {
    const result = formatAbsoluteDate('2024-12-01T19:14:38Z');
    expect(result.length).toBeGreaterThan(0);
    expect(result).not.toBe('2024-12-01T19:14:38Z'); // should be reformatted
  });

  it('returns the input verbatim for an invalid date', () => {
    expect(formatAbsoluteDate('not-a-date')).toBe('not-a-date');
  });
});

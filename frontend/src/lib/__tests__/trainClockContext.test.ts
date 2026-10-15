import { describe, expect, it } from 'vitest';
import { clockContextLine } from '../trainClockContext';

describe('clockContextLine', () => {
  it('both known', () => {
    expect(clockContextLine(236.9, 13.0)).toBe('Played after 13s, with 3:56 left.');
  });

  it('clock only', () => {
    expect(clockContextLine(236, null)).toBe('Played with 3:56 left.');
  });

  it('think time only', () => {
    expect(clockContextLine(null, 13)).toBe('Played after 13s.');
  });

  it('neither known gives null', () => {
    expect(clockContextLine(null, null)).toBeNull();
  });

  it.each([
    [80, '1m 20s'],
    [120, '2m'],
    [59.6, '1m'],
    [12.6, '13s'],
    [0.3, '0s'],
  ])('think time %s formats as %s', (seconds, expected) => {
    expect(clockContextLine(null, seconds)).toBe(`Played after ${expected}.`);
  });

  it.each([
    [5.9, '0:05'],
    [0, '0:00'],
    [599.99, '9:59'],
    [3600, '1:00:00'],
    [5130.4, '1:25:30'],
  ])('clock %s formats as %s', (seconds, expected) => {
    expect(clockContextLine(seconds, null)).toBe(`Played with ${expected} left.`);
  });
});

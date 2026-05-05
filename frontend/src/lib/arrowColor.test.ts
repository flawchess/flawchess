import { describe, it, expect } from 'vitest';
import {
  getArrowColor,
  arrowSortKey,
  DARK_GREEN,
  DARK_RED,
  DARK_BLUE,
} from './arrowColor';

describe('getArrowColor (3-zone score palette, low-data → blue)', () => {
  describe('low-data fallback', () => {
    it('returns DARK_BLUE when gameCount < MIN_GAMES_FOR_COLOR (10), regardless of score', () => {
      expect(getArrowColor(0.65, 9, 'high')).toBe(DARK_BLUE);
      expect(getArrowColor(0.30, 9, 'high')).toBe(DARK_BLUE);
      expect(getArrowColor(0.50, 9, 'high')).toBe(DARK_BLUE);
      expect(getArrowColor(0.99, 5, 'high')).toBe(DARK_BLUE);
    });
  });

  describe('low-confidence fallback', () => {
    it('returns DARK_BLUE when confidence is "low", regardless of score or sample size', () => {
      expect(getArrowColor(0.65, 20, 'low')).toBe(DARK_BLUE);
      expect(getArrowColor(0.30, 20, 'low')).toBe(DARK_BLUE);
      expect(getArrowColor(0.80, 100, 'low')).toBe(DARK_BLUE);
    });
  });

  describe('reliable + neutral (0.45..0.55) zone', () => {
    it('returns DARK_BLUE at exact pivot 0.50', () => {
      expect(getArrowColor(0.50, 20, 'high')).toBe(DARK_BLUE);
    });

    it('returns DARK_BLUE just above 0.45 and just below 0.55', () => {
      expect(getArrowColor(0.451, 20, 'high')).toBe(DARK_BLUE);
      expect(getArrowColor(0.499, 20, 'high')).toBe(DARK_BLUE);
      expect(getArrowColor(0.501, 20, 'high')).toBe(DARK_BLUE);
      expect(getArrowColor(0.549, 20, 'high')).toBe(DARK_BLUE);
    });
  });

  describe('reliable + green zone (>= 0.55)', () => {
    it('returns DARK_GREEN at exact threshold 0.55', () => {
      expect(getArrowColor(0.55, 20, 'high')).toBe(DARK_GREEN);
    });

    it('returns DARK_GREEN at 0.60 and 0.80', () => {
      expect(getArrowColor(0.60, 20, 'high')).toBe(DARK_GREEN);
      expect(getArrowColor(0.80, 20, 'high')).toBe(DARK_GREEN);
    });
  });

  describe('reliable + red zone (<= 0.45)', () => {
    it('returns DARK_RED at exact threshold 0.45', () => {
      expect(getArrowColor(0.45, 20, 'high')).toBe(DARK_RED);
    });

    it('returns DARK_RED at 0.40 and 0.20', () => {
      expect(getArrowColor(0.40, 20, 'high')).toBe(DARK_RED);
      expect(getArrowColor(0.20, 20, 'high')).toBe(DARK_RED);
    });
  });

  describe('medium confidence', () => {
    it('returns the score-zone color when confidence is "medium" and sample is reliable', () => {
      expect(getArrowColor(0.60, 20, 'medium')).toBe(DARK_GREEN);
      expect(getArrowColor(0.40, 20, 'medium')).toBe(DARK_RED);
      expect(getArrowColor(0.50, 20, 'medium')).toBe(DARK_BLUE);
    });
  });
});

describe('arrowSortKey', () => {
  it('returns 0 for DARK_GREEN (drawn last = on top)', () => {
    expect(arrowSortKey(DARK_GREEN)).toBe(0);
  });

  it('returns 1 for DARK_RED', () => {
    expect(arrowSortKey(DARK_RED)).toBe(1);
  });

  it('returns 2 for DARK_BLUE', () => {
    expect(arrowSortKey(DARK_BLUE)).toBe(2);
  });

  it('returns 3 for unknown color string (fallback)', () => {
    expect(arrowSortKey('#123456')).toBe(3);
  });

  // Verify sort keys via getArrowColor round-trip
  it('green color from getArrowColor has sort key 0', () => {
    expect(arrowSortKey(getArrowColor(0.65, 20, 'high'))).toBe(0);
  });

  it('red color from getArrowColor has sort key 1', () => {
    expect(arrowSortKey(getArrowColor(0.20, 20, 'high'))).toBe(1);
  });

  it('blue color from getArrowColor (in-between) has sort key 2', () => {
    expect(arrowSortKey(getArrowColor(0.50, 20, 'high'))).toBe(2);
  });

  it('blue color from getArrowColor (low-data) has sort key 2', () => {
    expect(arrowSortKey(getArrowColor(0.65, 9, 'high'))).toBe(2);
  });

  it('blue color from getArrowColor (low-confidence) has sort key 2', () => {
    expect(arrowSortKey(getArrowColor(0.65, 100, 'low'))).toBe(2);
  });
});

import { describe, it, expect } from 'vitest';
import {
  getArrowColor,
  arrowSortKey,
  GREY,
  DARK_GREEN,
  DARK_RED,
  DARK_BLUE,
} from './arrowColor';

describe('getArrowColor (3-category score zones)', () => {
  describe('below-min-games guard', () => {
    it('returns GREY when gameCount < MIN_GAMES_FOR_COLOR (10) and not hovered', () => {
      expect(getArrowColor(0.65, 9, 'high', false)).toBe(GREY);
      expect(getArrowColor(0.30, 9, 'high', false)).toBe(GREY);
      expect(getArrowColor(0.50, 9, 'high', false)).toBe(GREY);
    });

    it('returns GREY when hovered, even below MIN_GAMES_FOR_COLOR', () => {
      expect(getArrowColor(0.65, 9, 'high', true)).toBe(GREY);
      expect(getArrowColor(0.30, 9, 'high', true)).toBe(GREY);
    });
  });

  describe('low-confidence guard', () => {
    it('returns GREY when confidence is low, regardless of score', () => {
      expect(getArrowColor(0.65, 20, 'low', false)).toBe(GREY);
      expect(getArrowColor(0.30, 20, 'low', false)).toBe(GREY);
      expect(getArrowColor(0.80, 100, 'low', false)).toBe(GREY);
    });

    it('returns GREY when hovered, even with low confidence', () => {
      expect(getArrowColor(0.65, 20, 'low', true)).toBe(GREY);
    });
  });

  describe('hover short-circuit', () => {
    it('returns GREY on hover regardless of score', () => {
      expect(getArrowColor(0.50, 20, 'high', true)).toBe(GREY);
      expect(getArrowColor(0.80, 20, 'high', true)).toBe(GREY);
      expect(getArrowColor(0.20, 20, 'high', true)).toBe(GREY);
    });
  });

  describe('neutral blue zone (0.45..0.55)', () => {
    it('returns DARK_BLUE at exact pivot 0.50', () => {
      expect(getArrowColor(0.50, 20, 'high', false)).toBe(DARK_BLUE);
    });

    it('returns DARK_BLUE just above 0.45 and just below 0.55', () => {
      expect(getArrowColor(0.451, 20, 'high', false)).toBe(DARK_BLUE);
      expect(getArrowColor(0.499, 20, 'high', false)).toBe(DARK_BLUE);
      expect(getArrowColor(0.501, 20, 'high', false)).toBe(DARK_BLUE);
      expect(getArrowColor(0.549, 20, 'high', false)).toBe(DARK_BLUE);
    });
  });

  describe('green zone (>= 0.55)', () => {
    it('returns DARK_GREEN at exact threshold 0.55', () => {
      expect(getArrowColor(0.55, 20, 'high', false)).toBe(DARK_GREEN);
    });

    it('returns DARK_GREEN at extreme score 0.80', () => {
      expect(getArrowColor(0.80, 20, 'high', false)).toBe(DARK_GREEN);
    });

    it('returns DARK_GREEN at 0.60 (was DARK_GREEN under old 5-bucket scheme too)', () => {
      expect(getArrowColor(0.60, 20, 'high', false)).toBe(DARK_GREEN);
    });
  });

  describe('red zone (<= 0.45)', () => {
    it('returns DARK_RED at exact threshold 0.45', () => {
      expect(getArrowColor(0.45, 20, 'high', false)).toBe(DARK_RED);
    });

    it('returns DARK_RED at 0.40', () => {
      expect(getArrowColor(0.40, 20, 'high', false)).toBe(DARK_RED);
    });

    it('returns DARK_RED at extreme score 0.20', () => {
      expect(getArrowColor(0.20, 20, 'high', false)).toBe(DARK_RED);
    });
  });

  describe('medium confidence', () => {
    it('returns colored arrow when confidence is medium and score is significant', () => {
      expect(getArrowColor(0.60, 20, 'medium', false)).toBe(DARK_GREEN);
      expect(getArrowColor(0.40, 20, 'medium', false)).toBe(DARK_RED);
      expect(getArrowColor(0.50, 20, 'medium', false)).toBe(DARK_BLUE);
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

  it('returns 3 for GREY (drawn first = bottom)', () => {
    expect(arrowSortKey(GREY)).toBe(3);
  });

  it('returns 3 for unknown color string (fallback)', () => {
    expect(arrowSortKey('#123456')).toBe(3);
  });

  // Verify sort keys via getArrowColor round-trip
  it('green color from getArrowColor has sort key 0', () => {
    expect(arrowSortKey(getArrowColor(0.65, 20, 'high', false))).toBe(0);
  });

  it('red color from getArrowColor has sort key 1', () => {
    expect(arrowSortKey(getArrowColor(0.20, 20, 'high', false))).toBe(1);
  });

  it('blue color from getArrowColor has sort key 2', () => {
    expect(arrowSortKey(getArrowColor(0.50, 20, 'high', false))).toBe(2);
  });

  it('grey (low-data) from getArrowColor has sort key 3', () => {
    expect(arrowSortKey(getArrowColor(0.65, 9, 'high', false))).toBe(3);
  });
});

import { describe, it, expect } from 'vitest';
import {
  getArrowColor,
  arrowSortKey,
  GREY,
  LIGHT_GREEN,
  DARK_GREEN,
  LIGHT_RED,
  DARK_RED,
  HOVER_BLUE,
} from './arrowColor';

describe('getArrowColor (Phase 76 — score-based)', () => {
  describe('below-min-games guard', () => {
    it('returns GREY when gameCount < MIN_GAMES_FOR_COLOR (10) and not hovered', () => {
      expect(getArrowColor(0.65, 9, false)).toBe(GREY);
      expect(getArrowColor(0.30, 9, false)).toBe(GREY);
    });

    it('returns HOVER_BLUE when hovered, even below MIN_GAMES_FOR_COLOR', () => {
      expect(getArrowColor(0.65, 9, true)).toBe(HOVER_BLUE);
      expect(getArrowColor(0.30, 9, true)).toBe(HOVER_BLUE);
    });
  });

  describe('hover short-circuit', () => {
    it('returns HOVER_BLUE on hover regardless of score', () => {
      expect(getArrowColor(0.50, 20, true)).toBe(HOVER_BLUE);
      expect(getArrowColor(0.80, 20, true)).toBe(HOVER_BLUE);
      expect(getArrowColor(0.20, 20, true)).toBe(HOVER_BLUE);
    });
  });

  describe('neutral grey zone (strict boundaries)', () => {
    it('returns GREY at exact pivot 0.50', () => {
      expect(getArrowColor(0.50, 20, false)).toBe(GREY);
    });

    it('returns GREY just above pivot but below MINOR threshold (0.55)', () => {
      expect(getArrowColor(0.501, 20, false)).toBe(GREY);
      expect(getArrowColor(0.549, 20, false)).toBe(GREY);
    });

    it('returns GREY just above LIGHT_RED threshold (<=0.45) — i.e. 0.451', () => {
      expect(getArrowColor(0.451, 20, false)).toBe(GREY);
      expect(getArrowColor(0.499, 20, false)).toBe(GREY);
    });
  });

  describe('green buckets (positive score)', () => {
    it('returns LIGHT_GREEN at exact MINOR threshold 0.55', () => {
      expect(getArrowColor(0.55, 20, false)).toBe(LIGHT_GREEN);
    });

    it('returns LIGHT_GREEN just below MAJOR threshold 0.60', () => {
      expect(getArrowColor(0.599, 20, false)).toBe(LIGHT_GREEN);
    });

    it('returns DARK_GREEN at exact MAJOR threshold 0.60', () => {
      expect(getArrowColor(0.60, 20, false)).toBe(DARK_GREEN);
    });

    it('returns DARK_GREEN at extreme score 0.80', () => {
      expect(getArrowColor(0.80, 20, false)).toBe(DARK_GREEN);
    });
  });

  describe('red buckets (negative score)', () => {
    it('returns LIGHT_RED at exact MINOR threshold 0.45', () => {
      expect(getArrowColor(0.45, 20, false)).toBe(LIGHT_RED);
    });

    it('returns LIGHT_RED just above MAJOR threshold 0.40 — i.e. 0.401', () => {
      expect(getArrowColor(0.401, 20, false)).toBe(LIGHT_RED);
    });

    it('returns DARK_RED at exact MAJOR threshold 0.40', () => {
      expect(getArrowColor(0.40, 20, false)).toBe(DARK_RED);
    });

    it('returns DARK_RED at extreme score 0.20', () => {
      expect(getArrowColor(0.20, 20, false)).toBe(DARK_RED);
    });
  });
});

describe('arrowSortKey', () => {
  it('returns -1 for HOVER_BLUE (hovered arrow always on top)', () => {
    expect(arrowSortKey(HOVER_BLUE)).toBe(-1);
  });

  it('returns 0 for DARK_GREEN (green sorts first/on top)', () => {
    expect(arrowSortKey(DARK_GREEN)).toBe(0);
  });

  it('returns 0 for LIGHT_GREEN', () => {
    expect(arrowSortKey(LIGHT_GREEN)).toBe(0);
  });

  it('returns 1 for DARK_RED (red sorts second)', () => {
    expect(arrowSortKey(DARK_RED)).toBe(1);
  });

  it('returns 1 for LIGHT_RED', () => {
    expect(arrowSortKey(LIGHT_RED)).toBe(1);
  });

  it('returns 2 for GREY (grey sorts last/bottom)', () => {
    expect(arrowSortKey(GREY)).toBe(2);
  });

  it('returns 2 for unknown color string (fallback)', () => {
    expect(arrowSortKey('#123456')).toBe(2);
  });

  // Verify sort keys via getArrowColor round-trip (new score-based signature)
  it('hovered color from getArrowColor has sort key -1', () => {
    expect(arrowSortKey(getArrowColor(0.65, 20, true))).toBe(-1);
  });

  it('green color from getArrowColor has sort key 0', () => {
    expect(arrowSortKey(getArrowColor(0.65, 20, false))).toBe(0);
  });

  it('red color from getArrowColor has sort key 1', () => {
    expect(arrowSortKey(getArrowColor(0.20, 20, false))).toBe(1);
  });

  it('grey color from getArrowColor has sort key 2', () => {
    expect(arrowSortKey(getArrowColor(0.50, 20, false))).toBe(2);
  });
});

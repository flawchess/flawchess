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

describe('getArrowColor', () => {
  // ── Few games guard ────────────────────────────────────────────────────────
  it('returns GREY when gameCount < 10', () => {
    expect(getArrowColor(80, 0, 9, false)).toBe(GREY);
  });

  it('returns HOVER_BLUE when gameCount < 10 and hovered', () => {
    expect(getArrowColor(80, 0, 9, true)).toBe(HOVER_BLUE);
  });

  // ── Hover always returns blue ─────────────────────────────────────────────
  it('returns HOVER_BLUE when hovered regardless of WDL', () => {
    expect(getArrowColor(50, 30, 20, true)).toBe(HOVER_BLUE);
    expect(getArrowColor(65, 20, 20, true)).toBe(HOVER_BLUE);
    expect(getArrowColor(20, 65, 20, true)).toBe(HOVER_BLUE);
    expect(getArrowColor(57, 20, 20, true)).toBe(HOVER_BLUE);
    expect(getArrowColor(20, 57, 20, true)).toBe(HOVER_BLUE);
  });

  // ── Neutral zone (grey 45-55%) ─────────────────────────────────────────────
  it('returns GREY for win rate 45-55% (neutral zone)', () => {
    expect(getArrowColor(50, 30, 20, false)).toBe(GREY);
  });

  it('returns GREY at exactly winPct=55 (boundary: 55 is still grey)', () => {
    expect(getArrowColor(55, 20, 20, false)).toBe(GREY);
  });

  // ── Light green (win rate 55-60%) ──────────────────────────────────────────
  it('returns LIGHT_GREEN at winPct=55.1 (just above threshold)', () => {
    expect(getArrowColor(55.1, 20, 20, false)).toBe(LIGHT_GREEN);
  });

  it('returns LIGHT_GREEN at winPct=57', () => {
    expect(getArrowColor(57, 20, 20, false)).toBe(LIGHT_GREEN);
  });

  it('returns LIGHT_GREEN at winPct just below 60', () => {
    expect(getArrowColor(59.9, 20, 20, false)).toBe(LIGHT_GREEN);
  });

  // ── Dark green (win rate 60%+) ─────────────────────────────────────────────
  it('returns DARK_GREEN at winPct=60', () => {
    expect(getArrowColor(60, 20, 20, false)).toBe(DARK_GREEN);
  });

  it('returns DARK_GREEN at winPct=65', () => {
    expect(getArrowColor(65, 20, 20, false)).toBe(DARK_GREEN);
  });

  it('returns DARK_GREEN at winPct=80', () => {
    expect(getArrowColor(80, 10, 20, false)).toBe(DARK_GREEN);
  });

  // ── Light red (loss rate 55-60%, i.e. win rate 40-45%) ────────────────────
  it('returns LIGHT_RED at lossPct=55.1 (just above threshold)', () => {
    expect(getArrowColor(20, 55.1, 20, false)).toBe(LIGHT_RED);
  });

  it('returns LIGHT_RED at lossPct=57 (win rate ~40-45%)', () => {
    expect(getArrowColor(20, 57, 20, false)).toBe(LIGHT_RED);
  });

  it('returns LIGHT_RED at lossPct just below 60', () => {
    expect(getArrowColor(20, 59.9, 20, false)).toBe(LIGHT_RED);
  });

  // ── Dark red (loss rate 60%+, i.e. win rate below 40%) ───────────────────
  it('returns DARK_RED at lossPct=60', () => {
    expect(getArrowColor(20, 60, 20, false)).toBe(DARK_RED);
  });

  it('returns DARK_RED at lossPct=65', () => {
    expect(getArrowColor(20, 65, 20, false)).toBe(DARK_RED);
  });

  // ── Boundary: exactly at threshold 55 ─────────────────────────────────────
  it('returns GREY at lossPct=55 (boundary: 55 is still grey)', () => {
    expect(getArrowColor(20, 55, 20, false)).toBe(GREY);
  });

  // ── Edge case: both winPct and lossPct exceed 55% ─────────────────────────
  it('returns DARK_GREEN when winPct=70 lossPct=60 (win dominates)', () => {
    expect(getArrowColor(70, 60, 20, false)).toBe(DARK_GREEN);
  });

  it('returns DARK_RED when winPct=57 lossPct=62 (loss dominates)', () => {
    expect(getArrowColor(57, 62, 20, false)).toBe(DARK_RED);
  });

  it('returns DARK_GREEN when winPct=65 lossPct=65 (equal — win wins)', () => {
    // When both are equal, green takes precedence (winPct >= lossPct rule)
    expect(getArrowColor(65, 65, 20, false)).toBe(DARK_GREEN);
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

  // Verify sort keys via getArrowColor round-trip
  it('hovered color from getArrowColor has sort key -1', () => {
    expect(arrowSortKey(getArrowColor(65, 10, 20, true))).toBe(-1);
  });

  it('green color from getArrowColor has sort key 0', () => {
    expect(arrowSortKey(getArrowColor(65, 10, 20, false))).toBe(0);
  });

  it('red color from getArrowColor has sort key 1', () => {
    expect(arrowSortKey(getArrowColor(10, 65, 20, false))).toBe(1);
  });

  it('grey color from getArrowColor has sort key 2', () => {
    expect(arrowSortKey(getArrowColor(40, 20, 20, false))).toBe(2);
  });
});

import { describe, it, expect } from 'vitest';
import { getArrowColor, arrowSortKey } from './arrowColor';

// Helper to parse oklch components from "oklch(L C H)" string
function parseOklch(color: string): { l: number; c: number; h: number } {
  const match = color.match(/oklch\(([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\)/);
  if (!match) throw new Error(`Invalid oklch string: ${color}`);
  return { l: parseFloat(match[1]), c: parseFloat(match[2]), h: parseFloat(match[3]) };
}

describe('getArrowColor', () => {
  // ── Few games guard ────────────────────────────────────────────────────────
  it('returns grey when gameCount < 10', () => {
    const color = getArrowColor(80, 0, 9, false);
    const { l, c } = parseOklch(color);
    expect(c).toBeLessThan(0.05); // grey has near-zero chroma
    expect(l).toBeGreaterThan(0.5);
  });

  it('returns grey hover when gameCount < 10 and hovered', () => {
    const color = getArrowColor(80, 0, 9, true);
    const { l, c } = parseOklch(color);
    expect(c).toBeLessThan(0.05);
    expect(l).toBeGreaterThan(0.8); // hover is lighter
  });

  // ── Neutral zone (both <= 55) ──────────────────────────────────────────────
  it('returns grey when winPct=50 lossPct=30 (neutral)', () => {
    const color = getArrowColor(50, 30, 20, false);
    const { c } = parseOklch(color);
    expect(c).toBeLessThan(0.05);
  });

  it('returns grey when winPct=55 lossPct=55 (both at gradient start)', () => {
    const color = getArrowColor(55, 55, 20, false);
    const { c } = parseOklch(color);
    expect(c).toBeLessThan(0.05);
  });

  // ── Green gradient ─────────────────────────────────────────────────────────
  it('returns grey at winPct=55 (t=0)', () => {
    const color = getArrowColor(55, 20, 20, false);
    const { c } = parseOklch(color);
    expect(c).toBeLessThan(0.05);
  });

  it('returns full green at winPct=65 (t=1)', () => {
    const color = getArrowColor(65, 20, 20, false);
    const { l, c, h } = parseOklch(color);
    expect(c).toBeCloseTo(0.16, 2);
    expect(h).toBeCloseTo(145, 0);
    expect(l).toBeCloseTo(0.45, 2);
  });

  it('returns full green at winPct=75 (t clamped to 1)', () => {
    const color = getArrowColor(75, 10, 20, false);
    const { c, h } = parseOklch(color);
    expect(c).toBeCloseTo(0.16, 2);
    expect(h).toBeCloseTo(145, 0);
  });

  it('returns midpoint green at winPct=60 (t=0.5)', () => {
    const color = getArrowColor(60, 20, 20, false);
    const { l, c, h } = parseOklch(color);
    // t=0.5 interpolation between grey(L=0.75,C=0.01,H=260) and green(L=0.45,C=0.16,H=145)
    expect(l).toBeCloseTo(0.6, 1);    // (0.75+0.45)/2 = 0.60
    expect(c).toBeCloseTo(0.085, 1);  // (0.01+0.16)/2 = 0.085 (1 decimal = ±0.05 tolerance)
    expect(h).toBeCloseTo(202.5, 0);  // (260+145)/2 = 202.5
  });

  // ── Red gradient ───────────────────────────────────────────────────────────
  it('returns grey at lossPct=55 (t=0)', () => {
    const color = getArrowColor(20, 55, 20, false);
    const { c } = parseOklch(color);
    expect(c).toBeLessThan(0.05);
  });

  it('returns full red at lossPct=65 (t=1)', () => {
    const color = getArrowColor(20, 65, 20, false);
    const { l, c, h } = parseOklch(color);
    expect(c).toBeCloseTo(0.17, 2);
    expect(h).toBeCloseTo(25, 0);
    expect(l).toBeCloseTo(0.45, 2);
  });

  it('returns midpoint red at lossPct=60 (t=0.5)', () => {
    const color = getArrowColor(20, 60, 20, false);
    const { l, c, h } = parseOklch(color);
    expect(l).toBeCloseTo(0.6, 1);    // (0.75+0.45)/2 = 0.60
    expect(c).toBeCloseTo(0.09, 2);   // (0.01+0.17)/2 = 0.09
    expect(h).toBeCloseTo(142.5, 0);  // (260+25)/2 = 142.5
  });

  // ── Hover variants (boosted lightness) ─────────────────────────────────────
  it('hover grey has boosted lightness', () => {
    const normal = parseOklch(getArrowColor(50, 20, 20, false));
    const hover = parseOklch(getArrowColor(50, 20, 20, true));
    expect(hover.l).toBeGreaterThan(normal.l);
    expect(hover.l).toBeCloseTo(0.9, 1); // grey hover endpoint
  });

  it('hover full green has boosted lightness', () => {
    const normal = parseOklch(getArrowColor(65, 10, 20, false));
    const hover = parseOklch(getArrowColor(65, 10, 20, true));
    expect(hover.l).toBeGreaterThan(normal.l);
    expect(hover.l).toBeCloseTo(0.6, 1); // green hover endpoint
  });

  it('hover full red has boosted lightness', () => {
    const normal = parseOklch(getArrowColor(10, 65, 20, false));
    const hover = parseOklch(getArrowColor(10, 65, 20, true));
    expect(hover.l).toBeGreaterThan(normal.l);
    expect(hover.l).toBeCloseTo(0.6, 1); // red hover endpoint
  });

  // ── Edge case: both winPct and lossPct > 55 ────────────────────────────────
  it('prioritizes higher t when both win and loss > 55', () => {
    // winPct=70 (t=1.0), lossPct=60 (t=0.5) — win dominates -> should be green
    const color = getArrowColor(70, 60, 20, false);
    const { h } = parseOklch(color);
    expect(h).toBeCloseTo(145, 0); // green hue
  });

  it('prioritizes loss when loss t is higher', () => {
    // winPct=57 (t=0.2), lossPct=62 (t=0.7) — loss dominates -> should be red-ish
    // At t=0.7: hue = lerp(260, 25, 0.7) = 95.5 (between grey and red)
    const color = getArrowColor(57, 62, 20, false);
    const { c, h } = parseOklch(color);
    // chroma should be positive (colored, not grey)
    expect(c).toBeGreaterThan(0.05);
    // hue should be in the grey-to-red interpolation range (between 25 and 260)
    // and should not be in the green range (< 145 hue from red side)
    expect(h).toBeLessThan(200); // not in green territory (green hue = 145, grey = 260)
    expect(h).toBeGreaterThan(25); // interpolated, not yet fully red
  });
});

describe('arrowSortKey', () => {
  it('returns 0 for green-ish colors (green sorts first)', () => {
    const green = getArrowColor(65, 10, 20, false);
    expect(arrowSortKey(green)).toBe(0);
  });

  it('returns 1 for red-ish colors (red sorts second)', () => {
    const red = getArrowColor(10, 65, 20, false);
    expect(arrowSortKey(red)).toBe(1);
  });

  it('returns 2 for grey-ish colors (grey sorts last)', () => {
    const grey = getArrowColor(40, 20, 20, false);
    expect(arrowSortKey(grey)).toBe(2);
  });

  it('returns 0 for hover green', () => {
    const greenHover = getArrowColor(65, 10, 20, true);
    expect(arrowSortKey(greenHover)).toBe(0);
  });

  it('returns 1 for hover red', () => {
    const redHover = getArrowColor(10, 65, 20, true);
    expect(arrowSortKey(redHover)).toBe(1);
  });

  it('returns 2 for hover grey', () => {
    const greyHover = getArrowColor(40, 20, 20, true);
    expect(arrowSortKey(greyHover)).toBe(2);
  });
});

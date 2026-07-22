/**
 * botStyleBundles.ts unit tests (Phase 182, STYLE-01/02/03/04, D-02).
 *
 * Structural + identity invariants over the 4 shipped style bundles — NOT a
 * re-test of `botStyle.ts`'s pure transforms (already covered by
 * `botStyle.test.ts`) or `styleOpeningLines.ts`'s corpus membership (already
 * covered by `styleOpeningLines.test.ts`). This file only proves the
 * bundles themselves are well-formed data and match their documented
 * per-style identity from `182-CONTEXT.md`.
 */

import { describe, it, expect } from 'vitest';
import {
  ATTACKER_STYLE,
  TRICKSTER_STYLE,
  GRINDER_STYLE,
  WALL_STYLE,
  BOT_STYLE_BUNDLES,
} from '../botStyleBundles';
import { styleLinesFor, type Style } from '../styleOpeningLines';
import type { BotStyleParams } from '../botStyle';

const ALL_STYLES: Style[] = ['Attacker', 'Trickster', 'Grinder', 'Wall'];

const FEATURE_KEYS = [
  'isCheck',
  'isCapture',
  'isPawnAdvance',
  'isPawnStorm',
  'isExchange',
  'isRetreat',
] as const;

/** Recursively asserts no function-typed field exists anywhere in `style` (D-01/BOT-03). */
function assertNoFunctionFields(style: BotStyleParams): void {
  for (const [key, value] of Object.entries(style)) {
    if (key === 'featureMultipliers') {
      for (const [fmKey, fmValue] of Object.entries(value as Record<string, unknown>)) {
        expect(typeof fmValue, `featureMultipliers.${fmKey}`).not.toBe('function');
        expect(typeof fmValue, `featureMultipliers.${fmKey}`).toBe('number');
      }
      continue;
    }
    expect(typeof value, key).not.toBe('function');
    expect(typeof value, key).toBe('number');
  }
}

describe('BOT_STYLE_BUNDLES', () => {
  it('has exactly the 4 named style keys', () => {
    expect(Object.keys(BOT_STYLE_BUNDLES).sort()).toEqual([...ALL_STYLES].sort());
  });

  it.each(ALL_STYLES)('%s bundle has no function-typed field', (style) => {
    assertNoFunctionFields(BOT_STYLE_BUNDLES[style]);
  });

  it.each(ALL_STYLES)('%s bundle defines every FeatureMultipliers key as a finite number', (style) => {
    const bundle = BOT_STYLE_BUNDLES[style];
    for (const key of FEATURE_KEYS) {
      expect(Number.isFinite(bundle.featureMultipliers[key]), key).toBe(true);
    }
  });

  it.each(ALL_STYLES)('%s bundle carries a bookBoost in the D-06 ~20-50 range', (style) => {
    const bundle = BOT_STYLE_BUNDLES[style];
    expect(bundle.bookBoost).toBeGreaterThanOrEqual(20);
    expect(bundle.bookBoost).toBeLessThanOrEqual(50);
  });

  it.each(ALL_STYLES)(
    '%s bundle references a non-empty curated book set for at least one color',
    (style) => {
      const whiteLines = styleLinesFor(style, 'w');
      const blackLines = styleLinesFor(style, 'b');
      expect(whiteLines.size > 0 || blackLines.size > 0).toBe(true);
    },
  );

  // ─── Identity assertions (182-CONTEXT.md specifics) ────────────────────

  it('Grinder has positive contempt (avoids draws) and Wall has negative contempt (welcomes them slightly early) — D-09', () => {
    expect(GRINDER_STYLE.contempt).toBeGreaterThan(0);
    expect(WALL_STYLE.contempt).toBeLessThan(0);
  });

  it("Attacker's check and capture multipliers are greater than 1 (D-06 identity)", () => {
    expect(ATTACKER_STYLE.featureMultipliers.isCheck).toBeGreaterThan(1);
    expect(ATTACKER_STYLE.featureMultipliers.isCapture).toBeGreaterThan(1);
  });

  it("Grinder's exchange multiplier is greater than 1 (D-06 identity: trade-happy)", () => {
    expect(GRINDER_STYLE.featureMultipliers.isExchange).toBeGreaterThan(1);
  });

  it("Wall's exchange multiplier is greater than 1 and pawn-storm multiplier is less than 1 (D-06 identity: simplifying, never storms)", () => {
    expect(WALL_STYLE.featureMultipliers.isExchange).toBeGreaterThan(1);
    expect(WALL_STYLE.featureMultipliers.isPawnStorm).toBeLessThan(1);
  });

  it('Grinder never resigns early: threshold is far below the other 3 styles\' resign floor (D-08)', () => {
    expect(GRINDER_STYLE.threshold).toBeLessThan(ATTACKER_STYLE.threshold);
    expect(GRINDER_STYLE.threshold).toBeLessThan(TRICKSTER_STYLE.threshold);
    expect(GRINDER_STYLE.threshold).toBeLessThan(WALL_STYLE.threshold);
    expect(GRINDER_STYLE.hysteresisFloor).toBeGreaterThan(ATTACKER_STYLE.hysteresisFloor);
  });

  it('Trickster has the highest varianceBonus of the 4 styles (defining high-variance/swindle trait)', () => {
    const others = [ATTACKER_STYLE.varianceBonus, GRINDER_STYLE.varianceBonus, WALL_STYLE.varianceBonus];
    expect(others.every((v) => TRICKSTER_STYLE.varianceBonus > v)).toBe(true);
  });

  it('Wall has the lowest (most negative) varianceBonus of the 4 styles (defining flat/quiet trait)', () => {
    const others = [ATTACKER_STYLE.varianceBonus, GRINDER_STYLE.varianceBonus, TRICKSTER_STYLE.varianceBonus];
    expect(others.every((v) => WALL_STYLE.varianceBonus < v)).toBe(true);
  });
});

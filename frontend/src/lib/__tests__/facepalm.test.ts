/**
 * facepalm.ts unit tests: score units, the cut and the shared score meaning copy.
 */

import { describe, expect, it } from 'vitest';
import {
  FACEPALM_HIGH_CUTOFF,
  FACEPALM_PCT_MAX,
  FACEPALM_PCT_MIN,
  toFacepalmPct,
  isFacepalmBlunder,
  facepalmScoreMeaning,
  facepalmScoreLabel,
} from '../facepalm';

// Local scale for building scores from a whole-percent cut (never the cut as a literal, D-21).
const PCT_SCALE = 100;

describe('named constants', () => {
  it('whole-percent scale is 0..100', () => {
    expect(FACEPALM_PCT_MIN).toBe(0);
    expect(FACEPALM_PCT_MAX).toBe(100);
  });
});

describe('facepalmScoreMeaning', () => {
  it('names the level of whoever played the blunder', () => {
    expect(facepalmScoreMeaning()).toContain('a player at your level');
    expect(facepalmScoreMeaning('opponent')).toContain('a player at their level');
  });
});

describe('facepalmScoreLabel', () => {
  it('names a facepalm blunder "Facepalm N%, type"', () => {
    const score = (FACEPALM_HIGH_CUTOFF + 10) / PCT_SCALE;
    expect(facepalmScoreLabel(score, 'allowed_loss')).toBe(
      `Facepalm ${toFacepalmPct(score)}%, allowed loss`,
    );
  });

  it('names an ordinary blunder "Blunder, facepalm score N%, type"', () => {
    const score = (FACEPALM_HIGH_CUTOFF - 10) / PCT_SCALE;
    expect(facepalmScoreLabel(score, 'missed_win')).toBe(
      `Blunder, facepalm score ${toFacepalmPct(score)}%, missed win`,
    );
  });
});

describe('isFacepalmBlunder', () => {
  it('uses the floored percent against the cut', () => {
    expect(isFacepalmBlunder((FACEPALM_HIGH_CUTOFF + 1) / PCT_SCALE)).toBe(true);
    expect(isFacepalmBlunder((FACEPALM_HIGH_CUTOFF - 1) / PCT_SCALE)).toBe(false);
    expect(isFacepalmBlunder(1)).toBe(true);
  });

  it('counts the cut itself', () => {
    expect(isFacepalmBlunder(FACEPALM_HIGH_CUTOFF / PCT_SCALE)).toBe(true);
  });

  it('is false for an unscored blunder', () => {
    expect(isFacepalmBlunder(null)).toBe(false);
    expect(isFacepalmBlunder(undefined)).toBe(false);
  });
});

describe('toFacepalmPct', () => {
  it('floors the score to a whole percent', () => {
    expect(toFacepalmPct(0.946)).toBe(94);
    expect(toFacepalmPct(0.697)).toBe(69);
    expect(toFacepalmPct(0.27)).toBe(27);
  });

  it('floors the float4 0.70 as the API serves it to 69', () => {
    expect(toFacepalmPct(0.699999988079071)).toBe(69);
  });

  it('keeps the domain edges', () => {
    expect(toFacepalmPct(1)).toBe(100);
    expect(toFacepalmPct(0)).toBe(0);
  });

  it('clamps out-of-range scores into 0..100', () => {
    expect(toFacepalmPct(1.2)).toBe(100);
    expect(toFacepalmPct(-0.1)).toBe(0);
  });
});

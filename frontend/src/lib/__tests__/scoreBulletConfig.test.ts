import { describe, it, expect } from 'vitest';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MIN,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_DOMAIN,
  clampScoreCi,
} from '../scoreBulletConfig';

describe('scoreBulletConfig', () => {
  it('center is 0.5', () => {
    expect(SCORE_BULLET_CENTER).toBe(0.5);
  });

  it('neutral zone is symmetric and non-empty', () => {
    expect(SCORE_BULLET_NEUTRAL_MIN).toBeLessThan(0);
    expect(SCORE_BULLET_NEUTRAL_MAX).toBeGreaterThan(0);
  });

  it('domain stays inside [0, 1] when applied to center', () => {
    expect(SCORE_BULLET_CENTER - SCORE_BULLET_DOMAIN).toBeGreaterThanOrEqual(0);
    expect(SCORE_BULLET_CENTER + SCORE_BULLET_DOMAIN).toBeLessThanOrEqual(1);
  });
});

describe('clampScoreCi', () => {
  it('clamps below 0', () => {
    expect(clampScoreCi(-0.1)).toBe(0);
  });

  it('clamps above 1', () => {
    expect(clampScoreCi(1.2)).toBe(1);
  });

  it('passes through values inside [0, 1]', () => {
    expect(clampScoreCi(0)).toBe(0);
    expect(clampScoreCi(0.5)).toBe(0.5);
    expect(clampScoreCi(1)).toBe(1);
  });
});

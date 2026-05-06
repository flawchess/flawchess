import { describe, it, expect } from 'vitest';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MIN,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_DOMAIN,
  SCORE_BULLET_DOMAIN_WIDE,
  clampScoreCi,
  scoreBulletDomain,
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

describe('scoreBulletDomain', () => {
  it('returns the default (tighter) domain when CI fits inside [0.3, 0.7]', () => {
    expect(scoreBulletDomain(0.4, 0.6)).toBe(SCORE_BULLET_DOMAIN);
    expect(scoreBulletDomain(0.3, 0.7)).toBe(SCORE_BULLET_DOMAIN);
  });

  it('returns the wide domain when CI low overflows the default window', () => {
    expect(scoreBulletDomain(0.29, 0.6)).toBe(SCORE_BULLET_DOMAIN_WIDE);
  });

  it('returns the wide domain when CI high overflows the default window', () => {
    expect(scoreBulletDomain(0.4, 0.71)).toBe(SCORE_BULLET_DOMAIN_WIDE);
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

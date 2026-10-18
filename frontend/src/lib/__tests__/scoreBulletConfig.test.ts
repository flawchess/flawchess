import { describe, it, expect } from 'vitest';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MIN,
  SCORE_BULLET_NEUTRAL_MAX,
} from '../scoreBulletConfig';

describe('scoreBulletConfig', () => {
  it('center is 0.5', () => {
    expect(SCORE_BULLET_CENTER).toBe(0.5);
  });

  it('neutral zone is symmetric and non-empty', () => {
    expect(SCORE_BULLET_NEUTRAL_MIN).toBeLessThan(0);
    expect(SCORE_BULLET_NEUTRAL_MAX).toBeGreaterThan(0);
  });
});

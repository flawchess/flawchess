import { describe, it, expect } from 'vitest';
import {
  EVAL_NEUTRAL_MIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_ENDGAME_NEUTRAL_MIN_PAWNS,
  EVAL_ENDGAME_NEUTRAL_MAX_PAWNS,
  EVAL_ENDGAME_BULLET_DOMAIN_PAWNS,
} from '../openingStatsZones';

describe('openingStatsZones — MG-entry calibration (D-07)', () => {
  it('EVAL_NEUTRAL_MIN_PAWNS equals -0.20', () => {
    expect(EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.20);
  });
  it('EVAL_NEUTRAL_MAX_PAWNS equals +0.20', () => {
    expect(EVAL_NEUTRAL_MAX_PAWNS).toBe(0.20);
  });
  it('EVAL_BULLET_DOMAIN_PAWNS equals 1.50', () => {
    expect(EVAL_BULLET_DOMAIN_PAWNS).toBe(1.5);
  });
  it('MG neutral zone is symmetric around zero', () => {
    expect(EVAL_NEUTRAL_MAX_PAWNS).toBe(-EVAL_NEUTRAL_MIN_PAWNS);
  });
  it('MG domain strictly encloses neutral zone', () => {
    expect(EVAL_BULLET_DOMAIN_PAWNS).toBeGreaterThan(EVAL_NEUTRAL_MAX_PAWNS);
    expect(EVAL_BULLET_DOMAIN_PAWNS).toBeGreaterThan(-EVAL_NEUTRAL_MIN_PAWNS);
  });
});

describe('openingStatsZones — EG-entry calibration (D-09)', () => {
  it('EVAL_ENDGAME_NEUTRAL_MIN_PAWNS equals -0.35', () => {
    expect(EVAL_ENDGAME_NEUTRAL_MIN_PAWNS).toBe(-0.35);
  });
  it('EVAL_ENDGAME_NEUTRAL_MAX_PAWNS equals +0.35', () => {
    expect(EVAL_ENDGAME_NEUTRAL_MAX_PAWNS).toBe(0.35);
  });
  it('EVAL_ENDGAME_BULLET_DOMAIN_PAWNS equals 3.50', () => {
    expect(EVAL_ENDGAME_BULLET_DOMAIN_PAWNS).toBe(3.5);
  });
  it('EG neutral zone is symmetric around zero', () => {
    expect(EVAL_ENDGAME_NEUTRAL_MAX_PAWNS).toBe(-EVAL_ENDGAME_NEUTRAL_MIN_PAWNS);
  });
  it('EG domain strictly encloses EG neutral zone', () => {
    expect(EVAL_ENDGAME_BULLET_DOMAIN_PAWNS).toBeGreaterThan(EVAL_ENDGAME_NEUTRAL_MAX_PAWNS);
  });
});

describe('openingStatsZones — cross-phase invariants', () => {
  it('EG domain wider than MG domain (endgame entries are higher-variance)', () => {
    expect(EVAL_ENDGAME_BULLET_DOMAIN_PAWNS).toBeGreaterThan(EVAL_BULLET_DOMAIN_PAWNS);
  });
});

import { describe, it, expect } from 'vitest';
import {
  EVAL_NEUTRAL_MIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_BASELINE_PAWNS_WHITE,
  EVAL_BASELINE_PAWNS_BLACK,
  evalZoneColor,
} from '../openingStatsZones';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

describe('openingStatsZones — MG-entry calibration (D-07 / 260504-my2)', () => {
  it('EVAL_NEUTRAL_MIN_PAWNS equals -0.25', () => {
    expect(EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.25);
  });
  it('EVAL_NEUTRAL_MAX_PAWNS equals +0.25', () => {
    expect(EVAL_NEUTRAL_MAX_PAWNS).toBe(0.25);
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

describe('openingStatsZones — baseline pawn fallbacks (260504-my2)', () => {
  it('EVAL_BASELINE_PAWNS_WHITE equals +0.315', () => {
    expect(EVAL_BASELINE_PAWNS_WHITE).toBe(0.315);
  });
  it('EVAL_BASELINE_PAWNS_BLACK equals -0.189', () => {
    expect(EVAL_BASELINE_PAWNS_BLACK).toBe(-0.189);
  });
});

describe('evalZoneColor — baseline-centered (260504-my2)', () => {
  it('value within ±0.25 of center returns ZONE_NEUTRAL (white baseline)', () => {
    // delta = 0.50 - 0.32 = 0.18 -> inside ±0.25
    expect(evalZoneColor(0.50, 0.32)).toBe(ZONE_NEUTRAL);
  });

  it('value at least +0.25 above center returns ZONE_SUCCESS', () => {
    // delta = 0.60 - 0.32 = 0.28 -> >= 0.25
    expect(evalZoneColor(0.60, 0.32)).toBe(ZONE_SUCCESS);
  });

  it('value at least -0.25 below center returns ZONE_DANGER', () => {
    // delta = 0.05 - 0.32 = -0.27 -> <= -0.25
    expect(evalZoneColor(0.05, 0.32)).toBe(ZONE_DANGER);
  });

  it('default-center sanity: value=0, center=0 returns ZONE_NEUTRAL', () => {
    expect(evalZoneColor(0, 0)).toBe(ZONE_NEUTRAL);
  });

  it('black baseline near-zero delta returns ZONE_NEUTRAL', () => {
    // delta = -0.20 - (-0.19) = -0.01 -> inside ±0.25
    expect(evalZoneColor(-0.20, -0.19)).toBe(ZONE_NEUTRAL);
  });
});

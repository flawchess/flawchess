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
  it('EVAL_NEUTRAL_MIN_PAWNS equals -0.30', () => {
    expect(EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.30);
  });
  it('EVAL_NEUTRAL_MAX_PAWNS equals +0.30', () => {
    expect(EVAL_NEUTRAL_MAX_PAWNS).toBe(0.30);
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

describe('openingStatsZones — baseline pawn fallbacks (symmetric, 260504-rvh)', () => {
  it('EVAL_BASELINE_PAWNS_WHITE equals +0.25', () => {
    expect(EVAL_BASELINE_PAWNS_WHITE).toBe(0.25);
  });
  it('EVAL_BASELINE_PAWNS_BLACK equals -0.25', () => {
    expect(EVAL_BASELINE_PAWNS_BLACK).toBe(-0.25);
  });
  it('baselines are symmetric around 0', () => {
    expect(EVAL_BASELINE_PAWNS_WHITE).toBe(-EVAL_BASELINE_PAWNS_BLACK);
  });
});

describe('evalZoneColor — zero-centered (260504-rvh)', () => {
  it('value within ±0.30 returns ZONE_NEUTRAL', () => {
    expect(evalZoneColor(0)).toBe(ZONE_NEUTRAL);
    expect(evalZoneColor(0.10)).toBe(ZONE_NEUTRAL);
    expect(evalZoneColor(-0.20)).toBe(ZONE_NEUTRAL);
  });

  it('value at the upper neutral boundary (+0.30) returns ZONE_SUCCESS', () => {
    expect(evalZoneColor(0.30)).toBe(ZONE_SUCCESS);
  });

  it('value above +0.30 returns ZONE_SUCCESS', () => {
    expect(evalZoneColor(0.50)).toBe(ZONE_SUCCESS);
    expect(evalZoneColor(1.0)).toBe(ZONE_SUCCESS);
  });

  it('value at the lower neutral boundary (-0.30) returns ZONE_DANGER', () => {
    expect(evalZoneColor(-0.30)).toBe(ZONE_DANGER);
  });

  it('value below -0.30 returns ZONE_DANGER', () => {
    expect(evalZoneColor(-0.50)).toBe(ZONE_DANGER);
    expect(evalZoneColor(-1.0)).toBe(ZONE_DANGER);
  });

  it('white engine baseline (+0.25) sits in the neutral zone (within ±0.30 of 0)', () => {
    // Per 260504-rvh + symmetric recalibration: the per-color baseline is now
    // ±0.25, which falls inside the ±0.30 neutral zone. A user sitting exactly
    // at the typical asymmetry reads as engine-balanced-ish, not as a signal.
    expect(evalZoneColor(EVAL_BASELINE_PAWNS_WHITE)).toBe(ZONE_NEUTRAL);
  });

  it('black engine baseline (-0.25) sits in the neutral zone (within ±0.30 of 0)', () => {
    expect(evalZoneColor(EVAL_BASELINE_PAWNS_BLACK)).toBe(ZONE_NEUTRAL);
  });
});

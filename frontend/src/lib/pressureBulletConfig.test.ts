import { describe, it, expect } from 'vitest';
import {
  PRESSURE_DELTA_CENTER,
  PRESSURE_DELTA_DOMAIN,
  CLOCK_GAP_DOMAIN,
  clampDeltaCi,
  pressureDeltaZoneColor,
} from './pressureBulletConfig';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

describe('pressureBulletConfig constants', () => {
  it('PRESSURE_DELTA_CENTER is 0', () => {
    expect(PRESSURE_DELTA_CENTER).toBe(0);
  });

  it('PRESSURE_DELTA_DOMAIN is 0.20', () => {
    expect(PRESSURE_DELTA_DOMAIN).toBe(0.20);
  });

  it('CLOCK_GAP_DOMAIN is 0.30', () => {
    expect(CLOCK_GAP_DOMAIN).toBe(0.30);
  });
});

describe('clampDeltaCi', () => {
  it('clamps values above 1 to 1', () => {
    expect(clampDeltaCi(1.5)).toBe(1);
    expect(clampDeltaCi(2.0)).toBe(1);
  });

  it('clamps values below -1 to -1', () => {
    expect(clampDeltaCi(-1.5)).toBe(-1);
    expect(clampDeltaCi(-2.0)).toBe(-1);
  });

  it('passes through values within [-1, 1] unchanged', () => {
    expect(clampDeltaCi(0.1)).toBe(0.1);
    expect(clampDeltaCi(0.0)).toBe(0.0);
    expect(clampDeltaCi(-0.1)).toBe(-0.1);
    expect(clampDeltaCi(1.0)).toBe(1);
    expect(clampDeltaCi(-1.0)).toBe(-1);
  });
});

describe('pressureDeltaZoneColor', () => {
  const neutralMin = -0.06;
  const neutralMax = 0.06;

  it('returns ZONE_SUCCESS when delta >= neutralMax', () => {
    expect(pressureDeltaZoneColor(neutralMax, neutralMin, neutralMax)).toBe(ZONE_SUCCESS);
    expect(pressureDeltaZoneColor(0.10, neutralMin, neutralMax)).toBe(ZONE_SUCCESS);
    expect(pressureDeltaZoneColor(0.15, neutralMin, neutralMax)).toBe(ZONE_SUCCESS);
  });

  it('returns ZONE_DANGER when delta <= neutralMin', () => {
    expect(pressureDeltaZoneColor(neutralMin, neutralMin, neutralMax)).toBe(ZONE_DANGER);
    expect(pressureDeltaZoneColor(-0.10, neutralMin, neutralMax)).toBe(ZONE_DANGER);
    expect(pressureDeltaZoneColor(-0.15, neutralMin, neutralMax)).toBe(ZONE_DANGER);
  });

  it('returns ZONE_NEUTRAL for deltas between neutralMin and neutralMax', () => {
    expect(pressureDeltaZoneColor(0.0, neutralMin, neutralMax)).toBe(ZONE_NEUTRAL);
    expect(pressureDeltaZoneColor(0.03, neutralMin, neutralMax)).toBe(ZONE_NEUTRAL);
    expect(pressureDeltaZoneColor(-0.03, neutralMin, neutralMax)).toBe(ZONE_NEUTRAL);
  });

  it('accepts varying neutralMin/neutralMax per (TC, quintile)', () => {
    // Tighter band (high-pressure quintile)
    expect(pressureDeltaZoneColor(0.04, -0.04, 0.04)).toBe(ZONE_SUCCESS);
    expect(pressureDeltaZoneColor(-0.04, -0.04, 0.04)).toBe(ZONE_DANGER);
    expect(pressureDeltaZoneColor(0.02, -0.04, 0.04)).toBe(ZONE_NEUTRAL);
  });
});

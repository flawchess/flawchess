import { describe, it, expect } from 'vitest';

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import {
  ENDGAME_ENTRY_EVAL_CENTER,
  ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS,
  ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS,
  ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS,
  endgameEntryEvalZoneColor,
} from '@/lib/endgameEntryEvalZones';

describe('endgameEntryEvalZones constants', () => {
  it('uses ±0.75 pawn neutral band (benchmark IQR max(|p25|, |p75|) = 75 cp)', () => {
    expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.75);
    expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS).toBe(0.75);
  });
  it('centers on 0 pawns (D-07 H0)', () => {
    expect(ENDGAME_ENTRY_EVAL_CENTER).toBe(0);
  });
  it('uses ±3.75 pawn axis so the neutral band fills 20% of the chart (matches Achievable-score proportion)', () => {
    expect(ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS).toBe(3.75);
    const neutralFraction =
      (ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS - ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS) /
      (2 * ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS);
    expect(neutralFraction).toBeCloseTo(0.2, 6);
  });
});

describe('endgameEntryEvalZoneColor', () => {
  it('returns NEUTRAL for values inside the ±0.75 pawn band', () => {
    expect(endgameEntryEvalZoneColor(0)).toBe(ZONE_NEUTRAL);
    expect(endgameEntryEvalZoneColor(0.74)).toBe(ZONE_NEUTRAL);
    expect(endgameEntryEvalZoneColor(-0.74)).toBe(ZONE_NEUTRAL);
  });
  it('returns SUCCESS at and above +0.75 pawns', () => {
    expect(endgameEntryEvalZoneColor(0.75)).toBe(ZONE_SUCCESS);
    expect(endgameEntryEvalZoneColor(0.8)).toBe(ZONE_SUCCESS);
    expect(endgameEntryEvalZoneColor(2.0)).toBe(ZONE_SUCCESS);
  });
  it('returns DANGER at and below -0.75 pawns', () => {
    expect(endgameEntryEvalZoneColor(-0.75)).toBe(ZONE_DANGER);
    expect(endgameEntryEvalZoneColor(-0.8)).toBe(ZONE_DANGER);
    expect(endgameEntryEvalZoneColor(-2.0)).toBe(ZONE_DANGER);
  });
});

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
  it('uses ±2.0 pawn axis domain (D-15)', () => {
    expect(ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS).toBe(2.0);
  });
  it('uses ±0.5 pawn neutral band (Phase 82 D-09: half-pawn average swings are narratable)', () => {
    expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.5);
    expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS).toBe(0.5);
  });
  it('centers on 0 pawns (D-07 H0)', () => {
    expect(ENDGAME_ENTRY_EVAL_CENTER).toBe(0);
  });
});

describe('endgameEntryEvalZoneColor', () => {
  it('returns NEUTRAL for values inside the ±0.5 pawn band', () => {
    expect(endgameEntryEvalZoneColor(0)).toBe(ZONE_NEUTRAL);
    expect(endgameEntryEvalZoneColor(0.49)).toBe(ZONE_NEUTRAL);
    expect(endgameEntryEvalZoneColor(-0.49)).toBe(ZONE_NEUTRAL);
  });
  it('returns SUCCESS at and above +0.5 pawns', () => {
    expect(endgameEntryEvalZoneColor(0.5)).toBe(ZONE_SUCCESS);
    expect(endgameEntryEvalZoneColor(0.6)).toBe(ZONE_SUCCESS);
    expect(endgameEntryEvalZoneColor(2.0)).toBe(ZONE_SUCCESS);
  });
  it('returns DANGER at and below -0.5 pawns', () => {
    expect(endgameEntryEvalZoneColor(-0.5)).toBe(ZONE_DANGER);
    expect(endgameEntryEvalZoneColor(-0.6)).toBe(ZONE_DANGER);
    expect(endgameEntryEvalZoneColor(-2.0)).toBe(ZONE_DANGER);
  });
});

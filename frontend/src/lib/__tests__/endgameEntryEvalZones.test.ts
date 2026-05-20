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
  it('uses ±0.60 pawn neutral band (editorially tightened per diff item A 2026-05-17 vs 2026-05-19)', () => {
    expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS).toBe(-0.60);
    expect(ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS).toBe(0.60);
  });
  it('centers on 0 pawns (D-07 H0)', () => {
    expect(ENDGAME_ENTRY_EVAL_CENTER).toBe(0);
  });
  it('uses ±2.25 pawn axis domain (unchanged)', () => {
    expect(ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS).toBe(2.25);
  });
});

describe('endgameEntryEvalZoneColor', () => {
  it('returns NEUTRAL for values inside the ±0.60 pawn band', () => {
    expect(endgameEntryEvalZoneColor(0)).toBe(ZONE_NEUTRAL);
    expect(endgameEntryEvalZoneColor(0.59)).toBe(ZONE_NEUTRAL);
    expect(endgameEntryEvalZoneColor(-0.59)).toBe(ZONE_NEUTRAL);
  });
  it('returns SUCCESS at and above +0.60 pawns', () => {
    expect(endgameEntryEvalZoneColor(0.60)).toBe(ZONE_SUCCESS);
    expect(endgameEntryEvalZoneColor(0.8)).toBe(ZONE_SUCCESS);
    expect(endgameEntryEvalZoneColor(2.0)).toBe(ZONE_SUCCESS);
  });
  it('returns DANGER at and below -0.60 pawns', () => {
    expect(endgameEntryEvalZoneColor(-0.60)).toBe(ZONE_DANGER);
    expect(endgameEntryEvalZoneColor(-0.8)).toBe(ZONE_DANGER);
    expect(endgameEntryEvalZoneColor(-2.0)).toBe(ZONE_DANGER);
  });
});

/**
 * fastForwardStops.test.ts: the Jump stop set, both-sides by default and
 * filtered to the user's plies when the own-moves setting is on.
 */
import { describe, expect, it } from 'vitest';

import { computeFastForwardStops } from '@/lib/fastForwardStops';
import type { EvalPoint, FlawMarker, FlawSeverity } from '@/types/library';

function marker(ply: number, severity: FlawSeverity): FlawMarker {
  return {
    ply,
    severity,
    tags: [],
    is_user: false,
    move_san: null,
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
  };
}

function point(ply: number, tier: EvalPoint['best_move_tier']): EvalPoint {
  return {
    ply,
    es: 0.5,
    eval_cp: 0,
    eval_mate: null,
    clock_seconds: null,
    move_seconds: null,
    best_move: null,
    best_move_tier: tier,
    maia_prob: null,
  };
}

// White blunder (ply 4), black mistake (ply 7), white gem (ply 10), black great (ply 13),
// plus noise that is never a stop: an inaccuracy and best/good tiers.
const FLAW_MARKERS: FlawMarker[] = [marker(4, 'blunder'), marker(7, 'mistake'), marker(9, 'inaccuracy')];
const EVAL_SERIES: EvalPoint[] = [
  point(10, 'gem'),
  point(13, 'great'),
  point(14, 'best'),
  point(15, 'good'),
  point(16, null),
];

describe('computeFastForwardStops', () => {
  it('stops on both sides when ownMovesOnly is off', () => {
    const stops = computeFastForwardStops({
      flawMarkers: FLAW_MARKERS,
      evalSeries: EVAL_SERIES,
      userColor: 'white',
      ownMovesOnly: false,
    });
    expect([...stops].sort((a, b) => a - b)).toEqual([4, 7, 10, 13]);
  });

  it('keeps only the white (even) plies for a white user when ownMovesOnly is on', () => {
    const stops = computeFastForwardStops({
      flawMarkers: FLAW_MARKERS,
      evalSeries: EVAL_SERIES,
      userColor: 'white',
      ownMovesOnly: true,
    });
    expect([...stops].sort((a, b) => a - b)).toEqual([4, 10]);
  });

  it('keeps only the black (odd) plies for a black user when ownMovesOnly is on', () => {
    const stops = computeFastForwardStops({
      flawMarkers: FLAW_MARKERS,
      evalSeries: EVAL_SERIES,
      userColor: 'black',
      ownMovesOnly: true,
    });
    expect([...stops].sort((a, b) => a - b)).toEqual([7, 13]);
  });

  it.each([null, undefined, 'unknown', ''])(
    'falls back to both sides for unusable user color %j',
    (userColor) => {
      const stops = computeFastForwardStops({
        flawMarkers: FLAW_MARKERS,
        evalSeries: EVAL_SERIES,
        userColor,
        ownMovesOnly: true,
      });
      expect([...stops].sort((a, b) => a - b)).toEqual([4, 7, 10, 13]);
    },
  );

  it('returns an empty set for null or undefined inputs', () => {
    expect(
      computeFastForwardStops({ flawMarkers: null, evalSeries: null, userColor: 'white', ownMovesOnly: true }).size,
    ).toBe(0);
    expect(
      computeFastForwardStops({
        flawMarkers: undefined,
        evalSeries: undefined,
        userColor: undefined,
        ownMovesOnly: false,
      }).size,
    ).toBe(0);
  });
});

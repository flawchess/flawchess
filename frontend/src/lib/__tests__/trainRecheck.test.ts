import { describe, expect, it } from 'vitest';
import { buildRecheckPayload, recheckOutcome, shouldRecheck } from '@/lib/trainRecheck';
import type { ShouldRecheckInput } from '@/lib/trainRecheck';
import type { TrainMoveTier } from '@/lib/trainScore';

const BASE: ShouldRecheckInput = {
  puzzleType: 'sharp',
  keyUci: 'd2d4',
  runnerUpUci: 'c2c4',
  playedUci: 'e2e4',
  tier: 'good',
  serverGradedUcis: [],
};

describe('shouldRecheck (D-10, D-19)', () => {
  it('fires for a sharp keyed puzzle whose off-key, off-runner-up move graded good', () => {
    expect(shouldRecheck(BASE)).toBe(true);
  });

  it('fires when the puzzle has no runner-up', () => {
    expect(shouldRecheck({ ...BASE, runnerUpUci: null })).toBe(true);
  });

  it.each([
    ['soft', { puzzleType: 'soft' as const }],
    ['herring', { puzzleType: 'herring' as const }],
    ['null type', { puzzleType: null }],
    ['null key', { keyUci: null }],
    ['played == key', { playedUci: 'd2d4' }],
    ['played == runner-up', { playedUci: 'c2c4' }],
    ['wrong', { tier: 'wrong' as const }],
  ])('never fires for %s', (_label, override) => {
    expect(shouldRecheck({ ...BASE, ...override })).toBe(false);
  });
});

describe('shouldRecheck: inaccuracy rescue (quick 261008-ob1)', () => {
  const INACCURACY: ShouldRecheckInput = { ...BASE, tier: 'inaccuracy' };

  it.each([
    ['sharp', { puzzleType: 'sharp' as const }],
    ['soft', { puzzleType: 'soft' as const, runnerUpUci: null }],
    ['herring', { puzzleType: 'herring' as const, runnerUpUci: null }],
  ])('fires for an off-key inaccuracy on a %s puzzle', (_label, override) => {
    expect(shouldRecheck({ ...INACCURACY, ...override })).toBe(true);
  });

  it.each([
    ['null key', { keyUci: null }],
    ['played == key', { playedUci: 'd2d4' }],
    ['played == runner-up', { playedUci: 'c2c4' }],
    ['wrong on a soft puzzle', { puzzleType: 'soft' as const, tier: 'wrong' as const }],
  ])('never fires for %s', (_label, override) => {
    expect(shouldRecheck({ ...INACCURACY, ...override })).toBe(false);
  });
});

describe('shouldRecheck: server-graded moves are never re-checked (Phase 236 D-11)', () => {
  it.each([
    ['inaccuracy on a soft puzzle', { puzzleType: 'soft' as const, tier: 'inaccuracy' as const }],
    ['sharp + good', { puzzleType: 'sharp' as const, tier: 'good' as const }],
    ['sharp + inaccuracy', { puzzleType: 'sharp' as const, tier: 'inaccuracy' as const }],
  ])('returns false for a played move in the server-graded set: %s', (_label, override) => {
    expect(
      shouldRecheck({ ...BASE, ...override, serverGradedUcis: ['d2d4', 'e2e4'] }),
    ).toBe(false);
  });

  it('still fires when the played move is not in the server-graded set', () => {
    expect(shouldRecheck({ ...BASE, serverGradedUcis: ['d2d4', 'g1f3'] })).toBe(true);
  });
});

describe('recheckOutcome (D-13)', () => {
  it('is confirmed for a good tier and resolved for every other tier', () => {
    expect(recheckOutcome('good')).toBe('confirmed');
    const others: TrainMoveTier[] = ['inaccuracy', 'wrong'];
    for (const tier of others) expect(recheckOutcome(tier)).toBe('resolved');
  });
});

describe('buildRecheckPayload (D-17)', () => {
  it('maps the readings to the snake_case wire keys with schema version 1', () => {
    expect(
      buildRecheckPayload({
        outcome: 'confirmed',
        keyEs: 0.6,
        playedEs: 0.59,
        keyDepth: 12,
        playedDepth: 11,
        keyEsRecheck: 0.61,
        playedEsRecheck: 0.62,
        keyDepthRecheck: 18,
        playedDepthRecheck: 17,
      }),
    ).toEqual({
      v: 1,
      outcome: 'confirmed',
      key_es: 0.6,
      played_es: 0.59,
      key_es_recheck: 0.61,
      played_es_recheck: 0.62,
      key_depth: 12,
      played_depth: 11,
      key_depth_recheck: 18,
      played_depth_recheck: 17,
    });
  });

  it('sends a null depth as 0', () => {
    const payload = buildRecheckPayload({
      outcome: 'resolved',
      keyEs: 0.5,
      playedEs: 0.5,
      keyDepth: null,
      playedDepth: null,
      keyEsRecheck: 0.5,
      playedEsRecheck: 0.3,
      keyDepthRecheck: null,
      playedDepthRecheck: null,
    });
    expect(payload.key_depth).toBe(0);
    expect(payload.played_depth).toBe(0);
    expect(payload.key_depth_recheck).toBe(0);
    expect(payload.played_depth_recheck).toBe(0);
  });
});

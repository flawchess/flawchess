import { describe, expect, it } from 'vitest';

import { buildPhoneGradePayload, instantServerTier } from '@/lib/trainPhoneGrade';
import type { ServerGradedMove } from '@/types/train';

describe('buildPhoneGradePayload', () => {
  it('maps every camelCase field to the snake_case wire record', () => {
    expect(
      buildPhoneGradePayload({
        tier: 'inaccuracy',
        keyEs: 0.62,
        playedEs: 0.55,
        keyDepth: 14,
        playedDepth: 12,
      }),
    ).toEqual({
      v: 1,
      tier: 'inaccuracy',
      key_es: 0.62,
      played_es: 0.55,
      key_depth: 14,
      played_depth: 12,
    });
  });

  it('sends a null depth as 0', () => {
    const payload = buildPhoneGradePayload({
      tier: 'good',
      keyEs: 0.5,
      playedEs: 0.5,
      keyDepth: null,
      playedDepth: null,
    });
    expect(payload.key_depth).toBe(0);
    expect(payload.played_depth).toBe(0);
  });

  it('has exactly the six wire keys and no device or engine field (D-07)', () => {
    const payload = buildPhoneGradePayload({
      tier: 'wrong',
      keyEs: 0.7,
      playedEs: 0.3,
      keyDepth: 10,
      playedDepth: 10,
    });
    expect(Object.keys(payload).sort()).toEqual([
      'key_depth',
      'key_es',
      'played_depth',
      'played_es',
      'tier',
      'v',
    ]);
  });
});

describe('instantServerTier (Phase 236 D-09/D-10)', () => {
  const MOVES: ServerGradedMove[] = [
    { uci: 'd2d4', tier: 'good' },
    { uci: 'e2e4', tier: 'inaccuracy' },
  ];

  it('is null on the legacy path (no key)', () => {
    expect(instantServerTier(MOVES, 'e2e4', null)).toBeNull();
  });

  it('is null when the played move is the key, even while the key is listed (D-13/D-05)', () => {
    expect(instantServerTier(MOVES, 'd2d4', 'd2d4')).toBeNull();
  });

  it('returns the tier of a listed non-key move', () => {
    expect(instantServerTier(MOVES, 'e2e4', 'd2d4')).toBe('inaccuracy');
  });

  it('the first entry wins on a duplicate UCI', () => {
    const dup: ServerGradedMove[] = [
      { uci: 'e2e4', tier: 'good' },
      { uci: 'e2e4', tier: 'wrong' },
    ];
    expect(instantServerTier(dup, 'e2e4', 'd2d4')).toBe('good');
  });

  it('is null for an unlisted move', () => {
    expect(instantServerTier(MOVES, 'g1f3', 'd2d4')).toBeNull();
  });

  it('is null for an empty list', () => {
    expect(instantServerTier([], 'e2e4', 'd2d4')).toBeNull();
  });
});
